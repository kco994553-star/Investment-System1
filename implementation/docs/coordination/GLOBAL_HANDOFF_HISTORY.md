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
