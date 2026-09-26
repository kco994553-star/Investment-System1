Investment-System1 · CURRENT_HANDOFF

Timestamp: 2026-09-26 (round 11)
AI: Claude Code (container) + GitHub Actions workflow c21-real-data (runs #31-#40)
Repo/branch: kco994553-star/Investment-System1 @ claude/investment-system-top500-validation-alrugm
Handoff Status: OPEN — Official US Market-Cap Top 500 PIT DECLARED for as_of 2024-12-31 (Promotion Gate v2 PASS +
gate/snapshot consistency PASS). Real single_as_of / benchmark running (run #39); walk-forward dates 2024-09-30 (run #40)
and 2024-06-30 need their own independent gate PASS. Track B (PIL) frozen at P0.

Track A — Main Track (priority)
REAL-DATA -> complete PIT pool -> Official snapshot [2024-12-31 DONE] -> real single_as_of [running] -> >=3-date walk-forward
(each date gated independently) -> real 500-company benchmark -> regression/evidence -> backend baseline freeze.

2024-12-31 evidence: reports/gate_evidence/gate_chain_2024-12-31_real_gha.json (run #38, id 36212684383, commit b143d72)
- Promotion Gate v2 PASS; base PASS; Sufficiency PASS (Russell 1000 N-PORT superset 985 members: 0 missing, 0 not rankable,
  15 rule-excluded); Completeness FAIL (not required).
- gate_snapshot_consistency PASS: official_mcap500_snapshot_from_store(gate_candidates) = gate top 500 (members, order, mcap).
- rankable 982, #500 cutoff $15.338B (TPR); #1 AAPL $3.81T; total $53.97T.
- share basis of the 500: companyfacts 439, cover class sum lower bound 44 (membership exact, rank lower bound), cover class
  sum 8, economic equivalent 5 (RKT, TKO, TPG, DKS, RYAN; H $15.19B is economic-equivalent too but below the cutoff),
  cover-text confirmed 3, cover-text single count 1 (MTD).
- price basis: close x post-as_of split factor for all 500; approved NPORT_REPORTED_VALUE exception (PINC, WOLF only, 2024-12-31
  only) is outside the top 500 and cannot enter the snapshot (valued after the as_of cut).
- Reviewed filing evidence (chain re-verifies every quote verbatim, same CIK, filed <= as_of): class_economics_2024-12-31.json
  (H, RKT, TKO, TPG, RYAN, DKS), symbol_mappings_2024-12-31.json (DKS, IBKR), nport_price_exception / nport_reported_prices.
- Validation findings fixed (previously mis-ranked): HXL x10^6 scale error (#1 at $5 quadrillion), stale/one-class companyfacts
  counts (MA, CME, IBKR, DKS, ARES, COKE, AOS, PPLI …), duplicated cover facts (CME), class-symbol naming (BF-B, AOS, COKE,
  TRIP, AA, ARES), MTD cover text. Conflict Register C-32 (snapshot default path adjclose), C-33 (companyfacts share counts).

Next: run #39 results (official_snapshot_2024-12-31.json, single_as_of 2024-12-31 -> 2025-03-31, benchmark_500);
run #40 = independent gate for 2024-09-30; then 2024-06-30; walk-forward only when all three are Official.

Track B — Personal Investment Layer v1: Architecture FROZEN; P0 Common Contracts implemented and FROZEN
(src/investment_system/personal/, tests/test_pil_p0_contracts.py 13 tests). No P1 / broker / integration. C-24, C-25,
C-28, C-29, C-30 undecided; C-33 recorded as PIL upstream note.

Tests: 272/272 (mini_pytest shim and pytest): Track A 259, Track B 13.
