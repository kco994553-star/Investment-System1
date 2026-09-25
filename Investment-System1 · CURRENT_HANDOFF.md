Investment-System1 · CURRENT_HANDOFF

Timestamp: 2026-09-25 (round 9)
AI: Claude Code (container) + GitHub Actions workflow c21-real-data (runs #19-#24)
Repo/branch: kco994553-star/Investment-System1 @ claude/investment-system-top500-validation-alrugm
Handoff Status: OPEN — Sufficiency path implemented with an independent SEC-sourced PIT reference; Promotion Gate v2 FAILS on
two policy/data-source questions (prices for delisted issuers; lower-bound multi-class issuers). Official US Market-Cap Top 500 PIT
NOT declared. REAL-DATA VERIFIED: NO. C-18 RESOLVED.

Latest evidence: reports/gate_evidence/gate_chain_2024-12-31_real_gha.json (run #24, id 36137865942, commit cafab7f)
Reference: reports/gate_evidence/russell1000_nport_2024-12-31.json (SEC NPORT-P 0001752724-25-034052, iShares Russell 1000 ETF,
report date 2024-12-31, filed 2025-02-24; 1,007 common-equity holdings -> 971 CIKs; 20 unresolved names listed)
Raw store: Actions cache c21-raw-store-v2-* + artifacts (90 days); git: manifests + STORE_INDEX (5,141 artifacts, 4.31 GB)

Numbers (as_of 2024-12-31)
- eligible 952 (1,039 company-level -> 82 foreign private issuers at as_of, 4 not registered, 1 not trading excluded)
- rankable 935 · #500 cutoff $14.408B
- unrankable 17: 14 NO_AS_OF_PRICE (delisted after as_of / truncated Yahoo), XYZ shares missing, OZK no companyfacts, PPLI non-positive
- lower-bound multi-class issuers outside the top 500: 28 (unlisted classes; membership undetermined)
- Completeness FAIL (952/3,400 = 28.0%) · Sufficiency FAIL (Russell superset: 20 missing, 40 not rankable, 14 rule-excluded)
- Promotion Gate v2 FAIL · Official blockers: PROMOTION_GATE_V2_FAILED, LOWER_BOUND_ISSUERS_OUTSIDE_TOP500

Data sources tried and rejected (fail-closed, evidence in data/raw/*_run_*.json)
- Stooq per-ticker CSV: JavaScript proof-of-work bot check on every request (never bypassed); calibration UNAVAILABLE; nothing written.
- iShares IWB holdings CSV (asOfDate): HTML page returned; rejected.

Decisions needed (user)
1. Price source for delisted/renamed issuers (the 14 unrankable + members whose names resolve only to delisted entities).
2. Lower-bound rule for unlisted share classes (keep fail-closed, or accept an equal-economics upper bound).

Next action after decisions: implement the chosen rule/source, one workflow run, and only if Promotion Gate v2 passes:
official_mcap500_snapshot_from_store -> >=3 as_of walk-forward -> 500-company benchmark.
