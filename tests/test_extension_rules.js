const assert = require("node:assert/strict");
const {TELEMETRY_PROTOCOL_VERSION, DOM_READER_VERSION, classifyGame, safeTab, routeOfIo} = require("../chrome_extension/background.js");

assert.equal(TELEMETRY_PROTOCOL_VERSION, 2);
assert.equal(DOM_READER_VERSION, "trainer-xp-scoped-v1");

assert.equal(classifyGame("https://pokeidle.io/play?auth=hidden"), "io");
assert.equal(classifyGame("https://www.pokeidle.io/"), "io");
assert.equal(classifyGame("https://poke.idleworld.online/play"), "world");
assert.equal(classifyGame("https://evil.example/?q=pokeidle.io"), null);
assert.equal(classifyGame("https://pokeidle.io.evil.example/"), null);
assert.equal(classifyGame("http://pokeidle.io/"), null);
assert.equal(safeTab({url:"https://pokeidle.io/play",id:2,windowId:4,title:"Pokéidle",active:false}).active,false);
assert.equal(safeTab({url:"https://pokeidle.io/play",id:2,windowId:4,title:"Pokéidle",active:false}).title,"Pokéidle");
assert.equal(safeTab({url:"https://google.com",id:3,windowId:4}), null);
console.log("Regras da extensao aprovadas.");

assert.equal(routeOfIo("https://pokeidle.io/app"),"app");
assert.equal(routeOfIo("https://pokeidle.io/app#map"),"app");
assert.equal(routeOfIo("https://pokeidle.io/"),"landing");
assert.equal(routeOfIo("https://pokeidle.io/other"),"other");
assert.equal(safeTab({url:"https://pokeidle.io/app",id:7,windowId:3,title:"Pokeidle",active:false}).route,"app");
