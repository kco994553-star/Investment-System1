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
Source: `Investment-System1 · PERSONAL_INVESTMENT_LAYER_V1_HANDOFF.md` (additive, Architecture FROZEN, Implementation NOT
STARTED). Checked against code at commit 71976ed. Nothing below is resolved by guess; the Personal Layer (PIL) is not
implemented and no PIL code was added.

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
