# TC-D3P-006 A — C7 numerical selection contract

Status: PROPOSED / NOT APPROVED / NOT ACTIVE.
Scope: C7 Profile Selection only; approval is not profile promotion, C8 threshold
approval, Holdout consumption, automatic optimization or canonical merge.

## Repository authority gap

EVL_SPEC_v0.1 §4 fixes the order:
Pareto Frontier -> Stable Plateau -> Low Complexity -> Low Drift -> Representative Center.
Sections9/12 describe profile objectives, OOS distinctness and preference for simplicity.
No approved repository record defines cohort aggregation, plateau adjacency/tolerance,
plateau-size priority, drift aggregation, center distance or deterministic tie handling.
TC-D3P-001..005 do not approve these result-impact selection policies.
The same Landscape can produce different selected candidates under different choices.
C6 protocol PASS supplies computational integrity, not significance, skill or selection policy.

No C7 selected candidate, Champion/Challenger or acceptance result is produced by this proposal.
C7 stops at this new policy boundary. C8–C10 remain dependency blocked.

## Concrete proposed option A

1. Register one complete immutable Landscape before selection. Bind C5 whole candidate
   identities/attempts and all required C4/C6 research folds, Rolling/Expanding and
   Primary/Gap-stress cohorts. Re-resolve every ledger/report/input hash and invalidation.
   No surviving-subset substitution or post-result metric/cohort choice.
   All three profiles consume this same Landscape and retain all individual cohort values.
   Missing/nonfinite/incomplete evidence yields NOT_RUN; integrity violations yield FAIL.

2. Register each profile's exact metric paths/directions and explicit research constraint
   limits, plus required cohort/fold coverage. No numeric limit, profile weight or
   significance cutoff is defaulted. Preserve §9 objective families:
   Aggressive centers long-term arithmetic-risk-free-excess-supported excess CAGR with
   registered MDD/tail/turnover/OOS/risk-premium constraints; Balanced retains the
   CAGR/Sharpe/Sortino/Calmar/MDD/OOS/risk-premium vector; Defensive retains loss/downside/
   recovery/Sortino/real/risk-free-excess objectives and minimum growth.
   Any unsupported metric derivation requires explicit versioned provenance, never a
   substitute metric. Missing configuration blocks the affected selection.
   These are preregistered research selection filters, not C8 calibrated Promotion gates.

3. Aggregate each oriented metric conservatively: direction max uses the minimum across
   every required cohort/fold; direction min uses the maximum. Do not select a better
   Rolling/Expanding or Primary/Stress variant. Exact Pareto dominance requires no worse
   on every registered objective and strictly better on at least one. No weighted scalar
   objective, significance inference or implicit numerical dominance tolerance.

4. Define plateau adjacency on the preregistered fine parameter grid: one coordinate
   differs by one adjacent registered grid position, all other coordinates equal.
   An edge also requires absolute metric differences within each preregistered per-metric
   plateau tolerance in EVERY cohort/fold. Tolerances are explicit pre-result configuration,
   not chosen from the observed peak. A stable component has at least two candidates.
   Compute graph on the complete constraint-eligible Landscape, retain only Pareto candidates
   belonging to stable components, then retain components of largest cardinality.
   No plateau means NOT_RUN_NO_STABLE_PLATEAU, not peak selection.

5. Low Complexity uses the existing C5 count of parameter departures from its registered
   baseline; it cannot introduce an unrelated complexity score. Among retained candidates
   keep minimum complexity. Raw parameter/baseline/complexity evidence remains stored.

6. Low Drift uses C6 registered coordinate deltas/scales/time histories. For each cohort
   compute mean over time transitions of the sum of absolute normalized coordinate deltas;
   candidate drift is the maximum of these cohort values. Keep minimum drift among the
   prior-stage survivors. Missing coordinate/time/scale/history blocks selection.
   No effect-size/meaningfulness threshold or fitted drift weight is defaulted.

7. Representative Center: normalize each varying coordinate by its full preregistered
   domain range; constant coordinates contribute zero. Among prior-stage survivors,
   minimize sum of squared normalized distances to every member of its full stable component
   (restricted medoid). The final exact tie uses ascending immutable candidate identity
   hash solely for reproducibility. No tie breaker uses favorable unseen/OOS results.
   Retain all intermediate frontiers, components, raw values, exclusions and tie sets.

8. Register the OOS profile-distinctness metric paths and minimum separations before
   selection. Evaluate all selected profile pairs in every required OOS cohort using
   those explicit separations. A non-separated pair records PROFILE_NOT_DISTINCT.
   Missing separation configuration/evidence yields NOT_RUN. This does not silently replace
   a profile with the next-best candidate or re-optimize.
   Selected outputs are research ProfileCandidates only; no Official status, no skill.

9. Dedicated immutable C7 registration/Trial Ledger charges every selection/assessment
   attempt, preserves FAIL/NOT_RUN/invalidation and hashes every intermediate/output.
   Synthetic software acceptance is explicitly separate from real-PIT research selection.
   Proposed C7 software Freeze requires all algorithm/protocol acceptance paths on explicit
   deterministic fixtures, including independently verified Pareto/graph/complexity/drift/
   medoid/distinctness expectations and blocking negative cases. A synthetic candidate is
   never a real profile, skill or promotion input.
   Actual research configuration remains absent until explicitly preregistered.
   C8 still owns threshold calibration, hard gates, statistical/economic skill decisions
   and Freeze Manifest; C9 owns once-only sealed Holdout; C10 owns actual Forward monitoring.

## Effect, compatibility and validation

Existing: selection order only, no executable numerical policy.
Proposed: the deterministic rules above and explicit mandatory preregistration fields.
Reason: implement C7 without inventing thresholds or selecting an arbitrary formula.
Impact: changes which research representative/profile is selected; requires D3-P approval.
Compatibility: preserve C0–C6, EVL_SPEC_v0.1, QGV/Technical/Macro formulas, Official/Custom
isolation, Track A/B/D/E/Web, TAX_MODE=EXCLUDED and complete lineage. No real Investor-QGV.
Validation after approval: implementation -> C7 targeted -> C0–C6 regression -> full ->
PIT/lineage/Holdout/cross-track audit -> immutable evidence -> commit/push -> Actions ->
software Freeze judgment. PR #4 stays Draft/Open/unmerged.

Approve TC-D3P-006 A items1–9 as a general C7 policy, or provide an exact alternative
for the affected item. No actual research numerical values are approved by option A;
each remains a required explicit pre-result configuration. No C8 policy is bundled.
