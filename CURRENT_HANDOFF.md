# 현재 인수인계 — 2026-10-25

기준 **2026-10-25 08:56:10 UTC / 17:56:10 KST**. 기준 commit **`c43b223f18eff68f8b56ccf8c1ae1c1fdc3083a8`** (#406).
`origin/main`은 원격에 없어 `git log origin/main` 확인 불가. 실제 기본·통합 브랜치 **`origin/claude/investment-system-top500-validation-alrugm`**의 fetch 후 first-parent log와 `gh`를 대조했다. 이하 상태는 이 시각의 관측이다.

읽기: [START_HERE](START_HERE.md) → [방향 전환 대장](docs/SPEC/DIRECTION_CHANGES.md) → [WORKING_RULES](WORKING_RULES.md) → [기능 현황](docs/SPEC/FUNCTION_STATUS.md) → [사용자 결정](implementation/docs/USER_DECISIONS_PENDING.md).

## 0. 작업 범위·역할

DC-09 운영 역할을 유지한다. **이번 오너 직접 요청에 한해 Codex가 문서 갱신·docs 전용 PR을 작성한다.** 코드·워크플로·프론트엔드 작업, 병합·배포는 수행하지 않는다. 이 PR도 CI 통과 뒤 오너 승인 전에는 병합하지 않는다.

| 작업 | 담당 | 시작 UTC / KST | 상태 |
| --- | --- | --- | --- |
| 실상태 문서 갱신 (`docs/current-handoff-facts-20261025`) | Codex | 10-25 08:55 / 17:55 | 문서 전용 PR로 제출. 기존 #412와 문서가 겹치므로 오너가 채택 순서 결정 |

## 1. 오너 결정·승인 이행 (마감순)

**#409·#410·ALLSHARDS-1026은 10/25 결정으로 이미 승인됐다. 재승인 대기가 아니다.** [최신 결정 원문](implementation/docs/USER_DECISIONS_PENDING.md#결정됨--2026-10-25-407409410406408-병합-승인-all_shards-연속-집계-411).

| 번호 | 마감 UTC / KST | 기준 시각 상태·남은 조치 |
| --- | --- | --- |
| **#409 UNI-PSKY-ALIAS** | **10-26 22:00 / 10-27 07:00 전 종료** (후속 실행과 공통) | 승인·병합 완료. 수집·게시 반영은 아직 미확인 |
| **#410 UNI-ENDED** | **같음** | 조건 (i)~(vi) 포함 승인. CI build 실행 중; 최종 HEAD 녹색 뒤 Main이 병합 |
| **ALLSHARDS-1026, all_shards 1회** | **같음** | 승인·미실행. #409→#410 병합 뒤 정기·다른 수동 배포와 겹치지 않게 실행. 값 있는 행의 7일 초과 0, PSKY 새 acquired_at, WBD `listing_ended=1`, 10/26~10/28 PRIMARY 조건 확인 필요 |
| 중앙 V 첫 게시 창 (#393→#400→#403→#404→#405→#411) | 정확한 시각 미정; **11-04 전 목표** | 수정·재리허설·점검표 후 Main이 날짜 제안, 오너 승인. 이 창의 all_shards·숫자 재대조는 ALLSHARDS-1026과 별도 |
| #392 TARGET v0 결합 해소 | 미정 | 병합 승인 대기. 중앙 V·TARGET v1과의 순서 보고 필요; 현재 충돌 있음 |
| T-FRESH | 정확한 시각 미정; 11/9 확정 창 전 검토 | 신선도 기준 유지·변경 선택 대기 |
| CV-MONTHEND-RECENT · D5-UPDATE | 미정 | 최근 월말가 보충 1회·월말 갱신 방식 결정. 첫 게시 차단 아님 |
| LISTING-ENDED-CODE | 미정; 11/9 확정 창 뒤 별도 PR 권장 | 상장 종료 전용 사유 코드·스키마 변경 결정 |
| MANUAL-QUOTE | 시각 미정; P2-6 전 | 수동 시세 입력 위치 결정(프론트엔드 작업은 이번 범위 밖) |
| TV0-ACTUAL · TV0-SETS · TV0-NOCIK · TV0-CIKSRC · TV0-MEMO · TV0-RANKLIST · TV0-S06 | 미정 | #392 후속 7건, 선택지는 원문 |
| M-REENABLE · SH-BASIS · M3-COVER · SCALE-PUB · RAW-TAG · TYPE-SCOPE · XOM-COVER · MISS-RECOVER · FIN-NA-CODE | 미정 | [남아 있는 결정만](implementation/docs/USER_DECISIONS_PENDING.md#남아-있는-결정만) 참조 |
| BACKTEST(BT-1~17·MD-1~12) · IA-2~18 · NEWS-CAP · RADAR-AXES · TRACKC-PORT · DRAW-STORE · PROMPT-DOMAIN · WEEKLY-REPORT · REL-SOURCE · CHART-GATE · TA-G1~G3 | 미정 | 같은 원문 참조; 기존 허용 범위 유지 |

## 2. 10/25 KST 병합 확인

시각은 `gh`의 **mergedAt**이다. 이전 결정 기록의 #407 07:11 UTC 표기와 달리 실제 병합은 **07:33:54 UTC**다.

| PR | 내용 | 병합 UTC / KST | merge SHA |
| --- | --- | --- | --- |
| [#398](https://github.com/kco994553-star/Investment-System1/pull/398) | P1 결정 반영·DC-18 | 10-24 22:39:55 / 10-25 07:39:55 | `8e1fce12` |
| [#399](https://github.com/kco994553-star/Investment-System1/pull/399) | P2-1a 첫 화면 구조 | 10-24 23:22:48 / 10-25 08:22:48 | `4c3d8142` |
| [#407](https://github.com/kco994553-star/Investment-System1/pull/407) | 정기 verify 제한 60분 | 10-25 07:33:54 / 16:33:54 | `f61b0373` |
| [#409](https://github.com/kco994553-star/Investment-System1/pull/409) | PSKY SEC 별칭 복구 | 10-25 08:18:52 / 17:18:52 | `c65f187a` |
| [#406](https://github.com/kco994553-star/Investment-System1/pull/406) | 10/24~25 결정 기록 | 10-25 08:23:12 / 17:23:12 | `c43b223f` |

## 3. 열린 PR (14개, 이 문서의 새 PR 생성 전)

CI는 각 **HEAD**의 관측값이다. `green`=성공 6개, `running`=성공 5개+build 진행 중; replay_source·deploy의 skipped는 성공으로 세지 않았다. red 0개. **GitHub reviewDecision·reviewRequests·latestReviews는 모두 비어 있음**; 아래 승인은 결정 문서 기준이다. 보호규칙의 필수 승인 수는 API 403으로 **미확인**.

| PR | 제목 요지 | HEAD | CI | 오너 승인·이행 상태 |
| --- | --- | --- | --- | --- |
| [#412](https://github.com/kco994553-star/Investment-System1/pull/412) | 문서: 10/25 07:50 인수인계 | `2ef64b68` | green | 승인 필요; 이번 갱신과 중복, 기준이 #407 시점 |
| [#411](https://github.com/kco994553-star/Investment-System1/pull/411) | TARGET v1 확정 차단 점검 | `3f260f6b` | green | 버튼 추가 결정됨; #405 뒤 사슬과 함께, 게시 창 승인 대기 |
| [#410](https://github.com/kco994553-star/Investment-System1/pull/410) | WBD 상장 종료 NA | `afbec90e` | running | 이미 승인, 최종 HEAD 녹색 조건 |
| [#408](https://github.com/kco994553-star/Investment-System1/pull/408) | 새 프론트엔드 P2-1 홈·검색 | `9c0c3249` | running | 이미 승인, 이번 작업 범위 밖 |
| [#405](https://github.com/kco994553-star/Investment-System1/pull/405) | 중앙 V PR-D 옛 화면 판독기 | `eca9ab79` | green | 첫 게시 조건·창 승인 대기 |
| [#404](https://github.com/kco994553-star/Investment-System1/pull/404) | 중앙 V PR-C 워크플로·첫 게시 점검표 | `8005575c` | green | 같음; base #403 |
| [#403](https://github.com/kco994553-star/Investment-System1/pull/403) | 중앙 V PR-B 가드 | `993a4682` | green | 같음; base #400 |
| [#400](https://github.com/kco994553-star/Investment-System1/pull/400) | 중앙 V PR-A 계산 코어 U1~U3 | `3589fd44` | green | 수정·사슬 전파·재리허설 작업 대기; base #393 |
| [#393](https://github.com/kco994553-star/Investment-System1/pull/393) | F_k·calc_version 23.1 | `59c97730` | green | 중앙 V 첫 게시와 같은 배포 창 조건 |
| [#392](https://github.com/kco994553-star/Investment-System1/pull/392) | TARGET v0 결합 해소 | `f8307b7c` | green | 승인 필요; 충돌(DIRTY), 최신 통합 검증 아님 |
| [#361](https://github.com/kco994553-star/Investment-System1/pull/361) | Worker 분할 이벤트·가격 기준 연속성 | `910d5661` | green | 배포 보류, 공급원 결정 필요; 충돌(DIRTY) |
| [#305](https://github.com/kco994553-star/Investment-System1/pull/305) | [WIP] 프론트엔드 Atlas | `bbb7bb55` | green | draft·참고; 충돌, 이번 범위 밖 |
| [#281](https://github.com/kco994553-star/Investment-System1/pull/281) | [WIP] 프론트엔드 v2 시안 | `3b22cae1` | green | draft·참고, 이번 범위 밖 |
| [#267](https://github.com/kco994553-star/Investment-System1/pull/267) | 인터랙티브 투자 스튜디오 | `ad469e5c` | green | 보류·승인 필요, 이번 범위 밖 |

## 4. 구현 / 검증 / 통합 / 배포 / LIVE

| 대상 | 구현 완료 | 검증 완료 | 통합 완료 | 배포 | LIVE 확인 |
| --- | --- | --- | --- | --- | --- |
| #407 verify 60분 | 완료 | PR CI green | 완료 | 워크플로 병합 완료; 다음 정기 실행 적용 미확인 | 미확인 |
| #409 PSKY 복구 | 완료 | PR CI green | 완료 | 미배포 (최신 배포는 #409 전) | 미확인 |
| #406 결정 기록 | 완료 | 문서 반영 확인; 이 PR에서 코드 재검증 안 함 | 완료 | 해당 없음 | 해당 없음 |
| 중앙 V #393·#400·#403·#404·#405 | PR 구현 있음; 수정 잔여 | PR CI green / 운영 리허설 실패 | 미완료 | 미배포 | 미확인 |
| #410 WBD NA | PR 구현 있음 | CI running | 미완료 | 미배포 | 미확인 |
| #398·#399 새 프론트엔드 | 완료 | PR CI green | 완료 | 새 앱 미배포 | 미확인 |
| 기존 사이트·정기 자료 | 기존 구현 | 최신 collect·verify 성공 | 배포 SHA `4c3d8142` | Pages 성공 10-25 01:06:12 UTC / 10:06:12 KST | 실사이트 내용·브라우저 동작 미확인 |

대조: [FUNCTION_STATUS](docs/SPEC/FUNCTION_STATUS.md)의 기존 본문은 10/23~24 기준이다. 9.2 연속 성공만 아래 실측으로 맞췄다. 중앙 V의 canonical 미통합·TARGET v1 숫자 재대조 필요(DC-16)는 유지한다. [USER_DECISIONS_PENDING](implementation/docs/USER_DECISIONS_PENDING.md)의 최신 10/25 절이 과거 절의 승인 대기·집계 질의를 대체한다. Secret 이름 `QGV_OFFICIAL_HMAC_KEY`·`RAW_REPO_READ_TOKEN` 등록 완료는 문서 기록이며, 이번 세션에서 유효성은 **미확인**.

## 5. 다음 우선순위 (최대 3개, 프론트엔드 제외)

1. Main: #410 최종 HEAD CI 확인→기존 승인대로 병합→ALLSHARDS-1026 1회. **10/27 07:00 KST 전 종료**와 PSKY·WBD·PRIMARY 조건 확인.
2. Main: 중앙 V 재시도·gzip 순서 수정(#400)→사슬 전파→분리 리허설→첫 게시 점검표·게시 날짜 제안. #393 calc_version 변경·10종목 숫자 재대조를 같은 창에 묶음.
3. 오너: #392 병합·중앙 V와의 순서 결정. WBD 전용 사유 코드와 telecom 대체 규칙은 별도 후속으로 정리.

## 6. 정기 실행·리허설 (Actions 직접 확인)

| 대상 / 관측분 | run 번호 / ID | 시작→최종 갱신 UTC | 결과 |
| --- | --- | --- | --- |
| sec-daily-public-inputs 10/22분 | [#21 / 39879258841](https://github.com/kco994553-star/Investment-System1/actions/runs/39879258841) | 10-23 00:37:54→01:20:47 | collect·verify·deploy 성공, 연속 1/7 |
| 같은 워크플로 10/23분 | [#22 / 40045938631](https://github.com/kco994553-star/Investment-System1/actions/runs/40045938631) | 10-24 00:38:05→01:17:10 | 모두 성공, 2/7 |
| **같은 워크플로 10/24분 (최신)** | [**#23 / 40146210895**](https://github.com/kco994553-star/Investment-System1/actions/runs/40146210895) | 10-25 00:19:00→01:06:12 | **모두 성공, 3/7**; SHA `4c3d8142` |
| 중앙 V 분리 리허설 | [#1 / 40156760950](https://github.com/kco994553-star/Investment-System1/actions/runs/40156760950) | 10-25 03:03:01→03:32:46 | failure, 최종 verdict 단계 실패. attempt 1만 존재, 재실행 queued/running 없음 |

Pages 최신 deployment **7306836646**은 `4c3d8142`로 success([배포 job](https://github.com/kco994553-star/Investment-System1/actions/runs/40146210895/job/121037177505)). #409 병합 뒤 sec-daily-public-inputs의 정기·수동 신규 실행은 없으며 **ALLSHARDS-1026은 미실행**이다. 리허설 실패 사유 토큰은 로그 API Forbidden으로 **미확인**; 재시도·gzip 문제는 최신 결정 문서의 수정 지시다.

## 7. 알려진 위험

| 위험 | 영향·남은 확인 |
| --- | --- |
| **WBD 사유 코드 미분리** | #410도 공개 사유 `CIK_UNRESOLVED`를 사용해 화면은 'CIK 미해결'로 보인다. `LISTING_ENDED` 사유 코드 추가는 별도 결정·PR, 현재 승인 병합 차단 아님 |
| **telecom MIN_PEERS=8 경계** | #410 적용 시 비교군 9→8. 한 종목 더 빠질 때 업종 대체 규칙·점수 영향 미확인; PSKY 복구와 함께 적용 필요 |
| **중앙 V 리허설 재실행 작업 대기** | PR CI green은 운영 통과 증거가 아님. 수정·사슬 전파·재리허설 후 판정 필요. 가드 우회 금지 |

## 8. 유지할 경계

Universe504는 S&P 500 구성에서 출발해 고정한 목록(DC-01). 공식 V는 IEX HIST 기반 서버 계산·공개 방향(DC-02)이며 아직 canonical 미통합이다. 원시 가격·EV·배율·수익률·보유 정보·Secret 값·키·토큰 값은 문서·로그·공개 산출물에 넣지 않는다. NA를 0으로 채우지 않는다. Frozen·전진검증 원장·SUPERSEDED 기록 보존. force push·보호규칙·AUTONOMY_MODE 변경 없음.
