# Investment-System1 · GLOBAL_HANDOFF_HISTORY

This file is append-only. Add new entries at the end. Never edit or delete an earlier entry. A correction is a new entry that names the entry it corrects.

Single writer: the Primary Integration Writer.

This file is separate from root `Investment-System1 · HANDOFF_HISTORY.md`. That file is preserved unchanged and is still appended by scoped workers (for example Track C on its own branches). A separate file keeps the two histories from colliding at merge time.

---

## GCH-001 · 2026-10-03T01:20Z · Primary Integration Writer takeover

- Writer: Claude Code session `session_019znshzTYgyBnuuBmSxdPFN`, designated Primary Integration Writer and Integration Coordinator by the user on 2026-10-03.
- Started from:
  - a fresh fetch of 28 remote refs and 17 open PRs;
  - canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`, which equals the last independent audit checkpoint.
  - Prior chat summaries were not used as SSoT.
- Created this branch, `integration/global-handoff-v1`, from canonical. Added `GLOBAL_CURRENT_HANDOFF.md` (GCH-001), `GLOBAL_STATUS_INDEX.md` (GSI-001), this history file, and trial-integration evidence GIE-001.
- Worker Contract v1.0 was added on `ccr-2e16018a-qukwmg` @ `f1b5afb` (Draft PR #21). A parallel duplicate, Draft PR #20 @ `d87d4cd`, was created 90 seconds earlier by another writer and was not visible at audit time. It is recorded as IF-3 and USER_DECISION_REQUIRED. Neither PR was modified by the other side.
- Integration findings: IF-1 (Track C cross-track source overlap), IF-2 (branch-isolation sentinels), IF-3 (contract duplicate), IF-4 (CI gaps on #12, #13 and `ccr-22e3ff16`).
- Maturity transitions in this checkpoint: **none**. No capability moved stage, and coordination documents are not capability maturity.
- Not done:
  - No canonical merge.
  - No capability-branch edit.
  - No force-push or rebase.
  - No Holdout or CAL_VERIFY access.
  - No grant.
  - No Dynamic Workflow change.

## GCH-001a · addendum · Track C tip local regression

- `ccr-22e3ff16-p7n5k5` @ `97d1b94`, local full pytest: 910 passed, 0 failed. Recorded in GIE-001 §6 and in GSI-001 row 3.
- Not CI_VERIFIED. No maturity change.
- Correction to GCH-001: its heading time `01:20Z` was written before the commit. The actual commit time of `b118b68` is 2026-10-03T01:18:13Z. The GCH-001 heading is left unchanged (append-only). GSI and GCH now show 01:18:13Z.

## GCH-002 · 2026-10-03 · user decisions CDR-001..003 recorded

- Added `COORDINATION_DECISION_REGISTER.md`, append-only, with the user's wording quoted verbatim.
  - CDR-001: PR #21 exact HEAD `f1b5afb` is the operational routing SSoT for the Worker Contract. PR #20 is SUPERSEDED_DUPLICATE (not merged, retained, §J exception not adopted). Not canonical-merge approval.
  - CDR-002: the Track C ↔ producer merge order is deferred. A result-invariant compatibility audit (GIE-002) comes first.
  - CDR-003: Track C C8 method policy is separated from numeric configuration. Approved scope continues autonomously on the owner branch, and the numeric gate stays separate before CAL_VERIFY.
- GCH-002 replaces GCH-001 as the current handoff. GSI-002 updates the contract rows and IF-3.
- No canonical merge, grant, or capability-branch edit.

## GCH-002a · 2026-10-03 · IF-1 compatibility audit and C8 method analysis

- GIE-002 (workflow `wf_56296124-2cc`, 7 agents, local trials only): IMPOSSIBLE_WITHOUT_ONE_SIDE_CHANGE. Options A (producer re-pin, lineage in core) and B (Track C sidecar, C4-frozen change) were both measured result-invariant. A/B is escalated to the user per CDR-002.
- GIE-004: C8 method-choice impact analysis, with 2 LOCAL_FIXABLE fail-opens for the Track C owner. Not authoritative.
- GIE-003 (earlier this round): source overlap and escalation sweep.
- No capability-branch edit, canonical merge, grant, CAL_VERIFY or Holdout access. No maturity change.

## GCH-003 · 2026-10-03 · CDR-004 (IF-1 = A1 + owner adoption) and CDR-005 (C8 repair) recorded

- User wording recorded verbatim in `COORDINATION_DECISION_REGISTER.md`. GCH §4 updated. Execution starts as stacked proposal branches; no owner branch is committed to.

## GCH-003a · 2026-10-03 · Track C owner executed CDR-005; integration writer stood down from the Track C proposal

- Owner commits 9a9364c, 972a23f, b9e01a97 on `ccr-22e3ff16-p7n5k5`. The integration writer did not create `track-c/c8-fail-closed-repair-v1`; its first workflow run was stopped before that writer started and relaunched with the four producer writers plus a read-only Track C auditor.
- Actions run 37097149378 (`track-c-evl-validation.yml`, workflow_dispatch, `contents: read`) dispatched on the owner tip by the integration writer.
- New USER_DECISION_REQUIRED routed to the user: authoritative G-SUP method (K / M / C), from the owner's register entry. Not decided here.

## GCH-004 · 2026-10-03T06:58Z · fresh reconciliation; CDR-006/007/008 recorded

- Fresh fetch: canonical `b8e39a2` unchanged; Track C owner tip `b9e01a9` (Actions 37097149378 SUCCESS); A1 proposals #22–#27 pushed by the integration writer's workflow (adversarial review agents failed on a session rate limit, so integration-owner verification is pending); Codex PRs #28 (takeover audit), #29 (Web fixture/E2E), #30 (combined trial, FRESH, 9/9 green).
- No Codex Track C branch, PR or commit found.
- CDR-006 (G-SUP = M, additive v2), CDR-007 (source descriptor), CDR-008 (Codex implements; integration writer verifies) recorded verbatim.

## GCH-004a · 2026-10-03T07:03Z · CDR-009 Codex active-write exclusion recorded

- Track C C8 G-SUP v2 / source-descriptor / related C8 oracle/test/acceptance/evidence paths are out of the Primary Integration Writer's write set until Codex is DONE or HANDOFF_READY. Read and temporary trial merges allowed; conflicts are recorded, never resolved by commit.

## GCH-005 · 2026-10-03T07:55Z · GIE-006 recorded

- #30 FRESH_WITH_FINDINGS (no blocking; local 1165/1165). #22–#27 integration-owner verification PASS (66/66). New proposals #32 (#9) and #33 (#7) pushed and verified. Web G3 defect found (Web validator lacks the research guard). Codex `codex/track-c-gsup-v2-2026-10-03` @ `675d0d2` IN_PROGRESS (CDR-009 exclusion active).

## GCH-005a · 2026-10-03T08:05Z · PR #31 tracked; Codex-raised arithmetic-reduction decision recorded

- PR #31 (`codex/track-c-gsup-v2-2026-10-03` @ `675d0d2`, base #30) recorded read-only. Not DONE/HANDOFF_READY; CDR-009 exclusion active.
- Codex raises USER_DECISION_REQUIRED_ARITHMETIC_REDUCTION for M-B v2. Recorded as pending and as not yet independently verified by the integration owner.

## GCH-006 · 2026-10-03 · GIE-007 recorded (Web guard / UI / next local trial)

- #34 G3 render guard: review PASS. #36 production-state presentation: review BLOCKING (fail-open freshness label), in repair. Next local trial (1175/1175) superseded pending the repaired heads. Validator hardening stays a separate follow-up requiring a user decision if pursued (#17 protected digest).

## GCH-006a · 2026-10-03 · repair round 1 recorded

- #34 `a3cbf13` re-review PASS (contract validation-PASS parity added). #36 `8b6756b`: original exploit fixed; new bounded bypass B1 found; repair round 2 running. trial2 1189/1189, superseded pending round 2. Codex `codex/integration-hardening-2026-10-03` @ `fc6720b` (F1 fix) tracked read-only.
