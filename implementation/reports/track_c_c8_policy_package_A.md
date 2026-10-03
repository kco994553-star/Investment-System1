# Package A — C8 calibration / gates / promotion contract proposal

Status: PROPOSED / NOT APPROVED / NOT ACTIVE. Recorded: 2026-10-01 10:45:14 UTC.
Checkpoint:15fed506d4e67d89861221281e4879002e431b4a.
Preparation only; no C8 runtime, threshold value, lifecycle transition, promotion or
research/promotion FreezeManifest is created by this package.
Authority: EVL_SPEC_v0.1 sections3/5-12; TC-D3P-004 A;005 S;006B.
C7 has a separate plateau/drift policy blocker. This package does not resolve it.

## 1. Current contract
Universal/Statistical/Economic threshold classes; Universal thresholds are not calibrated.
Statistical/Economic calibration: candidate range -> coarse grid -> sensitivity ->
stable plateau -> rounded value -> Freeze. Calibration is threshold-only: no model/
parameter research. Hard-gate failure cannot be offset by higher return.
C6 computes all17 mandatory diagnostics with no significance/skill decision. Both DSR
counts and both benchmark Reality Checks retain complete family provenance.
C7 supplies descriptive profile differences and tied representatives, never a final
statistical/economic distinctness judgment or next-best replacement.
One Champion and one Challenger per profile; no automatic promotion/reoptimization.
Canonical states: DRAFT -> RESEARCH -> CANDIDATE -> VALIDATED -> FROZEN ->
HOLDOUT_TESTED -> OFFICIAL -> FORWARD_MONITORED -> FORWARD_VALIDATED.
Exceptions: REJECTED / RESEARCH_REOPENED / INVALIDATED; upstream suspension is also
defined by EVL section11. No new lifecycle state is proposed here.

Existing C0 FreezeManifest fields: artifact/profile/experiment/candidate/spec,
code/data hashes, vintage, parameters, thresholds, Holdout state, promotion state,
lineage_ids, tax mode. The class itself has no scope discriminator and only shallow
eligibility validation. C8 must wrap and resolve it; C0 source/API/tests stay frozen.

## 2. Unresolved decisions
Global C8 calibration versus inner C4 Validation; separation of threshold fitting and
assessment; evidence access order; threshold graph/stability/rounding/selection rules;
exact gate directions/limits/required coverage; statistical family and multiple testing;
skill/distinctness definitions; ties/roles/authorization; software-versus-real Manifest
scope. Actual dates, thresholds, grids, support and risk premium values remain UNSPECIFIED.

## 3. Proposed contract — exact approval items A1-A12
### A1 Dataset boundary
Preregister an OUTER calibration interval after the frozen Development/C7 research
interval and before sealed Final Holdout. Within it register chronological CAL_FIT
and CAL_VERIFY subpartitions; these are dataset roles, not lifecycle states.
Derive purge/publication exclusion from the approved horizon/rebalance contract.
Inner C4 Validation remains pipeline-threshold calibration and is not silently reused
as C8 gate-validation evidence. No Development/C7 OOS, CAL_VERIFY or Holdout observation
enters C8 threshold fitting. Candidate/model/parameters/metric definitions are frozen
before CAL_FIT access; calibrated thresholds frozen before CAL_VERIFY access.
All required Rolling/Expanding x Primary/Gap-stress evidence is separately retained.
Actual intervals require real data registration; missing complete support is NOT_RUN.
Previously accessed CAL_VERIFY cannot be declared unseen by resetting timestamps.

### A2 Preregistration and evidence resolution
Dedicated C8 ledger binds C7 full tie sets, C6 complete family and ALL charged attempts,
calibration partitions/coverage, metric paths/formulas/units, methods/seed, threshold
ranges/coarse grids/refinement and sensitivity grids, edge stability tolerances,
rounding precision/direction, gate roles/directions, family membership, budget and
approval authority before any relevant outcome access.
Resolve source ledgers/reports/checkpoints and current invalidation at every decision.
A declared timestamp alone does not prove pre-access registration: retain monotone
registration/access events and immutable source commitments. No defaults or zero filling.

### A3 Calibration algorithm
Enumerate the complete preregistered coarse threshold-combination grid and every
registered sensitivity neighborhood; no peak-only adaptive refinement.
For each point record each required candidate/cohort's complete gate vector on CAL_FIT
and preregistered calibration perturbation blocks. Gate classifications remain visible.
A stable edge differs by one adjacent registered threshold coordinate and satisfies
ALL preregistered per-gate acceptance-frequency/sensitivity tolerances on the registered
CAL_FIT blocks. Connected components require at least2 points; retain all components,
edge structure and full ranges; no diameter gate or largest-component preference.
No stable component -> NOT_RUN_NO_STABLE_THRESHOLD_PLATEAU.
No numerical tolerances/block dimensions are supplied here.

### A4 Rounded threshold selection and confirmation
Do not rank threshold points by returns, number of passing candidates or profile merit.
An explicit approver names a threshold vector from the recorded stable set, using only
the registered calibration criteria; the selection event exposes all alternatives.
Round to registered precision toward strictness: minimum gates upward; maximum gates
downward. Re-evaluate the rounded vector on CAL_FIT; it must remain in the registered
domain and have registered stable support, otherwise NOT_RUN with no automatic fallback.
Freeze exact threshold/selection hash before one CAL_VERIFY assessment. CAL_VERIFY
failure/NOT_RUN never causes automatic threshold adjustment. New research requires
RESEARCH_REOPENED plus a separately preregistered genuinely unused assessment interval,
new trial budget/family evidence; the prior outcomes remain logged. Holdout stays sealed.

### A5 Universal gates
Mandatory and noncalibratable: PIT Universe, availability<=decision_time, provenance/
vintage, complete ledger/budget/registration, immutable candidate/core scores,
no-lookahead, Official/Custom isolation, real-scope qualification, current invalidation,
Holdout isolation, tax exclusion and exact lineage integrity.
Integrity/nonfinite/forbidden-input violation=FAIL. Legitimate missing prerequisite/
undefined support=NOT_RUN. Both block promotion. Keep observed financial hard-gate
failure separate from computational-contract failure.

### A6 Statistical gates and multiple testing
Use the approved C6 method versions, full aligned family, period arithmetic net-minus-RF
Sharpe, both DSR views and both Reality Checks. Require all registered statistical
gates in ALL required cohorts/folds, without favorable-cohort averaging.
PSR probability>=registered min; DSR distinct/attempt probabilities each>=their registered
min; PBO<=registered max; both family Reality Check tail fractions<=registered limits;
bootstrap evidence includes registered lower quantiles/effect floors with exact path.
Limits are NOT supplied. Bare C6 PASS is not statistical PASS.
No max over DSR views, empirically invented effective trial count or selected-family rerun.

For newly tested skill/distinctness contrasts in A7/A8, propose jointly resampled paired
block contrasts using ALL preregistered pairs/metrics/cohorts in one declared family.
For each contrast: observed D=metric(left)-metric(right); use identical preregistered
circular block indices across all frozen candidates/benchmarks, recompute each approved
metric on each paired draw D_b, and report the two-sided centered tail fraction
count(abs(D_b-D)>=abs(D))/B with the raw replicates, B/seed/indices/method version.
Undefined resampled statistics make the contrast NOT_RUN; do not discard those draws.
Apply Holm step-down to the preregistered family of valid p-values at a separately
registered alpha; if required family support is incomplete, family decision NOT_RUN.
This is a NEW proposed C8 method requiring approval and independent verification;
existing kernels do not already implement or validate it. No percentile interval is
misrepresented as simultaneous coverage and no numerical alpha/B/L is defaulted.
All hypotheses, including rejected/failed/unused alternatives, remain accounted for;
a new metric or adaptive contrast requires a new registered family.

### A7 Skill assessment
Require qualified C6 robustness and ALL registered superiority contrasts against random
ranking, randomized weights, equal/simple and market-cap controls, with declared metric
directions and minimum economic effect. A6 multiplicity protection applies.
A valid, adequately supported failure to establish registered superiority records
NO_EVIDENCE_OF_SKILL and blocks promotion. Missing/undefined evidence is NOT_RUN, not
proof of indistinguishability or skill. Economic superiority alone never offsets a
failed statistical/universal gate. No actual investor weights or substitute controls.

### A8 Profile distinctness
Use C7 raw pair differences unchanged. For EACH profile pair and EACH required cohort,
require at least one preregistered metric contrast that BOTH rejects equality under A6
multiplicity protection AND exceeds its registered economic separation in absolute
magnitude (or a preregistered approved directional contrast).
Register the entire disjunction/family before access; report every contrast, including
zeros and ties. Well-supported failure=PROFILE_NOT_DISTINCT, blocking the declared
three-profile promotion batch. Incomplete family/support=NOT_RUN.
No automatic next-best candidate, substitute profile or post-result metric selection.
Additional metrics/derivations need their own versioned formula and policy approval.

### A9 Economic gates
ALL required cohorts and all hard gates must pass the EVL order:
NET_OF_TRADING_COST_PRE_TAX nominal CAGR>0 -> REAL_PRE_TAX CAGR>0 ->
RISK_FREE_EXCESS_PRE_TAX relative-wealth CAGR>0 -> registered required risk-premium
path/limit -> registered benchmark opportunity-cost path/limit -> registered
risk-adjusted metric paths/limits. Preserve gross/net/real/RF views and raw values.
Tail loss, MDD, turnover, recovery censoring and minimum growth use exact C3 paths and
explicit profile-specific registered directions/limits. None of these additional
values is supplied. Do not substitute arithmetic excess Sharpe for relative RF CAGR,
or an unrecovered duration for a completed recovery.
Passing one high-return gate cannot compensate for another hard-gate failure.

### A10 Tie-set, roles and authorization
Preserve all C7 representative ties in every C8 report. An explicit role-designation
approval identifies one Champion and one Challenger from the qualified registered
set for each profile, with rationale/provenance; hash cannot indicate merit.
No second eligible candidate -> no complete Champion/Challenger role assignment;
report NOT_RUN_ROLE_ASSIGNMENT. Same identity cannot occupy both roles for a profile.
Role identity and verification hypotheses are preregistered before CAL_VERIFY access;
C8 evaluates every declared role/tied alternative and multiplicity accounting includes
all assessments. No automatic next-best replacement on failure.
A failed role assignment requires separate registered research, not silent substitution.

### A11 Lifecycle and Manifest scope
Real VALIDATED/FROZEN requires all gates/role assignments with REAL_PIT_RESEARCH_VALIDATION
evidence and an explicit approval event bound to policy/assessment/threshold hashes.
C8 cannot confer OFFICIAL: C9 Holdout result and a subsequent explicit promotion approval
are required. HOLDOUT_READY and PROMOTED are NOT new lifecycle states.
Proposed immutable C8 artifact envelope:
schema/version, artifact_kind, evidence_scope, synthetic bool, source/checkpoint/code/
config hashes, validation_result, lineage, approval_event_ref, tax_mode, payload_hash.
SYNTHETIC_SOFTWARE_VALIDATION artifacts carry artifact_kind=SOFTWARE_ACCEPTANCE and
a separate fixture_manifest_payload plus simulated transitions. They have
official=false, research_state=null, promotion_authority=null, real_holdout_eligible=false.
They never create or register a real FreezeManifest/candidate state.
REAL_PIT_RESEARCH_VALIDATION artifacts may carry artifact_kind=RESEARCH_FREEZE_MANIFEST
and existing canonical FreezeManifest payload only after current evidence/approval
resolution. A forged scope field alone cannot qualify synthetic inputs. Missing scope
fails closed. Freeze scope is an evidence discriminator, not a lifecycle state.
Consumers require the real discriminator, real upstream inputs, all gates and current
approval before accepting a research Manifest; no producer/Web source changes.

### A12 Software Freeze
Complete deterministic synthetic positive algorithm fixtures and blocking negative
cases may support C8 SOFTWARE FROZEN ONLY after targeted, C0-C7, full, PIT/lineage/
Holdout/ledger/invalidation/cross-track audits and actual Actions/evidence binding.
The new contrasts/calibration/rounding procedures need independent expected outcomes,
boundary/metamorphic tests and documented limitations before acceptance.
No synthetic artifact supports real VALIDATED/FROZEN/OFFICIAL/Holdout eligibility.
Actual research qualification remains a separate NOT_RUN/PASS/FAIL result.

## 4. Alternatives
A1: reuse inner C4 Validation (less new data, but already involved in model pipeline
decisions); recommend separate outer interval with CAL_FIT/CAL_VERIFY.
A3/A4: deterministic conservative threshold ranking (requires additional result-impact
ordering across multi-dimensional incomparable vectors); recommend all-set evidence
plus explicit approver selection with no peak ranking.
A6: Bonferroni instead of Holm; paired linear mean-only contrasts instead of nonlinear
metric contrasts; recommend Holm plus explicitly versioned paired recomputation.
Neither method is approved by this package.
A8: require every metric separated (more restrictive); permit only economic separation
(omits statistical responsibility); recommend preregistered multiplicity-protected
one-or-more metric evidence in every required cohort.
A10: keep ties unresolved indefinitely; recommend explicit preregistered role identities.
A11: modify frozen C0 schema; recommend additive scope envelope preserving its API.

## 5. Result impact
A1-A4 alter available samples and frozen thresholds; A6-A9 alter qualification/skill/
distinctness; A10 alters eligible promotion identities; A11/A12 delimit real authority.
These are D3-P decisions, not implementation details or automatic consequences of006B.

## 6. Overfitting / lookahead impact
Outer reserved data and verify-only access prevent threshold fitting on assessed outcomes.
Full grids/families and immutable failed trials expose selection multiplicity.
No repeated verification, new metric picking, loser replacement or Holdout tuning.
Bootstrap assumptions and finite Monte Carlo precision stay visible; insufficient B or
invalid metric draws cannot be waived or repaired after results. Actual support/B/L/
alpha/limits still require pre-result research configuration and approval.

## 7. Recommendation
Approve A1-A12 as a METHOD/SCOPE contract only, subject to review of the proposed C8
contrast procedure. Then supply a separate complete registered real research config
before any actual research decision. Numeric template nulls are blockers, not defaults.
Implementation may start only after C7 Freeze and explicit Package A approval.
Package A approval alone does not authorize real Holdout consumption or actual promotion.

## 8. Exact approval target and implementation-ready interface
Approve/revise each A1-A12; select alternatives explicitly where changed. No authority
is inferred from silence or from approval of C7 execution.
Interfaces after approval: register_calibration(metadata, config, authority) ->
enumerate_calibration(CAL_FIT-only provider) -> freeze_thresholds(selection approval) ->
assess_candidate(CAL_VERIFY-only provider, resolved C6/C7) -> resolve_real_manifest().
Proposed files: evl/promotion_contracts.py, calibration.py, promotion.py, manifests.py;
tests/evl_c8_fixture.py, test_evl_c8_*.py; tools/track_c_c8_acceptance.py.
No fit/search callback or Holdout accessor enters these APIs.
Required negatives: calibration overlap/access-before-registration; model mutation;
changed config; wrong metric basis; incomplete multiplicity family; one DSR/Reality
view omitted; undefined ratio; hard fail offset; next-best fallback; synthetic
Manifest admitted as real; invalidated source/approval; budget/crash/duplicate assessment.
Prepared machine draft: track_c_c8_c10_contract_drafts.json. It is non-executable,
inactive and carries no real threshold values.
