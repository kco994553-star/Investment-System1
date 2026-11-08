# Owner-private retained price bridge — 2026-11-05

Owner decision: one screen, public default and authenticated private expansion. Both layers use the same calculation engine, weights, gates and missing-value rules. KIS plus eligible fundamentals may now produce private QGV, replacing the earlier prohibition in this scope. Public official results, ranks and TARGET remain independent. Main owns UI/auth/server/workflows/deployment; Codex owns these offline adapters. No new source request, workflow, permission or deployment is included.

## Implementation and reuse

Base: #478 `419add34261b6d976f374e1e962015f8ceb4927e` (technical path). Canonical observed: `620f57f264896c1efa34ac8e6c19ccd28c10d7d3`.

- `research/kis_price_bridge.py`: source receipt/hash and returned query validation; decimal-string common bars; existing NYSE calendar/actual close; confirmed split-only transformation; last-success incremental merge; shared technical and ledger adapters.
- `research/private_layer_qgv.py`: existing central `prepare → price_status → engine_quotes → score → projection`, unchanged calc23.1, default balanced/gate-on/type weights, same fixed operational membership. Private supplier evidence is checked before it becomes an engine quote. Known source split events retain the existing share-count split gate. No public publisher/signature/rank assignment is called.
- `tools/kis_retained_calculate.py`: normal CLI, local job JSON only. Modes normalize/analyze/compare/positions/update/qgv/technical-measures/technical-board. Output is outside Git,0600,new-file-only; console is a fixed success/failure line. It performs no HTTP/authentication.
- Existing `chart_bars`, `technical_display`/GSQ-015, `pit_filings.session_close`, ledger `observe/snapshot` and central QGV functions are called. There is no new scoring/indicator/portfolio engine. Synthetic daily-input gates are not changed.

`normalize` job has body_path plus arguments receipt/request/evidence/basis. Other modes have arguments matching the pure function. A generated result is a private candidate, not a validated Worker response or deployment artifact. The default output is never copied into public Pages.

## Main contract: kis-bars/1

| Field | Meaning |
| --- | --- |
| schema, symbol, security_id, issuer_id, exchange, currency | Version, requested/returned symbol, independently evidenced IDs or null, exchange, USD. CIK is not a security ID. |
| source, source_sha256, source_query | True provider and original bytes/query provenance; never an invented IEX source. |
| price_basis_date, collected_at, corrected_at | Last retained session; original receipt clock; proven correction clock or null. Recovery time is not capture time. |
| historical_available_at | Null unless independently established; current receipt does not establish historical PIT. |
| calendar, timezone, timestamp_basis | NYSE, America/New_York, date-only source. A derived midnight is an adapter join key, not a provider observation/publication time. |
| basis, dividend_adjustment | RAW MODP0 or SPLIT_ADJUSTED from confirmed events only; no dividends. MODP1 is never silently relabeled as split-only. |
| session_scope, price_scope_status, volume_basis, amount_basis | Evidence status of provider coverage. Scope metadata alone does not change the common price formulas/gates. Unknown volume meaning keeps volume adoption diagnostic. |
| confirmed_ranges / held_ranges | Inclusive from/to and evidence / reason. Held windows never yield adopted indicators. |
| splits | date, ratio as new shares/old shares, evidence, status CONFIRMED. Prior prices ÷ ratio; volume × ratio; amount unchanged. Raw bars are retained. |
| bars / raw_bars | Ordered unique sessions; date, OHLC, volume, amount as decimal strings or null, corrected boolean/null, per-row source_sha256 and collected_at. Zero volume differs from missing. |
| rejected_rows / suspensions | Rejected date/reason and separately proven suspension facts. Missing/zero volume alone does not establish suspension. |

Use provider attribution “KIS 보관 일봉” until consolidated/correction evidence exists; do not label every retained response “통합 정정 완료”. The adapter only admits a completed session using the existing early-close-aware NYSE close. It rejects intraday capture and never fills non-trading days.

`analyze` returns the existing13 indicator components with raw_value/value/null_reasons, raw/adopted counts and readiness. Status NORMAL/STALE/MISSING concerns the requested basis date; this is separate from adoption. Readiness carries current archive capture; historical availability remains unproven. The confirmed split-only adapter now feeds the adjusted OHLC path to the same kernels, preserves full recursive seeds and identifies diagnostic/chart basis explicitly. It validates adjusted bytes against the retained raw values and documented split ratios, requires action-coverage evidence and never treats MODP1 as proof. Main must match the chart and indicator basis.

Follow-up: the adapter now passes an evidenced action interval containing the observation date to the common kernel, which checks each metric's required window. Previously it discarded an interval unless it covered all retained history, incorrectly suppressing proven rolling windows too. With synthetic last20-session evidence, SMA5/SMA20 and the three Bollinger components match the common kernel exactly; recursive indicators stay null when their full seed precedes the evidence. Formulas, seeds and eligibility rules are unchanged.

Retained request audits distinguish the query's BYMD upper bound, returned100-session page, in-page gaps, older-page history not retained, and comparison sessions after BYMD that were never requested. MODP0/MODP1 byte equality is not split evidence. Issuer documents may be linked only after matching the KIS query/response identity and reviewed dates; another supplier's adoption flag is not inherited. A DOCUMENT_RECONSTRUCTED interval describes a bounded research application, not a permanent security master interval or historical PIT availability. Company-level evidence decisions, adoption deltas and original bytes are retained privately.

`positions` requires explicit same-day holdings, matched security identity and currency. It uses original raw denomination for the existing ledger's close marking and creates no orders. Missing holdings or fixed link yields NOT_COMPUTED; synthetic holdings are never reported as the owner's portfolio.

Private QGV uses the guarded `kis-qgv/1` output schema and preserves original engine factors/axis reasons and configuration. Supplied prices need source security evidence for the requested day; missing dates are not carried from a neighboring session. All504 operational rows remain in the calculation. Engine totals without V are reference totals, not full QGV coverage. Relative comparison/ranks stay unavailable unless the paired population/inputs are established. Financial-model V exclusions remain the engine's own reasons.

## Update interface, without activating collection

Phase1 remains one daily close. Main schedules after the provider's documented correction window, with that source-evidence status shown separately; passage of12:00 KST alone does not prove a correction. Initial load stores raw MODP0 and provenance; optional MODP1 comparison stays separate. Incremental input repeats the latest100-session page to catch revisions; deduplicate by symbol/session/basis, compare values separately from capture metadata, preserve older history and per-row provenance. Missing latest/requested sessions or rejected rows mark PARTIAL/FAILED, keep last_success_at and last valid values, and display stale. A newer capture with identical values is not a revision. Split/identity/range changes require explicit rebuild/review, not blind append. Source request limits/retries remain Main's approved collector settings; no collector is introduced here.

## Synthetic handoff and real evidence

`tools/kis_contract_fixture.py --output-dir <outside-Git>` emits two explicitly synthetic contract files and SHA-256: raw and confirmed2:1 split with a held session. The generator is public code; rendered files stay out of public tracked artifacts under the existing guard. Main can generate identical bytes locally, test its authenticated fake upstream and UI, and inspect the field table without accessing actual quotes.

Retained original archives and calculated company outputs stay in the KIS-specific private handoff branch. This PR contains no actual prices, per-code source hashes or KIS-derived company results. Actual archive/manifest and match-comparison counts are supplied privately. Synthetic engine tests, actual offline calculation, authenticated development UI, scheduled updates, deployment and owner use are separate acceptance states. A preserved research handoff is not an authenticated production data route; moving staged/chart/A/AMD.json into the authenticated read path remains Main integration work.

## Single-company measures and a dated group board

`research/private_technical_board.py` connects existing `technical_measures.measure`, `technical_leaderboard.build_board` and `filter_board`. It does not introduce another indicator/ranking engine. The existing `analyze` path remains the thirteen chart components; a complete comparison population is not required for either single-company path.

| Mode / result | Inputs and rule | Main use |
| --- | --- | --- |
| `technical-measures` / `kis-technical-measures/1` | One retained contract `c`, explicit `series_id`, `evaluation_day` | Three/six/twelve-calendar-month price momentum(%), six-month daily simple-return sample volatility(%/day, ddof1, not annualized), six-month mean dollar volume(USD/trading day) |
| `technical-board` / `kis-technical-board/1` | `series:[{series_id,contract}]`, one dated `group`, separately supplied `security_links`, optional `conditions` | Original complete group, metric-specific valid N, median/rank/decile and filter selection |

The five measures are pinned to the requested completed NYSE session S. Unlike a chart that may display the last retained day as stale, a missing S does **not** move the comparison date backwards. `data_asof` records the actual last retained session; missing-window raw/value remain null. Each price window uses the shared calendar anchor, all expected closes/returns and the existing identity/action gates. `gt_zero` follows adopted value; `raw_gt_zero` is diagnostic. Held intervals and dated source identity apply to each required window. No recursive chart seed is shortened or recomputed by this path.

KIS amount/volume never generates VWAP. The adapter preserves actual retained VWAP/trade-count fields from an eligible normalized baseline, if present, but keeps `trade_scope_status=UNCONFIRMED`; raw VWAP×volume, complete/observed means and `close_volume_proxy` remain separate from adopted dollar volume. The previously established provider-scope limitation remains in force. IEX last-trade observations are not accepted as OHLCV contracts.

### Board identity and filtering

- `group` reuses the existing fields `group_id`, `signal_day`, `membership_status`, `member_security_ids`, `membership_source`. Unknown membership has members=null, N/ranks/deciles=null. A confirmed group with missing measurement links retains its full member denominator and has valid N=0 where appropriate.
- A `security_link` supplies `series_id`, `security_id`, `identifier_type`, `valid_from`, `valid_to`, `reference`. The link must be current at S and consistent with the source contract's identity and any existing security ID. Supported identifier types are PERMNO, FIGI, ISIN, CUSIP, EXCHANGE_SECURITY_ID or PROVIDER_SECURITY_ID. These describe supplied evidence; this adapter neither obtains IDs nor verifies an external master. CIK/issuer ID and ticker are not accepted as security IDs. No links are inferred from a matching symbol.
- Author-created tests may use SYNTHETIC_FIXED_SECURITY_ID only when all contracts carry `fixture_kind=SYNTHETIC_NOT_A_COMPANY`. Synthetic and retained real inputs cannot be mixed. `evidence_kind` identifies the output scope; a synthetic fixture's rank count is not an actual security count.
- Missing links leave company measures intact. Repeated provider series linked to one security are rejected; the caller must resolve the duplicate source before ranking. Source failure/partial refresh status remains visible and cannot manufacture a missing S measurement.
- `conditions` uses the existing independent predicates. The result contains the full original `board` plus `selection.security_ids` and `rank_origin=ORIGINAL_GROUP`. Unknown membership explicitly yields `selection.status=NOT_COMPUTED`/`GROUP_MEMBERSHIP_UNCONFIRMED`; its empty selected-ID list is not a proven zero-match result. Filtered rows retain their original metric-specific N, ranks and deciles. Missing volatility and N<10 never pass `exclude_D10`.
- Both modes carry `publication_scope=OWNER_PRIVATE_ONLY`, `historical_available_at=null`/`pit_status=NOT_VERIFIED`. Current capture time is not historical availability. No group or QGV result is inferred from a one-company diagnostic.

Additional reader fields are `measurements`, `linkage` with per-series missing-link reasons, `requested_series_count`, `fixed_security_id_count`, `ranked_security_count`, and the nested shared board/selection. Each metric retains `raw_value`, `value`, `state=VALUE/DIAGNOSTIC/NOT_COMPUTED`, unit, observation/expected counts and null reasons. Public default data and private expansion use the same formulas and missing-value rules; Main chooses the authenticated source without replacing public official scores/ranks.

### Offline examples and update ownership

Run the existing CLI with a supplied local job:

```sh
python implementation/tools/kis_retained_calculate.py --job /private/jobs/company-measures.json --output /private/results/company-measures.json
python implementation/tools/kis_retained_calculate.py --job /private/jobs/dated-board.json --output /private/results/dated-board.json
```

Job shapes are `{mode:"technical-measures",arguments:{c:<retained contract>,evaluation_day:"2017-01-06",series_id:"SYNTHETIC:REQUEST:1"}}` and `{mode:"technical-board",arguments:{series:[...],group:{...},security_links:[...],conditions:[{metric:"volatility_6m",condition:"exclude_D10"}]}}`. Dates in these examples are author-created test dates. The synthetic test generator in `tests/research/test_private_technical_board.py` supplies twenty confirmed test members: original volatility N20, k2; excluding D10 selects eighteen while retaining ranks3..20. A missing six-month input can reduce volatility N without changing the momentum denominator; N9 suppresses deciles. Unknown membership preserves absolute company values and leaves the board's N/rank null.

Use the existing dailyprice endpoint and retained query/receipt files described above; no new endpoint is called by either mode. A three-month measure needs the anchor plus every completed session through S. Six/twelve-month measures need their longer explicit calendar windows, and recursive chart indicators retain the original initial-load start. A retained100-session page may cover three months but does not establish six/twelve months. Multiple source pages are only stitched after request identity, boundaries, pagination, original hashes and overlaps are verified; this is independent of a complete market population.

Initial loading should target the required longest window; with a source that actually returns100 sessions/page, a twelve-month window needs approximately3 pages per security, not a guaranteed API limit. The existing approved collector settings and request budget must govern any actual acquisition. Incremental refresh reuses the overlapping recent page, verifies all requested dates, and runs `merge_update` before the same adapters. Unchanged original data and settings reuse prior results; revised dates trigger only affected measures. Key caches by provider/query, security evidence, basis, S and settings hash. A failed/partial refresh preserves last-success data and explicit stale state; no retries or schedules are executed here.

Main owns authenticated routing, UI source selection, approved scheduling, retry limits and rights/operational activation. KIS private-use boundaries and the separate public-redistribution review remain unchanged. This code provides offline calculations, units and failure reasons, not new collection, a permission change, a scheduled update or public publication.

## Integration with merged Main readers (#470 / #471)

Canonical `ab6a83c3be2276abdcf855c71c5f273926e2dcc4` includes #470, #471 and the already resolved #481 screen fix. The #480 PR base remains #478; the existing #467 → #469 → #478 → #480 calculation dependency chain is preserved.

The rich `kis-technical-board/1.board` rows retain units, window boundaries and observation diagnostics. Directly passing that object to `IS2.techScreen.validate` fails with `KEY_UNKNOWN` at `rows[0].unit`: the existing reader intentionally accepts an exact display shape. New offline mode `technical-reader` accepts an **already calculated** result and exports only that accepted shape. It neither invokes a price/indicator calculator nor changes values, null reasons, conditions, ranks, valid N, membership or dates. The original result remains the evidence source.

```json
{"mode":"technical-reader","arguments":{"result":"<parsed saved kis-technical-board/1 object, not a pathname>"}}
```

Use the same CLI with a new private output filename. The result is `{data_kind:"SYNTHETIC"|"RETAINED_INPUT", publication_scope:"OWNER_PRIVATE_ONLY", cases:{private:<technical-leaderboard/1>}}`. Main can call `IS2.techScreen.validate(payload)` on its authenticated response and reuse the existing filter/display functions. The synthetic 20-member and unknown-group cases are exercised against the actual merged JS reader. Decimal values retain exact precision; exponent notation such as `1E-7` and `0E-49` is rendered as plain decimal text because the reader rejects exponents. This uses no float or rounding. The known units are checked before omitting them from the strict row: momentum `PERCENT`, volatility `PERCENT_PER_DAY` (sample standard deviation, no annualisation), dollar volume `USD_PER_TRADING_DAY`. A unit/date mismatch is refused rather than converted.

A confirmed group member without any requested price series remains in the original board with `series_id:null`. Main's current reader requires a nonempty string even when `security_id` exists. The exporter refuses with `READER_SERIES_ID_MISSING`; it does not invent a series/security identifier or remove the member. Main owns any change to that reader's nullable-series contract. Missing metrics for an existing series remain ordinary null rows and are supported.

`technical-measures` still provides five per-company metrics and their evidence; it is not the existing chart/13-component `analyze` result or a Lab performance file. #471's `lab-backtest-v2` accepts its separately agreed aggregate diagnostics only. Do not rename these files to satisfy another reader. Keep source collection time, requested signal day, original observation day, current lookup time and historical PIT status separate; projecting the display shape creates no fresh source observation or new adoption. Authentication, private response caching and routing remain Main's work.
