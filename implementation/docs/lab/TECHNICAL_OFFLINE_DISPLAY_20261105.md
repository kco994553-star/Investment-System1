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

`research.technical_display.measure_display(rows, signal_day, series_id, evidence, source_kind)`:
`technical-offline-display/1`, `result_kind=RAW_SERIES_DIAGNOSTIC`, `price_basis=RAW`, `pit_status=NOT_VERIFIED`.
`raw_value`는 보유 계열 산술, `value`는 신원·실제 의존 창 분할 연속성·통화 근거 충족 시만 값이다. 과거 공시 가용성/고정 증권 ID/공식 신호를 이 값으로 입증하지 않는다. 지표별 `unit`, `null_reasons`, `observation_days`, `expected_days`, `window_start`, `window_end`, `input_start`, `history_count`를 기록한다. 미래 행은 제외하며 중간 누락을 건너뛰어 EMA/RSI를 만들지 않는다. raw close·raw OHLC만 읽으며 IEX 마지막 체결을 봉으로 변환하지 않는다.

GSQ-015 기간·seed·warm-up은 `technical/research_display.py`를 직접 사용한다. SMA240은 기본 OFF. 거래량 결손은 종가 지표를 막지 않는다. ATR은 온전한 raw OHLC, 거래량 메모는 현재와 이전20봉을 별도로 요구한다. 세션은 #469의 NYSE 달력을 재사용한다. 공식 합성 진입점의 `REAL_INPUT_NOT_AUTHORIZED`를 해제하지 않는다.

CLI: `python tools/technical_display_offline.py --input <private JSON> --output <outside-git JSON>`.
입력: `{signal_day, series:[{series_id, source_kind:NORMALIZED_PROVIDER_DAILY_BARS, rows, evidence}]}`. 출력은 Git 외부 0600, 덮어쓰기 금지, 네트워크 없음. 회사별 입력과 결과는 비공개.

합성 예: 250개 연속 NYSE 세션의 close=1..250, raw high=close+1, low=close−0.5, open=close, volume=100을 넣으면 마지막 SMA20=240.5, RSI14=100, MACD12/26=7, signal=7, histogram=0. `identity_status=UNKNOWN`이면 raw 값은 남고 채택 value=null이다. 합성 예는 실자료 성과가 아니다.

SMA/Bollinger는 실제 마지막 N봉에만 기업행사 근거를 요구한다. EMA/RSI/MACD/ATR의 재귀 seed는 전체 입력에 의존하므로 `input_start`부터의 근거가 필요하다. source_kind가 없거나 IEX_LAST_TRADE이면 DAILY_BAR_SOURCE_REQUIRED로 거절한다.
