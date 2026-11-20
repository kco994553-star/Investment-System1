# KIS stock source journal and replaceable private views

Owner decision 2026-11-19, #571. Git keeps normalized RAW calculation inputs,
the capture hash summary and a small query reference. Serving responses are
replaceable objects in a separate private store. Main compares GitHub private
release assets and Cloudflare KV, then asks the owner to choose. The producer
works on local bytes and has no service connector, credentials or publisher.

This supersedes the /3 period-piece **writer** for this deployment. Legacy
projection and /3 remain available for replay and comparison. The frontend
still receives one kis-stock-view/1 response for an exact symbol.

| Path in producer staging output | What it contains | Placement |
|---|---|---|
| rows/<sha256>.json.gz | One bootstrap cohort or a daily patch of new RAW rows, superseding corrections, and changed evidence fields. Unchanged overlap carries no extra row. | Git source |
| captures/<sha256>.json | SHA-pinned parent, changed-row blobs and calculation context. Daily maximum 3 KiB. Bootstrap may list multiple cohorts. | Git source |
| query-refs/<sha256>.json | Capture pin and serving generation pin, maximum 3 KiB. | Git source after publication verification |
| stock/<sha256>.json.gz | Complete kis-stock-view/1 JSON for one symbol. RAW/confirmed split basis, OHLCV/amount, ten indicator columns, reasons and latest results. | Private serving store |
| qgv/<sha256>.json.gz | Separate QGV response using the pinned financial inputs, with the existing private projection. | Private serving store |
| generation.json | Manifest for serving objects, with compressed bytes/hash, JSON bytes/hash and source capture pin. | Private serving store |

An ordinary new trading day writes one shared data patch, one capture summary
and one query reference when each fits its byte cap. Large inputs are
partitioned and each part is pinned. Financial, symbol mapping and optional
month-end inputs are independently pinned immutable Git inputs. Keep them with
the selected capture checkout. The original provider body/receipt and its
retention policy stay with the existing source process. The journal retains
normalized RAW data and its provenance rather than duplicating the receipt body
or storing a copy of every computed indicator. A capture containing no changes
to inputs or context emits no new Git objects.

Ordinary stock refreshes reuse the old indicator row prefix if its source,
basis, split evidence and hold state still match. The existing GSQ015 kernel
uses the retained input history as its seed when calculating new values and the
latest measures. A correction, confirmed split, or changed hold that affects
the prefix causes a full projection for the affected symbol. Unchanged source
and evaluation context reuse the existing response bytes. A normal trading
day with prices for every symbol still produces 517 changed response files.
This is different from recalculating and replacing earlier day values for all
symbols. QGV stays separate because its cross-sectional calculation can change
when another price changes.

Gzip bytes have a fixed mtime. The manifest pins the immutable compressed
object and the decoded JSON. Give a consumer only the response of the selected
symbol after authorization. The JSON contains all retained days and the same
17-field layout from the original chart review. It contains no frontend math
and requires no client request when toggling indicators or changing the
period. For matching basis and split evidence, confirmed split adjustments
come from the existing kernel. The producer enforces the existing 1.8 MB
uncompressed limit, also checking staged files. A limit failure stops staging
instead of truncating history.

## Commands for Main

The input request is the existing pinned kis-offline-rebuild/1 dictionary with
the #564 staged retained data. It includes the evaluation day, clock, symbol
mapping, financial input and optional month-end pins. The source checkout
contains exact file bytes for those snapshot pins at their request-relative
paths. Main pins the source checkout commit and the resulting capture hash.

Bootstrap with a single pinned request and no --head. Subsequent updates also
pass the last committed --head and --head-sha256.

```sh
PYTHONPATH=implementation/src python3 -S -m investment_system.research.kis_stock_journal append \
  --source-root "$SOURCE_CHECKOUT" \
  --request "$PINNED_INPUT/request.json" --request-sha256 "$REQUEST_SHA256" \
  --head "$LAST_CAPTURE_PATH" --head-sha256 "$LAST_CAPTURE_SHA256" \
  --output-dir "$PRIVATE_SCRATCH/source-append"
```

Old date corrections, approved split/basis or identity-evidence changes, and
backfills require --revision-reference with the reviewed evidence ID. Overlap
with identical bars preserves original per-row capture provenance. Source
replay checks each parent/part hash and rejects conflicting row revisions and
clock regression. The command creates a new local directory. It never commits
or uploads. Main stages the new source files with previous source objects
before generating the matching view.

Full recovery works without a previous view, without the supplier request, and
without the supplier receipt releases. The checked-out Git source must
contain the capture chain, normalized data/evidence, and the pinned financial,
symbol and optional month-end snapshots. Use the producer code revision
associated with the capture. No authentication or network is needed locally.

```sh
PYTHONPATH=implementation/src python3 -S -m investment_system.research.kis_stock_journal restore \
  --source-root "$STAGED_SOURCE_CHECKOUT" \
  --head "$CAPTURE_PATH" --head-sha256 "$CAPTURE_SHA256" \
  --output-dir "$PRIVATE_SCRATCH/restored-view"
```

Use --check-only instead of --output-dir to time full compression and pin
verification without writing response files. For a daily selective build, add
--previous-view and --previous-view-sha256 for a local pinned prior
generation.json, with its referenced serving objects readable relative to
that file. The new manifest references both new assets and verified reused
assets. The new output directory contains only changed response objects plus
the manifest and query reference. If the previous objects are lost, run a
full restore. A clean full restore and the selective build for the same
capture must agree byte for byte when resolving both generations' objects.

Main validates the entire generation and stages immutable serving objects
before changing the active reference. Only the small query-refs entry belongs
in Git. A failed upload or validation preserves the currently active
generation. Private scope, access checks, two-generation retention, completed
upload, and publication ordering remain the integration contract. No vendor
deployment, data update or source collection runs in these commands.

## Local validation and measured scope

A held 100-session offline recovery recalculated 517 symbol responses in
32.194 seconds from only the normalized source journal and pinned financial
and mapping files. Largest per-symbol response was 46,642 bytes JSON and
13,177 bytes gzip. This is the local replay, calculation, compression and
verification path in check-only mode. It excludes checkout/network, disk
publication, Worker CPU and browser opening time.

The normal 517-symbol synthetic capture added one patch and one summary,
41,531 Git loose-blob bytes together. With the small query reference the
normal count is three Git files. The complete serving generation has 517 stock
objects, one QGV object and one manifest. With only a same-day reviewed price
correction, only the affected stock object changes, plus the manifest and any
changed QGV object. A confirmed split test retains the original RAW prices.

The 141-session synthetic update matched a full recovery byte for byte
while reusing both symbols' old indicator prefixes. Recovery can rebuild
those prefixes with the same existing kernel when no serving object survives.
These measurements are capacity evidence. No provider request, data commit
or external serving store was used.

| Local check-only recovery | Stock responses | Largest JSON | Largest gzip | Elapsed |
|---|---:|---:|---:|---:|
| Held 100 sessions | 517 | 46,642 B | 13,177 B | 32.194 s |
| Synthetic 1,260 sessions | 517 | 292,685 B | 68,630 B | 307.912 s |

The five-year run restored from a synthetic bootstrap plus one daily append.
It created no serving files and counted 35,584,320 bytes across the compressed
stock/QGV objects, generation manifest and query reference. Full materialization
and Git-only recovery use the same projection; writing files or uploading and
verifying them adds time. Normal prefix reuse was measured separately for
byte equivalence, not as a 517-symbol runtime claim.

## First publication and daily input preparation

For the first publication, reuse the previously audited 517-series, 51,606-row
day-1 handoff. The existing request is for 2026-11-13. Keep its original
calculation clock and independent request SHA256. Stage its exact
request.json, series.json, monthly.tar.gz, financial.json and symbols.json in
one local input directory. The first three inputs describe the price source.
Stage the pinned financial and symbol bytes at the same relative paths in
SOURCE_CHECKOUT for append and restore. Month-end input was absent for this
run. The original data checkout supplied the MODP0 .json body and corresponding
.receipt.json under kis/dailyprice/<storage-symbol>/MODP0/. Legacy chart outputs
and MODP1 are excluded. The archived handoff already verifies the original
Git blobs, receipt hash/size and monthly rows. Reuse it for first publication
with the bootstrap append and restore commands above.

For later input preparation, use the keyless
`investment_system.research.kis_request_builder`. It reads local files using
the standard library and reuses the existing normalization and monthly
deduplication. The private collector's fetch step leaves each response as
<name>.body and its metadata as <name>.json in RUNNER_TEMP. The same intake
command accepts a retained data-branch body paired with its .receipt.json.
Use the capture manifest or committed blob to pin the receipt itself.
The pinned receipt supplies the body hash and byte count.
Use the existing validated route/scope and matching per-series evidence
(currency, currency reference, identity, held ranges and confirmed ranges
where present). Create a pinned scope evidence file once from the approved
baseline request with:

```sh
PYTHONPATH="$CODE/implementation/src" python3 -S -m investment_system.research.kis_request_builder evidence \
  --baseline-request "$INPUT/request.json" --baseline-request-sha256 "$REQUEST_SHA256" \
  --output "$RUNNER_TEMP/kis-series-evidence.json"
```

The output contains a provider symbol and venue binding for each code. The
printed evidence_sha256 is the pin for page admission. Vendor matching alone
does not establish identity or split evidence. Only successful MODP0 pages with admissible rows enter the store.
A documented empty end-of-history result contributes no page.

Use a scratch copy of the selected #564 monthly inputs, with the complete
approved symbol scope. Process each accepted page in order of fetched_at.
Validate the collector plan, scope and accepted/refused totals for the batch
before publication. Use the following command for a single body/receipt pair,
called in a loop by the Main workflow.

```sh
export PYTHONPATH="$CODE/implementation/src"
python3 -S -m investment_system.research.kis_request_builder ingest-page \
  --store "$STAGE/store" --body "$PAGE_BODY" --receipt "$PAGE_RECEIPT" \
  --receipt-sha256 "$RECEIPT_SHA256" \
  --evidence "$SERIES_EVIDENCE" --evidence-sha256 "$SERIES_EVIDENCE_SHA256" \
  --code "$EXACT_INPUT_CODE"
```

New or reviewed revised rows become YYYY-MM.jsonl.gz members. The command
checks receipt/body integrity, preserves the original row clock and reports
new_rows, revised_rows, unchanged_rows and appended_bytes. Use
--revision-reference only for an approved changed overlap. Each input
page is a separate validation/write operation. On failure discard the staged
batch and retain the prior published generation. Confirmed later splits and
other evidence changes require the existing reviewed basis transition.
In particular, do not attach a later split to an older page; publish
consistently with the reviewed evidence for its retained series.

After staging the whole monthly input, freeze the request once. The following
snapshot paths are relative to STAGE and must contain the exact pre-pinned
bytes. Content-addressed names prevent an old journal frame from resolving a
new quarterly input at a reused path. An unchanged snapshot can reuse its
existing path and blob. If month-end data is absent, omit both month-end flags.

```sh
python3 -S -m investment_system.research.kis_request_builder freeze \
  --root "$STAGE" --store store --expected-series "$EXPECTED_SERIES" \
  --evaluation-day "$PRICE_DAY" --calculated-at "$CALCULATION_CLOCK" \
  --financial "inputs/financial/$FIN_SHA.json" --financial-sha256 "$FIN_SHA" \
  --symbols "inputs/symbols/$SYMBOL_SHA.json" --symbols-sha256 "$SYMBOL_SHA"
# Optional: --monthends "inputs/monthends/$MONTHEND_SHA.json" --monthends-sha256 "$MONTHEND_SHA"
```

Output is STAGE/request.json and STAGE/indexes/<sha256>.json. The command
reports request_sha256, scope count and number of retained normalized rows.
It reopens every series manifest/month/receipt, checks exact coverage against
the symbol mapping, rejects a source after the calculation clock or price
day, and rejects conflicting bytes at the same request path. Use a fresh
scratch directory for a new capture. Builder exit 0 is valid output, exit 2
is input, pin or local IO failure. Abort the batch on any nonzero status.
Both commands enforce private staging outside a Git checkout.

The live sequence is plan, fetch, keyless intake and freeze, journal append,
and restore. The KIS credentials are scoped only to fetch. Replace the old
`kis_collector store --data "$DATA_CHECKOUT"` persistence call. Do not git-add
scratch bodies, page receipts, the staged monthly store, or request/index.
Append to the previous frozen journal and commit only its new content-addressed
row parts and small hash summary. Main verifies the release objects before
publishing their number list and query reference. The checked-out source can
include newly approved immutable financial or mapping inputs at their pinned
paths. Preserve older committed inputs for replay. In append, a symbol whose staged capture
clock predates its previously committed clock causes a batch failure.

The builder deliberately fails on an incomplete scope. A run containing no
usable new page for some already held symbol may retain that symbol only from
its independently pinned monthly baseline. The journal can restore the
normalized calculation history, but cannot recreate lost provider JSON or
receipt bytes. Main must supply the selected retained monthly baseline on
the runner or stop the batch. Do not relabel a partial latest or older-only
capture as a complete replacement. When planning a later older-only run,
advance the historical cursor from the committed oldest RAW sessions, not
from the old page-directory coverage file or from a failed page.

```sh
python3 -S -m investment_system.research.kis_request_builder coverage \
  --source-root "$SOURCE_CHECKOUT" --head "$LAST_CAPTURE_PATH" \
  --head-sha256 "$LAST_CAPTURE_SHA256" --output "$PLAN_ROOT/kis/coverage.json"
# Also stage the pinned symbols lookup at "$PLAN_ROOT/kis/symbols.json".
# Main's existing collector plan reads --data "$PLAN_ROOT".
```

This scratch-only coverage is for the next request planner. It is never a
daily Git output. A planning failure does not move the committed cursor.


For the three planned older-only batches, run the same MODP0 intake for the
received older pages and retain the newest approved observations. Freeze
PRICE_DAY at the newest approved trading evaluation day. Use the actual
later knowledge clock so new page receipts are never backdated. Pass the
approved backfill reference to `append --revision-reference`, and carry the
previous committed capture path and SHA256 through each run. Verify new
first/last dates, row counts, overlap counts and any refusal before promoting.
Three backfill runs do not by themselves prove five-year coverage.

Once the committed capture contains verified five-year inputs, the real
timing command is the restore command above with `--check-only` replacing
`--output-dir`. Keep stdout JSON's elapsed_seconds, stock count and max file
measurements. It times local source replay, kernels and gzip, excluding
collection, checkout, writing and upload. The 307.912 s measurement above
used synthetic 1,260-session data. Actual five-year timing remains open.
