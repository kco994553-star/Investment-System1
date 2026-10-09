# 전체 차트·시각화 요구 목록 v0.2

기준: canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`, 기존 통합시험 `acaf1b5a82859ac2750a130ebe88f8b4d272ac66`, chart owner PR41. 최신 PR 변경은 별도 note이며 canonical 구현으로 계산하지 않는다.

**핵심81 + 추가 Spec24 + Macro Candidate8 + Cockpit IA 신규8 = 121개 요구 항목(기존113 + 실제 신규8). 독립 차트121개라는 뜻은 아니다.** 원래 핵심81개 완료율 분모는 유지한다. J7은 이번에 추가 식별한 요구이며 전체 구현 계층을 새로 감사한 결과가 아니다. K8은 후보 설계이고 확정 기본정책이 아니다. Cockpit IA v1의 9개 후보 중 L08은 기존 K01에 연결하며 신규 ID/행으로 계산하지 않는다.

Canonical/PR40의 L1–L5 판정은 `chart_inventory.json`에 보존했다. R=감사 범위 ready, I=입력 의존, P=부분, S=설계/구현미발견, H=placeholder, U=미재감사. 최신 DEMO/REFERENCE 검증은 실데이터 운영 완료와 별개이다.

## 공통 요구

- 실제값/합성/참고자료 구분
- source·as_of·observed_at·available_at·vintage
- 가격조정기준·기업행사·통화·timezone/session
- PIT/no-lookahead·분기snapshot 보존
- 결측≠0·목표≠실제·확률≠Confidence
- Research/Model·BACKTEST/FORWARD·canonical/PR 구분
- 모바일·축/단위·툴팁/범위·빈/차단상태 검증

## A. 시장 가격 차트 (9)

- **A01 Candlestick / OHLC** — NON_CANONICAL_DEMO_VERIFIED. PR41: 합성 일봉 캔들·거래량/범위/교차선·값 조회 검증. 실제 NVDA5일 원본 사전검사 통과. intraday·세션·PIT·운영 연결은 미완료.
- **A02 Volume** — NON_CANONICAL_DEMO_VERIFIED. PR41: 합성 일봉 캔들·거래량/범위/교차선·값 조회 검증. 실제 NVDA5일 원본 사전검사 통과. intraday·세션·PIT·운영 연결은 미완료.
- **A03 Timeframe / range** — NON_CANONICAL_DEMO_VERIFIED. PR41: 합성 일봉 캔들·거래량/범위/교차선·값 조회 검증. 실제 NVDA5일 원본 사전검사 통과. intraday·세션·PIT·운영 연결은 미완료.
- **A04 Adjusted / unadjusted basis** — BASELINE_AUDIT. PR41은 가격 basis·시세상태·PIT를 검증완료로 승격하지 않음. split 원본 표본은 확보했으나 차트 조정·세션 연결 미완료.
- **A05 Corporate Action 표시/처리** — BASELINE_AUDIT. PR41은 가격 basis·시세상태·PIT를 검증완료로 승격하지 않음. split 원본 표본은 확보했으나 차트 조정·세션 연결 미완료.
- **A06 Current / live / delayed / close** — BASELINE_AUDIT. PR41은 가격 basis·시세상태·PIT를 검증완료로 승격하지 않음. split 원본 표본은 확보했으나 차트 조정·세션 연결 미완료.
- **A07 Crosshair / tooltip contract** — NON_CANONICAL_DEMO_VERIFIED. PR41: 합성 일봉 캔들·거래량/범위/교차선·값 조회 검증. 실제 NVDA5일 원본 사전검사 통과. intraday·세션·PIT·운영 연결은 미완료.
- **A08 Zoom / pan series** — NON_CANONICAL_DEMO_VERIFIED. PR41: 합성 일봉 캔들·거래량/범위/교차선·값 조회 검증. 실제 NVDA5일 원본 사전검사 통과. intraday·세션·PIT·운영 연결은 미완료.
- **A09 Market Session 상태** — BASELINE_AUDIT. PR41은 가격 basis·시세상태·PIT를 검증완료로 승격하지 않음. split 원본 표본은 확보했으나 차트 조정·세션 연결 미완료.

## B. Technical (15)

- **B01 SMA** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B02 EMA** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B03 RSI** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B04 MACD** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B05 Bollinger Bands** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B06 ATR** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B07 Volatility** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B08 Support / resistance** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B09 Trend / regime** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B10 Technical State** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B11 Entry / Add / Wait / Risk-Reduction Zone** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B12 Invalidation** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B13 Signal / event marker** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B14 Research Indicator / Model Indicator 분리** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **B15 Future Path / probability fan** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다. 세부: 경로 S=1~N, 범위·trigger·confirmation·invalidation·QGV 적합성·확률/Confidence 분리, horizon별 불확실성·실제 forward 비교. 120/252일 예시는 확정 상수 아님.

## C. QGV (12)

- **C01 Q/G/V breakdown** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **C02 Total / attractiveness** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **C03 Confidence** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **C04 Historical QGV** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **C05 Historical valuation** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **C06 Valuation range** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **C07 Margin of safety** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **C08 Reverse DCF 표시** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **C09 Negative / Neutral / Positive scenario** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **C10 Target price / range** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **C11 Peer comparison** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **C12 Key Drivers / Risk 연결 시각화** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.

## D. Analyst / Consensus (8)

- **D01 Analyst count** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **D02 Average target** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **D03 Median target** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **D04 High / low target** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **D05 Revision direction** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **D06 Consensus history** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **D07 Current price vs target** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **D08 QGV target vs Consensus** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.

## E. Portfolio (11)

- **E01 산업 구성 도넛** — NON_CANONICAL_REFERENCE_DEMO_VERIFIED. PR41: 기존19종목 목표비중의 산업군 참고자료와 가상 기업의 유형별 독립 도넛·정확한 중복 조합 표시를 검증. 실제 계좌·기업별 유형·분기 이력은 미연결. 세부: 분기 immutable snapshot 연결, 실제/목표 산업비중과 변화.
- **E02 유형 구성 도넛** — NON_CANONICAL_REFERENCE_DEMO_VERIFIED. PR41: 기존19종목 목표비중의 산업군 참고자료와 가상 기업의 유형별 독립 도넛·정확한 중복 조합 표시를 검증. 실제 계좌·기업별 유형·분기 이력은 미연결. 세부: 유형 구성 텍스트와 도넛, 중복 허용·합계>100% 보존, 분기 snapshot.
- **E03 유형 중복 Overlap Chart** — NON_CANONICAL_REFERENCE_DEMO_VERIFIED. PR41: 기존19종목 목표비중의 산업군 참고자료와 가상 기업의 유형별 독립 도넛·정확한 중복 조합 표시를 검증. 실제 계좌·기업별 유형·분기 이력은 미연결. 세부: 정확한 유형 조합과 중복 노출, 분기 immutable snapshot.
- **E04 Actual vs target weight** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **E05 Weight gap** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **E06 Concentration** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **E07 Sector / industry exposure** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **E08 Contribution** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **E09 Unrealized P&L** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **E10 Portfolio drawdown** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **E11 Correlation / risk visualization** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.

## F. Simulation / Backtest (10)

- **F01 Portfolio equity curve** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **F02 S&P 500 TR** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **F03 Equal Weight TR** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **F04 Growth Index** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **F05 Sector / factor benchmark** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **F06 Drawdown** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **F07 Rolling return** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **F08 Quarterly performance** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다. 세부: 모든 보유종목·비중·시작/종료가격·수익률·QGV 및 산업/유형 노출 변화.
- **F09 Holding / weight history** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **F10 Trade / execution position** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.

## G. Macro (8)

- **G01 Macro regime history** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **G02 Cycle / regime visualization** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **G03 Rates** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **G04 Inflation** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **G05 Liquidity** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **G06 Growth** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **G07 Probability / confidence** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **G08 Sector impact** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.

## H. Leaderboard / 기업 상세 (8)

- **H01 QGV ranking** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **H02 Market-cap rank** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **H03 Price / daily return** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **H04 Target prices** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **H05 Consensus** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **H06 Scenario targets** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **H07 Historical rank** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **H08 Company comparison** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.

## I. 기존 추가 Spec (17)

- **I01 Portfolio scenario value range** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다. 세부: 회사별 비중·scenario 조건, 주요 기여/손실 기업.
- **I02 개별 보유종목 return curve** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **I03 보유종목 평균 curve** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **I04 기업 유형별 평균 curve** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **I05 Top500 Universe return curve** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **I06 공통 시작값 정규화·series on/off** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다. 세부: 공통 시작값·개별 series toggle·zoom.
- **I07 Growth/Quality/Momentum 중 최소 2개 비교** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **I08 Macro Risk pillar history** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **I09 Company QGV revision / outcome timeline** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다. 세부: Q/G/V 변화 vs 매출/EPS/FCF/ROIC 실현과 수익률, Key Driver 실현상태.
- **I10 Portfolio decision history** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **I11 QGV version별 성과·표본수** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **I12 Scenario calibration** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **I13 Confidence calibration** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **I14 Leaderboard cohort outcome** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **I15 Simulation vs Forward 비교** — BASELINE_AUDIT. 기존 감사 판정 유지. 새 코드가 canonical에 반영된 것은 아닙니다.
- **I16 RIG News Network / Discovery** — CANONICAL_RENDERER_EXISTS. 기존 RIG SVG renderer 존재. 실뉴스 서비스 전체 운영 완료와는 구분.
- **I17 RIG Potential Impact Path** — CANONICAL_RENDERER_EXISTS. 기존 RIG SVG renderer 존재. 실뉴스 서비스 전체 운영 완료와는 구분.

## J. 이번 완전성 점검 추가 (7)

- **J01 Portfolio QGV 평균·분포** — REQUIREMENT_IDENTIFIED_NOT_REAUDITED. §13,17의 명시 요구. 문서의 과거 완료 선언을 현재 구현 증거로 쓰지 않음.
- **J02 Portfolio Confidence 분포** — REQUIREMENT_IDENTIFIED_NOT_REAUDITED. §13의 명시 요구. 문서의 과거 완료 선언을 현재 구현 증거로 쓰지 않음.
- **J03 Portfolio Valuation / Safety Margin 노출** — REQUIREMENT_IDENTIFIED_NOT_REAUDITED. §13,17의 명시 요구. 문서의 과거 완료 선언을 현재 구현 증거로 쓰지 않음.
- **J04 기업 재평가 Trigger: 변화량·임계값·거리·상태** — REQUIREMENT_IDENTIFIED_NOT_REAUDITED. §18,19의 명시 요구. 문서의 과거 완료 선언을 현재 구현 증거로 쓰지 않음.
- **J05 Full VMR 비교: Beta·percentile·비정상 움직임** — REQUIREMENT_IDENTIFIED_NOT_REAUDITED. §19의 명시 요구. 문서의 과거 완료 선언을 현재 구현 증거로 쓰지 않음. 세부: 1D/5D/20D 수익률,20D/60D/1Y 변동성,일간sigma,ATR14%,Beta,변동성percentile,drawdown,기업/산업/시장 및 초과 움직임.
- **J06 재평가 이벤트 이력·사후 관찰·Calibration** — REQUIREMENT_IDENTIFIED_NOT_REAUDITED. §20의 명시 요구. 문서의 과거 완료 선언을 현재 구현 증거로 쓰지 않음. 세부: 고정 trigger event, QGV 전후, 원인, D+5/D+20/63D/252D 관찰. 자동 승격 금지.
- **J07 Technical QGV Fusion 결과·원점수 분리** — REQUIREMENT_IDENTIFIED_NOT_REAUDITED. §14의 명시 요구. 문서의 과거 완료 선언을 현재 구현 증거로 쓰지 않음.

## K. Macro Candidate 확장 (8)

- **K01 8개 거시 축의 수준·방향·모멘텀·surprise·stress·confidence** — CANDIDATE_SPEC_ONLY. 별도 후보 설계 범위. 기존81개 완료율 분모에서 제외.
- **K02 가변 Macro scenario 경로·분포** — CANDIDATE_SPEC_ONLY. 별도 후보 설계 범위. 기존81개 완료율 분모에서 제외.
- **K03 Factor→경제 경로→산업→기업→Q/G/V 전달** — CANDIDATE_SPEC_ONLY. 별도 후보 설계 범위. 기존81개 완료율 분모에서 제외.
- **K04 구조적·실증적·시장내재·이벤트 노출 비교** — CANDIDATE_SPEC_ONLY. 별도 후보 설계 범위. 기존81개 완료율 분모에서 제외.
- **K05 QGV base/context·Technical base/조건부 확률 비교** — CANDIDATE_SPEC_ONLY. 별도 후보 설계 범위. 기존81개 완료율 분모에서 제외.
- **K06 Portfolio 거시 요인 집중·위험 문맥** — CANDIDATE_SPEC_ONLY. 별도 후보 설계 범위. 기존81개 완료율 분모에서 제외.
- **K07 역사적·가상·Reverse stress 영향·기여도** — CANDIDATE_SPEC_ONLY. 별도 후보 설계 범위. 기존81개 완료율 분모에서 제외.
- **K08 Macro ablation·attribution·calibration·forward 비교** — CANDIDATE_SPEC_ONLY. 별도 후보 설계 범위. 기존81개 완료율 분모에서 제외.

## L. 기업분석 시안 추가 (Cockpit IA v1)

문서 요구 식별만 수행했다. 문서 중복 대조 기준은 canonical `011b75648f48f2890736d37c4a354f57004cf1f0`의 A–K 기존 113개 요구와 JSON 전체 객체이며, 위의 과거 감사 기준·metadata는 보존한다. 기존 ID의 상태·계층 판정·source evidence도 그대로 유지한다. 아래 9개 후보는 신규 8개와 기존 ID 연결 1개로 구분하며, 후보별 요구사항 상태는 모두 `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`, 데이터 공급처는 모두 `UNDECIDED`이다. 기존 ID 연결도 이번에 구현을 재감사하거나 완료로 승격한 것이 아니다. 기존 `core_denominator = 81` 및 baseline 완료 지표는 바꾸지 않는다.

### A–K 중복 대조와 기존 ID 연결

| 검토 범위 | 후보와의 관계 / 중복 경계 |
| --- | --- |
| A01–A09 | 가격·기업행사·기간·조회 계약은 기존 요구에 연결한다. 기업분석 이벤트 분류 전체나 배당/자사주 추이와 동일하지 않다. |
| B01–B15 | L05의 공통 marker 표현은 → 기존 ID 연결 `B13`. 기술 신호/marker 요구를 신규로 중복 등록하지 않는다. |
| C01–C12 | QGV·가치·peer 비교는 기존 요구다. L01 시장점유율, L02 매출 구성, L03 독립 재무 시계열과 동일하지 않다. |
| D01–D08 | L07과 관련한 analyst 수·평균/중앙/최고/최저 목표가·revision·history는 → 기존 ID 연결 `D01–D06`. 증권사별 원문 의견/목표가 표는 aggregate consensus와 별도 요구다. `D07–D08` 비교도 기존 상태를 유지한다. |
| E01–E11 | 포트폴리오 산업/유형 구성과 계좌 손익은 기업 자체 매출 구성·주주환원과 동일하지 않다. |
| F01–F10 | L04의 S&P 500/산업 benchmark 요구는 → 기존 ID 연결 `F02`, `F05`. `F08`은 전 보유종목·비중·QGV/노출을 포함한 포트폴리오 분기 성과이므로 기업 단위 분기/연간 비교와 동일하지 않다. |
| G01–G08 | 거시 history·금리·물가·유동성·성장 등은 기존 요구에 연결한다. L08 8축 board는 더 직접적인 K01로 연결한다. |
| H01–H08 | 기업 순위·가격·목표가·consensus·기업 비교는 기존 요구다. 일반 기업 비교 `H08`만으로 특정 시장점유율/매출 구성 요구를 중복으로 간주하지 않는다. |
| I01–I17 | L03의 QGV 변화와 매출/EPS/FCF/ROIC 실현 관계는 → 기존 ID 연결 `I09`; 독립 분기/연간 재무 그래프는 별도다. L04의 보유종목 curve·공통 series 정렬/토글은 → 기존 ID 연결 `I02`, `I06`; 단일 기업 기간별 benchmark 비교는 별도다. |
| J01–J07 | L05의 R 재평가 이력·QGV 전후·D+5/D+20 사후 관찰은 → 기존 ID 연결 `J06`이며 신규 calibration을 만들지 않는다. L09는 포트폴리오 분포 J01–J03이나 trigger/VMR J04–J05와 다른 reconciliation 상태별 건수 요약이다. |
| K01–K08 | L08 공식 UI 8축 board는 → 기존 ID 연결 `K01`. 사용자 UI 결정과 원문 8축 참조를 기록하며, K01의 기존 `CANDIDATE_SPEC_ONLY`·감사·evidence는 보존한다. K02–K08의 경로/전달/비교/집중/검증도 기존 상태를 유지한다. |

| 후보 | 판정 | 이유 | 요구사항 상태 | 데이터 공급처 |
| --- | --- | --- | --- | --- |
| L01 Market share | 신규 `L01`; → 기존 ID 연결 `C11`, `H08` | 기업/경쟁사 점유율 막대 + 점유율 추이는 기존 QGV peer/일반 기업 비교보다 구체적인 별도 요구. | `REQUIREMENT_IDENTIFIED_NOT_REAUDITED` | `UNDECIDED` |
| L02 Revenue composition | 신규 `L02`; → 기존 ID 연결 `E01`, `E07` | 사업부/지역별 기업 매출 구성은 포트폴리오 산업 구성·노출과 다른 재무 범위. | `REQUIREMENT_IDENTIFIED_NOT_REAUDITED` | `UNDECIDED` |
| L03 Financial trends | 신규 `L03`; → 기존 ID 연결 `I09` | 독립 분기/연간 매출 막대·성장률/EPS/ROIC 추이만 신규. QGV revision/outcome 관계는 I09를 재사용. | `REQUIREMENT_IDENTIFIED_NOT_REAUDITED` | `UNDECIDED` |
| L04 Periodic returns | 신규 `L04`; → 기존 ID 연결 `F02`, `F05`, `I02`, `I06` | 단일 기업의 분기/연간 toggle과 기업/S&P 500/산업 비교. F08 포트폴리오 성과를 대체하거나 재등록하지 않음. | `REQUIREMENT_IDENTIFIED_NOT_REAUDITED` | `UNDECIDED` |
| L05 Company events on price | 신규 `L05`; → 기존 ID 연결 `A01`, `A04`, `A05`, `B13`, `J06` | 비재평가 기업 이벤트 분류와 가격/사후수익률 조합만 신규. 공통 가격/marker·R 재평가 이력 및 관찰은 기존 ID. B(내 매수)는 기기 전용 개인 표시 요구에 연결. | `REQUIREMENT_IDENTIFIED_NOT_REAUDITED` | `UNDECIDED` |
| L06 Shareholder return | 신규 `L06`; → 기존 ID 연결 `A05` | 배당·자사주 매입 추이와 corporate-action 가격 처리/marker는 서로 다른 요구. | `REQUIREMENT_IDENTIFIED_NOT_REAUDITED` | `UNDECIDED` |
| L07 Broker targets / opinions | 신규 `L07`; → 기존 ID 연결 `D01–D06` | 증권사별 표만 신규이며 consensus aggregate/history는 기존 ID. | `REQUIREMENT_IDENTIFIED_NOT_REAUDITED` | `UNDECIDED` |
| L08 Macro 8-axis board | → 기존 ID 연결 `K01` | 같은 8축 요구. 신규 L08 ID/JSON item을 만들지 않음. 공식 UI 참조만 기록하고 K01 기존 감사 상태는 보존. | `REQUIREMENT_IDENTIFIED_NOT_REAUDITED` | `UNDECIDED` |
| L09 Reconciliation state counts | 신규 `L09` | 기존 차트 감사 계층/완료율이 아닌 reconciliation 6상태 건수 요약. | `REQUIREMENT_IDENTIFIED_NOT_REAUDITED` | `UNDECIDED` |

중복 경계의 원문 근거는 `QGV Simulation · Specification v1.0.md` §6–9(F02/F05/I02/I06 공유 범위 및 F08 전 보유종목 분기 보고), `QGV Track Record · Specification v1.0.md` §7·14·16(I09 revision/outcome), `QGV Leaderboard · Specification v1.0.md` §8·20(D 그룹 aggregate consensus와 J06 고정 재평가/사후 관찰), `QGV System · Common Schema & API Contract v1.0.md` §6(aggregate Consensus Snapshot), `Macro System · Latest Consolidated Record v0.1.4 Candidate.md` §15(K01 동일 8축)이다. 원문 요구 대조이며 현재 코드·원본 입력·차트 구현의 재감사가 아니다.

### L08 → 기존 ID 연결 K01 (신규 계수 제외)

2026-10-09 사용자 결정의 공식 UI 8축은 **Growth / Inflation / Liquidity / Monetary Policy / Credit / Labor / Fiscal / FX**다. [Cockpit IA v1](../../docs/frontend_ia_v1/COCKPIT_IA_v1.md) §3.8과 `Macro System · Latest Consolidated Record v0.1.4 Candidate.md` §15를 참조하며, 각 축의 **Level / Direction / Momentum / Surprise / Stress / Confidence** 요구가 기존 K01과 동일하다. 이 후보 연결의 상태는 `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`, 데이터 공급처는 `UNDECIDED`이다. 공식 UI 참조와 원문 일치만 기록한다. K01의 기존 `CANDIDATE_SPEC_ONLY`·scope·감사 계층·evidence를 변경하거나 모델·방법론·실데이터·구현 검증 완료를 주장하지 않는다.

### 신규 요구 (8)

- **L01 Market share: company / competitors / share trend** — `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`; 데이터 공급처 `UNDECIDED`. 기업과 경쟁사의 시장점유율 막대 및 점유율 추이. 시장 범위·경쟁사 집합·기간·비교가능성은 미결정이며 임의 점유율을 채우지 않는다.
- **L02 Revenue composition: business unit / region** — `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`; 데이터 공급처 `UNDECIDED`. 사업부 및 지역별 기업 매출 구성. 분류·기간·통화·segment 재작성의 비교가능성은 미결정이며 합계/누락을 추정하지 않는다.
- **L03 Financial trends: revenue / growth / EPS / ROIC** — `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`; 데이터 공급처 `UNDECIDED`. 분기/연간 매출 막대와 성장률·EPS·ROIC 추이. 재무 정의·기간·restatement 기준은 미결정이며 새 수식/산출정책을 만들지 않는다. QGV 변화 대비 실현 관계는 → 기존 ID 연결 `I09`.
- **L04 Periodic returns: company / S&P 500 / industry** — `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`; 데이터 공급처 `UNDECIDED`. 분기/연간 toggle의 단일 기업·S&P 500·산업 수익률 비교. 기업/benchmark 정렬과 가격수익률/TR·통화·기간·industry 정의는 미결정. 기존 benchmark/curve/정렬 요구는 → 기존 ID 연결 `F02`, `F05`, `I02`, `I06`; `F08`의 계좌/포트폴리오 분기 성과와 구분한다.
- **L05 Company events on price: E / P / L / M / R; B(내 매수, 기기 전용)** — `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`; 데이터 공급처 `UNDECIDED`. 영문 marker는 E Earnings(실적발표), P Product(제품발표), L Regulation / Litigation(규제/소송), M Acquisition / Partnership(M&A/파트너십), R Re-rating(재평가)다. 기존 재평가 표기 S는 R로 변경하며 B Buy(내 매수)는 아래 개인 표시 요구의 기기 전용 marker다. 주가와 함께 보여주는 기업 이벤트 시안 및 이벤트 후 5/20일 수익률 요구. 새 범위는 비재평가 기업 이벤트의 유형화·가격 연결·관찰 조합이다. 가격 basis/기업행사/공통 marker는 → 기존 ID 연결 `A01`, `A04`, `A05`, `B13`; R 이력과 D+5/D+20 관찰은 → 기존 ID 연결 `J06`. 거래일/달력일·event timestamp·수익률 basis는 미결정이며 인과 효과·새 calibration·자동 승격을 주장하지 않는다.
- **L06 Shareholder return: dividends / buybacks** — `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`; 데이터 공급처 `UNDECIDED`. 배당 및 자사주 매입 추이. 선언/지급·승인/실행 구분과 기간·금액/주식수 단위는 미결정. 가격조정/marker 처리는 → 기존 ID 연결 `A05`; 기업 주주환원을 계좌 입금·주문 실행으로 해석하지 않는다.
- **L07 Broker targets / opinions table** — `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`; 데이터 공급처 `UNDECIDED`. 증권사별 목표주가/의견 표. 기관/작성시점·의견 원문·목표가 basis는 미결정. 수·평균/중앙/최고/최저·revision/history는 → 기존 ID 연결 `D01–D06`; 의견 변환 규칙이나 임의 목표가는 만들지 않는다.
- **L09 Reconciliation state count summary** — `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`; 데이터 공급처 `UNDECIDED`. `MATCH`, `MISMATCH`, `NOT_AVAILABLE`, `NOT_COMPARABLE`, `PARTIAL`, `NO_DATA`별 건수 요약. 집계대상·중복/시점 규칙은 미결정이며 값이나 0건을 채우지 않는다. 기존 R/I/P/S/H/U 감사 계층·Confidence·핵심81 완료율과 혼합하지 않는다.

영문 ID/chart code/label은 문서 식별자이며 한국어 UI copy와 별도 관리한다. `E/P/L/M/R` 기업 이벤트 코드, 기기 전용 `B/S` 개인 거래 표시, L09 reconciliation 상태, 기존 감사 `L1–L5`/`R/I/P/S/H/U`는 서로 다른 문맥이다. 공급처·원본·정의·비교가능성·입력 승인·구현·검증은 여전히 미결정/미재감사다. 이 추가는 TARGET, 가중치, 방법론, 수식, 금융 개인정보, 주문/체결 또는 기존 broader gate를 변경하거나 닫지 않는다.

### 개인 표시 요구 (1개; 문서 요구 추가)

- **내 거래 표시(B/S 마커·AVG 선, 기기 전용·끄기 가능)** — 요구 상태 `REQUIREMENT`, 구현 상태 `NOT_IMPLEMENTED`. 사용자는 내 거래 표시를 끌 수 있으며, 끄면 B/S 마커와 AVG 선을 모두 숨긴다. 기존 기기 입력의 `average_cost`를 `AVG` 평균단가 선으로 D4 일봉 차트 위에 기기 안에서 그리는 표시만 먼저 요구한다. D4는 일일 데이터 파이프라인 설계의 가격 차트 경로를 가리킨다. 후속 B Buy(내 매수) / S Sell(내 매도) 거래일 marker는 사용자의 비공개 Google Sheets `Trades`를 기존 Google 로그인으로 읽기 전용으로 읽는 방식 또는 직접 입력 중 선택하며, 이번 문서에서 연결을 구현하지 않는다. 평균단가·거래일·가격·수량 등 개인 데이터는 기기에만 두고 공개 저장소·JSON·Pages 산출물에 싣지 않는다. 주문·매수·매도 실행 기능을 추가하지 않으며 투자 방법론·TARGET·평균단가 계산 규칙은 유지한다. 기존 121개 inventory 항목과 핵심81 완료율 분모는 보존하고, 이 개인 표시 요구 1개를 구현 완료로 계산하지 않는다.

## 상태 해석

가격 OHLCV와 Portfolio3개 renderer는 별도 PR에서 제한된 참고자료/가상 입력으로 검증됐다. 나머지 전체 chart 완성률을 테스트 개수로 환산하지 않는다. 과거 Spec의 RC26/366PASS 등 선언도 현재 소스·시험·원본 근거 없이 완료로 취급하지 않는다.

## 개선 순서

1. Portfolio 실제/목표 snapshot와 과거분류 데이터 연결, 분기 history 보존.
2. 가격종목 identity·일봉 session·조정기준·PIT 연결.
3. 이미 있는 QGV/순위 snapshot을 공통 계약에 연결.
4. 미구현 indicator·consensus·TR benchmark는 실제 source/calculation부터 진행.
5. MCP는 같은 payload를 읽는 후속 계층으로 유지.
