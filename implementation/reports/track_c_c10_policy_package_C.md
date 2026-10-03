# Package C — C10 Forward monitor / evidence / lifecycle proposal

Status: PROPOSED / NOT APPROVED / NOT ACTIVE. Recorded: 2026-10-01 10:45:14 UTC.
Checkpoint:15fed506d4e67d89861221281e4879002e431b4a.
Preparation only. No actual future observation, Forward prediction/result, Official
profile, scheduler or producer connection is created. Synthetic simulations are
never stored as actual Forward evidence.
Authority: EVL_SPEC_v0.1 sections2/3/7/8/10/11; C3 conventions; approved upstream
availability/lineage; C6 raw drift evidence. Packages A/B remain unapproved dependencies.

## 1. Current contract
Live Forward is real-time validation after promotion. Canonical lifecycle includes
OFFICIAL -> FORWARD_MONITORED -> FORWARD_VALIDATED with existing exception states.
No automatic promotion or reoptimization. Tax excluded; core scores immutable.
Dataset/Universe/source/Official snapshot invalidation propagates to downstream
SUSPENDED/INVALIDATED and dependent results cannot remain Official.
Past predictions/snapshots cannot be overwritten after outcomes.

## 2. Unresolved decisions
Forward start/effective schedule; monitoring/evaluation cadence; horizons/minimum
support; parameter/input/performance drift definition and limits; warning/suspension/
invalidation mappings; missing/stale/revised data; recovery; statistical sequential
evaluation; Forward validation decision; explicit approvals and software Freeze scope.
No numeric cadence/support/threshold/freshness default is supplied by the repository.
A producer infrastructure branch exists but supplies no real qualified EVL family,
monitoring cadence or economic drift authority.

## 3. Proposed contract — exact approval items C1-C12
### C1 Activation and Forward start
Require resolved real OfficialProfile, accepted real Holdout result, current source/
role/approval lineage, and an explicit Forward activation approval naming profile/
code/config/plan/source hashes. Register the complete decision/rebalance calendar.
Forward start is the FIRST eligible registered decision timestamp STRICTLY AFTER
the actual Official promotion approval timestamp. No backdating to fit prior results,
same-time retroactive prediction or replacement of a missing first slot with an
unregistered favorable start. Preserve missed registered slots as NOT_RUN events.
A user-supplied future effective start may delay activation only if preregistered;
the effective start is the first registered eligible slot strictly after promotion and at or after the approved future start.
No date or trading/calendar conversion is guessed.

### C2 Cadence / horizons / support
Preregister an explicit schedule/calendar ID and timestamp set/rule, evaluation
horizons, maturity/publication cutoffs, required cohorts/benchmarks, observation counts,
minimum calendar span, allowed missing-data coverage and planned review points.
Values and data freshness limits must come from separate approved real config.
Prediction cadence, outcome horizon, monitoring cadence and approval review cadence
are distinct. A complete event history is required; missing timestamps cannot be
removed to create apparent complete support. Unequal periods require an approved
upstream adapter; C3 regular-period conventions are unchanged.
C2 annual research reoptimization is not automatic Forward reoptimization authority.

### C3 Prediction before outcome
At each registered decision_time resolve real, non-estimated, non-synthetic stamped
inputs with available_at<=decision_time, source/vintage/content hash and exact frozen
model/parameters/thresholds. Persist prediction, decision_time, actual generated_at,
input/model/config/code/profile hashes and execution intent BEFORE outcome access.
No label enters predictor; no fit/calibrate/search hook. Delay/missed prediction is
recorded and cannot be backfilled as a timely real prediction.
Each record carries evidence_scope=REAL_PIT_RESEARCH_VALIDATION, event_kind=FORWARD,
and temporal_origin=ACTUAL_FORWARD; all must be resolved against actual upstream bytes.
A scope/origin string alone does not prove real data or actual timing.

### C4 Outcome maturity and append-only storage
Attach a separately stamped outcome event only after its horizon ends and outcome/
inflation publication is available at evaluation_time. Register risk-free inputs at
period start; inflation is ex-post attribution only.
Immutable keys: profile_version + decision_time + prediction_id + horizon_id.
Outcome revisions are new versioned events referencing the original prediction/
outcome; never overwrite historical original-vintage scores.
Persist registrations, prediction/outcome events, every failed/missed attempt,
monitoring reports, decision approvals, invalidation and external checkpoints.
Use per-profile/event namespace, exclusive idempotent writes, append-only journal,
hash-chain verification and externally retained checkpoints. Pure local hash chains
do not establish that a prediction existed before publication; real execution needs
independent timestamp/checkpoint retention. Infrastructure choice requires review,
not an invented security assertion.

### C5 Financial monitoring and planned decisions
Reuse exact C3 gross/net/real/RF views and frozen Package A gate definitions/limits,
registered benchmarks, execution/provenance and support. Report per-window/cohort
raw results and no-lookahead/support status; do not pool favorable windows.
Descriptive monitoring can run at the preregistered cadence; qualification decisions
occur only at preregistered mature non-overlapping decision windows.
Recommend fixed-horizon confirmatory reviews with a preregistered family-wise budget
across all planned windows/profiles/hypotheses (Bonferroni allocation of the approved
family alpha by the explicit planned review count; allocation values registered).
No optional stopping/indefinite repeated p-value testing. Adding reviews or adaptive
horizons requires a new policy/config and cannot reuse earlier outcomes as fresh tests.
Alternative sequential alpha-spending/e-process design is stated below and unapproved.
Missing complete aligned support -> NOT_RUN; invalid evidence -> FAIL.

### C6 Parameter drift
Model/parameters remain exactly frozen. Report each coordinate signed delta from the
approved frozen reference using its already registered C6 scale, and preserve all raw
values/times. If C7-D2 is approved, also report absolute scaled vector magnitudes.
Any UNAUTHORIZED frozen-parameter/threshold mutation is an integrity violation,
not acceptable drift, and immediately revokes usability.
An explicitly approved new version is a new lifecycle/research campaign with full
evidence, not automatic annual retuning inside the existing Forward monitor.
No weighted scalar aggregate or inferred investment significance.

### C7 Input / performance drift
These are separate from parameter drift. Before first Forward observation, register
exact variable IDs, reference interval/vintage, benchmark IDs, directions, formula
versions, window/coverage/support and coordinate-specific warning/suspension limits.
Recommended input diagnostic: each registered current-window feature mean minus
the frozen reference-window mean, divided by a strictly positive preregistered
reference scale; retain signed and absolute coordinate values separately. No fitted
Forward weights/scales, pooled feature score or post-result window selection.
Recommended performance diagnostic: each exact C3 metric value minus its preregistered
reference value, with direction declared per metric; preserve censoring/undefined
results and every window. Registered gates can inspect these components directly,
without a composite scalar.
These formulas/limits are NEW proposed policy. Units, reference feature distributions,
actual thresholds/support and significance procedures remain unspecified real config;
do not use synthetic illustrations as real baselines. A materiality claim needs its
own registered economic/statistical criterion, not a nonzero difference alone.

### C8 Warning / suspension / invalidation
Use warning as report metadata, not a new promotion lifecycle state.
Missing/late/stale/unverifiable required inputs or support -> NOT_RUN evidence and
artifact usability SUSPENDED under EVL section11, with no emitted usable Official
output until recovery approval. Preserve the prior lifecycle history.
Observed upstream invalidation, tampering, forbidden lookahead, synthetic-as-real
input or unauthorized parameter/threshold change -> INVALIDATED for dependent
artifacts and immediate revocation of usable Official status.
Statistical/economic hard-gate failure or an approved suspension-limit crossing ->
SUSPENDED usability pending explicit review; never automatic reoptimization/promotion.
Registered warning-limit crossing -> warning report; no automatic suspension unless
the separately preregistered rule requires it.
The active resolver must report official=false for suspended/invalidated artifacts
even when a historical immutable event says OFFICIAL. No cosmetic state reset.

### C9 Data outage / revision / recovery
No interpolation, zero filling, hindsight replacement vintage or latest-source join.
Record each absent/missed slot; a late realized outcome may append only as late
evidence bound to an existing timely prediction. An absent prediction cannot be
reconstructed after outcomes for qualification.
Revisions append source-version and impact records; rerun eligible attribution only
against the SAME immutable prediction and frozen policy, preserve both vintage results,
and suspend current usability if the approved result changes qualification.
Recovery requires complete verified missing/source evidence, unchanged profile/config,
current invalidation resolution, provenance/coverage audit and explicit recovery
approval. An invalidated version cannot be silently restored by replacing its source;
new qualified research/version is required. No fabricated actual observation.

### C10 Forward validation decision and lifecycle
FORWARD_MONITORED requires actual activation plus at least one real timely persisted
prediction; not just installing a monitor or running a synthetic fixture.
FORWARD_VALIDATED requires all preregistered minimum support/span/windows, every
mandatory universal/statistical/economic/drift gate, no unresolved suspension/
invalidation and an explicit validation approval naming the complete evidence hashes.
Missing support=NOT_RUN, observed failed gate=FAIL; no successful metric offsets a
mandatory failure. No automatic promotion, recovery, role replacement or parameter
research. RESEARCH_REOPENED remains the existing explicit review path with a new
registered trial/evidence campaign; old Forward evidence stays historical.
This package confers no actual promotion/activation/validation approval.

### C11 Synthetic clock/event fixtures
Use a wholly separate store/clock/source namespace:
evidence_scope=SYNTHETIC_SOFTWARE_VALIDATION,
configuration_scope=SYNTHETIC_SOFTWARE_VALIDATION_ONLY,
temporal_origin=SIMULATED, official=false, real_research_state=null.
Injected clock sequences test decision -> prediction -> horizon maturity -> publication
-> outcome -> monitor -> review; simulated review events never become real approvals.
Test actual code scheduling/persistence with deterministic synthetic events; no fixture
event is exported as ACTUAL_FORWARD and no real producer is changed.
Scope enforcement rejects mixed histories and forged origin with synthetic source.
No real Holdout accessor belongs in C10; consume only immutable authorized C9 evidence.

### C12 Software Freeze
Complete algorithm/persistence/scope/negative acceptance on synthetic fixtures may
support C10 SOFTWARE FROZEN after targeted->C0-C9->full->PIT/lineage/Holdout/ledger/
budget/invalidation/cross-track audits->actual Actions->immutable evidence binding.
Software Freeze does NOT require invented future data and does NOT grant real
FORWARD_MONITORED/FORWARD_VALIDATED. Actual Forward remains NOT_RUN until genuine
activation/timely observations; minimum elapsed time cannot be simulated as real.
After C0-C10 software Freeze, implementation baseline may be recorded separately
from research/Official/Forward readiness. Investor-QGV remains FUTURE_TRACK_C_INPUT.

## 4. Alternatives
C1: promotion timestamp itself versus next eligible slot; recommend strictly later
registered slot to make pre-outcome generation enforceable.
C2: daily/weekly/monthly defaults versus explicit producer/calendar config; recommend
explicit real config because calendars/horizons are data contracts, not guessed values.
C5: sequential alpha-spending/e-processes allow continuous confirmatory review but
require another mathematical approval and independently verified method; recommend
fixed planned review family for baseline.
C7: Wasserstein/PSI/KS or fitted composite scores add statistical/weight assumptions;
recommend transparent coordinate diagnostics with explicit limits, not an aggregate.
C8/C9: automatic restoration after outage versus explicit verified recovery; recommend
explicit approval and retained failures. Permanent invalidation for every outage is
more conservative but conflates missing evidence with proven integrity violation.
C10: monitoring-only baseline never labels FORWARD_VALIDATED; recommend implement
validation protocol in software but require actual evidence/time/approval for real state.

## 5. Result impact
Start/support/windows determine evaluation eligibility; sequential control affects
statistical conclusions; drift/limits/failure mapping affect continued usability;
lifecycle approvals affect Official/Forward authority. These are D3-P, not C7 authority.

## 6. Overfitting / lookahead impact
Timely predictions and external checkpoints prevent hindsight backfill. Frozen
references and planned reviews prevent drifting baselines and optional stopping.
No synthetic time passage, favorable-window filtering, threshold retuning or
unregistered source revision may improve a claimed real Forward result.

## 7. Recommendation
Approve/revise C1-C12 as a software/method scope contract after prior dependencies,
then require separate complete actual config and attributable real activation.
No producer schedule, actual Forward start or minimum support value is approved here.

## 8. Exact approval target and implementation-ready interface
APIs: register_forward_plan(metadata/config/authority) -> resolve_official_profile() ->
record_prediction(PIT-only provider, actual clock/checkpoint) ->
append_mature_outcome() -> monitor_registered_window() ->
review_forward(evidence, explicit approval) -> propagate_invalidation()/recover().
Proposed files: evl/forward_contracts.py, forward.py; tests/synthetic_forward_events.py,
test_evl_c10_*.py; tools/track_c_c10_acceptance.py.
Required negatives: naive/future/estimated availability; outcome before prediction;
late/backfilled prediction; wrong horizon/calendar; insufficient support; duplicate
event/concurrent writers; source/vintage revision; tampered checkpoint; synthetic
event as real; parameter mutation; missing/stale inputs; invalidated ancestor;
optional unplanned review; automatic recovery/reoptimization; actual Holdout accessor.
Prepared machine draft: track_c_c8_c10_contract_drafts.json; inactive, no future data.
