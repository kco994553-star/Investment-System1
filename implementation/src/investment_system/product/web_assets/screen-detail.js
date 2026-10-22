/* S09 macro and S10 validation canon sections, and the stamp layout of menu 6 (7.1) and menu n+1 Lab (9.1 / 9.2). Static markup only: every value is NOT_AVAILABLE with a reason
   (static guidance too: the 9.1 readiness checklist names documents and decision IDs, never a result; the personalisation order is a fixed explanation)
   (live raw values render in #public-macro from macro-screen.json).
   No inputs are connected, no numbers are invented, nothing is fetched, stored or sent. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ScreenDetail=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const na='<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span>';
 const pick=locale=>(ko,en)=>locale==='en-US'?en:ko;
 const dash='<span data-na="NOT_AVAILABLE">—</span>';
 function table(heads,rows){return `<div class="table-wrap"><table><thead><tr>${heads.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;}
 // S09: sections that follow the 8x6 axis grid. Inputs and the 8-axis mapping await user decisions; FRED/ALFRED are not used.
 function macroHtml(locale){
  const x=pick(locale);
  const wait=x('축별 상태 판정과 8축 국면 대응표는 보류 중이며 FRED/ALFRED는 사용하지 않습니다.','Per-axis state rules and the 8-axis regime mapping are deferred; FRED/ALFRED are not used.');
  // Growth/Inflation series ids are the user's 2026-10-11 v0 defaults (UNCALIBRATED, editable later); values come from macro-screen.json only.
  const v0=`<p data-macro-v0-series><span class="badge">${x('v0 기본값 · UNCALIBRATED','v0 default · UNCALIBRATED')}</span> Growth = BEA NIPA T10101 line 1 (A191RL, ${x('발표된 전기비 연율 % ÷ 100','published q/q annualized % ÷ 100')}) · Inflation = BLS CUUR0000SA0 (CPI-U NSA, ${x('전년 동월 대비','year over year')}). ${x('기존 MacroEngine v0.1.1 임계값에만 넣으며 국면은 NOT_AVAILABLE입니다.','They feed only the existing MacroEngine v0.1.1 thresholds; the regime stays NOT_AVAILABLE.')}</p>`;
  // Other 6 axes (user decision 2026-10-11): raw display only, regime judgement deferred. Values come from macro-screen.json only.
  const raw=`<p data-macro-raw-series><span class="badge">v0 · 원자료 표시 · 국면 판정 보류</span> Labor = BLS LNS14000000 (${x('실업률 SA, 발표 % ÷ 100','unemployment rate SA, published % ÷ 100')}) · Monetary Policy = Fed H.15 RIFSPFF_N.B (${x('영업일 월평균 ÷ 100','monthly mean of business days ÷ 100')}) · Liquidity = Fed H.4.1 ${x('총자산 수요일 잔액, 52주 전 대비','total assets Wednesday level vs 52 weeks earlier')} · Credit = Fed H.8 ${x('상업은행 bank credit SA, 12개월 전 대비','commercial bank credit SA vs 12 months earlier')} · Fiscal = Treasury MTS Table 1 current_month_dfct_sur_amt (${x('최근 12개월 합계','sum of latest 12 months')}). ${x('FX는 공개 가격 경계에 따라 표시하지 않습니다.','FX is not shown under the public price boundary.')}</p>`;
  return `<section class="card" id="macro-equity-state" data-macro-section="equity-state"><h2>${x('주식시장 상태 (참고 · 원인 축 아님)','Equity market state (reference · not a causal axis)')}</h2>
   <p>${na} ${x('변동성·상승 종목 폭·추세에 쓸 입력이 연결되지 않았습니다.','No inputs are connected for volatility, breadth or trend.')}</p>
   <dl class="kv"><dt>${x('변동성','Volatility')}</dt><dd data-na="NOT_AVAILABLE">—</dd><dt>${x('상승 종목 폭','Breadth')}</dt><dd data-na="NOT_AVAILABLE">—</dd><dt>${x('추세','Trend')}</dt><dd data-na="NOT_AVAILABLE">—</dd></dl></section>
  <section class="card" id="macro-regime-history" data-macro-section="regime-history"><h2>${x('국면 이력 (5년)','Regime history (5 years)')}</h2>
   <p>${na} ${x('금리·물가·유동성·성장 겹쳐 보기에 쓸 국면 기록이 없습니다. 합성 이력을 만들지 않습니다.','No regime record exists to overlay rates, inflation, liquidity and growth. No synthetic history is made.')}</p></section>
  <section class="card" id="macro-signal-evidence" data-macro-section="signal-evidence"><h2>${x('신호 → 근거','Signal → evidence')}</h2>
   ${v0}${raw}<p>${na} ${wait}</p>
   ${table([x('신호','Signal'),x('강도','Strength'),x('지표','Indicator'),x('값','Value'),x('발표일','Release date'),x('이용 가능 시점','Available at')],[[dash,dash,dash,dash,dash,dash]])}</section>
  <section class="card" id="macro-scenarios" data-macro-section="scenarios"><h2>${x('시나리오 (확률 검증 전)','Scenarios (before probability validation)')}</h2>
   <p>${na} ${x('시나리오 3개와 확률은 검증이 끝난 뒤에만 표시합니다. 숫자 확률을 임의로 채우지 않습니다.','Three scenarios and their probabilities appear only after validation. No numeric probability is filled in.')}</p>
   ${table([x('시나리오','Scenario'),x('확률','Probability')],[['S1',dash],['S2',dash],['S3',dash]])}</section>
  <section class="card" id="macro-transmission" data-macro-section="transmission"><h2>${x('영향 전달','Impact transmission')}</h2>
   <p>${na} ${x('요인 → 경제 경로 → 업종 → 기업 → Q·G·V 맥락(유리·중립·불리) 연결은 매크로 8축 대응표가 확정되기 전에는 만들지 않습니다.','The chain factor → economic path → industry → company → Q·G·V context (favorable / neutral / unfavorable) is not built before the 8-axis mapping is confirmed.')}</p>
   <ol class="chain" data-transmission-chain>${[['요인','Factor'],['경제 경로','Economic path'],['업종','Industry'],['기업','Company'],['Q·G·V 맥락','Q·G·V context']].map(([k,e])=>`<li>${x(k,e)} ${dash}</li>`).join('')}</ol></section>`;
 }
 // Stamp layout shared by menu 6 (프롬프트 라이브러리) and menu n+1 (Lab), owner draft "투자시스템 화면 시안 (손그림 칠판)".
 // Stamp numbers are the functional hierarchy (7.1.x, 9.x), not the menu numbers. Presentation only: states are
 // fixed labels of what is connected today; live values stay in the screens they come from (no number is made up).
 const STATE={ready:['사용 가능','Available'],partial:['일부 연결','Partly connected'],pending:['준비 중','In preparation'],na:['미산출','Not computed'],rule:['조건','Condition'],
  checked:['✓ 확인됨','✓ Checked'],decide:['결정 대기','Awaiting decision']};
 const stamp=n=>`<span class="plab-stamp" data-fn="${n}">${n}</span>`;
 const chip=(x,k)=>k?`<span class="plab-state" data-plab-state="${k}">${x(...STATE[k])}</span>`:'';
 const note=(x,ko,en)=>`<p class="plab-note" data-fn-note>${x(ko,en)}</p>`;
 function row(x,n,title,desc,state,body,attrs=''){
  return `<li class="plab-row" data-fn-row="${n}"${attrs}><div class="plab-label"><h3>${stamp(n)} <span class="plab-title">${title}</span></h3>${chip(x,state)}<p class="plab-desc">${desc}</p></div><div class="plab-body">${body}</div></li>`;}
 const doodle=name=>{const d=typeof globalThis!=='undefined'&&globalThis.Doodles;return d&&d.icon?d.icon(name,'plab-doodle'):'';};
 function group(x,n,id,title,lede,rows,extra=''){
  return `<section class="plab-group" data-fn-group="${n}" aria-labelledby="${id}"><h2 class="plab-head" id="${id}">${stamp(n)} <span class="hl">${title}</span>${doodle(n.startsWith('7')?'prompts':'lab')}</h2>${lede?`<p class="plab-lede">${lede}</p>`:''}${extra}<ol class="plab-rows">${rows.join('')}</ol></section>`;}
 const links=list=>`<p class="plab-links">${list.map(([h,t])=>`<a href="${h}">${t}</a>`).join('')}</p>`;
 // Menu 6 · 7.1 프롬프트 탐색·사용·개인화. The library itself (frameHtml) is the existing frozen-catalog page, unchanged.
 function promptsHtml(locale,frameHtml){
  const x=pick(locale);
  const rows=[
   row(x,'7.1.1',x('분야별 탐색','Browse by field'),x('공식 카탈로그(동결본)의 영역 바로가기 · 키워드 · 역할 · 범위 · Starter · Bundle.','Domain shortcuts, keyword, role, scope, Starter and Bundle over the frozen official catalogue.'),'ready',
    `<p>${x('뉴스·포트폴리오·백테스트 영역은 공식 카탈로그에 아직 없습니다.','News, portfolio and backtest domains are not in the official catalogue yet.')} ${chip(x,'pending')}</p>`),
   row(x,'7.1.2',x('맥락 반영','Context'),x('변수 칸을 채워 질문에 맥락을 넣습니다. 앱에 공개 분석 자료가 있으면 ‘가져오기’로 넣습니다.','Fill the variables to give the question its context. When the app has public analysis data, “Import” fills it in.'),'partial',
    `<p>${x('선택한 공개 기업은 라이브러리의 ‘선택 기업 가져오기’로 빈 기업 입력칸에 넣습니다. 이미 입력한 값은 유지합니다.','Use “Import selected company” in the library to fill empty company fields with the selected public identity. Existing inputs are kept.')}</p><p>${x('프롬프트마다 기간의 뜻이 달라 자동으로 옮기지 않습니다. 필요한 기간은 직접 입력합니다.','Periods mean different things in different prompts, so they are not transferred automatically. Enter the period you need.')}</p>`),
   row(x,'7.1.3',x('복사와 실행 안내','Copy and run'),x('필수 변수 검사 → 미리보기 → 복사.','Required-variable check → preview → copy.'),'ready',
    `<p>${x('이 앱은 AI를 부르지 않습니다. 복사한 글을 쓰는 AI 대화창에 붙여 넣고, 답은 직접 검토합니다.','This app never calls an AI. Paste the copied text into the AI chat you use and review the answer yourself.')}</p>`),
   row(x,'7.1.4',x('내 사본','My copies'),x('즐겨찾기와 개인 수정본 · 이 브라우저 기준. 공식 원문은 바뀌지 않습니다.','Favourites and personal copies · this browser only. The official text never changes.'),'ready',
    `<p>${x('로그인 계정 동기화는','Account sync after sign-in is')} ${chip(x,'pending')}</p>`),
   row(x,'7.1.5',x('화면 연결','Screen links'),x('다른 화면에서 프롬프트가 필요한 자리.','Places on other screens that hand you a prompt.'),'partial',
    links([['#report/real',x('메뉴 5.2 · 보고 불가 → 프롬프트','Menu 5.2 · report unavailable → prompt')],['#playbook',x('플레이북 · 기록용 프롬프트','Playbook · record prompt')],['#validation',x('메뉴 n+1 · Lab','Menu n+1 · Lab')]]))];
  // Personalisation order (function 7.2, number not fixed): a fixed explanation. Layer ① waits on IA-6 / DRAW-STORE (b)(c);
  // ② and ③ already work per screen. No count or current value is read here.
  const steps=[
   ['account',x('① 로그인 계정에 저장된 값','① Values saved to your signed-in account'),`<span class="badge fn-unconnected">${x('결정 대기','Awaiting decision')}</span> ${x('로그인 방식이 정해지지 않았습니다 (IA-6 · DRAW-STORE).','The sign-in method is not decided yet (IA-6 · DRAW-STORE).')}`],
   ['device',x('② 이 브라우저에 저장된 값','② Values saved in this browser'),x('관심 기업 · 가중치 · 차트 노트 · 프롬프트 사본 등. 다른 기기와 공유되지 않습니다. 일부는 설정의 기기 백업으로 파일에 보관할 수 있습니다.','Watchlist, weights, chart notes, prompt copies and so on. They are not shared with other devices. Some can be saved to a file with the device backup in Settings.')],
   ['default',x('③ 앱 기본값','③ App defaults'),x('공식 가중치 · 공식 프롬프트 원문 · 기본 화면. 내 값이 없을 때 씁니다.','Official weights, official prompt text, default screens. Used when you have no value of your own.')]];
  const order=`<section class="plab-group" data-personal-order aria-labelledby="plab-order"><h2 class="plab-head" id="plab-order"><span class="hl">${x('개인화 · 어떤 값을 먼저 쓰나요','Personalisation · which value comes first')}</span></h2>
   <p class="plab-lede">${x('위 단계에 값이 없으면 다음 단계로 내려갑니다. 지금은 로그인이 없어 ②와 ③만 씁니다.','If a step has no value, the next step is used. There is no sign-in yet, so only ② and ③ are used now.')}</p>
   <ul class="plab-rules" data-personal-order-steps>${steps.map(([k,t,d])=>`<li data-order-step="${k}"><strong>${t}</strong> · ${d}</li>`).join('')}</ul>${links([['#settings',x('설정 · 기기 백업','Settings · device backup')]])}</section>`;
  return note(x,'도장 번호(7.1.x)는 기능 번호입니다. 위 메뉴 번호(6)와 다릅니다.','Stamp numbers (7.1.x) are function numbers, not the menu number above (6).')+
   group(x,'7.1','plab-71',x('프롬프트 탐색·사용·개인화','Find, use and personalise prompts'),'',rows)+
   `<section class="plab-frame" aria-labelledby="plab-frame-title"><h2 class="plab-frame-title" id="plab-frame-title">${['7.1.1','7.1.2','7.1.3','7.1.4'].map(n=>`<span class="plab-stamp" data-fn-ref="${n}">${n}</span>`).join('')} <span>${x('라이브러리에서 바로 쓰기','Use it in the library')}</span></h2>${frameHtml||''}</section>`+order;
 }
 // Menu n+1 · Lab = 9.1 백테스트 + 9.2 전진검증. The six S10 canon sections keep their ids and DOM order
 // (setup, equity-curve, quarterly, track-record, baseline, promotion); the forward ledger mounts into 9.2.1-9.2.3.
 // No engine is connected, so every input is disabled and no period is selected.
 function validationHtml(locale){
  const x=pick(locale),noEngine=x('검증 엔진이 연결되지 않았습니다.','No validation engine is connected.');
  const dis=(id,label,control)=>`<label for="${id}">${label}</label>${control}`;
  const select=(id,opts)=>`<select id="${id}" disabled aria-disabled="true"><option value="">NOT_AVAILABLE</option>${opts.map(o=>`<option>${o}</option>`).join('')}</select>`;
  const text=(id,ph)=>`<input id="${id}" type="text" disabled aria-disabled="true" placeholder="${ph}">`;
  const setup=`<section class="card" id="validation-experiment-setup" data-validation-section="setup"><h4>${x('실험 설정','Experiment setup')}</h4>
   <p>${na} ${noEngine} ${x('기간은 사용자가 결정하며 에이전트는 선택하지 않습니다.','The period is your decision; no period is selected for you.')}</p>
   <div class="setup-form" role="group" aria-label="${x('실험 설정','Experiment setup')}">
   ${dis('exp-profile',x('전략·프로필','Strategy · profile'),select('exp-profile',[x('균형','Balanced'),x('공격','Aggressive'),x('방어','Defensive')]))}
   ${dis('exp-period',x('기간','Period'),text('exp-period','NOT_AVAILABLE'))}
   ${dis('exp-count',x('종목 수 (1~30)','Number of stocks (1~30)'),'<input id="exp-count" type="number" min="1" max="30" disabled aria-disabled="true" placeholder="1~30">')}
   ${dis('exp-rebalance',x('리밸런싱','Rebalancing'),select('exp-rebalance',[]))}
   ${dis('exp-cost',x('거래비용·세금','Trading cost · tax'),text('exp-cost','NOT_AVAILABLE'))}
   </div></section>`;
  const equity=`<section class="card" id="validation-equity-curve" data-validation-section="equity-curve"><h4>${x('자산 곡선','Equity curve')}</h4>
   <p>${na} ${x('시작값 100. 시리즈가 없어 곡선을 그리지 않습니다.','Starts at 100. There is no series, so no curve is drawn.')}</p>
   <dl class="kv"><dt>${x('시작값','Start value')}</dt><dd class="num">100</dd><dt>${x('성과 지표','Performance metrics')}</dt><dd data-na="NOT_AVAILABLE">—</dd></dl></section>`;
  const quarterly=`<section class="card" id="validation-quarterly" data-validation-section="quarterly"><h4>${x('분기 성과','Quarterly performance')}</h4>
   <p>${na} ${noEngine}</p>
   ${table([x('분기','Quarter'),x('보유','Holdings'),x('비중','Weight'),'QGV',x('노출','Exposure'),x('분기 수익률','Quarter return'),x('S&P 500 초과','vs S&P 500')],[[dash,dash,dash,dash,dash,dash,dash]])}</section>`;
  const track=`<section class="card" id="validation-track-record" data-validation-section="track-record"><h4>Track Record</h4>
   <p><strong>${x('과거 판단은 다시 쓰지 않음','Past judgements are never rewritten')}</strong> ${na}</p>
   ${table(['D+5','D+20','D+63','D+252'],[[dash,dash,dash,dash]])}
   <dl class="kv"><dt>${x('시나리오·신뢰도 보정 곡선','Scenario · confidence calibration curve')}</dt><dd data-na="NOT_AVAILABLE">—</dd><dt>${x('QGV 버전별 성과·표본 수·코호트','Performance, sample size, cohort by QGV version')}</dt><dd data-na="NOT_AVAILABLE">—</dd></dl></section>`;
  const baseline=`<section class="card" id="validation-baseline" data-validation-section="baseline"><h4>${x('기준선 · Track A','Baseline · Track A')}</h4>
   <p>${x('Track A 미국 상위 500 · 3개 시점 동결. 동결된 기록은 바꾸지 않습니다.','Track A US top 500 · 3 frozen points. Frozen records are not changed.')}</p>
   <p class="small">Holdout: ${x('사용 금지 · UNCONFIRMED','Do not use · UNCONFIRMED')}</p></section>`;
  const promotion=`<section class="card" id="validation-promotion" data-validation-section="promotion"><h4>${x('프로필 승격 (연구 → 검증됨)','Profile promotion (research → validated)')}</h4>
   <p>${na} ${x('통과한 검증 기록이 없어 승격할 수 없습니다.','There is no passed validation record, so promotion is unavailable.')}</p>
   <button type="button" disabled aria-disabled="true">${x('검증됨으로 승격','Promote to validated')}</button></section>`;
  const conditions=[x('PIT 시점 기준 데이터만','Point-in-time data only'),x('Holdout 기간 미정 · 사용 금지 · UNCONFIRMED','Holdout period undecided · do not use · UNCONFIRMED'),x('가격은 공개 파일에 두지 않음 · 기기 RAM 전용','No prices in public files · device RAM only')];
  const backtest=[
   row(x,'9.1.1',x('연구 목적','Research question'),x('무엇을 무엇과 견주어 확인할지 먼저 적는 칸.','Where the question and its comparison are written first.'),'pending',
    `<p>${na} ${x('공개 앱에 등록된 실험이 없습니다. 실험 기록(질문·비교 대상·기간)은 연결 전입니다.','No experiment is registered in the public app. The experiment record (question, comparison, period) is not connected yet.')}</p>`),
   row(x,'9.1.2',x('실험 구성','Experiment design'),x('전략·프로필 · 기간 · 종목 수 · 리밸런싱 · 비용.','Strategy/profile · period · count · rebalancing · cost.'),'pending',setup),
   row(x,'9.1.3',x('가중치 연구','Weight research'),x('축·세부 요인 가중치를 연구 프로필로 탐색합니다. 공식 기본값은 자동으로 바뀌지 않습니다.','Axis and factor weights are explored as research profiles. Official defaults never change automatically.'),'pending',
    links([['#lab-13f',x('QGV 1.3 · 13F 가중치 연구','QGV 1.3 · 13F weight research')],['#profiles',x('QGV 1.2 · 가중치 · 사용자 설정','QGV 1.2 · weights · user settings')]])),
   row(x,'9.1.4',x('평가 기준','Evaluation criteria'),x('무엇과 비교하고 어디를 넘어야 통과인지.','What it is compared with and what counts as a pass.'),'na',
    `<dl class="kv"><dt>${x('비교 대상','Benchmark')}</dt><dd>S&amp;P 500</dd><dt>${x('기준선','Baseline')}</dt><dd>Track A · ${x('9.2.3에서 확인','see 9.2.3')}</dd><dt>${x('성과 지표 · 통과 기준','Metrics · pass rule')}</dt><dd data-na="NOT_AVAILABLE">${x('미산출','Not computed')}</dd></dl>`),
   row(x,'9.1.5',x('데이터 조건','Data conditions'),x('결과를 믿기 위해 지키는 자료 규칙.','Data rules kept so results can be trusted.'),'rule',
    `<ul class="plab-rules">${conditions.map(c=>`<li>${c}</li>`).join('')}</ul>`),
   row(x,'9.1.6',x('결과 보고','Result report'),x('자산 곡선과 분기 성과. 결과가 없으면 그리지 않습니다.','Equity curve and quarterly results. Nothing is drawn without results.'),'na',equity+quarterly)];
  const forward=[
   row(x,'9.2.1',x('관측 기록','Observation record'),x('그날의 Q·G를 가격 없이 추가만 하는 원장. 아래 상태와 기록 수가 그대로입니다.','An append-only, price-free ledger of each day’s Q·G. The status and record count below are shown as published.'),'',
    '<div id="forward-validation-root"></div>'),
   row(x,'9.2.2',x('이후 성과','Later outcome'),x('기록 이후의 결과. 가격은 누를 때만 기기 메모리에서 계산합니다.','What happened after each record. Prices are computed in device memory only when you ask.'),'',
    '<div id="forward-validation-outcome" class="plab-slot"></div>'+track),
   row(x,'9.2.3',x('평가 가능 여부','Can it be evaluated?'),x('주 평가 조건을 채운 기록인지, 기준선·Holdout·승격 상태.','Whether records meet the primary rule; baseline, holdout and promotion state.'),'',
    '<div id="forward-validation-eligibility" class="plab-slot"></div>'+baseline+promotion),
   row(x,'9.2.4',x('운영 증거','Operating evidence'),x('기록이 제때, 고쳐 쓰이지 않고 쌓였다는 증거.','Evidence that records were added on time and never rewritten.'),'pending',
    `<p>${x('원장은 추가만 하며 지난 기록을 고쳐 쓰지 않습니다. 공개 원장에는 가격이 없습니다. 실행 기록은 이 화면에 아직 연결되지 않았습니다.','The ledger is append-only and past records are never rewritten. The public ledger holds no prices. Run records are not connected to this screen yet.')}</p>`+
    links([['#settings',x('설정 · 공개 자료 운영 상태','Settings · public data operations status')]]))];
  // 9.1 readiness: what must exist before any backtest result. ✓ only where a merged document records it
  // (#286 PIT filing adapter + early-close times, research only; FSDS_SAMPLE_20261017 two quarters). Decisions stay pending.
  const ready=[
   ['pit-adapter','checked',x('과거 시점 공시 어댑터 · 조기 폐장 종가 시각 — 연구 전용, 실제 자료 검증 전','Point-in-time filing adapter · early-close times — research only, not yet checked on real data')],
   ['fsds-sample','checked',x('SEC FSDS 표본 확인 — 2015년 4분기 · 2016년 1분기 두 분기만 (접수 시각 = 뉴욕 현지)','SEC FSDS sample check — two quarters only, 2015 Q4 and 2016 Q1 (filing time = New York local)')],
   ['past-universe','pending',x('과거 모집단 — 그때의 S&P 500 편입·퇴출 이력이 아직 없습니다 (BT-2)','Past universe — no record yet of S&P 500 joins and exits at each date (BT-2)')],
   ['bt-decisions','decide',x('기간 · 비용 · 체결 규칙 등 남은 결정 (BACKTEST BT-1~17 · 매크로 근사 MD-1~12)','Remaining choices such as period, cost and execution rules (BACKTEST BT-1~17 · macro approximation MD-1~12)')],
   ['regime-frequency','decide',x('국면 전환 빈도 계산 — 매크로 3.2 순환매 · 3.3 산업 사이클 확률의 근거 (IA-3 · BACKTEST 뒤)','Regime-change frequency — the basis for macro 3.2 rotation and 3.3 industry-cycle probabilities (after IA-3 · BACKTEST)')],
   ['returns','na',x('수익률 계산 — 위 결정이 끝난 뒤에만 합니다','Return calculation — only after the decisions above')]];
  const checklist=`<details class="plab-fold" data-bt-readiness><summary>${x('준비 체크리스트 · 결과 아님','Readiness checklist · not a result')}</summary>
   <ul class="plab-rules" data-bt-checklist>${ready.map(([k,s,t])=>`<li data-bt-item="${k}" data-bt-state="${s}">${chip(x,s)} ${t}</li>`).join('')}</ul>
   <p class="plab-desc">${x('Lab에서 다른 메뉴로 · 아래 두 화면의 확률은 이 계산과 검증 전까지 미산출입니다.','From Lab to other menus · probabilities on these two screens stay not computed until this calculation and its validation exist.')}</p>
   ${links([['#macro-rotation',x('매크로 3.2 · 순환매 위치','Macro 3.2 · sector rotation')],['#macro-industry',x('매크로 3.3 · 산업 사이클','Macro 3.3 · industry cycles')]])}</details>`;
  return note(x,'도장 번호(9.x)는 기능 번호입니다. 위 메뉴 번호(n+1)와 다릅니다.','Stamp numbers (9.x) are function numbers, not the menu numbers above (n+1).')+
   group(x,'9.1','plab-91',x('백테스트','Backtest'),x('공개 앱에 연결된 백테스트 결과가 없습니다. 아래 칸은 결과가 생기면 채울 자리입니다.','No backtest result is connected to the public app. The boxes below are where results will go.'),backtest,checklist)+
   group(x,'9.2','plab-92',x('전진검증','Forward validation'),x('결과를 미리 알 수 없는 날부터 쌓는 기록입니다. 기록이 없으면 없다고 적습니다.','Records kept from days whose outcome was not yet known. When there is no record, it says so.'),forward);
 }
 return Object.freeze({macroHtml,validationHtml,promptsHtml});
});
