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
