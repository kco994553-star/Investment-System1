# 3.1.2 기업별 지표 값 (기술적 분석 화면) — 2026-11-05

오너 지시(11/05): "기술: 기업별 지표와 그룹별 순위·필터를 각각 연결한다. 전체시장 순위가 없어도 적격 기업 지표는 표시할 수 있게 한다."
상태: **합성 입력으로 연결을 검증한 상태**(개발 빌드). 운영 아님.

## 무엇을 읽나

- Codex #478(head `419add34`, Draft)의 `technical-offline-display/1` 출력과 그 안의 `readiness`(`technical-display-readiness/1`).
  계약 문서: `docs/lab/TECHNICAL_OFFLINE_DISPLAY_20261105.md`, `docs/lab/TECHNICAL_SOURCE_UPDATE_DESIGN_20261105.md`(#478 브랜치).
- 판독기 `web_app/tech-display.js`(IS2.techDisplay): `validate`(첫 오류에서 파일 전체 거절, 고치거나 채우지 않음) · `find`(계열 symbol =
  고른 기업 ticker) · `view`(문구). 계산은 하지 않음(DC-42).
- 그리는 부분 `web_app/screen-tech-display-live.js`: 기술적 분석 화면 2-1의 3.1.2 표 바로 뒤, 고른 기업 하나만. 새 화면·경로 없음.

## 문구와 상태

| 구분 | 화면 |
|---|---|
| `VALUE` | 채택값 + 값(`[data-ram-price]` 안 글자만). 실제 0은 0 |
| `DIAGNOSTIC` | 진단값만 있음 · 값은 보이지 않음 · 사유 문구. `raw_value`는 RAM 글자로도 쓰지 않고 개수만 셈 |
| `NOT_COMPUTED` | 미산출 · 사유 문구(초기 봉 부족, 가격 변화 0, 고가·저가 결손, 빠진 거래일 등). null은 0이 아님 |
| 지표별 | 관측/필요 세션, 창, 초기 봉 READY/INSUFFICIENT/NOT_EVALUATED(최소·관측), 시작값 방식, 세션 연속, 의존 구간 무분할 근거 |
| 계열별 | 보유 일봉 수·기간, 원주가(RAW)·PIT 미검증·비공개 연구 범위, 신원, 가용 시각 NOT_VERIFIED, 최신 여부 UNKNOWN · 갱신 일정 미연결 |
| 순위 | 항상 "순위 없음 · 고정 증권 ID 없음 · 순위를 매기지 않음"(파일의 `fixed_security_id_state`) · 지표는 그대로 표시 |
| 그룹 순위·필터 | 여기서 그리지 않음. 1. QGV의 1.1.8 기술 조건 필터(`tech-screen.js`, `screen-tech-filter-live.js`)로 링크만 |
| 원천 | `source()` = NONE: "기업별 지표 자료가 아직 없습니다", 숫자 없음. 합성 자료면 "합성 개발 검증" |
| 거절·없음 | 계약과 다른 파일 → 파일 전체 미사용(코드 표시) · 파일에 그 기업 계열 없음 / 같은 symbol 2개 → 고르지 않음 |

공개 판정 띠(지표 판정 보류, `NO_APPROVED_PRICE_SERIES`)와 3.1.2 표의 판정 보류는 그대로다. 값 표시는 판정이 아니다.

## 시험

- 고정 자료 `tests/fixtures/technical_offline_display_synthetic.json`(SYNTHETIC, sha256 고정): Codex의 `tools/technical_display_offline.py`를
  #478 트리에서 그대로 돌린 출력. 입력은 `tools/build_tech_display_fixture.py`가 만든 합성 봉 6계열(전부 채택 · 최근120봉만 무분할 ·
  신원 미확인 · 평탄 35봉 · 마지막 고가 결손 · 빈 계열).
- `tools/web_app_tech_display_node_test.js`, `tools/web_app_tech_display_browser_test.js`(1440·390; 시험에서만 symbol을 NVDA로 바꿔 주입).

## 하지 않은 것

- 실자료 연결, 공개 파일 게시, 수집·스케줄·workflow·Secret. 거래량(`volume_latest`, `volume_note`)은 검사만 하고 표시하지 않음.
- 지표 판정·신호·순위 계산. 2-1의 비공개 패널(tech-kis-chart)은 건드리지 않음.

## 승인이 필요한 것

- 이 출력(비공개 연구 결과, Git 밖 0600)을 어떤 화면·누구에게 보일지(공개 OHLCV·파생지표 사용권 포함).
- 계열과 기업을 잇는 기준(지금은 symbol=ticker; 고정 증권 ID 연결 뒤 바꿈), 갱신 일정과 최신 여부 기준.
