Technical Analysis · Decision History v0.1  
정리 기준: 2026-09-22  
상태: 기존 설계 대화의 결정 기록. 새로운 사양을 임의 확정하지 않음.

1\. 초기 방향  
Technical Analysis는 Investment System의 독립 레이어로 설계한다.  
QGV와 연동하며 증권사 앱형 실시간 가격차트와 다양한 Technical Tool을 목표로 한다.

2\. QGV 경계  
QGV Fundamental 판단과 Technical 가격·실행 판단을 분리한다.  
Technical 결과가 QGV 원점수를 직접 덮어쓰지 않는다.  
결합 판단은 상위 Investment System에서 생성한다.  
상태: 확정 방향.

3\. Indicator 구조  
Research Indicator와 실제 Model Indicator Set을 분리한다.  
TSV 개념으로 Trend, Momentum, Volume/Flow, Relative Strength, Structure, Volatility, Composite, Confidence, Regime, Scenario 등을 묶는 설계를 진행했다.  
상태: 구조 방향 확정, 최종 목록·수식 미확정.

4\. Future Path  
현재 Signal뿐 아니라 미래 예상경로를 표시하는 구조로 확장했다.  
경로에는 가격범위, Trigger, Confirmation, Invalidation, Confidence/Probability를 연결한다.  
상태: 기능 방향 확정.

5\. Five-Scenario Prototype  
설명용 Prototype으로 S1 Strong Bull, S2 Trend Continuation, S3 Consolidation, S4 Correction → Recovery, S5 Structural Breakdown을 사용했다.  
상태: 예시이며 공식 고정 분류가 아님.

6\. S=1\~N  
고정 5개 대신 시장상태에 따라 Scenario 개수가 달라지는 동적 S=1\~N 구조로 발전시켰다.  
상태: 방향 확정, 생성 알고리즘 미확정.

7\. Probability  
각 Future Path에 Probability를 부여한다.  
주관적 숫자가 아니라 측정·검증 가능한 확률을 목표로 한다.  
현재 방법론 방향은 PIT 상태 정의 → 유사 과거상태 → Forward Path → Scenario/Cluster → Similarity Weight → Historical Frequency → 필요 시 통계/ML → OOS → Calibration → Track Record이다.  
Brier Score, Log Loss, Calibration Curve, 표본수, Regime별 성능을 평가 후보로 둔다.  
상태: 방법론 방향 확정, 최종 모델 미확정.

8\. Forecast Horizon  
약 120 Trading Days를 기본 검토 범위, 약 252 Trading Days를 장기 확장 범위로 논의했다.  
기간이 길어질수록 Uncertainty Band를 확대하고 QGV/Macro Context 중요도가 커지는 구조를 검토했다.  
상태: 설계안, 공식 기간 미확정.

9\. Regime  
동일 Signal도 시장상태에 따라 의미가 달라질 수 있어 Technical Regime을 별도 상태로 관리한다.  
상태: 방향 확정, 분류 알고리즘 미확정.

10\. Execution  
Technical Analysis는 진입, 추가매수, 축소, 대기, 위험관리 판단과 연결한다.  
Fundamental이 좋다는 이유만으로 자동 실행하지 않는다.  
상태: 방향 확정.

11\. Track Record  
Technical State, Regime, Scenario, Probability, Execution 판단을 당시 Snapshot으로 보존하고 실제 Forward Path와 비교한다.  
과거 예측을 결과에 맞춰 덮어쓰지 않는다.  
상태: 방향 확정.

12\. Unresolved Register  
U-01 공식 Model Indicator Set.  
U-02 Indicator 계산 파라미터.  
U-03 TSV 최종 Schema/가중치.  
U-04 Regime 분류 규칙.  
U-05 S=1\~N 생성/병합/제거 규칙.  
U-06 Path Similarity 함수.  
U-07 Probability Model/Calibration threshold.  
U-08 Forecast Horizon 공식 기본값.  
U-09 QGV-Technical Fusion 최종 출력 Schema/명칭.  
U-10 Real-time Market Data Provider.  
U-11 Chart Frontend Library/Data Contract.  
U-12 Execution Signal과 Portfolio Rebalancing의 정확한 경계.

13\. Version Rule  
원 설계 대화에서 확정된 결정만 Confirmed로 승격한다.  
새 아이디어는 Proposed/In Progress 상태로 남긴다.  
Specification이 업데이트되어도 과거 Decision History는 삭제하지 않는다.  
