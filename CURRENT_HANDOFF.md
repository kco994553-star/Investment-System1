# 현재 인수인계 — 2026-10-24 (Claude Code Main)

확인 시각: **2026-10-24 15:40 UTC / 2026-10-25 00:40 KST**. 이 시각 이후의 PR·Actions·게시 상태는 `git log`와 열린 PR로 다시 확인한다. 구현 / 시험 / 병합 / 게시 / 실사이트 확인을 나눠 적는다.

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
| #398 `claude/frontend-v2-p1-decisions` P1 결정 반영·결정 기록 | Claude Code Main | 2026-10-24 06:00 / 15:00 | DC-18 기기 시세 저장 중단, 한 클릭 한 동작, 백업 /5(옛 검증기 재사용), 판정 '기록 안 됨', 10/24 결정 기록. 필수 체크 녹색 뒤 병합 승인 요청 |
| #399 `claude/frontend-v2-p2-1-first-paint`(#398 위) P2-1a 첫 화면 구조 | Claude Code Main | 2026-10-24 06:00 / 15:00 | 셸 먼저, P1 층은 첫 그림 뒤 불러오기 + 성능 시험(느린 폰 조건 첫 화면 ≤2,000 ms·첫 전송 ≤100 KB). 측정 중앙값 848 ms / 24.4 KB(CI 837 ms). 녹색, #398 병합 뒤 기준 바꿔 동기화·병합 |
| #400 → #403 → #404(#393 위 사슬) 중앙 V PR-A·B·C | Claude Code Main | 2026-10-24 06:00 / 15:00 | U1~U3 정리(#400), 가드 U5(#403), 워크플로 U4·첫 게시 점검표(#404). 처음 연 #401·#402는 Gate A 이메일 검사가 옛 중간 커밋의 시험 URL을 계속 잡아 같은 트리의 새 브랜치(`-r2`)로 바꾸고 닫음. Secret 2개 등록 전에는 V 단계가 NOT_RUN이고 정기 실행은 성공해야 한다. 첫 게시 전 소유자 확인 CV-LEAK·CV-SPLIT(·CV-CARRY). 첫 게시 목표 11-04 전 |
| #405 `claude/central-v-reader`(#404 위) 중앙 V PR-D 옛 화면 작은 판독기 | Claude Code Main | 2026-10-24 10:40 / 19:40 | D8 (b): TARGET v1이 유효한 중앙 게시본이면 공식 V, 아니면 임시 V. 새 `qgv-official.js`(서버 검증기의 JS 쌍둥이), 클릭 때만 읽기. 새 프론트엔드 전환은 PR-D2(#398 뒤) |

## 1. 기준·게시

- canonical: **claude/investment-system-top500-validation-alrugm**, HEAD **fa0d9fcd** (#391 병합, 2026-10-24 06:58 UTC / 15:58 KST).
- 10/24 병합(모두 최신 canonical 위 필수 6체크 성공 확인 뒤, 소유자 승인):
  - #395 CI 실행기 `ubuntu-24.04` 고정: HEAD 67f2ca85 → 병합 **d6eaaa8a** (00:09 UTC / 09:09 KST). `ubuntu-latest`가 26.04로 바뀌어 Playwright 1.58.2 설치가 실패했기 때문이다.
  - #394 명세 원문·방향 전환 대장·금지 표현 검사·START_HERE: HEAD b3d5a41c → 병합 **9159df0d** (01:09 UTC / 10:09 KST). 문서·검사만이라 화면 변화 없음.
  - #385 새 프론트엔드 P0(셸·디자인 부품·글꼴·개발 빌드): 동기화본 2d7aec84(공용 CI 목록 충돌은 두 시험 모두 유지, 4.5 메뉴 "나비효과") → 병합 **a359ae91**. `web_app/`은 배포되지 않는다.
  - #396 옛 화면 4.5 "나비효과"(가드 해시 2개 재고정)·DC-02 계획·인수인계 → 병합 **d8fa097b** (05:44 UTC).
  - #397 새 프론트엔드 P1 자료·계산 층(옛 모듈 57개 재사용, 새 시험 5개 CI 등록) → 병합 **f3cee500** (06:26 UTC). 오늘 정기 실행 verify부터 P1 시험이 돈다. 실패하면 시험을 건너뛰지 않고 원인부터 보고한다(사용자 지시).
  - #391 TARGET v1 "임시 V"·F1(첫 확정본 날짜 기준, 사용자 결정)·F2 → 병합 **fa0d9fcd** (06:58 UTC).
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

- 연속 성공: **2/7** (10/23). 예약 22:17 UTC 실행이 나흘 연속 2시간 20분 안팎 늦게 시작했다(00:36·00:40·00:37·00:38 UTC). 확인은 01:30 UTC 무렵을 기본으로 한다.
- 10/23 게시 커버리지: Q 486 / G 494 / 양쪽 478, 분모 504, calc_version `qgv2-calc/2026-10-17.1`, 샤드 7/7, 7일 경과 행 0, as_of 2026-10-24 00:50 UTC.
- 부분 실패(배포는 막지 않음, 10/22와 같음): 8-K `ASML_6K_EARNINGS_UNCONFIRMED`(17개 중 1개), 뉴스 GDELT HTTP 429·IR 피드 실패로 PARTIAL_FAILED(항목 45), 로고 Wikidata 원천 불가로 이니셜 506. 원인 조사는 별도 작업.

## 3. TARGET v1 확정 조건 (확정 창 2026-11-09~11-15)

| 조건 | 상태 |
| --- | --- |
| 구현 #248·#263 | 병합·게시 |
| Q·G 각 454/504 이상 | 486 / 494 충족(10/23 게시본) |
| 10종목 숫자 대조(같은 calc_version) | **통과 기록**(10-23 #386, 앱 계산식 + 시험 가격, DC-16), `qgv2-calc/2026-10-17.1`. #393이 calc_version을 올리면 재대조 필요 → [계획 5절](implementation/docs/qgv_scoring_standard/CENTRAL_V_DC02_PLAN_20261024.md) |
| V 출처 | 중앙 V 미게시 → "임시 V"(#391 병합, 다음 배포에 반영). 중앙 V가 11-04 전에 게시되면 옛 화면 작은 판독기(D8 (b), PR-D)로 중앙 V |
| 실제 사용자 카드 응답 | 미시작 |

## 4. 열린 PR (10-24 15:40 UTC)

| PR | 상태 | 남은 것 |
| --- | --- | --- |
| #398 P1 결정 반영·결정 기록(DC-18) | 소유자 승인 대기 | 새 결정 대기 MANUAL-QUOTE(손으로 넣는 시세 위치, P2-6 전), 중앙 V CV-LEAK·CV-SPLIT·CV-CARRY |
| #399 P2-1a 첫 화면 구조(#398 위) | 녹색, 소유자 승인 대기 | #398 병합 뒤 기준을 canonical로 바꾸고 동기화·CI·병합 |
| #400·#403·#404 중앙 V PR-A·B·C(#393 위 사슬) | 모두 녹색, 소유자 승인 대기 | Secret 2개 등록, CV-LEAK·CV-SPLIT 결정, #393과 같은 날 병합(첫 게시 점검표) |
| #405 중앙 V PR-D(#404 위) | CI 중, 소유자 승인 대기 | 소유자 확인 CV-D-FRESH·CV-D-BUTTON·CV-D-ROWS·CV-D-CHURN(문구·V3/V4는 첫 게시 뒤 확인). 확정이 실제로 되려면 계획 5절 재기록 PR과 all_shards 1회가 먼저 |
| #392 TARGET v0 결합 해소 | 소유자 승인 대기. CI는 #395 전 | 기기 저장 키를 발행사 키로 이전. 후속 결정 7개를 USER_DECISIONS_PENDING으로 옮겨야 함. 가드 148·149행 붙은 줄 충돌(두 해시 유지로 해결) |
| #393 F_k·calc_version 23.1 | D1 (ii): 중앙 V 첫 게시와 같은 배포 창에 병합. 10-24 canonical 동기화, #397 시험의 벡터 수 고정(100 → 115) 수정, WSM 가격 판정 문구 삭제(c99c7471) | 병합 뒤 전체 샤드 실행·숫자 재대조(계획 5절, #391 병합됐으므로 재기록 PR 가능) |
| #361 Worker 분할 이벤트 | 배포 보류(Yahoo 권리 미해결) | 무료 대안 공급원 결정 |
| #305·#281(draft, 참고) · #267(보류) | 그대로 | — |

- 중앙 V 원본 브랜치 `claude/cv-core-publisher`는 #400으로 흡수됐다. `claude/iex-v4-backfill`(U8 1회 실행 완료)·`claude/iex-hist-probe`(PASS)는 기록 보존.
- `claude/fe2-*` 4개는 P0 커밋만 있는 빈 레인이다.

## 5. 다음 할 일

1. 10/24분 정기 실행 확인(연속 3/7 여부, 01:30 UTC 무렵). P1 시험이 verify에서 처음 돈다.
2. #398 녹색 → 병합 승인 → 병합. 이어서 P2-1a PR → 화면 P2 메뉴별(기능 1 → 2 → 6 → 5 → 3 → 4 → 7 → 8 → 9).
3. 중앙 V: 사용자 Secret 2개 등록(폰 절차 전달함) + CV-LEAK·CV-SPLIT 결정 → #400·#403·#404 승인 → #393과 같은 날 병합 → 전체 샤드 실행 → 첫 게시(목표 11-04 전, 넘기면 D1 (iii) 제안) → 숫자 재대조 → 옛 화면 판독기(PR-D).
4. 결정 대기: D5-UPDATE(월말가 월 1회 별도 실행 대안), MANUAL-QUOTE.
5. #392 승인 시 기준 병합 → CI → 병합. 8-K·뉴스·로고 부분 실패 원인 조사.

## 6. 유지할 경계

- 원시 가격·EV·수익률·배율·내재 성장률·보유·거래·시트 ID·토큰·환율 값을 저장소·Pages·Actions 로그에 넣지 않는다. 공식 V 점수·순위는 2026-10-23 결정(GSQ-024)으로 IEX HIST 기반 서버 계산 후 공개한다(아직 구현 안 됨). NA를 0으로 채우지 않는다.
- force push·ruleset·AUTONOMY_MODE(READ_ONLY) 변경 금지. 가드 비활성화·검사 생략·보호 대상 축소 금지. 권한 검사가 거부하면 우회하지 않고 보고한다.
- Frozen 자료·전진검증 원장 보존. Holdout 사용 권한 확대 없음.
- 다른 작업자의 worktree·scratchpad·원자료를 지우지 않는다.
