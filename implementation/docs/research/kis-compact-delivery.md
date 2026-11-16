# Compact private delivery, version2

Recommendation: **shared latest indicator file + B2 immutable daily RAW chart
pieces**, with sealed month/year pieces and a separate cold-source decision if
the300MB cap includes source history. Calculations and original evidence stay
in the existing engines/retained source store. This is a private query projection,
not a new model, verified security master, source archive or official publication.
Main owns all Worker/UI/workflow changes below; none are implemented here.

## Measured cost and annual planning

MB means1,000,000bytes;252 committed trading-day updates/year. Git columns use
zlib1 encoding of `blob <length>\0<bytes>`, **without any delta saving**.
An isolated synthetic Git blob matched actual Git's default loose-object level1.
The original five-year synthetic profile used level6; its metadata costs are
calibrated with measured day1 level1/level6 ratios for the estimates below.
No fixed4x compression assumption is used. Git tree/commit/other-feature growth is
a separate reserve; actual packed repository growth is not measured by a one-day
run. Five-year figures are capacity estimates, not actual five-year acquisition.

| Layout | New Git blobs/day | 252-day view payload | With bootstrap/sealing/reserve | Worker chart reads / Main change |
|---|---:|---:|---:|---|
| Current2069files,100sessions (actual) |5.738MB|1445.9MB|Already over300MB|1 full chart; existing readers|
| Full legacy five-year files (calibrated synthetic) |40.627MB|10238.0MB|Over300MB|1 large chart; no format improvement|
| A: latest indicators pooled, chart still rewritten in full |40.058MB|10094.7MB|Over300MB|1 full chart; add latest-file selection|
| A+B1: current-month bucket files rewritten |0.646MB|162.7MB|285.8MB estimate|Up to19; shared latest decoder + period chart reader|
| **A+B2: whole-market daily file written once** |**0.453MB planning**|**114.1MB**|**237.3MB estimate**|Up to41; same decoder + daily/period assembly|

The B1/B2 estimates replace synthetic latest/QGV cost with measured actual day1
cost. B2 conservatively charges each new day as the actual maximum day's **raw**
45,925bytes rather than assuming its compressed size. Both rows include23.146MB
for month/year sealing copies, a60MB one-time five-year bootstrap allowance, and
40MB for Git metadata and other data-branch features. These are budgets/estimates,
not observed annual growth. B1 has less room for higher-entropy recent-month data;
B2 avoids repeatedly writing the same current-month bars.

Actual day1 compact B2 projection:174files /6,246,362bytes; new loose blobs
1,995,936bytes before Git metadata. Latest indicators1,229,158bytes, QGV view
460,867bytes, chart index263,249bytes and manifest74,936bytes. All individual files
remain below the existing1,800,000-byte producer /2MiB Worker limits.
Latest indicators average2377bytes/series after sharing (517series).
All517 indicator/measures rows and all523 existing QGV result rows decode to the
same old values/states. Main's current validators accepted decoded analysis517,
measures517 and QGV1, rejected0. This is a direct Node codec/validator check,
**not** Worker integration, authentication, browser or deployment.

The five-year synthetic capacity run had517series×1260sessions. Its latest
indicator file716,428bytes is not substituted for the larger actual day1 cost in
the forecast. All six actual display holds are preserved; no old result was
promoted. The compact projection and full legacy rebuild are separate operations.

## What must be outside repeated data-view commits

The command emits **derived views only**. It does not copy raw MODP0 pages,
monthly source journals or source receipts into every data commit. Read sources
from the existing private collection/handoff ref and keep a pinned source locator.
Existing raw files already in data remain historical objects; this proposal does
not erase them or use force push.

Raw retention is still required. #564's measured full receipt/header metadata
alone was570,117bytes/capture for517series: repeating that shape for252captures
is143.7MB before source rows/manifests/Git overhead. Including the517per-series
manifests and517pointers, actual default-level1 Git metadata was1,294,109bytes
for this capture. Repeating that shape252times is **326.1MB/year without new raw
rows or active-month blobs**. This is a capture scenario, not actual annual growth;
future five-year manifest size could be larger. It is **additional** to the
view forecast. Keeping another branch does not reduce the same repository's
physical object storage. If the300MB objective is meant for the entire private
repository/all refs, or raw changes must also be copied into data, this view-only
estimate is insufficient. With the current source format the no-delta scenario
already exceeds300MB on source metadata alone. It requires a separately validated
source-format reduction or approved outside-Git cold storage. R2 is an owner/Main
decision, not enabled here. The local directory/archive input interface is
unchanged if Main hydrates approved cold objects before this offline command.

**No claim of overall300MB achievement is made.** The default compact ledger
charges at most260MB/year for view blobs, reserving
40MB toward the300MB target. It charges zlib1 changed blobs plus an uncompressed
manifest allowance, never credits deleted paths, and assumes no delta benefit.
It requires the previous pinned manifest for updates; explicit bootstrap is the
only initialization path. A repeat of identical bytes consumes no new charge.
Its year comes from the supplied QGV calculation clock, so a January1run using
December's last trading day does not charge the old year. Historical replay
clocks must not be used to publish a supposedly current batch.
Exceeding the budget fails with exit6 and keeps the previous batch. This is not
a substitute for Main measuring actual Git objects/other features after commits;
nondefault Git compression or more than252updates must be included in planning.

## Files and unchanged external routes

| Private stored path | Schema / contents | Main Worker action |
|---|---|---|
| latest/indicators.json | kis-record-pack/2, kind INDICATORS; all symbols, latest technical+measures only | Existing /kis/analysis selects technical; /kis/technical selects measures |
| qgv/latest.json | kis-record-pack/2, kind QGV; context+encoded original result rows | Decode to existing kis-qgv/1 response for /kis/qgv; raw detail omitted |
| chart/index.json | kis-chart-index/2; shared headers, pieces, evaluation date | Existing /kis/chart reads selected symbol bucket and dates |
| chart/year/YYYY/BB-HASH.json | kis-chart-piece/2, immutable RAW rows for one bucket/year | Fetch selected bucket once for each requested prior year |
| chart/month/YYYY-MM/BB-HASH.json | Same, completed months of current year | Fetch selected bucket for requested completed months |
| chart/day/YYYY-MM-DD/all-HASH.json | Same, all symbols for one current-month day | Fetch that day's file once; keep only requested symbol |
| manifest.json | kis-private-delivery/2; paths/sizes/SHA256, pieces, annual ledger | Validate whole batch and activate version2 atomically |

B1 comparison replaces daily pieces with `chart/recent/YYYY-MM/BB-HASH.json`.
It is not the recommended default. Period shards use32buckets, chosen by
SHA256(UTF8 exact symbol).first_byte modulo32, rendered as two decimal digits.
The bucket number is a storage partition, never a security or issuer ID. Do not
lowercase symbols, infer aliases, combine class shares or shrink a population.

The external five Worker route addresses need not expand. Only the chart response
needs a new **kis-chart-view/2** reader. Analysis/measures/QGV can keep their old
response shapes after decoding. Main must not serve the new packed wire directly
to the old validators, or label a chart view as retained source kis-bars/1.
The old data must remain active until those changed consumers are installed.

## Latest-value encoding and Main's reusable reader

The pure reference module is
`implementation/src/investment_system/research/kis_compact_reader.mjs`:

```js
const entry = decodeRecord(indicatorsPacket, exactSymbol);
// entry.technical and entry.measures are the old complete objects.
const header = decodeRecord(chartIndex.headers, exactSymbol);
const row = decodeRecord(qgvPacket, originalCodeRowId);
// QGV response: {...qgvPacket.context, rows: decodedRows}
```

`layouts` stores ordered object-key lists. `[0,layoutId,values]` is an object,
`[1,values]` an array, and `[2,sharedId]` a repeated value. Other JSON scalars retain
their original types. Shared nodes form a DAG; unknown tags/widths/refs/cycles are
rejected. The selected row is decoded individually, so Worker need not expand
all indicators. Null is not zero, a diagnostic value is not an adopted value, and
all display/hold/warmup/reason metadata remains intact. Python/Node tests use the
same wire and expected values. Main can reuse this pure file rather than duplicate
the codec; any shared-import guard change remains Main-owned and narrowly scoped.

QGV retains every original row/axis/factor/gate/count and the original population,
clock, model/configuration/source metadata. Only `private_raw_detail` is absent;
`raw_detail_state=REBUILDABLE_NOT_IN_VIEW` makes that explicit. It is not an empty
raw-detail result. Full details remain reproducible with legacy layout and can be
archived separately or on an approved monthly schedule. They are not a new score.
Private rank stays null; no reference sample, weights or official results change.

## Chart assembly and provenance

A piece has `fields=[date,open,high,low,close,volume,amount]`, RAW basis, currency
and `rows[exactSymbol]` arrays. Decimal strings/nulls are retained unchanged; no
missing session is filled. Original per-row response hashes/capture metadata stay
in the monthly source store. A piece hash is a **derived-view** hash and must not
be displayed or passed off as an original response hash.

The index carries the original header evidence, confirmed splits, held ranges,
unknown identity and reference display, without duplicating daily bars. Select
the bucket, verify each file's byte size/SHA, concatenate dates and reject duplicate
dates. Return `kis-chart-view/2`, with
`row_source_scope=DERIVED_VIEW_RETAINED_ORIGINALS_SEPARATE`. The Python reference
`assemble_chart` compares all actual economic rows and preserves the display.

Source pieces always remain RAW, even if the requested display uses approved
split-only adjustment. Reuse the existing adjustment kernel after assembly:
only CONFIRMED events through the evaluation day, pre-event prices divide by
new/old ratio, volume multiplies, amount remains RAW. No MODP1, dividend adjustment,
future event or second adjustment is allowed. If the consumer lacks that supported
helper it must retain RAW display; it cannot silently call it adjusted.

Prior full years are year pieces; the current year's completed months are month
pieces, with current-month daily pieces. This bounds the full-window chart read
to1index +at most6year +11month +23day files =41fetches, below50. The synthetic
fixture used36 for B2 and17 for B1; actual count depends on dates/calendar. Worker
returns only the requested series. One historical year shard was below the tested
716,428-byte maximum; every producer file is independently capped at1.8MB.
Do not fetch every bucket or every issuer's detail to draw one chart.

At month/year rollover a sealed aggregate is written once. Its rows may duplicate
older daily/monthly Git objects; the forecast explicitly charges both sealing
copies. Old periods never contain a current run timestamp or a whole-snapshot hash
that would force them to change every day. Backfill/corrections create a new
content-addressed piece and require a review reference when an existing logical
period changes; old objects are preserved. Source ingestion must accumulate
history, not replace it with a rolling100-row response.

## Main acceptance boundary

Authenticate and enforce the current private scope/NEVER contract as before.
Keep the current per-file cap, verify manifest/input/date/schema consistency and
file pins before decoding, reject partial batches and preserve the old data on
failure. Only the explicit derived prefixes are produced; unrelated classification,
macro/news and raw-source paths must not be overwritten by this command. Never
upload private output to Pages/public logs. No Worker, workflow, authorization,
storage setting or deployment was changed in this PR. Main must stop parallel
daily legacy publication after the compact cutover; keeping both writers active
would defeat the budget. The previous-manifest pin must come from the actual data
head used for the atomic commit, not a stale alternate ref. Other feature/raw
updates must also fit the reserved allowance or be budgeted separately.
