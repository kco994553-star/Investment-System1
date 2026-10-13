## 요약

PLAYBOOK_V1 13-5 「매크로 상태 기준 v1」을 구현합니다. 기준·문구는 바꾸지 않았고, 문서가 비어 있거나 두 가지로 읽히는 곳은 가장 문자 그대로의 해석을 택하고 아래 「문서 모순·공백」에 적었습니다. 상태: **v1 · UNCALIBRATED** (과거 재생 검증 전). 매크로는 매도 판단에 쓰지 않습니다(`sell_decisions: false`).

### 경고등 5개와 자료 상태

| 경고등 | 조건(문서 그대로) | 계산 위치 | 자료 상태 |
|---|---|---|---|
| 고용 악화 | 실업률 3개월 평균 ≥ 지난 12개월 최저 + 0.5%p | 공개 파이프라인 | BLS LNS14000000 · **LIVE**(기존 macro v0 수집 본문 재사용) |
| 물가 과열 | CPI 전년동월비 > 5% | 공개 파이프라인 | BLS CUUR0000SA0 · **LIVE**(기존 수집) |
| 금리 곡선 역전 | 10년 − 3개월 < 0 이 20거래일 이상 | 공개 파이프라인 | 재무부 일일 par yield curve XML · **이번 PR에서 수집 추가**(머지 후 일일 Actions에서 첫 수집) |
| 시장 스트레스 | SPY 52주 고점 대비 ≤ −20% 또는 20일 실현변동성 3년 분포 상위 5% | 기기(RAM)만 | Worker SPY 5y 이력 · **기기** |
| 신용 스트레스 | HYG ÷ IEF 20일 변화 ≤ −5% (추정) | 기기(RAM)만 | **차단** · Worker 허용 목록에 HYG·IEF 없음 → 「확인 불가 · Worker 허용 목록 필요」 |

- 상태: 위기(켜짐 ≥ 3, 또는 시장+신용, 또는 CPI > 8%) → 경고(켜짐 2, 또는 CPI > 5% 이고 성장 < 0) → 그 외 정상. 성장 = 기존 macro v0 GDP 축(BEA A191RL).
- 자료 없는 경고등은 판정에서 빼고 「매크로(n/5 경고등)」로 표시, 3개 미만이면 「판정 신뢰도 낮음」. 결측은 0으로 채우지 않습니다.
- 모든 숫자는 `macro/macro_lights_v1.json`(version `v1`, status `UNCALIBRATED`)에 있습니다.

## 변경 내용

**A. 순수 함수 (Python 참조 + JS 미러, 합성 벡터 59개 JS==Python 비트 단위 일치)**
- `implementation/src/investment_system/macro/macro_lights_v1.py` / `.json` — 경고등별 함수(`employment_light`, `inflation_light`, `curve_light`, `market_light`, `credit_light` → `{lit: true/false/null, reason, 값…}`)와 `macro_state(lights, cpi_yoy, growth)` → `{state, lit_count, available_count, low_confidence, reasons}`. 산술은 + − × ÷ √ 만 고정 순서로 써서 JS와 같은 값을 냅니다.
- `implementation/src/investment_system/product/web_assets/macro-lights.js` — 같은 함수의 JS 미러, 공개 블록 검증, 공개+기기 병합, 화면, `MacroLights.current()`(RAM만).
- `tools/macro_lights_reference.py` → `tests/fixtures/macro_lights_v1_vectors.json`(모두 합성), `tools/macro_lights_node_test.js`(ci_node_tests 등록), `tests/test_macro_lights_v1.py`.

**B. 공개 부분 (가격 없음)**
- `providers/macro_v0_collection.py`: `collect_treasury_curve` — `home.treasury.gov/.../pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=YYYY` 전년·당해 2건(20거래일 연속이 새해를 넘을 수 있음). 허용 URL은 기존 `ENDPOINTS["TREASURY"]` 하나, 쿼리는 `data`·`field_tdr_date_value=4자리 연도`만 허용, 리다이렉트 거부, 진단은 고정 토큰(`MACRO_V1_CURVE_FETCH stage/code/http/content/size`)만.
- `macro/macro_lights_public.py`: 재무부 XML 파서(DOCTYPE/ENTITY 거부, null 유지), 공개 블록 생성·검증.
- `product/public_engine_screens.py`: `macro-screen.json` `data.macro_lights_v1` = 고용·물가·곡선 3개만, 경고등별 `as_of`·`source`·`source_series_id`·입력 sha256. 두 해 중 하나라도 실패하면 곡선은 `NOT_AVAILABLE`(연속 일수가 몰래 짧아지지 않게). 시장·신용은 `device_lights`라는 이름만 있고 값은 없습니다.
- `tools/public_screens_pipeline.py`: `--macro-v0`에서 곡선 수집, 로그는 `MACRO_V1_LIGHT light=… state=… lit=ON/OFF/NO_DATA reason=…`(값 없음).
- `public-screens.js` 검증기에 블록 검증 추가(Python과 같은 규칙), 이전 v0.1.1 엔진 결과는 [자세히] 안으로.

**C. 기기 부분**
- 매크로 화면 상단 「매크로 상태」 카드: 경고등 5개(켜짐/꺼짐/자료 없음), 「매크로(n/5 경고등)」, 정상/경고/위기, 「판정 신뢰도 낮음」, [자세히] 「이전 기준(v0.1.1)」.
- 「SPY 불러와 시장 경고등 계산 (기기 RAM)」 버튼을 눌렀을 때만 Worker에서 SPY 5y를 읽습니다(비공개 이력 켜짐 + 승인 주소 + 구글 세션 필요). 저장·전송·로그 없음. `price-store.js`는 base에 없어 기존 Worker 이력 경로(`session.fetchHistory` + `VirtualTradingRunner.seriesFromHistory`)를 씁니다.
- `MacroLights.current()` → `{state, lit_count, available_count, low_confidence}` (앱 로드 시 공개 경고등으로 계산, 기기 계산 후 갱신, RAM만).

**E·F. 테스트·가드**
- `tools/macro_lights_browser_test.js`(ci_browser_tests 등록, 390·1280px): 빈 공개 화면, 공개 경고등, Worker 스텁으로 SPY만 요청 → 위기, 저장·전송 없음, [자세히].
- `pages_artifact_guard.py` 고정값 갱신(app.js, index.html, public-screens.js, locale.js, macro-lights.js 추가), files_scanned 76 → 77, 빌드 파일 목록에 `macro-lights.js` 추가. `tools/fixtures/empty_public_screens.json` 재생성.
- 기존 테스트 1곳 조정: `test_macro_raw_axes_v0.py`의 orphan 검사는 같은 BLS 본문을 읽는 `macro_lights_v1` 블록도 함께 지워야 LIVE 근거가 사라집니다.

## 과거 재생 (공개 경고등만: 고용·물가·곡선 + 성장)

`tools/macro_lights_replay.py`(로컬 CSV, stdout만, 파일 쓰기 없음)로 매주 금요일 평가. 자료: 수정치(현재 빈티지)의 UNRATE, CPI-U NSA, A191RL, T10Y3M(재무부 CMT 10Y−3M)을 GitHub 공개 미러에서 받아 로컬에서만 사용. 발표 지연 근사(월 자료는 다음 달 15일부터, 분기 자료는 분기 말 + 30일). 시장·신용(가격 기반) 결과는 이 PR에 넣지 않습니다.

| 구간 | 경고 첫 주 | 위기 첫 주 | 주 수(정상/경고/위기) | 켜진 경고등 첫 주 |
|---|---|---|---|---|
| 2000–2002 | 없음 | 없음 | 156/0/0 | 곡선 2000-08-18, 고용 2001-07-20 (동시에 켜진 적 없음) |
| 2007-07–2009-06 | 2008-07-18 (켜짐 2 + 물가>5%·성장<0) | 없음 | 91/13/0 | 고용 2008-02-15, 물가 2008-07-18 |
| 2020 | 없음 | 없음 | 52/0/0 | 고용 2020-05-15 |
| 2022 | 2022-11-25 | 2022-04-15 (CPI > 8%) | 15/6/31 | 물가 2022-01-07, 곡선 2022-11-25 |
| 대조 2004–2006 / 2013–2019 | 없음 | 없음 | 전부 정상 | 곡선 2006-08-18 / 2019-06-21 |

공개 경고등만으로는 2000·2020 위기를 잡지 못합니다(2020은 고용이 발표 지연으로 5월에야 켜짐). 시장·신용 경고등이 들어가야 판단할 수 있으며, 그 재생 결과는 가격 기반이라 소유자에게만 따로 보고했습니다. 수정치 사용·발표일 근사 때문에 실시간 재현이 아닙니다. **상태는 계속 v1 · UNCALIBRATED입니다.**

## 문서 모순·공백 (가장 문자 그대로의 해석으로 구현)

1. 13-5 표의 재무부 일일 금리 「수집 중」: base에는 `ENDPOINTS["TREASURY"]`와 10년물 파서만 있고 수집기는 없었습니다(3개월물도 없음). 이번 PR에서 수집기를 추가했습니다.
2. 고용 「지난 12개월 최저」: 최신 달을 포함한 12개월(t−11…t)의 **월별 값** 최저로 구현(Sahm 규칙처럼 3개월 평균의 최저가 아님). BLS가 발표하지 않은 달(예: 2025-10)은 건너뛰고 채우지 않으며 사용한 달 수(`low12_count`)를 표시합니다. 3개월 평균 창에 빈 달이 있으면 자료 없음.
3. 「20거래일」: 재무부가 금리를 발표한 날(채권시장 영업일)을 연속으로 셉니다. 연속 구간 안에 값 없는 날이 있고 아직 20일이 안 되면 자료 없음.
4. 시장: 가격 기준(원가/수정가)이 없어 Worker 계약의 원 종가(RAW_CLOSE). 52주 = 최신일 포함 364일. 실현변동성 정의가 없어 단순수익률 20개의 표본표준편차 × √252. 「상위 5%」 = 지난 3년(달력) 값 중 현재보다 큰 값이 5% 미만. 낙폭이 꺼짐이고 변동성 자료가 없으면 경고등은 자료 없음(OR의 미정).
5. 신용 「20일 동안 −5% 이하」: 두 ETF가 모두 있는 날 기준 20세션 전 대비 시점 간 변화로 구현(20일 안의 고점 대비 낙폭이 아님).
6. 「매크로(n/5 경고등)」의 n: 판정에 쓴 (자료 있는) 경고등 수로 해석, 켜진 수는 따로 표시.
7. 자료 있는 경고등이 0개일 때 문서대로면 「정상(0~1개)」 + 「판정 신뢰도 낮음」이 됩니다. 「판정 불가」로 할지 결정 필요.
8. 「물가 > 5%이고 성장 < 0」의 성장: 기존 GDP 축 = 가장 최근 분기 1개의 연율 성장률(수정 잦음, 2분기 연속 아님).
9. 「물가 > 8%」는 단독으로 위기 → 재생에서 2022-04~11 위기 31주가 CPI 하나로만 나옵니다(문서대로).
10. 시장+신용이 동시에 켜지면(2개) 위기가 경고보다 우선.
11. CPI 2025-10 미발표 때문에 2026-10 자료가 나오는 달에는 기준월이 없어 물가 경고등이 한 달 동안 「자료 없음」이 됩니다.

## 소유자 승인이 필요한 항목

1. **Worker 변경(별도 승인)**: `implementation/worker/src/index.js` `BENCHMARK_SYMBOLS`에 `HYG`, `IEF` 추가 후 재배포. 함께 바꿀 곳: `google-sheet-quotes.js` `HISTORY_SYMBOLS`, `macro-lights.js` `WORKER_ALLOWED`. 그 전까지 신용 경고등은 「확인 불가 · Worker 허용 목록 필요」이고 요청을 보내지 않습니다(허용되면 HYG·IEF 1y를 읽는 코드는 준비됨).
2. 일일 Actions의 새 외부 호출: `home.treasury.gov` 재무부 XML(연 2건/일).
3. 위 「문서 모순·공백」 해석 확인(특히 2, 4, 6, 7).
4. 재생 결과를 보고 UNCALIBRATED → 보정 여부 결정.

## 테스트

- pytest 전체 통과, node 매니페스트 전체 통과(45), Worker node 테스트 통과
- 브라우저 매니페스트(로컬 Playwright 1.56, pwa_browser_test 제외 — 1.57 이상 필요) 통과
- 빌드 + `pages_artifact_guard` PASS (files_scanned 77)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01P6ERCVvjUxs96HMBuTZ1o1
