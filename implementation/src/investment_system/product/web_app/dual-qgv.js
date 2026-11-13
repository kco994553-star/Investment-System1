/* 두 모형 연구 결과 reader (IS2.dualQgv; owner 2026-11-10 「통합 QGV·섹터 QGV」, 2026-11-11 「두 모형 실제 연결」; Codex #529
   46f73a07 research.dual_qgv.delivery_artifacts → qgv-dual-delivery/1, DUAL_QGV.md). Read as written; nothing is recalculated,
   re-ranked, filled or stitched (DC-42: Main uses the supplied counts, weights and ranks, never aggregates itself).
   - What it is: three preregistered research candidates on one evaluation population — U1 unified-roa-core and U2 unified-sales-core
     (통합 연구: one common core for every evaluated company, one common reference pool) and S1 sector-reduced-core (섹터 연구:
     sector × accounting model core, 핵심 요소 축소). PRIVATE_RESEARCH, NOT_ADOPTED, performance NOT_MEASURED: never the official QGV,
     never a default, never a performance claim. U1 / U2 / S1 scores are not on one scale and are never averaged, summed or differenced.
   - Selectable is not the same as complete: a delivery that passes every check below can be chosen and read (Q / G / factors / missing
     reasons) even when V and the total are null everywhere. A null total has no total rank (RANK_WITHOUT_TOTAL refuses otherwise).
     Recalculation, saving and replay are separate states: this screen shows retained results only (재계산 연결 안 됨); replay is the
     producer's (qgv-dual-saved/1, the same configuration, code and both input identities, else refused).
   - Trust: the delivery manifest's bytes are pinned at staging; here each file's own bytes are checked against the manifest (size and
     SHA-256, not a re-encoding), and the evaluation population must be the result already delivered in the checked held issuer
     bundle (coverage scope: population id / version / members hash / code-row denominator / evaluation day, and the input hash —
     operating504: the evaluation input; held1057: the reference source input, the evaluation rows being its projection).
   - Scopes: operating504 (평가 504 code rows / 501 issuers) and held1057 (보유 금융 표본 1057 issuers) are separate populations, never
     summed; the whole-market denominator and coverage are null (미측정).
   Pure except sha256 (passed in by the caller, WebCrypto); the RAM holder (ram) keeps checked deliveries until the classification
   bundle is dropped. No storage, no request of its own. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.dualQgv=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA=Object.freeze({MANIFEST:'qgv-dual-delivery-manifest/1',SUMMARY:'qgv-dual-delivery/1',INDEX:'qgv-dual-index/1',DETAIL:'qgv-dual-detail/1'});
// input: which side's input hash the delivered result names. operating504's evaluation input is that result's own input
// (EVALUATION_INPUT_MATCHED). held1057's evaluation input (a projection of the held rows) is not the delivered result's input;
// only its reference source input is, so its evaluation input stays UNVERIFIED until Codex gives the members / derivation / hash
// link (owner 2026-11-11 §2, #437 6794173362 q.1). The screen says so; it is never shown as a verified evaluation input.
const SCOPES=Object.freeze({
 operating504:Object.freeze({label:'운영504',anchor:'operating',input:'evaluation',text:'평가 504코드 행 / 501발행사'}),
 held1057:Object.freeze({label:'보유1057',anchor:'held_financial_subsample',input:'reference',text:'보유 재무 표본 1057발행사 · 운영504와 합치지 않음'})});
// Slots: where a checked delivery is held. A 3/3/3 delivery is the same evaluation scope (its manifest names operating504 / held1057)
// in its own slot ('<scope>@333', read with set=333 from its own private directory), so the reduced U1 / U2 / S1 delivery stays.
const SLOTS=Object.freeze({operating504:Object.freeze({scope:'operating504',gen:'REDUCED'}),held1057:Object.freeze({scope:'held1057',gen:'REDUCED'}),
 'operating504@333':Object.freeze({scope:'operating504',gen:'Q333'}),'held1057@333':Object.freeze({scope:'held1057',gen:'Q333'})});
const INPUT_CHECK=Object.freeze({evaluation:'EVALUATION_INPUT_MATCHED',reference:'REFERENCE_INPUT_MATCHED_EVALUATION_UNVERIFIED'});
// operating504's reference input is not tied to an independent anchor here (the staged bundle names only the evaluation input), so
// a delivery whose reference hash was changed consistently is not refused on that side; the word says so (Codex binding cases).
const INPUT_WORD=Object.freeze({EVALUATION_INPUT_MATCHED:'평가 입력 = 지금 받은 결과의 입력(해시 일치) · 참조 입력은 독립 기준과 대조 안 됨',
 REFERENCE_INPUT_MATCHED_EVALUATION_UNVERIFIED:'참조 원천 입력만 일치 · 평가 입력 연결 미확인(투영 증명 파일 없음)',
 EVALUATION_INPUT_PROJECTION_ATTESTED:'평가 입력 = 참조 원천의 투영 · 생산자 투영 증명과 대조됨(화면이 다시 계산한 것 아님)',
 EVALUATION_INPUT_MATCHED_REFERENCE_ANCHORED:'평가 입력 = 지금 받은 결과의 입력(해시 일치) · 참조 입력 = 생산자 독립 기준(참조 후보 스냅숏의 전체 신원)과 일치'});
// operating504's reference input against Codex's independent anchor (qgv-dual-reference-anchor/1, #437 6819835921): the full identity
// of the retained reference candidate snapshot, pinned at staging with its byte SHA and the staged #528 view's SHA. Every board's
// reference binding and its candidate population must be exactly that identity. The #528 view's selected-reference members are a
// different set and are not compared as if they were the same; the original catalog binding is another population again.
// Both sides of the input checked against an independent producer file: held1057 by its projection proof, operating504 by its
// reference anchor (its evaluation input is the result's own). Any other state is an unverified view, said so on every screen that
// shows the delivery's results, and never taken as verified.
const INPUT_VERIFIED=Object.freeze(['EVALUATION_INPUT_PROJECTION_ATTESTED','EVALUATION_INPUT_MATCHED_REFERENCE_ANCHORED']);
const inputVerified=d=>!!d&&CHECKED.has(d)&&INPUT_VERIFIED.includes(d.input_check);
const inputLine=d=>(inputVerified(d)?'입력 검증 완료 · ':'입력 검증 미완료 · 미검증 조회 · ')+INPUT_WORD[d.input_check];
const REF_ANCHOR_SCHEMA='qgv-dual-reference-anchor/1';
const REF_ANCHOR_KEYS=['schema_version','scope','expected_reference','source_snapshot_sha256','source_reference_view_sha256','source_reference_view_path',
 'source_reference_view_input_hash_field','source_reference_view_members_not_interchangeable','source_original_catalog_binding','matches_all_dual_boards',
 'eligible_members_are_not_candidate_members','old_selected_reference_rows','candidate_rows','generation_rule','new_score_calculations'];
function referenceAnchorCheck(x,scope,boards){const at='reference_anchor';exact(x,REF_ANCHOR_KEYS,at);
 if(x.schema_version!==REF_ANCHOR_SCHEMA)refuse('REFERENCE_ANCHOR_SCHEMA',at+'.schema_version');if(x.scope!==scope)refuse('SCOPE_MISMATCH',at+'.scope');
 if(!HEX.test(x.source_snapshot_sha256)||!HEX.test(x.source_reference_view_sha256)||x.matches_all_dual_boards!==true||x.new_score_calculations!==0
  ||x.source_reference_view_members_not_interchangeable!==true||!isObj(x.expected_reference)||x.expected_reference.code_rows!==x.candidate_rows)refuse('REFERENCE_ANCHOR_INVALID',at);
 for(const[k,b]of Object.entries(boards)){
  if(!same(b.bindings.reference,x.expected_reference))refuse('REFERENCE_ANCHOR_MISMATCH',at+'.expected_reference@'+k+'.bindings.reference');
  if(!same(b.reference_population.candidate_population,x.expected_reference)||b.reference_population.input_hash!==x.expected_reference.input_hash)
   refuse('REFERENCE_ANCHOR_MISMATCH',at+'.expected_reference@'+k+'.reference_population');}}
// The producer's projection proof of held1057's evaluation input (Codex 6794279588 §2, qgv-dual-input-projection-proof/1): it must
// bind exactly this delivery's evaluation population and reference source (the staged held input), a selection of that many
// issuers, only the five projection fields changed, row values and classification unchanged, no whole market, no new score.
const LINEAGE_SCHEMA='qgv-dual-input-projection-proof/1';
const PROJECTION_FIELDS=Object.freeze(['members','rows','snapshot_id','universe_id','universe_version']);
function lineageCheck(x,boards){const at='lineage';if(!isObj(x)||x.schema_version!==LINEAGE_SCHEMA)refuse('LINEAGE_SCHEMA',at+'.schema_version');
 for(const[k,b]of Object.entries(boards)){if(!same(x.evaluation,b.evaluation_population))refuse('LINEAGE_MISMATCH',at+'.evaluation');
  if(!same(x.reference_source,b.bindings.reference))refuse('LINEAGE_MISMATCH',at+'.reference_source');
  if(x.reference_source.input_hash!==b.reference_population.input_hash)refuse('LINEAGE_MISMATCH',at+'.reference_source.input_hash');}
 const ev=x.evaluation;
 if(x.selected_issuer_count!==ev.issuers||!HEX.test(x.selected_issuer_members_hash)||typeof x.selection_rule!=='string'||!x.selection_rule)refuse('LINEAGE_INVALID',at+'.selected_issuer_count');
 if(x.rows_equal_source_projection!==true||x.row_values_or_classification_changed!==false)refuse('LINEAGE_INVALID',at+'.rows_equal_source_projection');
 if(!Array.isArray(x.changed_top_level_fields)||!same([...x.changed_top_level_fields].sort(),PROJECTION_FIELDS))refuse('LINEAGE_INVALID',at+'.changed_top_level_fields');
 if(x.whole_market_denominator!==null||x.reference_source_is_not_eligible_whole_market!==true||x.new_score_calculations!==0)refuse('LINEAGE_INVALID',at+'.whole_market_denominator');}
const MODELS=Object.freeze({
 U1:Object.freeze({model_id:'unified-roa-core/0.1.0',kind:'COMMON',label:'통합 연구 U1',core:'Q ROA · G ROA 개선 · V 이익·장부',gen:'REDUCED'}),
 U2:Object.freeze({model_id:'unified-sales-core/0.1.0',kind:'COMMON',label:'통합 연구 U2',core:'Q ROA · G 매출 성장 · V 이익·장부',gen:'REDUCED'}),
 S1:Object.freeze({model_id:'sector-reduced-core/0.1.0',kind:'SECTOR',label:'섹터 연구 S1',core:'섹터·회계모형별 축소 핵심 요소',gen:'REDUCED'}),
 // The 3/3/3 candidates (owner 2026-11-13; Codex #534 qgv-333-contract/1, QGV_333.md): their own ids, version, adapter and the exact
 // configuration each was registered with (configuration_hash = SHA-256 of the contract's canonical candidate config, so its axes,
 // roles and integer weights). A board whose model, version, adapter or configuration differs is refused; never read as another one.
 'U2-333':Object.freeze({model_id:'unified-333-eps/0.1.0',kind:'COMMON',label:'통합 연구 U2-333',core:'Q3 · G3 · V3 · G에 희석 EPS 3년 성장',gen:'Q333',version:'0.1.0',
  adapter:'dual-qgv-research/0.2.0',config:'qgv-dual-config/2',configuration_hash:'8f102656cb5680e188f5551464f3ee685d21bee2506b9e95173a0eb07a96f3ab',
  factors:Object.freeze(['roa_ttm','accruals_assets_ttm','debt_assets','revenue_cagr_3y','eps_diluted_cagr_3y','roa_improvement_3y','ep_ttm_diluted','common_bp','cfo_mcap'])}),
 'U1-333':Object.freeze({model_id:'unified-333-persistence/0.1.0',kind:'COMMON',label:'통합 연구 U1-333',core:'Q3 · G3 · V3 · G에 매출 성장 지속성(U2-333과 G 한 요소만 다름)',gen:'Q333',version:'0.1.0',
  adapter:'dual-qgv-research/0.2.0',config:'qgv-dual-config/2',configuration_hash:'8d57491b52c0c406558793d41b5d50b8cc6b6e98fd90766500b74baaa103fa15',
  factors:Object.freeze(['roa_ttm','accruals_assets_ttm','debt_assets','revenue_cagr_3y','revenue_growth_consistency_3y','roa_improvement_3y','ep_ttm_diluted','common_bp','cfo_mcap'])}),
 'S1-333':Object.freeze({model_id:'sector-333/0.1.0',kind:'SECTOR',label:'섹터 연구 S1-333',core:'Q3 · G3 · V3 · 섹터×회계모형별 구성 · 축 비중은 기존 섹터 설정',gen:'Q333',version:'0.1.0',
  adapter:'dual-qgv-research/0.2.0',config:'qgv-dual-config/2',configuration_hash:'9efb87060cb095b817c56652966ae4ec6c67bf23ad7f959e00f173da43be5864',factors:null})});
// A delivery carries one generation only: the reduced U1 / U2 / S1 or the 3/3/3 candidates, never both in one bundle (the 3/3/3
// boards are their own models, not a newer version of U1 / U2 / S1). Each is held in its own slot, so loading one never replaces the other.
const GEN=Object.freeze({REDUCED:'축소 구성 U1·U2·S1(Q1·G1·V2 / Q2·G1·V2)',Q333:'3/3/3 U2-333·U1-333·S1-333(Q3·G3·V3)'});
// The 3/3/3 factor evidence, as the contract's factor table states it (axis, role, name, formula, period, direction, calculator
// state; tools/web_app_dual_qgv_333_node_test.js keeps it equal to qgv-333-contract.json). Display only: never a weight or a score.
const E=(axis,role,name,formula,period,direction,status)=>Object.freeze({axis,role,name,formula,period,direction,status});
const EVIDENCE_333=Object.freeze({
 accruals_assets_ttm:E('Q','accounting_quality','발생액/평균자산','difference_average','TTM','LOWER','IMPLEMENTED'),
 cfo_assets_improvement_3y:E('G','profitability_change','CFO/자산 3년 개선','difference','FY_3Y','HIGHER','IMPLEMENTED'),
 cfo_assets_ttm:E('Q','profitability','CFO/평균자산','ratio_average','TTM','HIGHER','IMPLEMENTED'),
 cfo_mcap:E('V','cash','PCR / CFO 수익률','ratio','TTM','HIGHER','IMPLEMENTED'),
 common_bp:E('V','other_value','PBR / 보통주 B/P','ratio','LATEST_QUARTER','HIGHER','IMPLEMENTED'),
 common_bps_cagr_3y:E('G','growth','보통주 BPS 3년 CAGR','cagr3','FY_3Y','HIGHER','IMPLEMENTED'),
 common_equity_assets:E('Q','financial_capacity','보통주자본/자산','ratio','LATEST_QUARTER','HIGHER','IMPLEMENTED'),
 debt_assets:E('Q','financial_capacity','차입금/자산','ratio','LATEST_QUARTER','LOWER','IMPLEMENTED'),
 dividend_yield_ttm:E('V','other_value','배당수익률','ratio','TTM','HIGHER','IMPLEMENTED'),
 ebitda_ev:E('V','other_value','EV/EBITDA','sum_ratio','TTM','HIGHER','IMPLEMENTED'),
 ep_ttm_diluted:E('V','earnings','PER / E/P (TTM 희석)','ratio','TTM','HIGHER','IMPLEMENTED'),
 eps_diluted_cagr_3y:E('G','growth','희석 EPS 3년 CAGR','cagr3','FY_3Y','HIGHER','IMPLEMENTED'),
 fcf_mcap:E('V','other_value','P/FCF (CFO−CAPEX)','difference_ratio','TTM','HIGHER','IMPLEMENTED'),
 ffo_per_share_growth:E('G','growth','FFO/주 성장','pending','UNRESOLVED','HIGHER','PENDING_DEFINITION'),
 interest_coverage_ttm:E('Q','interest_capacity','이자보상배율','ratio','TTM','HIGHER','IMPLEMENTED'),
 nareit_ffo_mcap:E('V','earnings','P/FFO (Nareit)','ratio','TTM','HIGHER','IMPLEMENTED'),
 operating_margin_ttm:E('Q','profitability','영업이익률','ratio','TTM','HIGHER','IMPLEMENTED'),
 revenue_cagr_3y:E('G','growth','매출 3년 CAGR','cagr3','FY_3Y','HIGHER','IMPLEMENTED'),
 revenue_growth_consistency_3y:E('G','growth','매출 성장 지속성','positive_growth_share','FY_3Y','HIGHER','IMPLEMENTED'),
 roa_improvement_3y:E('G','profitability_change','3년 ROA 개선','difference','FY_3Y','HIGHER','IMPLEMENTED'),
 roa_ttm:E('Q','profitability','ROA','ratio_average','TTM','HIGHER','IMPLEMENTED'),
 roe_common_ttm:E('Q','profitability','보통주 ROE','ratio_average','TTM','HIGHER','IMPLEMENTED'),
 sales_ev:E('V','other_value','EV/Sales','ratio','TTM','HIGHER','IMPLEMENTED'),
 sales_mcap:E('V','other_value','PSR / 매출수익률','ratio','TTM','HIGHER','IMPLEMENTED')});
const PERIOD_WORD=Object.freeze({TTM:'최근 4분기(TTM)',FY_3Y:'회계연도 3년(4개 연간 관측)',LATEST_QUARTER:'최근 분기말',UNRESOLVED:'기간 미정(정의 준비 중)'});
const DIRECTION_WORD=Object.freeze({HIGHER:'높을수록 좋음',LOWER:'낮을수록 좋음(점수는 좋은 쪽이 높게)'});
const RECIPE_WORD=Object.freeze({DEFINED_RESEARCH:'정의된 연구 구성',PREPARING:'정의 준비 중 · 총점 없음(G 세 번째 요소 정의 미승인 등) · Q·V·개별 요소는 따로 산출',
 MAPPING_UNRESOLVED:'분류 미확정 · 구성 적용 안 됨'});
const KIND=Object.freeze({COMMON:'통합 · 모든 평가 기업에 같은 핵심 요소와 같은 참조집단',SECTOR:'섹터 · 섹터×회계모형별 핵심 요소 · 다른 회계모형 순위와 합치지 않음'});
const BOARD_KEYS=Object.freeze(['model_id','model_version','engine_version','adapter_version','normalization_version','evaluation_population','reference_population',
 'bindings','cache_key','result_hash','coverage','classification_mode','performance_state','operating_adoption','deployment_state','configuration_hash']);
const COVERAGE_KEYS=Object.freeze(['denominator','target95','stages','causes_overlap','causes','incomplete_unique','current_sample_barrier','gap95','whole_market_denominator','whole_market_coverage']);
const STAGES=Object.freeze([['core_inputs','핵심 요소 입력 모두'],['core_raw','핵심 요소 원지표 모두'],['core_scores','핵심 요소 점수 모두'],['Q','Q 축'],['G','G 축'],['V','V 축'],['joint','세 축 동시'],['total','최종 총점']]);
// The 3/3/3 coverage also states 핵심 9요소 점수 모두 and 관문 판정 가능 (PASS + VALUE_EXCLUDED: a known gate, not total eligibility).
const STAGES_333=Object.freeze([...STAGES,['nine_core_scores','핵심 9요소 점수 모두'],['gate_known','관문 판정 가능(통과 + V 제외 · 총점 적격 아님)']]);
const stagesOf=gen=>gen==='Q333'?STAGES_333:STAGES;
const POP_KEYS=Object.freeze(['id','version','members_hash','valuation_date','as_of','code_rows','issuers','input_hash','snapshot_id','classification_records_hash','classification_context']);
const REF_EXTRA=Object.freeze(['factor_members_hash','candidate_population','scope']);
const HEAD_KEYS=Object.freeze(['axes','total','rank','rank_n','ranking_scope','status','gate_status']);
const DETAIL_KEYS=Object.freeze(['company_id','issuer_id','security_id','sector_id','accounting_template','factors','rank','status','axes','total','pre_gate_total','gate_status','ranking_scope','rank_n','selected_variants','scoring_representative']);
// Conditional-required (Codex #437 6794279588 §3, DUAL_QGV.md): present on every row with an applied preset, absent exactly when the
// row is MAPPING_UNRESOLVED (no preset); not tied to the total. Never filled with [] / 0 when absent.
const DETAIL_PRESET_FIELDS=Object.freeze(['missing_factors','nominal_axis_weights','nominal_effective_weights','post_gate_axis_weights','post_gate_effective_weights']);
const FACTOR_KEYS=Object.freeze(['raw_status','score','score_status','valid_n','raw_components_available','verified_external_available','kind','rank','rank_n','decile','decile_status']);
const MAX_BYTES=2000000;
const HEX=/^[0-9a-f]{64}$/,DAY=/^\d{4}-\d{2}-\d{2}$/,FILE=/^(summary|index)\.json$|^detail-\d{3}\.json$/,DETAIL_FILE=/^detail-\d{3}\.json$/;
const STATUS_WORD=Object.freeze({VALID:'산출',MISSING_INPUT:'입력 없음',MAPPING_UNRESOLVED:'분류 미확정',NOT_APPLICABLE:'산식 적용 부적합',PERIOD_MISMATCH:'기간 불일치',
 PEER_SAMPLE_SMALL:'비교 표본 부족(20 미만)',DOMAIN_INVALID:'값 범위 밖',GATE_UNKNOWN:'관문 판정 불가(UNKNOWN)',STRICT_INCOMPLETE:'핵심 요소 일부 미산출',
 PASS:'관문 통과',UNKNOWN:'관문 판정 불가',VALUE_EXCLUDED:'V 총점 반영 제외 · 기업 탈락 아님',
 // Codex #534 EPS history (6851482941): the historical common-share basis of that EPS is not confirmed — an input gap of its own,
 // never 「가격만 대기」.
 HISTORICAL_SHARE_BASIS_UNCONFIRMED:'역사 보통주 귀속 근거 미확인(가격 대기 아님)',
 ISSUER_REPRESENTATIVE_UNRESOLVED:'발행사 대표 행 미확정',SCOPE_MISMATCH:'비교 범위 불일치',SAMPLE_LT_10:'평가 유효 10개 미만 · 분위 없음',NO_VALID_SCORE:'유효 점수 없음'});
const word=c=>c===null||c===undefined?'—':STATUS_WORD[c]||String(c);

class Refusal extends Error{constructor(code,path){super(code);this.code=code;this.path=path;}}
const refuse=(c,p)=>{throw new Refusal(c,p);};
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const int=v=>Number.isInteger(v);
const num=v=>v===null||(typeof v==='number'&&Number.isFinite(v));
function canonical(v){if(Array.isArray(v))return'['+v.map(canonical).join(',')+']';
 if(isObj(v))return'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';return JSON.stringify(v);}
const same=(a,b)=>canonical(a)===canonical(b);
function exact(o,keys,at,optional=[]){if(!isObj(o))refuse('TYPE',at);for(const k of keys)if(!own(o,k))refuse('KEY_MISSING',at+'.'+k);
 for(const k of Object.keys(o))if(!keys.includes(k)&&!optional.includes(k))refuse('KEY_UNKNOWN',at+'.'+k);}
const count=(c,at,den)=>{exact(c,['code_rows','issuers'],at);if(!int(c.code_rows)||!int(c.issuers)||c.code_rows<0||c.issuers<0||c.issuers>c.code_rows)refuse('COUNT_RANGE',at);
 if(den&&(c.code_rows>den.code_rows||c.issuers>den.issuers))refuse('COUNT_RANGE',at);return c;};
// Only a delivery this reader checked can be held in RAM (the screens read nothing else).
const CHECKED=new WeakSet();
function freeze(o){if(o&&typeof o==='object'&&!Object.isFrozen(o)){Object.freeze(o);for(const v of Object.values(o))freeze(v);}return o;}

function population(p,at){if(!isObj(p))refuse('TYPE',at);
 for(const k of POP_KEYS)if(!own(p,k))refuse('KEY_MISSING',at+'.'+k);
 if(typeof p.id!=='string'||!p.id||typeof p.version!=='string'||!p.version||!HEX.test(p.members_hash)||!HEX.test(p.input_hash)
  ||!DAY.test(p.valuation_date)||typeof p.as_of!=='string'||!int(p.code_rows)||p.code_rows<1||!int(p.issuers)||p.issuers<1||p.issuers>p.code_rows)refuse('POPULATION_INVALID',at);}

// The 3/3/3 coverage's applicability-only upper bound (Codex qgv_333.extend_coverage): issuers left if every other input,
// classification, peer and gate gap were resolved; an assumption, never a forecast. Its arithmetic is checked as written.
const UPPER_KEYS=Object.freeze(['known_incompatible','issuers_all_rows_incompatible','optimistic_issuers','assumptions','can_reach95_under_known_scope']);
const UPPER_ASSUMPTION='ALL_OTHER_INPUTS_CLASSIFICATION_PEERS_AND_GATE_RESOLVED;NOT_FORECAST';
function upperBound(u,c,at){exact(u,UPPER_KEYS,at);const den=c.denominator;count(u.known_incompatible,at+'.known_incompatible',den);
 if(!int(u.issuers_all_rows_incompatible)||u.issuers_all_rows_incompatible<0||u.issuers_all_rows_incompatible>u.known_incompatible.issuers
  ||u.optimistic_issuers!==den.issuers-u.issuers_all_rows_incompatible||u.assumptions!==UPPER_ASSUMPTION
  ||u.can_reach95_under_known_scope!==(u.optimistic_issuers>=c.target95.issuers))refuse('UPPER_BOUND_INVALID',at);}
function coverage(c,ev,at,gen){exact(c,gen==='Q333'?[...COVERAGE_KEYS,'applicability_only_upper_bound']:COVERAGE_KEYS,at);const S=stagesOf(gen);
 const den=c.denominator;if(!isObj(den)||den.code_rows!==ev.code_rows||den.issuers!==ev.issuers)refuse('DENOMINATOR_MISMATCH',at+'.denominator');
 exact(c.stages,S.map(s=>s[0]),at+'.stages');for(const[k]of S)count(c.stages[k],at+'.stages.'+k,den);
 count(c.target95,at+'.target95',den);if(c.target95.code_rows<1||c.target95.issuers<1)refuse('COUNT_RANGE',at+'.target95');
 exact(c.gap95,['joint','total'],at+'.gap95');
 for(const s of['joint','total']){const g=count(c.gap95[s],at+'.gap95.'+s);
  for(const u of['code_rows','issuers'])if(g[u]!==Math.max(0,c.target95[u]-c.stages[s][u]))refuse('COUNT_ARITHMETIC',at+'.gap95.'+s+'.'+u);}
 if(c.causes_overlap!==true)refuse('CAUSES_NOT_OVERLAPPING',at+'.causes_overlap');
 if(!isObj(c.causes))refuse('TYPE',at+'.causes');for(const[k,v]of Object.entries(c.causes))count(v,at+'.causes.'+k,den);
 count(c.incomplete_unique,at+'.incomplete_unique',den);count(c.current_sample_barrier,at+'.current_sample_barrier',den);
 if(c.whole_market_denominator!==null||c.whole_market_coverage!==null)refuse('MARKET_NOT_NULL',at+'.whole_market_denominator');
 if(gen==='Q333')upperBound(c.applicability_only_upper_bound,c,at+'.applicability_only_upper_bound');}

function board(key,b,at){exact(b,BOARD_KEYS,at);const M=MODELS[key];
 if(b.model_id!==M.model_id)refuse('MODEL_MISMATCH',at+'.model_id');
 if(M.gen==='Q333'){if(b.model_version!==M.version||b.adapter_version!==M.adapter)refuse('MODEL_VERSION_UNKNOWN',at+'.adapter_version');
  if(b.configuration_hash!==M.configuration_hash)refuse('CONFIG_VERSION_MISMATCH',at+'.configuration_hash');}
 if(b.operating_adoption!=='NOT_ADOPTED')refuse('ADOPTION_CLAIMED',at+'.operating_adoption');
 if(b.performance_state!=='NOT_MEASURED')refuse('PERFORMANCE_CLAIMED',at+'.performance_state');
 if(!['RETROSPECTIVE_RECONSTRUCTION','AS_OF_CLASSIFICATION_NOT_SYSTEM_PIT_PROOF'].includes(b.classification_mode))refuse('CLASSIFICATION_MODE',at+'.classification_mode');
 for(const k of['cache_key','result_hash','configuration_hash'])if(!HEX.test(b[k]))refuse('HASH_INVALID',at+'.'+k);
 const ev=b.evaluation_population,ref=b.reference_population;population(ev,at+'.evaluation_population');
 population(ref,at+'.reference_population');for(const k of REF_EXTRA)if(!own(ref,k))refuse('KEY_MISSING',at+'.reference_population.'+k);
 if(ref.scope!=='FACTOR_INPUT_ELIGIBILITY_NOT_LISTING_OR_INVESTMENT_ELIGIBILITY')refuse('REFERENCE_SCOPE',at+'.reference_population.scope');
 if(ref.valuation_date!==ev.valuation_date||ref.as_of!==ev.as_of)refuse('REFERENCE_DATE_MISMATCH',at+'.reference_population');
 population(ref.candidate_population,at+'.reference_population.candidate_population');
 exact(b.bindings,['model_hash','evaluation','reference','code_hash','engine_version','adapter_version'],at+'.bindings');
 if(b.bindings.model_hash!==b.configuration_hash)refuse('BINDINGS_MISMATCH',at+'.bindings.model_hash');
 if(!same(b.bindings.evaluation,ev))refuse('BINDINGS_MISMATCH',at+'.bindings.evaluation');
 if(!same(b.bindings.reference,ref.candidate_population))refuse('BINDINGS_MISMATCH',at+'.bindings.reference');
 if(!HEX.test(b.bindings.code_hash)||b.bindings.engine_version!==b.engine_version||b.bindings.adapter_version!==b.adapter_version)refuse('BINDINGS_MISMATCH',at+'.bindings');
 coverage(b.coverage,ev,at+'.coverage',M.gen);}

// The manifest entry for a file; its own bytes must match (size and SHA-256).
async function bytesMatch(file,name,entries,sha256,at){
 if(!isObj(file)||!(file.bytes instanceof Uint8Array)||!isObj(file.body))refuse('BYTES_REQUIRED',at);
 const e=entries.get(name);if(!e)refuse('NOT_IN_MANIFEST',at);
 if(file.bytes.length!==e.size||(await sha256(file.bytes))!==e.sha256)refuse('BYTES_MISMATCH',at);return file.body;}

function manifestOf(m,scope){exact(m,['schema_version','data_kind','scope','files'],'manifest');
 if(m.schema_version!==SCHEMA.MANIFEST)refuse('SCHEMA','manifest.schema_version');if(m.scope!==scope)refuse('SCOPE_MISMATCH','manifest.scope');
 if(!['PRIVATE','SYNTHETIC'].includes(m.data_kind))refuse('DATA_KIND','manifest.data_kind');
 if(!Array.isArray(m.files)||!m.files.length||m.files.length>400)refuse('FILES_INVALID','manifest.files');const entries=new Map();
 m.files.forEach((f,i)=>{exact(f,['path','size','sha256'],'manifest.files['+i+']');
  if(!FILE.test(f.path)||entries.has(f.path)||!int(f.size)||f.size<1||f.size>MAX_BYTES||!HEX.test(f.sha256))refuse('FILES_INVALID','manifest.files['+i+']');entries.set(f.path,f);});
 if(!entries.has('summary.json')||!entries.has('index.json')||![...entries.keys()].some(p=>DETAIL_FILE.test(p)))refuse('FILES_INVALID','manifest.files');return entries;}

function anchorCheck(scope,ev,boards,anchor){const S=SCOPES[scope];
 if(!isObj(anchor)||!Array.isArray(anchor.scopes))refuse('ANCHOR_REQUIRED','$');const a=anchor.scopes.find(s=>s&&s.scope===S.anchor);if(!a)refuse('ANCHOR_REQUIRED','$');
 if(a.population_id!==ev.id||a.population_version!==ev.version||a.members_hash!==ev.members_hash||a.denominator!==ev.code_rows)refuse('DUAL_POPULATION_MISMATCH','evaluation_population');
 if(a.valuation_date!==ev.valuation_date)refuse('DUAL_DATE_MISMATCH','evaluation_population.valuation_date');
 for(const[k,b]of Object.entries(boards)){const input=S.input==='evaluation'?b.evaluation_population.input_hash:b.reference_population.input_hash;
  if(input!==a.input_hash)refuse('DUAL_INPUT_MISMATCH','boards.'+k+'.'+(S.input==='evaluation'?'evaluation_population':'reference_population')+'.input_hash');}}

function indexRows(x,summary,entries){exact(x,['schema_version','evaluation_population','rows'],'index');if(x.schema_version!==SCHEMA.INDEX)refuse('SCHEMA','index.schema_version');
 const keys=Object.keys(summary.boards),ev=summary.boards[keys[0]].evaluation_population;
 if(!same(x.evaluation_population,ev))refuse('INDEX_POPULATION_MISMATCH','index.evaluation_population');
 if(!Array.isArray(x.rows)||x.rows.length!==ev.code_rows)refuse('ROWS_INVALID','index.rows');
 const seen=new Set(),files=new Set();
 x.rows.forEach((r,i)=>{const at='index.rows['+i+']';exact(r,['company_id','issuer_id','security_id','boards','detail_file'],at);
  if(typeof r.company_id!=='string'||!r.company_id||seen.has(r.company_id))refuse('ROWS_INVALID',at+'.company_id');seen.add(r.company_id);
  if(!(r.issuer_id===null||typeof r.issuer_id==='string')||!(r.security_id===null||typeof r.security_id==='string'))refuse('TYPE',at);
  if(!DETAIL_FILE.test(r.detail_file)||!entries.has(r.detail_file))refuse('DETAIL_NOT_IN_MANIFEST',at+'.detail_file');files.add(r.detail_file);
  exact(r.boards,keys,at+'.boards');
  for(const k of keys){const b=r.boards[k],bt=at+'.boards.'+k;exact(b,HEAD_KEYS,bt);head(b,k,bt);}});
 for(const p of entries.keys())if(DETAIL_FILE.test(p)&&!files.has(p))refuse('DETAIL_UNREFERENCED','manifest.files.'+p);
 // The producer's stage counts are the rows as delivered: each axis, 세 축 동시 and the total, in code rows and issuers.
 for(const k of keys){const st=summary.boards[k].coverage.stages,has={Q:r=>r.axes.Q!==null,G:r=>r.axes.G!==null,V:r=>r.axes.V!==null,
   joint:r=>r.axes.Q!==null&&r.axes.G!==null&&r.axes.V!==null,total:r=>r.total!==null};
  if(MODELS[k].gen==='Q333')has.gate_known=r=>r.gate_status==='PASS'||r.gate_status==='VALUE_EXCLUDED';
  for(const[s,f]of Object.entries(has)){const hit=x.rows.filter(r=>f(r.boards[k]));
   if(hit.length!==st[s].code_rows||new Set(hit.filter(r=>r.issuer_id).map(r=>r.issuer_id)).size!==st[s].issuers)refuse('STAGE_COUNT_MISMATCH','summary.boards.'+k+'.coverage.stages.'+s);}}
 return x.rows;}

function head(b,k,at){exact(b.axes,['Q','G','V'],at+'.axes');for(const a of['Q','G','V'])if(!num(b.axes[a]))refuse('TYPE',at+'.axes.'+a);
 if(!num(b.total))refuse('TYPE',at+'.total');if(!int(b.rank_n)||b.rank_n<0)refuse('TYPE',at+'.rank_n');
 if(b.total===null&&b.rank!==null)refuse('RANK_WITHOUT_TOTAL',at+'.rank');
 if(b.rank!==null&&(!int(b.rank)||b.rank<1||b.rank>b.rank_n))refuse('RANK_RANGE',at+'.rank');
 if(typeof b.ranking_scope!=='string'||(MODELS[k].kind==='COMMON'?b.ranking_scope!=='COMMON':!/^SECTOR\|/.test(b.ranking_scope)))refuse('RANKING_SCOPE',at+'.ranking_scope');
 if(typeof b.status!=='string'||typeof b.gate_status!=='string')refuse('TYPE',at+'.status');
 if(b.gate_status==='UNKNOWN'&&b.total!==null)refuse('GATE_UNKNOWN_WITH_TOTAL',at+'.total');}

// manifest / summary / index: each {bytes, body}. opts {scope, anchor (IS2.referenceView.anchorOf of the checked bundle), sha256}.
async function checkDelivery(parts,opts){
 try{const o=opts||{};if(!own(SLOTS,o.scope))refuse('SCOPE_UNKNOWN','$');if(typeof o.sha256!=='function')refuse('HASH_UNAVAILABLE','$');
  const slot=o.scope,scope=SLOTS[slot].scope;
  const p=parts||{};if(!isObj(p.manifest)||!isObj(p.manifest.body))refuse('BYTES_REQUIRED','manifest');
  const entries=manifestOf(p.manifest.body,scope);
  const s=await bytesMatch(p.summary,'summary.json',entries,o.sha256,'summary');
  exact(s,['schema_version','visibility','boards'],'summary');if(s.schema_version!==SCHEMA.SUMMARY)refuse('SCHEMA','summary.schema_version');
  if(s.visibility!=='PRIVATE_RESEARCH')refuse('VISIBILITY','summary.visibility');
  const keys=isObj(s.boards)?Object.keys(s.boards):[];if(!keys.length||keys.some(k=>!own(MODELS,k)))refuse('BOARDS_INVALID','summary.boards');
  // One generation per delivery, and the slot's own: old and new candidates are never mixed in one bundle or read into the other's slot.
  const gens=new Set(keys.map(k=>MODELS[k].gen));if(gens.size!==1)refuse('MODEL_GENERATION_MIXED','summary.boards');
  if(!gens.has(SLOTS[slot].gen))refuse('MODEL_GENERATION_SLOT','summary.boards');
  for(const k of keys)board(k,s.boards[k],'summary.boards.'+k);
  const ev=s.boards[keys[0]].evaluation_population;
  for(const k of keys)if(!same(s.boards[k].evaluation_population,ev))refuse('EVALUATION_MISMATCH','summary.boards.'+k+'.evaluation_population');
  anchorCheck(scope,ev,s.boards,o.anchor);
  const x=await bytesMatch(p.index,'index.json',entries,o.sha256,'index');const rows=indexRows(x,s,entries);
  // held1057's evaluation input: attested only by a matching projection proof; a proof that does not match refuses the delivery.
  let input_check=INPUT_CHECK[SCOPES[scope].input];
  if(p.lineage!==undefined&&p.lineage!==null){if(SCOPES[scope].input!=='reference')refuse('LINEAGE_NOT_APPLICABLE','lineage');
   if(!isObj(p.lineage)||!isObj(p.lineage.body))refuse('LINEAGE_SCHEMA','lineage');lineageCheck(p.lineage.body,s.boards);input_check='EVALUATION_INPUT_PROJECTION_ATTESTED';}
  // operating504's reference input: anchored only by a matching independent anchor; one that does not match refuses the delivery.
  if(p.reference_anchor!==undefined&&p.reference_anchor!==null){if(SCOPES[scope].input!=='evaluation')refuse('REFERENCE_ANCHOR_NOT_APPLICABLE','reference_anchor');
   if(!isObj(p.reference_anchor)||!isObj(p.reference_anchor.body))refuse('REFERENCE_ANCHOR_SCHEMA','reference_anchor');
   referenceAnchorCheck(p.reference_anchor.body,scope,s.boards);input_check='EVALUATION_INPUT_MATCHED_REFERENCE_ANCHORED';}
  if(!(p.manifest.bytes instanceof Uint8Array))refuse('BYTES_REQUIRED','manifest');const manifest_sha256=await o.sha256(p.manifest.bytes);
  const value=freeze({scope,slot,gen:SLOTS[slot].gen,data_kind:p.manifest.body.data_kind,manifest_sha256,entries:Object.fromEntries(entries),summary:s,rows,models:keys,input_check});CHECKED.add(value);
  return{ok:true,value};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

// A 3/3/3 detail row (Codex qgv_333.fractions / run_board): recipe_state, and the producer's exact rational weights beside its
// display floats. Checked, never computed for display: every fraction is reduced; each side's axes sum to 1; every core factor gets
// exactly a third of its axis (role weight = its factor count, factor weight 1); nine core factors, three per axis, the selected
// ones; the unified candidates' registered nine factors at 1/3 per axis (1/9 each). A PREPARING recipe has no total.
const gcd=(a,b)=>{while(b){[a,b]=[b,a%b];}return a;};
function rational(x,at){exact(x,['numerator','denominator'],at);
 if(!int(x.numerator)||!int(x.denominator)||x.numerator<0||x.denominator<1||gcd(x.numerator,x.denominator)!==1)refuse('FRACTION_INVALID',at);return x;}
const ratEq=(a,b)=>a.numerator*b.denominator===b.numerator*a.denominator;
function sumIsOne(xs){let n=0,d=1;for(const x of xs){n=n*x.denominator+x.numerator*d;d*=x.denominator;const g=gcd(n,d)||1;n/=g;d/=g;}return n===d;}
const FRACTION_KEYS=Object.freeze(['nominal_axes','post_gate_axes','nominal_factors','post_gate_factors']);
function detail333(b,M,at,preset){
 if(!own(RECIPE_WORD,b.recipe_state))refuse('RECIPE_STATE',at+'.recipe_state');
 if(b.recipe_state==='PREPARING'&&(b.total!==null||b.rank!==null))refuse('PREPARING_WITH_TOTAL',at+'.total');
 const has=preset&&b.post_gate_axis_weights!==null;
 if(own(b,'weight_fractions')!==has)refuse(has?'WEIGHT_FRACTIONS_MISSING':'WEIGHT_FRACTIONS_UNEXPECTED',at+'.weight_fractions');
 if(!has)return;const w=b.weight_fractions,wt=at+'.weight_fractions';exact(w,FRACTION_KEYS,wt);
 const core=b.selected_variants;if(core.length!==9||new Set(core).size!==9)refuse('CORE_COUNT',at+'.selected_variants');
 for(const a of'QGV')if(core.filter(v=>EVIDENCE_333[v]&&EVIDENCE_333[v].axis===a).length!==3)refuse('CORE_COUNT',at+'.selected_variants.'+a);
 if(M.factors&&!same([...core].sort(),[...M.factors].sort()))refuse('CORE_NOT_REGISTERED',at+'.selected_variants');
 for(const side of['nominal','post_gate']){const ax=w[side+'_axes'],fs=w[side+'_factors'],st=wt+'.'+side;
  exact(ax,['Q','G','V'],st+'_axes');for(const a of'QGV')rational(ax[a],st+'_axes.'+a);if(!sumIsOne(['Q','G','V'].map(a=>ax[a])))refuse('WEIGHT_SUM',st+'_axes');
  exact(fs,core,st+'_factors');
  for(const v of core){const f=rational(fs[v],st+'_factors.'+v),A=ax[EVIDENCE_333[v].axis];
   if(f.numerator*3*A.denominator!==A.numerator*f.denominator)refuse('WEIGHT_NOT_THIRD',st+'_factors.'+v);}}
 if(M.factors)for(const a of'QGV')if(!ratEq(w.nominal_axes[a],{numerator:1,denominator:3}))refuse('WEIGHT_NOT_REGISTERED',wt+'.nominal_axes.'+a);}

// One detail file {bytes, body} for a checked delivery: every row of that file as the index heads it, factors without raw values.
async function checkDetail(file,name,delivery,sha256){
 try{const d=delivery;if(!d||!d.entries||!own(d.entries,name)||!DETAIL_FILE.test(name))refuse('NOT_IN_MANIFEST',name);
  const entries=new Map(Object.entries(d.entries)),x=await bytesMatch(file,name,entries,sha256,name);
  exact(x,['schema_version','rows'],name);if(x.schema_version!==SCHEMA.DETAIL)refuse('SCHEMA',name+'.schema_version');
  const want=d.rows.filter(r=>r.detail_file===name);
  if(!Array.isArray(x.rows)||x.rows.length!==want.length)refuse('DETAIL_ROWS_MISMATCH',name+'.rows');
  const out=new Map();
  x.rows.forEach((r,i)=>{const at=name+'.rows['+i+']',w=want[i];exact(r,['company_id','boards'],at);
   if(r.company_id!==w.company_id)refuse('DETAIL_ROWS_MISMATCH',at+'.company_id');exact(r.boards,d.models,at+'.boards');
   for(const k of d.models){const b=r.boards[k],bt=at+'.boards.'+k,q=MODELS[k].gen==='Q333';
    exact(b,q?[...DETAIL_KEYS,'recipe_state']:DETAIL_KEYS,bt,q?[...DETAIL_PRESET_FIELDS,'weight_fractions']:DETAIL_PRESET_FIELDS);
    const preset=b.status!=='MAPPING_UNRESOLVED';
    for(const f of DETAIL_PRESET_FIELDS)if(own(b,f)!==preset)refuse(preset?'PRESET_FIELD_MISSING':'PRESET_FIELD_UNEXPECTED',bt+'.'+f);
    if(q)detail333(b,MODELS[k],bt,preset);
    if(b.company_id!==w.company_id||b.issuer_id!==w.issuer_id||b.security_id!==w.security_id)refuse('DETAIL_IDENTITY',bt);
    for(const h of HEAD_KEYS)if(!same(b[h],w.boards[k][h]))refuse('DETAIL_MISMATCH',bt+'.'+h);
    if(!Array.isArray(b.selected_variants)||!isObj(b.factors)||b.selected_variants.some(v=>!own(b.factors,v)))refuse('FACTORS_INVALID',bt+'.selected_variants');
    for(const[v,f]of Object.entries(b.factors)){const ft=bt+'.factors.'+v;
     if(isObj(f)&&own(f,'raw_value'))refuse('RAW_VALUE_PRESENT',ft);exact(f,FACTOR_KEYS,ft);
     if((f.kind==='CORE')!==b.selected_variants.includes(v)||!['CORE','ADDITIONAL'].includes(f.kind))refuse('FACTOR_KIND',ft+'.kind');
     if(!num(f.score))refuse('TYPE',ft+'.score');if(!int(f.rank_n)||f.rank_n<0||!(f.valid_n===null||int(f.valid_n)))refuse('TYPE',ft+'.rank_n');
     if(f.score===null&&(f.rank!==null||f.decile!==null))refuse('RANK_WITHOUT_SCORE',ft+'.rank');
     if(f.rank!==null&&(!int(f.rank)||f.rank<1||f.rank>f.rank_n))refuse('RANK_RANGE',ft+'.rank');
     if(f.decile_status==='VALID'?!(int(f.decile)&&f.decile>=1&&f.decile<=10):f.decile!==null)refuse('DECILE_INVALID',ft+'.decile');}}
   out.set(r.company_id,r);});
  return{ok:true,value:freeze(out)};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

/* ---- words (counts and values as delivered; display rounding only) */
const fmt=v=>v===null||v===undefined?'미산출':(Math.round(v*10)/10).toFixed(1);
// An exact weight as the producer wrote it (numerator / denominator); never a rounded or re-derived share.
const frac=x=>x.numerator===0?'0':x.denominator===1?String(x.numerator):x.numerator+'/'+x.denominator;
const AXIS_WORD=Object.freeze({Q:'Q',G:'G',V:'V'});
const evidenceText=v=>{const e=EVIDENCE_333[v];return e?v+' · '+e.name+' · '+e.axis+' 축 '+e.role+' · 산식 '+e.formula+' · '+(PERIOD_WORD[e.period]||e.period)+' · '+DIRECTION_WORD[e.direction]
 +(e.status==='IMPLEMENTED'?'':' · 계산 정의 준비 중(PENDING_DEFINITION)'):v+' · 계약 요소표에 없음';};
const scopeWord=(s,sectorName)=>{if(s==='COMMON')return'평가 집단 전체';const[,sec,tpl]=s.split('|');
 return(sectorName?sectorName(sec):sec)+' · '+(tpl==='None'||!tpl?'회계모형 미확정':tpl);};
// Decile words (owner 2026-11-12). The producer's numeric decile 10 is the top band of the factor's own comparison group; the
// factor score already carries the factor's direction (a lower-is-better factor is scored 100 - score), so 상위 is the good side.
// The producer cuts bands by rank position (D10 and D1 hold floor(N/10) each, D9..D2 share the rest evenly, remainder to the
// higher bands; equal scores take positions by company_id), so a band name is never shown as an exact share.
const BAND=Object.freeze(Object.fromEntries(Array.from({length:10},(_,i)=>[10-i,'상위 '+i*10+'–'+(i+1)*10+'%'])));
const DECILE_RULE=Object.freeze(['분위 숫자 10 = 상위 0–10% · 1 = 상위 90–100% · 낮을수록 좋은 요소도 기존 평가 방향대로 좋은 쪽이 상위',
 '구간은 생산자가 순위 위치로 나눔 · 10·1 구간은 N/10(내림)개씩, 나머지 8구간이 남은 순위를 고르게 나눔 · 정확한 백분율 아님',
 '같은 점수도 회사 ID 순으로 순위가 정해져 서로 다른 구간에 들어갈 수 있음(저장된 분위 규칙 stored-evaluation-deciles/1 그대로 · 구간마다 실제 기업 수를 따로 보임)',
 '평가 유효 10개 미만이면 순위만 있고 분위 없음 · 점수 없는 요소는 순위·분위 없음 · 총점이 없어도 요소 분위는 보임',
 '통합(U1·U2)과 섹터(S1) 비교집단은 따로 · 섹터 분위를 합친 통합 분위 없음 · 추가 요소 분위는 핵심 점수에 더하지 않음',
 '구간 선택·필터는 보이는 기업만 고름 · 분위·순위·분모를 바꾸지 않음']);
const bandText=f=>f.decile!==null?BAND[f.decile]+'(분위 '+f.decile+')':'분위 없음('+(f.decile_status==='SAMPLE_LT_10'?'평가 유효 10개 미만':word(f.decile_status))+')';
const rankText=(b,sectorName)=>b.total===null?'총점 없음 · 순위 없음':b.rank+' / '+b.rank_n+' ('+scopeWord(b.ranking_scope,sectorName)+')';
const share=(c,d)=>String(c)+' / '+String(d);

function boardView(d,key){const b=d.summary.boards[key],M=MODELS[key],c=b.coverage,den=c.denominator,st=c.stages;
 return freeze({key,label:M.label,core:M.core,kind:KIND[M.kind],gen:M.gen,generation:GEN[M.gen],
  config:M.gen==='Q333'?'설정 '+M.config+' · 모형 '+M.model_id+' · 적용 '+M.adapter+' · 등록된 정확한 설정과 일치(설정 해시 '+M.configuration_hash.slice(0,12)+'…)':null,
  head:M.label+' · '+M.core+' · 연구 후보 · 운영 채택 안 됨 · 성과 미측정',
  states:[['보관 결과 조회','가능 · 목록표·요약·색인 검증됨'],['입력 연결',INPUT_WORD[d.input_check]],
   ['최종 총점',st.total.code_rows?'산출 '+share(st.total.code_rows,den.code_rows)+'코드 행':'미산출 · 이 모형의 총점 순위 없음'],
   ['화면 재계산','연결 안 됨 · 보관 결과만 보임'],
   ['저장·재현','생산자 저장본(설정·코드·두 입력 결합)으로만 · 다른 입력이면 거부 · 설정 '+b.configuration_hash.slice(0,12)+'… · 결과 '+b.result_hash.slice(0,12)+'…']],
  population:SCOPES[d.scope].label+' · '+b.evaluation_population.id+' · 코드 행 '+den.code_rows+' · 고유 발행사 '+den.issuers+' · 평가일 '+b.evaluation_population.valuation_date,
  reference:'참조집단 '+b.reference_population.id+' · 발행사 '+b.reference_population.issuers+' · 요소 입력 적격 연구 참조 · 상장·증권·투자 적격 아님 · 후보 원천 '+b.reference_population.candidate_population.code_rows+'행',
  classification:b.classification_mode==='RETROSPECTIVE_RECONSTRUCTION'?'분류: 평가일 뒤 지식으로 회고 재구성 · 당시 시스템 보유 증명 아님':'분류: 평가일 기준 분류 · 시스템 PIT 증명 아님',
  stages:stagesOf(M.gen).map(([k,l])=>freeze({key:k,label:l,text:'코드 행 '+share(st[k].code_rows,den.code_rows)+' · 발행사 '+share(st[k].issuers,den.issuers)})),
  target:'95% 목표 · 발행사 '+share(c.target95.issuers,den.issuers)+' · 코드 행 '+share(c.target95.code_rows,den.code_rows)
   +' · 세 축 동시 부족 발행사 '+c.gap95.joint.issuers+' · 최종 총점 부족 발행사 '+c.gap95.total.issuers,
  causes:Object.entries(c.causes).map(([k,v])=>word(k)+' ('+k+') · 발행사 '+v.issuers+' · 코드 행 '+v.code_rows),
  upper:c.applicability_only_upper_bound?'적용 범위만 본 상한(다른 입력·분류·비교 표본·관문 결손이 모두 해소된다는 가정 · 예측 아님) 발행사 '
   +share(c.applicability_only_upper_bound.optimistic_issuers,den.issuers)+' · 모든 행이 적용 부적합인 발행사 '+c.applicability_only_upper_bound.issuers_all_rows_incompatible
   +' · 95% 목표 발행사 '+c.target95.issuers+(c.applicability_only_upper_bound.can_reach95_under_known_scope?' · 이 가정에서도 도달 가능':' · 이 가정에서도 도달 불가'):null,
  incomplete:'총점 미산출 코드 행 '+c.incomplete_unique.code_rows+' · 비교 표본 부족이 걸린 행 '+c.current_sample_barrier.code_rows,
  market:'전체시장 분모·커버리지 미측정 · 관측 카탈로그는 상장 전체시장이 아님'});}

// 개별 요소 상위권 (Codex qgv-dual-factor-leaders/1, an optional companion of one checked delivery): its own manifest pins the
// delivery's manifest bytes (source_delivery_manifest_sha256); its index repeats each board's identity (model, configuration and
// result hashes, populations, bindings), which must be the checked delivery's own; each shard holds, per model × ranking scope ×
// factor, the first top_n of the STORED ranks (ranks 1..min(N, top_n), N = evaluation valid code rows) and the stored decile
// boundaries. Nothing is ranked, sorted, filled or merged here; the reference N is shown beside N, never instead of it.
const LEADERS=Object.freeze({MANIFEST:'qgv-dual-factor-leaders-manifest/1',INDEX:'qgv-dual-factor-leaders/1',DETAIL:'qgv-dual-factor-leaders-detail/1'});
const LEADER_SHARD=/^factor-leaders-\d{3}\.json$/;
const LEADER_BOARD_KEYS=['model_id','model_version','configuration_hash','result_hash','evaluation_population','reference_population','bindings'];
const LEADER_GROUP_KEYS=['group_id','board','ranking_scope','variant_id','evaluation_valid_n','reference_valid_n','file'];
const LEADER_DETAIL_KEYS=['group_id','board','ranking_scope','variant_id','evaluation_rows_in_scope','evaluation_valid_n','reference_valid_n','rank_unit','top_n','leaders','decile_status','decile_boundaries'];
const LEADER_KEYS=['company_id','issuer_id','security_id','score','rank','rank_n','decile','kind'];
const BOUNDARY_KEYS=['decile','count','first_rank','last_rank','first_score','last_score'];
const LEADERS_CHECKED=new WeakSet();
async function checkLeaders(parts,delivery,sha256){
 try{const d=delivery;if(!d||!CHECKED.has(d))refuse('DELIVERY_NOT_CHECKED','$');if(typeof sha256!=='function')refuse('HASH_UNAVAILABLE','$');
  const p=parts||{};if(!isObj(p.manifest)||!isObj(p.manifest.body))refuse('BYTES_REQUIRED','leaders_manifest');const m=p.manifest.body;
  exact(m,['schema_version','scope','data_kind','source_delivery_manifest_sha256','files'],'leaders_manifest');
  if(m.schema_version!==LEADERS.MANIFEST)refuse('SCHEMA','leaders_manifest.schema_version');
  if(m.scope!==d.scope||m.data_kind!==d.data_kind)refuse('SCOPE_MISMATCH','leaders_manifest.scope');
  if(m.source_delivery_manifest_sha256!==d.manifest_sha256)refuse('LEADERS_SOURCE_MISMATCH','leaders_manifest.source_delivery_manifest_sha256');
  if(!Array.isArray(m.files)||!m.files.length||m.files.length>400)refuse('FILES_INVALID','leaders_manifest.files');const entries=new Map();
  m.files.forEach((f,i)=>{exact(f,['path','size','sha256'],'leaders_manifest.files['+i+']');
   if(!(f.path==='factor-leaders.json'||LEADER_SHARD.test(f.path))||entries.has(f.path)||!int(f.size)||f.size<1||f.size>MAX_BYTES||!HEX.test(f.sha256))refuse('FILES_INVALID','leaders_manifest.files['+i+']');entries.set(f.path,f);});
  const x=await bytesMatch(p.index,'factor-leaders.json',entries,sha256,'leaders_index');
  exact(x,['schema_version','scope','data_kind','source_delivery_manifest_sha256','projection_only','rank_recalculated','whole_market_denominator','whole_market_coverage','boards','groups','optional_detail_fields'],'leaders_index');
  if(x.schema_version!==LEADERS.INDEX)refuse('SCHEMA','leaders_index.schema_version');
  if(x.scope!==m.scope||x.data_kind!==m.data_kind||x.source_delivery_manifest_sha256!==m.source_delivery_manifest_sha256)refuse('SCOPE_MISMATCH','leaders_index');
  if(x.projection_only!==true||x.rank_recalculated!==false||x.whole_market_denominator!==null||x.whole_market_coverage!==null)refuse('NOT_PROJECTION','leaders_index');
  exact(x.boards,d.models,'leaders_index.boards');
  for(const k of d.models){exact(x.boards[k],LEADER_BOARD_KEYS,'leaders_index.boards.'+k);
   for(const f of LEADER_BOARD_KEYS)if(!same(x.boards[k][f],d.summary.boards[k][f]))refuse('LEADERS_BOARD_MISMATCH','leaders_index.boards.'+k+'.'+f);}
  if(!Array.isArray(x.groups))refuse('GROUPS_INVALID','leaders_index.groups');
  const groups=new Map(),files=new Set(),rows=d.summary.boards[d.models[0]].evaluation_population.code_rows;
  x.groups.forEach((g,i)=>{const at='leaders_index.groups['+i+']';exact(g,LEADER_GROUP_KEYS,at);
   if(!own(MODELS,g.board)||!d.models.includes(g.board))refuse('GROUPS_INVALID',at+'.board');
   if(typeof g.ranking_scope!=='string'||(MODELS[g.board].kind==='COMMON'?g.ranking_scope!=='COMMON':!/^SECTOR\|/.test(g.ranking_scope)))refuse('RANKING_SCOPE',at+'.ranking_scope');
   if(typeof g.variant_id!=='string'||!g.variant_id||g.group_id!==[g.board,g.ranking_scope,g.variant_id].join('|')||groups.has(g.group_id))refuse('GROUPS_INVALID',at+'.group_id');
   if(!int(g.evaluation_valid_n)||g.evaluation_valid_n<0||g.evaluation_valid_n>rows||!int(g.reference_valid_n)||g.reference_valid_n<0)refuse('TYPE',at+'.evaluation_valid_n');
   if(!LEADER_SHARD.test(g.file)||!entries.has(g.file))refuse('DETAIL_NOT_IN_MANIFEST',at+'.file');files.add(g.file);groups.set(g.group_id,g);});
  for(const f of entries.keys())if(LEADER_SHARD.test(f)&&!files.has(f))refuse('DETAIL_UNREFERENCED','leaders_manifest.files.'+f);
  if(!(p.manifest.bytes instanceof Uint8Array))refuse('BYTES_REQUIRED','leaders_manifest');const manifest_sha256=await sha256(p.manifest.bytes);
  const value=freeze({scope:d.scope,delivery:d,manifest_sha256,entries:Object.fromEntries(entries),groups:[...groups.values()]});LEADERS_CHECKED.add(value);
  return{ok:true,value};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

// One leaders shard {bytes, body} of checked leaders: every group the index files there, each as indexed; the leaders are exactly
// the stored ranks 1..min(N, top_n) of the evaluation valid code rows; the decile state follows N (0: NO_VALID_SCORE, below 10:
// SAMPLE_LT_10 without boundaries, else VALID with the ten stored boundaries, D10 = ranks 1..floor(N/10)); no raw value.
async function checkLeaderShard(file,name,leaders,sha256){
 try{const L=leaders;if(!L||!LEADERS_CHECKED.has(L)||!own(L.entries,name)||!LEADER_SHARD.test(name))refuse('NOT_IN_MANIFEST',name);
  const x=await bytesMatch(file,name,new Map(Object.entries(L.entries)),sha256,name);
  exact(x,['schema_version','groups'],name);if(x.schema_version!==LEADERS.DETAIL)refuse('SCHEMA',name+'.schema_version');
  const want=new Map(L.groups.filter(g=>g.file===name).map(g=>[g.group_id,g]));
  if(!Array.isArray(x.groups)||x.groups.length!==want.size)refuse('GROUPS_MISMATCH',name+'.groups');const out=new Map();
  x.groups.forEach((g,i)=>{const at=name+'.groups['+i+']';exact(g,LEADER_DETAIL_KEYS,at);const w=want.get(g.group_id);
   if(!w||out.has(g.group_id))refuse('GROUPS_MISMATCH',at+'.group_id');
   for(const f of['board','ranking_scope','variant_id','evaluation_valid_n','reference_valid_n'])if(g[f]!==w[f])refuse('GROUP_CONTEXT',at+'.'+f);
   const n=g.evaluation_valid_n;
   if(g.rank_unit!=='EVALUATION_CODE_ROW'||!int(g.top_n)||g.top_n<1||!int(g.evaluation_rows_in_scope)||g.evaluation_rows_in_scope<n)refuse('TYPE',at+'.rank_unit');
   if(!Array.isArray(g.leaders)||g.leaders.length!==Math.min(n,g.top_n))refuse('LEADER_PREFIX',at+'.leaders');
   const status=n===0?'NO_VALID_SCORE':n<10?'SAMPLE_LT_10':'VALID';if(g.decile_status!==status)refuse('DECILE_STATUS',at+'.decile_status');
   g.leaders.forEach((r,j)=>{const lt=at+'.leaders['+j+']';if(isObj(r)&&own(r,'raw_value'))refuse('RAW_VALUE_PRESENT',lt);exact(r,LEADER_KEYS,lt);
    if(typeof r.company_id!=='string'||!r.company_id||r.rank!==j+1||r.rank_n!==n)refuse('LEADER_PREFIX',lt);
    if(typeof r.score!=='number'||!Number.isFinite(r.score)||!['CORE','ADDITIONAL'].includes(r.kind))refuse('TYPE',lt);
    if(status==='VALID'?!(int(r.decile)&&r.decile>=1&&r.decile<=10):r.decile!==null)refuse('DECILE_STATUS',lt+'.decile');});
   if(!Array.isArray(g.decile_boundaries))refuse('TYPE',at+'.decile_boundaries');
   if(status!=='VALID'){if(g.decile_boundaries.length)refuse('DECILE_STATUS',at+'.decile_boundaries');}
   else{if(g.decile_boundaries.length!==10)refuse('DECILE_STATUS',at+'.decile_boundaries');
    g.decile_boundaries.forEach((b,j)=>{exact(b,BOUNDARY_KEYS,at+'.decile_boundaries['+j+']');if(b.decile!==10-j||!int(b.count)||!int(b.first_rank)||!int(b.last_rank))refuse('DECILE_STATUS',at+'.decile_boundaries['+j+']');});
    const top=g.decile_boundaries[0];if(top.count!==Math.floor(n/10)||top.first_rank!==1||top.last_rank!==top.count)refuse('TOP_DECILE_BOUNDARY',at+'.decile_boundaries[0]');}
   out.set(g.group_id,freeze(g));});
  return{ok:true,value:out};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

// The optional selection contract of checked leaders (Codex qgv-dual-factor-leaders-selection/1, #437 6795150039): its manifest pins
// the leaders manifest bytes; per group it states the top-N prefix and the STORED top 10 % (k = floor(N/10), N < 10 not calculated)
// apart, and whether the top-N prefix holds the whole D10. Checked here only against the contract rules and the leaders (same groups,
// same contexts); nothing is ranked or counted from rows. Against a loaded shard, selectionMatchesShard compares the two.
const SELECTION=Object.freeze({MANIFEST:'qgv-dual-factor-leaders-selection-manifest/1',BODY:'qgv-dual-factor-leaders-selection/1'});
const SELECTION_KEYS=['schema_version','scope','data_kind','source_leaders_manifest_sha256','source_delivery_manifest_sha256','boards','groups','rank_unit','tie_policy',
 'top_decile_policy','additional_factor_score_contribution','rank_recalculated','new_score_calculations','whole_market_denominator','whole_market_coverage'];
const SELECTION_CHECKED=new WeakSet();
async function checkSelection(parts,leaders,sha256){
 try{const L=leaders;if(!L||!LEADERS_CHECKED.has(L))refuse('LEADERS_NOT_CHECKED','$');const d=L.delivery,p=parts||{};
  if(!isObj(p.manifest)||!isObj(p.manifest.body))refuse('BYTES_REQUIRED','selection_manifest');const m=p.manifest.body;
  exact(m,['schema_version','scope','data_kind','source_leaders_manifest_sha256','files'],'selection_manifest');
  if(m.schema_version!==SELECTION.MANIFEST)refuse('SCHEMA','selection_manifest.schema_version');
  if(m.scope!==L.scope||m.data_kind!==d.data_kind)refuse('SCOPE_MISMATCH','selection_manifest.scope');
  if(m.source_leaders_manifest_sha256!==L.manifest_sha256)refuse('SELECTION_SOURCE_MISMATCH','selection_manifest.source_leaders_manifest_sha256');
  if(!Array.isArray(m.files)||m.files.length!==1)refuse('FILES_INVALID','selection_manifest.files');const f=m.files[0];exact(f,['path','size','sha256'],'selection_manifest.files[0]');
  if(f.path!=='factor-leaders-selection.json'||!int(f.size)||f.size<1||f.size>MAX_BYTES||!HEX.test(f.sha256))refuse('FILES_INVALID','selection_manifest.files[0]');
  const x=await bytesMatch(p.body,f.path,new Map([[f.path,f]]),sha256,'selection');exact(x,SELECTION_KEYS,'selection');
  if(x.schema_version!==SELECTION.BODY)refuse('SCHEMA','selection.schema_version');
  if(x.scope!==m.scope||x.data_kind!==m.data_kind||x.source_leaders_manifest_sha256!==L.manifest_sha256||x.source_delivery_manifest_sha256!==d.manifest_sha256)refuse('SELECTION_SOURCE_MISMATCH','selection');
  if(x.rank_unit!=='EVALUATION_CODE_ROW'||x.rank_recalculated!==false||x.new_score_calculations!==0||x.additional_factor_score_contribution!==0||x.whole_market_denominator!==null||x.whole_market_coverage!==null)refuse('NOT_PROJECTION','selection');
  exact(x.boards,d.models,'selection.boards');
  for(const k of d.models){for(const fld of LEADER_BOARD_KEYS)if(!same(x.boards[k][fld],d.summary.boards[k][fld]))refuse('LEADERS_BOARD_MISMATCH','selection.boards.'+k+'.'+fld);}
  if(!Array.isArray(x.groups)||x.groups.length!==L.groups.length)refuse('GROUPS_MISMATCH','selection.groups');
  const want=new Map(L.groups.map(g=>[g.group_id,g])),out=new Map();
  x.groups.forEach((g,i)=>{const at='selection.groups['+i+']';exact(g,[...LEADER_GROUP_KEYS,'top_n','top_10_percent'],at);const w=want.get(g.group_id);
   if(!w||out.has(g.group_id))refuse('GROUPS_MISMATCH',at+'.group_id');for(const fld of LEADER_GROUP_KEYS)if(g[fld]!==w[fld])refuse('GROUP_CONTEXT',at+'.'+fld);
   exact(g.top_n,['requested_n','returned_n','complete'],at+'.top_n');const t=g.top_10_percent,n=g.evaluation_valid_n;
   exact(t,['status','k','first_rank','last_rank','returned_in_top_n','complete_in_top_n'],at+'.top_10_percent');
   if(!int(g.top_n.requested_n)||g.top_n.requested_n<1||g.top_n.returned_n!==Math.min(n,g.top_n.requested_n)||g.top_n.complete!==true)refuse('TOP_N',at+'.top_n');
   const status=n===0?'NO_VALID_SCORE':n<10?'SAMPLE_LT_10':'VALID',k=Math.floor(n/10);
   if(t.status!==status)refuse('DECILE_STATUS',at+'.top_10_percent.status');
   if(status==='VALID'?(t.k!==k||t.first_rank!==1||t.last_rank!==k||t.returned_in_top_n!==Math.min(k,g.top_n.returned_n)||t.complete_in_top_n!==(g.top_n.returned_n>=k))
     :(t.k!==null||t.first_rank!==null||t.last_rank!==null||t.returned_in_top_n!==0||t.complete_in_top_n!==false))refuse('TOP_DECILE_BOUNDARY',at+'.top_10_percent');
   out.set(g.group_id,freeze(g));});
  const value=freeze({leaders:L,groups:out});SELECTION_CHECKED.add(value);return{ok:true,value};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}
// A checked selection entry and the same group's checked shard tell the same: the prefix length and the stored D10 size.
function selectionMatchesShard(sel,g){if(!sel||!g)return false;const t=sel.top_10_percent;
 return sel.top_n.returned_n===g.leaders.length&&(t.status==='VALID'?g.decile_status==='VALID'&&g.decile_boundaries[0].count===t.k:g.decile_status===t.status);}
// Display of checked leaders: groups of one model (index order, the producer's), and one group's stored ranks as delivered.
function leaderGroups(L,key){return L.groups.filter(g=>g.board===key);}
function leaderView(g,{sectorName,selection}={}){const n=g.evaluation_valid_n,top=g.decile_boundaries[0];
 const scopeWord=g.ranking_scope==='COMMON'?'공통 순위':'섹터 순위 · '+g.ranking_scope.split('|').slice(1).map((x,i)=>i===0&&sectorName?sectorName(x):x).join(' · ');
 const d10=g.decile_status==='VALID'?'저장된 '+BAND[10]+' 구간 '+top.count+'개(순위 1–'+top.last_rank+') · 이 목록 '+g.leaders.length+'개'+(g.leaders.length>=top.count?' · 이 구간 전부 포함':' · 이 구간 일부만(상위 '+g.top_n+'개 표시 한도)')
  :g.decile_status==='SAMPLE_LT_10'?'평가 유효 '+n+'개 < 10 · 분위 계산 안 함':'유효 점수 없음 · 순위 없음';
 const inPreview=d=>g.leaders.filter(r=>r.decile===d).length;
 // All ten bands from the stored boundaries (count, rank and score range); members only as far as this preview reaches.
 const bands=g.decile_status==='VALID'?g.decile_boundaries.map(b=>{const k=inPreview(b.decile);return freeze({decile:b.decile,band:BAND[b.decile],count:b.count,
  ranks:b.count?'순위 '+b.first_rank+'–'+b.last_rank+' / '+n:'해당 순위 없음',scores:b.count?'요소 점수 '+fmt(b.first_score)+'–'+fmt(b.last_score):'—',
  shown:k,complete:k===b.count,members:!b.count?'빈 구간 · 평가 유효 N이 작아 이 구간에 놓인 순위 없음':k===b.count?'구성 기업 '+b.count+'개 전부 이 미리보기에 있음':'구성 기업 '+b.count+'개 중 이 미리보기에 '+k+'개 · 전체 구성 목록은 분할 전달 대기'});}):[];
 const sel=selection?(selectionMatchesShard(selection,g)?'생산자 선택 계약과 대조됨(D10 '+(selection.top_10_percent.complete_in_top_n?'전부 포함':selection.top_10_percent.status==='VALID'?'일부만':'해당 없음')+')':'생산자 선택 계약과 다름 · 이 목록 쓰지 않음'):'생산자 선택 계약 없음(저장된 경계로만 표시)';
 return freeze({head:g.variant_id+' · '+scopeWord,
  counts:'평가 유효 코드 행 '+n+' / 범위 내 '+g.evaluation_rows_in_scope+' · 참조 유효 '+g.reference_valid_n+'(순위 분모 아님)',d10,sel,bands,
  preview:'상위 '+g.top_n+'개 미리보기 · 10분위 전체 조회가 아님 · 10개 구간의 개수·순위 범위는 저장된 경계 그대로',selectionOk:!selection||selectionMatchesShard(selection,g),
  rows:g.leaders.map(r=>freeze({d:r.decile,rank:r.rank+' / '+r.rank_n,company_id:r.company_id,score:r.score.toFixed(1),decile:r.decile===null?'분위 없음':BAND[r.decile],kind:r.kind==='CORE'?'핵심':'추가(점수 기여 0)'}))});}

// 요소 10분위 전체 조회 (owner 2026-11-12; Codex qgv-dual-factor-distribution/1, #529 430f89ca FACTOR_DISTRIBUTION.md d6abe24b…):
// an optional companion of one checked delivery, read on its own route. The index repeats each board's identity, which must be the
// checked delivery's own (model, configuration and result hashes, populations, bindings), and lists every model × ranking scope ×
// factor group with its ten stored band counts and the unavailable count; each part holds ALL evaluation rows of a group (scored or
// not). The reader checks bytes, completeness and agreement (counts, ranks, bands) and keeps the rows as delivered: nothing is
// ranked, binned, filled or merged here. The display policy is the producer's and explicit; the reference-score candidate is
// research only and is refused on private data until the owner confirms it.
const DIST=Object.freeze({MANIFEST:'qgv-dual-factor-distribution-manifest/1',INDEX:'qgv-dual-factor-distribution/1',PART:'qgv-dual-factor-distribution-part/1',
 STORED:'stored-evaluation-deciles/1',REFERENCE:'reference-score-deciles/1'});
const DIST_PART=/^distribution-\d{3}\.json$/;
const DIST_INDEX_KEYS=['schema_version','scope','data_kind','display_policy','policy_state','bands','boards','companies','groups','rank_policy','minimum_reference_score_n',
 'minimum_stored_evaluation_decile_n','complete_evaluation_rows','filter_changes_population','rank_recalculated','additional_factor_score_contribution',
 'new_score_calculations','whole_market_denominator','whole_market_coverage'];
const DIST_BOARD_KEYS=['model_id','model_version','evaluation_population','reference_population','bindings','result_hash','normalization_version','engine_version',
 'adapter_version','configuration_hash','source_result_sha256'];
const DIST_GROUP_KEYS=['group_id','board','ranking_scope','variant_id','raw_direction','score_direction','evaluation_rows_in_scope','evaluation_valid_n','reference_valid_n',
 'comparison_group','reference_members_hash','reference_issuer_members_hash','bins','unavailable_count','unavailable_reasons','legacy_tie_splits','files'];
const DIST_ROW_KEYS=['company_id','score','rank','rank_n','stored_decile','stored_decile_status','decile','decile_status','score_status','raw_status','kind'];
const DIST_CHECKED=new WeakSet();
const isScore=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=100;
// The delivery context a distribution is checked against: a checked delivery (the screens), or — tests of Codex's own synthetic cases
// only — the synthetic files' own boards and companies (bound:false; never held in RAM, never shown by the screens).
function deliveryContext(d){return{bound:true,delivery:d,scope:d.scope,data_kind:d.data_kind,models:d.models,boards:d.summary.boards,
 rows:d.rows.map(r=>({company_id:r.company_id,issuer_id:r.issuer_id,security_id:r.security_id,scopes:Object.fromEntries(d.models.map(k=>[k,r.boards[k].ranking_scope]))}))};}
async function checkDistribution(parts,delivery,sha256){if(!delivery||!CHECKED.has(delivery))return{ok:false,code:'DELIVERY_NOT_CHECKED',path:'$'};
 return checkDist(parts,deliveryContext(delivery),sha256);}
async function checkDistributionSynthetic(parts,sha256,{scopes}={}){const x=parts&&parts.index&&parts.index.body;
 if(!isObj(x)||x.data_kind!=='SYNTHETIC'||!isObj(x.boards)||!Array.isArray(x.companies)||!isObj(scopes))return{ok:false,code:'SYNTHETIC_ONLY',path:'dist_index'};
 return checkDist(parts,{bound:false,delivery:null,scope:x.scope,data_kind:'SYNTHETIC',models:Object.keys(x.boards),boards:x.boards,
  rows:x.companies.map(c=>({...c,scopes:scopes[c.company_id]||{}}))},sha256);}
async function checkDist(parts,ctx,sha256){
 try{const d=ctx;if(typeof sha256!=='function')refuse('HASH_UNAVAILABLE','$');
  const p=parts||{};if(!isObj(p.manifest)||!isObj(p.manifest.body)||!(p.manifest.bytes instanceof Uint8Array))refuse('BYTES_REQUIRED','dist_manifest');const m=p.manifest.body;
  exact(m,['schema_version','scope','data_kind','display_policy','source_results','files'],'dist_manifest');
  if(m.schema_version!==DIST.MANIFEST)refuse('SCHEMA','dist_manifest.schema_version');
  if(m.display_policy!==DIST.STORED&&m.display_policy!==DIST.REFERENCE)refuse('DISPLAY_POLICY','dist_manifest.display_policy');
  if(m.display_policy===DIST.REFERENCE&&m.data_kind!=='SYNTHETIC')refuse('POLICY_NOT_CONFIRMED','dist_manifest.display_policy');
  if(m.scope!==d.scope||m.data_kind!==d.data_kind)refuse('SCOPE_MISMATCH','dist_manifest.scope');
  if(!Array.isArray(m.files)||!m.files.length||m.files.length>400)refuse('FILES_INVALID','dist_manifest.files');const entries=new Map();
  m.files.forEach((f,i)=>{exact(f,['path','size','sha256'],'dist_manifest.files['+i+']');
   if(!(f.path==='distribution-index.json'||DIST_PART.test(f.path))||entries.has(f.path)||!int(f.size)||f.size<1||f.size>MAX_BYTES||!HEX.test(f.sha256))refuse('FILES_INVALID','dist_manifest.files['+i+']');entries.set(f.path,f);});
  const x=await bytesMatch(p.index,'distribution-index.json',entries,sha256,'dist_index');exact(x,DIST_INDEX_KEYS,'dist_index');
  if(x.schema_version!==DIST.INDEX)refuse('SCHEMA','dist_index.schema_version');
  if(x.scope!==m.scope||x.data_kind!==m.data_kind||x.display_policy!==m.display_policy)refuse('SCOPE_MISMATCH','dist_index');
  if(x.policy_state!==(x.display_policy===DIST.STORED?'EXISTING_RULE':'RESEARCH_DISPLAY_CANDIDATE'))refuse('DISPLAY_POLICY','dist_index.policy_state');
  if(x.rank_policy!=='UNROUNDED_FACTOR_SCORE_DESC_COMPANY_ID_ASC_ORDINAL'||x.minimum_reference_score_n!==20||x.minimum_stored_evaluation_decile_n!==10)refuse('RULE_MISMATCH','dist_index.rank_policy');
  if(x.complete_evaluation_rows!==true||x.filter_changes_population!==false||x.rank_recalculated!==false||x.additional_factor_score_contribution!==0
   ||x.new_score_calculations!==0||x.whole_market_denominator!==null||x.whole_market_coverage!==null)refuse('NOT_PROJECTION','dist_index');
  if(!Array.isArray(x.bands)||x.bands.length!==10)refuse('BANDS_INVALID','dist_index.bands');
  x.bands.forEach((b,j)=>{exact(b,['decile','top_percent_from','top_percent_to','label'],'dist_index.bands['+j+']');
   if(b.decile!==10-j||b.top_percent_from!==j*10||b.top_percent_to!==j*10+10||b.label!==BAND[b.decile])refuse('BANDS_INVALID','dist_index.bands['+j+']');});
  if(!isObj(x.boards)||!Object.keys(x.boards).length)refuse('BOARDS_INVALID','dist_index.boards');exact(m.source_results,Object.keys(x.boards),'dist_manifest.source_results');
  for(const[k,b]of Object.entries(x.boards)){const at='dist_index.boards.'+k;if(!d.models.includes(k))refuse('BOARDS_INVALID',at);exact(b,DIST_BOARD_KEYS,at);
   for(const f of DIST_BOARD_KEYS.filter(f=>f!=='source_result_sha256'))if(!same(b[f],d.boards[k][f]))refuse('DIST_BOARD_MISMATCH',at+'.'+f);
   exact(m.source_results[k],['result_hash','sha256'],'dist_manifest.source_results.'+k);
   if(m.source_results[k].result_hash!==b.result_hash||m.source_results[k].sha256!==b.source_result_sha256||!HEX.test(b.source_result_sha256))refuse('DIST_BOARD_MISMATCH','dist_manifest.source_results.'+k);}
  // The companies are the delivery's evaluation code rows, with their identity (a null security id stays null).
  if(!Array.isArray(x.companies)||x.companies.length!==d.rows.length)refuse('COMPANIES_MISMATCH','dist_index.companies');
  const rowOf=new Map(d.rows.map(r=>[r.company_id,r])),seen=new Set();
  x.companies.forEach((c,i)=>{exact(c,['company_id','issuer_id','security_id'],'dist_index.companies['+i+']');const r=rowOf.get(c.company_id);
   if(!r||seen.has(c.company_id)||c.issuer_id!==r.issuer_id||c.security_id!==r.security_id)refuse('COMPANIES_MISMATCH','dist_index.companies['+i+']');seen.add(c.company_id);});
  if(!Array.isArray(x.groups))refuse('GROUPS_INVALID','dist_index.groups');const groups=new Map(),files=new Set();
  x.groups.forEach((g,i)=>{const at='dist_index.groups['+i+']';exact(g,DIST_GROUP_KEYS,at);
   if(!own(x.boards,g.board))refuse('GROUPS_INVALID',at+'.board');
   if(typeof g.ranking_scope!=='string'||(MODELS[g.board].kind==='COMMON'?g.ranking_scope!=='COMMON':!/^SECTOR\|/.test(g.ranking_scope)))refuse('RANKING_SCOPE',at+'.ranking_scope');
   if(typeof g.variant_id!=='string'||!g.variant_id||g.group_id!==[g.board,g.ranking_scope,g.variant_id].join('|')||groups.has(g.group_id))refuse('GROUPS_INVALID',at+'.group_id');
   if((g.raw_direction!=='HIGHER'&&g.raw_direction!=='LOWER')||g.score_direction!=='HIGHER_IS_BETTER')refuse('DIRECTION',at+'.score_direction');
   const n=g.evaluation_valid_n,rows=g.evaluation_rows_in_scope;
   if(!int(rows)||rows<1||rows>d.rows.length||!int(n)||n<0||n>rows||!int(g.reference_valid_n)||g.reference_valid_n<0)refuse('TYPE',at+'.evaluation_valid_n');
   exact(g.comparison_group,['role','unit','n','members_hash'],at+'.comparison_group');const cg=g.comparison_group;
   if(x.display_policy===DIST.STORED?(cg.role!=='EVALUATION_VALID'||cg.unit!=='EVALUATION_CODE_ROW'||cg.n!==n||!HEX.test(cg.members_hash))
    :(cg.role!=='FACTOR_REFERENCE'||cg.unit!=='REPRESENTATIVE_ISSUER'||cg.n!==g.reference_valid_n))refuse('COMPARISON_GROUP',at+'.comparison_group');
   if(!Array.isArray(g.bins)||g.bins.length!==10)refuse('BINS_INVALID',at+'.bins');let sum=0;
   g.bins.forEach((b,j)=>{exact(b,['decile','count'],at+'.bins['+j+']');if(b.decile!==10-j||!int(b.count)||b.count<0)refuse('BINS_INVALID',at+'.bins['+j+']');sum+=b.count;});
   if(!isObj(g.unavailable_reasons)||!int(g.unavailable_count)||Object.values(g.unavailable_reasons).some(v=>!int(v)||v<1)
    ||Object.values(g.unavailable_reasons).reduce((a,v)=>a+v,0)!==g.unavailable_count||sum+g.unavailable_count!==rows)refuse('BINS_INVALID',at+'.unavailable_count');
   // The stored policy: ten bands only from N 10, holding every valid row; below 10 the valid rows are unavailable (SAMPLE_LT_10).
   if(x.display_policy===DIST.STORED&&(n>=10?sum!==n:sum!==0))refuse('BINS_INVALID',at+'.bins');
   if(!Array.isArray(g.legacy_tie_splits))refuse('TYPE',at+'.legacy_tie_splits');
   g.legacy_tie_splits.forEach((t,j)=>exact(t,['score','last_rank','next_rank','from_decile','to_decile'],at+'.legacy_tie_splits['+j+']'));
   if(!Array.isArray(g.files)||!g.files.length||new Set(g.files).size!==g.files.length||g.files.some(f=>!DIST_PART.test(f)||!entries.has(f)))refuse('PART_NOT_IN_MANIFEST',at+'.files');
   g.files.forEach(f=>files.add(f));groups.set(g.group_id,g);});
  for(const f of entries.keys())if(DIST_PART.test(f)&&!files.has(f))refuse('PART_UNREFERENCED','dist_manifest.files.'+f);
  const manifest_sha256=await sha256(p.manifest.bytes);
  const value=freeze({scope:d.scope,bound:d.bound,delivery:d.delivery,manifest_sha256,display_policy:x.display_policy,policy_state:x.policy_state,data_kind:x.data_kind,
   entries:Object.fromEntries(entries),boards:x.boards,groups:[...groups.values()],scopeOf:Object.fromEntries(d.rows.map(r=>[r.company_id,r.scopes]))});DIST_CHECKED.add(value);
  return{ok:true,value};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

// One distribution part {bytes, body} of a checked distribution: its parts name only groups the index files there; the rows of each
// are kept (a group may continue in another part). Returns Map group_id → rows of this part.
async function checkDistributionPart(file,name,D,sha256){
 try{if(!D||!DIST_CHECKED.has(D)||!own(D.entries,name)||!DIST_PART.test(name))refuse('NOT_IN_MANIFEST',name);
  const x=await bytesMatch(file,name,new Map(Object.entries(D.entries)),sha256,name);
  exact(x,['schema_version','parts'],name);if(x.schema_version!==DIST.PART)refuse('SCHEMA',name+'.schema_version');
  if(!Array.isArray(x.parts)||!x.parts.length)refuse('PARTS_INVALID',name+'.parts');const byId=new Map(D.groups.map(g=>[g.group_id,g])),out=new Map();
  x.parts.forEach((q,i)=>{const at=name+'.parts['+i+']';exact(q,['group_id','rows'],at);const g=byId.get(q.group_id);
   if(!g||!g.files.includes(name))refuse('GROUP_NOT_IN_PART',at+'.group_id');if(!Array.isArray(q.rows)||!q.rows.length)refuse('ROWS_INVALID',at+'.rows');
   q.rows.forEach((r,j)=>exact(r,DIST_ROW_KEYS,at+'.rows['+j+']'));out.set(q.group_id,(out.get(q.group_id)||[]).concat(q.rows));});
  for(const g of D.groups)if(g.files.includes(name)&&!out.has(g.group_id))refuse('GROUP_MISSING',name+'.'+g.group_id);
  return{ok:true,value:freeze(out)};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

// All rows of one group, once every part it names is checked (Map part name → checkDistributionPart value): complete (every evaluation
// row of its scope once, none from another ranking scope), and in agreement with the index (N, ranks 1..N in the stored order, band
// counts, unavailable reasons, tie splits). Any disagreement refuses the group; nothing is repaired.
function distributionGroup(D,group_id,parts){
 try{if(!D||!DIST_CHECKED.has(D))refuse('NOT_CHECKED','$');const g=D.groups.find(x=>x.group_id===group_id);if(!g)refuse('GROUP_UNKNOWN',group_id);
  const rows=[],fileOf=new Map();for(const f of g.files){const p=parts&&parts.get(f);if(!p)refuse('PART_NOT_LOADED',f);for(const r of p.get(group_id)||[]){rows.push(r);fileOf.set(r,f);}}
  const at=group_id,ids=new Set(),scopeOf=new Map(Object.entries(D.scopeOf).map(([k,v])=>[k,v[g.board]]));
  if(rows.length!==g.evaluation_rows_in_scope)refuse('GROUP_ROWS',at);
  for(const r of rows){if(ids.has(r.company_id))refuse('GROUP_ROWS',at+'.'+r.company_id);ids.add(r.company_id);
   if(scopeOf.get(r.company_id)!==g.ranking_scope)refuse('RANKING_SCOPE',at+'.'+r.company_id);
   if(r.kind!=='CORE'&&r.kind!=='ADDITIONAL')refuse('TYPE',at+'.'+r.company_id+'.kind');
   if(r.score===null){if(r.rank!==null||r.stored_decile!==null||r.decile!==null||typeof r.score_status!=='string')refuse('RANK_WITHOUT_SCORE',at+'.'+r.company_id);}
   else if(!isScore(r.score)||!int(r.rank)||r.rank_n!==g.evaluation_valid_n)refuse('TYPE',at+'.'+r.company_id);
   if(r.decile===null?r.decile_status==='VALID':(!int(r.decile)||r.decile<1||r.decile>10||r.decile_status!=='VALID'))refuse('DECILE_INVALID',at+'.'+r.company_id);
   if(D.display_policy===DIST.STORED&&(r.decile!==r.stored_decile||(r.score!==null&&r.decile_status!==r.stored_decile_status)))refuse('DECILE_INVALID',at+'.'+r.company_id);}
  const valid=rows.filter(r=>r.score!==null).sort((a,b)=>a.rank-b.rank);
  if(valid.length!==g.evaluation_valid_n||valid.some((r,i)=>r.rank!==i+1))refuse('RANK_INTEGRITY',at);
  for(let i=1;i<valid.length;i++){const a=valid[i-1],b=valid[i];if(a.score<b.score||(a.score===b.score&&a.company_id>b.company_id))refuse('STORED_ORDER',at+'.'+b.company_id);}
  // Tallies of the delivered rows only (an absent key is a band or reason no row has; no count is filled in).
  const counts=new Map(),reasons=new Map(),tally=(m,k)=>m.set(k,m.has(k)?m.get(k)+1:1);for(const r of rows){if(r.decile!==null)tally(counts,r.decile);else tally(reasons,r.decile_status);}
  const stored=new Map(g.bins.filter(b=>b.count>0).map(b=>[b.decile,b.count]));
  if(stored.size!==counts.size||[...counts].some(([d,n])=>stored.get(d)!==n))refuse('BINS_MISMATCH',at);
  if(reasons.size!==Object.keys(g.unavailable_reasons).length||[...reasons].some(([k,v])=>g.unavailable_reasons[k]!==v))refuse('BINS_MISMATCH',at+'.unavailable_reasons');
  const splits=valid.filter((r,i)=>i&&valid[i-1].score===r.score&&valid[i-1].stored_decile!==r.stored_decile).length;
  if(splits!==g.legacy_tie_splits.length)refuse('TIE_SPLITS_MISMATCH',at);
  // The part file each row was read from (Codex #437 6848164775: a bin's member_files must be exactly the files holding its rows).
  const value=freeze({group:g,rows});GROUP_FILES.set(value,fileOf);return{ok:true,value};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}
const GROUP_FILES=new WeakMap();

// What the screen shows for one checked group: its context once, the ten bands with their stored counts and the unavailable rows apart,
// and for a chosen band (a decile, or 'NONE') one page of its rows in the stored rank order (unavailable rows as delivered). Choosing
// a band or a page narrows what is shown; the rank, N and band of every row stay the producer's.
const DIST_PAGE=50;
function distributionView(D,G,{band=null,page=0,sectorName}={}){const g=G.group,b=D.boards[g.board],n=g.evaluation_valid_n;
 const scope=g.ranking_scope==='COMMON'?'통합 비교집단(평가 집단 전체)':'섹터 비교집단 · '+g.ranking_scope.split('|').slice(1).map((x,i)=>i===0&&sectorName?sectorName(x):x).join(' · ');
 const policy=D.display_policy===DIST.STORED?'분위 기준: 저장된 평가 순위 분위(stored-evaluation-deciles/1 · 기존 규칙 유지)'+(g.legacy_tie_splits.length?' · 같은 점수가 서로 다른 구간에 들어간 곳 '+g.legacy_tie_splits.length+'곳(회사 ID 순으로 경계가 갈림)':' · 이 묶음에서는 같은 점수가 구간 경계에서 갈린 곳 없음')
  :'분위 기준: 참조 점수 10점 구간(reference-score-deciles/1 · 별도 연구 후보 · 활성화 안 함 · 합성만)';
 // Each stored split as delivered (score, the two saved ranks either side of the boundary, the two bands); nothing re-ranked.
 const ties=g.legacy_tie_splits.map(t=>freeze({text:'점수 '+fmt(t.score)+' · 순위 '+t.last_rank+'까지 '+BAND[t.from_decile]+' · 순위 '+t.next_rank+'부터 '+BAND[t.to_decile]}));
 const bands=g.bins.map(x=>freeze({decile:x.decile,label:BAND[x.decile],count:x.count,selected:band===x.decile}));
 const pick=band===null?null:band==='NONE'?G.rows.filter(r=>r.decile===null):G.rows.filter(r=>r.decile===band).sort((a,c)=>a.rank-c.rank);
 const total=pick?pick.length:0,pages=Math.max(1,Math.ceil(total/DIST_PAGE)),pg=Math.min(Math.max(0,page|0),pages-1),slice=pick?pick.slice(pg*DIST_PAGE,pg*DIST_PAGE+DIST_PAGE):[];
 return freeze({head:MODELS[g.board].label+' · '+g.variant_id+' · '+scope,
  context:'평가 유효 '+n+' / 범위 내 '+g.evaluation_rows_in_scope+' · 참조 N '+g.reference_valid_n+'(순위 분모 아님) · 원지표 '+(g.raw_direction==='LOWER'?'낮을수록 좋음':'높을수록 좋음')+' · 점수는 높을수록 좋음 · 평가일 '+b.evaluation_population.valuation_date,
  members:'비교집단 구성원 해시 '+g.comparison_group.members_hash.slice(0,12)+'… · 결과 '+b.result_hash.slice(0,12)+'…',policy,ties,bands,
  input:D.bound?inputLine(D.delivery):'합성 사례 · 전달본과 묶이지 않음',inputVerified:D.bound&&inputVerified(D.delivery),
  unavailable:freeze({count:g.unavailable_count,selected:band==='NONE',reasons:Object.entries(g.unavailable_reasons).map(([k,v])=>word(k)+' '+v)}),
  selected:band===null?null:band==='NONE'?'분위 없음 · '+total+'개':BAND[band]+' · 분위 '+band+' · '+total+'개'+(total?'':' · 확인된 빈 구간'),
  page:pg,pages,range:total?(pg*DIST_PAGE+1)+'–'+(pg*DIST_PAGE+slice.length)+' / '+total:'0 / 0',
  rows:slice.map(r=>freeze({company_id:r.company_id,rank:r.rank===null?'순위 없음':r.rank+' / '+r.rank_n,score:r.score===null?'미산출':fmt(r.score),
   band:r.decile===null?'분위 없음 · '+word(r.decile_status):BAND[r.decile]+'(분위 '+r.decile+')',kind:r.kind==='CORE'?'핵심':'추가(점수 기여 0)'}))});}

// 구간 색인 (Codex qgv-dual-factor-bins/1, "All-bin routing companion /1", #529 9a51b4ae): an optional companion of one checked
// distribution. Its manifest pins the distribution manifest (source_manifest_sha256); its index repeats the distribution's boards,
// bands and source index descriptor and routes every group to one bins file; each group record is the distribution's own group with
// all ten bins enriched: count, first/last SAVED rank, the members hash (SHA-256 of the canonical JSON list of company ids in saved
// rank order) and the distribution files that hold those members. The reader checks every record against the distribution and then,
// for a loaded group, every bin's members against its rows. Nothing is ranked or binned here.
const BINS=Object.freeze({MANIFEST:'qgv-dual-factor-bins-manifest/1',INDEX:'qgv-dual-factor-bins/1',PART:'qgv-dual-factor-bins-part/1'});
const BINS_PART=/^bins-\d{3}\.json$/;
const BINS_INDEX_KEYS=['schema_version','scope','data_kind','source_distribution_manifest','source_index','display_policy','boards','bands','groups','rank_policy',
 'minimum_reference_score_n','minimum_stored_evaluation_decile_n','tie_policy','remainder_policy','new_score_calculations','additional_factor_score_contribution',
 'filter_changes_population','whole_market_denominator','whole_market_coverage'];
const BIN_KEYS=['decile','count','first_rank','last_rank','members_hash','member_files'];
const BINS_CHECKED=new WeakSet();
async function checkBins(parts,D,sha256){
 try{if(!D||!DIST_CHECKED.has(D))refuse('DISTRIBUTION_NOT_CHECKED','$');if(typeof sha256!=='function')refuse('HASH_UNAVAILABLE','$');
  const p=parts||{};if(!isObj(p.manifest)||!isObj(p.manifest.body)||!(p.manifest.bytes instanceof Uint8Array))refuse('BYTES_REQUIRED','bins_manifest');const m=p.manifest.body;
  exact(m,['schema_version','scope','data_kind','source_manifest_sha256','files'],'bins_manifest');
  if(m.schema_version!==BINS.MANIFEST)refuse('SCHEMA','bins_manifest.schema_version');
  if(m.scope!==D.scope||m.data_kind!==D.data_kind)refuse('SCOPE_MISMATCH','bins_manifest.scope');
  if(m.source_manifest_sha256!==D.manifest_sha256)refuse('BINS_SOURCE_MISMATCH','bins_manifest.source_manifest_sha256');
  if(!Array.isArray(m.files)||!m.files.length||m.files.length>400)refuse('FILES_INVALID','bins_manifest.files');const entries=new Map();
  m.files.forEach((f,i)=>{exact(f,['path','size','sha256'],'bins_manifest.files['+i+']');
   if(!(f.path==='bin-index.json'||BINS_PART.test(f.path))||entries.has(f.path)||!int(f.size)||f.size<1||f.size>MAX_BYTES||!HEX.test(f.sha256))refuse('FILES_INVALID','bins_manifest.files['+i+']');entries.set(f.path,f);});
  const x=await bytesMatch(p.index,'bin-index.json',entries,sha256,'bins_index');exact(x,BINS_INDEX_KEYS,'bins_index');
  if(x.schema_version!==BINS.INDEX)refuse('SCHEMA','bins_index.schema_version');
  if(x.scope!==D.scope||x.data_kind!==D.data_kind||x.display_policy!==DIST.STORED||D.display_policy!==DIST.STORED)refuse('SCOPE_MISMATCH','bins_index');
  if(!same(x.source_distribution_manifest,{path:'distribution-manifest.json',size:x.source_distribution_manifest&&x.source_distribution_manifest.size,sha256:D.manifest_sha256})
   ||!int(x.source_distribution_manifest.size)||!same(x.source_index,D.entries['distribution-index.json']))refuse('BINS_SOURCE_MISMATCH','bins_index.source_distribution_manifest');
  if(!same(x.boards,D.boards))refuse('BINS_SOURCE_MISMATCH','bins_index.boards');
  if(!Array.isArray(x.bands)||x.bands.length!==10||x.bands.some((b,j)=>b.decile!==10-j||b.label!==BAND[b.decile]))refuse('BANDS_INVALID','bins_index.bands');
  if(x.rank_policy!=='UNROUNDED_FACTOR_SCORE_DESC_COMPANY_ID_ASC_ORDINAL'||x.minimum_reference_score_n!==20||x.minimum_stored_evaluation_decile_n!==10
   ||x.tie_policy!=='PRESERVE_STORED_ORDINAL_COMPANY_ID_BOUNDARIES'||x.remainder_policy!=='D10_D1_FLOOR_N_OVER_10;MIDDLE_REMAINDER_D9_TO_D2')refuse('RULE_MISMATCH','bins_index.rank_policy');
  if(x.new_score_calculations!==0||x.additional_factor_score_contribution!==0||x.filter_changes_population!==false||x.whole_market_denominator!==null||x.whole_market_coverage!==null)refuse('NOT_PROJECTION','bins_index');
  // Every distribution group is routed once, to a listed bins file; every listed bins file holds a routed group.
  if(!Array.isArray(x.groups)||x.groups.length!==D.groups.length)refuse('ROUTES_INVALID','bins_index.groups');const routes=new Map(),files=new Set();
  x.groups.forEach((r,i)=>{exact(r,['group_id','path'],'bins_index.groups['+i+']');
   if(!D.groups.some(g=>g.group_id===r.group_id)||routes.has(r.group_id)||!BINS_PART.test(r.path)||!entries.has(r.path))refuse('ROUTES_INVALID','bins_index.groups['+i+']');routes.set(r.group_id,r.path);files.add(r.path);});
  for(const f of entries.keys())if(BINS_PART.test(f)&&!files.has(f))refuse('PART_UNREFERENCED','bins_manifest.files.'+f);
  const value=freeze({dist:D,entries:Object.fromEntries(entries),routes:Object.fromEntries(routes)});BINS_CHECKED.add(value);return{ok:true,value};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

// One bins file of checked bins: exactly the groups routed there; each is the distribution's own group record (every original field
// the same) with ten bins in order whose counts are the distribution's, ranks null exactly when empty, and member files that are the
// distribution's own file descriptors among that group's files. Returns Map group_id → routed group.
async function checkBinsPart(file,name,B,sha256){
 try{if(!B||!BINS_CHECKED.has(B)||!own(B.entries,name)||!BINS_PART.test(name))refuse('NOT_IN_MANIFEST',name);
  const x=await bytesMatch(file,name,new Map(Object.entries(B.entries)),sha256,name);exact(x,['schema_version','groups'],name);
  if(x.schema_version!==BINS.PART)refuse('SCHEMA',name+'.schema_version');const D=B.dist,want=Object.entries(B.routes).filter(([,p])=>p===name).map(([g])=>g);
  if(!Array.isArray(x.groups)||x.groups.length!==want.length)refuse('GROUPS_MISMATCH',name+'.groups');const out=new Map();
  x.groups.forEach((r,i)=>{const at=name+'.groups['+i+']',g=D.groups.find(y=>y.group_id===(r&&r.group_id));
   if(!g||!want.includes(g.group_id)||out.has(g.group_id))refuse('GROUPS_MISMATCH',at+'.group_id');exact(r,[...DIST_GROUP_KEYS,'binned_evaluation_n','partition_status'],at);
   for(const k of DIST_GROUP_KEYS)if(k!=='bins'&&!same(r[k],g[k]))refuse('GROUP_CONTEXT',at+'.'+k);
   const n=g.evaluation_valid_n,status=n>=10?'COMPLETE':n>0?'SAMPLE_LT_10':'NO_VALID_SCORE';
   if(!Array.isArray(r.bins)||r.bins.length!==10)refuse('BINS_INVALID',at+'.bins');let sum=0;
   r.bins.forEach((b,j)=>{const bt=at+'.bins['+j+']';exact(b,BIN_KEYS,bt);if(b.decile!==10-j||b.count!==g.bins[j].count)refuse('BIN_COUNT',bt);sum+=b.count;
    if(b.count?(!int(b.first_rank)||!int(b.last_rank)||b.first_rank<1||b.last_rank<b.first_rank||b.last_rank>n):(b.first_rank!==null||b.last_rank!==null))refuse('BIN_RANKS',bt);
    if(!HEX.test(b.members_hash)||!Array.isArray(b.member_files)||(b.count?!b.member_files.length:b.member_files.length))refuse('BIN_FILES',bt);
    b.member_files.forEach(f=>{if(!isObj(f)||!g.files.includes(f.path)||!same(f,D.entries[f.path]))refuse('BIN_FILES',bt+'.member_files');});
    if(new Set(b.member_files.map(f=>f.path)).size!==b.member_files.length)refuse('BIN_FILES',bt+'.member_files');});
   if(r.binned_evaluation_n!==sum||r.partition_status!==status||(n>=10?sum!==n:sum!==0))refuse('BIN_PARTITION',at);out.set(g.group_id,r);});
  return{ok:true,value:freeze(out)};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

// A loaded group's rows against its routed record: in every bin, the rows carrying that decile, in saved rank order, are exactly the
// stated count, first and last rank and members hash. Any difference refuses the whole group (never an empty or shorter band).
async function binsMatchGroup(record,G,sha256){
 try{if(!record||!G||record.group_id!==G.group.group_id)refuse('GROUP_MISMATCH','$');
  for(const b of record.bins){const rows=G.rows.filter(r=>r.decile===b.decile).sort((a,c)=>a.rank-c.rank),at=record.group_id+'.D'+b.decile;
   if(rows.length!==b.count)refuse('BIN_MEMBERS',at+'.count');
   if(b.count&&(rows[0].rank!==b.first_rank||rows[rows.length-1].rank!==b.last_rank))refuse('BIN_MEMBERS',at+'.ranks');
   if((await sha256(new TextEncoder().encode(canonical(rows.map(r=>r.company_id)))))!==b.members_hash)refuse('BIN_MEMBERS',at+'.members_hash');
   // The bin names exactly the distinct part files its rows were read from: none missing, none extra (no duplicate by checkBinsPart).
   const fileOf=GROUP_FILES.get(G);if(!fileOf)refuse('GROUP_NOT_CHECKED',at);
   const holds=[...new Set(rows.map(r=>fileOf.get(r)))].sort(),named=b.member_files.map(f=>f.path).sort();
   if(holds.length!==named.length||holds.some((f,i)=>f!==named[i]))refuse('BIN_FILES',at+'.member_files');}
  return{ok:true};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

const RULES=Object.freeze(['U1·U2·S1 점수는 같은 척도가 아님 · 평균·합산·차이를 만들지 않음',
 '총점이 없으면 총점 순위도 없음 · 섹터 순위를 이어 붙인 통합 순위 없음',
 '연구 후보 · 공식 QGV·기본값·포트폴리오 목표에 반영되지 않음 · 성과 미측정',
 '필터·정렬은 생산자 행을 보이는 순서만 바꾸고 점수·순위·분모·참조 N을 바꾸지 않음']);

function rowsView(d,key,{sectorName,limit=50}={}){return d.rows.slice(0,limit).map(r=>{const b=r.boards[key];
 return freeze({company_id:r.company_id,issuer_id:r.issuer_id,Q:fmt(b.axes.Q),G:fmt(b.axes.G),V:fmt(b.axes.V),total:fmt(b.total),rank:rankText(b,sectorName),
  scope:scopeWord(b.ranking_scope,sectorName),status:word(b.status),gate:word(b.gate_status)});});}

// One factor of one company in one model: its band in its own comparison group (the board's ranking scope), the evaluation valid N
// (the rank denominator), the reference N and the valuation date; shown whether or not the board has a total.
const factorText=(v,f,{group,date}={})=>v+' · '+(f.score===null?'점수 미산출 · '+word(f.score_status):'점수 '+fmt(f.score)+' · '+bandText(f)+' · 요소 순위 '+f.rank+' / 평가 유효 '+f.rank_n)
 +' · 참조 N '+(f.valid_n===null?'—':f.valid_n)+(group?' · 비교집단 '+group:'')+(date?' · 평가일 '+date:'');

// One company in every model, side by side: each model's own words, never a difference or an average.
function compareView(row,d,{sectorName}={}){return freeze({company_id:row.company_id,
 note:'모형마다 핵심 요소·참조집단·순위 범위가 다름 · 점수 차이를 계산하지 않음',
 bandRule:DECILE_RULE,
 boards:d.models.map(k=>{const b=row.boards[k],M=MODELS[k],add=Object.entries(b.factors).filter(([,f])=>f.kind==='ADDITIONAL');
  const ctx={group:scopeWord(b.ranking_scope,sectorName),date:d.summary.boards[k].evaluation_population.valuation_date};
  const w=M.gen==='Q333'&&b.weight_fractions?b.weight_fractions:null,ax=o=>['Q','G','V'].map(a=>a+' '+frac(o[a])).join(' · ');
  const wtext=v=>w?' · 총점 비중 '+frac(w.nominal_factors[v])+(ratEq(w.nominal_factors[v],w.post_gate_factors[v])?'':' → 관문 뒤 '+frac(w.post_gate_factors[v])):'';
  return freeze({key:k,label:M.label,gen:M.gen,
   recipe:M.gen==='Q333'?'구성 상태 · '+RECIPE_WORD[b.recipe_state]:null,
   weights:M.gen!=='Q333'?null:w?'축 비중(관문 전) '+ax(w.nominal_axes)+' · 관문 뒤 '+ax(w.post_gate_axes)+' · 축 안 세 요소는 각 1/3':'비중 없음(구성 적용 안 됨)',
   missing:M.gen==='Q333'&&b.missing_factors?['Q','G','V'].map(a=>a+' 결손 '+(b.missing_factors[a].length?b.missing_factors[a].join(', '):'없음')).join(' · '):null,
   evidence:M.gen==='Q333'?b.selected_variants.map(evidenceText):[],
   axes:'Q '+fmt(b.axes.Q)+' · G '+fmt(b.axes.G)+' · V '+fmt(b.axes.V)+' · 총점 '+fmt(b.total),
   rank:rankText(b,sectorName),scope:scopeWord(b.ranking_scope,sectorName),status:word(b.status)+' · '+word(b.gate_status),
   core:b.selected_variants.map(v=>factorText(v,b.factors[v],ctx)+wtext(v)),
   additional:add.filter(([,f])=>f.score!==null).map(([v,f])=>factorText(v,f,ctx)),
   additionalMissing:add.filter(([,f])=>f.score===null).length});})});}

/* ---- the research engine route (owner 2026-11-11 §3; development bridge, tools/sector_qgv_engine_bridge.py): requests name the
   model and the candidate explicitly; an answer is used only when it is the answer to that very request (op, request id, model,
   model_id) and its board is that candidate's (qgv-dual-board/1, same model_id, no rank without a total). Nothing is computed here. */
const ENGINE=Object.freeze({REQUEST:'sector-qgv-engine-request/1',RESPONSE:'sector-qgv-engine-response/1',BOARD:'qgv-dual-board/1',SAVED:'qgv-dual-saved/1'});
const MODEL_OF=Object.freeze(Object.fromEntries(Object.entries(MODELS).map(([k,m])=>[m.model_id,Object.freeze({key:k,model:m.kind==='COMMON'?'INTEGRATED':'SECTOR'})])));
const ENGINE_OPS=Object.freeze(['context','preview','save','replay']);
const KIND_WORD=Object.freeze({SYNTHETIC_RECALCULATION:'합성 실제 재계산(지금 설정·지금 입력)',EXACT_REPLAY:'정확 재현(같은 설정·코드·원래 입력)'});
let reqSeq=0;
function engineRequest(op,model_id,fields={}){if(!ENGINE_OPS.includes(op))throw Error('DUAL_OP_UNKNOWN');const m=MODEL_OF[model_id];if(!m)throw Error('MODEL_ID_UNKNOWN');
 reqSeq=(reqSeq+1)%1e9;return Object.freeze({...fields,schema_version:ENGINE.REQUEST,op,request_id:'DUAL-'+op+'-'+m.key+'-'+reqSeq,model:m.model,model_id});}
// A saved research record (the engine's save_board answer as returned): schema, the four keys, a known candidate, hashes.
function validateSaved(x){try{exact(x,['schema_version','configuration','bindings','result_hash'],'saved');if(x.schema_version!==ENGINE.SAVED)refuse('SAVED_SCHEMA_MISMATCH','saved.schema_version');
  if(!isObj(x.configuration)||!MODEL_OF[x.configuration.model_id])refuse('MODEL_ID_UNKNOWN','saved.configuration.model_id');
  if(!isObj(x.bindings)||!HEX.test(x.bindings.model_hash)||!HEX.test(x.result_hash))refuse('HASH_INVALID','saved');return{ok:true};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}
function boardCheck(b,model_id){if(!isObj(b)||b.schema_version!==ENGINE.BOARD)refuse('BOARD_SCHEMA','board');if(b.model_id!==model_id)refuse('MODEL_RESPONSE_MISMATCH','board.model_id');
 if(!HEX.test(b.result_hash)||!Array.isArray(b.rows))refuse('BOARD_INVALID','board');
 b.rows.forEach((r,i)=>{const at='board.rows['+i+']';if(!isObj(r)||!isObj(r.axes))refuse('BOARD_INVALID',at);head(r,MODEL_OF[model_id].key,at);});}
function checkAnswer(req,res){try{if(!isObj(res)||res.schema_version!==ENGINE.RESPONSE)refuse('ENGINE_ANSWER_INVALID','$');
  if(res.request_id!==req.request_id||res.op!==req.op)refuse('ENGINE_ANSWER_OTHER_REQUEST','$');
  if(res.ok!==true)return{ok:false,code:typeof res.code==='string'&&/^[A-Z][A-Z0-9_:a-z]{1,79}$/.test(res.code)?res.code:'ENGINE_FAILED',path:'$'};
  if(res.model!==req.model||res.model_id!==req.model_id)refuse('MODEL_RESPONSE_MISMATCH','$.model_id');
  if(req.op==='preview'||req.op==='replay'){boardCheck(res.board,req.model_id);
   if(res.kind!==(req.op==='preview'?'SYNTHETIC_RECALCULATION':'EXACT_REPLAY'))refuse('ANSWER_KIND','$.kind');
   if(req.op==='replay'&&res.board.result_hash!==req.saved.result_hash)refuse('REPLAY_RESULT_MISMATCH','$.board.result_hash');}
  if(req.op==='save'){const v=validateSaved(res.saved);if(!v.ok)refuse(v.code,v.path);
   if(res.saved.configuration.model_id!==req.model_id||res.saved.result_hash!==req.result_hash)refuse('MODEL_RESPONSE_MISMATCH','$.saved');}
  return{ok:true,value:res};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}
function boardRowsView(b,{sectorName}={}){const key=MODEL_OF[b.model_id].key;return b.rows.map(r=>freeze({company_id:r.company_id,Q:fmt(r.axes.Q),G:fmt(r.axes.G),V:fmt(r.axes.V),
 total:fmt(r.total),rank:rankText(r,sectorName),status:word(r.status)+' · '+word(r.gate_status),key}));}

function ramStore(){let held=new Map();const ls=new Set();const tell=()=>{for(const f of[...ls]){try{f();}catch(_){}}};
 return Object.freeze({set(scope,v){if(!own(SLOTS,scope)||!CHECKED.has(v)||v.slot!==scope)throw Error('DUAL_UNCHECKED');held.set(scope,Object.freeze({delivery:v,details:new Map()}));tell();},get:scope=>held.get(scope)||null,
  drop(){if(!held.size)return;held=new Map();tell();},subscribe(f){ls.add(f);return()=>ls.delete(f);}});}
const ram=ramStore();

return Object.freeze({SLOTS,GEN,EVIDENCE_333,STAGES_333,stagesOf,RECIPE_WORD,evidenceText,INPUT_VERIFIED,inputVerified,inputLine,BINS,checkBins,checkBinsPart,binsMatchGroup,REF_ANCHOR_SCHEMA,DIST,DIST_PAGE,checkDistribution,checkDistributionSynthetic,checkDistributionPart,distributionGroup,distributionView,BAND,DECILE_RULE,bandText,SELECTION,checkSelection,selectionMatchesShard,LEADERS,checkLeaders,checkLeaderShard,leaderGroups,leaderView,LINEAGE_SCHEMA,PROJECTION_FIELDS,ENGINE,MODEL_OF,KIND_WORD,engineRequest,validateSaved,checkAnswer,boardRowsView,SCHEMA,SCOPES,INPUT_CHECK,INPUT_WORD,MODELS,KIND,STAGES,RULES,word,checkDelivery,checkDetail,boardView,rowsView,compareView,ram,ramStore,MAX_BYTES});
});
