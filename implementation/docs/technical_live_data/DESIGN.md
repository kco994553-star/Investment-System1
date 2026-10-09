# Technical 일봉 실데이터 연결 설계

기준일: **2026-10-09 UTC** · 읽기 기준 canonical: **`12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df`**(PR #87 병합) · 상태: **문서 설계안 / 구현·배포·운영 활성화 미실행**

이 문서는 기존 Technical 계약에 개인 전용 일봉 입력을 연결하는 순서와 한계를 정리한다. 새 지표·점수식·임계값·Fusion 방법론을 확정하지 않는다. 현재 작업은 문서만 작성하며 실제 시세·계정·토큰·키·Secret을 조회하지 않고, 가격 파이프라인·QGV 재점수·Worker 설정·가입·배포를 실행하지 않는다. 후속 구현 PR 제안은 실행 승인이 아니다.

## 1. 현재 코드로 가능한 범위

**첫 구현은 일봉 검증 → 기존 수익률 입력 → 기존 `TechnicalEngine.evaluate`의 mock 계약 확인으로 제한하는 것이 맞다.** 실데이터 연결만으로 현재 placeholder를 검증된 Technical 모델로 바꿀 수 없다.

| 근거 층 | 확인한 내용 | 이 설계에서의 의미 |
|---|---|---|
| 과거 개발 기록 | Phase 1~6·v0.6 구조 동결·159/159 PASS 기록이 있으나 실제 시장 예측 유효성·외부 실시간 데이터·전체 Forward Validation 완료와 다르다고 명시한다. [S01] | 원 개발 패키지가 현재 checkout에서 실행 가능하다는 증거로 쓰지 않는다. |
| canonical 엔진 | `TechnicalEngine.evaluate(company_id, as_of, returns, qgv=None, synthetic=True)`는 일봉이나 provider가 아닌 `list[float]`를 받는다. [S02] | 별도의 입력 검증·수익률 어댑터가 필요하다. |
| 실제 계산 | 전달된 전체 returns의 모집단형 표준편차, 마지막 return, 마지막 5개 return 합으로 regime/zone을 정한다. 엔진 자체에는 20개로 자르는 코드가 없다. [S02] | 공식 지표군 또는 완성된 TSV 모델로 해석하지 않는다. |
| 기존 일봉 연결 후보 | `validation/historical.py::bars_to_returns`는 `observed_at <= as_of`의 가격에서 단순 수익률을 만들고 마지막 20개를 반환한다. [S03] | 첫 PR의 호환 기준으로 사용하되, 저장·수집·QGV 계산을 포함하는 historical pipeline 전체를 실행하지 않는다. |
| 현재 producer | `TECHNICAL_NO_REAL_MODEL`이 기본 차단 사유이며, Web adapter의 COMPATIBLE은 shape만 뜻한다. [S04] [S05] | 실제 입력이 생겨도 LIVE 모델 완료로 승격하지 않는다. |
| 차트 목록 | B01~B15는 `BASELINE_AUDIT`, J07은 `REQUIREMENT_IDENTIFIED_NOT_REAUDITED`다. [S06] | 요구 항목과 현재 구현·검증 상태를 구분한다. |

현재 `implementation/src/investment_system/technical/`에는 `engine.py`와 export용 `__init__.py`가 있다. 이 범위에는 SMA·EMA·RSI·MACD·Bollinger Bands·ATR 계산, 공식 Model Indicator Set, TSV schema/가중치, 동적 경로 생성, empirical probability/calibration 계산이 없다. 공식 지표 목록·파라미터·regime 알고리즘·Fusion 출력명은 기존 결정 이력에서도 미확정이다. [S02] [S07]

## 2. 최신 개인 경로 결정과 승인 경계

PR #85의 조사·설계와 GSQ-007의 Yahoo 우선순위를 유지하며, 중계·인증 선택에는 PR #87에서 반영된 **GSQ-008이 우선**한다. [S08] [S09] [S10]

| 항목 | 적용할 결정 |
|---|---|
| 가격 출처 | Yahoo Finance의 키 없는 비공식 chart를 개인 조회·표시 설계의 1순위로 검토한다. **사전 허가 없는 자동 조회는 약관 부적합**이며 사용자도 이를 인지·수용했다. 사용자 수용은 공급자 허가나 실제 자동 수집·중계의 승인이 아니다. [S08] [S09] |
| 플랫폼·비용 | **Workers Free만, 비용 0·카드 없음**. Zero Trust/Access는 제외한다. 유료 전환·add-on·카드 등록을 하지 않는다. Free 조건을 유지하지 못하면 미제공으로 종료한다. [S10] |
| Google 로그인 | 기존 GIS token-client 흐름에 `email` scope를 추가하는 후속 방향이다. `https://www.googleapis.com/auth/spreadsheets.readonly`를 유지한다. canonical 코드는 아직 readonly 하나만 요청하며 응답 scope도 정확히 그 값으로 비교한다. 따라서 상수만 바꾸면 끝나는 변경이 아니다. [S10] [S11] |
| 앱 → Worker | Google **access token**을 검증용으로만 전달한다. 토큰을 Yahoo나 가격 공급자로 전달하지 않는다. [S10] |
| Worker 검증 | Google tokeninfo 결과의 `aud` = 기존 OAuth client ID, `email` = 본인 이메일, `email_verified` = 참, 유효·미만료인 만료 정보를 모두 확인한다. 누락·불일치·미확인·만료·tokeninfo 오류는 거부한다. 실제 client ID·이메일·토큰 값은 문서·소스 예시에 넣지 않는다. [S10] |
| CORS | 허용 Origin은 **`https://kco994553-star.github.io` 하나**다. wildcard·다른 Origin을 허용하지 않는다. CORS와 로그인 성공만으로 본인 인증을 대체하지 않는다. [S10] |
| 비보존 | 앱·Worker 모두 토큰·가격·가격 기반 파생값을 필요한 휘발성 메모리에서만 처리한다. 파일·DB·KV/D1/R2·Cache API·IndexedDB·localStorage·service worker cache·백업·공개 JSON·Pages 데이터·Actions 로그/아티팩트에 넣지 않는다. 토큰·응답 body·Authorization·tokeninfo 요청 URL·가격이 포함된 예외/관측 로그를 출력하지 않는다. [S08] [S10] |
| 대안 | 비밀 접속 코드 방식은 보류한다. Yahoo 실패 시 시장별 Tiingo/미국·KRX/한국의 조건을 확인하며, Google 시트·수동은 **현재가 fallback**이다. 현재가를 과거 일봉으로 확장하지 않는다. [S09] |

공개 Pages에는 승인된 정적 코드·가격 없는 식별/재무 입력만 있을 수 있다. 개인 일봉·수익률·지표·regime·scenario·가격이 결합된 QGV/V·시총 순위는 본인 RAM 응답에서만 다룬다. 공개 재무 자료의 기존 SEC·DART 경로를 유지하며, 공개 재무와 개인 가격을 결합한 결과를 공개 경로로 되돌리지 않는다. 기존 공개 산출물의 가격 기반 필드가 이미 모두 차단됐다는 완료 선언도 하지 않는다. [S08]

## 3. 필요한 일봉 입력과 역사 길이

### 3.1 입력 묶음 제안

아래는 후속 구현에서 검토할 **개인 입력 sidecar 제안**이다. 현행 `PricePoint`, `DataStamp`, `TechnicalSnapshot`을 이미 확장한 계약이 아니다.

| 입력 | 필요한 의미 | 결측 처리·현행 gap |
|---|---|---|
| 식별 | `company_id`, 실제 상장/security/listing 식별, 시장·거래소, 원 심볼, provider별 명시 심볼 | 티커 문자열만으로 동일 상장·주식 종류를 추정하지 않는다. TARGET/Frozen 식별과 mapping을 대조한다. |
| 일봉 시각 | bar의 관측 시각, 현지 timezone·거래 session, session 종료/완료 여부 | 날짜와 취득 시각을 최초 공개 시각으로 쓰지 않는다. 마지막 진행 중 bar를 완료 종가 입력에 섞지 않는다. finality 미확인은 그대로 남긴다. |
| 가격 필드 | 원 `open/high/low/close`, 별도 `adjclose` 또는 조정 가격, 각 가격의 basis | 현재 엔진에는 선택된 close 가격만 필요하다. OHLC는 캔들·구조/범위 요구를 위한 별도 입력이고, 없음은 null이다. |
| 거래량 | 원 volume, 단위·거래소/주식 종류, 조정 여부 | 현재 엔진은 volume을 사용하지 않는다. 누락은 거래량 기능의 미제공이며 0으로 채우지 않는다. 제공된 실제 0과 결측을 구분한다. |
| 조정·기업행사 | 공급자 조정 정책/확인 상태, split·배당 등 event의 효력 날짜·발표/가용 시각·원 출처·정정/vintage | event 배열이 비었다는 사실만으로 행사 없음이 검증됐다고 말하지 않는다. 조정 효과를 새 공식으로 재구성하지 않는다. |
| 통화·출처 | 원 통화, provider, interval, 원 심볼, source reference, `read_at`, 실제 관측 수 | 누락 통화→USD, 누락 시각→현재 UTC fallback을 쓰지 않는다. |
| 가용성·품질 | 원 `published_at/available_at`이 제공될 때 그 값, delay/availability 이유, synthetic 여부, 요청 `as_of` | 미확인 시각은 미확인으로 표현한다. 현행 `DataStamp`의 필수 datetime 칸에 취득 시각을 넣어 PIT 검증을 가장하지 않는다. |

`MarketDataProvider.price_stamp`는 단일 stamp만 제공하고 `PricePoint`는 단일 가격·통화 계약이다. 둘 다 OHLCV 역사·조정 basis·기업행사·세션 계약이 아니다. `DataStamp`에는 출처와 세 시각이 있으나, 일봉에서 알려지지 않은 최초 공개/가용 시각을 표현하는 방법은 별도 sidecar 검토가 필요하다. [S12] [S13] [S13R]

Yahoo `parse_bars`는 close/adjclose만 만들어 각 bar에서 adjclose가 있으면 그 값을, 없으면 close를 `price`로 쓴다. OHLCV·기업행사·연속 시리즈 basis 검증을 완료한 것으로 취급할 수 없다. `parse_chart`의 USD/현재시각 fallback, `to_price_point`의 세 시각 동일 지정도 새 경로의 검증 근거가 아니다. [S14] [S15]

### 3.2 기존 window에서만 유도한 요구 길이

| 용도 | repository의 기존 기간 | 일봉 입력에 대한 의미 |
|---|---|---|
| 엔진 regime의 마지막 합 | `returns[-5:]` [S02] | 5개 단순 수익률을 모두 재현하려면 앞선 기준 종가를 포함한 6개 가격 관측이 필요하다. 이는 수익률 변환의 길이 관계이며 새 모델 충분성 임계값이 아니다. |
| 현재 historical 어댑터 후보 | 최종 `rets[-20:]`; 2개 미만 가격이면 빈 returns [S03] | 20개 단순 수익률을 모두 재현하려면 21개 가격 관측이 필요하다. 2~20개 가격에서도 기존 helper는 더 짧은 returns를 만들 수 있다. 이를 완전한 모델 window로 표시하지 않는다. |
| 엔진 변동성 | 전달된 returns 전체 [S02] | historical 후보와 같은 입력을 만들 때만 마지막 20개 선택을 적용한다. 엔진 자체의 공식 고정 window라고 문서화하지 않는다. |
| VMR 표시 요구 | 1D/5D/20D return, 20D/60D/1Y realized volatility, Daily sigma, ATR(14)%, Beta·percentile·drawdown [S16] | 기간/항목, Company/Industry/Market 분리 및 시장·업종 조정 abnormal move 요구를 보존한다. 기술 모델 채택·계산식·연율화·benchmark 선택·percentile reference 구간을 확정하지 않는다. 1Y를 252 거래일로 자동 치환하지 않는다. |
| 전략프로필 | `technical_lookback` 30/14/8의 **PROVISIONAL placeholder** pack [S17] | `TechnicalEngine.evaluate`는 profile 인자를 받지 않는다. 이 수치를 지표 period나 일봉 fetch 기본값에 연결하지 않는다. |
| Future Path | 약 120/252 Trading Days는 검토안이며 공식 상수가 아니다. [S18] | forecast horizon은 과거 lookback의 결정 근거가 아니다. 현 설계에서 fetch 기간·경로 길이로 잠그지 않는다. |

20개를 선택하는 기존 변환을 재현하는 데 필요한 관측 수와, 모델 신뢰도를 주장할 충분한 역사 길이는 다른 요구다. **공식 지표별 period·warm-up·Model Indicator Set·검증 표본량은 UNKNOWN/DEFERRED**다. SMA/EMA/RSI/MACD/Bollinger의 관례적 기본값이나 ATR 라벨의 14를 모든 Technical 계산에 이식하지 않는다. [S07] [S16]

`interval=1d`와 provider의 `range`는 별개다. 달력 기간을 요청했다고 필요한 수의 완료 거래 관측이 확보됐다고 보지 않는다. 회사·시장별 완료 bar 수를 세고, 공급자가 제공한 역사 범위 밖을 합성하거나 다른 공급자/조정 series로 이어 붙이지 않는다. Yahoo의 시장별 최대 과거 기간·실제 coverage·완료 시점은 아직 확인되지 않았다. [S15]

### 3.3 조정 기준과 기업행사

원 OHLCV와 adjusted close를 별도 보존하는 RAM 구조를 택하고, returns에 쓰는 가격 basis는 **시리즈 단위로 명시**한다. bar마다 adjclose/close를 바꾸는 fallback은 사용하지 않는다. raw OHLC 중 close만 adjclose로 교체하면 캔들 내부 basis가 달라지므로 금지한다. 공급자 조정 의미·행사 반영 여부가 검증되지 않았으면 “adjusted array 존재”를 “기업행사/PIT 검증 완료”로 표시하지 않는다. [S14] [S19]

원 split·배당 event가 있더라도 조정 OHLC/volume·total-return을 새 방법론으로 계산하지 않는다. ticker/listing 변경, 분할·병합·배당·spin-off 등 처리 범위와 원 자료 vintage는 provider 계약 확인 후 정한다. 미검증 행사 구간에서 raw 가격 변화를 정상 연속 수익률로 간주하거나 임의 기준으로 discontinuity를 판정하지 않는다. 적합한 basis를 확인하지 못한 계산은 미제공으로 남긴다. 기존 historical outcome의 행사 gap 판정은 사후검증 후보의 별도 코드이며 이 설계의 새 실데이터 gate로 옮기지 않는다. [S03]

현재 chart 실험 계약도 `available_at=null`, `finality=UNKNOWN`, `pit_status=NOT_VERIFIED`를 보존하고 corporate action 검증이 구현되지 않았다고 제한한다. 이 점을 기준으로 “아는 값/모르는 값”을 분리하되 persisted raw bytes를 요구하는 실험 경로는 새 무저장 개인 경로에 연결하지 않는다. [S19]

## 4. 처리 위치와 실제 runtime

제안 흐름은 **사용자가 연 한 회사 → GIS access token → 본인 검증 Worker → 허가된 daily source → 앱 RAM 검증/계산/표시**다. 자동 polling·전체 기업 역사 선수집·Cron·Actions 가격 취득은 넣지 않는다. [S08] [S10]

| 위치 | 맡길 일 | 실행 가능성·경계 |
|---|---|---|
| 정적 앱 | 기존 식별/공개 재무 읽기, 사용자 작업 시작, 로그인·종목 선택, 메모리 수명 종료 | 공개 사이트에는 개인 가격을 저장하거나 빌드 시 계산하지 않는다. 기존 Google 시트·수동 저장 기능은 별도 기능이며 새 일봉 RAM을 그 저장 경로로 보내지 않는다. |
| Worker | tokeninfo 본인 검증, exact CORS, 허용된 company/provider-symbol/일봉·기간/응답 형식 검증, 제한된 공급자 요청, 개인 응답 전달 | 임의 URL을 받는 공개 프록시 금지. tokeninfo 호출과 가격 upstream 호출은 서로 다른 subrequest다. Free 한도·CPU·body 크기·본인 인증 성공을 실제 구현 단계에서 확인하며 미확인/실패 시 거부한다. |
| 본인 기기 | 일봉 일관성 검증, 허가·basis가 확인된 가격의 returns 준비, 후속 승인된 Technical runtime에서 계산, Research overlay와 Model output 분리 표시 | 가격/파생값을 작업 RAM에만 둔다. 화면 종료·로그아웃·취소 시 제거하고 늦게 도착한 응답을 이전 회사 화면에 붙이지 않는다. |
| 현재 Python | 첫 PR에서 mock 입력과 기존 엔진 계약을 검증하는 로컬 참조 구현 | `datetime`, `uuid`, dataclass/enum 및 Python package import를 쓰므로 기존 파일이 브라우저나 Worker에서 그대로 실행된다고 가정하지 않는다. |

**계산의 목표 위치는 기기이나 현재 실행 연결은 없다.** canonical Web MVP는 정적 읽기 전용 consumer이며 엔진을 실행하지 않는다. Google token은 현재 closure 내부에 있고 Worker로 전달할 공개 인터페이스도 없다. 후속 기기 runtime은 기존 엔진·방법론과 호환되는 별도 구현/복원 검토가 필요하다. Python 배포·Pyodide/WASM·Workers Python·Containers가 이미 가능하거나 비용 0 조건에 맞는다고 주장하지 않는다. [S02] [S11] [S20]

chart 실험의 `contract.mjs`는 `node:crypto`·`Buffer`·persisted raw bytes를 사용한다. lightweight-charts 의존성이나 합성 차트 검증은 Technical Python 엔진의 browser/Worker 실행 증거가 아니다. 검증 아이디어·OHLCV 필드만 참고하며 실험의 store/build/원 시세 pipeline을 실행·재사용하지 않는다. [S19] [S21]

Worker에서는 지표·scenario·QGV 계산을 수행하지 않는 제안을 유지한다. 기존 조사에 기록된 Free CPU/메모리 한도는 tokeninfo+응답 parsing의 실측을 대신하지 않는다. 새 TTL·정량 속도·payload 상한을 이 문서에서 만들지 않는다. 기존 일일 조회 예산 후보도 공급자 허용량·실동작 보장이 아니므로 별도 구현 검증 전 확정값으로 쓰지 않는다. module-global 가격 cache·지속 cache를 사용하지 않고, 진행 중 중복 작업의 RAM 공유도 허가된 같은 작업 범위 밖으로 확장하지 않는다. [S08]

후속 구현의 비보존 조건은 앱의 Worker 요청과 Worker의 upstream 요청에 `cache: no-store`, 개인 응답에 `Cache-Control: private, no-store`를 적용하고 Workers Logs/observability·invocation 로그 수집을 명시적으로 끄는 것이다. 이번 문서에서는 설정하지 않는다. CORS preflight는 허용 Origin·method/header 확인에 필요한 응답만 제공하고 가격·인증 결과를 전달하지 않는다. 실제 개인 데이터 요청은 매번 본인 검증을 통과해야 한다. [S08] [S10]

## 5. B01~B15·J07와 화면 연결

기존 IA S08의 **차트 / 상태 / 실행 / 기록**을 중심으로 S04 공통 종목, S05 기업분석, S01/S12 요약, S10 검증·연구를 연결한다. 같은 기업·상장·`as_of`를 유지하며 화면 요구 상태를 구현 완료 배지로 바꾸지 않는다. [S22]

| 기존 ID | 표시/연결 대상 | 이번 설계의 공급·계산 범위 |
|---|---|---|
| B01 SMA, B02 EMA, B03 RSI, B04 MACD, B05 Bollinger Bands | S08 차트의 Research 도구와 Model 채택 여부 | 입력 basis/period/warm-up·기존 방법론 복원 근거가 확인될 때만 후속 구현한다. 현재 목록 존재만으로 Model 채택이나 계산 완료를 주장하지 않는다. |
| B06 ATR | S08 변동성 도구; S05 VMR 요구와 별도 맥락 | high/low/close·이전 close가 필요한 입력 후보이나 공식 Technical 산식·period는 미확정이다. S05의 ATR(14)% 요구를 모델 채택으로 승격하지 않는다. |
| B07 Volatility | S08 변동성, 상태 근거 | 현재 엔진은 returns의 표준편차만 계산하며 값 자체를 snapshot에 출력하지 않는다. 이를 VMR 전체나 연율화 변동성으로 재명명하지 않는다. |
| B08 Support/resistance | S08 구조·무효화 근거 | swing 탐지·기간·가격 수준 계약은 없다. placeholder invalidation에서 실제 last swing low를 산출한 것으로 해석하지 않는다. |
| B09 Trend/regime, B10 Technical State | S08 상태, S04·홈 기술 요약 | 현행 regime enum과 기존 입력 계약만 보존한다. 새 TSV 점수/가중치·confidence 합성은 만들지 않는다. |
| B11 Entry/Add/Wait/Risk-Reduction Zone, B12 Invalidation | S08 실행·위험 조건 | enum 및 placeholder를 그대로 식별하며 READ_ONLY 분석으로 표시한다. 데이터 없음의 WAIT를 실제 대기 권고로 표현하지 않는다. |
| B13 Signal/event marker | S08 차트 marker, S05 이벤트 가격 맥락 | 실제 출처·시점·가격 basis가 있는 marker만 표시하는 후속 요구다. 신호/기업행사·기업뉴스/본인 매수는 의미와 개인 저장 경계가 다르다. 새 신호·인과 효과를 생성하지 않는다. |
| B14 Research/Model 분리 | S08 지표 선택·상태 | 사용자가 켠 overlay는 Research다. 승인된 Model Indicator Set 및 적용 버전이 없으면 “모델 채택”을 표시하지 않는다. Research 선택은 regime·zone·QGV 원점수를 바꾸지 않는다. |
| B15 Future Path/probability fan | S08 시나리오, S10 검증/기록 | 현행 구조 sample과 future model을 구분한다. 동적 S=1~N·범위·trigger·confirmation·invalidation·경로별 QGV compatibility·probability/confidence 분리·horizon별 불확실성·실제 forward path 비교·calibration 요구를 보존하되 실제 출력 데이터는 아직 공급되지 않는다. |
| J07 Technical QGV Fusion·원점수 분리 | S04/홈/상위 통합의 개별 판단 비교 | Technical과 QGV 참조를 나란히 보존한다. 새 합산/Fusion 점수·출력명을 만들지 않는다. |

B01~B15의 기존 `BASELINE_AUDIT`, J07의 미재감사 상태를 유지한다. chart 실험의 DEMO/REFERENCE 결과와 과거 구조 PASS는 실데이터 운영 또는 확률 calibration 완료의 근거가 아니다. [S06] [S07] [S18]

## 6. 현재 출력 계약을 그대로 보존할 것

### 6.1 엔진 snapshot

`TechnicalSnapshot`은 현재 다음 필드만 가진다. [S13]

| 필드 | 현행 계약/값 |
|---|---|
| 식별/기준 | `technical_snapshot_id`, `company_id`, `as_of` |
| 버전 | `technical_version="v0.6-STRUCTURAL-FREEZE"`, `implementation_kind="NEW IMPLEMENTATION"` [S23] |
| regime | `TREND_UP` / `TREND_DOWN` / `RANGE` / `HIGH_VOL` / `UNKNOWN` [S24] |
| execution_zone | `ENTRY` / `ADD` / `WAIT` / `RISK_REDUCTION` [S24] |
| scenarios | `scenarios: tuple[dict, ...]`; 현행 엔진은 `name=S1/S2/S3`, `return_shock=-0.1/0.0/0.1`, `kind="structural-placeholder"`를 출력한다. [S02] |
| 무효화 | `invalidation: Optional[str]`; 현행 값은 `close below last swing low (placeholder, NEW IMPLEMENTATION)` [S02] |
| 재검토 | `drawdown_recheck: bool`; 현행 엔진은 `False` [S02] |
| QGV 경계 | `qgv_snapshot_id_ref: Optional[str]`, `mutated_qgv=False` |
| 합성 | `synthetic: bool`; `evaluate` 기본값은 `True` |

엔진 안의 기존 `vol > 0.04`, 마지막 return과 마지막 5개 합의 부호, `last > 0.01`은 현재 structural 구현의 분기다. **그대로 재현하는 계약 검증 이외에는 공식 투자 임계값·검증된 매수 기준으로 승격하지 않는다.** 새 숫자나 최적화 기준을 추가하지 않는다. [S02]

returns가 비면 엔진은 `UNKNOWN/WAIT`를 출력하지만 scenario와 placeholder invalidation도 함께 반환한다. 따라서 결측 입력을 단순히 엔진에 넣은 뒤 정상 상태 카드로 공개하지 않는다. `synthetic=False`는 실제 입력의 출처 표시일 뿐 placeholder 모델·scenario의 유효성 검증이 아니다. 현 snapshot에는 OHLCV·TSV·indicator values·probability·confidence·horizon·trigger·confirmation·source refs·품질/coverage 필드가 없다. 새 입력 sidecar가 이 필드들을 이미 제공한다고 주장하지 않는다. [S02] [S13]

### 6.2 표시 상태와 입력 품질의 분리

| 축 | 기존 값·규칙 | 적용 경계 |
|---|---|---|
| Web 데이터 종류 | `LIVE`, `FROZEN_SNAPSHOT`, `DEMO`, `NOT_AVAILABLE` [S20] | 실제 일봉 수신만으로 Technical 모델을 LIVE로 만들지 않는다. mock는 DEMO·synthetic이며 실제값을 DEMO로 숨기지 않는다. |
| Web 신선도 | `FRESH`, `STALE`, `NOT_USABLE`, `NOT_APPLICABLE` [S25] | `expires_at`/`usable_until`은 producer가 선언한다. 현재 코드에는 공통 TTL이 없다. 이번 문서는 TTL을 정하지 않는다. |
| 원 stamp 신선도 | `Freshness.GREEN/YELLOW/RED` [S24] | Web 신선도와 같은 enum이 아니다. 임의 변환하지 않는다. |
| 입력 품질 후보 | 기존 `QualityState`의 `MISSING_DATA`, `STALE_DATA`, `CONFLICTING_SOURCE`, `PIT_UNAVAILABLE`, `IDENTIFIER_CHANGED`, `CALCULATION_ERROR`, `BLOCKED_DEPENDENCY`, `SYNTHETIC` 등 [S24] | 현 `TechnicalSnapshot`에 quality 필드는 없다. 새 sidecar에서 검토할 값이며 regime 이름으로 넣지 않는다. |
| coverage 후보 | `READY`, `PARTIAL`, `BLOCKED`, `SYNTHETIC` [S24] | 입력 준비 상태와 모델 검증 완료는 다르다. Technical snapshot에 현재 존재하는 필드로 가장하지 않는다. |
| 시세 시점 설명 | 지연·장중/최근 완료 session·원 가격시각·취득시각·미확인을 각각 표시 [S09] | `DELAYED/UNKNOWN`은 시세 메타데이터 설명이며 새 Web data state가 아니다. |

현재 producer 계약은 `NOT_AVAILABLE`에 data를 넣지 않으며 이유를 남긴다. synthetic는 DEMO로만 표시할 수 있고 연구/provisional 결과를 임의로 LIVE/FROZEN_SNAPSHOT에 게시할 수 없다. 기존 adapter는 직렬화만 하며 누락 필드를 채우거나 재점수하지 않는다. 이 원칙을 mock 계약 확인에 재사용하되 개인 결과를 public producer assembler/Pages bundle로 보내지 않는다. [S05] [S26]

### 6.3 Technical ≠ QGV

`qgv` 전달은 snapshot ID 참조를 보존하기 위한 것이며 Q/G/V 점수는 regime·zone 입력이 아니다. 기존 `TechnicalAdapter`는 Q/G/V 값의 변경을 검사한다. 첫 PR도 동일 QGV 입력의 불변성을 확인하고 score fusion은 만들지 않는다. [S02] [S27]

상위 시스템에서 QGV 기업 판단과 Technical 가격/실행 판단의 일치·충돌을 함께 보여주는 방향은 유지한다. 공식 Fusion 수식·스키마·명칭은 미확정이므로 J07의 요구를 새 점수로 구현하지 않는다. probability와 confidence도 서로 바꾸지 않는다. Portfolio의 하락 재검토 규칙을 자동 주문으로 연결하지 않으며 모든 실행 화면은 READ_ONLY다. [S07] [S18] [S22]

## 7. 결측·지연·차단 처리

| 상황 | 표시/처리 |
|---|---|
| 가격·원 통화·식별·basis가 없거나 충돌 | 계산 불가 이유와 `NOT_AVAILABLE`; 0·전일값·다른 상장·다른 공급자 series로 메우지 않는다. 실제 volume=0을 누락으로 바꾸지는 않는다. |
| 요청 window보다 짧은 history | 실제 관측 수와 부분 입력임을 보존한다. 기존 helper의 짧은 returns를 완전한 window나 검증된 모델 결과로 표시하지 않는다. 공식 충분성 gate가 미확정이면 Model 결과는 미제공이다. |
| null/배열 길이 불일치·중복/역순·비유한 가격·잘못된 OHLC·통화/심볼 충돌 | 입력 단계에서 거부하거나 해당 기능의 결측으로 분리한다. null bar를 삭제하고 앞뒤 날짜를 “연속 daily return”으로 이어 계산하지 않는다. |
| session 진행 중/종료 미확인 | 최근 확정 완료 session과 구분한다. completion 증거가 없으면 완료 종가 기반 Model 입력으로 채택하지 않는다. |
| delay 또는 가격시각 미확인 | 원 가격시각/`read_at`/delay 이유를 따로 표시한다. fetch 성공이나 취득시각만으로 FRESH·정확한 EOD를 주장하지 않는다. |
| `available_at`/최초 공개 시각·과거 vintage 없음 | `PIT_UNAVAILABLE` 또는 미검증 이유를 sidecar에 보존한다. 현재의 조정 history를 당시에도 알 수 있던 PIT history로 재생하지 않는다. [S28] |
| Google 검증 실패·다른 계정·tokeninfo 오류 | fail closed. 가격 upstream을 호출하지 않으며 원 토큰/검증 body를 로그에 남기지 않는다. |
| 공급자 허가 미확인·차단·cookie/crumb 요구·형식 변경·무료 한도 실패 | upstream 중단과 미제공 이유를 표시한다. 인증/프록시 회전·우회·무한 retry·자동 유료 전환을 하지 않는다. |
| 요청 취소·다른 회사 선택·화면 종료·로그아웃 | 진행 중 요청을 중단하고 해당 작업 RAM을 해제한다. 늦은 응답을 현재 회사 결과로 표시하거나 지속 저장하지 않는다. |

휴일/비거래일과 누락 거래 session은 다르다. 거래소별 calendar/session 증거가 없으면 timestamp 간격만으로 누락을 정상 휴일로 추정하지 않는다. 이 calendar와 세 시장의 finality/basis/event coverage는 후속 확인 항목이다. Google 시트·단일 수동 현재가를 받아도 일봉 역사·Research 지표·모델 regime의 결측은 해소되지 않는다. [S09] [S15]

## 8. mock-bar 검증 전략 — 이번 PR에서는 구현하지 않음

후속 첫 구현 PR은 외부 네트워크·실제 가격·계정 없이 synthetic bar만 사용한다. 실제 historical 파이프라인의 fetch·file track store·가격 outcome 저장을 호출하지 않는다. 테스트 산출물에는 실제 시세·토큰·이메일·키를 넣지 않는다.

| 검증 묶음 | 확인할 계약 |
|---|---|
| 정상 변환 | 순서·시각·식별·통화·선택 basis가 일치하는 완료 mock bars의 단순 수익률이 기존 `bars_to_returns`의 정상 입력 결과와 같고 마지막 20개 선택을 보존한다. 충분한 입력과 짧은 입력을 모두 다루며 새 계산 window를 만들지 않는다. |
| no-lookahead | 관측 시각이 cutoff 뒤인 bar를 계산에 쓰지 않는다. 별도로 mock 공개/가용 시각이 cutoff 뒤이면 PIT 확인을 통과시키지 않는다. 두 조건을 하나로 축약하지 않는다. |
| 결측/불량 | 빈 배열·단일 bar·null close·0/음수/비유한 가격·길이 불일치·중복/역순·잘못된 OHLC·심볼/통화 충돌을 확인한다. 실제 0 volume은 허용값과 결측을 구분한다. |
| basis·기업행사 | raw/adjusted 혼합·조정 배열 일부 누락·raw OHLC에 adjusted close만 치환·확인되지 않은 split/dividend 구간을 정상 검증으로 통과시키지 않는다. 알고리즘으로 행사 보정을 새로 구현하지 않는다. |
| 엔진 호환 | 기존 분기별 mock returns를 직접 넣은 결과와 어댑터 경유 결과의 regime·zone·scenarios·invalidation·drawdown_recheck·버전·synthetic를 비교한다. UUID snapshot ID는 같아야 하는 수치 결과로 비교하지 않는다. |
| QGV 경계 | Q/G/V와 원본 snapshot 필드가 어댑터 실행 전후 동일하고 참조 ID만 보존되는지 확인한다. Research 도구 선택을 모델 입력으로 전달하지 않는다. |
| 출력 부재 | 잘못된 입력이 `UNKNOWN/WAIT`의 정상 live 권고로 표시되지 않는지, mock는 synthetic/DEMO인지, `NOT_AVAILABLE`에는 정상 data가 없는지 확인한다. |
| 비보존·부작용 | 입력 모듈이 network/storage/public bundle 호출 없이 동작하고 mock runtime에서도 개인 가격·파생값·토큰을 persist/log하는 경로가 없는지 확인한다. |

토큰 검증·CORS·Workers Free 한도 테스트는 후속 Worker mock PR에서 한다. tokeninfo 성공/각 필드 누락·불일치/미검증 이메일·만료·오류·다른 계정, exact Origin과 거부 Origin, preflight, upstream 미호출, 무로그/무캐시를 mock로 확인한다. 실제 Google 로그인·토큰·Yahoo 호출을 mock 테스트의 완료 조건으로 삼지 않는다. 기기 port가 생기면 Python 참조와 동일 mock vectors의 호환성, 화면/종목 전환·취소·RAM 해제와 모바일 표시를 확인한다. 수치 허용오차·연산 변경이 필요하면 별도 검토하며 이번 문서에서 새 기준을 만들지 않는다.

## 9. 단계별 작업 계획과 첫 구현 PR 제안

| 단계 | 결과물 | 다음 단계 조건 |
|---|---|---|
| 문서 단계 — 현재 | 이 설계, 근거·미정 항목·mock 전략, 구체 첫 PR 제안 | 문서 PR은 별도 승인 전까지 병합 대기. 문서 병합만으로 구현·수집·배포를 승인하지 않는다. |
| 첫 구현 후보 | network/storage 없는 daily-bar 검증·기존 returns 입력 어댑터와 mock 계약 검사 | 입력 basis/time/missing/불변성·기존 engine shape 확인. 모델·provider 활성화 없음. |
| 모델/방법론 복원 검토 | 기존 Technical 원 개발 패키지/공식 지표·period·warm-up·TSV·regime·scenario·검증 근거와 현재 placeholder의 대조 | 누락 코드를 관례적 새 지표로 대체하지 않는다. 복원 근거와 변경 범위를 별도 확인한다. |
| 기기 runtime 후보 | 승인된 기존 계약을 실행할 browser 구현·Python mock 호환 근거·개인 RAM lifecycle | 현재 Python/Node 실험을 그대로 사용하지 않는다. public producer 경로에 연결하지 않는다. |
| Worker/auth mock 후보 | Workers Free·GSQ-008 인증·exact CORS·allowlist·fail closed·무저장·무로그 | 실제 가입/배포/인증 호출은 별도 승인 범위. 비용 0·카드 없음이 충족되지 않으면 중단한다. |
| 공급자 적합성·제한 실증 후보 | 공급자 허가·무료 entitlement·심볼/통화·완료 session·history/basis/event 확인 및 별도 승인된 최소 검증 | Yahoo 무허가 자동 조회 부적합 판정을 유지한다. 대체 출처도 권리·범위를 확인하기 전 활성화하지 않는다. |
| 개인 화면 연결 후보 | S08과 S04/S05/홈의 실제 가용 정보·미제공 표시 | 지표/모델·PIT/OOS/calibration 완료를 별개로 관리한다. 확률 fan·장기 Track Record는 무저장 정책과 근거 확보가 충돌하므로 별도 보존 정책 결정 없이는 보류한다. |

**첫 구현 PR 제목 제안:** `Technical: mock 일봉 검증과 기존 returns 입력 어댑터`

**목적:** 공급자와 runtime을 활성화하기 전에, 동일 basis의 검증된 일봉을 기존 `TechnicalEngine.evaluate` 입력으로 옮기는 경계를 재현 가능하게 만든다.

**제안 write-set(아직 생성하지 않음):**

- `implementation/src/investment_system/technical/daily_input.py` 신규: 개인/mocked daily-bar 입력의 검증·시리즈 basis/time/식별 검사와 returns 준비. `PricePoint`/`DataStamp`에 없는 역사 metadata는 별도 제안 타입으로 보존하고 현 shared 계약을 몰래 바꾸지 않는다.
- `implementation/tests/test_technical_daily_input.py` 신규: 위 mock-bar 사례, 정상 변환의 기존 helper 호환성, engine output shape·placeholder·QGV 불변성 검사. `TechnicalEngine`를 injected dependency로 사용할 수 있게 해 입력 오류 때 호출되지 않는지도 확인한다.
- `implementation/docs/technical_live_data/`의 후속 scoped README/검증 기록: fixture가 합성임을 명시하고 모델/실데이터/runtime 미완료 경계를 기록한다. 실제 가격이나 개인 입력은 담지 않는다.

**기존 계약 재사용:** `TechnicalEngine.evaluate`와 `TechnicalSnapshot`의 필드/enum/버전, `validation/historical.py::bars_to_returns`의 정상 입력 수익률과 마지막 20개 선택, `TechnicalAdapter`의 QGV 불변성 의미를 사용한다. historical helper는 검증 없이 입력 순서를 신뢰하고 null을 삭제한 시리즈의 gap을 식별하지 못하므로, 오류 입력을 수리·보간한 뒤 helper에 넘기는 방식은 쓰지 않는다. 새 input 준비 단계에서 거부/미제공 이유를 보존한다. [S02] [S03] [S13] [S27]

**PR의 완료 조건:** 제안 어댑터의 meaningful mock 사례와 기존 Technical 관련 영향 범위 검사가 통과하고, engine 코드·기존 수치 분기·scenario placeholder·QGV 점수·provider/공개 bundle·운영 모드가 바뀌지 않는다. 브라우저/Worker 실행 가능·실데이터 적격·공식 모델 완료를 주장하지 않는다. 모든 후속 PR은 별도 review·승인·병합 대기로 제안한다.

## 10. UNKNOWN / DEFERRED 목록

공식 Model Indicator Set·개별 산식/period/warm-up, TSV·regime 복원 근거, 모델 입력 충분성 기준, scenario 생성/확률·confidence/calibration, Fusion 출력 계약은 미확정이다. 세 시장 history 길이·거래 calendar·session finality·기업행사/조정 정책·최초 가용 시각/vintage, provider 접근 허가·실제 무료 entitlement, browser engine 실행과 Workers Free CPU/body/인증 동작도 미확인이다. [S07] [S08] [S18]

무저장 가격 정책에서는 과거 가격 PIT replay·가격 기반 immutable 예측/forward path·장기 calibration Track Record의 완전한 재현을 제공할 수 있다고 말하지 않는다. 가격/파생값을 보존하는 새 정책·권리와 공식 검증 근거가 필요한 항목은 별도 결정까지 보류한다. 현재 가능한 입력 계약 작업과 미래 모델/검증 기능을 같은 완료율로 합치지 않는다.

## 근거 — canonical 고정 permalink

아래 모든 코드·문서 링크는 **`12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df`**의 내용과 행 번호를 가리킨다. 문서 안에 기록된 더 오래된 canonical·PASS는 당시 이력이며 현재 구현 인증으로 확대하지 않는다.

| 참조 | 정확한 repository 경로 | 행 anchor |
|---|---|---|
| [S01] | `Technical Analysis System · Latest Status Update 2026-09-22.md` | L5–L40 |
| [S02] | `implementation/src/investment_system/technical/engine.py` | L17–L64 |
| [S03] | `implementation/src/investment_system/validation/historical.py` | L28–L56 |
| [S04] | `implementation/src/investment_system/producers/registry.py` | L91–L100 |
| [S05] | `implementation/src/investment_system/producers/adapters.py` | L1–L5, L15–L65 |
| [S06] | `implementation/experiments/chart-contract-v0.1/CHART_INVENTORY.md` | L7–L17, L31–L47, L144–L152 |
| [S07] | `Technical Analysis · Decision History v0.1.md` | L9–L18, L59–L76 |
| [S08] | `implementation/docs/daily_data_pipeline/PRIVATE_FREE_PRICE_PATH_RESEARCH.md` | L8–L46, L48–L111, L144–L162 |
| [S09] | `implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md` | L177–L221 |
| [S10] | `implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md` | L224–L248 |
| [S11] | `implementation/src/investment_system/product/web_assets/google-sheet-quotes.js` | L8–L15, L43–L54, L87–L127 |
| [S12] | `implementation/src/investment_system/providers/base.py` | L11–L23 |
| [S13] | `implementation/src/investment_system/contracts/models.py` | L34–L53, L135–L152 |
| [S13R] | `implementation/src/investment_system/contracts/raw.py` | L59–L64 |
| [S14] | `implementation/src/investment_system/providers/yahoo_chart.py` | L22–L73, L86–L98 |
| [S15] | `implementation/docs/daily_data_pipeline/PRIVATE_FREE_PRICE_PATH_RESEARCH.md` | L80–L91, L120–L142 |
| [S16] | `QGV Leaderboard · Specification v1.0.md` | L120–L140 |
| [S17] | `implementation/src/investment_system/contracts/strategy.py` | L1–L5, L87–L113 |
| [S18] | `Technical Analysis System · Consolidated Record v0.1.md` | L26–L54, L56–L115, L147–L161 |
| [S19] | `implementation/experiments/chart-contract-v0.1/contract.mjs` | L1–L2, L23–L27, L42–L89, L110–L140 |
| [S20] | `implementation/src/investment_system/product/web_mvp.py` | L1–L18, L39–L63 |
| [S21] | `implementation/experiments/chart-contract-v0.1/package.json` | L2–L17 |
| [S22] | `implementation/docs/frontend_ia_v1/COCKPIT_IA_v1.md` | L9–L20, L26–L45, L51–L68, L82–L102 |
| [S23] | `implementation/src/investment_system/versions.py` | L1–L14 |
| [S24] | `implementation/src/investment_system/contracts/enums.py` | L4–L30, L58–L70 |
| [S25] | `implementation/src/investment_system/producers/freshness.py` | L1–L8, L26–L40 |
| [S26] | `implementation/src/investment_system/producers/contract.py` | L1–L6, L108–L117, L142–L146, L189–L203 |
| [S27] | `implementation/src/investment_system/validation/adapters.py` | L21–L30 |
| [S28] | `implementation/src/investment_system/pit/resolver.py` | L1–L4, L21–L30 |

[S01]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/Technical%20Analysis%20System%20%C2%B7%20Latest%20Status%20Update%202026-09-22.md#L5-L40
[S02]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/technical/engine.py#L17-L64
[S03]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/validation/historical.py#L28-L56
[S04]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/producers/registry.py#L91-L100
[S05]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/producers/adapters.py#L1-L65
[S06]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/experiments/chart-contract-v0.1/CHART_INVENTORY.md#L7-L152
[S07]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/Technical%20Analysis%20%C2%B7%20Decision%20History%20v0.1.md#L9-L76
[S08]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/daily_data_pipeline/PRIVATE_FREE_PRICE_PATH_RESEARCH.md#L8-L162
[S09]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md#L177-L221
[S10]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md#L224-L248
[S11]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/product/web_assets/google-sheet-quotes.js#L8-L127
[S12]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/providers/base.py#L11-L23
[S13]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/contracts/models.py#L34-L152
[S13R]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/contracts/raw.py#L59-L64
[S14]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/providers/yahoo_chart.py#L22-L98
[S15]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/daily_data_pipeline/PRIVATE_FREE_PRICE_PATH_RESEARCH.md#L80-L142
[S16]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/QGV%20Leaderboard%20%C2%B7%20Specification%20v1.0.md#L120-L140
[S17]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/contracts/strategy.py#L1-L113
[S18]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/Technical%20Analysis%20System%20%C2%B7%20Consolidated%20Record%20v0.1.md#L26-L161
[S19]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/experiments/chart-contract-v0.1/contract.mjs#L1-L140
[S20]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/product/web_mvp.py#L1-L63
[S21]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/experiments/chart-contract-v0.1/package.json#L2-L17
[S22]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/docs/frontend_ia_v1/COCKPIT_IA_v1.md#L9-L102
[S23]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/versions.py#L1-L14
[S24]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/contracts/enums.py#L4-L70
[S25]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/producers/freshness.py#L1-L40
[S26]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/producers/contract.py#L1-L203
[S27]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/validation/adapters.py#L21-L30
[S28]: https://github.com/kco994553-star/Investment-System1/blob/12b5cbcbc52ce8af5bd22a9abf1c4722cd4b53df/implementation/src/investment_system/pit/resolver.py#L1-L30
