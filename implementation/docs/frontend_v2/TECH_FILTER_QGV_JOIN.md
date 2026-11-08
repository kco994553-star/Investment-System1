# 1.1.8 기술 조건 필터 — QGV 리더보드 결합 (Codex #515 계약 소비)

작성 2026-11-07 · Main. 근거는 오너 감사(11/07)와 같은 날 오너 지시다. "#515 계약과 반례를 그대로 쓰고, 티커 문자열로 대신 결합하지 않는다. 평가일·기업 ID·검증된 증권 ID·유효기간을 확인한다."

Main은 Codex PR #515(`research/technical-filter-join-20261107`, `b6fd0112`)의 결합 계약을 그대로 소비한다. Main이 따로 만든 계약은 없다. 이전 판에서 제안했던 `tech-qgv-security-map/0`은 버렸다.

## 1. 계약 (#515 `TECHNICAL_FILTER_JOIN_20261107.md`)

- 결합 키는 정확히 `(signal_day, security_id)`다.
- QGV 행마다 `signal_day`(계산 평가일)와 `security_id`(검증된 고정 증권 ID)가 있어야 한다. 행의 `id`(발행사 ID), `ticker`, `code`는 결합 키가 아니다.
- 증권 링크 항목: `series_id`, `security_id`, `identifier_type`, `reference`, `valid_from`, `valid_to`, `issuer_id`, `symbol`, `share_class`, `identity_status`, `identity_reference`.
  - `identity_status`는 `CONFIRMED`여야 한다.
  - 유효기간은 양 끝 날짜를 포함한다. 평가일에 유효한 링크가 정확히 하나여야 한다.
  - 링크의 `issuer_id`는 행 `id`와, `symbol`은 행 `ticker`(보드에 symbol이 있으면 그것과도)와, `series_id`는 보드 시리즈와 같아야 한다.
- 행이나 링크 하나라도 틀리면 결합 전체를 거부한다. 필터에서 빠질 행도 먼저 검사한다.

## 2. Main 구현

- `web_app/tech-screen.js::joinRows`는 `join_filtered_rows`를 순수 JS로 옮긴 것이다. 검사 순서와 사유 코드가 같다.
- Main만의 코드가 하나 있다. 원천에 링크 자료가 아예 없으면 `SECURITY_LINKS_NOT_CONNECTED`다.
- `web_app/qgv.js::rowRecord`는 `signal_day`와 `security_id`를 내지만, 지금은 근거가 없어 둘 다 null이다. `company_id`, 티커, 코드, `as_of`, 가격 기준일에서 만들지 않는다.
- QGV 평가일: #515는 QGV 행의 `signal_day`가 계산 평가일이라고만 정하고, 기존 Main 필드 중 어느 것인지는 정하지 않는다. 그래서 Main은 공식 게시본의 `price_basis_date`도 평가일로 쓰지 않는다. 이전 판의 선택은 버렸다.
- 결합이 안 되면 리더보드 표에 기술 조건을 적용하지 않는다. 표는 그대로 두고 블록에 사유를 적는다(`data-tf-join`, `data-na`에 코드).
- 문구는 "리더보드 표에 적용할 수 없음 · (사유) · … · 리더보드는 기술 조건 없이 그대로"다.

## 3. 사유 코드와 화면 문구

| 코드 | 문구 |
|---|---|
| `SECURITY_LINKS_NOT_CONNECTED` (Main) | 고정 증권 매핑 자료 미연결 · 매핑이 오기 전에는 결합하지 않음 |
| `JOIN_DATA_KIND_REQUIRED` | 자료 종류 표시 없음(합성 또는 보관 입력) |
| `TECHNICAL_BOARD_SCHEMA_MISMATCH` | 기술 보드 스키마 불일치 |
| `INVALID_SESSION_DATE` | 평가일 없음 또는 형식 오류 · QGV 행에 계산 평가일이 없음 |
| `GROUP_MEMBERSHIP_UNCONFIRMED` | 비교 그룹 구성원 미확인 |
| `TECHNICAL_METRICS_MISMATCH` | 기술 지표 목록 불일치 |
| `PERMANENT_SECURITY_ID_REQUIRED` | 고정 증권 ID 없음 |
| `REQUEST_SERIES_ID_REQUIRED` | 시리즈 ID 없음 |
| `DUPLICATE_TECHNICAL_KEY` | 기술 보드에 같은 증권이 두 번 |
| `TECHNICAL_IDENTITY_MISMATCH` | 지표 사이 증권·시리즈 불일치 |
| `FIXED_SECURITY_LINK_EVIDENCE_REQUIRED` | 증권 매핑 근거 없음 |
| `FIXED_SECURITY_LINK_UNCONFIRMED` | 증권 신원 미확인 |
| `ISSUER_OR_TICKER_IS_NOT_SECURITY_ID` | 발행사 ID·티커·코드는 증권 ID가 아님 |
| `SYNTHETIC_SECURITY_ID_ON_RETAINED_INPUT` | 합성 증권 ID가 실자료에 섞임 |
| `INVALID_SECURITY_LINK_RANGE` | 매핑 유효기간 오류(시작이 끝보다 늦음) |
| `DUPLICATE_SECURITY_LINK` | 매핑 중복 · 평가일에 겹치는 매핑 |
| `SIGNAL_DAY_MISMATCH` | 평가일 불일치 · 보드 (날짜) · QGV (날짜) |
| `DUPLICATE_QGV_KEY` | QGV 결합 키 중복(같은 평가일·같은 증권 두 행) |
| `SECURITY_ID_NOT_IN_BOARD` | 보드에 없는 증권 · 같은 티커의 다른 증권 또는 다른 종류주 |
| `FIXED_SECURITY_LINK_MISSING` | 매핑 없음 |
| `SECURITY_LINK_OUTSIDE_SIGNAL_DAY` | 매핑 유효기간 밖(만료 또는 아직 유효 전) |
| `SERIES_LINK_MISMATCH` | 매핑 시리즈 불일치 |
| `ISSUER_LINK_MISMATCH` | 발행사 불일치(QGV 행 id ≠ 매핑 발행사) |
| `SYMBOL_LINK_MISMATCH` | 티커 불일치(QGV 행·보드 ≠ 매핑 티커) |

## 4. 시험

- #515 fixture 두 파일을 바이트 그대로 `implementation/tests/fixtures/technical_filter_join_v1/`에 복사했다.
  - git blob이 #515와 같고, sha256을 고정했다(`inputs.json` 8411e823…, `expectations.json` f395414d…).
  - 내용은 고치지 않는다.
- `tools/web_app_tech_filter_node_test.js`는 이 두 파일을 직접 읽는다.
  - 시나리오 11개 모두 Codex 기대와 같다.
  - 성공이면 원래 QGV 순위 4·9, 점수 80·70, 모집단 10이 그대로다.
  - #515의 추가 경계 10개와 과거 링크 시험도 같은 코드로 확인한다.
- `tools/web_app_tech_filter_browser_test.js`(1440·390)는 다음을 확인한다.
  - 거부: 링크 없음, 오늘의 행(평가일 없음), 다른 날짜, 같은 티커·다른 증권, 다른 종류주, 링크 누락, 링크 중복. 모두 표가 그대로이고 사유가 보인다.
  - 성공: 시험 안에서만 만든 합성 키와 링크로 PASS 행만 QGV 순으로 남는다.

## 5. 실자료 연결에 아직 없는 것

- QGV 행마다 근거가 있는 `signal_day`(QGV 계산 평가일)와 `security_id`. 지금은 어느 공개 파일에도 없다.
- Universe504 전체에 대한 `CONFIRMED` 증권 링크 파일과 그 공개 경로. 원천은 지금 `NONE`(`security_links: null`)이다.
- 공통 분류 기록으로 확정된 보드 그룹의 전체 구성원 행(6절 3번). 그룹 안 행 하나라도 보드에 없으면 `SECURITY_ID_NOT_IN_BOARD`로 전체가 거부된다.
- 실자료 `data_kind`(`RETAINED_INPUT`) 표시.

이것이 오기 전에는 아무것도 결합하지 않는다.

## 5a. 결합 반례 (오너 2026-11-08, Codex #437 6714613662)

`tools/technical_filter_join_main_cases.py`가 Codex 고정 입력(`original_board`, `same_date_same_security`)에서 행·링크만 바꾼 11사례를
Codex `join_filtered_rows`로 돌려 `tests/fixtures/technical_filter_join_main/cases.json`에 기대 결과로 남긴다(pytest가 재생성과 바이트 비교).
`tools/web_app_tech_join_cases_node_test.js`는 Main `joinRows` + `evaluate`(화면 `keep()`과 같은 순서)가 모든 사례에서 Codex와 같은 행·순위 또는
같은 코드임을 확인한다. `web_app_classification_browser_test.js`는 실제 호출 경로(`screen-qgv-live` → `keep` → `groupRows` → `joinRows`)에서
그룹이 전체보다 작을 때 그룹 행만 QGV 순, "그룹 밖 N행 · 조건 적용 대상 아님 · 원래 점수·순위 그대로" 줄, 끄면 같은 표, 거부 시 표 불변을 본다.

Codex 함수는 넘겨받은 행만 본다. 그룹 구성원 행이 빠지면(사례 g2) 나머지로 결합한다. 그래서 Main은 결합 전에 `groupRows`가
그룹 전체 행을 1:1로 찾지 못하면 `MEMBER_NOT_MAPPED`로 결합 자체를 하지 않는다. Main 행의 `issuer_id`는 지금 모두 null이고
`groupRows`가 분류 기록의 발행사로 채운다(행에 다른 발행사가 있으면 `ISSUER_MISMATCH`). 명시적 null 발행사가 `joinRows`까지 가는 경로는
Codex 투영에서는 생기지 않아(확정 그룹은 발행사 확인 필요) node 사례 b에서만 확인한다.

## 5b. 결합 /2 (오너 2026-11-08 「공통 분류 최신 계약 반영 및 소비자 반례 마무리」, Codex #516 `5b0ec88a`)

COMMON 보드는 `techScreen.joinGroupRows`(`technical-filter-join/2`)로 결합한다. 입력: `IS2.classification.groupInput`의 신뢰된 명부
(`technical-filter-membership/1`, 분류 view·기술 투영에서만 만들고 화면 필터·결합 성공 행에서 만들지 않음), 요청 문맥, 명부가 가리키는 행 전부.
누락 `GROUP_MEMBER_MISSING`, 중복 `DUPLICATE_GROUP_ROW`, 그룹 밖 `ROW_OUTSIDE_GROUP`, 명부 미확인 `GROUP_MEMBERSHIP_UNCONFIRMED`,
행 분류 해시·기록 불일치 `ROW_CLASSIFICATION_MISMATCH`, 발행사 충돌 `ISSUER_CLASSIFICATION_MISMATCH`, 문맥 불일치 `GROUP_CONTEXT_MISMATCH:<필드>`는
전체 거부(표 그대로, 사유 문구). 확인된 빈 그룹은 `VERIFIED_EMPTY / 0`. 발행사 null은 같은 코드·기록·해시·평가일의 명부 근거로만 연결하고
`issuer_connections`에 남긴다(원래 행은 그대로). 다른 보드는 /1(완전성 NOT_CHECKED). 5a의 g2(행 누락을 Codex /1이 못 봄)는 /2에서 Codex가 거부한다.
시험: `tools/web_app_group_join_node_test.js`(Codex 23사례 직접 + 호출부 6사례), `web_app_classification_browser_test.js`.

## 6. Codex 답변 반영 (#437 댓글 6706590129, #516 `9343b5e6`)

| Main 질문 | Codex 답 | Main 처리 |
| --- | --- | --- |
| 1. QGV 행의 `signal_day` | 새 섹터 생산자의 `snapshot/preview.valuation_date`. `as_of`·`price_basis_date`로 대신하지 않는다. 기존 공개 공식 생산자에 검증된 평가일 필드가 없으면 null | `rowRecord.signal_day`는 null 유지. 공통 분류 기록이 연결되면 그 `valuation_date`를 쓴다 |
| 2. 증권 ID 공급 파일 | Universe504에서 검증된 고정 증권 ID 0건, 공개 파일 없음 | `security_id` null 유지 |
| 3. 504행 전체를 넘기는가 | **확정된 보드 그룹 전체**의 QGV 행을 넘긴다. 보드에 이미 있는 증권과의 교집합으로 결손을 숨기지 않는다. 그룹 밖 행·순위는 그대로. 그룹 안 필수 연결이 빠지면 거부 | `keep()`은 `IS2.classification.groupRows(board, universe)`가 준 그룹 전체 행만 넘긴다. 공급자가 없거나 그룹을 정하지 못하면 `BOARD_GROUP_ROWS_UNRESOLVED`(결합 없음). 2026-11-08: 공급자 `web_app/classification.js` 연결(원천 NONE이라 오늘은 null), 그룹을 못 정한 사유(`groupRowsWhy`: 분류 버전 불일치·구성원 미확인 등)를 같은 줄에 보임 |
| 4. 행 `id`와 `issuer_id` | 상장 단위 `id`는 발행사가 아니다. 새 생산자는 `issuer_id`를 따로 준다. 필드가 없을 때만 예전 규칙, 명시적 null은 대체 없음 | `joinRows`는 `issuer_id` 필드가 있으면 그것을 발행사로 검사하고 증권 ID와 같으면 거부. `rowRecord.issuer_id`는 null(대체 없음) |
| 5. 매핑 파일·`data_kind` | 승인된 비공개 증권 근거를 연결한 산출물이어야 하며 아직 적격 0건. 공개 links를 임의로 만들지 않는다 | `source().security_links` null 유지 |

작은 표본은 기능마다 다르다. 기술은 N<10이면 분위·상하위 10%만 없고 순위·중앙값은 그대로("유효 종목 N < 10 · 순위·중앙값만 · 분위 없음"). 그룹 구성원·신원 미확인은 순위·중앙값·분위 모두 없음("그룹 구성 미확인 · 순위·중앙값·분위 없음"). 섹터 QGV의 N<20 요소 점수 미산출은 2.2.7 화면에서 따로 보인다.
