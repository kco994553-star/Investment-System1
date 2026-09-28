# Track C C0 Acceptance Record

Contract: EVL_SPEC_v0.1
Upstream: Track A REAL-DATA BASELINE FROZEN_VERIFIED
Phase: C0 Experiment Infrastructure
Status: FROZEN

Acceptance criteria:
- [x] ExperimentSpec preregistration binds parameter space, search budget, dataset split, metric set, seed, code hash, data hash/vintage.
- [x] Official tax mode locked to EXCLUDED (Pre-Tax).
- [x] Append-only Trial Ledger records all terminal statuses and integrity hashes.
- [x] PIT guard enforces available_at <= decision_time and fails closed on missing provenance/vintage.
- [x] Freeze Manifest binds EVL spec, lineage, hashes, parameters/thresholds, profile, holdout state, promotion state.
- [x] Targeted regression PASS — 4/4.
- [x] Full regression PASS — 400/400.
- [x] Integration regression PASS — canonical diff contains only Track C EVL/CI/report/test additions; Track A/B/D/E mutation = 0.
- [x] No new D3-P.

Frozen after GitHub Actions run 36415764308 PASS. Upstream baseline remains b8e39a2 / Track A FROZEN_VERIFIED.
