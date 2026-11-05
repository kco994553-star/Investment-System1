# Owner-private retained price bridge — 2026-11-05

Owner decision: one screen, public default and authenticated private expansion. Both layers use the same calculation engine, weights, gates and missing-value rules. KIS plus eligible fundamentals may now produce private QGV, replacing the earlier prohibition in this scope. Public official results, ranks and TARGET remain independent. Main owns UI/auth/server/workflows/deployment; Codex owns these offline adapters. No new source request, workflow, permission or deployment is included.

## Implementation and reuse

Base: #478 `419add34261b6d976f374e1e962015f8ceb4927e` (technical path). Canonical observed: `620f57f264896c1efa34ac8e6c19ccd28c10d7d3`.

- `research/kis_price_bridge.py`: source receipt/hash and returned query validation; decimal-string common bars; existing NYSE calendar/actual close; confirmed split-only transformation; last-success incremental merge; shared technical and ledger adapters.
- `research/private_layer_qgv.py`: existing central `prepare → price_status → engine_quotes → score → projection`, unchanged calc23.1, default balanced/gate-on/type weights, same fixed operational membership. Private supplier evidence is checked before it becomes an engine quote. Known source split events retain the existing share-count split gate. No public publisher/signature/rank assignment is called.
- `tools/kis_retained_calculate.py`: normal CLI, local job JSON only. Modes normalize/analyze/compare/positions/update/qgv. Output is outside Git,0600,new-file-only; console is a fixed success/failure line. It performs no HTTP/authentication.
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

`analyze` returns the existing13 indicator components with raw_value/value/null_reasons, raw/adopted counts and readiness. Status NORMAL/STALE/MISSING concerns the requested basis date; this is separate from adoption. Readiness carries current archive capture, historical availability remains unproven. `SPLIT_ADJUSTED` charts are normalized, but the current RAW research adapter reports SPLIT_ADJUSTED_DISPLAY_ADAPTER_PENDING and adopts no indicator for that branch. It does not restart recursive seeds or falsely call adjusted bars raw. Main must not overlay raw diagnostic indicators on an adjusted chart as adopted results.

`positions` requires explicit same-day holdings, matched security identity and currency. It uses original raw denomination for the existing ledger's close marking and creates no orders. Missing holdings or fixed link yields NOT_COMPUTED; synthetic holdings are never reported as the owner's portfolio.

Private QGV preserves original engine factors/axis reasons and configuration. Supplied prices need source security evidence for the requested day; missing dates are not carried from a neighboring session. All504 operational rows remain in the calculation. Engine totals without V are reference totals, not full QGV coverage. Relative comparison/ranks stay unavailable unless the paired population/inputs are established. Financial-model V exclusions remain the engine's own reasons.

## Update interface, without activating collection

Phase1 remains one daily close. Main schedules after the provider's documented correction window, with that source-evidence status shown separately; passage of12:00 KST alone does not prove a correction. Initial load stores raw MODP0 and provenance; optional MODP1 comparison stays separate. Incremental input repeats the latest100-session page to catch revisions; deduplicate by symbol/session/basis, compare values separately from capture metadata, preserve older history and per-row provenance. Missing latest/requested sessions or rejected rows mark PARTIAL/FAILED, keep last_success_at and last valid values, and display stale. A newer capture with identical values is not a revision. Split/identity/range changes require explicit rebuild/review, not blind append. Source request limits/retries remain Main's approved collector settings; no collector is introduced here.

## Synthetic handoff and real evidence

`tools/kis_contract_fixture.py --output-dir <outside-Git>` emits two explicitly synthetic contract files and SHA-256: raw and confirmed2:1 split with a held session. The generator is public code; rendered files stay out of public tracked artifacts under the existing guard. Main can generate identical bytes locally, test its authenticated fake upstream and UI, and inspect the field table without accessing actual quotes.

Retained original archives and calculated company outputs stay in the KIS-specific private handoff branch. This PR contains no actual prices, per-code source hashes or KIS-derived company results. Actual archive/manifest and match-comparison counts are supplied privately. Synthetic engine tests, actual offline calculation, authenticated development UI, scheduled updates, deployment and owner use are separate acceptance states. At implementation time the dedicated repository has only main/auth-check and no data branch; moving staged/chart/A/AMD.json into the authenticated read path is Main integration work.
