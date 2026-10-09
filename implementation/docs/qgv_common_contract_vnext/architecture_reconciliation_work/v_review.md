# V ↔ Q/G architecture reconciliation · 2026-10-05

**D1/D2 AUDIT / DESIGN / SCORE-NEUTRAL CHARACTERIZATION COMPLETE. INACTIVE; NO PRODUCTION ADOPTION.**

Reviewed local snapshot: `4fb08a05728d83519b72a2bd995669f0cb06003a` in `/workspace/scratch/5f9c0923784f/qgv-policy-reconciliation-2026-10-05`. The parent freshly confirmed the remote baseline. This independent review made no remote, owner, STATE, Handoff, source or golden writes. An active remote owner lease remains a shared-write boundary. The preceding Missing-Data and B4 decision packages were read as established context; they were not rebuilt.

This report recommends **the same control contracts for Q/G/V, with economically distinct V metrics and methods**. KEEP means preserve a justified distinction or legacy behavior; ALIGN means a common control/metadata contract; CHANGE means a result-affecting choice requiring D3 before adoption. An ALIGN recommendation also requires D3 if runtime rejection, scoring, ranking or publication behavior changes.

## Current path and exact sources

Paths below are relative to the snapshot root. Full SHA-256 pins for 15 sources/artifacts are in `v_evidence.json`.

| Layer | Current source/function | Comparison and assessment |
|---|---|---|
| Raw metric | `implementation/src/investment_system/contracts/raw.py:RawFundamentals`; `qgv/raw_map.py:map_raw`, `_obs` | Q/G/V all use the same raw container and observation. `_obs` stores the normalized score in `raw_value`; it does not retain the actual metric. **ALIGN** an additive metric descriptor/lineage sidecar, preserving old bytes. |
| Evidence/admission | `qgv/scoring.py:_weighted`, `score_v_candidates`; `qgv/factors.py:missing_is_not_zero` | Q/G and production V prior reuse `_weighted`. V candidates have a separate admission loop. Numeric N/A is excluded by prior but admitted by candidates. **ALIGN** shared evidence-disposition vocabulary and trace; **CHANGE/D3** any runtime admission policy. |
| Applicability | `qgv/factors.py:factor_applicable`; `qgv/raw_map.py:map_raw`; `qgv/pipeline.py:AnalysisPipeline.analyze_raw` | Financial Q ROIC/WACC exclusion exists. V prior accepts profile; candidate loop has no profile/context argument. No sector-specific V predicate is established here. **ALIGN** context reference and applicability evidence; **KEEP** intentional financial metric differences; concrete V predicates remain unresolved/D3. |
| Normalization | `qgv/raw_map.py:_central_value_score`, `_mos_score`, `_reverse_dcf_score`, inline peer mapping | Q/G use domain-specific ratios/rubrics/linear clips; V mixes value-price ratios, P/E proxies, comparator scores and passthrough fields. **KEEP** different economic transformations. **ALIGN** declared units, direction, horizon, comparator and source/branch metadata. **CHANGE/D3** formula, bounds, polarity or fallback selection. |
| Factor definition | `qgv/factors.py:Q_WEIGHTS`, `G_WEIGHTS`, `V_FACTORS`, `V_INITIAL_PRIOR`, `V_CANDIDATES` | Seven Q, six G and seven V factors are distinct concepts. V research prior/candidates and their lifecycle/constraints are not Q/G production maturity. **KEEP** identities, legacy numbers and research status; do not manufacture symmetry or independent evidence from factor count. |
| Axis reduction | `qgv/scoring.py:_weighted`, `score_q`, `score_g`, `score_v_prior`, `score_v_candidates`, `production_v_score` | Prior and Q/G allow diagnostic partial sums without redistribution. Candidate all-seven completeness is stricter. `production_v_score` returns the prior with provisional lifecycle; its `prior_cov` argument is unused. **ALIGN** policy-referenced reduction trace. **KEEP** recorded arithmetic; **CHANGE/D3** activation, denominator, completeness, tolerances or candidate promotion. |
| Result metadata | `qgv/analysis.py:AnalysisEngine.analyze`; `contracts/models.py:QGVSnapshot`, `FactorObservation`, `VCandidate` | Overall coverage follows Q/G, not V. V table duplicates quality as confidence and coverage; effective weight follows numeric presence rather than admitted contribution. **ALIGN** separate quality, confidence, input coverage, completeness, lifecycle and admitted contribution metadata for all axes. Unknown assessments remain unknown. |
| Profile/evaluator | `personal/weights.py:OfficialRegistry`, `PersonalStrategyVersion`, `effective_tree`; `contracts/strategy.py:custom_profile`; `qgv/analysis.py:AnalysisEngine.analyze` | Personal tree/version/override exists; this snapshot's Analysis takes fixed Q/G/prior weights and has no override parameter. StrategyProfile is a separate parameter pack, with frozen Q/G and V enabling keys. **KEEP** namespace/registry boundaries. **ALIGN** references to existing tree/configuration; production wiring stays D3. |
| Composite/consumers | `qgv/analysis.py:AnalysisEngine.analyze`; `qgv/leaderboard.py:LeaderboardEngine.build`; `validation/historical.py:run_as_of`, `v_coverage_matrix` | Legacy total is the Q/G mean; V is excluded. Board consumes snapshots without rescoring. Coverage matrix counts numeric presence, not valid evidence. **KEEP** current composite/history; **ALIGN** exact producer assessment transported to consumers; **CHANGE/D3** participation/admission/adoption. |

The parent additionally compared a fresh integration tip `11d2f25`: 29/30 selected QGV/Personal/raw/model blobs matched this snapshot. The only different file was `models.py`, adding four optional Technical/Macro lineage fields without changing QGV fields. This narrows source drift; it is **not** full integration or runtime acceptance.

## Seven V economic descriptors, without new numeric policy

These descriptors recover observed code branches, not approved intended methods or requiredness assignments. Existing constants are characterized and preserved, never proposed as fresh defaults.

| V factor | Observed input/method | KEEP / ALIGN / CHANGE recommendation |
|---|---|---|
| `fundamental_value` | DCF value/price comparison, otherwise fixed P/E reference proxy in `_central_value_score` | **KEEP** central intrinsic-value concept distinct from MOS. **ALIGN** explicit branch and value/price unit/date compatibility. **CHANGE/D3** replacing or accepting P/E as the intended valuation method. |
| `peer_relative_value` | Own multiple versus supplied median; `validation/historical.py:run_as_of` supplies a self-inclusive cross-section and selects the upper middle for even samples | **KEEP** peer-relative concept. **ALIGN** multiple definition, peer identity/membership/date and source evidence. **CHANGE/D3** universe, leave-self-out rule, median method, scale/domain convention or sample criterion. No sample minimum selected. |
| `historical_valuation` | Mapper passes the field straight through. Historical candidate produces a clipped comparison of current P/E against one prior P/E | **KEEP** own-history concept separate from peers. **ALIGN** label as the actual legacy two-point comparison and record basis/direction. **CHANGE/D3** true percentile construction, reference window, polarity or normalization. A field name does not establish percentile direction. |
| `sector_context` | Supplied score passes through; historical candidate does not invent it when absent | **KEEP** sector context distinct from issuer valuation and theme. **ALIGN** rubric/period/source reference with Q/G rubric controls. **CHANGE/D3** scoring rubric and numeric admission criteria. |
| `theme_premium_discount` | Supplied score passes through | **KEEP** theme premium/discount concept distinct from sector. **ALIGN** evidence, sign meaning, score scale and rubric reference. **CHANGE/D3** theme taxonomy, rubric, direction and bounds. |
| `reverse_dcf` | Supplied implied growth, otherwise a P/E-derived growth proxy; compared with realized revenue YoY | **KEEP** reverse valuation question distinct from forward G; current function does not mutate G. **ALIGN** forecast/realized horizon, implied-growth source and proxy disclosure. **CHANGE/D3** actual solver, economic assumptions, same-horizon comparison or fallback. |
| `margin_of_safety` | Discounted DCF value against price, otherwise conservative fixed EPS multiple against price | **KEEP** conservative valuation concept distinct from central value. **ALIGN** price/value unit/date and uncertainty-method reference. **CHANGE/D3** conservative value policy, stress/discount formula and fallback. |

Three differently named factors can share one P/E input family: fundamental value, MOS and reverse DCF all have P/E-based fallback branches. That is an observed dependency, not proof of three independent valuation estimates. Future method comparison should include source-dependency/contribution overlap, without automatically merging factors, changing weights or adding a penalty.

## Reproduced counterexamples and score neutrality

`v_evidence.json` records **22/22 characterization checks**, plus **13/13 existing selected test functions** executed directly with their original assertions. The installed Python lacks `pytest`, so no pytest suite, Actions, real PIT/OOS or integration run is claimed. No live data was used.

Independent replay: `PYTHONDONTWRITEBYTECODE=1 python v_verify.py /path/to/exact/repository`. The supplied `v_verify.py` reruns all 22 checks and 13 existing assertions; a second successful read-only execution is recorded in `v_replay.json`. Output should remain outside the source repository.

| Counterexample | Actual current observation | Contract implication |
|---|---|---|
| Complete seven V factors at 70 | Prior and three candidates each return 70 | Preserve golden complete-input arithmetic while comparing contracts. |
| Fundamental value absent | Prior 52.5/PARTIAL; candidates null; Q/G-complete snapshot overall READY, total 70 | Overall readiness is not V readiness. A typed axis trace can state this without changing old coverage. |
| Fundamental value numeric 70 with N/A quality | Prior 52.5/PARTIAL; every candidate 70 | Candidate and prior evidence admission differ. A shared contract must explicitly retain legacy distinction until approved. |
| Fundamental value numeric 70 with PIT_UNAVAILABLE | Prior omits it, but V table reports effective weight 0.25 and identical confidence/coverage `PIT_UNAVAILABLE` | Displayed effective weight is not admitted weight; quality is not a confidence assessment. |
| DCF 120 and price 100 | Normalized FV 75; observation `raw_value` also 75 | Actual raw valuation metric is lost in this field; do not reconstruct it from score. |
| Historical field 10 versus 90 | Scores remain 10 versus 90 | The mapper is monotonic passthrough. Inversion cannot be declared until the percentile's economic direction is established. |
| Theme input 1,000 | Mapped score remains 1,000 | Common score-scale contract is missing. Clipping/rejection would change behavior and remains D3. |
| Peer median −20; own multiple 10 | Peer-relative maps to 100 | Truthiness allows a negative comparator; admissible domain and sign convention are unresolved, not approved by numeric presence. |
| Own multiple zero | Missing, due to truthiness test | Zero handling belongs in a declared metric-domain rule, not incidental control flow. |
| No DCF; price 100; EPS 5; revenues 120/100 | FV 50, MOS 0, reverse DCF approximately 100 | All three use the same P/E family but encode different formulas; fallback dependency must be disclosed. |
| Supplied own and peer multiple both 20 | Peer-relative 50 | Mapper cannot establish comparator identity, self-exclusion or sample admissibility. No coverage cutoff is inferred. |
| Source-extracted peer list [10, 30] | `run_as_of` chooses 30, the upper middle | Correcting to another median definition is a numeric method replacement requiring D3. |
| Change only reverse DCF implied growth | G factor mappings unchanged | Maintain valuation/growth result isolation while declaring cross-axis input dependencies. |
| Change only FV normalized score 70→100 | V 70→77.5; Q/G total stays 70 | Preserve legacy V-excluded composite; no implied Composite approval. |

All **7,770 tracked files** were SHA-256 digested before and after probes/regressions with identical aggregate digest. Golden hash stayed `ed01c7f25e6a01b23c9f474b9f66f1f204828834bbdbc25efc286d96050c5040`. Source-byte preservation proves this review did not change legacy inputs, code or fixtures; it does not validate a future method.

Key source SHA-256:

| Source | SHA-256 |
|---|---|
| `qgv/raw_map.py` | `79995e768babddf8f7d85e0d10a4a9bb3f7571138520975e569670adea1ff0ac` |
| `qgv/scoring.py` | `1aa4802a65175210be802c7d1d08e17e8af5cfa40a9b6faaa014447354d9e629` |
| `qgv/analysis.py` | `bfd4e1310dde9f908f60a8a2030cb9928f4267f73180c3eb5b12bc7947e3de88` |
| `qgv/factors.py` | `0df21503c383e3ff79a91bf143c003a8e131718918eb1fe57abecea7e6781a6e` |
| `validation/historical.py` | `02315a38e102bc312478dd1f00da401865db42d60423b21371b05879849a4aa8` |
| `personal/weights.py` | `2bfdb278feaa3892e9c2b0129419b93c7725570a81b37fe5d6643228357b14f5` |

## Smallest next executable D1/D2 contract step

Create an **inactive V normalization/metadata descriptor manifest** using the existing common reference shape and seven descriptors above. No new engine, class, ProfileConfig, normalization formula or score computation is needed. Each record should pin:

1. Existing factor and observed method/branch reference; source path and SHA-256.
2. Metric input fields, unit/horizon/price-basis/comparator evidence; unresolved fields explicitly unassessed, without assuming a unit or policy.
3. Observed transformation and output scale, with separate authority/approval reference. A recovered legacy formula is not approved intended semantics.
4. Quality/admission disposition and applicability context references; profile weights do not supply their truth.
5. Separate confidence, input coverage, method completeness, contribution, lifecycle and consumer-admission references. No legacy READY→valid or non-null→eligible translation.
6. Legacy replay result reference/hash, preserving literal fields and arithmetic; common Q/G/V control shape with V-specific economic parameters.

Verify the inactive manifest by source-pinned replay and asymmetric V-prior/candidate cases. Requiredness, numerical criteria and output admission can remain unresolved while descriptors/lineage close. This finite work is independent of G method approval, Composite and WeightOverride runtime wiring. It must be claimed through the existing owner/lease protocol before shared publication; this review itself does not acquire that lease.

## D3 choices remain concrete and separate

- Which actual V methods are intended, including fundamental/MOS P/E fallbacks, reverse DCF proxy/solver, own-history percentile versus two-point comparison, and peer universe/median convention.
- Which numerical normalization, metric-domain, polarity, coverage/confidence rubrics and applicability predicates are authorized. No thresholds, weights, minimum samples or default values are supplied here.
- Whether/when the common admission and result-safety contract is activated for V prior/candidates and consumers. A common design does not erase deliberate lifecycle differences or authorize partial scores as valid ranking inputs.
- Composite participation, candidate promotion, factor-node editability, Personal WeightOverride runtime wiring and calculation/legacy migration remain downstream D3. PIT/Frozen/Holdout/Official/canonical merge boundaries remain protected.

**Recommendation:** complete the additive inactive V descriptor manifest first. Seek D3 approval only for its unresolved method/policy choices when their evidence and impact package are reviewable. No blocker in one method prevents source/metadata convergence for the other factors.
