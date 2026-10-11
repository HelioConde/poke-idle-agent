"use strict";
const $ = id => document.getElementById(id);
function classify(address) {
  try {
    const { protocol, hostname } = new URL(address);
    if (protocol !== "https:") return null;
    if (["pokeidle.io", "www.pokeidle.io"].includes(hostname)) return "io";
    return hostname === "poke.idleworld.online" ? "world" : null;
  } catch (_error) { return null; }
}
async function refresh() {
  const state = await chrome.storage.local.get([
    "profile_label", "pairing_token", "last_count", "last_error", "last_sync"
  ]);
  $("profile").value = state.profile_label || "";
  $("token").value = state.pairing_token || "";
  const tabs = (await chrome.tabs.query({})).filter(t => classify(t.url || t.pendingUrl));
  $("status").textContent = state.last_error
    ? "Monitor: " + state.last_error
    : String(tabs.length) + " aba(s) encontrada(s). " +
      (state.last_sync ? "Sincronizado." : "Aguardando conexão.");
  const ul = $("tab-list"); ul.replaceChildren();
  tabs.forEach(tab => {
    const item = document.createElement("li");
    const name = classify(tab.url || tab.pendingUrl) === "io" ? "IO" : "World";
    item.textContent = name + ": " + String(tab.title || "Aba sem título").slice(0, 100) +
      " — " + (tab.active ? "selecionada" : "inativa");
    ul.appendChild(item);
  });
}
$("save").addEventListener("click", async () => {
  const profile_label = $("profile").value.trim().slice(0, 48) || "Perfil Chrome";
  const pairing_token = $("token").value.trim();
  if (pairing_token.length < 32 || pairing_token.length > 128) {
    $("status").textContent = "A chave deve ser copiada do monitor local.";
    return;
  }
  await chrome.storage.local.set({ profile_label, pairing_token });
  $("status").textContent = "Sincronizando...";
  await chrome.runtime.sendMessage({ type: "SYNC_TABS" });
  await refresh();
});
refresh().catch(error => { $("status").textContent = String(error); });
