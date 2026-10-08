import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseTargetV0Yaml, projectTargetV0, TARGET_V0_SHA256} from './target_v0_source.mjs';

const bytes=readFileSync('../../docs/portfolio_target_owner/TARGET_v0.yaml');
const text=bytes.toString('utf8');
const map=JSON.parse(readFileSync('../../docs/security_map19_owner/TARGET_v0_SECURITY_MAP.json','utf8'));
const project=(b=bytes,m=map)=>projectTargetV0(b,m,{observed_at:'2026-10-08T12:00:00Z'});

test('user YAML parses quoted listing commas without losing labels, units or current clocks',()=>{
 const d=parseTargetV0Yaml(text);
 assert.equal(d.owner.role,'USER');assert.equal(d.status,'ADOPTED');assert.equal(d.version,'v0');
 assert.equal(d.effective_at,'2026-10-08T20:37:00+09:00');assert.equal(d.available_at,d.effective_at);
 assert.deepEqual(d.themes.map(t=>t.target_units),[3000,2500,2000,2500]);
 assert.equal(d.themes[0].holdings[3].listing,'USER_DECIDED: TSE (Tokyo, 8035)');
 assert.equal(d.themes[0].holdings[4].ticker_hint,'042700');
 assert.equal(d.themes[2].holdings[1].listing,'USER_DECIDED: Class A (GOOGL)');
});
test('projection binds exact adopted source and keeps identity and classification unavailable',()=>{
 const d=parseTargetV0Yaml(text),p=project();
 assert.equal(p.data_state,'REFERENCE');assert.equal(p.data_kind,'USER_SPEC_REFERENCE');assert.equal(p.weight_basis,'TARGET');
 assert.equal(p.qgv_version,'NOT_AVAILABLE');assert.equal(p.publication_grant,null);assert.equal(p.pit_status,'NOT_VERIFIED');
 assert.equal(p.source_metadata.source_sha256,TARGET_V0_SHA256);assert.equal(p.source_metadata.owner,'USER');
 assert.equal(p.source_metadata.effective_at_utc,'2026-10-08T11:37:00Z');
 assert.equal(p.source_metadata.available_at_utc,'2026-10-08T11:37:00Z');
 assert.equal(p.source_metadata.adopted_at_utc,'2026-10-08T11:37:00Z');
 assert.equal(p.as_of,'2026-10-08T12:00:00Z');assert.equal(p.holdings.length,19);
 assert.equal(p.source_metadata.mapping.admitted,0);assert.equal(p.source_metadata.mapping.unresolved,19);
 assert.deepEqual(p.source_metadata.themes,d.themes.map(t=>({theme_id:t.theme_id,label:t.label,target_units:t.target_units})));
 assert(p.holdings.every(h=>h.security_id===null&&h.types===null&&/^\/themes\/\d+\/holdings\/\d+$/.test(h.holding_id)));
 assert.deepEqual(p.types.exposures,[]);
 const expected=d.themes.flatMap(t=>t.holdings.map(h=>[h.label,h.weight_units,t.label]));
 assert.deepEqual(p.holdings.map(h=>[h.label,h.weight_units,h.industry]),expected);
 assert.deepEqual(p.source_metadata.source_rows.map(r=>r.ticker_hint),d.themes.flatMap(t=>t.holdings.map(h=>h.ticker_hint)));
});
test('parser permits quoted punctuation and escaped double quotes as literal source text',()=>{
 const d=parseTargetV0Yaml(text.replace('label: ASML Holding','label: "ASML, \\"Holding\\" # exact"'));
 assert.equal(d.themes[0].holdings[0].label,'ASML, "Holding" # exact');
});
const invalid=[
 ['duplicate YAML field',text.replace('version: v0','version: v0\nversion: v0'),/duplicate/i],
 ['unknown schema field',text.replace('status: ADOPTED','status: ADOPTED\nsource_grant: invented'),/unknown|unexpected/i],
 ['missing row',text.replace(/^      - \{ label: Intel.*\n/m,''),/19|subtotal|count/i],
 ['decimal unit',text.replace('weight_units: 900','weight_units: 900.5'),/integer/i],
 ['quoted unit',text.replace('weight_units: 900','weight_units: "900"'),/integer/i],
 ['negative unit',text.replace('weight_units: 900','weight_units: -900'),/integer/i],
 ['unsafe unit',text.replace('weight_units: 900','weight_units: 9007199254740992'),/integer/i],
 ['theme drift with conserved overall total',text.replace('target_units: 3000','target_units: 3001').replace('target_units: 2500','target_units: 2499'),/subtotal/i],
 ['duplicate member across themes',text.replace('label: Intel,               ticker_hint: INTC','label: ASML Holding,        ticker_hint: ASML'),/duplicate/i],
 ['duplicate theme concept',text.replace('theme_id: ai_semi','theme_id: semi_equipment'),/duplicate|theme/i],
 ['missing cash',text.replace(/^cash_units:.*\n/m,''),/cash|missing/i],
 ['unsupported YAML alias',text.replace('version: v0','version: &alias v0'),/unsupported/i],
 ['bad flow map trailing field',text.replace('weight_units: 900 }','weight_units: 900, }'),/flow|empty|unexpected/i],
 ['unclosed quoted scalar',text.replace('ticker_hint: ASML','ticker_hint: "ASML'),/quote|flow/i],
 ['tab indentation',text.replace('  role: USER','\trole: USER'),/tab|indent/i],
 ['naive clock',text.replaceAll('2026-10-08T20:37:00+09:00','2026-10-08T20:37:00'),/clock|timezone|timestamp/i],
 ['invalid date',text.replaceAll('2026-10-08T20:37:00+09:00','2026-02-30T20:37:00+09:00'),/clock|timestamp|date/i],
 ['backdated clock',text.replace('effective_at: "2026-10-08T20:37:00+09:00"','effective_at: "2026-09-14T20:37:00+09:00"'),/backdat|clock|adopt/i],
];
for(const [name,s,why]of invalid)test('reject '+name,()=>assert.throws(()=>parseTargetV0Yaml(s),why));
test('a valid but modified allocation cannot replace immutable adopted bytes',()=>{
 const changed=Buffer.from(text.replace('weight_units: 900','weight_units: 901').replace('weight_units: 600','weight_units: 599'));
 assert.throws(()=>project(changed),/sha256|source bytes/i);
});
test('observed clock cannot precede source availability',()=>assert.throws(()=>projectTargetV0(bytes,map,{observed_at:'2026-10-08T11:36:59Z'}),/available|observation/i));
test('mapping source mismatch and identity fabrication fail closed',()=>{
 const wrong=structuredClone(map);wrong.user_target_source.sha256='0'.repeat(64);assert.throws(()=>project(bytes,wrong),/mapping.*source/i);
 const fake=structuredClone(map);fake.rows[0].security_id='ticker:ASML';assert.throws(()=>project(bytes,fake),/mapping|identity/i);
 const partial=structuredClone(map);partial.rows.pop();assert.throws(()=>project(bytes,partial),/mapping|19/i);
});
