# Official foreign exchange sources for KRW USD and JPY

## 현재 사용자 선택 (2026-10-09)

**26E 결정 = ① 시세·환율 수동 입력 + KRW 기준 표시 (사용자 선택, 2026-10-09).**
수동 입력 범위만 READY이며 자동 수집·공개 JSON(②)·실시간 API(③)는 미채택이다.
아래 조사는 선택 전 자료로 보존한다. 아래의 USD 대안은 현재 선택이 아니며,
과거 메타데이터 요청 영수증은 이번 문서 전용 PR의 새 관측값 호출이 아니다.
[결정 영수증·SSoT §8/§26D 영향](DEPLOYMENT_DECISION_26E.md),
[기기 직접 API의 미채택 후속 조사](DEVICE_DIRECT_QUOTES_RESEARCH.md).
이번 작업은 환율·계산식·입력값·앱 코드·데이터를 변경하지 않는다.

Official sources and documentation were fetched on 2026-10-09. ECB reference rates are a strong public daily FX candidate; Bank of Korea ECOS offers direct won-based series with an issued API key. A manual, device-local FX option could support KRW and USD valuation after separate selection and implementation while preserving an explicit N/A result whenever a required conversion rate is missing. This research changes no application or repository source.

## Confirmed ECB facts

- Publication is usually around 16:00 CET on working days excluding TARGET closing days. The rates are for information purposes; transaction use is strongly discouraged. The current framework, dated 23 June 2026, confirms the timing and covers USD, JPY and KRW. [Exchange rates](https://www.ecb.europa.eu/stats/exchange_rates/html/index.en.html), [Current framework](https://www.ecb.europa.eu/stats/pdf/exchange/Frameworkfortheeuroforeignexchangereferencerates.en.pdf).
- Euro TARGET closing days include weekends, 1 January, Good Friday, Easter Monday, 1 May, 25 December and 26 December. Other ECB office holidays are not necessarily TARGET closing days. [T2 opening hours](https://www.ecb.europa.eu/paym/target/t2/html/index.en.html), [2026 to 2028 holiday calendar](https://www.ecb.europa.eu/ecb/contacts/working-hours/html/index.en.html).
- The ECB publishes currency units per euro. Its public reference page includes USD, JPY and KRW. Same-date EUR legs therefore permit an application calculation of KRW per USD as `rKRW / rUSD`, KRW per JPY as `rKRW / rJPY`, and USD per JPY as `rUSD / rJPY`, where `rCurrency` means currency units per EUR. These are calculated cross rates, not separately published ECB pair observations. [Reference rate page](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html).
- Public ESCB statistics may be reused free of charge for commercial or noncommercial use, with source attribution and without modifying the statistics or metadata. Third-party data is excluded from this permission; continuity and absence of revisions are not guaranteed. Preserve original inputs and metadata. [ESCB reuse policy](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html).
- The general ECB copyright policy requires accurate reproduction and source citation, explicit disclosure of modifications, and disclosure that ECB information is freely available when incorporated in sold documents. Label application calculations clearly, for example, `Calculated from ECB reference rates`. The general policy's modification clause should not be represented as removal of the specific ESCB condition above. [Disclaimer and copyright](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html).

## ECB API access evidence and limits

The official SDMX documentation defines daily reference series keys such as `D.USD.EUR.SP00.A`, documents the OR operator, and supplies direct HTTPS request examples with no key or authorization parameter. `detail=serieskeysonly` explicitly excludes observations and attributes. [API data syntax](https://data.ecb.europa.eu/help/api/data), [API examples](https://data.ecb.europa.eu/help/api/data-examples).

A metadata-only GET on 2026-10-09 used `https://data-api.ecb.europa.eu/service/data/EXR/D.USD+JPY+KRW.EUR.SP00.A?detail=serieskeysonly&format=csvdata`. It returned HTTP 200 without a key or authorization header. The 171-byte CSV contained a header and three series identifiers, with columns `KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX` and no observations. With a supplied Origin header, the response had `Access-Control-Allow-Origin: *`. This confirms unauthenticated access and CORS headers for that metadata request; observation fetching, a production browser flow, uptime and future header behavior remain untested. [Metadata-only receipt](evidence/ecb-fx-metadata-receipt-2026-10-09.json).

Prefer the ECB reference dataset EXR for this option. The portal converter also includes Bloomberg FX data, which does not inherit the ESCB third-party reuse permission. [Converter explanation](https://data.ecb.europa.eu/currency-converter).

## Confirmed Bank of Korea ECOS facts

| Question | Official documentation finding |
| --- | --- |
| API key | ECOS terms Article 4 requires applying for an issued key. It has a two-year term and can be renewed in two-year increments. [Key application](https://ecos.bok.or.kr/api/#/AuthKeyApply). |
| USD rate | Table `731Y001`, daily frequency `D`, item `0000001`: Won per United States Dollar, basic exchange rate. Unit is KRW per USD. [Statistical code search](https://ecos.bok.or.kr/api/#/DevGuide/StatisticalCodeSearch). |
| JPY rate | Same table and frequency, item `0000002`: Won per Japanese Yen, 100 yen. Unit is KRW per 100 JPY; divide the series by 100 for KRW per JPY. [Statistical code search](https://ecos.bok.or.kr/api/#/DevGuide/StatisticalCodeSearch). |
| Redistribution | Terms Article 5 permits commercial use, except restricted statistics require originating agency approval. Article 7 requires identifying the information as provided by ECOS and also refers users to the ECOS statistical information usage guidelines. Terms are effective 2020-11-05. [ECOS API terms in the footer](https://ecos.bok.or.kr/api/). |
| CORS and schedule | Browser CORS support and a precise daily publication time were not established by the reviewed official documentation. No observation endpoint was requested. |

The terms and code-search results were retrieved through the ECOS site's own public documentation service, not its observation service. [Terms evidence](evidence/bok-ecos-openapi-terms-2026-10-09.txt), [Series code evidence](evidence/bok-ecos-fx-code-documentation-2026-10-09.json).

## Manual FX recommendations

Use KRW as the default reporting currency for Korean spending and planning, with USD as an alternative for US asset comparison. Always retain each instrument's native quote currency. Store manual FX rates locally with an explicit direction, unit, effective date and user-entered source label; normalize JPY rates to one yen. Manual entry avoids upstream credentials and allows a reviewable valuation snapshot.

Use a conversion multiplier of 1 only when the quote and reporting currencies match. Require a finite positive FX rate for every other conversion. A missing or invalid required rate yields N/A for the converted value and affected combined total; never substitute 0 or 1 or sum amounts in different currencies. Keep native values visible. Show the FX effective date separately from the quote date, and identify any prior-working-day rate used on weekends or TARGET holidays. If later automation uses ECB cross rates, require both input legs from the same effective date and label the result as calculated.
