/* Owner IA screens (PRODUCT_IA_DIRECTIVE_20261018): the structure trees (1.4 QGV, 2.4 기술적 분석, 3.6 매크로, 4.3 뉴스,
   5.4 포트폴리오, n 전체 시스템) and the numbered sections that have no engine yet (2.2, 2.3, 3.1–3.5).
   The trees describe the real system. Weights and rules are read at runtime from the engine modules (QgvV2, SecQgv2,
   ResearchIndicators, MacroLights, VirtualTrading); nothing here restates a number of its own. "예시 값" under a tree come
   only from published public data already loaded by the app (sec-qgv2.json, macro-screen.json, sec-disclosures.json,
   news-signals.json, actual-catalog.json), each with its file and time. Where no real value exists the example says NA
   and why; a price-based value is never shown here (prices stay on the device, GSQ-010). Sections without an engine say
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
   node('extra',esc(T(l,'스탯창(레이더) — QGV가 못 담는 것','Stat window (radar) — what QGV misses')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'축·공식·비교군 결정 대기(RADAR-AXES, IA-10). 그림을 만들지 않습니다.','Axes, formulas and peer groups pending (RADAR-AXES, IA-10). Nothing is drawn.')))]);
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
   '</div>';
 }
 // ---------- 2.4 기술적 분석 ----------
 function technicalTree(l){
  const tree=node('root',esc(T(l,'기술적 분석','Technical analysis')),esc(T(l,'QGV 점수와 나란히 볼 뿐 합치지 않습니다.','Shown next to QGV, never merged into it.')),[
   node('input',esc(T(l,'입력','Inputs')),esc(T(l,'일봉(이 기기 RAM · 비공개 Worker · 내 시트) · 가격 기준 RAW_CLOSE / PROVIDER_ADJUSTED_CLOSE','Daily bars (this device’s RAM · private Worker · my sheet) · price basis RAW_CLOSE / PROVIDER_ADJUSTED_CLOSE'))),
   node('','2.1 '+esc(T(l,'지표','Indicators')),esc(T(l,'연구 표시용(RESEARCH_DISPLAY_ONLY) · 매개변수는 지금 고정 · "정도" 선택은 미구현','Research display only · parameters fixed today · “degree” presets not built')),[
    leaf('SMA','5 · 20 · 60 · 120 (· 240)'),leaf('EMA','20'),leaf('RSI','14'),leaf('MACD','12 · 26 · 9'),leaf(esc(T(l,'볼린저','Bollinger')),'20 · 2σ'),leaf('ATR','14 · RAW_CLOSE')]),
   node('','2.1 '+esc(T(l,'신호 카드','Signal cards')),esc(T(l,'추세·모멘텀 등 상태 카드(technical-cards.js) · 실행 구간·기록은 NOT_AVAILABLE','Trend/momentum state cards (technical-cards.js) · execution zone and record NOT_AVAILABLE'))),
   node('','2.2 '+esc(T(l,'차트 패턴','Chart patterns')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'설계만(FORMED·CONFIRMED·FAILED·INVALIDATED·EXPIRED). 형태 적합도는 상승 확률이 아님','Design only (FORMED · CONFIRMED · FAILED · INVALIDATED · EXPIRED). Shape fit is not a probability'))),
   node('','2.1–2.2 '+esc(T(l,'가격 시나리오','Price scenarios')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'확률 근거 = 같은 패턴·정도에서 과거 결과 빈도 · 미산출','Probability basis = past outcome frequency for the same pattern and degree · not computed'))),
   node('','2.3 '+esc(T(l,'내 노트(보라색 펜)','My notes (purple pen)')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'저장 위치 결정 대기(DRAW-STORE) · 공식 증거로 쓰지 않음','Storage pending (DRAW-STORE) · never official evidence')))]);
  const ex='<div data-tree-example-body data-example-state="NOT_AVAILABLE"><p>'+na(l,T(l,'기술적 분석 값은 가격에서 나옵니다. 가격은 이 기기에서만 계산하고 공개하지 않으므로 이 화면에 예시 값이 없습니다. 2.1 화면에서 내 기기 값을 볼 수 있습니다.','Technical values come from prices, which stay on this device and are never published, so no example is shown here. See your device values on 2.1.'))+'</p><p><a href="#technical">2.1 '+esc(T(l,'지표 · 시나리오 →','Indicators →'))+'</a></p></div>';
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
   node('','3.1 '+esc(T(l,'경기·시장 위치 + 근거선','Economy · market position + evidence lines')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'위치 판정 모델 없음','No position model'))),
   node('','3.2 '+esc(T(l,'순환매 위치','Sector rotation')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'확률 근거 = 과거 국면 전환 빈도 · 미산출','Probability basis = past regime-transition frequency · not computed'))),
   node('','3.3 '+esc(T(l,'산업 사이클 (SIC 업종 그룹)','Industry cycles (SIC groups)')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'확률 근거 = 과거 국면 전환 빈도 · 미산출','Probability basis = past regime-transition frequency · not computed'))),
   node('','3.4 '+esc(T(l,'내가 고른 위치','My chosen position')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'시스템 값과 따로 저장 예정','Will be stored apart from the system value'))),
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
  try{[sec,news]=await Promise.all([SD?SD.load(root):null,NS?NS.load(root):null]);}catch(_){sec=null;news=null;}
  const ev=Array.isArray(sec?.events)?[...sec.events].sort((a,b)=>String(b.accepted_at).localeCompare(String(a.accepted_at))):[],it=Array.isArray(news?.items)?[...news.items].sort((a,b)=>String(b.published_at).localeCompare(String(a.published_at))):[];
  const line=(label,file,p,rows,show)=>'<div><dt>'+esc(label)+'</dt><dd data-example-source="'+file+'" data-example-count="'+(p?rows.length:'NA')+'">'+(p?esc(rows.length+T(l,'건 · 파일 기준 ',' items · file as of ')+(p.as_of||'NA'))+(rows[0]?'<br><span class="small">'+esc(T(l,'최신: ','Latest: ')+show(rows[0]))+'</span>':''):na(l,T(l,'파일을 읽을 수 없습니다.','File could not be read.')))+'</dd></div>';
  return '<div data-tree-example-body data-example-state="'+(sec||news?'LOADED':'NOT_AVAILABLE')+'"><p class="small">'+esc(T(l,'공개 파일의 건수와 가장 최근 한 건입니다.','Counts and the newest item of the public files.'))+'</p><dl class="tree-facts">'+
   line(T(l,'SEC 8-K','SEC 8-K'),'sec-disclosures.json',sec,ev,e=>String(e.company_id).toUpperCase()+' · '+e.form+' · '+(Array.isArray(e.items)?e.items.join(','):'')+' · '+e.accepted_at)+
   line(T(l,'뉴스·IR','News · IR'),'news-signals.json',news,it,i=>String(i.company_id).toUpperCase()+' · '+i.source+' · '+i.classification+' · '+i.published_at)+
   '<div><dt>'+esc(T(l,'관계','Relations'))+'</dt><dd>'+na(l,T(l,'관계 자료 없음(REL-SOURCE)','No relationship data (REL-SOURCE)'))+'</dd></div></dl></div>';
 }
 // ---------- 5.4 포트폴리오 ----------
 function portfolioTree(l){
  const VT=root.VirtualTrading?.CONFIG;
  const tree=node('root',esc(T(l,'포트폴리오','Portfolio')),esc(T(l,'실거래 없음 · 장부는 추가만(덮어쓰지 않음)','No real trades · ledgers are append-only')),[
   node('','5.1 '+esc(T(l,'모델 적합 포트폴리오','Model portfolio')),'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,'모델 포트폴리오 생성기 없음. 확정 목표(TARGET)는 따로 표시','No model generator yet. The confirmed TARGET is shown separately'))),
   node('','5.1 '+esc(T(l,'내 포트폴리오','My portfolio')),esc(T(l,'실제 보유(ACTUAL) · 이 기기 IndexedDB / 내 비공개 시트 · 공개하지 않음','Actual holdings · this device / my private sheet · never published'))),
   node('','5.1 '+esc(T(l,'모의 포트폴리오','Paper portfolio')),esc(T(l,'가상 매매 세트 A~D + 규칙대로 했다면(SHADOW)','Virtual sets A–D + “if the rules were followed” (SHADOW)')+(VT?' · '+VT.config_version+' · '+T(l,'시작 ','start ')+VT.start_date:'')),[]),
   node('','5.2 '+esc(T(l,'일일 보고','Daily report')),esc(T(l,'템플릿 v1 · 주간 보고는 결정 대기(WEEKLY-REPORT)','Template v1 · weekly report pending (WEEKLY-REPORT)'))),
   node('','5.3 '+esc(T(l,'모의 일일 보고','Paper daily report')),esc(T(l,'세트별 보고 · 비교','Per set · compare'))),
   node('',esc(T(l,'보고 불가 → 프롬프트','Cannot report → prompt')),esc(T(l,'사유 코드 → 최소 누락 입력 → 복사할 프롬프트(금액 없음) → AI 답 검토 후 저장','Reason code → smallest missing input → prompt to copy (no amounts) → review the AI answer, then save')))]);
  return page('portfolio',l,{eyebrow:'5.4 · PORTFOLIO STRUCTURE',title:T(l,'포트폴리오 시스템 내용구성','Portfolio structure'),lede:T(l,'모델 · 내 것 · 모의 → 매일 보고 → 보고 불가 시 프롬프트.','Model · mine · paper → daily report → prompt when a report cannot be made.'),tree,examples:loading(l)});
 }
 function portfolioExamples(l,catalog){
  const ok=object(catalog)&&Array.isArray(catalog.instruments);
  return '<div data-tree-example-body data-example-state="'+(ok?'LOADED':'NOT_AVAILABLE')+'"'+(ok?' data-example-source="actual-catalog.json"':'')+'><p class="small">'+esc(T(l,'실제 보유는 예시로 쓰지 않습니다. 공개 목표 목록만 읽습니다.','Actual holdings are never used as examples. Only the public target catalogue is read.'))+'</p><dl class="tree-facts">'+
   '<div><dt>TARGET</dt><dd data-example-count="'+(ok?catalog.instruments.length:'NA')+'">'+(ok?esc(T(l,'확정 목표 ','Confirmed target ')+(catalog.target_root_version||'NA')+' · '+catalog.instruments.length+T(l,'종목',' instruments')+(Array.isArray(catalog.themes)?' · '+catalog.themes.length+T(l,'개 테마',' themes'):'')):na(l,T(l,'actual-catalog.json을 읽을 수 없습니다.','actual-catalog.json could not be read.')))+'</dd></div>'+
   '<div><dt>MODEL</dt><dd>'+na(l,T(l,'생성기 없음','No generator'))+'</dd></div>'+
   '<div><dt>ACTUAL · PAPER</dt><dd>'+na(l,T(l,'개인 자료 · 이 기기에만 있음','Personal data · on this device only'))+'</dd></div></dl></div>';
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
  set('technical',na(l,T(l,'가격 기반 · 이 기기에서만','price-based · device only')));
  const m=screens&&screens['macro-screen.json'],obs=Array.isArray(m?.data?.observations)?m.data.observations.length:0;
  set('macro',obs?esc(T(l,'예: 공개 관측 ','e.g. published observations: ')+obs+' · '+(m.as_of||'NA')):na(l,T(l,'공개 관측 없음','no published observation')));
  set('portfolio',object(catalog)&&Array.isArray(catalog.instruments)?esc(T(l,'예: TARGET ','e.g. TARGET ')+(catalog.target_root_version||'NA')+' · '+catalog.instruments.length+T(l,'종목',' instruments')):na(l,T(l,'목표 목록 없음','no target catalogue')));
  set('prompts',esc(T(l,'공식 카탈로그 · 동결본(PLV1)','Official catalogue · frozen (PLV1)')));
  set('lab',na(l,T(l,'검증 기록은 n+1.2 전진 검증 화면에서 읽습니다','Records are read on the n+1.2 forward-validation screen')));
  const SD=root.SecDisclosures;if(SD)Promise.resolve(SD.load(root)).then(sec=>{if(!host.isConnected)return;set('news',Array.isArray(sec?.events)?esc(T(l,'예: 8-K ','e.g. 8-K: ')+sec.events.length+T(l,'건 · ',' · ')+(sec.as_of||'NA')):na(l,T(l,'공시 파일 없음','no disclosure file')));}).catch(()=>{});
  else set('news',na(l,T(l,'공시 파일 없음','no disclosure file')));
 }
 const TREES={qgv:qgvTree,technical:technicalTree,macro:macroTree,news:newsTree,portfolio:portfolioTree,system:systemTree};
 function treeHtml(key,l){const f=TREES[key]||TREES.qgv;return f(l||'ko-KR');}
 // Fill the example values of the tree on the page from the data the app already loaded (and the public news files).
 function mount(host,{screens,catalog,locale}={}){
  const l=locale||'ko-KR',box=host&&host.querySelector('[data-tree-examples]');if(!box)return;const key=box.dataset.treeExamples,body=box.querySelector('[data-tree-example-body]');
  if(key==='system'){systemExamples(host,l,screens,catalog);return;}
  const put=html=>{if(body&&body.isConnected)body.outerHTML=html;};
  if(key==='qgv')put(qgvExamples(l,screens));
  else if(key==='macro')put(macroExamples(l,screens));
  else if(key==='portfolio')put(portfolioExamples(l,catalog));
  else if(key==='news')void newsExamples(l).then(put);
 }
 // ---------- numbered sections without an engine (2.2, 2.3, 3.1–3.5): what is missing, no invented value ----------
 function naSection(id,sec,l,title,what,needs){
  return '<section class="card ia-na" id="'+id+'" data-ia-item="'+esc(sec)+'" aria-labelledby="'+id+'-title"><h2 id="'+id+'-title"><span class="ia-sec">'+esc(sec)+'</span> '+esc(T(l,...title))+'</h2>'+
   '<p><span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> '+esc(T(l,...what))+'</p><ul class="ia-needs">'+needs.map(x=>'<li>'+esc(T(l,...x))+'</li>').join('')+'</ul></section>';
 }
 function technicalHtml(l){
  return '<div class="ia-na-group" data-ia-group="technical">'+
   naSection('technical-pattern','2.2',l,['차트 패턴 + 정도 + 시나리오','Chart patterns + degree + scenarios'],['패턴 엔진과 공식 이력이 없습니다. 패턴·목표선·무효선·확률을 그리지 않습니다.','There is no pattern engine or official history. No pattern, target, invalidation line or probability is drawn.'],
    [['패턴 규칙(pattern-rules/1)과 상태 FORMED·CONFIRMED·FAILED·INVALIDATED·EXPIRED는 설계만 있음','Pattern rules (pattern-rules/1) and states exist as design only'],['"정도" = 일치도 문턱값 묶음(매개변수 묶음 버전) 결정 필요','“Degree” = match-threshold presets (versioned parameter sets) to be decided'],['시나리오 확률 근거 = 같은 패턴·정도에서 과거 결과 빈도 · 미산출','Scenario probability basis = past outcome frequency for the same pattern and degree · not computed'],['착수 결정 TA-G1~G3','Start decisions TA-G1–G3']])+
   naSection('technical-notes','2.3',l,['차트 위 내 노트','My notes on the chart'],['그리기·저장 기능이 아직 없습니다. 내 그림은 보라색 펜으로 구분할 예정이며, 공식 증거로 쓰지 않습니다.','Drawing and saving are not built yet. Your drawings will use a purple pen and are never official evidence.'],
    [['저장 위치 결정(DRAW-STORE): 이 브라우저 / 비공개 시트 / 로그인','Storage decision (DRAW-STORE): this browser / private sheet / account'],['좌표 기준: 종목 · 봉 주기 · 가격 기준 · 시간/가격(chart-annotation/1)','Anchors: listing · interval · price basis · time/price (chart-annotation/1)']])+'</div>';
 }
 function macroHtml(l){
  const freq=['확률 근거 = 과거 국면 전환 빈도: 같은 국면에서 다음 국면으로 넘어간 과거 횟수의 비율, 기간·표본 수와 함께. Lab 검증 전에는 미산출','Probability basis = past regime-transition frequency: share of past moves from the same phase to the next, with period and sample size. Not computed before Lab validation'];
  return '<div class="ia-na-group" data-ia-group="macro">'+
   naSection('macro-cycle','3.1',l,['경기 · 주식시장 현재 예상 위치 + 근거선','Economy and market position + evidence lines'],['위치 판정 모델과 시계열 이력이 없습니다. 위치 점·근거 세로선을 그리지 않습니다. 위의 상태판·경고등이 지금의 매크로입니다.','There is no position model or time-series history. No position dot or evidence line is drawn. The board and lights above are today’s macro.'],
    [['국면 어휘 고정(IA-4: 확장·둔화·수축·회복 / 상승 초기·상승 후기·하락·바닥)','Phase vocabulary (IA-4)'],['근거선 시각: 실제 발표 시각 필요(IA-16, 지금은 수집 상한)','Evidence time: real release time needed (IA-16; today a capture bound)']])+
   naSection('macro-rotation','3.2',l,['순환매 위치(저점·고점) + 조건 · 확률','Sector rotation (trough/peak) + conditions · probability'],['순환매 모델이 없습니다. 상향·유지·하향 조건과 확률은 미산출입니다.','No rotation model. Up / hold / down conditions and probabilities are not computed.'],[freq,['산업 단위 결정(IA-5)','Industry unit (IA-5)']])+
   naSection('macro-industry','3.3',l,['산업 사이클 (SIC 업종 그룹)','Industry cycles (SIC groups)'],['산업별 사이클 위치 모델이 없습니다. 위치·확률을 그리지 않습니다.','No industry-cycle model. No position or probability is drawn.'],[freq,['키 = QGV와 같은 industry_group(sic_industry_groups/v0)','Key = the same industry_group as QGV']])+
   naSection('macro-mine','3.4',l,['내가 고르는 현재 위치','My chosen position'],['선택·저장 기능이 아직 없습니다. 내 위치는 시스템 값과 따로 저장하고 점수에 쓰지 않을 예정입니다.','Choosing and saving are not built. Your position will be stored apart from the system value and never scored.'],[['저장 위치 결정(DRAW-STORE · IA-6)','Storage decision (DRAW-STORE · IA-6)']])+
   naSection('macro-chain','3.5',l,['연쇄 효과 지도','Causal-chain map'],['사건 → 원인 고리 → 영향받는 기업 지도는 아직 화면이 없습니다. 확인된 관계·추론·가설을 나눠 보여 줄 예정이며 방향·크기·확률은 만들지 않습니다.','The event → chain → affected companies map has no screen yet. It will separate confirmed relations, inferences and hypotheses, with no direction, size or probability.'],
    [['관계 자료원 결정(REL-SOURCE)','Relationship source (REL-SOURCE)'],['고리마다 근거·시차·반대 경로·반증 필드','Per-link evidence, lag, counter-path and falsifier fields']])+'</div>';
 }
 root.IaScreens=Object.freeze({treeHtml,mount,technicalHtml,macroHtml,TREE_KEYS:Object.freeze(Object.keys(TREES))});
})(window);
