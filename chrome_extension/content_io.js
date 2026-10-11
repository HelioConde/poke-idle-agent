/* Adaptador DOM mínimo: lê somente métricas numéricas já desenhadas na aba IO.
   Nunca lê localStorage, inputs, cookies, chat, URLs de sessão nem executa ações.
   Chrome pode suspender DOM/JS de abas inativas; nesse caso não fabricamos dados. */
"use strict";
(function () {
  const MAX_NODES = 3500;
  const RULES = [
    ["level", /^(?:n[ií]vel|level|lv\.?)\s*[:=#-]?\s*(\d[\d.,\s]*[kmb]?)\s*$/i],
    ["xp", /^(?:xp|exp|experi[eê]ncia)\s*[:=-]?\s*(\d[\d.,\s]*[kmb]?)(?:\s*\/\s*(\d[\d.,\s]*[kmb]?))?\s*$/i],
    ["hp", /^(?:hp|vida|health)\s*[:=-]?\s*(\d[\d.,\s]*[kmb]?)(?:\s*\/\s*(\d[\d.,\s]*[kmb]?))?\s*$/i],
    ["coins", /^(?:coins?|ouro|gold|moedas?)\s*[:=-]?\s*(\d[\d.,\s]*[kmb]?)\s*$/i],
    ["gems", /^(?:gems?|gemas?)\s*[:=-]?\s*(\d[\d.,\s]*[kmb]?)\s*$/i]
  ];
  const SKIP = /^(?:SCRIPT|STYLE|TEXTAREA|INPUT|OPTION|SELECT|NOSCRIPT)$/;

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
    return stats;
  }

  function scanDocument(root) {
    if (!root || typeof root.querySelectorAll !== "function") return {};
    const lines = [];
    // Captura rótulos visíveis no DOM, mesmo quando a aba está em segundo plano.
    // Não analisa valores de campos de formulário nem dados privados da sessão.
    for (const node of root.querySelectorAll("span,div,p,b,strong,small,label,li")) {
      if (lines.length >= MAX_NODES) break;
      if (SKIP.test(node.tagName || "")) continue;
      if (node.closest && node.closest("form,dialog,[contenteditable],input,textarea,script,style,[class*='chat'],[id*='chat']")) continue;
      // Preferimos nós de texto simples; evitamos repetir o texto dos containers.
      if (node.childElementCount > 0) continue;
      const text = node.textContent;
      if (typeof text === "string" && text.length > 1 && text.length <= 130) lines.push(text);
    }
    return extractFromLines(lines);
  }

  if (typeof chrome !== "undefined" && chrome.runtime?.onMessage && typeof document !== "undefined") {
    chrome.runtime.onMessage.addListener((message, sender, respond) => {
      if (!message || message.type !== "IGA_READ_IO_DOM") return false;
      // Esta mensagem vem do service worker do próprio complemento.
      const stats = scanDocument(document);
      respond({source:"dom", stats, available: Object.keys(stats).length > 0});
      return false;
    });
  }
  if (typeof module !== "undefined") module.exports = {toNumber, extractFromLines, scanDocument};
})();
