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

- [x] Add failing tests for reference admission, overlap/duplicates, day/version/
  provenance/future-input mismatch, nineteen/twenty boundary and target preservation.
- [x] Implement `research/sector_qgv_reference.py` using existing validation,
  preview/aggregate/ranking; add `reference-study` to existing tools/sector_qgv.py.
- [x] Bind both populations in cache/save/replay; test filter-invariant projection
  and hash mismatch through CLI. Tests use small hand expectations.
- [x] Generate actual synthetic fixtures; run changed-path and engine regression
  tests once after final changes. Main owns CI list, frontend and workflows.
- [x] Freeze a private job using retained #527 artifacts; admit individual issuer
  inputs for the nine groups, run one treatment, compare with retained baseline.
- [ ] Preserve real inputs/results/manifest/replay, open stacked Draft PR on #527,
  deliver exact SHA/contracts/fixtures and separately report CI and Main receipt.

Review focus: evaluation/ref overlap cannot replace target data; reference rows
cannot become scored targets; dates and classification evidence cannot be filled;
source subset must not become a market denominator; cache includes both sets.

Ruling: owner has already authorized implementation and comparison, so no repeat
design approval. Only changed tests run; no completed source calculations or
same-SHA successful audits are repeated. Native implementation, final review.

## Executable interface and Main handoff

`python implementation/tools/sector_qgv.py --job JOB.json --output PRIVATE_DIR`

Job mode `reference-study`: SHA-256 pinned `evaluation_snapshot`,
`evaluation_preview`, `reference_snapshot`, `reference_preview`, `reference_plan`.
`reference_saved` replaces plan/config for an exact saved replay. Inputs that do
not match the saved bindings fail before recalculation; latest inputs never
substitute. Directory must be new and outside any checkout for real data.

Outputs: reference-result.json (full private result/admission audit),
reference-settings.json, reference-snapshot.json (internal composite), manifest.
`reference-view.json` is a bounded, authenticated reader projection using
`sector-qgv-reference-view/1`: dual identities, bindings, original-504 comparison,
groups and null reasons inside factor records. Maximum 2,000,000 bytes. It is
PRIVATE_RESEARCH and cannot replace existing official/current delivery files.
The evaluation denominator and reference N must remain visible after filters.
The result hash binds the full private source, not just the visible rows.

`reference-synthetic/` contains executable source/evaluation, retained previews,
plan, result, saved settings, filtered projection, view and byte-hash manifest.
They reuse the existing fixture's 2026-11-02 synthetic day; actual study day is
2026-11-04. Do not combine them. Expect 3 target rows, 20 reference issuers,
Q/G gains3 each but union3, no V/total, and unchanged N20 when displaying1 row.

## Results and verification

First fixed plan SHA-256
`f1ea5c2847e609bb91669134741580bdd0bea8ada1b82ff0d1953bac0614b076`.
No return/score inspection changed the declared nine groups.

Actual evaluation: 504 code rows/501 issuers, 2026-11-04. Source8004 was screened
as a research catalog: 501 overlapping issuers retained their evaluation inputs,
7419 outside declared groups, 2 without eligible declared observations, **82
external issuers admitted**, all within held1057. This is factor-input eligibility,
not verified listing/security/investment eligibility. External issuers are energy25,
bank35 and insurance22. Source catalog8004 is not the whole market.

All active reference pools together contain504 unique issuer representatives
(422 retained +82 external), coincidentally the same number as evaluation code
rows. These two504s have different units and membership. Per-factor N is separate:

| Group | Factor | Before N | After N |
|---|---|---:|---:|
| ENERGY / GENERAL | operating_margin_ttm | 10 | 29 |
| ENERGY / GENERAL | accruals_assets_ttm | 17 | 39 |
| ENERGY / GENERAL | debt_assets | 17 | 42 |
| ENERGY / GENERAL | revenue_cagr_3y | 16 | 40 |
| ENERGY / GENERAL | roa_improvement_3y | 17 | 41 |
| FINANCIALS / BANK | roa_ttm | 18 | 53 |
| FINANCIALS / BANK | roa_improvement_3y | 18 | 53 |
| FINANCIALS / INSURANCE | roa_ttm | 18 | 40 |
| FINANCIALS / INSURANCE | roa_improvement_3y | 18 | 40 |

Existing raw values/statuses25,704 cells unchanged. New selected-factor scores149
row×factor observations across53 issuers; Q232→242 (+10), G343→359 (+16),
**unique issuers gaining either axis16**, V/joint/total remain0. No lost axes,
changed common-valid axis scores or total ranks. These are reference-set effects,
not improved financial results, official adoption or performance.

The nine treated groups remove their sample barrier. The other35 groups are
untreated: source evidence distinguishes13 with enough potential members but
missing inputs and22 with too few confirmed members. Do not say those13 have
already been expanded in this experiment. V/financial common-capital inputs and
gate limitations remain; original65 issuers still have an incomplete default
QGV route. Goal coverage QGV+total remains0/501; whole-market denominator null.

21 new synthetic tests plus affected common-engine/partial/saved-setting
regressions:89 passed at the reviewed fix. A final nullable-mapping exclusion
case brings the changed adapter suite to22 passing tests; unchanged common-engine
regressions were not repeated. Original normalizer endpoints are0..100; an initial test
expectation2.5 for a unique minimum was corrected to the existing formula's0,
without changing the formula. Independent review found two Important boundaries:
missing classification hash/other knowledge time could bypass admission; an
excluded row's classification record ID was missing from replay identity. Three
counterexamples failed then passed after fail-closed context checks and explicit
record/audit binding. No unaddressed review finding. Existing private sources
were not re-downloaded or re-parsed.

Real reconciliation: original504 rows/501 issuers preserved; 149 new scores checked
independently from reference ordering; all82 additions pinned to held sources;
non-target factors and original gates/settings unchanged. Main view397,008 bytes,
within2MB. Preliminary runs before boundary fixes were retained separately and
superseded by the accepted run; identical gains are counted only once.

Financial/V queue: this study admits issuer Q/G observations only. It adds no
TTM diluted EPS, class/action evidence, eligible11/04 price or EV inputs. Previously
verified financial components remain reusable; bank/insurance ROA scores now exist
but missing common ROE/equity/BPS still blocks their complete axes. WRB delivery
and other V inputs remain independent, without a new collection request here.

Implementation and retained-real comparison are complete; Main reader integration,
authenticated browser verification, operating adoption and deployment are separate.
