# 계층 3 연구 계산·검증 인계 기록

Draft [#469](https://github.com/kco994553-star/Investment-System1/pull/469),
base #467 `745b143a61ef4f2eaa450497ccb603ab9c149bb0`.
Actual calculation code: `ad72d4e674120a0b6e5a1d4066432b11df57def5`.
The subsequent commit changes this record, the plan checklist and package inventory tests only; it does not change calculation settings or algorithms.

## Calculation and handoff

The held 2018-02-16 inputs were processed without provider requests. Prior momentum and volume arithmetic/coverage were compared;
new sample volatility was independently checked using rational variance and `statistics.stdev`.
Real values, inputs, provenance, observation counts and missing reasons remain in the approved private handoff.
The remote delivery was downloaded again, every delivered file was opened/hash checked, and the null group-rank boards were checked.

Unknown dated membership or fixed security IDs retain null ranks/deciles; raw request-series diagnostics are not a security or market ranking.
The retained provider VWAP×volume arithmetic does not establish matching trade inclusion. Primary dollar volume remains gated until that evidence exists.
These are input limitations, not a reason to stop independent price measurements or a request to change QGV weights.

Main received the specification before real comparisons in [comment 6601332838](https://github.com/kco994553-star/Investment-System1/pull/437#issuecomment-6601332838).
The [final handoff 6601792076](https://github.com/kco994553-star/Investment-System1/pull/437#issuecomment-6601792076) links the pinned specification,
settings, five synthetic cases, and the private result location. Application reader/screen integration remains Main's responsibility.

## Tests and review

- Initial shared-code baseline: 26 passed.
- New measurement/ranking tests began red with absent implementation; the focused suite passed after implementation.
- One independent reviewer checked the whole calculation branch. A normalizer `VOLUME_MISSING` flag incorrectly invalidated valid closes.
  The regression reproduced it; the fix keeps close-based indicators independent while retaining close/OHLC/global quality checks.
- Focused calculation and related regressions after that fix: 63 passed; private-boundary/direction tests: 32 passed; direction guard: 0 hits.
- Additional full Python run: **4,845 passed, 1 skipped, 1 failed**. The failing package inventory test listed neither the prior
  `liquidity.py`/`sector_comparison.py` nor the new technical modules. The same test was run on base #467 and reproduced its prior-module failure.
  The explicit inventory and the single co-located frozen technical JSON read were added; banned network/provider/import/price IO checks remain.
  The failure and all changed-module, shared-regression and boundary checks were then rerun together: **104 passed**.
  The long full run was not represented as a second all-green run after this test-only correction.

Public changes are research modules/settings, research tests, synthetic fixtures and research documents.
No real source hashes or company metric values are included in this record. No app/shared operational engine, workflow, execution branch,
QGV weight, merge or deployment change is part of this PR. The ordinary research worktree remains available for review feedback.
