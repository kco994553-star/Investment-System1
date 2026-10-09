# 개인 전용 무료 주가 경로 조사·설계

조회일: **2026-10-09 UTC**. 사용자 결정은 **무료 + 사용자 본인만 사용**이며 유료 계약·공개 재배포는 하지 않는다.
이 문서는 조사·후속 설계만 다룬다. 가입·키/계정 접근·실제 가격/시트 조회·Worker/OAuth 설정·구현·재점수를 실행하지 않았다.
현재 계정 플랜·개인 이용 분류·적용 계약은 사용자가 확인할 사항이다.
변경 근거는 [26E GSQ-006](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md#gsq-006--26e-무료본인-전용-가격-경로-조사-결정-2026-10-09-utc)에 append-only 기록한다.

## 결정과 A~F 판정

주가 원자료와 **가격 기반 파생값(V=Valuation·시총 순위·가격을 포함한 QGV 등)**은 공개 저장소·Pages·Actions 로그/산출물에 저장·게시하지 않는다.
SEC·DART의 공개 재무 자료는 기존 공개 입력 경로를 유지한다. 공개 재무 fact에 가격을 결합한 결과는 개인 경로로만 취급한다.
공개 종목군의 Frozen 구성은 유지하되 현재 Top 500/V/QGV를 완성했다고 표시하지 않는다.
기존 공개물에 있는 가격 기반 값까지 새 원칙을 충족했는지는 별도 구현 감사 대상이며 이 문서가 공개물 삭제·비공개 전환을 대신하지 않는다.

### 현재 공개 경로에 남은 차단 과제

저장소 읽기 전용 점검에서 아래 **필드의 포함·non-null 여부만** 확인했다. 가격·점수의 값은 출력하지 않았다.

| 현재 경로 | 새 원칙과의 gap |
| --- | --- |
| `reports/gate_evidence/official_snapshot_2024-*.json` | tracked Frozen 원문에 `cutoff_mcap`, `members[].mcap/rank`가 있다. |
| `reports/v_coverage_us17_2026-09-23.json`, `reports/official_v11_book_snapshots.json` | 가격 기반 V 결과/후보 필드가 있다. 기본 Pages QGV가 실제 V를 연결한다는 확인은 아니다. |
| `data/raw/tiingo_run_1790379027.json`, `reports/gate_evidence/nport_reported_prices_2024-06-30.json` | tracked 원문에 가격 필드가 있다. 이 문서에서 삭제/재출판하지 않았다. |
| [Pages 빌더](../../tools/build_pages_cockpit.py), [공개 bundle](../../src/investment_system/product/web_mvp.py) | 시총 금액은 제거하지만 `market_cap_rank`/Frozen `rank`는 공개 projection에 남긴다. |
| [기존 Actions](../../../.github/workflows/c21-real-data.yml), [가격 도구](../../tools/nport_reported_prices.py) | 원문·gate evidence artifact/자동 커밋·가격 stdout 경로가 있어 후속 감사가 필요하다. 현재 외부 배포/과거 로그의 실제 내용은 조사하지 않았다. |

기존 [artifact guard](../../tools/pages_artifact_guard.py)의 PASS는 새 가격/V/순위 금지 규칙의 PASS와 다르다.
공개 Frozen **구성** 유지와 가격 기반 금액/순위 제거는 별개의 요구다. 보호된 이력·evidence를 문서 작업에서 지우거나 gate를 우회하지 않는다.

| 항목 | 종합 판정 | 조건·불가한 변형 |
| --- | --- | --- |
| A 본인 키 → 본인 전용 중계 → 휴대폰 | **조건부** | Worker 서버 fetch·Secret·본인 인증은 기술적 후보. 공급자 약관의 private relay 허용, 실제 앱 인증/CORS 확인이 필요하다. 공개 프록시·다른 사용자 접근은 불가. |
| B 연 기업 1개 과거 일봉 무저장 차트 | **조건부** | Tiingo 무료 한도 내 요청·휘발성 처리. 원시 차트의 표시 권리와 실제 계정 조건 확인 필요. 무저장만으로 허용을 확정하지 않는다. |
| C 하루 1회 개인 V·순위 | **조건부 / 일부 불가** | F에 따라 본인 Sheet 현재값을 1순위로 검토하고 기기에서만 계산·표시. 정확한 EOD·500개 완전성·가공 권리와 Tiingo 사용 변형의 비복원 파생 조건이 남는다. Tiingo 500개 즉시 조회와 Starter 원문/파생 영구 저장은 불가. |
| D 무료 중계·Secret·접근 제한 | **조건부** | Cloudflare Free cap, 본인 1명 인증, 로그/캐시 비보존, CPU·모바일 로그인 실측 필요. Paid/유료 저장/도메인 구매를 비용 0 설계에 넣지 않는다. |
| E 도쿄 8035·한미 042700 | **가능: 현행 유지** | 기존 본인 Google 시트·수동 입력 유지. Tokyo Electron은 기존 확인처럼 수동 입력을 유지하며 Sheet 지원을 확정하지 않는다. OTC/ADR/다른 상장으로 자동 치환하지 않는다. |
| F 본인 GOOGLEFINANCE 500행 리더보드 | **조건부: 1순위 후보** | Sheets 1 batch read 예산은 충분한 후보. 500행 성공 SLA·#N/A 실측·정확한 종가·개인 가공의 명시 허용은 미확인. Tiingo는 차트 전용, 대체는 Alpha Vantage 최근 최대 100개 거래 관측. |

**최신 F가 초기 C의 Tiingo 종목군 수집안보다 우선한다.** 리더보드 500 현재값과 과거 차트를 분리한다.
무료 조건/허용이 충족되지 않으면 해당 기능은 NOT_AVAILABLE이며 유료 업그레이드나 다른 출처 대량 조회로 우회하지 않는다.

## A. 두 입력 경로와 개인 경계

| 경로 | 제안 데이터 흐름 | 보존 경계 |
| --- | --- | --- |
| 기업 차트 | 본인 앱 → 본인 인증 Worker → 본인 Tiingo 키로 선택 기업 일봉 → 본인 앱 RAM 차트 | 처리 RAM만 사용. 응답·화면 작업 종료 시 제거. 차트 닫기/표시 끄기 때 가격 참조 제거. 가격 archive·로컬 DB·원문 로그 없음. |
| 리더보드 | 본인 기기 기존 Google 읽기 전용 로그인 → 본인 비공개 Sheet 500행 batch read → 공개 SEC/DART 재무 입력과 기기 RAM에서 결합 → 개인 V/순위 표시 | 기존 짧은 수명 Sheets token과 시세 응답은 기기 메모리만. 가격·가격 결합 QGV·V·시총 순위를 공개 경로로 돌려보내지 않는다. |

두 번째 경로는 **사용자가 하루 한 번 로그인/읽기를 시작하는 방식**을 우선 검토한다.
기존 메모리 전용 token으로 무인 일일 실행이 가능하다고 가정하지 않는다. offline refresh 권한·server token 저장·Cron을 자동 추가하지 않는다.
Worker에서 순위까지 계산하는 대안은 별도 권한·CPU·입력 전달 검증 대상이다. 첫 후보에서는 Sheets token을 Worker 신원 증명으로 보내지 않는다.
회사/거래소·허용된 endpoint·기간·응답 크기·호출 수를 제한하며 임의 URL을 받아 전달하는 범용 프록시를 만들지 않는다.
공개 앱 코드/재무 JSON에는 키·시세·개인 결과를 넣지 않는다. 앱 응답을 GitHub에 업로드하거나 Actions에서 가격을 대신 조회하는 방식은 제외한다.

## B. Tiingo 무료 과거 일봉과 표시 권리

[현재 Starter 가격표](https://www.tiingo.com/pricing)는 **$0, 월 500 unique symbols, 시간 50회, 일 1,000회, 월 1GB**를 표시한다.
이것을 현재 사용자 계정의 확인 결과로 쓰지 않는다. [Connecting](https://www.tiingo.com/documentation/general/connecting)은 서버용 REST와 Authorization Token 인증을 문서화한다.
[Developer Program](https://www.tiingo.com/documentation/appendix/developers)은 “Each user must have their own API token.”이라고 요구한다.
자기 키 모델에 부합할 근거가 있지만 본인 인증 Worker를 통한 단일 사용자 중계를 명시적으로 승인한 문구는 확인하지 못했다.
Worker 로그인을 Tiingo 가입/로그인 대행으로 만들거나 Tiingo 비밀번호를 앱에서 받지 않는다.

[공개 TOS](https://app.tiingo.com/tos/) 표시 변경일은 2026-10-06이다. 기존 이용자에게 게시·통지 후 30일 적용 조항이 있어 실제 계정 적용 시점은 미확인이다.
§1의 “personal or internal business purposes”에도 Starter의 별도 조건이 적용된다.
§1.6(a)의 “only transiently in volatile memory”는 원문과 **파생 결과** 모두에 적용되고, 본인을 대신해 운영되는 서비스도 포함한다.
작업에 필요한 동안만 RAM/비영구 임시 처리 후 즉시 제거하며 늦어도 작업·세션 종료 전에 지운다.
Worker Cache API·KV/D1/R2·로그·큐·백업·앱 IndexedDB/localStorage·service worker cache를 가격/파생 결과 저장소로 쓰지 않는다.

§1.6(c)는 비대체·비복원 “rankings, scores”를 잠재적 허용 예시로 들고, 원본을 드러내는 “dashboards, charts”를 제한 예시에 포함한다.
이를 모든 개인 일시 차트의 확정 금지로 단정하지 않지만, 구체적인 raw 차트 표시와 적용 계약의 정합성이 확인되지 않아 **B는 조건부**다.
원가격을 버리는 것만으로 V의 보존·복원 가능성이나 차트 표시 권리가 해결되지는 않는다.

자체 예산 후보는 **차트 40회/시간 + 오류·재시도 여유 10회**, 일 한도·월 대역폭·월 종목 합집합을 함께 관리하는 것이다.
동일 종목의 새로고침도 요청 수/대역폭을 사용한다. 1개 차트씩 요청하고 무제한 polling/동시 열기를 제한한다.
500행 리더보드를 Tiingo로 자동 수집하지 않는다. 월 unique는 watchlist 크기가 아닌 같은 Tiingo 계정에서 실제 조회한 모든 symbol의 월간 합집합으로 관리하며, 다른 개인 사용·중계의 요청도 계정 한도에 포함한다.
월중 새 회사·상장 변경·종목 대체도 unique 합집합에 포함되며 한도를 넘으면 다음 허용 구간까지 조회를 중단한다. 키 추가 발급으로 우회하지 않는다.

Tiingo의 브라우저 CORS는 [이전 직접 조회 조사](TIINGO_DEVICE_DIRECT_RESEARCH.md)에서 익명 OPTIONS 허용 헤더가 관측되지 않았다.
Worker→Tiingo 서버 요청은 그 브라우저 preflight와 다른 경로지만 **앱→Worker/Access** 인증·CORS의 성공까지 증명하지는 않는다.

## C. 개인 V·순위, EOD와 500심볼

V는 거래량(volume)이 아닌 **QGV Valuation**이다. 시총 순위는 주가 크기 순위가 아니다.
현재가만 있으면 시총을 만들 수 없고, 검증한 동일 통화의 market cap 또는 같은 주식 종류의 shares·시각/basis가 필요하다.
재무 가용 시각·통화·단위·정정 vintage와 가격시각을 대조하며 기존 투자 방법론/가중치/점수 수식을 이 문서에서 바꾸지 않는다.
공개 재무 자료는 계속 공개로 받을 수 있으나 가격을 결합한 V·순위·QGV 결과는 본인 화면 RAM에서만 표시하는 후보다.
원가격·P/E·시총·복원이 가능한 비율을 결과에 함께 붙여 비복원 점수라고 주장하지 않는다. 어떤 V 출력이 원가격을 복원할 수 있는지는 알고리즘별 검증 대상이다.
Tiingo Starter를 사용하는 변형에서는 하루 결과를 KV/파일에 남기는 것도 파생 영구 저장 제한에 맞지 않는다.
Google/Alpha 자료의 보존·가공 권리는 Tiingo 조건으로 대신 판정하지 않는다.

F의 GOOGLEFINANCE 현재값은 지연·종목별 비동기 갱신을 포함하므로 **정확한 일일 EOD snapshot과 동일하지 않다**.
하루 한 번 읽었다는 사실만으로 EOD, 현재 Top 500, 완전한 일일 V/QGV를 표시하지 않는다.
종가/완료 세션·타임존·전체 종목 시각 정합성이 확인되지 않으면 `PERSONAL_DELAYED_CURRENT_INPUT`, EOD/전체 순위는 UNKNOWN이다.
가격을 보존하지 않는 설계는 완전한 가격 PIT replay·과거 점수 재현을 제공하지 않는다. 공개 재무 receipt를 가격 보존 증거로 쓰지 않는다.

초기 C의 Tiingo EOD안은 다음 예산으로 비교하되 **최신 설계에서 채택하지 않는다**.

| 종목군안 | 무료 예산과 한계 |
| --- | --- |
| 미국 17종목 | 종목당 요청 1회라면 17회. 같은 시간 3회 전체 새로고침은 51회로 50/hour 초과. 다른 차트·retry도 포함한다. |
| 고정 500종목 | 500 unique가 월 허용량 전체를 쓰므로 종목군 밖 차트 여유가 없다. 요청 500회는 50/hour의 10개 시간 구간 예산을 사용하며 한 번에 처리 불가. 장시간 취득은 같은 시각의 전체 EOD라는 증거가 아니다. |
| 축소·순서안 | 별도 선택이 필요하다면 공개 TARGET 미국17→사용자가 정한 subset→나머지 순서, 40/hour 같은 여유 예산과 월 고정 allowlist를 제안한다. 조회하지 않은 회사는 NOT_AVAILABLE이며 subset 순위를 Top 500처럼 표시하지 않는다. 순서 변경은 권리·월 unique 문제를 해결하지 않는다. |

## D. Cloudflare 무료 중계·인증·Secret

[Workers Free 한도](https://developers.cloudflare.com/workers/platform/limits/)는 계정 합산 **100,000 요청/일(UTC 자정 reset)**,
HTTP/Cron **CPU 10 ms**, isolate 메모리 **128MB**, 외부 subrequest **50/호출**, 동시에 응답 헤더를 기다리는 외부 연결 **6/호출**, Cron **5/account**다.
네트워크 대기는 CPU와 다르지만 JWT·JSON·500행 계산이 10ms에 들어오는지는 실측 전 미확인이다. 무료 범위에서 실패하면 미제공 상태로 끝낸다.
Free 일 한도 초과 1027, CPU/메모리 초과 1102를 성공 응답으로 처리하지 않는다. route의 **fail closed**를 택해 인증 Worker 우회를 막는다.

[가격 문서](https://developers.cloudflare.com/workers/platform/pricing/)의 Workers Paid는 최소 $5/월이므로 선택하지 않는다.
Workers egress/bandwidth 별도 요금 없음은 다른 제품의 무료 보장이 아니다. 유료 add-on·저장·로그·Containers를 붙이지 않는다.
[workers.dev](https://developers.cloudflare.com/workers/configuration/routing/workers-dev/)로 도메인 구매 없이 개인용 URL을 검토한다.
custom domain 등록/갱신 비용까지 0이라고 가정하지 않는다. 기본 URL과 preview/version URL은 본인 인증 없이는 제공하지 않는다.

| 보안·운영 항목 | 제안 조건 |
| --- | --- |
| 본인만 접근 | [Google IdP](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/google/) + Access의 정확한 본인 계정 Allow·Google 인증 Require. Everyone/도메인 전체/Bypass 금지. Google 로그인 성공만으로 어느 사용자든 허용하지 않는다. |
| Worker 검증 | [Workers Access](https://developers.cloudflare.com/workers/configuration/cloudflare-access/)의 직접 인증 invocation에서 검증된 `ctx.access` identity를 확인한다. 미인증 undefined는 거부. Static Assets 내부 router/Service Binding으로 identity가 전파된다고 가정하지 않는다. 헤더 존재·Origin allowlist는 인증이 아니다. |
| ID token 대안 | [Google 서버 검증](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token)의 서명·issuer·audience·expiry·본인 `sub` 검증. 기존 Sheets readonly access token을 그대로 신원 증명으로 신뢰하지 않는다. |
| Secret | [Secret binding](https://developers.cloudflare.com/workers/configuration/secrets/)에 본인 Tiingo/Alpha 키를 보관한다. plaintext vars·소스·클라이언트 bundle·URL·환경 dump·예외 로그 금지. GitHub Actions의 기존 키를 가격 작업에 활성화하지 않는다. |
| 무저장 | 서버 fetch `cache: no-store`, 응답 `Cache-Control: private, no-store` 방향. 원문/파생물 Cache API·파일·DB·외부 분석·백업 금지. no-store만으로 공급자/플랫폼 내부의 모든 보존이 0이라고 증명하지 않는다. |
| 로그 | [새 Worker observability 기본 enabled](https://developers.cloudflare.com/workers/observability/logs/workers-logs/)이므로 배포 전에 Workers Logs/observability·invocation 로그 수집을 명시적으로 비활성화하고 body/custom 로그가 없음을 확인한다. 가격·V·순위·Secret·Authorization·응답/실제 키 URL을 어떤 로그에도 넣지 않는다. Access 로그인 운영 메타데이터까지 플랫폼 보존 0이라고 주장하지 않는다. |
| 앱 CORS | [Access CORS](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/cors/)의 인증 cookie·preflight 조건을 휴대폰에서 확인한다. 서버 fetch가 가능하다는 이유로 모바일→Access CORS까지 통과했다고 표시하지 않는다. |
| 한도 관리 | isolate RAM counter와 [Rate Limiting binding](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/)은 전역 정확한 월 unique/시간 예산 장부가 아니다. 공급자 한도·여유 예산·허용 symbol·중단을 적용한다. 전역 보장이 필요하면 가격 없는 count/reset-time/승인 symbol 집합만 private 직렬화하는 별도 무료 저장안을 검증한다. |

Access는 [2026 공식 안내](https://blog.cloudflare.com/adaptive-access-user-risk-scoring/)에 50명까지 무료 근거가 있으나 현재 가입 화면의 좌석/플랜은 사용자가 재확인한다.
이 설계는 본인 1명만 허용한다. [Zero Trust setup](https://developers.cloudflare.com/cloudflare-one/setup/)은
“If you chose the Zero Trust Free plan, this step is still needed but you will not be charged.”라고 하며 **Free도 payment details 입력이 필요**하다.
이것을 Workers Free 자체의 동일 가입 조건으로 혼동하지 않는다. 결제정보 등록을 원치 않으면 ID token 직접 검증 대안도 조건부로 남긴다.
계정·프로젝트의 Free 선택, 다른 구독 없음, cap 초과 중단, 주기적 가격/한도 확인이 비용 0 유지 조건이다. 미래의 요금제 변경까지 무료를 보장하지 않는다.
[Cloudflare Developer Platform 약관 §4](https://www.cloudflare.com/service-specific-terms-developer-platform/)는 해당 문서와 제3자 약관 준수를 요구한다.
Cloudflare 중계 기능이 Tiingo/Google/Alpha의 데이터 권리를 대신하지 않는다.

## E. 한국·일본 현행 경로

한미반도체 **KRX 042700**, Tokyo Electron **TSE 8035**는 기존 본인 Google 시트·수동 입력을 유지한다.
확인되지 않는 GOOGLEFINANCE 종목은 manual 상태이며 다른 거래소/OTC 심볼로 바꾸지 않는다.
이 경로의 현재가 지원을 과거 일봉 지원으로 확장하지 않는다. Tiingo의 미국 데이터 문서를 19종목 전체 커버리지 근거로 쓰지 않는다.
기존 사용자 시트·수동 입력의 저장 기능을 이번 조사 PR에서 변경하지 않는다.
그 개인 저장의 허용 범위는 각 출처 약관과 별도 검토하며, 새 Tiingo 데이터에 기존 저장 기능을 자동 적용하지 않는다.

## F. GOOGLEFINANCE 500행과 차트 대체 규칙

[GOOGLEFINANCE 문서](https://support.google.com/docs/answer/3093281?hl=en)는 current `price` 최대 20분 지연,
`tradetime`·`datadelay`·`currency`와 거래소:심볼 식별을 안내한다. [계산 설정](https://support.google.com/docs/answer/58515?hl=en)도 외부 자료 지연을 안내한다.
읽기/재계산 설정을 바꾸면 정확한 최신 종가가 확보된다고 가정하지 않는다.
날짜를 지정한 **역사 GOOGLEFINANCE**는 Sheets API/Apps Script에서 #N/A 제한이 있다. 이것을 현재값 전체의 API 금지나 과거 일봉 대체 허가로 해석하지 않는다.

[Sheets API 기본 read 한도](https://developers.google.com/workspace/sheets/api/limits)는 **300회/분/project, 60회/분/user/project**이며
분당 한도 내 별도 일일 요청 상한은 없다. payload 2MB 이하 권장, 처리 timeout 180초다.
[values.batchGet](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/batchGet) 1회로 500행의 고정 범위를 읽는 후보는 **정상 1 read/일**이다.
예를 들어 최초 1회+bounded retry 최대 2회=3 reads/일을 자체 예산으로 둔다. 함수 500개의 재계산은 Sheets read quota와 다른 문제다.
현재 standard use 추가 비용 없음 안내에 **2026년 후반 초과쿼터 과금 계획**도 있으므로 무료/과금 상태를 실행 전 확인하고 quota 초과 경로는 쓰지 않는다.
기존 [readonly scope](https://developers.google.com/workspace/sheets/api/scopes)와 [token model](https://developers.google.com/identity/oauth2/web/guides/use-token-model)을 유지한다.
scope 자체가 한 탭만 읽도록 제한하는 권한은 아니므로 사용자 Sheet ID·범위를 앱에서 고정하고 토큰은 기기 메모리만 사용한다.

**500행 안정성·#N/A 비율은 아직 실측하지 않았다.** 공식 500행 전부 성공 SLA·고정 갱신 주기·확정 GOOGLEFINANCE 함수 한도는 확인되지 않았다.
기존 19종목 실측을 500행 검증으로 확대하지 않는다. 후속 사용자가 할 평가는 다음과 같다.

- 승인된 Frozen 500 기대집합과 거래소/종목을 고정한다. 현재가·currency·tradetime·datadelay, 필요한 market cap/주식수 근거를 구분한다.
- 기기에서 하루 한 번 유효/500·fresh/500·#N/A/500·누락/500·시각 미확인/500와 거래시각 분포·HTTP 지연을 휘발성으로 집계한다. 가격·순위·응답을 파일/로그로 남기지 않는다.
- [빈 끝행/열 생략](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values)을 기대집합에 대조해 결측으로 센다. 중복·알 수 없는 종목·비숫자·0 이하 가격·통화/basis 불일치를 구분한다.
- read_at을 price_as_of로 바꾸지 않는다. Sheet timezone이 미확인이면 시각 UNKNOWN, 휴장/주말에는 최근 완료 session 기준을 따로 적용한다.
- 필수 한 행이라도 부족하면 완전한 500종목 순위는 UNKNOWN이다. 유효 499행만 새 분모로 삼아 Top 500을 선언하지 않는다. 짧은 표본 성공도 SLA/장중 안정성 증명이 아니다.

[Finance 면책](https://www.google.com/googlefinance/disclaimer/)은 정보용·정확성/가용성 비보장과 저장·가공·전송·재배포 등에 대한 사전 동의 조건을 둔다.
[Google API 약관 §5](https://developers.google.com/terms)도 API 접근권이 제3자 콘텐츠 권리를 대신하지 않음을 설명한다.
**개인 기기의 500종목 V/순위 가공까지 명시적으로 허용됐다는 근거는 확인하지 못했다.** 본인 시트와 무저장 설계만으로 이를 해소했다고 표시하지 않는다.

| 용도·상태 | 출처 선택/대체 | 출처 표시 |
| --- | --- | --- |
| 개인 리더보드 현재값 | 본인 GOOGLEFINANCE Sheet 1순위. 실패하면 해당 행/전체 순위 NOT_AVAILABLE/UNKNOWN. **Tiingo/Alpha로 500행 자동 대체하지 않는다.** | GOOGLEFINANCE·본인 비공개 시트·개인 일일 읽기·최대 20분 지연 안내·정보용, 원 trade 시각/미확인·read 시각·Frozen 구성 기준일. |
| 미국 기업 과거 차트 | Tiingo 1순위, 조건/한도 실패 시 **Alpha Vantage compact** 조건 확인 후 대체. 같은 종목·주식 종류·거래소·통화 검증. | provider·symbol/exchange·daily·raw/adjusted basis·마지막 session·실제 관측 수·취득 시각. |
| Alpha 대체 | [TIME_SERIES_DAILY compact](https://www.alphavantage.co/documentation/#daily): 무료의 **최근 최대 100 data points**, 달력 100일이 아닌 거래 관측이다. raw/as-traded OHLCV. 차트 전체 시리즈를 교체하고 Tiingo 조정값과 이어붙이지 않는다. | Alpha Vantage·비조정 일봉·최근 최대 100개 관측. IPO/중단/결측이면 실제 개수 표시, 누락을 0/전일값/다른 공급자 가격으로 채우지 않는다. |
| Alpha 한도/권리 | [공식 FAQ](https://www.alphavantage.co/support/) **25 requests/day**. 자체 예산 20회+여유5 같은 후보, 모든 retry 포함. full/adjusted는 premium이므로 제외. | 현재 계정·symbol 지원은 미검증. 무료 일봉을 현재 실시간 가격으로 표시하지 않는다. |
| 한국·일본 현재값 | 기존 본인 시트/수동 유지. 과거 차트는 지원 미확인으로 남긴다. | Google 시트 또는 수동, 정확한 KRX042700/TSE8035·통화·입력/가격 시각·basis/미확인. |

[Alpha Vantage TOS §2·3](https://www.alphavantage.co/terms_of_service/)는 개인·비상업, 비양도/재허여불가 조건을 둔다.
금융업 고용/제휴 등은 commercial 분류에 포함될 수 있어 사용자 확인이 필요하다. 개인 Worker 중계와 상세 보존 기간의 명시 허용은 미확인이다.
따라서 Alpha도 본인 키·본인 인증·무저장 차트로만 조건부 검토한다. [조정 일봉](https://www.alphavantage.co/documentation/#dailyadj), full 및 [실시간/지연 데이터](https://www.alphavantage.co/realtime_data_policy/) 유료 경로로 전환하지 않는다.

## 사용자가 해야 할 일과 구현 전 확인

1. 본인 개인 이용 분류·현재 Tiingo 플랜/적용 약관·잔여 unique/요청/대역폭을 확인한다. 본인 전용 relay·raw 차트·V/순위 가공 권리가 불명확하면 공급자에 직접 확인하고 허용 전 실행하지 않는다. 유료 계약은 선택하지 않는다.
2. 본인 비공개 Google Sheet의 500개 매핑·지원 속성·시각/통화, 기존 readonly 로그인, 프로젝트 실제 quota/과금 상태를 확인한다. 500행 실측은 기기 휘발성 집계로만 하고 Google 개인 가공 조건을 확인한다.
3. 중계 선택 시 Cloudflare Free 계정·2FA, workers.dev, 필요 시 Zero Trust Free/payment onboarding·Google IdP를 준비한다. 본인 1명 allowlist와 대체 ID-token 검증 방식을 결정한다. 이번 조사에서 가입/설정하지 않았다.
4. 본인 Tiingo 키와 선택한 Alpha 무료 키를 사용자 소유 Worker Secret으로만 등록한다. 키를 채팅/코드/로그/PR에 붙이지 않는다. 현재 GitHub 키 존재는 새 개인 중계 사용 승인이나 등록 결과가 아니다.
5. 후속 구현에서 미인증·다른 Google 계정·preview URL 우회·CORS·quota/CPU 초과·로그/캐시 비보존을 확인한다. 무료 cap에서 종료하고 유료 플랜을 활성화하지 않는다.
6. 기존 공개 저장소/Pages/Actions 산출물의 가격·V·시총 순위 노출을 별도 구현 감사한다. 문서의 원칙 기록과 기존 guard PASS만으로 새 금지 경계 준수 완료를 선언하지 않는다.

모든 숫자·권리 판정은 공식 공개 문서 조회에 근거하며 실제 사용자 계정·500행 안정성·휴대폰 경로 성공은 미확인이다.
**추천은 F의 본인 Sheet 일일 읽기와 B의 조건 확인된 차트 중계를 분리하는 최소 개인 경로**다.
이 PR의 병합은 공급자 채택·키 발급·중계 배포·가격 수집·QGV 계산 실행 승인이 아니다.
