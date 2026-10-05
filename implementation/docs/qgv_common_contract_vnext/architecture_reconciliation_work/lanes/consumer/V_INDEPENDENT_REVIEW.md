# Independent V alternative review — no method selection

**INDEPENDENT_REVIEW_PASS_WITH_LIMITS / INACTIVE / EVIDENCE_ONLY.** The V lane
preserves seven factor IDs, existing prior/candidate weights and legacy history.
No alternative was promoted, no new valuation formula/default was evaluated,
and `(Q+G)/2` remains unchanged. B1 stays MORE_EVIDENCE_REQUIRED; no requiredness
or consumer policy is inferred from finite scores.

Inputs: `../v/V_ALTERNATIVE_RESULTS.json`, `../v/V_IMPACT_MATRIX.json`, and the
source-only `../v/v_alternative_probe.py`. Exact hashes and artifact/source checks
are recorded in `V_INDEPENDENT_REVIEW_EVIDENCE.json`. The 21 lane assertions are
the author's new characterization result; this review checked the source,
fixtures, carrier meanings and numerical attribution, and does not inflate those
counts by claiming an independent rerun of all 21.

## Independent candidate verdicts

These are technical evidence dispositions, not approval or production choices.

| Candidate/family | Verdict | Economic meaning and data readiness | PIT/comparability/complexity/manipulation assessment |
|---|---|---|---|
| Existing seven concepts and historical prior | **KEEP** | Stable valuation questions and provisional prior are existing authority/history, not newly proven optimal methods | Keep exact history; input overlap among P/E-derived branches is a disclosure requirement, not automatic factor merging or reweighting |
| Common normalization-control/metadata references | **ALIGN** | Raw metric, normalized score, branch, quality, confidence, coverage, completeness, method validity and consumer permission are different meanings | Additive inactive refs are feasible without an engine; actual attachment/admission may alter identity/use and stays D3; unknowns cannot become default true |
| Supplied central/conservative DCF value versus existing P/E fallback | **MORE_EVIDENCE_REQUIRED** | Both branches exist and can be replayed; supplied DCF assumptions/per-share basis and conservative-value authority are not established | Need model/input/price vintage and units. A fixed EPS multiple is not peer normalization. Shared fallback input families may create correlated evidence; no method is selected |
| Supplied reverse-implied growth versus P/E-implied proxy | **MORE_EVIDENCE_REQUIRED** | Actual `reverse_dcf_implied_growth` field exists; realized revenue proxy is compared with supplied or inferred growth | Forward/realized horizon and executable solver assumptions are absent. Provider replay of supplied values does not prove a solver, forecast validity or full PIT |
| Advertising the P/E proxy as an executed reverse-DCF solver | **REJECT** | No implemented cash-flow/discount/reinvestment solver in this mapper branch | Reject unsupported interpretation while retaining legacy proxy identity; actual replacement remains D3 |
| Supplied peer comparator versus mixed-book/self-inclusive cohort | **MORE_EVIDENCE_REQUIRED** | Relative multiples are a grounded concept; book membership/upper-middle median is the actual historical mechanism | Need authorized comparable multiple/cohort/membership vintage. Membership can move one issuer's score without changing its fundamentals. Sector-bias direction/magnitude is unassessed |
| Existing own-history two-point comparison versus percentile family | **MORE_EVIDENCE_REQUIRED** | Current helper is executable; true historical percentile distribution/window/polarity is absent | Independent old-price/prior-EPS selection needs split/currency/period alignment; no fabricated percentile output or invented minimum history is accepted |
| Sector/theme passthrough-rubric family | **MORE_EVIDENCE_REQUIRED** | Distinct concepts preserved; fields exist, while authoritative rubric/taxonomy/domain/vintage are unresolved | Numeric passthrough is not authenticated rubric evidence. Metadata alignment is modest; real calibration and validation are not run |
| `initial_prior` weight candidate | **KEEP** as literal provisional prior | Existing concrete weights and arithmetic are source supported; no optimization or promotion evidence supplied | Source replay does not give behavioral/OOS/PIT validation; preserve exact reducer order/history. Promotion/Official weight remains D3 |
| `equal_research` weight candidate | **KEEP** as research comparison | Existing equal weights are a concrete implemented research alternative, not a recommended production normalization | Two fixture companies tie exactly. Stable list order is not economic preference or an approved tie rule. Equal weights do not cure incomparable factor methods |
| `mos_tilt_research` weight candidate | **KEEP** as research comparison | Existing safety-tilted weights change the synthetic preference; that sensitivity is evidence, not optimality | Same method/data deficiencies remain; no fitting to observed outcomes or promotion. Actual method/weight use remains D3 |
| Producer assessment → consumer admission activation | **CHANGE_RECOMMENDED**, pending D3 | Numeric error/version markers can still be aggregated and ranked; approved B4/B7 do not supply result-validity/rank policies | Inactive shared ref design is feasible; activation depends on B2/B3/B5/B6 and concrete method requirements. Board must consume producer assessments instead of recomputing QGV |

An actual future DCF model, true percentile normalizer, sector peer universe or
reverse-DCF solver cannot receive a quantitative preference from this package:
those grounded algorithms/inputs are not present. Uncomputed impacts are
correctly left unknown. The three concrete weight candidates are sensitivity
carriers, not three independent economic method estimators. No `PeerDerivedV`
weight family exists at the pinned code; its test name refers to a book comparator.

## Numerical meaning and review refinements

The complete synthetic supplied-DCF/implied-growth fixture has V prior
`66.08333333333334`; the combined P/E fallback fixture has `58.5`, while the Q/G
composite stays `82.0633` in both. **This comparison changes both DCF availability
and supplied implied-growth availability**, so the difference is a combined
branch-family impact, not an isolated DCF/MOS effect.

The already-produced controlled pair holds `reverse_dcf_implied_growth=None`:
`same_dcf_reverse_pe_proxy` gives V prior `68.08333333333334`; the P/E fallback
fixture gives `58.5`. This isolates the central-value/MOS source branches while
retaining the same reverse proxy. No additional method or fixture is needed.

Existing weight fixtures show:

| Candidate | Company A | Company B | Diagnostic relation |
|---|---:|---:|---|
| initial_prior | 73.5 | 61.0 | A > B |
| equal_research | 62.857142857142854 | 62.857142857142854 | Exact tie |
| mos_tilt_research | 57.5 | 67.5 | B > A |

The initially sorted `candidate_orderings` list for equal weights must not be
read as a preference. The V lane now records exact tie groups and labels this a
hypothetical V-only diagnostic comparison. Actual Leaderboard still sorts the
legacy Q/G total; no V ranking policy or tie tolerance was invented.

A same-weight arithmetic distinction is also material to identity: supplied-DCF
V prior is `66.08333333333334`, while candidate `initial_prior` is
`66.08333333333333`. `_weighted` iterates the prior dictionary order, whereas
the candidate loop iterates `V_FACTORS`. This is a literal floating arithmetic
ordering difference, not a different economic method or a scoring repair.
Shared reducer alignment must bind ordered inputs/arithmetic before claiming
exact legacy equivalence. No new rounding or epsilon is recommended.

Adding a low-multiple book member shifts the fixture's peer median 30→10 and
one unchanged issuer's peer factor 100→50. Swapping sector labels alone leaves
scores unchanged. This establishes membership sensitivity and lack of a sector
peer algorithm; it does not measure real sector bias. Removing old-price
history omits an existing 75-point history component and reduces the synthetic
V aggregate by approximately 11.25 without renormalization; it does not justify
a history cutoff, a missing-to-N/A conversion, or ranking permission.

`VERSION_MISMATCH` and `CALCULATION_ERROR` fixture tokens remain numerically
admitted. These are carrier/control counterexamples, not an actual replacement
method execution. Provider-run future bars/filings are excluded in the bounded
synthetic replay; direct future-stamped `analyze_raw` still produces a number.
Neither result proves full PIT across all entry points or real archived sources.

## Descriptor and consumer consequence

The previous inactive descriptor uses `implied_growth` for reverse DCF; the actual
public RawFundamentals field is **`reverse_dcf_implied_growth`** (`implied` is a
local variable). The lane's additive correction is appropriate: preserve the
old descriptor bytes/history and add the corrected source-bound input alias,
without pretending a production method registry now exists.

Seven records with null registered method IDs/versions remain source
characterizations. Their economic raw fields, selected branches, exact periods,
availability, source vintages and ordered normalization/reduction need explicit
refs. No old result may be certified as exact factor-method PIT solely from this
manual descriptor.

The consumer report separately distinguishes absent assessments, projected
metadata and retained-but-unused legacy coverage. Existing hash/identity/weight/
PIT/provisional-state guards are preserved. The narrow future adapter consumes
producer assessment refs after current persisted validation and before cohort
selection; method semantics are never implemented again inside the Leaderboard.

## Decision surface

Keep **V1** as intended valuation/normalization families (including source/fallback,
peer and own-history meanings) and **V2** as metadata/assessment methodology.
V1 needs exact economic inputs and G horizon/fallback dependencies where shared.
V2 depends on approved B4/B7 and the unapproved B2/B3/B5/B6 bundle; exact validity
criteria depend on actual method/requirement authority. Both remain unapproved
for production, with no numeric default or policy activation.

No V family wins by this review. Independent D1/D2 work can next converge
scope-preserving producer/consumer assessment references and exact model-input
availability/units. Production migration, Official weight, Composite, runtime
WeightOverride and historical recalculation stay D3. Manual review adds zero
actual scheduler hops.
