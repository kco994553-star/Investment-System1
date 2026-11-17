# 열린 PR 분류·의존 순서 조사 — 2026-11-15

## 조사 기준과 해석

- GitHub 열린 PR 목록 두 페이지를 읽은 스냅샷: **102개, Draft 93개, 일반 PR 9개**. 이 문서를 제출할 PR은 집계에 포함하지 않는다. 마지막 갱신 시각은 GitHub `updated_at`, UTC이다.
- 기본 가지 코드·결정 기준: `4a3141b8fa1593e68552390c7ad4b1ea16b89d2f`. 열린 PR의 제목·본문·base/head 메타데이터를 읽었다. 오래됐거나 Draft라는 이유만으로 종료를 제안하지 않는다.
- **분류는 검토 제안이며 병합·종료 승인이 아니다.** 102개 고정 head의 로컬 Git 조상 관계와 base…head 변경 파일 목록을 추가 확인했다. 최신 머리 CI, mergeability, 후속 반영의 바이트 동등성을 모든 PR에서 확인한 것은 아니다. 아래 머리 SHA로 Main이 승인 직전에 다시 대조해야 한다.
- “병합 후보”는 현행 방향에 맞는 우선 검토 대상이다. “다른 PR로 대체됨”은 본문에 후속/대체가 명시된 경우만 쓴다. “엔진·계약만 가져올 것”은 순수 계산·판독·검증·자료 형식을 선별하며 과거 화면·운영 설정을 통째로 병합하지 않는다는 뜻이다.
- “담당”은 지금 후속 확인을 맡을 흐름이다. 본문의 인수 문구와 DC-42 파일 책임을 우선하고, 없으면 가지·업무로 추론했다. GitHub 작성자 계정으로 Main/Codex를 구분하지 않았다. 연구 문서 #416·#418·#443·#486은 DC-42와 #452의 연구 인수에 따라 현행 후속 담당을 Codex로 표시했다. 과거 최초 작성자를 확정하는 표는 아니다.
- #459·#460은 도구/연구 담당 Codex로 표시했지만 실행 구성·워크플로·병합은 Main이다. #454·#464는 본문 인수에 따라 Codex, #550은 본문 명시 Codex(운영 통합 Main)이다.
- PR 종료는 **오너 승인 후 Main**이 한다. 이 조사에서는 코드·가드·워크플로 수정, PR 종료·병합·재실행을 하지 않는다.

## 분류 요약

| 분류 | 수 |
| --- | ---: |
| 닫을 것 | 5 |
| 엔진·계약만 가져올 것 | 65 |
| 판단 필요 | 18 |
| 병합 후보 | 12 |
| 다른 PR로 대체됨 | 2 |

## 전체 목록

기준 가지 `canonical`은 아래의 정확한 기본 가지 별칭이다. 나머지는 실제 base ref를 그대로 적는다.
`canonical = claude/investment-system-top500-validation-alrugm`

| PR | 제목 | 기준 가지 | 마지막 갱신 UTC | 담당 | 분류 | 근거·후속 대조 |
| --- | --- | --- | --- | --- | --- | --- |
| [#267](https://github.com/kco994553-star/Investment-System1/pull/267) | feat: 예시 데이터와 기존 엔진을 연결한 인터랙티브 투자 스튜디오 | `canonical` | 2026-10-15T11:23:02Z | Main | 닫을 것 | 독립 DEMO 스튜디오 제안이다. DC-56의 기존 자료층·엔진 유지 및 최소 화면 방향과 별도이므로 실험·검증 근거를 보존한 뒤 종료 제안. |
| [#281](https://github.com/kco994553-star/Investment-System1/pull/281) | [WIP] 투자 흐름 중심 프론트엔드 v2 시안 | `canonical` | 2026-10-17T03:45:33Z | Main | 닫을 것 | 별도 frontend-redesign 실험이며 본문에 TARGET v0 사용이 명시돼 현행 DC-24·56과 불일치. 운영 이식 없이 시안 기록만 보존. |
| [#305](https://github.com/kco994553-star/Investment-System1/pull/305) | [WIP] 프론트엔드 Atlas: 왼쪽 탐색·시스템 안내·실제 QGV 다각형 | `canonical` | 2026-10-18T04:42:18Z | Main | 닫을 것 | 무채색 Atlas 시안 적용안이다. DC-07·25의 대체된 시각 방향 및 DC-56 재작성과 맞지 않아 독립 시안 종료 제안. |
| [#392](https://github.com/kco994553-star/Investment-System1/pull/392) | TARGET v0(19종목) 결합 해소: 관심·★·그룹=Issuer 키, 차트 그림=Listing 키, 기기 시세·차트 범위=ACTUAL∪관심∪TARGET v1 후보 (소유자 승인 후 병합) | `canonical` | 2026-10-24T02:00:10Z | Main | 엔진·계약만 가져올 것 | Issuer/Listing 키와 비파괴 저장 이전은 재사용 가치가 있으나 기기 시세 범위·옛 화면은 DC-31·54·55에 맞춰 분리해야 한다. |
| [#416](https://github.com/kco994553-star/Investment-System1/pull/416) | docs(9.1): QGV v2 백테스트 실행 기준 v1·18개 설정·Codex 지시서 | `canonical` | 2026-10-26T11:18:13Z | Codex | 판단 필요 | 과거 calc 10-17.1 고정 연구 명세다. #417 보존 의존성과 최신 연구 계약 차이를 먼저 대조해 역사 문서로 보존할지 결정. |
| [#417](https://github.com/kco994553-star/Investment-System1/pull/417) | [WIP] research(9.1): QGV 장기 백테스트·30개 전략·합성 검증 (실자료 차단) | `canonical` | 2026-11-01T02:17:10Z | Codex | 판단 필요 | 본문이 과거 calc 의존성 보존을 명시하며 최신 canonical 조합 실패를 기록한다. 최신 엔진으로 그대로 승격·병합하지 않는다. |
| [#418](https://github.com/kco994553-star/Investment-System1/pull/418) | [WIP][Docs] Annual book-style stock reselection: QGV deciles, two US universes, factor TOP10 and 22 tables | `canonical` | 2026-10-27T11:10:06Z | Codex | 판단 필요 | 과거 연구 설계의 D1 최고 방향과 현재 D10 최고 전달 규칙이 다르다. 역사 명세 보존과 현행 연구 인수 범위 구분 필요. |
| [#430](https://github.com/kco994553-star/Investment-System1/pull/430) | research(9.1): #417 연구 명세 재고정 — calc_version 2026-10-23.1·canonical 96037d1c (#417 가지로 병합, 시험 33개 실패 해소) | `research/qgv-backtest-v1-20261026` | 2026-10-30T12:10:08Z | Main | 판단 필요 | #417을 calc 23.1로 재고정하는 제안이나 #417 최신 본문은 과거 calc 보존을 명시한다. 핀 변경 승인·재현 목적부터 확인. |
| [#432](https://github.com/kco994553-star/Investment-System1/pull/432) | BT-DATA-PILOT v0.6: 장기 가격 확장·PIT V 입력 감사·실자료 배당 장부 | `canonical` | 2026-10-31T07:50:33Z | Codex | 엔진·계약만 가져올 것 | KIS 장기 입력·PIT·배당 진단과 수집 안정화 코드 보존. 비공개 Lab 계약에 맞춰 채택하고 연구 성과로 승격하지 않는다. |
| [#433](https://github.com/kco994553-star/Investment-System1/pull/433) | 결정 기록(제안): GSQ-026 IEX 마지막 체결가 공개 · "가격은 클릭할 때만" 폐지(공개 IEX 가격 한정) · DC-33 (오너 승인 뒤 병합) | `canonical` | 2026-10-31T02:30:24Z | Main | 닫을 것 | IEX 원가격 공개와 클릭 제한 폐지의 미승인 제안이다. 현행 DC-54·55와 다른 범위이므로 제안 이력을 남기고 종료 검토. |
| [#437](https://github.com/kco994553-star/Investment-System1/pull/437) | [Lab 계약] 결과 경로 제안 — lab-backtest-v1 비공개 파일럿·기존 계약 차이 | `research/bt-data-pilot-alpaca-probe-20261031` | 2026-11-15T06:02:37Z | Codex | 판단 필요 | Lab 계약 PR이자 Main/Codex 지속 인계 창구다. 뒤 PR 수가 많다는 이유로 닫지 말고 인계 대체 위치·잔여 계약을 먼저 정한다. |
| [#443](https://github.com/kco994553-star/Investment-System1/pull/443) | [WIP][Docs] 전진검증 v3: 책 전략·QGV 바구니 규칙표와 PIT 계산 조건 | `canonical` | 2026-10-31T10:50:28Z | Codex | 판단 필요 | 책 규칙과 전진검증 v3 문서 제안이다. #452에서 대체·원문 대기 부분을 구분했으므로 미인수 근거만 대조한다. |
| [#452](https://github.com/kco994553-star/Investment-System1/pull/452) | [WIP][Research] 책 규칙 인수·종목 비교 경계 및 동결 French 보유기간 분석 | `canonical` | 2026-11-01T01:04:23Z | Codex | 엔진·계약만 가져올 것 | 책 규칙 인수·동결 French 분석은 연구 보존 대상이다. 공용 결정 기록과 공개 성과 연결 없이 필요한 연구 계약만 검토. |
| [#454](https://github.com/kco994553-star/Investment-System1/pull/454) | 연구 엔진: EXP-STOCK-INDICATOR-DECILES-v1 (선정·장부·지표·CLI·manifest·합성 실행 묶음) | `canonical` | 2026-11-01T09:52:43Z | Codex | 엔진·계약만 가져올 것 | exp_deciles 연구 계산 커널과 합성 계약의 선행 PR이다. 비공개 Lab용으로 의존 체인을 보존하며 선별 통합. |
| [#455](https://github.com/kco994553-star/Investment-System1/pull/455) | 자료층 브라우저 시험: 열린 읽기가 끝난 뒤 about:blank에서 새로 열기 (경합 고침, 시험만) | `canonical` | 2026-11-01T04:41:08Z | Main | 병합 후보 | 자료층 새 문서 요청 경합의 원인·시험 전용 수정이 본문에 있다. 통합 PR에 같은 패치가 들어 있어 중복 여부부터 확인. |
| [#458](https://github.com/kco994553-star/Investment-System1/pull/458) | [Draft] AI 탐색 범위 정리: 원자료·과거 기록의 불필요한 전체 읽기 방지 | `canonical` | 2026-11-01T07:18:20Z | GPT Work | 병합 후보 | 원자료 전체 탐색을 줄이는 AGENTS 문서 제안이다. 현재 START_HERE·권한 규칙과의 중복만 대조한 뒤 문서 인수 가능. |
| [#459](https://github.com/kco994553-star/Investment-System1/pull/459) | [Draft·실행 전] Alpaca SIP 소표본 1회 측정 도구 (11/01 결정 2) — 병합하지 않음 | `canonical` | 2026-11-01T11:22:31Z | Codex | 판단 필요 | 본문에 병합하지 않는 단발 측정 준비와 실행 가지 구분이 명시돼 있다. 실행·수집 상태를 확인하기 전 일반 병합 후보로 올리지 않는다. |
| [#460](https://github.com/kco994553-star/Investment-System1/pull/460) | SEC 1회용 수집 계획 (11/01 결정 1: 계획 먼저, 실행은 승인 뒤) + 8% 불일치 분류 + 측정 가지 코드 이관 | `canonical` | 2026-11-01T11:22:52Z | Codex | 판단 필요 | SEC 계획·수집 코드·실행 조건이 함께 있다. #462의 재개 보완 및 이미 수행된 수집과 대조해 현행 실행 경로만 인수. |
| [#461](https://github.com/kco994553-star/Investment-System1/pull/461) | 연구 입력: 기존 Alpaca 원본 OHLCV·출처 오프라인 정규화 | `claude/alpaca-sample-once` | 2026-11-01T11:12:33Z | Codex | 엔진·계약만 가져올 것 | #459 위 Alpaca 오프라인 정규화 계약이다. 현재 새 공급처 도입 보류와 별개로 보관 원문 재사용 코드만 보존·대조. |
| [#462](https://github.com/kco994553-star/Investment-System1/pull/462) | SEC 재개: 분할 manifest 파일명·크기 대사와 실패 임시파일 정리 | `claude/sec-once-collect-plan` | 2026-11-01T11:12:53Z | Codex | 병합 후보 | #460의 분할 재개 무결성·임시파일 결함 수정이다. 기존 정상본 보존에 필요하며 선행 코드와 함께 현재 트리에서 대조 필요. |
| [#464](https://github.com/kco994553-star/Investment-System1/pull/464) | [Draft·보존] 연구 엔진 입력 어댑터: SEC 일괄·IEX 신호·Alpaca 일봉 → 엔진 입력 묶음 (base #454, Codex 인계) | `claude/exp-deciles-engine` | 2026-11-02T10:14:09Z | Codex | 엔진·계약만 가져올 것 | 본문이 보존용·병합하지 않음과 Codex 인수를 명시한다. SEC/IEX/Alpaca 어댑터를 의존 버전과 함께 선별한다. |
| [#465](https://github.com/kco994553-star/Investment-System1/pull/465) | [WIP] 연구 시총 문턱을 2025년 CPI 구매력 기준으로 버전 분리 | `claude/exp-deciles-input-adapters` | 2026-11-02T10:19:13Z | Codex | 엔진·계약만 가져올 것 | CPI2025 시총 문턱의 별도 연구 버전이다. 공식 모집단 교체로 오해하지 않게 #464 의존성과 계약만 인수. |
| [#467](https://github.com/kco994553-star/Investment-System1/pull/467) | [WIP] research: AMD 원시 EV/매출 1회사 계산·섹터 QGV 준비 | `research/cpi2025-market-cap-20261101` | 2026-11-04T10:06:59Z | Codex | 엔진·계약만 가져올 것 | 단일 기업 비율·유동성 진단과 연구 CLI다. 전략 성과나 전체시장 검증으로 승격하지 않고 연구 엔진만 재사용. |
| [#468](https://github.com/kco994553-star/Investment-System1/pull/468) | P2-6 포트폴리오 공개 층: 5.1 모델 후보(N15 핵심 8%·일반 6%)·적용 버전·기준일·TARGET v1 확정 전 상태 | `canonical` | 2026-11-07T12:45:10Z | Main | 판단 필요 | 공개 포트폴리오 새 화면이다. #392와 중복은 아니나 DC-56 최소 화면 및 #559 중앙 V 빌더 기준으로 재검토 필요. |
| [#469](https://github.com/kco994553-star/Investment-System1/pull/469) | [WIP] research: 기술적 지표 5종·고정 그룹 리더보드 검증 | `research/sector-liquidity-diagnostics-20261102` | 2026-11-04T10:45:25Z | Codex | 엔진·계약만 가져올 것 | 기술 지표·고정 그룹 리더보드의 연구 기반이다. DC-55 비공개 방향에서 커널·그룹 검증을 재사용. |
| [#472](https://github.com/kco994553-star/Investment-System1/pull/472) | [WIP] 기업 통합 진입: 무형자산 3카드·12사 표본 연구 인계 | `canonical` | 2026-11-04T23:04:49Z | Codex | 판단 필요 | 무형자산 기업 진입 연구 카드 인계다. 회사별 근거와 새 프론트 제품 우선순위를 확인한 뒤 화면 요구사항으로 보존. |
| [#473](https://github.com/kco994553-star/Investment-System1/pull/473) | 연구: 포트폴리오 선택 모드와 Lab 선정·비중 재현 계약 | `canonical` | 2026-11-09T10:08:32Z | Codex | 엔진·계약만 가져올 것 | 선정 모드·비중·재현 계약이다. 공식 TARGET과 분리하고 비공개 Lab 소비자에 필요한 부분만 인수. |
| [#474](https://github.com/kco994553-star/Investment-System1/pull/474) | 계층 2: 날짜별 운영 QGV 보관본의 요인·축·프리셋 커버리지 CLI | `canonical` | 2026-11-04T12:20:30Z | Codex | 엔진·계약만 가져올 것 | 보관 공식 QGV의 요소·축 커버리지 CLI다. 555 연구 커버리지와 분모를 구분하는 감사 도구로 재사용. |
| [#475](https://github.com/kco994553-star/Investment-System1/pull/475) | 계층 9.1: 기존 회사 지표를 정상 연구 CLI에서 Lab v2로 인계 | `research/sector-liquidity-diagnostics-20261102` | 2026-11-05T01:27:37Z | Codex | 엔진·계약만 가져올 것 | #467 회사 지표를 lab-backtest-v2로 투영한다. 비공개 Lab 계약과 결과 종류를 유지해 인수. |
| [#476](https://github.com/kco994553-star/Investment-System1/pull/476) | 계층 9.2: 보관 QGV와 PIT QGV를 증권·날짜·계산 버전으로 대조 | `research/operational-qgv-coverage-20261104` | 2026-11-04T12:20:34Z | Codex | 엔진·계약만 가져올 것 | 고정 증권·날짜·버전의 보관/PIT 대조 경로다. v3 공개 수익률 실행으로 확장하지 않고 오프라인 검증만 재사용. |
| [#477](https://github.com/kco994553-star/Investment-System1/pull/477) | [WIP] 계층 4: 보관 매크로의 가용시각 조회·발표 후 값 유지와 갱신 인계 | `canonical` | 2026-11-05T04:23:00Z | Codex | 엔진·계약만 가져올 것 | 매크로 가용시각·수정본 계약이다. 역사 PIT 입증과 취득시각을 분리하는 판독 기능을 보존. |
| [#478](https://github.com/kco994553-star/Investment-System1/pull/478) | [WIP] 계층 3: 보유 일봉의 기존 기술 지표 연결과 공급처·갱신 설계 | `research/technical-leaderboard-20261103` | 2026-11-05T00:17:21Z | Codex | 엔진·계약만 가져올 것 | 보유 일봉의 기술 커널·가용성 계약이다. #556 현행 비공개 출력과 중복·잔여 지표를 대조해 가져온다. |
| [#479](https://github.com/kco994553-star/Investment-System1/pull/479) | [WIP] 계층 2·9: 보관 XBRL 입력 복구와 금융업 V 후보 계산 | `research/operational-qgv-coverage-20261104` | 2026-11-05T00:26:09Z | Codex | 엔진·계약만 가져올 것 | 금융 V 후보·XBRL 보완 경로다. 공식 중앙 V와 분리된 연구 입력 계약을 유지하며 최신 #537과 대조. |
| [#480](https://github.com/kco994553-star/Investment-System1/pull/480) | [WIP] 비공개 KIS 보관 가격을 공통 기술·장부·QGV 계산에 연결 | `research/technical-display-offline-20261105` | 2026-11-05T03:48:53Z | Codex | 엔진·계약만 가져올 것 | 기존 KIS 어댑터·기술·장부·QGV 연결이다. #556의 canonical 경로와 같은 기능을 중복 이식하지 않는다. |
| [#482](https://github.com/kco994553-star/Investment-System1/pull/482) | [WIP] 현재 확장: 보유 명부·재무 연결과 공통 QGV 실행 경로 | `canonical` | 2026-11-05T03:48:50Z | Codex | 엔진·계약만 가져올 것 | 현재 확장 후보의 명부·신원·적격성 구분 계약이다. 확정 Top500과 관측 카탈로그를 섞지 않는 경계만 인수. |
| [#483](https://github.com/kco994553-star/Investment-System1/pull/483) | [WIP] 뉴스·공시: 내용 수정·증분 상태와 보관 자료 재생 안정화 | `canonical` | 2026-11-05T03:48:52Z | Codex | 병합 후보 | 같은 URL 내용 수정·이전 수집분 역전 결함을 고친다. 현행 뉴스 수집 코드와 계약 호환을 확인한 뒤 독립 수정으로 검토. |
| [#484](https://github.com/kco994553-star/Investment-System1/pull/484) | 기록 11/04·11/05·11/07: #471·#470 병합(합성 입력 연결 검증 상태) + CURRENT_HANDOFF 11/05·11/07 갱신 | `canonical` | 2026-11-07T14:15:03Z | Main | 판단 필요 | 11/04~11/07 당시 기록 PR이다. 최신 CURRENT_HANDOFF와 겹쳐 과거 상태를 되살릴 수 있어 역사 기록만 남길지 판단. |
| [#485](https://github.com/kco994553-star/Investment-System1/pull/485) | Lab 9.1 연구 범위·선정 방식: Codex #474 커버리지·#473 선정 판독기와 화면 (합성, Draft) | `canonical` | 2026-11-08T12:25:06Z | Main | 엔진·계약만 가져올 것 | #473·#474 소비자 계약이 #522에 포함된 화면이다. DC-55·56에 맞춰 Lab 판독·재현 부분만 인수. |
| [#486](https://github.com/kco994553-star/Investment-System1/pull/486) | [WIP] docs: QGV v2 모델과 v1.5 레거시 기준의 혼동 방지 | `canonical` | 2026-11-05T02:59:04Z | Codex | 병합 후보 | QGV v2와 v1.5 레거시 혼동 방지 문서다. 현재 555/공식 모델 설명과 대조 후 역사 설명을 보존하는 수정으로 검토. |
| [#487](https://github.com/kco994553-star/Investment-System1/pull/487) | 운영 연결 준비 11/05: 계층별 실행 위치·주기·Secret·캐시·실패 재개·정상본, 단계별 연결표, 확장 명부 입력 3종, Census·DOL 조치 (문서만) | `canonical` | 2026-11-05T04:44:43Z | Main | 판단 필요 | 11/05 운영 준비 계획은 최근 #558 통합과 시점이 다르다. 실행 위치·Secret·보류 상태를 최신 운영안과 대조해야 한다. |
| [#488](https://github.com/kco994553-star/Investment-System1/pull/488) | 4.1.3 매크로 관측 자료·갱신 상태: Codex #477 macro-current-query/1 판독기·화면 (합성, Draft) | `canonical` | 2026-11-05T04:15:23Z | Main | 엔진·계약만 가져올 것 | 매크로 관측·갱신 화면으로 진단 정보가 많다. DC-56에 따라 판독 계약을 남기고 진단 표는 상태 화면 요구사항으로 전환. |
| [#489](https://github.com/kco994553-star/Investment-System1/pull/489) | [WIP] 기술 경로: Hypothesis 검증·날짜 결함 수정·화면 합성 입력 | `research/kis-price-bridge-20261105` | 2026-11-05T04:36:46Z | Codex | 엔진·계약만 가져올 것 | 기술 경로 날짜 결함과 속성 시험이다. 현행 #556 경로에 회귀가 남는지 확인해 검증·fixture만 가져온다. |
| [#490](https://github.com/kco994553-star/Investment-System1/pull/490) | 5.2.7 뉴스 원천별 갱신 기록: news-signals schema 2 refresh 판독기·표 (Codex #483 계약, Draft) | `canonical` | 2026-11-05T05:18:51Z | Main | 엔진·계약만 가져올 것 | 뉴스 원천 갱신 판독기·표다. 갱신 원장 계약은 보존하고 정상 시 운영 정보 표시는 DC-56으로 재구성. |
| [#491](https://github.com/kco994553-star/Investment-System1/pull/491) | 기술 2-1 기업별 지표 블록: Codex #478 technical-offline-display/1 판독기·화면 (합성, Draft) | `canonical` | 2026-11-05T15:38:01Z | Main | 엔진·계약만 가져올 것 | #478 기술 출력 소비자다. #558 최소 비공개 패널에 필요한 판독만 통합하고 옛 화면은 묶음 병합하지 않는다. |
| [#492](https://github.com/kco994553-star/Investment-System1/pull/492) | 검색·계산 범위: Universe504와 확장 모집단을 따로 세는 칸 (Codex #482 current-expansion-research/1, 합성, Draft) | `canonical` | 2026-11-06T11:59:47Z | Main | 엔진·계약만 가져올 것 | 운영504/확장 분모 구분 소비자다. 모집단 계약을 재사용하되 현행 Top500 전환 상태와 짧은 문구로 다시 연결. |
| [#493](https://github.com/kco994553-star/Investment-System1/pull/493) | 비공개 층(KIS·인증 경로)을 기존 화면에: Worker /kis/* 7경로 + 기술·QGV·매크로·뉴스 비공개 펼치기 (DC-44, Draft) | `canonical` | 2026-11-05T15:39:57Z | Main | 판단 필요 | 옛 7경로 Worker·화면은 #558의 5경로로 일부만 대체된다. 누락된 classification/macro/news까지 대체됐다고 보고 닫으면 안 된다. |
| [#494](https://github.com/kco994553-star/Investment-System1/pull/494) | 품질 점검: 기업 검색 → QGV → 기업 화면 흐름 (axe·키보드·200%·상태), 결함 5건 수정, Lighthouse·Impeccable 기준선 (Draft) | `canonical` | 2026-11-05T13:37:43Z | Main | 판단 필요 | 접근성 결함과 CI 변경이 섞여 있다. DC-56이 멈춘 외관 시험과 필수 접근성 수정 범위를 분리해 결정. |
| [#495](https://github.com/kco994553-star/Investment-System1/pull/495) | 리더보드 표 비교 시험: Tabulator 6.7.1 대 기존 표 (격리 개발 화면) — 결론: 기존 표 유지 (Draft) | `canonical` | 2026-11-05T08:37:02Z | Main | 닫을 것 | 본문 결론이 Tabulator 미채택·기존 표 유지다. 비교 보고 보존을 확인한 뒤 채택하지 않는 실험 PR 종료 제안. |
| [#496](https://github.com/kco994553-star/Investment-System1/pull/496) | 보안 검사 시험 문서: Betterleaks·Semgrep·Trivy·ZAP Baseline 로컬 실행 결과와 빈틈 (문서만, Draft) | `canonical` | 2026-11-05T08:37:16Z | Main | 병합 후보 | 보안 검사 결과·빈틈을 기록한 문서 한 개다. 지금 해결된 항목과 미해결 항목을 대조한 뒤 기록 인수. |
| [#497](https://github.com/kco994553-star/Investment-System1/pull/497) | 기술 경로 속성 시험을 필수 CI에서 실제로 실행 + #489 화면 fixture를 1.1.8 화면 시험에 연결 (Draft) | `research/technical-property-validation-20261105` | 2026-11-05T13:37:20Z | Main | 판단 필요 | #489 속성 시험을 CI에서 실제 실행시키는 워크플로 변경이다. 현재 CI 설치·목록과 중복 및 유지비를 Main이 확인해야 한다. |
| [#498](https://github.com/kco994553-star/Investment-System1/pull/498) | [WIP] 기술: 확인된 분할조정 가격을 공통 지표 커널에 연결 | `research/technical-property-validation-20261105` | 2026-11-05T10:48:23Z | Codex | 엔진·계약만 가져올 것 | 확인된 분할조정 경로다. #542·#547·#556의 조정/참고 등급과 대조해 순수 helper·경계 시험만 인수. |
| [#499](https://github.com/kco994553-star/Investment-System1/pull/499) | Connect held SEC evidence to financial V candidate inputs | `research/financial-v-input-recovery-20261105` | 2026-11-05T12:19:56Z | Codex | 엔진·계약만 가져올 것 | 보관 SEC cover·주식 기준의 금융 V 연결이다. #537 임시 금융 산식과 혼합하지 않고 비가격 입력 근거를 보존. |
| [#500](https://github.com/kco994553-star/Investment-System1/pull/500) | research: link retained security evidence into current evaluation | `research/current-expansion-pipeline-20261105` | 2026-11-05T10:50:40Z | Codex | 엔진·계약만 가져올 것 | 현재 확장 발행사 crosswalk 근거 연결이다. 후보·신원·실제 종류주 적격성을 분리하는 계약만 인수. |
| [#501](https://github.com/kco994553-star/Investment-System1/pull/501) | IEX 파서 전체 심벌 모드 (--all-symbols): 1024 상한·504 사전 필터 없이 기호별 디렉터리·상태·마지막 체결을 따로 기록 (Draft, 실행 없음) | `canonical` | 2026-11-05T15:37:32Z | Main | 엔진·계약만 가져올 것 | IEX 전체 심벌 파서의 오프라인 모드다. DC-54의 재요청 보류를 유지하고 기존 원문 처리 가능 범위만 보존. |
| [#502](https://github.com/kco994553-star/Investment-System1/pull/502) | IEX 2026-11-02 원본 단발 보존·금융 11코드 가격 추출 준비 (안 A, 실행 안 함, Draft) | `canonical` | 2026-11-06T12:50:18Z | Main | 판단 필요 | IEX 특정일 단발 취득 실행 준비다. DC-54 재요청 금지와 충돌하므로 실행하지 않고 보존/종료 방침을 결정. |
| [#503](https://github.com/kco994553-star/Investment-System1/pull/503) | [WIP] Add evidence-linked discovery company selection and Main contract | `canonical` | 2026-11-06T11:19:42Z | Codex | 엔진·계약만 가져올 것 | 근거 기반 의외의 기업 선택 계약이다. 화면·공개 채택과 분리해 검토 근거·상태 모델만 보존. |
| [#504](https://github.com/kco994553-star/Investment-System1/pull/504) | [WIP] Adapt retained IEX delivery into existing financial V CLI | `research/financial-v-held-bridge-20261105` | 2026-11-07T02:22:09Z | Codex | 엔진·계약만 가져올 것 | #502 원문형 결과를 금융 V에 잇는 오프라인 어댑터다. 기존 입력 재사용과 새 IEX 취득을 분리. |
| [#505](https://github.com/kco994553-star/Investment-System1/pull/505) | [WIP] 섹터 QGV v0·부분 Q/G 비교·V 비가격 입력과 재개 연결 | `canonical` | 2026-11-07T06:42:43Z | Codex | 엔진·계약만 가져올 것 | 섹터 QGV 초기 엔진·비가격 근거의 기반이다. #537 555가 의존하므로 계산·근거만 유지하고 옛 기본값을 복원하지 않는다. |
| [#506](https://github.com/kco994553-star/Investment-System1/pull/506) | 의외의 기업 화면: 리더보드 목록(2.1.8)·기업 상세 마크(2.4.6), Codex #503 discovery-company/v1 연결 (합성, Draft) | `canonical` | 2026-11-06T13:25:16Z | Main | 엔진·계약만 가져올 것 | #503 계약의 합성 화면이며 #510에 포함된다. 새 프론트에는 근거·판독만 가져오고 이전 화면을 일괄 병합하지 않는다. |
| [#507](https://github.com/kco994553-star/Investment-System1/pull/507) | [Draft] 섹터 QGV 1.2: Codex #505 공통 엔진 연결 + Q/G 부분 비교 (화면 합산·Main 기본값 삭제, 합성 입력) | `canonical` | 2026-11-07T07:35:33Z | Main | 엔진·계약만 가져올 것 | #505 엔진을 화면에 연결하고 #510으로 통합했다. 설정/재현 호출 계약은 보존하되 DC-56에 맞게 화면을 다시 최소화. |
| [#508](https://github.com/kco994553-star/Investment-System1/pull/508) | 공용 가드: IEX 순수 값 규칙을 providers/iex_values.py로 최소 분리 (#504 가드 실패 해결의 Main 몫, Draft) | `canonical` | 2026-11-07T00:52:40Z | Main | 병합 후보 | IEX 순수 도우미를 공급자 I/O에서 분리한 경계 수정이다. #504 적용 여부와 현행 모듈을 대조하고 가드 완화 없이 인수. |
| [#509](https://github.com/kco994553-star/Investment-System1/pull/509) | [WIP] 정책 근거 계약·Federal Register 오프라인 갱신 재생 | `canonical` | 2026-11-09T11:21:55Z | Codex | 엔진·계약만 가져올 것 | 정책 근거·오프라인 재생 계약이다. #512 숫자 바이트 고정과 함께 인수하고 공급처 실행/공개 게시를 별도로 판단. |
| [#510](https://github.com/kco994553-star/Investment-System1/pull/510) | [Draft] #506 의외의 기업 + #507 섹터 QGV 통합 가지 (screen-qgv.js 4,963/5,120) | `canonical` | 2026-11-08T01:42:59Z | Main | 엔진·계약만 가져올 것 | #506·#507와 저장 설정을 합친 통합 묶음이다. #519 이후 포함 이력과 최신 설정 계약을 대조해 선별. |
| [#511](https://github.com/kco994553-star/Investment-System1/pull/511) | [Draft] 4.5 나비효과 정책·지정학: Codex #509 view/2·/1 + #512 navigation/2(받은 바이트) 화면 연결 (합성 CI, 실자료는 비공개 개발 경로만) | `canonical` | 2026-11-07T11:57:02Z | Main | 엔진·계약만 가져올 것 | #509·#512 정책 소비자와 합성 화면이다. 판독·출처 계약을 보존하고 운영 설명은 DC-56에 맞춰 별도 정리. |
| [#512](https://github.com/kco994553-star/Investment-System1/pull/512) | [WIP] fix(research): numeric-safe policy navigation byte binding v2 | `research/policy-impact-20261107` | 2026-11-07T11:23:44Z | Codex | 엔진·계약만 가져올 것 | navigation/2 숫자 거부 결함과 실제 view 바이트 결합 수정이다. #509 선행 계약과 함께 선별 인수. |
| [#513](https://github.com/kco994553-star/Investment-System1/pull/513) | 매크로 근거: 실패 반환 처리·빈 기본값 게시 차단·이전본 미확인 구분·배포 시 이력 연속성 검사 (run 42326419126) | `canonical` | 2026-11-08T04:41:32Z | Main | 병합 후보 | 매크로 실패 시 정상본 보존·배포 차단 수정이다. 적용되지 않은 워크플로 패치는 별도 승인 대상으로 남기고 현재 운영과 대조. |
| [#514](https://github.com/kco994553-star/Investment-System1/pull/514) | research: preserve saved sector settings and validate original-context replay | `research/sector-qgv-default-20261106` | 2026-11-07T11:38:03Z | Codex | 엔진·계약만 가져올 것 | 섹터 설정 저장·원래 입력 재현 검증이다. #516 및 #537의 최신 재현 계약과 함께 인수. |
| [#515](https://github.com/kco994553-star/Investment-System1/pull/515) | research: validate dated security joins for technical filters | `research/technical-adjusted-link-20261105` | 2026-11-07T11:39:43Z | Codex | 엔진·계약만 가져올 것 | 날짜·고정 증권 ID 기반 기술/QGV 조인이다. 최신 group/2 및 비공개 기술 경계를 함께 유지. |
| [#516](https://github.com/kco994553-star/Investment-System1/pull/516) | research: share dated ten-sector classifications across QGV, technical and macro | `research/common-classification-base-20261107` | 2026-11-08T06:02:18Z | Codex | 엔진·계약만 가져올 것 | 공통 분류·group/2 계약의 기반이다. #520 이후 사업 근거 변경과 합쳐 핀을 확인하고 화면 없이 인수. |
| [#517](https://github.com/kco994553-star/Investment-System1/pull/517) | 기술 조건 필터 3.5: 같은 평가일·같은 증권일 때만 QGV 리더보드와 결합 (Codex #515 계약, 문자열 대체 없음, Draft) | `canonical` | 2026-11-08T01:42:33Z | Main | 엔진·계약만 가져올 것 | #515 기술 필터 소비자 수정이다. #519 이후 포함 여부를 대조해 조인 가드만 비공개 경로에 재사용. |
| [#518](https://github.com/kco994553-star/Investment-System1/pull/518) | 기능 ID 정렬(2.1.8·2.4.6·2.2.7·3.5·4.5.x.1) + 공통 분류체계 결정 기록(DC-48)·Main 소비 명세 (문서·트리, Draft) | `canonical` | 2026-11-08T02:29:13Z | Main | 판단 필요 | 기능 ID·공통 분류 결정과 트리가 섞여 있다. 최신 결정 번호·현황과 대조 후 기록만 통합할지 판단. |
| [#519](https://github.com/kco994553-star/Investment-System1/pull/519) | [Draft·통합] #455·#513·#510·#511·#517·#518 + Codex #516 5b0ec88a + 공통 분류 공급자·호출부 (한 트리 검증) | `canonical` | 2026-11-08T08:13:31Z | Main | 다른 PR로 대체됨 | #522 본문이 #519를 인수 완료 기준점으로 삼는 후속 통합임을 명시한다. 기준점·독자 공급자 근거를 보존하고 종료는 별도 승인. |
| [#520](https://github.com/kco994553-star/Investment-System1/pull/520) | Research: apply approved sector boundaries to held issuer classifications and Q/G inputs | `research/common-classification-20261107` | 2026-11-08T08:58:20Z | Codex | 엔진·계약만 가져올 것 | 공통 경계 정책·보유 재무 연결로 #523 이후 체인의 기반이다. 현재 555 입력에 필요한 분류·근거만 인수. |
| [#521](https://github.com/kco994553-star/Investment-System1/pull/521) | [Draft] 공통 분류 보관 묶음 비공개 전달(오너 인증 Worker) · 운영504/확장 표본 분리 · 평가일 · 경계 정책 기록 | `canonical` | 2026-11-08T12:12:32Z | Main | 엔진·계약만 가져올 것 | 분류 비공개 전달이 #522에 합쳐졌다. #558에서 해당 경로는 제외됐으므로 인증/원자적 배치 계약만 선별 보존. |
| [#522](https://github.com/kco994553-star/Investment-System1/pull/522) | [Draft·후속 통합] #519 d3e640bb(기준점) + #516 4cf2e037 + #520 41f2a25b + #523 6fc7a673 + #521 + #485 (한 트리 검증) | `canonical` | 2026-11-08T14:22:02Z | Main | 엔진·계약만 가져올 것 | #519 이후 누적 통합 기준점이다. #526~#538 화면 체인의 선행이며 DC-56에 따라 전체를 병합하지 않는다. |
| [#523](https://github.com/kco994553-star/Investment-System1/pull/523) | research: 기존 분류 결과의 Q/G·공식 관문 집계 연결 | `research/expanded-held-classification-20261108` | 2026-11-08T10:43:29Z | Codex | 엔진·계약만 가져올 것 | 원결과 해시 고정 집계 계약이다. #524 전달·최신 555 커버리지와 함께 분모/관문 구분을 재사용. |
| [#524](https://github.com/kco994553-star/Investment-System1/pull/524) | 연구: 보유 발행사 분할 전달과 기존 결과 기반 커버리지 | `research/classification-count-summary-20261108` | 2026-11-08T12:54:57Z | Codex | 엔진·계약만 가져올 것 | 1057발행사 작은 shard 전달과 결손 집계다. 기존 비공개 파일을 다시 계산하지 않고 검증/배치 계약만 인수. |
| [#525](https://github.com/kco994553-star/Investment-System1/pull/525) | 공통 산업의 매크로 근거 조회와 현행 10섹터 정의 연결 | `research/classification-count-summary-20261108` | 2026-11-08T12:20:48Z | Codex | 엔진·계약만 가져올 것 | 산업 분류→매크로 근거 조회 계약이다. 실제 대응 부재를 유지하며 #477/공통 분류 의존성과 함께 인수. |
| [#526](https://github.com/kco994553-star/Investment-System1/pull/526) | [Draft] 대기열 4·5번 + 선정 반례 + QGV 커버리지 단계: #524 확장 발행사 찾기 · #525 공통 사전·산업 매크로 · #473 상위 % 정밀도 · #527 입력 연결 수정 비교 | `claude/integration-20261108` | 2026-11-09T22:24:04Z | Main | 엔진·계약만 가져올 것 | #524·#525 소비자와 확장 화면의 누적 묶음이다. #530 이후 기반이므로 판독·근거 연결만 선별. |
| [#527](https://github.com/kco994553-star/Investment-System1/pull/527) | [WIP] 금융·REIT 보관 입력 연결과 동일 조건 QGV 증분 검증 | `research/held-issuer-delivery-20261108` | 2026-11-10T10:26:52Z | Codex | 엔진·계약만 가져올 것 | 금융·REIT 입력 연결 수정의 원결과 비교다. #528~#537 기반에서 실제 회복 근거를 보존해 인수. |
| [#528](https://github.com/kco994553-star/Investment-System1/pull/528) | 연구: 운영504 평가와 9개 요소 참조집단 분리 | `research/sector-held-input-repair-20261109` | 2026-11-10T11:20:17Z | Codex | 엔진·계약만 가져올 것 | 운영 평가와 확장 참조집단을 분리하는 연구 계약이다. 현행 555 참조 정의에 필요한 검증을 재사용. |
| [#529](https://github.com/kco994553-star/Investment-System1/pull/529) | [WIP] 연구: 고정 핵심 통합·섹터 QGV와 별도 참조·순위 계약 | `research/sector-reference-study-20261110` | 2026-11-12T11:19:42Z | Codex | 엔진·계약만 가져올 것 | 축소 U1/U2/S1 및 D1~D10 전 구간 계약이다. 555 대체 목표와 구분해 공통 전달·입력 검증만 인수. |
| [#530](https://github.com/kco994553-star/Investment-System1/pull/530) | 통합 QGV·섹터 QGV: #528·#529 인수, U1/U2/S1 연구 후보·기업 상세 비교, 요소 10분위 전체 조회·구간 색인·참조 입력 독립 기준 | `claude/expanded-browse-dictionary` | 2026-11-13T09:44:23Z | Main | 엔진·계약만 가져올 것 | #528·#529 소비자·전체 분위 조회의 누적 화면이다. #533 이후 기반에서 판독·구간 무결성만 선별. |
| [#531](https://github.com/kco994553-star/Investment-System1/pull/531) | [WIP] research: evidence-backed company ownership and subsidiary views | `canonical` | 2026-11-12T11:33:37Z | Codex | 엔진·계약만 가져올 것 | 근거 기반 모자회사·지분 관계 순수 모델이다. 검토 범위·receipt 경계를 보존하고 화면과 독립 인수. |
| [#532](https://github.com/kco994553-star/Investment-System1/pull/532) | 관계망 골격: 5.1.1·5.1.2·기업 화면 관계 줄 (Codex #531 company-ownership-view/1 판독, 합성) | `research/company-ownership-20261111` | 2026-11-13T09:44:20Z | Main | 엔진·계약만 가져올 것 | #531 관계망 판독·receipt 수정 화면이다. #533 통합에 포함되며 재작성 시 순수 판독과 근거만 가져온다. |
| [#533](https://github.com/kco994553-star/Investment-System1/pull/533) | 통합 Draft: #530 위 관계망(#532) 연결 · 관계 자료 인증 전달(Worker part·배치·판독 대조·오너 전용 불러오기) | `claude/dual-qgv-board` | 2026-11-13T09:44:25Z | Main | 엔진·계약만 가져올 것 | QGV와 관계망 인증 전달 통합 묶음이다. #536 선행이지만 DC-56에서 큰 화면 묶음을 재사용하지 않는다. |
| [#534](https://github.com/kco994553-star/Investment-System1/pull/534) | research: fixed QGV 3/3/3 candidates, exact weights and retained-input comparison | `research/dual-qgv-core-20261110` | 2026-11-13T23:19:04Z | Codex | 엔진·계약만 가져올 것 | 333 추가 진행은 중지됐으나 EPS/총차입금 연결과 #537 선행 코드가 있다. 333 기본값 승격 없이 재사용 부분만 인수. |
| [#535](https://github.com/kco994553-star/Investment-System1/pull/535) | [#536으로 대체] QGV 3/3/3 연구 후보(U2-333·U1-333·S1-333) 소비자 연결 — 계약·합성·실자료 인수, 판독기·화면·인증 경로 | `claude/qgv-ownership-integration` | 2026-11-13T23:37:20Z | Main | 다른 PR로 대체됨 | 제목과 #536 본문이 #536 대체를 명시한다. 실패 이력·실자료 핀을 보존한 뒤 Main이 오너 승인으로 종료. |
| [#536](https://github.com/kco994553-star/Investment-System1/pull/536) | QGV 3/3/3 소비자 연결 (r2) — EPS 입력 단계·Q 입력 복구·인계 대조·재시작 복원 (#535 대체) | `claude/qgv-ownership-integration` | 2026-11-14T00:13:38Z | Main | 엔진·계약만 가져올 것 | DC-56이 이 화면 묶음 병합 중단을 명시한다. EPS/Q 입력 복구·자료 형식·계약만 추출하고 333 화면은 진행하지 않는다. |
| [#537](https://github.com/kco994553-star/Investment-System1/pull/537) | research: 555 models, Top500 candidate flow and temporary financial raw-role bridge | `research/qgv-333-20261113` | 2026-11-14T08:25:03Z | Codex | 엔진·계약만 가져올 것 | 555·Top500·임시 금융의 생산자다. 현행 연구 엔진/계약을 선별 인수하되 공식 채택·실제 Top500 확정으로 해석하지 않는다. |
| [#538](https://github.com/kco994553-star/Investment-System1/pull/538) | QGV 555 · 시총 Top500 · 사용자 설정: 2.1 모집단·모형 선택, 2.2.7 5역할 설정 (DC-49) | `claude/qgv-333-r2` | 2026-11-14T08:15:31Z | Main | 엔진·계약만 가져올 것 | DC-56이 이 화면 묶음 병합 중단을 명시한다. 엔진·자료 형식·계약만 추출하며 합성 화면을 운영 완료로 보지 않는다. |
| [#541](https://github.com/kco994553-star/Investment-System1/pull/541) | research: isolate personal sheet V inputs and reuse Python/JS 555 calculation | `research/qgv-555-top500-20261114` | 2026-11-14T10:09:05Z | Codex | 엔진·계약만 가져올 것 | 내 시트 V 추가 개발은 DC-54로 보류다. #547이 재사용하는 순수 가격/V 계약만 보존하고 시트 화면 확장은 하지 않는다. |
| [#542](https://github.com/kco994553-star/Investment-System1/pull/542) | research: hand off KIS daily preprocessing and technical availability to Main | `research/qgv-555-top500-20261114` | 2026-11-14T12:49:47Z | Codex | 엔진·계약만 가져올 것 | KIS 전처리·기술 가용성 계약이다. #547·#556 최신 경로와 중복을 확인해 helper/검증만 인수. |
| [#544](https://github.com/kco994553-star/Investment-System1/pull/544) | research: prepare Top500 transition, public listing metadata and sheet review | `research/qgv-555-top500-20261114` | 2026-11-14T11:22:07Z | Codex | 엔진·계약만 가져올 것 | Top500 전환·상장 메타 계약이다. 실제 선정 미확정을 유지하고 시트 확장 보류 부분을 분리한다. |
| [#547](https://github.com/kco994553-star/Investment-System1/pull/547) | research: connect owner-private KIS close V and split evidence | `research/personal-sheet-v-20261114` | 2026-11-14T12:44:23Z | Codex | 엔진·계약만 가져올 것 | 555 기반 KIS V 연구 경로다. #556은 canonical calc23.1로 별도 구현돼 전체 대체가 아니며 공통 신원·가격 검증만 선별. |
| [#550](https://github.com/kco994553-star/Investment-System1/pull/550) | [WIP] Worker·화면의 명시적 무기한 토큰 상태와 접근 검증 | `ccr-263267c9-f5ng5h` | 2026-11-15T03:09:28Z | Codex | 엔진·계약만 가져올 것 | #538 위 NEVER/접근 검증 증분이다. #558 본문이 이를 선별 반영했다고 명시하므로 남은 검증 차이만 대조. |
| [#551](https://github.com/kco994553-star/Investment-System1/pull/551) | research: accept retained KIS latest requests and exact class symbols | `research/kis-owner-v-20261114` | 2026-11-15T03:26:03Z | Codex | 엔진·계약만 가져올 것 | 빈 BYMD·정확 종류주 slash 기호 수용 수정이다. #556 canonical 이관분과 대조해 미반영 회귀만 인수. |
| [#555](https://github.com/kco994553-star/Investment-System1/pull/555) | [WIP] docs: 전체 아키텍처와 공개·비공개 전환 상태 정리 | `canonical` | 2026-11-15T04:46:22Z | GPT Work | 병합 후보 | 전체 구조를 한 문서로 정리하는 문서 PR이다. #554 이후 결정 반영과 최신 #557 계획 구분을 Main이 확인한 뒤 검토. |
| [#556](https://github.com/kco994553-star/Investment-System1/pull/556) | Private KIS reference technical output and canonical V stage one | `canonical` | 2026-11-15T06:00:32Z | Codex | 병합 후보 | 기본 가지 위 KIS 기술 참고 출력·canonical V 생산자다. #558 소비자 필드 계약과 최신 머리 CI를 대조하는 우선 후보. |
| [#557](https://github.com/kco994553-star/Investment-System1/pull/557) | 결정 기록: FV3-PUBLIC 철회 · DC-55 새 앱 한정 실행 · TARGET v1 빌더 V 출처 · DC-56b 금지 표현 (문서 전용) | `canonical` | 2026-11-15T05:56:09Z | Main | 판단 필요 | 문서 전용이라는 제목과 달리 고정 diff 8파일에 direction_rules.json·시험이 포함된다. 제목/범위 정정 또는 기록·가드 분리부터 확인. |
| [#558](https://github.com/kco994553-star/Investment-System1/pull/558) | 비공개 구역 통합: Worker /kis/* 5개 경로(NEVER 읽기 토큰) + 새 앱 비공개 칸 | `canonical` | 2026-11-15T06:06:03Z | Main | 병합 후보 | 기본 가지에서 5경로 오너 인증과 최소 비공개 칸을 통합한다. #556 계약·최신 CI·오너 승인 및 배포 검증이 선행. |
| [#559](https://github.com/kco994553-star/Investment-System1/pull/559) | 11/16 PR: TARGET v1 빌더 V 출처를 중앙 V로 한정 (기기 V 경로 삭제, DC-31) | `canonical` | 2026-11-15T05:36:50Z | Main | 병합 후보 | TARGET v1의 중앙 V 전용 경로로 과도기 예외를 종료한다. #557 결정 기록과 기존 초안/원장 보존 시험을 함께 확인. |

## 쌓인 묶음: 실제 base 관계

아래 화살표는 **PR의 base가 앞 PR의 head 가지와 같은 관계**만 뜻한다. 현재 머리 포함·머지 순서 승인을 뜻하지 않는다. 각 줄은 루트부터 잎까지의 의존 순서다. 동일 앞부분을 공유하는 가지는 한 번만 통합해야 한다. 앞 PR 머리가 바뀌었으면 자식에 그 변경이 들어 있는지 다시 확인한다.

- [#417](https://github.com/kco994553-star/Investment-System1/pull/417) → [#430](https://github.com/kco994553-star/Investment-System1/pull/430)
- [#432](https://github.com/kco994553-star/Investment-System1/pull/432) → [#437](https://github.com/kco994553-star/Investment-System1/pull/437)
- [#454](https://github.com/kco994553-star/Investment-System1/pull/454) → [#464](https://github.com/kco994553-star/Investment-System1/pull/464) → [#465](https://github.com/kco994553-star/Investment-System1/pull/465) → [#467](https://github.com/kco994553-star/Investment-System1/pull/467) → [#469](https://github.com/kco994553-star/Investment-System1/pull/469) → [#478](https://github.com/kco994553-star/Investment-System1/pull/478) → [#480](https://github.com/kco994553-star/Investment-System1/pull/480) → [#489](https://github.com/kco994553-star/Investment-System1/pull/489) → [#497](https://github.com/kco994553-star/Investment-System1/pull/497)
- [#454](https://github.com/kco994553-star/Investment-System1/pull/454) → [#464](https://github.com/kco994553-star/Investment-System1/pull/464) → [#465](https://github.com/kco994553-star/Investment-System1/pull/465) → [#467](https://github.com/kco994553-star/Investment-System1/pull/467) → [#469](https://github.com/kco994553-star/Investment-System1/pull/469) → [#478](https://github.com/kco994553-star/Investment-System1/pull/478) → [#480](https://github.com/kco994553-star/Investment-System1/pull/480) → [#489](https://github.com/kco994553-star/Investment-System1/pull/489) → [#498](https://github.com/kco994553-star/Investment-System1/pull/498) → [#515](https://github.com/kco994553-star/Investment-System1/pull/515)
- [#454](https://github.com/kco994553-star/Investment-System1/pull/454) → [#464](https://github.com/kco994553-star/Investment-System1/pull/464) → [#465](https://github.com/kco994553-star/Investment-System1/pull/465) → [#467](https://github.com/kco994553-star/Investment-System1/pull/467) → [#475](https://github.com/kco994553-star/Investment-System1/pull/475)
- [#459](https://github.com/kco994553-star/Investment-System1/pull/459) → [#461](https://github.com/kco994553-star/Investment-System1/pull/461)
- [#460](https://github.com/kco994553-star/Investment-System1/pull/460) → [#462](https://github.com/kco994553-star/Investment-System1/pull/462)
- [#474](https://github.com/kco994553-star/Investment-System1/pull/474) → [#476](https://github.com/kco994553-star/Investment-System1/pull/476)
- [#474](https://github.com/kco994553-star/Investment-System1/pull/474) → [#479](https://github.com/kco994553-star/Investment-System1/pull/479) → [#499](https://github.com/kco994553-star/Investment-System1/pull/499) → [#504](https://github.com/kco994553-star/Investment-System1/pull/504)
- [#482](https://github.com/kco994553-star/Investment-System1/pull/482) → [#500](https://github.com/kco994553-star/Investment-System1/pull/500)
- [#505](https://github.com/kco994553-star/Investment-System1/pull/505) → [#514](https://github.com/kco994553-star/Investment-System1/pull/514)
- [#509](https://github.com/kco994553-star/Investment-System1/pull/509) → [#512](https://github.com/kco994553-star/Investment-System1/pull/512)
- [#516](https://github.com/kco994553-star/Investment-System1/pull/516) → [#520](https://github.com/kco994553-star/Investment-System1/pull/520) → [#523](https://github.com/kco994553-star/Investment-System1/pull/523) → [#524](https://github.com/kco994553-star/Investment-System1/pull/524) → [#527](https://github.com/kco994553-star/Investment-System1/pull/527) → [#528](https://github.com/kco994553-star/Investment-System1/pull/528) → [#529](https://github.com/kco994553-star/Investment-System1/pull/529) → [#534](https://github.com/kco994553-star/Investment-System1/pull/534) → [#537](https://github.com/kco994553-star/Investment-System1/pull/537) → [#541](https://github.com/kco994553-star/Investment-System1/pull/541) → [#547](https://github.com/kco994553-star/Investment-System1/pull/547) → [#551](https://github.com/kco994553-star/Investment-System1/pull/551)
- [#516](https://github.com/kco994553-star/Investment-System1/pull/516) → [#520](https://github.com/kco994553-star/Investment-System1/pull/520) → [#523](https://github.com/kco994553-star/Investment-System1/pull/523) → [#524](https://github.com/kco994553-star/Investment-System1/pull/524) → [#527](https://github.com/kco994553-star/Investment-System1/pull/527) → [#528](https://github.com/kco994553-star/Investment-System1/pull/528) → [#529](https://github.com/kco994553-star/Investment-System1/pull/529) → [#534](https://github.com/kco994553-star/Investment-System1/pull/534) → [#537](https://github.com/kco994553-star/Investment-System1/pull/537) → [#542](https://github.com/kco994553-star/Investment-System1/pull/542)
- [#516](https://github.com/kco994553-star/Investment-System1/pull/516) → [#520](https://github.com/kco994553-star/Investment-System1/pull/520) → [#523](https://github.com/kco994553-star/Investment-System1/pull/523) → [#524](https://github.com/kco994553-star/Investment-System1/pull/524) → [#527](https://github.com/kco994553-star/Investment-System1/pull/527) → [#528](https://github.com/kco994553-star/Investment-System1/pull/528) → [#529](https://github.com/kco994553-star/Investment-System1/pull/529) → [#534](https://github.com/kco994553-star/Investment-System1/pull/534) → [#537](https://github.com/kco994553-star/Investment-System1/pull/537) → [#544](https://github.com/kco994553-star/Investment-System1/pull/544)
- [#516](https://github.com/kco994553-star/Investment-System1/pull/516) → [#520](https://github.com/kco994553-star/Investment-System1/pull/520) → [#523](https://github.com/kco994553-star/Investment-System1/pull/523) → [#525](https://github.com/kco994553-star/Investment-System1/pull/525)
- [#522](https://github.com/kco994553-star/Investment-System1/pull/522) → [#526](https://github.com/kco994553-star/Investment-System1/pull/526) → [#530](https://github.com/kco994553-star/Investment-System1/pull/530) → [#533](https://github.com/kco994553-star/Investment-System1/pull/533) → [#535](https://github.com/kco994553-star/Investment-System1/pull/535)
- [#522](https://github.com/kco994553-star/Investment-System1/pull/522) → [#526](https://github.com/kco994553-star/Investment-System1/pull/526) → [#530](https://github.com/kco994553-star/Investment-System1/pull/530) → [#533](https://github.com/kco994553-star/Investment-System1/pull/533) → [#536](https://github.com/kco994553-star/Investment-System1/pull/536) → [#538](https://github.com/kco994553-star/Investment-System1/pull/538) → [#550](https://github.com/kco994553-star/Investment-System1/pull/550)
- [#531](https://github.com/kco994553-star/Investment-System1/pull/531) → [#532](https://github.com/kco994553-star/Investment-System1/pull/532)

열린 PR로 직접 대응되지 않는 비기본 base:

- [#516](https://github.com/kco994553-star/Investment-System1/pull/516): `research/common-classification-base-20261107` @ `419c29770b91db8dae90b06194e30cbcbbe035a0`. 이 조사 목록에 해당 head의 열린 PR이 없으므로 중간 가지로 별도 보존·대조한다.

## 고정 head의 Git 대조 결과

- `git merge-base --is-ancestor`로 102개 head를 기본 가지와 대조했다. **현재 head 전체가 기본 가지 조상인 PR은 0개**다. 일부 cherry-pick·동등 패치가 이미 반영됐는지까지 뜻하지 않는다.
- 열린 PR 간 직접 base 관계 44개 중 **42개는 최신 부모 head가 자식 head의 조상**, 다음 **2개는 아니다**. 단순 가지 순서만 보고 병합하면 최신 부모 변경이 빠질 수 있다.

| 부모 → 자식 | 확인 | 후속 |
| --- | --- | --- |
| #417 → #430 | 최신 #417 head가 #430에 미포함 | 보존용 과거 calc와 재고정안 목적부터 합의 |
| #509 → #512 | 최신 #509 head가 #512에 미포함 | #509 후속 실패 수정과 navigation/2를 함께 대조 |

나머지 42개 직접 관계는 포함된다. 아래는 누적 통합 head에서 **현재 열린 PR head가 실제 조상으로 포함된 번호**다. API 본문의 과거 포함 주장과 분리해 검증했다.

| 통합 PR | 포함된 현재 열린 PR head |
| --- | --- |
| #519 | #454, #455, #464, #465, #467, #469, #478, #480, #489, #498, #505, #506, #507, #510, #511, #512, #513, #514, #515, #517, #518 |
| #522 | #454, #455, #464, #465, #467, #469, #478, #480, #485, #489, #493, #498, #505, #506, #507, #510, #511, #512, #513, #514, #515, #516, #517, #518, #519, #520, #521, #523 |
| #526 | #454, #455, #464, #465, #467, #469, #473, #478, #480, #485, #489, #493, #498, #505, #506, #507, #510, #511, #512, #513, #514, #515, #516, #517, #518, #519, #520, #521, #522, #523, #524, #525, #527 |
| #530 | #454, #455, #464, #465, #467, #469, #473, #478, #480, #485, #489, #493, #498, #505, #506, #507, #510, #511, #512, #513, #514, #515, #516, #517, #518, #519, #520, #521, #522, #523, #524, #525, #526, #527, #528, #529 |
| #533 | #454, #455, #464, #465, #467, #469, #473, #478, #480, #485, #489, #493, #498, #505, #506, #507, #510, #511, #512, #513, #514, #515, #516, #517, #518, #519, #520, #521, #522, #523, #524, #525, #526, #527, #528, #529, #530, #531, #532 |
| #536 | #454, #455, #464, #465, #467, #469, #473, #478, #480, #485, #489, #493, #498, #505, #506, #507, #510, #511, #512, #513, #514, #515, #516, #517, #518, #519, #520, #521, #522, #523, #524, #525, #526, #527, #528, #529, #530, #531, #532, #533 |
| #537 | #454, #464, #465, #467, #469, #478, #480, #489, #498, #505, #514, #515, #516, #520, #523, #524, #527, #528, #529, #534 |
| #538 | #454, #455, #464, #465, #467, #469, #473, #478, #480, #485, #489, #493, #498, #505, #506, #507, #510, #511, #512, #513, #514, #515, #516, #517, #518, #519, #520, #521, #522, #523, #524, #525, #526, #527, #528, #529, #530, #531, #532, #533, #534, #536 |
| #558 | 없음 — 선별 이식 여부는 별도 파일 대조가 필요 |

- #558이 이전 PR head를 조상으로 포함하지 않는 것은 선별 이식을 하지 않았다는 뜻이 아니다. 본문은 #536/#538/#550 선별 반영을 명시하며 이번 검사는 전체 commit 포함 여부만 검증했다.
- #557은 실제 8파일 중 JSON 가드·Python 시험을 포함한다. #558 본문은 25파일이라고 쓰지만 고정 base…head는 26파일이다. 제출 시점 수치와 현재 머리 차이이므로 Main이 본문을 갱신해야 한다.

## 본문에 명시된 추가 통합·계약 관계

base만으로는 아래 관계가 보이지 않는다. 본문에 적힌 특정 SHA의 포함 기록이며 최신 head 전체 포함으로 확장해서 해석하지 않는다.

| 묶음 | 본문 근거의 검토 순서 | 주의 |
| --- | --- | --- |
| 초기 연구 | #416 → #417; #430 → #417 재고정 제안 | #417 최신 보존 목적과 #430 최신 calc 재고정이 충돌하므로 자동 병합 금지 |
| 연구 입력 | #454 → #464 → #465 → #467 | 본문 인수 기준을 보존; 실행·공개 성과 승격과 별개 |
| 옛 비공개 UI | #484 → #488·#490 → #493 | #558은 5경로만 선택했으므로 #493 전부 대체로 세지 않음 |
| 섹터/정책 | #503 → #506; #505 → #507; #506·#507 → #510; #509·#512 → #511 | 생산자 계약과 화면 통합을 구분 |
| 공통 분류 | #505·#514 및 #498·#515 → #516의 중간 base → #520 → #523 → #524·#525 | #516의 base는 별도 중간 가지로, 단순 PR 한 줄 체인이 아님 |
| 11/07 통합 | #455 → #513 → #510 → #511 → #517 → #518 → #519; #516 공급자 추가 | 과거 제안 순서이며 DC-56 이후 전체 화면 묶음 병합 지시 아님 |
| 11/08 후속 | #519 + #516·#520·#523 + #521 + #485 → #522 → #526 | 인수 기준점 #519 보존; #522는 화면·계산이 섞인 누적 트리 |
| 분위/관계망 | #528·#529 → #530; #531 → #532; #530·#532 → #533 | 분포·receipt 반례가 후속 head에 들어갔는지 SHA별 대조 |
| 333→555 | #534 → #537; #535는 #536으로 대체; #533 → #536 → #538 | 333 중지. DC-56은 #536·#538의 엔진/계약만 추출하도록 지정 |
| KIS 연구→현행 | #537 → #541 → #547 → #551; #542 helper가 #547에 포함; #556은 canonical 분리 | #556은 555 전체 대체가 아님. 계산 모형·출력 계약을 혼합하지 않음 |
| 무기한 토큰·최소 비공개 | #538 → #550; #558은 #536/#538/#550에서 선별 | #558이 제외한 분류/매크로/뉴스/555 경로를 완료로 세지 않음 |
| 지금 우선 검토 | #557 결정/가드 범위 확인 → #556 생산자 ↔ #558 소비자 대조; #559 TARGET 예외 종료 | 오너 승인, 현재 head CI, 인증·정상본 보존 검증 후 Main이 처리 |

## 종료 제안 전 체크

1. “닫을 것”은 #267·#281·#305·#433·#495의 비채택 제안이다. 원문·시험 근거·필요한 독립 결함 수정이 다른 문서나 Git 이력에서 재열람 가능한지 먼저 확인한다.
2. #535 대체는 명시적이다. #519는 #522의 후속 통합 기준점으로 보존한다. 종료와 가지 삭제는 다른 작업이며 가지/태그/원결과를 삭제하지 않는다.
3. #437은 인계 허브라 유지 여부를 별도 결정한다. #493·#550·#547 등 부분 추출된 PR은 미반영 기능이 남아 있으므로 일괄 “대체됨” 처리하지 않는다.
4. #557은 “문서 전용”이라는 제목과 본문의 가드·시험 변경 서술이 다르다. 고정 diff에서도 해당 두 파일을 확인했으며 이 감사는 수정하지 않고 Main 검토 항목으로 남긴다.

## 감사 시점의 head 고정값

PR 본문은 과거 SHA를 포함할 수 있다. 재검토에는 아래 API head를 사용한다. `Draft`는 스냅샷 시점 상태이며 CI 성공 여부가 아니다.

| PR | head SHA | Draft | base…head 파일 수 |
| --- | --- | --- | ---: |
| #267 | `ad469e5c8d3bc2fe9d7eba13a91a8ca856be3fec` | 아니오 | 13 |
| #281 | `3b22cae1fc0893514a93381a43341323fd0e0eec` | 예 | 12 |
| #305 | `bbb7bb5525fabb7a9de5cec305e6f9cef5782833` | 예 | 9 |
| #392 | `f8307b7cb51f6446e48e7f90b217c631a7b9d8e3` | 아니오 | 30 |
| #416 | `ce6acdfa47e7b3eabb63f4673e6e1053f9c6a621` | 아니오 | 3 |
| #417 | `c68af2c0de4ccec55374082974097ad33045a640` | 예 | 36 |
| #418 | `ef745b96621b06802c7055eb64da76f64f2800db` | 예 | 9 |
| #430 | `56a0e8ce1157ba3fc41da68beaec3b6fd32fc841` | 아니오 | 103 |
| #432 | `26396d1f9f71706ae6deaa1ee51797bebb4d9ffc` | 예 | 34 |
| #433 | `d5fdf8905701b0f2fd8c568419306c9643bb0247` | 아니오 | 3 |
| #437 | `6c285ada873a39ef88da49c6ddfecf4578907c71` | 예 | 5 |
| #443 | `d05c79f4f2abfa52beacbab985fda8cec9f0041e` | 예 | 1 |
| #452 | `e9bce9f9ffd6b11ccd3904a45fbbb4cf4a59fbb1` | 예 | 3 |
| #454 | `ec1fa06cb0e881c248849fdf2af6fe64a3bc1cb4` | 예 | 28 |
| #455 | `dfa23e8a67e41af380bbc1b451d1ec2c23837a33` | 아니오 | 1 |
| #458 | `d2fdc4c7d49b5ffea451e67c60bbba536cc6a904` | 예 | 1 |
| #459 | `7ab5cd4d8a2d6e9f0a64ce5bfb15637b6366d56e` | 예 | 4 |
| #460 | `63d4c2b7f146e8310a6fa70fcadf6b0730d3cbbb` | 아니오 | 8 |
| #461 | `6d6fd7faad7415b2b0c2dbfc1a4361d73c688c6f` | 예 | 2 |
| #462 | `5c0b0859a774471c7cc8fee75b7f62b3ad4fc3cb` | 예 | 2 |
| #464 | `9fc8f7e586f39c13706cc6c41cc1f05a953c592f` | 예 | 20 |
| #465 | `3b1ad9ebc151ad0eece81a40a1d51938fdb66c14` | 예 | 10 |
| #467 | `ab6309637732f6ce4e7b42972f0e5e081511abf0` | 예 | 19 |
| #468 | `d86f8d56b4c6637a1a6e98795910fe1e76fa6a30` | 아니오 | 14 |
| #469 | `eecf69d6a43b67480c65bece8c4a02049bd9b699` | 예 | 10 |
| #472 | `75441936031e9abec3e9f27146cee39e264e0b92` | 예 | 4 |
| #473 | `02e3d44e9082e3d9a7b1df6e0e68cdb0634e4d95` | 예 | 8 |
| #474 | `572f0b5e9822086fa807b62abe8d4c688cd957f4` | 예 | 4 |
| #475 | `53256c83182beadeadf5e02f78b9b509d79a55bb` | 예 | 6 |
| #476 | `743fa5714b9e77b3f399ebdcbfc5c1b7dc2a7e49` | 예 | 4 |
| #477 | `a90a93f392310dff92ebf5dd5131f62c2ae68d19` | 예 | 5 |
| #478 | `419add34261b6d976f374e1e962015f8ceb4927e` | 예 | 5 |
| #479 | `b25dfa9c28319aa0f7eb8fa71da382789af823d2` | 예 | 11 |
| #480 | `de9d87e46d060cba79651b394e64915ccf139d45` | 예 | 45 |
| #482 | `b68725f47b64a8f81672ce757c3cd0c19324f919` | 예 | 4 |
| #483 | `864c40ea1beccee40d9f966ffede2ddb2e8d065c` | 예 | 7 |
| #484 | `f5dde90e614fe2a4bf1fb8200fc9b8a0cf0396f4` | 아니오 | 3 |
| #485 | `98918af1fbe07a04ae7da391422ae041466066ab` | 예 | 13 |
| #486 | `c3356d72679220a1e50ab6984514d633a47c60a6` | 예 | 2 |
| #487 | `65d062a4a9f57082697cfac56342d984913b23de` | 예 | 1 |
| #488 | `01a0c23e81aaa015b64775d097675729bc002eca` | 예 | 14 |
| #489 | `59eb33ca3b085eff3f1486c230a74408aeb2558b` | 예 | 13 |
| #490 | `77b875b08031116b17a06a071c2bfc6d1853e2f5` | 예 | 11 |
| #491 | `b51d521d21cf10439d258c639b51b59a50020a80` | 예 | 16 |
| #492 | `9dce17b7acb77c0604e9b927931e00481f9a4a0c` | 예 | 17 |
| #493 | `2a104798558a9acf027ae63421ff371b0bdf44eb` | 예 | 41 |
| #494 | `4a2b73b6e1e47fe25381e8ecf694d5ec3d52d097` | 예 | 9 |
| #495 | `009a692ba00f3b87df8308deeaa99ebea86a028b` | 예 | 6 |
| #496 | `a38607cd0ff69cd240285d6bcdeb6482d344b1cb` | 예 | 1 |
| #497 | `d4ece8da378587e72189923ada834c59a5e78d09` | 예 | 6 |
| #498 | `5597e25e0f1eef13432250d6ebfb440f7da152f5` | 예 | 10 |
| #499 | `e1f1f35dd91ca64f3640624e0e51e0cf52bdf00f` | 예 | 7 |
| #500 | `589fd9806094fd51b9163d3fc07cb879dda02935` | 예 | 4 |
| #501 | `f6a69a99bb1d1dd74c7f2b910804041053db4482` | 예 | 3 |
| #502 | `06e63afb7a3f4929e42c5a57b23216b3efb8f065` | 예 | 10 |
| #503 | `998414635aa4f1899748b1b76fc7ebf3ddc9d12f` | 예 | 8 |
| #504 | `41075615cca715e94396bcde56594f8159f333ee` | 예 | 8 |
| #505 | `e3df0c1ecb1ad7cda4593dffc55fa5d7ea78edd6` | 예 | 38 |
| #506 | `439f397ef7cbf9a380820729ba8a82ad1a364c15` | 예 | 20 |
| #507 | `f9101b7339b3c3d7becc414d7450626116391484` | 예 | 66 |
| #508 | `df1a9abb8c72ee57a7f7a50011bb0dbf9ffb116f` | 예 | 3 |
| #509 | `77a8265ee6c6569d88a583cb085984791e554861` | 예 | 23 |
| #510 | `934dd96a8f16424292712d6e4fd3ce006e0b0925` | 예 | 82 |
| #511 | `507d0d7736a0be2ce4f0d785518e6577af7a3722` | 예 | 67 |
| #512 | `37cef5845459f32a83881461147036d979fefa81` | 예 | 24 |
| #513 | `617e792b84d99950045079eb5e334802df8e995c` | 예 | 22 |
| #514 | `8a483471d02f7a9cfc0294117722cc01a32abbab` | 예 | 4 |
| #515 | `b6fd0112b5c3bfc5af9c28e4ae91d49d7b7b16dc` | 예 | 5 |
| #516 | `4cf2e037188e41e54f55c648057da661b77946df` | 예 | 32 |
| #517 | `9736db691ff95c38008b0bc86021908a4548b35d` | 예 | 11 |
| #518 | `6661ade6a67f78143351d5c8bc653bf9f64f17c6` | 예 | 8 |
| #519 | `d3e640bbc05baec3ba1af7146ce584ba9a7cb2e5` | 예 | 310 |
| #520 | `41f2a25be8399cd21b2fcf0c4a219ef078251320` | 예 | 15 |
| #521 | `20601aa98816cad653399af9d9d62ba76959ef9b` | 예 | 339 |
| #522 | `f680c7192924ce4726afd7a3f59acf8517de087f` | 예 | 374 |
| #523 | `6fc7a67307b027467eeabcad994c8f86887e79f0` | 예 | 5 |
| #524 | `fb80b67bcf9695b21fe1ec9dc7a6bd32af930fc5` | 예 | 18 |
| #525 | `731e46827bd548db53bf39464e64ff8e5acbc2f6` | 예 | 12 |
| #526 | `7b4a805b081e4ceffc185b935e59ec167c0202b4` | 예 | 87 |
| #527 | `e76d402bbc318c351476610c0a82b3c4548693bb` | 예 | 7 |
| #528 | `2ca567b23a1a9119e0986f95ae10fe0001c89715` | 예 | 16 |
| #529 | `9a51b4ae2cf95911f3d6077fcbc102799a9adeb9` | 예 | 108 |
| #530 | `a8ef3fb77516a06ede37cbcc915eefe47fa43a6d` | 예 | 170 |
| #531 | `b53b0ec0a1947528397e35713f63586903361adc` | 예 | 8 |
| #532 | `4ec8802d20955b7d989ae01d99d6a84bac53c200` | 예 | 14 |
| #533 | `2dc1202c320b810a29197f4751286c50475ccbae` | 예 | 28 |
| #534 | `fe29867cf1301e97912656ff03d3a9bf3a17fe64` | 예 | 49 |
| #535 | `f2ad42587f05c4461d216686cf38ee08c7ef39f6` | 예 | 61 |
| #536 | `307dddd59ddd2ecefbd84cddc58f6ad38a35d5f9` | 예 | 65 |
| #537 | `b550113a091853493e47d3e0cdfa8571b3175f48` | 예 | 224 |
| #538 | `9f1fdd584a02419db3eb34485819875c6c9268d3` | 예 | 233 |
| #541 | `eaf11777848adbc80ba819044bf572200220c646` | 예 | 28 |
| #542 | `637e4243432e55365d1976d977faff543a0a5c5b` | 예 | 8 |
| #544 | `4d6a173bff2dfb02fb6bb0492dd1689595c9ca85` | 예 | 9 |
| #547 | `1aa15601ec995e7e08c41fc0aee37a6ba60f39dd` | 예 | 24 |
| #550 | `52c0305903ad207d04bdc564cd95026a7508f17e` | 예 | 7 |
| #551 | `49968f41042732203a59a9957c10e877546a979f` | 예 | 2 |
| #555 | `bc07b979c8d6e49e7410acd6388ce36aaa30d1b2` | 예 | 4 |
| #556 | `2abdd286d83400fd2686a4f49eeb7d495f704689` | 예 | 21 |
| #557 | `f69104f06c9aa35d969fee941a3a24a778573854` | 예 | 8 |
| #558 | `280a0e5d741206b14635eb52f5b2a7b12e404c7a` | 예 | 26 |
| #559 | `996b838481950b859e767504b40bb72894f5a9e7` | 예 | 25 |
