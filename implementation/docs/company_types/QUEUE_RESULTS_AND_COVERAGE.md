# TARGET19·500회사 목표 — 원자료/정의 커버리지 결과

2026-10-10, canonical #141/#143 이후 작업 환경. **NOT_AVAILABLE(NA)는미제공이고소속도0/점수0/‘테마없음’확정이아니다.** 실제종목결과를합성수치·업종명추측·metadata성공기록으로대체하지않았다. #135 유형/GSQ-017은 사용자 승인 후 병합됐다. SIC 표는 별도 사용자 확인 전 비활성이다.

## TARGET19 결과표

| 종목 | 성장 | 우량 | 경기민감 | 경기방어 | Q요소 | G요소 | 테마 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ASML | NA | NA | NA | NA | NA | NA | NA |
| LRCX | NA | NA | NA | NA | NA | NA | NA |
| KLAC | NA | NA | NA | NA | NA | NA | NA |
| 도쿄일렉트론 | NA | NA | NA | NA | NA | NA | NA |
| 한미반도체 | NA | NA | NA | NA | NA | NA | NA |
| NVDA | NA | NA | NA | NA | NA | NA | NA |
| AMD | NA | NA | NA | NA | NA | NA | NA |
| AVGO | NA | NA | NA | NA | NA | NA | NA |
| QCOM | NA | NA | NA | NA | NA | NA | NA |
| INTC | NA | NA | NA | NA | NA | NA | NA |
| MSFT | NA | NA | NA | NA | NA | NA | NA |
| GOOGL | NA | NA | NA | NA | NA | NA | NA |
| AMZN | NA | NA | NA | NA | NA | NA | NA |
| RTX | NA | NA | NA | NA | NA | NA | NA |
| SYK | NA | NA | NA | NA | NA | NA | NA |
| ETN | NA | NA | NA | NA | NA | NA | NA |
| HUBB | NA | NA | NA | NA | NA | NA | NA |
| GEV | NA | NA | NA | NA | NA | NA | NA |
| ROK | NA | NA | NA | NA | NA | NA | NA |

미국17개는RAW_BODY_NOT_PRESENT: STORE_INDEX의SEC_COMPANYFACTS취득metadata1117건·SEC_SUBMISSIONS1172건이있지만blobs실제파일0개(.gitkeep만),companyfacts원문별도파일0개다. 원문단위·연차범위·CIK·SHA를재현할수없어기존map_raw의Q/Gleafscore를산출하지못한다. public_sec_inputs schema3는주식수projection이므로companyfacts 재무원문의대용이아니다. 기준소속도는연차3YCAGR용4년매출이필요하다. 우량마진/부채결합·민감/방어변동성은정의도미정이다. 한국은DART_WAITING_USER_NOTICE,일본은EDINET_DEFERRED다. 배당/가치/주도는가격필요이므로이표대상에서제외했다. 테마는NPORT원문/Item1원문미공급및정규화미정이다.

## SEC daily 실제실행과 재무점수 재현의 차이

Actions workflow_dispatch **38039786166**,head303ae501854b1926bd21e406279cfe228d87dd26,completed/success에서고정진단만추출했다: **BUILD_OK / failed_companies=0**,company_index8(HUBB)의VALUE_INVALID행제외코드가있다. 로그값·URL·UA는출력하지않았다. #138의‘badfact한줄제외/핵심개념존재시회사유지’운영결과는확인됐다. 개별badrow의실제원본값·정확한원문줄은이실행환경에없어확정하지않았다. normalize성공17/17은전체재무Q/G실측17/17이아니다. 이전3실패의원인을IFRS라고단정하지않는다.

## 500회사 목표 커버리지

| 단계 | 검증된수 | 해석/제한 |
| --- | --- | --- |
| 승인code-only Universe |504개/중복없는504listing | 가격·시총·★·SheetID없음. 현재명단/PIT/currentS&Pmembership보증아님. |
| 목표 |500회사 |504listing과issuer500의CIK중복/누락관계를아직실측하지않음. |
| 로컬rawbody |0개 | metadata6808건중fact1117/sub1172/NPORT1/NPORTXML5는원문보존성공을증명하지않음. |
| TARGET19의재현가능Q/G |0/19 | source미공급NA.18/19등가공한점수커버리지주장없음. |
| TARGET19의실측가격없는유형 |0/19 | rawbody없음+일부유형정의미확정. |
| 자동테마membership |미확정/NA |바스켓14개/ETF25개존재확인과500companycoverage는별개.원문eligibleETFcoverage/issuerjoin·정규화정의없음. |
| Universe 실제CIK결속·daily취득 |미실측/NA |공급SECticker/exchange registry와분할collector준비,실제504대량취득안함. |

`0/19`는**관측 가능한결과수0개**이지각종목membership/score0이아니다.500개커버완료를주장할조건:source당as_of/공개시점·원문hash,eligiblefund/issuer/securityjoin,원자료결측과기준미정구분,각500회사결과수·unknown수보고. 회사500을504로자동대체하거나두shareclass를임의합산하지않는다.

## 테마바스켓 최종제안 — 아직확정아님

14개정의·25ETF·literalItem1keywords를[THEME_BASKET_PROPOSAL_V1.md](THEME_BASKET_PROPOSAL_V1.md)와버전theme_config/1에정리했다. 최종확인용목록: AI=AIQ;반도체=SOXX/SMH;클라우드=SKYY/CLOU;사이버=CIBR/HACK;핀테크=FINX/IPAY;전자상거래=IBUY/EBIZ;전력=GRID/PAVE;클린=ICLN/QCLN;방산=ITA/XAR;바이오/비만=IBB/XBI;의료기기=IHI;데이터센터=DTCR;로봇=BOTZ/ROBO;브랜드=XLP/XLY.

PAVE광범위인프라·IBB/XBI의비만치료제대형제약누락·XLP/XLY업종proxy는한계로남긴다. 바스켓ticker존재HTTP200은SECregistrant/series/class 식별확인이아니다. 사용자확인없이어느바스켓도baskets_confirmed로바꾸지않았다. NPORT공개holdings우선·Item1키워드보완·상위2표시/테마없음허용·기기override구조는구현됐으나보유ETF수/비중0~1정규화·keyword결합·쏠림경고threshold는미정이다. Q/G/V영향없음.

## SIC→업종군 매핑 초안 — 별도 사용자 확인 대상

사용자 후속 승인 조건: **표 확인 전 경기민감·경기방어는 NOT_AVAILABLE 유지**. 아래는 SEC SIC 산업 설명을 넓게 묶은 초안이며 민감/방어 판정표가 아니다. GICS 자료를 쓰지 않는다. 설정의 industry.groups는 비어 있으며 현재 계산에 적용하지 않았다.

| SIC 범위/코드 | 업종군 초안 | 확인할 점 |
| --- | --- | --- |
| 1000~1499 | 자원·광업 | commodity별 사업 혼합 확인; 민감 후보를 확정하지 않음 |
| 1500~1799 | 건설 | 산업 건설·주택 등 세부 사업 확인 |
| 2000~2199 | 식품·담배 | 방어 후보 검토; 2080 음료 등 세부 차이 |
| 2200~3999 | 제조·산업·기술 | 한 범위로 민감 판정 금지. 357x 컴퓨터·3674 반도체·384x 의료기기 분리 필요 |
| 4000~4799 | 운송·통신 | 물류·항공과 통신을 분리해야 함 |
| 4900~4999 | 유틸리티 | 방어 후보 검토; 발전사업과 전력장비 제조의 SIC 구분 |
| 5000~5999 | 유통·소매 | 5411 식품 소매와 경기민감 소비 구분 |
| 6000~6799 | 금융·부동산 | 은행·보험·REIT 별도 검토; 동일 변동성 램프 적용 금지 |
| 7000~8999 | 서비스·소프트웨어·의료 | 737x 소프트웨어와 8000~8099 의료 분리 필요 |

원기관: [SEC SIC Code List](https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list). 없는 SIC·0000·사업/종류 불일치는 NA다. 표의 범위 채택과 회사별 사업 혼합, 매출 변동성의 비교 기간/램프 및 결합 규칙은 별도 확인 사항이다. 표를 확인했다고 새 민감/방어 산식까지 자동 채택하지 않는다.

## 사용자결정/정의미확정

1. #135 병합은 사용자 승인됨. 위 SIC 매핑 표는 별도 사용자 확인 대기이며 경기민감·방어는 NA 유지.
2. 우량마진안정/부채낮음threshold·결합,가치P/E·EV/EBIT업종/자기과거basis·discount램프,경기민감/방어SIC표·매출변동성램프/결합,5년정규화이익→V점수.새산식자동창작없음.
3.14테마바스켓/keywords수정·채택,ETFcounts+weights정규화·누락분모·keyword보완/경고기준.
4. DCF10%/2%등기본파라미터제안과FCFE출처산식·통화·주당/ADR/splitbasis.확인전NOT_AVAILABLE.
5. [매크로8축대응초안](../macro_data_rights/EIGHT_AXIS_MAPPING_PROPOSAL.md)의GDP전기비연율/CPI NSA YoY및후속exactselector·8×6추가상태정의.확인전국면NA.
6. DART사용자키등록알림후만착수;EDINET보류. v2/forward시작일은향후사용자결정,에이전트기간선택/사용없음.
