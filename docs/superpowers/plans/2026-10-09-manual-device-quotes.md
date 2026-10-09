# Manual device quotations and disabled API structure implementation plan

> **For agentic workers:** Execute the explicit user design with TDD and a final fresh-context independent review. Root integrates; isolated agents own disjoint core/UI files.

**Goal:** Keep holdings, current prices, FX and timestamps on the device while displaying native values and complete KRW valuation; API stays off until a separate provider decision.

**Architecture:** Preserve holdings schema1 and store versioned market metadata separately in the same IndexedDB transaction. Backup schema2 combines strictly validated holdings and market data; API credentials remain in an independent record omitted from every export. No quote collection, polling, server or provider URL is introduced.

**Tech stack:** Existing vanilla JS/IndexedDB and Python build/privacy tooling; Node and Playwright verification.

**Spec:** User originals and Source confirmation in Global CDR048–050 at1a18ba697dc2798711ca6eac101d5fb24202dfc7, evidence/manual_quotes_decision_2026-10-09/. The direct detailed instruction authorizes implementation now; additional skill design-approval menus do not override that authorization. Normal merge authorization names PR69; the later feature PR is separately reviewable.

## Global constraints

- AUTONOMY_MODE READ_ONLY; Frozen, TARGET, scoring, Holdout and deferred automation unchanged.
- A-S2 nineteen reviewed references: US17, TSE8035, KRX042700; KRW display base.
- Quotes and FX use positive decimal strings and real supplied clocks, no invented fallback or average-cost substitution.
- Price age >=7days is STALE; status does not disguise the original timestamp.
- FX units are KRW per1USD and per1JPY; quote/native denomination comes from the reviewed listing.
- Service unselected, API off, no auto refresh; only structural key storage/delete/disabled refresh.
- CSP script-src/connect-src self only until a reviewed provider is selected; no external scripts or new server.
- Never commit/export/log real keys or user data. Synthetic browser payloads stay memory-only; screenshots use empty storage.
- Preserve legacy import; validate everything before atomic writes and preserve originals on failure/conflict.

## Review focus

- Missing one price/FX cannot normalize a partial portfolio into apparently complete weights.
- Corrupt local records or cross-tab races cannot overwrite holdings/market state silently.
- Import, backup and settings must never disclose or replace credential records.
- Future/bad clocks, exactly7days, large values and average-cost currency mismatch require honest native/FX labels.
- Source selection and API refresh remain off after save/unlock/render/refresh/locale changes; public requests contain no holdings or key.

### Task1: market data and backup core (manual_market_core)

Files: create web_assets/device-market.js and tools/device_market_node_test.js.
Interfaces: DeviceMarket.validateMarket(market,catalog,{now,minimumVersion}); makeMarket(catalog,quotes,fx,previous,now); emptyMarket(catalog,now); valuation(snapshot,catalog,market,{now}); exportBackup(snapshot,market,catalog,{now}); importBackup(payload,catalog,{now})=>{snapshot:legacy1,market}; staleness(asOf,now).

- [x] Write34 meaningful cases and observe missing-module RED.
- [x] Implement strict metadata/identity/decimal/time validation, supplied KRW conversion, complete-denominator weighting and safe schema2/legacy backup.
- [x] Run Node tests; inspect finite/overflow, stale, missing data and key exclusion cases.

### Task2: atomic ACTUAL/market and key settings UI (manual_quotes_ui)

Files: modify web_assets/device-actual.js/css; create tools/manual_quotes_browser_test.js.
Interfaces: existing DeviceActual.mount/summary; new DeviceActual.settings(host,{catalog,locale}); Task1 interfaces above. Keys actual/market/api-settings share database but credentials are excluded from market and backup. Root loads market module before ACTUAL and mounts settings host.

- [x] Write browser behavior assertions and observe missing manual-price RED.
- [x] Add editable price/time and FX/time, provenance/stale/native/KRW/%p display, atomic optimistic writes/import/delete, password key storage and separate deletion, disabled refresh.
- [x] Run390/1280ko/en119checks mixed-currency/save/reload/export/delete/import, missing/stale/invalid/conflict/key privacy tests; capture four empty screenshots.

### Task3: integration and public artifact boundary (root)

Files: app.js,index.html; build/privacy tests and guard pins; workflow test steps; owner docs.

- [x] Add failing public-build test for the market module plus rejection of market/FX/credential input.
- [x] Load self-hosted market module before ACTUAL, mount settings host and extend private-input recognition.
- [x] Review12generated web files and update only changed approved hashes; preserve canonical public JSON/source.
- [ ] Run full Python, old/new Node/browser flows, directory/raw-tar guard and repository guard.

### Task4: deployed baseline and provider comparison

- [x] Append exact user decision/Source confirmation/amendment; recheck PR69 head29bd CI2SUCCESS and fresh-review PASS.
- [x] Normal PR merge d71243bcc79139149541f3627e8f227a32c463c5 with identical tree3eecea810778f2d78daa51dce29a8bdfe543e02c; no force push.
- [x] Verify actual push deployment run37869779655; public URL390/1280ko/en ACTUAL flow and empty screenshots.
- [x] Official provider options include KIS and FSC public stock data: coverage, free limits/delay, auth/secret/token/CORS and personal terms; free user-only relay architecture if needed. No API or broker connection implementation.

### Task5: final independent review and feature PR

- [ ] Fresh strongest-capable reviewer uses exact final tree, new full tests and adversarial privacy/CSP/storage checks; do not reuse author results.
- [ ] Publish new canonical-target PR via GitHub connector, no force push; wait for applicable CI.
- [ ] Append execution receipts and request only outstanding concrete provider/feature-merge decisions. Report actual publication separately from an unmerged feature.
