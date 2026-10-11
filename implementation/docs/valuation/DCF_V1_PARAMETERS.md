# DCF v1·역DCF — 기본 파라미터 채택(v1 UNCALIBRATED 기본값)

> **v1.1로 대체됨 (2026-10-11).** 현재 기본값은 `dcf_parameters/v1.1-default`(`v1+dcf_v1_1_default`)이며 규칙은 [`DCF_V1_1_PARAMETERS.md`](DCF_V1_1_PARAMETERS.md)에 있다: 미보고 차입 항목 0 가정(`NOT_REPORTED_ASSUMED_ZERO`), IFRS(`ifrs-full`, 20-F/40-F) 지원, 명시기간 성장률 h = 3년 매출 CAGR을 [0, 0.15]로 제한(PROVISIONAL), 순방향 DCF·DCF 안전마진 계산. 이 문서와 `qgv/dcf_parameters_v1_default.json`은 이력으로 남긴다. 아래 '남은 결정' 1·2는 v1.1에서 결정되었다.

## 사용자 결정 (2026-10-11, 정본)

> "DCF: 5년 / 할인율 10% / 영구성장 2% / 역DCF -50%~+100%. FCFE = 영업현금흐름 − 설비투자 + 순차입, 희석주식수 기준. 정의를 문서에 명시."

모든 값은 **v1 UNCALIBRATED 기본값, 나중에 수정 가능**이며 화면에 기본값으로 표시한다. V(DCF)가 붙은 출력은 별도 버전 `v1+dcf_v1_default`로 기록한다(사용자 수정값은 `v1+dcf_custom`).

## 채택 파라미터 — `qgv/dcf_parameters_v1_default.json`

`config_version: dcf_parameters/v1-default`, `status: V1_UNCALIBRATED_DEFAULT`, `confirmed: true`. 로더·검증기는 `qgv/dcf_parameters.py`(`load_default_dcf_parameters`, `validate_dcf_parameters`), 기기 사본은 `web_assets/dcf-parameters-defaults.js`(`tests/test_dcf_parameters.py`가 동일성 확인).

| 파라미터 | 값 | 비고 |
| --- | --- | --- |
| 명시기간 `explicit_years` | 5 | |
| 할인율 `discount_rate` | 0.10 | basis `COST_OF_EQUITY`. 관측 자본비용이 아닌 사용자 기본값 |
| 영구성장률 `terminal_growth` | 0.02 | 현금흐름 성장의 증거가 아닌 사용자 기본값. r > g 필수 |
| 역DCF 탐색 구간 `solver.growth_lower/upper` | −0.50 / +1.00 | 구간 밖이면 `ROOT_NOT_BRACKETED`(자동 확장 없음) |
| solver 정밀도 | 상대 가격오차 1e−10 / 최대 200회 | 계산 종료 조건이지 금융 임계값 아님 |
| cashflow basis | `FCFE_PER_SHARE` | 아래 fcfe/1 정의 |
| 주식수 basis | `WEIGHTED_AVERAGE_DILUTED` | 희석 가중평균 주식수 |
| 통화 | `USD` | 통화 변환 없음. 불일치는 `CURRENCY_BASIS_UNCONFIRMED` |
| 명시기간 성장률 h `explicit_growth` | **null** | `EXPLICIT_GROWTH_UNDECIDED` — 사용자 미결정 |

공식 `type_config_v1.json`(type_config/1, OFFICIAL_PROVISIONAL)은 GSQ-017에 따라 불변이며 그 `dcf` 블록(null/confirmed=false)은 바꾸지 않는다. 이전 확인 대기 파일 `qgv/dcf_config_v1.json`도 이력으로 그대로 둔다. 채택값의 단일 출처는 `dcf_parameters_v1_default.json`이다.

## FCFE 정의 fcfe/1 — `product/sec_valuation_inputs.py`

```
FCFE = 영업현금흐름 − 설비투자 + 순차입
순차입 = 장기차입 발행 + 단기차입 순증감 − 장기차입 상환
FCFE/주 = FCFE ÷ 희석 가중평균 주식수
```

- 입력: SEC companyfacts 10-K(10-K/A 포함) 연간 사실만(기간 300~400일). M1(`providers/sec_m1.build_input`)이 고른 사실(filing 색인·acceptance·개정 승자 규칙 적용)을 그대로 쓴다.
- 회계기간: 영업현금흐름이 보고된 **가장 최근 연간 기간**(start·end) 하나. 모든 구성요소는 그 **동일 기간·동일 통화 단위**여야 하고(주식수는 `shares`), **동일 accn**(같은 공시)에서 와야 한다. 이전 기간 값으로 채우지 않는다.
- 결측: 공시가 보고하지 않은 구성요소는 `NOT_AVAILABLE`이며 **0으로 채우지 않는다**. 공시가 0을 보고하면 0이다.
- 부호: 지급(Payments…)·상환(Repayments…)은 보고값 그대로 빼고, 순증감(ProceedsFromRepayments…)은 그대로 더한다.

### 사용하는 us-gaap 개념(왼쪽부터 순서대로 대체)

| 구성요소 | 1순위 | 대체 |
| --- | --- | --- |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | `NetCashProvidedByUsedInOperatingActivitiesContinuingOperations` |
| 설비투자(차감) | `PaymentsToAcquirePropertyPlantAndEquipment` | `PaymentsToAcquireProductiveAssets` |
| 장기차입 발행(가산) | `ProceedsFromIssuanceOfLongTermDebt` | `ProceedsFromIssuanceOfSeniorLongTermDebt` |
| 장기차입 상환(차감) | `RepaymentsOfLongTermDebt` | `RepaymentsOfSeniorDebt` |
| 단기차입 순증감(가산) | `ProceedsFromRepaymentsOfShortTermDebt` | `ProceedsFromRepaymentsOfCommercialPaper` → (`ProceedsFromShortTermDebt` − `RepaymentsOfShortTermDebt`, 둘 다 보고된 경우만) |
| 희석주식수(분모) | `WeightedAverageNumberOfDilutedSharesOutstanding` | 없음 |

IFRS(`ifrs-full`) 공시자는 읽지 않는다(`US_GAAP_CASH_FLOW_NOT_REPORTED`).

### 고정 사유 코드

`SEC_INPUT_NOT_AVAILABLE`, `US_GAAP_CASH_FLOW_NOT_REPORTED`, `PERIOD_AMBIGUOUS`, `CURRENCY_AMBIGUOUS`, `COMPONENT_CURRENCY_MISMATCH`, `COMPONENT_AMBIGUOUS`, `MIXED_FILINGS`, `DILUTED_SHARES_NON_POSITIVE`, `NUMERIC_INVALID`, `<구성요소>_MISSING`(예: `NET_SHORT_TERM_BORROWING_MISSING`).

## 공개 파일 `sec-valuation-inputs.json` (가격 없음)

공개 화면 생성기(`public_engine_screens.generate_screen_bundle`)가 SEC 일일 수집과 같은 경로로 만든다. 기업별(공식 TARGET 19, US17만 값 가능) `fcfe`(state·reason_codes·fcfe_per_share·currency·회계기간 start/end·accn·form·구성요소별 concept·값)와 V 입력용 보고값 `v_inputs`(희석 EPS·매출·전기 매출·통화, 기존 승인 매핑 `facts_to_raw`와 동일)를 담는다. 가격·시가총액·V 점수·가격 대비 비율은 넣지 않는다. Python 검증기 `sec_valuation_inputs.validate_data`와 JS 검증기 `DeviceValuation.validate`가 같은 규칙(키 고정, FCFE 합계 재계산 일치, 출처 해시·신선도)을 적용하고, `pages_artifact_guard.py`는 `FILENAMES` 등록으로 이 파일을 검사한다.

## 기기 계산 (RAM 전용) — S04 요약 '가치 (이 기기)' 카드, S05 '가치·시나리오' 탭

`DeviceValuation.view`(Python 참조 `qgv/device_valuation.device_value_view`, 벡터 `tests/fixtures/device_valuation_reference_v1.json`):

- 가격: 이 기기에 저장된 시세(`DeviceActual.ramQuote`, 기존 ACTUAL 시장 데이터) 또는 S04에서 불러온 비공개 일별 이력 종가. 새 가격 출처를 호출하지 않는다. 결과에 가격을 넣지 않고 저장·전송하지 않는다.
- 역DCF 내재 성장률 h*: `EnginePreview.reverseDcf`(FCFE/주, 기기 가격, 채택 파라미터).
- V 요소: `EnginePreview.vFactors`(승인된 v1 raw_map) — `reverse_dcf`는 풀린 h*로만(실패 시 `REVERSE_DCF_NOT_AVAILABLE`, 기존 P/E 대용 성장률 미사용), `fundamental_value`는 승인된 EPS 대체식(P/E)만. 나머지(동종·과거·업종·테마)는 기존 사유 그대로 NOT_AVAILABLE.
- 순방향 DCF 내재가치와 DCF 안전마진: h 미결정 → `NOT_AVAILABLE · EXPLICIT_GROWTH_UNDECIDED`.
- 종합 V 점수는 만들지 않는다.

## 함수·basis (변경 없음)

`two_stage_dcf(cashflow_per_share, growth_rate, parameters, cashflow_currency)`와 `reverse_dcf(cashflow_per_share, price, parameters, cashflow_currency, price_currency)`는 keyword-only이며 가격을 인자로만 받고 반환 repr에서 수치를 숨긴다. 기호 F0=주당 FCFE, h=명시기간 성장률, r=할인율, g=영구성장률, n=명시기간:

- t=1..n: Ft=F0×(1+h)^t, PVt=Ft/(1+r)^t.
- terminal PV=Fn×(1+g)/(r−g)/(1+r)^n.
- value_per_share=PVt 합+terminal PV. 금융 값을 임의 clip하지 않는다.
- 역DCF는 같은 함수가 가격과 같아지는 h를 탐색 구간 안에서 이분법으로 찾는다. 양의 FCFE·r>g·동일 통화/주당 basis가 필요하다(`NON_POSITIVE_CASHFLOW` 등).

고정 실패 코드: PARAMETER_APPROVAL_PENDING, PARAMETER_INVALID, GORDON_RATE_ORDER, CASHFLOW_BASIS_UNCONFIRMED, SHARE_BASIS_UNCONFIRMED, CURRENCY_BASIS_UNCONFIRMED, INPUT_INVALID, SOLVER_INVALID, ROOT_NOT_BRACKETED, ROOT_NOT_CONVERGED, NUMERIC_OVERFLOW.

## 남은 결정

1. 명시기간 성장률 h(순방향 DCF 내재가치·DCF 안전마진의 전제).
2. 실데이터에서 단기차입 줄 자체가 없는 기업이 많으면 FCFE가 NOT_AVAILABLE이 된다. "공시에 해당 줄이 없으면 0" 허용 여부는 사용자 결정 사항이며 현재는 허용하지 않는다.
3. EPS 기반 안전마진 대체식(12×EPS)은 승인 raw_map에 있으나 DCF 안전마진과 구분하기 위해 표시하지 않는다.

## 검증

합성 입력만 사용: `tests/test_dcf.py`, `tests/test_dcf_parameters.py`, `tests/test_sec_valuation_inputs.py`, `tests/test_device_valuation.py`, `tools/device_valuation_node_test.js`, `tools/dcf_value_browser_test.js`. 기존 36개 Python↔JS 참조 벡터(`python_js_reference_v1.json`)는 바꾸지 않았다. 실제 종목·가격·Holdout은 사용하지 않는다.
