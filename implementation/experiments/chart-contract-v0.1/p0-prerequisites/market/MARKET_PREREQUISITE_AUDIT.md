# P0 Market production-evidence prerequisite audit

Status: READ_ONLY_PREREQUISITE_AUDIT / CURRENT_SOURCE_ACQUISITION_VERIFIED / PRODUCTION_NOT_READY.

Observed source acquisition: 2026-10-04 20:38:55–20:43:07 KST. Assessment recorded after those acquisitions. This is evidence work, not implementation or a production schema adoption. PR41 P0 v0.1, Core81/Extended24/Research Candidate8 and all previous audit verdicts remain unchanged.

## Pins and method

| Source | Exact pin |
|---|---|
| PR41 checkout | `97685dd` (full SHA in MARKET_EVIDENCE.json) |
| Existing audit baseline | `8668c69070c7956cb85d1ccf8cbeb8d9d2daf5cf` |
| Combined integration trial, noncanonical | `acaf1b5a82859ac2750a130ebe88f8b4d272ac66` |
| Canonical comparison source | `b8e39a2196a6d7794a04a0cd5393c68329e126ca` |

Existing `tools/fetch_real_data.py._get` was used unchanged. Nineteen single-attempt requests used no token, login or payment; the additional fifteen US labels used at most three concurrent requests. Raw responses are preserved byte-for-byte as scoped `probe_*_5y_original.json`, with request URLs, SHA256, byte counts and acquisition records. No raw-store slot, provider, parser, session binder, protected Web file or package production Python was changed. No grant or publication was issued.

`PUBLIC_ACQUISITION_PROBES.json` records the first four responses; `ADDITIONAL_REFERENCE_US_PROBES.json` records the remaining fifteen. `MARKET_REFERENCE_COVERAGE.json` independently checks all nineteen hashes, bytes, ordered unique timestamps, aligned field lengths, nulls, finite values and exact OHLC envelopes. It is an audit result, not a ChartDocument or admitted producer output. All source hashes are available in that file.

## Source readiness

| Capability | Evidence | Readiness |
|---|---|---|
| Current Yahoo daily OHLCV acquisition | 19/19 provider-label requests HTTP200, original bytes preserved | SOURCE_FEASIBILITY_CONFIRMED only |
| Original historical raw-store replay | 6,808 manifests; raw/blobs and raw/history contain no data files in this checkout | NOT_AVAILABLE here; earlier recorded audits are not replayed |
| Security→listing→provider series | Current CIK/ticker maps and identifier labels, global identity classes, dated listing contract | UNBOUND; no complete sourced crosswalk/history for these series |
| US session binding | Existing versioned calendar/listing/binder layer | Contract implemented; fixture tests only; real exchange vintage not replayed |
| JP/KR sessions | Actual provider timezone hints and official source candidates | UNSUPPORTED by existing US binder; dated calendars not supplied |
| Historical per-bar available_at/finality | No exact source availability in chart response | NOT_AVAILABLE |
| Adjusted/unadjusted full OHLCV | Source close+adjclose; corporate-action candidates; historical raw Tiingo manifests | Semantics and complete transformation lineage unverified |
| Feed live/delayed/official-close state | regularMarketTime and currentTradingPeriod only; state/delay fields absent | UNKNOWN |
| Production chart admission/publication | No identity/calendar/PIT/adjustment bindings or grant | NOT_READY / no elevation |

Current acquisition of historical values does not show that the same values or revisions were available at historical decision time. All nineteen evidence records retain `historical_available_at=null`. Acquisition completion bounds our observation now; it never substitutes for historical source publication. The first four completion records include local post-read persistence/summary work, so they are not asserted to be precise HTTP receipt times. Additional records separate acquisition completion and persistence.

## Exact observed symbol/period coverage

These are provider labels, not certified security identities. The seventeen US symbols occur explicitly in `qgv/identifiers.py:OFFICIAL_PORTFOLIO_V11`; Tokyo and Hanmi Yahoo labels were exploratory source checks, not a registry repair. In particular bare `TEL` remains ambiguous and was never queried as Tokyo Electron.

| Provider label | First bar date | Last bar date | Rows | Complete OHLCV | Exact envelope failures |
|---|---|---|---:|---:|---:|
| ASML | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| LRCX | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| KLAC | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| 8035.T | 2021-10-04 | 2026-10-02 | 1,222 | 1,222 | 1 |
| 042700.KS | 2021-10-05 | 2026-10-02 | 1,221 | 1,220 | 3 |
| NVDA | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| AMD | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| AVGO | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| QCOM | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| INTC | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| MSFT | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| GOOGL | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| AMZN | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| RTX | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| SYK | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| ETN | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| HUBB | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| GEV | 2024-03-27 | 2026-10-02 | 632 | 632 | 0 |
| ROK | 2021-10-04 | 2026-10-02 | 1,255 | 1,255 | 0 |
| Total | — | — | **23,155** | **23,154** | **4** |

All nineteen timestamp arrays are strictly ordered and unique, and all five OHLCV arrays align with them. Of these rows, 23,150 are both complete and exact-envelope-valid. This narrow shape result is not a count of production-admissible bars: security binding, session coverage, action basis, availability and publication remain unverified. The audit did not test Top500, intraday ranges, all listings, maximum history, or guaranteed future endpoint service. GEV's requested five-year range returned a shorter series; that fact is preserved, without filling the earlier period or asserting an IPO-date interpretation.

## Reproducible source counterexamples

| Provider label/date | Actual original OHLCV fact | Treatment |
|---|---|---|
| 8035.T / 2022-05-17 | O3821.333251953125; H3866.666748046875; L3770.666748046875; C3869.333251953125 | Close exceeds high; record failed invariant; no correction/drop |
| 042700.KS / 2024-01-15 | O57200; H57700; L56600; C56200 | Close below low; same treatment |
| 042700.KS / 2024-10-14 | O110200; H116000; L110200; C109500 | Close below low; same treatment |
| 042700.KS / 2025-04-09 | O59600; H60700; L58200; C61200 | Close exceeds high; same treatment |
| 042700.KS / 2025-09-19 | Timestamp exists; O/H/L/C/V are all null | Retain row and unknown cause; neither zero nor absent session |

The four price contradictions are material. No epsilon/tolerance or new numerical default was introduced. Hanmi also has thirteen zero-volume rows; they remain distinct from the null-volume row. Whether a source correction or a differing trade/basis convention explains any contradiction requires further source evidence, not a chart-side repair.

Hanmi's latest `currentTradingPeriod.regular.end` is `2026-10-02T06:00:00Z` (15:00 KST), while `regularMarketTime` is `2026-10-02T06:30:19Z`. Current KRX regular stock rules describe a 15:30 close. This is a concrete vendor-calendar conflict. It must not be resolved by selecting the earlier vendor value or silently changing the original record. The domain/session owner needs dated exchange authority, vendor-hint retention and conflict assessment.

Tokyo's current trading-period hint ends at 15:30 JST. JPX's dated announcement describes a change from 15:00 to 15:30 effective 2024-11-05; current JPX rules describe two daily sessions with a lunch break. Applying today's metadata to the full five-year span would be incorrect. No US binder expansion or fabricated Japanese calendar was made.

## Security→listing→price source joins

`global_universe.py` provides IssuerIdentity→SecurityIdentity→ListingIdentity and dated ticker/MIC/currency intervals. `sessions/listing.py` adds evidence ID, source hash and available_at. They are reusable contracts, not populated master-security datasets. `personal/security.py` is a separate namespace; it does not authorize a guessed personal→global mapping.

Actual repository joins still primarily use `company_id → {cik, yahoo}` in `us_sec_tickers_listings.json` / `us_ingested_facts_listings.json`, and `ingestion/replay.py.build_payloads_and_bars` looks up `yahoo_chart:<symbol>:<range>`. Example NVDA is `{cik:0001045810,yahoo:NVDA}`. This does not provide share class, stable security/listing IDs, dated interval, MIC evidence or crosswalk availability. The source replay's issuer/ticker association is not sufficient to admit a production candle series.

Primary source candidates newly checked:

- [NVDA SEC 10-Q cover](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm) supplies issuer common-stock/symbol/exchange facts for a specific filing. Admission still needs original source bytes, EDGAR acceptance evidence, explicit internal IDs and interval/history coverage.
- [Tokyo Electron issuer stock information](https://www.tel.com/ir/stocks/info/index.html) identifies domestic security code8035 and Tokyo Prime listing; it separately identifies TELWY ADR and its ratio. Domestic shares, ADRs and US tickerTEL must stay separate. The current page is a source candidate; it is not a historical listing-vintage dataset.
- Hanmi's response names the company, KRW and KSC/KSE, but no exchange/issuer-issued identity interval was captured in this audit. Vendor metadata alone remains insufficient.

Actual historical identity-repair evidence exists for PARA. `ca_unit_price_identity_repair.json` rejected a current reused-PARA series identifying another company and retained pre-merger history retrieved via PSKY. Original `PARA_price_source.json` has1,255 full daily OHLCV rows from2021-09-27 to2026-09-25, hash `d3627be917c0a5f4f51de223e1fe7e41b99622d88c4937f27225c4a56aeb1e21`; derived `PARA_historical_chart.json` has969 rows through2025-08-06. These bundled bytes are **REPAIR_EVIDENCE**, not a ready general price store/security master. The later mapping document is explicitly retrieval-identity-only; it must not become an as-of economic input or generic historical listing proof. The existing repair illustrates why provider symbol and security identity need distinct, versioned relations.

## Session/timezone and separate times

Reuse `sessions/calendar.py` as the versioned calendar contract and `sessions/binder.py` for supported US daily joins. Its admitted vendor-code map is only NMS→XNAS, NYQ→XNYS and PCX→ARCX. JapaneseJPX and KoreanKSC are unsupported; suffix-to-MIC inference is not evidence. Calendar contract pins IANA runtime timezone-data version and requires original source hashes plus row availability. Existing fixtures cannot establish actual exchange calendars.

| Time | Concrete observed fact | Production interpretation |
|---|---|---|
| Source daily bar timestamp | US09:30 local open; JP/KR09:00 local open for returned samples | Session-label candidate; not source publication |
| Market close | Candidate exchange rules and dated exceptions | Separate dated session evidence; calendar-close guard is a lower bound |
| regularMarketTime | NVDA/MSFT20:00:01Z on latest session; Hanmi06:30:19Z | Latest vendor print metadata; not each historical bar's availability/finality |
| acquired start/end | Actual probe clock records this turn | Observation of current response; no earlier knowability claim |
| persisted/fetched time | Scoped evidence or raw-store timestamp | Storage fact; not provider availability |
| historical available_at | No supplied source proof | Null/unavailable; retrospective view differs from historical replay |

The existing Yahoo parser selects adjclose when present and drops close-null rows. It also defaults currency toUSD. Existing `to_price_point` and Technical `bars_from_yahoo_chart` set available_at to bar time. These existing semantics are left unchanged; they are not reused as historical-final-OHLCV availability proof. Full O/H/L/V extraction already exists in PR41's experimental bridge; its structural extraction may later be reused after domain registration, but it cannot manufacture listing, calendar or publication evidence.

Official sources checked through web retrieval on2026-10-04:

| Source candidate | Supports | Does not establish |
|---|---|---|
| [Nasdaq 2026 calendar/hours](https://www.nasdaq.com/market-activity/stock-market-holiday-schedule) and [NasdaqTrader calendar](https://nasdaqtrader.com/trader.aspx?id=Calendar) | Current regular09:30–16:00 ET and2026 holiday/early-close notices | Full historical calendar bytes/admission; per-bar Yahoo publication |
| [JPX current domestic hours](https://www.jpx.co.jp/english/equities/trading/domestic/01.html) | Current morning/afternoon schedule | All historical exceptional session rows |
| [JPX dated2023-09-20 announcement](https://www.jpx.co.jp/corporate/news/news-releases/1030/20230920-01.html) | Announced close extension effective2024-11-05 | Historical minute-accurate source available_at or full calendar |
| [KRX stock rules](https://regulation.krx.co.kr/contents/RGL/03/03010100/RGL03010100T1.jsp) | Current regular09:00–15:30 KST | Full dated exception/holiday vintage or vendor-feed mapping |

Source content was verified through retrieval; original hash-addressed exchange notices/calendar rows are not materialized by this report. A candidate public webpage is not a production CalendarVintage.

## Adjustment/corporate-action source audit

The raw-store naming is not the provider authority. Of1,404 `yahoo_chart` IDs,1,346 manifests sayYAHOO_CHART and58 sayTIINGO_DAILY_RAW. Tiingo fallback conversion in `tools/fetch_tiingo_prices.py.to_chart` retains **close only** and constructs21:00UTC timestamps year-round. It loses O/H/L/V and does not represent real session close across US daylight-saving time. To obtain Tiingo OHLCV later, use original `tiingo_eod` bytes plus verified source metadata/calendar; never reverse-engineer missing prices from transformed chart IDs. There are74 TIINGO_EOD_JSON manifests, but their bytes are absent here. No Tiingo account key was read or API call made.

All nineteen current Yahoo samples include close and adjclose arrays, but the request did not request action events. Missing events therefore means NOT_REQUESTED/UNKNOWN_COVERAGE, not no corporate actions. A finite adjclose does not certify adjusted open/high/low/volume or dividend/split methodology. No raw unadjusted OHLCV was reconstructed from it.

Prior PR41 `nvda_events_5y_original.json` supplies a Yahoo split-event candidate and original hash. Its outer map key and inner event date differ; use source-documented event-date semantics, not the key as an announced timestamp. Existing TrackA `ca_unit_policy_v1.json` and bundled issuer HTML supply split/action evidence, e.g. NVIDIA. `audit_mcap_store.mcap_price` restores a scalar market-cap price using split factors after as_of; it is not a full-candle adjustment engine and stays untouched. Its policy cannot be silently generalized to a different chart basis.

[Tiingo's official EOD documentation](https://www.tiingo.com/documentation/end-of-day) documents original/adjusted OHLCV and split/dividend fields, with source methodology and evening corrections. It requires a token; documentation availability does not show that account entitlements or raw history are presently accessible. It is a reuse candidate subject to original-byte restoration and authorized access. Its usual EOD release/correction window is source behavior, not an exact availability rule for each row; no synthetic17:30 or20:00 available_at was added.

## Quote-state source support

All nineteen captured chart responses lack explicit `marketState`, `exchangeDataDelayedBy` and `quoteType`; regularMarketTime/currentTradingPeriod are present. They cannot certify real-time versus delayed feed, official closing print or bar finality. Quote state remainsUNKNOWN, independently of product LIVE/publication state and exchange open/closed state.

Yahoo's official help search results identify exchange/delay/provider guidance and user-visible real-time/delayed indicators, but direct help retrieval returned429. Even a general exchange-delay table would not certify these exact endpoint responses. Future support should preserve a vendor's explicit per-feed state/timestamp/delay with source evidence; no quote endpoint, token/crumb flow, browser login or new provider was introduced here.

## v0.1 adequacy and proposed market corrections

P0 v0.1's architecture is appropriate: it already separates identities, time facts, source lineage, adjustments, quote state, readiness and publication. The actual evidence proves it cannot yet become a production schema unchanged without more precise admission/absence fields. Keep v0.1 intact; the following are **v0.2 proposal requirements**, not adopted enums:

| Proposal | Evidence that requires it |
|---|---|
| Explicit source-fact epistemic status: exact, observed bound, declared assumption, unknown; retained evidence/ref per available_at/finality fact | Present acquired current history while original publication is unknown; old parser reuses bar timestamp |
| Separate provider interval hints, authoritative dated session/calendar refs and a conflict assessment | Hanmi15:00 vendor hint versus15:30 exchange rules; JPX dated close change |
| Per-row admission result/reason; raw-index/timestamp retention; response coverage/null reason without gap filling | Four genuine OHLC contradictions plus one all-null timestamp; source missing is not absent session |
| Explicit action-request/coverage and per-field basis status; source_kind/schema/transform chain/raw-input hashes | Action request omitted; Tiingo close-only conversion sits underYahoo IDs; close+adjclose insufficient for full adjusted candles |
| Range request versus returned span; listing-history status and provider-symbol mapping evidence | GEV returns632 rows; PARA current-symbol reuse repair; foreign provider labels remain exploratory |
| Quote-state evidence absent/unsupported versus exchange-session state and product publication | All responses lack exact quote-delay/state fields; closed market does not prove official close |

Decimal transport preservation remains required for Portfolio; this audit does not convert raw provider JSON binary numeric facts into fabricated Decimal precision. API/MCP would later return one domain/product payload/hash/state for the same snapshot, not run separate Yahoo requests and financial calculations.

## Dependency classification for market work

| Item | No protected mutation | P01 impact | TrackC code_hash impact | Integration/FPIA |
|---|---|---|---|---|
| Read-only source inventory, scoped raw bytes, identity/calendar/action candidate register and schema proposal | Yes | None | None | No production admission claimed |
| Read-only source counterexample/replay harness outside package under experiment scope | Possible | None if Web untouched | None if package untouched | Scoped validation only; cannot certify merged production |
| Restore immutable original raw-store artifacts and verify manifest/hash/role without owner source edits | Possible with authorized artifact access | None | None | Later producer consumers still need exact-tree evidence |
| Populate reviewed security/listing and dated calendar/action evidence as data, preserving hashes and availability | Candidate non-protected work; no guessed values | None by itself | None by itself | Domain owner must admit; scope must be checked before actual source writes |
| Register production OHLCV projection or change package provider/parser/binder | No; deferred | Depends on product wiring | **Yes** for packagePython | **Required**, after MAC-X1/FPIA; owner coordination |
| Register ChartDocument producer/validator/serializer and protected Web assembler route | No; deferred | **Yes** when protected paths change | **Yes** if packagePython changes | **Required**; protected contract acceptance |
| UI/API/MCP publication route, exact subject lifecycle/invalidation | Deferred, depends on implementation paths | Potential/required for guarded Web wiring | Potential | **Required** before merged production certification |

Safe work now is evidence restoration/inventory, source candidate reconciliation, raw counterexample review, schema-v0.2 proposal and non-package experiment specifications. After FPIA, owners can admit lossless projection and registered product/publication wiring. FPIA resolution is necessary for package integration but does not cure missing market evidence. No Frozen or Official change, grant or canonical merge is authorized by this report.

Evidence artifacts: `MARKET_EVIDENCE.json` (initial four + exact source blobs), `MARKET_REFERENCE_COVERAGE.json` (all nineteen + row invariants), `PUBLIC_ACQUISITION_PROBES.json`, `ADDITIONAL_REFERENCE_US_PROBES.json`, `SOURCE_COUNTEREXAMPLES.json`, and nineteen original response JSON files. No existing regression/Actions or production-ready claim is made from this prerequisite audit.
