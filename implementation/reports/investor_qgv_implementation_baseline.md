# Investor-QGV implementation baseline

Recorded 2026-09-30 KST. Parent implementation: `60b629026236bffb26875a2b708195023de4daf1`.
Canonical: `b8e39a2196a6d7794a04a0cd5393c68329e126ca`. Remote compare: 24 ahead / 0 behind; PR #4 OPEN DRAFT, not merged.

C0–C5 SOFTWARE FROZEN is preserved. Current-HEAD GitHub Actions run 36555849494 completed SUCCESS (2026-09-29). Retained C5 pytest evidence: targeted 103/103, full 499/499, normal-merge integration 499/499. This round independently replayed all 103 targeted and 499 full cases using an offline parametrized shim, NOT pytest. Source files were fetched by immutable Git blob SHA, verified against Git object hashes; shell Git fetch/clone failed because github.com DNS is unavailable. No new normal-merge replay or local Git history reconstruction is claimed.

The former configuration/evaluator issue is resolved for APPROVED controls: `evaluate_bound` passes cash_buffer into actual target weights and technical_lookback into actual Technical input windows; `test_evl_c4_bindings.py` checks changes in exposure, technical zones and integrated targets; `test_evl_c4.py` and C5 regression test bound calculations. Current code has no standalone `ProfileConfig` object. Undefined controls remain rejected. These implementations are reused, not rebuilt.

Investor-QGV behavioral inference is additive and does not require C6 execution modeling. Reuse C0/C1 ExperimentSpec/ExperimentLedger/TrialLedger/PITGuard, C2 splits and retained Train boundary, and C4 digest/journal/recovery primitives. C5 `register_search/run_search` cannot be reused for QGV weights because TC-D3P-002 explicitly permits only cash_buffer and technical_lookback. Investor weight search requires a separate additive contract; C5 approved semantics remain unchanged. C4 return-based metric runner is not mislabeled as behavioral OOS; reuse its split contract and accounting, with a behavioral scorer.

C6 / TC-D3P-003 remains PROPOSED / NOT APPROVED. No C6–C10 implementation authorized. No Track A/B/D/E/Web edits in this baseline record. Historical C4 common lineage repairs already present in parent remain preserved. No 13F-derived investor VALIDATED profile or Holdout/Forward result is claimed.
