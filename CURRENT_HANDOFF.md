# 현재 인수인계 — 2026-10-31

기준 **2026-10-31 02:35 UTC / 11:35 KST**, canonical **`32cc3ffd`** (#431). 직전 판: 2026-10-30, `b10b841a`(#429). 실제 기본 브랜치는 **`claude/investment-system-top500-validation-alrugm`**이다(`origin/main` 없음). git log·PR·Actions·공개 파일을 대조했다. 이후 실행은 다시 조회한다.

읽기: [START_HERE](START_HERE.md) → [방향 전환 대장](docs/SPEC/DIRECTION_CHANGES.md) → [WORKING_RULES](WORKING_RULES.md) → [기능 현황](docs/SPEC/FUNCTION_STATUS.md) → [결정 원문](implementation/docs/USER_DECISIONS_PENDING.md). 오늘 이행은 오너 10/31 결정 두 묶음(병합·확장·기기 V 폐지 DC-31 / 병렬 진행 체계 DC-32·가격 표시 검토)이다.

## 0. 역할·지금 관리할 흐름

역할은 **DC-32(10/31)**: 병합·공용 파일·워크플로·`docs/SPEC`·인수인계·결정 문서는 Main만. 화면 세션(Frontend)은 [START_HERE 4절](START_HERE.md#4-파일-담당표-2026-10-31-dc-32) 담당 화면 파일만 바꾸고 Draft PR까지만. Codex는 연구 가지와 문서만. Frontend·Codex PR은 Main이 canonical 동기화·CI 녹색·담당 파일만 바뀜을 확인하고 오너 승인 뒤 병합한다.

| 흐름 / 기능번호 | Main 이행 | 현재 상태 |
| --- | --- | --- |
| **1 기기 V 폐지 / 2·6** (Main 순서 1) | DC-31: 화면은 중앙 V만. PR-1a(새 앱 공식 V 판독기 + 점수 접근자 게시본 모드) → PR-1b(옛 화면 기기 V 제거, direction guard 규칙) → 11/16 TARGET 경로 PR | PR-1a 구현·검토 중(`claude/device-v-abolition-1a`) |
| **2 IEX 확장 구현 / 공통** (Main 순서 2) | 10/31 결정: PR 3개(① 파서·공개 경계 ② 워크플로 시험·월말가 채우기 ③ 공개 파일 한도), 거래대금 기준 제외, 확장분 정밀값·공개는 승격 뒤 | 기기 V PR 뒤 시작 |
| **3 V가 필요한 화면** (Main 순서 3) | 2.2, 2.4·레이더, 6 | 대기 |
| 가격 표시 | "가격은 클릭할 때만" 폐지 제안(GSQ-026·DC-33, 공개 IEX 마지막 체결가) | #433, 오너 승인 대기 |

### 작업 중

| PR·작업 | 담당 | 시작 (UTC) |
| --- | --- | --- |
| 이 문서 PR(DC-35 개발 체계 Main + Codex·#434 대체·lab-backtest-v1 계약 기록) | Claude Code Main | 10/31 08:05 |
| 표 PR(공개 + 비공개 2층 구조 표·DC-36, `claude/public-private-two-layer-table`, 이 문서 PR 위) | Claude Code Main | 10/31 13:30 |
| 공통 기반 PR(기업 목록 공통 접근·Lab 판독기·비공개 기능 상태·`parts.privatePanel`, `claude/web-app-common-base`, base = canonical) | Claude Code Main | 10/31 08:10 |
| 묶음 1 PR(매크로·프롬프트·트리, `claude/web-app-bundle-1`, base = canonical, 표와 어긋난 곳 수정 뒤 PR) | Claude Code Main | 10/31 08:10 |
| #436 보강(차트 이력·Lab 결과 저장·조회 계약) | Claude Code Main | 10/31 08:10 |

## 1. 10/31 오너 결정과 처리

| 결정 | 처리 |
| --- | --- |
| #428 병합(정기 실행 전) | 00:18 병합(`61709bb7`). 10/30분 정기 #31부터 PSKY 공식 V 보류 |
| PSKY 주식수 파일 STALE | 주식수 경로 별칭 PR 없음. 지금 만들면 인수 전 주식수로 시총이 "새로 수집됨"이 되어 만들지 않음(오너에게 즉시 보고). 10/31 03:13 UTC부터 PSKY M3 시가총액 순위만 사유 있는 NA(`STALE_INPUT`). 3분기 10-Q 뒤 별칭 + 주식수 사건 규칙 PR 제안(`PSKY-SHARES-ALIAS`) |
| #429 → #431 병합 | #429 01:10(`b10b841a`), #431 02:24(`32cc3ffd`). #430은 #417 담당 확인 뒤 |
| 비공개 구역·유료 공급처 | 불필요로 기록(#431, GSQ-025 보충은 이 PR). **같은 날 뒤 결정으로 비공개 구역은 "1인 비공개 구역 신설(KIS 한정)"로 바뀜**(#436). 유료 공급처 V·유료 공급처 비교는 계속 하지 않음 |
| 확장 결정 | `IEX-EXP-ADV` 기준 제외, `IEX-EXP-BUILD` PR 3개, `IEX-EXP-FORMAT` 정밀값·승격 뒤 공개(#431) |
| 기기 V 폐지 | DC-31(#431). PR-1a [#435](https://github.com/kco994553-star/Investment-System1/pull/435) **병합**(`44cd0b43`, 새 앱 공식 V 판독기). PR-1b [#439](https://github.com/kco994553-star/Investment-System1/pull/439)(옛 화면, 전체 시험 통과, 승인 대기). TARGET 경로는 11/16 PR |
| 병렬 진행 체계 | DC-32·WORKING_RULES·START_HERE 담당표(이 PR) |
| #426 | 필요한 원칙만 #431로 옮기고 닫음 |
| 측정용 가지 | 오너가 지움(세션 삭제 권한 없음) |
| 사용량 | 독립 검토는 계산·워크플로 변경에만 1개, 전체 시험은 push 전 1회, 보고는 하루 1회 |
| 가격 표시 | #433 GSQ-026·DC-33 결정 기록(승인 대기) |
| KIS·1인 비공개 구역 | 인증 검증 1회([41165951277](https://github.com/kco994553-star/Investment-System1/actions/runs/41165951277))·IEX 대비 비교 1회([41169962364](https://github.com/kco994553-star/Investment-System1/actions/runs/41169962364)) 완료. 같은 날 "KIS 보류" 지시는 뒤 지시로 **취소**, **1인 비공개 구역 신설(KIS 한정)** 설계 문서 PR [#436](https://github.com/kco994553-star/Investment-System1/pull/436)(DC-34·GSQ-027 제안, 결정 대기 `PRIV-*` 7개, 구현은 승인 뒤). 결정 기록·방향 전환 줄·"비공개 구역 불필요" 기록 수정은 #436에 있다 |

## 2. 병합 (mergedAt UTC)

| PR | 내용 | UTC | merge SHA |
| --- | --- | --- | --- |
| [#435](https://github.com/kco994553-star/Investment-System1/pull/435) | 기기 V 폐지 1a: 새 앱 공식 V 판독기(`qgv.js` OFFICIAL_READER)·`qgv-scores.js` 게시본 모드, 자료층 브라우저 시험의 명시적 대기(DC-31, 새 앱 미배포) | 10-31 07:56:53 | `44cd0b43` |
| [#431](https://github.com/kco994553-star/Investment-System1/pull/431) | IEX 확장 측정·설계·결정, DC-30·DC-31, 10/30·10/31 결정 기록, #426 이관 | 10-31 02:24:04 | `32cc3ffd` |
| [#429](https://github.com/kco994553-star/Investment-System1/pull/429) | GSQ-025·DC-29 결정 기록 | 10-31 01:10:59 | `b10b841a` |
| [#428](https://github.com/kco994553-star/Investment-System1/pull/428) | PSKY 주식수 사건 뒤 공식 V 보류 | 10-31 00:18:42 | `61709bb7` |
| [#427](https://github.com/kco994553-star/Investment-System1/pull/427) | 공개 JSON 오너 이메일 두 곳 `[redacted]` | 10-30 12:32:43 | `b5409cb6` |
| [#422](https://github.com/kco994553-star/Investment-System1/pull/422) | Codex 확장 카탈로그 E0/E1-A | 10-30 12:10:32 | `1377e474` |
| [#424](https://github.com/kco994553-star/Investment-System1/pull/424) | TARGET v1 숫자 검증 재기록(23.1) | 10-30 12:02:34 | `96037d1c` |
| [#425](https://github.com/kco994553-star/Investment-System1/pull/425) | 10/29 인수인계 | 10-30 11:26:57 | `f1c28bac` |
| [#423](https://github.com/kco994553-star/Investment-System1/pull/423) | 확장 모집단 계획·DC-27·DC-28 | 10-30 11:26:33 | `5578e1d9` |

10/29 병합(중앙 V 첫 게시 사슬 #393·#400·#403·#404·#405, 화면 #421·#415·#419·#420, #411)은 git 이력과 [10/29판](https://github.com/kco994553-star/Investment-System1/blob/f1c28bac/CURRENT_HANDOFF.md)에 있다.

## 3. 열린 PR·승인

| PR | 요지 | 상태 | 오너 승인·조건 |
| --- | --- | --- | --- |
| 이 문서 PR | DC-35 개발 체계(Main + Codex)·결정 문서·lab-backtest-v1 계약, START_HERE 담당표, 오늘 인수인계·기능 현황, GSQ-025 보충(#434 커밋 포함) | CI 확인 | 문서 병합 승인 필요 |
| [#434](https://github.com/kco994553-star/Investment-System1/pull/434) | DC-32 병렬 진행 체계(시행 전 대체) | 대체 종료 | 이 PR이 대체(이력 보존) |
| [#436](https://github.com/kco994553-star/Investment-System1/pull/436) | 설계: 1인 비공개 구역(KIS 한정), DC-34·GSQ-027 제안, 오너 폰 설정 절차, KIS 문의 초안 | CI 확인 | **설계 승인 필요**(`PRIV-*` 7개). 구현은 승인 뒤 |
| [#439](https://github.com/kco994553-star/Investment-System1/pull/439) | 기기 V 폐지 1b: 옛 화면은 중앙 V만, 기기 V·V 이력·가치 패널 제거, direction guard DC-31a~d | CI 확인(#435 병합 뒤 canonical 위) | **병합 승인 필요** |
| [#433](https://github.com/kco994553-star/Investment-System1/pull/433) | GSQ-026·DC-33 가격 표시 결정 기록(공개 IEX 마지막 체결가, 클릭 전용 폐지 범위) | CI 확인 | **결정 승인 필요**. 구현은 승인 뒤 |
| [#432](https://github.com/kco994553-star/Investment-System1/pull/432) | Codex 연구 `[WIP]` BT-DATA-PILOT v0.6(Alpaca OHLCV·IEX 빈 응답) | Draft | DC-32 연구 가지. 병합 전 Main 확인(담당 파일·CI·자료 권리) + 오너 승인 |
| [#430](https://github.com/kco994553-star/Investment-System1/pull/430) | #417 연구 명세 재고정(`96037d1c`·23.1), base = #417 가지 | CI 6 녹색 | #417 담당 확인 뒤 병합 |
| [#418](https://github.com/kco994553-star/Investment-System1/pull/418) · [#417](https://github.com/kco994553-star/Investment-System1/pull/417) · [#416](https://github.com/kco994553-star/Investment-System1/pull/416) | 백테스트 연구·기준(연구 담당) | Draft·Open | DC-32상 Codex 연구 가지 |
| [#392](https://github.com/kco994553-star/Investment-System1/pull/392) | TARGET v0 결합 해소 | DIRTY | 통합 검증·최종 승인 별도 |
| [#361](https://github.com/kco994553-star/Investment-System1/pull/361) | Worker 분할 이벤트 | DIRTY | 공급원 권리로 보류 |
| #305 · #281 · #267 | 옛 시안·스튜디오 | draft·보류 | 참고 |

닫음: #426(10/31, 오너 결정 — DC-27 번호 중복, #431과 겹침). 조회 범위: repo ruleset HG-02 — PR 필수, 리뷰 승인 수 0, 필수 check `repository-guard`. GitHub 리뷰 0과 오너 승인(대화·결정 기록)은 별개다.

## 4. 실제 상태·게시 검증

| 대상 / 기능번호 | 상태 |
| --- | --- |
| 중앙 V / 2·6 | 매일 게시. 10/30분 정기 #31: 성공, `attempt_state OK`, 가격 기준일 2026-10-29, 새 게시본(02:31 배포). 행 523·순위 356·V 358. **PSKY V 보류 확인**(`price_status` `SPLIT_AFTER_SHARE_COUNT`, #428). 가격 상태: SUPPLIED 501·ADR 1·체결 없음 1·주식수 사건 1 |
| 화면의 V | 리더보드·상세·레이더 V축은 아직 옛 화면 기기 계산값이다. DC-31로 폐지 결정, PR-1a·1b가 공식 V로 바꾼다. 공식 V를 읽는 화면은 옛 TARGET 빌더뿐(11/16까지 그대로) |
| 새 앱(`web_app/`) | 병합됨, 배포 안 됨(P3 전환 때). PR-1a가 `qgv.js` 공식 판독기를 채운다 |
| `sec-universe-shares.json` PSKY 행 | 10/31 03:13 UTC STALE → PSKY M3 시가총액 순위만 사유 있는 NA. `sec-qgv2.json`·`sec-universe-qg.json` PSKY 행은 LIVE |
| IEX 확장 | 측정·설계·결정 완료(#431). 구현 없음 |

## 5. 다음 우선순위 (10/31 밤 DC-35 기준)

1. #435(PR-1a 공식 V 판독기, CI 녹색) 오너 승인 병합 → PR-1b(옛 화면 기기 V 제거) PR·CI → 승인 병합. TARGET 경로는 11/16 PR.
2. IEX 확장 구현 PR ①②③(각 계산·워크플로 변경, 독립 검토 1). #435와 함께 최우선.
3. 공통 기반 PR → 묶음 1(4 매크로·7 프롬프트·8 트리) → 묶음 2(3 기술적 분석·5 뉴스·9 Lab). 화면 PR은 자체 검토, 묶음 PR마다 보고 1회.
4. #436 설계 보강(차트 이력 MODP=0 장부·MODP=1 차트 계열, Lab 결과 비공개 저장·조회). 구현은 `PRIV-*` 승인 뒤.
5. 6. 포트폴리오: 독립 UI는 진행 가능, 공식 V에 의존하는 결론·선정은 #435 뒤.
6. 가격 표시: GSQ-026 승인 뒤 가드 → 게시기·워크플로 → 새 앱 자료 층.
7. TARGET v1 확정 창 11/09~11/15(V 출처 바꾸지 않음), 11/16 기기 V 경로 제거 PR.

## 6. 정기 실행·수동 실행

| 대상 / 관측분 | run 번호 / ID | UTC 시작→종료 | 결과 |
| --- | --- | --- | --- |
| SEC 10/22분 | [#21 / 39879258841](https://github.com/kco994553-star/Investment-System1/actions/runs/39879258841) | 10-23 00:37→01:20 | 성공 1/7 |
| SEC 10/23분 | [#22 / 40045938631](https://github.com/kco994553-star/Investment-System1/actions/runs/40045938631) | 10-24 00:38→01:17 | 성공 2/7 |
| SEC 10/24분 | [#23 / 40146210895](https://github.com/kco994553-star/Investment-System1/actions/runs/40146210895) | 10-25 00:19→01:06 | 성공 3/7 |
| ALLSHARDS-1026 | [#24 / 40186520528](https://github.com/kco994553-star/Investment-System1/actions/runs/40186520528) | 10-25 10:52→12:03 | 성공(수동, 집계 밖) |
| SEC 10/25분 | [#25 / 40248709458](https://github.com/kco994553-star/Investment-System1/actions/runs/40248709458) | 10-26 00:18→00:56 | 성공 4/7 |
| SEC 10/26분 | [#26 / 40432704648](https://github.com/kco994553-star/Investment-System1/actions/runs/40432704648) | 10-27 01:27→02:13 | 성공 5/7 |
| SEC 10/27분 | [#27 / 40614210081](https://github.com/kco994553-star/Investment-System1/actions/runs/40614210081) | 10-28 01:18→02:02 | 성공 6/7 |
| SEC 10/28분 | [#28 / 40802503489](https://github.com/kco994553-star/Investment-System1/actions/runs/40802503489) | 10-29 01:47→02:28 | 성공 **7/7** |
| **중앙 V 첫 게시 all_shards** | [#29 / 40871484448](https://github.com/kco994553-star/Investment-System1/actions/runs/40871484448) | 10-29 12:13→13:31 | **성공**(수동, `d149c91d`). collect 39분(샤드 28.7·V 단계 6), verify 35분, deploy 1분. `attempt=OK published=NEW basis=2026-10-28 rows=523 ranked=356 supplied=357/357` |
| SEC 10/29분 | [#30 / 40988690629](https://github.com/kco994553-star/Investment-System1/actions/runs/40988690629) | 10-30 01:55→02:54 | 성공(연속 8). collect 22분, verify 37분. `attempt_state OK`, 가격 기준일 2026-10-28, 새 게시본 |
| SEC 10/30분 | [#31 / 41155975780](https://github.com/kco994553-star/Investment-System1/actions/runs/41155975780) | 10-31 01:34→02:31 | 성공(연속 9). collect 20분, verify 36분, deploy 1분. `attempt_state OK`, 가격 기준일 2026-10-29, PSKY V 보류 |

## 7. 알려진 위험·관리자 노트

| 위험 | 영향·확인 |
| --- | --- |
| TARGET v1 확정 | 확정 창 11/09~11/15. V 출처는 그 기간 바꾸지 않는다(DC-31). 열린 항목: EME·CMG 새 10-Q 칸 원문 대조 |
| PSKY | ① 공식 V는 #428로 보류(새 10-K 주식수가 나오면 저절로 풀림) ② 주식수 파일 행 STALE(M3 순위만 NA) ③ Q·G는 인수 전 재무(FYE 2024-12-31) 기준 |
| 규칙 변경 PR과 라이브 게시본 | 엔진·가중치·설정 버전을 바꾸는 PR은 라이브 게시본을 무효로 만들 수 있다(점검표 7절). 버전 상수를 바꾸지 않는 PR(#428)은 해당 없음 |
| 기기 V 폐지 중 | PR-1a는 새 앱만 바꾼다(라이브 사이트 동작 같음). 라이브 화면은 PR-1b 병합 뒤 바뀐다 |
| 측정용 가지 | `claude/iex-expansion-measure-once`·`claude/kis-verify-once`: 세션 삭제 권한 없음(403). 오너가 지운다. 두 가지의 워크플로는 그 가지에 push할 때만 돈다. KIS 가지에 push하면 KIS 토큰이 발급되어 오너에게 카카오톡 알림이 간다 |
| telecom MIN_PEERS=8 경계 | 하나 빠지면 Q가 GENERAL `UNIVERSE_FALLBACK`. 매일 8 미만이면 즉시 보고 |
| verify 시간 | 35~37/60분 |

관리자 노트: 기능 구현 %·프론트엔드 %는 미산정. 문서·리뷰만으로 제품 진행률을 올리지 않는다.

## 8. 경계

- 모집단·V
  - Universe504 고정(DC-01). 확장 모집단은 별도 연구 모집단이다(DC-27).
  - 공식 V는 IEX HIST 서버 계산·공개(DC-02, 10-29 게시).
- 넣지 않는 것: 원시 가격·EV·배율·수익률·보유·Secret 값·키·토큰 값은 문서·로그·공개 산출물에 넣지 않는다. Secret은 이름(`QGV_OFFICIAL_HMAC_KEY`·`RAW_REPO_READ_TOKEN`)만 적는다.
- 지킬 것: NA를 0으로 채우지 않는다. 가격 요청은 버튼을 누를 때만 한다. Frozen·원장·SUPERSEDED·#412 이력은 보존한다.
- 임의로 바꾸지 않는 것: 계산·가중치·T-FRESH·공개 경계·보호규칙·AUTONOMY_MODE.
