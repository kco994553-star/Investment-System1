QGV System · Common Schema & API Contract v1.0

Purpose  
QGV Analysis, Simulation, Portfolio, Leaderboard, Track Record가 동일한 기업·시점·버전·데이터 출처를 공유하도록 공통 식별자, Snapshot, API 경계와 검증 규칙을 정의한다.

1\. Canonical IDs  
company\_id: 기업의 영구 내부 식별자. ticker 변경과 무관하다.  
qgv\_snapshot\_id: 특정 분석시점의 QGV 결과.  
price\_snapshot\_id: 가격 관측값과 시장시점.  
consensus\_snapshot\_id: 컨센서스 관측값.  
scenario\_snapshot\_id: QGV 시나리오 세트.  
portfolio\_snapshot\_id: 포트폴리오 구성/평가 상태.  
leaderboard\_snapshot\_id: Universe와 순위 상태.  
simulation\_id: 하나의 재현 가능한 실험.  
track\_record\_id: 판단/결과 연결 기록.  
data\_stamp\_id: 출처·기준기간·발표일·신선도.

2\. Company Entity  
company\_id, legal\_name, display\_name, ticker, exchange, currency, country, sector, industry, active\_from, active\_to, identifier\_history.  
ticker는 표시/검색용이며 관계형 연결의 기준키로 사용하지 않는다.

3\. Data Stamp  
data\_stamp\_id, source\_provider, source\_type, source\_reference, period\_start, period\_end, published\_at, observed\_at, market\_time\_status, freshness\_status, estimated, estimation\_method, quality\_flags.  
Freshness: GREEN / YELLOW / RED.  
estimated=true이면 estimation\_method가 필수다.

4\. QGV Snapshot  
qgv\_snapshot\_id, company\_id, analyzed\_at, qgv\_system\_version, qgv\_standard\_version, profile\_id, Q\_score, G\_score, V\_score, total\_score, attractiveness\_10, type\_adjusted\_score\_100, confidence, key\_drivers, peer\_set\_id, valuation\_snapshot\_id, scenario\_snapshot\_id, data\_stamp\_refs, revision\_parent\_id.  
Snapshot은 immutable을 기본으로 하며 변경은 새 ID로 만든다.

5\. Price Snapshot  
price\_snapshot\_id, company\_id, observed\_at, session\_status, price, currency, daily\_return, market\_cap, market\_cap\_rank, fx\_rate\_to\_krw, data\_stamp\_id.  
장중/종가/지연 데이터 상태를 구분한다.

6\. Consensus Snapshot  
consensus\_snapshot\_id, company\_id, observed\_at, analyst\_count, average\_target, median\_target, high\_target, low\_target, currency, revision\_direction, source\_refs.  
QGV Scenario와 독립적으로 유지한다.

7\. Scenario Snapshot  
scenario\_snapshot\_id, qgv\_snapshot\_id, valid\_from, valid\_until.  
각 scenario: name(Negative/Neutral/Positive), assumptions, drivers, value\_low, value\_high, target\_price, confidence, trigger\_conditions.  
Scenario는 조건부 결과이며 단일 확정예측으로 취급하지 않는다.

8\. Portfolio Snapshot  
portfolio\_snapshot\_id, portfolio\_version, snapshot\_at, base\_currency, total\_cost, total\_market\_value, cash\_weight, qgv\_version\_ref, policy\_version.  
holding: company\_id, shares, average\_cost, actual\_weight, target\_weight, weight\_gap, qgv\_snapshot\_id, price\_snapshot\_id, role\_tags, risk\_flags.  
과거 Snapshot은 수정하지 않는다.

9\. Leaderboard Snapshot  
leaderboard\_snapshot\_id, universe\_id, universe\_as\_of, generated\_at, qgv\_version, profile\_id.  
row: company\_id, qgv\_snapshot\_id, price\_snapshot\_id, consensus\_snapshot\_id, scenario\_snapshot\_id, rank\_fields, freshness\_summary.  
Top30 사용 시 leaderboard\_snapshot\_id와 당시 company\_id 목록을 Simulation에 고정한다.

10\. Simulation Snapshot  
simulation\_id, created\_at, mode(HISTORICAL/CURRENT/FORWARD), start\_date, end\_date, initial\_capital, qgv\_version, qgv\_weight\_profile\_id, portfolio\_snapshot\_id, universe\_snapshot\_id, leaderboard\_snapshot\_id, rebalance\_rule, benchmark\_ids, transaction\_cost\_assumptions, tax\_assumptions, fx\_assumptions, data\_provider\_versions, pit\_policy\_version.  
결과: ending\_value, total\_return, CAGR, MDD, volatility, benchmark\_relative\_metrics, quarterly\_records, execution\_band\_records.

11\. Track Record  
track\_record\_id, record\_type, subject\_id, decision\_at, source\_snapshot\_refs, outcome\_window, outcome\_metrics, benchmark\_metrics, evaluation\_status, failure\_taxonomy, notes.  
source\_snapshot\_refs를 통해 당시 판단을 재구성할 수 있어야 한다.

12\. Version Objects  
qgv\_system\_version: 모듈/Schema/연결 구조 버전.  
qgv\_standard\_version: QGV 평가/점수 기준 버전.  
portfolio\_version: 공식 구성 정책 버전.  
technical\_version: 기술적 분석 버전.  
macro\_version: 매크로 버전.  
investment\_system\_version: 상위 통합 버전.  
서로 다른 버전 개념을 하나의 version 문자열로 합치지 않는다.

13\. API Boundaries  
Analysis API  
get\_company\_analysis(company\_id, as\_of, profile\_id) → qgv\_snapshot\_id.

Leaderboard API  
get\_leaderboard(universe\_id, as\_of, profile\_id, filters, sort) → leaderboard\_snapshot\_id \+ rows.

Portfolio API  
build\_portfolio(input\_mode, holdings\_or\_capital, policy, qgv\_refs) → portfolio\_snapshot\_id.  
evaluate\_portfolio(portfolio\_snapshot\_id, as\_of) → current valuation/exposure view.  
propose\_rebalance(portfolio\_snapshot\_id, constraints) → proposal only; execution is separate.

Simulation API  
run\_simulation(config\_snapshot) → simulation\_id.  
Simulation은 PIT resolver를 통하지 않은 미래 데이터를 읽을 수 없다.

Track Record API  
record\_decision(snapshot\_refs, decision\_metadata) → track\_record\_id.  
evaluate\_outcome(track\_record\_id, outcome\_window) → outcome record.

14\. Point-in-Time Resolver  
resolve(data\_type, company\_id, as\_of) 함수는 published\_at/available\_at \<= as\_of 조건을 만족하는 데이터만 반환한다.  
수정 재무제표나 최신 컨센서스가 과거 테스트로 역류하지 않도록 revision-aware lookup을 사용한다.  
Universe도 as\_of 기준 Snapshot을 사용한다.

15\. Validation Rules  
모든 관계 ID는 존재해야 한다.  
Snapshot의 analyzed\_at/generated\_at보다 미래의 Data Stamp를 참조할 수 없다.  
비중 합계는 허용 오차 내 100%.  
통화가 다르면 FX reference 필수.  
estimated 데이터는 표시와 방법론 필수.  
QGV Standard가 다른 점수의 직접 Ranking 비교는 경고 또는 차단한다.  
Backtest 결과와 Forward 결과는 동일 series로 합치지 않는다.

16\. Error/Quality States  
MISSING\_DATA  
STALE\_DATA  
ESTIMATED\_DATA  
CONFLICTING\_SOURCE  
PIT\_UNAVAILABLE  
VERSION\_MISMATCH  
IDENTIFIER\_CHANGED  
CALCULATION\_ERROR  
각 상태는 숨기지 않고 UI와 로그에 전달한다.

17\. Provenance  
계산 결과는 input\_snapshot\_refs, calculation\_version, generated\_at을 가진다.  
원 데이터 → 계산 → QGV → Portfolio/Leaderboard → Simulation/Track Record 경로를 역추적 가능하게 한다.

18\. Security  
API Key/Secret은 Snapshot, 문서, 코드 저장소에 직접 저장하지 않는다.  
환경변수 또는 Secret Manager를 사용한다.  
사용자 계정 식별정보와 투자 연구 데이터는 최소권한 원칙으로 분리한다.

19\. Migration Policy  
Schema 변경은 additive change를 우선한다.  
필드 삭제/의미 변경은 Major migration으로 취급한다.  
Migration 전후의 Snapshot 해석이 달라지면 기존 기록을 변환해 덮어쓰지 않고 schema\_version을 유지한다.

20\. Integration Contract  
Leaderboard/검색 → Analysis → Portfolio → Simulation → Track Record.  
Technical Analysis와 Macro는 QGV System 외부의 Investment System 레이어에서 명시적 interface를 통해 결합한다.  
QGV Fundamental Snapshot은 외부 레이어가 직접 수정하지 않는다.  
