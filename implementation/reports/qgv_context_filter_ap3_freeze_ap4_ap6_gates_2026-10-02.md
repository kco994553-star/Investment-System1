# AP3 recorded — Contract Freeze assessment and AP4/AP5/AP6 approval gates

Status: AP1/AP2/AP3 USER_APPROVED. AP4/AP5/AP6 NOT APPROVED. No implementation/source/test/grant/Holdout/merge activity.

## 1. Current baseline and AP3 recording

Fresh GitHub branches/open PRs were audited before this record. Canonical remains b8e39a2196a6d7794a04a0cd5393c68329e126ca; QGV/Entity/Producer/P01/Macro/Technical input/model/session/RIG/SEC/Leaderboard/Web/Language/Track C component heads match the previous review. Existing PR4–18 (the existing 14 PRs) remain Draft/Open with unchanged heads. Full names/SHAs are in [AP3 evidence](qgv_context_filter_ap3_approval_2026-10-02.json).

The separate Track C evidence branch moved from 862955a to ebe54827862f92dc5ba25ee632009a316a71e508: A6 method Q1–Q6 now conditionally approved there. This is a scoped policy-authority change, not a QGV Context formula/config grant. Frozen feature source ff78c4f is unchanged, numeric configuration is pending, Holdout unconsumed. AP1–AP3 contracts do not conflict with that delta and do not inherit that work's implementation authorization.

AP3 approval recorded at actual current KST **2026-10-02T20:48:42+09:00**. [Decision Register](qgv_context_filter_decision_register.md) appended QCF-AP3; no prior text replaced. Earlier AP3 pending statements remain historical; the new explicit entry supersedes their status only. AP1/AP2 evidence is unchanged. Original v0.3 proposal/package and v0.4 review remain unchanged. Commits: evidence 280903a; appended register 36bcb2b.

## 2. Freeze reassessment

| Scope | DESIGN_FREEZE_READY | Meaning / remaining limits |
|---|---|---|
| Common Context AP1 | YES | Approved time/freshness/conflict/PIT/interpretation admission |
| Model Suitability AP1/AP2 | YES | Approved issuer/segment, label admission and axis-local suitability; actual taxonomy/rubric absent => explicit unknown/not assessed |
| QGV Filter AP1/AP2/AP3 | YES | CF16 priority + CF17 complete-configuration contract approved; incomplete actual config remains POLICY_BLOCKED |
| Combined AP1–AP3 Contract | YES, scoped | Contract-level result admission and closed states are consistent; no actual numeric/rubric activation or software completion |
| P1 common interface design | INTERFACE_DESIGN_FREEZE_READY | Concrete [interface document](qgv_context_filter_p1_interface_design_2026-10-02.md), separate source/authority-based documentary audit; not external attestation or executed tests |
| All four feature contracts + publication | NO | AP4 Macro / AP5 News / AP6 publication scope still unapproved |
| P1 implementation / runtime validation | NOT STARTED | No implementation permission; no durability/replay guarantees established by a design document |

Contract Design Freeze is distinct from complete result policies and implementation Freeze. This report records readiness and the exact design reference; it does not promote any missing taxonomy/config/rubric to an active result policy.

## 3. P1 interface and audit result

The P1 document binds RevisionRef/SubjectRef/TimeBasis/PolicyRef/QualifiedState/DependencyRef; immutable envelope, Assessment, FilterDefinition, ThresholdConfiguration and SnapshotManifest; read requests/responses; single-writer staging/CAS commit; exact-hash raw history resolution; replay and invalidation failure states. It reuses RIG identities, RawDatasetStore history and Producer serialization rather than duplicating engines/stores. P01 publication remains separate.

Independent derivation pass checked approved CFs and existing source contracts against the proposed interface. Documentary counterexamples cover late-computed judgment, crossing availability interval, stale pointer after failed refresh, changed raw history, missing pinned bytes, missing company observation, duplicate identity with conflicting content, policy/clock cache identity, segment/issuer mismatch, bank axis isolation, condition order invariance, unspecified comparison boundary, provisional-factor promotion and withheld publication. No new policy selection was needed. This is a separate audit pass by the same assistant, not an external independent reviewer or a software test run.

P1 remains single-writer. The concrete design can be pinned, but consumer implementation/parallelization remains forbidden until separate implementation permission and the P1 interface Freeze/adoption gate. P2/P3 domain payload admission awaits AP4/AP5; P6 publication activation awaits AP6 plus actual support/grant. No new Macro/News functionality was designed.

## 4. AP4 — first user approval gate (Macro)

AP4 remains **READY_FOR_USER_APPROVAL / NOT APPROVED**. Recommendation: **CF04-B + CF05-B**, unchanged from v0.3.

| CF / exact decision | Option A | Option B / recommendation | Result impact / counterexample |
|---|---|---|---|
| CF04: episode candidate/phase eligibility and later curation | Reuse a later completed catalog across reconstructions | B: decision candidates/phase require assertions admissible at that decision time; later curation/outcome only retrospective; catalog revisions immutable | Turning point known only after T: A may select the episode because its outcome is known; B leaves T phase unresolved. Under approved AP1, A cannot silently make the hindsight result strict PIT or AS_RECORDED |
| CF05: four-layer aggregation, BROKEN and applicability | Allow a reviewed provisional aggregate from partial layers | B: preserve State/Cause/Transmission/Constraint findings; aggregate only with approved sufficiency rubric/reviewer evidence, otherwise NOT_ASSESSED; BROKEN requires explicit counterevidence; applicability separate | Same growth/inflation direction but unknown cause/constraint: A can yield a provisional resemblance label if separately authorized; B does not produce an aggregate. Missing mechanism evidence alone is not BROKEN |

Why B/B: preserves decision-time candidate membership and prevents outcome-informed phase selection; retains useful component evidence while refusing an unsupported aggregate. AP1's time/rubric authority is reused and not reapproved. No similarity score, cutoff, layer weights, required-layer rubric or catalog entries are created.

Exact CF approval targets from v0.3:

> CF04-B를 승인한다. decision용 episode 후보·phase는 평가 시점에 적격한 assertion만 사용하고, 후일 curation·outcome은 retrospective 설명으로 분리한다. catalog 수정은 새 revision이며 과거 snapshot을 덮어쓰지 않는다.

> CF05-B를 승인한다. 4-layer finding을 보존하고 승인된 종합 rubric·필수 근거·review가 없으면 NOT_ASSESSED로 유지한다. BROKEN은 기존 메커니즘에 대한 명시적 반증으로만 판단하며, 해결책 적용 가능성을 유사성에서 자동 도출하지 않는다.

Exact next user approval sentence:

> AP1을 전제로 AP4를 CF04-B, CF05-B로 승인한다. 각 CF의 v0.3 승인 문장 범위에 한정하여 episode 선정 시점과 종합판정 admission을 승인한다. 실제 catalog 선정·필수 layer/rubric 내용·similarity 수치·계산식·calibration·구현·테스트·publication grant·Holdout 소비·merge는 승인하지 않는다.

Unblocks: P0/P2 episode eligibility/curation/aggregate admission and P7 historical-family contract dependencies. Still blocked: actual catalogs/vintages/layer evidence, sufficiency rubric, actual methodology/configuration, implementation, AP5/AP6. If B/B is approved, Macro contract Freeze may be ready with missing-rubric NOT_ASSESSED; actual Macro analogy results are not thereby complete.

## 5. AP5 — prepared later gate (News)

AP5 is prepared for sequential review, **NOT APPROVED; no approval requested before AP4**. Recommendation remains CF06-A, CF07-A, CF08-B, CF09-A, CF10-B, CF11-B, CF12-B.

| CF / exact target | Alternatives | Recommendation and reason | Result impact / counterexample |
|---|---|---|---|
| CF06: economic-event linkage admission | A explicit same-event ref + reviewer evidence; B semantic linkage candidates from issuer/time/topic, still no automatic grouping | A: preserve existing dedup and require evidence of economic-event sameness | Same-day contract and new product can be different events; A keeps separate reaction attribution. B remains candidate only under existing semantic-grouping block |
| CF07: unsupported existing event kind | A preserve claim/evidence but event-level NOT_EVALUABLE; B defer a typed extension to later separate work, currently inactive | A: exact support boundary without RIG enum changes | Earnings claim cannot be relabelled CONTRACT to become evaluable. Both choices currently yield no event-level result for unsupported kinds |
| CF08: expectation/surprise basis | A choose a registered representative expectation type; B preserve separate guidance/consensus/etc comparisons and require exact expectation_kind | B: no automatic representative surprise; metric/period/basis/kind/formula required, range/denominator not guessed | Actual below guidance but above consensus yields opposite signs; B preserves both and blocks an ambiguous condition |
| CF09: reaction anchor/window/overlap | A preregistered explicit anchor/window/session/benchmark/basis; B retain possible-anchor sensitivity observations without a single direction | A: contract complete before single observation; TOO_EARLY versus unavailable distinguished | Uncertain intraday/after-close timing reverses the chosen session return; A does not guess. Overlap is observed change, not unique causal effect |
| CF10: priced-in aggregate sufficiency | A limited label from partial evidence; B approved rubric/review defining applicable required E1–E4 evidence | B: absent contract/needed evidence UNKNOWN, direct conflict retained | Pre-rise and post-event no reaction without expectation baseline is not enough to prove priced-in. No percentage/score added |
| CF11: public reaction population/origin | A aggregate populations under an explicit contract; B keep population/period/coverage separate | B: unknown origin independence remains UNKNOWN; no all-society sentiment extrapolation; missing rubric NOT_ASSESSED | Many echoes of one positive story plus critical social sample cannot be counted as independent positive majority |
| CF12: reality absence/nonconfirmation/refutation | A deadline-passed without confirmation => NOT_CONFIRMED; B due/coverage/confirmation/falsifier contract required | B: due-before TOO_EARLY, due-after missing data NOT_ASSESSED; explicit failed criterion versus counterevidence distinguished | Missing expansion filing after due date is not cancellation; an explicit cancellation can support CONTRADICTED. Partial confirmation requires predefined subclaims |

All alternatives remain subject to AP1 and existing RIG/Technical contracts; they do not authorize source guessing, future vintages, automatic interpretation or a new event ontology. No approved rubric is supplied by choosing B for an admission rule.

Exact later package sentence (not approved here):

> AP1을 전제로 AP5를 CF06-A, CF07-A, CF08-B, CF09-A, CF10-B, CF11-B, CF12-B로 승인한다. 각 CF의 v0.3 승인 문장 범위에 한정한다. 기존 RIG/dedup은 재승인하거나 변경하지 않으며, event ontology 확장·실제 window/anchor 설정·surprise 계산식·priced-in/public rubric·claim별 criteria·새 공급자 계약·구현·테스트·publication grant·Holdout 소비·merge는 승인하지 않는다.

Unblocks: P0/P3 supported-event boundaries, expectation comparison admission, reaction/public/priced-in/reality status contracts; P5 consumes only eligible stored outputs. Still blocked: actual sources/vintages/calendar/window/benchmark configs, expectation formulas, sufficient-evidence rubrics and claim criteria, unsupported event kinds, implementation and publication. Existing RIG, SEC and Technical source remain unchanged.

## 6. AP6 — prepared later gate (Publication)

AP6 remains **NOT APPROVED**. Recommendation remains **CF20-B**. Existing P01-A–J, grant NONE, supported extractor limitations, source withholding and schema-1 states are already authoritative; no reapproval of those rules is requested.

| Exact target | Option A | Option B / recommendation | Result impact |
|---|---|---|---|
| Future Context display approval-request scope | Defer Context display outside current supported payload/extractor scope | Require exact output hash, display fields and reference disclosure scope in a future authorization request; no automatic source-grant inheritance | Currently both yield no new Context publication. B makes future review scope explicit but does not issue a grant or implement an extractor/client |

Counterexample: a withheld QGV score is transformed into “quality condition passed.” Omitting the number does not make this derivative fact publishable. A future output grant cannot silently override upstream withholding. This boundary already follows P01 and is not reopened by AP3.

Exact later approval sentence (not approved here):

> CF20-B의 향후 Context 표시 승인 요청 단위만 승인한다. 정확 output hash·표시 필드·참조 disclosure 범위를 명시하도록 하고 기존 source grant를 자동 상속하지 않는다. P01 기승인 정책은 재승인하지 않으며, 지금 grant 발급·extractor/client 확장·publication 활성화·구현·테스트·merge를 승인하지 않는다.

Unblocks: P0/P6 future authorization-scope documentation. Still blocked: actual grants, supported Context extractor/client, applicable disclosures, upstream integration and P8 execution evidence. No publication is attempted.

## 7. Remaining dependency and stop

P0 approval records now cover AP1–AP3. P1 interface design is concretized and document-audited; its implementation stays single-writer and not started. AP4 is the first remaining domain-policy approval; AP5/AP6 are prepared only. Actual result-affecting values/rubrics/calibration are not defaults and remain explicit activation blockers.

No implementation/source changes, test implementation/execution, publication grant, Holdout consumption or merge. No implementation/validation progress percentage is inferred from old system code. Contract readiness does not imply full four-feature completion.

**Stop at AP4 user approval. Do not automatically approve AP4/AP5/AP6.**
