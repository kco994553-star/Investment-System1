# QGV architecture reconciliation — inactive control contract

Status: D1/D2 design only. This contract does not approve B2/B3/B5/B6, bind requiredness, change formulas or activate a consumer policy.

## Shared architecture and authority

Raw Metric → source/PIT/integrity admission → economic applicability and method-required inputs → method/version-pinned normalization → Factor result → Q/G/V axis result → explicit ProfileConfig/WeightOverride → isolated Official/Custom evaluation → consumer admission.

The arrows are dependency boundaries; they do not require every module to be collapsed into one class. Reuse current factor IDs, source stamps, hashes, result namespaces and profile contracts. Upstream applicability facts and evidence validity must not depend on downstream weights or ranking demand. Unresolved method semantics remain explicit rather than becoming OPTIONAL/N/A.

| Layer | Inactive alignment requirement | Domain authority still required |
|---|---|---|
| Raw/input | Units, horizon, currency, accounting basis, source-vintage and actual availability are explicit input-contract refs | Selecting new metrics, forecast providers, negative-base treatment and actual applicability predicates |
| Admission | Evidence is assessed before contribution weights; zero weight cannot waive relevant PIT/integrity/provenance | Production rubric, reason/scope bindings, thresholds and completeness criteria |
| Method/version | Same factor with changed method/horizon/fallback/normalization has distinct immutable method lineage | Replacing G, fallback or V formulas; calculation migration |
| Normalization | Every axis has traceable input, output direction, units/domain and versioned normalizer; economic formulas may differ | Numeric endpoints/defaults/caps, comparison cohorts, percentile direction/window |
| Axis results | Numeric existence, partial/complete and scoring validity are independent assessments; lineage survives projections | New completeness/validity rule adoption |
| Profile/evaluation | Existing authorized numeric weight/contribution changes stay isolated from method and Official identity | Production WeightOverride wiring, formula/Composite changes |
| Consumer | Producer assessment refs are consumed once; Leaderboard does not duplicate economic calculation meaning | Activation of admission criteria, ranking cohorts, publication decisions |

## KEEP / ALIGN / CHANGE semantics

- KEEP preserves a justified economic or historical distinction with its current lifecycle and evidence.
- ALIGN is a proposed shared contract/control representation. It does not authorize production semantics or even a metadata migration if that migration changes consumer identity or interpretation.
- CHANGE marks a result-affecting method/policy question requiring D3. Technical findings and successful legacy-characterization tests are evidence, not approval of the observed behavior or a repair.
- Historical legacy reports retain exact prior identity; new method descriptors may annotate a separate audit sidecar without renaming or recomputing past results.

V can retain valuation-specific multiples, yield, historical comparison, reverse-DCF and margin-of-safety concepts. Its source admission, applicability, completeness, method/version lineage, profile isolation and consumer responsibilities should be compared with Q/G through one explicit contract. Structural uniformity never justifies translating a revenue-growth normalizer into a valuation normalizer.

## Minimum next evidence task

Compile an inactive input-unit/domain/horizon evidence manifest for the G/fallback and V choices identified in the attached reports. Pin the exact current source and report hashes; distinguish economic metric, computed proxy, advertised label, normalization and consumer interpretation. Include negative/zero denominators, loss transitions, absent prior-period inputs, financial issuers and unresolved historical-percentile direction. Compare alternatives without selecting numeric bounds, assigning actual requiredness, enabling dispatch, recalculating history or changing ranking. Reuse the existing common-contract factor map and accepted audit receipts; do not restart broad audit or the scheduler canary.

Production score migration and real PIT/OOS validation are not started. Existing two-hop automation verification is a separate finite plan; this manual architecture review contributes zero actual scheduler hops.

