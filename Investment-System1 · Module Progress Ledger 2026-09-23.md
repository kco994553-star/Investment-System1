Investment-System1 · Module Progress Ledger  
기준: 2026-09-23 08:42 KST  
권한: 아래 %는 새 추정이 아니다. 기존 Official/Latest 문서의 동결 문구와 Evidence Ledger를 분해한 값이다.  
규칙: Design % ≠ Verified %. RECORDED PASS를 생산 완료로 읽지 않는다. 원본 패키지가 없는 축은 0%로 둔다.

1. 읽는 방법

축 A 설계 — 명세가 DESIGN/STRUCTURAL FREEZE라고 적은 범위.  
축 B 기록 회귀 — Drive/명세에 적힌 테스트 PASS. 패키지 부재로 RECORDED.  
축 C 이 허브 코드 — 현재 SSoT에 실행 패키지가 있으면 100, 없으면 0.  
축 D 이 허브 재실행 — VERIFIED. 현재 전 모듈 0.  
축 E 실증/운용 — PIT 실증, OOS, Calibration, Forward, Live, 실데이터 E2E. 패키지 전 착수 금지.

공식 진행률로 인용할 때 축을 밝힌다. 단일 숫자로 합치지 않으면 오해가 줄어든다.

2. 모듈별 현황

2.1 QGV Analysis  
버전: Specification v1.7.6 DESIGN FROZEN  
축 A 설계: 100% FROZEN  
공식 Stage Gate: 2/7 = 28.6% (Stage 0/1 PASS. Stage 2 Real Data부터 실행 남음)  
축 B 기록 회귀: Python 299 PASS · JS 27 PASS · Browser E2E NOT RUN  
축 C 코드: 0% MISSING  
축 D 재실행: 0%  
축 E 실증: 0% (V weights = VALIDATION_SELECTED, Calibration PENDING)  
막힘: 원본 freeze suite, 실데이터, NVDA PIT 데이터셋 없음. C-03 Q7 라벨 CONFLICT.

2.2 QGV Simulation  
버전: Spec v1.0 · 구현선 v0.6.8 local  
축 A 설계: PRE-VALIDATION FREEZE (추가 기능 설계 불필요라고 문서가 적음. 100% 설계 완료로 승격하되 empirical은 별도)  
축 B 기록 회귀: 103/103 PASS (local v0.6.8, RECORDED)  
축 C 코드: 0% MISSING  
축 D 재실행: 0%  
축 E 실증: 문서상 real-data validation started, effectiveness NOT VALIDATED. 이 허브 데이터셋 없음 → 실증 0%  
막힘: v0.6.8 패키지, PIT 데이터.

2.3 QGV Portfolio  
버전: Official baseline v1.1 · 2026-09-14 / 구현선 v3.0 RC26  
축 A 설계: 100% FROZEN  
축 B 기록 회귀: 366/366 PASS (RC26, RECORDED)  
축 C 코드: 0% MISSING  
축 D 재실행: 0%  
축 E 실증: 0% (문서: E2E PASS는 연결 무결성이며 투자모델 유효성이 아님. 실데이터 Validation 남음)  
막힘: RC26 패키지. C-07 holding.company_id GAP. C-08 TEL 식별자 OPEN.

2.4 QGV Leaderboard  
버전: Spec v1.0 DESIGN FREEZE  
축 A 설계: 100% DESIGN FREEZE  
축 B 기록 회귀: Python 313/313 + 8 subtests · Frontend 12/12 · Standalone Build PASS (RECORDED). Browser E2E / Historical Data는 문서상 미완  
축 C 코드: 0% MISSING  
축 D 재실행: 0%  
축 E 실증: 0%  
막힘: freeze suite, Universe snapshot.

2.5 QGV Track Record  
버전: Spec v1.0  
축 A 설계: Spec PRESENT. Design 100% 동결 문구 없음 → 설계 문서화됨, Freeze 미선언  
축 B 기록 회귀: PASS 숫자 없음  
축 C 코드: 0% MISSING  
축 D 재실행: 0%  
축 E 실증: 0% (성과 창·시나리오 평가 실행 기록 없음)  
막힘: 구현 패키지와 Outcome 로그 전부 Missing.

2.6 Technical Analysis  
버전: Phase 6 + Real PIT Validation v0.6 STRUCTURAL FREEZE  
축 A 설계/구조: STRUCTURAL FREEZE (구조 구현 완료로 기록)  
축 B 기록 회귀: 159/159 PASS (LATEST, RECORDED). Index 69/69는 STALE이며 인용 금지  
축 C 코드: 0% MISSING  
축 D 재실행: 0%  
축 E 실증: 실제 PIT Walk-Forward / Forward Validation 미완료 = 0%  
막힘: Technical v0.6 패키지, 실시간 데이터, QGV/Macro 실패키지 연결.

2.7 Macro System  
버전: CONFIRMED v0.1.1. 같은 파일의 v0.1.4 Candidate는 미승격 (C-01 OPEN)  
축 A 설계: Confirmed 기록은 v0.1.1 기준선. Candidate 문서의 “설계 약 98% / 개발 2/6=33.3%”는 CANDIDATE이며 CONFIRMED가 아님  
축 B 기록 회귀: confirmed 28/28 PASS. candidate 36/36 PASS는 미승격  
축 C 코드: 0% MISSING  
축 D 재실행: 0%  
축 E 실증: 외부 API 실응답 / 패키지 통합 / Forward = 0%  
막힘: v0.1.1 패키지. Candidate 승격 금지.

2.8 Investment System (통합)  
버전: Architecture v1.0 Freeze Candidate + Integration v1.2 PROVISIONAL  
축 A 설계: v1.1 흐름 정의 완료. v1.2 OM/TM/MM/RM·Deadband·단계진입은 PROVISIONAL  
축 B 기록 회귀: 통합 E2E 기록 없음  
축 C 코드: 0% MISSING  
축 D 재실행: 0%  
축 E 실증: Full E2E / 실거래 / Forward = NOT RUN = 0%  
막힘: 하위 3시스템 패키지 전부 부재. C-16 Work↔Drive 단절.

3. 시스템 합계 (허브 기준)

Spec Present: 8 / 8  
Design Freeze 선언: Analysis, Portfolio, Leaderboard, Simulation(pre-val), Technical(structural). Track Record는 Spec only. Macro confirmed는 v0.1.1. Integration은 PROVISIONAL  
Code Present: 0 / 8  
Reproducible: 0 / 8  
VERIFIED: 0 / 8  
discrepancies: 0 (비교 대상 패키지 없음)

QGV Analysis 공식 실행 Gate: 28.6% (2/7)  
Investment System 생산 준비: 0% (패키지·E2E·Forward 없음)

4. 검증 사다리 (전체)

Unit/모듈 회귀: RECORDED only, VERIFIED 0  
Integration / Browser E2E: NOT RUN 또는 패키지 부재  
Historical Backtest: 이 허브에서 NOT RUN  
PIT 실증: 구조 freeze만, 실증 0  
OOS: NOT RUN  
Calibration: PENDING  
Forward Validation: NOT RUN  
Live Operation: NOT RUN

5. 다음 작업이 진행률을 올리는 조건

축 C/D가 올라가려면 원본 패키지가 이 허브에 들어와야 한다.  
축 E가 올라가려면 패키지 VERIFIED 이후 사다리를 순서대로 탄다.  
설계 %를 더 올려 진행한 것처럼 보이지 않는다.

6. Update · 2026-09-23 08:54 · NEW IMPLEMENTATION axis

축 F 신규구현 — original이 아니라 investment_system_impl-v0.1.0.
QGV Analysis / Simulation / Portfolio / Leaderboard / Track Record / Technical / Macro / Integration: 실행 코드 PRESENT (NEW).
SYNTHETIC VERIFIED tests: 19 passed.
축 C original code: 여전히 0.
축 D original verified: 여전히 0.
축 E real-data/forward: 여전히 0.
공식 Analysis Stage Gate 2/7=28.6% 불변 (실데이터 Stage 2 미착수).
