# 저장설정 복원·재실행 호환성 — 2026-11-07

코덱스. 기능 2.2.3·2.2.6의 연구 계산 지원 범위다. 새 기본 선택은
`sector-qgv-default/0.1.0`과 **내 설정**이고, 기존 프리셋의 ID·저장설정·과거
결과는 보존한다. 화면 선택기·기기 저장·운영 연결은 Main 소유다.

기반은 #505 `e3df0c1ecb1ad7cda4593dffc55fa5d7ea78edd6`, 후속 가지는
`research/sector-settings-compat-20261107`이다. canonical
`ab6a83c3be2276abdcf855c71c5f273926e2dcc4`는 이 기반의 조상이다. 기존 #505
머리와 그 결과 파일은 수정하지 않았다.

## 확인된 공백과 최소 변경

기존 `save_user_config`의 6필드 기록은 그대로 유지한다:
`config`, `canonical_config_hash`, `preview_id`, `snapshot_id`, `universe_id`,
`universe_version`. Main #507 판독기는 정확히 이 6키를 요구한다.

이 기록만으로는 과거 계산을 식별할 수 없다. 엔진·입력 버전과 입력 해시는
보관된 preview에, 요인별 산식 버전과 모집단 구성원은 snapshot에 있다.
기존 CLI에는 저장 기록 전용 복원 경로가 없었다. 새 `saved_config` 필드를
보내도 읽지 않고 기본 설정으로 실행되던 사례를 신규 시험에서 확인했다.

`research/sector_qgv_restore.py::replay_saved_config`는 저장 기록, 보관 preview,
원래 snapshot을 함께 받아 기존 `save_user_config`, `assert_retained_preview`,
`preview_qgv`를 재사용한다. 계산기·프리셋·산식을 복제하거나 바꾸지 않는다.
새 요청 ID/preview ID 외의 모든 버전·해시·시점·결과 필드가 같아야 성공한다.
입력값, 모집단, 산식, 정책, 설정, 보관 결과가 달라지면 거부한다. 같은
snapshot ID에 다른 값이 들어가도 거부한다. display/Lynch 설정도 원본대로
복원하며 수치에 기업유형 배수를 더하지 않는다.

기존 CLI `mode=normalized`에 `saved_config`와 `retained_preview`의 해시 고정
파일 참조를 함께 주면 이 API를 호출한다. 이때 별도 `config`, `main_request`,
비교 처리 또는 다른 mode를 함께 지정하면 `SAVED_REPLAY_JOB_CONFLICT`다.
모형 자동 선택·자동 변환·최신 입력으로의 자동 교체는 없다. 결과는 기존
CLI의 새 출력 디렉터리에만 쓰고, 기존 경로에는 `OUTPUT_ALREADY_EXISTS`로
거부한다. 원래 manifest·snapshot·preview·saved-config 바이트는 보존된다.

## 유지되는 식별자와 정책

| 구분 | 식별자·버전 | 복원 정책 |
| --- | --- | --- |
| 새 기본 / 내 설정의 기반 | `sector-qgv-default/0.1.0`, `sector-qgv-config/1` | 저장된 전체 scoped override·config ID·표시 설정 보존 |
| 섹터 계산 | `sector-qgv-engine/0.1.0`, `sector-midrank-strict20/1`, `strict/1`, `book-sector-map/1` | 유효 peer 최소 20, fallback 없음, 양의 비중 필수요인 strict 결측, 기업유형 배수 없음 |
| 섹터 관문 | `official-q-percentile-required/1`, 입력 calc `qgv2-calc/2026-10-23.1` | 관문 UNKNOWN이면 최종 총점·순위 null 유지 |
| 공격형 | `user-preset/aggressive@0.1` | Q30/G50/V20, 기존 개인 프로필 경로 |
| 균형형 | `user-preset/balanced@0.1` | Q40/G30/V30, 기존 개인 프로필 경로 |
| 수비형 | `user-preset/defensive@0.1` | Q55/G15/V30, 기존 개인 프로필 경로 |
| 기존 프로필 저장 | `device-profile-drafts/2`, 키 `investment.web.v1.profile-drafts-v2` | 기존 `qgv2-*` 프로필 ID·정수 version·가중치·`type_weights`·`gate` 보존 |
| 기존 calc23.1 계열 | 기존 공식/개인 계산기 | 유효 비중 50% 이상 재배분, 업종 peer 8/전체 fallback, 기존 기업유형 정책을 섹터 strict20으로 바꾸지 않음 |

공격형·균형형·수비형은 `balanced/quality/growth/value` 코드 프리셋과도 다른
ID다. 섹터 복원 API에 구 프리셋 ID를 넣으면 거부하며 모형을 골라주지 않는다.
기존 프로필 저장 스키마에는 출발 프리셋 ID·calc/input/universe 버전이 없다.
따라서 그 프로필만으로 과거 계산 재현성을 주장하지 않는다. 실제 과거
결과는 원래 엔진·입력·결과 기록으로 보존하고, 누락 버전을 추측해 채우지
않는다. 신규 시험은 합성 입력과 현재 보관 엔진으로 설정 복원 동등성만
확인한다.

## 검증 결과와 재현

**38개 신규 호환 시험 + 변경 CLI의 기존 진입점 2개 = 40 passed.**

- 실제 CLI에서 사용자 Q60/G25/V15 저장 → JSON 복원 → 새 요청 재실행:
  설정·결과 행·입력/모형/모집단 identity 동일, 원래 출력 바이트 불변.
- 새 기본 및 내 설정의 strict 결측, peer 19, 관문 UNKNOWN, Lynch 표시:
  복원 뒤 null·사유·수치 정책 유지.
- 모형/엔진/정규화/분류/입력/모집단/시점/해시 14경계, 산식·입력값·필터된
  모집단·가중치·구 프리셋·결측정책·보관 결과 10경계: 재실행 거부.
- 기존 실제 Node `saveV2` → `writeV2` → `readV2` → `scoreUniverse` API:
  세 구 프리셋의 프로필 ID·version·가중치와 저장 바이트, 복원 전후 결과
  동일. `type_weights=false`·`gate=false`로 저장한 내 설정도 그대로 복원.
- Main #507 `f9101b7339b3c3d7becc414d7450626116391484`의 실제 bridge 소스를
  수정 없이 로드하여 `answer(context/preview/save)` 호출: 성공. 그 저장
  기록을 새 replay API로 재실행한 결과 행 동일, 실제 Node
  `sector-qgv.js::validateSaved`도 `{ok:true}`. #510
  `a932ffebd4b3db8326df20a19507fb8c1930aa1b`의 bridge·판독기 파일 blob도
  동일하다. 브라우저 화면·배포 검증을 뜻하지 않는다.

저장·복원 경계 시험과 변경 영향 범위만 실행했다. 이미 완료된 실자료 Q/G
비교, V 재개 입력·보관자료, 전체 엔진 합성 시험은 다시 계산하지 않았다.
새 실자료 계산 **0**, 채택 증가 **0**, 수집·병합·배포 **0**이다.

```sh
PYTHONPATH=implementation/src python -m pytest -q \
  implementation/tests/research/test_sector_qgv_saved_restore.py \
  implementation/tests/test_sector_qgv.py::test_cli_hashes_and_saved_config \
  implementation/tests/test_sector_qgv_main.py::test_existing_cli_accepts_editor_request_and_writes_engine_response
```

CLI 재현은 위 첫 시험이 새 임시 디렉터리에서 실제 프로세스로 수행한다.
직접 호출할 때 다음 job의 각 파일은 원래 실행의 파일이며 sha256은 해당
바이트의 실제 해시다. 원래 전체 모집단을 넣고 새 출력 경로를 사용한다.

```json
{
  "mode": "normalized",
  "data_kind": "SYNTHETIC",
  "request_id": "saved-settings-replay",
  "snapshot": {"path": "/tmp/original/snapshot.json", "sha256": "<원본 해시>"},
  "saved_config": {"path": "/tmp/original/saved-config.json", "sha256": "<원본 해시>"},
  "retained_preview": {"path": "/tmp/original/preview.json", "sha256": "<원본 해시>"}
}
```

```sh
PYTHONPATH=implementation/src python implementation/tools/sector_qgv.py \
  --job /tmp/saved-replay-job.json --output /tmp/new-saved-replay --synthetic
```

## Main 소비자 차이

현재 #507의 6필드 저장 판독에는 변경이 필요 없다. 새 연구 API/CLI는 기기
저장 형식과 별개의 **원래 입력에 대한 재실행** 경로다. 현재 화면은
저장된 `config`를 고른 입력으로 미리보기하며, 이 동작을 과거 결과 재현으로
표시해서는 안 된다. 과거 재실행을 연결하려면 보관 preview와 snapshot을
함께 공급하고 실패 시 기존 결과를 유지해야 한다.

현재 화면의 `readSaved()`는 `base_preset_id`만 보고 OK/BASE_DIFFERS를 구분한다.
엔진은 나머지 정책/버전 불일치를 거부하지만, 화면 복원 안내와 새 기본/내
설정 선택기의 경계 표시는 Main 소유다. BASE_DIFFERS에서 현재 기본값으로
편집하더라도 기존 기록을 바꿨다고 표시하거나 자동 저장하지 않는다.
구 프로필과 섹터 저장 키도 분리해서 보존한다. 기존 구 프로필에 없는
버전을 새 모델 버전으로 채우는 마이그레이션은 요청하지 않는다.

기존 cockpit-pages의 Full Python unit suite가 `tests/` 아래 연구 시험을
자동 발견하므로 CI 목록·공용 의존성 추가는 필요하지 않다.
프론트엔드·워크플로·가드·CI 목록·결정 문서는 이 변경에 포함하지 않는다.
