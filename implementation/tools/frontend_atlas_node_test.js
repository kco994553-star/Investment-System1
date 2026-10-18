'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const base=path.join(__dirname,'../src/investment_system/product/web_assets');
const Company=require(path.join(base,'company-screen.js'));
test('radar preserves scores and renders no segment across missing G',()=>{
 const d=Object.freeze({q:72,g:null,v:81,total:76});const before=JSON.stringify(d),html=Company.radarHtml(d,'ko-KR');
 assert.match(html,/72\.0 \/ 100/);assert.match(html,/81\.0 \/ 100/);
 assert.equal((html.match(/data-radar-axis=/g)||[]).length,2);
 assert.match(html,/<g class="radar-trace"><\/g>/);assert.equal(JSON.stringify(d),before);
 assert.equal((html.match(/정의 대기/g)||[]).length,3);
});
test('radar keeps zero as a valid score and rejects invalid numeric input',()=>{
 const html=Company.radarHtml({q:0,g:NaN,v:Infinity},'en-US');
 assert.match(html,/0\.0 \/ 100/);assert.equal((html.match(/data-radar-axis=/g)||[]).length,1);
 assert.doesNotMatch(html,/NaN|Infinity/);assert.match(Company.radarHtml(null,'en-US'),/Unavailable/);
 assert.equal((Company.radarHtml({q:-1,g:101,v:'70'},'en-US').match(/data-radar-axis=/g)||[]).length,0);
});
test('radar only connects adjacent known axes; it never manufactures a closed score area',()=>{
 const html=Company.radarHtml({q:50,g:60,v:70},'en-US');
 const trace=html.match(/<g class="radar-trace">(.*?)<\/g>/)[1];
 assert.equal((trace.match(/<line /g)||[]).length,2);assert.doesNotMatch(trace,/<polygon|<path/);
});
function shell(){const w={document:{addEventListener(){},querySelector(){return null;},querySelectorAll(){return[];}},location:{hash:'#system'},addEventListener(){},setTimeout,clearTimeout,innerHeight:800};w.window=w;vm.runInNewContext(fs.readFileSync(path.join(base,'app-shell.js'),'utf8'),w);return w.AppShell;}
test('system guide uses existing destinations, labels connection gaps, and keeps 13F pending',()=>{
 const s=shell();for(const loc of ['ko-KR','en-US']){const html=s.pendingHtml('system',loc);assert.match(html,/data-system-guide/);assert.equal((html.match(/atlas-map-card/g)||[]).length,7);assert.doesNotMatch(html,/data-pending-page|<script|RIG/);for(const href of ['#leaderboard','#technical','#macro','#news','#portfolio','#research','#validation'])assert.ok(html.includes('href="'+href+'"'));}
 assert.match(s.pendingHtml('lab-13f','ko-KR'),/data-pending-page="lab-13f"/);
 assert.equal(s.MENUS.find(x=>x.key==='system').items[0][3],undefined);
});
