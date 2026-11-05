# Technical pipeline validation and screen fixtures

Base: #480 de9d87e46d060cba79651b394e64915ccf139d45, containing canonical ab6a83c3be2276abdcf855c71c5f273926e2dcc4. The #467→#469→#478→#480 dependency chain remains. DC-42 assigns research modules/tests to Codex. UI, workflow, common guards, CI lists and decision records remain Main-owned.

## Scope and defect

Use the existing KIS JSON normalization → common technical measures → frozen group board/filter → reader export path. Existing pytest covers split/identity/history gates, VWAP scope, CLI privacy and detailed formulas. New Hypothesis properties cover independent invariants rather than a second calculator: permutation invariance; null/nonfinite values never becoming zero; tied value ordering by fixed ID; ranks 1..N; exact tail cardinalities; filters retaining original N/ranks; duplicate fixed IDs; same-invalid-date export; positive OHLC scaling and source order preserving momentum after actual normalization. No portfolio weighting, PIT completeness or whole-market claim is added.

Hypothesis minimized an invalid saved-result date to `2017-02-30`: matching outer/inner dates bypassed the exporter. Reuse its existing `_day` validator before export. No formula, population, weighting, gate relaxation or price change. Fixed synthetic regression runs without Hypothesis.

## Dependencies and execution

Test-only dependencies are pinned in `implementation/tests/research/dependencies/technical-properties.txt`: Hypothesis6.148.7 and sortedcontainers2.4.0. Operational dependencies are unchanged. Install in a test environment, not production:

```sh
python -m pip install -r implementation/tests/research/dependencies/technical-properties.txt
PYTHONPATH=implementation/src HYPOTHESIS_STORAGE_DIRECTORY=/tmp/investment-technical-hypothesis python -m pytest -q --hypothesis-show-statistics implementation/tests/research/test_technical_properties.py implementation/tests/research/test_technical_screen_fixtures.py
```

Node is required for the real merged Main JS reader integration test (already used by project UI checks). Properties use derandomize=True, database=None and explicit example limits. The property module explicitly skips if Hypothesis is absent; that is missing test coverage, not successful property execution. Date and fixture regressions are separate and still run.

Actual local results: related pipeline set79 passed; focused new tests7 passed; five properties101 passing generated examples after fix (40/4/40/5/12, discarded generated examples are not successful tests). Without test-only dependency path:2 passed,1 module skipped. Package installation succeeded separately. Only synthetic execution occurred; actual-data calculations/adoptions/backtests/new source requests=0.

## Pandera suitability

This selected path consumes JSON dictionaries/lists, Decimal strings and evidence objects. It has no DataFrame input. Existing normalize_page/validate_contract/_day and the actual JS reader already validate these structures. Pandera would require a conversion and duplicate the contract, so it is not adopted or installed. Pandas availability in the environment does not make this input DataFrame-based. No coercion, fill or missing-value replacement is introduced.

## Main screen inputs

Tracked public-safe, author-created synthetic files: `implementation/tests/research/fixtures/technical_screen_v1/`.

- normal.json: N10; negative/zero/positive momentum and ties. Rank1 is largest value, fixed-ID tie break. Volatility and dollar-volume fixtures remain nonnegative.
- empty.json: confirmed empty group, N0; no matched rows.
- partial_missing.json: volatility has one null adopted value and a separate raw diagnostic; valid N9, no deciles, filter UNKNOWN10. Empty selected IDs do not mean a proven zero-match group.
- unknown_group.json: group N/median/rank/deciles null; absolute company conditions remain distinct. Relative filter UNKNOWN10.
- stale.json: original evaluation-day payload retained. Harness query date is later; STALE metadata never creates a new observation or reranks values.
- failed.json: null payload. Harness ERROR is source failure, not an empty population.
- expectations.json: literal expected ordering, selected IDs, PASS/FAIL/UNKNOWN counts, units, evaluation/query dates, missing-value meanings and an author-created long Korean company display name.

Five nonfailure payloads use the existing `technical-leaderboard/1` cases bundle accepted by `IS2.techScreen.validate`, not a new UI contract. Transport state/freshness/company display name stay in the separate harness manifest, not in strict board rows; Main supplies those to its existing company-name/transport test harness. The retained raw diagnostic never fills an adopted null. Filter selection is separate from the original population's scores/ranks/deciles. No new percentile is computed after filtering. Existing13-component chart/analyze and Lab contracts remain separate.

Rebuild fixtures deterministically (synthetic only):

```sh
PYTHONPATH=implementation/src python -m investment_system.research.technical_screen_fixtures --output-dir implementation/tests/research/fixtures/technical_screen_v1
```

## Main requests and boundaries

1. Add the pinned test-only requirements to the CI test environment so the five Hypothesis properties actually run. No shared dependency/workflow file is edited by Codex. No new node/browser manifest entry is required: new Python files are already included by the existing full pytest discovery. Main may reuse fixture paths in its existing browser tests.
2. Keep the two dependency-free regression/fixture tests in full discovery; report an absent-Hypothesis module skip explicitly.
3. Connect normal/empty/partial/stale/error and long-name harness cases to existing UI/auth contracts. No production response schema change is requested.

No actual prices, portfolios, KIS raw responses, identifiers of real securities, source-body hashes, tokens or keys are included. No collection, merge, deployment, workflow execution or permission change is performed.
