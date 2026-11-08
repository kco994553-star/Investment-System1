# Sector QGV v0 implementation and preregistration

Owner attachment: Sector_QGV_Custom_Factors_Implementation_20261106.md §§4–9.
Base: ab6a83c3be2276abdcf855c71c5f273926e2dcc4. Research files only; official calc23.1 untouched.

1. Register exact §5 defaults, canonical variants and explicit accounting templates.
2. Add strict, versioned observation/config validation and hierarchical scoring using the shared percentile function.
3. Connect a JSON CLI, preview/save identity, synthetic UI fixtures and held operational snapshot adapter.
4. Run affected tests, held-input coverage, independent review; preserve private results and open Draft PR.

## Comparisons fixed before computation

Reference SQGV-20261106-R0 = sector-qgv-default/0.1.0. Official publication is an additional, separately labelled baseline; it is not a same-policy treatment.
All treatments retain the R0 observation matrix, original universe, mapping, strict missing rule, peer minimum 20, normalizer and gate policy. No historical A/B/C experiment is renamed.

- SQGV-20261106-C1 AXIS_ONLY: all explicit sector/accounting combinations use the existing balanced axis weights 34/33/33; factors and internal weights unchanged. This is the same-policy research baseline.
- SQGV-20261106-C2 FACTOR_ONLY: INFORMATION_TECHNOLOGY/GENERAL replaces sales/EV with EBITDA/EV at the same 30% V role budget. Other contexts unchanged.
- SQGV-20261106-C3 INNER_WEIGHT_ONLY: INFORMATION_TECHNOLOGY/GENERAL V changes E/P,CFO/Mcap,sales/EV from 30/40/30 to 35/35/30. Axis weights and factors unchanged.

Compare unrounded totals/ranks only for common valid rows; additions/losses and full-denominator coverage separately. Raw-factor coverage is independent of peer scoring. Performance window: NOT_REGISTERED_NO_ELIGIBLE_PIT_EXECUTION_COST_INPUT; no return, drawdown or turnover claims. These candidates are implementation diagnostics, not selected winners. R0 remains the initial default. Future performance work requires a dated chronological evaluation manifest before observing returns.

The owner subsequently supplied Sector_QGV_Factor_Catalog_20261106.md. Its Q01–Q13/G01–G12/V01–V15 are design IDs, not operating IDs. Latest implementation §5 overrides its earlier provisional weights and G06 alternative wording. The registry maps all design IDs and preserves differing formulas as variants.

## Q/G partial comparison fixed 2026-11-07 before computation

`SQGV-20261107-D1` is one user-configuration development diagnostic, not a
replacement for C1/C2/C3 or the initial default. Those registered treatments
change axis budgets or V, so they cannot exercise a Q/G factor-selection change.
For INFORMATION_TECHNOLOGY|GENERAL only, keep the Q profitability role at 40%
and change its internal allocation from operating_margin_ttm=100% to
operating_margin_ttm=50%, roa_ttm=50%. Accounting quality=30% and debt/assets=30%
are unchanged. Q's effective within-axis allocations become 20/20/30/30;
Q/G/V axis weights, G, V, gates, strict missing policy, minimum20, peer definition,
normalizer and the entire original Universe504 remain unchanged. No search for
better results, performance selection or default replacement is authorized.

Freeze the retained 2026-11-04 snapshot and reference preview from
`sector-qgv-classified-20261107/run-final`. Compare unrounded Q and G separately
for common valid companies; preserve every original member, additions/losses and
factor-specific valid N. Reuse the saved reference instead of recalculating it.
V, joint/total and performance stay unavailable. Classification additions are a
separate input treatment, applied only after this setting comparison is frozen;
they cannot be mixed into D1's score delta.
