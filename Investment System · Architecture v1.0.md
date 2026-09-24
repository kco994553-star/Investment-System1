Investment System · Architecture v1.0

1\. System Boundary  
Investment System \= QGV System (기본적 분석) \+ Technical Analysis System (기술적 분석) \+ Macro System (매크로).

2\. QGV System  
QGV System은 다음 5개 모듈로 구성한다.  
QGV Analysis — 기업의 Quality, Growth, Valuation을 평가한다.  
QGV Simulation — Point-in-Time 원칙으로 과거·현재 모의투자와 검증을 수행한다.  
QGV Portfolio — QGV 결과를 실제 포트폴리오 구성, 비중, 유형 노출과 연결한다.  
Leaderboard — 미국 대형주 Universe를 시작으로 QGV·가격·컨센서스·시나리오를 일일 비교한다.  
Track Record — 과거 판단, 점수, 시나리오와 실제 결과를 축적해 시스템 성능을 추적한다.

3\. Technical Analysis System  
QGV 결과와 실시간/과거 가격 데이터를 연결한다. Execution(실행), Risk(위험), Technical Signal(기술 신호), Future Path Scenario(미래 경로), Path Probability(경로 확률)를 담당한다. 시나리오 수 S는 고정 5개가 아니라 데이터와 불확실성에 따라 가변적으로 운용할 수 있도록 설계한다.

4\. Macro System  
거시환경과 주식시장 환경을 기업 Fundamental Score와 분리한다. 성장, 물가, 고용, 금리, 유동성 및 시장 환경의 Signal → Evidence를 축적하고 충분한 근거가 있을 때 제한적으로 가중치와 Context를 조정한다.

5\. Integration Flow  
기업 Universe → QGV 분석 → 후보 선정 → 포트폴리오 구성 → 기술적 실행/리스크 → 매크로 Context → 통합 운용 규칙 → Backtest → Forward Validation → Track Record → 개선.

6\. Point-in-Time and Data Governance  
과거 검증에서는 당시 이용 가능했던 정보만 사용한다. 미래정보 누출을 금지한다. 핵심 데이터에는 기준기간, 발표일, 신선도, 출처를 포함하는 Data Stamp를 유지한다. 추산값은 추산임을 명시하고 방법과 오차 가능성을 기록한다.

7\. Version Governance  
QGV System과 QGV Analysis를 구분한다. QGV v1.7은 현재 소프트웨어 개발선이며, QGV Standard v1.5 균형형은 현재 기억된 공식 평가 기준선이다. 공식 포트폴리오는 포트폴리오 v1.1 · 2026-09-14를 기준으로 한다. 변경 시 버전과 변경 이유를 기록한다.

8\. Engineering Policy  
정확성·안전성 \> 사용자 요구사항 \> 기존 동작 보존 \> 단순함 \> 유지보수성 \> 성능 \> 확장성.  
최소 변경을 우선하고 실제 실행·테스트·회귀 확인 후 완료로 판단한다. API Key와 비밀정보는 문서나 코드에 직접 저장하지 않는다.  
