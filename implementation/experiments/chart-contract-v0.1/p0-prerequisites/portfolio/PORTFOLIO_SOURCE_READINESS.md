# P0 Portfolio production prerequisite audit

Status: **SOURCE_AUDIT_COMPLETE / ACTUAL_NOT_AVAILABLE / CLASSIFICATION_ASSIGNMENTS_NOT_AVAILABLE**. This is read-only evidence work. No production adapter, schema implementation, catalog, assignment, threshold, Frozen edit or publication action is included.

## Pins and evidence boundary

- PR41 design baseline: `97685dd` (full SHA recorded in `EVIDENCE.json`); the immutable P0 v0.1 design is preserved.
- Integrated source inspection: `acaf1b5a82859ac2750a130ebe88f8b4d272ac66` in `audit-trial`, **NON_CANONICAL**.
- Canonical baseline cited by v0.1: `b8e39a2196a6d7794a04a0cd5393c68329e126ca`.
- Exact source blobs / SHA256 / scope of absence searches are recorded in `EVIDENCE.json`.
- The repository was inspected; user accounts, broker credentials and external private positions were not accessed. A negative result means absent from the inspected checkout, not proof that the user owns no securities.

## Actual-data readiness

| Input / capability | What actually exists | Readiness / limiting evidence |
|---|---|---|
| Actual position source | `personal/portfolio.py` accepts only `PositionSource.BROKER` or `USER_ENTERED`; `personal/ports.py` declares read-only `BrokerAdapter` | **NOT_AVAILABLE**: no concrete broker implementation or actual user position artifact found. `ActualPortfolioSnapshot` constructors outside its class occur in `tests/test_pil_p0_contracts.py` fixtures. `CURRENT_HANDOFF` says Track B P0 Frozen, P1+ NOT_STARTED, no live broker/integration |
| Current reference target | `qgv/portfolio.py: OFFICIAL_V11_TARGETS` stores 19 reference target weights; `contracts/portfolio_input.py` distinguishes GENERIC_INPUT / REFERENCE_FIXTURE | Current repository target is a reference, not broker data. Cannot claim the observed Git extraction time is the 2026-09-14 historical publication time |
| Model target contract | `personal/portfolio.py: ModelPortfolioSnapshot` has strategy/universe/policy/calculation versions, unique security IDs and an existing sum check | Contract reusable; actual source/history and target producer admission remain prerequisites. No tolerance changed |
| Account aggregation | `ActualPortfolioSnapshot.weights()` sums position market values by security ID across accounts; total includes all positions and cash | Existing calculation reusable. `account_scope`, `complete`, `sync_quality` must be retained; the method computes for incomplete data too, so its existence is not proof of a complete eligible donut |
| Market value | `Position.market_value: Money`; `Money.amount: Decimal`; quantity, price_as_of, position_as_of carried | Supplied market value, not recomputed by Actual contract. No price artifact/hash/valuation-method ref or source available_at carried. Chart must retain source valuation lineage rather than multiply quantity by a second price |
| Actual weight | Domain returns `dict[security_id, Decimal]` with positions / total market value | Preserve exact domain result. Cash share is not returned in `weights()`; a single owner-approved composition projection must retain a cash amount/denominator reference. Never use the float `portfolio_gap` output as the authoritative Decimal weight source |
| FX / PIT | `personal/money.py: convert` requires explicit `FxRate.available_at <= decision_time`, marks old quotes STALE by caller `max_age`, returns `ConvertedMoney(original, converted, fx, ...)` | Reusable checks; no real FX dataset/broker valuation binding found for actual holdings. `ActualPortfolioSnapshot` checks base-currency equality, not availability of prices/positions/FX |
| Quarterly actual history | Requirement in `QGV Portfolio · Specification v1.1.md` §14; read-only `BrokerAdapter.get_transactions(account_id, since)` Protocol | **NOT_AVAILABLE**: no actual quarterly snapshot persistence/source or broker transaction connector found. Current positions do not establish old positions. Public ETF holdings / SEC 13F / 10-Q monitoring are not the user's account history |

TARGET and ACTUAL stay distinct even when their numeric values are equal. ACTUAL absent means a structured unavailable result (`NOT_AVAILABLE`, with actual-source reason), not an empty portfolio, zero total, cash-only account or target fallback. A verified complete zero-position account is a different fact and needs its own evidence. A complete account with nonpositive total/signed positions is a view-capability case, not the same as source absence. No unsupported case is repaired by normalization.

### Important source gaps surfaced by applying v0.1

1. **FX lineage falls out of the actual object.** `ConvertedMoney` preserves original amount/currency and FX data, but `Position.market_value` stores only the converted `Money`. The same loss applies to `cash: tuple[Money, ...]`. An additive evidence binding must retain the conversion object or immutable original/FX references; passing only the actual dataclass cannot certify FX/PIT provenance.
2. **Cash lacks an account/time/source identity.** `ActualPortfolioSnapshot.cash` amounts have no account ID, position/price timestamps, source or available_at. Source evidence must associate each cash item with account/snapshot completeness and conversion lineage. Do not retrofit account IDs by tuple order.
3. **Completeness is a claim requiring evidence.** The domain validates position account inclusion but has no received/missing/expected-account receipt, per-account sync history or atomic sync boundary. `complete=True` alone does not prove all accounts were fetched. Incomplete actual is not equivalent to zero holdings.
4. **Time fields are descriptive, not availability.** Position times and snapshot `as_of` do not have attached availability facts; these dataclasses do not invoke `TimeStamps` on construction. A timezone-aware cut-off check over each material input is still required. Acquisition can evidence that the captured bytes were obtained then; it cannot prove older knowability.
5. **Aggregation context is not pinned.** Decimal sums/divisions follow the active Python Decimal context. The repeating weight output needs context/ordering/source refs; choosing a new precision/rounding rule is outside this audit. Money / Decimal hash encoding does not itself reject every non-finite Decimal: finite-value admission remains a separate prerequisite already stated by v0.1.
6. **Same security in several accounts is intentional.** Do not copy the JS demo's duplicate-ID rejection onto positions. Repeated same-account rows still need source row/position IDs and completeness/reconciliation evidence; do not silently deduplicate identical-looking input rows.

## TARGET/ACTUAL contamination audit

The existing model-side `contracts.models.Holding.actual_weight` is not an actual account weight. `qgv/portfolio.py: from_input`, `official_v11`, `us_working` seed it from target weights and model cash assumptions. `evaluate` can retain that model value when shares/price are missing. These paths remain unchanged and are not admitted as ACTUAL source data.

The integrated Web `product/web_assets/app.js` still uses `actual_weight ?? target_weight` in company detail and holdings view. This violates the requested production separation even when its values come through a correctly hashed producer. Protected Web-owner correction is necessary later; this audit does not edit it.

`producers/adapters.py: portfolio_section` accepts `contracts.models.PortfolioSnapshot`, not `personal.ActualPortfolioSnapshot`. A production actual document requires registered owner routing rather than relabelling the model object.

## Classification source readiness

**Taxonomy documentation, a company assignment, its effective validity, and its information availability are four distinct inputs.** Existing 30/25/20/25 group labels are `USER_ALLOCATION_GROUP`, not GICS/SIC. Search metadata is explicitly `SEARCH_PRESENTATION_ONLY` and cannot supply financial classification or historical PIT evidence. No actual-company industry/type assignment dataset with all requested provenance fields was found.

The following are concrete, publicly inspectable **candidate source routes**, not activated providers or selected taxonomies. A public document is not a complete authorized historical assignment feed.

| Candidate | Source/identity level | Version/effective-period candidate | available_at / history limits | Current result |
|---|---|---|---|---|
| Existing user allocation groups | `qgv/identifiers.py` + `qgv/portfolio.py`, company label → security requires reviewed crosswalk | Preserve source Git blob / portfolio version as reference group revision; snapshot effective date separately | No source available_at/dated group-assignment history carried. Do not infer it from the Git extraction clock | Reference group evidence exists; standard industry **NOT_AVAILABLE** |
| SEC SIC | Official SEC code list + a company's disseminated EDGAR filing header SIC; issuer/CIK level | Code-list captured version/hash separately from filing accession/assignment revision; effective validity must be supported or unknown | SEC says SIC appears in disseminated filings. An accession-linked acceptance/publication fact can evidence that filing's availability; current submissions top-level metadata does not establish past assignment validity. Filing header bytes and exact timestamps still need capture/replay | Best no-account US candidate using existing SEC submissions/raw-store route; no complete assignments activated |
| JPX SICC sector classification | Official SICC guidelines/sector table, issuer/listed issue; reviewed Japan code → listing mapping | Catalog capture/hash; sector-change announcement carries a change/effective event | Regular SICC change announcements are an actual history route; announcement time/date must remain separate from effective date. Current listed-company lookup alone cannot backfill history | Japan candidate confirmed; no Tokyo Electron assignment written |
| KRX KIND 업종 | Official listed-company list exposes industry and company/listing metadata | Captured current extract/hash; exact taxonomy/version/effective history must still be established | Public current table does not evidence the original assignment's available_at or earlier changes. Listing date is not industry assignment date. Existing KRX ingestion can be reused only if its returned fields prove the selected taxonomy | Korean current-source candidate; historical readiness unconfirmed |
| GICS official structure/methodology | MSCI/S&P documentation; single principal-business assignment per hierarchy tier | Official methodology and historical structures; dated assignment/change feed required independently | Public taxonomy/methodology does not supply complete issuer assignments or their release history. No credentials/purchase/feed entitlement was requested or assumed | Taxonomy documentation confirmed; assignment/feed access **NOT_VERIFIED** |
| iShares fund-holdings extract | Existing `ISHARES_FUND_HOLDINGS` raw manifest; security/ticker rows | Fund-as-of date + captured-vintage hash | Existing parser drops sector/classification fields, and historical fund-as-of date is not information available_at. Original raw bytes are not present in inspected checkout. Fund weights are not user's actual weights | Reuse raw acquisition concept; not actual or established classification source |
| Owner/user curated type evidence | Existing Spec names overlapping types (Growth/Value/Dividend/Quality/Cyclical/Defensive/Leader/Theme), not an adopted assignment feed | Proposed versioned catalog + method/evidence ledger + assignment revisions, all explicitly sourced | No source catalog adoption/versioned memberships/effective/available history currently found. Classification based on QGV thresholds must wait for its owner/reconciliation; no thresholds invented | Type memberships **NOT_AVAILABLE**; unknown remains unknown |

Public primary documents inspected on this audit date:

- [SEC SIC code list](https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list): catalog and disseminated-filing use.
- [SEC public API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces): submissions metadata route does not require authentication/API keys; ongoing updates are current metadata, not historical assignment evidence.
- [JPX SICC sector criteria](https://www.jpx.co.jp/english/sicc/sectors/01.html) and [change announcements](https://www.jpx.co.jp/english/sicc/sectors/): official taxonomy and revision-source route.
- [KRX KIND listed companies](https://kind.krx.co.kr/corpgeneral/corpList.do?method=loadInitPage): public current 업종 column; historical provenance not inferred.
- [GICS overview](https://www.msci.com/indexes/index-resources/gics) and [February 2025 methodology](https://www.msci.com/indexes/documents/methodology/1_MSCI_Global_Industry_Classification_Standard_GICS_Methodology_20250220.pdf): documentation inspected, not asserted to be a complete current assignment feed or automatically latest methodology.

No company assignment was authored, no taxonomy/version was made authoritative and no country taxonomy was automatically cross-mapped into a single common industry namespace. For a unified multinational donut, retain one declared namespace per view or obtain a sourced/versioned crosswalk; mixing SIC, JPX and KRX names into one chart without that crosswalk is not justified.

## Type exposure and exact Overlap

v0.1 semantics remain sufficient and are preserved:

- Each type exposure uses the same total portfolio denominator; combined type-member exposure can exceed 100%.
- Overlap groups by the exact, complete, sorted membership set and counts each aggregated holding once.
- Unknown/incomplete membership is not an empty set. A confirmed complete empty set means known no types; null/missing means unavailable classification.
- Type IDs require catalog/namespace/version refs. Equal labels in different versions/taxonomies cannot be treated as one exact set by display string alone.
- Cash is separate from unknown classification. Holdings are aggregated by the existing security domain first, then classification joins at the approved entity level apply; issuer classification expansion across share classes needs the explicit security→issuer map.

A quarterly snapshot needs immutable refs to TARGET or ACTUAL source, received/missing account scope, positions and cash, original valuations/FX, classification catalog and assignments, effective validity, source available_at, snapshot/knowledge cutoff, and projection/numeric context. Later classification revisions append new evidence and do not rewrite older views. Broker transactions are a possible future source only with opening positions, corporate actions, cash flows, valuation and timing completeness; a Protocol method is not history data.

## ChartDocument v0.1 adequacy / v0.2 proposals

v0.1 already covers Decimal preservation, finite values, source origin, target/actual separation, effective+available classification records, unknown/known-empty multitype sets, publication/invalidation and quarterly immutable refs. No correction of those semantics is needed. **It is insufficient as an executable source binding today** because the actual contract has lost or never carried several required facts. The v0.2 proposal should make these concrete source-binding obligations explicit, without rewriting v0.1 or implementing a new runtime schema:

| Proposal | Required explicit content | Reason from actual source |
|---|---|---|
| P-V02-01 Actual input evidence binding | Position/cash source-row ref/hash, snapshot acquisition/availability evidence, valuation methodology/source refs, original+converted amount/currency and FX ref | Position stores converted Money only; cash lacks provenance/account/timing |
| P-V02-02 Account completeness receipt | Expected/received/missing account scope, per-account sync receipt, coherent snapshot-boundary evidence and private scope reference | Domain complete/sync_quality is a coarse supplied claim; weights computes incomplete totals |
| P-V02-03 Numeric result reference | Original domain Decimal output + context/aggregation/version ref; cash amount/denominator trace in one projection | Decimal preservation is necessary but current context is not explicitly pinned; weights has no cash entry |
| P-V02-04 Unavailability capability reasons | ACTUAL_SOURCE_MISSING versus partial account data, missing classification versus known no-types, nonpositive/signed unsupported view, complete verified no-position account | All must avoid fallback/zero conversion; proposed reasons are not adopted enums |
| P-V02-05 Classification candidate/native namespace | Taxonomy catalog vs assignment refs, country/source namespace, issuer/security join authority, sourced crosswalk ref when needed | Existing labels are presentation or user groups; multiple native country taxonomies cannot silently become GICS |
| P-V02-06 Quarterly evidence manifest | Immutable source/value/classification/FX refs + both effective date and knowledge availability + original snapshot cutoff | No actual snapshot history service/source exists; retrospective fetch cannot certify old PIT |

No actual data record is manufactured to make these proposals pass. All absent evidence stays absent; readiness is assessed at the source/capability level, separately from publication state.

## Dependency classification and next feasible work

| Item | Protected edit needed now? | P01 effect if future runtime wired | Track C whole-package code_hash effect | Integration/FPIA |
|---|---|---|---|---|
| This source audit, evidence refs, v0.2 proposal, no-assignment source inventory | No | None | None | Documentation consistency only; not runtime PASS |
| Capture authorized public taxonomy/source documents in scoped evidence with bytes/hash | No | None | None | Verify evidence; historical adequacy independently assessed |
| Recover historical immutable raw inputs; identify captured source/assignment history | No if scoped evidence/retention only | None until registered | None for data/docs only | Data admission later; raw recovery is not automatic publication |
| Obtain actual user/broker holdings | External private input needed; do not probe account/credentials | None merely to receive private source | None merely for evidence | Separate consent/access and source completeness; absent now |
| Add production personal source/evidence adapter, one composition projection, Decimal encoding | **Held** by user package-Python prohibition | May affect P01 if registered serializer/producer paths change | **Yes** for Python under investment_system | **Exact-tree Integration/FPIA required after MAC-X1 resolution** |
| Replace Web fallback and wire actual shape / chart document | **Held**; owner-protected validator/assembler/UI routing | **Yes for protected validator/assembler; inventory owner confirms concrete path** | Python registration changes: yes; JS-only code_hash no | Affected owner regression + exact-tree FPIA |
| Publication/invalidation chart subject registration | No action now; future owner change | **Yes if predicate/facts/subject/digest paths affected** | Package Python yes | Exact-tree FPIA; grants remain unissued |
| Actual quarterly persistence/read service | Held for package runtime; source design/evidence audit feasible | Depends on exact registration/publication paths | Package Python yes | Exact-tree FPIA and immutable replay checks |

Useful non-protected work now: preserve/recover actual public source bytes, evidence/hashes and taxonomy native-version documentation; inspect dated classification change sources; define input evidence examples with explicit missing fields; source-history retention design; owner-routing/path inventory. None needs a speculative company type score or new chart calculation engine.

## Verification statement

Verification here is exact-tree source inspection, absence-search inventory and primary-source documentation retrieval. Existing P0 tests and PR41 demo tests remain their historical evidence; no runtime implementation or new full regression PASS is claimed. No production code was executed to generate real holdings. The audit makes zero requests for broker authentication, source grants, LIVE/Official promotion or canonical merge.
