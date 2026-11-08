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

## Classification / Main bridge continuation — 2026-11-07

Original #505 head `dc11144b4052139a5784e41beb1b97d6ebbf6a78`: final CI
7 successful / 2 skipped (deploy, replay_source), recorded without repeating
those successful checks. This continuation adds only classification/transport
paths; the original raw matrix and calculation formulas are unchanged.

Evaluation 2026-11-04, financial snapshot as_of
2026-11-04T02:29:35.166580Z, original **Universe504 code-row denominator 504**.
The separate 2026-11-02 financial 11-code price request is not part of this run.

| Stage | Before | After / 504 | New work |
|---|---:|---:|---|
| Held official SEC SIC source connected | not measured here | 503 | Verify pinned submissions members; official SIC kept separate |
| Book-sector + accounting research correspondence | 0 | 351 | 153 unresolved retained |
| Any valid raw observation | 501 | 501 | 14 variants / 5,439 observations reused; 0 rederived |
| Any factor score | 0 | 291 | 3,526 code-variant scores from existing raw observations |
| Q axis | 0 | 206 | Price-independent partial output |
| G axis | 0 | 280 | Price-independent partial output |
| V / all-three / model total | 0 / 0 / 0 | 0 / 0 / 0 | Strict inputs and date constraints unchanged |

Official-Q-only replay connected 485 valid gate inputs, 19 unavailable. Among
351 mapped rows: PASS 242, VALUE_EXCLUDED 100, UNKNOWN 9; 153 unclassified rows
have no applied sector model. These are **gate counts, not final-score counts**.
Replay uses existing official engine context (523 including TARGET query rows,
498 representative pool); sector score denominator remains the original 504.
The official Q >=8/fallback policy and new-model >=20/no-fallback policy are
kept separate. No price was used by the Q replay and no new official publication
was produced.

Research classification unresolved reasons (mutually exclusive, sum 153): exact
SIC correspondence not reviewed 54; REIT 27; mixed business services 16; low-capital
fee business unproven 14; instrument end market 9; mixed finance 7; mixed retail
7; media/telecom boundary 6; managed healthcare boundary 5; research end market
3; semiconductor equipment boundary 2; source accounting-profile conflict 2;
source not connected 1. They remain in the denominator. No post-result changes
to correspondence rules or peer grouping were made to cross the minimum N.

Selected-factor missing **events** (multiple per company, not a row partition):
MISSING_INPUT 1,233; PEER_SAMPLE_SMALL 175; issuer scoring representative
unresolved 5; PERIOD_MISMATCH 4. Price/identity/current-class/TTM EPS inputs are
still absent where required. Financial templates additionally lack the common
capital/BPS components; current mapped bank/insurance/broker groups are 17/18/7,
so they cannot meet the new 20-valid-issuer rule even if those inputs arrive.
Energy 14 and telecom 3 also remain small. No sector pooling or neutral fill.

Actual affected synthetic tests: classification 13 passed; Main bridge/CLI 8
passed. New tests cover unmodified raw reuse; partial Q/G without prices; 19-peer
failure; future/mismatched source and gate date; exact editor→engine→projection
values; role-budget mismatch; duplicate aliases; FY1/NTM ambiguity; mandatory gate;
all original UI rows and common-valid ranks; existing CLI output/save/request hash.
These are synthetic tests. The actual held-source run above is separately counted;
performance, historical PIT and full-market coverage remain **not measured**.

Read-only Node check of actual Main #507 `cd2fd62ed7793541d09f34d871d0ff24fef24135`:
its own fixture accepted; required gate policy rejected (`GATE_POLICY_UNSUPPORTED`);
common-engine response rejected (`KEY_MISSING`, `$.schema`). Python/CLI bridge
works; Main browser/server invocation is still to be connected. See
`MAIN_INTEGRATION.md` for exact Main-owned changes. Zero total rows means **0
computed / 504**, not company scores of zero and not 0% whole-market coverage.

Fresh independent review found and fixed two integration defects: identical
verified source hashes selected the first archive rather than the earliest
observed acquisition; gate replay inserted wall-clock time into input/cache
identity. Source selection now orders by acquisition, archive hash and member;
execution time is audit-only. Two minimized synthetic regressions passed. Only
the affected classification/scoring run was finalized again after these fixes;
no financial raw ratios were rederived. The newly connected official-engine import
path passed the existing official guard suite: 138 tests (53.05 seconds). No
shared guard was changed.

The final affected-source run preserved the same result rows/counts after the
reproducibility fix, and all original raw observations/members are exactly equal.
The public/private static boundary suite passed 28 tests. This continuation's
local checks comprise 21 new-path tests + 138 official guards + 28 privacy checks;
the previously successful unchanged 26-test sector suite was not rerun.
Private final resume location: `/workspace/private-sector-qgv-classified-20261107/run-final`;
initial `run/` is superseded and excluded from remote handoff. Aggregate before/
after counts, job, source references, raw-preservation audit and manifest are
saved alongside it. Actual company inputs/results are not repository fixtures.

## 2026-11-07 partial comparison and additive source correspondence

Reference aa9c4484 results are reused, not recalculated. D1 settings comparison
and independent I1 classification treatment are specified in
[PARTIAL_COMPARISON.md](PARTIAL_COMPARISON.md). Retained 504-row financial matrix,
gate input and previous351 mappings are unchanged. Independent read-only review
checked the49 affected Q deltas using0.2×(ROA−margin), G/gate invariance and
new14-source linkage. Q/G after classification is213/293; V/joint/total0 computed
rows, performance unmeasured.

Affected checks: `test_sector_qgv_partial.py` (4), new classification addendum
regression (1), existing partial-classification integration (1); all passed.
The counter contract now explicitly includes0 gains/losses. The final run also
executes the28 static private-boundary checks because new public fixtures were
added. It does not repeat the old whole-sector test/real calculation audit.

Main CI-list request: add `tests/test_sector_qgv_partial.py`. New fixtures are
synthetic20-company rows; real company comparisons, source evidence, input gaps
and targeted policy audit are only in the approved private handoff.
