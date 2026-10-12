#!/usr/bin/env node
'use strict';
// IVs e projeções PokeGrid (MIT). Somente cálculo local: nenhum login,
// extensão, request HTTP, script injetado ou ação no Poke Idle World.
const fs = require('node:fs');
const path = require('node:path');
const {projectPokemon, STAT_KEYS} = require('../vendor/pokegrid/iv-math.js');

const ROOT = path.resolve(__dirname, '..');
const MAX_FILE_BYTES = 1024 * 1024;
const MAX_POKEMON = 40;
function integer(value, label, min, max) {
  if (!Number.isInteger(value) || value < min || value > max) {
    throw new Error(label + ': inteiro fora do intervalo');
  }
  return value;
}
function str(value, label) {
  if (typeof value !== 'string' || !value.trim() || value.length > 64 ||
      /[\x00-\x1f]/.test(value) || value.includes('@')) {
    throw new Error(label + ': use apelido local de até 64 caracteres');
  }
  return value.trim();
}
function safeLocalFile(name) {
  if (typeof name !== 'string') throw new Error('Informe o JSON manual');
  const absolute = path.resolve(ROOT, name);
  if (!(absolute.startsWith(path.join(ROOT,'data')+path.sep) ||
        absolute.startsWith(path.join(ROOT,'examples')+path.sep)) ||
      path.extname(absolute).toLowerCase() !== '.json') {
    throw new Error('Leia somente JSON dentro de data/ ou examples/; nunca arquivos de conta');
  }
  const stat = fs.statSync(absolute);
  if (!stat.isFile() || stat.size > MAX_FILE_BYTES) throw new Error('JSON inválido ou muito grande');
  return absolute;
}
function validatePokemon(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Pokémon inválido');
  const allowed = new Set(['id','name','level','quality','ivs','ivTotal','power','species','observedStats']);
  if (Object.keys(input).some(key => !allowed.has(key))) throw new Error('Campo sensível ou desconhecido em Pokémon');
  str(input.id,'pokemon.id');
  str(input.name,'pokemon.name');
  integer(input.level,'pokemon.level',1,3000);
  if (!Number.isFinite(input.quality) || input.quality <= 0 || input.quality > 100) throw new Error('Qualidade inválida');
  if (!input.species || typeof input.species !== 'object' || Array.isArray(input.species) ||
      Object.keys(input.species).some(k=>k!=='baseStats')) throw new Error('species.baseStats obrigatório');
  const b = input.species.baseStats;
  if (!b || typeof b !== 'object' || Array.isArray(b) || Object.keys(b).length !== 6 ||
      STAT_KEYS.some(k => !Number.isFinite(b[k]) || b[k] < 1 || b[k] > 2000)) {
    throw new Error('Seis baseStats numéricos obrigatórios, fornecidos manualmente');
  }
  if (input.ivs != null) {
    if (typeof input.ivs !== 'object' || Array.isArray(input.ivs) ||
        Object.keys(input.ivs).length !== 6 ||
        STAT_KEYS.some(k => !Number.isInteger(input.ivs[k]) || input.ivs[k] < 1 || input.ivs[k] > 32))
        throw new Error('ivs: seis atributos inteiros entre 1 e 32');
  }
  if (input.observedStats != null) {
    if (typeof input.observedStats !== 'object' || Array.isArray(input.observedStats) ||
        Object.keys(input.observedStats).length !== 6 ||
        STAT_KEYS.some(k => !Number.isFinite(input.observedStats[k]) || input.observedStats[k] <= 0))
        throw new Error('observedStats inválidos');
  }
  if (input.ivTotal != null) integer(input.ivTotal,'ivTotal',6,192);
  if (input.power != null && (!Number.isFinite(input.power) || input.power < 1)) {
    throw new Error('power inválido');
  }
}
function evaluate(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload) ||
      Object.keys(payload).some(k=>!['game','source','profile_id','account_id','pokemon','levels'].includes(k)))
      throw new Error('JSON inválido / campos não permitidos');
  if (payload.game !== 'world') throw new Error('IV deste adaptador é específico do Poke Idle World');
  if (!['manual','demo'].includes(payload.source)) throw new Error('Origem manual ou demo exigida');
  const profile = str(payload.profile_id,'profile_id'), account = str(payload.account_id,'account_id');
  if (!Array.isArray(payload.levels) || !payload.levels.length || payload.levels.length > 6) throw new Error('levels: 1 a 6');
  for (const lvl of payload.levels) integer(lvl,'level',1,3000);
  if (!Array.isArray(payload.pokemon) || !payload.pokemon.length || payload.pokemon.length > MAX_POKEMON) {
    throw new Error('Informe de 1 a 40 Pokémon');
  }
  const ids = new Set();
  const results = payload.pokemon.map(p => {
    validatePokemon(p);
    if (ids.has(p.id)) throw new Error('Pokémon duplicado'); ids.add(p.id);
    const projections = payload.levels.map(level => {
      const value = projectPokemon(p, level);
      return {level, stats:value.stats, power:value.power, iv_source:value.ivSource,
              iv_exact:value.ivExact, iv_ranges:value.ivRanges};
    });
    return {id:p.id, name:p.name, current_level:p.level, projections};
  });
  return {game:'world',mode:'manual_offline',source:payload.source,
          profile_id:profile,account_id:account,
          derived_from:'PokeGrid-source MIT',pokemon:results,
          note:'Projeções matemáticas locais, não são leituras/garantias do jogo. Não acessa contas, não representa renda real.'};
}
function main() {
  if (process.argv.length !== 3) {
    process.stderr.write('Uso: node tools/pokegrid_iv_cli.js data/meus_ivs.json\n');
    process.exitCode = 2; return;
  }
  try {
    const input = JSON.parse(fs.readFileSync(safeLocalFile(process.argv[2]),'utf8'));
    process.stdout.write(JSON.stringify(evaluate(input),null,2)+'\n');
  } catch(error) {
    process.stderr.write('Erro no relatório manual: '+error.message+'\n');
    process.exitCode = 1;
  }
}
if(require.main===module) main();
module.exports={evaluate,validatePokemon,safeLocalFile};
