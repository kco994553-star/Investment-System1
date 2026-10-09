# M1 SEC Inputs Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans task by task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Preserve and replay SEC inputs for an explicit subset of the approved US17 with conservative PIT bounds, revision lineage and verified retention receipts.

**Architecture:** A strict provider filters accession-linked facts before reusing the existing SEC converter. Immutable raw snapshots bind each receipt; only a complete verified READY receipt advances an issuer pointer. A manual SEC-only tool supports offline imports and explicit live runs.

**Tech Stack:** Python standard library, existing SEC providers/RawDatasetStore, pytest.

**Spec:** [Approved M1 design](PIPELINE_DESIGN.md#8-첫-구현-pr-제안--실행하지-않음) and the user's 2026-10-09 M1 instruction.

## Global constraints

- Companies are an explicit subset of `markets.us.US_LISTINGS`, at most 17; no universe expansion.
- No price fetching, QGV scoring, scheduled workflows, Pages publishing or secret access.
- SEC acceptance metadata is not proof of first public release. This first version supports conservative observed bounds, not exact historical publication reconstruction.
- Existing analysis/replay consumers and their contracts remain separate from the M1 input path.
- Only temporary synthetic fixtures and mocked transport are used for verification; no actual financial data collection is required to create the PR.

## Review focus

- Newly acquired data must be invisible before its acquisition bound, including on its filing date.
- Invalid/naive timestamps, mismatched issuers and unavailable accessions must not reach converter fallbacks.
- Economic periods and observed payload revisions must not be mislabelled as proven amendment parents.
- Interrupted writes, tampered blobs/receipts and failed refreshes must preserve the previous verified input.
- Batch failures must remain isolated, and offline/unauthorized company inputs must not trigger networking or publishing.

## Task 1 — strict provider

Files: `providers/sec_m1.py`, `tests/test_sec_m1_provider.py`.

- [x] Add failing tests for observation cutoffs, metadata/issuer validation, period deduplication and amendment visibility.
- [x] Implement `build_input(company_id, companyfacts, submissions, acquired_at, as_of, *, form_filter='10-K') -> dict` using the existing SEC converter after strict filtering.
- [x] Run provider tests; preserve actual source publication as unknown, acquisition as a labelled conservative bound, and unresolved amendment parents as null.

## Task 2 — retention receipts and replay

Files: `ingestion/sec_m1.py`, `tests/test_sec_m1_receipts.py`.

- [x] Add failing tests for immutable snapshots, deterministic reruns, revision lineage, tampering and interrupted publication.
- [x] Implement `retain_input`, `load_receipt`, `load_latest` and `replay_receipt` with SHA256/size verification and atomic receipt/pointer publication.
- [x] Run receipt tests; incomplete/NOT_AVAILABLE input must not replace a READY pointer.

## Task 3 — manual SEC-only entry point

Files: `tools/sec_m1_inputs.py`, `tests/test_sec_m1_tool.py`, `docs/daily_data_pipeline/M1_SEC_INPUTS.md`.

- [x] Add failing tests for company restrictions, isolated transport/schema failures and offline operation.
- [x] Implement explicit offline imports and opt-in live requests using existing SEC request/retry tooling, valid User-Agent and throttling. Return identifiers/status only.
- [x] Document custody versus first-publication proof, supported forms/recent index limits and absence of operational scheduling or publication.
- [x] Run focused tests and full pytest; obtain independent branch review.
- [ ] Confirm repository/privacy guard on the committed diff and create an unmerged M1 PR. Final gate results are recorded in the PR.

Verified locally: focused **108 passed**; full suite **969 passed, 345 subtests passed**. Independent final review: Ready, no blocking issue. Synthetic inputs and mocked transport only.
