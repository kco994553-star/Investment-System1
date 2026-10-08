# Missing-Data policy comparison and recommendation

**PROPOSED / NOT_APPROVED / INACTIVE / SPEC-ONLY.**

This document recommends a policy design for a separate user decision. It does
not authorize a new enum, production evaluator, denominator, ranking gate,
normalization, cutoff, confidence formula, migration or merge. Original results,
fixtures, weights, history, Official/Personal boundaries and Holdout are preserved.
Synthetic examples describe candidate consequences, not calibrated investment
evidence or new numeric defaults.

## Evidence and scope

Reviewed source tree: `11cd2f5ac545af54d943dc206396c1fb6926689c` in the
QGV Missing-Data worktree. `git diff b8e39a2 HEAD -- implementation/src` has no
changes. Thus the current production observations below match the original
Common Contract audit without repeating remote recovery or golden capture.
The root fresh-read evidence establishes PR/CI/integration authority separately.

| Ref | Repository evidence | Finding used here |
|---|---|---|
| P1 | `implementation/src/investment_system/qgv/scoring.py:24–57,60–65,120–128` | Q/G/V prior accumulate fixed weighted contributions, skip missing, never divide by available weight, block on an applicable blocker or no used weight |
| P2 | `implementation/src/investment_system/qgv/scoring.py:68–117` | V candidate requires all seven numeric observations; excludes only MISSING_DATA/BLOCKED_DEPENDENCY/PIT_UNAVAILABLE among numeric states |
| P3 | `implementation/src/investment_system/qgv/factors.py:42,103–117` | Financial ROIC is excluded before its observation is read; N/A is omitted by prior but admitted by candidate when numeric |
| P4 | `implementation/src/investment_system/contracts/enums.py:10–30`; `contracts/models.py:74–81` | Existing quality/coverage vocabulary; no independent requiredness/applicability/reason fields or observation value validator |
| P5 | `implementation/src/investment_system/qgv/analysis.py:42–63,89–116` | Current total uses partial Q/G if numeric; V confidence/coverage copy quality; displayed effective weight is not actual admitted weight |
| P6 | `implementation/src/investment_system/qgv/leaderboard.py:30–54` | Consumer sorts supplied scores, including partial totals, without a completeness admission filter here |
| P7 | `implementation/src/investment_system/pit/resolver.py:21–38`; `providers/memory.py:20–29` | Both available_at and published_at must be no later than decision time in provider selection |
| P8 | `implementation/src/investment_system/personal/weights.py:145–187` | Existing immutable weight resolution, no silent base rebase or missing-weight redistribution; runtime QGV binding remains absent |
| P9 | `implementation/docs/qgv_common_contract_vnext/CONTRACT.md` | Separate presence/applicability/PIT dimensions; legacy replay; no invented confidence/coverage method; namespace/version isolation |
| P10 | `implementation/docs/qgv_common_contract_vnext/AUDIT.md`; `COMPATIBILITY.md`; `golden_cases.json` | Existing 71 synthetic cases and arithmetic anchors; historical preservation is mandatory but does not endorse old economics |

Previously delivered `MISSING_DATA_DECISION_SURFACE.md` and `DECISION_REVIEW.md`
are hypotheses and review history. The current source confirms their core
observations. This recommendation adds a concrete distinction between method
validity, score completeness and Official ranking admission; a coverage label
alone does not address missing-data selection bias.

## Current mathematical issue

The prior reducer emits `sum(w_i * score_i)` over admitted applicable factors.
Its `used` value decides coverage status; it is not a denominator. Missing is
not an observed zero, although a missing positive-weight contribution decreases
the emitted sum for scores in the declared nonnegative scale. Financial N/A also
decreases the represented weight: the existing all-70 financial fixture gives
Q=56 even though every economically applicable Q factor is present (P1/P3/P10).

The candidate loop withholds its entire result for an absent factor, but admits
numeric N/A. Both paths currently accept several numeric integrity labels and
do not themselves validate finite/range constraints (P2/P4). These are current
findings, not approval to use such inputs. Provider PIT guards exist, while direct
observation/raw entry has weaker preconditions; a shared future contract must
specify admission at every supported entry point rather than rely on one caller.

Two independent questions are therefore necessary:

1. Is the method valid for this subject and evidence at decision time?
2. Is the emitted number a complete, comparable estimate for the declared method,
   profile and planned denominator?

An optional missing factor can leave the method valid but its weighted result
incomplete. A required identity/PIT dependency can invalidate the method even
when its scoring weight is zero. Calling both conditions “PARTIAL” loses this
distinction.

## Policy alternatives

| Candidate | Precise interpretation |
|---|---|
| A — Fail-Closed | Withhold an axis score when a declared required applicable dependency is absent or inadmissible. Blanket “every registry item is required” is a stricter variant, not implied by A. Optional missing still needs a denominator/output rule. |
| B — Observed-weight renormalization | Omit unavailable factors from numerator and denominator, and divide the remaining contribution by observed weight. Requiredness and PIT validation must still be enforced separately. |
| C — Fixed partial contribution + Coverage | Keep the planned denominator, emit admitted contributions as a partial result, and independently disclose absent evidence. Whether partial values may enter Official rankings is another policy decision. |
| D — Requiredness/applicability hybrid | Resolve applicability and method-requiredness independently of weights; validate admitted inputs; use a planned applicable denominator; missing never changes that denominator; preserve diagnostics but withhold incomplete new Official comparable scores. |

No alternative includes a new default weight, coverage cutoff or confidence
multiplier. A and C are incomplete policy families until their missing reason,
scope, denominator and consumer rules are specified. D is recommended below as
one explicit combination, with separate approval clauses so its financial
denominator and ranking changes cannot be silently bundled into metadata work.

| Investment-model dimension | A — Fail-Closed | B — Observed renormalization | C — Fixed partial + Coverage | D — Recommended hybrid |
|---|---|---|---|---|
| Mathematical consistency | Consistent completeness rule after required set is fixed; optional denominator unresolved | Mean of observed scores; estimates a changing factor mix, not the original complete model | Consistent contribution accounting; partial is not a full-scale estimate | One planned applicable model; complete score and partial contribution are distinct outputs |
| Q/G/V comparability | Possible only with shared requiredness/admission plus axis-specific method meaning | Different missing sets produce different effective models and cannot be assumed comparable | Same planned scale, but missing weight depresses contribution; comparable complete/partial mixing remains unsolved | Within a pinned complete policy/profile; cross-axis/sector economic calibration is still not proven |
| Legacy/historical compatibility | New nulls/admissions can differ; archive exact | Can change scores/ranks; archive exact | Closest to prior arithmetic, but new integrity/admission gates can differ | Archive exact; only a separately approved new version has changed denominator/admission |
| Sparse-data bias | Selection attrition; could over-exclude otherwise useful partial evidence | Can reward selective availability and omitted weak factors | Penalizes sparse data numerically; labeling alone does not remove ranking bias | Keeps evidence visible; avoids incomplete Official ranking, but reports excluded cohorts to expose selection bias |
| Young-company bias | Insufficient history may block more young firms | Short-history firms may receive inflated scores when weaker history factors disappear | Smaller contribution often penalizes short histories | Explicit history reason and method scope; no silent N/A shortcut; new young-company method requires separate evidence |
| Financial-sector bias | Blanket required ROIC blocks financial firms incorrectly | True N/A and accidental missing may be conflated | Prior fixed contribution depresses financial Q maximum | Proven financial N/A excluded from planned denominator; residual economic sector comparability still needs validation |
| Other sector bias | Required set may fit some industries poorly | Sector-specific missingness changes the model mix | Persistent missingness depresses certain sectors | Versioned applicability, preserved unavailable reasons and explicit cohort attrition |
| Gaming/manipulation | Can induce score disappearance or cohort exclusion | Hiding low values can raise score without improving the firm | Cannot raise a bounded nonnegative fixed contribution by hiding a factor, but labels cannot rescue selection/rank semantics | No observation-driven denominator; policy-bound N/A; incomplete numbers cannot be promoted into Official rank |
| PIT/no-lookahead | Safe only if validation is independent of missing decision | Unsafe if PIT rejection merely removes a factor and a normal score survives | An illegal input can still be omitted into a normal-looking partial number | Refuse illegal evidence, preserve both time guards, block complete admission at affected scope; diagnostics do not legalize PIT failure |
| Ranking/Leaderboard | More null/unranked entries; cohort composition changes | Rank can improve after losing weak evidence | Partial scores can be ranked downward unfairly if mixed with complete ones | New Official ranking accepts complete results of accepted comparable versions; diagnostics stay outside normal score ranking |
| Personal/Official isolation | Safe if namespace and pinned policy remain distinct | Weight/policy changes must stay Personal; no override of Official admissions | Safe only with explicit result kind and immutable namespace | Same evaluator contract, pinned policy refs and immutable Official authority; Personal zero weights never edit Official requiredness |
| Migration complexity | Medium once requiredness is specified | High: missingness, factor-mix and cohort effects need validation | Lower arithmetic cost, substantial consumer/status work | Medium/high: definition registry, admission trace, typed result and consumer/version gates |
| Explainability | Simple withholding, but reason and scope must be shown | Can conceal redistributed influence unless full trace shown | Clear contributions, but partial result can be mistaken for low merit | Explicit excluded/N/A/missing/blocked ledger, planned denominator, result kind and rank eligibility |

### Selective missingness counterexample

For two positive weights `a` and `b`, observed scores `H > L`, and complete score
`(a*H + b*L)/(a+b)`, hiding the low-score factor yields observed-weight estimate
`H`, which is larger. There is no assumption that missingness is random in
financial reporting or provider coverage. A warning label or weighted coverage
ratio does not mathematically remove that increase. This is why B is rejected
for a generic comparable Official score in the recommendation. A later approved
missing-data estimator would need its own evidence, version and publication
policy; it is not disguised as basic aggregation.

Under C, hiding a bounded nonnegative factor cannot increase the fixed
contribution, but losing data can still change selection eligibility, comparisons,
rank ordering and cohort composition. Declining scores caused by missing data
are not proof of declining business quality. Complete and partial numbers should
not be mixed into a normal Official ranking without a separately approved model.

## Recommended integrated policy — M1 through M5

The following five decisions are the minimum independent approval clauses.
They are a coherent recommended bundle, **not approved values or live policies**.
The approved scope may cover these abstract rules first; runtime stays blocked
until a method/profile-specific factor and dependency declaration is complete.
Existing factors are not assigned new roles by this document.

### M1 — Requiredness and applicability

**Current:** the financial profile excludes ROIC, but factors otherwise have no
declared required/optional/conditional contract; one quality state can carry N/A
(P3/P4).

**Proposed:** a pinned method/profile declares which evidence is method-required,
which is optional, and any decision-time conditional requirement. Applicability
is a separate economic predicate. A proven N/A factor is excluded from the
planned active scoring set. Applicability cannot be inferred from null value,
provider outage, short history, future availability or low confidence. An unresolved
predicate or missing definition/configuration blocks complete new admission;
it is not assumed N/A or applicable. Conditional predicates must themselves use
PIT-eligible evidence. No registry-wide default “all required” is introduced.

**Why / alternatives rejected:** a blanket all-factor rule incorrectly blocks
financial applicability and unused optional metrics. Treating missing as N/A
changes model weights based on availability and enables gaming. An observation's
N/A label alone cannot override the pinned definition/profile: disagreement is
an applicability conflict needing resolution, not silent denominator removal.

**Impact:** legacy replay exact; new validity/eligibility may differ. Financial
and young-company classifications need evidence; old history remains literal.
Custom weights do not edit Official definitions. Declaration design is within
the current inactive audit authority; Official role/applicability activation is
**D3-P/user approval**, with method-specific table and migration evidence.

### M2 — Reason-specific admission and hard-failure scope

**Current:** prior omits MISSING_DATA/PIT_UNAVAILABLE/N/A, globally blocks an
applicable BLOCKED_DEPENDENCY within its axis, and admits numeric integrity
states; candidates disagree on N/A (P1/P2/P4).

**Proposed:** retain existing QualityState and structured reason evidence without
inventing a mandatory new runtime enum. Ordinary absence, source unavailability
and insufficient history refuse that factor's contribution and disclose its
cause. They do not become N/A. Unavailable required evidence fails method validity;
unavailable active optional evidence leaves only an incomplete diagnostic.

Input/value/identity/version/calculation integrity and PIT must be checked before
any admitted contribution. Known future data, ambiguous identity, incompatible
calculation version or invalid admitted value cannot be legalized by omitting a
weight. Preserve `available_at <= decision_time` **and**
`published_at <= decision_time`, plus existing source/vintage/provenance guards.
Unknown PIT evidence is not permission to consume latest data.

Scope must follow the dependency graph:

- Shared subject identity, required configuration, required source authentication
  or a corrupted common dependency can block the affected evaluation.
- A factor-local required dependency failure blocks the affected axis/method.
- An unavailable optional active factor cannot contribute or receive complete
  Official admission. A known integrity failure in evidence that the calculation
  consumed must be a visible hard failure at the affected scope.
- An independently excluded, optional, unconsumed input is outside that scoring
  dependency set. Its unused malformed/future payload does not automatically
  contaminate every unrelated axis. Exclusion must be established by the pinned
  policy before looking at its bad value, and retained in the trace.

Do not claim IDENTIFIER_CHANGED is always invalid: a verified effective-dated
identity mapping may resolve it. Numeric CONFLICTING_SOURCE, STALE_DATA and
ESTIMATED_DATA are not automatically approved or rejected here; their method-bound
acceptance/resolution rubric remains unresolved, with no invented age/confidence
cutoff. Until that policy is resolved, a new complete evaluation may not silently
inherit today's permissive admission as a certification.

**Why / alternatives rejected:** one “missing” bucket hides integrity; global
blocking on every unused payload creates unnecessary attrition; zero-weight/PIT
renormalization permits evidence bypass. Evidence is required at its real scope.

**Impact:** legacy replay exact; a new version can reject formerly numeric results
and change score availability/ranking. No retrospective invalidation or history
rewrite is implied. Entry-point validation, reason/admission matrix and lineage
closure are migration prerequisites. Narrower enforcement proposals still need
**D3-P/user approval** where Official admission changes; existing PIT protections
are preserved, not weakened.

### M3 — Planned denominator, N/A exclusion and no missing-driven reweight

**Current:** prior uses fixed contributions with no observed division; financial
N/A weight is not redistributed. Candidates require the full existing seven-weight
set (P1/P2/P3).

**Proposed:** define a planned denominator from the approved applicable active
factor weights under the exact profile/configuration, before availability is
considered. A proven policy-bound N/A factor is excluded from this set. Ordinary
missing, source unavailable, insufficient history, PIT rejection or invalid value
does **not** shrink this denominator. A complete new axis score uses this planned
applicable basis; incomplete admitted contributions retain that basis as
diagnostics, never an observed-factor mean. This is applicability normalization,
not missing-data renormalization.

If the planned denominator is zero (all N/A, all approved scoring weights zero,
or a structurally disabled axis), emit no numeric axis score. Never emit a fabricated
zero, default score, divide by zero or equal-weight fallback. Explain whether the
axis is excluded by configuration, economically N/A or unresolved. The existing
composite is unchanged; future excluded-axis propagation is a separate gate.

**Why / alternatives rejected:** B changes the model when data disappears. Keeping
financial fixed-denominator contribution as a complete 0–100 comparable score
preserves a known scale penalty. A new method may deliberately retain that scale,
but it must be labeled and compared as its own approved contract.

**Impact:** on the existing uniform-70 financial fixture, applicable normalization
would produce a new complete-basis value of 70 rather than legacy contribution
56. Stored factor weights would remain unchanged, but dividing by the smaller
applicable denominator increases the effective contribution of the remaining
factors. This is real redistribution through the denominator and requires the
same explicit semantic approval as a result-affecting weight/aggregation change;
it is not a score-neutral alignment or authorization to edit stored weights.
Applicability normalization does not prove
economic comparability across sectors; real cohort/PIT/OOS checks are required
before promotion. **D3-P/user approval** is required for the new denominator and
all resulting Official score/rank changes. Legacy path/history remain exact.

### M4 — Diagnostic contribution, coverage and complete-score admission

**Current:** numeric partial Q/G enter the current Q/G mean and current sorter;
coverage does not gate that sorter. V table uses quality as coverage/confidence
(P5/P6).

**Proposed:** retain partial admitted contributions and detailed omissions as
diagnostics, but a new comparable Official score requires both method validity
and completeness of all applicable positive-effective-weight scoring factors.
Missing optional active evidence therefore does not necessarily invalidate the
method; it does make the weighted score incomplete. Such a diagnostic does not
enter the new normal Official ranking/Leaderboard. Missing required evidence
additionally fails method validity, even if its contribution weight is zero.
No fractional coverage threshold is selected. Any later permission to rank a
partial estimate is a separate estimator/ranking policy decision.

Coverage views must remain distinct:

| View | What its denominator means | What it must not imply |
|---|---|---|
| Required evidence inventory | Exact method-required dependency IDs, with declared unit/count and admitted/missing sets | A weighted percentage cannot hide a missing required identity or zero-weight requirement |
| Scoring support | Planned applicable active weight and admitted support under the pinned configuration | High observed score support is not proof that required evidence or PIT is valid |
| Optional evidence inventory | Declared optional IDs/periods and availability reasons | Optional availability is not automatically a confidence formula |
| History/source coverage | Declared periods, source scope and vintage availability | It cannot be substituted for factor-weight support |

A ratio is meaningful only when its method, unit and denominator are declared;
this design introduces no universal published percentage formula. Confidence is
the reliability assessment of admitted evidence under an independent method.
Keep it UNASSESSED where that method is absent. Confidence is not a multiplier
or completeness substitute. Existing V metadata correction remains a separate
semantic issue; this decision does not approve a new confidence generator.

**Why / alternatives rejected:** partial labels alone do not solve comparability
or gaming. Blanket requiredness is unnecessary when completeness is a distinct
gate. An arbitrary coverage cutoff is unsupported. A separate partial research
display can retain valuable young-company information without inventing Official
rank equivalence.

**Impact:** legacy scores/boards remain exact. The new comparable cohort can be
smaller and rankings differ through admission; cohort attrition by sector, age,
source and reason must be reported before promotion. Existing TrackRecord is
preserved; new linked records only. New result kinds, consumer gates and version
acceptance need explicit implementation authority and **D3-P/user approval**.

### M5 — Zero weight, excluded evidence and Official/Personal isolation

**Current:** prior still inspects zero-weight observations and can block on them;
current V candidate constraints reject zero weights. Personal tree is not wired
to QGV (P1/P2/P8).

**Proposed:** zero effective scoring weight removes scoring contribution and its
weight from active scoring support. It does not turn evidence into missing or N/A,
and does not remove method-requiredness, applicability or shared input validation.
A factor's role remains determined by the pinned method, not by a user's slider.
Required/PIT/identity/configuration evidence cannot be evaded by setting zero.

Optional, genuinely unconsumed inputs under a predeclared zero-weight profile may
be excluded without a false global failure; retain their exclusion reason and
policy reference. This means an optional input may be unrequested in advance by
the pinned profile. It does not mean a factor already evaluated or provided as
part of the submitted decision lineage can have its known contamination erased
afterward by changing its weight to zero. Invalid independent extras are
quarantined as unconsumed inputs rather than silently relabeled admitted evidence.
If evidence was used to derive a factor, condition, applicability,
normalization, peer set or configuration, it is consumed even when that factor's
final direct contribution is zero. It remains subject to the corresponding guards.

Custom overrides operate only in their authorized namespace using the existing
immutable tree. They never change Official roles, policy, validity, registry or
publication. A Custom positive/zero weight changes only its pinned Personal
scoring-support set; comparisons across configurations are not automatically
Official rankings. An all-zero axis has no numeric result (M3). Runtime wiring,
Official weight authority and composite treatment remain separately unapproved.

**Why / alternatives rejected:** zero as a universal requirement bypass weakens
PIT; zero as a requirement for every unused metric causes avoidable false blocks.
The dependency/consumption boundary resolves both without a second weight engine.

**Impact:** current positive-weight Official behavior stays exact; future Personal
results may intentionally differ after separate authorization. Runtime isolation,
source trace, cache/storage key and namespace tests are required. Policy design is
authorized here; Official/Personal boundary or admission change and runtime
activation require **D3-P/user approval**, not implied by this recommendation.

## Minimum approvals versus unresolved bindings

Approve policy choices M1–M5 separately or as explicitly enumerated clauses;
do not approve an unspecified “hybrid.” The proposed bundle can be approved as a
**design contract only** without approving runtime activation. A production-ready
binding must additionally identify:

- Factor/method/profile-specific required, optional and conditional dependencies;
  no new assignment is made to the existing 20 factors here.
- Proven applicability predicates, including the financial ROIC rule and resolution
  of contradictory N/A observations; predicates retain decision-time provenance.
- Per-state, per-entry-point admission and failure scope, including resolution of
  stale/estimated/conflicting-source and effective-dated identity changes.
- Exact legacy/new calculation and denominator refs, allowed namespace, result-kind
  and ranking-consumer compatibility; no mixed-version board by implication.
- Migration evidence: old golden replay exact, all intentional new deltas documented,
  complete/partial/blocked cohort attrition, sector/age/source bias and rank effects,
  real PIT/OOS before promotion, without consuming Holdout under this task.

If any binding is unresolved, keep the new runtime inactive. An approved abstract
contract is not a substitute for approved factor roles or a production config.
Audit and inactive docs are within current authority; none of M1–M5 is APPROVED.

## Dependencies and next gate

Requiredness depends on factor meaning: a 3–5Y forecast needs different evidence
from a revenue-YoY proxy, and EPS-only versus a valid cash-flow fallback changes
the required input set. M1–M5 set the common rules but do not settle those methods.

1. Review M1–M5 as the Missing-Data **design** gate, with explicit integrity/PIT
   scope; do not activate a factor registry with unresolved bindings.
2. Review G 3–5Y and EPS→FCF together for evidence dependencies, recording separate
   semantic decisions and leaving current proxies/fallback intact until approved.
3. Review V economic meaning/normalization and independently its contribution trace,
   coverage/confidence methods. Metadata specification may proceed in parallel.
4. Review a new composite only for approved participating axis methods, weights and
   admission policies. Current `(Q+G)/2` stays unchanged.
5. Resolve immutable weight/config/node-factor authority in parallel; runtime
   WeightOverride remains a separately approved implementation/isolation gate.

No policy recommendation selects a new numeric cutoff, default weight, confidence
formula, EPS fallback, V normalization or composite formula. Real-data validation
and production migration remain excluded from this decision package.
