/* Adaptador DOM mínimo: lê somente métricas numéricas já desenhadas na aba IO.
   Nunca lê localStorage, inputs, cookies, chat, URLs de sessão nem executa ações.
   Chrome pode suspender DOM/JS de abas inativas; nesse caso não fabricamos dados. */
"use strict";
(function () {
  const MAX_NODES = 3500;
  const DOM_READER_VERSION = "trainer-xp-scoped-v1";
  const RULES = [
    ["level", /^(?:[—–-]\s*)?(?:n[ií]vel|level|lv\.?|nv\.?|lvl\.?)\s*[:=#-]?\s*(\d[\d.,\s]*[kmb]?)\s*$/i],
    ["xp", /^(?:xp|exp|experi[eê]ncia)\s*[:=-]?\s*(\d[\d.,\s]*[kmb]?)(?:\s*\/\s*(\d[\d.,\s]*[kmb]?))?\s*$/i],
    ["hp", /^(?:hp|vida|health)\s*[:=-]?\s*(\d[\d.,\s]*[kmb]?)(?:\s*\/\s*(\d[\d.,\s]*[kmb]?))?\s*$/i],
    ["coins", /^(?:coins?|ouro|gold|moedas?)\s*[:=-]?\s*(\d[\d.,\s]*[kmb]?)\s*$/i],
    ["gems", /^(?:gems?|gemas?)\s*[:=-]?\s*(\d[\d.,\s]*[kmb]?)\s*$/i]
  ];
  const SKIP = /^(?:SCRIPT|STYLE|TEXTAREA|INPUT|OPTION|SELECT|NOSCRIPT)$/;
  // Duas representações reais no DOM: "XP: 7346 / 15400" e
  // "7.346 / 15.400 xp". Bonus "+15% XP" NUNCA corresponde.
  const XP_PREFIX = /^(?:xp|exp|experi[eê]ncia)\s*[:=-]?\s*(\d[\d.,\s]*[kmb]?)(?:\s*\/\s*(\d[\d.,\s]*[kmb]?))?\s*$/i;
  const XP_SUFFIX = /^(\d[\d.,]*[kmb]?)\s*\/\s*(\d[\d.,]*[kmb]?)\s*(?:xp|exp|experi[eê]ncia)\s*$/i;

  function toNumber(value) {
    if (typeof value !== "string") return null;
    const input = value.replace(/\s/g, "").trim().toLowerCase();
    const match = input.match(/^(\d[\d.,]*)([kmb]?)$/);
    if (!match) return null;
    let numeric = match[1];
    const commas = (numeric.match(/,/g) || []).length;
    const dots = (numeric.match(/\./g) || []).length;
    if (commas && dots) {
      const decimal = numeric.lastIndexOf(",") > numeric.lastIndexOf(".") ? "," : ".";
      const thousands = decimal === "," ? "." : ",";
      numeric = numeric.split(thousands).join("").replace(decimal, ".");
    } else if (commas || dots) {
      const separator = commas ? "," : ".";
      const chunks = numeric.split(separator);
      if (chunks.length > 2 || (chunks.length === 2 && chunks[1].length === 3 && !match[2])) {
        numeric = chunks.join("");
      } else {
        numeric = numeric.replace(separator, ".");
      }
    }
    const factor = { "":1, k:1000, m:1000000, b:1000000000 }[match[2]];
    const n = Number(numeric) * factor;
    return Number.isFinite(n) && n >= 0 && n <= 1e15 ? n : null;
  }

  function xpPairs(lines) {
    const unique = new Map();
    for (const raw of lines.slice(0, MAX_NODES)) {
      if (typeof raw !== "string" || raw.length > 130) continue;
      const line = raw.replace(/\s+/g, " ").trim();
      const match = line.match(XP_PREFIX) || line.match(XP_SUFFIX);
      if (!match) continue;
      const current = toNumber(match[1]);
      const maximum = match[2] === undefined ? null : toNumber(match[2]);
      if (current === null || (match[2] !== undefined &&
          (maximum === null || current > maximum))) continue;
      const id = String(current) + "/" + String(maximum);
      unique.set(id, {current, maximum});
    }
    return [...unique.values()];
  }

  function extractFromLines(lines) {
    const stats = {};
    for (const raw of lines.slice(0, MAX_NODES)) {
      if (typeof raw !== "string" || raw.length > 130) continue;
      const line = raw.replace(/\s+/g, " ").trim();
      for (const [key, pattern] of RULES) {
        if (key === "level" && stats.level != null) continue;
        if (key === "xp" && stats.xp_current != null) continue;
        if (key === "hp" && stats.hp_current != null) continue;
        if (stats[key] != null && key !== "xp" && key !== "hp") continue;
        const found = line.match(pattern);
        if (!found) continue;
        const primary = toNumber(found[1]);
        if (primary === null) continue;
        if (key === "xp" || key === "hp") {
          stats[key + "_current"] = primary;
          const maximum = found[2] ? toNumber(found[2]) : null;
          if (maximum !== null && maximum >= primary) stats[key + "_max"] = maximum;
        } else {
          stats[key] = primary;
        }
      }
    }
    // Nao escolha o primeiro XP do DOM: o IO mostrou simultaneamente
    // "7.346/15.400 xp" e "0/100 xp" em widgets diferentes.
    // Repeticoes DIV+SPAN identicas contam apenas como UM candidato.
    delete stats.xp_current;
    delete stats.xp_max;
    const xp = xpPairs(lines);
    if (xp.length === 1) {
      stats.xp_current = xp[0].current;
      if (xp[0].maximum !== null) stats.xp_max = xp[0].maximum;
    }
    return stats;
  }

  function collectLines(root) {
    if (!root || typeof root.querySelectorAll !== "function") return [];
    const lines = [];
    // Captura rótulos visíveis no DOM, mesmo quando a aba está em segundo plano.
    // Não analisa valores de campos de formulário nem dados privados da sessão.
    for (const node of root.querySelectorAll("span,div,p,b,strong,small,label,li")) {
      if (lines.length >= MAX_NODES) break;
      if (SKIP.test(node.tagName || "")) continue;
      if (node.closest && node.closest("form,dialog,[contenteditable],input,textarea,script,style,[class*='chat'],[id*='chat']")) continue;
      // HUDs frequentemente usam label em SPAN e valor em STRONG irmão:
      // o container pequeno junta "XP" e "100/300" sem enviar textos brutos.
      if (node.childElementCount > 4) continue;
      const text = node.textContent;
      if (typeof text === "string" && text.length > 1 && text.length <= 130 &&
          (/^\s*(?:[—–-]\s*)?(?:nv\.?|lvl\.?|lv\.?|n[ií]vel|level|xp|exp|experi[eê]ncia|hp|vida|health|coins?|ouro|gold|moedas?|gems?|gemas?)/i.test(text) ||
            XP_SUFFIX.test(text.replace(/\s+/g, " ").trim()))) {
        lines.push(text);
      }
    }
    return lines;
  }

  function readScopedTrainer(root) {
    // Observado no IO: barra do TREINADOR em .tr-dados; XP do Pokemon
    // ativo em .ativo-info. Nunca escolher por valor maior ou posicao DOM.
    if (!root || typeof root.querySelectorAll !== "function") {
      return {reading:null, reason:"trainer_panel_missing"};
    }
    const panels = root.querySelectorAll(".tr-dados");
    if (!panels.length) return {reading:null, reason:"trainer_panel_missing"};
    const results = new Map();
    let missingLevel = false;
    let missingXp = false;
    let ambiguous = false;
    for (const panel of panels) {
      const lines = collectLines(panel);
      const stats = extractFromLines(lines);
      // Exigir nivel e barra completos dentro do mesmo quadro do treinador.
      if (stats.level == null) { missingLevel = true; continue; }
      if (stats.xp_current == null || stats.xp_max == null) {
        missingXp = true;
        if (xpPairs(lines).length > 1) ambiguous = true;
        continue;
      }
      // Nivel global pode estar vindo do Pokemon; o painel do treinador
      // tem prioridade, mas duas barras no mesmo painel permanecem invalidas.
      const id = [stats.level, stats.xp_current, stats.xp_max].join("/");
      results.set(id, {level:stats.level, current:stats.xp_current,
                       maximum:stats.xp_max});
    }
    if (results.size === 1) return {reading:[...results.values()][0], reason:"trainer_xp_scoped"};
    if (results.size > 1 || ambiguous) return {reading:null, reason:"trainer_xp_ambiguous"};
    if (missingLevel) return {reading:null, reason:"trainer_level_missing"};
    return {reading:null, reason:missingXp ? "trainer_xp_missing" : "trainer_xp_missing"};
  }

  function inspectDocument(root) {
    const lines = collectLines(root);
    const stats = extractFromLines(lines);
    const xpCandidates = xpPairs(lines).length;
    const scoped = readScopedTrainer(root);
    const trainer = scoped.reading;
    // Uma barra unica fora de .tr-dados pode pertencer ao Pokemon.
    // XP/h depende da experiencia do treinador, nunca de XP global solto.
    delete stats.xp_current;
    delete stats.xp_max;
    if (trainer) {
      stats.level = trainer.level;
      stats.xp_current = trainer.current;
      stats.xp_max = trainer.maximum;
    } else {
      // Um nível solto também pode ser do Pokémon. Sem o quadro do treinador
      // ele não representa uma medição segura da conta.
      delete stats.level;
    }
    return {stats, xpCandidates, trainerScoped: Boolean(trainer),
            xpReason:scoped.reason};
  }

  function scanDocument(root) {
    const report = inspectDocument(root);
    if (report.trainerScoped) return report.stats;
    // Mantém o helper de teste útil para métricas não-XP, mas nunca devolve
    // XP global: fora de .tr-dados pode ser a barra do Pokémon.
    const legacy = extractFromLines(collectLines(root));
    delete legacy.xp_current;
    delete legacy.xp_max;
    return legacy;
  }

  function diagnose(root, path) {
    const onApp = path === "/app" || path.startsWith("/app/");
    const report = onApp ? inspectDocument(root)
      : {stats:{},xpCandidates:0,trainerScoped:false,xpReason:"not_on_app"};
    const {stats,xpCandidates,trainerScoped,xpReason} = report;
    const count = selector => {
      try { return Math.min(99, root.querySelectorAll(selector).length); }
      catch (_err) { return 0; }
    };
    const status = !onApp ? (path === "/" ? "landing" : "other_route")
      : Object.keys(stats).length ? "metrics" : "no_matches";
    return {source:"dom", reader_version:DOM_READER_VERSION, stats, available:status==="metrics",
      diagnostic:{status,canvas:count("canvas"),iframes:count("iframe"),
        candidates:Math.min(3500,count("span,div,p,b,strong,small,label,li")),
        xp_candidates:Math.min(20,xpCandidates),
        xp_ambiguous:xpCandidates>1 && !trainerScoped,
        xp_trainer_scoped:trainerScoped,
        xp_reason:xpReason}};
  }

  // Referências independentes de launchers/Atlas do IO indicam os IDs abaixo.
  // São SOMENTE pistas para leitura; devem ser confirmadas na versão atual do
  // DOM antes de promover qualquer controle para execução.
  function controlSummary(root, selector, policy, nativeToggle=false) {
    let node = null;
    try { node = root.querySelector(selector); } catch (_err) {}
    const present = Boolean(node);
    const enabled = Boolean(node && node.disabled !== true &&
      node.getAttribute?.("aria-disabled") !== "true");
    const report = {selector, present, enabled, policy};
    if (nativeToggle) {
      report.toggle_state = node && typeof node.checked === "boolean"
        ? (node.checked ? "on" : "off") : "unknown";
    }
    return report;
  }

  function readMapState(root) {
    let modal = null, mapBox = null;
    try {
      modal = root.querySelector("#modal");
      mapBox = root.querySelector('#modal .modal-caixa[data-modal="mapa"]');
    } catch (_err) {}
    if (!modal) return "unknown";
    if (!mapBox) return "closed";
    const hidden = modal.hidden === true ||
      modal.classList?.contains("hidden") === true ||
      modal.getAttribute?.("aria-hidden") === "true" ||
      modal.style?.display === "none" ||
      mapBox.hidden === true ||
      mapBox.classList?.contains("hidden") === true;
    return hidden ? "closed" : "open";
  }

  // Somente contagens de elementos visíveis no corpo do menu Mapa;
  // não lê nomes, HTML, coordenadas, slugs nem emite qualquer clique.
  function readMapStructure(root, mapState) {
    // Uma captura real mostrou o modal oculto mas com marcadores montados.
    // Nunca contar DOM oculto como prova de hunts acessíveis.
    const empty = status => ({
      status, buttons:0, links:0, candidate_markers:0,
      rendered_regions:0, available_regions:0, rendered_markers:0,
      unlocked_markers:0, highlighted_markers:0
    });
    if (mapState !== "open") return empty("not_open");
    let body = null;
    try { body = root.querySelector("#modal-corpo"); } catch (_err) {}
    if (!body || typeof body.querySelectorAll !== "function") {
      return empty("body_missing");
    }
    const count = selector => {
      try { return Math.min(200, body.querySelectorAll(selector).length); }
      catch (_err) { return 0; }
    };
    return {status:"observed", buttons:count("button"),
      links:count("a[href]"),
      candidate_markers:count("[data-hunt], [data-hunt-id], [data-slug]"),
      // Todas as métricas representam somente o mapa FILTRADO no DOM.
      // Não ler atributos data-slug, textos ou links; não acionar elementos.
      rendered_regions:count(".mapa-areas button.mapa-area[data-regiao]"),
      available_regions:count(".mapa-areas button.mapa-area[data-regiao]:not(.mapa-area-travada)"),
      rendered_markers:count("#mapa-tela button.marcador[data-slug][data-travado]"),
      unlocked_markers:count('#mapa-tela button.marcador[data-slug][data-travado="0"]'),
      highlighted_markers:count("#mapa-tela button.marcador.on[data-slug]")
    };
  }

  // Os HUDs podem indicar o Pokémon do encontro, não o mapa/hunt.
  // Nome exibido é apenas contexto de encontro, NUNCA slug ou destino.
  function readHuntHint(root) {
    const find = selector => {
      let node = null;
      try { node = root.querySelector(selector); } catch (_err) {}
      if (!node || typeof node.textContent !== "string") return null;
      const raw = node.textContent.trim();
      if (raw.length > 100) return null;
      const match = raw.match(/^([\p{L}\p{N}][\p{L}\p{N} .'-]{0,47})\s*[·]\s*(?:nível|nivel|nv|level|lv)\s*(\d{1,5})\s*$/iu);
      if (!match) return null;
      const label = match[1].replace(/\s+/g, " ").trim();
      const level = Number(match[2]);
      if (!label || label.length > 48 || !Number.isInteger(level) || level < 1 || level > 10000) return null;
      return {label, level};
    };
    const hud = find("#hud-hunt"), eco = find("#eco-onde");
    if (!hud && !eco) return {status:"unavailable",label:null,level:null,source:"none"};
    if (hud && eco && (hud.label !== eco.label || hud.level !== eco.level)) {
      return {status:"ambiguous",label:null,level:null,source:"both"};
    }
    const item = hud || eco;
    return {status:hud && eco ? "matching_displays" : "single_display",
            label:item.label, level:item.level,
            source:hud && eco ? "both" : hud ? "hud" : "eco"};
  }

  // Estado visual de cena, NÃO confirmação de batalha/farm no servidor.
  // Derivado da estrutura estática vista no HTML real do Poke Idle IO.
  // Não lê texto, nomes, id de conta, dados de hunt ou atributos privados.
  function readSceneIndicator(root) {
    let stage = null, cure = null;
    try {
      stage = root.querySelector("#palco");
      cure = root.querySelector("#centro-curar");
    } catch (_err) { return "unknown"; }
    if (!stage || !stage.classList) return "unknown";
    const has = name => stage.classList.contains(name) === true;
    const cureVisible = !!(cure &&
      cure.hidden !== true &&
      cure.classList?.contains("hidden") !== true &&
      cure.getAttribute?.("aria-hidden") !== "true" &&
      cure.style?.display !== "none");
    const hunt = has("hunt-ativa");
    const center = has("centro-ativo") && cureVisible;
    if ((hunt && center) || (has("centro-ativo") && hunt)) return "conflict";
    if (center) return "center_scene";
    if (hunt && !cureVisible && !has("centro-ativo")) return "hunt_scene";
    return "unknown";
  }

  function readAutomationAudit(root, path) {
    const onApp = path === "/app" || path.startsWith("/app/");
    if (!onApp) return {route:"not_app", farm_state:"unknown",
                        map_state:"unknown", scene_indicator:"unknown", map_structure:readMapStructure(root,"unknown"),
                        hunt_hint:{status:"unavailable",label:null,level:null,source:"none"}, controls:{}};
    let panel = null;
    try { panel = root.querySelector("#eco-painel"); } catch (_err) {}
    const panelText = typeof panel?.textContent === "string" ? panel.textContent : "";
    const farming = /\bcaçando\b/i.test(panelText) ? "active" : "unknown";
    const mapState = readMapState(root);
    return {
      route:"app", farm_state:farming, scene_indicator:readSceneIndicator(root), map_state:mapState,
      map_structure:readMapStructure(root,mapState),
      hunt_hint:readHuntHint(root),
      controls:{
        trainer_panel:controlSummary(root,".tr-dados","read_only"),
        active_pokemon_panel:controlSummary(root,".ativo-info","read_only"),
        inventory:controlSummary(root,"#btn-bolsa","read_only"),
        surrender:controlSummary(root,"#eco-desistir","permanently_blocked"),
        hunt_map:controlSummary(root,'button[data-modal="mapa"]',"read_only"),
        map_dialog:controlSummary(root,'#modal .modal-caixa[data-modal="mapa"]',"read_only"),
        native_capture_until:controlSummary(root,"#auto-ball-captura","read_only",true),
        native_capture_repeat:controlSummary(root,"#auto-ball-sem-parar","read_only",true),
        native_revive:controlSummary(root,"#auto-revive","read_only",true),
        native_potion:controlSummary(root,"#auto-potion","read_only",true),
        native_return_hunt:controlSummary(root,"#auto-voltar-hunt","read_only",true)
      }
    };
  }

  if (typeof chrome !== "undefined" && chrome.runtime?.onMessage && typeof document !== "undefined") {
    chrome.runtime.onMessage.addListener((message, sender, respond) => {
      if (!message || message.type !== "IGA_READ_IO_DOM") return false;
      // Esta mensagem vem do service worker do próprio complemento.
      const path = typeof location === "undefined" ? "/" : location.pathname;
      respond(diagnose(document, path));
      return false;
    });
    chrome.runtime.onMessage.addListener((message, sender, respond) => {
      if (!message || message.type !== "IGA_READ_IO_AUTOMATION_AUDIT") return false;
      const path = typeof location === "undefined" ? "/" : location.pathname;
      respond(readAutomationAudit(document, path));
      return false;
    });
  }
  if (typeof module !== "undefined") module.exports = {DOM_READER_VERSION, toNumber, extractFromLines, scanDocument, diagnose, readAutomationAudit};
})();
