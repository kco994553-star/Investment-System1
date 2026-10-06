# Decision Package — Free Cloud Bounded Write Grant v1

Status: D3-R USER DECISION REQUIRED
Authority: CDR-024 / Autonomous Execution & Decision Authority SSoT v1.1
Context: PR #55, #56, #57 are merged; controller, bounded executor canary and write-scope contract all passed exact-head CI.

## Decision

Whether to grant GitHub Actions `contents: write` for one dedicated automation workflow, constrained to a single automation branch/path.

### Proposed grant

- Workflow: future `free-cloud-bounded-writer.yml`
- GitHub permission: `contents: write`
- Allowed branch: `automation/free-cloud-state-v1`
- Allowed path: `implementation/docs/coordination/automation_free/FREE_CLOUD_STATUS.json`
- All other branches/paths denied by `free_cloud_write_contract.py`
- No canonical, Global, governance control, owner implementation, methodology, numeric policy, Holdout, Official/LIVE, financial credential, paid resource, trade/order/fund movement.

## Why D3-R

This is a real repository write-authority expansion for unattended cloud automation. CDR-024 reserves authority expansion and security-boundary changes for user approval even when implementation-only and narrow.

## Recommendation

APPROVE NARROW CANARY ONLY.

Reason:
1. Scope is isolated from canonical/Global and all product code.
2. Existing exact-head CI already proves controller, executor canary and negative write contract.
3. The first write canary can be a harmless machine-generated status file on the dedicated automation branch.
4. Rollback is immediate: disable workflow or remove `contents: write`; delete only the dedicated automation branch if desired.
5. No paid API or external AI is involved.

## Canary acceptance

After approval:
1. create/update only `automation/free-cloud-state-v1`
2. write exactly one status JSON file
3. read back remote branch/path/SHA
4. prove attempted Global/canonical/governance writes are rejected before any API mutation
5. keep production `AUTONOMY_MODE=READ_ONLY`
6. do not treat the canary as Gate A OPEN or Main-GPT replacement
7. record exact run/job/head/output hashes
8. remove or disable the writer immediately if any scope escape is observed

## User decision surface

- APPROVE: allow the narrow write canary above.
- REJECT: remain read-only; free cloud automation stops at deterministic control-plane.
- MODIFY: specify a narrower branch/path or additional guard.
