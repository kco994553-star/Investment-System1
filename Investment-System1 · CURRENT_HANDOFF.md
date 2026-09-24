Investment-System1 · CURRENT_HANDOFF

Timestamp: 2026-09-25 (round 4)
AI: Claude Code (claude.ai/code cloud container, real terminal)
SSoT lineage: ...2026-09-25_claude_r3.zip -> Investment-System1_Handoff_2026-09-25_claude_code_r4.zip (this package)
Repo: kco994553-star/Investment-System1, branch claude/investment-system-top500-validation-alrugm (this package is also committed there)
Handoff Status: OPEN — C-21 still BLOCKED, now verified in a second, independent environment (egress-policy 403 on SEC + Yahoo). Runner/gate chain hardened so the next network-enabled session is a two-command run. No gate passed. Nothing fabricated.

Started From
r3 CURRENT_HANDOFF: C-21 sole blocker (no network in Claude Chat sandbox + RawDatasetStore blobs lost from ZIP). 257/282 missing large-caps CIK-ready, 25 pending. 173/173.

This round (read first)
1. Baseline: 173/173 reproduced from the r3 ZIP with tools/mini_pytest.py before any change.
2. Network, tested directly in this environment's real terminal (curl + urllib through the session proxy):
   www.sec.gov, data.sec.gov (companyfacts, submissions), query1/query2.finance.yahoo.com, efts.sec.gov -> CONNECT 403 "connect_rejected (organization policy)".
   pypi.org -> 200 (allowed). So this is the environment's network policy, not a code defect and not the old Claude Chat result reused.
   Per the proxy rules, 403 policy denials were not retried or routed around.
   Evidence: implementation/reports/network_probe_2026-09-25_claude_code_r4.json, implementation/data/raw/ingest_run_1790289959.json
   (fetch_real_data.py --plan: 793 artifacts, 3 real requests (one per host), 793 EGRESS_BLOCKED, 0 written).
3. Fix for the user (not something the agent can do): in the cloud environment settings -> Network access, allow
   www.sec.gov, data.sec.gov, query1.finance.yahoo.com (or a broader access level). Alternative without network:
   upload SEC companyfacts.zip (+ Stooq d_us_txt.zip) and run tools/import_bulk_real_data.py (already built, offline).
4. Minimal additive code changes (no redesign, existing behaviour/tests unchanged):
   - tools/fetch_real_data.py: retry + exponential backoff (2/4/8/16s, Retry-After honoured) for HTTP 429/5xx and transient
     network errors; no retry for other 4xx; egress-policy denial -> per-host circuit breaker (EGRESS_BLOCKED, no further
     requests to that host); --plan <priority plan JSON> (CIK-ready names + ticker->CIK via stored sec_tickers for the rest,
     UNRESOLVED reported, never invented; Yahoo symbol BRK.B -> BRK-B); every run writes <store>/STORE_INDEX.json.
     Resume unchanged: store.has() -> SKIPPED_ALREADY_PRESENT, no re-download.
   - tools/audit_mcap_store.py: evaluate_reference_coverage normalizes share-class tickers (BRK.B == BRK-B) and reads the
     price by the listing's Yahoo symbol; new ranked_top500() (#500 cutoff, same rules as audit()); Sufficiency Gate honours
     reference_role == "MISSING_LARGE_CAP_DETECTOR" (such a reference can FAIL the gate but can never make it PASS ->
     reason ONLY_DETECTOR_REFERENCES_PASSED). Legacy behaviour without the role is unchanged.
   - tools/run_top500_gate_chain.py (new, offline): listings(+plan names) -> audit/rankable -> ranked_top500/#500 cutoff ->
     evaluate_reference_coverage (S&P 500 forced to detector role) -> Universe Completeness -> Top-500 Sufficiency ->
     Promotion Gate v2. Declares Official only if v2 passes; walk-forward/benchmark reported NOT_RUN otherwise.
   - tests/test_c21_runner_and_gate_chain.py: 9 tests (retry, no-retry 404, egress breaker, plan resolution + resume,
     BRK.B/BRK-B, detector-only cannot pass, ranked_top500 == audit cutoff, chain fail-closed empty store, chain with full
     detector coverage still not Official).
5. Real finding: BRK.B was counted as "missing from pool" only because the reference uses BRK.B and the pool uses BRK-B.
   True S&P-2024-12-31 members missing from the 598 pool = 281 (256 CIK-ready + 25 needing CIK), not 282.
6. Store reality check: data/raw has 0 blobs (C-21). The 221 "present" names' blobs are also gone, so the next run must fetch
   the prior 598-listing pool too, not only the 282. Full resume plan: reports/gate_evidence/c21_resume_plan_2024-12-31.json
   (854 listings, 579 companyfacts CIKs, 854 price artifacts missing).

Tests: 182/182 (mini_pytest shim) and 182/182 (real pytest 8.x). reports/mini_pytest_2026-09-25_claude_code_r4.txt, reports/pytest_2026-09-25_claude_code_r4.txt

Status snapshot
- Raw artifacts in persistent RawDatasetStore (implementation/data/raw): 0 blobs, 0 manifests; 10 ingest-run logs; STORE_INDEX.json (n_artifacts 0)
- Reference coverage (S&P 500 reconstructed 2024-12-31, 503 members), identity vs 598 pool: 222 present / 281 missing (was reported 221/282; BRK.B fix)
- Missing large caps: 281 (256 CIK-ready, 25 need CIK: ANSS BWA CAG CPB DAY EMN ENPH EPAM FMC HES HOLX IPG JNPR K KMX LKQ LW MHK MKTX MOH MTCH PAYC POOL TFX WBA)
- rankable: last real computation 297 (r2 audit, blobs since lost); on the current real store the chain computes 0 (reports/gate_evidence/gate_chain_2024-12-31_claude_code_r4.json)
- #500 cutoff: not computable
- Universe Completeness Gate: FAIL (COMPANYFACTS_COVERAGE_BELOW_BENCHMARK_LOW_ESTIMATE)
- Top-500 Sufficiency Gate: FAIL (FEWER_THAN_500_RANKABLE, NO_CUTOFF_MCAP_COMPUTED, NO_REFERENCE_PASSED_ITS_OWN_CHECKS). S&P 500 is detector-only.
- Promotion Gate v2: FAIL (no eligibility evidence; <500 rankable; neither completeness nor sufficiency)
- Official US Market-Cap Top 500 PIT: NOT declared
- REAL-DATA VERIFIED: NO
- Walk-forward (>=3 dates, real): NOT RUN (gate v2 failed)
- 500-company real benchmark: NOT RUN (gate v2 failed)

Validation ladder: Code Present YES · Reproducible YES · SYNTHETIC VERIFIED YES (182, real pytest too) · REAL-DATA VERIFIED NO · Full PIT NO · OOS NO · Calibration NO · Forward NO.

Unchanged by rule
C-18 RESOLVED (Official Default Universe = US Market-Cap Top 500 PIT). V Initial Prior 25/20/15/15/10/10/5, no refit. rankable>=500 alone never promotes. S&P 500 = missing-large-cap detector only (now enforced in code). No fabricated data.

Raw data persistence policy
- Persistent store = implementation/data/raw in the git branch above (RawDatasetStore: blobs/, manifests/, history/).
- Always keep in git + ZIP: manifests/, STORE_INDEX.json (url + sha256 + bytes per artifact), ingest_run_*.json, resume plans.
- Blobs: keep in git/ZIP while total size is modest; if the store grows past ~500 MB (SEC companyfacts for ~800 names is
  likely 1-3 GB), ship manifests + STORE_INDEX only and keep blobs in external storage; STORE_INDEX makes every blob
  re-fetchable and sha256-verifiable. Never let the ZIP silently drop manifests again (that was the original C-21 loss).

Next Action (network-enabled session; run from implementation/)
0. Set a real SEC contact: export INVESTMENT_SYSTEM_SEC_UA="<name> <contact email>"
1. python tools/fetch_real_data.py --store data/raw --plan reports/gate_evidence/missing_large_cap_priority_plan_2024-12-31.json
   (sec_tickers first, 255 unique CIKs companyfacts+submissions, 282 Yahoo charts; the 25 CIK-less names resolve from sec_tickers;
   re-run the same command to resume — present artifacts are skipped; names delisted in 2025-26 that stay UNRESOLVED need
   a dated resolver pass via universe.resolve / submissions, never a guess.)
2. python tools/fetch_real_data.py --store data/raw --skip-tickers --ciks <c21_resume_plan.ciks> --symbols <c21_resume_plan.symbols>
   (re-ingests the lost 598-pool blobs; resumable).
3. python tools/run_top500_gate_chain.py --store data/raw --as-of 2024-12-31 --out reports/gate_evidence/gate_chain_2024-12-31_real.json
   (+ --eligibility-evidence <dated eligibility attestation> when one exists; + --sufficiency-reference for an independent
   dated PIT large-cap ranking reference if obtained — S&P alone cannot pass).
4. Only if promotion_gate_v2.passed: official_mcap500_snapshot_from_store -> run_walk_forward_from_store (>=3 real dates)
   -> tools/bench_universe_500.py on the real 500.
5. C-23 per-name verification (advisory) in parallel once real submissions exist.

Do Not Repeat
- Everything in prior rounds' Do Not Repeat.
- In this claude.ai/code environment: do not retry SEC/Yahoo while the Network access setting is unchanged; the proxy
  denial is policy (verified 2026-09-25). Check once with fetch_real_data.py (the breaker sends one request per host) and stop.
- Do not re-count BRK.B as missing.
