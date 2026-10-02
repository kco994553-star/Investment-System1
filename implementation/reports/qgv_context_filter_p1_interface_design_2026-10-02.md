# P1 Common Context Interface — design freeze preparation

Scope: AP1/AP2/AP3-approved Common Context + Company/Suitability + deterministic Filter transport and persistence. **INTERFACE_DESIGN_FREEZE_READY**, not implemented or software-frozen. No AP4/AP5/AP6 approval. This concretizes v0.2 §§4–6,11,13 without adding a domain engine or choosing result configuration.

## Authority and reuse

Authority: QCF-AP1/QCF-AP2/QCF-AP3 in the append-only Decision Register; v0.3 exact approved clauses. Upstream code pins remain the scoped approval evidence pins. Source read audit: canonical RawDatasetStore exposes current get_bytes(id) plus list_history(id), so latest-only get_bytes is insufficient for pinned replay; the adapter must resolve the exact existing history bytes. Producer Infrastructure serialization.py at f8af596 supplies canonical_bytes/canonical_sha256 and rejects naive datetime, unordered sets, NaN/Infinity. Reuse that behavior; no numeric normalization/rounding is added. P01 at 21039a0 supports only its four existing extractors and has no active grants.

P1 owns the common schema/ref/hash/time/manifest/operational-journal interface as **single writer**. P2/P3/P4/P5 own their typed payloads, never common fields. A consumer pins this document's immutable Git blob/commit and upstream serializer version via requires_contract_ref. Mismatch is a contract error, not compatibility guessing. This document is the design pin; it does not claim an executable schema registry already exists.

## Data types and validation boundary

| Type | Required shape / meaning |
|---|---|
| RevisionRef | namespace, kind, logical_id, revision_id, artifact_locator, artifact_sha256, semantic_hash where upstream supplies it; upstream hashes copied verbatim, never substituted for artifact-byte hash |
| SubjectRef | existing company/issuer/security/listing identity refs as applicable; scope_kind and exact scope_ref (issuer versus segment); no name/ticker inference |
| TimeBasis | explicit mode, decision_time, view_time; published/available/recorded/computed/economic-valid times remain separate; timestamp precision and source interval retained; timezone-aware instants, date-only facts not coerced to midnight |
| PolicyRef | decision/policy ID, revision, artifact/hash reference, exact approval scope and authority evidence; absence is not default approval |
| NullableFact | value=null with reason and evidence/unknown refs; never empty string/zero/false as a missing-data substitute |
| QualifiedState | owning contract/type + original state + reason refs. Evidence validity, freshness, assessment analytic state, execution status, producer validation, methodology maturity and publication mode are distinct fields |
| DependencyRef | parent revision/hash or absent-target query selector; child ref, role, requiredness, use_time, applicable policy ref. Evaluation DAG excludes semantic rebuttal links from its dependency edges |

These field names are a documentation-level binding for the existing logical design, not additions to frozen upstream objects. P1 stores extensions referring to existing RIG SourceRef/Evidence/Claim/Event identities. No raw-body duplication, new crawler, replacement identity registry, taxonomy provider, source-ranking engine or generic confidence converter.

## Immutable document envelope

Required envelope: contract_id, schema_version, record_id, revision_id, subject_ref, input_refs, methodology_ref, policy_refs, recorded_at, semantic_hash, operational_run_ref, typed payload reference/body. Applicable times and review evidence are explicit; absent required fields produce a structural error. Optional domain facts use NullableFact.

Semantic content includes all values that affect admission/replay/result: subject/scope, relevant temporal facts, policy/config/methodology pins, input hashes, result and limitation/reason evidence. Operational execution UUID/run log identity is excluded; an output's recorded/computed time is NOT discarded merely because it looks operational. Admission clocks therefore cannot disappear from semantic identity. Upstream source bytes are immutable and never rewritten for UTC display normalization.

The artifact SHA is computed over the stored artifact bytes externally; it is not a self-hash field recursively included in those bytes. semantic_hash covers the designated semantic object with its own hash field excluded. The serializer preserves list order; semantically unordered ref sets use their exact identity keys in a documented stable order. Condition display order is retained separately from the set predicates used by CF16. A display reorder must not change company_result; byte/hash identity is not asserted for deliberately different display metadata.

| Document | Required payload / constraint |
|---|---|
| EvidenceContext | existing evidence ref, source revision/hash/locator, content kind, origins, metric/time basis, quality dimensions, correction/retraction relation; no source-type winner |
| Assessment | qualified assessment type, target, inputs, result state, confidence basis, supporting/counter refs, unknowns/conflicts, knowledge cutoff, computed_at, prior revision, rubric/reviewer evidence when result admission requires them |
| DependencyEdge | exact parent/child refs; query dependency also records scope/metric/period for absent observations; cycles rejected for evaluation DAG |
| FilterDefinition | Universe identity/revision/member hash, decision time, typed conditions, requiredness, explicit waiver refs, config/preset/methodology/policy refs; no implicit waiver or preferred-only evaluation |
| ThresholdConfiguration | all CF17 exact metric/unit/direction/maturity/mode/reference/PIT/taxonomy/peer/history/time/formula/convention/tie/boundary/precision/missing/N.A./outlier/negative/support/constituent/combination/hash/approval/scope/calibration/invalidation semantics; unresolved applicable fields => POLICY_BLOCKED |
| ContextSnapshotManifest | chosen revision closure, upstream pins/hashes, Universe/identity/calendar/taxonomy refs as applicable, explicit clocks/mode/scope, policy/config roots, pending invalidation reference, result refs/hashes, completeness/limitations; no mixed generation |
| Operational journal | append-only input/config/policy-change and invalidation events, generation transition and replay dependencies. Derived index is rebuildable, not SSoT |

Macro/News-specific payload admission and publication projection are extension boundaries only. Unknown/unapproved typed payload contracts cannot manufacture an admitted result. P1 can retain opaque referenced candidate evidence without assigning Macro/News labels. No universal conversion of every blocked/error state to UNKNOWN is permitted.

## Read interface contracts

These are function/message contracts, not implemented endpoints.

| Operation | Required request | Response and side-effect boundary |
|---|---|---|
| resolve_context | explicit mode, decision_time, view_time, scope, pinned manifest OR pinned recipe, policy refs and requires_contract_ref | snapshot ref + chosen refs + completeness + limitations, OR explicit unavailable/reasons; no network refetch, automatic mode, or publication |
| resolve_revision | exact artifact identity/locator and expected SHA; approved existing-store roots | matching current/history bytes plus original provenance, OR ARTIFACT_UNRESOLVABLE/HASH_MISMATCH. Never latest fallback |
| get_assessment | exact assessment RevisionRef + requested evaluation scope | stored typed assessment and lineage plus admission projection under pinned AP1/2 policy; no LLM, no mutation of analytic original |
| evaluate_filter | definition RevisionRef, ContextSnapshotManifest ref, explicit clock bound to manifest, requires_contract_ref | definition validation state; company_result where evaluable; all condition states/reasons/evidence; all blocker/limitation refs. No scores or ranks |
| replay_snapshot | exact manifest ref, explicit mode and clock | original/replayed semantic refs, equality status, completeness, unavailable reasons and inherited PIT limitations; no new model generation |
| explain_change | old/new pinned result/manifest refs | exact input/config/policy/clock/ref deltas and cause evidence; no price-causal interpretation or invented magnitude |

No publication_projection activation is frozen in this interface. Existing P01 remains authoritative: unsupported Context shape/no grant => no publication. Internal atomic snapshot commit is not a publication grant.

## Writer interface and crash boundary

The single P1 writer accepts a staging generation consisting of immutable documents, closure refs, explicit clock/policy/config root, expected prior CURRENT pointer and idempotency identity. Consumer modules submit candidate documents to this interface; they never update the shared CURRENT pointer or index directly.

Sequence: validate contract/ref/identity/hash/time and evaluation-DAG closure → stage full generation → validate all object counts/hashes/refs → immutable object writes → durable manifest write → index transaction → compare-and-swap CURRENT pointer last. Existing bundle atomic-write helpers do not imply a multi-file transaction; this sequence is a P1 requirement, not an assertion about current implementation.

Staging failures never expose a half-generation. Restart inspects the journal and revalidates incomplete staging; incomplete data is not marked CURRENT. A stale writer whose expected prior pointer differs cannot commit. Idempotency uses the v0.2 input-root/methodology/policy identity; the input root includes explicit result-affecting clock, scope and configs. Same key and same content reuses the same result; same key with different content is a conflict, not last-writer-wins.

An old complete snapshot may remain stored after a failed refresh. If a current assessment is stale/reassessment pending/freshness unresolved, a current query must still project UNKNOWN under CF02; retaining the old pointer is not permission to return its old MATCH as current. The query binds an operational-journal view as well as the immutable manifest; a changed journal cannot silently be ignored. Historical replay uses its original clock/policy/state reference, not today's invalidation projection.

## Replay and policy-blocked boundaries

| Situation | Contract consequence |
|---|---|
| Missing mode or required identity/config meaning | Request/definition invalid; no evaluated membership. Missing CF17 config => POLICY_BLOCKED |
| Existing pinned bytes lost or hash mismatch | Replay unavailable with exact reason; no latest substitution. An evaluation requiring that unverifiable ref cannot be treated as valid |
| Normal company observation missing, complete valid definition | condition UNKNOWN; then CF16 applies. This is not a missing policy definition |
| No stored snapshot/judgment at T in AS_RECORDED | NOT_RECORDED; later reconstruction cannot masquerade as original judgment |
| Available-time interval crosses T | Evidence admission withheld; no rounding timestamps to admit it |
| Retrospective model/restatement limitation unresolved | Preserve limitation; not strict PIT or original judgment |
| Rubric/reviewer missing for derived label | candidate/NOT_ASSESSED; Filter condition not manufactured as MATCH |
| Approved static freshness N.A. | Distinct from unresolved required freshness; preserve validity checks |
| Unwaived mandatory N.A. versus all waived | INSUFFICIENT_EVIDENCE versus NOT_EVALUABLE/UNCONSTRAINED_DEFINITION under CF16 |
| Mandatory NO_MATCH plus UNKNOWN/PARTIAL | NO_MATCH, with unresolved states/evidence preserved |
| Config/reference/model/taxonomy revision changes | New dependency/generation, never silently mutate old manifest or upstream score |
| Missing-observation arrival | Query dependency wakes relevant reassessment; an absent evidence ID is not an excuse to miss invalidation |

## Independent audit pass and acceptance

A separate specification audit pass derives expected consequences from the approved clauses and existing source contracts, then compares them with this interface. This is documentary independence of derivation, **not an external reviewer attestation or executed independent test suite**. No user review authority is delegated by this audit.

| Audit case | Independent authority | Interface result |
|---|---|---|
| Concurrent stale writer attempts commit | v0.2 atomic-generation design | CAS blocks exposure; no mixed snapshot |
| Refresh crashes after invalidation, before pointer replacement | CF02 + immutable history | old history preserved; current condition UNKNOWN, not stale MATCH |
| Same source available before T but judgment computed after T | CF01 | AS_RECORDED excludes later judgment; reconstruction separately labelled |
| Current raw artifact changed; original history available | v0.2 exact-hash replay / RawDatasetStore | resolve exact history SHA; not current get_bytes alone |
| Raw history unavailable | same contract | ARTIFACT_UNRESOLVABLE, no network/latest fallback |
| Same evidence with new policy/clock | CF01/02/17 | semantic input root changes; no cache reuse under old key |
| Segment facts arrive for issuer industry condition | CF13 | no issuer classification promotion |
| Bank V missing, Q evidence valid | CF15 | axis-local assessments, no Q/G penalty |
| Metadata alias resembles an industry | Entity Metadata contract | search-only field cannot satisfy taxonomy requirement |
| Condition order permuted | CF16 | same company_result, original reasons retained |
| > versus >= unspecified at x=theta | CF17 | POLICY_BLOCKED; interface never chooses boundary |
| PROVISIONAL raw value has a number | QGV producer + CF17 | no validated promotion; admissibility must be approved |
| Serialization encounters set/NaN/naive datetime | existing Producer serializer | structural rejection, no invented normalization |
| P1 internal commit contains an otherwise valid result | P01 | no publication grant or schema-1 extension |

Verdict: no new result-affecting policy is required to freeze this limited P1 common interface design. Runtime correctness, durable storage availability and actual schema/API implementation remain unverified and unimplemented. Known operational storage/P03 constraints do not justify a long-term replay guarantee. **P1 INTERFACE_DESIGN_FREEZE_READY within AP1–AP3 scope; software/interface implementation NOT STARTED.**

## Dependency handoff

P1 owner alone changes common contract/hash/time/storage interfaces. Downstream packages consume an immutable interface reference and return a compatibility issue on mismatch; they cannot patch shared interfaces independently. Even with this design readiness, P2/P3/P4/P5 implementation requires separate permission, and actual parallel work must wait for the P1 interface pin to be adopted/frozen by its single writer. No parallel implementation is launched.

AP4/AP5/AP6 remain the next unresolved policy packages. P1 common interface does not define their domain meanings. First next user decision is AP4, with AP5/AP6 prepared for later sequential review.
