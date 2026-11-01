# Alpaca SIP 소표본 1회 측정 계획 (2026-11-01)

근거: 오너 2026-11-01 결정 2항("기존 Alpaca SIP 원본의 재사용 가능 범위와 이용 조건을 먼저 확인하라. 그다음 소표본 수집만 승인한다. 대량 수집은 그 결과를 본 뒤 정한다."). 첫 단계(기존 원본 범위·약관 확인)는 끝났다: 비공개 release `bt-data-pilot-v06-long-41168930483-1`, 10개 회사, 2016-01-04~2026-10-30 일봉, 상장폐지 AE·IDSA 포함. 연구: EXP-STOCK-INDICATOR-DECILES-v1(설정 문서 5·6.2·7절).

- 도구: `implementation/tools/measure_once/alpaca_sample_once.py`
- 시험: `implementation/tests/test_alpaca_sample_once.py`(가짜 응답만, 네트워크 없음)
- 1회 워크플로: `.github/workflows/alpaca-sample-once.yml`

## 1. 목적

대량 수집을 정하기 전에, Alpaca SIP 일봉이 전체 역사 후보(U-A·U-B)에 필요한 것을 줄 수 있는지 잰다.

| 필요한 것 | 날짜 |
| --- | --- |
| T 시가(통합 시가) | 2016-02-16, 2017-02-21, 2018-02-20, 2019-02-19 |
| S 종가 | 2016-02-12, 2017-02-17, 2018-02-16, 2019-02-15 |
| 월말 종가 | 2016-02 ~ 2017-01, 2017-02 ~ 2018-01(2016·2017 최초 구간 후보의 보유 기간), 2018-02 ~ 2019-02(대상 구간): 37개, 각 달의 마지막 NYSE 거래일(시험에서 `pit_filings.is_session`과 대조) |
| 어려운 경우 | 상장폐지·인수, 티커 변경, 기호 재사용, 종류주, ADR, REIT, 소형주, 기간 중 상장 |

- 2016년(T = 2016-02-16)은 최초 구간 후보라서 함께 잰다(설정 문서 6.2절). 월말 추가는 이미 받는 봉의 요약일 뿐, 요청은 늘지 않는다.
- 가중치·선정·성과는 보지 않는다. 결과는 자료 확보 가능 여부만 말한다.
- **SPY 분배금 원천은 이 실행으로 정하지 않는다.** 봉(`adjustment=raw`)에는 분배금이 없고, 이 실행은 분배금용 요청을 하지 않는다. SPY는 가격 원천 확인용이다. 분배금 원천(후보: Alpaca 기업 행위 자료, 발행사 분배 공시)은 이 측정 밖에서 따로 정한다.

## 2. 표본 (40종목, 10범주)

공개 사건으로 고른다. 가격·성과로 고르지 않는다. 각 항목에 공개 사건과 날짜, 확인 정도(WEB_CHECKED 공개 출처 발췌 확인 / RECALL 널리 알려진 사실, 재확인 안 함 / UNVERIFIED 실행 전 Main 확인)를 도구 안에 적었다.

구간(leg) 끝 규칙: `end` = 그 기호로 **더 이상 거래되지 않은 첫날**(배타적). 개장 전 효력 인수(EMC·WFM·MON·DNB)는 효력일, 장 마감 뒤 효력(DOW·TWX)은 다음 거래일, 개장부터 정지(SHPG)는 정지일, 이름 변경은 새 기호의 첫날. 그래서 마지막 봉은 `end` 바로 전 거래일이다(EVENT 차이 −1, 주말이면 −3, 연휴가 끼면 −4). 시험이 모든 기간 안 끝·시작일이 거래일인지 확인한다.

| 범주 | 종목 (요청 기호) | 무엇을 보나 |
| --- | --- | --- |
| CONTROL_LARGE | AAPL, MSFT | 기준(빠짐 없는지, 휴장일 기준표) |
| ETF_AUX | SPY | "ETF 보조 비교"용 가격(분배금은 이 실행 밖) |
| DELISTED_ACQUIRED | EMC(end 2016-09-07), WFM(2017-08-28), DOW(마지막 거래 2017-08-31 장 마감, end 2017-09-01; 2019년 Dow Inc.가 기호 재사용), MON(2018-06-07), TWX(마지막 거래 2018-06-14, end 2018-06-15), DNB(2019-02-08 개장 전 거래 중단, 마지막 2019-02-07; 2020년 기호 재사용), 21CF: FOXA(마지막 2019-03-18) → TFCFA(2019-03-19 하루, 2019-03-20 인수 효력; 같은 날부터 새 Fox가 FOXA 사용) | 마지막 거래일까지 자료가 있는지, 재사용 기호가 섞이는지 |
| DELISTED_OTHER | SUNE(2016-04-21 거래정지), BTU(2016-04-13 정지 → 2017-04-04 같은 기호로 새 주식 재상장, 이름 변경 없음), SHLD(2018-10-24 개장부터 정지), WIN(2019-03-06 Nasdaq 정지·상장폐지) | 파산·상장폐지 직전까지 있는지 |
| TICKER_CHANGE | PCLN→BKNG(2018-02-27), YHOO→AABA(2017-06-19, 투자회사로 종류 변경), DPS→KDP(2018-07-10), VRX→BHC(2018-07-16), FB→META(2022-06-09, 기간 뒤) | 옛 기호·새 기호 중 어느 쪽이 어느 기간을 주는지 |
| MULTI_CLASS | GOOGL·GOOG, BRK.A(점 표기 UNVERIFIED)·BRK.B(점 표기: Alpaca 포럼 직원 답변만), Under Armour A(UA→UAA)·C(UA.C→UA, 2016-12-07 기호 맞바꿈; UA.C 첫 거래일 2016-04-08은 10-K로 확인, Alpaca의 UA.C 표기는 UNVERIFIED) | 종류별로 따로 받는지 |
| ADR | BABA, TSM, SHPG(런던 주식 정지로 2019-01-07 개장부터 ADS 정지, 마지막 정규 거래 2019-01-04, 계획 효력 2019-01-08) | ADR 자료와 인수 뒤 끝 |
| REIT | O, PLD, DCT(2018-08-22 인수) | REIT 자료와 인수 뒤 끝 |
| SMALL_CAP | KIRK(2018-02 무렵 약 USD 170m-210m), LCUT(약 USD 205m, 2018-03-02 주식 발행 뒤 약 USD 280m), BGFV(2018-02 무렵 약 USD 130m-170m, T2017 무렵 약 USD 285m-380m), RT(T2017 무렵 약 USD 110m-225m, 2017-12-21 인수) | 소형주. 미리 정한 시총 구간으로 고르지 않았다. SEC 10-K(주식 수 × 분기 가격 범위)로 본 수준은 대략 USD 100m-400m, $250m 진입선 아래 또는 근처 |
| IPO_IN_WINDOW | TWLO(2016-06-23), SNAP(2017-03-02), DBX(2018-03-23), SPOT(2018-04-03 직접상장), LYFT(2019-03-29 = 기간 마지막 거래일) | 첫 거래일부터 있는지 |

리뷰 사실 확인으로 고친 것: DOW·TWX 마지막 거래일(효력일 당일), 21CF의 TFCFA 하루(구간·요청 추가), SHPG 마지막 정규 거래일, DNB 마지막 거래일, UA.C 첫 거래일, 소형주 시총 수준과 범주 이름(구간 주장 없는 SMALL_CAP). KIRK(2025년 TBHC로 이름 변경, 2026년 합병)·BGFV(2025-10-02 상장폐지)는 기간 뒤 변화가 있고 이 측정은 그 기호로 `asof=-`만 받는다.

**UNVERIFIED 3개**: MC03 Alpaca의 BRK.A 점 표기(과거 봉), MC06 Alpaca의 UA.C 점 표기, SC04 RT가 2017-12-21에 거래됐는지(그래서 RT END 차이는 0 또는 −1).

종류주 접미 기호(BRK.A, BRK.B, UA.C)가 NO_DATA나 ERR_HTTP400이면 "**기호 표기를 모르거나 봉이 없음**"으로 읽는다. "Alpaca에 그 종류 자료가 없다"로 읽지 않는다. UA.C는 MC06의 날짜 asof UA 요청(2016-12-07 이름 변경을 거꾸로 따라감)이 따로 확인한다. 이 경우 MC06 계보 코드는 MISSING_SYMBOL이다(2016-12-07 전 UA 봉은 MC05 A주의 기호 재사용이라 CURRENT_SYMBOL_ONLY로 세지 않는다).

## 3. 요청

- 주소: `https://data.alpaca.markets/v2/stocks/{기호}/bars`, `timeframe=1Day`, `adjustment=raw`, `feed=sip`, 2016-01-01 ~ 2019-03-31(뉴욕 시각), `limit=10000`, `sort=asc`.
- **67개 요청**(쪽 넘김이 없으면 67회): 기호 47개 × `asof=-`(그 기호로 거래된 봉만) + 계보 확인 20개.
  - `asof=<그 종목이 상장돼 있던 날>` 11개: 그 날의 발행사를 이름 변경을 따라가며 받는지(PCLN·YHOO·DPS·VRX·FB·DOW·FOXA·BTU 2개·UA 2개).
  - `asof=2026-10-30` 9개: 지금 기호(BKNG·KDP·BHC·META·UAA·UA·BTU)가 옛 기간을 주는지, 재사용 기호(DOW·FOXA)가 옛 회사를 섞는지.
  - BTU 날짜 요청은 그 날 상장돼 있던 주식만 기대한다(2016-02-16 → 옛 Peabody, 2018-02-20과 현재 → 새 Peabody). 옛·새 주식은 이름 변경 없는 다른 주식이다.
- Alpaca 문서: asof가 그 날 기호를 찾지 못하면 기호 그대로의 자료를 준다(`asof=-`와 같음). 그래서 모든 asof 결과를 **같은 기호의 `asof=-` 결과와 비교**한다. 날짜 비교는 공개, 값 비교는 비공개(4절).
- 요청 전 고정 대기 0.6초 → 분당 100회 이하(무료 한도 200). 재시도 상한(5xx·연결 2회, 429 3회), 재시도 대기는 남은 시간을 넘지 않는다. 401·403이면 즉시 멈춤, 전체 요청 150회·수집 9분 상한. 키는 Actions Secret `APCA_API_KEY_ID`·`APCA_API_SECRET_KEY`에서만 읽고 출력하지 않는다.
- 주소 허용 목록은 정확히 위 형식과 계획된 기호·asof 조합뿐이다. 넘겨주기(redirect)는 거절한다.

## 4. 출력

이 저장소는 공개라서 Actions 기록도 공개다. 출력은 두 가지로 나뉜다.

### 4.1 공개 Actions 기록: 있음·없음과 날짜만

도구의 `LINE_SPECS` 허용표에 있는 줄 종류·키 순서·값 형식만 찍는다(`checked_line`이 나머지를 거절). 값은 고정 코드 목록, 범위가 정해진 작은 정수(개수, 일수 차이), 고정 체크포인트·사건 날짜, release 태그뿐이다. 내용은 **어떤 날에 봉이 있는지(값이 이상한 봉도 봉으로 센다), 그런 날의 개수, 같은 실행의 다른 계열과 날짜 집합 비교, 첫·끝 봉과 공개 사건 날짜의 일수 차이**뿐이다. 가격·거래량·수익률·값 비교(같은 봉/다른 봉)·값 유효성(OK/BAD)·종목별 봉 개수·키·토큰·주소·응답 본문·예외 문구는 찍지 않는다. 소수점 숫자도 없다.

| 줄 | 키(순서대로) |
| --- | --- |
| `ALPSAMPLE_START` | securities symbols series categories window feed adjustment timeframe max_requests pace_ms release |
| `ALPSAMPLE_SERIES` | id sid cat mode expect status fit first last gaps t_bar s_bar monthend monthend_2016w monthend_2017w days_vs_raw echo |
| `ALPSAMPLE_EVENT` | sid cat sym event event_day bar_vs_event_days |
| `ALPSAMPLE_LINEAGE` | sid cat raw asof_pit asof_current common_days |
| `ALPSAMPLE_CLASSES` | pair days |
| `ALPSAMPLE_CATEGORY` | cat securities symbols symbols_with_data symbols_no_data symbols_error t_bar t_unexpected s_bar s_unexpected monthend monthend_unexpected monthend_2016w monthend_2016w_unexpected monthend_2017w monthend_2017w_unexpected complete gapless |
| `ALPSAMPLE_CHECKPOINT` | cp day field expected bar missing error unexpected (T 4, S 4, 월말 37 = 45줄) |
| `ALPSAMPLE_REQUESTS` | series series_done total pages retries http400 http401 http403 http404 http422 http429 http5xx http_other network elapsed_s stopped |
| `ALPSAMPLE_STORAGE` | status release files roundtrip retries / 실패 시 status code retries |
| `ALPSAMPLE_STOP` | reason (예상 밖 오류는 reason class: 예외 클래스 이름만) |

- `t_bar`·`s_bar`·월말 상태: BAR(봉 있음)·MISS·UNEXP(기대 밖 봉)·-·ERR. 월말은 FULL·PARTIAL·NONE·NA(+UNEXP).
- `days_vs_raw`(asof 계열만): 같은 기호 `asof=-` 계열과 날짜 집합 비교 SAME_DAYS·FEWER_DAYS·MORE_DAYS·OTHER_DAYS. SAME_DAYS면 날짜로는 대응(mapping)이 보이지 않는다.
- `common_days`(계보), `days`(종류주): 두 기호가 같은 날 봉을 갖는지(날짜만).
- `--plan`의 `ALPSAMPLE_PLAN`·`ALPSAMPLE_PLAN_CATEGORY`도 같은 허용표를 지난다.

### 4.2 비공개 manifest에만: 값 비교 코드

가격 값을 비교하거나 검사해서 나온 코드는 RAM에서 계산해 비공개 release의 manifest `private_lines`에만 넣고 찍지 않는다.

- `ALPSAMPLE_PRIVATE_ASOF id vs_raw legs_vs_raw`: asof 계열이 같은 기호 `asof=-` 계열과 날짜·값까지 같으면 **SAME_AS_RAW = 대응이 보이지 않음**(Alpaca가 기호 그대로 답함), 다르면 DIFFERS. `legs_vs_raw`는 기대 구간마다 그 구간 기호의 `asof=-` 봉과 비교(SAME_BARS·DIFFERENT_BARS·PARTLY_SAME·SAME_ON_COMMON_DAYS·NO_ASOF_BARS·NO_RAW_BARS). Under Armour 맞바꿈: 2016-02-16 asof UA가 A주를 따라가면 `SAME_BARS,SAME_BARS`(2016-12-07부터 UAA와 같음), 기호 그대로면 `SAME_BARS,DIFFERENT_BARS`(2016-12-07부터 C주). MC06 날짜 UA 요청은 2016-12-07 전 봉을 UA.C와 비교한다.
- `ALPSAMPLE_PRIVATE_SERIES`: T 시가·S 종가·월말의 값 유효성(OK·BAD), 값이 이상한 봉 수.
- `ALPSAMPLE_PRIVATE_LINEAGE`·`ALPSAMPLE_PRIVATE_CLASSES`: 이어지는 기호·종류주 두 기호의 봉 값이 같은지.
- `ALPSAMPLE_PRIVATE_CHECKPOINT`: 체크포인트별 OK·BAD 수.

비공개 코드는 Main이 바로 읽을 수 없다(raw 저장소 토큰은 Secret에만 있음). 읽으려면 별도로 승인된 읽기 워크플로가 필요하고, 이 실행에는 들어 있지 않다.

## 5. 저장 (비공개만)

- 응답 원본 바이트 그대로 + 파일별 sha256 manifest를 메모리에서 zip으로 묶어, 비공개 raw 저장소의 **새 release `alpaca-sample-v1-<run_id>`** 에만 올린다(Secret `RAW_REPO_TOKEN`, 설정 문서 6.3절의 기존 승인 경로).
- 코드로 제한: 저장소가 비공개인지와 그 이름의 release가 없는지를 Alpaca 요청 전에 확인하고, **만들기 직전에 둘 다 다시 확인**한다(있으면 멈춤, 재사용 안 함). 만든 뒤에는 만든 release id로 올리기와 이번 실행이 올린 asset id 내려받기만 허용한다. 다른 release는 목록·읽기·수정·삭제하지 않는다. KIS release는 건드리지 않는다. 올린 뒤 내려받아 sha256을 대조한다.
- 일시 오류 대비: GitHub 호출마다 짧은 제한 시간(60초), 저장 전체 5분·사전 확인 2분 30초 예산, 5xx·연결 오류는 호출마다 최대 2회 재시도(대기는 남은 예산 안). release 만들기 응답만 잃은 경우에는 태그를 다시 조회해, 이번 실행이 만든 빈 release(asset 없음)일 때만 이어서 쓴다.
- 그래도 저장이 실패하면 자료는 RAM에만 있었으므로 사라진다. 다시 받으려면 새 push로 두 번째 수집을 해야 하고, 이는 오너 확인이 필요하다.
- 공개 저장소·Pages·Actions 산출물에는 아무것도 남기지 않는다(업로드·캐시·요약 없음).

## 6. 약관

Alpaca 약관은 개인·비상업 사용만 허용하고, 공개 게시는 사전 서면 동의가 필요하다. 가격 없는 파생 결과의 공개 가능 여부는 확인되지 않았다(서면 확인 필요). 그래서 가격·값 비교에서 나온 것은 공개 기록에 하나도 두지 않고(4.2절, 비공개 release에만), 공개 Actions 기록에는 4.1절의 있음·없음·개수·날짜 차이 줄만 남는다. **이 줄들이 공개 Actions 기록에 나와도 되는지 실행 전에 오너가 확인한다.**

## 7. 결과로 정할 것 (실행 전에 고정한 읽기 규칙)

판정은 공개 줄로 범주마다 GO 또는 OTHER_SOURCE(그 범주만 다른 원천 목록)로 적는다. 대량 수집 여부는 이 결과를 보고 **오너가** 정한다. 아래 예외는 미리 이름을 붙인 것뿐이고, 결과를 본 뒤 기준을 바꾸지 않는다.

공통 기준(범주 안 모든 종목):
- C1. 기대되는 T·S·월말 체크포인트가 모두 BAR(CATEGORY의 `t_bar`·`s_bar`·`monthend`·`monthend_2016w`·`monthend_2017w`가 모두 x/x, `*_unexpected`=0).
- C2. 모든 END·RENAME_OUT 차이가 −4 ~ 0(기대는 `end` 바로 전 거래일: −1, 주말 −3, 연휴 −4), 모든 START·RENAME_IN·RELIST 차이가 0. NONE·ERR 없음. 0은 빈 곳이 아니라 `end` 당일에도 봉이 있다는 뜻이라 GO를 막지 않고, 종목을 적어 날짜를 다시 확인한다(마지막 거래일을 재확인하지 않은 RT·DCT·EMC·WFM 등).
- C3. 받은 구간 안에 빠진 거래일 없음(`gapless` x/x).
- 미리 정한 예상값: AD03 SHPG END −3(2019-01-07 정지일 기준), SC04 RT END 0 또는 −1(UNVERIFIED), IP05 LYFT START 0(첫날 = 기간 마지막 거래일).

범주별:
1. **CONTROL_LARGE·ETF_AUX**: C1~C3 모두. 하나라도 어기면 원천 또는 실행 자체를 의심해 **전체 판단을 보류**한다.
2. **DELISTED_ACQUIRED·DELISTED_OTHER**: C1~C3. 21CF는 FOXA RENAME_OUT −1, TFCFA RENAME_IN 0, TFCFA END −1이어야 마지막 거래일까지 있다고 본다. BTU는 END −1, RELIST 0.
3. **TICKER_CHANGE**: 기간 안 4개(TC01~TC04)가 C1·C2를 만족하고 LINEAGE `raw=PIT_SYMBOLS`이면 GO(`asof=-` 시점 기호 방식). CURRENT_SYMBOL_ONLY·MISSING_SYMBOL이 있으면 그 종목을 적고 8번 요청 방식 판단으로 넘긴다.
4. **MULTI_CLASS**: 각 종류 기호가 DATA이고 C1, CLASSES `days`가 GOOGL+GOOG·BRK.A+BRK.B에서 SAME_DAYS. 종류주 접미 기호의 NO_DATA는 "기호 표기를 모르거나 봉이 없음"으로 적고 표기 확인 목록에 올린다(그 자체로 Alpaca에 자료가 없다고 판단하지 않는다).
5. **ADR·REIT·SMALL_CAP·IPO_IN_WINDOW**: C1~C3.
6. **대량 수집 계획 PR 제안 조건**: 1번이 GO일 때만. OTHER_SOURCE 범주는 그 범주만 다른 원천을 찾는다.
7. **표본의 한계**: 40개는 범주마다 3~7개를 사건으로 고른 것이라 **행동을 보여줄 뿐, 긴 꼬리(작은 상장폐지 종목들)의 확보율을 추정할 수 없다.** 대량 수집을 하게 되면 종목별 확보 여부를 따로 보고해야 한다.
8. **요청 방식**(티커 변경·재사용): asof 계열마다 공개 `fit`·`days_vs_raw`와 비공개 `vs_raw`·`legs_vs_raw`로 읽는다.
   - 대응을 따라감: 비공개 `vs_raw=DIFFERS`이고 `legs_vs_raw`가 모두 SAME_BARS(또는 공개 `fit=MATCH`이고 `days_vs_raw`가 SAME_DAYS가 아님).
   - 대응이 보이지 않음: 비공개 `vs_raw=SAME_AS_RAW`(공개만으로는 `days_vs_raw=SAME_DAYS`에 PARTIAL·+OUTSIDE).
   - Under Armour A주(2016-02-16 asof UA)는 날짜가 같아서 공개 줄로는 구별되지 않는다. 비공개 `legs_vs_raw`로만 구별된다.
   - BTU: Alpaca 대응은 이름 변경을 따라가는데 BTU는 이름 변경이 없으므로 SAME_AS_RAW(공개 MATCH+OUTSIDE)가 예상 답이고 대응이 없다는 증거가 아니다. 공개 `fit=MATCH`에 FEWER_DAYS가 나와야 옛·새 주식을 나눈다고 본다.
   - `asof` 방식은 TC01~TC04의 날짜 요청이 모두 대응을 따라갈 때만 대량 수집 후보로 둔다. 비공개 코드가 필요한 판단은 4.2절의 별도 읽기 워크플로가 승인된 뒤에 한다.
9. **2016년 최초 구간**: 2016-02-12 종가, 2016-02-16 시가, 2016-02 ~ 2017-01 월말이 C1을 만족하는지(CHECKPOINT `S2016`·`T2016`·`ME201602`~`ME201701`, CATEGORY `monthend_2016w`).
10. **SPY 분배금**: 이 실행은 정하지 않는다(1절).

## 8. IEX 마지막 체결가

IEX 마지막 체결가 방식은 **같은 표본·같은 조건 측정을 한 뒤에만 별도 변형으로 제안**할 수 있다. 이 측정은 SIP 통합 시가만 잰다. IEX와 차이가 작다고 단정하지 않는다.

## 9. 실행 전 Main 확인

- UNVERIFIED 3개(2절).
- 오너 확인: 4.1절의 공개 줄(있음·없음·개수·날짜 차이)이 공개 Actions 기록에 나와도 되는지(6절).
- Secret 세 개(`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `RAW_REPO_TOKEN`)가 공개 저장소 Actions에 있는지(Codex 워크플로가 이미 같은 이름을 씀).
- 워크플로 모양: 오프라인 시험은 Secret 없는 별도 job(`offline`, `pytest -q --tb=no -rN -p no:warnings`: 실패해도 통과·실패 표시와 개수만 찍힘), Secret을 가진 `measure` job은 `needs: offline`이고 pip를 돌리지 않은 새 실행기에서 `python -I -S`로 표준 라이브러리만 쓰는 도구를 돌린다. 단계 제한 20분(수집 9분 + 사전 확인·저장 예산), job 25분.
- 실행: 승인된 커밋을 `claude/alpaca-sample-once-run` 가지로 한 번 push → 워크플로 1회 → 결과 줄을 읽은 뒤 가지 삭제. 다른 가지·PR·일정·수동 실행으로는 돌지 않는다.
- `--plan`으로 네트워크 없이 요청 수를 다시 볼 수 있다(`python implementation/tools/measure_once/alpaca_sample_once.py --plan`).
