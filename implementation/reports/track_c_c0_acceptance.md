# Track C C0 Acceptance Record

Contract: EVL_SPEC_v0.1
Upstream: Track A REAL-DATA BASELINE FROZEN_VERIFIED
Phase: C0 Experiment Infrastructure
Status: VALIDATION_PENDING

Acceptance criteria:
- [x] ExperimentSpec preregistration binds parameter space, search budget, dataset split, metric set, seed, code hash, data hash/vintage.
- [x] Official tax mode locked to EXCLUDED (Pre-Tax).
- [x] Append-only Trial Ledger records all terminal statuses and integrity hashes.
- [x] PIT guard enforces available_at <= decision_time and fails closed on missing provenance/vintage.
- [x] Freeze Manifest binds EVL spec, lineage, hashes, parameters/thresholds, profile, holdout state, promotion state.
- [ ] Targeted regression PASS.
- [ ] Full regression PASS.
- [ ] Integration regression PASS / no upstream Track A/B/D/E mutation.
- [ ] No new D3-P.

Do not mark FROZEN until all unchecked criteria pass.
