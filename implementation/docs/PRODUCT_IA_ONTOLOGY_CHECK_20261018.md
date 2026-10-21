# 새 정보구조(IA) 연결·온톨로지 점검 (2026-10-18)

상태: **점검 문서만.** 코드·가드·워크플로·결정 기록은 바꾸지 않았다.
기준 커밋: canonical `35ffbf84` (`claude/investment-system-top500-validation-alrugm`, #303 병합).
근거 지시: 사용자 새 화면 구조(2026-10-18). 홈=기업 검색, 1 QGV ~ 6 프롬프트, n 전체 시스템 트리, n+1 Lab.
화면 요소별 자료 출처·갱신·신선도 계약: [FRONTEND_DATA_CONTRACT](FRONTEND_DATA_CONTRACT.md).

> 이 문서를 병합해도 아래 IA-2~IA-18 권장안의 승인이 아니다. 각 항목은 결정 후보로 남는다.
> IA-1(3.5 이름)만 결정됐다: **연쇄 효과 지도**(사용자 결정, 2026-10-18, 코디네이터 전달).
> [USER_DECISIONS_PENDING](USER_DECISIONS_PENDING.md)의 기존 항목(PRESET-NUM, RADAR-AXES, DRAW-STORE, REL-SOURCE, WEEKLY-REPORT, KR-NAMES, NEWS-CAP, TA-G1~G3, TRACKC-PORT, #300 기본값)은 다시 올리지 않고 번호로만 가리킨다.

## 읽는 법

- 이 문서는 [기능 대응표 PRODUCT_FEATURE_MAP_20261018](PRODUCT_FEATURE_MAP_20261018.md)(이하 **FM**)를 확장한다. FM에 있는 생산자·계약·검증 근거는 다시 적지 않는다. "FM A-4"는 Map A 표 4행, "FM B-3"은 Map B 3절이다.
- FM 기준은 `228e2ea0`(#295)다. 그 뒤 병합: #296(지시 원문), #298(뉴스 필터·중요도·영향 경로 설계), #299(보고 불가 카드·AI 답 검토 후 저장·프롬프트 즐겨찾기), #301(인수인계), #302(무채색 셸·8메뉴), #303(13F 연구 준비). 엔진 파일(`qgv/`, `rig/`, `macro/`, `universe/`)은 그 뒤 바뀌지 않았다. 그래서 FM의 엔진 줄 번호는 그대로 맞다.
- 같이 읽은 문서: [PRODUCT_FRONTEND_REDESIGN_20261018](PRODUCT_FRONTEND_REDESIGN_20261018.md)(이하 **지시**), [IMPACT_PATH_AND_CYCLE_DESIGN_20261018](news_relations/IMPACT_PATH_AND_CYCLE_DESIGN_20261018.md)(이하 **IMP**), [TA_PREP_STATUS_20261017](technical/TA_PREP_STATUS_20261017.md)(이하 **TA**), [THIRTEENF_WEIGHT_RESEARCH_PREP_20261018](backtest/THIRTEENF_WEIGHT_RESEARCH_PREP_20261018.md)(이하 **13F**), [BACKTEST_RESEARCH_PLAN](backtest/BACKTEST_RESEARCH_PLAN.md), [BACKTEST_DATA_AUDIT](backtest/BACKTEST_DATA_AUDIT.md).

경로 약어:

- `S/` = `implementation/src/investment_system/`
- `WA/` = `S/product/web_assets/`
- `T/` = `implementation/tools/`
- `WK/` = `implementation/worker/src/`

상태 기호: **있음** = 화면·자료·엔진이 연결돼 동작한다. **일부** = 일부 조각만 있거나 범위가 좁다. **없음** = 코드가 없다(문서만 있어도 없음).
빠진 것 기호: **F** 화면, **B** 새 백엔드·생산자, **D** 새 자료, **결정** 사용자 결정.

경계 기호(표의 "경계" 칸):

- **B-PRICE**: 가격과 가격 파생값은 기기 RAM·비공개 Worker·사용자 비공개 시트에만 둔다. 공개 JSON·Pages·Actions 로그에 넣지 않는다(GSQ-010, `WA/app.js:1155`의 공개 구획 차단).
- **B-PERSONAL**: 보유·거래·메모·그림·즐겨찾기 등 개인 자료는 공개 파일에 넣지 않는다.
- **B-LOGIN**: 로그인·계정 동기화는 외부 연결이다. 별도 승인 대상이다.
- **B-PROB**: 확률은 모델·표본·기간·검증 근거가 있을 때만 쓴다. 그 전에는 "확률 미산출"이다. 숫자를 만들지 않는다.

---

## 0. 요약 — 가장 큰 격차 10개

1. **검색 결과 기업 페이지가 둘로 갈린다.** TARGET 19개는 통합 상세(`WA/app.js:464-476`)가 있다. Universe504 코드는 SEC 주식수 카드만 나온다(`WA/app.js:233-243`). 504개의 Q·G는 공개 `sec-qgv2.json`에 있는데 그 화면에 안 붙는다.
2. **504개 이름 검색이 안 된다.** 504 검색 항목은 "이름 미공개"다(`WA/entity-search.js:87-100`, `WA/home-screen.js:47`). KR-NAMES 결정과 이름 공개 경로가 필요하다.
3. **관심 기업이 19개에 묶여 있다.** `WA/watchlist.js:3-4`는 TARGET 19개 id만 받는다. 4.1·4.2의 즐겨찾기, 2.3 그림, 차트 범위(TA G2)가 모두 여기에 걸린다.
4. **기업 키가 셋이다.** TARGET `company_id` 슬러그(`stry` ≠ 티커 SYK), Universe `EXCHANGE:SYMBOL`, CIK. 관계망은 C-39 `issuer_id`만 받는다. 이어 주는 어댑터가 없다.
5. **매크로 3.1~3.4는 엔진이 없다.** 경기·시장·산업 위치, 근거 수직선, 조건, 사용자 위치 저장 모두 코드가 없다. 기업 상세의 "거시 노출" 칸은 항상 비어 있다(`WA/app.js:474`, `D.macro`는 GSQ-010으로 항상 NA).
6. **확률을 만들 자료가 없다.** 매크로 빈티지(FRED/ALFRED)는 저장 금지 판정, 가격은 Worker 5년이 한계다(BACKTEST_DATA_AUDIT §0). 3.2·3.3의 확률은 당분간 "미산출"이다.
7. **레이더는 코드가 없다.** 공개 파일의 비QGV 서술값 중 `revenue_volatility_5y_rank_pct`는 사실상 G축 `g_consistency`와 같은 값이다(§3). 진짜 비QGV 축은 대부분 가격 기반이라 기기 전용이다.
8. **경쟁사 평균을 낼 자료가 없다.** 경쟁 관계(REL-SOURCE 미정)와 사업 탭이 비어 있다(`WA/company-screen.js:206`). 레이더 비교군 셋 중 "산업"만 지금 계산할 수 있다.
9. **관계 경로가 세 갈래다.** `data.json.relationships`(GSQ-010으로 항상 NA), Track D 렌더 페이지(`S/product/web_mvp.py:101-102,114-118`, Pages에서 삭제), 관계망 도메인(`S/rig/`, 화면 미연결). 하나로 합쳐야 한다.
10. **13F 가중치(1.3)의 메뉴 위치가 엇갈린다.** 새 구조는 QGV 1.3, 현재 셸은 Lab(`WA/app-shell.js:38-39`)이다. 화면은 아직 "준비 중"이다(`WA/app-shell.js:124-130`).

---

## 1. 항목 대응표

메뉴 셸은 이미 새 구조와 거의 같다. `WA/app-shell.js:14-40`이 1 QGV ~ 8 Lab을 정의한다. 새 구조의 6은 셸의 6, n은 셸의 7(`#system`), n+1은 셸의 8(`#validation`)이다. 다른 점은 13F 가중치 위치 하나다(IA-2).

### 1-0. 홈·검색·기업 페이지

| 항목 | 기존 화면·경로 | 기존 데이터 파일 | 기존 엔진 | 상태 | 빠진 것 | 경계 |
|---|---|---|---|---|---|---|
| 0 검색 | `#home`, 전역 검색 `WA/home-screen.js`(SearchUI), 최근 검색 `investment.web.v1.recent-search`(`WA/home-screen.js:22`) | `entities.json`(`S/product/web_mvp.py:111`, `S/product/entity_catalog.py:32-85`: TARGET 19 + 산업 1 + 매크로 1), `universe-codes.json`(504 코드, 이름 없음), `sec-universe-shares.json` | `WA/entity-search.js` 정규화·순위(추천 아님) | 일부 | **D** 504 이름(KR-NAMES). **F** 투자자·테마 검색 항목(유형만 있음 `WA/entity-search.js:8`) | 이름은 공개 정보. 가격·순위는 색인하지 않음 |
| 0 기업 페이지(QGV+기술+매크로) | `#company/<id>`, `#analysis/<id>/<tab>` 7탭(`WA/company-screen.js:11`) | `sec-qgv2.json`(Q·G), `sec-valuation-inputs.json`, `sec-filing-windows.json` | `WA/qgv-scores.js` → `WA/qgv-v2.js`(기기 V) | 일부 | **F** 504 코드에 Q·G·유형·SIC 표시(자료는 이미 공개). **B** 기업별 매크로 노출(없음). **F** 기술 요약은 TARGET만(`WA/private-history.js` 19개) | V·가격 파생 = B-PRICE |

### 1-1. QGV

| 항목 | 기존 화면·경로 | 기존 데이터 파일 | 기존 엔진 | 상태 | 빠진 것 | 경계 |
|---|---|---|---|---|---|---|
| 1.1 리더보드 | `#leaderboard` S06, `WA/leaderboard-screen.js` | `sec-qgv2.json`(행마다 `sic`·`industry_group`·`profile`, `S/universe/sec_qgv2.py:71-73`) | `WA/qgv-scores.js:175` 순위, `WA/app.js:633 rankOrder`, M3 시총 순위 `WA/private-subset.js:177` | 일부 | **F** 표시 행이 19개(FM A-4). 504 행 표시. **F** SIC·유형 필터(자료 있음). **B** 기업별 기간 수익률: `daily` 열이 미연결(`WA/leaderboard-screen.js:13`). 기간 정의는 원장용만 있음(`WA/report-benchmarks.js:11` 1D/5D/20D/60D/120D). **D** 504 종목 과거 종가(`Prices_D`는 핵심 종목만) | 수익률·시총 = B-PRICE. 기기에서만 정렬 |
| 1.1 기업 유형 열 | S06 유형 칩, `#types` | `company-types-pricefree.json`(TARGET 19만, `WA/public-screens.js:5`) | `S/qgv/qgv_v2.py:147 pricefree_memberships`(504는 기기에서 계산) | 일부 | **결정** 유형 규칙 대부분 미정(FM A-1c: 499/504 대체값) | 없음 |
| 1.2 가중치·사용자 설정 | `#profiles` S13 `WA/device-profiles.js`(v1 초안만, `investment.web.v1.profile-drafts`) | `sec-qg-factors.json`(v1 요인) | v2 2단계 경로는 #300(미병합). 공식 경로는 `PRESET_INVALID`(`WA/qgv-v2.js:110`) | 일부 | **B** #300 병합(엔진 `weights` 인자). **결정** PRESET-NUM, #300 기본값 4건, IA-9 이름 충돌 | 개인 프로필 = B-PERSONAL(이 브라우저) |
| 1.3 13F 가중치 연구 | `#lab-13f` "준비 중"(`WA/app-shell.js:124-130`), 조회 `#thirteenf` S16 | `sec-13f-changes.json`(최신 2분기, 10기관) | 파서·비교 `S/providers/sec_13f.py:313,389`. Track C 커널은 다른 브랜치(13F §1) | 없음(연구) | **D** 다년 보유 패널·정정 계보·PIT CUSIP(13F §4). **B** 탐색기·평가 등록부. **결정** IA-2 메뉴 위치, TRACKC-PORT, 13F-R1~R16 | 연구 결과는 공식 기본값을 바꾸지 않음 |
| 1.4a QGV 구조 트리 | `#qgv` 허브 상태 카드, `#system` 준비 중(`WA/app-shell.js:115-123`) | `sec-qgv2.json` `method`(가중치·최소 동종 8·백분위 방식, `S/universe/sec_qgv2.py:57-67`) | `S/qgv/v2_scoring.py:39-66 SUBMETRICS`(축→요인→세부 지표·방향) | 일부 | **F** 트리 화면. 트리는 `method`와 `SUBMETRICS`에서 자동 생성 가능. **결정** IA-8 Q1~V5 표기 | 예시: Q·G는 공개 실제 값(출처·시각 표시). V는 기기 값 또는 "예시" 표시 |
| 1.4b n각형 레이더 | 없음 | 비QGV 후보 일부(§3) | 없음(FM A-5) | 없음 | **F** 레이더. **B** 기기 가격 축 계산. **D** 경쟁사 집합. **결정** RADAR-AXES, IA-10 | 가격 축 = B-PRICE. 면적을 점수로 쓰지 않음 |

### 1-2. 기술적 분석

| 항목 | 기존 화면·경로 | 기존 데이터 파일 | 기존 엔진 | 상태 | 빠진 것 | 경계 |
|---|---|---|---|---|---|---|
| 2.1 기존 TA + 정도 + 시나리오 | `#technical`, `WA/technical-chart.js`(SVG), `WA/technical-cards.js` 6카드 | 공개 파일 없음. Worker 일봉(`WA/private-history.js`, RAM) | `WA/chart-indicators.js` 고정 매개변수(FM B-1) | 일부 | **F** "정도" = 매개변수 묶음 선택(지금은 상수). **B** 매개변수 묶음 버전(`ParameterSet`). **F** 시나리오 A/B/C는 2단계 설계만(TA §8) | B-PRICE. 착수 조건 1/6(TA §10) |
| 2.2 차트 패턴 + 정도 + 시나리오 | 없음 | 없음 | 없음. 설계·시험 사례만(TA §6) | 없음 | **B** 패턴 엔진·공식 이력. **결정** 착수 승인, TA-G1~G3 | 형태 적합도 ≠ 상승 확률(B-PROB) |
| 2.3 사용자 그림·메모 | 없음. 플레이북 메모만(`WA/playbook-screen.js`, `investment.web.v1.playbook`) | 없음 | 없음 | 없음 | **B** `chart-annotation/1`(종목·봉 주기·가격 기준·시간/가격 좌표). **결정** DRAW-STORE, IA-7 키 | B-PERSONAL. 공식 감지 증거로 쓰지 않음 |
| 2.4 TA 트리 | 없음 | — | 지표 정의는 `WA/chart-indicators.js`, 최소 봉 수는 TA §5 | 없음 | **F** 트리. 예시는 합성 봉(TA §6 사례 재사용) | 실제 종목 가격 예시 금지 → 합성 표시 |

### 1-3. 매크로

| 항목 | 기존 화면·경로 | 기존 데이터 파일 | 기존 엔진 | 상태 | 빠진 것 | 경계 |
|---|---|---|---|---|---|---|
| 3.1 현재 위치 그래프 + 근거 수직선 + 기존 매크로 | `#macro`: 8축×6차원(`WA/public-screens.js:109`), 경고등 `WA/macro-lights.js:9-15`, 참고 모드 `:241` | `macro-screen.json`(최신 관측만, 시계열 아님) | `S/macro/primary_input.py`, `S/macro/raw_axes_v0.py:40-55`, `S/macro/growth_inflation_v0.py` | 일부(기존 매크로만) | **B** 위치 판정 모델. **D** 시계열 이력. **D** 실제 발표 시각: 지금 `available_at`은 수집 시각 상한이다(`S/macro/primary_input.py:42,49` `OBSERVED_CAPTURE_UPPER_BOUND`). **결정** IA-4, IA-16 | 시장 위치 입력(SPY·HYG/IEF)은 B-PRICE. B-PROB |
| 3.1 예: 운송 매출 증가 근거 | 없음 | `sec-qgv2.json`의 `industry_group=transportation` 행 `revenue_ttm_growth`·`v_inputs_v2.revenue`(가격 없음) | 없음 | 없음 | **B** 산업군 매출 집계(공개 가능, 가격 없음). 운송 ETF는 Worker 허용 목록에 없다(`WK/index.js:52`, 운송은 XLI로 묶임 `S/qgv/sector_etf_map_v1.json` 13행) | SEC 자료 집계는 공개 가능 |
| 3.2 순환매 위치 + 조건·확률 | 없음 | — | SIC→섹터 ETF 대응 `S/qgv/sector_basis.py`(D-22, 가상매매 이상 하락용) | 없음 | **B** 순환매 모델. **D** 섹터 ETF 이력(기기). **결정** IA-3, IA-5 | B-PRICE, B-PROB |
| 3.3 SIC 산업 사이클 | 없음. SIC 그룹 라벨만(`S/qgv/sic_industry_groups_v0.json`, 경기민감·방어 "후보", 구성원 NA) | `sec-qgv2.json` `industry_group` | `S/qgv/sic_industry.py classify_sic` | 없음 | **B** 산업 지표·위치 모델. **결정** IA-5 그룹 단위 | B-PROB |
| 3.4 사용자 위치 선택·저장 | 없음 | — | — | 없음 | **B** 저장(사용자 위치·이유·시각). 시스템 추정과 나란히(IMP b-5) | B-PERSONAL. 점수에 안 씀 |
| 3.5 연쇄 효과 지도(매크로 인과 사슬) | 없음(화면). 엔진 `S/rig/discovery/impact.py` | 없음 | `impact_graph`, `ConceptKind` `MACRO_DRIVER`/`VALUE_CHAIN_STAGE`, `Hop` `EXPOSURE`/`PEER` | 일부(엔진만, 합성 시험) | **B** 경로 설명 필드(전제·시차·반대 경로·상쇄·반증, IMP a-2). **D** 개념·노출 자료. **결정** REL-SOURCE. 이름은 결정됨(IA-1: 연쇄 효과 지도) | 방향·크기·확률 없음(IMP a-2 규칙 4·5) |
| 3.6 매크로 트리 | 없음 | `macro-screen.json` 축·차원 정의 | `S/macro/primary_contract.py:14 DIMENSIONS` | 없음 | **F** 트리 | 예시는 공개 관측(출처·시각) |

### 1-4. 뉴스·공시·기업 관계

| 항목 | 기존 화면·경로 | 기존 데이터 파일 | 기존 엔진 | 상태 | 빠진 것 | 경계 |
|---|---|---|---|---|---|---|
| 4.1 관계망 | `#news`의 iframe은 `D.relationships`가 있을 때만(FM B-3). Pages에는 `network.html`이 없다 | 없음 | `S/rig/` P0~P4(`model.py:86 RelationshipType`, `intel/intel.py` 상태) | 일부(엔진만) | **D** 관계 자료(REL-SOURCE). **B** `IdentityLookup` 어댑터(IMP a-6 2번), 공개 생산자. **F** 검색 없을 때 "매크로 주목 기업"(IA-13). **F** 즐겨찾기 = 단일 관심 목록 | 즐겨찾기 = B-PERSONAL |
| 4.2 공시·뉴스 | `#news`, `#watchlist`. 필터·중요도 4단계(`WA/news-signals.js:103-122`) | `news-signals.json`, `sec-disclosures.json`, `dart-disclosures.json`(모두 TARGET 기업만) | `S/product/news_signals.py`, `S/product/sec_disclosures.py` | 일부 | **D** 504 기업 공시·뉴스. **B** 5줄 요약(IA-14). **B** 사건 전후 가격 반응(§4, 기기). **결정** NEWS-CAP | 반응 = B-PRICE. `score_effect: NONE` 유지(`news_signals.py:77`) |
| 4.3 뉴스 트리 | 없음 | — | 분류·중복 묶기 규칙(`news_signals.py:298-323`) | 없음 | **F** 트리 | 예시는 공개 항목 |

### 1-5. 포트폴리오

| 항목 | 기존 화면·경로 | 기존 데이터 파일 | 기존 엔진 | 상태 | 빠진 것 | 경계 |
|---|---|---|---|---|---|---|
| 5.1 모델·사용자·모의 | `#model`(항상 NA, FM B-4), `#portfolio`, `#actual` | `actual-catalog.json`(TARGET v0) | ACTUAL IndexedDB `WA/device-actual.js`, PAPER `WA/virtual-trading.js:7`(SET_A..D + SHADOW) | 일부 | **B** 모델 포트폴리오 생성기. **F** 셋 나란히 비교. 새 구조에 TARGET이 빠짐 → §2-3 G1 | ACTUAL·PAPER = B-PERSONAL, B-PRICE |
| 5.2 일일·주간 보고 | `#report/real`, `WA/daily-report.js:138-179` 13영역 | 없음(기기) | `WA/report-benchmarks.js` | 일부(일일만) | **B** 주간 집계. **결정** WEEKLY-REPORT | B-PERSONAL |
| 5.3 모의 일일 보고 | `#report/mock` | 없음(기기·사용자 시트) | `WA/virtual-trading-runner.js` | 일부 | 시작일 2026-10-19(`WA/virtual-trading.js:6`, D-13). 첫 실행 전 | B-PRICE |
| 5.4 포트폴리오 트리 | 없음 | — | — | 없음 | **F** 트리 | 예시는 "예시" 표시. 실제 보유를 예시로 쓰지 않음 |
| 5.x 보고 불가 → 프롬프트 | 보고 불가 카드(`WA/daily-report.js:329-430`, #299) | — | 사유 코드 → 최소 누락 입력 → 복사 프롬프트 | 있음 | 주간·모의 보고에도 같은 카드 연결 | 프롬프트에 금액 없음 |

### 1-6. 프롬프트 라이브러리·개인화

| 항목 | 기존 화면·경로 | 기존 데이터 파일 | 기존 엔진 | 상태 | 빠진 것 | 경계 |
|---|---|---|---|---|---|---|
| 6 카탈로그 | `#research` → `research.html`(`S/product/web_mvp.py:110-111`) | 빌드 시 생성 | `S/prompt_library/catalog.py:24-60`(70개, 5영역) | 있음 | **결정** PROMPT-DOMAIN(뉴스·포트폴리오·백테스트 영역 없음) | — |
| 6 즐겨찾기·개인 수정본 | `WA/research-bridge.js:133-140`(#299) | `investment.web.v1.prompt-favorites`, `…prompt-personal-copies` | — | 있음(이 브라우저) | — | B-PERSONAL |
| 6 로그인 → 계정 | Google 로그인은 시트·Worker 접근용(`WA/google-sheet-quotes.js`), 앱 계정이 아님 | — | Worker 단일 소유자 확인(`WK/index.js:291`) | 없음 | **B** 계정 저장소. **결정** IA-6 | B-LOGIN |
| 6 비로그인 → 이 기기 | 약 20개 `investment.web.v1.*` 키, 백업 `WA/device-backup.js` | — | — | 있음 | 문구: "이 브라우저 프로필 기준"(지시 §10) | B-PERSONAL |
| 6 입력 없음 → 개발자 기본값 | 각 설정의 기본값(예: `WA/profile-defaults.js`, `WA/type-config-defaults.js`, `WA/playbook-config-defaults.js`) | — | — | 일부 | **F** 우선순위(계정 → 브라우저 → 기본값)를 한 곳에서 해석하는 층 | 실제 보유를 기본값으로 채우지 않음 |

### 1-7. n 전체 트리, n+1 Lab

| 항목 | 기존 화면·경로 | 기존 데이터 파일 | 기존 엔진 | 상태 | 빠진 것 | 경계 |
|---|---|---|---|---|---|---|
| n 전체 시스템 트리 | `#system` 준비 중(`WA/app-shell.js:115-123`) | — | — | 없음 | **F** 트리. **B** 식별자 연결표(§2) | 예시 규칙(실제=출처·시각, 합성=예시 표시) |
| n+1.1 백테스트 | `#validation-backtest`(같은 화면 앵커, `WA/app.js:833`), 설정 칸은 비활성(FM A-7) | 없음 | 등록부는 문서뿐(BACKTEST_RESEARCH_PLAN §3, 24개 ID). `S/validation/backtest.py`는 재사용 금지 | 없음(실행) | **D** 상장폐지 포함 가격·과거 모집단(BACKTEST_DATA_AUDIT §0). **결정** BACKTEST(BT-1~17) | B-PRICE |
| n+1.2 전진 검증 | `#validation-forward`, `WA/forward-validation.js` | `forward-validation-ledger.json` | `S/validation/forward_ledger.py`(Q·G만) | 일부 | 첫 기록 2026-10-19 이후 | 과거 기록 수정 금지 |

---

## 2. 온톨로지

### 2-1. 엔티티 표

"정규 ID 제안"은 결정 전 권장안이다. 근거가 있는 것만 적었다.

#### A. 기업·식별

| 엔티티 | 지금 있는 곳 | 지금의 식별자 | 정규 ID 제안 | 불일치·위험 |
|---|---|---|---|---|
| Issuer(발행인) | `S/contracts/global_universe.py:62` `IssuerIdentity`(관계망만 사용). `sec-qgv2.json` 행 `cik` | `issuer_id`(형식 미정), CIK 10자리 | `issuer_id = "sec:" + CIK10`(미국). 비SEC 발행인은 별도 접두(예: `dart:`, `tse:`) | 관계망은 "티커·CIK 필드 없음"(`S/rig/model.py:1-5`). 그런데 웹은 CIK를 안 넘긴다. 어댑터 없음 |
| Security(증권) | `global_universe.py:77`. 13F CUSIP(`sec-13f-changes.json`) | `security_id`, CUSIP | `security_id`는 CUSIP 또는 ISIN 기반. 시점별 | CUSIP→기업은 TARGET만(FM A-6a) |
| Listing(상장) | `global_universe.py:93`. Universe 코드 `S/universe/universe_codes_v1.json`(504) | `EXCHANGE:SYMBOL` | `listing_id = Universe 코드` | 같은 CIK의 여러 종류주(GOOGL/GOOG)는 다른 상장. 순위는 발행인 1점(`S/universe/sec_qgv2.py:64`) |
| Company(화면 기업) | `S/qgv/identifiers.py:14` `OFFICIAL_PORTFOLIO_V11`, `WA/watchlist.js:3`, `WA/public-screens.js:5` | `company_id` 슬러그 19개 | TARGET 별칭으로만 유지. 정규 키는 Issuer | `stry`(티커 SYK), `tokyo_electron`, `hanmi`: 슬러그 ≠ 티커. 504에는 슬러그가 없음 |
| Investor(13F 기관) | `S/config/manager_styles_v0.json`(10기관), 즐겨찾기 `investment.web.v1.investor-stars`(`WA/public-screens.js:143`) | 기관 CIK | `investor_id = "sec:" + CIK10` + `entity_type=INVESTOR` | 기업 CIK와 같은 SEC 번호 체계. 유형 없이 CIK만 쓰면 섞임. 기관 즐겨찾기와 기업 관심 목록이 따로 있음(목적이 달라 유지 가능) |
| Profile(재무 프로필) | `sec-qgv2.json` 행 `profile` | `FINANCIAL` / `GENERAL`(SIC 6000-6799, `METHOD.financial_sic_range`) | 그대로 | 화면 "기업 유형"과 다른 개념. 이름을 "재무 프로필"로 분리 표시 |

#### B. 분류

| 엔티티 | 지금 있는 곳 | 식별자 | 정규 ID 제안 | 불일치·위험 |
|---|---|---|---|---|
| SIC | `sec-qgv2.json` 행 `sic`(SEC submissions 현재 값) | 4자리 | `sic:NNNN` + 기준 시각 | 과거 SIC는 FSDS 경로(13F §6, BACKTEST_DATA_AUDIT §0 5번). 현재 SIC를 과거에 쓰지 않음 |
| IndustryGroup | `S/qgv/sic_industry_groups_v0.json`(10그룹 + 7하위) | `resources_mining` 등 | `industry_group:<id>@sic_industry_groups/v0` | QGV 동종 비교 기준(`METHOD.industry_groups`)과 같다. `manufacturing_industrial_tech`(SIC 2200-3999)는 사이클 분석에는 너무 넓다 |
| Sector(섹터 ETF 기준) | `S/qgv/sector_etf_map_v1.json`(13규칙, D-22) | ETF 티커 | 가격 비교 기준으로만 사용 | 10 SIC 그룹과 경계가 다르다(예: 운송은 XLI). 산업 그룹과 섞지 않음 |
| 옛 섹터 라벨 | `S/qgv/identifiers.py` `sector="Semicap"` → `entities.json` `industry`(`entity_catalog.py:58`) | 자유 문자열 | 표시 전용으로 격하 | 네 번째 산업 어휘. 검색 결과에만 보임 |
| 탐색 산업 | `entity_catalog.py:22-24` `INDUSTRY:semiconductor` | `semiconductor` | 산업 그룹 id에 연결 | SIC 하위 그룹 `semiconductors`, 테마 `semiconductors`와 철자·의미가 갈림 |
| CompanyType | `S/qgv/type_config_v1.json` `types` 8개(growth, value, dividend, quality, cyclical, defensive, leader, theme) | 유형 id | `company_type:<id>@type_config/1` | `defensive`(경기방어)·`cyclical`이 SIC 그룹의 `CYCLICAL_CANDIDATE`/`DEFENSIVE_CANDIDATE`와 이름이 겹친다. 유형 `theme`이 테마 분류와 겹친다 |
| Theme | `S/qgv/theme_config_v1.json` 12개, 공개 `company-classification.json`(TARGET만) | `ai`, `semiconductors` 등 | `theme:<id>@theme_config/v1` | 지시 §11: 산업·유형·테마는 서로 상하위가 아님. 유지 |

#### C. QGV

| 엔티티 | 지금 있는 곳 | 식별자 | 정규 ID 제안 | 불일치·위험 |
|---|---|---|---|---|
| Axis | `S/qgv/qgv_v2.py:20-24`, `WA/qgv-v2.js` | `Q`, `G`, `V` | 그대로 | — |
| Factor | 같은 곳(15개), Q·G 10개는 `S/qgv/v2_scoring.py:26-29` | `q_profitability` … `v_expectation_check` | 요인 id가 정규. `Q1`~`V5`는 표시 별칭 | **Q1~V5 대응표가 어디에도 없다.** v1 요인(7/6/7, `WA/profile-defaults.js`)은 다른 집합이다(IA-8) |
| SubMetric | `v2_scoring.py:39-66 SUBMETRICS`, 원값 `sec-qgv2.json` `metrics` | `roic` 등 + 방향 | 그대로 | FINANCIAL은 `q_earnings_quality`가 정의상 없음(FIN-NA-CODE) |
| Preset(코드) | `qgv_v2.py:28-34`: `balanced`/`quality`/`growth`/`value` | 키 | "축 비중 시작값"으로 표시 | 사용자 프리셋과 다르다(지시 §0-1) |
| UserPreset(사용자) | 없음(#300 편집기에 "수치 미정") | — | 별도 네임스페이스(IA-9) | `balanced` 키 재사용 금지. `StrategyStyle` Defensive/Balanced/Aggressive(`S/contracts/strategy.py:85-118`)는 Q/G 비중을 **동결 키**로 막는다. 같은 영어 이름, 다른 의미 |
| WeightProfile | v1 `device-profile-drafts/1`(`WA/device-profiles.js`). v2 트리는 #300 | 초안 id | `qgv-v2/custom/<hash12>/gate-on|off`(FM A-3 제안) | v1 초안을 v2로 착각하면 안 됨 |
| Gate | `qgv_v2.py` `GATE_DEFAULT`, `GATE_PERCENTILE=30` | 켬/끔 | 프로필 속성 | — |
| ScoreVersion | `calc_version`(`qgv2-calc/2026-10-17.1`), `TYPE_SCOPE` | 문자열 | 모든 점수 관측에 붙임 | 버전 혼합 행은 순위 밖(`sec_qgv2.py:337-338`) |

#### D. 기술적 분석

| 엔티티 | 지금 있는 곳 | 식별자 | 정규 ID 제안 | 불일치·위험 |
|---|---|---|---|---|
| Bar / PriceSeries | `WA/private-history.js` `private-history/1`, `WA/price-store.js` `Prices_D` | 기호 + 가격 기준(`RAW_CLOSE` 등) | `listing_id + interval + price_basis` | 기호가 Worker 기호다. Universe 코드와 다를 수 있음(`042700.KS`) |
| TechnicalIndicator | `WA/chart-indicators.js` | `sma20`, `rsi14` 등(매개변수가 이름에 박힘) | `indicator:<kind>` + `ParameterSet` | "정도"를 바꾸면 이름이 바뀌는 구조. 매개변수를 이름에서 분리해야 함 |
| ParameterSet("정도") | 없음 | — | `ta-params/<kind>/<version>` | 공식 이력은 한 기본 묶음으로만 기록(TA §9) |
| Pattern / PatternState | 설계만(TA §6, `pattern-rules/1`) | `FORMED`·`CONFIRMED`·`FAILED`·`INVALIDATED`·`EXPIRED` | 설계 그대로 | — |
| Scenario | 네 곳에서 다른 뜻: TA 스윙 A/B/C(TA §8), 매크로 NA 카드(`WA/screen-detail.js`), 일일 보고 ⑨ Driver/시나리오, 기업 "가치·시나리오" 탭(DCF) | — | 화면 이름을 나눔(§2-3 G6) | 같은 낱말 "시나리오"가 넷 |
| UserDrawing | 없음 | — | `chart-annotation/1`(FM B lane D 제안) | 사용자 그림은 공식 증거가 아님 |

#### E. 매크로·사이클·인과

| 엔티티 | 지금 있는 곳 | 식별자 | 정규 ID 제안 | 불일치·위험 |
|---|---|---|---|---|
| MacroIndicator | `S/macro/raw_axes_v0.py:40-55` `source_series_id`(예: `BLS:LNS14000000`). 탐색 엔티티 `MACRO:CPIAUCSL`(`entity_catalog.py:25-28`) | 기관 계열 id / FRED 코드 | 파이프라인 `source_series_id`가 정규. FRED 코드는 별칭 | 검색은 FRED 코드, 실제 물가 수집은 BLS `CUUR0000SA0`(`raw_axes_v0.py:123`). FRED는 저장 금지 판정(BACKTEST_DATA_AUDIT §0 4번) |
| MacroObservation | `S/macro/primary_input.py` `MacroObservation` | `observation_id` | 그대로 | `available_at` = 수집 시각 상한. 실제 발표 시각이 아님(IA-16) |
| AxisCell(8축×6차원) | `S/macro/primary_contract.py:14` | 축 × 차원 | 그대로 | Level 외 5차원은 NA |
| MacroLight | `S/macro/macro_lights_v1.json`, `WA/macro-lights.js:9-15` | 5개 | 그대로 | 재가동은 M-REENABLE |
| CyclePhase(경기) / MarketPhase(주식시장) | 없음. 후보 어휘만(IMP b-2) | — | `cycle:economy:<phase>`, `cycle:market:<phase>` + 모델 버전 | 어휘를 먼저 고정해야 3.4 사용자 선택과 비교 가능(IA-4) |
| SectorRotationPosition | 없음 | — | `rotation:<industry_group>@<as_of>` | 단위 결정(IA-5) |
| IndustryCycle | 없음 | — | `cycle:industry:<industry_group>` | 같음 |
| Evidence | `S/rig/model.py:153` `Evidence`(evidence_id, source_id, locator, available_at) | `evidence_id` | **이 한 형태를 매크로 근거에도 재사용** | 매크로용 근거 기록을 따로 만들면 중복 |
| Condition(상향·유지·하향) | 없음. 설계 IMP b-4 | — | `condition:<target>:<up|hold|down>:<version>` | 숫자 기준 미정 |
| Probability | 없음 | — | 조건마다 `{model_id, sample, period, calibration}` 필수 | B-PROB. 자료 신뢰도를 확률로 바꾸지 않음 |
| UserPositionNote(3.4) | 없음 | — | 사용자 저장소 키 + `user_note:<target>:<at>` | 공식 위치를 덮지 않음 |
| Concept | `S/rig/discovery/impact.py` `ConceptKind` | `MACRO_DRIVER`·`TECHNOLOGY`·`VALUE_CHAIN_STAGE` | 그대로 | 개념 정의 소유는 매크로(IMP a-3) |
| CausalChain(3.5 "연쇄 효과 지도") = ImpactPath | `impact.py` `ImpactPath`(nodes, hops), `MAX_HOPS=3` | 요청 시 계산, 저장 안 함 | 같은 `ImpactPath` + 설명 필드(IMP a-2) | 3.5와 4.1이 같은 엔진. 그래프를 둘 만들지 않음 |

#### F. 뉴스·관계

| 엔티티 | 지금 있는 곳 | 식별자 | 정규 ID 제안 | 불일치·위험 |
|---|---|---|---|---|
| NewsItem | `news-signals.json` `ITEM_KEYS`(`S/product/news_signals.py:182-183`) | `group_id = news:<company_id>:<시각>`(`:311`), `published_at` | 사건 키를 Issuer 기준으로 | 키가 `company_id`라 504로 못 넓힘. GDELT `published_at`은 최초 보도 시각이 아닐 수 있음 |
| Filing(8-K) | `sec-disclosures.json` `EVENT_KEYS`(`S/product/sec_disclosures.py:39-40`) | `accession`, `accepted_at`(초 단위) | `filing:sec:<accession>` | 가장 믿을 만한 사건 시각. §4의 기준 |
| DART 공시 | `dart-disclosures.json` | 접수번호 | `filing:dart:<rcept_no>` | hanmi만 |
| NewsEvent / EconomicEvent | `S/rig/model.py:198,203` | 사건 id | 공개 피드 → 관계망 사건 어댑터(IMP a-6 3번) | 어댑터 없음 |
| Relationship / RelationshipState | `S/rig/model.py:254,270`, `S/rig/intel/intel.py` | 관계 id, 상태 NEW…ENDED | 그대로 | 실제 자료 없음(REL-SOURCE) |
| NewsStatus | 공개 `NEW`/`REPEAT` vs 관계망 `NEW`/`UPDATE`/`FOLLOW_UP`/`DUPLICATE` | — | IMP a-5 대응표 | `FOLLOW_UP` 구분 규칙 없음 |
| ImportanceTier | 웹 4단계(`WA/news-signals.js:107`) vs 관계망 6단계(`S/rig/myview/scope.py:45-54`) | — | 6단계를 정본, 웹은 중요도 산출 전까지 4단계 표시 | 중요도(Materiality) 생산자 없음 |
| Watchlist | 웹 `investment.web.v1.personal`(`WA/app.js:56`, 19개 id만), 관계망 `S/rig/myview/prefs.py` | `company_id` | **하나만**. 키는 Issuer(IA-7) | 두 구현. 504 기업을 못 담음 |
| Summary5Line | 없음 | — | `summary:<event_id>:<version>` + 근거 링크 | 사실·가설 구분 필드 필요 |
| PriceReaction | 없음 | — | 기기 RAM 값, 저장 안 함(§4) | B-PRICE |

#### G. 포트폴리오·보고·프롬프트·사용자

| 엔티티 | 지금 있는 곳 | 식별자 | 정규 ID 제안 | 불일치·위험 |
|---|---|---|---|---|
| Portfolio | MODEL(없음), TARGET(`actual-catalog.json`), ACTUAL(IndexedDB), PAPER SET_A..D·SHADOW(`WA/virtual-trading.js:7`) | 종류 열거 | `portfolio:<MODEL|TARGET|ACTUAL|PAPER_SET_x|SHADOW>` | 새 구조는 "모델 적합·사용자·모의" 셋. TARGET이 없다. "사용자"=ACTUAL, "모의"=PAPER로 대응(§2-3 G1) |
| Holding | TARGET `target_units`, ACTUAL 기기 | `company_id` | `listing_id` 기준 | 19개 슬러그에 묶임 |
| Ledger | 가상 원장 시트(`WA/virtual-ledger-sheets.js`), 거래(`WA/private-trades.js`), 전진 원장 | 원장 종류 | 그대로 | 전진 원장(공개, Q·G)과 가상 원장(개인)을 섞지 않음 |
| Report | 일일 템플릿 v1(`WA/daily-report.js:7`), 보고 불가 카드 | `템플릿 v1`·`지침 v1` | `report:<daily|weekly|mock>:<template_version>` | 주간 없음 |
| Prompt | `S/prompt_library/catalog.py`(PLV1, 동결) | 프롬프트 id | 그대로 | 카탈로그 밖 문구: 플레이북 `prompt()`, 보고 `GUIDE_A`(FM B-5). 두 번째 카탈로그 금지 |
| UserProfile / Settings | `investment.web.v1.settings` 외 약 20키 | 브라우저 저장소 키 | 계정 키(없음) → 브라우저 키 → 기본값 | 계정 저장소 없음(IA-6) |
| Experiment | BACKTEST_RESEARCH_PLAN §3(24개 ID, 문서) | `A0-10` 등 | 그대로. 공격·균형·수비, 13F 후보는 새 ID | 시도 기록 코드 없음 |

### 2-2. 필요한 관계

화살표는 "가리킨다"이다. 시각 속성은 [ ]에 적었다.

1. Issuer 1 → n Security 1 → n Listing. Listing = Universe 코드.
2. Company(`company_id`) → Listing. TARGET 19개만. 별칭 관계다.
3. Issuer → SIC [기준 시각]. SIC → IndustryGroup(규칙 버전). Issuer → Profile(FINANCIAL/GENERAL).
4. Issuer → CompanyType(소속도 0~1, 유형 범위 버전). Issuer → Theme(근거 종류 ETF/KEYWORD).
5. Factor → Axis. SubMetric → Factor(방향). WeightProfile → {Axis 비중, Factor 비중}. Preset = 이름 붙은 WeightProfile.
6. Score(Issuer, Factor|Axis, calc_version) [as_of, acquired_at]. V 점수는 기기 관측이며 저장하지 않는다.
7. Listing → PriceSeries(interval, price_basis) [기기]. PriceSeries → TechnicalIndicator(ParameterSet) → Pattern(PatternState) [known_at].
8. UserDrawing → Listing + interval + price_basis + (시간, 가격).
9. MacroIndicator → MacroObservation [available_at, 기준 기간]. Evidence → MacroObservation | Filing | NewsItem.
10. CyclePosition(Economy | Market | IndustryGroup) [as_of, model_version] ← Evidence(n). CyclePosition → Condition(up/hold/down) → Probability(모델 근거 있을 때만).
11. UserPositionNote → 같은 대상(Economy | Market | IndustryGroup). 공식 CyclePosition과 나란히. 덮지 않음.
12. ImpactPath = Concept | NewsEvent → Hop(EXPOSURE/UPSTREAM/DOWNSTREAM/PEER) → Issuer. Hop → Relationship(있으면) + Evidence + 전제·시차·반증.
13. NewsItem | Filing → Issuer [published_at | accepted_at]. NewsItem → Filing(`related_8k_accession`).
14. PriceReaction(Filing | NewsItem, Listing, 기준 ETF) [기기 RAM].
15. Watchlist → Issuer. 뉴스·관계·차트가 같은 목록을 읽는다.
16. Holding(Portfolio, Listing). Report(Portfolio, 기간, template_version) → Prompt(보고 불가 시).
17. Experiment → WeightProfile | Preset | 13F 후보. Experiment → Portfolio(가상).

### 2-3. 불일치 정리

| # | 불일치 | 근거 | 영향 | 권장 |
|---|---|---|---|---|
| G1 | 포트폴리오 종류: 새 구조 3개(모델 적합·사용자·모의) vs 코드 5개(MODEL·TARGET·ACTUAL·PAPER·SHADOW) | `WA/virtual-trading.js:7`, 지시 §9 | TARGET·SHADOW가 화면에서 빠질 위험 | 화면은 셋으로 묶되 TARGET은 "확정 목표", SHADOW는 "규칙대로 했다면"으로 각 그룹 안에 표시 |
| G2 | 기업 키 셋(`company_id`·Universe 코드·CIK) + 관계망 `issuer_id` | §2-1 A | 504 확장 불가, 관계망 연결 불가 | IA-7 |
| G3 | Universe 코드 vs TARGET id vs 엔티티 id | `entities.json` COMPANY는 `company_id`(`entity_catalog.py:53`). 504는 코드(`entity-search.js:100`). `sec-qgv2.json`은 `records`(코드 키)와 `target`(id 키) | 같은 기업이 두 행(TARGET이 자기 발행인 점을 대체, `v2_scoring.py:156-160`) | 화면 키를 Issuer로 통일. TARGET 행은 "TARGET 기준 행"으로 표시 |
| G4 | SIC vs 테마 vs 유형 vs 섹터 ETF vs 옛 섹터 라벨 | §2-1 B | "반도체"가 다섯 곳 | 산업 = SIC 그룹(IA-5). 테마·유형은 독립. 섹터 ETF는 가격 비교 기준으로만. 옛 라벨은 표시 전용 |
| G5 | 프리셋 이름: 코드 `balanced/quality/growth/value` vs 사용자 공격·균형·수비 vs `StrategyStyle` Aggressive/Balanced/Defensive vs EVL 목표 vs 유형 `defensive`(경기방어) | FM A-2 §2, `type_config_v1.json` | "균형"·"수비/방어"가 여러 뜻 | IA-9 |
| G6 | "시나리오" 네 뜻 | §2-1 D | 화면 문구 혼동 | 화면 이름: "가격 시나리오(TA)", "매크로 경로", "보고 원인·시나리오", "가치 시나리오(DCF)" |
| G7 | "Track D" 관계망 vs 영향 경로 설계 | `S/product/web_mvp.py:101-102`(`relationships`는 Track D 렌더 페이지 필요), `:114-118`(`--rig-page` 없으면 `network.html` 삭제), `WA/app.js:1155`(`relationships` 공개 구획 차단). IMP는 `S/rig/` 엔진 확장 | 같은 기능의 세 통로 | 관계망 도메인 하나로. `data.json.relationships`와 운영자 HTML 경로는 퇴역 후보(IA-17) |
| G8 | 중요도 4단계 vs 6단계 | §2-1 F | 정렬 결과가 다를 수 있음 | 6단계 정본, 중요도 산출 전 4단계 |
| G9 | 신규·중복 어휘 | IMP a-5 | `FOLLOW_UP` 표시 불가 | IMP 대응표 유지 |
| G10 | 매크로 엔티티 id: 검색 `CPIAUCSL`(FRED) vs 수집 `CUUR0000SA0`(BLS) | `entity_catalog.py:25-28`, `raw_axes_v0.py:123` | 검색에서 연 지표와 실제 화면 값이 다른 계열 | `source_series_id` 정규, FRED는 별칭 |
| G11 | Evidence 두 갈래 위험 | `S/rig/model.py:153`. 매크로 근거 기록 없음 | 매크로 근거를 새로 만들면 중복 | rig `Evidence` 형태 재사용 |
| G12 | 13F 가중치 메뉴 위치 | 새 구조 1.3 vs `WA/app-shell.js:38-39` Lab | 화면 둘 생길 위험 | IA-2 |
| G13 | Q1~V5 별칭 미정의 | §2-1 C | 사용자 문서와 코드가 어긋남 | IA-8 |
| G14 | 사건 시각 의미 | 공시 `accepted_at`(초), 뉴스 `published_at`(수집원 기준), 매크로 `available_at`(수집 상한) | 근거 수직선·반응 분석 시각이 섞임 | 시각 종류를 필드 이름으로 구분해 보존(지시 §11) |

### 2-4. 만들지 말 것(중복 금지)

- 두 번째 기업 레지스트리. 관계망용·뉴스용 기업 목록을 따로 두지 않는다(`S/rig/model.py:3-5`).
- 두 번째 관심 목록. 뉴스·관계·차트가 같은 목록을 읽는다(지시 §8).
- 두 번째 인과 그래프. 3.5는 `impact.py` 확장이다(IMP a-2).
- 두 번째 근거 기록. 매크로 근거도 rig `Evidence` 형태.
- 두 번째 프롬프트 카탈로그. 개인 수정본은 이미 분리돼 있다(`WA/research-bridge.js:133-140`).
- 사용자 프리셋을 코드 `PRESETS`에 끼워 넣기. `balanced` 키 재사용 금지.
- 두 번째 기간 정의. 기업 수익률 기간은 `WA/report-benchmarks.js:11`의 기간 id를 재사용한다.
- 레이더 전용 동종 집합. 산업 비교군은 QGV와 같은 `industry_group`·최소 8개 규칙(`v2_scoring.py:32`)을 쓴다.

---

## 3. 레이더 추가 축 후보 (QGV가 잘 못 잡는 것)

판정 기준:

- "QGV와 겹침": 이미 Q·G·V 세부 지표에 들어 있으면 "겹침".
- "비교군": 산업 평균(`industry_group`), 경쟁사 평균(경쟁 관계), SIC(같은 4자리 또는 하위 그룹).
- 가격 축은 기기에서만 계산한다. 동종 평균도 기기가 동종 가격을 모두 받아야 한다. Worker는 소유자 1인 분당 12건, 간격 5초 이상이다(TA §4). 동종 50개면 약 4~5분이 걸린다.

### 3-1. 후보 표

| 후보 | 지금 쓸 수 있는 자료 | 가격 의존(기기 전용?) | QGV와 겹침 | 산업 평균 | 경쟁사 평균 | SIC | 상태 |
|---|---|---|---|---|---|---|---|
| 가격 변동성(실현 변동성) | Worker 일봉 5y(`WA/private-history.js`), `Prices_D`. 산식 조각: 원장 √252(`S/qgv/virtual_trading_compare.py:113-126`), 지수 rv20(`WA/macro-lights.js:228` 부근) | 예(기기) | 없음 | 기기에서만. 동종 가격 일괄 요청 필요. 대안: 섹터 ETF 변동성(`WK/index.js:52`) | 불가(경쟁 집합 없음) | 기기에서만 | 없음(기업별 산식 없음) |
| 최대 낙폭 | 같음. 원장 MDD(`virtual_trading_compare.py`), 지수 낙폭(`macro-lights.js`) | 예 | 없음 | 위와 같음 | 불가 | 위와 같음 | 없음 |
| 유동성·거래대금 | Worker 일봉 거래량(FM A-5). 시총은 기기 M3(`WA/private-subset.js:177`) | 예 | 없음 | 위와 같음 | 불가 | 위와 같음 | 없음(ADV 산식 없음) |
| 모멘텀·추세 | `WA/chart-indicators.js` SMA·RSI·MACD(연구 표시) | 예 | 없음(V `v_vs_own_history`는 수익률 역사이지 가격 추세가 아님) | 위와 같음 | 불가 | 위와 같음 | 일부(지표만, 12-1 같은 정의 없음) |
| 베타·매크로 민감도 | 베타: 기업 + SPY 일봉(둘 다 허용 목록). 매크로 민감도: 매크로 이력 필요(FRED 저장 금지, BLS·BEA 원기관은 가능) | 베타 예. 매크로 민감도도 가격 수익률 필요 | 없음 | 위와 같음 | 불가 | 위와 같음 | 없음 |
| 13F 보유 집중도 | `sec-13f-changes.json`: 10기관 수량·SEC 단위 금액. 발행주식수는 `sec-universe-shares.json` | 아니오(공개 SEC 자료) | 없음 | **불가**: CUSIP→Universe504 대응 없음(FM A-6a) | 불가 | 불가 | 일부(TARGET만). 10기관은 2026 선택 명단이라 "기관 보유 집중도"가 아님(13F T8) |
| 뉴스·사건 위험 | `sec-disclosures.json` 8-K 건수·항목, `news-signals.json`(TARGET만, GDELT 429 관측) | 아니오 | 없음 | 불가(504 자료 없음) | 불가 | 불가 | 없음(위험 정의 없음, 검증 없음) |
| 추정치 수정 | 없음. 컨센서스 열 미연결(`WA/leaderboard-screen.js:13`), `earnings_surprise: OMITTED_NO_FREE_SOURCE`(`S/universe/sec_qgv2.py:66`) | — | (V `v_expectation_check`와 일부 목적 겹침) | 불가 | 불가 | 불가 | 없음. 유료 자료 필요 |
| 규모 | 가격 없는 대리값: 매출 `v_inputs_v2.revenue`(`S/universe/sec_qgv2.py:80`, 504 공개). 시총은 기기(M3, 245/504만, M3-COVER) | 매출: 아니오 / 시총: 예 | 없음 | **가능**(매출, 공개 자료로 504 전체) | 불가 | 가능 | 일부(자료 있음, 축 정의 없음) |
| 이익률 안정성(추가 후보) | `operating_margin_std_5y_pp`(GENERAL·FINANCIAL, `S/qgv/v2_factors.py:255-256`) | 아니오 | 없음(Q·G 세부 지표 아님. 플레이북 품질 입력) | **가능** | 불가 | 가능 | 일부(값 공개, 축 정의 없음) |

### 3-2. 공개 파일에 이미 있는 비QGV 지표

| 지표 | 파일·근거 | QGV와 관계 | 레이더 적합성 |
|---|---|---|---|
| `revenue_volatility_5y_rank_pct` | `sec-qgv2.json` `metrics`, 계산 `S/universe/sec_qgv2.py:343-349`, `S/qgv/v2_scoring.py:156` | **겹침.** 원값 `revenue_growth_std_5y`는 `revenue_growth_volatility`와 같은 식(`S/qgv/v2_factors.py:1109,1113`, 관측 5개일 때 동일). 그 값은 G `g_consistency` 세부 지표다(`v2_scoring.py:49`) | 낮음. "QGV가 못 잡는 것"이 아님 |
| `revenue_growth_std_5y` | 같은 파일 | 위와 같음 | 낮음 |
| `moat_return_std_5y` | 같은 파일(서술값) | `moat_proxy`의 입력(`v2_factors.py:1094`) | 낮음 |
| `roic_avg_3y` | 같은 파일(GENERAL) | Q `q_profitability`의 `roic`와 가까움 | 낮음 |
| `operating_margin_std_5y_pp` | 같은 파일 | Q·G 세부 지표 아님 | **높음**(가격 없는 안정성 축) |
| `dilution_3y` | 같은 파일 | Q `q_capital_allocation` 세부 지표(`v2_scoring.py:46`) | 낮음 |
| `v_inputs_v2.revenue` | 같은 파일 | 점수에 직접 안 씀(V 입력) | 중간(규모 대리값) |
| M3 시총 순위 | 기기 전용(`WA/private-subset.js:177`) | 없음 | 중간(가격, 245/504) |
| 13F 변화(NEW/ADD/REDUCE/EXIT) | `sec-13f-changes.json` | 없음. 플레이북 E4 참고 증거만 | 낮음(TARGET만, 10기관) |

### 3-3. 축 조합 메모(결정 아님)

- 비교군 셋 중 지금 계산 가능한 것은 **산업 평균**뿐이다. 그것도 가격 없는 축만 504 전체로 가능하다.
- 경쟁사 평균은 REL-SOURCE가 정해진 뒤에만 가능하다. 그 전에는 "비교군 없음"으로 비운다.
- SIC 비교는 4자리 SIC 안 동종이 8개 미만이면 산업 그룹으로 올린다. QGV와 같은 규칙이다(`METHOD.submetric_fallback`).
- 가격 축 동종 평균은 기기가 동종 가격을 다 받아야 한다. 섹터 ETF 값을 "산업 평균"이라고 부르지 않는다. "섹터 ETF 기준"으로 따로 표시한다.
- 위험이 큰 값을 좋은 점수처럼 그리지 않는다. 축마다 "높을수록 뜻"을 적는다(지시 §4.5).

---

## 4. "주가 반영 여부"를 알 수 있는가

### 4-1. 답

- **"반영됐다"는 직접 알 수 없다.** 가격에 무엇이 들어갔는지는 관측할 수 없다.
- 대신 **사건 전후 가격 반응**은 잴 수 있다. 이것을 "반영 여부 추정"이 아니라 "사건 전후 반응"으로 표시한다(지시 §8).

### 4-2. 방법(사건 연구 방식)

1. 사건 시각을 정한다.
   - 공시: `accepted_at`(초 단위, `S/product/sec_disclosures.py:39`). 미국 장 마감(16:00 ET) 뒤면 다음 거래일이 0일이다.
   - 뉴스: `published_at`. 수집원 시각이라 최초 보도보다 늦을 수 있다. 공시와 묶인 뉴스(`related_8k_accession`)는 공시 시각을 쓴다.
2. 기준 수익률을 정한다.
   - 기본: 같은 날 섹터 ETF(D-22 `S/qgv/sector_etf_map_v1.json`), 없으면 SPY. 둘 다 Worker 허용 목록에 있다(`WK/index.js:52`).
   - 선택: 시장 모형. 사건 전 구간(예: −250~−30일)에서 베타를 추정한다.
3. 비정상 수익 = 기업 수익 − 기준 수익. 누적 구간 예: [−1, +1], [0, +5].
4. 사전 흐름: [−20, −2] 누적 비정상 수익. 미리 움직였는지 본다.
5. 크기 판단: 사건 전 252일 분포 대비 z값. 이미 같은 형태의 커널이 있다(`WA/virtual-trading.js:64-76` `abnormalDrop`: 20세션 상대 수익의 252세션 분포 z). 그대로 쓰지 말고 창만 바꾼 별도 함수로 둔다.
6. 거래량: 사건일 거래량 ÷ 직전 20일 중앙값.

### 4-3. 필요한 자료

- 기업 일봉(종가·거래량, `RAW_CLOSE`)과 섹터 ETF·SPY 일봉: Worker, 기기 RAM.
- 분할·기업행사 이벤트: 없음(TA G1). 창이 분할일을 지나면 `CORPORATE_ACTION_IN_WINDOW`로 판정 불가.
- 같은 창의 다른 사건 목록: 공시·뉴스 파일(교란 표시용).
- 504로 넓히려면 504 공시·뉴스 수집(지금 TARGET만).

### 4-4. 말할 수 있는 것 / 없는 것

말할 수 있는 것:

- "사건 0일~+1일 동안 섹터 기준 대비 x% 움직였다. 평소 분포에서 z = y다."
- "사건 전 20일 동안 이미 z만큼 움직였다(사전 흐름)."
- "같은 창에 다른 사건 n건이 있어 분리할 수 없다."
- "자료 부족 / 기업행사 창 / 판정 불가."

말할 수 없는 것:

- "가격에 n% 반영됐다." 반영률은 만들지 않는다.
- "이미 반영됐으니 더 안 오른다/내린다." 미래 방향을 말하지 않는다.
- "이 반응이 이 사건 때문이다." 인과를 단정하지 않는다. 일봉으로는 장중 순서를 모른다.
- 확률. 표본·검증 없이 쓰지 않는다(B-PROB).
- Q·G 점수 변화. 뉴스는 점수를 바꾸지 않는다(`news_signals.py:77` `score_effect: NONE`).

### 4-5. 경계

- 가격 기반이므로 **기기 전용**이다. 결과를 공개 파일·저장소·로그에 남기지 않는다(B-PRICE).
- CI·Pages 빌드에서 계산하지 않는다.
- 사용자가 차트를 열거나 버튼을 누를 때만 요청한다(결정 Q4, TA §4).
- 문구 고정: "사건 전후 반응 · 반영 여부 추정 아님 · 투자 유용성 미검증".

---

## 5. 결정 후보 IA-1~IA-18

기존 결정 항목과 겹치면 그 번호를 적고, 이 문서에서 새로 생긴 쟁점만 다룬다. IA-1은 결정됨이다. 나머지는 열린 후보다.

| 번호 | 무엇을 | 선택지 | 권장안 | 근거 |
|---|---|---|---|---|
| IA-1 | 3.5 사용자 명칭 — **결정됨** | (검토했던 후보: 영향 경로 / 파급 경로 / 연결 추적 / 사건 연쇄 / 영향 가설 지도) | **결정: "연쇄 효과 지도"** (영문 Causal-chain map). 사용자 결정 2026-10-18(코디네이터 전달). 머리말 "확인된 관계·추론·가설을 나눠 보여 줍니다"는 그대로 권장 | 이 결정은 IMP (c)와 REL-SOURCE의 "영향 경로" 권장을 3.5 화면에서 대신한다. 엔진(`impact.py` `ImpactPath`)과 내부 이름은 바꾸지 않는다. 4.1 관계망 화면의 경로 버튼 문구를 같은 이름으로 맞출지는 결정 기록 반영 때 Main이 정리한다 |
| IA-2 | 13F 가중치 연구 메뉴 위치 | (a) QGV 1.3 (b) Lab (c) 양쪽 별도 화면 | **(a) 메뉴는 QGV 1.3, 화면은 `#lab-13f` 하나.** Lab 개요에서 링크. 실험 등록은 Lab 등록부 | 사용자 최신 구조가 1.3이다. 실험 ID·시도 기록은 Lab 소유(지시 §12). 화면 둘은 중복 |
| IA-3 | 확률 방법론(3.2·3.3, 2.x 시나리오) | (a) 미산출 유지 (b) 과거 빈도(조건부 전이 빈도 + 표본 수) (c) 모형(로지스틱·체제 전환) + 표본 밖 보정 (d) 사용자 주관 확률(3.4, "내 생각" 표시) | **지금 (a). 자료 확보 뒤 (b)부터 Lab에서 검증.** (d)는 사용자 입력으로만 허용. 공식 칸에 섞지 않음 | B-PROB. 빈티지 저장 금지, 가격 5y 한계(BACKTEST_DATA_AUDIT §0). (b)는 설명이 쉽고 표본 수를 그대로 보여 줄 수 있다. 보정 지표(브라이어 점수 등)는 Lab 등록 |
| IA-4 | 사이클 위치 어휘 | (a) 경기 4단계(확장·둔화·수축·회복), 시장 4단계(상승 초기·상승 후기·하락·바닥) (b) 연속 점수 (c) 미정 | **(a)를 표시 어휘로 먼저 고정.** 판정 규칙은 미정 | IMP b-2 후보와 같다. 어휘가 있어야 3.4 사용자 선택을 저장·비교할 수 있다. 판정은 "가설·미산출" |
| IA-5 | 3.2·3.3 산업 단위 | (a) SIC 그룹 v0 10개 (b) (a) + 하위 그룹 확장 (c) 섹터 ETF 13규칙 (d) 테마 (e) GICS | **(b).** 키는 `industry_group`. 섹터 ETF는 가격 비교 기준으로만 | QGV 동종 기준과 같다. 504 전체에 공개돼 있다. `manufacturing_industrial_tech`(2200-3999)는 사이클에 너무 넓다. GICS는 쓰지 않음(`gics_used: false`, 유료). 하위 그룹 추가는 SIC 그룹 설정 변경이라 별도 승인 |
| IA-6 | 로그인 백엔드 | (a) 없음(브라우저 + 백업 파일) (b) 기존 Google 로그인 + 사용자 시트 "Settings" 탭 (c) 새 Worker + KV/D1 (d) 외부 인증 서비스 | **(b).** 전까지 (a)와 "이 브라우저 기준" 표시 | DRAW-STORE (b)와 같은 저장 경로. CSP가 이미 `sheets.googleapis.com`을 허용한다(`WA/index.html:5`). 새 서버 자료가 없다. (c)(d)는 B-LOGIN 별도 승인 |
| IA-7 | 화면 상태의 기업 키(관심·그림·메모·뉴스) | (a) `company_id` (b) Universe 코드 (c) CIK 기반 `issuer_id` (d) C-39 전체 | **관심·메모·뉴스 = Issuer(`sec:` + CIK10). 차트 그림 = Listing(Universe 코드). `company_id`는 TARGET 별칭.** | 관계망 그래프 키가 Issuer다(`S/rig/model.py:108-110`). QGV는 발행인 1점(`sec_qgv2.py:64`). 그림은 가격 좌표라 상장 단위여야 한다. TA G2와 함께 닫는다 |
| IA-8 | Q1~V5 표기 | (a) `WEIGHTS` 순서로 별칭 고정 (b) 별칭 쓰지 않음 | **(a).** Q1 = `q_profitability` … V5 = `v_expectation_check`. 정규 키는 요인 id | 사용자는 Q1~V5로 말한다. 대응표가 없다. 순서 근거: `S/qgv/qgv_v2.py:20-24` |
| IA-9 | 사용자 프리셋 id 이름공간 | (a) 코드 `PRESETS` 확장 (b) 새 이름공간(`qgv-user-preset/v1:aggressive|balanced|defensive`) | **(b).** 코드 프리셋 화면 이름은 "축 비중 시작값" | `balanced` 키 충돌, `StrategyStyle`(Q/G 동결 키) 충돌, 유형 `defensive`(경기방어) 충돌. 수치는 PRESET-NUM |
| IA-10 | 레이더 첫 축 묶음(RADAR-AXES 보완) | 후보는 §3 | **Q·G·V + 이익률 안정성(공개) + 규모(매출, 공개) + 실현 변동성 1y·최대 낙폭 1y·거래대금(기기).** 비교군은 산업 평균만 먼저 | 공개 축 2개는 504 전체 산업 평균이 지금 가능하다. 가격 축은 QGV가 못 잡는 위험을 보여 준다. `revenue_volatility_5y_rank_pct`는 G와 겹쳐 제외. 13F·추정치 수정은 자료가 없다 |
| IA-11 | 손그림 느낌 글꼴 | (a) 시스템 글꼴만(현행 `WA/theme.css:40-42`) (b) OFL 손글씨 글꼴 1종 자가 호스팅, 장식에만 (c) CDN | **(b).** 한글 하위 집합 woff2, 라이선스 파일 동봉, 크기 상한. 본문·숫자는 시스템 글꼴 | CSP `default-src 'self'`라 CDN 글꼴은 막힌다(`WA/index.html:5`). 새 파일은 `T/pages_artifact_guard.py` 허용 목록·해시 고정이 필요하다(Main 소유). 지시 §2: 손그림은 장식에 한정 |
| IA-12 | 기업별 수익률 기간(1.1) | (a) 1D/5D/20D만 (b) `report-benchmarks.js` 기간 id 재사용(1D/5D/20D/60D/120D) (c) + 1Y | **(b).** 1Y는 가격 조정·배당 기준을 정한 뒤 | 기간 정의를 두 벌 만들지 않는다. 지시 §4.4: 60D/1Y는 거래일·조정·배당 정의 뒤. 504 과거 종가 경로가 먼저 필요 |
| IA-13 | 4.1·4.2 검색 없을 때 "매크로 주목 기업" | (a) 숨김 (b) Universe504 무작위 + "매크로 근거 미산출" 표시 (c) SIC 경기민감 후보 라벨 기반 | **(b).** 3.2가 생기면 그 근거로 교체 | 지시 §8: 추천 근거·자료 시각을 표시. (c)는 후보 라벨일 뿐 근거가 아니다(구성원 NA) |
| IA-14 | 5줄 요약 생성 | (a) CI에서 언어 모델 호출 (b) 프롬프트 복사 → 사용자 붙여넣기 → 검토 후 저장 (c) 필드 기반 규칙 문장(사실 줄만) | **(c) 사실 줄 + (b) 가설 줄.** (a)는 외부 연결 승인 뒤 | 앱에 AI 호출 경로가 없다. 붙여넣기·검토 후 저장 흐름이 이미 있다(#299). Q/G 영향은 가설로만 |
| IA-15 | 사건 반응 표시(4.2, §4) | 창·기준·문구 | **창 [−1,+1]·[0,+5], 사전 흐름 [−20,−2], 기준 D-22 섹터 ETF 없으면 SPY, z 표시, 임계값 문구 없음** | 임계값은 Lab 검증 전까지 정하지 않는다. D-5 이상 하락 규칙(가상매매용)과 목적이 달라 설정을 공유하지 않는다 |
| IA-16 | 근거 수직선 시각(3.1) | (a) 수집 시각(현행 상한) (b) 기관 발표 일정(BLS·BEA 공개 일정) (c) ALFRED | **(b) + (a) 표시.** 일정이 없으면 "수집 시각 기준(상한)" | 지금 `available_at`은 수집 상한이다(`S/macro/primary_input.py:42,49`). ALFRED는 저장 금지 판정 |
| IA-17 | 관계 통로 정리(G7) | (a) 현행 셋 유지 (b) 관계망 도메인 하나 + 공개 관계 파일 생산자, `data.json.relationships`·운영자 HTML 퇴역 | **(b), REL-SOURCE 결정 때 함께** | 같은 기능 세 통로. 지시 §7: 별도 중복 그래프 금지 |
| IA-18 | 504 기업 페이지 범위(0) | (a) 현행 식별 카드 (b) Q·G·유형·SIC·공시 창(공개 자료) + 기기 V·차트 | **(b).** 이름은 KR-NAMES 결정 뒤 | 자료가 이미 공개돼 있다(`sec-qgv2.json`). 홈=검색 구조에서 검색 결과의 대부분이 504 코드다 |

---

## 6. 하지 않은 것

- 코드·가드·워크플로·CI 목록 변경.
- CURRENT_HANDOFF·USER_DECISIONS_PENDING·WORKING_RULES·대기열 문서 수정. 위 IA 항목의 결정 기록 반영은 Main이 한다.
- 가격·보유·개인 자료·계정 정보 기록. 예시 숫자도 넣지 않았다.
- 확률·임계값·프리셋 수치 제안.
