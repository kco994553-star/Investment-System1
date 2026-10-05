# Inactive Missing-Data regression and validation plan

**Status: DESIGN ONLY / INACTIVE / NO TEST IMPLEMENTATION / NO RUNTIME CHANGE.**

This plan receives the user's M1–M5 **policy-principle approval at 2026-10-05T09:57:52+09:00**. Approval of principles is not approval of factor-specific requiredness, new N/A definitions, a completeness/ranking method, production implementation, or migration. Historical proposals and simulation files keep their original **PROPOSED / NOT_APPROVED** status as records of when they were produced; this document does not rewrite them.

The planning baseline is `ed907b8f5a046008319cddecc6ef40b9bd6759dc`. PR #44 remains a separate inactive Common Contract publication, not a runtime migration grant. Root-scoped fresh GitHub/Handoff evidence controls any later HEAD or CI change; the values here are a planning checkpoint, not a claim that remote state is permanently fixed.

## Reused evidence, not newly executed validation

The existing `../simulation_results.json` records **102 synthetic cases × four alternatives = 408 policy outputs**, with **270 arithmetic/safety anchors PASS**. The root's original verification receipt is `../evidence/verification.json`. This task reads and maps that evidence; it **does not rerun the simulation, golden suite, contract suite, targeted tests, full regression, or GitHub Actions**.

The original `../../golden_cases.json` contains **71 historical characterization cases**. Its retained SHA-256 is:

`ed01c7f25e6a01b23c9f474b9f66f1f204828834bbdbc25efc286d96050c5040`

Existing contract tests cover score-neutral metadata/config manifests, synthetic Official/Custom object isolation, PIT reference shape/time boundaries, and score/version preservation. They are not tests of a new Missing-Data runtime. Existing real-data PIT/OOS remains **NOT_RUN**; Holdout remains **UNCONSUMED**. Existing simulation source-hash checks recorded 33 unchanged production source files; this plan does not present that old execution as a new hash-verification run.

The simulation's toy REQUIRED/OPTIONAL assignments, hypothetical N/A predicates, zero vectors, and candidate complete-ranking flags are **not approved method bindings**. Its Fraction arithmetic is explanatory arithmetic, not a future production accumulation/rounding decision or a bitwise equivalence oracle.

## Approval boundary for future expected results

| Item | Approved principle | Still UNRESOLVED / not authorized by this approval | Consequence for a future test oracle |
|---|---|---|---|
| M1 | Economic applicability and method-requiredness are independent of weight; they must be identifiable rather than guessed from missingness | Actual required/optional/conditional factor assignments; condition predicates; new economic N/A taxonomy | Use explicitly labelled toy bindings for principle tests; never infer an Official registry from simulation roles |
| M2 | Ordinary absence differs from relevant PIT/integrity/config failures; source/identity/admission boundaries cannot be bypassed by weights | Source-specific reason mapping and integrity scope; resolution methods; production admission migration | Pin which inputs were consumed and their request/source identity; preserve provider guards |
| M3 | Ordinary missing cannot trigger available-only denominator redistribution; proven N/A **can** be excluded under a defined policy | Which version permits N/A exclusion, its predicates and construct interpretation; production arithmetic/rounding | Assert missing-denominator stability; condition N/A deltas on a pinned version policy, not a universal exclude rule |
| M4 | Partial, complete, and ranking validity are separate concepts; partial output must not silently become a complete Official score | Exact completeness predicate; the prior proposal that all positive-weight factors must be present; ranking/admission method and any coverage rule | Test distinct fields and absence of unauthorized promotion; do not hard-code the old simulation's complete-ranking flag as approved truth |
| M5 | Zero weight changes contribution, not method-requiredness, related/shared PIT/integrity, or Official validity; Custom does not mutate Official | Runtime wiring, valid override vectors, request-subset selection, Official/cache/storage implementation | Prove scope isolation; keep mandatory evidence and admission checks independent of weight |

No numeric cutoff, confidence formula, default weight, new normalization, or alternative composite is chosen. An unresolved method binding should be reported as **UNRESOLVED / NOT_RUN**, not manufactured into an expected production result.

## The requested fourteen scenario families

In the table, `{axis}` means each of the actual prefixes `Q`, `G`, and `V` in the existing simulation. Future phase labels identify planned work only. They are not tests added by this document.

| # | Requested scenario | Exact existing evidence identifiers | What can be asserted from approved principles | Additional oracle/binding work needed before runtime acceptance |
|---|---|---|---|
| 1 | All factors present | `{axis}/all_present`, `{axis}/heterogeneous_present`; original golden `all_70`, `all_zero`, `all_100`, `heterogeneous_fractional` | Unchanged legacy input/version preserves historical result; metadata-only configuration does not alter it | A new method's COMPLETE/rank predicate remains version-bound; uniform arithmetic is not proof of economic correctness |
| 2 | Required missing | `{axis}/required_missing`; original `q_one_absent`, `g_one_absent`, `v_one_absent` characterize current behavior, without declaring those factors required | A factor declared method-required in an explicit binding cannot become satisfied by absent evidence or weight tricks | The real Official factor assignment remains UNRESOLVED; toy roles are only an independent principle fixture |
| 3 | Optional missing | `{axis}/optional_missing`, `{axis}/factor_absent`, `{axis}/score_none`, `{axis}/source_unavailable`, `{axis}/young_company_history` | Ordinary missing remains labelled and does not change the planned denominator; partial/complete/ranking purposes stay separate | Whether diagnostic output is permitted and its method-bound score kind must be explicit; no universal COMPLETE rule is approved |
| 4 | Proven N/A | `{axis}/proven_na`, `{axis}/na_with_consumed_contamination`; denominator sensitivity row `Q/financial_na` | Missingness alone cannot prove N/A; consumed contamination cannot be relabelled out of scope | N/A exclusion is tested only when an approved version binding permits it; retain a version that does not exclude where required for legacy replay |
| 5 | Unresolved applicability | `{axis}/unknown_applicability`, `{axis}/unverified_na_claim` | Unknown applicability cannot masquerade as proven N/A or an approved admission decision | Expected typed outcome/reason must be bound; do not invent a new production enum in the tests |
| 6 | PIT unavailable | `{axis}/pit_unavailable`, `{axis}/provider_available_at_after_decision`, `{axis}/provider_published_at_after_decision` | Consumed/admission-relevant PIT failure cannot be bypassed by reweighting; keep `available_at` and `published_at` protection | Distinguish no admissible vintage from a demonstrated future-data breach under the source-specific reason mapping; preserve both evidential reason and request scope |
| 7 | Integrity failure | `{axis}/invalid_consumed`, `{axis}/numeric_integrity_failure`, `{axis}/version_mismatch`, `{axis}/identifier_ambiguous`, `{axis}/identifier_changed_unresolved_mapping`, `{axis}/calculation_error`, `{axis}/blocked_dependency` | A valid-looking numeric score cannot erase a relevant integrity failure | Use the resolved counterpart `{axis}/identifier_changed_resolved_mapping`; identifier change alone is not universally invalid |
| 8 | Zero weight | `{axis}/zero_weight_present`, `{axis}/zero_weight_optional_missing`, `{axis}/all_zero_weight` | Zero contribution is distinct from missing evidence and N/A; weight zero does not waive requiredness or source integrity | Simulation's “optional-zero inventory missing but complete construct” is only one unapproved completeness method; retain inventory and request-subset evidence and await M4 binding |
| 9 | Zero weight + PIT failure | `{axis}/zero_weight_required_pit`, `{axis}/zero_weight_optional_consumed_pit`; `unsafe_counterexamples` entries for `{axis}/zero_weight_required_pit` | Related/consumed PIT failure blocks admission independently of contribution weight | Add future scoped counterexamples proving when an extra, genuinely unrequested and unconsumed artifact is irrelevant; it must not influence identity/applicability/global source admission |
| 10 | Zero weight + required missing | `{axis}/zero_weight_required_missing` | Zeroing a method-required factor cannot remove required evidence | Method binding supplies requiredness; no actual Official factor is newly assigned by these fixtures |
| 11 | Multiple missing | `{axis}/several_optional_missing`, `{axis}/all_missing`; original golden `q_all_absent`, `g_all_absent`, `v_all_absent`, `no_factors` | Missing reasons remain individually visible; no missing-driven denominator shrink; no missing factor is stored as numeric zero | Partial/complete/blocked result and ranking use require the approved method binding; undefined denominator/support must not yield a fabricated score |
| 12 | Financial applicability | `Q/financial_na`, `Q/financial_na_even_if_bad_roic`, `Q/financial_optional_missing`; original golden `financial_na`, `financial_na_even_if_bad_roic` | Current Q=56 remains immutable under legacy replay; existing financial applicability is observed, not rewritten | Possible 56→70 result requires an explicit new version allowing N/A exclusion. The unused ROIC observation is distinct from contamination consumed by identity/applicability |
| 13 | Custom override | Toy weights in `{axis}/zero_weight_present`, `{axis}/zero_weight_required_missing`, `{axis}/zero_weight_optional_missing`; existing `test_official_custom_isolation_existing_boundary` | Personal/Custom changes must leave Official score, validity, stored evidence, Leaderboard and Track Record unchanged | Existing simulation is **not** a valid WeightOverride runtime test. Future tests must exercise the existing resolver and authenticated scope/binding, request, storage and cache paths only after wiring is separately approved |
| 14 | Official path | All original golden case IDs; existing `test_neutral_metadata_and_config_manifest_leave_scores_unchanged`, `test_official_custom_isolation_existing_boundary`; original `V_only_delta` | Legacy Official replay and publication namespace remain intact; Custom cannot issue an Official result through a metadata label | Actual producer/board/storage integration and ranking admission are separate gates. Q/G/V/composite version and source identities must be pinned and traceable |

The table maps to evidence actually present. It does not claim all fourteen families already have production tests. In particular, Custom resolver-to-runtime isolation, persistent Official publication, zero-weight + INVALID, and future complete/ranking-method acceptance remain **planned / NOT_IMPLEMENTED**.

## Denominator and accounting invariant proposals

Cross-document notation is identical to CONTRACT.md: registered Wr; planned
denominator basis Wp; admitted/eligible evidence We; contributing Wc; permitted
N/A-excluded Wna. For one resolved nonnegative weight vector and the same axis
and units, Wr = Wp + Wna and 0 ≤ Wc ≤ We ≤ Wp ≤ Wr. Ordinary observation loss
may reduce We/Wc, never Wp. These are mathematical domain-accounting identities,
not a new binary-float equality/rounding oracle. Legacy arithmetic and evaluation
order remain unchanged; exact future comparison/precision rules are unselected.

The inactive contract should expose enough accounting to distinguish the following concepts. Names below are semantic roles, not a mandatory new runtime object or enum:

- **Registered weight:** the weight vector selected by the immutable Official/profile/config reference, before any factor-eligibility evaluation.
- **Planned weight:** the weight scheduled for the bound applicable scoring construct. An ordinary missing observation does not remove a planned factor. Requiredness is tracked separately from whether its contribution weight is positive.
- **N/A weight:** weight explicitly excluded, if and only if the versioned applicability/denominator policy permits that proven economic N/A exclusion. A bare quality label does not authorize this amount.
- **Eligible evidence weight:** weight with admissible source, PIT, identity, version and calculation evidence. Physical data presence alone does not establish eligibility. An axis may remain blocked by a relevant shared/required integrity failure even if other eligible evidence exists.
- **Contributing weight:** eligible weight for which an admitted normalized factor score actually contributes. Missing factor scores remain absent; they are not rewritten as zero observations.

The denominator is a **bound method attribute**, not an alias for eligible/contributing/available weight. When the chosen contract uses planned applicable weight, the following assertions should hold in future principle tests:

1. Removing an ordinary optional observation while holding registry, profile, applicability, and method identity fixed changes contributing evidence but **not** planned weight or its denominator.
2. A source becoming unavailable, history being insufficient, an absent factor, or `score=None` must not silently shrink that denominator. Reasons remain different even when arithmetic consequences match.
3. The N/A-exclusion amount changes only through an evidenced, version-bound applicability decision. Holding that binding fixed while hiding data cannot create additional N/A weight.
4. Zero weight reduces scoring contribution; it does not remove required evidence, erase a relevant source failure, or change an Official construct through a Custom request.
5. The numerator and any admitted score must identify which planned, eligible and contributing weights they used. A coverage field reporting eligible/contributing weight cannot be repurposed as the denominator without method authority.
6. An empty/all-zero admitted scoring basis cannot be divided into a fabricated numeric result. Its typed blocked/not-applicable/undefined outcome must follow the bound method; this plan does not choose its runtime enum.

For nonnegative valid fixture weights, contributing weight should be a subset of eligible evidence weight, and eligible evidence weight a subset of planned weight, **within the same request, profile, and applicability scope**. These subset relations do not replace integrity guards or imply that the highest ratio grants COMPLETE/ranking status. The accounting should avoid counting the same excluded N/A weight in both planned and excluded sums; version-specific accounting reconciles the selected vector without assuming a universal normalization rule.

The existing financial sensitivity rows are useful independent anchors: numerator 56 with a full-registry basis of 1 gives 56; a separately authorized N/A-excluded basis of 0.8 gives 70. With an additional toy optional factor absent, the numerator becomes 45.5. Keeping that same applicable basis gives 56.875, while shrinking to available-only 0.65 gives 70. The latter demonstrates exactly the missing-driven redistribution prohibited by M3. These are existing illustration values, not new defaults or newly executed tests.

## Safety, provenance, scope and isolation invariants

Future tests should verify behavior at the actual request/admission boundary, not only a post-hoc arithmetic function:

| Invariant | Independent proof strategy | Approved versus unresolved boundary |
|---|---|---|
| Missing is not observed zero | Compare two explicit source records: valid score zero with evidence, and absent score with reason; retain unequal factor states/provenance even if a contribution sums to the same number | Principle approved; emitted runtime types remain bound |
| PIT cannot be bypassed by zero weight or renormalization | A request with consumed future/unavailable evidence must fail admission under a valid positive vector and a permitted zero-weight variant; do not calculate a “good” result from only the remaining rows | Admission preservation approved; valid vector and consumed scope must be explicit |
| Zero + INVALID cannot bypass integrity | Plan a future paired fixture with a valid-looking nonnull numeric payload and an independently recorded integrity failure, then zero its contribution weight | **Not present as a combined case in the current simulation.** Do not relabel `numeric_integrity_failure` or `zero_weight_optional_consumed_pit` as this executed test |
| Requiredness cannot be removed by zero | Use an explicitly declared toy method-required evidence reference at both positive and zero weight; missing required evidence remains unsatisfied | Principle approved; actual factor role mapping unresolved |
| Identity change needs resolution, not a blanket ban | Pair the existing resolved dated-mapping and unresolved ambiguous-mapping fixtures; compare provenance/lineage and admission reason | Ordinary identifier change is not universally INVALID; real resolution binding unresolved |
| Out-of-scope data cannot create false blockers or hide consumed contamination | Track requested, consumed, dependency/shared-identity and genuinely irrelevant artifacts before weighting; only an evidenced unrelated extra artifact can be ignored | Scope principle approved; source/method-specific consumed dependencies unresolved |
| Provenance survives every partial/blocked outcome | Every factor/reason, registry/profile/version ref, source/vintage ref, time boundary and request identity remains traceable; missing refs reject applicable admission rather than being fabricated | Shape-only existing schema checks are not source authentication or real PIT execution |
| Confidence is independent of coverage | Alter inventory presence while holding evidence-quality assessment inputs fixed; preserve separate methods/fields; never infer a confidence formula from a weight fraction | Separation approved; no confidence formula is approved or tested here |
| M4 no silent promotion | A diagnostic result cannot be serialized/cached/published as COMPLETE or rank-admitted solely because it contains a number or coverage equals 1 | Separation approved; exact COMPLETE and ranking predicate unresolved |
| Custom cannot mutate Official | Snapshot/hashes of Official score, validity, board order, Track Record, registry and historical evidence remain unchanged through a valid Custom request; exercise cache/storage/producer scope | Existing synthetic objects provide limited baseline evidence; runtime/persistent isolation is future work |
| Canonical/history preservation | Compare old tracked artifacts, source hashes, legacy version and stored evidence identities; append new versioned evidence separately | Current approval grants no canonical merge, producer publication or history rewrite |

Scope checks must occur before a contributing-weight filter could erase a relevant failure. If a failure has already contaminated applicability, global identity or admission, later N/A or zero-weight labels cannot make it unrelated. Conversely, presence of an unrelated extra artifact is not automatically evidence of a consumed failure. The test must prove this scope distinction rather than treating all present artifacts alike.

## Independent oracle design

Future test expected results should be derived independently from the implementation under test:

1. **Immutable legacy oracle:** reuse the original 71-case fixture and documented semantic projection. UUID exclusions remain exactly as previously documented. Do not regenerate golden expected values from a new evaluator. Historical binary-float fingerprints detect accidental arithmetic changes; the rational policy illustrations do not replace them.
2. **Method-bound principle oracle:** use a small explicitly labelled synthetic binding that declares requiredness, applicability, consumed/requested scope and the permitted denominator policy. Write the expected factor sets, reason transitions and allowed result kinds in a reviewable table before testing runtime code. This binding is never an Official factor-registry decision.
3. **Hand-derived accounting oracle:** use existing weight/observation anchors to write out the numerator and planned, eligible, contributing and N/A weight accounting separately. Do not call the same aggregation helper to construct expected outputs. Specify which values must match exactly and which float comparison contract applies only after the production arithmetic binding is authorized; introduce no tolerance here.
4. **Metamorphic oracle:** removing a valid nonnegative score under an unchanged fixed planned denominator cannot improve the contribution; hiding a low score can inflate available-only estimates, so the planned denominator must remain stable. This mathematical property is scoped to unchanged applicability, config and nonnegative fixture inputs and does not settle complete-score eligibility.
5. **Admission oracle:** source/PIT/identity evidence determines whether the request may score before any weight-dependent contribution. Vary weights while holding that evidence fixed; relevant admission failure must remain visible. Separate failure reason from numeric absence.
6. **Isolation oracle:** compare independently captured immutable Official payloads and persistence keys before/after Custom operations, not only equality of two results computed through the same helper. The test must distinguish Official and Custom config/result namespaces and reference identities.
7. **Negative binding oracle:** an unapproved/unknown completeness or ranking method, mismatched config version, unproven N/A exclusion, or unresolved requiredness must not be converted into an apparent approved runtime result. Until those bindings are supplied, their method-acceptance tests are **NOT_RUN / BLOCKED_BY_BINDING**, not failing invented expectations.

The test plan should exercise the existing weight resolver and evaluator configuration contracts where sufficient. It should not create a second weight engine or assume a new ProfileConfig object is necessary. Candidate research-vector restrictions remain intact; toy zero-weight fixtures do not authorize a formerly invalid V candidate vector.

## Planned validation phases and gates

| Phase | Planned work | Execution gate | Evidence to preserve |
|---|---|---|---|
| P0 — design receipt | Map approved principles, pending bindings, scenario coverage and independent oracle sources | Current documentation scope | This plan; approval reference; original evidence identities; no test execution claim |
| P1 — binding review | Pin factor-role/application/source/denominator/output-kind/config references; identify remaining M4 completeness/ranking decisions | Separate user/D3 review for unresolved semantic bindings; no arbitrary numeric default | Versioned method and config references; explicit unresolved list |
| P2 — inactive test design review | Review expected state transitions, request scopes, factor sets and accounting tables using existing immutable examples | Bindings sufficient to make expectations meaningful; still no runtime authorization implied | Test specification/oracle tables; legacy/new compatibility labels |
| P3 — separately authorized implementation | Add only approved evaluator/metadata/test changes after explicit implementation grant | Runtime implementation approval; scope, fallback, normalization, composite and WeightOverride dependencies satisfied as applicable | Changed-source manifest; exact commit/version identity; no history rewrite |
| P4 — focused validation | Existing QGV targeted → new method/contract checks → golden equivalence → isolation/provenance checks | Approved implementation exists; expectations independently reviewed | Actual commands/counts/results, expected intentional deltas, local versus Actions separation |
| P5 — regression/integration | Existing full regression; affected Actions; latest integration overlay; persistent isolation where wiring is approved | New source or binding impact justifies checks; do not repeat unchanged evidence by default | Exact tested HEADs, workflow/run identities, required checks, source/config overlaps |
| P6 — migration/promotion | Old/new side-by-side cohort/rank impact, real-data PIT/OOS, rollback/version/namespace readiness | Separate migration/Official/ranking/publication approval; Holdout separately protected | Immutable new evidence linked to old; no canonical merge or historical replacement without explicit authority |

For this task, only **P0 documentation** is performed. P1–P6 are not executed or automatically authorized. If sources, method bindings and config refs remain unchanged, retain applicable original CI/golden evidence and report its tested SHA instead of rerunning it for a new count. If they change later, recalculate the impact boundary first and run only the affected checks before broadening regression.

## Acceptance bookkeeping

A future report must distinguish:

- **Legacy compatibility PASS:** unchanged legacy input/version reproduces the old semantic projection. It does not declare new semantics approved.
- **Principle invariant PASS:** an independently bound toy/synthetic fixture obeys M1–M5 principles. It does not approve its toy requiredness, N/A rules, or a production method.
- **Method acceptance PASS:** a separately authorized, version-pinned completeness/denominator/admission method passes its own oracle. This cannot currently be declared for unresolved bindings.
- **Official/Custom runtime isolation PASS:** actual approved request/storage/cache/producer wiring has been exercised. Existing synthetic in-memory isolation alone is insufficient.
- **PIT/OOS PASS:** actual eligible real-data replay has run with source/vintage/provenance protection. Synthetic guard illustrations do not establish it.
- **Remote CI PASS:** the exact relevant commit's Actions/required checks have completed successfully. Existing local results are not remote CI.

Intentional deltas must be identified by method/version and approval reference instead of updating old expected results. A metadata-only change must keep scores unchanged. A config-reference addition alone must not implicitly activate a new calculation path. Any change to G 3–5Y, EPS→FCF, V normalization/scoring, composite, WeightOverride runtime, Official weights, Leaderboard or Track Record stays outside this plan's implementation authority.

**Stop condition:** preserve this inactive regression plan and its original evidence references; await the unresolved method bindings and explicit implementation/migration authorization. No production tests, runtime implementation, or legacy/history rewrites are performed here.
