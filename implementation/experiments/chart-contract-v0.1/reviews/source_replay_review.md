# Independent source / replay feasibility review

Reviewed 2026-10-04 KST. Read-only repository inspection; scratch-only no-key source capture. Repository HEAD at inspection: `68780785688bec33d4bdceb5c42769be7739e6b0`. No source, fixture, canonical raw, or owner-branch edits made.

## Material conclusions

1. **Canonical raw manifest is not accessible raw data.** `implementation/data/raw/blobs` contains only tracked `.gitkeep` in chart-work, audit-repo and audit-trial. No Yahoo body or Git LFS pointer was present. Historical `STORE_INDEX.json` says 6,808 blobs existed in an earlier runner, but those bytes are not in these checkout directories. NVDA 5y manifest claims 140,988 bytes/hash `f1602f57f1c71433830cc88d34e434fee8d31a1ac9fff6fddfa7bda7e97dca5e`; the matching original body cannot be revalidated here. Do not silently replace that vintage with a fresh response.
2. **No account/payment needed to capture one actual source payload.** Existing `tools/fetch_real_data.py` `_get` and `YAHOO_CHART_URL` fetched NVDA daily5d once, HTTP200, original bytes preserved. Existing same-symbol split-events URL also returned HTTP200. This establishes source feasibility only, not entitlement, public redistribution rights, exchange-official status, historical availability or publication permission.
3. **Source OHLCV is available, full identity is not.** Fresh response contains all five OHLCV arrays, five daily observations, USD and named exchange/timezone. Existing ticker→CIK report supports an issuer-mapping candidate; no verified dated security_id/listing_id mapping was found. Do not manufacture `security:NVDA`, infer a MIC from NMS, or present a report's current mapping as historical identity proof.
4. **Do not unlock production rendering for this probe.** Current candidate contract's real-data `NOT_AVAILABLE`, null grant, `NOT_VERIFIED` PIT and unknown price basis remain appropriate. A source preflight can report raw coverage before an identity-complete chart candidate exists.

## Preserved evidence

Scratch root: `/workspace/scratch/e21499bd6a66/source-replay-scratch/`

| Evidence | Result |
|---|---|
| `nvda_5d_original.json` | 1,758 exact bytes, SHA256 `469e185faec7925e724efdc23546967e86f6b3ccbc3ba8d05a2767f968f722a6` |
| `fetch-evidence.json` | Request start `2026-10-04T10:23:16.489426+00:00`, completion `2026-10-04T10:23:22.885843+00:00`; HTTP200, JSON content type |
| Daily source URL | `https://query1.finance.yahoo.com/v8/finance/chart/NVDA?interval=1d&range=5d` |
| `raw-store/blobs/yahoo_chart__NVDA__5d` | Same exact bytes persisted through existing `RawDatasetStore.put` |
| `raw-store/manifests/yahoo_chart__NVDA__5d.json` | Same hash; persistence `fetched_at=2026-10-04T10:24:05.100367+00:00`. Notes explicitly preserve acquisition-window distinction. Do not claim this later persistence time is response receipt or exchange availability. |
| `nvda_events_5y_original.json` | 8,183 exact bytes, SHA256 `928602422cfb5d63d7df588480705a413ddf78d2a24f1bc3e347d50727287a26` |
| `events-fetch-evidence.json` | Second same-symbol request, HTTP200; acquisition `10:23:58.390860Z`–`10:24:05.099565Z` |
| Events source URL | `https://query1.finance.yahoo.com/v8/finance/chart/NVDA?interval=1mo&range=5y&events=split` |

No network restriction or authentication bypass occurred. No retries, credentials or paid service were used. Existing `_get` returns original bytes/status/content-type; it was imported and called directly rather than writing a duplicate fetcher.

## Actual payload fields and limitations

| Dimension | Daily source observation | Limit |
|---|---|---|
| Symbol / name | NVDA / NVIDIA Corporation | Provider symbol/name does not resolve dated internal security/listing identity |
| Interval | `meta.dataGranularity=1d`, request `interval=1d` | Events payload is `1mo`; never relabel it daily |
| OHLCV | All arrays length5, numeric | Covers only five returned daily points, not the historical missing5y artifact |
| Bar timestamp | 2026-09-28 through2026-10-02 at13:30UTC | Session-open stamp; not close-completion/available_at evidence |
| Exchange | `NMS`, `NasdaqGS` | Provider label is not an authoritative MIC mapping |
| Currency / timezone | USD; America/New_York; EDT; current `gmtoffset=-14400` | Never apply fixed EDT offset across historical DST changes |
| Quote summary | regularMarketTime `2026-10-02T20:00:01Z`; regularMarketPrice233.95 | Does not establish all bar finality, delayed/live entitlement or current trade status |
| Session | `currentTradingPeriod` pre/regular/post for one provider session | No historical exchange calendar; cannot fill per-bar historical session_end from it |
| Adjustments | Both quote.close and adjclose exist; identical in these5 rows | Equality over5 days does not establish unadjusted basis or full corporate-action policy |
| Corporate actions | Separate events response has split10:1, event `date=1718026200`; raw map key1717214400 differs | Reuse event payload `date`, not dictionary key as event date; keep raw evidence. No dividend request/no dividend coverage proof. |
| PIT / vintage | Actual response acquisition saved | `available_at`, source revision-vintage history and per-bar finality absent; fetch_at is not historical availability |

## Existing identity evidence

`implementation/reports/us_sec_tickers_listings.json` and `us_ingested_facts_listings.json` both contain `nvda: {yahoo: NVDA, cik: 0001045810}`. First report's full-file SHA256 is `f532cc80edf5305f787e1091cc24244423acd9084375f01727bbd4508d351316`; second `74a615614770980a039dc6eb6caf440eebd3a53efbcfe3226846a56346cfbc13`.

`implementation/data/raw/manifests/sec_tickers.json` records original SEC ticker source URL, fetched_at2026-09-25T08:20:49.704034Z, original hash `3749c0b4a6197feb35e91a6704b3836e45f245dbc2dec1ffa559d1c028852d23`. The original `sec_tickers` body is absent, so the report is not a newly source-revalidated mapping. `universe/resolve.py` already explicitly guards CURRENT_OPEN vs dated historical resolution and warns against applying current ticker mapping backward. `contracts/global_universe.py` already defines issuer/security/listing with dated validity; schema availability does not imply populated records.

## Reuse and minimal next steps

- Reuse `ingestion/raw_store.py` history-preserving raw persistence and `ingestion/manifest.py` hash/provenance. For future acquisition put immediately after receipt and optionally preserve request start/receipt fields separately; do not overwrite past manifests to backdate them.
- Reuse existing `tools/fetch_real_data.py` no-key request construction and failure behavior for captures; no duplicate HTTP stack is needed for this experiment.
- `providers/yahoo_chart.py:parse_bars` discards O/H/L/volume and chooses adjusted close as price. Do not wire that projection into a candlestick adapter; read the exact stored quote arrays through new isolated adapter.
- `ingestion/replay.py:load_price_bars` reuses the lossy projection. Reuse store loading, not claim this existing method delivers OHLCV.
- `tools/audit_mcap_store.py:load_splits` already reads split event values' `date`; `mcap_price` is market-cap specific and must not silently become a whole-OHLC adjustment policy.
- `providers/yahoo_chart.py:to_price_point` assigns available_at=observed and parse_chart has now/USD defaults. These are existing paths, not sufficient evidence for chart availability/currency defaults.
- Best next concrete increment: hash/manifest source preflight + shape/interval/metadata extraction + explicit identity-blocked reason; then bind only a sourced dated identity mapping. Keep source readiness distinct from product publication and historical PIT.
