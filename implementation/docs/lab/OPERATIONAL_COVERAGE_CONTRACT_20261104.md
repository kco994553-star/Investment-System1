# Operational coverage / 1

`python implementation/tools/operational_qgv_coverage.py --archive <local-qgv-official.json> --output <new-private-file>`

The strict official reader validates a dated publication before the report counts its explicit factor and axis observations. Membership is the publication's non-TARGET code keys. `denominator.count` is code rows, not fixed security IDs; `unique_issuer_ciks` counts the CIKs actually stored on those rows (distinct from the score engine's peer pool). No historical whole-market denominator is inferred.

Report fields: `times` (price basis, input vintage, generation), `calc_version`, source SHA-256, denominator detail, fifteen `factors`, three `axes`, `all_axes`, seven `presets`, missing reason counts and categories. Counts use the same code denominator; NOT_APPLICABLE stays separately visible. Published generic missing reasons cannot identify an absent underlying SEC tag without raw evidence. `raw_input_connection_audit` and signal-date PIT eligibility remain null when that evidence is not linked.

Preset validity is **derived from archived axes**, type weights and the unchanged total-eligibility rule; it is neither an observed stored preset total nor a PIT reconstruction. The official default's derived count can be compared to `published_default_total`. An engine SHA mismatch or unlinked type weights leaves the affected count null with evidence. No score or factor formula changes.

Synthetic example: 2 code rows, 1 issuer CIK, fixed security count null; Q=2, G=2, V=1, all axes=1. A missing financial-profile V factor is NOT_APPLICABLE. Balanced total coverage can be 2/2 while three-axis coverage is 1/2. Those quantities must not share a label.

Results remain private. This contract is for Main's later connection; it creates no UI, endpoint, schedule or publication.
