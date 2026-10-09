# Method/Profile Binding + Consumer Admission Decision Package v0.1

**DESIGN_READY / RECOMMENDED_NOT_APPROVED / INACTIVE / SPEC-ONLY.**
M1–M5 are approved policy principles, not approval of the bindings below.
No production, schema migration, actual method replacement, legacy rescoring,
Official promotion, grant, Holdout, PR44/canonical merge or paid use is authorized.
Intake authorities and existing CI are in [fresh_intake.json](fresh_intake.json).
The delivery HEAD is the owner ref; it is deliberately not a self-referential hash.

## Evidence and independent reviews

- [Factor role audit](FACTOR_ROLE_AUDIT.md), [factor inventory](factor_roles.json),
  [applicability audit](APPLICABILITY_AUDIT.md).
- [B4 independent review](B4_REVIEW.md), [six adversarial cases](b4_cases.json).
- [Consumer/profile review](CONSUMER_PROFILE_REVIEW.md),
  [consumer evidence](consumer_profiles.json).
- [Automation audit](../automation/CONTINUATION_AUDIT.md),
  [continuation protocol](../automation/CONTINUATION_PROTOCOL.md).

These are evidence-backed recommendations. Source/code behavior is SUPPORTED
only as characterization; it does not establish semantic requiredness authority.
The existing 102×4 simulation and 71 golden cases remain read-only historical
evidence, not a new vNext acceptance oracle. New probes are synthetic and scoped.

## Minimal decision surface and independent verdict

Seven independently changeable policies remain useful. Collapsing them into one
approval would conceal the financial denominator, method and consumer effects.
The user can review them in three groups: identity/isolation (B4+B7), evidence
authority (B1+B2+B3), result use (B5+B6). A group approval cannot fill unresolved
factor values or authorize production. No numeric default or cutoff is supplied.

| ID | Recommended policy | Technical verdict | Adoption class |
|---|---|---|---|
| B1 | Roles belong to an immutable approved method/input declaration; no role inference from positive weight, field presence or current code usage | MORE_EVIDENCE_REQUIRED for actual factor roles; authority mechanism is recommended | D3 for actual roles; D1/D2 audit/design |
| B2 | One pinned subject/profile context for mapping and applicability; predicate evidence admitted independently; proof plus explicit exclusion permission required for N/A denominator change | APPROVE_RECOMMENDED for the modified proof/context contract; concrete predicates require more evidence | D3 for actual predicates/exclusion; D1/D2 trace/design |
| B3 | Identity/config/method and relevant/shared predicate/observation evidence admitted before weights; failure reason and dependency scope preserved | APPROVE_RECOMMENDED as a bounded principle, not an unreviewed source-quality rubric | D3 for runtime policy binding; D1/D2 verification |
| B4 | Factor identity and immutable method/version identity are separate references; input horizon, fallback and normalization participate in method content identity; result pins calculation/config/source lineage | APPROVE_RECOMMENDED for reference contract; actual method replacements remain separate | D3 for runtime binding/migration; D1/D2 inactive design |
| B5 | Numeric contribution, coverage, completeness, scoring validity, ranking and publication are independent assessments with policy/authority refs | APPROVE_RECOMMENDED; unresolved assessment cannot be silently true | D3 for assessment rules; D1/D2 design |
| B6 | Diagnostic display, comparable ranking, portfolio decisions and publication have explicit consumer-specific admission; preserve research disclosure versus Official/LIVE grant separation | APPROVE_RECOMMENDED for the modified scoped consumer matrix; actual criteria/adoption remain open | D3 for adoption and cohort/ranking rules; D1/D2 audit |
| B7 | Existing Personal registry/override/versioning changes permitted numeric weights/contributions only; no implicit method/role/truth/admission/Official mutation | APPROVE_RECOMMENDED; does not authorize runtime wiring or factor inclusion edits | D3 for wiring/editability adoption; D1/D2 comparison |

All verdicts describe **Work technical recommendation**, never user approval.

## B1 — Factor requiredness authority

**Current:** Q/G/prior reducers use fixed factors without a role declaration;
V candidates require all inputs algorithmically. Code-frozen weights and a loop
do not establish approved economic REQUIRED/OPTIONAL/CONDITIONAL assignments.
**Proposed:** reference a role declaration with authority, method/version,
input scope and deterministic conditional predicate. Unknown method semantics
preclude fixing roles. **Rationale:** otherwise weight zero or a mapper fallback
could alter evidence obligations silently. **Rejected alternatives:** all used
factors required; all low weights optional; roles chosen from toy simulations.
**Compatibility:** exact legacy behavior remains. **Score/Official impact:** no
current effect; future role rules can change validity/consumer inclusion even
without changing a scalar. **PIT:** predicate/shared inputs retain admission.
**Consumer impact:** completeness cannot be asserted until obligations resolve.
**Migration cost:** reviewed declarations and versioned bindings, not a new enum
engine. **Evidence gap:** factor semantic authority/maturity, especially G/V
proxies and Q7/C-03. Proposed roles are not production selections.

## B2 — Applicability / N/A authority

**Current:** bool financial ROIC exclusion and mapper profile come from caller
context; a complete dated classification proof is absent. An explicit pipeline
profile can differ from raw-map context. **Proposed:** reuse factor_applicable
and sidecar assessments with coherent context reference, policy/version, source
vintage, subject/period/reason, availability and reproducibility. A supplied N/A
label, missing input, unknown identity or profile override is insufficient proof.
**Rationale:** denominator exclusion changes effective weighting.
**Rejected alternatives:** missing→N/A; current sector label alone→proof; exclude
before checking evidence; automatic universal N/A exclusion.
**Compatibility:** preserve legacy output and context literally.
**Score impact:** synthetic financial numerator56 / registered1 =56 versus
numerator56 / planned0.8 =70 when ROIC weight0.2 has both proven N/A and explicit
exclusion permission. This is a 14-point conditional change, not rounding or
metadata repair. **Official/PIT:** new denominator admission needs separate
approval; latest classification cannot stand in for historical availability.
**Consumer:** old/new bases must not share an undifferentiated cohort.
**Migration cost:** predicate/context and exclusion ledger plus replay linkage.

## B3 — Evidence admission boundary

**Current:** provider guards available_at and published_at; direct raw entry has
different preconditions and reducers do not authenticate all quality reasons.
**Proposed:** resolve method/context/scope before predicates; admit predicate
dependencies before N/A/conditional roles; admit related observation evidence
before numeric contribution. Reference existing DataStamp, QualityState,
provenance, namespaces and Common Contract, retaining original reasons.
PIT/provenance/source/identifier/version/calculation failures cannot be turned
into passing evidence by zero, renormalization or downstream display.
**Rationale:** method inputs establish affected scope independently of weights.
**Rejected alternatives:** blanket failure of unrelated predeclared inventory;
retroactively dropping failed input scope; collapse all failure reasons into
ordinary missing. **Compatibility:** no historical reclassification.
**Score/Official:** blocked evidence can affect future validity/rank admission;
no current score changes. **PIT:** both time guards preserved, never retrieved
timestamp substituted. **Consumer:** blocked evidence can be retained as a
diagnostic trace, without a valid/rankable score claim. **Migration cost:**
reference admission traces and caller contracts; no duplicate admission engine.
Exact stale/estimated/conflicting-source rubric and failure scope remain open.

## B4 — Method/version binding

**Current:** FactorObservation lacks method identity and snapshots use coarse
versions; factor names coexist with YoY/fallback/proxy calculations. Generic
sidecar refs can describe lineage but current audit validation is not method
authentication or runtime enforcement.
**Proposed:** Factor definition ref → Method ref/version → Input contract ref
(units/period/horizon/source scope) → Applicability/roles ref → Result ref;
also pin normalization/fallback branch/arithmetic/calculation/config/source.
Existing ref shape id/version/sha256/locator is reused in a composed inactive
manifest, without changing old schema/example or adding a ProfileConfig.
A method version is immutable content. Reusing its ID/version with changed
content is a binding failure. A changed implementation ref must be recorded;
semantic method equivalence requires explicit evidence, never an automatic hash
inference. Selecting a new method requires a distinct pinned evaluation identity
and separate authorized calculation-version binding. Historical lookup uses old
pins and literal stored output, never latest-method substitution.
**Rationale:** stable factor name is a concept; it is insufficient calculation
identity. **Rejected alternatives:** factor rename alone; static global version
alone; latest method lookup; using Custom overrides to replace method refs.
**Compatibility:** absent method refs in old snapshots mean LEGACY_UNASSESSED,
not invalidated history or invented historical lineage.
**Score/PIT/Official impact:** metadata proposal changes none; actual horizon,
fallback or normalization replacement can change scores and remains D3.
**Consumer:** compare only explicitly compatible method/config/version cohorts.
**Migration cost:** additive source-pinned manifest and linked versioned results;
actual activation/backfill rules remain separately approved.

## B5 — Result validity and completeness

**Current:** scalar/null plus CoverageState and V metadata do not encode these
independent assessments. Q/G coverage does not prove V completeness/validity.
**Proposed:** preserve those legacy fields and add reference-based assessments
of contribution, evidence coverage, method completeness and scoring validity.
Consumer ranking/publication remains distinct. UNASSESSED stays unresolved.
**Rationale:** partial information is useful without acquiring decision authority.
**Rejected alternatives:** score non-null→complete; READY→valid V; Personal
actionable(PARTIAL)→Official rankable; a new invented minimum percentage.
**Compatibility:** no literal old field is repaired or overwritten.
**Score/Official/PIT:** no score effect now; assessment selection affects future
admission, must preserve rejected reasons. **Consumer:** display limitations
and expose accepted policy references. **Migration cost:** sidecar linkage, not
replacement of QGVSnapshot or translation of legacy READY into a new boolean.

## B6 — Consumer/ranking admission

**Current:** legacy Leaderboard ranks partial snapshots; producer mechanically
PASS records and P01 research publication are separate authorities. Empty active
grants do not authorize public/Official operation.
**Proposed:** Analysis/Personal may expose qualified diagnostics; research may
retain them with source/method/limitations and separate disclosure authorization.
Leaderboard needs explicit ranking acceptance and comparable method/version/
namespace cohort. Portfolio reference display is distinct from score-derived
allocation decisions. Track Record preserves original immutable payloads;
new records append references and do not rewrite outcomes. Web/API transports
the admitted state and authority, never converts non-null to eligible.
Publication requires its separately approved P01 route/grant; ranking does not
create publication permission, and a research PARTIAL grant does not create
Official/LIVE eligibility. **Rationale:** display, ordering and decisions carry
different meanings. **Rejected alternatives:** global ban on every partial
research disclosure; scalar rank; grant-free publication; Custom Official rows.
**Compatibility:** legacy replay/ranks retained and labelled as legacy.
**Score/Official impact:** new admission may change membership/order without
rescoring; no current board change. **PIT:** consumer cannot repair rejected
lineage. **Migration cost:** consumer adapter/policy versions and cohort evidence,
not a new cutoff. Exact rank/publication/adoption rules still require D3.

## B7 — Profile mutation boundary

**Current:** PersonalRegistry/WeightOverride enforce namespaces, versions,
editability and sibling weights; runtime QGV wiring remains absent. StrategyProfile
is a separate provisional advanced parameter pack, not a factor-method registry.
**Proposed:** permitted local weight changes affect numeric contribution/planned
weight accounting through existing tree only, under the same pinned method,
roles/applicability/admission. Zero is not removal from semantic obligations.
Factor inclusion requires its own authorized method declaration and is not
inferred from a zero override. No Custom method/role/truth/PIT/integrity/provenance
or Official ranking validity edit. **Rejected alternatives:** new ProfileConfig;
making override supply methods; silent Official fallback; assuming all factor
nodes editable because code accepts a tree.
**Compatibility:** preserve Official/Personal result namespaces and no rebase.
**Score impact:** actual override wiring would change Custom numbers, remains
unapproved; Official source/validity immutable. **PIT/consumer:** shared guards
and namespace-aware admission apply. **Migration cost:** resolve factor-node map
and C-24/C-30 authority, then separately authorize wiring.

## Dependency review — no cycle is authorized

| Order | Depends on | Output | Cycle guard |
|---|---|---|---|
| Method identity/context/input plan (B4) | Existing factor definition, immutable code/input refs | Declared method scope | Method selection never depends on result/weight/missingness |
| Policy refs and predicate input admission (B1/B2/B3) | B4 plan and authenticated authority | Resolved roles/applicability or explicit unresolved | Predicate inputs cannot depend on N/A exclusion/score |
| Observation admission (B3) | Declared input scope and predicate assessment | Independent eligibility/failures | Scope cannot change retrospectively after failure |
| Authorized numeric weights (B7) and M3 ledger | Resolved context, explicit exclusion permission | Planned basis and numeric contribution | Ordinary loss/zero never proves N/A or erases obligations |
| Result assessment (B5) | Roles/admission/method completeness policy | Separate partial/complete/valid states | Coverage cannot select its own requirements |
| Consumer assessment (B6) | B5 plus compatible cohort/namespace/publication authority | Ranking/decision/display/publication disposition | Rank cannot define method/roles or create grant |

Requiredness may reference method, while method declares its inputs; this is a
static declaration, not recursive runtime selection. The registry must resolve
the entire dependency graph before evaluation; unresolved refs or cycles fail
binding admission rather than trigger a default.

## M1–M5 adversarial cross-check

| Attempt | Required contract rejection | Preserved principle |
|---|---|---|
| Missing → N/A → smaller denominator → higher score | No admitted predicate proof or exclusion permission; planned basis unchanged | M1/M3 |
| Zero → waive REQUIRED or applicability | Role/predicate checks precede weights; obligation remains unresolved/failed | M1/M5 |
| Zero → PIT/integrity/provenance PASS | Relevant/shared failed evidence remains failed | M2/M5 |
| Custom → Official validity or method mutation | Immutable refs/namespace boundary; weight-only request cannot carry method replacement | M2/M5 |
| Partial diagnostic → rank/publication | Independent consumer policy/cohort/grant needed | M4 |
| Method change → same calculation binding | Content/version mismatch or missing authorized new evaluation binding | M2/B4 |
| Historical fetch → latest method rewrite | Original result/pin bytes retained; new result linked separately | M5/B4/history boundary |

The existing architecture does not enforce every row today. These are tested
design requirements, not a declaration that production has been repaired.

## Next semantic gate and migration

B4/B7 identity/isolation principles can be reviewed first without choosing new
factor methods. Then resolve **G 3–5Y and EPS→FCF intended-method semantics**
as separate choices in a common impact package before fixing their requiredness.
V normalization/method and V metadata are independent later decisions; the
research prior/candidates cannot be promoted by metadata correction.
Consumer contract design can proceed in parallel, but implementation requires
explicit B3/B5/B6 adoption and an authorized version/write set. Missing-data
runtime awaits actual B1/B2/exclusion/admission/result bindings plus migration
approval. Composite and production WeightOverride stay downstream.

Two finite D1/D2 automation verification tasks are specified in the continuation
protocol: source-pinned legacy replay manifest, then independent manifest closure.
They choose no method replacement, role, predicate, cutoff or consumer adoption.
After those tasks, stop at concrete D3 decisions instead of manufacturing work.

**Recommended user decision:** approve/amend only B4+B7 identity/isolation
principles as written here. This is not approval of runtime implementation,
calculation migration, individual factor roles, N/A exclusion or consumer rules.
