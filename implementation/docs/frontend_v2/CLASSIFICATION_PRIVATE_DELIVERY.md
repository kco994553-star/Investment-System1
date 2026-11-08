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

## 2. 비공개 저장소 배치 (2026-11-08 갱신)

배치 위치는 `investment-system1-kis-private` `data` 가지 `classification/`이다. 전체 SHA는 PR 본문에 적는다.
도구 `implementation/tools/stage_private_classification.py`가 인계 명세의 크기·SHA-256, 스키마, 같은 분류 해시·평가일을 확인한다. 모든 검사가 통과해야 파일을 쓰고, 공개 저장소 안으로는 쓰지 않는다.

**운영504** (Universe504, 화면들이 읽는 기록)
- 출처: raw `handoff/input-recovery-20261103` @ `6f940b9c`, `handoffs/common-classification-20261107/reviews/20261108-completed`
- 생산자 #516 `4cf2e037`, Codex #437 6718032455
- 묶음 `result/` 다섯 파일을 바이트 그대로 옮겼다.

| 부분 | 바이트 | SHA-256 |
| --- | --- | --- |
| view | 1,803,857 | `07cae91f74bb88c55cfc4ef5f7b1224c59ce512de0f304791f0d9e1af360ae1e` |
| technical | 201,257 | `42eaaca64924d5397fc2f47732df2345cec672b5ade004e75b4a55cdd3377c09` |
| macro | 884,399 | `d6a389884fe8837856c9e8c4fd7a37d78ef49ddd349f8a2cb10f41329f4d3d9f` |
| qgv_links | 79,672 | `9b69270f476016b5785bb98b201d5d2da228f074e313cbf28a5e60ac97a664e3` |
| dictionary | 2,917 | `9ae49c5f849535d325aaa64689da9fa61147347a9c8f8dafcf4055c0ef6d5776` |

**확장 발행사 표본** (별도 모집단, Codex #520 `4c8c9381`)
- 출처: 같은 커밋의 `handoffs/expanded-held-classification-20261108`
- `final/summary.json`만 `expanded_summary`로 옮겼다(2,930 바이트, `051e50f2632fc63b3dd8bc11a0d5d3d85fa3f3e15d779adfb9c45fbdf8e71cbd`).
- 확장 view(13.5MB)와 preview(124MB)는 Worker 파일 상한 2MB를 넘어 옮기지 않았다. 행 단위 화면은 없고, 표본의 분모와 개수만 보인다.

**앞선 배치:** 11/07 묶음(`d6196b6`)과 11/08 1차 검토(`097c20d`)는 더 이상 현재 전달본이 아니다.

## 3. 실자료 대조 (로컬, 배포 아님 — 개수만 기록)

- **실행 방식:** 실제 Worker 처리 코드와 실제 판독기로 여섯 부분을 받았다. GitHub와 Google은 디스크·고정 응답으로 대신했고, 네트워크는 쓰지 않았다.
- **결과:**
  - 받은 바이트 = 배치 바이트
  - 분류 버전 불일치 0
  - 평가일 2026-11-04 · `RETAINED_INPUT`
- **운영504 개수** (Codex 수치와 같음):

  | 항목 | 개수 |
  | --- | --- |
  | 기업 행 | 504 |
  | 섹터 확인 | 416 |
  | 하위 산업 확인 | 92 |
  | 회계모형 확인 | 407 |
  | 섹터·회계모형 둘 다 확인 | 394 |
  | 미분류 | 88 |

  기록 상태: `SECTOR_ONLY` 324 · `CONFIRMED` 92 · `UNRESOLVED` 86 · `NO_DATA` 2

- **확장 표본 개수** (별도로 보임):

  | 범위 | 발행사 | 섹터 | Q | G |
  | --- | --- | --- | --- | --- |
  | 관측 카탈로그 전체 | 8,004 | 821 | 470 | 633 |
  | 보유 재무 하위표본 | 1,057 | 815 | 470 | 633 |

  전체시장 분모는 null, 새 증권 ID는 0이다. 운영504 개수에 더하지 않는다.
- **기술 투영:** 그룹 10개(모두 구성원 미확인), 보드 신호일 2026-11-04, 검증된 증권 ID 0
- **섹터 미리보기:** 보관 미리보기 504행이 links와 같은 미리보기다. `previewCheck` OK, `signal_day` 2026-11-04.
- **판독기 차이 수정:** 근거 참조 길이 상한을 따로 둔 것(`MAX.ref`)과 회계모형 독립 상태(1차 수정)는 그대로다.

## 3-1. 화면의 두 모집단 (오너 2026-11-08)

- **비공개 패널:** "운영504 · 공식 모집단(Universe504)" 칸과 "확장 발행사 표본 · 별도 모집단 · 운영504와 합치지 않음" 칸을 따로 둔다.
  - 확장 칸에는 다음을 적는다:
    - 관측 카탈로그 발행사라는 점(투자 적격 모집단 아님)
    - 카탈로그 관측일과 경과일(평가일 상장 명부 아님)
    - 두 범위의 분모와 개수
    - 전체시장 분모 미산출, 새 증권 ID 0
    - 발행사 행 ID는 증권 ID가 아니라는 점
  - 확장 개수는 504 개수에 더하지 않는다.
- **기업 상세·QGV·기술·매크로:** 운영504 기록만 읽는다. 확장 행은 기업 화면이나 기술 결합에 쓰지 않는다.

## 4. 남은 것

- **Worker 배포:** `/kis/*` 경로(#493 포함)가 배포되기 전에는 패널이 "비공개 서버에 이 경로가 아직 없습니다(Worker 배포 전)"를 보인다. 배포는 별도 승인이다.
- **#493 병합:** 이 가지는 #493을 병합해 그 위에 얹었다. #493 자체는 Draft다.
- **실제 결합 없음:** 증권 ID 0, QGV 행 평가일 없음(`SIGNAL_DAY_CONTRACT.md`). 기술 결합은 계속 거부된다.
