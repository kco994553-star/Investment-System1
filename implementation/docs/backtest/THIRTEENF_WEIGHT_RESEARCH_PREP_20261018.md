# 13F 가중치 연구 준비 — 자산 조사·대응표·설계 선택지

기준일: 2026-10-18. 상태: **조사·설계 준비만.** 코드 변경 없음. 성과·유사도 결과 없음. SEC 요청 없음.

기준 커밋: canonical `0eeb933a`(#299 병합). Track C 브랜치: `origin/feature/track-c-evl` `ff78c4f6`(merge-base `b8e39a21`, canonical에 없는 커밋 54개).

> **이 문서를 병합해도 13F-R1~13F-R16 권장안의 승인이 아니다.** 각 항목은 결정 후보로 남는다. BT-·AS-·MD- 항목의 상태도 바꾸지 않는다.

사용자 지시(2026-10-18) 요약:

- 13F 연구는 **가중치 학습 연구**다. 과거 공개 13F 보유와 비슷한 선택을 만드는 Q/G/V 축 가중치와 Q1…Q5·G1…G5·V1…V5 세부 요인 가중치를 찾는다.
- 찾은 가중치를 **다른 기간**에서 유사도와 투자 성과로 검증한다.
- 기관 관심도 슬라이더나 보유 조회가 아니다.
- 결과는 기관의 실제 기준 복원이 아니다. 공식 기본값을 자동으로 바꾸지 않는다.
- 근거: [PRODUCT_FRONTEND_REDESIGN_20261018.md](../PRODUCT_FRONTEND_REDESIGN_20261018.md) §0-3·§5·§12, [USER_DECISIONS_PENDING.md](../USER_DECISIONS_PENDING.md) "결정됨 — 2026-10-18" 3번.

경로 약어:

- `src/` = `implementation/src/investment_system/`
- `tests/` = `implementation/tests/`
- `TC:` = `origin/feature/track-c-evl` 브랜치의 같은 경로. 예: `TC:src/evl/splits.py:76`.
- 줄 번호는 위 기준 커밋 기준이다. [BACKTEST_RESEARCH_PLAN.md](BACKTEST_RESEARCH_PLAN.md)는 보존 스냅샷 S0 기준이라 일부 줄 번호가 다르다(예: `score_universe`).

## 목차

1. [자산 목록과 판정](#1-자산-목록과-판정)
2. [연구 필요 항목 대응표](#2-연구-필요-항목-대응표)
3. [설계 선택지 (수치 없음)](#3-설계-선택지-수치-없음)
4. [자료 공백과 결정 후보 13F-R1~R16](#4-자료-공백과-결정-후보-13f-r1r16)
5. [제약](#5-제약)
6. [조사 중 발견한 사실](#6-조사-중-발견한-사실)

---

## 1. 자산 목록과 판정

판정 기호:

- **재사용**: 고치지 않고 호출만 한다.
- **변경 이식**: 별도 연구 경로로 옮기고 정해진 부분만 바꾼다. 운영 파일은 고치지 않는다.
- **재사용 안 함**: 이 연구에 쓰지 않는다. 이유를 적는다.

시험 수는 `def test_` 개수다(매개변수화 사례는 따로 세지 않음). canonical의 Python 시험은 `.github/workflows/cockpit-pages.yml:25`가 `tests` 전체를 돌린다. Track C 시험은 브랜치 전용 워크플로(`TC:.github/workflows/track-c-evl-validation.yml`)에서만 돈다.

### 1-1. 운영 13F (canonical)

| # | 자산 | 위치 | 하는 일 | 시험 | PIT 처리 | 판정 | 이유 |
|---|---|---|---|---|---|---|---|
| T1 | 정보표 파서 | `src/providers/sec_13f.py:313` `parse_information_table`, `:35` `FilingMetadata`, `:274` `_aggregate`, `:288` `_comparison_reasons` | 13F XML 정보표를 행으로 읽는다. CUSIP·종류·SH/PRN·Put/Call·재량·otherManager 귀속을 보존한다. 같은 bucket만 합친다. 잘못된 행 하나면 전체 무효 | `tests/test_sec_13f.py` 39개(합성 XML). 정정 유형 검사 포함 | `:177-182`: 취득 시각 > as_of 또는 제출일 > as_of 날짜면 `NOT_AVAILABLE_AS_OF`. 제출 **날짜**만 본다. 접수 시각 없음 | **재사용** | 형식 검사와 bucket 규칙은 연구에도 그대로 맞다. 단 as_of 검사는 "취득 시각"과 "공개 시각"을 한 값으로 본다. 과거 결정 시각으로 호출하면 2026 취득본이 모두 NA가 된다. 연구는 as_of = 실제 취득 시각으로 파싱만 하고, 공개 시각은 `research/pit_filings.public_time`으로 따로 판정한다(§6-1) |
| T2 | 두 분기 비교 | `src/providers/sec_13f.py:389` `compare_quarters`, `:366` `_eligible_capture` | 연속 분기의 보고 수량 변화 NEW/ADD/REDUCE/EXIT | 같은 파일 | 두 입력의 as_of 동일 요구(`:401-402`) | **재사용(선택)** | 가중치 학습의 목표는 분기말 보유 집합이다. 변화 목록은 기관 회전율 진단에만 쓴다. EXIT는 실제 매도 확정이 아니라는 표시(`:21`)를 유지한다 |
| T3 | 기관 확인·최신 두 분기 수집 | `src/providers/sec_13f_managers.py:149` `verify_manager`, `:182` `select_quarters`, `:370` `collect_managers`, `:123` `_filings` | 설정된 CIK의 이름을 정확히 맞추고 최신 13F-HR 두 분기를 받는다 | `tests/test_sec_13f_managers.py` 12개. 정정 사례 시험 0개 | 수집 시각 기준 cutoff(`:171-175`). 최근 200일 안 13F-HR 요구(`:40`) | **재사용 안 함**(패널 수집) | "최신 두 분기" 운영 논리다. `_filings`는 `filings.recent`만 읽는다(`:124`). 과거 페이지(`filings.files`)를 읽지 않는다. 정정이 있는 분기는 `lineage_resolved=False`가 되어 비교에서 빠진다(`:199`) |
| T4 | 표지 파서·단일 제출 수집 | `src/providers/sec_13f_managers.py:249` `parse_cover`, `:310` `capture_filing`, `:42` `DOLLAR_VALUES_FROM` | 표지의 보고 유형·정정 유형·항목 수·합계·비공개 생략·otherManager를 읽는다. 금액 단위를 **제출일**로 정한다(`:345`) | 위 12개 중 일부 | 제출일만 | **변경 이식** | 표지 파서와 단위 규칙은 그대로 맞다. 그러나 `capture_filing`은 원본만 결속한다(`:339-341`, `is_amendment is False`). 정정본(13F-HR/A)을 받을 수 없다. 정보표 XML이 정확히 1개라는 가정(`:326-328`)도 과거 제출에서 확인하지 않았다 |
| T5 | 공개 보유 투영 | `src/product/thirteenf_details.py:24` `project_details`, `:12` `SCOPE` | 완전·비교 가능한 보고의 매수 SH·옵션 제외 행만 원 단위로 투영 | `tests/test_thirteenf_enrichment.py` 7개 + 브라우저 시험 | 제출일만 | **재사용(정의만)** | "적격 보유 = 매수 SH, Put/Call 없음, 수량 > 0"(`:28`) 정의를 연구 표적 정의의 기준으로 쓴다. 공개 producer로는 쓰지 않는다 |
| T6 | 식별·플레이북 참고 | `src/product/thirteenf_quarter.py:32` `cusip_valid`, `:42` `isin_valid`, `:57` `cusip_from_isin`, `:64` `target_securities`, `:19` `EATON_EVIDENCE`, `:126` `playbook_evidence` | CUSIP·ISIN 검사 숫자. TARGET 19개를 현재 카탈로그 ISIN으로 CUSIP에 잇는다 | `tests/test_thirteenf_enrichment.py`, node 시험 | 없음(현재 식별만) | 검사 함수 **재사용** / 대상 연결 **재사용 안 함** | `TARGET`(`:11-14`)은 2026 목록이다. 과거 대상 선택에 쓰면 미래 정보다(계획 §4-5 금지와 같은 원리). 현재 ISIN은 과거 CUSIP 식별의 근거가 아니다 |
| T7 | 운영 단계·배포 | `implementation/tools/sec_13f_managers.py:39` `build`, `.github/workflows/sec-daily-public-inputs.yml:131-135` | 매일 공개 `sec-13f-changes.json`을 다시 쓴다 | 위 시험 + Pages 가드 | 수집 시각 | **재사용 안 함** | 공개 산출물 단계다. 연구 패널은 비공개 별도 작업이다. 공개 파일 크기 한도(`:28`)도 맞지 않는다 |
| T8 | 기관 설정 | `src/config/manager_styles_v0.json`(10기관·8유형), `src/config/manager_styles.py:41` `validate_manager_styles` | 추적 기관과 유형 라벨 | `tests/test_sec_13f_managers.py:130` | 없음 | **재사용(라벨 붙여서만)** | 2026년에 고른 명단이다. 과거 연구 기관 명단으로 그대로 쓰면 선택 편향이다(13F-R1) |
| T9 | 화면 | `src/product/web_assets/thirteenf-quarter.js`, `app.js:583` `thirteenf()`, `app.js:259`("Investor-QGV 미연결") | S16 조회 화면 | node·브라우저 시험 | — | **재사용 안 함**(연구 화면) | 조회 화면은 유지한다. 연구 화면 흐름(기관·기간 선택 → 연결률 → … → 프로필 저장)은 새 Lab 화면이다 |
| T10 | 규칙 문서 | [SEC_13F_REPORTED_CHANGES.md](../fundamentals_sources/SEC_13F_REPORTED_CHANGES.md), [LANE_E_20261013.md](../thirteenf/LANE_E_20261013.md), PLAYBOOK_V1 §13-8 | 단위·정정(RESTATEMENT/NEW_HOLDINGS)·EXIT 의미·공개 경계 | — | — | **재사용** | 연구 표적 규칙의 근거다. §13-8 "13F는 점수를 바꾸지 않음"은 운영 규칙이다. 이 연구는 연구 프로필만 만들고 운영 점수를 바꾸지 않으므로 충돌하지 않는다 |
| T11 | 식별자 보조 | `src/providers/sec_classification_inputs.py:58` `security_identifiers`, `implementation/tools/fetch_nport_reference.py` | US ISIN에서 CUSIP 파생. N-PORT 보유 목록(CUSIP·ISIN·이름 포함)으로 PIT 대형주 참고 목록을 만든 Track A 도구 | 각 도구 시험 | N-PORT 보고일 기준 | 함수 **재사용** / N-PORT 경로 **변경 이식 후보** | N-PORT 보유 행은 시점이 있는 CUSIP↔ISIN↔이름 증거가 될 수 있다(13F-R6·R9). `tools/nport_reported_prices.py`는 가격 예외 도구라 이 연구에 쓰지 않는다 |

### 1-2. PIT 재무·QGV 계산 (canonical)

| # | 자산 | 위치 | 하는 일 | 시험 | PIT 처리 | 판정 | 이유 |
|---|---|---|---|---|---|---|---|
| P1 | PIT 공시 어댑터 | `src/research/pit_filings.py:318` `public_time`, `:403` `pit_filter_companyfacts`, `:479` `resolve_as_of`, `:530` `as_filed_sic`, `:571` `qg_raw_metrics_as_of`, `:592` `cross_section_as_of`, `:235` `signal_decision_time` | 사실 하나의 공개 시각을 정한다. 접수 시각이 있으면 그 시각, 날짜만 있으면 다음 세션 개장. 정정은 자기 공개 시각부터 보인다. `frame` 태그 제거. as-filed SIC는 FSDS `sub`에서 | `tests/test_research_pit_filings.py` 30개(S1~S4, 달력, 조기 폐장, 정정, 운영 모듈 비의존 검사 `:506`, `:523`) | 엄격. filed 없으면 버리고 센다. 현재 SIC로 채우지 않는다. 모호한 시간대는 늦은 쪽(`conservative`) | **재사용** | `public_time`은 제출 날짜와 접수 시각만 받는 일반 함수다. 13F 제출(13F-HR, 13F-HR/A)의 공개 시각 판정에도 그대로 쓸 수 있다. `cross_section_as_of`는 과거 모집단이 없어 항상 `NEEDS_HISTORICAL_UNIVERSE`다(`:568`) |
| P2 | FSDS 표본 | [FSDS_SAMPLE_20261017.md](FSDS_SAMPLE_20261017.md), [BACKTEST_DATA_AUDIT.md](BACKTEST_DATA_AUDIT.md) D3·D10·8-1절 | `sub.sic` as-filed, `accepted` = 뉴욕 현지 시각(분 반올림) | 2015q4·2016q1 표본만 | — | **재사용(근거)** | 두 분기만 확인됐다. 다른 분기는 미검증이다 |
| P3 | v2 원지표 | `src/qgv/v2_factors.py:1298` `compute`, `:38` `CALC_VERSION` | companyfacts → Q·G 원지표·V 입력. `filed ≤ cutoff` | 기존 v2 시험 | cutoff 포함 비교 | **재사용** | P1이 호출한다. 연구가 직접 cutoff를 넘기지 않는다 |
| P4 | Q·G 단면 점수 | `src/qgv/v2_scoring.py:118` `score_rows`, `:26-29` 내부 비중, `:32-33` 최소 비교군·축 50% | 단면 백분위, Q·G 축 | 기존 시험 | 같은 calc_version 단면 | **재사용** | 요인 백분위는 가중치와 무관하다. 시점마다 한 번 계산하고 후보 가중치마다 다시 집계만 한다(계획 §5) |
| P5 | V·총점·관문 | `src/qgv/qgv_v2.py:20` `WEIGHTS`, `:28` `PRESETS`, `:71` `axis_score`, `:165` `composite_weights`, `:346` `score_universe` | V 요인, 축 결측 재정규화, 총점, 가치 함정 관문 | `tests/fixtures/qgv_v2_vectors_v1.json` 벡터 | 가격 입력 필요 | **재사용** + 동등성 기준 | 연구 어댑터는 임의 가중치 θ로 다시 집계한다. 같은 θ가 현행 값이면 `score_universe`와 완전히 같아야 한다(계획 S28과 같은 원리) |
| P6 | PIT 판정 개념 | `src/pit/resolver.py:21` `is_available`, `:34` `select_latest` | `available_at ≤ as_of` | 기존 시험 | — | **재사용(개념)** | 표시용 자료 시각 꼬리표에 쓴다 |
| P7 | 전진 원장 | `src/validation/forward_ledger.py:33` `START_DATE`, `:42` `HOLDOUT = 'UNCONFIRMED_NOT_USED'` | 전진 관측 | 기존 시험 | — | **재사용 안 함** | 섞지 않는다. 보호 상태를 바꾸지 않는다 |
| P8 | toy 백테스트 | `src/validation/backtest.py`, `src/validation/engine.py` | 장난감 하네스, 결측 수익 0 처리 | — | — | **재사용 안 함** | 계획 §7 판정과 같다 |
| P9 | v1 사실 선택 | `src/providers/sec_vintage.py` | filed 없으면 기간 종료일로 대신 | — | 부정확 | **재사용 안 함** | 계획 §7 판정과 같다 |
| P10 | 성과 지표 정의 | `src/qgv/virtual_trading_compare.py`, `src/qgv/report_benchmarks.py` | MDD·변동성·참여율 정의 | 기존 시험 | — | **재사용(정의)** | 성과 단계에서 계획 §11-3 정의와 함께 쓴다. 이 과제에서는 계산하지 않는다 |
| P11 | 모집단 역산 도구 | `implementation/tools/reconstruct_sp500_from_wikipedia.py` | 현재 구성 + 변경표 역산 | — | 2025 이후 사본만 | **재사용(조건부)** | 모집단 결정(BT-2) 뒤에만 쓴다 |

### 1-3. Track C (브랜치 `origin/feature/track-c-evl`, canonical 아님)

공통 사실:

- EVL 사양 v0.1은 canonical 루트 문서다(`Investment-System1 · Experiment & Validation Layer Specification v0.1.md` §2·§3·§10). 코드는 브랜치에만 있다.
- 브랜치는 오래된 기준(`b8e39a21`, 2026-09-30 무렵)에서 갈라졌다. 그대로 병합하면 큰 충돌과 검토 부담이 생긴다.
- 모든 시험은 합성 자료다. 실데이터 실행 기록은 없다.

| # | 자산 | 위치 | 하는 일 | 시험 | PIT 처리 | 판정 | 이유 |
|---|---|---|---|---|---|---|---|
| C0 | 실험 계약 | `TC:src/evl/contracts.py:76` `ExperimentSpec`, `:101` `TrialRecord`, `:29` `DatasetSplit`, `:47` `ParameterSpace`, `:59` `SearchBudget`, `:24` `HoldoutState`, `:119` `FreezeManifest` | 실험 식별·자료 해시·코드 해시·시드·탐색 공간·예산·분할 | `TC:tests/test_evl_c0.py` 4개 | 분할 순서 검사(`:39-43`) | **변경 이식** | 등록 항목이 13F 연구에 필요한 것과 같다. 단 `HoldoutState`는 이 연구에서 쓰지 않는다(§5) |
| C1 | 시도 원장 | `TC:src/evl/ledger.py:35` `TrialLedger`(`:75` append, `:83` 파일 잠금, `:99` verify), `TC:src/evl/experiments.py:32` `ExperimentLedger` | 덧붙이기 전용 시도 기록, 해시 검증 | `TC:tests/test_evl_c1.py` 14개 | — | **변경 이식** | 지시가 요구하는 "탐색 범위·제약·목적함수·시도 수 기록"에 바로 맞는다. 파일 잠금이 POSIX 전용이다. 저장 위치는 비공개 경로로 정해야 한다 |
| C2 | PIT 가드 | `TC:src/evl/pit.py:18` `PITGuard.enforce` | `available_at > decision_time`이면 실패 | `TC:tests/test_evl_c2.py`(일부) | 실패 즉시 중단 | **재사용 안 함**(중복) | P1이 더 엄격하고 canonical에 있다. 같은 일을 두 번 만들지 않는다 |
| C3 | 연 단위 분할 | `TC:src/evl/splits.py:76` `annual_splits`(학습 5년·검증 1년·OOS 1년, 롤링·확장), `:92` `SplitContract`, `:106` Holdout 진입 거부, `:116` 스트레스 cutoff, `:175` `split_samples` | 시간순 분할, 정답 공개 지평 기준 제거(purge) | `TC:tests/test_evl_c2.py` 11개 | 표본의 정답 공개 시각 검사 | **변경 이식** | 시간순 학습→검증→미사용 평가 구조가 그대로 필요하다. 바꿀 점: (1) 정답 지평 = 다음 13F 보유가 **공개되는 시각**까지 (2) `holdout_start` 인자는 보호 Holdout 지정처럼 읽힌다. 이 연구는 Holdout을 정하지 않는다. "연구 자료 끝 경계"로 이름과 뜻을 바꾸고 보호 구간과 겹치지 않는지만 검사한다(13F-R13) |
| C4 | 지표 | `TC:src/evl/metrics.py:126` `evaluate_metrics`, `:18` `METRIC_VERSION` | 수익 기간 → CAGR·MDD 등 | `TC:tests/test_evl_c3.py` 10개 | 평가 시각 이후 결과 차단 | **변경 이식**(성과 단계) | canonical 정의(P10)와 계획 §11-3 정의를 하나로 맞춘 뒤에 쓴다. 이 과제에서는 쓰지 않는다 |
| C5 | 전진 분할 실행기 | `TC:src/evl/walkforward.py:135` `run_fold`, `:67` `register_runner`, `:32` `LearningRow`, `:260` `run_annual` | 분할별 학습·평가 실행, 중단 복구 | `TC:tests/test_evl_c4.py` 8개 | 등록된 분할만 | **변경 이식** | 수익 기반 실행기다. 13F 단계 1은 "행동 유사도 채점기"가 필요하다(`TC:implementation/reports/investor_qgv_implementation_baseline.md` 같은 결론). 실행·복구·해시 구조만 가져온다 |
| C6 | 매개변수 바인딩 | `TC:src/evl/bindings.py:16` `BINDINGS`(cash_buffer·technical_lookback·deadband), `:21` 미해결 키 | v1 통합·기술·매크로 엔진에 연결 | `TC:tests/test_evl_c4_bindings.py` 9개 | — | **재사용 안 함** | QGV 가중치가 아니다. v1 엔진(`..integration.engine`, `..technical.engine`)에 묶여 있다. 현재 v2와 다르다 |
| C7 | 제약 격자 탐색 | `TC:src/evl/search.py:24` `register_search`, `:80` `run_search`, `:21` `KEYS` | 사전 등록 격자, 단계별 선별, OOS 입력 없음 | `TC:tests/test_evl_c5.py` 7개 | 개발 구간만 | **변경 이식**(구조만) | 승인 정책 TC-D3P-002가 cash_buffer·technical_lookback만 허용한다(`:3`). QGV 가중치 탐색은 별도 추가 계약이 필요하다(baseline 보고서). 사전 등록·단계 선별·챔피언 고르기 금지 구조는 그대로 쓴다 |
| C8 | 통계 커널 | `TC:src/evl/statistical_kernels.py:102` PSR, `:130` 기대 최대 Sharpe, `:145` DSR, `:175` CSCV-PBO, `:215`·`:241` 원형 블록 부트스트랩, `:266` Reality Check | 다중 시도 보정, 과적합 확률 | `TC:tests/test_evl_c6_statistical_kernels.py` 18개 | — | **변경 이식**(순수 함수 그대로) | PBO·부트스트랩은 기간별 값 계열이면 쓸 수 있다. 유사도 계열에도 적용 가능하다. DSR·PSR은 Sharpe 전용이라 성과 단계에서만 쓴다 |
| C9 | 강건성·체결 | `TC:src/evl/robustness.py`, `TC:src/evl/execution.py` | C6 체결 모델·강건성 보고 | `TC:tests/test_evl_c6_robustness.py` 14개, `TC:tests/test_evl_c6_execution.py` 16개 | — | **보류**(성과 단계에서 재검토) | 가격·체결 자료가 먼저 필요하다. 계획 §7의 장부 요구와 겹친다. 지금 이식하지 않는다 |
| C10 | 안정 구간 선택 | `TC:src/evl/selection.py:16` `frontier`, `:35` `plateau`, `:80` `complexity`, `:87` `low_drift`, `:96` `medoids`, `TC:src/evl/profile_selection.py`, `TC:src/evl/selection_contracts.py:10` `PROFILES` | 파레토 → 안정 고원 → 낮은 복잡도 → 낮은 표류 → 대표 중심 | `TC:tests/test_evl_c7_selection.py` 23개, `TC:tests/test_evl_c7_protocol.py` 25개 | 사전 선언(`selection_contracts.py:1`) | **변경 이식** | "여러 가중치가 같은 선택을 만든다"는 지시에 맞는다. 최고점 하나 대신 고원의 중심을 고른다. 주의: `PROFILES` Aggressive/Balanced/Defensive는 Track C 운용 제어 프로필이다. 사용자 공격형·균형형·수비형 QGV 프리셋과 같은 것으로 보지 않는다 |
| C11 | 보정·Holdout 실행 | `TC:src/evl/calibration_contracts.py`, `calibration_protocol.py`, `calibration_ledger.py`, `calibration_evidence.py` | C8 보정 단계와 Holdout 메타데이터 결속(최신 커밋 `ff78c4f6`) | `TC:tests/test_evl_c8_*.py` 52개 | Holdout 1회 소비 규칙 | **재사용 안 함** | 보정·Holdout 단계다. 이 연구는 Holdout을 쓰지 않는다. 보호 권한을 넓히지 않는다(§5) |
| C12 | Investor-QGV 기준 기록 | `TC:implementation/reports/investor_qgv_implementation_baseline.md` | C0/C1/C2/C4 재사용, 별도 추가 계약, 행동 채점기 필요 | — | — | **재사용(설계 입력)** | 결론이 이 문서와 같다. 코드는 없다 |
| C13 | Investor-QGV 미래 입력 요건 | `TC:implementation/reports/track_c_c6_independent_validation_2026-09-30.md:175-196` | 상태 `NOT_IMPLEMENTED / FUTURE_TRACK_C_INPUT`. 요건: 불변 증거·설정 ID, accession·빈티지, 보유 관측 기간과 공개 시각, 유명 이름으로 가중치 추정 금지, 공식/개인 분리 | — | — | **재사용(요건 목록)** | 13F-R 결정 후보의 점검표로 쓴다 |

### 1-4. Investor-QGV

- **코드 없음.** canonical과 Track C 브랜치 모두에 ProfileConfig·Research Spec v1.0·13F 파이프라인이 없다.
- 근거: `implementation/docs/qgv_common_contract_vnext/AUDIT.md:43`(ProfileConfig 없음), `implementation/docs/global_language_search/CONTRACT.md:25`, `src/product/web_assets/app.js:259`("Investor-QGV 미연결"), C13.
- 판정: 재사용할 구현이 없다. 새로 만들 때 C12·C13 요건을 따른다.

### 1-5. 이번에 열지 않은 것

- `origin/codex/track-c-gsup-v2-2026-10-03`, `origin/codex/fpia-execution-coverage-2026-10-05`, `origin/ccr-22e3ff16-p7n5k5`: [PRODUCT_FEATURE_MAP_20261018.md](../PRODUCT_FEATURE_MAP_20261018.md) 6b 행에만 근거가 있다. 이번 과제는 지정된 두 브랜치만 받았다. **미확인.**
- Track A raw store, Holdout 관련 파일: 보호 대상이라 열지 않았다.

### 1-6. 판정 요약

| 판정 | 자산 |
|---|---|
| 재사용 | T1, T2(선택), T5(정의), T6(검사 함수), T8(라벨 붙여서), T10, T11(함수), P1~P6, P10, P11(조건부), C12, C13 |
| 변경 이식 | T4, T11(N-PORT 경로), C0, C1, C3, C4, C5, C7(구조), C8, C10 |
| 재사용 안 함 | T3, T6(대상 연결), T7, T9, P7, P8, P9, C2, C6, C11 |
| 보류 | C9 |

---

## 2. 연구 필요 항목 대응표

열의 뜻: **있는 자산** / **빠진 것** / **새 백엔드 필요 여부**. "새 백엔드"는 연구 전용 비공개 경로다. 운영 producer가 아니다.

| 필요 항목 | 있는 자산 | 빠진 것 | 새 백엔드 |
|---|---|---|---|
| **다년 13F 보유** (기관 × 분기) | T1 파서, T4 표지 파서·단위 규칙, T5 적격 정의 | 과거 제출 목록(submissions 과거 페이지 또는 EDGAR 색인). 정정본 수집. 비공개 패널 저장 형식. XML 이전 시기(텍스트 정보표) 처리 [가정: XML 의무화는 2013년 무렵]. 기관 명단 규칙(13F-R1) | **필요.** 연구 전용 수집기(비공개, 일회성 배치). T3·T7을 고치지 않는다 |
| **정정 계보** (13F-HR/A) | T1의 정정 유형 검사, T10 규칙(RESTATEMENT = 대체, NEW_HOLDINGS = 추가), P1의 "정정은 자기 공개 시각부터" 원칙(`tests/test_research_pit_filings.py:287`) | 시점별 합성 규칙: 시각 t에 보이는 원본 + 추가 정정 + 대체 정정. 같은 분기 여러 원본 처리. 비공개 처리 해제(NEW_HOLDINGS) 반영 시각 | **필요.** 계보 해석기(순수 함수). 합성 시험 먼저 |
| **CUSIP → 발행사 식별** (시점별) | T6 검사 숫자, T11 US ISIN→CUSIP, Eaton N-PORT 증거 1건(T6 `:19`) | 과거 CUSIP↔CIK 연결표가 없다. CUSIP은 종류 단위다. 발행사 앞 6자리 변경·재사용, 합병, 티커 변경을 다루는 규칙이 없다. 라이선스 확인(13F-R6) | **필요.** 식별 해석기 + 증거 기록. 미해결은 NA로 센다 |
| **공개 시각 vs 분기말** | P1 `public_time`(날짜 → 다음 세션 개장, 접수 시각 우선, 보수적 해석), 세션 달력 2009~2028(`src/research/pit_filings.py:69-70`) | 13F 제출 접수 시각 확보(제출 헤더 또는 submissions `acceptanceDateTime`). 두 실험 유형의 구분 등록(§3-1) | 일부. P1을 13F 제출에 호출하는 얇은 어댑터만 |
| **PIT 재무** (FSDS / companyfacts) | P1 `pit_filter_companyfacts`, `as_filed_sic`, `qg_raw_metrics_as_of`. P3 `compute`. P2 FSDS 표본 | FSDS 나머지 분기 검증. 상장폐지 CIK의 companyfacts. 대량 수집 승인 | 기존 계획 W1·W2·W7과 같다. 13F용 새 백엔드 없음 |
| **과거 시점 요인 재구성** (15요인) | P4 Q·G 백분위, P5 V·총점·관문. 요인 백분위는 가중치와 무관(계획 §5) | 과거 모집단(D1)이 없어 백분위가 안 나온다(`cross_section_as_of` → `NEEDS_HISTORICAL_UNIVERSE`). V는 가격 필요(D5). 임의 θ(축 + 세부)로 다시 집계하는 연구 함수 | **필요.** θ 재집계 어댑터(운영 함수 호출만, 동등성 시험 포함). 모집단·가격은 백테스트 계획과 공유 |
| **유사도 목적함수** | 없음. C8 PBO·부트스트랩은 계열만 있으면 쓸 수 있다 | 표적 정의(13F-R7·R8), 목적함수(13F-R11), 공통 적격 모집단 정의, 연결률 보고 | **필요.** 행동 유사도 채점기(순수 함수) |
| **표본 외 분할** | C3 `annual_splits`·`SplitContract`·`split_samples`, C5 실행 구조, C1 시도 원장 | 13F 정답 지평(공개 지연) 기반 제거 규칙. "Holdout" 이름을 쓰지 않는 연구 끝 경계. 기간 길이(자료 확인 뒤) | **변경 이식.** C1·C3·C5를 연구 패키지로 옮긴다(13F-R15) |
| **탐색기** | C7 구조(사전 등록 격자, 단계 선별), C10 고원 선택 | QGV 가중치용 추가 계약(축만 / 세부만 / 둘 다 분리). 정규화(13F-R12) | **필요.** 추가 계약 + 탐색 실행기 |
| **성과 평가** | P10 지표 정의, C4 지표, C8 DSR·Reality Check, 계획 §11-3 표와 AS-1~AS-14 | 가격·배당·분할·상장폐지 정산(D5), 총수익 지수(D6), 현금 금리(D7), 장부 | 백테스트 계획과 **공유.** 13F 전용 새 백엔드 없음. 자료 전까지 `BLOCKED_ON_DATA` |
| **등록부·연구 프로필** | 계획 §3 "24개 밖 후속 후보" 칸, C0·C1 | 13F 실험 ID 체계, 연구 프로필 저장(공식/개인/연구 분리), Lab 화면 | **필요.** 등록부 코드는 계획 §7 "새로 필요" 목록과 같은 것을 함께 쓴다 |

---

## 3. 설계 선택지 (수치 없음)

수치(기간 길이, N, 격자 간격, 벌점 크기, 판정 문턱)는 이 문서에서 정하지 않는다. 결과를 보기 전에 등록부에서 한 번에 고정한다.

### 3-1. 문제 정의

- 기관 m, 분기 q의 **표적 집합** H(m, q) = 적격 보유(13F-R7) 중 시점별 모집단 안 발행사(CIK 단위, 종류는 1회로 합침).
- 후보 가중치 θ = (축 비중 Q·G·V) × (축마다 세부 요인 비중 5개). 각 묶음은 음수가 아니고 합이 일정하다.
- 점수 s(i, θ, t) = 현행 엔진과 같은 집계식(축 결측 재정규화, 축 50% 기준, 관문)을 θ로 다시 쓴 값. 요인 백분위는 시점 t에 한 번 계산한다.
- 선택 P(θ, t) = 점수 순위 또는 상위 N.

두 실험 유형을 **따로 등록**한다(재설계 §5 "보유를 사후 설명하는 실험과 공개 후 실행 가능한 전략을 구분"):

| 유형 | 요인 시점 | 보유 시점 | 쓸 수 있는 말 | 쓸 수 없는 말 |
|---|---|---|---|---|
| E1 사후 설명형 | 분기말 q 기준 PIT 요인 | 분기말 q 보유(공개는 나중) | "q 보유와 비슷한 선택을 만든 가중치" | 실행 가능한 전략, 수익 근거 |
| E2 실행 가능형 | 결정 시각 t 기준 PIT 요인 | t 전에 **공개된** 보유만으로 학습 | "공개 정보만으로 학습한 가중치의 이후 유사도·성과" | 기관 기준 복원 |

- E2의 공개 시각은 P1 `public_time`으로 정한다. 분기말을 공개 시각으로 쓰지 않는다.
- E1 결과를 성과 검증 근거로 옮기지 않는다.

### 3-2. 목적함수 후보

| ID | 후보 | 장점 | 약점 | 필요 자료 |
|---|---|---|---|---|
| O1 | 상위 N 겹침, 정밀도·재현율 | 상위 N 선정과 같은 모양. 설명이 쉽다 | 계단 함수라 탐색이 거칠다. N과 보유 수에 민감 | 이진 표적 |
| O2 | 순위 일치도(보유/비보유 쌍의 순서 일치 비율, AUC와 같은 꼴) 또는 순위 상관 | 문턱이 없다. N에 의존하지 않는다. 표적 수가 달라도 비교 가능 | 상위권 일치를 따로 강조하지 않는다 | 이진 표적 + 공통 적격 모집단 |
| O3 | 가중 Jaccard(보고 금액 비중 vs 점수 비중) | 큰 보유를 더 반영한다 | 보고 금액은 가격에서 나온 값이다. 단위 전환(2023-01-03 제출분부터 달러), 비공개 생략, 귀속 문제 검증이 먼저다. 비공개 환경만 | 검증된 금액 비중(13F-R8) |
| O4 | 로지스틱 적합(보유 여부 ~ 요인), 계수를 단체(simplex)로 제한 | 연속 최적화, 정규화가 자연스럽다 | 결측 처리가 엔진 재정규화와 다르다. 확률 해석이 과장되기 쉽다. 적합 결과를 엔진 집계로 다시 평가해야 한다 | 이진 표적 |

**권장:** 주목적함수는 **O2**. 보조 보고는 등록된 N의 **O1**. **O3**는 13F-R8에서 금액 비중을 검증한 뒤 진단으로만. **O4**는 탐색 시작 영역을 제안하는 진단으로만 쓴다.

근거:

- 기관마다 보유 수가 다르다. 문턱 없는 순위 지표가 기관 간 비교에 맞다.
- 최종 후보는 반드시 엔진과 같은 집계로 평가해야 화면·실험에 그대로 쓸 수 있다. O4의 계수를 그대로 쓰면 결측 처리가 달라진다.
- 재설계 §5가 든 "상위 N 겹침·정밀도/재현율·순위 유사도"를 모두 덮는다.

### 3-3. 탐색 공간과 실험 분리

- 지시대로 세 실험을 분리한다: **축 비중만**(세부는 현행 고정) / **세부 비중만**(축은 현행 고정) / **둘 다**.
- 각 실험에 탐색 범위, 제약, 목적함수, 시도 수를 C1 원장에 기록한다.
- 고정해야 할 것(결과 전): 관문 켬/끔, 유형 비중 결합 범위(A0형 미분류 또는 A형), 축 50% 기준, N, 동점 규칙(BT-16), CIK 1회(BT-17).
- 가중치 변화로 후보 자격·커버리지가 바뀐다. **공통 적격 모집단**(모든 후보 θ에서 총점이 나오는 기업)과 **실제 적용 모집단** 결과를 따로 본다(재설계 §5, 계획 §6과 같은 원칙).

### 3-4. 정규화 선택지

| ID | 방법 | 효과 | 비고 |
|---|---|---|---|
| G1 | 거친 사전 등록 격자 | 유효 자유도를 줄인다 | C7 구조 재사용 |
| G2 | 기준 가중치와의 거리 벌점 | 근거 없는 큰 이동을 막는다 | 기준(현행 공식 또는 균등)을 결과 전에 고정 |
| G3 | 가중치마다 하한·상한 | 한 요인 쏠림을 막는다 | 경계값 근거 필요 |
| G4 | 기관 묶음 공유(계층) | 기관별 표본 부족을 줄인다 | 묶음 정의가 사후 지식이면 안 된다(13F-R2) |
| G5 | 고원 중심 선택(C10) | 최고점 하나에 의존하지 않는다 | 고원 허용 오차를 결과 전에 고정 |

**권장:** G1 + G2 + G5를 함께 쓴다. G2의 기준은 **현행 공식 가중치**로 하고 균등 기준을 민감도로 둔다. 근거: 현행 대비 차이로 설명할 수 있다. 공식 기본값은 바꾸지 않는다. 고원 선택은 Track C에 시험된 구현이 있다.

### 3-5. 과적합 방지

- 시간순 학습 → 검증 → 미사용 평가 구간. 미래 공시·정정·가격을 쓰지 않는다. 정정 보유는 자기 공개 시각부터만 보인다.
- 모든 시도를 원장에 남긴다. 실패·중단도 지우지 않는다.
- 후보 묶음에 CSCV-PBO(C8)를 적용한다. 성과 단계에서는 DSR·Reality Check를 함께 본다.
- **기준선**과 비교한다: 균등 가중치, 현행 공식 가중치, 무작위 가중치 분포, 업종군 안에서 보유를 섞은 순열 귀무. 기준선 정의는 결과 전에 고정한다.
- **혼동 요인**: 기관은 큰 기업을 많이 보유한다. 요인 유사도가 기업 규모를 대신할 수 있다. 규모 기준선은 가격(시가총액)이 필요해 비공개 환경의 성과 단계에서만 다룬다. 공개 문서에는 쓰지 않는다.
- **비보유를 부정 선택으로 보지 않는 범위**: 모집단 밖, 식별 불명, 13F 비대상 자산은 표적에서 빼고 센다. 모집단 안 비보유도 소액 생략·비공개 처리 때문에 잡음이 있다. 연결률·제외·미확인 수를 보고한다.
- **식별 불가능성**: 여러 θ가 같은 선택을 만든다. 후보 묶음, 범위, 기간별 안정성을 보인다. "기관의 진짜 가중치"라고 쓰지 않는다.

### 3-6. 평가 기준 선택지

| 영역 | 선택지 | 권장 | 이유 |
|---|---|---|---|
| 유사도 판정 단위 | (a) 기관별 (b) 기관 묶음 (c) 전체 합산 | (a) 주, (c) 보조 | 화면 흐름이 "기관·기간 선택"에서 시작한다. 합산은 기관 수에 끌려가므로 보조로 둔다 |
| 유사도 비교 대상 | (a) 기준선 대비 차이 (b) 절대값 | (a) | 절대값은 보유 수·모집단 크기에 따라 바뀐다 |
| 기간 안정성 | (a) 미사용 구간 한 번 (b) 분할마다 반복 + 분포 | (b) | 한 구간 결과는 시장 국면에 좌우된다 |
| 성과 비교 | (a) 시장 총수익만 (b) 시장 총수익 + 현행 QGV(A0/A) + 단순 기준(공통 후보 동일 비중) | (b) | 재설계 §5·§12와 계획 P1~P3 구조와 같다. 유사도가 높다고 수익이 검증된 것은 아니다 |
| 판정 범주 | 계획 §11-1의 지지 근거 있음 / 방어 효과 있음 / 증거 부족 / 지지 못 함 / 판정 불가 | 그대로 재사용 | 종합 점수 하나로 줄이지 않는다는 기존 원칙과 같다 |
| 판정 문턱 | 결과 전 고정 | 값은 정하지 않음(13F-R11·R12와 함께 결정) | 근거 없는 수치를 만들지 않는다 |

---

## 4. 자료 공백과 결정 후보 13F-R1~R16

권장안은 결정이 아니다. 결정 전에는 문서·합성 시험·어댑터 설계만 한다.

| 번호 | 무엇을 | 선택지 | 권장안 | 근거 |
|---|---|---|---|---|
| 13F-R1 | 연구 기관 명단 | (a) 현행 10기관 설정(T8) 그대로 (b) 시점마다 과거 정보만으로 정한 규칙(예: 그 분기 13F-HR 제출 기관 중 사전 정의 조건) (c) 사용자가 고른 목록 | (b)가 정식. (a)·(c)는 제목에 "현재 선정 기관 탐색"을 붙인다 | 10기관은 2026년 지식으로 고른 명단이다. 계획의 "현재 생존 종목 한정 탐색" 라벨과 2026 TARGET 목록 사용 금지와 같은 원리다 |
| 13F-R2 | 학습 단위 | (a) 기관별 (b) 유형 묶음 (c) 전체 합산 | (a) 주, (c) 보조. (b)는 유형 라벨이 시점 정보일 때만 | `manager_styles_v0` 유형은 2026 라벨이다. 과거 묶음에 쓰면 사후 지식이 들어간다 |
| 13F-R3 | 보유 원천 | (a) 제출별 XML 정보표(T1 파서) (b) SEC 13F 구조화 자료 묶음 [미확인: 범위·열 정의] (c) 유료 공급자 | (a) 주. (b)는 대조용으로 범위를 먼저 확인. XML 이전 시기는 범위 밖 | 기존 파서가 XML을 검증한다. 이번 과제는 SEC 요청을 하지 않아 (b)를 확인하지 못했다 |
| 13F-R4 | 정정 계보 규칙 | (a) 원본 하나만 있는 분기만(현행 `select_quarters` 방식) (b) 시점별 합성: 원본 + NEW_HOLDINGS 추가 + RESTATEMENT 대체, 각자 공개 시각부터 (c) 최신 정정본 | (b) 주, (a) 민감도. (c) 금지 | (c)는 사후 수정치다. P1의 정정 원칙(S3)과 T10 규칙에 맞는 것은 (b)다. (a)는 정정 분기를 모두 버려 표본이 기운다 |
| 13F-R5 | 보유 공개 시각 | (a) 제출 날짜 → 다음 세션 개장 (b) 접수 시각이 날짜와 맞으면 그 시각 (c) 분기말 | E2는 P1 `public_time`(보수적 해석, (b) 우선 (a) 대체). (c)는 E1에만, 라벨 필수 | 분기말과 공개 시각은 다르다(재설계 §5). P1이 이미 시험된 규칙이다 |
| 13F-R6 | CUSIP → 발행사(CIK) 식별 | (a) 시점이 있는 공개 증거(N-PORT 보유 행의 CUSIP·ISIN·이름, 발행사 앞 6자리 + 이름 대조 기록) (b) 현재 카탈로그 ISIN (c) 유료 식별자 마스터 | (a) 주. 미해결은 NA + 건수. (b)는 현재 시점 표시에만. (c)는 약관 확인 뒤 | 현재 ISIN은 과거 식별 근거가 아니다(T6). CUSIP 마스터 이용 조건은 확인하지 않았다 [미확인]. 종류가 여럿이면 CIK 1회로 합친다(BT-17과 같은 단위) |
| 13F-R7 | 적격 보유 정의 | (a) T5 범위(매수 SH, Put/Call 없음, 수량 > 0) + 모집단 안 발행사 (b) PRN·옵션·펀드·ADR 포함 | (a). 나머지는 빼고 사유별로 센다 | T5가 이미 공개 경계 승인을 거친 정의다. 비대상을 기관의 부정 선택으로 보지 않는다(재설계 §5) |
| 13F-R8 | 표적 종류 | (a) 이진(보유/비보유) (b) 보고 금액 비중 | (a) 주. (b)는 단위·분모·적격성을 검증한 비공개 연구 자료에서만 | 재설계 §5 문장 그대로다. 금액은 가격에서 나온 값이라 공개하지 않는다. 단위는 제출일 기준(T4 `:345`) |
| 13F-R9 | 과거 모집단 | (a) 시점별 S&P 500 구성(BT-2 A) (b) 지수 ETF N-PORT 보유 목록(T11 방식) (c) 현재 504 | BT-2 결정을 따른다. (b)는 13F 연구용 후보로 따로 검토(식별 증거도 함께 얻음). (c)는 "현재 생존 종목 한정 탐색" | 모집단이 없으면 백분위가 없다(P1 `:568`). N-PORT 공개 시작 시기와 범위는 확인하지 않았다 [미확인] |
| 13F-R10 | 요인 재구성 범위 | (a) 1단계 Q·G만(V 축 비중 학습 안 함, 등록부에 명시) (b) 가격 확보까지 대기 (c) 가격 없는 V 대용치 | (a)를 먼저 별도 실험으로. (b)로 전체 15요인. (c)는 승인 없음 | V는 가격이 필요하다(D5 유료 미정). Q·G 원지표는 P1이 이미 준비한다 |
| 13F-R11 | 목적함수 | O1 / O2 / O3 / O4(§3-2) | O2 주, O1 보조, O3·O4 진단 | §3-2 |
| 13F-R12 | 정규화·선택 | G1~G5(§3-4) | G1 + G2(기준 = 현행 공식, 균등은 민감도) + G5 | §3-4 |
| 13F-R13 | 표본 외 분할과 미사용 구간 이름 | (a) C3 연 단위 분할(롤링·확장 둘 다) 이식, 정답 지평 = 보유 공개 지연 (b) 단일 시간순 분할 (c) 분기별 확장 창 | (a). 기간 길이는 자료 범위 확인 뒤, 결과 전에 고정. 미사용 구간은 **"연구 미사용 평가 구간"**으로 부르고 Holdout이라 부르지 않는다 | 계획 BT-10은 "가중치 변경 연구를 하게 되면 그 전에 따로 정한다"고 적었다. 이 연구가 그 경우다. 보호 Holdout(UNCONFIRMED_NOT_USED)은 그대로 둔다 |
| 13F-R14 | 등록과 공식 채택 경로 | (a) 계획 §3 "24개 밖 후속 후보"에 새 ID 묶음(실험 유형 E1/E2 × 축/세부/둘 다 × N, 버전 포함) (b) 기존 24개에 섞음 | (a). 결과 → 개인 실험 적용 → 공식 채택을 단계별로 분리. 자동 변경 없음 | 재설계 §12 "13F 학습 후보는 별도 실험 ID·버전", 주검정을 몰래 바꾸지 않음 |
| 13F-R15 | Track C 자산 반영 방식 | (a) 브랜치 통째 병합 (b) 순수 커널만 연구 패키지로 이식(C0·C1·C3·C5·C7 구조·C8·C10), 별도 PR (c) 새로 작성 | (b) | 브랜치가 오래된 기준에서 54커밋 갈라졌다. C6은 v1 엔진에 묶였다. C11은 Holdout 단계다. 시험된 커널을 버리고 새로 쓰면 중복이다 |
| 13F-R16 | 단계 순서와 성과 단계 의존 | (a) 1단계: 패널·계보·식별·Q·G 유사도(가격 불필요) → 2단계: V 포함 → 3단계: 고정 가중치 성과 (b) 모든 자료가 갖춰질 때까지 대기 | (a). 성과 단계는 백테스트 계획 자료(D1·D5·D6·D7)와 AS-1~AS-14를 공유하고 그때까지 `BLOCKED_ON_DATA` | 재설계 §13 3단계 순서. 가격 없이 할 수 있는 일을 막지 않는다 |

비공개 생략(confidential treatment)이 있는 기관·분기는 학습에서 빼고 센다. 13F-R4·R7에 함께 적용한다. 별도 번호를 두지 않는다.

---

## 5. 제약

- **Holdout은 쓰지 않는다.** 보호 Holdout 상태(`src/validation/forward_ledger.py:42` `UNCONFIRMED_NOT_USED`, [HOLDOUT_PROTECTION_CHECK_20261010.md](../qgv_v2_readiness/HOLDOUT_PROTECTION_CHECK_20261010.md))를 바꾸지 않는다. 기존 보호 권한을 넓히지 않는다. Track C C11(보정·Holdout)을 가져오지 않는다. 연구 미사용 평가 구간은 Holdout이 아니다(13F-R13).
- Track A Frozen 기준선과 raw store는 열지 않고 입력으로 쓰지 않는다([BACKTEST_DATA_AUDIT.md](BACKTEST_DATA_AUDIT.md) 4절).
- 전진 관측(2026-10-19 이후)을 섞지 않는다.
- **이 과제에서는 수익을 계산하지 않았다.** 유사도도 계산하지 않았다. 실데이터를 읽지 않았다.
- **공식 가중치를 바꾸지 않는다.** 연구 결과는 연구 프로필이다. 개인 실험 적용과 공식 채택은 각각 별도 결정이다.
- 가격·가격 파생값(보고 금액 비중 포함)·순위·과거 선정 목록·기관별 학습 결과는 공개 저장소에 쓰지 않는다. 실데이터 실행은 허용된 비공개 환경에서만 한다.
- 13F는 운영 점수를 바꾸지 않는다(PLAYBOOK §13-8). 이 연구도 운영 점수를 바꾸지 않는다.
- 결과를 "기관의 실제 기준 복원"이라고 쓰지 않는다.

---

## 6. 조사 중 발견한 사실

수정은 하지 않았다. Main이 판단할 사실만 적는다.

1. **취득 시각과 공개 시각이 한 검사에 묶여 있다.** `src/providers/sec_13f.py:177-182`는 취득 시각이 as_of보다 늦으면 NA다. 운영에는 맞다. 과거 연구에 그대로 쓰면 모든 과거 보유가 NA가 된다. 연구 어댑터는 파싱(as_of = 취득 시각)과 공개 시각 판정(P1)을 나눠야 한다.
2. **운영 수집기는 정정 분기를 버린다.** `select_quarters`(`src/providers/sec_13f_managers.py:199`)와 `capture_filing`(`:339-341`) 때문이다. 운영 두 분기 비교에는 안전한 선택이다. 다년 패널에는 표본 편향이 된다.
3. **운영 수집기는 최근 제출 목록만 본다**(`:124` `filings.recent`). 과거 분기는 submissions 과거 페이지나 EDGAR 색인이 필요하다.
4. **시간대 설명이 문서마다 다르다.** `src/research/pit_filings.py` 머리말은 "FSDS `accepted`에 시간대가 없고 확인하지 못함"이라고 적는다. [FSDS_SAMPLE_20261017.md](FSDS_SAMPLE_20261017.md) §5는 표본 20/20에서 뉴욕 현지 시각임을 확인했다. 코드의 `conservative` 해석은 두 경우 모두 늦은 쪽을 고르므로 결과는 안전하다. 머리말 갱신 여부는 Main 판단이다.
5. **Track C 프로필 이름이 사용자 프리셋과 겹친다.** `TC:src/evl/selection_contracts.py:10`의 Aggressive/Balanced/Defensive는 운용 제어(cash_buffer 등) 프로필 선택이다. 사용자 공격형·균형형·수비형 QGV 프리셋과 같은 것으로 보지 않는다.
6. **Investor-QGV는 이름만 있다.** 화면 문구(`app.js:259`)와 문서뿐이다. 재사용할 코드가 없다.
