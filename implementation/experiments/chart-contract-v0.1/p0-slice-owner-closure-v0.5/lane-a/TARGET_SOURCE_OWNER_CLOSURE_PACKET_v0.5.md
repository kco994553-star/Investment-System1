# Target Strategy Theme owner admission request v0.5

**IMPLEMENTATION_NOT_READY; open 6 / closed 0.** Source-owned gates A-S1/A-S2/A-S3 remain open. This packet makes the next owner response concrete; it is not an admitted source, a production schema, a grant or activation. Existing v0.4 diagnostics and history are reused without running the source/Market replay again.

## Bounded delta from v0.4

Chart source is fresh PR #41 `d93c7ace37603d91f1d9342152c97e8acb3d4e8c`, rather than the previous `581c61c`. Canonical remains `b8e39a2196a6d7794a04a0cd5393c68329e126ca`; inspected FPIA owner tree is `523e702a806a718d163cfbf62aa3fc29d8c3ef3c`; Global owner handoff is `9d9b2b2b942cfa6d1f7b296ad81d380ec6a70b3e`. Nine selected source/identity/Personal handoff paths were pinned at these exact refs. Eight selected Target/identity/Personal source paths agree between Chart/canonical/FPIA. The Conflict Register has the already-recorded Integration overlay; its C-25/D-27/D-28/D-29 source boundary remains unchanged. No new Target root, identity admission, Theme catalog or assignment revision was found in this scoped evidence.

The concrete new deliverable is [TARGET_OWNER_ADMISSION_REQUEST.json](TARGET_OWNER_ADMISSION_REQUEST.json): 19 existing reference row keys, exact authored weight strings, four Theme relations and pinned provenance, plus unresolved owner-return fields left null. [TARGET_OWNER_DELTA_EVIDENCE.json](TARGET_OWNER_DELTA_EVIDENCE.json) records exact source blobs/hashes and the bounded package construction search. No production readiness promotion occurred.

## Existing identity capability to reuse

`contracts/global_universe.py` already defines `IssuerIdentity → SecurityIdentity → dated ListingIdentity`; security identity is distinct from ticker/listing and listing validity is explicit. It is a reusable common contract, not a loaded production lookup for these 19 Target rows. Six scoped searches on canonical/FPIA `implementation/src` found no Target ModelPortfolioSnapshot construction, explicit global identity construction, or Personal SecurityRecord/CompanyLink/resolver construction. This is evidence within those pinned package sources; it does not prove absence of unpublished owner data.

`personal/security.py` resolves explicit, dated SecurityRecords using strong keys or ticker+exchange and fails closed on ambiguity. It must receive admitted records. `CompanyLink` is an explicit reviewed link with default status PROPOSED under C-25, rather than an automatic alias between company_id and security_id. Existing D-27/D-28 keep company_id as the legacy US key and ticker as display; D-29 establishes Tokyo Electron at company level while leaving the TSE-versus-ADR listing choice unresolved. The observed Yahoo `8035.T` price candidate does not adopt that security for the Target root. Existing issuer association/CIK/provider aliases and test fixture IDs cannot substitute for an admitted Security subject.

Target needs the owner’s exact security/share-form relation, not a new Chart identity system. Full Market listing/session/calendar/price admission is independent of current Target Theme and is excluded from this source gate. The companion Market audit owns its dated listing/provider lookups.

## Source-root authority boundary

`QGV Portfolio · Specification v1.1.md` §2 is the authoritative authored value/membership source for this inspected baseline. Its 19 rows agree with `OFFICIAL_V11_TARGETS` and the preserved reference. This previously verified agreement is reused, not promoted to a globally adopted current production root. The specification date `2026-09-14` is a document baseline label; the reference extraction `as_of` and Git clocks do not supply source effective_at/available_at/current adoption.

The role of `PortfolioEngine.official_v11()` remains REFERENCE_FIXTURE. The separate 17-row US-working fixture remains a different book. `ModelPortfolioSnapshot` is the existing Frozen model contract, with no source-producing 19-row construction found in the scoped current package sources. Frozen contracts remain unchanged.

Owner-return fields in the packet are null until an exact source admission exists. This includes portfolio/root/revision identity, current applicability semantics, separately evidenced availability, completeness, denominator, security/issuer namespace and reviewed company link, Theme catalog/concept/version and assignment revision. Observed source weights/labels are populated only in the `observed_*` sections. Missing fields remain unknown; there is no guessed date, invented ID, current-root adoption or production payload.

Source adoption is separate from A-G1 Product/publication authority. Neither the user’s known target totals nor arithmetic/reference validation creates a code-defined publication grant. User-authored Theme is not external GICS and does not require a GICS entitlement to resolve this Target source.

## Three owner closure receipts

| Gate | Owner | Exact response that permits rejudgment | Current state |
|---|---|---|---|
| A-S1 | Target/Personal source owner | One immutable current TARGET root/revision with named portfolio/version, full19 rows plus explicit cash, source/hash/use receipt, current applicability semantics and completeness/denominator; explicit routing resolves authored specification versus reference fixture versus adopted root | OWNER_ACTION_REQUIRED |
| A-S2 | Identity + Target owner | Root-row→reviewed company/issuer→admitted common security namespace map, exact security type/share form, identity revision/source and19-row completeness; preserve C-25/D-29 without inventing IDs or adopting Yahoo symbols | OWNER_ACTION_REQUIRED |
| A-S3 | Target/Theme source owner | Adopted user-defined Strategy Theme catalog/concept/version and complete security assignment revision bound to that root/map, source/hash/effective validity and completeness; retain30/25/20/25 source allocation and prior revisions | OWNER_ACTION_REQUIRED |

Owner may return the receipts together, but closure predicates remain independent. Root weights can be complete while security identity or Theme revision is unadopted. Closing source gates leaves A-G1 Product/authority/interface, A-G2 exact write-set/owner/base acceptance and A-G3 Integration/FPIA governance closure separate. The total remains six distinct pre-code gates, rather than counting19 missing IDs separately. Any future authoritative revision that changes pinned values requires an explicit owner record; Chart does not select between conflicting inputs.

The current Target source does not depend on ACTUAL, GICS, Investment Type, Overlap, quarterly Actual history or OHLCV. ACTUAL remains NOT_AVAILABLE with its own root/snapshot/denominator/provenance and no Target fallback. Future classification history appends immutable root/catalog/assignment revisions; a newly evidenced current receipt cannot fabricate earlier historical knowledge time.

## Nineteen preserved source rows

The keys below already exist in v0.4; they are reference row keys, not production security IDs. Every owner-return security and Theme ID remains null. Each JSON row also carries original specification/code lines, JSON pointer and immutable source commit/blob/SHA256.

| Existing source row key | Legacy company_id | Observed target | User-defined Strategy Theme | Preserved reference pointer |
|---|---|---:|---|---|
| `reference:company:asml` | `asml` | 9% | 반도체 장비 | `/holdings/0` |
| `reference:company:lrcx` | `lrcx` | 6% | 반도체 장비 | `/holdings/1` |
| `reference:company:klac` | `klac` | 5.5% | 반도체 장비 | `/holdings/2` |
| `reference:company:tokyo_electron` | `tokyo_electron` | 5% | 반도체 장비 | `/holdings/3` |
| `reference:company:hanmi` | `hanmi` | 4.5% | 반도체 장비 | `/holdings/4` |
| `reference:company:nvda` | `nvda` | 8% | AI·반도체 | `/holdings/5` |
| `reference:company:amd` | `amd` | 5% | AI·반도체 | `/holdings/6` |
| `reference:company:avgo` | `avgo` | 5% | AI·반도체 | `/holdings/7` |
| `reference:company:qcom` | `qcom` | 4% | AI·반도체 | `/holdings/8` |
| `reference:company:intc` | `intc` | 3% | AI·반도체 | `/holdings/9` |
| `reference:company:msft` | `msft` | 7% | Big Tech | `/holdings/10` |
| `reference:company:googl` | `googl` | 7% | Big Tech | `/holdings/11` |
| `reference:company:amzn` | `amzn` | 6% | Big Tech | `/holdings/12` |
| `reference:company:rtx` | `rtx` | 6% | 기타산업 | `/holdings/13` |
| `reference:company:stry` | `stry` | 5.5% | 기타산업 | `/holdings/14` |
| `reference:company:etn` | `etn` | 5% | 기타산업 | `/holdings/15` |
| `reference:company:hubb` | `hubb` | 3.5% | 기타산업 | `/holdings/16` |
| `reference:company:gev` | `gev` | 3% | 기타산업 | `/holdings/17` |
| `reference:company:rok` | `rok` | 2% | 기타산업 | `/holdings/18` |

The prior v0.4 replay verified exact100%, explicit baseline cash0%, a single19-row partition, four group totals30/25/20/25 and six negative cases. This packet preserves that result; current admitted production denominator/total remain NOT_AVAILABLE because no root is admitted. Current baseline cash0% is not a policy that future roots must have zero cash.

## L1~L5 and next exact step

L1 remains VERIFIED_REFERENCE / production BLOCKED. L2 exact reference aggregation is VERIFIED_DIAGNOSTIC but shared production projection is NOT_IMPLEMENTED. L3 minimal contract is a proposal/NOT_ADOPTED. L4 production renderer is NOT_IMPLEMENTED. L5 prior offline diagnostics are preserved, while production L1→L5 validation is NOT_RUN. No production tests, package adapter, Frozen change or merge-result FPIA was executed for this source request.

Next action: Target/identity/Theme owners return new immutable A-S1/A-S2/A-S3 receipts against these exact19 keys. Verify the new receipts with the existing v0.4 root/completeness/Decimal-negative diagnostics, then rejudge all six gates using separate Product/Web/Integration evidence. If any receipt conflicts with the pinned source, preserve both and obtain explicit authoritative routing; do not rewrite existing evidence or silently choose. No new Chart D3 or repeated confirmation of known30/25/20/25 is created here. Existing C-25/D-29 identity and Integration decisions remain in their owner paths.
