# Missing-Data policy impact simulation

**Status: PROPOSED / INACTIVE / SYNTHETIC ONLY / NOT APPROVED.** This research script is not imported by the production evaluator. It changes no score, factor, weight, existing fixture, workflow, historical record, or runtime configuration. PIT/OOS is **NOT_RUN**; Holdout is **UNCONSUMED**.

## Purpose and limits

The comparison exposes the mathematical consequences of possible Missing-Data policies. It does not decide which real Q/G/V factors are required or optional, which new sector exclusions should exist, or whether any incomplete result may enter an Official ranking.

Inputs are the existing `current_factor_map.json` weights and read-only observations from `golden_cases.json`. Uniform scores of 70 and the heterogeneous scores come from those existing synthetic fixtures. Zero weights are explicit toy Custom-profile experiments; they do not alter an Official default. No new numeric default, calibration, confidence formula, coverage cutoff, or tolerance is proposed.

For every axis, the first factor in the existing map is assigned **REQUIRED**, and the others **OPTIONAL**, solely to make the alternatives observable. This is an arbitrary **simulation assignment**, not a factor-registry recommendation. New hypothetical N/A cases are also simulation-only. The financial Q example is different: the existing production `FINANCIAL_NOT_APPLICABLE` already excludes `roic_wacc`, and the original golden case records Q = 56.

The script checks the original golden identity and all 33 pinned production source identities before and after the comparison. It reads the stored historical expectations; it does not rerun or regenerate the original golden baseline.

Toy zero-weight cases set a copied factor weight to zero without redistributing sibling weights. Their resulting relative sum can be below 1, so they are **denominator/requiredness sensitivity inputs, not configuration-valid Personal WeightOverride requests** under the existing sibling-sum contract. The prototype compares arithmetic after that hypothetical input; a real evaluator must first validate its pinned configuration. No existing config validator is bypassed, no runtime wiring is exercised, and these cases do not prove Personal/Official runtime isolation.

## Alternatives kept separate

All four alternatives share a **proposed** safety boundary: consumed PIT/integrity failures and global source-admission failures block before weights; unproven applicability blocks; zero positive applicable weight or no scoring evidence cannot produce a score. These guards are evaluated in this research model only. They are not new production implementation.

| Alternative | Ordinary missing | Denominator | Partial output | Required missing |
|---|---|---|---|---|
| A — strict complete-case | Withhold score whenever applicable evidence is incomplete | Applicable configured weight | None | Block |
| B — available estimate | Estimate from whatever admissible evidence exists | Available configured weight | `PARTIAL_ESTIMATE`, diagnostic only | Estimate in this alternative |
| C — fixed partial contribution | Keep missing factor weight | Applicable configured weight | `PARTIAL_CONTRIBUTION`, diagnostic only | Contribution in this alternative |
| D — requiredness hybrid | Separate required, active optional, proven N/A, and unresolved applicability | Applicable configured weight; ordinary missing stays included | Positive-weight optional missing permits `PARTIAL_CONTRIBUTION`, diagnostic only | Block regardless of weight |

A is a **stronger** fail-closed illustration than the user's minimum “required missing blocks” proposal: even toy optional missing withholds the result. D differs by permitting an explicitly incomplete diagnostic. Whether to permit optional diagnostics or withhold them is an independent approval choice.

B/C deliberately show alternatives that do not enforce the toy requiredness assignments. They are mathematical comparisons, not claims that required evidence may safely be omitted. The separate Decision Package must establish requiredness before any alternative is approved.

Proven N/A exclusion is a common assumption for the four main comparisons. It is **not buried as an approved denominator decision**: the financial sensitivity table below compares retaining N/A weight, excluding N/A weight, and available-only weight separately.

For every incomplete output, `complete_rank_eligible_under_this_candidate` is false. This is an illustrative future completeness boundary, not a current Official Leaderboard admission rule. Even a complete synthetic result is not a grant to publish it. No actual ranking or Leaderboard was generated or changed.

## Arithmetic and metadata

Let `W_applicable` be configured weight for factors whose economic applicability has been resolved as true. Proven N/A factors are excluded; unknown applicability prevents defining this denominator. Let `W_available` be weight supported by admissible present factor evidence, and `N` the sum of weight × score for that evidence.

The fixed contribution is `N / W_applicable`; the available-only estimate is `N / W_available`. Existing Q/G/V weights sum to 1, so retaining the entire registry denominator reproduces the current sum-of-contributions meaning for ordinary missing. Removing N/A from the denominator is a distinct proposed semantic change.

The result preserves the numerator, applicable weight, available weight, selected denominator, missing reason, required-evidence counts, coverage, score kind, and final status. Arithmetic diagnostics can exist on a blocked row for explanation, but its admitted `score` is `null` and it cannot rank. They must not be mistaken for an allowed result.

Coverage has separate observations: available/applicable **weight fraction**, all applicable **evidence-inventory count**, and **positive-weight active-scoring count**. None has a proposed cutoff. Inventory count retains zero-weight rows, making missing evidence visible even where weighted coverage equals 1. Construct completeness under the proposed M4 context requires method-required evidence and active scoring evidence; optional predeclared unrequested zero-weight inventory may be absent without making that construct partial. Required evidence remains compulsory at zero weight. All-zero weights have no weighted coverage denominator and cannot score; complete count coverage alone cannot authorize a result.

Confidence is not calculated or inferred from coverage. The original input confidence label is retained as source metadata, while `formula = NOT_DEFINED`. This simulation does not repair the current V/Quality metadata reuse.

Exact rational arithmetic uses the decimal representations already present in the factor map and golden observations. It introduces no epsilon or rounding policy. This is conceptual arithmetic for policy comparison, **not a recommendation for future production accumulation/rounding and not a bitwise equivalence test**. Tiny differences between stored legacy binary-float representations and displayed rational values are not production changes.

## Observable policy effects

`—` denotes blocked, with `score = null`. All noncomplete numeric outputs below are diagnostics excluded from complete-ranking illustration.

| Case | A | B | C | D | What the example establishes |
|---|---:|---:|---:|---:|---|
| Q/G/V: all present at 70 | 70 | 70 | 70 | 70 | Complete uniform inputs agree |
| Q: toy optional ROIC weight 0.20 missing | — | 70 | 56 | 56 | Available-only estimate masks the missing weight |
| Q: toy required competitive advantage weight 0.20 missing | — | 70 | 56 | — | Requiredness is a separate decision from denominator |
| G: toy optional growth efficiency weight 0.20 missing | — | 70 | 56 | 56 | Fixed contribution is 70 × 0.80 |
| V: toy optional reverse DCF weight 0.20 missing | — | 70 | 56 | 56 | Same arithmetic contract can span axes |
| Q: zero-weight required factor missing | — | 70 | 70 | — | Weighted coverage of 1 does not establish required-evidence completeness |
| Q: predeclared unrequested zero-weight optional inventory missing | — | 70 | 70 | 70 | B/C/D construct complete; inventory count stays partial; A is stronger |
| Consumed PIT/integrity failure, including at zero weight | — | — | — | — | Weights cannot bypass the shared safety boundary |
| Unknown applicability or unsupported N/A claim | — | — | — | — | A reason label cannot prove economic N/A |
| All missing, all N/A, or all-zero weight | — | — | — | — | No synthetic score is emitted for undefined scoring support |

Factor absent, score `None`, source unavailable, insufficient history, several optional missing, blocked dependency, version mismatch, identifier ambiguity, numeric integrity failure, and both provider time-field failures are separate cases in the JSON evidence. Ordinary missing reasons remain separately labelled even where arithmetic is identical. A change of identifier is not automatically invalid: a hypothetical dated/resolved mapping remains present and scores 70, while an unresolved/ambiguous mapping blocks. The mapping examples adopt no new identifier-resolution policy.

The zero-weight optional fixture explicitly says **predeclared unrequested**, `consumed = false`, and cannot affect identity, applicability, or global admission. D returns a complete required/active construct at 70, while inventory coverage still records one missing factor. This creates no Official validity gain: the fixture is a toy Custom profile and no Official scope is modified. A separate zero-weight optional **consumed PIT failure** blocks all four alternatives. B/C numeric diagnostics on missing **required** zero-weight evidence never receive a complete-ranking flag under the shared proposed M4 context.

### Financial applicability is a real compatibility decision

The existing financial golden Q = **56** is preserved. With all applicable factors at 70, current Q skips ROIC but retains its 0.20 weight in the effective full-registry denominator. It also reports partial coverage under the legacy rule. All main proposed candidates instead treat proven N/A as excluded from applicability and would produce 70 in this synthetic comparison.

| Financial scenario | Numerator | Keep full registry denominator | Exclude proven N/A; retain ordinary missing | Available-only denominator |
|---|---:|---|---|---|
| Existing financial N/A golden | 56 | 1.00 → **56** | 0.80 → **70** | 0.80 → **70** |
| Same fixture, toy optional market position also missing | 45.5 | 1.00 → **45.5** | 0.80 → **56.875** | 0.65 → **70** |

This is a potential Official score/ranking delta, not metadata-only alignment. Excluding real economic N/A can reduce financial-sector penalties, but cross-sector comparability still requires approved applicability definitions and interpretation of the new applicable-factor construct. Migration must retain old historical results and separately validate the new scoring version. No historical expectation is rewritten.

The existing `financial_na_even_if_bad_roic` fixture has an unused ROIC observation marked blocked. It does not contaminate the simulated calculation because the existing financial applicability branch never consumes that observation. This narrow case is distinct from **contamination already consumed by applicability/global identity**, which blocks even if a later label says N/A. Out-of-scope data may only be ignored with explicit scope evidence, never by relabelling a consumed failure.

### Selective removal can inflate an available-only estimate

The heterogeneous observations already exist in the golden fixture. Selectively hiding the lowest-scoring factor keeps the same registry weights and meanings.

| Axis | Complete score | Hidden observation | B available estimate after hiding | C fixed contribution after hiding | D after hiding |
|---|---:|---|---:|---:|---|
| Q | 31.975 | Competitive advantage = 0.125, weight 0.20 | **39.9375** | 31.95 | Blocked: toy required factor missing |
| G | 45.025 | Growth efficiency = 7.125, weight 0.20 | **54.5** | 43.6 | 43.6, diagnostic only |
| V | 47.075 | Historical valuation = 1.125, weight 0.15 | **55.18382352941177** | 46.90625 | 46.90625, diagnostic only |

Thus a sparse company can display a higher available-only estimate when weak factors are absent. The guarded B candidate prevents complete-ranking promotion, so this is an arithmetic gaming pressure, not a demonstrated exploit of an Official production ranking. Permitting partial estimates to rank later would reopen that risk. Fixed contributions cannot improve under removal of nonnegative scores with the same applicable denominator, but they penalize ordinary missing and can disadvantage young companies or sectors with weak source coverage. Diagnostic-only handling exposes that penalty without treating it as a complete investment-quality score.

### PIT and zero-weight counterexample

A deliberately **rejected** helper illustrates the unsafe order “filter zero weights → discard PIT failure → renormalize remaining evidence.” On a toy zero-weight required PIT failure it produces 70 for each axis. All four guarded alternatives instead return `null` and `BLOCKED_CONSUMED_PIT_OR_INTEGRITY`. The rejected helper is reported only in `unsafe_counterexamples`; it is never a fifth recommended policy.

Separate provider cases assert that `available_at > decision_time` and `published_at > decision_time` block globally despite complete numeric factors. This preserves the existing admission direction; it does not change any timestamp or policy. No real provider/PIT/OOS execution occurs here.

## Verification and reproduction

Run only the research script:

```bash
python implementation/docs/qgv_common_contract_vnext/missing_data_gate/simulate_policies.py
```

Result: **102 synthetic cases × 4 alternatives = 408 policy outputs**, plus 3 explicitly rejected bypass illustrations and 2 denominator sensitivity rows. **270 arithmetic/safety anchors PASS.** The anchors include hand-derived uniform contributions, the financial 56/0.8 = 70 delta, nonimprovement of fixed nonnegative contributions after removal, inflation of available-only estimates after selective removal, requiredness at zero weight, complete required/active constructs despite missing unrequested optional-zero inventory, blocked consumed zero-weight optional PIT failures, resolved versus unresolved identifier changes, blocked provider time guards, and undefined-denominator cases.

Original golden SHA-256 remains:

`ed01c7f25e6a01b23c9f474b9f66f1f204828834bbdbc25efc286d96050c5040`

All 33 pinned production source hashes match the existing inactive-contract baseline; before/after hashes match for every read-only input. Original tests, workflows, golden expectations, and runtime source were not changed. These research checks are **local simulation verification**, not the existing contract/golden regression counts and not GitHub Actions PASS.

The JSON output retains every scenario, hypothetical role assignment, policy result, input hash, arithmetic diagnostic, safety result, and missing reason for review. This is deterministic synthetic illustration, not a PIT/OOS backtest, score distribution study, future confidence rule, or calibrated coverage policy.

## Recommendation supported by the simulation

D is the coherent **proposed** combination: required evidence and applicability independent of weight; consumed PIT/integrity failures block before weighting; proven economic N/A excluded; positive-weight optional missing keeps applicable denominator and may emit an explicitly partial diagnostic; incomplete required/active constructs cannot be treated as complete Official scores. Predeclared unrequested optional-zero inventory stays separately visible and cannot change Official validity. A remains the simpler stronger alternative if users prefer to withhold any applicable-inventory-incomplete result.

The simulation supports taking these choices to approval. It does **not** approve the actual factor requiredness registry, N/A taxonomy, denominator change, partial-result publication boundary, confidence model, ranking admission, or runtime implementation. Financial-score changes and current integrity-state behavior changes require a versioned migration and the repository's D3/user approval boundary before production work.
