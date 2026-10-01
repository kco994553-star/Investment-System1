# Investment-System1 · REAL Producer Readiness Audit — 2026-10-01

Status: **PREFLIGHT AUDIT / NO IMPLEMENTATION**. Scoped report + evidence only.
Machine evidence: `producer_readiness_audit_2026-10-01.json`. Contract probe: `producer_readiness_probe_2026-10-01.py`.

No new investment calculation, no paid API, no secret, no deployment, no canonical/PR merge.
Track C results are not assumed. No Investor-QGV profile was created.

## 0. GitHub SSoT pinned for this audit

| Ref | SHA | State |
|---|---|---|
| Canonical `claude/investment-system-top500-validation-alrugm` | `b8e39a2` | Track A FROZEN_VERIFIED integrated |
| PR #5 `feature/web-mvp-v1` | `a4e49c8` | OPEN/DRAFT |
| PR #6 `feature/global-language-search-v1` (stacked on #5) | `eda65bf` | OPEN/DRAFT; sequential merge gate PASS (`integration/web-mvp-language-search@e09d24e`) |
| PR #4 `feature/track-c-evl` | `9cf4d7d` | OPEN/DRAFT; C6 software frozen; C7 policy NOT APPROVED |

Regression re-run in this session (local container, no network):

| Target | Result |
|---|---|
| Canonical `b8e39a2` (`tools/mini_pytest.py`) | 396 passed / 0 failed |
| PR #6 head `eda65bf` (`tools/mini_pytest.py`) | 409 passed / 0 failed |
| PR #4 head `9cf4d7d` (real `pytest`, scratch venv) | 629 passed. The `mini_pytest` shim has 9 import-level failures (`pytest.mark`); that is a limitation of the runner, not a test failure |

## 1. Producer dependency graph (current, actual)

```
 SEC EDGAR (companyfacts/submissions/N-PORT/filings)  Yahoo chart  Stooq  [Tiingo*]   FRED csv / [ALFRED*]
          \__________________ tools/fetch_*.py  (c21-real-data.yml, manual dispatch) __/          |
                                 |                                                               |
                     RawDatasetStore (sha/available_at)                       providers/fred_csv.py (no key)
                     blobs ONLY in Actions artifact (expires 2026-12-26)                         |
                                 |                                                               |
             run_top500_gate_chain.py  ── manual CA/D3-C review                                   |
                                 |                                                               |
            UNIVERSE (Track A)  Official 2024-06-30 / 09-30 / 12-31 FROZEN_VERIFIED               |
                                 |                                                               |
            official_pipeline.py -> vertical_slice -> historical.run_as_of (real Q/G/V)          |
                 |  per-company Q/G/V NOT persisted; only aggregates (PROVISIONAL_RESEARCH rule) |
                 |                                                                               |
   QGV ──X── Technical  (engine = v0.6 STRUCTURAL placeholder, adapter synthetic=True)           |
   QGV ──X── Macro      (engine threshold rule; adapter synthetic=True) <─── X ─────────────────┘
   QGV ──X── Leaderboard (LeaderboardEngine exists; never run on real data; no persisted output)
   QGV ──X── Portfolio  (Official v1.1 engine on SYNTHETIC fixture book; Track B P0 contracts only)
   Track C EVL ──X── (no validated outputs; C7 not approved; Holdout unconsumed)
   News/RIG    ──X── (P0–P4 model/UI on fixtures; NO news source/ingestion; P5 blocked on Track C)
                                 |
   Web MVP (PR5+6): schema-1 bundle  <── only Universe is connected (FROZEN_SNAPSHOT 2024-12-31)
                                          every other section = NOT_AVAILABLE
   X = no real producer→consumer connection exists in GitHub today
   * = optional free-registration key; not required by the frozen baseline
```

## 2. Module audit table

| Module | Current producer | Data source | PIT contract | Update cadence | Output schema | Freshness | Provenance | Secrets/API | Consumer | Actually connected? | Blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|
| REAL DATA ingestion | `tools/fetch_real_data.py`, `fetch_nport_reference.py`, `fetch_cover_xbrl.py`, `fetch_tiingo/stooq_prices.py`, etc. via `c21-real-data.yml` | SEC EDGAR (free, UA required); Yahoo chart (free, **unofficial**, no key); Stooq (free); Tiingo (optional fallback); FRED csv (no key) | `RawDatasetStore`: SHA/size and fetch-time `available_at`; offline replay; history kept on refresh | **manual `workflow_dispatch` only**; no `schedule:` | blobs + `manifests/` + `STORE_INDEX.json` | Vintage frozen at 2026-09-27 for as_of ≤ 2024-12-31 | Strong (6830 raw hashes verified) | `SEC_USER_AGENT` (required); `TIINGO_API_KEY` (optional) | Gate chain, vertical slice | YES, for the historical baseline only | No schedule. 0 blobs in git; only artifact `c21-raw-store-36305927245` (451 MB) holds them, and it **expires 2026-12-26** |
| Universe (Track A) | `run_top500_gate_chain.py` → `official_mcap500_snapshot` | PIT shares × PIT price; N-PORT IWB reference; reviewed CA evidence | FROZEN_VERIFIED reconstruction contract (CA-UNIT-v1.0, dated identities) | Per as_of, needs an N-PORT fund-quarter date and gate/CA review → **quarterly at best** | `official_snapshot_<as_of>.json` (members, rank, rank_is_lower_bound) | Latest = **2024-12-31** (~21 months old) | Strong, hash-checked in `repository_bundle()` | SEC UA | Web `universe`, vertical slice | YES (Web reads frozen 2024-12-31 file, FROZEN_SNAPSHOT) | No as_of after 2024-12-31. Each new date may raise new CA/D3-C cases. The Web path is hard-coded to the `2024-12-31` file, and the Companies view has a hard-coded label `FROZEN_SNAPSHOT / DEMO` |
| QGV | `validation/historical.run_as_of` inside `vertical_slice` / `official_pipeline.py` | Real SEC companyfacts + Yahoo bars from the store | as_of filing availability (SEC vintage), Track A boundary | Ad-hoc per run | In-run `quality{Q,G,V}`; persisted JSON has **aggregates only** (`n_selected`, `equal_weight_realized`) | 2024 dates only | `rule_status=PROVISIONAL_RESEARCH`, `official_selection=false` | none beyond SEC UA | Leaderboard, Portfolio, Web `qgv` | **NO** (Web `qgv` = NOT_AVAILABLE) | No persisted per-company `QGVSnapshot` export. No current-date run. Official profile/selection belongs to Track C (not validated) |
| Technical | `technical/engine.py` (`TechnicalEngine`) | Return list from caller | None on canonical. PR #4 adds `evaluate_stamped` lineage (unmerged) | n/a | `TechnicalSnapshot` (regime, execution_zone, invalidation, scenarios) | n/a | `technical_version=v0.6-STRUCTURAL-FREEZE`, `invalidation="…placeholder…"`, scenarios `structural-placeholder` | none | Web `technical`, Leaderboard scenario | **NO** | **No real Technical model.** The adapter emits `synthetic=True`, so `validate_bundle` rejects it as LIVE (probe) |
| Macro | `macro/engine.py` (`MacroEngine` confirmed v0.1.1 contract) + `providers/fred_csv.collect_indicators` | FRED csv (free, keyless); ALFRED vintage (optional free key) | ALFRED vintage adapter exists. PR #4 adds `evaluate_stamped` (unmerged) | n/a | `MacroSnapshot` (state, regime, environment.indicators) | n/a | Adapter `synthetic=True`; v0.1.4 Candidate not promoted | `FRED_API_KEY` optional | Web `macro` | **NO** | Adapter output is always synthetic (rejected as LIVE). The Web reads `data.indicators` and `data.exposures[company_id]`, but MacroSnapshot has `environment.indicators` and no exposures at all. No company exposure producer exists |
| Track C validated outputs | `evl/*` (C0–C6) on PR #4 | Synthetic deterministic fixture families only | EVL_SPEC_v0.1 PIT / Holdout isolation | n/a | Registrations/ledgers/reports (Actions artifacts) | n/a | Strong lineage | none | Official profiles → Portfolio/Leaderboard; RIG P5; Investor-QGV | **NO** | TC-D3P-006 (C7 selection) is NOT APPROVED. C8–C10 have not started. REAL_PIT_RESEARCH_VALIDATION has not run. Holdout is unconsumed. **No validated output exists, so none may be shown as production** |
| Investor-QGV | — | — | — | — | — | — | — | — | Web search (INVESTOR type) | NO | FUTURE_TRACK_C_INPUT. No code or profile exists, and none was created |
| Portfolio | `qgv/portfolio.PortfolioEngine` (Official v1.1 targets); `vertical_slice.to_portfolio` (equal weight); Track B `personal/*` P0 contracts and `BrokerPort` protocol | Synthetic fixture book; provisional selection; no holdings source | Track B `timecontract`/`pit_quality` contracts (P0) | n/a | `PortfolioSnapshot` / `PortfolioInput` (target weights) | n/a | `synthetic` / `role` flags | Broker credentials would be needed for any live sync (none exist) | Web `portfolio` (holdings, actual_weight, return, market_value, currency, exposure) | **NO** (DEMO only) | No actual holdings producer (Track B P1+ NOT STARTED). The Official model portfolio needs Track C profiles. The Web fields `return`/`market_value`/`exposure` have no producer |
| Leaderboard | `qgv/leaderboard.LeaderboardEngine` (sort by total_score, no rescore) | QGVSnapshot list | Inherits QGV | n/a | `LeaderboardRow` (rank, ticker, Q/G/V, total, freshness) | n/a | `recomputed_qgv` flag | none | Web `leaderboard` | **NO** | Upstream QGV export is missing. The Web row fields `market_cap_rank`, `daily_move`, `consensus`, `scenario`, `reevaluation_trigger` are **not in `LeaderboardRow`** (probe). Consensus has **no data source**: free sources are unknown and typical vendors are paid |
| News / RIG | `rig/*` P0–P4 (model, intel, network, myview, discovery) | **None.** Test fixtures only (`tests/rig_fixtures.py`) | `available_at` gate; DataEvent NEWS is evidence-only | n/a | Web `news[]` (headline, issuer_ids, available_at, status, source_language), `relationships` = rendered RIG HTML | n/a | Claim/Evidence trace (design) | Unknown. No source chosen; SEC 8-K via EDGAR is a free candidate, **not decided** | Web `news`, `relationships` | **NO** | No news ingestion or NewsItem→Claim→Event extractor. 0/500 Web companies carry `issuer_id`, so news cannot link to companies. P5 is blocked on Track C |
| Prompt Library (Track E) | static Frozen catalog | — | — | static | 70 prompts | n/a | Frozen | none | Web Research | YES | none (no producer dependency) |
| Web MVP | `product/web_mvp.py` static build (`--input` bundle schema 1) | Producer bundle | Display only; `LIVE` requires tz `as_of` + `expires_at`; synthetic rejected unless DEMO | external operator build (no scheduler) | `data.json`, `entities.json`, html/js | UI shows STALE when `expires_at` ≤ now | Original values preserved; evidence panel | none | user (phone) | Universe only | PR #5/#6 unmerged. No exporter writes schema-1. No scheduler. No private hosting |

## 3. Web MVP: FROZEN_SNAPSHOT/DEMO → Daily producer interface

The only entry point is `python -m investment_system.product.web_mvp --out DIR --input bundle.json [--rig-page reviewed.html]`.
Each section uses the envelope `{state ∈ LIVE|FROZEN_SNAPSHOT|DEMO|NOT_AVAILABLE, as_of, source, expires_at (LIVE), data}`.

| Section | Required `data` shape (consumer = `app.js`) | Existing upstream type | Gap |
|---|---|---|---|
| `companies[]` | `company_id`, `ticker`, `name`, `market_cap_rank`, `rank_is_lower_bound`, **`issuer_id`** | Official snapshot members | `issuer_id` mapping is missing (needed for News) |
| `universe` | Official snapshot JSON | `official_snapshot_<as_of>.json` | `repository_bundle()` is pinned to 2024-12-31. A current Official as_of does not exist |
| `qgv` | `{company_id: {Q_score,G_score,V_score,total_score,confidence,coverage_state,…}}` | `QGVSnapshot` (all fields present) | **No exporter or persisted snapshot.** The research-vs-Official status has to travel as a data field: schema 1 has no PROVISIONAL state, so marking it needs a decision |
| `technical` | `{company_id: {regime, execution_zone, invalidation}}` | `TechnicalSnapshot` | Fields match, but the producer is a placeholder and `synthetic=True` |
| `macro` | `{state, regime, indicators{}, exposures{company_id}}` | `MacroSnapshot` | `indicators` is nested under `environment`. `exposures` has no producer. The adapter sets `synthetic=True` |
| `portfolio` | `{role, holdings[{company_id,ticker,actual_weight|target_weight,return}], return, market_value, currency, exposure}` | `PortfolioSnapshot` (target weights only) | No actual holdings, valuation, returns or exposure |
| `leaderboard` | `{rows[{rank,company_id,ticker,market_cap_rank,total_score,daily_move,consensus,scenario,reevaluation_trigger}]}` | `LeaderboardRow` | 5 fields missing; consensus has no source |
| `news` | `[{event_id, headline, issuer_ids[], available_at, status, source_language, summary?}]` | RIG cards (fixture) | No source or ingestion |
| `relationships` | trusted rendered Track D HTML (`--rig-page`) | `rig.network.render` | No operating graph |
| `changes` | `{summary, summary_localized?}` | none | **No producer is defined anywhere** |

Contract probe results (`producer_readiness_probe_2026-10-01.py`, run on PR #6 head):
- Default bundle: universe FROZEN_SNAPSHOT 2024-12-31; all 8 other sections NOT_AVAILABLE; 500 companies; 0 with `issuer_id`.
- Existing Technical and Macro adapter output submitted as LIVE → **REJECTED** (`synthetic data must be DEMO`). This is correct fail-closed behaviour.
- LIVE without `expires_at` → rejected with a raw `KeyError`: it fails closed, but not with a clean `ValueError`.
- LIVE already expired at build time → accepted, and the UI marks it STALE (by design). There is no build-time `expires_at > as_of` check.
- No module named `export*`, `daily*`, `producer*` or `bundle*` exists. **There is no producer→bundle exporter.**

## 4. Readiness levels (definitions and verdicts)

- **UI_INTEGRATION_READY**: the Web can render the section from schema-1 with real metadata. The shape is defined and tested.
- **REAL_PRODUCER_READY**: a non-synthetic, PIT-stamped producer writes per-entity output from real data in GitHub.
- **DAILY_OPERATION_READY**: a scheduled, unattended, current-as_of run produces fresh LIVE data with expiry and lineage, and failures fail closed.
- **PRIVATE_DEPLOYMENT_READY**: an access-controlled private host and phone access are decided and provisioned.

| Module | UI_INTEGRATION | REAL_PRODUCER | DAILY_OPERATION | PRIVATE_DEPLOYMENT |
|---|---|---|---|---|
| REAL DATA ingestion | n/a | YES (historical) | NO | n/a |
| Universe | YES | YES (historical, quarterly) | NO | NO |
| QGV | YES | PARTIAL (real but research, not persisted) | NO | NO |
| Technical | YES (shape) | **NO** (placeholder) | NO | NO |
| Macro | PARTIAL (shape mismatch) | PARTIAL (real FRED input, synthetic-flagged output) | NO | NO |
| Track C | n/a | **NO** (no validated output) | NO | n/a |
| Portfolio | PARTIAL | **NO** | NO | NO |
| Leaderboard | PARTIAL | **NO** | NO | NO |
| News/RIG | PARTIAL (needs `issuer_id`) | **NO** | NO | NO |
| Web MVP | YES (PR5+6 unmerged) | n/a | NO | **NO** |

**System verdict: UI_INTEGRATION_READY (pending PR5/6 merge) · REAL_PRODUCER_READY = NO · DAILY_OPERATION_READY = NO · PRIVATE_DEPLOYMENT_READY = NO.**

## 5. Missing data/API, free vs paid, secrets

| Dependency | Use | Cost | Secret | Status |
|---|---|---|---|---|
| SEC EDGAR (companyfacts, submissions, N-PORT, filings) | Fundamentals, shares, reference, CA evidence; candidate news (8-K) | Free (fair-access, ≤10 req/s) | `SEC_USER_AGENT` (contact string, required) | In use (required by fetch steps; value not readable here) |
| Yahoo chart | Prices, split events | Free, **unofficial / no SLA / ToS risk** | none (`INVESTMENT_SYSTEM_YAHOO_UA` optional) | In use |
| Stooq | Fallback prices | Free | none | In use (fallback) |
| Tiingo | Fallback prices | Free tier needs registration; paid tiers exist | `TIINGO_API_KEY` (optional) | Optional. The workflow only warns when it is absent. **No new signup made** |
| FRED csv | Macro indicators | Free | none | Code exists; not used for Daily |
| FRED/ALFRED API | Vintage macro (PIT) | Free with registration | `FRED_API_KEY` (optional) | Optional |
| KRX Open API | KR market | Free with registration | `KRX_AUTH_KEY` | KR track DEFERRED (D-16) |
| Consensus estimates | Leaderboard `consensus` | Typically **paid**; no free source identified | — | **MISSING**, must stay NOT_AVAILABLE |
| News feed (headline/text) | RIG | Licensed feeds are typically paid. SEC filings are a free alternative | — | **MISSING, source not decided** |
| Broker / holdings | Actual Portfolio | Broker API (credentials) or manual import | Broker credentials (future, Track B P1+) | **MISSING** |
| Private hosting | Phone access | Free options exist, but none is chosen | Possibly an access secret | **Not decided** |

Secret presence: the workflow references only `SEC_USER_AGENT` and `TIINGO_API_KEY`. Their configured values are not readable from this session and were not touched.

## 6. Update schedule (what is achievable vs. required)

| Feed | Native cadence | PIT lag | Current repo cadence |
|---|---|---|---|
| Prices (Yahoo/Stooq) | Daily after close | T+0 evening | manual |
| SEC companyfacts / 10-Q / 10-K | Event-driven (filing) | Filing `available_at` | manual |
| Official Universe | Quarterly (N-PORT fund quarter end, published ≈60 days later) + CA review | ≈2 months | manual, 3 historical dates |
| FRED macro | Monthly/weekly per series | Release lag | none |
| Web build | Planned 6/12h external operator build (W-D06) | — | none |

How the Universe works between quarterly Official dates (reuse, drift, interim rules) is **policy and not decided**. It needs a D3-P and was not decided in this audit.

## 7. Integration blockers (ranked)

1. **B1 · No producer→Web exporter** for QGV/Leaderboard/Macro/Technical (schema-1 bundle writer is absent).
2. **B2 · No current Official Universe.** The latest is 2024-12-31. New dates require a gate chain run plus possible CA D3-C review.
3. **B3 · Technical has no real model** (v0.6 structural placeholder). The spec for a real implementation is the owner's decision.
4. **B4 · Macro output is always synthetic-flagged.** It also does not match the Web shape, and no exposure producer exists.
5. **B5 · Track C has no validated outputs.** C7 TC-D3P-006 is not approved and C8–C10 have not started. This blocks the Official Portfolio, Official Leaderboard semantics, RIG P5 and Investor-QGV.
6. **B6 · No actual holdings** (Track B P1+ not started).
7. **B7 · No news source or ingestion**, and no `company_id↔issuer_id` mapping.
8. **B8 · No scheduler** (`c21-real-data.yml` is dispatch-only; Web build has no workflow).
9. **B9 · Raw store durability.** The only raw blobs are in an Actions artifact that expires 2026-12-26.
10. **B10 · PR #5/#6/#4 unmerged.** Merging is for the integration owner.
11. **B11 · No private hosting/access decision.**
12. **Minor contract notes:** LIVE without `expires_at` raises `KeyError` rather than `ValueError`. Schema 1 has no PROVISIONAL marker for research-grade QGV. `changes` has no defined producer.

## 8. Critical path to DAILY_OPERATION_READY

Two paths, because Official profile semantics depend on Track C.

**Path A: Daily cockpit with real, clearly labelled non-Official research data.** Shortest path; no Track C assumption.
1. Integration owner normal-merges PR #5 → PR #6 (gate already PASS). → UI_INTEGRATION_READY.
2. Persist the raw store beyond the artifact expiry (B9) and add a scheduled ingestion run. Free sources and the SEC UA only.
3. **[D3-P]** Interim Universe policy between quarterly Official dates. Then produce the latest feasible Official as_of (e.g., 2026-06-30 once N-PORT is public), with CA review as needed (B2).
4. Persist per-company `QGVSnapshot` and write a schema-1 exporter (B1). **[D3-P]** Decide how PROVISIONAL_RESEARCH status is labelled in the bundle.
5. Macro: merge the stamped-lineage path (PR #4 contains it) or an equivalent. **[D3-P]** Decide the real-input `synthetic=False` policy and the Web shape mapping (B4). Exposures stay NOT_AVAILABLE unless an owner defines them.
6. Technical: owner implements the real model per the Technical record (B3), or Technical stays NOT_AVAILABLE.
7. Leaderboard export from step 4 (sorted by QGV, no rescore). Fields without a source stay NOT_AVAILABLE.
8. Scheduled bundle build with `expires_at` and STALE handling (B8).
9. Private hosting decision → PRIVATE_DEPLOYMENT_READY (B11).

The critical path is **steps 2 → 3 → 4 → 8**. Step 3 (the Universe policy decision plus a new Official date with CA review) is the longest and least predictable item.

**Path B: Full Official Daily Operation** = Path A plus:
Track C C7 approval (TC-D3P-006) → C8 gate → C9/C10 → real PIT validation → Official Aggressive/Balanced/Defensive profiles → Official Portfolio/Leaderboard. Then Investor-QGV (FUTURE_TRACK_C_INPUT), RIG P5, Track B P1+ actual holdings, and a news source decision with RIG ingestion and issuer mapping.
Its critical path runs through **Track C**, which is on-going and has no validated output, so no date can be assumed.

## 9. Not done (by instruction)

No paid API signup or use, no secret created or committed, no deployment, no canonical or PR merge, no Track C result assumed, no Investor-QGV profile, and no new investment calculation or policy. Shared SSoT indices (CURRENT_HANDOFF / Master Status) were not rewritten. This report is a scoped integration input.
