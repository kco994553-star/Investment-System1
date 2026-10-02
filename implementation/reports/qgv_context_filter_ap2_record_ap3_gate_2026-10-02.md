# QGV Context & Filter — AP1/AP2 recorded; AP3 approval gate

Review date: 2026-10-02 KST. Status: **AP1 USER_APPROVED / AP2 USER_APPROVED / AP3 READY_FOR_USER_APPROVAL (NOT APPROVED)**.

This is a new, scoped, history-preserving review record. Existing proposal, v0.3 approval package and v0.4 review are unchanged. No implementation, tests, new taxonomy/cutoff/rubric/formula, publication grant, Holdout access or merge is performed or authorized here.

## 1. Actual approval record and authority

Approval processing clock: **2026-10-02T20:37:34+09:00** (actual current KST read from the environment).

- [Decision Register](qgv_context_filter_decision_register.md): QCF-AP1 and QCF-AP2.
- [Scoped approval evidence](qgv_context_filter_ap1_ap2_approval_2026-10-02.json): exact user approval sentences, exact clause scope, exclusions, original-document hashes and GitHub branch pins.
- AP1 is imported from the prior explicit user approval; its precise original message time is unknown and remains unset. The processing clock is not backdated into an invented AP1 approval time.
- AP2's repeated identical approval messages are confirmations of one scoped decision, not multiple policy changes.
- Evidence commit: `9874d2315221d65d6c58fd5e5e4a5a5bc298d85e`.
- Register commit: `79d610fc3dbd12d11257a036f6642f9fa7cea31f`.
- Both files were reread from GitHub at the register commit and matched the submitted contents exactly.
- Documentation branch: `docs/qgv-context-policy-approvals`, created from canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`. Canonical was not merged or edited.

The user's current instruction authorizes these approval documentation writes. It does not activate the earlier P0–P8 implementation plan. No source change is included.

## 2. Fresh GitHub audit after AP1/AP2 recording

GitHub branches and open PRs were fetched again after the register writes. Check clock: **2026-10-02T20:40:04+09:00**. Only this documentation branch changed during recording; component heads remained unchanged. PR #4/#5/#6/#7/#9/#10/#11/#12/#13/#14/#15/#16/#17/#18 remained Draft/Open with the same heads.

| Component | Current short SHA | Compared with v0.4 |
|---|---|---|
| Canonical | b8e39a2 | SAME |
| QGV Real Producer | 5eec129 | SAME |
| Entity Metadata | a013f1c | SAME |
| Producer Infrastructure | f8af596 | SAME |
| P01 Publication | 21039a0 | SAME |
| Macro | 61d3352 | SAME |
| Technical input | a2e0790 | SAME |
| Technical model | ce58704 | SAME |
| Technical session | 2c088ce | SAME; previous docs-only delta from v0.3 already audited |
| RIG/News | 8bb990b | SAME |
| SEC disclosure | ef65caa | SAME |
| Leaderboard | 0d48d86 | SAME |
| Web MVP | a4e49c8 | SAME |
| Language/Search | eda65bf | SAME |
| Track C feature source | ff78c4f | SAME |

Full SHAs are in scoped evidence. [Branches](https://api.github.com/repos/kco994553-star/Investment-System1/branches?per_page=100) and [open PRs](https://api.github.com/repos/kco994553-star/Investment-System1/pulls?state=open&per_page=100) were the live sources, not cached conversation status.

Additional side-branch findings:

- [4514810](https://github.com/kco994553-star/Investment-System1/commit/451481088327b8e2953dc3d27d21d576daffaa8e) adds Track C A6 partial approval evidence and appends its register/handoff. This is a real policy-authority update within Track C, **not merely a formatting change**. It leaves the Frozen source, actual test form/numeric configuration and Holdout boundary unchanged. It neither supplies nor approves a CF17 threshold configuration. It causes no conflict with AP1/AP2 or the proposed AP3 contract.
- [f415615](https://github.com/kco994553-star/Investment-System1/commit/f4156150022bbc0ce18948c6bc949ff01a194a7d) is a historical producer-readiness report/probe on a separate branch. Its older pins and readiness claims do not override current component contracts. No probe was executed in this review.

No result-affecting conflict requiring a new QGV Context policy choice was found. No existing Frozen contract needs alteration.

## 3. Approved-scope consistency and counterexample review

These are documentary counterexample checks, not implemented or executed tests.

| Case | Approved-contract consequence | Preserved boundary |
|---|---|---|
| Conglomerate: issuer primary differs from software segment | The issuer industry condition uses the dated provider's issuer classification; segment evidence cannot make the issuer software MATCH. Missing designated classification/crosswalk remains UNKNOWN | Metadata aliases/user groups do not become PIT taxonomy; QGV peer factors are not recalculated |
| Product exists; revenue/capex contribution unknown | PRODUCT_BACKED fact can be preserved. No HIGH exposure label follows without its approved rubric and reviewer evidence; missing magnitude is NOT_ASSESSED, not LOW | Evidence kind and intensity remain distinct |
| Bank: Q assessment admissible; V adapter absent | Preserve Q's separately justified assessment; G remains independently assessed. Without its rubric, V remains NOT_ASSESSED with limitation evidence | No automatic Q/G LIMITED; FINANCIAL ROIC N.A. does not prove a validated bank valuation adapter |
| Confirmed identity/hash/PIT integrity failure | Relevant assessment INVALID; if required for the Filter evaluation to be valid, CF16 proposes NOT_EVALUABLE | No laundering invalid evidence into ordinary missingness |
| Integrity sound; required company evidence missing | NOT_ASSESSED upstream and condition UNKNOWN downstream | Not INVALID; mandatory UNKNOWN is not a pass/fail |
| Current stale/reassessment pending/required freshness unresolved | Condition UNKNOWN under AP1; historical replay uses its original clock/policy | No new TTL or stale-result fallback |
| Competing direct claims without explicit correction | Unresolved under CF03; no automatic source-type winner | Retraction is not proof of the opposite proposition |

Existing QGV scores, 20 factors, attractiveness, Leaderboard ranking, RIG, Producer Infrastructure and Track C Frozen source are preserved. Context consumes existing outputs and carries their limitations; upstream confidence/producer PASS is not blanket approval of a new Context label.

## 4. Model Suitability Contract Freeze reassessment

**DESIGN_FREEZE_READY = YES, within the approved AP1/AP2 contract scope.**

Approved now: issuer/segment separation; evidence-kind versus derived label admission; independent Q/G/V suitability; integrity failure versus insufficient evidence; AP1 time/freshness/conflict/reviewer boundaries.

Still absent and not invented: actual taxonomy provider/value/crosswalk, industry-specific requirements/rubrics, label sufficiency criteria, adapter validation, operational data and numeric configurations. Their absence has defined closed states (UNKNOWN / NOT_ASSESSED / INVALID where integrity fails), so it need not block this limited contract Freeze. It does block actual result-label activation where those dependencies are required.

This is a readiness judgment, not software completion, full result-policy completion, an implementation-interface Freeze, or publication permission. Common Context remains ready within AP1 scope. **QGV Filter Contract remains WAITING_AP3_APPROVAL**, because AP2's semantic dependency is now resolved but AP3 itself is not approved.

## 5. AP3 recommendation remains valid after AP1/AP2

Recommendation remains **CF16-A + CF17-B**. AP2 supplies the Company/Suitability input meaning without changing the proposed Filter aggregation or computation-admission contract. No new formula, threshold, taxonomy value or rubric is needed to review these contracts.

| Decision | Recommended option | Alternative in v0.3 | Actual result difference |
|---|---|---|---|
| CF16 state aggregation | A: invalid evaluation → mandatory confirmed failure → mandatory uncertainty → conditional reasons → MATCH; guard unconstrained definitions | B: invalid evaluation → mandatory uncertainty → mandatory confirmed failure; preferred conditions informative only | Mandatory NO_MATCH + UNKNOWN: A=NO_MATCH retaining UNKNOWN; B=INSUFFICIENT_EVIDENCE. Mandatory MATCH + preferred NO_MATCH: A=CONDITIONAL_MATCH, B does not downgrade solely for the preference |
| CF17 computation contract | B: preserve existing comparison-mode contracts, permit comparison only with complete version-pinned approved configuration | A: contract ABSOLUTE only first; other modes remain design-deferred | A leaves relative comparisons unavailable. B also blocks them while config is incomplete, but allows them once the separately approved complete config exists. Neither option approves actual numeric values or a percentile method |

CF16-A preserves a conclusive counterexample to an AND condition without erasing unresolved evidence. CF17-B closes reproducibility/failure semantics across the already designed modes while keeping actual configuration choices outside this approval. The alternatives are not silently selected or implemented.

## 6. Exact CF16-A approval target

The priority below is unchanged from v0.3 and the user's v0.4 review request:

1. Definition/identity/hash/PIT failure that makes the evaluation invalid → **NOT_EVALUABLE**.
2. Confirmed NO_MATCH in CRITICAL_REQUIRED or REQUIRED → **NO_MATCH**, retaining other UNKNOWN/PARTIAL states and evidence.
3. Mandatory UNKNOWN, mandatory N.A. without waiver, or CRITICAL_REQUIRED PARTIAL_MATCH → **INSUFFICIENT_EVIDENCE**.
4. REQUIRED PARTIAL_MATCH, or PREFERRED NO_MATCH/PARTIAL_MATCH/UNKNOWN/N.A. without waiver → **CONDITIONAL_MATCH**.
5. All required conditions MATCH with no higher-priority reason → **MATCH**. INFORMATIONAL condition status does not change company_result.
6. Before aggregation, if no CRITICAL_REQUIRED/REQUIRED condition remains after explicit waiver → **NOT_EVALUABLE**, reason=**UNCONSTRAINED_DEFINITION**.

The last guard counts the required conditions remaining after explicit waiver. It does not silently remove unwaived N.A. conditions. It is a structural precheck, not a newly chosen numeric threshold. Invalid/unconstrained causes are preserved rather than inventing a new rule for discarding one of several reasons.

| Counterexample | Result under CF16-A |
|---|---|
| REQUIRED NO_MATCH + mandatory UNKNOWN | NO_MATCH; UNKNOWN preserved |
| REQUIRED NO_MATCH + REQUIRED or CRITICAL_REQUIRED PARTIAL | NO_MATCH; PARTIAL preserved |
| Mandatory MATCH + mandatory UNKNOWN | INSUFFICIENT_EVIDENCE |
| Mandatory MATCH + REQUIRED PARTIAL | CONDITIONAL_MATCH |
| Mandatory MATCH + CRITICAL_REQUIRED PARTIAL | INSUFFICIENT_EVIDENCE |
| Mandatory MATCH + PREFERRED NO_MATCH | CONDITIONAL_MATCH |
| All MATCH; at least one required condition remains | MATCH |
| All N.A.; unwaived mandatory conditions remain | INSUFFICIENT_EVIDENCE |
| All waived; no required condition remains | NOT_EVALUABLE / UNCONSTRAINED_DEFINITION |
| Preferred-only, even if all preferred MATCH | NOT_EVALUABLE / UNCONSTRAINED_DEFINITION |
| Invalid definition + otherwise MATCH | NOT_EVALUABLE |
| Evaluation input PIT-invalid + otherwise MATCH | NOT_EVALUABLE |
| Mandatory MATCH + INFORMATIONAL NO_MATCH/UNKNOWN/PARTIAL/N.A. | MATCH |

Order invariance follows from set predicates (existence/all) over the same pinned conditions and waiver evidence, not a first-input-wins rule. Every permutation of the same inputs therefore has the same company_result in this contract. No software test or implementation was created to claim this documentary result.

## 7. Exact CF17-B approval target

Approve only the calculation contract: a configuration must specify and version-pin all applicable meaning-bearing parameters before comparison. No default fills an unresolved choice.

Required meaning includes:

- Metric exact path, unit, direction, methodology maturity/admissibility, comparison mode.
- Universe/reference membership, PIT identity, taxonomy/peer revision, history span, measurement time.
- Formula ID/version, percentile/quantile convention, tie policy, boundary inclusion, rounding/precision.
- Missing/N.A./outlier/negative handling and support requirement.
- HYBRID/MULTI_CONTEXT constituent references and combination logic, including missing constituent semantics.
- Config hash, approval reference, scope, calibration provenance and invalidation rules.

Parameters not applicable to a mode cannot be confused with unresolved applicable parameters. This approval does not choose a formula/convention, value, span or support cutoff. The actual absolute boundary parameter must also exist in an activated config; the symbol θ is not an approved value.

**Incomplete config → definition validation failure / POLICY_BLOCKED (NOT_EVALUABLE if reporting evaluation status). Sound configuration with normal company-level missing data → condition UNKNOWN.** These failures must remain separate.

| Counterexample | Contract consequence; no new policy choice |
|---|---|
| x=θ with > versus >= | Opposite membership at equality is possible; operator/boundary must be explicit. Neither is chosen here |
| Ties at percentile boundary | Convention/tie policy can change membership; absent policy blocks configuration instead of picking by input/issuer order |
| Peer-set revision changes | Same raw value can change relative result; pin revision and retain old snapshot |
| Universe membership changes | Reference distribution can change; pin dated membership rather than use current members retrospectively |
| Historical span changes | Relative result can change; pin span/time/formula identity |
| PROVISIONAL factor used as validated | Preserve upstream maturity; do not fabricate validation. Admissibility missing is a config defect; false validated identity is a contract/integrity defect |
| One HYBRID constituent missing | Missing ref/combination policy is config failure. Normal company data missing is UNKNOWN at that constituent; combine only under a separately approved complete rule, with no automatic omission/reweighting |

AP1/AP2 do not fill these remaining configuration fields. Track C A6 partial approval also does not supply a CF17 calibration grant or statistical/numeric configuration.

## 8. What AP3 would and would not approve

| Would approve | Would NOT approve |
|---|---|
| CF16-A priority and unconstrained-definition guard | Q/G/V rescore, attractiveness change, new Filter Score, ranking/re-ranking |
| Preservation of condition states/reasons/evidence and order-invariant company_result | Treating UNKNOWN as pass/fail; automatic N.A. waiver or auto-relax |
| CF17-B complete configuration requirements and missing-config failure semantics | Actual threshold, percentile method/value, TTL, confidence/similarity cutoff, formula selection |
| Configuration failure versus normal company missingness | Calibration values/execution, validation promotion, Track C Frozen changes, Holdout use |
| Read-only deterministic consumption of stored QGV/Classification/Checklist/Suitability/Industry/Evidence status | Query-time LLM; new taxonomy provider/value; rubric/requirement contents |
| P0/P5 contract-policy blockers resolved within that scope | Implementation, test implementation/execution, publication grant, merge, AP4/AP5/AP6 approval |

The Filter outputs only membership/status and reason/evidence. CONDITIONAL_MATCH is not silently relabelled MATCH or used to create a new ranking. Original stored QGV and upstream status are preserved.

## 9. Remaining blockers and dependency audit

| Stage | Blocker after AP1/AP2 | What AP3 approval would change |
|---|---|---|
| Model Suitability Contract Freeze readiness | No remaining policy-selection blocker within AP1/AP2 scope | No further AP3 approval needed for Suitability's own contract |
| QGV Filter Contract Freeze readiness | AP3 not approved | CF16/CF17 policy blocker resolves; ready within the defined closed-state contract scope |
| P1 implementation interface | Single-writer schema/interface Freeze and separate implementation permission still required | No implementation permission; no P2/P3/P4/P5 parallel implementation before P1 interface Freeze |
| Actual Company label output | Taxonomy, requirements/rubrics, review evidence, data and adapter validation as applicable | None automatically supplied |
| Actual threshold comparison | Complete scoped approved config, data support and applicable calibration provenance | No values/conventions/config automatically supplied |
| Macro/News conditions | AP4/AP5 and their own output-policy dependencies | No automatic approval; preserve unresolved/inactive scope |
| Publication / Web output | AP6 scope, existing P01 supported shape and actual grants | No grant; withholding cannot be bypassed via Filter reasons |
| P7/P8 | Approved interfaces and separate validation/integration authorization/evidence | Only contract preparation dependency resolves; no execution/Holdout authority |

P0–P8 package structure remains appropriate. Critical design path is now **AP3 user decision → QGV Filter Contract Freeze readiness confirmation**. Future implementation still requires separate authority, P0/P1 interface work, then applicable P2/P3/P4/P5 consumers and P6/P7/P8 integration. No work is started along that implementation path here.

AP4/AP5/AP6 remain unapproved. AP1/AP2 selections are consistent with their existing proposed dependencies and do not require new Macro/News functionality. A different future AP3 selection would require rechecking affected aggregation contracts before use.

## 10. Exact next user decision — AP3 only

Recommended approval sentence:

> AP1/AP2 적용을 전제로 AP3를 CF16-A와 CF17-B로 승인한다. 각 CF의 v0.3 승인 문장 범위에 한정하며, CF16의 명시 우선순위 1–6과 조건별 상태·사유 보존, CF17의 완전한 version-pinned configuration 요구 및 미완성 configuration 차단 계약만 승인한다. 실제 taxonomy 값·cutoff·requirement/rubric 내용·threshold·percentile 방식/값·TTL·confidence/similarity cutoff·계산식 선택·calibration 값/실행·구현·테스트·publication grant·Holdout 소비·merge는 승인하지 않는다.

The sentence does not approve AP4/AP5/AP6 or fill any absent result policy. It has **NOT** been approved by the user in this record.

**Stop state: AP1/AP2 recorded and USER_APPROVED; Model Suitability Contract DESIGN_FREEZE_READY=YES; AP3 READY_FOR_USER_APPROVAL; QGV Filter Contract WAITING_AP3_APPROVAL.**
