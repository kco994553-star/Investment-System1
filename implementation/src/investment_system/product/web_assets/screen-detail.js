/* S09 macro and S10 validation canon sections. Static markup only: every value is NOT_AVAILABLE with a reason.
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
  const wait=x('입력·대응표가 사용자 결정 대기 중이며 FRED/ALFRED는 사용하지 않습니다.','Inputs and mapping await your decision; FRED/ALFRED are not used.');
  return `<section class="card" id="macro-equity-state" data-macro-section="equity-state"><h2>${x('주식시장 상태 (참고 · 원인 축 아님)','Equity market state (reference · not a causal axis)')}</h2>
   <p>${na} ${x('변동성·상승 종목 폭·추세에 쓸 입력이 연결되지 않았습니다.','No inputs are connected for volatility, breadth or trend.')}</p>
   <dl class="kv"><dt>${x('변동성','Volatility')}</dt><dd data-na="NOT_AVAILABLE">—</dd><dt>${x('상승 종목 폭','Breadth')}</dt><dd data-na="NOT_AVAILABLE">—</dd><dt>${x('추세','Trend')}</dt><dd data-na="NOT_AVAILABLE">—</dd></dl></section>
  <section class="card" id="macro-regime-history" data-macro-section="regime-history"><h2>${x('국면 이력 (5년)','Regime history (5 years)')}</h2>
   <p>${na} ${x('금리·물가·유동성·성장 겹쳐 보기에 쓸 국면 기록이 없습니다. 합성 이력을 만들지 않습니다.','No regime record exists to overlay rates, inflation, liquidity and growth. No synthetic history is made.')}</p></section>
  <section class="card" id="macro-signal-evidence" data-macro-section="signal-evidence"><h2>${x('신호 → 근거','Signal → evidence')}</h2>
   <p>${na} ${wait}</p>
   ${table([x('신호','Signal'),x('강도','Strength'),x('지표','Indicator'),x('값','Value'),x('발표일','Release date'),x('이용 가능 시점','Available at')],[[dash,dash,dash,dash,dash,dash]])}</section>
  <section class="card" id="macro-scenarios" data-macro-section="scenarios"><h2>${x('시나리오 (확률 검증 전)','Scenarios (before probability validation)')}</h2>
   <p>${na} ${x('시나리오 3개와 확률은 검증이 끝난 뒤에만 표시합니다. 숫자 확률을 임의로 채우지 않습니다.','Three scenarios and their probabilities appear only after validation. No numeric probability is filled in.')}</p>
   ${table([x('시나리오','Scenario'),x('확률','Probability')],[['S1',dash],['S2',dash],['S3',dash]])}</section>
  <section class="card" id="macro-transmission" data-macro-section="transmission"><h2>${x('영향 전달','Impact transmission')}</h2>
   <p>${na} ${x('요인 → 경제 경로 → 업종 → 기업 → Q·G·V 맥락(유리·중립·불리) 연결은 매크로 8축 대응표가 확정되기 전에는 만들지 않습니다.','The chain factor → economic path → industry → company → Q·G·V context (favorable / neutral / unfavorable) is not built before the 8-axis mapping is confirmed.')}</p>
   <ol class="chain" data-transmission-chain>${[['요인','Factor'],['경제 경로','Economic path'],['업종','Industry'],['기업','Company'],['Q·G·V 맥락','Q·G·V context']].map(([k,e])=>`<li>${x(k,e)} ${dash}</li>`).join('')}</ol></section>`;
 }
 // S10: canon blocks under the existing tabs. No engine is connected, so every input is disabled and no period is selected.
 function validationHtml(locale){
  const x=pick(locale),noEngine=x('검증 엔진이 연결되지 않았습니다.','No validation engine is connected.');
  const dis=(id,label,control)=>`<label for="${id}">${label}</label>${control}`;
  const select=(id,opts)=>`<select id="${id}" disabled aria-disabled="true"><option value="">NOT_AVAILABLE</option>${opts.map(o=>`<option>${o}</option>`).join('')}</select>`;
  const text=(id,ph)=>`<input id="${id}" type="text" disabled aria-disabled="true" placeholder="${ph}">`;
  return `<section class="card" id="validation-experiment-setup" data-validation-section="setup"><h2>${x('실험 설정','Experiment setup')}</h2>
   <p>${na} ${noEngine} ${x('기간은 사용자가 결정하며 에이전트는 선택하지 않습니다.','The period is your decision; no period is selected for you.')}</p>
   <div class="setup-form" role="group" aria-label="${x('실험 설정','Experiment setup')}">
   ${dis('exp-profile',x('전략·프로필','Strategy · profile'),select('exp-profile',[x('균형','Balanced'),x('공격','Aggressive'),x('방어','Defensive')]))}
   ${dis('exp-period',x('기간','Period'),text('exp-period','NOT_AVAILABLE'))}
   ${dis('exp-count',x('종목 수 (1~30)','Number of stocks (1~30)'),'<input id="exp-count" type="number" min="1" max="30" disabled aria-disabled="true" placeholder="1~30">')}
   ${dis('exp-rebalance',x('리밸런싱','Rebalancing'),select('exp-rebalance',[]))}
   ${dis('exp-cost',x('거래비용·세금','Trading cost · tax'),text('exp-cost','NOT_AVAILABLE'))}
   </div></section>
  <section class="card" id="validation-equity-curve" data-validation-section="equity-curve"><h2>${x('자산 곡선','Equity curve')}</h2>
   <p>${na} ${x('시작값 100. 시리즈가 없어 곡선을 그리지 않습니다.','Starts at 100. There is no series, so no curve is drawn.')}</p>
   <dl class="kv"><dt>${x('시작값','Start value')}</dt><dd class="num">100</dd><dt>${x('성과 지표','Performance metrics')}</dt><dd data-na="NOT_AVAILABLE">—</dd></dl></section>
  <section class="card" id="validation-quarterly" data-validation-section="quarterly"><h2>${x('분기 성과','Quarterly performance')}</h2>
   <p>${na} ${noEngine}</p>
   ${table([x('분기','Quarter'),x('보유','Holdings'),x('비중','Weight'),'QGV',x('노출','Exposure'),x('분기 수익률','Quarter return'),x('S&P 500 초과','vs S&P 500')],[[dash,dash,dash,dash,dash,dash,dash]])}</section>
  <section class="card" id="validation-track-record" data-validation-section="track-record"><h2>Track Record</h2>
   <p><strong>${x('과거 판단은 다시 쓰지 않음','Past judgements are never rewritten')}</strong> ${na}</p>
   ${table(['D+5','D+20','D+63','D+252'],[[dash,dash,dash,dash]])}
   <dl class="kv"><dt>${x('시나리오·신뢰도 보정 곡선','Scenario · confidence calibration curve')}</dt><dd data-na="NOT_AVAILABLE">—</dd><dt>${x('QGV 버전별 성과·표본 수·코호트','Performance, sample size, cohort by QGV version')}</dt><dd data-na="NOT_AVAILABLE">—</dd></dl></section>
  <section class="card" id="validation-baseline" data-validation-section="baseline"><h2>${x('기준선 · Track A','Baseline · Track A')}</h2>
   <p>${x('Track A 미국 상위 500 · 3개 시점 동결. 동결된 기록은 바꾸지 않습니다.','Track A US top 500 · 3 frozen points. Frozen records are not changed.')}</p>
   <p class="small">Holdout: ${x('사용 금지 · UNCONFIRMED','Do not use · UNCONFIRMED')}</p></section>
  <section class="card" id="validation-promotion" data-validation-section="promotion"><h2>${x('프로필 승격 (연구 → 검증됨)','Profile promotion (research → validated)')}</h2>
   <p>${na} ${x('통과한 검증 기록이 없어 승격할 수 없습니다.','There is no passed validation record, so promotion is unavailable.')}</p>
   <button type="button" disabled aria-disabled="true">${x('검증됨으로 승격','Promote to validated')}</button></section>`;
 }
 return Object.freeze({macroHtml,validationHtml});
});
