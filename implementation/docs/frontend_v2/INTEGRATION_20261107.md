# 통합 가지 2026-11-07 (`claude/integration-20261107`)

오너 2026-11-07 「공통 분류 인수 및 남은 통합 마무리」 6항의 통합 기록이다. 각 PR의 CI 녹색은 통합 완료를 대신하지 않는다. 이 가지는 아래 PR 머리를 한 트리에 합쳐 따로 검증한다. 병합·배포 승인이 아니다.

## 1. 합친 순서와 머리

| 순서 | PR | 머리 | 내용 |
| --- | --- | --- | --- |
| 1 | #455 | `dfa23e8a` | 자료층 브라우저 시험 경합 고침(시험만) |
| 2 | #513 | `9d45f25c` → `5af1cb69` | 매크로 근거 실패 처리 + 배포 때 검증된 공개본 옮기기(워크플로 연결은 미적용 패치) |
| 3 | #510 | `ef4c721b` → `934dd96a` | 의외의 기업 + 섹터 QGV, 2.2.7 섹터 QGV 설정(요소·가중치) 저장 규칙, Codex #514 포함 |
| 4 | #511 | `507d0d77` | 4.5 정책·지정학(Codex #509·#512 포함) |
| 5 | #517 | `9736db69` | 기술 조건 필터 3.5 엄격 결합(#515), 명시적 `issuer_id`, 그룹 전체 행 |
| 6 | #518 | `88949a5f` → `6661ade6` | 기능 ID 정렬, DC-48 공통 분류 기록, 2.2.7 이름 |
| 7 | Codex #516 | `9343b5e6` | `common-classification/1`(base #514 `8a483471` + #515 `b6fd0112`) |
| 8 | 공통 분류 화면 | `828be663` | `claude/common-classification-screens`: 판독기·화면·시험·문서, 기술 결합 반례(Codex 기대값 = Node = 실제 호출부 브라우저) |

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

- 저장소 전체 시험(이 가지 `7cf13f11`의 트리): Python 5,279 + 하위 512, node·Worker, 저장소 가드, 빌드, Pages 가드, 브라우저 107개 파일 모두 통과(실패 0).
- 각 PR 머리의 전체 시험은 PR마다 따로 돌렸다(#513 `1c9b858b`, #510 `934dd96a`, #517 `9736db69`, #518 `6661ade6`). 각 PR이 녹색이라고 해서 이 통합 결과를 대신하지 않는다.
- #510 `95db4e73`의 첫 전체 시험에서 실제 결함 1건이 나왔다. 대기 문구에 기능 번호 숫자가 들어가 `web_app_qgv_browser_test.js`가 실패했다. `69bef7b4`·`934dd96a`로 고쳤고, 이 가지에도 들어 있다.
- CI #519 `23dd5dc5`의 build는 `web_app_policy_impact_browser_test.js`의 widths 단계에서 "Execution context was destroyed"로 실패했다.
  - 로컬 통합 트리에서 부하가 있을 때 대략 3번에 1번 재현했다. #511 단독에서는 한 번도 나지 않았다.
  - 추적 결과: 상세를 연 지 약 0.3초 뒤 `page.evaluate(IS2.ready)`의 문맥만 사라졌다. 탐색·탐색 요청·충돌·페이지 오류는 기록되지 않았다. **원인은 특정하지 못했다.**
  - `828be663`에서 그 단계를 locator 대기로 바꿨다. 확인 항목은 그대로이고, 고친 뒤 부하 속 8번 중 8번 통과했다.
