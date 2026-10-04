# 전체 차트·시각화 요구 목록 v0.2

기준: canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`, 기존 통합시험 `acaf1b5a82859ac2750a130ebe88f8b4d272ac66`, chart owner PR41. 최신 PR 변경은 별도 note이며 canonical 구현으로 계산하지 않는다.

**핵심81 + 추가 Spec24 + Macro Candidate8 = 113개 요구 항목. 독립 차트113개라는 뜻은 아니다.** 원래 핵심81개 완료율 분모는 유지한다. J7은 이번에 추가 식별한 요구이며 전체 구현 계층을 새로 감사한 결과가 아니다. K8은 후보 설계이고 확정 기본정책이 아니다.

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

## 상태 해석

가격 OHLCV와 Portfolio3개 renderer는 별도 PR에서 제한된 참고자료/가상 입력으로 검증됐다. 나머지 전체 chart 완성률을 테스트 개수로 환산하지 않는다. 과거 Spec의 RC26/366PASS 등 선언도 현재 소스·시험·원본 근거 없이 완료로 취급하지 않는다.

## 개선 순서

1. Portfolio 실제/목표 snapshot와 과거분류 데이터 연결, 분기 history 보존.
2. 가격종목 identity·일봉 session·조정기준·PIT 연결.
3. 이미 있는 QGV/순위 snapshot을 공통 계약에 연결.
4. 미구현 indicator·consensus·TR benchmark는 실제 source/calculation부터 진행.
5. MCP는 같은 payload를 읽는 후속 계층으로 유지.
