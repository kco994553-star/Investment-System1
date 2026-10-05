# Product Platform SSoT Autonomous Execution Loop v1.0

Authority: explicit user directive received2026-10-05 16:15:41 Asia/Seoul. This supplements the existing independent audit role and Risk-Proportional Verification; it does not grant another owner's source/write set. Current queue, receipts and dependencies are in [STATE.json](STATE.json). The audit branch is codex/product-platform-storage-auth-review-2026-10-05; PR45 retains its historical fixture-harness head17244b4. Product source owner remains codex/product-platform-audit-v1.

## Execute until the actual checkpoint

1. Fresh-read relevant GitHub repository/ref, scoped handoff/state, Global, decisions/approvals, immutable evidence/CI and owner contracts; conversation comes last.
2. Reconcile CURRENT / STALE / SUPERSEDED / HISTORICAL / UNVERIFIED / CONFLICTING. Actual immutable input and authoritative current state win. Match source/test/dependency/workflow hashes and scope before receipt reuse; do not relabel old PASS for changed code.
3. Discover tasks across every approved lane. Classify READY / WAIT_DEPENDENCY / D3_REQUIRED / DONE / SUPERSEDED / INVALID with exact acceptance and dependency references. One blocked lane never blocks an unrelated READY lane.
4. Choose shared blocker, critical path, security/integrity, owner return, integration, acceptance, bounded implementation, then documentation. Execute the selected READY task now, not as a future suggestion.
5. Implement/test/repair/retest/verify/publish within the accepted write set. Failure is RETRY / REPAIR / REPLAN / WAIT_DEPENDENCY / D3; retain the original failure and correction history.
6. Publish through the verified GitHub API path when needed, preserve exact identity and fresh parent, no force/history rewrite. Update scoped state/handoff only for real change and route integration-relevant returns via registered PR45. Global and other owner branches remain read-only.
7. Re-evaluate immediately: did this result make new work READY? Execute it. Otherwise inspect other lanes. A report is not a stop condition while READY remains.

## Risk, roles and boundaries

One auditor; add at most one independent security verifier only for actual unresolved security/cross-user ambiguity. CRITICAL Auth/session/revocation/authorization/tenant/cross-user/read-only/secrets/financial provenance/integrity/reconciliation/production connection retain relevant adversarial/negative security checks. STANDARD uses targeted→negative→affected regression; FAST uses deterministic targeted→close. Full repository regression only when justified by actual impact. Completed mock/fixture/CI evidence is reused, not repeated to create activity.

This Work owns independent specialist audit and bounded fixture/test/evidence candidates, not large Platform implementation or whole integration. Exact implementation-owner acceptance is required before consuming its source changes. Caller identity and mock PASS cannot certify trusted runtime ownership. Actual credentials/accounts, production auth, tenant policy, paid resources, trade execution, protected semantics, Frozen/PIT/Official/LIVE/canonical/deploy remain D3; a pending D3 blocks only its dependent action.

Supabase without confirmed adoption and an approved DEV locator/environment mapping stays NOT_CONFIRMED / NOT_RUN. No repeated search, guessed project or backend replacement. Existing first-tool-use/version-matched docs/current-stage skill rules remain. Provider-neutral ready work continues. No new competing contract or owner implementation solely to avoid a wait.

## One executor, two wake-up paths

PR45 conversation/inline comments, reviews and HEAD changes have one narrowly scoped GitHub event trigger. The existing follow-up task covers material owner-branch/Global/canonical/CI changes that this connector cannot directly trigger. These paths share this queue and audit branch; they are not separate implementation owners. Event support is PR-scoped, not a branch-push or CI-terminal webhook. Registered triggers are not proof of unattended execution; scheduler-hop verification is separate.

Before a write-producing READY action, fresh-read remote ref/state. Claim an explicit run_id/writer/scope/input-fingerprint/UTC lease through a commit whose parent is that exact ref, update with force=false and read back. Two competing children of one parent cannot both fast-forward the branch: the losing claimant re-reads and does not duplicate the winning scope. Never steal another owner's lease or infer permission from a null lease. Lease duration/renewal is operational metadata (default30 minutes), not Auth/financial policy. Renew only the owned scope for long actions; release at checkpoint/WAIT. No READY means no lease-only commit.

Deduplicate by task+input+decision fingerprint, not by account name. Main and this Work share a GitHub account; Main returns must still be consumed. Ignore this Work's exact self-publication markers platform-ssot-loop / platform-audit-return when they convey no new owner/CI/input evidence. Events are wake-ups: fetch current SSoT and handle semantic relevance, not just the event payload. Bootstrap without STATE cannot authorize source takeover.

## Consume returned work, then continue

Track the observed owner-return progression SENT→ACKNOWLEDGED→IN_PROGRESS→RETURNED→INDEPENDENTLY_VERIFIED→CONSUMED→CLOSED. Do not invent intermediate observations. Main's consumption of audit evidence is separate from the implementation owner's ACK/adoption. Verify exact returned HEAD, scope, source/test/evidence; use the cheapest reliable affected verifier; consume the result, rejudge blockers and immediately discover newly READY work.

CI RUNNING permits another lane. Terminal SUCCESS requires relevant artifact consumption and next action. FAILURE is bounded self/owner repair or dependency routing; cancelled/infra failures get an appropriate retry assessment. Exact previously consumed successful runs do not need another dispatch. This Work has no pending scoped CI at this checkpoint; unrelated Main FPIA CI is not adopted as Platform acceptance.

## WAIT and resume

Global WAIT requires all six counts zero: READY D1/D2; other-lane READY; bounded repair READY; returned-owner results consumable now; terminal CI results consumable now; SSoT update/closure READY. Remaining approved tasks must be DONE, WAIT_DEPENDENCY or D3_REQUIRED. Record exact owner/ref/run/decision, required return, material trigger and next automatic action. Do not busy-poll unchanged dependencies.

Material triggers: accepted writer/write set, source/contract/dependency delta, owner return, CI terminal/artifact, approved decision, integration/canonical change or actual tool-target availability. Timestamp-only or already consumed self/control delta does not reopen completed work. A queued READY task can execute without a new external event. Whole Work stops only at acceptance DONE, actual D3, exhausted D1/D2 dependency wait, or an actual unrecoverable tool/system blocker.

At actual WAIT/D3/DONE report exact SSoT, Product blockers closed separately from coordination/acceptance closures, real verification, consumed returns, remaining READY, WAIT references/triggers, D3 and next automatic action. Maintain each named capability's maturity and start/closed/new/end/net, verified capabilities, owner actions, tool-blocked items, gates/dependencies/acceptance criteria and candidate readiness. Test/commit/agent counts are evidence, not progress. No need to ask the user to type “continue” for a permitted next action.
