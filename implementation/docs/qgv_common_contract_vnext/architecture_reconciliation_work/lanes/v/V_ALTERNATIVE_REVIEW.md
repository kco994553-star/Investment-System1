# V Alternative Impact Analysis — bounded continuation

STATUS: D1_D2_IMPACT_COMPLETE / INACTIVE / NO_METHOD_SELECTED.

This continues the seven-factor V descriptor and KEEP/ALIGN/CHANGE review, rather than redesigning V. The parent freshly authenticated canonical, owner, Global and PR refs. This lane read the exact local code snapshot `4fb08a05728d83519b72a2bd995669f0cb06003a` and existing reconciliation artifacts that match remote `df5c70447dfa83805395b7cbbcacbc2024e77f3d`. The active owner lease was respected: no owner source, STATE, receipt, Handoff, old evidence, golden, Global or remote write occurred.

New files in this lane are an audit sidecar, executable replay, source-run results and machine-readable impact matrix. They are not a runtime registry, new engine, profile configuration, policy activation or production method selection. Method source anchors characterize observed code. Registered method IDs/versions remain unknown where the legacy architecture has none.

## Seven identities and current methods

The existing seven V factors, prior/research weights, legacy results and `(Q+G)/2` composite are preserved.

| Factor | Actual current normalization/source | Current metadata and limitation | Grounded alternative comparison |
|---|---|---|---|
| `fundamental_value` | `_central_value_score`: clipped supplied DCF/price comparison, otherwise fixed P/E proxy | Notes/stamp/quality; no assumptions, unit/per-share/model authority or registered method ID | Existing supplied-value branch vs existing P/E fallback; no DCF solver invented |
| `peer_relative_value` | Supplied own/median multiple difference; `run_as_of` supplies self-inclusive book median, selecting upper middle at even count | Multiple/cohort/date comparability unresolved; book membership is not proven sector peers | Supplied comparator and actual runner cohorts; changing median convention/peer-universe policy remains uncomputed |
| `historical_valuation` | Supplied field passthrough; runner computes clipped current vs one prior P/E comparison | A distribution percentile, polarity and aligned historical basis are not established | Existing passthrough inputs and actual two-point helper; true percentile family has no computed impact |
| `sector_context` | Supplied `sector_context_score` passthrough | No admitted rubric/taxonomy/domain/version/vintage | Existing present/missing input behavior; new rubric family uncomputed |
| `theme_premium_discount` | Supplied `theme_premium_score` passthrough | Theme meaning is distinct from sector, but direction/rubric authority unresolved | Existing passthrough behavior; new mapping uncomputed |
| `reverse_dcf` | Supplied implied growth or P/E proxy compared with realized revenue YoY | No actual reverse-DCF solver or same-horizon forward comparison established | Existing supplied-implied branch vs P/E proxy; solver family uncomputed |
| `margin_of_safety` | Conservative supplied DCF/price branch or fixed EPS-multiple proxy | Conservatism policy/unit basis unresolved; P/E input family overlaps central value and reverse proxy | Existing supplied-value vs existing fallback; no new stress/discount formula |

The old inactive descriptor's reverse-DCF input label `implied_growth` is a field alias mismatch: the actual public `RawFundamentals` field is **`reverse_dcf_implied_growth`**, and the mapper local variable is `implied`. The new sidecar records the actual field and this additive correction. The original descriptor bytes are preserved.

There is no concrete **PeerDerivedV weight family** in this code snapshot. `test_peer_derived_v.py` tests filling the peer factor with a book comparator; it does not define a fourth V weight set. `AnalysisEngine.peer_weights` is normalized snapshot metadata and is not wired into V factor weights. Inventing such candidate weights would contradict the source.

## Actual-source numeric impacts

Numbers below are synthetic stimuli run through the existing source. They do not estimate issuer intrinsic value, choose normalization, establish appropriate defaults or supply calibration. Full precision and exact source pins are in `V_ALTERNATIVE_RESULTS.json`.

| Scenario | Factor/reducer impact | Legacy composite |
|---|---|---|
| Supplied DCF 120 / price 100, EPS 5, supplied implied growth .08 | FV 75, MOS 33.3333, reverse 90; V prior **66.0833** | 82.0633 |
| Same price/EPS/revenue with existing P/E fallback branches | FV 50, MOS 0, reverse 100; V prior **58.5**. The 7.5833 difference from the row above is a **combined DCF/MOS + reverse-input branch-family effect** | 82.0633 |
| Controlled DCF/MOS comparison, holding reverse P/E proxy constant | DCF branch prior **68.0833** vs no-DCF fallback **58.5**, delta **9.5833** from FV/MOS branches only | 82.0633 both |
| Same DCF with reverse P/E proxy vs supplied implied growth .25 | Reverse 100 vs 33.3333; V prior **68.0833 vs 54.75** | 82.0633 both |
| Sector input absent | Numeric V presence 6/7; prior **60.0833 / PARTIAL**; all three all-factor candidate reducers return null | 82.0633 |
| DCF and EPS absent; no supplied implied growth | Numeric V presence 4/7; prior **26 / PARTIAL**; all candidates null | 74.5633; EPS also affects G, so this is not a V-only composite comparison |
| Supplied historical score input 20 vs 80 | Historical score 20 vs 80; V prior **58.5833 vs 67.5833** | 82.0633 both |

The source uses different factor loop order for the prior and the initial-prior candidate. A last-bit difference in full-precision sum is preserved literally; it is not an economic alternative or a new rounding/tolerance policy.

All available concrete weight candidates were compared on two nonuniform V vectors using the existing golden observation topology. Only the seven V outputs were changed in memory; no golden was written.

| Existing candidate | Company A: central/reverse strength | Company B: safety strength | Diagnostic V comparison |
|---|---:|---:|---|
| Initial prior | 73.5 | 61 | A higher |
| Equal research | 62.857142857142854 | 62.857142857142854 | **Exact tie** |
| MOS tilt research | 57.5 | 67.5 | B higher |

This is a genuine weight-sensitivity reversal between prior and MOS tilt, not a recommended winner. The equal result has an explicit exact-score tie group; source/input order is not treated as a ranking preference. These hypothetical V-only comparisons do not describe the current Leaderboard, which sorts the unchanged Q/G composite. No tie-break policy, threshold, weight or tolerance is introduced.

## Peer, sector and sparse-history effects

The actual `run_as_of` provider path was exercised on synthetic filing/price data, with records saved only outside the repository.

| Exact current method scenario | Result |
|---|---|
| Book P/Es `[10, 30]` | Upper-middle median 30; same issuer's peer score 100 and V 73.3333 |
| Add a low-P/E member: `[10, 30, 10]` | Median 10; same issuer's peer score 50 and V 65.8333 |
| Swap synthetic sector labels with unchanged numerical membership | V factors unchanged; the implementation does not construct sector-relative peers from these labels |
| Remove old price while keeping current filings/prices and cohort | Historical factor becomes missing; same issuer V 73.3333 → 62.0833, a loss of **11.25** from the missing weighted historical contribution; no redistribution |
| Add a future price and a later-filed EPS value | Current factor results unchanged in this resolver/provider path; future values are excluded |

The two-point historical helper returns 75 in the complete fixture because old P/E uses prior EPS 1 while current P/E uses EPS 2 at unchanged price. This is a reproducible **two-point P/E change score**, not a percentile distribution. Old-price and prior-EPS selection are separate source operations; the replay does not prove exact same-period, currency or split-basis comparability.

These fixtures demonstrate cohort-membership sensitivity and missing-history contribution loss. They **do not estimate actual sector-performance bias or its direction**, which remains unassessed. The current book comparator lacks the method authority needed to call it economically comparable sector peers. Existing `peer_confidence=LOW` is a legacy sample-count heuristic, not a new confidence assessment or evidence of PIT correctness. No sample minimum or peer threshold is selected.

## Missingness, method validity and consumer safety

The previous partial-score/N/A risk is extended with new method-lineage evidence:

- A numeric `NOT_APPLICABLE` observation is excluded by the prior but accepted by all-seven candidates. Numeric presence and admitted contribution differ; the old discrepancy is retained in the impact matrix, not repaired.
- Numeric `VERSION_MISMATCH` and `CALCULATION_ERROR` observations still yield finite prior/candidate results because these quality states are not excluded by the legacy reducers. This does not make them valid.
- A producer with both G and V `VERSION_MISMATCH` observations still yields total 70 and is consumed as Leaderboard rank 1 without rescoring. Factor method identity/version/semantic validity are not certified by the numeric total.
- The provider-run historical path excludes the future synthetic inputs, but direct `AnalysisPipeline.analyze_raw` with a future-stamped raw input still produces numeric V and total at an earlier `as_of`. Provider-side availability filtering alone does not protect every entry point. No PIT check was weakened or production guard added.

Existing V table `confidence`/`coverage` strings duplicate `QualityState`, and the overall snapshot confidence defaults to `MEDIUM`. They are recorded as literal legacy metadata. In the new sidecar, **confidence assessment, input coverage, semantic completeness, method validity, ranking eligibility and publication eligibility remain null**. No READY/SYNTHETIC/non-null literal is upgraded into validity or consumer permission.

The integration point remains **producer assessments → consumer-specific admission** under B2/B3/B5/B6. Consumer code should not recalculate QGV economics. Numeric coverage, complete score, valid score, ranking and publication are independent concepts. Activating their policy remains D3.

## Independent candidate dispositions

Detailed economic meaning, data availability, PIT reproducibility, peer/historical comparability, complexity and manipulation-risk grounds are in `V_IMPACT_MATRIX.json`.

| Family/candidate | Verdict | Boundary |
|---|---|---|
| Seven identities/prior/history | KEEP | Legacy identity/research/history preservation |
| Shared control + raw/normalized/assessment metadata separation | ALIGN | Inactive sidecar only; runtime change needs approval |
| Supplied DCF vs P/E fallback | MORE_EVIDENCE_REQUIRED | No branch chosen; valuation basis/authority gaps remain |
| Supplied reverse implied growth vs P/E proxy | MORE_EVIDENCE_REQUIRED | No solver or target horizon approved |
| P/E proxy relabeled as executed reverse-DCF solver | REJECT | Unsupported method interpretation; preserve disclosed legacy proxy |
| Supplied comparator vs book-cohort peer family | MORE_EVIDENCE_REQUIRED | Membership/median/domain policy unresolved |
| Historical two-point vs percentile family | MORE_EVIDENCE_REQUIRED | True percentile impact explicitly uncomputed |
| Sector/theme rubric family | MORE_EVIDENCE_REQUIRED | No invented rubric or numeric mapping |
| Existing prior/equal/MOS research weight comparisons | KEEP | Preserve comparisons; no candidate promotion/Official weight |
| Producer-validity → consumer-safety activation | CHANGE_RECOMMENDED | Technical recommendation only; depends on B2/B3/B5/B6 D3 policy approval |

No economic method was prematurely selected. Distinct candidate families without a grounded numeric mapping remain qualitative and uncomputed; missing scores are not filled with fabricated outputs.

## B1 and minimal policy package

Lineage evidence is stronger: actual branch identities, raw inputs, sparse-history effects and consumer failure modes are source-pinned. It does **not** supply requiredness authority. B1 remains **MORE_EVIDENCE_REQUIRED**, with no additional REQUIRED/OPTIONAL/CONDITIONAL role assigned. Unresolved horizon, fallback, valuation basis, comparator and historical direction remain blockers for semantic factor promotion.

Keep the next V decisions within two existing groups:

1. **V1 — method/normalization families:** intended supplied-value/P.E authority, reverse implied-growth source/solver horizon, peer cohort/median convention and historical two-point versus distribution semantics. Numerical parameters are not proposed here. G1/G2 provide cross-axis horizon and fallback input dependencies.
2. **V2 — metadata and admission methodology:** raw versus normalized output, confidence/quality, coverage/completeness and producer validity to consumer admission. B4/B7 isolation is retained, and activation depends on the consolidated B2/B3/B5/B6 contract. Concrete method-validity predicates also depend on V1 semantics.

This package does not authorize method replacement, normalization, requiredness, ranking, composite, WeightOverride, calculation migration, historical rewrite, Holdout use, PIT relaxation, merge or deployment.

## Verification and next executable work

**21/21 new continuation checks PASS.** The prior 22 characterization and 13 regression checks were reused as evidence and not rerun. All 7,770 tracked source files retain aggregate SHA-256 `e2c00ceefad0442d66f50863ab36f83806bb74c54a18514ad6db02d2693ed6dd`; the 18 selected source/artifact pins match before and after. Source/golden/history files remain unchanged. The comparison scripts produce only new external evidence and synthetic record stores. No Actions, real issuer valuation, full PIT/OOS or production migration is claimed.

Replay outside the source repository:

```bash
PYTHONDONTWRITEBYTECODE=1 python v_alternative_probe.py /path/to/exact/snapshot /path/to/output
PYTHONDONTWRITEBYTECODE=1 python build_impact_matrix.py /path/to/output
```

Next independent D1/D2 work is to compare these exact source/hash-bound V findings with the G lane, annotate the common method/result/consumer contract, and prepare the minimal G1/G2+V1/V2 policy package without selecting numerical methods. The parent will perform the independent review and scoped delivery according to ownership.

This is a **manual Work execution**. It counts as no scheduler hop. Actual scheduler continuation remains **0/2 / UNVERIFIED** pending authentic HOP1/HOP2 receipts and exact output-hash handoff. This lane neither wrote scheduler state nor used automation verification to stop the independent V evidence work.
