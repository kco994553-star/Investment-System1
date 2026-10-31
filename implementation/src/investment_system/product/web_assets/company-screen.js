/* S04 company summary and S05 company analysis (design canvas). Presentation only: no new methodology,
   weights or thresholds. Public inputs are price-free; anything that needs a price or an approval stays
   NOT_AVAILABLE. Industry (SIC group v0) and strategy theme (v0) chips come from classification-screens.js. ACTUAL is read from this device only and is never replaced by TARGET.
   Owner decisions 2026-10-14: QGV v2 is the only score (no v1 comparison or [자세히] v1 reference; a missing v2 shows its
   NOT_AVAILABLE reason); the raw public cards (Q·G leaf scores, price-free types, filing windows) live in Settings >
   원자료 보기(개발자용) (app.js rawDataUI), and the summary carries one next-earnings line (nextEarningsLine).
   Owner decision 2026-10-31 (DC-31, device V abolished): the QGV card shows the central V of qgv-official.json with its basis line and
   IEX attribution; the device value card (2.4.4), the '가치·시나리오' tab and the device price badge are removed. */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.CompanyScreen=api;})(typeof globalThis==='object'?globalThis:this,function(g){
'use strict';
const TYPES=['growth','quality','cyclical','defensive'];
const TYPE_LABEL={growth:['성장','Growth'],quality:['우량','Quality'],cyclical:['경기민감','Cyclical'],defensive:['경기방어','Defensive']};
const TABS=[['summary','종합','Overview'],['business','사업·경쟁','Business'],['financials','재무','Financials'],['events','주가·이벤트','Price / events'],['factors','QGV 요소','QGV factors'],['compare','비교·컨센서스','Compare / consensus']];
const esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tr=locale=>(ko,en)=>locale==='en-US'?en:ko;
const na=(reason,locale)=>'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span>'+(reason?' <span class="small">'+esc(reason)+'</span>':'');
const num=(v,locale,digits=1)=>new Intl.NumberFormat(locale==='en-US'?'en-US':'ko-KR',{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(v);
const fmtPct=(ratio,locale)=>typeof ratio==='number'&&Number.isFinite(ratio)?num(ratio*100,locale)+'%':'—';
const fmtPp=(ratio,locale)=>typeof ratio==='number'&&Number.isFinite(ratio)?(ratio>0?'+':ratio<0?'−':'')+num(Math.abs(ratio)*100,locale)+' %p':'—';
const typeName=(id,locale)=>TYPE_LABEL[id]?TYPE_LABEL[id][locale==='en-US'?1:0]:id;
function record(screens,file,id){const p=screens?.[file];return p&&p.data&&p.data.companies&&Object.hasOwn(p.data.companies,id)?p.data.companies[id]:null;}
// Official mixing rule of type_config/1 (minimum_membership, maximum_types, exclusive_pairs, CONFIG_ORDER tie-break).
function selectTypes(memberships,config=g.TypeConfigDefaults){
 const mix=config&&config.mixing;if(!mix||!memberships)return null;
 const order=config.types.map(t=>t.id);
 const candidates=TYPES.filter(id=>typeof memberships[id]==='number'&&memberships[id]>=mix.minimum_membership).sort((a,b)=>memberships[b]-memberships[a]||order.indexOf(a)-order.indexOf(b));
 const out=[];for(const id of candidates){if(out.length>=mix.maximum_types)break;if(mix.exclusive_pairs.some(([x,y])=>(id===x&&out.includes(y))||(id===y&&out.includes(x))))continue;out.push(id);}
 return out;
}
function classification(screens,id,locale){
 const CS=g.ClassificationScreens,cls=CS&&screens?screens[CS.FILE]:null,T=tr(locale),rec=record(screens,'company-types-pricefree.json',id),picked=rec&&rec.state!=='NOT_AVAILABLE'?selectTypes(rec.memberships):null;
 const items=[['industry',T('산업','Industry'),CS?CS.industryChip(cls,id,locale):na('',locale)],
  ['theme',T('전략 테마','Strategy theme'),CS?CS.themeChip(cls,id,locale):na('',locale)],
  ['type',T('투자 유형','Investment type'),picked&&picked.length?picked.map(t=>'<span class="badge LIVE" data-type-chip="'+esc(t)+'">'+esc(typeName(t,locale))+' '+esc(num(rec.memberships[t],locale,2))+'</span>').join(' ')+' <span class="small">'+esc(T('소속도 0.3 이상','membership ≥ 0.3'))+'</span>'
   :na(rec?T('소속도 0.3 이상 유형 없음 또는 자료 없음','No type with membership ≥ 0.3, or no data'):T('공개 유형 자료가 연결되지 않았습니다.','Public type data is not connected.'),locale)]];
 return '<section class="card" data-company-card="classification"><h2>'+esc(T('분류 3축','Three classification axes'))+'</h2><ul class="axis-chips">'+items.map(([k,name,body])=>'<li data-axis="'+k+'"><b>'+esc(name)+'</b> '+body+'</li>').join('')+'</ul><p class="small">'+esc(T('산업 / 전략 테마 / 투자 유형은 서로 다른 축입니다. 서로 대신 채우지 않습니다.','Industry / strategy theme / investment type are separate axes. None substitutes for another.'))+'</p></section>';
}
function dataBadges(screens,locale,withPit,sr=null){
 const T=tr(locale),p=screens?.['sec-qg-factors.json'],state=p?p.state:'NOT_AVAILABLE',aged=p&&state!=='NOT_AVAILABLE'&&Date.now()-Date.parse(p.as_of)>p.stale_after_seconds*1000,v2AsOf=sr&&sr.S?sr.S.v2_as_of:null;
 // Score time = sec-qgv2.json as_of (v2). sec-qg-factors.json is labelled as the v1 PREVIEW input only (its existing STALE rule unchanged).
 // Its aged badge names its input (D4, 2026-10-18): a bare 'STALE' beside the v2 score time read as if the v2 score were old.
 return '<div class="chips data-badges" data-company-badges><span class="badge" data-score-as-of="'+(v2AsOf?'v2':'NOT_AVAILABLE')+'">'+esc(T('점수 기준 ','Score as of ')+(v2AsOf||'NOT_AVAILABLE'))+'</span><span class="badge" data-scoring-default="v2">'+esc(sr&&g.QgvScores?g.QgvScores.basisText(sr.S,locale==='en-US'):T('점수 기준 v2 · PROVISIONAL','Score basis v2 · PROVISIONAL'))+'</span>'
  +'<span class="badge '+esc(state)+'" data-badge="data" data-v1-preview-as-of>'+esc(T('v1 미리보기 입력 ','v1 PREVIEW input ')+state+' · '+(p?T('기준 ','as of ')+p.as_of:T('기준 시각 없음','no as-of')))+'</span>'+(aged?'<span class="badge freshness STALE" data-v1-input-stale>'+esc(T('v1 입력 STALE','v1 input STALE'))+'</span>':'')
  +(withPit?'<span class="badge" data-badge="pit">'+esc('PIT '+(p&&p.data.availability_basis?p.data.availability_basis:'NOT_AVAILABLE'))+'</span>':'')+'</div>';
}
/* The one next-earnings line of the company summary: '다음 실적 MM/DD경 (확정 아님) · D-n'. Source: the same SEC filing-timing
   pattern (sec-filing-windows.json -> PublicScreens.earningsStatus / nextFilingWindow) as the leaderboard 'next_window' column.
   MM/DD is the START of the next estimated 10-Q/10-K filing window and D-n counts days to that start (D-0 while the window is
   open). When the current quarter's release is already confirmed (8-K Item 2.02), the line shows the following window (searched
   from 45 days after the release). No pattern -> '다음 실적 확인 불가'. Never a confirmed date. */
function nextEarningsLine(screens,id,locale,now=new Date()){
 const T=tr(locale),PS=g.PublicScreens,rec=record(screens,'sec-filing-windows.json',id);let w=null;
 if(rec&&rec.state!=='NOT_AVAILABLE'&&PS&&PS.earningsStatus&&PS.nextFilingWindow){const s=PS.earningsStatus(rec,now);
  if(s&&s.status==='ESTIMATED')w=s.window;
  else if(s&&s.status==='CONFIRMED'){const day=d=>Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate()),after=new Date(Date.parse(s.date+'T00:00:00Z')+45*864e5),base=after>now?after:now,n=PS.nextFilingWindow(rec,base);
   if(n)w={...n,days_until_start:n.days_until_start+Math.round((day(base)-day(now))/864e5)};}}
 if(!w)return '<p class="next-earnings" data-next-earnings-line="NOT_AVAILABLE">'+esc(T('다음 실적 확인 불가','Next earnings not available'))+'</p>';
 return '<p class="next-earnings" data-next-earnings-line="ESTIMATED">'+esc(T('다음 실적 ','Next earnings ~')+w.start.replace('-','/')+T('경 (확정 아님) · D-',' (not confirmed) · D-')+w.days_until_start)+'</p>';
}
function nextEarnings(screens,id,locale){
 const T=tr(locale),rec=record(screens,'sec-filing-windows.json',id),s=rec&&g.PublicScreens&&g.PublicScreens.earningsStatus?g.PublicScreens.earningsStatus(rec):null;
 if(s&&s.status==='CONFIRMED')return '<span class="badge LIVE" data-earnings-status="CONFIRMED">'+esc(T('확인','Confirmed'))+'</span> <span data-next-earnings>'+esc(s.date)+'</span> <span class="small">'+esc(T('실적 발표 · SEC 8-K Item 2.02','Earnings release · SEC 8-K Item 2.02'))+'</span>';
 const w=s&&s.status==='ESTIMATED'?s.window:null;
 if(!w)return na(T('공시 시기 패턴 자료 없음','No filing-timing pattern'),locale);
 return '<span class="badge" data-earnings-status="ESTIMATED">'+esc(T('추정','Estimated'))+'</span> <span data-next-earnings>'+esc(w.form+' '+w.start+'–'+w.end+' · D-'+w.days_until_start)+'</span> <span class="small">'+esc(T('예상 시기 · 확정일 아님','Estimated timing · not a confirmed date'))+'</span>';
}
// Scores only through QgvScores (the scoring_default setting): ctx.scores from the app, else computed here (no device quotes).
function scoreRow(ctx){const QS=g.QgvScores;if(!QS||!ctx)return null;let S=ctx.scores||null;try{if(!S)S=QS.compute({identities:[{company_id:ctx.id,ticker:ctx.ticker||''}],publicScreens:ctx.screens||{}});}catch(_){return null;}
 const row=S&&S.rows?S.rows[ctx.id]:null;return row?{S,row}:null;}
const V2_LABEL={q_profitability:['수익성','Profitability'],q_moat_proxy:['해자 대리','Moat proxy'],q_earnings_quality:['이익의 질','Earnings quality'],q_financial_safety:['재무 안전','Financial safety'],q_capital_allocation:['자본 배분(경영진 대리)','Capital allocation'],
 g_revenue_growth:['매출 성장','Revenue growth'],g_per_share_growth:['주당 이익·FCF 성장','Per-share earnings / FCF growth'],g_growth_efficiency:['성장 효율','Growth efficiency'],g_consistency:['성장 일관성','Growth consistency'],g_recent_acceleration:['최근 가속','Recent acceleration'],
 v_earnings_yield:['이익 수익률 (EBIT/EV)','Earnings yield (EBIT/EV)'],v_fcf_yield:['FCF 수익률 (FCF/EV)','FCF yield (FCF/EV)'],v_vs_industry:['업종 대비 (EV/EBIT 업종 백분위)','Vs industry (EV/EBIT industry percentile)'],v_vs_own_history:['자기 과거 대비 (5년)','Vs own history (5y)'],v_expectation_check:['기대 점검 (역DCF − 실현 성장)','Expectation check (reverse DCF − realized growth)']};
function flagsHtml(d,locale){const QS=g.QgvScores;return QS&&d?QS.flagText(d.flags,locale==='en-US',d).map(f=>' <span class="badge STALE" data-qgv2-flag>'+esc(f)+'</span>').join(''):'';}
/* QGV menu layout (design lane D2; owner draft "손그림 칠판", function numbers 2.4.1–2.4.5 of 2.4 QGV 상세; the menu strip keeps 1 / 1.1).
   Presentation only: the same values, attributes and links; numbered stamp headings, Q·G·V bars and the radar moved next to the
   QGV card. 2.4.1–2.4.4 names are the layout's grouping (provisional until the owner confirms); 2.4.5 = 기업 비교 레이더. */
const FN24={total:['2.4.1','종합 점수와 Q·G·V','Total and Q·G·V'],rank:['2.4.2','순위와 쓰임','Rank and use'],status:['2.4.3','산출 상태와 근거','Calculation status and sources'],radar:['2.4.5','기업 비교 레이더','Company comparison radar']};
function fnHead(key,locale,tag='h3'){const[n,ko,en]=FN24[key];return '<'+tag+' class="fn-head" id="cs-fn-'+n.replaceAll('.','-')+'"><span class="ia-sec">'+n+'</span> <span class="fn-title">'+esc(locale==='en-US'?en:ko)+'</span></'+tag+'>';}
function fnSec(key,locale,body){const n=FN24[key][0];return '<section class="fn-sec" data-fn="'+n+'" aria-labelledby="cs-fn-'+n.replaceAll('.','-')+'">'+fnHead(key,locale)+body+'</section>';}
/* Q·G·V bars (decoration: aria-hidden; the numbers are in the data-qgv cells next to them). SVG width attributes, no inline style
   (CSP style-src 'self'). A missing axis is an empty dashed track, never a 0 bar. */
function qgvBarsHtml(d){if(!d||![d.q,d.g,d.v].some(v=>typeof v==='number'&&Number.isFinite(v)))return '';const bar=(a,v)=>{const ok=typeof v==='number'&&Number.isFinite(v),w=ok?Math.max(0.5,Math.max(0,Math.min(100,v))*0.99):0;
  return '<span class="qb" data-axis="'+a+'" data-state="'+(ok?'OK':'NA')+'"><svg viewBox="0 0 100 10" preserveAspectRatio="none" focusable="false"><rect class="qb-track" x="0.5" y="1" width="99" height="8" rx="2"/>'+(ok?'<rect class="qb-fill" x="0.5" y="1" width="'+w.toFixed(2)+'" height="8" rx="2"/>':'')+'</svg></span>';};
 return '<span class="qgv-bars qgv-bars-l" aria-hidden="true" data-qgv-bars>'+bar('Q',d.q)+bar('G',d.g)+bar('V',d.v)+'</span>';}
function v2Body(d,locale){
 const T=tr(locale),cell=(v,attr,note='')=>'<dd data-qgv="'+attr+'">'+(typeof v==='number'?'<span class="num">'+esc(num(v,locale))+'</span>':na('',locale))+(note?' '+note:'')+'</dd>';
 const reference=d?.reference_only?'<p class="badge partial" data-qgv2-reference>'+esc(T('참고 순위 · 미국 504종목과 같은 계산, 정식 순위 아님','Reference ranking · same calculation as US504, not an official rank'))+'</p>':'';
 const QS=g.QgvScores,why=QS&&QS.naText?QS.naText(d,locale==='en-US'):'SEC_QGV2_NOT_AVAILABLE';
 // v2 NOT_AVAILABLE: the reason in words (factors n/total, axis below 50%). Never a v1 fallback. A row whose V was computed
 // (Q and G below 50%) still shows that V, as S06, the Universe page and the radar do ('V 일치', owner 2026-10-19).
 if(!d||d.state==='NOT_AVAILABLE'&&d.q===null&&d.g===null&&!Number.isFinite(d.v))return reference+'<dl class="kv"><dt>QGV v2</dt><dd data-qgv="total">'+na('',locale)+'</dd><dt>Q</dt><dd data-qgv="Q">'+na('',locale)+'</dd><dt>G</dt><dd data-qgv="G">'+na('',locale)+'</dd><dt>V</dt><dd data-qgv="V">'+na('',locale)+'</dd></dl><p class="small" data-qgv2-na>'+esc(why)+'</p>';
 const rr=d.reference_range,range=rr&&rr.state!=='NOT_AVAILABLE'?esc(num(rr.low,locale,2)+' ~ '+num(rr.high,locale,2)):na(rr?rr.reason:'',locale);
 return reference+'<dl class="kv"><dt>QGV v2</dt>'+cell(d.total,'total')+'<dt>Q</dt>'+cell(d.q,'Q')+'<dt>G</dt>'+cell(d.g,'G')+'<dt>V</dt>'+cell(d.v,'V',QS&&QS.lastTradeHtml?QS.lastTradeHtml(d,locale==='en-US'):'')+'</dl>'
  +(d.total===null?'<p class="small" data-qgv2-na>'+esc(why)+'</p>':'')
  +'<p class="small" data-qgv2-summary>'+esc(T('산출 요인 ','Factors available ')+d.factors_available+'/'+d.factors_total+(d.profile?' · '+d.profile.id:''))+flagsHtml(d,locale)+'</p>'
  +(d.v_excluded?'<p class="small" data-qgv2-gate>'+esc(T('가치 함정 주의: Q가 업종 내 하위 30%라 V를 총점에서 뺐습니다.','Value-trap caution: Q is in the bottom 30% of its industry, so V is left out of the total.'))+'</p>':'')
  +'<p class="small" data-qgv2-range>'+esc(T('DCF 참고 범위 (점수 미반영 · FCF/주 · 성장률 규칙 하한~상한): ','DCF reference range (not scored · FCF/share · growth-rule lower~upper): '))+range+'</p>';
}
/* FE-MISSING-2 (owner instruction 2026-10-17): per axis, whether it was calculated (정상 / 부분 산출 / 미산출 / 해당 없음 /
   사용 중지), its fill rate against the ORIGINAL weights ('충족률 80% · 4/5 요인'), each missing factor with a sentence (raw code
   under 근거), the weights before and after the engine's renormalization (QgvV2.WEIGHTS through QgvScores.coverageFor), whether
   it counts in the total and whether the company is used for the device rank / candidates. Data states and source facts
   (fiscal period, SEC companyfacts, acquired_at, used now or not) come from the published row. Nothing is estimated and an NA
   factor never shows 0. compact (S04): one line per axis, the factor list folded; S05 shows the per-factor table instead. */
const dayOf=x=>typeof x==='string'?x.slice(0,10):null;
function clockText(x){return typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(x)?x.slice(0,10)+' '+x.slice(11,16)+' UTC':'—';}
function pctText(ratio,locale,digits=0){return typeof ratio==='number'&&Number.isFinite(ratio)?num(ratio*100,locale,digits)+'%':'—';}
const AXIS_BADGE={READY:'LIVE',PARTIAL:'partial',NOT_AVAILABLE:'NOT_AVAILABLE',NOT_APPLICABLE:'NOT_AVAILABLE',STOPPED:'NOT_AVAILABLE'};
function factorShare(f,axis,locale){const T=tr(locale);return T('원래 ','original ')+num(f.weight,locale,0)+'% → '+(f.share!==null?T('재배분 ','renormalized ')+num(f.share,locale,1)+'%':axis.score===null?T('재배분 안 함','not renormalized'):T('제외','left out'));}
function evidence(body,locale){return '<details class="evidence" data-evidence><summary>'+esc(tr(locale)('근거','Evidence'))+'</summary><p class="small">'+body+'</p></details>';}
function factorEvidence(f,locale){const T=tr(locale),parts=[];if(f.raw)parts.push(T('계산 코드 ','Engine code ')+'<code>'+esc(f.raw)+'</code>');if(f.reason&&f.reason!==f.raw)parts.push(T('화면 분류 ','Screen class ')+'<code>'+esc(f.reason)+'</code>');
 if(f.metrics&&f.metrics.length)parts.push(T('하위 지표 ','Sub-metrics ')+f.metrics.map(m=>'<code>'+esc(m)+'</code>').join(', '));if(f.basis)parts.push(T('비교 기준 ','Basis ')+esc(f.basis));return parts.join(' · ')||'—';}
function useText(a,locale){const T=tr(locale);return {INCLUDED:T('종합 점수에 반영','Counted in the total'),TOTAL_NOT_AVAILABLE:T('종합 점수 미산출','No total score'),AXIS_NOT_AVAILABLE:T('이 축은 종합 점수에 반영 안 됨','Not counted in the total'),VALUE_TRAP_GATE:T('가치 함정 관문으로 종합 점수에서 제외','Left out of the total by the value-trap gate')}[a.use]||'—';}
function axisCoverageHtml(a,cv,locale,compact){
 const T=tr(locale),en=locale==='en-US',QS=g.QgvScores,V2L=f=>V2_LABEL[f.id]?V2_LABEL[f.id][en?1:0]:f.id;
 const fill=a.status==='NOT_APPLICABLE'||a.status==='STOPPED'?'':T('충족률 ','Fill ')+pctText(a.weight_available,locale)+' · '+a.factors_available+'/'+a.factors_total+T(' 요인',' factors')+(a.not_applicable&&a.status!=='NOT_APPLICABLE'?T(' (해당 없음 ',' (not applicable ')+a.not_applicable+T('개 제외)',' excluded)'):'');
 const head='<div class="axis-head"><b>'+esc(a.axis)+'</b> <span class="badge '+AXIS_BADGE[a.status]+'" data-axis-status-label>'+esc(QS.axisStatusText(a.status,en))+'</span>'+(a.score!==null?' <span class="num">'+esc(num(a.score,locale))+'</span>':'')+(fill?' <span class="small" data-axis-fill>'+esc(fill)+'</span>':'')+'</div>';
 const why=a.reason?'<p class="small" data-axis-reason>'+esc(QS.reasonText(a.reason,en))+'</p>':'';
 const use='<p class="small" data-axis-use>'+esc(useText(a,locale))+'</p>';
 const missing=a.factors.filter(f=>f.score===null);
 let list='';if(compact){
  list='<ul class="factor-coverage">'+a.factors.map(f=>'<li data-factor-coverage="'+esc(f.id)+'" data-factor-state="'+esc(f.category)+'"><span><b>'+esc(V2L(f))+'</b> <span class="small">'+esc(factorShare(f,a,locale))+'</span></span>'
   // A factor missing for the axis' own reason (e.g. no device price) names only its state; the sentence is on the axis line.
   +(f.score===null?' <span class="badge '+(f.category==='NOT_APPLICABLE'?'NOT_AVAILABLE':'partial')+'">'+esc(QS.stateText(f.category,en))+'</span>'+(a.reason&&f.reason===a.reason?'':'<span class="small" data-factor-reason>'+esc(QS.reasonText(f.reason,en))+'</span>'+evidence(factorEvidence(f,locale),locale)):' <span class="small">'+esc(T('점수 ','score ')+num(f.score,locale))+'</span>')+'</li>').join('')+'</ul>';}
 const pub=a.published,pubText=pub?esc(T('공개 파일 축 정보: ','Published axis: ')+'factors_available '+(pub.factors_available??'—')+' · available_weight '+(pub.available_weight??'—')+' · '+T('비교 기준 ','peer basis ')+(pub.peer_basis??'—')+(Number.isInteger(pub.peer_count)?' ('+pub.peer_count+T('곳)',')'):'')+' · '+T('대체 순위 ','sub-metric fallbacks ')+(pub.submetric_fallbacks??'—')+' · reason_codes '+(pub.reason_codes.length?pub.reason_codes.join(', '):'—')):'';
 let vline='';if(a.axis==='V'&&a.status!=='NOT_APPLICABLE'&&a.status!=='STOPPED'&&cv.source&&cv.source.state!=='NOT_AVAILABLE'){const miss=cv.v_inputs_missing,per=Object.entries(cv.v_periods||{}).map(([k,v])=>k+' '+v).join(' · ');
  vline='<p class="small" data-v-inputs="'+(miss.length?'MISSING':'OK')+'">'+esc(miss.length?T('가격 외 V 입력 중 없는 항목: ','Price-free V inputs missing: ')+miss.map(k=>QS.vInputText(k,en)).join(' · '):T('가격 외 V 입력(SEC)은 모두 있습니다. 가격이 들어오면 계산합니다.','All price-free V inputs (SEC) are present; V is calculated once a price is available.'))+'</p>'+(per?evidence(esc(T('V 입력 기준기간: ','V input periods: ')+per),locale):'');}
 const renorm=a.score!==null&&missing.some(f=>f.category!=='NOT_APPLICABLE'||a.not_applicable)?'<p class="small" data-axis-renorm>'+esc(T('재배분: 있는 요인의 원래 가중치 비율대로 나눠 계산합니다 (Σ가중치×점수 ÷ Σ있는 요인 가중치). 빠진 요인을 0으로 채우지 않습니다.','Renormalized: present factors keep their original weight ratio (Σ weight×score ÷ Σ present weights). Missing factors are not filled with 0.'))+'</p>':'';
 const body=list+renorm+vline+(pubText?evidence(pubText,locale):'');
 return '<li data-axis-coverage="'+a.axis+'" data-axis-status="'+a.status+'">'+head+why+use+(compact&&body?'<details data-keep-open="axis-'+a.axis+'"><summary>'+esc(missing.length?T('빠진 요인·가중치 재배분','Missing factors and weights'):T('요인·가중치','Factors and weights'))+'</summary>'+body+'</details>':body)+'</li>';
}
/* Data-state chips + per-axis coverage + device-use and source lines of one score row (sr from scoreRow). */
function qgRefOf(sr){const QS=g.QgvScores;if(!sr||!sr.row||!QS||!QS.qgReference)return null;return sr.row.qg_reference||(QS.qgReference(sr.row.primary)?{order:null,...QS.qgReference(sr.row.primary)}:null);}
// 'QG 참고 목록 (V 미포함) · 2번 · 공식 QGV 순위 아님 · <V reason in words>'.
function qgRefText(ref,QS,en){return QS.QG_REFERENCE_LABEL[en?1:0]+(ref.order?' · '+(en?'#'+ref.order:ref.order+'번'):'')+(en?' · not an official QGV rank':' · 공식 QGV 순위 아님')+(ref.reason?' · '+QS.reasonText(ref.reason,en):'');}
function coverageHtml(sr,locale,{compact=true}={}){
 const T=tr(locale),en=locale==='en-US',QS=g.QgvScores,d=sr?sr.row.primary:null,cv=d&&d.coverage?d.coverage:null;
 if(!QS||!QS.coverageFor||!cv)return '';
 const src=cv.source,stale=src&&src.state==='STALE';
 const chips=cv.states.map(st=>'<span class="badge '+(st==='NOT_APPLICABLE'?'NOT_AVAILABLE':st==='STALE'?'freshness STALE':'partial')+'" data-data-state="'+esc(st)+'">'+esc(QS.stateText(st,en)+(st==='STALE'&&src?T(' · 마지막 유효 값 기준 FY ',' · last valid value FY ')+(src.fiscal_year_end||'—')+T(' · 수집 ',' · collected ')+(dayOf(src.acquired_at)||'—'):'')+(st==='SOURCE_MISSING'&&src&&src.reason_codes.length?' · '+src.reason_codes.join(', '):''))+'</span>').join('');
 const states='<p class="chips" data-data-states>'+(chips||'<span class="badge LIVE" data-data-state="OK">'+esc(T('자료 정상','Data complete'))+'</span>')+'</p>';
 const axes=cv.axes?'<ul class="axis-coverage">'+['Q','G','V'].map(a=>axisCoverageHtml(cv.axes[a],cv,locale,compact)).join('')+'</ul>':'';
 // D11: a total from Q·G only (V not applicable / not computed) is in the QG 참고 목록 (V 미포함), never the official device rank.
 const rank=sr.row.rank,qgRef=rank===null?qgRefOf(sr):null;
 const usable=qgRef?'<p class="small" data-qgv-usable="QG_REFERENCE">'+esc(T('순위: ','Rank: ')+qgRefText(qgRef,QS,en))+'</p>':'<p class="small" data-qgv-usable="'+(rank!==null?'RANKED':'EXCLUDED')+'">'+esc(T('순위·후보: ','Rank / candidates: ')+(rank!==null?T('사용 (순위 ','used (rank ')+rank+')':d.reference_only?T('참고 순위 · 정식 순위·후보 아님','reference ranking · not an official rank or candidate'):T('제외 · ','excluded · ')+(d.total_reason==='PRICE_IDENTITY_CONFLICT'?QS.FLAG.PRICE_IDENTITY_CONFLICT[en?1:0]:T('QGV 종합 점수가 없어 순위·후보에 넣지 않습니다','no QGV total, so no rank or candidate place'))))+'</p>';
 const used=!src?T('미반영','Not used'):src.state==='LIVE'?T('반영','Used'):src.state==='STALE'?T('반영 · 오래된 자료(마지막 유효 값)','Used · stale (last valid value)'):src.state==='WITHDRAWN'?T('미반영 · 식별 충돌로 사용 중지','Not used · stopped: identity conflict'):T('미반영 · 자료 없음','Not used · no data');
 const mismatch=cv.states.includes('CALC_VERSION')?T('미반영 · 계산 규칙 버전 다름','Not used · different calculation-rule version'):null;
 const source=src?'<dl class="kv" data-qgv-source="'+esc(src.state)+'"><dt>'+esc(T('기준기간','Fiscal period'))+'</dt><dd data-source-period>'+esc(src.fiscal_year_end?'FY '+src.fiscal_year_end:'—')+'</dd><dt>'+esc(T('출처','Source'))+'</dt><dd>'+esc(T('SEC companyfacts (공개 sec-qgv2.json)','SEC companyfacts (public sec-qgv2.json)'))+'</dd><dt>'+esc(T('수집 시각','Collected at'))+'</dt><dd data-source-acquired>'+esc(clockText(src.acquired_at))+'</dd><dt>'+esc(T('현재 계산 반영','Used in the current calculation'))+'</dt><dd data-source-used>'+esc(mismatch||used)+(stale?' <span class="badge freshness STALE">STALE</span>':'')+'</dd></dl>':'';
 return '<div class="qgv-coverage" data-qgv-coverage><h3>'+esc(T('산출 상태','Calculation status'))+'</h3>'+states+axes+usable+source+'</div>';
}
// QGV v2 only (owner decision 2026-10-14). Without the accessor the v2 NOT_AVAILABLE state is shown, never v1.
function qgvBody(screens,id,locale,sr=null){return v2Body(sr?sr.row.primary:null,locale)+provenanceHtml(sr,locale)+centralLine(screens,locale);}
/* DC-31: the central V basis under the QGV values: '공식 V · 중앙 게시 · IEX 마지막 체결가 기준(공식 종가 아님) · 가격 기준일 · 게시 시각
   (· STALE)' and the IEX attribution with its terms link (QgvScores.centralHtml of the page's one publication read); without a
   publication the reason in words. Never a device V. */
function centralLine(screens,locale){const QS=g.QgvScores;if(!QS||typeof QS.centralHtml!=='function')return '';const P=QS.pagePublication();
 return '<div data-qgv-central>'+QS.centralHtml(QS.centralBasis(P.publication,{reason:P.reason,v2Inputs:screens?screens['sec-qgv2.json']||null:null}),locale==='en-US')+'</div>';}
/* Provenance of the shown QGV total (QgvScores.provenance): '공식 가중치 · 가격 없음 · 중앙 게시(qgv-official.json)' on the official
   result of the central publication, '개인 프리셋(…) · …' on any other S06 preset or with the gate off (D11: a personal result says
   개인). No device price goes into any shown value (DC-31). Labels only. */
function provenanceOf(sr){const QS=g.QgvScores,d=sr?sr.row.primary:null;return d&&!d.reference_only&&typeof d.total==='number'&&QS&&typeof QS.provenance==='function'?QS.provenance({profile:d.profile||(sr.S&&sr.S.profile)||null,central:!!sr.S&&sr.S.source==='PUBLICATION'}):null;}
function provenanceHtml(sr,locale){const x=provenanceOf(sr),T=tr(locale);return x?'<p class="small" data-qgv-provenance="COMPANY"'+g.QgvScores.provenanceAttrHtml(x)+'>'+esc(T('QGV 계산 근거: ','QGV basis: ')+g.QgvScores.provenanceText(x,locale==='en-US'))+'</p>':'';}
// Rank scope of an officially split result: 'Universe 공식 QGV 순위 · 12개 중 · 공식 가중치 · …' or '개인 프리셋 순위 (Universe 기준) · …'.
function rankScopeText(sr,locale){const QS=g.QgvScores,en=locale==='en-US',x=provenanceOf(sr),label=QS&&typeof QS.rankLabel==='function'?QS.rankLabel(sr.S.profile,en):(en?'Official Universe QGV rank':'Universe 공식 QGV 순위');
 return label+(en?' · of '+sr.S.official.ranked:' · '+sr.S.official.ranked+'개 중')+' · '+(x?QS.provenanceText(x,en):(en?'no total':'종합 점수 없음'));}
function holdingPlaceholder(locale){
 const T=tr(locale);
 return '<h2>'+esc(T('내 보유','My holding'))+'</h2><p>'+na(T('공개 카탈로그를 불러오는 중이거나 이 기업이 TARGET에 없습니다.','Loading the public catalog, or this company is not in TARGET.'),locale)+'</p><a href="#actual">'+esc(T('ACTUAL 입력·관리 →','Enter / manage ACTUAL →'))+'</a>';
}
function holdingHtml({locale,catalog,inst,ram}){
 const T=tr(locale),theme=catalog.themes.find(x=>x.theme_id===inst.theme_id),target=inst.target_units/catalog.total_units;
 const row=ram&&ram.state==='AVAILABLE'?ram.rows.find(r=>r.ticker===inst.ticker&&Number.isFinite(r.weight)):null;
 const why=!ram||ram.state==='NOT_AVAILABLE'&&ram.reason==='NO_ACTUAL'?T('기기에 보유가 없습니다','No holdings on this device'):T('시세가 부족해 평가할 수 없습니다','Not enough quotes to value');
 return '<h2>'+esc(T('내 보유','My holding'))+'</h2><dl class="kv"><dt>'+esc(T('전략 테마','Strategy theme'))+'</dt><dd data-holding="theme">'+esc(locale==='en-US'?theme.label_en:theme.label)+'</dd>'
  +'<dt>TARGET · '+esc(catalog.target_root_version)+'</dt><dd data-holding="target">'+esc(fmtPct(target,locale))+'</dd>'
  +'<dt>ACTUAL</dt><dd data-holding="actual">'+(row?esc(fmtPct(row.weight,locale)):'— <span class="small">NOT_AVAILABLE</span>')+'</dd>'
  +'<dt>'+esc(T('차이','Gap'))+'</dt><dd data-holding="delta">'+(row?esc(fmtPp(row.weight-target,locale)):'—')+'</dd></dl>'
  +'<p class="small">'+esc(row?T('ACTUAL은 이 기기의 보유·시세로만 계산합니다(RAM).','ACTUAL is computed only from this device (RAM).'):T('ACTUAL 없음: ','ACTUAL unavailable: ')+why+T(' · TARGET으로 채우지 않습니다.',' · TARGET is not used as a substitute.'))+'</p><a href="#actual">'+esc(T('ACTUAL 입력·관리 →','Enter / manage ACTUAL →'))+'</a>';
}
async function mountHolding(host,{locale,ticker,catalogPromise,actual=g.DeviceActual,view=g}){
 if(g.StatRadar&&host)void g.StatRadar.mount(host.ownerDocument,{catalogPromise});  // the summary's stat window: V from the shared page result, price axes in RAM (stat-radar.js)
 if(!host)return;let catalog=null;try{catalog=await catalogPromise;}catch(_){}
 if(!host.isConnected)return;
 const inst=catalog&&ticker?catalog.instruments.find(i=>i.ticker===ticker):null;
 if(!inst){host.innerHTML=holdingPlaceholder(locale);return;}
 let ram=null;try{ram=actual&&actual.ramView?await actual.ramView(view,catalog):null;}catch(_){ram=null;}
 if(host.isConnected)host.innerHTML=holdingHtml({locale,catalog,inst,ram});
}
function summary(ctx){
 const{locale,id,screens}=ctx,T=tr(locale),link=(href,text,attr='')=>'<a href="'+href+'"'+attr+'>'+esc(text)+'</a>',cid=encodeURIComponent(id);
 const sr=scoreRow(ctx);
 return ctx.headerHtml+dataBadges(screens,locale,false,sr)+nextEarningsLine(screens,id,locale)
  +'<p class="small" data-price-na>'+esc(T('현재가·일간 등락','Price and daily move'))+' '+na(T('공개 파일에 가격 없음','Public files carry no prices'),locale)+'</p>'
  +classification(screens,id,locale)
  +'<section class="card" id="company-holding" data-company-card="holding">'+holdingPlaceholder(locale)+'</section>'
  +'<div id="company-groups">'+ctx.groupsHtml+'</div>'
  +'<section class="card qgv-detail" data-company-card="qgv" data-fn="2.4"><h2><span class="flow-number">1</span> QGV <span class="small fn-legend" data-fn-legend="2.4">'+esc(T('기능 2.4 QGV 상세','Function 2.4 QGV detail'))+'</span></h2>'+fnSec('total',locale,qgvBarsHtml(sr?sr.row.primary:null)+qgvBody(screens,id,locale,sr))
  +fnSec('rank',locale,'<dl class="kv" data-cx-company'+(sr&&g.QgvScores&&typeof g.QgvScores.marks==='function'?g.QgvScores.markAttrs(g.QgvScores.marks(sr.row,ctx.priceBasis||null,g)):'')+'><dt>'+esc(T('리더보드 순위','Leaderboard rank'))+'</dt><dd data-qgv="rank">'+(qgRefOf(sr)&&sr.row.rank===null?'<span class="small" data-qgv-rank="QG_REFERENCE" data-qg-order="'+esc(qgRefOf(sr).order===null?'':String(qgRefOf(sr).order))+'">'+esc(qgRefText(qgRefOf(sr),g.QgvScores,locale==='en-US'))+'</span>':sr&&sr.row.rank!==null?'<span class="num">'+esc(String(sr.row.rank))+'</span> <span class="small" data-qgv-rank-scope="'+(sr.S&&sr.S.official?'UNIVERSE':'IDENTITIES')+'"'+(provenanceOf(sr)?g.QgvScores.provenanceAttrHtml(provenanceOf(sr)):'')+'>'+esc(sr.S&&sr.S.official?rankScopeText(sr,locale):T('표시 순서 · 공식 순위 아님','Display order · not an official rank'))+'</span>':sr&&sr.row.outside_universe?'<span class="small" data-qgv-rank="OUTSIDE_UNIVERSE">'+esc(T('Universe 밖 TARGET · 공식 순위 대상 아님','TARGET outside the Universe · not in the official ranking'))+'</span>':na('',locale))+'</dd><dt>'+esc(T('재평가 신호','Re-evaluation signal'))+'</dt><dd data-qgv="reeval">'+na('',locale)+'</dd></dl>')+fnSec('status',locale,coverageHtml(sr,locale,{compact:true})
  +'<p>'+link('#analysis/'+cid+'/factors',T('QGV 요소 자세히 보기 →','Open QGV factors →'),' data-analysis-link="factors"')+'</p>')+'</section>'
  +(g.StatRadar?'<section class="card" data-company-card="radar" data-fn="2.4.5">'+fnHead('radar',locale,'p')+g.StatRadar.html({targetId:id},{screens,locale})+'</section>':'')
  +'<section class="card" data-company-card="technical"><h2><span class="flow-number">2</span> '+esc(T('기술','Technical'))+'</h2><div id="private-history-chart"></div><div id="tradingview-mini" data-company-tradingview></div><dl class="kv"><dt>'+esc(T('상태·국면','State / regime'))+'</dt><dd>'+na('',locale)+'</dd></dl><p>'+link('#technical/'+cid,T('기술적 분석에서 이어 보기 →','Continue in technical analysis →'))+'</p></section>'
  +'<section class="card" data-company-card="macro"><h2><span class="flow-number">3</span> '+esc(T('매크로 영향','Macro impact'))+'</h2><p>'+na(T('시장 국면·업종 영향·종목 영향이 아직 검증되지 않았습니다.','Market regime, industry and company impact are not yet validated.'),locale)+'</p><p>'+link('#macro',T('매크로 보기 →','Open macro →'))+'</p></section>'
  +'<section class="card" data-company-card="news"><h2>'+esc(T('뉴스·관계','News / relations'))+'</h2><p>'+na(T('공개 뉴스·관계망 자료가 연결되지 않았습니다.','No public news or relationship data connected.'),locale)+'</p><p>'+link('#news/'+encodeURIComponent(id),T('뉴스·관계망 화면 →','News / network screen →'))+'</p></section>'
  +'<section class="card" data-company-card="vmr"><h2>'+esc(T('가격 맥락 (VMR)','Price context (VMR)'))+'</h2><p>'+na(T('정상 범위 대비 위치는 가격이 필요합니다.','Position vs normal range needs prices.'),locale)+'</p></section>'
  +'<h2 class="section-title">'+esc(T('근거 자료','Source data'))+'</h2><div id="sec-reported-panel"></div><p class="small" data-raw-data-link><a href="#settings">'+esc(T('원자료 보기(개발자용)는 설정에 있습니다 →','Raw data (developer) is in Settings →'))+'</a></p>'+(ctx.candidateHtml||'');
}
function v2FactorTable(d,locale){
 const T=tr(locale),en=locale==='en-US'?1:0,W=g.QgvV2?g.QgvV2.WEIGHTS:null;if(!W)return '<p>'+na('',locale)+'</p>';
 const rows=['Q','G','V'].flatMap(axis=>Object.keys(W[axis]).map(f=>{const x=d&&d.factors?d.factors[f]:null,ok=x&&x.score!==null;
  // FE-MISSING-2: weight after the engine's renormalization, the missing-data class and a sentence (raw code under 근거).
  const c=d&&d.coverage&&d.coverage.axes?d.coverage.axes[axis].factors.find(y=>y.id===f):null,QS=g.QgvScores;
  const state=ok?(x.basis||x.state):c?QS.stateText(c.category,en===1):'NOT_AVAILABLE',why=ok?'':c?esc(QS.reasonText(c.reason,en===1))+evidence(factorEvidence(c,locale),locale):esc((x&&x.reason)||'');
  return '<tr data-v2-factor="'+f+'"'+(c&&!ok?' data-factor-state="'+esc(c.category)+'"':'')+'><td>'+axis+'</td><td>'+esc(V2_LABEL[f][en])+'</td><td class="num">'+esc(num(W[axis][f],locale,0))+'%</td><td class="num" data-factor-share>'+(c&&c.share!==null?esc(num(c.share,locale,1))+'%':'—')+'</td><td class="num" data-factor-score>'+(ok?esc(num(x.score,locale)):'—')+'</td><td><span class="badge '+(ok?'LIVE':c&&c.category==='NOT_APPLICABLE'?'NOT_AVAILABLE':c?'partial':'NOT_AVAILABLE')+'">'+esc(state)+'</span></td><td class="small">'+why+'</td></tr>';}));
 const dt=d&&d.detail?d.detail:null,pct=v=>typeof v==='number'&&Number.isFinite(v)?num(v*100,locale)+'%':'—';
 const det=dt?'<p class="small" data-v2-detail>'+esc(T('이 기기 계산(메모리 전용): 이익 수익률 ','On this device (RAM only): earnings yield ')+pct(dt.ebit_yield)+' · '+T('FCF 수익률 ','FCF yield ')+pct(dt.fcf_yield)+' · '+T('역DCF 내재 성장률 ','reverse-DCF implied growth ')+pct(dt.implied_growth)+' · '+T('실현 매출 성장(3년) ','realized revenue growth (3y) ')+pct(dt.realized_growth)+' · '+(dt.earnings_basis==='NORMALIZED'?T('정상화 이익 기준 · ','normalized earnings basis · '):'')+T('업종 기준 ','industry basis ')+(dt.industry_basis||'—')+(dt.industry_peers?' ('+dt.industry_peers+')':''))+'</p>':'';
 return '<div class="table-wrap"><table data-v2-factor-table><thead><tr><th scope="col">'+esc(T('축','Axis'))+'</th><th scope="col">'+esc(T('요인 (v2)','Factor (v2)'))+'</th><th scope="col">'+esc(T('기본 비중','Default weight'))+'</th><th scope="col">'+esc(T('재배분 후','Renormalized'))+'</th><th scope="col">'+esc(T('점수','Score'))+'</th><th scope="col">'+esc(T('상태','State'))+'</th><th scope="col">'+esc(T('사유','Reason'))+'</th></tr></thead><tbody>'+rows.join('')+'</tbody></table></div>'
  +'<p class="small">'+esc(T('산출 요인 ','Factors available ')+(d?d.factors_available+'/'+d.factors_total:'0/15')+T(' · 점수는 504종목(가격 있는 행) 안 백분위, 업종 대비는 SIC 업종군 안 백분위(8개 미만이면 전체) · 결측은 0으로 채우지 않음 · QGV v2 PROVISIONAL',' · scores are percentiles within the priced Universe504 rows; vs-industry within the SIC group (whole universe below 8 peers) · missing is never 0 · QGV v2 PROVISIONAL'))+'</p>'+det;
}
// QGV v2 factors only (owner decision 2026-10-14). The raw v1 SEC Q·G leaf scores are in Settings > 원자료 보기(개발자용).
function factorTable(screens,id,locale,sr=null){return coverageHtml(sr,locale,{compact:false})+v2FactorTable(sr?sr.row.primary:null,locale);}
function panel(key,title,body,hidden){return '<section class="card analysis-panel" role="tabpanel" id="analysis-panel-'+key+'" aria-labelledby="analysis-tab-'+key+'" data-analysis-panel="'+key+'"'+(hidden?' hidden':'')+'><h2>'+esc(title)+'</h2>'+body+'</section>';}
function naRow(label,reason,locale,attr){return '<dt>'+esc(label)+'</dt><dd'+(attr?' data-na="'+attr+'"':'')+'>'+na(reason,locale)+'</dd>';}
const TAB_KEYS=TABS.map(t=>t[0]);
// '#analysis/<id>/<tab>' deep link: an unknown or missing tab opens the overview.
function tabKey(key){return TAB_KEYS.includes(key)?key:'summary';}
function analysis(ctx){
 const{locale,id,screens,ticker}=ctx,T=tr(locale),sr=scoreRow(ctx),v2=sr?sr.row.primary:null,why=g.QgvScores&&g.QgvScores.naText?g.QgvScores.naText(v2,locale==='en-US'):'SEC_QGV2_NOT_AVAILABLE',open=tabKey(ctx.tab);
 const tabs='<div class="chips screen-tabs analysis-tabs" role="tablist" aria-label="'+esc(T('기업분석 탭','Analysis tabs'))+'">'+TABS.map(([k,ko,en])=>'<button type="button" role="tab" id="analysis-tab-'+k+'" data-analysis-tab="'+k+'" aria-controls="analysis-panel-'+k+'" aria-selected="'+(k===open)+'" tabindex="'+(k===open?0:-1)+'">'+esc(T(ko,en))+'</button>').join('')+'</div>';
 const overview=panel('summary',T('종합','Overview'),'<dl class="kv">'+(v2&&v2.total!==null?'<dt>'+esc(T('종합 매력도','Overall attractiveness'))+'</dt><dd data-overall="v2"><span class="num">'+esc(num(v2.total,locale))+'</span> <span class="small">QGV v2 PROVISIONAL · '+esc(v2.profile?v2.profile.id:'')+'</span>'+flagsHtml(v2,locale)+'</dd>':naRow(T('종합 매력도','Overall attractiveness'),why,locale,'overall'))
  +'<dt>'+esc(T('신뢰도','Confidence'))+'</dt><dd data-confidence>'+na('',locale)+'</dd></dl><p class="small" data-confidence-note>'+esc(T('신뢰도: 확률 아님. 데이터 충분도와 근거 일관성을 뜻합니다.','Confidence: not a probability. It means data sufficiency and evidence consistency.'))+(v2?' '+esc(T('QGV v2 산출 요인 ','QGV v2 factors available: '))+v2.factors_available+'/'+v2.factors_total+'.':'')+'</p>'+qgvBody(screens,id,locale,sr),open!=='summary');
 const business=panel('business',T('사업·경쟁','Business / competition'),'<dl class="kv">'+naRow(T('사업 설명','Business description'),T('연간 보고서 출처 연결 전','Annual-report source not connected'),locale)+naRow(T('경쟁우위·열위','Strengths / weaknesses'),'',locale)+naRow(T('시장 지위','Market position'),T('요소 점수는 QGV 요소 탭','Factor score is in the QGV factors tab'),locale)+naRow(T('시장 점유율','Market share'),T('출처·추정 여부 표시 전 자료 없음','No sourced, estimate-flagged data'),locale)+naRow(T('매출 구성','Revenue mix'),'',locale)+'</dl>'+classification(screens,id,locale).replace('class="card"','class="subcard"'),open!=='business');
 const financials=panel('financials',T('재무','Financials'),'<div id="sec-reported-panel"></div><dl class="kv">'+naRow(T('재무 추이 (L03)','Financial trend (L03)'),T('공개 SEC 보고 패널만 연결됨','Only the public SEC reported panel is connected'),locale)+naRow(T('주주환원 (L06)','Shareholder returns (L06)'),'',locale)+(g.StatRadar?g.StatRadar.marginDetail({targetId:id},{screens,locale}):'')+'</dl>',open!=='financials');
 const events=panel('events',T('주가·이벤트','Price / events'),'<p><a href="#company/'+encodeURIComponent(id)+'" data-chart-link>'+esc(T('요약 화면의 가격 차트 열기 →','Open the price chart on the summary →'))+'</a> · <a href="#technical/'+encodeURIComponent(id)+'" data-technical-link>'+esc(T('기술적 분석 →','Technical analysis →'))+'</a></p><dl class="kv"><dt>E '+esc(T('실적 시기','Earnings timing'))+'</dt><dd>'+nextEarnings(screens,id,locale)+'</dd>'
  +['P '+T('제품','Product'),'L '+T('법률·규제','Legal / regulatory'),'M '+T('경영','Management'),'R '+T('재평가 신호','Re-evaluation signal'),'B·S '+T('내 거래','My trades')].map(x=>'<dt>'+esc(x)+'</dt><dd>'+na('',locale)+'</dd>').join('')+'</dl>',open!=='events');
 const factors=panel('factors',T('QGV 요소','QGV factors'),factorTable(screens,id,locale,sr),open!=='factors');
 const compare=panel('compare',T('비교·컨센서스','Compare / consensus'),'<dl class="kv">'+naRow(T('동종 비교','Peer comparison'),T('업종군 v0 연결됨 · 동종 비교 기준 미정','Industry group v0 connected · peer-comparison basis undefined'),locale)+naRow(T('컨센서스','Consensus'),T('공급원 없음','No source'),locale)+'</dl>',open!=='compare');
 return '<a class="parent-link" href="#company/'+encodeURIComponent(id)+'" data-analysis-back>'+esc('← '+ticker+' '+T('요약','summary'))+'</a>'+ctx.headerHtml+dataBadges(screens,locale,true,sr)+tabs+overview+business+financials+events+factors+compare;
}
// onSelect(key) runs after a user tab change (the app mirrors it into the hash with replaceState).
function wireTabs(rootEl,{onSelect=null}={}){
 if(!rootEl)return;const tabs=[...rootEl.querySelectorAll('[data-analysis-tab]')];
 const select=key=>{for(const b of tabs){const on=b.dataset.analysisTab===key;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;}for(const p of rootEl.querySelectorAll('[data-analysis-panel]'))p.hidden=p.dataset.analysisPanel!==key;if(onSelect)onSelect(key);};
 tabs.forEach((b,i)=>{b.addEventListener('click',()=>select(b.dataset.analysisTab));b.addEventListener('keydown',e=>{const d=e.key==='ArrowRight'?1:e.key==='ArrowLeft'?-1:e.key==='Home'?-i:e.key==='End'?tabs.length-1-i:0;if(!d&&e.key!=='Home')return;e.preventDefault();const n=tabs[(i+d+tabs.length)%tabs.length];select(n.dataset.analysisTab);n.focus();});});
}
return Object.freeze({esc,na,fmtPct,fmtPp,num,tr,typeName,record,selectTypes,V2_LABEL,scoreRow,qgvBody,coverageHtml,factorTable,classification,nextEarningsLine,summary,analysis,mountHolding,wireTabs,tabKey,TYPES,TAB_KEYS});
});
