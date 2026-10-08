# Market basis and immutable raw-anomaly audit v0.3

Status: READ_ONLY_EVIDENCE_AUDIT / ACTION_SOURCE_CANDIDATES_EXPANDED / PRODUCTION_NOT_READY.

Chart baseline is PR41 `54ee25446ccf6cfa32ddf164a8ed31b7e1036b9a`. Audit baseline `8668c69070c7956cb85d1ccf8cbeb8d9d2daf5cf`, P0 v0.1, P0 prerequisite v0.2 and Core81 / Extended24 / Research Candidate8 remain unchanged. No production contract, protected Web path, package Python, Frozen policy, owner branch or publication authority was changed.

## Evidence retained and narrowed

All nineteen original scoped five-year daily response hashes were independently recomputed and matched. The original **23,155 rows / one all-null OHLCV row / four exact OHLC envelope contradictions** are unchanged. New acquisition used the existing `tools/fetch_real_data.py._get` unchanged, no credentials/payment, one attempt per symbol and a maximum of three concurrent requests. Nineteen *separate* immutable daily responses explicitly requested `events=div,splits`; all nineteen returned HTTP200.

The new responses contain **283 provider dividend candidates and nine provider split candidates**. These are provider assertions currently observed, not a certified corporate-action ledger. No announcement timestamp, historical price/action `available_at`, event completeness, issuer/security interval continuity or full OHLCV adjustment lineage was established by obtaining those responses. AMD returned no event map; that is an observed empty response under the requested range, not proof of no corporate actions.

Original raw bytes are retained in `p0-prerequisites/market`. New capture bytes and their SHA256, request URL, acquisition clock interval and persistence clock are in `ACTION_ACQUISITION_PROBES_v0.3.json`. The original responses did not request actions; their missing events are NOT_REQUESTED, not a no-action assertion.

## Source-value readiness for all nineteen labels

The labels below are **provider symbols**, not newly certified internal security identities. Production admission remains BLOCKED for every row pending the separate identity/session/availability/basis bindings. READY below means only that the corresponding original source arrays are present, complete and structurally valid for the requested response. PARTIAL includes the preserved anomaly. These states must not be reported as product readiness.

| Provider symbol | Original rows | OHLCV structural facts | Non-null adjclose | Dividend / split candidates | Full unadjusted OHLCV | Full split+dividend adjusted OHLCV | Exact historical available_at | Feed quote state |
|---|---:|---|---:|---:|---|---|---|---|
| NVDA | 1255 | READY | 1255 | 20 / 1 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| MSFT | 1255 | READY | 1255 | 20 / 0 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| 8035.T | 1222 | PARTIAL | 1222 | 10 / 2 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| 042700.KS | 1221 | PARTIAL | 1220 | 5 / 1 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| ASML | 1255 | READY | 1255 | 19 / 0 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| LRCX | 1255 | READY | 1255 | 20 / 1 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| KLAC | 1255 | READY | 1255 | 20 / 1 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| AMD | 1255 | READY | 1255 | 0 / 0 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| AVGO | 1255 | READY | 1255 | 20 / 1 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| QCOM | 1255 | READY | 1255 | 20 / 0 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| INTC | 1255 | READY | 1255 | 12 / 0 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| GOOGL | 1255 | READY | 1255 | 10 / 1 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| AMZN | 1255 | READY | 1255 | 0 / 1 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| RTX | 1255 | READY | 1255 | 20 / 0 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| SYK | 1255 | READY | 1255 | 20 / 0 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| ETN | 1255 | READY | 1255 | 20 / 0 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| HUBB | 1255 | READY | 1255 | 20 / 0 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| GEV | 632 | READY | 632 | 7 / 0 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |
| ROK | 1255 | READY | 1255 | 20 / 0 | NOT_AVAILABLE | BLOCKED | NOT_AVAILABLE | UNKNOWN |

A raw byte capture means **original source bytes**; it does not mean unadjusted traded prices. A finite source `adjclose` is a source scalar field, not adjusted open/high/low/volume. The original Hanmi source close and adjclose each have one null; `SOURCE_FIELD_COMPLETENESS_AND_DIFFERENCE_AMPLITUDE_v0.3.json` supplies per-field READY/PARTIAL completeness so field existence is not confused with all-row coverage. Thirteen zero-volume Hanmi rows remain distinct from the all-null row.

All nineteen original metadata objects lack explicit `marketState`, `exchangeDataDelayedBy` and `quoteType` state evidence. A latest `regularMarketTime`, current-session hint or elapsed close cannot certify LIVE/DELAYED/CLOSE, official close or bar finality. Quote state stays UNKNOWN; `price feed state != Investment-System Official/LIVE state`.

## Immutable anomaly detail

`IMMUTABLE_RAW_ANOMALIES_v0.3.json` preserves certified-security identity as null/UNBOUND, provider company-name hint, exact source path/full SHA256, row index, original numeric tokens, timestamp/field JSON pointers, deterministic outcome, affected fields, latest comparison hash and downstream candidates for every anomaly.

| Provider symbol | Original index | Exact raw UTC timestamp | Original O / H / L / C / V tokens | Deterministic result |
|---|---:|---|---|---|
| 8035.T | 149 | 2022-05-17T00:00:00+00:00 | 3821.333251953125 / 3866.666748046875 / 3770.666748046875 / 3869.333251953125 / 11776500 | CLOSE_GT_HIGH |
| 042700.KS | 560 | 2024-01-15T00:00:00+00:00 | 57200.0 / 57700.0 / 56600.0 / 56200.0 / 58752 | CLOSE_LT_LOW |
| 042700.KS | 740 | 2024-10-14T00:00:00+00:00 | 110200.0 / 116000.0 / 110200.0 / 109500.0 / 916860 | CLOSE_LT_LOW |
| 042700.KS | 859 | 2025-04-09T00:00:00+00:00 | 59600.0 / 60700.0 / 58200.0 / 61200.0 / 973664 | CLOSE_GT_HIGH |
| 042700.KS | 970 | 2025-09-19T00:00:00+00:00 | null / null / null / null / null | SOURCE_NULL_OHLCV |

All five affected rows are identical in both observed OHLCV responses. No returned daily action has the same provider date as an anomaly, but that observation does **not** rule out basis issues or establish a cause. Explanation remains **UNKNOWN**. No source correction, row deletion, gap-fill, fabricated OHLC value, volume-zero fallback, epsilon or tolerance was applied.

Candidate downstream handling (proposal, not adopted production policy):

- Invalid OHLC row: block that candle and any calculation that requires a consistent full bar. Keep all original facts and an explicit validation failure. Do not silently expand high/low or substitute adjclose.
- All-null row: preserve the timestamp and mark all source fields NOT_AVAILABLE. A source-null bar is neither a zero-price/zero-volume session nor proof that the market was closed.
- Diagnostic display: original values may be annotated as failed/unavailable evidence. A future degraded series would need explicit hole/reason metadata; silent omission is prohibited. Until the owner admits that mode, block the production series.
- Derived indicators: block dependent windows until the calculation owner specifies and verifies its missing/invalid-input contract. No renderer decides its own repair or classification rules.

## Separate action date roles and actual source candidates

`CURRENT_ACTION_EVENT_CANDIDATES_v0.3.json` retains all returned event values/keys/inner dates with raw-hash and exact JSON pointer. All daily outer keys match their inner dates in this capture; the earlier monthly NVDA capture has an outer key of 2024-06-01 and inner date 2024-06-10. Neither key is treated as announcement/availability time.

| Subject hint | Evidence | Distinct roles that cannot be aliased |
|---|---|---|
| NVDA | Existing issuer original `ca_unit_sources/NVDA.html`, SHA256 `de513cf9e2db874690e45fa023adbb21520b714e57757433f5660158cce9b6a5`, verified against existing CA-UNIT document | Document date 2024-05-22 versus provider/first adjusted-trading date 2024-06-10. Existing CA-UNIT policy is preserved and not generalized to full candles. |
| LRCX | Issuer announcement retrieved as text; original-byte capture failed egress403 | Expected legal effect after 2024-10-02 close versus expected adjusted trading at 2024-10-03 open; announcement date 2024-05-21. |
| KLAC | Issuer-hosted 8-K retrieved as text; original-byte capture failed egress403 | Announcement/report 2026-05-07, record 2026-06-04, expected legal effect after 2026-06-11 close, expected adjusted trading 2026-06-12. |
| AVGO | Issuer announcement retrieved as text; original-byte capture failed egress403 | Record 2024-07-11, expected distribution after 2024-07-12 close, expected adjusted trading 2024-07-15. |
| 8035.T | Issuer presentation/search-extract candidate | Provider dates 2023-03-30 and 2026-09-29 are separate from issuer record dates 2023-03-31 / 2026-09-30 and legal effective dates 2023-04-01 / 2026-10-01. The adjustment/trading-date mapping remains unverified. |

All URLs, retrieval roles and availability limitations are in `BASIS_ACTION_PRIMARY_SOURCE_REVIEW_v0.3.json`. Issuer webpages and presentation extracts are source candidates, not an admitted dated action vintage. Human-readable source dates are not invented exact historical `available_at` timestamps. Other returned split/dividend candidates are not independently certified issuer events in this scope. GEV when-issued/regular-way identity evidence is owned by the identity/time audit and cross-referenced there; no common-series splice is inferred here.

## Provider/transform reuse and remaining basis gap

- Existing Yahoo `parse_bars` selects `adjclose` for scalar price when present, drops close-null rows and does not preserve full OHLCV. That path is unchanged and cannot serve as a production full-candle preservation proof or historical availability proof.
- Existing OHLCV experimental extractor preserves source arrays, but does not create a certified action basis, listing continuity or finality.
- Existing raw-store authority is `source_kind` and original hash, not the `yahoo_chart` filename. Prior evidence still has58 Tiingo-close-only conversions under Yahoo chart IDs. The Tiingo transformation discards O/H/L/V and builds21:00UTC timestamps; no missing fields are reconstructed from it.
- Official Tiingo EOD documentation describes original/adjusted OHLCV plus ex-date cash dividends and splitFactor and a split/dividend methodology. Access needs a token and no account/entitlement was used. Most-US evening publication/correction guidance does not produce exact per-row available_at. Restored original Tiingo EOD bytes, entitlement, transform scope and dated availability would still need audit.
- Official Yahoo help search metadata describes split/dividend adjusted close. Its full page was rate limited. It does not certify these chart endpoint O/H/L/V adjustment semantics, source precision or transformation version.

## Cross-request source-value differences are not economic-revision proof

The original request and later actions request have different query parameters and retrieval times. All **23,155 timestamps and OHLCV values match exactly**, but **10,862 adjclose values differ exactly**. Most examples are small finite-precision-sized differences: NVDA old19.64547348022461 versus new19.645471572875977. The largest symbol-level absolute differences are in `SOURCE_FIELD_COMPLETENESS_AND_DIFFERENCE_AMPLITUDE_v0.3.json`; Hanmi's largest is0.0078125KRW and Tokyo's0.0009765625JPY. The cause is UNKNOWN. This is not a claim of10,862 economically material revisions, incorrect prices or historically known vintages.

Preserve both source snapshots, query parameters and hashes. Never normalize these differences away to force API/MCP/old/new independently acquired sources to share a hash. One exact verified document served through API/Web/MCP must preserve its own values/hash; separate acquisitions may legitimately differ. No numeric tolerance or automatic reclassification was adopted.

## ChartDocument v0.2 implications (proposal only)

Keep the prior seven candidate directions. This evidence requires per-field basis and epistemic status, exact raw index/hash binding, action request/coverage and event-date roles, explicit per-row validation/absence, and source/transform snapshot version. Current-response acquisition clocks remain separate from source event timestamps and unavailable historical knowledge. Security scope remains unresolved until the identity owner binds the series.

The candidate contract should preserve source strings/numeric tokens without inventing Decimal precision. Portfolio Decimal semantics remain its owner contract; a source JSON float is not retroactively promoted to an exact financial Decimal merely because this audit compares original tokens without rounding.

## Dependency boundary

| Future item | Protected change now | P01 | TrackC package code_hash | Integration/FPIA |
|---|---|---|---|---|
| These new immutable captures, anomaly records and outside-package audit helpers | None | None | None | No production admission; scoped replay only |
| Source/action candidate register and missing-source feasibility reads | None | None | None | Domain source owner admission remains separate |
| Domain/package candle-basis adapter or producer parser changes | Forbidden in this stage | Exact path assessment required | Affects broad package hash | Owner review + exact merge-result FPIA before implementation/admission |
| Protected Web assembler/validator and diagnostic rendering semantics | Forbidden in this stage | Affects protected digest | Exact tree assessment required | Separate owner boundary + exact merge-result checks |

## Verification and limitation

This scope independently verified original19 hashes, new19 hashes, complete aligned raw arrays, exact5 original anomaly records, new292 provider action candidates and exact cross-request field comparisons. It did not run production tests, Actions, grant issuance, FPIA, Holdout or canonical merge. All production-readiness blockers remain distinct from successful source acquisition.

One primary-source capture helper was automatically rejected because its fixed-path write_bytes could overwrite evidence. All six attempted primary captures had recorded network failures and no primary HTML bytes were written. The helper was changed to exclusive-create (`xb`) without retrying those network requests; the failure records remain immutable. Source text already obtained by public web retrieval is labelled as text/search evidence rather than original raw bytes. There is no permission request or unfinished authorized mutation in this scope.
