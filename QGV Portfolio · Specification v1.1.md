QGV Portfolio · Specification v1.1

Purpose  
QGV Analysis의 기업평가를 실제 보유자산·목표비중·산업/유형 노출·리밸런싱 판단으로 변환하는 QGV System의 포트폴리오 모듈이다. 단일 QGV 점수만으로 자동매매하지 않고 가치, Confidence, 유형, 위험, 포트폴리오 목적을 함께 사용한다.

1\. Portfolio Input Modes  
A. 총 투자금액 기반 구성.  
B. 보유 주식수 \+ 평균단가 기반 구성.  
C. 기존 Portfolio Snapshot 불러오기.  
각 입력은 현금, 종목, 통화, 평가시점과 함께 Snapshot으로 저장한다.

2\. Official Baseline  
Portfolio v1.1 · 2026-09-14.  
현금 0%.  
반도체 장비 30%: ASML 9, LRCX 6, KLAC 5.5, TEL 5, 한미반도체 4.5.  
AI·반도체 25%: NVDA 8, AMD 5, AVGO 5, QCOM 4, INTC 3\.  
Big Tech 20%: MSFT 7, GOOGL 7, AMZN 6\.  
기타산업 25%: RTX 6, Stryker 5.5, Eaton 5, Hubbell 3.5, GE Vernova 3, Rockwell 2\.  
합계 100%.

3\. Holding Schema  
portfolio\_id, snapshot\_at, company\_name, ticker, market\_cap\_rank, shares, average\_cost, current\_price, currency, fx\_rate, market\_value, invested\_cost, unrealized\_pnl, actual\_weight, target\_weight, weight\_gap, sector, industry, company\_types, qgv\_version, qgv\_score, type\_adjusted\_qgv, confidence, valuation\_range, margin\_of\_safety, risk\_flags.

4\. QGV Connection  
QGV Analysis에서 원 QGV, 유형조정 QGV, Q/G/V, Confidence, Key Drivers, 적정가치/시나리오, 안전마진, 주요 Risk를 받는다.  
Portfolio는 원 QGV와 유형조정 QGV를 모두 보존한다.  
점수 변화만으로 즉시 목표비중을 변경하지 않고 Evidence와 Portfolio Constraint를 함께 확인한다.

5\. Allocation Engine  
목표비중은 QGV, Confidence, Valuation, 기업유형, 산업집중도, 상관/위험, 포트폴리오 목적을 입력으로 사용한다.  
Hard Constraint와 Soft Preference를 분리한다.  
Hard Constraint 위반은 구성 단계에서 차단 또는 경고한다.  
Soft Preference는 제안 비중에만 반영한다.  
모든 비중 합계는 100%로 검증한다.

6\. Actual vs Target  
현재가와 환율을 이용해 실제 평가액과 실제비중을 계산한다.  
Weight Gap \= Actual Weight \- Target Weight.  
괴리는 금액과 %p를 함께 표시한다.  
리밸런싱 필요 여부는 단순 0% 괴리가 아니라 설정된 Band와 거래비용을 고려한다.

7\. Portfolio Purpose  
포트폴리오 목적을 장기 성장, Quality, 방어, 경기민감, 배당 등 복수 Objective로 표현할 수 있다.  
각 기업이 어떤 목적에 기여하는지 Contribution을 표시한다.  
기업을 단순 보유목록이 아니라 ‘왜 이 포트폴리오에 존재하는가’로 설명한다.

8\. Industry Exposure  
산업별 실제/목표 비중과 변화를 표시한다.  
분기마다 산업 도넛 차트를 제공한다.  
장비 우선·수요사 후순위 같은 Portfolio Policy는 명시적 정책으로 보존한다.

9\. Type Exposure  
Growth, Value, Dividend, Quality, Cyclical, Defensive, Leader, Theme 등 중복 유형을 허용한다.  
분기마다 유형 구성 텍스트와 유형 도넛을 제공한다.  
중복 유형은 별도 Overlap Chart로 표시하며 단순 합계가 100%를 넘을 수 있음을 명확히 한다.

10\. Risk View  
기업별 변동성, Beta, ATR, Concentration, Correlation 및 QGV Risk Flags를 연결한다.  
\-20% 하락은 자동매수가 아니라 Re-check Trigger로 처리한다.  
가격 하락 원인을 구조적/일시적 악재와 시장·산업 요인으로 구분해 재검토한다.

11\. Rebalancing  
고정/월/분기/연 또는 사용자 정의 Review를 지원한다.  
Trigger: Weight Band 이탈, Fundamental Revision, Valuation 변화, Risk Limit, 목적 변화.  
매매 전 예상 거래비용, 세금, 환율 영향을 표시한다.  
Technical Analysis System 연결 후 Execution Timing은 별도 레이어에서 결정한다.

12\. Scenario Exposure  
각 기업의 Negative/Neutral/Positive QGV Scenario를 포트폴리오 수준으로 집계한다.  
시나리오별 Portfolio Value Range와 주요 기여/손실 기업을 보여준다.  
단순 목표가 합산이 아니라 각 기업 비중과 Scenario 조건을 반영한다.

13\. Portfolio Health  
핵심 화면: 구성, 목표/실제 괴리, 산업 집중, 유형 중복, QGV 분포, Confidence 분포, Valuation/Safety Margin, Risk, Scenario Exposure.  
상태는 원인과 함께 표시하고 단순 색상 하나로 전체 포트폴리오를 평가하지 않는다.

14\. Quarterly Snapshot  
분기마다 모든 종목, 주식수, 평균단가, 실제/목표비중, QGV Snapshot, 산업, 유형을 보존한다.  
산업 도넛, 유형 도넛, 유형 중복 차트를 Snapshot에 연결한다.  
과거 Snapshot은 덮어쓰지 않는다.

15\. Simulation Connection  
Portfolio Snapshot은 QGV Simulation의 입력으로 사용한다.  
Historical Simulation에서는 해당 시점의 Portfolio/QGV Snapshot만 사용한다.  
Simulation 결과를 현재 Portfolio 규칙에 소급 적용하지 않는다.

16\. Track Record  
목표비중 변경, 리밸런싱, 신규편입/제외의 이유와 당시 QGV/가격/Confidence를 기록한다.  
이후 결과와 연결해 Allocation Decision의 성과를 평가한다.

17\. UI  
상단 Summary: 총자산, 투자원금, 평가손익, QGV 평균/분포, 주요 Risk.  
Holdings Table: 기업명(TICKER)\#시가순위, 수량, 평단, 현재가, 평가액, 실제/목표비중, 괴리, QGV, Confidence.  
Views: 산업 / 유형 / 중복유형 / Valuation / Risk / Scenario / Rebalancing History.  
Ticker 클릭 시 QGV Analysis로 이동한다.

18\. Output Rule  
‘포트폴리오:’ 보고서 처음과 마지막에 Portfolio 버전 / QGV 버전 / 기간을 표시한다.  
모든 종목을 실제 이름과 티커로 공개한다.  
외화는 원화 환산값을 함께 표시한다.  
추산값은 실제 데이터와 구분한다.

19\. Versioning  
구성 변경은 Portfolio Patch로 기록한다.  
Patch에는 변경 전/후 비중, 이유, 적용일, 관련 QGV/리스크 근거를 남긴다.  
공식 버전 승격 전에는 기존 공식 Snapshot을 보존한다.

20\. Implementation Freeze · RC26  
Portfolio 모듈의 핵심 기능·아키텍처 설계는 완료되어 Design Freeze 상태로 전환한다.  
구현 기준선: QGV Portfolio v3.0 RC26. 전체 회귀 테스트 366/366 PASS.  
완료 범위: 1\~30종목 Builder, HOLDINGS/CAPITAL/HYBRID 입력, 기업유형/QGV/세부항목 가중치, 개인 Portfolio 분석, Investor-Implied/Backtest-Derived Policy, PIT Backtest, Portfolio News, News Event Study, 주/분기/연 TOP10, Cohort/Fairness Gate, Evidence Graph, Attribution, Alert/Change Detection, Data Provider Contract, SEC/XBRL Fundamental Input, Market Data, VMR, Valuation Context, V Input/Reconciliation, V Policy Research/Validation/Lifecycle/Handoff, V→Immutable Snapshot→Portfolio E2E Gate.  
설계 경계: QGV Analysis가 기업 수준 Q/G/V와 Immutable QGV Snapshot의 Source of Truth이다. Portfolio는 Snapshot을 read-only로 소비하며 재채점하거나 원본을 덮어쓰지 않는다.  
V 흐름: Market/Fundamental Data → V Input → validated/locked V policy → QGV Analysis V Score → Immutable Snapshot → Portfolio.  
E2E PASS는 연결·무결성 검증이며 투자모델의 실증적 유효성 검증을 의미하지 않는다.  
Cash 0%는 현재 공식 Portfolio v1.1의 상태일 뿐 시스템 전역 고정 정책이 아니다. Portfolio 엔진은 가변 현금을 지원해야 한다.

21\. Remaining Work — Validation / Data / Integration  
새로운 핵심 설계 추가보다 검증과 실제 데이터 연결을 우선한다.  
순서: Design Freeze → Q/G/V 통합 회귀검증 → 실제 Provider 연결 → 실제 데이터 기반 QGV 검증 → Portfolio 실데이터 E2E → Frontend/API 통합 → 회귀 테스트 → Forward Validation → Production Release 판단.  
실제 QGV 유효성 검증은 별도 단계이며 synthetic/mock/fixture 테스트 통과와 구분한다.  
실데이터 검증 시 PIT(Point-in-Time), Look-ahead 방지, 데이터 출처·as\_of·available\_at, Coverage, Confidence를 보존한다.

22\. Frontend Target  
Portfolio: 1\~30종목 설정, 기업유형/QGV/QGV 세부항목 가중치 조정, Portfolio 분석, 유명 투자자 Implied QGV 및 Backtest-Derived QGV Policy 비교.  
Portfolio News: 티커 / 뉴스 / 클릭 가능한 출처 / Q·G·V 추세 / 상태, Watch Next, 과거 유사 뉴스와 유의미한 시장 반응.  
Leaderboard: 주/분기/연 수익률 TOP10 Portfolio, 각 Portfolio QGV 가중치, Holdings 기준 QGV Exposure 분석. BACKTEST와 FORWARD는 분리한다.  
정보 구조: Portfolio State → QGV Exposure → Concentration/Risk → Change Detection → Evidence → Policy Fit → Historical Validation → Forward Validation.

23\. Status  
Design: 100% / FROZEN.  
Implementation baseline: RC26.  
Regression tests: 366/366 PASS.  
Next: 새로운 설계가 아니라 전체 Q/G/V 통합검증과 실데이터 Validation.  
