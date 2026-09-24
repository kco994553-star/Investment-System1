Investment-System1 · Master Status Index  
기준: 2026-09-22  
역할: 저장 허브의 최신 상태와 문서 우선순위를 한 곳에서 관리한다.  
Artifact Recovery: BLOCKED. 이 인덱스의 PASS 숫자는 모두 RECORDED다. VERIFIED = 0.

1. Version Authority  
QGV System software line: v1.7.  
QGV scoring baseline: QGV Standard v1.5 balanced.  
Official Portfolio baseline: Portfolio v1.1 · 2026-09-14.  
Technical Analysis: 설계·구조 구현 완료, Phase 6 + Real PIT Validation v0.6 STRUCTURAL FREEZE.  
Macro: latest confirmed record v0.1.1. 동일 Latest 문서의 v0.1.4 Candidate는 CONFIRMED로 승격하지 않는다.  
Investment System integration: v1.1 flow + v1.2 PROVISIONAL policy layer.

2. Evidence Ledger (권한과 별도)

등급  
RECORDED: Drive/명세에 적힌 PASS. 원본 재실행 전.  
VERIFIED: 원본 패키지·테스트·로그로 이 허브에서 재실행해 기록이 맞음을 확인.  
MISSING / NOT RUN: 원본 또는 실행 자체가 없음.

현재 합계  
VERIFIED = 0  
Code Present = 0  
Reproducible = 0  
Recorded-only 모듈 = 6 (Analysis, Simulation, Portfolio, Leaderboard, Technical, Macro)

모듈별 RECORDED (덮어쓰지 말 것)  
QGV Analysis: Python 299 / JS 27 · Browser E2E NOT RUN  
QGV Simulation: 103/103 (local v0.6.8)  
QGV Portfolio: 366/366 (RC26)  
Leaderboard: 313+8 / Frontend 12 / Standalone Build  
Track Record: PASS 숫자 없음  
Technical LATEST: 159/159 (Master Status / Latest Status Update 2026-09-22)  
Technical STALE: 69/69 · Phase 4 (Project Index 구기록. LATEST를 덮지 못함. LATEST가 STALE을 삭제하지도 않음. 둘 다 VERIFIED 아님)  
Macro confirmed: 28/28 (v0.1.1)  
Macro candidate: 36/36 (v0.1.4, 미승격)  
Investment System E2E: NOT RUN

Technical 혼동 방지  
최신으로 인용할 숫자 = 159/159 RECORDED STRUCTURAL FREEZE.  
69/69는 역사 기록이며 현재 권한 숫자가 아니다.  
실제 PIT 실증과 Forward Validation은 159/159와 별도 단계이며 미완료.

3. Document Status Rules  
OFFICIAL/BASELINE: 사용자 또는 원 개발 흐름에서 공식 기준으로 확정된 문서.  
LATEST: 현재 가장 최근 확인 상태를 반영한 저장용 기록.  
PROVISIONAL: 설계는 진행됐지만 calibration/validation 전이라 공식값으로 고정하지 않는 항목.  
HISTORY: 과거 설계·결정과 변경 이유를 보존하는 문서.  
ARCHIVE: 최신 기준에 의해 대체됐지만 삭제하지 않는 구버전.  
RECORDED vs VERIFIED: Drive 문서의 PASS 숫자는 RECORDED. 원본 패키지·로그로 재실행하기 전에는 VERIFIED로 표시하지 않는다.

4. QGV System  
Primary integrated baseline: QGV System · Integrated Specification v1.7.  
Supporting contracts: Common Schema & API Contract v1.0.  
QGV Analysis · Specification v1.7.6 DESIGN FROZEN.  
QGV Simulation · Specification v1.0.  
QGV Portfolio · Specification v1.1.  
QGV Leaderboard · Specification v1.0.  
QGV Track Record · Specification v1.0.  
QGV System · Module Map v1.7.  
Core Implementation Plan은 구현계획 기록이며 Integrated Specification보다 상위 사양이 아니다.  
QGV Analysis 모듈 상세 freeze는 v1.7.6이 우선이다. Integrated Spec의 Q7 라벨(Capital Allocation)과 v1.7.6 Q7(Management Quality)은 CONFLICT로 유지한다.

5. Technical Analysis  
LATEST: Technical Analysis System · Latest Status Update 2026-09-22.  
HISTORY/CONSOLIDATED: Consolidated Record v0.1 · Decision History v0.1.  
최신 권한: STRUCTURAL FREEZE + 159/159 PASS 기록 (RECORDED).  
Project Index의 69/69 · Phase 4 서술은 STALE.  
실제 PIT 실증 / Forward Validation은 미완료이며 패키지 확보 전 착수하지 않는다.

6. Macro  
LATEST FILE: Macro System · Latest Consolidated Record v0.1.4 Candidate.  
CONFIRMED: v0.1.1, offline regression 28/28 PASS (RECORDED).  
CANDIDATE (not promoted): v0.1.4, 문서 기록 36/36 PASS (RECORDED).  
실데이터 API, 패키지 integration, full E2E, Forward Validation은 완료 표시 금지.

7. Investment System  
LATEST INTEGRATION: Latest Integration Record v1.2 PROVISIONAL.  
BASE ARCHITECTURE: Architecture v1.0.  
v1.2 OM/TM/MM/RM, Deadband, staged entry는 PROVISIONAL.

8. Cross-System Boundary  
QGV Raw Fundamental Snapshot은 Technical/Macro가 직접 수정하지 않는다.  
Technical과 Macro는 각각 가격/실행 및 거시 Context를 제공한다.  
최종 Target Weight와 Order는 상위 Investment System에서 한 번만 결정한다.  
-20% Drawdown은 자동매수 조건이 아니라 Re-check Trigger다.

9. Validation Boundary  
통과한 하위 모듈 테스트를 전체 시스템 검증 완료로 확대하지 않는다.  
Historical Backtest, Out-of-Sample, Forward Validation을 구분한다.  
Artifact Recovery BLOCKED 동안 Full E2E / PIT 실증 / OOS / Calibration / Forward Validation을 시작하지 않는다.  
PIT를 강제하고 당시 판단 Snapshot을 사후 결과로 덮어쓰지 않는다.

10. Current Storage Completion  
QGV: 핵심 Specification/Schema/Module 문서 저장됨. 실행 패키지 Missing.  
Technical: Consolidated/Decision/Latest Status 저장됨. 패키지 Missing.  
Macro: Latest Consolidated Record 저장됨 (confirmed + candidate in one file). 패키지 Missing.  
Investment System: Architecture + Latest Integration 저장됨. 통합 패키지 Missing.  
Artifact Inventory 2026-09-22: SSoT ZIP = 마크다운 21개.  
Missing Artifact Register 2026-09-22: Recovery BLOCKED. Code Present 0 / Reproducible 0 / VERIFIED 0.  
Contract Conflict Register 2026-09-22: C-01~C-16. C-01/C-03/C-08/C-16 OPEN.  
Module Progress Ledger 2026-09-23: 축 A 설계 / B RECORDED / C Code / D VERIFIED / E 실증. C=D=E=0.  
남은 정리: 폴더 중복/구버전 분류, Version History/Release Index, Work 산출물의 Drive 이관.

11. QGV Latest Update · 2026-09-22  
QGV pre-validation design is 100% complete and PRE-VALIDATION FREEZE. Design milestone only; empirical effectiveness unvalidated.  
Simulation local line v0.6.8 103/103 = RECORDED, package missing.  
NVDA PIT pilot은 명세 기록이나 데이터셋이 SSoT에 없음.  
메인 remaining work는 새 architecture가 아니다. 원본 Artifact 확보 → 재실행 → 그 다음 empirical calibration/validation.  
CALIBRATION_PENDING: numerical thresholds, peer-distribution, persistence, type-specific Q/G/V matrices, V reconciliation weights.  
증거 없으면 null/BLOCKED를 유지한다.

12. Update Rule  
새 개발 대화 결과가 들어오면: 원 개발 결과 확인 → 기존 최신본과 비교 → 확정/미확정 구분 → 해당 폴더에 저장 → Master Status Index 갱신.  
이 저장 허브에서 새로운 기능이나 수치를 임의로 공식화하지 않는다.  
Artifact Recovery를 같은 Drive 스냅샷에서 반복하지 않는다.

13. Update · 2026-09-23 · NEW IMPLEMENTATION evidence (Claude)
Original Recovery: BLOCKED (unchanged). NEW IMPLEMENTATION investment_system_impl-v0.2.0 present.
Validation ladder (NEW IMPLEMENTATION): Code Present YES · Reproducible YES (fresh sandbox, 123/123 shim) · SYNTHETIC VERIFIED YES · Integrated E2E synthetic only · REAL-DATA VERIFIED NO · Full PIT NO · OOS NO · Calibration NO · Forward NO.
Universe: Official = DECISION_REQUIRED (C-18). Candidates A (S&P history) / B (mcap top-N) implemented as RESEARCH only.
500-scale: SYNTHETIC in-process benchmark run; live network wall-clock not run.
Current handoff authority: Investment-System1 · CURRENT_HANDOFF.

14. Update · 2026-09-23 round 4 · C-18 RESOLVED (Claude, per explicit user decision)
Official Default Universe = US Market-Cap Top 500, PIT (as-of shares x as-of price; current roster never applied backward). Decided by the user, not inferred. Implementation: universe.sources.official_mcap500_snapshot (the one sanctioned OFFICIAL constructor) + official_mcap500_snapshot_from_store (fed from the ingestion/RawDatasetStore built round 3).
S&P 500 interval-file code kept as Benchmark/Research only (UniverseKind.SP500_HISTORY_CANDIDATE) — not deleted, not Official.
Caveat: Official status requires a complete US-listed-filer PIT candidate pool; this hub has run the constructor only on synthetic pools (138 SYNTHETIC VERIFIED). No real Official Top-500 snapshot has been produced yet — REAL-DATA VERIFIED remains 0, unchanged by this decision.

---
Update 2026-09-23 · OpenAI relay round 5
NEW IMPLEMENTATION evidence supersedes the old hub-only “VERIFIED=0” statement for the implementation line only; it does NOT recover or verify missing ORIGINAL packages.
- investment_system_impl-v0.2.0: Code Present YES; Reproducible YES; 140 SYNTHETIC VERIFIED after round-5 regression.
- REAL-DATA VERIFIED: NO. Full PIT / OOS / Calibration / Forward: NO.
- C-18: RESOLVED — Official Default Universe US Market-Cap Top 500 PIT; S&P retained Benchmark/Research.
- Live raw ingestion: BLOCKED by current container outbound DNS/HTTP. Actual runner 0/4 on SEC/Yahoo; see Evidence Register round 5.
- Ingestion provenance hardening: repeated intentional refreshes now archive prior raw bytes+manifest; default runner remains idempotent.
Original Recovery status remains BLOCKED and all legacy module PASS counts remain RECORDED unless separately reproduced from their original artifacts.

## Current overlay — 2026-09-23 16:49 KST / OpenAI relay round 6
This overlay supersedes stale recovery-era counts above where they conflict with current implementation evidence; historical text is retained for provenance.
- Implementation baseline: **140/140 VERIFIED** via mini_pytest shim.
- C-18: RESOLVED; Official Default Universe = US Market-Cap Top 500 PIT.
- Validation: Code Present YES / Reproducible YES / SYNTHETIC VERIFIED YES / Integrated E2E synthetic only / REAL-DATA VERIFIED NO / Full PIT NO / OOS NO / Calibration NO / Forward Validation NO.
- C-20: BLOCKED by container DNS/outbound HTTPS; existing real ingestion runner attempted and returned 0/4 successful.
- Next priority after resolution: real ingestion → complete PIT candidate pool → official Top-500 snapshot from store → real single_as_of → >=3-date walk-forward → actual 500-company network-inclusive benchmark.

15. Update · 2026-09-24 · Claude (new session, adopted latest SSoT) — Promotion Gate v2
Baseline reproduced: 150/150 (one test-runner-shim fix, not a code regression; see
CHANGELOG). Full suite after this round's additions: 162/162.
Promotion Gate extended with two independent gates: Universe Completeness Gate (sizes the
whole investable universe against a dated external benchmark, never sets
candidate_pool_complete alone) and Top-500 Sufficiency Gate (passes only with a clean,
dated, PIT large-cap reference showing no missing/unranked large-cap name -- an
independent, weaker-but-sufficient path to Official promotion). build_promotion_gate_v2
composes: base gate numeric/eligibility checks AND (completeness OR sufficiency).
Real (non-synthetic) evidence this round: WFE December 2024 exchange-listing counts
(NYSE 2,132 + Nasdaq-US 3,289; reports/gate_evidence/exchange_reference_wfe_2024-12-31.json),
run against the real 598-companyfacts/297-rankable audit -- Universe Completeness Gate
correctly FAILS (17.6% coverage). Top-500 Sufficiency Gate correctly FAILS (no dated
large-cap reference obtained this round -- C-22).
CRITICAL: RawDatasetStore blobs backing the 297-rankable state are absent from the
delivered ZIP (C-21) -- only run-log summaries and the 598-identity map survived. Coverage
expansion beyond identity-level work is BLOCKED until either the blobs are re-attached or
a network-enabled re-ingest runs.
Official Top-500: still NOT justified. REAL-DATA VERIFIED still NO. C-18 (Official
Default Universe = US Market-Cap Top 500 PIT) remains RESOLVED and was not revisited.

16. Update · 2026-09-24 (continued) · Claude — candidate hygiene finding, network re-exhausted
Network re-probed this session: still fully blocked (bash_tool, pip, and web_fetch's one
plausible route to the fja05680 CSV all failed for different reasons -- see Conflict
Register C-20/C-22 exhausted-attempts log). No further data collection possible this
session without fabrication, which was avoided throughout.
New offline finding: 185/598 (31%) of the current candidate pool matches a preferred-share
or foreign-OTC-ADR ticker shape (tools/audit_candidate_hygiene.py, heuristic/advisory only,
not auto-applied -- C-23). Recommends filtering these before further ingestion to conserve
API budget, once verified against real security-type data.
Full suite: 166/166. No promotion this session. REAL-DATA VERIFIED still NO.

17. Update · 2026-09-25 · Claude — C-22 core blocker resolved, real Sufficiency Gate run
A materially different route (URL-encoded Wikipedia article fetch) succeeded where prior
attempts (plain-URL Wikipedia, raw.githubusercontent.com, pip) had failed. Mechanically (code,
not manual reading) reconstructed real, dated S&P 500 membership as of 2024-12-31 (503 names,
18/19 independent spot-checks correct, 1 disclosed discrepancy). Cross-referenced against the
real 598-name pool: 282 real S&P 500 constituents entirely missing (priority fetch plan with
CIKs saved for the next network round). Ran the real Top-500 Sufficiency Gate against this
reference for the first time -- correctly FAILS (missing large caps). Promotion Gate v2 still
FAILS overall (base numeric gate also fails, 297 < 500 rankable).
C-23: 2 sample flagged tickers real-verified (1 primary SEC source, 1 secondary); the OTC-ADR
Y-suffix heuristic corroborated by an authoritative Schwab source. Still advisory only.
173/173 tests. No promotion. REAL-DATA VERIFIED still NO. C-21 (missing store blobs) and C-20
(network blocked, reconfirmed) remain the two blockers to actually passing any gate.

18. Update · 2026-09-25 round 2 · Claude
C-21 re-attempted per instruction (recover-or-reingest first): no recoverable store found;
network re-confirmed blocked; a new web_search+web_fetch angle for SEC's JSON API specifically
was tried and does not work (API responses aren't indexed as fetchable documents, unlike the
Wikipedia HTML page that unblocked C-22). C-21 remains the sole blocker to using the real
282-name priority plan.
AMTM discrepancy from the prior round resolved as a spot-check reading error, not a
reconstruction defect (19/19 now, corrected from 18/19). 4 more CIKs resolved (257/282 now
ready). No change to rankable/gates: 297 rankable, Universe Completeness FAIL, Top-500
Sufficiency FAIL (still 282 missing large caps), Promotion Gate v2 FAIL. 173/173 tests
(unchanged, no code this round). REAL-DATA VERIFIED still NO.

19. Update · 2026-09-25 round 3 · Claude
C-21 reconfirmed BLOCKED per a single fresh probe; no new workaround forced, no data
fabricated, per explicit instruction. No change to rankable (297), #500 cutoff (not
computable), Universe Completeness (FAIL), Top-500 Sufficiency (FAIL, 282 missing), or
Promotion Gate v2 (FAIL). 173/173 tests. REAL-DATA VERIFIED still NO. The full ingest ->
evaluate_reference_coverage -> gate pipeline this round's instruction requested is ready to
run exactly as specified the moment a network-enabled runner is available.
