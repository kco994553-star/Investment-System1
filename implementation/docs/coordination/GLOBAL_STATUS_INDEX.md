# Investment-System1 · GLOBAL_STATUS_INDEX

Routing/index only. This file is not a calculation, policy, approval or publication authority. Where it disagrees with a scoped STATUS/HANDOFF, a Decision Register, approval evidence or the exact SHA, those win. Report the disagreement to the Primary Integration Writer.

| Field | Value |
|---|---|
| Index revision | GSI-004 (CDR-004/005 execution in progress; Track C owner tip b9e01a97; Actions run 37097149378 dispatched) |
| Recorded | 2026-10-03T01:18:13Z, commit `b118b68` (fresh `git fetch` of all 28 remote refs at 2026-10-03T01:07Z) |
| Writer | Primary Integration Writer, Claude Code session `session_019znshzTYgyBnuuBmSxdPFN` |
| Live location | `origin/integration/global-handoff-v1` : `implementation/docs/coordination/GLOBAL_STATUS_INDEX.md` |
| Canonical | `claude/investment-system-top500-validation-alrugm` @ `b8e39a2196a6d7794a04a0cd5393c68329e126ca` (= `origin/HEAD`; unchanged since 2026-09-28) |
| Operating contract | `CLAUDE_CODE_WORKER_CONTRACT_v1.0` at PR #21 exact HEAD `f1b5afb` is the operational routing SSoT (CDR-001). PR #20 is SUPERSEDED_DUPLICATE (not merged, retained) |

## 1. Maturity scale and state columns

Maturity is the highest stage actually reached in order: `DESIGN → IMPLEMENTED → SYNTHETIC_VERIFIED → REAL_DATA_VERIFIED → INTEGRATED → OPERATIONAL`. It is never computed from test or commit counts.

- `SOFTWARE_FROZEN` and `FREEZE_READY` are separate software states. Neither implies REAL_DATA_VERIFIED, Official, Holdout-tested or OPERATIONAL.
- `INTEGRATED` requires a canonical merge.
- A capability merged with only synthetic verification is shown as `SYNTHETIC_VERIFIED · canonical MERGED`.

The three state columns are separate:

- `BRANCH_STATE`: the owner branch HEAD and the CI on that exact HEAD.
- `INTEGRATION_STATE`: trial or read-only integration evidence.
- `CANONICAL_STATE`: whether the work is on canonical.

## 2. Capability index

CI column key:

- **HEAD ✓**: a GitHub Actions success on the exact HEAD.
- **code ✓ / head docs-only**: success on the tested code SHA, and the later HEAD commits change docs or evidence only. Verified with `git diff --name-only`.
- **NOT_RUN**: no Actions run exists for the branch.

| # | Capability | Owner branch @ HEAD | PR | Maturity | BRANCH_STATE (CI on HEAD) | INTEGRATION_STATE | CANONICAL_STATE | Scoped status |
|---|---|---|---|---|---|---|---|---|
| 1 | Track A REAL-DATA main | canonical (`recovery/track-a-real-data-frozen` @ `a79642f`, merged) | #3 merged | **INTEGRATED** (FROZEN_VERIFIED) | merged | merged as `bd6bf42` | MERGED | root `Investment-System1 · TRACK_A_REAL_DATA_STATUS.md` |
| 2 | Track B Personal Investment Layer | canonical (P0 only) | — | IMPLEMENTED (P0 contracts FROZEN); P1+ NOT_STARTED | — | — | P0 MERGED | root `Investment-System1 · PERSONAL_INVESTMENT_LAYER_V1_HANDOFF.md` |
| 3 | Track C EVL (C0–C8) | `feature/track-c-evl` @ `ff78c4f`; ahead: `ccr-22e3ff16-p7n5k5` @ **`b9e01a97`** (owner tip; no PR) | #4 | SYNTHETIC_VERIFIED (C0–C7 SOFTWARE_FROZEN, 8/11 software phases; C8 PARTIAL_FOUNDATION_VERIFIED + G-SUP fail-closed repairs 9a9364c/b9e01a97). Real PIT validation NOT_RUN | #4 HEAD ✓ (run 36994387375). `ccr-22e3ff16` @ `b9e01a97`: Actions run **37097149378** (workflow_dispatch by the integration writer, `contents: read`) in progress at 04:37Z; owner-reported local full suite 923 passed at 972a23f | Text-clean with every branch. IF-1 decided: CDR-004 (A1 + owner adoption); producer re-pin proposals in progress | NOT_MERGED | `feature/track-c-evl`: root `CURRENT_HANDOFF` + `implementation/reports/track_c_decision_register_2026-10-01.md` (owner tip has CDR-005 entries) |
| 4 | Track D RIG/News P0–P4 | canonical | #1 merged | SYNTHETIC_VERIFIED · canonical MERGED | merged | merged | MERGED (P0–P4) | root `Investment-System1 · RIG News Architecture v0.1.md` |
| 5 | Track E Prompt Library v1 | canonical | #2 merged | SYNTHETIC_VERIFIED · canonical MERGED (PLV1_CONTENT_V1.0 Frozen) | merged | merged | MERGED | root `Investment-System1 · TRACK_E_PROMPT_LIBRARY_V1_STATUS.md` |
| 6 | QGV Real Producer | `ccr-db5d5960-qen9yi` @ `5eec129` | #10 | **REAL_DATA_VERIFIED** (500/500 persisted × 3 dates from Track A Frozen raw; not fully scored; READY coverage 0) | code ✓ `4b772c2` (run 36852186517) / head docs-only | Trial: clean merge. Sentinel IF-2 fails by design after #9 merges | NOT_MERGED | `implementation/docs/qgv_producer/STATUS.md` |
| 7 | QGV Context & Filter policy | `docs/qgv-context-policy-approvals` @ `b42f2be` | none | DESIGN (AP1–AP3 user-approved, AP4–AP6 gated; no implementation) | docs only | clean | NOT_MERGED | `implementation/reports/qgv_context_filter_decision_register.md` |
| 8 | Leaderboard REAL Producer | `feature/leaderboard-real-producer-v1` @ `0d48d86` | #14 | **REAL_DATA_VERIFIED** (research replay of real QGV exports; 500 persisted per date; READY 0; publication NOT_AVAILABLE; within-tie order POLICY_BLOCKED) | HEAD ✓ (run 36979467756) | Trial: clean merge. IF-1 guards fail with Track C. Sentinel IF-2 fails after #9 | NOT_MERGED | `implementation/docs/leaderboard_real_producer/STATUS.md` |
| 9 | Technical real-input producer | `feature/technical-real-producer-v1` @ `a2e0790` | #11 | SYNTHETIC_VERIFIED (3-name live-fetched input gate; `model_applied=false`) | HEAD ✓ (run 36855446809) | IF-1 guard fails with Track C | NOT_MERGED | `implementation/docs/technical_real_producer/STATUS.md` |
| 10 | Technical REAL model (M1/M2; M3 held) | `feature/technical-real-model-v1` @ `ce58704` (on #11) | #15 | SYNTHETIC_VERIFIED. REAL_TECHNICAL_RESEARCH_PRODUCER_READY = NO | HEAD ✓ (run 36859556060) | IF-1 guard fails with Track C | NOT_MERGED | `implementation/docs/technical_real_model/STATUS.md` |
| 11 | US Equity Trading Session v1 | `feature/us-equity-session-v1` @ `2c088ce` (on #15) | #18 | SYNTHETIC_VERIFIED (fixture vintages; no exchange-issued vintage replayed) | HEAD ✓ (run 36997929255) | IF-1 guard fails with Track C | NOT_MERGED | `implementation/docs/us_equity_session/STATUS.md` |
| 12 | Macro REAL Producer | `feature/macro-real-producer-v1` @ `61d3352` (on #9 @ `6fe9eee`) | #12 | SYNTHETIC_VERIFIED (caller-supplied ALFRED vintages; no live FRED; `real_data_verified=false`) | **NOT_RUN** on Actions. Local pytest at exact HEAD: 442 passed (this checkpoint) | IF-1 guard fails with Track C. PR base moved `6fe9eee → f8af596` (docs-only delta) | NOT_MERGED | `implementation/docs/macro_real_producer/STATUS.md` |
| 13 | RIG news real ingestion | `feature/rig-news-real-ingestion-v1` @ `8bb990b` | #13 | SYNTHETIC_VERIFIED (contract/normalizer; no provider activated) | **NOT_RUN** on Actions. Local pytest at exact HEAD: 410 passed (this checkpoint) | Sentinel IF-2 fails after #7 merges | NOT_MERGED | `implementation/docs/rig_news_ingest/STATUS.md` |
| 14 | SEC 8-K primary disclosure | `feature/sec-primary-disclosure-v1` @ `ef65caa` (on #13) | #16 | SYNTHETIC_VERIFIED (supplied Atom bytes; live fetch not run) | HEAD ✓ (run 36979915604) | clean | NOT_MERGED | `implementation/docs/sec_primary_disclosure/STATUS.md` |
| 15 | Producer Infrastructure | `feature/producer-infrastructure-v1` @ `f8af596` (on #6) | #9 | SYNTHETIC_VERIFIED | HEAD ✓ (run 36982361014) | clean; P01 policy APPROVED/ACTIVE recorded on this branch | NOT_MERGED | `implementation/docs/producer_infrastructure/STATUS.md` |
| 16 | P01 Research Publication | `feature/p01-research-publication-v1` @ `21039a0` (on #9) | #17 | SYNTHETIC_VERIFIED. All grants NONE; `RESEARCH_DISPLAY_ACTIVE=NO` | HEAD ✓ (run 36994066298) | IF-1 guards (fingerprint + protected bytes) fail with Track C | NOT_MERGED | `implementation/docs/research_publication/STATUS.md` |
| 17 | QGV Invalidation binding | `feature/qgv-invalidation-binding-v1` @ `c3dbf8a` (on #17) | #19 | SYNTHETIC_VERIFIED. Not a display grant | HEAD ✓ (runs 37003833031, 37003833035) | clean | NOT_MERGED | `implementation/docs/invalidation_binding/STATUS.md` |
| 18 | Web MVP v1 | `feature/web-mvp-v1` @ `a4e49c8` | #5 | SYNTHETIC_VERIFIED (presentation FREEZE_READY; not LIVE) | HEAD ✓ (run 36418935056) | **Sequential trial PASS** canonical→#5→#6 on Actions (`integration/web-mvp-language-search` @ `e09d24e`) | NOT_MERGED | `implementation/docs/web_mvp/STATUS.md` |
| 19 | Global Language & Search | `feature/global-language-search-v1` @ `eda65bf` (on #5) | #6 | SYNTHETIC_VERIFIED | code ✓ `82ae07c` (run 36709513419) / head docs-only | **Sequential trial PASS** (as row 18) | NOT_MERGED | `implementation/docs/global_language_search/STATUS.md` |
| 20 | Entity Metadata coverage | `ccr-41677301-10nj3u` @ `a013f1c` (on #6) | #7 | **REAL_DATA_VERIFIED** (SEC/Wikidata ingest run 36847160494; search/display only, not PIT feature evidence) | code ✓ `773b264` (run 36848115601) / head docs-only | clean | NOT_MERGED | `implementation/docs/entity_metadata/STATUS.md` |
| 21 | Producer readiness audit | `ccr-e0fc1e48-9tcto3` @ `f415615` | none | audit artifact (no maturity) | docs/report only | clean | NOT_MERGED | `implementation/reports/producer_readiness_audit_2026-10-01.md` |
| 22 | Worker Contract (coordination) | `ccr-2e16018a-qukwmg` @ `f1b5afb` (#21, **operational SSoT**, CDR-001); `integration/claude-worker-contract-v1` @ `d87d4cd` (#20, SUPERSEDED_DUPLICATE) | #21 (#20 superseded) | DESIGN (operating document) | docs only; NOT_RUN (no docs CI) | #20 × #21 add/add conflict, resolved by CDR-001 (#20 is not merged) | NOT_MERGED (#21 canonical merge not approved) | the contract itself |
| 23 | Global Handoff (this index) | `integration/global-handoff-v1` | none | routing/index | docs only | — | NOT_MERGED (live branch by design) | `GLOBAL_CURRENT_HANDOFF.md` |
| 24 | Dynamic Workflow | — | — | `DYNAMIC_WORKFLOW_V1_SOFTWARE_FROZEN`, per the user's 2026-10-03 instruction | NOT_FOUND_IN_REPOSITORY: no Dynamic Workflow artifact or checkpoint file exists on any of the 28 branches | — | — | none |
| 25 | Daily operation pipeline | — | — | DESIGN (not started) | — | — | — | — |
| 26 | Portfolio actual operation (Track B P1+) | — | — | DESIGN (not started) | — | — | — | — |

Out of scope: `claude/lol-coach-relay-format-y8uk0x` @ `57032bf` is the separate LoL Coach project, 9 behind and 2 ahead of an older canonical. It is not tracked as an Investment-System capability.

Stale merged heads, no action: `feature/track-d-rig-news` and `claude/track-d-rig-news-p0-ot2gy6` @ `da86dfc` (#1), `feature/track-e-prompt-library-v1` @ `d226481` (#2), `recovery/track-a-real-data-frozen` @ `a79642f` (#3). All are fully contained in canonical.

## 3. Open PR classification

| PR | Head | Classification | Why |
|---|---|---|---|
| #5 Web MVP | `a4e49c8` | READY_FOR_INTEGRATION_AUDIT, audit done | HEAD ✓. Actions trial PASS. Waiting on the canonical-merge decision |
| #6 Language & Search | `eda65bf` | READY_FOR_INTEGRATION_AUDIT, audit done | Code ✓, head docs-only. Actions trial PASS. Must merge after #5 |
| #7 Entity Metadata | `a013f1c` | READY_FOR_INTEGRATION_AUDIT | Code ✓, head docs-only. Depends on #6 |
| #9 Producer Infrastructure | `f8af596` | READY_FOR_INTEGRATION_AUDIT | HEAD ✓. Depends on #6 |
| #17 P01 | `21039a0` | READY_FOR_INTEGRATION_AUDIT, with IF-1 | HEAD ✓. Depends on #9. Its engine guards conflict with Track C (IF-1) |
| #19 Invalidation | `c3dbf8a` | READY_FOR_INTEGRATION_AUDIT | HEAD ✓. Depends on #17 |
| #12 Macro | `61d3352` | STALE_CI_REVALIDATION_REQUIRED | No Actions run ever. PR base moved to `f8af596` (docs-only delta). Local exact-HEAD pytest 442 passed is not CI. IF-1 with Track C |
| #10 QGV Producer | `5eec129` | DEPENDENCY_BLOCKED (#9 merge order) | Code ✓. Its "PR #9 not merged" sentinel fails once #9 is in (IF-2), so the owner must adapt it at integration |
| #14 Leaderboard | `0d48d86` | DEPENDENCY_BLOCKED (#9, #10 pins) | HEAD ✓. Sentinel IF-2. IF-1 with Track C. Publication POLICY_BLOCKED |
| #11 Technical producer | `a2e0790` | READY_FOR_INTEGRATION_AUDIT, with IF-1 | HEAD ✓ |
| #15 Technical model | `ce58704` | READY_FOR_INTEGRATION_AUDIT, with IF-1 | HEAD ✓. Depends on #11 |
| #18 US Equity Session | `2c088ce` | READY_FOR_INTEGRATION_AUDIT, with IF-1; real validation DATA_BLOCKED | HEAD ✓. Depends on #15. No exchange-issued calendar vintage replayed |
| #13 RIG ingestion | `8bb990b` | STALE_CI_REVALIDATION_REQUIRED | No Actions run ever (local exact-HEAD pytest 410 passed). Sentinel IF-2 vs #7. Real provider: USER_DECISION (source/paid) |
| #16 SEC 8-K | `ef65caa` | DEPENDENCY_BLOCKED (#13) | HEAD ✓ |
| #4 Track C | `ff78c4f` | CONTINUE_IMPLEMENTATION, gated by USER_DECISION_REQUIRED | C8 A6 numeric configuration and 5 method details await approval (`ccr-22e3ff16`). IF-1 cross-track overlap needs a merge-order decision |
| #21 Worker Contract | `f1b5afb` | Operational routing SSoT (CDR-001); canonical merge = USER_DECISION_REQUIRED | Docs-only. Clean against canonical |
| #20 Worker Contract duplicate | `d87d4cd` | SUPERSEDED_DUPLICATE (CDR-001) | Not merged. History retained. §J exception not adopted |

## 4. Dependency DAG

Stacked PRs (`→` means "is the base of"):

```
canonical b8e39a2
├─ #5 Web MVP → #6 Language/Search ─┬─ #7 Entity Metadata
│                                   └─ #9 Producer Infra ─┬─ #17 P01 → #19 Invalidation
│                                                         └─ #12 Macro (PR base #9; branch contains #9 @ 6fe9eee only)
├─ #11 Technical producer → #15 Technical model → #18 US Equity Session
├─ #13 RIG ingestion → #16 SEC 8-K
├─ #10 QGV producer                       (read-only pin: #9 @ 5fa7ce0)
├─ #14 Leaderboard                        (read-only pins: #10 @ 5eec129, #9 @ 6fe9eee)
├─ #4 Track C → ccr-22e3ff16 (C8 G-SUP, no PR)
├─ docs/qgv-context-policy-approvals      (no PR)
├─ ccr-e0fc1e48 producer readiness audit  (no PR)
└─ #20 | #21 Worker Contract              (mutually exclusive)
```

Read-only cross-capability pins: these are consumed in tests or CI, not merged.

- #16 → #7 and #9 commits.
- #13 → #7 registry @ `a013f1c` and #9 @ `6fe9eee`.
- #14 → #10 and #9.
- #10 → #9 @ `5fa7ce0`.

Merge-order constraint: a stacked PR is never canonical-integration-ready before its base (contract §M).

## 5. Integration findings (from GIE-001)

Evidence: `implementation/docs/coordination/evidence/GIE-001_trial_integration_2026-10-03.md` (+ `.json`).

- **IF-1: Track C cross-track source overlap. Needs a merge-order decision.**
  - Track C commit `2137883` (2026-09-29, the "four-file C4 upstream repair") adds 88 lines and deletes 0 in four files: `technical/engine.py`, `macro/engine.py`, `contracts/models.py` and `contracts/lineage.py`.
  - Values are invariant. On the producer fingerprint fixtures, the only change is 4 new null/empty lineage fields (`available_at`, `data_stamp_refs`, `source_vintages`, `input_hash`) on each of 23 Technical/Macro snapshots, and no existing value changes.
  - It still changes the byte hashes and the serialized-snapshot fingerprints that 7 guard tests pin, across #11, #12, #14, #15, #17 and #18.
  - Without Track C, every engine fingerprint equals its pin.
- **IF-1 audit result (GIE-002, 2026-10-03): IMPOSSIBLE_WITHOUT_ONE_SIDE_CHANGE**, not refuted by the adversarial skeptic.
  - `contracts/lineage.py` is compatible as-is under every option.
  - The `models.py` fields and the two `evaluate_stamped` methods can move to a sidecar, but only by changing 2 Track C C4-frozen blobs (option B). Keeping them requires producer re-pins (option A).
  - Both options were measured result-invariant. A/B is USER_DECISION_REQUIRED (GCH-002 §4).
  - Evidence: `evidence/GIE-002_trackc_producer_compat_audit_2026-10-03.md` (+ `.json`, reference patches in `evidence/GIE-002_patches/`, not applied).
- **CDR-005 executed by the Track C owner session on its own branch (not by the integration writer):** 9a9364c (Q3 Development-only estimate computed inside the registry; one-shot keyed by CAL_VERIFY content commitment + profile + role, independent of campaign_id/role_id/label/root), 972a23f (docs), b9e01a97 (Development gate bound to preregistered `development_content_hash` + lineage ref; GIE-004 and the owner's five-item impact analysis recorded as EVIDENCE / NOT_AN_APPROVAL; M-B vs kernel minimal counterexamples CE1–CE5 recorded; **USER_DECISION_REQUIRED: authoritative method K / M / C**). The integration writer's planned proposal branch `track-c/c8-fail-closed-repair-v1` was therefore not created. Independent read-only audit of the fix: GIE-005 (in progress).
- **Track C C8 (GIE-004).** Independent read-only analysis of the method choices. Two fail-open bugs within approved policy are LOCAL_FIXABLE for the Track C owner:
  - (a) the Q3 Development-only estimate is not enforced;
  - (b) one-shot no-retest is bypassable via a new `campaign_id` (a synthetic retest returned STAT_PASS).
  - Evidence: `evidence/GIE-004_trackc_c8_method_impact_2026-10-03.md`.
- **IF-2: branch-isolation sentinels.**
  - #10 and #14 assert "PR #9 not merged here" (`infra_boundary.load_infra() is None`). #13 asserts that PR #7's `reports/entity_metadata` is absent.
  - These are false by design after integration. Each owner must convert its sentinel when its dependency merges. This is LOCAL_FIXABLE for the owner, not for other workers.
- **IF-3: Worker Contract duplicate.** Resolved by CDR-001: #21 is the SSoT and #20 is superseded.
  - #20 and #21 both add `CLAUDE.md` and `implementation/docs/coordination/CLAUDE_CODE_WORKER_CONTRACT.md` as v1.0, which is an add/add conflict.
  - The texts differ in meaning: #20 §J adds an exception, "unless an approved contract explicitly permits it", to the no-future-fill rule, and #20 §M narrows the numerical/semantic invariance check to "where an existing approved fingerprint exists". Neither is in the user's 2026-10-03 specification. #21 reproduces the specification and adds coordination locations, document relationships, a change log and a start-prompt appendix.
- **GIE-003 (source overlap and escalation sweep, 2026-10-03).** Besides IF-1, no PR modifies a pre-existing file owned by a capability outside its own stack. #17 appends to the P01 approval record without changing it; #9 normalizes the Web error type with the accept/reject set unchanged. A heuristic sweep of 13,187 added source lines found 0 grant/Official/LIVE/Holdout escalations (a pattern sweep, not a proof). Evidence: `evidence/GIE-003_source_overlap_escalation_2026-10-03.md`.
- **IF-4: CI gaps.** #12 and #13 have never run on Actions, and `ccr-22e3ff16` has no workflow trigger. Local exact-HEAD runs in this checkpoint are recorded in GIE-001 and are **not** CI_VERIFIED.
