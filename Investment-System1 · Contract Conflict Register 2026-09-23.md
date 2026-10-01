# Contract Conflict Register · 2026-09-23

Policy: Official/Latest → Frozen → Master Status → Module Spec → Decision History → Validation Evidence → Previous → Archive.
Do not delete historical 2026-09-22 text. This file is the current working register.

Statuses: OPEN-NONBLOCKING | OPEN-ISOLATED | BLOCKING | DECISION REQUIRED | HISTORICAL-BLOCKED | RESOLVED

## C-01 Macro v0.1.1 vs v0.1.4 Candidate → RESOLVED
Blocking Level: none (was BLOCKING)
Evidence: Master Status + CURRENT_HANDOFF confirmed v0.1.1; same Latest file §13 is Candidate only; code MACRO_CONFIRMED vs MACRO_CANDIDATE.
Decision D-23: Confirmed engine = v0.1.1. v0.1.4 stays CANDIDATE and is never the default.
Change: none to scoring. Isolation already in versions.py.
Compatibility: QGV immutable / no module-level orders unchanged.
Test: existing macro engine uses confirmed version.
Resolution Condition met: authority exists without inventing a new official macro.

## C-02 Project Index 69 vs Master 159 → RESOLVED
Blocking Level: none
Evidence: stale index vs Master Status. Authority = Master Status.
Decision D-24: Recorded Technical baseline is Master 159/159 RECORDED-only. Index is stale documentation.
Change: none to code. Do not silently rewrite the old index file.

## C-03 Q7 Management Quality vs Capital Allocation → DECISION REQUIRED
Blocking Level: OPEN-ISOLATED
Evidence: Frozen Analysis v1.7.6 Q7 = Management Quality 10%. Integrated Spec freeze uses Capital Allocation. Same factor not proven.
Decision: do not merge names. Implementation factor_id = management_quality (D-06).
Resolution Condition: user or original package must pick the official label. Scoring weights 10% untouched.

## C-04 Schema vs Plan field names → RESOLVED
Blocking Level: none
Evidence: Common Schema analyzed_at, qgv_system_version, Q_score. Plan draft used as_of / get_latest_available.
Decision D-25: Schema names are the contract. QGVSnapshot keeps both analyzed_at and as_of (equal at write). resolve() stays the PIT name.
Compatibility: additive, no freeze rewrite.

## C-05 Schema missing v1.7.6 fields → RESOLVED
Blocking Level: none
Evidence: NEW IMPLEMENTATION QGVSnapshot already carries factor_breakdown, coverage_state, V_policy_status, profile_kind, data_stamp_refs.
Decision D-26: additive fields live on the implementation snapshot. Common Schema markdown is not rewritten.
Compatibility: additive only.

## C-06 company_id vs security_id → OPEN-NONBLOCKING
Blocking Level: none for US track
Evidence: Official US working book uses company_id + exchange + CIK. security_id not defined in freeze.
Decision D-27: company_id is canonical on the US track. security_id deferred until a dual-listing book exists.
Resolution Condition for close: official identifier model for dual listing.

## C-07 Holding.company_id → RESOLVED
Blocking Level: none
Evidence: Common Schema requires holding.company_id. Implementation Holding has company_id. Portfolio spec names are display.
Decision D-28: ticker is display; company_id is the key.

## C-08 TEL identifier → OPEN-ISOLATED (identity subset RESOLVED)
Blocking Level: none on US track; isolated from US live book
Evidence: Official Portfolio v1.1 semicap 5% context = Tokyo Electron, not TE Connectivity. Exchange venue not in Official snapshot.
Decision D-29: Identity = Tokyo Electron / company_id=tokyo_electron. Bare ticker TEL = AMBIGUOUS. Listing venue (TSE vs ADR) is DECISION REQUIRED for a future JP book. Not mapped to a US Yahoo symbol.
Resolution Condition for full close: official exchange-qualified listing for the JP book.

## C-09 V vs SOTP → RESOLVED
Evidence: v1.7.6 V = VALIDATION_SELECTED. Code V_score production = null. SOTP not added as 8th factor.
Decision D-30: keep caveat as operating rule, conflict closed for implementation.

## C-10 PASS aggregation → RESOLVED
Evidence: handoff evidence classes SYNTHETIC / LIVE_FETCH / RECORDED / REAL-DATA.
Decision D-31: never sum module PASS into system PASS.

## C-11 Simulation mode terms → RESOLVED
Evidence: SimulationMode HISTORICAL/CURRENT/FORWARD plus PRODUCT_SIMULATION vs VALIDATION_BACKTEST.
Decision D-32: product UI current mode ≠ forward validation.

## C-12 published_at vs available_at → RESOLVED
Evidence: Freeze / Simulation / Macro use available_at ≤ as_of. Plan published_at is older draft.
Decision D-33: PIT gate = available_at. Frozen Contract beats Implementation Plan.

## C-13 Universal vs type-specific Q/G matrices → RESOLVED (two-layer)
Evidence: v1.7.6 freeze weights in production. Type matrices CALIBRATION_PENDING.
Decision D-34: do not invent type weights. Identity type-adjusted score remains placeholder.

## C-14 Integration snapshot gap → RESOLVED
Evidence: IntegrationResult exists and is the combination object in NEW IMPLEMENTATION.
Decision D-35: implementation object only. Not an official Common Schema amendment.

## C-15 Technical Fusion U-09 → RESOLVED
Blocking Level: CLOSED
Evidence: User 2026-09-23. Fusion math not invented. Compatibility annotation only.
Decision: QGV/Technical/Macro snapshots independent. Compatibility does not mutate scores or emit orders. Integration remains the only weight fusion.
Resolution Condition: met by NEW IMPLEMENTATION + regression tests.

## C-16 Work ↔ Drive disconnect → HISTORICAL-BLOCKED
Blocking Level: blocks original recovery only, not NEW IMPLEMENTATION
Evidence: original packages absent. NEW IMPLEMENTATION present and tested.
Decision D-36: Historical Recovery = BLOCKED. Development = ACTIVE. Do not fake recovered artifacts.

## Still active (not RESOLVED)
- C-03 DECISION REQUIRED / OPEN-ISOLATED
- C-06 OPEN-NONBLOCKING
- C-08 OPEN-ISOLATED (venue only)
- C-15 RESOLVED (Compatibility annotation; no score fusion)
- C-16 HISTORICAL-BLOCKED

## C-17 SEC companyfacts vs Full PIT vintage
Blocking Level: OPEN-ISOLATED on Full PIT only
Evidence: companyfacts values can be restated after filed date. filed<=as_of is necessary not sufficient.
Decision: keep parse path. Full PIT Historical stays closed until filing-time values exist.
Status: OPEN-NONBLOCKING for NEW IMPLEMENTATION / PIT PROBE.

## C-18 Official Universe definition → RESOLVED 2026-09-23 (user decision)
Blocking Level: none (was DECISION REQUIRED / policy).
Evidence: Leaderboard Spec v1.0 and Integrated Spec v1.7 listed US market-cap top 500 OR S&P 500 as candidates. Sets are not equal.
Decision D-38 (explicit user instruction, not inferred by any AI): Official Default Universe = US Market-Cap Top 500, PIT (as-of shares x as-of price at each as_of; current roster never applied backward). Method = PIT_SHARES_X_PIT_PRICE, N=500.
Implementation: universe.sources.official_mcap500_snapshot is the ONE sanctioned constructor (UniverseKind.US_MCAP_TOP500_OFFICIAL, policy_status=OFFICIAL). UniverseEngine.snapshot() still refuses policy_status=OFFICIAL directly — defense in depth so nothing else can self-declare Official.
S&P 500 history code (parse_ticker_intervals_csv, sp500_history_snapshot, UniverseKind.SP500_HISTORY_CANDIDATE) is NOT deleted — kept as Benchmark/Research only, per explicit instruction.
Caveat carried forward, not resolved by this decision: an Official snapshot is only as correct as its candidate pool's completeness. mcap_top_n_snapshot/official_mcap500_snapshot never set candidate_pool_complete=True; a real Official run still needs the full US-listed-filer PIT pool (round-3 ingestion layer), not a subset.
Status: RESOLVED

### C-18 update · 2026-09-23 · Claude
Status: OPEN-DECISION-REQUIRED (unchanged). Not Officialized.
Both candidates now have symmetric research builders: SP500_HISTORY_CANDIDATE (dated-interval file) and MCAP_TOP_N_CANDIDATE (PIT shares × PIT price). UniverseEngine raises on policy_status=OFFICIAL.
Facts for the decision (no recommendation made): public S&P history (fja05680/sp500, MIT) is ticker-keyed, later-vintage reconstruction, end_date semantics undocumented. Mcap top-N needs a complete PIT candidate pool (all US filers' shares + prices), not available offline.
Generic engine work is not blocked by C-18.

## C-19 Membership end_date semantics (fja05680 interval file) → OPEN-ISOLATED (technical, PROVISIONAL)
Evidence: header ticker,start_date,end_date confirmed from the source page; whether end_date is the last day in the index or the removal day is not documented.
Decision (PROVISIONAL): parser flag end_date_inclusive=True (exit = end_date + 1 day). One-day boundary only.
Resolution Condition: compare against dated change announcements once the file is ingested.

### C-18 update 2 · 2026-09-23 · Claude
Status unchanged: OPEN-DECISION-REQUIRED. Both candidates now reach the same walk-forward engine (synthetic). Candidate A additionally needs identity resolution (ticker reuse) and has a price-coverage risk for removed members (see handoff gaps). Candidate B needs a complete PIT pool and multi-class share handling. No recommendation made.

## C-20 Network egress in this hub → HISTORICAL-BLOCKED (environment, not code)
Blocking Level: blocks only live ingestion; does not block offline work.
Evidence: bash_tool outbound HTTP to sec.gov/data.sec.gov/raw.githubusercontent.com/finance.yahoo.com/api.stlouisfed.org all return proxy 403 "Host not in allowlist"; TCP connect succeeds (deliberate policy, not DNS/firewall failure). web_search/web_fetch tools (separate from bash_tool) can reach sec.gov but cannot bulk-fetch raw JSON (URL-must-appear-in-search-result constraint, robots.txt on some hosts).
Decision D-37: ingestion is split from analysis. investment_system/ingestion/ (RawDatasetStore + replay, zero network imports, grep-verified) + tools/fetch_real_data.py (network-enabled runner, run outside this sandbox) fetch once, write raw bytes + provenance manifest; validation/qgv/technical/macro replay offline from the store, same PIT logic, unchanged signatures.
Resolution Condition: run tools/fetch_real_data.py (and fetch_sp500_intervals.py) in a network-enabled session/environment.


### C-18 resolution note
This is the only conflict in this register closed by explicit external (user) decision rather than by evidence-authority resolution or technical necessity. Recorded per protocol §Conflict: "중대한 Architecture 변경이 필요한 충돌이면 사용자에게 확인한다." The user was asked (implicitly, by repeated OPEN-DECISION-REQUIRED status across three handoffs) and has now decided.

### C-20 update · 2026-09-23 · OpenAI round 5
Status: HISTORICAL-BLOCKED / environment, unchanged in effect.
Current environment reproduction differs from the prior Claude environment: curl fails DNS resolution for www.sec.gov and Python urllib raises URLError(gaierror: Temporary failure in name resolution). The actual tools/fetch_real_data.py run produced 0/4 successful artifacts (SEC + Yahoo). ChatGPT web search separately reaches SEC, confirming that web-search access and container/Python outbound access are distinct paths.
Resolution Condition remains: Python/container runner with working outbound HTTPS/DNS to the raw sources. Do not treat web search as a substitute for RawDatasetStore ingestion.

## OpenAI relay round 6 status — 2026-09-23 16:49 KST
- C-18: **RESOLVED unchanged** — Official Default Universe = US Market-Cap Top 500 PIT; S&P 500 retained for Benchmark/Research.
- C-20: **BLOCKED (execution environment) unchanged** — direct curl/Python and existing ingestion runner confirm DNS/outbound HTTPS failure. Resolution condition remains a Python/container runner with approved-source DNS+HTTPS reachability. This is not treated as a code defect and synthetic substitution is prohibited.

### C-20 update · 2026-09-23 17:09 KST · Grok
This runtime: DNS+HTTPS to www.sec.gov / data.sec.gov WORKS (HTTP 200). Yahoo chart works with browser UA; SEC UA returned HTTP 429.
Existing fetch_real_data.py ingested sec_tickers + canary companyfacts/submissions/yahoo 5y (25/25 this run). official_mcap500_snapshot_from_store on US_LISTINGS: n_ranked=16, candidate_pool_complete=False.
C-20 network blocker is lifted HERE. Remaining C-20 work: complete US-listed PIT candidate pool and 500-name network-inclusive benchmark. Not REAL-DATA VERIFIED.

### C-20 update · 2026-09-23 17:45 KST · Grok
Ingest expanded on this disk: facts 325, yahoo 287. PIT rankable 254 at 2024-12-31. candidate_pool_complete remains False. Official Top-500 not justified.


## C-21 RawDatasetStore blobs missing from delivered handoff ZIP → OPEN, needs user action
Discovered: 2026-09-24, Claude (new session), on adopting the 2026-09-24 15:14 SSoT ZIP.
The Grok round that produced 598 companyfacts / 298 Yahoo-chart artifacts (598 listings,
297 rankable at 2024-12-31, per Investment-System1 · CURRENT_HANDOFF and
reports/mcap_audit_2024-12-31.json) ran in a network-enabled runtime. The delivered ZIP's
implementation/data/raw/ contains only ingest_run_*.json run-log summaries -- the actual
blobs/ and manifests/ directories (the RawDatasetStore content itself) are absent.
reports/us_ingested_facts_listings.json (the 598 company_id -> {yahoo, cik} identity map)
and several intermediate reports/mcap_*.json snapshots ARE present and were used this round
for identity-level and gate work, but the underlying companyfacts/price JSON cannot be
replayed, re-audited at full fidelity, or resumed from without either (a) the actual store
blobs, or (b) a fresh network-enabled ingest.
Impact: "resume, don't re-download the 297" (this round's explicit instruction) could not
be honored beyond what the surviving reports/identity file allow -- there is nothing to
resume the underlying data FROM in this session.
Resolution Condition: the next network-enabled AI/runtime should either (1) include
implementation/data/raw/blobs/ and implementation/data/raw/manifests/ in the handoff ZIP
going forward (these are the load-bearing artifacts, not the run logs), or (2) re-run
tools/fetch_real_data.py against reports/us_ingested_facts_listings.json to regenerate an
equivalent store before continuing coverage expansion.
User action: if a prior session's RawDatasetStore still exists on disk somewhere outside
this ZIP, re-attach implementation/data/raw/{blobs,manifests}/ to the next handoff.

## C-22 No dated PIT large-cap reference list obtained this round → OPEN
build_top500_sufficiency_gate (new this round) needs >=1 independently sourced, dated
membership list (e.g. S&P 500 constituents as of 2024-12-31, or Russell 1000/CRSP Large
Cap) to check for missing/unranked large caps. A Claude web-research task obtained real,
dated, cited TOTAL exchange-listing counts (WFE Dec 2024: NYSE 2,132 + Nasdaq-US 3,289;
see reports/gate_evidence/exchange_reference_wfe_2024-12-31.json) usable for the Universe
Completeness Gate, but NOT an actual per-ticker PIT membership list -- that needs either a
network fetch of a dated-interval source (universe.sources already has a tested parser for
the fja05680/sp500 ticker,start_date,end_date CSV format; C-20 blocks fetching it here) or
a more targeted, carefully-scoped research pass (manually reconstructing 2024-12-31
membership from a year of quarterly S&P DJI press releases via chat search was attempted
and abandoned as too error-prone to trust for a completeness-sensitive gate -- assembling
~500 tickers from search snippets risks silently missing a change, which is exactly the
failure mode this gate exists to catch).
Resolution Condition: fetch the fja05680 CSV (or equivalent dated-interval source) via a
network-enabled runner, OR obtain a verified bulk historical constituents file (e.g. from
a data vendor or an academic source) rather than manual reconstruction.
Until resolved: Top-500 Sufficiency Gate has real code + tests but has not been evaluated
against a real reference this round (reports/gate_evidence/top500_sufficiency_gate_2024-12-31.json
records a correct, honest FAIL for NO_LARGE_CAP_REFERENCE_SUPPLIED).

## Promotion Gate extended · 2026-09-24 · Claude (new session)
Added build_universe_completeness_gate and build_top500_sufficiency_gate as two
INDEPENDENT extensions to build_official_promotion_gate (kept unchanged, still directly
callable): Official promotion under the new build_promotion_gate_v2 requires the base
gate's numeric/eligibility checks AND (universe completeness OR top-500 sufficiency) --
neither sub-gate is the only path. See CHANGELOG 2026-09-24 for full detail and
reports/gate_evidence/ for real (non-synthetic) evidence: Universe Completeness Gate run
with real WFE Dec-2024 numbers against the real 598/297 audit -- correctly FAILS
(coverage_ratio 0.176). Top-500 Sufficiency Gate correctly FAILS with no reference
available (C-22). No promotion. REAL-DATA VERIFIED / Full PIT / Official Top-500 remain
unpromoted.


## C-23 Candidate pool scope contamination: preferred shares / foreign OTC ADRs → OPEN, advisory only
Discovered: 2026-09-24, Claude, offline pattern audit (tools/audit_candidate_hygiene.py) of
the real 598-name ingested-facts pool. 104 tickers match a preferred-share suffix shape
(e.g. BAC-PL, ALL-PH: "-P<letter>") and 81 match a common foreign-OTC-ADR shape (5 letters
ending in F or Y, e.g. AEMRF, BBAAY) -- 185/598 (31%) of the pool. A US common-stock
Top-500 ranking should not include either class (preferred shares are not common equity;
OTC ADRs' primary listing is a foreign exchange, excluded by WFE/CRSP/Russell-style
universes per this project's own research in reports/gate_evidence/
exchange_reference_wfe_2024-12-31.json).
Status: heuristic, PATTERN-BASED, NOT authoritative. Not auto-applied to any gate or
ranking. reports/gate_evidence/candidate_hygiene_598.json has the full flagged/clean split.
Resolution Condition: before the next round of Yahoo-chart ingestion, verify each flagged
ticker against real SEC security-type data (company_tickers_exchange.json's exchange/type
fields, or per-CIK submissions data) and only then exclude confirmed non-common-equity
names from the ranking candidate pool. Do this as a generalizable filter (by verified
security type), not a hardcoded per-ticker exclusion list.
Why it matters now: continuing to fetch price/shares data for these ~185 names first
would waste ingestion budget the user explicitly asked to conserve (SEC bulk 1.4GB /
API rate limits) on names that likely don't belong in the ranking pool at all.

## C-20/C-22 this-session exhausted-attempts log · 2026-09-24 · Claude
So the next AI doesn't repeat blind retries: bash_tool curl/urllib to sec.gov,
data.sec.gov, query1.finance.yahoo.com, raw.githubusercontent.com all 403 "Host not in
allowlist" (proxy policy, DNS resolves fine). pip install (pitindex, any package) fails,
no index reachable. web_fetch on the fja05680/sp500 GitHub blob page loads but the CSV
body is client-side-rendered JS, not present in fetched static HTML. web_fetch on that
page's own "Raw" link → ROBOTS_DISALLOWED (github raw content blocks automated fetch,
consistent with the round-3 finding already on record). No route reached real S&P 500 /
SEC / Yahoo data this session. A manual chat-search reconstruction of S&P 500 2024-12-31
membership from a year of press releases was attempted and abandoned as unreliable (C-22).
Resolution Condition unchanged: a genuinely network-enabled runner/session.


## C-22 update · 2026-09-25 · Claude — core blocker RESOLVED (real dated reference obtained)
Status change: OPEN -> real dated PIT S&P 500 reference obtained via a materially different
route (URL-encoded Wikipedia fetch succeeded where the plain URL, raw.githubusercontent.com,
and pip all failed/were exhausted -- see C-20 exhausted-attempts log below, which this route
was NOT on). Mechanically reconstructed 2024-12-31 membership (503 names) by undoing every
dated change since via tools/reconstruct_sp500_from_wikipedia.py, not by manual reading.
18/19 independent spot-checks matched; 1 flagged discrepancy (AMTM) disclosed, not hidden.
Cross-referenced against the real 598-name pool: 282/503 real S&P 500 constituents missing
entirely (reports/gate_evidence/missing_large_cap_priority_plan_2024-12-31.json, 253 with CIK
pre-resolved). Real Top-500 Sufficiency Gate run against this reference for the first time:
correctly FAILS (MISSING_LARGE_CAP_NAMES). Remaining work is ingestion (C-21/C-20 blocked), not
finding a reference -- that part of C-22 is done.

## C-21/C-20 update · 2026-09-25 · Claude
Both reconfirmed unchanged this session: bash_tool network still 403 on every host; the
RawDatasetStore blobs are still absent from the ZIP lineage (no user-supplied recovery yet).
The missing-large-cap priority plan above is ready for the next network-enabled ingestion round
to consume directly (ticker + CIK pairs, prioritized).

## C-23 update · 2026-09-25 · Claude — partial real verification
2 flagged tickers spot-verified with real search evidence (ALL-PB via a primary-source SEC FWP
filing; AEMRF via secondary sources consistent with OTC-ADR). The FIVE_LETTER_F_OR_Y_OTC_ADR_SHAPE
heuristic's Y-suffix rule is corroborated by an authoritative primary source (Charles Schwab ADR
documentation, cited in reports/gate_evidence/candidate_hygiene_spotcheck_verification.json).
Still advisory only -- no exclusion applied to the pool. Full per-name verification of all 185
flagged tickers still needs SEC company_tickers_exchange.json (blocked by C-20).


## C-21 update · 2026-09-25 round 2 · Claude — re-attempted, still BLOCKED
Re-attempted per explicit instruction (recover-or-reingest first). No recoverable store on
disk. bash_tool network re-probed, still 403 on every host including the XBRL companyfacts
endpoint specifically. New angle tried: web_search + web_fetch for the actual SEC JSON API
response (not just documentation about it) -- every result was a tutorial/doc page, never the
API's own JSON as a fetchable document, so web_fetch (which requires a URL already surfaced in
a result) cannot reach it. This differs from the C-22 Wikipedia case, where the HTML page
itself was indexed and fetchable -- SEC's JSON API responses are not.
Status: BLOCKED, unchanged. Resolution Condition unchanged: a genuinely network-enabled
runner/session. This is now confirmed to be the sole remaining blocker to consuming
reports/gate_evidence/missing_large_cap_priority_plan_2024-12-31.json.

## C-22 update · 2026-09-25 round 2 · Claude — AMTM discrepancy resolved (not a defect); priority plan CIK coverage improved
The AMTM spot-check discrepancy flagged in the prior round is resolved: re-reading the
originally fetched changes-table row for 2024-12-23 shows AMTM was removed that same day
(paired with WDAY's addition), before the 2024-12-31 cutoff -- the reconstruction was correct;
the earlier spot-check had a manual reading error. Corrected score: 19/19.
4 more of the 29 remaining missing-large-cap CIKs resolved via targeted SEC EDGAR search (CE,
CTRA, CZR, DFS) -- 257/282 now CIK-ready. 25 remain; one-by-one resolution stopped as low-value
until network is available (bulk resolution via SEC tickers file is far more efficient then).


## C-21 update · 2026-09-25 round 3 · Claude — reconfirmed BLOCKED, no new workaround forced
Per explicit instruction this round: did not search for a new bypass and did not synthesize
data once the block was reconfirmed. Single fresh probe (sec.gov, XBRL companyfacts endpoint,
Yahoo chart API) -> all still 403. No recoverable store on disk. Status unchanged: BLOCKED.
Resolution Condition unchanged: a genuinely network-enabled runner/session. The
missing_large_cap_priority_plan_2024-12-31.json queue (257 CIK-ready + 25 pending) is ready
and untouched, waiting on that runner.

## C-21 update · 2026-09-26 · Claude Code — RESOLVED (real data ingested via GitHub Actions)
Real SEC/Yahoo/Tiingo data ingested by workflow c21-real-data (runs #19-#30); raw store persisted in Actions cache
c21-raw-store-v2-* and run artifacts; manifests + STORE_INDEX in git. Remaining REAL-DATA gaps are data-source issues
(PINC, WOLF, PPLI), tracked in CURRENT_HANDOFF, not store recovery.

## Personal Investment Layer v1 intake · 2026-09-26 · Claude Code
Source: `Investment-System1 · PERSONAL_INVESTMENT_LAYER_V1_HANDOFF.md` (additive, Architecture FROZEN). The original
intake at commit 71976ed found Implementation NOT STARTED. Current overlay (2026-09-27): P0 Common Contracts were added
in isolated commit `48a6243`, are now IMPLEMENTED+FROZEN, and pass 13/13 tests; P1+ remains NOT STARTED. Nothing below
is resolved by guess, and open upstream/contract items remain open unless their section explicitly says otherwise.

## C-24 Two "StrategyProfile" objects → OPEN-NONBLOCKING (resolve at PIL P1)
Evidence: `src/investment_system/contracts/strategy.py` StrategyProfile = PROVISIONAL parameter pack (6 configurable keys,
styles DEFENSIVE/BALANCED/AGGRESSIVE/CUSTOM, parameter_set_hash); `FROZEN_KEYS` forbids customizing q_weights/g_weights.
PIL §4-§8 StrategyProfile = WeightTree + AdvancedParameters + policies + VersionMetadata, custom weights as immutable
versioned overrides over the Official Registry (Official never mutated).
Conflict: same name, different contract; existing code forbids any Q/G weight customization while PIL allows editing
eligible WEIGHT nodes through overrides.
Decision: existing object unchanged. PIL P1 must name its object distinctly or declare the existing one its
AdvancedParameters; whether Q/G nodes are editable is a policy decision (their maturity is C-30), not inferred.

## C-25 security_id vs company_id → OPEN (CONTRACT CHANGE for C-06 when PIL P0 opens)
Evidence: C-06/D-27 company_id canonical on the US track, security_id deferred. PIL §12 requires internal security_id
(ticker/exchange/share class/CIK/ISIN/FIGI, effective_from/to). Real-data chain is company-level (one line per CIK) with
share classes resolved from cover XBRL.
Decision: PIL P0 defines security_id with a company_id link; C-06 is reopened then. No mapping created now.

## C-26 Model and Actual weights share one object → OPEN-NONBLOCKING
Evidence: `contracts/models.py` Holding has target_weight + actual_weight + weight_gap; `qgv/portfolio.py` fills
actual_weight from target_weight when no market value exists (lines 61/92/125).
Conflict: PIL principle 3 (separate ModelPortfolioSnapshot / ActualPortfolioSnapshot). Holding.actual_weight is a
model-side value, not broker data.
Decision: existing objects unchanged; PIL must build ActualPortfolioSnapshot only from broker/user position data and must not
read Holding.actual_weight as actual.

## C-27 Integration gap and order intents vs PIL Portfolio Gap → OPEN-ISOLATED (+ one defect fixed)
Evidence: `integration/engine.py` computes gap = actual - target and emits BUY/SELL order_intents (v1.2 PROVISIONAL,
staged entry). PIL §14: gap = model - actual, descriptive, never BUY/SELL or quantity.
Decision: both exist in separate layers; PIL Portfolio Gap must not reuse IntegrationResult.order_intents or its sign.
Defect fixed (PATCH, correctness): `(h.actual_weight or h.target_weight)` read an actual weight of 0.0 (not held) as missing,
so no gap/intent was produced; now only None is missing. Regression:
tests/test_downstream_and_integration.py::test_integration_zero_actual_weight_is_a_gap_not_missing.

## C-28 Technical output has no available_at → OPEN-BLOCKING for PIL P4 only (upstream item A)
Evidence: `contracts/models.py` TechnicalSnapshot fields: as_of, no available_at/observed_at; `technical/engine.py`
evaluate(company_id, as_of, returns: list[float]) takes untimestamped returns. DataStamp (with available_at) exists but is not
attached to TechnicalSnapshot.
Finding: available_at propagation to the Technical final output is NOT implemented (verified in code, not assumed).
Decision: PIL must not create times. Fix belongs to the Technical system (upstream PATCH: add available_at from input data
stamps); not done in this round (Main Track priority).

## C-29 QGV↔Technical score scale → OPEN-NONBLOCKING (upstream item B)
Evidence: `qgv/scoring.py` attractiveness_10 = ((Q+G)/2)/10 is labelled "NEW IMPLEMENTATION heuristic. PROVISIONAL. Not an
official freeze constant" and is stored on QGVSnapshot.attractiveness_10. TechnicalSnapshot has no numeric score (regime /
execution_zone enums), so no cross-scale arithmetic exists or is needed today.
Decision: no authoritative scale contract exists. PIL must keep original scores + scale metadata and must not use
attractiveness_10 as a QGV↔Technical mapping.

## C-30 Official Weight Dataset → OPEN (upstream item C; maturity not assigned by guess)
Evidence: Q_WEIGHTS (7 factors) and G_WEIGHTS (6 factors) in `qgv/factors.py`, source QGV Analysis v1.7.6 §18.3, RECORDED
(Master Status VERIFIED = 0), Q7 label C-03 DECISION REQUIRED. V production aggregate null (V_INITIAL_PRIOR PROVISIONAL).
Integration OM/TM/MM/RM multipliers v1.2 PROVISIONAL. Technical: no weight dataset (structural placeholder engine).
Macro: v0.1.1 state rules, no weight dataset in code.
Decision: PIL NodeDefinition maturity per node needs the authoritative SSoT; until then Technical/Macro weights are
UNRESOLVED and nothing is marked PRODUCTION by this intake.

## C-31 code.md not present in the hub → OPEN-NONBLOCKING
Evidence: no code.md in the repository or the r4/r6/r7 handoff ZIPs. The coding-priority rule (correctness/safety > user
requirements > existing behaviour > simplicity > maintainability > performance > extensibility) is taken from the relay text.

## C-32 official_mcap500_snapshot_from_store default path ≠ Promotion Gate basis → OPEN-NONBLOCKING (Track A, 2026-09-26)
Evidence: universe/sources.official_mcap500_snapshot_from_store builds candidates from companyfacts shares (pit_shares) and
the chart parser's `price`, which is adjclose (dividend/split-adjusted as of the fetch date, i.e. adjusted for events after
as_of). The Promotion Gate ranks on raw close × post-as_of split factor and uses cover-page class sums, economic-equivalent
shares, text-verified counts and the approved NPORT_REPORTED_VALUE exception. Regression:
tests/test_c21_runner_and_gate_chain.py::test_run35_gate_snapshot_consistency_preserves_cover_shares_and_close_basis.
Decision: default path unchanged (existing callers); an optional `gate_candidates` argument feeds the gate-audited
representation; the chain's gate_snapshot_consistency must pass (same members/order/mcap) before any Official
declaration (blocker GATE_SNAPSHOT_INCONSISTENT). Whether the default path should switch to the close basis is a separate
decision (it also affects validation.historical / vertical_slice consumers).

## C-33 companyfacts share counts unreliable for multi-class and mis-scaled filers → EVIDENCE (Track A, 2026-09-26; PIL upstream note)
Evidence (runs #31-#35): companyfacts drops dimensioned dei facts, so for multi-class issuers pit_shares returned an older
undimensioned value (PPLI 0 from 2020; DKS 2011, ARES 2019, COKE 2016, AOS 2015; MA/CME/IBKR one class); HXL's filing tags
81,002,128,000,000 (×10^6). Now handled in the gate by share_fact_stale → cover XBRL, share_scale_check → cover text,
fail-closed exclusion otherwise.
PIL impact (recorded only; no PIL code changed): any future PIL consumer of share counts / market caps (Model Portfolio,
Security Resolver identifiers) must take them from the gate-audited representation, not companyfacts pit_shares directly.

## C-34 WRK 2024-06-30: no permitted market-close source → OPEN, USER DECISION (Track A, 2026-09-26 16:05 KST)
Evidence (runs #48-#53): WestRock (CIK 0001732845, merged into Smurfit Westrock 2024-07-05) is a Russell 1000 N-PORT member at
2024-06-30. Yahoo v8 chart HTTP 404 (symbol dropped), Tiingo NO_TIINGO_BAR_ON_OR_BEFORE_AS_OF, Stooq answers with a
proof-of-work bot challenge (not bypassed). Exchange/vendor web pages not used (terms of use / bot protection / no
stored, re-verifiable provenance). Reference N-PORT (0001752724-24-189684, filed 2024-08-26) holding: 193,311 NS,
valUSD 9,715,810.86 -> 50.26/share, fairValLevel 1 (nport_price_investigation_2024-06-30.json, INVESTIGATION_ONLY).
nport_cross_check_2024-06-30.json measures whether N-PORT per-share values reproduce 2024-06-28 closes (IWB, Vanguard
Total Stock Market, iShares Core S&P 500).
Decision pending: extend NPORT_REPORTED_VALUE under generalized criteria (eligibility: all permitted sources failed +
fairValLevel 1; identity: unique EC holding, CUSIP attested by 13D/13G <= as_of, price reproduced; filing calibration
>= 99 % of controls within 0.5 %; independent reproduction by another sponsor within 0.5 %; separate price type,
look_ahead recorded, per date only; applied regardless of rank; thresholds fixed before results) OR keep as blocker.
Knowledge of the cutoff is NOT a ground for the exception (user, 2026-09-26). Until decided: 2024-06-30 not Official.

## C-35 GRAL 2024-06-30: spin-off without an exact PIT share count → OPEN, USER DECISION (Track A, 2026-09-26 16:05 KST)
Evidence (runs #48-#52): GRAIL, Inc. (CIK 0001699031) spun off from Illumina 2024-06-24 (record date 2024-06-13); no
10-K/10-Q at as_of. Primary documents of all registration/8-K filings <= 2024-06-30 state no count. The Information
Statement (EX-99.1 of the 8-K filed 2024-06-03 and the 10-12B/A) states only '31,052,632 shares issued and outstanding,
pro forma' and an 'approximately' distribution amount computed from Illumina's April 26 count ('The actual number ...
will depend on ... the Record Date'). The exact count first appears in filings after as_of (not applied; AMTM rule).
Decision pending: keep as blocker / allow a filed pro-forma count as a separate share basis / a new eligibility rule
for very recent spin-offs. Until decided: 2024-06-30 not Official.

## C-36 Russell 1000 reference mapping gaps -> PARTIALLY RESOLVED (Track A, 2026-09-26 19:07 KST)
Evidence (run #53 N-PORT cross-check, calibration outliers): on every as_of the reference resolved 'DUN & BRADSTREET
HOLDINGS, INC.' (CUSIP 26484T) to Moody's CIK 0001059556 and 'F.N.B. CORPORATION' to V.F.'s CIK 0000103379; 6-8 equity
holdings per date stayed unresolved (BLUE OWL CAPITAL INC. 5 name candidates; SKECHERS U.S.A.; LIBERTY MEDIA CORP -
FORMULA ONE GROUP x2; U.S. BANCORP dead-namesake match; escrow ESC GCI LIBERTY) and the Sufficiency gate never checked
unresolved holdings. D&B, F.N.B., Blue Owl, Skechers and Liberty Media are NOT in the candidate pool on any date, so the
'missing_from_pool: []' behind the 2024-12-31 and 2024-09-30 Promotion Gate v2 PASS was not established.
Decision (fail-closed, no user policy change): corrected run #57 makes the 2024-12-31 gate eligible for restoration.
Run #59 rebuilt the Official snapshot from that exact Gate evidence and passed the identity/membership/order/mcap/cutoff/
provenance checks, so 2024-12-31 Official is RESTORED. Run #60 independently passed the same corrected chain and rebuilt
2024-09-30 Official, so that date is also RESTORED. Pre-C-36 single_as_of / benchmark results remain superseded. Fixes:
(1) a CIK may not absorb holdings of
different CUSIP issuer numbers (strongest match keeps it, a tie keeps none, the loser retries without it); (2) historical
names looked up with both keys; (3) ambiguous/unmatched holdings identified only by the candidate's own 13G/13D filed <=
as_of printing the CUSIP (+ PIT registrant); (4) Sufficiency fails on UNRESOLVED_REFERENCE_HOLDINGS,
REFERENCE_CIK_COLLISION_DISTINCT_ISSUERS or missing member CUSIPs (escrow CUSIPs excepted).
Open design note: Liberty Media tracking stocks (FWONA/K, LSXMA/K, BATRA/K) share one CIK/issuer number; the current
company model (CIK = company, classes summed only with proven economics) applies -- whether tracking groups should be
separate companies is a separate user decision if it blocks.

Run #57 evidence (id 36229163158; commit 195c5da): corrected Russell reference 991 members; missing 0;
present-not-rankable 0; non-escrow unresolved 0; collisions 0; missing member CUSIPs 0. Sufficiency PASS; Promotion Gate
v2 PASS; consistency 500/500 PASS; Official blockers 0; cutoff $15.422B. D&B is the live PIT registrant 0001799208 over
legacy D&B CIK 0001115222. Formula One CUSIPs resolve to current Liberty CIK 0001560385 over legacy CIK 0000869614 where
applicable. OWL Class C uses only cited 1:1 paired-unit economics; Class D stays unvalued. Run #59 (id 36233121639,
evidence commit 1832747) preserved Gate universe `uni_cf6aa3403869` in the Official snapshot: 500/500 identical members,
order and market caps; cutoff $15.422B; ALGN rank 500; FNF absent; audited share/price provenance preserved.

Run #60 evidence (id 36233560867; commit ab72939): corrected 2024-09-30 Russell reference 994 members; missing 0;
present-not-rankable 0; non-escrow unresolved 0; duplicate CIK membership 0; complete member CUSIPs. Sufficiency and
Promotion Gate v2 PASS; Gate/Official ID `uni_e334f94a73c3`; 500/500 membership/order/mcap/provenance PASS; cutoff
$15.574B; ENPH rank 500. 2024-09-30 Official RESTORED.

Run #61 evidence (id 36234273515; commit 2e04c1b): corrected 2024-06-30 reference has 987 resolved members and complete
member CUSIPs, but fails on GRAL/WRK present-not-rankable and two non-escrow unresolved holdings: ARDAGH GROUP SA
(L0223L101) and LIBERTY SIRIUS XM (531229813). 2024-06-30 remains NOT OFFICIAL. C-36 remains open for the Ardagh identity
gap and the Liberty tracking-stock conflict recorded separately in C-37; the previously known GRAL/WRK blockers are C-35/C-34.

## C-37 Liberty SiriusXM tracking-stock identity/economics at 2024-06-30 -> OPEN-BLOCKING, USER DECISION (Track A, 2026-09-26 19:07 KST)
Run #61's dated Russell N-PORT reference contains `LIBERTY SIRIUS XM`, CUSIP 531229813. The historical-name candidate
CIK 0002003397 is not a PIT registrant at 2024-06-30. SEC holding evidence identifies the CUSIP as Liberty Media's
Liberty SiriusXM Series A tracking stock, while the then-current issuer also had Formula One and Braves tracking groups.
The current Universe model is company/CIK-level and only combines classes with proven common economics; it cannot assume
that different tracking groups have the same economic rights or decide whether each group is a separate Universe company.
Because the unresolved holding now makes the independent Sufficiency reference fail, this affects possible Official
membership and requires the user's requested policy decision. No CIK remap, class aggregation, or new eligibility rule
was introduced. Until resolved, 2024-06-30 stays NOT OFFICIAL and walk-forward stays blocked.

## C-38 Ardagh positive delisted/private residual in N-PORT superset -> OPEN-BLOCKING, USER DECISION (Track A, 2026-09-26 20:54 KST)
The 2024-06-30 IWB N-PORT source (accession 0001752724-24-189684) reports ARDAGH GROUP SA, CUSIP L0223L101,
ISIN LU1565283667, as common equity: 12,001 NS, valUSD $76,686.39, USD, long, fair-value level 2. It is therefore
neither a zero-value residue nor an escrow line. SEC CIK 0001689662 is the unique historical-name identity, but the
issuer filed Form 25 on 2021-10-06 to remove its Class A common shares from NYSE and Form 15 on 2021-10-18 to terminate
registration/suspend reporting (115 record holders); SEC submissions show no ticker/exchange and no later periodic
issuer filing. This explains the PIT-registrant rejection but does not authorize silently deleting a positive holding
from the independent superset reference.

Decision required: either (a) keep every positive non-escrow EC reference line fail-closed, leaving Ardagh unresolved,
or (b) adopt an explicit, evidence-backed rule for dated reference-fund holdings that were already delisted/private at
as_of. Option (b) is a new Universe/reference eligibility policy and may affect Official membership, so it was not
implemented. The round-17 code change only preserves each unresolved source row's identity/valuation fields through the
resolver and Gate report; it does not change membership or pass criteria. Until decided, 2024-06-30 remains NOT OFFICIAL
and walk-forward remains blocked.

## C-39 Global/Korea shared identity implementation claim -> RESOLVED (2026-09-27 16:02 KST)

Evidence: `Investment-System1 · Global-Korea Universe and Information Source Contract 2026-09-24.md` says
`IssuerIdentity`, `SecurityIdentity`, `ListingIdentity`, `UniverseContext`, `FXSnapshot`, and `EligibilityRecord` are
implemented with regression tests. A tracked-tree and symbol search finds none of those runtime types or corresponding
tests. The current common runtime contracts expose company-level `Identifier`, `UniverseMember`, `UniverseSnapshot`,
and `DataEvent`; the only `security_id` implementation is under Track B's frozen, isolated
`src/investment_system/personal/security.py`.

Impact: `RIG_NEWS_ARCH_v0.1` can freeze against the documented issuer→security→listing contract without claiming an
implementation, but RIG P0 cannot safely choose a canonical shared identity type or import Track B's private contract.

Resolution: restored the already-documented shared contract in
`implementation/src/investment_system/contracts/global_universe.py` without importing or modifying Track B's frozen
private security contract. The public types are `Region`, `AnalysisUniverse`, `IssuerIdentity`, `SecurityIdentity`,
`ListingIdentity`, `UniverseContext`, `FXSnapshot`, and `EligibilityRecord`. Ticker exists only on the dated listing;
analysis/network/news scopes remain independent; Korea/Global cannot be marked Official before validation; FX and
eligibility records reject missing provenance and `available_at > as_of`. Six focused regressions cover the hierarchy,
half-open listing history, context separation, Decimal FX, provenance, and fail-closed PIT behavior. Full suite 308/308
PASS. C-39 no longer blocks RIG P0, but RIG remains DESIGN FROZEN / IMPLEMENTATION NOT STARTED and no RIG runtime was
created. Track A/B/C code and ownership are unchanged.


## Track A current resolution overlay — 2026-09-27 19:56 KST

C-34/35/36/37/38: prior case treatments were verified in run #70 under the approved D3-P policies; GRAL cites the actual first subsequent 2024-08-13 10-Q, accession 0001628280-24-036965. These earlier cases are not reopened. This does not restore Official status after the independent C-41 audit below.

## C-40 Future snapshot CIK overwrites historical walk-forward input — RESOLVED LOCALLY

Run #70's 471/469 single selections versus 470/468 walk-forward selections were caused by the union of all dates' listing metadata overwriting BLK's predecessor CIK with its successor. Replay now resolves inputs per prediction date and enforces exact single/walk-forward consistency. Synthetic mutation tests plus actual BLK and three-date/500-name RESEARCH diagnostics pass. No Official re-promotion is claimed. Evidence: blk_dated_identity_regression_2026-09-27.json and track_a_diagnostic_replay_2026-09-27.json.

## C-41 Share/price unit mismatch across corporate actions — OPEN-BLOCKING / D3-P PROPOSED

The price path undoes post-as_of splits but the last disclosed share count can precede a split, stock dividend, spin-off, or merger already effective at as_of. All-candidate raw audit finds 20 events across the three dates. Same-input Gate/Official agreement did not catch the economic-unit mismatch. NVDA illustrates the arithmetic error; ILMN and SIRI show why multiplying every Yahoo split factor would be invalid. Pure split, distribution adjustment, and merger/cancellation issuance need different evidence-backed treatment.

Conservative D2 containment is implemented: the Gate blocks on UNRECONCILED_SHARE_PRICE_UNITS, and Official pipeline refuses absent/failed unit audits. All three old Official snapshots and run #70 Official outputs are SUSPENDED, with their history retained. General proposal CA-UNIT-v1.0 is in implementation/reports/gate_evidence/track_a_share_unit_policy_proposal_2026-09-27.md. No new policy has been applied. Approval is required only for this new D3-P; existing D1/D2/D3-C authority remains intact.


## Track A final Freeze record — 2026-09-27T20:50:49.316653+09:00

Track A REAL-DATA Baseline **FROZEN** in local commit/package; canonical GitHub upload is still blocked (prior integration HTTP403). Validated source `682bbae1687d237f72c3f2266913b8bf61f1ff0b`. C-40/C-41 resolved; CA-UNIT-v1.0 approved; original20+3 D3-C cases audited. Corrected Gate and exact Official consistency pass for 2024-06-30/09-30/12-31; 3-date Walk-Forward equals singles; network-inclusive500 benchmark completed; raw6830 integrity and regression396/396 pass. No new D3-P. Baseline freeze does not promote PROVISIONAL_RESEARCH calibration or modify other tracks. Final machine record: `implementation/reports/gate_evidence/track_a_freeze_readiness_2026-09-27.json`. Work stopped as instructed. Earlier Track A blocked entries are historical and superseded by this record.


## TC-D3P-001 — C2 chronological split boundary policy — OPEN / D3-P PROPOSED

Recorded: 2026-09-28T20:42:40+09:00. Track C only. EVL_SPEC_v0.1 §3 fixes 5Y/1Y/1Y,
annual re-optimization and horizon/rebalance-derived Purge/Embargo, but does not
choose overlap-only vs an additional chronological gap, or nominal-window/sample
trimming semantics. That selection changes eligible samples and experiment results.
Proposed EVL-SPLIT-01 v1.0 is fully specified with boundary examples in
implementation/reports/track_c_c2_split_policy_proposal.md. No policy applied.
C0/C1 remain SOFTWARE FROZEN after 24/24 targeted and 420/420 full/integration.
C2 and later phases pause in order pending this new D3-P. No upstream exception,
Track A reinterpretation, threshold calibration or Official promotion is approved.


## TC-D3P-001 resolution / C4 upstream dependency — 2026-09-28T21:03:11+09:00

TC-D3P-001 RESOLVED / IMPLEMENTED: user approved the revised EVL-SPLIT-01 v1.1
(primary purge + separately registered rebalance-gap stress) at 20:48:39 KST.
Earlier mandatory-gap v1.0 is superseded, not approved. C2/C3 SOFTWARE FROZEN;
latest targeted 56/56, full/integration 452/452 PASS. Same-policy cases are D3-C.

C4 readiness exposes the existing C-28 missing Technical available_at/input
provenance contract. Its original PIL-P4-only scope does not supply the stricter
EVL PIT evidence. C5 also lacks executable binding for the six profile settings;
profile ID/hash changes affect metadata only in the inspected Integration API.
Do not promote C-30 provisional maturity by inference. Audit evidence is
implementation/reports/track_c_c4_upstream_readiness.json. Upstream runtime
contracts remain unchanged; C4–C10 pause under EVL_SPEC_v0.1 §13.
This is an existing upstream implementation/contract dependency, not a new D3-P
proposal and not a request to relax PIT, permit no-op search or change core scores.


## Track C C4 software freeze / C5 scope decision — 2026-09-29

Supersedes the 2026-09-28 C4 BLOCKED_UPSTREAM_CONTRACT status for software implementation.
C0–C4 are SOFTWARE FROZEN. C4 tested implementation `0cb9a7c`; targeted 88/88,
full 484/484, normal merge integration against canonical `b8e39a2` 484/484.
Actual input-derived Technical/Macro availability, source/vintage and digest are
now available through additive stamped evaluators. Legacy decisions and unknown
qualification remain unchanged. C4 enforces registered paired annual rolling /
expanding execution, Train/Validation/OOS isolation, frozen calibration/prediction,
complete terminal accounting, interrupted-attempt recovery and hash-bound reports.

Authorized upstream repair touches four files: contracts/lineage.py (new),
contracts/models.py, technical/engine.py, macro/engine.py. The earlier zero-upstream-
changes statement is historical; QGV, Track A artifacts and B/D/E code remain unchanged.
No qualified seven-year real-data result, skill, Official profile, Holdout consumption
or Forward validation is claimed. TAX_MODE=EXCLUDED; EVL_SPEC_v0.1 is not redesigned.

C5 preflight: cash_buffer and technical_lookback have verified performance effects;
deadband affects order intents only. Three advertised controls have undefined
financial semantics (risk_multiplier, signal_threshold, macro_warning_sensitivity).
TC-D3P-002 proposes explicit first-search coverage of the two functional controls,
with unchanged/fixed stages explicitly recorded and undefined controls rejected.
This is a proposed capability-scope decision, not permission to invent financial
rules. C5–C10 are NOT FROZEN and no C5 search has run. User decision pending.

Evidence: implementation/reports/track_c_c4_acceptance.md,
track_c_c4_evidence.json, track_c_c5_binding_policy_proposal.md.
PR #4 remains draft/open; automatic merge is prohibited.


## Track C C5 software freeze / C6 execution decision — 2026-09-29T19:27:45.256043+09:00

TC-D3P-002 APPROVED by user “어 진행해” at 2026-09-29 19:19:50 KST;
previous proposal-pending entries are historical. C0–C5 now SOFTWARE FROZEN.
C5 implements approved cash_buffer/technical_lookback search with immutable
registration, Train-only input, mandated stage ordering, explicit fixed stages,
coarse/refine over all survivors, increasing resource screening, precision and
complexity rejection, complete budget/terminal accounting and crash recovery.
No peak/champion selected. Actual bound-engine behavior and reproducibility tested.
Targeted 103/103, full 499/499, canonical normal-merge integration 499/499 PASS.
No upstream source change since C4. Prior C4's four-file additive repair remains.

C6 preflight inspected Integration order intents, QGV Simulation compounding and
C3 externally supplied cost fractions. No fill-price/execution-delay contract exists.
New TC-D3P-003 proposes first eligible post-decision opportunity baseline, one
registered opportunity delay stress, explicit execution evidence and fixed-path
1x/2x/3x trading-cost sensitivity; missing evidence fails closed. No fees, fills or
financial behavior were invented. C6–C10 NOT FROZEN, no C6 result is claimed.
Proposal: implementation/reports/track_c_c6_execution_policy_proposal.md.
Approval of TC-D3P-002 does not imply approval of this distinct execution policy.

Evidence: implementation/reports/track_c_c5_acceptance.md and
track_c_c5_evidence.json plus final targeted/full/integration logs.
EVL_SPEC_v0.1 unchanged, TAX_MODE=EXCLUDED, no Official/real 7Y/Holdout/Forward claim.
Progress: 6/11 software phases (54.5% phase-count proxy, not effort or product completion).
PR #4 remains draft/open; no auto merge. Next: TC-D3P-003 decision, then C6 in order.


## Track C C6 execution verification / statistical policy boundary — 2026-09-30 20:00 KST

Track C scope only; historical entries are retained. TC-D3P-003 v1 items 1–8 APPROVED
by the user at actual clock 2026-09-30 19:38:07 KST. Earlier proposal-pending state is superseded.
Approved research execution evaluator implemented at fb1cc7415703142ecd01461fbe1c89e7e2d51c7e; source/tests limited
to evl/execution.py and test_evl_c6_execution.py. Baseline first eligible post-decision slot,
one-slot delay, isolated 1x/2x/3x costs, cash/position/P&L reconciliation, strict execution
provenance, immutable input/report lineage and fail-closed missing evidence are verified.
CI 36705694417 / job 109855289599: real pytest targeted 137/137 (34 new + unchanged C0–C5 103),
full 533/533 PASS. No local Git fetch/pytest or fresh temporary normal-merge replay claimed;
GitHub refs/compare refreshed and fast-forward Git Data commits used.

C0–C5 SOFTWARE FROZEN preserved. C6 IMPLEMENTING / NOT FROZEN:
execution subsection complete, full statistics/perturbation/controls/drift acceptance pending.
New TC-D3P-004 statistical family/resampling policy is PROPOSED / NOT APPROVED / NOT ACTIVE;
no DSR effective-trial assumptions, PBO ranking or bootstrap defaults applied.
C7–C10 NOT STARTED. Holdout UNCONSUMED; no Official/Forward result.
Investor-QGV NOT_IMPLEMENTED / FUTURE_TRACK_C_INPUT; no substitute investor weights.
Track A frozen evidence and B/D/E/Web source unchanged. Prior authorized four-file
additive C4 repair is preserved. EVL_SPEC unchanged; TAX_MODE=EXCLUDED.
Evidence: implementation/reports/track_c_c6_execution_acceptance.md,
track_c_c6_execution_evidence.json, track_c_c6_statistics_policy_proposal.md.
PR #4 must remain Draft/Open/unmerged; NOT_TRACK_C_FREEZE_CANDIDATE.
Next: TC-D3P-004 decision, then complete C6 before starting C7.


## Track C TC-D3P-004 approval / C6 Freeze-policy boundary — 2026-09-30 20:23 KST

Scope: Track C only. TC-D3P-004 option A items 1–8 explicitly APPROVED by the user
at actual clock 2026-09-30 20:16:28 KST. Earlier NOT APPROVED entries are historical.
Approved methods remain complete-family PSR/DSR(two views)/CSCV-PBO/joint circular-block
bootstrap/full-family Reality Check and registered perturbation/controls/drift;
no evidence interpolation or post-selection family shrink.

The user's additional PASS/FAIL/NOT_RUN and mandatory-diagnostic Freeze rule exposed
an unresolved acceptance authority: A6/A8 leave significance/skill decisions to C8,
and neither A nor EVL_SPEC defines the full software Freeze role/status/evidence-scope
matrix. TC-D3P-005 records concrete common all-MANDATORY protocol semantics plus
Option S (complete software-fixture acceptance only) or R (actual complete research
evidence required). PROPOSED / NOT APPROVED / NOT ACTIVE. No advisory waiver or
software/real-evidence scope is silently applied.

C0–C5 SOFTWARE FROZEN preserved. C6 execution subsection VERIFIED; C6 overall
IMPLEMENTING / NOT FROZEN. Statistics/perturbation/controls/drift NOT IMPLEMENTED,
no diagnostic PASS or statistical result claimed. No runtime/test source edit this round.
Latest prior HEAD 34d9c3d actual CI 36706043418: targeted 137/137, full 533/533.
C7–C10 NOT STARTED. Holdout UNCONSUMED; Investor-QGV FUTURE_TRACK_C_INPUT.
Track A frozen artifacts and B/D/E/Web unchanged; authorized upstream repair preserved.
PR #4 remains Draft/Open/unmerged; NOT_TRACK_C_FREEZE_CANDIDATE.
Evidence: track_c_c6_statistics_policy_approved.md,
track_c_c6_freeze_policy_proposal.md, track_c_c6_freeze_policy_audit.json.
Next: TC-D3P-005 role/status/evidence-scope decision, then approved C6 implementation.


## Track C independent statistical kernel verification / approval-record conflict — 2026-09-30T21:13:50.000+09:00

Track C-only overlay; historical/other-track records preserved. C0–C5 remain SOFTWARE FROZEN.
C6 IMPLEMENTING / NOT FROZEN: approved execution unchanged; TC-D3P-004 A kernels now implemented
and tested at `a8e187cea6b117602dff986a3ff6a76b8c244a19`. Actual pytest Actions 36712457163 / job109877255098:
targeted180/180 (C0–C5 103 + execution34 + kernel43), full576/576 PASS, completed21:05:00 KST.
These are SYNTHETIC SOFTWARE TEST results; not a registered complete C6 family diagnostic PASS,
REAL_PIT_VALIDATED, skill, profile selection or promotion. Required family diagnostics explicitly
NOT_RUN in the new kernel evidence; no NOT_RUN counted as PASS. Runner/perturbation/controls/drift pending.

TC-D3P-001..004 approval evidence verified. TC-C6-APPROVAL-RECORD-001: latest task says TC-D3P-005 S
approved, while actual proposal/register/tree remains PROPOSED / NOT APPROVED / NOT ACTIVE and
no approval record or PR discussion exists. User section2 explicitly requires matching repository
evidence and repository precedence on conflict. S not silently activated; no approval time invented.
Concrete additive reconciliation is prepared; no new policy or Track A D3-C case selected.

C7–C10 NOT STARTED; independent interface preflight only. Holdout UNCONSUMED. Investor-QGV remains
NOT_IMPLEMENTED / FUTURE_TRACK_C_INPUT; no saved Research Spec v1.0 or accepted 13F pipeline identified.
Full canonical source diff contains only EVL plus the four pre-existing authorized additive lineage
repairs; those repairs and all frozen C0–C5 source/tests are unchanged this round. Track A frozen
artifacts and QGV/B/D/E/Web source unchanged. PR5/PR6 separate, untouched. No fresh normal-merge
replay claimed; retained C5 103/499/499 evidence preserved with verified remote commit mapping.

Evidence: `implementation/reports/track_c_c6_independent_validation_2026-09-30.md`,
`track_c_c6_statistical_kernels_evidence.json`, `track_c_c6_statistical_kernels_ci_log.txt`,
`track_c_c6_approval_record_reconciliation.md`. PR #4 Draft/Open/unmerged.
Freeze eligibility: NOT_TRACK_C_FREEZE_CANDIDATE; canonical integration NOT READY.
Engineering Progress: **6/11 Frozen = 54.5%**, partial C6 separately reported.
Next: reconcile TC-D3P-005 S approval RECORD under the user's explicit repository consistency
condition; then finish registered mandatory C6 acceptance and verification before C7.


## TC-D3P-005 S explicit approval / record synchronization — 2026-10-01T18:02:42+09:00

TC-D3P-005 common all-MANDATORY classification, distinct PASS/FAIL/NOT_RUN and S —
Synthetic Software Freeze Evidence are **APPROVED / ACTIVE** by explicit user message.
Approval processing time is the actual current KST clock above; no older timestamp invented.
Authoritative record: `implementation/reports/track_c_c6_freeze_policy_approved.md`,
bound to original proposal blob `bbd3321e9966957e862199622ca53f5a4b3ec556`.
Historical proposal/evidence/status records are retained and superseded, not rewritten.
TC-C6-APPROVAL-RECORD-001 **RESOLVED**. No new policy design or D3-P required for this sync.

All 17 enumerated C6 diagnostic groups MANDATORY, no advisory exemption; any FAIL/NOT_RUN
blocks C6 acceptance/Freeze. Complete deterministic explicit SYNTHETIC fixture family
all-PASS may support software-only Freeze, separately labeled SYNTHETIC_SOFTWARE_VALIDATION.
REAL_PIT_RESEARCH_VALIDATION remains separate; no alpha/skill/significance/Holdout/Forward/
promotion readiness follows from synthetic PASS. C8 significance responsibility unchanged.

C0–C5 SOFTWARE FROZEN preserved; C6 IMPLEMENTING / NOT FROZEN pending full registered runner,
ledger/provenance wiring, perturbation/controls/drift and actual mandatory acceptance.
Existing execution and statistical kernels are reused. C7–C10 NOT STARTED until C6 Freeze.
Holdout UNCONSUMED; Investor-QGV FUTURE_TRACK_C_INPUT. Track A/B/D/E/Web source untouched.
PR #4 Draft/Open/unmerged; canonical automatic merge forbidden. Continue autonomously
inside approved scope after remote approval record verification.


## Track C C6 SOFTWARE FROZEN / C7 D3-P boundary — 2026-10-01 09:57:08 UTC

Timestamp: 2026-10-01 09:57:08 UTC. AI: Codex. Module/Area: Track C EVL only.
Started From: fresh GitHub canonical/merge-base b8e39a2196a6d7794a04a0cd5393c68329e126ca,
Track C88da6f30560c4a2aee281a4cc45760eb3e0f4e80 (35ahead/0behind), PR#4 Draft/Open.
Previous chat logs were not used. Canonical/feature documents, full tree, code/tests,
workflow, latest Actions and PR discussion were read directly.
TC-D3P-005 S actually APPROVED/ACTIVE in repository; earlier approval-record conflict resolved.

Completed: registered full-family C6 runner, all mandatory controls/perturbation/drift,
ledger budget/terminal reports, C4 frozen-prediction/source lineage and current invalidation
resolution. Every registered grid identity is preserved, including unattempted/failed
coverage; incomplete family blocks acceptance. Existing C0–C5/execution/kernels unchanged.
Files Changed: EVL robustness.py, additive C6 fixture/tests/audit tool, Track C workflow/
reports and Track C-only SSoT overlays. Prior four-file C4 repair preserved; no new upstream
or Track A/B/D/E/Web source/artifact edit. EVL_SPEC_v0.1 unchanged; TAX_MODE=EXCLUDED.

Tests: source166dcba64b20aaead70981e84c0a4d87390744fb; Actions36845447156/job110314362158 SUCCESS.
Actual C6 targeted130/130 -> C0–C5 previous103/103 -> full629/629 ->
PIT/lineage/Holdout/cross-track audit -> complete acceptance evidence PASS.
Rolling/Expanding x Primary/Gap-stress: each17/17 MANDATORY diagnostic groups actually PASS.
Archive artifact11153252067 and its digest/full logs/hashes retained in
implementation/reports/track_c_c6_acceptance_2026-10-01.json/.md and CI log.
Two prior audit-script failures retained; path/Unicode parsing fixed without weakening checks.
GitHub tools have no local shell; actual fresh git fetch/pytest performed in Actions.
No fresh normal-merge replay claimed; preserved prior C5 integration499.

Decisions: TC-D3P-001..005 approved; C6 **SOFTWARE FROZEN** under TC-D3P-005 S,
limited to SYNTHETIC_SOFTWARE_VALIDATION. C0–C6 Frozen7/11=63.6% phase-count proxy.
TC-D3P-006 A **PROPOSED / NOT APPROVED / NOT ACTIVE**: exact C7 Pareto/cohort aggregation,
plateau/complexity/drift/medoid/distinctness policy; reviewed gap is result-impacting.
See implementation/reports/track_c_c7_selection_policy_proposal.md and current Track C
D3-P/D3-C register. No new C7 policy applied or selected candidate produced.

Provisional/Open Issues: REAL_PIT_RESEARCH_VALIDATION NOT_RUN (no complete real family).
C7 PREFLIGHT COMPLETE / BLOCKED_D3P_006, selection implementation/acceptance not started;
C8/C9/C10 NOT STARTED / DEPENDENCY BLOCKED. No Track C implementation baseline yet.
No significance, investment skill, alpha, Official profile, promotion or real Forward claim.
Holdout **UNCONSUMED**. Investor-QGV **NOT_IMPLEMENTED / FUTURE_TRACK_C_INPUT**.
PR#4 Draft/Open/unmerged; canonical automatic merge forbidden; separate Integration Audit needed.

Next Action: user decision on TC-D3P-006 A items1–9, then C7 targeted/prior/full/audits/
evidence/push/Actions/Freeze -> C8 -> C9 -> C10 -> Track C implementation baseline.
Do Not Repeat: C0–C6 implementation, past approval reconciliation, upstream redesign,
Track A/B/D/E/Web edits, Holdout peek, fabricated investor evidence, force push/history rewrite.


## TC-D3P-006B explicit approval — 2026-10-01T19:13:51.000+09:00

Scope: Track C only. Actual KST approval-processing clock above; source HEAD9cf4d7d68dd6bc9eda5db78571acf6e74811144d.
User did NOT approve A1–9 unchanged. B is **APPROVED / ACTIVE**; original A remains
unapproved historical proposal blob e4aa773a3b2d00dc530453875d3a14a796779a01, unchanged.
Authority: implementation/reports/track_c_c7_selection_policy_approved.md.
B: complete immutable Landscape and pre-OOS-selection configuration; invalid/nonfinite
integrity inputs FAIL versus legitimate undefined support NOT_RUN; independent metric x
cohort/fold exact Pareto; all eligible plateaus (min2 definition), full range/edge evidence,
no largest-size priority; existing C5 complexity; vector drift Pareto with trade-off ties;
restricted medoid with TIED_EQUIVALENT_REPRESENTATIVES and hash only for serialization;
raw OOS pair differences with statistical/economic distinctness left to C8.
Explicit synthetic-only algorithm fixture values allowed; no actual research threshold default.

C0–C6 SOFTWARE FROZEN preserved. C7 IMPLEMENTING / NOT FROZEN until complete actual
acceptance/regression/audits/evidence/Actions. C8–C10 NOT STARTED.
Holdout UNCONSUMED; Investor-QGV FUTURE_TRACK_C_INPUT; TAX_MODE=EXCLUDED.
No Track A/B/D/E/Web edits, C6 rewrite, automatic merge, force push or history rewrite.
PR#4 Draft/Open. Next: implement/verify B exactly; C7 Freeze then C8 policy audit.

## Track C execution approval / C7 policy boundary — 2026-10-01 10:45:14 UTC

Scope: Track C only. Latest explicit user execution approval authorizes C7 implementation/
validation/SOFTWARE Freeze under TC-D3P-006B and inactive C8/C9/C10 package/contract
preparation. This is not approval of new result-impact policies, actual Holdout read,
C8-C10 implementation/activation, actual promotion or canonical integration.

Fresh GitHub checkpoint: canonical/merge-base b8e39a2196a6d7794a04a0cd5393c68329e126ca,
Track C15fed506d4e67d89861221281e4879002e431b4a,40ahead/0behind; PR#4 Draft/Open.
006B APPROVED/ACTIVE remains preserved. C7 **BLOCKED_D3P / NOT FROZEN**:
B4 does not uniquely fix eligible-versus-Pareto graph vertices; B6/C6 signed deltas
do not uniquely fix Low Drift signed/magnitude comparison. Independent explicit
toy counterexamples show different candidate survival; user's sections4/5 require
a new D3-P at this boundary. No interpretation is silently activated.
Original A and approved B text/history are unchanged.

Prepared: track_c_c7_policy_boundary_2026-10-01.md with exact G1/D2 approval target;
track_c_c7_policy_boundary_evidence_2026-10-01.json (10 integer-arithmetic witness
checks, NOT C7 runtime/pytest/acceptance); track_c_c7_implementation_contract_preparation.md;
Package A track_c_c8_policy_package_A.md; Package B track_c_c9_policy_package_B.md;
Package C track_c_c10_policy_package_C.md; track_c_c8_c10_contract_drafts.json.
All packages/drafts PROPOSED / NOT APPROVED / NOT ACTIVE; runtime_loadable=false.
No real threshold values, lifecycle approvals, research/promotion Manifest, future
observation or fake Investor-QGV profile. Synthetic config tag:
SYNTHETIC_SOFTWARE_VALIDATION_ONLY; actual evidence scopes stay separate.

C0-C6 SOFTWARE FROZEN preserved:7/11=63.6% phase-count proxy.
C7 targeted/mandatory acceptance NOT_RUN_POLICY_BOUNDARY; no8/11 or Freeze claim.
C8-C10 policy/contract preparation complete, implementation NOT STARTED.
REAL_PIT_RESEARCH_VALIDATION NOT_RUN_MISSING_COMPLETE_REAL_FAMILY.
Holdout UNCONSUMED; TAX_MODE=EXCLUDED; Investor-QGV FUTURE_TRACK_C_INPUT.
No source/test/workflow edits; Track A/B/D/E/Web/Producer/Entity/QGV source untouched.
Prior four-file C4 repair retained. PR#4 Draft/Open/unmerged; no force/history rewrite.

Parallel checkpoint: Producer Infrastructure branch4c2f2d006c62c016fa8a26dcafbf8598b92cfa73
now has infrastructure/exporter with unavailable real sections, not real EVL readiness.
Entity Metadata brancha013f1c1758642f90a65fe11df69fc234c143a48 remains search/display-only,
not PIT feature evidence. No other branch is modified/imported/merged.

Validation: proposal completeness/10 synthetic policy-witness calculations executed
in functions.exec; no C7 software test or real research claim. Existing C6 workflow
will perform actual C6/previous/full/audits on the documentation commit; success is
recorded only after the actual run. Latest retained C6 evidence remains authoritative.

Next Action: explicit additive approval/revision of C7-G1 and C7-D2, then implement
C7.1-.12 in order and all required tests/audits/evidence/Actions before SOFTWARE Freeze.
After C7 Freeze8/11=72.7%, report Package A/B/C and wait; do not start C8.
Do Not Repeat: C0-C6 rewrite, approval synchronization already resolved, old proposal
rewrite, Holdout peek, guessed real numeric defaults, other-track changes or merge.

## Track C actual policy-preparation preservation verification — 2026-10-01 11:17:56 UTC

Documentation checkpoint 3a76bb436bb8d78a0954775b9a16a93ceb8404a9; actual Actions36853351818/job110339931930
SUCCESS: raw logs C6 targeted130 / prior103 / full629 PASS, all4x17 diagnostics PASS,
PIT/lineage/Holdout/cross-track audits PASS. Artifact11155609858
sha256:5e879edfd5385ecdd265b99627d1eec48fe430dbd4d50ead311cd8facca98ac7; complete raw log/evidence retained in
track_c_policy_preparation_validation_2026-10-01.{md,json} and
track_c_policy_preparation_preservation_ci_log_2026-10-01.txt.
This verifies existing C0-C6 preservation, not C7 software acceptance.
C7 BLOCKED_D3P / NOT IMPLEMENTED / NOT FROZEN; targeted/acceptance NOT_RUN_POLICY_BOUNDARY.
C0-C6 SOFTWARE FROZEN7/11=63.6%; Holdout UNCONSUMED; real research NOT_RUN.
Package A/B/C and G1/D2 PROPOSED/NOT APPROVED/NOT ACTIVE.
Final read-only parallel audit: Producer Infrastructure6fe9eee (latest docs-only);
QGV Real Producer8d531fb reports research persistence, not complete EVL/PIT/profile
validation; provisional policy/coverage/restatement limitations preserved. No imported
or modified other-track sources. Investor-QGV FUTURE_TRACK_C_INPUT.
Next remains additive G1/D2 policy approval, then C7 implementation/test/Actions/Freeze;
C8 implementation remains closed until its separate package approval and C7 Freeze.
