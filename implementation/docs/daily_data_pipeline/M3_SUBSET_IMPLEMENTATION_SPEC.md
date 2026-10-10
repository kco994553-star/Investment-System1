# GSQ-013 M3 TARGET19 + 기기 ★ + 비공개 Universe 상위 N — 코덱1 구현 명세

작성/갱신: **2026-10-10 UTC**. 갱신 기준 canonical `72c80e8c4252d5e6dd6a23ad044e57255e206aa8`(#99). 현재 상태 진입점: [CURRENT_HANDOFF.md](../../../CURRENT_HANDOFF.md). 운영: [WORKING_RULES.md](../../../WORKING_RULES.md). 최신 채택: [26E GSQ-013](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md). GSQ-012의 기기 ★ 입력을 유지하고, 대형주 추가를 사용자 비공개 Universe 시트의 검증된 상위 N 경로로 구체화한다. GSQ-011의 약100개·수동 대형주 seed 제안은 적용하지 않는다. 기준 설계: [개인 M3](M3_PRIVATE_UNIVERSE_DESIGN.md).

**Goal:** **TARGET19 + 사용자 기기의 ★ 관심 기업 + 비공개 Universe 시트의 검증된 시총 상위 N**을 개인 작업 목록으로 구성하고 SEC 주식 수·기기 Sheet 가격/필요한 본인 Worker 가격을 검증해 기기 RAM에서 기존 `shares×price` 순위를 계산한다. 실제 ★ 목록은 기기에서 읽고 Universe는 기존 읽기 전용 로그인으로 1회 읽는다. 시트 ID·실제 목록·가격·시총·순위는 저장소에 기록하거나 제출받지 않는다.
**Architecture:** 기기 `prefs.interests` snapshot + TARGET identity + 기존 GIS session의 Universe 1회 GET → 기기의 SEC shares/price·marketcap 품질 비교 → 검증 행의 상위 N → 세 출처 합집합 manifest → 개인 RAM 순위. Worker는 필요한 SEC 공개 재무/기존 개인 가격만 relay하며 시트 ID·시트 payload·선정 목록을 전달받지 않는다.
**Stack:** 기존 vanilla JS/Node test runner/Worker ES modules. 첫 PR은 pure input/계산 계약, 둘째 PR은 본인 인증 relay·기기 연결로 분리한다. 아래 code write-set은 **후속 구현 제안**이며 이번 작업은 .md만 변경한다.

1차 규모는 TARGET19∪기기 ★∪검증된 Universe 상위 N이며 고정100개 목표/최소 표본이 없다. N은 사용자 설정이고 **기본 N/품질 임계값 제안은 §2A에서 사용자 확인 대기**다. 시총 계산 부하·권리 확인 조건을 유지하며 Sheets 읽기 권한을 데이터의 정확성·재배포 권리로 해석하지 않는다. 전체500과 Official/P02 중간 시점 정책도 후속이다. 새 투자 방법론·가중치·FX 변환·share-class/ADR 보정·QGV 점수식을 만들지 않는다. Yahoo 비공식 자동 조회의 **무허가 부적합** 판정과 공급자 허가 미확인은 GSQ-007대로 유지한다. 본인용·무저장·Free가 공급자 허가를 대신하지 않는다.

## 1. 코드 PR 분할과 파일/함수

| PR | 후속 write-set | 구현 책임 |
| --- | --- | --- |
| A 순수 부분집합 경계 | 신규 `implementation/src/investment_system/product/private_subset_core.js` | UMD export `PrivateSubset`; 아래 기기 관심·Universe parser/품질 비교/상위 N/roster/SEC shares/price/candidate/rank/controller 함수. 실제 HTTP·DOM mount·저장 없이 injected inputs만 처리. 자동 public asset copy 대상인 `web_assets` 밖에 둠 |
| A | 신규 `implementation/tools/private_subset_node_test.js` | 합성 Node 계약 테스트 §7 A |
| A | 신규 `implementation/tests/test_private_subset_mcap_contract.py` | 합성 JS 결과와 기존 Python mcap ordering/report 계약의 비교. 저장/provider/runner import 없음 |
| A | 신규 `implementation/docs/daily_data_pipeline/M3_SUBSET_VERIFICATION.md` | 실제 명령·결과·미완료와 synthetic-only 검증 기록 |
| B 본인 relay | 신규 `implementation/worker/src/private-subset.js`; 제한 수정 `implementation/worker/src/index.js`, `implementation/worker/tests/worker.test.mjs` | 고정 SEC request plan·선택 목록과 독립된 source mapping validator·M3 query/response validator. 기존 authenticate/admit/release 및 exact Origin/Free 경계 아래 dispatch |
| B 기기 연결 | 제한 수정 `implementation/src/investment_system/product/web_assets/google-sheet-quotes.js`, `app.js`, `index.html`; 신규 같은 폴더 `private-subset-view.js` | session closure 안에 `fetchSubset`; `app.js::leaderboard`의 별도 개인 패널·`renderRoute` mount/dispose; 기존 prefs의 ★ snapshot, 별도 Universe 설정과 기존 session의 1회 read 전달·변경 시 작업 취소; token 외부 export 금지, foreground controller/view·취소/로그아웃 정리 |
| B static code packaging | 제한 수정 `implementation/src/investment_system/product/web_mvp.py::build`, `implementation/tools/pages_artifact_guard.py` 및 해당 합성 privacy/browser 검사 | 검토된 core JS를 `private-subset.js`라는 static code asset로 복사·script 로드·새 code asset hash pin. private manifest/가격/결과는 builder에 전달하지 않음. 기존 public data pin/허용 조건을 완화하지 않음 |

B의 asset/guard 변경은 **static code 추가에 한정한 별도 owner 검토 범위**다. 현재 builder는 `web_assets` 파일을 자동 복사하고 public guard는 asset hash/목록을 고정하므로 A를 그 폴더에 추가하면 곧바로 public artifact가 달라진다. A는 위 별도 core 파일을 Node에서 직접 읽어 이 문제를 피한다. B는 private 결과를 `D.leaderboard`/producer/공개 JSON으로 넣거나 실제 가격 파일·Frozen/공개 membership·워크플로를 바꾸지 않는다. 코드 PR에는 합성 fixture만 넣고 실제 관심 목록·가격·순위·토큰·개인 Worker 설정을 넣지 않는다. code/mixed PR은 자체 병합 대상이 아니며 review/승인·병합 대기로 인계한다.

## 2. 대상 구성 규칙

1. **TARGET19 필수 seed:** 기존 [device actual identity catalog](../../src/investment_system/product/device_actual_catalog.py)의 pin된 TARGET/identity hash를 확인하고 identity 필드만 읽는다. 비중을 변경·복사하거나 보유 목록으로 해석하지 않는다. 현재 [private-history mapping](../../src/investment_system/product/web_assets/private-history.js)의 company_id→심볼은 아래와 같다.

| TARGET company_id | 공급자 심볼·통화 |
| --- | --- |
| asml, lrcx, klac, nvda, amd, avgo, qcom, intc | ASML, LRCX, KLAC, NVDA, AMD, AVGO, QCOM, INTC · USD |
| msft, googl, amzn, rtx, stry, etn, hubb, gev, rok | MSFT, GOOGL, AMZN, RTX, **SYK**, ETN, HUBB, GEV, ROK · USD |
| hanmi | **042700.KS · KRW** |
| tokyo_electron | **8035.T · JPY** |

2. **기기 ★ snapshot:** 기존 [app.js](../../src/investment_system/product/web_assets/app.js)의 `load/validatePrefs/star`가 관리하는 `prefs.interests` company_id 배열을 사용한다. 관심 기업·즐겨찾기는 같은 목록이며 Groups/holdings/가격 순위는 선택 출처가 아니다. 사용자가 foreground 계산을 시작할 때 UI가 `{version: prefs.version, interestIds: [...prefs.interests], storageStatus, synthetic:false}`만 순수 경계에 전달한다. `storageStatus`는 기존 load/validation의 `corruptStorage`가 true이면 UNREADABLE, 정상 기기 목록이면 OK이며 단순 save 실패로 이미 알려진 RAM 목록을 지우지 않는다. 모듈은 localStorage를 별도로 읽거나 prefs/groups를 수정하지 않는다. 빈 정상 ★ 목록이면 TARGET19만으로 선택을 완료하며 누락된 수동 seed를 요구하지 않는다. 손상/읽기 실패는 빈 정상 목록으로 취급하지 않고 `DEVICE_INTERESTS_UNREADABLE`과 선택 미확인을 표시한다. 알 수 없는 ID/모호한 listing은 missing에 남기고 public catalog 순서·시총·대형주로 채우지 않는다.
3. **동일 listing dedup:** `listing_id`로 TARGET/DEVICE_INTEREST/UNIVERSE_TOP_N 출처 tags를 합친다. 같은 symbol의 다른 issuer/security를 합치지 않는다. CIK/issuer 관계·상장기간·심볼 변경·MIC·통화·provider symbol·share class를 대조한다. 동일 issuer의 여러 class/listing은 가격을 자동 합산하지 않고 기존 CA-UNIT/issuer-wide basis의 검증 receipt가 없으면 ranking 후보에서 차단한다.
4. **SEC 후보 lookup:** `https://www.sec.gov/files/company_tickers.json`의 `cik_str/ticker/title`를 identity lookup용으로 사용한다. 필요 시 `company_tickers_exchange.json`의 `fields/data`로 거래소 후보를 보조 확인한다. current catalog는 dated membership·거래소 적격성·security type·share-class·ADR ratio·전체 pool 완전성을 보장하지 않는다. 이름 유사도·티커 접미사·해외 OTC로 자동 resolve하지 않는다. canonical 기존 SEC source 경로와 [공식 API 설명](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)을 따른다. 두 catalog의 이번 실제 응답/현재 schema/범위는 미실측이며 위 schema는 후속 validator target이다.
5. **비공개 manifest:** ★ 선택의 원본은 기기 prefs이며 파생 manifest는 작업 RAM에만 둔다. 실제 관심 ID/목록을 Git/PR/문서/fixture/Pages/공개 JSON/Worker config·KV·D1·R2에 복사하지 않는다. Worker의 source mapping/grant는 공개 identity와 허용 출처를 검증하는 설정이며 ★ 여부나 선택 roster를 저장하지 않는다. 요청한 한 listing의 identity/job/manifest hash만 처리하고 인증된 기기 입력만으로 source grant를 늘리지 않는다. 기존19개 `/history` allowlist는 그대로다. 새 M3 경로의 추가 mapping은 권리·identity 검증을 통과해야 하며 미설정 관심 기업도 roster/missing에 남긴다. Universe 실제 code 목록·순서·선정 membership도 공개하거나 Worker roster로 저장하지 않는다.

TARGET 한국/일본2개는 roster에 유지한다. **SEC는 두 본상장의 주식 수 보완 출처가 아니다.** 미국 ADR/OTC·다른 회사 CIK로 대체하지 않는다. ASML NASDAQ ADR도 ordinary shares와 가격단위의 관계를 확인해야 한다. 1차의 SEC-only shares로 검증되지 않는 대상은 `SHARES_NOT_AVAILABLE`/`BASIS_UNCONFIRMED`; DART/EDINET·사용자 확인 보완의 별도 승인/근거가 필요하다. USD/KRW/JPY를 숫자만 비교한 전체 순위는 만들지 않는다.

## 2A. 비공개 Universe 1회 읽기·품질 비교·상위 N

### 입력과 기존 로그인 경계

사용자 보고(2026-10-10): 비공개 시트 이름/탭 **Universe**, A=`code`, B=`marketcap`, C=`price`, GOOGLEFINANCE, 후보504개=사용자가 설명한 현재 S&P500 구성+ASML. **503/504 값 있음·PSKY 빈칸**, BLK·BNY의 marketcap이 실제보다 수십~수백 배 작다는 오류 보고다. 이번에는 시트를 읽거나 값을 검증하지 않았으며 ‘값 있음’은 각 B/C 필드의 별도 검증 성공을 뜻하지 않는다. 504개/구성 설명은 사용자 제공 metadata이고 공식/완전/dated membership 증거가 아니다.

- Sheet ID/URL은 기기 설정에서만 입력/보관하며 백업/export에서 제외한다. 실제 ID를 Git/PR/문서/로그/telemetry/Worker에 넣지 않는다. 기존 Quotes 설정 ID/range를 덮어쓰지 않고 별도 Universe source 설정을 사용한다.
- 기존 `GoogleSheetQuotes.createSession/sessionFor`의 readonly scope+email·메모리 token을 재사용한다. token getter/새 OAuth scope·Sheets 쓰기·Apps Script/공개 CSV proxy는 없다. 기존 `sheetsURL`의 `valueRenderOption=UNFORMATTED_VALUE`, `dateTimeRenderOption=SERIAL_NUMBER`를 유지한다.
- 사용자가 foreground 작업을 시작할 때 **`fetchValues(deviceId, "'Universe'!A1:C1025", {signal, maxBytes:1048576})` 한 번** 호출한다. 1024 data rows/1MiB는 투자 범위가 아닌 parser/resource 방어 상한이다. 504개가 바뀌었다고 가짜 행을 추가하거나 무조건 실패시키지 않되 row limit 도달/범위 밖 가능성은 `ROW_LIMIT_REACHED`로 남기고 완전성 확인으로 처리하지 않는다. 범위/byte 상한 확장은 별도 검토하며 자동 추가 read는 없다.
- 후속 PR B는 기존 `createSession.fetchValues(id, range)`에 **optional** signal/bounded reader만 추가한다. Universe options에서는 redirect=error와 response 1MiB stream cap을 적용한다. 기존 두 인자 호출은 유지하고 기존 Quotes importer/저장 동작을 바꾸지 않는다. Universe module은 `GoogleSheetCore.parseValues`/`importQuotes`로 보내지 않는다. 기존 importer의 A=code,B=price,C=tradetime과 Universe의 B=marketcap,C=price는 다르다.
- GET/정상 body 취득 시각을 `acquired_at`으로 기록한다. C에는 trade time/currency가 없으므로 aware trade timestamp·RAW_CLOSE·정확 EOD·PIT를 만들지 않는다. GOOGLEFINANCE의 지연 가능한 **현재 참고 가격**이며 available_at은 취득 상한이다. body를 받으면 job/session epoch를 재확인한다. OFF/만료/401/취소는 실패이며 자동 로그인·재시도·polling 없이 그 작업을 끝낸다.

### 정규화와 재계산

`parseUniverseValues`는 A/B/C 위치를 고정한다. 첫 행이 정확한 code/marketcap/price header(case-insensitive)면 한 번만 제외하며 header가 없으면 첫 행도 data다. 완전 빈 trailing row만 제외한다. code가 있는데 B/C가 빈 행·`#N/A/#VALUE!/#REF!`·boolean·NaN/Infinity·비양수·자리수 불명 문자열은 missing/quality reason으로 남긴다. UNFORMATTED_VALUE 숫자를 우선하며 명시 숫자 문법 외에 통화기호/단위(M/B)/locale 추정으로 값의 배율을 고치지 않는다. price 결측은 R 재계산 불가이며 PSKY도 row별 실제 결측을 그대로 표시한다.

code는 `NASDAQ:...`/`NYSE:...` 또는 공급된 명시 mapping의 단일 심볼을 정규화한다. SEC ticker/CIK·MIC·currency·security/class·ADR 단위와 대조하며 `BRK.B→BRK-B` 같은 punctuation 변환도 승인된 identity mapping 없이는 만들지 않는다. 동일 listing의 동일 row는 dedup, 상충 row는 해당 listing 실패다. 여러 listing/class가 같은 issuer이면 자동 합산/중복 상위 후보를 만들지 않고 기존 issuer/CA-UNIT 근거가 필요하다. Sheet C와 B의 금액 단위가 같은 **검증된 USD**인지 확인한다. currency 없는 값을 USD로 자동 지정하지 않으며 확인 불가 행은 NOT_VERIFIABLE이다.

각 Universe row에서 기존 SEC shares selector의 `dei:EntityCommonStockSharesOutstanding` 우선/eligible 없을 때만 us-gaap fallback·shares 단위·CIK/accn/측정일/취득/가용 시각을 검증한다. **R = 검증된 SEC 발행주식 수 × 같은 row의 C price**다. price를 별도 Yahoo 값으로 바꿔 G와 비교하지 않는다. 최신 취득된 발행주식 수는 filing 기준이며 current outstanding/가격과 동시라는 증거가 아니므로 날짜·basis·revision/currentness 제한을 표시한다. issuer-wide shares와 class/ADR 가격 단위가 불일치하거나 근거가 없으면 비교 전에 BASIS_UNCONFIRMED다.

B의 Google 시총을 G라 하면 **relative_difference = abs(G-R)/R**다. R>0·finite여야 하며 denominator를 G로 바꾸거나 임의 rounding/clip/scale 교정을 하지 않는다. 동일한 shares×price 수식을 **모든 검증 가능한 행의 정렬키 R**로 사용한다(기존 mcap 계약 유지). G는 비교 원자료로 보존한다. 임계 이상이면 R 사용+**‘검증 불일치’**를 명시하고 G/검증/사용 출처를 구분한다. 임계 미만도 정렬은 R이며 ‘비교 범위 내’로 표시한다. G 결측/불량이고 R을 검증할 수 있으면 R을 사용하되 GOOGLE_MCAP_MISSING/INVALID를 표시한다. SEC/price/basis가 미확인이면 G만으로 검증 완료/상위 후보를 만들지 않는다.

### 사용자 확인 대상 제안과 범위 표시

| 설정 | 제안 | 근거·제한 | runtime gate |
| --- | --- | --- | --- |
| 기본 N | **20**; 사용자가 integer 1..시트의 dedup code 행 수로 설정 | TARGET19와 비슷한 추가 표시 규모로 기기 결과/render 부하를 처음 관찰하기 위한 운영 기본 제안. 투자 가중치/최적표본/상위20 방법론이 아니다. N이 작아도 전체 후보 검증 비용은 그대로다. | `selectionConfig.confirmed=false`면 CONFIG_CONFIRMATION_REQUIRED; 자동 적용하지 않음 |
| 상대오차 임계 | **10% (0.10), 경계 포함 ≥** | 보고된 10배/100배 축소는 이 정의에서 약90%/99% 오차로 탐지된다. 10%는 반올림·서로 다른 shares 갱신 시점의 작은 차이를 별도로 볼 수 있는 초기 검토값이며 실측 분포/보편 허용오차로 검증된 값이 아니다. 단위/ADR 오류·old filing을 임계값으로 승인하지 않는다. | `qualityConfig.confirmed=false`면 비교 label/상위 N 확정은 CONFIG_CONFIRMATION_REQUIRED; 합성 테스트에만 제안값 사용 |

임계는 **데이터 품질 표시**, N은 **선택/부하 설정**이고 QGV/투자 점수·가중치·새 factor가 아니다. 임계값으로 R 수식이나 basis 검증을 바꾸지 않는다. 확인이 끝나도 실측 값을 매개변수로 튜닝하거나 Holdout/v2를 사용하지 않는다.

G/price/basis/share 미확인의 진단은 각각 보존한다. tolerance는 positive finite, N은 integer 범위 검증이며 threshold 경계에서 round하지 않는다. 원 가격의 배율/환산·새 confidence 점수를 만들지 않는다.

모든 시트 code 후보를 검사한 뒤 R 내림차순·동률 canonical ASCII company_id 오름차순으로 **검증된 행 중 상위 N**을 기기에서 선택한다. 낮게 나온 G 때문에 원래 후보가 제외될 수 있으므로 G 상위 N/상위 몇 배만 SEC 검증하는 shortcut은 금지한다. 미검증/결측/issuer ambiguity/row limit가 있으면 `selection_status=PARTIAL`, scope=VERIFIED_UNIVERSE_ROWS, requested_n/selected_n와 row/verified/missing counts를 표시한다. PSKY 같은 missing이 있을 때도 ‘504개 전체의 확정 상위 N’이라 표시하지 않는다. 선택 가능 행이 N보다 적으면 실제 수만 선택하고 채우지 않는다. 전체 실패/미확인 설정이면 Universe 추가0·NOT_AVAILABLE, TARGET/★는 별도 상태로 보존한다.

이 선택 ID를 TARGET19/★와 합친다. overlap은 listing별 한 번만 계산하고 origin tags를 합친다. **Universe 선정이 PARTIAL/UNCONFIRMED이면 최종 manifest/result도 그 상태를 보존한다.** final rank는 검증된 USD 행의 개인 참고 부분순위이며 미국 전체500/공식 구성·현재 QGV 재점수를 뜻하지 않는다.

## 3. source request와 Worker 경계(PR B)

| source | 고정 upstream | 반환/처리 경계 |
| --- | --- | --- |
| Universe 현재 참고값 | `GET https://sheets.googleapis.com/v4/spreadsheets/<device-only-id>/values/<encoded Universe range>` | 기존 `createSession.fetchValues`, readonly scope·email 유지. §2A 전용 parser 사용, 토큰 getter/Sheet ID Worker 전달 없음 |
| SEC identity | 위 `company_tickers.json` (optional exchange catalog는 별도 명시 선택) | 가격 없는 public metadata지만 관심 목록을 결합한 작업 결과는 개인 RAM에 유지. whole-US pool 채택으로 해석 안 함 |
| SEC shares facts | `https://data.sec.gov/api/xbrl/companyfacts/CIK<10digits>.json` | 독립 source mapping과 일치하는 CIK만 허용. `dei:EntityCommonStockSharesOutstanding`, 대체 `us-gaap:CommonStockSharesOutstanding`, units=`shares` 검사 |
| SEC accession metadata | `https://data.sec.gov/submissions/CIK<10digits>.json` | CIK·accession/form/filingDate/acceptanceDateTime 결속. recent에 없는 accession은 실패; files 자동 전이/전체 archive crawl은 1차 제외 |
| 개인 가격 | 기존 고정 Yahoo chart host, `interval=1d`, range=`1mo`; 검증된 source mapping의 provider symbol만 | 비공식 source label·RAW_CLOSE·원 bar 시각/read_at/session status/basis를 보존. actual 권리·session/basis 확인 전 활성화하지 않음 |

SEC의 data.sec.gov는 **CORS 미지원**이다. 브라우저 직접 fetch가 가능하다고 설계하지 않는다. B는 본인 Worker relay를 추가하는 후속 구현이며 기존 Worker에 SEC proxy가 이미 있는 것은 아니다. SEC는 연락 가능한 runtime User-Agent와 총10req/sec 이하 정책을 요구한다. 값/연락정보는 private 설정이며 문서/코드에 실값을 넣지 않는다. 원 endpoint를 URL parameter로 받아 public proxy가 되는 경로는 없다.

B의 route contract:

- `GET /m3/sec-catalog?job_id=<opaque>`: 고정 기본 company_tickers 하나만.
- `GET /m3/sec?listing_id=<opaque>&kind=companyfacts|submissions&job_id=<opaque>`: 기기 listing_id와 승인된 source mapping을 대조한 뒤 고정 CIK URL 하나만.
- `GET /m3/history?listing_id=<opaque>&job_id=<opaque>`: 기기 listing_id와 승인된 source mapping을 대조한 뒤 fixed `range=1mo`의 Yahoo 요청 하나만. response는 legacy `/history`와 구별된 `private-subset-source/1` envelope로 input hash·job/listing/company·body/read_at를 결속한다.

추가 query·중복 query·임의 host/url·CIK/symbol/통화 override·fragment·비정상 encoding을 거부한다. opaque ID는 nonempty ASCII `[A-Za-z0-9_-]`와 허용된 source mapping 값으로 검증하고 job ID도 같은 안전 문자·최대128자다. source 요청은 header `X-M3-Input-Hash`(lowercase SHA-256 64자리)와 `X-M3-Input-Version`(동일 안전 문자·최대128자)로 기기 작업을 결속한다. M3 preflight의 허용 header는 기존 `Authorization`과 위 두 작업 header만이며 순서/대소문자는 집합으로 검사한다. catalog에는 Authorization만 허용하는 경우도 처리한다. legacy `/history`의 기존 preflight 계약은 유지한다. catalog 요청만 아직 roster를 resolve하는 단계라 두 header가 없을 수 있으며 catalog envelope의 input_hash는 이 경우 null이다. Worker는 전체 ★ 목록/manifest를 요구·보관하거나 전체 목록을 검증했다고 주장하지 않는다. source 권한 검증은 header hash와 독립적이다. listing_id/hash/version 불량은 거부하고 mapping 미설정은 `SOURCE_MAPPING_NOT_CONFIGURED`, 권리/feature grant 미확인은 `SOURCE_NOT_CLEARED`다. 옵션으로 raw source body를 정상화해도 token·authorization·개인 config를 응답에 echo하지 않는다.

성공 envelope의 공통 필드는 `schema="private-subset-source/1"`, `kind=sec_catalog/companyfacts/submissions/history`, `job_id`, `input_hash`, `listing_id`, `company_id`, `acquired_at`, `synthetic=false`다. catalog만 listing/company가 null이다. SEC 응답에는 `body_base64`와 원 bytes의 `response_sha256`를 넣고 기기에서 decoded byte limit·digest를 대조한다. facts/submissions의 두 acquisition 중 늦은 시각을 SecReceipt.acquired_at로 사용하며 두 원 receipt도 작업 RAM에 유지한다. history에는 원 JSON dump 대신 검증된 `PriceReceipt` 후보를 `data`에 넣고 미확인 finality/basis를 그대로 남긴다. 전체 envelope의 identity/job/input_hash와 data 안의 값이 다르면 실패다. 최종 manifest hash는 Worker가 echo하는 source receipt와 구분하고 기기 candidate/result에서 결속한다. upstream 취득이 끝난 실제 시각만 acquired_at로 기록한다. 실패 envelope는 고정 reason만 반환하며 raw upstream body/요청 query를 반환하지 않는다.

기존 `createHandler`의 **exact Origin, authenticate(request,env), tokeninfo aud/email/email_verified/expiry, admit/release lease**를 모든 M3 GET에 적용한다. 기기 hash echo를 source 사용 권한으로 해석하지 않는다. OPTIONS는 실제 GET grant가 아니며 기존 방식으로 preflight만 처리한다. M3 dispatch는 authenticate/admit 전 source fetch를 못 한다. 권한 없는 요청에서 manifest/CIK/관심 목록이 노출되지 않게 한다. `google-sheet-quotes.js`의 session 내부 `fetchSubset(origin, path, options)`가 Bearer를 본인 Worker에만 붙이고 공급자에는 전달하지 않는다. 외부 module에 token getter·공개 일반 URL fetch를 export하지 않는다.

운영 제한은 투자 방법론/표본 기준이 아니다. 가격은 기존 **512KiB/1500bar** 경계를 유지하고 SEC body는 bounded **8MiB**까지만 reader로 제한한다(초과 `SOURCE_TOO_LARGE`). 한 요청·한 upstream source, 동시1·기존 전체 owner5초 간격/분당 최대12회 admission·lease·timeout·abort를 공유한다. **현재 source에는 일일 admission 구현이 없다**. 플랫폼 Free quota와 별도 일일 budget의 실제 확인은 후속 운영 의존성이며 이미 구현됐다고 주장하지 않는다. catalog/facts/가격을 한 요청에서 선택 목록 전체로 확장하는 batch는 없다. Free CPU/메모리·payload·폰 latency 실측 전 실제 연결을 완료로 보고하지 않으며 한도 확장·유료 전환/카드 등록·proxy/key 회전으로 우회하지 않는다.

**504개 전체 검증의 부하:** sheet read1 + SEC catalog1 + cold facts/submissions 최대2×U + 시트 밖 TARGET/★의 필요한 가격 P다. U=504 가정이면 Worker source 약1009개, 5초 간격만 약84분이며 tokeninfo/retry/CPU·기존 사용은 별도다. 기존 token 상한1시간과 충돌하므로 단일 cold 작업 완료를 약속하지 않는다. N을20으로 줄여도 전체 후보 검증 비용은 줄지 않는다.

선행 SEC **비가격** receipt를 supplied catalogue/cache로 재사용할 수 있게 PR B에 `loadPublicSecReceipt(cik)`/`validatePublicSecReceipt` 경계를 둔다. 이는 권한/Free 검토 후의 구현 의존성이다. cache는 SEC 원 출처의 CIK·concept·shares·accn·단위·측정/취득/가용 시각·source hash만 whitelist로 허용하며 price/marketcap·sheet ID/row/code 목록·★·manifest/job/hash·선정/rank는 저장하지 않는다. cached available_at를 새 read 시각으로 다시 만들지 않고 lineage/currentness를 검사한다. source grant/사실 검증을 기기 업로드로 우회하지 않는다. 실제 Free CPU/읽기·쓰기 한도·cache 준비 coverage 실측 없이 운영 연결을 완료로 보고하지 않는다.

준비되지 않은 cold 작업은 `VALIDATION_INCOMPLETE`/`BUDGET_NOT_READY`로 남긴다. session 만료/취소에서 시트/가격/선택 RAM을 폐기하며 자동 재로그인·시트 재읽기·batch 무한 확장은 없다. 사용자가 새 foreground 작업을 명시하면 그 작업에서 새 시트를1회 읽는다. 비가격 SEC receipt 재사용이 모든504 행의 최신/동시 shares를 증명하는 것은 아니다.

## 4. 기기 순수 함수와 sidecar 타입(PR A)

아래 JS object는 공유 production schema를 바꾸지 않는 private sidecar다. 시각은 명시 ISO aware 문자열이며 validation 후 epoch 비교한다. 불명 시각/통화/identity를 현재시간/USD로 채우지 않는다.

| 타입 | 필수 필드 |
| --- | --- |
| `ListingSeed` | `listing_id, company_id, issuer_id, security_id, symbol, mic, currency, timezone, provider_symbol`; `cik: 10digits|null`; `origin_tags: TARGET/DEVICE_INTEREST/UNIVERSE_TOP_N[]`; `valid_from, valid_to|null`; `identity_evidence_ref`; `synthetic: boolean` |
| `DeviceInterestSnapshot` | `source="DEVICE_STAR"`, `prefs_version=1`, `interest_ids: string[]`, `storage_status=OK/UNREADABLE`, `state=AVAILABLE/NOT_AVAILABLE`, `reason_codes[]`, `synthetic`; copied/deduped ID snapshot, Groups/holdings 없음 |
| `SubsetManifest` | `schema="private-subset-manifest/1"`, `version`, `manifest_hash`, `input_hash`, `interest_snapshot: DeviceInterestSnapshot`, `universe_selection: UniverseSelection`, `listings: ListingSeed[]`, `unresolved_interest_ids: string[]`, `selection_status=COMPLETE/PARTIAL/UNCONFIRMED`, `synthetic` |
| `UniverseReceipt` | `source="GOOGLEFINANCE_PRIVATE_UNIVERSE"`, `acquired_at`, `content_sha256`, `job_id`, `session_epoch`, `synthetic`; Sheet ID/URL/token 필드 없음 |
| `UniverseParseResult` | `state=INPUT_RESEARCH/NOT_AVAILABLE`, `receipt`, `rows: UniverseRow[]`, `row_count`, `missing[]`, `reason_codes[]`, `row_limit_reached`, `synthetic`; usable price 행과 전체 후보 count를 구분 |
| `UniverseRow` | `row_index`, `code`, `listing_id/company_id|null`, `google_mcap:number|null`, `sheet_price:number|null`, `currency/basis_status`, `reason_codes[]`, receipt ref; RAM-only |
| `CapCheck` | row identity, `state=VERIFIED/NOT_AVAILABLE`, `recomputed_cap:number|null`, `google_mcap:number|null`, `relative_difference:number|null`, `effective_cap=R|null`, `quality=WITHIN_TOLERANCE/MISMATCH/GOOGLE_MCAP_MISSING/GOOGLE_MCAP_INVALID/UNCONFIRMED`, `reason_codes[]`, shares/price lineage refs |
| `UniverseSelection` | `source="PRIVATE_UNIVERSE_VERIFIED_TOP_N"`, `scope="VERIFIED_UNIVERSE_ROWS"`, `state=PERSONAL_REFERENCE/NOT_AVAILABLE`, `selection_status=COMPLETE/PARTIAL/UNCONFIRMED`, `content_sha256`, `requested_n/selected_n`, `row_count/verified_count/missing_count`, `selected_listing_ids[]`, `missing[]`, `synthetic` |
| `SecReceipt` | `cik`, `companyfacts_body: Uint8Array`, `submissions_body: Uint8Array`, `acquired_at`, `facts_sha256`, `submissions_sha256`, `synthetic` (payload log/외부 serialize 금지) |
| `ShareBasisReceipt` | `listing_id,company_id,security_id`, `basis_status=SINGLE_CLASS_CONFIRMED/CA_UNIT_APPROVED/UNKNOWN`; `source_evidence_ref`, `source_sha256`, `available_at`; `share_unit="shares"`, `price_basis=RAW_CLOSE/GOOGLEFINANCE_CURRENT`, `currency`, `synthetic` |
| `SharesInput` | `state=INPUT_RESEARCH/NOT_AVAILABLE`, `company_id,listing_id`, `shares:number|null`, `shares_available_at`, `measurement_date`, `accn`, `concept`, `basis_status`, `reason_codes[]`, `historical_first_publication=false` |
| `PriceReceipt` | `job_id,input_hash,listing_id,company_id,provider_symbol,currency,timezone`, `price:number|null`, `basis="RAW_CLOSE"`, `bar_timestamp`, `price_observed_at`, `available_at`, `read_at`, `session`, `session_status`, `finality_evidence_ref|null`, `basis_evidence_ref|null`, `synthetic` |
| `SessionEvidence` | `listing_id,session`, `bar_start_at`, `close_at`, `available_at`, `finality_status=CONFIRMED/UNKNOWN`, `basis_status=CONFIRMED/UNKNOWN`, `source_evidence_ref`, `source_sha256`, `synthetic` |
| `SubsetResult` | `schema="private-subset-result/1"`, `state=PERSONAL_REFERENCE/NOT_AVAILABLE`, `scope="SUPPORTED_USD_ROWS"`, `official=false`, `candidate_pool_complete=false`; `job_id,manifest_hash,as_of`, `selection_status=COMPLETE/PARTIAL/UNCONFIRMED`, `configured_count,ranked_count,missing_count`, `rows[]`, `missing[]`, `full_configured_rank_status=UNKNOWN`, `pit_status=OBSERVED_BOUND_ONLY/NOT_VERIFIED`, `model_status=NOT_PROMOTED` |

Sheet PriceInput은 `price_kind=GOOGLEFINANCE_CURRENT`, available/observed=receipt.acquired_at(취득 시각), `trade_time=null`, `exact_eod=false`, basis/통화/identity/shares 단위 근거를 가진다. 기존 Worker PriceReceipt의 RAW_CLOSE/session/finality 계약과 별도 branch로 검증하며 sheet price를 확정 일봉으로 변환하지 않는다. quality/selection config는 각각 `{relative_tolerance,confirmed}`와 `{n,confirmed}`이며 불명/불량/미확인 설정을 자동 기본값으로 채우지 않는다.

manifest hash는 canonical JSON(version + 정렬된 DEVICE_STAR snapshot/unresolved IDs + Universe content hash/N/검증된 선택 identity + listing identity/allowlist/source/evidence 필드)의 SHA-256이다. hash 자체도 선택 목록의 공개를 허가하지 않는다. 가격·rank·holdings·token을 포함하지 않는다. A는 WebCrypto digest를 주입할 수 있게 하며 실제 private manifest를 공개 fixture에 넣지 않는다. SharesInput·결과 행·payload는 private RAM에만 유지한다. `configured_count`는 TARGET company_id∪정상 ★ ID∪Universe의 검증된 상위 N의 중복 제거 개수이며 unresolved ★ ID도 missing/count에 포함한다. Universe 선택에서 제외된 원 후보의 missing/count는 UniverseSelection에 별도로 보존하고 final configured count와 혼동하지 않는다. 읽기 불능 ★의 전체 개수는 알 수 없으므로 TARGET/Universe의 알려진 합집합 count만 표시하고 selection_status=UNCONFIRMED를 함께 보존한다.

```text
readDeviceInterestSnapshot({version, interestIds, storageStatus, synthetic}) -> DeviceInterestSnapshot
parseUniverseValues(values, receipt, {identityLookup, digest}) -> Promise<UniverseParseResult>
prepareUniversePrice(row, basisReceipt, {asOf}) -> PriceInput
compareUniverseMarketCap(row, sharesInput, priceInput, qualityConfig) -> CapCheck
selectVerifiedUniverseTopN(checks, selectionConfig) -> UniverseSelection
buildSubsetManifest(targetSeeds, interestSnapshot, universeSelection, {identityLookup, asOf, digest}) -> Promise<ManifestResult>
parseSecCatalog(payload, {acquiredAt, synthetic}) -> CatalogResult
prepareSecShares(listing, secReceipt, basisReceipt, {asOf, digest}) -> Promise<SharesInput>
prepareWorkerPrice(listing, envelope, sessionEvidence, {jobId, inputHash, asOf}) -> PriceInput
prepareSubsetCandidates(manifest, sharesByListing, pricesByListing, {asOf}) -> CandidateResult
rankSupportedUsdSubset(candidateResult, {jobId, manifestHash, asOf}) -> SubsetResult
createSubsetJobController({fetchUniverseOnce, fetchSource, clock}) -> {start({targetSeeds, interestSnapshot, universeSettings, qualityConfig, selectionConfig}), cancel(), clear(), onSessionChanged(), snapshot()}
```

함수 options key는 위 서명을 따르며 기존 private-history API를 변경하지 않는다. 불량 입력은 고정 reason의 result로 반환하고 raw 예외·source payload를 진단에 넣지 않는다. A의 `fetchUniverseOnce`/`fetchSource`는 합성 test stub만 주입한다. read1 counter/abort를 controller에서 관리하고 pure parsers는 HTTP를 실행하지 않는다. clock은 명시 취득/작업 시각을 기록하는 의존성이며 거래시각·누락 timestamp를 만드는 fallback이 아니다.

`prepareSecShares`는 injected async digest로 원 bytes 두 개와 SHA를 대조한 뒤 UTF-8 JSON을 parse한다. bytes가 없거나 digest/JSON/CIK가 다르면 usable shares를 만들지 않는다. `parseSecCatalog`는 supplied JSON metadata만 처리한다. `ManifestResult/CatalogResult/CandidateResult/PriceInput`도 `state`, `reason_codes[]`, 정상 `data` 또는 null을 가지며 불량 입력의 정상 data를 만들지 않는다. CandidateResult는 `selection_status`, `configured_count`, `candidates[]`, `missing[]`를 보존한다. rank 결과도 선택 미확인 상태를 이어받으며 알려진 count를 전체 ★/Universe 목록의 count로 표시하지 않는다. selection_status 우선순위는 UNCONFIRMED > PARTIAL > COMPLETE이며 세 출처 상태를 결합한다. candidate 필드는 기존 helper의 `company_id,ticker,shares,shares_available_at,price,price_observed_at`와 동일하며 private lineage metadata는 sidecar에 둔다.

session/basis receipt에는 실제 source metadata·상장/단위/시간과 내용 hash가 결속돼야 한다. owner 검토가 필요한 외부 증거의 실증을 이 순수 함수가 수행했다고 주장하지 않는다. 단순 status 변경/임의 reference로 검증을 우회하지 않고 미확인 receipt는 실패로 남긴다. first A의 confirmed receipt는 명시 합성 fixture에만 있다.

controller는 source 취득이 끝나면 `clock`의 실제 `completed_at`을 작업 `as_of`로 고정하고 입력별 available_at를 대조한다. 이는 취득을 마친 지식 시점이며 서로 다른 source의 원 가격시각을 동시 시각으로 만들지 않는다. 순수 함수의 asOf는 명시 입력이고 `now()`로 누락 시각을 채우지 않는다. 화면에 작업 완료시각과 원 가격/session 시각·미확인을 분리한다.

## 5. shares·price·후보 검증과 기존 계산

- **SEC shares:** CIK/hash/receipt 취득·submissions accession/form/acceptance를 결속한다. dei cover shares가 우선이며 eligible dei가 없을 때만 기존 us-gaap fallback을 쓴다. units=shares, 양수 finite, cutoff 당시 취득한 filing만 사용한다. 같은 concept의 최신 eligible filing 및 그 안의 최신 measurement end를 선택하고 같은 end의 다른 val은 `MULTI_CLASS_AMBIGUOUS`다. 결측·단위 불일치·미확인 accession을 0/추정값으로 채우지 않는다.
- **가용성:** filed 날짜를 UTC 자정 가용 시각으로 만들지 않는다. 첫 경계는 `shares_available_at=acquired_at`이라는 보수적 관측 상한이며 known acceptance>acquired 또는 acquired>as_of는 실패다. 현재 companyfacts의 과거 행을 이전 as_of에 백필하지 않는다. 기존 M1의 US17 allowlist를 관심 목록에 맞춰 바꾸지 않고 새 private sidecar로 검증한다.
- **basis/기업행위:** SEC companyfacts는 dimension/class 정보가 누락될 수 있다. 값이 하나라도 전체 shares와 선택 listing 가격의 경제적 단위가 같다는 증거는 아니다. ShareBasisReceipt의 identity/content/available_at와 기존 single-class/CA-UNIT 검토 근거를 확인한다. `CONFIRMED` label만으로 승인하지 않는다. ADR 배율·여러 class 합산·과거 CA-UNIT의 미래 split factor를 새로 계산/적용하지 않는다. 근거가 없으면 `BASIS_UNCONFIRMED`다.
- **가격:** Universe/중복 TARGET/★의 sheet 현재 참고값은 §2A의 전용 검증을 사용한다. 시트 밖 TARGET/★의 기존 Worker history는 아래 엄격 계약을 유지한다. listing/company/symbol/currency/timezone/basis/job/hash 정확 일치, 양수 finite, 명시 source 시각/available/read 및 cutoff를 검증한다. daily bar timestamp는 시작 시각일 수 있으며 최초 공개·확정 close 시각과 동일하지 않다. 현재 Worker의 `COMPLETE`는 공급자 추정이다. 명시 session close·finality/basis 근거가 없으면 `FINALITY_UNCONFIRMED`/`BASIS_UNCONFIRMED`다. 진행/unknown, adjusted→raw fallback, 전일/다른 상장 대체는 없다.
- **범위:** USD의 검증된 후보만 기존 mcap 정렬에 전달한다. KRW/JPY를 USD 숫자와 비교하지 않고 `CURRENCY_SCOPE_NOT_SUPPORTED`를 남긴다. 적격 US security가 미확인이면 `IDENTITY_UNCONFIRMED`다. 결측/실패 대상을 configured roster에서 지우지 않고 missing에 유지한다.
- **계산:** 기존 `universe/sources.py::mcap_top_n_snapshot`의 `shares*price`, mcap 내림차순·동률 company_id 오름차순을 재현한다. rank 전에 반올림/normalize/localeCompare를 하지 않는다. company_id는 canonical ASCII ID이며 같은 issuer의 중복 후보는 자동 집계하지 않는다. 양수 finite 입력의 곱이 nonfinite여도 `NONFINITE_MCAP`다. n은 유효 USD 행 수이며 상위100/500으로 자르지 않는다.
- **표시:** rows는 `SUPPORTED_USD_ROWS`의 **개인 참고 부분순위**다. TARGET19∪★∪Universe 상위 N 전원의 완전순위·미국 전체 순위·Official·정확 EOD가 아니다. 유효 행이 있으면 PERSONAL_REFERENCE, 0이면 NOT_AVAILABLE이며 configured_count/missing_count를 표시하고 full_configured_rank_status=UNKNOWN을 유지한다. 전체 후보 완전성 근거가 없어 candidate_pool_complete=false다.
- **QGV:** 첫 구현에 QGV/V 재점수·새 가중치·score 순위를 넣지 않는다. 이후 기존 QGV snapshot을 개인 view에 연결해도 대상 전원의 snapshot·score/coverage·cutoff/PIT/현재성 근거가 별도로 필요하다. 기존 leaderboard는 null/오래된 snapshot을 검증하지 않는다. mcap 성공을 현재 QGV 순위 성공으로 표시하지 않는다.

ShareBasisReceipt/sessionEvidence 검증은 입력 경계다. 실제 증거가 없으면 NOT_AVAILABLE이며 테스트를 통과시키려고 실제 값에 synthetic 표지·가짜 확인 receipt를 붙이지 않는다.

## 6. 작업 수명과 공개 금지

controller는 start에서 unique job ID/session epoch·설정/★ snapshot을 고정하고 Universe를 한 번 읽는다. 그후 canonical(values)의 SHA-256를 UniverseReceipt.content_sha256로 만들고 parser에서 injected digest로 대조한다. input_hash=SHA-256(version+TARGET/★ identity snapshot+Universe content hash+N/품질 설정)로 원 입력을 결속한 뒤 SEC 조회·비교·선택을 수행한다. 최종 manifest hash는 상위 N 결정 후 만들어 candidate/result에 결속한다. 최종 선택 전 SEC 조회에 최종 manifest가 필요하도록 구현하지 않는다. 시트 밖 TARGET/★의 추가 Worker 가격도 같은 input_hash로 결속한다. input hash는 작업 식별이며 source 사용 grant가 아니다. login/session epoch·job·manifest version·listing이 다른 늦은 응답은 버린다. ★ 추가/해제·관심 설정 import·기존 iframe 관심 변경·N/품질 설정/Universe 연결 설정 변경 경로에서 선택 snapshot이 달라지면 작업을 취소·폐기한다. 새 foreground 실행 때만 현재 prefs로 다시 구성하며 자동 가격 fetch를 시작하지 않는다. logout/인증 실패·다른 owner·cancel·clear·pagehide/화면 파기·manifest 변경에서 abort하고 source/Universe raw/checks/selection/shares/prices/candidates/rows/missing의 RAM 참조를 해제한다. 다른 작업 결과를 재사용하지 않는다.

Universe 시트 ID/URL/원 payload·GOOGLEFINANCE 가격/시총·SEC 비교/오차·가격/returns/시총/가격 의존 V·QGV/순위 및 그 순위로 선정한 membership, 실제 interest/선택 manifest를 public Git/Pages/JSON/Actions log/artifact/PR/telemetry로 보내지 않는다. localStorage/IndexedDB/Cache API/KV/D1/R2/file/backup/service-worker cache/log/crash에도 가격/파생값을 저장하지 않는다. Worker module-global price cache는 없다. 허용된 비가격 rate state 저장은 가격 보관의 예외가 아니다.

기존 기기 ★ prefs의 저장/load/import/export 동작은 선택 입력의 기존 기능으로 유지한다. M3는 이를 읽기만 하고 파생 manifest/가격/결과를 prefs·Groups·기존 holdings/Sheets/Worker origin 저장이나 설정 export/backup에 덧붙이지 않는다. 기기 ★ 원본의 기존 로컬 보관과 M3 파생 자료의 RAM-only 경계를 구분한다. 오류는 고정 code/count만 쓰고 입력값·개인 listing/CIK/URI query/token을 echo하지 않는다. response/upstream은 no-store, redirect=error다. 로그가 없다는 사실이 공급자 권리 증명은 아니다.

가격을 유지하지 않아 종료 후 완전 replay·과거 시총 순위·historical PIT/OOS/Calibration을 보장하지 않는다. Holdout/v2를 실행하지 않는다. SEC 공개 자료/metadata 권리를 개인 가격·선택 membership의 공개 권리로 확장하지 않는다.

## 7. 합성 테스트와 리뷰

PR A는 실제 가격/주식 수·개인 관심 목록을 fixture에 넣지 않는다. TARGET19 public identity는 기존 mapping/hash로 대조하고 계산 비교는 `synthetic_a/b/...`와 가상 issuer의 합성값만 쓴다.

| test 이름(A Node) | assertions |
| --- | --- |
| `target19_identity_is_preserved_without_weights_or_holdings` | 19 identity, stry→SYK, KR/JP 본상장, weight/holdings 입력 변경 없음 |
| `device_star_snapshot_union_deduplicates_listing_and_keeps_origin_tags` | 합성 prefs 관심 ID를 copy, TARGET 중복 tag 병합, 같은 listing만 dedup, 빈 정상 ★는 AVAILABLE·TARGET 기본19 유지, 최종 selection_status는 Universe 상태와 결합, 원 prefs 불변 |
| `device_star_unreadable_or_unknown_ids_do_not_select_large_caps` | corrupt storage와 빈 정상 목록 구별, unknown ID missing, Groups/holdings 미사용, SEC 순서/가격/시총으로 보충 없음, LARGE_CAP 입력 거부 |
| `catalog_cik_ticker_and_identity_ambiguity_fail_closed` | paddedCIK/current metadata 한계 유지, ticker reuse/class/issuer mismatch 거부 |
| `manifest_hash_binds_private_identity_and_source_mapping` | 필드 변경→hash 변경, 가격/token/관심 목록 dump 없음, version 충돌 거부 |
| `shares_follow_existing_concept_precedence_and_measurement_selection` | dei 우선·eligible없을 때만GAAP, 최신knownfiling/end, 같은end 다중값 거부 |
| `shares_require_receipt_accession_units_and_acquisition_cutoff` | CIK/accn/unit 결측·future capture/acceptance·filed 자정 backfill 거부 |
| `single_value_shares_do_not_prove_class_or_adr_basis` | basis UNKNOWN/label-only/다른상장 거부, identity/hash/receipt 검증된 경우만 통과 |
| `worker_price_binds_job_listing_currency_basis_and_time` | job/hash/listing/symbol/currency 불일치·nonfinite/null/0/음수 거부, fallback 없음 |
| `estimated_complete_and_bar_start_do_not_prove_finality` | legacyCOMPLETE만으로 실패, 명시session close/evidence 일치, unknown/gap/진행중 거부 |
| `currency_scope_keeps_kr_jp_rows_without_cross_currency_rank` | roster19 유지·KRW/JPY missing, OTC/ADR/FX 자동 대체 없음 |
| `mcap_ranking_matches_existing_formula_and_ascii_tie_order` | shares×price exact, 내림차순/동률ID, n=유효행, 반올림/새weight 없음 |
| `missing_rows_stay_visible_and_full_rank_is_unknown` | 유효행만PERSONAL_REFERENCE, counts/exclusions일치, 전체실패N/A, official/fullpoolfalse |
| `overflow_duplicates_and_mixed_synthetic_do_not_create_rows` | nonfinite곱·duplicate issuer·synthetic 혼합 고정reason 거부 |
| `job_controller_drops_late_response_and_clears_all_ram` | logout/cancel/pagehide/hash/session/★ toggle/import 변경 후late결과 없음, abort·RAM정리 |
| `pure_boundary_has_no_io_mutation_storage_or_diagnostics` | input deepcopy동일, 순수함수 fetch/storage/loggingspy0, stdout/sentinel 노출없음 |

PR A Python test `test_js_subset_mcap_matches_existing_candidate_order`는 기존 `mcap_top_n_snapshot`에 **합성 입력만** 전달해 Node의 같은 fixture company 순서/곱/selected count와 비교한다. shares/price gate에서 미리 제외된 대상은 sidecar 전용 reason이므로 기존 helper의 raw excluded.reason과 동일하다고 주장하지 않는다. 양쪽에 같은 invalid 후보를 전달한 별도 사례에서는 기존 `MISSING_INPUT`, `NOT_AVAILABLE_AT_AS_OF`, `NON_POSITIVE`도 그대로 비교한다. Official constructor/store/historical runner는 호출하지 않는다. candidate_pool_complete=false를 확인한다. Node가 없으면 새 runner/dependency를 임의 설치하지 않고 제한을 기록한다.

PR B 추가 테스트(기존 Worker/Google session harness에 합성 fetch 주입):

- `m3_routes_require_exact_origin_owner_audience_email_and_expiry`: 다른Origin/owner·token 결측/만료/Google 실패에서 sourcecalls0. 인증 전 manifest 목록 노출 없음.
- `m3_routes_bind_device_job_and_use_independent_fixed_source_mapping`: query/encoding/CIK/symbol/URLoverride·미설정 source mapping/불량 작업header 거부, M3 preflight Authorization/작업header 집합 검사. 기기 hash만으로 source grant 불가, ★ 목록/manifest를 Worker config/store에 기록하지 않음. legacyhistory19 allowlist/response 유지.
- `m3_sec_headers_limits_stream_and_redirect_fail_closed`: 합성 SEC 연락User-Agent, Bearer 전달없음, bodylimit/timeout/redirect/HTTPerror 차단.
- `m3_sources_share_existing_owner_admission_and_release`: 기존 history와 동시/5초/daily/lease 공유, 실패/abort도release, rate metadata에 가격/CIK/token 없음.
- `m3_responses_are_private_no_store_and_have_no_credentials`: response/upstream no-store, 관측/오류/log/response에 auth/config sentinel 없음.
- `fetch_subset_keeps_token_inside_existing_session`: tokengetter 없음, approvedOrigin만 호출, logoutepoch/abort·401/403에서 결과 폐기.
- `m3_view_is_foreground_only_and_never_writes_public_or_backup`: 자동poll/시작fetch 없음, 다른 화면/job/★ snapshot과 혼합 없음, 선택 원본 prefs 불변·M3 derived storage/backup/svcworker호출0. public builder에 private manifest/가격/result를 입력하면 privacy guard가 거부함.

Universe 추가 합성 테스트(PR A):

| test 이름 | assertions |
| --- | --- |
| `universe_columns_are_code_marketcap_price_not_quotes_format` | header/no-header·UNFORMATTED 숫자·B/C 위치·bounds, Quotes parser/저장 호출0 |
| `universe_missing_and_error_rows_are_not_zero_or_filled` | 합성 PSKY 결측처럼 price/mcap 각각 missing, errors/boolean/배율 추정·fallback 없음 |
| `universe_identity_currency_class_and_adr_are_required` | CIK/code/MIC/USD/단위 일치, punctuation override·multi-class/ADR unknown 거부 |
| `google_marketcap_is_compared_with_sec_shares_times_same_sheet_price` | R=shares×같은행C, 다른 source price 혼합 없음, G 없이 검증가능하면 R+missing 표시 |
| `quality_threshold_is_relative_to_recomputed_cap_and_inclusive` | 합성 R=100,G=90 경계 mismatch, G=90.01 within; 축소10배/100배 탐지, nonfinite곱/denominator0 거부 |
| `n_and_quality_proposals_require_user_confirmation` | 미확인 N/threshold 적용 없음, 정수/범위·finite tolerance검증, score/weight 불변 |
| `full_pool_validation_precedes_top_n_selection` | 합성 낮은 G의 큰 R 후보가 N 밖에서도 재진입, G prefix 검증 shortcut 없음 |
| `verified_top_n_keeps_partial_coverage_and_target_interest_overlap` | 동률 ASCII·N부족/unknown/rowlimit PARTIAL, tags합집합, TARGET/★ 미손실, fullpool/officialfalse |
| `universe_job_and_settings_changes_drop_late_private_data` | sheet read1, ★/N/threshold/ID설정/session/취소 변경 후late무효, sheet raw/quality/rank RAM 폐기 |

PR B 추가: `universe_reads_existing_readonly_session_once_without_storage`(같은 작업 GET1·readonly scope·private ID/token/URL export없음·OFF/취소0calls·401폐기), `universe_fetch_values_options_preserve_legacy_quotes_calls`(기존2인자 importer회귀·optional abort/1MiB/redirect error), `public_sec_receipt_cache_rejects_all_price_selection_and_sheet_fields`(공개 SEC whitelist만·client upload우회없음·old available유지·cold budget/coverage 미확인). 새 tests는 실제 값이 아닌 합성 입력만 사용한다.

고정 reason: `CONFIG_CONFIRMATION_REQUIRED`, `UNIVERSE_SCHEMA_MISMATCH`, `ROW_LIMIT_REACHED`, `GOOGLE_MCAP_MISSING`, `GOOGLE_MCAP_INVALID`, `VALIDATION_INCOMPLETE`, `BUDGET_NOT_READY`, `INVALID_INPUT`, `DEVICE_INTERESTS_UNREADABLE`, `IDENTITY_UNCONFIRMED`, `MANIFEST_MISMATCH`, `CIK_MISMATCH`, `ACCESSION_UNCONFIRMED`, `SHARES_NOT_AVAILABLE`, `MULTI_CLASS_AMBIGUOUS`, `BASIS_UNCONFIRMED`, `INVALID_TIMESTAMP`, `INVALID_TIME_ORDER`, `AVAILABLE_AFTER_AS_OF`, `PRICE_NOT_AVAILABLE`, `FINALITY_UNCONFIRMED`, `CURRENCY_SCOPE_NOT_SUPPORTED`, `DUPLICATE_ISSUER`, `NONFINITE_MCAP`, `MIXED_SYNTHETIC_INPUT`, `CANCELED`. transport는 기존 auth/rate code 및 `SOURCE_MAPPING_NOT_CONFIGURED`, `SOURCE_NOT_CLEARED`, `SOURCE_TOO_LARGE`, `SEC_UNAVAILABLE`, `SEC_FORMAT_CHANGED`를 쓰며 raw 예외는 숨긴다. 복수 오류는 identity→time→shares→basis→price→currency→product 순서의 첫 code를 검사한다.

후속 구현의 검증 명령(cwd=repo root):

```bash
node --test implementation/tools/private_subset_node_test.js
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=implementation/src python -m pytest -p no:cacheprovider -q implementation/tests/test_private_subset_mcap_contract.py
node --test implementation/worker/tests/worker.test.mjs
node --test implementation/tools/google_sheet_auth_node_test.js
git diff --name-status
git diff --check
```

이번에는 신규 tests/코드를 **구현·실행하지 않았다**. A 완료는 합성 개인 입력·기존 계산·결측·수명 계약이며 B 연결/실데이터/TARGET19∪★∪Universe 상위 N free coverage 완료가 아니다. B에는 권리·Free/private manifest·basis/session 근거·auth/privacy 회귀와 제한된 foreground 확인이 필요하다. workflow/Frozen/public data를 바꾸어 검사 통과를 만들지 않는다. static code asset 변경도 명시된 owner review 범위 안에서만 검증한다.

## 8. 사용자 확인 대상과 후속 의존성

GSQ-013로 1차 선택 출처는 TARGET19 + 기기 ★ + 비공개 Universe 상위 N이다. **관심 목록·시트 ID를 제출받거나 저장소에 기록하지 않는다.** A는 합성 prefs/Sheet/SEC로 검증하고 B는 기존 readonly session을 사용한다. 사용자 확인 대상은 **기본 N=20 제안과 상대오차 임계10% 제안**이며 미확인 제안을 runtime 확정값으로 적용하지 않는다. 실제 source mapping·basis/통화·비가격 SEC 준비 coverage·Free 부하·권리는 연결 의존성으로 남는다.

기존 Holdout은 **UNCONFIRMED로 유지하고 v2 검증 근거로 사용하지 않는다**. 향후 v2 검증은 누적되는 **전진(forward) 데이터**를 사용하며 시작 시점은 v2 착수 시 사용자가 결정한다. 에이전트는 기간을 선택·사용하지 않고, 이번 문서 갱신으로 v2 착수/forward 수집·검증을 실행하지 않는다. 문서 병합 후 대기한다.

근거: [기존 M3 설계](M3_PRIVATE_UNIVERSE_DESIGN.md), [universe/sources.py](../../src/investment_system/universe/sources.py), [SEC M1](../../src/investment_system/providers/sec_m1.py), [listing 계약](../../src/investment_system/contracts/global_universe.py), [Worker](../../worker/src/index.js), [기존 session](../../src/investment_system/product/web_assets/google-sheet-quotes.js), [SEC API/CORS](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [SEC Fair Access](https://www.sec.gov/about/developer-resources). 외부 설명2개는 2026-10-10 HTTP200으로 확인했으며 company catalog/회사 facts/submissions/가격 endpoint는 호출하지 않았다. SEC 직접 경로는 FRED를 사용하지 않는다.
