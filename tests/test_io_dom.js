const assert = require("node:assert/strict");
const {toNumber, extractFromLines, scanDocument, diagnose} = require("../chrome_extension/content_io.js");

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
 source:"dom",stats:{},available:false,
 diagnostic:{status:"no_matches",canvas:2,iframes:1,candidates:0,
   xp_candidates:0,xp_ambiguous:false,xp_trainer_scoped:false}
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
 source:"dom",stats:{level:19},available:true,
 diagnostic:{status:"metrics",canvas:9,iframes:0,candidates:4,
   xp_candidates:2,xp_ambiguous:true,xp_trainer_scoped:false}
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
  source:"dom",available:true,
  stats:{level:19,xp_current:7346,xp_max:15400},
  diagnostic:{status:"metrics",canvas:9,iframes:0,candidates:5,
    xp_candidates:2,xp_ambiguous:false,xp_trainer_scoped:true}
});

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
