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

- [x] Task1: failing contract tests → implement normalize/validate and per-company
  query using common IdentityRef. Verify Decimal, broken provenance, alias identity,
  dates, differing denominators, planned/control/13F and independent numeric facts.
- [x] Task2: failing version/update/public/paths tests → append-only merge, dual-time
  projection, no inferred intervals, failed refresh and bounded offline CLI.
- [x] Task3: synthetic cases/expected outcomes generated from the tested public packet;
  Draft PR and Main first handoff before real source review.
- [x] Task4: inspect only identified retained sources for1–3 groups. Hash→excerpt→
  known issuer/unknown mention→result. Preserve private inputs/output/manifests,
  report units separately. No target count forcing or new collection.
- [x] Task5: fresh review and changed regression checks; Main exact SHA/contract,
  real limitations, CI separate from local and browser/deployment.

Commands: `PYTHONPATH=implementation/src python -m pytest
implementation/tests/research/test_company_ownership.py -q`; CLI documented with
the synthetic handoff after implementation. Existing pytest tests/ discovery
includes research tests; no CI-list edit requested.

State at plan commit: NOT_STARTED (preserved history). Current: adapter/CLI implemented; first handoff prepared. QGV/V new calculation0; unchanged inputs pending.

## First Main handoff: executable synthetic interface

`synthetic.json` contains 18 cases with the exact upstream identity document bytes,
source bytes, case input, query, expected view/error, and canonical view SHA-256.
These are fictional companies. The hand-written tests establish semantic invariants;
the generated views are shared producer/consumer examples, not independent proof.
Main can consume `expected_view` directly for5.1.1/5.1.2 and use the same query inputs.
The failed-refresh tests use `merge_update`; a failure receipt is separate from the
unchanged last good dataset. No provider is called and no browser has been tested.

Python API:

```python
normalized = normalize_packet(packet, identity_document_bytes, artifacts_by_sha256)
view = company_view(normalized, entity_id=existing_issuer_id,
                    valid_on="2025-12-31", knowledge_at="2026-01-05T12:00:00Z",
                    generated_at="2026-01-05T12:00:00Z", public=False)
update = merge_update(previous, incoming, outcome="SUCCESS",
                      attempted_at="2026-01-06T12:00:00Z")
```

CLI (local files only; output directory must not exist):

```sh
PYTHONPATH=implementation/src python implementation/tools/company_ownership.py \
  --input INPUT.json --input-sha256 INPUT_SHA256 --identity UPSTREAM.json \
  --artifacts HASH_NAMED_FILES_DIR --entity-id EXISTING_ISSUER_ID \
  --valid-on 2025-12-31 --knowledge-at 2026-01-05T12:00:00Z \
  --generated-at 2026-01-05T12:00:00Z --output-dir NEW_PRIVATE_DIRECTORY
```

Add `--synthetic` only for SYNTHETIC input. RETAINED output inside any Git checkout/worktree is
rejected. View, normalized input and manifest are each bounded at2MiB; no silent
truncation. File hashes are raw SHA-256 bytes; `expected_view_sha256` uses
`json_bytes` (UTF-8, sorted keys, compact separators, LF, no NaN). Main need not
re-hash JS numeric serialization: observations are deliberate exact Decimal strings;
raw artifact/view file bytes are the integrity boundary.

A public projection is an explicit Python API request requiring approval on the
dataset and every visible entity/assertion/history/source. Raw excerpts are omitted
from all company views. `normalized.json` retains source excerpts and must stay
private for RETAINED inputs. No publication route is added. Error output contains
fixed diagnostic codes; no raw source, private paths, or exception payloads.

`VERIFIED_ZERO_IN_SCOPE` additionally needs explicit reviewed zero evidence,
COMPLETE scope and matching zero_observed_on. It does not prove all relationships
in the world. `NOT_FOUND_IN_REVIEWED_SCOPE` never becomes a verified zero merely
because assertions are empty. A later collection review is withheld from an earlier
knowledge query. `historical_system_pit=false`: upstream identity history is not
established by this adapter; `query_mode` distinguishes retrospective/system-asof
queries without claiming completed historical PIT.

Main remains owner of frontend/authenticated retrieval/bridge/operating RIG enum.
Read this contract through the adapter; do not coerce it into VALUE_CHAIN or use
RIG's available_at fallback as an ownership valid_from. New tests are under tests/ automatic discovery. No dependency/workflow/CI-list edit
is requested. One existing Main-owned architecture guard does need a narrow update:
`tests/test_rig_p0_foundation.py::test_no_other_package_depends_on_rig` currently
rejects every external RIG import. The owner's requested reuse introduces exactly
`research/company_ownership.py -> rig.model` (IdentityRef, Node, stable_id). Main
should permit this specific pure-domain dependency while retaining all other bans.
Codex did not delete/skip/change the guard or disguise the import. Current targeted
result: adapter30 passed + RIG14 passed; this single architecture guard failed.


## Final review and retained-source result

Fresh reviewer checked the whole implementation without rerunning completed suites.
Five findings were independently reproduced and corrected with failing-then-passing
regression tests: private updates retaining public approval; later observations
hiding an earlier applicable version; nested source-period metadata escaping public
projection; merged verified-zero scope conflicting with retained claims; equivalent
relationship paths counted twice under different assertion IDs. No minor findings
were deferred. Additional source-kind tests reject NEWS/OTHER-only confirmation;
synthetic source text now matches each scenario's numerical observations.

Changed adapter suite:39 passed. The previously passed RIG14 tests were reused;
the unchanged all-external-RIG-import architecture guard remains Main's narrow
integration change, already requested at #437 comment6794279588. No broad waiver,
copy of shared logic or dynamic import is proposed. This is an ownership-boundary
integration dependency, not an owner approval request.

Retained-source execution:1 company group reviewed,1 existing issuer connected,
1 unresolved investee mention,0 confirmed relationships,0 ownership observations.
One already preserved historical disclosure/receipt was hash-checked and passed
through the same offline CLI. Its transaction-percentage wording does not establish
current ownership, a remaining percentage, investee legal identity, directness or
continuity. Publication date remains DATE, original acquisition timestamp is
preserved, assertion review/knowledge time is the actual new review time. Historical
system PIT is not claimed. This run neither recalculates nor increases QGV/V.
Company-level input/source/view stay in the approved private handoff; no real
company examples were added to this contract or synthetic fixture.

Publication permissions only become more restrictive during merge; updates cannot
inherit old approval for newly private content. Assertion history is selected by
both valid time and system knowledge. Conflicting zero-scope updates fail closed
instead of deleting prior facts. Equivalent paths use stable relationship IDs;
all supporting assertions are retained without indirect percentage arithmetic.
`merge_update` failure returns the previous dataset unchanged plus a separate
attempt receipt: Main should retain the original file bytes and write only the
attempt sidecar, not reserialize the last good file on failure.

QGV consumption status is reused from #4376792797898: #530
c84e85d86dd7108dbe66a7a6696ca65094410b64 has no newly delivered consumer SHA at
this review. The INTEGRATED-to-legacy-context bridge difference was handed to Main;
no duplicate contract/fixture/recalculation was produced. V source/receipt/eligible
price inputs remain pending. Browser/authenticated delivery/operating adoption/
deployment are separate and have not been verified by this research adapter.

Additional private-output boundary: the CLI rejects retained output beneath any Git checkout/worktree, not just its own. Regression was reproduced before the guard was broadened. No Main-owned guard was changed. New #530 9d1129d223dcd7a73605d1e17736f3d334673cab arrived after the initial review; its changed model bridge and bounded reader were independently accepted in Python/Node, with no real-company recalculation. Main browser/authenticated live delivery remains separate.

## Consumer acceptance supplement (2026-11-12)

The original `synthetic.json` bytes/pin stay unchanged. Additive, producer-created
`consumer-synthetic.json` is generated by
`PYTHONPATH=implementation/src python implementation/tools/generate_ownership_consumer_examples.py`.
It carries inputs, per-case synthetic evidence, expected views/byte hashes and
separate failed-attempt receipts. No real company is in either fixture.

Full `collection_state` values (all six, not a five-value allowlist):

| Value | Meaning |
|---|---|
| NOT_COLLECTED | This query centre has no completed dedicated review. Incoming reviewed evidence from another centre can still exist; do not reject it or infer zero relationships. |
| FILTER_EMPTY | Relationships exist but none match the chosen type filter. |
| VERIFIED_ZERO_IN_SCOPE | Explicit dated zero evidence in the complete declared review scope; not all relationships everywhere. |
| NOT_FOUND_IN_REVIEWED_SCOPE | No relationship found in the reviewed scope; not positive evidence of zero. |
| PARTIAL_REVIEW | Reviewed relationships/unresolved claims exist; declared scope is partial or unknown. |
| REVIEWED_SCOPE | Completed within the declared review scope; no whole-market completeness claim. |

Incoming queries retain source→target assertion and relationship IDs. Only
`relative_direction` changes; `direction` remains SOURCE_TO_TARGET. An INDIRECT
observation neither invents intermediaries nor multiplies percentages. A 13F
observation has INVESTMENT_DISCRETION/MANAGED_HOLDINGS and is not corporate
investment or control. Zero percentages and explicit zero-relationship scope
are different examples. Unresolved names are not promoted to issuer IDs.

`merge_update` receipts have outcomes SUCCESS / FAILED / PARTIAL / PARSE_FAILED.
Non-success retains the previous normalized dataset and original view bytes,
view.generated_at and collection.last_success_at. The new attempted_at belongs
to the separate receipt. `collection.last_failure` in company-ownership-view/1
remains null intentionally: the view is not an error-log transport. Main should
bind the separate attempt receipt to its retained dataset/view hash and render
refresh failure beside that prior view. Do not mutate its generated/success time
or synthesize a producer field to activate an existing UI branch. Receipt
absence means no known refresh status, not a successful new collection.

Direct Node check against Main #532 fb6d567cd42bc844c6fef7c23562a34c290831bf:
10/12 new views accepted; `reviewed_scope` rejected because COLLECTION omits
REVIEWED_SCOPE; `incoming_centre_not_reviewed` rejected by the blanket
NOT_COLLECTED-with-relationships prohibition. Expected both accepted, preserving
the scope warning. Main owns `product/web_app/ownership-view.js` fixes at its
COLLECTION dictionary and collection-state cross-check. The refresh views are
accepted but their external attempt receipts are not yet consumed by view().
These are Node contract results, not browser/authenticated/operating completion.

Guard handoff: this research adapter imports exactly `IdentityRef`, `Node`,
`stable_id` from the pure `investment_system.rig.model`. No RIG collector,
storage, scoring or runtime graph is called. The operating boundary test
`tests/test_rig_p0_foundation.py::test_no_other_package_depends_on_rig`
currently rejects every outside-RIG import, including this authorized research
adapter. Main must review a path-and-symbol-specific allowance (and retain the
rest of the guard). Codex does not duplicate the pure helper, hide the import,
edit the guard, or claim the pre-existing CI failure resolved.
