# 4.1.3 관측 자료 · 갱신 상태 — 매크로 화면과 `macro-current-query/1` 연결

작성 2026-11-05 · Main. 합성 입력으로 연결을 검증한 상태다. 운영 연결이 아니다.

근거:
- 오너 지시(11/05): "매크로: 관측 기간·갱신 시각·발표 근거·값 유지·수정·stale를 표시한다. 관측 자료와 미채택 국면 판단을 구분한다. 기존 운영 보류를 임의 해제하지 않는다."
- Codex #477(`efc8715f`, Draft) `implementation/docs/research/MACRO_UPDATE_20261105.md`(#477 브랜치에만 있음) "Main은 이 필드로 기준기간·원발표미확인·수집시각·값유지/수정·stale를 연결한다."
- 계산은 Codex, 화면은 Main이다(DC-42). JS는 상태·stale·개수를 계산하지 않고, 파일끼리 맞는지만 확인한다.

## 1. 읽는 파일

화면은 **`macro-current-query/1`** 하나를 읽는다. Codex `tools/macro_observed_timeline.py --timeline-cache … --cache-sha256 … --at …`의 출력이다.
- 근거 계약은 `macro-observed-evidence/1`이다. 계열 행은 `macro-observed-timeline/1` 캐시의 마지막 조회를 그대로 옮긴 것이다.
- timeline 파일은 과거 조회 시점용이다. 지금 화면의 현재 상태는 current query가 맞다(문서 "현재 조회 파일 연결").
- 판독기 `web_app/macro-observed.js`(`IS2.macroObserved`): `validate` → 깊게 동결한 사본 또는 `{code, path}`. 첫 위반에서 파일 전체를 거부한다. 고치거나 채우지 않는다.
  - 14계열 집합, 값 ↔ `RAW_DIAGNOSTIC`, `NOT_COMPUTED`인데 값이 있으면 거부(`VALUE_WITH_NOT_COMPUTED`)
  - 약관 보류 계열의 값 거부, `state`·`stale`·`reason` 일치
  - `official_release_at`·`source_version_id` null + `NOT_PROVEN_IN_ARCHIVE`, `historical_pit_eligible=false`, `model_status=NOT_APPLIED`, `scope` = 탐색 전용(공식 판정·확률·게이트 없음)
  - 현재 조회의 전환 플래그(`new_observation`·`revised`·`newly_available`)는 false, `held = query_usable`
  - `update_status` ↔ 마지막 성공·수집 상태, 경과 초 ↔ 시각, `counts` ↔ 행
- 원천 `source()`는 **NONE**이다. 승인된 공개 파일이 없어서 요청하지 않는다.

## 2. 화면 (3.1 안, 근거 세로선 다음 블록)

- 고정 문구: "관측 자료의 기간·시각·상태만 · 채택된 국면 판단이 아님 · 공식 국면은 미산출 · 기존 운영 보류(M-REENABLE 등) 그대로". 3.1 위의 "공식 국면은 아직 미산출" 줄도 그대로다.
- NONE: "관측 조회 파일이 아직 연결되지 않았습니다"와 이유. 숫자와 행은 없다.
- 파일이 있으면 다음 순서로 보인다.
  1. 자료 종류(합성이면 **합성 개발 검증**)
  2. 조회 시각, 계산 캐시 기준과 경과, 보관본 생성, 갱신(계산 캐시 재사용 · 원천을 새로 받지 않음 · 외부 요청 0건)
  3. 파일의 개수: 조회 가능(신선·stale), 값 유지, 미산출, 원발표·원기관 버전 입증 수, 과거 시점 검증 가능 수
- 계열마다 보이는 것:
  - 상태: 조회 가능 / stale · 기준 기간 지연 / 자료 없음 · 사유. 사건 계열(FOMC)은 stale 판정 없음.
  - 기준 기간 · `data_asof` · 빈도 · 단위 · 계절조정
  - 진단값 관측 · 채택된 국면 판단 아님 / 미산출 · 사유
  - **원발표 시각 미확인 · NOT_PROVEN_IN_ARCHIVE**. 취득·게시·계획 시각으로 채우지 않는다.
  - 첫 취득(기록된 수신, 또는 "기록 없음 · 늦어도 … 보관본 생성 상한"), 선택 버전 취득(또는 보수 상한), 버전 종류(최초 보관 기준값·첫 기록·수정 버전)
  - 값 유지 · 수정 버전 · 이번 조회의 수정 · 새 관측 · 새로 조회 가능
  - 마지막 성공 수집과 경과, 갱신 상태(마지막 성공 유지 / 최근 수집 실패 · 마지막 성공값 유지 · 실패 사유 / 성공한 수집 없음)
  - 출처 · 약관(접힘): 기관, 사용권 분류, 공개 범위, 약관 확인일과 메모, 원기관 자료 버전 미확인, PIT 검증 불가
- 후보 규칙 상태(`candidate_state`)는 이 블록에 표시하지 않는다(해석 후보 · 미승인).

## 3. 값을 표시하지 않는 이유

문서에 "현재 조회 파일은 비공개로 생성해 Main 계약만 인계한다", "공개 화면의 파일 소비는 Main 담당이며 별도 승인 없이 바꾸지 않는다", "실값은 이 PR에 넣지 않는다"가 있다. 그래서 화면은 관측값 숫자를 그리지 않고 상태·시각·개수만 보인다. `view()`에는 값이 들어가지 않는다.

## 4. 시험

- 합성 fixture: `implementation/tests/fixtures/macro_current_query_v1_synthetic.json`(sha256 고정).
  - Codex #477 도구를 임시 폴더에서 `python3 -I`로 실행해 만들었다. 기존 `evidence_lines.build`로 만든 가짜 보관본 두 개를 썼다.
  - 사례 main: 곡선 수정 + 유지, BLS 실업률 성공 뒤 실패, 근로시간 stale, G17 상한만, Census 키 없음, DOL 보류
  - 사례 late: 200일 뒤, stale 5
  - 사례 never: 수집 없음
  - 값은 표지 숫자 `7319NN`이다.
- `tools/web_app_macro_observed_node_test.js`(11)
- `tools/web_app_macro_observed_browser_test.js`(1440·390, 13): NONE, 합성 사례, STALE, 유지+수정 버전, FAILED_AFTER_SUCCESS, NEVER_SUCCEEDED, 거부(스키마, NOT_COMPUTED 값), 390 넘침 없음, 요청·저장 없음, 값 숫자 없음

## 5. 하지 않은 것 · 승인이 필요한 것

- 하지 않은 것: 공개 파일 게시, 데이터 계층(`data.js`) 연결, 스케줄·워크플로, 재시도·보존 정책, 새 수집.
- M-REENABLE, GSQ-011, FX 공개 제외, DOL 약관 보류, Census 키는 그대로 둔다.
- 오너 승인이 필요한 것:
  1. current query 파일을 공개 산출물로 게시할지
  2. 관측값 숫자를 공개 화면에 보일지
  3. 갱신 스케줄
- 승인 뒤에 `source()`를 데이터 계층 파일로 바꾼다.
- Codex 확인 사항:
  - current query에서 `revised`·`new_observation`·`newly_available`이 언제나 false인지. 화면은 true면 거부한다.
  - 원발표 근거가 생기면 `official_release_status`에 어떤 값이 오는지. 지금은 null이 아니면 거부한다.
