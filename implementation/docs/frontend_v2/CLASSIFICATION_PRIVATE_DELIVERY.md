# 공통 분류 보관 묶음 · 비공개 전달 (2026-11-08)

근거: 오너 2026-11-08 「통합 결과 수령」 2항.
- "기존 인증 구조를 이용한 보존 분류 묶음의 비공개 전달 연결."
- "공개 분류 파일 게시를 비공개 개발 연결의 선행 조건으로 만들지 않는다."

이 문서는 병합·워크플로 적용·배포·신규 취득 승인이 아니다.

## 1. 경로

DC-44(#493)의 구조를 그대로 쓴다. 구조는 다음 세 가지다.
- 오너 Google 로그인
- Worker의 서버 쪽 오너 확인
- 읽기 전용 토큰으로 비공개 저장소 `data` 가지의 파일을 그대로 넘김

| 층 | 무엇 | 파일 |
| --- | --- | --- |
| Worker | `GET /kis/classification?part=<view·technical·macro·qgv_links·dictionary·expanded_summary>` → `classification/<part>.json`. 읽을 때마다 오너를 확인한다. 각 부분은 자기 Codex 스키마여야 넘긴다. 저장·로그·리다이렉트 없음 | `implementation/worker/src/index.js` |
| 클라이언트 | 경로 이름은 `kis-private.js` 한 파일에만 있다(좁은 예외 목록 8개). Bearer 헤더만 보내고, `credentials: omit`·`no-store`·`no-referrer`를 쓴다 | `web_app/kis-private.js`, `web_app/prices.js` |
| 화면 | 기업 상세 공통 분류 칸 아래 "공통 분류 보관 묶음" 비공개 패널. 한 번 누르면 여섯 부분(운영504 다섯 + 확장 표본 요약)을 5초 간격으로 차례로 읽는다. view는 반드시 있어야 하고, 나머지는 없으면 빼고 대신 채우지 않는다 | `web_app/private-expand-live.js`, `screen-search-live.js` |
| 판독 | `IS2.classification.connectPrivate`가 묶음 전체를 검사한다. 통과하면 RAM의 현재 원천이 된다(`delivery: PRIVATE`). 모든 화면이 같은 묶음을 읽는다 | `web_app/classification.js` |
| 해제 | 접기·연결 끊기·403·토큰 만료 → `disconnectPrivate`. 화면은 NONE으로 돌아간다 | 같은 파일 |

- 화면 문구는 "비공개 보관본 · 인증 경로 · 게시본 아님"이다.
- 공식 QGV 순위·TARGET·공개 파일은 바뀌지 않는다. 화면이 분류를 다시 추론하지 않는다.

## 2. 비공개 저장소 배치 (2026-11-08 2차 갱신 · 경계 정책판)

배치 위치는 `investment-system1-kis-private` `data` 가지 `classification/`이다(@ `7ec77023`). 전체 SHA는 PR 본문에 적는다.

**도구** `implementation/tools/stage_private_classification.py`
- 인계 명세의 크기·SHA-256과 각 부분의 스키마를 확인한다.
- 분류 해시·평가일이 묶음 전체에서 같아야 한다.
- 판 짝은 `VERSION_PAIRS` 두 가지뿐이다. 사전 판은 view의 판과 같아야 하고, `/2`면 view와 사전이 같은 경계 정책을 적어야 한다.
- 새 판은 옆에 써서 다시 해시한 뒤 통째로 바꾼다. 하나라도 실패하면 기존 `classification/`을 그대로 둔다(오너 2026-11-08 3항).
- 공개 저장소 안으로는 쓰지 않는다. 파일 상한·인증은 바꾸지 않았다.

**운영504** (Universe504, 화면들이 읽는 기록)
- **출처:** raw `handoff/input-recovery-20261103` @ `6168ce2`, `handoffs/common-boundary-policy-20261108/delivery-compatible/`
- **생산자:** Codex #520 `41f2a25b`
- **판:** `common-industry-dictionary/2` + `common-classification-map/2`, 경계 정책 `common-sector-boundaries/2026-11-08.1`
- 다섯 부분을 바이트 그대로 옮겼다.

| 부분 | 바이트 | SHA-256 |
| --- | --- | --- |
| view | 1,844,958 | `fa3fdc17e19aead20fa25e8742356fc7680b2762b7cc11e33f65a38e2f90df35` |
| technical | 199,671 | `f1f55f16a2b1b3f01f4e8c0cf1b5194a6691aeb8dc36a4a976020b3bd6784715` |
| macro | 900,223 | `e207ff37e0bc3670c1d12bd0d9abf1c6c9e6e9ca5d45ade9a74e6a8ec251fe5b` |
| qgv_links | 79,672 | `67f716910b68fe90e7f9114a59e93bb8ddbb6b18db6154497f56040b06c41b83` |
| dictionary | 3,374 | `cfd693371bea04dc8b10328db9f7ff71016ca250b5a696c7b7997d11fd156a3f` |

**확장 발행사 표본** (별도 모집단)
- `final/summary.json`만 `expanded_summary`로 옮겼다. 2026-11-08 2차로 Codex #523 `6fc7a673`의 요약으로 바꿨다(`data` @ `af36a27`).
  - 출처: raw @ `418ff2e` `handoffs/classification-count-summary-20261108/final/summary.json`
  - 크기·해시: 19,300 바이트, `98f3e2095aa630a408c87d151135009c85d3641abaee5924b5373596d899eab4`
  - 새 선택 필드 `calculation_counts`(`common-classification-calculation-counts/1`)가 들어 있다. 앞 요약(3,194 바이트, `0e0de51e…`)은 이 필드의 `source_summary`로 남아 있다.
  - 배치 도구는 이 필드의 운영 범위가 같이 배치되는 view 바이트(`fa3fdc17…`)와 그 해시·평가일·504행을 가리키는지 확인했다. 다른 다섯 부분은 바뀌지 않았다.
- 확장 view·preview는 Worker 파일 상한 2MB를 넘어 옮기지 않았다.
- 행 단위 화면: 2026-11-09 Codex #524 전달본(목록표·색인·커버리지·상세 조각)으로 연결했다(Draft #526, [EXPANDED_DICTIONARY_20261109](EXPANDED_DICTIONARY_20261109.md) 2절). 그 전 판에서는 "확장 발행사 행 단위 화면은 아직 없음 · 요약만 연결됨"으로 적었다.

**앞선 배치:** 다음 둘은 더 이상 현재 전달본이 아니다. 판독기는 `/1` 묶음도 계속 읽는다.
- `/1` 완료본(raw @ `6f940b9c`, view `07cae91f…`)
- 11/07 묶음(`d6196b6`)

## 3. 실자료 대조 (로컬, 배포 아님 — 개수만 기록)

- **실행 방식:** 통합 가지의 실제 Worker 처리 코드와 실제 판독기로 여섯 부분을 받았다. GitHub와 Google은 디스크·고정 응답으로 대신했고, 네트워크는 쓰지 않았다.
- **결과:**
  - 받은 바이트 = 배치 바이트
  - 분류 버전 불일치 0
  - 평가일 2026-11-04 · `RETAINED_INPUT`
  - 판 `/2` + `/2`, 경계 정책 `common-sector-boundaries/2026-11-08.1`
- **운영504 개수** (오너 비교 대상과 같음):

  | 항목 | 개수 |
  | --- | --- |
  | 기업 행 | 504 |
  | 섹터 확인 | 456 |
  | 하위 산업 확인 | 92 |
  | 회계모형 확인 | 424 |
  | 섹터·회계모형 둘 다 확인 | 424 |
  | 미분류 | 48 |

  기록 상태: `SECTOR_ONLY` 364 · `CONFIRMED` 92 · `UNRESOLVED` 46 · `NO_DATA` 2

  섹터 QGV 원결과의 Q·G 산출 수(`calculation_counts`, #523, 원결과 집계·재계산 없음): Q 232/504, G 320/504. 평가일 2026-11-04.
  - 운영504의 공식 Q 관문 입력 연결은 이 요약에서 미측정(`NOT_MEASURED`)이다. 0으로 보이지 않는다.
  - 섹터 미리보기 자체(약 8.4MB)는 여전히 Worker 상한 2MB를 넘어 옮기지 않았다.
- **확장 표본 개수** (별도로 보임, 서로 더하지 않음):

  | 범위 | 발행사 | 섹터 | 회계모형 | Q | G |
  | --- | --- | --- | --- | --- | --- |
  | 관측 카탈로그 전체 | 8,004 | 935 | — | 495 | 671 |
  | 보유 재무 하위표본 | 1,057 | 929 | 844 | 494 | 670 |

  - 전체시장 분모·커버리지는 null, 새 증권 ID는 0이다.
  - 공식 Q 관문 입력 연결: 관측 카탈로그 483/8004, 보유 재무 하위표본 478/1057(`calculation_counts`)
    - 기존 Universe504 공식 Q 재생값의 입력 연결이다.
    - 관문 통과 수도, 새 섹터 Q 산출 수도, 확장 표본 Q도 아니다.
- **기술 투영:** 그룹 10개(모두 구성원 미확인), 보드 신호일 2026-11-04, 검증된 증권 ID 0
- **판 검사:** 판독기는 `/1` 완료본과 `/2` 경계 정책판을 모두 읽는다. 섞인 짝·모르는 판·정책 누락·해시 불일치는 거부하거나 따로 둔다(통합 가지 `claude/integration-20261108`의 `web_app_classification_policy_node_test.js`, Codex 6사례).

## 3-1. 화면의 두 모집단 (오너 2026-11-08)

- **비공개 패널:** "운영504 · 공식 모집단(Universe504)" 칸과 "확장 발행사 표본 · 별도 모집단 · 운영504와 합치지 않음" 칸을 따로 둔다.
  - 확장 칸에는 다음을 적는다:
    - 관측 카탈로그 발행사라는 점(투자 적격 모집단 아님)
    - 카탈로그 관측일과 경과일(평가일 상장 명부 아님)
    - 두 범위의 분모와 개수
    - 전체시장 분모 미산출, 새 증권 ID 0
    - 발행사 행 ID는 증권 ID가 아니라는 점
    - 공식 Q 관문 입력 연결 수와 분모를 범위마다 따로(관측 카탈로그 · 보유 재무 하위표본). "관문 통과·새 섹터 Q 산출 아님"으로 적는다
    - 행 단위 화면은 아직 없고 요약만 연결됐다는 점
  - 패널 위쪽에 분류 사전·대응 판, `/2`면 경계 정책판(시스템 대응 정책 · 책의 직접 명시 아님)을 적는다.
  - 확장 개수는 504 개수에 더하지 않는다.
  - 운영504 칸에는 섹터 QGV 원결과의 Q·G 산출 수를 평가일과 함께 적는다(원결과 집계, 재계산 없음).
  - `calculation_counts` 검사는 판독기(`classification.js`)가 한다. 필드가 없으면 "없음", 검사에 실패하면 "연결 오류(코드)"로 보이고 수는 보이지 않는다. 묶음의 다른 부분은 그대로 읽는다.
- **기업 상세·QGV·기술·매크로:** 운영504 기록만 읽는다. 확장 행은 기업 화면이나 기술 결합에 쓰지 않는다.

## 4. 남은 것

- **Worker 배포:** `/kis/*` 경로(#493 포함)가 배포되기 전에는 패널이 "비공개 서버에 이 경로가 아직 없습니다(Worker 배포 전)"를 보인다. 배포는 별도 승인이다.
- **#493 병합:** 이 가지는 #493을 병합해 그 위에 얹었다. #493 자체는 Draft다.
- **실제 결합 없음:** 증권 ID 0, QGV 행 평가일 없음(`SIGNAL_DAY_CONTRACT.md`). 기술 결합은 계속 거부된다.
