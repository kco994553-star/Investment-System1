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
| HG-01 | Frozen/history/evidence destruction | A | VERIFIED | PR #50 exact head `c7738c0`; run `37300758757` SUCCESS. Canonical-target PR #51 exact head `de84abf`; run `37303986881` SUCCESS. Ruleset 24499602 now requires GitHub Actions `repository-guard`; missing/failed check blocks canonical merge | continue registry maintenance under §26A; protection removal/exclusion remains D3-R |
| HG-02 | canonical mutation | A | VERIFIED | Ruleset `24499602` ACTIVE on exact canonical ref; deletion blocked, non-fast-forward/force-push blocked, PR required with 0 approvals, bypass list empty, required check=`repository-guard` bound to GitHub Actions integration id 15368; canonical `protected=true` | preserve exact ruleset; changes/removal/bypass expansion require D3-R |
| HG-03 | runaway/cost control | A | PARTIAL_VERIFIED | PR #52 merged `f8c9802`; run `37305259790` SUCCESS. PR #53 canary runs `37305552562`/`37305552582` SUCCESS and merged `549f9a8`. Runtime guard behavior is verified. Current scheduled-task interface exposes no supported watcher→dedicated-Work executor invocation, so unattended wake/resume E2E is not yet proven | external product-runtime wake channel or supported Work invocation; production AUTONOMY_MODE remains READ_ONLY until then |
| HG-04 | real trade/order/fund movement | P | NOT_VERIFIED | no authorization inferred; credential/module isolation not verified | verify no order credential in agent environment and separate execution authority |
| HG-05 | financial credential/authority expansion | P | NOT_VERIFIED | no credential-access evidence admitted | verify secret isolation and .env read/write protection |
| HG-06 | Holdout consumption | P | NOT_VERIFIED | Holdout remains unconsumed by current project records; hard access separation not verified | verify storage/permissions/access logging |
| HG-07 | Official/LIVE promotion/deploy | P | NOT_VERIFIED | current policy reserves promotion/deploy; environment protection not verified | verify deployment environment approval gate |
| HG-08 | PIT/no-lookahead relaxation | P | NOT_VERIFIED | semantic policy remains fail-closed; required CI guard not yet verified | verify mandatory CI checks protecting PIT/no-lookahead |
| HG-09 | security/Tenant isolation | P | NOT_VERIFIED | Platform security work is partial; mandatory fail-closed gate not yet verified | verify negative cross-user/tenant checks as required CI |
| HG-10 | new numeric criteria/methodology | P | NOT_VERIFIED | §§26A/26B procedural guard active; static semantic numeric registry not yet verified | implement/verify protected semantic registry and diff detector |
| HG-11 | paid payment/paid API | P | NOT_VERIFIED | no paid-resource approval inferred; environment isolation not verified | verify absence of billing credentials/paid keys in agent runtime |

## Gate A status

- HG-01: VERIFIED
- HG-02: VERIFIED
- HG-03: PARTIAL_VERIFIED

Gate A: **CLOSED / UNATTENDED AUTONOMY DISABLED**

HG-01 and HG-02 are VERIFIED. HG-03 repository/runtime guard behavior is verified by CI canary, but actual Watcher → Work executor wake/resume has not been observed. Gate A remains CLOSED until that product-runtime E2E is proven.

Latest bounded evidence: `governance/evidence/GATE_A_PR50_VERIFICATION_2026-10-05.md` and `governance/evidence/HG03_RUNTIME_WAKE_E2E_2026-10-05.md`. HG-02 is VERIFIED by active ruleset `24499602`; do not regress or bypass it. HG-03 remains PARTIAL_VERIFIED because the supported product-runtime Watcher → dedicated Work executor invocation path has not been demonstrated.

User-observed/session execution remains allowed under v1.1. Read-only watcher behavior remains separate from unattended executor activation.

## G2 immediate-blocker baseline

No G2 condition is asserted present from this registration alone. A G2 blocker is created only from concrete evidence.
