# Confirmed split-only prices connected to existing technical kernels

Base #489 59eb33ca3b085eff3f1486c230a74408aeb2558b, with #480/#478/#469/#467 dependencies and canonical ab6a83c3be2276abdcf855c71c5f273926e2dcc4. This is offline research/data adapter work; no UI, workflow, guard, collection or operational model change.

## Removed blocker

The existing KIS chart normalizer already transforms raw MODP0 OHLC/volume for confirmed splits. The technical adapter previously always consumed raw_bars and suppressed all SPLIT_ADJUSTED values. Both normal CLI analyze (13 components) and technical-measures/technical-board (3/6/12-month momentum, volatility, dollar-volume) now use the proper price basis through the existing numerical kernels.

The original transformation is shared, not reimplemented: OHLC before an event is divided by the documented ratio; volume is multiplied. Amount stays raw. validate_contract verifies adjusted bars exactly against raw bars plus the confirmed event list and rejects dividend-adjusted or altered values. MODP1 remains rejected. Dataframe conversion, new seeding, indicator formulas, weights and population rules are not introduced.

At S, prices are rebased using only events dated through S, even if a newer retained archive contains later events. The original raw rows are separately validated and passed to liquidity; VWAP/volume scope must still be evidenced and KIS scope remains unconfirmed. Adjusted OHLC is never called RAW. Direct-source symbol/asof/session/hash validation is shared for price and separate raw liquidity inputs.

## Adoption conditions and output contract

Existing dated identity, complete expected observations, held ranges, minimum periods and full retained recursive seeds remain required. RAW uses no_split_* evidence; adjusted uses adjustment_start/end/reference and adjustment_method=CONFIRMED_SPLITS_ONLY, derived from the existing documented action-coverage range. A split list by itself does not prove completeness. Missing coverage keeps diagnostic raw_value but null value. A legacy report-reconstructed range remains report-reconstructed evidence, not new original-source verification.

Analysis reports price_basis/chart_basis/diagnostic_basis=SPLIT_ADJUSTED and result_kind=SPLIT_ADJUSTED_SERIES_DIAGNOSTIC. Readiness adjustment.state=CONFIRMED_SPLITS_ONLY with the actual coverage fields. RAW outputs keep their original kind and frozen technical-leaderboard/2026-11-03.1 settings bytes/hash. Adjusted five-measure boards have a separate technical-leaderboard/split-adjusted-2026-11-05.1 settings version/hash; mixed RAW/adjusted comparison groups are refused. Numerical settings are unchanged; only the approved basis policy is separately versioned. raw_value means unqualified indicator arithmetic on the declared diagnostic basis, not an unadjusted quote. Main must keep chart/indicator basis aligned and handle this adjusted result kind/state; authentication/routes remain Main work. Publication and historical PIT status remain private/NOT_VERIFIED.

## Actual execution and limits

Synthetic confirmed 2:1 path equals an independently authored economic constant-price100 path: SMA/EMA100, MACD/signal0, ATR2; price momenta and volatility0. Tests exercise transformed volume, tampering rejection, missing action coverage, a split after S, and literal initialization boundaries14/15,19/20,25/26,33/34 sessions. The separate liquidity-input validation regression was reproduced and fixed after independent review. Related regression108 passed, including15 adjusted-path cases. Five existing Hypothesis properties also passed after the adapter change. No additional Critical/Important remained on review.

Existing approved AMD KIS100-bar inputs at2016-04-01 and2026-10-23 document split-free windows. The adjusted identity transformation was executed through normal CLI: 13-component raw/adopted12/12 and12/5; five-measure raw/adopted1/1 and1/0. This opens18 adjusted-basis measure cells that the old adapter suppressed, while reusing the same company's previously eligible RAW economic inputs. It adds no distinct security, current-date quote, overall-market denominator or unique-company coverage. Both actual windows contain0 split events; actual split-event validation remains unverified. Corporate-event continuity across a real split is synthetic-only. Transaction-value adoption remains null.

Company values, source bodies, reconstructed evidence and outputs are preserved only in the existing approved private KIS handoff. No public fixture contains actual company prices or returns. Missing2026-11-02 prices are not filled with these dates. Same-day financial V/QGV is unaffected.

## Entry point and Main handoff

Use the unchanged local-job CLI tools/kis_retained_calculate.py with a validated SPLIT_ADJUSTED contract in analyze or technical-measures mode. normalize still requires original MODP0 and confirmed event evidence; never relabel a provider-adjusted response. Output stays outside Git0600, new-file-only, fixed non-sensitive console lines. The source code/hashes and exact private result locations are recorded in the private handoff manifest.

Main must display the basis and evidence state above, retain original source/evaluation/capture times, and avoid merging different evaluation dates into coverage. No workflow/Secret/schedule/CI-list change is requested. #497's property dependency/UI integration is a separate Main PR and its completed tests are reused.
