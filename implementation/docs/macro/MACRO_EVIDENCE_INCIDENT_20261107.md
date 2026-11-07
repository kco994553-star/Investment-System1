# 매크로 근거 파일 빈 기본값 게시 (2026-11-07) · 원인과 수정

이 수정은 오너 11/07 두 지시를 따른다.
- 「매크로 근거 자료 운영 복구를 최우선으로 진행하라」
- 2차 「매크로 장애 원인 구분 및 복구·재발 방지 진행」

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
- 다음 정상 실행은 공개본을 `EMPTY_LIVE`로 읽고 continuity `RESET_PREVIOUS_UNAVAILABLE`로 새 기준을 시작한다. 11/06까지의 발표·수정 기록은 이어지지 않는다.
- 오래된 값을 최신 수집처럼 다시 만들거나 확인 시각을 새로 고치지 않는다.

## 4. 수정 (이 PR)

**호출부 `tools/public_screens_pipeline.py`**
- 생성기 반환값이 0이 아니거나 예외가 나면 `macro_evidence.withhold(out)`를 부른다.
  - 산출물의 근거 파일은 검증된 정상본일 때만 남긴다.
  - 빈 기본값이나 그 밖의 파일은 지워서 게시하지 않는다.
  - 로그: `MACRO_EVIDENCE WITHHELD file=macro-evidence.json reason=NO_GOOD_COPY`.
- SEC 수집은 지금처럼 멈추지 않는다. 워크플로 파일은 바꾸지 않았다.

**생성기 `tools/macro_evidence.py`**
- 순서: 이전 공개본 읽기 → 수집 → 만들기 → 검사 → 임시 파일에서 바꿔 쓰기. 이전 공개본 읽기 결과는 `LOADED`·`EMPTY_LIVE`·`NO_LIVE`·`UNAVAILABLE`·`INVALID`로 남는다.
- 검사는 규격 검증(`require_macro_evidence`)에 더해 `require_successor`로 실제 출력을 본다:
  - `generated_at` = 이번 시도 시각
  - `previous`·`continuity`가 이전 공개본 읽기 결과와 맞음
  - 수집 시작 ≤ 생성 시각
  - 전체 상태가 지표 상태와 맞음
  - 정상본 뒤라면: 같은 수집 시작, 더 늦은 생성, 발표·사건 기록은 뒤에 붙기만 함, 이어온 관측을 잃지 않음
- LIVE 개수는 기준이 아니다. 부분 수집은 정상 결과다.
- 실패 + 정상본 있음: 정상본 바이트를 그대로 둔다. 값·기준일·확인 시각·`generated_at`이 그대로이고, 상태에 `PREVIOUS_KEPT`를 쓴다.
- 실패 + 정상본 없음, 또는 쓰기도 실패: 상태에 `NO_GOOD_COPY`를 쓰고 1을 돌려준다. 호출부가 파일을 보류한다.
- 새 파일을 쓴 뒤 요약·상태 기록에서 오류가 나면 `STATUS_WRITE_FAILED`만 찍고, `BUILD_FAILED`로 찍지 않는다.

**상태 파일 `macro-evidence-status.json` (`macro-evidence-status/1`, `macro/evidence_lines.py`)**
- 이번 시도를 자료와 따로 적는다:
  - 시각, `BUILT`/`FAILED`, 실패 단계, 예외 종류 이름
  - 게시 결과 `NEW`·`PREVIOUS_KEPT`·`NO_GOOD_COPY`
  - 옆 자료의 `generated_at`·SHA-256, 이전 공개본 읽기 결과
- 값·URL·메시지는 넣지 않는다.
- Pages 가드는 이 이름 하나만 허용하고 엄격 검증한다.

**수동 화면 배포 (`--preserve-only`, cockpit-pages)**
- 공개 정상본은 바이트 그대로 옮긴다. 상태 기록은 그 파일을 설명할 때만 같이 옮긴다.
- 공개 정상본이 없으면(404 또는 빈 기본값) 빌드의 빈 기본값을 보류한다. 공개 `NO_GOOD_COPY` 기록은 함께 옮긴다.
- 공개본을 읽지 못하면 빈 기본값을 그대로 두고 배포 검사가 판단한다. 정상본이 공개돼 있으면 거부(`EMPTIED`).

**배포 검사 (`tools/pages_freshness_guard.py`)**
- 실제 배포 산출물을 공개본과 비교한다.
- 다른 기능 배포는 기존 운영 정책(중앙 V의 D-CV16 (a))에 맞췄다. 이 파일만 보류하고 나머지 배포는 계속한다.

| 경우 | 판정 |
| --- | --- |
| 공개 정상본을 빈 기본값으로 덮음 | 거부 (`EMPTIED`) |
| 산출물 파일 손상 | 거부 (`ARTIFACT_INVALID`) |
| 공개본보다 오래됨 | 거부 (`OLDER`) |
| 같은 시각인데 바이트가 다름 | 거부 (`CHANGED`) |
| 상태 파일이 옆 자료와 맞지 않음(빈 기본값 옆의 어떤 기록이든 포함) | 거부 (`STATUS_MISMATCH`) |
| 공개 정상본이 있는데 산출물에 파일 없음(이번 실행이 정상본 없이 보류) | **보류** (`MISSING` → `WITHHELD`, 배포 계속) |
| 공개본이 규격 오류 | **보류** (`LIVE_INVALID` → `WITHHELD`) |
| 정상본 유지(같은 바이트) | 통과 (`EQUAL`) |
| 더 새로운 정상 수집(일부 수집 포함) | 통과 (`NEWER`) |
| 공개 정상본 없음 | 통과 (`NO_LIVE`) |

**새 화면 (`screen-macro-live.js` 4.1.3)**
- 상태 파일을 페이지당 한 번 읽는다.
- 실패 + 정상본 유지: "이번 갱신 실패 (시각 · 단계) · 아래는 마지막 정상본 그대로 (생성 …) · 자료 지연".
- 정상본 없음: "근거 파일이 아직 게시되지 않았습니다"와 "이번 갱신 실패 … · 정상본이 없어 근거 파일을 게시하지 않음 · 0건이 아니라 미수집".
- 기록이 옆 자료와 맞지 않거나 규격이 틀리면 시도 줄로 쓰지 않는다.
- 옛 화면(`web_assets`)은 바꾸지 않았다. 파일이 없으면 기존처럼 "미게시"로 보인다.

**남은 위험 (동작 변경 안 함)**
- 수집 때 공개본 읽기가 네트워크 오류(`UNAVAILABLE`)이면, 지금처럼 새 기준(`RESET_PREVIOUS_UNAVAILABLE`)으로 만든다. 배포 검사는 `NEWER`로 통과시킨다. 공개 정상본이 있는데도 이어온 기록이 끊길 수 있다.
- 그때 생성도 실패하면 파일은 보류(`WITHHELD`)되고, 다음 정상 실행까지 사이트에서 빠진다. 중앙 V와 같은 알려진 잔여 위험이다.
- 배포 job에서 공개본을 다시 실어 나르려면 새 업로드 단계가 필요하다. 이는 오너 결정 사항이다.

## 5. 시험 (실패 조건)

| 조건 | 시험 | 결과 |
| --- | --- | --- |
| 생성 실패 + 정상본 | `test_daily_generation_failure_with_a_good_copy_publishes_it_unchanged` | 산출물 = 공개본 바이트, `PREVIOUS_KEPT`, 배포 검사 `EQUAL` |
| 생성 실패 + 정상본 없음 | `test_daily_generation_failure_without_a_good_copy_withholds_the_file` | 파일 보류, `NO_GOOD_COPY`. 공개본이 빈 기본값/없음이면 `NO_LIVE`, 정상이면 `WITHHELD` |
| 쓰기 실패 | `test_daily_write_failure` | 첫 쓰기만 실패: 정상본 유지(`WRITE`, `EQUAL`). 계속 실패: 보류(`WITHHELD`) |
| 정상 부분 수집 | `test_daily_normal_partial_collection_is_published` | `PARTIAL`, 기록 이어 붙음, `NEWER` 통과 |
| 일관성 오류 출력 | `test_daily_inconsistent_output_never_replaces_the_good_copy` (5가지) | `VALIDATE` 실패, 정상본 유지 |
| 화면 배포 보존 | `test_ui_deploy_preserve_never_publishes_the_placeholder_as_a_result` | 빈 기본값 보류, 읽기 실패면 `EMPTIED` 거부 |
| 사고 재현(빈 기본값 덮기) | `test_macro_incident_placeholder_replacing_a_good_copy_is_refused` | 거부 |

- 위 daily 시험은 실제 호출부(`public_screens_pipeline.collect`)를 거쳐 만든 산출물 디렉터리에 Pages 가드와 배포 검사 규칙을 그대로 돌린다.

## 6. 중앙 V (따로 기록, 동작 변경 없음)

- 같은 실행: `QGV_OFFICIAL attempt=SUPPLY_FAILED reason=IEX_DOWNLOAD_FAILED published=KEPT_LAST_GOOD iex_curl_rc=28`.
  - 내려받기 시간 초과로 02:01:42 → 02:11:43, 약 10분이고, 단계 상한 12분 안이다.
- 공개 `qgv-official-status.json`: `SUPPLY_FAILED`, 시도 11/07 02:01Z.
  - 공식본은 11/06 검증, 가격 기준일 11/04 그대로다.
- 마지막 정상본이 유지됐다. 이 수정은 중앙 V 보존 동작을 바꾸지 않는다.
