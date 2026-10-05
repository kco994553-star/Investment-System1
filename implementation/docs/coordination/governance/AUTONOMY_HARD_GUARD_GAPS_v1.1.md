# AUTONOMY HARD-GUARD GAP REGISTER · v1.1

Status: ACTIVE / INITIAL BASELINE
Authority: CDR-024
Recorded: 2026-10-05
Global baseline at registration start: 9680c455c10eba9d3b4bd3f3283aaea5274ddafc
Canonical: b8e39a2196a6d7794a04a0cd5393c68329e126ca

This register implements PART G of Autonomous Execution & Decision Authority SSoT v1.1.

Rules:
- NOT_VERIFIED / NOT_IMPLEMENTED are Hard-Guard Gaps, not automatic global blockers.
- Gate A gaps block unattended AUTONOMY_MODE=RUN.
- Gate P gaps block only the relevant protection area at production-candidate entry.
- Any confirmed G2 condition is an immediate Security/Integrity blocker.
- Status may advance only with repository path + behavior-test evidence + exact HEAD.

| ID | Protection area | Gate | Initial status | Current evidence | Next verification |
|---|---|---|---|---|---|
| HG-01 | Frozen/history/evidence destruction | A | NOT_VERIFIED | v1.1 policy only; implementation evidence not yet admitted | inspect freeze/path guard, branch protection, no-force enforcement and tests |
| HG-02 | canonical mutation | A | NOT_VERIFIED | canonical unchanged at b8e39a2; hard guard itself not yet verified | inspect PR/check/CODEOWNERS/branch-rules enforcement |
| HG-03 | runaway/cost control | A | NOT_VERIFIED | v1.1 Kill Switch/hard-stop policy adopted; implementation evidence not yet verified | locate AUTONOMY_MODE control and executable enforcement/readback |
| HG-04 | real trade/order/fund movement | P | NOT_VERIFIED | no authorization inferred; credential/module isolation not verified | verify no order credential in agent environment and separate execution authority |
| HG-05 | financial credential/authority expansion | P | NOT_VERIFIED | no credential-access evidence admitted | verify secret isolation and .env read/write protection |
| HG-06 | Holdout consumption | P | NOT_VERIFIED | Holdout remains unconsumed by current project records; hard access separation not verified | verify storage/permissions/access logging |
| HG-07 | Official/LIVE promotion/deploy | P | NOT_VERIFIED | current policy reserves promotion/deploy; environment protection not verified | verify deployment environment approval gate |
| HG-08 | PIT/no-lookahead relaxation | P | NOT_VERIFIED | semantic policy remains fail-closed; required CI guard not yet verified | verify mandatory CI checks protecting PIT/no-lookahead |
| HG-09 | security/Tenant isolation | P | NOT_VERIFIED | Platform security work is partial; mandatory fail-closed gate not yet verified | verify negative cross-user/tenant checks as required CI |
| HG-10 | new numeric criteria/methodology | P | NOT_VERIFIED | §§26A/26B procedural guard active; static semantic numeric registry not yet verified | implement/verify protected semantic registry and diff detector |
| HG-11 | paid payment/paid API | P | NOT_VERIFIED | no paid-resource approval inferred; environment isolation not verified | verify absence of billing credentials/paid keys in agent runtime |

## Gate A status

- HG-01: NOT_VERIFIED
- HG-02: NOT_VERIFIED
- HG-03: NOT_VERIFIED

Gate A: **CLOSED / UNATTENDED AUTONOMY DISABLED**

User-observed/session execution remains allowed under v1.1. Read-only watcher behavior remains separate from unattended executor activation.

## G2 immediate-blocker baseline

No G2 condition is asserted present from this registration alone. A G2 blocker is created only from concrete evidence.
