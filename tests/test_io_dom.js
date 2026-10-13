const assert = require("node:assert/strict");
const {toNumber, extractFromLines, scanDocument, diagnose, readAutomationAudit} = require("../chrome_extension/content_io.js");

assert.equal(toNumber("1.234"), 1234);
assert.equal(toNumber("1.234,5"), 1234.5);
assert.equal(toNumber("1,5k"), 1500);
assert.equal(toNumber("3.2M"), 3200000);
assert.equal(toNumber("invalid"), null);
assert.deepEqual(extractFromLines([
  "Nível 44", "XP: 1.234 / 2.000", "Coins: 100.000",
  "Gemas: 12", "HP: 25 / 100", "password: 123", "email: abc"
]),{level:44,xp_current:1234,xp_max:2000,hp_current:25,hp_max:100,coins:100000,gems:12});
const fakeDoc = {querySelectorAll(){return [
 {tagName:"DIV",childElementCount:0,textContent:"XP 20 / 100",closest(){return null;}},
 {tagName:"DIV",childElementCount:0,textContent:"Password: abc",closest(){return null;}}
];}};
assert.deepEqual(scanDocument(fakeDoc), {}); // Sem .tr-dados, pode ser XP do Pokemon
const publicHud = {querySelectorAll(){return [
  {tagName:"DIV",childElementCount:0,textContent:"— Nv 1",closest(){return null;}},
  {tagName:"INPUT",childElementCount:0,textContent:"senha secret",closest(){return null;}}
];}};
assert.deepEqual(scanDocument(publicHud), {level:1});
assert.deepEqual(extractFromLines(["Nv 44", "Coins1000", "Gems 10"]), {
  level:44, coins:1000, gems:10
});
const nested = {querySelectorAll(){return [
  {tagName:"DIV",childElementCount:2,textContent:"XP100 / 300",closest(){return null;}},
  {tagName:"DIV",childElementCount:2,textContent:"HP50 / 100",closest(){return null;}},
  {tagName:"DIV",childElementCount:2,textContent:"CPF 123.456",closest(){return null;}}
];}};
assert.deepEqual(scanDocument(nested), {
  hp_current:50, hp_max:100 // XP fora do painel do treinador não é confiável
});
assert.deepEqual(scanDocument({querySelectorAll(){return [];}}), {});
console.log("IO DOM: parser numerico e exclusao de credenciais OK");

assert.deepEqual(extractFromLines(["— Nv 40"]), {level:40});
const blankDoc={querySelectorAll(selector){
  if(selector==="canvas")return [{},{}];
  if(selector==="iframe")return [{}];
  return [];
}};
assert.deepEqual(diagnose(blankDoc,"/app"),{
 source:"dom",reader_version:"trainer-xp-scoped-v1",stats:{},available:false,
 diagnostic:{status:"no_matches",canvas:2,iframes:1,candidates:0,
   xp_candidates:0,xp_ambiguous:false,xp_trainer_scoped:false,
   xp_reason:"trainer_panel_missing"}
});
assert.equal(diagnose(blankDoc,"/").diagnostic.status,"landing");
assert.equal(diagnose(blankDoc,"/news").diagnostic.status,"other_route");


// O DOM do jogo pode conter DIV e SPAN duplicando uma mesma barra.
assert.deepEqual(extractFromLines([
  "7.346 / 15.400 xp", "7.346 / 15.400 xp", "Nível 19",
  "+15% XP", "XP+0%"
]),{level:19,xp_current:7346,xp_max:15400});

// Valores de XP DIFERENTES nunca podem ser escolhidos por ordem ou maior valor.
assert.deepEqual(extractFromLines([
  "Nível 19", "7.346 / 15.400 xp", "0 / 100 xp", "+10% XP"
]),{level:19});
assert.deepEqual(extractFromLines([
  "0 / 100 xp", "7.346 / 15.400 xp", "Nível 19"
]),{level:19});
// Não confundir bônus, percentuais e strings incoerentes com XP.
assert.deepEqual(extractFromLines(["+15% XP","XP+0%"]),{});
assert.deepEqual(extractFromLines(["120 / 100 xp"]),{});
assert.deepEqual(extractFromLines(["XP: 9.001 / 10.000"]),
 {xp_current:9001,xp_max:10000});

const doubleXP={querySelectorAll(selector){
 if(selector==="canvas")return Array(9).fill({});
 if(selector==="iframe")return [];
 return [
  {tagName:"SPAN",childElementCount:0,textContent:"7.346 / 15.400 xp",closest(){return null;}},
  {tagName:"DIV",childElementCount:2,textContent:"7.346 / 15.400 xp",closest(){return null;}},
  {tagName:"SPAN",childElementCount:0,textContent:"0 / 100 xp",closest(){return null;}},
  {tagName:"SPAN",childElementCount:0,textContent:"Nível 19",closest(){return null;}}
 ];
}};
assert.deepEqual(diagnose(doubleXP,"/app"),{
 source:"dom",reader_version:"trainer-xp-scoped-v1",stats:{},available:false,
 diagnostic:{status:"no_matches",canvas:9,iframes:0,candidates:4,
   xp_candidates:2,xp_ambiguous:true,xp_trainer_scoped:false,
   xp_reason:"trainer_level_missing"}
});
console.log("IO XP: formato sufixo identificado e barras concorrentes bloqueadas");


// Cenário observado na conta real: XP treinador AlchemyFlames Nv 19 em
// .tr-dados, XP do Pokémon Oddish Nv 1 em .ativo-info. Dados aqui são fixos.
function sampleNode(txt, tag="SPAN", child=0) {
  return {tagName:tag, childElementCount:child, textContent:txt,
    closest(){return null;}};
}
const trainerPanel = {
  querySelectorAll(selector) {
    if (selector.includes("span,div,p")) return [
      sampleNode("Alguém", "DIV"), sampleNode("Nv 19"),
      sampleNode("7.346 / 15.400 xp"), sampleNode("7.346 / 15.400 xp","DIV",2),
      sampleNode("+15% XP")
    ];
    return [];
  }
};
const scopedHud = {
  querySelectorAll(selector) {
    if(selector===".tr-dados") return [trainerPanel];
    if(selector==="canvas")return Array(9).fill({});
    if(selector==="iframe")return [];
    return [sampleNode("Nv 19"),sampleNode("7.346 / 15.400 xp"),
      sampleNode("0 / 100 xp"),sampleNode("Nv 1"),sampleNode("+15% XP")];
  }
};
assert.deepEqual(scanDocument(scopedHud),
  {level:19,xp_current:7346,xp_max:15400});
assert.deepEqual(diagnose(scopedHud,"/app"),{
  source:"dom",reader_version:"trainer-xp-scoped-v1",available:true,
  stats:{level:19,xp_current:7346,xp_max:15400},
  diagnostic:{status:"metrics",canvas:9,iframes:0,candidates:5,
    xp_candidates:2,xp_ambiguous:false,xp_trainer_scoped:true,
    xp_reason:"trainer_xp_scoped"}
});

// O HUD é atualizado sem recarregar a página. A barra ativa do Pokémon pode
// mudar entre leituras, mas a telemetria deve continuar vindo somente do
// quadro .tr-dados do treinador.
let trainerXp = "7.346 / 15.400 xp";
let pokemonXp = "0 / 100 xp";
const dynamicPanel = {querySelectorAll(selector) {
  if (selector.includes("span,div,p")) return [sampleNode("Nv 19"),
    sampleNode(trainerXp), sampleNode(trainerXp, "DIV", 2)];
  return [];
}};
const dynamicHud = {querySelectorAll(selector) {
  if (selector === ".tr-dados") return [dynamicPanel];
  if (selector === "canvas" || selector === "iframe") return [];
  return [sampleNode("Nv 19"), sampleNode(trainerXp),
    sampleNode("Oddish Nv 1"), sampleNode(pokemonXp)];
}};
assert.equal(diagnose(dynamicHud,"/app").stats.xp_current,7346);
pokemonXp = "99 / 100 xp";
assert.equal(diagnose(dynamicHud,"/app").stats.xp_current,7346);
trainerXp = "7.500 / 15.400 xp";
assert.equal(diagnose(dynamicHud,"/app").stats.xp_current,7500);

// Proteção: se o quadro do treinador contiver 2 progressões diferentes,
// nem escolher pelo maior XP nem herdar o XP do Pokemon.
const uncertainPanel = {
  querySelectorAll(selector) {
    if (selector.includes("span,div,p")) return [
      sampleNode("Nv 19"), sampleNode("7.346 / 15.400 xp"),
      sampleNode("400 / 1.000 xp")
    ];
    return [];
  }
};
const uncertainHud = {...scopedHud,
 querySelectorAll(selector) {
    if(selector===".tr-dados") return [uncertainPanel];
    return scopedHud.querySelectorAll(selector);
 }};
assert.deepEqual(scanDocument(uncertainHud), {level:19});
assert.equal(diagnose(uncertainHud,"/app").diagnostic.xp_ambiguous,true);
console.log("IO DOM: XP treinador separado de XP Pokemon por tr-dados");

const auditDoc={querySelector(selector){
  if(selector==="#eco-painel") return {textContent:"SESSÃO caçando"};
  if(selector===".tr-dados" || selector==="#btn-bolsa" || selector==="#eco-desistir") return {disabled:false};
  return null;
}};
const audit=readAutomationAudit(auditDoc,"/app");
assert.equal(audit.route,"app");
assert.equal(audit.farm_state,"active");
assert.deepEqual(audit.controls.surrender,{selector:"#eco-desistir",present:true,enabled:true,policy:"permanently_blocked"});
assert.deepEqual(audit.controls.hunt_map,{selector:'button[data-modal="mapa"]',present:false,enabled:false,policy:"read_only"});
console.log("IO DOM: auditoria somente leitura e Desistir bloqueado");

assert.deepEqual(audit.hunt_hint,{status:"unavailable",label:null,level:null,source:"none"});
assert.deepEqual(audit.map_structure,{status:"not_open",buttons:0,links:0,candidate_markers:0});
assert.equal(audit.map_state,"unknown");
assert.equal(audit.controls.native_revive.toggle_state,"unknown");

// Estrutura do modal Mapa observada em referências externas do MESMO jogo.
// Nunca interagir com os botões; aqui somente verificamos presença e estados.
function makeMapDoc({hidden=false,mapButton=true,modalBox=true}={}) {
  const nodes={
    "#eco-painel":{textContent:"caçando"},
    ".tr-dados":{disabled:false},
    "#eco-desistir":{disabled:false},
    "#modal":{hidden:false,classList:{contains(name){return hidden&&name==="hidden";}}},
    "#auto-revive":{checked:true,disabled:false},
    "#auto-potion":{checked:false,disabled:false},
    "#auto-ball-captura":{checked:true,disabled:false},
    "#auto-ball-sem-parar":{checked:false,disabled:false},
    "#auto-voltar-hunt":{disabled:false}
  };
  if(mapButton)nodes['button[data-modal="mapa"]']={disabled:false};
  if(modalBox)nodes['#modal .modal-caixa[data-modal="mapa"]']={disabled:false};
  return {querySelector(selector){return nodes[selector]||null;}};
}
const openMap=readAutomationAudit(makeMapDoc(),"/app");
assert.deepEqual(openMap.map_structure,{status:"body_missing",buttons:0,links:0,candidate_markers:0});
assert.equal(openMap.map_state,"open");
assert.equal(openMap.controls.hunt_map.present,true);
assert.equal(openMap.controls.map_dialog.present,true);
assert.equal(openMap.controls.native_revive.toggle_state,"on");
assert.equal(openMap.controls.native_potion.toggle_state,"off");
assert.equal(openMap.controls.native_return_hunt.toggle_state,"unknown");
assert.equal(openMap.controls.surrender.policy,"permanently_blocked");
const closedMap=readAutomationAudit(makeMapDoc({hidden:true}),"/app");
assert.equal(closedMap.map_state,"closed");
assert.equal(closedMap.map_structure.status,"not_open");
assert.equal(readAutomationAudit(makeMapDoc({modalBox:false}),"/app").map_state,"closed");
assert.equal(readAutomationAudit(makeMapDoc({mapButton:false}),"/app").controls.hunt_map.present,false);
assert.deepEqual(readAutomationAudit(makeMapDoc(),"/login"),{
  route:"not_app",farm_state:"unknown",map_state:"unknown",
  map_structure:{status:"not_open",buttons:0,links:0,candidate_markers:0},
  hunt_hint:{status:"unavailable",label:null,level:null,source:"none"},controls:{}
});
console.log("IO DOM: mapa e automacoes nativas detectados somente em leitura");


// O indicador do local é apenas pista, jamais slug ou identidade de conta.
// As amostras são fixtures locais, não leitura do jogo real.
function hintDoc(hud,eco){
  return {querySelector(selector){
    if(selector==="#hud-hunt")return hud===null?null:{textContent:hud};
    if(selector==="#eco-onde")return eco===null?null:{textContent:eco};
    return null;
  }};
}
assert.deepEqual(readAutomationAudit(hintDoc("Larvitar · nível 30","Larvitar · nível 30"),"/app").hunt_hint,
  {status:"matching_displays",label:"Larvitar",level:30,source:"both"});
assert.deepEqual(readAutomationAudit(hintDoc("Larvitar · nível 30",null),"/app").hunt_hint,
  {status:"single_display",label:"Larvitar",level:30,source:"hud"});
assert.deepEqual(readAutomationAudit(hintDoc(null,"Oddish · Lv 15"),"/app").hunt_hint,
  {status:"single_display",label:"Oddish",level:15,source:"eco"});
assert.deepEqual(readAutomationAudit(hintDoc("Larvitar · nível 30","Oddish · nível 30"),"/app").hunt_hint,
  {status:"ambiguous",label:null,level:null,source:"both"});
assert.deepEqual(readAutomationAudit(hintDoc("<script> · nível 20",null),"/app").hunt_hint,
  {status:"unavailable",label:null,level:null,source:"none"});
assert.deepEqual(readAutomationAudit(hintDoc("trainer@email.com · nível 20",null),"/app").hunt_hint,
  {status:"unavailable",label:null,level:null,source:"none"});
assert.deepEqual(readAutomationAudit(hintDoc("Larvitar · nível 30",null),"/not-app").hunt_hint,
  {status:"unavailable",label:null,level:null,source:"none"});
console.log("IO DOM: HUD de hunt observado como pista, sem ID nem autorizacao");


// Com mapa ABERTO, somente conta categorias fixas; não percorre texto,
// dados privados, links ou nomes. Mapa fechado nem consulta o corpo.
let reads = 0;
const mapTestDoc = {
  querySelector(selector) {
    if(selector === "#modal")return {hidden:false,classList:{contains(){return false;}}};
    if(selector === '#modal .modal-caixa[data-modal="mapa"]')return {disabled:false};
    if(selector === "#modal-corpo")return {querySelectorAll(kind){
      reads++;
      return Array(kind==="button"?7:kind==="a[href]"?3:2).fill({});
    }};
    return null;
  }
};
const mapRead=readAutomationAudit(mapTestDoc,"/app");
assert.deepEqual(mapRead.map_structure,
  {status:"observed",buttons:7,links:3,candidate_markers:2});
assert.equal(reads,3);
assert.equal(mapRead.controls.surrender.policy,"permanently_blocked");
const hiddenDoc={...mapTestDoc,querySelector(selector){
  if(selector==="#modal")return {hidden:true,classList:{contains(){return false;}}};
  return mapTestDoc.querySelector(selector);
}};
assert.equal(readAutomationAudit(hiddenDoc,"/app").map_structure.status,"not_open");
assert.equal(reads,3);
console.log("IO DOM: mapa aberto reporta somente contagens fechadas");
