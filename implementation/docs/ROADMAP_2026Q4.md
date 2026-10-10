# 투자시스템 2026년 4분기 전체 로드맵

기준일: **2026-10-09 UTC**. 기준 저장소: `kco994553-star/Investment-System1`. 기준 canonical: **`12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df`**, PR #87 병합 이후. 아래 코드·문서 근거 링크는 별도 명시가 없으면 이 SHA에 고정한다.

현재까지 완료된 것은 Track A의 동결 기준선, 일부 입력·후보 계산 코드, 기기 수동 시세·Google 시트 연결, Cockpit IA 문서와 탐색 구조다. **일일 실데이터를 네 분석 흐름에 연결하고 검증·게시하는 전체 운영 경로는 완료되지 않았다.** M1 입력 보존과 M2 가격 없는 Q·G 후보 계산의 코드 존재를 실데이터 성공·완전 QGV·LIVE로 올려 읽지 않는다. [C01] [C03] [C05] [C10] [C11]

이 로드맵은 **문서 전용 계획**이다. 수집기 실행, 앱/Worker 구현·배포, 예약 작업, 방법론·TARGET·Holdout 변경, 다른 PR 병합, ruleset 또는 `AUTONOMY_MODE` 변경의 승인이 아니다. Secret은 이름·확인된 존재 여부만 다루며 실제 개인 가격·V·시총 순위·토큰·보유정보를 기재하지 않는다. [C06] [C07] [C08]

## 상태를 읽는 기준

| 표시 | 의미 |
| --- | --- |
| 완료 | 표시한 범위의 산출물과 canonical 병합/확인 기록이 있다. 문서·코드·운영 완료를 각각 명시한다. |
| 진행 중 | 단계의 일부 산출물이 존재하지만 목표 범위가 남아 있다. 수집기나 예약 작업이 현재 실행 중이라는 뜻이 아니다. |
| 대기 | 문서에 기록된 사용자 조치·별도 후속 범위·정확한 의존 산출물을 기다린다. |
| 차단 | 현재 권리·PIT·계약·검증 조건으로 해당 경로를 통과할 수 없다. |

전체 프로젝트·네 흐름·UI·운영의 진행률: **측정 근거 없음**. 승인된 전체 범위와 분모가 없어 테스트 수·PR 수·차트 수를 완료율로 바꾸지 않는다. 기존 QGV vNext 문서도 전체 QGV 구현률을 산정할 수 없다고 구분한다. [C17]

과거 `CURRENT_HANDOFF`·Project Index의 “GitHub 업로드 불가”, “Artifact 0”, “Track A 미동결”은 뒤의 PR #3 통합 검증 기록으로 대체된 Track A 이력이다. 그 기록에 포함되지 않은 다른 트랙·현재 일일 운영까지 완료로 넓히지 않는다. 마찬가지로 #77/#81/#84/#85/#87 문서의 작성 당시 “미병합/승인 대기”는 아래 실제 병합 기록과 구분한다. [C01] [C02]

## canonical에 반영된 주요 산출물

| 범위 | 현재 상태와 경계 | PR / 병합 커밋 | 근거 |
| --- | --- | --- | --- |
| Track A 역사적 실데이터 기준선 | **완료 — FROZEN_VERIFIED**. 세 역사 기준일·Walk-Forward·보존 원문·회귀를 확인한 동결 기준선. strict zero-lookahead·현재 데이터·모델 승격의 증거는 아니다. | #3 / `bd6bf42bdd9c6274b595471c65e3482f37317f9c` (handoff 기록) | [C01] [C02] |
| 기기 ACTUAL·수동 시세·KRW 평가 | **완료 — 구현 범위**. 누락은 NOT_AVAILABLE, 개인 자료는 기기 보관. 브로커 연결·자동 시세와 분리한다. | [#70][P70] / `011b75648f48f2890736d37c4a354f57004cf1f0` | [C18] |
| 선택형 Google 시트와 CSP 수정 | **완료 — 구현 범위**. 기본 OFF, 버튼 조회, 기존 spreadsheets.readonly 토큰은 메모리 보관. 일반 앱 계정·계좌 연결 완료는 아니다. | [#73][P73] / `13e025b0e545fb3da14c15ce065a6a8e4a368eb0`; [#74][P74] / `eed718a0b5cef943ba669b8fe82bff24f07a5a19` | [C09] |
| Cockpit IA v1 | **완료 — 요구사항 문서·탐색 재배치**. 12개 화면의 데이터·세부 배치·390/1440 검증 전체 완료는 아니다. | [#72][P72] / `c8b9debecaeaebf392672c74f5bfd50b20217227`; [#75][P75] / `771a3bf67a330e72349591b4879891e03340d7c1` | [C09] [C10] |
| 리서치 프롬프트 | **완료 — 공개 안전 import·필드 안내 코드**. 독립 분석 점수나 검증 결과를 생성하는 엔진은 아니다. | [#76][P76] / `3f3eb3f8ba1dacb2cfebfe2ac0a83ab5d42c6dbc` | [C10] |
| KR/JP 재무 조사·파이프라인 설계 | **완료 — 조사·설계**. DART/EDINET 인증·수집·adapter 구현은 별도다. | [#77][P77] / `36c8982dd1d95075879899a770704dcaf853be24`; [#78][P78] / `c31b9556ad584d2132268f77bb98445416c7bca6` | [C03] [C19] |
| SEC M1 | **완료 — 제한된 수동 입력·보존·replay 코드**. 실제 수집 및 정확한 역사 최초 공개 시각 검증은 완료되지 않았다. | [#81][P81] / `c7dffd246fbada838e5a61b302d82aaa436489ef` | [C04] [C05] |
| SEC M2 가격 없는 Q·G v1 | **완료 — 오프라인 부분집합 후보 계산 코드**. `PROVISIONAL_RESEARCH`, candidate-only, 공개·완전 QGV·공식 순위 미검증. | [#86][P86] / `9febfab83974d3e9e02d971315e53b4e578ec3e6` | [C11] [C12] |
| DART 입력 준비·개인 가격 설계 | **완료 — 문서**. 키·계정·실제 호출·가격 차단 구현을 완료했다는 뜻은 아니다. | [#84][P84] / `34a9ee5e0a99861135e3ecbc88f919b5e4c9c4ca`; [#85][P85] / `11cf1f622a28dbee6a8ec1fd9e25492e3adc4cea` | [C06] [C07] |
| GSQ-008 본인 인증 방향 | **완료 — append-only 결정 문서**. Workers Free·scope·tokeninfo·CORS 실제 구현/배포는 대기다. | [#87][P87] / `12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df` | [C08] |

[#79][P79]와 [#82][P82]는 **CLOSED / 미병합**이다. 각 head `e72283470f6892b38f7033d6570b6eb8bfbf3461`, `2c190bd3f09444476ee76f16ed4cbd842983ebd2`의 작업을 별도의 canonical 완료분으로 합산하지 않는다. #78의 D6가 #77을 OPEN으로 설명하는 부분은 작성 당시 이력이며 #77의 현재 상태는 위 병합 기록이다.

## 일일 데이터 파이프라인 M0부터 M5

원래 단계와 진입 조건은 #78 설계 §6을 따른다. 이후 GSQ-007/008은 **무료·본인 전용 가격 경로**와 **가격 및 가격 기반 V·시총 순위·가격 결합 QGV 공개 금지**를 명시했다. 따라서 #78의 M2/M3 공개 가격·파생값 후보는 그대로 실행 가능한 현행 공개 계획이 아니다. 공개 SEC/DART 재무와 본인 전용 가격 처리를 분리한 후속 범위가 필요하다. [C03] [C07] [C08]

| 단계 | 현재 상태 | 남은 결과와 다음 단계 진입 조건 | 증거 |
| --- | --- | --- | --- |
| M0 현재 문서 | **완료 — 설계 병합** | D1~D6·가격 옵션·표시 요구가 기록됐다. #78 병합은 수집·운영 승인이 아니다. 최신 개인 가격 결정을 함께 적용한다. | #78, #85, #87 / [C03] [C07] [C08] |
| M1 SEC 입력/PIT | **진행 중 — 코드 완료, 운영 입력 대기** | #81 수동 US17 명시적 부분집합·불변 receipt·정정/replay 경로가 있다. 후속 운영에는 대상/연락 가능한 User-Agent·접근 예산·보존 위치·실제 입력 검증이 필요하다. `published_at=null`, 관측 취득 상한 `available_at`, `full_pit_historical=false`를 정확한 최초 공개 증명으로 바꾸지 않는다. | #81 / [C04] [C05] |
| M2 D2+D3 생산 후보 | **진행 중 — 가격 없는 Q·G 후보 코드 완료; 전체 연결 차단** | #86은 명시적 SEC receipt 부분집합 preview다. producer/registry/Pages 연결과 V·전체 QGV는 없다. 기존 v1·결측 규칙을 보존하고, 실제 입력·기간/통화·PIT·producer 검증 및 별도 게시 gate가 필요하다. PRICE→V 갱신 owner 정책도 미결이다. 가격 결합 결과는 최신 결정의 개인 경로로 한정한다. | #86 / [C11] [C12]; #78 / [C03] |
| M3 현재 전체 종목군/일일 공개 | **차단 — 완전성·권리·게시 조건 미충족** | 현재 전체 적격 후보 풀·dated identity/기업행위·PIT 주식수/가격·정상 동적 bundle guard가 필요하다. 현재의 Frozen 2024-12-31 구성은 오늘 Top500이 아니다. 가격 기반 순위 공개는 GSQ-007의 현행 금지와 충돌하므로 공개 membership-only 경로와 개인 순위를 먼저 구분해야 한다. | [C03] [C07] [C13] |
| M4 19종목 일봉·기기 AVG | **차단 — 실가격 공급·Worker 미연결** | 과거 일봉의 3시장 지원·세션·통화·basis·기업행위·허가를 확인해야 한다. Yahoo 무허가 자동 조회는 약관 부적합 판정을 유지한다. GSQ-008은 본인 인증 설계만 완료했다. 기기 AVG·내 거래 B/S는 개인 데이터로 처리하고 실제 기술 엔진 채택과 분리한다. | #83, #85, #87 / [C07] [C08] [C14] |
| M5 Macro·KR/JP 재무 | **대기 — 준비 문서; Macro 경로는 차단** | DART는 키/서비스 재개와 계정 ID·기간·단위·scope 실제 매핑 후 별도 adapter가 필요하다. EDINET은 조사 상태다. Macro는 권리·PIT·8축 producer·shape·게시 gate가 남아 있다. #77/#84 병합은 인증·수집의 성공이 아니다. | #77, #84 / [C06] [C19]; [C03] |

M1의 READY는 해당 입력 묶음·보존 검증 상태이며 모든 QGV 필드 완전성을 보장하지 않는다. M2는 `prices_used=false`, `candidate_only=true`, `publication_approved=false`, `publication_eligible=false`, `real_data_verified=false`, `full_pit_historical=false`다. 실행 성공·CI PASS·후보 JSON 존재를 LIVE 또는 공식 리더보드로 해석하지 않는다. [C05] [C11] [C36]

GSQ-008의 최신 본인 인증 방향은 **Workers Free만 사용, 비용0·카드없음·Access 미사용**이다. 기존 GIS의 `spreadsheets.readonly`에 `email` scope를 추가하고 Google access token을 Worker의 본인 확인에만 전달한다. Worker는 Google tokeninfo의 `aud`가 기존 OAuth 클라이언트 ID, `email`이 본인 이메일, `email_verified`가 참이며 만료 정보가 유효·미만료인지 모두 확인한다. 누락·불일치·미확인·만료·tokeninfo 오류는 거부하고, 가격 공급자에 토큰을 전달하지 않는다. 허용 Origin은 `https://kco994553-star.github.io` 하나이며 Origin만으로 인증하지 않는다. 토큰은 앱/Worker의 필요한 휘발성 메모리로만 취급하고 저장·로그를 금지한다. 비밀 접속 코드 대안은 보류다. 이 방향의 **문서 결정은 완료, 실제 구현·설정·인증·배포는 대기**이며 Yahoo 허가 부재 판정은 유지한다. [C08]

## 네 분석 흐름과 실제 데이터 연결

| 흐름 | canonical에서 확인되는 것 | 현재 실데이터/UI 연결 상태 | IA 목적 화면 | 다음 확인점 |
| --- | --- | --- | --- | --- |
| QGV | Track A Frozen 기준선, STANDARD v1·UNCALIBRATED, SEC M1, 오프라인 Q·G 부분집합 후보 코드 | **진행 중 — 제한된 코드 산출물**. 기본 공개 bundle의 QGV·리더보드는 NOT_AVAILABLE. M2 preview는 운영 producer가 아니다. | S02~S06, S01/S12 요약 | 실제 입력·결측·PIT·기간/통화와 publication gate. v1 상태를 calibration 완료로 바꾸지 않음. [C01] [C11] [C13] [C15] [C36] |
| 기술적 분석 | 구조 엔진·기존 chart renderer와 UI 상태 화면 | **차단 — 실제 모델/일봉 경로 미연결**. synthetic 구조 검증·renderer 존재는 실제 기술 분석이 아니다. 앱은 실제 차트 NOT_AVAILABLE을 표시한다. | S08, S04/S05 및 S01/S12 요약 | 허가된 가격·시장별 identity/basis와 비synthetic 실제 모델 생산자·검증. [C03] [C10] [C16] |
| 매크로 | 확정 v0.1.1, v0.1.4-CANDIDATE와 8축×6상태 요구 | **차단 — 권리·PIT·8축 생산·adapter 형태**. 앱 8축×6칸은 NOT_AVAILABLE이며 단일 Macro Score를 만들지 않는다. | S09, S04 및 S01/S12 요약 | 원기관별 권리·발표/vintage 시각·Stage3와 producer/adapter 정합. 후보 엔진 승격은 별도. [C03] [C09] [C10] |
| 검증·연구 | Track A 검증 기준선·실험/검증 계약·공개 리서치 프롬프트 | **진행 중 — 기준선·리서치 일부 존재**. 앱의 모의투자·백테스트·전진검증 결과 연결은 대기. Frozen 프롬프트의 사용 가능과 실험/성과 검증은 분리한다. | S10, 기업/코호트 Track Record, S01/S12 요약 | 실제 lineage·dataset split·PIT/OOS/Calibration·당시 예측/사후 관찰 연결. Holdout 보호 확인·사용 gate 유지. [C01] [C09] [C10] [C15] [C37] |

현재 기본 공개 builder는 `repository_bundle()`을 사용한다. 이 bundle은 **2024-12-31 FROZEN_SNAPSHOT Universe**만 로드하고 QGV·technical·macro·portfolio·leaderboard·news·relationships·changes 8개 section을 NOT_AVAILABLE로 둔다. 기기 ACTUAL·별도 TARGET 페이지·연구 도구의 개별 기능은 이 공개 bundle의 8개 section 완료와 별개다. [C13] [C16] [C34]

생산자 registry의 blocker 문자열은 현행 기본 경로의 동작 근거다. 해당 주석은 2026-10-01 감사에 기반하므로 최신 upstream 전체에 코드가 전혀 없다는 단정으로 확장하지 않는다. LIVE/FROZEN 게시에는 producer validation PASS와 비연구 상태가 필요하고 synthetic은 DEMO로만 허용된다. [C16] [C35]

## Cockpit IA v1 S01부터 S12

**완료된 범위는 화면 요구사항 기록과 5개 목적 메뉴/PC sidebar 재배치다.** IA 문서의 요구사항 상태는 `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`다. 사용자 보고인 private canvas 8축 수정 완료를 저장소의 12화면 재감사·앱 배포·모바일/PC 합격으로 바꾸지 않는다. 후속 기준은 390px·1440px이며 과거 390/1280 검증 기록과 구분한다. [C09] [C10] [C29]

| 화면 | 역할과 데이터 의존 | 남은 상태 |
| --- | --- | --- |
| S01 오늘 | QGV·기술·Macro·상위 통합 요약, TARGET/ACTUAL | **대기** — 네 원본 판단·시점·통합 규칙 근거의 연결 |
| S02 QGV 허브 | 내 투자·종목 찾기·시장 정보·성과 | **완료 — 허브 탐색 / 대기 — 상세 시안·실데이터**. 전략프로필·모델포트폴리오·관심기업·13F 상세 시안은 OPEN |
| S03 포트폴리오 | 분기 snapshot, GICS·유형·겹침, 8칸·12열 | **진행 중 — 기존 TARGET/기기 ACTUAL 기능 / 대기 — IA 전체 정합**. 정확한 8칸/12열 원문 매핑 미재감사 |
| S04 공통 종목 | 동일 기업 맥락, QGV·기술·Macro·뉴스·13F·가격 | **대기** — 각 원본 데이터와 식별·시점 정합. 가격·가격 기반 순위는 개인 경로 |
| S05 기업분석 | 사업·재무·이벤트·VMR·QGV·시나리오·Track Record | **대기** — SEC/DART facts와 차트/분석/검증 producer의 연결 |
| S06 리더보드 | 기본/내 프로필·재평가·과거순위·코호트 | **차단** — 공개 QGV upstream 미연결, 후보 preview 미승격. 필터8/열9의 세부 배치는 OPEN |
| S07 뉴스·관계망 | 사실·잠재 경로·영향 카드, Overlay OFF | **대기** — 원본/producer·세부 영향6항목 재감사. 잠재 경로를 확정 관계·점수 가산으로 만들지 않음 |
| S08 기술 | 차트·상태·실행·기록 | **차단** — 실제 일봉/모델 producer 미연결. 실행은 READ_ONLY 분석 |
| S09 매크로 | 공식8축×6상태·국면·신호→근거 | **차단** — 실제8축 입력/producer·shape/PIT·권리 미완료 |
| S10 검증·연구 | 모의투자·백테스트·전진검증·Track Record·실험·리서치 | **진행 중 — 리서치 기능 / 대기 — 실제 결과 연결**. 지표6개 정확한 배치 OPEN, Holdout 미선택 |
| S11 계정·기록·설정 | 기존 수동/Sheets 시세 인증과 기기 기록 | **완료 — 수동·선택형 Sheets 범위 / 대기 — 일반 계정·계좌/동기화·GSQ008 Worker** |
| S12 PC 홈 | S01 요약·sidebar·이탈표·변동 | **완료 — 탐색 구조 / 대기 — 1440px 전체 정합·원본 데이터** |

각 화면의 요구 근거: #72 IA [C09]. 현재 목적 메뉴·허브/상태 화면 코드: #75 [C10]. S03/S11 기기 수동 기능: #70 [C18], Sheets: #73/#74 [C09]. 개별 화면 상태는 위 범위에 한정하며 요구사항 표의 존재를 화면 전체 완성으로 세지 않는다.

## 차트 목록과 실제 제공 상태

현재 파일의 121개 ID와 JSON `latest_state`를 대조한 계수는 다음과 같다. **상태코드의 문서상 분포**이며 현재 실가격·구현·운영 완료율이 아니다. [C20] [C21]

| inventory 상태코드 | 전체121 | 공식 core81 | core 밖40 |
| --- | ---: | ---: | ---: |
| BASELINE_AUDIT | 88 | 73 | 15 |
| NON_CANONICAL_DEMO_VERIFIED | 5 | 5 | 0 |
| NON_CANONICAL_REFERENCE_DEMO_VERIFIED | 3 | 3 | 0 |
| CANONICAL_RENDERER_EXISTS | 2 | 0 | 2 |
| REQUIREMENT_IDENTIFIED_NOT_REAUDITED | 15 | 0 | 15 |
| CANDIDATE_SPEC_ONLY | 8 | 0 | 8 |
| 합계 | **121** | **81** | **40** |

공식 core81은 A01~A09(9), B01~B15(15), C01~C12(12), D01~D08(8), E01~E11(11), F01~F10(10), G01~G08(8), H01~H08(8)이다. 전체121은 **core81 + 저장소 기존/추가 요구24 + Macro 후보8 + Cockpit 추가 요구8**이다. L08은 기존 K01에 연결해 중복 행을 만들지 않으며 추가 행은 L01~L07·L09다. [C20] [C21]

core81의 기존 L1~L5 상태코드는 아래처럼 따로 보존돼 있다. 각 행의 여섯 코드 계수는81을 이룬다. `c`는 과거 canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`, `t`는 PR #40 trial `acaf1b5a82859ac2750a130ebe88f8b4d272ac66`이며 **현재 SHA의 새 감사가 아니다**. R=READY(해당 감사 범위), I=입력 의존 구현, P=PARTIAL, S=SPEC_ONLY/구현 미발견, H=PLACEHOLDER, U=미재감사/미확인으로 읽는다. [C20] [C22]

| core81 층 | 과거 c의 R/I/P/S/H/U | 과거 t의 R/I/P/S/H/U |
| --- | --- | --- |
| L1 원천 | 1/0/55/25/0/0 | 6/0/53/22/0/0 |
| L2 계산 | 1/5/33/42/0/0 | 4/7/34/36/0/0 |
| L3 계약 | 1/0/35/45/0/0 | 2/0/39/40/0/0 |
| L4 화면 | 0/0/0/0/81/0 | 0/0/20/0/61/0 |
| L5 검증 | 0/0/33/48/0/0 | 0/0/44/37/0/0 |

과거 all-five-R은 두 대상 모두0/81이다. renderer2개·noncanonical DEMO8개·요구사항 행은 실가격 연결이나 LIVE를 증명하지 않는다. **내 거래 B/S + AVG 표시 요구는 121개 밖의 별도 REQUIREMENT / NOT_IMPLEMENTED**이며, 기기 전용·표시 끄기 요구를 구현 완료로 세지 않는다. 현재 inventory viewer의 L 그룹 누락과 “81+24+8=113” 설명은 파일의121 분모와 다른 표시 정합 과제로 남긴다. [C14] [C20] [C21] [C22]

## Gate A와 자율운영 경계

현재 canonical의 `AUTONOMY_MODE`는 **READ_ONLY**다. 마지막 게시된 Main owner hard-guard 기록은 **2026-10-08T11:13:57Z / ref `59cc73a005196f73e92af8c47c594a9da8341a6c` / CDR038**이며 아래 판정을 담는다. 이 owner register는 현재 canonical에 포함되지 않아, 해당 판정을 **현재 SHA의 전체 재검증 결과로 승격하지 않는다**. [C23] [H01]

| gate | 마지막 게시 owner 판정 | canonical 12b5에서의 해석과 남은 조건 |
| --- | --- | --- |
| HG01 | **완료 — VERIFIED(해당 기록 범위)** | 현재 전체 runtime/kill behavior 재판정 근거 없음. 현재 READ_ONLY 값 확인과 구분한다. |
| HG02 | **진행 중 — PARTIAL_VERIFIED** | 인증된 canary 삭제 거부 증거·전체 executor identity/refusal matrix가 남아 있다. repository guard와 GitHub branch/ruleset 강제 검증은 별개다. |
| HG03 | **진행 중 — PARTIAL_VERIFIED** | actual E2E는 WAIT_PRODUCT_RUNTIME_CAPABILITY, PAUSE wake-up은 NOT_RUN으로 남아 있다. |
| Gate A 전체 | **차단 — 마지막 게시 CLOSED / freeze ACTIVE** | 현재 canonical 전체 PASS 근거 없음. READ_ONLY를 RUN이나 unattended 실행 승인으로 바꾸지 않는다. |

2026-10-05 scoped QGV handoff의 HG01~03 NOT_VERIFIED는 더 오래된 `Global1596649` intake 기록이다. 10-08 owner 기록보다 최신 판정으로 사용하지 않는다. 그 handoff의 watcher-enabled/executor-paused·canary0/2도 해당 과거 범위이며 현재 scheduler 설정·실행 증거를 대신하지 않는다. [C24] [H01]

canonical `.github/workflows/autonomy-gate-a.yml`의 범위는 repository guard 단위 검사, 비교-base, Frozen/history/evidence diff, mode readback이다. config도 repository guard가 HG02에 **필요하지만 충분하지 않다**고 명시한다. 체크 성공·모드 값 허용·readback만으로 HG01~03 runtime 또는 전체 GateA PASS를 주장하지 않는다. [C25] [C26]

## FPIA F1부터 F25

F1~F25에는 서로 다른 두 범위가 있다. **외부 source inventory**는 ref `59cc73a005196f73e92af8c47c594a9da8341a6c`, 작성 **2026-10-08T10:52:32.084651Z**, 대상 PR #47 stacked verifier `7215a9f60ad7128b1748f405051eac684298614f`다. 25개 모두 **FIXED_RECORDED**로 기록됐지만 `canonical_adoption=false`다. 이는 외부 code repair 기록이며 현재 canonical의25개 수정 완료 선언이 아니다. 관련 PR [#42](https://github.com/kco994553-star/Investment-System1/pull/42)·[#46](https://github.com/kco994553-star/Investment-System1/pull/46)·[#47](https://github.com/kco994553-star/Investment-System1/pull/47)은 기준일 현재 **OPEN / 미병합**이다. [H02] [H03]

현재 canonical에 있는 triage는 별도의 과거 부분집합 후보 `e3619846d77176d280321826ecd0d8f2c8485a30`와 외부 verifier `7215a9f...`를 대조한 기록이다. **25개 모두 LATER**, 재현된 해당 후보 implementation blocker0개다. 아래 “대기”는 이 기록의 LATER를 뜻하며 25개 새로운 미수정 버그를 뜻하지 않는다. [C27]

| ID | 기록된 수정 범위 | 외부 fix commit / 관련 PR | canonical 보존 triage |
| --- | --- | --- | --- |
| [F1](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L19) | 실행 파일명 인식 | [`2135962a`](https://github.com/kco994553-star/Investment-System1/commit/2135962a1e6fd19c3acd220a30c6464431eddf95) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42), [#46](https://github.com/kco994553-star/Investment-System1/pull/46) | **대기 — LATER** |
| [F2](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L38) | workflow identity 위장 | [`11d2f25e`](https://github.com/kco994553-star/Investment-System1/commit/11d2f25ef8bef3459ca969f50eec190099f15ecb) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F3](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L57) | literal invocation·도달 source | [`11d2f25e`](https://github.com/kco994553-star/Investment-System1/commit/11d2f25ef8bef3459ca969f50eec190099f15ecb) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F4](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L76) | job/service container 목록 | [`2135962a`](https://github.com/kco994553-star/Investment-System1/commit/2135962a1e6fd19c3acd220a30c6464431eddf95) / [#46](https://github.com/kco994553-star/Investment-System1/pull/46) | **대기 — LATER** |
| [F5](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L95) | 환경경로·사용자와 hash | [`11d2f25e`](https://github.com/kco994553-star/Investment-System1/commit/11d2f25ef8bef3459ca969f50eec190099f15ecb) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F6](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L114) | run metadata·출력 취급 | [`11d2f25e`](https://github.com/kco994553-star/Investment-System1/commit/11d2f25ef8bef3459ca969f50eec190099f15ecb) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F7](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L133) | fetch 거부 parsing | [`11d2f25e`](https://github.com/kco994553-star/Investment-System1/commit/11d2f25ef8bef3459ca969f50eec190099f15ecb) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F8](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L152) | Track C namespace 분류 | [`11d2f25e`](https://github.com/kco994553-star/Investment-System1/commit/11d2f25ef8bef3459ca969f50eec190099f15ecb) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F9](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L171) | verifier provenance 목록 | [`11d2f25e`](https://github.com/kco994553-star/Investment-System1/commit/11d2f25ef8bef3459ca969f50eec190099f15ecb) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F10](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L190) | 기존 CI의 PyYAML 의존 | [`523e702a`](https://github.com/kco994553-star/Investment-System1/commit/523e702a806a718d163cfbf62aa3fc29d8c3ef3c) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F11](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L209) | compound evidence identity | [`a3e3f6cf`](https://github.com/kco994553-star/Investment-System1/commit/a3e3f6cf5452d056de2df7845a17014765aa3ff3) / [#46](https://github.com/kco994553-star/Investment-System1/pull/46) | **대기 — LATER** |
| [F12](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L228) | D002 literal 자기제약 | [`6fea6c7f`](https://github.com/kco994553-star/Investment-System1/commit/6fea6c7f0a191a4e621941ce3f6a7cac83a7f3d6) / [#46](https://github.com/kco994553-star/Investment-System1/pull/46) | **대기 — LATER** |
| [F13](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L247) | 상대/동적 import scope | [`50fa7f49`](https://github.com/kco994553-star/Investment-System1/commit/50fa7f49080b3fa3d1808f9745d8f97770d1c9df) / [#47](https://github.com/kco994553-star/Investment-System1/pull/47) | **대기 — LATER** |
| [F14](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L266) | pyw·확장자 없는 실행파일 | [`50fa7f49`](https://github.com/kco994553-star/Investment-System1/commit/50fa7f49080b3fa3d1808f9745d8f97770d1c9df) / [#47](https://github.com/kco994553-star/Investment-System1/pull/47) | **대기 — LATER** |
| [F15](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L285) | workflow의 checkout 대상 | [`50fa7f49`](https://github.com/kco994553-star/Investment-System1/commit/50fa7f49080b3fa3d1808f9745d8f97770d1c9df) / [#47](https://github.com/kco994553-star/Investment-System1/pull/47) | **대기 — LATER** |
| [F16](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L304) | workflow/source identity | [`50fa7f49`](https://github.com/kco994553-star/Investment-System1/commit/50fa7f49080b3fa3d1808f9745d8f97770d1c9df) / [#47](https://github.com/kco994553-star/Investment-System1/pull/47) | **대기 — LATER** |
| [F17](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L323) | PR47 native CI 회귀 | [`7215a9f6`](https://github.com/kco994553-star/Investment-System1/commit/7215a9f60ad7128b1748f405051eac684298614f) / [#47](https://github.com/kco994553-star/Investment-System1/pull/47) | **대기 — LATER** |
| [F18](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L342) | shallow Git·fetch 실패 | [`465354a6`](https://github.com/kco994553-star/Investment-System1/commit/465354a6479810a175fbefe32ef2c993b1e214c2) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F19](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L361) | Frozen tool canonical 전제 | [`465354a6`](https://github.com/kco994553-star/Investment-System1/commit/465354a6479810a175fbefe32ef2c993b1e214c2) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F20](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L380) | V ancestry 없는 A_V | [`465354a6`](https://github.com/kco994553-star/Investment-System1/commit/465354a6479810a175fbefe32ef2c993b1e214c2) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F21](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L399) | stdout/stderr 원문 보존 | [`465354a6`](https://github.com/kco994553-star/Investment-System1/commit/465354a6479810a175fbefe32ef2c993b1e214c2) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F22](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L418) | AC32 attribution·job 충돌 | [`465354a6`](https://github.com/kco994553-star/Investment-System1/commit/465354a6479810a175fbefe32ef2c993b1e214c2) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F23](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L437) | trigger·subject/register/artifact | [`50fa7f49`](https://github.com/kco994553-star/Investment-System1/commit/50fa7f49080b3fa3d1808f9745d8f97770d1c9df) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42), [#47](https://github.com/kco994553-star/Investment-System1/pull/47) | **대기 — LATER** |
| [F24](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L456) | Frozen byte-only 범위 표시 | [`465354a6`](https://github.com/kco994553-star/Investment-System1/commit/465354a6479810a175fbefe32ef2c993b1e214c2) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |
| [F25](https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L475) | authority transport 환경 표시 | [`babf0a41`](https://github.com/kco994553-star/Investment-System1/commit/babf0a41dd8a740190743ee1e27289b17d8118d3) / [#42](https://github.com/kco994553-star/Investment-System1/pull/42) | **대기 — LATER** |

**코드 수정·fixture/도구 검증·fail-closed 정책·운영 수용을 분리한다.** 외부 inventory의 exact-head CI 재사용은 그 도구와 기존 회귀 범위의 기록이고 전용 Tier1/Tier2 Track C job은 SKIPPED다. canonical에는 해당 FPIA 구현/fixture/workflow 전체가 없어 현재 코드·fixture 전체 PASS를 주장하지 않는다. F13·F14·F23은 보수적인 applicability/trigger 범위를 강제한 **수정된 fail-closed 규칙**이며, 정상적인 scope 거부를 세 버그의 재발로 바꾸지 않는다. [H02] [C27]

별도 formal acceptance blocker는 과거 후보 기준 **1개**다: applicability BLOCKED, FPIA NOT_RUN, integration acceptance BLOCKED, `root_final_head=null`. 외부 기록도 독립적인 exact verifier/launcher/runtime receipt·authenticated compound 실행·dynamic/transitive/external coverage 또는 enforced isolation·GIE/실제 assembled merge acceptance를 OPEN/NOT_RUN으로 남긴다. **현재 canonical 전체 FPIA는 미검증(NOT_VERIFIED)으로 관리하며, 이는 현재 head의 감사 결과 코드가 아니라 재판정 근거가 없다는 로드맵 표시다. 전체 PASS 또는25/25 운영 완료의 근거는 없다.** 과거 후보의 실제 `fpia_status=NOT_RUN` 및 항목별 `LATER`는 위 기록 그대로 구분한다. [C28] [H03]

## 사용자 결정과 의존 작업 대기 목록

| 항목 | 상태 | 현재 확인된 사실 / 다음 조치 | 근거 |
| --- | --- | --- | --- |
| DART 서비스·키 | **대기** | 사용자는 **2026-10-11 18:00 이후** `DART_API_KEY` 등록 예정이라고 기록했다. 공지 시간대는 **미명시**다. 예정 시각 도달을 실제 재개/등록/성공으로 간주하지 않고, 실제 재개·등록 여부를 이름·존재만으로 확인한다. 이번 문서는 Secret 등록 상태를 조회하지 않았다. | #84 / [C06] |
| DART adapter | **대기** | 한미1회사 account_id·CFS/OFS·기간·통화/scale·revision·receipt가 실제 근거로 검증된 후 별도 후속 구현 범위. 현재 승인 계정 ID 목록0개를 추정으로 채우지 않는다. | [C06] [C33] |
| Yahoo 접근 허가 | **차단** | **무허가 자동 조회 부적합** 판정을 사용자가 인지·수용했다. 개인·무료·저빈도·휘발성 처리 및 Worker 인증 결정은 공급자 허가를 대신하지 않는다. 허가된 경로의 근거 또는 조건이 확인된 fallback이 필요하다. | #85/#87 / [C07] [C08] |
| Worker 구현·배포 | **대기** | GSQ008은 Workers Free 비용0·카드없음, GIS email 추가·기존 readonly scope 유지, access token→Worker→tokeninfo 검증, 단일 허용 Origin을 문서화했다. 실제 구현·설정·인증 호출·가입·배포는 별도 후속 범위다. 배포일은 미정이다. | #87 / [C08] |
| KRX·대체 가격 조건 | **대기** | KRX 키 보유와 적용 조건은 사용자 확인 대기. Tiingo(미국)/KRX(한국)/본인 Sheet 현재가/수동은 지원·권리·무료 한도 확인 후만 대체 후보로 삼는다. 실제 키·계정을 조회해 확인하지 않았다. | #85 / [C07] |
| 공개 가격·파생값 경계 | **차단 — 완료 감사 근거 없음** | 최신 금지와 기존 tracked Frozen 원문·rank projection·artifact/stdout 경로 사이의 gap이 문서에 기록됐다. membership-only와 개인 처리 분리의 구체 범위·보호 이력 보존·회귀 검증이 필요하다. 문서 병합과 기존 hash guard PASS는 새 경계 충족 증거가 아니다. | [C07] |
| QGV v2 시작 시점 | **대기 — 일정 미확정** | v2는 v1과 별도로 보존한다. 먼저 Holdout 보호 상태를 명시 확인하고 PIT/OOS/Calibration 증거와 별도 사용자 결정이 필요하다. 이 저장소 근거만으로 착수일·승인·완료를 만들지 않는다. | [C15] |
| Holdout 보호·사용 | **대기** | 보호 상태 확인이 선행 조건이며 현재 문서/IA는 기간을 선택·소비하지 않았다. v2 계획과 S10 화면을 Holdout 사용 선택으로 취급하지 않는다. | [C09] [C15] |
| PRICE→V·게시/만료 정책 | **대기** | 가격 변경시 V 재계산·producer expiry/usable_until·게시 적격성은 owner의 별도 결정 사항이다. 실행일로 기존 as_of를 바꾸지 않는다. | [C03] |
| Macro 권리·실데이터/shape | **차단** | FRED/원기관·각 시리즈의 저장·변환·재배포·AI 범위 공식 확인, PIT·8축·adapter 정합이 남아 있다. BLS/BEA 후보 검토가 공급자 변경 승인은 아니다. | [C03] [C31] |
| IA 세부 시안·원문 매핑 | **대기** | 전략프로필·모델포트폴리오·관심기업·13F 상세 및 8칸/12열·8필터/9열·영향6·지표6의 정확한 배치를 확인한다. private canvas를 임의 재설계하거나 공개하지 않는다. | [C09] |

이는 문서에 확인된 의존 목록이다. “진행해도 된다”는 실행 승인이나 사용자의 새 일정 약속을 뜻하지 않는다.

## 다음 4주 우선순위 제안

아래 주차는 **순서 제안**이며 시작일·완료일·예약 실행 약속이 아니다. 앞 단계의 통과 근거가 없는 후속 작업은 그 의존 지점에서 대기하고, 독립된 문서·검증 준비는 분리할 수 있다.

| 순서 | 우선 범위 | 먼저 두는 이유 | 리뷰 가능한 종료 조건 |
| --- | --- | --- | --- |
| 1주차 | 현행 공개 가격·파생값 경계의 범위 확정과 감사 계획, M1 입력 실제 검증 계획, GateA/FPIA 현행 근거 정리 | 최신 GSQ007/008과 기존 공개 경로의 gap을 먼저 명확히 해야 개인 가격·일일 공개 연결을 잘못 확대하지 않는다. GateA는 과거 부분 검증을 현재 전체 PASS로 가져오면 안 된다. | 보호 이력 보존 방식·membership-only/개인 분리 범위, 허용 입력/대상·receipt/PIT 확인 항목, current-head gate 근거/미확인 목록이 확정된 별도 검토 결과. [C05] [C07] [C08] |
| 2주차 | SEC M1→가격 없는 Q·G 후보의 실제 입력·기간/통화·결측 검증 준비; DART 서비스/키 확인 후 한미 매핑 준비 | #81/#86 코드가 이미 있으므로 새 방법론보다 실제 입력이 어디까지 뒷받침하는지 확인하는 편이 네 흐름의 upstream 의존을 줄인다. DART 예정 시각만으로 인증 성공을 가정하지 않는다. | 지정 부분집합의 custody/replay·취득 전 cutoff 차단·raw/factor 결측 trace·연구 상태 보존 및 DART 실제 재개/키 존재/계정 매핑 근거의 분리된 결과. [C05] [C06] [C11] |
| 3주차 | 허가된 개인 가격 경로와 GSQ008 인증의 구체 구현 검토, IA 한 흐름의 작은 연결 범위 선정 | Worker 인증 가능성과 공급자 접근 허가는 독립 조건이다. 작은 범위에서 3시장 identity·basis와 유출 경계를 확인한 뒤19종목/500종목의 지원 범위를 별도로 검증한다. | 허가/지원/비용0 조건, tokeninfo fail-closed·Origin·토큰 무저장/무로그 조건, 기기 AVG/개인 마커와 공개 bundle 분리, 선택한 화면의 데이터/빈 상태 검증 범위. [C07] [C08] [C09] |
| 4주차 | 네 흐름 producer·상태·계약 정합과 390/1440 IA 검증 계획; 검증 split/Holdout 보호·v2 진입조건 정리 | 입력이 있어도 실제 엔진·Macro shape·게시 gate가 남는다. 데이터 가용성과 모델 검증을 구분해야 S01/S12 요약·S10 성과가 근거를 넘어가지 않는다. | 네 흐름의 as_of/provenance·LIVE/Frozen/DEMO/N.A 매핑, Macro8축×6상태 결측 보존, 검증 결과 연결 계획과 Holdout 보호 확인 기록. v2는 별도 결정 전 v1과 분리. [C03] [C09] [C13] [C15] [C16] |

## 근거 링크

canonical 고정 링크는 `12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df`의 경로와 줄 앵커를 가리킨다. PR 링크는 병합 여부·merge commit의 출처이며 이후 PR 변동이나 새 데이터는 이 문서의 기준 밖이다. 과거 audit/후보 결과를 인용할 때는 그 결과의 원래 대상 SHA를 본문에 함께 적는다.

[C01]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/Investment-System1%20%C2%B7%20CURRENT_HANDOFF.md#L48-L50

- [C01] Investment-System1 · CURRENT_HANDOFF.md L48-50 — Track A 통합 검증

[C02]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/Investment%20System%20%C2%B7%20Project%20Index.md#L111-L113

- [C02] Investment System · Project Index.md L111-113 — 프로젝트 흐름·Track A 후속 통합 기록

[C03]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/daily_data_pipeline/PIPELINE_DESIGN.md#L296-L333

- [C03] implementation/docs/daily_data_pipeline/PIPELINE_DESIGN.md L296-333 — M0~M5 진입 조건·남은 결정

[C04]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/daily_data_pipeline/M1_SEC_INPUTS_PLAN.md#L29-L55

- [C04] implementation/docs/daily_data_pipeline/M1_SEC_INPUTS_PLAN.md L29-55 — M1 구현 계획의 완료 항목·모의 검증 범위

[C05]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/daily_data_pipeline/M1_SEC_INPUTS.md#L3-L70

- [C05] implementation/docs/daily_data_pipeline/M1_SEC_INPUTS.md L3-70 — M1 수동 범위·관측 시각·과거 PIT 제한

[C06]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/daily_data_pipeline/DART_CONNECTION_READINESS.md#L8-L23

- [C06] implementation/docs/daily_data_pipeline/DART_CONNECTION_READINESS.md L8-23 — DART 키/점검 대기·인수 범위; 매핑/미검증은 L98~128

[C07]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/daily_data_pipeline/PRIVATE_FREE_PRICE_PATH_RESEARCH.md#L8-L46

- [C07] implementation/docs/daily_data_pipeline/PRIVATE_FREE_PRICE_PATH_RESEARCH.md L8-46 — 개인 가격·파생값 경계와 공개 gap

[C08]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md#L177-L248

- [C08] implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md L177-248 — GSQ007/008와 문서 전용 결정

[C09]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/frontend_ia_v1/COCKPIT_IA_v1.md#L26-L176

- [C09] implementation/docs/frontend_ia_v1/COCKPIT_IA_v1.md L26-176 — S01~S12 요구사항과 상세/검증 경계

[C10]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/product/web_assets/app.js#L319-L409

- [C10] implementation/src/investment_system/product/web_assets/app.js L319-409 — 현재 앱의 소비 화면·목적 허브·빈 상태

[C11]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/qgv/sec_m2.py#L314-L339

- [C11] implementation/src/investment_system/qgv/sec_m2.py L314-339 — M2 후보 상태와 결측/적격성 한계

[C12]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/tools/sec_m2_qg.py#L1-L5

- [C12] implementation/tools/sec_m2_qg.py L1-5 — 수동 오프라인·private output 범위

[C13]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/product/web_mvp.py#L72-L90

- [C13] implementation/src/investment_system/product/web_mvp.py L72-90 — Frozen Universe와8개 NOT_AVAILABLE 기본 bundle

[C14]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/experiments/chart-contract-v0.1/CHART_INVENTORY.md#L216-L218

- [C14] implementation/experiments/chart-contract-v0.1/CHART_INVENTORY.md L216-218 — core/121 밖의 기기 전용 B/S·AVG 요구

[C15]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/qgv_scoring_standard/QGV_SCORING_STANDARD_v1.md#L156-L179

- [C15] implementation/docs/qgv_scoring_standard/QGV_SCORING_STANDARD_v1.md L156-179 — v1 검증 범위·v2/Holdout 선행 조건

[C16]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/producers/registry.py#L91-L101

- [C16] implementation/src/investment_system/producers/registry.py L91-101 — 현재 default unavailable 사유; 계약 게시 조건은 별도 C35

[C17]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/qgv_common_contract_vnext/STATUS.md#L62-L78

- [C17] implementation/docs/qgv_common_contract_vnext/STATUS.md L62-78 — 설계/런타임/전체 진행률의 분리

[C18]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/manual_quotes_owner/README.md#L10-L49

- [C18] implementation/docs/manual_quotes_owner/README.md L10-49 — 기기 ACTUAL·수동 시세 구현 범위

[C19]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/fundamentals_sources/KR_JP_FILINGS_RESEARCH.md#L1-L24

- [C19] implementation/docs/fundamentals_sources/KR_JP_FILINGS_RESEARCH.md L1-24 — KR/JP 조사·권리·인증 조건

[C20]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/experiments/chart-contract-v0.1/CHART_INVENTORY.md#L1-L214

- [C20] implementation/experiments/chart-contract-v0.1/CHART_INVENTORY.md L1-214 — 121/core81 목록·최신 추가/보존 baseline

[C21]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/experiments/chart-contract-v0.1/chart_inventory.json#L1-L61

- [C21] implementation/experiments/chart-contract-v0.1/chart_inventory.json L1-61 — 121/core81 분모·baseline 계수·요구사항 경계

[C22]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/experiments/chart-contract-v0.1/inventory_app.js#L3-L19

- [C22] implementation/experiments/chart-contract-v0.1/inventory_app.js L3-19 — R/I/P/S/H/U 정의·113 설명과 L 그룹 표시 gap

[C23]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/coordination/governance/AUTONOMY_MODE#L1

- [C23] implementation/docs/coordination/governance/AUTONOMY_MODE L1 — 현재 READ_ONLY

[C24]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/CURRENT_HANDOFF.md#L1-L24

- [C24] implementation/docs/qgv_common_contract_vnext/architecture_reconciliation_work/CURRENT_HANDOFF.md L1-24 — 과거 Global159 intake·운영 상태 증거 제한

[C25]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/.github/workflows/autonomy-gate-a.yml#L10-L42

- [C25] .github/workflows/autonomy-gate-a.yml L10-42 — repository guard CI의 범위

[C26]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/coordination/governance/AUTONOMY_GUARD_CONFIG.v1.json#L4-L26

- [C26] implementation/docs/coordination/governance/AUTONOMY_GUARD_CONFIG.v1.json L4-26 — mode·repository guard와 HG02 강제의 구분

[C27]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L3-L16

- [C27] implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json L3-16 — 과거 부분집합 후보25LATER·fixed fail-closed

[C28]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json#L496-L505

- [C28] implementation/docs/integration_candidate_v1_1_20261008/F1_F25_TRIAGE.json L496-505 — 과거 후보 별도 acceptance blocker1

[C29]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/frontend_ia_v1/DESIGN_SOURCE.md#L5-L11

- [C29] implementation/docs/frontend_ia_v1/DESIGN_SOURCE.md L5-11 — 디자인 SSoT·private 재감사 경계

[C30]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/daily_data_pipeline/PIPELINE_DESIGN.md#L25-L38

- [C30] implementation/docs/daily_data_pipeline/PIPELINE_DESIGN.md L25-38 — 현재 연결점·producer/shape/공개 경로

[C31]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/daily_data_pipeline/PIPELINE_DESIGN.md#L98-L181

- [C31] implementation/docs/daily_data_pipeline/PIPELINE_DESIGN.md L98-181 — QGV PRICE→V·기술/Macro 권리·PIT/shape 경계

[C32]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/daily_data_pipeline/PIPELINE_DESIGN.md#L42-L96

- [C32] implementation/docs/daily_data_pipeline/PIPELINE_DESIGN.md L42-96 — 현재500 종목군·SEC 입력/PIT 조건

[C33]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/daily_data_pipeline/DART_CONNECTION_READINESS.md#L98-L128

- [C33] implementation/docs/daily_data_pipeline/DART_CONNECTION_READINESS.md L98-128 — DART account_id 미확보·raw mapping/소비 gate

[C34]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/tools/build_pages_cockpit.py#L16

- [C34] implementation/tools/build_pages_cockpit.py L16 — 공개 builder repository_bundle 호출

[C35]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/producers/contract.py#L189-L202

- [C35] implementation/src/investment_system/producers/contract.py L189-202 — synthetic DEMO·LIVE/Frozen validation/연구 상태 제한

[C36]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/qgv_scoring_standard/QGV_SCORING_STANDARD_v1.md#L3-L19

- [C36] implementation/docs/qgv_scoring_standard/QGV_SCORING_STANDARD_v1.md L3-19 — STANDARD v1 UNCALIBRATED·forward-only 채택

[C37]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/validation/integrated.py#L25-L33

- [C37] implementation/src/investment_system/validation/integrated.py L25-33 — 통합 검증 skeleton·비Official/비실데이터 상태

[H01]: https://github.com/kco994553-star/Investment-System1/blob/59cc73a005196f73e92af8c47c594a9da8341a6c/implementation/docs/coordination/governance/AUTONOMY_HARD_GUARD_GAPS_v1.1.md#L1-L3

- [H01] **외부 과거 ref `59cc73a005196f73e92af8c47c594a9da8341a6c`** / implementation/docs/coordination/governance/AUTONOMY_HARD_GUARD_GAPS_v1.1.md L1-3 — Main owner의 CDR038 마지막 게시 GateA 판정; 현재 canonical에 없는 owner 문서

[H02]: https://github.com/kco994553-star/Investment-System1/blob/59cc73a005196f73e92af8c47c594a9da8341a6c/implementation/docs/coordination/evidence/main_fpia_recorded_defects_2026-10-08/INVENTORY.json#L3-L34

- [H02] **외부 과거 ref `59cc73a005196f73e92af8c47c594a9da8341a6c`** / implementation/docs/coordination/evidence/main_fpia_recorded_defects_2026-10-08/INVENTORY.json L3-34 — 외부 FPIA inventory 시점·scope·canonical_adoption=false; 현재 canonical에 없는 owner 문서

[H03]: https://github.com/kco994553-star/Investment-System1/blob/59cc73a005196f73e92af8c47c594a9da8341a6c/implementation/docs/coordination/evidence/main_fpia_recorded_defects_2026-10-08/INVENTORY.json#L3706-L3714

- [H03] **외부 과거 ref `59cc73a005196f73e92af8c47c594a9da8341a6c`** / implementation/docs/coordination/evidence/main_fpia_recorded_defects_2026-10-08/INVENTORY.json L3706-3714 — 외부 inventory의 남은 구현/수용 의무; 현재 canonical에 없는 owner 문서

[P70]: https://github.com/kco994553-star/Investment-System1/pull/70
[P72]: https://github.com/kco994553-star/Investment-System1/pull/72
[P73]: https://github.com/kco994553-star/Investment-System1/pull/73
[P74]: https://github.com/kco994553-star/Investment-System1/pull/74
[P75]: https://github.com/kco994553-star/Investment-System1/pull/75
[P76]: https://github.com/kco994553-star/Investment-System1/pull/76
[P77]: https://github.com/kco994553-star/Investment-System1/pull/77
[P78]: https://github.com/kco994553-star/Investment-System1/pull/78
[P79]: https://github.com/kco994553-star/Investment-System1/pull/79
[P81]: https://github.com/kco994553-star/Investment-System1/pull/81
[P82]: https://github.com/kco994553-star/Investment-System1/pull/82
[P83]: https://github.com/kco994553-star/Investment-System1/pull/83
[P84]: https://github.com/kco994553-star/Investment-System1/pull/84
[P85]: https://github.com/kco994553-star/Investment-System1/pull/85
[P86]: https://github.com/kco994553-star/Investment-System1/pull/86
[P87]: https://github.com/kco994553-star/Investment-System1/pull/87

## 2026-10-10 코덱2 준비 문서 후속 기록

이 절은 위 **2026-10-09 / `12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df` 기준 본문을 보존한 후속 기록**이다. 이번 읽기 기준 canonical은 `ee039041ae7f5cb94e6a127930c7e43effb811ec`(#93 병합 후)이다. 아래 완료는 조사·설계·명세 작성 범위이며 운영 연결·수집·Holdout 사용·모델 승격의 완료가 아니다.

사용자 최신 승인은 **문서 전용 PR(.md만 변경), 최종 head의 실행된 필수 체크 전부 성공·실패 0**일 때 자체 병합하는 것이다. 코드·데이터·워크플로가 섞인 PR의 병합은 금지한다. force push·ruleset·`AUTONOMY_MODE`·방법론·가중치 변경 없이 적용하며 과거 문서의 개별 PR 승인 기록을 재작성하지 않는다.

| 후속 항목 | 이번 문서 결론 | 유지되는 차단/후속 조건 |
| --- | --- | --- |
| #93 | 세션 시작 때 이미 병합된 문서 10개 PR임을 확인했다. build/repository-guard 성공, deploy 조건부 skipped, 실패 0. [처리 기록](codex2_queue/RECEIPT_20261010.md). | GSQ-010 코덱1 코드·데이터·출력 경로 정리는 이 문서 작업으로 완료되지 않는다. |
| Macro 8축 권리/PIT | [조사](macro_data_rights/RESEARCH.md)·[FRED/ALFRED 근거](macro_data_rights/FRED_ALFRED_EVIDENCE.md)·[원기관 근거](macro_data_rights/PRIMARY_AGENCY_EVIDENCE.md) 작성. 무료 원기관 직접 자료의 개인 처리 후보를 추천한다. | FRED 개발/저장 경로 서면 허가, series 원권리, 각 빈티지/최초 가용 시각, 8축 producer·Macro shape·Surprise 기대치 근거는 미해소다. 원기관 채택/구현은 별도 후속 범위다. |
| QGV v2/Holdout | [보호 확인 및 PIT/OOS/Calibration 진입 체크리스트](qgv_v2_readiness/HOLDOUT_AND_ENTRY_CHECKLIST.md) 작성. 보호·소비 상태는 각각 **UNCONFIRMED**다. | 기존 메타데이터/접근통제/소비 기록 근거와 권한 있는 owner 확인이 필요하다. 이번 작업은 Holdout 기간 선택·원자료/결과 열람·사용을 하지 않았으며 v2 착수/채택을 승인하지 않는다. STANDARD v1 UNCALIBRATED 유지. |
| Technical 첫 PR | [#90 상세 작업 명세](technical_live_data/FIRST_IMPLEMENTATION_SPEC.md) 작성. 신규 파일·정확 함수/타입·합성 테스트·실패 부재·기존 helper/엔진 비교까지 지정한다. | 실제 공급자·Worker/browser Technical 연결·PIT/model 검증은 범위 밖이다. 코덱1 후속 code PR은 자체 병합 금지이며 별도 review·승인 대상이다. |
| M3 개인 종목군·순위 | [기기 RAM 계산·본인 Worker relay 설계](daily_data_pipeline/M3_PRIVATE_UNIVERSE_DESIGN.md) 작성. 개인 가격에서 선정한 현재 구성 목록도 공개하지 않는다. | 전체 적격 풀·권리·비용0·PIT·identity/CA와 기존 Official gate가 없으면 현재 Top500/전체 순위 UNKNOWN. P02 중간 시점 정책과 PRICE→QGV 자동 재계산 정책을 선택하지 않는다. |

#88 이후 canonical에는 본인 인증 Worker와 개인 일봉 표시 코드가 존재한다. 위의 과거 ‘Worker 미구현/미연결’ 상태는 작성 당시의 기록이다. 현재 코드의 존재는 실제 배포/조회 성공·공급자 허가·전체 미국 후보·Technical/Macro/QGV runtime 연결의 증거가 아니다. [M3 설계의 현재 연결 상태](daily_data_pipeline/M3_PRIVATE_UNIVERSE_DESIGN.md#현재-연결-상태)를 함께 적용한다.
