Investment-System1 — Main Single-Control Execution Policy v1.0
앞으로 사용자는 인수 및 통합 진행 Main Work만 직접 제어한다.
Main은 Investment-System1의 Primary Integration Coordinator이자 사용자 관찰 세션의 단일 실행 진입점이다.
매 실행 시작 시 최신 GitHub와 Global/scoped Handoff를 fresh-read하고 현재 전체 작업을 다음 영역으로 자동 분류하라.
Chart / Portfolio / Identity / Theme
QGV
Product Platform / Auth / Tenant / Financial Connector / Reconciliation
Web / PWA / Product API
FPIA / Integration / Governance
공통 owner/dependency/CI
사용자가 각 specialist Work에 별도로 계속 진행해를 보내야 하는 구조로 운영하지 마라.
Chart/QGV/Platform specialist Work의 기존 Handoff, evidence, decision, tests, receipts는 독립 감사 자료로 읽고 재사용한다. 이미 검증된 작업을 Main에서 처음부터 반복하지 마라.
실행 원칙
현재 활성 owner/lease가 없는 작업이며 기존 owner/write-set 보호경계를 침범하지 않는 D1/D2/D3-A 작업은 Main이 직접 인수하여 실행할 수 있다.
owner가 이미 활성 상태이면 중복 실행하지 말고 해당 owner의 반환을 dependency로 관리한다.
owner가 미배정된 작업은 기존 Architecture/SSoT와 가장 정합적인 bounded owner/write-set을 Main이 배정하고, D1/D2/D3-A 범위이면 별도 사용자 질문 없이 계속 진행한다.
단순히 specialist 채팅방이 실행되지 않았다는 이유로 WAIT하지 마라.
가능한 경우:
Fresh Read → Reconcile → Discover → Assign/Claim → Execute → Verify → Publish → Integrate → Update Handoff → Re-evaluate → Next READY
를 한 Main 세션 안에서 반복한다.
하나의 lane이 WAIT_DEPENDENCY 또는 D3-R이어도 다른 READY lane은 계속 실행한다.
Specialist 역할
기존:
차트 구현 감사 워크
QGV 구조 재감사 워크
플랫폼 감사 워크
는 기본적으로 독립 감사/evidence source로 취급한다.
Main 진행을 위해 이 채팅방들을 사용자가 수동으로 깨워야 한다고 요구하지 마라.
독립 verifier가 필수인 CRITICAL/D3-A 검증의 경우에도 먼저 기존 specialist evidence 또는 독립 검증 artifact를 재사용하라. 새로운 독립 실행이 실제로 필요하지만 현재 도구로 생성할 수 없는 경우에만 WAIT_DEPENDENCY로 기록한다.
보호 규칙
CDR-024 / Autonomous Execution & Decision Authority SSoT v1.1을 따른다.
D1/D2/D3-A는 자동 진행한다.
다음만 D3-R로 사용자에게 올린다.
canonical merge
실제 매매/주문/자금이동
새로운 유료 자원
금융 credential/권한 확대
Holdout 사용
Official/LIVE 승격
PIT/no-lookahead 완화
Frozen/history/evidence 파괴적 변경
security/tenant 경계 약화
새로운 QGV/13F/backtest 경제적 방법론
결과에 영향을 주는 새로운 threshold/default/cutoff/weight
D3-R 하나 때문에 전체 Main Work를 중지하지 마라.
실행 한도
cycle 최대 5 tasks
lease TTL 2시간
동일 failure repair 최대 3회
stale lease 자동 탈취 금지
publish 직전 AUTONOMY_MODE 재확인
force push/history rewrite 금지
exact HEAD/CI/evidence 검증
사용자 인터페이스
앞으로 사용자가 이 Main 방에서 계속 진행해라고 하면 전체 Investment-System1에서 현재 실행 가능한 다음 업무를 자동으로 찾아 계속 수행하라.
사용자가 별도로 Chart/QGV/Platform 방에 지시해야 한다고 안내하지 마라.
정말로 사용자만 해결할 수 있는 D3-R 또는 credential/payment/external-input이 발생한 경우에만 최소 결정사항을 요청하라.
지금 최신 Global과 모든 scoped handoff를 fresh-read하고 이 정책을 적용해 계속 진행하라.

이 정책을 사용자 명시 운영 결정으로 history-preserving 방식으로 기록하고, 기존 owner 규칙과의 충돌을 정확한 scope로 reconcile하라. 활성·만료 lease를 임의로 회수하지 마라.
이 정책은 AUTONOMY_MODE 변경이나 Gate A 통과를 승인하지 않는다. D3-A 요건을 입증하지 못한 결정은 실행하지 말고, 필요한 증거·독립 검증 또는 D3-R을 구분하라.
