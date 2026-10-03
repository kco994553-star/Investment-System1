# Investment-System1 Claude Code Worker Contract

**Contract:** CLAUDE_CODE_WORKER_CONTRACT  
**Version:** v1.0  
**Status:** ACTIVE_WORKING_CONTRACT  
**Scope:** repository work coordination only  
**Policy authority:** none — scoped Decision Registers, approval evidence, Freeze evidence, and exact-SHA source remain authoritative.

## A. Repository truth hierarchy

Do not use prior chat summaries as repository SSoT. At the start of every task, fetch the latest remote state and read in this order:

1. GLOBAL_CURRENT_HANDOFF / GLOBAL_STATUS_INDEX — routing/index only, when present.
2. Capability-scoped CURRENT_HANDOFF / STATUS.
3. Decision Register / approval evidence.
4. Freeze / acceptance evidence.
5. Source and tests at the exact branch HEAD.
6. Latest relevant GitHub Actions.

Always distinguish:
- BRANCH_STATE
- INTEGRATION_STATE
- CANONICAL_STATE

Draft/unmerged branch results are not canonical completion. If global routing documents are absent or stale, use scoped evidence and report the gap.

## B. Worker ownership

A worker modifies only its assigned capability and owner branch. Other active worker branches are READ-ONLY upstream.

Do not force-push, rebase, reset, rewrite history, commit to, or merge another worker's active branch.

Shared integration metadata is single-writer:
- GLOBAL_CURRENT_HANDOFF
- GLOBAL_STATUS_INDEX
- HANDOFF_HISTORY
- shared integration evidence
- cross-capability dependency index
- common decision-routing metadata

## C. Autonomous Execution

Without additional user approval, continue within already approved scope for:
- implementation details and bug fixes
- adapters and wiring
- branch creation
- commits and feature-branch pushes
- Draft PR creation/update
- CI / GitHub Actions
- tests, fixtures, independent oracles
- regression and deterministic replay
- evidence and documentation
- compatibility repair and dependency audit
- repeated application of an already approved policy

Only perform actions the environment actually permits. Never bypass authorization or invent credentials.

## D. USER_DECISION_REQUIRED

Stop for user approval only when work requires:
1. a new investment formula;
2. ranking or eligibility rule changes;
3. a new threshold or default;
4. real calibration numeric configuration;
5. modification of a Frozen contract;
6. relaxation of PIT/no-lookahead;
7. first real CAL_VERIFY access/consumption;
8. real Holdout consumption;
9. Research/Frozen/Live publication grant;
10. Official promotion;
11. paid API/service/payment;
12. canonical merge;
13. production deployment;
14. an irreversible external change; or
15. choosing among reasonable alternatives that materially change investment or validation results.

Do not stop merely to provide a progress update.

## E. Blocker handling

Classify blockers as:
- LOCAL_FIXABLE
- DEPENDENCY_BLOCKED
- DATA_BLOCKED
- POLICY_BLOCKED
- USER_DECISION_REQUIRED
- REMOTE_WRITE_BLOCKED

Resolve LOCAL_FIXABLE autonomously. A blocked capability must not stop unrelated READY work. Reallocate effort to independent READY work when possible. Only USER_DECISION_REQUIRED is a policy reason to halt the relevant decision path.

## F. Dynamic parallelism

Do not fix the worker count. Choose parallelism from the dependency DAG, file ownership, and write-collision risk.

Independent implementation writers may run in parallel. Read-only audit/research/oracle workers may run alongside writers. Never assign concurrent writers to the same shared file.

Optimize capability maturity advancement, not worker count.

## G. Dynamic Workflow

Keep DYNAMIC_WORKFLOW_V1_SOFTWARE_FROZEN. Do not add orchestration features unless they are strictly required to implement an Investment-System capability.

Dynamic Workflow is an execution/validation mechanism, not a product capability to keep expanding.

## H. Capability maturity

Do not measure progress by test count or commit count.

Use:
DESIGN → IMPLEMENTED → SYNTHETIC_VERIFIED → REAL_DATA_VERIFIED → INTEGRATED → OPERATIONAL

SOFTWARE_FROZEN is a separate software/contract state. It does not imply REAL_DATA_VERIFIED, Official, Holdout-tested, or OPERATIONAL.

Only report progress when maturity actually changes.

## I. Validation semantics

Never broaden PASS semantics:
- producer PASS ≠ fully scored
- SOFTWARE_FROZEN ≠ real validation
- synthetic PASS ≠ real-data PASS
- Track C SOFTWARE_FROZEN ≠ Track C validation PASS
- research result ≠ Official
- FRESH ≠ Official
- persisted result ≠ investment-ready

Do not convert FAIL, NOT_RUN, BLOCKED, PARTIAL, or WITHHELD into PASS.

## J. PIT / Holdout / provenance

Maintain available_at <= decision_time. fetched_at is not available_at. Do not fill missing history with future, current, synthetic, or inferred values unless an approved contract explicitly permits it.

Do not read or consume real Holdout without explicit user approval.

Where the contract requires source, vintage, hash, lineage, identity, or availability evidence, missing evidence is fail-closed.

## K. Existing work preservation

Do not rewrite existing Frozen source, tests, evidence, proposals, approval records, Decision History, or historical handoffs.

Add new approvals/status history-preservingly. Never overwrite a historical evidence hash with a current run.

## L. Git/GitHub rules

At task start inspect current branch, HEAD, git status, remote refs, ahead/behind, worktrees, unpushed commits, and relevant Actions when the environment permits.

Preserve local-only or unreferenced commits. Different SHAs are different commits; do not claim otherwise.

No force-push or history rewrite.

Feature branch push and Draft PR creation are allowed within approved implementation scope. Canonical merge is USER_DECISION_REQUIRED.

CI not run = NOT_RUN. Stale Actions are not current-HEAD PASS.

## M. Integration rules

Preserve dependency chains. A stacked PR is not canonical-integration-ready before its base dependency.

Before actual merge, perform trial/read-only integration when possible and verify:
- merge conflicts
- source overlap
- contract compatibility
- regression
- numerical/semantic invariance where an existing approved fingerprint exists
- PIT/provenance
- cross-track preservation
- no publication/Official escalation

When integration debt is high, prefer reducing existing Draft-PR integration debt over adding unrelated features.

## N. Protected boundaries

Without explicit approval, do not change:
- QGV scoring semantics
- approved Technical methodology
- approved Macro methodology
- Leaderboard ranking semantics
- Portfolio investment policy
- Track C Frozen phases
- PIT/no-lookahead rules
- publication authority
- Holdout state
- Official state
- canonical baseline

Never weaken another capability's contract for convenience.

## O. Reporting

Checkpoint reports must distinguish what was actually executed from what was inferred. Include at minimum:
- exact branch / HEAD
- base / merge-base
- changed files
- maturity before → after
- tests actually executed
- Actions actually executed
- evidence/artifact hash when applicable
- dependencies and blockers
- USER_DECISION_REQUIRED status
- next autonomous action
- BRANCH_STATE
- INTEGRATION_STATE
- CANONICAL_STATE

Anything not executed is NOT_RUN.

## P. Worker routing order

For every new worker/task, read:
GLOBAL_CURRENT_HANDOFF
→ GLOBAL_STATUS_INDEX
→ capability scoped STATUS/HANDOFF
→ Decision Register / approval evidence
→ Freeze/acceptance evidence
→ exact-HEAD source/tests
→ latest Actions

If global documents are absent or stale, proceed from scoped evidence and report the routing gap.

## Q. End condition

Do not terminate merely because one blocker was found or a checkpoint can be written.

Continue READY work until at least one is true:
1. capability maturity actually advances;
2. a genuine USER_DECISION_REQUIRED boundary is reached;
3. all independent READY work in scope is exhausted; or
4. the execution environment makes further work impossible.

## Version history

- v1.0 — initial repository-wide Claude Code worker coordination contract.

Future changes must be history-preserving and record reason, approval basis, and effective version. Any change that alters investment results, validation outcomes, or authority boundaries requires user approval.
