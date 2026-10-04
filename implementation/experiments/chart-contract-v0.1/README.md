# Chart Contract Lab v0.1 — isolated DEMO

Source baseline: canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`.
Audit comparison: PR40 `acaf1b5a82859ac2750a130ebe88f8b4d272ac66`.
Coordination read: `bb4cb174fd4a0af3b2281d4c37ae3abb4d540f88`, GCH-014 / CDR-014.

This experiment implements the smallest chart contract/renderer slice after the Chart Implementation Audit. It does not activate a production API, provider account, MCP server, Web route, research display grant, Official/LIVE output or canonical merge. No existing source/test/workflow is changed.

## Selected architecture

API ingestion -> existing RawDatasetStore -> deterministic typed chart payload -> browser/static bundle.
Later, a read-only MCP facade may query that same payload. There is one calculation/source-of-truth path. A separate REST server is not required for P0. The current lab accepts original response bytes offline; raw-store-to-lab production wiring is still pending, not claimed implemented.

Four independent perspectives favored API-first delivery and optional MCP later. Provider and frontend reviewers initially ranked "API-first now" over "hybrid immediately"; PIT and MCP reviewers used "hybrid" to mean the phased design. This is agreement on implementation sequence, not an invented four-way vote for immediate dual servers. MCP-first received no recommendation. The PIT reviewer preferred a weight-comparison first slice; that remains a follow-up alternative. The parent chose the OHLCV slice to close the audited missing O/H/L seam directly, while keeping source access and investment methodology outside this experiment.

## Implemented

- Original-byte SHA-256 check and provider vs delivery-transport lineage.
- Offline Yahoo quote and Alpaca single-symbol bars response mapping; O/H/L/C/V preserved exactly.
- Strict ordering, duplicate/future/invalid-calendar rejection; partial OHLC pair constraints; null distinct from zero.
- Daily interval evidence required. Yahoo basis stays UNVERIFIED_PROVIDER_QUOTE. Alpaca requires explicitly declared 1Day/raw; `asof` never implies data vintage.
- `available_at`, session close/finality and historical source vintage remain unknown. No PIT-ready output can be created.
- Synthetic input -> DEMO. Non-synthetic input -> NOT_AVAILABLE, renderer blocked.
- Lightweight Charts 5.2.1 pinned; candle/volume, exact crosshair values, range selection, empty/blocked states, local NOTICE/LICENSE and pinned Korean font.

Missing volume is whitespace, not zero. Missing OHLC is whitespace, not a candle fabricated from close. The fixture intentionally includes a zero-volume point and a null-volume point. All 12 dates and prices are synthetic, including weekends; not an exchange-session fixture. No adjusted-close substitution, resampling, indicator, scoring, portfolio weight, probability, target or benchmark calculation is introduced.

## Reproduce

```sh
cd implementation/experiments/chart-contract-v0.1
npm ci --ignore-scripts
npm test
npm run build
node node_modules/playwright/cli.js install chromium --only-shell
node browser_test.cjs
```

Open `dist/index.html`. Build output is deliberately ignored by git. Browser tests use Playwright 1.58.2, matching the previously inspected repository browser-validation runtime. The bundle runs without a runtime CDN or provider request. Unit tests use Node's test runner, not missing pytest.

## Integration / boundaries

The code is outside the current runtime package because it is an isolated experiment, not to bypass acceptance. It is not an integration exemption: closed-world Frozen checks may still reject added files. Landing requires owner review and the exact merge-result FPIA route. No Frozen files, historical identities, protected web_mvp.py digest, existing owner branch or publication records are modified. Existing Yahoo provider, RawDatasetStore, producer serialization, and P01 publication remain the intended reuse points; no duplicate network client or scoring engine is built.

## Deferred decisions

- Actual account entitlement/feed, market coverage, historical horizon and licensing. No paid purchase or login performed.
- Official session vintage/availability and corporate-action basis for historical decisions.
- Producer-envelope/Web integration and publication grant, not inferred from this lab.
- Consensus provider/median/revision history, benchmark TR, new indicator method definitions.

## Failure history

1. Initial 21 contract tests passed, but independent adversarial review found interval relabelling, missing identity/provenance acceptance, partial-OHLC envelope bypass and invalid-calendar normalization. All repaired additively; regression cases retained (26 tests).
2. Build first failed because the npm distribution omits NOTICE. Exact v5.2.1 upstream NOTICE was fetched from the official repository and preserved; build now succeeds.
3. Playwright browser downloads (v1234 and pinned-runtime v1208) returned invalid archives. Browser verification instead used Playwright 1.58.2 with npm-distributed @sparticuz/chromium 153.0.0. Its first extraction reported a font chown EINVAL; the extracted binary was then reusable. No permission or access control was changed.
4. Initial browser assertions assumed the renderer retained whitespace records at fixed indexes; corrected the test to lookup timestamps. Range assertions now wait for the renderer update.
5. Browser testing exposed the environment locale en-US@posix as invalid for Intl formatting. The chart now explicitly uses ko-KR. Visual inspection found missing Korean glyphs; pinned local Noto Sans KR 5.3.0 resolves them.
6. Final verification: 26/26 contract tests; 6/6 independent adversarial probes; browser PASS at 360, 390 and 1280 px. These results cover the synthetic demo only. A build invoked from the wrong working directory failed once and succeeded from this package directory.

Optional browser-runtime override, when the standard Playwright download is unavailable:

```sh
CHART_CHROMIUM_MODULE=/absolute/path/to/@sparticuz/chromium/build/index.js node browser_test.cjs
```

That alternate binary is a verification environment dependency, not an application runtime dependency. See ACCEPTANCE.json for the exact tested scope. Full existing Python regression was not run: this additive experiment imports no existing runtime code, and production integration is deferred.

## Primary documentation

- https://docs.alpaca.markets/us/reference/stockbars — feed, adjustment, pagination; asof is symbol mapping.
- https://massive.com/docs/rest/stocks/aggregates/custom-bars — split adjustment and feed/history plan distinctions.
- https://www.massive.com/docs/rest/partners/benzinga/consensus-ratings — separate consensus product, not historical-vintage proof.
- https://modelcontextprotocol.io/specification/2026-07-28/server/tools — typed structured tool output.
- https://github.com/alphavantage/alpha_vantage_mcp — MCP exposes underlying API functions, not extra entitlement/PIT guarantees.
- https://tradingview.github.io/lightweight-charts/docs — renderer/build variants; library is not a data source.

Provider facts above are documentation checks, not successful authenticated provider calls. No pricing decision is made.
