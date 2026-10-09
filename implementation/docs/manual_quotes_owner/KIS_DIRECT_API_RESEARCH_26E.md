# KIS Developers direct-API official research — decision 26E

As of 2026-10-09 UTC. **Service remains undecided, OFF / 26EWAIT.** This report establishes documented capabilities and limitations only; it does not establish that the requester owns an eligible account or that any TARGET19 instrument returns usable data.

Public documentation and official `koreainvestment/open-trading-api` samples were fetched through the inherited proxy with TLS verification. Network policy was read; environment/credential readiness, secret files and process environment were not inspected. No keys/tokens, authentication issuance, account linking, holdings, trading, paid subscriptions, live quotes or FX observations were obtained. No repository file was edited or committed. Two production endpoint probes had no keys, no token, no symbol, no query; response bodies were not read.

## What is supported by official evidence

| Requirement | Official evidence | Exact limitation |
|---|---|---|
| Domestic KRX quotes | `GET /uapi/domestic-stock/v1/quotations/inquire-price`, TR `FHKST01010100`; market selector `J:KRX` and input instrument code | General market capability; KRX042700 not queried or individually verified |
| US Nasdaq/New York/Amex quotes | `GET /uapi/overseas-price/v1/quotations/price`, TR `HHDFS00000300`; EXCD explicitly `NAS`, `NYS`, `AMS` | General exchange-query codes; no promise of full consolidated US feed or exact-symbol completeness |
| Tokyo quotes | The same overseas current-price schema explicitly enumerates `TSE:도쿄`; price-detail schema and official GitHub sample also list TSE | Tokyo support is documented. TSE8035/Tokyo Electron instrument access remains unverified |
| Overseas quote details | `/uapi/overseas-price/v1/quotations/price-detail`, TR `HHDFS76200200`; currency, decimal positions and trading units in schema | Documentation marks price-detail as live-account only; field presence is not an observed response |
| Domestic plus overseas holdings later | Separate domestic `inquire-balance`, overseas `inquire-balance`, and overseas `inquire-present-balance` official samples | Overseas stock service application required; requester account and access remain unknown; no integration performed |
| Generic FX charts | `/uapi/overseas-price/v1/quotations/inquire-daily-chartprice` has `FID_COND_MRKT_DIV_CODE=X` for FX | No required USDKRW/JPYKRW identifiers, reciprocal direction or JPY unit normalization established |

The same KIS API suite and account-configured official samples cover domestic and overseas stocks. That supports KIS as a credible one-broker candidate. It does not verify that one particular existing account has the necessary overseas enrollment and entitlements, nor all 19 target instruments.

**TARGET19 individual proof: UNKNOWN for all 19.** US17: ASML, LRCX, KLAC, NVDA, AMD, AVGO, QCOM, INTC, MSFT, GOOGL, AMZN, RTX, SYK, ETN, HUBB, GEV, ROK. Japan: requested TSE8035 Tokyo Electron. Korea: requested KRX042700 Hanmi. These identities came from the task and were not independently mapped to KIS instruments. Official master-download code maps `nas/nys/ams/tse` to their markets, but its archives contain base-price fields, so they were not downloaded under the no-quote constraint. The sample reader also disables TLS verification; it was read only and never run.

## Free service, delays and eligibility

The official basic-fee FAQ states: “현재 기본서비스로 제공되는 유량(현재 초당 10건)은 0원으로 제공됩니다.” It says no plan to charge the basic allocation. The FAQ was created 2022-03-15, and service terms article11 permits a posted fee schedule; this is evidence of a free basic offering, not an irrevocable free guarantee. Its historical 10 requests/second text is not treated as the current limit.

The overseas price and price-detail API summaries state that OpenAPI offers free overseas data only; paid real-time market data cannot be received through OpenAPI even if a customer purchases it elsewhere. **Japan is 15 minutes delayed. US is zero-minute free Nasdaq TotalView data from the Nasdaq market center.** The documentation describes the free US service as containing about 50% of the information of paid services and warns of differences in current price, order book, momentary volume, charts and OHLC. The zero-minute policy is stated generally for the United States while the endpoint accepts NAS/NYS/AMS; it does not independently prove complete data for every symbol or venue, and does not establish SIP equivalence.

A KIS account, ID/account linking, OpenAPI application, App Key/App Secret issuance, and identity/account verification are required. Terms reject under-19 applicants. A 2026-03-26 FAQ lists 위탁01, 연금저축22, ISA01, 국내선물옵션03, 해외선물옵션08 and RIA01 as eligible for orders/account/quote inquiries. IRP29 permits account and quotes but no orders. DC55 is unavailable. These are general account-category rules, not permission proof for every market or security. The brokerage service application URL redirects to login; no login or application was attempted.

Personal users may use data for their own investing and a webpage for their own viewing/analysis. The official 2025-08-11 webpage FAQ says: “시세 데이터를 활용한 비즈니스 서비스 제공 또는 외부 서비스(앱) 배포는 불가능합니다.” Business services or external app distribution with KIS data require a direct information agreement with the relevant exchange/provider. Corporate use/display also requires separate agreements. A future user-only relay would need to remain within authorized private use; public redistribution is not covered by the free personal-use evidence.

## Token flow and browser architecture

Official docs and samples use `POST /oauth2/tokenP` with JSON `grant_type=client_credentials`, `appkey`, and `appsecret`. Personal account access tokens last24hours; a repeat issuance within6hours returns the prior token. REST price requests require `Authorization: Bearer …`, `appkey`, `appsecret`, and `tr_id`. `AUTH=""` in overseas query parameters is not an authentication exemption. The quote and token schemas explicitly warn that appkey/appsecret must never be exposed: “절대 노출되지 않도록 주의해주세요.” No token request was made.

| Architecture option | Assessment for this decision |
|---|---|
| Current browser with holdings and keys device-local | KIS needs an App Secret in token and quote calls. A webpage runtime and its loaded code can access a browser-stored secret, so device-local storage alone does not establish non-exposure. Direct browser use is not currently approved or implemented |
| Future user-owned, user-only free relay | Conditional option: secret and tokens could be stored in the user's private relay secret storage; the browser could call only explicitly allowed read endpoints. This moves secrets off-device, changes the current storage boundary and needs a later user decision. A free hosting allowance, actual security/CORS behavior and terms compatibility remain unverified. No relay or account integration was built |

Header-only CORS evidence, observed 2026-10-09T01:28:23Z through the inherited proxy: unauthenticated no-symbol GET to the overseas-price endpoint returned HTTP500 and `Access-Control-Allow-Origin: *`. A preflight OPTIONS for GET with authorization/appkey/appsecret/tr_id/content-type returned HTTP501 and no allow-methods/allow-headers in the inspected headers. No body was read. These are error responses, not proof that an authenticated browser fetch or token request works. No official CORS support statement was found. The explicit secret non-exposure requirement stands independently of CORS.

## FX and future holdings limits

Price-detail schema contains `curr` (currency), `t_rate` (day FX) and `p_rate` (prior-day FX), but its explanatory descriptions do not define the currency pair, reciprocal direction or denominator. Execution-based overseas balance schema contains `bass_exrt` for KRW valuation and `frst_bltn_exrt` for initially posted FX; documentation says foreign-currency valuation uses the day's initial posted rate and differs from actual conversion. These account valuation fields do not establish a suitable current quote-only FX feed.

**USD/KRW support as a precise endpoint/pair: unverified. JPY/KRW support as a precise endpoint/pair: unverified. KRW per1JPY versus per100JPY: unverified.** No values were fetched and no unit conversion is assumed. Do not silently divide yen rates by100 or treat a balance valuation rate as current FX.

For future holdings research, overseas balance accepts Japan `OVRS_EXCG_CD=TKSE` with `TR_CRCY_CD=JPY`; US codes include NASD/NAS/NYSE/AMEX and USD. These holdings exchange codes differ from quote `TSE/NAS/NYS/AMS`. Overseas balance allows pagination after100 entries, requires overseas service enrollment, excludes MiniStock holdings, and warns that some valuation fields differ from HTS during US daytime. Execution-based balance has settlement/timing caveats and limited paper output. This establishes future read-query capability only; current holdings remain device-local and unchanged.

## Key official sources

Every fetched source, exact URL, UTC timestamp, HTTP status and short relevant excerpt/paraphrase is recorded in `KIS_DIRECT_API_SOURCES_26E.json` beside this report. Public docs HTTP200 are documentation metadata, not broker data responses.

- [Official KIS Developers](https://apiportal.koreainvestment.com/)
- [Overseas current-price guide](https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/overseas-price/v1/quotations/price)
- [Current-price public documentation JSON](https://apiportal.koreainvestment.com/api/apis/public/detail?accessUrl=%2Fuapi%2Foverseas-price%2Fv1%2Fquotations%2Fprice)
- [Current-price property schema](https://apiportal.koreainvestment.com/api/apis/guide/property/3eeac674-072d-4674-a5a7-f0ed01194a81)
- [Domestic KRX price guide](https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/domestic-stock/v1/quotations/inquire-price)
- [Token guide](https://apiportal.koreainvestment.com/apiservice-apiservice?/oauth2/tokenP)
- [Official basic-fee FAQ](https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000002/post/beb2459a-f6b4-432e-928a-d3462dd0daef)
- [Official eligible-account FAQ](https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000002/post/0b29069f-812b-4a70-94db-63d07d5ad54c)
- [Official own-view/external-distribution FAQ](https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000002/post/01a0b635-3630-4aee-8970-42f83828118c)
- [Public service terms](https://apiportal.koreainvestment.com/api/terms/public?termsType=MARKET)
- [Official GitHub README](https://github.com/koreainvestment/open-trading-api)
- [Official overseas quote sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/price/price.py)
- [Official overseas price-detail sample including TSE](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/price_detail/price_detail.py)
- [Official overseas balance sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/inquire_balance/inquire_balance.py)
- [Official master reader; read only](https://github.com/koreainvestment/open-trading-api/blob/main/stocks_info/overseas_stock_code.py)

**Decision consequence:** KIS has stronger documented Japan plus US plus KRX market capability than a genericUS-only quote candidate. Exact TARGET19 access, exact FX pairs/units, requester account eligibility and a compatible private secret-storage architecture remain unresolved. Preserve undecided/OFF/26EWAIT.
