# Evaluation population / reference population research v1

Owner 2026-11-10 authorizes this separate research comparison. Existing model,
defaults, official output and prior results remain unchanged. No new collection.

## Design and contract (Main draft)

`sector-qgv-reference-study/1` evaluates the original population with the common
engine. `research-reference-additive/1` adds eligible external issuer observations
only to preregistered sector × accounting × variant pools. Existing evaluation
issuers always retain their original inputs and scoring representative. An
external source cannot replace them. Classification remains 투자시스템 공통 10섹터.

We reuse the existing engine on an internal composite input, then project **only
evaluation rows**. This avoids a second normalizer/formula/price engine. Broadly
changing all pools or taking already-expanded scores would confound this study.

Both `evaluation_population` and `reference_population` carry id, version,
members_hash, valuation_date, as_of, row/issuer counts and input_hash. Reference
membership also has `group_members_hash`: each variant's effective issuer set is
explicit, including original eligible representatives. Source catalog membership
is not eligibility. Missing/invalid observations and unresolved mapping remain
excluded from that factor's reference N, with reasons, without deleting targets.

Admission requires the same evaluation day, availability cutoff, model, formula
and normalization versions; validated observation period/unit/availability;
confirmed matching sector/accounting mapping with evidence; stable issuer ID;
one evidenced scoring representative. Preserve classification knowledge time
and distinguish retrospective reconstruction from historical system PIT. Fiscal
end dates may differ under the **existing** factor-period contract; there is no
new same-fiscal-year-end requirement or relaxed freshness rule.

Study id `PEER-POOL-95-20261110-01`, version `1`. First treatment is fixed before
execution to the nine previously documented sufficient groups: ENERGY/GENERAL
(operating_margin_ttm, accruals_assets_ttm, debt_assets, revenue_cagr_3y,
roa_improvement_3y); FINANCIALS/BANK and FINANCIALS/INSURANCE (roa_ttm,
roa_improvement_3y). It does not expand the other13 input-shortage groups or22
member-shortage groups. Minimum20, strict, weights and official-Q gate stay fixed.

Cache and saved study settings bind config, evaluation snapshot, reference-source
snapshot/preview, admission plan, engine version and both population identities.
Replay requires those exact inputs; a changed source is a new study run. Display
filters are applied after the result and cannot enter this API or alter N/ranks.
Old `sector-qgv-config/1` saved settings are not migrated or overwritten.

Output: comparison by row and unique issuer, factor and axis gained/lost/common
changes, separate joint/total, original denominator, per-group reference N and
admission reasons. A null total has null rank. Any valid total ranks only against
the original evaluation rows using the existing ordering rule. No new axis rank
or whole-market rank is introduced. V raw ratios are independent of minimum N.

Synthetic example `reference-contract-example.json`: three target companies,
twenty eligible reference issuers for one factor. The reference N remains20 if a
screen displays one target. Missing V leaves total/rank null. Real company rows
and references are kept only in the approved private handoff.

## Implementation plan / ledger

- [ ] Add failing tests for reference admission, overlap/duplicates, day/version/
  provenance/future-input mismatch, nineteen/twenty boundary and target preservation.
- [ ] Implement `research/sector_qgv_reference.py` using existing validation,
  preview/aggregate/ranking; add `reference-study` to existing tools/sector_qgv.py.
- [ ] Bind both populations in cache/save/replay; test filter-invariant projection
  and hash mismatch through CLI. Tests use small hand expectations.
- [ ] Generate actual synthetic fixtures; run changed-path and engine regression
  tests once after final changes. Main owns CI list, frontend and workflows.
- [ ] Freeze a private job using retained #527 artifacts; admit individual issuer
  inputs for the nine groups, run one treatment, compare with retained baseline.
- [ ] Preserve real inputs/results/manifest/replay, open stacked Draft PR on #527,
  deliver exact SHA/contracts/fixtures and separately report CI and Main receipt.

Review focus: evaluation/ref overlap cannot replace target data; reference rows
cannot become scored targets; dates and classification evidence cannot be filled;
source subset must not become a market denominator; cache includes both sets.

Ruling: owner has already authorized implementation and comparison, so no repeat
design approval. Only changed tests run; no completed source calculations or
same-SHA successful audits are repeated. Native implementation, final review.
