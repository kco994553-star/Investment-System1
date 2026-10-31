# 공식 V 옆 "마지막 체결 시각" — 게시본 필드 계약 (2026-10-31)

소유자 결정(10/31, 원문): 「소형주 IEX 체결 지연(약 2~3%가 30분 이상 묵은 값)은 해당 종목의 V 옆에 "마지막 체결 시각"을 표시하는 것으로 처리하라. 계산은 바꾸지 않는다.」

이 문서가 계약의 한 곳이다. 코드: `src/investment_system/qgv/qgv_official.py`(검증기 `require_qgv_official`), `product/web_assets/qgv-official.js`(JS 쌍둥이 검증기 + 표시 규칙 `lastTrade` / `lastTradeText`). JS = Python 판정은 `tests/fixtures/qgv_official_vectors_v1.json`의 `last_trade_*` · `session_close_*` 사례로 고정한다.

## 1. 순서와 이 PR의 범위

설계 순서(비공개 설계 §17.6): ① IEX 파서가 정규장 마지막 정수주(round-lot) 체결 시각도 준다(메모리만, 가격과 같은 규칙) ② 독자·검증기가 새 필드를 받아들인다 ③ 그다음에 게시기가 행마다 시각을 쓴다 ④ 화면은 마감 30분 이상 전 체결인 행에만 V 옆에 시각을 보인다. 게시본 형식이 바뀌므로 ②가 먼저 나간다.

**이 PR = ② + ④.** 게시기·워크플로·V 계산은 바꾸지 않는다. 지금 게시본에는 두 키가 없으므로 화면에는 아무것도 새로 나오지 않는다(③이 들어온 뒤부터 보인다).

## 2. 필드

| 위치 | 키 | 형식 | 언제 있나 |
| --- | --- | --- | --- |
| 파일 | `times.price_session_close_at` | `YYYY-MM-DDTHH:MM:SSZ`(UTC, 초 단위, 소수점 없음) | 선택. 행 시각이 하나라도 있으면 반드시 있어야 한다 |
| 행 | `rows.<code>.v_last_trade_at` | 같은 형식 | 선택. 그 행에 V가 있을 때만(아래 규칙). `null`은 쓰지 않는다(없으면 키 자체가 없다) |

- `v_last_trade_at` = 그 행 V에 쓰인 가격의 체결 시각: IEX TOPS 1.6 정규장(확장 시간 플래그 없음, 단주 플래그 없음) 마지막 정수주 체결의 타임스탬프를 초 단위로 버림. 가격이 아니다. 가격·가격 해시·월말가는 계속 게시하지 않는다.
- `price_session_close_at` = `times.price_basis_date` 그날 정규장 마감 시각. 뉴욕 16:00:00, 조기 폐장일은 13:00:00.
- 두 키 말고 다른 키는 여전히 거부한다(`TIMES_OPTIONAL_KEYS`, `ROW_OPTIONAL_KEYS` 정확히 이 둘). 두 키가 없는 옛 파일은 그대로 유효하다.

### 왜 파일 수준 마감 시각인가(행별 표시 플래그가 아니라)

- 규칙이 한 곳에 남는다: "30분 이상 전"은 화면 쪽 `lastTrade` 하나가 `마감 − 체결 ≥ 30분`으로 판단하고, 게시본은 사실(체결 시각, 그날 마감)만 싣는다. 기준(30분)을 바꿔도 게시본 형식은 그대로다.
- 조기 폐장을 바르게 처리한다: 조기 폐장일에는 13:00이 기준이다. 지금 운영 파이프라인은 반일장을 따로 알지 못한다(`providers/iex_hist.py`는 09:30–16:00 창 + TOPS 확장 시간 플래그로 13:00 뒤 체결을 거른다). 그래서 16:00을 화면에 박아 두면 조기 폐장일의 12:59 체결이 "3시간 묵음"으로 잘못 보인다. 마감 시각을 게시본이 말하게 해 두면 ③이 그 값을 정한다.
- 검증 가능하다: 마감 시각이 있으면 행 시각이 그날 정규장 안인지(09:30 이상, 마감 미만) 검증기가 확인할 수 있다. 행별 플래그는 검증할 근거가 없다.

## 3. 검증 규칙(Python과 JS가 같다)

1. 키 집합: `times`는 기존 6개 + 선택 `price_session_close_at`, 행은 기존 24개 + 선택 `v_last_trade_at`. 그 밖의 키는 `OFFICIAL_INVALID`.
2. `price_session_close_at`(있을 때): 정확히 `YYYY-MM-DDTHH:MM:SSZ`, 실제 달력 시각(02-30, 24:00, 60초 거부), 날짜 부분 = `price_basis_date`, 뉴욕(`America/New_York`, 서머타임 포함) 날짜 = `price_basis_date`, 뉴욕 벽시계가 정확히 13:00:00 또는 16:00:00. 어느 날이 조기 폐장인지는 검증기가 따로 달력을 두지 않는다(게시기가 말한 값을 형식으로만 묶는다).
3. `v_last_trade_at`(있을 때): 마감 시각이 있어야 하고, 그 행의 V 축 점수가 유한수이고 `price_status = SUPPLIED`여야 하며, 같은 형식·실제 시각, 날짜 부분과 뉴욕 날짜 = `price_basis_date`, 뉴욕 09:30:00 이상, 마감 시각 **미만**.
4. JS는 뉴욕 시각을 `ForwardValidation.eastern`(이미 `nyNow`가 쓰는 시계)으로 구한다. 그 모듈이 없으면 두 키가 있는 파일만 `OFFICIAL_UNAVAILABLE`이고 옛 파일은 그대로 읽힌다.
5. 금지 키(`FORBIDDEN_KEYS`)와 Pages 가드 민감 키는 바뀌지 않았다. 두 키 이름은 어느 쪽에도 걸리지 않으며, 가드의 내용 검사는 계속 엄격 검증기 하나다.

## 4. 화면 규칙(④)

- 규칙 하나: `QgvOfficial.lastTrade(payload, key)` → `{at, ny_time 'HH:MM', minutes_before_close, note}`; `note = (마감 − 체결) ≥ 30분`(정확히 30분이면 표시). `lastTradeText(info)` = `마지막 체결 HH:MM (뉴욕)`(영문 `last trade HH:MM (New York)`), `note`가 아니면 `null` → 아무것도 보이지 않는다. 키가 없거나(옛 게시본) 그 행에 V가 없으면 표시 없음.
- V 값·순위·정렬 값·적용 범위 수는 바뀌지 않는다(테스트로 고정). 시각은 행의 표시용 메타데이터일 뿐 점수가 읽지 않는다.
- 표시 위치(작은 회색 글, 기존 보조 글 규칙 DC-25/DC-26):
  - 새 앱: 1.1 리더보드 V 칸(PC: 값 아래 한 줄, 모바일 390px: 행 아래 `Q · G · V` 줄의 V 뒤), 기업 진입 QGV 카드(V 막대 아래 `V · 마지막 체결 HH:MM (뉴욕)`). 층 `IS2.qgv` 행의 `v_last_trade.text`.
  - 옛 화면: S06 리더보드 행 상세 한 줄(`QgvScores.summaryText`: `… · V 48.2 · 마지막 체결 HH:MM (뉴욕) · 산출 요인 …`)과 일부 축 배지, 기업 상세 QGV 카드 V 칸, Universe 기업 페이지 V 줄, 스탯창(레이더) 상세 표의 기업 V 칸, 홈 검색 결과 QGV 카드(막대 아래). 모두 `QgvScores.lastTradeText` / `lastTradeHtml`.
  - 넣지 않은 곳: V 커버리지 패널(개수만 있고 행별 V가 없다), TARGET v1 초안 표(기기에 저장되는 초안 형식이 바뀌므로 11/16 PR과 함께 결정), 일일 보고서 내보내기(화면 밖 문서).

## 5. 게시기 PR(③)에 남기는 메모

- 체결 시각의 출처는 이미 있다: `tools/iex_tops/iex_last_trade.c`가 기호마다 `SYMBOL status price_e4 timestamp_ns …`를 출력하고, `ROUND` 줄의 `timestamp_ns`가 바로 그 가격의 체결 시각(UTC 나노초)이다. 지금 `iex_hist.parse_rows`는 상태와 가격만 남기고 이 열을 버린다. ③은 이 열을 가격과 같은 규칙(메모리만, 로그·예외·파일에 쓰지 않음)으로 `IexDay`에 붙이고, 게시할 때 초 단위로 버려 `v_last_trade_at`에 쓴다. V가 있는 행에만 쓴다.
- 마감 시각: 하드코딩 16:00이 아니라 그날의 실제 마감이어야 한다. 제안: 같은 TOPS 파일의 System Event 메시지(정규장 끝 이벤트)의 시각을 파서가 함께 내고, 게시기는 그 뉴욕 벽시계가 16:00 또는 13:00일 때만 그 값을 `price_session_close_at`으로 쓴다(TOPS 1.6 명세와 실제 파일로 먼저 확인할 것; 첫 실제 조기 폐장은 2026-11-27). 이벤트가 없거나 두 시각이 아니면 **두 키를 모두 쓰지 않는다**(게시 실패가 아니라 표시 없음으로 닫힌다). 연구용 NYSE 조기 폐장 표(`research/pit_filings.py`)는 교차 확인용 후보일 뿐, 운영 경로가 연구 모듈을 읽는 것은 따로 승인이 필요하다.
- `publication_id` 매니페스트: 지금 매니페스트에는 시각이 없다. 같은 가격 묶음이면 같은 파일에서 같은 시각이 나오지만, 같은 `publication_id`는 같은 바이트여야 하므로(배포 검사 "CHANGED, refused") ③은 행 시각과 마감 시각(또는 그 해시)을 매니페스트에 넣을지 정해야 한다.
- 크기: 약 520행 × 약 40B ≈ 20KB 늘어난다(현재 약 1.06MiB, 상한 2MiB).
- 설계 문서 `docs/qgv_scoring_standard/CENTRAL_V_PUBLICATION_DESIGN_20261018.md` §4-2의 "종목별 가격 시각 — 절대 아니오" 줄에서 이 한 필드(체결 시각, 가격 아님)만 소유자 결정 2026-10-31로 공개로 바뀐다. 가격·월말가·가격 해시·HMAC 금지는 그대로다.
