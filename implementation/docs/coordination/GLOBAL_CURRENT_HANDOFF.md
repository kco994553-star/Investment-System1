# Investment-System1 · GLOBAL_CURRENT_HANDOFF

Routing/index SSoT only. This file is not a calculation, policy, approval or publication authority. Scoped Decision Registers, approval evidence and the exact SHA win on any conflict. Draft-branch results recorded here are not canonical completion.

| Field | Value |
|---|---|
| Handoff ID | GCH-001 (first global handoff) |
| Recorded | 2026-10-03T01:20Z |
| Primary Integration Writer | Claude Code session `session_019znshzTYgyBnuuBmSxdPFN`, designated by the user on 2026-10-03 |
| Live location | `origin/integration/global-handoff-v1` : `implementation/docs/coordination/GLOBAL_CURRENT_HANDOFF.md` |
| Canonical branch / HEAD | `claude/investment-system-top500-validation-alrugm` @ `b8e39a2196a6d7794a04a0cd5393c68329e126ca`. This matches the last independent audit checkpoint, and canonical has not moved since 2026-09-28 |
| Remote refs audited | 28 branches, 17 open PRs (#4, #5, #6, #7, #9–#21; #8 closed, #1–#3 merged) |
| Operating contract | `CLAUDE_CODE_WORKER_CONTRACT_v1.0`. Two candidates exist (IF-3). Selecting one is USER_DECISION_REQUIRED |
| Supersedes | nothing. The root `Investment-System1 · CURRENT_HANDOFF.md` remains the canonical Track A/historical handoff, and Track C appends to it on its own branches. It is older than the current parallel state and is not edited here |

## 1. Read next

1. `GLOBAL_STATUS_INDEX.md` (same directory): per-capability `BRANCH_STATE`, `INTEGRATION_STATE`, `CANONICAL_STATE`, maturity, PR classification, dependency DAG.
2. `evidence/GIE-001_trial_integration_2026-10-03.md`: trial integration of every open PR tip.
3. The scoped STATUS/HANDOFF of your capability (paths in the index), then its Decision Register and approval evidence.

## 2. Canonical state

The following are on canonical, from merged PRs #1, #2 and #3:

- Track A REAL-DATA baseline FROZEN_VERIFIED (#3 as `bd6bf42`).
- Track B P0 contracts FROZEN.
- Track D RIG P0–P4 (#1).
- Track E Prompt Library v1 (#2).

Nothing else is on canonical, and no capability other than Track A is `INTEGRATED`. The canonical baseline regression was reproduced in this checkpoint: 396 passed, 0 failed (mini_pytest shim) at `b8e39a2`.

## 3. Critical path (re-judged after the fresh audit)

| Order | Path | Current gate | Type |
|---|---|---|---|
| 1 | Track C C8 → C9 → C10 | A6 numeric configuration (tolerance, envelope/margin, α, B, L, seed, effect floor, minimum support) and 5 implementation-defined method details (AR1_LAG1, Gaussian envelope, exceedance counting, variance computation, feasibility seed) on `ccr-22e3ff16` @ `97d1b94`. A8/A10 not approved. The Track C session is idle in `need_input` | USER_DECISION_REQUIRED |
| 2 | Technical REAL + US Equity Session real validation | #11 → #15 → #18 green on HEAD. Real validation needs an exchange-issued calendar vintage replayed end to end | DATA_BLOCKED |
| 3 | QGV persisted export → Leaderboard | #10 and #14 are REAL_DATA_VERIFIED (research). Publication requires a P01 research-display grant. Within-tie order is POLICY_BLOCKED | USER_DECISION_REQUIRED (grant, tie policy) |
| 4 | Macro REAL/PIT | #12 has no Actions run. A live ALFRED fetch needs an API key secret. Exposure has no approved coefficient | STALE_CI + DATA_BLOCKED + POLICY_BLOCKED |
| 5 | RIG real-source boundary | #13 has no Actions run. No news provider is selected (possibly paid). The SEC 8-K path (#16) works on supplied bytes | STALE_CI + USER_DECISION_REQUIRED (provider) |
| 6 | P01 + Invalidation integration | #9 → #17 → #19 green on HEAD. All grants NONE | READY_FOR_INTEGRATION_AUDIT; grants are user decisions |
| 7 | Producer → Web integration | #5 → #6 sequential trial PASS on Actions. #7 and #9 stack on #6 | Canonical merge = USER_DECISION_REQUIRED |
| 8 | Track B / Portfolio actual operation | P1+ not started | DESIGN |
| 9 | Daily operation pipeline | not started | DESIGN |

## 4. USER_DECISION_REQUIRED queue

1. **Worker Contract SSoT (IF-3).** Choose #21 (`ccr-2e16018a-qukwmg`) or #20 (`integration/claude-worker-contract-v1`).
   - #20 adds a §J exception ("unless an approved contract explicitly permits it") to the no-future-fill PIT rule. That is a PIT relaxation the user specification does not contain.
   - #20 also narrows §M invariance to existing fingerprints.
   - Until the choice is made, where the two differ, workers follow the user's 2026-10-03 specification text, which #21 reproduces.
2. **Track C ↔ producers merge order (IF-1).** Track C `2137883` adds lineage fields and `evaluate_stamped` wrappers inside the protected `technical/engine.py`, `macro/engine.py` and `contracts/models.py`. Values are invariant, but byte and serialized-shape guards in #11, #12, #14, #15, #17 and #18 pin the pre-change bytes. The options:
   - (A) Track C merges first, and the producer owners re-pin their guards after re-verifying their values and semantic hashes.
   - (B) Producers merge first, and Track C moves its additions out of protected files. That changes the Track C SOFTWARE_FROZEN C4 phase, so it needs approval.
   - In both cases, accepting the Track C edit to Technical and Macro engine files is a cross-capability protected-boundary acceptance (contract §N). No Technical or Macro owner approval of it was found.
3. **Track C C8.** A6 numeric configuration plus 5 method details. Then A8 and A10. The first real CAL_VERIFY access is a separate gate.
4. **Canonical merges.** Any merge of #5 → #6 → (#7, #9 → #17 → #19), etc. is the user's decision. Start with the integration-ready chain #5 → #6.
5. **Publication grants.** P01 research-display, Frozen and Live grants are all NONE.
6. **Data and providers.** The Macro ALFRED key, a news provider, and an exchange-calendar vintage source.

## 5. Next autonomous actions (Primary Integration Writer)

1. Combined-tree full regression (GIE-001 tree A, pytest): 1058 passed, 10 failed. The failures are 7 IF-1 guards and 3 IF-2 sentinels, and no other test fails. Next: keep the evidence current as heads move.
2. Keep this index current on every remote change. Re-fetch, update GSI and GCH, and append to GLOBAL_HANDOFF_HISTORY.
3. When the user approves a canonical merge, run an exact-SHA pre-merge trial of that specific chain in merge order, then merge only what was approved.
4. Do not modify capability branches. IF-2 sentinel conversions and IF-4 CI enablement are owner actions. Their proposals are recorded in GIE-001.

## 6. Preserved objects and records

- `b84d768…` and `e4ae01b…` (local/unreferenced commits from past reports): **ORIGINAL_OBJECT_UNAVAILABLE**. Neither resolves in this clone's object database after a full fetch. They are not assumed identical, and no commit here claims either SHA.
- The Dynamic Workflow checkpoint is **NOT_FOUND_IN_REPOSITORY**: no branch contains a Dynamic Workflow artifact. `DYNAMIC_WORKFLOW_V1_SOFTWARE_FROZEN` is maintained per the user's instruction, and no Dynamic Workflow feature was added.
- Freeze evidence observed, not re-run:
  - Track A FROZEN_VERIFIED (canonical; `implementation/reports/gate_evidence/track_a_freeze_readiness_2026-09-27.json`).
  - Track C C0–C7 SOFTWARE_FROZEN (`feature/track-c-evl` reports).
  - Web MVP FREEZE_READY (`implementation/docs/web_mvp/STATUS.md`).
  - Track E PLV1_CONTENT_V1.0 Frozen (canonical).
- Approval evidence observed:
  - Track C partial approvals for C8 Package A and A6 (`implementation/reports/track_c_c8_*approval*_2026-10-02.*`).
  - P01 policy APPROVED/ACTIVE (`implementation/docs/producer_infrastructure/P01_APPROVAL_2026-10-02.md`).
  - QGV Context AP1–AP3 (`implementation/reports/qgv_context_filter_*approval*_2026-10-02.json`).
