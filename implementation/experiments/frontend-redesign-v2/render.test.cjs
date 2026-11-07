/* String rendering / state smoke tests. Not a browser layout or accessibility test. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function setup(){
 const elements=new Map(),handlers=new Map(),storage=new Map();
 function el(id){if(!elements.has(id))elements.set(id,{innerHTML:'',value:'',isConnected:true,open:false,dataset:{},classList:{toggle(){},add(){},remove(){}},addEventListener(t,f){handlers.set(id+':'+t,f);},focus(){},setSelectionRange(){},showModal(){this.open=true;},close(){this.open=false;}});return elements.get(id);}
 const document={documentElement:{},body:{classList:{toggle(){}}},getElementById:el,querySelectorAll:()=>[],addEventListener(t,f){handlers.set('doc:'+t,f);},activeElement:null};
 const c={console,document,location:{hash:'#today'},localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},URL,Intl,Date,setTimeout:()=>1,clearTimeout(){},addEventListener(t,f){handlers.set('win:'+t,f);},scrollTo(){}};c.window=c;c.globalThis=c;vm.createContext(c);
 for(const f of ['data.js','model.js','app.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,f),'utf8'),c,{filename:f});
 return{c,el,handlers,eval:s=>vm.runInContext(s,c)};
}
test('all primary routes and company tabs render in both languages',()=>{
 const s=setup();for(const lang of ['ko','en'])for(const route of ['today','explore','company/NVDA','company/042700','portfolio','market','records','settings']){
  s.eval(`lang=${JSON.stringify(lang)};location.hash=${JSON.stringify('#'+route)};render()`);
  assert.match(s.el('main').innerHTML,/<h1>/);assert.doesNotMatch(s.el('main').innerHTML,/>undefined<|>NaN<|NaN%/);
 }
 for(const tab of ['overview','financial','price','news']){s.eval(`location.hash='#company/NVDA';companyTab='${tab}';render()`);assert.ok(s.el('main').innerHTML.length>1000);}
});
test('source snapshot coverage and target allocation match source counts',()=>{const s=setup();assert.equal(s.eval("coverage('Q')"),65);assert.equal(s.eval("coverage('G')"),64);assert.equal(s.eval('targets.length'),19);assert.equal(s.eval('targets.reduce((n,r)=>n+r.target,0)'),100);assert.equal(s.eval("lookup.get('NVDA').q"),74.81437969924812);assert.equal(s.eval("lookup.get('042700').q"),null);});
test('search and compare preserve exact selected tickers',()=>{const s=setup();s.eval("query='엔비디아';location.hash='#explore';render()");assert.match(s.el('main').innerHTML,/#company\/NVDA/);assert.doesNotMatch(s.el('main').innerHTML,/#company\/MSFT/);s.eval("toggleCompare('NVDA');toggleCompare('MSFT');toggleCompare('AMD');toggleCompare('ASML');compareModal()");assert.equal(s.eval('compare.length'),3);assert.equal(s.el('dialog').open,true);assert.match(s.el('dialog').innerHTML,/74\.8/);});
test('empty state never shows a fabricated price or portfolio return',()=>{const s=setup();s.eval("location.hash='#portfolio';render()");assert.match(s.el('main').innerHTML,/보유가 없습니다/);s.eval("location.hash='#company/NVDA';companyTab='price';render()");assert.match(s.el('main').innerHTML,/가격 이력이 없습니다/);assert.doesNotMatch(s.el('main').innerHTML,/<svg class="chart"/);});
test('external article titles and saved note text are escaped',()=>{const s=setup();const output=s.eval("newsItems([{kind:'news',ticker:'X',title:'<img src=x onerror=alert(1)>',source:'x',url:'javascript:alert(1)',at:'2026-10-17',occurrence:'NEW'}])");assert.doesNotMatch(output,/<img|href="javascript:/);assert.match(output,/&lt;img/);s.eval("notes=[{text:'<script>oops</script>',at:'2026-10-17'}];location.hash='#records';render()");assert.doesNotMatch(s.el('main').innerHTML,/<script>/);});
test('watchlist persistence is namespaced and does not write production keys',()=>{const s=setup();s.eval("watch=['NVDA'];save()");assert.match(s.c.localStorage.getItem('investment.ui-design.v2'),/NVDA/);assert.equal(s.c.localStorage.getItem('investment.web.v1.personal'),undefined);});
test('empty results and changing filters clamp pagination',()=>{const s=setup();s.eval("page=50;query='no such company';location.hash='#explore';render()");assert.match(s.el('main').innerHTML,/조건에 맞는 기업이 없습니다/);assert.equal(s.eval('page'),1);});
test('missing timestamps never become January 1970',()=>{const s=setup();assert.equal(s.eval('date(null,true)'), '시점 미제공');assert.equal(s.eval("date('',true)"), '시점 미제공');s.eval("location.hash='#company/042700';render()");assert.doesNotMatch(s.el('main').innerHTML,/1970/);});
test('Korean IME composition does not replace the active input',()=>{const s=setup();s.eval("location.hash='#explore';render()");const before=s.el('main').innerHTML;s.handlers.get('company-search:input')({isComposing:true,target:{value:'엔',selectionStart:1}});assert.equal(s.el('main').innerHTML,before);});
test('version mismatch is explicit in the explorer score cell',()=>{const s=setup();const output=s.eval("score(null,'Q',{record:{state:'LIVE',calc_version:'old',acquired_at:'2026-10-16T00:00:00Z'}})");assert.match(output,/버전 불일치/);});
