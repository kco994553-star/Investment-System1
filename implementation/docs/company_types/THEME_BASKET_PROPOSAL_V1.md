# 테마 v1 바스켓·키워드 제안 — 사용자 확인 대기

GSQ-017: Q/G/V 비중 영향 없이 노출·쏠림 경고용. 버전 있는 [`theme_config_v1.json`](../../src/investment_system/qgv/theme_config_v1.json)에 14개 정의·ETF·키워드·한계를 분리했다. type_config의 exposure-only 부분에 넣을 companion 설정이며 공식 유형 원본을 수정하지 않는다. `membership_rule=null`, baskets_confirmed=false: 확인 전 자동 소속도는NA다. 공식 설정과 사용자 복사본/override는 섞지 않는다.

2026-10-10 발행사 페이지 HTTP200·상품 제목/티커를 확인했다. **ETF 존재 확인은 N-PORT fund series/class 식별이나 실제 holdings 취득 성공이 아니다.** 현재 SEC series/class ID는null이며 임의 CIK/ticker 매칭·가격·현 보유 추정을 하지 않는다. ETF 매수 추천이 아니다.

| 테마 | ETF 후보 | 10-K Item1 키워드 제안 | 한계 |
| --- | --- | --- | --- |
| AI | [AIQ](https://www.globalxetfs.com/funds/aiq/) | artificial intelligence, generative ai, machine learning | BOTZ는 로봇 바스켓에서 사용; 반도체와 중복 가능 |
| 반도체 | [SOXX](https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf), [SMH](https://www.vaneck.com/us/en/investments/semiconductor-etf-smh/) | semiconductor, integrated circuit, wafer, chip fabrication | 장비·설계·파운드리 혼합 |
| 클라우드·소프트웨어 | [SKYY](https://www.ftportfolios.com/Retail/Etf/EtfSummary.aspx?Ticker=SKYY), [CLOU](https://www.globalxetfs.com/funds/clou/) | cloud computing, software as a service, enterprise software | 순수 클라우드 아닌 소프트웨어 포함 |
| 사이버보안 | [CIBR](https://www.ftportfolios.com/Retail/Etf/EtfSummary.aspx?Ticker=CIBR), [HACK](https://www.amplifyetfs.com/hack/) | cybersecurity, cyber security, endpoint security, network security | 광범위 IT와 중복 |
| 핀테크·결제 | [FINX](https://www.globalxetfs.com/funds/finx/), [IPAY](https://www.amplifyetfs.com/ipay/) | payment processing, digital payments, financial technology | 핀테크와 결제업무를 구분할 수 없음 |
| 전자상거래 | [IBUY](https://www.amplifyetfs.com/ibuy/), [EBIZ](https://www.globalxetfs.com/funds/ebiz/) | e-commerce, ecommerce, online marketplace | 유통·플랫폼 혼합 |
| 전력 인프라 | [GRID](https://www.ftportfolios.com/Retail/Etf/EtfSummary.aspx?Ticker=GRID), [PAVE](https://www.globalxetfs.com/funds/pave/) | electric grid, power transmission, grid infrastructure, power distribution | PAVE는 미국 인프라 전반이며 전력 순수성 낮음 |
| 클린에너지 | [ICLN](https://www.ishares.com/us/products/239738/ishares-global-clean-energy-etf), [QCLN](https://www.ftportfolios.com/Retail/Etf/EtfSummary.aspx?Ticker=QCLN) | renewable energy, solar energy, wind power, clean energy | 공급망·전기차 혼합, 수익성/가치 판정 아님 |
| 방산·우주항공 | [ITA](https://www.ishares.com/us/products/239502/ishares-us-aerospace-defense-etf), [XAR](https://www.ssga.com/us/en/individual/etfs/spdr-sp-aerospace-defense-etf-xar) | aerospace, defense systems, defence systems, space systems | 민항을 포함; 우주 전용 바스켓 아님 |
| 바이오·비만치료제 | [IBB](https://www.ishares.com/us/products/239699/ishares-nasdaq-biotechnology-etf), [XBI](https://www.ssga.com/us/en/individual/etfs/spdr-sp-biotech-etf-xbi) | biotechnology, glp-1, obesity treatment, weight management | 비만치료제 순수 노출 아님; 대형 제약 누락 가능 |
| 의료기기 | [IHI](https://www.ishares.com/us/products/239516/ishares-us-medical-devices-etf) | medical device, surgical instrument, diagnostic device | 미국 의료기기 중심이며 해외 coverage 제한 |
| 데이터센터·리츠 | [DTCR](https://www.globalxetfs.com/funds/dtcr/) | data center, data centre, digital infrastructure, colocation | DTCR에는 데이터센터 외 디지털 인프라 포함 |
| 로봇·자동화 | [BOTZ](https://www.globalxetfs.com/funds/botz/), [ROBO](https://www.roboglobaletfs.com/robo) | robotics, industrial automation, robotic automation | AI·산업장비와 중복 |
| 소비자 브랜드 | [XLP](https://www.ssga.com/us/en/individual/etfs/the-consumer-staples-select-sector-spdr-fund-xlp), [XLY](https://www.ssga.com/us/en/individual/etfs/the-consumer-discretionary-select-sector-spdr-fund-xly) | consumer brand, branded products, brand portfolio | 미국 소비 업종 proxy이며 브랜드 분류와 동일하지 않음 |

## SEC 원기관 수집 계약 / 분기

[SEC Form N-PORT Data Sets](https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets) 원문을 확인했다: monthly portfolio holdings 보고 자료이며 data sets는 **분기 갱신**, 공개 disseminated filings만 포함한다. 보고 월·제출 시점·공개 시점·취득시각을 구분한다. 분기 배치일이나 월말을 최초 공개 시각으로 소급하지 않는다. 제출빈도/공개 지연 규정은 운영 시 재확인하고 해당 원문 지연을 따르며 비공개 보고를 추론하지 않는다.

1. 후보 ETF를 exact SEC registrant CIK+series ID+class ID로 결속(동명 상품/동일 registrant의 다른 펀드 금지). 확인 전 수집 binding 없음.
2. 공개 NPORT-P 계열 filing의 보고월·acceptance/public availability·amendment를 보존. 공급 cutoff 이전 자료만 사용; 여러 보고월 혼합 비교·정정 자동 대체 금지.
3. 직접 equity holding과 security/issuer 식별이 확인된 기록만 thematic evidence로 추출. 파생상품·현금·펀드 look-through를 주식 노출로 바꾸지 않는다. 보유 ETF 수/각 reported portfolio weight·유효 ETF 수·결측 ETF 목록을 보존한다. source weight가 없는 경우0 대체 금지.
4. actual N-PORT fetch/parser/bulk500 결합은 후속이다. 이번 구현은 공급된 근거의 집계와 keyword 빈도·기기 override이며 공개 producer/사용자 포트폴리오/가격에는 연결하지 않는다.

## pure Python 계약

`theme_exposure.summarize_theme_exposure(config=..., etf_evidence={ticker:{held,portfolio_weight,source:'SEC_NPORT'}}, item1_text=None, market='US', industry_default=None, overrides=None)`.

호출자는 ETF/fund·issuer·security·as-of 적격성을 먼저 검증한다. 함수는 입력 출처 진위를 증명하지 않는다. 알려진 ETF 근거가 없거나 불량이면 count도None·소속도None. 알려진 미보유가 공급되면 관측 count0은 가능하되 membership은 정규화 미정으로NA. raw Item1 text는 반환/저장하지 않고 사전에 있는 literal phrase의 빈도만 반환한다; 전체10-K·Item1A·HTML nav·risk text를 섞거나 단순 'AI' 문자열을 검색하지 않는다. 빈도는 최종 소속도가 아니며 `keyword_counts=0`은 실제 제공 Item1에서 관측한0이다.

종목당 상위2는 검증된 사용자 override0~1이 있을 때 표시한다(동률 config순서). override0 허용, 빈 display 허용. 자동 membership은NA이므로 빈 표시를 실제 ‘테마 없음’ 판정으로 해석하지 않는다. override는 DEVICE_PREVIEW·기기 저장만, 공식 근거 원본이나 Q/G/V를 바꾸지 않는다. 기기 저장/화면은 코덱1.

KR/JP는 사용자 공급 업종 기본값과NA, Item1 keyword/미국 N-PORT 근거를 DART/EDINET 공시의 대용으로 만들지 않는다. ETF 누락/범위·상장국·중복 테마 때문에 ‘500개 coverage’는 목표이지 이번 검증 결과가 아니다.

## 결정 필요

- 위14개 바스켓·키워드 채택/수정. GRID+PAVE의 광범위 인프라, IBB/XBI의 비만치료제 누락, XLP/XLY의 브랜드 proxy를 특히 확인한다.
- ETF 보유 수와 각 비중의0~1 정규화/결합 방식, 누락 ETF의 denominator, Item1 keyword 보완 규칙. 아직 수학적 정의·임계값이 없으므로 임의 새 산식·가중치는 넣지 않았다.
- 쏠림 경고 기준(포트폴리오 노출 한도/중복 테마 집계): 미정, 현재 경고 임계값 추가 없음.
