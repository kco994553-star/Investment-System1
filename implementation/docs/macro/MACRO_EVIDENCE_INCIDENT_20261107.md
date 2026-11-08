# 매크로 근거 파일 빈 기본값 게시 (2026-11-07) · 원인과 수정

이 수정은 오너 11/07 두 지시를 따른다.
- 「매크로 근거 자료 운영 복구를 최우선으로 진행하라」
- 2차 「매크로 장애 원인 구분 및 복구·재발 방지 진행」
- 3차 「매크로 기록 초기화 위험 보완 및 정책 /2 연결」

이 문서는 사실·원인·수정 범위만 적고, 값은 적지 않는다.

## 1. 일어난 일

| 항목 | 내용 |
| --- | --- |
| 실행 | `sec-daily-public-inputs.yml` run 42326419126 (2026-11-07) |
| 로그 | `01:57:43Z MACRO_EVIDENCE BUILD_FAILED nothing_written`, 그 뒤 verify·deploy 성공 |
| 공개 결과 | `macro-evidence.json` = 빌드 단계의 빈 기본값과 바이트까지 같음(`NOT_AVAILABLE`, `generated_at` null, continuity `NOT_COLLECTED`, 18,884 B). Codex가 운영 SHA·산출물과 대조해 확인 |
| 그 전 정상본 | 11/06 실행: `state=PARTIAL previous=LOADED continuity=CONTINUOUS releases=6597 replay_events=135`, 14계열 중 LIVE 11 |

## 2. 원인

**확인: 빈 기본값이 게시된 경로**
1. collect job의 `build_pages_cockpit.py`가 빈 기본값 `macro-evidence.json`을 먼저 쓴다.
2. 생성기 `macro_evidence.run_from_capture`가 예외를 잡고 `BUILD_FAILED nothing_written`을 찍은 뒤 1을 돌려줬다.
3. 호출하는 쪽 `public_screens_pipeline.collect`가 그 반환값을 처리하지 않았다. 그래서 빈 기본값이 산출물에 남았다.
4. Pages 가드는 빈 기본값을 받는다(규격에 맞는 파일).
5. 배포 신선도 가드에 `macro-evidence.json` 규칙이 없었다.

**미확인: 최초 예외**
- 예외 종류와 단계가 로그에 없다(옛 생성기는 고정 문구 하나만 찍음).
- 같은 단계 로그의 v0 수집 줄(H15 404, DDP H41·H8 BODY_SIZE 0)은 성공한 11/06과 같다.
- `MACRO_EVIDENCE_FETCH` 진단 줄은 두 날 모두 0건이다. 그래서 수집·만들기·쓰기 중 어디서 났는지 로그로 좁힐 수 없다.
- 이 수정부터 실패 단계(`PREVIOUS`·`COLLECT`·`BUILD`·`VALIDATE`·`WRITE`, 호출부 예외는 `CALLER`)와 예외 종류 이름만 로그와 상태 파일에 남는다. 원문·메시지·비밀값은 남기지 않는다.
- 이 수정은 최초 예외 재현을 선행 조건으로 두지 않았다.

## 3. 실행 당시 자료 보존 여부 (확정, 다시 탐색하지 않음)

| 자료 | 보존 | 근거 |
| --- | --- | --- |
| capture(원응답 본문) | **미보존** | `public_screens_pipeline.collect`의 `TemporaryDirectory`에만 있었고 단계가 끝나면 지워진다. 이 단계에는 비공개 저장소 토큰이 없고, 올리는 것은 공개 cockpit 산출물뿐이다 |
| manifest | **미보존** | 같은 임시 디렉터리·메모리에만 있었다 |
| 응답 상태 | **일부만** | job 로그의 고정 코드 줄(`MACRO_V0_FETCH` 3줄)만 남았다 |
| 이전 정상본(11/06) | **미보존** | 11/06 산출물은 보관 기간 만료, 11/07 산출물(13556366626)은 빈 기본값이다. 공개본은 덮였다. 비공개 저장소·웹 보관소에 없고, 작업 환경의 사본은 모두 빈 기본값이다 |

- 새 수집으로 당시 실패를 재현했다고 하지 않는다.
- 다음 정상 실행은 공개본을 `EMPTY_LIVE`(빈 기본값만 있음)로 읽고 continuity `RESET_PREVIOUS_UNAVAILABLE`로 새 기준을 시작한다. 파일에도 `previous=UNAVAILABLE`로 남는다. 11/06까지의 발표·수정 기록은 이어지지 않는다.
- 오래된 값을 최신 수집처럼 다시 만들거나 확인 시각을 새로 고치지 않는다.

## 4. 수정 (이 PR)

**호출부 `tools/public_screens_pipeline.py`**
- 생성기 반환값이 0이 아니거나 예외가 나면 `macro_evidence.withhold(out)`를 부른다.
  - 산출물의 근거 파일은 검증된 정상본일 때만 남긴다.
  - 빈 기본값이나 그 밖의 파일은 지워서 게시하지 않는다.
  - 로그: `MACRO_EVIDENCE WITHHELD file=macro-evidence.json previous=<읽기 값> status=WITHHELD`.
- SEC 수집은 지금처럼 멈추지 않는다. 워크플로 파일은 바꾸지 않았다.

**생성기 `tools/macro_evidence.py`**
- 이전 공개본을 네 갈래로 나눠 읽는다(3차):

| 이전본 상태 | 읽기 값 | 처리 |
| --- | --- | --- |
| 검증된 정상본 | `LOADED` | 이어서 만든다(CONTINUOUS). 실패하면 그 바이트를 그대로 둔다 |
| 확인된 부재 | `NO_LIVE`(404, 시도 기록도 없음) | 첫 기준(BASELINE) |
| 확인된 부재 | `EMPTY_LIVE`(빈 기본값만 있음) | 기록 단절을 밝힌 새 기준(`RESET_PREVIOUS_UNAVAILABLE`) |
| 확인된 부재 | `REMOVED`(404인데 공개 시도 기록이 있음: 있던 파일이 빠짐) | 기록 단절을 밝힌 새 기준(`RESET_PREVIOUS_UNAVAILABLE`). 첫 기준으로 보이지 않는다 |
| 조회 실패 | `UNAVAILABLE`(2초·5초 간격으로 3번 읽어도 실패) | **새 기준을 만들지 않는다.** 단계 `PREVIOUS`에서 멈추고 파일을 보류한다 |
| 손상된 응답 | `INVALID`(HTTP 200이지만 JSON·크기·규격 오류) | **새 기준을 만들지 않는다.** 단계 `PREVIOUS`에서 멈추고 파일을 보류한다 |

- 순서: 이전 공개본 읽기 → 수집 → 만들기 → 검사 → 임시 파일에서 바꿔 쓰기.
- 검사는 규격 검증(`require_macro_evidence`)에 더해 `require_successor`로 실제 출력을 본다:
  - `generated_at` = 이번 시도 시각
  - `previous`·`continuity`가 이전 공개본 읽기 결과와 맞음
  - 수집 시작 ≤ 생성 시각
  - 전체 상태가 지표 상태와 맞음
  - 정상본 뒤라면 `continues`를 만족해야 한다: 같은 수집 시작, 더 늦은 생성, 발표·사건 기록은 뒤에 붙기만 함, 계열마다 기준 시각 유지, 성공 시각이 앞당겨지지 않음, 이력 유지, 이번에 못 모은 계열은 관측·성공 시각 그대로
- LIVE 개수는 기준이 아니다. 부분 수집은 정상 결과다.
- 실패 + 정상본 있음: 정상본 바이트를 그대로 둔다. 값·기준일·확인 시각·`generated_at`이 그대로이고, 상태에 `PREVIOUS_KEPT`를 쓴다.
- 실패 + 정상본 없음, 이전본 읽기 실패·손상, 쓰기도 실패: 상태에 `WITHHELD`와 실제 사유(`previous`, 단계, 예외 종류 이름)를 쓰고 1을 돌려준다. 호출부가 파일을 보류한다.
- 새 파일을 쓴 뒤 요약·상태 기록에서 오류가 나면 `STATUS_WRITE_FAILED`만 찍고, `BUILD_FAILED`로 찍지 않는다.

**상태 파일 `macro-evidence-status.json` (`macro-evidence-status/1`, `macro/evidence_lines.py`)**
- 이번 시도를 자료와 따로 적는다:
  - 시각, `BUILT`/`FAILED`, 실패 단계, 예외 종류 이름
  - 게시 결과 `NEW`·`PREVIOUS_KEPT`·`WITHHELD`(파일 없음. 사유는 `previous`와 단계로 구분)
  - 옆 자료의 `generated_at`·SHA-256, 이전 공개본 읽기 결과
- 값·URL·메시지는 넣지 않는다.
- Pages 가드는 이 이름 하나만 허용하고 엄격 검증한다.

**수동 화면 배포 (`--preserve-only`, cockpit-pages)**
- 공개 정상본은 바이트 그대로 옮긴다. 상태 기록은 그 파일을 설명할 때만 같이 옮긴다.
- 공개 정상본이 없으면(404 또는 빈 기본값) 빌드의 빈 기본값을 보류한다. 공개 `WITHHELD` 기록은 함께 옮긴다.
- 공개본을 읽지 못하면 빈 기본값을 그대로 두고 배포 검사가 판단한다. 정상본이 공개돼 있으면 거부(`EMPTIED`).

**배포 검사 (`tools/pages_freshness_guard.py`)**
- 실제 배포 산출물을 배포 직전 공개본과 비교한다.
- D-CV16 (a)와 대조한 결과:
  - 파일 단위 `WITHHELD`(이 파일만 빠지고 나머지 배포는 계속)는 중앙 V와 같게 유지한다.
  - 배포 직전 공개본 조회 실패는 중앙 V와 같이 배포 전체를 거부한다(`PAGES_FRESHNESS_LIVE_UNREACHABLE … deploy=REFUSED`). 자동 통과하지 않는다.

| 경우 | 판정 |
| --- | --- |
| 배포 직전 공개본 조회 실패 | 거부 (배포 전체) |
| 산출물에 빈 기본값: 공개 정상본 위 | 거부 (`EMPTIED`) |
| 산출물에 빈 기본값: 그 밖 | 거부 (`PLACEHOLDER`) |
| 산출물 파일 손상 | 거부 (`ARTIFACT_INVALID`) |
| 공개본보다 오래됨 | 거부 (`OLDER`) |
| 같은 시각인데 바이트가 다름 | 거부 (`CHANGED`) |
| 더 늦지만 공개 정상본을 잇지 않음(기록 빠짐, 시각 다시 찍힘, 정상본 위 새 기준) | 거부 (`DISCONTINUOUS`) |
| 상태 파일이 옆 자료와 맞지 않음 | 거부 (`STATUS_MISMATCH`) |
| 공개 정상본이 있는데 산출물에 파일 없음 | **보류** (`MISSING` → `WITHHELD`, `effect=LIVE_GOOD_COPY_REMOVED`, 배포 계속) |
| 공개본이 손상됨 | **보류** (`LIVE_INVALID` → `WITHHELD`, `effect=LIVE_INVALID_COPY_REPLACED`) |
| 정상본 유지(같은 바이트) | 통과 (`EQUAL`) |
| 더 새로운 정상 후속(일부 수집 포함, `continues` 만족) | 통과 (`NEWER`) |
| 공개 정상본 없음 | 통과 (`NO_LIVE`) |

- **보류는 보존이 아니다.** GitHub Pages는 산출물 전체로 사이트를 바꾼다. 그래서 공개 정상본이 있을 때 보류하면 그 파일이 사이트에서 빠진다.
  - 로그 줄에 `effect=LIVE_GOOD_COPY_REMOVED`로 적고, 화면에도 "이전 공개 파일도 이 배포에서 빠짐(보존 아님)"으로 보인다.
  - 다음 실행은 그 상태를 `REMOVED`로 읽고 기록 단절을 밝힌 새 기준으로 시작한다(손실을 숨기지 않음).
  - 수집 때만 읽기가 실패하고 배포 때는 읽히는 경우(일시 장애)가 여기에 해당한다. 배포 job이 공개본 바이트를 실어 나르게 하려면 배포 job에 새 업로드 단계가 필요하다. 중앙 V의 AUDIT 10-6-3과 같은 오너 결정 사항이라 이 PR에는 넣지 않았다(제안만).

**새 화면 (`screen-macro-live.js` 4.1.3)**
- 상태 파일을 페이지당 한 번 읽는다.
- 실패 + 정상본 유지: "이번 갱신 실패 (시각 · 단계) · 아래는 마지막 정상본 그대로 (생성 …) · 자료 지연".
- 정상본 없음: "근거 파일이 아직 게시되지 않았습니다"와 "이번 갱신 실패 … · 정상본이 없어 근거 파일을 게시하지 않음 (사유) · 0건이 아니라 미수집".
- 이전본 조회 실패·손상: "이번 갱신 실패 (시각 · 이전 공개본 조회 실패|손상된 응답) · 이전 기록을 이어받지 못해 근거 파일을 게시하지 않음 · 이전 공개 파일도 이 배포에서 빠짐(보존 아님)".
- 기록이 옆 자료와 맞지 않거나 규격이 틀리면 시도 줄로 쓰지 않는다.
- 옛 화면(`web_assets`)은 바꾸지 않았다. 파일이 없으면 기존처럼 "미게시"로 보인다.

**남은 위험**
- 수집 때만 공개본 읽기가 실패하면(재시도 뒤에도) 파일은 보류되고 공개 정상본은 사이트에서 빠진다. 기록은 다음 실행에서 단절로 드러난다.
- 막으려면 배포 job에서 검증된 공개본 바이트를 실어 나르는 단계가 필요하다(오너 결정). 그 전까지 이 경우는 "정상본 보존"이 아니다.

## 5. 시험 (실패 조건, 모두 실제 산출물 기준)

| 조건 | 시험 | 결과 |
| --- | --- | --- |
| 생성 실패 + 정상본 | `test_daily_generation_failure_with_a_good_copy_publishes_it_unchanged` | 산출물 = 공개본 바이트, `PREVIOUS_KEPT`, 배포 검사 `EQUAL` |
| 생성 실패 + 정상본 없음 | `test_daily_generation_failure_without_a_good_copy_withholds_the_file` | 파일 보류, `WITHHELD`. 공개본이 빈 기본값/없음이면 `NO_LIVE`, 정상이면 `WITHHELD` |
| 쓰기 실패 | `test_daily_write_failure` | 첫 쓰기만 실패: 정상본 유지(`WRITE`, `EQUAL`). 계속 실패: 보류 |
| 정상 부분 수집 | `test_daily_normal_partial_collection_is_published` | `PARTIAL`, 기록 이어 붙음, `NEWER` 통과 |
| 일관성 오류 출력 | `test_daily_inconsistent_output_never_replaces_the_good_copy` (5가지) | `VALIDATE` 실패, 정상본 유지 |
| 이전본 상태 4갈래 + 재시도 | `test_previous_read_states_are_told_apart` | LOADED / NO_LIVE / REMOVED / EMPTY_LIVE / UNAVAILABLE(3번 시도) / INVALID |
| 수집 때 조회 실패, 배포 때 조회 성공 | `test_a_failed_or_damaged_previous_read_never_publishes_a_new_baseline[unavailable]`, 배포 검사 `withheld` | 새 기준 만들지 않음, `PREVIOUS`/`OSError`, 배포 검사 `WITHHELD effect=LIVE_GOOD_COPY_REMOVED` |
| 배포 직전 조회도 실패 | `test_macro_live_read_failing_right_before_deploy_refuses_the_deploy` | 배포 전체 거부 |
| HTTP 200 + 손상된 JSON | `…[damaged]`, `test_macro_damaged_live_copy_is_withheld_not_kept` | 수집: `INVALID`/`JSONDecodeError` 보류. 배포: `LIVE_INVALID` 보류 |
| 확인된 부재 | `test_confirmed_absence_builds_and_says_whether_history_was_lost` | 처음: BASELINE. 빠진 뒤: RESET + `REMOVED` |
| 정상본이 있는데 기록이 빠진 새 산출물 | `test_a_new_file_missing_records_never_replaces_the_good_copy`, 배포 검사 `reset_over_good`·`lost_release`·`restamped` | 생성기 `VALIDATE` 실패로 정상본 유지, 배포 검사 `DISCONTINUOUS` 거부 |
| 화면 배포 보존 | `test_ui_deploy_preserve_never_publishes_the_placeholder_as_a_result` | 빈 기본값 보류, 읽기 실패면 `EMPTIED` 거부 |
| 사고 재현(빈 기본값 덮기) | `test_macro_incident_placeholder_replacing_a_good_copy_is_refused` | 거부 |

- daily 시험은 실제 호출부(`public_screens_pipeline.collect`)를 거쳐 만든 산출물 디렉터리에 Pages 가드와 배포 검사 규칙을 그대로 돌린다.
- 배포 검사 시험은 `pages_freshness_guard.run`을 산출물 폴더와 가짜 공개 사이트로 돌린다.

## 6. 중앙 V (따로 기록, 동작 변경 없음)

- 같은 실행: `QGV_OFFICIAL attempt=SUPPLY_FAILED reason=IEX_DOWNLOAD_FAILED published=KEPT_LAST_GOOD iex_curl_rc=28`.
  - 내려받기 시간 초과로 02:01:42 → 02:11:43, 약 10분이고, 단계 상한 12분 안이다.
- 공개 `qgv-official-status.json`: `SUPPLY_FAILED`, 시도 11/07 02:01Z.
  - 공식본은 11/06 검증, 가격 기준일 11/04 그대로다.
- 마지막 정상본이 유지됐다. 이 수정은 중앙 V 보존 동작을 바꾸지 않는다.
