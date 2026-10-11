const assert = require("node:assert/strict");
const {classifyGame, safeTab} = require("../chrome_extension/background.js");

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
