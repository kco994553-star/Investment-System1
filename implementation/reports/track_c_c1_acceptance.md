# Track C C1 Acceptance Record

Contract: EVL_SPEC_v0.1 §4–5. Phase: C1 Experiment Ledger.
Status: **FROZEN — SOFTWARE ACCEPTANCE ONLY**
Recorded: 2026-09-28T20:42:40+09:00
Baseline: canonical b8e39a2 / Track A FROZEN_VERIFIED.
Validated remote implementation: 5db4acfa0baedbf0d2e0bf4f80b2cc04d8b5bb45.

## Acceptance and evidence

| Acceptance criterion | Result |
|---|---|
| One-time ExperimentSpec registration before trials; seed/space/budget/split/metrics/code/data/vintage bound by digest | PASS; registration snapshot survives caller mutation; repeat and post-result registration rejected |
| Every terminal status retained append-only | PASS; original bytes preserved, failures/rejections/stops consume search budget, invalidation appended as an event |
| Unlogged/failed/invalidated/unregistered/out-of-space/incomplete results cannot support promotion | PASS; supporting_trial resolves eligible evidence only, never promotes |
| Tampered/malformed/partial ledger blocks reads/appends; invalid finite metrics blocked | PASS |
| Duplicate IDs/sequence and concurrent writers | PASS; POSIX advisory lock, flush and fsync; colliding sequence admits exactly one writer |
| C0 envelope/API compatibility and Pre-Tax contract | PASS; legacy envelopes remain readable without rewriting; original C0 tests pass |
| Targeted regression | 24/24 PASS (4 C0 + 20 C1 cases), real pytest |
| Full regression | 420/420 PASS, real pytest |
| Normal-merge integration regression | 420/420 PASS against canonical b8e39a2, real pytest |
| Ownership audit | Track A/B/D/E runtime/data/spec mutations = 0 |
| GitHub Actions | run 36417028774 SUCCESS on 5db4acf |
| New D3-P required for C1 | None |

Logs: track_c_c1_targeted_regression.txt, track_c_c1_full_regression.txt,
track_c_c1_integration_regression.txt. Boundary/commit metadata:
track_c_c1_integration_boundary.json.

Integration merge was local and disposable; PR #4 remains draft/unmerged.
Local tested implementation a74d5df and remote implementation 5db4acf have the
identical tree 48f468b8931e63e41aec6b4453787e562133d3e8. The connector created the
remote commit because shell push had no credentials; no history was force-pushed.

## Limits and phase boundary

Local POSIX storage requires cooperating writers and protected filesystem access.
Hash/sequence checks detect corruption, not malicious whole-file replacement or
undetectable tail removal without an external trusted checkpoint. This module
cannot discover trials performed entirely outside the registered runner; later
C5/C8 integration must route all trials and promotion evidence through this ledger.
Over-budget attempts are preserved but cannot support promotion; stopping the
optimizer before exceeding budget belongs to C5. Precision/complexity search
constraints belong to C5 and no current API claims to enforce all promotion gates.

No real experiment, skill, profile distinctness, statistical calibration, Holdout,
Official promotion or Forward Validation is claimed by this software Freeze.
EVL_SPEC_v0.1 is unchanged. C0/C1 are complete; C2 is D3-P_PENDING for
EVL-SPLIT-01 v1.0, documented in track_c_c2_split_policy_proposal.md.
C2 runtime and C3–C10 were not started; approval has not been inferred.
