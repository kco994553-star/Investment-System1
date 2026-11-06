# Validation and held-input scope

## Implemented and synthetic validation

Exact owner §5 defaults registered as `sector-qgv-default/0.1.0`. Catalog: 51 variants, 39 implemented calculators, 12 individually held definitions; all Q01–Q13/G01–G12/V01–V15 design IDs plus Q14/G13/G14 represented. Historical dictionary IDs and operating composite IDs are not equated. See `CATALOG_MAPPING.md` and `catalog.json` for each pending recipe.

Shared common percentile and SEC facts normalization reused. No official qgv file, public result, frontend, workflow, guard or dependency was changed. Same public/private numerical configuration and inputs give identical results. The old company-type multiplier and Lynch tags are absent from sector arithmetic.

Synthetic end-to-end: 20 companies, normal preview 20/20 totals, original-population ranks, separate before/after common ranks for preregistered C1 axis / C2 factor / C3 internal-weight candidates, matching-preview configuration save and CLI artifacts. Hand expectations include 80/60/40 at 30/20/50 => 56 before the gate; EPS 5/price100 => .05; PEG20/.10 => 2; signed/zero observations; split/ADR scope; same-role budgets; missing gate despite Q deselection; strict missing before gate; peers19 vs20; ties; 90-valid-per-factor/80-joint example; version/cache identity and public/private parity.

New suite: 26 tests passed across the final full run (25) plus added stored-fixture regression (1). Commands:

```sh
PYTHONPATH=/workspace/scratch/technical-leaderboard-test-deps:implementation/src \
 python -m pytest implementation/tests/test_sector_qgv.py -q
PYTHONPATH=/workspace/scratch/technical-leaderboard-test-deps:implementation/src \
 python -m pytest implementation/tests/test_private_boundary_static.py implementation/tests/test_qgv_official_guards.py -q
```

The first combined run passed 186 cases (20 new + 166 existing relevant boundary/official-guard cases). After changes, the new suite and affected held/CLI regressions passed; the private boundary suite passed 28 cases again. Unchanged official checks were not repeated.

A fresh independent branch review found five synthetic defects: post-valuation forecast leakage, future valuation dates, cross-issuer hash relabeling, composite shareholder-yield identity/basis bypass, and lost source STALE disposition. All are fixed with regressions. The held run also exposed unavailable rows with null old calculation version; these rows are retained as unavailable, rather than aborting other companies or adopting their inputs.

## Real held input: measured, not performance

Scope: the **dated operational Universe504 code rows**, not unique verified securities, current whole market or historical C2. Source snapshot `2026-11-04T02:29:35.166580Z`; sector valuation date `2026-11-04`. No prices were imported from another date. Exact source snapshot SHA-256: `36cab8fdda135c01f0b3a87da9fc33dbe304fcb71c562f91e616bd2a921b3204`.

503/504 code rows link to archived SEC companyfacts by source hash and CIK. 501 codes produce at least one valid raw observation; 14 raw variants yield 5,439 code/variant observations. Two hash-connected records are explicitly unavailable and one record has no matching source hash. No fresh collection or old baseline arithmetic was performed.

| Raw variant | All required primitives present / 504 | Valid raw ratio / 504 |
|---|---:|---:|
| Operating margin TTM | 361 | 359 |
| Accruals / average assets TTM | 423 | 417 |
| Debt / assets | 385 | 385 |
| ROA TTM | 493 | 491 |
| CFO / average assets TTM | 426 | 421 |
| Interest coverage TTM | 328 | 298 |
| Revenue 3-year CAGR | 427 | 427 |
| ROA 3-year improvement | 485 | 485 |
| Gross profit / average assets TTM | 182 | 180 |
| Net debt / assets | 384 | 384 |
| Revenue 1-year growth | 430 | 430 |
| Revenue 5-year CAGR | 414 | 414 |
| Operating income 3-year CAGR | 362 | 321 |
| Revenue growth consistency (3 changes) | 427 | 427 |

**Scored factors, Q/G/V, all axes and model totals: 0/504 measured.** Book-sector/accounting/effective-date evidence has not been connected (0 mappings); verified new-model price/share/TTM EPS inputs are also unconnected. A raw ratio is not an adopted score. Required sector peers are not assembled by repurposing operating SIC/ETF classifications. No unresolved company is dropped from the denominator. Actual common-valid comparison count is 0 for C1/C2/C3, and score deltas are unavailable. Performance, drawdown, turnover and PIT backtest remain unmeasured, not zero.

Separate preserved official publication: Q485/G493/V357, all axes356, default total481 / 504; price date `2026-11-02`, generated `2026-11-04T02:35:15.601145Z`, calc23.1. This is a cached reference with different input/normalization/model policies and a different price date; it is **not** a matched-date causal before/after score comparison. Its earlier coverage computation was reused unchanged. No claimed official coverage improvement.

All company observations/results remain private. Private resume directory: `/workspace/private-sector-qgv-20261106/final-run`, with job, source archive references, input snapshot, preview, comparisons, saved configuration and SHA-256 manifest. Remote handoff repo/ref and content hash are supplied in the PR/Main handoff after preservation.

## Remaining boundaries

Main: dated book-sector/accounting mapping, evidenced duplicate-issuer representative, existing official gate observation linkage; authenticated CLI/job delivery, UI and CI-list integration. Codex: consume those existing input contracts and score the original group when available. Price/share/TTM EPS/financial-common-equity/REIT/forecast recipes remain individual data dependencies; no neutral fills or formula swaps. Pending catalog definitions remain visible but not executable selections.

Owner: no new collection, merge, deployment or official replacement executed or requested by this PR. Performance validation is not a prerequisite for using the implemented initial default in development.
