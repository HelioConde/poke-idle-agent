"""Painel local de comparação de sessões. Somente GET em 127.0.0.1."""
import argparse
import json
import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from app.financial_ledger import FinancialLedger
from app.lab import aggregate, load_sessions
from app.world_pokegrid_report import analyze_file

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"

def start(csv_path: Path, port: int, ledger_path: Path | None = None,
          finance_identity: tuple[str, str, str] | None = None,
          world_report_path: Path | None = None) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("Porta inválida")
    if (ledger_path is None) != (finance_identity is None):
        raise ValueError("Ledger e identidade financeira devem ser informados juntos")
    if ledger_path is not None and not ledger_path.is_file():
        raise ValueError("Ledger financeiro não encontrado")
    if world_report_path is not None and not world_report_path.is_file():
        raise ValueError("Relatório manual World não encontrado")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            path = urllib.parse.urlparse(self.path).path
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
            if path == "/api/finance":
                if ledger_path is None or finance_identity is None:
                    result = {"configured": False,
                              "reason": "Informe --ledger, --finance-game, --finance-profile e --finance-account."}
                else:
                    game, profile_id, account_id = finance_identity
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
    args = parser.parse_args()
    fields = (args.finance_game, args.finance_profile, args.finance_account)
    if any(fields) and not all(fields):
        parser.error("Informe jogo, perfil e conta juntos para a visão financeira")
    if bool(args.ledger) != all(fields):
        parser.error("--ledger e identidade financeira devem ser informados juntos")
    start(args.csv.resolve(), args.port, args.ledger.resolve() if args.ledger else None,
          fields if all(fields) else None,
          args.world_report.resolve() if args.world_report else None)

if __name__ == "__main__":
    main()
