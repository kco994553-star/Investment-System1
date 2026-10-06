# Free Cloud Bounded Executor v1

Status: CANARY / READ-ONLY E2E
Authority: CDR-024
Cost: no new paid resource

## Purpose

Prove a PC-free GitHub-native wake path:

GitHub event → free-cloud-controller → free-cloud-bounded-executor → deterministic bounded plan

without pretending that this is Main GPT reasoning.

## v1 write boundary

No repository write permission exists in this canary. The intended future mutation surface is exactly:

- branch: `automation/free-cloud-state-v1`
- path: `implementation/docs/coordination/automation_free/FREE_CLOUD_STATUS.json`

No canonical, Global, owner implementation branch, methodology, numeric policy, credential,
Holdout, Official/LIVE, trade/order/fund, or paid-resource mutation is admitted.

## Gate semantics

- READ_ONLY / PAUSE → deny
- RUN + Gate A CLOSED → deny
- active runtime state → deny
- only RUN + Gate A OPEN + IDLE may become eligible
- this canary still has read-only GitHub permissions even if eligible

## Promotion condition

Write permission must not be added until:
1. controller exact-head CI PASS
2. bounded executor exact-head CI PASS
3. event→controller→executor E2E is observed
4. path/branch scope is independently re-adjudicated as implementation-only / behavior-preserving
5. a negative test shows canonical/Global writes remain impossible
