# 현재 인수인계 — 2026-10-24 (Claude Code Main)

확인 시각: **2026-10-24 01:40 UTC / 10:40 KST**. 이 시각 이후의 PR·Actions·게시 상태는 `git log`와 열린 PR로 다시 확인한다. 구현 / 시험 / 병합 / 게시 / 실사이트 확인을 나눠 적는다.

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
| #385 `claude/frontend-v2-p0` 새 프론트엔드 P0 | Claude Code Main | 2026-10-24 01:15 / 10:15 | 사용자 승인(동기화·병합). canonical 9159df0d 동기화본 2d7aec84(충돌 `ci_browser_tests.txt` 한 줄은 두 시험 모두 유지, 4.5 메뉴 이름 "나비효과"). 필수 체크 통과 뒤 병합 |
| `claude/frontend-v2-p1`(#385 위) 새 프론트엔드 P1 자료·계산 층 | Claude Code Main | 2026-10-24 00:15 / 09:15 | 공개 파일 엄격 리더·QGV v2 점수 접근자(V 출처 OFFICIAL_CENTRAL/DEVICE_TEMPORARY)·가격(클릭할 때만)·기기 저장·엔진 연결. 옛 모듈 재사용 |
| #396 `ccr-263267c9-f5ng5h` 4.5 "나비효과"·DC-02 계획·인수인계 | Claude Code Main | 2026-10-24 00:00 / 09:00 | 옛 화면 문구 + 가드 해시 2개 재고정, [중앙 V 구현 계획](implementation/docs/qgv_scoring_standard/CENTRAL_V_DC02_PLAN_20261024.md), 이 파일. 소유자 승인 대기 |

## 1. 기준·게시

- canonical: **claude/investment-system-top500-validation-alrugm**, HEAD **9159df0d** (#394 병합, 2026-10-24 01:09 UTC / 10:09 KST).
- 10/24 병합(모두 최신 canonical 위 필수 6체크 성공 확인 뒤, 소유자 승인):
  - #395 CI 실행기 `ubuntu-24.04` 고정: HEAD 67f2ca85 → 병합 **d6eaaa8a** (00:09 UTC / 09:09 KST). `ubuntu-latest`가 26.04로 바뀌어 Playwright 1.58.2 설치가 실패했기 때문이다.
  - #394 명세 원문·방향 전환 대장·금지 표현 검사·START_HERE: HEAD b3d5a41c → 병합 **9159df0d** (01:09 UTC / 10:09 KST). 문서·검사만이라 화면 변화 없음.
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
| V 출처 | 중앙 V 미게시 → "임시 V"(#391 승인 대기). 중앙 V가 11-04 전에 게시되면 중앙 V |
| 실제 사용자 카드 응답 | 미시작 |

## 4. 열린 PR (10-24 01:40 UTC)

| PR | 상태 | 남은 것 |
| --- | --- | --- |
| #385 새 프론트엔드 P0 | 승인됨. 동기화 2d7aec84 CI 중 | 필수 체크 통과 → 병합 |
| #391 TARGET v1 "임시 V"·F1·F2 | 소유자 승인 대기. CI는 #395 전(병합 전에 기준 병합·재실행 필요) | F1 판정 기준: 지금은 마지막 저장본 날짜. 제때 확정 뒤 마감 다음 날 다시 저장하면 11월 목록이 사라진다. **첫 확정본 날짜로 바꾸기를 권장** |
| #392 TARGET v0 결합 해소 | 소유자 승인 대기. CI는 #395 전 | 기기 저장 키를 발행사 키로 이전. PR 본문에만 있는 후속 결정 7개를 USER_DECISIONS_PENDING으로 옮겨야 함. #396과 가드 148·149행 붙은 줄 충돌(두 해시 유지로 해결) |
| #393 F_k·calc_version 23.1 | 소유자 승인 대기 | 병합 시점 = 결정 D1(권장: 중앙 V 첫 게시와 같은 배포 창). 병합하면 숫자 재대조·전체 샤드 실행 필요 |
| #396 4.5 "나비효과"·DC-02 계획·인수인계 | 소유자 승인 대기 | 가드 해시 2개 재고정 포함 |
| #361 Worker 분할 이벤트 | 배포 보류(Yahoo 권리 미해결) | 무료 대안 공급원 결정 |
| #305·#281(draft, 참고) · #267(보류) | 그대로 | — |

- **PR 없는 미병합 브랜치(중앙 V):** `claude/cv-core-publisher`(U1~U3 코드, #393과 합치면 시험 3개 실패), `claude/iex-v4-backfill`(U8 월말가 1회 수집 실행 완료 → 비공개 저장소), `claude/iex-hist-probe`(Actions 실현 가능성 PASS). 정리 순서는 계획 2절.
- `claude/fe2-*` 4개는 P0 커밋만 있는 빈 레인이다.

## 5. 다음 할 일

1. #385 필수 체크 통과 → 병합. P1 PR의 base를 canonical로 바꾼다.
2. 새 프론트엔드 P1 PR(자료·계산 층)을 내고 CI·승인 요청. 그다음 P2 메뉴별 PR(기능 1 → 2 → 6 → 5 → 3 → 4 → 7 → 8 → 9).
3. #396 승인 → 병합. 화면 반영은 다음 정기 실행 배포.
4. 중앙 V 결정 D1~D10 받기 → PR-A(U1~U3를 #393 위로 정리) → PR-B(가드) → PR-C(워크플로).
5. #391·#392 승인 시 기준 병합 → CI → 병합. 8-K·뉴스·로고 부분 실패 원인 조사.

## 6. 유지할 경계

- 원시 가격·EV·수익률·배율·내재 성장률·보유·거래·시트 ID·토큰·환율 값을 저장소·Pages·Actions 로그에 넣지 않는다. 공식 V 점수·순위는 2026-10-23 결정(GSQ-024)으로 IEX HIST 기반 서버 계산 후 공개한다(아직 구현 안 됨). NA를 0으로 채우지 않는다.
- force push·ruleset·AUTONOMY_MODE(READ_ONLY) 변경 금지. 가드 비활성화·검사 생략·보호 대상 축소 금지. 권한 검사가 거부하면 우회하지 않고 보고한다.
- Frozen 자료·전진검증 원장 보존. Holdout 사용 권한 확대 없음.
- 다른 작업자의 worktree·scratchpad·원자료를 지우지 않는다.
