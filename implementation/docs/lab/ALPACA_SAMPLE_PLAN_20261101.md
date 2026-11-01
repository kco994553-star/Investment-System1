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
| 월말 종가 | 2018-02 ~ 2019-02 (13개) |
| 어려운 경우 | 상장폐지·인수, 티커 변경, 기호 재사용, 종류주, ADR, REIT, 소형주, 기간 중 상장 |

- 2016년(T = 2016-02-16)은 최초 구간 후보라서 함께 잰다(설정 문서 6.2절).
- 가중치·선정·성과는 보지 않는다. 결과는 자료 확보 가능 여부만 말한다.

## 2. 표본 (40종목, 10범주)

규칙으로 고른다. 가격·성과로 고르지 않는다. 각 항목에 공개 사건과 날짜, 확인 정도(WEB_CHECKED 공개 출처 발췌 확인 / RECALL 널리 알려진 사실, 재확인 안 함 / UNVERIFIED 실행 전 Main 확인)를 도구 안에 적었다.

| 범주 | 종목 (요청 기호) | 무엇을 보나 |
| --- | --- | --- |
| CONTROL_LARGE | AAPL, MSFT | 기준(빠짐 없는지, 휴장일 기준표) |
| ETF_AUX | SPY | "ETF 보조 비교"용 가격(분배금은 별도 원천) |
| DELISTED_ACQUIRED | EMC(2016-09-07), WFM(2017-08-28), DOW(2017-08-31, 2019년 다른 회사가 기호 재사용), MON(2018-06-07), TWX(2018-06-14), DNB(2019-02-08, UNVERIFIED), FOXA(2019-03-19 새 Fox가 기호 사용, UNVERIFIED) | 마지막 거래일까지 자료가 있는지, 재사용 기호가 섞이는지 |
| DELISTED_OTHER | SUNE(2016-04-21 거래정지), BTU(2016-04-13 정지 → 2017-04-04 같은 기호로 재상장), SHLD(2018-10-24 Nasdaq 상장폐지), WIN(2019-03-06 Nasdaq 상장폐지) | 파산·상장폐지 직전까지 있는지 |
| TICKER_CHANGE | PCLN→BKNG(2018-02-27), YHOO→AABA(2017-06-19, 투자회사로 종류 변경), DPS→KDP(2018-07-10), VRX→BHC(2018-07-16), FB→META(2022-06-09, 기간 뒤) | 옛 기호·새 기호 중 어느 쪽이 어느 기간을 주는지 |
| MULTI_CLASS | GOOGL·GOOG, BRK.A·BRK.B(점 표기 UNVERIFIED), Under Armour A(UA→UAA)·C(UA.C→UA, 2016-12-07 기호 맞바꿈) | 종류별로 따로 받는지 |
| ADR | BABA, TSM, SHPG(2019-01-08 인수) | ADR 자료와 인수 뒤 끝 |
| REIT | O, PLD, DCT(2018-08-22 인수) | REIT 자료와 인수 뒤 끝 |
| SMALL_CAP_NEAR_THRESHOLD | KIRK, LCUT, BGFV, RT(2017-12-21 인수) | $250m 근처 소형주(시총 수준은 저장소에 자료가 없어 UNVERIFIED) |
| IPO_IN_WINDOW | TWLO(2016-06-23), SNAP(2017-03-02), DBX(2018-03-23), SPOT(2018-04-03 직접상장), LYFT(2019-03-29 = 기간 마지막 거래일) | 첫 거래일부터 있는지 |

UNVERIFIED 9개: DA06 DNB 완료일, DA07 21CF가 FOXA로 거래한 마지막 날, MC03·MC04 Alpaca의 BRK 점 표기, MC06 UA.C 첫 거래일, SC01~SC04 소형주 시총 수준.

## 3. 요청

- 주소: `https://data.alpaca.markets/v2/stocks/{기호}/bars`, `timeframe=1Day`, `adjustment=raw`, `feed=sip`, 2016-01-01 ~ 2019-03-31(뉴욕 시각), `limit=10000`, `sort=asc`.
- **66개 요청**(쪽 넘김이 없으면 66회): 기호 46개 × `asof=-`(그 기호로 거래된 봉만) + 계보 확인 20개.
  - `asof=<그 종목이 상장돼 있던 날>` 11개: 그 날의 발행사를 이름 변경을 따라가며 받는지(PCLN·YHOO·DPS·VRX·FB·DOW·FOXA·BTU 2개·UA 2개).
  - `asof=2026-10-30` 9개: 지금 기호(BKNG·KDP·BHC·META·UAA·UA·BTU)가 옛 기간을 주는지, 재사용 기호(DOW·FOXA)가 옛 회사를 섞는지.
- 요청 전 고정 대기 0.6초 → 분당 100회 이하(무료 한도 200). 재시도 상한(5xx·연결 2회, 429 3회), 401·403이면 즉시 멈춤, 전체 요청 150회·12분 상한. 키는 Actions Secret `APCA_API_KEY_ID`·`APCA_API_SECRET_KEY`에서만 읽고 출력하지 않는다.
- 주소 허용 목록은 정확히 위 형식과 계획된 기호·asof 조합뿐이다. 넘겨주기(redirect)는 거절한다.

## 4. 출력 (공개 Actions 기록)

고정 줄만 찍는다. **가격·거래량·종목별 숫자·키·토큰·주소·응답 본문은 찍지 않는다.** 소수점 숫자는 하나도 없다.

- `ALPSAMPLE_SERIES`: 요청마다 상태(DATA·NO_DATA·ERR_…), 기대 구간과의 맞음(MATCH·PARTIAL·+OUTSIDE), 첫·끝 봉이 기간 처음·끝인지, 빠진 거래일 유무, T 시가·S 종가 4개씩(OK·MISS·BAD·UNEXP·-), 월말 상태.
- `ALPSAMPLE_EVENT`: 상장폐지·이름 변경·상장일과 실제 첫·끝 봉 날짜의 **일수 차이만**.
- `ALPSAMPLE_LINEAGE`: 티커 변경·재사용 종목의 동작 분류(PIT_SYMBOLS, CURRENT_SYMBOL_ONLY 등), asof 요청의 맞음.
- `ALPSAMPLE_CLASSES`: 종류주 두 기호가 서로 다른 봉인지.
- `ALPSAMPLE_CATEGORY`: 범주별 자료 있는 기호 수, T 시가·S 종가·월말 확보 수/기대 수, 기대 밖 봉 수, 완전 종목 수, 빠진 거래일 없는 종목 수.
- `ALPSAMPLE_CHECKPOINT`: 날짜별 기대·확보·누락 수. `ALPSAMPLE_REQUESTS`: 요청·재시도·상태 코드 수. `ALPSAMPLE_STORAGE`: 저장 결과.

## 5. 저장 (비공개만)

- 응답 원본 바이트 그대로 + 파일별 sha256 manifest를 메모리에서 zip으로 묶어, 비공개 raw 저장소의 **새 release `alpaca-sample-v1-<run_id>`** 에만 올린다(Secret `RAW_REPO_TOKEN`, 설정 문서 6.3절의 기존 승인 경로).
- 코드로 제한: 저장소가 비공개인지와 그 이름의 release가 없는지를 Alpaca 요청 전에 확인, 만들기 직전에 다시 확인(있으면 멈춤, 재사용 안 함). 다른 release는 목록·읽기·수정·삭제하지 않는다. KIS release는 건드리지 않는다. 올린 뒤 내려받아 sha256을 대조한다.
- 공개 저장소·Pages·Actions 산출물에는 아무것도 남기지 않는다(업로드·캐시·요약 없음).

## 6. 약관

Alpaca 약관은 개인·비상업 사용만 허용하고, 공개 게시는 사전 서면 동의가 필요하다. 이 측정은 비공개 연구용이며 **아무것도 공개하지 않는다.** 가격 없는 파생 결과의 공개 가능 여부는 확인되지 않았다(서면 확인 필요).

## 7. 결과로 정할 것

1. **대량 수집 여부**: 기대되는 T 시가·S 종가·월말 종가가 거의 다 있으면(특히 상장폐지·인수 종목이 마지막 거래일 무렵까지 있으면) 대량 수집 계획 PR로 간다. 범주 하나라도 체계적으로 비면 그 범주만 다른 원천을 찾는다.
2. **요청 방식**: 티커 변경·재사용에서 `asof=-`(기호 그대로)와 `asof=<그날>`(발행사 따라감) 중 어느 쪽이 시점 기호와 맞는지 → 대량 수집의 요청 방식을 정한다.
3. **다른 원천이 필요한 경우**: 비는 범주(예: 상장폐지 직전, 재상장, 종류주 점 표기, 기간 중 상장)를 목록으로 남긴다.
4. 2016년을 최초 구간으로 넣을 수 있는지(2016-02-12 종가, 2016-02-16 시가).

## 8. IEX 마지막 체결가

IEX 마지막 체결가 방식은 **같은 표본·같은 조건 측정을 한 뒤에만 별도 변형으로 제안**할 수 있다. 이 측정은 SIP 통합 시가만 잰다. IEX와 차이가 작다고 단정하지 않는다.

## 9. 실행 전 Main 확인

- UNVERIFIED 9개(2절).
- Secret 세 개(`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `RAW_REPO_TOKEN`)가 공개 저장소 Actions에 있는지(Codex 워크플로가 이미 같은 이름을 씀).
- 실행: 승인된 커밋을 `claude/alpaca-sample-once-run` 가지로 한 번 push → 워크플로 1회 → 결과 줄을 읽은 뒤 가지 삭제. 다른 가지·PR·일정·수동 실행으로는 돌지 않는다.
- `--plan`으로 네트워크 없이 요청 수를 다시 볼 수 있다(`python implementation/tools/measure_once/alpaca_sample_once.py --plan`).
