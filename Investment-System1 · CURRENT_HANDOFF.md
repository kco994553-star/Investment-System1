Investment-System1 · CURRENT_HANDOFF

Timestamp: 2026-09-25 (round 8)
AI: Claude Code (claude.ai/code container; network work on GitHub Actions workflow c21-real-data)
Repo/branch: kco994553-star/Investment-System1 @ claude/investment-system-top500-validation-alrugm (pushed)
Handoff Status: OPEN — real-data PIT market-cap ranking is now data-quality clean except one lower-bound issuer (PSKY);
Promotion Gate v2 FAILS on structural evidence (eligibility attestation, completeness, independent sufficiency reference).
Official US Market-Cap Top 500 PIT NOT declared. REAL-DATA VERIFIED: NO. C-18 RESOLVED (unchanged).

Latest evidence: implementation/reports/gate_evidence/gate_chain_2024-12-31_real_gha.json (run #18, id 36130095307, commit dfd94b3)
Raw store: GitHub Actions cache c21-raw-store-v2-* (+ artifact c21-raw-store-<run_id>, 90 days); git holds manifests + STORE_INDEX
(3,256 artifacts: companyfacts 606, submissions 606, submissions pages 251, XBRL instances 64, Yahoo charts 864, split events 864).
SEC_USER_AGENT: repository secret only (masked in logs).

Current numbers (as_of 2024-12-31)
- eligible issuers 530 (604 -> company-level; 73 foreign private issuers at as_of excluded; HONA not registered at as_of)
- rankable 516 · #500 cutoff $8.223B
- class-sum overrides 30 (6 exact, 24 lower bound; lower bound = unlisted class not priced, never guessed)
- unrankable 14: 13 NO_AS_OF_PRICE (ANSS DAY HES HOLX IPG JNPR K WBA DFS CTRA = Yahoo 404 after delisting;
  AVB EA EQR = Yahoo returns a truncated ~1.3 KB chart, identical on refresh) + SNDK (not listed at as_of; UNKNOWN, kept)
- top-500 quality flags 0; official blockers: PROMOTION_GATE_V2_FAILED, LOWER_BOUND_ISSUERS_OUTSIDE_TOP500 (PSKY: Paramount
  Global class B = PARA, delisted, no price -> lower bound $1.1B; true value near the cutoff cannot be proven)
- Universe Completeness FAIL (530 / WFE low 3,400 = 15.6%)
- Top-500 Sufficiency FAIL (only reference = S&P detector: 13 members not rankable, 13 ranked outside computed top 500;
  detector can never pass alone)
- Promotion Gate v2 FAIL (no dated eligibility attestation; eligible not all rankable; neither completeness nor sufficiency)

Decisions needed from the user (policy / data source) — see the round-8 report
1. Price source for 14 names without an as-of Yahoo price (delisted/renamed + 3 truncated).
2. Universe completeness path: full SEC-registrant ingest needs a PIT exchange-listing source for 2024-12-31
   (current listing files would apply today's status backward -> not allowed).
3. Eligibility attestation / independent PIT top-N reference for the base gate and Sufficiency.

Next action once decided: add the chosen source as a fetch step, re-run the workflow once, then only if
Promotion Gate v2 passes: official_mcap500_snapshot_from_store -> >=3 as_of walk-forward -> 500-company benchmark.
