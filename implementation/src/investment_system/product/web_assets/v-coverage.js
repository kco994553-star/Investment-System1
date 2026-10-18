/* VCoverage: "V 산출 현황 · 이 기기" on S06 (1.1 리더보드). How many Universe GENERAL companies get a V on THIS device once the
   user's own Universe sheet prices are read ("Universe 읽기", PrivateSubsetView, RAM). Numbers come from the shared page result
   (QgvScores.pageResult: one collectQuotes + one compute over every code of the loaded sec-qgv2.json, the same result the stat
   radar reads) and its counts (QgvScores.vCoverage): the real engine rules, no extra required input, no other metric in place
   of V. Financials are their own line ('현재 금융업 가치평가 모델 미지원'), never a data shortage. The full basis keeps
   not-applicable and unknown rows in its denominator. '공개 입력 기준 상한' is an upper bound, never a count. The 90% target is an
   observation metric only (applicable n and target computed live from the loaded file), wired to nothing else.
   Price time: the sheet READ time is shown apart from the price's own time; the GOOGLEFINANCE column has no trade time, so it is
   '미확인' and a fresh read never makes an old price look current.
   RAM only: no price, count or result is stored, sent or logged; the panel shows counts, never a price. No inline style (CSP). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.VCoverage=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const FINANCIAL='FINANCIAL_PROFILE_V_NOT_DEFINED';
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const SHARES_RULE=['V-SHARES-SCALE: 같은 공시 표지 주식수의 0.1~10배 밖이면 NA (1,000배 등 배율 보정 없음)','V-SHARES-SCALE: NA when outside 0.1–10× the cover share count of the same filing (no ×1,000 rescaling)'];
const SOURCE_REASON={NOT_COLLECTED:['아직 수집 안 됨','not collected yet'],CIK_UNRESOLVED:['CIK 미해결','CIK unresolved'],NO_ANNUAL_SEC_FINANCIALS:['연간 SEC 재무 없음','no annual SEC financials'],NON_SEC_ISSUER:['SEC 공시 대상 아님','not an SEC filer']};
const PRICE_SOURCE={UNIVERSE_SHEET:['Universe 시트(GOOGLEFINANCE)','Universe sheet (GOOGLEFINANCE)']};
/* '2026-10-18 09:31 UTC · 2026-10-18 18:31 KST' (KST = UTC+9, no DST). */
function clock(iso){const t=typeof iso==='string'?Date.parse(iso):NaN;if(!Number.isFinite(t))return null;const f=ms=>new Date(ms).toISOString().slice(0,16).replace('T',' ');return f(t)+' UTC · '+f(t+9*3600e3)+' KST';}
const frac=(a,b)=>a===null||a===undefined?'—':a+'/'+b;
/* HTML of one QgvScores.vCoverage result (s). */
function html(s,{en=false,reasonText=c=>c}={}){
 const T=(ko,e)=>en?e:ko,P=s.population,G=P.general,N=P.total,on=s.connected,cell=(attr,val)=>'<td'+(attr?' '+attr:'')+'>'+esc(val)+'</td>',count=(name,val)=>name+(on?'="'+val+'"':'');
 let h='<section class="card v-coverage" data-v-coverage="'+(on?'READY':'NOT_CONNECTED')+'"><h2>'+T('V 산출 현황 · 이 기기','V coverage · this device')+'</h2>';
 h+='<p class="small">'+esc(T('이 기기 RAM에서만 계산 · 저장·전송 없음 · 공개 sec-qgv2.json '+N+'개 코드 × 내 Universe 시트 가격 · 실제 엔진 규칙','Computed in this device’s RAM only · not stored or sent · public sec-qgv2.json '+N+' codes × my Universe sheet prices · real engine rules'))+'</p>';
 if(!on)h+='<p class="v-coverage-state" data-v-coverage-state>'+esc(T('가격 미연결: V 실제 산출 수는 Universe 읽기 뒤 표시','No prices connected: the actual V count is shown after the Universe read'))+'</p>';
 h+='<p class="v-coverage-target" data-v-target="'+s.target.n+'"'+(on?' data-v-met="'+(s.target.met?'MET':'NOT_MET')+'"':'')+'>'+esc(T('관찰 지표 · 목표 ','Observation metric · target ')+s.target.n+'/'+G+T(' (일반 기업 90%) · 현재 ',' (90% of general) · now ')+(on?s.v.general+'/'+G+' ('+(s.target.met?T('달성','met'):T('미달','not met'))+')':'— ('+T('가격 미연결','no prices')+')'))+'</p>';
 h+='<p class="small" data-v-target-note>'+esc(T('관찰용 지표이며 TARGET 확정 조건에 쓰이지 않습니다 · 적용 n과 목표는 불러온 파일에서 계산','An observation metric, not a TARGET confirmation condition · applicable n and target computed from the loaded file'))+'</p>';
 h+='<ul class="v-coverage-pop" data-v-population><li data-pop-total="'+N+'">'+esc(T('전체 Universe ','All Universe ')+N)+'</li><li data-pop-general="'+G+'">'+esc(T('일반 기업(V 적용) ','General (V applies) ')+G)+'</li><li data-pop-financial="'+P.financial+'">'+esc(T('금융업 · ','Financials · ')+reasonText(FINANCIAL)+' '+P.financial)+'</li><li data-pop-unknown="'+P.unknown+'">'+esc(T('프로필·업종 미확인(자료 없음) ','Profile/industry unknown (no data) ')+P.unknown)+'</li>'+(P.stopped?'<li data-pop-stopped="'+P.stopped+'">'+esc(T('식별 충돌로 사용 중지 ','Stopped: identity conflict ')+P.stopped)+'</li>':'')+'</ul>';
 h+='<div class="v-coverage-table-wrap"><table class="v-coverage-table" data-v-coverage-table><thead><tr><th scope="col">'+T('항목','Item')+'</th><th scope="col">'+esc(T('전체 '+N+' 기준','All '+N))+'</th><th scope="col">'+esc(T('일반 기업 '+G+' 기준','General '+G))+'</th></tr></thead><tbody>';
 h+='<tr data-v-row="v"><th scope="row">'+T('V 산출 (실제 엔진 규칙)','V computed (engine rules)')+'</th>'+cell(count('data-v-full',on&&s.v.full),on?frac(s.v.full,N):'—')+cell(count('data-v-general',on&&s.v.general),on?frac(s.v.general,G):'—')+'</tr>';
 h+='<tr data-v-row="qgv"><th scope="row">'+T('Q·G·V 공통 산출','Q·G·V all computed')+'</th>'+cell(count('data-qgv-full',on&&s.qgv.full),on?frac(s.qgv.full,N):'—')+cell(count('data-qgv-general',on&&s.qgv.general),on?frac(s.qgv.general,G):'—')+'</tr>';
 // Q·G-only totals = financials + no price / V not computed. Value-trap-gate rows had V computed and the approved gate rule
 // excluded it from the total: not a 'V 없음' result, kept in the official ranking, so they get their own line (all GENERAL rows).
 const qo=s.qg_only_total,qgFull=on?qo.full-qo.gate:null,qgGeneral=on?qo.general-qo.gate:null;
 h+='<tr data-v-row="qg-only-total"><th scope="row">'+T('Q·G만으로 종합점수가 난 행','Rows with a total from Q·G only')+'</th>'+cell(count('data-qg-only-full',qgFull),on?qgFull+T(' (금융 ',' (financial ')+qo.financial+T(' · 가격 없음/V 미산출 ',' · no price/V not computed ')+qo.no_v+')':'—')+cell(count('data-qg-only-general',qgGeneral),on?qgGeneral+T(' (가격 없음/V 미산출 ',' (no price/V not computed ')+qo.no_v+')':'—')+'</tr>';
 h+='<tr data-v-row="gate"><th scope="row">'+T('가치 함정 관문으로 V 제외(공식 규칙 · 순위 유지)','V excluded by the value-trap gate (official rule · stays ranked)')+'</th>'+cell(count('data-gate-full',on&&qo.gate),on?frac(qo.gate,N):'—')+cell(count('data-gate-general',on&&qo.gate),on?frac(qo.gate,G):'—')+'</tr>';
 h+='<tr data-v-row="complete"><th scope="row">'+T('V 입력 완비 (빠진 V 입력 없음)','V inputs complete (none missing)')+'</th>'+cell('data-complete="'+s.input_complete+'"',frac(s.input_complete,N))+cell('',frac(s.input_complete,G))+'</tr>';
 h+='<tr data-v-row="financial"><th scope="row">'+esc(T('금융업 · ','Financials · ')+reasonText(FINANCIAL))+'</th>'+cell('data-financial="'+P.financial+'"',frac(P.financial,N))+cell('',T('해당 없음 (분모 아님)','not applicable (not in denominator)'))+'</tr>';
 h+='<tr data-v-row="unknown"><th scope="row">'+T('프로필·업종 미확인 (자료 없음)','Profile/industry unknown (no data)')+'</th>'+cell('data-no-data="'+P.unknown+'"',frac(P.unknown,N))+cell('','—')+'</tr>';
 if(P.stopped)h+='<tr data-v-row="stopped"><th scope="row">'+T('식별 충돌로 사용 중지','Stopped: identity conflict')+'</th>'+cell('data-stopped="'+P.stopped+'"',frac(P.stopped,N))+cell('','—')+'</tr>';
 h+='</tbody></table></div>';
 h+='<p class="small" data-v-composition>'+esc(T('전체 '+N+' = 일반 '+G+' + 금융 '+P.financial+' + 미확인 '+P.unknown+(P.stopped?' + 사용 중지 '+P.stopped:'')+' · 금융업은 자료 부족이 아니라 모델 미지원으로 따로 셈','All '+N+' = general '+G+' + financial '+P.financial+' + unknown '+P.unknown+(P.stopped?' + stopped '+P.stopped:'')+' · financials are counted apart as model not supported, not as missing data'))+'</p>';
 h+='<p class="small" data-v-upper="'+s.upper_bound+'">'+esc(T('공개 입력 기준 상한 '+s.upper_bound+'/'+G+' · 주식수와 EBIT 또는 FCF가 있는 일반 기업 수 · 상한일 뿐 산출 수가 아님','Upper bound from public inputs '+s.upper_bound+'/'+G+' · general companies with shares and EBIT or FCF · an upper bound, not a count'))+'</p>';
 if(on){
  h+='<h3>'+esc(T('V 미산출 사유 · 일반 기업 '+s.not_computed+'곳','Why V is not computed · '+s.not_computed+' general companies'))+'</h3><ul class="v-coverage-reasons" data-v-reasons>'+s.reasons.map(([c,k])=>'<li data-v-reason="'+esc(c)+'" data-count="'+k+'"><b>'+k+'</b> · '+esc(c)+' · '+esc(reasonText(c))+'</li>').join('')+'</ul>';
  h+='<details data-v-factor-details><summary>'+T('미산출 행의 요인별 엔진 사유 (한 행이 여러 사유에 들어감)','Engine reasons of the missing factors in those rows (a row can count under several)')+'</summary><ul class="v-coverage-reasons" data-v-factor-reasons>'+s.factor_reasons.map(([c,k])=>'<li data-v-factor-reason="'+esc(c)+'" data-count="'+k+'"><b>'+k+'</b> · '+esc(c)+' · '+esc(reasonText(c))+'</li>').join('')+'</ul></details>';
 }
 // Price time per source: the GOOGLEFINANCE column has no trade time (미확인); a device quote with its own time shows it.
 const times=on?s.price_time.map(t=>'<li data-price-source="'+esc(t.source)+'" data-rows="'+t.rows+'" data-unconfirmed="'+t.unconfirmed+'">'+esc((PRICE_SOURCE[t.source]?PRICE_SOURCE[t.source][en?1:0]:t.source)+' '+t.rows+T('행 · ',' rows · ')+(t.unconfirmed===t.rows?T('미확인 (가격 자체 시각 없음)','unconfirmed (no price time)'):(t.from===t.to?t.from:t.from+' ~ '+t.to)+(t.unconfirmed?T(' · 미확인 ',' · unconfirmed ')+t.unconfirmed+T('행',' rows'):'')+(t.stale?T(' · 오래됨 ',' · stale ')+t.stale+T('행',' rows'):'')))+'</li>').join(''):'';
 const read=clock(s.read_at),unconfirmed=on?s.price_time.every(t=>t.unconfirmed===t.rows):true,shareText='SEC v_inputs_v2.diluted_shares · '+T('기간 말 ','period end ')+(s.shares.period_from?s.shares.period_from+' ~ '+s.shares.period_to:'—')+' · '+s.shares.rows+'/'+G+T('행',' rows')+' · '+SHARES_RULE[en?1:0];
 h+='<h3>'+T('가격 기준','Price basis')+'</h3><dl class="v-coverage-basis" data-v-price-basis>';
 h+='<dt>'+T('시트 읽은 시각','Sheet read at')+'</dt><dd data-v-acquired>'+esc(on?(read||'—')+T(' · Universe 탭을 가져온 시각 (가격 시각 아님)',' · when the Universe tab was fetched (not a price time)'):T('읽기 전','not read yet'))+'</dd>';
 h+='<dt>'+T('가격 기준 시각','Price time')+'</dt><dd data-v-price-time="'+(on?(unconfirmed?'UNCONFIRMED':'PER_SOURCE'):'NOT_READ')+'">'+esc(on?(unconfirmed?T('미확인','unconfirmed'):T('출처별','per source')):T('읽기 전','not read yet'))+(on?'<ul class="v-coverage-reasons">'+times+'</ul>':'')+'</dd>';
 h+='<dt>'+T('통화','Currency')+'</dt><dd data-v-currency'+(on?' data-currency-mismatch="'+s.currency_mismatch+'"':'')+'>'+esc('USD'+(on?T(' · 가격 반영 '+s.priced+'/'+N+'행 · 통화 불일치 '+s.currency_mismatch+'행(일반 기업, 환율 변환 없음)',' · priced '+s.priced+'/'+N+' rows · currency mismatch '+s.currency_mismatch+' rows (general, no FX conversion)'):''))+'</dd>';
 h+='<dt>'+T('주식수 기준','Share count basis')+'</dt><dd data-v-shares>'+esc(shareText)+'</dd>';
 h+='<dt>'+T('계산 버전','Calc version')+'</dt><dd data-v-calc-version>'+esc((s.calc_version||'—')+(s.as_of?T(' · 공개 파일 기준 ',' · public file as of ')+s.as_of:''))+'</dd></dl>';
 if(s.unknown_rows.length)h+='<p class="small" data-v-no-data-rows>'+esc(T('미확인(자료 없음): ','Unknown (no data): ')+s.unknown_rows.map(r=>r.code+(r.reasons.length?' ('+r.reasons.map(x=>SOURCE_REASON[x]?SOURCE_REASON[x][en?1:0]:x).join(', ')+')':'')).join(' · '))+'</p>';
 return h+'</section>';
}
let painted=null,ticket=0;
/* Paint into host (S06 '#v-coverage-root'). catalog: the device catalog or a function returning its promise (for the device quote
   path of the given identities). Returns the vCoverage counts (RAM) or null. */
async function paint(host,{publicScreens={},catalog=null,identities=[],preset=null,gate=null,locale='ko-KR',view=globalThis}={}){
 if(!host)return null;const mine=++ticket,QS=view.QgvScores,QI=view.Qgv2Inputs,en=locale==='en-US';
 try{
  const inputs=QS&&QI&&publicScreens?publicScreens[QI.FILE]||null:null;
  if(!inputs||typeof QS.pageResult!=='function'){host.innerHTML='<section class="card v-coverage" data-v-coverage="NOT_AVAILABLE"><h2>'+(en?'V coverage · this device':'V 산출 현황 · 이 기기')+'</h2><p class="small">'+(en?'Public sec-qgv2.json not loaded: V coverage cannot be shown':'공개 sec-qgv2.json이 없어 V 산출 현황을 표시할 수 없습니다')+'</p></section>';painted=null;return null;}
  let cat=null;try{cat=typeof catalog==='function'?await catalog():await catalog;}catch(_){cat=null;}
  const result=await QS.pageResult(view,{v2Inputs:inputs,catalog:cat,identities,preset,gate});if(mine!==ticket||!host.isConnected||!result)return null;
  if(painted&&painted.host===host&&painted.result===result&&painted.locale===locale)return painted.summary;
  const s=QS.vCoverage(result,inputs),open=host.querySelector('[data-v-factor-details]')?.open===true;if(!s)return null;
  host.innerHTML=html(s,{en,reasonText:c=>QS.reasonText(c,en)});if(open){const d=host.querySelector('[data-v-factor-details]');if(d)d.open=true;}
  painted={host,result,locale,summary:s};return s;
 }catch(_){return null;}
}
return Object.freeze({html,paint,clock});
});
