# 무료 출처 조합 — 현재 V용 미국 일일 종가

검토일: **2026-10-18 UTC**(2026-10-19 KST). 범위는 중앙 계산 V(QGV의 Value)에 쓸
**미국 상장 약 504개 코드 + SPY의 거래일별 종가 1개**다. 기업행위·주식 수·식별자·환율·
과거 OHLCV는 형제 문서가 다룬다. 이 문서는 [가격 권리 선택안](PRICE_RIGHTS_OPTIONS.md)의
기존 조사(Alpha Vantage, EODHD, Twelve Data, Tiingo, Market Data)를 다시 하지 않고
현행 약관으로 갱신·확장한다.

방법: 공식 가격표·약관·문서만 읽었다. 가입, 키 발급, 인증 API 호출, 공급자 연락,
가격 수집은 하지 않았다. 인증 없이 공개된 메타데이터 2건만 읽었다. IEX HIST 파일
목록(날짜·피드·크기·링크)과 Nasdaq Data Link 데이터표 메타데이터이며 가격 값은 없다.
이 문서와 커밋에는 가격 값이 없다.

## 결론

1. **무료이면서 공식 약관상 파생 점수 공개가 막히지 않은 출처는 IEX HIST 하나뿐이다.**
   IEX Historical Data Terms §01은 배포·판매까지 상정하고 출처 문구만 요구한다.
   다만 값은 **IEX 거래소 단독 마지막 체결가**이고 공식 종가가 아니다. 하루 8~15GB
   pcap 파일을 T+1로 받아 해석해야 한다.
2. **Alpaca 무료 Basic**은 SIP 통합 일봉을 하루 1~2요청으로 받을 수 있어 기술상 가장
   적합하다. 그러나 개인·비상업 조건이고, 타인용 앱은 30일 사전 통지가 필요하다.
   파생 점수 공개 조항이 없어 **서면 확인 전 미확인**이다.
3. **Massive(구 Polygon) 무료 Basic의 grouped daily**는 하루 1호출로 전 종목을 받는다.
   하지만 약관 §5(c)·§5(d)가 파생 저작물의 제3자 제공과 non-display 이용을 금지한다.
   **서면 동의 없이는 불가**다.
4. **Tiingo 무료 Starter는 불가**다. §1.6(a)가 파생 점수의 지속 저장까지 막는다.
   월 고유 심볼 500개도 505개 코드보다 적다. 유료 Power(월 30달러)는 §1.6(c)
   두 요건을 충족한 파생 점수의 보관·배포를 허용한다. 무료 우선 원칙의 예외 후보로만 둔다.
5. FMP, Alpha Vantage, Twelve Data, EODHD, Marketstack, Finnhub, Market Data의 무료
   등급은 한도나 약관 중 하나 이상에서 불충족이다. Nasdaq Data Link에는 현재 무료 미국
   일봉이 없다. Cboe·Nasdaq·NYSE의 무료 공식 종가 파일과 공개 라이선스 일봉 데이터는
   찾지 못했다.

## 유지되는 결정 경계

- 소유자의 중앙 V 승인은 Main을 통해 전달받았다. 하지만
  [결정 기록](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md)에는 아직
  없다. GSQ-001의 Actions 시세 수집 금지와 GSQ-006·007·023의 공개 V 금지는 append-only
  새 기록이 생길 때까지 유효하다. GSQ-010의 공개 원시 가격 금지도 같다.
  이 문서는 금지를 해제하거나 공급자를 채택하지 않는다.
- 원시 가격 공개 권리와 파생 점수 공개 권리는 따로 판정한다. IEX처럼 원자료 배포가
  허용되는 출처라도 **원시 종가·EV·수익률·배율은 공개하지 않는다**. 공개 대상은
  0~100 백분위 점수, 순위, 근거 문구, 커버리지, 기준일뿐이다.
- "무료로 보기·내려받기 가능"을 저장·공개 허가로 해석하지 않는다.
- 공개 값에서 가격을 되살릴 수 없어야 한다. 공개 SEC 수치와 결합해 가격을 역산할 수 있는
  배율(P/E 등)은 근거 문구에 넣지 않는다. 이는 Tiingo §1.6(c)의 금지 예시와 같은 원리다.

## 표 A — 8개 권리

권리 번호: ① 자동 수집 ② 서버·Actions 중앙 계산 ③ 원자료 비공개 저장·캐시
④ 파생 점수·순위 영구 저장 ⑤ 파생 점수 익명 공개 웹 표시 ⑥ 파생 점수 공개 다운로드 JSON
(원시 가격 없음) ⑦ 날짜별 점수·검증 이력 보관 ⑧ 계정·구독 종료 후 보관 가능 범위.

| 출처·플랜 | ① | ② | ③ | ④ | ⑤ | ⑥ | ⑦ | ⑧ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IEX HIST(무료, 계정 표시 없음) | 미확인 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 미확인 |
| Alpaca Basic(무료) | 허용 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 |
| Massive Stocks Basic(무료) | 허용 | 불가 | 미확인 | 불가 | 불가 | 불가 | 불가 | 불가 |
| Tiingo Starter(무료) | 허용 | 허용 | 불가 | 불가 | 불가 | 불가 | 불가 | 불가 |
| *참고: Tiingo Power(유료)* | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 | 허용 |
| FMP Basic(무료) | 허용 | 불가 | 미확인 | 불가 | 불가 | 불가 | 불가 | 불가 |
| Alpha Vantage(무료 키) | 허용 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 |
| Twelve Data Basic(무료) | 허용 | 불가 | 불가 | 불가 | 불가 | 불가 | 불가 | 불가 |
| EODHD Free | 허용 | 미확인 | 허용 | 허용 | 불가 | 불가 | 허용 | 미확인 |
| Marketstack Free | 허용 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 |
| Finnhub Free | 허용 | 미확인 | 허용 | 미확인 | 불가 | 불가 | 미확인 | 불가 |
| Market Data Free Forever | 미확인 | 미확인 | 미확인 | 미확인 | 불가 | 불가 | 미확인 | 불가 |
| Stooq | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 |

칸별 조건:

- **IEX ②~⑦**: HIST 약관에는 이용 제한이 §02(불법 이용·규칙 위반 금지)뿐이다.
  §01은 배포·판매·임대·제공을 상정하고 지정 문구 인용만 요구한다. 파생 점수는 원자료보다
  좁은 이용이지만 **파생물을 직접 언급한 조항은 없다**. 그래서 서면 확인 대상으로 남긴다.
  ①은 자동 다운로드 조항이 없어 미확인이다. iex.io 웹 포털 약관은 이번에 검토하지 않았다.
  ⑧은 계정·종료 조항이 없어 미확인이다.
- **Alpaca**: 약관에 파생 데이터 조항이 없다. 반면 Content의 공개 표시·게시는 서면 동의를
  요구하고, 타인용 앱은 30일 사전 통지가 필요하다. 그래서 ②~⑧을 미확인으로 둔다.
- **Massive ③**: 비공개 저장을 직접 다룬 조항이 없다. §2는 공개·배포 목적의 서버 복제를
  금지한다. **⑧**: §8은 원자료 삭제를 요구한다. 파생물 처리는 명시하지 않았으나 §5(c)가
  이미 제3자 제공을 금지한다.
- **Tiingo Starter ②**: 휘발성 메모리에서 작업 중에만 허용한다. 작업이 끝나기 전에 삭제해야
  한다(§1.6(a)). **Power**: ③은 유료 플랜이 활성일 때만 허용한다(§1.6(b)).
  ④~⑦은 §1.6(c)의 두 요건(대체 불가·역산 불가)을 충족할 때만 허용한다. ⑧은 요건을 충족한
  파생물만 보관할 수 있고 원자료는 삭제해야 한다. 가격표 표시는 "Internal Use Only"다.
  §1.6(c)와 조화되는지 서면 확인이 필요하다.
- **EODHD ③④⑦**: 비공개·비상업 범위에서만 허용한다. 공개 표시는 재포장 형태까지 금지한다.
- **Finnhub ③**: 구독 중에만 허용한다. 종료 시 삭제해야 한다.
- **Marketstack**: 적용 약관 문서를 특정하지 못해 미확인이다. 아래 근거를 본다.

## 표 B — 커버리지·한도·종가 기준·지연

| 출처 | 미국 상장·SPY | 505개 일일 호출 추정 | 무료 한도 | 종가 기준 | 공개 지연 | 키·계정 | 출처 표시 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IEX HIST TOPS | IEX에서 거래된 종목만 포함. ETF 포함 여부는 데이터로 미검증 | 파일 1개/일, 8.0~14.6GB gz(2026-10-07~16 목록) | 요금 없음 | IEX 단독 정규장 마지막 체결가, 원시. 공식 종가는 IEX 상장 종목만 | T+1. 관측 생성 시각은 다음 날 03:25~10:21 UTC | 목록·링크에 키 없음 | 필수(§01 문구) |
| Alpaca Basic | US Stocks & ETFs, SIP 이력 | 1~2요청(요청당 최대 10,000 데이터점, URL 길이 제한) | 200회/분 | SIP 통합 일봉, 기본 raw(split·dividend·all 선택) | SIP 이력은 15분 경과 후 조회 가능. 확정 시각 미확인 | 키 + Alpaca 계정 | 미확인 |
| Massive Basic grouped daily | All US Stocks Tickers. ETF 포함 명시는 미확인 | 1호출/일. 2년 백필은 약 500호출(5회/분) | 5회/분, 2년 이력 | 기본 분할 조정. `adjusted=false`면 원시. 배당 조정 없음 | "End-of-day". 시각 미명시 | 키 | 해당 없음(공개 불가) |
| Tiingo Starter | 미국 주식·ETF·ADR | 종목당 1요청 = 505/일 | 50/시, 1,000/일, **월 고유 500** | 원시 close + adjClose(CRSP 분할·배당) | 대부분 오후 5:30 EST, 정정은 오후 8시 EST까지 | 키 | 재배포 허가 시 "Data sourced by Tiingo" + 링크 |
| FMP Basic | 미국 | 505/일 | 250/일. EOD Bulk는 Basic에 없음 | close·adjusted close | 미확인 | 키 | 표시 자체에 별도 계약 필요 |
| Alpha Vantage | 글로벌 | 505/일 | 25/일 | DAILY는 원시. 조정은 premium | quote는 거래일 종료 시 갱신. 일봉 시각 미확인 | 키 | 미확인 |
| Twelve Data Basic | 미국 EOD | 505 credits/일 | 8/분·800/일(최소 64분 소요) | 미확인 | 미확인 | 키 | add-on 조건 |
| EODHD Free | US | 505/일 | 20/일, 이력 1년. Bulk(100호출)는 Free 제외 | close·adjusted_close | 미확인 | 키 | 미확인 |
| Marketstack Free | 미국(Tiingo 출처) | 요청당 묶음 한도 미확인. 100개 묶음 가정 시 약 126/월 | 100/월, 이력 1년 | 미확인 | 미확인 | 키 | 미확인 |
| Finnhub Free | 미국 quote | `/quote` 505회(60/분이면 약 9분). 일봉 candle은 premium | 60/분 | quote의 현재·전일 값. candle은 분할 조정 | 미확인 | 키 | 미확인 |
| Market Data Free | 미국 | bulkcandles 1 credit/종목 = 505 | 100 credits/일, 이력 1년 | `adjustsplits` 선택(CRSP) | **24시간 지연** | 계정 | 미확인 |

호출 수는 계획 추정치다. 실제로 호출하지 않았다. 재시도·심볼 조회·백필은 포함하지 않았다.

## 출처별 근거

### IEX Exchange HIST — 무료 공식 거래소 데이터

- 플랜: 무료 HIST. 계정 요건 표시는 없다. 확인일 2026-10-18.
  [시장 데이터 표](https://www.iex.io/products/market-data-connectivity)는 "Equities HIST
  Free historical data downloads from IEX equities available on a T+1 basis"라고 쓴다.
  [다운로드 페이지](https://iextrading.com/trading/market-data/)는 페이지가 공개
  `/api/1.0/hist` 목록을 읽는다. 목록은 2016-12-12부터 2026-10-16까지 2,491 날짜다.
  장기간 계속 제공된 근거다.
- [약관](https://www.iex.io/legal/hist-data-terms) §01: "If you distribute, sell, lease,
  furnish, or otherwise permit or provide access to … IEX historical data, you must cite
  IEX as the source with the following text and link: 'Data provided for free by IEX. By
  accessing or using IEX Historical Data, you agree to the IEX Historical Data Terms of Use.'"
  §08·§10은 IEX 외 시장 거래를 반영하지 않는 참고값이라고 고지한다.
- [TOPS v1.66 명세](https://www.iex.io/documents/tops-v1-66): 심볼은 Nasdaq Integrated
  symbology다. Official Price Message(공식 시가·종가)와 Security Directory의 조정 전일
  공식 종가는 **IEX 상장 종목에만** 있다. NYSE·Nasdaq·Cboe 상장 종목은 Trade Report만으로
  마지막 체결가를 구해야 한다.
- 운영 위험: 하루 파일이 8~15GB gz다. Actions 러너에 저장하지 않고 스트리밍 해석해야 한다.
  해석 시간·디스크·대역폭은 검증하지 않았다. 해당 일에 IEX 체결이 없는 종목은
  NOT_AVAILABLE이다. 다른 출처로 채우지 않는다.

### Alpaca Market Data — Basic

- [데이터 요금](https://alpaca.markets/data),
  [Market Data API 안내](https://docs.alpaca.markets/docs/about-market-data-api):
  Basic은 Free이고 실시간은 IEX뿐이다. Historical은 Since 2016, 제한은 "latest 15 minutes",
  호출은 200/min이다. 확인일 2026-10-18.
- [Historical bars](https://docs.alpaca.markets/reference/stockbars): `symbols`는 쉼표 목록,
  `limit`은 전체 데이터점 1~10000, `adjustment` 기본값은 raw, `feed` 기본값은 sip다.
- [Terms and Conditions](https://files.alpaca.markets/disclosures/library/TermsAndConditions.pdf):
  "solely for your own personal and non-commercial purposes". 타인에게 제공하는
  "User Application"은 "30 days advance written notice"가 필요하고 Alpaca가 연결을 제한할 수
  있다. Content는 "publicly displayed … without Alpaca's express prior written consent"가
  금지다. [Customer Agreement](https://files.alpaca.markets/disclosures/library/AcctAppMarginAndCustAgmt.pdf)
  §30: "not to reproduce, distribute, sell or commercially exploit the market data".
  **빠진 조항**: 파생 점수, 저장 기간, 종료 후 보관.

### Massive(구 Polygon) — Stocks Basic

- [가격표](https://massive.com/pricing?product=stocks): Stocks Basic은 $0/month, 5 API
  Calls/Minute, 2 Years Historical, End of Day Data, Individual use다. 확인일 2026-10-18.
- [Daily Market Summary](https://massive.com/docs/rest/stocks/aggregates/daily-market-summary):
  `GET /v2/aggs/grouped/locale/us/market/stocks/{date}`는 "all U.S. stocks"를 반환한다.
  Basic 포함, End-of-day다. `adjusted`는 분할 조정이고 기본 true다.
- [Market Data Terms](https://massive.com/legal/market-data-terms-of-service)(Last Updated
  2025-08-28):
  - §1: "exclusively for your personal, non-business, and non-commercial purposes …
    may not use the Market Data to build an application intended for use by end users other
    than you"
  - §2: "strictly for display use only"
  - §5(c): Market Data 또는 "Derived Works"를 제3자에게 배포·게시하는 것을 금지한다.
  - §5(d): "non-display use or to create derivative works … unless you are licensed"
  - §8: 종료 시 "delete all Market Data"

### Tiingo — Starter(무료)·Power(유료 참고)

- [약관](https://app.tiingo.com/tos/)(Last Updated 2026-10-06, 확인 2026-10-18):
  - §1.6(a) Starter: 원자료와 Derived Product 모두 "persistent or durable storage" 금지.
    로그·백업 등 "operated on your behalf" 시스템에도 적용된다.
  - §1.6(c): "rankings, scores … percentiles"는 두 요건 충족 시 허용될 수 있는 예시다.
    가격과 SEC 수치를 결합한 P/E는 역산 가능 예시다. Tiingo로 다른 EOD를 검증하는 것도 금지다.
  - Starter·Power에는 예외 계약이 없다. 예외는 Start-up·Enterprise·Institutional
    (월 250달러부터)만 받을 수 있다.
  - §7.3: "All data via the API is for internal consumption only". 재배포는 "special request
    and permission".
  - §2.2: "not have more than one Account per platform"
- 기존 가격표 확인값(2026-10-09, [PRICE_RIGHTS_OPTIONS.md](PRICE_RIGHTS_OPTIONS.md#tiingo)):
  Starter는 월 고유 500·50/시간·1,000/일이고, Starter·Power 모두 Internal Use Only다.
  이번에는 가격표가 스크립트 렌더링이라 다시 읽지 못했다.
- [EOD 문서](https://www.tiingo.com/documentation/end-of-day) 본문(사이트 스크립트에서 읽음):
  "Most US Equity prices are available at 5:30 PM EST, however exchanges may send
  corrections until 8 PM EST." 원시·조정 가격은 CRSP 방식이다. 심볼은 하이픈 표기다(`BRK-B`).
- 기존 Secret `TIINGO_API_KEY`는 조사·사용·검사하지 않았다. 실제 계정 플랜은 미확인이다.

### 나머지 후보

- **FMP Basic** — [가격표](https://site.financialmodelingprep.com/pricing-plans),
  [TOS](https://site.financialmodelingprep.com/terms-of-service)(Last updated 2023-08-01),
  [EOD Bulk](https://site.financialmodelingprep.com/developer/docs/stable/eod-bulk):
  - Basic은 250 Calls/Day, EOD, 5년이고, 비교표의 Bulk 행은 Basic이 "-"다.
  - "Displaying or redistributing data sourced from FMP requires a specific Data Display
    and Licensing Agreement"
  - §2.2.1·§2.2.2는 제3자용 도구와 다중 사용자 웹 표시를 금지한다.
  - §2.6.1(i)은 "derived from The Services"의 제3자 제공을 금지한다.
  - §6.2·§6.3은 종료 시 파생 정보까지 파기하도록 요구한다.
  - 일반 브라우저 식별자로만 CloudFront 차단 없이 열렸다.
- **Alpha Vantage** — [지원](https://www.alphavantage.co/support/),
  [문서](https://www.alphavantage.co/documentation/),
  [약관](https://www.alphavantage.co/terms_of_service/):
  - 무료 한도는 25 requests/day다. "verified open-source or educational projects" 예외는
    승인 근거가 없다.
  - Realtime Bulk Quotes는 Premium이다.
  - 약관 §2(a)는 "computer or mobile device … that you own or control, for personal,
    non-commercial use"다. Actions 러너가 여기에 해당하는지, 저장, 파생 공개에 관한 조항은 없다.
  - §7은 종료 시 접근 비활성화만 규정한다.
- **Twelve Data Basic** — [가격표](https://twelvedata.com/pricing),
  [약관](https://twelvedata.com/terms)(Last updated 2026-01-01):
  - Basic은 "Internal non-display usage … testing, evaluation, or development purposes only.
    The data cannot be displayed to users, shared externally, or used in production systems."
  - §2.3(l)은 무료 등급의 상업 이용을 금지한다.
  - §12.5·§16.2는 종료 시 Data 삭제를 요구한다. §6.2는 적법 Derived Data의 고객 권리를 인정한다.
- **EODHD Free** — [가격표](https://eodhd.com/pricing),
  [약관](https://eodhd.com/financial-apis/terms-conditions),
  [Bulk API](https://eodhd.com/financial-apis/bulk-api-eod-splits-dividends):
  - Free는 20 calls/day, 1 yr다. "Bulk downloads are not part of the Free plan."
  - 개인은 "store, manipulate, and analyze … for private, non-commercial purposes"가 허용된다.
    "displaying … in its original or repackaged form"은 금지다.
- **Marketstack Free** — [가격표](https://marketstack.com/pricing):
  - Free는 100 Requests/mo, 1 Year History, "Non-Commercial Use"다.
  - "Stock market data from United States exchanges is licensed and sourced from Tiingo"
  - `marketstack.com/terms`는 Idera APILayer 법무 페이지로 이동한다. 연결된 Master SaaS
    Agreement §16(c)의 Freeware는 "solely for Customer's own testing and evaluation purposes"다.
    이 조항이 Marketstack 무료 API에 적용되는지는 특정하지 못했다.
  - 문서는 로그인 리디렉션이라 묶음 한도를 확인하지 못했다.
- **Finnhub Free** — [약관](https://finnhub.io/terms-of-service),
  [API 명세](https://finnhub.io/static/swagger.json):
  - "not redistribute or share access to data or derived results from the data … without
    written approval"
  - "All data must be deleted should your subscription to that data ends."
  - `/stock/candle`은 "Premium Access Required"다. 가격표는 스크립트 렌더링이라 읽지 못했다.
    60/분은 제3자 자료에만 있다.
- **Market Data** — [가격표](https://www.marketdata.app/pricing/),
  [약관](https://www.marketdata.app/terms/)(Last Updated 2025-08-18),
  [Bulk candles](https://www.marketdata.app/docs/api/stocks/bulkcandles):
  - Free Forever는 100 Daily API Credits, 24h Delayed, 1년이고, bulk는 종목당 1 credit다.
  - "may not distribute the data programmatically as a data feed, an API, or an export file."
  - 종료 시 모든 사본을 삭제해야 한다.
  - 기존 문서의 공개 이용조건 판정(기계 판독 파일 불가)을 유지한다.
  - 30일 trial은 제외한다.
- **Nasdaq Data Link** — 공개 메타데이터:
  - `WIKI/PRICES`는 "does not exist"를 반환한다.
  - `QUOTEMEDIA/PRICES`(EOD Prices)는 `premium: true`다.
  - 현재 무료 미국 일봉 데이터셋은 찾지 못했다. 웹 목록은 스크립트 렌더링이다.
- **Stooq** — 2026-10-18에 `stooq.com`·`stooq.pl`이 연결 재설정으로 열리지 않아 공식 약관을
  확인하지 못했다. 제3자 설명에 따르면 일괄 다운로드와 키 발급에 CAPTCHA가 있다.
  CAPTCHA 자동화는 접근통제 우회이므로 운영 후보에서 제외한다.
- **Cboe·Nasdaq·NYSE 공식** — 무료 일일 종가 파일을 찾지 못했다.
  - [Cboe DataShop](https://datashop.cboe.com/)은 유료 상점이다.
  - [NYSE Proprietary Market Data Pricing Guide](https://www.nyse.com/publicdocs/nyse/data/NYSE_Market_Data_Pricing.pdf)
    (2026-10-09)는 재배포·non-display 요금을 둔다.
  - `nasdaqtrader.com`은 이 환경에서 DNS 실패로 가격표를 확인하지 못했다.
- **공개 라이선스 데이터셋** — 공식 출처의 현재 일일 미국 종가를 명시적 개방 라이선스로 주는
  데이터셋을 찾지 못했다. 업로더가 CC0 등을 붙인 재포장본은 원 공급자 권리를 줄 수 없다.

## 심볼 매핑과 종가 기준

- 내부 코드 `거래소:티커`를 출처별 표기로 바꾸는 **명시적 매핑표**를 둔다. 추측 변환은 하지 않는다.
  - Tiingo는 하이픈(`BRK-B`)이다.
  - IEX는 Nasdaq Integrated symbology다.
  - Alpaca·Massive의 분할 클래스 표기는 공식 문서에서 확인하지 못했다. 각 출처의 참조 목록으로
    검증할 항목이다.
- `GOOGL`/`GOOG`, `FOXA`/`FOX`, `NWSA`/`NWS`는 각 행을 따로 받는다. 한 클래스 가격을 다른
  클래스에 쓰지 않는다. 클래스 합산은 GSQ-020 규칙과 형제 문서의 주식 수 기준을 따른다.
- `NASDAQ:ASML`은 미국 상장 USD 거래 라인만 쓴다. 유로넥스트 가격·환산으로 대체하지 않는다.
  ADR/등록주식 비율은 형제 문서의 식별자 범위다. `BATS:CBOE`는 Cboe BZX 상장 종목이다.
- 현재 V는 **기준일 원시(as-traded) 종가**를 쓴다. 분할·배당 조정은 과거 시점만 바꾸므로
  최신일 값은 같다. 그래도 basis는 항상 기록한다. 날짜별 이력을 다시 계산할 때는 원시 종가와
  해당 시점 주식 수를 짝지어야 한다. 다른 출처나 다른 basis를 이어 붙이지 않는다.
- IEX 값은 `IEX_LAST_TRADE`, Alpaca 값은 `SIP_CONSOLIDATED_DAILY_BAR`로 basis를 표시한다.
  공식 상장시장 종가(`PRIMARY_OFFICIAL_CLOSE`)와 구분한다.

## 추천 순위와 조합

1. **IEX HIST — 1순위(조건부).** 무료 후보 중 권리 근거가 가장 명확하다. 결함은 종가 basis가
   IEX 단독 체결이라는 점과 대용량 파일이다. 화면과 JSON에 basis·출처 문구를 표시하고,
   체결이 없는 종목은 NOT_AVAILABLE로 둔다. 소유자는 이 근사가 V에 충분한지 결정해야 한다.
2. **Alpaca Basic — 2순위(서면 확인 후).** 통합 일봉이고 호출이 적다. 파생 점수 공개 허용과
   타인용 앱 통지 조건을 서면으로 받으면 IEX를 대체하거나 보완할 수 있다.
3. **Massive Basic — 3순위(서면 동의 필요).** 기술상 최적이지만 현행 약관은 불가다.
4. **Tiingo Power — 무료가 아닌 대안.** 무료 원칙을 바꾸는 별도 결정이 필요하다.
   Starter와 기존 Secret으로 대신하지 않는다.

정보 유형별 조합: 일일 종가는 IEX(필요 시 서면 확인을 받은 Alpaca), SPY는 같은 출처를 쓴다.
기업행위·주식 수·식별자는 형제 문서의 공식 출처를 쓴다. 출처 간 상호 검증에 Tiingo를 쓰지
않는다(§1.6(c) 금지). 서로 다른 출처의 값을 같은 날짜에 섞지 않는다. 출처 전환은 새 버전으로
기록한다.

## 제외 — 사유

| 대상 | 사유 |
| --- | --- |
| Yahoo Finance chart 등 비공식 endpoint | 공식 API 아님. 약관 §2(d)(ix)는 사전 허가 없는 자동 수집을 금지한다([기존 조사](PRIVATE_FREE_PRICE_PATH_RESEARCH.md)). GSQ-007의 개인 전용 범위는 공개 중앙 계산에 적용되지 않는다. |
| Nasdaq.com·NYSE.com·Google Finance 화면 등 스크래핑 | 화면 표시가 수집·공개 권리를 주지 않는다. Tiingo §1.4(e)처럼 대부분 약관이 금지한다. |
| CAPTCHA·로그인·지역 차단 우회 | 접근통제 우회다. Stooq CAPTCHA 자동화가 여기에 해당한다. |
| 계정·키 여러 개로 한도 늘리기 | Tiingo §2.2는 플랫폼당 계정 1개다. FMP·Market Data는 일회용 이메일 계정을 금지한다. Twelve Data §2.3(h)는 한도 초과 자동화를 금지한다. |
| 체험판·크레딧성 무료 | Market Data 30일 trial, Twelve Data Free trial, EODHD welcome bonus 500 calls 등. 지속 무료 서비스가 아니다. |
| IEX Cloud | 서비스 종료로 알려져 있다. 이번에 공식 확인하지 않았고 후보로 쓰지 않는다. |

## 미해결 조건

1. **결정 기록**: 소유자의 중앙 V 승인을 GSQ append-only 기록으로 남겨야 한다. 이때 GSQ-001·
   006·007·010·023과의 관계(Actions 가격 취득, 공개 V)를 명시한다.
2. **IEX**: 파생 점수 공개에 §01 문구가 필요한지, 자동 다운로드가 허용되는지(웹 포털 약관 포함),
   계정·종료 조건이 있는지 확인해야 한다. 또 IEX 마지막 체결가를 V 기준 종가로 쓸지 소유자가
   결정하고, 505개 일별 IEX 체결 커버리지를 측정해야 한다. 측정은 가격 비공개 런으로만 한다.
3. **Alpaca**: 공개 비상업 사이트의 파생 점수·순위 공개 허가, User Application 30일 통지
   대상 여부, Actions 서버 이용, 비공개 캐시 기간, 계정 종료 후 파생 점수 보관을 서면으로
   받아야 한다.
4. **Massive**: §5(c)·§5(d)에 대한 서면 동의가 없으면 불가다.
5. **Tiingo**: Power를 고려하려면 "Internal Use Only"와 §1.6(c)가 조화되는지, 점수·순위가 두
   요건을 충족하는지 서면 확인이 필요하다. 계정 실제 플랜과 약관 통지일은 사용자가 확인한다.
6. **공통**: 근거 문구에 배율·EV·수익률·가격 경로를 넣지 않는다. SPY 수익률 경로를 공개하지
   않는다. 공개 JSON에는 점수·순위·근거·커버리지·기준일만 둔다.

## 부록 — 문의 초안(미발송)

받는 곳 후보: IEX 시장데이터팀(연락처는 IEX 공식 표 참조), Alpaca 지원,
Massive 지원(연락처는 약관 §3 참조), Tiingo(약관 §1.6 문의처). 발신자 정보는
소유자가 채운다. 이 초안은 저장만 하고 보내지 않았다.

### 한국어

제목: 공개 비영리 연구 사이트의 파생 점수 공개 가능 여부 문의

안녕하세요. 개인이 운영하는 비영리 투자 연구 사이트(공개 GitHub 저장소와 GitHub Pages)에서
귀사 데이터 이용 조건을 확인하고 싶습니다.

- 사용 데이터: 미국 상장 약 504개 종목과 SPY의 거래일별 종가 1개(필요 시 날짜·심볼만)
- 처리: 하루 1회 GitHub Actions 러너 메모리에서 일시적으로만 사용합니다. 공개 재무 자료와
  결합해 0~100 백분위 점수와 순위를 계산합니다. 작업이 끝나면 원시 값은 삭제합니다.
- 공개: 점수, 순위, 근거 문구(백분위 표현), 커버리지, 기준일만 익명 방문자에게 웹 화면과
  내려받기 JSON으로 공개합니다. 원시 가격, EV, 수익률, 배율은 공개하지 않습니다.
- 보관: 날짜별 점수·검증 이력을 공개 저장소에 계속 남깁니다.

질문:

1. 위 자동 수집과 서버(GitHub Actions) 계산이 무료 플랜에서 허용됩니까?
2. 원시 값의 비공개 임시 저장(최대 기간 포함)이 허용됩니까?
3. 파생 점수·순위의 영구 저장, 웹 표시, 공개 JSON 배포가 허용됩니까? 필요한 출처 문구는
   무엇입니까?
4. 계정이나 구독이 끝난 뒤 이미 공개한 점수 이력을 유지할 수 있습니까?
5. 허용되지 않는다면 가능한 플랜이나 계약은 무엇입니까?

### English

Subject: Permission inquiry — publishing derived scores on a non-commercial public research site

Hello. I run a personal, non-commercial investment research site (a public GitHub repository
served on GitHub Pages) and would like to confirm the permitted use of your data.

- Data: one daily closing price per trading day for about 504 US-listed stocks plus SPY.
- Processing: once a day, used transiently in memory in a GitHub Actions runner. Combined with
  public financial filings to compute 0–100 percentile scores and ranks. Raw values are
  discarded when the job ends.
- Publication: only scores, ranks, reason text (in percentile terms), coverage and the basis
  date, shown to anonymous visitors on web pages and in a downloadable JSON. No raw prices,
  EV, yields or multiples are published.
- Retention: dated score and validation history stays in the public repository.

Questions:

1. Are this automated collection and server-side (GitHub Actions) computation permitted on the
   free plan?
2. Is private temporary storage of the raw values permitted, and for how long?
3. Are permanent storage, web display and public JSON distribution of the derived scores and
   ranks permitted? What attribution is required?
4. May already-published score history be kept after the account or subscription ends?
5. If not permitted, which plan or agreement would permit it?
