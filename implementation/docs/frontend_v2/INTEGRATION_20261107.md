# 통합 가지 2026-11-07 (`claude/integration-20261107`)

오너 2026-11-07 「공통 분류 인수 및 남은 통합 마무리」 6항의 통합 기록이다. 각 PR의 CI 녹색은 통합 완료를 대신하지 않는다. 이 가지는 아래 PR 머리를 한 트리에 합쳐 따로 검증한다. 병합·배포 승인이 아니다.

## 1. 합친 순서와 머리

| 순서 | PR | 머리 | 내용 |
| --- | --- | --- | --- |
| 1 | #455 | `dfa23e8a` | 자료층 브라우저 시험 경합 고침(시험만) |
| 2 | #513 | `9d45f25c` → `1c9b858b` | 매크로 근거 실패 처리 + 배포 때 검증된 공개본 옮기기(워크플로 연결은 미적용 패치) |
| 3 | #510 | `ef4c721b` → `95db4e73` | 의외의 기업 + 섹터 QGV, 2.2.7 섹터 QGV 설정(요소·가중치) 저장 규칙, Codex #514 포함 |
| 4 | #511 | `507d0d77` | 4.5 정책·지정학(Codex #509·#512 포함) |
| 5 | #517 | `9736db69` | 기술 조건 필터 3.5 엄격 결합(#515), 명시적 `issuer_id`, 그룹 전체 행 |
| 6 | #518 | `88949a5f` → `c7e1da90` | 기능 ID 정렬, DC-48 공통 분류 기록, 2.2.7 이름 |
| 7 | Codex #516 | `9343b5e6` | `common-classification/1`(base #514 `8a483471` + #515 `b6fd0112`) |
| 8 | 공통 분류 화면 | `d04d862e` | `claude/common-classification-screens`: 판독기·화면·시험·문서 |

Codex 파일은 바꾸지 않았다. #516이 canonical 뒤로 바꾼 파일 161개가 이 가지에서 `9343b5e6`과 바이트가 같다.

## 2. 충돌과 해결 (모두 기계적)

- **#511 병합:**
  - DC 행은 번호 순, 결정 기록은 최신 먼저.
  - `data.js` STATIC은 canonical 6개, `macro-evidence-status.json`, 정책 4개 순이고 `BYTE_FILES`를 둔다.
  - loader LOAD_ORDER는 #510 파일, 정책 파일 순. CI 목록은 양쪽을 다 둔다. qgv node 기대 이름도 양쪽을 다 둔다. reuse LIVE는 LOAD_ORDER 순.
- **통합 전용 한 줄씩:** `web_app_discovery_browser_test.js`·`web_app_policy_impact_browser_test.js`의 미게시 허용 목록에 `macro-evidence-status.json`. #513이 자기 시험에 넣은 것과 같은 줄이다.
- **#518 병합:**
  - `FUNCTION_HIERARCHY_ADDITIONS.md`(add/add)는 #518 판을 쓴다(#510 문장을 포함하는 상위 판).
  - FUNCTION_STATUS 행은 #518의 기능 번호와 #510·#511의 근거 열을 합친다.
- **#510 2.2.7 저장 규칙:** FUNCTION_STATUS 갱신 줄은 양쪽을 다 두고, 2.2.7 행의 남은 것 열에 저장 규칙을 더했다.

## 3. 중복 변경 대조

| 중복 | 관계 | 처리 |
| --- | --- | --- |
| #505 파일 41개 (#510 안, #516 base 안) | 같은 Codex 커밋 | 두 머리에서 바이트 동일. 한 번만 들어감 |
| #515 fixture `inputs.json`·`expectations.json` | #517은 Main 경로 `tests/fixtures/technical_filter_join_v1/` 사본(SHA-256 고정), #516은 Codex 경로 `tests/research/fixtures/…` 원본 | 바이트 동일. #515가 canonical에 들어가면 Main 사본을 지우고 Codex 경로를 읽게 바꾼다(후속) |
| `join_filtered_rows`의 `issuer_id` 확장 | #516(Python)·#517(JS 판독기) | 같은 규칙: 필드가 있으면 그 값으로 발행사 검사, 명시적 null은 대체 없음 |
| #455 시험 고침 | #518에 cherry-pick(`88949a5f`, CI 경합 대응) | 같은 내용. #455가 먼저 들어가면 no-op |
| `macro-evidence-status.json` 미게시 허용 | #513 시험 + 통합 전용 두 줄 | 위 2절 |

## 4. 검증

(전체 시험 결과를 여기에 적는다)
