# F1 independent source-protection review

READ-ONLY review of source commit `675d0d298fbaab5b8473ed048a561ef84e2f3e78` and routing commit `6cd7eeedda28e3a15bf8e27655d35d2b4d9ee971`.

The QGV/Leaderboard SHARED union contains 11 files: exact-state `models.py` plus 10 non-model files. Every non-model file in the source commit is byte-identical to canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`. The inventory records Git blob IDs and SHA256 values. Independently running the old helper with the same directory and an unrelated mutation of `qgv/scoring.py` returned PASS, reproducing the vacuous self-comparison.

## Baseline trust and scope

The proposed repair is an implementation compatibility fix under CDR-004. The canonical source commit is a fixed exact Git object, not a current branch or HEAD. Baseline lookup must use the helper-owned implementation directory; caller source roots must not select the baseline repository. Exact-object identity provides the content trust, assuming ordinary Git object integrity. Missing Git executable, object or path must produce FAIL without reading a working file or another revision as fallback.

Same-resolved-path comparisons, including symlink aliases, must independently compare every non-model shared body against that exact baseline. Both supplied bodies must exist. Models retain their existing two exact approved byte states and complete original AST guard, including the explicitly supported mixed pre/adopted pair. Distinct source paths retain the pre-existing BYTE_IDENTICAL behavior; they do not gain independent canonical protection in this bounded repair.

## Meaningful acceptance cases

- All 10 canonical non-model files pass; each individual dirty mutation fails even when both arguments point to it.
- A symlink alias to the same directory follows the protected same-tree path.
- Missing current file fails.
- Unavailable baseline Git/object/path fails without fallback or exception escaping the compatibility result.
- Distinct external equal sources pass and unequal sources fail as before.
- Exact old/adopted models, mixed pair and identical unapproved models retain prior acceptance/rejection behavior.
- Reports distinguish SAME_TREE canonical protection from external byte comparison and name the exact baseline SHA/path/hash.

## Limits

This review does not authorize or change any investment semantics, Frozen file, numeric configuration, source taxonomy, grant, owner/canonical branch or publication. Git repositories or configuration deliberately subverted by a privileged operator are outside this helper-level threat model. Distinct equal untrusted copies remain pair comparisons by design; broadening their contract would be a separate scope.

## Final review result

PASS, no blocking finding. The final helper uses `git --no-replace-objects` and a fixed helper-owned lookup directory. Independent focused regression executed on CPython 3.11: `tests/test_producer_source_compat.py` — 25 PASS. The reviewer also ran 21 standalone expected-result cases, all matched. These include 10 single-file dirty mutations, missing source/object/path/Git, symlink alias, unchanged distinct-tree behavior, mixed models, an unrelated caller repository, and an actual replacement ref in a disposable fixture. Ordinary lookup used the replacement content; the reviewed helper ignored it and rejected the changed bytes.

The final reviewed helper SHA256 is `8c059e443763136d12769c7ba9ef3e2389850a2d61ea0ee63d5a355c1fc6d892`. Tests and standalone probes used the writer's working delta based on `675d0d298fbaab5b8473ed048a561ef84e2f3e78`; no claim is made about a later commit until the writer verifies that hash. Full suite and Actions were NOT_RUN by this reviewer. No protected repository source or original Git reference was modified. All fixture Git objects and replacement refs were disposable under the review evidence directory.

BRANCH_STATE: READ_ONLY_REVIEW_PASS_ON_HASHED_DELTA.
INTEGRATION_STATE: HELPER_SCOPE_VERIFIED; parent integration pending.
CANONICAL_STATE: NOT_MERGED, unchanged by this review.
USER_DECISION_REQUIRED: false for this bounded compatibility fix.

