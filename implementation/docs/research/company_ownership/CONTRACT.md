# Company ownership research adapter /1 — implementation plan and Main contract

Owner: Codex_QGV_Relationship_Queue_20261111.md (2026-11-11). Base canonical
ab6a83c3be2276abdcf855c71c5f273926e2dcc4. Main #530 c84e85d86dd7108dbe66a7a6696ca65094410b64
has not changed; #437 6792797898 acceptance is reused. QGV producer #529 unchanged.

Goal: provide source-backed corporate investment and separately stated parent/
subsidiary facts for Main 5.1, without changing scores, classification, macro or
selection. This is a research adapter and static file projection, not a second
identity registry, relationship service, database or collection framework.

## Design and reuse

Reuse RIG `IdentityRef`, `Node.for_issuer`, `stable_id` and append-only lineage
semantics; reuse `providers.sec_classification_inputs.html_text` to locate retained
HTML evidence. Existing RIG enum has no ownership/control type and its
RelationshipState uses availability date for unknown valid_from. We therefore
do not mislabel ownership VALUE_CHAIN or force date-only evidence into UTC times.
Date-precision observations remain in a versioned research envelope. Main may
later adopt an operational RIG extension; no rig/, UI, bridge or guard edits here.

Alternatives considered: modifying operational RIG now would alter the meaning of
existing records; reusing a supply-chain label would misstate facts. A typed
observation adapter is the smallest compatible extension and is the implementation
choice within the owner's authorized scope. No new policy/role approval is needed.

Files: research/company_ownership.py (validation, normalization, append, projection),
tools/company_ownership.py (offline hash-pinned CLI), tests/research/test_company_ownership.py,
this document and synthetic.json. No added dependencies. Native implementation;
one fresh final review. User's continuous execution and no repeated tests override
skill defaults for extra approval rounds and unrelated full-suite reruns.

## Contract

Input `company-ownership-input/1`: dataset_id, version, data_kind, identity_context,
entities, mentions, evidence, assertions, paths, collection, publication.
The identity context pins an upstream namespace/version/registry SHA. Entity rows
reference an existing issuer via IdentityRef; company_ids are existing code rows,
not tickers guessed into issuer IDs. Normalization receives the exact upstream
identity records, verifies its SHA and matches each entity's issuer/company IDs.
Mentions have evidence IDs and local mention IDs only; unresolved names are not
invented legal entities or accepted graph edges. Several code rows share one issuer.

Evidence: id, source_kind, url, document_id, locator, artifact_hash, excerpt,
published/available/acquired (precision objects), source_period, publication.
Publication/availability/acquisition are independent. Precision objects contain
value plus DATE/DATETIME/UNKNOWN. DATE is never rewritten as midnight. Unknown
publication is allowed but cannot establish historical availability. Normalization
matches excerpts to hash-checked retained bytes; a review annotation supplies the
semantic assertion. This is source verification, not an automatic legal inference.

Assertions: assertion_id, version, previous_version, source_entity_id/mention,
target_entity_id/mention, type OWNERSHIP or PARENT_SUBSIDIARY, directness
DIRECT/INDIRECT/UNKNOWN, capacity CORPORATE_INVESTMENT/LEGAL_OWNERSHIP/
BENEFICIAL_OWNERSHIP/INVESTMENT_DISCRETION/UNKNOWN, status UNREVIEWED/VERIFIED/
PLANNED/COMPLETED/DISPOSED/CONFLICT, statement, evidence_ids, observations,
temporal and publication. Confirmed subsidiary prose is independent of numeric
ownership. 13F can establish INVESTMENT_DISCRETION only, never a subsidiary or
corporate-investment fact. Announcement and completion are different versions.

Observation: observation_id, metric SHARE_CAPITAL/VOTING_POWER/MANAGED_HOLDINGS,
value/lower/upper as exact decimal strings or null, qualifier EXACT/APPROX/RANGE/
AT_LEAST/AT_MOST/NOT_DISCLOSED, unit PERCENT, denominator_basis,
security_id/share_class, observed_as_of, missing_reason. Decimal range is0..100.
JSON decimal strings are deliberate wire precision, not inferred/filled numbers.
Every observation retains its own denominator/class/date. Disjoint measurements
are not averaged or summed. Incompatible values on the same basis flag CONFLICT.
Zero is a valid observation, not a positive position or an inferred termination.

Temporal: valid_from/to nullable confirmed dates (end exclusive), observed_on,
system_known_at, reviewed_at (aware timestamps), previous_version. Unknown interval
stays unknown. Old observations show REVIEW_REQUIRED/VALIDITY_UNCONFIRMED at later
query dates; an open-ended interval never proves future continuity. Query uses
valid_on date AND knowledge_at timestamp; all evidence and assertion versions must
be available then. Date-only availability on the cutoff day remains time-unknown.
Late acquired historical documents are retrospective, not historical system PIT.

Output `company-ownership-view/1`: dataset/version/hash, query_as_of,
generated_at, entity_context, entities, relationships, unresolved_assertions,
evidence, confirmed_paths, diagnostics, collection, publication, counts.
Relationship direction is holder→investee or stated parent→subsidiary. The reverse
company view reuses the same relationship_id and marks INCOMING; it never stores a
second fact. Paths are explicitly supplied evidence-backed edge chains; cycles and
duplicate paths are rejected/diagnosed; no economic look-through ratio is computed.

Per-company request: existing entity_id, valid_on, knowledge_at, optional
relationship_type filter, public=false. Filter0 differs from no reviewed relation,
NOT_COLLECTED, PARTIAL_REVIEW and NOT_FOUND_IN_REVIEWED_SCOPE. Unknown true relationship
denominator and coverage stay null. Reviewed target counts are a separate unit.
Output <=2MiB; oversized output fails, never silently truncates. Main owns authenticated
delivery, UI and any operational route. A schema/version is not publication approval.
Public projection requires explicit dataset and referenced-record approvals and
whitelists fields; no raw text, private paths, portfolio, token or private macro/KIS.

Updates are append-only by evidence/assertion version. A conflicting existing ID,
missing prior version or conflicting content fails. A failed/partial collection
retains the last good dataset and original generated/confirmation times, with a
separate attempt status; absence in a newer document is not deletion/termination.

## Implementation and validation ledger

Review focus: date-only cutoff ambiguity; a recent acquisition of an old document;
unresolved subsidiary names becoming fake entities;13F corporate/parent inference;
public output with private reference metadata. These are explicit tests.

- [ ] Task1: failing contract tests → implement normalize/validate and per-company
  query using common IdentityRef. Verify Decimal, broken provenance, alias identity,
  dates, differing denominators, planned/control/13F and independent numeric facts.
- [ ] Task2: failing version/update/public/paths tests → append-only merge, dual-time
  projection, no inferred intervals, failed refresh and bounded offline CLI.
- [ ] Task3: synthetic cases/expected outcomes generated from the tested public packet;
  Draft PR and Main first handoff before real source review.
- [ ] Task4: inspect only identified retained sources for1–3 groups. Hash→excerpt→
  known issuer/unknown mention→result. Preserve private inputs/output/manifests,
  report units separately. No target count forcing or new collection.
- [ ] Task5: fresh review and changed regression checks; Main exact SHA/contract,
  real limitations, CI separate from local and browser/deployment.

Commands: `PYTHONPATH=implementation/src python -m pytest
implementation/tests/research/test_company_ownership.py -q`; CLI documented with
the synthetic handoff after implementation. Existing pytest tests/ discovery
includes research tests; no CI-list edit requested.

State at plan commit: NOT_STARTED. QGV/V new calculation0; unchanged inputs pending.
