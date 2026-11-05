# 계층 3 보유 봉의 표시 지표 연결

2026-11-05, 연구 전용. #469 `eecf69d6a43b67480c65bece8c4a02049bd9b699` 위에서 기존 계산을 재사용한다. 현재 공식 점수·운영 수집·화면 계약은 바꾸지 않는다.

## 상태와 이번 범위

| 항목 | 계산 | 자료 연결·실자료 검증 | 정기 갱신 / 화면 |
|---|---|---|---|
| 3·6·12개월 모멘텀, 6개월 표본 변동성 | #469 구현 완료 | 2018-02-16 보유 12계열 중 가격 산술 11; 기존 결과 참조 | 정기 갱신 미연결; Main 보드 판독 계약 완료 |
| 6개월 VWAP×v | #467/#469 원시 진단 구현 | 원시 10계열; 채택값 null. 새 공식 FAQ는 v와 VWAP 분모가 다를 수 있음을 명시 | 거래대금 채택·필터 변경 없음 |
| SMA5/20/60/120/240, EMA20, RSI14, MACD12/26/9, Bollinger20±2σ, ATR14 | GSQ-015 Python/JS 합성 검증 완료 | 이번 연구 어댑터가 기존 Python 커널을 보유 정규화 봉에 연결 | 실자료 운영 갱신 미연결; 합성/비공개 UI는 Main |
| 일봉 거래량·이전20봉 평균×1.5 참고 표시 | pattern-rules/1 구현 | 기존 `_volume_note`를 그대로 사용; 별도 모델 아님 | 조건부 참고, 패턴 확인 조건에 추가하지 않음 |
| 피벗·지지저항·박스돌파/이탈·이중바닥/천장 | pattern-rules/1 합성 구현 | 연속성·신원 검증 구간만 판단 가능; 실제 패턴 성공률 미검증 | 기존 보류 유지. 새 패턴·성과 정의 없음 |
| 사용자 노트·시나리오·차트 | Main 구현 | 개인 기기/합성 경로 | 이번 변경 없음 |

## 구현 계약

`research.technical_display.measure_display(rows, signal_day, series_id, symbol, evidence, source_kind)`:
`technical-offline-display/1`, `result_kind=RAW_SERIES_DIAGNOSTIC`, `price_basis=RAW`, `pit_status=NOT_VERIFIED`.
`raw_value`는 보유 계열 산술, `value`는 신원·실제 의존 창 분할 연속성·통화 근거 충족 시만 값이다. 과거 공시 가용성/고정 증권 ID/공식 신호를 이 값으로 입증하지 않는다. 지표별 `unit`, `null_reasons`, `observation_days`, `expected_days`, `window_start`, `window_end`, `input_start`, `history_count`를 기록한다. 미래 행은 제외하며 중간 누락을 건너뛰어 EMA/RSI를 만들지 않는다. raw close·raw OHLC만 읽으며 IEX 마지막 체결을 봉으로 변환하지 않는다.

GSQ-015 기간·seed·warm-up은 `technical/research_display.py`를 직접 사용한다. SMA240은 기본 OFF. 거래량 결손은 종가 지표를 막지 않는다. ATR은 온전한 raw OHLC, 거래량 메모는 현재와 이전20봉을 별도로 요구한다. 세션은 #469의 NYSE 달력을 재사용한다. 공식 합성 진입점의 `REAL_INPUT_NOT_AUTHORIZED`를 해제하지 않는다.

CLI: `python tools/technical_display_offline.py --input <private JSON> --output <outside-git JSON>`.
입력: `{signal_day, series:[{series_id, symbol, source_kind:NORMALIZED_PROVIDER_DAILY_BARS, rows, evidence}]}`. 출력은 Git 외부 0600, 덮어쓰기 금지, 네트워크 없음. 회사별 입력과 결과는 비공개.

합성 예: 250개 연속 NYSE 세션의 close=1..250, raw high=close+1, low=close−0.5, open=close, volume=100을 넣으면 마지막 SMA20=240.5, RSI14=100, MACD12/26=7, signal=7, histogram=0. `identity_status=UNKNOWN`이면 raw 값은 남고 채택 value=null이다. 합성 예는 실자료 성과가 아니다.

SMA/Bollinger는 실제 마지막 N봉에만 기업행사 근거를 요구한다. EMA/RSI/MACD/ATR의 재귀 seed는 전체 입력에 의존하므로 `input_start`부터의 근거가 필요하다. source_kind가 없거나 IEX_LAST_TRADE이면 DAILY_BAR_SOURCE_REQUIRED로 거절한다.

정규화 provenance는 #469와 같은 요청/반환 symbol, direct-symbol asof, raw basis, NY 일봉 시작 timestamp, 원문 SHA, 거래세션을 확인한다. 현재 거래량은 S행이 없으면 null이고 실제 마지막 관측일만 표시한다. 거래량 메모의 기업행사 근거 창은 현재와 이전20봉, 단일 거래량은 S 한 세션이다. 독립 검토에서 이 세 경계(이전 날짜 거래량, 혼합 symbol, 거래량 근거 창)를 지적받아 회귀 시험으로 수정했다.

## 초기화·채택 조건 분리와 기존 근거 연결

초기화와 최소 이력은 [GSQ-015 구현 계약](../technical_live_data/RESEARCH_DISPLAY_INDICATORS_V1.md)의 승인값이다. 최소 세션 수는 최초 값이 생기는 경계이며, 전체 입력을 그 길이로 잘라 다시 seed하라는 뜻이 아니다.

| 지표 | 최초 값의 최소 세션 | 의존 구간 / 조건 |
|---|---:|---|
| SMA5/20/60/120 | 5/20/60/120 | 마지막 N개 종가; SMA240은 계속 기본 OFF |
| EMA20 | 20 | 전체 입력 첫20종가 평균 seed, 이후 재귀 |
| RSI14 | 15 | 전체 입력 첫14변화 gain/loss 평균 seed, 이후 Wilder |
| MACD12/26 | 26 | 전체 입력의 독립 SMA-seed EMA12−EMA26 |
| MACD signal / histogram | 34 | 첫9개 유효 MACD 평균 seed / 두 값의 차 |
| Bollinger20 | 20 | 마지막20종가; 모집단 표준편차 |
| ATR14 | 15 | 첫14개 TR 평균 seed, 이후 Wilder. OHLC 공백은 기존 규칙대로 재초기화 |

모든 재귀 지표는 보유 입력 시작일을 유지한다. 과거의 `no_split_start`가 표시 계산보다 짧은 모멘텀 창으로 전달된 한 계열에 대해, [기존 전체 분할 이력 확인 기록](AMD_EV_SALES_CALCULATED_20261103.md#공식-문서로-해소한-입력)을 같은 문서 재구성 수준으로 전체 입력 창에 연결했다. 첫 봉·seed·산식·최소 이력·원시 봉은 바꾸지 않았다. 원래 추출 바이트는 미복구이며 이 연결은 새로운 원문 확인, PIT 가용성 검증, 고정 증권 ID 확보가 아니다.

동일 2018-02-16, 요청12계열에서 13개 표시 component의 원시 유효 수는 각각11로 동일하다. 기존 SMA4개·Bollinger3개는 채택각1 유지, EMA·RSI·MACD3개·ATR의 6개 component만 채택각0→1이다. 채택은 **비공개 연구 문서 재구성 계약**에서의 값이다. 초기화 구간 전체가 확인된 공식 운영 가격이나 순위로 승격하지 않는다. 156칸(유효143, null13)의 원시 값과 모든 의존 창은 이전 결과와 정확히 같고, 연구 채택6칸만 증가했다.

현재 각 component의 상호 배타 상태는 `VALUE=1`, `DIAGNOSTIC=10`, `NOT_COMPUTED=1`이다. 미채택11계열의 중첩 사유는 신원 미확인11, 무분할 근거 미확인11, 빈 가격계열1이다. 정상 계산된11계열은 각각284봉으로 warm-up 충족; 빈계열1은 warm-up 평가 자체가 불가하다. 날짜 누락을 채우거나 신원·분할 조건을 완화하지 않았다. 새 고정 증권 ID와 순위는 계속0이다.

## Main의 상태 판독

기존 `technical-offline-display/1`의 `raw_value`, `value`, `null_reasons`는 보존하고 `readiness`를 부가한다. Main은 숫자의 truthiness가 아닌 null 여부로 판독한다. 유효0은 값이다.

| 필드 | 의미 |
|---|---|
| `readiness.schema` | `technical-display-readiness/1` |
| `readiness.metrics.<id>.state` | `VALUE`: 채택 `value`; `DIAGNOSTIC`: raw만 있음; `NOT_COMPUTED`: raw도 null |
| `.initialization` | 승인된 method, policy, 최초 `input_start`; rolling 지표와 전체 입력 seed 구분 |
| `.warmup` | `minimum_sessions`, 종가 `observed_sessions`, `READY/INSUFFICIENT/NOT_EVALUATED`; ATR의 재초기화 상태는 기존 커널 사유를 따름 |
| `.continuity`, `.adjustment`, `.identity` | 세션/종가 결손, 실제 의존 창과 무분할 근거 범위, 문서 신원과 고정 ID를 별도로 표시 |
| `.block_reasons` | 기존 `null_reasons` 그대로. 사유별 수는 중첩되므로 합산 분모로 쓰지 않음 |
| `readiness.as_of` | 지표 평가 세션; 자료 발표·가용 시각이 아님 |
| `availability_status`, `source_available_at` | 현재 `NOT_VERIFIED`, null. 역사 자료 수령/사용 가능 시각을 날짜에서 추정하지 않음 |
| `stale_status`, `stale_reason` | 현재 `UNKNOWN`, `UPDATE_SCHEDULE_NOT_CONNECTED`. 제안된 갱신 기준을 운영 승인으로 간주하지 않음 |

합성 예: 같은250봉에서 EMA20의 raw=240.5, 분할 근거가 마지막120봉만 덮으면 `value=null`, `state=DIAGNOSTIC`, `warmup=READY`, `adjustment=UNCONFIRMED`다. 보유 문서가 실제 전체250봉을 덮는 경우에만 그 근거를 연결하면 raw=240.5 그대로 `value=240.5`, `state=VALUE`가 된다. 신원·근거 확인 없이 기간만 자르는 전환은 없다. 가격계열 자체가 비면 `NOT_COMPUTED`; 평탄한35봉의 RSI는 `ZERO_TOTAL_CHANGE`이고 warm-up 부족과 구별한다. 모든 예에서 과거 가용성과 stale은 별도 미확인이다.

VWAP 체결범위 제한과 종가×거래량 대용치 구분은 기존 판정을 유지한다. 이번 입력 근거 연결로 거래대금 채택값을 채우지 않는다.
