# C7 implementation-ready contract preparation (inactive at policy boundary)

Recorded: 2026-10-01 10:45:14 UTC. Status: PREPARED / NO C7 RUNTIME ACTIVATED.
Authority: approved006B; policy choices G1/D2 remain PROPOSED, not active.
Source checkpoint15fed506d4e67d89861221281e4879002e431b4a.
Readiness means engineering interfaces are specified, not C7 acceptance or Freeze.

## Contract decomposition and exact access flow
C7.1 selection_contracts.py: immutable registration envelopes and explicit source refs.
C7.2 register_selection(metadata-only providers): persist metric/constraint/tolerance/
drift/coverage declarations BEFORE any target OOS value/provider access. Capture
registration hash, independent event checkpoint and first_selection_access event.
A matching old timestamp cannot turn already seen real outputs into preregistration.
C7.3 landscape.py: complete C5 domain identities plus every attempt (including failed,
rejected, early-stopped, invalidated, unattempted identities) and C4/C6 checkpoint refs.
Landscape inventory is never replaced by eligibility/frontier survivors.
C7.4 resolve_landscape(after_registration): current C5 inventory, C4 report/prediction
hashes, all17 C6 diagnostics and all required cohorts/folds, exact scope qualification,
ledger/budget/invalidation/provenance. Missing support=NOT_RUN; observed corruption,
nonfinite required input, forbidden partition/scope or invalidation=FAIL.
C7.5 selection.py: exact objective vector dominance, preserving every declared metric
x required cohort/fold independently. No hidden cohort averaging or tolerance.
C7.6 graph_vertices/edges/components: awaits G1/G2 D3-P clarification; no default.
C7.7 min C5 baseline-departure count on actual plateau/Pareto survivors.
C7.8 drift vector extraction/directions: awaits signed/magnitude D3-P clarification.
C7.9 restricted medoid: registered full domain ranges, constant coordinate0,
sum of squared distances to ALL own full component members among prior survivors;
all exact representative ties retained. No hash merit.
C7.10 profile candidate sets and all pairwise raw metric/cohort OOS differences.
C7.11 dedicated attempt budget/ledger, pending recovery, input/stage/output hashes,
invalidation events, fixtures and complete positive/negative acceptance.
C7.12 targeted C7 -> C0-C6 -> full -> PIT/lineage/Holdout/scope/cross-track audit ->
immutable evidence -> commit/push -> actual Actions -> all-mandatory SOFTWARE Freeze.
No .6/.8 interpretation or selected candidate is executed in this preparation.

## Proposed immutable payload fields
SelectionRegistration:
contract_id/version, approved_policy_id+blob hash, evidence_scope, configuration_scope,
registered_at, registration_event_checkpoint, target_access_epoch, source_checkpoint,
selection_code_commit/content hash, seed, max_attempts, tax_mode=EXCLUDED,
LandscapeCommitment, all3 ProfileDefinitions, MetricRegistrations, constraints,
required_cohort_fold_dimensions, plateau_tolerances, drift_dimension_registry,
explicit approved_graph_policy and drift_comparison_policy (currently UNRESOLVED).
Graph/drift unresolved -> no executable selection registration eligible for acceptance.

LandscapeCommitment:
complete registered candidate identities/parameters/evaluator/source experiment refs,
full domain grid and baseline, all charged C5 attempt refs/statuses, unattempted coverage,
four cohort/fold C4/C6 experiment/split/ledger/report/prediction hashes, source code/data/
dataset-vintage checkpoints, upstream provenance and invalidation resolver IDs.
A source commitment may be formed from already frozen metadata/checkpoint hashes
without selection-result access; full OOS package deserialization happens only after
selection preregistration. Provider interfaces separate metadata from result values.
C7 code hash is separate from retained C4/C5/C6 source code hashes; never rewrite ancestors.

MetricRegistration:
metric_id, exact JSON path, canonical EVL_METRICS_v1 formula ID/version, units,
oriented direction, ordered required cohort/fold IDs, required support/provenance,
derivation ID/formula/version if new and separately approved. No 'excess CAGR' alias.
Constraints:
metric path+formula+direction+unit+explicit value+config authority+registered coverage;
no null numeric default for real execution. Legitimate None metric is NOT_RUN.
Configuration scope SYNTHETIC_SOFTWARE_VALIDATION_ONLY is mandatory for fixture-only
values; it cannot satisfy REAL_PIT_RESEARCH_VALIDATION input eligibility.

StageEvidence:
ordered stage ID, complete parent input hashes, source/registration hash,
every candidate raw value and eligibility/exclusion reason, output IDs/tie sets,
FAIL/NOT_RUN details and affected scope, stage output hash, actual attempt identity.
ProfileCandidate:
profile/candidate/parameters/evaluator IDs, full tie set, serial representative hash
(optional ordering only), all stage/component references, metrics raw paths/cohorts,
scope, tax mode, lineage, official=false, skill/statistical/economic decision=NOT_ASSESSED.
Distinctness:
every profile/representative pair x registered metric x cohort/fold raw left/right/delta,
missing support/reason, registration/method/source refs; no C7 threshold or PROFILE_NOT_DISTINCT.

## Existing module adapters (no frozen source changes)
Reuse contracts.py ExperimentSpec/SearchBudget/TrialRecord; experiments.py dedicated
ExperimentLedger/TrialLedger; robustness.py source_inventory/candidate_identity/
c4_report/resolve_robustness; C3 evaluate_metrics; C2/PIT; walkforward.py digest/
exclusive write/pending recovery patterns. Current C1 metrics must be finite numbers:
rational stage values belong in immutable stage reports; terminal completion marker
may be a finite protocol metric, not an investment score.
Do not bypass complete real source resolution with caller-supplied JSON or old PASS.
C6 resolve requires complete raw ledgers/bundles, not just repository acceptance JSON.
C6 hashes/scales/frozen code/tests remain unchanged; C7 does not relax missing C6 family.

## Numeric and graph engineering
Canonical decimal text -> exact rational comparison using registered formula/units;
no epsilon, significance tolerance or quantization of upstream metrics. Preserve
original source numeric representation and exact canonical conversion declaration.
Metric similarity tolerances are only registered edge rules, never Pareto tolerances.
Connectivity ranges/diameters are diagnostics, not unstated cutoff gates.
Global Landscape identity remains full even when profile eligibility subsets differ.
Low Complexity and drift frontier do not mutate upstream source inventories.

## Ledger and invalidation engineering
Dedicated C7 directory/experiment registration; no C5/C6 append or overwrite.
Register planned selection/assessment attempt units and budget before execution.
Pending journal before work; terminal immutable report then ledger append; interrupted
attempt remains charged and cannot silently rerun/resample. Exhaustion=NOT_RUN_BUDGET.
SUCCESS/FAILED/REJECTED/INVALIDATED remain canonical TrialStatus; diagnostic FAIL/NOT_RUN
are separately reported. Invalidation references ancestors without editing old bytes.
Before supporting C8, re-resolve current input/stage/report/approval checkpoints.
Positive/negative acceptance must verify accounting units as well as complete stages;
unattempted budget paths remain visible and cannot count as PASS.

## Fixture and CI preparation
Fixtures are generic integrated-profile algorithm examples, not Investor-QGV.
Four required cohorts with explicit metric trade-offs, all stable components,
dominated bridges, isolated points, component chain diameter, C5 complexity ties,
coordinate/time drift trade-offs, constant domains, medoid ties, zero differences.
Negative cases: every mandatory stage FAIL/NOT_RUN; missing/bad metric; incomplete
family; wrong scope; future/missing provenance; report/source/config tamper; ancestor
invalidation; budget crash/duplicate/concurrent writes; hash-as-merit; next-best search.
Expected rejection tests prove blocking; they are not positive diagnostic PASS.

Existing tools/track_c_c6_acceptance.py currently permits only C6-specific new test
paths. Future C7 commit must extend the scope audit with an EXACT new-file manifest,
not broad exemptions, while verifying existing C0-C6 source/tests and four historical
C4 upstream repairs by original blob identity.
The C6 fixture CODE hashes the entire Python source tree. New C7 files legitimately
change a new fixture run's code/report hashes; regenerate the whole synthetic family
and retain old C6 evidence untouched. Do not claim identical historic acceptance hash.
Actual Actions required; no shell/pytest execution is available in this connector session.

## Freeze/stop state
Prepared contracts do not complete C7.1-.12 implementation. Targeted C7/positive
acceptance NOT_RUN_POLICY_BOUNDARY; C7 NOT FROZEN.7/11=63.6% retained.
Only actual complete acceptance permits8/11=72.7% SOFTWARE phase count.
Holdout UNCONSUMED; real research NOT_RUN; Investor-QGV FUTURE_TRACK_C_INPUT.
