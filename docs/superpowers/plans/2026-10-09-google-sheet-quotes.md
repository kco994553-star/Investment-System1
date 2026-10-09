# Google Sheet quotations implementation plan

> **For agentic workers:** Execute the user's explicit design with parallel disjoint core, UI and privacy/documentation tasks; root owns storage/integration and final verification. No additional design permission is required: the user supplied the design and instructed execution. PR merge remains pending user approval.

**Goal:** Optionally import private GOOGLEFINANCE observations directly from the user's browser, or from pasted A–C columns, while preserving manual input.

**Architecture:** Pure fixed-map parsing feeds the existing versioned device market store. Google Identity Services uses only the Sheets read-only scope and memory tokens. Separate device settings and batch history never enter public builds; settings and tokens never enter backups.

**Tech Stack:** Existing vanilla JS, IndexedDB, Python guards/build, Node and Playwright.

**Spec:** User's 2026-10-09 “구글 시트(GOOGLEFINANCE) 시세 불러오기 + 일괄 붙여넣기” instruction; scoped decision register at `implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md`.

## Global constraints

- Base `claude/investment-system-top500-validation-alrugm` at `011b75648f48f2890736d37c4a354f57004cf1f0`; work branch `codex/google-sheet-quotes-20261009`; one PR; no merge.
- Preserve READ_ONLY, TARGET, methodology and manual input. Alpha Vantage OFF; KIS/relay DEFERRED.
- Default OFF. No background reads, server, relay or Actions collection. All Google calls require user actions; CI mocks all Google endpoints.
- Only scope `https://www.googleapis.com/auth/spreadsheets.readonly`. Public client ID supplied by user; no client secret. Tokens only in memory; revoke clears memory immediately.
- Settings ID/range stay on device and out of backups. Fixed 19-stock/two-FX mapping only; failure never replaces saved values.
- Exchange-local clocks must be unambiguous. Unknown clocks use retrieval time with explicit unknown label. Existing seven-day rule remains.
- New source label `GOOGLEFINANCE · 최대 20분 지연 · 정보용`. FX missing time explicitly marked unknown; TYO:8035 remains manual on #N/A.
- Public source/JSON/Pages contain no user observations, spreadsheet IDs or tokens; tests construct synthetic inputs in memory and capture only empty screenshots.

## Review focus

- DST gaps/ambiguous hours, malformed/future clocks and duplicate symbols cannot fabricate known timestamps or replace valid data.
- Disable/revoke/expiry during outstanding sign-in/fetch cannot reintroduce tokens or commit stale responses.
- Cross-tab storage conflict/corruption must fail without erasing existing holdings, prices or history.
- Locale/route/reload changes must preserve privacy settings and keep sign-in explicitly initiated.
- Empty client ID hides Google buttons while paste remains usable without login.

### Task 1: Core parsing and market provenance (core agent)

Files: `device-market.js`, new `google-sheet-core.js`, `tools/google_sheet_core_node_test.js`.
Interfaces: `parseValues(values,catalog,{now})`, `parsePaste(text,catalog,{now})` → validated quotes/FX, success/failure names and safe warnings; `apply(catalog,previous,result,now)` → next market preserving failures. Optional `time_status` on GOOGLEFINANCE observations forwards into valuation.

- [x] Write and observe failing tests for 21 rows, #N/A, unknown/duplicate codes, bad values, exchange clocks and paste.
- [x] Implement fixed mapping and strict validation; preserve backward-compatible manual records.
- [x] Run old market and new core Node suites.

### Task 2: Login and browser UI (UI agent)

Files: new `google-sheet-quotes.js/css`, `tools/google_sheet_auth_node_test.js`, `tools/google_sheet_quotes_browser_test.js`.
Interfaces: `mount(host,{catalog,locale,clientId})`; root provides `DeviceActual.sheetSettings`, `applyMarketImport` and `readMarketImportHistory`.

- [x] Observe auth/unit/browser failures before implementation.
- [x] Add explicit OFF switch, local configuration, gesture-safe GIS token sign-in, fetch/revoke/expiry and login-free paste.
- [x] Verify all four width/locale combinations with mocked Google routes, cancellation and backup/privacy checks.

### Task 3: Device persistence and integration (root)

Files: `device-actual.js`, app/config/index assets, storage browser test, public-build tests/pins and cockpit workflow.
Interfaces: `sheetSettings(view,value?)`; `applyMarketImport(view,catalog,result,{now,method})`; `readMarketImportHistory(view,catalog)` returns summaries. Atomic CAS writes append one batch entry containing only validated observations and safe names; failed rows retain previous market records. Credentials/settings are excluded from backup construction.

- [x] Observe missing-helper storage/browser and public-build tests fail.
- [x] Implement strict settings and history, atomic market import and bilingual provenance.
- [x] Load/mount new assets; add only requested CSP hosts/path. Review public assets before repinning; public JSON hashes remain unchanged.
- [x] Run full Python and existing/new Node/browser suites, directory/raw-tar guards.

### Task 4: Privacy guard and owner docs (security/docs agent)

Files: privacy guard/tests, setup and scoped append-only decision register.

- [x] Observe dynamically constructed spreadsheet URL/ID and token cases fail, then extend guard without leaking diagnostics.
- [x] Document Google Cloud setup, formula-only 21-row example and confirmed limitations.
- [x] Record user decision and merge boundary; no mutation of separate global shared branch.

### Task 5: Independent review and PR (root/reviewer)

- [x] Fresh independent review of final implementation and privacy boundaries; resolve material findings and verify fixes.
- [ ] Commit/push only work branch, create one canonical-target PR and check all triggered CI.
- [ ] Report PR, file summary, test results, setup order and remaining live-Google risks in Korean; no merge/deploy.
