Investment-System1 · CURRENT_HANDOFF

Timestamp: 2026-09-27 08:24 KST (round 18)
AI: Codex + Claude Code changes + GitHub Actions workflow c21-real-data (runs #54-#61)
Repo/branch: kco994553-star/Investment-System1 @ claude/investment-system-top500-validation-alrugm
Handoff Status: OPEN — C-36 is PARTIALLY RESOLVED. 2024-12-31 and 2024-09-30 each passed an independent corrected Gate,
Official artifact identity/provenance verification, single_as_of, and real 500-company benchmark; both dates are
RESTORED. 2024-06-30 independently revalidated fail-closed in run #61 and remains NOT OFFICIAL: GRAL (C-35), WRK (C-34),
ARDAGH GROUP SA delisted residual eligibility (C-38), and Liberty SiriusXM tracking-stock identity/economics (C-37)
block Sufficiency. Track B (PIL)
remains frozen at P0.
All user-facing times are KST (UTC+9).

Track A — Main Track (priority)
REAL-DATA -> complete PIT pool -> Official snapshot [12-31 RESTORED, 09-30 RESTORED, 06-30 BLOCKED] -> real
single_as_of [12-31/09-30 corrected; prior pre-C-36 results superseded] -> >=3-date
walk-forward (each date gated independently) -> real 500 benchmark -> regression/evidence -> baseline freeze.

2024-12-31 Gate (run #57, id 36229163158, evidence commit 195c5da): corrected Russell reference 991 members; 0 missing,
0 present-not-rankable, 0 non-escrow unresolved holdings, 0 CIK collisions, 0 members missing CUSIPs. Sufficiency PASS,
Promotion Gate v2 PASS, gate/internal-snapshot consistency PASS 500/500, Official blockers 0, cutoff $15.422B. OWL entered
at rank 336 on a conservative $27.633B lower bound (Class A + cited 1:1 Class C only); FNF left the prior #500 position and
ALGN is the corrected #500.

2024-12-31 Official rebuild (run #59, id 36233121639, evidence commit 1832747): input Gate universe
`uni_cf6aa3403869` was preserved as the Official universe ID. Gate and Official membership are identical 500/500 with
identical order, ranks, market caps and cutoff $15,421,829,271.493835; #500 is ALGN; FNF is absent; every member's audited
`shares_basis`, `price_basis`, `shares_available_at`, and `price_observed_at` is preserved. Corrected single_as_of:
468 selected/linked, 500 universe, 494 investable, 6 missing, 0 name errors, EW -0.01649309224255184. Corrected real
500-company benchmark: 29.956 s, peak RSS 9,478.8 MB, 0 name errors. Run #58 first exposed a random rebuilt-universe-ID
mismatch (`uni_78060185a0d6` Gate vs `uni_5eb9effc9165` Official); the pipeline now fail-closes on a missing Gate ID and
reuses that audited ID after exact membership/order verification. Pre-C-36 run #41 and run-#58 outputs remain superseded.

2024-09-30 corrected rebuild (run #60, id 36233560867, evidence commit ab72939): Russell N-PORT 994 members; 0 missing,
0 present-not-rankable, 0 non-escrow unresolved, 0 duplicate CIK membership, complete member CUSIPs. Sufficiency and
Promotion Gate v2 PASS; blockers 0. Gate ID = Official ID = `uni_e334f94a73c3`; membership 500/500, order/rank, market
caps, cutoff $15,573,548,285.00, and every audited share/price provenance field match; #500 ENPH. Corrected single_as_of
to 2024-12-31: 469 selected/linked, 495 investable, 5 missing, 0 name errors, EW 0.0004569665513276751. Corrected real
benchmark: 28.362 s, peak RSS 9,534.8 MB, 0 name errors. 2024-09-30 Official is RESTORED; runs #46/#47 remain superseded.

2024-06-30 corrected revalidation (run #61, id 36234273515, evidence commit 2e04c1b): NOT OFFICIAL. Internal candidate
consistency still passes 500/500, cutoff $14,021,530,297.505974, but corrected Russell N-PORT reference fails its own
checks: GRAL and WRK are present but not rankable; ARDAGH GROUP SA (CUSIP L0223L101) and LIBERTY SIRIUS XM
(CUSIP 531229813) are non-escrow unresolved holdings. Sufficiency and Promotion Gate v2 FAIL. No Official snapshot,
single_as_of, benchmark, or walk-forward was promoted.
- RKT/TPG/TOST: dated carry-over dropped their Aug-2024 10-Q citations; every claim re-proven from FY2023 10-Ks (filed
  Feb 2024) -> class_economics_2024-06-30.json (commit f0713ac), verified by run #51.
- GRAL (GRAIL, spun off from Illumina 2024-06-24, no periodic filing): registration/8-K documents give no unique count
  with the existing pattern; distribution_sentences diagnostic (run #50) shows the actual wording. Stays blocker unless a
  verbatim unique count filed <= 2024-06-30 exists.
- WRK (WestRock, merged into Smurfit Westrock 2024-07-05): NO permitted market-close source (Yahoo 404, Tiingo no bar,
  Stooq bot-challenge — not bypassed). nport_price_investigation_2024-06-30.json = investigation only, never applied.
  NEEDS USER DECISION (extend N-PORT exception to WRK for this date / keep blocker / another source).
- Stooq fallback wired (calibrated, fail-closed) but unusable: bot challenge.
- Liberty SiriusXM is now an actual Gate blocker. The existing company-level model cannot silently equate or aggregate
  tracking-stock economic rights. C-37 records the required user policy decision; no mapping/economic rule was invented.
- Ardagh is not a zero-value residue: the source N-PORT reports 12,001 shares and $76,686.39 (fair-value level 2).
  SEC Form 25/15 show its Class A shares left NYSE and registration/reporting ended in October 2021. Treating a positive
  delisted/private fund residue as outside a superset reference requires a new eligibility rule, so C-38 is OPEN-BLOCKING.
  The resolver now preserves original valuation/identity fields on unresolved rows; Gate behavior remains fail-closed.

Track B — Personal Investment Layer v1: Architecture FROZEN; P0 Common Contracts implemented and FROZEN
(src/investment_system/personal/, 10 package files, 13 tests). P1+ NOT STARTED; no live broker/integration. Track B code
has no Track A imports and Track A has no reverse runtime imports into personal/. C-24, C-25, C-28, C-29, C-30, C-33
remain explicit upstream/contract items; none was resolved by inference. All Official tracks remain Pre-Tax.

Track C — Experiment & Validation Layer: `EVL_SPEC_v0.1` is registered as
`Investment-System1 · Experiment & Validation Layer Specification v0.1.md`. Status is DESIGN FROZEN /
IMPLEMENTATION NOT STARTED. Track C owns PIT experiments, validation, and Official Aggressive/Balanced/Defensive profile
promotion; Track B is a consumer. Core scores, Official/Custom isolation, Trial Ledger completeness, Final Holdout
isolation, invalidation propagation, tax exclusion, and fail-closed uncertainty are locked. C0 implementation must not
start until Track A REAL-DATA baseline Freeze; current Track A is not frozen because 2024-06-30 is NOT OFFICIAL.

Tests re-run 2026-09-27 KST: full 295/295 and Track B 13/13 PASS (mini_pytest shim). Targeted N-PORT/gate regressions
previously 103/103; prior targeted Official identity regressions 102/102. Track C has no code/tests by design.
py_compile and diff check PASS for the round-17 code patch.
