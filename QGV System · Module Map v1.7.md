QGV System · Module Map v1.7

Purpose  
QGV System v1.7 개발선에서 5개 모듈의 책임과 데이터 흐름을 고정한다.

01 QGV Analysis  
Input: 기업 식별자, 재무·시장·산업·컨센서스·가격·뉴스 데이터.  
Core: Q/G/V 평가, Data Stamp, Confidence, Key Drivers, Peer Weight, Track Record 연결.  
Output: 원점수, 유형조정 점수, 매수매력도, 부정/중립/긍정 시나리오, 근거 및 불확실성.  
Rule: 빠르게 변하는 뉴스와 거시 신호가 안정적 Fundamental Score를 임의로 흔들지 않도록 분리한다.

02 QGV Simulation  
Modes: 과거 / 현재.  
Historical mode: 기간, QGV 가중치·세부항목 가중치, 포트폴리오, 종목수 1\~30, 직접선택/QGV Top30/개인화 Top30, 리밸런싱 주기를 입력한다.  
Validation: Point-in-Time, 미래정보 금지, Benchmark 비교, Execution Band, CAGR/MDD/TR 등.  
Output: 포트폴리오 및 종목별 성과, 유형별 비교, 시장 대비 결과, 오차·추산 기록.

03 QGV Portfolio  
Input modes: 총 투자금액 또는 보유 주식수 \+ 평균단가.  
Core: 목표비중, 실제비중, 괴리, 산업·기업유형 노출, QGV 연결, 리밸런싱 후보.  
Official baseline: 포트폴리오 v1.1 · 2026-09-14.  
Quarterly visualization: 산업 도넛, 유형 도넛, 중복 유형 노출.

04 Leaderboard  
Initial Universe: 미국 시가총액 상위 500개 또는 S\&P 500 후보군에서 시작해 확장.  
Daily columns: 티커, 시가총액, QGV값, 주가 및 전일대비 수익률, 컨센서스 평균 목표가, QGV 부정·중립·긍정 시나리오 목표가.  
Purpose: 기업 검색·분석 진입점과 시장 전체 상대 비교를 연결한다.

05 Track Record  
Stores: 평가 시점의 Q/G/V, Confidence, Key Drivers, 시나리오, 목표범위, 실제 이후 성과, 데이터 버전.  
Purpose: QGV 판단이 시간에 따라 얼마나 재현되고 맞았는지 측정하며 모델 개선 근거를 제공한다.

Cross-module Flow  
Leaderboard/검색 → QGV Analysis → Portfolio → Simulation → Track Record.  
Technical Analysis와 Macro는 QGV System 밖의 상위 Investment System 레이어에서 결합한다.

Version Rule  
QGV System 버전과 QGV Analysis 평가표준 버전을 별도로 기록한다. 모듈 간 Schema 변경은 영향 범위와 마이그레이션 필요성을 먼저 확인한다.  
