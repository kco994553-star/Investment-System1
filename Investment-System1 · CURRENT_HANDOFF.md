Investment-System1 · CURRENT_HANDOFF

Timestamp: 2026-09-25 (round 7)
AI: Claude Code (claude.ai/code cloud container; real network work executed on a GitHub Actions runner)
SSoT lineage: ...gpt_r5.zip -> ...claude_code_r6.zip -> Investment-System1_Handoff_2026-09-25_claude_code_r7.zip (this package)
Repo: kco994553-star/Investment-System1, branch claude/investment-system-top500-validation-alrugm (pushed; GitHub push works again)
Handoff Status: OPEN — C-21 data acquisition RESOLVED (real SEC + Yahoo raw data ingested). Official Top-500 NOT declared: Promotion Gate v2 FAIL and unresolved market-cap quality blockers (foreign ADR ratios, 5 rows without split history, 13 multi-class issuers without shares). Nothing fabricated.

How real data was obtained (read first)
- The Claude cloud container still has SEC/Yahoo egress denied (CONNECT 403, org policy; not routed around).
- GitHub push access started working this round, and the repo's GitHub-hosted runners have normal egress. With the user's explicit
  approval, .github/workflows/c21-real-data.yml (workflow_dispatch only) runs the EXISTING tools unchanged:
  offline tests -> fetch_real_data.py --plan (priority plan) -> fetch_real_data.py --with-split-events (resume plan) ->
  fetch delisted-CIK candidates -> run_top500_gate_chain.py -> upload artifact -> commit manifests/STORE_INDEX/gate evidence back.
- SEC User-Agent: dispatch input sec_user_agent (the user chose this and accepted that it is visible in public run metadata);
  a repository secret SEC_USER_AGENT takes precedence if set. SEC ~6.7 req/s max (0.15 s throttle), retry/backoff, resume.
- Runs: #1 fail-fast (no UA, 0 requests) · #2 first ingest (2,053 artifacts) · #3 candidates (evidence push rejected, fixed) ·
  #4 chain · #5 split events · #6 chain after pit_shares fix (current evidence).

Persistent raw store (C-21 manifest/evidence policy)
- In git + this ZIP: implementation/data/raw/manifests/ (2,912), STORE_INDEX.json (url + sha256 + bytes per artifact), ingest_run_*.json.
- Blobs (2.35 GB) are NOT in git/ZIP (git-ignored): GitHub Actions artifact "c21-raw-store-36117017112" (id 10855214590, 190 MB zip,
  sha256 24dd30ce..., expires 2026-12-24) and actions cache key prefix c21-raw-store-v1- (evicted after 7 days unused).
  Re-run the workflow before expiry to refresh; any blob is re-fetchable from STORE_INDEX source_url and sha256-verifiable.

Code changes this round (minimal, additive, all tested)
1. run_top500_gate_chain.py: company-level ranking, one line per CIK (primary = first SEC submissions ticker present). Row-level
   listings had 879 rows for 604 issuers (preferreds BAC-PB, OTC lines ASMLF, extra classes), each ranked with the issuer's total
   shares -> inflated rankable 731 / cutoff $22.0B. Row-level audit still reported for comparison.
2. audit_mcap_store.py: market-cap price = Yahoo close x split factor after as_of (yahoo_events artifact). Before, parse_bars
   'price' (= dividend-adjusted adjclose) was used, and post-as_of splits shrank caps (ORLY 15:1, BKNG 25:1, KLAC 10:1 in 2025).
   Verified: ORLY $68.1B, BKNG $165B, KLAC $84.8B at 2024-12-31. Also row_detail() diagnostics.
3. universe/sources.py pit_shares: within the latest filing, use the latest 'end' date before calling values multi-class
   (10-Q reports period-end and prior-year-end shares). Fixed 13 false MULTI_CLASS_AMBIGUOUS (GOOGL #5 $2.35T, PLTR, DELL, ADM...).
   True same-date multi-values stay ambiguous (existing test unchanged).
4. Delisted 2024-12-31 S&P members (ANSS DAY HES HOLX IPG JNPR K WBA): candidate CIKs in
   reports/gate_evidence/delisted_cik_candidates_2024-12-31.json, accepted ONLY after SEC submissions name match -> 8/8 verified.
5. Official is blocked while any top-500 row carries a quality flag (FOREIGN_ISSUER_ADR_RATIO_UNRESOLVED for 20-F/40-F filers,
   SPLIT_EVENTS_MISSING) — per contract "duplicate listings/share classes/ADR must be resolved before official promotion".
6. fetch_real_data.py: --with-split-events; throttle only after a real request (skips no longer sleep).
7. Tests: 194/194 (shim) and 194/194 (real pytest). reports/mini_pytest_2026-09-25_claude_code_r7.txt, reports/pytest_2026-09-25_claude_code_r7.txt

Status snapshot (as_of 2024-12-31, evidence: reports/gate_evidence/gate_chain_2024-12-31_real_gha.json)
- Raw artifacts: 2,912 (SEC companyfacts 604, submissions 604, Yahoo charts 860, split events 843, sec_tickers 1), 2.35 GB
- Pool: 879 listing rows -> 604 issuers (275 extra lines collapsed; 89 multi-line issuers, all primary chosen from SEC submissions)
- Reference coverage (S&P 500 reconstructed, 503, detector only): missing_from_pool 0 · present_not_rankable 26 · rankable outside computed top 500: 52
- rankable: 554 issuers (missing price 13 = 10 delisted/404 on Yahoo + 3; missing shares 29; ambiguous 0; non-positive 8)
- #500 cutoff: $12.43B
- Top-500 row quality: 432 clean · 63 FOREIGN_ISSUER_ADR_RATIO_UNRESOLVED (e.g. TM $2.6T, BABA $1.6T, HSBC $0.95T are ADR-ratio-inflated) · 5 SPLIT_EVENTS_MISSING (MOH EPAM CAG POOL KMX)
- Universe Completeness Gate: FAIL (604 issuers vs WFE low estimate 3,400)
- Top-500 Sufficiency Gate: FAIL (NO_REFERENCE_PASSED_ITS_OWN_CHECKS; the S&P detector itself shows 26 not-rankable + 52 outside; detector can never pass it)
- Promotion Gate v2: FAIL (no dated eligibility attestation; neither completeness nor sufficiency)
- Official US Market-Cap Top 500 PIT: NOT declared (blockers: PROMOTION_GATE_V2_FAILED, TOP500_ROWS_FOREIGN_ISSUER_ADR_RATIO_UNRESOLVED, TOP500_ROWS_SPLIT_EVENTS_MISSING)
- REAL-DATA VERIFIED: NO (real data INGESTED and ranked; not verified: gates fail and known defects remain)
- Walk-forward (>=3 real dates): NOT RUN · 500-company real benchmark: NOT RUN (Official blocked)
Validation ladder: Code YES · Reproducible YES · SYNTHETIC VERIFIED YES (194) · REAL DATA INGESTED YES (new) · REAL-DATA VERIFIED NO · Full PIT NO · OOS NO · Calibration NO · Forward NO.

Open issues (priority)
1. ADR ratio for 63 foreign issuers in the top 500 (SEC dei = ordinary shares; US line is often an ADR). Needs an ADR-ratio source
   or a policy decision to exclude foreign private issuers from the US Top-500 (C-18 wording: "US Market-Cap Top 500"). USER DECISION.
2. 13 S&P issuers with shares MISSING because cover-page shares are class-dimensioned and absent from companyfacts
   (META, XOM, LEN, STZ, TSN, UHS, RL, MKC, HRL, EL, ERIE, ABNB, PSKY). Needs a filing-instance (XBRL) share-class provider;
   never approximate with weighted-average shares.
3. Prices for 10 names delisted after 2024-12-31 (Yahoo 404: ANSS DAY HES HOLX IPG JNPR K WBA DFS CTRA) — needs a delisted-price source.
4. Eligibility attestation for the base gate (dated eligible-US-listing source) and an independent (non-S&P) PIT large-cap
   reference for Sufficiency; pool expansion beyond 604 issuers for Completeness (full SEC filer universe).
5. C-17 filing vintage/restatement; C-23 now mostly handled by company-level dedupe (remaining: foreign ADR lines).

Next Action
1. Decide #1 (ADR policy). If "exclude foreign private issuers": add that as a documented eligibility rule and re-run the chain
   (workflow_dispatch skip_fetch=true). If "include": add an ADR-ratio source.
2. Implement #2 (XBRL instance share classes) as a new provider + artifact kind; re-run.
3. Only when official_blockers is empty: official_mcap500_snapshot_from_store -> >=3-date real walk-forward -> 500-company benchmark
   (add them as workflow steps; the runner has the data).

Do Not Repeat
- Everything in prior Do Not Repeat lists.
- Do not rank row-level listings (one issuer = one row). Do not use adjclose or split-adjusted closes for PIT market cap.
- Do not treat two dates in one filing as multi-class. Do not accept unverified CIK candidates.
- Do not re-probe SEC/Yahoo from the Claude container; use the workflow. Do not re-download: the cache/artifact resume works.
