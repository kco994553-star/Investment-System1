# 생산자별 평가일 계약 — signal_day (Main 제안, Codex 확인 대기)

작성 2026-11-08 Main. 근거: 오너 2026-11-08 「통합 결과 수령」 2항.
- "Codex와 생산자별 평가일 계약을 맞춰 signal_day 연결."
- "평가일을 가격일·생성일에서 추정하지 않는다."

이 문서는 병합·배포·신규 취득 승인이 아니다.

## 1. 원칙

- 기술 조건 필터의 결합 키는 `(signal_day, security_id)`다(Codex #515·#516 `technical_filter_join`).
- `signal_day`는 **그 행을 만든 생산자가 평가일이라고 명시한 필드**에서만 읽는다.
- 다음 값은 평가일로 쓰지 않는다:
  - 가격 기준일(`price_basis_date`·`data_asof`)
  - 수집·생성·계산 시각(`collected_at`·`generated_at`·`calculated_at`)
  - 재무 입력 기준(`as_of`·`financial_input_as_of`)
  - 게시 시각
- 생산자 필드가 없으면 `null`로 두고, 사유를 따로 보인다.

## 2. 생산자별 필드 (Codex 코드에서 확인한 것)

| 생산자 · 계약 | 평가일 필드 | 근거 | Main 읽기 |
| --- | --- | --- | --- |
| 공통 분류 `common-classification-view/1` | `valuation_date` | `records.resolve` | 읽음 (분류 평가일) |
| 공통 분류 기술 투영 `common-classification-technical/1` 안의 보드 `technical-leaderboard/1` | 보드 `signal_day` = view `valuation_date` | `technical_macro.py` 99·182·221행: 측정값의 `signal_day`가 다르면 넣지 않음 | 읽음 (보드 평가일) |
| 그룹 명부 `technical-filter-membership/1` | `context.signal_day` | `group_join.build_group_manifest` | 읽음 |
| 매크로 투영 `common-classification-macro/1` | `valuation_date` | `technical_macro.py` 247행 | 읽음 |
| Q/G 연결 `common-classification-qgv-links/1` | `valuation_date` | CLI 출력, `preview_identity`로 미리보기와 묶임 | 읽음 (2.2.7 대조) |
| 섹터 QGV 미리보기 `sector-qgv-preview/1` | `valuation_date` (모든 `result_rows`에 공통) | 보관 묶음 최상위 필드(`as_of`는 재무 입력 기준 시각으로 따로 있음) | **확인 요청 ①** |
| 비공개 KIS 측정 `kis-technical-measures/1`·분석 | `evaluation_day`(+ `signal_day`) | `private_technical_board.measure_contract` | 비공개 화면에만 표시 |
| 공개 QGV 리더보드 (`qgv-official.json`·`sec-qgv2.json`) | **없음** | 행·파일에 평가일 필드가 없음. `as_of`는 SEC 재무 입력 기준 | `null` 유지, **확인 요청 ②** |

## 3. Main이 이번에 바꾼 것

- 그룹 결합 `/2`(`tech-screen.js` `joinGroupRows`)가 날짜 불일치로 거부할 때 보드 평가일과 행 평가일을 함께 넘긴다.
  - 고치기 전에는 화면에 "보드 undefined · QGV undefined"가 보였다.
- 행 평가일이 없으면 다음 문구로 보인다. 두 날짜가 서로 다른 경우와 따로 보인다.
  > 평가일 불일치 · 보드 (날짜) · QGV 행 평가일 미제공(생산자 평가일 필드 없음 · 가격일·생성일로 추정 안 함)
- `qgv.js` `rowRecord`는 `signal_day: null`을 그대로 둔다. ②가 확정되기 전에는 다른 필드에서 채우지 않는다.
- 시험: `web_app_group_join_node_test.js` "signal_day" 항목(두 경우, `undefined` 없음).

## 4. Codex에 확인할 것

1. **`sector-qgv-preview/1`**
   - `valuation_date`가 모든 `result_rows`의 평가일인가?
   - 그렇다면 Main은 이 미리보기에서 온 행의 `signal_day`를 이 값으로 둔다. 이 값은 같은 `preview_identity`로 묶인 Q/G 연결과 같아야 하며, 다르면 거부한다.
2. **공개 QGV 리더보드 생산자**
   - 평가일 필드를 명시적으로 내보낼 계획이 있는가? 예를 들면 행 또는 파일의 `valuation_date`.
   - 계획이 없다면 이 리더보드 행은 기술 결합 대상이 아니다(`signal_day` null 유지).
3. **같은 날의 정의**
   - 공통 분류 기술 보드의 `signal_day`(= 분류 `valuation_date`)와 QGV 행의 평가일은 같은 거래일 문자열로 직접 비교하는가?
   - 휴장일 처리는 보드 쪽 `schedule.is_session`만 따르는가?

**결합이 실제로 생기려면** 평가일 외에 검증된 `security_id`가 있어야 한다. 현재는 0건이다(보관 묶음 기술 투영 504행 중 0). 평가일 계약이 맞아도 증권 근거가 없으면 결합은 계속 거부된다.
