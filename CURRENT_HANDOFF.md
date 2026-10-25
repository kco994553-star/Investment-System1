# 현재 인수인계 — 2026-10-25 (Claude Code Main)

- **기준 시각: 2026-10-25 07:50 UTC / 16:50 KST** (사실 확인 07:42~07:50 UTC). 기준 commit: canonical `claude/investment-system-top500-validation-alrugm` **f61b0373**(#407 병합). 이 시각 뒤 상태는 `git log`·열린 PR·Actions로 다시 확인한다.
- 현재 Pages 게시본: 정기 실행 [run 40146210895](https://github.com/kco994553-star/Investment-System1/actions/runs/40146210895)이 canonical **4c3d8142**를 10/25 01:06 UTC에 배포. f61b0373(#407)은 워크플로만 바꿔 다음 정기 실행부터 적용된다.
- 먼저 읽기: [START_HERE.md](START_HERE.md) → [방향 전환 대장](docs/SPEC/DIRECTION_CHANGES.md) → [WORKING_RULES.md](WORKING_RULES.md) → 이 파일 → [기능 명세 v1.0](docs/SPEC/FUNCTION_HIERARCHY_v1.0.md) → [기능 현황](docs/SPEC/FUNCTION_STATUS.md) → [사용자 결정](implementation/docs/USER_DECISIONS_PENDING.md).
- 이전 기록: [10/24~10/25 오전](implementation/docs/handoff/HANDOFF_HISTORY_20261024.md) · [10/23](implementation/docs/handoff/HANDOFF_HISTORY_20261023.md) · [10/21](implementation/docs/handoff/HANDOFF_HISTORY_20261021.md) · [10/20](implementation/docs/handoff/HANDOFF_HISTORY_20261020.md).
- 역할: 병합·공용 파일(가드 고정값, CI 목록, 이 파일, `USER_DECISIONS_PENDING.md`)은 Claude Code Main 하나가 맡는다. Codex는 검증·리뷰만 한다. 병합·배포·워크플로·가드·방법론·가중치 변경은 소유자 승인 뒤에만 한다.

## 작업 중

다른 쪽이 손대기 전에 여기에 PR·담당·시작 시각을 적고, 끝나면 지운다([WORKING_RULES](WORKING_RULES.md)).

| PR·작업 | 담당 | 시작 (UTC) |
| --- | --- | --- |
| #409 → #410 병합 → all_shards → 원장 확인 | Claude Code Main | 10/25 07:34 (#409 동기화 push) |
| IEX 다운로드 수정 → 중앙 V 사슬(#400~#405)·리허설 가지 반영(로컬 commit, push 전) | Claude Code Main | 10/25 07:01 |
| 이 문서 PR(`claude/handoff-20261025`) | Claude Code Main | 10/25 07:40 |

## 1. 오너 결정·승인 대기 (마감순)

결정 원문·선택지는 [USER_DECISIONS_PENDING](implementation/docs/USER_DECISIONS_PENDING.md). 10/24 밤·10/25 결정 기록은 #406 병합 대기라 canonical 문서에는 아직 없다.

| 번호 | 무엇을 | 상태 (기준 시각) | 마감 |
| --- | --- | --- | --- |
| #409 | PSKY 별칭 병합 | 승인됨(10/25). 동기화본 a6ebbd1c 5/6 녹색, build 진행 중 | **10/27 07:00 KST (10/26 22:00 UTC)** |
| #410 | WBD 상장 종료 NA 병합 | 승인됨(10/25). 536e0fcf 6/6 녹색(기준 4c3d8142) → #409 병합 뒤 canonical 동기화·CI 다시 | 같음 |
| all_shards 1회 | 수동 수집·배포 1회 | 승인됨(10/25). #409·#410 병합 뒤, 정기 실행·다른 수동 배포와 겹치지 않게. 뒤에 원장 10/26~10/28 세션 PRIMARY 조건 확인(값 있는 행 중 7일 넘은 행 0, PSKY 새 `acquired_at`, WBD `listing_ended=1`) | 같음 |
| 중앙 V 첫 게시 날짜 | 사슬 병합·all_shards·계획 §5 숫자 재기록을 같은 창에서 | 리허설 재실행 PASS 뒤 Main이 제안 | 11/04 전 목표(10/24 밤 결정) |
| #392 | TARGET v0 결합 해소 병합 | 승인 대기. canonical과 충돌(가드 고정값) | 중앙 V 첫 게시 뒤 권장 |
| LISTING-ENDED-CODE | 정확한 '상장 종료' 사유 코드(스키마·고정 해시 변경, 별도 PR) | 계획 단계 | 11/09 뒤 |
| CV-MONTHEND-RECENT | 전 종목 최근 월말가 보충(CV-SPLIT (ii) 보조 검사를 전 종목에 효과 있게) | 제안 | 없음(첫 게시를 막지 않음) |
| MANUAL-QUOTE · D5-UPDATE · TV0-* | 손 입력 시세 · 월말가 갱신 방식 · #392 후속 7개 | 대기 | MANUAL-QUOTE는 P2-6 전 |

- 승인된 병합 중 마감 없는 것: #406·#408(CI 녹색이면), #407(완료), #411(#405 뒤 사슬과 함께).
- T-FRESH는 결정됨(7일). 여유 0 운영 위험만 7절에 둔다.

## 2. 오늘(10/25 KST) 병합

| PR | 병합 commit | 시각 (UTC / KST) |
| --- | --- | --- |
| #398 새 프론트엔드 P1 결정 반영 | 8e1fce12 | 10/24 22:39 / 10/25 07:39 |
| #399 새 프론트엔드 P2-1a 첫 화면 구조·성능 시험 | 4c3d8142 | 10/24 23:22 / 10/25 08:22 |
| #407 정기 실행 verify 제한 40 → 60분 | f61b0373 | 10/25 07:33 / 16:33 |

## 3. 열린 PR

CI = 필수 6체크(build, guard, repository-guard, ingest-and-gate, presentation, validate), 현재 HEAD 기준.

| PR | 제목(요약) | HEAD | CI | 승인 |
| --- | --- | --- | --- | --- |
| #409 | PSKY: SEC (NYSE, SKYD) 별칭, CIK 고정 | a6ebbd1c | 진행 중(5/6, build) | 승인됨 |
| #410 | WBD: '상장 종료' 항목으로 사유 있는 NA | 536e0fcf | 녹색(동기화 필요) | 승인됨 |
| #406 | Main 결정 기록(10/24 밤·10/25 결정) | 378c6a1b | 진행 중(5/6, build) | 승인됨(녹색이면) |
| #408 | 새 프론트엔드 P2-1 홈·기업검색(배포 안 됨) | b036324e | 녹색(동기화 필요) | 승인됨(녹색이면) |
| #411 | TARGET v1 확정 차단 점검(표시 전용, 점검 버튼) | 3f260f6b | 녹색(동기화 필요) | 승인됨 — #405 뒤 사슬과 함께 |
| #393 → #400 → #403 → #404 → #405 | 중앙 V 사슬(F_k·calc_version, 계산 코어, 가드, 워크플로, 옛 화면 판독기) | 59c97730 · 3589fd44 · 993a4682 · 8005575c · eca9ab79 | 녹색(#404 build는 60분 제한 취소 뒤 1회 재실행 성공). #393은 동기화 필요(기준 4c3d8142) | 첫 게시 날짜 승인 필요 |
| #392 | TARGET v0 결합 해소 | f8307b7c | 녹색(10/24 기준), 충돌 | 승인 대기 |
| #361 | Worker 분할 이벤트 | 910d5661 | 녹색(10/20 기준 6/6), canonical보다 593 commit 뒤 | 배포 보류(공급원 권리) |
| #305 · #281 | 옛 프론트엔드 시안(draft) | — | — | 참고용 |
| #267 | 인터랙티브 투자 스튜디오 | — | — | 보류 |

## 4. 상태 구분

구현 = 코드 작성 · 검증 = 시험/CI 녹색 · 통합 = canonical 병합 · 배포 = Pages 게시 · LIVE = 실사이트 확인.

| 작업 | 구현 | 검증 | 통합 | 배포 | LIVE |
| --- | --- | --- | --- | --- | --- |
| verify 60분(#407) | 완료 | 완료 | 완료 | 해당 없음(워크플로) | 미확인(10/25분 정기 실행 대기) |
| 새 프론트엔드 P1D·P2-1a(#398·#399) | 완료 | 완료 | 완료 | 해당 없음(`web_app/`은 P3 전환 때 배포) | 해당 없음 |
| 4.5 "나비효과"(#396)·TARGET v1 "임시 V"(#391) | 완료 | 완료 | 완료(10/24) | 완료(run 40146210895) | 미확인(공개 파일 내용만 확인, 화면 직접 확인 안 함) |
| PSKY 별칭(#409)·WBD NA(#410) | 완료 | 합본 로컬 전체 시험 3,676 통과. CI #409 진행 중·#410 녹색 | 미완 | 미완 | 미완 |
| TARGET v1 확정 차단 점검(#411) | 완료 | 완료 | 미완(#405 뒤) | 미완 | 미완 |
| P2-1 홈·검색(#408) | 완료 | 완료 | 미완 | 해당 없음(P3) | 해당 없음 |
| 중앙 V 사슬 | 완료 | CI 완료 · 리허설 실패(7절) | 미완 | 미완 | 미완 |
| 시안 추가 보드 18쌍(손그림 칠판 아티팩트) | 그리기 완료 | 검토 진행 중 | 해당 없음 | 아티팩트 게시 미완 | 해당 없음 |

## 5. 다음 우선순위

1. #409 → #410 병합 → all_shards 1회 → 원장 PRIMARY 조건 확인(10/26 22:00 UTC 전).
2. #406·#408 동기화·병합, 10/25분 정기 실행 확인(10/26 00:19 UTC 무렵).
3. IEX 다운로드 수정 push(사슬 위로) → 리허설 재실행 → 첫 게시 날짜 제안.

## 6. 정기 실행(sec-daily-public-inputs)

| 관측일 | run | 결과 | 연속(DC-13) |
| --- | --- | --- | --- |
| 10/22분 | 39879258841 | 성공 | 1/7 |
| 10/23분 | 40045938631 | 성공 | 2/7 |
| 10/24분 | 40146210895 | 성공(시작 00:19 UTC, 배포 01:06 UTC, verify 33.7분) | **3/7** |

- 연속 집계는 10/22분부터 센다(DC-13, 소유자 확인 10/25: 10/21 실행은 넣지 않음).
- 다음: 10/25분 실행(10/26 00:19 UTC 무렵, verify 제한 60분 첫 적용). 진행 중 run 없음(기준 시각).

## 7. 알려진 위험

| 위험 | 내용 | 대응 |
| --- | --- | --- |
| WBD 사유 코드 미분리 | #410 뒤 WBD 사유가 `CIK_UNRESOLVED`라 화면에 'CIK 미해결'·'CIK 미확인'으로 보인다(CIK는 알고 있음) | LISTING-ENDED-CODE 별도 PR(결정 대기) |
| telecom `MIN_PEERS` 8 경계 | #410 뒤 telecom 업종군이 8곳. 하나 더 빠지면 업종군 전체가 GENERAL 전체 순위로 바뀐다(`qgv/v2_scoring.py`의 `UNIVERSE_FALLBACK`). 예: PSKY까지 빠지면 Q가 FOX·FOXA 약 −18.3, TMUS −12.2, VZ −11.0 | #409 뒤 PSKY 업종군 유지 확인, 8 미만이 되면 즉시 보고 |
| 중앙 V 리허설 재실행 대기 | run 40156760950(10/25 03:03 UTC): 12기준 중 6 PASS. FAIL: 입력 행 calc_version 섞임(other_calc=2), V 단계 `IEX_GZIP_FAILED`(나머지 4기준 미측정). 섞인 2행이 PSKY·WBD 보존 행이라는 것과 IEX 10/23 파일 자체가 정상이라는 것은 실행 기록 밖 근거(공개 sec-qgv2.json 대조, 컨테이너 스트림 시험) | #409·#410 병합과 IEX 수정 뒤 재실행 |
| 확정 7일 기준과 7샤드 회전 | T-FRESH 7일과 7샤드 회전 사이 여유가 0. 매일 00:00 UTC부터 그날 배포까지 확정이 막히고, 정기 실행이 하루 빠지면 약 7일 막힌다 | #411 점검 줄로 미리 보임 |
| 사슬 동기화 | canonical f61b0373(#407)이 #404와 같은 워크플로 파일을 바꿨다. 로컬 병합 시험은 충돌 없음 | 사슬 push 때 canonical도 함께 병합 |

- 보존 행 매일 점검: 기호 해석 실패로 이전 값이 보존된 행이 6일 이상이면 매일 보고에 넣는다(소유자 지시 10/25). 10/25 as_of 기준 보존 행 2(PSKY·WBD), 회전 대기 85(샤드 0).

## 8. 유지할 경계

원시 가격·가격 파생값·보유·거래·시트 ID·토큰·이메일은 저장소·Pages·로그에 넣지 않는다. Secret은 이름(`QGV_OFFICIAL_HMAC_KEY`, `RAW_REPO_READ_TOKEN`)만 쓴다. NA를 0으로 채우지 않는다. 가격 요청은 버튼을 누를 때만 한다. CSP·Pages 가드를 완화하지 않는다. 주문·매매 기능은 만들지 않는다. force push, ruleset·AUTONOMY_MODE 변경, 가드 완화 금지.
