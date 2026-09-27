# Investment-System1 · RIG / News Architecture v0.1

Contract ID: `RIG_NEWS_ARCH_v0.1`

Status: **DESIGN FROZEN / P0–P1 IMPLEMENTED + FROZEN; P2–P5 NOT_STARTED**

Registered: 2026-09-27 11:07 KST

Authority: additive to the existing Investment-System1 SSoT. It does not replace or redesign Track A, Track B,
Track C / EVL, QGV, Technical, Macro, Portfolio, Universe, provenance, or identity contracts.

## Repository consistency lock

The attached v0.1 candidate was compared with the current repository tree before registration. This freeze has the
following binding interpretation:

- Track A continues to own REAL-DATA, PIT Universe, source provenance/vintage, and Official snapshots. RIG does not
  alter its gates, scores, membership, or current work order.
- Track B remains P0 IMPLEMENTED+FROZEN and P1+ NOT STARTED. RIG does not import, modify, or extend the frozen
  `investment_system.personal` package. Portfolio data may only be consumed through a future read-only boundary.
- Track C remains `EVL_SPEC_v0.1`, DESIGN FROZEN / IMPLEMENTATION NOT STARTED. The RIG Feature lifecycle below is a RIG
  feature-maturity label, not a replacement Track C state machine or an authorization to start EVL implementation.
- Existing `DataEvent` remains the incremental pipeline event. `NewsEvent` / `EconomicEvent` are separate future RIG
  domain objects and may connect only through an adapter to `DataEvent(kind=NEWS)`.
- The existing Global/Korea contract's `NewsItem -> Claim -> Event` normalization and shared Feed/Network IDs are
  upstream contracts. RIG refines their product/domain use; it must not create a second Event, Evidence, Relationship,
  or view-state source of truth.
- Company/security/listing identity and PIT provenance remain upstream. The Global/Korea contract says the related
  runtime types are implemented, but they are not present in the current public source tree; C-39 records this evidence
  mismatch. RIG P0 must fail closed until the canonical shared identity implementation is confirmed or supplied, and
  it must not import Track B's frozen security contract as a shortcut.
- Tracking-stock/share-class economic rights remain an upstream identity/Universe matter. RIG does not infer or merge
  them; unresolved identities/rights remain Pending/Unresolved.
- `yahoo_events__*` artifacts are Yahoo split-event payloads (`source_kind=YAHOO_SPLIT_EVENTS`, `events=split`) used by
  market-cap adjustment. They are not NewsEvent, EconomicEvent, Claim, or RIG Evidence.
- Attention/Notification runtime remains outside this contract and is not implemented. RIG owns only the News/Network
  domain and presentation behavior specified here; it does not silently create a notification service.

No RIG runtime package, database/store, UI route, alert/notification runtime, score, test result, or implementation
progress is claimed by this registration.

## Registration audit result

| Category | Repository-grounded result |
|---|---|
| (1) Reuse | `DataEvent` / `EventKind.NEWS`, `available_at` PIT gate, raw provenance/vintage, upstream identity contract, Global/Korea `NewsItem -> Claim -> Event` normalization, shared Feed/Network IDs, and Frontend Summary→Evidence→Detail. |
| (2) Conflict | No architecture-level conflict. C-39 is an existing SSoT-versus-code implementation-evidence mismatch and blocks RIG P0, not design freeze. `DataEvent` and real-world domain events remain separate. |
| (3) New | News↔Network two-view UX; RIG NewsEvent/EconomicEvent, Claim/Evidence trace, Relationship/Deal state, Fact/Impact graph separation, graph interactions, and phased P0–P5 scope. None is implemented. |
| (4) Policy needed | No new policy is required to freeze v0.1. A future Attention runtime owner/contract and any Track C execution path for RIG feature validation must be explicitly opened at their phases; this registration does not decide them. Tracking-stock/share-class economics remains upstream and unresolved where applicable. |
| (5) Ownership | Track A: data/Universe/identity/provenance; RIG: News/Relationship domain plus News/Network presentation; Track B: unchanged personal investment contracts; Track C: unchanged EVL validation authority; Attention runtime: separate future layer. |

Cross-architecture audit: no RIG store or runtime dependency exists, so no data double ownership or dependency cycle is
introduced. News View and Network View are projections over the same Event/Relationship/Evidence IDs; only transient
viewport state may differ. PIT uses `available_at`, and no Track B/C ownership is imported into RIG.

## Purpose

기존 News를 유지하면서 동일한 Event/Relationship 정보를
`News(뉴스) | Network(관계망)` 두 방식으로 탐색한다. 핵심 원칙은 **Same
Information, Two Views(같은 정보, 두 가지 보기)**다.

## Core rules

- News View와 Network View는 동일 Event/Relationship/Evidence를 참조한다.
- 기존 `NEWS is evidence only — does not dirty QGV scores`를 보존한다.
- Fact, Expected/Inference, Impact Path를 분리한다.
- Historical Graph는 `available_at <= graph_as_of` PIT 규칙을 따른다.
- Portfolio와 관심기업을 우선 표시하되 전체 시장 탐색을 제한하지 않는다.
- RIG는 BUY/SELL/HOLD나 새 종합 투자점수를 소유하지 않는다.

## UX

```text
뉴스
        [ 뉴스 | 관계망 ]
[ 내 기업 | 전체 ]
◎ 보유   ★ 관심   그룹   연관   필터+
─────────────────────────────
              CONTENT
```

뉴스 클릭 시 기존 News Feed + 관계정보, 관계망 클릭 시 같은 Content 영역
전체가 Graph로 전환된다. 좌우 동시 분할은 기본 구조가 아니다. View 전환
시 Scope/Filter/Group과 Graph의 Zoom/Pan/Focus를 유지한다.

### News card

기업, 제목, NEW/UPDATE/FOLLOW-UP, 계약 확정/예상, 관계 강화/약화,
중요도, 2~3줄 요약, 시간, 출처 수만 우선 표시한다.
QGV/Technical/Macro/Consensus/Scenario/Signal/Evidence/PIT/Track C 상세는 `더보기`
아래로 이동한다.

동일 사건 기사는 Event 하나로 묶는다. `NEW`=새 Event, `UPDATE`=중요한 새 사실,
`FOLLOW-UP`=후속 진행, `DUPLICATE`=새 정보 없음이며 기본 Feed에서 반복 카드로
만들지 않는다.

## Network visual contract

Node: `◎` Portfolio, `★` 관심기업, `●` 일반기업, `◆` Technology/Product,
`▣` Value Chain Stage, `⬡` Macro/Common Driver.

Edge: 실선=Confirmed Fact, 점선=Expected/Unconfirmed, 점-화살표=Potential Impact Path,
화살표=제품·서비스/가치 흐름, 굵기=Materiality. 기본 Badge는 최대 2개로
NEW/DISCOVERED/↑강화/↓약화/✓확정/예상 등을 사용한다.

Investment Overlay는 기본 OFF다.

## Graph interaction

- Pinch/Wheel = Zoom
- 빈 공간 Drag = Pan
- Node Drag = 위치 조정
- Node Tap/Click = Quick View
- Edge Tap/Click = Relationship Quick View
- Double Tap/Click = Focus
- `+N개 관계` = Graph Expansion
- `⌂` = Fit Current Graph
- Search = 기업·기술·Driver 검색 및 Focus

Visual Zoom과 Graph Expansion은 별개다. 기본은 선택 Node 주변 5~8개 핵심
관계만 표시하고 나머지는 `+N개 관계`로 접는다. 우선순위는 Critical Event →
Portfolio/관심 → High Materiality → Recent Change → Common Connection → 기타다.

## Relationship types

P1 핵심은 Supply Chain(공급망), Customer(고객), Competitor(경쟁사),
Value Chain(밸류체인)이다. `Industry Chain`은 별도 용어로 두지 않고
Value Chain으로 통일한다. 가능하면 Upstream → Downstream 방향을 유지한다.

## Relationship / Deal state

`NEW`는 실제 신규 관계 근거가 있을 때만, `DISCOVERED`는 최근 발견했지만
시작일이 과거/불명일 때 사용한다. 추가 상태는
STRENGTHENED/STABLE/WEAKENED/ENDED다.

Deal은 RUMORED → EXPECTED → NEGOTIATING → ANNOUNCED → CONFIRMED → ACTIVE 이후
EXPANDED/RENEWED/REDUCED/CANCELLED/EXPIRED를 가질 수 있다.
Relationship State와 Deal State는 별도다.

## DataEvent vs NewsEvent/EconomicEvent

기존 `DataEvent`는 FUNDAMENTAL/PRICE/MACRO/NEWS/MEMBERSHIP 등
Incremental/PIT pipeline용 시스템 이벤트다. 새 `NewsEvent/EconomicEvent`는 Contract,
Customer Win/Loss, Supplier Change, Partnership, Investment, Capacity Expansion, Regulatory Action
등 현실세계 사건을 표현한다. 둘을 동일 객체로 합치지 않는다.

필요 시
`NewsEvent/EconomicEvent → DataEvent(kind=NEWS) → Existing Incremental Engine → Evidence-only`
경계를 사용한다.

## Evidence / PIT

Official Relationship은
`Source → Evidence → Claim → NewsEvent/EconomicEvent → Relationship Candidate → Update Gate → RIG Edge`로
역추적 가능해야 한다. Update Gate는
Identity/Evidence/Temporal/Direction/Duplicate/Contradiction을 포함한다.
실패 후보는 Pending/Unresolved로 보존한다.

Historical Graph는 `available_at <= graph_as_of`만 사용한다. 주요 시간
필드는 valid_from, valid_to, first_detected_at, last_confirmed_at, available_at이다.

## Fact Graph vs Impact Graph

Fact Graph는 확인된 고객/공급/경쟁/계약/Value Chain 관계다. Impact Graph는
Event/Macro Driver에서 파생되는 잠재 영향경로다. Impact Path를 Fact Relationship으로
저장하지 않는다.

## Personal UX

**내 기업 = Portfolio + 관심기업.** Favorite/Watchlist를 나누지 않고
`★ 관심기업` 하나로 통합한다. 사용자 명시적 Action으로만 추가/제거한다.

`My Groups(내 그룹)`은 선택적 Organization Layer다. 한 기업이 여러 그룹에
들어갈 수 있고 Portfolio와 관심기업을 함께 묶을 수 있다. 그룹은
Filter/Organization/Graph Focus 전용이며 투자점수에 영향이 없다. User Group과
System Industry/Value Chain Classification은 분리한다.

## Priority / Overlay

News 우선순위는 보유 중요 Event → 관심 중요 Event → 내 기업의
High-Materiality 1-Hop Event → Research Priority 신규기업 → 전체 시장이다.
**Feed Priority ≠ Investment Attractiveness**다.

Investment Overlay ON 시 기존 QGV/Technical/Macro/Portfolio/Profile을 read-only로 표시한다.
새 RIG 종합점수를 만들지 않는다. Research Priority는 High/Medium/Low의
조사 우선순위이며 BUY/SELL/HOLD가 아니다.

## Boundaries

- QGV: RIG가 score를 직접 변경하지 않는다.
- Technical: 관계 Event로 Technical score를 직접 변경하지 않는다.
- Macro: Macro Driver definition은 Macro가 소유하고 RIG는 참조한다.
- Track B: 현재 P0 IMPLEMENTED + FROZEN 유지. RIG 때문에 수정하지 않는다.
- Track C: 관계 사실을 결정하지 않고 RIG Feature의 투자 유효성만 검증한다.

RIG Feature lifecycle:
`INFORMATION_ONLY → GRAPH_RESEARCH_FEATURE → Track C → GRAPH_VALIDATED_FEATURE`,
실패 시 `REJECTED_AS_SIGNAL`. 정보 자체는 삭제하지 않는다.

## Attention / Notification

Notification은 RIG 소유가 아니다. 별도 Attention Layer가 Event Importance/User
Relevance/Materiality/Recency/Confidence를 이용해 Immediate/Digest/Feed Only 등을 결정한다.

## Language

공식 표시 모드는 English / English (한국어) / 한국어다. 원칙은
**One Data / One Terminology / Three Presentations**. 언어 변경으로 점수나
Event/Relationship State가 바뀌지 않는다.

## Progressive Disclosure

1. Glance(한눈에)
2. Explain(설명)
3. Analyze(분석)
4. Evidence & Validation(근거·검증)

## Implementation phases

- P0 Foundation: Identity/PIT/Evidence/Node/Edge/Temporal/Fact-Inference separation
- P1 Basic Network: News↔Network, Supply/Customer/Competitor/Value Chain, Zoom/Pan/Drag
- P2 Relationship Intelligence: NEW/DISCOVERED, 강화/약화, Deal State, Timeline
- P3 Personal UX: Portfolio/관심/My Groups/Related News/Attention integration
- P4 Discovery: Graph Position/Emerging/Common Connections/Impact Graph/Research Priority
- P5 Validation: Track C integration

각 Phase는 `NOT_STARTED → IMPLEMENTING → TESTING → FROZEN`. 현재 Phase
Acceptance에 필요 없는 다음 Phase 기능을 선행 구현하지 않는다.

## OUT OF SCOPE v0.1

자동매매, RIG 자체 BUY/SELL 점수, 자동 관심기업 추가, AI 자동 그룹 생성,
그룹 투자점수, Track B P0 수정, Track C 재설계, 기존 QGV 점수 자동변경,
3D Graph, Social/Public Groups, 무제한 Graph Expansion, News와 Network의 별도 상태 저장.

## Repository integration

기존 Company/Identity Contract, `DataEvent`, `available_at` PIT Gate,
`NEWS is evidence only — does not dirty QGV scores`, Frontend의
Summary→Evidence→Detail 패턴, QGV/Technical/Macro snapshots을 우선 재사용한다.

`yahoo_events__*`는 이름만 보고 NewsEvent/RIG Evidence로 간주하지 말고
실제 schema와 semantics를 확인한다.

## Current state

- Architecture Design: 100% (unchanged; phases add implementation only)
- Repository consistency audit: completed against local/remote-identical tree at registration
- C-39: RESOLVED and re-verified 2026-09-27 17:13 KST (`contracts/global_universe.py`, 6/6 focused regressions)
- P0 Foundation: **FROZEN** (2026-09-27 17:44 KST; code baseline `e3b1b62`)
- P1 Basic Network: **FROZEN** (2026-09-27 17:55 KST; baseline = the commit adding the P1 record)
- P2–P5: NOT_STARTED

## P0 Foundation implementation record (2026-09-27 17:13 KST, Track D)

Branch: `feature/track-d-rig-news`, based on canonical `5acb047` (C-39 resolution). Package
`implementation/src/investment_system/rig/` (5 files); tests `implementation/tests/test_rig_p0_foundation.py` (15).

- Identity: RIG is a consumer of the common C-39 hierarchy only. `IdentityRef(issuer_id, security_id?, listing_id?)`
  enforces Issuer → Security → Listing; graph `Node` id is `issuer:<issuer_id>`; no ticker/CIK field exists. Identity
  records are read through an `IdentityLookup` protocol supplied by the upstream owner; RIG holds no identity universe.
- Lineage: `SourceRef → Evidence → Claim → NewsEvent/EconomicEvent → RelationshipCandidate → GateDecision →
  RelationshipState → Edge`, append-only `LineageIndex`, and `RelationshipLedger.trace(edge)`.
- Update Gate: IDENTITY / EVIDENCE / TEMPORAL / DIRECTION / DUPLICATE / CONTRADICTION. Identity failure → UNRESOLVED;
  any other failure → PENDING. Candidates and decisions are never deleted.
- Time: `valid_from`/`valid_to` = real-world validity (date, `valid_to` exclusive); `available_at` = public knowledge
  time; `first_detected_at` / `last_confirmed_at` = knowledge time of first/latest accepted assertion; `decided_at` =
  system time, never used for PIT. Historical graph uses `available_at <= graph_as_of`; lineage look-ahead,
  candidate-before-lineage, evidence-before-source, out-of-order backfill, naive datetimes and future `valid_on` fail
  closed. Unknown `valid_from` is treated as valid only from the `available_at` date.
- Fact/Inference: `FACT`, `SUPPORTED_INFERENCE`, `UNVERIFIED_SIGNAL`. The gate never changes a candidate's status;
  `UNVERIFIED_SIGNAL` is never an edge; FACT requires at least one PRIMARY_DISCLOSURE or NEWS source; a later
  inference cannot downgrade a FACT with the same interval.
- DataEvent separation: `NewsEvent`/`EconomicEvent` are independent classes; `rig.adapter.to_data_event` builds
  `DataEvent(kind=NEWS)` only with an explicitly supplied pipeline `company_id`. `DataEvent` and the incremental engine
  are unchanged; NEWS remains evidence-only.
- Not implemented (P1+): UI, Zoom/Pan/Drag, clustering, Relationship/Deal state UX, Personal overlay, My Groups,
  Research Priority, Hub/Bridge/Bottleneck, Impact Graph, notification, Track C/E integration, any score, persistence.

## P0 Freeze record (2026-09-27 17:44 KST, Track D)

- Frozen code baseline: `e3b1b62` on `feature/track-d-rig-news` (`rig/` 5 files, 15 tests). Any later change to
  `investment_system.rig` P0 semantics (identity use, time fields, gate categories/outcomes, Fact/Inference rules,
  DataEvent adapter) requires a new decision record; P1 may only add on top of it.
- Evidence: RIG targeted 15/15 and full 323/323 (mini_pytest shim) on the Track D branch; the same 323/323 also passed
  on a throwaway merge with the latest canonical `ed343ba` (no conflicts, not committed). Canonical changes since the
  Track D base are Track A only (C-21 run evidence, GRAL/CA share reconstruction) and do not touch RIG, contracts or
  `DataEvent`.
- Open integration items (not blockers for P0): issuer_id → pipeline `company_id` mapping, a production
  `IdentityLookup` supplied by the identity owner, and shared status documents (Handoff / Master Status / Project
  Index) at canonical merge time.

## P1 Basic Network record (2026-09-27 17:55 KST, Track D) — FROZEN

Package `implementation/src/investment_system/rig/network/` (`views.py`, `labels.py`, `render.py`), tests
`test_rig_p1_network.py` (11), shared fixture `tests/rig_fixtures.py`, optional browser smoke
`tools/rig_browser_smoke.js`. P0 files are unchanged.

- Same Information, Two Views: `build_view_model` projects one P0 `RIGGraph` into News cards and Network
  nodes/edges with identical event / relationship / node ids. `NewsIndex` holds only news-view metadata keyed by P0
  event ids (no second Event store).
- News cards: NEW (no link) / UPDATE / FOLLOW_UP / DUPLICATE via append-only, PIT-checked `EventLink`; DUPLICATE is
  hidden from the default feed; source count = distinct lineage sources; untraceable events are not shown.
- Network: relationship types Supply Chain / Customer / Competitor / Value Chain; solid = FACT, dashed =
  SUPPORTED_INFERENCE, arrow = directed upstream→downstream (Competitor undirected); at most 2 edge badges.
- `ViewState` (view, filters, focus, expansion steps, viewport); `switch_view` changes only the view. Filters apply
  to both views. Focus shows 5–8 core relationships (default 8) with `+N` expansion by steps; overview capped at 60
  edges per step (no unlimited expansion). P1 edge priority: FACT, most recently confirmed, id.
- Page: whole content area swaps between News and Network; wheel/pinch zoom, empty-space pan, node drag, node/edge
  quick view, double-click focus, `+N`, `⌂` fit, search; EN / English (한국어) / 한국어 change labels only.
- Evidence: targeted P1 11/11, P0 15/15, full 334/334 (mini_pytest shim); browser smoke 18/18 checks in Chromium
  (found and fixed a pointer-capture bug that suppressed node click/double-click).
- D2 decisions: NEW/UPDATE/FOLLOW-UP news status is P1 (News View core), relationship NEW/DISCOVERED stays P2;
  non-company nodes (◆ ▣ ⬡) are deferred to P4 with the Impact Graph; the page is a standalone RIG render, not yet
  registered in the shared App Shell `NAV_PAGES` (INTEGRATION_REQUIRED at canonical merge); later phases extend the
  page only through `PageExtras`.
