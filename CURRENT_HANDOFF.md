# 현재 인수인계 — 2026-10-24 (Claude Code Main)

확인 시각: **2026-10-24 23:25 UTC / 2026-10-25 08:25 KST**. 이 시각 이후의 PR·Actions·게시 상태는 `git log`와 열린 PR로 다시 확인한다. 구현 / 시험 / 병합 / 게시 / 실사이트 확인을 나눠 적는다.

먼저 읽기: **[START_HERE.md](START_HERE.md) → [방향 전환 대장](docs/SPEC/DIRECTION_CHANGES.md)** → [WORKING_RULES.md](WORKING_RULES.md) → 이 파일 → [기능 명세 v1.0](docs/SPEC/FUNCTION_HIERARCHY_v1.0.md) → [기능 현황](docs/SPEC/FUNCTION_STATUS.md) → [사용자 결정](implementation/docs/USER_DECISIONS_PENDING.md) → [새 프론트엔드 계획](implementation/docs/frontend_v2/FRONTEND_V2_PLAN.md)(#385) → [자료 계약](implementation/docs/FRONTEND_DATA_CONTRACT.md).
이전 기록: [10/23](implementation/docs/handoff/HANDOFF_HISTORY_20261023.md) · [10/21 Codex Main 원문](implementation/docs/handoff/HANDOFF_HISTORY_20261021.md) · [10/20](implementation/docs/handoff/HANDOFF_HISTORY_20261020.md) · [10/18~19](implementation/docs/handoff/HANDOFF_HISTORY_20261018_19.md).

## 0. 역할

- **병합·공용 파일·이 파일 갱신은 Claude Code Main 하나가 맡는다**(2026-10-22). 공용 파일은 가드 고정값(`pages_artifact_guard.py`), CI 목록(`ci_*_tests.txt`), `app.js` 통합, 이 파일, `USER_DECISIONS_PENDING.md`다.
- **2026-10-24 사용자 결정: 이 Main 세션이 새 프론트엔드 P1도 맡는다.** P1·P2 PR은 `web_app/`·그 시험·`docs/frontend_v2/`만 고친다. 공용 파일 변경은 Main 몫으로 따로 적는다. P3 전환(경계 시험 이식·가드 고정값 교체·옛 화면 삭제·배포)은 사용자 승인으로 한다.
- **Codex는 검증·리뷰만 한다.** push·병합하지 않는다.
- 어떤 PR을 작업하려면 아래 "작업 중" 표에 **PR 번호·담당·시작 시각**을 먼저 적고, 끝나면 지운다. 표에 다른 담당이 있는 PR은 건드리지 않는다.

### 작업 중

| PR | 담당 | 시작 (UTC / KST) | 내용 |
| --- | --- | --- | --- |
| #393 → #400 → #403 → #404 → #405 중앙 V 사슬 | Claude Code Main | 2026-10-24 06:00 / 15:00 | 결정 완료(CV-LEAK (i)·CV-SPLIT (ii)·CV-CARRY (i)·CV-D-*). **10-24 밤 정기 실행 전 병합 금지.** 첫 게시 전 조건: Secret 2개, 하루치 측정(GSQ-024 검증 먼저), CV-SPLIT (ii) 반영 뒤 #400 재시험, 첫 게시 점검표 채우기 → 첫 게시 날짜 제안 |
| `ccr-263267c9-f5ng5h` Main 문서(10-24 밤 결정·#392 후속 결정·인수인계) | Claude Code Main | 2026-10-24 22:50 / 10-25 07:50 | `USER_DECISIONS_PENDING`·이 파일 |

## 1. 기준·게시

- canonical: **claude/investment-system-top500-validation-alrugm**, HEAD **4c3d8142** (#399 병합, 2026-10-24 23:22 UTC / 10-25 08:22 KST).
- 10/24 병합(모두 최신 canonical 위 필수 6체크 성공 확인 뒤, 소유자 승인):
  - #395 CI 실행기 `ubuntu-24.04` 고정: HEAD 67f2ca85 → 병합 **d6eaaa8a** (00:09 UTC / 09:09 KST). `ubuntu-latest`가 26.04로 바뀌어 Playwright 1.58.2 설치가 실패했기 때문이다.
  - #394 명세 원문·방향 전환 대장·금지 표현 검사·START_HERE: HEAD b3d5a41c → 병합 **9159df0d** (01:09 UTC / 10:09 KST). 문서·검사만이라 화면 변화 없음.
  - #385 새 프론트엔드 P0(셸·디자인 부품·글꼴·개발 빌드): 동기화본 2d7aec84(공용 CI 목록 충돌은 두 시험 모두 유지, 4.5 메뉴 "나비효과") → 병합 **a359ae91**. `web_app/`은 배포되지 않는다.
  - #396 옛 화면 4.5 "나비효과"(가드 해시 2개 재고정)·DC-02 계획·인수인계 → 병합 **d8fa097b** (05:44 UTC).
  - #397 새 프론트엔드 P1 자료·계산 층(옛 모듈 57개 재사용, 새 시험 5개 CI 등록) → 병합 **f3cee500** (06:26 UTC). 오늘 정기 실행 verify부터 P1 시험이 돈다. 실패하면 시험을 건너뛰지 않고 원인부터 보고한다(사용자 지시).
  - #391 TARGET v1 "임시 V"·F1(첫 확정본 날짜 기준, 사용자 결정)·F2 → 병합 **fa0d9fcd** (06:58 UTC).
  - #398 새 프론트엔드 P1 결정 반영·결정 기록·DC-18 → 병합 **8e1fce12** (22:39 UTC, 사용자 승인 10-24 밤, 최종 HEAD 13d47c3e 필수 6체크 녹색). 배포 안 되는 범위.
  - #399 새 프론트엔드 P2-1a 첫 화면 구조(셸 먼저, 자료층은 첫 그림 뒤)·폰 성능 시험 → canonical 기준으로 바꾸고 동기화 ebaa4118(필수 6체크 녹색) → 병합 **4c3d8142** (23:22 UTC). 배포 안 되는 범위. 새 성능 시험 `web_app_first_paint_browser_test.js`가 10/24분 정기 실행 verify에서 처음 돈다(실패하면 원인부터 보고, 건너뛰기 금지).
  - #396·#391의 화면 변화(4.5 이름, TARGET v1 임시 V 표시)는 10/24분 정기 실행 배포 때 실사이트에 반영된다.
- 10/23 병합: #384 #378 #382 #387 #389 #388 #386(마지막 81d7b58d). 자세한 내용은 [10/23 기록](implementation/docs/handoff/HANDOFF_HISTORY_20261023.md).
- **실제 게시: d6eaaa8a.** 10/23분 정기 실행 [run 40045938631](https://github.com/kco994553-star/Investment-System1/actions/runs/40045938631)이 collect·verify·deploy 모두 성공했다(24.04, 시작 00:38 UTC, 배포 01:17 UTC / 10:17 KST).

## 2. 정기 실행·연속 성공

| 관측일 | run | 결과 | 비고 |
| --- | --- | --- | --- |
| 10/20 | 39522288311 | collect 성공 · **verify 실패** · deploy 건너뜀 | 연속 끊김. 수정 #370, 10/20 자료는 #371 복구 게시 |
| 10/21 | 39701051682 | 성공 | (셈 시작 전) |
| 10/22 | 39879258841 | **성공 · 연속 1회째** | 사용자 결정(10/22)으로 이 실행부터 센다. 원장 각 4건 |
| 10/23 | 40045938631 | **성공 · 연속 2회째** | #395 병합 뒤 첫 실행(24.04). 원장 v1/v2 각 5건(`appended=1`, session 2026-10-23), RAW 재사용(`source=RAW raw=FOUND recovered_records=0`), 비공개 업로드 `forward-ledger-2026-10-23`. 샤드 5(65종목) 수집 65/65 |

- 연속 성공: **2/7** (10/23, 이 표의 10-22 결정 기준). 사용자는 10-24 밤 3/7로 적었다(10/21 run 39701051682를 넣은 셈으로 보임) — 기준 확인 대기. 예약 22:17 UTC 실행이 나흘 연속 2시간 20분 안팎 늦게 시작했다(00:36·00:40·00:37·00:38 UTC). 확인은 01:30 UTC 무렵을 기본으로 한다.
- 10/23 게시 커버리지: Q 486 / G 494 / 양쪽 478, 분모 504, calc_version `qgv2-calc/2026-10-17.1`, 샤드 7/7, 7일 경과 행 0, as_of 2026-10-24 00:50 UTC.
- 부분 실패(배포는 막지 않음, 10/22와 같음): 8-K `ASML_6K_EARNINGS_UNCONFIRMED`(17개 중 1개), 뉴스 GDELT HTTP 429·IR 피드 실패로 PARTIAL_FAILED(항목 45), 로고 Wikidata 원천 불가로 이니셜 506. 원인 조사는 별도 작업.

## 3. TARGET v1 확정 조건 (확정 창 2026-11-09~11-15)

| 조건 | 상태 |
| --- | --- |
| 구현 #248·#263 | 병합·게시 |
| Q·G 각 454/504 이상 | 486 / 494 충족(10/23 게시본) |
| 10종목 숫자 대조(같은 calc_version) | **통과 기록**(10-23 #386, 앱 계산식 + 시험 가격, DC-16), `qgv2-calc/2026-10-17.1`. #393이 calc_version을 올리면 재대조 필요 → [계획 5절](implementation/docs/qgv_scoring_standard/CENTRAL_V_DC02_PLAN_20261024.md) |
| V 출처 | 중앙 V 미게시 → "임시 V"(#391 병합). 중앙 V가 11-04 전에 게시되면 #405(옛 화면 작은 판독기, D8 (b))로 공식 V. 결정: CV-D-FRESH 2일·CV-D-BUTTON 둔다·CV-D-ROWS 기기 경로 대응·CV-D-CHURN 다시 만들기 |
| 실제 사용자 카드 응답 | 미시작 |

## 4. 열린 PR (10-24 23:00 UTC)

| PR | 상태 | 남은 것 |
| --- | --- | --- |
| #393 → #400 → #403 → #404 → #405 중앙 V 사슬 | 모두 녹색, 결정 완료, 첫 게시 조건 진행 중 | CV-SPLIT (ii)를 #400에 넣고 위로 병합(로컬 작업 중), Secret 2개, 하루치 측정, 점검표, 첫 게시 날짜 제안 |
| #392 TARGET v0 결합 해소 | 10-23부터 승인 대기. **canonical과 충돌**(`pages_artifact_guard.py` 고정값만, 시험 병합으로 확인). 마지막 동기화 a359ae91 | 후속 결정 7개는 `TV0-*`로 옮김. 순서 권장은 사용자 보고 참고(중앙 V 첫 게시 뒤 동기화·CI·폰 확인) |
| #361 Worker 분할 이벤트 | 배포 보류(Yahoo 권리 미해결) | 무료 대안 공급원 결정 |
| #305·#281(draft, 참고) · #267(보류) | 그대로 | — |

- 중앙 V 원본 브랜치 `claude/cv-core-publisher`는 #400으로 흡수됐다. `claude/iex-v4-backfill`(U8 1회 실행 완료)·`claude/iex-hist-probe`(PASS)는 기록 보존.
- `claude/fe2-*` 4개는 P0 커밋만 있는 빈 레인이다.

## 5. 다음 할 일

1. 10/24분 정기 실행 확인(01:30 UTC 무렵). P1 시험이 verify에서 처음 돈다. 실패하면 원인부터 보고(시험 건너뛰기 금지).
2. 화면 P2 메뉴별(기능 1 → 2 → 6 → 5 → 3 → 4 → 7 → 8 → 9), PR-D2(새 프론트엔드 `OFFICIAL_READER` 전환).
3. 중앙 V 첫 게시 조건(10-24 밤 결정): Secret 2개(사용자) → 하루치 측정(분리 실행, 게시 안 함) → CV-SPLIT (ii) 반영·재시험 → 점검표 → 첫 게시 날짜 제안(11-04 전, 연속 집계를 깨지 않는 날) → 그날 사슬 병합·`all_shards` 1회·§5 재기록 PR.
4. 결정 대기: D5-UPDATE, MANUAL-QUOTE, `TV0-*` 7개, CV-SPLIT-DATA(전 종목 최근 월말가 보충, 제안 준비 중).
5. #392 동기화(가드 고정값 충돌) → CI → 폰 확인 → 병합(순서는 사용자 결정). 8-K·뉴스·로고 부분 실패 원인 조사.

## 6. 유지할 경계

- 원시 가격·EV·수익률·배율·내재 성장률·보유·거래·시트 ID·토큰·환율 값을 저장소·Pages·Actions 로그에 넣지 않는다. 공식 V 점수·순위는 2026-10-23 결정(GSQ-024)으로 IEX HIST 기반 서버 계산 후 공개한다(아직 구현 안 됨). NA를 0으로 채우지 않는다.
- force push·ruleset·AUTONOMY_MODE(READ_ONLY) 변경 금지. 가드 비활성화·검사 생략·보호 대상 축소 금지. 권한 검사가 거부하면 우회하지 않고 보고한다.
- Frozen 자료·전진검증 원장 보존. Holdout 사용 권한 확대 없음.
- 다른 작업자의 worktree·scratchpad·원자료를 지우지 않는다.
