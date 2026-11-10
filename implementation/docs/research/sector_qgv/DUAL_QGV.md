# Dual QGV research — fixed core v0

Owner attachments 2026-11-10 authorize research implementation, not operating
adoption. Spec: Dual_QGV_Evidence_and_Contract_20261110.md and
Codex_Dual_QGV_Queue_20261110.md. Base #528 2ca567b23a1a9119e0986f95ae10fe0001c89715;
canonical ab6a83c3be2276abdcf855c71c5f273926e2dcc4. Codex owns research engine,
CLI, tests and this contract; Main owns readers/auth/workflows/guards/DC.

## Preregistration (before new real calculations)

Study DUAL-QGV-20261110-01. Exactly three candidates, no return-selected tuning:

| ID/version | Core Q | Core G | Core V | Axis weights | Reference/scoring |
|---|---|---|---|---|---|
| unified-roa-core/0.1.0 (U1) | roa_ttm 100% | roa_improvement_3y 100% | ep_ttm_diluted 50%, common_bp 50% | Q:G:V=1:1:1 exactly | common eligible issuer factor pool |
| unified-sales-core/0.1.0 (U2) | same U1 | revenue_cagr_3y 100% | same U1 | same U1 | same common pool source |
| sector-reduced-core/0.1.0 (S1) | general: operating margin70/debt30; financial: ROA70/common equity/assets30; equity REIT: CFO/assets70/debt30 | general/financial: ROA improvement100; equity REIT: CFO/assets improvement100 | general: earnings/cash in original relative proportion; financial: original E/P60/B/P40; equity REIT: FFO62.5/CFO37.5 | original approved sector weights | sector × accounting × variant |

Every candidate is fixed for all its targets; no issuer-specific substitution.
Financial means BANK/INSURANCE/BROKER/MORTGAGE_REIT; ASSET_MANAGER retains
its existing general Q/G and financial V definition. S1 transfers removed Q
role budget to profitability, keeps financial capacity30; removed G budget goes
to profitability change; V retains the original ratio of its two retained roles.
Thus this is **core reduction plus declared internal budget redistribution**, not
an isolated zero-weight deletion. Axis weights are unchanged in S1. Removed
factors remain additional diagnostics with zero core weight.

U1 is a deliberately narrow profitability/change/book+earnings research control,
not a complete quality/safety model. It loses accounting-quality and leverage
roles, and absolute profitability across industries may be biased. U2 isolates
G definition substitution under the same common reference policy, and sales is
not applicable to all financial accounting models. Existing ROA scope excludes
EQUITY_REIT; no hidden CFO/ROE replacement or GENERAL relabeling. These limitations
must appear in coverage and economic applicability, even if coverage is worse.
Profit-stability remains PENDING_DEFINITION (metric/std/loss guard); common ROE
is financial-only in the retained dictionary and is not relabeled all-company.
Neither is silently added as a universal core element.

Baselines: #527 retained original; #528 retained 9-group treatment. Operating
504/501 uses the #528 composite input unchanged. Held1057 uses the retained8004
reference source and projects the held1057 issuer IDs; it does not change N to1057.
Three candidate configurations are identical between evaluation scopes. Retained
reference source is individually validated by factor; 8004 is a catalog, not an
eligible market universe. The whole-market denominator remains null.

S1 versus #528 isolates core composition/budget at fixed inputs/pools/gates.
U2 versus U1 isolates G variant under common references. U1 versus S1 is a whole
model comparison (normalization, weights and elements differ), not causal effect
of one element. Preserve A/B/C names from earlier studies; these use new IDs.

## Shared contract and Main interface

`qgv-dual-board/1`: model_id/version, config hash, core/additional selection,
normalization/minimum20/strict/gate/engine/classification versions, evaluation and
reference identity (id/version/members_hash/valuation_date/as_of/input_hash),
per-factor reference members hash/N, result hash. Original rows retain company_id,
issuer_id, security_id, scoring_representative and ranking_scope. Total ranking
is only inside the evaluation set; S1 scopes are sector+accounting, never stitched
into a global or cross-accounting sector rank. Reference-only rows cannot rank.

Q/G/V role budgets remain10000 units; unified axis budget uses three equal integer
units (1,1,1), not rounded3334/3333/3333. Existing official/default configs retain
10000-unit axes. Nominal and gate-effective weights are separate. UNKNOWN gate
keeps final total null; VALUE_EXCLUDED drops V contribution, not issuer admission,
with existing strict pre-gate prerequisites unchanged.

Additional factors reuse common raw validation and scoring; they never enter
core aggregate. Their missing values cannot affect totals. Individual-factor
rank is within original evaluation ranking_scope; deciles require10 valid
issuers, extremes floor(N/10), remaining D9..D2 front-loaded, stable code-row tie
break (issuer representatives only). This is issuer-factor research ranking, not
historical security/technical strategy eligibility. Filters only project rows.

Saved payload binds exact configuration, code, both input identities and result;
missing/changed original inputs reject replay. New input means new calculation.
Private delivery: bounded summary/index and per-company details <=2MB each,
byte SHA256 manifest. No automatic public/official file replacement. Main must
use supplied counts/weights/ranks, not aggregate itself.

## Evidence and differences

EPUB retained original: Drive file 1ZmzhcJONp4Wi2UDiMVLg5deBt7fiozaC,
modified2026-11-02T10:35:50.487Z, SHA256
019de18190d4e5e12c10871fbd7db8efac8f5ba5c8eacf812d43a9c4867e9921.
Read ops/ch08,14,15,17,18,19,24,25.html in this session. Books/real inputs private.
Chapter8 CF=NI+depreciation+other noncash; book FCF additionally subtracts capex,
dividends/preferred dividends. Neither equals our CFO or CFO-capex by default.
Ch14/15 composites use neutral50 for missing; ours strict has no imputation.
Ch15 supports multiple valuation perspectives, not two-factor optimality.
Ch17–19 warn high standalone growth/profitability is not sufficient; ch19 ROA/ROE
studies do not establish our TTM/mean-assets or FY3 change formula.
Ch24 studies separate historical sectors/quintiles, not our common dictionary,
minimum20 or equal QGV weights. Ch25 value+momentum is not our financial G.
All candidates are CONCEPT_REFERENCE_SYSTEM_VARIANT, no direct book replication.

The supplied evidence document cites QMJ (2019, online2018), MSCI June2017 p4,
Nareit FFO. Their original external pages were **not newly fetched** in this work;
source claims use owner-supplied evidence, not a fresh independent paper audit.
QMJ profitability/growth/safety informs roles, not exact deltaROA/strict recipe.
MSCI heterogeneous industry recipes cannot be called a uniform common core.
REIT GAAP earnings may be calculable but depreciation limits economic comparability.

Original design attachments SHA256: implementation
719e68b2297ab2bf4a4834c4ce6b33441494ec1c2615f7ed5a205ffa4b3faf6a;
catalog d3c865e8545ec5f2820f4647748714715f5814d6c3e676d687dda7a85fdbb586.
Their §5 initial configuration remains unchanged. Exact factor formula/period/
unit/direction/applicability/input/overlap/source metadata is reused from CATALOG,
and is emitted in the new candidate evidence catalog, not copied into a second registry.

## Implementation ledger / plan

Native implementation; user explicitly authorized these research starting values
and continuous execution. No repeated design/role approval. Existing isolated
worktree, ordinary research branch; no frontend/workflow/guard edits.

- [ ] Red tests: common-label invariance vs sector pools, strict core/additional,
  19/20, issuer duplication, invalid mapping/date/hash, gate independence,
  exact thirds, scoped ranking, 0/negative/null, save/replay, CLI and delivery.
- [ ] Extend existing preview core with explicit research execution policy; same
  calculator/percentile/aggregate/ranking, old entry default byte-compatible.
- [ ] Add research dual config/validation, exact-source admission, projections,
  per-row scope, dual comparisons and stage coverage/overlapping missing causes.
- [ ] Existing CLI dual-study path, pinned inputs/config, saved replay, bounded
  views and manifest. Main synthetic first handoff/Draft before real execution.
- [ ] Reuse retained baselines, run3 frozen candidates for operating504 and held1057,
  independently reconcile source preservation, scopes, new/lost/common, n/N.
- [ ] Review changed code; private preserve/readback; Main precise SHA/contract;
  CI and actual reader/browser/adoption states separately.

Review focus: common scopes must truly pool; evaluation overlap cannot replace
raw data; core default unknowns stay in denominator; scopes cannot hide missing
issuer/classification records; exact replay cannot silently use latest input.

Implementation/real comparison: IN_PROGRESS. Integration/deployment/live: NOT_STARTED.

### Review rulings before real execution

Fresh review found evaluation-own classification context missing and shared
qgv_v2.py omitted from exact-code replay. Both have failing-then-passing regression
cases. Knowledge timestamps now parse timezone-aware and cannot exceed the
preregistration cutoff2026-11-10T12:03:13Z. They may exceed the financial cutoff
only as explicitly labeled RETROSPECTIVE_RECONSTRUCTION; the retained11/08
classification is not rewritten into11/04 system possession. The reviewer’s
suggested financial-cutoff comparison would reject this authorized retrospective
study, so the separate research cutoff is used instead. Active reference members
and source candidate population now have separate identities/counts. Common
preset metadata has no misleading IT/GENERAL label. These are validation/metadata
fixes before the first real candidate execution, not result-selected tuning.

Current adapter29 tests plus98 affected regression tests:127 passed. Full CI
is separate. Existing branch/official snapshots remain reproducible; no baseline
real calculation was rerun.

A final denominator counterexample showed unclassified common-model targets had
an empty selected-factor list inherited from the sector adapter. The common core
is now selected for **all** evaluation rows; unresolved classification still
blocks scores, but cannot shrink the selected-factor diagnostic denominator.
The new counterexample failed then passed; adapter suite30 passed. Earlier127
related checks are retained (shared core unchanged by this metadata-only fix).
First-run arithmetic is preserved; accepted outputs are regenerated for the new
code binding and checked for identical raw values/scores/axes/ranks. No gain is
counted twice.
