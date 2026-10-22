/* Owner IA screens (PRODUCT_IA_DIRECTIVE_20261018): the structure trees (1.4 QGV, 2.4 기술적 분석, 3.6 매크로, 4.3 뉴스,
   5.4 포트폴리오, n 전체 시스템) and the numbered sections that have no engine yet (2.2, 2.3), and the stamp layout of menu 3 매크로 (function numbers 4.1–4.6).
   The trees describe the real system. Weights and rules are read at runtime from the engine modules (QgvV2, SecQgv2,
   ResearchIndicators, MacroLights, VirtualTrading); nothing here restates a number of its own. "예시 값" under a tree come
   only from published public data already loaded by the app (sec-qgv2.json, macro-screen.json, sec-disclosures.json,
   news-signals.json, actual-catalog.json), each with its file and time. Where no real value exists the example says NA
   and why; a price-based value is never shown here (prices are never published, GSQ-010: they live in this browser's memory,
   the user's private Google Sheet or this browser's storage). Sections without an engine say
   NOT_AVAILABLE and what is missing; no position, probability or chart is drawn for them. Presentation only: no storage,
   no request of its own except reading the same public disclosure/news files the news screen reads. */
(function(root){
 'use strict';
 const T=(l,ko,en)=>l==='en-US'?en:ko;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
 const finite=v=>typeof v==='number'&&Number.isFinite(v),object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
 const fmt1=v=>finite(v)?(Math.round(v*10)/10).toFixed(1):'NA';
 const fmtRaw=v=>finite(v)?(Math.abs(v)>=100?String(Math.round(v)):String(Math.round(v*1000)/1000)):'NA';
 const na=(l,why)=>'<span class="badge NOT_AVAILABLE">NA</span> <span class="small">'+esc(why)+'</span>';
 // Display names of the real QGV v2 factors (factor ids are the engine's; Q1…V5 follow the engine's WEIGHTS order).
 const FACTOR={q_profitability:['수익성','Profitability'],q_moat_proxy:['해자 대리','Moat proxy'],q_earnings_quality:['이익의 질','Earnings quality'],q_financial_safety:['재무 안전','Financial safety'],q_capital_allocation:['자본 배분','Capital allocation'],
  g_revenue_growth:['매출 성장','Revenue growth'],g_per_share_growth:['주당 성장','Per-share growth'],g_growth_efficiency:['성장 효율','Growth efficiency'],g_consistency:['성장 일관성','Growth consistency'],g_recent_acceleration:['최근 가속','Recent acceleration'],
  v_earnings_yield:['이익 수익률','Earnings yield'],v_fcf_yield:['FCF 수익률','FCF yield'],v_vs_industry:['업종 대비','vs industry'],v_vs_own_history:['자기 과거 대비','vs own history'],v_expectation_check:['기대 점검','Expectation check']};
 const AXIS={Q:['질','Quality'],G:['성장','Growth'],V:['가치','Value']};
 // How each V factor is formed (qgv-v2.js metrics(); V is computed on this device with its own prices only).
 const V_HOW={v_earnings_yield:['EBIT ÷ EV','EBIT ÷ EV'],v_fcf_yield:['FCF ÷ EV','FCF ÷ EV'],v_vs_industry:['이익 수익률의 업종 안 백분위','Earnings yield percentile within the industry'],
  v_vs_own_history:['지금 주당 EBIT ÷ 가격을 과거 결산 시점과 비교','Current EBIT per share ÷ price vs past fiscal year-ends'],v_expectation_check:['역DCF 내재 성장률 − 실현 3년 매출 성장률','Reverse-DCF implied growth − realised 3-year revenue growth']};
 const qv=()=>root.QgvV2||null,sq=()=>root.SecQgv2||null;
 const factorsOf=axis=>{const W=qv()?.WEIGHTS?.[axis];return W?Object.entries(W):[];};
 const alias=(axis,i)=>axis+(i+1);
 function weightNote(l){const V=qv();if(!V)return '';
  return T(l,'축 비중 시작값 '+Object.entries(V.PRESETS[V.DEFAULT_PRESET].weights).map(([k,v])=>k+v).join(' / ')+' (공격·균형·수비형 수치는 결정 대기)','Starting axis weights '+Object.entries(V.PRESETS[V.DEFAULT_PRESET].weights).map(([k,v])=>k+v).join(' / ')+' (aggressive/balanced/defensive numbers pending)');}
 // ---------- tree drawing ----------
 const node=(cls,head,body,kids,attrs)=>'<li><div class="tree-node '+cls+'"'+(attrs||'')+'><b>'+head+'</b>'+(body?'<span class="tree-body">'+body+'</span>':'')+'</div>'+(kids&&kids.length?'<ul class="tree-branch">'+kids.join('')+'</ul>':'')+'</li>';
 const leaf=(head,body,attrs)=>'<li><div class="tree-leaf"'+(attrs||'')+'><b>'+head+'</b>'+(body?' <span class="tree-body">'+body+'</span>':'')+'</div></li>';
 function page(key,l,{eyebrow,title,lede,tree,rules,examples}){
  return '<section class="ia-tree" data-tree="'+key+'" aria-labelledby="tree-title">'+
   '<p class="eyebrow">'+esc(eyebrow)+'</p><h1 id="tree-title">'+esc(title)+'</h1>'+
   '<p class="tree-lede">'+esc(lede)+'</p>'+
   '<p class="tree-legend small">'+esc(T(l,'트리는 실제 시스템의 구조입니다. 비중·규칙은 엔진 코드에서 읽습니다. 숫자 예시는 아래 "예시 값"에만 있고 공개 자료에서 읽습니다.','The tree is the real system. Weights and rules are read from the engine code. Example numbers appear only under “Example values”, read from published data.'))+'</p>'+
   '<ul class="tree-root">'+tree+'</ul>'+
   (rules?'<section class="tree-rules card"><h2>'+esc(T(l,'규칙','Rules'))+'</h2><ul>'+rules.map(r=>'<li>'+r+'</li>').join('')+'</ul></section>':'')+
   '<section class="tree-examples card" data-tree-examples="'+key+'" aria-live="polite"><h2><span class="hl">'+esc(T(l,'예시 값','Example values'))+'</span></h2>'+examples+'</section></section>';
 }
 const loading=l=>'<div data-tree-example-body><p class="small">'+esc(T(l,'공개 자료를 읽는 중…','Reading published data…'))+'</p></div>';
 // ---------- 1.4 QGV ----------
 function qgvTree(l){
  const V=qv(),S=sq(),sub=S?.SUBMETRICS?.GENERAL||{},fin=S?.SUBMETRICS?.FINANCIAL||{};
  const subText=f=>{const g=(sub[f]||[]).map(([k,d])=>k+(d>0?' ↑':' ↓')).join(' · '),x=(fin[f]||[]).map(([k,d])=>k+(d>0?' ↑':' ↓')).join(' · ');
   return esc(g||'—')+(x!==g?'<br><span class="small">'+esc(T(l,'금융: ','Financial: ')+(x||T(l,'정의상 해당 없음','not applicable by definition')))+'</span>':'');};
  const axisNode=axis=>node('axis','<span class="axis-letter" data-axis="'+axis+'">'+axis+'</span> '+esc(T(l,...AXIS[axis])),
   axis==='V'?esc(T(l,'이 기기 시세로만 계산 · 공개 파일에 없음','Computed with this device’s prices only · not in public files')):esc(T(l,'SEC 공시에서 계산 · 공개 sec-qgv2.json','From SEC filings · public sec-qgv2.json')),
   factorsOf(axis).map(([f,w],i)=>leaf(esc(alias(axis,i)+' '+T(l,...FACTOR[f]))+' <span class="w" data-weight="'+esc(f)+'">'+esc(w)+'</span>',axis==='V'?esc(T(l,...V_HOW[f])):subText(f),' data-factor="'+esc(f)+'"')),' data-axis="'+axis+'"');
  const tree=node('root',esc(T(l,'QGV 점수','QGV score')),esc(weightNote(l)),[
   node('input',esc(T(l,'입력','Inputs')),esc(T(l,'SEC companyfacts · submissions(10-K/10-Q) → 지표 계산 → 업종 안 백분위(0~100). V는 공개 v_inputs_v2 + 이 기기 시세','SEC companyfacts · submissions (10-K/10-Q) → metrics → percentile within the industry (0–100). V: public v_inputs_v2 + this device’s prices'))),
   axisNode('Q'),axisNode('G'),axisNode('V'),
   node('extra',esc(T(l,'스탯창(레이더) — QGV + QGV가 못 담는 것','Stat window (radar) — QGV + what QGV misses')),root.StatRadar?'<span class="badge'+(root.StatRadar.DECISION.state==='DECIDED'?'':' partial')+'">'+esc(root.StatRadar.DECISION.state==='DECIDED'?T(l,'결정됨','DECIDED'):root.StatRadar.DECISION.state==='CANDIDATE'?T(l,'후보 축 포함','with candidate axes'):'PROVISIONAL')+'</span> '+esc(root.StatRadar.AXES.map(a=>T(l,...a.name)+(a.kind==='PRICE'?T(l,'(후보 축 · 내 가격 자료)',' (candidate · your price data)'):a.kind==='DEVICE_SCORE'?T(l,'(기존 V 경로)',' (existing V path)'):T(l,'(공개)',' (public)'))).join(' · ')+T(l,' · 모든 축 바깥 = 더 좋은 평가 · 보조: 이익률 안정성(선택) · 비교군: 업종 · SIC · 경쟁사(미산출, REL-SOURCE 대기) · ',' · outer = better on every axis · auxiliary: margin stability (optional) · groups: industry · SIC · competitors (n/a, REL-SOURCE pending) · ')+T(l,...root.StatRadar.DECISION.ref)+T(l,' · 예시는 아래',' · example below')):'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span>',null,' data-tree-radar-node')]);
  const rules=V?[
   esc(T(l,'축 안 비례 재정규화: 없는 요인을 빼고 남은 비중을 같은 비율로 키웁니다(0으로 채우지 않음).','Proportional renormalisation within an axis: missing factors are dropped and the remaining weights scale up (never filled with 0).')),
   esc(T(l,'축 최소 ','Axis minimum ')+Math.round(V.MIN_AXIS_WEIGHT*100)+T(l,'%: 남은 비중이 이보다 작으면 그 축은 NA.','%: below this remaining weight the axis is NA.')),
   esc(T(l,'가치 함정 관문: Q 업종 백분위 ≤ ','Value-trap gate: Q industry percentile ≤ ')+V.GATE_PERCENTILE+T(l,'이면 V를 뺍니다(기본 ',' drops V (default ')+(V.GATE_DEFAULT?T(l,'켬','on'):T(l,'끔','off'))+')'),
   esc(T(l,'비교군: SIC 업종 그룹(sic_industry_groups/v0), 동종 ','Peers: SIC industry group (sic_industry_groups/v0), at least ')+V.MIN_PEERS+T(l,'개 미만이면 전체 모집단으로 내림. 발행사 하나에 한 점.',' peers, else the whole universe. One point per issuer.')),
   esc(T(l,'FINANCIAL 동종(SIC 6000–6499)은 별도 세부 지표를 씁니다. 이익의 질은 정의상 해당 없음, V는 정의하지 않음.','FINANCIAL peers (SIC 6000–6499) use their own sub-metrics; earnings quality is not applicable by definition and V is not defined.'))]:null;
  return page('qgv',l,{eyebrow:'1.4 · QGV STRUCTURE',title:T(l,'QGV 시스템 내용구성','QGV structure'),lede:T(l,'축 → 요인 → 세부 지표 · 비중 · 비교군을 한눈에 봅니다.','Axis → factor → sub-metric · weight · peer group at a glance.'),tree,rules,examples:loading(l)});
 }
 function qgvExamples(l,screens){
  const p=screens&&screens['sec-qgv2.json'],S=sq(),V=qv();
  if(!p||!object(p.records))return '<div data-tree-example-body data-example-state="NOT_AVAILABLE"><p>'+na(l,T(l,'sec-qgv2.json이 아직 게시되지 않았거나 읽을 수 없습니다. 예시를 지어내지 않습니다.','sec-qgv2.json is not published or could not be read. No example is invented.'))+'</p></div>';
  const code=Object.keys(p.records).filter(c=>!c.startsWith('TARGET:')).sort().find(c=>{const r=p.records[c];return r.state==='LIVE'&&r.in_cross_section&&finite(r.qg_axes?.Q?.score)&&finite(r.qg_axes?.G?.score);});
  if(!code)return '<div data-tree-example-body data-example-state="NOT_AVAILABLE"><p>'+na(l,T(l,'Q·G가 모두 산출된 LIVE 행이 없습니다.','No LIVE row with both Q and G.'))+'</p></div>';
  const r=p.records[code],sub=S?.SUBMETRICS?.[r.profile==='FINANCIAL'?'FINANCIAL':'GENERAL']||{};
  const raw=f=>(sub[f]||[]).map(([k])=>k+' '+fmtRaw(r.metrics?.[k])).join(' · ');
  const rows=['Q','G'].flatMap(axis=>factorsOf(axis).map(([f,w],i)=>'<tr data-example-factor="'+esc(f)+'"><th scope="row">'+esc(alias(axis,i)+' '+T(l,...FACTOR[f]))+'</th><td data-label="'+esc(T(l,'비중','Weight'))+'">'+esc(w)+'</td><td data-example-value data-label="'+esc(T(l,'백분위','Percentile'))+'">'+esc(fmt1(r.factors?.[f]))+'</td><td class="small">'+esc(raw(f)||'—')+'</td></tr>'));
  const vRows=factorsOf('V').map(([f,w],i)=>'<tr data-example-factor="'+esc(f)+'"><th scope="row">'+esc(alias('V',i)+' '+T(l,...FACTOR[f]))+'</th><td data-label="'+esc(T(l,'비중','Weight'))+'">'+esc(w)+'</td><td data-example-value data-label="'+esc(T(l,'백분위','Percentile'))+'">NA</td><td class="small">'+esc(T(l,'이 기기 시세 필요 · 공개하지 않음','Needs this device’s prices · never published'))+'</td></tr>');
  const ax=a=>{const x=r.qg_axes?.[a]||{};return fmt1(x.score)+(x.peer_basis?' · '+x.peer_basis+(Number.isInteger(x.peer_count)?' '+x.peer_count:''):'');};
  return '<div data-tree-example-body data-example-state="LIVE" data-example-source="sec-qgv2.json" data-example-code="'+esc(code)+'" data-example-as-of="'+esc(p.as_of||'')+'">'+
   '<p class="small">'+esc(T(l,'공개 sec-qgv2.json에서 코드 순서로 처음 나온 LIVE 행 하나입니다. 추천이 아닙니다.','The first LIVE row (code order) of the public sec-qgv2.json. Not a recommendation.'))+'</p>'+
   '<dl class="tree-facts"><div><dt>'+esc(T(l,'코드','Code'))+'</dt><dd data-example-field="code">'+esc(code)+'</dd></div>'+
   '<div><dt>SIC · '+esc(T(l,'업종 그룹','group'))+'</dt><dd>'+esc((r.sic||'NA')+' · '+(r.industry_group||'NA'))+'</dd></div>'+
   '<div><dt>'+esc(T(l,'재무 프로필','Profile'))+'</dt><dd>'+esc(r.profile)+'</dd></div>'+
   '<div><dt>Q</dt><dd data-example-axis="Q">'+esc(ax('Q'))+'</dd></div><div><dt>G</dt><dd data-example-axis="G">'+esc(ax('G'))+'</dd></div>'+
   '<div><dt>V</dt><dd>NA · '+esc(T(l,'기기 계산','device only'))+'</dd></div>'+
   '<div><dt>'+esc(T(l,'자료 기준','As of'))+'</dt><dd data-example-field="as_of">'+esc((p.as_of||'NA')+' · '+T(l,'수집 ','acquired ')+(r.acquired_at||'NA')+' · FY '+(r.fiscal_year_end||'NA'))+'</dd></div></dl>'+
   '<div class="tree-table"><table><thead><tr><th scope="col">'+esc(T(l,'요인','Factor'))+'</th><th scope="col">'+esc(T(l,'비중','Weight'))+'</th><th scope="col">'+esc(T(l,'백분위','Percentile'))+'</th><th scope="col">'+esc(T(l,'세부 지표 원값','Sub-metric raw values'))+'</th></tr></thead><tbody>'+rows.join('')+vRows.join('')+'</tbody></table></div>'+
   (root.StatRadar?'<div class="tree-radar" data-tree-radar>'+root.StatRadar.html({code},{screens,locale:l})+'</div>':'')+
   '</div>';
 }
 // ---------- 2.4 기술적 분석 ----------
 function technicalTree(l){
  const tree=node('root',esc(T(l,'기술적 분석','Technical analysis')),esc(T(l,'QGV 점수와 나란히 볼 뿐 합치지 않습니다.','Shown next to QGV, never merged into it.')),[
   node('input',esc(T(l,'입력','Inputs')),esc(T(l,'일봉(이 기기 RAM · 비공개 Worker · 내 시트) · 가격 기준 RAW_CLOSE / PROVIDER_ADJUSTED_CLOSE','Daily bars (this device’s RAM · private Worker · my sheet) · price basis RAW_CLOSE / PROVIDER_ADJUSTED_CLOSE'))),
   node('','2.1 '+esc(T(l,'지표','Indicators')),esc(T(l,'연구 표시용 · 차트에서 지표 표시와 패턴 매개변수·정도를 설정합니다. 공식 결과와 개인 미리보기를 구분합니다.','Research display only · set indicator visibility and pattern parameters/degree in the chart. Official results and personal previews stay separate.')),[
    leaf('SMA','5 · 20 · 60 · 120 (· 240)'),leaf('EMA','20'),leaf('RSI','14'),leaf('MACD','12 · 26 · 9'),leaf(esc(T(l,'볼린저','Bollinger')),'20 · 2σ'),leaf('ATR','14 · RAW_CLOSE')]),
   node('','2.1 '+esc(T(l,'신호 카드','Signal cards')),esc(T(l,'추세·모멘텀 등 상태 카드(technical-cards.js) · 실행 구간·기록은 NOT_AVAILABLE','Trend/momentum state cards (technical-cards.js) · execution zone and record NOT_AVAILABLE'))),
   node('','2.2 '+esc(T(l,'차트 패턴','Chart patterns')),esc(T(l,'패턴·감지 이력 구현. 실제 가격 기준 미확인 구간은 판정 불가. 형태 적합도는 상승 확률이 아님','Patterns and detection history are implemented. Unconfirmed real-price basis means unavailable judgement. Shape fit is not a probability'))),
   node('','2.1–2.2 '+esc(T(l,'가격 시나리오','Price scenarios')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'확률 근거 = 같은 패턴·정도에서 과거 결과 빈도 · 미산출','Probability basis = past outcome frequency for the same pattern and degree · not computed'))),
   node('','2.3 '+esc(T(l,'내 노트(보라색 펜)','My notes (purple pen)')),esc(T(l,'이 브라우저에 저장 · 내보내기/가져오기 가능 · 공식 증거로 쓰지 않음 · 계정 동기화 없음','Saved in this browser · export/import available · never official evidence · no account sync')))]);
  const ex='<div data-tree-example-body data-example-state="NOT_AVAILABLE"><p>'+na(l,T(l,'기술적 분석 값은 가격에서 나옵니다. 가격은 공개하지 않습니다(이 브라우저 메모리에서 계산하며, 저장은 사용자 비공개 구글 시트·이 브라우저에만 둡니다). 그래서 이 화면에 예시 값이 없습니다. 2.1 화면에서 내 값을 볼 수 있습니다.','Technical values come from prices, which are never published (computed in this browser’s memory; stored only in the user’s private Google Sheet or this browser), so no example is shown here. See your values on 2.1.'))+'</p><p><a href="#technical">2.1 '+esc(T(l,'지표 · 시나리오 →','Indicators →'))+'</a></p></div>';
  return page('technical',l,{eyebrow:'2.4 · TECHNICAL STRUCTURE',title:T(l,'기술적 분석 내용구성','Technical analysis structure'),lede:T(l,'입력 → 지표 → 신호 → 패턴 → 시나리오 → 내 노트.','Input → indicators → signals → patterns → scenarios → my notes.'),tree,examples:ex});
 }
 // ---------- 3.6 매크로 ----------
 function macroTree(l){
  const ML=root.MacroLights,lights=ML?.LIGHTS||[],pub=ML?.PUBLIC_LIGHTS||[];
  const LIGHT={employment:['고용','Employment'],inflation:['물가','Inflation'],curve:['금리 곡선','Yield curve'],market:['시장','Market'],credit:['신용','Credit']};
  const tree=node('root',esc(T(l,'매크로','Macro')),esc(T(l,'정보 제공용 · 점수에 직접 쓰지 않음','Information only · not a direct score input')),[
   node('input',esc(T(l,'입력','Inputs')),esc(T(l,'원기관 공개 지표(BLS · BEA · 재무부 · 연준) · 시장·신용 등 가격은 이 기기에서만 · FRED/ALFRED 사용 안 함','Primary agencies (BLS · BEA · Treasury · Fed) · market and credit prices on this device only · no FRED/ALFRED'))),
   node('',esc(T(l,'경고등 ','Lights ')+lights.length),esc(T(l,'정상·경고·위기 판정 · v1 UNCALIBRATED','Normal / warning / crisis · v1 UNCALIBRATED')),lights.map(n=>leaf(esc(T(l,...(LIGHT[n]||[n,n]))),esc(pub.includes(n)?T(l,'공개 자료','public data'):T(l,'이 기기 가격','device prices'))))),
   node('',esc(T(l,'상태판 8축 × 6칸','Board 8 axes × 6 states')),esc(T(l,'Growth · Inflation · Liquidity · Monetary Policy · Credit · Labor · Fiscal · FX × Level · Direction · Momentum · Surprise · Stress · Confidence (하나로 합치지 않음)','… kept separate, never one score'))),
   node('','3.1 '+esc(T(l,'경기·시장 위치 + 근거선','Economy · market position + evidence lines')),esc(T(l,'개념 링·실제 관측 근거를 구분해 조회 · 공식 위치·확률은 미산출','Concept rings and observed evidence are shown separately · official position and probability not computed'))),
   node('','3.2 '+esc(T(l,'순환매 위치','Sector rotation')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'확률 근거 = 과거 국면 전환 빈도 · 미산출','Probability basis = past regime-transition frequency · not computed'))),
   node('','3.3 '+esc(T(l,'산업 사이클 (SIC 업종 그룹)','Industry cycles (SIC groups)')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'확률 근거 = 과거 국면 전환 빈도 · 미산출','Probability basis = past regime-transition frequency · not computed'))),
   node('','3.4 '+esc(T(l,'내가 고른 위치','My chosen position')),esc(T(l,'공식 값과 별도로 이 브라우저에 기록 · 내보내기/가져오기 가능 · 점수에 쓰지 않음','Recorded in this browser separately from official values · export/import available · never scored'))),
   node('','3.5 '+esc(T(l,'연쇄 효과 지도','Causal-chain map')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'관계 자료원 결정 대기(REL-SOURCE)','Relationship source pending (REL-SOURCE)')))]);
  return page('macro',l,{eyebrow:'3.6 · MACRO STRUCTURE',title:T(l,'매크로 시스템 내용구성','Macro structure'),lede:T(l,'입력 → 경고등 · 상태판 → 위치 · 순환매 · 산업 사이클 → 연쇄 효과.','Inputs → lights · board → position · rotation · industry cycles → causal chains.'),tree,examples:loading(l)});
 }
 function macroExamples(l,screens){
  const p=screens&&screens['macro-screen.json'],obs=Array.isArray(p?.data?.observations)?p.data.observations:[];
  if(!obs.length)return '<div data-tree-example-body data-example-state="NOT_AVAILABLE"><p>'+na(l,T(l,'macro-screen.json에 공개 관측이 없습니다(상태 ','No published observation in macro-screen.json (state ')+(p?.state||'NOT_AVAILABLE')+'). '+T(l,'예시를 지어내지 않습니다.','No example is invented.'))+'</p></div>';
  const seen=new Set(),pick=[];for(const o of obs){if(seen.has(o.axis))continue;seen.add(o.axis);pick.push(o);if(pick.length>=4)break;}
  return '<div data-tree-example-body data-example-state="'+esc(p.state)+'" data-example-source="macro-screen.json" data-example-as-of="'+esc(p.as_of||'')+'"><p class="small">'+esc(T(l,'공개 macro-screen.json의 축별 첫 관측입니다. 원값 그대로이며 판정이 아닙니다.','First observation per axis in the public macro-screen.json. Raw values, not judgements.'))+'</p>'+
   '<div class="tree-table"><table><thead><tr><th scope="col">'+esc(T(l,'축','Axis'))+'</th><th scope="col">'+esc(T(l,'계열','Series'))+'</th><th scope="col">'+esc(T(l,'기간','Period'))+'</th><th scope="col">'+esc(T(l,'값','Value'))+'</th><th scope="col">'+esc(T(l,'수집 상한 시각','Available at (capture bound)'))+'</th></tr></thead><tbody>'+
   pick.map(o=>'<tr data-example-series="'+esc(o.source_id)+'"><th scope="row">'+esc(o.axis)+'</th><td>'+esc(o.provider+' · '+o.source_id)+'</td><td>'+esc(o.observation_period)+'</td><td data-example-value>'+esc(o.value+' '+o.unit)+'</td><td>'+esc(o.available_at||'NA')+'</td></tr>').join('')+'</tbody></table></div><p class="small">'+esc(T(l,'파일 기준 ','File as of ')+(p.as_of||'NA'))+'</p></div>';
 }
 // The same in-tab copy of a public list file as the 4.2 list (DataRefresh: one read per publication, D6); the reader directly
 // only on a page without DataRefresh.
 function shared(key,api){return root.DataRefresh&&typeof root.DataRefresh.list==='function'?root.DataRefresh.list(root,key):api.load(root);}
 // ---------- 4.3 뉴스 ----------
 function newsTree(l){
  const tree=node('root',esc(T(l,'뉴스','News')),esc(T(l,'점수를 바꾸지 않음(score_effect NONE) · 정보 제공용','Never changes scores (score_effect NONE) · information only')),[
   node('input',esc(T(l,'수집','Collection')),esc(T(l,'SEC 8-K(sec-disclosures.json) · DART(dart-disclosures.json) · 뉴스·IR(news-signals.json) · 지금은 고정 대상 기업만','SEC 8-K · DART · news and IR · fixed target companies only for now'))),
   node('',esc(T(l,'분류','Classification')),esc(T(l,'8-K 항목 → 분류 · 같은 사건 묶기(NEW / REPEAT) · 중요도 4단계 표시','8-K items → class · same-event grouping (NEW / REPEAT) · four display tiers'))),
   node('','4.1 '+esc(T(l,'관계망','Company network')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'관계 자료원 결정 대기(REL-SOURCE) · "기업 관계 · 미연결"','Relationship source pending (REL-SOURCE)'))),
   node('','4.2 '+esc(T(l,'공시 · 뉴스 목록','Filings and news list')),esc(T(l,'최신순 · 관심 기업 · 범위 필터','Newest first · watchlist · scope filters'))),
   node('',esc(T(l,'5줄 요약 · 주가 반영 여부','Five-line summary · price reaction')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'요약 방식 결정 대기(IA-14) · 반영 여부는 직접 알 수 없음, "사건 전후 반응"만 이 기기에서','Summary method pending (IA-14) · “priced in” cannot be known; only event-window reaction, on this device'))),
   node('',esc(T(l,'개인화','Personal')),esc(T(l,'관심 기업(이 기기) · 로그인 저장은 결정 대기','Watchlist on this device · account storage pending')))]);
  return page('news',l,{eyebrow:'4.3 · NEWS STRUCTURE',title:T(l,'뉴스 시스템 내용구성','News structure'),lede:T(l,'수집 → 분류 → 관계망 · 목록 → 요약 → 개인화.','Collect → classify → network · list → summary → personal.'),tree,examples:loading(l)});
 }
 async function newsExamples(l){
  const SD=root.SecDisclosures,NS=root.NewsSignals;let sec=null,news=null;
  try{[sec,news]=await Promise.all([SD?shared('sec',SD):null,NS?shared('news',NS):null]);}catch(_){sec=null;news=null;}
  const ev=Array.isArray(sec?.events)?[...sec.events].sort((a,b)=>String(b.accepted_at).localeCompare(String(a.accepted_at))):[],it=Array.isArray(news?.items)?[...news.items].sort((a,b)=>String(b.published_at).localeCompare(String(a.published_at))):[];
  const line=(label,file,p,rows,show)=>'<div><dt>'+esc(label)+'</dt><dd data-example-source="'+file+'" data-example-count="'+(p?rows.length:'NA')+'">'+(p?esc(rows.length+T(l,'건 · 파일 기준 ',' items · file as of ')+(p.as_of||'NA'))+(rows[0]?'<br><span class="small">'+esc(T(l,'최신: ','Latest: ')+show(rows[0]))+'</span>':''):na(l,T(l,'파일을 읽을 수 없습니다.','File could not be read.')))+'</dd></div>';
  return '<div data-tree-example-body data-example-state="'+(sec||news?'LOADED':'NOT_AVAILABLE')+'"><p class="small">'+esc(T(l,'공개 파일의 건수와 가장 최근 한 건입니다.','Counts and the newest item of the public files.'))+'</p><dl class="tree-facts">'+
   line(T(l,'SEC 8-K','SEC 8-K'),'sec-disclosures.json',sec,ev,e=>String(e.company_id).toUpperCase()+' · '+e.form+' · '+(Array.isArray(e.items)?e.items.join(','):'')+' · '+e.accepted_at)+
   line(T(l,'뉴스·IR','News · IR'),'news-signals.json',news,it,i=>String(i.company_id).toUpperCase()+' · '+i.source+' · '+i.classification+' · '+i.published_at)+
   '<div><dt>'+esc(T(l,'관계','Relations'))+'</dt><dd>'+na(l,T(l,'관계 자료 없음(REL-SOURCE)','No relationship data (REL-SOURCE)'))+'</dd></div></dl></div>';
 }
 // ---------- 5.4 포트폴리오 ----------
 function portfolioTree(l){
  // Function numbers 6.1–6.3 on stamp boxes (owner draft, design lane D4); the menu numbers are 5.1–5.4 (stated in the lede).
  const VT=root.VirtualTrading?.CONFIG,st=n=>'<span class="ia-sec" data-fn-stamp>'+n+'</span> ';
  const tree=node('root',st('6.4')+esc(T(l,'포트폴리오','Portfolio')),esc(T(l,'실거래 없음 · 장부는 추가만(덮어쓰지 않음)','No real trades · ledgers are append-only')),[
   node('',st('6.1')+esc(T(l,'포트폴리오 구성','Portfolio composition')),esc(T(l,'메뉴 5.1','Menu 5.1')),[
    node('',st('6.1.1')+esc(T(l,'종류 구분','Kinds')),'',[
     node('',esc(T(l,'모델 적합 포트폴리오','Model portfolio')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'모델 포트폴리오 생성기 없음. 확정 목표(TARGET)는 따로 표시','No model generator yet. The confirmed TARGET is shown separately'))),
     node('',esc(T(l,'내 포트폴리오','My portfolio')),esc(T(l,'실제 보유(ACTUAL) · 이 기기 IndexedDB / 내 비공개 시트 · 공개하지 않음','Actual holdings · this device / my private sheet · never published'))),
     node('',esc(T(l,'모의 포트폴리오','Paper portfolio')),esc(T(l,'가상 매매 세트 A~D + 규칙대로 했다면(SHADOW)','Virtual sets A–D + “if the rules were followed” (SHADOW)')+(VT?' · '+VT.config_version+' · '+T(l,'시작 ','start ')+VT.start_date:'')),[])]),
    node('',st('6.1.2')+esc(T(l,'모델 후보와 선정','Model candidates and selection')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'후보 생성기 없음 · 지금 기준은 확정 목표(TARGET)','No candidate generator · the current reference is the confirmed TARGET'))),
    node('',st('6.1.3')+esc(T(l,'비중과 조건','Weights and conditions')),esc(T(l,'TARGET 대비 ACTUAL · 산업·유형·테마 구성 · 쏠림 경고(v0 기본값)','TARGET vs ACTUAL · industry, type and theme mix · concentration warning (v0 default)'))),
    node('',st('6.1.4')+esc(T(l,'입력과 버전','Inputs and versions')),esc(T(l,'실제 보유는 이 기기에서 입력 · TARGET 버전 · 시세 기준 시각','Actual holdings entered on this device · TARGET version · quote time'))),
    node('',st('6.1.5')+esc(T(l,'개인·모의 구성 관리','Personal and paper sets')),esc(T(l,'세트 B~D는 내 비공개 시트에 정의 · 플레이북(산 이유·무효화 조건)','Sets B–D defined in my private sheet · playbook (reasons, invalidation)')))]),
   node('',st('6.2')+esc(T(l,'실제 포트폴리오 일일·주간 보고','Actual portfolio daily · weekly report')),esc(T(l,'메뉴 5.2','Menu 5.2')),[
    node('',st('6.2.1')+esc(T(l,'보고 내용','Report contents')),esc(T(l,'템플릿 v1 · 그림자 장부는 "규칙대로 했다면"의 가상 기록','Template v1 · the shadow ledger is a virtual “had the rules been followed” record'))),
    node('',st('6.2.2')+esc(T(l,'기간 선택','Period')),esc(T(l,'기간별 성과·상대지수 · 주간 보고는 결정 대기(WEEKLY-REPORT)','Per-period and relative performance · weekly report pending (WEEKLY-REPORT)'))),
    node('',st('6.2.3')+esc(T(l,'보고 불가 시 프롬프트','Prompt when no report')),esc(T(l,'사유 코드 → 최소 누락 입력 → 복사할 프롬프트(금액 없음)','Reason code → smallest missing input → prompt to copy (no amounts)'))),
    node('',st('6.2.4')+esc(T(l,'결과 검토','Review the result')),esc(T(l,'AI 답 붙여넣기 → 검토 → 보관 · 템플릿에 없는 숫자 표시','Paste the AI answer → review → keep · numbers not in the template are flagged')))]),
   node('',st('6.3')+esc(T(l,'모의 포트폴리오 일일·주간 보고','Paper portfolio daily · weekly report')),esc(T(l,'메뉴 5.3','Menu 5.3')),[
    node('',st('6.3.1')+esc(T(l,'모의 성과','Paper performance')),esc(T(l,'세트별 보고 · 비교','Per set · compare'))),
    node('',st('6.3.2')+esc(T(l,'판단 추적','Judgement tracking')),esc(T(l,'규칙 판단 · 리허설(기록 없음) · 누적 검증','Rule judgements · rehearsal (not recorded) · cumulative check'))),
    node('',st('6.3.3')+esc(T(l,'보고 불가 시 프롬프트','Prompt when no report')),esc(T(l,'세트별 사유 · 복사할 프롬프트','Per-set reason · prompt to copy')))])]);
  return page('portfolio',l,{eyebrow:'5.4 · PORTFOLIO STRUCTURE',title:T(l,'포트폴리오 시스템 내용구성','Portfolio structure'),lede:T(l,'모델 · 내 것 · 모의 → 매일 보고 → 보고 불가 시 프롬프트. 상자의 번호(6.x)는 기능 번호이며 메뉴 번호(5.x)가 아닙니다.','Model · mine · paper → daily report → prompt when a report cannot be made. The stamp numbers (6.x) are function numbers, not menu numbers (5.x).'),tree,examples:loading(l)});
 }
 function portfolioExamples(l,catalog){
  const ok=object(catalog)&&Array.isArray(catalog.instruments);
  return '<div data-tree-example-body data-example-state="'+(ok?'LOADED':'NOT_AVAILABLE')+'"'+(ok?' data-example-source="actual-catalog.json"':'')+'><p class="small">'+esc(T(l,'실제 보유는 예시로 쓰지 않습니다. 공개 목표 목록만 읽습니다.','Actual holdings are never used as examples. Only the public target catalogue is read.'))+'</p><dl class="tree-facts">'+
   '<div><dt>TARGET</dt><dd data-example-count="'+(ok?catalog.instruments.length:'NA')+'">'+(ok?esc(T(l,'확정 목표 ','Confirmed target ')+(catalog.target_root_version||'NA')+' · '+catalog.instruments.length+T(l,'종목',' instruments')+(Array.isArray(catalog.themes)?' · '+catalog.themes.length+T(l,'개 테마',' themes'):'')):na(l,T(l,'actual-catalog.json을 읽을 수 없습니다.','actual-catalog.json could not be read.')))+'</dd></div>'+
   '<div><dt>MODEL</dt><dd>'+na(l,T(l,'생성기 없음','No generator'))+'</dd></div>'+
   '<div><dt>ACTUAL · PAPER</dt><dd>'+na(l,T(l,'개인 자료 · 공개 안 함(ACTUAL은 이 브라우저, PAPER 원장은 사용자 비공개 구글 시트)','Personal data · never published (ACTUAL in this browser, the PAPER ledger in the user’s private Google Sheet)'))+'</dd></div></dl></div>';
 }
 // ---------- n 전체 시스템 ----------
 function systemTree(l){
  const menus=root.AppShell?.MENUS||[];
  const cols=menus.filter(m=>m.key!=='system').map(m=>'<section class="sys-col" data-menu-col="'+m.key+'"><h2><a href="'+m.href+'"><span class="ia-sec">'+esc(m.num)+'</span> '+esc(T(l,m.ko,m.en))+'</a></h2><ul>'+
   m.items.map(([href,sec,ko,en,pending])=>'<li><a href="'+href+'"><span class="ia-sec">'+esc(sec)+'</span> '+esc(T(l,ko,en))+'</a>'+(pending?' <span class="badge NOT_AVAILABLE">NA</span>':'')+'</li>').join('')+
   '</ul><p class="sys-ex small" data-system-example="'+m.key+'"></p></section>').join('');
  const SRC=[['SEC 공시','SEC filings','companyfacts · 10-K · 8-K · 13F'],['DART','DART',T(l,'한국 공시','Korean filings')],[T(l,'시세','Prices'),T(l,'시세','Prices'),T(l,'이 기기에서만','this device only')],[T(l,'경제지표','Economic data'),T(l,'경제지표','Economic data'),'BLS · BEA · Treasury · Fed'],[T(l,'뉴스','News'),T(l,'뉴스','News'),'GDELT · IR'],[T(l,'내 정보','My data'),T(l,'내 정보','My data'),T(l,'보유 · 설정 · 노트 (비공개)','holdings · settings · notes (private)')]];
  return '<section class="ia-tree ia-system" data-tree="system" aria-labelledby="tree-title"><p class="eyebrow">n · SYSTEM TREE</p><h1 id="tree-title">'+esc(T(l,'투자시스템 한 장 지도','The investment system on one page'))+'</h1>'+
   '<p class="tree-lede">'+esc(T(l,'재료 → 투자시스템 → 메뉴 1~6 · n+1. 기업을 검색하면 한 기업을 QGV · 기술적 분석 · 매크로 · 뉴스로 봅니다.','Inputs → the system → menus 1–6 · n+1. Search a company to see it through QGV, technical, macro and news.'))+'</p>'+
   '<h2 class="sys-h">'+esc(T(l,'재료 (어디서 오나)','Inputs (where data comes from)'))+'</h2><ul class="sys-sources">'+SRC.map(([ko,en,d])=>'<li><b>'+esc(T(l,ko,en))+'</b><span class="small">'+esc(d)+'</span></li>').join('')+'</ul>'+
   '<div class="sys-core"><span>'+esc(T(l,'투자시스템','The system'))+'</span></div>'+
   '<div class="sys-cols">'+cols+'</div>'+
   '<section class="card sys-links"><h2>'+esc(T(l,'서로 이어지는 선','How the parts connect'))+'</h2><ul>'+
   [['SEC 공시 → QGV Q·G → (모델 포트폴리오 후보: 미구현) → 일일 보고 "확인할 것"','SEC filings → QGV Q·G → (model candidates: not built) → daily report “to check”'],
    ['시세(이 기기) → V · 기술적 분석 지표 → 같은 보고의 기술 항목','Prices (device) → V · technical indicators → the report’s technical items'],
    ['경제지표 → 매크로 경고등·상태판 → (위치·사이클: 미구현) → 레이더 "매크로 민감도"(결정 대기)','Economic data → macro lights and board → (position, cycles: not built) → radar “macro sensitivity” (pending)'],
    ['8-K 공시 → 뉴스 목록 → (5줄 요약·관계망·연쇄 효과 지도: 미구현)','8-K filings → news list → (summary, network, causal-chain map: not built)'],
    ['오늘의 Q·G → Lab 전진 검증 기록(추가만) → 나중에 결과와 맞춰 봄','Today’s Q·G → Lab forward-validation record (append-only) → later compared with outcomes']].map(x=>'<li>'+esc(T(l,...x))+'</li>').join('')+'</ul></section>'+
   '<section class="tree-examples card" data-tree-examples="system" aria-live="polite"><h2><span class="hl">'+esc(T(l,'예시 값','Example values'))+'</span></h2><p class="small">'+esc(T(l,'각 메뉴 아래 "예"는 공개 자료에서 읽은 값입니다. 없으면 NA와 이유를 씁니다.','Each “e.g.” under a menu is read from published data; otherwise NA and why.'))+'</p><div data-tree-example-body data-example-state="LOADED"></div></section></section>';
 }
 function systemExamples(host,l,screens,catalog){
  const set=(k,html)=>{const n=host.querySelector('[data-system-example="'+k+'"]');if(n)n.innerHTML=html;};
  const p=screens&&screens['sec-qgv2.json'];
  if(p&&object(p.records)){const codes=Object.keys(p.records).filter(c=>!c.startsWith('TARGET:'));const live=codes.filter(c=>p.records[c].state==='LIVE'&&finite(p.records[c].qg_axes?.Q?.score)).length;
   set('qgv',esc(T(l,'예: Q 산출 LIVE ','e.g. LIVE rows with Q: ')+live+' / '+codes.length+' · '+(p.as_of||'NA')));}
  else set('qgv',na(l,T(l,'sec-qgv2.json 없음','sec-qgv2.json missing')));
  set('technical',na(l,T(l,'가격 기반 · 공개 안 함(사용자 비공개 시트·이 브라우저)','price-based · never published (private sheet / this browser)')));
  const m=screens&&screens['macro-screen.json'],obs=Array.isArray(m?.data?.observations)?m.data.observations.length:0;
  set('macro',obs?esc(T(l,'예: 공개 관측 ','e.g. published observations: ')+obs+' · '+(m.as_of||'NA')):na(l,T(l,'공개 관측 없음','no published observation')));
  set('portfolio',object(catalog)&&Array.isArray(catalog.instruments)?esc(T(l,'예: TARGET ','e.g. TARGET ')+(catalog.target_root_version||'NA')+' · '+catalog.instruments.length+T(l,'종목',' instruments')):na(l,T(l,'목표 목록 없음','no target catalogue')));
  set('prompts',esc(T(l,'공식 카탈로그 · 동결본(PLV1)','Official catalogue · frozen (PLV1)')));
  set('lab',na(l,T(l,'검증 기록은 n+1.2 전진 검증 화면에서 읽습니다','Records are read on the n+1.2 forward-validation screen')));
  const SD=root.SecDisclosures;if(SD)Promise.resolve(shared('sec',SD)).then(sec=>{if(!host.isConnected)return;set('news',Array.isArray(sec?.events)?esc(T(l,'예: 8-K ','e.g. 8-K: ')+sec.events.length+T(l,'건 · ',' · ')+(sec.as_of||'NA')):na(l,T(l,'공시 파일 없음','no disclosure file')));}).catch(()=>{});
  else set('news',na(l,T(l,'공시 파일 없음','no disclosure file')));
 }
 const TREES={qgv:qgvTree,technical:technicalTree,macro:macroTree,news:newsTree,portfolio:portfolioTree,system:systemTree};
 function treeHtml(key,l){const f=TREES[key]||TREES.qgv;return f(l||'ko-KR');}
 // Fill the example values of the tree on the page from the data the app already loaded (and the public news files).
 function mount(host,{screens,catalog,locale}={}){
  const l=locale||'ko-KR',box=host&&host.querySelector('[data-tree-examples]');if(!box)return;const key=box.dataset.treeExamples,body=box.querySelector('[data-tree-example-body]');
  if(key==='system'){systemExamples(host,l,screens,catalog);return;}
  const put=html=>{if(body&&body.isConnected)body.outerHTML=html;};
  if(key==='qgv'){put(qgvExamples(l,screens));if(root.StatRadar)void root.StatRadar.mount(box);}
  else if(key==='macro')put(macroExamples(l,screens));
  else if(key==='portfolio')put(portfolioExamples(l,catalog));
  else if(key==='news')void newsExamples(l).then(put);
 }
 function technicalHtml(l){
  return '<p class="small" data-ia-group="technical">'+esc(T(l,'패턴·정도·감지 이력과 내 노트는 위 차트에서 사용합니다. 실가격 기준이 미확인인 구간은 판정 불가이며, 형태 일치도는 상승 확률이 아닙니다.','Use patterns, degree, detection history and personal notes in the chart above. Unconfirmed real-price basis means unavailable judgement; shape fit is not an upward probability.'))+'</p>';
 }
 // ---------- menu 3 매크로: functional stamp layout (design lane D7, 2026-10-20) ----------
 // Owner draft "투자시스템 화면 시안 (손그림 칠판)" with the functional hierarchy numbers 4.1–4.6 on the stamps (menu 3 /
 // sub-menus 3.1–3.6 stay on the strip above). The existing modules are placed, not changed: the cycle ring (4.1.1, 4.1.2 and
 // the ring parts of 4.1.5, 4.2, 4.3, 4.4), the evidence lines (4.1.3), the lights, board, raw axes and S09 sections (4.1.4/4.1.5).
 // parts = the markup app.js already builds ({lights, evidence, status, raw, canon}). The old sub-menu anchors
 // (#macro-cycle … #macro-chain) are the group ids. Nothing is computed here: no position, no probability, no example value
 // of the draft. States are fixed labels of what is connected today; the official layer stays in the ring ("미산출").
 function macroHtml(l,parts){
  const p=parts||{},x=(ko,en)=>esc(T(l,ko,en));
  const stamp=n=>'<span class="plab-stamp" data-fn="'+n+'">'+n+'</span>';
  const STATE={ready:['사용 가능','Available'],partial:['일부 연결','Partly connected'],frame:['화면 틀','Screen frame'],explore:['탐색 전용','Exploration only'],pending:['준비 중','In preparation'],na:['미산출','Not computed'],rule:['기준 미정','Criteria undecided']};
  const chip=k=>k?'<span class="plab-state" data-plab-state="'+(k==='frame'||k==='explore'?'partial':k)+'">'+x(...STATE[k])+'</span>':'';
  // "NOT_AVAILABLE" stays as text for the sub-menu contract (each 3.x section states it), on its own class (not .badge.NOT_AVAILABLE).
  const naLine=(ko,en)=>'<p class="mc-na"><span class="mc-na-code">NOT_AVAILABLE</span> '+x(ko,en)+'</p>';
  const link=(h,ko,en)=>'<a href="'+h+'">'+x(ko,en)+'</a>';
  const links=list=>'<p class="plab-links">'+list.map(a=>link(...a)).join('')+'</p>';
  const row=(ns,title,desc,state,body)=>'<li class="plab-row" data-fn-row="'+ns.join(' ')+'"><div class="plab-label"><h3>'+ns.map(stamp).join(' ')+' <span class="plab-title">'+title+'</span></h3>'+chip(state)+(desc?'<p class="plab-desc">'+desc+'</p>':'')+'</div><div class="plab-body">'+body+'</div></li>';
  const group=(n,id,menu,title,lede,rows,extra)=>'<section class="plab-group mc-group" id="'+id+'" data-fn-group="'+n+'" data-ia-item="'+menu+'" aria-labelledby="'+id+'-title"><h2 class="plab-head" id="'+id+'-title">'+stamp(n)+' <span class="hl">'+title+'</span></h2>'+(lede?'<p class="plab-lede">'+lede+'</p>':'')+(extra||'')+'<ol class="plab-rows">'+rows.join('')+'</ol></section>';
  const freq=x('확률 근거 = 과거 국면 전환 빈도: 같은 국면에서 다음 국면으로 넘어간 과거 횟수의 비율. 기간과 표본 수를 함께 적습니다. Lab에서 계산·검증하기 전에는 숫자를 쓰지 않습니다.','Probability basis = past phase-transition frequency: the share of past moves from the same phase to the next, shown with its period and sample size. No number before Lab computes and validates it.');
  const slots=(list)=>'<ul class="mc-slots">'+list.map(([ko,en])=>'<li><b>'+x(ko,en)+'</b><span data-na="NOT_AVAILABLE">—</span></li>').join('')+'</ul>';
  const conds=slots([['상향 조건','Up'],['유지 조건','Hold'],['하향 조건','Down']]);
  const prob=slots([['비율','Share'],['기간','Period'],['표본 수','Samples']]);
  const toRing=[['#macro-cycle-ring','4.1.1 링으로','To the 4.1.1 ring']];
  const show=root.MacroCycleRing&&Number.isInteger(root.MacroCycleRing.USER_SHOW)?root.MacroCycleRing.USER_SHOW:null;
  const g41=group('4.1','macro-cycle','3.1',x('경기 · 주식시장 국면','Economy · equity-market phases'),
   x('경기와 주식시장은 서로 다른 모델이고 따로 돕니다. 위치는 승인된 모델이 게시한 구간으로만 보입니다.','Economy and market are separate models that turn separately. A position appears only as an interval published by an approved model.'),[
   row(['4.1.1','4.1.2'],x('국면 그래프 · 국면 탐색','Phase graph · phase browsing'),x('개념도입니다. 칸 길이는 기간이 아닙니다. 돌리거나 국면을 눌러 근거 패턴·전환 조건을 봅니다. 링 안의 작은 도장도 기능 번호입니다.','A concept diagram; cell length is not time. Turn it or pick a phase to read its evidence pattern and transition conditions. The small stamps inside the ring are function numbers too.'),'frame',
    '<div id="macro-cycle-ring-root" data-cycle-ring-host></div>'),
   row(['4.1.3'],x('근거 세로선','Evidence lines'),x('공개 정부 통계를 실제 발표 시각에 세로선으로 그립니다. 발표 시각이 없으면 수집 시각으로 표시합니다. 탐색 화면이며 공식 위치·판정·확률에 쓰지 않습니다.','Public government statistics drawn as vertical lines at their real release time; collection time is shown when release time is unknown. Exploration only; never used for an official position, judgement or probability.'),'explore',
    p.evidence||''),
   row(['4.1.4'],x('기존 지표 연결','Existing indicator links'),x('경고등 5개(참고 모드) · 8축 원자료 · 기존 화면 절. 국면 링과 섞지 않습니다.','The five lights (reference mode), the 8-axis raw data and the existing sections. Never mixed into the phase rings.'),'ready',
    (p.lights||'')+(p.raw||'')+(p.canon||'')),
   row(['4.1.5'],x('판단 상태','Judgement state'),x('공식 판정은 각 링의 「공식 판정」 줄이 기준입니다. 게시된 모델 출력이 없으면 미산출로 둡니다.','The official judgement is the “Official judgement” line of each ring. Without a published model output it stays not computed.'),'na',
    '<ul class="plab-rules mc-layers"><li>'+x('공식 층: 위치 · 확률 = 승인된 모델이 게시한 것만. 그 전에는 미산출.','Official layer: position and probability only as published by an approved model; until then not computed.')+'</li><li>'+
     x('사용자 층: 내 추정은 이 기기에만 따로 저장하고 공식 층에 섞지 않습니다(4.4).','User layer: your estimate is kept apart on this device and never mixed into the official layer (4.4).')+'</li><li>'+
     x('탐색 층: 근거 세로선은 판정에 쓰지 않습니다(4.1.3).','Exploration layer: evidence lines are never used for a judgement (4.1.3).')+'</li></ul>'+(p.status||''))]);
  const g42=group('4.2','macro-rotation','3.2',x('순환매','Sector rotation'),
   x('4.1 국면 위에서 저점 · 고점 어디쯤인지와, 다음으로 옮길 조건 · 확률을 붙이는 자리입니다.','Where the trough/peak position on the 4.1 phases goes, with the conditions and probability of the next move.'),[
   row(['4.2.1'],x('위치 (저점 · 고점)','Position (trough · peak)'),x('순환매 위치 모델이 없어 점 · 구간을 그리지 않습니다.','No rotation model, so no point or interval is drawn.'),'na',links(toRing)),
   row(['4.2.2'],x('조정 조건','Adjustment conditions'),x('상향 · 유지 · 하향 조건. 각 국면 설명(4.1.2) 안의 같은 칸과 이어집니다.','Up / hold / down conditions, the same boxes as in each phase panel (4.1.2).'),'rule',conds),
   row(['4.2.3'],x('확률','Probability'),freq,'na',prob)],
   naLine('순환매 모델과 검증된 전환 빈도가 없습니다.','There is no rotation model and no validated transition frequency.'));
  const g43=group('4.3','macro-industry','3.3',x('SIC 산업 사이클','SIC industry cycles'),
   x('QGV와 같은 업종 그룹 키(sic_industry_groups/v0)로 산업을 골라 위치 · 조건 · 확률을 봅니다.','Pick an industry by the same group key as QGV (sic_industry_groups/v0) to see its position, conditions and probability.'),[
   row(['4.3.1'],x('산업 선택','Choose an industry'),x('링의 「SIC 산업」 탭에서 공개 sec-qgv2.json의 업종 그룹을 고릅니다. 산업 어휘는 미정입니다.','Choose a group from the public sec-qgv2.json in the ring’s “SIC industry” tab. The industry vocabulary is undecided.'),'partial',links(toRing)),
   row(['4.3.2'],x('현재 예상 위치','Current estimated position'),x('산업별 사이클 위치 모델이 없어 위치를 그리지 않습니다.','No industry-cycle model, so no position is drawn.'),'na',''),
   row(['4.3.3'],x('조정 조건과 확률','Conditions and probability'),freq,'na',conds+prob)],
   naLine('산업별 사이클 모델이 없습니다.','There is no industry-cycle model.'));
  const g44=group('4.4','macro-mine','3.4',x('사용자 국면 판단','My phase judgement'),
   x('내가 고른 위치는 공식 판정이 아닙니다. 보라색 점선으로 따로 그리고 점수에 쓰지 않습니다.','Your chosen position is not an official judgement. It is drawn apart as a dashed purple line and never scored.'),[
   row(['4.4.1'],x('위치 선택','Choose a position'),x('각 링 아래 「사용자 추정」 칸에서 시작 · 끝 구간과 근거(선택)를 고릅니다.','In the “User estimate” box under each ring, choose a from/to interval and an optional reason.'),'ready',links(toRing)),
   row(['4.4.2'],x('저장과 비교','Save and compare'),x('이 기기에만 저장합니다. 기록마다 그때의 시스템 표시를 함께 남겨 비교합니다. 기록은 모두 보관하고 화면에는 최근 기록만 보입니다.','Saved on this device only. Each record keeps what the system showed then, for comparison. Every record is kept; the screen shows the latest ones.')+(show?' '+x('(최근 '+show+'개)','(latest '+show+')'):''),'ready',
    '<p>'+x('파일 내보내기 · 가져오기(합치기)로 옮깁니다. 계정 동기화는','Move them with file export / import (merge). Account sync is')+' '+chip('pending')+'</p>')],
   naLine('로그인 계정 간 동기화는 없습니다(저장 위치 결정 DRAW-STORE · IA-6).','There is no sync between signed-in devices (storage decision DRAW-STORE · IA-6).'));
  const chainBox=(ko,en)=>'<li><b>'+x(ko,en)+'</b><span data-na="NOT_AVAILABLE">—</span></li>';
  const g45=group('4.5','macro-chain','3.5',x('연쇄 효과 지도','Causal-chain map'),
   x('사건 → 원인 고리 → 영향받는 기업. 고리마다 근거 · 시차 · 확신도를 붙입니다. 방향 · 크기 · 확률은 만들지 않습니다.','Event → causal links → affected companies, each link with evidence, lag and confidence. No direction, size or probability is made.'),[
   row(['4.5.1'],x('사건 · 출발점','Event · starting point'),x('공시 · 뉴스 사건, 또는 매크로 동인 · 기술 · 밸류체인 단계 같은 개념.','A filing or news event, or a concept such as a macro driver, technology or value-chain stage.'),'pending',''),
   row(['4.5.2'],x('원인 고리','Causal links'),x('걸음마다 사실 · 추론 · 가설을 나눕니다. 한 걸음이라도 가설이면 경로 전체가 가설입니다.','Each step is fact, inference or hypothesis; one hypothesis step makes the whole path a hypothesis.'),'pending',''),
   row(['4.5.3'],x('영향받는 기업','Affected companies'),x('관계망과 같은 관계 자료를 씁니다.','Uses the same relationship data as the company network.'),'pending',links([['#news-network','뉴스 4.1 · 관계망','News 4.1 · network']])),
   row(['4.5.4'],x('근거 · 시차 · 확신도','Evidence · lag · confidence'),x('전제 · 시차 · 반대 경로 · 상쇄 요인 · 반증 조건 · 근거(발표 시각). 사람이 적거나 근거 문서에서 옮기며 자동으로 만들지 않습니다.','Premises, lag, counter-paths, offsets, falsifiers and evidence (release time), written by a person or taken from a source, never generated.'),'rule',
    '<p class="small">'+x('확신도 숫자는 검증 전에는 쓰지 않습니다.','No confidence number before validation.')+'</p>')],
   naLine('사건 → 고리 → 기업 지도는 화면이 없습니다(관계 자료원 결정 REL-SOURCE).','The event → link → company map has no screen yet (relationship source decision REL-SOURCE).')+
   '<ol class="mc-chain" aria-label="'+x('연쇄 효과 지도 틀 · 빈 칸','Causal-chain map frame · empty')+'">'+chainBox('사건','Event')+chainBox('원인 고리','Causal links')+chainBox('영향받는 기업','Affected companies')+'</ol>');
  const g46='<section class="plab-group mc-group mc-tree" data-fn-group="4.6" data-ia-item="3.6" aria-labelledby="mc-46-title"><h2 class="plab-head" id="mc-46-title">'+stamp('4.6')+' <span class="hl">'+x('내용구성 트리','Content structure tree')+'</span></h2>'+
   '<p class="plab-lede">'+x('입력 → 경고등 · 상태판 → 위치 · 순환매 · 산업 사이클 → 연쇄 효과를 한 장으로 봅니다. 예시 값은 공개 자료에서만 읽습니다.','Inputs → lights · board → position · rotation · industry cycles → chains on one page. Example values come from published data only.')+'</p>'+
   links([['#tree/macro','3.6 구조 트리 열기','Open the 3.6 structure tree']])+'</section>';
  return '<div class="mc-screen" data-ia-group="macro"><p class="plab-note" data-fn-note>'+x('도장 번호(4.x)는 기능 번호입니다. 위 메뉴 번호(3, 3.1~3.6)와 다릅니다.','Stamp numbers (4.x) are function numbers, not the menu numbers above (3, 3.1–3.6).')+'</p>'+
   '<p class="mc-legend">'+x('공식 국면 · 확률 = 승인된 모델이 게시할 때만 · 내 추정 = 보라색 점선, 이 기기에만 · 근거 세로선 = 탐색 전용','Official phase and probability = only when an approved model publishes · my estimate = dashed purple, this device only · evidence lines = exploration only')+'</p>'+
   g41+g42+g43+g44+g45+g46+'</div>';
 }
 root.IaScreens=Object.freeze({treeHtml,mount,technicalHtml,macroHtml,TREE_KEYS:Object.freeze(Object.keys(TREES))});
})(window);
