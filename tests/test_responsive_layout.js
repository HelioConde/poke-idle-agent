"use strict";

/* Regressão do overflow observado na captura real de 390 px. */
const assert = require("assert");
const fs = require("fs");
const css = fs.readFileSync("public/styles.css", "utf8");

assert.match(css, /html,body\{width:100%;max-width:100%\}/);
assert.match(css, /@media\(max-width:750px\)\{[\s\S]*?\.nav\{flex-wrap:wrap;justify-content:flex-start\}/);
assert.match(css, /\.privacy\{max-width:100%;overflow-wrap:anywhere\}/);
assert.match(css, /\.shell\{width:100%;max-width:1200px/);
assert.match(css, /\.world-results\{[^}]*min-width:0;max-width:100%\}/);
assert.match(css, /main,section,\.lead,\.banner,\.muted,\.state,h1,h2,h3,\.world-results,\.unified-toolbar\{width:100%;min-width:0\}/);
assert.match(css, /\.banner,\.muted,\.state,h1,h2,h3\{max-width:100%;overflow-wrap:anywhere\}/);
console.log("Layout responsivo: proteção contra overflow móvel aprovada.");
