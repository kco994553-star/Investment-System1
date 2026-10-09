# 일일 가격 데이터 권리 선택안

검토일: **2026-10-09 UTC**. 공식 설명·약관·가격표만 확인했다. 키 발급,
가입, 공급자 연락, 가격 API 호출, 실제 일봉 수집은 하지 않았다. 가격표의
구독료는 API 접근 비용의 비교값이며 공개 재배포 총비용이나 견적이 아니다.

**추천은 ② ‘정적 공개파일 재배포까지 명시한 EOD 라이선스’의 조건부 검토다.**
최신 미국 상위 500 구성·가격 의존 QGV와 19종목 차트를 함께 충족하려면
가격 접근권 외에 공개 산출물 권리가 필요하다. 이번 조사에서 세 시장의
원시 일봉을 공개 Git/Pages JSON으로 배포할 권리가 확정된 단일 상품은
확인하지 못했다. 공급자 선정·예산·채택은 사용자 결정으로 남긴다.

## 유지되는 결정과 필요한 구분

[26E 선택안](../pages_cockpit_owner/QUOTES_FX_OPTIONS_26E.md)과
[GSQ-001](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md)을
유지한다. Alpha Vantage는 OFF, 한국투자증권·중계 서버는 DEFERRED다.
구글 시트 현재 시세는 사용자 기기가 직접 읽고 수동 입력을 유지한다.
서버·중계·GitHub Actions 시세 수집 및 공개 원시 시세 저장 금지는 계속
적용된다. 아래 추천은 이 금지를 해제하거나 새 공급자를 채택하는 결정이
아니다. 사용자 결정 후 26E에 append-only로 변경 범위를 기록하고,
수집·저장·공개 각각에 대한 별도 구현 승인을 받아야 한다.

- **D1**은 승인된 미국 상위 500 구성 기준을 그대로 적용한다. S&P 500
  지수 구성으로 대체하지 않는다. 현재 후보 전체에서 같은 시점의 가격과
  해당 시점에 이용 가능했던 주식 수·주식 종류를 비교해야 한다. 기존
  500개만 조회하면 새 진입 종목을 찾을 수 없다. 순위·시가총액·구성 목록
  공개 권리도 계약 대상이다. 주식 수가 공개 SEC 사실이라고 가격이나
  공급자의 시가총액 공개 권리가 자동 생기지 않는다.
- **D4**는 공개 TARGET의 미국 17종목, `KRX:042700`, Tokyo Electron
  `TSE:8035`의 과거 일봉이다. 이는 보유 목록이 아니다. 일본 종목을 미국
  OTC 대체 종목으로 바꾸지 않는다. 전체 종목의 정확한 시장·통화·주식
  종류와 원시/수정 OHLCV·분할/배당 제공 범위가 필요하다.
- **공개 화면 표시**, **익명 다운로드 가능한 JSON**, **공개 Git 이력·캐시**는
  서로 다른 사용 방식이다. 웹 표시 라이선스를 나머지 방식의 허가로
  해석하지 않는다. 비영리·무료 사이트라는 이유만으로 재배포가 허용되지
  않는다. 익명 공개 파일은 회수·구독 종료 후 삭제를 보장하기 어렵다.

## 네 가지 선택지

| 선택 | 비용·범위 | D1 최신 500 / D4 19종목 | 공개 권리와 판정 |
| --- | --- | --- | --- |
| **① 사용자 무료 키 → 기기 직접 조회** | Alpha Vantage 무료 기본 한도 25요청/일. 무료 DAILY는 최근 100관측의 `compact`; 전체 이력·수정 일봉은 유료 제한. | 19종목이 모두 지원된다는 가정에서 일봉 최소 19요청으로 하루 한도 안에 들어간다. 다만 미국 17개별 종목 접근권, 한국·일본 종목 지원은 미확인. 최신 전체 미국 후보 조회·공개 500 구성을 해결하지 못한다. | 개인·비상업 사용 및 사용자 자격 조건. 가격은 기기 안에만. 공개 재배포 불가로 취급. 현재 OFF 유지; 부분 기기 차트 후보. |
| **② 재배포 허용 EOD 계약 — 조건부 추천** | EODHD 개인 EOD $19.99/월은 비교값일 뿐. 사업용·거래소·외부 배포·보관 권리는 별도 견적. 여러 공급자가 필요할 수 있다. | 미국 전체 후보+D4 정확한 19종목·필요 이력·기업행위 자료를 계약에 명시해야 한다. 단일 후보의 세 시장 전부 제공은 미확인. | 원시 JSON·공개 Git 이력·캐시·재사용·계약 종료 보관까지 명시 허용하는 계약이 있을 때만 후보. 현행 GSQ 경계와 사용자 결정 전에는 실행 불가. |
| **③ 원시 비공개, 파생값만 공개** | 수익률·순위로 바꿔도 원자료 접근·처리·보관권은 필요. 무료 플랜이 영구 보관을 허용한다고 가정하지 않는다. | 권리가 확인된 구성 목록·기존 QGV/순위 공개에는 조건부 적용 가능. D4 원시 일봉을 내려받는 앱 차트는 해결하지 못한다. | 공급자별 약관 확인 필수. 원가격을 복원하는 수익률 경로·시가총액·가격비율은 단순히 ‘파생값’이라 허용되지 않는다. 아래 비교 기준을 충족하지 못하면 공개 차단. |
| **④ 공식 보완 출처 조합** | JPX J-Quants(개인/Pro), KRX Open API, 기존 GOOGLEFINANCE, Tiingo 등. 각 접근·지연·보관·기기 직접 접근 조건은 별도. | 일본·한국 또는 미국 일부를 보완할 수 있으나 무료·현재·19/19·공개 JSON을 동시에 충족하는 조합은 확인되지 않았다. | 국가별 직접 출처도 공개 파일 권리를 자동 주지 않는다. 승인 전에는 조사 후보이며 운영 출처로 채택하지 않는다. |

### ① Alpha Vantage: 한도와 19종목의 차이

무료 **25요청/일**은 공식 지원 안내의 기본 한도다. 검증된 오픈소스·교육
프로젝트 예외도 안내돼 있으나 이 저장소가 승인됐다는 근거는 없다.
19요청에 검색·재시도·분할/배당·환율 요청을 더하면 한도가 달라진다.
다중 quote 요청을 일봉 배치 요청으로 간주하지 않는다.
[공식 지원](https://www.alphavantage.co/support/)

`TIME_SERIES_DAILY` 무료 `compact`는 최근 **100개 관측**이며 1년 이력과
동일하지 않다. `outputsize=full`은 premium이고 `TIME_SERIES_DAILY_ADJUSTED`
도 premium이다. 공식 문서의 해외시장 예시는 Tokyo `8035`나 KRX `042700`
지원 증거가 아니다. 정확한 provider 식별자는 미확인으로 남기며 `.T` 등의
접미사를 추측하지 않는다. 브라우저 CORS와 이 앱의 직접 호출 허용도
미확인이다. CSP 확장·호출 실험을 이번 문서 PR에 추가하지 않는다.
[공식 일봉 문서](https://www.alphavantage.co/documentation/#daily)

라이선스 §2는 소유·통제 기기의 개인·비상업 사용을 규정하고 사용자 자격과
제3자 제공을 제한한다. 개인 키는 공개 JS·백업·Actions에 넣지 않는다.
개인 무료 키만으로 공개 가격·공개 파생값 사용을 승인하지 않는다.
[공식 약관](https://www.alphavantage.co/terms_of_service/)

### ② 비용과 실제 재배포 조건

| 공식 후보·제공 범위 | 조회한 비용 표시 | 이 앱에서 필요한 추가 확인 |
| --- | --- | --- |
| EODHD EOD / 사업용 계약 | 개인 EOD **$19.99/월**, **$199/년**. 사업용 별도 견적. | 공식 거래소 목록에 US·KO/XKRX가 있으나 Tokyo는 확인되지 않음. 정확한 17+042700 제공·정적 공개파일·파생 공개·보관 권리는 미확인. 개인 구독 약관은 원형 또는 재포장 자료의 공개·재배포를 금지. |
| Twelve Data 사업용 + Redistribution Rights Add-On/별도 계약 | 세 시장·공개파일 총비용 **미확정**. | KRX 페이지에 EOD·`/time_series`가 명시됨. Tokyo 페이지에는 Core 가격 API가 없어 카탈로그 존재만으로 8035 일봉을 확정할 수 없음. 비미국 가격 사업용 추가 승인과 모든 재배포의 별도 계약 필요. |
| JPX J-Quants Pro 조정 OHLC | 내부 단일기업 사용 **¥150,000/월(세전)**. 외부 배포요금 별도 문의. | 가격표에 해당 OHLC의 공개웹 배포 가능(YES)이 있으나 부속서 4 §2(3)(ii)(a)는 **파일 다운로드 기능을 금지**. 공개 Pages 원시 JSON·Git 이력은 이 표시 권한으로 승인할 수 없음. 파일 배포를 허용하는 별도 계약 가능 여부도 미확인. |

EODHD의 공개 설명은 일부 가격이 거래소 통합 원시 피드가 아닌 자체 집계
출처임을 밝힌다. 공식 거래소 종가와 같다고 가정하지 않고 산출 기준·오류
정정·기업행위 처리를 계약에서 확인한다.
[가격표](https://eodhd.com/pricing/),
[사업용 안내](https://eodhd.com/financial-apis/commercial-vs-personal-license-use),
[약관](https://eodhd.com/financial-apis/terms-conditions),
[거래소 목록](https://eodhd.com/list-of-stock-markets)

Twelve Data 개인 플랜은 개인·내부 사용이며 재배포를 허용하지 않는다.
사업용 표시 권한과 원시 파일 배포 권한도 구분한다.
[공식 이용 안내(2026-08-04)](https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage),
[약관 §2.2·§2.3](https://twelvedata.com/terms),
[KRX 제공 범위](https://twelvedata.com/exchanges/xkrx),
[Tokyo 제공 범위](https://twelvedata.com/exchanges/xjpx)

일본 가격의 외부 표시 라이선스는 실제 공식 선택지지만 현재 정적 파일
아키텍처에 그대로 적용할 수 없다. 인증 서버를 추가해 해결한 것으로
설계하지 않는다.
[JPX Pro 가격·이용표](https://pro.jpx-jquants.com/pdfs/appendix-1-2-pricing-and-usage-table-en.pdf),
[외부 배포 부속서 4(2026-09-28 개정)](https://pro.jpx-jquants.com/pdfs/appendix-4-external-distribution-en.pdf)

### ③ 파생값의 허용 근거와 제한

**조건부 허용 근거는 있다.** Tiingo 약관 §1.6(c)는 원자료·서비스를 대체하지
않고 다른 공개 정보와 결합해도 원자료를 복원할 수 없는 파생 결과의 배포를
허용한다. 복원 가능한 단일 종목의 연속 수익률·100 기준 경로는 금지 예시에
해당한다. 무료 Starter/Trial은 원자료와 파생값의 **기간과 무관한 지속/내구 저장**을
금지한다. 짧은 TTL의 파일/IndexedDB나 공개 Git 스냅샷도 허용된 보관 경로가 아니다.
기존 점수·방법론을 바꾸는 우회는 없다. 아래 Tiingo 검토의 계정·약관 적용일 구분을 따른다.
[Tiingo 약관 §1.6(2026-10-06 개정)](https://app.tiingo.com/tos/)

Twelve Data는 복원 불가능한 Derived Data 생성과 고객 권리를 규정하지만
§2의 사용·공개 제한이 함께 적용된다. 생성 권리를 별도 공개 파일 허가로
해석하지 않는다. EODHD의 개인 약관은 재포장 형태까지 공개를 금지한다.
공급자별 기존 QGV 점수·V 근거·리더보드·시가총액·구성 목록 각각의 공개
허용 여부를 판정해야 한다.
[Twelve Data §2·§6.2](https://twelvedata.com/terms),
[EODHD 개인/사업용 약관](https://eodhd.com/financial-apis/terms-conditions)

Market Data의 교육·저널리즘 조건은 복원 불가능한 집계 발표를 허용하지만
범위가 해당 저작물로 한정되며 기계 판독 파일·API·제3자용 소프트웨어와
저장소 배포를 금지한다. 이 앱의 공개 JSON에는 적용할 수 없다.
[공식 역사 데이터 공개 이용조건](https://www.marketdata.app/terms/public-use/)

### ④ 공식 보완 대안의 범위

- **JPX J-Quants 개인 API:** 일본의 조정/미조정 역사 OHLC를 제공하는 공식
  출처다. 개인 서비스와 Pro 공개 배포 계약은 별개다. 개인 사이트 직접
  조회가 접근 제한으로 실패해 현재 무료 플랜 지연·가격·8035 개별 접근권은
  확정하지 않았다. 기존 제3자 설명의 무료 지연 수치를 최신 조건처럼
  가져오지 않는다. [JPX 공식 서비스 설명](https://www.jpx.co.jp/english/markets/other-data-services/j-quants-api/index.html)
- **KRX Open API:** §11②의 제3자 제공 금지 때문에 공개 원시 JSON 출처로
  채택 불가다. §11③은 계약 종료 후 이용도 제한한다. 개인 기기 후보로
  검토할 경우도 계정·키·직접 호출·조건 확인이 필요하다.
  [공식 약관](https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO002.jsp)
- **기존 GOOGLEFINANCE:** 현재 시세의 기기 직접 입력 경로만 유지한다.
  공식 안내는 역사 데이터를 Sheets API/Apps Script로 가져올 수 없다고
  명시한다. D4 일봉 해결책으로 확장하지 않는다. Tokyo 미지원에 대한 기존
  실측 결정을 유지한다. [Google 공식 제한](https://support.google.com/docs/answer/3093281?hl=en)
- **Tiingo 사용자 키:** 공식 문서는 앱 사용자가 각자 자신의 키를 넣고 앱이
  데이터를 배포하지 않는 방식과 공급자가 수집해 재배포하는 방식을 구분한다.
  후자는 별도 redistribution license가 필요하다. 기존 Secret의 서버 수집·공개 권리를
  이 기기 직접 조회 모델로 대신하지 않는다. [Developer Program](https://www.tiingo.com/documentation/appendix/developers)

### Tiingo

기존 Secret·무료/현재 요금제와 정확한 19종목을 검토했다.

**`TIINGO_API_KEY`**가 정확한 이름이다. `.github/workflows/c21-real-data.yml:160`의
`secrets.TIINGO_API_KEY` 참조를 확인했다. 존재는 사용자 확인을 근거로 한다.
이름 목록 조회는 HTTP 403으로 거부돼 독립적으로 확인하지 못했으며 값 조회나
인증 호출로 우회하지 않았다. **실제 계정 플랜·잔여 한도·적용 약관/추가 계약은 미확인**이다.

공식 [가격표](https://www.tiingo.com/pricing)의 공개 개인 요금제 비교(2026-10-09 UTC):

| 항목 | Starter | Power |
| --- | --- | --- |
| 가격 | **$0/월** | **$30/월** |
| 월 unique symbols | **500** | 110,229 |
| 최대 요청/시간 | **50** | 10,000 |
| 최대 요청/일 | **1,000** | 100,000 |
| 월 대역폭 | **1GB** | 40GB |
| 라이선스 | **Internal Use Only** | **Internal Use Only** |

과거 안내의 50 unique tickers를 현재 월 한도로 쓰지 않는다. [한도 안내](https://www.tiingo.com/documentation/general/overview)는
시간 한도를 매시간, 일 한도를 midnight EST에 초기화하며 분/초 고정 한도는 없다고 한다.
종목당 요청 1개라면 17~19회/일은 요청·심볼 예산 안이지만 백필·재시도·대역폭도 합산한다.
가격표의 30+년은 각 회사 30년 이력을 보장하지 않는다.

| 정확한 D4 범위 | 공개 지원목록 확인 |
| --- | --- |
| 미국 · USD | **17/17 존재**: `ASML, LRCX, KLAC, NVDA, AMD, AVGO, QCOM, INTC, MSFT, GOOGL, AMZN, RTX, SYK, ETN, HUBB, GEV, ROK`; 모두 `endDate=2026-10-08` |
| 일본 · JPY | **TSE:8035 본상장 없음**, TSE 거래소 항목 없음 |
| 한국 · KRW | **KRX:042700 본상장 없음**, KRX 거래소 항목 없음 |

[Symbology](https://www.tiingo.com/documentation/appendix/symbology)는 미국 주식/ETF/펀드와 중국 주식을
안내하고 [EOD 상품](https://www.tiingo.com/products/end-of-day-stock-price-data)의 거래소 목록에도
TSE·KRX가 없다. 인증 없이 읽은 [공식 supported_tickers.zip](https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip)
108,972행에서 두 거래소와 `8035`·`042700` 본상장을 찾지 못했다(2026-10-09 UTC).
Tokyo Electron 미국 OTC `TOELY`·`TOELF`·`TELWY`는 TSE 8035의 대체물로 쓰지 않는다.
[EOD 문서](https://www.tiingo.com/documentation/end-of-day)는 예약 심볼도 목록에 포함된다고 경고한다.
17개 목록 존재는 실제 계정 API 성공·전체 이력 완전성의 증명이 아니다.
공개목록상 GEV는 2024-03-27, HUBB는 2015-12-24부터다.

[공식 약관](https://app.tiingo.com/tos/)의 최종 변경 표시는 **2026-10-06**, 조회는 **2026-10-09 UTC**다.

| 조항 | 짧은 원문 | 설계 적용 |
| --- | --- | --- |
| §1.6(a) | “any persistent or durable storage” | Starter/Trial 원본·파생물의 비휘발성 저장 금지; 일시적인 파일·로그·DB 저장도 포함 |
| §1.6(c) | “simple transformations of open, high, low, close, volume” | 형식/필드명 변경으로 가격 JSON 공개 권리가 생기지 않음 |
| §7.3 | “special request and permission” | API 재배포는 별도 허가·추가 비용 필요 |
| §7.3 | “Data sourced by Tiingo” | 허가 후에도 출처 표시와 Tiingo 링크 필요 |

§1.6(b)의 유효 유료 플랜 내부 저장도 종료·다운그레이드 시 원본 삭제가 필요하다.
§1.6 예외는 Start-up/Enterprise/Institutional의 별도 서면 계약으로만 가능하며 Starter/Power에는 제공하지 않는다.
기존 이용자의 개정 적용은 게시/이메일 통지 후 30일 조건이고 추가 약관이 우선할 수 있다.
**10월 6일 변경 표시만으로 이 계정의 10월 9일 적용 약관을 확정하지 않는다.**
공개 최신 조건을 설계 기준으로 삼되 실제 계약·통지일은 미확인이다.
EOD 상품의 Display Redistribution 가격도 원시 JSON·Git 이력 배포 허가를 확정하지 않는다.

**판정: 미국 17종목 내부 사용 후보는 조건부 가능. 무료 Starter의 비휘발성 저장과 별도 계약 없는
공개 Pages OHLCV JSON은 공개 최신 조건상 불가. TSE 8035·KRX 042700은 다른 출처가 필요해
Tiingo 단독 19종목 선택지는 채택하지 않는다.** 현재 fallback은 종가·UTC 21:00·USD 중심이므로
19종목 전체 OHLCV 어댑터로 그대로 재사용하지 않는다. 기존 코드·워크플로·데이터는 변경하지 않는다.

Yahoo 비공식 호출·운영 스크래핑·출처 불명 공개 JSON은 후보에서 제외한다.

## 사용자 결정과 가격 단계 진입 조건

1. **목표와 예산:** 최신 공개 500·완전 QGV까지 필요한지, 원시 가격은 기기
   차트에만 두는 부분 접근으로 시작할지 결정한다. 후자는 D1과 완전한 D3를
   해결한 것으로 표시하지 않는다. 무료 19/19 자동화는 이번 조사에서 확인되지 않았다.
2. **공개 권리:** 공급자가 정확한 종목·이력·가격/기업행위·파생값 및 익명
   JSON/Git 이력·캐시·보관·계약 종료 조건을 서면으로 승인해야 한다. 공개
   파일 배포가 금지된 계약이면 현재 Pages 구조의 해당 가격 단계는 보류한다.
3. **승인 경계:** 채택 결정과 26E append-only 변경 기록, 서버 수집/공개 시세
   금지에 대한 명시적 새 승인, 별도 구현 PR 승인이 필요하다. 사용자 개인
   키·구글 시트·보유·거래·평균단가는 계속 기기 전용이다.

권리·비용·19종목 제공·CORS의 미확인은 수집 실험이나 기본값 변경으로
해소하지 않았다. 소스 지연·시장별 거래일·PIT·실패 처리는
[파이프라인 설계](PIPELINE_DESIGN.md)의 동일 규칙을 적용한다.
