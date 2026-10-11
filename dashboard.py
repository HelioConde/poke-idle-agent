"""Painel local de comparação de sessões. Somente GET em 127.0.0.1."""
import argparse
import json
import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from app.lab import aggregate, load_sessions

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"

def start(csv_path: Path, port: int) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("Porta inválida")

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
    args = parser.parse_args()
    start(args.csv.resolve(), args.port)

if __name__ == "__main__":
    main()
