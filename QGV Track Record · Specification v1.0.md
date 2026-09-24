QGV Track Record · Specification v1.0

Purpose  
QGV System의 판단과 실제 이후 결과를 시간축으로 연결하는 검증·감사 모듈이다. “현재 점수가 무엇인가”뿐 아니라 “당시 무엇을 알고 어떤 판단을 했으며 이후 실제로 어떻게 되었는가”를 보존한다.

1\. Core Principle  
과거 Snapshot은 수정하거나 덮어쓰지 않는다.  
새 정보가 들어오면 Revision을 추가한다.  
판단 당시 이용 가능했던 데이터와 이후 결과를 분리한다.  
Track Record는 QGV 점수를 사후에 좋게 보이도록 재작성하는 공간이 아니다.

2\. Record Types  
Analysis Record: QGV Analysis 판단.  
Leaderboard Record: 당시 순위와 Universe.  
Portfolio Decision Record: 편입/제외/비중 변경.  
Simulation Record: 실험 설정과 결과.  
Scenario Record: 부정/중립/긍정 시나리오와 실제 경로.  
Revision Record: 점수/가치/Confidence 변경.  
Data Quality Record: 데이터 수정, 누락, 공급자 변경.

3\. Analysis Snapshot  
record\_id, company\_id, ticker, analysis\_at, qgv\_system\_version, qgv\_standard\_version, profile, Q/G/V, total\_score, attractiveness, type\_adjusted\_qgv, confidence, key\_drivers, peer\_set, valuation\_range, margin\_of\_safety, scenarios, risk\_flags, data\_stamp\_refs.

4\. Revision History  
revision\_id, previous\_record\_id, revised\_at, changed\_fields, old\_value, new\_value, reason, evidence\_refs, confidence\_change.  
Revision 이유를 New Evidence / Data Correction / Methodology Change / Corporate Event / Manual Review로 구분한다.  
Methodology Change는 실제 기업 변화와 분리해 성능평가 시 혼동하지 않는다.

5\. Outcome Windows  
기본 평가창을 1D, 5D, 20D, 3M, 6M, 1Y 및 필요 시 3Y/5Y로 확장한다.  
각 기간의 Price Return과 Total Return을 구분할 수 있게 한다.  
Benchmark-relative Return을 함께 계산한다.  
장기 Fundamental 판단과 단기 가격반응을 동일 지표로 평가하지 않는다.

6\. Scenario Evaluation  
각 Scenario의 전제, 가격/가치 범위, 유효기간, Confidence를 저장한다.  
실제 결과가 어느 Scenario 범위/조건에 가까웠는지 기록한다.  
단일 목표가 적중/실패만으로 평가하지 않고 방향, 범위, 조건 충족, 시간창을 분리한다.

7\. Q/G/V Track Record  
Q, G, V 각 축의 변화와 이후 실적/가격을 연결한다.  
예: Growth 점수 상승 이후 실제 매출/EPS 성장, Valuation 판단 이후 향후 수익률, Quality 판단 이후 Margin/ROIC/FCF 안정성.  
이를 통해 어떤 축이 어떤 시장/기업유형에서 유효했는지 분석한다.

8\. Confidence Calibration  
High/Medium/Low Confidence별 실제 결과 분포를 측정한다.  
High Confidence 판단이 Low Confidence보다 실제로 더 안정적인지 검증한다.  
향후 충분한 표본이 쌓이면 Confidence Calibration Curve를 제공한다.

9\. Key Driver Validation  
각 분석의 Key Drivers 3\~5개를 이후 실제 데이터와 비교한다.  
Driver가 실현/부분실현/미실현/반대로 전개되었는지 기록한다.  
점수 적중 여부뿐 아니라 “왜 맞았거나 틀렸는가”를 학습한다.

10\. Leaderboard Evaluation  
당시 Universe와 QGV Rank를 보존한다.  
Top10/Top30 및 분위수별 이후 수익률과 Benchmark-relative 성과를 측정한다.  
Survivorship Bias를 막기 위해 당시 Universe에서 사라진 기업도 기록에서 제거하지 않는다.

11\. Portfolio Decision Evaluation  
편입, 제외, 증액, 감액, 리밸런싱 당시 이유와 Snapshot을 보존한다.  
결정 이후 성과, 대안 대비 Opportunity Cost, Risk 변화와 연결한다.  
결과가 좋았다는 이유만으로 당시 의사결정 품질이 좋았다고 단정하지 않고 당시 정보와 규칙 준수 여부를 별도 평가한다.

12\. Simulation Track Record  
Simulation ID, PIT 조건, Universe, QGV Weight Profile, Portfolio, Rebalancing, Benchmark, 거래비용/환율 가정, 결과를 보존한다.  
실험 간 비교에서는 바뀐 변수를 기록한다.  
사후 Parameter Tuning과 사전 정의 실험을 구분한다.

13\. Forward Validation  
과거 개발/Out-of-Sample 검증이 충분해지면 실제 미래 데이터만 누적하는 Forward Validation Track을 시작한다.  
Forward 시작일 이후 규칙 변경은 새 Version/Experiment로 분리한다.  
Historical Backtest와 Forward 결과를 한 성과곡선으로 섞어 표시하지 않는다.

14\. Metrics  
Return: Total Return, CAGR, Excess Return.  
Risk: MDD, Volatility, Downside Risk.  
Selection: Top-N spread, quantile spread.  
Scenario: range hit, direction, condition fulfillment.  
Calibration: Confidence bucket outcomes.  
Fundamental: revenue/EPS/FCF/ROIC realization versus prior expectations.  
모든 지표는 표본수와 평가기간을 함께 표시한다.

15\. Failure Taxonomy  
Data Failure: 데이터 누락/오류/시점 오류.  
Model Failure: QGV 판단 구조의 실패.  
Assumption Failure: Scenario 전제 실패.  
Execution Failure: 좋은 판단이나 나쁜 체결.  
Portfolio Failure: 집중/비중/상관 문제.  
Macro Regime Failure: 환경 변화에 대한 Context 실패.  
이 분류는 개선 대상을 정확히 찾기 위한 것이며 사후 책임 회피용으로 사용하지 않는다.

16\. UI  
Company Timeline: 기업별 QGV Revision과 실제 결과.  
System Dashboard: QGV Version별 성과와 표본수.  
Scenario Calibration.  
Confidence Calibration.  
Leaderboard Cohort.  
Portfolio Decision History.  
Simulation/Forward Validation 비교.  
각 그래프에서 원 Snapshot으로 Drill-down 가능하게 한다.

17\. Auditability  
모든 Record는 생성시점, 데이터 기준시점, 버전, Source Reference를 가진다.  
삭제 대신 superseded/invalidated 상태를 사용해 감사흔적을 보존한다.  
데이터 수정은 원본과 수정본을 구분한다.

18\. Improvement Loop  
Track Record → 실패유형 분류 → Evidence 축적 → 개선안 → 새 버전 → Historical/OOS 검증 → Forward Validation.  
성과가 나빴다는 이유만으로 즉시 QGV 점수를 변경하지 않는다.  
충분한 표본과 반복 가능한 근거가 있을 때만 Methodology Change를 제안한다.

19\. Non-negotiable  
Look-ahead 금지.  
과거 판단 덮어쓰기 금지.  
실패 사례 삭제 금지.  
표본수 없는 적중률 제시 금지.  
Backtest와 Forward 결과 혼합 금지.  
Version/Methodology 변경 이력 누락 금지.  
