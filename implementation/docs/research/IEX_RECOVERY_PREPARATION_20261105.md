# IEX 2026-11-02 recovery preparation — not execution authorization

One Main location request was posted to #437 on2026-11-05: comment6645770798. It identifies run41759732114, the already examined Pages artifact, operational input hashes, previous private manifests and six monthend bundles. These locations are not searched again. Main should return an exact retained manifest/artifact/path/hash, or confirm no separate retention. No reply is treated as neither existence nor absence.

## Conditional minimum acquisition proposal

If no retained copy is identified, the target is exactly the TOPS1.6 **20261102** file. No nearest-prior-day fallback is allowed. Existing `iex_hist.tops_files`, `gcs_metadata_url`, `file_checks`, `session_ns`, dated symbol mapping and C parser semantics are reused; `fetch_day` must not be invoked unchanged because it permits nearest-day selection and whole-stream retries.

The earlier shorthand 'one listing + one file' omitted the existing integrity metadata read. Retaining the current size/MD5 verification requires **three source GETs**: (1) official HIST index once, (2) selected GCS object's JSON metadata once, (3) the selected compressed file once. Source metadata is not another market-data file. No HEAD/probe/automatic retry or range-resume request is added. A strict two-GET allowance would stop after preparation rather than silently weakening integrity or adding a request.

- Index: `https://iextrading.com/api/1.0/hist`. Require date20261102, TOPS1.6, allowlisted IEX bucket link and positive declared size.
- Metadata: derive the JSON URL from that one index entry using the existing helper; require index size = metadata size and a valid MD5. Save both responses privately with acquisition timestamps and hashes.
- **Compressed download cap:20,000,000,000 bytes (20 decimal GB)**, one attempt. Exact size is unknown until the index is read. Stop before the file GET if size exceeds the cap or metadata disagrees. Enforce the same cap while streaming; never raise it automatically.
- Existing held62 source-date entries range1,775,247,226–18,582,907,090 bytes. A previously documented2026-10-23 TOPS file is13,079,032,608 bytes. These are planning references, not an estimate asserted for November2. Source charge is0USD; compute/transfer/storage are separate resource constraints.
- Request only the snapshot's fixed504 code strings. `iex_symbol(code,'20261102')` applies dated aliases; unresolved mappings remain missing. Several codes may map to one parser symbol, and explicit None mappings must not be invented. Decoder sees the whole one-day stream once and retains only requested symbols; expanded-market extraction is not included.
- Reuse IEX regular-session last eligible round-lot trade rules; November2 session09:30–16:00 America/New_York, as-traded USD. It is neither consolidated-market OHLCV nor an official exchange close. Keep ODD_ONLY/NO_TRADE separate; no price substitution.
- Preserve the parser's integer price_e4, timestamp_ns, trade/status fields, code→symbol mapping, input snapshot SHA, parser/source-code hashes and exact schema/versions. Convert price_e4 to USD only after validating the integer. Do not attach fixed security IDs from ticker or CIK.

## Preservation and stopping

The minimal retained research input is the complete504-code quote/status result, parser output for its mapped symbols, source index/metadata and a manifest with actual file bytes, MD5 and SHA-256. Preserve privately under the existing raw handoff repository, with local0600 files and remote readback. No quote, price-derived hash or per-code raw output goes to public logs/PRs/Pages.

The large whole-market pcap is streamed; **full pcap remote archival is not part of this minimum proposal**. If full-byte retention is required, a separately approved large-file storage/chunking budget must precede execution. The private504 quote file permits deterministic calculator replay; hashes alone do not recreate a discarded pcap.

Stop without another source request on HTTP failure, missing target date/feed, bad metadata, over-cap bytes, time/resource exhaustion, gzip/MD5/size/SHA processing failure, parser failure, wrong symbol set, or invalid price/timestamp/session. Discard partial quote output from adoption, retaining only a failure manifest. No automatic retry, neighboring-date fetch, new provider, rule relaxation or workflow execution. Proposed execution limits are30 seconds to connect and1800 seconds total for the single file stream, with no retry on timeout; confirm adequate disk/memory before starting. No schedule/Secret/permission change is authorized here.

The41 missing annual filings are prioritized in the private handoff by required field and expected documentary purpose. They are not a batch acquisition request. Existing quarter instances, source tagging/unit conflicts, five-year normalization gaps and identity-policy questions are distinguished; a filing can confirm an amount without making it eligible under calc23.1.
