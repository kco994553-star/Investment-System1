/* TARGET v1 builder screen (owner decision 2026-10-14), mounted under the playbook TARGET v1 section (PlaybookScreen.mount).
   Device only: the v2 scores (V needs this device's prices) and the price series for the set comparison stay in RAM; the
   device stores only the draft ranking, the user's card answers, the confirmed TARGET v1 versions, the R-B / R-C rule-index
   definitions (규칙 지수; 2026-10-15 T-SET, never the sheet ledger's user sets B/C/D) and the symbols the user added for TV1 scoring
   inside the playbook store (target_v1, part of the existing device backup), plus one judgement record per card answer.
   T-PRICE (2026-10-15): a TV1 name outside the 19 has no runner series, so after the user's click and a confirm dialog its daily
   closes are appended to the user's own private sheet (PriceStore, Prices_D) and read back into RAM for scoring; a missing close
   stays NA. 2026-10-15 supplement: the 확정 button re-reads the published sec-qgv2.json at that moment and shows every blocker
   (calc_version, freshness, Q·G coverage, the number check of the same calc_version, name shortfall); until TARGET v1 is
   finalized a rebalance round shows the risk-code checks only. 2026-10-15 evening: freshness by row acquisition time (7 days);
   the draft records the input basis of the published file and a changed basis at finalize regenerates the draft. Nothing here publishes, logs or sends prices, holdings or
   amounts. No order function and no buy/sell wording.
   PR-D (owner decision D8 (b), GSQ-024; spec 2.1.7, 6.1.2~6.1.4): the Build and Finalize clicks also read the central V publication
   qgv-official.json through QgvOfficial (next to the sec-qgv2.json re-read; never at mount). It is used only when it is valid,
   verified, of the re-read file's calc_version and at most 2 New York sessions old; otherwise the device path ("임시 V") with one
   line saying why. Labels follow the draft's V source; official V is shown with the publication's IEX attribution and basis day. */
(function(root,factory){const node=typeof module==='object'&&module.exports;
 const api=factory(root,node?require('./target-v1-builder.js'):root.TargetV1Builder,node?require('./target-v1-config-defaults.js'):root.TargetV1ConfigDefaults,node?require('./playbook-config-defaults.js'):root.PlaybookConfigDefaults,
  node?()=>require('./qgv-official.js'):()=>root.QgvOfficial);
 if(node)module.exports=api;else root.TargetV1Screen=api;})(typeof globalThis==='object'?globalThis:this,function(g,B,DEFAULT_CFG,PCFG,officialReader){
'use strict';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite=v=>typeof v==='number'&&Number.isFinite(v),n1=v=>finite(v)?v.toFixed(1):'NA',pctText=v=>finite(v)?v.toFixed(2).replace(/\.?0+$/,'')+'%':'NA';
const pp=v=>finite(v)?(v>0?'+':v<0?'−':'')+Math.abs(v).toFixed(2)+'%p':'NA',ret=v=>finite(v)?(v>0?'+':v<0?'−':'')+Math.abs(v*100).toFixed(2)+'%':'NA';
const GRADE={CORE:'핵심',GENERAL:'일반',EQUAL:'균등'},SAFETY={PASS:'통과',FAIL:'불통과',UNKNOWN:'확인 불가'};
const EXCLUDE={TOTAL_NOT_AVAILABLE:'총점 없음',AXIS_COVERAGE_LOW:'축 산출 50% 미만',VALUE_TRAP_GATE:'가치 함정 관문',FINANCIAL_SAFETY_FAIL:'재무 안전 불통과',FINANCIAL_SAFETY_NOT_AVAILABLE:'재무 안전 자료 없음(NA)',SUBGROUP_MAX:'업종 하위 묶음 4개 상한',SECTOR_GROUP_MAX:'업종 묶음 40% 상한',SINGLE_MAX:'단일 10% 상한',USER_DISAGREE:'사용자 반대',IDENTITY_CONFLICT_WITHDRAWN:'신원 충돌로 사용 중지'};
// Finalize blockers (finalizeBlockers / finalize error .blockers) as one line each.
const BLOCKERS={TARGET_V1_CARDS_PENDING:'카드 응답 대기',TARGET_V1_SHORTFALL:'통과 종목 부족(조건 완화 없음)',TARGET_LIMITS_BLOCKED:'16절 한도 위반',V_FACTORS_V3_V4_MISSING:'V3(업종 대비)·V4(자기 과거 대비)가 빠진 V로 계산된 선정 종목이 있어 확정할 수 없음(초안은 가능 · 2026-10-23 결정)',SEC_QGV2_NOT_AVAILABLE:'최신 공개 sec-qgv2.json을 읽지 못함',
 V_SOURCE_CHANGED:'초안 이후 V 출처(공식 V ↔ 임시 V, 또는 중앙 V 게시본)가 바뀜 · 초안 재생성 필요',CALC_VERSION_MISSING:'calc_version 없음(이전 형식 파일)',CALC_VERSION_MIXED:'행마다 calc_version이 다르거나 NA 사유 없는 빈 행이 있음',ROW_DATA_STALE:'값이 있는 행의 SEC 수집 시각이 7일을 넘음(파일 as_of는 신선도로 보지 않음)',DRAFT_BASIS_CHANGED:'초안 이후 입력 기준(calc_version·유형 적용 범위·신원 충돌 사용 중지·샤드별 수집 시각)이 바뀜 · 초안 재생성 필요',FINANCIAL_SAFETY_RECHECK_FAILED:'선정 종목 재무 안전 재검사(최신 자료) 불통과',
 Q_COVERAGE_LOW:'Q 산출 종목 90% 미만',G_COVERAGE_LOW:'G 산출 종목 90% 미만',NUMBER_CHECK_NOT_PASSED:'숫자 검증(10개 기업) 미통과',NUMBER_CHECK_CALC_VERSION_MISMATCH:'숫자 검증 calc_version이 현재 파일과 다름',DATE_INVALID:'날짜 오류',TARGET_V1_DRAFT_REQUIRED:'초안 없음'};
const ERRORS={NUMBER_CHECK_NOT_PASSED:null,TARGET_V1_SHORTFALL:'통과 종목이 15개에 못 미쳐 확정할 수 없습니다(조건을 완화하지 않음).',TARGET_V1_CARDS_PENDING:'모든 카드에 응답해야 확정할 수 있습니다.',TARGET_LIMITS_BLOCKED:'16절 한도를 넘어 확정할 수 없습니다.',DISAGREE_REASON_REQUIRED:'반대 이유를 한 줄로 적어 주세요.',
 QGV2_NOT_READY:'QGV v2 점수가 이 기기에서 아직 계산되지 않았습니다.',OFFICIAL_INVALID:'중앙 V 게시본을 쓸 수 없습니다.',V_SOURCE_MIXED:'공식 V 초안은 게시본 점수로만 만듭니다.',TARGET_V1_DRAFT_REQUIRED:'먼저 초안을 만드세요.',REASON_INVALID:'이유는 줄바꿈 없이 200자 이내로 적어 주세요.',TARGET_V1_NOT_SELECTED:'현재 선정에 없는 종목입니다.'};
/* V factor count (user decision 2026-10-23, TargetV1Builder.vFactors): 'n/5' per candidate and a marker when V lacks V3 (업종 대비)
   or V4 (자기 과거 대비); such a name can stay in a draft but blocks finalize (V_FACTORS_V3_V4_MISSING). A draft row built before the
   count has no v_missing → 'NA' and the marker (V3·V4 not confirmed). */
const V_SHORT={v_vs_industry:'V3',v_vs_own_history:'V4'};
function vText(r){if(!Array.isArray(r.v_missing))return 'NA';return r.v_n+'/'+r.v_total;}
function vMarker(r){if(!B.vIncomplete(r))return '';const miss=Array.isArray(r.v_missing)?B.V_REQUIRED.filter(k=>r.v_missing.includes(k)).map(k=>V_SHORT[k]).join('·')+' 빠짐':'V3·V4 확인 불가(이전 초안)';
 return ' <span class="badge partial" data-tv1-v-marker>'+esc(miss+' · 확정 불가')+'</span>';}
function vAttrs(r){return ' data-tv1-v-count="'+esc(Array.isArray(r.v_missing)?r.v_n:'NA')+'"'+(B.vIncomplete(r)?' data-tv1-v-incomplete':'');}
function vReasonHtml(rows,attr){const bad=rows.filter(B.vIncomplete);if(!bad.length)return '';
 return '<p '+attr+'>V3(업종 대비)·V4(자기 과거 대비)가 빠진 V · '+esc(bad.map(r=>r.symbol+' V '+vText(r)).join(' · '))+' · 초안은 그대로 쓸 수 있지만 이 종목이 선정에 있으면 TARGET v1을 확정할 수 없습니다(2026-10-23 결정)</p>';}
const today=()=>new Date().toISOString().slice(0,10),key=t=>String(t||'').replaceAll('.','-').toUpperCase();
/* ---------- V source (PR-D, D8 (b)) ---------- */
// QgvOfficial when the page loads it (lazy); absent → no central V step at all, the screen is the device path as before.
function reader(){try{const R=officialReader();return R&&typeof R.resolve==='function'?R:null;}catch(_){return null;}}
// Why the central V was not used (QgvOfficial.REASONS, M4), one short line.
const OFFICIAL_REASON={OFFICIAL_NOT_PUBLISHED:'중앙 V 게시본 없음(404)',OFFICIAL_UNAVAILABLE:'중앙 V 게시본을 읽지 못함',OFFICIAL_INVALID:'중앙 V 게시본 검증 실패',
 OFFICIAL_CALC_VERSION_DIFFERS:'게시본 calc_version이 최신 sec-qgv2.json과 다름',OFFICIAL_STALE:'게시본 가격 기준일이 뉴욕 거래일 2일보다 오래됨(또는 미래 날짜)'};
function reasonLine(code,fallback){return '공식 V 사용 안 함 · '+code+' · '+(OFFICIAL_REASON[code]||code)+(fallback?' → 임시 V':'');}
const sourceOf=d=>B.V_SOURCES?.[d?.v_source]||B.V_SOURCE;
/* GSQ-024: official V is shown with the IEX attribution sentence, its terms link and the basis wording, from the publication read at
   the click; after a reload (no publication in memory) from the reader's constants, which every accepted publication equals. */
function attributionHtml(draft,pub){
 if(draft?.v_source!=='OFFICIAL_CENTRAL')return '';const id=draft.official?.publication_id,a=pub&&pub.publication_id===id?pub.attribution:reader()?.ATTRIBUTION;if(!a)return '';
 return '<p class="small" data-tv1-attribution><span data-tv1-attribution-label>'+esc(a.label_ko)+'</span> · 가격 기준일 '+esc(draft.official?.price_basis_date||'NA')+' · <span data-tv1-attribution-text>'+esc(a.text)+'</span>'
  +(/^https:\/\//.test(a.terms_url)?' <a data-tv1-terms href="'+esc(a.terms_url)+'" target="_blank" rel="noopener noreferrer">이용 약관</a>':'')+'</p>';}
function officialText(draft){const o=draft?.official;return o?' · 가격 기준일 '+o.price_basis_date+' · 게시본 '+String(o.publication_id).slice(0,19):'';}
function typeNames(types){const list=g.TypeConfigDefaults?.types||[];return types.length?types.map(id=>list.find(t=>t.id===id)?.name||id).join('·'):'미분류';}
function subgroupName(id){if(!id)return '확인 불가';const row=PCFG.sector_checks.find(s=>s.id===id);if(row)return row.name;const combined=PCFG.portfolio_limits.combined_groups.find(x=>x.id===id);if(combined)return combined.ko;if(id==='technology_hardware')return '기술 하드웨어';if(id==='general_industrial')return '일반 산업';return id.startsWith('industry:')?'업종군 '+id.slice(9):id;}
function money(v){const R=g.DailyReport;if(!finite(v))return 'NA';if(R?.money){let hidden=true;try{hidden=R.hiddenSetting(g.localStorage);}catch(_){hidden=true;}return R.money(v,{hidden});}return '●●●만원';}

/* ---------- storage (inside the playbook store) ---------- */
function readState(P,storage){const v=P.read(storage);return v.target_v1?B.validateState(JSON.parse(JSON.stringify(v.target_v1))):B.emptyState();}
function writeState(P,storage,state){const v=P.read(storage);v.target_v1=B.validateState(state);P.write(storage,v);}

/* ---------- inputs ---------- */
function existingSymbols(catalog){return [...new Set([...PCFG.assignments.map(a=>a.symbol),...(catalog?.instruments||[]).map(i=>i.ticker)])];}
function v0Weights(catalog){const out={};for(const i of catalog?.instruments||[])if(Number.isInteger(i.target_units))out[i.ticker]=i.target_units/catalog.total_units*100;return out;}
// TARGET v0 tickers → price symbols (TEL / 한미반도체 trade in Tokyo / Seoul; local price return basis).
function priceSymbol(ticker){const T=g.VirtualTradingRunner?.TARGETS;if(T)for(const s of Object.values(T))if(s.split('.')[0]===ticker)return s;return key(ticker);}
async function defaultCloses(symbols,from){const S=g.PriceStore,out={};if(!S||typeof S.dailyCloses!=='function')return out;for(const s of symbols){try{const c=await S.dailyCloses(priceSymbol(s),from,{fetch:true});if(c&&typeof c==='object'&&Object.keys(c).length)out[s]=c;}catch(_){}}return out;}

/* ---------- html ---------- */
function candidateTable(draft,cfg,pub){const rows=B.candidates(draft,cfg),src=sourceOf(draft);return '<section class="card" data-tv1-candidates><h2>후보 '+rows.length+' · QGV v2 총점순 · 업종 하위 묶음당 최대 '+cfg.sector_spread.max_per_subgroup+'</h2><p class="small">'+esc(draft.coverage.label||'커버리지 조건 충족')+' · 초안 '+esc(draft.created)+' · V 출처: '+esc(src.ko+' ('+src.note+')'+officialText(draft))+' · 제외: 축 산출 50% 미만·가치 함정 관문·재무 안전 불통과·재무 안전 자료 없음(NA)</p>'+attributionHtml(draft,pub)+'<div class="table-wrap"><table><thead><tr><th>티커</th><th>업종</th><th>유형</th><th>Q</th><th>G</th><th>V('+esc(src.ko)+')</th><th>V 요인</th><th>총점</th><th>업종 내 순위</th><th>산출 요인</th><th>기존 19</th></tr></thead><tbody>'+rows.map(r=>'<tr data-tv1-candidate="'+esc(r.symbol)+'"'+vAttrs(r)+'><td>'+esc(r.symbol)+'</td><td>'+esc(subgroupName(r.subgroup))+'</td><td>'+esc(typeNames(r.types||[]))+'</td><td>'+n1(r.q)+'</td><td>'+n1(r.g)+'</td><td>'+n1(r.v)+'</td><td data-tv1-v-cell>'+esc(vText(r))+vMarker(r)+'</td><td>'+n1(r.total)+'</td><td>'+esc(r.industry_rank&&r.industry_size?r.industry_rank+'/'+r.industry_size:'NA')+'</td><td>'+esc(r.factors_n+'/'+r.factors_total)+'</td><td>'+(r.in19?'예':'아니오')+'</td></tr>').join('')+'</tbody></table></div>'+vReasonHtml(rows,'data-tv1-v-reason')+'</section>';}
function limitsText(l){if(!l)return 'NA';if(l.ok===true)return '16절 한도 통과(단일 10% · 업종 묶음 40% · 최소 10종목 · 합계 100%)';return '16절 한도 '+(l.ok===false?'위반':'확인 불가')+' · '+l.violations.map(v=>v.rule+' '+(v.symbol||v.group||'')+' '+(v.pct??v.count??'')).join(' / ');}
function selectionHtml(sel,cfg){const groups=sel.limits?.group_pct||{};return '<section class="card" data-tv1-selection><h2>최종 '+sel.rows.length+' · 핵심 '+sel.core_count+'×'+cfg.selection.core.pct+'% + 일반 '+(sel.rows.length-sel.core_count)+'×'+cfg.selection.general.pct+'%</h2><p data-tv1-limits>'+esc(limitsText(sel.limits))+(sel.cash_pct>0?' · 현금 '+pctText(sel.cash_pct)+'(핵심 조건 미달 또는 후보 부족)':'')+'</p><p class="small">핵심 = 총점 상위 중 산출 요인 '+Math.round(cfg.selection.core.min_factor_ratio*100)+'% 이상·재무 안전 통과 '+cfg.selection.core.count+'개 · 업종 묶음 비중 '+esc(Object.entries(groups).map(([k,v])=>subgroupName(k)+' '+pctText(v)).join(' · ')||'NA')+'</p>'+(sel.rejected.length?'<p data-tv1-rejected>반대로 제외 · '+esc(sel.rejected.join(' · '))+' → 다음 순위로 자동 교체</p>':'')+(sel.shortfall>0?'<p data-tv1-shortfall>통과 종목 부족 '+sel.shortfall+'종목 · 조건 완화·제외 종목 복귀 없음 · 확정 불가 · 사유: '+esc(Object.entries(sel.shortfall_reasons).map(([k,v])=>(EXCLUDE[k]||k)+' '+v).join(' · ')||'후보 부족')+'</p>':'')+vReasonHtml(sel.rows,'data-tv1-v-reason-selected')+'<ol class="small">'+sel.rows.map(r=>'<li>'+esc(r.symbol+' · '+GRADE[r.grade]+' '+pctText(r.pct)+' · '+subgroupName(r.subgroup)+' · V '+vText(r))+vMarker(r)+'</li>').join('')+'</ol></section>';}
function cardHtml(r,answer,cfg,src=B.V_SOURCE){const label=answer?cfg.cards.answers.find(a=>a.id===answer.answer)?.ko+(answer.answer==='UNKNOWN'?' · 미확인':'')+' · '+answer.date:'응답 대기';
 return '<article class="card" data-tv1-card="'+esc(r.symbol)+'"><h3>'+esc(r.symbol+' · '+GRADE[r.grade]+' '+pctText(r.pct))+'</h3><p class="small">'+esc(subgroupName(r.subgroup)+' · '+typeNames(r.types||[])+' · QGV v2 '+n1(r.total)+' (Q '+n1(r.q)+' · G '+n1(r.g)+' · '+src.ko+' '+n1(r.v)+') · V 요인 '+vText(r)+' · 산출 요인 '+r.factors_n+'/'+r.factors_total+' · 재무 안전 '+SAFETY[r.safety]+(r.in19?' · 기존 19종목':''))+vMarker(r)+'</p><h4>산 이유</h4><ol>'+r.reasons.map(t=>'<li>'+esc(t)+'</li>').join('')+'</ol><h4>무효화 조건</h4><ol>'+r.invalidations.map(c=>'<li>'+esc(c.text)+'</li>').join('')+'</ol><div class="chips">'+cfg.cards.answers.map(a=>'<button type="button" data-tv1-answer="'+a.id+'" aria-pressed="'+(answer?.answer===a.id)+'">'+esc(a.ko)+'</button>').join('')+'</div><label>반대 이유(한 줄 · 반대일 때 필수)<input data-tv1-reason maxlength="200" value=""></label><p data-tv1-card-state>'+esc(label)+'</p></article>';}
function rebalanceHtml(state,catalog,ram,cfg,date,round){
 const version=B.latestVersion(state),first=B.firstVersion(state),v1={},list=B.rounds(cfg),current=round||((list.find(r=>r.date>=date)||list[list.length-1]).round),info=list.find(r=>r.round===current);
 const chips='<div class="chips">'+list.map(r=>'<button type="button" data-tv1-round="'+r.round+'" aria-pressed="'+(r.round===current)+'">'+r.round+'회차 '+esc(r.month)+'</button>').join('')+'</div>';
 // 2026-10-15 supplement: no per-round list or amount unless TARGET v1 was finalized on or before this round day.
 if(B.roundMode(state,info,cfg)!=='LIST')return '<section class="card" data-tv1-rebalance><h2>리밸런싱 주간 보기 · '+current+'회차 '+esc(info.date)+' 주</h2>'+chips+'<p data-tv1-risk-only>'+esc(first?'TARGET '+first.version+'은 '+first.date+'에 처음 확정되어 이 회차('+info.date+')에는 종목별 목록이 없습니다 · 위험 코드 점검만':'TARGET v1 미확정 · 회차별 종목 목록·예상 금액 없음 · 이번 회차는 위험 코드 점검만')+'</p><ul class="small" data-tv1-risk-codes>'+B.riskCodes(cfg,PCFG).map(c=>'<li>'+esc(c.code+' · '+c.text)+'</li>').join('')+'</ul><p class="small">보유 종목별 점검은 위 플레이북 기기 기록에서 합니다. 실제 거래 목록은 만들지 않습니다.</p></section>';
 for(const r of version.rows)v1[r.symbol]=r.pct;
 const actual=ram?.state==='AVAILABLE'?Object.fromEntries((ram.rows||[]).filter(r=>finite(r.weight)).map(r=>[r.ticker,r.weight*100])):null;
 const rows=B.transitionRows({v0:v0Weights(catalog),v1,actual,total:finite(ram?.total)?ram.total:null,round:current,cfg});
 return '<section class="card" data-tv1-rebalance><h2>리밸런싱 주간 보기 · '+current+'회차 '+esc(info.date)+' 주</h2><p>TARGET '+esc(version.version)+' · '+esc(version.date)+' 확정 · calc_version '+esc(version.calc_version||'NA')+'</p>'+chips+'<p class="small">v0 → v1 차이를 3회에 1/3씩 · 이번 회차 %p = (최종 목표 − v0) × 1/3 · 예상 금액 = %p × 현재 평가액(이 기기 RAM, 숨김 설정 따름) · 실제 거래는 사용자가 직접 합니다 · 주문 기능 없음</p><div class="table-wrap"><table><thead><tr><th>종목</th><th>현재 비중</th><th>최종 목표</th><th>이번 회차 %p</th><th>회차 후 목표</th><th>예상 금액</th></tr></thead><tbody>'+rows.map(r=>'<tr data-tv1-rebalance-row="'+esc(r.symbol)+'"><td>'+esc(r.symbol)+'</td><td>'+pctText(r.current_pct)+'</td><td>'+pctText(r.final_pct)+'</td><td>'+pp(r.step_pp)+'</td><td>'+pctText(r.round_target_pct)+'</td><td>'+esc(money(r.amount===null?null:Math.abs(r.amount)))+'</td></tr>').join('')+'</tbody></table></div></section>';}
// R-B / R-C always carry their source (규칙 지수) next to the name.
function ruleLabel(cfg,id){const r=cfg.virtual_sets[id];return r.ko+' ('+r.source_ko+')';}
function compareTable(cmp,cfg){const label={A:cfg.virtual_sets.A.ko,'R-B':ruleLabel(cfg,'R-B'),'R-C':ruleLabel(cfg,'R-C'),SP500:cfg.virtual_sets.benchmark.ko};return '<div class="table-wrap"><table data-tv1-compare><thead><tr><th>세트</th><th>수익률</th><th>기준일</th><th>상태</th></tr></thead><tbody>'+B.COMPARE_KEYS.map(k=>{const x=cmp?.[k];return '<tr data-tv1-compare-row="'+k+'"><td>'+esc(label[k])+'</td><td>'+ret(x?.return)+'</td><td>'+esc(x?.base_date||cmp?.window_start||'NA')+'</td><td>'+esc(x?.state==='OK'?'~ '+x.date:'NA · '+(x?.reason||'가격 불러오기 전'))+'</td></tr>';}).join('')+'</tbody></table></div>';}
function transitionHtml(state,cfg,date,cmp,review){
 const list=B.rounds(cfg),c=state.rule_c;
 return '<section class="card" data-tv1-transition><h2>실제 포트폴리오 전환 계획 · 3회</h2><p class="small">TARGET v0 → v1 차이를 '+list.map(r=>r.month).join(' · ')+' 리밸런싱에 1/3씩 · 각 회차 전에 세트 A·R-B·R-C(규칙 지수)와 S&P 500 성과를 나란히 확인 · '+esc(cfg.virtual_sets.return_basis_ko)+' · 실제 거래는 사용자가 직접 합니다</p><div class="table-wrap"><table><thead><tr><th>회차</th><th>리밸런싱 주</th><th>상태</th><th>이동</th></tr></thead><tbody>'+list.map(r=>'<tr data-tv1-round-row="'+r.round+'"><td>'+r.round+'</td><td>'+esc(r.date)+'</td><td>'+(date>=r.date?'지남':'예정')+'</td><td>'+(B.roundMode(state,r,cfg)==='LIST'?'v0→v1 차이의 1/3':'위험 코드 점검만')+'</td></tr>').join('')+'</tbody></table></div>'+scheduleHtml(state,cfg,date)+'<h3>회차 전 성과 비교 · 기준 '+esc(cmp?.window_start||c?.start||'R-C 시작 전')+' ~ '+esc(cmp?.as_of||date)+'</h3>'+compareTable(cmp,cfg)+'<button type="button" data-tv1-load-compare '+(c?'':'disabled')+'>성과 불러오기(이 기기 가격)</button>'+'<p data-tv1-review class="small">'+esc(reviewText(review,cfg))+'</p><p class="small">비교 탭(일일보고서 → 비교)의 세트 A는 가상매매 엔진 장부이고, 여기의 A·R-B·R-C는 같은 규칙 지수(기준일 100)로 계산합니다. '+esc(cfg.rebalance.day_rule_ko+' · '+cfg.rebalance.holiday_rule_ko)+'</p></section>';}
function scheduleHtml(state,cfg,date){const s=B.scheduleState(state,date,cfg);
 return '<p class="small" data-tv1-schedule>TARGET v1 확정 목표 '+esc(cfg.schedule.finalize_target_ko)+' · '+esc(s.finalized?'확정 '+s.finalized_on+(s.late?' (목표 이후 확정 · 그 전 회차는 위험 코드 점검만)':''):s.postponed?'목표 주까지 조건 미충족 · 확정 연기 · 11월 회차는 위험 코드 점검만':'미확정 · 조건을 못 맞추면 확정을 미루고 11월 회차는 위험 코드 점검만')+'</p>';}
function reviewText(r,cfg){if(!r)return '3회차 보류 제안 규칙 · 성과를 불러오면 판정';if(r.state==='NOT_DUE')return '3회차 보류 제안 규칙 · '+(r.from||'')+'부터 '+(r.until||'')+' 전까지 판정(지금은 대상 기간 아님)';if(r.state==='NOT_AVAILABLE')return '3회차 보류 제안 규칙 · 판정 불가 · 수익률 NA';return r.suggest?'제안 · '+r.text:'3회차 보류 제안 없음 · R-B 또는 R-C가 A·S&P 500 중 하나 이상보다 높거나 같음';}
function setsHtml(state,cfg,date){const b=state.rule_b,last=b.length?b[b.length-1]:null,c=state.rule_c;
 return '<section class="card" data-tv1-sets><h2>가상 세트 A · R-B · R-C(규칙 지수) · 소급 없음</h2><ul><li>'+esc(cfg.virtual_sets.A.ko)+' · 변경 없음(가상매매 엔진 장부)</li><li data-tv1-rule-b>'+esc(ruleLabel(cfg,'R-B'))+' · '+(last?'시작 '+esc(b[0].date)+' · 최근 선정 '+esc(last.date)+' · 다음 재선정 '+esc(B.nextRebalanceOnOrAfter(date>last.date?date:last.date,cfg)||'NA')+' · '+esc(last.rows.map(r=>r.symbol).join(' · ')):'v2 점수가 준비된 날 자동 시작')+'</li><li data-tv1-rule-c>'+esc(ruleLabel(cfg,'R-C'))+' · '+(c?'시작 '+esc(c.start)+' · '+esc(c.version):'TARGET v1 확정 후 그날부터 시작')+'</li></ul><p class="small">R-B는 리밸런싱일(2·5·8·11월 셋째 주 월요일, 휴장이면 지수 계산은 다음 거래일)마다 사람 판단 없이 다시 고릅니다. '+esc(cfg.virtual_sets.naming_note_ko)+'</p></section>';}
/* ---------- T-PRICE: TV1 scoring prices through the user's own sheet ---------- */
// SIC per ticker from the public sec-qgv2.json records (TARGET:<id> rows skipped).
function sicLookup(inputs){const map=new Map();for(const[code,r]of Object.entries(inputs?.records||{})){if(code.startsWith('TARGET:'))continue;map.set(key(code.slice(code.indexOf(':')+1)),r?.sic??null);}return s=>map.get(key(s))??null;}
// TV1 names outside the 19: pending (no price path yet) and tracked (added to Prices_D by the user).
function scoringNames(P,storage,catalog,inputs,state,cfg){let records=[];try{records=P.read(storage).records;}catch(_){records=[];}
 const all=B.scoringNeeds(records,{have:(catalog?.instruments||[]).map(i=>i.ticker),sicOf:sicLookup(inputs),cfg}),added=new Set(state.price_symbols);
 return{pending:all.filter(n=>!added.has(n.price_symbol)),tracked:all.filter(n=>added.has(n.price_symbol))};}
function storeState(){try{return g.PriceStore?.status?g.PriceStore.status({view:g}):null;}catch(_){return null;}}
const STORE_TEXT={OFF:'가격 탭 OFF · 설정 → 가격 저장 탭에서 먼저 켜세요',AUTH_REQUIRED:'구글 로그인이 필요합니다',SHEET_NOT_CONNECTED:'연결된 시트가 없습니다(설정 → Google 첫 설정)',LOADING:'내 시트 가격 탭 읽기 전',READY:'내 시트 가격 탭 연결됨',ERROR:'가격 탭을 쓸 수 없습니다'};
function confirmText(pending,cfg){const syms=[...new Set(pending.flatMap(n=>[n.price_symbol,n.sector_symbol]).concat(cfg.scoring_prices.benchmark))];
 return '판정 채점용 가격 추가 · 내 구글 시트\n\n다음 종목의 일봉 종가를 승인된 비공개 가격 Worker에서 받아 내 비공개 구글 시트의 '+cfg.scoring_prices.tab+' 탭에 덧붙입니다:\n'+syms.join(' · ')
  +'\n\n· 쓰는 곳은 내 시트 하나뿐입니다. 가격은 이 기기 메모리와 내 시트에만 있고 공개 파일·로그·저장소에는 남지 않습니다.\n· 이후 앱을 열 때 다른 핵심 종목처럼 마지막 저장일 이후 일봉만 덧붙입니다. 기록한 행은 고치지 않습니다.\n· 종가가 없는 날은 채점이 NA입니다(0으로 채우지 않음).\n\n추가할까요?';}
function pricesHtml(names,store,cfg,note){const code=store?.state||'OFF',ok=code==='READY'||code==='LOADING';
 return '<section class="card" data-tv1-prices><h2>판정 채점 가격 · TARGET v1 응답 종목</h2><p class="small">기존 19종목은 가상매매 엔진 시계열로 채점합니다. 그 밖의 종목은 가격 경로가 없어 NA이므로, 버튼을 누르고 확인하면 내 시트 '+esc(cfg.scoring_prices.tab)+' 탭에 일봉을 덧붙여 같은 방식으로 채점합니다. 화면에는 개수·날짜·코드만 표시합니다.</p>'
  +'<p data-tv1-prices-pending>가격 경로 없음 '+names.pending.length+'종목'+(names.pending.length?' · '+esc(names.pending.map(n=>n.price_symbol).join(' · ')):'')+'</p>'
  +'<p data-tv1-prices-tracked>내 시트에서 읽는 종목 '+names.tracked.length+(names.tracked.length?' · '+esc(names.tracked.map(n=>n.price_symbol).join(' · ')):'')+'</p>'
  +'<p class="small" data-tv1-prices-store>'+esc((STORE_TEXT[code]||code)+(store&&store.fetch&&store.fetch!=='READY'?' · Worker '+store.fetch:''))+'</p>'
  +'<button type="button" data-tv1-add-prices '+(names.pending.length&&ok?'':'disabled')+'>내 시트 '+esc(cfg.scoring_prices.tab)+'에 '+names.pending.length+'종목 추가</button><p role="status" class="small" data-tv1-prices-status>'+esc(note||'')+'</p></section>';}
// Daily closes from the user's sheet into RAM only (fetch:false: reading never writes). {} when the store is off.
async function sheetCloses(symbols){const S=g.PriceStore,out={};if(!S||typeof S.dailyCloses!=='function')return out;for(const s of symbols){try{const c=await S.dailyCloses(s,null,{view:g,fetch:false});if(c&&typeof c==='object'&&Object.keys(c).length)out[s]=c;}catch(_){}}return out;}
async function sheetSync(symbols){const S=g.PriceStore;if(!S||typeof S.syncMany!=='function')return{state:'OFF'};return S.syncMany(g,symbols,'1d',{kind:'TV1',allowlistOnly:true});}
function syncText(r){if(!r||r.state!=='READY')return '추가 불가 · '+(r?.state||'OFF')+(r?.reason_codes?.length?' · '+r.reason_codes.join(', '):'');const f=Object.entries(r.failed||{}).filter(([k])=>k!=='WORKER_ALLOWLIST').map(([k,v])=>k+' '+v).join(', ');
 return '내 시트 추가 · 종목 '+r.symbols+' · 요청 '+r.fetched+' · 덧붙인 행 '+r.appended_rows+(r.not_allowed?' · WORKER_ALLOWLIST '+r.not_allowed:'')+(r.write_failed?' · WRITE_FAILED '+r.write_failed:'')+(f?' · '+f:'');}
// Symbols the user added for TV1 scoring (app open keeps them current with the other core symbols). Symbols only.
function priceSymbols(P=g.PlaybookScreen,storage=g.localStorage){try{return readState(P,storage).price_symbols.slice();}catch(_){return [];}}
function numberCheckHtml(cfg){const r=cfg.number_check.result||{};return r.passed===true?'<p data-tv1-number-check>숫자 검증 통과 · '+esc((r.companies??0)+'개 기업 · calc_version '+(r.calc_version||'NA')+' · '+(r.date||'NA'))+(cfg.number_check.result_label_ko?' · '+esc(cfg.number_check.result_label_ko):'')+' · 확정 순간 파일의 calc_version과 같아야 합니다</p>':'<p data-tv1-number-check>'+esc(cfg.number_check.message)+'</p>';}
function checkHtml(c,cfg){if(!c)return '';return '<div data-tv1-finalize-check><p>'+(c.blockers.length?'확정 불가 · 사유 '+c.blockers.length+'개':'확정 검사 통과')+'</p><ul class="small">'+c.blockers.map(b=>'<li data-tv1-blocker="'+esc(b)+'">'+esc(b+' · '+(BLOCKERS[b]||b))+'</li>').join('')+'</ul>'+(c.check?'<p class="small" data-tv1-published>최신 공개 파일 · calc_version '+esc(c.check.calc_version||'없음')+' · as_of '+esc(c.check.as_of||'NA')+' · Q '+c.check.q+'/'+c.check.size+' · G '+c.check.g+'/'+c.check.size+' · 정상 NA 행 '+(c.check.na_rows??0)+' · 계산 버전 다른 행 '+(c.check.mixed_rows??0)+' · 7일 넘은 행 '+(c.check.stale_rows??0)+' · 가장 오래된 수집 '+esc(c.check.oldest_acquired||'NA')+'</p>':'')
  +(c.blockers.includes('ROW_DATA_STALE')?'<p data-tv1-stale-action>'+esc(cfg.finalize_check.stale_action_ko)+'</p>':'')+(c.safety_failed?.length?'<p class="small" data-tv1-safety-recheck>재무 안전 재검사 불통과 · '+esc(c.safety_failed.join(' · '))+'</p>':'')+(c.v_incomplete?.length?'<p class="small" data-tv1-v-recheck>V3·V4 빠진 V · '+esc(c.v_incomplete.join(' · '))+'</p>':'')+'</div>';}
// The published price-free sec-qgv2.json, re-read now (no cache); null when it cannot be read (→ SEC_QGV2_NOT_AVAILABLE).
async function latestPublished(){try{const r=await g.fetch('sec-qgv2.json',{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',headers:{Accept:'application/json'}});if(!r.ok)return null;const t=await r.text();if(t.length>8*1024*1024)return null;return JSON.parse(t);}catch(_){return null;}}
function rawHtml(state,sel,cfg){const d=state.draft;return '<details class="card" data-tv1-raw><summary>원자료 보기</summary>'+(d?'<p class="small">Universe 행 '+d.universe_rows+' · 통과 '+d.eligible_count+' · 제외 '+esc(Object.entries(d.excluded_counts).map(([k,v])=>(EXCLUDE[k]||k)+' '+v).join(' · ')||'없음')+' · 프로필 '+esc(d.profile_id||'NA')+' · 유형 범위 '+esc(d.basis?.type_scope||'NA')+' · v2 기준일 '+esc(d.v2_as_of||'NA')+'</p><div class="table-wrap"><table><thead><tr><th>제외 종목</th><th>총점</th><th>사유</th><th>재무 안전</th></tr></thead><tbody>'+d.excluded.map(r=>'<tr><td>'+esc(r.symbol)+'</td><td>'+n1(r.total)+'</td><td>'+esc(r.reasons.map(x=>EXCLUDE[x]||x).join(' · '))+'</td><td>'+esc(SAFETY[r.safety]||r.safety)+'</td></tr>').join('')+'</tbody></table></div><p class="small">선정 과정 건너뜀 · '+esc(sel?.skipped.map(s=>s.symbol+' '+s.reason).join(' · ')||'없음')+'</p><div class="table-wrap"><table><thead><tr><th>종목</th><th>무효화 지표</th><th>조건</th><th>현재</th><th>규칙</th></tr></thead><tbody>'+(sel?.rows||[]).flatMap(r=>r.invalidations.map(c=>'<tr><td>'+esc(r.symbol)+'</td><td>'+esc(c.metric)+'</td><td>'+esc(c.op+' '+c.threshold)+'</td><td>'+esc(c.current)+'</td><td>'+esc(c.rule)+'</td></tr>')).join('')+'</tbody></table></div>':'<p>초안 없음</p>')+'<p class="small">규칙 · '+esc(Object.entries(cfg.templates.rules).map(([k,v])=>k+': '+v).join(' / '))+' · '+esc(cfg.config_version)+' · v0 · UNCALIBRATED</p></details>';}

// Settings > collapsed raw-data viewer only (owner screen rule 2026-10-14). Reading does not create a draft or rule index.
function rawDataHtml({playbook=g.PlaybookScreen,storage=g.localStorage,config=DEFAULT_CFG}={}){
 try{const state=readState(playbook,storage);return rawHtml(state,state.draft?B.currentSelection(state,config):null,config);}
 catch(_){return '<p data-tv1-raw>확인 불가 · TARGET 기기 기록을 읽을 수 없습니다.</p>';}
}
/* ---------- mount ---------- */
async function mount(host,context={}){
 if(!host)return;const P=context.playbook||g.PlaybookScreen,cfg=context.config||DEFAULT_CFG,storage=context.storage||g.localStorage,date=context.date||today(),catalog=context.catalog||await context.catalogPromise,screens=context.screens||{};
 const inputs=screens?.['sec-qgv2.json']||null,computed=context.computed||null,ready=computed?.v2_state==='READY',universeCodes=context.universeCodes||[],closesFor=context.closesProvider||defaultCloses;
 const loadPublished=context.publishedProvider||latestPublished;let lastCheck=null;
 // PR-D: the central V at the click (QgvOfficial.resolve: one no-store read, never throws). officialSource / nyToday: test seams.
 const R=reader(),officialSource=context.officialSource||g;let lastOfficial=null,officialNote='';
 const officialNow=async published=>{try{return await R.resolve(officialSource,{secCalcVersion:published&&typeof published.calc_version==='string'?published.calc_version:null,nyToday:context.nyToday||R.nyToday()});}
  catch(_){return{ok:false,reason:'OFFICIAL_UNAVAILABLE',sessions:null,payload:null};}};
 // Input basis of the published file, only when it is the file the page's scores were computed from (same as_of).
 const basisFor=async published=>{if(!published)return null;try{return await B.inputBasis(published);}catch(_){return null;}};
 const readCloses=context.scoringClosesProvider||sheetCloses,syncPrices=context.priceSync||sheetSync,ask=context.confirm||(t=>g.confirm(t)),storeOf=context.priceStoreStatus||storeState;
 let state;try{state=readState(P,storage);}catch(_){host.innerHTML='<section class="card" data-tv1-builder><h2>TARGET v1 빌더</h2><p>확인 불가 · 기기 기록을 읽을 수 없습니다.</p></section>';return;}
 let message='',armed=false/* false | 'auto' | 'official' */,round=null,cmp=null,review=null,priceNote='';const cover=B.coverage(inputs,cfg);
 const save=next=>{writeState(P,storage,next);state=next;};
 // C: R-B starts the day v2 is ready on this device and is re-selected on every quarterly rebalance day (no backfill).
 if(ready&&B.ruleBDue(state,date,cfg)){try{const eligible=B.universeRows({computed,inputs,universeCodes,existing:existingSymbols(catalog),cfg}).filter(r=>!B.exclusions(r,cfg).length),seg=B.ruleBSegment(eligible,date,cfg);if(seg.ready){const{ready:_,...row}=seg;save({...state,rule_b:[...state.rule_b,row]});message='R-B(규칙 지수) 선정 · '+date+' · '+seg.rows.length+'종목';}}catch(_){}}
 // T-PRICE: series of the tracked TV1 names, read from the user's sheet into RAM, fed to the playbook scoring table.
 const refreshScoring=async()=>{const names=scoringNames(P,storage,catalog,inputs,state,cfg);if(!names.tracked.length||!P.addScoringSeries)return 0;
  const syms=[...new Set(names.tracked.flatMap(n=>[n.price_symbol,n.sector_symbol]).concat(cfg.scoring_prices.benchmark))],closes=await readCloses(syms),series={};
  for(const n of names.tracked){const s=B.scoringSeries(n,closes,cfg);if(s)series[n.symbol]=s;}P.addScoringSeries(series);
  const table=host.ownerDocument?.querySelector('[data-playbook-scoring]');if(table&&P.scoringSeries){let records=[];try{records=P.read(storage).records;}catch(_){records=[];}table.outerHTML=P.scoringHtml(records,P.scoringSeries());}
  return Object.keys(series).length;};
 const draw=()=>{if(!host.isConnected)return;const sel=state.draft?B.currentSelection(state,cfg):null;
  host.innerHTML='<section class="card" data-tv1-builder><h2>TARGET v1 빌더 · 규칙 기반 선정</h2><p class="small">QGV v2 기준 · '+esc(cfg.config_version)+' · v0 · UNCALIBRATED · 이 기기에서 계산(가격은 RAM에만) · 공개·전송 없음</p><p data-tv1-coverage>'+esc(cover.label||'커버리지 조건 충족 (Q '+cover.q+'/'+cover.size+', G '+cover.g+'/'+cover.size+')')+'</p><p data-tv1-readiness>'+(ready?'QGV v2 계산됨 · 기기 가격 '+esc(computed.priced_codes??'NA')+'종목':'NA · QGV v2 총점에는 V가 필요하고 V에는 이 기기의 가격이 필요합니다(유니버스 시트 읽기·가격 저장소). 초안 만들기 비활성')+'</p>'
   // M3: before a click nothing claims 임시 V or 공식 V. Without device prices only the central V can make a draft (its own button).
   +(R?'<p class="small" data-tv1-v-plan>V 출처: 초안 만들 때 확인 · 유효한 중앙 게시본이 있으면 공식 V, 없으면 임시 V'+(ready?'':' · 이 기기 가격이 없으면 공식 V로만 만들 수 있습니다')+'</p>':'')
   +'<button type="button" data-tv1-build '+(ready?'':'disabled')+'>'+(armed==='auto'?'다시 만들면 카드 응답이 초기화됩니다 · 한 번 더 누르세요':state.draft?'규칙으로 초안 다시 만들기':'규칙으로 초안 만들기')+'</button>'
   +(R&&!ready?'<button type="button" data-tv1-build-official>'+(armed==='official'?'다시 만들면 카드 응답이 초기화됩니다 · 한 번 더 누르세요':'중앙 V 게시본으로 초안 '+(state.draft?'다시 ':'')+'만들기')+'</button>':'')
   +(officialNote?'<p class="small" data-tv1-official-reason>'+esc(officialNote)+'</p>':'')+'<p role="status" data-tv1-status>'+esc(message)+'</p></section>'
   +(state.draft?candidateTable(state.draft,cfg,lastOfficial)+selectionHtml(sel,cfg)+'<section data-tv1-cards><h2>카드 응답 · '+(sel.rows.length-sel.pending.length)+'/'+sel.rows.length+'</h2><p class="small">반대는 한 줄 이유가 필요하고 그 종목은 빠지며 다음 순위가 자동으로 들어옵니다(한도 재검사). 모름은 유지하고 미확인으로 기록합니다. 모든 응답은 판정 기록으로 저장되어 나중에 채점됩니다.</p>'+sel.rows.map(r=>cardHtml(r,sel.answers[key(r.symbol)],cfg,sourceOf(state.draft))).join('')+'</section><section class="card" data-tv1-confirm><h2>TARGET v1 확정</h2><p>응답 '+(sel.rows.length-sel.pending.length)+'/'+sel.rows.length+' · '+esc(limitsText(sel.limits))+'</p>'+numberCheckHtml(cfg)+'<p data-tv1-v-source>V 출처: '+esc(sourceOf(state.draft).ko+' · '+sourceOf(state.draft).note+officialText(state.draft))+' · 확정 기록에 남습니다</p>'+attributionHtml(state.draft,lastOfficial)+scheduleHtml(state,cfg,date)+'<p class="small">확정 버튼을 누르는 순간 최신 공개 sec-qgv2.json을 다시 읽어 calc_version·값이 있는 행의 SEC 수집 시각 '+cfg.finalize_check.freshness_max_days+'일 이내(파일 as_of 아님)·초안 입력 기준·선정 종목 재무 안전·Q·G 산출 '+Math.round(cfg.coverage.ready_min_ratio*100)+'% 이상을 검사합니다(초안 때 결과는 쓰지 않음).'+(R?' 중앙 V 게시본도 다시 읽어 초안의 V 출처와 같은지 확인합니다(다르면 초안 재생성).':'')+'</p><button type="button" data-tv1-finalize '+(sel.complete&&!sel.shortfall?'':'disabled')+'>TARGET v1 확정 저장</button>'+checkHtml(lastCheck,cfg)+''+(state.versions.length?'<p data-tv1-version>저장된 TARGET '+esc(B.latestVersion(state).version+' · '+B.latestVersion(state).date+' · V 출처 '+(B.V_SOURCES?.[B.latestVersion(state).v_source]||B.V_SOURCE).ko+(B.latestVersion(state).price_basis_date?' · 가격 기준일 '+B.latestVersion(state).price_basis_date:''))+'</p>':'')+'</section>':'')
   +rebalanceHtml(state,catalog,context.ram,cfg,date,round)+transitionHtml(state,cfg,date,cmp,review)+setsHtml(state,cfg,date)+pricesHtml(scoringNames(P,storage,catalog,inputs,state,cfg),storeOf(),cfg,priceNote);
  bind(sel);};
 const say=t=>{message=t;const n=host.querySelector('[data-tv1-status]');if(n)n.textContent=t;};
 const run=fn=>{try{fn();}catch(e){say(ERRORS[e.message]===null?cfg.number_check.message:ERRORS[e.message]||e.message);}};
 const bind=sel=>{
  // The draft records its input basis (calc_version, as_of, per-shard acquisition) when the re-read file is the page's file.
  // PR-D M3/M4: the central V is read at this click next to sec-qgv2.json; usable → the draft from its rows (official), else the
  // device scores as before (mode 'auto'), or no draft (mode 'official': the button shown without device prices).
  const buildWith=async mode=>{if(state.draft&&state.answers.length&&armed!==mode){armed=mode;draw();return;}armed=false;
   const published=await loadPublished();if(!host.isConnected)return;const off=R?await officialNow(published):null;if(!host.isConnected)return;
   const basis=published&&inputs?.as_of&&published.as_of===inputs.as_of?await basisFor(published):null;if(!host.isConnected)return;
   const pub=off?.ok?off.payload:null;if(pub)lastOfficial=pub;officialNote=off&&!pub?reasonLine(off.reason,mode==='auto'):'';
   if(mode==='official'&&!pub){message='공식 V 초안 불가 · 임시 V 초안에는 이 기기의 가격이 필요합니다';draw();return;}
   run(()=>{const draft=pub?B.buildDraft({computed:B.officialComputed(pub),inputs,universeCodes,existing:existingSymbols(catalog),date,basis,official:pub,cfg}):B.buildDraft({computed,inputs,universeCodes,existing:existingSymbols(catalog),date,basis,cfg});save({...state,draft,answers:[]});message='초안 만듦 · 통과 '+draft.eligible_count+' · 후보 '+B.candidates(draft,cfg).length+(basis?' · 입력 기준 '+(basis.calc_version||'calc_version 없음'):' · 입력 기준 기록 불가(확정 때 재생성)')+(pub?' · 공식 V(가격 기준일 '+pub.times.price_basis_date+')':'');draw();});
   if(off&&!pub)draw();};
  const build=host.querySelector('[data-tv1-build]');if(build)build.onclick=()=>buildWith('auto');
  const buildOfficial=host.querySelector('[data-tv1-build-official]');if(buildOfficial)buildOfficial.onclick=()=>buildWith('official');
  for(const card of host.querySelectorAll('[data-tv1-card]'))for(const b of card.querySelectorAll('[data-tv1-answer]'))b.onclick=()=>run(()=>{
   const symbol=card.dataset.tv1Card,kind=b.dataset.tv1Answer,reason=card.querySelector('[data-tv1-reason]').value,row=sel.rows.find(r=>r.symbol===symbol);
   const next=B.answer(state,{symbol,answer:kind,reason,date},cfg),saved=next.answers[next.answers.length-1];
   P.saveRecord(storage,B.judgementRecord({row,answer:kind,reason:saved.reason,date,id:'TV1-'+date+'-'+symbol+'-'+kind+'-'+Date.now()+'-'+Math.random().toString(36).slice(2,6)},cfg));save(next);
   const after=B.currentSelection(state,cfg),added=after.rows.filter(r=>!sel.rows.some(x=>x.symbol===r.symbol)).map(r=>r.symbol);
   message=kind==='DISAGREE'?'반대 · '+symbol+' 제외 → '+(added.length?added.join(' · ')+' 추가':'교체 후보 없음 · 현금')+' · '+limitsText(after.limits):cfg.cards.answers.find(a=>a.id===kind).ko+' · '+symbol+' 기록됨';draw();});
  // Finalize: re-read the published file now and re-check everything (never the draft-time state).
  const fin=host.querySelector('[data-tv1-finalize]');if(fin)fin.onclick=async()=>{fin.disabled=true;say('최신 공개 파일 다시 읽는 중');const published=await loadPublished();if(!host.isConnected)return;
   // PR-D M3: the central V re-read at this click too; the source usable now is checked against the draft's (V_SOURCE_CHANGED).
   const off=R?await officialNow(published):null;if(!host.isConnected)return;const official=off?.ok?off.payload:null;if(official)lastOfficial=official;officialNote=off&&!official?reasonLine(off.reason,false):'';
   const basis=await basisFor(published);if(!host.isConnected)return;lastCheck=B.finalizeBlockers(state,{date,published,basis,official,cfg});
   // Changed input basis on a valid file → regenerate the draft (same-symbol answers kept); needs the page's scores of that file.
   const fileOk=!!lastCheck.check&&!lastCheck.check.reasons.some(r=>['SEC_QGV2_NOT_AVAILABLE','CALC_VERSION_MISSING','CALC_VERSION_MIXED'].includes(r));
   if(lastCheck.basis_changed&&fileOk){
    // From the source usable now: the publication's rows when it is usable, else the page's device scores (the rules as before).
    const moved=lastCheck.v_source_changed===true;
    if((official||ready)&&inputs?.as_of&&published.as_of===inputs.as_of){try{const r=B.regenerateDraft(state,{computed:official?B.officialComputed(official):computed,inputs,universeCodes,existing:existingSymbols(catalog),date,basis,official,cfg});save(r.state);lastCheck=B.finalizeBlockers(state,{date,published,basis,official,cfg});
      message=(moved?'V 출처가 바뀌어('+sourceOf(r.state.draft).ko+') ':'입력 기준이 바뀌어 ')+'초안을 다시 만들었습니다 · 응답 유지 '+r.carried.length+' · 새로 확인할 종목 '+r.fresh.length+(r.fresh.length?' ('+r.fresh.join(' · ')+')':'')+' · 카드 확인 후 다시 확정하세요';}catch(e){message='초안 재생성 불가 · '+(ERRORS[e.message]||e.message);}}
    else message=moved?'V 출처(공식 V ↔ 임시 V, 또는 중앙 V 게시본)가 초안과 달라 초안을 다시 만들어야 합니다'+(official?'':' · 임시 V로 만들려면 이 기기의 가격이 필요합니다')+' · 페이지를 새로 고친 뒤 다시 확정하세요':'입력 기준(calc_version·유형 적용 범위·신원 충돌 사용 중지·샤드별 수집 시각)이 초안과 달라 초안을 다시 만들어야 합니다 · 페이지를 새로 고친 뒤 다시 확정하세요';
    draw();return;}
   try{const next=B.finalize(state,{date,published,basis,official,cfg});save(next);const v=B.latestVersion(next);message='TARGET '+v.version+' 저장 · calc_version '+v.calc_version+' · R-C(규칙 지수) '+date+' 시작 · 원본 v0 유지'+(v.publication_id?' · 공식 V 게시본 '+v.publication_id.slice(0,19)+' · 가격 기준일 '+v.price_basis_date:'');}
   catch(e){message=ERRORS[e.message]===null?cfg.number_check.message:e.message==='NUMBER_CHECK_CALC_VERSION_MISMATCH'?cfg.number_check.mismatch_message:ERRORS[e.message]||('확정 불가 · '+(BLOCKERS[e.message]||e.message));}draw();};
  for(const b of host.querySelectorAll('[data-tv1-round]'))b.onclick=()=>{round=Number(b.dataset.tv1Round);draw();};
  const load=host.querySelector('[data-tv1-load-compare]');if(load)load.onclick=async()=>{try{say('가격 불러오는 중 · 이 기기 RAM');const v0=v0Weights(catalog),bSyms=state.rule_b.flatMap(s=>s.rows.map(r=>r.symbol)),cSyms=(state.versions.find(v=>v.version===state.rule_c?.version)?.rows||[]).map(r=>r.symbol);
   const from=state.rule_c?.start||date,closes=await closesFor([...new Set([cfg.virtual_sets.benchmark.symbol,...Object.keys(v0),...bSyms,...cSyms])],from);if(!host.isConnected)return;
   cmp=B.compareSets({state,v0Weights:v0,closes,asOf:date,cfg});review=B.reviewRule({compare:cmp,date,cfg});message='성과 계산 · RAM 전용';draw();}catch(_){say('성과 계산 불가');}};
  // T-PRICE: the only write path — the user's click, then an explicit confirm; the sheet is the user's own private sheet.
  const add=host.querySelector('[data-tv1-add-prices]');if(add)add.onclick=async()=>{const names=scoringNames(P,storage,catalog,inputs,state,cfg);if(!names.pending.length)return;
   if(!ask(confirmText(names.pending,cfg))){priceNote='취소 · 시트를 바꾸지 않았습니다';draw();return;}
   try{const next=B.addPriceSymbols(state,names.pending,cfg);add.disabled=true;priceNote='내 시트에 추가하는 중 · 개수만 표시';const n=host.querySelector('[data-tv1-prices-status]');if(n)n.textContent=priceNote;
    const r=await syncPrices(next.price_symbols);if(!host.isConnected)return;
    // Symbols outside the Worker allowlist are not tracked (no fetch path; they stay NA).
    if(r?.state==='READY')save({...next,price_symbols:next.price_symbols.filter(x=>r.results?.[x]?.code!=='WORKER_ALLOWLIST')});priceNote=syncText(r);
    if(r?.state==='READY'){const scored=await refreshScoring();if(!host.isConnected)return;priceNote+=' · 채점 시계열 '+scored+'종목(RAM)';}}
   catch(e){priceNote='추가 불가 · '+(e.message||'WRITE_FAILED');}draw();};
 };
 draw();void refreshScoring().catch(()=>0);return{state:()=>state,refreshScoring};
}
return Object.freeze({mount,readState,writeState,v0Weights,existingSymbols,priceSymbol,priceSymbols,confirmText,rawDataHtml});
});
