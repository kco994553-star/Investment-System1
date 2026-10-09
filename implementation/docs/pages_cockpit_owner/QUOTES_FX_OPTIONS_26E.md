# 19종목 시세와 환율 선택안

**26E 결정 = ① 시세·환율 수동 입력 + KRW 기준 표시 (사용자 선택, 2026-10-09).**
시세·환율 lane은 **수동 입력 범위만 READY**이며, 자동 수집·공개 JSON(②)·실시간 API(③)는 채택하지 않았습니다.
이번 PR은 문서 전용이며 구현하지 않습니다. 결정 영수증·SSoT §8/§26D 영향은
[26E 결정 기록](DEPLOYMENT_DECISION_26E.md)에, 미채택 기기 직접 API 후보는
[별도 조사](DEVICE_DIRECT_QUOTES_RESEARCH.md)에 기록합니다.

아래는 2026-10-09 UTC의 선택 전 비교 자료를 보존한 것입니다. 수동 입력은 19종목을 모두 다루면서 외부 서비스 비용을 0원으로 유지할 수 있습니다. 자동화는 미국뿐 아니라 도쿄 8035와 한국 042700의 가격 제공 및 공개 재배포 권리까지 확인해야 합니다. 시세 수집·API 연동·키 발급·유료 가입은 이번 결정 및 PR의 범위 밖입니다.

## 선택 전 비교 1 (현재 선택: ①)

**19종목의 시세와 환율을 ① 앱 수동 입력, ② 일일 종가·환율 공개 JSON, ③ 실시간 API 중 어떤 방식으로 확보할까요?**

| 선택 | 비용과 이용조건 | 19종목과 USD·JPY·KRW | 갱신 지연과 위험 | 상대 작업량과 되돌리기 |
| --- | --- | --- | --- | --- |
| **① 앱 수동 입력 — 추천** | **외부 서비스 0원.** 사용자가 이용 권한이 있는 증권사·거래소 등의 화면에서 확인한 가격과 환율을 개인 기기에 입력. 입력값을 서버나 공개 JSON으로 내보내지 않음. | **19/19 입력 가능.** 미국 17종목 USD, Tokyo Electron TSE 8035 JPY, 한미반도체 KRX 042700 KRW. 기준통화가 KRW이면 `KRW/1 USD`, `KRW/1 JPY` 두 환율; USD이면 `USD/1 KRW`, `USD/1 JPY` 두 환율을 입력. | 사용자가 갱신한 시각만큼 오래될 수 있음. 종목별 가격 시각·환율 기준일이 필요. 필수 값이 없으면 관련 금액·비중은 N/A, 임의 0원 대체 금지. | 가장 짧음. 외부 계정·계약이 없어 설정과 개인 기기 입력값을 통해 되돌리기 쉬움. |
| **② GitHub Actions 일일 종가·환율 → 공개 JSON** | 공개 저장소의 **표준 GitHub 호스팅 실행 시간은 무료**이지만 **주가 API 및 공개 JSON 재배포의 총비용은 미확정**. 공급자의 API 이용권과 별도로 공개 원시가격 파일, Git 이력·보관·캐시까지 허용되는 재배포 권리가 필요. ECB 공식 기준환율은 조건부 무료 재사용 후보. | **자동 19/19는 미확인.** Twelve Data는 미국시장과 KRX EOD 지원이 공개돼 있지만 Tokyo 가격 엔드포인트를 확인하지 못함. EODHD는 US·KRX 목록은 있으나 Tokyo를 확인하지 못함. FX는 ECB EUR 기준 USD·JPY·KRW의 같은 기준일 자료로 교차환율 산출 가능하되 파생 기준환율임을 표시. | 각 시장의 최근 완료 거래일 종가와 FX 기준일이 서로 다를 수 있음. 휴장일·시차·누락·정정 및 작업 지연이 있음. 일일 갱신은 실시간 가격이 아님. | 중간, 공급자·권리 확인 전 일정 미정. 이후 승인된 경우 작업 중지와 수동 입력 복귀가 가능하나 이미 공개된 파일·Git 이력·캐시는 완전 회수가 어려움. |
| **③ 실시간 API** | **유료 가능, 전체 총액 미확정.** 예시 후보 Twelve Data 사업용 Venture 표시는 `From US$149/mo`, Enterprise는 `From US$1,099/mo`; 이것은 세 시장의 실시간 가격·재배포 권리를 포함한 견적이 아님. 거래소별 실시간·지연·표시·재배포 계약이 따로 필요할 수 있음. | **19/19 실시간 지원은 미확인.** 현재 후보 자료에서 KRX는 EOD, Tokyo는 가격 엔드포인트 미확인. 미국만 실시간이라고 전체를 실시간으로 표시할 수 없음. 실시간 FX도 별도 제공 범위·계약 확인 필요; ECB·ECOS 일일 FX를 쓰면 혼합 지연을 명시. | 시장별 지연 차이, 부분 체결시장 피드, 요청 한도·장애·비용 증가. API 이름이 `/price` 또는 `/quote`여도 거래소별 지연 정책 우선. | 가장 큼, 계약·접근권·키 보호·운영 확인 전 일정 미정. 호출 중지·키 철회·수동 입력 복귀 가능하나 이미 발생한 사용료 및 계약 의무는 별도. |

②의 실행 시간 무료 조건은 [GitHub 공식 과금 안내](https://docs.github.com/en/billing/concepts/product-billing/github-actions)에 따른 것입니다. 공식 일정 안내에는 부하에 따른 실행 지연·작업 누락 가능성과 공개 저장소의 60일 비활동 시 예약 작업 비활성화가 있습니다. 이를 확정 시각에 도착하는 가격 서비스로 가정할 수 없습니다. [GitHub 일정 안내](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## 19종목 적용 범위

공개 식별 기준은 검토 대상 저장소 커밋 `17b8f82bd09bce4cd0655e9f0795f3670bd805d8`의 [CURRENT_TARGET_IDENTITY_MAP.json](https://github.com/kco994553-star/Investment-System1/blob/17b8f82bd09bce4cd0655e9f0795f3670bd805d8/implementation/docs/security_map19_owner/v1_1_cycle_20261008/CURRENT_TARGET_IDENTITY_MAP.json)입니다. 아래 목록은 공개 TARGET 카탈로그이며 실제 보유목록을 뜻하지 않습니다. Alphabet은 Class A `GOOGL`, ASML은 승인된 NASDAQ 종목, 일본은 TSE `8035`, 한국은 KRX `042700`을 유지합니다. `8035`를 미국 OTC 종목으로 대체하지 않습니다.

| 시장과 통화 | 대상 종목 | 수동 입력 | 자동 가격 확인 상태 |
| --- | --- | --- | --- |
| 미국 17종목 · USD | ASML Holding `ASML`, Lam Research `LRCX`, KLA `KLAC`, NVIDIA `NVDA`, AMD `AMD`, Broadcom `AVGO`, Qualcomm `QCOM`, Intel `INTC`, Microsoft `MSFT`, Alphabet Class A `GOOGL`, Amazon `AMZN`, RTX `RTX`, Stryker `SYK`, Eaton `ETN`, Hubbell `HUBB`, GE Vernova `GEV`, Rockwell Automation `ROK` | 17/17 가능 | 미국시장 제공은 공식 자료에 존재. 17개 개별 종목의 선택 요금제 접근권, 정확한 주식 종류·시장·가격 필드·공개 재배포는 아직 검증하지 않음. |
| 일본 · JPY | Tokyo Electron `TSE:8035` | 1/1 가능 | Twelve Data 카탈로그 종목 존재는 확인. Tokyo 거래소 페이지는 지연을 `–`로 표시하고 Core 가격 엔드포인트를 열거하지 않으므로 EOD·실시간 가격 제공은 미확인. |
| 한국 · KRW | 한미반도체 `KRX:042700` | 1/1 가능 | Twelve Data 카탈로그 종목 및 거래소 EOD 제공은 확인. 해당 종목의 계정·요금제에서의 가격 응답과 공개 재배포 권리는 미확인. |

## 가격 공급자와 재배포 조건

- **Twelve Data:** Tokyo `8035`와 한미 `042700`의 공식 카탈로그 페이지가 있어 종목 검색 후보로 사용할 수 있습니다. 다만 카탈로그 존재는 가격 API 제공·구독 접근권을 보증하지 않습니다. 일본 거래소 페이지에는 Reference/Fundamentals/Analysis 등이 있고 Core data는 없으며, 한국은 EOD 및 Core data가 표시됩니다. [Tokyo 종목](https://twelvedata.com/markets/433047/stock/jpx/8035), [한미 종목](https://twelvedata.com/markets/180577/stock/krx/042700), [Tokyo 거래소](https://twelvedata.com/exchanges/xjpx), [한국 거래소](https://twelvedata.com/exchanges/xkrx)
- **Twelve Data 비용·권리:** 공식 사업용 가격표의 최저 표시 가격과 특정 선택 구성의 가격은 다릅니다. 과금 주기·크레딧 구성에 따라 달라지며 실제 세 시장 견적은 미정입니다. 2026-08-04 이용 안내는 개인 플랜을 개인·내부용으로 한정하고, 비미국 가격의 상업 이용에 추가 승인이 필요하며 **모든 재배포는 별도 계약**이 필요하다고 명시합니다. 무료 Basic·개인 유료 플랜을 공개 JSON 권리로 해석하지 않습니다. [사업용 가격표](https://twelvedata.com/pricing-business), [공식 이용 안내](https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage)
- **미국 실시간의 범위:** Twelve Data 기본 미국 피드는 공식 안내상 전체 미국 거래량의 약 5%에 해당하는 시장 활동을 포착합니다. 전체 거래소 통합 피드와 동일한 가격·체결 범위를 보증하지 않습니다. 외부 재배포 권한은 별도 Add-On 대상입니다. [미국 피드와 재배포 안내](https://support.twelvedata.com/en/articles/9935903-us-equities-market-data)
- **EODHD:** 공식 거래소 목록에서 US 및 `KO / XKRX`는 확인되지만 검토한 공개 목록에서 Tokyo·Japan·XJPX를 확인하지 못했습니다. 따라서 19종목 단일 공급자로 확정하지 않습니다. 개인 플랜의 낮은 가격을 공개 서비스 비용으로 가져오지 않으며 사업용 라이선스·가격·Tokyo 지원은 미정입니다. [공식 거래소 목록](https://eodhd.com/list-of-stock-markets), [사업용 안내](https://eodhd.com/lp/b2b-solution)
- **KRX Open API:** 현행 공개 약관 제11조②는 제공받은 정보를 제3자에게 제공할 수 없다고 명시합니다. 키당 하루 10,000회 제한도 있습니다. 비영리·무료 앱이어도 이 API의 데이터를 그대로 공개 JSON에 게시하는 근거가 되지 않습니다. 별도 정보 이용·분배 권리 확인이 필요합니다. [KRX 약관](https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO002.jsp), [KRX 정보 수신·계약 안내](https://openapi.krx.co.kr/contents/OPP/DATA/OPPDATA003.jsp)
- **JPX:** 공식 월별 예시에서 공급자로부터 종가를 받아 제3자에게 재배포하는 경우 `JPY 280,000/month`가 제시됩니다. **적용 방식에 따라 달라지는 예시일 뿐 이 앱의 견적이나 최소요금은 아닙니다.** 종가도 무료 재배포라고 가정하면 안 된다는 근거입니다. [JPX 정보 이용요금](https://www.jpx.co.jp/english/markets/paid-info-equities/realtime/01.html)

Yahoo의 비공식 무료 호출, Stooq 스크래핑 또는 출처 불명 공개 JSON은 ②의 승인된 공급자로 채택하지 않습니다. 가격이 공개 화면에 보이는 것과 원시가격을 다시 공개 파일로 배포할 권리는 별개의 확인사항입니다.

## 환율 후보와 기준일

- **ECB 일일 기준환율:** 공식 EUR 기준 목록에는 USD·JPY·KRW가 포함됩니다. 보통 TARGET 휴무일을 제외한 근무일 16:00 CET 전후에 갱신하며 정보 제공용 기준환율입니다. 주말과 TARGET 휴무일에는 새 일일 값이 없을 수 있습니다. 실제 체결·거래에 사용하는 환율과 다릅니다. `KRW/1 USD = (KRW/1 EUR) ÷ (USD/1 EUR)`, `KRW/1 JPY = (KRW/1 EUR) ÷ (JPY/1 EUR)`로 환산할 수 있습니다. 이것은 선택안 설명용 기존 환산 관계이며 이번에 계산 코드나 새 계산 규칙을 추가하지 않습니다. [공식 환율 안내](https://www.ecb.europa.eu/stats/exchange_rates/html/index.en.html), [기준환율 체계](https://www.ecb.europa.eu/stats/pdf/exchange/Frameworkfortheeuroforeignexchangereferencerates.en.pdf)
- **ECB 재사용·접근:** ESCB 공개 통계는 출처 표시 등 조건을 지키면 상업·비상업 재사용이 무료입니다. 원자료와 메타데이터를 정확히 보존하고, EUR 자료에서 계산한 교차환율에는 **파생 환율임을 표시**해야 합니다. 제3자 자료는 이 정책에서 제외됩니다. ECB EXR 데이터의 USD·JPY·KRW **메타데이터만** 요청한 연구용 확인에서는 인증키 없이 HTTP 200과 `Access-Control-Allow-Origin: *`를 관측했습니다. 실제 환율 관측값 수집, 앱 CORS·운영 한도·완전한 갱신 흐름은 검증하지 않았습니다. [통계 재사용 정책](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html), [사이트 이용조건](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html), [API 문서](https://data.ecb.europa.eu/help/api/data)
- **한국은행 ECOS 대안:** 공식 개발 문서·통계코드 자료에서 일일 표 `731Y001`, USD 항목 `0000001`은 **원/1 USD**, JPY 항목 `0000002`는 **원/100 JPY**입니다. JPY 원자료를 원/1 JPY로 쓸 때 100으로 나눠야 합니다. 발급 키가 필요하며 약관상 상업 이용은 제한 통계의 원기관 조건을 제외하고 허용되고 ECOS 출처 표시가 필요합니다. 키 유효기간·갱신은 공식 약관 기준 2년입니다. 환율 관측값 호출이나 운영 검증은 하지 않았습니다. [ECOS 개발 안내·약관](https://ecos.bok.or.kr/api/), [통계코드 검색](https://ecos.bok.or.kr/api/#/DevGuide/StatisticalCodeSearch), [키 안내](https://ecos.bok.or.kr/api/#/AuthKeyApply)

미국·일본·한국의 휴장일과 ECB·ECOS의 통계 기준일을 하나의 날짜로 덮어쓰지 않습니다. 마지막 정상값을 표시하는 경우에도 실제 기준일을 유지하며 새 값인 것처럼 표시하지 않습니다. 필요한 가격·환율이 없으면 관련 금액·비중은 N/A입니다.

## 선택 전 비교 2 (현재 선택: KRW)

**합산 금액과 비중의 표시 기준통화를 KRW와 USD 중 어느 것으로 할까요?**

| 선택 | 영향과 장점 | 되돌리기 |
| --- | --- | --- |
| **KRW — 국내 자산·생활비 기준을 우선하면 추천** | 원화로 전체 자산을 이해하기 쉽고 한미반도체 원화 가격을 바로 비교할 수 있음. 미국 17종목·일본 1종목에는 KRW 환산이 필요해 환율 영향이 함께 보임. | 원통화 가격·수량·평균단가를 보존한 채 표시 기준을 USD로 다시 선택할 수 있음. |
| **USD — 미국 종목 비교를 우선하면 선택** | 미국 17종목 평가를 USD로 직접 비교하기 쉬움. 일본·한국 종목은 USD 환산이 필요하고 원화 생활 자산과 비교할 때 환율 영향을 따로 이해해야 함. | 원통화 가격·수량·평균단가를 보존한 채 표시 기준을 KRW로 다시 선택할 수 있음. |

기준통화 선택은 실제 보유값 업로드, 거래통화 변경 또는 수익률·목표비중 계산의 새 규칙 승인을 뜻하지 않습니다. 본 검토의 실제 보유수량·매수단가·입력값은 휴대전화 안에만 남아야 합니다.

## 개인정보와 구현 대기

가격 조회에 필요한 공개 종목 식별자·통화·시장·기준시각 외에 실제 보유수량, 매수단가 또는 기기 입력값을 공급자·GitHub·공개 JSON으로 보내지 않습니다. 이후 자동화 설계에서는 선택된 보유종목만 요청하는 대신 공개 카탈로그 19종목을 동일하게 조회하는 방식을 검토할 수 있습니다. 이것은 오늘 구현한 기능이 아닙니다.

Twelve Data 등 공급자 키는 인증정보입니다. 향후 ②가 승인되면 GitHub Secrets 등 비공개 실행 위치에서만 사용하고, ③은 비공개 서버 또는 공급자가 명시적으로 허용한 공개 접근 방식이 필요합니다. 정적 앱 JS에 비밀 키를 넣거나 공개 JSON에 키를 포함할 수 없습니다. 공급자의 CORS 허용만으로 키 비밀성과 재배포 권리가 해결되지 않습니다. [Twelve Data 인증 문서](https://twelvedata.com/docs)

| 26E 기록 항목 | 상태 |
| --- | --- |
| 사용자 결정 | ① 시세·환율 수동 입력 + KRW 기준 표시 (2026-10-09). ②/③ 미채택. |
| 선택 기록처 | [26E 결정 영수증](DEPLOYMENT_DECISION_26E.md)의 SSoT §8·§26D 범위 영향, [Cockpit IA v1](../frontend_ia_v1/COCKPIT_IA_v1.md). Global 정책 자체는 무변경. |
| 시세·환율 구현 lane | **수동 입력 범위만 READY**. 문서 갱신이지 구현 완료가 아님. 자동 수집·공개 JSON·실시간 API·기기 직접 API는 미채택. |
| 별도 배포 lane | 기존 사용자 승인과 실제 배포 증거는 별도 판단. 이 문서 전용 PR은 배포·재배포하지 않음. |
| 후속 선택 | 기기 직접 API는 공식 문서 조사만. 사용자 선택 전 도입·키 발급·가입·호출 코드 추가 없음. |

## 출처 확인일과 연구 한계

위 공식 출처를 **2026-10-09 UTC**에 조회했습니다. 가격표는 당시 공개 안내이며 특정 계정·실행 구성·세 시장 이용조건의 견적이 아닙니다. 출처와 HTTP 상태·조회시각을 기록한 [문서 GET 영수증](evidence/QUOTES_SOURCE_FETCH_RECEIPT.json) 및 [공식 FX 검토](FX_RESEARCH_26E.md)가 있습니다. 직접 조회한 가격 API 관측값이나 실제 보유정보는 없습니다. 모든 자동 19종목 커버리지·제공자 계약·운영 CORS·원시가격 공개 파일 재배포는 공급자와 권리 확인이 끝날 때까지 미확인 상태입니다.
