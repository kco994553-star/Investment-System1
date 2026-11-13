# Retained-input 3/3/3 comparison — 2026-11-13

Study QGV-333-20261113-01, financial valuation2026-11-04, input cutoff
2026-11-04T02:29:35.166580Z. Classification knowledge2026-11-08 is explicitly
retrospective reconstruction, not historical system-PIT completion. No new
price/filing acquisition. Source normalized observations were reused; this is
new fixed-core scoring, not newly recovered raw fundamentals.

Original targets are504 code rows/501 issuers and1057 issuer rows. Operating
factor references use the retained586-row source (504+82 prior admissions).
Held references use the retained8004 observation catalog, with factor-specific
eligibility, not all8004 peers. Catalog8004 is neither the evaluation population
nor a verified whole-market denominator. Its new 3/3/3 evaluation coverage was
not separately measured; whole-market denominator/coverage remain null.

## New candidate counts (unique issuers)

| Evaluation | Model | Q | G | V | All9 raw / scored | QGV simultaneous | Final | Gate known | 95% target |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| operating501 | U2-333 |303|0|0|0 / 0|0|0|409|476|
| operating501 | U1-333 |303|363|0|0 / 0|0|0|409|476|
| operating501 | S1-333 |242|0|0|0 / 0|0|0|409|476|
| held1057 | U2-333 |569|0|0|0 / 0|0|0|406|1005|
| held1057 | U1-333 |569|698|0|0 / 0|0|0|406|1005|
| held1057 | S1-333 |494|0|0|0 / 0|0|0|406|1005|

0 means no qualifying output in this execution, not a score of0. Gate-known
includes PASS and VALUE_EXCLUDED and does not imply all factors or total exist.
No axes are assembled across different code rows of an issuer. Each transition
set is deduplicated at issuer level; per-company files retain code-row detail.

## Input / valid raw / scored for the nine unified factors

Each cell is count over501 or1057 original issuers. Input presence is distinct
from validity/scope/period/classification/representative and scoring eligibility.

| Variant | operating501 input/raw/score | held1057 input/raw/score |
|---|---:|---:|
| roa_ttm |490 /465 /390|1043 /1017 /804|
| accruals_assets_ttm |488 /415 /341|1031 /896 /684|
| debt_assets |430 /400 /333|837 /773 /612|
| revenue_cagr_3y |488 /448 /373|1022 /929 /724|
| roa_improvement_3y |482 /482 /408|1015 /1015 /810|
| eps_diluted_cagr_3y (U2) |0 /0 /0|0 /0 /0|
| ep_ttm_diluted |0 /0 /0|0 /0 /0|
| common_bp |0 /0 /0|0 /0 /0|
| cfo_mcap |0 /0 /0|0 /0 /0|

U1 substitutes only revenue_growth_consistency_3y. Valid raw/scored counts are
448/373 and931/726; G-axis counts363/698 require all three G factors. Q and V are
identical for every U1-333/U2-333 code row. U1/U2 common valid G is0, so a common
G score-change distribution cannot be calculated. This is not a performance win.

S1 per-recipe selected-target inputs/raw/scores and overlapping failure reasons
are in private factor-coverage.csv and study-summary.json. Financial raw common
ROE0/2, common-equity/assets3/11 (operating/held), scored0 in both; common BPS
CAGR0. Same23 equity REIT issuers are present in both populations and are not
added together: interest coverage raw15, scored0 from N<20; FFO/share growth
is definition-pending. Their prior CFO/assets improvement remains a reused raw
observation, not a newly recovered G axis under a three-factor strict recipe.

## Changes from retained reduced models

No old result was recalculated. Each new model is compared to its corresponding
old U1/U2/S1 at the same evaluation inputs. This is a whole-model comparison:
core selections/weights changed; the official model was not replaced.

| Evaluation | Comparison | New Q/G | Lost Q/G | Common Q/G | Common-score changed Q/G |
|---|---|---:|---:|---:|---:|
| operating501 | U2 → U2-333 |0 /0|87 /373|303 /0|303 /0|
| operating501 | U1 → U1-333 |0 /0|87 /45|303 /363|303 /363|
| operating501 | S1 → S1-333 |0 /0|8 /397|242 /0|242 /0|
| held1057 | U2 → U2-333 |0 /0|235 /724|569 /0|569 /0|
| held1057 | U1 → U1-333 |0 /0|235 /112|569 /698|569 /698|
| held1057 | S1 → S1-333 |0 /0|21 /793|494 /0|494 /0|

Total ranks remain null; factor ranks/deciles use the same retained algorithm.
Changing a core recipe is not a financial improvement or investment return.

## Structural upper bound and next inputs

Unified known accounting incompatibility blocks67 operating issuers
(44 capital-financial+23 equity REIT), and132 held issuers (109+the same23).
Even assuming every other input/classification/peer/gate gap solved, optimistic
upper bounds are434/501=86.63% and925/1057=87.51%, below476 and1005 required.
These are scope-only bounds, not predicted recoveries. No financial formula was
silently substituted and no original target removed.

A fixed accounting-specific S1 research configuration is the separate design
route; its feasibility is unproven, and its current results do not reach95%.
The missing inputs are four comparable diluted-EPS FY observations with dated
share/action identity; verified TTM diluted EPS; common BPS attribution/basis;
2026-11-04 prices; class-complete issuer equity and required EV components;
financial common-owner history and independent official-Q gate evidence.
Normalized snapshot absence does not assert that every original filing lacks
these values. Existing WRB acquisition/delivery queue is retained. Nov2 prices
are not substituted for Nov4. The frozen input cutoff02:29UTC is before the
Nov4 US regular close: a future Nov4 closing price cannot be injected into this
snapshot merely because its calendar date matches. Later-acquired historical
inputs keep actual retrieval times and require a separately versioned research
snapshot/availability context, never backdated acquisition. Equity-REIT growth
definition remains an explicit
owner-policy decision, not a data fetch problem.

Performance is NOT_MEASURED. A later performance comparison must retain dated
PIT universe/input versions, identical trade timing/costs and fixed out-of-sample
windows in the approved backtest path. No extra factor configurations or
performance-selected changes were added.

## Verification and private resume

Six existing CLI dual-study runs completed. Independent three-factor mean checks
3541; unchanged Q/V under the G-only contrast1561 code-row comparisons; run file
byte/hash reopen102; all-bin group partition2040. Existing normalization and
stored tie rules were not rewritten. Delivery files maximum1799966 bytes.
Evaluation and reference identities were independently regenerated from pinned
source inputs and compared to delivery bindings. Consumer/browser/auth/deployment
remain Main tasks; producer file validation is not consumer acceptance.

Private local resume: /workspace/private-qgv333-20261113. New configurations,
six pinned jobs, run results, comparison-rows.json, factor-coverage.csv,
study-summary.json, verification.json, delivery-verification.json,
continuation-inputs.json and delivery/distributions/bin-routing are preserved.
Remote resume details and final CI are in the final Main handoff; actual company
rows and original methodology PDFs are not in public fixtures.
