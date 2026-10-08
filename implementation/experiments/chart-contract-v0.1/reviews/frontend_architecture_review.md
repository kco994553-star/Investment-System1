# Independent frontend/product architecture review

## Verdict

Rank 1: API-first vertical slice with a transport-neutral read model; add a thin MCP adapter later only for demonstrated assistant use. Rank 2: hybrid introduced immediately (same read model, HTTP for browser, MCP for assistant). Rank 3: MCP-first chart delivery.

This is an architectural judgement from the actual audited frontend, not a measured latency benchmark or a claim that HTTP/MCP intrinsically prevents PIT errors. MCP and HTTP can both carry the same JSON. The personal web MVP needs deterministic browser fetch/interaction independently of an LLM/tool invocation. An initial MCP server adds deployment/authentication/discovery surface without supplying missing OHLCV or rendering any chart. Hybrid is a sensible destination, but immediate dual transports duplicate acceptance work before the first useful chart exists. API-first here does not mean a new server is mandatory now: a versioned static JSON read model is sufficient for a bounded fixture demonstrator and can later be served unchanged by a read-only HTTP endpoint.

## Repository implications

Canonical product/render_app.py remains a static placeholder. Noncanonical PR40 product/web_mvp.py already copies JSON/assets and web_assets/app.js is plain JS with cards, navigation, research/freshness guards; there is no framework prerequisite. Keep owner code untouched for this design. Future implementation must be on the agreed separate branch and use the selected exact integration baseline. Frozen calculation modules, publication grants and broad Track C code_hash boundary remain outside scope; a Python adapter still changes package identity even if it only reads values.

Reuse: section state/as_of/source presentation and evidence details; entity IDs/company navigation; read-only bundle validation; actual existing Yahoo parser/source path when proven suitable. Do not call existing snapshot wrappers a ChartSeries contract. Do not transplant RIG graph pan/zoom into candlestick plotting: network topology and time/price coordinates differ.

## Minimal useful vertical slice

One explicitly fixture-labelled security, one supported daily interval, one bounded date range, Candlestick + Volume when valid volume is supplied. Show source, source timestamp/as_of, observed/available metadata when known, price basis, timezone/session, currency, quality/data-state; make missing metadata visible and block claims of historical PIT readiness when unavailable. Crosshair displays exact source OHLCV values, time-range selection works over supplied series, chart has pan/zoom/reset, missing/empty/error states, mobile 360/390 and desktop 1280 layouts. No live data claim, new indicator, forward path, targets, signal zones, probability or assumed corporate-action adjustment.

If the actual source path cannot supply all OHLC fields, do not synthesize them from close. If volume is missing, label volume unavailable; candlestick-only may work but full Candlestick+Volume remains incomplete. If no approved usable data is available, deliver only an explicit fixture demonstrator and separately retain operational-data BLOCKED status. Market-session identity and completed-bar status must come from supplied contract facts; the browser clock must not infer PIT availability.

Proposed read-model fields (design proposal, not approved production schema): schema_version, entity/security/listing identity, interval, requested range, display currency, timezone, price basis, dataset/source references, availability semantics and data state; records contain time, open, high, low, close and optional volume, plus record-level provenance when it differs. Distinguish session-date daily bars from UTC intraday timestamps. A common envelope is useful, but avoid one giant universal chart schema: typed OHLCV/line-series/exposure snapshots should share provenance metadata and retain their domain-specific constraints.

Return already validated series from a pure read-only adapter. UI maps fields into renderer arguments without computing financial values or inventing missing points. Static bundle/HTTP/MCP all reuse that exact adapter and contract if later needed. An MCP discovery tool could enumerate available series, declared capabilities and evidence refs; a read tool could return the same bounded payload. MCP must not become a second calculator or chart-specific method-policy authority.

## Renderer choice (primary-source check, 2026-10-04)

TradingView Lightweight Charts is a plausible fit for the existing framework-free app, not an approval or dependency change. Current official docs show v5.2, client-side ES2020 requirements, ESM and standalone IIFE builds, createChart/addSeries APIs and Candlestick/Histogram/Line families. Therefore a pinned standalone or ESM dependency can fit plain JS without React migration. The renderer is not a market-data source. Prefer locally packaged pinned assets to a floating runtime CDN.

Sources for parent to open before citing:
- https://tradingview.github.io/lightweight-charts/docs (retrieved ref turn4view0; current v5.2; lines 28–48 client-side/ES2020/IIFE; 52–57 attribution notice + TradingView link; 77–85 series families; 119–135 candles)
- https://github.com/tradingview/lightweight-charts (retrieved ref turn4view1 / search turn2search6; official project)
- https://www.tradingview.com/lightweight-charts/ (search turn2search11; official Apache 2.0 statement)

Follow the pinned distribution's LICENSE/NOTICE and required creator attribution/link in the page. This is Lightweight Charts, not the separate proprietary Advanced Charts product. No need to use a generated image for exact market chart values.

## Tests and acceptance before operational completion

1. Pure schema checks: malformed OHLC/time, duplicate/out-of-order times, inconsistent identity/basis/currency, optional-volume absence and record metadata propagation. Do not silently sort away conflicting duplicates or fill gaps with fabricated candles.
2. Fixture exactness: renderer input equals validated DTO values; immutable source/evidence; available_at > selected cutoff cannot reach a PIT-mode payload. If source lacks availability metadata, explicit NOT_PIT_VERIFIED/BLOCKED mode, not guessed dates.
3. Deterministic integration: source/provider fixture -> adapter -> DTO -> page. No provider network dependency needed for fixture acceptance, but fixture PASS must remain distinct from real ingestion PASS.
4. Browser: nonempty candles/volume, exact crosshair label on known bar, interval/range semantics, pan/zoom/reset, mobile resize/no overflow, loading/empty/error, status/provenance visibility, no fictitious latest price, no plot after blocked payload, no console errors. Existing 10 web tests do not prove any of these financial-chart properties.
5. Numeric data preservation across range changes and display locale. UI must not recompute OHLC aggregation or split/dividend adjustment.

## Critical dependency and stop boundaries

First close data/adjustment/availability semantics and narrow read model; then fixture adapter/rendering; then browser acceptance; then approved real source ingestion and honest state labels; only then optional assistant/MCP consumption. Operational data licensing/provider/billing decisions and numerical policy are user/owner boundaries, not frontend choices. A missing data source is the actual blocker; substituting MCP does not resolve it.

No application code edited. No new library installed. No fabricated production data or new indicator policy. This file is independent review evidence, not implementation readiness or production approval.
