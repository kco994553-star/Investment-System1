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

- [x] Red tests: common-label invariance vs sector pools, strict core/additional,
  19/20, issuer duplication, invalid mapping/date/hash, gate independence,
  exact thirds, scoped ranking, 0/negative/null, save/replay, CLI and delivery.
- [x] Extend existing preview core with explicit research execution policy; same
  calculator/percentile/aggregate/ranking, old entry default byte-compatible.
- [x] Add research dual config/validation, exact-source admission, projections,
  per-row scope, dual comparisons and stage coverage/overlapping missing causes.
- [x] Existing CLI dual-study path, pinned inputs/config, saved replay, bounded
  views and manifest. Main synthetic first handoff/Draft before real execution.
- [x] Reuse retained baselines, run3 frozen candidates for operating504 and held1057,
  independently reconcile source preservation, scopes, new/lost/common, n/N.
- [x] Review changed code; private preserve/readback; Main precise SHA/contract;
  CI and actual reader/browser/adoption states separately.

Review focus: common scopes must truly pool; evaluation overlap cannot replace
raw data; core default unknowns stay in denominator; scopes cannot hide missing
issuer/classification records; exact replay cannot silently use latest input.

Implementation/real comparison: TESTED. Integration/deployment/live: NOT_STARTED.

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

## Retained-real comparison (2026-11-04)

No new raw factor was calculated or source collected. All input observations are
retained. Financial cutoff2026-11-04T02:29:35.166580Z; classification knowledge
2026-11-08T08:05:49.349866+00:00, explicitly retrospective, not historical system PIT.

| Evaluation | Candidate/baseline | Q | G | V / joint / total |
|---|---|---:|---:|---:|
| operating504 rows /501 issuers | #527 retained default |232|343|0|
| same | #528 retained nine-group reference |242|359|0|
| same | S1 sector reduced |250|397|0|
| same | U1 common ROA/change |390|408|0|
| same | U2 common ROA/sales |390|373|0|
| held1057 issuers | #527 retained default (source8004 pools) |494|693|0|
| same | S1 sector reduced |515|793|0|
| same | U1 common ROA/change |804|810|0|
| same | U2 common ROA/sales |804|724|0|

Counts in this table equal unique issuers, but original evaluation code-row and
issuer denominators remain separate. S1 versus retained: operating Q+8/G+38,
unique gaining46, lost0, common-score changes Q242/G352. Held Q+21/G+100,
unique121, lost0, common-score changes Q494/G688. Do not sum shared issuers across
operating and held populations. U2 versus U1 G: operating gained10/lost45/common
changed363; held gained26/lost112/common changed698. U1 versus S1 is a whole-model
change: operating Q gained145/lost5; held gained299/lost10. No total valid/rank or
performance comparison is available, so the common-total-only comparison is an
explicit empty set alongside the full original population comparison.

Candidate source input586 rows (original504 plus82 admitted previously) for
operating; actual active reference union504 issuers across all valid factors.
Held uses original8004 catalog as candidate source; actual active factor union844.
Neither candidate-source count is an eligible full-market denominator. Each factor
has its own valid N/member hash. Q/G correlations and sector composition are
private diagnostics, not additional optimization or performance claims.

Full core joint input/raw/score coverage is0 for each candidate due to V inputs.
That does **not** mean all raw Q/G observations are absent: selected-factor raw
and score counts are reported individually. Common candidate selection denominator
is every original evaluation member, including unresolved classifications.
95% requires476/501 issuers (or479/504 code rows), and1005/1057 held issuers.
Current joint/total0 in both scopes; those are the respective shortfalls.
The whole-market denominator and coverage remain null.

Conditional limits have been recomputed, not copied from old436/501. With existing
confirmed classification/representative/reference membership fixed, optimistic
input-completion ceilings for U1/U2/S1 are399/355/410 of501 and821/712/825 of1057.
If unresolved classifications/representatives are additionally assumed solvable,
known structural-only upper bounds are478/434/489 and1034/925/1038 respectively.
These are **different assumptions**, not forecasts or promised recoveries. U2's
known common-formula incompatibility already prevents95% within either current
scope; more price data alone cannot fix that. U1 retains23 equity-REIT Q
incompatibilities; S1 retains small accounting-specific groups and common-equity
input shortages. No winning model/default is selected on coverage alone.

### Verification and delivery

Initial independent reconciliation: source raw preservation51,687 observations,
40,796 factor scores independently checked against reference ordering; 4,683
company-model detail projections matched. After the common-core denominator fix,
accepted six runs retain exactly the same numerical outputs (238,833 factor
records and32,781 row numerical fields checked), reusing the independent arithmetic
proof rather than repeating it. All original rows and official-gate outcomes match.

Bounded authenticated output: operating24 files, held48 files (excluding manifests),
maximum1,754,749 bytes. Index→detail matches every original target; raw financial
values are omitted from reader detail, preserved in full private results. Manifest
SHA256 identifies actual bytes; result_hash is the Python canonical result identity,
not a browser reserialization instruction. Source/config/classification/input and
reference identities accompany each board. Core_raw/core_scores mean **all core
factors jointly valid**, not any-factor availability. Cause counts overlap.

State: implementation TESTED; retained-real candidate comparison TESTED;
Main INTEGRATED/DEPLOYED/LIVE_VERIFIED NOT_STARTED. No API compatibility or
out-of-sample strategy performance test in this work. #528 final CI7success/2skipped
was queried, not rerun. #529 current CI is reported separately in its PR/handoff.

### Independent blocked queues / next data

No new financial/V input was delivered. Existing verified TTM diluted EPS and
same11/04 common-class BPS/price/action basis are required for U1/U2; selecting B/P
for general companies creates a broader capital-input requirement, not evidence
that it is already available. S1 retains EPS, CFO/all-common-class market cap,
and equity-REIT Nareit FFO requirements by variant. Missing capital/ADR/action
components are not zero;11/02 finance prices cannot fill11/04. WRB approved filing
execution/receipt remains Main's independent queue. Existing source-specific
minimum acquisition proposals remain pending; this work adds no download request.

Keep all three research candidates, flag U2's known applicability limit, and do
not promote any to a default until missing V and economic comparability have
been evaluated. A future stability variant/expanded ROA accounting scope needs
an explicit definition/comparison; existing variants were not broadened here.

## 2026-11-11 Main #530 changed-boundary handoff

Consumer head `9d1129d223dcd7a73605d1e17736f3d334673cab`: Codex independently
exercised the new Bridge model route (previous missing-model-ID fallback now
`MODEL_ID_REQUIRED`), three explicit candidate contexts/previews, separate3-row
evaluation/20-row reference, QG_ONLY, save/exact replay, incompatible saved schema,
and missing-original-input rejection. Published synthetic result hashes match;
original snapshots and saved descriptor remain unchanged. Real results were not
recalculated. Node checked both original operating504/held1057 indices and one
23-row detail shard per scope, date mismatch rejection and display limit preserving
stored rows. This is direct Python/Node acceptance, not browser/live deployment.

### Main question1: held1057 input lineage

Evaluation hash `d10961f48f4e8d0911062bd5277fecd6d8a538f5a8c9af76050bf564595c4e40`
is the existing8,004-row source input
`91f3726c1a4c54538049f7d577be4f2ce41f6bdd364b61ba4d5d787ca0523804`
projected to the1,057 issuer IDs whose retained financial state is not NOT_AVAILABLE.
Rows are selected in source order, without changing any row value/classification.
Only rows, members, snapshot_id, universe_id and universe_version differ. The
preparation script is already preserved in the original private #529 archive.
`run_board` independently requires each evaluation row to equal its reference
source row. `bindings.evaluation` and `bindings.reference` retain both input hashes;
`reference_population.candidate_population` describes the source candidate set,
not an eligible whole market. New private `input-lineage.json` records this exact
projection/byte hashes; it is a lineage check, not another QGV run.

### Main question2: conditional detail fields

`missing_factors`, `nominal_axis_weights`, `nominal_effective_weights`,
`post_gate_axis_weights`, `post_gate_effective_weights` are emitted by aggregate()
when an applicable preset exists. They do NOT require a valid total. An unresolved
sector/accounting mapping bypasses aggregate(): the five fields are absent, axes/
total/pre_gate_total are null and gate_status is UNKNOWN. Do not replace absent
fields by empty arrays, zero weights, or a claim of no missing inputs.

Existing real data: each of these five fields is present on424/504 operating rows
and844/1057 held rows, absent on80/213 respectively (MAPPING_UNRESOLVED), in all
three candidates. These are reused result counts, not newly calculated axes.

### Main question3: exact synthetic delivery manifest

`dual-synthetic/delivery-manifest.json` uses the SAME existing
`qgv-dual-delivery-manifest/1` format (SYNTHETIC, operating504, path/size/sha256)
for original summary.json/index.json/detail-000.json bytes. The original seven-file
`dual-synthetic/manifest.json` and all original fixture bytes are unchanged, so the
bridge's existing input pin and stored result hashes remain valid. No duplicated
summary/index/detail fixture was created.

### Main question4: factor leader projection (new optional companion)

`research.dual_qgv_delivery.factor_leaders_artifacts` consumes hash-pinned existing
summary/index/detail files and projects the stored factor rank, score and decile.
It never calls run_board/preview, ranks scores, changes ties, or chooses new peers.
`top_n=20` is a display limit on existing ranks, not a portfolio selection rule.
The scorer's code-file list is unchanged; replay/config/result hashes stay valid.

Outputs:
- `factor-leaders.json`, schema qgv-dual-factor-leaders/1: original board contexts,
  source delivery manifest SHA, group→file index, effective evaluation N and
  reference valid N, plus counts of optional-detail field presence.
- `factor-leaders-NNN.json`, schema qgv-dual-factor-leaders-detail/1: each
  model×ranking_scope×variant, original rank unit EVALUATION_CODE_ROW, first20
  existing ranks and stored decile boundaries (first/last rank and unrounded score).
  N<10 retains SAMPLE_LT_10; no scores retains NO_VALID_SCORE. Zero-valid groups
  remain visible in the index. Reference N is never substituted for evaluation N.
- `factor-leaders-manifest.json`, schema qgv-dual-factor-leaders-manifest/1:
  source_delivery_manifest_sha256 plus path/size/sha256 for every new file.

The companion manifest pins the new projection and original delivery together.
Original delivery manifests/summary/index/detail files are not changed. Main's
current reader allows only summary/index/detail filenames; this companion needs
an explicit optional route/reader before use. Do not put it through the existing
strict delivery reader or silently widen its allowlist. Public synthetic counterpart:
`dual-factor-leaders-synthetic/`; all actual company outputs remain private.

Offline projection (existing data only; fresh output directory):

```sh
PYTHONPATH=implementation/src python -m investment_system.research.dual_qgv_delivery \
  --source-dir EXISTING_PRIVATE_DELIVERY --manifest-sha256 ORIGINAL_MANIFEST_SHA \
  --output-dir NEW_PRIVATE_PROJECTION --top-n 20
```

Files are bounded to1,800,000 bytes (Main2,000,000-byte limit retained). Existing
private delivery: operating1071 groups/139 with valid scores; held969/151. These
include all registered factor groups, not company coverage or new calculations.
Each scope needs three new files; measured maximum sizes1,471,953 and1,545,810bytes.
Raw factor values are never copied. Private-output CLI refuses Git checkouts.
Whole-market denominator/coverage remain null. Main owns authenticated retrieval,
Worker paths, display and browser verification; no deployment is performed here.
