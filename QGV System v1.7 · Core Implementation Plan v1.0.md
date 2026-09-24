QGV System v1.7 · Core Implementation Plan v1.0

Purpose  
통합 명세를 실제 코드로 옮기기 위한 최소 구현(MVP Core) 기준을 고정한다. 외부 API 없이 Mock Data만으로 Analysis → Leaderboard/Portfolio → Simulation → Track Record 전체 흐름을 재현하는 것이 첫 목표다.

1\. Package Structure  
qgv\_system/  
  domain/  
    models.py  
    enums.py  
    validation.py  
  data/  
    repository.py  
    pit\_resolver.py  
    mock\_provider.py  
  qgv\_analysis/  
    scoring.py  
    snapshot.py  
  leaderboard/  
    service.py  
  portfolio/  
    service.py  
  simulation/  
    engine.py  
    metrics.py  
  track\_record/  
    service.py  
  interfaces/  
    technical.py  
    macro.py  
  tests/  
    test\_domain.py  
    test\_pit.py  
    test\_analysis.py  
    test\_portfolio.py  
    test\_simulation.py  
    test\_track\_record.py  
    test\_e2e.py

2\. Minimal Domain Models  
Company: company\_id, legal\_name, display\_name, ticker, exchange, currency.  
DataStamp: source, period, published\_at, observed\_at, freshness, estimated.  
QGVSnapshot: company\_id, as\_of, standard\_version, Q/G/V, total, attractiveness, confidence, refs.  
PriceSnapshot: company\_id, observed\_at, price, currency, market\_cap, rank.  
PortfolioHolding: company\_id, shares, average\_cost, target\_weight.  
PortfolioSnapshot: version, as\_of, holdings, total\_value.  
LeaderboardSnapshot: universe, as\_of, rows.  
SimulationConfig/Result.  
TrackRecord.

3\. Immutability  
Snapshot 모델은 생성 후 수정하지 않는다.  
변경은 새 Snapshot ID와 parent/revision reference를 만든다.  
Repository update 대신 append를 기본으로 한다.

4\. Validation  
Q/G/V와 15개 scored item의 범위 검사.  
QGV Standard v1.5 총점 최대 150\.  
Portfolio target weight 합계 100% 허용오차 검사.  
다중통화 평가 시 FX 누락 차단.  
미래 DataStamp 참조 차단.  
서로 다른 Standard의 직접 순위 비교 경고.

5\. PIT Resolver  
get\_latest\_available(company\_id, data\_type, as\_of).  
published\_at \<= as\_of 조건.  
revision이 존재하면 as\_of 당시 이용 가능했던 revision만 선택.  
데이터가 없으면 PIT\_UNAVAILABLE 반환.  
Silent fallback 금지.

6\. QGV Scoring Core  
15개 점수항목 × 10점.  
Raw score /150.  
Q/G/V aggregation은 Weight Profile로 분리.  
Attractiveness /10은 명시적 변환함수와 version을 가진다.  
Type-adjusted score는 Raw score를 덮어쓰지 않는다.

7\. Leaderboard Core  
입력: Universe Snapshot \+ QGV Snapshots \+ Price/Consensus/Scenario refs.  
출력: sortable rows.  
기본 QGV와 personalized profile을 별도 Snapshot으로 생성.  
Top30 export 시 company\_id 순서와 snapshot refs를 잠근다.

8\. Portfolio Core  
입력 A: total capital \+ target weights.  
입력 B: shares \+ average cost.  
평가: market value, invested cost, unrealized P/L, actual weight, target gap.  
산업/유형 노출 계산 인터페이스 제공.  
Rebalance는 Proposal 객체만 생성하며 주문 실행은 하지 않는다.

9\. Simulation Core  
동일 Config \+ 동일 Snapshot refs → 동일 결과를 보장한다.  
초기 버전은 단순 buy-and-hold \+ fixed/monthly/quarterly/yearly rebalance를 지원한다.  
거래비용, FX, benchmark는 명시적 input.  
Look-ahead 방지를 PIT Resolver 수준에서 테스트한다.

10\. Track Record Core  
record\_decision().  
record\_revision().  
evaluate\_outcome().  
원 판단 Snapshot reference를 보존한다.  
Historical/OOS/Forward mode를 분리한다.

11\. Technical/Macro Interfaces  
초기에는 Protocol/DTO만 정의한다.  
TechnicalResult: execution\_state, risk\_metrics, paths, probabilities.  
MacroResult: regime, market\_environment, discount\_rate\_context, confidence.  
두 인터페이스 모두 QGVSnapshot을 수정할 권한이 없다.

12\. Mock End-to-End Test  
Mock Universe 5개 기업.  
각 기업에 과거 시점별 DataStamp/QGV/Price 생성.  
Leaderboard 생성.  
Top 기업을 Portfolio에 구성.  
PIT Simulation 실행.  
Track Record에 당시 판단과 이후 outcome 기록.  
같은 입력으로 재실행해 deterministic equality 확인.

13\. Test Gates  
T1 Domain validation.  
T2 Snapshot immutability.  
T3 PIT future-data rejection.  
T4 QGV max/min and weighted calculation.  
T5 Portfolio weight/value calculations.  
T6 Leaderboard snapshot lock.  
T7 Simulation deterministic rerun.  
T8 Track Record revision preservation.  
T9 End-to-End reference integrity.

14\. Definition of Done — Core Alpha  
모든 T1\~T9 통과.  
Mock E2E 실행 성공.  
외부 API 의존성 0\.  
Secret 0\.  
QGV Standard v1.5 baseline 표현 가능.  
Portfolio v1.1 구조 입력 가능.  
PIT violation이 테스트에서 차단됨.  
동일 Snapshot 재실행 결과 동일.

15\. Next Implementation Step  
첫 코드 묶음은 domain/models.py \+ enums.py \+ validation.py \+ repository.py \+ pit\_resolver.py로 제한한다.  
이 기반 테스트 통과 후 scoring/portfolio/leaderboard로 확장한다.  
과잉 추상화, 데이터베이스, 웹 프레임워크, 외부 API는 Core Alpha에서 도입하지 않는다.  
