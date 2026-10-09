# FSC stock API research for Investment System1 decision 26E

As of 2026-10-09, the service remains **OFF / 26E WAIT**. The official public dataset confirms free access through an approved personal service key, domestic KRX stock scope, delayed daily publication, and a restrictive license. It does not establish complete 19-ticker coverage or an approved browser data flow. Public TARGET is a 19-ticker catalogue, with no holdings or portfolio information.

## Official access and current endpoint

The [FSC dataset page](https://www.data.go.kr/data/15094808/openapi.do) was retrieved over HTTPS with status 200 on 2026-10-09. Its listed modification date is 2026-09-07. It states “비용부과유무 무료,” automatic approval for development and operation, and development-account traffic of 10,000; the displayed traffic entry does not itself specify the period. Operation traffic can be increased by application after registering a use case.

The current page and [linked official user guide](https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000007632094&fileDetailSn=1) document this stock endpoint:

`https://apis.data.go.kr/1160100/GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2`

The current Swagger advertises HTTPS and HTTP. Use HTTPS. The previously suggested `/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo` path was checked only for keyless response headers and is not proved to be the currently supported approved route. The guide's document property reports modification at 2026-08-26T07:38:00Z.

The guide marks serviceKey authentication and a required serviceKey obtained from the portal. The [official portal API use guide](https://www.data.go.kr/ugs/selectPublicDataUseGuideMetView.do) explains that automatic approval occurs at application, and an authentication key is issued after approval. Free pricing and automatic approval are not evidence that an application has been made or that this user has permission. No application, key creation, login, or account connection occurred.

## Coverage and quote meaning

| Requirement | Official evidence | Decision 26E status |
| --- | --- | --- |
| 042700 Hanmi Semiconductor | Stock operation describes “KRX에 상장된 주식”; response market enumeration is KOSPI/KOSDAQ/KONEX. | Domestic scope is documented. Exact 042700/name/ISIN API-row coverage is **unproved**. Do not promote scope eligibility to an individual coverage claim. |
| 17 US targets | All four documented operations concern KRX-listed securities. | Outside the documented dataset scope; no US rows were requested. |
| TSE 8035 | No Tokyo exchange operation or market enumeration. | Outside the documented dataset scope; no Japanese rows were requested. |
| USD/KRW and JPY/KRW | Operations are stocks, beneficiary certificates, and preemptive-right securities/certificates. | FX pairs are outside this stock dataset. A separate authorized FX source would be required. |

The official response definitions document `clpr` as 종가, “정규시장의 매매시간 종료시까지 형성되는 최종가격” (the final price formed through the regular session's end), `basDt` as reference date, `srtnCd` as a unique six-digit short code, `itmsNm` as name, and `mrktCtg` as market category. This establishes the **close field with high official-source confidence**, not a live quote or a price observation.

The cited page and guide do not explicitly define a currency field or unit for `clpr`. A search of the guide's extracted text for KRW, 원화, 통화, 단위, (원), and currency found no explicit unit declaration. Native KRW is a reasonable domestic-market context inference, but **provider-confirmed KRW units remain unproved** and must not be represented as verified by this evidence.

## Publication delay and license

The page's summary “업데이트 주기” says 실시간, and its introductory description also uses that word. Its explicit caveat states “데이터 갱신주기는 일 1회” and “모든 서비스는 실시간이 아니며,” with updates after 13:00 on the business day after the reference date. Friday data is provided Monday, or the next business day if Monday is a holiday. The current DOCX repeats once-daily loading and non-real-time publication after 13:00 the following business day. Treat it as delayed daily close data; do not use the summary label as evidence of real-time operation. The quoted text does not explicitly name the timezone or promise a service-level deadline.

The current page and guide state KOGL Type 4: attribution, noncommercial use, and no alteration. They additionally state:

> 본 데이터는 상업적 목적 여부와 상관 없이 제3자 무단 제공 및 재배포가 엄격히 금지됩니다.

Unauthorized provision or redistribution to third parties is strictly prohibited regardless of commercial purpose. Commercial use requires purchasing from the original rights holder, KRX, under its stated conditions. Such paid use was not pursued. “Free” therefore does not mean unrestricted reuse or redistribution. A public quote feed cannot be authorized merely because TARGET is a public ticker catalogue. Permission for owner-only relay processing or display transformations is not established by a generic free-access label.

## HTTPS and CORS receipts

All API checks omitted the query string, serviceKey, ticker, reference date, and data parameters. Response bodies were not read. The synthetic Origin was `https://investment-system1.example`. These are server-header receipts, not actual browser execution.

| Current V2 probe | Status | Relevant response headers |
| --- | --- | --- |
| HEAD without Origin | 400 | Vary: Origin,Access-Control-Request-Method,Access-Control-Request-Headers; no ACAO captured |
| HEAD with synthetic Origin | 403 | Vary; no ACAO captured |
| OPTIONS with synthetic Origin and requested GET | 200 | ACAO: https://investment-system1.example; ACAM: GET,OPTIONS; content-length: 0 |
| GET with synthetic Origin, no query/key, headers only | 400 | ACAO: https://investment-system1.example; Vary; application/xml |

The legacy candidate's HEAD with Origin returned 403 without a captured ACAO header. That receipt does not prove successful legacy data access or diagnose its cause.

The positive V2 preflight and keyless GET CORS header are evidence that CORS is **not absent on those particular unauthenticated responses**. HEAD's 403 must not be presented as a GET authorization failure; the preflight advertises GET and OPTIONS. Conversely, echoed ACAO on a preflight or keyless error is not proof of a successful approved GET, target-origin support, permission, or authenticated response policy. A browser CORS error also does not prove an authorized data flow. No authenticated response or response body was inspected.

## Personal service key and owner-only relay comparison

The [portal terms](https://www.data.go.kr/ugs/selectPortalPolicyView.do#use_stplat), Article 7, require members to manage ID/password and related information safely and prohibit giving their information/accounts to others. These general account-security terms are explicit. A serviceKey-specific confidentiality or browser-use prohibition was not found in the cited text; do not invent one.

As a security inference, a key embedded in public frontend source, a static bundle, or a public API URL is visible to recipients. Owner-only runtime entry keeps the key out of the distributed bundle, but the key remains visible in the owner's browser and request URL; it is not a server-held secret. No key was entered or stored.

A future owner-only free relay is an architecture option if direct CORS or the required credential handling is unsuitable. The user's personal approved key would be held in the user's own encrypted secret storage (for example, a user-owned worker secret), with the user's own identity/access gate. The relay would use HTTPS upstream, allow only the required operations, keep the key out of frontend artifacts/responses/logs, and avoid publishing public quote JSON. This is an architectural comparison only: no worker, access service, secret, deployment, account, or paid service was configured.

A relay changes credential location and browser-origin handling. It does not grant market coverage, remove publication delay, bypass approval, permit redistribution or alteration, or prove zero hosting cost. The provider's owner-only processing terms and any hosting free-tier limits remain unresolved. Positive unauthenticated CORS receipts make a relay's necessity undecided, while the key handling and license questions remain separate.

## Decision and evidence boundary

Keep **OFF / 26E WAIT**. Mandatory FSC research is complete, but exact 042700 coverage, price currency units, approved response behavior, actual browser behavior, and owner-only relay permission remain unresolved. The domestic scope cannot cover the 17 US tickers, TSE 8035, or the two FX pairs.

Only official documentation and no-key no-data response headers were requested. No quote or FX observations, demo-key requests, credentials/environment inspection, holdings/portfolio requests, trades, repository edits, commits, account linking, or paid-service actions occurred. Networking used the inherited proxy and normal TLS verification. Exact official source URLs, UTC retrieval times, selected headers, document hashes, and probe receipts are in `FSC_DIRECT_API_SOURCES_26E.json`.
