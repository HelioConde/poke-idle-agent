/* Detecta abas pelos endereços autorizados, sem ler conteúdo do jogo. */
"use strict";
const ENDPOINT = "http://127.0.0.1:8768/api/sync";

function classifyGame(address) {
  if (typeof address !== "string") return null;
  try {
    const url = new URL(address);
    if (url.protocol !== "https:") return null;
    if (url.hostname === "pokeidle.io" || url.hostname === "www.pokeidle.io") return "io";
    if (url.hostname === "poke.idleworld.online") return "world";
  } catch (_err) {}
  return null;
}


function routeOfIo(address) {
  try {
    const path = new URL(address).pathname;
    if (path === "/app" || path.startsWith("/app/")) return "app";
    if (path === "/") return "landing";
  } catch (_error) {}
  return "other";
}

function safeTab(tab) {
  const game = classifyGame(tab.url || tab.pendingUrl);
  if (!game || !Number.isInteger(tab.id) || !Number.isInteger(tab.windowId)) return null;
  return {
    game, tab_id: tab.id, window_id: tab.windowId,
    ...(game==="io" ? {route:routeOfIo(tab.url || tab.pendingUrl)} : {}),
    title: (typeof tab.title === "string" ? tab.title : game === "io" ? "Poke Idle IO" : "Poke Idle World").slice(0, 120),
    active: tab.active === true
  };
}

async function readProfile() {
  let state = await chrome.storage.local.get(["profile_id", "profile_label", "pairing_token"]);
  if (!state.profile_id) {
    state.profile_id = crypto.randomUUID();
    await chrome.storage.local.set({ profile_id: state.profile_id });
  }
  return state;
}
// Captura por DOM somente em abas IO. O jogo World continua metadados-only.
async function observeTab(tab) {
  const item = safeTab(tab);
  if (!item || item.game !== "io") return item;
  const empty = {canvas:0,iframes:0,candidates:0};
  if (item.route !== "app") {
    item.observation = {...empty,status:item.route==="landing"?"landing":"other_route"};
    return item;
  }
  item.observation = {...empty,status:"reader_unavailable"};
  try {
    const reading = await chrome.tabs.sendMessage(tab.id, {type:"IGA_READ_IO_DOM"});
    if (reading && reading.source === "dom" && reading.stats &&
        typeof reading.stats === "object" && !Array.isArray(reading.stats)) {
      item.telemetry = {source:"dom",stats:reading.stats};
      const d=reading.diagnostic||{};
      const bounded = (n, max)=>Number.isInteger(n)?Math.max(0,Math.min(max,n)):0;
      item.observation = {
        status:reading.available?"metrics":"no_matches",
        canvas:bounded(d.canvas,99),iframes:bounded(d.iframes,99),
        candidates:bounded(d.candidates,3500),
        xp_candidates:bounded(d.xp_candidates,20),
        xp_ambiguous:d.xp_ambiguous===true,
        xp_trainer_scoped:d.xp_trainer_scoped===true
      };
    }
  } catch (_ignored) {
    // Script nao injetado, aba suspensa, nao ha leitura confiavel.
  }
  return item;
}

let inFlight = null;
async function performScan() {
  const state = await readProfile();
  // Abas de outros sites nao expoem URL/titulo devido as permissoes restritas.
  const found = await chrome.tabs.query({});
  const tabs = (await Promise.all(found.slice(0, 80).map(observeTab))).filter(Boolean).slice(0, 40);
  const result = { tabs, count: tabs.length, paired: Boolean(state.pairing_token) };
  if (!state.pairing_token) {
    await chrome.storage.local.set({
      last_count: tabs.length, last_error: "Cole a chave do monitor no popup.", last_sync: 0
    });
    return result;
  }
  try {
    const response = await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-IGA-Token": state.pairing_token },
      body: JSON.stringify({
        profile_id: state.profile_id,
        profile_label: (state.profile_label || "Perfil Chrome").slice(0, 48),
        tabs
      })
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    await chrome.storage.local.set({
      last_count: tabs.length, last_sync: Date.now(), last_error: ""
    });
    return result;
  } catch (error) {
    await chrome.storage.local.set({
      last_count: tabs.length, last_error: String(error.message || error).slice(0, 120)
    });
    return { ...result, error: String(error.message || error) };
  }
}
function syncTabs() {
  if (!inFlight) inFlight = performScan().finally(() => { inFlight = null; });
  return inFlight;
}
function installHandlers() {
  const ensureAlarm = () => chrome.alarms.create("tab-sync", { periodInMinutes: 0.5 });
  chrome.runtime.onInstalled.addListener(() => { ensureAlarm(); syncTabs(); });
  chrome.runtime.onStartup.addListener(() => { ensureAlarm(); syncTabs(); });
  chrome.alarms.onAlarm.addListener(alarm => {
    if (alarm.name === "tab-sync") syncTabs();
  });
  chrome.tabs.onUpdated.addListener(() => { syncTabs(); });
  chrome.tabs.onActivated.addListener(() => { syncTabs(); });
  chrome.tabs.onRemoved.addListener(() => { syncTabs(); });
  chrome.tabs.onCreated.addListener(() => { syncTabs(); });
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type !== "SYNC_TABS") return false;
    syncTabs().then(sendResponse).catch(error => sendResponse({
      count: 0, error: String(error.message || error)
    }));
    return true;
  });
  ensureAlarm();
  syncTabs();
}
if (typeof chrome !== "undefined" && chrome.runtime?.id) installHandlers();
if (typeof module !== "undefined") module.exports = { classifyGame, safeTab, routeOfIo };
