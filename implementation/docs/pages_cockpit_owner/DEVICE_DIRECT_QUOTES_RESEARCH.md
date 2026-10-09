# Device direct quotes — official-document research

조회 기준일 / 모든 아래 공식 문서 검색·열람일: **2026-10-09**.
상태: **RESEARCH ONLY / OPTIONAL FUTURE / USER DECISION REQUIRED**.

## 범위와 현재 결정

현재 선택된 **26E①: 증권앱에서 확인한 시세·환율을 기기에서 수동 입력하고 KRW 환산을 표시**하는 흐름을 유지한다. 이 문서는 향후 사용자가 본인의 무료 market-data API key를 모바일 브라우저에만 보관하고 provider → device로 시세를 받는 선택지를 조사한다. 이 PR에서 API 옵션을 채택하거나 구현하지 않는다.

공식 공개 문서만 검색·열람했다. 가입, key 발급, 로그인, 계좌 연결, provider API 호출, CORS 헤더 관찰, 실제 quote/FX 응답 수집을 하지 않았다. 문서 웹페이지에 포함된 가격·환율은 근거로 사용하거나 이 문서에 전재하지 않았다. public JSON, 빌드 출력, 저장소, backend, proxy, 자동화 서버에 key·시세·개인 보유정보를 보관하는 대안은 범위 밖이다.

**결론: 현재 ELIGIBLE 제공자는 없다.** Twelve Data / Alpha Vantage / Finnhub / EODHD는 `PARTIAL`, KIS Open API의 계좌 연결 App Key / App Secret 방식은 `NOT_ELIGIBLE`이다. 이는 아래 공식 자료와 명시된 미확인 gate를 적용한 **본 조사 판단**이며 서비스 이용 승인이나 법률 판단이 아니다. `PARTIAL`은 구현 승인도, 브라우저에서 작동한다는 뜻도 아니다.

## 판정 기준

| 판정 | 이 프로젝트에서의 뜻 |
| --- | --- |
| ELIGIBLE | 공식 문서로 CORS/해당 정적 origin의 직접 호출 허용, 주문·계좌 접근 불가능한 key 범위, 원하는 정확한 quote의 무료 entitlement, 충분한 quota, 본인 기기 개인 표시 권한이 모두 확인됨 |
| PARTIAL | 일부 긍정적 문서가 있으나 하나 이상의 필수 gate가 미확인; 채택·실행하지 않음 |
| NOT_ELIGIBLE | 명시적 금지 또는 hard gate 위반. **주문 가능한 key는 호출 코드를 조회 전용으로 제한한다고 약속해도 제외** |

공식 CORS 허용 문구를 찾지 못한 경우는 **미확인**이지 “CORS를 지원하지 않는다”는 단정이 아니다. REST/JSON, NodeJS 예제, 브라우저로 열리는 문서, SDK, 거래소·symbol 검색 결과는 static GitHub Pages → provider quote endpoint 직접 호출 가능성이나 무료 price entitlement를 증명하지 않는다. CORS가 미확인이면 **no-backend 정적 배포 실현 가능성은 UNKNOWN**이다. 미확인 gate를 proxy/backend로 우회하지 않는다.

## 정확한 조사 대상: 공개 identity만

아래 label/ticker는 `implementation/src/investment_system/product/device_actual_catalog.py`가 지정한 공개 identity map인 `implementation/docs/security_map19_owner/v1_1_cycle_20261008/CURRENT_TARGET_IDENTITY_MAP.json`의 `target_row.label` / `ticker_hint`만 읽어 확인했다(2026-10-09). 수량·평균단가·보유금액을 읽지 않았다. 이는 provider symbol mapping이나 quote coverage 검증이 아니다.

| 구분 | 공개 label | 원본 ticker hint | 5개 provider의 이 정확한 상장 quote 무료 coverage |
| --- | --- | --- | --- |
| US | ASML Holding | ASML | 각각 미확인 |
| US | Lam Research | LRCX | 각각 미확인 |
| US | KLA Corporation | KLAC | 각각 미확인 |
| US | NVIDIA | NVDA | 각각 미확인 |
| US | Advanced Micro Devices | AMD | 각각 미확인 |
| US | Broadcom | AVGO | 각각 미확인 |
| US | Qualcomm | QCOM | 각각 미확인 |
| US | Intel | INTC | 각각 미확인 |
| US | Microsoft | MSFT | 각각 미확인 |
| US | Alphabet | GOOGL | 각각 미확인 |
| US | Amazon | AMZN | 각각 미확인 |
| US | RTX Corporation | RTX | 각각 미확인 |
| US | Stryker | SYK | 각각 미확인 |
| US | Eaton | ETN | 각각 미확인 |
| US | Hubbell | HUBB | 각각 미확인 |
| US | GE Vernova | GEV | 각각 미확인 |
| US | Rockwell Automation | ROK | 각각 미확인 |
| TSE | Tokyo Electron | 8035 | 각각 미확인; Twelve Data Basic 일반 entitlement는 아래에서 제외 |
| KRX | 한미반도체 | 042700 | 각각 미확인; Twelve Data Basic 일반 entitlement는 아래에서 제외 |

`ASML`을 네덜란드 상장으로, `GOOGL`을 다른 Alphabet share class로, `8035`/`042700`을 임의 provider suffix로 치환하지 않았다. 정확한 provider symbol + 거래소/MIC + 통화 + quote endpoint entitlement는 향후 별도 검증 대상이다. “US market 지원”은 US17 개별 성공의 증명이 아니다.

## 공급자별 공식 문서 결과

각 `[...]`는 맨 아래 **공식 URL + 열람일 + 문서 구간**에 대응한다. 미확인은 해당 자료에서 입증되지 않았다는 조사 결과다.

| 제공자 | 무료 quota / 19개 하루 1회 조건 | 시세 종류·시장 entitlement | 본인 개인 표시 / key 범위 / CORS | 판정 |
| --- | --- | --- | --- | --- |
| Twelve Data Basic | 무료 8 credits/min, 800/day. credits는 endpoint weight × symbol 수로 소비됨. 1-credit quote가 허용된다면 19/day 산술상 충분하지만 한번에 19개 요청은 minute quota 초과 가능 [TD1, TD2] | Basic 문서는 US real-time 제공. Japan XJPX와 Korea XKRX의 최소 individual plan은 Pro; Basic의 8035/042700 가격 권한으로 해석하지 않음. XJPX delay 표시는 `–`여서 freshness 미확인 [TD1, TD3]. US17 각각의 quote 접근 미확인 | Individual은 personal/internal use이고 redistribution·third-party commercial display 불가. metadata listing과 price subscription은 다르다고 명시 [TD4]. 문서상 market-data 서비스이나 credential-level 주문/계좌 불가 보장·read-only scope는 미확인 [TD5, TD6]. GitHub Pages/mobile browser quote CORS 명시 미확인 [TD6] | **PARTIAL**; US17-only 후보, 무료 19 전체 자동화 후보 아님 |
| Alpha Vantage | 기본 무료 25 requests/day. GLOBAL_QUOTE는 1 ticker/request이므로 19개 1회는 19 calls, 잔여 6; 검색·재시도·FX는 추가 소모 [AV1, AV2] | 기본 quote는 거래일 종료 때 갱신. US real-time 및 15-minute delayed quote는 premium 개인 entitlement 필요 [AV2]. US17 / 8035 / 042700 각각 실제 무료 quote coverage 미확인 | 본인 소유/통제 컴퓨터·모바일 기기에서 personal non-commercial 사용·표시 허용; 금융업 관련 신분 등 commercial 분류 조건 확인 필요 [AV3]. market-data endpoint 문서일 뿐 credential-level read-only scope 및 주문/계좌 불가 보장 미확인. static browser quote CORS 미확인 [AV2] | **PARTIAL**; 무료 EOD가 사용자 요구에 맞는 경우만 검토 |
| Finnhub | 공식 pricing 검색 결과에서 60 API calls/min 표기는 발견했으나 Free column 귀속·daily cap·현재 free quote entitlement의 본문 교차검증은 **미완료**. 따라서 19/day 충족 확정은 **미확인** [FH1]. 모든 plan에 추가 30 calls/sec 제한 명시 [FH3] | 공식 Quote 검색 결과는 US real-time quote를 설명. 국제 시장 real-time quote free 권한, US17 각각, 8035/042700 free quote는 미확인 [FH2] | personal plan은 personal only, business internal use 및 professional 조건 제한. data뿐 아니라 derived results도 written approval 없이 제3자 공유 불가 [FH3]. token/header 인증 안내는 있으나 credential-level read-only scope·주문/계좌 불가 보장은 미확인 [FH4]. static browser CORS 명시 미확인 [FH2, FH4] | **PARTIAL**; free quota/entitlement 원문 검증도 남음 |
| EODHD Sandbox / Free | 현재 pricing은 20 calls/day, 20 requests/min. EOD/live 1 call이라면 19/day 산술상 가능, 여유 1; intraday 5 calls 등 endpoint별 비용 주의 [EH1]. 별도 limits 문서는 default 1,000 requests/min이라 pricing과 차이가 있어 free의 보수적 값 20/min 사용 [EH2] | 현재 pricing은 free EOD 1년, live/delayed 15-min, live US extended quote 포함; intraday·real-time WebSocket 미포함 [EH1]. “Global” 표시는 정확한 US17/8035/042700 free quote의 증거가 아님. 약관은 거래소 feed 대신 market-maker/OTC 등 집계 기반 indicative 가격이고 실제 시장가격과 다를 수 있음을 명시하므로 공식 거래소 가격으로 표시하지 않음 [EH3] | private personal 투자 목적 저장·분석은 허용하나 금지 목록에 `displaying`도 포함됨. 본인 기기만의 비공개 화면 표시까지 허용되는지 **미확인**, provider 해석 확인 필요 [EH3]. token 인증은 문서화되나 credential-level read-only 범위·주문/계좌 불가 보장 미확인 [EH4]. static browser CORS 미확인 [EH4] | **PARTIAL**; 표시권한 해석 gate 때문에 우선 권고하지 않음 |
| KIS Open API — 계좌 App Key/App Secret | 공개 문서만으로 current free ≥19/day·고객별 quota·해외 market entitlement를 확정하지 않음. 2026-04-20 유량 공지와 신규 고객 제한 공지 제목은 있으나 상세 본문 수치는 미확인 [KI4] | 국내·해외 주식 시세 기능이 있다는 문서와 샘플은 있음. US17 / TSE8035 / KRX042700 각각 exact quote·무료·실시간 entitlement는 미확인 [KI2] | 계좌 Appkey/App secret으로 access token 발급; 같은 Open API 체계에 국내/해외 주문과 잔고 기능이 존재. 공식 order API 문서도 appkey/appsecret 사용을 명시 [KI1, KI2, KI3]. **주문 가능한 계좌 credential이므로 hard gate 탈락**. 별도 market-data-only scope는 미확인; CORS·개인 display·해외 이용 조건도 미확인 | **NOT_ELIGIBLE**; 키를 기기에만 두더라도 제외 |

### 지역·국외 사용 조건

| 제공자 | 공식 확인 / 남은 미확인 |
| --- | --- |
| Twelve Data | 수출통제법 및 금지 국가·단체로의 platform/data 이전 금지 조항이 있다 [TD5 §13]. 대한민국 개인의 해당 free data 사용·모바일 direct display에 대한 별도 geographic approval는 미확인. 거래소 위치가 이용자 지역 허용을 뜻하지 않음 |
| Alpha Vantage | 개인/상업적 분류 조건은 확인 [AV3 §2]. 대한민국에서의 device-only 접근과 특정 exchange 데이터의 국외 사용 조건은 미확인 |
| Finnhub | non-professional 및 business 사용 제한 확인 [FH3]. 대한민국 이용자의 별도 geographic/cross-border entitlement는 미확인 |
| EODHD | own personal/non-professional 정의는 확인 [EH3]. 대한민국 이용·해외 데이터 국외 사용 조건은 미확인 |
| KIS | 계좌 연결 인증 체계 확인 [KI1]. 한국 외 기기 접속·해외 거래소 가격 표시 조건은 미확인; hard gate 탈락을 바꾸지 않음 |

## FX: ECB 일일 reference — keyless 후보, CORS는 미확인

ECB 공식 reference 문서는 EUR base, USD/JPY/KRW 통화와 XML/CSV 다운로드를 안내한다. 보통 TARGET 휴일을 제외한 근무일 16:00 CET경 갱신하며, 정보 목적이고 transaction에 사용하지 말 것을 강하게 권고한다 [FX1]. FX API endpoint나 XML 파일을 호출하지 않았다.

공식 페이지의 공개 다운로드 경로에는 API key 입력 절차가 나타나지 않아 **keyless 공개-download 후보**로만 기록한다 [FX1]. 별도 SDMX API가 있다는 공식 안내는 있으나 API help 원문을 열람하지 못했다 [FX3, FX4]. 인증 불필요 보장의 범위, 모바일 GitHub Pages origin에서 XML/SDMX를 직접 읽을 CORS 허용, rate limit은 **미확인**이다. 공개 XML 링크가 존재한다는 사실만으로 browser fetch를 승인하지 않는다. 따라서 ECB도 정적 direct-device 방식은 **PARTIAL**이다.

ECB 일반 copyright 조건은 정확한 재현·출처 명시, 수정/계산 여부 명시 등을 요구한다 [FX2]. ESCB 통계의 별도 재사용 정책은 상업·비상업 무료 재사용을 허용하되 출처·원본 통계·metadata 보존 조건을 두며 제3자 자료를 제외한다 [FX5]. 일반 수정 고지 조항이 이 통계 정책을 없애는 것으로 해석하지 않는다. 같은 날짜의 원본 **통화 단위/EUR** 자료를 사용하는 기존 교차환산 관계는 `KRW-per-USD = (KRW-per-EUR) ÷ (USD-per-EUR)`, `KRW-per-JPY = (KRW-per-EUR) ÷ (JPY-per-EUR)`다. 이는 [기존 FX 조사](FX_RESEARCH_26E.md)의 관계를 설명한 것이며 새 계산 코드·계산 정책 변경도 ECB 직접 USD/KRW·JPY/KRW 관측값이라는 주장도 아니다. 표시에는 `ECB daily reference / reference date / derived cross-rate / 거래용 환율 아님`을 구별해야 한다. 현재 26E①의 수동 FX를 자동 ECB로 변경하지 않는다.

## US17 API + TSE/KRX 2개 수동 혼합은 가능한가?

**설계상 가능하지만 공식 문서만으로 실행 가능 판정은 못 한다.** 국제 2개 free coverage가 없더라도 US17 API + 8035/042700 수동이라는 별도 사용자 선택은 구성할 수 있다. 조건은 정확한 US17 listing/quote entitlement, market-data-only key, 개인 표시 권한, static origin CORS가 모두 먼저 확인되는 것이다. 특히 Twelve Data는 문서상 Basic US와 Pro Japan/Korea 구분이 뚜렷해 이 혼합 방식의 **후속 조사 우선 후보**이며, 무료 realtime의 실제 source/범위·US17별 권한도 확인해야 한다 [TD1, TD3, TD4, TD6]. EOD도 허용된다면 Alpha Vantage가 다음 조사 후보다 [AV1, AV2]. 이것은 추천 순서이지 채택 결정이 아니다.

하루 1회, symbol당 1-credit/call의 가정에서 US17은 17, 전체19는 19이다. Alpha Vantage는 각각 8/6 calls, EODHD는 3/1 calls만 남는다. 이 산술은 **quota가 quote 제공 또는 CORS를 보장하지 않으며**, FX·symbol lookup·재시도·수동 refresh가 추가 요청이면 예산을 따로 예약해야 한다 [AV1, AV2, EH1, TD2]. 무료 다회 polling을 제안하지 않는다.

향후 혼합 모드에서도 source/manual/API, 원통화, price-as-of, timezone, realtime/delayed/EOD, FX-reference-date, stale/error를 종목별로 표시해야 한다. 실패 시 0 가격이나 다른 상장으로 대체하지 않고 마지막 유효값의 stale 표시 또는 수동 상태를 유지하는 **설계 제안**이다. 보유수량·평균단가·계좌번호는 provider 요청에 포함시키지 않는다.

## 다음 선택 전 닫아야 하는 gate — 이 PR에서는 실행하지 않음

1. Provider 공식 문서 또는 공개 공식 지원 답변으로 static GitHub Pages origin / 모바일 browser / 해당 quote endpoint / key 전달 방식의 CORS·client-side key 이용 허용을 확인한다. 확인 전 feasibility는 UNKNOWN.
2. Credential 자체가 거래·계좌 접근 불가인 market-data-only인지 확인한다. 조회 코드만 제한하는 것은 불충분. KIS 계좌 key를 입력받지 않는다.
3. 위 19개 중 자동화할 정확한 symbol·거래소·share class·통화의 **price endpoint 무료 entitlement**를 확인한다. catalog 조회는 증거로 쓰지 않는다.
4. 본인 비공개 개인 표시, professional 조건, 지역 조건을 확인한다. 특히 EODHD `displaying` 문구와 Finnhub Free pricing 본문은 unresolved.
5. 사용자가 realtime/delayed/EOD, US17+2manual 여부와 책임을 선택한다. 어떤 선택도 이 docs-only PR에서 API 구현·key 발급·실제 호출 승인이 되지 않는다.

## 공식 출처 목록과 검증 범위

아래 열람일은 모두 **2026-10-09**이며, 위 주장은 해당 번호의 URL/구간에 연결된다. 공식 site의 공개 문서·공식 운영 repository만 근거로 사용했다. 제3자 API directory, blog, 사용자 issue의 성공/실패 관찰은 근거로 사용하지 않았다.

| ID | 공식 URL | 열람일 | 근거 구간 / 상태 |
| --- | --- | --- | --- |
| TD1 | https://support.twelvedata.com/en/articles/5335783-trial | 2026-10-09 | Basic Plan (Free), plans; 본문 확인 |
| TD2 | https://support.twelvedata.com/en/articles/5615854-credits | 2026-10-09 | API weights, daily reset; 본문 확인 |
| TD3 | https://twelvedata.com/exchanges | 2026-10-09 | Min. individual plan: US Basic, XJPX/XKRX Pro; 본문 확인; catalog는 개별 가격 coverage 근거 아님 |
| TD4 | https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage | 2026-10-09 | Individual plans / Metadata Visibility and Subscription Access; 본문 확인 |
| TD5 | https://twelvedata.com/terms | 2026-10-09 | Terms of Use, §13 export; 본문 확인 |
| TD6 | https://twelvedata.com/docs | 2026-10-09 | 공식 검색 결과 확인, open은 content-length failure; 전체 본문 검증 미완료, CORS/read-only 미확인 |
| AV1 | https://www.alphavantage.co/support/ | 2026-10-09 | Usage/frequency limits 25/day; 본문 확인 |
| AV2 | https://www.alphavantage.co/documentation/#latestprice | 2026-10-09 | Quote Endpoint / entitlement / default EOD, 본문은 https://www.alphavantage.co/documentation/ 에서 확인 |
| AV3 | https://www.alphavantage.co/terms_of_service/ | 2026-10-09 | PDF §2 personal/mobile display 및 commercial criteria; 본문 확인 |
| FH1 | https://finnhub.io/pricing | 2026-10-09 | 공식 검색 snippet 60 API calls 표기; 본문 extraction 0 lines, Free/daily/entitlement 검증 미완료 |
| FH2 | https://finnhub.io/docs/api/quote | 2026-10-09 | 공식 검색 snippet US real-time quote; 본문 extraction 0 lines; exact symbols/CORS 미확인 |
| FH3 | https://finnhub.io/terms-of-service | 2026-10-09 | Redistribution Rights and Personal Use / API Limit and Access; 본문 확인 |
| FH4 | https://finnhub.io/docs/api/websocket-trades | 2026-10-09 | 공식 검색 결과 token / X-Finnhub-Token 인증 안내; read-only·browser CORS 미확인 |
| EH1 | https://eodhd.com/pricing | 2026-10-09 | Sandbox / Developer Access & Usage / Market Prices & Reference; 본문 확인 |
| EH2 | https://eodhd.com/financial-apis/api-limits | 2026-10-09 | Daily/Minute limits, call cost; 본문 확인; free minute 값은 EH1과 차이 기록 |
| EH3 | https://eodhd.com/financial-apis/terms-conditions | 2026-10-09 | Personal and Commercial Use of Information, Access; 본문 확인 |
| EH4 | https://eodhd.com/financial-apis/quick-start-with-our-financial-data-apis | 2026-10-09 | 공식 검색 결과 personal token 인증 안내; CORS/read-only 미확인 |
| KI1 | https://apiportal.koreainvestment.com/intro | 2026-10-09 | 계좌 Appkey/App secret REST 인증; 본문 확인 |
| KI2 | https://github.com/koreainvestment/open-trading-api | 2026-10-09 | 공식 repository §2.2 domestic_stock / overseas_stock 시세·주문·잔고; 본문 확인 |
| KI3 | https://apiportal.koreainvestment.com/apiservice-apiservice%3F/uapi/domestic-stock/v1/trading/order-cash | 2026-10-09 | 공식 검색 결과 order-cash의 appkey/appsecret 요구; 공개 공식 order sample https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/order_cash/order_cash.py 도 확인 |
| KI4 | https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000001 | 2026-10-09 | 유량/신규고객 제한 공지 제목; 상세 quota 본문 미확인 |
| FX1 | https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html | 2026-10-09 | Update schedule / informational purpose / EUR base / Downloads; 문서만 확인, linked XML/CSV 호출 없음 |
| FX2 | https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html | 2026-10-09 | Copyright 조건 1–4 / disclaimer; 본문 확인 |
| FX3 | https://www.ecb.europa.eu/stats/accessing-our-data/html/index.en.html | 2026-10-09 | Data API SDMX 2.1 소개; 본문 확인 |
| FX4 | https://data.ecb.europa.eu/help/api/overview 및 https://data.ecb.europa.eu/help/api/data | 2026-10-09 | open 실패; 인증/CORS/quota 검증 미완료. 실제 data endpoint 호출 없음 |
| FX5 | https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html | 2026-10-09 | ESCB 통계 별도 무료 재사용·출처·원본/metadata 보존·제3자 제외 조건; 본문 확인 |

재조사 없이 이 문서를 미래의 가격·약관·entitlement 보증으로 사용하지 않는다. **현재 선택은 26E① 유지, API는 OPTIONAL future research만, 최종 채택은 사용자 결정**이다.
