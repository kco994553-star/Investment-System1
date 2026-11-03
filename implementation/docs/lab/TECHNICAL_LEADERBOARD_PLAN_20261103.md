# Technical leaderboard implementation plan

> For agentic workers: execute inline using superpowers:executing-plans; one independent calculation review at the end.

Goal: five independently measured technical indicators and frozen-group ranks, with an executable private sample handoff.
Architecture: research-only pure measurement module + board/rank module; shared normalization/liquidity/decile selection are reused.
Tech stack: Python standard library Decimal/statistics, existing pytest tests. Spec: [TECHNICAL_LEADERBOARD_V1.md](TECHNICAL_LEADERBOARD_V1.md).
Global constraints: no new market-data collection; no execution branch, app/shared contract, workflow, merge or deployment changes.
Raw results stay in the approved private handoff. Public fixtures are synthetic.

Review focus: missing first previous close; wrong trade-scope promotion; absent/duplicate fixed IDs; N-dependent tails and middle bins;
filtering that silently recomputes the original population. Each is explicitly tested below.

## Task 1 — fixed settings and measurement

Files: `research/exp_deciles/technical_measures.py`, `technical_leaderboard_v1.json`,
`tests/research/test_technical_leaderboard.py`.
Interface: `measure(rows, *, signal_day, symbol, series_id, evidence) -> dict`.
- [ ] Write/run failing tests for six-month known returns, full coverage and anchor, raw/economic separation, scope/currency, duplicates.
- [ ] Implement using canonical schedule and `liquidity.summarize`, preserving the five units and independent missing reasons.
- [ ] Run focused tests; commit settings/measurement before actual sample comparisons.

## Task 2 — board and filter

Files: `research/exp_deciles/technical_leaderboard.py`, same test file, synthetic fixture builder in tests.
Interfaces: `build_board(measurements, *, group) -> dict`; `filter_board(board, conditions) -> list[str]`.
- [ ] Write/run failing tests for N=9/10/11/23, decimal ties, nonpositive medians, per-metric N, missing/duplicate IDs and unknown groups.
- [ ] Implement approved extreme tails via `selection.select`; allocate only interior bins; filter frozen conditions without reranking.
- [ ] Generate public synthetic examples and send the field/unit/group contract to Main before real comparisons.

## Task 3 — private execution and delivery

File: `experiments/technical-leaderboard-20261103/run_held_sample.py`; research documentation.
- [ ] Run through the public research functions on already restored normalized rows, preserving source/evidence references.
- [ ] Compare old momentum/volume counts and values; independently check volatility with exact rational variance + sample stdev.
- [ ] Record counts/null reasons, private manifest and remote readback receipt. No public real rows.
- [ ] Run relevant regressions and required guards once; independent review; fix demonstrated issues and recheck affected tests.
- [ ] Commit/push ordinary research branch, open one stacked Draft PR, and post final Main handoff links. No execution branch push.

Ruling: owner explicitly authorized completing this queue without per-step replies; implement the delegated formula/bin choices as
recorded in the spec. Local worktree metadata uses `.git/info/exclude` to avoid an unrelated tracked `.gitignore` change.
Ruling: pytest is absent from the environment; install the test tool into local scratch only. This is test setup, not research data collection.
