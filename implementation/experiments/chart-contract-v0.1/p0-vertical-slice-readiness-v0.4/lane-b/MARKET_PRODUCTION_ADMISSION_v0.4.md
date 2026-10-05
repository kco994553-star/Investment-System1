# Lane B — Market/OHLCV production admission v0.4

Baseline: PR #41 Chart `581c61c4af859f6cbdc3418209bba9be7bbc76a3`. This is an additive readiness assessment, not a production schema or implementation. Core 81 / Extended 24 / Research Candidates 8, all prior reports, original source payloads and their history remain unchanged. There was no new acquisition or requirement-inventory expansion.

## Decision and bounded change

**Production admission remains BLOCKED for 19/19 provider symbols; admitted 0/19.** Original OHLCV structure remains 17 READY / 2 PARTIAL, with 23,155 rows preserved. A structurally present candle is not an admitted economic/security/listing/session/basis/PIT observation.

This stage closes no missing production evidence and makes no readiness promotion. It converts the existing identity/time and basis/action evidence into the requested priority-ordered 19 × 8 matrix. Eight shared evidence families remain unclosed. The 152 non-ready field cells are repeated scope manifestations, not 152 independent governance decisions. The two affected raw subjects add five preserved anomaly rows whose cause and production render/indicator policy remain unresolved.

Exact field values, reasons and JSON-pointer provenance are in [MARKET_ADMISSION_19_BY_8_v0.4.json](MARKET_ADMISSION_19_BY_8_v0.4.json). Each provider symbol is explicitly distinguished from a certified security identity. READY would apply only to the exact field scope; PARTIAL identifies existing candidates; BLOCKED identifies an unadmitted required join; NOT_AVAILABLE retains absent evidence; UNKNOWN retains an unproved exact state.

## 19-symbol admission matrix

Columns follow the user's priority order. Listing/history is BLOCKED because the required admitted listing relation is absent, even where a current venue association or part of listing history exists. The history-only substatus is 18 NOT_AVAILABLE / 1 PARTIAL (GEV). Exchange/session/timezone is PARTIAL for current candidate facts; dated session join is independently BLOCKED.

| Provider symbol | Security identity | Listing/history | Exchange/session/timezone | Dated join | Adjustment | Corporate action | Historical available_at | Quote state | OHLCV structure | Admission |
|---|---|---|---|---|---|---|---|---|---|---|
| ASML | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| LRCX | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| KLAC | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| 8035.T | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | PARTIAL | BLOCKED |
| 042700.KS | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | PARTIAL | BLOCKED |
| NVDA | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| AMD | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| AVGO | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| QCOM | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| INTC | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| MSFT | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| GOOGL | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| AMZN | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| RTX | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| SYK | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| ETN | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| HUBB | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| GEV | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |
| ROK | BLOCKED | BLOCKED | PARTIAL | BLOCKED | PARTIAL | PARTIAL | NOT_AVAILABLE | UNKNOWN | READY | BLOCKED |

No field becomes READY in this projection. Quote-state uses the explicit existing value UNKNOWN; v0.3's evidence-readiness NOT_AVAILABLE remains preserved by reference. This normalization supplies no new state evidence.

## Exact evidence gaps and closing actions

1. **Security identity — 19 BLOCKED.** A source owner must admit a dated issuer → security relation for the exact priced economic instrument. Current SEC issuer/ticker associations corroborate 17 US labels; issuer Tokyo Electron code 8035 and DART Hanmi code 042700 corroborate the other two. A company alias, ticker, CIK, suffix or firstTradeDate is insufficient. ASML's NASDAQ ordinary-share identifiers are current candidates, distinct from Euronext; Tokyo domestic shares must not inherit TELWY ADR identifiers.
2. **Listing identity/history — 19 BLOCKED.** Supply internal listing identity, share form/currency/MIC, validity intervals, provider-series crosswalk and continuity/change/reuse evidence over the admitted history. GEV has 632 raw rows from 2024-03-27: the first three (2024-03-27, 2024-03-28, 2024-04-01) precede the confirmed 2024-04-02 regular-way opening. Preserve those rows and require exact trading-regime/provider mapping; date-compatible when-issued candidate evidence does not certify the splice.
3. **Exchange/session/timezone — 19 PARTIAL.** Admit complete source-bound calendar/timezone/session vintages, including holidays, early closes, extraordinary closures and split sessions. Existing ordinary-hour sources and some dated notices are candidates. Nasdaq 2025-01-09 extraordinary closure has a separate notice; current NYSE calendar alone is not 2021–2026 history. JPX changed close from 15:00 to 15:30 on 2024-11-05 and has a midday break. KRX ordinary 09:00–15:30 is separate from the 2025-11-13 CSAT 10:00–16:30 exception. A current gmtoffset is not five years of US DST.
4. **Dated session join — 19 BLOCKED.** Bind each exact provider bar label/date to its admitted security/listing/session/calendar relation with conflict/absence reasons. Hanmi raw index 1004 labels 2025-11-13 09:00 KST while the official opening was 10:00; bar timestamp == actual open is invalid as a universal rule. The latest Hanmi vendor regular-period end 15:00 also conflicts with ordinary KRX close 15:30. Preserve both facts. The existing US binder is a historical read-only Integration candidate, not present in this Chart HEAD; foreign support cannot be added by guessing aliases.
5. **Adjustment basis — 19 PARTIAL.** Obtain exact source/transform/version evidence for each O/H/L/C/V and adjclose field, raw/unadjusted versus split/dividend-adjusted semantics, volume adjustment and source revision behavior. Original bytes do not prove unadjusted prices. An adjclose scalar does not supply adjusted O/H/L/V. The currently retained raw-unadjusted full OHLCV is NOT_AVAILABLE and a complete split/dividend-adjusted full series is BLOCKED.
6. **Corporate-action basis — 19 PARTIAL.** Admit a complete, identity-continuous action ledger with source/version and distinct announcement, record, ex-date, legal effect, adjusted-trading and availability roles. Existing separate requests returned 283 dividend / 9 split candidates. AMD's empty map proves only the observed response. The original price requests omitted action events; absence is NOT_REQUESTED, not no-actions. Source/date candidates do not establish a certified historical ledger or cause of anomalies.
7. **Historical available_at — 19 NOT_AVAILABLE.** Supply verifiable historical per-bar/action publication, revision and finality/access evidence; absent values remain UNKNOWN/null. Bar date, market close, provider latest quote time, current collector observation and persistence time cannot fill this gap. A future collection can record its own current observation bounds; it cannot retroactively prove historical availability. PIT relaxation is not a closing action in this scope.
8. **Quote-state — 19 UNKNOWN.** Obtain exact source/endpoint/response/row state semantics and finality evidence. All original exact responses omit marketState, exchangeDataDelayedBy and quoteType. Yahoo service guidance is separate (Nasdaq real-time candidate; JP/KR 20-minute candidate; no inference from the NYSE Indices row for equity feeds). Feed state, exchange open/closed state, source close finality and Investment-System Official/LIVE authority remain distinct.

The first exact next step is owner-admitted security/listing/provider interval evidence, followed by dated session/calendar and per-field adjustment/action basis. Historical availability and exact quote-state require source evidence; an offline calculation or UI contract cannot manufacture them. Partial per-symbol closure may be reported without admitting other symbols or historical intervals.

## Existing anomalies preserved

[PRESERVED_RAW_ANOMALIES_v0.4.json](PRESERVED_RAW_ANOMALIES_v0.4.json) carries each original anomaly record unchanged, including exact provider subject, UNBOUND security status, raw source path/full SHA256, index, timestamp, source numeric tokens, JSON pointers, affected fields, comparison source/hash and downstream/render candidates. All five causes remain UNKNOWN, with no production policy adoption.

| Exact provider subject / name hint | Date | Original index | Affected fields in retained record | Deterministic failure | Raw payload SHA256 |
|---|---|---:|---|---|---|
| 8035.T / Tokyo Electron Limited | 2022-05-17 | 149 | high, low, close | CLOSE_GT_HIGH | `4b73393390ac0f41865f6ceab82e682d4b3a69fcf9d42b8264b3ca908c7eb758` |
| 042700.KS / HANMI Semiconductor Co., Ltd. | 2024-01-15 | 560 | high, low, close | CLOSE_LT_LOW | `0fd4f74e03fa3908dda2ae4b7970537fef9e1d855003bd7179c6a3f180390552` |
| 042700.KS / HANMI Semiconductor Co., Ltd. | 2024-10-14 | 740 | high, low, close | CLOSE_LT_LOW | `0fd4f74e03fa3908dda2ae4b7970537fef9e1d855003bd7179c6a3f180390552` |
| 042700.KS / HANMI Semiconductor Co., Ltd. | 2025-04-09 | 859 | high, low, close | CLOSE_GT_HIGH | `0fd4f74e03fa3908dda2ae4b7970537fef9e1d855003bd7179c6a3f180390552` |
| 042700.KS / HANMI Semiconductor Co., Ltd. | 2025-09-19 | 970 | open, high, low, close, volume | SOURCE_NULL_OHLCV | `0fd4f74e03fa3908dda2ae4b7970537fef9e1d855003bd7179c6a3f180390552` |

The Tokyo subject points to `p0-prerequisites/market/probe_8035_T_5y_original.json`; all four Hanmi records point to `p0-prerequisites/market/probe_042700_KS_5y_original.json`. Original and later actions responses have identical affected OHLCV values. No provider action candidate matches an anomaly bar date, but this does not rule out basis issues or prove a cause.

Candidate downstream policy, pending owner adoption: block invalid/missing candles and dependent indicator windows; diagnostic views may annotate retained source values and explicit row state. A degraded series requires a verified explicit gap/reason contract. Until admitted, block the production series. Do not expand high/low, substitute adjclose, delete rows, fill zero values, infer market closure or repair with epsilon/tolerance. The all-null Hanmi row remains distinct from thirteen separate zero-volume rows.

## Time and cross-request semantics

The machine-readable report separates bar label/date, trade event time, dated session time/close, latest provider timestamp, current observed_at, historical available_at, knowledge_time and explicit ingestion/persistence. Unconfirmed exact timestamps are never synthesized. The first four collection completion windows include post-read work; they are not promoted to precise HTTP receipt clocks.

The offline replay confirms all 23,155 timestamps and OHLCV values are equal across the original and separate actions requests. Exactly 10,862 adjclose values differ; query parameters and collection times also differ. The cause is UNKNOWN. These are separate preserved observations, not proof of economic revisions, source error or historically available vintages.

## Minimum Lane B contract contribution, proposal only

Use immutable source snapshot/hash plus exact provider-series/security/listing interval refs; lossless source OHLCV/adjclose tokens with field-basis and validation/absence state; explicit action-ledger/transform/version refs; provider-label-to-dated-session/calendar relation and conflict reasons; distinct timestamp roles/access bounds; exact quote-state UNKNOWN where unproved; and explicit row/gap diagnostics. Immutable source-rights evidence may be included in the payload. Current mutable Product publication/invalidation authority remains external to immutable payload identity. A product validator must refuse required unadmitted bindings rather than letting the renderer repair or recompute them.

This supplies the bounded Lane B facts needed for the shared C01–C08 assessment. It does not freeze a schema, add ACTUAL/GICS dependencies to Lane A, or implement API/Web/MCP calculations. Product authority, source rights and exact P01/Track C/FPIA closure are common implementation gates owned by the parent assessment and are separate from this 19 × 8 evidence matrix.

## Offline verification and implementation boundary

[OFFLINE_EVIDENCE_REPLAY_v0.4.json](OFFLINE_EVIDENCE_REPLAY_v0.4.json) records PASS for exact original bytes against the Chart baseline and acquisition SHA256/size records: 38 price/actions payloads, 22 retained identity/session source captures, and 8 existing evidence records (68 existing files total). It independently replays ordered/aligned arrays, all 23,155 rows, exactly four envelope failures/one all-null row, exact anomaly numeric tokens, action counts, both timestamp/listing counterexamples and 10,862 adjclose differences. It does not rerun source acquisition.

Read-only replay command from repository root:

```sh
python implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/lane-b/verify_market_evidence.py
```

Safe work now: existing-byte replay, field matrix/provenance consolidation, source-binding data proposals and owner/path planning outside package/protected code. Protected/package production adapters, source admission, calendar population for product use, candle repair policies, Official/LIVE promotion, grants, Holdout access, Frozen changes and canonical merge remain outside this stage. No production code was changed. Production tests and actual Chart merge-result FPIA are NOT_RUN by this lane. No new D3 was required for this read-only evidence consolidation; runtime policy/source admission remains the relevant owner's action.
