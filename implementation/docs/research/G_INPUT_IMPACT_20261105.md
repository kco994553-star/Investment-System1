# G input impact audit / qg-input-impact/1

The auditor consumes two normalized snapshots with identical membership, issuer/profile/state/industry/version metadata. It calls the unchanged official Q/G scorer and independently reconstructs rank arithmetic as exact fractions. No weights, gates, source data or scores are changed by this audit.

G peer policy is **GENERAL-wide**, not industry-relative. FINANCIAL uses its separate profile pool. Q's industry rule must not be described as G's rule. One eligible point per issuer CIK is used; CIK is not a security ID. TARGET rows replace their issuer point for their own evaluation and are reported separately from the fixed operational-code denominator.

For each submetric retain own input, direction, comparison-set membership, less/equal/n and percentile `100*(less+(equal-1)/2)/(n-1)`. Then retain factor means, available factor weight, official unrounded axis float and exact rank fraction. Inputs have already undergone the official six-significant-digit metric normalization; the audit does not claim to undo that normalization. The G score itself is not rounded before comparison.

`input_changed` records any metric edit independently. `effect_kind` and direct/indirect counts use exact own-input and peer contributions, so a Q-only input edit cannot make a peer G change direct. Mixed nonzero contributions count once under direct; unavailable scores/transitions remain unattributed. Ordering is called preserved only after comparing all submetric less/equal/n/percentile tuples. Offset contributions and changed ranks with unchanged axis scores are explicit. `peer_crossings` names the issuer and metric that crossed a row's unchanged input. The counterfactual first changes the row's own inputs against old peers, then the peers; this order is an explanatory convention and not a performance or improvement claim.

Checks cover fixed membership/config/version, Q invariance, financial G invariance, factor-valid sets, comparison-set members and unchanged factors. A population change or unsupported calculator version rejects this same-population audit. Missing scores remain null; no neutral value is inserted.

## Main synthetic example

Ten GENERAL issuers, five in each of two industry groups, have acceleration0..9. Four other G factors are tied at50. Changing only issuer0's acceleration to9.5 moves its G from42.5 to57.5 and changes the other nine GENERAL scores through the same global pool. An unchanged issuer1 moves by exactly−5/3 points; a separate financial pool is unchanged. These are synthetic values, not company results.

Fields: `before/after.score_unrounded` (0–100 points), `score_exact` and `delta_exact` (numerator/denominator), `changed_metrics`, `peer_basis`, `peer_count`, `factor_details`, `peer_crossings`, `unaffected_checks`. The score movement is not labeled an improvement. Real rows and input/config/source differences stay in the private handoff.
