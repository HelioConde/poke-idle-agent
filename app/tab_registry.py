"""Registro local de abas do Chrome, sem screenshots, senhas ou ações no jogo."""
from __future__ import annotations

import argparse
import json
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from app.io_telemetry import dry_run_decision, measured_xp_per_hour, sanitize, sanitize_observation
from app.memory import MemoryStore

MAX_BODY = 16384
MAX_TABS = 40
EXPIRY_SECONDS = 120
PROFILE_ID = re.compile(r"^[0-9a-f-]{8,64}$", re.IGNORECASE)
EXTENSION_ORIGIN = re.compile(r"^chrome-extension://[a-p]{32}$")
ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = ROOT / "data" / "tab_registry_token.txt"

PAGE = """<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Idle Game Agent · Abas</title>
<style>
:root{font-family:system-ui,sans-serif;background:#0c1426;color:#eef2ff}
body{max-width:1320px;padding:25px;margin:auto}h1{font-size:clamp(25px,4vw,40px)}
p{color:#aebad0;line-height:1.6}.card{border:1px solid #354461;background:#15213a;
border-radius:14px;padding:20px;margin:12px 0}small{color:#92a5c2}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:12px;text-align:left;
border-bottom:1px solid #34445c;overflow-wrap:anywhere}th{color:#b5c5e4}
.tag{background:#344569;border-radius:7px;padding:3px 8px;display:inline-block}
</style>
<h1>Abas dos jogos</h1>
<p>Localiza abas abertas em segundo plano. No IO, também tenta ler métricas
numéricas do HUD. Não captura credenciais, screenshots ou executa ações.</p>
<div class="card"><b id="summary">Aguardando extensão...</b>
<p id="hint">Aguardando primeira sincronização da extensão.</p></div>
<div class="card"><table><thead><tr><th>Perfil</th><th>Jogo</th>
<th>Aba</th><th>Ativa</th><th>Nível</th><th>XP/h</th><th>HP</th>
<th>Coins</th><th>Gems</th><th>Diagnóstico</th><th>Decisão simulada</th><th>Atualizada</th></tr></thead>
<tbody id="rows"><tr><td colspan="12">Aguardando...</td></tr></tbody></table>
<p>XP/h só é calculado quando o DOM fornece duas amostras válidas no mesmo nível.
O coletor não lê Canvas, inventário privado ou dados da sessão.</p></div>
<script src="/app.js"></script>
</html>"""

SCRIPT = """async function refresh(){
const summary=document.getElementById('summary');
const hint=document.getElementById('hint');
const body=document.getElementById('rows');
try{
 const result=await fetch('/api/tabs',{cache:'no-store'});
 if(!result.ok)throw Error('HTTP '+result.status);
 const data=await result.json(); body.replaceChildren();
 const tabCount=data.tabs.length, profileCount=data.profiles;
 const inactive=data.tabs.filter(t=>!t.active).length;
 summary.textContent=tabCount+' '+(tabCount===1?'aba encontrada':'abas encontradas')+
   ' em '+profileCount+' '+(profileCount===1?'perfil':'perfis');
 hint.textContent=profileCount>0
   ? 'Extensão conectada e sincronizando. '+inactive+
     (inactive===1?' aba inativa detectada.':' abas inativas detectadas.')+
     ' Este painel mostra somente metadados; não captura imagens do jogo.'
   : 'Nenhum perfil sincronizado. Instale a extensão da pasta chrome_extension e informe a chave exibida no terminal.';
 if(!data.tabs.length){const tr=document.createElement('tr');
 const td=document.createElement('td');td.colSpan=12;td.textContent='Nenhuma aba sincronizada.';
 tr.appendChild(td);body.appendChild(tr);}
 for(const row of data.tabs){
  const tr=document.createElement('tr');
  const stats=row.telemetry?.stats||{};
  const read=(value)=>typeof value==='number'?value.toLocaleString('pt-BR'):'—';
  const hp=typeof stats.hp_current==='number'
    ?read(stats.hp_current)+(typeof stats.hp_max==='number'?'/'+read(stats.hp_max):''):'—';
  const obs=row.observation||{};
  const explanations={
    landing:"Página inicial. Clique em Jogar Grátis para entrar em /app.",
    other_route:"Fora de /app: confirme se abriu o jogo.",
    reader_unavailable:"Leitor não respondeu: recarregue extensão e aba /app.",
    no_matches:"DOM acessado, mas HUD ainda não reconhecido.",
    metrics:"Leitura numérica disponível."
  };
  let diagnostic=row.game==='world'?'World: somente identificação de aba':
    (explanations[obs.status]||"Aguardando dados");
  if(row.game==='io'&&obs.status==='no_matches'){
    diagnostic+=' Canvas '+(obs.canvas||0)+', iframes '+(obs.iframes||0)+
      ', elementos '+(obs.candidates||0);
  }
  const advice=row.game==='world'?'Apenas identificação da aba':
    (row.advice?.reason||'Aguardando HUD no DOM');
  for(const value of [row.profile_label,row.game==='io'?'Poke Idle IO':'Poke Idle World',
    row.title,row.active?'Sim':'Não',read(stats.level),read(row.xp_per_hour),
    hp,read(stats.coins),read(stats.gems),diagnostic,advice,row.age_seconds+'s atrás']){
   const td=document.createElement('td');td.textContent=String(value);tr.appendChild(td);
  }body.appendChild(tr);
 }
}catch(e){summary.textContent='Serviço indisponível: '+e.message;
 hint.textContent='Verifique se o monitor local está em execução.';}
}refresh();setInterval(refresh,3000);"""


class Registry:
    def __init__(self, token: str, memory: MemoryStore | None = None):
        self.token = token
        self.memory = memory
        self.records: dict[str, dict] = {}
        self.samples: dict[tuple[str, int], dict] = {}
        self.lock = threading.RLock()

    def ingest(self, data: object) -> int:
        if not isinstance(data, dict):
            raise ValueError("Formato inválido")
        profile_id = data.get("profile_id")
        if not isinstance(profile_id, str) or not PROFILE_ID.fullmatch(profile_id):
            raise ValueError("Identificador de perfil inválido")
        label = data.get("profile_label", "")
        if not isinstance(label, str) or len(label) > 48:
            raise ValueError("Nome de perfil inválido")
        tabs = data.get("tabs")
        if not isinstance(tabs, list) or len(tabs) > MAX_TABS:
            raise ValueError("Lista de abas inválida")
        cleaned = []
        seen = set()
        for tab in tabs:
            if not isinstance(tab, dict) or tab.get("game") not in ("io", "world"):
                raise ValueError("Jogo inválido")
            tab_id, window_id = tab.get("tab_id"), tab.get("window_id")
            if type(tab_id) is not int or type(window_id) is not int or tab_id < 0:
                raise ValueError("IDs inválidos")
            title = tab.get("title", "")
            if not isinstance(title, str) or len(title) > 120:
                raise ValueError("Título inválido")
            if type(tab.get("active")) is not bool:
                raise ValueError("Indicador de seleção inválido")
            route = tab.get("route") if tab.get("game") == "io" else None
            if route is not None and route not in ("landing", "app", "other"):
                raise ValueError("Rota IO inválida")
            key = (tab_id, window_id)
            if key in seen:
                raise ValueError("Aba duplicada")
            seen.add(key)
            entry = {"game": tab["game"], "tab_id": tab_id,
                     "window_id": window_id, "title": title,
                     "active": tab["active"]}
            if route is not None:
                entry["route"] = route
            if tab["game"] == "io" and "telemetry" in tab:
                if route != "app":
                    raise ValueError("Telemetria IO exige rota /app")
                entry["telemetry"] = sanitize(tab["telemetry"])
            if tab["game"] == "io" and "observation" in tab:
                if route is not None and route != "app" and tab["observation"].get("status") not in (
                        "landing", "other_route"):
                    raise ValueError("Diagnóstico não corresponde à rota IO")
                entry["observation"] = sanitize_observation(tab["observation"])
            if tab["game"] != "io" and (
                    "telemetry" in tab or "observation" in tab):
                raise ValueError("World não aceita telemetria de conta")
            cleaned.append(entry)
        with self.lock:
            now = time.monotonic()
            for tab in cleaned:
                if tab["game"] != "io":
                    continue
                reading = tab.get("telemetry")
                stats = (reading or {}).get("stats") or {}
                key = (profile_id, tab["tab_id"])
                last = self.samples.get(key)
                rate = last.get("rate") if last else None
                if not stats:
                    rate = None
                    self.samples.pop(key, None)
                if stats:
                    if last and now - last["seen"] >= 5:
                        rate = measured_xp_per_hour(
                            last["stats"], stats, now - last["seen"])
                    if not last or now - last["seen"] >= 5:
                        self.samples[key] = {
                            "seen": now, "stats": stats, "rate": rate}
                tab["xp_per_hour"] = rate
                tab["advice"] = dry_run_decision(stats, rate)
                if self.memory:
                    self.memory.record_observation(
                        profile_id=profile_id,
                        game="io",
                        session_id=f'{tab["window_id"]}:{tab["tab_id"]}',
                        state={"source": "dom", "stats": stats,
                               "observation": tab.get("observation")},
                        decision=tab["advice"],
                    )
            self.records[profile_id] = {
                "profile_label": label.strip() or "Perfil sem nome",
                "tabs": cleaned, "seen": now,
            }
        return len(cleaned)

    def snapshot(self) -> dict:
        with self.lock:
            now = time.monotonic()
            for key in list(self.records):
                if now - self.records[key]["seen"] > EXPIRY_SECONDS:
                    del self.records[key]
            for key, reading in list(self.samples.items()):
                if now - reading["seen"] > EXPIRY_SECONDS:
                    del self.samples[key]
            tabs = []
            for profile_id, profile in self.records.items():
                age = max(0, int(now - profile["seen"]))
                for tab in profile["tabs"]:
                    tabs.append({**tab, "profile_id": profile_id,
                                 "profile_label": profile["profile_label"],
                                 "age_seconds": age})
            tabs.sort(key=lambda t: (t["game"], t["profile_label"],
                                     t["window_id"], t["tab_id"]))
            return {"profiles": len(self.records), "tabs": tabs}


def load_token(path: Path = TOKEN_FILE) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        token = path.read_text(encoding="utf-8").strip()
        if len(token) < 32:
            raise ValueError("Chave local inválida; revise o arquivo de emparelhamento")
        return token
    token = secrets.token_urlsafe(32)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(token)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return token


def create_handler(registry: Registry):
    class Handler(BaseHTTPRequestHandler):
        def send_data(self, status: int, body: bytes, content_type: str,
                      origin: str | None = None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; script-src 'self'; "
                             "style-src 'unsafe-inline'; object-src 'none'")
            if origin and EXTENSION_ORIGIN.fullmatch(origin):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            origin = self.headers.get("Origin", "")
            if not EXTENSION_ORIGIN.fullmatch(origin):
                self.send_error(403)
                return
            if urlsplit(self.path).path != "/api/sync":
                self.send_error(404)
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers",
                             "Content-Type, X-IGA-Token")
            self.send_header("Access-Control-Max-Age", "600")
            self.end_headers()

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/":
                self.send_data(200, PAGE.encode(), "text/html; charset=utf-8")
            elif path == "/app.js":
                self.send_data(200, SCRIPT.encode(), "text/javascript; charset=utf-8")
            elif path == "/api/tabs":
                output = json.dumps(registry.snapshot(), ensure_ascii=False).encode()
                self.send_data(200, output, "application/json; charset=utf-8")
            else:
                self.send_error(404)

        def do_POST(self):
            origin = self.headers.get("Origin", "")
            if (urlsplit(self.path).path != "/api/sync" or
                    not EXTENSION_ORIGIN.fullmatch(origin)):
                self.send_error(403)
                return
            submitted_token = self.headers.get("X-IGA-Token", "")
            if not secrets.compare_digest(submitted_token, registry.token):
                self.send_error(401)
                return
            size = self.headers.get("Content-Length")
            if not size or not size.isdecimal() or not 1 <= int(size) <= MAX_BODY:
                self.send_error(413)
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.send_error(415)
                return
            try:
                request = json.loads(self.rfile.read(int(size)))
                count = registry.ingest(request)
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                self.send_error(400, "Dados inválidos")
                return
            response = json.dumps({"ok": True, "tab_count": count}).encode()
            self.send_data(200, response, "application/json", origin)
    return Handler


def main():
    parser = argparse.ArgumentParser(description="Monitor local de abas dos jogos")
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Escolha porta entre 1024 e 65535")
    token = load_token()
    memory = MemoryStore(ROOT / "data" / "agent.sqlite3")
    server = ThreadingHTTPServer(("127.0.0.1", args.port),
                                 create_handler(Registry(token, memory)))
    print("Idle Game Agent — monitor de abas do Chrome (somente leitura)")
    print(f"Painel: http://127.0.0.1:{args.port}")
    print(f"CHAVE DE EMPARELHAMENTO (uso local): {token}")
    print("Insira essa chave na extensão, nunca a publique no GitHub.")
    print("Use Ctrl+C para parar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
