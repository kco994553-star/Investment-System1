Investment-System1 · CURRENT_HANDOFF

Timestamp: 2026-09-26 15:40 KST (round 12)
AI: Claude Code (container) + GitHub Actions workflow c21-real-data (runs #41-#51)
Repo/branch: kco994553-star/Investment-System1 @ claude/investment-system-top500-validation-alrugm
Handoff Status: OPEN — Official US Market-Cap Top 500 PIT DECLARED for 2024-12-31 and 2024-09-30 (each: Promotion Gate v2
PASS + gate/snapshot consistency PASS). 2024-06-30 gate FAIL (GRAL share count, WRK price) -> >=3-date walk-forward blocked.
Track B (PIL) frozen at P0. All user-facing times are KST (UTC+9).

Track A — Main Track (priority)
REAL-DATA -> complete PIT pool -> Official snapshot [12-31 DONE, 09-30 DONE, 06-30 OPEN] -> real single_as_of [12-31, 09-30
DONE] -> >=3-date walk-forward (each date gated independently) -> real 500 benchmark -> regression/evidence -> baseline freeze.

2024-12-31 (run #38 gate, run #41 pipeline): PGV2 PASS, consistency 500/500, cutoff $15.338B; single_as_of to 2025-03-31:
468 selected/linked, EW -1.56 %; benchmark 26.25 s, peak RSS 9.5 GB, 0 errors.

2024-09-30 (run #46 gate, run #47 pipeline): PGV2 PASS (Russell 1000 N-PORT 988 members: 0 missing, 0 not rankable),
consistency 500/500 (order + mcap identical), cutoff $15.548B. AMTM (spin-off 2024-09-27) from its 8-K filed 2024-09-27
(153,280,369 shares, REGISTRATION_DOC_SHARE_COUNT); RPRX economic equivalent $16.74B (10-K 'one -for-one' extraction
whitespace tolerated, wording unchanged); PINC/WOLF N-PORT exception for this date (look_ahead recorded). single_as_of to
2024-12-31: 469 selected/linked, EW -0.0094 %; benchmark 25.06 s, 9.5 GB. walk_forward_status BLOCKED_FEWER_THAN_3_DATES.

2024-06-30 (runs #48-#51): consistency PASS 500/500; PGV2 FAIL. Cutoff $13.78B.
- RKT/TPG/TOST: dated carry-over dropped their Aug-2024 10-Q citations; every claim re-proven from FY2023 10-Ks (filed
  Feb 2024) -> class_economics_2024-06-30.json (commit f0713ac), verified by run #51.
- GRAL (GRAIL, spun off from Illumina 2024-06-24, no periodic filing): registration/8-K documents give no unique count
  with the existing pattern; distribution_sentences diagnostic (run #50) shows the actual wording. Stays blocker unless a
  verbatim unique count filed <= 2024-06-30 exists.
- WRK (WestRock, merged into Smurfit Westrock 2024-07-05): NO permitted market-close source (Yahoo 404, Tiingo no bar,
  Stooq bot-challenge — not bypassed). nport_price_investigation_2024-06-30.json = investigation only, never applied.
  NEEDS USER DECISION (extend N-PORT exception to WRK for this date / keep blocker / another source).
- Stooq fallback wired (calibrated, fail-closed) but unusable: bot challenge.

Track B — Personal Investment Layer v1: Architecture FROZEN; P0 Common Contracts implemented and FROZEN
(src/investment_system/personal/, 13 tests). No P1 / broker / integration. C-24, C-25, C-28, C-29, C-30 undecided.

Tests: 287/287 (Track A 274, Track B 13).
