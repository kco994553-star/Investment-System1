# Investment-System1 · GLOBAL_CURRENT_HANDOFF

Routing/index SSoT only. This file is not a calculation, policy, approval or publication authority. Scoped Decision Registers, approval evidence and the exact SHA win on any conflict. Draft-branch results recorded here are not canonical completion.

| Field | Value |
|---|---|
| Handoff ID | GCH-008 (supersedes GCH-007 as the current handoff; every earlier entry is kept in GLOBAL_HANDOFF_HISTORY) |
| Recorded | GCH-001 2026-10-03T01:18:13Z (`b118b68`); GCH-002 after CDR-001..003; GCH-007 2026-10-03 after GIE-008; GCH-008 after CDR-010/011 |
| Primary Integration Writer | Claude Code session `session_019znshzTYgyBnuuBmSxdPFN`, designated by the user on 2026-10-03 |
| Live location | `origin/integration/global-handoff-v1` : `implementation/docs/coordination/GLOBAL_CURRENT_HANDOFF.md` |
| Canonical branch / HEAD | `claude/investment-system-top500-validation-alrugm` @ `b8e39a2196a6d7794a04a0cd5393c68329e126ca`. This matches the last independent audit checkpoint, and canonical has not moved since 2026-09-28 |
| Remote refs audited | 28 branches, 17 open PRs (#4, #5, #6, #7, #9–#21; #8 closed, #1–#3 merged) |
| Operating contract | `CLAUDE_CODE_WORKER_CONTRACT_v1.0` at **PR #21 exact HEAD** `f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798` (blob `617ef6d4…`) is the operational routing SSoT (CDR-001). PR #20 is SUPERSEDED_DUPLICATE: not merged, history retained, §J exception not adopted. #21 canonical merge is not approved |
| Supersedes | nothing. The root `Investment-System1 · CURRENT_HANDOFF.md` remains the canonical Track A/historical handoff, and Track C appends to it on its own branches. It is older than the current parallel state and is not edited here |

## 1. Read next

0. The operating contract at its operational SSoT pin (CDR-001): `git show f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798:implementation/docs/coordination/CLAUDE_CODE_WORKER_CONTRACT.md`.
1. `COORDINATION_DECISION_REGISTER.md`, then `GLOBAL_STATUS_INDEX.md` (same directory): per-capability `BRANCH_STATE`, `INTEGRATION_STATE`, `CANONICAL_STATE`, maturity, PR classification, dependency DAG.
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

Decided in this round (see `COORDINATION_DECISION_REGISTER.md`):

- **CDR-001.** Worker Contract SSoT = PR #21 exact HEAD. PR #20 is SUPERSEDED_DUPLICATE. This is not canonical-merge approval.
- **CDR-002.** The Track C ↔ producer merge order (IF-1) is **not chosen**. A result-invariant compatibility audit comes first (GIE-002). A/B returns to the user only if a change to one side's Frozen or protected contract is proven unavoidable.
- **CDR-003.** Track C C8: method policy is separated from numeric configuration. Already-approved method scope and synthetic/software validation continue autonomously on the Track C owner branch. Each unapproved method choice is presented with its result impact. α, B, L, seed, effect floor, minimum support and the real calibration configuration form a separate preregistered approval gate before CAL_VERIFY. No CAL_VERIFY or Holdout access.

Still open:

1. **Canonical merges** (always gated). Integration candidates: #30 `86ad362` (TRIAL_INTEGRATION_VERIFIED_WITH_NONBLOCKING_FINDINGS, GIE-006) and its published extension #38 `7e3861b` (#30 + #32 + #33 + #34 + #36; 9/9 CI ✓, GIE-008 §4). #31 and #35 are verified (GIE-008 §1, §3) but wait on the arithmetic decision.
2. **Publication grants.** P01 research-display, Frozen and Live grants remain NONE.
3. **Data and providers.** The Macro ALFRED key, a news provider, and an exchange-calendar vintage source.

Decided and in execution:

- **CDR-004** IF-1 = A1 + owner adoption: proposals #22–#27 pushed (writer gates PASS; Codex independent audit PASS; integration-owner verification pending). Remaining evidence-only adoption items outside #22–#27: #9 `docs/producer_infrastructure/evidence/validation.json` and #7 `docs/entity_metadata/evidence/numeric_fingerprint` record pre-adoption Technical/Macro fingerprints.
- **CDR-005** executed by the Track C owner (`9a9364c`, `972a23f`, `b9e01a9`); Actions 37097149378 SUCCESS on `b9e01a9`.
- **CDR-006** G-SUP method = M (additive v2, v1 preserved). **CDR-007** source descriptor (source/vintage/sample identity, synthetic scope). **CDR-008** implementer is Codex; the Primary Integration Writer verifies (13-point list) and does not implement. Codex #31 `29c2c20` is HANDOFF_READY and verified (GIE-008 §1); v2 waits on the arithmetic decision. CDR-009's end condition (HANDOFF_READY) is met for this checkpoint, but CDR-008 keeps Codex as the implementer, so the Codex branches and C8 G-SUP v2 paths stay read-only for the Primary Integration Writer.

- **CDR-010 (decided): M-B v2 arithmetic contract** = `math.fsum` reducer, block grouping, direct block sums, replicate mean `(Σ full block sums + partial)/n`, degenerate when `sqrt(v/n) > 0` is false. v1 and its historical results are preserved; v2 is additive. Codex implements it in PR #31 (CDR-008). Resolves the arithmetic item raised in PR #31 and reproduced in GIE-008 §2. It is not C8 FROZEN, CAL_VERIFY, numeric configuration, Holdout, Official or publication approval.
- **CDR-011 (decided):** the CDR-009 write exclusion applies again until PR #31's next HANDOFF_READY; read-only tracking only. At that checkpoint: fresh fetch, continue the 13-point verification with items 5 and 6b re-run plus the user's added list (GIE-008 successor), then a new combined trial of the verified trial + #31 + #35 on fresh heads. #38's results are not reused as the new trial.

Not approved (CDR-006/007 list): α, B, L / block rule, seed, effect floor, minimum support, size tolerance, dependence envelope / margin, real source taxonomy/default, real CAL_VERIFY access, C8 foundation ↔ G-SUP registry unification, Holdout, C8 SOFTWARE FROZEN, publication grant, Official, LIVE, canonical merge.

## 5. Next autonomous actions (Primary Integration Writer)

1. Current integration evidence: #30 `86ad362` re-audited (GIE-006); trial #38 `7e3861b` = #30 + #32 + #33 + #34 + #36, 9/9 pull-request CI ✓ plus a manually dispatched `codex-integration-readiness` run (GIE-008 §4). The GIE-001 combined-tree result (1058 passed, 10 IF-1/IF-2 failures) is historical: CDR-004 adoption removed the IF-1 failures in #30. Keep the evidence current as heads move.
1a. CDR-010 decided. Codex implements v2 in PR #31 (CDR-008); the Primary Integration Writer tracks it read-only (CDR-011) and does not duplicate it. At its next HANDOFF_READY: independent re-verification (items 5, 6b and the CDR-011 list), then a new combined trial of the verified trial + #31 + #35 on fresh heads.
1b. Owner-side follow-ups recorded, not done here: the IF-2 sentinel conversions; the Technical stack order (#22 on #11, then forward through #15 with #23 to #18 with #24); #31 N2 identity canonicalization before any real-source work; #31 N3 numpy importorskip or push-workflow numpy pins; #35 NB1/NB2.
1c. Web validator hardening (`web_mvp.py`) needs a #17 protected-digest repin and is not done autonomously (user instruction of 2026-10-03).
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
