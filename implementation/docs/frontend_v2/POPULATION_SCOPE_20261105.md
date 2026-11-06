# 검색·계산 범위 — Universe504와 확장 모집단 (2026-11-05)

오너 11/05 후속 지시 3항("Universe504와 확장 모집단을 명확히 구분한다. 검색 가능 수·QGV 계산 가능 수·순위 가능 수를 각각 표시한다. 실제 확장 데이터가 없으면 합성 개발 검증으로 표시한다. 부분 자료를 전체시장으로 표시하지 않는다.")의 화면 연결이다. 계산은 Codex #482(`current-expansion-research/1`, `research/current_expansion.py`)가 맡는다(DC-42). 이 화면은 검사·읽기·문구만 한다.

## 어디에 보이나

기업 검색 첫 화면(`#/`), 명언 아래 **검색·계산 범위** 칸이다. 두 카드는 합치지 않는다.

| 카드 | 자료 | 행 |
| --- | --- | --- |
| Universe504 (공식 운영) | `IS2.companies`(코드 목록) · `IS2.qgv`(공개 점수 파일의 공개 쪽 행) | 검색 가능 · QGV 총점 산출 · 공식 순위 |
| 확장 모집단 (연구) | `IS2.population.source()` — 오늘은 NONE(비공개 연구, 공개 연결 승인 전) | 검색 가능 · 전체 시장 분모 · 적격/제외/미확정 · 재무 보유 · QGV 계산 가능(Q·G·V·세 축) · 순위 가능 |

## 규칙

- 고정 문구: "Universe504(공식 운영)와 확장 모집단(연구)은 다른 모집단입니다 · 확장 결과는 공식 점수·순위·TARGET을 바꾸지 않습니다".
- 완전한 평가일 IEX 거래 목록이 없으면(`COMPLETE_CURRENT_IEX_ROSTER_UNCONFIRMED`) 전체 시장 분모·커버리지·점수·순위가 null이다. 화면은 `미확정 · 사유`로 쓰고 0으로 쓰지 않는다. "부분 목록 · 전체 시장 분모 미확정 · 점수·순위 없음"을 붙인다.
- `source.source_ref`가 `SYNTHETIC:`으로 시작하면 "합성 개발 검증 · 실제 시장 자료 아님"을 붙인다.
- 판독기는 첫 결함에서 파일 전체를 거부한다. 거부 사유: 부분 목록을 전체 시장으로 표시(`PARTIAL_AS_FULL_MARKET`), 모집단이 확정되지 않았는데 커버리지·점수·순위가 있음, 셈이 맞지 않음, 공식 모집단 대체 표시, 공개 표시 등.
- 새 요청·저장 없음. 새 공개 파일 없음.

## 시험

- `tools/web_app_population_node_test.js`(9): Codex 도구로 만든 합성 출력 2개(`tests/fixtures/current_expansion_research_v1_synthetic.json`: 부분 12행, 완전 12행 중 재무 1행 없음), 거부 11가지, Universe504 문구, #500 단계 합성 2개와 거부 21가지, #499 요약 한 줄과 거부 7가지.
- `tools/web_app_population_browser_test.js`(1440·390): 두 카드, Universe504 수가 공개 쪽과 같음, NONE이면 숫자 없음, 부분·완전 합성, 이전 형식의 단계 행 NA, #500 단계 행, #499 카드 밖 한 줄(NONE·합성·거부), 거부, 요청·저장·넘침 없음.

## 증거 단계 (#500) · 금융업 후보 입력 (#499) — 오너 11/05 지시

확장 카드는 Codex #500(`current-expansion-staged-evidence/1`, `research/current_evidence_bridge.py`)의 증거 단계를 **단계마다 한 행**으로 따로 센다. 판독기는 단계 파일 안의 `evaluation`(CLI가 `current-expansion.json`으로 쓰는 평가 결과)을 기존 규칙으로 검사하고, 각 행을 `evaluation_observation_id`로 잇는다(`original_observation_id`는 출처 추적용으로만). 이전 형식 `current-expansion-research/1`도 그대로 읽는다.

| 행 | #500 필드 | 값 · 분모 |
| --- | --- | --- |
| 재무 연결 | `stages.issuer_link.state` = `SUBMISSIONS_CORROBORATED` | 제출 목록 티커 일치 수 / 티커 관측 수 · 카탈로그만 · 발행사 수 |
| 증권 설명 | `stages.security_type_evidence.state` ≠ `UNKNOWN` | 보관 문서 설명 수 / 티커 관측 수 · "적격 판정 아님" · 평가일 S 적용 수 |
| 평가일 동일 증권 | `stages.same_security_at_basis.state` = `DOCUMENTED_AT_BASIS` | S를 덮는 문서 수 / 티커 관측 수 · S 날짜 · S 밖 문서 · 보관 설명만 · 증거 없음 |
| 외부 증권 ID | `stages.external_fixed_id.value` | 확인 수 / 티커 관측 수 · 입력만 있음(미검증) · 없음 |
| 대표 증권 | `stages.representative.value` | 확정 수 / 발행사 수 · 티커 수로 정하지 않음 |
| 시총 적격성 | `stages.market_cap_eligibility` (`NOT_COMPUTED`, `reasons`) | `NA · 미산출` / 티커 관측 수 · 막힌 입력별 행 수(주식수 · 같은 날 주가 · 주가–증권 연결 · 통화 · 조정 척도) |

- 검색 가능 · 전체 시장 분모 · 적격/제외/미확정 · 재무 보유 · QGV 계산 가능 · 순위 가능 행은 그대로 따로 있다. 카드 머리에 "평가일(S) 2026-11-02"와 "증거 단계는 따로 셉니다 · 문서상 증권 종류는 적격이 아니며 대표 증권도 아닙니다"를 붙인다.
- 0은 단계를 평가한 파일에서만 0이다. 이전 형식 결과의 단계 행은 `NA · 증거 단계 평가 없음`이다.
- 거부(파일 전체, 코드·경로): 모르는 단계 상태·막힘 사유(`STAGE_STATE`), 단계가 상태보다 많이 주장함(`STAGE_PROMOTED`: 값이 있는 대표·외부 ID·시총·주가, S를 덮지 않는 문서의 동일 증권·S 증권 종류, 적격 행, S 동일 증권 없는 제외 행), 평가 결과와 잇기 실패(`JOIN_MISMATCH`, `DUPLICATE_OBSERVATION_ID`), 단계 수 불일치(`COUNT_MISMATCH`), 평가 결과 없음(`EVALUATION_MISSING`), 평가일 불일치(`BASIS_DATE_MISMATCH`). 평가 결과의 결함은 `$.evaluation…` 경로로 보인다.
- #500의 비공개 실제 실행(티커 관측 1,512 · 발행사 1,057 · 제출 목록 일치 1,511 · 증권 설명 179 · S 동일 증권 0 · 외부 ID 0 · 대표 0 · 시총 0 · 적격/제외/점수 0 · 미확정 1,512)은 이 화면에 연결하지 않았다. `source()`는 계속 NONE이다.

**금융업 후보 입력 (연구) · 공식 QGV와 별개** — Codex #499(`financial-v-held-bridge/1`)의 `summary`만 읽어 두 카드 밖 한 줄로 쓴다: 업종별 주 지표 기준 `분자 준비 · 같은 날 주가 · 기준 맞는 비율 / 금융업 코드`. Universe504 카드에 넣지 않고 QGV 커버리지로 세지 않는다. `scored_joint_valid`·`preset_totals`가 null이 아니거나 운영 분모가 504가 아니면 거부한다. `financialSource()`는 NONE이며 화면은 "금융업 후보 입력 (연구) · 공식 QGV와 별개 · 비공개 연구 결과 미연결"만 쓴다. 요약에는 합성 표시가 없어서, 합성 여부는 소스 포장(`synthetic: true`)이 알린다.

시험 자료: `tests/fixtures/current_expansion_staged_evidence_v1_synthetic.json`(#500 `link_and_evaluate`를 그 시험의 합성 입력을 여섯 행으로 늘려 실행: S를 덮는 문서 1건 / 0건 두 경우), `tests/fixtures/financial_v_held_bridge_v1_summary_synthetic.json`(#499 `connect`·`summarize`를 그 시험의 합성 입력으로 실행, 요약만). 실제 기업 자료·주가 없음.

## 하지 않은 것 · 승인 필요

- 실제 확장 결과 연결: 비공개 연구 결과다. 공개 화면에 싣거나 비공개 펼치기로 읽으려면 따로 승인이 필요하다.
- 공식 운영 모집단 변경·게시·배포: 별도 승인.
- 확장 모집단의 첫 실제 입력: 승인된 평가일 IEX 거래 상태 목록 1건(Codex #482가 다음 입력으로 지목, Main의 IEX 확장 흐름 담당).
