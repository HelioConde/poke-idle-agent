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
from urllib.parse import parse_qs, urlsplit

from app.io_advisory import build_io_advisory
from app.io_telemetry import (dry_run_decision, measured_xp_per_hour, sanitize,
                              sanitize_observation, sanitize_automation_audit)
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
.table-scroll{overflow-x:auto;max-width:100%}
table{border-collapse:collapse;width:100%;min-width:1240px;font-size:13px}
th,td{padding:12px;text-align:left;border-bottom:1px solid #34445c}
th{color:#b5c5e4;white-space:nowrap}td{overflow-wrap:break-word}
.tag{background:#344569;border-radius:7px;padding:3px 8px;display:inline-block}
</style>
<h1>Abas dos jogos</h1>
<p>Localiza abas abertas em segundo plano. No IO, também tenta ler métricas
numéricas do HUD. Não captura credenciais, screenshots ou executa ações.</p>
<div class="card"><b id="summary">Aguardando extensão...</b>
<p id="hint">Aguardando primeira sincronização da extensão.</p></div>
<div class="card"><div class="table-scroll"><table><thead><tr><th>Perfil</th><th>Jogo</th>
<th>Aba</th><th>Ativa</th><th>Nível</th><th>XP atual/máx.</th><th>XP/h</th><th>HP</th>
<th>Coins</th><th>Gems</th><th>Diagnóstico</th><th>Decisão simulada</th><th>Atualizada</th></tr></thead>
<tbody id="rows"><tr><td colspan="13">Aguardando...</td></tr></tbody></table></div>
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
   : 'Nenhuma sincronização recebida. Abra o popup da extensão para verificar emparelhamento e conexão local.';
 if(!data.tabs.length){const tr=document.createElement('tr');
 const td=document.createElement('td');td.colSpan=13;td.textContent='Nenhuma aba sincronizada.';
 tr.appendChild(td);body.appendChild(tr);}
 for(const row of data.tabs){
  const tr=document.createElement('tr');
  const stats=row.telemetry?.stats||{};
  const read=(value)=>typeof value==='number'?value.toLocaleString('pt-BR'):'—';
  const hp=typeof stats.hp_current==='number'
    ?read(stats.hp_current)+(typeof stats.hp_max==='number'?'/'+read(stats.hp_max):''):'—';
  const obs=row.observation||{};
  const legacy=obs.status==='legacy_protocol';
  const xp=legacy?'Bloqueado: leitor desatualizado':(typeof stats.xp_current==='number'
    ?read(stats.xp_current)+(typeof stats.xp_max==='number'?'/'+read(stats.xp_max):''):'Aguardando segunda amostra');
  const rate=legacy?'Bloqueado: protocolo incompatível':read(row.xp_per_hour);
  const explanations={
    landing:"Página inicial. Clique em Jogar Grátis para entrar em /app.",
    other_route:"Fora de /app: confirme se abriu o jogo.",
    reader_unavailable:"Leitor não respondeu: recarregue extensão e aba /app.",
    no_matches:"DOM acessado, mas HUD ainda não reconhecido.",
    metrics:"Leitura numérica disponível.",
    legacy_protocol:"Leitor desatualizado: recarregue a extensão 0.2.2 e a aba /app."
  };
  let diagnostic=row.game==='world'?'World: somente identificação de aba':
    (explanations[obs.status]||"Aguardando dados");
  if(row.game==='io'&&obs.status==='no_matches'){
    diagnostic+=' Canvas '+(obs.canvas||0)+', iframes '+(obs.iframes||0)+
      ', elementos '+(obs.candidates||0);
  }
  if(row.game==='io' && obs.xp_ambiguous===true){
    diagnostic='XP ambíguo: '+obs.xp_candidates+
      ' barras diferentes no DOM; nenhuma foi selecionada.';
  } else if(row.game==='io' && obs.xp_trainer_scoped===true) {
    diagnostic='XP do treinador identificado em tr-dados; Pokémon separado.';
  } else if(row.game==='io' && obs.xp_reason){
    const reasons={
      trainer_panel_missing:'Quadro tr-dados não localizado; XP/h bloqueado.',
      trainer_level_missing:'Nível do treinador ausente no quadro; XP/h bloqueado.',
      trainer_xp_missing:'Barra de XP do treinador ausente ou incompleta; XP/h bloqueado.',
      trainer_xp_ambiguous:'Mais de uma barra no quadro do treinador; XP/h bloqueado.',
      reader_unavailable:'Content script não respondeu; nenhuma métrica foi inventada.',
      unknown:'Extensão sem diagnóstico de origem; recarregue a versão 0.2.2.'
    };
    diagnostic=reasons[obs.xp_reason]||diagnostic;
  }
  if(row.game==='io' && obs.content_state==='outdated'){
    diagnostic='Content script desatualizado: recarregue a extensão e a aba /app.';
  }
  const advice=row.game==='world'?'Apenas identificação da aba':
    (row.advice?.reason||'Aguardando HUD no DOM');
  for(const value of [row.profile_label,row.game==='io'?'Poke Idle IO':'Poke Idle World',
    row.title,row.active?'Sim':'Não',read(stats.level),xp,rate,
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
        self.samples: dict[tuple[str, int, int], dict] = {}
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
                observation = sanitize_observation(tab["observation"])
                # Um diagnóstico parcial de versões anteriores tinha status=metrics,
                # mas não carregava a prova de escopo nem o protocolo 2. Tratá-lo
                # como leitura válida confundiria o painel; normalize explicitamente.
                entry["observation"] = (observation if "telemetry_protocol" in observation else {
                    "status": "legacy_protocol", "canvas": 0,
                    "iframes": 0, "candidates": 0,
                })
            elif tab["game"] == "io":
                # Protocolos anteriores não enviavam diagnóstico; mantemos a aba,
                # mas rejeitamos seus valores de XP para cálculo de XP/h.
                entry["observation"] = {"status": "legacy_protocol", "canvas": 0,
                                        "iframes": 0, "candidates": 0}
            if tab["game"] == "io" and "io_audit" in tab:
                entry["io_audit"] = sanitize_automation_audit(tab["io_audit"])
            if tab["game"] == "io" and "telemetry" in entry:
                # Nao confiar em XP de extensoes antigas (ou barras do Pokemon).
                # Somente a leitura comprovada em .tr-dados vale como XP do treinador.
                observation = entry.get("observation", {})
                scope_verified = (observation.get("xp_trainer_scoped") is True and
                                  observation.get("telemetry_protocol") == 2 and
                                  observation.get("reader_version") == "trainer-xp-scoped-v1" and
                                  observation.get("content_state") == "responded")
                if not scope_verified:
                    entry["telemetry"]["stats"].pop("xp_current", None)
                    entry["telemetry"]["stats"].pop("xp_max", None)
                    entry["telemetry"]["available"] = bool(entry["telemetry"]["stats"])
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
                # A taxa representa a aba atual, NÃO uma identidade de conta
                # confirmada. Nunca reaproveitar amostras entre janelas.
                key = (profile_id, tab["window_id"], tab["tab_id"])
                last = self.samples.get(key)
                observation = tab.get("observation", {})
                scope_verified = (observation.get("xp_trainer_scoped") is True and
                                  observation.get("telemetry_protocol") == 2 and
                                  observation.get("reader_version") == "trainer-xp-scoped-v1" and
                                  observation.get("content_state") == "responded")
                valid_xp = (scope_verified and type(stats.get("level")) is int and
                            type(stats.get("xp_current")) in (int, float) and
                            (stats.get("xp_max") is None or
                             type(stats["xp_max"]) in (int, float)))
                rate = None
                windows = {}
                if not valid_xp:
                    self.samples.pop(key, None)
                else:
                    # Troca de nível, barra, queda de XP ou intervalo sem
                    # leituras válidas encerra a janela anterior imediatamente.
                    previous = last["stats"] if last else None
                    invalid_transition = (last is not None and (
                        now - last["seen"] > EXPIRY_SECONDS or
                        previous.get("level") != stats["level"] or
                        previous.get("xp_max") != stats.get("xp_max") or
                        stats["xp_current"] < previous["xp_current"]))
                    if invalid_transition:
                        self.samples.pop(key, None)
                        last = None
                    if last and now - last["seen"] >= 5:
                        rate = measured_xp_per_hour(
                            last["stats"], stats, now - last["seen"])
                    elif last:
                        rate = last["rate"]
                    if not last:
                        self.samples[key] = {"seen": now, "stats": dict(stats),
                                             "rate": None, "history": [
                                                 (now, stats["xp_current"])]}
                    elif now - last["seen"] >= 5:
                        # Buffer estritamente numérico e temporário em RAM,
                        # com limite de tamanho, sem credenciais ou conta.
                        history = [(t, xp) for t, xp in last["history"]
                                   if now - t <= 3600]
                        history.append((now, stats["xp_current"]))
                        self.samples[key] = {
                            "seen": now, "stats": dict(stats), "rate": rate,
                            "history": history[-1024:]}
                    readings = self.samples[key]["history"]
                    for label, duration in (("5m", 300), ("15m", 900),
                                            ("60m", 3600)):
                        eligible = [(t, xp) for t, xp in readings
                                    if now - t <= duration]
                        if eligible and now - eligible[0][0] >= duration * 0.8:
                            elapsed = now - eligible[0][0]
                            delta = stats["xp_current"] - eligible[0][1]
                            if delta >= 0 and elapsed >= 5:
                                windows[label] = round(delta * 3600 / elapsed, 2)
                tab["xp_per_hour"] = rate
                tab["xp_windows"] = windows
                tab["advice"] = dry_run_decision(stats, windows.get("5m", rate))
                tab["advisory_queue"] = build_io_advisory(stats, windows, tab.get("io_audit"))
                if self.memory:
                    self.memory.record_observation(
                        profile_id=profile_id,
                        game="io",
                        session_id=f'{tab["window_id"]}:{tab["tab_id"]}',
                        state={"source": "dom", "stats": stats,
                               "observation": tab.get("observation")},
                        decision=tab["advice"],
                    )
            # Abas removidas ou navegando fora de /app não devem manter
            # leituras capazes de produzir uma taxa na próxima sessão.
            active_io = {(profile_id, tab["window_id"], tab["tab_id"])
                         for tab in cleaned if tab["game"] == "io"
                         and tab.get("route") == "app"}
            for key in list(self.samples):
                if key[0] == profile_id and key not in active_io:
                    del self.samples[key]
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

    def history(self, profile_id: str, window_id: int, tab_id: int,
                limit: int = 20) -> list[dict]:
        """Expõe somente o histórico normalizado de uma aba IO conhecida."""
        if self.memory is None:
            return []
        if (not PROFILE_ID.fullmatch(profile_id) or type(window_id) is not int or
                type(tab_id) is not int or window_id < 0 or tab_id < 0):
            raise ValueError("Consulta de histórico inválida")
        return self.memory.history(profile_id, f"{window_id}:{tab_id}", limit)


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
            elif path == "/api/history":
                query = parse_qs(urlsplit(self.path).query)
                try:
                    profile_id = query.get("profile_id", [""])[0]
                    window_id = int(query.get("window_id", [""])[0])
                    tab_id = int(query.get("tab_id", [""])[0])
                    limit = int(query.get("limit", ["20"])[0])
                    if not 1 <= limit <= 100:
                        raise ValueError
                    output = json.dumps(registry.history(
                        profile_id, window_id, tab_id, limit), ensure_ascii=False).encode()
                except (ValueError, TypeError):
                    self.send_error(400, "Consulta inválida")
                    return
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
