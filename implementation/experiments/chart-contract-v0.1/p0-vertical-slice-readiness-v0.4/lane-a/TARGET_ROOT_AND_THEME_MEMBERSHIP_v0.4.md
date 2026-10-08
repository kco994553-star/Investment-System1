# Lane A — Target root and Strategy Theme source readiness v0.4

Status: **AUTHORED_REFERENCE_VERIFIED / PRODUCTION_CURRENT_TARGET_ROOT_NOT_ADMITTED**.
This additive review narrows the first Target Strategy Theme slice. It changes no existing source, reference, production code, scope inventory, or Frozen record. It does not register a producer or adopt a production schema. Contract, Web/API, publication authority and FPIA are assessed separately by the parent readiness review.

## Source verdict

`QGV Portfolio · Specification v1.1.md` §2 is the authoritative **authored baseline values and bucket membership** within the inspected repository. The Project Index and Master Status Index both name the same Official Portfolio v1.1 · 2026-09-14. `OFFICIAL_V11_TARGETS` reproduces its 19 target weights; the preserved chart `portfolio_reference.json` reproduces the weights and four bucket memberships. No same-version weight or grouping discrepancy was found. The user has reiterated the four bucket totals as current strategy intent; this supports their names/meaning and does not automatically adopt every reference row as a current production holding.

**No admitted, globally named current production Target root was found.** The authored baseline, runtime reference fixture and diagnostic chart reference are distinguishable artifacts. Choosing the fixture as the current production root would be an unsupported promotion. The root identity, current revision/applicability, security bindings, adopted Theme revision and completeness admission still need owner evidence.

The document's date label `2026-09-14` is known. Its exact `effective_at`, effective end, current applicable period and source `available_at` are not established. The preserved reference's `as_of=2026-10-04T10:49:27.857Z` is an extraction timestamp according to its source evidence; it is neither the baseline publication time nor a current portfolio valuation/effective time. Git commit timestamps preserve repository history and do not supply an unproven historical availability date.

## Fresh pinned repository evidence

| Inspected tree | Exact SHA | Role in this source check |
|---|---|---|
| PR #41 baseline | `581c61c4af859f6cbdc3418209bba9be7bbc76a3` | Local immutable authored/reference source and previous evidence |
| Canonical | `b8e39a2196a6d7794a04a0cd5393c68329e126ca` | Current canonical reference sources |
| CDR-012 trial | `acaf1b5a82859ac2750a130ebe88f8b4d272ac66` | Noncanonical integrated source inspection |
| PR #42 FPIA head | `523e702a806a718d163cfbf62aa3fc29d8c3ef3c` | Latest FPIA branch source inspection; no governance closure claim |
| Global handoff | `9d9b2b2b942cfa6d1f7b296ad81d380ec6a70b3e` | Owner routing/source status only |

The primary authored specification, target literal dictionary and identifier registry have identical bytes in these pinned trees. The chart reference exists on PR #41; its absence from other trees is explicit in `SOURCE_PINS.json`, not treated as a conflict. The current handoff describes Portfolio actual operation as P1+ not started. This is absence evidence within the named inspected trees, not a claim about unseen private accounts or unpublished owner work.

| Source | SHA256 |
|---|---|
| `QGV Portfolio · Specification v1.1.md` | `d24eda232102bbb8163fe06d5cdb0d70611f5dc8abd5048941a00f6c11b0fa3e` |
| `implementation/src/investment_system/qgv/portfolio.py` | `ecb44165cb163d2e975e94c39c343a18ed3e2d43538431394065b4523246da49` |
| `implementation/src/investment_system/qgv/identifiers.py` | `38c68c1dc35546f6a7a9800340999f6ad7780aab0c09fa8f2dd51ffc7a04c917` |
| `implementation/experiments/chart-contract-v0.1/portfolio_reference.json` | `05f38b9e3266eac7271a10a1c080367c4c73176bf6469b52850733f84a5d2a96` |

All 16 selected local file pins, baseline Git blobs, and presence/bytes of the selected files in the four other pinned trees are replayed by `validate_target_sources.py`. Full hashes, sizes, baseline blobs and absence searches are retained in `SOURCE_PINS.json`.

## Target root fields

| Required fact | Observed evidence | Production source verdict |
|---|---|---|
| Portfolio identity | Authored name Portfolio v1.1; diagnostic `reference:portfolio-v1.1:2026-09-14`; fixture generates random `pf_*` IDs | **NOT_AVAILABLE** for a globally adopted current production `portfolio_id`/root |
| Portfolio version | §2 v1.1; `versions.py` v1.1-2026-09-14; diagnostic display version agrees | **PARTIAL**: authored version known, current producer/root admission absent |
| Effective/applicable period | Baseline date label 2026-09-14 | **UNKNOWN** for exact validity interval and current-use admission |
| Constituent identity | 19 `company_id` keys; source reference row IDs; all reference `security_id=null` | **PARTIAL** at company level, **NOT_AVAILABLE** for Target→19 production security bindings |
| Target weight | §2 numeric tokens agree 19/19 with code literal tokens and chart reference units | **READY** as source values; production calculation/encoding contract still separate |
| Strategy Theme membership | §2 explicitly partitions 19 constituents into four groups | **PARTIAL**: authored membership proven, adopted security assignment records absent |
| Theme taxonomy/version | Four source labels; diagnostic `USER_ALLOCATION_GROUPS_V1.1; TYPES_UNRESOLVED` | **PARTIAL**: diagnostic description exists, adopted Theme catalog/revision absent |
| Source/provenance | Named specification, exact line/blob/hash references, D-28/D-29 identity decisions | **READY** for inspected reference provenance; current adoption authority absent |
| Completeness | §2 declares 100%, explicit cash 0%, 19 unique source rows form one partition | **PARTIAL**: reference complete; current Target revision/source receipt not admitted |
| Total validation | Exact Decimal/rational replay below | **READY** for source arithmetic; production L5 remains NOT_RUN |

`ModelPortfolioSnapshot` is a reusable immutable contract with strategy/universe/policy/calculation fields and a float sum check. It does not supply an actual 19-row source. Searches found its construction in tests, not in the inspected production package sources. `PortfolioEngine.official_v11()` and `us_working()` deliberately emit `REFERENCE_FIXTURE`; the Official book runner is synthetic. The separate 17-row US working book excludes Tokyo Electron and Hanmi and normalizes its own working mass: its unnormalized original weight mass is exactly 0.905. It is a different provisional book and cannot substitute for the complete 19-row target.

## Nineteen constituent membership evidence

Every row below has **READY authored membership evidence**, **PARTIAL_NOT_ADOPTED production Theme assignment**, **NOT_AVAILABLE Target production security binding**, and **UNKNOWN current effective period**. Every row's exact source lines and JSON pointer are available in `TARGET_ROOT_AND_MEMBERSHIP_EVIDENCE.json`. Membership is user/system-defined **Strategy Theme / Portfolio Bucket** and never GICS or an objective industry assertion.

| Source constituent / company_id | Target % | User Strategy Theme | Authoritative authored source |
|---|---:|---|---|
| ASML / `asml` | 9 | 반도체 장비 | Spec §2 line 15 |
| LRCX / `lrcx` | 6 | 반도체 장비 | Spec §2 line 15 |
| KLAC / `klac` | 5.5 | 반도체 장비 | Spec §2 line 15 |
| TEL / `tokyo_electron` | 5 | 반도체 장비 | Spec §2 line 15 + D-29 |
| 한미반도체 / `hanmi` | 4.5 | 반도체 장비 | Spec §2 line 15 |
| NVDA / `nvda` | 8 | AI·반도체 | Spec §2 line 16 |
| AMD / `amd` | 5 | AI·반도체 | Spec §2 line 16 |
| AVGO / `avgo` | 5 | AI·반도체 | Spec §2 line 16 |
| QCOM / `qcom` | 4 | AI·반도체 | Spec §2 line 16 |
| INTC / `intc` | 3 | AI·반도체 | Spec §2 line 16 |
| MSFT / `msft` | 7 | Big Tech | Spec §2 line 17 |
| GOOGL / `googl` | 7 | Big Tech | Spec §2 line 17 |
| AMZN / `amzn` | 6 | Big Tech | Spec §2 line 17 |
| RTX / `rtx` | 6 | 기타산업 | Spec §2 line 18 |
| Stryker / `stry` | 5.5 | 기타산업 | Spec §2 line 18 |
| Eaton / `etn` | 5 | 기타산업 | Spec §2 line 18 |
| Hubbell / `hubb` | 3.5 | 기타산업 | Spec §2 line 18 |
| GE Vernova / `gev` | 3 | 기타산업 | Spec §2 line 18 |
| Rockwell / `rok` | 2 | 기타산업 | Spec §2 line 18 |

D-28 makes `company_id` the key and ticker a display field. D-29 resolves the source's TEL company to Tokyo Electron while retaining ambiguous bare ticker and unresolved listing venue. This confirms the company-level authored membership; it does not permit assigning TE Connectivity, a TSE/ADR venue or a production security identifier. No reference `industry` field is rewritten. The successor evidence interprets that old field as the authored Strategy Theme grouping.

The proposed P0 scope is **SECURITY**, as requested by the security→Theme relation. Therefore the 19 explicit Target security bindings remain necessary. A company-only chart is a possible narrower owner proposal, not an adopted workaround or a closure of this security-scope gap. Market listing/session/price admission is independent: a current Target security→Theme binding does not require OHLCV prices, exchange calendars or historic Market availability.

## Deterministic validation

`python implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/lane-a/validate_target_sources.py` passes against the saved additive diagnostic output. The script imports no production modules. It parses source AST literal text using Decimal, reads specification numeric tokens independently, checks each of the 19 weights and Theme memberships against the preserved reference, and verifies the exact rational sum.

| Group | Constituents | Exact sum of constituent target percentages |
|---|---:|---:|
| 반도체 장비 | 5 | 30.0 |
| AI·반도체 | 5 | 25 |
| Big Tech | 3 | 20 |
| 기타산업 | 6 | 25.0 |
| Holdings | 19 | 100.0 |
| Cash | Explicit baseline cash | 0 |
| Holdings + cash | One complete reference partition | 100.0 |

All three source representations agree 19/19. Source reference units sum to 10,000. The exact rational sum of source weight ratios is `1`, with no rounding, reweighting or optimization. The diagnostic Decimal context uses precision 50 only to replay the finite source tokens; it is not an adopted production numeric policy and does not change owner float contracts.

Six negative evidence cases are rejected: duplicate constituent, missing constituent, one-source weight drift, nonfinite weight, unknown membership, and an incorrect group reassignment preserving the 100% total. The last case shows that a correct overall total does not prove correct group membership. These checks are offline source diagnostics, not production unit/E2E coverage. **Production L5=NOT_RUN.**

## Three atomic Lane A source closure actions

These three actions are the source-owned portion of the parent's complete blocker registry. They do not count GICS, Actual holdings, Investment Type, Type Overlap, quarterly Actual history or Market admission as Lane A dependencies.

| ID | Owner action | Exact closure evidence | Current status |
|---|---|---|---|
| A-S1 | Target/Portfolio owner admits one immutable current Target root | Named `portfolio_id`, root/snapshot/revision identity, source refs/hash, current applicable period with documented semantics, full 19-row target/cash source and completeness receipt; explicit routing resolves authored spec vs reference fixture vs production current root | **BLOCKED**: reference complete, production root not admitted |
| A-S2 | Target identity owner binds the admitted root's 19 constituents to the requested SECURITY scope | Source-backed immutable `target_row -> company_id -> security_id` bindings, identity authority/revision and completeness. Preserve D-29 Tokyo company evidence; no ticker/venue invention and no Market-price dependency | **BLOCKED**: all reference security IDs null and no Target security-binding adoption |
| A-S3 | Strategy Theme owner admits a versioned catalog and the root's complete assignment revision | Declare `USER_DEFINED_STRATEGY_THEME_PORTFOLIO_BUCKET`; four named concepts, adopted taxonomy/version, exact 19 security→Theme assignments, root/revision binding, current effective period, source provenance and completeness. Carry 30/25/20/25 unchanged; no external industry conversion | **BLOCKED**: authored memberships complete, catalog/assignment production admission absent |

Closing A-S1 does not itself resolve A-S2 or A-S3: a root can have complete weights with unresolved security identity or unadopted classifications. Closing these three source actions does not certify contract/API/Web/publication/governance readiness; those closures remain distinct in the full parent report. No new source arithmetic decision or repeat user confirmation of the known four totals is required by this review. Exact owner integration routing remains a separate dependency.

## Preserve future Theme history

The existing specification requires Portfolio patches with before/after values, reason and applicable date, and prohibits overwriting official snapshots. Git and preserved audit reference bytes provide source history but are not a production dated Theme assignment ledger. A minimal proposed source ledger should retain immutable Target root revisions, immutable Theme catalog revisions and immutable assignment revisions bound to a particular Target root and security binding. Each revision records explicit effective validity, source/provenance/hash, completeness and its evidenced observation/availability roles, with a superseded revision reference where applicable.

Future changes append a new root/assignment revision; older source weights/memberships and their unknown fields remain unchanged. Historical `available_at` must remain UNKNOWN until source evidence exists. A new current source receipt can evidence new current knowledge without claiming the baseline was knowable at a previous historical cutoff. Current Theme readiness does not require quarterly Actual history or backfilled historical classifications. This is a source-history proposal, not a schema freeze, producer implementation or fabricated timestamp.

## Next source step

Deliver the pinned baseline rows and this exact three-action receipt to the Target/identity/Theme owners. The existing immutable reference is enough to review the proposed target values and assignments; it is not enough to activate them as the current production root. Once owners return A-S1/A-S2/A-S3 source admissions, replay the admitted root and assignment hashes through the same source disagreement/completeness/numeric diagnostics, then run the parent's distinct contract, publication and exact merge-result dependency gates. No protected production code or canonical merge is performed here.
