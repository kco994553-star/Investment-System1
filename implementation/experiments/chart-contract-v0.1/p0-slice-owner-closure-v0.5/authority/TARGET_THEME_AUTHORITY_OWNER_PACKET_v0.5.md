# Target Theme authority and interface owner packet v0.5

Status: **READ_ONLY_INTERFACE_EVIDENCE / OWNER_ACTION_REQUIRED / NOT_ADOPTED**. This packet narrows A-G1/A-G2 from v0.4. It does not add a seventh pre-code gate, a grant, a permission enum, a new policy, or a Chart production implementation. Previous contracts, raw evidence, scoped history and inventory remain unchanged.

## Exact source and delta

Chart continuation baseline is `d93c7ace37603d91f1d9342152c97e8acb3d4e8c`. Existing runtime source is read-only PR42 `523e702a806a718d163cfbf62aa3fc29d8c3ef3c`, not code already present on Chart/canonical. PR17 `21039a0a7f9677b123abd8587fd8d89784a73a3c` originated P01; PR19 `c3dbf8a02c9c5ed0cf4ffb15c5532d31ae45fa3e` originated QGV/invalidation. Fresh owner/global governance is recorded by the root checkpoint separately. The diagnostic pins 18 relevant source/doc/test files and verifies working bytes equal their exact PR42 Git objects.

| v0.4 unresolved interface | Narrowed fact at v0.5 | Remaining owner action |
|---|---|---|
| Decimal wire/hash compatibility | Existing serializer accepts explicit tagged numeric strings, preserves `5.50` as a string, supports Korean UTF-8, and is invariant to object key order. Native Decimal is rejected | Accept the existing proposed lexical-decimal adapter and immutable preimage; no serializer modification is inherently needed |
| Chart publication registration | Existing extractor has four registered persisted shapes; an independent Target Theme Chart shape matches zero and raises `ExtractionError` | Determine applicability and register an exact owner-admitted subject through the selected route |
| P01 current-content authority | P01 is a research-display policy. Its production attachment hardwires the empty active grant set and refuses display. It is not an established display route for user-authored current TARGET allocation | Product/P01 owner explicitly records whether existing research policy applies, and names the applicable admitted owner route. Do not assume a research grant is required or automatically satisfied |
| Invalidation reuse | Generic `resolve_target` already supplies availability-filtered supersedes-chain mechanics. QGV-specific `qgv_binding` rejects Chart input | Reuse mechanical resolver only under owner-admitted Target subject/dependency binding; keep TARGET applicability/source authority separate |
| API existence | Web currently fetches static `data.json` and `entities.json`. Source scan found no live Chart HTTP route or API server/mount | Product/API/Web owner chooses an exact host/read interface and current-authority clearing behavior. A Python read function alone is not an HTTP API |
| Seven-file protected digest | Existing Web build copies ordinary new `.html/.js/.css` assets; an independent page and read product can avoid edits to Web validator/assembler | Accept exact page/mount/write set. Avoiding those files does not bypass authority or whole-package code identity |

Source-compatibility uncertainty around canonical serialization is narrowed. **A-G1 remains open** because policy applicability, actual admitted route, subject registration and exact current-authority behavior are not established. A-G2 still requires owner acceptance of the integration base/write set. Existing FPIA governance and source gates are not independently adjudicated by this packet.

## Existing functions that can be reused

All paths below are beneath `implementation/src/investment_system/` in the pinned PR42 tree.

| Existing exact function | Inputs / output | Reuse and limit |
|---|---|---|
| `producers.serialization.to_jsonable(value)` | Supported Python values → JSON-compatible object | Native Decimal unsupported. Explicit string encoding must precede this call; string preservation is serialization, not source admission or numeric validation |
| `producers.serialization.canonical_bytes(value)` | Supported object → sorted-key, compact, UTF-8 JSON bytes | `ensure_ascii=False`, `allow_nan=False`. Array order is preserved, not sorted. No classification/aggregation occurs |
| `producers.serialization.canonical_sha256(value)` | Supported object → canonical SHA256 | Reuse on the owner-adopted immutable payload preimage. Do not include its self-hash or mutable current authority |
| `publication.extractors.extract(document)` | One registered persisted shape → eligibility fact | Exactly one match is required. Copies stored subject hashes/status tokens; does not validate arbitrary payload bytes or admit a new Chart shape |
| `publication.facts.make_fact(**fields)` | Exact v1 eligibility keys → validated fact | Fingerprint must equal subject hash; Track C field must be NOT_RUN. No TARGET identity, root admission, classification or byte-hash verification is provided |
| `publication.predicate.decide(fact, authorizations=ACTIVE_AUTHORIZATIONS)` | Validated fact + explicit authorization tuple → publication decision | Pure predicate. Current default set is empty. Produces NOT_AVAILABLE, with schema1 NOT_AVAILABLE and official/live/track_c false. A hypothetical fixture grant is never activated by a call |
| `publication.envelope.attach_publication_envelope(bundle, records=())` | Schema-1 bundle + recognized records → copied bundle with top-level envelope | Production route uses only the empty active set; caller cannot supply grants. Section state/data stay unchanged. It does not attach to an independent ChartDocument |
| `publication.authorization.validate_authorization(record)` / `matching_grant(authorizations, kind, subject_sha256)` | Existing exact v1 grant record / exact kind+subject → validated copy / boolean | Does not issue or persist anything. Existing kinds are RESEARCH_DISPLAY, FROZEN, LIVE; no new Target kind is proposed |
| `publication.invalidation.validate_event(event)` / `event_id(event)` | Exact existing event body → validated body / canonical ID | Requires existing state/reason pair, aware dates, target hash and nonempty authority_ref. A nonempty reference alone is not authentication or evidence of a permission |
| `publication.invalidation.admit(existing, event)` | Existing immutable log + event → appended tuple | Rejects duplicate, missing/cross-target predecessor and successor of terminal INVALIDATED. Call result is not a grant |
| `publication.invalidation.resolve_target(events, target_sha256, decision_time)` | Exact target + explicit aware knowledge clock → resolution/event/defect | Filters by available_at, then resolves chain without timestamp-based head selection. Does not check TARGET applicable period, verify authority_ref, or confer display authority |
| `product.web_mvp.unavailable(reason)` | Reason → existing NOT_AVAILABLE presentation with data=None | Reuse for denied/unavailable presentation where the selected owner route requires it. Do not encode diagnostic allocations inside renderable data |
| `product.web_mvp.validate_bundle(bundle)` | Existing schema-1 bundle → validated copy | Fixed section set and states. Portfolio referential check is company_id-based. Does not register a security-scoped Chart capability |
| `product.web_mvp.build(out, bundle=None, demo=False, rig_page=None)` | Validated existing bundle → static files | Copies ordinary assets, writes data.json/entities.json and reviewed auxiliary pages. Does not implement current Chart HTTP reads or authorization refresh |

Existing producer registry only accepts the current section list. Calling a new section `chart` is refused. Squeezing Target Theme into `portfolio` does not supply a registered renderer, subject authority or correct TARGET/ACTUAL meaning. Using an extra top-level field that the validator ignores is likewise not a registered production capability.

The existing `publication.qgv_binding.provenance_from_persisted/build_binding/resolve_binding` are **not** generic Chart APIs: they require `QGV_COMPANY_RESULT`, `QGV_PRODUCER_BATCH_MANIFEST`, QGV version/universe/weight/cross-section provenance and a specific producer ID. Do not manufacture those fields for a Theme chart or duplicate that QGV contract under a Chart name.

## Denials and withholding already established

| Condition in existing P01 | Current behavior |
|---|---|
| Unsupported Chart document | ExtractionError: persisted document matched 0 publication extractors |
| Producer PASS / complete fact with no exact research-display grant | NOT_AVAILABLE; `RESEARCH_DISPLAY_GRANT_NONE`; `PRODUCER_VALIDATION_IS_NOT_A_GRANT` is recorded |
| Withheld bytes, blocked result, stale/expired, synthetic | NOT_AVAILABLE, including if a hypothetical fixture research grant is supplied |
| Frozen or Live grant without research-display grant | Does not satisfy research-display; does not change schema-1 |
| LIVE/FROZEN/OFFICIAL/VALIDATED/RESEARCH promotion request | PromotionForbidden |
| Production envelope attachment | Grants NONE, DISPLAY_RESEARCH inactive; existing section data/state unchanged |

The Web's existing render-time guard withholds invalid producer/research sections and NOT_USABLE persisted freshness into NOT_AVAILABLE/data=None. It does not currently interpret a Target Chart current-authority envelope. It loads the static bundle once; `cache:"no-store"` is a request option, not an invalidation subscription or authorization guarantee. A registered Chart renderer must clear prior displayed values when the selected exact-subject authority is denied, missing, invalid, changed or unresolved, according to the owner's accepted contract. No new polling interval/TTL/cache authority is selected here.

The old Portfolio route's `actual_weight ?? target_weight` remains an owner-owned defect to fix on its branch. An independent Target-only page can avoid that function entirely and uses only explicit TARGET results. The first slice does not depend on resolving ACTUAL holdings or making broad changes to the existing Portfolio view.

## Smallest owner-facing interface decision

This is an implementation interface plan, **not adoption**. Field names below identify the decision evidence needed, not a new executable contract or permission schema.

| Required owner receipt item | Concrete answer needed to close the existing G1 predicate |
|---|---|
| Policy applicability | Is this user-authored current TARGET display governed by existing P01 research-display policy, or a separately established applicable Product/Personal content route? Cite the existing adopted policy/owner evidence; none is inferred from the user's request |
| Admitted route | Exact existing or owner-approved subject/read interface, module/mount and state/denial mapping. No route is presumed to be already implemented |
| Subject and integrity | Exact payload hash/preimage/version; registration match predicate or route validator; actual hash recomputation before eligibility/authority assessment; source-root/catalog/assignment revision dependencies |
| Current authority | Exact subject named by the applicable current owner decision, explicit clock/reference and existing invalidation resolution; no source hash, arithmetic PASS, CLEAR event or CI PASS substitutes for authority |
| Availability / denial | No renderable allocation on absence/denial/unresolved subject. Immutable diagnostic evidence may exist separately. Existing NOT_AVAILABLE presentation is reused where applicable; no new Web state enum is invented |
| Numeric / wire acceptance | Lossless tagged strings before unchanged canonical serializer; stable arrays; self-hash and mutable authority excluded. API/Web consume the same persisted result/hash, not re-aggregation |
| Consumer handoff | Exact thin read function inputs: admitted persisted payload, applicable exact-subject authority source, explicit request/knowledge clock. It returns the same immutable payload only on the applicable accepted display path, with a separate current assessment; transport request time does not mutate the payload hash |

If owner selects P01 reuse, a Chart extractor by itself only closes structural recognition: the production attachment remains deny-only under active empty authorizations, and the research-policy applicability must be explicitly accepted. This packet does not request or issue a grant. If owner identifies a valid personal-content route, reuse its adopted controls; an independent endpoint may not create an implicit substitute authority. Until that receipt exists, an allocation-serving success path is **not established**.

## Minimal additive candidate write set and direct impact

These are owner candidate actions at a future accepted integration base, not edits performed here. Existing v0.4 source/domain/contract paths remain proposals; this packet narrows the interface/renderer portion only.

| Candidate path under implementation/ | Exact purpose | Owner | P01 seven-file digest | Whole-package Python code_hash |
|---|---|---|---|---|
| `src/investment_system/product/chart_api.py` ADD | Thin authority-aware read service for persisted accepted Chart payload; no calculation | Product/API + Chart + Publication | No direct membership | Yes |
| `tools/serve_chart_api.py` ADD, only if selected | HTTP mount/host adapter around that same read service, with one payload/authority contract | Product/API + Web | No | No direct membership |
| `src/investment_system/product/web_assets/target-theme.html` ADD | Independent Target-only page; no old Portfolio fallback path | Web + Chart | No | No |
| `src/investment_system/product/web_assets/target-theme-chart.js` ADD | Authority-first consumer and materialized projection renderer; selection, counts, exact supplied weights/table | Web + Chart + Publication | No | No |
| `src/investment_system/product/web_assets/target-theme.css` ADD | Accessible independent page styling | Web | No | No |
| `src/investment_system/publication/extractors.py` MODIFY, only if P01 route selected | Owner-accepted structural subject extraction; no predicate exception | Publication/P01 | No direct membership | Yes |

An owner can first expose the standalone page without editing `app.js` or `index.html` navigation; discoverability inside the cockpit is a later Web owner choice. Existing `build()` copies this ordinary `.html/.js/.css` naming and needs no protected builder edit solely for assets. It does **not** automatically supply their Chart data or current-authority service; the chosen API/static release mechanism is still an owner task. Copying a payload file after build is not an authorization route.

No protected validator/assembler change is inherently needed for this additive candidate. `publication/extractors.py` lies outside the seven-file digest but remains Publication-owned, and its change alters whole-package code_hash. All new package Python (including source/domain/contract additions outside this table) affects Track C whole-package code_hash. All selected owner paths still require attribution, applicable owner checks and actual merge-result FPIA. Unchanged digest does not waive policy/owner acceptance; no repin blocker is manufactured for unchanged files. Frozen Personal contracts, P01 authorization/predicate policy and Track C modules are untouched.

## Diagnostic receipt and next exact action

`EXISTING_AUTHORITY_INTERFACE_DIAGNOSTIC_v0.5.json` records:

- 18 byte-verified source pins at exact PR42 head.
- 11 selected unchanged P01 owner test functions and all 16 unchanged QGV-binding test functions: **27 PASS / 0 FAIL**, using the repository's existing `mini_pytest` raises shim. This is **not pytest**, not a production Chart test, not an independent FPIA adversarial review.
- Actual existing-function probes: tagged numeric strings canonicalize losslessly; Decimal fails; Chart extraction and QGV binding fail; active grants remain empty. A synthetic negative-only event probe shows an available event with future effective_at resolves CLEAR mechanically, so TARGET applicability cannot be inferred from that call. The fixture is never admitted or persisted as authority.
- Track C import guard active; loaded Track C modules = 0. No grant written/activated. Production Chart tests and actual Chart merge-result FPIA = NOT_RUN.

Initial real-pytest attempt found no installed pytest and ran no cases; this is recorded rather than disguised as a pytest run. The unchanged existing offline shim was then reused. No tests mirroring a new Chart implementation were written.

Next owner action: **Product/Publication/Personal owner fills the G1 policy-applicability/route receipt above; Web/API owner accepts the additive page/read mount and exact write set as part of G2.** Chart then validates that accepted receipt and concrete source pins. No new D3 is asserted by this packet; if owner finds an actual policy change is necessary, that owner must report its exact change and decision boundary first. Existing source gates/FPIA governance remain with their owners. No external message/comment, other branch write, merge, grant, Freeze, Official/LIVE promotion, Holdout access or PIT relaxation occurs here.
