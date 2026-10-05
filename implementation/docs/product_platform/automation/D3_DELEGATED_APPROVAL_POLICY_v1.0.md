Investment-System1 — D3 Delegated Approval Policy v1.0
기존 D1/D2/D3 체계를 D1 / D2 / D3-A / D3-R로 확장한다.
**D3-A(Design-Aligned Delegated Approval)**는 사용자가 이미 승인한 제품 목표, Architecture, SSoT, Decision Register, 보호원칙과 실질적으로 같은 방향의 결정을 의미한다. 다음 조건을 모두 충족하면 별도 사용자 재승인 없이 자동 승인·실행한다.
기존 승인된 목적과 설계 방향을 유지한다.
새로운 투자방법론·경제적 의미·점수 의미를 만들지 않는다.
기존 보호경계를 완화하지 않는다.
PIT/no-lookahead/provenance/Frozen/history를 약화시키지 않는다.
보안·Tenant·금융계정 권한을 확대하지 않는다.
실제 매매·주문·자금이동을 발생시키지 않는다.
기존 evidence/history를 삭제·rewrite하지 않는다.
합리적으로 rollback 가능하다.
deterministic 또는 독립 검증이 가능하다.
복수 선택지가 있으면 기존 SSoT와 가장 정합적이고 보수적인 방법을 선택한다.
D3-A로 판정하면:
CLASSIFY → AUTO-APPROVE → EXECUTE → VERIFY → DECISION RECEIPT → UPDATE SSoT → RE-EVALUATE → CONTINUE
로 처리한다.
사용자에게 “승인할까요?”라고 다시 묻지 않는다.
Decision Receipt에는 최소한 결정, 근거가 된 기존 SSoT/승인, 대안, 설계정합성, 보호경계 보존 여부, 검증 결과, rollback 가능성을 기록한다.
**D3-R(Reserved)**은 사용자 승인을 유지한다. 다음은 자동승인하지 않는다.
유료 결제 또는 새로운 유료 자원
실제 매매·주문·자금이동
실제 금융기관 credential 제공 또는 권한 확대
Holdout 최초 소비 또는 재소비
Official/LIVE 승격
PIT/no-lookahead 완화
Frozen/history/evidence의 파괴적 변경
보안·Tenant isolation 완화
irreversible delete/migration
QGV/13F/백테스트/투자판단 결과의 의미를 실질적으로 변경하는 새로운 방법론
새로운 numeric threshold/default/cutoff/weight 등 결과를 실질적으로 변경하는 수치정책
기존 SSoT만으로 설계 정합성을 입증할 수 없는 결정
중요: 단순히 합리적으로 보인다는 이유만으로 D3-A로 분류하지 않는다. 기존 SSoT/Decision Register/승인된 Architecture와의 정합성을 구체적인 evidence로 입증할 수 있어야 한다. 불확실하면 D3-R이다.
D3-R이 한 lane에서 발생해도 Work 전체를 중지하지 않는다. 해당 dependent lane만 WAIT시키고 독립적인 D1/D2/D3-A를 계속 실행한다.
기존 D3 중 이미 pending인 항목도 fresh SSoT에서 재분류한다. 기존 설계방향을 단순 구체화하는 항목이면 D3-A로 전환하여 자동 처리하고, Reserved 조건에 해당하는 것만 D3-R로 유지한다.
이 정책은 새로운 제품·투자방법론을 승인하는 포괄 위임이 아니다. 사용자가 이미 결정한 설계 방향을 반복 승인하는 병목을 제거하기 위한 delegated authority다.
목표는:
Human approval frequency ↓
Autonomous completion ↑
Protection boundary 유지
Decision traceability 유지
이다.

