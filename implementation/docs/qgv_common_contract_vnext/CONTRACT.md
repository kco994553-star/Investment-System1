# QGV Common Contract vNext · 0.1

**INACTIVE / SPEC-ONLY. Runtime enabled = false.**

Authority: user instruction of 2026-10-04 20:23 KST authorizes audit, inactive
schema/spec, golden characterization, neutral tests and scoped delivery. It does
not approve this proposed contract as a production policy. No runtime wiring,
new aggregation implementation, new score, migration, grant or merge is enabled.

## 1. Objective and boundaries

Preserve the current Q/G/V results and history while specifying a shared domain
contract and a reviewable migration boundary. Reuse current identities, the
Personal weight tree, immutable versions and existing evaluator components.
No new ProfileConfig class or parallel weight engine is justified at this stage.

Current source baseline is `b8e39a2196a6d7794a04a0cd5393c68329e126ca`.
Integration comparison is `acaf1b5a82859ac2750a130ebe88f8b4d272ac66`.
The QGV, Personal and StrategyProfile code is identical at those two trees.
`current_factor_map.json` records 7 Q, 6 G and 7 V factors and existing candidate
weights. These are observations, not a new authoritative Official dataset.

## 2. Minimal hierarchy and identity

QGV -> axis Q/G/V -> existing stable factor ID -> optional subfactor references.
Current factors have no first-class subfactor tree, so `subfactors=[]` means
**not defined**, not an implicit single metric or equally weighted children.
Raw fields are metric inputs, not automatically subfactors. Each factor definition
has axis, stable ID, immutable definition version/hash, economic meaning, supported
subject scope/profile, metric refs, optional ordered children, normalization ref,
aggregation ref and applicability policy ref. Semantic split/merge requires new
IDs and an explicit migration map; a display rename does not change identity.

Financial applicability is an intended domain difference. Shared structure must
not force financial ROIC applicability or erase sector-specific meaning. The
current 7 V IDs remain pinned: fundamental_value, peer_relative_value,
historical_valuation, sector_context, theme_premium_discount, reverse_dcf,
margin_of_safety. A Growth-adjusted factor has no current 1:1 mapping; it is not
silently added or funded by redistributing existing weights.

## 3. Data and result contracts

| Element | Required semantics | Current binding / unresolved part |
|---|---|---|
| Subject | Existing issuer/company/security/listing identity, exact scope | Reuse current IDs; no ticker inference or company/security equivalence |
| Raw metric | Metric ID/version, original value/unit, economic period, source field | RawFundamentals and source artifacts; raw_map currently places normalized score in FactorObservation.raw_value |
| Normalized input | Value, unit/scale, direction, normalization policy/version, input refs | Existing raw_map transform remains pinned; no new transform or default |
| Factor result | Stable ID/version, nullable score, score scale, method ref, input refs, applicability and original quality | Existing FactorObservation as historical payload; never recover raw metric by inverting a clipped score |
| Axis result | Q/G/V, component contributions when available, aggregation ref, score-kind, coverage and confidence | Historical score is copied without recomputation |
| Weight | Local weight, origin OFFICIAL/OVERRIDE/UNSET, parent, exact registry/version | Reuse Personal effective_tree; global weight is derived along path, not editable |
| Confidence | Assessment state, qualified level, method/rubric ref, evidence refs, limitations | Not QualityState or coverage; no default MEDIUM is invented in the new metadata |
| Coverage | Assessment state, declared numerator/denominator units, method ref, optional ratio, missing reasons | No universal percentage formula, cutoff or threshold selected; legacy state retained separately |
| Provenance | Source ID/version/hash/locator, vintage, raw stamp, transformation and calculation refs | Preserve raw data outside the sidecar; reference rather than copy/rename evidence |
| Time | as_of, decision_time, available_at, calculated_at, source publication and economic period where available | Different meanings; fetched_at/calculated_at never substitute for available_at |
| Calculation | Exact scoring-contract/version, source identity, policy refs | Source divergence is reported; never normalize source hash to appear unchanged |
| Configuration | Immutable binding manifest of existing versioned refs | No new runtime class, parser, default registry or mutable settings store |

The JSON schema is a **documentation sidecar shape**, not a new QGVSnapshot,
producer API or public evaluation request. A sidecar references the legacy
snapshot and preserves its score as `legacy_score`, including legacy out-of-range
values. It does not assert that such a value is admissible as a new 0–100 score.
Structured/qualitative source inputs remain referenced artifacts; the sample
input projection only covers scalar numeric metrics. Unsupported shapes are
explicitly outside this example, not guessed/coerced.

The minimal proposed state representation separates:

- value presence: PRESENT / ABSENT / UNASSESSED;
- applicability: APPLICABLE / NOT_APPLICABLE / UNASSESSED;
- original legacy QualityState and reason codes (unchanged);
- PIT admission: UNASSESSED / ELIGIBLE / INELIGIBLE;
- methodology maturity, namespace and publication authority (separate refs).

INSUFFICIENT_HISTORY and SOURCE_UNAVAILABLE remain evidence-backed reason codes,
not automatically new scores or aliases for NOT_APPLICABLE. INVALID integrity
is different from absence. No lossful many-to-one conversion of legacy states is
approved. Unknown metadata stays UNASSESSED/null with reason, not low confidence,
zero coverage, zero score, or pass. A missing policy/config is different from a
missing company observation and must block new evaluation until resolved.

## 4. Time/PIT contract

Every future admitted evaluation must satisfy `available_at <= decision_time`
for every required input under its pinned PIT policy and retain source/vintage
authentication and revision limitations. `as_of` is an economic/view basis, not
proof of availability. Date-only periods remain dates. Availability known only
as a date/interval may be retained in referenced evidence, but is not coerced to
midnight; this minimal scalar sample cannot mark that input ELIGIBLE. Missing or
ambiguous time/provenance cannot be repaired with fetched_at or latest data.

The audit-sidecar validator checks time awareness, equality boundary, explicit
source/vintage references and future timestamps. It does **not** authenticate
remote artifacts or prove a full PIT lineage closure. Its SPEC_VALID means only
structural consistency. Synthetic sample refs never establish real PIT/Official.
SEC restatement limitations are preserved. Contract tests are not real PIT/OOS.

## 5. Weight architecture and precedence (design only)

OfficialRegistry version + Official calculation/policy version -> Official QGV
snapshot -> its Official Leaderboard/TrackRecord namespace.

Same pinned registry + PersonalStrategyVersion + immutable WeightOverride ->
effective local/global tree -> future personal evaluator request -> Personal QGV
view/records in a distinct namespace. No global mutation and no silent rebase.

Resolution precedence for an authorized custom namespace is: valid explicit
override for editable node; otherwise weight from the exact pinned registry;
otherwise UNSET. No fallback to current/latest Official. Override is rejected in
OFFICIAL, on LOCKED/UNRESOLVED/non-WEIGHT nodes, or when maturity does not permit
the requested namespace. Sibling sum and range enforcement reuse existing
Personal rules and their pinned tolerance; no new epsilon is chosen here.

The factor-to-node binding must be explicit, complete and versioned. Factor IDs
do not automatically become editable production nodes. C-30 authoritative weight
and maturity evidence is required. Structural GROUP nodes are not automatically
editable WEIGHT nodes. A parent zero may retain child local mix; effective global
contribution is zero. Absent weights are not redistributed.

Target UX has L1 axes and L2 factors. Advanced metric weights are only exposable
if a real approved weighted metric layer exists. This spec does not create one.

Binding manifest references: registry/version/hash; PersonalStrategyVersion ID;
override_set_hash; base Official strategy version where authority exists;
existing StrategyProfile parameter_set_hash as AdvancedParameters if applicable;
scoring/normalization/aggregation/applicability/missing policy refs; node-factor
map; namespace and subject/time scope. The manifest contains **references**, not
a duplicate weight dataset or new independent configuration engine. Unresolved
refs remain unresolved and cannot activate scoring.

## 6. Shared aggregation — feasibility, not implementation

Q, G and V prior already share `_weighted`. V candidates use a different loop.
Shared arithmetic is possible only after admission/completeness semantics are
explicitly aligned or intentionally versioned. Do not hide current differences
behind a large axis switch statement or call candidate results equivalent today.

Proposed input: ordered eligible factor-result refs + resolved local weight refs
+ applicability/missing policy ref + normalization/calculation version + namespace
and complete input lineage. Normalization occurs before aggregation; the reducer
does not select units, peer sets, growth periods, factor roles or raw mappings.

Proposed output: nullable score + score-kind (complete score versus partial
contribution), original component states/contributions, coverage assessment and
method, confidence assessment and method, input/config/calculation refs, PIT
decision and limitation reasons. Confidence is not a multiplier. Coverage is not
implicitly confidence. Metadata cannot silently reweight scores.

The arithmetic must preserve documented order, arithmetic primitives and rounding
for a legacy-equivalent path. Do not replace `sum`/loop accumulation by fsum or
reorder factors without checking exact expected outputs. Missing-policy choices
(partial contribution versus withheld score, applicable denominator, renormalize
or no renormalize, zero-weight requirements, completeness) remain proposals that
require a separate decision if changing results. No coverage cutoff is selected.

Future Official and Custom requests under the same approved calculation version
use the same evaluator. Archived legacy-version replay remains available by exact
version dispatch; this does not justify separate Official/Custom engines.

## 7. Composite and score kinds

Current Q/G/V scores are separate. Current total is `round((Q+G)/2,4)` when both
are not null; current attractiveness is `round(((Q+G)/2)/10,2)`;
type_adjusted_score_100 is currently the total unchanged. V does not enter total.
These are observations of current behavior, not freshly approved formulas.

Future composite must name participating axes, scale/direction, resolved weights,
completeness policy, arithmetic/version and lineage. The proposed V integration
formula and axis weights are **UNRESOLVED / INACTIVE**. No `(Q+G+V)` rule is chosen.
Profile-adjusted score must identify its profile and transformation; personal
score additionally identifies namespace/override version. Do not label current
unadjusted total as a proven type-calibrated result. Mixing versions or namespaces
in a leaderboard requires an explicit separate compatibility policy.

## 8. Verifiable isolation invariants

1. Changing a Personal override leaves the Official registry bytes/hash unchanged.
2. Existing Official snapshot, board and track-record semantic hashes unchanged.
3. Official evaluator inputs cannot contain a Personal override set.
4. Custom result ID/cache/storage/ranking scope includes namespace, registry,
   calculation and override-version refs; cannot overwrite Official keys.
5. Missing binding or stale base version rejects, never silently rebases.
6. Old TrackRecord payload is unchanged; intentional migration writes a new
   snapshot/version and linkage, not an overwrite.

Current tests cover existing weight-tree isolation and unchanged synthetic
snapshot/board/record objects. Invariants 3/4 across a future runtime request,
cache and publication path remain a migration acceptance gate, NOT_TESTED now.

## 9. Migration gates and authority

G0 current source/fixtures pinned and characterized (this package).
G1 inactive schema/mapping/compatibility and negative contract tests (this package).
G2 approve exact affected contract and semantic decisions; no omnibus approval.
G3 implement adapter/evaluator binding only in newly approved scope, prove legacy
golden equivalence and future namespace isolation; preserve old version access.
G4 targeted/full integration, consumer version/hash acceptance and delta report.
G5 preregistered real PIT/OOS and data coverage/revision checks before new method
promotion; Investor weights additionally require 13F/PIT evidence and behavioral
OOS, not arbitrary defaults. Real CAL_VERIFY/Holdout needs explicit authority.
G6 separately authorized migration/publication/Official promotion/canonical merge.

See AUDIT.md and COMPATIBILITY.md for decisions, impact and frozen boundaries.
This phase stops after G0/G1 deliverables. No production migration starts here.
