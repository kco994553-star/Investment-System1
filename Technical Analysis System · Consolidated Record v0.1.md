Technical Analysis System · Consolidated Record v0.1  
정리 기준: 2026-09-22  
문서 상태: 기존 대화에서 진행된 설계의 Consolidated Record(통합 정리본). 새 사양을 임의 확정하지 않음.

1\. System Position  
상위 Investment System \= QGV System(기본적 분석) \+ Technical Analysis System(기술적 분석) \+ Macro System(매크로).  
Technical Analysis는 QGV와 Macro에서 분리된 독립 핵심 엔진이며, QGV 기업평가 원점수를 임의로 수정하지 않는다.  
기본 역할은 가격·추세·모멘텀·거래량·변동성·가격구조·지지/저항을 이용해 진입, 비중조절, 위험관리, 실행 판단을 제공하는 것이다.

2\. Current Design Flow  
Market Data  
→ Chart  
→ Indicator  
→ Signal  
→ Technical State  
→ Regime  
→ QGV Fusion  
→ Future Scenario  
→ Path Probability  
→ Execution  
→ Track Record.

최근 정리된 축약 흐름:  
Market Data → Indicator → Signal → 기술상태/Regime → QGV Fusion → 미래 Scenario → 경로별 Probability → Execution → Track Record.

3\. Brokerage-style Chart  
실제 증권사 앱과 유사한 실시간 주가차트를 목표로 한다.  
사용자가 다양한 Technical Tool/Indicator를 차트에서 탐색할 수 있게 한다.  
Research Tool과 실제 Model 판단에 채택된 지표를 분리한다.  
여러 지표의 중첩 표시를 지원하는 방향으로 설계 중이다.  
차트는 단순 시각화가 아니라 Signal/State/Scenario/Execution 판단의 공통 화면 역할을 한다.

4\. Indicator Architecture  
기존 설계에서 TSV(Technical State Vector) 개념을 사용했다.  
주요 구성 후보:  
Trend  
Momentum  
Volume/Flow  
Relative Strength(RS)  
Structure  
Volatility  
Composite  
Confidence  
Regime  
Scenario.  
다양한 Research Indicator 전체와 실제 QGV 결합 판단에 사용하는 Model Indicator Set은 분리한다.  
공식 지표 목록과 최종 점수식은 아직 확정 단계가 아니다.

5\. QGV Fusion  
사용자의 핵심 요구는 “QGV와 연동해서 어떤 값을 도출한다”는 흐름을 유지하는 것이다.  
QGV는 기업의 질·성장·가치 판단을 담당한다.  
Technical은 가격상태와 실행환경을 담당한다.  
QGV 방향 판단과 Technical Price Path Probability는 동일 값으로 합쳐 숨기지 않고 별도로 보존한다.  
Fusion은 QGV 원점수를 덮어쓰는 방식이 아니라 상위 Investment System에서 결합 판단을 생성하는 방식으로 설계한다.

6\. Future Scenario Paths  
초기에는 5개 경로 샘플을 검토했다:  
S1 Strong Bull  
S2 Trend Continuation  
S3 Consolidation  
S4 Correction → Recovery  
S5 Structural Breakdown.

이후 사용자의 제안에 따라 고정 5개가 아니라 S=1\~N의 동적 경로 생성 구조로 발전시켰다.  
따라서 위 S1\~S5는 고정 공식 분류가 아니라 설계 과정의 대표 Scenario Template/샘플로 취급한다.  
시장상태에 따라 필요한 경로 수가 달라질 수 있다.

7\. Scenario Components  
각 미래 경로는 최소한 다음 요소를 연결하는 방향으로 설계되었다:  
예상 Price Path / Range  
Trigger  
Confirmation  
Invalidation  
QGV Compatibility  
Confidence  
Historical Frequency 또는 검증된 Empirical Probability.  
ATR 기반 Price Range/Horizon 접근도 설계 과정에서 검토했다.

8\. Probability Method  
경로별 Probability는 임의 주관 확률로 고정하지 않는다.  
현재 설계 흐름:  
① Point-in-Time 유사 상태 검색  
② 당시 상태 이후 실제 Forward Path 수집  
③ 후속 경로를 Scenario/Cluster로 분류  
④ 현재 상태와 과거 상태의 Similarity Weight 적용  
⑤ 가중 Historical Frequency 산출  
⑥ 필요 시 통계/ML Model 결합  
⑦ Out-of-Sample 검증  
⑧ Brier Score / Log Loss 등을 이용한 Probability Calibration 검증  
⑨ Track Record에 예측과 실제 결과 저장.

검증 데이터가 충분하지 않은 초기 단계에서는 Probability를 확정적 수치처럼 표시하지 않는다.  
QGV 방향확률과 Price Path Probability를 별도로 관리한다.

9\. Forecast Horizon  
미래차트의 기본 검토 범위로 약 120 Trading Days가 제안되었고, 장기 확장 범위로 약 252 Trading Days를 검토했다.  
Forecast Horizon이 길어질수록 불확실성 Band를 확대한다.  
단기 경로는 Technical Signal의 설명력이 상대적으로 높고, 장기 경로는 QGV/Fundamental/Macro 영향이 커진다는 구조를 전제로 한다.  
120/252일은 현재 Consolidated Design 값이며 최종 공식 상수로 잠긴 상태는 아니다.

10\. Regime  
Technical Regime은 개별 지표 하나가 아니라 Trend/Momentum/Volatility/Structure 등의 결합 상태로 정의하는 방향이다.  
같은 Indicator Signal이라도 Regime에 따라 의미와 Historical Frequency가 달라질 수 있으므로 Probability 계산에서 상태 조건으로 사용한다.

11\. Execution  
Technical Analysis의 최종 목적 중 하나는 실제 Execution 판단이다.  
QGV가 투자대상 가치판단을 제공하더라도 Technical은 진입, 추가매수, 축소, 대기, 위험관리 시점을 별도로 평가한다.  
QGV가 좋다는 이유만으로 Technical 조건을 무시해 자동매수하지 않는다.  
Portfolio의 \-20% 하락 규칙 역시 자동매수가 아니라 Re-check Trigger라는 상위 규칙과 연결된다.

12\. Track Record Connection  
각 Signal/Regime/Scenario/Probability/Execution 판단을 당시 Snapshot으로 저장한다.  
실제 Forward Path와 비교한다.  
Scenario Frequency, Probability Calibration, Execution 결과를 누적 검증한다.  
과거 결과를 이용해 당시 예측을 덮어쓰지 않는다.

13\. Relationship with Macro  
Macro는 Technical 원점수를 임의 변경하는 엔진이 아니다.  
상위 Investment System에서 시장환경/거시국면 Context를 제공한다.  
장기 Forecast Horizon으로 갈수록 Macro Context의 중요도가 커지는 구조를 검토한다.

14\. UI Direction  
실시간 Brokerage-style Chart.  
Indicator Overlay.  
Research Indicator 선택.  
Model Indicator 표시.  
Technical State / Regime.  
QGV Fusion 결과.  
Future Path S=1\~N.  
각 Path Probability/Confidence.  
Trigger / Confirmation / Invalidation.  
Execution 상태.  
Track Record 접근.  
정확한 UI 컴포넌트와 데이터 계약은 별도 Specification에서 확정할 필요가 있다.

15\. Confirmed vs In-Progress  
확정/강한 방향:  
\- QGV와 연동하되 QGV 원점수는 임의 수정하지 않음.  
\- 증권사 앱형 실시간 차트.  
\- Research Tool과 Model Indicator 분리.  
\- Future Path를 표시.  
\- 경로 수는 고정 5개가 아니라 S=1\~N 동적 구조.  
\- 경로별 Probability를 측정.  
\- Probability는 Historical/PIT/OOS/Calibration 근거를 가져야 함.  
\- Track Record와 연결.

진행 중/미확정:  
\- 공식 Indicator Set.  
\- TSV 최종 수식/가중치.  
\- Regime 공식 분류 알고리즘.  
\- S=1\~N 생성 알고리즘.  
\- Similarity 함수와 Probability 결합식.  
\- Forecast Horizon 120/252일의 공식 고정 여부.  
\- Technical-QGV Fusion 최종 출력값 이름/수식.  
\- 실시간 Market Data Provider/API.  
\- 최종 Frontend Data Contract.

16\. Archival Rule  
이 문서는 다른 기술적 분석 대화에서 진행된 내용을 파일화한 정리본이다.  
미확정 항목을 공식 사양으로 승격시키지 않는다.  
향후 원 대화에서 항목이 확정되면 해당 결정만 반영해 새 Version으로 갱신한다.  
