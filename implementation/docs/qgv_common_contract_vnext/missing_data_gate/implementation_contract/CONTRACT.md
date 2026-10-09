# Missing-Data Implementation Contract vNext · 0.1

**INACTIVE / SPEC-ONLY / RUNTIME_ENABLED=false.**
M1–M5 principles are APPROVED in [approval.json](approval.json).
This implementation contract is a new design proposal, not production authorization.

## Authority and exact scope

Intake owner HEAD: `ed907b8f5a046008319cddecc6ef40b9bd6759dc`.
PR #44 remains Draft/Open at `cb1906b207623168fd70f3dcdb5b30f2d82d807d`;
canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`;
integration #42 `523e702a806a718d163cfbf62aa3fc29d8c3ef3c`.
The user approved principle clauses at **2026-10-05 09:57:52 KST**,
not every stronger prior recommendation or simulation assumption.

No actual factor requiredness, new N/A rule, completeness/ranking criterion,
coverage cutoff, arithmetic/rounding default, calculation migration or runtime
code is selected here. Legacy Q/G/V and candidate paths are preserved.
See [REUSE_MAP.md](REUSE_MAP.md), [MIGRATION_BOUNDARY.md](MIGRATION_BOUNDARY.md)
and [REGRESSION_PLAN.md](REGRESSION_PLAN.md).

## 1. Reuse, not a second configuration engine

Use the existing Common Contract sidecar's version/hash/locator reference,
value presence, applicability, legacy QualityState, PIT assessment, independent
coverage/confidence and config_binding_ref. Reference the existing factor IDs,
ProfileKind, DataStamp, raw/source/vintage artifacts and dependency evidence.
Keep QualityState and Personal DataQuality in their original domains.

Use Personal OfficialRegistry, PersonalStrategyVersion, WeightOverride,
effective_tree, ResultNamespace, content_hash and Provenance for their existing
purposes. Retain C-24/C-30 authority constraints, existing sibling/range checks
and no silent rebase. StrategyProfile remains its existing provisional parameter
bundle. No new ProfileConfig, weight engine, enum hierarchy, mutable settings
store, duplicated factor-weight dataset or runtime parser is introduced.

Minimum missing **data expressions**, composed by references rather than new
classes, are: method-requiredness declaration, provenance-backed applicability
determination, scoped dependency/admission trace, planned weight-basis ledger,
and independent result-use assessments. The current bool applicability helper,
single QualityState, scalar/null result and coverage enum cannot express all of
these independent meanings. This is the reason for the additions; actual schema
or production class design remains a later authorized implementation choice.

## 2. Minimal reference binding and factor decision record

A factor is identified by axis + existing stable factor ID + exact definition/
calculation version. A selected method/profile binding must resolve every
required reference before a future evaluation can claim a policy-admitted result.
The absence of a policy is not missing company data and does not imply OPTIONAL,
APPLICABLE, N/A or complete. Keep UNASSESSED and qualified unresolved reasons.

| Expression | Minimum contents / reuse | Unselected value or boundary |
|---|---|---|
| Method/config binding | Existing config_binding_ref; method/profile/subject/namespace, exact definition/normalization/calculation/registry refs, factor-node map | No new default profile, factor role or factor weight |
| Requiredness declaration | requirements_ref to an immutable authorized method declaration; scope, authority, exact factor/input IDs; conditional predicate ref if relevant | Actual REQUIRED/OPTIONAL/CONDITIONAL roles are UNRESOLVED, not guessed |
| Applicability determination | Existing applicability state; policy/predicate/version/source refs; admitted evidence inputs, reason, subject/profile/period and decision time | APPLICABLE / NOT_APPLICABLE / UNASSESSED are existing sidecar terms, not a new runtime enum |
| Dependency/admission trace | Input IDs, original QualityState/reason, source/vintage/stamp, predicate/requiredness/scoring/shared use, policy ref, affected scope and disposition | No blanket scope from weight or axis label; no new stale/estimated/conflict rubric |
| Weight-basis ledger | Registry/version/override refs; ordered factor refs; declared planned, eligible, contributing and N/A-excluded weights and reasons | No available-factor redistribution or new source-of-truth weights |
| Result-use assessments | Referenced contribution, independent coverage/confidence, completeness, scoring validity, consumer ranking/publication policy decisions | Neither scalar nor READY nor complete automatically proves rank/publication authority |

No actual 20-factor role table is supplied. An immutable method declaration may
use REQUIRED, OPTIONAL and CONDITIONAL as vocabulary if an approved existing
method document uses them; a future data shape can refer to that declaration
without creating a second runtime enum. CONDITIONAL needs a deterministic
predicate and admitted dependencies, not an implicit field-presence heuristic.
A conditional dependency cycle or missing binding cannot be resolved by selecting
a weight default or a toy role from the previous simulation.

## 3. Admission / applicability / scoring pipeline

The user's conceptual pipeline is suitable with a dependency-aware refinement.
The *plan* (identities and input scope) must be resolved before observations are
interpreted; numeric weights cannot decide which validity obligations exist.

| Stage | Operation | Output / ordering invariant |
|---|---|---|
| A0 · Envelope and context | Authenticate/pin subject, namespace, calculation/method/configuration and declared dependency scope; preserve original artifacts | Shared identity/config/integrity failures cannot be waived by an override |
| A1 · Predicate-input admission | Admit evidence used for applicability and conditional-requiredness decisions under existing PIT/provenance protections | No future/ambiguous/unauthenticated fact may prove N/A and then hide its own failure |
| A2 · Applicability | Evaluate the exact applicability predicate using A1 evidence, independently of weight/value presence | Proven APPLICABLE/N/A or UNASSESSED plus explicit reason/provenance |
| A3 · Requiredness | Resolve the authorized method/input obligations and conditional predicates | N/A does not remove the evidence needed to prove applicability; missing rule stays unresolved |
| A4 · Observation admission and scoring eligibility | Check factor-input validity, reason, finite/declared numeric shape and original lineage under the selected policy; distinguish ordinary absence | Relevant PIT/integrity failure remains blocking before numeric weight application, including zero |
| A5 · Planned basis and numeric contribution | Resolve already-authorized weight tree; construct the planned denominator ledger; accumulate only admitted values using pinned arithmetic | Basis is determined independently of ordinary observation loss; no available-only mean |
| A6 · Coverage and result meaning | Describe contribution, coverage, completeness and scoring-validity assessments independently | Numerical existence does not fill an unresolved completeness or consumer policy |
| A7 · Consumer admission | Apply separately approved method/version/namespace-specific ranking/publication criteria | No automatic rank, Official validity, grant or migration |

A1 and A4 are two uses of the **same admission obligation**, not separate
Official/Custom evaluators. They are needed because applicability itself consumes
evidence before the full factor-input set is known. The current provider resolver
already checks both available_at and published_at before analysis; current
_weighted skips applicability before reading observation quality. Those historical
orders are characterized, not changed by this design.

Denominator planning is logically independent of ordinary missing before final
numeric aggregation. This refines the displayed contribution→denominator sequence:
calculation can report numerator and denominator together, but losing an
observation must not rebuild the denominator from contributing weights.

Related/shared failure scope is declared by methodology/input lineage and cannot
be edited by an override. Truly unrelated inventory is not automatically a
global failure, but its scope must be independently evidenced. Optional-zero
input-request suppression is **not authorized** by M5: it is a separate future
scope-binding option. A previously consumed/provided related PIT/integrity failure
cannot be retrospectively made 'unrequested' by changing its weight.

## 4. Applicability contract

Reuse factor_applicable and existing FINANCIAL/GENERAL_CORPORATE identities as
current behavior sources, not as automatic authority for a new exclusion.
Its bool result must be accompanied by exact policy source/version, subject and
period scope, predicate evidence, original reason and code/data provenance.
The current financial roic_wacc exclusion is a legacy characterization only;
no new industry taxonomy or numeric rule is invented.

| Field / requirement | Contract meaning |
|---|---|
| Source/authority | Pinned applicability policy/method ref plus approval ref; caller-supplied QualityState.NOT_APPLICABLE alone is not proof |
| Predicate/version | Deterministic definition, exact code/rule/content identity, declared inputs and supported subject/profile scope |
| Reason | Economic non-applicability explanation, kept separate from data absence, invalidity or short history |
| Provenance | Input source/stamp/vintage/hash/locator and dependency refs; provenance must itself satisfy admission |
| Time | as_of describes economic scope; decision_time controls admission; predicate evidence available_at and published_at must satisfy current protections |
| Resolution | Existing APPLICABLE / NOT_APPLICABLE / UNASSESSED; conflict or unsupported policy stays unresolved |
| Reproduction | Same subject, input vintages, decision time, method/profile and predicate identity reproduce the determination; latest sector metadata cannot substitute |
| Exclusion permission | Explicit denominator-policy binding determines whether this proven N/A is excluded; proof does not mandate automatic exclusion |

Retain date/interval precision and missing-time limitations. Do not synthesize
midnight, use retrieved_at/calculated_at as availability, or convert Personal
TimeStamps into DataStamp wholesale; their observed_at meanings differ and
Personal TimeStamps lacks published_at. No PIT policy is weakened or activated.

## 5. Requiredness contract

The requirements_ref is an immutable method/profile declaration with authority,
effective scope, factor/input ID, role meaning, conditional predicate/evidence
where relevant, and input-obligation refs. It is **not stored in WeightOverride**.
The factor/node identity map remains explicit; fixed weight size, current
candidate complete-case behavior and sample role labels do not establish roles.

Requiredness resolution precedes numeric weight application. It also identifies
shared and applicability-proof obligations which remain even when the factor
is N/A or zero-weight. Actual required/optional/conditional values, conditions,
failure scope and role-dependent result behavior need separate semantic binding.
This design does not decide whether every missing REQUIRED factor blocks an
entire axis, the whole evaluation or a particular consumer; related admission
failures still cannot be reported as passing under M2/M5.

## 6. Denominator accounting and invariants

All weights here are within one declared axis and the same pinned registry/
configuration basis. Local axis-factor weights and global path-product weights
must not be mixed. Existing tree validation comes first; unset is not zero.
Record the original ordered weights rather than duplicating a weight engine.

Let F be the registered scoring factor set for the pinned method/profile. Let N be only those members
whose N/A determination is proven and whose exclusion is explicitly permitted
by the selected denominator binding. Let P be F minus N, the planned denominator
basis. Let A be members of P with admitted evidence, and C be members of A whose
score can actually contribute. **Planned weight is independent of evidence
availability; eligible evidence weight is not the denominator.** These terms
have the same meanings in REGRESSION_PLAN.md.

| Quantity | Definition |
|---|---|
| REGISTERED WEIGHT · Wr | Sum of the pinned method/profile weight vector over F before permitted N/A exclusion |
| PLANNED WEIGHT · Wp | Sum over P, the planned denominator basis; ordinary missing remains in P |
| N/A EXCLUDED WEIGHT · Wna | Sum over N; every member has proof and exclusion permission |
| ELIGIBLE EVIDENCE WEIGHT · We | Sum over A, with admitted source/PIT/identity/version/calculation evidence; this can shrink with missing evidence |
| CONTRIBUTING WEIGHT · Wc | Sum over C, only actually admitted numeric contributors; zero contributes zero |
| Numerator · T | Pinned ordered arithmetic over admitted weight × value contributions; rejected observations never contribute |

For valid nonnegative resolved weights:
**Wr = Wp + Wna**, **0 ≤ Wc ≤ We ≤ Wp ≤ Wr**.
These are mathematical domain-accounting identities, not a new binary-float
equality or rounding oracle. Preserve legacy evaluation order and arithmetic;
future numeric comparison/precision rules need an exact method binding, and no
epsilon, rounding default or replacement summation is selected here.
The differences Wp−We and We−Wc are accounting observations, not evidence assigned score 0.
Factor absence/null/source-missing/history-short does not by itself change F, N,
P or Wp. N/A label without proof cannot enter N. Weight zero does not move a
factor into N or remove its evidence obligations. Keep any rejected-input
contributions out of T while retaining their reason and blocking disposition.

If a selected future method defines a weighted ratio, its denominator is Wp,
not We or Wc. The conversion T/Wp, units, order, rounding and score-kind require the
exact arithmetic/method binding; this is **not a new universal scoring formula**.
Wp=0/unset/unresolved has no valid ratio: never fabricate 0/100/NaN/Infinity or
a default pass. A separately approved result contract will decide which
diagnostic quantities may be emitted; validity cannot be made PASS by arithmetic.

Available-only regression invariant: with method/profile/applicability/weights
fixed, removing an ordinary observation changes the admitted/contributor trace
and possibly T, We or Wc, **never Wp**; complete/ranking status is separately assessed, not inferred.
A verified N/A exclusion may change Wp only with its bound policy and evidence
recorded. This can alter effective relative contributions without changing stored
weights, and therefore cannot be advertised as score-neutral metadata alignment.

## 7. Contribution, coverage, completeness, validity and ranking

Reuse legacy scalar and coverage as historical fields. New design views do not
overwrite them or translate READY into complete/rankable.

| Independent concept | Future contract content | No implicit inference |
|---|---|---|
| Numeric contribution | Ordered admitted contributions, numerator, planned basis and score-kind/method refs | Non-null value does not certify complete score |
| Coverage | Named evidence universe, presence/admission inventory, numerator/denominator units, method/assessment ref | A weighted/count fraction does not prove completeness or confidence |
| Completeness | Decision against an exact requirements/completeness method with reason/input refs | No all-positive-weight rule or minimum percentage selected |
| Scoring validity | Admission/configuration/identity and method obligations with dependency scope | Legacy quality=OK or Personal actionable(PARTIAL) is insufficient |
| Ranking eligibility | Independent consumer/version/profile/namespace decision and authority | Diagnostic/complete output does not automatically authorize ranking |
| Confidence | Existing independent assessment/method/evidence/limitations | No formula, cutoff, QualityState copy or score multiplier |

Unknown method or consumer assessment remains UNASSESSED rather than true.
M4 does not settle every consumer's treatment of partial results: complete/rank
conditions and any allowed research view are a separate decision. Official
maturity/publication grant is an additional authority, never an arithmetic result.
V's existing confidence/coverage reuse remains a separate metadata gate.

## 8. Zero-weight and Official/Custom invariants

For the same subject/time/method/requirements/applicability/evidence lineage,
changing a weight to zero may change numeric contribution and declared weight
accounting, but must not change:
- related/shared PIT or integrity failure into PASS;
- requiredness resolution or missing obligation into satisfied;
- applicability into N/A or eliminate applicability validation;
- required provenance/identity/version evidence into optional;
- an Official registry/validity/result/board/record into a Custom one.

Zero-parent path product retains child local mix under existing effective_tree;
it does not cancel child method-requiredness. Existing V candidate zero-weight
constraints remain unchanged; no relaxation or input-request optimization occurs.
Personal edits must use the pinned authorized namespace and existing version/
editability validation. Same-evaluator future reuse is a design goal, not wiring.
Config/score/cache/storage/consumer identity includes namespace and immutable
method/configuration/override refs; no override is injected into OFFICIAL.

## 9. Legacy and future migration boundary

Legacy outputs remain under their exact existing method/source/config identities,
including candidate rules, financial partial contributions and (Q+G)/2.
New method dispatch, parallel linked results, comparison cohorts and consumer
adoption are **future proposals requiring authorization**, not active defaults.

The financial uniform-70 case remains legacy Q=56. A future specifically approved
N/A denominator exclusion could yield 70 under a ratio binding. M3 has not
approved that application, effective weight redistribution, score migration or
historical rewrite. See MIGRATION_BOUNDARY for separate semantic/version gates.

This phase stops after reference-based design, approved-principle recording,
test-plan reuse/checking, protected-byte verification and scoped publication.
No tests/evaluator/schema/runtime implementation is introduced. Prior 102×4/
408 outputs and 270 checks remain historical synthetic policy comparisons,
not new approved-vNext acceptance results. Full Actions/real PIT/OOS acceptance
for this proposed design is NOT_RUN. Holdout remains UNCONSUMED.

**Next single gate:** prepare/review the bounded method/profile binding and
consumer-admission package, selecting roles/predicates/reason-scope/denominator/
completeness/consumer refs for a chosen scope without defaulting the 20 factors.
