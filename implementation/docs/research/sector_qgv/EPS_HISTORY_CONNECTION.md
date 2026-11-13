# Annual diluted EPS input connection — 2026-11-13

Owner follow-up to #534 f79e9776929144e12bd3001e2ba57ef89e8b2cf8.
The previous real execution cda233a4b570f40bd368bd68d9182dd4f589869b and all
original inputs/results remain immutable. Model IDs, fixed recipes, weights,
strict policy, minimum20, official-Q gate and stored deciles are unchanged.

## Identified defects and bounded repair

`sector_qgv_held` did not extract annual diluted EPS or request
`eps_diluted_cagr_3y`. It now uses existing calc23.1 `_Facts.annual`, fiscal
anchors and `_Company.eps/share_factor`; no EPS reconstruction engine is added.
Only annual-form350..380day EPS in currency/shares is accepted. Fiscal0..3
observations are all required; positive endpoints use the existing CAGR kernel.
Negative/zero endpoints are not imputed or assigned alternate growth factors.
Same-filed latest conflicts cannot resurrect an older/alternate-concept value.
The reported value, normalization factor, concept, accession, filing date,
period, unit, original acquisition and hash-bearing source reference survive.
Filing dates stay date precision; acquisition is not initial publication.
TTM EPS is still not created from unsupported quarterly/cumulative arithmetic.

Historical issuer EPS and valuation-date security prices have different identity
requirements. The fixed333 scorer previously demanded the valuation security ID
for every currency/share input. A new optional reviewed history proof makes that
requirement precise for annual EPS growth only. Existing validated-security paths
remain compatible. Common BPS growth and V are not silently opted into this proof.

## Optional historical-common-share-basis/1

An input record may carry `historical_share_basis`:

- `schema_version`, `status=VERIFIED`, `issuer_id`;
- `class_basis`: evidence-backed issuer-local common class/basis, **not** an
  exchange/security ID; `attribution=COMMON_DILUTED`;
- `adjustment_basis`: reviewed common normalized basis across four fiscal years;
- `valid_from`, inclusive `valid_to`: must cover all fiscal observations;
- `source_available_at`, `retrieved_at`, nonempty `provenance`;
- `normalized_components_hash`: canonical digest of the four normalized
  component records, including original source/period/value/basis metadata.

This is a trusted reviewed-input assertion, not proof obtained merely by giving
an issuer or ticker an internal ID. Automated issuer-level SEC concepts, a single
current trading symbol, or absence of a split fact do not establish all common
class attribution/continuity. Existing split normalization alone is insufficient.
Proof outside the retained input cutoff is rejected; later review/acquisition
must use a separate versioned availability context rather than backdating.

Output optionally includes the proof, `historical_components_hash`,
`historical_period_start`, and `price_join_eligible=false`. Raw/score validation
rechecks issuer, component binding, periods and availability. An absent/invalid
proof with no validated legacy share basis yields
`HISTORICAL_SHARE_BASIS_UNCONFIRMED`, value null. A numeric endpoint diagnostic is
explicitly `adopted=false` and is never passed to the scorer as a valid value.

| Calculation | Required identity/capital scope |
|---|---|
| Annual diluted EPS CAGR | same issuer, evidenced common/diluted historical class and normalized basis over FY0..3; no evaluation price or listing identity |
| E/P or B/P | valuation-date validated security, compatible EPS/BPS class/ADR/split basis and same-date price; historical proof alone insufficient |
| CFO/issuer market cap | issuer numerator plus all corresponding common classes, actual class shares and prices/currency/actions; no annual EPS proof substitution |
| EV ratios | previous market-cap scope plus exact debt/preferred/NCI/cash components; missing components not zero |

## Existing CLI and incremental reuse

`sector_qgv.py --job PRIVATE_JOB.json --output FRESH_PRIVATE_DIR` accepts the
existing `held-input-repair` mode with `transform_only=true` and a pinned repair
plan `projection=EPS_HISTORY_ONLY`. It emits only new snapshot, connection audit
and file manifest; no unrelated sector preview is recalculated. Existing
`dual-study` jobs consume the new evaluation/reference snapshots afterwards.
A retained repair audit may reuse identical source hash/record/template/cutoff
under the same code hash and projection. Other observations, members,
classification and official gates are preserved byte-for-value.
Input adapter `held-sec-annual-eps/1` is appended to the new input version.
Model/recipe versions do not change because formulas/policy did not change;
new input/code/config bindings and result hashes distinguish executions.

## Review / delivery

Main keeps null values and the diagnostic reason; numeric endpoint candidates
are not core raw observations, adopted factors or coverage gains. Existing333
contract handoffs: #437 comments6849630620,6850109806,6850174335. This optional
history evidence is private input provenance, not a new public security ID.

Synthetic tests cover extraction, full history, YTD exclusion, unit/future/
latest conflict, split direction/no double application, nonpositive endpoints,
proof issuer/class/time/hash/period mismatch, historical scoring without a price
join, and EPS-only CLI preserving unrelated inputs. Actual source-based counts,
issuer-set intersections and reproduction paths are supplied in the private
follow-up report. No external acquisition, operating publication or model
adoption is performed.
