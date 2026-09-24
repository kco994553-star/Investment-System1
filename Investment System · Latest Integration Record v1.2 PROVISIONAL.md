Investment System · Latest Integration Record v1.2 PROVISIONAL  
기준: 2026-09-22  
문서 목적: QGV, Technical, Macro, Portfolio/Execution의 최신 통합 상태를 저장 허브에 보존한다. PROVISIONAL 항목을 공식 고정값으로 승격하지 않는다.

1\. System Boundary  
Investment System \= QGV System(Fundamental) \+ Technical Analysis \+ Macro System \+ Portfolio/Risk/Execution Integration.  
각 하위 시스템의 원본 Snapshot을 보존하고 최종 Target Weight와 Order는 상위 Investment System에서 한 번만 결정한다.

2\. QGV System  
QGV System은 QGV Analysis, Simulation, Portfolio, Leaderboard, Track Record의 5개 모듈로 관리한다.  
QGV Raw Fundamental Score와 Snapshot은 Technical/Macro가 직접 덮어쓰지 않는다.  
현재 저장 기준의 scoring baseline은 QGV Standard v1.5(균형형)이며 software development line과 분리 관리한다.

3\. Technical Analysis  
최신 확인 상태는 Technical Analysis System 설계·구조 구현 완료 및 Real PIT Validation v0.6 STRUCTURAL FREEZE다.  
QGV × Technical × Forecast × Portfolio 연결, Dynamic S1\~Sn, Probability Calibration/Fan, EFH, Execution State, Entry/Add/Wait/Risk-Reduction Zone, Invalidation, \-20% Re-check, UI/Realtime, Validation/Track Record 구조가 포함된다.  
최신 구조 검증 테스트 기록: 159/159 PASS.  
이는 실시간 데이터/실거래/Forward Validation 완료를 의미하지 않는다.

4\. Macro  
최신 확인 기준: Macro v0.1.1.  
오프라인 회귀검증 기록: 28/28 PASS.  
Macro는 QGV Raw Score를 변경하지 않고 Regime, 시장환경, 금리·유동성·경기·Risk Context를 상위 Integration에 제공한다.  
외부 API 실응답과 QGV/Technical 실제 패키지 연결은 별도 검증 대기 상태다.

5\. Integration v1.1 Flow  
QGV Snapshot  
\+ Technical Snapshot  
\+ Macro Snapshot  
→ Gate  
→ Integration  
→ Portfolio/Risk  
→ Target Weight  
→ Order  
→ Execution  
→ Track Record.

6\. v1.2 PROVISIONAL Weight Architecture  
검토 중인 구조:  
Target Weight \= Base Weight × OM × TM × MM × RM.

OM \= Opportunity Multiplier.  
TM \= Technical Multiplier.  
MM \= Macro Multiplier.  
RM \= Risk Multiplier.

이 구조는 각 시스템의 원본 판단을 보존하면서 상위 레이어에서 비중을 조정하기 위한 설계다.  
Multiplier의 정확한 수치구간은 Calibration 전 PROVISIONAL이다.

7\. PROVISIONAL Execution Policy  
현재 검토 기록:  
Deadband 약 0.50%p.  
단계진입 50% → 75% → 100%.  
Portfolio Cap 및 각 Multiplier 구간표.  
이 값들은 Calibration/실제 검증 전까지 공식 고정 정책으로 표시하지 않는다.

8\. Single Decision Boundary  
QGV는 기업의 Fundamental Quality/Growth/Valuation을 평가한다.  
Technical은 가격상태, Regime, Forecast Path, Execution Context를 평가한다.  
Macro는 시장·경기·금리·유동성 Context를 평가한다.  
Portfolio/Risk는 집중도, 상관, 변동성, 목적, 기존 보유상태를 반영한다.  
최종 Target Weight/Order는 상위 Integration Layer만 생성한다.

9\. \-20% Drawdown Policy  
\-20%는 자동매수 조건이 아니다.  
자동매도 조건으로도 고정하지 않는다.  
Re-check Trigger로 사용하며 QGV, Technical, Macro, Thesis, Risk를 다시 평가한다.

10\. Snapshot / PIT / Track Record  
모든 의사결정은 당시 사용 가능했던 데이터와 Version을 Snapshot으로 고정한다.  
PIT(Point-in-Time)를 적용해 미래정보 유입을 차단한다.  
QGV/Technical/Macro/Portfolio 판단을 결과에 맞춰 사후 수정하지 않는다.  
Historical Backtest, Out-of-Sample, Forward Validation을 분리한다.

11\. Current Validation State  
확인 완료 범위:  
Technical 최신 구조 검증 테스트 기록 159/159 PASS. 실제 PIT 실증 및 Forward Validation은 미완료.  
Macro v0.1.1 오프라인 회귀검증 28/28 PASS.  
QGV의 기존 명세·Schema·PIT 설계 문서화.

아직 완료로 표시하지 않는 범위:  
QGV 최신 실제 코드/데이터 E2E 검증.  
Technical 실시간 Market Data 연결.  
Macro 외부 API 실응답.  
세 시스템의 실제 패키지 통합 E2E.  
Brokerage 실제 Execution.  
장기간 Forward Validation.

12\. Version Governance  
QGV System software version, QGV scoring standard, Technical version, Macro version, Portfolio version, Investment System version을 분리한다.  
PROVISIONAL 정책은 검증 후에만 공식 버전으로 승격한다.  
과거 Version/Decision History는 삭제하지 않는다.

13\. Next Integration Gate  
다음 공식 통합 단계는 새로운 기능 추가가 아니라 최신 QGV/Technical/Macro 패키지의 Contract 정합성 확인이다.  
그 후 Mock/Replay E2E → 실제 데이터 E2E → Out-of-Sample → Forward Validation 순서로 검증한다.

14\. Archival Rule  
이 문서는 저장 허브용 최신 Integration Record다.  
원 개발 대화에서 더 최신 확정본이 나오면 그 내용을 우선한다.  
확정되지 않은 수치·정책을 자동으로 Official로 변경하지 않는다.  
