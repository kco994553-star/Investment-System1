# 사용자 결정·조치 대기 목록

기준일: 2026-10-10 UTC, canonical 확인 HEAD `ce98f752f1658a5c13eef6631f0196ebbed75acf`(#161 병합 후). 한 장 요약이며 새 결정이나 방법론을 만들지 않는다. 현재 진행 상태의 단일 진입점은 [CURRENT_HANDOFF](../../CURRENT_HANDOFF.md), 범위는 [ROADMAP_2026Q4](ROADMAP_2026Q4.md)다. 두 문서와 다르면 CURRENT_HANDOFF가 우선한다.

`권장안`은 기존 문서에 이미 적힌 권장만 옮겼다. 문서에 권장이 없으면 "문서상 권장 없음"으로 적는다. 결정 전에는 해당 값이 모두 `NOT_AVAILABLE`이며 0이나 추정값으로 대체하지 않는다.

## 1. 워크플로·배포

### 1-1. #156 워크플로 PR 병합 승인

- 무엇을 결정하나: cockpit-pages와 SEC 일일 워크플로가 `ci_node_tests.txt`·`ci_browser_tests.txt` manifest로 테스트를 실행하고 전체 `pytest tests/` 단계를 추가하는 변경을 병합할지.
- 선택지: 승인 후 병합 / 보류.
- 권장안: 문서상 권장 없음. 병합 후 이번 세션 새 테스트를 manifest에 추가하는 작은 PR이 이어진다(CURRENT_HANDOFF).
- 결정 전 상태: 새 테스트(design_responsive, design_canvas, profile_preview, thirteenf_filings, ops_status, private_subset)는 CI에 등록되지 않고 로컬 실행·통과만 확인됐다. 워크플로 변경이라 자체 병합 불가.
- 링크: [#156](https://github.com/kco994553-star/Investment-System1/pull/156)

### 1-2. Pages 배포 시점

- 무엇을 결정하나: #148 이후 병합분(프로필, 엔진 이식, ★, A2, B9, B10, C11, S03~S05)을 Pages에 언제 배포할지.
- 선택지: (a) cockpit-pages `workflow_dispatch`로 지금 배포 / (b) 예약된 SEC 일일 실행에 맡김. SEC 일일 실행은 기본 브랜치를 매일 22:17 UTC에 빌드·배포하므로 (b)를 택해도 다음 22:17 UTC에 자동 포함된다.
- 권장안: 문서상 권장 없음(CURRENT_HANDOFF는 두 선택지만 적음).
- 결정 전 상태: 마지막 실제 배포는 SEC run 38042681260(#144 기준). 이후 변경은 공개 사이트에 없다. 배포는 사용자 승인 대상이며 실행하지 않았다.
- 링크: [CURRENT_HANDOFF](../../CURRENT_HANDOFF.md)(canonical·배포 상태)

## 2. 공개 데이터 경계

### 2-1. M3 SEC 주식수 공급 경로

- 무엇을 결정하나: M3 '내 기기 기준' Universe 계산에 쓸 SEC 주식수를 기기에 어떻게 전달할지.
- 선택지: (a) Actions가 Universe 코드별 SEC 주식수·basis(가격 없음)를 공개 JSON으로 제공(공개 데이터 경계 변경 + 504 workflow 확장) / (b) Worker가 SEC를 중계(Worker 변경).
- 권장안: (a). 근거: CURRENT_HANDOFF가 (a)를 권장으로 표기. 현재 공개 `sec-public-inputs.json`에 US17 reported_shares가 있으나 M3 어댑터는 원본 body+SHA 검증을 요구해 그대로는 쓸 수 없다.
- 추가 조건: 주식수만으로는 부족하다. **주식 종류(share-class) basis 근거도 함께 필요**하며, basis가 UNKNOWN이면 `BASIS_UNCONFIRMED`로 처리한다. 자동 보정은 하지 않는다.
- 결정 전 상태: SEC 주식수 입력이 연결되지 않아 M3 시가총액·순위는 `NOT_AVAILABLE · SEC_INPUTS_NOT_CONNECTED`.
- 링크: [#122](https://github.com/kco994553-star/Investment-System1/pull/122), [SEC_M3_INPUT_ADAPTER](daily_data_pipeline/SEC_M3_INPUT_ADAPTER.md), [M3_PRIVATE_UNIVERSE_DESIGN](daily_data_pipeline/M3_PRIVATE_UNIVERSE_DESIGN.md)

### 2-2. 가격 불필요 유형 지표 공개

- 무엇을 결정하나: `company-types-pricefree.json`에 가격이 필요 없는 지표(revenue_cagr_3y, roic) 원값을 추가해 공개할지.
- 선택지: 승인 후 draft 브랜치를 마무리·병합 / 보류.
- 권장안: 문서상 권장 없음.
- 결정 전 상태: 지표 원값이 공개되지 않아 기기에서 커스텀 유형 램프로 기업별 유형 미리보기를 계산할 수 없다. 해당 값은 `NOT_AVAILABLE`.
- 링크: draft 브랜치 `claude/type-metrics-public`(WIP, 공개 데이터 경계라 승인 필요), [CURRENT_HANDOFF](../../CURRENT_HANDOFF.md)

### 2-3. SEC 504 확대와 비공개 다일 raw 보관 정책

- 무엇을 결정하나: US17을 넘어 Universe 504 코드를 수집하려면 며칠에 걸친 분할 수집(shard) 결과를 어디에 보관할지.
- 선택지: 사용자 소유 비공개 저장소(로컬 디스크 또는 개인 클라우드) 등 문서에 정리된 후보 중 선택. 위치와 복원·검증 절차를 문서화해야 한다.
- 권장안: 문서상 권장 없음.
- 결정 전 상태: SEC 일일 워크플로 테스트가 `actions/cache`, `upload-artifact@`, `git push`, `git commit` 사용을 금지하므로 일일 워크플로 안에서 다일 raw를 보관할 수 없다. #145 분할 모듈은 워크플로에 연결되지 않았고, 실제 504 취득 결과는 `NOT_AVAILABLE`. raw JSON/manifest는 Pages·공개 artifact로 복사하지 않는다.
- 링크: [SEC_UNIVERSE_SHARDS](daily_data_pipeline/SEC_UNIVERSE_SHARDS.md), [RAW_PERSISTENCE_OPTIONS](producer_infrastructure/RAW_PERSISTENCE_OPTIONS.md), [#145](https://github.com/kco994553-star/Investment-System1/pull/145)

## 3. 분류·밸류에이션·매크로 확인

### 3-1. SIC→업종군 매핑

- 무엇을 결정하나: SEC SIC 범위를 업종군으로 묶은 초안 표를 채택할지(표 확인 후에도 경기민감·방어 산식은 자동 채택되지 않음).
- 선택지: 초안 그대로 채택 / 수정 후 채택 / 보류.
- 권장안: 문서상 권장 없음(초안만 제시, 확인할 점이 표에 적혀 있음).
- 결정 전 상태: 경기민감·경기방어 판정과 업종군 분류는 `NOT_AVAILABLE`. 설정의 industry.groups는 비어 있다.
- 링크: [QUEUE_RESULTS_AND_COVERAGE](company_types/QUEUE_RESULTS_AND_COVERAGE.md)(SIC 절). 26E 결정 기록 변경이므로 별도 승인.

### 3-2. DCF 기본값

- 무엇을 결정하나: DCF·역DCF 금융 파라미터를 확정할지.
- 선택지: 문서의 제안값(명시기간 5년, 할인율 10%, 영구성장률 2%, 역DCF 탐색 구간 -50%~+100%)을 채택 / 수정 / 보류. FCFE 산출 정의와 주식 종류·희석 처리도 미확정.
- 권장안: 문서상 권장 없음. 제안값은 "사용자 결정 전 비활성"이며 관측된 자본비용이 아니라고 문서에 명시돼 있다.
- 결정 전 상태: 금융 파라미터가 null/confirmed=false라 DCF·역DCF·V 결과는 `NOT_AVAILABLE`(`PARAMETER_APPROVAL_PENDING`).
- 링크: [DCF_V1_PARAMETERS](valuation/DCF_V1_PARAMETERS.md), [#143](https://github.com/kco994553-star/Investment-System1/pull/143)

### 3-3. 매크로 8축 대응표

- 무엇을 결정하나: 8축별 공식 입력·표시 방식 초안을 채택할지. Growth는 연율 또는 전년동기비 선택, Inflation은 NSA YoY 채택 여부, 후속 4축의 exact series/필드/단위 선택 포함.
- 선택지: 초안 채택 / 수정 / 보류.
- 권장안: 문서상 권장 없음. 문서는 Growth(T10101 발표 연율%)와 Inflation(CUUR0000SA0 전년동월 대비)을 같은 cutoff 캡처에서 함께 엔진에 넣는 방식을 "제안"으로만 적었다.
- 결정 전 상태: 실제 국면, Direction/Momentum/Surprise/Stress/Confidence 및 6상태는 `NOT_AVAILABLE`. 입력 파서(#128)와 공개 raw 화면(#141)만 준비됐다.
- 링크: [EIGHT_AXIS_MAPPING_PROPOSAL](macro_data_rights/EIGHT_AXIS_MAPPING_PROPOSAL.md)

### 3-4. 테마 바스켓 (#152)

- 무엇을 결정하나: 14개 테마 바스켓 제안(ETF 후보·10-K 키워드)을 승인하고, 새 공개 파일로 표시하는 것을 허용할지.
- 선택지: 승인 / 수정 / 보류.
- 권장안: 문서상 권장 없음. 제안은 노출·쏠림 경고용이며 Q/G/V 비중에는 영향이 없다고 문서에 적혀 있다.
- 결정 전 상태: baskets_confirmed=false, membership_rule=null. 테마 소속은 `NOT_AVAILABLE`. 새 공개 파일은 공개 데이터 경계 변경이라 승인 필요.
- 링크: [#152](https://github.com/kco994553-star/Investment-System1/pull/152), [THEME_BASKET_PROPOSAL_V1](company_types/THEME_BASKET_PROPOSAL_V1.md)

## 4. 입력 범위·시점

### 4-1. 13F 추적 기관(manager) 집합

- 무엇을 결정하나: 13F를 수집·비교할 기관 목록.
- 선택지: 사용자가 기관을 직접 지정.
- 권장안: 문서상 권장 없음.
- 결정 전 상태: 기본 추적 목록이 없어 투자자별·종목별 겹침 비교는 `NOT_AVAILABLE`(#159는 읽기 경고·보기 화면까지).
- 링크: [#159](https://github.com/kco994553-star/Investment-System1/pull/159), [ROADMAP_2026Q4](ROADMAP_2026Q4.md) 할 일 13

### 4-2. forward(모의투자·전진검증) 시작일

- 무엇을 결정하나: 시작 시점, 대상, 전략 버전, 입력 cutoff, 결과 보관·검증 규약, QGV v2 착수 여부.
- 선택지: 사용자가 시작일을 지정.
- 권장안: 문서상 권장 없음. 에이전트는 기간을 선택·소급하지 않는다.
- 결정 전 상태: 시작일 미정. 기존 Holdout은 UNCONFIRMED로 두고 사용하지 않으며 QGV v2는 보류.
- 링크: [ROADMAP_2026Q4](ROADMAP_2026Q4.md) 할 일 16, [Holdout 확인](qgv_v2_readiness/HOLDOUT_PROTECTION_CHECK_20261010.md)

## 5. 외부 서비스 등록

### 5-1. DART 키 등록 알림

- 무엇을 결정하나: DART_API_KEY 등록을 마친 뒤 알려 주는 것.
- 선택지: 해당 없음(알림 한 번). 10/11 18:00 이후에 알린다. 시간 도달만으로 알림으로 보지 않는다.
- 권장안: 해당 없음.
- 결정 전 상태: 알림 전에는 코드 작성, 키 존재 확인, 인증·API 호출 모두 하지 않는다. DART 재무(한미반도체)는 `NOT_AVAILABLE`.
- 링크: [DART_CONNECTION_READINESS](daily_data_pipeline/DART_CONNECTION_READINESS.md), [ROADMAP_2026Q4](ROADMAP_2026Q4.md) 할 일 8

### 5-2. EDINET

- 무엇을 결정하나: 현재는 후순위 보류. 나중에 착수할 때 Subscription-Key 등록 조건을 확인한다.
- 선택지: 보류 유지 / 착수 결정(착수 시 키 등록 필요).
- 권장안: 보류 유지(사용자의 기존 결정, ROADMAP 할 일 9).
- 결정 전 상태: adapter 미착수. 도쿄일렉트론 공시 재무는 `NOT_AVAILABLE`.
- 링크: [KR_JP_FILINGS_RESEARCH](fundamentals_sources/KR_JP_FILINGS_RESEARCH.md), [ROADMAP_2026Q4](ROADMAP_2026Q4.md) 할 일 9

## 참고

- 열린 PR #162(Python 3.13 호환 + 백업 `/3`)는 이 목록의 결정 항목이 아니다. 병합은 CURRENT_HANDOFF의 병합 규칙을 따른다.
- 값(키, 토큰, 이메일, 시트 ID, 가격)은 이 문서에 적지 않는다. 설정 이름과 저장 위치만 [CURRENT_HANDOFF](../../CURRENT_HANDOFF.md)에 있다.
