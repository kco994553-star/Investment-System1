# 확장 모집단 정의 · 가격 공급처 약관 · 역산 시험 (오너 결정 2026-10-30, Main)

> **상태:** 오너 결정을 기록하고 숫자를 제안하는 문서다. 코드·워크플로·일정·공개 파일·공식 모집단은 바꾸지 않았다. 계약·가입·서면 문의도 하지 않았다.
> **숫자의 성격:** §1.3의 종목 수는 **측정값이 아니다.** 공개 1차 자료(FTSE Russell, CRSP 집계)로 낸 추정이고, 표마다 근거 수준을 적었다. 확정 숫자는 §1.4 측정 1회 뒤에 나온다.
> **역산 시험:** 공개 SEC 재무(공개 파일 `sec-qgv2.json` 23.1)와 **합성 가격**으로 했다. 실제 가격은 내려받지도, 쓰지도, 저장하지도 않았다. 스크립트는 세션 스크래치(저장소 밖)에만 있다.

## 0. 오너 결정 (2026-10-30)

| 번호 | 결정 | 구현 상태 |
| --- | --- | --- |
| 1 | **ADR을 포함한다.** | 문서만 |
| 2 | **확장 모집단 = "초소형주를 뺀, 일반 투자자가 쉽게 찾고 살 수 있는 중소형주까지".** 네 기준을 모두 충족해야 한다: ① 주요 거래소 상장(OTC 제외) ② 시총 하한(약 $200m, 대략의 선) ③ 일평균 거래대금 하한(약 $1m) ④ 최소 주가(약 $2~5). 숫자는 실제 분포를 근거로 제안하고, 기준을 넣고 뺄 때 종목 수 변화를 표로 보인다. | 문서만(§1) |
| 3 | **가격 공급처 확장은 "가격은 보이지 않고 역산도 안 되며, 점수만 공개" 조건으로만 검토한다.** 공급처마다 약관 원문 조항을 인용하고, 불명확하면 "서면 확인 필요"로 둔다. 계약·가입은 하지 않는다. | 문서만(§2) |
| 4 | **역산 방지:** V는 정밀 값 대신 백분위나 구간으로, T+1로 공개한다. 공개 SEC 재무와 V로 가격을 몇 % 오차까지 추정할 수 있는지 시험한다. | 시험 완료(§3), 구현 없음 |
| 5 | **숨김 범위:** 가격에서 나온 요소(V 세부 요소, 정확한 시총)만 숨긴다. Q·G 세부와 가중치는 공개한다. | 문서만(§3.4) |
| 6 | 결정 9개 중 이 결정으로 해결된 것을 지우고 남는 것만 다시 묻는다. | §4 |

**Main 해석(오너 확인 대기):**
- 오너 문장은 CPI를 말하지 않았다. 10/29 지시는 "물가조정 $200m과 명목 $200m을 분리"하라고 했다.
- Main은 "약 $200m, 대략의 하한선"을 오늘 달러 기준 **명목** 하한으로 읽고 이 문서를 썼다.
- 이 해석은 `EXP-CPI-POLICY`에서 한 줄로 확인받는다. 확인되면 2026-10-29 설계(§4 E2)의 물가조정 판정은 확장 카탈로그에서 빠지고, CPI 정책은 #418 과거 모집단(`U-BOOK200`)에만 남는다.
- 모집단 ID `U-US-CAP200-REF`는 그대로 두고 정의만 바꾼다(DC-28).

## 1. 정의와 Main 제안 숫자

### 1.1 네 기준과 제안값

진입선과 유지선을 따로 둔다. 문턱 근처 종목이 매달 들락거리지 않게 하는 완충이다. 판정은 월 1회, 직전 거래일 자료로 한다.

| 기준 | 진입 | 유지(이 아래로 내려가면 빠짐) | 근거 |
| --- | --- | --- | --- |
| ① 거래소 | NYSE · Nasdaq(전 계층) · NYSE American · Cboe BZX | 같음 | #422 코어 정책(`NASDAQ`·`NYSE`·`NYSE_AMERICAN`·`BATS`)과 같다. OTC는 제외 |
| ② 시총 | **$250m** | **$200m** | SEC 투자자 안내서 "Microcap Stock: A Guide for Investors"(2013): "A typical definition would be companies with a market capitalization of less than $250 or $300 million". 2026-04-30 Russell 2000 최하단 회사는 $146.4m(FTSE Russell). 오너의 $200m은 절대 하한으로 둔다: $200m 아래는 들어오지도 남지도 않는다 |
| ③ 거래대금 | 직전 63거래일 일거래대금 **중앙값 $1m** | 중앙값 $0.75m | **오너 문장("일평균")과 다르다.** 하루 급등락에 흔들리지 않게 평균 대신 중앙값을 제안한다(`EXP-DEF-NUMBERS`에서 확인). 시총 $250m에서 $1m는 하루 회전율 0.4%(연 약 100%) |
| ④ 주가 | **$5** | **$3** | $5는 저가주를 거르는 흔한 선이다(학술 연구 관행, 예: Jegadeesh·Titman 2001, Amihud 2002는 $5 미만 제외). Nasdaq 상장 유지 기준은 $1이라 $2는 상폐 직전 종목만 거른다 |

- 시총은 발행사 전체 기준(종류주 합산)이다. 거래대금·주가는 그 발행사의 대표 증권(가장 거래가 많은 종류) 기준이다.
- 한 발행사는 1개로 센다. 순위에는 대표 증권 하나만 넣는다(중앙 V의 CIK 대표 규칙과 같다).
- 숫자는 성과를 보고 바꾸지 않는다. 바꾸면 새 정의 버전으로 기록한다.

### 1.2 종류 범위와 ADR

| 포함 | 제외 | 남은 결정 |
| --- | --- | --- |
| 보통주(종류주 각각, 발행사는 1개로 셈), ADR/ADS, 외국 회사 보통주 직접 상장(캐나다 등), REIT, LP(MLP), BDC | ETF·ETN·폐쇄형 펀드, 우선주, 워런트, 권리, 유닛 | SPAC·셸(`EXP-SHELL`) |

ADR을 넣으면 생기는 일(구현 항목, 결정 아님):
- **시총:** 원주 주식수(20-F 표지) × ADS 가격 ÷ ADS 비율. 비율은 SEC 서류(F-6, 20-F Item 12.D)에서 읽는다. 비율을 확인하지 못하면 시총 판정을 보류한다(`ADR_RATIO_UNCONFIRMED`). 중앙 V는 같은 코드로 20-F·40-F 제출사에 가격을 주지 않는 보수 규칙(D7)을 쓴다. 확장은 비율을 읽어 이 보류를 풀어야 ADR을 실제로 넣을 수 있다.
- **통화:** 20-F·40-F 제출사는 재무가 현지 통화다. V 계산에 환율이 필요하다. 후보는 연준 H.10이다(권리는 확인 필요).
- **회계 태그:** IFRS(`ifrs-full`) 태그를 Q·G 지표에 연결해야 한다. 지금 SEC 계산은 US GAAP 중심이다.
- **보고 주기:** 반기 보고 회사가 많다. TTM 신선도 규칙을 따로 정한다(예: 직전 반기 기준, 만료 9개월).
- OTC를 빼면 OTC에서만 거래되는 대형 외국 회사 ADR(Level I)이 빠진다. 오너 정의(①)대로다.

### 1.3 기준별 종목 수 (추정, 측정 아님)

**출발점(공개 1차 자료)**

| 자료 | 숫자 | 날짜 |
| --- | --- | --- |
| CRSP 집계(Jay Ritter, UF): 주요 거래소 상장 **미국 운영회사**(REIT·펀드·ETF 제외, 미합병 SPAC 포함) | **3,657** | 2025년 말 |
| 같은 자료: 주요 거래소 상장 **외국 회사**(ADR 포함, 글로벌 SPAC 포함. "2024~2025년 외국 소형 저가 IPO가 많았다") | **1,515** | 2025년 말 |
| FTSE Russell: Russell 1000/2000 경계("approximately $5.7 billion", 대략 1,000번째 회사) | **약 $5.7B** | 2026-04-30 |
| FTSE Russell: Russell 2000 최하단(3,000번째 회사, 미국 회사만, REIT 포함) | **$146.4m** | 2026-04-30 |
| (참고, 미확인) MSCI USA IMI 구성 종목 수(유동성·유통주식 기준 적용, 미국만). 검색 요약으로만 봤고 원문 페이지는 열지 못했다 | 2,174 | 2026-04-30 |

**미국 회사 시총 분포 추정.** 두 Russell 점(1,000번째 $5.7B, 3,000번째 $146.4m)을 거듭제곱 분포로 이었다: N(≥x) = 3,000 × (x / $146.4m)^−0.300. 한계는 다음과 같다.
- Russell 자격 규칙(국적, 의결권 5%, 적격 종류)을 따르는 수다. REIT는 들어가고, 외국 회사·ADR은 빠진다.
- CRSP 집계(REIT 제외, 미합병 SPAC 포함)와 포함 종류가 달라, 두 자료를 빼서 낸 숫자는 대략이다.
- 4/30 이후 시장 상승분은 반영하지 않았다.
- 두 점만 이었으므로 하단 기울기는 실제와 다를 수 있다.

| 시총 하한 | 미국 회사 수(추정) | 근거 수준 |
| --- | --- | --- |
| $146.4m | 3,000 | Russell 실측점 |
| $200m | ≈ 2,730 | 보간 |
| **$250m** | **≈ 2,560** | 보간 |
| $300m | ≈ 2,420 | 보간 |
| $500m | ≈ 2,080 | 보간 |
| $1B | ≈ 1,690 | 보간 |

**네 기준을 하나씩 넣고 뺄 때(제안값 기준, 발행사 수).** 거래대금·주가 분포는 공개 통계를 찾지 못했다. 아래 범위는 Main의 추론이고 근거가 약하다. 측정으로 바꿔야 한다.

| 경우 | 미국 | 외국(ADR 포함) | 합계 | 근거 수준 |
| --- | --- | --- | --- | --- |
| 거래소만(①) | 3,657 + REIT | 1,515 | 약 5,200+ | CRSP 실측 |
| ①+② 시총 $250m | ≈ 2,560 | 500~800 | 약 3,100~3,350 | 미국 보간 / 외국 추론 |
| ①+②+③ 거래대금 $1m | 2,150~2,350 | 350~600 | 약 2,500~2,950 | 추론: 시총 $250m~$1B 구간에서 주로 빠짐(소형 은행·지배주주 회사·미국 거래가 적은 ADR) |
| **①+②+③+④ 주가 $5 (제안 정의)** | **2,050~2,300** | **300~550** | **약 2,350~2,850** | 추론. 미국 쪽은 참고값 MSCI USA IMI 2,174(미확인)와 비슷한 크기 |
| ④를 $2로 낮추면 | +20~60 | +10~40 | +30~100 | 추론 |
| ④를 빼면 | +70~190 | +30~80 | +100~270 | 추론 |
| ③을 빼면 | +210~420 | +100~250 | +310~670 | 추론 |
| ②를 $200m로 낮추면 | +≈170(시총만), 나머지 기준 뒤 +100~150 | +30~60 | +130~210 | 보간 / 추론 |
| ②를 빼면 | +약 1,100(대부분 ③·④에서 다시 빠짐) | +700~1,000 | — | CRSP(REIT 제외) − Russell 보간(REIT 포함): 기준이 달라 대략 |
| ①을 빼면(OTC 포함) | — | OTC 대형 ADR 수백 개 추가 | — | 측정 안 함, 공급원 권리상 OTC 목록 없음 |

### 1.4 측정 1회 계획 (승인 필요)

확정 숫자를 내려면 다음 두 자료가 필요하다.
1. **SEC 표지 주식수**(무료, 재배포 허용): 기존 Actions의 SEC User-Agent로 받을 수 있다. 새 수동 워크플로라서 승인이 필요하다(`EXP-DRYRUN`과 같은 실행으로 묶을 수 있다).
2. **통합 거래량·종가**(유료): IEX HIST는 IEX 한 곳의 거래량이라 ③에 쓸 수 없다. 공급자 개인 구독이 필요하다(`EXP-PRICE`).

산출물은 기준 조합별 발행사 수 표(집계만)이다. 비공개로 두고, 집계 숫자를 이 문서에 옮겨도 되는지는 공급자 서면 확인 범위에 넣는다. Sharadar는 §8에서 자료 평가 결론의 공개를 서면 승인 사항으로 둔다(§2).

## 2. 가격 공급처 약관 ("가격은 보이지 않고 역산도 안 되며, 점수만 공개" 조건)

2026-10-30에 공개 약관·요금·문서 페이지만 읽었다. 가입·문의·자료 내려받기는 하지 않았다. 원문 인용은 저장한 페이지 사본과 다시 대조했다.

| 공급처 | 판정 | 핵심 조항 | 가격(USD, 개인) |
| --- | --- | --- | --- |
| Sharadar | **서면 확인 필요** | 약관 §2·§4·§6·§8·§10 | 가격만 전체 이력 $39/월($299/년), 5년 $9/월($99/년). 재무 포함 번들 $69/월($499/년) |
| Tiingo | **서면 확인 필요** | 문서 §1.1.6, 요금 페이지. 이용약관은 HTTP 403으로 못 읽음 | Power $30/월($300/년) |
| EODHD | **서면 확인 필요** | 약관 "Personal and Commercial Use of Information" 1·2 | EOD $19.99/월($199/년) |
| Norgate | **서면 확인 필요** | EULA 20261002 정의·§8(i)(ii)(v)·§21 | 가격 표시 못 읽음(10/29 확인: Platinum $630/년) |
| Massive(옛 Polygon) | **서면 동의 없이는 명시 금지** | 시장데이터 약관 §2·§5(c)(d) | Advanced $199/월 |
| IEX HIST | **서면 확인 필요**(확장 용도) | 조항 01·03·08 | 무료 |
| Alpha Vantage | **서면 확인 필요** | §2 | 확인 안 함 |
| Financial Modeling Prep | 판정 못 함 | 약관 HTTP 403 | — |

**명시 허용인 공급처는 없다.** 원문(필요한 부분만):

- **Sharadar** (sharadar.com/terms)
  - §2: "This License is granted solely to natural persons for personal use. … Prohibited uses include, without limitation, professional research, analysis, trading or investing on behalf of others, consulting, operations, publication, …"
  - §4: "You may not publish, disseminate, re-distribute or share the Services Data, or any part thereof, or any derivative data that allows reverse engineering of part or all of the Services Data, with anyone else."
  - §6: "Attribution is not required for research outputs, backtest results, models, summary statistics, trade logs, and similar derived works that do not display the Services Data itself. Public display under this License remains subject to personal use only and does not permit commercial or professional redistribution."
  - §8: "To the extent that you conduct any sort of testing or evaluation of the Services or the Services Data for purposes of determining usability or fitness for purposes intended, the conclusions arrived at related to the value, usability or fitness for purpose, or any other attributes of the Service or the Services Data shall not be published in any way … without prior written approval of Sharadar."
  - §10: "You may keep research outputs, backtest results, models, summary statistics, trade logs, and similar derived works that do not contain and cannot reproduce the Services Data or Sharadar tables."
  - 판단: §4는 금지 대상을 "역산을 허용하는 파생 자료"로 한정하고, §6은 원자료를 보이지 않는 파생물의 공개 표시를 전제한다. 이번 조건과 가장 가깝다. 다만 §2가 "publication"을 금지 용도로 들고, 무료 공개 사이트가 "personal use"인지 불명확하다. §8 때문에 측정 집계(예: 몇 개 회사가 기준을 통과하는지)를 공개하는 것도 승인 대상일 수 있다 → 서면 확인 필요.
- **Tiingo**
  - 문서 §1.1.6: "For Basic and Power accounts, data is for internal and personal use only. You may not redistribute the data in any form." / "If you would like to redistribute the data for commercial or personal use, for example: a presentation, a proposal, a website or app, or any other usage case, please E-mail [영업 이메일, 주소 생략] …"
  - 요금 페이지: "Internal use means you may only use the data for your own personal use and you may not display or share the data with another person or organization"
  - 판단: 웹사이트 이용은 영업 문의로 보낸다. 파생 점수 조항은 없다 → 서면 확인 필요.
- **EODHD**
  - "Non-Professional Users are permitted to store, manipulate, and analyze the data for private, non-commercial purposes. However, they are prohibited from: … Selling, reselling, retransmitting, redistributing, displaying, or granting access to the Information or Services, whether in its original or repackaged form."
  - 판단: 역산 안 되는 순위 구간이 "repackaged form"인지 약관이 말하지 않는다 → 서면 확인 필요.
- **Norgate** (EULA 20261002)
  - 정의 "Derived Data": "… (iv) cannot be reverse-engineered, disassembled, or decompiled to create the Content from which it was produced. Examples of Derived Data include trading results, simulated trading (backtests), and statistics related to those results."
  - §8(i): 다른 사람이 쓰게 하지 않는다, "except where express permission has been sought and obtained from Norgate to publish limited extracts" / §8(ii): "place the Content in a shared, public or multi-user environment …" 금지 / §21: "The Licensee is permitted to retain Derived Data in accordance with this Agreement."
  - 판단: 파생 자료 보관은 되지만 공개 허용 조항이 없다 → 서면 확인 필요.
- **Massive**
  - §5(c): 서면 동의 없이 "Redistribute, display, disseminate, … publish … the Market Data—or any data, charts, analytics, research, or other works based on, referring to, or derived from the Market Data ("Derived Works") — to any third party"
  - 판단: 서면 동의 없는 파생 분석물 공개를 명시적으로 금지한다 → **쓰지 않는다.**
- **IEX HIST** (iex.io/legal/hist-data-terms)
  - 01: "If you distribute, sell, lease, furnish, or otherwise permit or provide access to … IEX historical data, you must cite IEX as the source with the following text and link: …"
  - 판단: 출처 표기를 조건으로 배포를 전제한다. 개인 용도 제한도 없다. 그러나 명시적 허락이 아니라 조건이고 파생물 언급이 없다. 중앙 V 용도는 이미 승인돼 있다. 확장 용도는 서면 확인 필요. 또 IEX 거래량만 있어 거래대금 기준(③)에는 쓸 수 없다.
- **Alpha Vantage** §2: 개인·비상업 용도 외는 서면 합의가 필요하다. "private and individual"을 넘는 이용은 상업 이용으로 본다 → 서면 확인 필요.

**Main 권장:** 서면 문의는 **Sharadar 먼저** 한다. 약관이 "역산을 허용하는 파생 자료"를 금지 기준으로 삼아 이번 조건과 가장 가깝다. 통합 거래량 제공 여부와 ADR(20-F 제출사) 범위는 저장한 페이지로 **확인 안 됨**이라 문의에 함께 넣는다. 문의는 오너 계정·이메일로만 할 수 있어 Main이 보내지 않는다. 문의 초안(영문, 오너가 그대로 보내도 됨):

> I am an individual considering your Personal Use License. I would like to publish, on a free, non-commercial public website, derived scores computed partly from your price data. The only price-based item would be a valuation score shown as one of five buckets (quintiles), published one trading day late. Exact quality and growth scores computed from SEC filings, and their weights, would also be shown; any total score or rank would be computed from the valuation bucket's midpoint, not from an exact valuation. No prices, returns, market capitalizations or exact valuation values would be shown, so prices could not be reconstructed precisely. In a simulation with synthetic prices, the five-bucket score left a price range of roughly ±20–30% (median half-width). I would also like to show aggregate counts, such as how many companies pass a liquidity screen. (1) Is this permitted under your Personal Use License (sections 2, 4, 6, 8 and 10)? If not, which license would cover it, and at what price? (2) Do your price files include consolidated daily volume, and do they cover ADRs of foreign (20-F) filers?

## 3. 역산 시험: 공개 SEC 재무와 V로 가격을 얼마나 맞힐 수 있나

### 3.1 방법

- **재무:** 공개 파일 `sec-qgv2.json`(calc 23.1)의 실제 SEC 값(EBIT, FCF, 부채, 현금, 희석 주식수, 3년 매출 성장)을 그대로 쓴다. 금융 프로필과 EBIT·FCF가 0 이하인 회사는 뺐다(σ = 0.50에서 302개, σ = 0.35에서 301개).
- **가격:** 합성이다. EV/EBIT 배율을 로그정규로 뽑고(중앙값 18배, 성장률에 따라 기울기, 로그 표준편차 σ = 0.50과 0.35) 가격을 역산했다.
- **V 계산:** 저장소 엔진 함수(`qgv_v2._metrics`, `percentile`, `axis_score`)를 그대로 쓴다. 자기 이력 요소(v_vs_own_history)는 과거 월말가가 필요해 뺐다(4요소). 가중치는 균형(Q 34·G 33·V 33), 종류 가중·가치 함정 관문은 끈 단순화다.
- **공격자: "구간을 아는 공격자".** 다른 모든 회사의 진짜 값을 안다고 가정하고, 공개 값과 일치하는 가격 구간을 엔진으로 정확히 찾는다. 구간 안에서 고르는 방법은 세 가지다.
  - (가) 출발 추정을 구간 안으로 자르기. 출발 추정은 전체 회사의 진짜 EBIT·FCF 배율 중앙값(기하평균) × 재무다(업종 구분 없음).
  - (나) 사후 중앙값(정규 사전분포). 사전분포는 다른 회사들의 "진짜 가격 ÷ 출발 추정"에서 맞춘다.
  - (다) 사후 중앙값(경험 분포). 구간에 드는 다른 회사들의 비율 중앙값을 쓴다.
  - 표의 "가장 강한 추정"은 (나)·(다) 중 오차 중앙값이 작은 쪽이다.
- **이것도 상한은 아니다.** 시험하지 않은 새는 길이 있다.
  - 목표 회사의 가격이 움직이면 다른 회사의 공개 구간도 바뀐다.
  - 날마다 구간이 바뀌는 시점이 쌓인다.
  - 모집단 소속(시총 ≥ $200m, 주가 ≥ $3)과 SEC 주식수를 합치면 가격 하한이 나온다.
  - 시총 규모 구간도 가격 범위를 알려 준다.
- **구간 폭:** 추정법과 무관한 지표다. 일치 구간의 로그 폭 중앙값을 "±%"(반폭)로 적는다.
- **기준선:** V 공개가 없을 때 출발 추정의 오차다.
- **T+1:** 공개 값은 전날 가격으로 만들고, 맞힐 대상은 오늘 가격이다. 하루 변동 표준편차는 2%(확장 규모 시험은 3.5%)로 가정했다.
- **오차:** |추정 ÷ 실제 − 1|. 중앙값, 상위 10% 경계(p90), ±5% 안에 든 비율을 적는다.

### 3.2 결과

**σ = 0.50, 302개, 같은 날**

| 공개 수준 | 구간 반폭(중앙값) | 오차 중앙값: (가) / 가장 강한 추정 | ±5% 안: (가) / 가장 강한 추정 |
| --- | --- | --- | --- |
| 공개 없음(기준선) | — | 46.0% | 4.3% |
| V 세부 4요소 백분위, 정밀값(지금 중앙 V 형식) | ±0.26% | 0.21% / **0.10%** | 99.3% / 100% |
| V 백분위(0~100) 정밀값 | ±0.92% | 0.71% / **0.39%** | 94.4% / 97.0% |
| Q·G 정밀값 + 총점 순위(V 숨김) | ±1.15% | 0.97% / **0.53%** | 89.4% / 93.0% |
| **V 10구간** | **±12.3%** | 10.3% / **6.4%** | 28.5% / 39.4% |
| V 10구간, 총점·순위도 구간 중앙값으로 계산 | ±12.5% | 10.3% / 6.5% | 28.5% / 38.7% |
| **V 5구간** | **±28.8%** | 18.9% / **12.0%** | 14.9% / 23.5% |
| V 3구간 | 사실상 열림(±197%) | 26.0% / **19.1%** | 9.3% / 13.6% |

**σ = 0.35, 301개, 같은 날:** 기준선 35.1%. 가장 강한 추정의 오차 중앙값은 다음과 같다.
- V 세부 정밀 0.11%(반폭 ±0.20%), V 백분위 정밀 0.34%, 총점 순위 0.42%
- **10구간 4.9%(반폭 ±9.1%, ±5% 안 50.8%)**
- **5구간 8.9%(반폭 ±20.4%, ±5% 안 30.2%)**
- 3구간 13.3%

**확장 규모(합성 1,509개, 무작위 300개 대상, 같은 날):** 실제 SEC 재무 302개를 흔들어 5배로 늘렸다(재무·주식수에 무작위 잡음). 기준선 47.9%. 가장 강한 추정의 오차 중앙값은 다음과 같다.
- V 세부 정밀 **0.02%**(반폭 ±0.05%), V 백분위 정밀 0.07%, 총점 순위 0.11%
- **10구간 6.3%(반폭 ±11.8%)**
- **5구간 12.4%(반폭 ±29.5%)**

**T+1((가) 추정, σ = 0.50):**
- 정밀 V 세부: 0.21% → 1.33%(확장 규모 0.04% → 2.4%)
- 10구간 10.3% → 10.5%, 5구간 18.9% → 19.0%

**실제 공개 파일 확인:** 지금 `qgv-official.json`에서 V가 총점에 들어간 265행(전체 523행 중)은 총점·Q·G·가중치만으로 V 축 점수가 **모두 정확히 풀린다**(최대 차이 7×10⁻¹⁴).

**단순 공격자(참고):** 공개 자료만 쓰고 출발 추정에서 전체 가격을 5회 반복해 맞추는 방법이다. 출발 추정의 배율 중앙값은 진짜 값에서 계산해서, 완전히 공개 자료만 쓴 것은 아니다. σ = 0.50에서 같은 날 오차 중앙값은 다음과 같다.
- V 축 정밀 13.7%
- V 백분위 정밀 39%
- 10구간·5구간 약 40%
- 세부 4요소를 동시에 맞추는 경우는 수렴하지 않아 기준선보다 나빴다.

Main이 만든 단순한 방법이라 안전의 근거로 쓰지 않는다.

### 3.3 해석

1. **정밀값은 사실상 가격 공개다.** V 세부 백분위나 V 축 점수를 정밀하게 공개하면, 구간을 아는 공격자는 가격을 0.1%(302개)~0.02%(1,509개) 오차로 맞힌다. 회사가 많을수록 더 정확해진다.
2. **"백분위"도 정밀하면 안 된다.** 0~100 정밀 백분위는 0.07~0.4% 오차다. 구간으로 묶어야 한다.
3. **총점과 순위가 새는 길이다.** Q·G·가중치가 공개이므로 V를 숨겨도 정밀 총점에서 V가 정확히 풀린다(실제 파일로 확인). 총점 순위만으로도 0.1~0.5%로 좁혀진다.
   - **총점과 순위는 V 구간의 중앙값으로 계산해야 한다.**
   - 그러면 새는 정보가 V 구간과 같아진다(10구간 6.4% ≈ 6.5%).
4. **T+1만으로는 막지 못한다.** T+1은 하루 변동만큼 오차를 더할 뿐이고, 전날 가격은 그대로 풀린다. 실시간 대체를 막는 효과는 있다.
5. **구간 수가 핵심이다.** 같은 공개 정보로 가격이 들어갈 수 있는 범위(반폭)는 10구간 ±9~12%, 5구간 ±20~29%이고, 3구간은 사실상 막지 않는다.
   - 다만 사전 지식을 잘 쓰는 공격자는 그 범위 안에서 더 잘 고른다. 오차 중앙값은 10구간 5~6%, 5구간 9~12%, 3구간 13~19%다(기준선 35~48%).
   - V 신호를 조금이라도 보이면 정보는 일부 나간다. 0으로 만들 수는 없다.
6. **시험하지 않은 길(§3.1)** 때문에 실제 새는 정도는 위 숫자보다 클 수 있다. 갱신을 주 1회로 줄이면 시점이 쌓이는 문제는 줄어든다(시험 안 함).

### 3.4 공개 규칙 제안 (확장 모집단, 구현 전)

| 항목 | 공개 | 근거 |
| --- | --- | --- |
| Q·G 세부 요소 점수, Q·G 축 점수, 가중치 | 공개(정밀값) | 오너 결정 5. 가격과 무관 |
| V 세부 5요소 | **숨김** | 오너 결정 5, §3.2 |
| V | **5구간**(권장) 또는 10구간, **T+1**. 3구간은 더 강하지만 신호가 크게 줄어든다 | §3.3-5 |
| 총점·순위 | **V 구간 중앙값으로 계산한 값만** | §3.3-3 |
| 시총 | **숨김.** 규모 구간만(예: $0.2–2B / $2–10B / $10B+) | 오너 결정 5. 규모 구간 ÷ SEC 주식수도 가격 범위를 준다(시험 안 함) |
| 가격 의존 사유 코드(예: `EV_NON_POSITIVE`) | 중앙 V처럼 `PRICE_DEPENDENT_NOT_COMPUTABLE` 하나로 묶어 공개 | 원 코드는 가격 경계를 바로 알려 준다. 다만 중앙 V 감사(`public_price_boundary/AUDIT.md` §10-3)대로 묶어도 경계 정보는 남는다 |
| 기준 판정(①~④ 통과 여부) | 공개하지 않음(모집단 소속만) | 문턱 통과 여부도 가격 정보다. 소속 자체도 시총·주가 하한을 알려 준다(시험 안 함) |

중앙 V(Universe504)는 이번 결정 대상이 아니다. 지금 형식(V 세부 정밀 백분위)은 IEX 출처 표기 조건으로 승인돼 그대로 둔다. 중앙 V 감사(§10-3)는 "다른 종목 가격을 알면 이웃 사이 구간이 나온다, 점 복원은 안 된다"고 적었다. 이번 합성 시험에서 그 구간의 반폭은 중앙값 ±0.26%(302개)였다. 중앙 V에도 같은 규칙을 적용할지는 오너가 원할 때 따로 정한다.

## 4. 결정표 정리

10/29 보고의 결정 9개를 이 결정으로 다시 분류했다. **완전히 해결된 것은 없다.** `EXP-CPI-POLICY`만 범위가 줄어 한 줄 확인으로 바뀌었다.

| 번호 | 처리 | 이유 |
| --- | --- | --- |
| EXP-CPI-POLICY | **범위 축소 → 한 줄 확인** | 오너 문장은 CPI를 말하지 않았다. Main은 "약 $200m"을 오늘 달러 명목으로 읽었다(§0). 확인할 것은 "현재 판정은 명목인가" 하나다. CPI 계열·기준·발표 시각 정책은 #418 과거 모집단 자료가 생길 때 다시 묻는다(지금은 `BLOCKED_ON_DATA`) |
| EXP-C03-MEANING | 남음 | 정의와 무관(사건 시점 해석) |
| EXP-ID-RELIST | 남음 | 정의와 무관(재상장 ID) |
| EXP-GENESIS | 남음 | 정의와 무관(초기 적재) |
| EXP-CORE-LIVE | 남음 | 정의와 무관(코어 실자료 라벨) |
| EXP-QUARANTINE | 남음 | 정의와 무관(문제 사건 처리) |
| EXP-OPENFIGI | 남음 | ADR 포함으로 쓸모가 커졌다(ADR↔원주 연결). 권장은 그대로(측정 M3 뒤) |
| EXP-SHELL | 남음 | 네 기준만으로는 SPAC가 걸러지지 않는다(신탁금으로 시총·$10 주가 통과) |
| LAB-GUARD-KEYS | 남음 | 정의와 무관(9.1 Lab 가드 키) |

같은 결정으로 원칙이 정해진 기존 항목:
- **EXP-PUBLIC:** "점수만 공개, 가격 파생 정밀값 숨김"으로 원칙 결정. 남은 것은 V 구간 수(`EXP-V-BUCKET`)와 공급처 서면 확인이다.
- **EXP-PRICE:** "점수만 공개" 조건으로 공급처 검토. 명시 허용 공급처가 없어(§2) 남은 것은 서면 문의 대상과 측정용 구독이다.

이 결정으로 새로 생긴 질문:
- **EXP-DEF-NUMBERS:** §1.1 숫자와 §1.2 종류 범위.
  - 숫자: 진입 $250m/유지 $200m, 거래대금 중앙값 $1m/$0.75m, 주가 $5/$3, 월 1회.
  - 거래대금을 "일평균" 대신 중앙값으로 바꾸는 것도 함께 확인받는다.
- **EXP-V-BUCKET:** V를 5구간(권장)으로 할지 10구간으로 할지, 그리고 총점·순위를 구간 중앙값으로 계산하는 규칙.
