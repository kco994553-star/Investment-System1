# Monthly retained-price storage

Offline data/storage implementation on canonical; Main owns collection workflow,
Worker, authentication, UI and deployment. No collection is performed by this code.
Existing calc23.1, technical kernels, private verification state and file caps are
unchanged. The current official population is Universe504; Top500 is a transition
goal. Private KIS results do not replace the public central V.

## Storage and commit protocol

`research.monthly_price_store` reuses `kis_price_bridge.normalize_page` and
`validate_contract`, plus the existing canonical JSON/hash functions and
1,800,000-byte delivery cap. Original MODP0/RAW only; MODP1 and adjusted input are
rejected. No source, price, indicator or scoring engine is added.

For each provider series (symbol, venue, currency, calendar and RAW lane), the
store has:

- `series/<fingerprint>/months/YYYY-MM.jsonl.gz`: concatenated deterministic gzip
  members containing **only new rows or explicitly reviewed revisions**. Each
  record preserves the full provider row, normalized raw row, original source
  hash/capture time, receipt hash and revision predecessor. The fingerprint is a
  storage key, never a verified security ID. No missing dates/values are filled.
- `receipts/<receipt-hash>.json.gz` under that series: exact original receipt text,
  response hash/size, response header without the row array, pinned input-contract
  hash and contract header. No overlapping response body is copied. Old approved
  source archives remain untouched. `raw_body_retained=false` and
  `original_body_reconstructable=false` mean the exact old response bytes cannot
  be reconstructed from this new store alone.
- Immutable `manifests/<hash>.json`, and a small `latest.json` pointer committed
  last. A month entry pins its **committed prefix length**, SHA256 and record count.
  Readers must honor that length rather than reading to EOF. Older manifests can
  replay older prefixes and revisions. A per-series OS lock serializes writers.

An identical receipt is idempotent. A later capture containing unchanged values
adds receipt/manifest metadata but zero monthly-row bytes; its clock does not
replace each row's first observation time. Any changed provider/normalized value
requires an explicit `revision_reference`. It is retained alongside its previous
version, never silently adopted as a split or adjusted price.

An interrupted append does not invalidate the old prefix. An exact retry reuses
the matching complete/partial tail. A different uncommitted tail is a hard error
(`DIFFERENT_UNCOMMITTED_TAIL`); it is not deleted, treated as empty, or published.
Source/receipt/contract pins, timestamps and evidence must validate first. A
changed identity/action-evidence context fails `SERIES_EVIDENCE_CHANGE`; explicitly
review and version that context separately. This store cannot promote verification.

## One bounded query JSON

`query_bytes(store, manifest)` materializes **one existing `kis-bars/1` JSON per
selected series**, carrying the combined journal pin and `UNVERIFIED_REFERENCE`.
Storage alone returns `WITHHELD/SAVED_DISPLAY_REVIEW_REQUIRED`. To preserve the
previous reference display/hold, supply the independently pinned saved chart;
all source, identity, row, basis and time context must match exactly. Its display
decision is copied, not recomputed. A changed input requires the existing
preprocessor's review path, not a copied stale `AVAILABLE` label.
Per-row source hashes/times remain intact; the header source hash identifies only
the most recent response. It is not asserted to hash all historical rows.

Main can place this JSON at the existing `chart/<first>/<symbol>.json` path. Worker
does not need to fetch or decompress sixty months of archives for one request.
The existing producer 1,800,000-byte and Worker 2MiB limits stay unchanged; an
oversized query fails instead of truncating history or increasing limits. Saved
technical/measures/QGV outputs remain separate and are not recalculated by storage.
Their signal dates/input pins must match before Main publishes a joined batch.
Slash encoding remains a filename operation, not a security alias.

The pure API takes independently pinned retained bytes:

```python
from investment_system.research.monthly_price_store import ingest, load_manifest, query_bytes

out = ingest(approved_private_store, contract_bytes=retained_contract_bytes,
             body=retained_modp0_response_bytes, receipt_bytes=original_receipt_bytes,
             expected_contract_sha256=manifest_contract_pin,
             expected_receipt_sha256=source_receipt_pin)
manifest = load_manifest(approved_private_store, out['series_id'])
chart_bytes = query_bytes(approved_private_store, manifest,
    saved_chart_bytes=matching_saved_reference_chart,
    expected_saved_chart_sha256=independent_saved_chart_pin)
# Main's private writer controls delivery, authentication and atomic batch swap.
```

The network-free CLI retains the outside-Git private-output restriction:

```sh
PYTHONPATH=implementation/src python -m investment_system.research.monthly_price_store \
  --store PRIVATE_STORE --contract CONTRACT.json --body MODP0.json \
  --receipt ORIGINAL.receipt.json --expected-contract-sha256 CONTRACT_PIN \
  --expected-receipt-sha256 RECEIPT_PIN --query-output PRIVATE_CHART.json
```

Use `--saved-chart SAVED_CHART.json --expected-saved-chart-sha256 SAVED_CHART_PIN`
to reuse the matching saved display decision. Without it the query stays held.

The actual migration used the pure API with the existing approved private writer;
this is not a claim that the CLI succeeded in a workspace whose writable roots
are all beneath Git. Main must connect workflow/Worker; no such files change here.

## Changed-boundary verification and retained migration

Synthetic tests cover full-row roundtrip, repeated/overlapping capture, month
boundary, explicit correction/history replay, mismatched pins/basis, failed commit,
unknown append tail, empty success versus HTTP failure, identity changes, archive
tampering, path containment, query-size limits and a 1,260-session bounded query.
That synthetic window is a capacity test, not five years of actual collected data.
The full Python CI already discovers `tests/research`; no CI-list edit is needed.

The retained day-1 migration checks the original source commit blobs, input pins,
all normalized fields and every full provider row. Results: 517 series (502
operating code rows +15 ETFs), 51,606 rows, differences 0; identical replay writes
0 monthly bytes. No indicator/score recalculation, adjustment, promotion or new
eligible adoption. Actual company files and script remain in the private handoff.

Measured new store: 3,097 monthly chunks /4,940,883 compressed bytes, receipt
metadata 570,117 bytes, store total 7,044,025 bytes before filesystem allocation.
The bounded query files total 29,049,027 bytes; maximum one file 57,760 bytes.
The matching saved display retains six held series and 511 available reference
series (496 operating code rows +15 ETFs); no hold is released by this migration.
These full-provider-field/provenance measurements differ from the earlier
seven-column size estimate. Future daily append/receipt/Git growth is not measured
by this one retained batch; do not call it an exact five-year storage forecast.
The migration delivery is streamed into a private archive to avoid retaining
thousands of duplicate local scratch files, then every archived member is reopened
and checked. Normal operation may store the same layout as regular private files.
