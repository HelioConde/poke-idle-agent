const assert = require("node:assert/strict");
const {toNumber, extractFromLines, scanDocument} = require("../chrome_extension/content_io.js");

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
assert.deepEqual(scanDocument(fakeDoc), {xp_current:20,xp_max:100});
assert.deepEqual(extractFromLines(["Nv 44", "Coins1000", "Gems 10"]), {
  level:44, coins:1000, gems:10
});
const nested = {querySelectorAll(){return [
  {tagName:"DIV",childElementCount:2,textContent:"XP100 / 300",closest(){return null;}},
  {tagName:"DIV",childElementCount:2,textContent:"HP50 / 100",closest(){return null;}},
  {tagName:"DIV",childElementCount:2,textContent:"CPF 123.456",closest(){return null;}}
];}};
assert.deepEqual(scanDocument(nested), {
  xp_current:100, xp_max:300, hp_current:50, hp_max:100
});
assert.deepEqual(scanDocument({querySelectorAll(){return [];}}), {});
console.log("IO DOM: parser numerico e exclusao de credenciais OK");
