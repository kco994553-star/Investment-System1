# Frontend Information Architecture · 2026-09-23

Status: DESIGN PROVISIONAL overlay. Does not change Frozen Contracts, scoring, Integration policy, or C-15.
Implementation line: investment_system_impl-v0.2.0
Authority read: CURRENT_HANDOFF 1158, PRODUCT_ARCHITECTURE.md, QGV Module Map v1.7, Technical Consolidated v0.1, Macro Latest v0.1.4 Candidate (confirmed engine still v0.1.1), Architecture v1.0, web/app/* prototype (17 pages).

## 1. Current UI vs Target IA

| Area | Current prototype | Target IA | Action |
|---|---|---|---|
| Top nav | Home + QGV 5 links + Technical 6 pages + Macro 3 pages + Integrated + Strategy Lab | Home / QGV System / Technical Analysis / Macro / Strategy·Settings | Collapse Technical+Macro page links |
| QGV | 5 separate pages, no hub | QGV Hub cards → 5 module pages | Add hub; keep 5 pages |
| Technical | 6 separate pages (search/chart/signal/state/scenario/execution) | One Technical Workspace with sections | Merge routes; keep backend modules separate |
| Macro | dashboard + pillars + regime | One Macro Dashboard | Merge routes |
| Home | 4 static cards, not an Integration dashboard | Integration Decision Dashboard | Re-purpose Home |
| Security context | mentioned in PRODUCT_ARCHITECTURE, not wired in HTML | Persist company_id/ticker/as_of | Add context bar only |
| Evidence class | badges on pages | every number labeled SYNTHETIC / LIVE_FETCH / PARTIAL / VERIFIED | Keep honesty |

Reuse: serif theme, sidebar brand, badge language, QGV 5 URLs, Strategy Lab page.
Change: Technical 6 files → 1 workspace; Macro 3 files → 1 dashboard; Home content; add QGV hub; mobile stack.

Do not add Provider/SEC/PIT/Raw Map to user nav.

## 2. Target navigation

```
Investment System
├─ Home / Integration Dashboard
├─ QGV System                         ← hub only
│   ├─ Analysis
│   ├─ Simulation
│   ├─ Portfolio
│   ├─ Leaderboard
│   └─ Track Record
├─ Technical Analysis                 ← single workspace
├─ Macro                              ← single dashboard
└─ Strategy / Settings                ← profile + lab (not a 6th engine)
```

Backend modules stay split. Frontend pages do not 1:1 map to engines except QGV's five user purposes.

## 3. Screen map

| Screen ID | Route (target) | User job | Backend consumed |
|---|---|---|---|
| IS-HOME | / | Read integration decision | IntegrationResult, Portfolio, three snapshots |
| QGV-HUB | /qgv | Pick a QGV purpose | none (nav) |
| QGV-AN | /qgv/analysis | Score one company | AnalysisEngine, SecurityContext |
| QGV-SIM | /qgv/simulation | Product simulation (≠ backtest) | SimulationEngine |
| QGV-PF | /qgv/portfolio | Official/US working book | PortfolioEngine |
| QGV-LB | /qgv/leaderboard | Universe ranking | Leaderboard |
| QGV-TR | /qgv/track | QGV predictions vs outcomes | TrackRecordStore scope=QGV |
| TA-WS | /technical | One-name technical flow | TechnicalEngine + price provider |
| MAC-DB | /macro | Market regime dashboard | MacroEngine v0.1.1 |
| ST-LAB | /settings | Profile hash, frozen vs configurable | StrategyProfile |

Retired as top-level routes: technical/search, chart, signal, state, scenario, execution; macro/pillars, regime.

## 4. Common Security Context

Fields: company_id, ticker, yahoo, exchange, as_of, profile_id, parameter_set_hash.
Rules:
- Set on QGV Analysis search or Leaderboard row click or Technical header search.
- QGV ↔ Technical carries the same context. Do not force re-search.
- Macro stays market-level. Optional transmission panel may *read* context; it does not become a company workspace.
- security_id remains undefined (C-06). UI shows company_id + ticker only.
- TEL ticker stays AMBIGUOUS (C-08). No US symbol invented.

## 5. QGV Hub → Module pages

```
┌ QGV System ──────────────────────────────────────┐
│  context: NVDA · 2026-09-14 · Balanced           │
│  ┌ Analysis ┐ ┌ Simulation ┐ ┌ Portfolio ┐      │
│  ┌ Leaderboard ┐ ┌ Track Record ┐                │
└──────────────────────────────────────────────────┘
```

Do not merge the five into one dashboard. Each module page: Summary → Evidence → Detail drawer.
Analysis page shows Q/G, V=null + VALIDATION_SELECTED, coverage PARTIAL/BLOCKED honestly.
Simulation labeled PRODUCT_SIMULATION, not VALIDATION_BACKTEST.

## 6. Technical Single Workspace

Backend still separate: Market Data / Indicator / Signal / State / Regime / Scenario / Probability / Execution / Track Record / (Fusion C-15 isolated).

Desktop layout:

```
┌ sticky: Name  Ticker  Px  as_of  freshness  Profile  range ┐
│                                                           │
│  [======= Price Chart + State chip =======]  55% height   │
│                                                           │
│  Indicator cards (Trend Momentum Volume RS Structure Vol) │
│           summary → expand drawer                         │
│  Regime  |  Scenarios S=1..N                              │
│  Probability / Confidence   (unverified ≠ VERIFIED)       │
│  Execution zone  (NOT system order)                       │
│  Technical Track Record                                   │
└───────────────────────────────────────────────────────────┘
```

Mobile: same order vertical. Chart first. Cards collapse. Bottom tabs: Chart · State · Execute · Record.

Fusion (C-15): no UI control that implies an official fusion score.

## 7. Macro Single Dashboard

Confirmed engine v0.1.1. v0.1.4 Candidate not default.

```
┌ sticky: as_of  freshness  macro v0.1.1  Profile  Regime  conf ┐
│  1 Current Regime (large)                                      │
│  2 Indicator grid: Growth Inflation Rates Liquidity Risk       │
│  3 Signal → Evidence                                           │
│  4 VMR panel labeled OWNERSHIP UNCONFIRMED                     │
│  5 Scenarios                                                   │
│  6 Transmission Market→Sector→Name (reads SecurityContext)     │
│  7 Macro Track Record                                          │
│  If FRED missing: Regime = UNAVAILABLE, no synthetic fill      │
└────────────────────────────────────────────────────────────────┘
```

## 8. Home = Integration Dashboard

```
Portfolio summary
QGV snapshot card  → /qgv
Technical snapshot → /technical
Macro snapshot     → /macro
Risk
        ↓
Integration gate + reasons + profile hash
        ↓
Target weights / execution state   (only source)
        ↓
Integrated Track Record
```

No module-level Buy/Sell button on Home.

## 9. Responsive rules

| Breakpoint | Nav | Content |
|---|---|---|
| ≥960px | left rail | multi-column where density helps (Home cards, Macro grid) |
| <960px | top sticky + hamburger or bottom quick nav | single column, importance order |
| Chart | min 280px height on mobile | never shrink 6 technical pages side by side |

## 10. Component hierarchy (shared)

- AppShell (nav + context bar + evidence badges)
- SecurityContextBar
- SnapshotCard (links to workspace)
- EvidenceDrawer (Summary / Evidence / Detail)
- TrackRecordList (parent immutable, child outcome)
- ProfileChip (id + hash, frozen keys locked)

## 11. Migration plan (do not execute in this session)

1. Keep current 17 HTML files until Validation work needs no frontend.
2. Add qgv/index.html hub only when UI work resumes.
3. Redirect technical/*.html → technical/workspace.html#section
4. Redirect macro/pillars.html and regime.html → macro/dashboard.html#section
5. Replace Home copy with Integration layout using existing JSON reports, still labeled SYNTHETIC/LIVE_FETCH.
6. Wire context in query string `?company_id=nvda&as_of=2026-09-14` before any SPA.

## 12. Frontend implementation priority (after Validation)

P0 Validation/PIT/factor coverage — not UI.
P1 Context bar + evidence badges on existing pages (low risk).
P2 Home as Integration dashboard using already persisted envelopes.
P3 Technical workspace collapse.
P4 Macro dashboard collapse.
P5 QGV hub page.
P6 Visual polish / brokerage chart — last. No official indicator list yet.

## 13. What this design does not decide

- C-03 Q7 label
- C-15 Fusion formula
- V production
- Official probability calibration
- VMR ownership
- security_id schema
- Macro v0.1.4 promotion

## 14. Progress tables (conservative maturity)

Scoring key: Design / Implementation / Synthetic / Integration / Real-data / PIT / OOS / Calibration / Forward.
Percent ≈ filled stages / 9, rounded down. Frontend presence does not raise Real-data or PIT.

### 14.1 Investment System overall

| Stage | Status |
|---|---|
| Design | Architecture v1.0 + this IA PROVISIONAL |
| Implementation | NEW IMPLEMENTATION present |
| Synthetic | pytest 64 |
| Integration E2E | 17-name synthetic + 3-name PIT candidate |
| Real-data verified | 0 |
| Full PIT | candidate only |
| OOS / Calibration / Forward | not run |
| **Overall (conservative)** | **~33%** (Design+Impl+Synthetic; Integration partial) |

### 14.2 Four systems

| System | Design | Impl | Synthetic | Integ | Real | PIT | OOS | Cal | Fwd | % |
|---|---|---|---|---|---|---|---|---|---|---|
| QGV System | Frozen spec | Yes (new) | Yes | Partial | 0 | vintage probe | — | — | — | 33 |
| Technical | Structural freeze | Thin engine | Yes | Partial | LIVE_FETCH prices | bar PIT | — | — | — | 22 |
| Macro | Confirmed v0.1.1 | Thin engine | Yes | Snapshot only | FRED blocked | unavailable | — | — | — | 22 |
| Integration | v1.2 PROVISIONAL | Yes | E2E | Yes | 0 | candidate | — | — | — | 33 |

### 14.3 Backend modules (even if UI is one screen)

QGV

| Module | Design | Impl | Synthetic | Real/PIT |
|---|---|---|---|---|
| Analysis | Frozen v1.7.6 | Yes | Yes | PARTIAL vintage |
| Simulation | Spec v1.0 | Yes | Yes | product ≠ backtest |
| Portfolio | Official v1.1 | Yes | Yes | US working provisional |
| Leaderboard | Spec v1.0 | Yes | Yes | 0 |
| Track Record | Spec v1.0 | Yes + file store | Yes | live outcome probe only |

Technical (single workspace, separate backend %)

| Module | Design | Impl | Synthetic | Real/PIT |
|---|---|---|---|---|
| Market Data | Yes | Yahoo adapter | Yes | LIVE_FETCH |
| Chart | Goal recorded | Prototype page | — | — |
| Indicator | TSV candidate, list unfrozen | Placeholder | Yes | 0 |
| Signal | Recorded | Thin | Yes | 0 |
| State | Recorded | Thin | Yes | 0 |
| Regime | Recorded | Thin | Yes | 0 |
| Scenario | S=1..N placeholder | Thin | Yes | 0 |
| Probability | Recorded | Not calibrated | — | 0 |
| Execution zone | Recorded | Thin | Yes | not system order |
| Track Record | Generalized store | Yes | Yes | probe |
| Fusion | C-15 DECISION REQUIRED | Not implemented | — | — |

Macro (single dashboard, separate backend %)

| Module | Design | Impl | Synthetic | Real/PIT |
|---|---|---|---|---|
| Regime | v0.1.1 | Yes | Yes | UNAVAILABLE live |
| Growth/Inflation/Rates/Liquidity/Risk | v0.1.1 | Threshold heuristic | Yes | FRED blocked |
| Signal/Evidence | Recorded | Thin | Yes | 0 |
| VMR | Ownership unconfirmed | Not official | — | — |
| Scenarios | Recorded | Thin | Yes | 0 |
| Transmission | Recorded | Not built | — | — |
| Track Record | Generalized | Store ready | Yes | 0 |

