# B2 stock response: C1–C3 producer revision

**2026-11-19 owner decision:** the period-piece writer and 703.872 MB forecast
are retained for comparison. Use the [append-only journal and replaceable
private responses](kis-stock-journal.md) for #571 deployment and recovery.

Owner chart prerequisites, 2026-11-18/19. This supersedes the **query view** of
#571 `fd5de9f5`; its RAW retention/monthly receipt design stays separate.
One symbol request returns retained OHLCV and all ten indicator series together.
Toggles and retained-period changes select columns/rows in memory, without new
server requests or recalculating an indicator. No Worker, UI, auth, workflow,
data update, collection or deployment is implemented here.

Main review: [C1–C3](https://github.com/kco994553-star/Investment-System1/issues/437#issuecomment-6977823569).
The old `/2` latest-only output must not be called DC-58 ready. Its old277.587MB
forecast did **not** include these daily series or the new bounded-read layout.
Use the new measurement below; do not carry that forecast over.

## C1: producer-calculated series

New response `kis-stock-view/1`, private only. The proposed external route is
Main's `/kis/stock?symbol=...`; old routes remain until atomic cutover.
The new wrapper is explicit: it is not the old `kis-chart-view/2` body.

| Field | Meaning |
|---|---|
| `symbol` | Exact original provider symbol. Reuse the pinned code→KIS mapping. A storage filename's underscore is not a slash alias or verified security ID. |
| `evaluation_day` | Pinned requested trading day, not capture/current day. |
| `fields` / `rows` |17-column vectors, sorted unique retained sessions. Same dates for OHLCV and indicators. |
| `chart` | `kis-chart-metadata/1`: original basis/currency/split evidence, display tier/holds, original capture clocks; no repeated bar objects. |
| `indicators` | `kis-indicator-series/1` metadata: seed policy, reference tier, sparse `reason_runs`, display. `adopted_values_included=false`. |
| `latest` | Unchanged saved technical/measures objects; verified and reference values remain separate. |
| `coverage` | Actual retained start/end/session count, `ALL_RETAINED_SESSIONS`. Missing sessions are not filled. |
| `raw_fields` / `raw_rows` | Only for SPLIT_ADJUSTED display: original RAW rows alongside confirmed-split display rows. Absent for RAW; no duplicate RAW payload. |

Exact17 fields:

```text
date,open,high,low,close,volume,amount,
SMA_20,SMA_60,SMA_120,
BOLL_MIDDLE_20,BOLL_UPPER_20_2,BOLL_LOWER_20_2,
RSI_14,MACD_12_26,MACD_SIGNAL_9,MACD_HISTOGRAM_12_26_9
```

OHLCV/amount decimal strings/null are preserved; indicator floats are not rounded
for storage. Volume comes from the same row, with the original scope restriction.
Volume absence alone does not block close-only indicators. Amount is not VWAP.
`reason_runs` uses inclusive zero-based `{field,from,to,reason}` over the complete
returned row sequence; do not rebase the reason coordinates after a UI filter.
Warmup null, undefined RSI on constant prices, gaps and arithmetic failures stay
null. MA120 first appears at the120th valid retained session; MACD signal at34.
Initial seed uses **all retained history**, never the selected screen period.

Both the latest-value path and new series call
`technical_display.close_indicator_paths` → the existing GSQ015 kernels.
The formula source is not copied into JS. The JS reference only verifies bytes,
decodes packets and assembles vectors. Current-snapshot restated price basis is
not a historical PIT signal. Only RAW MODP0 and confirmed splits through the
evaluation day are supported; MODP1/dividend-adjusted data cannot prove a split.
Already adjusted rows are not adjusted again. Reviewed split/restatement changes
to old derived periods require a new revision reference and charged new bytes.

All series are `UNVERIFIED_REFERENCE`; this addition promotes no security/action
evidence. The same six saved WITHHELD cases remain held, with no reference series
values. Latest raw/adopted numbers and original null reasons are unchanged.

## C2/C3: bounded fetches and smaller parse units

New manifest `kis-private-delivery/3`, layout `B2_STOCK_SERIES`. No silent `/2`
reinterpretation. These are stored files, not additional frontend requests.

| Stored path | Consumer |
|---|---|
| `manifest.json` | Small top manifest:32 stock bucket pins,32 QGV bucket pins, QGV context pin, offline writer pin, evaluation day and ledger. |
| `stock/latest/BB.json` | `kis-record-pack/2`, kind STOCK. Decode exact provider symbol; includes header, latest technical/measures, series metadata and that symbol's piece pins. |
| `stock/pieces/<symbol-hash>/<kind>/<period>-<sha>.json` | `kis-stock-piece/1`: one symbol's price+indicator rows, same17 fields. |
| `qgv/buckets/BB.json` | Code-row QGV packets, separate from provider-symbol stock keys. |
| `qgv/context.json` | Original shared QGV context, population, exclusions/counts/clocks. Raw details remain reproducible, not an empty result. |
| `writer-manifest.json` | Full file list, closed-piece pins and growth ledger for the offline writer. **Worker does not fetch or parse it.** |

Bucket rule is unchanged SHA256 UTF8 first byte mod32. Packet codec is the
existing `decodeRecord`. Piece kind is: closed3-calendar-year era, completed
year inside the open era, completed current-year quarter, completed month in
the current quarter, then current month. Completed pieces are content addressed;
the current month changes with new sessions. Month/quarter/year/era sealing copies
are charged in addition to prior objects. Old Git objects are not deleted for
budget credit. Raw monthly price parts keep every source row/revision separately.

For five calendar years there are at most4 historical pieces +3 completed
quarters +2 completed months +1 active month =10. Thus a cold symbol open takes
**1 manifest +1 stock bucket +at most10 combined pieces =12 data-file fetches**.
DO admit/release add2 subrequests, still below50. No GraphQL bulk-query behavior,
Worker cache hit, Git delta compression or frontend formula is assumed.
The frontend makes one stock request and keeps the response in private memory.
`readStock(readBytes, exactSymbol)` is the pure reference in
`research/kis_stock_reader.mjs`; Main owns the authenticated byte reader/route.

`전체` means all actually retained history; nothing is cut to five years. Longer
history adds one era file per three years plus boundary fragments. Never report
`ALL_RETAINED_SESSIONS` after silently trimming. A response/file over the unchanged
1.8MB producer/2MiB Worker cap fails, preserving the previous good batch; further
retention needs an explicit consumer paging/budget decision, not implicit loss.

**12/minute is not a token-budget proof:**12 data calls ×12 cold opens/minute
would be8640 GitHub calls/hour, above5000. Main must charge actual data calls
against remaining token budget (or bound worst-case opens to6/minute with room
for other work). Producer does not change the limiter/guards. Authentication,
NEVER/no-store, account changes and disposal of in-memory prices stay Main-owned.

## Sizes, storage and opening time

Measurements are recorded by `implementation/tools/kis_stock_capacity.py` using
default zlib1 Git loose-blob accounting without delta/deletion savings. Its
held-day1 case reuses the pinned saved latest/QGV results and adds only the new
daily series. The five-year case uses synthetic prices with held metadata for
capacity; it is not a real five-year acquisition, eligibility result or QGV run.

The first implementation **exceeds the previous300MB/year target** once daily
series, bounded reads and RAW retention are included. The final measured table
and component totals follow. Do not activate a writer by claiming
the old277.6MB forecast still holds, and do not raise the guard to make it fit.

| New `/3` measurement | Held day1,100 sessions | Five-year synthetic capacity,1260 sessions |
|---|---:|---:|
| Series / output files |517 /2133|517 /4203|
| Cold data-file reads per symbol, measured maximum |6|10 (calendar bound12)|
| Largest file parsed by the chart reader |102,099B|176,067B|
| Largest stock latest bucket |102,099B|118,379B|
| Largest QGV code bucket |19,988B|19,988B|
| Shared QGV context |117,436B|117,436B|
| Small manifest |9,395B|9,404B|
| Offline writer file (never read by Worker) |565,426B|1,135,301B|
| Largest combined symbol response, JSON /gzip |46,558B /13,089B|318,232B /75,834B|
| Largest aggregate data bytes fetched for one open |134,282B|422,700B|
| New series+projection time, excluding old QGV calculation |19.80s|144.76s|

Held-day1's new series end values match saved latest reference values with
**0differences**; old QGV/technical/measures numbers were not recalculated.
An additional format-only audit found0differences in517 price/latest/display
projections and523 QGV rows/context; six holds remain. No original result engine
was rerun for that audit.
The original `/2` largest latest file was1,229,158B and QGV460,867B. `/3` uses
smaller selected buckets; its writer-only large file must never be parsed for
an interactive open. QGV context remains117KB to preserve original population/
per-code exclusion diagnostics; it is not an excuse to fetch all32 code buckets
for a one-code read. Main must measure CPU at this actual size, not the40KB example.

The inclusive **first-year estimate is703.872MB**,426.285MB above the previous
277.587MB estimate and403.872MB above the300MB target. This is a conditional
forecast based on five-year synthetic price entropy and held metadata, not
measured annual repository growth. It includes the initial five-year import:

| Included component | Decimal MB |
|---|---:|
| Latest/bucket/manifest/writer updates + active-month rewrites,252 batches |472.978|
| Month/quarter/year/era sealing copies (four-copy allowance) |57.298|
| Initial five-year derived views |53.287|
| Initial five-year full RAW records (previous held-source estimate) |52.663|
| New RAW rows (previous held-source estimate),252 batches |26.646|
| Daily source-hash summaries/final pointers |1.000|
| Git trees/commits, other features and reserve |40.000|
| **Total** |**703.872**|

The active-month allowance uses the maximum complete-month mean across the
synthetic history, not the cheapest month. Mutable blobs use the full measured
latest/index shape, without assuming useful Git deltas. No old objects or receipt
assets are deleted for credit. Receipt release bytes remain outside this Git
total. The same-sized continuing-year scenario is597.923MB before future index
growth; it is not a measured second year. The old view-only ledger cannot certify
300MB including RAW. Budget/cold-view placement is therefore an unresolved
activation condition even though C1–C3 data contracts/tests are supplied.

The old `/2` did not contain indicator histories, so its response/open time is
not a feature-equivalent baseline. Main measures the current real Worker/phone
and the staged new handler before approval. A local Node decode/hash/serialize
measurement is separately labelled; it is not Workers Free10ms CPU compliance,
network time, browser open time or deployment verification.
The held-day1 largest-response sample took34.91ms on first local Node reference
read/hash/decode/serialize, then3.59–10.86ms across three warm samples. All bytes
were already in memory, and input JSON loading was outside that timer. These
are wall-clock timings, not Worker CPU measurements; they do **not** certify10ms.
Real old/new Worker and phone-open times remain Main's staged measurements.

Reproduce the capacity calculation, without a data update or external request:

```sh
PYTHONPATH=implementation/src python3 -S implementation/tools/kis_stock_capacity.py \
  --archive "$PRIVATE_INPUT/saved-compact-day1.tar.gz" --expected-sha256 "$ARCHIVE_PIN" \
  --synthetic-sessions 1260 --receipt "$RUNNER_TEMP/stock-capacity.json"
```

Omit synthetic-sessions for the held-day1 projection. The saved compact archive
is checked once against its preserved independent pin. Synthetic capacity output
cannot be saved through the optional real-bundle argument. Stdout contains counts
only; receipts/output stay private. This does not hydrate sources, compute old
QGV again, acquire five years or publish a batch.

Main decision alternatives if300MB remains binding: keep query-ready dynamic
views outside repeated Git commits in an approved private object/asset store,
with small immutable pins in Git; or approve a changed storage budget. Monthly
**receipt** release approval is not automatic approval to serve dynamic query
assets. This PR creates no storage service/upload/token/workflow. Reformatting
does not discard source rows or loosen per-file limits.

## Commands, fixture and cutover

```sh
PYTHONPATH=implementation/src python3 -S -m investment_system.research.kis_rebuild \
  --request "$INPUT/rebuild.json" --expected-request-sha256 "$REQUEST_SHA256" \
  --layout stock --bootstrap --check-only --run-receipt "$RUNNER_TEMP/stock-run.json"
```

For a subsequent staged writer replace bootstrap with
`--previous-manifest "$DATA/writer-manifest.json" --expected-previous-sha256 ...`.
This is the **offline writer** manifest, not the small Worker `manifest.json`.
Output uses the existing new-directory staging guard. Failures/size/budget exits
remain2/3/4/6, not empty success. No automatic data commit or provider request.
An unchanged run is deterministic and adds no new growth charge. The view ledger
does not by itself enforce the combined RAW+receipt-summary+Git300MB budget.

Public synthetic bytes: `implementation/tests/fixtures/kis-stock-wire-v1.json`.
File SHA256: `084c9de2f4c05e2277899470179dc151420d8780eb04de4d448ba8cf86a56c23`
(22,975B).
It contains exact file text so byte hashes survive the test; do not parse then
reformat stored files before checking pins. Main can pass
`async path => new TextEncoder().encode(example.files[path])` to `readStock`.
140 sessions; five file reads; last MA20=10, MACD signal=0, RSI=null because all
price changes are zero. Holds/gaps/split/MODP1, corrupt/missing pieces, exact
symbol/storage-name mismatch and budget failures are in the producer tests.

1. Keep the old data head/reader active; no parallel daily old/new writers.
2. Main stages `/3` manifest and transitive file pin validation plus the pure
   reader. A bad/missing piece rejects the batch; do not shrink successful rows.
3. Compare staged single-response OHLCV, series/holds/latest against producer
   fixtures and the approved private projection; separately measure real CPU/time.
4. Settle the inclusive storage/token budget, then atomic consumer+data cutover
   through Main's approved workflow. No partial schema switch or automatic deploy.

#575 remains an unadopted financial research result. No additional definitions,
coverage runs or unrelated research are part of this foundation change.
