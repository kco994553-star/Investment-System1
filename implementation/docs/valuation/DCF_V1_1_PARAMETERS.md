# DCF v1.1 — 미보고 항목 0 가정 · IFRS 지원 · 명시기간 성장률 h (v1.1 UNCALIBRATED 기본값 · 나중에 수정 가능)

## 사용자 결정 (2026-10-11, 정본)

1. 회사에 따라 실제로 없을 수 있는 FCFE 차입 항목(장기차입 발행·장기차입 상환·단기차입 순증감)이 선택된 공시에 **보고되지 않으면 0으로 가정**하고 `assumed_zero: true`, 사유 `NOT_REPORTED_ASSUMED_ZERO`로 표시한다. 핵심 항목(영업현금흐름·설비투자·매출·희석주식수)은 없으면 NOT_AVAILABLE이며 절대 0으로 채우지 않는다. 화면에 "미보고 → 0 가정"으로 보인다. 보고된 항목에는 동일 기간·동일 accn 규칙을 그대로 적용한다.
2. SEC companyfacts에 `ifrs-full` 사실을 보고하는 공시자(예: ASML, 20-F)를 지원한다. 통화가 다르면 환율을 만들지 않고 기존 `CURRENCY_BASIS_UNCONFIRMED` 규칙을 유지하며 화면에 보인다.
3. 명시기간 성장률 h(PROVISIONAL) = 자사 3년 매출 CAGR을 [0, 0.15]로 제한한 값. CAGR이 없으면 순방향 DCF는 NOT_AVAILABLE(`EXPLICIT_GROWTH_NOT_AVAILABLE`).

아래 규칙은 모두 **v1.1 UNCALIBRATED 기본값 · 나중에 수정 가능**이다. 보정·검증된 값이 아니다.

## 파라미터 — `qgv/dcf_parameters_v1_1_default.json` (v1.1 UNCALIBRATED 기본값 · 나중에 수정 가능)

`config_version: dcf_parameters/v1.1-default`, `status: V1_1_UNCALIBRATED_DEFAULT`, `supersedes: dcf_parameters/v1-default`, `fcfe_definition: fcfe/1.1`, 출력 버전 `v1+dcf_v1_1_default`(사용자 수정값은 계속 `v1+dcf_custom`). 명시 5년·할인율 10%·영구성장 2%·역DCF −50%~+100%·solver 정밀도는 v1과 같다. 바뀐 것은 다음 한 블록이다.

```json
"explicit_growth_rule": {"kind": "REVENUE_CAGR_3Y_CLAMP", "metric": "revenue_cagr_3y", "lower": 0.0, "upper": 0.15, "status": "PROVISIONAL"}
```

- 로더·검증기: `qgv/dcf_parameters.py` — `load_default_dcf_parameters()`는 이제 v1.1을, `load_v1_dcf_parameters()`는 이력 v1을 돌려준다. `validate_dcf_parameters`는 두 버전의 고정 형태를 모두 검사한다(`PARAMETERS_EXPLICIT_GROWTH` 등).
- 기기 사본: `web_assets/dcf-parameters-defaults.js`는 v1.1 사본이다(`tests/test_dcf_parameters.py`가 동일성 확인).
- v1 문서 `qgv/dcf_parameters_v1_default.json`은 이력으로 바꾸지 않는다. v1 파라미터를 넘기면 h는 여전히 `EXPLICIT_GROWTH_UNDECIDED`이고 출력 버전은 `v1+dcf_v1_default`이다.
- `type_config_v1.json`(GSQ-017)의 `dcf` 블록은 바꾸지 않았다.

### h 계산 (`dcf_parameters.explicit_growth`, JS `DeviceValuation.explicitGrowth`) — v1.1 UNCALIBRATED 기본값 · 나중에 수정 가능

```
h = min(upper, max(lower, revenue_cagr_3y))      # lower=0, upper=0.15
```

| 경우 | 결과 |
| --- | --- |
| 규칙 없음(v1) | `EXPLICIT_GROWTH_UNDECIDED` |
| 규칙 형태 오류(lower>upper 등) | `EXPLICIT_GROWTH_RULE_INVALID` |
| CAGR 없음·비유한 | `EXPLICIT_GROWTH_NOT_AVAILABLE` |
| 그 외 | h(`clamped`=제한 적용 여부 함께 표시) |

### CAGR 출처 선택

CAGR은 `sec_valuation_inputs.revenue_cagr_3y`로 계산해 `sec-valuation-inputs.json`의 `v_inputs.revenue_cagr_3y`에 싣는다. (2026-10-14 변경: `company-types-pricefree.json`의 유형 지표 `revenue_cagr_3y`는 이제 QGV v2 기간 규칙으로 계산한다 — `docs/daily_data_pipeline/PUBLIC_ENGINE_SCREENS.md`. 정확한 달력 연간 기간이 있는 기업은 두 값이 유효숫자 6자리까지 같다(테스트로 확인). 52/53주 회계연도 기업은 이 h 입력이 여전히 null이며, DCF h 규칙 변경은 별도 결정 사항이다.) 이렇게 한 이유: 기기는 파일 하나로 FCFE와 h를 같은 출처 해시·같은 신선도로 받고, 유형 엔진(type_config) 가져오기 실패와 무관하게 h가 계산된다. 계산 규칙: 같은 태그·단위(보고 통화)의 정확한 연간 기간 4개(최근 매출이 `facts_to_raw` 매출과 일치, 첫 해·최근 해 매출 > 0)에서 `(최근/3년 전)^(1/3) − 1`. 회계연도 추정 없음. 없으면 null + `REVENUE_CAGR_3Y_MISSING`.

## FCFE 정의 fcfe/1.1 — `product/sec_valuation_inputs.py` (v1.1 UNCALIBRATED 기본값 · 나중에 수정 가능)

```
FCFE = 영업현금흐름 − 설비투자 + 순차입
순차입 = 장기차입 발행 + 단기차입 순증감 − 장기차입 상환
FCFE/주 = FCFE ÷ 희석 가중평균 주식수
```

- 연간 서식: `10-K`, `10-K/A`, `20-F`, `20-F/A`, `40-F`(M1 `SUPPORTED_FORMS`와 같음. M1은 이미 이 서식을 받고 있었으므로 선택 규칙은 바꾸지 않았다). 기간 300~400일.
- taxonomy 선택: `us-gaap`과 `ifrs-full` 각각에서 영업현금흐름의 가장 최근 연간 종료일을 구해 더 최근인 쪽을 쓴다. 같은 날이면 `TAXONOMY_AMBIGUOUS`. 둘 다 없으면 `CASH_FLOW_NOT_REPORTED`(v1의 `US_GAAP_CASH_FLOW_NOT_REPORTED`를 대체). 한 행의 모든 구성요소는 선택된 taxonomy에서만 읽는다. 공개 행에 `taxonomy` 필드를 추가했다.
- 기간·통화·공시: 영업현금흐름의 최근 연간 기간 하나, 동일 통화 단위(주식수는 `shares`), 보고된 모든 구성요소는 동일 accn·동일 서식(아니면 `MIXED_FILINGS`). 이전 기간 값으로 채우지 않는다.
- 부호: 지급·상환·취득(Purchase…)은 보고값 그대로 빼고, 순증감은 그대로 더한다. IFRS도 같다.

### 미보고 → 0 가정 (`OPTIONAL_COMPONENTS`)

대상: `long_term_debt_issuance`, `long_term_debt_repayment`, `net_short_term_borrowing`만. 어떤 대체 개념도 완전히 맞지 않을 때:

1. 같은 기간에 다른 통화로 보고됨 → `COMPONENT_CURRENCY_MISMATCH`(NOT_AVAILABLE).
2. 같은 종료일에 모호한 개정 후보 → `COMPONENT_AMBIGUOUS`(NOT_AVAILABLE).
3. 그 구성요소의 어떤 개념도 그 기간(start·end)으로 **보유된 SEC 후보 어디에도**(선택·제외 모두) 없음 → `{"concepts": [], "value": 0.0, "assumed_zero": true, "reason": "NOT_REPORTED_ASSUMED_ZERO"}`.
4. 차입 쌍(발행 − 상환, 예: `ProceedsFromShortTermDebt` − `RepaymentsOfShortTermDebt`, IFRS `ProceedsFromCurrentBorrowings` − `RepaymentsOfCurrentBorrowings`)의 한쪽만 보고되고 다른 쪽은 그 기간 보유 후보 어디에도 없음 → 없는 쪽을 0으로 보고 `{"concepts": [보고된 개념], "value": 보고된 쪽의 부호 반영 값, "assumed_zero": false, "reason": "BORROWING_PAIR_PARTIAL"}`(사용자 결정 2026-10-11). 행은 LIVE로 남는다.
5. 그 밖(예: 다른 공시에만 보고되어 제외, 쌍의 다른 쪽이 보고되었지만 쓸 수 없음) → `<구성요소>_MISSING`(NOT_AVAILABLE). 보고된 줄은 버리지 않는다.

다른 공시(예: 10-K/A)에만 그 기간 값이 있으면 그 값이 선택되어 `MIXED_FILINGS`가 된다(0 가정 아님). 핵심 항목(영업현금흐름·설비투자·희석주식수)은 위 3에 해당해도 `<구성요소>_MISSING`이다. 보고된 0은 진짜 0이며 `assumed_zero: false`다. 공개 구성요소 형태는 `{concepts, value, assumed_zero, reason}`이다.

### 개념 목록 (왼쪽부터 순서대로 대체)

| 구성요소 | us-gaap | ifrs-full |
| --- | --- | --- |
| 영업현금흐름 (핵심) | `NetCashProvidedByUsedInOperatingActivities` → `NetCashProvidedByUsedInOperatingActivitiesContinuingOperations` | `CashFlowsFromUsedInOperatingActivities` |
| 설비투자 (핵심, 차감) | `PaymentsToAcquirePropertyPlantAndEquipment` → `PaymentsToAcquireProductiveAssets` | `PurchaseOfPropertyPlantAndEquipment` (유형자산만) |
| 장기차입 발행 (가산, 0 가정 가능) | `ProceedsFromIssuanceOfLongTermDebt` → `ProceedsFromIssuanceOfSeniorLongTermDebt` | `ProceedsFromNoncurrentBorrowings` → `ProceedsFromBorrowingsClassifiedAsFinancingActivities` |
| 장기차입 상환 (차감, 0 가정 가능) | `RepaymentsOfLongTermDebt` → `RepaymentsOfSeniorDebt` | `RepaymentsOfNoncurrentBorrowings` → `RepaymentsOfBorrowingsClassifiedAsFinancingActivities` |
| 단기차입 순증감 (가산, 0 가정 가능) | `ProceedsFromRepaymentsOfShortTermDebt` → `ProceedsFromRepaymentsOfCommercialPaper` → (`ProceedsFromShortTermDebt` − `RepaymentsOfShortTermDebt`, 둘 다 보고된 경우만) | `ProceedsFromCurrentBorrowings` − `RepaymentsOfCurrentBorrowings` (둘 다 보고된 경우만) |
| 희석주식수 (핵심, 분모) | `WeightedAverageNumberOfDilutedSharesOutstanding` | `AdjustedWeightedAverageShares` |

- 설비투자는 유형자산(PP&E)만이다. `PurchaseOfIntangibleAssets`(무형자산 취득)는 **넣지 않는다**(사용자 결정의 선택지 중 PP&E만 채택; 테스트가 무형자산 줄이 있어도 FCFE가 바뀌지 않음을 확인).
- 이중 계상 방지: IFRS 대체 개념 `…BorrowingsClassifiedAsFinancingActivities`는 단기차입을 포함한 총차입이다. 장기 발행·상환 중 하나라도 이 총차입 대체를 쓰는데 단기 쌍(`ProceedsFromCurrentBorrowings`/`RepaymentsOfCurrentBorrowings`)도 보고되면 `BORROWING_SCOPE_OVERLAP`(NOT_AVAILABLE). 단기 쌍이 미보고(0 가정)이면 총차입을 그대로 쓴다.

### V 입력 (`v_inputs`)

`eps`, `revenue`, `revenue_prev`(기존 승인 매핑 `facts_to_raw`와 동일)에 `revenue_cagr_3y`를 추가했다. IFRS 공시자를 위해 `facts_to_raw`의 희석 EPS 목록 끝에 `ifrs-full:DilutedEarningsLossPerShare`(`EUR/shares`, `USD/shares`)를 추가했고, M1 `DURATION_CONCEPTS`에도 같은 개념을 넣었다(시작일 없는 행 제외). 매출은 이미 `ifrs-full:Revenue`를 읽고 있었다. us-gaap 공시자는 `ifrs-full` 태그를 보고하지 않으므로 기존 us-gaap 결과는 그대로다. 이 변경으로 IFRS 공시자의 공개 Q·G 요소(EPS 성장)에도 EPS가 들어갈 수 있다.

### 고정 사유 코드

FCFE: `SEC_INPUT_NOT_AVAILABLE`, `CASH_FLOW_NOT_REPORTED`, `TAXONOMY_AMBIGUOUS`, `PERIOD_AMBIGUOUS`, `CURRENCY_AMBIGUOUS`, `COMPONENT_CURRENCY_MISMATCH`, `COMPONENT_AMBIGUOUS`, `MIXED_FILINGS`, `BORROWING_SCOPE_OVERLAP`, `DILUTED_SHARES_NON_POSITIVE`, `NUMERIC_INVALID`, `<구성요소>_MISSING`. 구성요소 사유: `NOT_REPORTED_ASSUMED_ZERO`, `BORROWING_PAIR_PARTIAL`. V 입력: 기존 + `REVENUE_CAGR_3Y_MISSING`.

## 공개 파일 `sec-valuation-inputs.json` (가격 없음)

`data.fcfe_definition`이 `fcfe/1.1`로 바뀌었다. 행의 `fcfe`에 `taxonomy`, 구성요소에 `assumed_zero`·`reason`, `v_inputs`에 `revenue_cagr_3y`가 추가되었다. Python 검증기 `sec_valuation_inputs.validate_data`와 JS 검증기 `DeviceValuation.validate`가 같은 규칙(0 가정은 선택 항목·빈 개념·값 0·고정 사유만, `BORROWING_PAIR_PARTIAL`은 선택 항목의 2항 쌍 중 순서를 지킨 일부 개념만, taxonomy별 개념 목록, 총차입 중복 금지, FCFE 합계 재계산)을 적용한다. 가격·시가총액·V 점수·가격 대비 비율·DCF 값은 넣지 않는다. 오프라인 빈 화면 픽스처(`tools/fixtures/empty_public_screens.json`)를 다시 만들었다.

## 기기 계산 (RAM 전용) — `DeviceValuation.view` / `qgv/device_valuation.device_value_view` (v1.1 UNCALIBRATED 기본값 · 나중에 수정 가능)

- `explicit_growth`: `{state, reason_codes, value(h), revenue_cagr_3y, clamped}`.
- 순방향 DCF: FCFE/주와 h가 모두 있으면 `EnginePreview.dcf`(Python `two_stage_dcf`)로 주당 내재가치를 계산한다. **가격을 쓰지 않는다**(가격 없이도 계산된다). 없으면 `FCFE_NOT_AVAILABLE`·h 사유. FCFE 통화가 파라미터 통화(USD)와 다르면 `CURRENCY_BASIS_UNCONFIRMED`(환율 변환 없음; 예: EUR로 보고하는 IFRS 공시자).
- V 요소(승인된 v1 raw_map, `qgv/raw_map.py` / `EnginePreview.vFactors`): DCF 값을 `dcf_value`로 넘긴다.
  - `margin_of_safety` = 승인 매핑의 DCF 분기만: 보수가치 0.75×DCF값, `clip(50 + (보수가치/가격 − 1)/0.3×50)`. DCF 값이 없으면 `DCF_NOT_AVAILABLE`, 0이면 `DCF_VALUE_ZERO`. 같은 매핑의 12×EPS 대체식은 DCF 안전마진이 아니므로 표시하지 않는다.
  - `fundamental_value` = 승인 매핑 그대로: DCF 값이 있으면 DCF 분기 `clip(50 + (DCF값/가격 − 1)/0.4×50)`, 없으면 기존 EPS(P/E) 분기.
  - DCF 값이 있을 때는 가격 통화가 FCFE 통화와도 같아야 한다(아니면 `BASIS_UNCONFIRMED`).
  - `reverse_dcf`는 그대로 풀린 h*만 사용. 나머지(동종·과거·업종·테마)는 기존 사유 그대로 NOT_AVAILABLE. 종합 V 점수는 만들지 않는다.
- 가격은 RAM 전용이다. 결과·저장소·요청 어디에도 가격이나 가격 파생값을 넣지 않는다.
- 화면(S04 요약 '가치 (이 기기)', S05 '가치·시나리오'): 배지 "v1.1 UNCALIBRATED 기본값 · 나중에 수정 가능"·`v1+dcf_v1_1_default`, 파라미터 줄에 h 규칙, 행 "명시기간 성장률 h"(값·3년 CAGR·범위 제한 여부), "DCF 내재가치", "안전마진"(점수), "미보고 항목: 미보고 → 0 가정 …(NOT_REPORTED_ASSUMED_ZERO)", 통화 불일치 시 "통화: CURRENCY_BASIS_UNCONFIRMED · 보고 통화 EUR · 기준 통화 USD · 환율 변환 없음", FCFE 줄에 서식·회계기준(US GAAP/IFRS).

## 그대로 NOT_AVAILABLE인 것

- CAGR이 없는 기업(연간 매출 4개 연속 기간 없음 등)의 h·순방향 DCF·DCF 안전마진.
- 보고 통화가 USD가 아닌 기업(예: EUR IFRS 공시자)의 순방향·역DCF와 가격 기반 V 요소(환율 없음).
- 핵심 항목 결측, 일부만 보고된 차입 쌍, 다른 통화·모호·다른 공시의 차입 줄, 총차입 대체와 단기 쌍의 중복.
- 동종·과거 밸류에이션·업종·테마 V 요소, 시나리오, 종합 V 점수.
- 공개 순방향 검증 원장의 V 버전 키(`forward_validation/v1+dcf_v1_default`, `V_REQUIRES_DEVICE_PRICES`)는 바꾸지 않았다.

## 검증

합성 입력만 사용: `tests/test_sec_valuation_inputs.py`(us-gaap 0 가정·IFRS 20-F/40-F·무형자산 제외·총차입 중복·CAGR 동일성), `tests/test_dcf_parameters.py`(v1.1 값·v1 이력·h 규칙·JS 동일), `tests/test_device_valuation.py`, `tools/device_valuation_node_test.js`, `tools/dcf_value_browser_test.js`. 참조 벡터 `tests/fixtures/device_valuation_reference_v1.json`을 `tools/device_valuation_reference.py --write`로 다시 만들었다(25개, h 범위 제한·CAGR 없음·EUR·v1 이력·규칙 오류·FCFE 0 포함). 실제 종목·가격·Holdout은 사용하지 않는다.
