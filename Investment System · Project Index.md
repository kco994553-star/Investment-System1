Investment System · Project Index

Purpose  
통합 투자 연구·검증 시스템의 공식 프로젝트 인덱스이자 Work 전환 기준 문서.

System Architecture  
Investment System  
→ QGV System (Fundamental Analysis / 기본적 분석)  
   → QGV Analysis  
   → QGV Simulation  
   → QGV Portfolio  
   → Leaderboard  
   → Track Record  
→ Technical Analysis System (기술적 분석)  
→ Macro System (매크로)

Integration Flow  
QGV Snapshot + Technical Snapshot + Macro Snapshot  
→ Gate / Integration  
→ Portfolio & Risk  
→ Target Weight  
→ Order / Execution  
→ Track Record  
→ Backtest / Out-of-Sample / Forward Validation

Current Baselines · 2026-09-22  
QGV software development line: v1.7  
QGV Analysis module: v1.7.6 DESIGN FROZEN  
QGV scoring reference: Standard v1.5 balanced  
Official Portfolio: v1.1 · 2026-09-14  
Technical Analysis: 핵심 설계·구조 구현 완료 / Real PIT Validation v0.6 STRUCTURAL FREEZE · latest recorded structural tests 159/159 PASS (Master Status / Latest Status 우선). Project Index에 남아 있던 69/69 · Phase 4 서술은 stale.  
Macro System: latest confirmed v0.1.1 · offline regression 28/28 PASS. v0.1.4 Candidate는 미승격.  
Investment System: 핵심 Architecture 설계 완료 / Freeze Candidate  
Latest Integration: v1.2 PROVISIONAL

Validation Boundary  
Technical 159/159 PASS와 Macro 28/28 PASS는 각각 모듈 수준의 확인 기록(RECORDED)이다.  
전체 Investment System의 실제 데이터 E2E 검증 완료를 의미하지 않는다.  
실데이터 Provider/API, 세 시스템 package integration, real-time market data, brokerage execution, 장기 Forward Validation은 별도 검증 대상이다.  
2026-09-22 SSoT 스냅샷에는 실행 패키지가 없어 위 PASS를 VERIFIED로 승격하지 않는다.

Current Phase  
신규 기능 설계를 계속 확장하는 단계는 종료한다.  
Artifact Recovery: BLOCKED (2026-09-22). Code Present 0 / Reproducible 0 / VERIFIED 0.  
다음 AI의 첫 작업은 새 설계가 아니라 실제 원본 Artifact 확보다.  
이후 우선순위:  
원 개발 대화/Work에서 산출물 회수 → Drive SSoT 이관 → 무결성 확인 → 기존 테스트 재실행(RECORDED/VERIFIED 분리) → 그 다음 실제 데이터 연결 → E2E → PIT → OOS → Calibration → Forward Validation.  
패키지가 오기 전에 Full E2E / PIT 실증 / OOS / Calibration / Forward Validation을 시작하지 않는다.  
PROVISIONAL 계수와 임계값은 Calibration/Validation 전까지 공식 상수로 승격하지 않는다.

Work Handoff Policy  
실제 구현·실데이터 연결·통합 테스트·E2E 검증은 ChatGPT Work를 주 실행공간으로 사용한다.  
Work는 기존 설계를 처음부터 재설계하지 않고 현재 Freeze Candidate를 기준선으로 인수한다.  
Work에서 확정된 변경은 검증 후 Google Drive의 해당 모듈 폴더와 Master Status Index에 반영한다.

Repository Policy  
Google Drive의 Investment-System1을 프로젝트 Source of Record로 사용한다.  
공식 Specification, Latest Status, Decision History, Validation Record, Release Artifact를 보존한다.  
버전이 있는 공식 문서가 비공식 대화 메모보다 우선한다.  
이 저장 허브에서 새로운 기능이나 수치를 임의로 공식화하지 않는다.

Update · QGV Portfolio  
QGV Portfolio 핵심 설계 완료. Design 100% / FROZEN.  
Current implementation baseline: v3.0 RC26.  
Regression: 366/366 PASS (RECORDED; package missing from 2026-09-22 SSoT snapshot).  
Next work: 패키지 확보 후 Full Q/G/V integration regression → real-data validation → Frontend/API integration → Forward Validation. 새로운 핵심 설계 추가는 보류하고 검증을 우선한다.

Update · SSoT inventory 2026-09-22  
Artifact Inventory와 Contract Conflict Register가 추가되었다.  
Missing Artifact Register: Recovery BLOCKED. C-01/C-03/C-08/C-16 OPEN.  
다음 작업의 전제는 원본 회수이며 설계 확장이 아니다.

Update · Module Progress Ledger 2026-09-23  
모듈별 진행률은 `Investment-System1 · Module Progress Ledger 2026-09-23`을 본다.  
설계 Freeze와 이 허브 재실행(VERIFIED=0)을 한 숫자로 합치지 않는다.

Update · Track separation 2026-09-27

- Track A: REAL-DATA Main Track. All three historical Official dates are SUSPENDED after the share/price-unit audit (C-41).
  C-40 dated-identity replay is fixed; 500-name RESEARCH diagnostics pass. D3-P CA-UNIT-v1.0 and final Official reruns remain pending.
  Latest Track A detail: `Investment-System1 · TRACK_A_REAL_DATA_STATUS.md`. Local update; remote upload blocked by 403.
- Track B: Personal Investment Layer. Architecture FROZEN; P0 Common Contracts IMPLEMENTED+FROZEN; P1+ NOT STARTED.
- Track C: Experiment & Validation Layer, `EVL_SPEC_v0.1`. DESIGN FROZEN / IMPLEMENTATION NOT STARTED. It validates
  integrated Aggressive/Balanced/Defensive candidates and owns their Official promotion after Track A baseline Freeze.
- Ownership: Track A data/Universe/provenance → Track C experiment/validation/promotion → Track B Official-profile
  consumption. Upstream QGV/Technical/Macro definitions and core scores are not redesigned.
- Tax: Official tracks remain Pre-Tax; tax functionality is OUT_OF_SCOPE.

Update · RIG / News Architecture v0.1 · 2026-09-27

- SSoT: `Investment-System1 · RIG News Architecture v0.1.md`, contract `RIG_NEWS_ARCH_v0.1`.
- Status: DESIGN FROZEN / IMPLEMENTATION NOT STARTED; P0–P5 NOT_STARTED.
- Boundary: additive News/Relationship domain and News↔Network views. Existing DataEvent/PIT/identity/provenance and
  Summary→Evidence→Detail contracts are reused; QGV/Technical/Macro scores are not mutated.
- Track preservation: Track A REAL-DATA priority unchanged; Track B P0 stays frozen; Track C EVL stays frozen and
  unimplemented. RIG is not a new scoring track and no runtime/UI/store was added by this registration.

Update · C-39 shared identity contract · 2026-09-27 16:02 KST

- C-39 RESOLVED: the documented common `Issuer → Security → Listing` runtime contract is restored in
  `contracts/global_universe.py`, with separate Analysis/Network/News contexts and fail-closed FX/eligibility PIT gates.
- Six focused regressions and the full 308/308 suite pass. Track B's frozen private security contract was neither
  imported nor changed. This removes the identity-contract blocker for RIG P0; RIG itself remains unimplemented.


## Track A final Freeze record — 2026-09-27T20:50:49.316653+09:00

Track A REAL-DATA Baseline **FROZEN** in local commit/package; canonical GitHub upload is still blocked (prior integration HTTP403). Validated source `682bbae1687d237f72c3f2266913b8bf61f1ff0b`. C-40/C-41 resolved; CA-UNIT-v1.0 approved; original20+3 D3-C cases audited. Corrected Gate and exact Official consistency pass for 2024-06-30/09-30/12-31; 3-date Walk-Forward equals singles; network-inclusive500 benchmark completed; raw6830 integrity and regression396/396 pass. No new D3-P. Baseline freeze does not promote PROVISIONAL_RESEARCH calibration or modify other tracks. Final machine record: `implementation/reports/gate_evidence/track_a_freeze_readiness_2026-09-27.json`. Work stopped as instructed. Earlier Track A blocked entries are historical and superseded by this record.
