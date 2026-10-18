# 기능 대응표 — 기존 코드·계약·화면·신규 백엔드 (2026-10-18)

[PRODUCT_FRONTEND_REDESIGN_20261018](PRODUCT_FRONTEND_REDESIGN_20261018.md) §3에 따른 조사 결과다. 기준 커밋 228e2ea0(#295). 읽기 전용 조사이며 코드 변경은 없다. 상태: R=기존 구현 재사용 가능, C=연결·표시 개선 필요, N=신규 구현 필요, W=자료·방법론 결정·검증 대기. 문서 존재·함수 존재·합성 시험·실데이터 검증·화면 연결·게시 확인은 서로 다른 상태다.

조사 원문은 영어로 남긴다(파일·함수 경로 대조용). 요약은 결정 기록과 인수인계에 한국어로 적는다.

---

# Map A — QGV engine · presets · two-level weights · leaderboard · radar · 13F · Lab

Base: `origin/claude/investment-system-top500-validation-alrugm` @ **228e2ea0bce560c994b91216744ff9f8ce6395cc** (#295, 2026-10-17 22:42 KST). This is the same commit the atlas used. Paths are under `implementation/src/investment_system/` unless they start with `implementation/` or a root doc name. Read-only investigation.
Newer unmerged branch: `origin/claude/product-redesign-doc` (283cc939, 2026-10-18 01:44 UTC). It saves the 10-18 directive and adds a "결정됨 2026-10-18" block to USER_DECISIONS_PENDING. It changes no code.

Evidence levels: **D** doc exists · **F** function exists · **T** synthetic test passes · **R** real-data verified · **W** wired into an operating screen · **P** confirmed published.

## Table

| 기능 | 기존 생산자/계산 코드 | 입력·출력 계약 | 현재 소비 화면 | 검증 근거 | 부족한 연결 | 신규 설계·백엔드 | 선행 조건·owner |
|---|---|---|---|---|---|---|---|
| **1a QGV v2 Q·G factor/axis engine** — 기존 구현 재사용 가능 | `qgv/v2_factors.py:1298 compute` (raw metrics, `CALC_VERSION` :38 = `qgv2-calc/2026-10-17.1`). `qgv/v2_scoring.py:118 score_rows` (sub-metric percentiles → factor = mean → axis = renormalized weighted mean, coverage < 50% → NA :230). Publishing: `universe/sec_qgv2.py:336 publish`. Strict validator recomputes every score: `sec_qgv2.py:505`, JS `sec-qgv2.js:106-144`, tolerance 1e-9 | Published `sec-qgv2.json` rows carry `metrics` (raw), `factors` (10 Q/G percentiles, unrounded floats), and `axes{Q,G}` {score, factors_available, available_weight, peer_basis, peer_count, submetric_fallbacks, reason_codes}. Weights: Q 25/20/20/20/15, G 25/25/20/15/15 (`v2_scoring.py:26-29`) | S04/S05/S06 through `QgvScores` | T: `tests/test_qgv_v2.py`, `sec_qgv2_vectors_v1.json`. P: run 38996553263 published Q 485 / G 493 / both 477 of 504 (CURRENT_HANDOFF:38-40) | Raw sub-metric **values** and sub-metric percentiles are not shown. The UI lists sub-metric names only (`company-screen.js:106`) | Drill-down: raw value → percentile → factor → inner weight → contribution | Owner of `claude/withdrawn-peer` (calc `2026-10-17.2`, local, not pushed; CURRENT_HANDOFF:66) touches the same files |
| **1b Device V + composite + gate** — 기존 구현 재사용 가능 | `qgv/qgv_v2.py` (Python reference) ⇄ `web_assets/qgv-v2.js` (device). V factors `_metrics` :197; cross-sections `_cross` :307; composite `score_universe` :346; gate :402 (Q industry percentile ≤ 30 drops V; the total's 50% test still counts V's weight :409-416) | Input: companies {factors, qg_axes, v_inputs, memberships, industry_group, cik, in_cross_section} plus quotes {price, currency, month_closes} (RAM). Output per code: axes, factors (PUBLIC / CALCULATED / NA + reason), weights, total, flags, q_industry_percentile | `qgv-scores.js:60-68 universeScores` → S04/S05/S06/report | T: `qgv_v2_vectors_v1.json` 7 cases, Python==JS (`tools/qgv_v2_node_test.js`). W: yes. R/P: V is device-only and is never published (correct by design) | — | — | Prices stay in RAM; nothing goes to a public file (`qgv-scores.js:1-8`) |
| **1c Company types / TYPE-SCOPE** — 기존 구현 재사용 가능 (effect is small) | `qgv_v2.py:98 type_axis_weights`, `:147 pricefree_memberships`, `:165 composite_weights` (preset × type / fallback). Config `qgv/type_config_v1.json` / `type-config-defaults.js`. `TYPE_SCOPE = qgv2-type-scope/2026-10-17.1` | Only the growth ramp on `revenue_cagr_3y` 0.10→0.20 evaluates. All other types are null | S04 type chips; S13 types editor (device copy) | T + W. R: 499/504 rows end up at the 34/33/33 fallback (`docs/company_types/TYPE_SCOPE_20261017.md:43`) | value / quality / cyclical / defensive / dividend / leader rules are unresolved | — | Type rule approvals (owner) |
| **1d Missing / withdrawn / version** — 기존 구현 재사용 가능 | `qgv2-inputs.js:26 versionMismatch`, `:60-72 withdrawal` (IDENTITY_CONFLICT_WITHDRAWN plus same-CIK codes), UNI-TARGET price conflict `qgv-scores.js:33-42`. Coverage and reasons `qgv-scores.js:116-144 coverageFor`. Explore groups `:147` | Missing is null, never 0. Per-axis status READY / PARTIAL / NOT_AVAILABLE / NOT_APPLICABLE / STOPPED. Original weights and renormalized shares (`share` :123) | S04/S05 coverage panels (`company-screen.js:93-110`), S06 explore filter | T (browser tests). W: #292 / #294 | The 'STALE' state is shown. There is no "unit under review" or "refresh failed" per-row field (`qgv-scores.js:69-73`) | — | — |
| **1e Personal profile / weight layers** — 기존 구현에 연결·표시 개선 필요 (it is **v1 only**) | `device-profiles.js` S13: v1 leaf weights (`profile-defaults.js` = v1 7/6/7 factor names), `weights()` :9, `previewRanks` :126 through `engine-preview.js:20 strategy` (v1) on `sec-qg-factors.json` (v1 factors). Schema `device-profile-drafts/1`. S13 v2 panel `activeV2View` :36-46 is **display only**. Leaderboard "내 프로필" view = v1 preview (`leaderboard-screen.js:50-51`, `app.js:665`). Track B `personal/weights.py` (hierarchical tree, sibling-sum, overrides, namespaces) has **no QGV caller** (`docs/qgv_common_contract_vnext/AUDIT.md` H2) | v1 drafts {Q:{7}, G:{6}, V:{7}}, each axis sums to 100 | S13, S06 profile tab (labelled "v1 미리보기 · 공식 v2 점수 아님") | T (v1). W as v1 preview | **No v2 inner-weight path exists.** `qgv_v2.axis_score` and `qgvV2.axisScore` read the constant `WEIGHTS[axis]`. `score_universe` accepts only a preset id and throws `PRESET_INVALID` on anything else (`qgv-v2.js:110`) | v2 two-level profile schema (/2), engine parameter, editor, compare view | See lane B below |
| **2 Presets** — 자료 확보·방법론 결정·검증 대기 (공격/균형/수비 numbers) | (i) v2 axis presets `qgv_v2.py:28-34` / `qgv-v2.js:15-16`: balanced 34/33/33 '균형', quality 50/25/25 '우량 중심', growth 30/50/20 '성장 친화', value 25/20/55 '가치(관문 켬)'. Source `docs/qgv_scoring_standard/QGV_V2_CANDIDATE.md` §5. Gate is a separate toggle (§4). (ii) `contracts/strategy.py:85-118` `StrategyStyle` Defensive / Balanced / Aggressive / Custom builtin packs (PROVISIONAL): cash 0.15/0.05/0.00, risk_mult 0.70/1.00/1.30, TA lookback 30/14/8, signal 0.70/0.55/0.45, macro sens 0.80/0.60/0.40, deadband 0.75/0.50/0.25. **q_weights and g_weights are FROZEN_KEYS** (:28-34). (iii) EVL_SPEC_v0.1 §9 Aggressive / Balanced / Defensive = integrated-profile **objectives** (CAGR vs MDD/Sortino…), owned by Track C | (i) axis weights only, applied with type weights on top. (ii) non-QGV parameters. (iii) metric objectives, no weights | (i) S06 preset chips (`leaderboard-screen.js:47-49`), S13 list. (ii) legacy v1 paths only: `render_app.py:100`, `qgv/us_live.py:135`, `validation/e2e.py:55`, `historical.py:152` (BALANCED). (iii) none. Lab setup select 균형/공격/방어 is disabled (`screen-detail.js:42`) | (i) T, W. (ii) T (`tests/test_product_strategy_validation.py`). (iii) D. Track C code exists only on unmerged branches | No QGV-weight definition of 공격/균형/수비 exists anywhere | Preset contract: purpose, axis + 15 inner weights, gate, safety conditions, expected tilt, limits, validation status | Owner decision on numbers. Lab validation |
| **3 Two-level weight recompute** — 신규 구현 필요 (the engine pieces are reusable) | `_published_axis` `qgv_v2.py:335-343` / `publishedAxis` `qgv-v2.js:105-106` | When a row has a `qg_axes` dict (every real `sec-qgv2.json` row: `qgv2-inputs.js:48`, `qgv-scores.js:66`), Q and G **always** take the published score. Factor scores feed only the coverage fields. **A changed inner weight would be ignored** | — | Measured with `score_rows` on a synthetic 300-row universe (Py 3.13): recompute from published factors equals the published axis in 446/585 cases and differs in 139 by ≤ 1.42e-14. Cause: `v2_scoring.py:233` uses builtin `sum` (compensated in Py ≥ 3.12; publish CI uses 3.12, `sec-daily-public-inputs.yml:61`). `qgv_v2`/JS use a plain loop. No NA mismatch | Recompute path. Gate cross-section on the recomputed Q. Custom axis weights in place of the preset. Coverage shares (`qgv-scores.js:117`) bound to the effective weights | See lane B | — |
| **4 Leaderboard** — 기존 구현에 연결·표시 개선 필요 | Order: `qgv-scores.js:175` total desc, tie **ticker asc**, NA unranked. `app.js:634 rankOrder`: NA last by ticker. Sorts `app.js:612` `LEADER_SORTS=['qgv','ticker','name','favorites']`, options `app.js:385-389`. Other sorts `watchlist.js:5`. PC header sort `table-sort.js` (≥ 1024px, parses **display text**, NA last, stable, cycles asc→desc→original). M3 cap rank `private-subset.js:177`: effective_cap desc, tie **company_id asc** | Scope: rank over the **19 identities** (`leaderboard-screen.js:92`, `identityCompanies` `app.js:1147`). Percentile cross-section = all 504 + TARGET records. M3 = device private-sheet verified subset | S06; S15 watchlist uses the same filter fn | W; browser tests `leaderboard_profile_screens_browser_test.js` | No structured sort for Q/G/V, market cap, return, safety margin or as-of. Phones have no column sort (dropdown only). Filters: interest, group, text, explore only (no SIC, type, score, cap, freshness or earnings). Per-company 1D/5D/20D **does not exist**: only spec §19 (`QGV Leaderboard · Specification v1.0.md:130`), the 'daily' UNCONNECTED column (`leaderboard-screen.js:13`), and ledger-level periods in `report-benchmarks.js:11` | Sort-key model (number, direction, NA last) shared by PC and mobile. Return-period contract (trading days, adjusted or not, dividends) | Price-period definition (owner, for 60D/1Y) |
| **5 Radar n-gon** — 신규 구현 필요 | No radar or spider code (searched). Pieces: `virtual_trading_compare.py:14,113-126` / `virtual-trading-compare.js:59` (√252 vol and MDD for **ledgers**). `macro-lights.js:228` (index drawdown from 52w high, rv20). `playbook-engine.js:319 e4Level` (drawdown vs 3y MDD; inputs not wired). `chart-indicators.js` (SMA/EMA/RSI/MACD/Boll/ATR only). `private-history.js` (OHLCV incl. volume, on click). `price-store.js:113-117` (daily and month-end closes from the user's sheet). Published non-price candidate: `revenue_volatility_5y_rank_pct` (`v2_scoring.py:156`) | — | — | F only (none for per-company vol/MDD/beta/liquidity) | Per-company price series selection (PriceStore / Worker / private-history). Beta and liquidity (ADV) formulas do not exist | Axis contract: formula, window, direction (risk ≠ good), normalization (peer percentile within SIC group, min peers 8), min history, NA rule, peer set and count. Device-only (prices) | Owner choice of extra axes and windows |
| **6a 13F operating** — 기존 구현 재사용 가능 | Parser and two-quarter compare `providers/sec_13f.py:313 parse_information_table`, `:389 compare_quarters`. Collector `providers/sec_13f_managers.py:149 verify_manager`, `:182 select_quarters` (latest two), `:370 collect_managers`. Full long-SH projection `product/thirteenf_details.py:24 project_details`. Step `tools/sec_13f_managers.py`, run daily by `.github/workflows/sec-daily-public-inputs.yml:135`. 10 managers / 8 styles `config/manager_styles_v0.json` | `sec-13f-changes.json`: reported quantities, kinds NEW/ADD/REDUCE/EXIT, `details.{previous,current}.reported_holdings` (cusip, issuer names, quantity, SEC-unit value) | S16 (`thirteenf-quarter.js`), playbook E4 evidence (`thirteenf_quarter.py:126`, PLAYBOOK_V1 §13-8) | T: `test_sec_13f*.py`, node / browser tests. W. P: included in the daily deploy (per CURRENT_HANDOFF the W-F1 order includes 13F). File not re-read here | CUSIP→company only for TARGET via catalog ISIN (`thirteenf_quarter.py:64`, Eaton via N-PORT). **No CUSIP→Universe504 map** | — | — |
| **6b Track C / Investor-QGV** — 자료 확보·방법론 결정·검증 대기 | **Not on canonical.** EVL code `implementation/src/investment_system/evl/*` (C0–C8 partial) lives on `origin/feature/track-c-evl` (ff78c4f6, 54 commits) and `origin/codex/track-c-gsup-v2-2026-10-03` / `origin/codex/fpia-execution-coverage-2026-10-05` (7215a9f6). Reusable kernels `evl/statistical_kernels.py`: PSR, expected max Sharpe, DSR, CSCV-PBO, circular block bootstrap, Reality Check. Also `splits.py` (annual walk-forward, purge), `pit.py PITGuard`, `ledger.py TrialLedger` (append-only), `experiments.py`. Report `implementation/reports/investor_qgv_implementation_baseline.md` (branch `origin/ccr-22e3ff16-p7n5k5`) | EVL search is bound to **cash_buffer / technical_lookback** only (TC-D3P-002; `evl/bindings.py`). Investor weight search "requires a separate additive contract". Profiles Aggressive / Balanced / Defensive selection over a candidate landscape (`evl/selection_contracts.py:10`) | none | T on those branches only (synthetic). Investor-QGV = **NOT_IMPLEMENTED / FUTURE_TRACK_C_INPUT**: no ProfileConfig, no Research Spec v1.0 saved, no 13F pipeline (`track_c_c6_independent_validation_2026-09-30.md:175-183`) | Methodology assumed: v1-era (EVL bindings call v1 `integration/technical/macro` engines; QGV core treated as an immutable input). Adapter: v2 factor panel → candidate weights → selection set → behavioral scorer (holding similarity) plus return metrics, with C2 splits / C1 ledger reused | Missing: multi-year manager×quarter holdings panel, 13F-HR/A lineage, filing acceptance time, PIT CUSIP / share-class map, PIT universe, PIT 15 factors (PR #286 `research/pit_filings.py`: public time, as-filed SIC from FSDS, `qg_raw_metrics_as_of`, `cross_section_as_of`; `docs/backtest/FSDS_SAMPLE_20261017.md` 2 quarters only), prices / corporate actions / delistings (paid source undecided, `BACKTEST_DATA_AUDIT.md:26`), weight search, evaluation registry | Owner: merge or port the EVL kernels (separate PR). Data purchase. Objective function. PLAYBOOK §13-8 says 13F does not change scores, so this stays research only |
| **7 Lab** — 기존 구현에 연결·표시 개선 필요 (registry = doc only) | `implementation/docs/backtest/BACKTEST_RESEARCH_PLAN.md` §3: 24 IDs = A0-10/15/20, A/B/C/D × N (READY_TO_PREPARE), E (BLOCKED_ON_DATA), F/G (BLOCKED_ON_RULE). Primary contrasts P1–P4, R1. §5 B = axes 1/3, **C = inner factors equal, recomputed from factor scores**, D = no V. S28 "A 동등성" (exact). Forward ledger `validation/forward_ledger.py` (v1 + `forward_validation/v2` Q/G only, TARGET v0, start 2026-10-19). `validation/backtest.py` is a toy (do not reuse) | — | `forward-validation.js`, Lab setup stub `screen-detail.js:36-46` (disabled) | D; PIT adapter T (`test_research_pit_filings.py`) | No registry or trial-ledger code on canonical (`§7` "실험 등록부·시도 기록 … 새로 필요") | Register 공격/균형/수비 and 13F candidates as **new IDs** outside the 24 (the §3 "후속 후보" list is the slot), each with N and trial count, separate forward arrays | BT-1..17 decisions (owner) |

## 2. Preset sources compared (do not treat them as equal)

| Source | Names | What the numbers control | Status |
|---|---|---|---|
| `QGV_V2_CANDIDATE.md` §5, `qgv_v2.py:28-34` | 균형 / 우량 중심 / 성장 친화 / 가치(관문 켬) | Q/G/V **axis** weights only. Inner weights fixed. Type weights on top. Gate separate (default on) | Came in with the v2 candidate adopted as default (GSQ-022/023 approve v2 itself, USER_DECISIONS_PENDING:382). No separate preset-number decision was found. PROVISIONAL, UNCALIBRATED. Running on the device |
| `contracts/strategy.py`, `contracts/enums.py:85-89`, `PRODUCT_ARCHITECTURE.md:31-36`, COCKPIT_IA A18 | Defensive / Balanced / Aggressive / Custom | cash buffer, risk multiplier, TA lookback, signal threshold, macro sensitivity, deadband. **Excludes Q/G weights by contract** | PROVISIONAL placeholders. Used only in v1 legacy paths |
| `EVL_SPEC_v0.1` §9 (root doc), Track C branches | Aggressive / Balanced / Defensive | Performance objectives with hard constraints (excess CAGR vs MDD / downside / Sortino) | DESIGN FROZEN. Code unmerged. Holdout unconsumed |
| `versions.py:5` `v1.5-balanced`, Architecture v1.0 §7 | "QGV Standard v1.5 균형형" | Legacy 150-point standard label | No numbers in the repo |
| `type_config_v1.json` `defensive` | 경기방어 (company type) | Type weights 45/20/35 | Rule unresolved. A company type, not a user preset |
| `screen-detail.js:42`, `DESIGN_CANVAS_SCREENS_v1.md:153` | 균형·공격·방어 (Lab experiment select) | none | Disabled stub |

Not decided for 공격/균형/수비: axis weights, 15 inner weights, gate default, safety conditions (minimum coverage, Q floor), whether type weights apply, the link to cash, TA or macro (the directive says not to extend it), the risk claim, and the validation plan.

## 3. Lane B minimal first implementation

1. Python `qgv/qgv_v2.py`: add `weights=None` to `score_universe`. `None` keeps the current path untouched.
   - The weight tree is `{axes:{Q,G,V}, factors:{Q:{5},G:{5},V:{5}}}`. Validate integers 0–100. Each axis's factor weights sum to 100, and the axes sum to 100.
   - `axis_score(scores, axis, weights=WEIGHTS[axis])`.
   - For each of Q and G: if the inner weights equal `WEIGHTS[axis]`, use `_published_axis`. Otherwise call `axis_score(qg[i], axis, inner)` and drop the published score.
   - `q_pct` is recomputed over every pooled row from the effective Q, so the gate is re-evaluated.
   - `composite_weights(tree.axes, type, fallback)` replaces `PRESETS[preset]`.
   - `profile.id = 'qgv-v2/custom/' + sha256(tree)[:12] + '/gate-on|off'` and `namespace = 'PERSONAL_PREVIEW'`.
2. JS `web_assets/qgv-v2.js`: the same `scoreUniverse(..., {weights})`. `qgv-scores.js compute({..., weights})` gets its own memo key and returns the result under `personal`, never `primary`. `axisCoverage` uses the effective weights.
3. `device-profiles.js`: schema `device-profile-drafts/2` holds the v2 tree. /1 v1 drafts stay readable and are labelled v1. No storage of scores.
4. Tests:
   - **E1 (exact):** for every case in `qgv_v2_vectors_v1.json`, including `published-axes`, `score_universe(..., weights=official_tree(preset))` deep-equals `score_universe(..., preset=preset)` apart from `profile`. Check this in Python and in JS, and check Python == JS for the new vectors file.
   - **E2 (recompute consistency):** take a universe whose `qg_axes` come from `v2_scoring.score_rows`. With the recompute path forced at official weights:
     - NA pattern identical
     - |ΔQ|, |ΔG| ≤ 1e-9 (observed ≤ 1.5e-14)
     - gate flags identical
     - |Δtotal| ≤ 1e-9
     - rank order identical (ties by ticker)
   - **E3:** changing one inner weight changes Q only for rows where that factor is present and the axis is not NA, and moves the gate only through `q_pct`. The official result object is unchanged (memo isolation).
   - **E4:** all existing vectors and node tests pass unchanged.

## 4. Owner decisions

1. Coverage rule under custom inner weights.
   - (a) 50% of the custom weights
   - (b) 50% of the official weights
   - Recommendation: (a). It is the same rule applied to the profile the user chose. Show the original-weight fill rate next to it (directive 4.1).
2. Zero weight.
   - (a) The factor is excluded and is not missing
   - (b) Disallowed
   - Recommendation: (a), with the axis sum required > 0.
3. Type weights on personal axis weights.
   - (a) Apply them as on presets (GSQ-017)
   - (b) Personal weights are final
   - Recommendation: (a) by default with a visible toggle. Today 499/504 rows are at the fallback, so the effect is small.
4. At the official weights, exact published reuse versus always recompute.
   - Recommendation: reuse. Bitwise equality is impossible otherwise (Py ≥ 3.12 compensated `sum`).
5. 공격/균형/수비 numbers. Leave them undecided. Lab registers candidate sets with new IDs. Do not rename the current 4 presets.
6. Radar extra axes and windows. Choose from volatility, MDD, liquidity (ADV) and beta, or the non-price revenue-volatility rank.
7. Track C EVL kernels. Port them as a research-only module with v2 adapters, or keep them on their branches.


---

# Map B: TA / Macro / News·Relations / Portfolio·Report / Prompt / Personalization / Ontology / IA

Basis: `origin/claude/investment-system-top500-validation-alrugm` = **228e2ea0bce560c994b91216744ff9f8ce6395cc** (merge #295, 2026-10-17 22:42 KST). Read-only. Paths are relative to `implementation/`. WA = `src/investment_system/product/web_assets/`.
Evidence levels: DOC = document only · FN = function exists · SYN = synthetic/unit test · REAL = real-data verified · SCREEN = wired to a route · PUB = in the Pages build/workflow.
Status: R = 기존 구현 재사용 가능 · C = 기존 구현에 연결·표시 개선 필요 · N = 신규 구현 필요 · W = 자료 확보·방법론 결정·검증 대기.

## 1. Technical analysis

| 기능 | 기존 생산자/계산 코드 | 입력·출력 계약 | 현재 소비 화면 | 검증 근거 | 부족한 연결 | 신규 설계·백엔드 | 선행 조건·owner | 상태 |
|---|---|---|---|---|---|---|---|---|
| Indicators SMA5/20/60/120(+240), EMA20, RSI14, MACD12/26/9, Boll20/2, ATR14 | WA/chart-indicators.js:32-52 (`ResearchIndicators.calculate`); Py mirror `technical/research_display.py` | daily bars ≤1500, COMPLETE only, `RAW_CLOSE`/`PROVIDER_ADJUSTED_CLOSE`; out role `RESEARCH_DISPLAY_ONLY`, `pit_status NOT_VERIFIED`; ATR only on RAW (:27) | #technical, #company (via PrivateHistory) | FN+SYN (`tests/test_technical_research_display.py`, vectors `docs/technical_live_data/PYTHON_REFERENCE_VECTORS.md`); not REAL-PIT | weekly variants (G3 undecided); parameter "sensitivity" UI | none for daily | — | R |
| Chart renderer | WA/technical-chart.js:12-24 (fixed 640×240 SVG candles, overlays, AVG line, B/S markers) | bars+indicators+selected set | #technical, #company | FN; browser tests `tools/technical_macro_validation_browser_test.js` | no volume pane, zoom/pan/crosshair/measure, keyboard, weekly | LWC adapter (design P1-7/P1-8) | TA start conditions | C (fallback stays per Q6) |
| Daily bars (Worker) | WA/private-history.js:150-167 load, :20-50 `validateHistory`; worker/src/index.js:59 ranges, :159/:315 `interval=1d` | `private-history/1`, 1mo–5y, RAW_CLOSE, RAM only, click-to-load, Google token + Worker email allowlist (worker:291) | #technical (symbol select :217-223), #company | FN+SYN; real Worker deployed (private-history-deploy.yml) | **19 TARGET symbols only** (:9); no request dedupe/RAM cache (P1-11) | symbol-scope resolver (held+TARGET+watch), shared queue | G2; P1-11 | C |
| Weekly bars | none (Worker returns 1d only) | — | — | — | — | `chart-bars.js` + `technical/chart_bars.py` W1 rule (design §7.4, P1-1) | start approval | N |
| 6 cards | WA/technical-cards.js:7-14 | latest value per indicator; Model mode always NA (:45-47) | #technical | FN; browser test | Trend/Momentum/Volatility = **approved GSQ-015 research display**; Volume, Relative strength, Structure = "승인된 정의 없음" (:10-12) | pattern card replaces Structure NA (P1-10) | volume/RS definitions = owner methodology | R (3) / W (3) |
| Canon sections (regime, QGV context, scenarios) | WA/technical-cards.js:80-91 | static NA text | #technical | — | no definitions | — | methodology | W |
| TradingView widgets | WA/tradingview-widgets.js:7,34,49,75 | iframe, default OFF, per-device toggle | #technical (advanced), #company (mini), #brief (ticker tape) | FN | kept separate from pattern chart (TA_PREP §1) | — | — | R (display-only) |
| LWC experiment | experiments/chart-contract-v0.1/ (LWC 5.2.1, synthetic 12 bars; app.js:4 `attributionLogo:true`) | isolated | none | SYN + width evidence | network-record test missing; logo must be false (Q5) | P1-7 vendoring | start approval | R as reference only |
| Pattern engine/history (pivots, S/R zones, box break, double top/bottom incl. FAILED/INVALIDATED/EXPIRED) | none in code | design `docs/technical_chart/TECHNICAL_PATTERN_CHART_V1_DESIGN.md` §8-9, cases `docs/technical/TA_PREP_STATUS_20261017.md` §6 | — | DOC only | — | P1-2..P1-6 | conditions §10: 1/6 met; Q7 separate approval; gaps G1-G3 | W |
| Drawing / notes on chart | **no chart note storage**. Only playbook record `memo`/thesis (WA/playbook-screen.js:18, localStorage `investment.web.v1.playbook`) | — | #playbook | FN | anchor to symbol/interval/basis/time-price absent | user-assumption layer P2-3; storage location "different from official" (design §11.4) not decided for user drawings | owner: where user drawings live | N + W |
| Corporate-action handling | none (Worker has no split/dividend fields) | design §7.3: `PRICE_BASIS_CONTINUITY_UNCONFIRMED`, `CORPORATE_ACTION_IN_WINDOW` | — | DOC | — | P1-W Worker PR | G1 provider/field; Worker deploy approval | W |
| Start conditions | TA_PREP §10 | (1) 7 consecutive runs from 10/19 ✗ (2) Q/G≥454 ✓ (3) 10-co recheck ✗ (4) ledger/calc ✗ (5) TARGET v1 ✗ (6) owner approval ✗ | — | — | — | — | Main/owner | W |

## 2. Macro

| 기능 | 기존 생산자/계산 코드 | 입력·출력 계약 | 현재 소비 화면 | 검증 근거 | 부족한 연결 | 신규 설계·백엔드 | 선행 조건·owner | 상태 |
|---|---|---|---|---|---|---|---|---|
| 8 axes × 6 dims grid | `macro/primary_contract.py:14` DIMENSIONS; `macro/primary_input.py:172-190`; JS WA/public-screens.js:7,110-111 | `macro-screen.json`: 48 cells; only `Level` may be `RAW_EVIDENCE`; FX always NA; `regime:null` | #macro `#public-macro` | FN+SYN; PUB (daily `public_screens_pipeline.py --macro-v0`, sec-daily-public-inputs.yml:83) | Direction/Momentum/Surprise/Stress/Confidence all NA by contract | — | methodology (regime mapping) | R (Level) / W (other 5 dims) |
| Growth/Inflation v0 | `macro/growth_inflation_v0.py` (BEA A191RL, BLS CPI YoY) → `MacroEngine` v0.1.1 thresholds (`macro/engine.py:16-44`) | UNCALIBRATED | #macro (ScreenDetail WA/screen-detail.js:15) | FN+SYN+PUB | regime NA | — | — | R |
| Remaining 6 axes raw | `macro/raw_axes_v0.py:32-73` (Labor, MonPol, Liquidity, Credit, Fiscal; FX excluded) | raw display only, no state | #macro | FN+SYN+PUB | — | — | regime deferred (2026-10-11) | R |
| 5 risk lights | WA/macro-lights.js:9-15 CONFIG; Py `macro/macro_lights_v1.py`, `macro_lights_public.py` | employment/inflation/curve public; market (SPY) + credit (HYG/IEF) device RAM via Worker | #macro `#macro-lights-root` (app.js:878) | FN+SYN (`tests/test_macro_lights_v1.py`)+PUB (3/5 LIVE) | device lights need Worker load | — | — | R |
| Reference mode (#260) | WA/macro-lights.js:241; `playbook-config-defaults.js` `gate_active:false` | no expansion block / no U3 | #macro, playbook | merged 1049627e | — | — | M-REENABLE after replay | R |
| Replay / M-RULE C (#262) | **open PR #262** (touches macro-lights.js, playbook-config-defaults.js) — not in 228e2ea0 | M-RULE C = hypothesis; out-of-sample replay | — | — | device replay results | — | owner merge review + device replay; **lane E must not edit macro-lights.js** | W |
| Equity-market state / regime history / signal→evidence / scenarios | WA/screen-detail.js:18-26 static NA cards | — | #macro | — | inputs absent | — | — | W |
| Cycle position (economy, equity), SIC industry cycle / rotation | **none**. Only SIC `cyclical_defensive_candidate` labels, membership NOT_AVAILABLE (`qgv/sic_industry_groups_v0.json:11-19`) | — | — | — | — | new model (hypothesis/미산출 until validated) | owner methodology + data | N + W |
| User position notes vs system | none | — | — | — | — | new storage (per-browser first) | personalization decision | N |

## 3. News / disclosures / relations

| 기능 | 기존 생산자/계산 코드 | 입력·출력 계약 | 현재 소비 화면 | 검증 근거 | 부족한 연결 | 신규 설계·백엔드 | 선행 조건·owner | 상태 |
|---|---|---|---|---|---|---|---|---|
| News signals (GDELT + IR) | `product/news_signals.py` (classes EARNINGS/PRODUCT/MA/LEGAL/OTHER :41, NEW/REPEAT, RELATED_TO_8K, 72h grouping); `tools/news_signals.py`; JS WA/news-signals.js | `news-signals.json` titles+links only, `score_effect:NONE`, TARGET companies only (:83) | #news `#news-disclosures`, #watchlist (app.js:395-398, 918-931) | FN+SYN (`tests/test_news_signals.py`)+PUB (sec-daily-public-inputs.yml:147, continue-on-error; GDELT 429 seen) | no 5-line summary/Q-G hypothesis fields; 30-row list (sec-disclosures.js:81-88) | — | **NEWS-CAP** pending | C |
| SEC 8-K disclosures | `product/sec_disclosures.py`; WA/sec-disclosures.js (90-day window) | `sec-disclosures.json`, channel DISCLOSURE '공시·확정' | same list (merged timeline) | FN+SYN+PUB | 8-K pushed out by news (NEWS-CAP) | — | NEWS-CAP | C |
| DART disclosures | `product/dart_public.py`; WA/dart-disclosures.js | `dart-disclosures.json` (hanmi) | #news, #watchlist | FN+SYN+PUB | — | — | — | R |
| Legacy `D.news` list | app.js:674-681 `paintNews` (3-tier: portfolio→interest→other) | `data.json.news` — adapter `NO_UPSTREAM` (`producers/adapters.py:23,39`) | #news `#news-list` | — | **always empty on Pages** | — | — | C (retire or feed) |
| RIG P0 model | `rig/model.py` (SourceKind :62, EpistemicStatus FACT/SUPPORTED_INFERENCE/UNVERIFIED_SIGNAL :69, RelationshipType SUPPLY_CHAIN/CUSTOMER/COMPETITOR/VALUE_CHAIN :86, EdgeDirection :96, IdentityRef :108), `rig/gate.py`, `rig/ledger.py` | C-39 issuer/security/listing refs via `IdentityLookup` protocol (gate.py:43); no own registry | none | FN+SYN (`tests/test_rig_p0..p4*.py`) | no producer feeding real events/relations; no identity adapter from Universe | data source + producer | owner: relation data source | W |
| RIG P1 news/network views, dedup | `rig/network/views.py:25-29` NewsStatus NEW/UPDATE/FOLLOW_UP/DUPLICATE (NEW = no link), EventPresentation 1-3 lines; `rig/network/render.py` static page | same ids for News and Network views | `network.html` iframe only if `D.relationships.data` (app.js:510) | FN+SYN; `tools/rig_browser_smoke.js` (not in CI) | **Pages build never passes `rig_page`** → network.html deleted (web_mvp.py:116-120); demo only (`tools/build_web_mvp_demo.py`) | vocabulary bridge NEW/REPEAT ↔ NEW/UPDATE/FOLLOW_UP/DUPLICATE | — | C (not wired) |
| RIG P2 intel | `rig/intel/intel.py:32-50` Materiality LOW..CRITICAL, RelationshipStatus NEW/DISCOVERED/STRENGTHENED/STABLE/WEAKENED/ENDED, DealState :52 | append-only observations | none | FN+SYN | — | — | — | C |
| Priority order (보유→관심→직접 연결→조사 후보→기타→시장) | `rig/myview/scope.py:45-54` FeedTier HELD_IMPORTANT, INTEREST_IMPORTANT, MY_HIGH_MATERIALITY_ONE_HOP, RESEARCH_PRIORITY_NEW, MY_OTHER, MARKET; `feed_order` :197-199 (tier, then P1 recency = newest first) | needs Materiality per relation | none | FN+SYN | "important" requires materiality — GDELT items have none | — | owner: importance rule for public feed | W |
| Single watchlist / groups | `rig/myview/prefs.py` (one ★ list, append-only); web WA/watchlist.js + `investment.web.v1.personal` | — | #watchlist | FN | rig prefs not connected to web prefs (same concept, two impls) | adapter only | — | C |
| Impact path | `rig/discovery/impact.py:20` MAX_HOPS=3, default 2; Hop EXPOSURE/DOWNSTREAM/UPSTREAM/PEER :88-93; `event_impact`/`concept_impact` :143-154; ConceptKind MACRO_DRIVER/TECHNOLOGY/VALUE_CHAIN_STAGE | derived on demand, "potential", not stored | none | FN+SYN | premises/lag/counter-path/falsifier fields absent | extend path record (no new graph) | owner naming "영향 경로" | C + N |
| NEWS-CAP | `docs/USER_DECISIONS_PENDING.md:17` | 8-K minimum vs newest-30 | — | — | — | — | owner | W |

## 4. Portfolio & reports

| 기능 | 기존 생산자/계산 코드 | 입력·출력 계약 | 현재 소비 화면 | 검증 근거 | 부족한 연결 | 신규 설계·백엔드 | 선행 조건·owner | 상태 |
|---|---|---|---|---|---|---|---|---|
| MODEL | app.js:546-552 (always NA "실데이터 QGV 연결 전") | — | #model | — | no model generator | — | methodology | W |
| TARGET | `product/device_actual_catalog.py` → `actual-catalog.json` (TARGET v0, 19) | target_units | #model, #portfolio, reports | PUB | TARGET v1 (#248→#263) | — | owner/TARGET v1 | C |
| ACTUAL | WA/device-actual.js (IndexedDB :187), `DeviceActual.ramView` | device only | #actual, #portfolio, report REAL | FN+browser tests | — | — | — | R |
| PAPER sets / shadow | WA/virtual-trading.js:7 LEDGER_KINDS SET_A..D + SHADOW; runner, ledger sheet (`virtual-ledger-sheets.js`, user's sheet) | "규칙대로 했다면" virtual | #report/mock, #report/real, #portfolio card (portfolio-screen.js:21-30) | FN+SYN (`tests/test_virtual_trading*.py`) | start date D-13 undecided → NOT_STARTED | — | owner start date | R |
| Portfolio screen | WA/portfolio-screen.js:13-19 (TARGET v0 facts, SIC v0, theme concentration >40%) | ACTUAL from RAM only | #portfolio | browser tests | model/user/paper side-by-side compare absent | — | — | C |
| Daily report, 13 areas | WA/daily-report.js:135-180 template v1: 요약, ①장부 ②구성 ③전 종목 ④기여 ⑤QGV ⑥기술 ⑦거시 ⑧뉴스·경쟁·산업 ⑨Driver/시나리오 ⑩행동요령·가상장부 ⑪누적검증 ⑫기간별 ⑬성과·위험 — matches owner list | export text + screen | #report/mock, #report/real (app.js:682,693-) | FN + `tools/daily_report_browser_test.js` | screen shows only summary+③⑩⑪⑫⑬ (:310-327); ②④⑥⑦⑨ hard-coded N/A (:142,148,154,155,157) | — | data wiring (SIC, TA, macro) | C |
| Weekly report | **none** (no code; "weekly" only in playbook config) | — | — | — | — | aggregation spec (period change, contribution, open items) | owner spec | N |
| Impossible → missing inputs → copyable prompt | partial: reason codes (virtual-trading.js:262-351 labels) and full-template export with N/A | — | report | — | no "minimum missing inputs" list + dedicated prompt | small wrapper over existing codes | — | N (small) |
| Amount hiding | daily-report.js:34-39 single `money()` (default hidden), HIDE_KEY | screen ●●● / export [숨김] or % of limit | report | FN+tests | — | — | — | R |
| Export | daily-report `renderTemplate` → clipboard; device backup (`device-backup.js`, schema /4) | user copy only | report, settings | FN+tests | — | — | — | R |
| AI answer paste | daily-report.js:192-209 `checkAnswer` (foreign numbers, format, version, date) + `saveAnswer` (localStorage, 30 max); mailbox via user sheet | stored as AI text only; never changes holdings/ledger | report | FN | **saved first, check shown after** (no review-before-save step); playbook has review-then-user-verdict (playbook-screen.js:52,65) | — | — | C |

## 5. Prompt library

| 기능 | 기존 생산자/계산 코드 | 입력·출력 계약 | 현재 소비 화면 | 검증 근거 | 부족한 연결 | 신규 설계·백엔드 | 선행 조건·owner | 상태 |
|---|---|---|---|---|---|---|---|---|
| Official catalog | `prompt_library/catalog.py:24-60` (PLV1_CONTENT_V1.0, FROZEN md pinned by sha256 f0a6ed90…; 70 ACTIVE: FUNDAMENTAL 21, TECHNICAL 14, DISCOVERY 13, MACRO 13, CROSS_VALIDATION 9; 10 bundles; scope vars :40-46; system input vars :48-58) | variables, roles, migrations | #research → `research.html` iframe (app.js:512-514; built web_mvp.py:87,114) | FN+SYN (`tests/test_prompt_library_v1.py`)+PUB | no NEWS / PORTFOLIO / BACKTEST domains | adding prompts = changing FROZEN catalog | owner | R / W (new domains) |
| Fill / checks / search | `prompt_library/fill.py`, `validation.py`, `search.py`; UI `prompt_library/ui.py:128-209` (domain/role/scope/starter/bundle filters, plvCheck, copy) | ready-to-copy gate | #research | FN+SYN | current company/period not passed from app | — | — | C |
| Favorites / personal copies | **none** | — | — | — | — | per-browser store (localStorage) | personalization decision | N |
| Prompt text outside the catalog | WA/playbook-screen.js:41 `prompt()` (PLAYBOOK §10); WA/daily-report.js:18-19 GUIDE_A/HEADER_B | — | #playbook, report | FN | de-facto second prompt sources | register as catalog entries (no 2nd catalog) | owner | C |

## 6. Personalization / auth

| 기능 | 기존 생산자/계산 코드 | 입력·출력 계약 | 현재 소비 화면 | 검증 근거 | 부족한 연결 | 신규 설계·백엔드 | 선행 조건·owner | 상태 |
|---|---|---|---|---|---|---|---|---|
| Google sign-in | WA/google-sheet-quotes.js:9,57,104-107,175 (GIS token client, `drive.file`+`email`) | token in RAM; user's own sheet only | settings, report mailbox, trades, price store | FN+tests | it is **Sheets/Worker access, not an app account** | — | — | R (as-is) |
| Worker auth | worker/src/index.js:275-293 tokeninfo; `aud` = client id and `email == ALLOWED_EMAIL` | single owner | private history | REAL deployed | single-user only | — | — | R |
| Browser-profile storage | ~20 `investment.web.v1.*` localStorage keys (personal, settings, theme, recent-search, playbook, profile-drafts, report-ai-answers, …) + IndexedDB ACTUAL | per browser profile/origin | all | FN | UI text must say "this browser profile" | — | — | R |
| Backup/restore | WA/device-backup.js (schema /4, prices excluded, 16MiB) | file export/import | #settings (app.js:895-897) | FN + `tools/device_backup_node_test.js` | — | — | — | R |
| "로그인 계정의 명시적 설정" | **none** (no account store, sync, conflict/merge, isolation) | — | — | — | — | new backend + import-conflict UX | owner: store choice | N + W |

## 7. System tree / ontology

| 기능 | 기존 생산자/계산 코드 | 입력·출력 계약 | 현재 소비 화면 | 검증 근거 | 부족한 연결 | 신규 설계·백엔드 | 선행 조건·owner | 상태 |
|---|---|---|---|---|---|---|---|---|
| Issuer/Security/Listing | `contracts/global_universe.py:62,77,93` (C-39) | issuer_id→security_id→listing | rig only | SYN | web uses `company_id` slugs (19 TARGET, `product/entity_catalog.py:36-53`), Universe uses `EXCHANGE:SYMBOL` (`universe/universe_codes_v1.json`) + CIK (`universe/sec_qgv2.py:71`) | one identifier link table (company↔security↔filing↔event↔relation↔score↔portfolio↔experiment) | — | N (doc) |
| Second relation registry? | **none** — rig consumes `IdentityLookup` (rig/gate.py:43), "no RIG-owned identity universe" (rig/model.py:3-6) | — | — | — | adapter from Universe504 identities to IdentityLookup missing | — | — | R (good) |
| Classifications | SIC group v0 `qgv/sic_industry_groups_v0.json`; theme v0 `qgv/theme_membership`; company types `type-config-defaults.js`; public sidecar `product/public_classification.py` | separate files, no forced hierarchy | #portfolio, company, #types | FN+PUB | cyclical/defensive membership NA | — | — | R |
| System tree / "how it's made" | QGV hub status cards app.js:521-545; ScreenDetail canon | — | #qgv | — | no tree | new content page | — | N |

## 8. Home / IA after #295 → owner's 8 menus

Current: app.js:836 routes; app-shell.js:11-17 tabs (홈·기업 탐색·내 투자·시장·뉴스·기록), :19-25 더보기. Parent-row/flow labels app.js:596-605, 881-887.

| Existing route | Current tab | New home |
|---|---|---|
| #home | 홈 | Home (search) — reuse home-screen.js, home-quotes.js, recent search |
| #companies, #leaderboard(/interest), #watchlist, #types, #profiles, #qgv | 기업 탐색 / 내 투자 | 1 QGV (#profiles = weight editor; #qgv hub content → 7) |
| #company/<id>, #analysis/<id>/<tab> | 기업 탐색 | shared "통합 분석" from search (QGV primary) |
| #entity/<id> | 기업 탐색 | INDUSTRY → 1/7, MACRO → 3, INVESTOR → 8 |
| #technical (+#technical-chart/state/execution/record) | 시장·뉴스 | 2 기술적 분석 |
| #macro | 시장·뉴스 | 3 매크로 |
| #news/<id> | 시장·뉴스 | 4 뉴스·공시·기업 관계 |
| #portfolio, #actual, #model, #playbook, #brief, #report/mock, #report/real | 내 투자 / 기록 | 5 포트폴리오 (reports inside) |
| #research | 기록 | 6 프롬프트 라이브러리 |
| (none) | — | 7 투자시스템 안내·구조 (new) |
| #validation (+-paper/backtest/forward/track/trials), #thirteenf | 기록 / 시장·뉴스 | 8 Lab |
| #settings | header tool | header tool (personalization) |

## Shared-file hazards
- Every WA file is SHA-pinned in `tools/pages_artifact_guard.py` (e.g. :61 daily-report, :73 technical-cards, :126 news-signals, :128 macro-lights); new files need index.html script tag + guard entry → Main-owned.
- Open PRs: #262 (macro-lights.js, playbook-config-defaults.js), #248/#263 (index.html, device-actual, playbook-screen, guard).

## Parallel lanes — smallest safe next step (no new methodology, no engine/schema change)

| Lane | Smallest safe next implementation | Files it would own (no app.js) | Blockers needing owner decision (options → recommendation · reason) |
|---|---|---|---|
| A design/shell | Remap app-shell.js TABS/MORE to Home + 8 menus (route→menu table above; phone bottom bar = 홈·QGV·포트폴리오·뉴스·전체, rest in 전체 메뉴); monochrome tokens light/dark + reduced-motion; replace sea/lighthouse home SVGs with neutral sketch texture; keep home-quotes/recent search | WA/app-shell.js, theme.css, style.css, pc-layout.css, theme-boot.js, home-screen.js, home-bg-*.svg (+ build_pages_cockpit.py HOME_BACKGROUNDS) | App.js parent-row/FLOW labels (app.js:596-605) still say "← QGV/검증": Main folds a one-line follow-up. No owner decision needed (directive already fixes IA/design) |
| D TA | Docs only: close G1-G3 (split-event source & field; out-of-19 watch/held path; "phase 1 = no weekly indicators"), add contracts for `chart-bars/1`, `pattern-rules/1`, and a new `chart-annotation/1` (user lines/zones/notes anchored to symbol·interval·price basis·time/price; separate from official history) | docs/technical_chart/*, docs/technical/* | (1) Start approval — keep waiting (conditions 1/6). (2) User-drawing storage: a) browser localStorage now, b) user's private sheet append-only tab like Q2, c) RAM only → **b**, matches Q2 and survives devices; a as fallback when not signed in. (3) Volume/RS card definitions: a) define now, b) leave NA → **b** until pattern P1 lands |
| E macro/news/relations | news-signals.js display-only filters (channel 공시/뉴스, class 실적/제품/M&A/법률/기타, NEW vs REPEAT) with state kept across #news↔#watchlist; user-vocabulary labels ("기업 관계 · 미연결" instead of Track D/RIG) via a new news-screen module Main swaps in; docs: "영향 경로" path record (premise, lag, counter-path, offset, falsifier) on top of rig/discovery/impact.py, and cycle-position as hypothesis/미산출 | WA/news-signals.js, WA/sec-disclosures.js (list only), new WA/news-screen.js, docs/news/* | (1) NEWS-CAP: a) 8-K minimum quota, b) newest 30 → **a** (confirmed disclosures must not vanish). (2) Public-feed importance for the 6-tier order: a) use rig Materiality (no producer yet), b) tier by 보유/관심/기타/시장 only and mark "중요도 미산출" → **b** now, a later. (3) Relation data source for rig producer → defer; no screen claim. Do **not** touch macro-lights.js until #262 resolves |
| F portfolio/report/prompt/personalization | (1) "보고 불가" card in daily report: reason codes → minimum missing inputs → copyable prompt (target, period, versions, available/missing data, sources, computable range); (2) review-before-save for pasted AI answer (run `checkAnswer` before `saveAnswer`, user confirms); (3) prompt favorites + personal copies in research page, per browser profile, official text read-only | WA/daily-report.js, prompt_library/ui.py, WA/research-bridge.js | (1) Account settings store: a) user's own Google sheet "Settings" tab via existing drive.file, b) new Worker+KV/D1 per account, c) none yet → **a** (no new server data, same boundary as ledger/trades), label as browser-profile until built. (2) Weekly report spec (aggregation rules) → owner approve outline. (3) NEWS/PORTFOLIO/BACKTEST prompt domains require editing the FROZEN catalog → new catalog version, owner approval. Avoid index.html/device-actual/playbook-screen while #248/#263 open |
