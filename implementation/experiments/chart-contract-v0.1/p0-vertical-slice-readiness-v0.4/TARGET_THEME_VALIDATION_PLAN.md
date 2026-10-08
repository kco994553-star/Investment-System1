# Target Theme L1→L5 validation plan

Status: PLANNED / PRODUCTION_NOT_RUN. This plan is sufficient to specify deterministic source→domain→contract→API→Web verification once the unresolved owner/source gates close. Offline reference arithmetic and hash replay receipts are separate, and do not certify production.

| Test | Layer/trigger | Deterministic oracle / refusal |
|---|---|---|
| T01 | L1 current root | Only an explicitly admitted current immutable TARGET root is eligible; same weights in a REFERENCE_FIXTURE do not make it current. Check identity/version/applicability/completeness/source/hash |
| T02 | L1 root identity/constituents | Match exact root rows and sourced security namespace/IDs. Unknown share form/ticker collision/missing binding refuses security-scoped projection; no inferred venue |
| T03 | L1 Theme relation | Each root constituent has one source-backed assignment at the root's applicable period and pinned taxonomy/revision. Unknown/partial/conflicting assignments remain diagnostic; no label guessing |
| T04 | L2 exact target arithmetic | Independent authored-source oracle validates 19 reference weights sum exactly 100%, counts 5/5/3/6 in Theme order 반도체 장비/AI·반도체/Big Tech/기타산업 and Themes 30/25/20/25. Production oracle uses admitted root numeric evidence including authored cash; never normalize incomplete/invalid input |
| T05 | L2 numeric losslessness | Preserve original Decimal tokens/context/results and original float representations when applicable. Reject NaN/Infinity/unsupported encoding; roundtrip hashes/values remain identical. No invented quantization/epsilon |
| T06 | L2→L3 shared projection | Each materialized segment's constituent set equals source-backed Theme membership; count and aggregate agree with independent admitted source oracle. One projection only; API/Web never re-aggregate |
| T07 | L3 independence | With GICS/Type/ACTUAL/quarterly history/Market unavailable, admitted TARGET Theme still materializes. ACTUAL request independently returns NOT_AVAILABLE and no target data/denominator fallback |
| T08 | L3 immutable lineage | Tamper root/source/assignment bytes or select incompatible revision: refuse. Same admitted inputs/context produce same payload hash; changed input revision produces a new exact subject; old bytes unchanged |
| T09 | L3 state distinctions | Missing source → NOT_AVAILABLE reason; invalid/partial root → capability diagnostic; verified zero preserved; empty invalid total never promoted as a full 100% chart. Existing Web data-state enums unchanged |
| T10 | L3 API/authority | Same authorized request yields same immutable domain result/hash through read service and API. Absent/revoked/wrong-subject/scope authority refuses display; cached old authority is rechecked; rights evidence cannot issue Product authority |
| T11 | L4 semantics/interaction | Title `Target Strategy Theme Allocation`; explicit user-defined Theme namespace. Select each segment via mouse/keyboard to show domain-supplied constituent list/weights, count, taxonomy/version and effective period; accessible table equivalent |
| T12 | L4 unavailable transition | On authority/root invalidation, stale allocation/selected constituent data clears. No actual_weight ?? target_weight path; no GICS label absent assignment; unsupported input never rendered as normal data |
| T13 | L5 deterministic integration/E2E | Replay one admitted immutable source root plus assignments through actual domain producer, registered shared contract, authority-aware read API and production renderer. API/payload hash and displayed four groups/detail rows match T04/T06 oracle at 360/390/1280px; no errors/overflow |
| T14 | L5 owner/integration | Run changed-owner regression and exact combined Chart result FPIA on approved tool/tree once implementation is available. Separate implementation/CI/review/D3/GIE/Chart result; historical experiment tests are not new production verification |

Evidence gate is not crossed by generating a synthetic root or a reference-fixture screenshot. No broker connection, new GICS membership, PIT relaxation, numeric policy, grant, schema Freeze or canonical merge is authorized by this plan.
