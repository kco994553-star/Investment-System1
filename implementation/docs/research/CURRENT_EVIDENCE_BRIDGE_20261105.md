# Current expansion: documentary evidence bridge

Research contract `current-expansion-staged-evidence/1`; basis date `2026-11-02`.
This extends #482's existing `current_expansion.evaluate` entry point. It consumes
the retained normalized financial cache and verified documentary crosswalk. It
does not normalize financial statements again, fetch sources, change the official
504-code population, or create a complete current or historical market population.

## Executable path

`tools/current_evidence_bridge.py` verifies five input file hashes before calling
`research.current_evidence_bridge.link_and_evaluate`. The bridge verifies catalog
identity, source hashes, cover context/byte references and bounded document links,
then supplies staged evidence to the existing evaluator. Original sparse catalog
observation IDs are preserved separately from the subset indices used by evaluate.
CIK becomes an issuer reference only; an external security ID remains a separate
field. Cached financial calculation versions must match the existing calculator.

```sh
python implementation/tools/current_evidence_bridge.py \
  --job /private/example-job.json --output-dir /private/new-result-directory
```

Synthetic job shape (each path identifies an already held file):

```json
{
  "basis_date": "2026-11-02",
  "inputs": {
    "held": {"path": "/private/held-normalized.json", "sha256": "<64 hex>"},
    "crosswalk": {"path": "/private/financial-ticker-crosswalk.json", "sha256": "<64 hex>"},
    "covers": {"path": "/private/cover-evidence.json", "sha256": "<64 hex>"},
    "sources": {"path": "/private/source-evidence.json", "sha256": "<64 hex>"},
    "links": {"path": "/private/bounded-document-links.json", "sha256": "<64 hex>"}
  }
}
```

Outputs are `staged-evidence.json`, `pipeline-inputs.json`,
`current-expansion.json`, and a byte/hash manifest. The CLI refuses output inside a
Git checkout and creates private files with mode 0600. The pipeline input artifact
references the verified original financial cache, avoiding duplicate calculation.

## Stages and adoption boundaries

| Stage | Evidence carried | What remains independent |
| --- | --- | --- |
| Issuer link | Catalog CIK/ticker, submissions exact ticker, source receipt | A ticker observation does not establish security continuity |
| Security type | Literal archived cover titles, context, source byte ranges | Archived type is not a current inclusion/exclusion decision |
| Same security at basis | Explicit bounded research document interval | Filing period and retrieval time are not security validity dates |
| External fixed ID | Separate supplied-value/status fields | No ID is invented from CIK, current ticker, or a row index |
| Representative | Observed issuer ticker multiplicity | One observed ticker does not establish representative status |
| Valuation inputs | Cached financial share period/currency as diagnostic references | Diluted financial shares are not same-day all-class shares; financial currency is not quote currency |
| Market-cap eligibility | Separate missing share, price, quote identity, currency, action-scale reasons | No market cap or nominal threshold test without those inputs |

An explicit bounded document can establish documentary identity inside its own
interval even when an external fixed ID is absent. The evaluator's existing fixed
ID requirement remains unchanged. Old cover periods are retained verbatim and
never copied into `valid_from`/`valid_to`. Unsupported literal security titles stay
unclassified. An empty title in a bounded link is rejected.

## Held-data execution scope

The supplied 1,512 distinct ticker observations link to 1,057 cached issuers.
The execution carries 1,511 exact submissions matches and one catalog-only row.
Archived security-type evidence is available for 179 rows: 178 existing cover
descriptions and one separate bounded documentary link outside the basis date.
The 178 cover periods are in 2024; the separate document interval ends on
2026-10-30. Neither proves applicability on 2026-11-02.

At the basis date, dated documentary identity is 0; 178 are archived descriptions,
one has evidence outside the date, and 1,333 remain unknown. External fixed ID,
representative and adopted issuer market cap each remain 0. All 1,512 rows remain
eligibility-unknown; eligible, excluded, scored and ranked counts are 0. Full-market
denominator, relative scores/ranks and coverage remain null. Unknown rows are kept.

All 1,512 row-level raw-metric mappings are compared with the retained earlier
output and the 1,057 cached issuer records. Financial recomputation is 0. The new
result changes the traceability of missing evidence, not the financial values or
official scoring model. The supplied subset is forcibly marked incomplete even
if a caller labels its upstream catalog complete.

## Main/private handoff

The new research artifact is a producer contract only. No authenticated reader or
screen is claimed connected. Consumers may join the existing evaluator result by
`evaluation_observation_id`; retain `original_observation_id` for source lineage.
`stages.<stage>.state` and reason fields distinguish documentary evidence, date
applicability, external identifiers and eligibility blockers. Raw company rows and
source receipts stay private; public examples and tests are synthetic.

Minimum next evidence is a basis-date valid security/issuer relationship with
type, exchange/listing scope, representative rule and external security ID, plus
same-day raw USD quote and all-class shares with corporate-action consistency.
Obtaining any new source remains a separate approval; no supplier is prescribed.

The parent independently reviewed the actual linkage path. Its missing-title
edge case was addressed by fail-closed validation and regression tests.
