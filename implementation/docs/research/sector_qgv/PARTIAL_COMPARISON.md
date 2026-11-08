# Q/G partial comparison, retained input continuation

The producer contract `sector-qgv-axis-comparison/1` is an additive artifact;
`sector-qgv-main-response/1` remains unchanged. Main can join `rows.company_id`
to the existing detail view. Each axis has unrounded before/after/delta,
common_valid, transition, missing reasons and factor details. Details include
canonical variant, role/inner/within-axis/nominal-total weights, before/after
factor score and valid_n. Keep null as unavailable. All original rows remain;
UI filters must not change the underlying comparison or peer sets. No axis rank,
QGV total or market rank is invented. Official Q gate percentile is not an axis.

`partial-synthetic-comparison.json` contains a real engine-generated synthetic
response. Its source is `partial-synthetic-snapshot.json` and settings are in
`partial-synthetic-config.json`. The fixture's Q changes are a configuration
diagnostic, G is unchanged, V/total are null. The retained-reference CLI shape:

```json
{
  "mode": "normalized", "data_kind": "PRIVATE", "request_id": "D1",
  "snapshot": {"path": "/private/snapshot.json", "sha256": "<hash>"},
  "config": {"...": "saved canonical sector-qgv-config/1"},
  "axis_comparison": {
    "comparison_id": "SQGV-20261107-D1",
    "before_preview": {"path": "/private/reference-preview.json", "sha256": "<hash>"},
    "before_config": {"...": "original saved canonical configuration"}
  }
}
```

Use existing `tools/sector_qgv.py --job ... --output /private/new-directory`.
It verifies pinned bytes and reference input/config identities, calculates only
the changed setting, and writes `axis-comparison.json` plus normal preview/save
artifacts. A saved setting is not an operational model change. The classification
input treatment instead sets `input_treatment=true`, supplies pinned
`before_snapshot`, and keeps before/after config equal. Never mix this with D1.

## Frozen real diagnostic

D1 was recorded before computation, 2026-11-07T02:12:39.762815+00:00, using
2026-11-04T02:29:35.166580Z, original Universe504. Reference #505
`aa9c4484e65baced0dd06622eb64c71e33a9c2fd`, 501 raw-company rows,
14 variants/5439 observations. IT GENERAL profitability role40% changes only
its inner margin/ROA mix from100/0 to50/50. Common Q206:49 changed,157 unchanged;
common G280:all unchanged. Gains/losses0, V/joint/total0 computed rows.
An independent read-only reviewer checked all504 rows and
`delta Q = 0.2*(ROA score - operating-margin score)` for the affected49.
No company-specific real result is in this repository.

## Separate classification input treatment

The retained source primary-business descriptions support13 additional exact
SIC rules covering14 rows, research correspondence version0.2.0. Original0.1.0
rules and existing mapped rows are preserved. Named prepared foods/oils/cleaning
supplies, coatings, leather products, industrial ordnance/fabricated metals/
controls, electric generation, motor parts distribution, construction supply,
restaurants and equipment leasing are mapped under the existing activity-based
principle. This is SEC primary-activity evidence, not verified segment weights,
official GICS, representative security or legal-history proof. Broad/mixed,
REIT, stale/contradictory activity and accounting cases remain unresolved.

Mapping351→365; factor-scored companies291→305; factor-score observations
3526→3724; Q206→213; G280→293. New mapping has7 newly valid Q and13 G;
existing common Q125/G173 also change because their valid peer sets expand.
That is peer rescoring, not new financial inputs or an improvement claim.
Raw observations and official Q gate inputs are unchanged, recomputed0.
V/joint/total remain0/504 computed rows. Full-market95%, historical PIT and
performance are not measured. Bank17, insurance18, broker7, energy14,
telecom3 mapped members remain below20 even before factor-specific exclusions;
prices cannot resolve these Q/G peer shortages.

139 classifications remain unresolved (40 unreviewed exact SIC,27 REIT and
72 other reasons). Private input-requirements.json preserves every company,
required Q/G input field/period/unit, source scope, group shortage and
representative issue. No unknown member is deleted from504.

Official calc23.1 is not the same-policy baseline: it has different factors,
normalization groups/8-peer fallback and missing-axis rules. Its Q percentile
is retained only as the approved gate input. This comparison changes none of
those operating rules or the initial sector default. Return/drawdown/turnover
performance is unavailable.

## Main integration and validation

Main #507 reader/server connection remains pending; the offline producer works
without it. Add `tests/test_sector_qgv_partial.py` to CI during Main integration;
no new dependency, shared guard or workflow changes from Codex. The new addendum
regression is in the existing classification test module. Existing completed
#505/#509 tests are not repeated. Main #508 pure helper is connected separately
in #504; financial11 prices remain pending and belong to November2, not this
November4 comparison.
