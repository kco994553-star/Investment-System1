# Offline KIS rebuilding

Owner scope: research/data command only. No Worker, frontend, workflow, guard,
collection, deployment or official-result change. Runtime: Python3.12 standard
library and existing repository modules; no pip package, key, HTTP or Google/KIS
login. `python -S` works. The test subprocess refuses socket connections as well.
Existing provider modules may be imported by package initialization; their
collection functions are never called by this entry point.

## One entry point, two delivery layouts

```sh
PYTHONPATH=implementation/src python3 -S -m investment_system.research.kis_rebuild \
  --request "$INPUT/rebuild.json" --expected-request-sha256 "$REQUEST_SHA256" \
  --layout legacy --output-dir "$RUNNER_TEMP/kis-next" \
  --run-receipt "$RUNNER_TEMP/kis-run.json"
```

Legacy emits exactly the existing `chart/`, `technical/`, `measures/`,
`manifests/` and `qgv/latest.json` paths. It calls
`calculate_and_project` → `reference_files`, and `official_reference` using
canonical calc23.1. It does not import the unmerged555 engines or copy saved
scores. RAW/MODP0 input, approved split-only adjustment, the reference display,
hold rules and THREE_AXES_REQUIRED total policy remain unchanged.

Compact uses the **same calculation iterator**, followed by a view projection:

```sh
PYTHONPATH=implementation/src python3 -S -m investment_system.research.kis_rebuild \
  --request "$INPUT/rebuild.json" --expected-request-sha256 "$REQUEST_SHA256" \
  --layout compact --recent daily --bootstrap \
  --output-dir "$RUNNER_TEMP/kis-next-v2" \
  --run-receipt "$RUNNER_TEMP/kis-run-v2.json"
```

For daily updates replace `--bootstrap` with
`--previous-manifest "$DATA/manifest.json" --expected-previous-sha256 "$PREVIOUS_SHA256"`.
Bootstrap must be explicit; silently resetting the growth ledger is forbidden.
Use `--revision-reference` only for a reviewed old-period correction/backfill.
The compact paths/reader changes are in [kis-compact-delivery.md](kis-compact-delivery.md).
Do not switch the service data until Main's version2 reader is ready.

Both writers stage a complete **new** directory and rename it only on success.
They do not overwrite a previous good directory or push a branch. The CLI keeps
the existing outside-Git private-output boundary; Main should use RUNNER_TEMP,
then its authenticated private writer. This workspace has Git ancestors even
under /tmp, so actual validation here used the read-only command below. Synthetic
tests also exercise the pure staging writer. No boundary was weakened.

## Pinned input request

The request is UTF8 JSON, schema `kis-offline-rebuild/1`, scope OWNER_PRIVATE_ONLY.
All paths below are relative to the request directory; parent escapes and symlinks
escaping that root are refused. No input is downloaded by the command.

| Field | Meaning |
|---|---|
| evaluation_day | Requested trading evaluation day; never replaced by capture/current day |
| calculated_at | Explicit timezone-aware calculation/knowledge clock, fixed for replay |
| series_id_prefix | Original internal analysis context prefix, e.g. OWNER_KIS:; not a security ID |
| store | Local monthly store directory, **or** archive descriptor below |
| series_index | `{path,sha256}` pin for the existing #564 query-files/source index |
| financial | `{path,sha256}` for the exact approved sec-qgv2.json bytes |
| symbols | `{path,sha256}` for the exact existing code→provider route lookup |
| monthends | Optional pinned eligible official-engine month-end input; omitted means unavailable |
| price_basis | RAW default; SPLIT_ADJUSTED only with existing confirmed split/coverage evidence |

Archive store form: `{archive:"monthly.tar.gz",sha256:"…",prefix:"store"}`.
It verifies the archive, ignores its old derived chart views, and loads only the
monthly journal/receipt/manifest tree. One series is staged at a time; no archive
member is extracted with extractall, and source-path escapes are rejected.
The archive source members are held in RAM; ordinary directory input is preferred
for large five-year operation. One retained contract is cached, not all issuers'
five-year histories.

Each existing source-index row supplies `code`, `symbol`, `series_id`,
`store_manifest_sha256`, `source_contract_sha256`. The first is the original code
row; provider symbol and storage fingerprint are not verified fixed security IDs.
The pinned index must match the selected committed source manifest. A pointer
that has advanced since the request was frozen causes failure, not a latest-input
substitution. Keep missing original population members in the financial snapshot;
do not narrow it to received price series.

**Three different hashes:** the original pretty-printed normalized input's byte
hash is recorded in the independently pinned receipt metadata and cross-checked
against the pinned index. The month/receipt byte hashes validate reconstructed
input values. The engine's canonical-object hash is computed from those values.
Reconstruction does not reproduce original JSON key order/whitespace, and does
not call a recorded original-file hash a freshly computed canonical hash.

The clock must be at/after source capture and financial availability. New receipt
times are never backdated. Five years of daily bars do not alone verify security,
share basis, actions or financial history. Missing eligible month-end valuation
inputs remain missing; the command does not fabricate them from arbitrary bars.

## Read-only exact comparison

```sh
PYTHONPATH=implementation/src python3 -S -m investment_system.research.kis_rebuild \
  --request "$INPUT/rebuild.json" --expected-request-sha256 "$REQUEST_SHA256" \
  --layout legacy --check-only \
  --reference-index "$INPUT/data-reference.json" \
  --expected-reference-sha256 "$REFERENCE_SHA256" \
  --run-receipt "$RUNNER_TEMP/kis-compare.json"
```

The independent reference index is pinned by file SHA256 and lists every expected
delivery path/size with SHA256 **or** Git blob SHA1. It must enumerate the exact
delivery scope, never a successful subset. Missing/extra/different files fail the
run. A Git blob pin hashes `blob <length>\0<bytes>`, not file bytes alone.
Comparison is read-only and consumes one calculation pass; it cannot be combined
with --output-dir or compact layout to accidentally calculate twice or compare
different schemas. No generated raw values are written to stdout.

Held day1 authorization was limited to offline replay/comparison. Actual run:
2069 matched, different0, missing0, extra0 against private data commit
`ddde6ca32d03bd2f9aef12de7298daffa061368e`; elapsed25.80443842seconds.
Execution source commit: `9b61ea5f77f89ee79afe26863194008c04de49ff`.
All source and result byte pins, request and receipt are in the approved private
handoff, not in this public document. The6 held series remain held, all results
remain UNVERIFIED_REFERENCE, and V-missing partial totals remain null.
No data branch was updated by the command. Five-year real-data execution was not
authorized or performed.

## Failures, logs and deterministic bytes

| Exit | Meaning; Main action |
|---|---|
|0|Complete valid result/comparison; Main may validate and stage its own private update|
|2|Input/hash/scope/date/format contract invalid; keep previous batch|
|3|Unexpected calculation failure; keep previous batch and inspect sanitized receipt|
|4|Read/write/new-directory/receipt IO failure; keep previous batch|
|5|Exact comparison mismatch, including missing/extra paths; do not publish|
|6|Compact file/annual/daily capacity budget exceeded; do not trim or increase caps|

Stdout is one JSON of integer counts only. No symbol, price, raw filing, key or
exception body is logged. --run-receipt is a separate new file containing elapsed
time, sanitized reason, code-independent file hashes and counts; it is **not** a
service output and is excluded from byte comparison. Errors are never converted
to empty success. Existing good output and original source captures remain intact.

Service bytes have no wall-clock/file-mtime/commit-time injection. Same frozen
inputs, clock, code/configuration and Python3.12 runtime produce the same bytes;
tests compare fresh processes with different Python hash seeds. Pin the code ref
and retain the exact financial snapshot/lookup. Do not confuse a later execution
or delivery-generation time with the original calculation time.

## Daily work and runtime

Upstream #564 ingest appends **new/reviewed revised source rows only**. This
command then recalculates the full requested technical history for every supplied
series and the whole eligible QGV reference snapshot. It is not a stateful
incremental EMA/RSI engine. Global QGV normalization can change other companies'
scores, so updating only a selected company would be incorrect.

Sealed chart views are serialized deterministically; unchanged bytes retain the
same Git object. Only the current day's B2 file and latest views/index/manifest
need new blobs. At month/year close a sealed archive is added once. This is
incremental **storage**, not incremental **indicator math**. Main controls actual
branch updates and must not duplicate raw sources into every delivery commit.

Measured day1 full legacy rebuild+independent audit25.8s; compact projection of
the already computed day1 values4.0s (separately measured, not a timed end-to-end
combined run). A synthetic517×1260-session
technical calculation/serialization benchmark took230.3s; compact projections
took19.3s each. Its QGV packet is an explicit capacity placeholder: **no five-year
QGV runtime or real five-year execution is claimed**. Actual filesystem, CPU and
financial/eligible month-end inputs can change duration. No completed real-data
calculation was rerun merely to check status.
