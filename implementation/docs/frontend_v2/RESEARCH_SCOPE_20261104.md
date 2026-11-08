# Lab 9.1 연구 범위 · 선정 방식 (Main 판독기·화면, 2026-11-04)

Main | 오너 2026-11-04 3차 지시 4항 | 개발 빌드 · 합성 자료 · Draft

계산은 Codex가 맡고, Main은 판독기와 화면만 만든다(DC-42).

- **#474**: 운영 커버리지 `operational-qgv-coverage/1`. Codex `572f0b5e`, `research/operational_coverage.py`.
- **#473**: 일반 연구 선정 방식. Codex `f14262a6`, `validation.vertical_slice`의 `selection_policy`·`n_eligible`·`n_selected`·`selected`·`weights`.

실제 연구 결과는 비공개다. 공개 승인 전에는 연결하지 않으며, 지금 원천은 `NONE`(요청 없음)이다.

## 화면 위치

새 앱 `#/lab`의 n+1.1 백테스트에서 비공개 칸 "연구 결과" 아래 **연구 범위 · 선정 방식** 칸이다. 새 메뉴나 절은 만들지 않았다.

## 운영 커버리지

- **분모 문구를 먼저 보인다.** 504개이면 "운영 Universe504 코드 504개 기준", 아니면 "운영 게시본 코드 n개 기준 · Universe504(504개)와 다름"이다. 이어서 "게시 행 중 TARGET 제외 · 고정 증권 ID 아님 · 발행사 CIK 수(또는 미확인과 CIK 없는 행 수)"를 붙인다. 개수를 504로 맞춰 넣지 않는다.
- **줄은 12개이고 이름이 모두 다르다.**
  - Q 축 단독, G 축 단독, V 축 단독
  - Q·G·V 세 축 동시
  - 프리셋 총점 7개: 균형·품질·성장·가치·공격형·균형형·방어형. 보관된 축 점수에서 도출한 값이며, 저장된 총점이나 과거 시점 재구성이 아니다.
  - 게시본 기본 총점(저장값)
- **해당 없음**(`FINANCIAL_PROFILE_V_NOT_DEFINED`)은 결손과 따로 센다.
- **프리셋 값이 null이면** 엔진 버전 불일치나 유형 가중치 미연결 때문이다. "미산출"과 사유로 보이고 0이 되지 않는다.
- 팩터 15개와 원본 ID(게시본 ID, SHA-256)는 접힌 칸에 둔다.
- "선택한 운영 게시본 하나 기준 · 과거 전체 시장 커버리지 아님 · 신호일 기준 시점 검증 안 됨"을 항상 함께 보인다.
- **첫 위반에서 파일 전체를 거부한다.** 거부 코드:
  - `SCHEMA_VERSION`, `KEY_UNKNOWN`·`KEY_MISSING`
  - `DENOMINATOR_MISMATCH`, `COUNT_MISMATCH`, `COUNT_RANGE`, `PRESET_VALID_MISMATCH`, `ENGINE_MISMATCH_NOT_NULL`
  - `WHOLE_MARKET_NOT_ALLOWED`, `SECURITY_ID_NOT_ALLOWED`, `CODE_INVALID`·`CODE_DUPLICATE`

## 일반 연구 선정 방식

- **선정 방식 이름**
  - 조건 충족 전부: 정책 없음이면 "(선정 방식 지정 없음)"을 붙인다.
  - 상위 N개
  - 상위 p%: 소수점 아래는 버린다.
- **선정 수**는 "조건 충족 n개 중 m개 선정"으로 쓴다. Codex `select_provisional`과 같은 규칙으로 검사한다.
  - 전부: n개
  - 상위 N: min(n, N)개
  - 상위 p%: floor(n × p / 100)개
- **비중**은 같은 비중이다. 선정 0개이면 "비중 없음"이다.
- "공식 모델은 기존 N15 구간·TARGET 규칙 그대로 · 이 선정 방식을 따르지 않음"을 항상 보인다.
- 같은 결과 안의 `outcomes`·실현 수익률은 읽지도 보이지도 않는다.
- 거부 코드: `SELECTED_COUNT_MISMATCH`, `POLICY_INVALID`, `ENUM`, `SELECTED_INVALID`, `WEIGHTS_INVALID`, `WEIGHTS_NOT_EQUAL`.

## 시험 자료

`implementation/tests/fixtures/operational_qgv_coverage_v1_synthetic.json`은 합성 자료다. Codex #474 코드를 공개 fixture `qgv_official_vectors_v1.json`의 `base_text`에 그대로 돌린 출력이며, 두 변형이 들어 있다.

- `engine_mismatch`: `coverage_from_archive`를 그대로 돌린 결과. 엔진이 달라 프리셋 7개가 모두 null이다.
- `engine_matched`: 같은 행을 `summarize_rows`로 돌리고 `engine_matches`를 true로 둔 결과. 프리셋 가능 수를 도출한다.

Codex 코드가 바뀌면 같은 방법으로 다시 만든다. 실제 운영 게시본의 커버리지 값은 이 저장소에 없다.

## 남은 일

- 비공개 연결(원천 경로·로그인)과 공개 여부는 오너 승인 뒤에 한다(`LAB-PUBLISH`와 같은 경계).
- 선정 결과를 Lab v2 실행(`sample.selection`)과 잇는 방식은 Codex와 합의가 필요하다. 지금은 vertical_slice 결과의 필드를 직접 읽는다.
