# 26E Alpha Vantage Free 브라우저 직접 조회 검토

검토일: **2026-10-09 UTC**. 최신 사용자 선택은 **부분 API + 미지원 종목 수동 입력의 REVIEW ONLY**이다. 우선 검토 공급자는 Alpha Vantage이며 **API는 OFF**, 구현·외부 조회 활성화 승인은 아직 없다. KIS + Worker는 **DEFERRED**로 두며 기존 5개 공급자 제안의 우선순위를 이번 결정에 적용하지 않는다.

**판정: 미국 EOD + FX의 부분 지원은 공식 문서와 공개 demo CORS 수준에서 가능하다. 승인된 미국 17종목과 USD/KRW·JPY/KRW의 개인 무료 키 응답, 사용자 비상업 자격, 개인 키의 브라우저 직접 사용 조건은 UNCONFIRMED이다. 따라서 현재 결과로 완성된 서비스 채택·배포를 확정할 수 없다.** UNCONFIRMED는 검증 대기 상태이며 기술적 불가능 판정으로 사용하지 않는다.

사용자는 각자 발급한 무료 키를 자기 기기에서만 사용하고, 키는 백업에서 제외한다. 키 없는 수동 입력 경로를 유지한다. Tokyo Electron `TSE:8035`와 한미반도체 `KRX:042700`은 **MANUAL**이다. 서버·릴레이·KIS·유료 API·계좌 연동은 이번 선택 범위에 없다. 이 연구는 애플리케이션 또는 저장소를 수정하거나 commit하지 않았다.

## 항목별 가능/불가와 근거

| 항목 | 판정 | 확인한 근거와 남은 범위 |
| --- | --- | --- |
| 미국 주식 EOD 단일 quote 요청 | **문서상 가능** | `GLOBAL_QUOTE`는 1 ticker/요청이고 기본 quote는 거래일 종료 시 갱신한다. 정확한 US17 무료 성공 응답은 전부 UNCONFIRMED. [공식 quote 문서](https://www.alphavantage.co/documentation/#latestprice) |
| 미국 실시간 또는 15분 지연을 무료로 사용 | **이번 무료 범위에서 불가** | 공식 quote 문서·FAQ는 해당 미국 데이터를 premium 상품으로 구분한다. 기본 EOD를 실시간으로 표시할 수 없다. [FAQ](https://www.alphavantage.co/support/) |
| USD→KRW, JPY→KRW 요청 형식 | **문서상 구성 가능** | `CURRENCY_EXCHANGE_RATE`, `from_currency`, `to_currency`와 USD·JPY·KRW 공식 코드가 존재한다. 두 KRW 쌍의 무료 entitlement·실제 성공 응답은 UNCONFIRMED. [FX 문서](https://www.alphavantage.co/documentation/#currency-exchange), [통화 목록](https://www.alphavantage.co/physical_currency_list/) |
| 17 quote + 2 FX 전체 갱신 1회 | **예산상 가능, 성공 조건 미확인** | 17 + 2 = **19 ≤ 25 요청/일**, 잔여 **6**. 검색·재시도·다른 사용처 요청을 제외한 계산이며 19개 성공을 확인한 결과가 아니다. |
| 같은 하루에 전체 갱신 2회 | **무료 예산상 불가** | 19 × 2 = **38 > 25**. 잔여 6요청으로 두 번째 전체 갱신을 할 수 없다. |
| 별도 출처 브라우저 CORS | **공개 demo에서 가능 확인** | 모바일 화면을 모사한 Chromium의 실제 `fetch`로 IBM quote와 USD→JPY demo JSON을 읽었다. 두 성공 응답은 HTTP 200, `Access-Control-Allow-Origin: *`. 개인 무료 키·KRW 쌍·실제 휴대폰의 성공은 UNCONFIRMED. |
| 개인 비상업 대시보드 표시 | **약관상 조건부 가능** | 약관 §2(a)는 소유·통제하는 컴퓨터/모바일 기기에서 개인 비상업 access/display를 명시한다. 사용자에게 §2(a)의 상업 사용 판별 기준이 적용되지 않는지는 확인하지 않았다. [약관 PDF](https://www.alphavantage.co/terms_of_service/) |
| 다른 사람에게 시세를 표시·재배포하거나 공용 키 제공 | **이번 승인 범위에서 불가; 허용권 미확인** | private/individual 범위를 넘는 사용은 약관의 상업 사용 기준과 연결된다. 라이선스는 non-sublicensable/non-transferable이다. 무료 공개 재배포 허용을 확보하지 않았다. |
| 사용자 개인 키를 브라우저에서 직접 사용 | **UNCONFIRMED** | 검토한 공식 자료에서 이 모델을 별도로 명시 허용하거나 명시 금지하는 조항을 찾지 못했다. CORS 성공은 키 사용 약관 허용을 증명하지 않는다. 브라우저에서 키를 쓰면 해당 기기의 페이지 코드·개발자 도구에서 키를 볼 수 있다. |
| Tokyo Electron·한미반도체 자동 조회 | **이번 선택 범위에서 불가 → MANUAL** | 이 검토로 두 시장·정확한 종목의 무료 이용권을 확보하지 않았다. 미국 ADR/OTC, 다른 거래소, 다른 주식 클래스로 대체하지 않는다. |
| 현재 API 기능 구현·활성화 | **승인 범위상 불가 → OFF 유지** | 사용자가 승인한 이번 작업은 REVIEW ONLY이다. 이 문서는 구현 승인을 대신하지 않는다. |

## 공식 한도와 요청 예산

[Support FAQ](https://www.alphavantage.co/support/)는 **“25 API requests per day”**와 **“unlimited API requests for verified open-source or educational projects”**를 명시한다. 조회: **2026-10-09 04:08:20 UTC**, HTTP 200. 공개 소스 프로젝트라는 이유만으로 verified 예외를 적용하지 않는다. [Premium](https://www.alphavantage.co/premium/)도 기본 한도를 **“25 API requests per day”**로 설명한다. 조회: **2026-10-09 04:10:38 UTC**, HTTP 200.

[Quote 문서](https://www.alphavantage.co/documentation/#latestprice)의 정확한 짧은 문구는 **“You can specify one ticker per API request.”**, **“by default, the quote endpoint is updated at the end of each trading day for all users.”**이다. 미국 실시간·15분 지연을 원하면 **“please subscribe to a premium membership plan for your personal use”**라고 이어진다. 조회: **2026-10-09 04:11:00 UTC**, HTTP 200. 무료 EOD 계획에서 `entitlement=realtime` 또는 `entitlement=delayed`, 유료 bulk quote를 사용하지 않는다.

| 가정한 조회 | 요청 수 |
| --- | ---: |
| 승인된 미국 종목 17개 × `GLOBAL_QUOTE` 1회 | 17 |
| USD→KRW·JPY→KRW × `CURRENCY_EXCHANGE_RATE` 각 1회 | 2 |
| 전체 1회 | **19** |
| 문서상 하루 한도 25에서 남는 예산 | **6** |
| 전체 2회 | **38 — 한도 초과** |

가능한 계획은 **전체 갱신 하루 1회 수준**이다. 이미 다른 곳에서 같은 키를 사용했거나 검색·실패·재시도 호출이 있으면 남은 예산이 줄 수 있다. 확인한 공식 FAQ·관련 endpoint 문서에는 무료 한도의 **정확한 reset 시각·시간대, UTC 자정 reset, 오류 요청 차감 방식, 현재 무료 분당 제한**이 명시되지 않았다. 모두 UNCONFIRMED로 남긴다. 과거의 5회/분이나 다른 데이터셋의 UTC 갱신 설명을 현재 무료 quota reset 근거로 사용하지 않는다.

## 정확한 17종목과 환율의 증거 수준

다음은 승인된 공개 카탈로그를 그대로 사용한 요청 후보이다. 공식 문서는 `symbol` 형식과 검색 endpoint를 설명하지만 이 17개 전체의 무료 응답을 보증하지 않는다. 이번 연구에서는 17개 symbol search 또는 quote를 요청하지 않았고, 개인 무료 키도 요청·발급·사용하지 않았다. **유효한 사용자 무료 키를 통한 정확한 17개 수락/성공은 0개 검증, 17개 UNCONFIRMED**이다.

| 승인된 symbol | 승인된 대상 | 실제 무료 quote·심볼 대응 |
| --- | --- | --- |
| ASML | 미국 NASDAQ ASML · USD | UNCONFIRMED |
| LRCX | 미국 LRCX · USD | UNCONFIRMED |
| KLAC | 미국 KLAC · USD | UNCONFIRMED |
| NVDA | 미국 NVDA · USD | UNCONFIRMED |
| AMD | 미국 AMD · USD | UNCONFIRMED |
| AVGO | 미국 AVGO · USD | UNCONFIRMED |
| QCOM | 미국 QCOM · USD | UNCONFIRMED |
| INTC | 미국 INTC · USD | UNCONFIRMED |
| MSFT | 미국 MSFT · USD | UNCONFIRMED |
| GOOGL | 미국 Alphabet Class A · USD | UNCONFIRMED |
| AMZN | 미국 AMZN · USD | UNCONFIRMED |
| RTX | 미국 RTX · USD | UNCONFIRMED |
| SYK | 미국 SYK · USD | UNCONFIRMED |
| ETN | 미국 ETN · USD | UNCONFIRMED |
| HUBB | 미국 HUBB · USD | UNCONFIRMED |
| GEV | 미국 GEV · USD | UNCONFIRMED |
| ROK | 미국 ROK · USD | UNCONFIRMED |

ASML을 Amsterdam 종목으로, GOOGL을 GOOG로 바꾸지 않는다. IBM demo 성공은 위 17종목의 coverage 증거로 사용하지 않는다. [공식 SYMBOL_SEARCH 문서](https://www.alphavantage.co/documentation/#symbolsearch)는 후속 심볼 대응 검증 방법이며 이번에 해당 17개 메타데이터를 확보했다는 뜻은 아니다.

[FX 문서](https://www.alphavantage.co/documentation/#currency-exchange)는 **“This API returns the realtime exchange rate for a pair of fiat currencies”**라고 설명한다. 해당 제목은 Premium으로 표시되지 않고 무료 키 발급 링크와 USD→JPY 공개 demo를 제공한다. 이 사실과 일반 무료 제공 FAQ는 FX의 문서상 무료 후보 근거이며, 두 KRW 쌍의 실제 무료 entitlement 확인을 대신하지 않는다. 조회: **2026-10-09 04:11:00 UTC**, HTTP 200.

[공식 physical currency 목록](https://www.alphavantage.co/physical_currency_list/)에서 **“USD,United States Dollar”**, **“JPY,Japanese Yen”**, **“KRW,South Korean Won”**을 확인했다. 조회: **2026-10-09 04:08:20 UTC**, HTTP 200. 통화 코드 존재와 두 통화 조합의 정상 무료 응답은 서로 다른 검증이다.

| 필요한 환율 | 문서에 따른 요청 후보 | 무료 응답/단위/시각 판정 |
| --- | --- | --- |
| KRW/1 USD | `function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=KRW` | 구성 가능. 정확한 쌍의 무료 응답·통화 코드·필드·시각은 UNCONFIRMED. |
| KRW/1 JPY | `function=CURRENCY_EXCHANGE_RATE&from_currency=JPY&to_currency=KRW` | 구성 가능. 정확한 쌍의 무료 응답·통화 코드·필드·시각은 UNCONFIRMED. 원/100 JPY 자료로 대체하지 않는다. |

주식의 `latest trading day`와 FX의 `Last Refreshed`·`Time Zone`은 각각의 값 시점을 확인할 필드이다. 조회 시각으로 가격 시점을 덮어쓰지 않는다. 공개 IBM quote demo에는 통화 필드가 없었으므로 가격 숫자만으로 USD·거래소·주식 클래스 검증이 완료됐다고 처리할 수 없다.

## 별도 브라우저 CORS 확인

애플리케이션과 분리된 일회성 페이지 **`http://127.0.0.1:47861/alpha-cors-probe`**에서 Playwright + **Chromium 151.0.7922.173**으로 실제 브라우저 `fetch`를 실행했다. 페이지 응답만 로컬 route로 제공했고, 공급자 HTTPS 요청은 기존 정책의 `http://proxy:8080`을 사용했다. CSP `connect-src`는 Alpha Vantage만 허용했다. `mode: cors`, `credentials: omit`, `cache: no-store`, TLS 검증 활성화, `ignore_https_errors: false`를 유지했다. viewport 390×844, touch/mobile emulation, DPR 3 설정이며 실제 Android/iOS 휴대폰 검증은 아니다.

공식 문서가 게시한 **`apikey=demo`**만 사용했다. demo는 사용자 소유 키가 아니다. API GET은 총 **3회**였으며 US17·두 KRW 쌍의 시세 요청이나 19회 전체 조회는 수행하지 않았다.

| 별도 출처의 요청 | UTC 조회 시각 | HTTP / CORS / JSON | 판정 |
| --- | --- | --- | --- |
| 공개 demo `GLOBAL_QUOTE` · IBM | 04:09:18 | 200 / `*` / `Global Quote`, IBM 일치, 가격 필드·거래일 필드 존재, 통화 필드 없음 | **성공 schema를 브라우저에서 읽음** |
| 공개 demo `CURRENCY_EXCHANGE_RATE` · USD→JPY | 04:09:55 | 200 / `*` / `Realtime Currency Exchange Rate`, 요청 통화 코드 일치, 환율·갱신시각·시간대 필드 존재 | **성공 schema를 브라우저에서 읽음** |
| 키·함수 없는 `/query` | 04:09:55 | 200 / 응답 헤더 별도 캡처 없음 / `Error Message`, 정상 quote·FX 객체 없음 | **브라우저에서 읽은 오류 JSON** |

키 없는 HTTP 200 오류는 정상 시세 성공이나 인증 무료 키의 CORS/entitlement 증거가 아니다. 공식 문서도 **“Examples in this documentation are for demo purposes”**라고 명시한다. demo 성공으로 own-key 응답을 추정하지 않는다. CORS는 관측한 브라우저·Origin·demo 응답의 결과이며 모든 모바일 브라우저/Origin/인증 응답의 보장은 아니다. 숫자·실제 거래일·실제 FX 시각·원문 응답은 저장하거나 출력하지 않았다. 안전 영수증에는 status·필드 이름/존재·symbol/통화 일치 여부·응답 byte count·SHA-256만 남겼다.

## 개인 표시, 재배포, 키 조건

[공식 약관 PDF §2(a)](https://www.alphavantage.co/terms_of_service/)는 **“use, access, display and run”**, **“any computer or mobile device … that you own or control”**, **“for personal, non-commercial use”**를 명시한다. 단 약관 전체 준수 조건이다. 조회: **2026-10-09 04:10:38 UTC**, HTTP 200.

§2(a)(i)는 **“activities that are private and individual in nature”**를 개인 범위의 기준으로 설명한다. §2(a)(iii)는 상업 활동에서 다른 사람이 직접/간접 정보에 접근하게 하는 경우를 포함한다. §2(a)(iv)는 다음 자격도 상업 사용으로 구분한다: **“currently employed or have an active affiliation with a financial planning advisor, insurance company, investment advisor, investment bank, money manager … securities broker-dealer”** 등. 사용자의 적용 여부는 UNCONFIRMED이다. 개인적으로 쓰려는 의도만으로 이 약관상 자격을 확정하지 않는다. §3의 라이선스는 **“non-exclusive, non-sublicensable, non-transferable, non-assignable, revocable”**이다. 공개 시세 JSON·공용 키·타인에게 제공하는 대시보드의 무료 재배포 권한을 이번 연구에서 확보하지 않았다.

[공식 Premium 페이지](https://www.alphavantage.co/premium/)는 **“Please keep your API key at a safe physical or digital place”**와 침해 의심 시 통지 안내를 제공한다. 조회: **2026-10-09 04:10:38 UTC**, HTTP 200. 검토한 Terms·Support·Privacy·Documentation에는 공개 앱 셸에서 각자의 키를 입력하여 직접 브라우저 호출하는 모델을 별도로 명시 허용하는 문구를 찾지 못했다. NodeJS 예제와 demo CORS는 그 허용을 확정하지 않는다. 명시 금지 조항도 확보하지 못했으므로 **UNCONFIRMED / 공급자 확인 대상**으로 기록한다.

기기 내 개인 키는 해당 기기의 실행 중 페이지에서 읽을 수 있다. 이를 공용 키로 번들·Git·백업·로그에 넣는 허용으로 해석하지 않는다. 사용자 조건은 기기 전용 사용·백업 키 제외·키 없는 수동 경로이며 이번 연구에서 이 동작을 새로 구현하거나 활성화하지 않았다.

## 공식 무료 키 링크와 다음 결정

공식 발급 페이지는 **https://www.alphavantage.co/support/#api-key**이다. **“Claim your free key … with lifetime access”**, **“Get Free API Key”**를 표시하며 occupation 선택과 organization/email 입력을 제공하고 legitimate email을 권장한다. 키 취득·사용 시 Terms 및 Privacy Policy에 동의한다고 안내한다. 조회: **2026-10-09 04:10:38 UTC**, HTTP 200. 검토용 UI 안내는 “공식 페이지에서 본인 무료 키 발급 → 본인 기기에 입력; 키는 백업에서 제외”로 표현할 수 있다. 이 연구에서 신청 양식을 제출하거나 계정을 만들지 않았다.

후속 결정에는 정확한 US17·두 KRW 쌍의 무료 entitlement/응답, 해당 사용자의 비상업 자격, 개인 키 브라우저 모델의 제공자 조건을 구분해 남긴다. 무료 조건을 충족하지 않는 대상은 기존 MANUAL/N/A 경로를 유지하며 유료·릴레이·다른 종목으로 우회하는 승인을 이번 선택에서 부여하지 않는다. 현재 상태는 **PARTIAL_API_MANUAL_REVIEW_ONLY / Alpha Vantage 우선 검토 / API_OFF / IMPLEMENTATION_NOT_APPROVED / KIS_WORKER_DEFERRED**이다.

공식 URL·UTC·HTTP 상태·fingerprint와 값이 없는 CORS 결과는 [안전 영수증](ALPHA_VANTAGE_FEASIBILITY_26E.json)에 보존한다. 실제 사용자 키·가격·환율·계좌정보·실제 보유값을 수집하지 않았고, proxy/TLS 정책·환경변수·자격증명·애플리케이션·GitHub를 변경하지 않았다.
