# Discovery company execution plan

Spec: implementation/docs/research/discovery_company/CONTRACT.md, owner instruction.
Base: ab6a83c3be2276abdcf855c71c5f273926e2dcc4. Worktree: discovery-company.

1. Contract + synthetic six-state vectors, no real company fixtures. Reuse raw
   store and common issuer contract. Main gets contract before real research completes.
2. RED: source/hash/date/identity, six gates, null awareness, counterevidence,
   state transitions, targeted update/dedup, immutable replay, CLI output tests.
   GREEN: stdlib-only producer and offline CLI. No production/UI/guard changes.
3. Run 1–3 held companies with exact existing raw receipts. Preserve private
   inputs, results, coverage and costs. No forced selection or new acquisition.
4. Targeted regressions and repository-required guards; fresh whole-branch review;
   fix important findings, Draft PR and Main handoff with full SHA.

Shared interfaces: extractors produce evidence IDs used by judgments; producer
   emits schema/vectors consumed by Main. Unknowns never become false/zero.
Ruling: proceed with the owner's explicit detailed design and implementation
authorization; no redundant design approval. Publication remains separate.
Ruling: canonical's already successful unrelated checks are not repeated; run
changed-path tests and required guards, matching the owner's verification scope.

Review focus: imported snapshots forging selection/history, source/time metadata,
cross-company evidence, stale/revised core claims, HTML injection boundary,
automatic promotion and real data leaking into public output.

Ruling: RIG dependency guard prohibits consumers of its private model. The initial
reuse attempt failed test_no_other_package_depends_on_rig; use common
IssuerIdentity instead and retain RIG's isolation. No shared guard changed.

Completed: contract/6 synthetic states; offline producer/CLI; first held-company
execution (candidate, no forced selection); one independent review and six
RED→GREEN fixes. Targeted tests 22 + common/RIG 15 passed. No deferred findings.
The output-root declaration is an existing private authorization record, not a
substitute for Main authentication. Whole-market/PIT/awareness measurement absent.
