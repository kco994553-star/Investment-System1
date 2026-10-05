# Gate A verification receipt — PR #50 · 2026-10-05

Authority: CDR-024 / Autonomous Execution & Decision Authority SSoT v1.1
Subject branch: governance/autonomy-gate-a-v1
Exact head: 65a6c9d1bbe26b836e0aa25edd6687f1d8f2646f
PR: #50
Workflow: autonomy-gate-a
Run: 37300641046
Conclusion: SUCCESS

## Verified in this receipt

- Guard configuration pins CDR-024 operating values: cycle tasks 5, lease TTL 7200 seconds, repair cap 3.
- AUTONOMY_MODE is explicit and currently READ_ONLY.
- Unit/negative tests passed.
- Repository diff guard fails closed for modifications/deletes/renames of registered immutable Frozen paths.
- Existing append-only exact files and existing files under append-only evidence prefixes cannot be modified/deleted/renamed by the guard.
- GitHub Actions workflow executes the guard with contents:read permission only.

## Not yet verified

### HG-01
PARTIAL_VERIFIED only.
The repository-level path/history guard and negative tests are proven on this exact head, but GitHub-side enforcement that the check is required before protected integration/canonical changes is not yet verified.

### HG-02
NOT_VERIFIED.
Attempt to read canonical branch protection through the connected GitHub App returned HTTP 403 Resource not accessible by integration.
Repository ruleset read returned an empty list, which is not evidence that branch protection is absent because the branch-protection endpoint itself is permission-blocked.
Admin/user credential inspection is required. Do not infer PASS or FAIL.

### HG-03
PARTIAL_VERIFIED only.
AUTONOMY_MODE readback and adopted operating-value guard are proven. Actual executor behavior for RUN/PAUSE/READ_ONLY, per-cycle task cap, lease TTL use, repair cap enforcement, publish-time recheck, and watcher→executor E2E are not yet independently observed.

## Gate A

CLOSED.
Unattended AUTONOMY_MODE=RUN remains disabled.
Next critical dependency: GitHub-side protection inspection/configuration for HG-02, then executor integration/E2E for HG-03.
