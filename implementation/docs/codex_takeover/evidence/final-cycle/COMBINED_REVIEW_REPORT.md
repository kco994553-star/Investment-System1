# Combined exact-SHA review and RIG integration guard repair

Reviewed combined trial `bfa3e26a6fad894bfde7d96149f9d05555bac53c` read-only.

Preservation PASS:

- Track C owner `b9e01a97`: all 43 EVL source/fixture/test files identical.
- Pre-C8 baseline `86e345e5`: all 232 existing source/test blobs identical.
- Canonical `b8e39a2`: all 18 QGV math source files identical.
- Canonical raw/data and gate evidence: all 7,323 tracked blobs identical.
- Approved four C-28 source files: byte-identical to owner `b9e01a97`.

The new producer compatibility helper accepts only exact legacy or approved
C-28 `models.py` bytes and independently verifies the entire original AST after
removing exactly the eight optional Technical/Macro lineage declarations.
Other shared sources still require byte identity. QGV/Leaderboard compatibility
guards reject partial/unloadable or incomplete infrastructure and run their
existing complete probes in integrated trees. Historical dependency pins remain
distinct from actual integrated source references. No new scoring, ranking,
publication or Official authority is introduced by the reviewed code.

The new workflow has `contents: read`, Python 3.11, exact owner/canonical
preservation checks and offline existing fixtures/known retrospective exports.
It does not dispatch the QGV rebase workflow or enable a live provider.

One additional LOCAL_FIXABLE test guard defect was found: RIG considered a
missing entire entity_metadata directory to mean original branch isolation,
even when the integrated HEAD committed its registry. A synthetic mock made the
existing full registry test PASS while no working registry read occurred. The
committed source and real directory were never mutated during reproduction.

The root then authorized a test-only repair in an isolated worktree. Commit
`0366a3c3f9b9b3281173af58d250418d3a67f4c0` on
`codex/rig-registry-guard-2026-10-03` has direct parent/merge-base `bfa3e26`.
Worktree: `/workspace/rig-registry-guard-review` (clean).

Only `implementation/tests/test_rig_news_ingest.py` changed. The caller now
resolves required registry presence from `git ls-tree HEAD` and checks the exact
pinned committed Git blob. An integrated registry's whole directory/file must
exist and its bytes remain pinned. True original HEAD absence is preserved.
Git command failures or unavailable Git fail closed. Negative regressions cover
whole directory deletion, isolated HEAD absence, Git failures, and changed
committed blob; fixtures mock subprocess responses without changing repository
artifacts.

Exact-head targeted verification: **20 passed** with Python 3.11.16 / pytest
9.1.1. Log `rig_registry_guard_exact_head_pytest311.log` SHA256:
`033fb2c250179ef897c71b5e827c29cc42a4963d2e60fca95af2a591d57b8fd8`.
Test file SHA256:
`46b090b9f63f814e98f134851f35fa4b0a7a8a6e12b426fb23fb3c2693172627`.

BRANCH_STATE: local committed repair, targeted PASS. INTEGRATION_STATE: ready
for root normal merge and fresh full/Actions verification. CANONICAL_STATE:
NOT_MERGED. Maturity unchanged; no USER_DECISION_REQUIRED for this approved
guard repair. Full combined tests and Actions were NOT_RUN by this reviewer and
remain root-owned evidence. No production/Frozen source or statistical
convention changed.

Machine evidence: `combined_review.json`. Next autonomous action: root merges
the exact repair commit preserving history, then finishes fresh final-HEAD
combined regression and CI before updating the Draft integration proposal.
