# 현재 인수인계 — 2026-10-23 (Claude Code Main)

> **2026-10-24 정리(23:16 UTC 10/23 확인):** 아래 1~5절은 10/23 01:40 UTC 기준이라 그 뒤 병합(#384 #378 #382 #387 #389 #388 #386)이 빠져 있었다. 작업 중 표·3절·4절·5절의 낡은 줄만 고쳤다. 10/23 결정 요지는 [USER_DECISIONS_PENDING](implementation/docs/USER_DECISIONS_PENDING.md) "결정됨 — 2026-10-23".

확인 시각: **2026-10-23 01:40 UTC / 10:40 KST**. 이 시각 이후의 PR·Actions·게시 상태는 다시 확인한다. 구현 / 시험 / 병합 / 게시 / 실사이트 확인을 나눠 적는다.

먼저 읽기: **[START_HERE.md](START_HERE.md) → [방향 전환 대장](docs/SPEC/DIRECTION_CHANGES.md)** → [WORKING_RULES.md](WORKING_RULES.md) → 이 파일 → [사용자 결정](implementation/docs/USER_DECISIONS_PENDING.md) → [병렬 분담](implementation/docs/PARALLEL_LANES_20261020.md) → [제품 IA](implementation/docs/PRODUCT_IA_DIRECTIVE_20261018.md) → [자료 계약](implementation/docs/FRONTEND_DATA_CONTRACT.md).
이전 기록: [10/21 Codex Main 원문](implementation/docs/handoff/HANDOFF_HISTORY_20261021.md) · [10/20](implementation/docs/handoff/HANDOFF_HISTORY_20261020.md) · [10/18~19](implementation/docs/handoff/HANDOFF_HISTORY_20261018_19.md) · [복구 게시 증거](implementation/docs/handoff/RECOVERY_PUBLICATION_20261021.md) · [프런트엔드 연결](implementation/docs/handoff/FRONTEND_WIRING_20261021.md).

## 0. 역할 (2026-10-22 사용자 결정)

- **병합·공용 파일·이 파일 갱신은 Claude Code 하나가 맡는다.** 공용 파일은 가드 고정값(`pages_artifact_guard.py`), CI 목록, `app.js` 통합, 이 파일, `USER_DECISIONS_PENDING.md`다.
- **Codex는 검증·리뷰만 한다.** push·병합하지 않는다.
- 다른 쪽이 어떤 PR을 작업하려면 아래 "작업 중" 표에 **PR 번호·담당·시작 시각**을 먼저 적고, 끝나면 지운다. 표에 다른 담당이 있는 PR은 건드리지 않는다.

### 작업 중

| PR | 담당 | 시작 (UTC / KST) | 내용 |
| --- | --- | --- | --- |
| #394 `claude/spec-direction-register` 명세 원문·방향 전환 대장·시작 문서 | Claude Code | 2026-10-23 23:20 / 10-24 08:20 | 문서·검사만. 공용 파일은 이 파일과 USER_DECISIONS_PENDING 머리 부분만 고침 |

## 1. 기준·게시

- canonical: **claude/investment-system-top500-validation-alrugm**, HEAD **a4705807** (#381 병합, 2026-10-22 13:21 UTC / 22:21 KST).
- 10/22 병합(모두 최종 HEAD가 직전 canonical과 동기화된 상태에서 필수 6체크 성공 확인 뒤):
  - #248 TARGET v1 빌더: HEAD 87904cc6 → 병합 5691f7cd (08:54 UTC / 17:54 KST)
  - #263 TARGET v1 후속(확정 재검사·calc_version 숫자 검증·NA 제외·일정): HEAD eaa7df68(Codex 검증본 995b0103과 같은 파일 구성) → 병합 7e821375 (10:10 UTC / 19:10 KST)
  - #262 매크로 규칙 C(가설·UNCALIBRATED, gate_active=false 유지): HEAD c9889ce2(Codex 검증본 70a10767과 같은 파일 구성) → 병합 dcf489fc (10:50 UTC / 19:50 KST)
  - #373 인수인계(305691db), #374 매크로 4.1 근거 전체 목록(ecde3640), #377 매크로 메뉴 3 도장 배치(8966b854), #381 시안 대조 레인 6개 통합(a4705807: 2.1 SIC 필터 · 2.3 13F 흐름 · 2.4 레이더 비교군 · 6.1 폰 탭 · 9.1 준비 목록 · 9.2 운영 증거). 개별 #375·#376·#379·#380은 #381로 대체해 닫음.
- **실제 게시: a4705807**. 10/22 정기 실행 [run 39879258841](https://github.com/kco994553-star/Investment-System1/actions/runs/39879258841)이 collect·verify·deploy 모두 성공했다. 실제 시작 10/23 00:37 UTC / 09:37 KST(예정보다 2시간 20분 늦음), 배포 01:20 UTC / 10:20 KST. 실사이트에서 새 레이더·매크로 배치 자산을 확인했다. TARGET 확정은 `number_check_passed: false`로 계속 막혀 있다.

## 2. 정기 실행·연속 성공

| 관측일 | run | 결과 | 비고 |
| --- | --- | --- | --- |
| 10/19 | 39336213259 | 성공 | |
| 10/20 | 39522288311 | collect 성공 · **verify 실패** · deploy 건너뜀 | 원인: `macro_evidence_browser_test.js`가 실제 수집 파일에서도 미수집 배너를 기다림. **수정 #370(e967cbd3) 병합 확인**, 10/20 자료는 #371 복구 게시 |
| 10/21 | 39701051682 | 성공 | 원장 v1/v2 각 3건(10/19·10/20·10/21), 기존 보존. RAW 재사용(`source=RAW raw=FOUND`) |
| 10/22 | 39879258841 | **성공 · 연속 1회째** | 사용자 결정(10/22)으로 이 실행부터 센다. 원장 v1/v2 각 4건(10/19~10/22), 기존 3건 바이트 동일·10/22 1건 추가(`appended=1`). RAW 재사용(`source=RAW raw=FOUND recovered_records=0`), 비공개 업로드 `forward-ledger-2026-10-22` |

- 연속 성공: **1/7** (10/22). 예약 22:17 UTC 실행이 사흘 연속 2시간 20분 안팎 늦게 시작했다(00:36·00:40·00:37 UTC). 지연 점검(00:17 UTC)은 실행이 아직 없을 수 있으므로 01:30 UTC 재확인을 기본으로 한다.
- 10/22 게시 커버리지: Q 486 / G 494 / 양쪽 478, 분모 504, calc_version `qgv2-calc/2026-10-17.1`, 7일 경과 행 0, 샤드 4(76종목) 수집·이전 값 유지 2.
- 매크로 근거(P1) PARTIAL 그대로(지표 13·계열 14). 공식 국면·확률은 미산출 그대로다.
- 부분 실패(배포는 막지 않음, 기존 파일 유지): SEC 8-K 수집이 `ASML_6K_EARNINGS_UNCONFIRMED`로 출력 없이 끝남(게시 파일은 NOT_AVAILABLE·NO_ELIGIBLE_INPUT, 10/18·10/19 게시본도 같은 상태). 뉴스 GDELT HTTP 429·IR 피드 실패로 새로 고침 PARTIAL_FAILED(기존 36건 유지). 로고는 Wikidata 원천 불가로 이니셜 506. 원인 조사는 별도 작업.
- XOM·HONA는 NOT_AVAILABLE(`NO_ANNUAL_SEC_FINANCIALS`), XOM 주식수 COVER_UNCONFIRMED.

## 3. TARGET v1 확정 조건 (목표 2026-11 둘째 주)

| 조건 | 상태 |
| --- | --- |
| 구현 통합 #248 → #263 | 둘 다 병합·게시(10/22 정기 실행, a4705807) |
| Q·G 각 454/504 이상 | 486 / 494 충족(10/22 게시본) |
| 10종목 숫자 재대조(같은 calc_version) | **통과 기록(10-23 #386, 앱 계산식 + 시험 가격, DC-16).** `number_check.result.passed = true`, `qgv2-calc/2026-10-17.1`. #393이 calc_version을 올리면 재대조 필요. 아래는 10-23 01:40 UTC 시점 기록: |
| (이전) 10종목 숫자 재대조 | 원지표 40칸은 현재 게시본(`qgv2-calc/2026-10-17.1`, as_of 10/22 00:50 UTC)에서도 불일치 0. **기기 FCF 수익률 7칸(FIX·RL·MA·RSG·MNST·CMG·EXPE) 미검증** — 가격이 필요해 기기에서만 맞출 수 있다. [대조 문서 0-2-7절](implementation/docs/qgv_scoring_standard/QGV_V2_NUMBER_CHECK_20261017.md). `number_check.result`는 그대로 `passed: false` |
| 실제 사용자 카드 응답 | 미시작(#263 병합·게시 뒤) |

## 4. 열린 PR

- **#361** Worker 분할 이벤트: 배포 보류(Yahoo 권리 미해결). Yahoo 블록 누락은 "분할 정보 미확인". 무료 우선 대안 조사 결정 D1~D7 대기.
- #305·#281(draft, 참고 보존), #267(합성 스튜디오, 보류).
- (2026-10-24 정리) **#378·#382는 10-23 병합**(#384 tar 상한 8 MiB 승인·병합 뒤). 지금 열린 PR: #385 새 프론트엔드 P0(draft) · #390 Universe 지수 추종 설계(draft, **UNI-FOLLOW 결정 전 병합 안 함**) · #391 "임시 V" · #392 TARGET v0 결합 해소 · #393 V-PRICE-BASIS·calc_version 올림 — #391~#393은 소유자 승인 대기.
- (이전) **#378** 기술 메뉴 2 도장 배치: 최신 canonical 동기화(f7733799), 로컬 핵심 11개 통과. **CI 실패 원인 = tar 모드 가드 상한 `MAX_ARCHIVE_BYTES` 4 MiB**. canonical 빌드 tar가 4,177,920바이트(여유 약 16 KB)이고 #378이 약 +20 KB라 4,198,400바이트가 됨. tar 모드는 시험에서만 쓰이고 실제 배포 가드는 디렉터리 모드(파일당 2 MiB·192개). 상한 조정은 가드 완화라 **사용자 결정 대기**(권장: 8 MiB).
- **#382** 기술 3.3 노트 도구(draft, #378 위): 펜·수평선·지우개·되돌리기, 가져오기 중복 판정 결함 수정. 로컬 86/86. #378 뒤.

## 5. 다음 할 일

0. (2026-10-24 정리) 1번과 3번은 10-23에 끝났다(#384·#378·#382, #386). 4번은 `docs/SPEC/FUNCTION_HIERARCHY_v1.0.md`로 들어왔다. 지금 결정 대기: #391·#392·#393 승인, UNI-FOLLOW, CHAIN-NAME.
1. tar 상한 결정 → (승인 시) 상한 조정 PR → #378 → #382 순서로 병합.
2. 10/23 정기 실행 결과 확인(연속 2회째 여부, 01:30 UTC 무렵). 8-K·뉴스·로고 부분 실패 원인 조사.
3. 기기 FCF 수익률 7칸: 사용자 기기 절차(대조 문서 0-2-3)로 맞춘 뒤 `number_check.result`를 같은 calc_version으로 갱신하는 작은 커밋.
4. 기능 계층 명세 v1.0 1~9 본문을 받으면 저장소에 넣고 시안 대조표(추정 번호)를 확정.
5. #361 대안 공급원 결정 반영.

## 6. 유지할 경계

- 원시 가격·EV·수익률·배율·내재 성장률·보유·거래·시트 ID·토큰·환율 값을 저장소·Pages·Actions 로그에 넣지 않는다. 공식 V 점수·순위는 2026-10-23 결정(GSQ-024)으로 IEX HIST 기반 서버 계산 후 공개한다. NA를 0으로 채우지 않는다.
- force push·ruleset·AUTONOMY_MODE(READ_ONLY) 변경 금지. 가드 비활성화·검사 생략·보호 대상 축소 금지. 권한 검사가 거부하면 우회하지 않고 보고한다.
- Frozen 자료·전진검증 원장 보존. Holdout 사용 권한 확대 없음.
- 다른 작업자의 worktree·scratchpad·원자료를 지우지 않는다.
