# 개인 무료 시세 API와 사용자 전용 릴레이 선택안

검토일은 **2026-10-09 UTC**입니다. **공식 자료만으로 무료 19종목 시세와 USD/KRW·JPY/KRW를 모두 충족하는 단일 서비스를 확정하지 못했습니다. 26E 서비스 선택은 WAIT, B 외부 조회는 OFF를 유지합니다.** 한국투자증권 KIS는 한국·미국·Tokyo TSE 조회 시장을 함께 문서화한 후보이지만, 19개 개별 종목의 이용권·응답과 필요한 환율의 코드·단위는 확인되지 않았습니다. 앱키와 앱시크릿 노출 금지 때문에 사용자 전용 서버 릴레이도 함께 검토해야 합니다.

현재 검토 모델은 개인 사용자가 **자기 API 키로, 갱신 버튼을 누를 때만** 공개 TARGET19 시세와 환율을 조회하는 방식입니다. 실제 보유수량·평균단가·입력값은 기기에 남고 공급자에게 보내지 않습니다. 공용 공급자 키, 공개 가격 JSON, GitHub Actions 시세 수집, 공개 재배포는 이 선택안에 포함하지 않습니다. 계좌 연결·키 발급·서비스 가입·유료 신청·시세 수집·Worker 설정을 수행하지 않았습니다.

## 확인해야 할 공개 대상

| 구분 | 승인된 공개 식별자와 원통화 | 이번 연구의 증거 범위 |
| --- | --- | --- |
| 미국 17종목 | `ASML`, `LRCX`, `KLAC`, `NVDA`, `AMD`, `AVGO`, `QCOM`, `INTC`, `MSFT`, `GOOGL`, `AMZN`, `RTX`, `SYK`, `ETN`, `HUBB`, `GEV`, `ROK` · USD | 미국시장 제공 문서는 확인. **각 종목의 무료 계정 실제 가격 응답 17/17은 검증하지 않음.** ASML은 승인된 NASDAQ 종목, Alphabet은 Class A GOOGL을 유지. |
| 일본 1종목 | Tokyo Electron `TSE:8035` · JPY | Twelve Data 공식 참조 카탈로그에 존재. KIS의 TSE 시장 조회 문서는 존재. 두 사실 모두 8035의 무료 가격 응답을 보증하지 않음. |
| 한국 1종목 | 한미반도체 `KRX:042700` · KRW | Twelve Data 공식 참조 카탈로그에 존재. KIS 국내 KRX와 금융위원회 국내 시장 범위는 확인. 해당 종목의 이용권·가격 행 응답은 미검증. |

이 목록은 실제 보유목록이 아닌 공개 카탈로그입니다. `8035`를 미국 OTC/ADR로, `ASML`을 Amsterdam 종목으로, `GOOGL`을 `GOOG`로 대체하지 않습니다. 공급자별 종목 코드·거래소·원통화 대응은 이후 승인된 검증에서 별도로 확인해야 합니다. [기존 공개 TARGET19 선택안](../pages_cockpit_owner/QUOTES_FX_OPTIONS_26E.md)

## 무료 후보 5개 비교

| 후보 | 무료 범위와 지연 | TARGET19에서 확인된 것과 미확인인 것 | USD/KRW와 JPY/KRW | 브라우저·키 조건 |
| --- | --- | --- | --- | --- |
| **한국투자증권 KIS Developers** | 기본 API 무료 안내 존재. 계좌 보유·계좌/ID 연결·서비스 신청·본인 확인이 필요. 미국은 무료 0분 지연 Nasdaq TotalView 시장센터 자료, 일본은 무료 15분 지연. 전체 미국 통합 SIP와 같다고 볼 수 없음. 현재 호출 한도는 별도 확인 필요. | 국내 KRX 및 해외 `NAS/NYS/AMS/TSE` 조회 코드가 공식 문서에 있음. **세 시장 지원 확인과 19개 개별 종목 확인은 다름.** 19/19 응답·상품별 계좌 자격은 미확인. | FX 차트 조회 구분은 존재하나 필요한 두 원화 환율의 정확한 코드·방향·1 JPY/100 JPY 단위·시점은 미확인. 계좌 잔고의 환산 필드를 일반 환율 대용으로 채택하지 않음. | `appkey` + `appsecret`로 24시간 bearer 발급; 시세 요청에도 두 값이 요구됨. 공식 노출 금지 경고. 무키 오류 GET의 CORS 헤더만 관측했고 인증 브라우저 흐름은 미검증. **개인 전용 릴레이 후보로 검토.** |
| **Twelve Data Basic** | 무료 **8 API credits/분, 800/일**. 기본 미국 실시간 주식과 FX가 포함된다고 안내. 국제시장 확장은 상위 요금제·일부 trial symbols로 구분. | 미국시장 지원은 확인. Tokyo 8035·KRX 042700 참조 카탈로그 확인. KRX는 EOD 및 Core data가 있지만 무료 trial 종목은 `000080`; 042700의 Basic 가격 접근권은 미확인. Tokyo 거래소는 delay `–`, Core 가격 엔드포인트 없음. **19/19 무료 불확정.** | 공개 FX 참조 메타데이터에 `USD/KRW`, `JPY/KRW` 존재. Basic의 일반 FX 포함 안내는 확인했지만 두 쌍의 인증 무료 가격 응답은 미검증. | 무키·무종목 `/price` 오류에서 CORS `*` 관측. 약관은 credentials 비밀 유지·공유 금지. 브라우저에서 개인 키를 노출할 수 있다는 명시 허용은 찾지 못함. 가격표 Basic은 **internal non-display**로 표시되어 개인 대시보드 표시 권한도 확인 필요. |
| **Alpha Vantage Free** | 무료 **25 API requests/일**. `GLOBAL_QUOTE`는 1종목/요청, 기본 EOD 갱신. 미국 실시간·15분 지연은 유료. 오래된 5회/분 수치를 현재 제한으로 가져오지 않음. | 미국 및 일부 국제시장의 일반 주식 API 문서는 확인. 승인된 17개 미국 종목과 Tokyo 8035·KRX 042700의 무료 개별 접근권은 미검증. 일본/한국을 다른 시장 종목으로 대체하지 않음. | `CURRENCY_EXCHANGE_RATE`의 `from_currency`→`to_currency` 문서와 물리 통화 목록의 USD·JPY·KRW를 확인. 두 원화 쌍은 문서 형식상 요청 후보이며 실제 무료 응답은 미검증. | 자기 소유·통제 기기의 개인 비상업 사용을 약관이 허용. 무키·무함수 오류 GET에서 CORS `*` 관측. **브라우저 키 노출에 대한 별도 명시 허용과 실제 인증 CORS는 미확인.** |
| **Market Data Free Forever** | **$0/월, 카드 불필요, 100 credits/일**, 최소 24시간 지연, 과거 1년. trial만 무료인 서비스와 구분. 주식 quote 비용은 종목당 1 credit. | 공식 상품은 미국 주식/ETF 중심. 17개 개별 무료 응답은 미검증. Tokyo 8035·KRX 042700 지원 근거 없음. 따라서 전체 TARGET19 후보로 확정하지 않음. | 이 서비스의 공식 검토 범위에서 FX 엔드포인트·필요 두 쌍을 확인하지 못함. 별도 FX 공급자가 필요할 가능성. | **공식 문서가 개인 브라우저 대시보드와 CORS를 명시적으로 허용.** 단 접근을 본인이 통제하는 환경이어야 하며, 공용 페이지에 토큰 삽입·다른 사람에게 데이터 제공은 금지. 공개 앱 셸에서 사용자 각자의 키를 입력하는 배포모델까지 허용된다고 자동 해석하지 않음. |
| **공공데이터포털 금융위원회 주식시세정보 V2** | 포털에 무료, 개발/운영 자동 승인, 개발 트래픽 10,000 표기. 상세 설명은 **1일 1회, 기준일 다음 영업일 13시 이후 갱신**. 요약 메타데이터의 실시간 표시보다 상세 갱신 설명을 적용. | `KOSPI/KOSDAQ/KONEX` 국내 시장, 6자리 `srtnCd`, 종목명, 기준일·종가 정의를 확인. 042700의 실제 제공 행은 미검증. 미국 17·Tokyo 8035는 이 데이터셋 범위 밖. | 주식 데이터셋이며 FX를 제공한다는 근거 없음. `clpr` 종가 정의는 확인했지만 제공자 문서의 통화 단위 명시는 확인하지 못함; 국내/KRW 카탈로그 문맥만으로 단위 검증을 대신하지 않음. | 개인 `serviceKey` 필요. 무키 preflight와 오류 GET의 Origin 허용을 관측했으나 인증 성공 GET·개인 브라우저 키 사용 조건은 미검증. 현재 포털 이용조건과 제3자 제공 금지를 지켜야 함. 필요하면 사용자 전용 릴레이 검토. |

KIS: [기본 무료 FAQ](https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000002/post/beb2459a-f6b4-432e-928a-d3462dd0daef), [시작 안내](https://apiportal.koreainvestment.com/about-howto), [해외 현재가 공식 문서](https://apiportal.koreainvestment.com/api/apis/public/detail?accessUrl=%2Fuapi%2Foverseas-price%2Fv1%2Fquotations%2Fprice), [거래소·키/시크릿 공식 schema](https://apiportal.koreainvestment.com/api/apis/guide/property/3eeac674-072d-4674-a5a7-f0ed01194a81), [공식 해외 현재가 샘플](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/price/price.py), [계좌별 신청 가능 범위 FAQ](https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000002/post/0b29069f-812b-4a70-94db-63d07d5ad54c).

Twelve Data: [개인 가격표](https://twelvedata.com/pricing), [trial 정책](https://support.twelvedata.com/en/articles/5335783-trial), [Tokyo 거래소](https://twelvedata.com/exchanges/xjpx), [KRX 거래소](https://twelvedata.com/exchanges/xkrx), [Tokyo 8035 참조](https://twelvedata.com/markets/433047/stock/jpx/8035), [KRX 042700 참조](https://twelvedata.com/markets/180577/stock/krx/042700), [개인 사용 조건](https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage), [약관](https://twelvedata.com/terms).

Alpha Vantage: [공식 무료 한도](https://www.alphavantage.co/support/), [quote·FX API 문서](https://www.alphavantage.co/documentation/), [통화 목록](https://www.alphavantage.co/physical_currency_list/), [개인 사용 약관 PDF](https://www.alphavantage.co/terms_of_service/).

Market Data: [Free Forever](https://www.marketdata.app/docs/account/plans/free-forever/), [주식 quote 비용과 지연](https://www.marketdata.app/docs/api/stocks/quotes/), [미국 주식 상품](https://www.marketdata.app/data/stocks/), [브라우저 CORS와 토큰 규칙](https://www.marketdata.app/docs/api/cors/), [개인 데이터 이용 조건](https://www.marketdata.app/docs/account/data-policies/data-redistribution/).

금융위원회: [공식 데이터셋과 이용허락](https://www.data.go.kr/data/15094808/openapi.do), [공식 V2 이용 가이드](https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000007632094&fileDetailSn=1), [개인 키와 승인 절차 안내](https://www.data.go.kr/ugs/selectPublicDataUseGuideMetView.do). 현재 주식 경로는 `https://apis.data.go.kr/1160100/GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2`입니다. 상세 출처와 원문 항목은 [금융위원회 검토](FSC_DIRECT_API_RESEARCH_26E.md)에 보존합니다.

## FX 방향과 무료 요청 예산

KRW 표시에는 **KRW/1 USD**와 **KRW/1 JPY**가 필요합니다. Twelve Data의 base/quote 기호에서는 `USD/KRW`와 `JPY/KRW`, Alpha Vantage에서는 `from_currency=USD|JPY`와 `to_currency=KRW`가 해당 방향의 후보입니다. 기호와 from/to 문서에 따른 해석이며 실제 숫자·가격시각·무료 계정 응답으로 검증한 환율이 아닙니다. 원/100 JPY 자료를 원/1 JPY와 혼동하지 않습니다. [Twelve Data FX 문서](https://twelvedata.com/docs), [USD/KRW 참조 메타데이터](https://api.twelvedata.com/forex_pairs?currency_base=USD&currency_quote=KRW), [JPY/KRW 참조 메타데이터](https://api.twelvedata.com/forex_pairs?currency_base=JPY&currency_quote=KRW), [Alpha Vantage FX 문서](https://www.alphavantage.co/documentation/).

Alpha Vantage에서 가정상 미국 17종목 EOD와 FX 2쌍을 한 번씩 요청하면 19요청이므로 하루 25요청 중 6요청만 남습니다. 이것은 17개 실제 응답 성공을 확인한 계산이 아닙니다. Twelve Data에서 종목/쌍당 1 credit인 엔드포인트를 사용하면 같은 19개 조회는 최소 3개의 분당 한도 구간에 걸칩니다. HTTP batch 한 번으로 credit 소모가 1이 된다고 가정하지 않습니다. Market Data의 미국 17종목 quote는 문서상 17 credits/회이며 무료 100 credits 안에서 반복 횟수가 제한됩니다. 공급자 에러·검색·재시도·이전 요청도 예산을 줄일 수 있습니다.

주가 EOD, 일본 15분 지연, FX 실시간 또는 일일 기준환율을 섞을 경우 **시세별 가격시각과 FX 기준일을 따로 표시**해야 합니다. 오래된 값을 새 조회 시각으로 덮어쓰지 않으며, 지원하지 않거나 필수 환율이 없는 값은 N/A로 남깁니다. ECB 일일 기준환율은 별도 무료 FX 후보로 기존 [공식 FX 검토](../pages_cockpit_owner/FX_RESEARCH_26E.md)에 정리돼 있지만 오늘 선택하거나 관측값을 수집하지 않았습니다.

## 개인 키의 브라우저 사용과 사용자 전용 릴레이

| 구조 | 키와 보유정보 위치 | 허용 범위와 장점 | 위험과 선택 조건 |
| --- | --- | --- | --- |
| **브라우저 직접 조회** | 공급자가 허용한 개인 API 키를 사용자 기기에서만 사용. 실제 보유값은 공급자에게 전송하지 않음. | 사용자 갱신 시 공개 카탈로그·FX만 공급자 HTTPS에 요청. 별도 서버 운영 없이 진행할 수 있음. | 페이지 스크립트·브라우저 확장·XSS·기기 접근자는 키를 읽을 수 있음. 사용자 입력 키와 앱 공용 비밀은 구분하되 **공용/기존 프런트 비밀을 재사용하거나 번들·Git·백업·로그에 넣지 않음**. 공급자의 개인 브라우저 사용 허용, 무료 display 권리, 실제 인증 CORS가 먼저 확인돼야 함. |
| **사용자 소유 Cloudflare Workers Free 릴레이** | 공급자 키/앱시크릿은 **사용자가 소유한 Worker의 encrypted secret binding에만** 저장. 사용자 보유값은 계속 기기 안에 유지. | 본인 인증 후 공개 TARGET19·FX 요청만 고정 공급자 엔드포인트로 전달. 서버에서 공급자 요청을 보내므로 공급자 브라우저 CORS 문제를 줄일 수 있음. KIS 앱시크릿을 페이지에 전달하지 않을 수 있음. | 서비스 키가 기기 밖 사용자 Worker에 저장되므로 원래의 기기 전용 키 저장 정책과 다른 선택이다. Cloudflare 및 계정·배포 코드에 대한 신뢰가 추가된다. 공급자 개인 이용약관·클라우드 호출 자격·데이터 제공 조건은 여전히 적용된다. 익명 공개 proxy나 가격 JSON으로 운영해서는 안 됨. |

Cloudflare 공식 문서상 Workers Free는 **계정 전체 100,000 요청/일, invocation당 CPU 10ms**, 요청당 subrequest 50회, 동시 외부 연결 6개입니다. 키는 평문 변수 대신 **Worker Secrets**에 저장하는 구성이 문서화돼 있습니다. 이는 플랫폼 무료 범위이며 공급자 API 한도를 늘려주지 않습니다. [Free 가격과 한도](https://developers.cloudflare.com/workers/platform/pricing/), [연결·subrequest 한도](https://developers.cloudflare.com/workers/platform/limits/), [encrypted secrets](https://developers.cloudflare.com/workers/configuration/secrets/).

본인만 쓰는 relay에는 CORS Origin 제한과 별개로 **실제 사용자 인증**이 필요합니다. Cloudflare Access는 `workers.dev`를 포함해 Worker 앞에서 승인된 사용자만 통과시키는 방식을 공식 지원합니다. 현재 공식 Free 계획은 50사용자 범위이며, Zero Trust 초기 설정은 Free를 선택해도 **결제정보 입력을 요구하지만 청구하지 않는다고 안내**합니다. 따라서 월 사용료 0원 범위의 대안이지, 계정/결제정보 없이 이미 사용할 수 있는 완성 서비스는 아닙니다. 새 도메인 구매가 꼭 필요한 구조로 가정하지 않습니다. [Worker Access](https://developers.cloudflare.com/workers/configuration/cloudflare-access/), [Zero Trust Free 가격표](https://www.cloudflare.com/plans/), [무료 계획 결제정보 조건](https://developers.cloudflare.com/learning-paths/cybersafe/account-creation/create-zero-trust-org/).

릴레이를 나중에 선택한다면 본인만 허용하는 Access 정책, 허용된 공개 ticker/FX 목록, 고정 외부 URL, 요청 한도, 키·토큰 로그 제외, 개인 데이터의 `no-store` 응답 정책을 검토해야 합니다. 클라이언트가 임의 URL·계좌 API·주문 API를 전달하는 범용 proxy는 선택안에 포함하지 않습니다. 인증을 위해 공급자 appsecret을 브라우저에 다시 보내거나 기존 프런트 비밀을 릴레이 암호로 재사용하지 않습니다. 키/시크릿을 보유한 Worker 코드가 유출·변조되면 공급자 계정 권한에 영향을 줄 수 있으므로 단순 암호화 보관만으로 운영 위험이 사라지지는 않습니다. **Worker·Access·Secrets를 설정하거나 배포하지 않았습니다.**

## 개인 이용 조건과 향후 계좌 연동

공개 JSON을 제거하면 공개 재배포 라이선스를 기본 요구로 삼을 필요는 줄어듭니다. 그래도 각 공급자의 **개인/비상업 사용자 자격, 개인 표시 권한, 키의 브라우저 사용 규칙**은 남습니다. 무료라는 이유만으로 공개 앱이나 공용 토큰을 허용한다고 해석하지 않습니다.

KIS 공식 개인 이용 안내는 본인의 투자·열람/분석을 위한 웹페이지를 허용하는 반면 시세 데이터로 비즈니스 서비스 제공·외부 앱 배포는 제한하며, 법인·외부 제공에는 관련 거래소/정보제공자 약정이 필요합니다. 기본 무료 FAQ의 당시 초당 10건 숫자는 2022년 게시 내용이므로 현재 호출 한도 증거로 쓰지 않습니다. [개인 웹페이지 FAQ](https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000002/post/01a0b635-3630-4aee-8970-42f83828118c), [서비스 소개](https://apiportal.koreainvestment.com/about-open-api), [시장 이용약관](https://apiportal.koreainvestment.com/api/terms/public?termsType=MARKET).

금융위원회 포털은 이번 조회에서 **공공누리 제4유형: 출처 표시·상업적 이용 금지·변경 금지**를 표시했고, 무단 제3자 제공·재배포 금지 안내도 확인했습니다. 무료 개인 조회와 공개 재배포를 혼동하지 않습니다. [현재 이용허락과 주의사항](https://www.data.go.kr/data/15094808/openapi.do).

KIS는 국내·해외 잔고 조회의 공식 엔드포인트/샘플도 있으므로 **향후 별도 범위에서 계좌 보유 연동을 검토할 기술적 후보**입니다. 이는 이번 시세 선택의 승인이 아니며 계좌번호·계좌 토큰·잔고를 요청하거나 연동하지 않았습니다. 미래에는 계좌 인증, 보유정보 저장 위치, 조회/주문 권한 분리, 장기 비밀과 토큰 보호를 따로 결정해야 합니다. [공식 국내 잔고 샘플](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/inquire_balance/inquire_balance.py), [공식 해외 잔고 샘플](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/inquire_balance/inquire_balance.py).

Finnhub도 선별 검토했습니다. 개인 사용·제3자 데이터/접근 공유 금지 약관과 무키 오류 CORS 헤더는 확인했지만, 공개 가격/문서 페이지의 동적 렌더링 때문에 현재 무료 범위·필요 두 KRW FX 쌍·브라우저 키 노출 허용을 충분히 공식 검증하지 못해 주 비교 5개에 넣지 않았습니다. 과거/제3자 출처의 60회/분 수치를 확정 조건으로 가져오지 않습니다. [Finnhub 약관](https://finnhub.io/terms-of-service), [공식 가격표](https://finnhub.io/pricing).

## 선택 판단과 26E 상태

**무료 단일 서비스 19/19 + FX 2쌍 추천은 보류**합니다. 세 시장을 한 공급자로 다루는 후속 검증 우선 후보는 KIS입니다. 공식 TSE 지원과 일본 무료 15분 지연이 확인됐기 때문이며, 정확한 19종목·FX·계좌별 자격과 사용자 전용 relay 조건을 확인하기 전에는 서비스 채택을 뜻하지 않습니다. 브라우저 직접 개인 사용을 가장 명시적으로 설명한 후보는 Market Data지만 미국·24시간 지연 범위이므로 이 앱 전체 시세/환율의 단일 후보는 아닙니다. Alpha Vantage는 미국 EOD·FX의 일부 조회 후보, 금융위원회는 국내 전일 이후 시세의 보완 후보입니다.

| 기록 항목 | 상태 |
| --- | --- |
| 서비스 결정 | **미정 / 26E WAIT**. 기존 수동 입력을 계속 사용할 수 있음. |
| B 외부 조회 | **OFF / disabled**. 조회 서비스 선택·외부 요청·버튼 활성화는 구현하지 않음. 별도 후보 PR의 기기 내 키 입력/삭제 구조는 조회 OFF 상태로 제공. |
| 갱신 모델 | 선택 이후에도 사용자 갱신 동작에 따른 공개 ticker/FX 요청만 검토. background polling·Cron·공개 JSON 없음. |
| 무료 범위 | 유료 API·실시간 상품 가입을 승인하거나 수행하지 않음. Free 한도를 넘는 계획을 확정하지 않음. |
| 개인 정보 | 실제 보유수량·평균단가·입력값·기기 백업은 공급자나 릴레이로 전송하지 않는 설계 조건. |
| 계좌 연동 | 향후 가능성 조사만 수행. 이번 범위에서 계좌 연결/인증/잔고 조회/주문은 없음. |
| 다음 확인 | 선택할 서비스의 정확한 19종목 대응·무료 entitlement·FX 코드/단위·개인 표시/브라우저 또는 private relay 허용을 공식 조건과 계정 검증으로 확인할 대상. 미선택이면 WAIT 유지. |

## 선택별 비용·소요·위험과 26E 요청

아래 소요는 계정 자격·개인 표시 약관·인증 CORS·종목/환율 대응이 확인된 뒤의 **개발 및 검증 작업량 추정**입니다. 공급자의 가입/본인 확인/문의 응답 대기는 포함하지 않으며 출시 날짜나 무료 이용권을 보장하지 않습니다. 미확인 조건이 유료 상품을 요구하면 이번 무료 범위에서는 중단합니다.

| 선택 | 비용 | 예상 작업량 | 남는 위험/조건 |
| --- | --- | --- | --- |
| 수동만 유지, API OFF | 별도 서비스 요금0원 | 추가 API 개발0일; 현재가19개·환율2개와 시각은 사용자가 입력 | 입력 누락/단위/오래된 시각을 직접 관리; 새 수동 기능 PR 병합은 별도 승인 |
| KIS + 본인 전용 무료 Worker | KIS 기본 API 및 Worker 무료 한도 내 플랫폼 월0원; 계좌 자격/Access 가입 조건은 사용자 확인 | 인증·서버 비밀·토큰/호출 한도·19종목/FX·휴대폰 검증까지3–5작업일 | 정확한19/19·FX·개인 웹/클라우드 호출 조건 미확인; appsecret은 서버 비밀 저장소에만; 기기 전용 키 정책의 명시적 변경 필요 |
| Twelve Data Basic | 무료8credits/분,800/일 이내0원 | 직접 호출이 허용되면2–3작업일 | 무료 display·Tokyo/KRX 접근권·성공 CORS 미확인; 충족 안 되면 수동 유지 |
| Alpha Vantage Free | 무료25요청/일 이내0원 | 미국 EOD/FX 직접 요청의 부분 지원1–2작업일 | 필요한 개별 심볼/FX·키 브라우저 허용·성공 CORS 미확인; 일본/한국 자동 지원 확정 불가 |
| Market Data Free Forever | 무료100credits/일 이내$0/월 | 미국 부분 지원1–2작업일 | 최소24시간 지연, Tokyo/KRX/FX 보완 필요; 공개 셸+개인 키 배포 조건 확인 |
| 금융위원회 V2 보완 | 무료 개발 트래픽10000표기 범위0원 | 국내1종목 직접 요청1–2작업일 | T+1갱신,042700/단위/성공 CORS 및 키 사용조건 확인; 출처표시·비상업·변경금지 준수 |
| CORS/비밀 때문에 별도 중계 추가 | Workers Free·사용자 전용 Access 무료 범위 월0원; Free 초기 결제정보 입력 조건 존재 | 직접 요청 후보에 인증/비밀/한도/키·토큰을 남기지 않는 로그 검증2–3작업일 추가; KIS 위 견적에는 포함 | 공개 Origin 제한만으로 보호 안 됨; 본인 인증 필수, 클라우드 신뢰·공급자 약관·무료 초과 중단 필요 |

26E 결정 항목은 **서비스와 호출 경로**입니다. 선택할 수 있는 묶음은 (1) 수동만 유지/API OFF, (2) KIS를 우선 확인하며 본인 전용 무료 중계 조건까지 검토, (3) Alpha Vantage 등 부분 지원 후보 + 미지원 종목 수동 입력입니다. 금융위원회 V2는 국내 보완 후보로 함께 선택할 수 있습니다. 무료19/19·FX가 미확인인 선택은 이를 먼저 확인하고, 미충족이면 대체 종목·값·유료 가입으로 우회하지 않습니다. 서비스가 정해지기 전에는 API OFF를 유지합니다. 계좌 보유 내역 연동은 어떤 선택에서도 이번 구현에 포함하지 않습니다.

## 출처와 HTTP 확인 범위

공식 문서와 참조 메타데이터를 2026-10-09 UTC에 GET했습니다. Twelve Data의 두 FX **참조 목록**만 HTTP 200으로 확인했으며 가격·환율 관측값은 요청하지 않았습니다. CORS 연구의 API 요청은 키·종목·시세 함수가 없는 오류 응답 또는 헤더 확인이었습니다.

| 무키 CORS 확인 | 관측 | 한계 |
| --- | --- | --- |
| Twelve Data `/price` · 키/종목 없음 | HTTP 401, `Access-Control-Allow-Origin: *` | 성공한 가격 응답·실제 인증 브라우저 호출 아님. |
| Alpha Vantage `/query` · 키/함수 없음 | HTTP 200 **오류 JSON**, Origin `*` | HTTP 200을 정상 시세 성공으로 해석하지 않음. |
| Market Data `/v1/stocks/quotes/` · token/종목 없음 | HTTP 401, Origin `*` | 공식 CORS 문서가 별도 근거; bearer preflight/인증 가격 흐름은 실행하지 않음. |
| Finnhub `/api/v1/quote` · 키/종목 없음 | HTTP 401, Origin `*` | 현재 무료 플랜·개별 종목·FX·브라우저 허용 검증 아님. |
| KIS 해외 price · 키/종목 없음 | 헤더 전용 GET HTTP 500, Origin `*`; OPTIONS HTTP 501 | 무키 오류의 헤더이며 인증 요청과 appsecret/Authorization preflight 동작은 미확인. |
| 금융위원회 V2 · 키/조회 조건 없음 | 헤더 전용 오류 GET HTTP 400에 Origin 허용; OPTIONS HTTP 200에 요청 Origin과 GET/OPTIONS 허용 | 인증 성공 GET·서비스 key 브라우저 노출 이용조건은 별도 확인 필요. |

`Access-Control-Allow-Origin` 헤더는 기술적 교차 출처 접근의 일부 증거이며 개인 표시 라이선스나 비밀 공개 허용을 뜻하지 않습니다. 실제 인증 브라우저 흐름·운영 안정성·19개 시세 성공을 검증했다고 주장하지 않습니다. 문서의 예시/사이트 배너 시세는 수집 가격으로 채택하지 않았습니다.

통합 [공식 출처와 HTTP 영수증](DIRECT_API_SOURCES_26E.json), [KIS 상세 검토](KIS_DIRECT_API_RESEARCH_26E.md), [KIS 영수증](KIS_DIRECT_API_SOURCES_26E.json), [금융위원회 상세 검토](FSC_DIRECT_API_RESEARCH_26E.md), [금융위원회 영수증](FSC_DIRECT_API_SOURCES_26E.json)에 URL·조회 시각·HTTP 상태·네트워크/범위를 남겼습니다. 상속 proxy와 TLS 검증을 유지했고 환경변수·자격증명 내용을 확인하지 않았습니다. 연구 에이전트는 애플리케이션/저장소를 수정하거나 commit하지 않았습니다. 이 문서와 출처 영수증은 통합자가 검토 후 후보 PR의 문서로 포함했습니다.
