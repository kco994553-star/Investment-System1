# Track C C8 Package A — explicit partial approval

Approval processing clock: **2026-10-02T17:47:51.000+09:00** (actual current KST); UTC 2026-10-02 08:47:51 UTC.

Authority: explicit latest user approval. Source GitHub HEAD `86e345e54678de05ebcdf2e1db53c9dbe72ca52a`. This is **PARTIAL approval only**, not whole Package A approval. Original Package A/dossier and all historical C0–C7 policy/Freeze evidence remain untouched. The accompanying JSON is the runtime-pinned scoped authority record.

## A1 — APPROVED_WITH_MODIFICATION

C8 calibration은 C4 model-fitting/calibration 및 C7 selection과 명시적으로 분리된 C8 calibration boundary를 사용한다.
C4 또는 C7에서 이미 selection에 사용한 OOS evidence를 새로운 independent confirmation evidence처럼 재사용하지 않는다.
CAL_FIT과 CAL_VERIFY의 identity, scope, available_at, dataset lineage를 사전 등록한다.
Holdout은 calibration source로 사용할 수 없다.
실제 CAL_FIT/CAL_VERIFY dataset allocation은 별도 real research configuration이 없으면 실행하지 않는다.

## A2 — APPROVED_WITH_MODIFICATION

C8 전용 immutable registration/ledger를 사용한다.
threshold/gate/calibration attempt는 결과 접근 전에 등록한다.
모든 family member와 attempt를 accounting한다.
FAIL/NOT_RUN/pending/crash/invalidation을 보존한다.
사후 재등록, trial 삭제, successful subset만의 accounting을 금지한다.
접근 증거와 registration 순서를 검증 가능하게 보존한다.

## A3 — APPROVED_WITH_MODIFICATION

Threshold calibration search가 실제로 사용되는 경우 range/grid/sensitivity/plateau 정의는 pre-result configuration이어야 한다.
graph universe와 adjacency/tolerance는 사전 등록한다.
plateau stability는 statistical/economic validity와 동일한 의미가 아니다.
largest peak 또는 best observed result를 자동 선택하지 않는다.
실제 numeric range/grid/tolerance는 이번 승인에 포함하지 않는다.

## A4 — APPROVED_WITH_MODIFICATION

CAL_FIT에서 생성된 적격 threshold candidate 중 어떤 candidate를 선택하는지 명시적 selection/approval event로 보존한다.
rounding rule과 rounding support는 사전 등록한다.
CAL_VERIFY는 one-shot confirmation boundary로 취급한다.
CAL_VERIFY 실패 후 threshold 재적합, next-best 자동 선택, tolerance 변경, metric 변경, rounding 변경을 하지 않는다.
실패 후 새로운 연구를 하려면 새 registration/trial로 시작한다.

## A5 — EXISTING_POLICY_RECONFIRMED

Universal hard gates는 calibration 대상이 아니다.
PIT, provenance, lineage, complete ledger, scope, tax mode, invalidation, Holdout isolation 등의 integrity failure를 높은 성과나 statistical/economic gate PASS로 상쇄하지 않는다.

## A6 — PROPOSED_NOT_APPROVED_NOT_ACTIVE

새 bootstrap-derived p-value, multiple-testing combination, statistical family decision rule은 아직 구현하지 않는다.
기존 C6 PSR, DSR sensitivity views, PBO, joint circular-block bootstrap, Reality Check 계산 evidence는 보존할 수 있으나, C8 statistical PASS/FAIL을 새로 결정하는 규칙으로 확장하지 않는다.
A6는 별도 statistical-validation package로 재검토한다.

## A7 — APPROVED_WITH_MODIFICATION_FRAMEWORK_ONLY

Negative-control / skill assessment framework를 승인한다.
그러나 NO_EVIDENCE_OF_SKILL 또는 skill evidence를 판정하려면 사전 등록된 control과 비교하여 지정 후보가 승인된 방향으로 superiority evidence를 가져야 한다.
단순히 control이 실패했다는 사실, candidate return이 양수라는 사실, C6 diagnostic PASS만으로 skill을 선언하지 않는다.
실제 effect threshold 및 statistical decision rule은 A6/real configuration 승인 전에는 활성화하지 않는다.

## A8 — PROPOSED_NOT_APPROVED_NOT_ACTIVE

Profile distinctness hard decision은 보류한다.
C7의 raw pairwise distinctness evidence만 보존한다.
distinctness metric family, pair family, cohort aggregation, multiple-comparison handling, OR/AND semantics, statistical/economic separation criteria가 승인되기 전에는 PROFILE_NOT_DISTINCT, DISTINCT hard decision을 만들지 않는다.
자동 next-best profile 탐색도 금지한다.

## A9 — STRUCTURE_APPROVED_NUMERIC_CONFIG_REQUIRED

Economic gate의 순서는 기존 계약대로 유지한다.
nominal → real → risk-free excess → premium → opportunity cost → risk-adjusted
각 단계의 exact metric identity/formula/provenance를 versioned configuration으로 등록해야 한다.
실제 premium minimum, opportunity-cost threshold, risk-adjusted limit 등의 숫자는 이번 승인에 포함하지 않는다.
숫자가 없으면 해당 real economic decision은 NOT_RUN이다.
한 단계의 높은 성과로 다른 hard failure를 상쇄하지 않는다.

## A10 — PROPOSED_NOT_APPROVED_NOT_ACTIVE

Champion / Challenger 지정은 보류한다.
C7 representative/tie set에서 qualified candidate pool, singleton behavior, role count, role assignment authority, assignment timing, tie handling이 확정되기 전에는 역할을 자동 지정하지 않는다.
hash, rank, 최고 return 등을 암묵적 role selector로 사용하지 않는다.

## A11 — APPROVED_WITH_MODIFICATION

Synthetic/software evidence와 real research evidence를 실제 current evidence resolution으로 분리한다.
단순 boolean, scope 문자열, producer PASS, synthetic=false만으로 real validation authority를 부여하지 않는다.
특히 robustness.acceptance().real_pit_research_validated를 단독 promotion/validation authority로 사용하지 않는다.
C8 진입 시 실제 evidence identity/hash, dataset lineage, current invalidation, approval authority, methodology/version, scope를 재검증한다.
Synthetic C8 fixture가 real Manifest 또는 Official 상태를 만들 수 없다.

## A12 — APPROVED_SOFTWARE_PROTOCOL_ONLY

C8 synthetic SOFTWARE validation protocol을 승인한다.
단 이 단계에서 검증 가능한 것은 승인된 C8 protocol/software path뿐이다.
Synthetic fixture PASS는 REAL_PIT_VALIDATED, VALIDATED, HOLDOUT_TESTED, OFFICIAL, FORWARD_VALIDATED를 의미하지 않는다.

## Scope / stop conditions

Approved implementation is restricted to C8 foundation contracts, immutable preregistration/ledger/budget/invalidation, separate calibration boundaries, threshold registration machinery, Universal integrity gates, control evidence framework, economic identity/config framework, scope separation and synthetic fixtures/partial acceptance runner.

A6/A8/A10 and actual numeric research configuration remain PROPOSED / NOT APPROVED / NOT ACTIVE. No placeholder defaults. No real allocation/calibration/PIT validation, Holdout content/result read or Official promotion. No C8 SOFTWARE FROZEN until outstanding policies and all mandatory acceptance are approved/completed. Frozen phase count remains **8/11 = 72.7%**, software only.

Package B/C remain unchanged and inactive. PR#4 Draft/Open/unmerged; no canonical/automatic merge, force push or history rewrite. Investor-QGV FUTURE_TRACK_C_INPUT. C0–C7 frozen source/tests and historical evidence are preserved. After approved foundation regression, stop and report implementation/tests/unresolved A6/A8/A10/A9 configuration/new D3-P need.
