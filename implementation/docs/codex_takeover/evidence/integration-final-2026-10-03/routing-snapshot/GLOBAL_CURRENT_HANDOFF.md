# Investment-System1 · GLOBAL_CURRENT_HANDOFF

Routing/index SSoT only. This file is not a calculation, policy, approval or publication authority. Scoped Decision Registers, approval evidence and the exact SHA win on any conflict. Draft-branch results recorded here are not canonical completion.

| Field | Value |
|---|---|
| Handoff ID | GCH-002 (supersedes GCH-001 as the current handoff; GCH-001 is kept in GLOBAL_HANDOFF_HISTORY) |
| Recorded | GCH-001 2026-10-03T01:18:13Z (`b118b68`); GCH-002 updates after the user decisions CDR-001..003 |
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

1. **Canonical merges** (always gated). Integration candidate: #30 `86ad362` (FRESH at 06:58Z, 9/9 Actions green; re-audit GIE-006 pending).
2. **Publication grants.** P01 research-display, Frozen and Live grants remain NONE.
3. **Data and providers.** The Macro ALFRED key, a news provider, and an exchange-calendar vintage source.

Decided and in execution:

- **CDR-004** IF-1 = A1 + owner adoption: proposals #22–#27 pushed (writer gates PASS; Codex independent audit PASS; integration-owner verification pending). Remaining evidence-only adoption items outside #22–#27: #9 `docs/producer_infrastructure/evidence/validation.json` and #7 `docs/entity_metadata/evidence/numeric_fingerprint` record pre-adoption Technical/Macro fingerprints.
- **CDR-005** executed by the Track C owner (`9a9364c`, `972a23f`, `b9e01a9`); Actions 37097149378 SUCCESS on `b9e01a9`.
- **CDR-006** G-SUP method = M (additive v2, v1 preserved). **CDR-007** source descriptor (source/vintage/sample identity, synthetic scope). **CDR-008** implementer is Codex; the Primary Integration Writer verifies (13-point list) and does not implement. No Codex Track C branch exists yet.

- **Raised by Codex in PR #31 (not yet independently verified by the integration owner): USER_DECISION_REQUIRED_ARITHMETIC_REDUCTION.** Authoritative M-B v2 is not active because the floating-point reduction used inside the replicate statistic changes integer exceedance counts with identical frozen indices, formulas and inputs. Codex's synthetic example: `[.01,.01,-.01,-.02,.02,.01,.01,.01]`, n=8, L=3, B=19, seed 46 → `math.fsum` p=.10 vs literal NumPy cumulative-block reduction p=.20; a second example gives Python left-to-right `sum` p=.40 vs `fsum` p=.35. The Q1 approval evidence did not record its NumPy version. Source: `implementation/reports/gsup_v2_oracle/ARITHMETIC_REDUCTION_REVIEW_2026-10-03.md` on `codex/track-c-gsup-v2-2026-10-03` @ `675d0d2`. No option selected.

Not approved (CDR-006/007 list): α, B, L / block rule, seed, effect floor, minimum support, size tolerance, dependence envelope / margin, real source taxonomy/default, real CAL_VERIFY access, C8 foundation ↔ G-SUP registry unification, Holdout, C8 SOFTWARE FROZEN, publication grant, Official, LIVE, canonical merge.

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
