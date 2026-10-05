# Missing-Data Implementation Contract vNext — reuse and boundary map

**INACTIVE / SPEC-ONLY / NO RUNTIME CHANGE.** This additive map implements the
documentation scope of the user's M1–M5 **principle-only** approval. It does not
activate production aggregation, select factor requiredness, choose a sector
taxonomy, set a numeric default/cutoff, authorize rankings, or migrate history.

Intake worktree: `ed907b8f5a046008319cddecc6ef40b9bd6759dc`. Production source
remains the pinned canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`.
Root-scoped evidence records fresh GitHub, PR #44 and integration identities.
This continuation reuses the existing current-behavior evidence; it does not
repeat Remote Recovery, regenerate golden results or re-audit all Q/G/V methods.

References below are relative to `implementation/src/investment_system/` unless
explicitly prefixed `implementation/`. Existing documents are historical
proposals/evidence, not automatic sources of additional approval.

## 1. Exact limits of reuse and approval

The existing Missing-Data proposal selected stronger implementation assumptions
in its simulation. Those assumptions remain useful sensitivity illustrations,
but **principle approval is narrower**:

- M1 separates economic applicability, method-requiredness and weight. Actual
  factor roles and conditional predicates remain to be specified and approved.
- M2 preserves distinction between ordinary absence and relevant/shared
  PIT/integrity/configuration failures. Failure scope must remain explicit;
  no blanket rejection of unrelated data is inferred.
- M3 prevents ordinary-missing-driven denominator reduction. Proven N/A
  exclusion **may** be permitted by a pinned policy; universal mandatory
  exclusion is not approved.
- M4 separates coverage, partial contribution, score validity/completeness and
  ranking eligibility. No coverage cutoff, all-positive-weight completeness
  rule, or partial-result ranking rule has been approved.
- M5 zero weight does not waive requiredness or relevant/shared admission and
  must not mutate Official authority. Actual editable nodes and runtime wiring
  remain outside this inactive implementation contract.

The 77 current snapshots, 18 reducer zero-weight diagnostics and 71 legacy
golden cases remain characterization of the old evaluator. The policy simulation
is not a vNext acceptance oracle. Any future regression plan must distinguish
approved invariants from unselected outcome rules.

## 2. Existing structures versus minimum missing expressions

| Component and exact source | Reusable expression | Current limitation | Minimal inactive addition / binding |
|---|---|---|---|
| `contracts/enums.py:10–23`, `contracts/models.py:74–81` | Preserve literal QualityState, factor ID, nullable raw/score, stamp ID and notes | One quality enum cannot express independent presence, economic applicability, requiredness, input validity and failure scope; null OK is possible | Reference original observation unchanged; expose separate assessments using the existing Common Contract representation and qualified reason evidence |
| `contracts/enums.py:26–30` | Preserve historical READY/PARTIAL/BLOCKED/SYNTHETIC coverage | Legacy READY does not prove valid V, complete evidence or ranking authority | Retain legacy coverage; reference new coverage/completeness assessment method independently, without reinterpreting READY |
| `qgv/factors.py:42,103–106` | Existing financial ROIC economic exclusion and factor IDs | Boolean helper knows neither unresolved applicability nor predicate evidence/version; all other factors default true | Bind the existing determination to exact policy/profile provenance; add an unresolved assessment in the inactive sidecar when authoritative applicability is not supplied, not a new sector rule |
| `qgv/raw_map.py:159–169` | Existing financial N/A observation and missing numerical mapper outcomes | Missing raw field collapses to MISSING_DATA; no independent history/source failure class; raw_value repeats normalized score | Reference original raw data/stamp and the existing map; preserve specific upstream reason without adding or aliasing runtime enum values |
| `qgv/scoring.py:24–57,60–65,120–123` | Ordered accumulation, existing dictionaries, no ordinary-missing renormalization and exact legacy coverage | Applicability skips before observation; integrity states other than BLOCKED/PIT can be admitted; no requiredness declaration or independent completeness | Keep legacy reducer unchanged; describe separate admission/role/basis/result records for a future version, without constructing a second weight engine |
| `qgv/scoring.py:68–117`; `qgv/factors.py:52–62,79–100` | Exact research candidate IDs, lifecycle, seven-factor constraints and complete-case legacy loop | Algorithmic requirement of all factors is not an approved economic role registry; numeric N/A differs from prior; no candidate coverage/confidence | Preserve candidate replay. Future candidate evaluation would consume the same policy inputs only after candidate-method compatibility is separately approved |
| `qgv/scoring.py:126–128`; `qgv/analysis.py:36–61` | Current V initial prior and Q/G composite | V candidate completeness cannot silently become production V; V is excluded from total | Pin calculation/composite/lifecycle references; no new formula, V promotion or score substitution |
| `contracts/models.py:34–50`; `pit/resolver.py:21–38` | Source/stamp fields; BOTH available_at and published_at <= as_of; existing provider selection | Time admission alone does not authenticate source bytes or full vintage closure; arbitrary direct raw entry bypasses provider selection | Reference raw/stamp/source/vintage separately; record admission result and its dependency scope; retain both time guards |
| `providers/memory.py:20–29,44–46`; `qgv/pipeline.py:21–50` | Provider returns no raw when no PIT-eligible record exists; direct raw path remains historical behavior | No universal new evaluation boundary or failure trace across all direct callers | Document caller preconditions and future authoritative admission boundary; do not strengthen or relax any existing runtime path in this phase |
| `personal/timecontract.py:18–43` | Time-aware available_at/decision_time invariant, no invented timestamps | No published_at field; observed_at <= available_at has a specific Personal meaning that cannot be imposed blindly on DataStamp.observed_at | Compose compatible time checks and qualified timestamp meanings; retain published_at independently; do not replace the provider resolver with this helper |
| `personal/versioning.py:13–22,44–59` | Existing result namespaces, content hash and referenced Provenance | Hash shape/content hashing does not prove source authenticity; retrieved_at is not available_at; Provenance lacks a complete input dependency/admission graph | Reuse immutable namespace/version/hash and provenance reference, compose with stamp/vintage and scoped dependency refs rather than creating a duplicate identity system |
| `personal/quality.py:8–28` | Existing Personal data-quality summary and explicit quality/confidence distinction | worst() is severity aggregation, not scoped admission; is_actionable(PARTIAL) is not QGV complete-score or Official ranking admission | Optional qualified Personal presentation mapping preserving source detail; do not use it as a scorer/completeness/ranking shortcut |
| `personal/weights.py:49–82,94–145,146–187` | OfficialRegistry, WeightOverride, immutable version, namespace/editability, sibling sum, unset no-redistribution and zero-parent contribution | Registry does not declare factor method-requiredness/applicability; QGV runtime remains unwired; C-24/C-30 authority gaps remain | Add a reference-only factor-to-node/method-policy binding manifest. No new weight store, engine, defaults, class or runtime connection |
| `contracts/strategy.py:19–35,46–83,139–145` | Existing version/hash-bearing parameter pack; frozen Q/G keys rejected | This profile is not the hierarchical factor-weight registry or missing policy | Reference as AdvancedParameters only where applicable; do not duplicate or repurpose StrategyProfile as a new QGV policy engine |
| `qgv/analysis.py:42–56,89–114` | Literal existing snapshot confidence/coverage/table and V status evidence | Snapshot coverage combines Q/G only; V metadata copies QualityState; effective_weight depends on numeric presence, not admission | Preserve old fields. Add separately qualified coverage/confidence/actual-contribution references only; no confidence formula or label repair in stored history |
| `qgv/leaderboard.py:29–34,43–55` | Existing ranking consumes snapshots without rescoring | It has no new validity/completeness/ranking policy admission check | Define a separate future consumer admission reference. Leave policy and ranking criteria UNRESOLVED; do not infer new rules from legacy ordering |
| `qgv/track_record.py:19–43,45–59` | Existing record creation, overwrite rejection and linked child outcome | New sidecars must not be presented as corrected old snapshots or retrospective rescoring | Reference original IDs/payload and append separately identified records if later authorized; no old bytes rewritten |

No wholesale replacement of QualityState with Personal DataQuality is justified.
For example VERSION_MISMATCH, IDENTIFIER_AMBIGUOUS and CALCULATION_ERROR must
retain their original reason and scope even if an independent presentation view
groups them. DataQuality.INVALID alone cannot recover that evidence. Similarly,
INSUFFICIENT_HISTORY and SOURCE_UNAVAILABLE remain evidence-backed reasons, not
newly selected runtime enum aliases or substitutes for NOT_APPLICABLE.

## 3. Existing Common Contract sidecar is the primary reuse point

`implementation/docs/qgv_common_contract_vnext/CONTRACT.md:section 3` already
separates value presence, applicability, original quality, PIT admission,
confidence, coverage, provenance and configuration references. Its documented
factor definition can reference applicability and aggregation policies. It is
an inactive sidecar, not QGVSnapshot replacement or an evaluator request.

The existing `contract_record.schema.json` expresses input value_state,
applicability, legacy_quality and reason_codes (`:114–181`), separate confidence
and coverage definitions (`:188–385`), constant inactive/runtime-disabled status
(`:394–400`) and a referenced PIT assessment (`:486–520`).
`implementation/tools/qgv_contract_audit.py:58–101` verifies structural/time
coherence and explicitly returns `runtime_enabled=False`. It does not implement
missing scoring, authenticate remote lineage or make a production admission.

The existing example lacks a full axis-result/requiredness/scoped dependency
ledger; adding those semantics is necessary if a future record must explain
policy decisions. These are **minimal reference-based conceptual additions**:

| Needed expression | Existing material reused | Minimum addition, still inactive |
|---|---|---|
| Method-requiredness | Factor ID/version/method references | Reference to an immutable method declaration and, if conditional, predicate/input evidence. Actual roles and predicate values remain unselected |
| Applicability determination | Existing applicability assessment and financial helper | Policy/profile/predicate evidence and resolution state, retaining conflicts rather than accepting a supplied N/A label as proof |
| Scope of consumed dependencies/failures | Source/vintage/stamp/provenance and original quality/reason | Declared method-request scope, dependency edges and evidence of which inputs affect identity, configuration, applicability, requiredness or scoring; relevant/shared scope cannot be erased by weight zero |
| Factor eligibility/admission | Original observation plus PIT assessment | Qualified decision and reason references against the pinned method/input contract; value validation is distinct from ordinary absence |
| Planned aggregation basis | Pinned official/local weights and aggregation policy | Reference to denominator policy and an inclusion/exclusion ledger determined independently of observation availability. N/A treatment remains policy-selectable, not universally mandated |
| Contribution/result meaning | Legacy scalar and Common Contract score-kind concept | Qualified numerator/contribution trace and separate partial/complete/validity assessments; no rule equating a scalar, coverage=READY or weighted fraction with completeness |
| Coverage and confidence | Existing independent sidecar shapes | Method-reference-based evidence scope/numerator/denominator where defined, plus assessment limitations; no numeric cutoff or confidence formula |
| Ranking/publication | Result namespace, lifecycle and consumer/source references | Separate approved consumer/admission-policy reference or unresolved state. No all-positive-weight rule, rank flag or publication grant is derived automatically |

These expressions need not become eight new runtime classes. A composed,
versioned reference manifest with separate qualified assessments can satisfy the
architecture. Any future schema extension must be new and versioned; the
existing inactive sample and historical golden expectations are not rewritten.
This task does not introduce that runtime parser or schema migration.

## 4. Pipeline order audit and refinement

The conceptual chain Admission → Applicability → Requiredness → Eligibility →
Contribution → Denominator → Coverage/Completeness → Ranking captures the
needed concerns. It is not a single unconditional reducer order. Four refinements
avoid approvals being weakened or broadened accidentally:

1. **Configuration/identity admission precedes economic predicates.** Pin the
   subject, namespace, calculation/method/version, registry/override version,
   original references and scope declarations. Missing configuration is not an
   ordinary missing company observation. A policy cannot use an unadmitted
   future/ambiguous input to prove N/A and then discard the failure.
2. **Predicate inputs and observation inputs have separate admission points.**
   Inputs needed to resolve applicability or conditional requiredness must pass
   their relevant/shared PIT/integrity guard before their predicates are used.
   Once scope is resolved, score observations receive their own eligibility
   assessment. Truly unrelated, predeclared unconsumed inventory is not
   automatically treated as a shared failure, but scope evidence must prove it.
3. **The planned denominator is defined before ordinary observation loss.**
   It depends on pinned configuration and a separately selected N/A treatment.
   Contribution accumulation and denominator arithmetic can be displayed in
   either order, but the denominator policy cannot be derived from which scores
   happen to survive. Ordinary missing must not trigger available-weight
   renormalization. Proven N/A treatment remains a future method-level choice
   within M3's permitted boundary, with impact evidence.
4. **Coverage, completeness, validity and ranking are distinct assessments.**
   Coverage inventories evidence. Requiredness constrains method validity.
   Partial contribution is a result meaning. Completeness depends on a future
   declared method/consumer rule; ranking additionally requires separate
   consumer policy, compatible versions and namespace/publication authority.
   No one-to-one implication or all-positive-weight completeness rule is approved.

An inactive implementation review can therefore reason in this dependency order:

| Stage | Inputs / reuse | Output meaning / remaining boundary |
|---|---|---|
| Context and scope admission | Existing namespace, registry/version/hash, calculation/method and subject refs | Pinned context plus explicit requested/shared dependency scope; no runtime activation |
| Predicate evidence admission | DataStamp and provider time/provenance guards | Admitted inputs for applicability and conditional method roles; no scope laundering |
| Applicability and requiredness resolution | Existing financial rule plus immutable method declaration refs | Separate qualified economic and methodological assessments; real new roles/predicates unresolved |
| Observation eligibility | Presence/original quality/PIT/source/value evidence | Ordinary absence versus relevant/shared failure kept distinct; no unknown-to-valid coercion |
| Planned basis and contribution | Resolved policy/weights plus eligible observations | Independent inclusion ledger and numerator trace; ordinary missing does not rebase denominator; N/A policy not fixed universally |
| Result, coverage and method validity | Contributions plus independent assessments | Partial result, coverage and validity/completeness remain separate; no numeric threshold or ranking rule |
| Consumer acceptance | Namespace/version/method/consumer policy/authority | Ranking/publication unresolved until its separate approved criteria exist |

Method requiredness is not mechanically inferred from positive weight. Weight
zero affects contribution but does not waive declared requiredness or a related
shared integrity failure. Conversely, a profile-specific unrequested optional
input is not automatically shared solely because it appears in a data inventory.
The scope declaration must retain why that input is unrelated/unconsumed, and
cannot be rewritten after a failure to manufacture exclusion.

## 5. Isolation, replay and reference discipline

Reuse the existing Personal registry/version/override objects and namespace
rules. A Custom request could reference different authorized local weights only
after separate runtime wiring approval. It must reference, rather than mutate,
Official definitions and policy authority. No new Personal profile may rewrite
Official requiredness, validity, source evidence, board or Track Record.

Official and future Custom evaluation should share the same approved evaluator
contract for a calculation version. Current legacy replay must remain exact;
that preservation is not approval to continue every old permissive admission in
a newly activated method. Old serialized result fields remain literal evidence,
including legacy partial numbers and V quality-label reuse.

Never use a provenance hash as authenticated source bytes, a fetched/retrieved
timestamp as historical availability, a QualityState label as independent
confidence, or a coverage count as Official rank eligibility. Referenced policy
or method information that is unresolved stays unresolved and inactive.

## 6. Validation scope and next dependencies

This file adds no executable implementation or test. Previously verified source
and probe evidence are reused. The separate regression plan should eventually
check principle invariants, exact old replay, denominator stability under ordinary
loss, requiredness/non-bypass at zero weight, reason/scope preservation and
Official/Custom isolation. It must leave completeness/ranking outcome fixtures
unfixed until the user approves the missing method/consumer criteria.

Remaining implementation prerequisites include actual method-requiredness and
applicability declarations, scoped dependency rules, selected method-specific
N/A denominator treatment, result/completeness interpretation, and separate
ranking/admission rules. These are not runtime blocker fixes performed here.
G horizon/fallback, V normalization/metadata, composite and WeightOverride wiring
remain separate semantic decisions and retain their original protected history.

**Production changed: NO. Legacy/Official score changed: NO. History rewritten:
NO. New factor roles/taxonomy/default/cutoff selected: NO. Runtime tests added:
NO. Runtime migration begun: NO.**
