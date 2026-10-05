# Minimal ChartDocument v0.2 — Current Target Strategy Theme

Status: PROPOSED / NOT_ADOPTED / NOT_FROZEN. This is a scoped owner contract proposal, not a production schema or publication authorization. Earlier v0.1/v0.2 and all evidence remain unchanged. The first slice is `Target Strategy Theme Allocation`, explicitly `User-defined Strategy Theme / Portfolio Bucket`.

## Scope and flow

Verified current TARGET source and sourced Theme assignments → one domain Theme projection → one immutable Chart/Product payload → one authority-aware read service → API → Web. A future MCP reads the same payload but is outside this work.

ACTUAL remains a separate NOT_AVAILABLE product with no denominator or data substituted from TARGET. GICS, Investment Type, Type Overlap, prices, valuation/FX, quarterly ACTUAL history, Market admission and QGV scoring are not required inputs to this current slice.

## Minimum logical payload

Names below express responsibilities for owner alignment; neither field spelling nor a new state enum is adopted.

| Role | Minimum evidence/value |
|---|---|
| Product subject | Chart capability/current TARGET request identity; schema/projection version; immutable payload hash and explicit hash-preimage/encoding version |
| Target root | Authoritative portfolio identity/version and immutable root hash; TARGET basis; applicable/effective period with evidence; source artifact/revision/hash; declared completeness; denomination of target weight; explicit authored cash target if applicable |
| Constituent | Stable target row/holding reference; sourced security identity and namespace; label; original target numeric token/type; assignment reference. A ticker/company label does not establish a security/listing |
| Theme catalog | Dimension=StrategyTheme; user/system-defined taxonomy namespace/version; stable theme key/name; source/hash and effective period. No label is named GICS |
| Theme assignment | Security → Theme relation; assignment revision; taxonomy/version; effective period; exact source/artifact/hash; membership completeness. For a four-bucket partition each admitted constituent has one evidenced membership; conflicts are diagnostics |
| Calculation | Authoritative numeric input, owner-approved arithmetic/context/version and encoding; exact denominator/total validation evidence; aggregation result hash and projection version |
| Theme segment | Theme key/name; domain-produced target weight; constituent count; materialized constituent references/list and each target weight; catalog/assignment/effective-period references |
| Assessment | Capability/reason/evidence distinguishing source absence, unknown/partial membership, invalid values and verified zero/empty. Backend validation and authorized product publication are separate facts |
| Time roles | Authored/effective dates and any actual observation/ingestion/access times each retain their role. Missing available_at is explicit; receipt time does not establish historical availability. No Market session/close field is required for this TARGET view |
| Rights evidence | Source provenance plus evidence of allowed intended use if applicable. UNKNOWN stays UNKNOWN. An authored user allocation is not blocked by missing GICS rights; no external classification feed is used |

The following mutable authority information stays outside the immutable payload hash: exact product subject/hash, consumer/use scope, owner decision/time, grant or absence, invalidation/current authority reference. Use existing Publication/P01 contracts once owners align them; no new permission states or grant is issued here. Unknown/absent authority fails closed at the read service and renderer handoff, including cached payloads.

## Narrow arithmetic semantics

The domain owner aggregates admitted source target values once. For Theme t: target_weight(t) = sum(target_weight(i) for admitted constituent i assigned to t). The denominator is the admitted TARGET root's full target allocation including any explicitly authored cash. Do not normalize to only classified holdings, deduplicate by ticker, repair a non-100 total, divide across Themes, apply a tolerance, invent zero cash or use ACTUAL weights.

Current authored reference values can be validated exactly in Decimal from their decimal source tokens. This proves reference arithmetic, not root admission. Binary float inputs keep their original representation and require an explicit lossless owner adapter; converting a float's formatted display back to Decimal does not restore original decimal provenance. Existing personal Model validation and its tolerance are not changed. No numeric precision/rounding/epsilon policy is introduced.

Bounded implementation detail specified here: for the documented finite decimal TARGET tokens, retain token/sign/coefficient/exponent and sum without rounding (exact decimal coefficient alignment, independently checked by rational arithmetic). Record percent versus ratio explicitly; a 30% result encodes its source/result decimal string and unit, not an implicit 30 versus 0.30 conversion in the renderer. Preserve source numeric metadata; render conversion cannot overwrite it. Unsupported float input to this lexical-decimal projection is diagnostic until an owner adapter is supplied; it is not coerced with Decimal(float). This defines only the current authored-token slice, not a replacement financial numeric policy.

Proposed wire/hash detail: Decimal results are explicit strings with numeric-kind/unit/source/calculation evidence. Arrays are ordered by stable root/Theme/constituent keys before serialization; field keys use existing canonical serializer ordering. Reuse the existing UTF-8 canonical JSON rule (sort_keys=True, compact separators, ensure_ascii=False, allow_nan=False) after explicit Decimal→string encoding. The hash preimage is the versioned immutable payload without its self-hash or current authority envelope, and includes numeric/classification/source/result revisions. A differently encoded revision has a different version/hash; do not silently repair an old subject. This is now a concrete implementation design; production owner registration remains unresolved, schema Freeze remains NOT_DONE.

Constituent count and list derive from the admitted root/assignment relation, not the UI. Completeness is checked against that exact root; 19 captured rows alone do not prove current portfolio completeness. Future revisions append catalog/assignment/root revisions and invalidate exact downstream subjects; old payloads/hashes remain immutable. Historical selection needs additional availability evidence and is outside the current slice.

## Contract and UI behavior

- A current root without admission returns source absence/reason; known invalid root/membership returns a diagnostic. Neither carries a renderable allocation. A verified zero target for a constituent is valid; an empty input cannot satisfy a full 100% four-Theme TARGET root and is not promoted to valid-empty.
- A positive admitted TARGET slice is labelled `Target Strategy Theme Allocation`; show name, exact domain-produced weight, count and a selectable Theme segment with its constituent list/weights, taxonomy/version and effective period. Provide a keyboard-operable list/table equivalent and keep display formatting distinct from source values.
- Renderer consumes the materialized projection. It only lays out/formats values and converts them to coordinates; it does not assign Themes, aggregate allocation, renormalize data or infer current identity.
- No `actual_weight ?? target_weight` path is used by this capability. ACTUAL NOT_AVAILABLE remains visible as a separate product state if requested.
- API returns the verified immutable payload and the current authority assessment for that exact subject. API/Web use the same numeric result/hash; transport envelopes and request/access times do not mutate that hash.
- Registration must be aligned with the existing Product/Producer contract. A standalone experiment endpoint or a bypass of P01 is not production readiness. The current trial has no chart capability registration/read API and its serializer rejects Decimal.

## C01–C08 applied to these two Lanes

| Candidate | Verdict | Minimum current TARGET use / Market follow-up |
|---|---|---|
| C01 | KEEP | Root/input/result hash immutable; current publication authority separate. Market retains raw request/payload revisions |
| C02 | KEEP | Source token/type, owner calculation context/result and lossless encoding. Market raw quote/adjclose numeric representation is preserved |
| C03 | CHANGE | Per-capability absence/diagnostic/partial/known-zero/verified-empty. Do not add these as unapproved Web state enums |
| C04 | CHANGE | TARGET root/weights/cash evidence only. ACTUAL positions/valuation/FX are independent future requirements |
| C05 | CHANGE | TARGET effective/current applicability with explicit time roles. Market separately requires dated session/provider/availability clocks |
| C06 | CHANGE | Theme catalog+assignment revision/completeness only for this slice; GICS and Types stay separate capabilities |
| C07 | KEEP | Exact payload subject publication/invalidation/read scope, never generic CI/validation permission |
| C08 | KEEP | Retain proposed separation of source-use rights and product authority. Source applicability differs by Lane; this verdict does not adopt rights/permission schema |

DROP=0. C08 was previously an additional proposal; KEEP here retains that proposed responsibility only. Production schema Freeze remains NOT_DONE. The Market-specific listing/session/action/basis evidence objects are deferred until that Lane is admitted; they are not mandatory TARGET fields.

## Compatibility and required owner alignment

Existing: PR41's experiment requires unrelated qgv_version/type_catalog and integer units, calls buckets industry and gates observed data. Trial Product/Producer uses Web schema-1 envelope/portfolio holdings, a non-Decimal serializer, no shared chart read service, and portfolio display mixes target/actual fallbacks.

Proposed: additive independent TARGET Theme capability, one domain projection, registered owner-controlled shared payload and read service, explicit source/applicability and lossless numeric encoding. Reuse the visual layout only after relabelling and consuming the shared domain result; do not promote the old experiment contract.

Impact: package Python changes affect Track C whole-package code_hash. The proposed primary path uses an independent registered Chart read product and avoids the seven-file P01 digest paths; it still requires approved authority semantics and owner write-set acceptance. If Product/Web owners choose the existing portfolio section integration, changes to protected Product validator/Producer assembler affect P01 and require the explicit owner branch. API/Web must preserve current authority behavior and remove the basis fallback for this slice under their owners. See governance path matrix for exact paths and boundary evidence. No protected/package production implementation occurs in this checkpoint.
