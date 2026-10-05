# Target Theme implementation paths and fresh FPIA dependency v0.4

Status: **READ_ONLY_PREIMPLEMENTATION_EVIDENCE / NOT_IMPLEMENTATION_READY**. This additive record keeps the 81 Core / 24 Extended / 8 Research scope and all previous evidence/history. No package/protected source, owner branch, grant, Frozen record or canonical state is changed. No GitHub comment/review/message is sent.

## 1. Fresh baseline and evidence limits

GitHub was fresh-read during this checkpoint; assessment capture receipt is 2026-10-04T23:54:36Z. Raw connector response envelopes are preserved under `raw/`; the two large directory-tree lookup envelopes are losslessly stored as `.json.gz` with original byte hashes in `GOVERNANCE_ARTIFACT_MANIFEST.json`. Decoded exact-SHA upstream source text is under `source-excerpts/`. Directory lookup is used only to locate the existing owner/runtime paths; it does not expand the requirement inventory.

| Subject | Fresh observation | Meaning |
|---|---|---|
| PR #42 | Draft/open; head `523e702a806a718d163cfbf62aa3fc29d8c3ef3c`; base `acaf1b5a82859ac2750a130ebe88f8b4d272ac66` | Head remains the same as v0.3's reference; this is a fresh observation, not reliance on its remembered value |
| PR #42 update | 2026-10-04T21:59:24Z | Latest owner body explicitly records remaining review/D3/GIE items |
| Integration global handoff | `9d9b2b2b942cfa6d1f7b296ad81d380ec6a70b3e`, committed 14:30:23Z, GCH-014/GSI-020 | Fresh branch tip still predates final 21:55Z CI; records implementation/verification in progress |
| Worker Contract routing | PR #21 fresh head `f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798` | CDR-001's operational routing SSoT; not canonical merge approval |
| Chart local baseline | `581c61c4af859f6cbdc3418209bba9be7bbc76a3` | PR41's tree does not itself contain the trial's Web/P01/Producer/EVL runtime; implementation candidates must be reconciled with an owner-accepted fresh integration base |
| Native branch check enforcement | PR42 base branch exposes protected=false, required status contexts=[], enforcement off; repository rulesets=[] | No claim that these waive CDR/owner governance |

`raw/pr42_branch_protection.json` preserves an encoded-branch endpoint rejection from the connector. The successful unencoded branch read in `raw/pr42_base_ref.json` supplies the available branch protection summary. No denied endpoint is treated as proof of required-check configuration.

## 2. FPIA: implementation, CI and closure are distinct

| Required distinction | Fresh verdict | Evidence |
|---|---|---|
| Tool implementation | PRESENT on exact Draft PR42 head; not integrated | PR metadata/body and exact workflow/source |
| Observed CI | Seven check runs and seven PR workflows success | `raw/pr42_checks.json`, `raw/pr42_workflow_runs.json` |
| Exact PR42 FPIA audit | FPIA_PASS | Run 37234682864 / job 111531323882, exact subject T=`523e702...`, authority register `9d9b2b2...` |
| Historical/Frozen identity | HISTORICAL_FROZEN_IDENTITY_PRESERVED | Four historical records + four CI logs replayed; 27 byte-protected-only disclosed |
| Package code identity | CODE_IDENTITY_DIVERGED | R code_hash `0ef3a900` → T `df34b84f`; do not normalize to SAME/PASS |
| Frozen tools on current T | FROZEN_TOOLS_ON_T_FAIL | Separate verbatim BRANCH_FROZEN_VALIDATION evidence class; a green FPIA job does not erase this |
| Projection / interference / v2 / regression | TRACK_C_PROJECTION_PRESERVED / INTEGRATION_INTERFERENCE_NONE / PASS / PASS | Exact CI log; this review does not independently reproduce it |
| Dedicated Tier 1 / Tier 2 job steps | SKIPPED in this PR-triggered run | Workflow deliberately runs them only on workflow_dispatch. Owner body separately reports final-head local Tier1 256 PASS and Tier2 9 PASS; these are owner-reported evidence, not new independent review |
| Independent adversarial/completeness review at final tool head | NOT_RUN per current owner body | Submitted GitHub reviews, issue comments and review comments are all empty; the fresh global handoff contains no final-head closure |
| Existing Integration D3 | OPEN | D3-a/b/c/d remain undecided; G7 trigger interpretation is pending user confirmation |
| GIE closure | NOT_RUN per owner body; no final closure in fresh handoff | Integration owner action remains |
| Future actual Chart merge-result FPIA | NOT_RUN; exact tree not yet produced | PR42's successful tool-head audit is not a Chart+Integration merge-result audit |

The exact CI result hash is `d85ecc4b4913b31efb61dc2417898d6a51f3d9f7398d9b17bce7f233d847c520`. The log reports `fpia-output: VERIFIED`. Artifact 11315618718 is present, not expired, 51,254 bytes, ZIP digest `sha256:e1d16877accf451bb8d490d58bc3e5e51c2f34e4a1a6decf591ffb118689c226`. The binary artifact was not downloaded or independently authenticated by this review.

Existing decisions stay with the Integration owner:

- D3-a: authentication/pinning of the CI verifier.
- D3-b: content-independent workflow job-id collision rule.
- D3-c: dynamic-invocation non-claim.
- D3-d: #28 importer attribution.
- G7: interpretation of integration-branch-only PR triggering.

Verdict: **TOOL_CI_VERIFIED_ON_EXACT_PR_HEAD / INTEGRATION_GOVERNANCE_GATE_NOT_CLOSED**. No new Chart D3 is established here.

## 3. Product authority and source rights

At PR42, `publication/extractors.py:201-214` registers only QGV, Leaderboard, Macro and Technical persisted shapes. Exactly one structural match is required; an unknown ChartDocument matches zero and is refused. No current Target Theme read-service route or subject registration exists.

`publication/authorization.py:16-17` has `ACTIVE_AUTHORIZATIONS=()`. `publication/envelope.py` enforces that empty set, and the current P01 predicate does not issue LIVE, FROZEN_SNAPSHOT or OFFICIAL. P01's research-display eligibility is not a generic user-target display authority.

Product/P01 owners must classify this exact current TARGET capability and explicitly accept its product subject, source bindings, authority/invalidation behavior and denial path. They may accept the applicable existing authority route or define an approved scoped route for user-authored portfolio content. Neither repository presence, a producer PASS, a source right nor the user's audit request is automatically an existing code-defined grant. A new independent endpoint cannot serve as an authority bypass.

C08 keeps source-use/display rights separate from product publication authority. This user-defined Theme slice requires an admissible-use/provenance record for its actual Target source; it does not acquire a GICS/feed/licensing dependency. This record is part of source-root admission S1; no hypothetical external licence or grant is added as a separate blocker.

## 4. Minimal numeric and serialization alignment

The root checkpoint's `MINIMAL_CHARTDOCUMENT_v0.2_TARGET_THEME.md` now specifies a bounded exact lexical-decimal projection: preserve source decimal tokens and units, aggregate without rounding, verify independently with rational arithmetic, keep source/calculation/result evidence, and emit exact numeric strings.

PR42 `producers/serialization.py:14-43` rejects a Decimal object. Its canonical bytes at :46-49 use sorted keys, compact separators, ensure_ascii=False, allow_nan=False and UTF-8. Explicit Decimal→string encoding must precede reuse. Stable arrays are ordered before serialization, and the immutable hash preimage excludes self-hash and current authority.

These are concretized design requirements, not a new active schema, numeric policy, tolerance, threshold or independent numeric-approval blocker. Existing Personal/Frozen contracts are not modified. Production owner contract registration remains G1.

## 5. Exact implementation candidate paths and impact

The preferred scoped route adds the Target domain and shared Chart read product independently of the existing schema-1 portfolio assembler. `web_mvp.build()` already copies ordinary .js/.css assets, so new Chart renderer assets do not inherently require a protected Web builder edit. Owner acceptance of the route remains G2.

Flags below refer to direct hash membership. They do not mean ownership or FPIA can be skipped.

| Candidate exact path (under implementation/) | Role | P01 seven-file digest | Track C package code_hash | Owner routing |
|---|---|---|---|---|
| src/investment_system/charts/__init__.py | New namespace | No | Yes | Chart |
| src/investment_system/charts/target_source.py | Validate admitted TARGET source/root and complete membership inputs | No | Yes | Chart + Personal/Portfolio |
| src/investment_system/charts/target_theme.py | Exact one-time TARGET Theme aggregation | No | Yes | Chart + Personal/Portfolio |
| src/investment_system/contracts/chart.py | Minimal versioned immutable Chart contract | No | Yes | Chart + Product |
| src/investment_system/product/chart_api.py | Shared query, current exact-subject authority envelope | No | Yes | Product/API + Chart + P01 |
| src/investment_system/publication/extractors.py | Optional registration only if P01 owner selects that route | No | Yes | P01/publication |
| tools/serve_chart_api.py | Optional API host/mount adapter; existing Web is static | No | No | Product/API + Web |
| src/investment_system/product/web_assets/target-theme-chart.js | Segment/drilldown renderer of precomputed contract | No | No | Web |
| src/investment_system/product/web_assets/app.js | Target route; explicit basis presentation and remove production actual_weight ?? target_weight fallback | No | No | Web |
| src/investment_system/product/web_assets/locale.js | Strategy Theme/user-defined labels and availability messages | No | No | Web/Language |
| src/investment_system/product/web_assets/style.css | Accessible selection/table presentation | No | No | Web |
| tests/test_target_theme_domain.py | Exact domain oracle/completeness/revision tests | No | No | Chart + Personal |
| tests/test_target_theme_product_contract.py | Hash and changing-authority/withholding tests | No | No | Chart + Product + P01 |
| tests/test_target_theme_api.py | API/Web payload/result/hash parity | No | No | Product/API + Chart |
| tools/target_theme_chart_browser_test.js | Source→segments→selected constituents; keyboard and labels | No | No | Web + Chart |

Every selected path needs the owner-approved exact write set and future exact merged-tree FPIA. New .py files anywhere within `src/investment_system/` affect package code_hash, even when no Track C-owned file changes. Tools/tests/JS/CSS do not directly enter that Python hash; FPIA still checks the actual final tree and attribution.

Optional central schema-1 integration is a separate alternative:

| Existing protected path | P01 digest | Track C code_hash | Required boundary |
|---|---|---|---|
| src/investment_system/product/web_mvp.py | Yes | Yes | Web + P01 + Integration; separately adjudicated protected change/digest path |
| src/investment_system/producers/assembler.py | Yes | Yes | Producer + P01 + Integration; separately adjudicated protected change/digest path |

The preferred route avoids those edits. **No #17 repin blocker is invented for an unchanged seven-file digest.** If owners select the protected alternative, its existing authorization boundary must be closed explicitly; FPIA PASS never supplies repin authority.

Read-only byte reconstruction from fresh exact-SHA raw sources reproduces the current C28-adopted P01 digest `e6de46714f4405b52d4b25a418cc4081ff6df9d8891f332f59cc47e5ccc6c909` (see `P01_DIGEST_FRESH_READ_PROOF.json`). `evl/calibration_contracts.py:74-77` derives code_hash from sorted package-relative .py paths, NUL separators and raw file bytes across the whole package. The full 204-file package hash was not recomputed in this checkpoint; the old same-head v0.3 proof and fresh CI report remain separately attributed.

No edits are proposed to `personal/*` Frozen contracts, `evl/*` Track C projections, publication authorization/grant activation or P01 predicate policy.

## 6. Atomic readiness closure predicates

The root's total is **6 remaining preimplementation closure predicates**: S1–S3 from the independent Lane A source investigation, plus these three governance predicates. Subactions below are concrete closure evidence, not separately counted or double-counted tests.

| ID | Open predicate | Exact owner action / closure evidence |
|---|---|---|
| G1 | Shared Product/Chart registration and current exact-subject authority admission | Chart/Product/P01 owners accept the scoped target contract and subject extraction, dependency invalidation, current authority/denial path and API/Web equality. Explicitly classify the user-target authority route without inventing a grant |
| G2 | Accepted exact cross-owner write set, integration base and P01 branch | Chart/Personal/Product/API/Web/P01/Integration owners accept the listed paths at a fresh base, prefer additive route with unchanged seven-file digest, select applicable owner checks and future merge-result audit plan; explicitly adjudicate any selected protected alternative |
| G3 | Final FPIA tool governance closure | Integration owner obtains final-head independent adversarial/completeness review, closes the existing D3/G7 items through that owner's route, and records final GIE/global closure evidence |

Bounded numeric serialization is documented; source admissible-use/provenance is part of S1. Neither is counted as a hypothetical seventh/eighth blocker. Future production tests and the actual Chart merge-result FPIA are implementation/verification exit gates; their current NOT_RUN state is not a separate missing-input blocker.

Target Strategy Theme has no dependency on Market OHLCV, GICS, Investment Type, overlap or ACTUAL histories. FPIA tool closure does not close source/contract/path gates.

## 7. Exact next implementation sequence

1. Close S1–S3 and G1–G3 with the source/contract/owner/Integration evidence above.
2. Pin the accepted fresh integration base and exact write set; implement the source adapter, exact Theme domain and shared contract/read product once.
3. Wire the accepted current-authority route and Web renderer; display ACTUAL as NOT_AVAILABLE when requested, with no target fallback.
4. Run the deterministic source/domain/contract/API/browser plan from the root checkpoint; owner regressions verify no schema-1 or authority escalation.
5. Produce a history-preserving actual Chart+Integration candidate and run the accepted FPIA verifier against that exact merge-result SHA, preserving and reporting package code identity divergence.
6. Record the scoped result for the Integration owner. Canonical merge, grant, Freeze and production deployment remain outside this stage.

This investigation performs read-only remote/local inspection plus additive evidence creation. It is not an independent FPIA adversarial review, test run, workflow dispatch, owner acceptance or production certification.
