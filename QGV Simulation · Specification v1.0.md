QGV Simulation · Specification v1.0

Purpose  
QGV System의 평가기준과 포트폴리오 규칙이 실제 과거·현재 시장에서 어떻게 작동했는지 재현·검증한다. 목적은 수익률을 사후 최적화하는 것이 아니라 QGV의 유효성, 안정성, 재현성과 실패 조건을 측정하는 것이다.

1\. Main UI  
상단에 과거 / 현재 모드를 둔다.

2\. Historical Mode  
기간: 데이터가 실제 확보 가능한 최초 시점부터 현재까지 선택 가능하게 한다. 종목·지표별 데이터 시작일이 다르면 공통 시작일과 개별 가용범위를 표시한다.  
QGV 설정: Q/G/V 가중치와 15개 점수항목 세부 가중치를 불러오고 변경 가능하게 하되 사용한 설정을 Simulation Snapshot으로 잠근다.  
Portfolio: 기존 포트폴리오 불러오기 또는 새 구성.  
종목 수: 1\~30.  
선정 방식: 직접 선택 / 기본 QGV Top30 / 개인화 QGV Top30.  
Rebalancing: 고정 / 월 / 분기 / 연.  
추가투자 기본값: 0원.

3\. Point-in-Time Rule  
각 시점에 공개되어 있던 정보만 사용한다.  
재무 데이터는 회계기간이 아니라 실제 발표·이용 가능 시점을 기준으로 한다.  
당시 Index/Universe 구성과 당시 공개정보를 사용한다.  
미래 실적, 이후 수정된 컨센서스, 미래 편입종목 등 Look-ahead를 금지한다.  
정확한 PIT 데이터가 없으면 추산 여부, 방법, 오차를 기록한다.

4\. Universe and Availability  
초기 Universe는 미국 상위 500개 기업 또는 S\&P 500 기반 후보군을 지원한다.  
데이터 공급자별 earliest available date를 저장한다.  
Simulation 시작 가능일 \= 필요한 핵심 데이터의 가용성 조건을 충족하는 최초 날짜.  
UI에는 “최대 과거 범위”와 제한 원인을 보여준다.

5\. Portfolio Construction  
동적 비중을 지원하며 기본 예시는 종목당 3\~8% 범위다.  
총 비중은 100%.  
모든 선정 종목과 실제 비중을 표시하며 ‘기타/나머지’로 생략하지 않는다.  
기업 표기는 기업명(TICKER)\#시가순위를 지원한다.

6\. Price/Return Graph  
상대 수익률 기준으로 동일 시작값에 정규화한다.  
Series:  
개별 포트폴리오 종목  
포트폴리오 종목 평균  
포트폴리오 전체  
미국 상위 500 Universe 비교  
기업 유형별 평균  
Benchmark  
기간 확대/축소 및 Series on/off를 지원한다.

7\. Benchmarks  
S\&P 500 Total Return  
S\&P 500 Equal Weight Total Return  
Growth / Quality / Momentum 계열 중 최소 2개  
동일 시작금액 기준으로 비교한다.

8\. Performance Metrics  
기간수익률, 수익액, 종료자산, CAGR, Total Return, MDD, 변동성, Sharpe 등 핵심 지표를 계산한다.  
필요 시 YTD와 분기별 성과를 제공한다.  
Benchmark 대비 초과수익과 위험 차이를 함께 보여준다.

9\. Quarterly Report  
각 분기 실제 20종목 또는 사용자가 지정한 종목 수 전체를 공개한다.  
종목, 비중, 시작가, 종료가/수익률, QGV Snapshot을 기록한다.  
분기 포트폴리오 수익률을 표시한다.  
산업·기업유형 노출과 변화도 기록한다.

10\. Execution Band  
체결가가 해당 월 또는 정의된 실행기간의 저가\~고가 범위에서 어느 위치였는지 기록한다.  
Technical Analysis System이 연결되면 실행 품질 비교에 사용한다.

11\. Current Mode  
현재 QGV Snapshot과 현재 Portfolio를 기준으로 Forward Simulation 상태를 생성한다.  
과거 데이터를 이용한 사후 수정 없이 이후 실제 데이터를 누적한다.  
충분한 Out-of-Sample 검증 후 Forward Validation 단계로 승격한다.

12\. Experiment Snapshot  
각 실행은 Simulation ID, 생성시점, 기간, QGV 버전, QGV 가중치, 세부항목 가중치, Portfolio 버전/구성, Universe, 리밸런싱, 데이터 공급자/버전, 거래비용·세금·환율 가정을 저장한다.  
같은 Snapshot은 동일 입력 데이터에서 재현 가능해야 한다.

13\. Bias Controls  
Look-ahead Bias, Survivorship Bias, Selection Bias, Data Revision Bias를 검사한다.  
결과가 지나치게 좋은 경우 자동으로 데이터 누출과 규칙 변경 여부를 우선 점검한다.  
규칙은 테스트 구간 결과를 본 뒤 소급 변경하지 않는다.

14\. Comparison Experiments  
기본 QGV vs 개인화 QGV.  
QGV-only vs QGV \+ Technical \+ Macro.  
고정 vs 월/분기/연 리밸런싱.  
유형조정 전/후.  
비교 실험에서는 변경 변수를 최소화해 원인을 식별한다.

15\. Output Contract  
보고서 처음과 끝에 Simulation 버전 / QGV 버전 / Portfolio 버전 / 기간을 표시한다.  
시작금액, 종료금액, 기간수익률, 수익액을 명시한다.  
정확한 과거값이 없으면 값과 함께 추산 등급/방법/오차 가능성을 공개한다.

16\. Track Record Connection  
Simulation 결과는 Track Record에 실험 단위로 연결한다.  
QGV 버전별 성과, 유형별 성과, 시나리오 정확도, 실패 패턴을 누적한다.

17\. Non-negotiable  
미래정보 금지.  
종목 생략 금지.  
데이터 부족을 정밀한 숫자로 위장하지 않는다.  
성과 최적화보다 QGV 유효성 검증을 우선한다.

18\. Latest Development Status · 2026-09-22  
Implementation line: QGV\_SIM v0.6.8 pilot line. Simulation engine/regression line reached 103/103 PASS in the latest confirmed local package.  
Design status: PRE-VALIDATION FREEZE. No additional feature design is required before empirical validation.  
Real-data validation: started, but QGV empirical effectiveness is NOT VALIDATED. NVDA is the first fixed-company pilot for PIT fundamental/price reconstruction.  
Scoring dependency: Q/G/V architecture, PIT gates, missing-data handling, confidence separation, peer/persistence normalization method and validation protocol are designed. Numerical normalization parameters, type-specific Q/G/V weights and V reconciliation parameters remain CALIBRATION\_PENDING and must be estimated on TRAIN data, then frozen before VALIDATION/TEST.  
Validation order: real PIT data → TRAIN calibration → parameter freeze → VALIDATION → TEST → Historical QGV outcomes → Forward Validation.  
Fail-closed: missing required evidence remains null/BLOCKED; do not convert missing data to zero or average values. Do not tune the frozen version after observing validation/test returns.  
Historical-universe work includes stable security\_id, dated ticker aliases, security lives and explicit corporate-action settlement evidence. Ticker changes alone must not imply merger/delisting settlement terms.

