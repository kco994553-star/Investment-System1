# 현재 인수인계 — 2026-10-25

기준 **2026-10-25 12:25 UTC / 21:25 KST**, canonical **`ef5ff9c7`** (#413). `origin/main`은 없으며 실제 기본 브랜치는 **`claude/investment-system-top500-validation-alrugm`**이다. git log·PR 메타데이터·Actions job 로그·공개 파일을 대조했다. 이후 실행은 다시 확인한다. **10/25 프론트엔드 일시 제외(DC-20)는 같은 날 사용자 지시로 풀렸다(DC-21, 프론트엔드 재개).**

읽기: [START_HERE](START_HERE.md) → [방향 전환 대장](docs/SPEC/DIRECTION_CHANGES.md) → [WORKING_RULES](WORKING_RULES.md) → [기능 현황](docs/SPEC/FUNCTION_STATUS.md) → [결정 원문](implementation/docs/USER_DECISIONS_PENDING.md). 최신 이행 순서는 10/25 오너 지시(DC-19·DC-21)가 과거 대기·순서 표현에 우선한다.

## 0. 역할·지금 관리할 흐름 (최대 3개)

Main이 공용 파일·코드·병합·배포를 조정한다. Codex는 검증·리뷰와 허용된 문서만 작성·push한다(DC-09, DC-19). 문서 예외를 코드·병합·배포 권한으로 확대하지 않는다. 긴급 흐름(#410 → ALLSHARDS-1026)은 끝났다.

| 흐름 / 기능번호 | Main 이행 | 현재 상태 |
| --- | --- | --- |
| **1 중앙 V / 2·6** | #400 IEX 스트림 수정(검토 반영) → #409·#410 포함 canonical을 #393 → #400 → #403 → #404 → #405 → 리허설 가지로 → 수정된 새 SHA로 비게시 재리허설 | 로컬 수정·검토·사슬 병합 진행 중(push 전). 재리허설은 오늘 03:00~19:30 UTC 창, 다른 수집·배포와 겹치지 않게 |
| **2 프론트엔드 / 1·2** | 시안 추가 보드 18쌍 검토 반영 → 시안 아티팩트에 추가. P2-2a(2.1 리더보드) 명세 → 구현 → 검토 → PR(병합은 승인 뒤) | 보드 수정 재개, P2-2a 명세 작성 중(가지 `claude/frontend-v2-p2-2-qgv`, push 전) |
| **3 정본 문서 / 공통** | 이 PR: #413 뒤 사실(#410·#408·#413 병합, ALLSHARDS-1026 결과, 원장 판정, DC-21) | 병합은 오너 승인 뒤 |

### 작업 중

| PR·작업 | 담당 | 시작 (UTC) |
| --- | --- | --- |
| 중앙 V 사슬 canonical 병합(첫 게시 날짜 승인 대기, 리허설 run 40307781072 PASS) | Claude Code Main | 10/25 07:01 |
| P2-2a 리더보드 #415 + 10/27 오너 지시(DC-22 기준 칩·문구, DC-23, DC-24 TARGET v0 제외) | Claude Code Main | 10/25 11:10 · 10/27 10:19 |
| 시안 바뀌는 화면 상태 보드·검색 부품 보드 → 아티팩트 게시 | Claude Code Main | 10/27 10:19 |
| 공용 기업 검색 부품 PR(DC-23, #415 위)·QGV 카드 갱신 시각·홈 기본 목록 | Claude Code Main | 10/27 11:00 |

## 1. 승인 이행·오너 결정 (마감순)

| 번호 | 마감 UTC / KST | 실제 상태·남은 조건 |
| --- | --- | --- |
| **#409 UNI-PSKY-ALIAS** | 10-26 22:00 / 10-27 07:00 | **완료.** 병합 `c65f187a`, ALLSHARDS-1026으로 게시(PSKY 새 acquired_at 10-25 11:19 UTC) |
| **#410 UNI-ENDED** | 같음 | **완료.** 병합 `0de4148f`, 게시(WBD `NOT_AVAILABLE`·`CIK_UNRESOLVED`·값 없음, `listing_ended=1`) |
| **ALLSHARDS-1026 1회** | 같음 | **완료.** [run 40186520528](https://github.com/kco994553-star/Investment-System1/actions/runs/40186520528) 10:52:03→12:03:16, collect·verify·deploy 성공(아래 4·6절) |
| #413 채택·#412 중복 종료 | — | **완료.** #413 병합 `ef5ff9c7`, #412 닫음(브랜치·이력 보존) |
| 중앙 V 첫 게시 창 | **11-04 전 목표** | 수정 후보 재리허설·점검표 뒤 날짜 제안. **게시 창 실행은 오너 승인 뒤.** 이 창의 all_shards는 ALLSHARDS-1026과 별도 |
| #408 처리(DC-20 시점) | — | DC-20은 10:03 UTC #413 커밋 97c40352로 기록됐다(본문 최종 확인 10:43 UTC). #408은 10:52 UTC 병합 — Main은 DC-20을 병합 뒤에 확인했다. 배포 안 됨. DC-21로 프론트엔드가 재개돼 그대로 둔다(되돌리기는 오너 지시가 있을 때만) |
| #392 TARGET v0 결합 해소 | 미정; 중앙 V와 다른 창 | 준비·검증 뒤 병합안 보고. 최종 병합 승인 별도, TV0 후속 7건 자동 승인 아님 |
| CV-MONTHEND-RECENT · D5-UPDATE · LISTING-ENDED-CODE | 시각 미정 | 첫 게시 비차단. 전용 상장 종료 사유 코드는 별도 PR·결정(11/9 확정 창 뒤 권장) |
| T-FRESH · MANUAL-QUOTE · TV0-* 및 나머지 장기 결정 | [결정 원문](implementation/docs/USER_DECISIONS_PENDING.md#남아-있는-결정만)의 선행 조건 | 현행 계산·T-FRESH 유지. MANUAL-QUOTE는 P2-6 전 |

## 2. 10/25 KST 병합 (mergedAt)

| PR | 내용 | UTC / KST | merge SHA |
| --- | --- | --- | --- |
| [#398](https://github.com/kco994553-star/Investment-System1/pull/398) | P1 결정·DC-18 | 10-24 22:39:55 / 10-25 07:39:55 | `8e1fce12` |
| [#399](https://github.com/kco994553-star/Investment-System1/pull/399) | P2-1a 첫 화면 | 10-24 23:22:48 / 10-25 08:22:48 | `4c3d8142` |
| [#407](https://github.com/kco994553-star/Investment-System1/pull/407) | verify 제한 60분 | 10-25 07:33:54 / 16:33:54 | `f61b0373` |
| [#409](https://github.com/kco994553-star/Investment-System1/pull/409) | PSKY 별칭 | 10-25 08:18:52 / 17:18:52 | `c65f187a` |
| [#406](https://github.com/kco994553-star/Investment-System1/pull/406) | 결정 기록 | 10-25 08:23:12 / 17:23:12 | `c43b223f` |
| [#410](https://github.com/kco994553-star/Investment-System1/pull/410) | WBD 상장 종료 NA | 10-25 10:51:48 / 19:51:48 | `0de4148f` |
| [#408](https://github.com/kco994553-star/Investment-System1/pull/408) | P2-1 홈·검색(배포 안 됨) | 10-25 10:52:29 / 19:52:29 | `a7a2f32d` |
| [#413](https://github.com/kco994553-star/Investment-System1/pull/413) | 문서 정본(Codex) | 10-25 10:58:48 / 19:58:48 | `ef5ff9c7` |

#410은 CI 녹색(09:16 UTC) 뒤 Main 세션 사용량 한도로 약 1시간 35분 늦게 병합했다. #406·#408·#413은 바로 앞 병합을 포함하지 않은 HEAD로 병합했다. #406·#408은 바로 앞 병합과 바뀐 파일이 겹치지 않는다. #413은 #408과 `FUNCTION_STATUS.md`를 함께 바꿨으나 다른 행이라 충돌이 없다.

## 3. 열린 PR·CI·승인

| PR | 제목 요지 | HEAD | CI | 오너 승인·조건 |
| --- | --- | --- | --- | --- |
| [#411](https://github.com/kco994553-star/Investment-System1/pull/411) | TARGET 확정 차단 점검 | `3f260f6b` | green(옛 기준) | #405 뒤 동기화·검증, 사슬과 함께 |
| [#405](https://github.com/kco994553-star/Investment-System1/pull/405) | 중앙 V PR-D 판독기 | `eca9ab79` | green(옛 기준) | 게시 창 조건; base #404 |
| [#404](https://github.com/kco994553-star/Investment-System1/pull/404) | 중앙 V PR-C 워크플로 | `8005575c` | green(옛 기준) | 수정 사슬·리허설·게시 창 조건; base #403 |
| [#403](https://github.com/kco994553-star/Investment-System1/pull/403) | 중앙 V PR-B 가드 | `993a4682` | green(옛 기준) | 같음; base #400 |
| [#400](https://github.com/kco994553-star/Investment-System1/pull/400) | 중앙 V PR-A 계산 코어 | `3589fd44` | green(옛 기준) | IEX 수정 반영본 push 전; base #393 |
| [#393](https://github.com/kco994553-star/Investment-System1/pull/393) | F_k·calc_version 23.1 | `59c97730` | green(옛 기준) | canonical 동기화 진행 중; 중앙 V 첫 게시와 같은 창 |
| [#392](https://github.com/kco994553-star/Investment-System1/pull/392) | TARGET v0 결합 해소 | `f8307b7c` | green(10/24 기준) | DIRTY, 통합 검증·최종 병합 승인 별도 |
| [#361](https://github.com/kco994553-star/Investment-System1/pull/361) | Worker 분할 이벤트 | `910d5661` | green(10/20 기준) | DIRTY, 공급원 권리로 배포 보류 |
| [#305](https://github.com/kco994553-star/Investment-System1/pull/305) | [WIP] Atlas | `bbb7bb55` | green(10/18 기준) | draft·참고, DIRTY |
| [#281](https://github.com/kco994553-star/Investment-System1/pull/281) | [WIP] 프론트엔드 시안 | `3b22cae1` | green(10/17 기준) | draft·참고 |
| [#267](https://github.com/kco994553-star/Investment-System1/pull/267) | 투자 스튜디오 | `ad469e5c` | green(10/15 기준) | 보류 |

조회 범위(#413 기록 유지): repo ruleset 24499602 HG-02 canonical hard guard — PR 필수, 리뷰 승인 수 0, 필수 check `repository-guard`, bypass actors 없음. legacy branch protection API만 403. GitHub 리뷰 0과 오너 승인(대화·결정 기록)은 별개다.

## 4. 실제 상태·게시 검증

| 대상 / 기능번호 | 구현 | 실제 시험·검증 | 통합 | 배포 | LIVE |
| --- | --- | --- | --- | --- | --- |
| #407 / 9.2 | 완료 | PR CI green | 완료 | ALLSHARDS-1026 verify 잡 33.9분(제한 60) | 정기 실행 적용은 10/25분 실행에서 확인 |
| #409·#410 / 2·9.2 | 완료 | CI green, 합본 로컬 전체 시험 3,756 통과 | 완료 | **완료**(run 40186520528, 12:03 UTC) | 공개 파일 확인(아래). 화면 직접 확인은 미확인 |
| #398·#399·#408 / 1 | 완료 | 각 PR CI green | 완료 | 해당 없음(`web_app/`은 P3 전환 때) | 해당 없음 |
| 중앙 V / 2·6 | 수정 진행 | CI green(옛 기준), 리허설 1회 FAIL | 미완료 | 미배포 | 미확인 |

공개 파일 **12:20 UTC** 확인([QGV](https://kco994553-star.github.io/Investment-System1/sec-qgv2.json), as_of 2026-10-25 11:26:42 UTC):

| 항목 | ALLSHARDS-1026 뒤 실측 |
| --- | --- |
| Universe·커버리지 | 504, Q 485, G 493, 양쪽 477, LIVE 501·STALE 0·NOT_AVAILABLE 3, 샤드 7/7, 단면 498, calc_version `qgv2-calc/2026-10-17.1` |
| PSKY | LIVE, acquired_at **2026-10-25 11:19:47 UTC**, CIK 0002041610, 업종군 telecommunications(SIC 4833) 유지 |
| WBD | **NOT_AVAILABLE**, 사유 `CIK_UNRESOLVED`, 값·calc_version 없음, CIK 0001437107·acquired_at 10-17 03:15 UTC 유지. 로그 `listing_ended=1` |
| 7일 초과 | **값 있는 행 0.** 로그 `stale_7d_rows=1`은 WBD NA 행(값 없음, 원장 계산에서 빠짐) |
| 원장 판정 | `forward_ledger.observation_basis`를 이 파일에 적용: 세션 **10/26·10/27·10/28 PRIMARY**(사유 없음, 취득일 10-25). 이 파일만으로는 10/30(7일 이내 마지막 세션)까지 PRIMARY, 11/02는 `ROW_DATA_STALE` — 정기 실행의 샤드 갱신이 이어져야 한다. 실제 기록은 각 세션 자기 파일로 정기 실행 뒤 판정되므로 그때 다시 확인 |
| 수집 로그 | issuers 500/500, failed 0, `unresolved_codes=1`(WBD), `preserved_previous_shares=2`(WBD·PSKY shares 행), `identity_not_preserved=0`. 오늘은 일요일이라 원장 추가 없음(`appended=0`) |

PSKY의 `sec-universe-shares.json` 행은 #409 설계대로 보존(M3 주식수 경로는 별칭을 쓰지 않음)되어 10-31 03:13 UTC에 STALE이 된다. TARGET 확정·원장·중앙 V 순위는 이 파일을 읽지 않는다.

## 5. 다음 우선순위·대기열

1. **중앙 V 재리허설**: 사슬 동기화·교차 검토 → 사슬·리허설 가지 push → 비게시 재리허설(오늘 19:30 UTC 전) → 결과(run ID, 처리 시간·디스크·누락, 12기준 판정) → 첫 게시 날짜 제안. 구 SHA 재실행으로 수정 검증을 대신하지 않는다.
2. **프론트엔드**: 시안 추가 보드 게시 → P2-2a(2.1 리더보드) PR. 다음 순서 2.2 → 2.4·2.3.1·2.5 → 6 → 5 → 3 → 4 → 7 → 8 → 9. P3 실사이트 전환·배포는 별도 승인.
3. **10/25분 정기 실행 확인**(10/26 00:19 UTC 무렵): 연속 4/7 여부, verify 60분 제한 첫 정기 적용, 보존 행 6일 이상 점검.

장기 대기열: **#392** 최신 canonical 동기화·충돌 해결·기기 키 이전·백업·기존 그림 보존·멱등성 검증 → 중앙 V와 다른 창의 병합안(최종 승인 별도, TV0 후속 7개 제외).

중앙 V 게시 창 계획: **#393 → 수정 #400 → #403 → #404 → 전환용 별도 all_shards·새 calc_version 숫자 재대조 → #405 → #411**. #411은 #405 뒤 동기화해 `freshFor`·`official`·숨김 상태·TARGET 핸들러 충돌을 검증한다.

## 6. 정기 실행·수동 실행·중앙 V 실측

| 대상 / 관측분 | run 번호 / ID | UTC 시작→종료 | 결과 |
| --- | --- | --- | --- |
| SEC 10/22분 | [#21 / 39879258841](https://github.com/kco994553-star/Investment-System1/actions/runs/39879258841) | 10-23 00:37:54→01:20:47 | 성공, 1/7 |
| SEC 10/23분 | [#22 / 40045938631](https://github.com/kco994553-star/Investment-System1/actions/runs/40045938631) | 10-24 00:38:05→01:17:10 | 성공, 2/7 |
| SEC 10/24분 | [#23 / 40146210895](https://github.com/kco994553-star/Investment-System1/actions/runs/40146210895) | 10-25 00:19:00→01:06:12 | 성공 3/7, `4c3d8142` |
| **ALLSHARDS-1026** | [#24 / 40186520528](https://github.com/kco994553-star/Investment-System1/actions/runs/40186520528) | 10-25 10:52:03→12:03:16 | **성공**(workflow_dispatch, `0de4148f`). collect 36.6분, verify 33.9분, deploy 12:03:13. 수동 실행이라 연속 집계에 넣지 않음 |
| 중앙 V 비게시 리허설 | [#1 / 40156760950](https://github.com/kco994553-star/Investment-System1/actions/runs/40156760950) | 10-25 03:03:01→03:32:46 | 최종 FAIL, 6/12 PASS. IEX_GZIP_FAILED·ROWS_OF_ANOTHER_CALC_VERSION(other_calc=2)·NOT_MEASURED 4 |

부분 실패(배포는 막지 않음, 이전과 같음): 8-K `ASML_6K_EARNINGS_UNCONFIRMED`(17개 중 1개), 뉴스 GDELT HTTP 429·IR 피드 실패(PARTIAL_FAILED), 로고 Wikidata 원천 불가(이니셜 506).

## 7. 알려진 위험·관리자 노트

| 위험 | 영향·확인 |
| --- | --- |
| WBD 사유 코드 미분리 | `CIK_UNRESOLVED` 표기('CIK 미해결'·'CIK 미확인'). 전용 `LISTING_ENDED`는 별도 결정·PR |
| telecom MIN_PEERS=8 경계 | **ALLSHARDS-1026 뒤 실측: telecom 업종군 발행사 8곳**(값 있는 코드 9, FOX·FOXA 한 발행사). 하나 더 빠지면 Q가 GENERAL `UNIVERSE_FALLBACK`(v2_scoring.py). 매일 8 미만이면 즉시 보고 |
| 중앙 V 두 오류 | gzip 실패와 입력 버전 혼합은 별개. 수정·새 SHA·최종 판정으로 확인, 가드 약화 금지 |
| 신선도·원장 | 7샤드 회전과 T-FRESH 7일의 여유 0: 정기 실행이 하루 빠지면 원장·확정이 막힌다. 6일 이상 보존 행은 매일 보고. `sec-qgv2.json` 값 있는 보존 행 0. **`sec-universe-shares.json`의 PSKY 행(LIVE, 10-17 03:13 UTC 취득, 이미 6일 초과)이 보고 대상**이며 10-31 03:13 UTC에 STALE(#409 설계: M3 주식수 경로는 별칭을 쓰지 않음) |

관리자 노트: 기능 구현 %·프론트엔드 %는 미산정(#413). 문서·리뷰만으로 제품 진행률을 올리지 않는다.

## 8. 경계

Universe504 고정(DC-01), 공식 V는 IEX HIST 서버 계산·공개 방향(DC-02), 아직 canonical 미통합. 원시 가격·EV·배율·수익률·보유·Secret 값·키·토큰 값은 문서·로그·공개 산출물에 넣지 않는다(Secret은 이름 `QGV_OFFICIAL_HMAC_KEY`·`RAW_REPO_READ_TOKEN`만). NA를 0으로 채우지 않는다. 가격 요청은 버튼을 누를 때만. Frozen·원장·SUPERSEDED·#412 이력 보존. 계산·가중치·T-FRESH·공개 경계·보호규칙·AUTONOMY_MODE 임의 변경 없음.
