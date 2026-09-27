Investment-System1 · Artifact Evidence Register  
기준: 2026-09-23 08:54 KST

1. Classes

ORIGINAL — 원 개발 패키지·로그. 회수된 것만 ORIGINAL.  
RECORDED — 문서 PASS. 재실행 전.  
NEW IMPLEMENTATION — 이번 허브에서 명세 기반으로 새로 작성한 코드.  
VERIFIED — 이번 환경에서 새 구현 테스트를 실제로 실행해 PASS.  
SYNTHETIC VERIFIED — fixture/synthetic 입력으로 VERIFIED. 실데이터 검증 아님.  
MISSING ORIGINAL — 과거 패키지 부재.

2. Original Recovery

Status: BLOCKED  
Code Present (original) = 0  
Reproducible (original) = 0  
VERIFIED (original) = 0

3. New implementation

Path: Investment-System1/implementation/  
Line: investment_system_impl-v0.1.0  
Kind: NEW IMPLEMENTATION  
Tests executed 2026-09-23: 19 passed  
Evidence class: SYNTHETIC VERIFIED  
Report: implementation/reports/pytest_2026-09-23.txt  
Pipeline: implementation/reports/synthetic_pipeline_2026-09-23.json

4. Do not confuse

19 SYNTHETIC VERIFIED ≠ Python 299 / JS 27 / 103/103 / 366/366 / 159/159 / 28/28.  
Those remain RECORDED-only / ORIGINAL MISSING.

5. Update 2026-09-23 09:07
Implementation line v0.2.0.
Tests: 26 passed SYNTHETIC VERIFIED.
SEC fixture parser covered. Optional live fetch is LIVE_FETCH if network works.
Original Recovery still BLOCKED. Official Stage Gate still 2/7.

6. Update 2026-09-23 09:12
pytest 31 passed SYNTHETIC VERIFIED.
Official v1.1 book runner uses synthetic fixtures only.
REAL-DATA VERIFIED still 0. Stage Gate 2/7 unchanged.

7. Update 2026-09-23 09:21
pytest 34 SYNTHETIC VERIFIED.
Yahoo NVDA/JPM/MSFT = LIVE_FETCH prices.
JPM SEC companyfacts pull = LIVE_FETCH fundamentals parse, incomplete factor coverage, not Stage 2.
REAL-DATA VERIFIED remains 0.

8. Update 2026-09-23 09:26
pytest 38 SYNTHETIC VERIFIED.
US Yahoo live prices 17/17 LIVE_FETCH. Not historical PIT. Not Stage 2.
KR track not started.

9. Update 2026-09-23 · Claude
Runner: tools/mini_pytest.py shim (pytest not installable; no network). 123 passed = SYNTHETIC VERIFIED. Report: implementation/reports/mini_pytest_2026-09-23_claude.txt
Prior 112 reproduced 112/112 in a fresh sandbox after fixing one hardcoded absolute path (portability, not logic).
500-company benchmark = SYNTHETIC, in-process only: implementation/reports/bench_universe_500_2026-09-23.json. Live wall-clock (network) NOT measured.
S&P interval ingest: NOT RUN (egress 403). REAL-DATA VERIFIED still 0.

10. Update 2026-09-23 round 2 · Claude
127 passed SYNTHETIC VERIFIED (shim). reports/mini_pytest_2026-09-23_claude_r2.txt
fetch tool wiring verified with stubbed HTTP only. No real data fetched. REAL-DATA VERIFIED 0.

11. Update 2026-09-23 round 3 · Claude
132 passed SYNTHETIC VERIFIED. reports/mini_pytest_2026-09-23_claude_r3.txt
Network investigation: bash_tool egress BLOCKED (proxy allowlist, reproducible, see C-20). web_search/web_fetch reach sec.gov but are not a bulk-ingestion path. tools/fetch_real_data.py NOT RUN (no route succeeded). Ingestion/replay split built and tested with stubbed HTTP only — no real bytes in this store. REAL-DATA VERIFIED still 0.

12. Update 2026-09-23 round 5 · OpenAI GPT-5.6 Sol
Baseline reproduction BEFORE changes: 138 passed, 0 failed, SYNTHETIC VERIFIED. Report: implementation/reports/mini_pytest_2026-09-23_openai_r5.txt.
Actual existing ingestion runner executed against SEC tickers + AAPL companyfacts/submissions + Yahoo chart: 0/4; all ERROR_URLError due container name-resolution failure. Report: implementation/reports/real_ingestion_probe_2026-09-23_openai_r5.txt. This is BLOCKED evidence, not REAL-DATA evidence.
Post-change regression: 140 passed, 0 failed, SYNTHETIC VERIFIED. Report: implementation/reports/mini_pytest_2026-09-23_openai_r5_postchange.txt.
Offline implementation evidence: RawDatasetStore replacement archives prior bytes+manifest; fetch_real_data.py --refresh enables intentional new raw vintages without destructive overwrite. Two new tests verify archive and refresh behavior.
REAL-DATA VERIFIED = 0. Validation ladder not promoted.

## OpenAI relay round 6 evidence — 2026-09-23 16:49 KST
- R6-E1 Reproducibility: `implementation/reports/mini_pytest_2026-09-23_openai_r6_baseline.txt` — 140 passed / 0 failed. VERIFIED.
- R6-E2 REAL ingestion attempt: `implementation/reports/real_ingestion_probe_2026-09-23_openai_r6.txt` + `implementation/data/raw/ingest_run_*.json` — existing runner/store, 0/4 successful, 4/4 ERROR_URLError due DNS resolution failure. BLOCKED evidence; not REAL-DATA VERIFIED.
- R6-E3 500-company regression: `implementation/reports/bench_universe_500_2026-09-23_openai_r6.txt` — full batch median 0.1741s; PIT historical synthetic 0.8959s; 0 lookahead violations; PASS. SYNTHETIC only.

12. Update 2026-09-24 · Claude (new session)
Baseline reproduced from the uploaded SSoT ZIP: 150/150 (one mini_pytest.py shim fix --
MonkeyPatch.setattr dotted-string form -- not a code regression). Full suite after this
round's Promotion Gate v2 additions: 162/162. reports/mini_pytest_2026-09-24_claude.txt
Real (non-synthetic) evidence: reports/gate_evidence/exchange_reference_wfe_2024-12-31.json
(WFE Dec 2024 exchange counts, real sourced/dated), universe_completeness_gate_2024-12-31.json
(FAIL, 17.6% coverage vs real benchmark), top500_sufficiency_gate_2024-12-31.json /
promotion_gate_v2_2024-12-31.json (FAIL, no large-cap reference available -- C-22).
All evaluated against the real reports/mcap_audit_2024-12-31.json (598 companyfacts, 297
rankable) audit carried over from the prior session.
REAL-DATA VERIFIED: still NO. Nothing promoted. Network BLOCKED again this session
(reconfirmed, same allowlist-403 signature as prior Claude-hub rounds). RawDatasetStore
blobs missing from the delivered ZIP (C-21) -- flagged to user.

13. Update 2026-09-24 (continued) · Claude
reports/gate_evidence/candidate_hygiene_598.json: real, offline, pattern-based audit of the
real 598-name pool -- 185 flagged (104 preferred-share-shaped, 81 OTC-ADR-shaped), 413
clean. Heuristic only, not authoritative, not applied to any gate.
Full suite 166/166 (162 prior + 4 new). reports/mini_pytest_2026-09-24_claude.txt covers
the earlier count in this session; hygiene-tool tests added after that snapshot -- final
count confirmed by direct run, not yet re-saved to a dated report file (see next write).

14. Update 2026-09-25 · Claude
173 passed (166 prior + 7 new). Real evidence this round: sp500_current_2026_raw.md +
sp500_changes_since_2025-01-01_raw.json (fetched verbatim from Wikipedia) ->
sp500_reconstructed_2024-12-31.json (mechanical reconstruction, 503 members, validated) ->
missing_large_cap_priority_plan_2024-12-31.json (282 missing, 253 with CIK) ->
top500_sufficiency_gate_2024-12-31_real_reference.json (real FAIL, MISSING_LARGE_CAP_NAMES) ->
promotion_gate_v2_2024-12-31_updated.json (real FAIL). candidate_hygiene_spotcheck_verification.json
(2 real spot-checks + 1 authoritative pattern-level citation).
REAL-DATA VERIFIED still NO -- these are real reference/identity checks, not real
companyfacts/price ingestion (still blocked by C-21/C-20).

15. Update 2026-09-25 round 2 · Claude
No new code; evidence-file updates only. missing_large_cap_priority_plan_2024-12-31.json: 4
more CIKs resolved (CE, CTRA, CZR, DFS), 257/282 now ready. sp500_reconstructed_2024-12-31.json:
AMTM discrepancy resolved and documented (qa_note field), corrected 19/19 spot-check score.
173/173 tests unchanged. REAL-DATA VERIFIED still NO -- C-21 network/store recovery remains
BLOCKED after a genuine re-attempt this round (see Conflict Register).

16. Update 2026-09-25 round 3 · Claude
No new evidence produced -- C-21 reconfirmed BLOCKED, no workaround forced per instruction.
173/173 tests unchanged. REAL-DATA VERIFIED still NO.

17. Update 2026-09-26 · Claude Code
- REAL-DATA chain evidence: reports/gate_evidence/gate_chain_2024-12-31_real_gha.json from Actions run #30 (id 36206384858,
  commit 316ada7): 979 rankable, #500 cutoff $15.189B, Promotion Gate v2 FAIL (Russell superset: PINC, WOLF not rankable;
  PPLI non-positive shares). Official US Market-Cap Top 500 PIT NOT declared. REAL-DATA VERIFIED: NO (gate not passed).
- class_rights_passages_2024-12-31.json (verbatim 10-K/10-Q passages, filed <= as_of) and class_economics_2024-12-31.json
  (reviewed determinations; verified by the chain: H, RKT, TKO, TPG ECONOMIC_EQUIVALENT_DETERMINED).
- Personal Investment Layer v1 relay package imported as
  `Investment-System1 · PERSONAL_INVESTMENT_LAYER_V1_HANDOFF.md` (additive, Architecture FROZEN, Implementation NOT
  STARTED). Intake conflicts C-24..C-31.
- Tests: 242/242 (mini_pytest shim) and 242/242 (pytest), SYNTHETIC + replayed evidence; one correctness fix (C-27).

18. Update 2026-09-26 17:53 KST · Codex / C-36 independent revalidation
- Baseline at a83fb64 reproduced: 291/291. Corrected merged tree with OWL evidence: 293/293; py_compile and diff check PASS.
- Run #56 (id 36228653355, evidence commit 361ff46): subject-CIK/CUSIP fixes worked; Russell reference 991/991, only
  explicit escrow unresolved, but OWL was still present-not-rankable because the run started before its class-economics
  evidence commit. Official remained suspended, correctly fail-closed.
- Run #57 (id 36229163158, head eb98031, evidence commit 195c5da): corrected Russell reference 991 members; missing 0;
  present-not-rankable 0; non-escrow unresolved 0; collisions 0; missing member CUSIPs 0. Sufficiency PASS; Promotion Gate
  v2 PASS; gate/snapshot consistency 500/500 PASS; cutoff $15,421,829,271.49; Official blockers 0.
- Run #57 gate result is eligible for Official restoration, but the persisted `official_snapshot_2024-12-31.json` was not
  regenerated: it still records universe `uni_0ad936238f45`, cutoff $15.338B, and TPR at rank 500. The corrected gate has
  OWL rank 336 at $27.633B (Class A + cited 1:1 Class C; Class D unvalued), ALGN rank 500 at $15.422B, and no FNF.
- Fail-closed correction: 2024-12-31 Official remains SUSPENDED until a single-date `official_pipeline` rebuild consumes
  run #57 evidence. 2024-09-30 remains SUSPENDED pending the same independent revalidation; 2024-06-30 remains open.
  `real_data_verified` is still emitted as false, so REAL-DATA backend Freeze is not claimed.

19. Update 2026-09-26 18:38 KST · Codex / corrected 2024-12-31 Official rebuild
- Run #58 (id 36231916104, evidence commit f425e4d) regenerated correct 500-member content but exposed a provenance-identity
  defect: independent reconstruction minted Gate universe `uni_78060185a0d6` and Official universe `uni_5eb9effc9165`.
  Official remained SUSPENDED; no result was promoted.
- Minimal fix: after exact Gate/Official membership and order verification, `official_pipeline.py` preserves the Gate
  universe ID and fails closed if the ID is absent. Workflow committed-Gate reuse is permitted only with `skip_fetch=true`
  and explicit dates. Targeted regressions 102/102; full suite 294/294 (mini_pytest shim); py_compile/diff check PASS.
- Run #59 (id 36233121639, head 94fb5f8, evidence commit 1832747) used the committed corrected Gate evidence. Official
  snapshot ID = Gate ID = `uni_cf6aa3403869`; membership 500/500, order/rank, market cap and cutoff are identical;
  cutoff $15,421,829,271.493835; #500 ALGN; FNF absent; all 500 audited share/price provenance records preserved.
- Corrected single_as_of: 468 selected/linked, 494 investable, 6 missing, 0 name errors, EW -0.01649309224255184.
  Corrected 500-company benchmark: 29.956 s, peak RSS 9,478.8 MB, 0 name errors. Walk-forward correctly remained blocked
  because only one date was supplied. 2024-12-31 Official is RESTORED. 2024-09-30 remains SUSPENDED; 2024-06-30 open.

20. Update 2026-09-26 18:55 KST · Codex / corrected 2024-09-30 independent rebuild
- Run #60 (id 36233560867, head 1832747, evidence commit ab72939) fetched and resolved the 2024-09-30 reference anew:
  994 members; missing 0; present-not-rankable 0; non-escrow unresolved 0; duplicate membership 0; member CUSIPs complete.
- Sufficiency and Promotion Gate v2 PASS; Official blockers 0. Gate ID = Official ID = `uni_e334f94a73c3`; membership
  500/500, order/rank, market caps, cutoff $15,573,548,285.00, and all audited share/price provenance fields match.
  #500 ENPH. 2024-09-30 Official is RESTORED; pre-C-36 runs #46/#47 remain superseded.
- Corrected single_as_of: 469 selected/linked, 495 investable, 5 missing, 0 name errors, EW 0.0004569665513276751.
  Corrected benchmark: 28.362 s, peak RSS 9,534.8 MB, 0 name errors. Walk-forward not run (single date only).

21. Update 2026-09-26 19:07 KST · Codex / corrected 2024-06-30 independent revalidation
- Run #61 (id 36234273515, head ab72939, evidence commit 2e04c1b): internal candidate consistency PASS 500/500 and
  cutoff $14,021,530,297.505974, but the corrected Russell reference fails: GRAL/WRK present-not-rankable plus non-escrow
  unresolved ARDAGH GROUP SA (L0223L101) and LIBERTY SIRIUS XM (531229813). Sufficiency/Promotion Gate v2 FAIL.
- Pipeline correctly emitted `BLOCKED_NO_OFFICIAL_DATE`; no single_as_of, benchmark, or walk-forward result was promoted.
  WRK N-PORT remained investigation-only; GRAL's pro-forma count was not promoted. Liberty tracking-stock policy is C-37.

22. Update 2026-09-26 20:54 KST · Codex / Ardagh source-row audit and evidence-preservation fix
- Re-read SEC N-PORT accession 0001752724-24-189684. ARDAGH GROUP SA (L0223L101 / LU1565283667) is a positive EC
  position: 12,001 NS, valUSD $76,686.39, long, fair-value level 2. LIBERTY SIRIUS XM (531229813 / US5312298137) is
  55,497 NS, valUSD $1,229,258.55, long, fair-value level 1. Neither is a zero-value or escrow residue.
- SEC Form 25 (filed 2021-10-06) removed Ardagh Class A shares from NYSE; Form 15 (filed 2021-10-18) terminated
  registration/suspended reporting and stated 115 record holders. This converts the Ardagh item from an identity-search
  gap into policy conflict C-38: positive delisted/private fund residue versus the listed-company Universe. Structured
  evidence: implementation/reports/gate_evidence/nport_unresolved_source_audit_2024-06-30.json.
- Minimal Track A patch retains title/ISIN/category/country/value/balance/units/currency/fair-value-level/payoff profile
  when a historical-name member is demoted and carries those fields into Sufficiency evidence. Gate criteria remain
  unchanged and fail-closed. Targeted N-PORT/gate tests 103/103 PASS; full regression 295/295 PASS. Track B unchanged.

23. Update 2026-09-27 08:24 KST · Codex / Track A-B-C relay reconciliation
- Fresh fetch: local HEAD `bdf0939`; remote branch `4f08571`; local ahead 17 / behind 0; worktree clean before this
  documentation update. Existing history including `069e7c2` was not rewritten or squashed.
- Baseline directly re-run: 295/295 PASS via mini_pytest shim. Track B dedicated suite: 13/13 PASS.
- Track B static dependency audit: 10 personal package files; no import out to Track A and no Track A reverse runtime
  import into `investment_system.personal`. Diff from its implementation commit `48a6243` is zero.
- Track C repository audit: no EVL spec or implementation existed. Registered
  `Investment-System1 · Experiment & Validation Layer Specification v0.1.md` as `EVL_SPEC_v0.1`, DESIGN FROZEN /
  IMPLEMENTATION NOT STARTED. No Track C code or tests were created.
- SSoT-only reconciliation: Master/Project/Current and the Track B handoff now reflect P0 IMPLEMENTED+FROZEN,
  Track C ownership/dependency, Pre-Tax scope, and the unchanged Track A priority/blockers. No new feature was added.

24. Update 2026-09-27 11:07 KST · Codex / RIG-News repository consistency audit
- Input read in full: `RIG_NEWS_WORK_HANDOFF_PROMPT_v0.1.md` and `RIG_NEWS_ARCHITECTURE_v0.1.md` from the supplied ZIP.
- Fresh fetch baseline: local `3fe8312`, remote `7b0c93e`, ahead 27 / behind 0, identical trees, clean worktree before
  registration. No squash/rebase/reset/history rewrite was performed.
- Actual contract/code evidence: `contracts/universe.py` defines DataEvent/EventKind; `universe/events.py` defers
  unavailable events and routes NEWS to evidence only; tests prove NEWS does not mutate QGV and future events defer.
  Frontend IA defines Summary→Evidence→Detail. Global/Korea contract defines shared NewsItem→Claim→Event IDs and
  evidence-bearing RelationshipEdge semantics.
- Actual Yahoo evidence: `yahoo_events__AAPL__5y.json` has source kind `YAHOO_SPLIT_EVENTS`, its URL requests
  `events=split`, and `audit_mcap_store.py` reads only `chart.result[].events.splits`; it is not News/RIG evidence.
- Cross-architecture result: no duplicate runtime/store was created; DataEvent and future real-world events remain
  separate; Track A/B/C ownership and freezes remain intact. C-39 records the shared identity implementation-evidence
  mismatch. Full baseline 297/297 PASS (mini_pytest shim).
- Registered `Investment-System1 · RIG News Architecture v0.1.md` as DESIGN FROZEN / IMPLEMENTATION NOT STARTED.
  No RIG code, tests, UI, store, notification runtime, score, or Official result was created.

25. Update 2026-09-27 16:02 KST · Codex / C-39 shared identity recovery
- Restored the Global/Korea SSoT's already-declared common identity/context implementation at
  `implementation/src/investment_system/contracts/global_universe.py`; no new mapping policy, provider, or Official
  result was introduced. The hierarchy is issuer -> security -> dated listing, and ticker is listing-only.
- `UniverseContext` keeps Analysis Universe, Network Region, and News Region independent. `FXSnapshot` and
  `EligibilityRecord` require explicit raw/evidence provenance and reject `available_at > as_of`; Korea/Global
  AnalysisUniverse instances reject premature Official status.
- Evidence: `implementation/tests/test_global_universe_contracts.py` 6/6 PASS; full mini_pytest suite 308/308 PASS;
  py_compile and diff check PASS. Static boundary: the common module imports no Track B `personal` code, and no frozen
  Track B file changed. C-39 is RESOLVED; RIG remains DESIGN FROZEN / IMPLEMENTATION NOT STARTED.


## Track A audit overlay — 2026-09-27 19:56 KST

This Track A overlay supersedes prior Track A status claims only. Source run #70/ed343ba recovered and hashes verified (6,808 artifacts). C-40 dated-identity replay fixed; three 500-name RESEARCH replays and two adjacent-date steps match exactly, 0 name errors. C-41 share/price-unit audit detects 20 events (4/8/8); all three final Official gates are blocked, historical snapshots SUSPENDED, Freeze NOT DECLARED. Corporate-action policy candidate CA-UNIT-v1.0 remains D3-P PROPOSED. Full regression 388/388 PASS (mini_pytest shim). Evidence: `implementation/reports/gate_evidence/track_a_freeze_readiness_2026-09-27.json`; detail: `Investment-System1 · TRACK_A_REAL_DATA_STATUS.md`. GitHub write returned 403; this update is local pending upload. Other tracks were not modified.
