QGV Leaderboard · Specification v1.0

Purpose  
QGV System의 시장 탐색·상대비교 모듈. 넓은 기업 Universe를 동일한 QGV 기준과 데이터 시점으로 비교하고, QGV Analysis·Portfolio·Simulation으로 진입하는 탐색 허브 역할을 한다.

1\. Initial Universe  
초기 후보는 미국 시가총액 상위 500개 기업 또는 S\&P 500 구성기업이다.  
Universe 정의, 구성일, 데이터 기준일을 Snapshot으로 저장한다.  
향후 미국 전체시장, 한국시장 및 사용자 정의 Universe로 확장할 수 있도록 Universe ID를 분리한다.

2\. Daily Update  
기본 갱신주기는 일일.  
가격 데이터와 QGV 데이터의 기준시점이 다르면 각각의 Data Stamp를 별도로 표시한다.  
실시간/지연/전일종가 여부를 명확히 구분한다.

3\. Required Columns  
Ticker.  
Market Cap.  
QGV Value.  
Price \+ Daily Return.  
Consensus Average Target Price.  
QGV Negative Scenario Target.  
QGV Neutral Scenario Target.  
QGV Positive Scenario Target.

4\. Extended Columns  
Company Name.  
Market Cap Rank.  
Sector / Industry.  
Company Types.  
Q/G/V Subscores.  
Type-adjusted QGV.  
Confidence.  
Data Freshness.  
Safety Margin.  
Next Earnings status and D-day.  
Key Risk Flag.  
Last QGV Revision.

5\. Ranking Policy  
Ticker 자체는 순위를 매기지 않는다.  
수치형 항목은 사용자가 해당 컬럼 기준으로 정렬할 수 있다.  
QGV 원점수와 Type-adjusted QGV를 구분한다.  
서로 다른 데이터 시점의 기업을 비교할 때 Freshness Warning을 표시한다.  
결측치를 0으로 간주해 순위를 왜곡하지 않는다.

6\. QGV Integration  
Leaderboard의 QGV 값은 QGV Analysis의 동일 Snapshot을 참조한다.  
Leaderboard가 별도의 독립 QGV 계산식을 갖지 않는다.  
Ticker 클릭 시 해당 기업 QGV Analysis 화면으로 이동한다.  
QGV Revision 발생 시 Leaderboard의 reference가 새 Snapshot을 가리키되 이전 Snapshot은 Track Record에 남긴다.

7\. Scenario Columns  
Negative / Neutral / Positive 값은 QGV Analysis의 조건부 Scenario를 사용한다.  
목표가만 보여주지 않고 상세화면에서 Scenario assumptions, validity period, Confidence로 연결한다.  
Consensus Target과 QGV Scenario는 서로 다른 출처/방법론임을 구분한다.

8\. Consensus  
주요 증권사/데이터 공급자의 최신 Consensus를 집계한다.  
평균 목표가, 관측치 수, 기준일, 최근 변화 여부를 저장한다.  
공급자별 원자료가 없으면 평균값의 정밀도를 과장하지 않는다.

9\. Search and Filters  
Company/Ticker 검색.  
Sector/Industry.  
Company Type.  
QGV Range.  
Q/G/V Range.  
Confidence.  
Market Cap Rank.  
Safety Margin.  
Freshness.  
Earnings proximity.  
사용자는 복수 필터를 조합할 수 있다.

10\. Personalization  
기본 QGV Leaderboard와 개인화 QGV Leaderboard를 분리한다.  
개인화는 사용자가 선택한 Q/G/V 및 세부항목 가중치를 적용한다.  
개인화 결과는 기본 QGV 원점수를 덮어쓰지 않는다.  
사용한 Weight Profile을 Snapshot으로 저장한다.

11\. Top30 Connection  
QGV Simulation의 ‘기본 QGV Top30’과 ‘개인화 QGV Top30’은 Leaderboard Snapshot을 참조한다.  
Simulation 시작 시 사용된 Top30 목록과 순위를 잠가 재현성을 보장한다.

12\. Portfolio Connection  
Leaderboard에서 기업을 Portfolio 후보로 추가할 수 있다.  
추가 전 현재 산업/유형 집중도, 기존 보유와의 중복, QGV/Confidence/Valuation 정보를 보여준다.  
Leaderboard 순위만으로 자동 편입하지 않는다.

13\. Track Record  
일별 Leaderboard Snapshot 또는 변경 이벤트를 저장한다.  
기업별 순위 변화, QGV Revision, Consensus 변화, 실제 이후 성과를 Track Record와 연결한다.  
향후 ‘높은 QGV 순위가 실제 초과성과로 이어졌는가’를 검증할 수 있어야 한다.

14\. UI  
상단: Universe, Data Date, QGV Version, Weight Profile, Freshness Summary.  
중앙: 정렬/필터 가능한 Leaderboard Table.  
Ticker 클릭 → QGV Analysis.  
Portfolio action → QGV Portfolio.  
Backtest action → QGV Simulation.  
각 수치의 Data Stamp를 빠르게 확인할 수 있어야 한다.

15\. Data Quality  
Missing, stale, estimated, conflicting source 상태를 구분한다.  
Freshness가 임계치를 넘으면 Warning.  
기업행 전체를 최신처럼 보이게 하지 않고 데이터 필드별 시점을 유지한다.  
Corporate Action, ticker change, delisting, merger 등 식별자 변경을 추적한다.

16\. API/Data Contract  
Leaderboard Row는 company\_id를 canonical key로 사용하고 ticker는 표시/검색 key로 사용한다.  
QGV Snapshot ID, Price Snapshot ID, Consensus Snapshot ID, Scenario Snapshot ID를 참조한다.  
이를 통해 서로 다른 시점 데이터가 조용히 섞이는 것을 방지한다.

17\. Non-negotiable  
동일 QGV 정의 없이 기업간 점수를 비교하지 않는다.  
결측값을 임의값으로 대체해 순위를 만들지 않는다.  
Consensus와 QGV Scenario를 동일한 예측으로 취급하지 않는다.  
과거 Leaderboard 검증에서 당시 존재하지 않았던 데이터 사용을 금지한다.  
18\. Company Reassessment Trigger · Design Freeze Update  
Leaderboard Row에 기업별 변동성 기반 재평가 상태를 authoritative field로 포함한다.  
재평가 상태는 NORMAL / WATCH / NEAR\_TRIGGER / REASSESS / INSUFFICIENT\_DATA를 사용한다.  
Trigger 기간은 1D / 5D / 20D / DRAWDOWN이다.  
각 Trigger는 observed\_change, system\_dynamic\_threshold, user\_override, validated\_candidate, effective\_threshold, distance, state를 보존한다.  
User Override가 있으면 Effective Threshold에 우선 적용한다. 예: NVDA Drawdown \-20%. 이는 매수·매도 신호가 아니라 QGV Fundamental 재검토 Trigger이다.  
Validated Candidate는 TRAIN/HOLDOUT 검증을 통과해도 자동으로 공식 기준으로 승격하지 않는다.  
REASSESS 발생은 QGV 점수를 자동 변경하지 않으며 automatic\_qgv\_change=false, execution\_authorized=false를 유지한다.

19\. VMR / Regime / Dynamic Threshold  
Full VMR은 1D/5D/20D return, 20D/60D/1Y realized volatility, Daily sigma, ATR(14)%, Beta, Volatility Percentile, Drawdown을 포함한다.  
Company / Industry / Market VMR을 분리하고 Market-adjusted 및 Industry-adjusted abnormal move를 계산한다.  
시장 변동성 국면은 LOW\_VOL / NORMAL\_VOL / HIGH\_VOL / STRESS로 분리한다.  
Regime별 Threshold는 별도 TRAIN/HOLDOUT 검증을 수행하며 표본 부족 시 VALIDATION\_INSUFFICIENT로 남긴다.  
Threshold 출처는 SYSTEM\_DYNAMIC / USER\_OVERRIDE / VALIDATED\_CANDIDATE를 구분하고 실제 적용값의 출처를 기록한다.

20\. Trigger Track Record / Calibration  
REASSESS Event에는 security\_id, company\_id, trigger type, threshold, observed change, triggered\_at, QGV before/after, cause classification을 동결한다.  
사후 관찰은 D+5 / D+20 / 63D / 252D를 사용한다.  
Calibration의 목적은 가격 예측이나 매수 타이밍 최적화가 아니라 Fundamental/QGV 재검토가 필요한 사건을 포착하는 Threshold의 유효성 검증이다.  
TRAIN에서 후보를 선택하고 이후 HOLDOUT에 동일 Threshold를 그대로 적용한다. 자동 승격은 금지한다.

21\. PIT Backtest Runner  
Portfolio Analysis → Backtest Input → Historical Market Dataset → PIT Validation → Rebalancing → Equity Curve → Benchmark 비교 구조를 사용한다.  
지원 리밸런싱은 NONE / MONTHLY / QUARTERLY / YEARLY이다.  
available\_at 기반 미래정보 차단, Corporate Action-aware 데이터 요구, 가격 누락 fail-closed, benchmark 동일 시작자금 정규화를 적용한다.  
현재 v1.0 체결 가정은 연구용 당일 종가이며 실제 체결 가능성을 의미하지 않는다. Slippage, 세금, FX, borrow cost, intraday execution은 후속 Execution Layer 범위다.

22\. Current Verification / Release Gate  
Design status: 100% · DESIGN FREEZE.  
현재 검증 기준: Python 313/313 PASS \+ 8 subtests PASS \+ Frontend 12/12 PASS \+ Standalone Build PASS.  
Browser E2E와 실제 Historical Market Data 기반 실증검증은 아직 완료되지 않았다.  
LIVE 전환 조건은 실제 데이터 연결, 기업별 Threshold 실증검증, 실제 PIT Backtest, Browser E2E, 전체 회귀검증, 문서/Schema/Frontend 일치 확인이다.

