Investment-System1 · CURRENT_HANDOFF

Timestamp: 2026-09-25 (round 6)
AI: Claude Code (claude.ai/code cloud container, real terminal)
SSoT lineage: ...claude_code_r4.zip -> ...gpt_r5.zip -> Investment-System1_Handoff_2026-09-25_claude_code_r6.zip (this package)
Handoff Status: OPEN — C-21 BLOCKED (no complete SEC bulk archive, no price archive, SEC/Yahoo/Stooq egress still denied here). Bulk import path is now fail-closed on archive integrity, so the next complete archive can be imported safely in one step. No gate passed. Nothing fabricated.

Started From
gpt_r5 CURRENT_HANDOFF: 182/182. User-supplied companyfacts.zip (948,238,703 bytes, sha256 01ba5438...) is truncated: 9,577 complete local entries, CIK0001436425.json cut 20,941 bytes short, no EOCD/central directory. Not ingested. C-18 RESOLVED (US Market-Cap Top 500 PIT).

This round
1. Baseline: gpt_r5 ZIP extracted, 182/182 reproduced (mini_pytest) before any change.
2. Egress re-probed from the real terminal: www.sec.gov, data.sec.gov, query1.finance.yahoo.com, stooq, nasdaqtrader, huggingface -> CONNECT 403.
   raw.githubusercontent.com and pypi are reachable but were NOT used as data sources (third-party mirrors are not official
   provenance and would route around the sec.gov policy block). Evidence: implementation/reports/network_probe_2026-09-25_claude_code_r6.json
3. Google Drive (connected here) searched: only the same truncated companyfacts.zip + its 10 parts. No new/complete archive, no price archive.
   The r5 truncation finding was not re-litigated (the 948 MB object cannot be streamed into this container via the connector).
4. Minimal code changes (additive, fail-closed):
   - tools/import_bulk_real_data.py: verify_archive() runs BEFORE any store write: sha256, PK local-header signature,
     zipfile open (EOCD/central directory present), full testzip() CRC, expected-member count, optional --sec-sha256/--stooq-sha256.
     Any failure -> exit 2, nothing written (previously a CRC error mid-archive would crash after partial writes).
     --verify-only and --report-out added. Archive sha256 recorded in every imported artifact's manifest notes. STORE_INDEX.json
     rewritten after import.
   - Test hygiene bug fixed: running the suite rewrote committed evidence (reports/track_store.json grew by ~860 lines and
     reports/us_session_track_record.json was overwritten on every run -- the r4->r5 diffs in those files were test side effects,
     not evidence). us_live/book/e2e default report paths now honour INVESTMENT_SYSTEM_REPORTS_DIR; tests/__init__.py points it
     at a temp dir. Production default (implementation/reports) unchanged. Both files restored to the r5 bytes.
   - tests/test_bulk_archive_integrity.py: 4 tests (valid import + provenance, r5-style truncation rejected with store untouched,
     CRC corruption rejected, sha mismatch / verify-only writes nothing).
5. Found: tools/import_bulk_real_data.py --stooq-us defaults to --chart-range max, but run_top500_gate_chain.py/audit read 5y.
   Pass --chart-range 5y at import (or run the chain with --chart-range max) or imported prices are invisible to the gates.
   Default left unchanged (documented) to avoid silently changing artifact ids.
6. Gate chain re-run on the real store: reports/gate_evidence/gate_chain_2024-12-31_claude_code_r6.json (unchanged result).

Tests: 186/186 (mini_pytest shim) and 186/186 (real pytest). reports/mini_pytest_2026-09-25_claude_code_r6.txt, reports/pytest_2026-09-25_claude_code_r6.txt.
Suite run no longer modifies any tracked file.

Status snapshot
- Raw artifacts in RawDatasetStore (implementation/data/raw): 0 blobs / 0 manifests; STORE_INDEX n_artifacts 0
- Reference coverage (S&P 500 reconstructed 2024-12-31, 503): 222 present in pool by identity / 281 missing (256 CIK-ready, 25 need CIK)
- rankable on real store: 0 (last historical real computation 297, blobs lost) · #500 cutoff: not computable
- Universe Completeness Gate: FAIL · Top-500 Sufficiency Gate: FAIL (S&P = detector only) · Promotion Gate v2: FAIL
- Official US Market-Cap Top 500 PIT: NOT declared · REAL-DATA VERIFIED: NO
- Walk-forward (>=3 real dates): NOT RUN · 500-company real benchmark: NOT RUN
Validation ladder: Code Present YES · Reproducible YES · SYNTHETIC VERIFIED YES (186) · REAL-DATA VERIFIED NO · Full PIT NO · OOS NO · Calibration NO · Forward NO.

What the user needs to provide (either path unblocks C-21)
A. Network: environment settings -> Network access -> allow www.sec.gov, data.sec.gov, query1.finance.yahoo.com. Then the r4 two-command
   fetch path (fetch_real_data.py --plan ..., then --ciks/--symbols from c21_resume_plan) + run_top500_gate_chain.py.
B. Files: a COMPLETE https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip (current full archive is well above
   948 MB; the Drive copy stopped mid-file, typical of an interrupted browser download -- check the download finished and that the
   archive opens/tests locally before uploading), PLUS a daily price archive (e.g. Stooq d_us_txt.zip). Companyfacts alone
   cannot pass any gate: rankable needs prices.

Next Action
1. python tools/import_bulk_real_data.py --sec-companyfacts <path> [--stooq-us <path> --chart-range 5y] --verify-only --report-out reports/gate_evidence/bulk_integrity_<date>.json
2. If passed: same command without --verify-only (resume: present ids are skipped).
3. python tools/run_top500_gate_chain.py --store data/raw --as-of 2024-12-31 --out reports/gate_evidence/gate_chain_2024-12-31_real.json
4. Only if promotion_gate_v2.passed: official_mcap500_snapshot_from_store -> run_walk_forward_from_store (>=3 real dates) -> tools/bench_universe_500.py on the real 500.
5. Persistence: keep manifests/STORE_INDEX/ingest logs in git + ZIP; a full companyfacts import is multi-GB -> keep blobs outside the ZIP, ship STORE_INDEX (url+sha256) and the archive sha256.

Open Issues
- C-21 BLOCKED (above). C-17 filing vintage/restatement unresolved. C-23 advisory pending real submissions.
- GitHub push from this environment is refused (Claude GitHub App access for kco994553-star/Investment-System1); commits are local only and fully contained in this ZIP.

Do Not Repeat
- Everything in prior Do Not Repeat lists (r4, gpt_r5).
- Do not import any archive that fails verify_archive; do not salvage the 9,577 truncated-archive entries as a complete universe.
- Do not use third-party GitHub/HF mirrors of SEC or price data as REAL-DATA provenance without an explicit user decision.
- Do not re-probe SEC/Yahoo in this environment until the Network access setting is changed.
