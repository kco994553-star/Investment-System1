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
