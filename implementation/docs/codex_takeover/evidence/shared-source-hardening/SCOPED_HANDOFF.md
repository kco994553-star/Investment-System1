# F1: integrated shared-source protection

Source commit `8b10c258d0ce92159c25491263c0fb08ae0e7738`, branch
`codex/shared-source-protection-2026-10-03`. Base/merge-base:
`675d0d298fbaab5b8473ed048a561ef84e2f3e78`. Fresh upstream routing:
Global `6cd7eeedda28e3a15bf8e27655d35d2b4d9ee971`, GIE-006 F1.
This is an implementation protection repair under existing CDR-004, with no
new formula, threshold, default, numeric configuration or adoption convention.

The before implementation compared each non-models SHARED file with itself in
SAME_TREE. A deterministic probe changed each of the actual ten protected paths
independently: all ten incorrectly returned PASS. The same ten altered inputs
now return FAIL. Before/after per-path receipts are committed here.

When source directories resolve to the same tree, every non-models shared path
now compares actual bytes to its exact canonical
`b8e39a2196a6d7794a04a0cd5393c68329e126ca` Git blob. The lookup runs from the
helper's own repository, with `--no-replace-objects`; caller source, unrelated
Git HEAD, moving refs and local Git replacement refs cannot become the baseline.
Missing Git, commit object or baseline source file gives a structured FAIL with
explicit baseline-unavailable metadata, without falling back to self-comparison.
The report exposes exact baseline commit, path and SHA256 for every protected file.

The original models acceptance policy is unchanged: only exact canonical or
approved C-28 bytes pass, with the existing full AST preservation check. External
old/adopted mixed pairs remain accepted in either direction. Distinct external
trees retain their original byte-pair comparison. This repair addresses the
SAME_TREE defect; it does not expand external routes into new canonical policy.

Actual native CPython3.11.16 / pytest9.1.1 validation:

- Exact675 baseline: nine targeted cases PASS in1.02s.
- Final source: 27 targeted cases PASS in1.25s: 25 helper cases plus complete
  QGV and Leaderboard compatibility probes, without skipping or weakening them.
- The18 added cases cover both exact accepted models controls, every actual
  non-models path mutation, same-resolved symlink alias, missing baseline
  object/path/Git and both mixed-model directions.
- Exact `producer_engine_fingerprint.py` executed before/after: stdout is
  byte-identical, SHA256 `f690f9c08b6b2692af5c0c1cdfc957c768ffa13841406f837f4f899518320866`.
  Technical/Macro/QGV/Leaderboard/Portfolio values and decision outputs are
  unchanged. The helper itself reads source and never executes scoring code.

An independent read-only reviewer reproduced 25 targeted PASS and21/21 expected
results, including an actual Git replacement-ref counterexample in a disposable
fixture. Ordinary lookup read replacement content, while this helper used the
original object and rejected the mutation. Original repository refs, owner
source and remotes were untouched. Separate reviewer evidence is copied under
`independent-review/`, with execution attributed to that reviewer.

Only two existing files changed: the helper and its non-Frozen protection tests.
All215 existing `implementation/src` files remain byte-identical. Existing EVL,
Frozen tests/manifests, G-SUP source/evidence, owner records, model hashes and
lineage constants are unchanged. No workflow, pin or investment source changed.

This is a protection delta, with overall software maturity still
SYNTHETIC_VERIFIED. BRANCH_STATE is locally committed and validated;
INTEGRATION_STATE awaits parent normal merge and final combined regression;
CANONICAL_STATE remains NOT_MERGED. Full suite, Actions, push and canonical merge
were NOT_RUN by this worker. Actual CAL_VERIFY and Holdout remain untouched.
There is no USER_DECISION_REQUIRED for this LOCAL_FIXABLE defect.

Parent next action: normal history-preserving merge, final combined regression
and actual Actions receipts for the final proposed source. Scoped exact hashes
and preservation evidence are in `CHECKPOINT.json`.
