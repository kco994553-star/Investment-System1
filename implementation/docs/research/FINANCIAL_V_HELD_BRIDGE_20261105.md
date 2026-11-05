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

## Dated balance components (bridge 1.1)

`balance_inputs` connects eight primitive observations before the common-class
gate: direct common equity, parent equity, preferred shares, common shares, NCI,
goodwill, other intangibles and combined intangibles. Every selected value retains
its unit, balance date, filing date, accession, companyfacts hash and JSON pointers.
`ELIGIBLE_OBSERVATION` means a dated fiscal observation, **not** eligible common
equity, a confirmed security, or an adopted candidate ratio. Parent/total equity
cannot silently become common equity. Assets/total equity can locate the latest
balance anchor but do not supply any numerator.

`PRESENT_BUT_INELIGIBLE` and `NOT_PRESENT_IN_HELD_SOURCE` are distinct. Rejected
observations retain reasons/pointers (unit, duration, stale/future date, accession,
form, nonfinite or conflicting values). An eligible older/different-accession
component cannot fill the selected anchor. `primary_applicability` separately
marks required/alternative inputs, inputs not used by an earnings primary, and
unresolved business models; absence of a standard tag does not prove absence
from an unheld issuer-extension filing. Missing values remain null.

The existing combined-intangibles mapping now also accepts
`IntangibleAssetsNetIncludingGoodwill`. Conflicting aliases fail closed, including
when a separate goodwill/other sum exists. Formula, class gate, explicit zero NCI,
and research configuration hash remain unchanged.

The same CLI also passes the held, hash-matched XBRL instance through the existing
`xbrl_supplement.supplement` parser with an explicit financial balance-concept
subset. Default calc23.1 parser behavior is retained. Only consolidated standard
concepts in exact filing/period/unit contexts can supplement companyfacts; issuer
extensions, dimensional/class contexts and currency conversion are not inferred.
`balance_supplement` records additions, conflicts and rejected context/unit
references. Future/unidentified filings are skipped with a reason. The original
companyfacts bytes are immutable; derived pointers are reproducible from the
original payload plus audited additions and a canonical derived-payload hash.
An instance/companyfacts conflict at the selected balance key blocks that
component and affected book numerator rather than choosing either observation.

## Optional prepared IEX prices

A price file uses `records[code][metric]`. Each metric requires its own prepared
quote because EPS and balance-sheet shares can have different filing bases.
The file envelope is `financial-v-price-input/1`, with `valuation_date` equal to
the manifest and a `records` map. Required quote fields are `code`, `cik`, `date`,
`value`, `currency`, `unit`, `share_basis`, `source`, `basis_source`, `traded_at`,
`acquired_at`, `price_type=IEX_LAST_REGULAR_TRADE`, `price_basis=RAW`, and
`trade_validation=ELIGIBLE`. This prepared handoff is for Main's IEX day file;
it neither calls IEX nor labels its last trade an official closing price/OHLCV.
Main must apply the existing trade-condition/correction/cancellation policy,
record ROUND/ODD_ONLY/NO_TRADE and parser completeness, and leave rejected trades
null. The calculation adapter does not reparse packets or approve new conditions.

Both timestamps must include timezone. The trade must fall within the shared
regular-session calendar on the valuation date (including early closes).
Acquisition must follow session completion/trade and precede the new job's
`input_vintage`; acquisition is not the historical availability time. A future
delivery therefore gets a **new** manifest/vintage, never the old receipt time.

Each source reference contains a SHA-256 and JSON pointer. `price_evidence` in
the manifest lists the corresponding small local JSON file descriptors. Their
bytes are verified and pointers must resolve. The trade record must match all
quote value/identity/date/unit/time/type/validation fields; the basis record must
match code/CIK/share_basis, cover S with `valid_from`/`valid_to`, and record
`action_status=MATCHED_TO_NUMERATOR`. Main retains the actual supporting
corporate-action/class evidence and original-source/packet manifest pointers in
these records. Structural verification cannot establish the economic correctness
of a claim or mint a security ID. No multi-GB pcap is loaded by this CLI.

Synthetic quote (numbers/identifiers are invented; hashes below are placeholders):

```json
{
  "schema_version": "financial-v-price-input/1",
  "valuation_date": "2026-11-02",
  "records": {"NYSE:EXAMPLE": {"earnings_yield": {
    "code": "NYSE:EXAMPLE", "cik": "0000000001", "date": "2026-11-02",
    "value": 40, "currency": "USD", "unit": "USD/share",
    "share_basis": "FY0:synthetic-accession:2026-02-01",
    "traded_at": "2026-11-02T15:59:00-05:00",
    "acquired_at": "2026-11-05T12:00:00Z",
    "price_type": "IEX_LAST_REGULAR_TRADE", "price_basis": "RAW",
    "trade_validation": "ELIGIBLE",
    "source": {"sha256": "<trade-file-sha256>", "json_pointer": "/records/0"},
    "basis_source": {"sha256": "<basis-file-sha256>", "json_pointer": "/records/0"}
  }}}
}
```

The source record repeats the quote fields except its two references. The basis
record additionally carries `valid_from`, `valid_to`, `action_status` and the
documentary links. Manifest `prices` pins this file; `price_evidence` pins both
evidence files. A synthetic EPS of USD 4/share gives E/P 0.1 only if all existing
numerator/class gates also pass. Missing evidence is not a zero ratio.

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

The first component-only run on the same 68 held issuers exposed 260/544 dated
cells, with 84 ineligible and 200 absent from companyfacts. The subsequent held
instance check found five apparently absent cells in ineligible XML contexts and
four cross-source conflicts, three at the selected balance key. No missing
eligible observation was added from XML. The final component and numerator
counts are recorded in the private handoff and PR result; the component-only
counts are not the final adoption counts. Same-date prices and actual candidate
ratios remain 0. These are input linkage diagnostics, not a coverage improvement
or historical PIT proof. Company-level values, source pointers, rejected
observations and missing-input lists remain private.
