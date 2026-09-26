# PERSONAL_INVESTMENT_LAYER_V1_HANDOFF

> Imported 2026-09-26 verbatim (text only) from the user-supplied relay package
> `PERSONAL_INVESTMENT_LAYER_V1_RELAY_PACKAGE.docx`. Additive frozen architecture: it does NOT replace the
> Investment-System1 SSoT (CURRENT_HANDOFF > Master Status > Conflict Register > Evidence Register > Specs/Contracts >
> code > tests/reports > HANDOFF_HISTORY). Code/document conflicts found at intake: Contract Conflict Register C-24..C-31.

Investment-System1Personal Investment Layer v1 Relay Package
Additive Handoff · Architecture FROZEN · Implementation NOT STARTED
Document role: Additive Handoff / Relay Package  
Architecture status: FROZEN  
Architecture progress: 100%  
Implementation status: NOT STARTED  
Implementation priority: BELOW CURRENT REAL-DATA MAIN TRACK  
SSoT rule: This document does not replace the existing Investment-System1 SSoT.


## 0. Relay Prompt

Investment-System1의 기존 최신 SSoT와 CURRENT_HANDOFF를 기준으로 작업을 이어서 진행해.이번 릴레이에는 기존 시스템에 추가로 설계 완료된 "Personal Investment Layer v1 Architecture"가 포함된다.중요:- 이 Personal Investment Layer는 기존 QGV / Technical / Macro / Portfolio / Simulation / Leaderboard / Track Record를 재설계하거나 대체하지 않는다.- 기존 Investment System 위에 추가되는 개인화 계층이다.- 기존 CURRENT_HANDOFF → Project/Master Status → Conflict Register → Evidence Register → 최신 Specification/Contract → 실제 코드 → tests/reports → HANDOFF_HISTORY 순서와 기존 프로젝트의 권위 체계를 우선한다.- 기존 구현을 재작성하지 말고 최소 변경한다.- 기존 REAL-DATA Main Track의 우선순위를 변경하지 않는다.- Personal Investment Layer v1 Architecture는 DESIGN FREEZE 상태다. 새 기능을 임의로 추가하거나 버전을 올리지 않는다.먼저 기존 최신 SSoT를 복원하고 baseline을 실제로 확인한 뒤, 이 문서의 Personal Investment Layer를 additive frozen architecture로 인수해. 문서와 실제 코드/테스트가 충돌하면 추측하지 말고 Conflict/Evidence 방식으로 기록한다.현재 Main Track 우선순위:REAL-DATA → complete PIT candidate pool → official_mcap500_snapshot_from_store → real single_as_of → ≥3-date walk-forward → actual 500-company network benchmark → Promotion/validation 완료Personal Investment Layer 핵심 구조:Investment System├─ QGV├─ Technical├─ Macro├─ Portfolio / Simulation / Leaderboard / Track Record└─ Personal Investment Layer   ├─ Strategy Profile   │  └─ Hierarchical Strategy Weight Tree   ├─ Model Portfolio   ├─ Broker Hub   ├─ Security Resolver   ├─ Actual Portfolio   ├─ Portfolio Gap   ├─ Personal Fit   └─ Personal Dashboard핵심 원칙:1. Official과 Custom Strategy를 완전히 분리한다.2. 사용자 Custom Weight가 Official QGV/Technical/Macro 결과, Official Leaderboard, Official Track Record를 변경하면 안 된다.3. Model Portfolio와 Actual Portfolio를 별도 객체로 유지한다.4. Portfolio Gap은 Model과 Actual의 차이이며 자동 매수/매도/주문량이 아니다.5. Personal Fit v1은 단일 점수가 아니라 다축 Decision Context다.6. Personal Fit 때문에 QGV/Technical/Macro 원점수를 변경하지 않는다.7. Broker integration v1은 Read-only 우선이다.8. 자동매매/주문/출금/이체는 v1 범위 밖이다.9. Broker별 차이는 BrokerAdapter에서 흡수한다.10. Broker symbol을 primary key로 쓰지 않고 internal security_id로 정규화한다.11. Security mapping이 불확실하면 fail-closed한다.12. PIT/no-lookahead/provenance/version/track-record immutability는 사용자 Weight로 해제할 수 없는 Locked Rule이다.13. available_at <= decision_time 규칙을 유지한다.14. Weight Editor는 한 창의 계층형 UI이며 긴 상세 설명을 넣지 않는다.15. GROUP/WEIGHT/PARAMETER/COMPUTED/INFORMATION/LOCKED를 구분한다.16. 미확정 Official Weight를 임의 생성하지 않는다.17. PROVISIONAL weight를 Production 값처럼 취급하지 않는다.18. QGV↔Technical score scale을 임의로 72→7.2처럼 변환하지 않는다.19. Preview/Sandbox/Backtest/Forward/Actual Track Record를 구분한다.20. Strategy Version과 모든 결과의 provenance/hash를 보존한다.미해결 upstream:- Technical output의 available_at propagation 실제 구현 검증- QGV↔Technical score-scale 산술 계약- QGV/Technical/Macro Official Weight Dataset 최종 검증이 세 항목을 Personal Layer에서 추측으로 해결하지 마. 원 시스템 SSoT/코드/테스트에서 확인·해결한다.현재 상태:- Personal Layer Architecture: 100% 설계 완료 / FREEZE- Personal Layer Implementation: NOT STARTED- Implementation Plan: READY- GitHub/저장소 변경: 이 설계 릴레이 자체로는 요구하지 않음구현 우선순위(실제 구현 단계가 열렸을 때):P0 Common ContractsP1 Strategy InfrastructureP2 Portfolio InfrastructureP3 Broker Read LayerP4 Portfolio Gap / Personal FitP5 UIP6 Validation단, Personal Layer 구현은 기존 REAL-DATA Main Track을 침범하지 않는다.변경 분류:- PATCH: Freeze 유지- CONTRACT CHANGE: 영향 Contract만 재검증- ARCHITECTURE CHANGE: Freeze 재검토기존 code.md 원칙을 그대로 적용한다:정확성·안전성 > 사용자 요구사항 > 기존 동작 보존 > 단순함 > 유지보수성 > 성능 > 확장성.작업 마지막에는 반드시 다음을 보고한다:- 진행률- 상태- 이번에 실제 변경한 것- 테스트 결과- 미해결 문제- 다음 단계


## 1. Purpose

Personal Investment Layer v1은 기존 Investment System의 QGV, Technical, Macro, Portfolio, Simulation, Leaderboard, Track Record를 대체하거나 재설계하지 않는다. 기존 분석·포트폴리오 시스템 위에 사용자 전략 설정 + 실제 증권계좌 상태 + 모델 포트폴리오와의 차이 + 개인 Decision Context를 추가하는 계층이다.
기존 Main Track의 우선순위는 유지한다.
`REAL-DATA → complete PIT candidate pool → official_mcap500_snapshot_from_store → real single_as_of → ≥3-date walk-forward → actual 500-company network benchmark → Promotion/validation`


## 2. Scope / Non-Scope

In Scope
Strategy Profile
Hierarchical Strategy Weight Tree
Official / Custom Strategy isolation
Strategy Versioning
Model Portfolio
Broker Hub abstraction
Security Resolver
Actual Portfolio
Portfolio Gap
Personal Fit v1
Personal Dashboard contract
PIT/time/data-quality/freshness contracts
Read-only security model
Preview / Sandbox / Backtest / Forward / Actual Track Record separation
Out of Scope for v1
자동매매
Buy/Sell 주문 실행
출금/이체
Personal Fit 단일 종합점수
검증되지 않은 AI 자동 Weight 최적화
미확정 upstream 계약의 추측 기반 해결


## 3. Architecture

Investment System├─ QGV├─ Technical├─ Macro├─ Portfolio├─ Simulation├─ Leaderboard├─ Track Record└─ Personal Investment Layer   ├─ Strategy Profile   │  └─ Hierarchical Strategy Weight Tree   ├─ Model Portfolio   ├─ Broker Hub   ├─ Security Resolver   ├─ Actual Portfolio   ├─ Portfolio Gap   ├─ Personal Fit   └─ Personal Dashboard
Responsibility shorthand:
QGV = What?
Technical = When / How?
Macro = Environment?
Portfolio = How much?
Broker = What do I actually own?
Portfolio Gap = How different am I from the model?
Personal Fit = What does that difference mean under my strategy and constraints?


## 4. Strategy Profile

StrategyProfile├─ WeightTree│  ├─ QGV│  ├─ Technical│  └─ Macro├─ AdvancedParameters├─ RiskProfile├─ PortfolioPolicy├─ UniversePolicy└─ VersionMetadata
BrokerAccount는 StrategyProfile 외부에 둔다.
Top-level QGV/Technical/Macro 영향도와 각 시스템 내부 scoring weight는 의미가 다를 수 있다. 단순 `Final = QGV*w + Technical*w + Macro*w`를 Official 기본계약으로 강제하지 않는다. Custom Integration이 향후 명시적으로 필요할 때만 별도 계약으로 연다.


## 5. Hierarchical Strategy Weight Tree

Weight Editor는 한 창의 계층형 편집 UI다. 상세 설명은 QGV/Technical/Macro 원래 분석 화면에 남기고, Weight Editor에는 이름·값·상태·편집 컨트롤만 둔다.
Strategy Weight Editor├─ QGV│  └─ ...├─ Technical│  └─ ...└─ Macro   └─ ...
Node Types
`GROUP`
`WEIGHT`
`PARAMETER`
`COMPUTED`
`INFORMATION`
`LOCKED`
Maturity
`PRODUCTION`
`VALIDATED`
`PROVISIONAL`
`UNRESOLVED`
`LOCKED`
Only eligible `WEIGHT` nodes may be edited.  
`PARAMETER`는 Advanced Strategy Settings에 둔다.  
`COMPUTED`는 모델 출력이다.  
`LOCKED`는 사용자 customization으로 변경할 수 없다.
Local / Global Weight
Local Weight = 사용자 편집 대상
Global Weight = 계층 경로상의 Local Weight 곱
Global Weight는 계산값이며 직접 편집하지 않는다.
sibling local weights는 해당 부모 아래에서 합계 규칙을 만족해야 한다.
parent weight가 0이 되어도 child local mix는 보존할 수 있으나 effective global contribution은 0이 된다.


## 6. Node Registry Contract

권장 분리:
NodeDefinition- node_id- parent_id- system- node_type- weight_role- maturity- official_weight- editable_policy- source_spec_id- source_spec_version- effective_from- deprecated_atWeightOverride- strategy_version_id- node_id- local_weight- created_at
`custom_weight`를 Official NodeDefinition 자체에 저장하지 않는다.
Stable node ID는 display label이나 version을 ID에 인코딩하지 않는다. 단순 rename은 같은 ID를 유지할 수 있지만 semantic split/merge는 새 ID와 migration mapping을 사용한다.
Definition Tree, Effective Tree, Evaluation Graph를 구분한다.


## 7. Official vs Custom Strategy

Effective Custom Strategy= Official Registry Version+ Immutable Versioned User Overrides
User customization MUST NOT mutate:
Official QGV
Official Technical
Official Macro
Official Leaderboard
Official Track Record
Official 업데이트가 기존 Custom Strategy를 silent rebase하면 안 된다. 기존 Custom은 자신이 참조한 base registry/version으로 재현 가능해야 한다. 새 Official로 이동하려면 clone/rebase하여 새 Strategy Version을 만든다.


## 8. Strategy Versioning

StrategyVersion- strategy_version_id- strategy_id- base_registry_version- base_official_strategy_version- override_set_hash- parameter_profile_version- risk_profile_version- portfolio_policy_version- universe_policy_version- status- created_at- activated_at- effective_from
권장 상태:
`DRAFT → SANDBOX → VALIDATED → ACTIVE → ARCHIVED`
저장은 기존 버전 overwrite가 아니라 새 immutable version 생성이 기본이다.


## 9. Model Portfolio

Model Portfolio는 Strategy Version의 결과다.
ModelPortfolioSnapshot- strategy_version_id- as_of- universe_snapshot_id- holdings[]  - security_id  - target_weight  - rank  - qgv_context  - technical_context  - macro_context  - reason_codes- cash_target- portfolio_policy_id- calculation_version- snapshot_hash
`target_weight != order`
Model Portfolio는 실제 계좌를 변경하지 않는다.


## 10. Broker Hub

Broker Hub responsibilities:
Authentication
Account discovery
Balance read
Position read
Transaction read
Order-history read where supported
Normalization
Sync / Freshness
v1은 READ-ONLY first다.
Common Adapter
BrokerAdapterconnect()refresh_auth()disconnect()get_accounts()get_balances()get_positions()get_transactions()get_orders()get_capabilities()get_sync_status()sync()
Broker별 인증/API 차이는 Adapter 내부에서 흡수한다.
Capabilities 예:
ACCOUNTS
POSITIONS
CASH
TRANSACTIONS
ORDERS_READ
REALTIME_POSITIONS
COST_BASIS
REALIZED_PNL
UNREALIZED_PNL
지원하지 않는 기능은 임의 구현하지 않고 `UNSUPPORTED`로 표현한다.


## 11. Broker Security Boundary

v1:
Account Read: allowed
Balance Read: allowed
Position Read: allowed
Transaction Read: allowed
Order History: if supported
Buy/Sell: out of scope
Transfer/Withdrawal: out of scope
Auto Trading: out of scope
Broker credential/token은 분석 엔진이나 frontend persistent state에 평문으로 전달·보관하지 않는다. Credential layer와 normalized portfolio data를 분리한다.


## 12. Security Resolver

Broker symbol을 canonical primary key로 사용하지 않는다.
Broker Instrument      ↓Security Resolver      ↓internal security_id
가능한 identifiers:
ticker
exchange
share class
CIK
ISIN
FIGI (available)
effective_from
effective_to
Uncertain mapping = fail-closed.  
비슷한 ticker라는 이유로 자동 매핑하지 않는다.


## 13. Actual Portfolio

ActualPortfolioSnapshot- user_id- account_scope- as_of- accounts[]- positions[]- cash[]- currency[]- pending_orders[] (if available/read-only)
Position canonical fields 예:
Position- account_id- security_id- quantity- market_price- market_value- average_cost- cost_basis- unrealized_pnl- currency- price_as_of- position_as_of- data_quality
Multi-broker는 Account Aggregator를 통해 전체/증권사별/계좌별 view를 제공할 수 있다. 같은 security_id는 unified view에서 합산 가능하되 account-level provenance를 보존한다.


## 14. Portfolio Gap

gap = model_weight - actual_weight
Gap은 descriptive state다.
Gap MUST NOT be interpreted directly as:
BUY
SELL
order quantity
PortfolioGapSnapshot- model_snapshot_id- actual_snapshot_id- calculated_at- security_id- model_weight- actual_weight- gap- quality_status- reason_codes


## 15. Personal Fit v1

Personal Fit v1은 단일 종합점수가 아니라 multi-axis Decision Context다.
Axes:
Fundamental
Technical
Macro
Portfolio Fit
Risk
Account Context
Personal Fit MUST NOT modify upstream QGV, Technical, Macro scores.
Possible Decision States:
`OBSERVE`
`ELIGIBLE_TO_ADD`
`HOLD_CONTEXT`
`REBALANCE_REVIEW`
`RISK_REVIEW`
`BLOCKED`
이 상태는 `BUY/SELL`과 동일하지 않다.
PersonalFitSnapshot- strategy_version_id- qgv_snapshot_id- technical_snapshot_id- macro_snapshot_id- model_portfolio_snapshot_id- actual_portfolio_snapshot_id- gap_snapshot_id- risk_snapshot_id- decision_state- decision_policy_version- reason_codes[]- calculated_at
Machine-readable reason code를 우선 보존하고 frontend가 설명문을 생성한다.


## 16. Personal Dashboard

최소 구성:
Active Strategy
Actual Portfolio
Model Portfolio
Portfolio Gap
Needs Attention
Position-level Personal Fit
Broker sync/freshness status
Broker 미연결 사용자도 QGV/Technical/Macro/Weight Editor/Leaderboard/Simulation/Model Portfolio를 사용할 수 있어야 한다. Broker 연결은 기존 기능의 prerequisite가 아니다.


## 17. PIT / Time Contract

최소 구분:
`observed_at`
`available_at`
`decision_time`
`calculated_at`
Locked invariant:
available_at <= decision_time
`as_of`를 `available_at`과 동일하다고 가정하지 않는다. No-lookahead는 사용자 Weight로 해제할 수 없다.
Technical output에서 `available_at`이 최종 산출물까지 실제 전달되는지는 upstream 구현 검증 항목이다. Personal Layer가 임의 시간을 생성하지 않는다.


## 18. Data Quality / Freshness

공통 quality status:
`VALID`
`PARTIAL`
`STALE`
`UNRESOLVED`
`INVALID`
Quality와 Confidence는 별개다.
Broker/portfolio freshness는 position, price, FX, mapping, sync 상태를 고려한다. 중요한 구성요소가 stale/unresolved이면 Portfolio Gap/Personal Fit도 제한 상태로 내려간다.


## 19. Currency / FX Contract

Monetary value에는 필요 시 다음 provenance를 보존한다:
amount
currency
fx_rate
fx_pair
fx_as_of
base_currency
원통화를 보존하고 portfolio 비교를 위해 명시적인 base currency conversion을 수행한다. 오래된 FX를 최신 valuation처럼 취급하지 않는다.


## 20. Preview / Sandbox / Backtest / Forward

결과 namespace를 구분한다:
`OFFICIAL`
`CUSTOM_ACTIVE`
`SANDBOX`
`PREVIEW`
`BACKTEST`
`FORWARD`
Preview에서 Strategy/Model Portfolio는 변할 수 있지만 Actual Portfolio는 절대 변하지 않는다.
Backtest와 Forward는 가능한 한 동일한 Strategy Engine을 사용하고, 차이는 시점 데이터와 execution simulation에서 발생하도록 한다.


## 21. Track Record

Strategy Version 변경 시 과거 결과를 overwrite하지 않는다.
구분:
Official Strategy Track Record
Custom Strategy Track Record
Model Portfolio Track Record
Actual Account Performance
Retrospective Backtest와 Forward Track Record를 구분한다.


## 22. Locked Rules

사용자 Weight로 해제할 수 없는 대표 규칙:
PIT
No-lookahead
Data provenance
Vintage preservation where applicable
Corporate-action handling
Backtest execution integrity
Track-record immutability
Broker authorization/security
Security identity fail-closed
Missing != zero
검증되지 않은 missing-weight 자동 재분배 금지
모델 산출 probability를 사용자 weight로 오인하지 않음


## 23. Official Weight Dataset Policy

미확정 Official Weight를 임의 생성하지 않는다.
`PRODUCTION`: Official editable exposure 가능
`VALIDATED`: 정책에 따라 활성화 가능
`PROVISIONAL`: Sandbox/연구 범위
`UNRESOLVED`: 사용자 편집 비활성
`LOCKED`: 변경 불가
현재 확인되지 않은 QGV/Technical/Macro weight를 예시값으로 production에 넣지 않는다.


## 24. Upstream Dependencies

A. Technical `available_at` propagation
PIT/time contract 자체는 존재하는 것으로 취급한다.
실제 Technical 최종 output/schema까지 전달되는지 코드/테스트에서 검증 필요.
Personal Layer가 추정하지 않는다.
B. QGV ↔ Technical score-scale
권위 있는 산술 mapping이 확인되기 전에는 변환하지 않는다.
`72 → 7.2` 같은 암묵 변환 금지.
cross-scale arithmetic이 실제 필요할 때만 명시적 versioned contract를 추가한다.
원본 score와 scale metadata를 보존한다.
C. Official Weight Dataset
QGV / Technical / Macro의 실제 authoritative SSoT에서만 확정한다.
미확정 값은 unresolved/provisional로 유지한다.
이 세 항목은 upstream dependency이며 Personal Layer Architecture Freeze 자체를 무효화하지 않는다.


## 25. Implementation Sequence

실제 구현 단계가 열렸을 때:
P0 Common Contracts
Security ID
PIT / Time
Version / Hash
Data Quality
P1 Strategy Infrastructure
Node Registry
WeightTreeEngine
StrategyVersion
Sandbox
P2 Portfolio Infrastructure
ModelPortfolioSnapshot
ActualPortfolioSnapshot
SecurityResolver
P3 Broker Read Layer
BrokerAdapter
Normalizer
Sync/Freshness
AccountAggregator
P4 Comparison
PortfolioGapSnapshot
PersonalFitSnapshot
P5 UI
Strategy Weight Editor
Personal Dashboard
Broker Connection
P6 Validation
PIT
Regression
Multi-broker
Forward Track Record
DO NOT begin or prioritize this sequence if it disrupts the current REAL-DATA Main Track.


## 26. Freeze / Change Policy

PATCH
데이터값, API mapping, field propagation, adapter mapping 등의 수정.  
→ Architecture Freeze 유지.
CONTRACT CHANGE
기존 interface/field의 의미가 변경되는 경우.  
→ 영향받는 Contract만 재검증.
ARCHITECTURE CHANGE
레이어 책임이나 핵심 데이터 흐름 자체가 변경되는 경우.  
→ Freeze 재검토.
Official Weight 확정, `available_at` propagation 수정, broker symbol mapping 추가는 일반적으로 Architecture Change가 아니다.
자동주문처럼 새로운 책임을 추가하는 경우는 별도 Architecture 검토 대상이다.


## 27. Acceptance Criteria

Architecture
- [x] Responsibility boundaries defined
- [x] Official / Custom isolation
- [x] Model / Actual isolation
- [x] Weight hierarchy defined
- [x] Node types/maturity defined
- [x] Versioning defined
- [x] Broker abstraction defined
- [x] Security Resolver defined
- [x] Portfolio Gap defined
- [x] Personal Fit v1 defined
- [x] PIT/time rules defined
- [x] Data quality/freshness contract defined
- [x] Currency/FX boundary defined
- [x] Security/read-only policy defined
- [x] Preview/Backtest/Forward separation defined
- [x] Freeze/change policy defined
Implementation
- [ ] Not started
Upstream
- [ ] Technical `available_at` propagation verified in implementation
- [ ] QGV/Technical scale contract resolved if arithmetic mapping is actually required
- [ ] Official Weight Dataset verified from authoritative SSoT
Architecture completion MUST NOT be reduced merely because implementation has not started.  
Implementation completion MUST NOT be claimed from architecture alone.


## 28. Relay Operating Rules

1. 기존 CURRENT_HANDOFF와 기존 SSoT가 우선이다.
2. 이 문서는 additive frozen architecture다.
3. Personal Layer 때문에 기존 시스템을 재작성하지 않는다.
4. Main REAL-DATA Track을 중단하지 않는다.
5. 추측으로 unresolved contract를 닫지 않는다.
6. 코드/테스트가 문서와 충돌하면 실제 증거를 확인하고 Conflict/Evidence 방식으로 처리한다.
7. 이미 완료된 설계를 진행률을 위해 확장하지 않는다.
8. 구현 시 최소 변경 + 회귀검증 원칙을 적용한다.
9. 새 증권사/API는 기존 Adapter contract를 우선 사용한다.
10. Architecture 변경이 필요한 경우에만 Freeze 재검토를 제안한다.

## 29. Relay Completion Report Format

각 릴레이 작업 종료 시:
진행률:상태:이번에 실제 변경한 것:테스트 결과:미해결 문제:다음 단계:


## 30. Current Handoff Summary

Personal Investment Layer v1Architecture       = 100% / FROZENImplementation     = NOT STARTEDImplementation Plan= READYCurrent Main Priority= Existing Investment-System REAL-DATA / Promotion ValidationOpen Upstream1. Technical available_at implementation propagation2. QGV ↔ Technical scale contract if arithmetic mapping is required3. Official QGV / Technical / Macro Weight Dataset verification
Do not add speculative features merely to continue progress.
