# 무료 출처 조사 — V 이외 입력(B 정합성·C 차트·D 백테스트)과 FX (2026-10-18)

작성: 2026-10-18 23:41 UTC / 2026-10-19 08:41 KST. 문서만 바꾼다. 코드·워크플로·게시 파일은 그대로다.
기준: canonical `c948569e`(#322 병합). 미국 일일 종가는 별도 문서가 다룬다. 이 문서는 그 밖의 입력만 다룬다.

**이번에 하지 않은 것.** 가입, 키 발급, 인증 API 호출, 공급자 연락, 가격 데이터 조회. 가격·환율 값은 이 문서에 없다.
**받은 것.** 키 없는 공개 메타데이터 4개만 받았다(SEC 티커 파일 2개, Nasdaq Trader 기호 파일 2개). 약관·문서 페이지를 읽었다. 원본은 저장소 밖 작업 공간에만 있다.

## 0. 결론

- **B(정합성)는 무료로 대부분 된다.** 1순위는 SEC다. SEC는 자동 수집, 저장, 파생값 공개, 원자료 재배포를 모두 허용한다. 식별은 SEC 티커 파일로 504/504 코드가 CIK 하나씩에 묶인다.
- **B의 보조 출처 권리는 갈린다.** OpenFIGI의 FIGI 식별자는 공공 영역이다. Nasdaq Trader 기호 파일은 저작권 조항상 저장·표시가 **미확인**이다. 공개 산출물의 근거로 쓰지 않는다.
- **배당 기준일(ex-date)은 무료로 공개 가능한 출처가 없다.** SEC에는 공시 기준 주당 배당만 있다. 무료 시세 API의 배당·분할 자료는 모두 개인용이며 공개를 막는다.
- **FX는 ASML 1곳에만 필요하다.** ASML Nasdaq 주식은 ADR이 아니고 보통주 자체다(비율 1, 확인 필요). 그래서 ADR 비율 보정이 아니라 **EUR↔USD 환산이 맞는 해법**이다. 단, 역DCF 매개변수가 USD 전용이라 FX만으로는 V가 완성되지 않는다. 출처는 ECB 기준환율 1순위, 연준 H.10 2순위다. 둘 다 무료이고 재사용이 허용된다.
- **C(차트 일봉)는 공개용 무료 출처가 없다.** Tiingo·Massive·Alpha Vantage·FMP 무료 등급은 모두 개인·내부 사용이다. 공개 Pages 차트나 공개 파생 지표의 근거가 되지 않는다.
- **D(백테스트)는 재무만 무료다.** SEC 공시 시점 재무(상장폐지 기업 포함)는 무료다. **상장폐지 종목 가격과 PIT 지수 구성은 무료로 저장·사용이 허용된 출처가 없다.**

## 1. 권리표

판정: **허용 / 불가 / 미확인.** "무료로 받을 수 있음"은 저장·공개 허가가 아니다. 원자료 공개와 파생 결과 공개를 따로 적는다.
항목 번호: ① 자동 수집 ② 서버·Actions 계산 ③ 원자료 비공개 저장 ④ 파생 점수 영구 저장 ⑤ 파생 결과 익명 웹 표시 ⑥ 파생 결과 공개 JSON 다운로드(원자료 없음) ⑦ 날짜별 이력 ⑧ 계정 종료 후 보관.

| # | 출처 · 플랜 · 확인일(UTC) | ① | ② | ③ | ④ | ⑤ | ⑥ | ⑦ | ⑧ | 원자료 공개 |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | SEC EDGAR API(companyfacts·submissions·일괄 ZIP) · 무료, 키 없음 · 2026-10-18 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용(계정 없음) | 허용 |
| S2 | SEC `company_tickers.json`·`company_tickers_exchange.json` · 무료 · 2026-10-18 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용(계정 없음) | 허용 |
| S3 | SEC Financial Statement Data Sets(분기) · 무료 · 2026-10-18 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용(계정 없음) | 허용 |
| S4 | Nasdaq Trader 기호 디렉터리(`nasdaqlisted.txt`·`otherlisted.txt`) · 무료 · 2026-10-18 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 불가 |
| S5 | OpenFIGI API · 키 없음 등급 · 2026-10-18 | 허용 | 허용 | 허용(FIGI) · 미확인(설명 필드) | 허용 | 허용(FIGI) | 허용(FIGI) | 허용 | 허용(계정 없음) | 허용(FIGI) · 미확인(설명 필드) |
| S6 | ECB 유로 기준환율 EXR · 무료, 키 없음 · 2026-10-18(재사용 정책 재확인) | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용(계정 없음) | 허용(무수정·출처 표시) |
| S7 | 연준 H.10 · 무료 · 2026-10-18 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용(계정 없음) | 허용(출처 표시) |
| S8 | Tiingo Starter(무료) · 2026-10-09 기존 조사 재사용 | 허용 | 미확인 | 불가 | 불가 | 불가 | 불가 | 불가 | 불가 | 불가 |
| S9 | Massive(옛 Polygon) Stocks Basic $0 · 2026-10-18 | 허용 | 불가 | 미확인 | 불가 | 불가 | 불가 | 불가 | 불가 | 불가 |
| S10 | Alpha Vantage 무료 키 · 2026-10-18 | 허용 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 불가 |
| S11 | FMP 무료 · 2026-10-18 원문 열람 실패 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 |
| S12 | Wikipedia S&P 500 변경표(레포 사본) · 이번에 재확인 안 함 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 |

### 1-1. 판정 근거(원문 인용)

**S1~S3 SEC.**
- 재사용: “Information presented on sec.gov is considered public information and may be copied or further distributed by users of the web site without the SEC’s permission.” SEC 인장·로고·EDGAR 상표는 쓰지 않는다. [Privacy and dissemination, 2023-11-29 갱신](https://www.sec.gov/about/privacy-information)
- 공정 접근: “Current max request rate: 10 requests/second.” User-Agent 선언이 필요하다. “The SEC does not allow botnets or automated tools to crawl the site.” 정책 안의 스크립트 접근은 허용 범위다. 기존 수집기는 초당 5회 이하다. [Accessing EDGAR data, 2024-06-26 갱신](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- 갱신: “The JSON structures are updated throughout the day, in real time.” submissions는 1초 미만, XBRL API는 1분 미만 지연이다. 일괄 ZIP은 매일 약 03:00 ET에 다시 만든다. `data.sec.gov`는 CORS를 지원하지 않는다. 그래서 서버(Actions) 계산이 맞다. [EDGAR APIs, 2025-04-08 갱신](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- FSDS: “Data sets will be updated quarterly.” 공시에서 추출한 자료이며 정확성은 보장하지 않는다. [FSDS, 2026-09-30 갱신](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets)

**S4 Nasdaq Trader.** 파일은 공식 HTTP·FTP로 제공된다(“updated periodically through-out each day”). 그러나 사이트 저작권 조항이 적용된다.
- “may not be copied, reproduced, transmitted, displayed, performed, distributed, rented, sublicensed, altered, stored for subsequent use … without the prior written consent of Nasdaq … except for one temporary copy in a single computer's memory and one unaltered permanent copy to be used by the viewer for personal and non-commercial use only.”
- 기호 파일에 별도 이용 조건이 있는지는 찾지 못했다. 그래서 ①~⑧은 미확인, 원자료 공개는 불가다. 공개 산출물의 근거로 쓰지 않는다. 쓰려면 Nasdaq 서면 동의가 필요하다. [Symbol directory](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs), [Copyright & Disclaimer](https://www.nasdaqtrader.com/Trader.aspx?id=CopyDisclaimMain)

**S5 OpenFIGI.**
- “Bloomberg … hereby dedicates FIGI Identifiers to the public domain.” 이 헌정은 FIGI 문자열에 대한 것이다. 거래소 코드·종목명 같은 “Related Security Descriptions”는 면책 대상으로만 적혀 있다. 그래서 설명 필드의 저장·공개는 미확인이다. [Terms of Service, 2018-11-27 갱신](https://www.openfigi.com/docs/terms-of-service)
- 한도: 키 없이 분당 25요청, 요청당 10작업. 키가 있으면 분당 250요청·100작업. 검색 API는 키 없이 분당 5요청. 상장폐지 종목은 `includeUnlistedEquities`로 포함할 수 있다. [API 문서](https://www.openfigi.com/api/documentation)

**S6 ECB.** “All publicly available ESCB statistics may be reused free of charge on the condition that the source is quoted … and that the statistics (including metadata) are not modified.” 제3자 자료는 제외다. 원 값은 고치지 않고 보존한다. 환산값은 “ECB 기준환율에서 계산”으로 표시한다. [ESCB 재사용 정책](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html). 공표 시각·키 없는 API·CORS는 [FX_RESEARCH_26E](../pages_cockpit_owner/FX_RESEARCH_26E.md)를 그대로 따른다.

**S7 연준 H.10.** “Unless otherwise indicated, information on Board's website is in the public domain and may be copied and distributed without permission. Please cite to the Board as the source.” [Website disclaimer](https://www.federalreserve.gov/disclaimer.htm). 자료는 뉴욕 정오 매입률이다. 주간 공표이며 국가별 이력은 매주 월요일 16:15에 갱신된다(“updated weekly on Mondays at 4:15 p.m.”). 과거 공표본은 수정되지 않는다. EUR은 1유로당 USD로 표시된다. [H.10 소개](https://www.federalreserve.gov/releases/h10/about.htm), [최근 공표 2026-10-13](https://www.federalreserve.gov/releases/h10/current/default.htm). 자동 접근을 따로 다룬 조항은 찾지 못했다. 공공 영역 조항을 근거로 ①을 허용으로 둔다.

**S8 Tiingo Starter.** [PRICE_RIGHTS_OPTIONS의 Tiingo 절](PRICE_RIGHTS_OPTIONS.md#tiingo)을 그대로 쓴다. 요금제 표기는 “Internal Use Only”다. §1.6(a)는 Starter/Trial의 “any persistent or durable storage”를 금지한다. 원자료와 파생물이 모두 대상이다. §1.6(c)의 파생 결과 배포 허용도 이 저장 금지와 함께 적용된다. 공개 Pages 파일은 저장물이라 ④~⑦은 불가다. ②는 내부 사용 범위 안인지 미확인이다. 이번에는 약관 페이지가 스크립트로만 열려 재조회하지 못했다.

**S9 Massive Stocks Basic.** 무료, 분당 5요청, 2년 이력, 일봉, 기업행사·참조 자료 포함, “license_type: personal”. [Pricing](https://massive.com/pricing)
- 개인 약관: “solely for your own personal, non-commercial, and non-business purposes.” [Individuals ToS, 2025-07-18](https://massive.com/legal/individuals-terms-of-service)
- 시장자료 약관 §(c): “Redistribute, display … the Market Data—or any data, charts, analytics, research, or other works based on, referring to, or derived from the Market Data ("Derived Works") — to any third party”를 금지한다. §(d): “Use Market Data for non-display use or to create derivative works”를 금지한다. §8: 종료 시 “delete all Market Data in your possession”. [Market Data ToS, 2025-08-28](https://massive.com/legal/market-data-terms-of-service)
- 그래서 서버 계산(비표시 사용)과 파생 공개가 모두 불가다. 분할·배당 자료도 같은 약관이다.

**S10 Alpha Vantage.** 소유자 결정으로 OFF다(GSQ-001). 무료 키는 하루 25요청이다. 분할(`SPLITS`)·배당(`DIVIDENDS`)·상장/상장폐지 목록(`LISTING_STATUS`, 2010-01-01 이후 날짜 지정 가능)은 문서상 키로 호출한다. 수정 일봉(`TIME_SERIES_DAILY_ADJUSTED`)과 `outputsize=full`은 Premium이다. [문서](https://www.alphavantage.co/documentation/)
- 약관 §2(a): “on any computer or mobile device … that you own or control, for personal, non-commercial use.” Actions 실행기는 소유 기기가 아니다. 그래서 ②는 미확인이다.
- §2(a)(iii): “use or provide information … as part of any type of commercial activity that allows individuals or entities other than User to access information directly or indirectly”는 상업 사용이다. 무료 공개 사이트가 여기에 드는지 원문으로 정해지지 않는다. 그래서 ⑤⑥은 미확인이다.
- 저장·보관 조항은 없다. §7은 종료 시 접근 중지만 적는다. 그래서 ③④⑦⑧은 미확인이다. [Terms of Service(PDF)](https://www.alphavantage.co/terms_of_service/)

**S11 FMP.** 약관·요금 페이지가 이 환경에서 HTTP 403(CDN 차단)으로 열리지 않았다. 검색 요약에는 무료 하루 250요청, 개인용 표기가 보였다. 원문 확인 전이라 전부 미확인이다. [Terms of Service](https://site.financialmodelingprep.com/terms-of-service)

**S12 Wikipedia.** 레포의 기존 사본과 [BACKTEST_DATA_AUDIT](../backtest/BACKTEST_DATA_AUDIT.md) D1 판단을 따른다. 표 제목이 “Selected changes”라 누락 가능성이 있다. 이번에 이용 조건을 다시 읽지 않았으므로 미확인으로 둔다.

### 1-2. 제외한 출처와 이유

| 출처 | 제외 이유 |
|---|---|
| Yahoo Finance 차트·이벤트 호출 | 비공식 엔드포인트. 기존 결정으로 운영 출처 아님. |
| Stooq CSV | 2026-10-18 조회 시 자바스크립트 작업증명(브라우저 검증) 페이지가 응답했다. 자동 수집은 접근 제한 우회가 된다. 공식 API·이용 조건도 없다. |
| EDGAR 전문 검색 JSON(`efts.sec.gov`) | 공식 FAQ는 화면 검색만 설명한다(2001년 이후 전문). API 문서에 없는 내부 엔드포인트다. 화면 수동 조회만 둔다. [FAQ](https://www.sec.gov/edgar/search/efts-faq.html) |
| FRED/ALFRED | 기존 판정 유지. 약관상 저장·캐시·제3자 제공 제한(PIPELINE_DESIGN D5). FX도 FRED 경유가 아니라 원기관(ECB·연준)에서 받는다. |
| EODHD 무료, Twelve Data Basic | 개인 약관이 원형·재포장 자료의 공개·재배포를 금지(기존 조사 2026-10-09). |
| GOOGLEFINANCE 이력 | 공식 안내상 Sheets API·Apps Script로 역사 자료를 가져올 수 없다. 기기 현재가 경로만 유지. |
| Nasdaq Daily List, NYSE 기업행사 파일 | 이번에 이용 조건을 확인하지 못했다. 유료 구독 여부도 미확인. 후보로 올리지 않는다. |
| 여러 계정·여러 무료 키로 한도 늘리기, 체험판 반복 | 지속 불가. 약관 회피. 금지. |
| 화면 스크래핑(거래소·포털 시세 페이지) | 금지. |
| CRSP, Norgate, Sharadar, S&P DJI 구성 | 유료. 무료 우선 범위 밖. 기존 감사 문서의 유료 후보로만 남긴다. |

## 2. FX — ASML

- **필요한 곳은 V 1곳이다.** GENERAL 434곳 중 공시 통화가 USD가 아닌 곳은 NASDAQ:ASML 하나다([V_GENERAL_COVERAGE](../qgv_scoring_standard/V_GENERAL_COVERAGE_20261018.md) 2-2절). 다른 V 입력에는 FX가 필요 없다. 아일랜드 등 외국 법인 19곳은 Nasdaq Trader 이름에 “Ordinary Shares”가 있지만 ADR이 아니다.
- **ADR 비율 문제가 아니다.** Nasdaq Trader는 ASML을 “New York Registry Shares”로 적는다. 504개 중 이 표기는 ASML 하나다. “American Depositary” 표기는 0개다. ASML 20-F(검색 요약)는 Nasdaq 주식을 별도 예탁증서가 아닌 등록 보통주로 설명한다. 그래서 주식수(IFRS `AdjustedWeightedAverageShares`, 보통주)와 Nasdaq 주식은 1:1로 예상된다. **최신 20-F 표지와 Item 9 원문 확인 전까지 비율 1은 확인 대상이다.**
- **그래서 FX가 맞는 해법이다. 하지만 FX만으로는 부족하다.**
  1. EV: 같은 날짜의 FX로 USD 가격을 EUR로(또는 재무를 USD로) 바꾼다. 같은 통화일 때만 EV를 만든다.
  2. 자기 역사 요인: 월말 종가마다 그 월말 FX가 필요하다.
  3. 역DCF: 매개변수가 USD 전용이다. 이는 FX가 아니라 **방법론 결정**이다. 결정 전에는 이 요인만 NA로 둘 수 있다.
  4. 환산 방향(가격→EUR 또는 재무→USD)과 기준 시각은 소유자 결정이다. 결정 전에는 현행 `CURRENCY_BASIS_UNCONFIRMED`를 유지한다.
- **출처 우선순위.** ① ECB EXR `D.USD.EUR.SP00.A`(USD/EUR, TARGET 영업일 16:00 CET 전후, 키 없음). ② 연준 H.10 EUR(USD/EUR, 뉴욕 정오, 주간 공표라 최대 약 1주 지연). 두 값은 기준 시각이 달라 섞지 않는다. 미국 종가(16:00 ET)와도 시각이 다르다. 이 차이를 표시한다.
- **휴일.** ECB는 TARGET 휴일에 값이 없다. 직전 영업일 값을 쓰면 그 날짜를 따로 적는다. 0이나 1로 채우지 않는다.
- **비용 대비.** 1곳을 위해 새 입력 경로를 여는 일이다. NA 유지도 정당한 선택이다.

## 3. 매핑표

목적: A=공식 V(별도 문서), B=정합성 점검, C=차트·레이더·기술 분석, D=과거 백테스트. 우선순위는 ①이 먼저다. 표를 두 개로 나눈다. 같은 행 번호가 같은 입력이다.

### 3-1. 출처·수량·주기

| # | 입력 | 목적 | 이미 있음? | 무료 1순위 → 대체 | Universe 매핑 수(측정) | 갱신 주기·지연 | 일일 호출·한도 |
|---|---|---|---|---|---|---|---|
| 1 | 분할·역분할 이벤트 | B, C, D | 부분: `SPLIT_RATIO_CONCEPTS` 사실, 주식수 재작성 연결(SPLIT 규칙) | ① SEC companyfacts 분할비율 사실 + 같은 기간 주식수 재작성 → ② SEC submissions 8-K 항목 코드(이미 파싱) → ③ 표지 주식수 급변(V-SHARES-SCALE) | 미측정(사실 태그 유무는 기업별). 알려진 누락: BKNG(25:1, 분할비율 사실 없음) | 공시 시점. 분할 실행일보다 늦을 수 있음 | 기존 SEC 수집 안. 추가 0 |
| 2 | 배당 이벤트(기준일·금액) | C, D | 아니오 | SEC는 공시 기준 주당 배당 선언액만(`CommonStockDividendsPerShareDeclared` 등). **기준일은 무료 공개 가능 출처 없음** | — | 분기 공시 | — |
| 3 | 기업행사: 분사·합병·티커/CIK 변경·상장폐지 | B, D | 부분: 8-K 항목, 레지스트리 | ① SEC 티커 파일 매일 대조 + submissions(8-K, Form 25 등 서식) → ② OpenFIGI(상장 상태) → ③ Nasdaq Trader(점검 신호만) | 측정: Nasdaq Trader 없음 2(PSKY, WBD). 새 CIK 2(XOM 2115436, HONA 2089271) | SEC 티커 파일 갱신 시각 미확인. submissions 1초 미만 | SEC 1~2회 + 대상 CIK만 |
| 4 | 주식수 기준(희석·표지·종류 차원) | A 보조, B | 예: `v_inputs_v2` 희석 주식수, 표지 주식수, V-SHARES-SCALE | ① SEC companyfacts(차원 없는 사실) → ② 공시 XBRL 인스턴스(차원 사실, 새 경로·승인 필요) | 희석 주식수 결측 10곳(V 커버리지 문서). 그중 종류 차원만 있음: V, HSY, STZ, BKR | 공시 시점 | 기존 7샤드 수집 안 |
| 5 | 증권 식별: 상장 ↔ CIK | B, C, D | 예: `universe_registry`(SEC 티커·거래소 파일) | ① SEC `company_tickers_exchange.json` → ② OpenFIGI(거래소+티커 → FIGI) → ③ Nasdaq Trader(점검 신호만) | SEC 504/504, CIK 501개, 충돌 0. Nasdaq Trader 502/504 | 1일 1회 | SEC 1회. OpenFIGI 51요청(키 없이 약 3분) |
| 6 | 주식 종류(다중 종류·종류 태그) | B | 예: `share_class_groups/v0`(3그룹) | ① SEC 표지 XBRL(종류별 주식수) → ② OpenFIGI share-class FIGI → ③ Nasdaq Trader 이름(점검만) | 한 CIK에 Universe 코드 2개: 3(GOOGL/GOOG, FOXA/FOX, NWSA/NWS). Universe 밖 다른 보통주 종류 상장: 5(BRK-A, BF-A, LEN-B, TAP-A, MKC-V). 이름에 “Class”: 43 | 공시 시점 | 기존 수집 안 |
| 7 | ADR·외국 상장 기준 | A 보조, B | 부분: CIK·통화 | ① SEC 20-F 표지·Item 9 → ② OpenFIGI 증권 유형 → ③ Nasdaq Trader 이름 | “Registry/Depositary” 1(ASML). “American Depositary” 0. “Ordinary Shares” 19 | 연 1회(20-F) | 거의 0 |
| 8 | EUR/USD 일별 | A(ASML) | 아니오(26E 조사만) | ① ECB EXR → ② 연준 H.10 | 필요 1곳(ASML) | ECB 영업일 16:00 CET. H.10 주 1회 | ECB 1회. H.10 주 1회 |
| 9 | 일봉 OHLCV(원시) | C, D | 아니오(기기 경로만) | **공개용 무료 출처 없음.** 내부용 후보: Tiingo Starter(저장 금지), Massive Basic(2년, 개인) | 미측정(가격 미조회 원칙) | — | Tiingo 1,000/일·50/시간, Massive 5/분 |
| 10 | 조정 계수(분할·배당 반영) | C, D | 아니오 | 분할 계수는 1번에서 만들 수 있음. 배당 반영은 2번이 막혀 **무료 불가** | — | — | — |
| 11 | 거래일 달력 | C, D | 예: 레포 Nasdaq 달력 PDF(2021~2025) | 레포 사본 → 거래소 공지 | — | 연 1회 | 0 |
| 12 | PIT 재무(공시본·접수 시각) | D | 부분: companyfacts·submissions·FSDS 표본 2분기 | ① SEC FSDS(as-filed) + submissions 접수 시각 → ② companyfacts(최신값, PIT 아님) | 현재 504 CIK. 상장폐지 CIK도 EDGAR에 남음 | 분기 | 분기 ZIP 1개 |
| 13 | PIT 식별·티커 이력 | D | 아니오 | **무료 체계 출처 없음.** SEC 티커 파일은 현재값만. OpenFIGI는 현재 매핑 중심 | — | — | — |
| 14 | 상장폐지 종목 가격·정산 | D | 아니오 | **무료로 저장·사용 허용된 출처 없음** | — | — | — |
| 15 | PIT 지수 구성(S&P 500 등) | D | 부분: 현재 구성 + 2025-03 이후 변경 34건 | **공식 무료 출처 없음.** 근사: Wikipedia 변경표(누락 가능), 지수 ETF의 SEC N-PORT 보유 목록(보유 ≠ 지수 구성) | — | N-PORT 분기 | — |

### 3-2. 키·기준·권리·남은 문제

| # | 식별 키 | 시간 기준·통화·단위 | 조정 기준 | 권리(1절 행) | 남은 문제와 확인 방법 |
|---|---|---|---|---|---|
| 1 | CIK + accession | 공시 `filed`·acceptance(ET). 비율 `pure` | 주식수 재작성 비율로 방향 판정 | S1 허용 | 분할비율 사실이 없는 분할(BKNG). → 8-K 항목·표지 주식수 급변을 함께 본다. 분할 실행일(거래 기준)은 SEC에 없을 수 있다. |
| 2 | CIK | 회계 기간·USD/주 | — | S1 허용(선언액). 기준일 출처 없음 | 차트 배당 조정·총수익은 무료 공개 불가. → 가격 원천 계약에서 해결. |
| 3 | CIK, 티커, FIGI | 공시 접수 시각. 티커 파일 시각 미확인 | — | S1·S2 허용, S5 FIGI 허용, S4 미확인 | WBD가 Nasdaq Trader에 없는 이유 미확인. → SEC submissions에서 Form 25·8-K Item 3.01 확인(다음 정기 수집). PSKY↔SKYD: SEC는 한 CIK에 두 티커, Nasdaq Trader는 SKYD(NYSE)만. → 코드 갱신 여부는 소유자 결정. |
| 4 | CIK + accession + 차원 | 기간 종료일·주 | 분할 연결(SPLIT) | S1 허용 | 종류 차원만 있는 희석 주식수(V, HSY, STZ). → SH-BASIS 결정 후 XBRL 인스턴스 경로. Alphabet 의무전환 우선주(GOOGM, GOOGN) 상장 → 희석 주식수 영향 확인. |
| 5 | (거래소, 티커) → CIK | 파일 취득 시각 | — | S2 허용, S5 허용, S4 미확인 | SEC 거래소 표기가 거칠다(SPY를 “NYSE”로 표기, 실제 NYSE Arca). → 거래소 대조는 Nasdaq Trader·OpenFIGI로 점검만. BRK.B는 SEC `BRK-B`, Nasdaq Trader `BRK.B`. OpenFIGI 표기는 호출 전이라 미확인. |
| 6 | CIK + 종류 | 공시 표지 기준일 | 전환비율(BRK.A:BRK.B 등) | S1 허용 | Nasdaq Trader 이름에 종류가 없는 곳: V(“Visa Inc.”), HSY·STZ(“Common Stock”). → 종류 태그는 기호 파일이 아니라 SEC 표지 XBRL로만. |
| 7 | CIK + 증권 유형 | 20-F 연 1회 | 예탁 비율(ASML은 1 예상) | S1 허용 | ASML 비율 1 → 최신 20-F 표지·Item 9 원문 확인. |
| 8 | 통화쌍 + 기준일 | ECB: 16:00 CET. H.10: 뉴욕 정오. 1유로당 USD | 없음(원값) | S6·S7 허용 | 환산 방향·기준 시각·역DCF 매개변수는 소유자 결정. 가격 날짜와 FX 날짜를 따로 표시. |
| 9 | 티커(공급자 기호) | 세션일·USD | 원시 | S8 불가(저장), S9 불가 | 공개 차트는 무료로 불가. → 별도 종가 문서·유료 재배포 계약. 기기 직접 조회(사용자 키)는 같은 값 공개가 아님. |
| 10 | — | — | 분할만 가능 | — | 배당 조정 불가. → 차트를 “분할만 조정”으로 표시할지 결정 필요. |
| 11 | 거래소 | ET | — | 레포 사본 권리 미확인 | 2026 이후 달력 사본 필요. |
| 12 | CIK + adsh | 접수 시각 | — | S3 허용 | FSDS 2분기 표본만 확인됨. → 나머지 분기 표본 확인. |
| 13 | — | — | — | — | 무료 해결 없음. → 유료 영구 ID 또는 범위 축소. |
| 14 | — | — | — | — | 무료 해결 없음. |
| 15 | — | — | — | S12 미확인, S1(N-PORT) 허용 | 공식 PIT 구성은 유료. N-PORT는 2019년 이후 공개(기존 감사 문서 가정)라 2016~2018을 못 채운다. |

## 4. 측정한 매핑 수

받은 파일(키 없음, 2026-10-18 23:34 UTC): SEC `company_tickers.json`·`company_tickers_exchange.json`(각 10,443행), Nasdaq Trader `nasdaqlisted.txt`(5,634행)·`otherlisted.txt`(7,674행). Nasdaq Trader 파일 생성 표시는 `10/16/2026 21:31`이다. 시간대는 적혀 있지 않다(미확인).
대상: `universe_codes_v1.json` 504코드(NYSE 343, NASDAQ 160, BATS 1). 규칙은 레포 `universe_registry`와 같다(`.`→`-`, CBOE 별칭 1쌍).

| 점검 | 결과 |
|---|---|
| SEC 거래소+티커 → CIK 1개 | **504/504.** 충돌 0, 미해결 0. 고유 CIK **501** |
| SEC 티커만(`company_tickers.json`) | 504/504 |
| 한 CIK에 Universe 코드 2개 | 3쌍: GOOGL/GOOG, FOXA/FOX, NWSA/NWS(= `share_class_groups/v0`) |
| Universe CIK 중 SEC 파일에 다른 티커도 있는 곳 | 76곳(대부분 우선주·채권·워런트). 보통주 다른 종류: BRK-A, BF-A, LEN-B, TAP-A, MKC-V(5곳) |
| Nasdaq Trader 기호+시장 일치 | **502/504.** 시장 불일치 0. 없음 2: NASDAQ:PSKY, NASDAQ:WBD |
| Nasdaq Trader 시험 종목(Test Issue=Y) | 0 |
| Nasdaq 상장 Financial Status | 158/158 정상(N) |
| ETF 표시(ETF=Y) | Universe 안 0. SPY는 Universe 밖, `otherlisted` 거래소 P(NYSE Arca), ETF=Y |
| “New York Registry/Depositary” 이름 | 1(ASML). “American Depositary” 0 |
| “Ordinary Shares” 이름 | 19(ACN, AON, LYB, LIN, MDT, ETN 등 외국 법인) |
| 이름에 “Class” | 43 |
| 식별 변화 신호 | XOM → CIK 2115436(ExxonMobil Holdings). 옛 CIK 34088은 SEC 티커 파일에 없음. HONA → 새 CIK 2089271(분사). PSKY → SEC에 PSKY(Nasdaq)·SKYD(NYSE) 둘, Nasdaq Trader엔 SKYD만 |

이 수는 공개 메타데이터 기준이다. 가격·시가총액과 무관하다. 순위나 적격성 판정이 아니다.

## 5. 검증 표본(모두 `universe_codes`에 있는 코드, SPY만 예외)

| 경우 | 코드 | 확인할 것 |
|---|---|---|
| 최근 분할(분할비율 사실 없음) | NASDAQ:BKNG | 25:1 분할 후 주당 이력 NA가 유지되는지. 8-K 신호로 분할을 잡는지 |
| 다른 최근 분할 | NASDAQ:NFLX(약 10:1), NASDAQ:ORLY, NASDAQ:FAST, NASDAQ:IBKR | 분할비율 사실 유무를 기업별로 확인하고 재작성 연결 결과를 대조 |
| 역분할 | NYSE:AMCR | 방향 판정 |
| ADR·외국 상장 | NASDAQ:ASML | 비율 1 확인, EUR 재무 + USD 가격, `CURRENCY_BASIS_UNCONFIRMED` 유지 또는 FX 환산 |
| 다중 종류(같은 경제권) | NASDAQ:GOOGL / NASDAQ:GOOG | 비상장 B주 포함 합산, 의무전환 우선주 GOOGM/GOOGN 영향 |
| 다중 종류(전환비율 ≠ 1) | NYSE:BRK.B | `BRK-B`/`BRK.B` 표기, BRK-A 합산 금지 |
| 다중 종류(의결권만 다름) | NASDAQ:FOXA / NASDAQ:FOX, NASDAQ:NWSA / NASDAQ:NWS | 표지 종류 수 2 |
| 종류 태그만 있는 희석 주식수 | NYSE:V, NYSE:HSY, NYSE:STZ | SH-BASIS 전 NA 유지. 기호 파일 이름으로 종류 판정하지 않기 |
| Universe 밖 종류가 상장된 곳 | NYSE:BF.B, NYSE:LEN, NYSE:TAP, NYSE:MKC | 한 종류 가격 × 전체 주식수 혼합 금지 |
| 주식수 단위 오류 | NYSE:MCD, NYSE:WAT | V-SHARES-SCALE 차단 유지 |
| 가격 누락·늦음 후보 | NASDAQ:WBD, NASDAQ:PSKY | 기호 파일에 없음 → 가격 없음으로 표시, 0 채우기 금지 |
| 새 CIK·짧은 이력 | NYSE:XOM, NASDAQ:HONA | 전신 CIK로 대체하지 않기, 이력 부족은 NA |
| 비표준 시장 | BATS:CBOE | CBOE 별칭 1쌍만 적용 |
| ETF 기준선 | SPY(Universe 밖) | NYSE Arca, ETF=Y. companyfacts V 입력 없음. 기준선 전용 |

## 6. 무료 출처가 해결하지 못하는 것

1. **공개 가능한 일봉 OHLCV 이력(C).** 무료 등급은 모두 개인·내부용이거나 미확인이다.
2. **배당 기준일과 배당 조정 계수(C, D).** SEC에는 기준일이 없다.
3. **상장폐지 종목 가격·정산(D).** 무료로 저장·사용이 허용된 출처가 없다. Alpha Vantage `LISTING_STATUS`는 목록만 주고 개인용이며 OFF다.
4. **PIT 지수 구성(D).** 공식 무료 출처가 없다. Wikipedia·N-PORT는 근사다.
5. **PIT 티커·종류 이력(D).** SEC 티커 파일은 현재값만이다.
6. **ASML 역DCF 통화 기준.** FX가 아니라 방법론 결정이다.

무료로 되는 것: SEC 재무·공시·식별(상장폐지 기업 재무 포함), FIGI 식별자, ECB·연준 환율.

## 7. 소유자 결정 후보(제안만)

- **FX-ASML:** ECB 환산 도입 / NA 유지. 도입 시 환산 방향·기준 시각·역DCF 처리.
- **ID-CHECK:** Nasdaq Trader를 비공개 점검 신호로만 쓸지. 공개 산출물 근거로는 서면 동의 전 사용 안 함.
- **PSKY·WBD 코드:** 승인 목록 갱신 여부(이 문서는 바꾸지 않음).
- **CHART-ADJ:** 무료로 배당 조정이 안 되므로 차트를 “분할만 조정”으로 표시할지, 유료 계약을 기다릴지.

## 8. 출처와 확인일

모두 2026-10-18 UTC 조회(Tiingo·EODHD·Twelve Data는 2026-10-09 기존 조사).
SEC: [Privacy and dissemination](https://www.sec.gov/about/privacy-information) · [Accessing EDGAR data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) · [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) · [FSDS](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets) · [Full-text search FAQ](https://www.sec.gov/edgar/search/efts-faq.html) · [company_tickers_exchange.json](https://www.sec.gov/files/company_tickers_exchange.json).
Nasdaq Trader: [Symbol directory](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs) · [Copyright & Disclaimer](https://www.nasdaqtrader.com/Trader.aspx?id=CopyDisclaimMain).
OpenFIGI: [Terms](https://www.openfigi.com/docs/terms-of-service) · [API](https://www.openfigi.com/api/documentation).
FX: [ESCB 재사용 정책](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html) · [FX_RESEARCH_26E](../pages_cockpit_owner/FX_RESEARCH_26E.md) · [연준 disclaimer](https://www.federalreserve.gov/disclaimer.htm) · [H.10 소개](https://www.federalreserve.gov/releases/h10/about.htm).
시세 API: [Massive pricing](https://massive.com/pricing) · [Massive Individuals ToS](https://massive.com/legal/individuals-terms-of-service) · [Massive Market Data ToS](https://massive.com/legal/market-data-terms-of-service) · [Alpha Vantage 문서](https://www.alphavantage.co/documentation/) · [Alpha Vantage 약관](https://www.alphavantage.co/terms_of_service/) · [FMP 약관(403)](https://site.financialmodelingprep.com/terms-of-service) · [Tiingo 기존 조사](PRICE_RIGHTS_OPTIONS.md#tiingo).
ASML 상장 형태(검색 요약, 원문 미열람): [20-F FY2020](https://www.sec.gov/Archives/edgar/data/937966/000093796621000007/asml-20201231.htm).
관련 레포 문서: [PRICE_RIGHTS_OPTIONS](PRICE_RIGHTS_OPTIONS.md) · [PIPELINE_DESIGN](PIPELINE_DESIGN.md) · [V_GENERAL_COVERAGE](../qgv_scoring_standard/V_GENERAL_COVERAGE_20261018.md) · [BACKTEST_DATA_AUDIT](../backtest/BACKTEST_DATA_AUDIT.md) · [SEC_8K_DISCLOSURES](SEC_8K_DISCLOSURES.md).
