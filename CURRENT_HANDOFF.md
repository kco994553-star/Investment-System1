# 현재 인수인계 — 2026-11-01

기준 **2026-11-01 07:10 UTC GitHub 조회**, canonical **`9a4e249d`**(#447). 앞 판(`1465260e`, #446) 뒤 병합은 아래 11/01 다섯 건뿐이다(첫 부모 이력으로 확인). 10/31 저녁 오너 승인으로 병합: #448 `ef0e90cb`(Worker 배포 run 41252518944) → #438 `f8e9a4ef` → #440 `edb11b1c` → #442 `70d0e447` → #441 `37b7ddc4` → #445 `1c73cb9b` → #450 `c33ec071` → #446 `1465260e`. 11/01 병합: #436 `c86be9b9` → #449 `111f86c7` → #451 `d8fe9bc8` → #453 `428b417e` → #447 `9a4e249d`(워크플로 ① `private-boundary-push.yml` 포함). 실제 기본 브랜치는 **`claude/investment-system-top500-validation-alrugm`**.

읽기: [START_HERE](START_HERE.md) → [방향 전환 대장](docs/SPEC/DIRECTION_CHANGES.md) → [WORKING_RULES](WORKING_RULES.md) → [기능 현황](docs/SPEC/FUNCTION_STATUS.md) → [결정 원문](implementation/docs/USER_DECISIONS_PENDING.md). 11/01 이행은 오너 결정 네 묶음(DC-40 두 흐름·연구 인계 / 11/01 2차 15항목 / 보완 지시: NAV 정정·점수화 모집단 검토, DC-41 / **역할 확대·계산·자료 구현 인계, DC-42**)이다. 원문은 결정 기록 2026-11-01 블록.

## 0. 역할·지금 관리할 흐름

역할은 **DC-42(11/01 3차, 역할 확대 — DC-40의 "Main 엔진·입력 / Codex 실행·대사" 분담을 대체)**: **Main**은 기능 계층 1~9의 모든 프론트엔드·UI/UX·차트·화면 연결(9 Lab 화면 포함), 인증·권한·Secret·워크플로·운영 인프라·공용 가드, 결정 기록·DC 번호·최종 통합, 승인 범위의 병합·배포. **Codex**는 계산·데이터·연구 구현(수집·변환 로직, PIT·증권 신원·입력 연결, 백테스트·전진검증 계산·결과 산출, 책 조사·규칙표·연구 문서, Notion. 인수한 공통 계산 모듈은 직접 수정). 역할은 오너가 확정했다(두 메시지, 재승인 대기 없음). #454 엔진·입력 어댑터 [#464](https://github.com/kco994553-star/Investment-System1/pull/464)·#459/#460의 수집·변환·진단 코드는 [#437 인계 3](https://github.com/kco994553-star/Investment-System1/pull/437#issuecomment-6557255668)로 Codex에 넘겼다(11/01 11:19 UTC). 넘긴 파일은 Main이 병행 수정하지 않는다. 파일 담당표·공통 파일 규칙: [START_HERE 4절·4.1절](START_HERE.md). Codex PR이 DC 번호·결정 기록을 직접 바꾸면 Main이 번호를 다시 매겨 반영한다. Codex PR은 Main이 canonical 동기화·CI 녹색·담당 파일만 바뀜을 확인하고 오너 승인 뒤 병합한다. 이 역할 변경은 병합·배포·SEC/Alpaca 실행 승인이 아니다. 이전 분담(DC-40) 원문은 [방향 전환 대장](docs/SPEC/DIRECTION_CHANGES.md)에만 남고 현행 규칙이 아니다. **AUD-01**(레거시 플레이북 `target_v1.grades` GENERAL 4~5% ↔ 승인된 일반 6%)은 인계 3으로 Codex에 넘겼다(설정 수정 Codex, 생성 사본·가드 고정값·화면 영향 Main).

| 흐름 / 기능번호 | Main 이행 | 현재 상태 |
| --- | --- | --- |
| **1 기기 V 폐지 / 2·6** (Main 순서 1) | DC-31: 화면은 중앙 V만. PR-1a(새 앱 공식 V 판독기 + 점수 접근자 게시본 모드) → PR-1b(옛 화면 기기 V 제거, direction guard 규칙) → 11/16 TARGET 경로 PR | PR-1a #435 병합(`44cd0b43`) · PR-1b #439 병합(`5e16d3e6`). 남은 것: S06 대표 증권 후속 PR, 11/16 TARGET 경로 PR |
| **2 IEX 확장 구현 / 공통** (Main 순서 2) | 10/31 결정: PR 3개(① 파서·공개 경계 ② 워크플로 시험·월말가 채우기 ③ 공개 파일 한도), 거래대금 기준 제외, 확장분 정밀값·공개는 승격 뒤 | 기기 V PR 뒤 시작 |
| **3 V가 필요한 화면** (Main 순서 3) | 2.2, 2.4·레이더, 6 | 대기 |
| 가격 표시 | "가격은 클릭할 때만" 폐지 제안(GSQ-026·DC-33, 공개 IEX 마지막 체결가) | #433, 오너 승인 대기 |

### 작업 중

근거 표시: **(조회)** = 07:10 UTC GitHub 직접 조회, **(실행)** = Main이 이 세션에서 직접 실행, **(PR 보고)** = PR 본문·댓글의 보고(재실행 안 함).

| PR·작업 | 담당 | 시작 (UTC) | 상태·다음 |
| --- | --- | --- | --- |
| [#456](https://github.com/kco994553-star/Investment-System1/pull/456) 중앙 V 기준일: IEX 목록의 비거래일 파일 건너뛰기 | Main | 11/01 03:10 | CI 9개 중 7 성공·2 생략(조회, 생략은 PR에서 원래 도는 일 없는 deploy·replay_source). 전체 시험 통과(실행). **병합은 오너 승인 뒤**. 병합 전까지 야간 중앙 V는 같은 이유로 `KEPT_LAST_GOOD` **11/01 재확인(조회):** 머리 `a922d6eb` 그대로, base `9a4e249d` 최신, 파일 3개, calc_version 그대로, 공개 JSON 스키마 그대로(`engine.publisher_sha256` 값만 바뀜, 검사는 16진수 형식만), Pages 가드 고정 파일 변경 없음. CI 7 성공·2 생략(deploy·replay_source는 PR에서 원래 생략). 병합 뒤 확인: 워크플로 성공 / `attempt_state` / 실제 거래 기준일 / 게시본 갱신을 따로 |
| [#457](https://github.com/kco994553-star/Investment-System1/pull/457) 결정 기록 11/01 2차·보완, DC-41, 연구 설정 10절(이 문서도 여기서 갱신) | Main | 11/01 03:00 | CI 성공(조회). 오너 승인 뒤 병합. 결정 대기 `EXP-SCORING-POP`·`EXP-CALC-ALIGN` **DC-42 역할 확대**(정본 4개·START_HERE 4.1절 공통 파일 규칙)와 새 결정 대기 `EXP-T-OPEN-DEF`(체결가 시가의 뜻)도 이 PR |
| [#455](https://github.com/kco994553-star/Investment-System1/pull/455) 자료층 브라우저 시험 경합 고침(시험만) | Main | 11/01 03:15 | CI 성공(조회). 오너 검토 뒤 병합(11/01 결정 12) |
| [#454](https://github.com/kco994553-star/Investment-System1/pull/454) 연구 엔진 `EXP-STOCK-INDICATOR-DECILES-v1`(Draft) | Codex(11/01 11:19 인계 3. 그 전 Main) | 11/01 01:20 | 머리 `ec1fa06c` push(08:30 UTC 무렵). 전체 시험 Python 4,661·브라우저 101 통과, 합성 묶음 두 번 바이트 동일(실행). F1~F11 상태표·새 기대 해시를 [#437 인계 2](https://github.com/kco994553-star/Investment-System1/pull/437#issuecomment-6555502936)에 남김. **11/01 DC-42로 후속 구현은 Codex**([#437 인계 3](https://github.com/kco994553-star/Investment-System1/pull/437#issuecomment-6557255668)). Codex 재검증 [6555833317](https://github.com/kco994553-star/Investment-System1/pull/437#issuecomment-6555833317)(PR 보고: 280 passed+1 skipped, 21/21·5/5 동일, 기대값 75/0) |
| [#464](https://github.com/kco994553-star/Investment-System1/pull/464) 연구 엔진 입력 어댑터(Draft, base #454) | Codex(11/01 11:19 인계 3. 작성 Main) | 11/01 08:40 | `36d8e3f9`. 연구 시험 377 passed·전체 시험 Python 4,694·node·worker·저장소 가드·빌드·Pages 가드·브라우저 통과(실행). 지금 원천(SEC·IEX·Alpaca)만으로는 모든 발행사 UNKNOWN(상장 상태·증권 종류·분할 기준은 `attributes`로만). 후속 구현 Codex |
| [#460](https://github.com/kco994553-star/Investment-System1/pull/460) SEC 1회용 수집 계획(실행 안 함) | Codex 코드·문서 / Main 워크플로·Secret·실행(DC-42) | 11/01 07:25 | `63d4c2b7`, CI 성공(조회), 전체 시험 Python 4,610 passed(실행). 실행은 오너 승인 뒤(열린 질문 Q1~Q7). 측정 가지 코드 이관 포함 파일별 담당은 PR 본문 표. 실행은 여전히 오너 승인 뒤 |
| [#459](https://github.com/kco994553-star/Investment-System1/pull/459) Alpaca 소표본 1회 측정 도구(Draft, 병합 안 함) | Codex 코드·문서 / Main 워크플로·Secret·실행(DC-42) | 11/01 07:20 | `7ab5cd4d` push, 전체 시험 Python 4,458 passed(실행). **실행 전**. 실행 전 오너 확인: 공개 로그에 범위·개수 줄만 남기는 것, Alpaca Secret 존재 파일별 담당은 PR 본문 표. 실행은 여전히 오너 확인 뒤 |
| [#452](https://github.com/kco994553-star/Investment-System1/pull/452) 책 규칙 인수·종목 비교 경계·동결 French 보유기간 분석(Draft) | Codex | 11/01 01:04 | 연구 경로 새 3파일, CI 성공(조회). Main 요청 4개(담당표 두 흐름 갱신 = #453 반영됨, 인계, LOSS 구분, #443 대체 범위) |
| [#437](https://github.com/kco994553-star/Investment-System1/pull/437) Lab 계약·EXP 연구 대사 창구(Draft, base #432) | Codex | 10/31 | Codex가 `78ac5c3e` 합성 묶음 재현(19/19 바이트 일치, 대사 28 일치·알려진 3 불일치, PR 보고). 다음: Main 인계 2 수령 뒤 재검증 |
| [#417](https://github.com/kco994553-star/Investment-System1/pull/417) QGV 장기 백테스트(Draft) | Codex | 10/26 | 11/01 `c68af2c0`로 의존성 코드 보존(PR 보고 204 passed). mergeable `unstable`(조회). calc 17.1 보존본, Main 엔진 아님 |
| [#458](https://github.com/kco994553-star/Investment-System1/pull/458) AI 탐색 범위 정리 `AGENTS.md`(Draft, 문서만) | GPT 문서 정리 세션(PR 본문 등록) | 11/01 07:18 | mergeable `unstable`(조회). Main 검토용. DC-40상 흐름은 Main·Codex 둘이라 담당 정리는 오너 확인 필요 |
| [#443](https://github.com/kco994553-star/Investment-System1/pull/443) 전진검증 v3 책 규칙표(Draft) | Codex(옛 GPT Work) | 10/31 | #452: 대체된 시행 초안은 되살리지 않고 원문 대기 부분만 Codex가 이어받음 |

## 1. 10/31 오너 결정과 처리

| 결정 | 처리 |
| --- | --- |
| #428 병합(정기 실행 전) | 00:18 병합(`61709bb7`). 10/30분 정기 #31부터 PSKY 공식 V 보류 |
| PSKY 주식수 파일 STALE | 주식수 경로 별칭 PR 없음. 지금 만들면 인수 전 주식수로 시총이 "새로 수집됨"이 되어 만들지 않음(오너에게 즉시 보고). 10/31 03:13 UTC부터 PSKY M3 시가총액 순위만 사유 있는 NA(`STALE_INPUT`). 3분기 10-Q 뒤 별칭 + 주식수 사건 규칙 PR 제안(`PSKY-SHARES-ALIAS`) |
| #429 → #431 병합 | #429 01:10(`b10b841a`), #431 02:24(`32cc3ffd`). #430은 #417 담당 확인 뒤 |
| 비공개 구역·유료 공급처 | 불필요로 기록(#431, GSQ-025 보충은 이 PR). **같은 날 뒤 결정으로 비공개 구역은 "1인 비공개 구역 신설(KIS 한정)"로 바뀜**(#436). 유료 공급처 V·유료 공급처 비교는 계속 하지 않음 |
| 확장 결정 | `IEX-EXP-ADV` 기준 제외, `IEX-EXP-BUILD` PR 3개, `IEX-EXP-FORMAT` 정밀값·승격 뒤 공개(#431) |
| 기기 V 폐지 | DC-31(#431). PR-1a [#435](https://github.com/kco994553-star/Investment-System1/pull/435) **병합**(`44cd0b43`, 새 앱 공식 V 판독기). PR-1b [#439](https://github.com/kco994553-star/Investment-System1/pull/439) **병합**(`5e16d3e6`, 10/31 오너 승인, 옛 화면은 중앙 V만). S06 같은 발행사 두 번째 주식 종류(GOOG) 표시는 후속 PR(오너 원칙 "시총은 발행사 단위, 점수는 대표 증권 하나"). TARGET 경로는 11/16 PR |
| 병렬 진행 체계 | DC-32·WORKING_RULES·START_HERE 담당표(이 PR) |
| #426 | 필요한 원칙만 #431로 옮기고 닫음 |
| 측정용 가지 | 오너가 지움(세션 삭제 권한 없음). 11/01 추가: `claude/fv3-pit-ticker-measure`(워크플로 ② 측정 끝남, [run 41255597310](https://github.com/kco994553-star/Investment-System1/actions/runs/41255597310): `dei:TradingSymbol` 48%, 파일 이름 앞부분 100%, 둘이 같음 92% — 설계 12절) |
| 사용량 | 독립 검토는 계산·워크플로 변경에만 1개, 전체 시험은 push 전 1회, 보고는 하루 1회 |
| 가격 표시 | #433 GSQ-026·DC-33 결정 기록(승인 대기) |
| KIS·1인 비공개 구역 | 인증 검증 1회([41165951277](https://github.com/kco994553-star/Investment-System1/actions/runs/41165951277))·IEX 대비 비교 1회([41169962364](https://github.com/kco994553-star/Investment-System1/actions/runs/41169962364)) 완료. 같은 날 "KIS 보류" 지시는 뒤 지시로 **취소**, **1인 비공개 구역 신설(KIS 한정)** 설계 문서 PR [#436](https://github.com/kco994553-star/Investment-System1/pull/436)(DC-34·GSQ-027 제안, 결정 대기 `PRIV-*` 7개, 구현은 승인 뒤). 결정 기록·방향 전환 줄·"비공개 구역 불필요" 기록 수정은 #436에 있다 |

## 2. 병합 (mergedAt UTC)

| PR | 내용 | UTC | merge SHA |
| --- | --- | --- | --- |
| [#447](https://github.com/kco994553-star/Investment-System1/pull/447) | 비공개 구역 1단계 가드·research-request/1, 워크플로 ① `private-boundary-push.yml` | 11-01 03:11:05 | `9a4e249d` |
| [#453](https://github.com/kco994553-star/Investment-System1/pull/453) | DC-40 두 흐름 + 연구 `EXP-STOCK-INDICATOR-DECILES-v1` 설정·인계 계약 | 11-01 02:21:19 | `428b417e` |
| [#451](https://github.com/kco994553-star/Investment-System1/pull/451) | 10/31 저녁 결정(FV3-TR·PIT-TICKER·FV3-SIZE·443 대조, DC-39) | 11-01 02:09:52 | `d8fe9bc8` |
| [#449](https://github.com/kco994553-star/Investment-System1/pull/449) | 마지막 체결 시각 ① 판독기·검증기(게시 쪽은 다음 PR) | 11-01 01:22:55 | `111f86c7` |
| [#436](https://github.com/kco994553-star/Investment-System1/pull/436) | 1인 비공개 구역(KIS 한정) 설계 | 11-01 00:37:41 | `c86be9b9` |
| [#446](https://github.com/kco994553-star/Investment-System1/pull/446) · [#450](https://github.com/kco994553-star/Investment-System1/pull/450) · [#445](https://github.com/kco994553-star/Investment-System1/pull/445) · [#441](https://github.com/kco994553-star/Investment-System1/pull/441) · [#442](https://github.com/kco994553-star/Investment-System1/pull/442) · [#440](https://github.com/kco994553-star/Investment-System1/pull/440) · [#438](https://github.com/kco994553-star/Investment-System1/pull/438) · [#448](https://github.com/kco994553-star/Investment-System1/pull/448) | 10/31 저녁 오너 승인 병합(머리말 순서) | 10-31 23:25~23:29 | 머리말 |
| [#439](https://github.com/kco994553-star/Investment-System1/pull/439) | 기기 V 폐지 1b | 10-31 09:11:55 | `5e16d3e6` |
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

## 3. 열린 PR·승인 (07:10 UTC 조회 17개 + 그 뒤 #458·#459)

| PR | 요지 | 상태(조회) | 오너 승인·조건 |
| --- | --- | --- | --- |
| [#457](https://github.com/kco994553-star/Investment-System1/pull/457) · [#456](https://github.com/kco994553-star/Investment-System1/pull/456) · [#455](https://github.com/kco994553-star/Investment-System1/pull/455) · [#454](https://github.com/kco994553-star/Investment-System1/pull/454) | Main 11/01 PR(위 작업 중 표) | #454 Draft, 나머지 CI 성공 | 각각 오너 승인 뒤 |
| [#433](https://github.com/kco994553-star/Investment-System1/pull/433) | GSQ-026·DC-33 가격 표시 결정 기록 | **DIRTY**(base `32cc3ffd`, 그 뒤 대장·결정 기록이 바뀜) | 결정 승인 필요. 승인 나면 Main이 canonical과 합친 뒤 병합 |
| [#458](https://github.com/kco994553-star/Investment-System1/pull/458) | AI 탐색 범위 정리(문서) | Draft·`unstable` | Main 검토 뒤 오너 승인 |
| [#459](https://github.com/kco994553-star/Investment-System1/pull/459) | Alpaca 소표본 도구(Main) | Draft | 병합 안 함. 실행은 오너 확인 뒤 1회 |
| [#452](https://github.com/kco994553-star/Investment-System1/pull/452) · [#437](https://github.com/kco994553-star/Investment-System1/pull/437) · [#432](https://github.com/kco994553-star/Investment-System1/pull/432) · [#443](https://github.com/kco994553-star/Investment-System1/pull/443) · [#418](https://github.com/kco994553-star/Investment-System1/pull/418) · [#417](https://github.com/kco994553-star/Investment-System1/pull/417) · [#416](https://github.com/kco994553-star/Investment-System1/pull/416) | Codex 연구·문서 PR | #417 `unstable`, 나머지 clean·Draft(#416 Open) | 연구 가지. 병합 전 Main 확인(담당 파일·CI·자료 권리) + 오너 승인 |
| [#430](https://github.com/kco994553-star/Investment-System1/pull/430) | #417 연구 명세 재고정(base = #417 가지) | Open | #417 담당 확인 뒤 |
| [#392](https://github.com/kco994553-star/Investment-System1/pull/392) | TARGET v0 결합 해소 | `unknown`(10/24 이후 갱신 없음) | 통합 검증·최종 승인 별도 |
| #305 · #281 · #267 | 옛 시안·스튜디오 | draft·보류 | 참고 |

닫음: #361(10-31 09:16, 병합 안 함 — TA-361), #444(#445가 대체), #434(#438이 대체), #426. 조회 범위: repo ruleset HG-02 — PR 필수, 리뷰 승인 수 0, 필수 check `repository-guard`. GitHub 리뷰 0과 오너 승인(대화·결정 기록)은 별개다.

## 4. 실제 상태·게시 검증

| 대상 / 기능번호 | 상태 |
| --- | --- |
| 중앙 V / 2·6 | **10/31분 정기 #32(11-01 01:06→01:53, 워크플로 성공)에서 게시 시도는 `SUPPLY_FAILED`·`SUPPLY_BELOW_THRESHOLD`, 지난 정상본 유지(공개 기준일 2026-10-29)** — 공개 `qgv-official-status.json` 직접 확인(07:10 UTC). 원인: IEX가 토요일 파일 `20261031`을 올렸고 기준일 선택이 거래일인지 보지 않음 → #456. 그 전: 10/30분 정기 #31: 성공, `attempt_state OK`, 가격 기준일 2026-10-29, 새 게시본(02:31 배포). 행 523·순위 356·V 358. **PSKY V 보류 확인**(`price_status` `SPLIT_AFTER_SHARE_COUNT`, #428). 가격 상태: SUPPLIED 501·ADR 1·체결 없음 1·주식수 사건 1 |
| 화면의 V | 기기 V 폐지(DC-31, #435·#439 병합): 새 앱과 옛 화면( 리더보드·상세·레이더·V 산출 현황·Universe 페이지·S13 비교·플레이북)은 중앙 V(`qgv-official.json`)만 보인다. 늦으면 마지막 중앙 V + 게시 시각 + STALE. TARGET v1 빌더만 11/16 PR까지 옛 V 출처 유지. 가치(DCF) 패널 제거. S06 GOOG 표시 차이는 후속 PR |
| 새 앱(`web_app/`) | 병합됨, 배포 안 됨(P3 전환 때). `qgv.js` 공식 판독기 채움(#435 병합) |
| `sec-universe-shares.json` PSKY 행 | 10/31 03:13 UTC STALE → PSKY M3 시가총액 순위만 사유 있는 NA. `sec-qgv2.json`·`sec-universe-qg.json` PSKY 행은 LIVE |
| IEX 확장 | 측정·설계·결정 완료(#431). 구현 없음 |
| 비공개 구역 / 2층 | 설계 #436·가드 #447 병합. Worker 수정 #448 병합·배포(run 41252518944, PR 보고). 로그인 /history 실기기 확인은 오너 폰 절차 전(미확인) |
| 마지막 체결 시각 | ① 판독기 #449 병합. ③ 게시 쪽 PR 미착수 |
| 연구 `EXP-STOCK-INDICATOR-DECILES-v1` | **합성 자료만**: 엔진 `78ac5c3e` 합성 묶음은 Main 재현(실행)·Codex 재현(PR 보고). 실자료 파일럿·전체 백테스트·실환경 검증은 **없음**(SEC 수집·T 시가 원천 승인 전). 합성 통과를 실자료 결과로 쓰지 않는다 |

## 5. 다음 우선순위 (11/01, DC-42 기준)

**Main**
1. **#456 병합 승인**(중앙 V 야간 실패 해소). 병합 뒤 다음 정기 실행에서 기준일·공급 비율 확인.
2. 계층 1~9 승인된 프론트엔드 잔여: P3 전환 조건([정리 11/01](implementation/docs/frontend_v2/P3_SWITCH_CONDITIONS_20261101.md) — 막는 것은 아직 없는 화면 6·2.2~2.4·세부 7개, 배포 빌드·가드 고정값, 옛 모듈 61개·PWA 방침), 포트폴리오 P2-6/#392, 계산 결과 → 화면 입력 계약(Codex에 스키마·상태값·예시 데이터 요청, 인계 3의 8절). 실자료 백테스트·회원 DB 완성은 선행 조건이 아니다.
3. 실행 기반: #459 공개 로그 범위·Secret 오너 확인 뒤 1회 실행, #460 Q1~Q7 답 뒤 실행(둘 다 실행 가지 push는 Main).
4. 결정 대기: `EXP-SCORING-POP`·`EXP-CALC-ALIGN` ②·`EXP-T-OPEN-DEF`(#457), #433 가격 표시, #455 시험 고침.
5. 기기 V 폐지 남은 것: 11/16 TARGET 경로 PR. TARGET v1 확정 창 11/09~11/15(V 출처 바꾸지 않음).
6. IEX 확장 구현 PR ①②③, 마지막 체결 시각 ③ 게시 쪽 PR — 위 순서 뒤.

**Codex**(인계 3): 실자료 차단 입력(역사 상장 상태·증권 종류·대표 증권·ADR 비율·다중 종류 주식 수·기업행사·SPY 분배금) 확보 경로 조사와 입력 연결, 첫 실자료 묶음, 엔진·어댑터 후속, 화면용 스키마·예시.

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
| SEC 10/31분 | [#32 / 41259677591](https://github.com/kco994553-star/Investment-System1/actions/runs/41259677591) | 11-01 01:06→01:53 | 워크플로 성공(조회). 중앙 V 게시 시도 `SUPPLY_FAILED`·`KEPT_LAST_GOOD`, 공개 기준일 10/29 유지(공개 상태 파일 확인). 원인 IEX 토요일 파일 → #456 |

## 7. 알려진 위험·관리자 노트

| 위험 | 영향·확인 |
| --- | --- |
| 중앙 V 야간 | #456 병합 전까지 매일 `KEPT_LAST_GOOD`(공개 V는 10/29 기준에 머묾). 화면은 마지막 중앙 V + STALE 표시 |
| 측정 가지 `claude/fv3-pit-ticker-measure` | 재현 코드는 아직 그 가지에만 있다. SEC 계획 PR(코드 이관 포함)이 올라간 뒤 오너가 지운다 |
| TARGET v1 확정 | 확정 창 11/09~11/15. V 출처는 그 기간 바꾸지 않는다(DC-31). 열린 항목: EME·CMG 새 10-Q 칸 원문 대조 |
| PSKY | ① 공식 V는 #428로 보류(새 10-K 주식수가 나오면 저절로 풀림) ② 주식수 파일 행 STALE(M3 순위만 NA) ③ Q·G는 인수 전 재무(FYE 2024-12-31) 기준 |
| 규칙 변경 PR과 라이브 게시본 | 엔진·가중치·설정 버전을 바꾸는 PR은 라이브 게시본을 무효로 만들 수 있다(점검표 7절). 버전 상수를 바꾸지 않는 PR(#428)은 해당 없음 |
| 기기 V 폐지 | #439 병합으로 라이브 옛 화면은 중앙 V만 보인다(기기 V·V 이력·가치 패널 없음). S06에서 GOOG가 QG 보기에 순서 없이 나와 QG 개수 12 · 게시본 11로 다르다 → 후속 PR |
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
