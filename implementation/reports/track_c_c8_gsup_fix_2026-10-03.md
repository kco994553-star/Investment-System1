# Track C C8 G-SUP fix addendum — fail-open paths inside approved Q3 / Q4·A6-S4 (2026-10-03)

Fix commit `9a9364c` (ccr-22e3ff16-p7n5k5), on top of `97d1b94`. Trigger: independent read-only audit relayed by the
Primary Integration Writer (GIE-004 on origin/integration/global-handoff-v1 @ cc9570b). Both findings were reproduced
independently in this session before fixing. Policy unchanged; this enforces already-approved rules only.

## (a) Q3 Development-only provenance was not enforced at the feasibility entry points
Reproduced: estimate `{phi:-5.0, dataset_role:CAL_VERIFY}` accepted, status FEASIBLE.
Fix: `GsupRegistry.record_feasibility(key, development_series, dataset_role, dataset_id)` computes the estimate itself.
`validate_estimate` (called by `assess_feasibility` and `combined_envelope`) requires exact fields, `DEVELOPMENT` role,
registered estimator, dataset id equal to the new registration field `development_dataset_id` and different from the
CAL_VERIFY id, n ≥ 3, φ ∈ (−1, 1), and an intact `estimate_hash`.

## (b) Q4 / A6-S4 one-shot no-retest was not enforced across campaign_id or registry roots
Reproduced: a second assessment of the same verify dataset under a new campaign with changed α/seed was accepted, and so was one from another registry root.
Fix: new registration field `verify_content_hash` (preregistered CAL_VERIFY content commitment). Feasibility verdict,
access intent and result live in an explicit shared `access_registry`, keyed by (content commitment, profile, role) only,
independent of campaign_id, role_id, dataset label and registry root. Any later registration for a spent/verdicted key
is refused (`no retest`), which also blocks feasibility shopping with a changed L/α/B/seed. Provider content must match the commitment.
Champion and Challenger on the same content remain separately assessable.

## Verification (local; no Actions — workflow triggers on feature/track-c-evl only)
G-SUP 81 (68 + 13 new regressions), C8 targeted 197, C7 97, C6 130, C0–C5 103, full 923 PASS; C6/C7/C8-partial acceptance
exit 0 with no unauthorized/unexpected files. Log: `track_c_c8_gsup_fix_local_verification_2026-10-03.txt`.

## Remaining limitations (not closed)
- One-shot protection assumes one trusted shared access registry; passing a different `access_registry` path is not
  detectable locally (same trusted-storage boundary as the foundation `AccessRegistry`).
- G-SUP access is not yet unified with the foundation CAL_VERIFY `ACCESS_INTENT` registry (calibration_ledger.py); the two
  modules could each consume the same CAL_VERIFY once. Unification needs a design decision (no real CAL_VERIFY access exists).

## Disclosure for the user's method decision (no code change made)
- The Q1 approval evidence (`track_c_c8_a6_method_simulation_source_2026-10-02.py`) used replicate variance over
  ceil(n/L)−1 blocks and scored degenerate replicates as never exceeding. The implemented kernel uses n//L full blocks and
  scores degenerate replicates/ties as exceedances. These coincide only when L does not divide n and no replicate is
  degenerate, so the approved size table does not exactly describe the implemented kernel. Size of the implemented
  convention is measured separately in the 5-item impact analysis (items 3/4).
- `tests/evl_c8_gsup_oracle.py` is independent code but encodes the same (unapproved) conventions as the kernel; it
  verifies arithmetic, not the choice of convention.
- These are part of the five implementation-defined method details still awaiting the user's decision.

C8 NOT FROZEN; 8/11 = 72.7%; A8/A10 NOT APPROVED; Holdout UNCONSUMED; no CAL_VERIFY access; numeric configuration unapproved.
