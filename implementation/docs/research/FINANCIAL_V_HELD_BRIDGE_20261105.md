# Held financial V input bridge

`tools/financial_v_connect.py` connects local SEC companyfacts and existing
share-class evidence to the unchanged `financial-v-research/1` evaluator.
It extracts annual diluted EPS through the existing calc23.1 share-basis logic
and common book inputs through `common_book_inputs`. It writes the prepared
inputs, per-metric candidate results, source receipts and subtype shortages.
It never calculates official scores, ranks, joint coverage or preset totals.

This is a research input adapter. It does not approve financial V for operation,
establish a fixed security identity or reconstruct a historical PIT snapshot.
The universe remains the supplied fixed 504-member population. Financial
membership must match that universe exactly; TARGET rows are not inputs.

## Local manifest

Every file descriptor is `{ "path": "relative-or-absolute-local-path",
"sha256": "64-character-digest" }`. The CLI verifies the complete bytes before
consuming a source. A manifest contains:

```json
{
  "valuation_date": "2026-11-02",
  "input_vintage": "2026-11-04T12:00:00Z",
  "universe": {"path": "universe.json", "sha256": "<sha256>"},
  "shares": {"path": "shares.json", "sha256": "<sha256>"},
  "issuers": [{
    "code": "NYSE:EXAMPLE",
    "companyfacts": {"path": "facts.json", "sha256": "<sha256>"},
    "cover": {"path": "cover.xml", "sha256": "<sha256>"}
  }],
  "prices": null
}
```

The universe and shares files retain their existing `records` maps. Each issuer
uses its universe CIK, SIC, acquisition date, calc version and companyfacts hash.
The cover is optional; missing or foreign-entity evidence cannot confirm a class.
The cover hash must match the share record. The cover must directly report the
symbol in a standard DEI namespace and a context identifying the same SEC CIK.
Existing class status is accepted only with eligible measurement and filing dates.
Timezone-aware capture timestamps for financial inputs and cover-backed share
evidence must be no later than `input_vintage`, including the time within a day.
Evidence cutoffs are the earlier of financial acquisition date and valuation date;
later filings cannot replace the annual input. Acquisition is not publication.
Current companyfacts vintage is retained and is not labeled historical PIT.

## Optional prepared prices

A price file uses `records[code][metric]`. Each metric requires its own prepared
quote because EPS and balance-sheet shares can have different filing bases.
Required quote fields are `code`, `cik`, `date`, `value`, `currency`, `unit`,
`share_basis`, `source`, and `basis_source`. Each source reference contains a
SHA-256 and a JSON pointer into the retained evidence. These references identify
upstream reviewed price/basis evidence; this adapter validates their shape, not
the economic correctness of arbitrary external evidence or a split conversion.
The prepared price file itself is hash-verified by the manifest.

The evaluator requires an exact valuation date, positive finite price and
numerator, matching currency/unit and exact share-basis identifier. An EPS basis
has the form `FY0:<accession>:<filed-date>`; a common book basis has the form
`BALANCE_COMMON:<accession>`. Equal labels alone do not establish security identity
or a conversion. No closing price is carried forward or substituted from another
month. Different-date fiscal diagnostics remain in their separate existing path.

To close a numerator gap, retain annual diluted EPS with fiscal start/end and
filing basis, or common-equity and point-in-time common-share facts from the same
accession/date. Common equity must exclude preferred interests and NCI. Tangible
common equity also needs explicit goodwill/intangibles attribution. Retain the
class proof and its filing/measurement dates. Missing components are not imputed.

## Run and validation

```bash
python implementation/tools/financial_v_connect.py \
  --manifest /private/input-manifest.json --output /private/new-connected.json
```

Output must be outside Git working trees and must not already exist. It is
created with mode 0600. Console output contains only schema and row count; raw
evidence and results stay private. The command performs no network requests.

The new synthetic tests cover actual ratio computation on distinct metric bases,
retained numerators without quotes, date/basis/issuer mismatches, hash and entity
checks, future filings/class evidence, fixed membership and private output.
Existing successful suites and old fiscal diagnostics need not be repeated to
exercise this new adapter.
