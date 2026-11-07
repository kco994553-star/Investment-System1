# Financial IEX input adapter /1

Codex, 2026-11-06. Based on #499 e1f1f35dd91ca64f3640624e0e51e0cf52bdf00f;
Main source contract #502 a7a6c84a06ee31a6d12ecd7da44106a486a64c11. No dependency on
discovery #503. This branch changes the research adapter and existing offline CLI
only. It imports existing session/price limits, timestamp checks, bridge and
candidate evaluator. No separate ratio engine, QGV change, collector or workflow.

## Resume command and input

Keep the existing command:

```sh
PYTHONPATH=implementation/src python implementation/tools/financial_v_connect.py \
  --manifest /private/financial-job.json --output /private/financial-result.json
```

Existing 504-code universe/shares/companyfacts/cover references remain hash-pinned.
Use a new input_vintage that includes the actual delivery; never overwrite the old
vintage or valuation_date (2026-11-02). Add `iex_handoff` instead of `prices`:

```json
{"iex_handoff": {
  "manifest": {"path":"manifest-rRUNaATTEMPT.json","sha256":"<received-file-sha256>"},
  "derived": {"path":"iex-20261102-financial11-last-trade-rRUNaATTEMPT.json","sha256":"<received-file-sha256>"},
  "requests": {"path":"price-request-11.json","sha256":"<existing-request-sha256>"},
  "basis": {"path":"reviewed-price-basis.json","sha256":"<reviewed-file-sha256>"},
  "basis_evidence": [{"path":"retained-proof.xml","sha256":"<source-sha256>"}]
}}
```

`basis` is optional: absence preserves prices as diagnostics and candidate inputs
as null. Do not manufacture it from a ticker match. Per code/primary metric the
reviewed basis must contain code, CIK, exact IEX symbol, currency, share_basis,
identity_status=DOCUMENT_LINKED, action_status=MATCHED_TO_NUMERATOR, valid_from/to
covering S, and evidence_refs (SHA-256 + locator). The CLI verifies cited files'
hashes and the existing #499 `_verify_price_sources` contract. The reviewer must
establish what the citation says; a hash alone does not prove identity/actions.
No raw financial/share data is inferred from the price file.

Main delivers the COMPLETE manifest and exact derived body/name/hash from the
approved private release `current-iex-20261102`. Codex joins existing 11-code
requests and reviewed class/action evidence. Files are not yet received.

## Integrity and time semantics

- Every supplied file uses the existing manifest reader/hash check. The adapter
  checks derived bytes against Main's recorded SHA/size, original SHA/MD5/size
  consistency, successful stream/completeness and streaming reassembly/chunk
  receipts, parser version, request indices/membership, date and session window.
- The original multi-GB file is **not re-downloaded or locally rehashed** here.
  `original_integrity=PINNED_MANIFEST_REASSEMBLY_ATTESTATION_NOT_LOCAL_RAW_REHASH`
  states the exact verification scope. This trusts the approved Main receipt.
- `last_trade_ns` and 9-digit `last_trade_utc` must agree. They are preserved.
  `received.completed_at_utc` must equal derived `acquired_at_utc`; no fallback to
  job finish, generated_at or trade time. Generation/reassembly/write times remain
  separate and are checked in order and against the new input vintage.
- Price is an exact four-decimal source string. Conversion to the existing numeric
  contract must round-trip; the original string/ns remain in trade_evidence. No
  rounding, missing→0, other-date fill, currency, class or corporate-action guess.

## Result and Main reader

Top-level #499 `financial-v-held-bridge/1.1` and 504 denominator remain unchanged.
Optional `iex_handoff` adds `financial-v-iex-adapter/1`, source/derived/manifest
hashes, three separate clocks, `prices` in `financial-v-price-input/1`, normalized
trade evidence, per-code rows and summary.

| Field | Meaning |
|---|---|
| rows[].source_state | PRICE / NO_TRADE / NOT_IN_FILE / PRICE_INVALID from Main |
| source_reason | Original source reason, retained even if additional proof gaps |
| price_present | Finite positive numeric payload exists; not an adoption claim |
| price_input_ready | Trade/date/basis/identity/currency/actions passed adapter |
| reasons | Missing/invalid input evidence; failed rows keep null prices |
| raw_ratio_value | Existing evaluator result for requested primary metric, unit x |
| candidate_primary_adopted | Existing candidate primary gate; not official QGV |
| candidate_reasons | Existing evaluator's numerator/security/period/etc. reasons |
| summary.price_available_codes | Price payload count, separately from readiness |
| summary.raw_ratio_metrics | Non-null ratios actually calculated by existing engine |
| summary.primary_adopted_codes | Actual candidate primary results, no score/rank |

Input-integrity failures reject the batch before calculation. Row-level absence,
bad trade, identity/class/action gaps preserve source rows/null/reasons. A COMPLETE
download does not establish candidate adoption. Basis references without source
files fail the job rather than inventing confirmation. Result-file permissions
and no-overwrite behavior remain the existing CLI's private boundary.

`synthetic.json` supplies a source-native handoff and normalized output, explicitly
synthetic. The tests cover actual CLI traversal and hand arithmetic EPS 4 / price
40 = 0.1; primary adoption is 1 for the asset-manager fixture, 0 for a bank whose
primary TB/P is missing. No actual price/company values are in public fixtures.

## Validation and remaining ownership

Run `python -m pytest implementation/tests/test_financial_v_iex.py`. Only the
existing CLI compatibility test directly affected by the new optional branch was
rerun; unchanged #499 calculations, NVDA diagnostics and backup searches were not.
Main adds this test to shared CI and preserves/authorizes actual delivery. Codex
reviews metric-specific evidence and runs this same CLI after delivery. No new
runtime/test dependencies, official model changes, acquisition, merge or deploy.

Current status: conversion implemented/synthetic verification; real price receipt
0, real ratios 0, real candidate adoption 0. NVDA remains conditional with missing
event original and zero newly adopted technical indicators.

Verification on this change: 27 new synthetic adapter/integration cases passed;
the directly affected existing CLI compatibility case passed (14 unchanged bridge
tests deselected). Private-boundary/direction 32 passed and direction guard 0 hits.
One independent review found three boundary defects; RED→GREEN regressions now
reject two missing/invalid symbols as identity proof, manifests written after the
input vintage, and final-session absence inferred from preclose acquisition.
No real price calculation was run and no deferred review finding remains.

## Main pure helper dependency (2026-11-07 continuation)

Codex consumer now imports `MAX_PRICE_E4`, `session_ns`, `valid_symbol` from
`providers.iex_values`, supplied unchanged by Main #508 at
`df1a9abb8c72ee57a7f7a50011bb0dbf9ffb116f`. The exact Main commit is retained
as a dependency; its provider/guard files are Main-authored, not a Codex guard
relaxation. #504 still builds on #499. Integrate #508 before the #504 consumer.
Only the offline converter import changed. The previous producer-byte/contract
verification is reused. Actual financial11 prices/manifest are still pending;
no acquisition, raw ratio calculation or adoption success is claimed.
