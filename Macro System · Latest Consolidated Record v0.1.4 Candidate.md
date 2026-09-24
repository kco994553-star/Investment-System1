Macro System · Latest Consolidated Record v0.1.1  
기준: 2026-09-22  
문서 목적: 지금까지 Macro System에서 진행·검증된 최신 내용을 저장용 기준 기록으로 통합한다. 새로운 사양을 임의로 추가하지 않는다.

1\. 현재 최신 기준  
Macro System 최신 확인 기준은 v0.1.1이다.  
오프라인 회귀검증 결과는 28/28 PASS(100%)로 기록되어 있다.  
다만 외부 API 실제 응답 확인과 QGV/Technical 실제 패키지 연결 전에는 “실데이터 연결 완료” 또는 “전체 Investment System 통합 완료”로 승격하지 않는다.

2\. Investment System 내 위치  
Investment System \= QGV \+ Technical \+ Macro \+ Portfolio/Execution.  
QGV는 Fundamental 판단을 담당한다.  
Technical은 가격상태·경로·실행환경을 담당한다.  
Macro는 거시 Regime, 시장환경, 금리·유동성·경기·위험 Context를 제공한다.  
최종 Target Weight와 Order는 상위 Investment System에서 한 번만 결정한다.

3\. 핵심 경계  
Macro는 QGV 원본 점수를 직접 변경하지 않는다.  
Macro Signal은 별도 Evidence/Confidence와 함께 유지한다.  
거시 변화만으로 기업 Fundamental Snapshot을 자동 재작성하지 않는다.  
Macro는 자동매매 엔진이 아니라 상위 Portfolio/Execution 의사결정의 Context/Multiplier/Gate 입력으로 사용한다.

4\. 기존 기준에서 보존할 설계  
이전 투자시스템 설계에서 Macro v1.0 후보로 VMR-V2 Dual Horizon \+ DB1 \+ Medium 구조가 검토·고정 후보로 관리되었다.  
Macro 상태판은 Normal / Warning / Emergency 구조로 설계되었으며 상태 자체가 자동주문을 발생시키지 않는다.  
이는 현재 v0.1.1 구현·검증 기록과 구분하여 Version History에서 보존한다.

5\. QGV 연결  
QGV Fundamental Snapshot은 Macro와 독립적으로 보존한다.  
Macro는 할인율, 유동성, 경기국면, 시장 Risk Environment 등의 Context를 제공한다.  
QGV Valuation/Scenario 해석에 필요한 거시 Evidence를 제공할 수 있지만 QGV Raw Score를 덮어쓰지 않는다.

6\. Technical 연결  
Technical의 Signal/Regime/Forecast와 Macro Regime을 상위 Investment System에서 결합한다.  
Forecast Horizon이 길어질수록 Macro Context의 중요도가 커질 수 있다는 설계 방향을 유지한다.  
Technical 또는 Macro 어느 한쪽이 독립적으로 최종 주문을 생성하지 않는다.

7\. 상위 통합 구조  
최신 상위 설계 기록에는 Invest System v1.1과 v1.2 PROVISIONAL 설계가 존재한다.  
v1.1 흐름: QGV/Technical/Macro Snapshot → Gate → Integration → Portfolio/Risk → Target Weight → Order → Execution.  
v1.2 PROVISIONAL에서는 Target Weight \= Base × OM × TM × MM × RM 구조를 검토했다.  
OM/TM/MM/RM 구간표, Portfolio Cap, Deadband 0.50%p, 단계진입 50→75→100%는 Calibration 전 PROVISIONAL 값이며 공식 고정값으로 승격하지 않는다.

8\. 현재 검증 상태  
완료로 기록 가능한 범위:  
\- Macro v0.1.1 기준 오프라인 회귀검증 28/28 PASS.  
\- 모듈 내부 규칙과 기존 계약에 대한 회귀검증.  
완료로 기록하면 안 되는 범위:  
\- 외부 데이터 공급자 API 실응답 검증.  
\- 실제 QGV 패키지 연결 검증.  
\- 실제 Technical 패키지 연결 검증.  
\- 전체 Investment System End-to-End 실데이터 통합.  
\- 실제 운용/Forward Validation.

9\. 데이터/API 상태  
현재 저장 기준에서는 API 실응답 확인이 남아 있다.  
따라서 API Key가 필요한 Provider와 실제 인증/응답이 확인되기 전까지 실데이터 연결 완료로 표시하지 않는다.  
키·Secret은 코드나 문서에 직접 저장하지 않고 환경변수/Secret 관리 경계를 유지한다.

10\. Track Record 및 검증  
Macro Regime/Signal/Evidence/Confidence는 당시 시점 Snapshot으로 보존해야 한다.  
과거 결과를 이용해 당시 Macro 판단을 덮어쓰지 않는다.  
Backtest, Out-of-Sample, Forward Validation을 구분한다.  
상위 Investment System의 실제 성능과 Macro 기여도를 분리해서 검증할 수 있어야 한다.

11\. 최신 상태 분류  
Confirmed:  
Macro v0.1.1 최신 확인 기준.  
28/28 오프라인 회귀검증 PASS.  
QGV Raw Score 불변.  
Technical/Macro가 직접 최종 주문을 만들지 않음.  
상위 Investment System이 최종 Target Weight/Order를 결정.  
실데이터/API/E2E 완료 표시 금지.

Provisional / Validation Pending:  
Invest v1.2의 OM/TM/MM/RM 수치 정책.  
Deadband 0.50%p.  
단계진입 50→75→100%.  
VMR-V2 Dual Horizon/DB1/Medium의 최신 Macro v0.1.1과의 최종 정합성.  
외부 API Provider/실응답.  
QGV/Technical 실제 패키지 연결.  
Forward Validation.

12\. 저장 원칙  
이 문서는 저장 허브용 최신 통합 기록이다.  
원 개발 대화에서 더 최신 확정본이 생기면 해당 내용을 우선 반영한다.  
과거 결정은 삭제하지 않고 Version/Decision History로 이동한다.  
미확정 수치는 자동으로 공식값으로 승격하지 않는다.  
13\. 2026-09-22 설계 업데이트 — v0.1.4 Candidate 이후  
현재 구현 기준선은 Macro System v0.1.4 Candidate이다.  
오프라인 회귀검증 기준선은 36/36 PASS다.  
전체 개발 6단계 중 완료 단계는 2/6 \= 33.3%이며, Stage 3 실데이터/PIT와 Stage 4 기존 모듈 통합은 진행 중이다.  
기능 아키텍처 설계는 Design Review 직전 단계까지 진행되었으며, 설계 진행률은 약 98%로 관리한다. 이 수치는 전체 개발 진행률과 구분한다.

14\. Macro System 최종 기능 아키텍처  
Macro Data/PIT → Macro Factors → Macro State → Regime → Scenario Engine → Transmission Engine → Industry/Company Exposure → Q/G/V Context \+ Technical Conditional Context → Portfolio Risk/Budget Context → Decision Integration → Track Record/Calibration의 흐름으로 설계한다.  
Macro System은 방향을 단정하는 예측기가 아니라 조건부 확률과 거시 Context/Risk를 제공하는 시스템이다.  
Macro 원본 판단, QGV Base, Technical Base는 서로 덮어쓰지 않고 독립 Snapshot으로 보존한다.

15\. Macro Factors와 State  
핵심 Macro Axis는 Growth, Inflation, Liquidity, Monetary Policy, Credit, Labor, Fiscal, FX로 구성한다.  
각 축은 Level, Direction, Momentum, Surprise, Stress, Confidence를 보존한다.  
단일 Macro Score만으로 의사결정을 수행하지 않는다.  
Regime은 하나의 확정 라벨이 아니라 복수 국면의 확률분포와 전환 정보를 보존한다.

16\. Scenario Engine  
Macro Scenario는 S1\~Sn 가변 구조를 사용하며 고정 개수로 제한하지 않는다.  
각 Scenario는 probability, horizon, path, evidence, confidence를 가진다.  
Scenario Engine은 발생 가능성이 있는 미래경로를 다루며 Stress Engine과 분리한다.  
Macro Scenario와 Technical Scenario를 동일 객체로 취급하지 않는다.

17\. Transmission Engine  
모든 Macro 영향은 Factor → Economic Channel → Industry → Company → Fundamental Target → Q/G/V Context의 설명 가능한 전달경로를 가져야 한다.  
TransmissionPath는 factor, shock\_direction, economic\_channel, industry, company, fundamental\_target, Q/G/V\_target, direction, magnitude, lag, duration, evidence, confidence, available\_at, source\_refs, model\_version을 보존한다.  
Magnitude는 QGV Raw Score에 직접 더하는 값이 아니다.  
Lag와 Duration은 분리한다.

18\. Company Macro Exposure  
기업 Macro Exposure는 Structural Exposure, Empirical Exposure, Market-Implied Exposure, Event Exposure를 분리하여 보존한다.  
Exposure는 얼마나 노출되어 있는지를 뜻하고 Sensitivity는 노출 1단위 변화가 기업에 미치는 영향을 뜻하므로 서로 동일하게 취급하지 않는다.  
Impact는 Shock × Exposure × Sensitivity × Persistence × Confidence의 설명 구조로 분석할 수 있으나 검증 전 기계적인 투자점수 공식으로 고정하지 않는다.  
기본 Horizon은 H1 0\~1개월, H2 1\~3개월, H3 3\~12개월, H4 1\~3년으로 설계하며 경로별 Lag/Duration을 별도로 유지한다.

19\. QGV 연결  
Macro는 QGV Base를 수정하지 않는다.  
Macro는 Q, G, V 각각에 별도의 Pressure/Tailwind Context를 제공한다.  
Q에는 이자비용, 재무건전성, 현금흐름 안정성, 마진 안정성, Pricing Power, Credit Risk 등의 경로를 연결한다.  
G에는 Revenue, Orders, Backlog, CAPEX Cycle, End-market Demand, Government Spending 등의 경로를 연결한다.  
V에는 Risk-free Rate, Real Yield, Credit Spread, ERP, Discount Rate, Terminal Growth, Liquidity Premium 등의 경로를 연결한다.  
QGV Base와 Macro Context는 UI와 데이터에서 동시에 보존한다.

20\. Technical 연결  
Technical의 S1\~Sn Base Probability는 불변으로 보존한다.  
Macro는 P(Si | Macro State)에 필요한 조건부 Context를 제공한다.  
Technical Base Probability와 Macro-adjusted/Conditional Probability를 동시에 저장해 Macro 추가가 Calibration을 개선했는지 사후 검증할 수 있게 한다.  
Macro Adjustment Budget 개념을 두되 정확한 조정 상한은 백테스트와 Calibration 전 고정하지 않는다.  
QGV, Technical, Macro가 충돌하는 상태는 정상 상태로 취급하며 Conflict/Agreement 정보를 별도로 보존한다.

21\. Portfolio 연결  
Macro 출력은 regime, scenario\_distribution, sector\_exposure, factor\_exposure, company\_exposure, risk\_budget\_pressure, concentration\_risk, cash\_pressure, hedge\_pressure, confidence, horizon의 Context를 제공한다.  
cash\_pressure는 cash\_weight와 동일하지 않다.  
현금 비중은 0% 고정값이 아니며 Portfolio Policy가 허용한 범위와 사용자 설정에 따라 최종 결정한다.  
Macro는 Expected Return을 직접 결정하기보다 Risk Budget과 Exposure Risk에 우선적으로 영향을 주도록 설계한다.  
종목 분산과 별개로 공통 Macro Factor에 대한 Portfolio Macro Concentration을 측정한다.

22\. Stress Engine  
Scenario와 Stress를 분리한다.  
Stress는 Historical, Hypothetical, Reverse Stress의 세 계층을 지원한다.  
Stress 결과에 실제 발생확률을 자동 부여하지 않는다.  
Shock은 factor, magnitude, direction, onset, duration, decay, correlations, transmission\_assumptions, evidence, source\_refs, created\_at, available\_at을 포함해 버전화한다.  
비선형 영향, Threshold, Feedback Loop를 표현할 수 있게 하되 초기 구현에서 검증되지 않은 복잡한 동적모형을 강제하지 않는다.  
Portfolio Stress 결과는 Tail Impact, Sector/Company/Factor Contribution, Macro Concentration, Correlation Breakdown, Liquidity Risk, Valuation Compression, Fundamental Pressure, Recovery Horizon, Confidence, Model Limitations를 보존한다.

23\. PIT Backtest  
모든 Macro 데이터는 observation\_period, release\_at, available\_at, vintage\_at, ingested\_at을 구분한다.  
decision\_time에서 사용할 수 있는 데이터는 available\_at \<= decision\_time 조건을 만족해야 한다.  
현재 시점의 수정된 역사 데이터와 당시 투자자가 실제로 이용 가능했던 PIT 정보집합을 동일하게 취급하지 않는다.  
First Release, Estimate, Revised History 등 Vintage를 구분한다.  
Backtest 평가는 State Accuracy, Regime Quality, Probability Calibration, Transmission Accuracy, Investment Value Added로 분리한다.

24\. Ablation / Track Record / Attribution  
PIT 조건에서 QGV only, Technical only, Macro only 및 각 2개 조합과 QGV+Technical+Macro 전체 조합을 비교할 수 있게 한다.  
Macro Track Record는 Regime Track Record, Scenario Probability Calibration, Transmission Accuracy, Portfolio Value Added, Integration Value Added로 분리한다.  
성과 Attribution은 QGV, Technical, Macro 단독 기여뿐 아니라 QGV×Macro, Technical×Macro, QGV×Technical, Triple Interaction, Residual을 연구 가능하게 원자료를 보존한다.  
성과 평가는 Total Return/CAGR뿐 아니라 Volatility, Sharpe, Sortino, MDD, Calmar, Hit Rate, Turnover, Tail Loss, Recovery Time 및 Calibration을 함께 사용한다.

25\. Walk-Forward / Forward Validation  
Train → Validation → Out-of-Sample → Roll Forward 구조를 사용한다.  
Forward Validation에서는 T0 시점의 Macro Snapshot과 Prediction을 Freeze한 뒤 실제 Outcome과 비교한다.  
Snapshot은 snapshot\_id, model\_version, decision\_time, input\_hash, prediction\_hash를 보존한다.  
Research → Backtest → Walk-Forward → Shadow Mode → Forward Validation → Production Review 순서를 사용한다.  
운용 상태는 RESEARCH → BACKTEST\_VALIDATED → FORWARD\_VALIDATING → PRODUCTION\_REVIEW → PRODUCTION\_ELIGIBLE로 관리하며 자동 승격하지 않는다.

26\. Model Risk  
Data Risk, Revision Risk, Model Risk, Regime Risk, Parameter Risk, Correlation Risk, Structural Break Risk, Policy Shock Risk를 별도 관리한다.  
Model Confidence와 Scenario Probability는 서로 다른 값이다.  
Track Record 결과가 나쁘더라도 시스템이 자동으로 정책 가중치를 변경하지 않는다.  
Outcome → Track Record → Calibration Proposal → Validation → Version Update 절차를 사용한다.

27\. Macro Snapshot 최종 계약 방향  
MacroSnapshot은 META, DATA, FACTORS, STATE, REGIME, SCENARIOS, TRANSMISSION, TECHNICAL\_CONTEXT, PORTFOLIO\_CONTEXT, STRESS, CONFIDENCE, VALIDATION, PROVENANCE 영역을 가진다.  
Provenance에는 source\_refs, input\_hash, model\_hash, prediction\_hash를 보존한다.  
실제 데이터 및 계약 검증이 끝나기 전에는 이 설계만으로 READY 또는 실제 운용 적격으로 승격하지 않는다.

28\. 설계 불변 원칙  
1\) PIT First.  
2\) No Future Leakage.  
3\) Probabilities, not Certainty.  
4\) Scenario ≠ Stress.  
5\) Exposure ≠ Sensitivity.  
6\) Macro Context ≠ QGV Base.  
7\) Macro Context ≠ Technical Base.  
8\) Recommendation ≠ Execution.  
9\) Track Everything.  
10\) Validate Before Promotion.

29\. 현재 검증 및 다음 단계  
FRED 연결 진단은 KEY\_MISSING → KEY\_CONFIGURED → PROVIDER\_REACHABLE → AUTHENTICATED → PIT\_VALIDATED 상태를 분리한다.  
PIT\_VALIDATED 자체는 Investment System READY를 의미하지 않는다.  
QGV/Technical/Macro 정상 통합 Gate는 Macro PIT 검증, QGV 의미 검증, QGV 척도 검증, Technical available\_at 검증, Technical source\_refs 검증이 모두 충족되어야 정상경로 테스트 후보가 된다.  
현재 실제 실데이터 성공 통합과 실제 운용 적격성은 미확인이다.  
다음 작업은 신규 기능 추가가 아니라 Design Review → Requirement Traceability → QGV/Technical/Portfolio 계약 충돌 검사 → PIT/Leakage 검사 → Schema 누락 검사 → 중복 제거 → Design Freeze 후보 판정 순서로 진행한다.

