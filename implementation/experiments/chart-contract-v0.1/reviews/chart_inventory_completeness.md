# Chart inventory completeness pass · 2026-10-04

Read-only inspection of `/workspace/scratch/e21499bd6a66/chart-work` repository specifications against scratch `audit-matrix.json` (81 A–H requirements + 17 I entries). This is a requirements-completeness pass, not a new implementation audit. Historical assertions of RC26/366 PASS or 313/313 PASS in specifications are not proof of current checkout implementation.

## Result

The 98 entries cover the user's current explicit A–H request well, but do **not** exhaust repository visual requirements. In addition, 98 is a count of requirements/capabilities, not 98 independent charts: metadata, controls and views overlap. Do not raise completion percentages by counting minor controls as completed charts or change the denominator without a versioned inventory.

### Explicit extra UI requirements worth adding

| ID candidate | Requirement | Repository evidence | Why material / existing overlap |
|---|---|---|---|
| J01 | Portfolio QGV distribution and average | `QGV Portfolio · Specification v1.1.md:74,92` | C01/C02 are company scores; portfolio holding distribution is separate. |
| J02 | Portfolio Confidence distribution | Same `:74` | C03 company confidence is not weighted holding exposure/distribution. |
| J03 | Portfolio Valuation / Safety Margin view | Same `:74,94` | Company range/MOS in C06/C07 is not portfolio valuation exposure. Computation/weighting remains to be specified. |
| J04 | Company reassessment trigger display: observed change vs effective threshold, distance, state, threshold source | `QGV Leaderboard · Specification v1.0.md:120–127,134` | H03 price/daily return and B invalidation do not cover 1D/5D/20D/DRAWDOWN reassessment. Not buy/sell signal. |
| J05 | Full VMR comparison: 1D/5D/20D return, 20D/60D/1Y volatility, daily sigma, ATR14%, Beta, volatility percentile, drawdown; company/industry/market and abnormal moves | Same `:129–134`; `QGV Portfolio · Specification v1.1.md:57–60` | B06/B07/E11 cover some components. Beta, percentile and market/industry adjusted moves not explicit inventory rows. Prefer one grouped VMR requirement with exact subitems. No fixed numeric method inferred. |
| J06 | Reassessment event timeline / outcome calibration | `QGV Leaderboard · Specification v1.0.md:136–140` | I09 QGV revision and I12 scenario calibration do not capture frozen trigger event, before/after QGV and D+5/D+20/63D/252D outcomes. |
| J07 | Technical QGV Fusion result and base/context separation | `Technical Analysis System · Consolidated Record v0.1.md:49–54,122–134` | Existing B14 research/model separation and B15 future path omit explicit QGV Fusion result UI. Must not overwrite raw QGV score or conflate QGV direction with path probability. |

## Existing rows needing richer subrequirements (no need to invent new chart count)

- **B15 Future Path:** variable S=1~N (S1–S5 merely examples), each path range/trigger/confirmation/invalidation/QGV compatibility/confidence/empirical probability, widening uncertainty with horizon, actual forward path comparison. Source Technical consolidated `:56–99,111–115`. 120/252 trading-day horizons are proposals, not frozen official constants. Overlay selection follows `:26–30,122–134`.
- **E01/E02/E03:** quarterly immutable snapshot linkage, not only current pie. Portfolio `:47–55,77–80`. Include actual-vs-target industry change `:48` and exact snapshot/version/as-of labels. Fields taxonomy does not mean populated historical memberships.
- **I01 portfolio scenario range:** show main contribution/loss companies and preserve company weight/scenario conditions, not add target prices. Portfolio `:68–71`.
- **F/I return plots:** common initial value, each constituent, holding average, whole portfolio, universe, type averages, benchmarks; zoom and individual toggle; no omitted 'other' holdings. Simulation `:31–52`. Growth/Quality/Momentum minimum two is broader than one Growth Index.
- **F08 quarterly:** show industry/type exposure changes, all constituents, weights, start/end price/return and QGV snapshot. Simulation `:59–63`.
- **F performance comparison:** explicit benchmark excess return and risk difference; separate risk/performance metric cards from time-series plots. Simulation `:54–57`.
- **Simulation comparisons:** basic vs personalized QGV, QGV-only vs Technical/Macro combined, rebalance frequencies, type-adjusted vs raw. Simulation `:83–88`. These are comparison modes, not all independent renderers.
- **I09–I15 Track Record:** original snapshot drill-down; sample size and evaluation period; do not blend historical/OOS/forward into one curve. Track Record `:70–82,93–101`.
- **I09 Q/G/V outcomes:** per-axis score change vs revenue/EPS/FCF/ROIC realization and returns; Key Driver realized/partial/not/opposite status. Track Record `:40–53`. This is more than score revision line.

## Candidate design extensions — explicitly not approved production or proven implementation

`Macro System · Latest Consolidated Record v0.1.4 Candidate.md` is candidate design. `Investment-System1 · Frontend Information Architecture 2026-09-23.md:109` explicitly says v0.1.4 Candidate is not default.

| Candidate visual family | Source lines | Essential distinction |
|---|---|---|
| Eight macro axes + state views: growth/inflation/liquidity/monetary/credit/labor/fiscal/FX with level/direction/momentum/surprise/stress/confidence | 100–104 | Current A–H G rows omit labor/fiscal/FX and states. These are candidate design scope. |
| Variable macro scenario path/distribution | 106–110 | Not the same object as Technical scenario; probability != confidence. |
| Factor→economic channel→industry→company→Q/G/V transmission view | 112–116 | Preserve lag vs duration, evidence and provenance. Frontend IA explicitly requests transmission at117–119. |
| Structural/empirical/market-implied/event company exposure views | 118–122 | Exposure != sensitivity. Formula is explanatory proposal, not fixed calculation. |
| QGV base vs macro context and Technical base vs conditional probability comparison | 124–137 | Keep raw base unchanged; display agreement/conflict, not silently merge. |
| Portfolio macro factor concentration/risk context | 139–144 | Cash pressure != cash weight; cash is not permanently0%. |
| Historical/hypothetical/reverse stress impact and contribution | 146–152 | Stress must not receive invented occurrence probability. |
| Macro ablation/attribution/calibration/forward comparison | 161–172 | Distinguish train/OOS/forward and single/joint effects. |

The broad request to list all requirements should mention these as **repository candidate extensions**, rather than claim all were mandatory frozen chart specifications or implemented.

## Type donut and overlap semantics

Source of authority is Portfolio `:53–55`: multiple types allowed; per-type sums may exceed100%; type composition text + donut + separate overlap are required. No primary-type assignment, equal fractional allocation or forced normalization is specified.

Recommended faithful UI representation:
1. Industry donut: mutually exclusive source taxonomy if provided; denominator explicitly actual or target capital; unknown/unclassified slice retained.
2. Type donut: **exact membership-set composition** (e.g. Growth+Quality), labelled `유형 조합별 구성`; each holding's weight is counted once so mutually exclusive slices sum to the portfolio denominator. This is a presentation grouping, not a new type policy.
3. Alongside it preserve the user's requested **marginal per-type exposure text** (`Growth 60%, Quality 50%, ...`) or bars whose total may exceed100%. Never reinterpret the exact-set donut as per-type exposure.
4. Overlap chart: exact-set intersection bars/UpSet-like matrix retain each membership combination and weight. If pairwise overlaps are shown they must be clearly labelled inclusive pairwise intersections; a triple membership contributes to several pairs, so pairwise sums are not total portfolio weight.
5. Do not infer memberships from company names, sectors or familiar stocks. Missing memberships stay `UNCLASSIFIED`/`UNKNOWN` with coverage. An explicit empty type set and unavailable taxonomy should not silently merge semantically.
6. Keep taxonomy version, snapshot ID/date, security identity, weight basis, actual-vs-target scope and source reference. Current labels cannot be projected into past holdings without historical evidence.
7. For synthetic demonstration use fictional holdings and explicit DEMO labels. Real portfolio target weights alone cannot establish actual weights or historical classification.

This presentation does not decide or modify scoring weights, type taxonomy, numeric methodology, Official/LIVE permissions, or existing portfolio allocation.
