Investment-System1 · CURRENT_HANDOFF

Timestamp: 2026-09-27 16:02 KST (round 20)
AI: Codex + Claude Code changes + GitHub Actions workflow c21-real-data (runs #54-#66)
Repo/branch: kco994553-star/Investment-System1 @ claude/investment-system-top500-validation-alrugm
Handoff Status: OPEN — C-39 is RESOLVED. C-36 is PARTIALLY RESOLVED. 2024-12-31 and 2024-09-30 each passed an independent corrected Gate,
Official artifact identity/provenance verification, single_as_of, and real 500-company benchmark; both dates are
RESTORED. D3-P policies removed the WRK, Ardagh, and Liberty blockers in run #66, but 2024-06-30 remains NOT OFFICIAL
because the cited GRAL 10-K was not its first subsequent periodic report. The local correction now cites the actual
first subsequent 10-Q and passes tests, but has not yet been uploaded or re-run. Track B (PIL) remains frozen at P0.
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

2024-06-30 D3-P application (run #66, id 36300544234, evidence commit f2a66f8 at 2026-09-27 15:47:10 KST): NOT
OFFICIAL. Internal snapshot consistency passes 500/500; 991 issuers are rankable and cutoff remains
$14,021,530,297.505974. General, result-independent policies were applied without cutoff input:
- CA-PRICE-01 reconstructs WRK at $50.26 from three calibrated Level-1 N-PORT sponsors (two independent), with PIT
  shares 258,148,056 and market cap $12,974,521,294.56. WRK is rankable outside the Top 500.
- CA-ELIGIBILITY-01 excludes Ardagh from sufficiency only after exact-security Form 25/Form 15 evidence, while preserving
  the positive $76,686.39 residual source row in audit evidence. CA-SECURITY-01 forbids cross-tracking-group equivalence;
  Liberty no longer remains unresolved under the exact-CUSIP issuer evidence path.
- CA-SHARES-01 failed closed for GRAL because policy evidence cited its 2025-03-05 10-K, while SEC submissions identify
  a 2024-11-13 10-Q as the first subsequent periodic report. GRAL alone remains present-not-rankable, so the Russell
  reference fails its own check and Promotion Gate v2 fails. No downstream result was promoted.
- Local commit `10f4acc` corrects the citation to accession `0001628280-24-047606`, whose 10-Q states that the June 24
  spin-off resulted in issuance of exactly 31,049,148 shares. It passed the targeted and full regressions but still
  requires remote upload and a fresh real-data workflow before any Official claim.

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

Tests re-run 2026-09-27 16:02 KST: full 308/308 PASS (mini_pytest shim); C-39 focused 6/6 PASS. Track B's 13-test
frozen baseline remains unchanged. Targeted N-PORT/gate regressions 109/109 and prior targeted Official identity
regressions 102/102 passed. Track C has no code/tests by design. py_compile and diff check PASS.

RIG / News — `RIG_NEWS_ARCH_v0.1` is registered as
`Investment-System1 · RIG News Architecture v0.1.md`. Status is DESIGN FROZEN / IMPLEMENTATION NOT STARTED; P0–P5
are NOT_STARTED. Repository audit confirmed that existing DataEvent NEWS handling is evidence-only, future-available
events are deferred, Frontend IA uses Summary→Evidence→Detail, and the Global/Korea contract already defines shared
NewsItem→Claim→Event and Feed/Network identity. No RIG code, store, UI, notification runtime, score, or test was added.
`yahoo_events__*` is split-event market-data provenance, not news. C-39 is now RESOLVED: the common Global/Korea
`IssuerIdentity -> SecurityIdentity -> ListingIdentity`, independent Analysis/Network/News contexts, and fail-closed
FX/eligibility PIT contracts are implemented in `contracts/global_universe.py` with six regressions. Track B's frozen
private identity implementation was not imported or changed. RIG remains DESIGN FROZEN / IMPLEMENTATION NOT STARTED.

Repository baseline: remote `f2a66f8` contains run #66 evidence. The local branch was safely rebased onto that head;
the duplicate local D3-P patch was dropped because its tree was already upstream. The GRAL 10-Q correction is the one
preserved local commit above remote; the C-39 implementation/documentation is the current uncommitted worktree change.
