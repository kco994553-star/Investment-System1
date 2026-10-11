# 판단 7단계·보조 칩·사유 코드 일관성 점검 (2026-10-11)

대상: D-19 판단 7단계(■차단 > ▼위험재검토 > ▼비중축소검토 > ▲비중확대검토 > ●추가검토 > ●보유맥락 > ●관찰), 보조 칩, 사유 코드가 나오는 모든 곳.

- **S17** 일일보고서(`daily-report.js`): 모의투자·투자 일일보고서 화면, 보고서 템플릿 v1 내보내기(우체통 포함).
- **가상매매 모듈:** `virtual-trading.js`(엔진), `virtual-trading-runner.js`, `virtual-trading-signals.js`, `virtual-trading-v-history.js`, `virtual-ledger-sheets.js`(S17 장부 시트 카드).
- **S03** 포트폴리오(`#portfolio`, `portfolio-screen.js`). 점검 시점에는 가상 판단을 전혀 보여 주지 않았다. 아래 6번처럼 S17과 같은 판단을 보여 주는 카드를 추가했다. 기업 화면(S04·S05)에는 가상 판단이 없다.
- 390px·1440px.

규칙값·설정·방법론·가중치·TARGET·결정 기록부는 바꾸지 않았다. 표시 방식만 바꿨다.

## 1. 한 곳에서 정의 (one source)

| 항목 | 정의 위치 | 쓰는 곳 |
| --- | --- | --- |
| 단계 순서 `LEVELS`, 기호 `SYMBOLS` | `VirtualTrading`(`virtual-trading.js`), 고정(freeze) | 엔진 판정, 모든 화면·템플릿 |
| 한국어·영어 이름 `LABELS`, 표기 `label()` = 기호+이름 붙여 쓰기(`▲비중확대검토`) | `VirtualTrading` | S17 칩·집계·우선순위 문장, 템플릿 ③·지침 판단 어휘 줄, S03 카드 |
| 색 계열 `TONES`(block·risk·reduce·increase·review·neutral) | `VirtualTrading` → `style.css .chip.vt[data-tone]` | 모든 판단 칩. 판단 색은 수익률 색과 다름(템플릿 §7.1) |
| 보조 신호 칩 `SIGNALS`(`OVERWEIGHT`→`▼비중`, `INCREASE_CANDIDATE`→`▲확대 후보`) | `VirtualTrading` | 템플릿 §7.3 예시 그대로 |
| 사유 코드 라벨 `CODE_LABELS`(코드마다 [한국어, 영어], 120개) | `VirtualTrading` | S17 표·취소 범례·입력 카드·V 기록 줄·업종 기준 칸, 템플릿 사전, 장부 시트 카드, S03 카드 |
| 고정 문구 `DISCLAIMER` "가상 · 실제 추천 아님 · 주문 기능 없음" | `VirtualTrading` | S17 머리글·③·⑩, 장부 시트 카드, 템플릿 ③·⑩, S03 카드 |
| 행 순서 `compareRows`(주 판단 우선순위 → 기업 ID) | `VirtualTrading` | S17 ③, S03 카드 |
| 렌더러 `judgementTokens/Text/Html`, `reasonsHtml`, `codeText`, `codesText`, `disclaimerHtml`, `priorityText` | `VirtualTrading` | 같은 토큰이 화면 칩과 템플릿 문장을 만든다 |
| 코드 목록 `CODES` | 엔진(`VirtualTrading.CODES` 9개 묶음), `VirtualTradingRunner.CODES`, `VirtualTradingSignals.CODES`, `VirtualTradingVHistory.CODES`, `VirtualLedgerSheets.CODES` | 라벨 노드 테스트 |

Python(`qgv/virtual_trading.py`)은 순서와 기호만 갖는다. 피할 수 없는 사본이라 `tests/test_virtual_trading.py::test_level_order_and_symbols_match_the_device_vocabulary`가 JS와 같은지 확인한다(이름·색 계열·라벨 키 순서도 `LEVELS`와 같아야 함).

## 2. 발견한 불일치와 수정

| # | 불일치 | 위치 | 수정 |
| --- | --- | --- | --- |
| 1 | 판단 이름 사본이 두 개였다. `LEVEL_KO`(기호 붙여 씀)와 `VirtualTrading.label()`(기호 뒤 띄어 씀 `▲ 비중확대검토`) | `daily-report.js`, `virtual-trading.js` | `LEVEL_KO` 삭제. `label()` 하나로 통일했고, 결정 기록부 D-19 표기대로 붙여 쓴다 |
| 2 | 우선순위 문장 `■차단 > … > ●관찰`과 AI 지침의 판단 어휘 줄이 손으로 쓴 문자열이었다 | `daily-report.js` 화면 ③, `GUIDE_A` | `priorityText()`로 만든다 |
| 3 | 사유 코드 라벨 사본(`REASON_KO`, 22개)은 한국어만 있었다. `BASIS_KO`·`V_SLOPE_KO`는 따로 있었다 | `daily-report.js` | `CODE_LABELS`로 옮겼다(한국어+영어). V 기울기 상태 라벨도 같은 표에서 가져온다 |
| 4 | 보조 코드(`aux`)를 S17 화면·템플릿 어디에도 표시하지 않았다. 템플릿 §7.3의 `▼비중`·`▲확대 후보` 보조 칩이 빠졌다 | `daily-report.js` `buildModel` | 판단 객체 전체를 넘긴다. 방향 보조 신호는 칩으로 보이고(주·보조 단계와 겹치면 생략), 나머지 보조 코드는 사유 목록에 라벨과 함께 나온다 |
| 5 | 보조 칩 정렬을 보장하지 않았고, 주 판단과 같은 단계가 보조로 다시 나와도 막지 않았다 | 화면·템플릿 | `judgementTokens`: 주 판단은 정확히 1개, 보조는 단계 우선순위 순, 같은 단계는 한 번만 |
| 6 | S03에 가상 판단이 없어서 "같은 회사·같은 날 = 같은 판단"을 확인할 수 없었다 | `portfolio-screen.js`, `app.js` | 가상 판단 카드를 추가했다. 이 페이지에서 투자 일일보고서가 마지막으로 계산한 그림자 장부 판단(기록 모드만, RAM 전용)을 S17과 같은 렌더러·순서·라벨로 보여 준다. 규칙을 다시 돌리거나 가격을 요청하지 않는다. 계산 전에는 NOT_AVAILABLE과 S17 링크를 보여 준다 |
| 7 | ③ 표에 사유가 없었다. ⑩ 체결 사유와 입력 카드·V 기록·업종 기준·장부 시트 카드는 코드를 그대로 보여 줬다 | `daily-report.js`, `virtual-ledger-sheets.js` | 표시하는 모든 코드를 "라벨 (CODE)"로 바꿨다. ③에 사유 칸을 추가했다. 업종 기준 칸은 기존 "CODE n/273" 뒤에 라벨을 붙인다 |
| 8 | 템플릿 사유 코드 사전이 라벨 없는 코드를 조용히 빼 버렸다. 보조 코드와 장부 정지 코드가 사전에 없었다 | `renderTemplate` | 그날 쓰인 모든 코드를 싣는다(보조 코드, 계산 전 장부 사유 포함). 라벨이 없으면 "라벨 없음 · 코드 그대로"로 남긴다 |
| 9 | 판단 칩 CSS가 없었다(`chip judgement`, `chip aux`). 색이 없고 줄바꿈 규칙도 없었다 | `style.css` | `.vt-judgement`는 flex-wrap으로 줄을 바꾸고, `.chip.vt`는 칩 안 글자가 잘리지 않게 nowrap을 준다. 색 계열 6개를 두고, 1024px 미만에서는 ③ 판단·사유 칸에 최소 폭을 준다(표는 `.table-scroll` 안에서 가로로 스크롤, 1024px 이상은 PC 레이아웃 규칙대로 스크롤 없이 맞춤) |
| 10 | 고정 문구가 일부만 있었다. ⑩·템플릿 ⑩은 "가상 · 실제 추천 아님"만, 장부 시트 카드는 전체 문구, 머리글·③에는 없었다 | S17·템플릿 | `DISCLAIMER` 전체 문구를 머리글(두 보고서 모두)·③·⑩·장부 시트 카드·템플릿 ③·⑩·S03 카드에 붙였다 |
| 11 | 가상 장부가 아닌 곳에 매수·매도 동사가 있었다. S17 요약의 "매수 한도/매도 한도", 취소 표의 "매수/매도", "매도대금", ③ 안내문, S03 안내문 "매수·매도·주문 기능은 없습니다" | `daily-report.js`, `portfolio-screen.js` | "가상 매수 한도", "가상 매수/가상 매도", "가상 매도대금", "가상 매수·가상 매도 표현은 …"으로 바꿨다. S03 안내문은 "매수·매도 지시 아님 · 주문 기능 없음"(홈의 통합 판단 카드와 같은 부정 문구)으로 바꿨다 |
| 12 | 행 정렬 비교 함수가 화면마다 따로 있었다 | `daily-report.js` | `compareRows` 하나를 S17·S03이 같이 쓴다 |
| 13 | `LEVELS`·`SYMBOLS` 내보내기 객체를 바꿀 수 있었다 | `virtual-trading.js` | `Object.freeze`로 고정했다 |

## 3. 라벨이 없던 코드 (96개, 모두 한국어·영어 라벨 추가)

점검 전에는 `REASON_KO` 22개와 V 기울기 상태 2개에만 한국어 라벨이 있었고, 영어 라벨은 하나도 없었다(판단 이름 제외).

- **엔진 보조:** OVERWEIGHT, INCREASE_CANDIDATE, COVERAGE_PARTIAL, EARNINGS_WINDOW, TYPE_CHANGED, SECTOR_SP500_SUBSTITUTE
- **엔진 장부 정지:** START_DATE_NOT_SET, INPUT_INVALID, CONFIG_INVALID, TARGET_NOT_AVAILABLE, NO_SESSION_ON_OR_AFTER_START, INITIAL_VALUE_NOT_AVAILABLE
- **엔진 D-5 기준·D-22 업종:** SECTOR_BASIS_NOT_AVAILABLE, PRICE_NOT_ALIGNED, HISTORY_INSUFFICIENT, DISTRIBUTION_DEGENERATE, SIC_NOT_AVAILABLE, SEMIS_MEMBERSHIP_NOT_AVAILABLE, SECTOR_ETF_NOT_MAPPED
- **엔진 적중·플래그:** INSUFFICIENT_SAMPLE, HOLD, EXCLUDE, CONFIRMED_TEMPORARY, CONFIRMED_STRUCTURAL, CLEAR
- **실행기:** TARGET_CATALOG_INVALID, SESSIONS_NOT_AVAILABLE, SET_B_NOT_DEFINED, SET_B_INVALID, NO_ACTUAL, ACTUAL_INVALID, INITIAL_COST_FX_MISSING, BEFORE_START_DATE, LEDGER_NOT_AVAILABLE, NOT_REQUESTED, HISTORY_UNAVAILABLE, HISTORY_FORMAT_INVALID, CURRENCY_MISMATCH, OFF, REQUEST_INVALID, ORIGIN_UNAPPROVED, AUTH_REQUIRED, AUTH_FORBIDDEN, AUTH_UNAVAILABLE, ORIGIN_FORBIDDEN, CONFIG_UNAVAILABLE, CANCELED, RATE_LIMIT_UNAVAILABLE, RATE_LIMITED, LEDGER_UNREACHABLE, LEDGER_INVALID, LEDGER_NOT_PUBLISHED, AUTH_FAILED, YAHOO_UNAVAILABLE
- **V 기록:** DATE_INVALID, DATE_BEFORE_LAST_RECORDED, UNCHANGED, NO_VALUES, DEVICE_STORAGE_UNAVAILABLE, V_STORE_INVALID, SESSION_NOT_AVAILABLE, VALUATION_INPUTS_UNAVAILABLE
- **장부 시트:** LEDGER_REPLAY_MISMATCH, SHEET_ROWS_INVALID, SHEET_HEADER_MISMATCH, META_INVALID, META_ROW_INVALID, LEDGER_UNKNOWN, INPUTS_NOT_READY, INPUTS_INCOMPLETE, INPUTS_CHANGED, WAITING_FOR_QG_RECORD, VALUATION_NOT_AVAILABLE, SHEET_NOT_READY, SHEET_NOT_LOADED, NOT_CONNECTED, SHADOW_NOT_STARTED, SHADOW_ALREADY_STARTED, SET_B_REDEFINED, REHEARSAL_NOT_RECORDED, NUMBER_INVALID, VALUE_INVALID, CONFIG_NOT_CANONICAL, COMPANY_NOT_SUPPORTED, WEIGHT_INVALID, WEIGHT_SUM_OVER_100, WEIGHTS_EMPTY, WRITE_FAILED, READ_FAILED, HASH_UNAVAILABLE, SOURCE_TOO_LARGE, INVALID
- **S17 연결부(`app.js`):** RUNNER_LOADING, RUNNER_FAILED, PUBLIC_CATALOG_UNAVAILABLE, MAILBOX_FAILED

**의도된 그대로 표시(fallback):** 비공개 가격 Worker가 넘겨주는 오류 코드는 목록 밖일 수 있다. 라벨이 없는 코드는 지어내지 않고 빼지도 않는다. 코드를 그대로 보여 주고 `data-unlabeled`를 붙이며, 템플릿 사전에는 "라벨 없음 · 코드 그대로"로 싣는다. 이 동작은 노드 테스트와 브라우저 테스트가 확인한다.

코드가 아닌 대문자 값(티커·통화·장부 종류·행 종류·상태·설정값)은 노드 테스트의 `NOT_CODES` 목록에 묶음별로 적어 두었다. 새 코드가 라벨도 목록도 없이 생기면 테스트가 실패한다. 이 검사는 JS 5개 모듈, S17 연결부, Python 참조 구현 4개(`virtual_trading*.py`, `virtual_ledger_sheets.py`)를 훑는다.

## 4. 그대로 둔 것

- S13 프로필 편집기(`device-profiles.js`)의 "6관점" 안내문(관찰/추가검토/보유맥락/비중재검토/위험재검토/차단)은 판정이 정의되지 않은 별도 어휘(NOT_AVAILABLE)다. D-19 개정안은 채택될 때 S13 어휘도 함께 바꾸라고 한다(템플릿 §7). 결정 사항이라 이번 점검에서는 바꾸지 않았다.
- 시안(`mockups/S17_REPORT_MOCKUP.dc.html`)은 기호 뒤를 띄어 쓴다(`▲ 비중확대검토`). 시안은 예시 수치라 고치지 않았다. 앱은 결정 기록부 표기(붙여 씀)를 따른다.
- 결정 기록부·규칙값·Worker·워크플로는 바꾸지 않았다.

## 5. 테스트

- `tools/judgement_labels_node_test.js`(CI 노드 목록): D-19 순서·이름·색 계열이 한 표에 있는지, 엔진·실행기·신호·V 기록·장부 시트 코드 목록이 모두 한국어·영어 라벨을 갖는지, 소스 전체 훑기(JS·S17 연결부·Python), 그대로 표시 fallback, `VirtualTrading` 밖에 판단 어휘 사본이 없는지, 주 판단 7개 × 보조 단계 128가지 조합 × 보조 신호 4가지(3,584가지)에서 주 칩이 1개이고 보조 칩이 우선순위 순이며 반복이 없는지, 기준 벡터 S17 화면과 템플릿이 같은 판단 문장을 쓰는지.
- `tools/judgement_consistency_browser_test.js`(CI 브라우저 목록):
  - A(390): 앱의 실행기 경로를 합성 입력으로 돌려 투자 일일보고서가 그림자 장부를 계산하게 한다. 회사마다 S03 카드 칩, S17 ③ 칩, 내보낸 템플릿 ③ 문장이 같은지, 행 순서가 같은지, 고정 문구와 동사 규칙을 지키는지 본다.
  - B(390·1440): 7단계, 보조 조합, 모든 코드 묶음(판단·보조·주문·EXEC_*·장부·실행기·신호·V 기록·장부 시트 일부)을 넣은 합성 하루를 앱 모듈로 모의·투자 두 보고서와 S03에 그린다. 칩 글자와 색 계열, 계열별 색이 하나인지, 주 칩이 1개인지, 보조 칩이 우선순위 순인지, S03·S17·템플릿 문장이 같은지, 모든 코드에 라벨이 있는지(그대로 표시는 테스트용 코드 하나뿐), 매수·매도 동사가 "가상 매수/매도" 또는 "매수·매도 지시 아님"에서만 나오는지, 고정 문구가 머리글·③·⑩·장부 시트 카드·S03에 있는지, 칩이 잘리지 않는지, 줄바꿈되는지, 페이지가 가로로 스크롤되지 않는지, 영어 칩도 같은 표에서 오는지 본다.
- `tests/test_virtual_trading.py`: Python `LEVELS`·`SYMBOLS`가 JS와 같은지.
- `tools/pc_layout_browser_test.js`의 합성 S17 모델이 없어진 `DailyReport.LEVEL_KO` 대신 `VirtualTrading.LEVELS`를 쓰도록 고쳤다. 손으로 만든 행(`main`·`aux`만 있음)도 같은 렌더러로 그린다.
- 기존 테스트에서 바뀐 기대값은 세 가지다. `label()` 붙여 쓰기, ⑩ 고정 문구 전체, 업종 기준 칸 라벨 덧붙임(`HISTORY_INSUFFICIENT 272/273 · 정렬된 일봉 부족`).
