/* VCoverage: "V 산출 현황 · 중앙 게시" on S06 (1.1 리더보드). Owner decision 2026-10-31 (DC-31, device V abolished): how many
   Universe companies have an official V in the central publication qgv-official.json, read from its own coverage block (counts
   only, recomputed by QgvOfficial.validate from the published rows: same vocabulary as before) next to the publication's basis
   (price basis day, publication time, STALE past 2 completed New York sessions, calc version) and the IEX attribution with its
   terms link. This device computes no V and reads no price for it. Without a publication: the reason (OFFICIAL_NOT_PUBLISHED /
   OFFICIAL_INVALID / OFFICIAL_UNAVAILABLE) and no V count, never a device V. Financials are their own line ('현재 금융업 가치평가
   모델 미지원'), never a data shortage. The 90% target is an observation metric only, wired to nothing else.
   RAM only: nothing is stored, sent or logged; the panel shows counts, never a price. No inline style (CSP). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.VCoverage=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const FINANCIAL='FINANCIAL_PROFILE_V_NOT_DEFINED';
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const STATUS=['SUPPLIED','NO_IEX_TRADE','ODD_LOT_ONLY','PRICE_SYMBOL_UNMAPPED','ADR_RATIO_UNCONFIRMED','SPLIT_AFTER_SHARE_COUNT','PRICE_IDENTITY_CONFLICT'];
const frac=(a,b)=>a===null||a===undefined?'—':a+'/'+b;
/* HTML of one publication coverage (c: pub.coverage, or null without a publication). basisHtml: QgvScores.centralHtml of the same
   publication (basis line + IEX attribution); reasonText: QgvScores.reasonText; calc: {calc_version, as_of} of the publication. */
function html(c,{en=false,reasonText=x=>x,basisHtml='',calc=null,reason=null}={}){
 const T=(ko,e)=>en?e:ko,on=!!c,cell=(attr,val)=>'<td'+(attr?' '+attr:'')+'>'+esc(val)+'</td>';
 let h='<section class="card v-coverage" data-v-coverage="'+(on?'READY':'NOT_PUBLISHED')+'"><h2>'+T('V 산출 현황 · 중앙 게시','V coverage · central publication')+'</h2>';
 h+='<p class="small">'+esc(T('공식 V = 중앙 게시본 qgv-official.json · 이 기기는 V를 계산하지 않고 가격을 읽지 않음 · 기기 V로 채우지 않음','Official V = the central publication qgv-official.json · this device computes no V and reads no price for it · never filled with a device V'))+'</p>'+basisHtml;
 if(!on)return h+'<p class="v-coverage-state" data-v-coverage-state="'+esc(reason||'OFFICIAL_NOT_PUBLISHED')+'">'+esc(reasonText(reason||'OFFICIAL_NOT_PUBLISHED')+T(' · V 산출 수 없음',' · no V count'))+'</p></section>';
 const P=c.population,G=P.general,N=P.total,qo=c.qg_only_total;
 h+='<p class="v-coverage-target" data-v-target="'+c.target.n+'" data-v-met="'+(c.target.met?'MET':'NOT_MET')+'">'+esc(T('관찰 지표 · 목표 ','Observation metric · target ')+c.target.n+'/'+G+T(' (일반 기업 90%) · 현재 ',' (90% of general) · now ')+c.v.general+'/'+G+' ('+(c.target.met?T('달성','met'):T('미달','not met'))+')')+'</p>';
 h+='<p class="small" data-v-target-note>'+esc(T('관찰용 지표이며 TARGET 확정 조건에 쓰이지 않습니다 · 수치는 게시본의 coverage','An observation metric, not a TARGET confirmation condition · counts from the publication’s coverage'))+'</p>';
 h+='<ul class="v-coverage-pop" data-v-population><li data-pop-total="'+N+'">'+esc(T('전체 Universe ','All Universe ')+N)+'</li><li data-pop-general="'+G+'">'+esc(T('일반 기업(V 적용) ','General (V applies) ')+G)+'</li><li data-pop-financial="'+P.financial+'">'+esc(T('금융업 · ','Financials · ')+reasonText(FINANCIAL)+' '+P.financial)+'</li><li data-pop-unknown="'+P.unknown+'">'+esc(T('프로필·업종 미확인(자료 없음) ','Profile/industry unknown (no data) ')+P.unknown)+'</li>'+(P.stopped?'<li data-pop-stopped="'+P.stopped+'">'+esc(T('식별 충돌로 사용 중지 ','Stopped: identity conflict ')+P.stopped)+'</li>':'')+'</ul>';
 h+='<div class="v-coverage-table-wrap"><table class="v-coverage-table" data-v-coverage-table><thead><tr><th scope="col">'+T('항목','Item')+'</th><th scope="col">'+esc(T('전체 '+N+' 기준','All '+N))+'</th><th scope="col">'+esc(T('일반 기업 '+G+' 기준','General '+G))+'</th></tr></thead><tbody>';
 h+='<tr data-v-row="v"><th scope="row">'+T('공식 V 있음','Official V present')+'</th>'+cell('data-v-full="'+c.v.full+'"',frac(c.v.full,N))+cell('data-v-general="'+c.v.general+'"',frac(c.v.general,G))+'</tr>';
 h+='<tr data-v-row="qgv"><th scope="row">'+T('Q·G·V 공통 산출','Q·G·V all computed')+'</th>'+cell('data-qgv-full="'+c.qgv.full+'"',frac(c.qgv.full,N))+cell('data-qgv-general="'+c.qgv.general+'"',frac(c.qgv.general,G))+'</tr>';
 h+='<tr data-v-row="qg-only-total"><th scope="row">'+T('Q·G만으로 종합점수가 난 행','Rows with a total from Q·G only')+'</th>'+cell('data-qg-only-full="'+qo.full+'"',qo.full+T(' (금융 ',' (financial ')+qo.financial+T(' · 공식 V 없음 ',' · no official V ')+qo.no_v+')')+cell('data-qg-only-general="'+qo.general+'"',String(qo.general))+'</tr>';
 h+='<tr data-v-row="gate"><th scope="row">'+T('가치 함정 관문으로 V 제외(공식 규칙 · 순위 유지)','V excluded by the value-trap gate (official rule · stays ranked)')+'</th>'+cell('data-gate-full="'+qo.gate+'"',frac(qo.gate,N))+cell('','—')+'</tr>';
 h+='<tr data-v-row="ranked"><th scope="row">'+T('공식 순위 · QG 참고 목록','Official ranks · Q·G reference list')+'</th>'+cell('data-ranked="'+c.ranked+'" data-qg-reference="'+c.qg_reference+'"',c.ranked+' · '+c.qg_reference)+cell('','—')+'</tr>';
 h+='</tbody></table></div>';
 h+='<p class="small" data-v-composition>'+esc(T('전체 '+N+' = 일반 '+G+' + 금융 '+P.financial+' + 미확인 '+P.unknown+(P.stopped?' + 사용 중지 '+P.stopped:'')+' · 금융업은 자료 부족이 아니라 모델 미지원으로 따로 셈','All '+N+' = general '+G+' + financial '+P.financial+' + unknown '+P.unknown+(P.stopped?' + stopped '+P.stopped:'')+' · financials are counted apart as model not supported, not as missing data'))+'</p>';
 const st=Object.entries(c.price_status||{}).sort((x,y)=>STATUS.indexOf(x[0])-STATUS.indexOf(y[0]));
 h+='<p class="small" data-v-price-status>'+esc(T('IEX 가격 상태: ','IEX price status: ')+st.map(([k,n])=>k+' '+n).join(' · '))+'</p>';
 h+='<h3>'+esc(T('공식 V 없음 사유 · 일반 기업 '+c.not_computed+'곳','Why there is no official V · '+c.not_computed+' general companies'))+'</h3><ul class="v-coverage-reasons" data-v-reasons>'+c.reasons.map(([k,n])=>'<li data-v-reason="'+esc(k)+'" data-count="'+n+'"><b>'+n+'</b> · '+esc(k)+' · '+esc(reasonText(k))+'</li>').join('')+'</ul>';
 h+='<details data-v-factor-details><summary>'+T('공식 V 없는 행의 요인별 사유 (한 행이 여러 사유에 들어감)','Factor reasons of those rows (a row can count under several)')+'</summary><ul class="v-coverage-reasons" data-v-factor-reasons>'+c.factor_reasons.map(([k,n])=>'<li data-v-factor-reason="'+esc(k)+'" data-count="'+n+'"><b>'+n+'</b> · '+esc(k)+' · '+esc(reasonText(k))+'</li>').join('')+'</ul></details>';
 h+='<p class="small" data-v-calc-version>'+esc(T('계산 버전 ','Calc version ')+(calc&&calc.calc_version||'—')+(calc&&calc.as_of?T(' · 입력 sec-qgv2.json 기준 ',' · input sec-qgv2.json as of ')+calc.as_of:''))+'</p>';
 return h+'</section>';
}
let painted=null;
/* Paint into host (S06 '#v-coverage-root') from the page's one publication read (QgvScores.pagePublication). Returns the shown
   coverage (or null). */
async function paint(host,{publicScreens={},locale='ko-KR',view=globalThis}={}){
 if(!host)return null;const QS=view.QgvScores,QI=view.Qgv2Inputs,en=locale==='en-US';
 try{
  if(!QS||typeof QS.pagePublication!=='function'){host.innerHTML=html(null,{en,reason:'OFFICIAL_UNAVAILABLE'});painted=null;return null;}
  const R=QS.pagePublication(),pub=R.publication,inputs=QI&&publicScreens?publicScreens[QI.FILE]||null:null,b=QS.centralBasis(pub,{reason:R.reason,v2Inputs:inputs}),key=JSON.stringify([b,locale]);
  if(painted&&painted.host===host&&painted.key===key&&host.querySelector('[data-v-coverage]'))return painted.coverage;
  const open=host.querySelector('[data-v-factor-details]')?.open===true,c=pub?pub.coverage:null;
  host.innerHTML=html(c,{en,reasonText:x=>QS.reasonText(x,en),basisHtml:QS.centralHtml(b,en),calc:pub?{calc_version:pub.calc_version,as_of:pub.inputs[0].as_of}:null,reason:b.reason});
  {const sec=host.querySelector('[data-v-coverage]');if(sec&&typeof QS.readMarks==='function')for(const[k,v]of Object.entries(QS.readMarks(QS.publicationBasis(),view)))sec.setAttribute(k,v);}
  if(open){const d=host.querySelector('[data-v-factor-details]');if(d)d.open=true;}
  painted={host,key,coverage:c};return c;
 }catch(_){return null;}
}
return Object.freeze({html,paint});
});
