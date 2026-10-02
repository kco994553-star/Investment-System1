# QGV Context & Filter — Decision Register

History-preserving approval record. Created 2026-10-02T20:37:34+09:00 (KST).

Scope: documentation only, branch `docs/qgv-context-policy-approvals`. Canonical baseline `b8e39a2196a6d7794a04a0cd5393c68329e126ca` is unchanged. No canonical merge, implementation, test execution, publication grant or Holdout access is authorized by these entries.

This new scoped register preserves the original proposal, v0.3 approval package and v0.4 review unchanged. Their historical PROPOSED/READY statuses describe the state at those reviews; these later entries supersede only the approval status of the exact clauses below. No existing source document is rewritten. Later changes must be appended as separately scoped decisions, not silently overwrite these records.

Scoped authority: [AP1/AP2 evidence](qgv_context_filter_ap1_ap2_approval_2026-10-02.json). Exact original-document byte hashes and component pins are recorded there. These hashes identify the reviewed local originals; the originals have not been modified or implicitly incorporated as new repository policy.

## QCF-AP1 — prior explicit user approval imported

Status: **USER_APPROVED** (previous review: APPROVED_BY_USER_IN_THIS_REVIEW).

Recorded at: **2026-10-02T20:37:34+09:00**. The original AP1 message's exact time was not captured; it is intentionally not invented or replaced by this recording time. This is not an AP1 reapproval.

> AP1을 CF01-A, CF02-A, CF03-B, CF18-B, CF19-B로 승인한다. 각 CF의 v0.3 승인 문장 범위에 한정하며 수치 설정·구현·테스트·publication grant는 승인하지 않는다.

- **CF01-A:** 시간 모드는 명시적으로 선택하고 기본값을 두지 않는다. AS_RECORDED는 당시 저장·완료된 판단만 사용하며, 공개시각의 가능한 범위가 T를 걸치면 해당 증거를 당시 이용 가능했다고 판정하지 않는다.
- **CF02-A:** 현재 조건 평가에서 stale·재평가 대기·필요 신선도 정책 미확정은 UNKNOWN으로 처리한다. 유효한 static reference의 freshness N.A.는 별도로 허용하며, 과거 재생은 당시 clock과 정책을 사용한다. 신규 TTL은 승인하지 않는다.
- **CF03-B:** 명시적 정정 관계 외에는 source 유형만으로 충돌의 승자를 고르지 않는다. 직접 충돌·동시 상충 revision은 unresolved로 보존하고, 철회는 반대 명제의 증명이 아닌 근거 부적격 사유로 처리한다.
- **CF18-B:** strict PIT와 제한을 명시한 retrospective reconstruction의 적격 집합을 분리한다. restatement 또는 후일 모델 위험이 해소되지 않은 결과를 strict PIT·당시 실제 판단으로 승격하지 않는다.
- **CF19-B:** 해석·분류·범주형 confidence는 승인된 rubric과 지정 reviewer의 근거 기록이 갖춰질 때만 결과에 반영한다. 그 전에는 candidate/NOT_ASSESSED를 유지하며 confidence cutoff나 자동 해석 권한을 새로 부여하지 않는다.

Effect: AP1 common time/freshness/conflict/PIT/interpretation-admission policy blockers are resolved within those clauses. Actual rubric contents, confidence cutoff, automatic authority, numeric configuration, implementation and publication remain outside approval.

## QCF-AP2 — current explicit user approval

Status: **USER_APPROVED**. Depends on QCF-AP1.

Approval recorded at actual current KST: **2026-10-02T20:37:34+09:00**. This is the processing clock, not a fabricated chat delivery timestamp. Repeated identical AP2 approval messages confirm this one scoped decision.

> AP1 적용을 전제로 AP2를 CF13-A, CF14-B, CF15-B로 승인한다. 각 CF의 v0.3 승인 문장 범위에 한정한다. 실제 taxonomy 공급자·분류 cutoff·업종별 requirement/rubric 내용·구현·테스트·publication grant는 승인하지 않는다.

- **CF13-A:** company industry 조건은 명시한 dated taxonomy/provider/version의 issuer 분류를 사용하고, segment 근거를 issuer 전체로 승격하지 않는다. 지정 분류나 승인된 crosswalk가 없으면 UNKNOWN을 유지한다.
- **CF14-B:** evidence kind는 magnitude·quality 라벨과 분리한다. axis별 rubric·scope·cardinality·기간 및 reviewer 승인 없는 파생 label은 NOT_ASSESSED로 유지하고, 미공개 강도를 LOW로 대체하지 않는다.
- **CF15-B:** suitability는 Q/G/V 축별로 판정하고, adapter 부족이나 한 축의 한계를 다른 축의 감점·부적합으로 전파하지 않는다. 업종별 requirement와 label rubric이 확정되지 않은 축은 NOT_ASSESSED로 유지하며 INVALID는 평가 integrity 실패에 사용한다.

Effect: issuer/segment scope, classification-label admission, axis-local Q/G/V suitability and integrity-versus-insufficiency semantics are approved. **Model Suitability Contract DESIGN_FREEZE_READY = YES within AP1/AP2 scope.** This records readiness, not completed software, full result-policy activation or a frozen P1 implementation interface.

No actual taxonomy provider/value/crosswalk, cutoff, industry requirement/rubric content, adapter validation, numeric parameter, formula, implementation, test, publication grant or Holdout use is approved. Existing QGV/20 factors/attractiveness/Leaderboard ranking, RIG, Producer Infrastructure and Frozen Track C remain unchanged.

## Pending packages — no implied approval

| Package | Status | Dependency / remaining boundary |
|---|---|---|
| AP3: CF16-A / CF17-B | READY_FOR_USER_APPROVAL; NOT APPROVED | Aggregation and threshold computation contract only; actual values/formulas/configuration remain separate |
| AP4 Macro | NOT APPROVED | Existing proposal only; no new Macro design |
| AP5 News | NOT APPROVED | Existing proposal only; no RIG redesign |
| AP6 Publication | NOT APPROVED | No publication grant; existing P01 authority retained |

P0 documentation entries are now recorded on this docs branch. P1 remains a single-writer interface dependency: no P2/P3/P4/P5 parallel implementation before its interface Freeze and separate implementation authorization. AP1/AP2 approval does not authorize implementation.

## QCF-AP3 — explicit user approval recorded 2026-10-02T20:48:42+09:00

Status: **USER_APPROVED**. Depends on QCF-AP1 and QCF-AP2. Actual KST approval-processing clock: **2026-10-02T20:48:42+09:00**. Scope authority: [AP3 scoped evidence](qgv_context_filter_ap3_approval_2026-10-02.json).

> AP1/AP2 적용을 전제로 AP3를 CF16-A와 CF17-B로 승인한다. 각 CF의 v0.3 승인 문장 범위에 한정하며, CF16의 명시 우선순위 1–6과 조건별 상태·사유 보존, CF17의 완전한 version-pinned configuration 요구 및 미완성 configuration 차단 계약만 승인한다.
> 실제 taxonomy 값·cutoff·requirement/rubric 내용·threshold·percentile 방식/값·TTL·confidence/similarity cutoff·계산식 선택·calibration 값/실행·구현·테스트·publication grant·Holdout 소비·merge는 승인하지 않는다.

This appended decision supersedes only the earlier AP3 NOT APPROVED / READY_FOR_USER_APPROVAL status. All prior sections and AP1/AP2 evidence remain byte-preserved historical records; AP4/AP5/AP6 remain NOT APPROVED.

Approved: CF16-A priority 1–6, order-independent aggregation and original condition states/reasons; CF17-B complete, scoped, approved version-pinned configuration and POLICY_BLOCKED for incomplete configuration, distinct from normal company missing data (UNKNOWN).

Reassessment: **QGV Filter Contract DESIGN_FREEZE_READY=YES; combined AP1–AP3 Contract DESIGN_FREEZE_READY=YES**, limited to common admission, Company/Suitability and deterministic Filter contracts. This is not full four-function policy completion, actual configuration activation, implementation, publication or merge authority. Absent required configuration remains POLICY_BLOCKED; absent label rubric remains NOT_ASSESSED under its approved admission contract.

Authorized follow-on work is documentation-only P1 single-writer interface concretization and independent contract audit, plus preparation of AP4/AP5/AP6 choices. No result-affecting value/formula/rubric is filled and no AP4/AP5/AP6 option is implicitly approved.
