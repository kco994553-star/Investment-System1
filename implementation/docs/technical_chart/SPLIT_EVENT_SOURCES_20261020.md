# 분할 이벤트 출처 비교 (무료 우선)

조회일: **2026-10-20 UTC**. 문서만 바꾼다. 코드·키·가격은 넣지 않았다.

관련: [기술 차트 설계 §7.3](TECHNICAL_PATTERN_CHART_V1_DESIGN.md), PR #361(Worker 분할 블록, 미병합·미배포), [개인 무료 주가 경로 조사](../daily_data_pipeline/PRIVATE_FREE_PRICE_PATH_RESEARCH.md).

## 0. 이 문서의 전제

- 소유자 결정(2026-10-20): Worker 배포는 **보류**다. Yahoo 경로 확장은 약관 문제가 풀릴 때까지 승인되지 않는다.
- Yahoo 응답에 split 블록이 없으면 **"분할 정보 미확인"(`NOT_REPORTED`)** 이다. "분할 없음 확인"이 아니다.
- 확인은 **확인 범위와 겹치는 분석 창에만** 적용한다. 창 일부가 범위 밖이면 미확인이다. #361에 합성 시험을 더했다.
- 이 문서는 권리를 만들지 않는다. 약관에서 찾지 못한 것은 **미확인**으로 적는다.

## 1. 기존 Yahoo 호출 경로의 권리 — 미확인

- 현재 Worker의 Yahoo chart 호출 자체도 사용권이 확인되지 않았다. 분할 이벤트만의 문제가 아니다.
- [Yahoo 약관](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) 표시 갱신일 **2026-08-04**(2026-10-20 재확인). 원문:
  > "access or collect data … from our Services using any automated means … for any purpose without our express, prior permission."
- 저장소의 기존 판정 "무허가 자동 조회 부적합"(GSQ-007, [조사 문서](../daily_data_pipeline/PRIVATE_FREE_PRICE_PATH_RESEARCH.md))을 그대로 둔다.
- `events=split` 추가는 요청 수를 늘리지 않지만 권리 문제를 풀지도 않는다.

## 2. 비교 기준

| 기준 | 뜻 |
|---|---|
| 자동 접근 | 약관이 API·자동 조회를 허용하는가. 인용·확인일. |
| Worker 중계 | 본인 Worker가 받아 본인 기기로 넘기는 것이 허용되는가. |
| 범위 | 종목·시장·기간. |
| 필드 | 분할 날짜와 비율. |
| 정정 | 취소·정정 처리. |
| 범위 질의 완전성 | "이 기간에 분할 없음"을 적극적으로 말할 수 있는가. |
| 비용 | 무료 한도. |

## 3. 후보별 요약

| 출처 | 자동 접근 | Worker 중계 | 범위 | 날짜·비율 | 정정 | "없음" 확인 | 비용 |
|---|---|---|---|---|---|---|---|
| Yahoo chart `events=split` (현재) | **불허**(사전 허가 필요) | 불허와 같다 | 미국·한국·일본 종목, 실측 미확인 | `date`(초), numerator/denominator | 미확인 | **불가**. 블록 누락은 미확인 | 무료, 키 없음 |
| SEC EDGAR (data.sec.gov, XBRL·8-K) | **허용**(공정 접근 정책, 10 req/s, User-Agent 선언) | 서버 측 조회는 정책 범위 안. 재배포 조항 미확인 | 미국 SEC 등록사만 | XBRL 비율은 있음. 효력일은 보장 안 됨 | 정정 공시(10-K/A 등)로 | **불가** | 무료, 키 없음 |
| Tiingo EOD `splitFactor` (현재 대체 경로) | 허용(개인 계정·키) | **내부 사용만**. 본인 기기 표시 범위 미확정 | 미국 EOD 종목 | 행별 계수. 날짜=행 날짜 | 미확인 | 행 단위로는 가장 가깝다. 단 공급자 기록일 뿐 | Starter $0 |
| Tiingo Splits 엔드포인트 | 위와 같다 | 위와 같다 | EOD와 같은 종목 | exDate, splitFrom, splitTo, splitFactor | **splitStatus a/c(취소)** | 미확인 | 접근 조건이 문서 안에서 엇갈림 |
| Massive(구 Polygon) `/stocks/v1/splits` | 허용(개인·비영리, Non-Professional) | **"display use only"**, non-display 사용 금지. 판정 사용 허용 여부 미확인 | 미국 주식 | execution_date, split_from, split_to, adjustment_type | 미확인 | 미확인 | Basic 무료: 5 calls/min, 분할 2년 |
| EODHD `/api/splits` | 허용(개인 Non-Professional) | 저장·분석 허용. 재전송·표시 제공 금지. 본인 기기 중계 해석 미확인 | 여러 거래소 | date, "new/old" 문자열 | 미확인 | **불가**(공급자가 빈 배열은 모호하다고 명시) | Free 플랜 포함(이력 1년만) |
| Alpha Vantage `SPLITS` | 허용(개인·비상업) | 라이선스는 "본인이 소유·통제하는 컴퓨터·기기". Worker 해당 여부 미확인 | 미확인 | 응답 필드 미확인(키 없이 조회 안 함) | 미확인 | 미확인(기간 인자 없음) | 무료 25 req/day |
| FMP `stable/splits` | 저장소 기록(2026-10-09)만. 오늘 재확인 실패 | 미확인 | 미확인 | numerator/denominator(공급자 안내글) | 미확인 | 미확인 | 무료 포함 여부 미확인 |
| Nasdaq Daily List | 유료 계약·사전 승인 | 회사 단위 계약 | Nasdaq 상장 종목만, 1999년부터 | 분할 통지 포함 | 15분 단위 갱신 | 상장사 통지 기반. 개인 이용 불가에 가깝다 | 월 $1,750→$3,500(2024 제안, 현재가 미확인) |
| Stooq | 미확인(접속 실패) | 미확인 | 미확인 | 분할 목록 제공 여부 미확인 | 미확인 | 미확인 | 미확인 |
| Finnhub | 미확인(문서가 스크립트로만 열림) | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 | 미확인 |

## 4. 후보별 근거

### 4.1 SEC EDGAR

- [EDGAR API 안내](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) (표시 갱신 2025-04-08):
  > "These APIs do not require any authentication or API keys to access."
  > "data.sec.gov does not support Cross Origin Resource Scripting (CORS)."
  - 기기 직접 조회는 안 된다. 본인 Worker 같은 서버 측 조회만 가능하다.
- [공정 접근](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) (표시 갱신 2024-06-26): "Current max request rate: 10 requests/second." User-Agent에 연락처를 선언해야 한다.
  - [Privacy and Security Policy](https://www.sec.gov/privacy) (2023-11-29): "unclassified" 봇은 허용하지 않는다.
  - 연락처 값은 소유자가 정한다. 저장소에는 넣지 않는다.
- SEC 사이트 자료의 재배포 조항은 이번에 찾지 못했다. **미확인**이다.
- **XBRL 태그.** `us-gaap:StockholdersEquityNoteStockSplitConversionRatio1`, 형식 `pureItemType`, 기간 `duration`.
  - 정의: "Ratio applied to the conversion of stock split, for example but not limited to, one share converted to two or two shares converted to one." ([공시 렌더링 예](https://www.sec.gov/Archives/edgar/data/824142/000082414215000014/R7.htm))
  - 비율만 담는다. 효력일은 맥락(context)에 따라 다르고 보장되지 않는다.
  - 10-Q·10-K 같은 정기 보고에 늦게 나온다. 회사가 태그를 쓰지 않거나 자체 태그를 쓸 수 있다.
- **8-K.** [Form 8-K](https://www.sec.gov/files/form8-k.pdf) (SEC 873 (02-25))에는 분할 전용 항목이 없다.
  - 분할은 Item 8.01(기타), 5.03(정관 변경. 역분할에서 흔함), 3.03(권리 변경) 등으로 흩어진다. 보도자료(Item 7.01)만 있는 경우도 있다.
- **SEC 공시에서 분할을 찾지 못한 것은 "분할 없음"의 확인이 아니다.**
  - 태그 누락, 자체 태그, 항목 분산, 정기 보고 지연, 비SEC 등록 종목 때문에 범위 질의 완전성이 없다.
  - SEC는 "공시에 분할 언급 있음" 보조 표시로만 쓸 수 있다. `CONFIRMED`의 근거로 쓰지 않는다.

### 4.2 Tiingo

- [약관](https://app.tiingo.com/tos/) "Last Updated Date: October 6th, 2026" (2026-10-20 확인).
  - §7.3: "All data via the API is for internal consumption only." 재배포는 별도 허가·요금이다.
  - [가격표](https://www.tiingo.com/about/pricing): "Internal use means you may only use the data for your own personal use and you may not display or share the data with another person or organization".
  - §1.6(a): Starter·Trial은 휘발성 메모리에서만 처리한다. 지속 저장은 금지다. 기존 RAM 전용 설계와 맞는다.
- **중요(§1.6(c))** — 금지 예시에 다음이 있다.
  > "using Tiingo Data to validate, reconcile, or confirm another dataset, including, without limitation, using Tiingo end-of-day data to validate another end-of-day dataset."
  - 따라서 **Tiingo 분할 정보로 Yahoo 가격의 연속성을 확인하는 것은 약관상 금지 예시에 해당한다.**
  - Tiingo 분할 정보는 Tiingo가 준 가격 계열 자체에만 쓴다. #361은 Tiingo 행의 `splitFactor`를 Tiingo 응답 안에서만 쓴다.
- [EOD 문서](https://www.tiingo.com/documentation/end-of-day): `splitFactor`는 "The factor used to adjust prices when a company splits, reverse splits, or pays a distribution."
  - 1이 아닌 값이 분할이 아니라 분배일 수 있다. #361은 1이 아닌 값을 모두 분할로 기록한다. Tiingo 가격 기준이 `UNADJUSTED`라서 그 창은 판정 불가가 된다. 잘못 확인하는 쪽이 아니라 보수적인 쪽으로 틀린다.
- [Splits 문서](https://www.tiingo.com/documentation/corporate-actions/splits): `exDate`, `splitFrom`, `splitTo`, `splitFactor`, `splitStatus`(a 유효, c 취소).
  - 같은 페이지가 "Beta-enabled customers and enterprise customers"와 "included for all customers with the End-of-Day endpoint entitlement"를 함께 적는다. 무료 접근은 **미확인**이다.
- 범위 질의: EOD 응답은 받은 모든 세션 행에 `splitFactor`를 둔다. 행 단위 "1.0"은 가장 직접적인 "그날 기록 없음"이다. 다만 공급자 기록이며 독립 확인은 아니다.

### 4.3 Massive (구 Polygon)

- [Splits 문서](https://massive.com/docs/rest/stocks/corporate-actions/splits): "Included in all Stocks plans".
  - Basic 무료 이력 2년, 유료 전체(1978-10-25부터), 매일 갱신.
  - 필드: `execution_date`, `split_from`(이전 주식), `split_to`(새 주식), `adjustment_type`(forward_split / reverse_split / stock_dividend), `historical_adjustment_factor`. 필터·정렬이 있다.
- [가격표](https://massive.com/pricing?product=stocks): Stocks Basic은 5 API Calls / Minute, 2 Years Historical Data, Corporate Actions 포함.
- [Market Data Terms](https://massive.com/legal/market-data-terms-of-service) "Last Updated: August 28, 2025":
  - "personal, non-business, and non-commercial purposes", "you may not use the Market Data to build an application intended for use by end users other than you."
  - "any and all Market Data is strictly for display u[se only]", §(d) "Use Market Data for non-display use or to create derivative works … unless you are licensed to do so".
  - 자동 연속성 판정이 non-display 사용인지는 **미확인**이다. 서면 확인 전에는 쓰지 않는다.
- 빈 결과가 "없음"이라는 보증 문구는 찾지 못했다. **미확인**.

### 4.4 EODHD

- [Splits·Dividends 문서](https://eodhd.com/financial-apis/api-splits-dividends): `from`·`to` 포함 범위, 비율 문자열 "new/old"(예 `10.000000/1.000000`).
  - "In plans: … and Free (1 year of history only) plans".
- 공급자 스스로 빈 배열을 모호하다고 적는다.
  > "An empty array is ambiguous … the company genuinely has no such events …, the window you asked for contains none …, the instrument has no corporate actions by nature …, or your date failed to parse."
  - 잘못된 날짜도 HTTP 200과 빈 배열을 준다. **"없음" 확인 불가.**
- [약관](https://eodhd.com/financial-apis/terms-conditions) (표시 연도 2017-2026, 개별 갱신일 미표시):
  - "Non-Professional Users are permitted to store, manipulate, and analyze the data for private, non-commercial purposes."
  - 금지: "Selling, reselling, retransmitting, redistributing, displaying, or granting access to the Information or Services".
  - 본인 Worker → 본인 기기가 "retransmitting"인지 **미확인**이다.
- 무료 일일 호출 한도는 공식 페이지에서 확인하지 못했다(제3자 글은 20/day). **미확인**.

### 4.5 Alpha Vantage

- [문서](https://www.alphavantage.co/documentation/): "Corporate Action - Splits … This API returns historical split events." 인자는 `symbol`, `datatype`뿐이고 기간 인자는 없다. `TIME_SERIES_DAILY_ADJUSTED`는 Premium이다.
- [지원](https://www.alphavantage.co/support/): 무료 25 API requests per day.
- [약관 PDF](https://www.alphavantage.co/terms_of_service/) (PDF 수정 2026-08-27):
  - "install, use, access, display and run the software on any computer or mobile device … that you own or control, for personal, non-commercial use".
  - 본인 Cloudflare Worker가 "own or control"에 해당하는지 **미확인**이다.
- 응답 필드와 빈 결과의 의미는 키 없이 조회하지 않아 **미확인**이다.

### 4.6 FMP

- 오늘 공식 페이지 요청이 CDN에서 403으로 차단됐다. 차단을 우회하지 않았다.
- 저장소 기록(2026-10-09, [조사 문서 §7](../daily_data_pipeline/PRIVATE_FREE_PRICE_PATH_RESEARCH.md)): TOS 개정 2023-08-01, 개인·비상업. 가격표에 "requires a specific Data Display and Licensing Agreement with FMP".
- 분할 엔드포인트 `stable/splits`의 numerator/denominator는 공급자 안내글 기준이다. 무료 포함·범위·완전성은 **미확인**이다.

### 4.7 거래소 공지

- [Nasdaq Daily List](https://www.nasdaqtrader.com/Trader.aspx?id=DailyListPD): "Dividends: Provides notification of cash dividends, stock dividends and stock splits to Nasdaq securities." 1999년 이후 이력.
  - "firms must submit the appropriate documentation and receive prior approval from Nasdaq".
- [SR-NASDAQ-2024-027](https://www.sec.gov/files/rules/sro/nasdaq/2024/34-100416.pdf) (2024-06-25): 월 $1,750 → $3,500 제안. 15분마다 갱신.
  - 실행 정보는 NasdaqTrader.com 공개 웹에도 게시한다고 적는다. 그 웹의 이용 조건은 오늘 접속 실패로 **미확인**이다.
- NYSE 대응 상품은 조사하지 않았다. **미확인**.
- FINRA Daily List는 OTC 종목용이라 이 대상(거래소 상장 종목)에 맞지 않는다.

### 4.8 그 밖

- Stooq: 접속이 연결 재설정으로 실패했다. 약관·분할 목록 모두 **미확인**. 제외한다.
- Finnhub: 문서가 스크립트로만 열려 확인하지 못했다. **미확인**.
- 한국(KRX)·일본: 이 문서 범위 밖이다. KRX 경로는 이벤트가 없어 계속 `NOT_AVAILABLE`이다.

## 5. 판단

- 다음 세 가지를 모두 만족하는 무료 출처를 찾지 못했다.
  - 자동 조회와 본인 Worker 중계가 약관상 분명히 허용된다.
  - 기간 안에 분할이 없음을 적극적으로 말한다.
  - 현재 가격 출처(Yahoo)와 같은 계열을 확인하는 데 쓸 수 있다.
- 다른 공급자의 분할 목록으로 Yahoo 가격을 확인하는 것은 공급자마다 막히거나 미확인이다. Tiingo는 금지 예시에 명시돼 있다.
- SEC는 자동 접근이 가장 분명하지만 "없음"을 확인하지 못한다. 보조 표시용이다.

## 6. 권고

1. **기본값 유지.** 분할 정보가 확인되지 않은 창은 계속 판정 불가로 둔다. #361 동작 그대로다(`NOT_REPORTED`, 범위 밖 창은 `CORPORATE_ACTION_COVERAGE_GAP`).
2. **같은 출처 안에서만 확인.** 가격을 준 공급자가 함께 준 분할 정보만 그 가격 계열에 쓴다. 다른 공급자의 분할 정보로 교차 확인하지 않는다.
3. **Tiingo 대체 경로.** Tiingo 가격 계열에는 Tiingo 행의 `splitFactor`를 쓴다. 분배로 1이 아닌 값이 오면 지금은 판정 불가로 끝난다(보수적). 분배와 분할을 나누려면 Splits 엔드포인트가 필요하다(D3, 코드 변경은 별도 승인).
4. **SEC는 보조로만.** 쓴다면 "공시에 분할 언급 있음" 안내 문구로만 쓴다. `CONFIRMED`에 쓰지 않는다. 서버 측 조회와 연락처 User-Agent가 필요하다.
5. **Massive·EODHD·Alpha Vantage·FMP**는 서면 확인 전에는 쓰지 않는다. 확인할 질문은 §7에 있다.
6. **Yahoo.** 권리가 확인될 때까지 배포 보류를 유지한다.

## 7. 소유자 결정이 필요한 것

| # | 결정 | 선택지 |
|---|---|---|
| D1 | Yahoo 경로 | (a) Yahoo에 서면 허가 요청 (b) 1순위에서 내림 (c) 보류 유지. 현재는 (c). |
| D2 | Tiingo 행 `splitFactor`를 Tiingo 가격 계열의 "확인"으로 인정할지 | 인정 / 미인정. 인정하더라도 Yahoo 확인용은 아니다(§1.6(c)). 본인 계정 플랜과 2026-10-06 약관 적용 시점도 확인. |
| D3 | Tiingo Splits 엔드포인트 접근 | 본인 계정에 열려 있는지 Tiingo에 문의할지. |
| D4 | Massive에 서면 문의 | "본인 Worker를 거쳐 본인 기기에서 분할 정보로 자동 연속성 판정을 하는 것이 display use 범위인가". 문의 / 안 함. |
| D5 | EODHD·Alpha Vantage 문의 | 본인 Worker → 본인 기기 중계가 "retransmitting" 또는 "own or control" 밖인지. 문의 / 안 함. |
| D6 | SEC 보조 표시 | 도입 / 안 함. 도입 시 User-Agent 연락처를 소유자가 정한다(저장소에 넣지 않음). |
| D7 | 유료 출처 검토 | 무료로 "없음" 확인이 안 되면 유료 개인 플랜(예 EODHD 개인 EOD, 저장소 기록 $19.99/월)을 검토할지. Nasdaq Daily List는 회사 계약이라 제외 권고. |

## 8. 하지 않은 것

- 키 발급·API 호출·실가격 조회를 하지 않았다. 공급자 응답 형식은 문서 기준이다.
- 차단(FMP 403)을 우회하지 않았다. 접속 실패(Stooq, NasdaqTrader 약관)는 미확인으로 남겼다.
- 코드·Worker·배포를 바꾸지 않았다.
