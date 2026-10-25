# 현재 인수인계 — 2026-10-25

기준 **2026-10-25 09:40:20 UTC / 18:40:20 KST**, canonical **`c43b223f18eff68f8b56ccf8c1ae1c1fdc3083a8`** (#406). `origin/main`은 없으며 실제 기본 브랜치는 **`claude/investment-system-top500-validation-alrugm`**이다. fetch·git log·gh·공개 파일·플러그인 로그를 대조했다. 이후 실행은 다시 확인한다.

읽기: [START_HERE](START_HERE.md) → [방향 전환 대장](docs/SPEC/DIRECTION_CHANGES.md) → [WORKING_RULES](WORKING_RULES.md) → [기능 현황](docs/SPEC/FUNCTION_STATUS.md) → [결정 원문](implementation/docs/USER_DECISIONS_PENDING.md). 최신 이행 순서는 **10/25 오너 Main 지시(아래)**가 과거 대기·순서 표현에 우선한다.

## 0. 역할·지금 관리할 흐름 (최대 3개)

Main이 공용 파일·코드·병합·배포를 조정한다. Codex는 검증·리뷰와 허용된 **#413 문서**만 작성·push한다(DC-09). 문서 예외를 코드·병합·배포 권한으로 확대하지 않는다. 한 항목의 새 승인만 BLOCKED로 두고 독립적인 기승인 작업은 계속한다.

| 흐름 / 기능번호 | Main 이행 | Codex 검증·문서 | 현재 상태 |
| --- | --- | --- | --- |
| **1 긴급 / 2·9.2** | #410 최종 HEAD 확인·기승인 병합 → ALLSHARDS-1026 1회 → collect/verify/deploy·게시 검증 | HEAD·CI·중복 실행·현 게시본 점검 | #410 green·미병합, all_shards 미실행. **#413·#392·중앙 V는 선행조건 아님** |
| **2 정본 문서 / 공통** | 최종 #413 지정 검사·CI 성공 후 기승인 병합 → 중복 #412 닫기 | #412 고유 내용 회수·조회 한계 보정·#413 최종 검사 | 최종 수정 HEAD 검증·CI 조건 이행 중. 이력·브랜치 삭제 승인 없음 |
| **3 중앙 V / 2·6** | 두 오류 원인 확인 → #400 최소 수정·사슬 전파 → 비게시 재리허설 | 로그·합성 재현·수정안 리뷰 | 원인 구조 재현; 실제 run 최초 유발 원인은 미확정. 수정·새 리허설 미실행 |

#392 준비와 화면 확장은 장기 대기열에 유지하며 동시에 새 흐름을 더 열지 않는다.

## 1. 승인 이행·오너 결정 (마감순)

**#409·#410·ALLSHARDS-1026·#408은 이미 승인됐다. #413도 최종 변경 HEAD의 지정 검사·CI 성공 조건으로 Main 병합이 승인됐다. 재승인을 요청하지 않는다.**

| 번호 | 마감 UTC / KST | 실제 상태·남은 조건 |
| --- | --- | --- |
| **#409 UNI-PSKY-ALIAS** | **10-26 22:00 / 10-27 07:00 전 종료** (후속 실행과 공통) | 병합 완료 `c65f187a`; 게시 반영은 아직 안 됨 |
| **#410 UNI-ENDED** | **같음** | 최종 `afbec90e` CI 6 성공·2 skipped, clean·미병합. Main 기승인 병합 |
| **ALLSHARDS-1026 1회** | **같음** | 미실행. #410 병합 뒤 기본 브랜치에서 1회, 정기·다른 수동 배포와 중복/겹침 없이 collect→verify→deploy→게시 확인까지 종료 |
| #413 채택·#412 중복 종료 | 미정; 긴급 이행 선행조건 아님 | **채택 승인됨**. #412 고유 내용 회수 완료. 최종 검사·CI 성공 뒤 Main #413 병합→#412 닫기; 브랜치·이력 보존 |
| 중앙 V 첫 게시 창 | 정확한 날짜 미정, **11-04 전 목표** | 수정 후보 재리허설·점검표 후 날짜 제안, **게시 창 실행은 오너 승인 뒤**. 이 창의 all_shards는 ALLSHARDS-1026과 별도 |
| #392 TARGET v0 결합 해소 | 미정; 중앙 V와 다른 변경 창 | 준비·검증 뒤 병합안 보고. **최종 병합 승인 별도**, TV0 후속 7건 자동 승인 아님 |
| CV-MONTHEND-RECENT · D5-UPDATE · LISTING-ENDED-CODE | 시각 미정 | 첫 게시 비차단. 전용 상장 종료 사유 코드는 별도 PR·결정(11/9 확정 창 뒤 권장) |
| T-FRESH · MANUAL-QUOTE · TV0-* 및 나머지 장기 결정 | [결정 원문](implementation/docs/USER_DECISIONS_PENDING.md#남아-있는-결정만)의 선행 조건, 정확한 시각 미정 | 현행 계산·T-FRESH 유지. MANUAL-QUOTE는 P2-6 전. 긴 대기열은 보존하며 일괄 착수하지 않음 |

## 2. 10/25 KST 병합 (gh mergedAt)

| PR | 내용 | UTC / KST | merge SHA |
| --- | --- | --- | --- |
| [#398](https://github.com/kco994553-star/Investment-System1/pull/398) | P1 결정·DC-18 | 10-24 22:39:55 / 10-25 07:39:55 | `8e1fce12` |
| [#399](https://github.com/kco994553-star/Investment-System1/pull/399) | P2-1a 첫 화면 | 10-24 23:22:48 / 10-25 08:22:48 | `4c3d8142` |
| [#407](https://github.com/kco994553-star/Investment-System1/pull/407) | verify 제한 60분 | 10-25 07:33:54 / 16:33:54 | `f61b0373` |
| [#409](https://github.com/kco994553-star/Investment-System1/pull/409) | PSKY 별칭 | 10-25 08:18:52 / 17:18:52 | `c65f187a` |
| [#406](https://github.com/kco994553-star/Investment-System1/pull/406) | 결정 기록 | 10-25 08:23:12 / 17:23:12 | `c43b223f` |

#407의 과거 문서 07:11 UTC 표기는 실제 mergedAt과 다르다. 기준 이후 새 병합 없음.

## 3. 열린 PR·CI·승인

전체 15개(#413 포함). 아래 14개는 **각 HEAD에 성공 6개**, red/running 0개다. deploy·replay_source skipped는 성공으로 세지 않았다. #413의 자기 HEAD·최종 CI는 [PR 메타데이터](https://github.com/kco994553-star/Investment-System1/pull/413)로 확인한다(문서 수정 전 `7739e31d` 6개 성공).

| PR | 제목 요지 | HEAD | CI | 오너 승인·조건 |
| --- | --- | --- | --- | --- |
| [#412](https://github.com/kco994553-star/Investment-System1/pull/412) | 07:50 문서 초안 | `2ef64b68` | green | 고유 내용 회수, #413 병합 뒤 닫기 승인 |
| [#411](https://github.com/kco994553-star/Investment-System1/pull/411) | TARGET 확정 차단 점검 | `3f260f6b` | green | #405 뒤 동기화·검증, 사슬과 함께 |
| [#410](https://github.com/kco994553-star/Investment-System1/pull/410) | WBD 상장 종료 NA | `afbec90e` | green | 병합 조건 (i)~(vi) 포함 기승인 |
| [#408](https://github.com/kco994553-star/Investment-System1/pull/408) | P2-1 홈·검색 | `9c0c3249` | green | 기승인 통합, 새 web_app 미배포 |
| [#405](https://github.com/kco994553-star/Investment-System1/pull/405) | 중앙 V PR-D 판독기 | `eca9ab79` | green | 게시 창 조건; base #404 |
| [#404](https://github.com/kco994553-star/Investment-System1/pull/404) | 중앙 V PR-C 워크플로 | `8005575c` | green | 수정 사슬·리허설·게시 창 조건; base #403 |
| [#403](https://github.com/kco994553-star/Investment-System1/pull/403) | 중앙 V PR-B 가드 | `993a4682` | green | 같음; base #400 |
| [#400](https://github.com/kco994553-star/Investment-System1/pull/400) | 중앙 V PR-A 계산 코어 | `3589fd44` | green | 두 오류 최소 수정·재리허설 필요; base #393 |
| [#393](https://github.com/kco994553-star/Investment-System1/pull/393) | F_k·calc_version 23.1 | `59c97730` | green | 중앙 V 첫 게시와 같은 창 |
| [#392](https://github.com/kco994553-star/Investment-System1/pull/392) | TARGET v0 결합 해소 | `f8307b7c` | green | DIRTY, 통합 검증·최종 병합 승인 별도 |
| [#361](https://github.com/kco994553-star/Investment-System1/pull/361) | Worker 분할 이벤트 | `910d5661` | green | DIRTY, 공급원 권리로 배포 보류 |
| [#305](https://github.com/kco994553-star/Investment-System1/pull/305) | [WIP] Atlas | `bbb7bb55` | green | draft·참고, DIRTY |
| [#281](https://github.com/kco994553-star/Investment-System1/pull/281) | [WIP] 프론트엔드 시안 | `3b22cae1` | green | draft·참고 |
| [#267](https://github.com/kco994553-star/Investment-System1/pull/267) | 투자 스튜디오 | `ad469e5c` | green | 보류 |

조회 범위: repo ruleset 목록·**24499602 HG-02 canonical hard guard** 상세·canonical 실효 branch rules는 조회 성공. PR 필수, 리뷰 승인 수 **0**, 필수 check `repository-guard`, bypass actors 없음. **legacy branch protection API만 403**이며 모든 ruleset 미확인으로 쓰지 않는다. GitHub 리뷰 0과 오너 승인(대화·결정 기록)은 별개다.

## 4. 실제 상태·게시 검증

| 대상 / 기능번호 | 구현 | 실제 시험·검증 | 통합 | 배포 | LIVE |
| --- | --- | --- | --- | --- | --- |
| #407 / 9.2 | 완료 | PR CI green | 완료 | 워크플로 반영; 다음 정기 적용 미확인 | 미확인 |
| #409·#410 / 2·9.2 | PR 구현 | 양쪽 최종 CI green | #409만 완료 | 새 수집·게시 미반영 | 아래 공개 파일 실측, 성공 조건 미충족 |
| #398·#399·#408 / 1 | 구현 | 각 PR CI green | #398·#399 완료, #408 미완료 | 새 web_app 미배포 | 새 앱 실사이트 미확인 |
| 중앙 V / 2·6 | PR 구현·수정 잔여 | CI green, 리허설 최종 FAIL, 합성 원인 재현 | 미완료 | 미배포 | 미확인 |
| 기존 사이트 / 2·9.2 | 기존 구현 | collect·verify 성공 | `4c3d8142` | Pages 성공 | 공개 자료 확인; 브라우저 동작 미확인 |

공개 파일 **09:38:28 UTC** 확인([Universe](https://kco994553-star.github.io/Investment-System1/universe-codes.json)·[QGV](https://kco994553-star.github.io/Investment-System1/sec-qgv2.json)·[원장](https://kco994553-star.github.io/Investment-System1/forward-validation-ledger.json)):

| 항목 | 현재 실측 | ALLSHARDS-1026 뒤 확인할 것 |
| --- | --- | --- |
| Universe·커버리지 | 고유 504/504, Q 486/504, G 494/504, 양쪽 478/504, 샤드 7/7 | 504 유지·실제 커버리지 재측정; 사전 예상치를 완료값으로 쓰지 않음 |
| PSKY | 세 파일 acquired_at **10-17 03:13:16.553527 UTC** | 새 acquired_at |
| WBD | 세 파일 LIVE, shares `COVER_UNCONFIRMED`, QG/QGV 사유 없음 | 사유 있는 NA·값 없음·`listing_ended=1` |
| 7일 초과 | 전체 2, **값 있는 Universe 2**(Universe+TARGET도 2), state STALE=0 | **값 있는 행 7일 초과 0**. WBD NA의 마지막 관측 때문에 남는 전체 stale와 분리 |
| 원장 PRIMARY | 공개 최신은 10/23 PRIMARY | 10/26~10/28은 **미래·미실행, 실제 결과 미확인**. 현재 조건 충족 여부와 후속 run 결과를 따로 기록 |

값 있는 행은 LIVE/STALE다. 7일 초과 집계는 파일 as_of 또는 읽기 시각과 acquired_at의 7×24h 차이(두 기준 모두 2). 원장 PRIMARY는 같은 calc_version의 값 있는 Universe+TARGET의 **UTC 취득 날짜와 세션 날짜 차이**를 쓰므로 별도 검사한다. 최신 [collect 로그](https://github.com/kco994553-star/Investment-System1/actions/runs/40146210895/job/121028026556)는 플러그인으로 읽음: `stale_7d_rows=2`, `unresolved_codes=2`, `listing_ended` 토큰 없음. gh 로그 경로 Forbidden과 플러그인 읽기 성공을 구별한다.

## 5. 다음 우선순위·대기열

1. **긴급 이행**: Main #410 최종 HEAD 재확인·병합→기본 브랜치 ALLSHARDS-1026 1회→collect/verify/deploy·게시 자료 확인. 실행 직전 활성 run 재확인(기준 시각 겹치는 run 0). 정기 cron 22:17 UTC, 공통 배포 concurrency만 믿고 중복 run을 만들지 않는다.
2. **#413 정본**: 지정 검사·최종 CI 성공→Main 기승인 병합→#412 중복 종료. [#412 고유 원문 회수](implementation/docs/handoff/HANDOFF_PR412_20261025.md)·[10/24 이력](implementation/docs/handoff/HANDOFF_HISTORY_20261024.md)은 보존. 긴급 흐름을 기다리게 하지 않는다.
3. **중앙 V 재검증**: [오류별 검증 리뷰](implementation/docs/qgv_scoring_standard/CENTRAL_V_REHEARSAL_REVIEW_20261025.md)→Main #400 최소 수정→#409·#410 포함 사슬 전파→수정된 새 후보 SHA로 비게시 리허설. 구 SHA Re-run으로 수정 검증을 대신하지 않는다.

장기 대기열(현재 흐름을 닫으며 순차 진행): **#392** 최신 canonical 동기화·충돌 해결·기기 키 이전·백업·기존 그림 보존·멱등성 검증→중앙 V와 다른 창의 병합안(최종 승인 별도, TV0 후속 7개 제외). **프론트엔드** #408 기승인 통합 뒤 기능 **2 QGV→6 포트폴리오→5 뉴스→3 기술→4 매크로→7 프롬프트→8 트리→9 Lab**. 기존 엔진·승인 명세 재사용, 미완성 백엔드는 NA·사유. 중앙 V/정기 7/7 때문에 모든 화면 구현·미리보기를 멈추지 않는다. **P3 실사이트 전환·배포 별도 승인**.

중앙 V 게시 창 계획: **#393→수정 #400→#403→#404→전환용 별도 all_shards·새 calc_version 숫자 재대조→#405→#411**. #411은 #405 뒤 동기화해 `freshFor`·`official`·숨김 상태·TARGET 핸들러 충돌 검증. 11-04 전 날짜는 재리허설·점검표 후 제안하고 오너 승인 뒤 실행한다. 긴급 ALLSHARDS-1026과 목적·run을 분리한다.

## 6. 정기 실행·중앙 V 실측

| 대상 / 관측분 | run 번호 / ID | UTC 시작→종료 | 결과 |
| --- | --- | --- | --- |
| SEC 10/22분 | [#21 / 39879258841](https://github.com/kco994553-star/Investment-System1/actions/runs/39879258841) | 10-23 00:37:54→01:20:47 | collect·verify·deploy 성공, 1/7 |
| SEC 10/23분 | [#22 / 40045938631](https://github.com/kco994553-star/Investment-System1/actions/runs/40045938631) | 10-24 00:38:05→01:17:10 | 성공, 2/7 |
| **SEC 최신 10/24분** | [**#23 / 40146210895**](https://github.com/kco994553-star/Investment-System1/actions/runs/40146210895) | 10-25 00:19:00→01:06:12 | **성공 3/7**, SHA `4c3d8142`, Pages deployment 7306836646 success |
| 중앙 V 비게시 리허설 | [#1 / 40156760950](https://github.com/kco994553-star/Investment-System1/actions/runs/40156760950) | 10-25 03:03:01→03:32:46 | **최종 FAIL, 6/12 PASS**, attempt1. IEX_GZIP_FAILED·ROWS_OF_ANOTHER_CALC_VERSION(other_calc=2)·NOT_MEASURED4개 |

**ALLSHARDS-1026 미실행**, 중앙 V 수정 후보 재리허설도 미실행. Secret은 로그의 기능상 결과만 사용하며 값·키·토큰을 조회/기록하지 않는다. step success나 workflow success만으로 중앙 V 게시 성공을 주장하지 않는다.

## 7. 알려진 위험·관리자 노트

| 위험 | 영향·확인 |
| --- | --- |
| WBD 사유 코드 미분리 | #410도 `CIK_UNRESOLVED` 표기. 전용 `LISTING_ENDED`는 별도 결정·PR, 긴급 병합 차단 아님 |
| telecom MIN_PEERS=8 경계 | #410 뒤 9→8. **8 미만이면 Q의 GENERAL UNIVERSE_FALLBACK**(v2_scoring.py:183~194); 요인별 값 부족도 fallback. 실제 변경 뒤 비교군·영향 확인 |
| 중앙 V 두 오류 | gzip 실패와 입력 버전 혼합은 별개. NOT_MEASURED는 미검증. 수정·새 SHA·최종 verdict로 판정, 가드 약화 금지 |
| 신선도·원장 | 전체 stale·값 있는 행·세션 날짜 규칙 분리. 6일 이상 보존 행은 매일 보고. T-FRESH·계산 규칙 임의 변경 없음 |

관리자 노트: **기능 구현 % = 미산정 / 프론트엔드 % = 미산정**(분모·완료 기준 별도 필요). 이번 문서·리뷰만으로 제품 진행률을 올리지 않는다. 완료 묶음은 **기능번호 / 구현 / 실제 시험 / 통합 / 배포 / LIVE / PR·HEAD·run / 남은 조건 / 다음 승인**으로 보고한다.

## 8. 경계

Universe504 고정(DC-01), 공식 V는 IEX HIST 서버 계산·공개 방향(DC-02), 아직 canonical 미통합. 원시 가격·EV·배율·수익률·보유·Secret 값·키·토큰 값은 문서·로그·공개 산출물에 넣지 않는다. NA를 0으로 채우지 않는다. Frozen·원장·SUPERSEDED·#412 이력 보존. 계산·가중치·T-FRESH·공개 경계·보호규칙·AUTONOMY_MODE·유료 계약 임의 변경 없음.
