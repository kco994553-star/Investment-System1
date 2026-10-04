# MCP / API architecture independent review

Date: 2026-10-04 KST. Lens: protocol, runtime architecture, reproducibility, credentials. Read-only review; no plugin installation, provider signup, secrets access, payment, repository mutation, or server implementation.

## Vote and ranking

**C (hybrid API ingestion plus optional MCP read-only query) > A (API-only) > B (MCP-first chart runtime).** This is one independent vote, not a majority result. C is recommended as a target architecture, implemented API-first now; defer a custom MCP server until the common query/serialization contract is validated. A is a valid MVP subset of C, not a bad architecture.

| Candidate | Advantages | Material problems | Judgment |
|---|---|---|---|
| A API-only | Fewest runtime components; deterministic scheduled ingestion and offline replay; easy bulk/history paging and cache ownership | Assistant integration later needs a wrapper or direct tools | Best immediate implementation slice |
| B MCP-first runtime | Existing official provider MCP can speed exploratory assistant queries; structured results possible | Does not create missing OHLC, PIT vintage, rights, consensus history or chart renderer; adds tool/protocol dependency to chart availability | Do not use as primary chart data plane |
| C hybrid | Same stored data and serializers serve frontend and assistant; no duplicated financial calculations; API bulk ingestion can run without an LLM | Requires discipline to avoid building two services upfront | Preferred target; thin MCP after API/data contract |

No measured latency benchmark was run. The claim is architectural: routing every chart fetch through a model adds a model dependency; MCP itself can be invoked deterministically and is not inherently nondeterministic or incapable of bulk data. No universal assertion that MCP is slower than HTTP is warranted.

## Fresh official evidence

1. MCP tools expose external systems including APIs and databases; optional outputSchema and structuredContent support validated server-produced JSON, explicitly distinct from LLM structured generation. MCP does not define finance semantics or data quality.
   https://modelcontextprotocol.io/specification/2026-07-28/server/tools
   Relevant lines 25–33, 253–257, 407–419 (web refs turn8view0 / turn10view2).
2. Official Alpha Vantage MCP wraps its market APIs, needs an API key, and documents remote OAuth; its legacy API-key-in-URL setup is marked deprecated. It demonstrates that MCP is a second access surface for underlying data, not an independent source or free entitlement bypass.
   https://github.com/alphavantage/alpha_vantage_mcp
   https://mcp.alphavantage.co/
   Relevant repository lines 203–210, 226–233 (web refs turn10view0 / turn11view0).
3. Alpha Vantage daily adjusted endpoint documentation includes raw OHLCV plus adjusted close and corporate-action data, and marks the endpoint premium. This is a candidate evidence example, NOT selected provider or spending approval. A provider endpoint marked adjusted must still be checked field by field; adjusted close does not imply adjusted O/H/L.
   https://www.alphavantage.co/documentation/
   TIME_SERIES_DAILY_ADJUSTED section, web refs turn10view1 / turn11view2.
4. MCP security guidance forbids unvalidated token passthrough; downstream API credentials and MCP caller authorization must be distinct security boundaries.
   https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices
   Relevant lines 186–216, web refs turn8view1 / turn10view3.

Do not rely on old transport assumptions when eventually implementing MCP. The versioned 2026-07-28 spec differs from 2025-11-25; select and pin a mutually supported protocol/SDK version after host compatibility verification. Implementing a server is deferred, so no SDK default was chosen.

## Repository evidence and impact

Audit baseline: canonical b8e39a2196a6d7794a04a0cd5393c68329e126ca; trial acaf1b5a82859ac2750a130ebe88f8b4d272ac66. No fresh remote claim is made by this reviewer; parent coordinates live refs.

- Existing `implementation/src/investment_system/ingestion/raw_store.py` RawDatasetStore.put archives old bytes and manifests and separates network collectors from offline engines. Reuse this store; do not replace it with a parallel MCP cache.
- Existing `implementation/src/investment_system/ingestion/manifest.py` documents fetched_at != PIT available_at. Preserve this distinction through every API/MCP response.
- Existing `implementation/src/investment_system/providers/yahoo_chart.py` parse_bars preserves close/adjclose and observed_at but not O/H/L/volume. parse_chart can default currency to USD and observed_at to current time. New chart adapter must not treat those defaults as verified metadata.
- Existing pit_bar gates observed_at only; this is not proof of adjustment-vintage PIT safety. A newly fetched adjusted historical series must not silently become historical simulation evidence.
- Existing chart audit found a missing full Chart Contract and financial renderer. Adding MCP alone closes neither gap.
- Existing code_hash cross-capability coupling is a reported integration risk. A new Python MCP module may change Track C identity even on separate feature work. Do not bypass by changing Frozen hash policy or moving code merely to avoid hash inclusion.

## Minimal seam: no new framework

1. Provider adapter produces raw response bytes and redacted request metadata into RawDatasetStore; credentials stay server-side and never enter artifact source_url, logs, frontend bundle, or prompts.
2. Additive chart normalizer reads stored raw artifacts; preserve old parsers and numeric engines. Existing storage, provenance and publication gates remain authoritative.
3. One versioned ChartQuery/ChartResult service produces explicit instrument/security identity, interval/range, timezone/session, currency/unit, timestamp + OHLCV, source + artifact hash, observed_at, source available_at if evidenced, retrieved_at, adjustment basis/vintage, market-data freshness state, and gap/status reasons. Unknown source availability remains unknown; do not invent timestamps.
4. Query path uses exact snapshot/artifact identity when historical reproducibility is requested. Display-only historical view and PIT-admissible simulation evidence have distinct eligibility. Current adjusted data is not eligible merely because bar timestamps precede as_of.
5. Product renderer consumes those exact serialized values via existing bundle architecture or a narrowly scoped HTTP endpoint. An HTTP API is not mandatory for the first static daily bundle MVP; API-first here means external provider ingestion and stable internal service boundaries.
6. Later optional read-only MCP tools call the same query service: e.g. get_chart_snapshot, get_series_range, get_source_evidence. Return structuredContent + outputSchema with identical snapshot hashes and explicit unavailable/stale states. Bound result sizes; return handles/resources for large history rather than dumping it into context.

MCP should serve assistant investigations, explain provenance, retrieve chart snapshots, and inspect completeness. Do not expose order execution, canonical merge, grant issuance, or unbounded refresh/payable collection through the initial tool set. Tool read-only annotations alone do not enforce authorization.

## Addition/removal/modification recommendations

- Add provider capability/entitlement matrix per endpoint (OHLCV, adjustments, event basis, timestamps, historical vintages, exchange coverage, quotas) before vendor selection.
- Add same-snapshot parity check for HTTP/bundle vs future MCP outputs; do not duplicate serializers/calculations.
- Remove assumption that buying/connecting MCP automatically resolves backend gaps or grants free historical/live rights.
- Remove custom MCP server from P0 critical path; keep it an optional P1/P2 assistant surface.
- Modify prior plan to first try additive OHLCV extraction from existing saved raw artifacts, if complete and allowed, before purchasing/replacing providers. Validate source semantics before promoting.
- Modify quote state to distinguish product publication state (e.g. LIVE) from market feed live/delayed/close state.

## Acceptance checks before coding production path

- Reproducible raw artifact → normalized chart series, including null/gap behavior, same-basis OHLC, timestamps and units.
- Strictly distinguish unknown, delayed, close and stale data; no fabricated fallback metadata.
- Invalid/missing PIT availability/vintage blocks historical model use while allowing clearly labeled display where appropriate.
- Provider failure, rate limit, no entitlement and empty response remain distinct from valid zero values.
- Existing protected code/evidence remains unchanged; integration owner addresses code_hash policy separately.

No custom MCP implementation is needed to complete these gates. No account installation or paid provider decision has been made.
