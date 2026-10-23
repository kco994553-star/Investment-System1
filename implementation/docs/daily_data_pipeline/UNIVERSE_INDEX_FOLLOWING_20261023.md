# Universe504 대조와 지수 변경 추종 규칙 설계 (B-1, 2026-10-23)

상태: **설계 초안**이다. 계산, 워크플로, 공개 경계는 바꾸지 않는다. Universe 목록 변경은 별도 PR로 낸다(머지는 owner 승인 뒤).
소유자 원칙: Universe는 지수 편입 변경을 따른다. 임의로 빼거나 넣지 않는다.

## 0. 요약

- 지금 목록은 2026-10-10 승인본이다. 그 뒤 반영된 S&P 500 변경이 없다. 이미 발효된 변경 세 건이 빠져 있다.
  - 2026-09-21 분기 리밸런싱: 3개 제외, 3개 편입.
  - 2026-10-01 Corteva 분할: Vylor 편입, 2026-10-06 Corteva 제외.
  - 2026-10-06 Twilio 편입, WBD 제외.
- 코드만 바뀐 종목은 하나다. `NASDAQ:PSKY`가 `NYSE:SKYD`로 바뀌었다(같은 CIK 0002041610).
- 504개 전부를 SEC 공시로 다시 훑었다. 위 6개 말고 코드, CIK, 상장 폐지가 바뀐 종목은 없다(§2-3).
- `NASDAQ:ASML`은 S&P 500 종목이 아니다. 2026-10-10 owner가 승인한 예외(TARGET 종목)다. 이번 PR에서는 건드리지 않는다. 계속 둘지는 owner가 정한다(§5-6).
- 영향(Q·G 재계산 시뮬레이션): 단면이 499에서 498 CIK로 준다. telecommunications 그룹은 9에서 8 CIK가 된다. `MIN_PEERS`가 8이므로 경계값에 걸린다. 같은 그룹의 Q가 최대 8.69점 움직인다. G는 최대 0.58점 움직인다.

## 1. 현재 목록이 정의된 곳

| 항목 | 위치 | 내용 |
| --- | --- | --- |
| 목록 원본 | `implementation/src/investment_system/universe/universe_codes_v1.json` | 504개 코드 문자열 배열만 있다. as_of, version 필드는 없다. |
| 버전 | 파일 이름의 `v1`과 git 이력뿐이다 | 마지막 변경은 `e8a9d69e`, 2026-10-10 07:29 UTC(16:29 KST)다. |
| 출처 설명 | `docs/daily_data_pipeline/SEC_M3_INPUT_ADAPTER.md:35`, `M3_SUBSET_IMPLEMENTATION_SPEC.md:67` | 사용자가 설명한 "현재 S&P 500 + ASML"이다. 공식 dated membership이 아니라고 적혀 있다. |
| 공개 | `universe/universe_codes.py:16,21-31` | `public_payload()['codes']`가 위 JSON을 그대로 낸다. |
| 검증 | `universe/universe_codes.py:34-44` | 공개본이 저장소 목록과 같아야 한다. |
| CIK 결합 | `providers/sec_universe_collection.py:76-90` | SEC `company_tickers_exchange.json`의 (거래소, ticker)로 코드를 CIK에 묶는다. |
| 같은 목록을 쓰는 곳 | `universe/sec_universe_shares.py:67`, `sec_qgv2.py:291`, `worker/src/index.js`(US_SYMBOLS), `web_assets/google-sheet-quotes.js`, `web_assets/company-names-ko.json` 등 | 목록을 바꾸면 이 사본들도 함께 바뀐다. |

PSKY는 359행, WBD는 485행, ASML은 505행에 있다.

## 2. 대조 결과

### 2-1. 출처와 접근 상태

- S&P DJI 지수 페이지(`spglobal.com/spdji/...`)는 HTTP 403이었다. 그래서 같은 S&P Global 뉴스룸(`press.spglobal.com`)의 S&P DJI 원문 보도자료를 1차 근거로 썼다. 원문 접근은 되었다.
- 교차 확인에는 SEC EDGAR 공시를 썼다(submissions, 원문 문서).
- 구성 대조에는 SPY 보유 목록(State Street, "As of 22-Oct-2026")의 ticker만 썼다. 비중과 수량은 쓰지 않았고 저장소에 남기지 않는다.
  링크: https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx
- SPY 목록에는 주식 503줄이 있다. 여기에 현금 1줄과 TPG CVR 1줄(`436CVR021`)이 더 있다. CVR은 지수 종목이 아니라서 뺐다.
- SPY와 504를 ticker로 맞춰 본 결과는 다음과 같다. 504에만 있는 것: ASML, BLDR, CTVA, PSKY, TAP, TTD, WBD. SPY에만 있는 것: BE, ILMN, P, SKYD, TWLO, VYLR. 아래 S&P 발표와 정확히 맞는다.
- 2026-10-01 이후 2026-10-22까지 S&P 500 변경 발표는 없었다. 그 기간의 발표는 SmallCap 600 건뿐이었다.

S&P DJI 원문 보도자료:
- [S1] 2026-09-04 "Bloom Energy, Illumina, and Everpure Set to Join S&P 500" — https://press.spglobal.com/2026-09-04-Bloom-Energy,-Illumina,-and-Everpure-Set-to-Join-S-P-500-Others-to-Join-S-P-100,-S-P-MidCap-400,-and-S-P-SmallCap-600
- [S2] 2026-10-01 "Vylor Added to the S&P 500; Twilio Set to Join S&P 500" — https://press.spglobal.com/2026-10-01-Vylor-Added-to-the-S-P-500-Twilio-Set-to-Join-S-P-500-Others-to-Join-S-P-MidCap-400-and-S-P-SmallCap-600

시각 기준: S&P의 "effective prior to the open"은 그날 09:30 ET다. 2026-09-21, 2026-10-06 모두 13:30 UTC(22:30 KST)다.

### 2-2. 차이 표

**A. 지수에서 빠졌는데 목록에 남은 종목 (5)**

| 코드(현재 목록) | CIK | 발효일 | 사유 | 근거 |
| --- | --- | --- | --- | --- |
| `NYSE:TAP` (319행) | 0000024545 | 2026-09-21 개장 전 | 분기 리밸런싱. SmallCap 600으로 이동 | [S1] |
| `NASDAQ:TTD` (446행) | 0001671933 | 2026-09-21 개장 전 | 분기 리밸런싱. SmallCap 600으로 이동 | [S1] |
| `NYSE:BLDR` (78행) | 0001316835 | 2026-09-21 개장 전 | 분기 리밸런싱. SmallCap 600으로 이동 | [S1] |
| `NYSE:CTVA` (130행) | 0001755672 | 2026-10-06 개장 전 | 종자 사업(Vylor)을 2026-10-01 분할한 뒤 MidCap 400으로 이동 | [S2]. Corteva 8-K Item 2.01 "On October 1, 2026 … completed the separation": https://www.sec.gov/Archives/edgar/data/1755672/000119312526414490/ck0001755672-20260929.htm |
| `NASDAQ:WBD` (485행) | 0001437107 | 2026-10-06 개장 전 | Skydance(구 PSKY)가 현금으로 인수했다(주당 $31.01666668). 상장 폐지 | [S2]. WBD 8-K(2026-10-06, 2.01 완료, 3.01 상장 폐지): https://www.sec.gov/Archives/edgar/data/1437107/000119312526415055/d200872d8k.htm |

WBD 공시 순서(SEC submissions에서 확인):
- 2026-10-06: 8-K 제출. Form 25(`0001193125-26-415091`)와 Nasdaq의 25-NSE(`0001354457-26-000951`)도 이날 나왔다. POS AM 8건, S-8 POS 5건도 이날 제출했다.
- 2026-10-07: EFFECT 7건(접수는 10-08).
- IEX(Main 확인, 실행 39944426209): WBD 체결은 10-05가 마지막이다. 10-06부터는 상태 메시지와 체결이 없다.
- 2026-10-16: 15-12G 제출: https://www.sec.gov/Archives/edgar/data/1437107/000119312526423513/d188095d1512g.htm . 같은 날 채권 등 15-15D 8건도 제출했다.
- SEC `company_tickers.json`(Last-Modified 2026-10-16 11:54 UTC)에는 CIK 0001437107의 ticker가 없다. 반면 `company_tickers_exchange.json`(11:53 UTC)에는 아직 `WBD/Nasdaq`이 남아 있다. 저장소의 CIK 결합은 이 exchange 파일을 쓴다(`sec_universe_collection.py:74-84`). 그래서 지금도 WBD 행이 수집되고 LIVE로 남는다.

**B. 지수에 들어왔는데 목록에 없는 종목 (5)**

| 제안 코드 | CIK | SIC → 업종군 | 발효일 | 사유 | 근거 |
| --- | --- | --- | --- | --- | --- |
| `NYSE:BE` | 0001664703 | 3620 → manufacturing_industrial_tech | 2026-09-21 개장 전 | TAP 대체(리밸런싱) | [S1] |
| `NYSE:P` | 0001474432 | 3572 → manufacturing_industrial_tech | 2026-09-21 개장 전 | TTD 대체. 옛 이름 Pure Storage, 2026-01 Everpure로 바뀜(SEC formerNames) | [S1] |
| `NASDAQ:ILMN` | 0001110803 | 3826 → manufacturing_industrial_tech | 2026-09-21 개장 전 | BLDR 대체 | [S1] |
| `NYSE:VYLR` | 0002128626 | 0100 → 업종군 없음(NA) | 2026-10-01 | Corteva 분할 회사 | [S2]. 연간 SEC 재무가 아직 없다(10-12B만 있음) |
| `NYSE:TWLO` | 0001447669 | 7372 → services_software_health | 2026-10-06 개장 전 | WBD 대체. MidCap 400에서 이동 | [S2] |

**C. 코드가 바뀐 종목 (1)**

| 이전 → 새 코드 | CIK | 날짜 | 사유 | 근거 |
| --- | --- | --- | --- | --- |
| `NASDAQ:PSKY` → `NYSE:SKYD` | 0002041610(그대로) | Nasdaq 거래는 2026-10-05 장 마감에 끝났다. NYSE 거래와 사명 변경은 2026-10-06 개장부터다 | 상장을 Nasdaq에서 NYSE로 옮기면서 ticker를 바꿨다. 사명은 Paramount Skydance에서 Skydance Corp로 바뀌었다. 같은 날 WBD 인수를 마쳤다. S&P 500 종목 자격은 그대로다([S2]: "Post merger, Paramount Skydance will switch its primary listing to the NYSE") | 8-K(2026-10-02) ticker 변경 예고: https://www.sec.gov/Archives/edgar/data/2041610/000110465926113076/tm2626659d3_8k.htm · 8-A12B(2026-10-05): https://www.sec.gov/Archives/edgar/data/2041610/000110465926113569/tm2626659d5_8a12b.htm · Form 25(2026-10-05, Nasdaq 자발 상장 폐지): https://www.sec.gov/Archives/edgar/data/2041610/000110465926113696/tm2626659d6_25.htm · 완료 8-K: https://www.sec.gov/Archives/edgar/data/2041610/000110465926113913/tm2626659d7_8k.htm |

- SEC `company_tickers.json`은 CIK 0002041610을 `SKYD`와 `SKYD-WT`로 매핑한다. exchange 파일에는 `PSKY/Nasdaq`이 아직 남아 있다.
- IEX 거래 증거(Main 확인, IEX TOPS 조사 실행 39944426209, 개수만 확인). 이 레인은 IEX에 접근하지 않았다.
  - PSKY: 2026-10-02와 10-05에 체결이 있다. 10-06부터는 없다.
  - SKYD: 10-05까지 없다. 10-06부터 체결이 있다(10-21과 22도 같다).
  - WBD: 10-05까지 체결이 있다. 10-06부터는 IEX 상태 메시지도 체결도 없다.
  - SEC 공시 날짜와 맞는다. PSKY는 Form 25(10-05)와 NYSE 상장(10-06)이다. WBD는 인수 완료와 상장 폐지(10-06), POS AM(10-06), EFFECT(10-07), 15-12G(10-16)다.

### 2-3. 504개 전부를 독립적으로 다시 확인

방법: SEC exchange 파일로 504개 코드를 CIK에 맞춘 뒤 각 CIK의 SEC submissions(2026-08-01 이후)를 받았다. 확인한 것은 세 가지다. (1) Form 25, 25-NSE, 15-12B, 15-12G, 15-15D, 8-K12B 제출 여부. (2) 2026년 안의 실제 사명 변경. (3) 코드 거래소 접두어가 SEC exchange와 맞는지.

- 거래소 접두어는 504개 모두 SEC exchange와 맞았다.
- 위 A·C 말고 걸린 종목은 모두 영향이 없다.
  - 25-NSE(T, C, KO, CMCSA, DHR, IFF, MRSH, MRK, MAA, PM, PG, WMT): 거래소가 낸 채권이나 우선주 상장 폐지다. 보통주 ticker와 CIK는 그대로다. 2026-10-22 SPY 목록에도 모두 있다.
  - `NYSE:KHC`: Nasdaq에서 NYSE로 옮겼다(2026-09-08 Form 25 자발 폐지와 8-A12B). 목록은 이미 `NYSE:KHC`다. https://www.sec.gov/Archives/edgar/data/1637459/000163745926000062/khc-form25gdcdraftx6001812.htm
  - `NYSE:OKE`: 2026-09-10 지주회사 재편을 했다(8-K12B, 12g-3(a) 승계). 승계 회사가 같은 CIK 0001039684로 신고하고 ticker도 같다. 2026-09-28의 15-12G는 옛 회사 보증 증권 대상이다. 코드 영향은 없다. 다음 10-Q부터 XBRL 연속성을 지켜볼 대상이다. https://www.sec.gov/Archives/edgar/data/1039684/000119312526387972/d81803d8k12b.htm
  - `NYSE:APO`: 15-12G(2026-08-11)를 냈지만 보통주 ticker는 그대로다. SPY 목록에도 있다.
  - 사명 변경: BEN(Franklin Resources → Franklin Templeton Inc, ticker 그대로)과 VMRK(Equity Residential → Vivmark, 목록이 이미 VMRK)다. 나머지는 대소문자만 바뀌었다.
- 결론: Main의 CIK → 현재 ticker 대조 결과와 같다. 코드나 CIK가 바뀐 종목은 PSKY와 WBD 둘뿐이다. 다만 지수 편출입 8건(A의 TAP, TTD, BLDR, CTVA와 B의 5건)은 CIK 대조로는 보이지 않는다. 이번 S&P 원문 대조로 처음 확인한 것이다.

## 2-4. Universe 안의 과거 ticker 변경과 신규 상장(가격 이력용 근거)

배경: Main의 U8 실행 39945012772에서 IEX 월말 거래가 현재 심볼로는 없는 구간이 나왔다. 아래는 그 구간을 SEC 원문으로 설명한 것이다. 모두 CIK가 같고 심볼만 바뀌었다. 따라서 과거 가격 이력은 이전 심볼로 이어 붙여야 한다(§5-3 CODE_CHANGE의 과거판, 날짜가 있는 심볼 이력표).

| 현재 코드 | 이전 심볼 | 변경일(새 심볼 거래 시작) | IEX 무거래 월말(Main) | 근거(SEC) |
| --- | --- | --- | --- | --- |
| NASDAQ:WTW | WLTW | 2022-01-10 | 2021-12 | 8-K 2022-01-07: https://www.sec.gov/Archives/edgar/data/1140536/000119312522004045/d267396d8k.htm |
| NYSE:BALL | BLL | 2022-05-10 | 2021-12 | 8-K 2022-05-03 Item 8.01 "changing our ticker to BALL effective May 10, 2022": https://www.sec.gov/Archives/edgar/data/9389/000000938922000010/bll-20220427x8k.htm |
| NYSE:ELV | ANTM | 2022-06-28(사명 변경과 같은 날) | 2021-12 | 8-K 2022-06-28 표지 심볼 ELV: https://www.sec.gov/Archives/edgar/data/1156039/000119312522183957/d359422d8k.htm · 2022 위임장의 예고: https://www.sec.gov/Archives/edgar/data/1156039/000115603922000047/a2022proxystatement.htm |
| NYSE:CPAY | FLT | 2024-03-25 | 2021-12~2024-12 | 8-K 2024-03-12 EX-99.1: https://www.sec.gov/Archives/edgar/data/1175454/000162828024010593/exhibit991corpayrebrand_re.htm |
| NYSE:XYZ | SQ | 2025-01-21(**회사 발표 기억, SEC 원문 미확인**) | 2021-12~2024-12 | 8-K 2025-02-06 표지 심볼 XYZ: https://www.sec.gov/Archives/edgar/data/1512673/000119312525021783/d843940d8k.htm · 10-K(2025-02-24) "under the symbol XYZ" |
| NASDAQ:EXE | CHK | 2024-10-02 | 2022-12 | 8-K 2024-10-01: https://www.sec.gov/Archives/edgar/data/895126/000110465924104976/tm2425151d1_8k.htm |
| NYSE:COR | ABC | 2023-08-30 | 2022-09 | 8-K 2023-08-30 EX-99.1: https://www.sec.gov/Archives/edgar/data/1140859/000110465923096698/tm2324358d1_ex99-1.htm |
| NYSE:RVTY | PKI | 2023-05-16 | 2023-01 | 8-K 2023-05-11 EX-99.1: https://www.sec.gov/Archives/edgar/data/31791/000115752323000815/a53397725ex99_1.htm |
| NASDAQ:FISV | FISV(Nasdaq) → FI(NYSE) → FISV(Nasdaq) | FI: 2023-06-07, FISV: 2025-11-11경 | 2023-12, 2024-12 | 8-K 2023-05-25 EX-99.1: https://www.sec.gov/Archives/edgar/data/798354/000119312523154199/d470900dex991.htm · 8-K 2025-10-29("effective on or about November 11, 2025", 심볼 FISV): https://www.sec.gov/Archives/edgar/data/798354/000119312525254670/d17957d8k.htm |
| NYSE:MRSH | MMC | 2026-01 중(2026-01-14 이전) | 2021-12~2025-12 | 2025-10-16 8-K EX-99.1 "In January 2026 … will change from MMC to MRSH": https://www.sec.gov/Archives/edgar/data/62709/000006270925000123/mmc3q2025ex991newsrelease.htm · 2026-01-14 8-K 표지 심볼 MRSH. 정확한 날짜는 미확인 |
| NYSE:VMRK | EQR | 2026-08-18 | 2021-12~2025-12 | 8-K 2026-08-17: https://www.sec.gov/Archives/edgar/data/906107/000114036126033377/ef20080318_8k.htm |
| NASDAQ:ECHO | SATS | 2026-06-18~06-25 사이(**정확한 날짜 미확인**) | 2021-12~2025-12 | 8-K 표지 심볼이 2026-06-18 제출분은 SATS이고, 2026-06-25 제출분은 ECHO다: https://www.sec.gov/Archives/edgar/data/1415404/000141540426000030/sats-20260623x8k.htm |

Main 표의 IEX 무거래 구간은 조사한 월말만 보여 준다. 예를 들어 BALL과 ELV는 2022-01~05 월말도 이전 심볼이었다.

신규 상장과 분할. 상장 전 가격 이력은 없다. 채우지 않고 NA로 둔다(V4).

| 코드 | 첫 정규 거래일 | 사유 | 근거(SEC) |
| --- | --- | --- | --- |
| NASDAQ:GEHC | 2023-01-04 | GE에서 분할 | https://www.sec.gov/Archives/edgar/data/1932393/000119312523001161/d386556dex991.htm |
| NYSE:VLTO | 2023-10-02 | Danaher에서 분할 | https://www.sec.gov/Archives/edgar/data/1967680/000196768023000005/exhibit992pressrelease.htm |
| NYSE:GEV | 2024-04-02 | GE에서 분할 | https://www.sec.gov/Archives/edgar/data/1996810/000119312524084048/d807682dex991.htm |
| NYSE:SOLV | 2024-04-01 | 3M에서 분할 | https://www.sec.gov/Archives/edgar/data/1964738/000162828024014887/exhibit992-8xksolventumpre.htm |
| NYSE:SW | 2024-07-08 | Smurfit Kappa와 WestRock 결합(2024-07-05 완료) 뒤 NYSE 상장 | 8-K 2024-07-08: https://www.sec.gov/Archives/edgar/data/2005951/000110465924078355/tm2418700d1_ex99-2.htm |
| NYSE:KVUE | 2023-05-04 | J&J 자회사 IPO | 8-K(2023-05-08): "May 4, 2023, the date that Kenvue Common Stock was first listed": https://www.sec.gov/Archives/edgar/data/1944048/000162828023016423/kvue-20230503.htm |
| NASDAQ:SNDK | 2025-02-24 | Western Digital에서 분할 | https://www.sec.gov/Archives/edgar/data/2023554/000119312525033433/d849281dex991.htm |
| NYSE:FDXF | 2026-06-01 | FedEx에서 분할 | https://www.sec.gov/Archives/edgar/data/2082247/000110465926068521/tm2615735d1_ex99-1.htm |

설계에 반영할 점(§5-3 보충):
- 이벤트 로그에 과거 CODE_CHANGE도 `effective` 날짜와 함께 싣는다. 가격 이력 레인은 이 표로 이전 심볼 구간을 찾는다.
- 분할이나 IPO 종목은 `listed_from`을 싣는다. 그 전 기간은 NA다(대체값으로 채우지 않는다).
- 이 표는 Universe 구성 변경이 아니다. 그래서 `universe_version`을 올리지 않는다.

## 3. Q·G·V와 백분위에 주는 영향

입력: 게시 `sec-qgv2.json`
- `as_of` 2026-10-23T00:48:22Z(09:48 KST), `calc_version` `qgv2-calc/2026-10-17.1`
- sha256 `80a6f12484fce802e9fd54fd989e5190e4fb34981e09fcbf1b29cda6bf130d20`
- 단면 499(GENERAL 431, FINANCIAL 68)

방법:
- 저장소 `qgv.v2_scoring.score_rows`로 다시 계산했다. 게시 점수와 불일치는 0이다.
- 바꾼 Universe는 A의 5개를 빼고, PSKY 행을 SKYD로 옮기고, B의 5개를 넣은 것이다.
- B의 5개 행은 SEC companyfacts와 submissions(2026-10-23 수집)로 `sec_qgv2.build_row`를 돌려 만들었다. 가격은 쓰지 않았다.

| 항목 | 지금 | 지수 추종 후 |
| --- | --- | --- |
| 코드 수 | 504 | 504(−5, +5, 이름 변경 1) |
| 단면(CIK) | 499 = GENERAL 431 + FINANCIAL 68 | 498 = GENERAL 430 + FINANCIAL 68 |
| Q NA(코드 기준) | 18 | 19 |
| G NA(코드 기준) | 10 | 11 |
| telecommunications | 9 CIK | **8 CIK**(`MIN_PEERS` = 8, `v2_scoring.py:32`). 경계값이다 |
| food_tobacco | 19 | 18 |
| wholesale_retail | 40 | 39 |
| manufacturing_industrial_tech | 181 | 184 |
| 업종군 NA(GENERAL) | 1(CTVA, SIC 0100은 v0 표에 없다) | 0. VYLR(SIC 0100)도 업종군이 없지만 NOT_AVAILABLE이라 단면에 없다 |
| services_software_health | 75 | 75(TTD −1, TWLO +1) |

NA가 하나씩 늘어나는 이유: VYLR에 연간 재무가 없다(`NO_ANNUAL_SEC_FINANCIALS`). 그래서 Q와 G가 모두 NA다.

빠지는 행의 지금 점수(참고):
- WBD: Q 20.37(업종 9), G 18.07
- CTVA: Q 53.43(UNIVERSE_FALLBACK), G 45.39
- TAP: Q 39.67, G 32.37
- TTD: Q 69.56, G 66.41
- BLDR: Q 37.51, G 9.72

들어오는 행의 시뮬레이션 점수:
- BE: Q 25.03, G 83.57
- ILMN: Q 55.29, G 50.04
- P: Q 63.87, G 67.93
- TWLO: Q 48.12, G 65.99(3/5)
- VYLR: NA

남는 행의 점수 변화:
- Q: 481행 중 323행이 바뀐다. 1점 이상 바뀌는 행은 12개다. telecommunications 7개는 FOXA/FOX −8.69, CHTR −7.14, CMCSA −6.01, VZ −5.61, TMUS −1.96, ECHO +1.15다. food_tobacco 5개는 −1.2에서 −1.75 사이다. peer_basis가 바뀌는 행은 없다.
- G: 489행 중 424행이 바뀐다. 최대 0.58점(GEV, TTWO)이고 1점 이상 바뀌는 행은 없다.
- 해석: WBD(Q 20.37)는 telecom 그룹의 하위 점수다. WBD가 빠지면 나머지가 상대적으로 내려간다. 이것은 지수 구성을 따른 결과이고 계산 오류가 아니다.

경계 위험:
- telecom에서 한 CIK만 더 빠지면 7 < 8이 된다. 그러면 그룹 전체의 Q가 `UNIVERSE_FALLBACK`(GENERAL 전체 비교)으로 바뀐다. 다음 편출입 때 꼭 확인할 항목이다.

V(중앙 V):
- 가격이 필요해서 이 레인에서는 계산하지 않았다.
- 구조 영향만 정리한다. V 단면도 같은 GENERAL 모집단(LIVE/STALE, CIK당 한 점)을 쓴다. 그래서 같은 그룹 크기 변화(telecom 9 → 8 등)가 그대로 적용된다.
- SKYD V 입력은 인수 전 대차대조표 그대로다. `v_inputs_v2.total_debt`가 2026-06-30 기준 15.156B이고, `diluted_shares`가 1.12B다.
- WBD 인수는 전액 현금이었고 차입이 따랐다(SKYD 8-K 2026-10-13, Item 2.03). 그래서 Q3 10-Q가 나오기 전까지 EV와 순부채 기반 V가 실제보다 좋게 보일 가능성이 크다(**추정**). Q3 10-Q 제출일은 확인하지 않았다.

PSKY/SKYD의 FY0 문제(보충 지시 3):
- 게시 행의 `fiscal_year_end`는 2024-12-31이다. G는 0/5라 NA(`AXIS_COVERAGE_BELOW_50`)다. Q는 3/5(가용 가중 65)로 업종 9개 안에서 32.01점이다.
- FY2025 10-K(2026-02-25)는 합병 전후로 나뉘어 있다. 2025-01-01~08-06이 217일, 2025-08-08~12-31이 145일이다. 둘 다 연간 규칙(300~400일)에 맞지 않아 FY0이 2024로 남았다. 이 사실은 Main이 지시에 적은 것이고, 이 레인은 원문을 다시 열지 않았다.
- 이름 변경만으로는 이 상태가 달라지지 않는다(같은 CIK, 같은 companyfacts).
- 예상되는 정상화 시점은 FY2026 10-K다(**추정**: 2027-02경, 첫 365일 연간). 다만 WBD를 2026-10-06부터 연결하므로 FY2026 성장률은 인수 효과가 섞인다.

## 4. Universe 갱신이 늦을 때 생기는 일 (지금 상태)

- 빠진 5개 코드는 지금도 수집되고 단면에 들어간다. WBD도 SEC exchange 파일에 `WBD`가 남아 있는 동안은 LIVE다.
- exchange 파일에서 WBD가 빠지면 등록 해제(unresolved) → PRESERVE가 된다. 14일 뒤에는 STALE이 된다. 그래도 STALE은 단면에 남는다(`v2_scoring.py:36` `SCORED_STATES`). 즉 목록에서 지우기 전까지는 백분위 분모에 계속 들어간다.
- 들어올 5개 코드는 백분위 분모에 없다.

## 5. 지수 변경 추종 규칙(설계)

### 5-1. 원칙

1. 근거는 S&P DJI 공식 발표만이다. 원문은 `press.spglobal.com` 또는 `spglobal.com/spdji`다. SEC 공시는 날짜와 CIK 확인용이고, ETF 보유 목록은 교차 확인용이다. 이 둘만으로는 목록을 바꾸지 않는다.
2. 적용 시점은 발표의 effective date다. "prior to the open on D"는 세션 D부터 새 구성이라는 뜻이다. 일일 게시는 D의 장 마감 뒤에 돈다(22:17 UTC 계열). 그래서 세션 D의 게시본이 처음으로 새 구성을 쓴다.
3. 발표만 나고 아직 발효되지 않은 이벤트는 기록만 하고 적용하지 않는다.
4. 예외(지수 밖 종목)는 owner 결정 번호가 있는 명시 목록으로만 둔다. 지금 해당하는 것은 ASML 하나다.

### 5-2. 데이터 모양(제안)

`universe/universe_membership_v2.json`(새 파일, 공개 가능, 가격 없음):

```json
{
  "schema": "universe-membership/1",
  "index": "S&P 500",
  "base": {"universe_version": "universe/2026-10-10.0", "codes": ["...504..."], "approved": "2026-10-10", "commit": "e8a9d69e"},
  "exceptions": [{"code": "NASDAQ:ASML", "cik": "0000937966", "decision_ref": "<owner 결정 번호>", "reason": "TARGET 종목"}],
  "events": [
    {"id": "sp500-2026-09-21-1", "action": "DELETE", "code": "NYSE:TAP", "cik": "0000024545",
     "announced": "2026-09-04", "effective": "2026-09-21", "reason": "QUARTERLY_REBALANCE",
     "source": "https://press.spglobal.com/2026-09-04-...", "sec_evidence": []},
    {"id": "sp500-2026-10-06-p1", "action": "CODE_CHANGE", "code": "NYSE:SKYD", "old_code": "NASDAQ:PSKY",
     "cik": "0002041610", "effective": "2026-10-06", "reason": "LISTING_TRANSFER_TICKER_CHANGE",
     "source": "https://www.sec.gov/Archives/edgar/data/2041610/000110465926113076/tm2626659d3_8k.htm"}
  ]
}
```

- `action`은 `ADD`, `DELETE`, `CODE_CHANGE` 중 하나다. CODE_CHANGE는 CIK가 같을 때만 쓴다. CIK가 달라지면(새 법인, 분할 신설) DELETE와 ADD 두 이벤트로 적는다.
- 이벤트는 append-only다. 고칠 때는 `supersedes`를 가진 새 이벤트를 추가한다.
- `universe_version`은 `universe/<마지막으로 적용한 effective date>.<순번>`이다. 이번 묶음은 `universe/2026-10-06.1`이 된다.
- `membership_at(D)`는 base에 effective ≤ D인 이벤트를 차례로 적용한 결과다. 순수 함수다.
- 지금의 `universe_codes_v1.json`은 `membership_at(today)`에서 만들어지는 파생물이 된다. 공개 `universe-codes.json` 모양은 그대로 둔다. 이렇게 하면 사본(worker, quotes.js, names-ko)이 한 원본에서 나온다.

### 5-3. 행과 이력 처리

| 경우 | `sec-qgv2.json` 등 게시 행 | 이력 |
| --- | --- | --- |
| DELETE | 발효 세션부터 `records`에서 뺀다. 단면에서도 빠진다. | 이미 게시된 원장 기록은 그대로 둔다(append-only). 빠진 코드의 마지막 행은 비공개 raw 릴리스에 이미 있다. 공개 `universe-changes.json`에 코드, CIK, 날짜, 사유, 출처만 남긴다(값은 남기지 않는다). |
| ADD | 빈 `NOT_COLLECTED` 행으로 들어간다. 해당 CIK 샤드가 수집될 때 채워진다(최대 7일). 제안: 발효일 실행에서 추가 CIK만 한 번 즉시 수집한다(별도 승인 항목). | 시작 세션을 기록한다. 그 전 기간을 소급해 채우지 않는다. |
| CODE_CHANGE | 같은 CIK의 보관 행을 새 코드로 옮긴다(값은 그대로, `acquired_at`도 그대로). 새 수집이 오면 평소처럼 교체한다. | CIK 기준으로 이어진다. 화면에는 "이전 코드 PSKY"를 표시한다. |

- 이미 지난 발효일(이번처럼 9/21과 10/6을 10/23에 반영하는 경우): 다음 게시부터 적용한다. 과거 게시본과 원장은 다시 쓰지 않는다. 이벤트에 `applied_session`을 함께 남겨 지연(발효일과 적용일의 차이)을 공개한다.
- 같은 CIK가 둘 이상의 코드(GOOGL/GOOG, FOX/FOXA)인 경우는 지금처럼 CIK당 한 점이다. 바꿀 것이 없다.

### 5-4. 버전과 원장 구간

- 지금 원장의 구간은 `calc_version` 하나다(`validation/forward_ledger.py:202,232`). 단면 크기와 CIK 해시는 `population`(`:212,229`)에 들어간다. 그래서 구성이 바뀌면 해시는 달라지지만 구간은 이어진다.
- 제안 1(이번 라운드): 중앙 V `calc_version` 올림과 같은 게시에서 Universe를 바꾼다. 그러면 원장은 `calc_version` 변경 한 번으로 구간이 나뉜다. 원장 코드를 바꾸지 않아도 된다(원장 코드는 이 레인 범위 밖이다).
- 제안 2(다음부터 Universe만 바뀔 때): 원장 basis에 `universe_version`을 추가한다. 구간 키는 `calc_version + '|' + universe_version`으로 한다. 원장 검증(`:432` `segment == version`)을 바꾸므로 owner 승인이 필요하다. 그 전까지 Universe만 바뀌는 변경은 다음 calc_version 올림까지 기다렸다가 함께 적용한다. 다만 S&P 발효일에서 많이 늦어지므로 기간 상한을 정해야 한다(owner 결정 항목).
- 중앙 V 설계(`CENTRAL_V_PUBLICATION_DESIGN_20261018.md:228`)는 Universe 구성 변경 때 `population.version`만 바꾸고 `calc_version`은 두라고 한다. 이번에는 owner 지시에 따라 두 변경을 한 게시로 묶는다. 이때 `population.version` = `universe_version`으로 맞춘다. D-CV7(`:461`)의 필드 분리는 그대로 둔다.
- 원장의 `UNIVERSE_SIZE = 504`와 `PRIMARY_MIN_SCORED = 454`(`forward_ledger.py:80-81`)는 504 고정이다. 이번 변경은 504를 유지하므로 영향이 없다. 크기가 바뀌는 변경(예: ASML 제외 시 503)이 생기면 `ceil(0.9 × 코드 수)`로 바꿔야 한다. 원장 코드 변경이므로 별도 승인이 필요하다.

### 5-5. 자동 감지(설계만)

- 매일 실행에서 두 가지를 확인해 경고만 낸다. 목록은 바꾸지 않는다.
  - SEC exchange 파일에서 Universe CIK의 ticker가 사라지거나 바뀌었는가.
  - 25, 15-12B, 15-12G 중 보통주 대상 공시가 나왔는가.
- S&P 발표 페이지 감시는 외부 연결 추가라서 별도 승인 항목이다.

### 5-6. owner 결정 항목

1. 이번 변경(§2-2 A·B·C)을 중앙 V `calc_version` 올림과 한 게시로 묶을지. 권장: 묶는다.
2. ASML을 명시 예외로 계속 둘지(권장), 아니면 지수 원칙대로 뺄지. 빼면 504가 503이 되고 원장 454 기준도 바뀐다.
3. 새로 들어오는 CIK를 발효일에 즉시 수집할지(외부 SEC 요청이 늘어난다).
4. Universe만 바뀌는 변경을 calc_version 올림까지 최대 며칠 미룰 수 있는지.

## 6. 테스트 초안

`implementation/tests/test_universe_index_membership_draft.py`. 아직 없는 모듈 `investment_system.universe.index_membership`에 대한 계약 테스트다. 모듈이 생기기 전까지는 `pytest.importorskip`으로 건너뛴다. 숫자와 코드는 모두 합성이다.

## 7. 이 문서가 바꾸지 않는 것

계산 코드, 워크플로, 원장 코드, 중앙 V 파일, TARGET 파일은 바꾸지 않는다. 목록 변경 PR은 별도 브랜치에서 낸다(머지 금지, owner 승인 대기).
