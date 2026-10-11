'use strict';
// S16 13F quarter view and S13 custom type PREVIEW: JS equals the Python reference (tools/s16_s13_reference.py).
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const W='../src/investment_system/product/web_assets/',Q=require(W+'thirteenf-quarter.js'),P=require(W+'device-profiles.js'),engine=require(W+'engine-preview.js');
const vectors=JSON.parse(fs.readFileSync(path.join(__dirname,'../tests/fixtures/s16_s13_reference_v1.json'),'utf8'));
function equal(a,b,where='$'){if(typeof b==='number'){assert.equal(typeof a,'number',where);assert.ok(Math.abs(a-b)<=Math.max(1e-10,Math.abs(b)*1e-10),where+' '+a+' != '+b);}
 else if(Array.isArray(b)){assert.ok(Array.isArray(a),where);assert.equal(a.length,b.length,where);b.forEach((v,i)=>equal(a[i],v,where+'['+i+']'));}
 else if(b&&typeof b==='object'){assert.ok(a&&typeof a==='object',where);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),where);for(const k of Object.keys(b))equal(a[k],b[k],where+'.'+k);}
 else assert.equal(a,b,where);}
function run(c){const d=structuredClone(c.input),before=JSON.stringify(d);let out;
 if(c.operation==='cusip_from_isin')out=d.isins.map(x=>Q.cusipFromIsin(x));
 else if(c.operation==='s16_pipeline'){const targets=Q.targetSecurities(d.catalog),summaries=d.reports.map(r=>Q.summarizeReport(r,targets));out={targets,summaries,overlap:Q.targetOverlap(summaries,targets)};}
 else if(c.operation==='type_target_preview')out=P.targetTypePreview(d.types,d.qg,d.custom,engine);
 else if(c.operation==='config_diff')out=P.configDiff(d.official,d.custom);
 else throw Error('UNKNOWN_OPERATION');
 assert.equal(JSON.stringify(d),before,'input not mutated');return out;}
assert.equal(vectors.synthetic,true);assert.ok(vectors.cases.length>=12);
for(const c of vectors.cases)test('python reference '+c.operation+' '+c.id,()=>equal(run(c),c.expected));
test('TARGET ids agree between S16 and S13 modules',()=>{assert.deepEqual(Q.TARGET.map(t=>t[0]),[...P.TARGET_IDS]);});
test('check digits: ISIN and CUSIP',()=>{assert.equal(Q.isinValid('US0378331005'),true);assert.equal(Q.isinValid('US0378331006'),false);assert.equal(Q.cusipValid('037833100'),true);assert.equal(Q.cusipValid('037833101'),false);assert.equal(Q.cusipFromIsin('IE00B8KQN827'),null);});
test('summary never derives values: only reported quantities and fixed NOT_AVAILABLE gaps',()=>{const targets=Q.targetSecurities(null),s=Q.summarizeReport({manager_cik:'0000000001',previous_quarter:'2026-03-31',current_quarter:'2026-06-30',state:'LIVE',changes:[{cusip:'A00000000',security_key:'c'.repeat(64),unit:'SH',kind:'NEW',reported_before:0,reported_after:5,reported_delta:5}]},targets);
 assert.equal(s.filed_date,null);assert.equal(s.filed_date_reason,'FILING_DATE_NOT_PUBLISHED');assert.equal(s.top10_weight,null);assert.equal(s.holdings_count,null);assert.ok(!/"[a-z_]*(?:value|price|amount)[a-z_]*":/i.test(JSON.stringify(s)));assert.ok(s.target.every(r=>r.status==='NOT_AVAILABLE'&&r.reason==='CATALOG_NOT_AVAILABLE'));});
test('custom PREVIEW never touches the official config object',()=>{const official=require(W+'type-config-defaults.js'),before=JSON.stringify(official),c=P.copyOfficialTypes();c.types[0].weights.Q=40;c.types[0].weights.G=40;
 P.targetTypePreview({data:{companies:{nvda:{metrics:{revenue_cagr_3y:0.3}}}}},null,c,engine);assert.equal(JSON.stringify(official),before);assert.equal(official.status,'OFFICIAL_PROVISIONAL');});
