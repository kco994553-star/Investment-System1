# Five-year private daily-bar storage proposal — not collection execution

Scope: retained day-1 measurement over517 received series (502 operating code rows
and15ETF),100-session maximum /51,606 RAW rows. The target list had519 series; two
missing series and future population growth are not silently included in the
measurement. Capacity assumption:5×252=1,260 unique sessions, not an actual future
trading-calendar count. MB/GB below are decimal bytes. No five-year dataset was
collected, generated or falsely presented as observed.

Owner's reported35MB day-1 bundle implies441MB for one non-overlapping five-year
snapshot under linear scaling. The cache measured here has24.125MB logical bytes
and29.676MB allocated for2,071 files, including original/modified responses and
receipts. These are different accounting scopes;35MB is retained as the owner's
conservative baseline, not silently replaced by a compression claim.

## Measured RAW-only payload alternatives

Each row uses the same517-series RAW lane. Existing MODP1 remains separately
preserved but is not a split-only source or calculation input. Keeping both lanes
roughly doubles payload/receipt storage; it does not improve proof of a split.

| Format | One five-year unique-history payload estimate | New bytes on an ordinary daily update | Source/chunk size per symbol (not the Worker API contract) |
|---|---:|---:|---|
| Original100-row response JSON |150MB |11.89MB/day if every fresh overlapping response is retained |about23KB per100-row page; multiple pages for5years |
| Each original response gzip |31.5MB for non-overlapping backfill pages |2.49MB/day of new captures |about5KB per100-row page compressed |
| Entire symbol history JSONL.gz |19.3MB |up to19.3MB/day of newly replaced compressed blobs once the5year window is full |estimated maximum45KB gzip /168KB decoded per symbol |
| Symbol×month JSONL.gz |approximately20–25MB |about0.30MB/day of rewritten active-month blobs in this sample; sample upper-size proxy0.45MB |maximum observed860B gzip per month/symbol, around3KB decoded |

The last two rows project a compact seven-field price/volume row
(`xymd/open/high/low/clos/tvol/tamt`), not a replacement for original-source
preservation. Values remain exact source strings; missing/zero, currency, adjustment
state and security/class relations must not be changed to gain compression.
Unknown/extra provider fields stay recoverable from the original response.
Partial sampled months and future number widths mean compression extrapolation is
an estimate, not a measured five-year size or hard bound.

## Snapshot size is not repository history growth

Five years of **daily100-session response captures** at the measured rate adds
about3.14GB gzip RAW payload (about15.0GB uncompressed), even though there are only
1,260 unique trading dates. Original-plus-MODP1 captures would be about6.58GB gzip,
excluding receipts. Using the owner's35MB whole-bundle baseline without compression
would add about44.1GB across1,260 daily captures. These are capture-history figures,
not a five-year unique price-series size.

Receipts also matter: the measured RAW receipt group is27,208B gzip per collection
day. One13-page historical backfill would be roughly0.35MB of such metadata; a
five-year daily collection history is about34.3MB gzip. Both are estimates under
the respective collection pattern. Do not attach a fresh full SHA/timestamp to
every row unnecessarily: use deterministic capture references and retain each
original receipt/hash once, without losing exact source-byte reconstruction.

Git is not assumed to deduplicate gzip blobs. A full five-year compressed file
changed daily can add an entire new blob for every symbol. Monthly chunks bound
that write amplification; completed months stay immutable, corrections create
explicit revisions rather than rewriting past evidence. Actual packed Git size,
remote replication, corrections and backups are not measured here.

## Recommended separation

1. **Cold source preservation:** unchanged raw responses plus receipt and request
   metadata, in private monthly release/archive bundles with file hashes. Reuse
   the approved private archive route; do not put all daily capture bodies into
   ever-growing Git branch history. A sample month of RAW captures is roughly
   2.49MB×21=52MB before cross-capture compression benefits; no such extra benefit
   is assumed. Grouping per symbol may improve overlap compression but has not
   been measured with successive real100-row responses.
2. **Unique calculation history:** symbol×month JSONL.gz, deterministic ordered dates,
   source capture references and explicit correction records. Finalized months
   are immutable. One small symbol manifest references chunks, provenance,
   security relations, currency and adjustment basis; the global search index
   references symbol manifests rather than embedding31,020 chunk entries.
3. **Hot Worker view:** keep the existing `chart/`, `technical/`, `measures/`,
   `qgv/latest.json` JSON contracts. Build bounded per-symbol chart views offline;
   Worker need not fetch60 monthly chunks or decode archives on every request.
   The current maximum chart payload is56,989B for100 sessions; linear1,260-session
   projection is about0.72MB, below the existing1.8MB producer /2MiB Worker caps.
   That is an estimate: measure every produced file and reject oversize files.
   Indicators/measures remain small result objects, separate from raw history.

A mature five-year monthly RAW price store is roughly20–25MB plus receipt/history
and manifest overhead (about34MB more for five years of daily receipts under the
sample pattern). Cold raw captures remain a separate multi-GB archive budget.
The hot chart view is separately bounded, and exact company-level outputs remain
private. No DB, new supplier, Worker decoder, workflow, limit relaxation, collection
run or deployment is introduced by this proposal. Owner/Main must approve any
collection/archive-workflow change before execution.
