# Event + state continuation protocol · proposed control v2

**Score-neutral owner infrastructure. D3 boundaries unchanged.**
This protocol does not dispatch production calculations, edit scores, select
factor roles, approve B decisions, or consume Holdout. The read-only
`continuation_probe.py` evaluates eligibility; the lease-holding executor alone
may carry out an eligible authorized task and publish accepted output.

## Fresh-read and two independent inputs

On every invocation read actual owner/canonical/#44/#42 refs, relevant approval
evidence, scoped Handoff, STATE, immutable source pins, receipts and relevant
Actions. Actual repository and authenticated approval evidence take precedence
over stale control prose. Parse two independent queues:

1. EVENT: material source/dependency/PR/review/comment/CI change, keyed by actual
   delivery/event or run ID and attempt. Disposition each event independently.
2. STATE: an unfinished explicitly authorized D1/D2 task in the current finite
   plan, with available exact inputs, satisfied dependencies, no active other
   owner lease, and no accepted completed receipt for its exact task fingerprint.

No fresh event, self-only event, or empty pending CI does not suppress STATE.
Conversely a new control receipt alone does not manufacture semantic work or
an approval. Each watch applies the selector. Hourly CI watch first examines
pending CI; it may then execute one finite eligible state task. Process genuine
completed CI only for its original head/attempt, never relabel ancestor success
as exact-current-HEAD Actions PASS. Report meaningful output or blocker only.

## Task fingerprint and receipt

Task fingerprint is SHA-256 of canonical JSON (sorted object keys, deterministic
UTF-8, no NaN) containing repository, task ID/version, explicit work spec,
classification, exact semantic source **path+content hash** pins, method-policy
refs, approval dependency IDs/scopes+content hashes, prerequisite task/output
bindings, output contract, acceptance validator identity, and any explicit replan.
Do not key work by arbitrary owner HEAD, timestamps, lease/control/receipt noise,
or actor identity. Source hashes must match actual files before selection. A
missing/changed input remains a wait/replan; never silently hash the latest file
into a historical task. Approval digest pins scope, not just APPROVED text.

`COMPLETED` requires current authorized D1/D2 scope, all pinned source/policy/
approval bytes still matching, an ACCEPTED output receipt for that fingerprint,
the exact acceptance validator **path+content hash** (not just its name/version),
every contracted output path, and actual output hashes matching the receipt.
Current source/validator drift or revoked authority is a validation/replan hold,
not accepted completion and not an implicit command to rerun old work.
An acceptance reference may pin a reviewed owner acceptance specification,
such as CANARY_ACCEPTANCE.md, rather than an executable validator. In that case
ACCEPTED records the owner's evidenced assessment against those exact bytes;
it does not authenticate a platform execution or convert a recommendation into
domain approval. A callable validator must additionally pin its exact source.
Intake, NO_ACTION, PENDING_D3, WAITING_FOR_APPROVAL,
WAITING_EXTERNAL, FAILED, local-test or documentation receipts are not task
completion. Completed input-watermark disposition is independent of task
completion: a D3 event may be acknowledged without finishing its dependent task.

If a prerequisite completes, its accepted output digest becomes an exact HOP2
input. An unfinished dependent template is not executable until its manifest is
finalized and hash-pinned under the same owner protocol. Completion does not
invent further tasks or extend authority.
The finite task IDs include both HOP1 and HOP2 from the outset. When HOP2 is
still a template, accepted HOP1 yields WAITING_NEXT_TASK_BINDING, not terminal
completion. The same authorized HOP1 checkpoint binds the exact output hash
into HOP2; it does not execute HOP2 in that same scheduler hop.

## Lease and failure

Keep optimistic force:false git-ref CAS. Root/manual work owns the current lease;
workers must not edit STATE/receipts concurrently. Same-parent competing claim
loser stops. Re-read token after acquisition and before each mutation; losing
lease means discard cached writes, not rebase them over another token.

No stale lease is stolen based on age/expiry. A stale-looking RUNNING lease still
blocks writes until independent execution evidence proves termination and the
owner performs an explicit recovery checkpoint. Long CI/approval/input waits
release a properly held lease; write pending state only when materially changed.
Read-only selector output does not itself claim or release a lease.

A FAILED receipt for an unchanged fingerprint yields REPLAN_REQUIRED. Do not
retry on every hourly tick. An explicit finite replan names the exact failed
fingerprint, a concrete corrective action, changed evidence/source pins and a
new task version; it must remain within D1/D2. Record another failure as terminal
for that new fingerprint. Unresolved D3 or external dependencies block only their
own path, not independent tasks. No policy numeric default is introduced.

## Minimal existing-watch patch

Apply this block to **both existing prompts**, preserving their existing IDs,
schedule/trigger set, owner scope, CAS, no-force/history/PIT/Holdout/Frozen and D3
rules. Resolve same-chat target by actual settings readback. Exact patch block:

```text
CONTINUATION PROTOCOL v2 (supersedes conflicting no-event/no-pending-CI stop
clauses only for authorized unfinished D1/D2 work): Fresh-read Actual GitHub,
approval evidence, scoped Handoff, STATE, task plan and receipts. Evaluate
EVENT-DRIVEN inputs and STATE-DRIVEN tasks independently. No new event, own
control-only event, empty pending CI, or no owner PR is not task completion.
If an explicit unfinished D1/D2 task has matching exact inputs, satisfied
dependencies, no conflicting active lease, and no accepted-output completion
receipt for its canonical task fingerprint, execute that bounded task using the
existing owner lease/CAS protocol. Never choose/adopt D3 policies. A D3-blocked
dependent path stays pending; independent D1/D2 work continues.
Fingerprint source content/method-policy/approval dependency refs and exact
prerequisite outputs, not arbitrary owner HEAD/control noise. Completion requires
accepted actual output hashes and its exact validator; intake/wait/failure is
not completion. Same failed fingerprint requires an explicit actionable replan;
no hourly blind retry. Never steal a stale-looking lease.
CI watch retains its existing schedule and pending-CI readback first, then the
same finite state selector. Event watch retains exact #44/#42 full trigger set.
Use current owner finite plan: HOP1 legacy source-pinned method replay manifest;
HOP2 independent exact-HOP1-output dependency/test closure. No production,
legacy score, policy adoption, merge, Holdout or paid use. After HOP2 terminal
D3 wait unless explicitly authorized fresh work opens.
verify_on_next_execution: Read prior receipts and outputs before executing.
Only two distinct actual scheduler executions with validated HOP1 and HOP2,
fresh-read/input pins/lease/disposition evidence and HOP2 consuming exact HOP1
output may produce AUTONOMOUS_CONTINUATION_VERIFIED. Manual execution or local
simulation is not a scheduler hop. If scheduler execution identity/evidence is
unavailable, retain REAL_EXECUTION_EVIDENCE_REQUIRED; never fabricate it.
```

## Finite natural two-hop canary

| Hop | D1/D2 work | Acceptance | Next |
|---|---|---|---|
| HOP1 | Generate source-pinned replay manifest for the already-audited legacy20 factors: existing factor ID, current method/input horizon, fallback, normalization, source hashes and history anchors. Reuse factor audit, do not restart it. | Read-only validators match actual legacy code/history, no score/production change; accepted manifest output hash and actual scheduler run receipt. | Publish exact-hash-bound HOP2 template; do not adopt policy. |
| HOP2 | Independently close method/input/admission dependencies and adversarial test matrix against exact HOP1 manifest hash and existing binding package. | No missing/ambiguous lineage hidden as PASS; tests and comparison evidence accepted; actual distinct scheduler run receipt. | TERMINAL_D1_D2_COMPLETE_AWAITING_D3; no invented third task. |

Required real-run receipt fields: automation ID, platform execution ID, execution
start/end/readback evidence, fresh remote inputs, run/lease token, task fingerprint,
input source/approval digests, accepted output path/hash+validator, disposition,
HOP1 output consumed by HOP2, exact owner before/after refs. Actual run IDs must
come from exposed platform evidence; a locally generated run token is not one.
Execution evidence locators/hash refs must themselves be retained.

Pass criteria: two real distinct scheduler executions (not two writes in one
manual run), exactly bound accepted outputs, both fresh-read and owner lease
evidence, unchanged protected production/golden, no D3 adoption. Until then:
**TWO_HOP_PLAN_READY / REAL_EXECUTION_NOT_VERIFIED**. Pure selector unit tests,
including local simulated two-step dependency progression, prove only local
protocol behavior. No artificial human comment or production canary is required.
