# 개인 전용 무료 주가 경로 조사·설계 — Yahoo 1순위

조회일: **2026-10-09 UTC**. 최신 사용자 결정은 **무료 + 사용자 본인만 사용, Yahoo Finance 비공식 chart를 주가 1순위로 검토**하는 것이다.
앞선 A~H의 Tiingo·Google 시트 중심 설계를 이 문서의 1~7로 대체한다. 기존 비교는 7절에 남긴다.
이 문서는 조사·설계만 다룬다. 가입·키/계정 접근·실제 가격/시트 조회·Worker/OAuth 설정·구현·배포·QGV 재점수를 실행하지 않았다.
결정은 [26E GSQ-007](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md#gsq-007--26e-yahoo-finance-우선-개인-가격-경로-정정-2026-10-09-utc)에 append-only 기록한다.

## 최신 결정과 1~7 판정

주가 원자료와 **가격 기반 파생값(V=Valuation·시총 순위·가격을 결합한 QGV 등)**은 공개 저장소·Pages·Actions 로그/산출물에 저장·게시하지 않는다.
SEC·DART 공개 재무 자료는 기존 공개 경로와 PIT·검증 기준을 유지한다. 재무와 가격을 결합한 결과는 본인 전용 경로에서만 처리한다.
기존 Frozen 종목 **구성**을 유지하며 오늘의 Top 500을 새로 발견한 목록으로 표시하지 않는다. 투자 방법론·점수식·TARGET·Holdout·운영 모드를 바꾸지 않는다.
이 결정은 [기존 공개 가격 선택안](../pages_cockpit_owner/QUOTES_FX_OPTIONS_26E.md)의 Yahoo 운영 채택 금지를 **본인 전용 조회·표시 후보 범위에서 변경**한다.
과거 문서는 이력으로 남기며, 개인 경로를 공개 가격 배포 권한으로 확대하지 않는다.

**핵심 한계:** Yahoo의 공식 약관은 사전 허가 없는 자동 수집을 금지한다. 사용자 선택·키 없음·개인 사용·저빈도·무저장은 공급자의 허가를 대신하지 않는다.
따라서 아래 기술 설계를 작성할 수 있으나 **사전 허가 없는 Yahoo 자동 조회는 현행 약관에 부합한다고 판정할 수 없다**. 공식 허가 근거는 확인되지 않았다.

| 요구 | 판정 | 확인된 범위와 남은 조건 |
| --- | --- | --- |
| 1 Yahoo → 본인 Worker → 휴대폰 | **기술 조건부 / 무허가 자동 조회는 약관 부적합** | 키 없는 비공식 endpoint는 기존 코드에 있다. 본인 인증·모바일 CORS·무료 CPU와 Yahoo 접근 허가 확인이 필요하다. |
| 2 한 기업 과거 일봉·무저장·짧은 캐시 | **조건부 / 지속 캐시 미채택** | 일봉 파서 참고 가능. 실제 3종목 이력·기업행위·표시권은 미확인. 짧은 RAM 재사용도 허가된 조회의 동일 작업 안으로 제한한다. |
| 3 하루 1회 현재가 → 개인 V·순위 | **조건부** | 종목별 요청 예산·기기 RAM 계산 설계 가능. Yahoo 자동 수집권, 500개 완전성·주식수/통화/시각·현재 QGV 엔진 상태가 남는다. |
| 4 3시장 심볼·기존 provider | **심볼 규칙 가능 / 코드 재사용 조건부** | 미국 티커, `042700.KS`, `8035.T`. 기존 Python endpoint/파서만 참고하며 잘못된 통화·시각 fallback과 저장 도구는 재사용하지 않는다. |
| 5 무료 중계·본인 접근·비용 0 | **조건부** | Workers Free·본인 1명 인증·cap 초과 중단. CPU·전화기 로그인/CORS 실측, Free 가입/요금 조건 확인 필요. |
| 6 약관·차단·형식 감지와 대체 | **설계 가능 / 실동작 미검증** | 비가격 상태 메타데이터로 감지, 우회 없이 공급자별 차단·대체·결측 처리. 실제 장애시험은 구현 범위다. |
| 7 대체 출처 비교 | **조건부 후보 / 일부 무료안 불가** | Tiingo(미국), KRX(한국), 본인 Sheet 현재가, 수동을 우선순위로 둔다. Alpha·Twelve Data·FMP·Polygon/Massive는 비교이며 자동 채택하지 않는다. |

### 현재 공개 경로에 남은 차단 과제

읽기 전용 점검에서 아래 **필드의 포함·non-null 여부만** 확인했다. 실제 가격·V·순위 값은 출력하지 않았다.

| 현재 경로 | 새 원칙과의 gap |
| --- | --- |
| `reports/gate_evidence/official_snapshot_2024-*.json` | tracked Frozen 원문에 `cutoff_mcap`, `members[].mcap/rank`가 있다. |
| `reports/v_coverage_us17_2026-09-23.json`, `reports/official_v11_book_snapshots.json` | 가격 기반 V 결과/후보 필드가 있다. 기본 Pages에 실제 V가 연결된다는 확인은 아니다. |
| `data/raw/tiingo_run_1790379027.json`, `reports/gate_evidence/nport_reported_prices_2024-06-30.json` | tracked 원문에 가격 필드가 있다. 이 문서에서 삭제·재출판하지 않았다. |
| [Pages 빌더](../../tools/build_pages_cockpit.py), [공개 bundle](../../src/investment_system/product/web_mvp.py) | 시총 금액은 제거하지만 `market_cap_rank`/Frozen `rank`가 공개 projection에 남는다. |
| [기존 Actions](../../../.github/workflows/c21-real-data.yml), [가격 도구](../../tools/nport_reported_prices.py) | 원문·gate evidence artifact/자동 커밋·가격 stdout 경로가 있어 후속 감사가 필요하다. 기존 외부 배포·과거 로그의 실제 내용은 조사하지 않았다. |

기존 [artifact guard](../../tools/pages_artifact_guard.py)의 PASS는 새 가격/V/순위 금지 경계의 PASS와 다르다.
공개 Frozen 구성 유지와 가격 기반 금액·순위 제거는 별개다. 보호된 이력·evidence를 문서 작업에서 지우거나 gate를 우회하지 않는다.
후속 구현은 공개 **membership-only** 식별 자료와 공개 재무 입력만 읽고, 개인 가격·점수·시총 순위를 공개 bundle로 돌려보내지 않아야 한다.
기존 [entity catalog](../../src/investment_system/product/entity_catalog.py)의 `entities.json` COMPANY 목록은 가격·rank 없는 후보이나,
exchange/currency/provider_symbol과 pin된 Frozen as_of/universe_id/hash가 없어 listing map으로 바로 사용할 수 없다.
TARGET19는 [actual catalog](../../src/investment_system/product/device_actual_catalog.py)의 식별·통화·hash를 참고하고 별도 Yahoo mapping을 대조한다.

## 1. Yahoo → 사용자 전용 중계 → 휴대폰

제안 흐름은 **본인 앱 → 본인 인증 Worker → Yahoo chart → 본인 앱 RAM**이다.
가격 조회·가격 결합 QGV 계산을 GitHub Actions로 실행하거나 공개 JSON 생산자에 연결하지 않는다.
Worker는 허용된 회사·시장별 심볼·일봉 interval·기간·응답 크기만 받는다. 임의 URL을 전달하는 공개 프록시를 만들지 않는다.
Yahoo에는 API 키를 넣지 않는다. Cookie/crumb가 요구되면 인증 우회·타인 세션·키 회전·프록시 회전으로 해결하지 않고 중단한다.

[기존 provider](../../src/investment_system/providers/yahoo_chart.py)는
`https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={range}`를 사용한다.
이것은 비공식 접근점이며 공식 무료 API 상품·SLA·정량 호출 한도·chart 이용 라이선스는 확인되지 않았다.
Yahoo 서버 fetch와 휴대폰→Worker/Access CORS는 서로 다르다. Yahoo의 브라우저 CORS 허용을 문서화하거나 실측하지 않았다.
기존 repository에서 호출한 사실을 허가·향후 3시장 가용성의 증거로 쓰지 않는다.

### Yahoo 약관 원문과 캐시 판단

[Yahoo US TOS](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html)의 표시 개정일은 **2026-08-04**다.
[Singapore TOS](https://legal.yahoo.com/sg/en/yahoo/terms/otos/index.html)는 **2026-08-19**이며 실제 적용 지역·계약은 사용자 확인 사항이다.
US §2(d)(ix)는 자동 수집에 대해 **“for any purpose without our express, prior permission”**이라고 제한한다.
§2(e)는 제공 interface·instruction 이외 접근 방법을 제한한다. 공개 URL과 키 없는 접근은 이 제한의 예외가 아니다.
§2(d)(x)의 경쟁·실질 대체 앱/data feed 제한에 해당하는지도 미확인이며 모든 개인 분석이 금지됐다고 확대하지 않는다.
본인용 원시 차트·V/순위 가공·외부 클라우드 중계의 명시 허가도 확인되지 않았다.

[Yahoo Finance 공식 Help](https://help.yahoo.com/kb/finance/SLN2310.html)는 **“You must not redistribute information displayed on or provided by Yahoo Finance.”**라고 명시한다.
정보용·as-is·정확성/계속 제공 비보장이며, 시장별 데이터 공급자와 지연이 다르다.
LSEG 콘텐츠의 caching 포함 재사용에는 별도 동의 조건도 있다. 모든 chart가 LSEG라고 단정하지 않지만 짧은 TTL이면 자동 허용된다고 판단하지 않는다.
범용 [Yahoo Developer API 약관](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html)의 user data 24시간 조건을 비공식 chart 가격 보관 허가로 전용하지 않는다.

**기본은 지속 캐시 없음**이다. 허가된 요청의 진행 중 중복 클릭을 같은 in-flight 응답으로 합치는 RAM 처리만 후보로 둔다.
캐시 예산 후보는 동일 화면·동일 작업에서 최대 60초 RAM 재사용이며 **허가·실제 약관 적합성을 확인하기 전 활성화하지 않는다**.
차트 닫기·로그아웃·작업 종료 시 제거한다. Worker isolate RAM은 다른 요청에 남을 수 있으므로 사용자를 섞는 module-global price cache는 제외한다.
Cache API·KV/D1/R2·파일·localStorage·IndexedDB·service worker·로그·백업에 짧은 TTL로 적재하는 방식도 채택하지 않는다.

## 2. 연 기업 한 개의 과거 일봉

사용자가 차트를 연 회사 하나만 요청하고 자동 polling·미리 전체 종목 차트 수집을 하지 않는다.
기존 endpoint/`parse_bars`의 `timestamp`, `indicators.quote.close`, `indicators.adjclose.adjclose`가 해석 참고점이다.
현재 파서는 close/adjclose만 만들므로 OHLC·거래량 전체 차트 계약을 이미 제공한다고 표시하지 않는다.
범위는 후속 구현에서 고정 allowlist와 크기 상한을 적용한다. 비공식 chart의 최대 과거 기간·세 시장별 전체 이력은 이번 조사에서 확정하지 않았다.

화면 출처는 **Yahoo Finance(비공식)**, 거래소·원 심볼·통화·daily·raw/adjusted basis·최근 session·실제 관측 수·취득 시각이다.
일봉 timestamp를 가격의 최초 공개 시각으로 쓰지 않는다. 마지막 bar가 진행 중인 시장 세션이면 완료 종가와 분리한다.
관측 길이 불일치·null·비유한/0 이하 가격·중복·역순·통화/심볼 불일치·기업행위/조정 배열 결측은 감지해 결측 또는 지원 불가로 표시한다.
공급자별 raw/adjusted를 한 연속 시리즈에 이어 붙이거나 누락을 0·전일값으로 메우지 않는다.
가격을 보존하지 않으므로 과거 가격 PIT replay·과거 QGV의 완전한 재현을 제공한다고 표시하지 않는다.

## 3. 하루 1회 개인 리더보드·QGV

본인이 하루 한 번 foreground 작업을 시작하고, 서버 가격 archive·무인 가격 예약 작업은 이 첫 설계에 넣지 않는다.
현재 입력은 `meta.regularMarketPrice`와 대응하는 `regularMarketTime`을 검증하는 후보이며 장중/지연값과 최근 완료 종가를 구분한다.
누락 시 마지막 close로 대체하려면 **그 close의 실제 bar timestamp와 basis**를 같이 사용하고 현재가로 위장하지 않는다.
`read_at`은 실제 취득 시각이며 `price_as_of`가 아니다. 최신 값이 지연되거나 시각을 모르면 `DELAYED/UNKNOWN`이다.

| 자체 운용 예산 제안 — 공급자 허용 한도가 아님 | 호출량·완전성 |
| --- | --- |
| 기본 속도 | 본인 계정 전체에서 **최대 1 upstream 요청/5초, 동시 1개**, foreground 한 작업만. 공식 허용 수치가 아닌 보수적 후보이며 이 속도도 차단되지 않는다는 보장은 없다. |
| TARGET 19 | 미국17 + 한국1 + 일본1이면 단순 최소 19회, 대기 간격만 약 95초 예산. 실제 가용성·응답 시간·휴장·재시도는 별도다. 공개 TARGET은 실제 보유목록이 아니다. |
| Frozen 500 | 기존 단일-symbol chart 방식이면 최소 **500 upstream 요청**. 5초 간격만 약 42분이며 정확히 동시에 관측한 현재가가 아니다. 공개 quote batch를 새로 가정해 요청 수를 줄이지 않는다. |
| 일일 상한 후보 | 종목군 최대 500회 + 사용자가 연 차트 20회 + 제한된 retry 10회 = **최대 530회/일**, 다른 본인 호출까지 합산. 초과는 다음 작업까지 중단. 무한 retry·다중 탭/키로 상한 우회 없음. |
| 무료 Worker 경계 | 요청마다 upstream 1개를 우선해 subrequest 상한을 피한다. 더 큰 묶음은 JWT/JSON CPU·payload·모바일 연결을 실측한 뒤에만 검토한다. 500 요청은 Worker 일 100,000보다 작지만 CPU·제공자 사용권의 증명은 아니다. |

TARGET19와 Frozen500은 별도 예산 사례다. 두 집합을 합치면 최대519 listing이므로 동일 상장만 중복 제거하고,
500회 종목군 상한을 넘는 요청은 별도 작업으로 자동 추가하지 않는다. 요청되지 않은 항목은 결측/subset으로 표시한다.
전역 순차 속도와 하루 1회 보장은 isolate RAM counter만으로 구현되지 않는다. 후속 구현에서 가격 없는 작업 상태/count/reset-time만 private 직렬화하거나,
단일 기기 세션으로 동시 실행을 막는 한계를 명시해야 한다. 저장 제품 추가 시 별도 Free 한도·요금 검증이 필요하며 가격/파생값은 넣지 않는다.
작업 완료 후 결과는 본인 앱 RAM에서만 계산·표시한다. 앱 종료 후 다음 날까지 점수를 보관하는 방식은 기본 설계에 넣지 않는다.

V는 volume이 아닌 **Valuation**이다. 현재가만으로 시총이 생기지 않으며 같은 주식 종류의 검증된 shares 또는 market cap·통화·basis가 필요하다.
chart 응답에 시총·현재 주식수가 항상 있다고 가정하지 않는다. 공개 SEC/DART 재무 입력은 통화·단위·주식 종류·공시 가용 시각·정정 vintage를 대조한다.
500 회사 중 필수 입력이 하나라도 빠지면 완전한 500 순위는 UNKNOWN이다. 유효 499행을 새 분모로 전체 순위처럼 표시하지 않는다.
일부 subset 결과는 subset·기준시각 범위를 표시한다. 이 설계는 기존 QGV 점수식·생산자 연구 상태를 운영 검증 완료로 승격하지 않는다.
장시간 500 조회와 시장별 휴장/지연을 고려해 `PERSONAL_DELAYED_CURRENT_INPUT`을 사용하며 EOD·현재 Top 500·정확한 일일 PIT로 표시하지 않는다.

## 4. 3시장 심볼과 기존 provider 재사용

[Yahoo 공식 거래소 표](https://help.yahoo.com/kb/finance/SLN2310.html)는 한국 유가증권시장 `.KS`, KOSDAQ `.KQ`, 도쿄 `.T`를 안내한다.
KRX와 Tokyo의 표에는 **20분 지연**이 표시된다. 이는 실제 응답의 지연·종목 가용성 SLA가 아니다.

| 회사/시장 | Yahoo 심볼 규칙 | 통화·시간 검증 |
| --- | --- | --- |
| 공개 TARGET 미국17 | 승인된 미국 상장 ticker 유지: 예 `NVDA`, `GOOGL`, NASDAQ `ASML`. class/security mapping을 먼저 확인. | USD·미국 해당 exchange/timezone. 클래스 구분 기호는 회사별 명시 mapping으로 검증. |
| 한미반도체 KRX 042700 | **`042700.KS`**, 선행 0 보존. KOSDAQ `.KQ`나 OTC로 치환하지 않는다. | KRW·Asia/Seoul 후보를 provider meta와 거래소에 대조. |
| Tokyo Electron TSE 8035 | **`8035.T`**, 같은 회사의 미국 OTC/ADR로 치환하지 않는다. | JPY·Asia/Tokyo 후보를 검증. |

이 두 개별 Yahoo 심볼의 실응답은 조회하지 않았으므로 규칙과 실제 coverage를 구분한다.
[기존 `yahoo_chart.py`](../../src/investment_system/providers/yahoo_chart.py)는 Python/urllib이므로 Worker에 그대로 배포하는 것으로 설계하지 않는다.
endpoint·응답 파서·PricePoint/DataStamp의 개념을 재사용 대상으로 문서화하되 다음 계약 보완이 필요하다.

- `parse_chart`의 누락 통화→USD, 누락 시각→현재 UTC fallback은 제거 대상이다. 원 통화/시각 미확인은 UNKNOWN으로 남긴다.
- 마지막 close fallback의 시각과 quote 시각을 분리한다. `published_at/available_at=observed_at`을 실제 최초 공개/PIT 증거로 인정하지 않는다.
- `parse_bars`의 adjclose 우선 선택을 전체 시리즈의 기업행위 조정 검증으로 간주하지 않는다. 원 close·adjclose·basis를 구분한다.
- [기존 수집 도구](../../tools/fetch_real_data.py)의 `yahoo_symbol`은 `.`을 `-`로 바꾸므로 `042700.KS/8035.T`에 적용하지 않는다. 시장별 provider_symbol을 명시한다.
- 같은 도구의 RawDatasetStore·manifest·ingest report·stdout, 공개 가격이 결합되는 기존 pipeline을 개인 경로로 실행하지 않는다.

개인 응답 계약 후보는 `provider`, `provider_symbol`, `exchange`, `currency`, `interval`, `price_as_of/session`, `read_at`, `basis`, `delay_status`, `availability_reason`이다.
실제 숫자 가격과 V/순위는 본인 인증 응답/RAM에만 있고 공개 receipt·Actions artifact·PR·로그에는 넣지 않는다.

## 5. Cloudflare 무료 중계·접근 제한·비용 0

[Workers Free 한도](https://developers.cloudflare.com/workers/platform/limits/)는 계정 합산 **100,000 요청/일(UTC 자정 reset)**,
HTTP/Cron **CPU 10 ms**, isolate **128MB**, 외부 subrequest **50/호출**, 동시에 응답 헤더를 기다리는 외부 연결 **6/호출**, Cron **5/account**다.
네트워크 대기는 CPU와 다르다. JWT·전체시장 KRX 응답·JSON이 10ms에 들어오는지는 미확인이다. 계산은 기기에 두며 Free 실패 시 미제공으로 끝낸다.
한도 초과 1027·CPU/메모리 초과 1102를 처리하고 route는 fail closed를 사용한다.
[Workers Paid 최소 $5/월](https://developers.cloudflare.com/workers/platform/pricing/)은 선택하지 않는다. egress 별도 요금 없음이 다른 제품의 무료 보장은 아니다.
[workers.dev](https://developers.cloudflare.com/workers/configuration/routing/workers-dev/)로 도메인 구매 없는 개인 URL을 검토하며 유료 add-on·저장·로그·Containers는 추가하지 않는다.

| 항목 | 설계 조건 |
| --- | --- |
| 본인 인증 | [Google IdP](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/google/) + Access에서 정확한 본인 계정 Allow·Google 인증 Require. Everyone/전체 도메인/Bypass 금지. 로그인만 성공한 다른 계정은 거부. |
| Worker identity | [Workers Access](https://developers.cloudflare.com/workers/configuration/cloudflare-access/) 직접 인증 invocation의 검증된 `ctx.access`만 사용하고 undefined는 거부. Static Assets 내부 router/Service Binding에 identity 전파를 가정하지 않는다. 기본/preview URL도 보호한다. |
| 대안 인증 | [Google ID token](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token) 서명·issuer·audience·expiry·본인 sub 검증. 기존 Sheets readonly access token은 Worker 신원 증명이 아니다. Origin/CORS는 인증이 아니다. |
| 키 | Yahoo 키는 없음. 선택한 Tiingo·KRX 등 본인 키는 [Worker Secret binding](https://developers.cloudflare.com/workers/configuration/secrets/)에만 보관한다. KRX 보유 여부는 사용자 확인 예정, 이름은 `KRX_API_KEY`. DART 재무용 `DART_API_KEY`와 가격 키를 섞지 않는다. 이번 작업에서 이름 외 값·존재 여부를 조회하지 않았다. |
| 비보존 | upstream `cache: no-store`, 개인 응답 `Cache-Control: private, no-store`, 가격/V/순위 Cache API·DB·파일·외부 분석·백업 금지. 공급자/플랫폼 내부 모든 메타데이터 보존이 0이라는 보장은 아니다. |
| 로그 | [새 Worker observability 기본 enabled](https://developers.cloudflare.com/workers/observability/logs/workers-logs/)이므로 배포 전 Workers Logs/observability·invocation 로그 수집을 명시적으로 끈다. body/custom 로그·Authorization·실제 키 URL·가격·개인 점수 출력 없음. |
| CORS | [Access CORS](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/cors/)의 cookie/preflight를 실제 휴대폰 origin에서 확인한다. 서버 fetch 성공이 이 검증을 대신하지 않는다. |
| 한도 | isolate RAM과 [Rate Limiting binding](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/)은 정확한 전역 한도 장부가 아니다. own run·provider별 count·중단·개인 상태 메타데이터 별도 검증이 필요하다. |

Access는 [2026 공식 안내](https://blog.cloudflare.com/adaptive-access-user-risk-scoring/)에 50명까지 무료 근거가 있으나 현재 Free 가입 화면은 사용자가 확인한다. 본인 1명만 허용한다.
[Zero Trust setup](https://developers.cloudflare.com/cloudflare-one/setup/)은 Free도 payment details 입력이 필요하나 청구하지 않는다고 안내한다.
결제정보 등록을 원치 않으면 ID-token 직접 검증 대안도 조건부다. Workers Free 가입 자체의 동일 조건으로 혼동하지 않는다.
Free 선택·다른 구독 없음·초과 시 중단·주기적 요금/한도 재확인이 비용 0 조건이다. 무료 계정의 미래 요금 유지까지 보장하지 않는다.
[Cloudflare Developer Platform 약관 §4](https://www.cloudflare.com/service-specific-terms-developer-platform/)의 제3자 약관 준수 조건을 따르며 중계 기술로 Yahoo/대체 출처 사용권을 대신하지 않는다.

## 6. 약관·차단·형식 감지와 대체 규칙

| 감지 | 동작·기록 경계 |
| --- | --- |
| 약관/출처 조건 변경 | 구현 시작 전·주기적 수동 검토에서 공식 URL/개정일/허용 범위를 다시 확인. 허용 근거가 없거나 철회되면 공급자 중단. 공개 조사에는 약관 URL·개정일·판정만 남기고 가격 응답을 첨부하지 않는다. |
| HTTP 401/403/429·captcha/HTML·crumb 요구 | 즉시 해당 Yahoo 경로를 멈춘다. Retry-After가 있어도 만료가 재허가/성공 보장은 아니다. 같은 실행에서 재폭주·IP/UA/쿠키 회전·차단 우회 없음. 다음 사용자 작업에서도 계속 막히면 출처 unavailable. |
| timeout/5xx | 전체 일일 retry 예산 안에서 최대 1회만 bounded backoff 후보. 연속 실패는 공급자 작업 중단·대체. 오류 원문/HTML/가격 포함 body는 저장·로그하지 않는다. |
| chart.error/result 없음·schema/type/배열/identity 변경 | 내부 reason·HTTP code·provider·실패 count/reset-time 같은 **비가격 메타데이터만** 개인 운영 상태로 사용. UNKNOWN/NOT_AVAILABLE를 반환하며 parser 추측·통화/시각/가격 0 default 금지. |
| 오래된 시각·잘못된 통화/조정·부분 universe | 해당 행 결측/지연 표시. 완전한 순위/QGV 산출 불가이면 UNKNOWN. 진입일·휴장·진행중 세션은 거래일 검증으로 구분. |

| 용도·시장 | 최신 사용자 대체 순서 | 표시·불가한 대체 |
| --- | --- | --- |
| 미국 과거 차트 | **Yahoo → Tiingo(미국) → 수동/NOT_AVAILABLE** | 허가·계정 한도 충족 출처만 사용. Tiingo 실패 후 Alpha 등 비교 후보로 자동 이동하지 않는다. Sheet 현재가로 과거 시리즈를 만들지 않는다. |
| 한국 과거 차트 | **Yahoo `042700.KS` → KRX → 수동/NOT_AVAILABLE** | KRX는 승인·중계권 확인된 비수정 일봉만. raw/adjusted가 바뀌면 시리즈 전체 교체. |
| 일본 과거 차트 | **Yahoo `8035.T` → 수동/NOT_AVAILABLE** | Tiingo 미국/KRX 한국은 일본 대체가 아니다. Google 시트 현재값이나 OTC/ADR로 일봉을 대체하지 않는다. |
| 현재가/개인 V 입력 | **Yahoo → 시장에 맞는 Tiingo(미국)/KRX(한국) → 본인 Google 시트 현재가 → 수동** | KRX의 전일 종가는 현재 실시간 값이 아니므로 별도 종가/지연 표시. Japanese는 맞는 중간 공급자가 없으면 본인 Sheet 지원 여부 확인 후 수동. |
| 마지막 실패 | 해당 값 결측, 관련 V/순위 UNKNOWN | **0·전일값·다른 상장 종목으로 대체하지 않는다.** 단일 수동 가격이 과거 일봉 이력을 충족한다고 표시하지 않는다. |

자동 대체의 전제는 각 출처의 개인 사용·무저장·중계·무료 한도 확인이다. Yahoo 차단이 다른 공급자 허가를 만들지 않는다.
차트는 전체 시리즈를 교체하며 자료를 이어 붙이지 않는다. 순위 입력에 출처가 섞이면 행별 공급자·가격 시각·통화·basis를 표시하고 비교 시각 범위/결측 수를 드러낸다.
출처 표시는 **Yahoo Finance(비공식)** / Tiingo / **한국거래소 통계정보(KRX Open API)** / GOOGLEFINANCE(본인 시트) / 수동이다.
본인 표시에서도 정보용·지연/비공식 상태를 유지하며 실제 체결·투자 판단용 가격 정확성을 보장하지 않는다.

## 7. 대체 출처 — 기존 비교 축약 보존

아래는 비교이며 Yahoo 1순위와 최신 fallback 순서를 변경하지 않는다. 무료 플랜·실제 사용자 계정·3시장 개별 종목 접근권은 별도다.
브라우저 CORS 허용은 공급자 권리와 다르며 서버 relay에서 upstream CORS가 없어져도 앱→Worker 인증/CORS 검증은 남는다.

| 출처 | 무료 한도·과거 기간 | CORS·개인 이용·판정 |
| --- | --- | --- |
| Tiingo(미국) | Starter **$0·500 unique/month·50 requests/hour·1,000/day·1GB/month**. 제공되는 EOD 역사 범위는 종목별, 사용자 계정 플랜은 사용자 확인 예정. | 직접 브라우저 CORS는 이전 익명 OPTIONS에서 허용 헤더 미관측. 자기 token developer 모델이나 private relay/raw 차트 명시 허가는 미확인. Starter 원문·파생은 작업/세션 중 RAM만, 지속 저장 불가. **조건부 대체**. |
| KRX(한국) | **무료·키당10,000/day**(0시~24시), 초/분별 별도 cap 없음. `stk_bydd_trd`: **2010-01-04부터**, 전일 자료 **익일 영업일08:00** 갱신. 비수정 OHLCV. | 승인 키+해당 API 활용 승인 모두 필요. basDd 한 날짜의 전체 유가증권시장 응답에서 종목을 검증·선별; 과거 날짜 수만큼 호출. 개인 연구/투자 비상업, 제3자 제공 금지. 외부 본인 Worker 허용·CORS는 미확인. **조건부 대체**. |
| 본인 GOOGLEFINANCE Sheet | 현재값 최대20분 지연. Sheets read **300/min/project·60/min/user/project**, 분당 한도 내 별도 daily cap 없음. 500행 **1 batchGet/일 + 최대2 retry** 후보. 역사값은 Sheets API/Apps Script #N/A 제한. | 기존 readonly 기기 OAuth 사용, token RAM. 500행 성공 SLA·#N/A 비율 실측 없음. 개인 V/순위 가공의 명시 허가 미확인. **현재가 fallback 후보**, 과거 차트 불가. |
| Alpha Vantage | 무료 **25 requests/day**. DAILY compact **최근 최대100 거래 관측**, raw/as-traded. full·DAILY_ADJUSTED 유료 제외. | 개인/비상업·금융업 종사 commercial 분류 확인. 무료 자체 예산20+여유5 후보. private relay·CORS·정확한 KR/JP 접근권 미확인. **비교 후보**, 최신 자동 fallback에 추가하지 않음. |
| Twelve Data | Basic **8 API credits/min·800/day**, time_series 종목당1 credit·요청 최대5,000관측. 미국 EOD 후보, JP/KR은 유료 Pro 범위. 개별 종목 전체 무료 역사 기간은 미확인. | Basic은 **Internal non-display usage**, 화면 표시 접근은 유료 Grow에 배치. 본인 화면도 non-display라고 단정하지 않는다. CORS 보장 미확인. **무료 차트 채택 보류**. |
| FMP | Basic **250 calls/day·최근30일500MB**, 무료 EOD 포함. **비교표상 역사5년**이나 각 endpoint/symbol 무료 entitlement는 별도 확인. | 개인·비상업 근거와 별도 Data Display and Licensing Agreement 요구를 함께 적용. JP/KR 무료 coverage·CORS 보장 미확인. **표시 권한 확인 전 보류**. |
| Polygon → Massive | Stocks Basic **5 calls/min·2년 이력·EOD**. 미국 주식 전용, JP/KR 현지시장 불가. | 개인·비상업·비전문가 display 조건부. non-display/V 파생 허용으로 확대하지 않는다. CORS 보장 미확인. **비교 후보**, 최신 자동 fallback에 추가하지 않음. |

### 비교 근거와 남은 조건

- **Tiingo:** [가격](https://www.tiingo.com/pricing), [TOS](https://app.tiingo.com/tos/), [Developer Program](https://www.tiingo.com/documentation/appendix/developers), [이전 직접 조회](TIINGO_DEVICE_DIRECT_RESEARCH.md).
  TOS 표시 변경일2026-10-06, 기존 이용자는 통지 후30일 적용 조항이 있어 실제 계정 적용 시점은 미확인. §1.6(a) **“only transiently in volatile memory”**는 원문·파생과 본인 대신 운영되는 서비스에도 적용.
  §1.6(c)의 비복원·비대체 rankings/scores 조건과 raw charts/dashboard 제한을 확인해야 하며 원가격 삭제만으로 V가 비복원이라고 판단하지 않는다.
  월 unique는 watchlist 크기가 아닌 계정 전체에서 실제 요청한 symbol 합집합이다. 500 리더보드 자동 대체는 500 unique 전체와 최소500 호출을 소비하며 채택하지 않는다.
- **KRX:** [약관](https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO002.jsp), [이용방법](https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO003.jsp), [FAQ](https://openapi.krx.co.kr/contents/OPP/COMM/faq/OPPCOMM004.cmd), [공식 FAQ 원문](https://openapi.krx.co.kr/contents/OPP/COMM/faq/OPPCOMM004D1.cmd?pageNum=1&rowCount=100&totalCount=0&pageCount=10), [유가증권 명세](https://openapi.krx.co.kr/contents/OPP/USES/service/OPPUSES002_S2.cmd?BO_ID=JvJFzlAENzZlPBDNGAWC).
  약관 시행2025-12-26. §6② 비상업, §11② **“제3자에게 제공할 수 없다”**, §10③ 화면 **“한국거래소 통계정보”** 표시. 키1년 이용/연장·12개월 미사용 삭제 가능, 키 양도 금지.
  FAQ 무료·비수정·익영업일08시 안내의 시간대 이름은 미명시. 공식 명세의 `ISU_CD`와042700 식별은 실응답 검증 전 미확인이다. 공개 UI sample URL을 production URL로 확정하지 않았다. KRX 키 보유 여부는 사용자 확인 예정이며 보유 시 Secret 이름 `KRX_API_KEY`만 문서화한다.
- **Google:** [함수/지연/역사 제한](https://support.google.com/docs/answer/3093281?hl=en), [Sheets quota](https://developers.google.com/workspace/sheets/api/limits), [batchGet](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/batchGet), [Finance 면책](https://www.google.com/googlefinance/disclaimer/), [API 약관 §5](https://developers.google.com/terms).
  payload2MB 이하 권장·180초 timeout. Standard use 무료 안내와2026년 후반 초과쿼터 과금 계획을 함께 확인하며 실제 프로젝트 무료/과금은 실행 전 확인. Sheets token을 Worker에 전달하지 않는다.
  500개 함수 재계산은 API read quota와 별개. 기대500 고정 분모로 유효·fresh·#N/A·누락/시각미확인 비율을 **기기 RAM**에서만 집계하고 끝행 생략도 결측으로 센다. 최대20분 지연 현재값은 정확한 EOD가 아니다.
  Finance 면책의 저장·가공·전송 사전 동의 조건을 본인 시트로 해소했다고 표시하지 않는다. Tokyo 현행 수동 입력과 종목별 미지원 상태를 유지한다.
- **Alpha Vantage:** [FAQ](https://www.alphavantage.co/support/), [DAILY](https://www.alphavantage.co/documentation/#daily), [TOS](https://www.alphavantage.co/terms_of_service/). 최근100은 달력100일/전체 역사가 아니다. 서로 다른 출처·조정 시리즈를 이어 붙이지 않는다.
- **Twelve Data:** [Individual 가격표](https://twelvedata.com/pricing), [약관](https://twelvedata.com/terms), [시장표](https://twelvedata.com/exchanges), [미국 EOD Basic](https://support.twelvedata.com/en/articles/9935903-us-equities-market-data), [역사 관측 수](https://support.twelvedata.com/en/articles/5656039-how-to-get-historical-prices).
  약관 수정2026-01-01. **“Internal non-display usage”**와 **“Internal display data access”**를 구분한다. 시장 전체 카탈로그가 무료 접근권을 뜻하지 않는다.
- **FMP:** [가격표](https://site.financialmodelingprep.com/pricing-plans), [TOS](https://site.financialmodelingprep.com/terms-of-service), [공식 CORS/중계 가이드](https://site.financialmodelingprep.com/insights/platform/api-access/should-you-call-the-fmp-api-from-the-front-end-back-end-or-a).
  TOS 수정2023-08-01, 개인·비사업·비상업과 가격표의 **“requires a specific Data Display and Licensing Agreement with FMP”** 조건을 함께 확인한다. 하단 비교표 Basic 첫 셀의5년 표시를 확인했으나 개별 가격 endpoint/종목의 무료 접근까지 보장하지 않는다.
- **Polygon/Massive:** [현행 가격](https://massive.com/pricing?product=stocks), [시장 범위](https://massive.com/knowledge-base/article/does-massive-offer-international-data), [Market Data Terms](https://massive.com/legal/market-data-terms-of-service), [2025-10-30 리브랜드](https://massive.com/blog/polygon-is-now-massive).
  약관 수정2025-08-28, §2 **“strictly for display use only”**와 §5(d)의 non-display/파생 제한을 구분한다. 오래된 Polygon PDF를 현행 라이선스로 쓰지 않는다.

## 사용자가 해야 할 일

1. Yahoo 자동 접근의 공식 허가 여부와 적용 지역 약관을 확인한다. 사용자 결정만으로 허가된 것으로 처리하지 않으며 허가 근거가 없으면 Yahoo 자동 조회를 실행하지 않고 허용된 대체/수동을 검토한다.
2. 무료 중계 선택 시 본인 Cloudflare 계정·2FA·Workers Free·workers.dev를 준비한다. Access Free/payment onboarding+Google IdP 또는 본인 ID-token 검증을 고르고 정확한 본인1명만 허용한다. 이번 작업에서 계정을 만들지 않았다.
3. 폰 앱 origin/로그인 흐름, 3시장 심볼·통화·시각·chart basis와 Frozen 구성만 담은 입력 목록을 확인한다. 500 조회 시간·결측을 수용하거나 subset 표시를 선택하며 전체 순위로 오인하지 않게 한다.
4. 대체를 원하면 본인 Tiingo 플랜/조건·월 unique, KRX 키 보유/기한·해당 API 승인/중계 허용 여부를 확인한다. 보유 시 `KRX_API_KEY` 등 키는 사용자 소유 Worker Secret에만 등록하며 채팅·소스·로그·커밋·PR에 값은 넣지 않는다. 이번 조사에서 키 존재를 확인하거나 등록하지 않았다.
5. Google fallback은 본인 비공개 Sheet·기존 readonly 로그인·종목별 지원/시각·가공권·프로젝트 quota/무료 상태를 확인한다. Tokyo 미지원이면 현행 수동을 유지한다. 추가 유료 계약·자동 유료 전환은 하지 않는다.
6. 후속 구현에서 본인 인증/다른 계정 거부·preview 우회·CORS·CPU/cap 초과·차단/형식변경·결측·로그/캐시 비보존을 확인하고, 기존 공개물의 가격/V/시총 순위 노출을 별도 감사한다. 이 문서/기존 guard PASS가 감사 완료를 뜻하지 않는다.

**추천은 허가·Free 조건이 충족된 출처만 본인 경로에서 낮은 빈도로 조회하고, 확인되지 않으면 결측/수동을 유지하는 방식**이다.
이 PR은 문서만이며 병합 승인 대기다. 병합이 공급자 허가·키 발급·중계 배포·가격 수집·QGV 실행 승인은 아니다.


## GSQ-008에 따른 변경

최신 사용자 결정은 [26E GSQ-008](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md)에 append-only 기록한다.
**기존 인증 절과 위 본문은 수정하지 않고 이 메모만 끝에 추가한다.** 아래 변경은
기존 본문의 Zero Trust/Access·본인 ID-token 검증 후보 및 Sheets token을 Worker에
전달하지 않는 선택에 우선하는 최신 중계·인증 결정이다.

- **중계:** 카드 등록을 요구하는 Cloudflare Zero Trust/Access는 사용하지 않는다.
  **Workers Free만 사용하며 비용 0·카드 없음**을 조건으로 둔다. 유료 전환·유료 add-on·카드 등록은 진행하지 않는다.
- **로그인 scope:** 기존 Google Identity Services 로그인에 **`email`**을 추가한다.
  기존 **`https://www.googleapis.com/auth/spreadsheets.readonly`**는 유지한다.
- **검증 흐름:** **앱 → Worker로 Google access token 전달 → Worker가 Google tokeninfo로 검증**한다.
  `aud`는 기존 OAuth 클라이언트 ID, `email`은 사용자 본인 이메일과 일치해야 하며,
  `email_verified`는 참이고 만료 정보는 유효·미만료여야 한다. 하나라도 불일치·누락·
  미확인·만료 또는 tokeninfo 오류이면 거부한다. 실제 ID·이메일·토큰 값은 문서에 넣지 않는다.
- **토큰:** 앱과 Worker의 필요한 휘발성 메모리에서만 취급하며 **저장·로그 출력 금지**다.
  지속 저장·캐시·관측/오류 로그·공개 산출물에 넣거나 Yahoo/다른 가격 공급자로 전달하지 않는다.
- **CORS:** **`https://kco994553-star.github.io`만 허용**한다. wildcard·다른 Origin은
  허용하지 않는다. CORS 허용 여부와 별개로 모든 요청에 본인 tokeninfo 검증이 필요하다.
- **대안:** 비밀 접속 코드 방식은 **보류**한다.

이번 변경은 문서상 결정 기록이다. 앱 scope·Worker·tokeninfo·CORS의 실제 구현·
설정·인증 호출·가입·배포는 실행하지 않으며 **문서 PR 1개는 병합 대기**다.
GSQ-007의 **Yahoo 무허가 자동 조회 부적합 판정과 사용자 인지·수용** 및 가격/파생값
공개 금지·SEC/DART 공개 재무 경로는 유지한다. 다른 PR 병합·force push·ruleset·
`AUTONOMY_MODE` 변경은 금지한다.
