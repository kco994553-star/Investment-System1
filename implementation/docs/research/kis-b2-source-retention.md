# B2 cutover and monthly private source receipts

**2026-11-19 C1–C3 revision:** the latest-only `/2` query layout and277.587MB
forecast below are preserved history, not the current chart-ready proposal.
[Stock series `/3`](kis-stock-series.md) adds per-day indicators, bounded reads,
bucketed latest values and an inclusive703.872MB first-year estimate. It does
not meet300MB; Main/owner must settle placement/budget before activation. The
RAW monthly-part/receipt retention design below is unchanged and unactivated.

Owner decision 2026-11-17: B2 is selected. This updates #567's **view-only**
planning; it does not activate a collector, release upload, Worker or data writer.
Main owns those integrations. Existing per-file limits and private/NEVER scope
remain unchanged. No source, official score, verification tier or hold changes.

## Combined data-branch estimate

Decimal MB, 517series, 252committed trading-day batches/year, 1260sessions for
the initial five-year window. Git blobs use default zlib1; no delta saving,
deletion credit or force push. This is **estimated new growth**, not the current
repository size, measured annual growth or a promise for more series/updates.

| Included part | First year, including initial five-year import |
|---|---:|
| Latest views/index/manifests + B2 day pieces, 0.452904MB ×252 |114.132MB|
| Month/year chart sealing copies, charged in addition to day pieces |23.146MB|
| Initial five-year derived views, allowance |20.000MB|
| Initial five-year full RAW records, extrapolated from held rows |52.663MB|
| New full RAW rows in immutable month parts, 0.105739MB ×252 |26.646MB|
| Daily source-hash summaries and final month pointers, allowance |1.000MB|
| Git trees/commits, other data features, uncertainty reserve |40.000MB|
| **Combined first-year estimate** |**277.587MB**|
| **Headroom below300MB** |**22.413MB**|

After the initial import, the same model is204.924MB/year (including the40MB
reserve), before future changes in series count, entropy or update frequency.
Private release assets are outside Git objects and are **not** included in this
data-branch total; their actual archive size/storage/restore behavior is still
unmeasured. Another branch in the same repository is not outside-Git storage.

Source measurement is storage-only, not a repeated indicator/score calculation:
held day1 has517series, 51,606records,100sessions across6months. Full records
roundtrip through the month-part prototype with0differences. Provider fields,
normalized bars, decimal strings, null/rejected rows, source hashes, capture
times, receipt references and revision chains all remain in the price record.
Aggregate original-month parts cost4,171,969Git bytes; largest all-series day
part costs105,739Git bytes. Bootstrap uses
`ceil(4,171,969 ×517 ×1260 /51,606) =52,662,560`bytes. New days use the largest
observed day, not its mean. Real five-year prices/entropy are not measured.

The old60MB view-bootstrap allowance was not a measured Git cost. The existing
five-year synthetic profile cost12,345,881bytes at zlib6. Replacing its small
latest/QGV placeholders with the larger held-day1 metadata and applying the
observed1.143154level1/level6 correction gives14.315MB. The new allowance is
20MB, leaving5.685MB within that component; this adjustment is explicit, not
hidden as a new compression assumption. The114.132MB annual view figure still
uses the larger held-day1 latest/QGV cost. Calculated scores are not recomputed.

**Moving receipts alone is insufficient.** Do not rewrite an entire active
source month on every capture. Source price files must be immutable **new-row
parts within a month**, not daily copies of the whole rolling100-day response.
The prototype also measures a current-month-rewrite scenario for comparison:
0.459MB/day mean,0.896MB/day maximum, giving366.617MB/year even at that mean
when the other inclusive costs are added. It is a storage scenario using the
same held rows, not observed daily captures or the proposed writer.
The combined estimate depends on both changes.
Do not run old and new daily publication in parallel after cutover.

The current `kis_compact` ledger enforces **view** growth only. It does not yet
enforce277.6MB or the combined300MB total. Main's eventual commit step must charge
new view blobs + new RAW blobs + summaries, track actual tree/commit growth,
and stop while keeping the previous good batch if the combined budget or an
individual1.8MB producer/2MiB Worker limit fails. No guard/cap was relaxed.
No corrections/backfills or more than252updates are silently included: charge
them against the remaining allowance and stop/rebudget before exhausting it.

## Git versus monthly private release

Proposed source paths below are a **storage design**, not new Worker routes or
an activated replacement for #564. Existing retained sources stay intact.

| Location | Contents and invariant |
|---|---|
| Git `raw/prices/YYYY-MM/parts/<content-sha256>.jsonl.gz` | New/reviewed revised rows only, grouped by month and series. A line is `[series_id, original_record]`. Stable series order preserves each series' append order. Never deduplicate revisions by date. Month directories are the monthly price pieces; no repeated full-month re-sealing is needed for raw data. |
| Git `raw/summaries/YYYY-MM-DD/<capture-root>.json` | At most3KiB: schema/scope, capture ID, actual capture time, price-root, metadata snapshot-root, row/series counts, new part path/size/hash, private repo/tag locator. No full receipts or per-series manifest lists. Multiple changed months require bounded split summaries; count their bytes. |
| Private release tag `kis-source-YYYY-MM` | Deterministic monthly archive/catalog of original receipt bytes, original manifest/pointer bytes, normalized contract headers, per-capture source index and revision review references. Member path/bytes/SHA256 and capture subtree roots. No reconstructed timestamps. |
| Git final month pointer | Small repo/tag/asset ID/name/bytes/SHA256 and catalog-root pin after download-back verification. The catalog itself stays in the release. No token/authenticated URL. |

Summary allowance1MB covers252×3KiB plus12small final pointers. It is a planning
limit, not implemented enforcement. If a real summary exceeds that size, do not
discard members: split/measure and charge actual bytes before publication.
The shared delivery `manifest.json` needed by Worker remains in Git and is
already included in the view estimate. It is separate from cold **raw-source**
manifests. Exact old receipt/manifest bytes are preserved, not rewritten JSON.

Use the existing `tools/raw_store_release.py` upload/download-back/hash pattern;
its current workflow is a fixed TrackA archive copy, **not** a KIS schedule.
Reuse the helper without changing/running that workflow here. Main must confirm
the destination repository is PRIVATE, credentials are scoped there and restore
works. Its upload MIME is presently zip; choose a monthly zip wrapper or make
the small media-type change when Main connects it, rather than pass tar as zip.
API/storage/permission success has not been verified for these proposed assets.
Plan bounded64MiB transport parts plus one member catalog if a monthly archive
grows beyond that size; pin each part and the full member root. This is a
proposed archive partition, not a change to Worker limits. Monthly asset bytes
and release quotas must be measured/confirmed before activation.

### Open month, sealing, failure and replay

1. Validate existing pins, append only new/reviewed rows to immutable price parts.
   A duplicate capture changes neither rows nor summary; content changes require
   an explicit reviewed revision reference. Preserve earlier records and reasons.
2. Build the cumulative **open-month** receipt archive with a new generation name.
   Do not wait for month end on an ephemeral runner. Upload the new generation,
   download it back, verify whole-asset and every member/capture root. Originals
   stay in runner/source storage until this durable step succeeds.
3. Only then atomically commit the new price parts + small daily summary + query
   bundle. Upload failure, missing original, partial page or pin mismatch is a
   failure, never empty/no-change success; keep the previous data head.
4. At month close seal a final immutable archive. Retain the previous verified
   generation until a restore from the new one succeeds. Asset cleanup, retention,
   token scope and publication are Main decisions; this PR deletes/uploads none.
5. A daily summary pins its immutable **capture subtree root**. The later monthly
   bundle has a different whole-asset hash and location. A resolver may move the
   transport location only through a verified month catalog preserving the exact
   old capture root and original bytes. Never substitute the newest receipt or
   call an unpinned current release name historical evidence.
6. Hydrate a temporary #564-compatible source tree from Git full price records and
   the verified monthly metadata snapshot before `kis_rebuild`. Re-encoded gzip
   is not the original compressed prefix: materialized month/manifests/index and
   rebuild request need **new pins**, linked to both original capture roots.
   Preserve original manifest hashes in the cold archive. Reconstructed contract
   values, per-row provenance and header's original-file pin must be crosschecked;
   never re-label a new byte hash as the old hash. This hydration adapter and its
   end-to-end replay are not implemented/validated by the sizing prototype.

Original publication, trading, capture and knowledge times stay separate. Monthly
upload/seal time is a transport time, not historical system availability. RAW
MODP0 and confirmed splits only; MODP1 never proves a split. No verification
upgrade or removal of the six existing holds is part of storage migration.

## Worker paths and fields: Main cutover checklist

External addresses need not change. These are the #567 producer's actual paths
and fields; source-release paths above are never fetched by the chart Worker.

| Existing request | New stored path | Consumer work |
|---|---|---|
| `/kis/analysis` | `latest/indicators.json` (`kis-record-pack/2`, INDICATORS) | `decodeRecord(packet, exactSymbol).technical`; return existing technical object. |
| `/kis/technical` | Same file | Select `.measures`; return existing measures object. |
| `/kis/qgv` | `qgv/latest.json` (`kis-record-pack/2`, QGV) | Preserve packet.context and decode original code rows. `raw_detail_state=REBUILDABLE_NOT_IN_VIEW`; not an empty raw-detail result. |
| `/kis/chart` | `chart/index.json`, then selected year/month/day pieces | New response `kis-chart-view/2`; preserve headers/display, assemble RAW rows, verify piece byte size and SHA before approved adjustment. |
| Batch pin | `manifest.json` (`kis-private-delivery/2`, `layout=COMPACT_DAILY`) | Verify evaluation_day, files/pieces path/bytes/SHA, growth ledger; atomic activation only. |

Chart index fields: `evaluation_day`, `buckets=32`,
`bucket_rule=SHA256_UTF8_FIRST_BYTE_MOD_32`, `headers` (packed), `fields`,
`row_source_scope=DERIVED_VIEW_RETAINED_ORIGINALS_SEPARATE`, `pieces`.
Each piece reference is `{kind,period,bucket,path,bytes,sha256}`. Paths:
`chart/year/YYYY/BB-HASH.json`, `chart/month/YYYY-MM/BB-HASH.json`,
`chart/day/YYYY-MM-DD/all-HASH.json`. Each piece has `basis=RAW`, `currency`,
`fields=[date,open,high,low,close,volume,amount]`, `period`, `rows[exactSymbol]`.
Prior-year pieces use the selected bucket; completed current-year months use
the selected bucket; current-month days use `all`. No symbol casing/ID inference.
Maximum planned fetches:1index+6year+11month+23day=41, not every bucket.

1. Pin current legacy data/source refs and keep them active; do not redownload
   or recalculate already validated day1. Preserve the old snapshots in history.
2. Main installs the pure `research/kis_compact_reader.mjs::decodeRecord`, chart
   assembly, schema/size/hash checks and the private route readers in one staged
   consumer version. Old and new schemas must be explicit; never feed packed wire
   to a v1 validator or label a derived chart as retained-source `kis-bars/1`.
3. Reuse the existing compact day1 archive and decoded consumer evidence for
   acceptance. Verify route-specific selected objects and chart assembly with
   unchanged values/holds. Node evidence is not browser/auth/deployment evidence.
4. Connect the cold source restore and keyless rebuild command in runner staging,
   verify both source roots and all new bundle files, then atomic data commit.
   No partial consumer switch. On any failure continue serving the old bundle.
5. Activate B2 only after consumer readiness, then stop the legacy daily writer.
   Do not put new daily receipt/manifest copies or duplicate raw bodies in Git.
   Later cleanup must not erase old good refs or rewrite history for this budget.

Main still owns Worker/cache/auth/NEVER handling, workflow, release upload and
cutover approval. Codex supplied producer/reader prototype/contracts; actual
authenticated route, browser, release restore, data update and deployment are
**not executed** by this change.
