# Research 표시 전용 지표 v1

2026-10-10 사용자 결정 [26E GSQ-015](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md#gsq-015--26e-research-표시-전용-기본값한국식-모델-채택-아님-2026-10-10-utc). **표시 전용 기본값(한국식), 모델 채택 아님**. 현행 TechnicalEngine의 세 계산은 별도 [#111](https://github.com/kco994553-star/Investment-System1/pull/111)이며 이 구현의 의존 PR이 아니다. 과거 DESIGN의 미확정 모델 지표 집합을 확정·복원한 것으로 해석하지 않는다.

## 입력·출력 경계

`technical/research_display.py::calculate_research_display(series, as_of, *, include_sma240=False)`는 #105의 `prepare_daily_returns`로 입력을 먼저 검증한다. 합성 입력만 허용하고 시각·달력·거래일 완결·상장 identity·가격 basis·기업행위 근거의 기존 차단을 그대로 따른다. #105의 last-20 returns는 검증 metadata로만 남고 표시 계산은 **as_of까지 검증된 전체 일봉**을 사용한다. 실제 입력 허용·공급자 호출·수집·PIT 검증 완료를 추가하지 않는다.

출력은 frozen dataclass와 tuple로 된 RAM 객체이며 result/data/각 component 모두 `role=RESEARCH_DISPLAY_ONLY`다. 일반 상태는 `DEMO` 또는 `NOT_AVAILABLE`, 각 지표 마지막 값의 `latest_state`는 `AVAILABLE` 또는 `NOT_AVAILABLE`이다. `DEMO`는 합성 표시 계산이며 모델 준비 완료를 뜻하지 않는다. 날짜별 `values[i] is None`은 해당 칸의 **null(NOT_AVAILABLE)**이며 `unavailable_reasons[i]`가 원인을 나타낸다. 유효한 계산의 실제 0과 결측을 구분한다. 숫자는 repr에 숨기며 serializer/export/logger/file/provider 경로를 만들지 않는다. **Model·TSV·QGV·public bundle 연결 금지**. 기기 화면·Worker 연결은 코덱1 후속 범위다.

미국·한국·일본 모두 caller가 제공하고 #105가 확인한 **거래 세션 개수**로 계산한다. 휴일·달력 날짜로 period를 채우거나 누락 거래일을 보간하지 않는다. 합성 시험 날짜는 author-created 예시이며 Holdout 또는 검증 기간 선택이 아니다. `pit_status=NOT_VERIFIED`·`PLACEHOLDER_UNVALIDATED` metadata를 유지한다.

## 승인된 계산과 최초 값

첫 거래 세션을 1로 센다. 초기값은 아래 방식으로 고정하고 임의 period·임계값·신호·새 지표를 받는 API는 만들지 않는다.

| 출력 ID | 계산·초기값 | 최초 유효 거래 세션 | 표시 기본값 |
| --- | --- | --- | --- |
| SMA_5/20/60/120 | 최근 N개 선택 basis 종가의 산술평균 | N번째 | 기본 표시 |
| SMA_240 | 동일, `include_sma240=True`일 때만 계산 | 240번째 | 선택 항목, 기본 OFF |
| EMA_20 | α=2/(20+1), 첫20개 종가 SMA로 seed, 이후 `prev + α×(close-prev)` | 20번째 | period 승인; 화면 ON/OFF는 구현 범위 밖 |
| RSI_14 | 첫14개 종가 변화의 gain/loss 산술평균 seed, 이후 Wilder `prev+(current-prev)/14`. `100×avg_gain/(avg_gain+avg_loss)` | 15번째 | 동일 |
| MACD_12_26 | 전체 입력의 SMA seed EMA12와 EMA26의 차 | 26번째 | 동일 |
| MACD_SIGNAL_9 | 유효 MACD 차이 첫9개 평균 seed, α=2/(9+1) EMA | 34번째 | 동일 |
| MACD_HISTOGRAM_12_26_9 | MACD−signal, 두 값이 모두 유효할 때 | 34번째 | 동일 |
| BOLL_MIDDLE_20 | SMA20 | 20번째 | 동일 |
| BOLL_UPPER_20_2 / BOLL_LOWER_20_2 | SMA20 ± 2×최근20 종가의 **모집단 표준편차**(분모20) | 20번째 | 동일 |
| ATR_14 | `TR=max(high-low, abs(high-prev_close), abs(low-prev_close))`; 이전 종가가 필요한 첫 TR은 2번째 세션. 첫14개 TR 평균 seed, 이후 Wilder `prev+(TR-prev)/14` | 15번째 | 동일 |

MACD의 EMA12는 전체 입력의 첫12개 종가로 시작한다. TA-Lib `MACD()`가 fast EMA를 뒤쪽 구간으로 초기화하는 경우와 초기값이 다를 수 있다. 참조 시험도 **독립 EMA12−EMA26 및 그 유효 차이의 EMA9**를 비교한다. 표시 전용 초기화 규약이며 모델 산식·채택을 변경하지 않는다.

RSI는 gain>0/loss=0일 때100, gain=0/loss>0일 때0이다. **둘 다0이면 undefined → null, `ZERO_TOTAL_CHANGE`**로 두며 0·50을 대체값으로 넣지 않는다. EMA/ATR의 최초 유효값 전과 MACD signal 초기화 전은 `WARMUP`이다. 119거래일의 입력으로 SMA120을 만들지 않는다.

## OHLC·오류 처리

- 종가 기반 지표는 series의 RAW_CLOSE 또는 PROVIDER_ADJUSTED_CLOSE 하나를 선택한다. bar별 fallback은 없다.
- ATR은 **raw OHLC+raw 이전 종가**의 근거가 모두 있을 때만 계산한다. adjusted close와 raw OHLC를 혼합하지 않고 ATR만 null(`OHLC_BASIS_UNCONFIRMED`)로 둔다.
- OHLC 전체 미제공은 ATR만 `OHLC_MISSING`; 부분 제공·잘못된 high/low 등은 기존 #105 gate가 전체 입력을 차단한다. OHLC 공백 후 ATR은 상태를 초기화하고 연속14개 유효 TR을 다시 요구한다. 공백을 건너뛰어 smoothing하지 않는다.
- 유한 평균의 중간 합이 overflow하면 정규화한 평균으로 계산한다. 계산 결과가 비유한이거나 산술 실패면 해당 칸을 null(`CALCULATION_ERROR`)로 두고 독립적으로 계산 가능한 지표는 유지한다. NaN/Infinity·오류 원문·가격을 출력하지 않는다.
- `include_sma240`는 bool만 받는다. 다른 값은 `INVALID_DISPLAY_CONFIG`와 전체 `NOT_AVAILABLE`; true처럼 보이는 문자열·숫자를 변환하지 않는다.

## 검증·재현

`tests/test_technical_research_display.py`는 합성 데이터만 사용한다. 고정 fixture는 별도 C 구현 **TA-Lib 0.6.8**의 SMA/EMA/RSI/BBANDS/ATR와 독립 EMA MACD component로 생성했다. 종가는 `100+(i*7)%19+i//6` (i=0..259), high/low도 합성식이다. 실제 종목·공급자 응답·가격·Holdout은 없다. fixture의14개 component, 최초 유효값 양쪽 경계 및 후기 값을 대조한다. 비교 오차 `rel=abs=1e-10`은 부동소수점 **테스트 허용 오차**이며 투자 임계값이 아니다.

선형/무변동 수열의 손계산 값, RSI 실제0/undefined, 120/240 warm-up, 거래 세션의 시장 공통성, 미래 일봉 제외/가용시각 차단, 가격 basis·OHLC 공백, 큰 유한 숫자·overflow, RAM 불변성·repr·모델/네트워크 미호출도 검사한다.

```sh
cd implementation
python -m pytest tests/test_technical_research_display.py tests/test_technical_daily_input.py -q
python -m pytest -q
```

fixture 재생성은 별도 임시 환경에서만 `TA-Lib==0.6.8`, `numpy==2.5.3`을 설치한 뒤 아래를 실행한다. 제품/CI dependency에는 추가하지 않는다. 일반 테스트는 고정 JSON만 읽으며 TA-Lib·numpy 설치가 필요 없다.

```sh
python implementation/tools/technical_research_reference.py --output implementation/tests/fixtures/technical_research_reference.json
```

코드 PR은 완성·검증 후에도 사용자 병합 승인 대기다. GSQ-007의 개인 가격·파생값 공개 금지, FRED/ALFRED 차단, Holdout UNCONFIRMED·미사용, DART 등록 알림 전 착수 금지를 유지한다.
