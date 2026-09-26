Investment-System1 · CURRENT_HANDOFF

Timestamp: 2026-09-26 (round 10)
AI: Claude Code (container) + GitHub Actions workflow c21-real-data (runs #25-#30)
Repo/branch: kco994553-star/Investment-System1 @ claude/investment-system-top500-validation-alrugm
Handoff Status: OPEN — Main Track (REAL-DATA) blocked by 3 data-source gaps (PINC, WOLF, PPLI); Promotion Gate v2 FAILS.
Official US Market-Cap Top 500 PIT NOT declared. REAL-DATA VERIFIED: NO. C-21 RESOLVED (store persisted in Actions).
Additive context: Personal Investment Layer v1 = Architecture FROZEN (100%), Implementation NOT STARTED, below Main Track.

Main Track (unchanged priority)
REAL-DATA -> complete PIT candidate pool -> official_mcap500_snapshot_from_store -> real single_as_of -> >=3-date
walk-forward -> actual 500-company network benchmark -> Promotion/validation.
Current step: complete PIT candidate pool / Promotion Gate v2 (not passed).

Latest evidence: reports/gate_evidence/gate_chain_2024-12-31_real_gha.json (run #30, id 36206384858, commit 316ada7)
Reference: reports/gate_evidence/russell1000_nport_2024-12-31.json (SEC NPORT-P 0001752724-25-034052, report date
2024-12-31, filed 2025-02-24; 985 member CIKs, 6 holdings unresolved and not counted as members)
Raw store: Actions cache c21-raw-store-v2-* + run artifacts (90 days); git: manifests + STORE_INDEX

Numbers (as_of 2024-12-31, run #30)
- rankable 979 · #500 cutoff $15.189B (H at #500)
- Russell superset: missing from pool 0; present but not rankable 2 (PINC, WOLF); rule-excluded 15
- S&P detector: 0 not rankable
- unrankable 3: PINC, WOLF (no price on/before as_of in Yahoo or Tiingo; Tiingo search returns only other "Premier"
  companies / "Wolfspeed Inc (New)"), PPLI (cover XBRL shares 0, no priced class)
- multi-class: H, RKT, TKO, TPG resolved from filings <= as_of (class_economics_2024-12-31.json, chain-verified quotes):
  H $15.19B, RKT $22.00B, TKO $24.48B, TPG $23.14B
- Completeness FAIL · Sufficiency FAIL (REFERENCE_MEMBERS_PRESENT_BUT_NOT_RANKABLE) · Promotion Gate v2 FAIL

Decisions needed (user, policy)
1. PINC/WOLF price: licensed delisted-price source, or the iShares N-PORT 2024-12-31 per-share value (filed after as_of,
   one trading day different from the 12-30 close basis) recorded as a separate price basis.
2. PPLI: allow checking later SEC filings for the correct share count (post-as_of information).

Next action after decisions: implement, one workflow run; only if Promotion Gate v2 passes:
official_mcap500_snapshot_from_store -> real single_as_of -> >=3 as_of walk-forward -> 500-company benchmark.

Personal Investment Layer v1 (additive; see `Investment-System1 · PERSONAL_INVESTMENT_LAYER_V1_HANDOFF.md`)
- Architecture FROZEN; Implementation NOT STARTED (P0..P6 plan READY; not started because it must not displace the Main Track).
- Intake conflicts registered: C-24 StrategyProfile name/contract, C-25 security_id vs company_id, C-26 Model/Actual in one
  Holding, C-27 Integration gap/order intents vs Portfolio Gap, C-28 Technical output lacks available_at (verified not
  implemented), C-29 no authoritative QGV↔Technical scale contract, C-30 Official weight maturity unresolved, C-31 code.md
  absent.
- Open upstream (not solved in PIL): Technical available_at propagation (C-28), score-scale contract (C-29), Official weight
  dataset (C-30).

Tests: 242/242 (tools/mini_pytest.py) and 242/242 (pytest).
