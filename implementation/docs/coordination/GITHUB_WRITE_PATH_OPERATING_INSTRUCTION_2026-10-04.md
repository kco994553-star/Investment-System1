# GitHub Write Path — Common Operating Instruction

Instruction received: 2026-10-04 20:53:23 KST.
Authority: user's explicit common operating instruction in this Work conversation.
Scope: all Investment-System1 workers, including Claude Code, Codex and ChatGPT Work.
Effective: immediately, within each worker's existing approved branch and scope.

## Confirmed operating fact

The user reports a previously successful GitHub API publication of a local commit to a handoff branch with the exact local commit SHA preserved. A Git transport push failure therefore does not establish that GitHub repository write is unavailable. Historical push/credential/transport/403 reports must be interpreted separately from current API capability.

## Write policy

When Git transport is blocked, use the verified official alternative GitHub API publication path:
Git transport failure → inspect API write capability → publish the existing local commit objects → publish the approved handoff branch → verify remote SHA.

Prefer exact existing local commit identity over creating a replacement commit with equivalent changes. Preserve local SHA, tree, ordered parents, commit message, author and committer metadata, history and branch lineage. An API wrapper that cannot carry required metadata or signed commit headers is insufficient for exact identity publication; do not silently re-create an existing local commit through such a wrapper.

## Required publication verification

1. Confirm the remote branch was created or updated.
2. Explicitly verify local commit SHA == remote HEAD SHA.
3. Verify parents and ancestry.
4. Report ahead/behind against freshly read canonical.
5. Confirm no unexpected history rewrite.
6. Confirm working tree and publication target match; record any excluded uncommitted work.
7. Where PR/CI/Actions apply, verify they target the exact intended remote SHA.

Record actual remote evidence and distinguish PASS, NOT_RUN and unavailable checks. Do not treat an equivalent tree as exact commit identity.

## Worker behavior and authority

Before stopping work or requesting manual push because Git transport failed, inspect current API publication capability. Retain approved branch ownership, scope, protected boundaries and D3 approval requirements.

Transport capability ≠ Change authority.

This instruction grants no new feature implementation, canonical merge, Frozen-area change, production change, score change or publication grant.

## Handoff routing

This is an additive scoped operating record based on Global Handoff HEAD bb4cb174fd4a0af3b2281d4c37ae3abb4d540f88. Global coordination files declare the Primary Integration Writer as their single writer. That owner should append this instruction to GLOBAL_CURRENT_HANDOFF / GLOBAL_HANDOFF_HISTORY without rewriting existing history or evidence.

Other workers apply the instruction immediately when received and adopt it at their next fresh-read. Publication of this record does not prove that every independently running worker has read or acknowledged it.

## Evidence boundary for this record

The previously successful exact-local-SHA publication is user-attested here; this record does not independently re-run that historical operation. This new documentation record has no pre-existing local commit to republish and is created through the contents API. It must not be cited as proof that a metadata-limited create_commit wrapper preserves arbitrary existing local commit identity.
