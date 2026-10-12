"""Inicializador UNICO do Idle Game Agent.

Um processo Python, uma porta localhost e um painel:
- IO Chrome: /api/sync com token da extensão existente, somente leitura.
- Planejador World, PokeGrid, capturas sem VIP: arquivos manuais locais.
- Livro-caixa: read-only por conta explicitamente cadastrada.
- IVs: cálculo local PokeGrid via Node opcional; sem acesso ao jogo.
Nenhuma transação, login, macro nem bot do World é iniciado.
"""
from __future__ import annotations
import argparse
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

import dashboard
from app.memory import MemoryStore
from app.tab_registry import Registry, load_token

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORT = 8768
VERSION = 1


def available_files(root: Path = ROOT) -> dict:
    """Nunca copiar exemplos para data/ nem tratá-los como dados reais."""
    data = root / "data"
    choices = {
        "accounts_path": data / "accounts.json",
        "world_report_path": data / "world_snapshots.json",
        "world_capture_path": data / "world_capture.json",
        "ivs_path": data / "world_ivs.json",
        "ledger_path": data / "financial.sqlite3",
    }
    return {key: path if path.is_file() else None for key, path in choices.items()}


def existing_unified_server(port: int) -> bool:
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/unified/status",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=1.0) as res:
            if res.status != 200:
                return False
            import json
            data = json.loads(res.read(2048))
            return data.get("app") == "idle-game-agent" and data.get("mode") == "unified"
    except (OSError, ValueError, TimeoutError):
        return False


def launch(*, port: int = DEFAULT_PORT, browser: bool = True, root: Path = ROOT) -> int:
    if not 1024 <= port <= 65535:
        raise ValueError("Porta deve estar entre 1024 e 65535")
    url = f"http://127.0.0.1:{port}"
    if existing_unified_server(port):
        print("O painel unificado ja esta aberto. Reutilizando a janela.")
        if browser:
            webbrowser.open(url)
        return 0
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)
    registry = Registry(
        load_token(data / "tab_registry_token.txt"),
        MemoryStore(data / "agent.sqlite3"),
    )
    options = available_files(root)
    print("IDLE GAME AGENT - PAINEL UNIFICADO")
    print("IO: leitura da extensao Chrome, sem comandos de jogo.")
    print("World: dados manuais; sem Auto-Throw, login ou bots externos.")
    print("Livro-caixa: leitura local; nenhum saque, compra ou venda automatica.")
    print("URL: " + url)
    print("Extensao Chrome: carregue chrome_extension/ e emparelhe com a")
    print("chave local em data/tab_registry_token.txt. NAO a compartilhe.")
    for key, path in options.items():
        print(("[OK] " if path else "[AGUARDANDO] ") + key +
              (": " + path.name if path else " (nenhum arquivo privado configurado)"))
    print("Ctrl+C encerra todos os servicos deste processo.")
    try:
        dashboard.start(
            root / "examples" / "sessoes_demo.csv",
            port,
            options["ledger_path"],
            None,
            options["world_report_path"],
            options["world_capture_path"],
            registry=registry,
            accounts_path=options["accounts_path"],
            ivs_path=options["ivs_path"],
            open_browser=browser,
        )
        return 0
    except OSError as exc:
        print(f"Nao foi possivel abrir {url}: {exc}", file=sys.stderr)
        print("Verifique se a porta esta ocupada por um monitor antigo.", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Idle Game Agent: um BAT, painel/monitor na mesma porta"
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--check", action="store_true",
                        help="Somente verificar requisitos, sem iniciar servidor")
    args = parser.parse_args(argv)
    if args.check:
        for rel in ("dashboard.py", "chrome_extension/manifest.json",
                    "app/world_capture_assistant.py", "app/world_pokegrid_report.py",
                    "app/io_action_engine.py", "tools/pokegrid_iv_cli.js"):
            if not (ROOT / rel).is_file():
                print("FALTA: " + rel, file=sys.stderr)
                return 1
        print("OK: painel, extensao, IO, World e IVs presentes.")
        return 0
    return launch(port=args.port, browser=not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
