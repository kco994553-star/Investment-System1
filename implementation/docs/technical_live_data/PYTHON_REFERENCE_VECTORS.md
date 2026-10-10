# Research 표시 지표 v1: Python 참조와 코덱1 테스트 벡터

이 도구는 GSQ-015의 표시 전용 지표를 합성 데이터로 대조하는 독립 참조 구현이다. 앱에서 import하지 않으며 Model·TSV·QGV 입력이나 공개 serializer에 연결하지 않는다. 실제 가격·파일 입력·네트워크 옵션은 없고 Python 표준 라이브러리만 사용한다.

## 파일과 재생성

- 참조 도구: [`../../tools/research_display_python_reference.py`](../../tools/research_display_python_reference.py)
- 전체 벡터: [`../../tests/fixtures/research_display_python_vectors.json`](../../tests/fixtures/research_display_python_vectors.json)
- Python 계약 테스트: [`../../tests/test_research_display_python_reference.py`](../../tests/test_research_display_python_reference.py)
- 알려진 참조값: [`../../tests/fixtures/technical_research_reference.json`](../../tests/fixtures/technical_research_reference.json) — TA-Lib 0.6.8로 만든 합성 체크포인트 336개를 모두 대조한다. TA-Lib는 실행 의존성이 아니다.

저장소의 `implementation/`에서 실행한다.

```sh
python tools/research_display_python_reference.py > tests/fixtures/research_display_python_vectors.json
python -m pytest -q tests/test_research_display_python_reference.py
```

`reference_vectors()`는 인자 없이 고정된 합성 사례의 새 복사본을 반환한다. CLI는 같은 JSON을 stdout으로 출력한다. `--input` 등 외부 데이터 인자는 거부한다.

## JSON 계약과 JavaScript 대조

문서 버전은 `schema_version=1`, `version=v1`이다. 루트·사례·결과·모든 지표에 `role=RESEARCH_DISPLAY_ONLY`를 붙인다. `cases[]`는 `case_id`, `input.bars`, `input.options`, `expected`를 갖는다. JavaScript는 변환 없이 `ResearchIndicators.calculate(input.bars, input.options)`를 호출할 수 있다.

`expected.indicators[]`의 순서는 SMA 5/20/60/120/240, EMA 20, RSI 14, MACD line/signal/histogram, Bollinger middle/upper/lower, ATR 14이다. 각 `values[]`와 `unavailable_reasons[]`는 입력 길이와 같고, 거래일 인덱스별로 대조한다. `null`에는 이유가 있으며 0은 유효한 계산값일 때만 출력한다. 최신 인덱스가 `null`이면 `latest_state=NOT_AVAILABLE`이다.

벡터는 선택 SMA 240까지 대조하므로 `input.options.includeSma240=true`이다. 실제 기본값은 루트 `display_defaults.include_sma240=false`, 지표 `SMA_240.default_visible=false`로 보존한다. 다른 SMA 5/20/60/120은 기본 표시한다.

코덱1은 각 사례의 모든 지표·인덱스를 대조한다. `null`과 이유·역할·기본 표시·상태는 정확히 비교하고, 숫자는 기존 JavaScript 참조 테스트와 같은 `abs(actual - expected) <= 1e-10 * max(1, abs(expected))`를 사용한다. 이 허용 오차는 부동소수점 비교용이며 모델 임계값이 아니다.

```js
for (const sample of vectors.cases) {
  const actual = ResearchIndicators.calculate(sample.input.bars, sample.input.options);
  // sample.expected와 role/state/price_basis/pit_status 및 모든 지표 배열을 비교한다.
}
```

## 초기값과 결측

| 항목 | 첫 유효 인덱스(0부터) | 규칙 |
| --- | --- | --- |
| SMA n | n−1 | 최근 n개 거래일의 산술평균 |
| EMA 20 | 19 | 첫 20개 SMA 초기값, 이후 α=2/21 |
| RSI 14 | 14 | 첫 14개 종가 변화의 평균 gain/loss, 이후 Wilder |
| MACD 12/26 | 25 | 전체 이력에서 각각 초기화한 EMA12−EMA26 |
| MACD signal/histogram | 33 | 유효 MACD 9개의 SMA로 EMA9 초기화 |
| Bollinger 20·2σ | 19 | 20개 종가의 모집단 표준편차 |
| ATR 14 | 14 | 인덱스 1부터 이전 종가를 쓴 TR 14개 평균, 이후 Wilder |

초기값 이전은 `null/WARMUP`이다. RSI에서 gain+loss가 모두 0인 평탄 구간은 `null/ZERO_TOTAL_CHANGE`로 남긴다. 상승 RSI 100, 하락 RSI 0과 구분하며, TA-Lib의 평탄 RSI 0을 결측 대체로 채택하지 않는다.

누락·진행 중인 세션은 초기값을 다시 누적하고 앞뒤를 연결하지 않는다. ATR은 raw OHLC와 raw close가 같은 기준일 때만 계산하며 adjusted close를 쓰는 사례는 모든 ATR을 `null/OHLC_BASIS_UNCONFIRMED`로 둔다. 미국·한국·일본 모두 거래일 인덱스와 같은 초기화 규칙을 적용한다. 벡터의 2030년 timestamp는 합성 인덱스 정렬값이며 실제 기간이나 Holdout 선택이 아니다.

11개 사례는 260거래일 참조 이력, 평탄·상승·하락, 빈 이력·1일·14일, Wilder 재귀, 누락 세션, adjusted 기준, 마지막 미완료 세션이다. 원천 입력과 전 인덱스 출력이 포함돼 부분 체크포인트 밖의 구현 차이도 확인할 수 있다.
