"""Painel local de comparação de sessões. Somente GET em 127.0.0.1."""
import argparse
import json
import mimetypes
import shutil
import subprocess
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from app.financial_ledger import FinancialLedger
from app.lab import aggregate, load_sessions
from app.world_pokegrid_report import analyze_file
from app.world_capture_assistant import analyze_file as analyze_world_capture
from app.adaptive_strategy import Account
from app.tab_registry import Registry, create_handler, PAGE as REGISTRY_PAGE, SCRIPT as REGISTRY_SCRIPT

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"

def start(csv_path: Path, port: int, ledger_path: Path | None = None,
          finance_identity: tuple[str, str, str] | None = None,
          world_report_path: Path | None = None,
          world_capture_path: Path | None = None,
          *, registry: Registry | None = None,
          accounts_path: Path | None = None,
          ivs_path: Path | None = None,
          open_browser: bool = False) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("Porta inválida")
    if registry is None and (ledger_path is None) != (finance_identity is None):
        raise ValueError("Ledger e identidade financeira devem ser informados juntos")
    if finance_identity is not None and ledger_path is None:
        raise ValueError("Conta financeira requer arquivo do livro-caixa")
    if ledger_path is not None and not ledger_path.is_file():
        raise ValueError("Ledger financeiro não encontrado")
    if world_report_path is not None and not world_report_path.is_file():
        raise ValueError("Relatório manual World não encontrado")
    if world_capture_path is not None and not world_capture_path.is_file():
        raise ValueError("Configuração manual de captura World não encontrada")
    if accounts_path is not None and not accounts_path.is_file():
        raise ValueError("Arquivo de contas não encontrado")
    if ivs_path is not None and not ivs_path.is_file():
        raise ValueError("Arquivo manual de IVs não encontrado")

    def read_accounts() -> list[Account]:
        if accounts_path is None:
            return []
        if accounts_path.stat().st_size > 1048576:
            raise ValueError("Arquivo de contas muito grande")
        raw = json.loads(accounts_path.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, list) or len(raw) > 100:
            raise ValueError("Lista de contas inválida")
        accounts = [Account.parse(item) for item in raw]
        if len({item.key for item in accounts}) != len(accounts):
            raise ValueError("Contas duplicadas")
        return accounts

    registry_handler = create_handler(registry) if registry is not None else BaseHTTPRequestHandler

    class Handler(registry_handler):
        def do_GET(self):  # noqa: N802
            path = urllib.parse.urlparse(self.path).path
            if registry is not None and path in {"/api/tabs", "/api/history"}:
                super().do_GET()
                return
            if path == "/api/unified/status":
                result = {"app": "idle-game-agent", "mode": "unified" if registry is not None else "legacy",
                          "registry_enabled": registry is not None, "world_execution": False,
                          "io_real_actions": False}
                payload = json.dumps(result).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(payload)
                return
            if registry is not None and path in {"/monitor", "/monitor/registry.js"}:
                if path == "/monitor":
                    body = REGISTRY_PAGE.replace('src="/app.js"', 'src="/monitor/registry.js"').encode("utf-8")
                    mimetype = "text/html; charset=utf-8"
                else:
                    body = REGISTRY_SCRIPT.encode("utf-8")
                    mimetype = "text/javascript; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", mimetype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/api/accounts":
                try:
                    info = []
                    for item in read_accounts():
                        active = next((p for p in item.roster if p.id == item.active_pokemon_id), None)
                        info.append({"game": item.game, "profile_id": item.profile_id,
                                     "account_id": item.account_id,
                                     "trainer_level": item.trainer_level,
                                     "pokemon_count": len(item.roster),
                                     "active_pokemon": active.species if active else None})
                    payload = json.dumps({"configured": accounts_path is not None,
                                          "accounts": info},ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(payload)))
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(payload)
                except (OSError, ValueError, TypeError) as error:
                    self.send_error(422, "Cadastro local inválido: " + str(error))
                return
            if path == "/api/world-ivs":
                try:
                    if ivs_path is None:
                        result = {"configured": False, "reason":
                                  "Copie exemplos para data/world_ivs.json e preencha manualmente."}
                    elif shutil.which("node") is None:
                        result = {"configured": False, "reason":
                                  "Node.js não instalado; cálculo de IVs opcional indisponível."}
                    else:
                        script = ROOT / "tools" / "pokegrid_iv_cli.js"
                        completed = subprocess.run(["node", str(script), str(ivs_path)],
                                                   cwd=ROOT, capture_output=True,
                                                   text=True, timeout=6, check=True)
                        result = {"configured": True, "report": json.loads(completed.stdout)}
                    payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(payload)))
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(payload)
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    self.send_error(422, "IVs manuais inválidos: " + str(error))
                return
            if path == "/api/summary":
                try:
                    result = aggregate(load_sessions(csv_path))
                    payload = json.dumps({
                        "games": result,
                        "source_file": csv_path.name,
                        "sample": all(x["source"] == "DEMONSTRAÇÃO" for x in result)
                    }, ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(payload)
                except (OSError, ValueError, KeyError) as error:
                    self.send_error(422, "CSV inválido: " + str(error))
                return
            if path == "/api/world-pokegrid":
                try:
                    report = ({"configured": True, "report": analyze_file(world_report_path)}
                              if world_report_path is not None
                              else {"configured": False, "reason":
                                    "Somente dados manuais; use --world-report data/world_snapshots.json"})
                    payload = json.dumps(report, ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(payload)
                except (OSError, ValueError, KeyError) as error:
                    self.send_error(422, "Relatório World inválido: " + str(error))
                return
            if path == "/api/world-capture":
                try:
                    report = ({"configured": True, "report": analyze_world_capture(world_capture_path)}
                              if world_capture_path is not None
                              else {"configured": False, "reason":
                                    "Arquivo manual ausente; use --world-capture data/world_capture.json"})
                    payload = json.dumps(report, ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(payload)
                except (OSError, ValueError, KeyError) as error:
                    self.send_error(422, "Configuração World inválida: " + str(error))
                return
            if path == "/api/finance":
                if ledger_path is None:
                    result = {"configured": False,
                              "reason": "Sem livro-caixa: data/financial.sqlite3 não encontrado."}
                else:
                    identity = finance_identity
                    if identity is None and registry is not None:
                        args = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                        game = args.get("game", [""])[0]
                        profile = args.get("profile", [""])[0]
                        account = args.get("account", [""])[0]
                        if (game, profile, account) in {item.key for item in read_accounts()}:
                            identity = (game, profile, account)
                    if identity is None:
                        result = {"configured": False,
                                  "reason": "Selecione uma conta IO cadastrada para consultar o livro-caixa."}
                    else:
                        game, profile_id, account_id = identity
                        result = {"configured": True,
                                  "summary": FinancialLedger(ledger_path).summary(
                                      game=game, profile_id=profile_id, account_id=account_id)}
                payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(payload)
                return
            if path == "/":
                path = "/index.html"
            if path not in {"/index.html", "/styles.css", "/app.js"}:
                self.send_error(404)
                return
            body = (PUBLIC / path.removeprefix("/")).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(path)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Painel local: http://127.0.0.1:{port}")
    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=ROOT / "examples" / "sessoes_demo.csv")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--finance-game", choices=("io", "world"))
    parser.add_argument("--finance-profile")
    parser.add_argument("--finance-account")
    parser.add_argument("--world-report", type=Path,
                        help="JSON manual World para análise PokeGrid offline")
    parser.add_argument("--world-capture", type=Path,
                        help="JSON manual World com contas, Pokébolas e capturas")
    args = parser.parse_args()
    fields = (args.finance_game, args.finance_profile, args.finance_account)
    if any(fields) and not all(fields):
        parser.error("Informe jogo, perfil e conta juntos para a visão financeira")
    if bool(args.ledger) != all(fields):
        parser.error("--ledger e identidade financeira devem ser informados juntos")
    start(args.csv.resolve(), args.port, args.ledger.resolve() if args.ledger else None,
          fields if all(fields) else None,
          args.world_report.resolve() if args.world_report else None,
          args.world_capture.resolve() if args.world_capture else None)

if __name__ == "__main__":
    main()
