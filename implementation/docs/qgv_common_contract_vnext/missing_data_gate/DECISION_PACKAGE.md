# QGV Missing-Data Semantics Decision Gate v0.1

**READY_FOR_USER_POLICY_REVIEW / RECOMMENDED ≠ APPROVED / INACTIVE / SPEC-ONLY.**

이 문서는 QCC-P01의 Missing-Data 정책 선택을 M1–M5로 분리한 신규 제안이다. QCC-P02의 PIT/validation admission 경계를 함께 참조한다. 현재 계산을 수정하거나 정책을 승인·활성화하지 않는다. 기존 Common Contract, golden, publication evidence, 이전 Decision Package는 그대로 보존한다.

## 인수한 권위와 범위

PR [#44](https://github.com/kco994553-star/Investment-System1/pull/44)는 Draft/Open, unmerged이며 HEAD `cb1906b207623168fd70f3dcdb5b30f2d82d807d`에서 **REMOTE_VERIFIED / DRAFT_PR_CI_VERIFIED**다. Push run `37245014376`, PR run `37245037812` SUCCESS를 fresh-read했다. Canonical은 `b8e39a2196a6d7794a04a0cd5393c68329e126ca`, integration candidate는 `523e702a806a718d163cfbf62aa3fc29d8c3ef3c`로 유지된다.

원본 `4b39197`과 공개 transport commit `cb1906b`는 tree `a951276e66ed01614e27b0b00c4c14bb4f3e00ca`가 같다. Metadata/SHA 차이는 publication evidence branch `11cd2f5ac545af54d943dc206396c1fb6926689c`에 별도로 기록되어 있다. Commit identity equivalence로 표현하지 않는다. 이번 작업은 Remote Recovery를 반복하지 않는다.

Global Handoff GCH-014 / Global Status GSI-020은 routing 문서다. 일부 현재 HEAD와 PR 정보는 뒤처져 있으며 scoped exact-SHA evidence가 우선한다. Global 파일은 Primary Integration Writer의 단일 작성 영역이므로 이 작업은 별도 scoped Handoff만 추가한다. 이전 STATUS/Decision Package의 publication BLOCKED/NOT_RUN 문장은 당시 이력으로 보존한다.

현재 권한은 감사, 정책 설계, 격리된 synthetic 비교, 문서·evidence·scoped Handoff 게시다. Production scoring, factor meaning/weights, G/FCF, V, composite, runtime WeightOverride, Official boards/records, PIT 완화, Holdout, Frozen history, canonical 및 PR #44 merge는 포함하지 않는다.

## 결론과 최소 선택지

추천은 **Requiredness/Applicability 기반 Hybrid**다. 다섯 항목을 하나의 일관된 원칙 묶음으로 승인할 수 있지만 각 조항은 독립적으로 수정·거절할 수 있다. 어느 조항도 아직 승인되지 않았다.

| Decision | 사용자에게 필요한 정책 선택 | Work 추천 |
|---|---|---|
| M1 | 방법상 필요한 evidence와 경제적 적용 여부를 어떻게 구분할 것인가 | Requiredness와 applicability를 별도로 version-pin; 관측 부재·zero weight에서 역할/N/A를 추론하지 않음 |
| M2 | 어떤 결측은 부분 진단을 허용하고, 어떤 실패는 차단하는가 | reason·dependency scope별 admission; 관련 PIT/integrity/config 실패는 가중치 적용 전에 차단 |
| M3 | 결측과 N/A가 denominator에 미치는 영향 | 일반 결측은 계획 applicable denominator 유지; 입증된 정책상 N/A만 제외; available-only renormalization 배제 |
| M4 | 부분 점수를 complete score·Official ranking으로 쓸 수 있는가 | PARTIAL_CONTRIBUTION 진단 허용, 신규 Official complete score/rank admission은 applicable active 및 method-required evidence 완전성 요구 |
| M5 | zero-weight는 무엇을 해제하는가 | 수치 기여만 제외; requiredness·공유 validity·관련 PIT/integrity를 해제하지 않음 |

M1/M2가 평가 집합을 정하고, M5가 active scoring 집합을 정한 뒤 M3의 denominator를 계산한다. M4가 결과의 용도를 결정한다. Coverage 숫자 하나로 이 순서를 대체하지 않는다.

## M1 — Requiredness / Applicability

**Current behavior.** 현재 factor registry에는 공통 REQUIRED/OPTIONAL/CONDITIONAL binding이 없다. `factor_applicable`은 금융업 profile의 `roic_wacc`만 제외한다. `_weighted`는 그 관측값과 quality를 읽기 전에 제외한다. V candidate에는 같은 applicability 경로가 없다.

**Proposed policy.** 기존 stable factor ID, ProfileKind, Common Contract의 presence/applicability/legacy reason 구조를 재사용한다. Method-required는 계산·validity에 필수인 evidence다. Optional은 방법이 불완전 evidence에서도 진단 출력을 허용하는 항목이며, complete Official 비교에서 없어도 된다는 뜻은 아니다. Conditional requiredness/applicability는 issuer/profile/period에 대한 승인된 predicate를 먼저 평가한다. Predicate 또는 role binding이 없거나 판단 불가하면 UNASSESSED 및 policy/config blocking으로 남긴다.

경제적 N/A는 승인된 applicability rule와 decision-time evidence로 입증한다. 데이터 없음, 짧은 history, 부적절한 값, 낮은 점수, 사용자 weight 0은 N/A의 근거가 아니다. 금융업 ROIC 예외는 기존 의도된 차이를 그대로 mapping하며 새로운 업종 예외·taxonomy·role default를 만들지 않는다. 공통 enum을 새로 구현할 필요가 있다고 가정하지 않는다.

**Why / alternatives.** 모든 factor를 기계적으로 REQUIRED로 고정하면 신규기업·업종 availability를 과도하게 제한한다. 모든 부재를 OPTIONAL/N/A로 처리하면 의미가 없어지고 선택적 누락으로 평가 집합을 바꿀 수 있다. Weight를 requiredness proxy로 사용하면 Custom이 Official validity를 해제할 수 있다.

**Impact / approval.** Legacy 값과 history는 그대로다. 신규 version의 role/applicability admission은 score availability와 sector별 비교에 영향을 줄 수 있어 D3-P/equivalent다. Official/Personal은 pinned methodology requiredness를 공유하고 namespace별 weight만 분리한다. Input predicate evidence의 PIT와 source/version을 보존한다. Production 이전에 20개 기존 factor의 method/profile별 role·conditional predicate·evidence binding을 별도 검토해야 하며 이번 제안은 그 값을 정하지 않는다.

## M2 — Missing reason별 Eligibility / Blocking

**Current behavior.** Q/G/V prior는 absent/null/MISSING_DATA/PIT_UNAVAILABLE을 skip하여 partial contribution을 낼 수 있다. BLOCKED_DEPENDENCY는 해당 axis를 차단한다. Candidate는 불완전 V를 전체 차단하지만 numeric NOT_APPLICABLE을 사용한다. Numeric VERSION_MISMATCH, IDENTIFIER_AMBIGUOUS, CALCULATION_ERROR도 reducer에서 별도로 차단하지 않는다. Provider PIT guard와 direct factor/raw entry의 전제는 다르다. 이 사실을 historical leak 또는 모든 과거 결과 INVALID라는 주장으로 확대하지 않는다.

**Proposed policy.** Presence, applicability, admission, legacy reason을 독립적으로 보존한다. INSUFFICIENT_HISTORY/SOURCE_UNAVAILABLE/INVALID를 억지로 동일 QualityState에 압축하지 않는다. 현재 enum에 없는 이유는 evidence-backed reason/ref로 표현할 수 있다. 사유 mapping이 없거나 policy config가 불완전하면 새로운 평가를 정상 결과로 승인하지 않는다.

| 상태 / scope | 제안 처리 |
|---|---|
| Applicable method-required evidence absent/null, source unavailable, insufficient history | 해당 axis의 complete score 차단; 관측·원인·가능한 진단 contribution 보존 |
| Applicable positive-weight active optional ordinary missing | denominator를 유지한 PARTIAL_CONTRIBUTION 진단 가능; complete score/rank admission 불가. M5의 사전 미요청 optional zero-weight는 active scoring completeness와 별도 |
| Proven policy-bound N/A | 입력값 대체가 아니라 평가 scope에서 제외; N/A reason 및 predicate evidence 보존 |
| Required/consumed lineage의 PIT unavailable, future availability, missing provenance | 관련 axis 차단; soft missing이나 zero로 우회 불가 |
| Shared subject identity/time/config/version integrity failure | 영향받는 evaluation 전체 차단 |
| Factor-local invalid/nonfinite/calculation/version/ambiguous identity failure | 명시된 dependency scope 차단; 단순 결측으로 denominator 재계산하지 않음 |
| Unrelated, proven unconsumed out-of-scope artifact | 해당 artifact를 score/evidence admission에 사용하지 않음; 다른 axis를 임의 오염시키지 않음 |
| IDENTIFIER_CHANGED | 변경이라는 이름만으로 무조건 INVALID 처리하지 않음; dated identity lineage가 입증되면 pinned rule로 해소, ambiguity는 차단 |
| STALE/ESTIMATED/CONFLICTING numeric data | 현재 수용 이력 보존; 신규 admission은 method별 source/quality policy가 명시될 때만 판정. 미정 rubric을 임의 기본값으로 대신하지 않음 |
| SYNTHETIC | synthetic namespace에서만 검증; real PIT/Official evidence로 승격하지 않음 |

Input의 선언된 score scale과 finite validity를 검증할 경계는 QCC-P02와 연결한다. 기존 legacy out-of-range/nonfinite 결과는 literal evidence로 보존하며 새 clipping, epsilon, cutoff를 만들지 않는다. `available_at <= decision_time` 및 기존 `published_at` guard를 약화하지 않는다. Fetched/calculated/latest 시각을 availability의 대용으로 쓰지 않는다.

**Why / alternatives.** 모든 reason을 missing으로 취급하면 PIT나 integrity 실패가 renormalization에 의해 사라질 수 있다. 모든 artifact 실패를 전역 차단하면 적용되지 않는 ROIC의 임의 관측값이나 관련 없는 source 오류가 다른 axis까지 오염시킨다. Scope는 explicit lineage graph로 입증하고 불명확한 shared failure는 fail-closed한다.

**Impact / approval.** 현행 legacy path는 exact replay한다. 신규 numeric-invalid admission, direct entry validation 또는 factor-required blocking은 Official availability/rank를 바꿀 수 있으므로 D3-P/equivalent와 별도 runtime 승인이 필요하다. 현재 PIT를 완화하지 않는다. Personal override는 이 admission을 바꾸지 못한다. Missing-history와 G horizon 의미는 별도 G decision에 의존하며 기간 threshold는 정하지 않는다.

## M3 — Denominator / Renormalization

**Current behavior.** `_weighted`는 원래 weights가 합 1인 fixed contribution sum이며 actual observed weight로 나누지 않는다. 금융업 N/A weight도 재분배하지 않는다. V candidate는 완전한 기존 factor set과 sum을 요구한다.

**Proposed policy (신규 version의 설계).** Frozen stored weights를 그대로 참조한다. Profile에 유효하게 활성화된 scoring factor 중 경제적으로 applicable한 집합을 먼저 확정한다. 계획 denominator는 그 집합의 weight 합이다. Ordinary missing은 그 집합에 남고 numerator에 관측 기여를 넣을 수 없으나 zero 관측값으로 저장하지 않는다. 입증된 N/A는 집합에서 제외한다. Score-kind는 M4로 판정한다.

진단용 산술 관계는 `sum(admitted weight × score) / planned applicable active weight`다. 이것을 absent factor에 0점을 부여한 완전한 score 또는 expected complete estimate라고 부르지 않는다. 일반 결측이 있는 경우 **PARTIAL_CONTRIBUTION**이다. Available-only denominator로 바꾸지 않는다. All-N/A/all-zero이면 유효 denominator가 없으므로 score=None와 구체적인 blocking reason을 보존하며 0/100/NaN 같은 결과를 만들지 않는다. Unknown applicability/configuration은 denominator를 추정할 수 없다.

**Why / alternatives.** Available-weight estimate는 낮은 factor를 없애면 score를 높일 수 있다. 같은 fixed-all denominator에서 N/A까지 결측과 동일하게 남기면 적용되는 factor가 모두 같은 점수인 금융업도 비금융업보다 낮아질 수 있다. 진짜 N/A에만 계획 denominator를 변경하는 방식은 두 문제를 구분하지만 업종간 경제적 의미가 자동으로 같아지는 것은 아니다. Sector/profile별 comparison eligibility를 검증해야 한다.

**Impact / approval.** 저장된 Official factor weights를 바꾸지 않아도 N/A 제외는 effective contribution의 재분배다. 기존 금융업 uniform-70 Q=56이 신규 applicable basis에서는 70이 될 수 있다. 이는 metadata repair가 아닌 **D3 semantic delta**다. Old result/history는 덮어쓰지 않는다. 신규 계산 version과 peer/cohort comparison, rank/selection delta report, separately authorized consumer migration이 필요하다. 동일 정책은 Official/Personal evaluator에 적용하되 서로의 denominator/config/result를 수정하지 않는다.

## M4 — Coverage / Score Validity / Ranking / Confidence

**Current behavior.** Axis CoverageState는 READY/PARTIAL/BLOCKED enum이다. Snapshot overall coverage는 Q/G만 보며 V는 제외한다. 전체 confidence는 default/caller 값이고 V factor table은 QualityState를 confidence와 coverage로 재사용한다. Current Leaderboard는 total와 Q를 정렬하고 coverage로 rows를 별도 차단하지 않는다.

**Proposed policy.** 네 개념을 분리한다: (1) 진단 arithmetic contribution, (2) complete axis score, (3) complete/comparable-method eligibility, (4) Official rank/publication admission. Method-required applicable evidence와 positive-weight applicable active scoring evidence가 모두 admitted일 때만 complete axis score로 분류한다. Optional missing에서 진단 contribution은 가능하지만 신규 Official complete score/ranking 입력으로 승격하지 않는다. 이 eligibility는 V research의 Official 승격이나 publication grant를 발급하지 않는다.

Coverage는 어떤 evidence universe의 존재/admission을 측정하는지 version/ref로 선언한다. 최소 감사 inventory는 method-required evidence, applicable active scoring evidence, N/A exclusions, missing/rejected reasons이다. Count와 weight coverage는 서로 다른 view다. Weighted active coverage가 완전해도 zero-weight method-required evidence가 없으면 score가 blocked일 수 있다. History period coverage는 G factor 존재 coverage와 별개다. Unknown denominator/assessment는 UNASSESSED/null로 남긴다. 새로운 percentage cutoff를 선택하지 않는다.

Confidence는 이미 존재하는 admitted evidence의 신뢰도·평가 방법이다. Coverage의 동의어나 score multiplier가 아니다. Rubric/method/authority가 없으면 Common Contract의 UNASSESSED를 유지한다. Context CF19-B의 NOT_ASSESSED는 그 계약의 별도 표기이며 새 공통 runtime enum으로 통합하지 않는다. V의 Quality 복사 문제는 이 단계에서 수정하지 않고 별도 metadata gate로 보낸다. 새 confidence formula는 만들지 않는다.

**Why / alternatives.** 부분 estimate에 coverage label만 붙여도 rank 사용을 허용하면 희소 데이터의 상향 편향은 유지된다. 임의 coverage cutoff는 정책 근거와 validation 없이 비교 가능성을 만들어 낼 수 없다. 완전성 조건은 신규 정책의 eligibility rule이며 기존 board를 재계산하는 작업이 아니다.

**Impact / approval.** 신규 version에서는 일부 현재 partial rows의 rank admission이 달라질 수 있으므로 D3-P/equivalent다. Stored Official/legacy board·TrackRecord는 불변이다. Complete도 method/profile 비교·real PIT/OOS 검증·Official maturity·publication authority가 필요한 별도 조건이다. Personal 진단 결과는 PERSONAL namespace에 남고 Official admission/history를 바꾸지 않는다. Consumer가 complete/partial/blocked와 method IDs를 구분하도록 별도 migration 검증이 필요하다.

## M5 — Zero-weight

**Current behavior.** `_weighted`는 weight 0이어도 factor status를 읽으며 BLOCKED_DEPENDENCY가 axis를 block할 수 있다. 기존 V candidate는 현재의 5–30% 제약 때문에 zero weight가 configuration error다. Personal weight tree는 있지만 QGV runtime에는 연결되지 않았다. 이 단계는 candidate 제약을 완화하지 않는다.

**Proposed policy.** 이미 허용된 pinned configuration에서 weight 0은 contribution 0, active scoring denominator에서 weight 0만큼 제외하는 뜻이다. 관측값 missing/N/A를 뜻하지 않는다. Method-required evidence의 존재·applicability predicate·공유 identity/config/PIT validity는 유지된다. Zero-weight를 바꿔 Official validity나 Official registry를 바꿀 수 없다.

명시된 method가 선택적인 optional factor를 사전에 요청하지 않을 수 있는지는 method/config binding에 기록한다. 이미 평가·제출된 decision lineage의 known PIT/integrity failure를 뒤늦게 weight 0으로 지울 수 없다. N/A 또는 unrelated unconsumed input과 이 경우를 구분한다. All-zero active axis는 유효 score를 만들 수 없다. Current candidate zero validation 및 frozen profile 범위는 그대로 보존하고 확장은 별도 승인을 요구한다.

**Why / alternatives.** Zero=requiredness removal이면 사용자 조정이 품질·PIT 검증을 우회할 수 있다. 모든 비사용 optional source를 무조건 계산하면 의미 없는 source 의존성과 outage를 늘린다. Method-required/included lineage와 proven out-of-scope 자료를 구분해야 한다.

**Impact / approval.** Legacy/current tree 동작은 그대로다. 미래 WeightOverride의 validity binding과 active denominator에 영향을 주므로 정책 원칙은 D3-P/equivalent, 실제 wiring은 별도 미승인 gate다. Same evaluator와 namespace isolation을 유지한다. Override 뒤 Official config, score, board, record 및 historical evidence hash가 불변임을 runtime migration에서 검증해야 한다.

## Alternatives와 영향 검증

전체 후보 A fail-closed / B available-weight renormalization / C partial+coverage / D guarded Hybrid의 14개 영향 비교는 [POLICY_COMPARISON.md](POLICY_COMPARISON.md)에 있다. 현재 production flow와 reason별 근거는 [CURRENT_BEHAVIOR.md](CURRENT_BEHAVIOR.md)에 있다. 격리된 수치 비교는 [SIMULATION.md](SIMULATION.md) 및 `simulation_results.json`에서 제공한다.

이 시뮬레이션의 role assignment는 **illustrative**, 기존 Q/G/V weights와 scores는 fixture 입력이다. Official role table, numeric cutoff/default, 새 confidence method가 아니다. Ranking impact는 synthetic counterexample이며 실제 전체 Leaderboard 또는 시장 universe의 rank delta가 아니다. Real PIT/OOS, empirical sparse/young/financial-sector bias 및 full integration acceptance는 NOT_RUN이다.

## 이후 dependency와 migration gate

1. **지금:** M1–M5 정책 원칙 승인 또는 수정. 구현은 포함하지 않는다.
2. Method/profile별 factor role·applicability·reason admission·consumer binding을 작성하고 영향 검증한다. 승인되지 않은 role default, industry taxonomy, history cutoff를 채우지 않는다.
3. G 3–5Y 의미와 EPS→FCF fallback을 함께 연구하되 별도 조항으로 결정한다. G 입력 기간 의미가 insufficient-history/requiredness binding의 선행조건이다.
4. V normalization/applicability와 V metadata를 별도 정책으로 검토한다. Confidence 방법은 normalization의 대용이 아니며 metadata mapping은 병렬 설계 가능하다.
5. New composite participating axes·completeness·comparison meaning을 결정한다. M4가 complete axis의 선행조건이며 V는 여전히 current composite에 들어가지 않는다.
6. C-24/C-30 registry authority와 factor-node map을 해결한 뒤 WeightOverride runtime scope를 별도 승인한다. Official/Personal storage/cache/result keys와 PIT config vintage를 검증한다.
7. 별도 승인된 새 version의 구현·Old/New delta·consumer regression·real PIT/OOS를 거쳐 promotion/migration/merge를 각각 판단한다. Holdout은 자동 소비하지 않는다.

Legacy 계산 version과 byte-preserved golden/history는 계속 exact replay 대상이다. Intentional delta는 승인된 새 version·새 snapshot/record로만 기록하고 old history를 overwrite하지 않는다. Partial admission, N/A denominator, integrity blocking, ranking 변경은 production 승인 없이 적용하지 않는다.

## 승인 표면 / 기록 상태

| ID | Class | 현재 상태 | 승인 시에도 포함되지 않는 것 |
|---|---|---|---|
| QCC-P01.M1 | D3-P/equivalent policy | PROPOSED / NOT_APPROVED / INACTIVE | factor별 역할·predicate default 선택, runtime |
| QCC-P01.M2 (QCC-P02 연계) | D3-P/equivalent admission | PROPOSED / NOT_APPROVED / INACTIVE | production input/PIT guard 변경, source/fallback 실행 |
| QCC-P01.M3 | D3-P/equivalent arithmetic | PROPOSED / NOT_APPROVED / INACTIVE | legacy score 수정, 새 weights/normalization, migration |
| QCC-P01.M4 | D3-P/equivalent validity/ranking | PROPOSED / NOT_APPROVED / INACTIVE | board 재계산, grant/Official 승격, confidence formula |
| QCC-P01.M5 | D3-P/equivalent validity/config | PROPOSED / NOT_APPROVED / INACTIVE | candidate 제약 변경, WeightOverride runtime wiring |

Current audit/simulation/doc work는 기존 권한의 D1, conservative interpretation·recommendation은 D2다. **추천안을 production domain policy로 채택하는 것은 D3다.** 승인 기록은 [DECISION_REGISTER.md](DECISION_REGISTER.md)에 append해야 하며 추천을 승인으로 표시하지 않는다.

사용자가 선택할 다음 한 단계는 **M1–M5 guarded Hybrid 정책 원칙 묶음을 승인할지, 수정할지**이다. 그 결정 없이 G/V/composite/runtime wiring 또는 PR #44 merge로 진행하지 않는다.
