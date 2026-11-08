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
| Worker | `GET /kis/classification?part=<view·technical·macro·qgv_links·dictionary>` → `classification/<part>.json`. 읽을 때마다 오너를 확인한다. 각 부분은 자기 Codex 스키마여야 넘긴다. 저장·로그·리다이렉트 없음 | `implementation/worker/src/index.js` |
| 클라이언트 | 경로 이름은 `kis-private.js` 한 파일에만 있다(좁은 예외 목록 8개). Bearer 헤더만 보내고, `credentials: omit`·`no-store`·`no-referrer`를 쓴다 | `web_app/kis-private.js`, `web_app/prices.js` |
| 화면 | 기업 상세 공통 분류 칸 아래 "공통 분류 보관 묶음" 비공개 패널. 한 번 누르면 다섯 부분을 5초 간격으로 차례로 읽는다. view는 반드시 있어야 하고, 나머지는 없으면 빼고 대신 채우지 않는다 | `web_app/private-expand-live.js`, `screen-search-live.js` |
| 판독 | `IS2.classification.connectPrivate`가 묶음 전체를 검사한다. 통과하면 RAM의 현재 원천이 된다(`delivery: PRIVATE`). 모든 화면이 같은 묶음을 읽는다 | `web_app/classification.js` |
| 해제 | 접기·연결 끊기·403·토큰 만료 → `disconnectPrivate`. 화면은 NONE으로 돌아간다 | 같은 파일 |

- 화면 문구는 "비공개 보관본 · 인증 경로 · 게시본 아님"이다.
- 공식 QGV 순위·TARGET·공개 파일은 바뀌지 않는다. 화면이 분류를 다시 추론하지 않는다.

## 2. 비공개 저장소 배치

- **배치한 것:** `investment-system1-kis-private` `data` 가지 `classification/`. 전체 SHA는 PR 본문에 적는다.
- **출처:** Codex 보관 검토 `investment-system1-raw` `handoff/input-recovery-20261103` @ `097c20d`, `handoffs/common-classification-20261107/reviews/20261108`(생산자 #516 `4cf2e037`). 묶음의 `result/` 다섯 파일을 바이트 그대로 옮겼다.
- **도구:** `implementation/tools/stage_private_classification.py`.
  - 인계 명세의 크기·SHA-256, 스키마, 같은 분류 해시·평가일을 확인한다.
  - 모든 검사가 통과해야 파일을 쓴다. 공개 저장소 안으로는 쓰지 않는다.

  | 부분 | 바이트 | SHA-256 |
  | --- | --- | --- |
  | view | 1,802,474 | `428af5b04ea800ee2a72c220f9cadf1ebf7b664523ce9240cd6721d84bbd1bdb` |
  | technical | 201,276 | `52d7af96bea0ca0c229a6b917c4f714d201ebcf5056833e413cff3f1dc765db0` |
  | macro | 884,186 | `be5dad121342d4ef34793f64b426f34f5625b4fc66dab62e17428ee54f1d2f00` |
  | qgv_links | 79,672 | `86f8c2ba705ae518d28dd7dc0c7500474036b187c581e5770952c47416613515` |
  | dictionary | 2,917 | `9ae49c5f849535d325aaa64689da9fa61147347a9c8f8dafcf4055c0ef6d5776` |

- **11/07 묶음:** `d6196b6`, 섹터 365. Main 판독기를 그대로 통과한다. 11/08 검토 결과가 나와서 현재 전달본으로 쓰지 않았다. 어느 쪽을 현재로 둘지는 Codex 확인 사항이고, 같은 도구로 바꿀 수 있다.

## 3. 실자료 대조 (로컬, 배포 아님 — 개수만 기록)

- **실행 방식:** 실제 Worker 처리 코드에 배치한 파일을 넣고, 실제 판독기까지 이어서 돌렸다. GitHub와 Google은 디스크·고정 응답으로 대신했고, 네트워크는 쓰지 않았다.
- **결과:**
  - 다섯 부분 모두 받은 바이트 = 배치 바이트
  - 분류 버전 불일치 0
  - 평가일 2026-11-04 · `RETAINED_INPUT`
- **분류 개수:**

  | 항목 | 개수 |
  | --- | --- |
  | 기업 행 | 504 |
  | 섹터 확인 | 415 |
  | 하위 산업 확인 | 92 |
  | 회계모형 확인 | 406 |
  | 섹터·회계모형 둘 다 확인 | 393 |

- **기록 상태:** `SECTOR_ONLY` 323 · `CONFIRMED` 92 · `UNRESOLVED` 87 · `NO_DATA` 2
- **기술 투영:** 그룹 10개(모두 구성원 미확인 `UNKNOWN`), 보드 신호일 2026-11-04, 검증된 증권 ID 0
- **Main 판독기 차이 1건 수정:** 11/08 검토 결과의 근거 참조(최대 330자)가 표시 글 상한 300에 걸려 파일 전체가 거부되었다. 근거 참조는 화면에 보이지 않는 위치 문자열이므로 상한을 따로 두었다(`MAX.ref` 4096). 표시 글 상한 300은 그대로다.

## 4. 남은 것

- **Worker 배포:** `/kis/*` 경로(#493 포함)가 배포되기 전에는 패널이 "비공개 서버에 이 경로가 아직 없습니다(Worker 배포 전)"를 보인다. 배포는 별도 승인이다.
- **#493 병합:** 이 가지는 #493을 병합해 그 위에 얹었다. #493 자체는 Draft다.
- **실제 결합 없음:** 증권 ID 0, QGV 행 평가일 없음(`SIGNAL_DAY_CONTRACT.md`). 기술 결합은 계속 거부된다.
