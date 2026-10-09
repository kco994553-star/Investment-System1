/* All positions below are generated synthetic inputs; no holdings fixture is persisted. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const modulePath = require('node:path').join(__dirname, '../src/investment_system/product/web_assets/device-actual.js');
const api = fs.existsSync(modulePath) ? require(modulePath) : {};
const now = '2030-01-02T12:00:00.000Z';
const catalog = {
  schema:'DEVICE_ACTUAL_CATALOG/1', target_root_version:'v0', target_root_sha256:'a'.repeat(64),
  identity_map_version:'map-v1', identity_map_sha256:'b'.repeat(64), total_units:10000,
  themes:[{theme_id:'first',label:'첫째',label_en:'First',target_units:6000},{theme_id:'second',label:'둘째',label_en:'Second',target_units:4000}],
  instruments:Array.from({length:3},(_,i)=>({row_index:i,label:`Public instrument ${i}`,ticker:`PUBLIC${i}`,theme_id:i<2?'first':'second',target_units:[3000,3000,4000][i],security_reference:{scheme:'ISIN',value:`PUBLIC-IDENTITY-${i}`},currency:i===2?'JPY':'USD'}))
};
const rows = (count=2) => Array.from({length:count},(_,i)=>({security_reference:{...catalog.instruments[i].security_reference},quantity:String(i+1),average_cost:String((i+1)*7),currency:catalog.instruments[i].currency}));
function snapshot(){return api.makeSnapshot(catalog,rows(),null,now);}
function mutate(fn){const s=snapshot();fn(s);return s;}
function rejected(s,options={now}){let rejected=false;try{api.validate(s,catalog,options);}catch{rejected=true;}assert.ok(rejected,'invalid snapshot must be rejected');}
function quote(i,price){return {security_reference:{...catalog.instruments[i].security_reference},price:String(price),currency:catalog.instruments[i].currency,as_of:'2030-01-02T10:00:00Z',available_at:'2030-01-02T11:00:00Z'};}

test('device-only snapshot helpers are available',()=>{for(const name of ['validate','makeSnapshot','valuation'])assert.equal(typeof api[name],'function',name+' helper required');});
test('snapshot binds device ownership, complete themes and exact public catalog',()=>{
  const s=snapshot(), valid=api.validate(s,catalog,{now});
  assert.ok(valid.schema==='device-actual-holdings/1'&&valid.kind==='ACTUAL'&&valid.ownership==='USER_DEVICE_ONLY');
  assert.ok(valid.owner.role==='USER'&&valid.owner.storage==='USER_DEVICE_ONLY');
  assert.ok(s.version===1&&s.themes.length===catalog.themes.length&&s.themes[1].holdings.length===0);
  assert.ok(s.target_root_sha256===catalog.target_root_sha256&&s.identity_map_sha256===catalog.identity_map_sha256);
  valid.themes[0].holdings[0].quantity='99';assert.ok(s.themes[0].holdings[0].quantity!=='99','validation returns an independent snapshot');
});
test('snapshot revision increases and minimum revision checks reject stale revisions',()=>{
  const old=snapshot(), next=api.makeSnapshot(catalog,rows(),old,now);
  assert.ok(next.version===old.version+1);rejected(old,{now,minimumVersion:old.version});
  assert.ok(api.validate(next,catalog,{now,minimumVersion:old.version}).version>old.version);
});
test('strict envelope rejects unknown properties, ownership and bound version mismatches',()=>{
  for(const fn of [s=>s.extra=true,s=>s.owner.extra=true,s=>s.owner.role='SYSTEM',s=>s.ownership='SERVER',s=>s.schema='other',s=>s.kind='TARGET',s=>s.version=0,s=>s.version=1.5,s=>s.target_root_version='v1',s=>s.target_root_sha256='c'.repeat(64),s=>s.identity_map_version='other',s=>s.identity_map_sha256='c'.repeat(64),s=>s.themes[0].extra=true,s=>s.themes.pop()])rejected(mutate(fn));
});
test('strict identities reject duplicates, theme mismatch and catalog ref variants',()=>{
  for(const fn of [s=>s.themes[0].holdings.push({...s.themes[0].holdings[0]}),s=>s.themes[1].holdings.push(s.themes[0].holdings.pop()),s=>s.themes[0].holdings[0].security_reference.extra=true,s=>s.themes[0].holdings[0].security_reference.value='UNKNOWN',s=>s.themes[0].holdings[0].security_reference='PUBLIC-IDENTITY-0',s=>s.themes[1].theme_id='first'])rejected(mutate(fn));
});
test('strict numeric strings and supported currencies fail closed',()=>{
  for(const value of ['-1','NaN','Infinity','1e2',' 1','01','1.','',1,null,'9'.repeat(100)])rejected(mutate(s=>s.themes[0].holdings[0].quantity=value));
  for(const value of ['-1',null,1])rejected(mutate(s=>s.themes[0].holdings[0].average_cost=value));
  rejected(mutate(s=>s.themes[0].holdings[0].currency='usd'));rejected(mutate(s=>s.themes[0].holdings[0].currency='EUR'));
  rejected(mutate(s=>s.themes[0].holdings[0].extra=true));
});
test('future, missing and inconsistent clocks are rejected',()=>{
  for(const fn of [s=>delete s.effective_at,s=>s.available_at='2030-01-03T00:00:00Z',s=>s.effective_at='2030-01-02T12:01:00Z',s=>s.effective_at='2030-01-02',s=>s.effective_at='2030-02-30T00:00:00Z',s=>s.available_at='bad'])rejected(mutate(fn));
});
test('missing ACTUAL and missing quotes never substitute average cost',()=>{
  assert.ok(api.valuation(null,catalog,[],{now}).state==='NOT_AVAILABLE');
  const v=api.valuation(snapshot(),catalog,[],{now});
  assert.ok(v.total===null&&v.rows.every(r=>r.market_value===null&&r.weight===null&&r.delta===null));
  assert.ok(v.state==='NOT_AVAILABLE'&&v.reason==='MISSING_QUOTES');
});
test('complete same-currency quotes calculate values, weights and target deltas',()=>{
  const v=api.valuation(snapshot(),catalog,[quote(0,10),quote(1,20)],{now});
  assert.ok(v.state==='AVAILABLE'&&v.total===50&&v.currency==='USD');
  assert.ok(v.rows[0].market_value===10&&Math.abs(v.rows[0].weight-0.2)<1e-12&&Math.abs(v.rows[0].delta+0.1)<1e-12);
  assert.ok(v.themes[0].weight===1&&Math.abs(v.themes[0].delta-0.4)<1e-12);
});
test('partial quote coverage blocks all portfolio weights and preserves row values',()=>{
  const v=api.valuation(snapshot(),catalog,[quote(0,10)],{now});
  assert.ok(v.total===null&&v.rows[0].market_value===10&&v.rows[1].market_value===null);
  assert.ok(v.rows.every(r=>r.weight===null&&r.delta===null)&&v.themes.every(t=>t.weight===null&&t.delta===null));
});
test('mixed currencies keep local row values without inventing FX or normalizing',()=>{
  const v=api.valuation(api.makeSnapshot(catalog,rows(3),null,now),catalog,[quote(0,10),quote(1,20),quote(2,30)],{now});
  assert.ok(v.state==='NOT_AVAILABLE'&&v.reason==='FX_NOT_AVAILABLE'&&v.total===null);
  assert.ok(v.rows.every(r=>r.market_value!==null&&r.weight===null&&r.delta===null));
  assert.ok(v.currency_totals.USD===50&&v.currency_totals.JPY===90);
});
test('invalid, ambiguous or future quotes cannot produce portfolio availability',()=>{
  for(const qs of [[quote(0,10),quote(0,11),quote(1,20)],[{...quote(0,10),available_at:'2030-01-03T00:00:00Z'},quote(1,20)],[{...quote(0,10),currency:'JPY'},quote(1,20)],[{...quote(0,10),as_of:null},quote(1,20)],[{...quote(0,10),price:'-1'},quote(1,20)]]) {
    const v=api.valuation(snapshot(),catalog,qs,{now});assert.ok(v.state==='NOT_AVAILABLE'&&v.total===null);
  }
});
test('quote denomination must match catalog and holding without an FX contract',()=>{
  const localRows=rows();localRows[0].currency='JPY';
  const s=api.makeSnapshot(catalog,localRows,null,now);
  const v=api.valuation(s,catalog,[{...quote(0,10),currency:'JPY'},quote(1,20)],{now});
  assert.ok(v.rows[0].market_value===null&&v.total===null&&v.state==='NOT_AVAILABLE');
});
test('a malformed duplicate quote cannot hide identity ambiguity',()=>{
  const v=api.valuation(snapshot(),catalog,[{...quote(0,10),price:'invalid'},quote(0,10),quote(1,20)],{now});
  assert.ok(v.rows[0].market_value===null&&v.total===null&&v.state==='NOT_AVAILABLE');
});
test('non-finite aggregate values fail closed in portfolio and currency summaries',()=>{
  const localRows=rows().map(row=>({...row,quantity:'1'}));
  const s=api.makeSnapshot(catalog,localRows,null,now);
  const v=api.valuation(s,catalog,[{...quote(0,1),price:1e308},{...quote(1,1),price:1e308}],{now});
  assert.ok(v.state==='NOT_AVAILABLE'&&v.total===null&&v.currency_totals.USD===null&&v.reason==='CALCULATION_ERROR');
});
test('zero quantity still requires a valid supplied market quote',()=>{
  const zeroRows=rows(1).map(row=>({...row,quantity:'0'}));
  const s=api.makeSnapshot(catalog,zeroRows,null,now);
  const missing=api.valuation(s,catalog,[],{now});
  assert.ok(missing.rows[0].market_value===null&&missing.rows[0].weight===null&&missing.total===null);
  const quoted=api.valuation(s,catalog,[quote(0,10)],{now});
  assert.ok(quoted.rows[0].market_value===0&&quoted.rows[0].weight===null&&quoted.state==='NOT_AVAILABLE');
});
test('backup normalization preserves input values and advances the stored revision',()=>{
  assert.equal(typeof api.prepareImport,'function','backup import preparation helper required');
  const backup=snapshot(), current=api.makeSnapshot(catalog,rows(),backup,now);
  const imported=api.prepareImport(backup,catalog,current,'2030-01-02T12:01:00Z');
  assert.ok(imported.version===current.version+1&&imported.effective_at===backup.effective_at&&imported.available_at==='2030-01-02T12:01:00.000Z');
  assert.ok(JSON.stringify(imported.themes)===JSON.stringify(backup.themes));
  const same=api.prepareImport(current,catalog,current,'2030-01-02T12:01:00Z');
  assert.ok(same.version===current.version+1);
  const fresh=api.prepareImport(backup,catalog,null,'2030-01-02T12:01:00Z');
  assert.ok(fresh.version===backup.version&&fresh.available_at==='2030-01-02T12:01:00.000Z');
  let rejected=false;try{api.prepareImport({...backup,identity_map_version:'invalid'},catalog,current,now);}catch{rejected=true;}assert.ok(rejected);
});
