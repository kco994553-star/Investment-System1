# Missing-Data Gate — current behavior reconciliation

**OBSERVATION ONLY / INACTIVE / NOT APPROVED.** This is a scoped continuation of
PR #44's `AUDIT.md`, `CONTRACT.md`, `COMPATIBILITY.md`, `current_factor_map.json`
and frozen golden evidence. It does not repeat Remote Recovery, alter runtime
code, propose new default weights, or settle any semantic policy.

Inspected worktree HEAD: `11cd2f5ac545af54d943dc206396c1fb6926689c`.
Runtime source baseline remains canonical
`b8e39a2196a6d7794a04a0cd5393c68329e126ca`; the inspected source hashes accompany
the new probes. Root-scoped intake evidence records the live PR/integration
status, rather than this file repeating historical remote claims.

Paths below are relative to `implementation/src/investment_system/`, unless
marked otherwise. Line references identify the inspected source. Existing
71-case `golden_cases.json` is preserved and not regenerated or rerun merely to
complete this map.

## 1. Relevant contracts already present

`contracts/enums.py:10–30` defines `QualityState` and `CoverageState`.
`contracts/models.py:74–90` defines nullable `FactorObservation.score_0_100` and
`VCandidate.v_score`. Required/optional/conditional factor roles are not encoded
in these result objects. `factor_applicable` currently encodes exactly one
structural exclusion: financial-profile `roic_wacc` (`qgv/factors.py:42,103–106`).
No runtime factor-role registry is inferred from fixed weights or V candidates.

Existing QualityState values include OK, MISSING_DATA, STALE_DATA, ESTIMATED_DATA,
CONFLICTING_SOURCE, PIT_UNAVAILABLE, VERSION_MISMATCH, IDENTIFIER_CHANGED,
CALCULATION_ERROR, BLOCKED_DEPENDENCY, NOT_APPLICABLE, SYNTHETIC,
IDENTIFIER_AMBIGUOUS. **INSUFFICIENT_HISTORY, SOURCE_UNAVAILABLE and INVALID are
not QualityState values.** The current map therefore preserves their upstream
reason rather than pretending they already have scorer-specific dispatch.

The inactive Common Contract separates value presence, applicability, original
quality, PIT admission and assessment metadata. That representation is a design
starting point, not an activated missing-policy implementation or new taxonomy.

## 2. Exact reducer flow for Q, G and V prior

All three call the same existing `_weighted`
(`qgv/scoring.py:24–65,120–123`). They differ in the existing dictionary and in
the financial exclusion applicable only to Q. The arithmetic below describes
the code; it does not authorize it as a future complete-score definition.

For every ordered `(factor_id, weight)`:

1. `factor_applicable` false: record `NOT_APPLICABLE`; skip before examining the
   observation, score, quality, or blocked state.
2. Absent observation: record `MISSING`, set `missing_any`, skip contribution.
3. `missing_is_not_zero` removes numeric or null values with MISSING_DATA,
   PIT_UNAVAILABLE, BLOCKED_DEPENDENCY or NOT_APPLICABLE
   (`qgv/factors.py:109–117`).
4. Applicable BLOCKED_DEPENDENCY sets the axis-wide blocked flag, regardless of
   score presence and regardless of weight zero.
5. Otherwise null score sets `missing_any` and records the original quality
   string, even if that string is OK.
6. Every other numeric value contributes `weight * score`; `used += weight`.
   No finite/range or integrity admission check occurs in this reducer.

Let `N` be the accumulated contribution and `U` the admitted sum of weights.
There is **no denominator variable or division**. With the shipped dictionaries
whose nominal sums are 1, the effective denominator remains 1 even if some
factors are absent or structurally N/A. Neither missing nor N/A redistributes
weight. The value is a full-weight partial contribution when evidence is absent,
not the available-factor weighted mean.

`blocked=True` or `U == 0` gives `score=None, coverage=BLOCKED`.
Otherwise `score=N`; coverage is PARTIAL if `missing_any` or
`U < 1.0 - 1e-12`, and READY otherwise. The tolerance is an observed existing
constant, not a newly proposed cutoff. No new percentage or minimum coverage
threshold is selected.

## 3. Q/G/V prior state matrix

For concise numerical anchors, all existing factors have synthetic score 70;
the altered representatives have weights `wQ=.20` (`competitive_advantage`),
`wG=.25` (`next_3_5y_growth`), `wV=.10` (`sector_context`). These are **existing
weights and illustrative data**, not new defaults. Other factors remain present.

| Input state | Eligibility / contribution | Numerator Q / G / V prior | Denominator | Axis score and coverage | Confidence | Final status |
|---|---|---|---|---|---|---|
| All present, OK numeric | All admitted | 70 / 70 / 70 | Implicit 1 | 70, READY | No axis computation | Coverage enum only; no separate validity enum |
| Factor absent | Representative excluded | 56 / 52.5 / 63 | 1 unchanged | Same as numerator, PARTIAL | No response to absence | Q/G absence makes snapshot PARTIAL; V-only absence leaves snapshot READY |
| `score=None`, OK | Excluded; original note is `factor=OK` | 56 / 52.5 / 63 | 1 unchanged | Partial contribution, PARTIAL | No response | Numeric presence and quality cannot be inferred from the note alone |
| MISSING_DATA, numeric or null | Excluded even if numeric | 56 / 52.5 / 63 | 1 unchanged | Partial contribution, PARTIAL | No response | Original quality retained in notes, not a zero observation |
| Observation NOT_APPLICABLE, numeric or null | Excluded as missing by reducer | 56 / 52.5 / 63 | 1 unchanged | Partial contribution, PARTIAL | No response | No reason-specific denominator handling |
| Structural N/A: financial `roic_wacc` | Skip before observation/quality | Q=56; G/V unchanged | 1 unchanged | Q=56, PARTIAL even with all other factors present | No response | Profile economic exclusion differs from absent evidence |
| PIT_UNAVAILABLE, numeric or null | Factor excluded; other factors remain | 56 / 52.5 / 63 | 1 unchanged | Partial contribution, PARTIAL | No response | Factor-level PIT failure does not fail-close the whole axis here |
| BLOCKED_DEPENDENCY, numeric or null | Affected applicable axis blocked | Other contributions may be accumulated, then discarded | No emitted denominator | None, BLOCKED | No response | Q/G blocks snapshot and total; V-only block leaves QG snapshot READY and total 70 |
| VERSION_MISMATCH, IDENTIFIER_AMBIGUOUS, CALCULATION_ERROR with numeric score | Currently admitted | 70 / 70 / 70 | 1 | 70, READY | No response | No integrity distinction inside reducer |
| Same integrity states with null score | Excluded because null | 56 / 52.5 / 63 | 1 unchanged | Partial contribution, PARTIAL | No response | Null wins only through generic missing branch |
| STALE_DATA, ESTIMATED_DATA, CONFLICTING_SOURCE numeric | Currently admitted | 70 / 70 / 70 | 1 | 70, READY | No derived discount/confidence | No policy approval inferred from current inclusion |
| All axis factors absent or no admitted positive-weight factor | No admitted weight | 0 / 0 / 0 internally | No emitted denominator | None, BLOCKED | No response | Presence of valid zero-weight observation alone cannot yield a score |
| Multiple absent positive-weight factors | Surviving contribution only | Example Q=49, G=52.5, V=49 | 1 unchanged | PARTIAL for each; legacy total=50.75 | No response | Partial score can reach ranking consumers |
| INSUFFICIENT_HISTORY / SOURCE_UNAVAILABLE / INVALID | No native quality dispatch | Depends on upstream translation or absence | Depends on resulting path above | Not an encoded standalone scorer state | No formula | See upstream-state matrix below |

`IDENTIFIER_CHANGED` follows the same admission membership rule as the three
integrity examples above; the existing frozen golden covers the full enum. It
is not newly asserted to be equivalent in economic severity. Direct scalar
inputs outside 0–100 and non-finite scalars also lack reducer validation.
New scoped numeric V probes preserve the actual result: NaN/Inf can propagate
into V prior and all candidates while V coverage is READY and the candidate
blocked reason is null. Evidence serializes non-finite results as explicit
markers; it does not substitute a valid number or repair production output.

## 4. V candidate evaluator state matrix

`score_v_candidates` (`qgv/scoring.py:68–117`) is a separate research evaluator,
not the source of current production V. Candidate weights are checked for exact
seven-factor identity, sum and the existing 5–30% bounds
(`qgv/factors.py:52–62`), then **every factor is required by this algorithm**.
This is algorithmic complete-case behavior, not an authoritative requiredness
registry. It does not receive `ProfileKind` or call `factor_applicable`.

| Input state | Eligibility | Numerator / denominator | Score | Coverage | Confidence | Final status |
|---|---|---|---|---|---|---|
| All seven numeric, admitted quality | Complete vector | Ordered weighted sum; weights nominally sum to 1 | Weighted sum, synthetic uniform example 70 | No candidate coverage field | No candidate confidence field | Existing lifecycle plus null `blocked_reason` |
| Factor absent | Complete vector fails | Stops at first missing; any intermediate sum discarded | None | Not emitted | Not emitted | `incomplete V factors; no auto-reweight` |
| `score=None`, any quality | Complete vector fails | Same early exit | None | Not emitted | Not emitted | Same incomplete reason |
| MISSING_DATA / PIT_UNAVAILABLE / BLOCKED_DEPENDENCY, even numeric | Rejected | Same early exit; no renormalization | None | Not emitted | Not emitted | Same incomplete reason conflates these failure reasons |
| NOT_APPLICABLE numeric | **Currently admitted** | Full weights and full sum retained | Uniform example 70 while V prior is 63 | Not emitted | Not emitted | No blocker; structural difference from prior |
| VERSION_MISMATCH / IDENTIFIER_AMBIGUOUS / CALCULATION_ERROR numeric | Currently admitted | Full sum | Uniform example 70 | Not emitted | Not emitted | No integrity blocker |
| STALE_DATA / ESTIMATED_DATA / CONFLICTING_SOURCE numeric | Currently admitted | Full sum | Weighted sum | Not emitted | Not emitted | No derived confidence |
| INSUFFICIENT_HISTORY / SOURCE_UNAVAILABLE / INVALID | No native quality state | Depends on upstream absent/null/quality translation | Conditional on actual represented state | Not emitted | Not emitted | Cannot invent reason-specific candidate behavior |
| Zero candidate weight | Current validator rejects it | Does not enter factor loop | None if such candidate were submitted to current validation flow | Not emitted | Not emitted | Existing 5–30% weight constraint error |
| Partial availability | Complete vector fails | No available-weight denominator | None | Not emitted | Not emitted | Complete-case blocking |

The candidate's `used` sum is a completeness check, not a renormalizing division.
Its lifecycle is preserved when blocked; there is no promotion to VALIDATED or
STANDARD. `production_v_score` always returns the supplied prior and
PROVISIONAL_INITIAL_PRIOR (`qgv/scoring.py:126–128`), not a candidate substitution.

## 5. Upstream reason, eligibility and integrity boundaries

| Input / boundary | Current eligibility flow | Numerator / denominator / score | Coverage / confidence / final state | Evidence |
|---|---|---|---|---|
| Raw field absent or ratio denominator zero | `_ratio` / `_yoy` returns None; `map_raw` emits score None + MISSING_DATA | Reducer/candidate paths above | Original reason is only free-text mapper notes; no separate source-unavailable dispatch | `qgv/raw_map.py:31–40,159–169` |
| Source unavailable, fetch timeout/error | `try_fetch_companyfacts` returns None | No raw payload; wrappers may return None, or mapper later sees missing fields | No SOURCE_UNAVAILABLE QualityState; this branch does not produce a QGV snapshot | `providers/sec_companyfacts.py:299–307`; `qgv/financial_issuer.py:39–47` |
| Malformed filing / parser failure in historical cross-section | Exception recorded for issuer and issuer skipped | No issuer score | `quality[cid]` records `raw=False,error=...`, not a synthesized factor zero | `validation/historical.py:162–172` |
| No provider record eligible at decision time | `select_latest` admits only BOTH available_at and published_at <= as_of | `analyze_as_of` returns None before mapper/reducer | No snapshot, coverage or confidence emitted | `pit/resolver.py:21–38`; `providers/memory.py:20–29,44–46`; `qgv/pipeline.py:46–50` |
| Direct `analyze_raw` with future available_at OR future published_at | Current entry point bypasses provider resolver | Mapper/reducer can emit score | Existing permissive internal entry; not evidence that actual historical runs leaked | `qgv/pipeline.py:21–44`; two new synthetic entry-point probes |
| `pit_state` called separately | Future stamp becomes PIT_UNAVAILABLE, absent stamp becomes MISSING_DATA | That state affects scoring only if supplied on factor observation | Not automatically called by direct raw mapping | `pit/resolver.py:41–50`; `qgv/raw_map.py:87–90` |
| Insufficient requested G history | `assess_horizon` emits MISSING/PARTIAL plus INSUFFICIENT_QUARTERLY_HISTORY reason | G arithmetic unchanged; horizon is metadata only | Snapshot `g_horizon` copies state and fallback_used, not fallback_reason; axis/snapshot coverage remains independent | `qgv/g_horizon.py:74–90`; `qgv/pipeline.py:27,36–43` |
| Identifier ambiguity before analysis | Registry returns IDENTIFIER_AMBIGUOUS instead of resolved Identifier | Resolver caller must stop or handle it; scorer does not resolve identity | Factor marked numeric IDENTIFIER_AMBIGUOUS is nevertheless admitted by the scorer | `qgv/identifiers.py:45–72`; `qgv/scoring.py:39–49,89–96` |
| Generic integrity flags on DataStamp | `map_raw` derives quality OK/SYNTHETIC from source kind/synthetic, not generic stamp flags | No universal scorer-side provenance/version/identity gate | Independent producer/provider validation can exist; no blanket claim that all upstream paths lack integrity checks | `contracts/models.py:34–50`; `qgv/raw_map.py:87–90` |

Factor-level PIT_UNAVAILABLE and provider-level PIT admission are therefore not
the same current behavior. Ordinary missing renormalization cannot be assumed to
be the implementation of either. For a new policy, the Decision Package must
express the domain scope of an integrity failure (unused input, factor input,
dependency, identity/config, or whole evaluation) rather than masking it as an
ordinary missing observation. This document records the gap without resolving
or changing current PIT policy.

`validation/historical.py:554–577` contains a separately named
`full_pit_candidate_eval` checklist. It keeps full_pit_pass, OOS, calibrated and
real_data_verified false and checks outcome linkage and parent immutability.
It is **not** the V candidate weighted reducer and does not establish a new
factor missing policy. Its `v_coverage_matrix` counts score presence irrespective
of factor-quality admission (`validation/historical.py:458–488`).

## 6. Zero-weight semantics — observed limits

The shipped Q/G/prior weights are all positive. Personal `WeightOverride`
accepts zero (`personal/weights.py:149–157`) but is not connected to QGV runtime.
The existing tree defines zero-parent global contribution while retaining child
mix, and prohibits missing-weight redistribution (`personal/weights.py:142–145,
166–185`). Consequently **there is no current production Custom QGV zero-weight
result to report**.

Read-only diagnostic calls pass local, sum-preserving synthetic dictionaries to
the existing `_weighted` without modifying any shipped dictionary. They test
what the current reducer itself does if such input reaches it:

| Zero-weight factor state | Contribution / denominator | Current reducer result | Requiredness effect |
|---|---|---|---|
| Numeric admitted | Adds zero; admitted weight adds zero | Remaining score can be READY | No explicit role or skip-before-read rule |
| Absent or null | Adds nothing, but sets `missing_any` | Same numeric remaining score, PARTIAL | Zero does not eliminate missing detection |
| Numeric PIT_UNAVAILABLE or observation N/A | Adds nothing, sets missing flag | Same numeric remaining score, PARTIAL | Zero does not define eligibility |
| BLOCKED_DEPENDENCY | Blocked flag set before contribution | None, BLOCKED | Weight zero does not bypass this blocker |
| Profile financial structural N/A | Applicability skips observation first | Blocked quality on excluded ROIC is ignored | Structural exclusion differs from zero contribution |
| No positive admitted weights at all | `used == 0` | None, BLOCKED | Zero-valid factors alone cannot produce a score |

The candidate zero-weight diagnostic validates a **local copy** of the existing
prior with one factor set to zero and its weight moved to another already
allowed factor solely to isolate the validator result. It returns the existing
lower-bound constraint error. These diagnostic values are neither new candidate
defaults nor recommended Personal weights. They do not wire overrides or edit
Official requiredness. Future zero-weight policy remains a separate decision.

## 7. Coverage, confidence, downstream final status

Axis `_weighted` coverage is an enum driven by admitted weight, missing flag and
blocker; it is not a published evidence count or percentage. Q/G factor coverage
and axis confidence are not separately assessed in current snapshot output.
`AnalysisEngine` combines only Q/G coverage (`qgv/analysis.py:42–50`). When both
scores are numeric, legacy total remains `(Q+G)/2` even with PARTIAL coverage
(`qgv/analysis.py:58–63`). Synthetic only relabels READY snapshot coverage to
SYNTHETIC; it does not erase PARTIAL/BLOCKED.

Snapshot confidence remains the caller-supplied argument, default MEDIUM
(`qgv/analysis.py:33,89`). It does not react to data coverage or become a
multiplier. V factor table copies QualityState into both confidence and coverage,
and determines effective_weight and missing_reason only from score presence
(`qgv/analysis.py:100–114`). Thus numeric PIT_UNAVAILABLE can display weight .10,
missing_reason null and confidence/coverage PIT_UNAVAILABLE despite exclusion
from prior and blocking all candidates. This separate existing metadata problem
is **preserved**, not fixed or combined with a confidence formula here.

`quality_states` in a snapshot is not the full factor-state union. It currently
adds SYNTHETIC and, for Q/G combined BLOCKED coverage, BLOCKED_DEPENDENCY only
(`qgv/analysis.py:52–56`). V failure can coexist with snapshot READY; therefore
READY is not proof of valid V or PIT-integrity closure.

Leaderboard consumes snapshots without rescoring and sorts by total then Q,
without a coverage-based admission filter (`qgv/leaderboard.py:29–34`). Partial
Q/G results can therefore affect current ordering. This is an observed consumer
dependency, not authorization to recalculate existing boards or histories.

## 8. New scoped evidence and limits

`current_behavior_probe.py` calls existing runtime functions without patching
globals, writing Official objects, fetching live data, or touching expected
fixtures. `evidence/current_behavior_probes.json` captures:

- 77 direct snapshot observations across Q/G/V prior/candidates, numeric/null
  state variants, multiple absence, all absence, financial applicability and
  malformed numeric admission;
- 18 zero-weight reducer diagnostic observations and existing candidate-weight
  validation, not hypothetical future-policy outputs;
- separate synthetic future available_at and published_at entry-point contrasts;
- insufficient-history metadata nonmutation and existing synthetic financial
  raw fixture behavior;
- source SHA256 and unchanged golden SHA256
  `ed01c7f25e6a01b23c9f474b9f66f1f204828834bbdbc25efc286d96050c5040`;
- independent arithmetic/entry-point assertions: PASS.

These counts are probe observations, **not** 95 new pytest tests or remote CI
results. Existing PR #44 remote CI and frozen golden evidence are reused by
their pinned SHA; no claim of new CI coverage is made here. Real PIT/OOS is
NOT_RUN; Holdout UNCONSUMED. Production code, weights, legacy expected results,
Official scores/Leaderboards/Track Record, Frozen history and canonical remain
unchanged. Policy alternatives and recommendation are owned by the separate
Decision Package and remain RECOMMENDED ≠ APPROVED.
