# GICS feasibility / data / rights / history audit v0.3

**Result: GICS is a coherent industry-exposure candidate, but Target GICS exposure is BLOCKED for current production readiness. Official/authorized complete assignments admitted: 0/19.** Public documentation is PARTIAL source readiness, not an assignment feed or permission to publish it. No provider, license, taxonomy catalog or company assignment is adopted by this audit.

Recorded 2026-10-05 KST; exact audit timestamps and original PR41 pin `54ee25446ccf6cfa32ddf164a8ed31b7e1036b9a` are in `REPOSITORY_EVIDENCE.json`. Preserve baseline `8668c69`, v0.1/v0.2, and Core81 / Extended24 / ResearchCandidate8. This is a scoped documentation delta. No production, Protected/Frozen, grants, Official/LIVE, Holdout, or other-owner edits.

## 1. What was established from official documents

MSCI describes four company classification levels and one principal-business assignment per level. S&P's current public page lists 11 sectors, 25 industry groups, 74 industries and 163 sub-industries. This supports a **Sector-first, optional hierarchy drill-down proposal**, without deciding any actual company codes. [GICS-S01, GICS-S02]

The current S&P-linked methodology is **April 2026**. Earlier February 2025 documentation remains historical evidence. The newer document describes company-linked equities inheriting the company classification and review following major corporate actions; classification evidence still requires a verified security/listing→company join. [GICS-S03]

S&P offers separate **GICS Direct** current classifications and **GICS History** historical company classifications. Marketplace describes history through from/thru validity dates; the independent S&P product page confirms historical codes, names and identifiers. Public marketing does not disclose this project's entitlement or establish every desired company's coverage. The Marketplace open returned zero extractable lines, so its details remain search-retrieved marketing rather than an inspected feed schema. [GICS-S04, GICS-S05]

A July 2026 consultation addresses AI/semiconductor categories and is open through October 30, with results planned for November. It does not establish adopted taxonomy changes. Do not create production AI/semiconductor GICS categories from consultation proposals. [GICS-S09]

## 2. Readiness matrix

| Required evidence | Current state | What the evidence supports / gap |
|---|---|---|
| Four-tier industry meaning | READY as documented candidate | Global company principal-business hierarchy; separate from custom strategy buckets and overlapping investment types |
| Catalog structure/version | PARTIAL | Public current/historical structure links exist; authoritative catalog bytes/version/effective interval and use rights have not been admitted |
| Current official company assignments | NOT_AVAILABLE | Product route confirmed; no authorized complete 19-company assignment records captured |
| Exact security→issuer/company mapping | BLOCKED | Provider symbol or company label alone cannot join a licensed company code to the correct equity/listing/history |
| Assignment effective date/history | PARTIAL product route / NOT_AVAILABLE records | History offering and from/thru semantics advertised; actual revision records and interval boundary semantics not inspected |
| Publication / available_at / vintage | NOT_AVAILABLE | An effective interval or later fetch does not establish when the old record was released or knowable |
| Source/method/version/provenance | PARTIAL | Primary documentation register exists; individual assignment source IDs, raw hashes and producer/version binding absent |
| Usage entitlement | NOT_VERIFIED; production admission BLOCKED | No user-specific order, permission or authorized vendor agreement inspected |
| API/Web/MCP display, derivation and access rights | NOT_VERIFIED; production admission BLOCKED | Internal use, hosted service, recipient access and raw/derived distribution must be checked separately against actual rights |
| Quarterly historical GICS snapshots | BLOCKED | Need target/actual historical snapshot plus point-in-time catalog/assignment/vintage and identity joins |

“READY as documented candidate” is not production approval. “BLOCKED” describes the present evidence boundary, not a claim that GICS can never be legally used or must always be purchased. No fee, account or license status was inferred.

## 3. Licensing / redistribution boundary

MSCI's Terms of Use were revised **2026-07-15**. Their public/no-order scope is internal non-production; express order permissions govern database/derivative creation, third-party/cloud redistribution and unauthorized automated extraction, including AI agents and MCP. Separate agreements may supersede conflicts. None was supplied or examined. [GICS-S06]

S&P's website terms distinguish personal/internal/non-commercial access from redistribution and derived-data/database use. Its SPDJI subsection adds limits on classification/history databases, derived data and unauthorized display/disclosure. The methodology separately describes display/derivative/distribution licensing. These public terms do not replace a GICS Direct/vendor agreement. [GICS-S07, GICS-S03]

Implementation consequence (audit inference): **a personal MVP is not, by itself, proof of production entitlement**. Nor is a purchased internal feed, if one later exists, proof of rights to publish company assignments or make them accessible to a third-party hosted API/MCP. Conversely, an authenticated personal view should not automatically be called public redistribution: the applicable agreement and actual audience/access/hosting determine the unresolved rights. A Sector-level aggregate may still be derived output; do not presume aggregation removes source-use restrictions.

No contact forms submitted, sign-in/account probing, price enquiry, purchase, entitlement activation, bulk MSCI/S&P extraction, or bypass of any access control occurred. Bounded quotations support audit findings; full copyrighted catalog, methodology or feed content is not copied into this directory.

## 4. Effective time is different from available time

The 2022 structure-change announcement is a concrete example: it was dated March 31, 2022, described implementation after the March 17, 2023 close, and separately scheduled client-list releases. The announcement, assignment list, effective event and project acquisition are different evidence objects. [GICS-S08]

For future admission preserve, when sourced: catalog revision/effective interval; company assignment revision/effective interval; source publication or distribution time; acquisition/observation time; ingestion time; and original vintage hash. Unknown publication/availability must stay UNKNOWN. A provider from/thru interval is not a knowledge-time record. Historical codes alone do not prove historical PIT eligibility; no present code may be copied backward into older quarters. Restated histories require original vintage/revision evidence rather than assuming later data is what users knew earlier.

## 5. Bounded local evidence: GICS-like labels already exist, but are insufficient

PR41 contains a secondary Wikipedia S&P500 raw snapshot with GICS-labeled sector/subindustry columns for **16/19** target provider symbols. Missing from that snapshot: **ASML, 8035.T, 042700.KS**. The hash and row-presence inventory are in `REPOSITORY_EVIDENCE.json`; no assignments or classification values were copied into a production object.

The reconstruction tool captures sector/subindustry in its regex, but `parse_constituents` retains only security name, date-added and CIK. It reconstructs index membership, not historical industry classifications. The raw snapshot has no admitted licensed-feed rights, company-assignment effective/available revision manifest, complete19 coverage or proven classification history. Thus **0/19 official/authorized production assignments admitted** remains the correct denominator. This does not claim no isolated public company label exists anywhere.

The prior `portfolio_reference.json` calls its grouping USER_ALLOCATION_GROUPS and explicitly says not GICS. SEC SIC, JPX SICC and KRX KIND remain named native candidates; they are not converted into GICS by labels, sector names or an unsourced lookup table. A future crosswalk is a separate versioned mapping problem with its own evidence, coverage and rights assessment.

## 6. Next permitted work and later implementation dependency

Permitted now: classify documentation/source readiness; inspect already-authorized evidence; design native namespace, provenance and rights envelopes; preserve append-only review records; refine source-selection alternatives without selecting a provider. Continue Target Strategy Theme independently using the user-defined allocation source, without naming its 30/25/20/25 buckets GICS industries.

Before Target GICS runtime work: obtain an authorized source manifest scoped to current/historical assignments; verify19 identity joins and catalog/assignment revisions; distinguish current-view readiness from historical PIT readiness; establish permitted local processing, retention, derived exposure, Web/API audience and future MCP access. In the absence of those inputs display an unavailable GICS capability, not guessed sectors or a fabricated pie.

These documents/evidence have no P01 or package code_hash effect. Any future package Python adapter/projection changes affect Track C whole-package code_hash; any protected validator/assembler/publication-path change requires owner path inventory plus exact merge-result Integration/FPIA. FPIA PASS would not supply missing GICS rights/data/vintages. This audit creates no new active D3 decision; no licensing/provider choice or runtime approval was requested or exercised.

## Source / verification artifacts

- `SOURCE_REGISTER.json`: 9 primary source URLs, document dates, tool refs, extraction limitations and bounded excerpt hashes.
- `BOUNDED_EXCERPTS.json`: fewer than25 quoted words per source; not a catalog or assignment dataset.
- `REPOSITORY_EVIDENCE.json`: local immutable file hashes and target presence audit, bounded absence scope.
- `SHA256SUMS.json`: artifact integrity, not full webpage/PDF or production feed integrity.

URLs, not transient tool reference IDs, are the durable source locator. A hashed bounded excerpt is not a raw-source hash or permission record. This source/design audit does not establish production regression, Actions or FPIA PASS.
