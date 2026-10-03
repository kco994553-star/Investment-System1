# Track C C8 Package A6 — explicit PARTIAL approval (superiority requirement only)

Approval processing clock: **2026-10-02T20:04:01+09:00** (actual KST at processing); UTC 2026-10-02 11:04:01 UTC.
Authority: explicit latest user message. Source GitHub HEAD `ff78c4f6c4a1a8fd15db21807de6be3905c89548` (feature/track-c-evl).
This is **not** a whole-A6 statistical method approval. Original Package A, dossier, partial Package A approval
(2026-10-02T17:47:51 KST) and all C0–C7 evidence remain unchanged. Basis: A6 pre-approval method audit
(designated-role vs control one-sided mean superiority, independent oracle + simulation, verdict REQUIRED, scope-limited).

## A6-S1 — SUPERIORITY REQUIREMENT APPROVED
C8 skill assessment에는 designated candidate/role의 control-relative superiority evidence가 필요하다.
PSR, DSR, PBO, family Reality Check, absolute positive return, positive Sharpe, C6 diagnostic PASS만으로 superiority를 선언하지 않는다.
Family-level rejection은 designated candidate가 특정 control보다 우월하다는 증거로 해석하지 않는다.

## A6-S2 — APPROVED CONTROLS
G-SUP superiority comparison의 현재 지원 control은 EQUAL_SIMPLE, MARKET_CAP 두 개로 제한한다.
C6 RANDOM_RANKING, RANDOMIZED_WEIGHTS는 superiority hard decision control로 사용하지 않는다(candidate당 하나의 seeded realization만 보존 → randomization uncertainty 미반영).
상태는 UNSUPPORTED_SINGLE_DRAW로 유지한다. Multiple preregistered draws 또는 별도 randomization-test contract 승인 전까지 G-SUP에 넣지 않는다.

## A6-S3 — CONJUNCTION SEMANTICS APPROVED
Superiority claim은 "designated candidate가 승인된 모든 required control을 모든 required cohort에서 우월하다"라는 conjunction / intersection-union semantics다.
하나의 control 또는 하나의 cohort만 통과해서는 G-SUP PASS가 아니다. beats-at-least-one-control 의미로 변경하지 않는다. OR semantics는 별도 multiple-testing policy가 필요하다.

## A6-S4 — FRESH CAL_VERIFY BOUNDARY APPROVED
Designated candidate/role, statistic family, required controls, bootstrap method/version, block convention, seed convention, effect-floor convention은 CAL_VERIFY evidence 접근 전에 고정한다.
Development/C7 selection evidence로 superiority를 confirmation하지 않는다. CAL_VERIFY는 one-shot confirmation boundary다.
실패 후 next-best candidate, 다른 control/statistic/block convention/seed convention/effect floor/alpha로 자동 재시험하지 않는다. 새 연구는 새로운 preregistered trial이어야 한다.

## A6-S5 — TEST FORM NOT APPROVED
A(existing C6 unstudentized kernel 재사용) / B(studentized bootstrap superiority test) / C(기타 새 method) 중 어느 것도 승인하지 않는다.
기존 kernel 사용 가능성은 그 kernel의 C8 superiority validity 승인이 아니다. Serial dependence에서 size distortion이 확인되었으므로 임의 선택하지 않는다.
실제 G-SUP statistical PASS/FAIL은 test-form policy 승인 전까지 NOT_RUN이다.

## A6-S6 — NUMERIC CONFIG NOT APPROVED
alpha, bootstrap B, block length, seed, effect floor, minimum sample support를 포함하지 않는다.
Fixture/simulation 숫자를 real research default로 승격하지 않는다. 실제 data access 전 별도 preregistered configuration과 power/feasibility evidence가 필요하다.

## A6-S7 — EFFECT FLOOR DEFERRED
Statistical significance와 economic effect floor 분리 원칙만 유지한다. Effect floor의 metric/unit/aggregation/threshold/statistical test 결합 방식은 승인하지 않는다.
Effect floor가 없다고 0을 기본값으로 사용하지 않는다.

## A6-S8 — SOFTWARE IMPLEMENTATION BOUNDARY
현재 구현 가능: superiority requirement contract, supported-control validation, unsupported random-control rejection, conjunction family construction,
CAL_VERIFY preregistration enforcement, one-shot/no-retry enforcement, NOT_RUN behavior, synthetic fixtures, independent oracle interface.
실제 statistical PASS/FAIL kernel은 A6-S5가 닫히기 전에는 활성화하지 않는다.

## Status
A6: **PARTIALLY_APPROVED / METHOD_PENDING**. A8: NOT APPROVED. A10: NOT APPROVED. C8: NOT FROZEN.
Track C phase count 8/11 = 72.7% (software only) unchanged. Holdout UNCONSUMED. Package B/C unchanged.
No implementation is started by this record. Next: separate A6 statistical-method decision package (test form), with numeric configuration kept separate.
