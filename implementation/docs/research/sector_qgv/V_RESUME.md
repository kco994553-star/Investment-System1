# Default V retained-input resume contract

Version `sector-qgv-v-resume/1`, model `sector-qgv-default/0.1.0`. Research only.
This adds two modes to the existing `implementation/tools/sector_qgv.py` CLI:
`v-prepare` and `v-resume`. No HTTP, quote parser, scheduling or new scoring engine.
The original Q/G snapshots and formal-Q gate observations are retained unchanged.

## Preparation and handoff

`v-prepare` hash-checks the original SEC snapshot, already identified archives,
classification snapshot and #499 financial cache. It writes `v-resume-input.json`,
`readiness.json` and `manifest.json` to a private directory. It never calls the
scoring engine. Existing calc23.1 TTM revenue/EBIT values and the eligible #499
common-book input are reused. Needed CFO/capex/D&A use the existing fiscal-period
extractor; incomplete latest TTM does not fall back to an older annual period.
EPS requires a verified TTM diluted-EPS composition; annual EPS/NI/current shares
are not substitutes. Dividends, preferred capital and NCI are never filled with 0.
Source archive/member/hash, filing-period inventory, units, currency and acquisition
availability are retained. Observed-by-acquisition is not a first-release timestamp.

`readiness` separates numerator validity, remaining non-price evidence, pending
price fields and a structural peer shortage. Its mapped-group size is an upper
bound, not the valid-factor peer N. A group with >=20 mapped members may still fail
minimum20 after price/factor validation. Identity/share/ADR/corporate-action proof
must support the valuation date. Financial numerators alone do not meet this test.

## Market delivery and execution

The job pins `v_pack` and `market_inputs` using path/SHA256 descriptors and provides
`market_evidence` descriptors for real evidence files. A real market envelope has
`schema_version=sector-qgv-v-market-input/1`, `data_kind=PRIVATE`, `valuation_date`,
`as_of`, `resume_hash` (canonical JSON digest of the pack), and `records` keyed by
original company ID. See `v-synthetic-market.json` for the full shape.

Each record supplies dated `basis`, normalized `inputs` (only price, issuer_mcap,
enterprise_value), optional `field_basis`, and necessary `capital_evidence`.
Per-share fields require the already established source share basis to match the
target; this adapter does not perform an implicit split/ADR conversion. Capital
inputs require all common classes, actual shares, matched normalized quotes and
currency; supplied totals are checked against those primitives. EV additionally
requires explicitly evidenced debt/cash/preferred/NCI with matching fiscal periods.
Financial observations cannot be replaced through the price delivery.
Every real provenance/evidence reference must identify a supplied hash-verified
file using `#sha256=<64 hex>`. A hash proves file integrity; it does not itself
prove that the cited document supports a claimed fact. Main/Codex must review it.

Calculation `as_of` may be later than the frozen financial snapshot, which remains
`source_financial_as_of`. No original availability is restamped. All evidence is
bounded by calculation time and UTC valuation date; retrieval may be later only
with an explicit later calculation time. This is a current reconstruction, not
proof of historical system availability. Nov2 financial11 and Nov4 sector504
remain separate deliveries. A different valuation date fails validation.

```sh
python implementation/tools/sector_qgv.py --job /private/resume-job.json --output /private/new-v-result
python implementation/tools/sector_qgv.py --job implementation/docs/research/sector_qgv/v-synthetic-job.json --output /tmp/sector-v-synthetic-new --synthetic
```

The existing kernel performs raw variant calculations, sector/accounting peer
normalization, strict Q/G/V and gate/total assessment. Existing preview/save
contracts remain unchanged; no official QGV output is overwritten. The private
resume job supplied with the pack requires an actual eligible delivery before
execution; it contains no placeholder price. Public/synthetic and private kinds
must match at job, pack and market levels. Output collisions are refused.

## Execution scope, 2026-11-07

New private preparation for 2026-11-04: original denominator504, mapped365;
1,053 selected V variant rows, 587 numerator-ready rows across323 companies.
728 linked primitive fields:242 retained TTM fields,1 retained common-book field,
485 newly extracted using the existing TTM parser. Price-only-ready0; additional
non-price gaps1,053 rows/365 companies. Structural peer shortage135 rows/59
companies overlaps those gaps. Unmapped139 stay in504, without assumed defaults.
Real raw V/factor V/axis V/total remain0. This is not a zero company score.

Synthetic20 companies: raw ratios, V and total20; missing one EPS leaves peer N19
and V0. Basis/EV absence, mismatched dates/units/classes, future UTC evidence,
financial override, reconciliation, and mixed public/private labels are rejected.
These are synthetic engine tests, not real V adoption or performance validation.
Main uses the existing preview reader; collection/auth/UI/workflows stay Main-owned.
#507's synthetic engine call is reported connected; private delivery remains pending.

## Focused completion attempt: one retained common-book input

2026-11-07 followup adds `connect_held_cover` to this module. It uses existing
`sec_cover_shares.parse_cover/class_symbols`, pins the original cover hash and
share-record CIK/availability, and appends historical cover evidence to the pack.
It does not manufacture a security ID, an applicability interval or a quote.

The private focus is one issuer/common_bp at valuation2026-11-04. Existing BPS,
equity/share period/currency and numerator are reused. One new documentary
connection carries literal common-stock title/symbol and the July27 share observation
from its July31 filing. It does not prove security continuity or the absence of
split/ADR/share-basis changes through November4. Thus newly complete non-price,
raw ratio, factor score, V and total counts all remain0. Original504 and prior
587/323,1053/365,135/59,unmapped139 counts are unchanged; the small-peer group is
an independent scoring constraint. The updated private pack is readable by the
same v-resume CLI once eligible evidence/price is delivered.

A one-security synthetic test now explicitly produces three raw ratios while
factor scores/V/total remain null for peer N1. Minimum20 is not a raw-ratio gate.
No completed Q/G comparison or NVDA diagnostic was repeated.
