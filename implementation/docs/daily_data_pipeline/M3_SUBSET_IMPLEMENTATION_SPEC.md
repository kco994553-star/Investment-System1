# GSQ-011 M3 개인 부분집합 — 코덱1 구현 명세

작성: **2026-10-10 UTC**. 읽기 기준 canonical `8d7fcb55728920a4d9d8f39023c1b4d566cd3e13`. 채택: [GSQ-011](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md). 기준 설계: [개인 M3](M3_PRIVATE_UNIVERSE_DESIGN.md).

**Goal:** TARGET19 + 본인이 명시한 관심 기업/대형주 일부의 약100개 계획 범위를 개인 작업 목록으로 구성하고 SEC 주식 수·본인 Worker 가격을 검증해 기기 RAM에서 기존 `shares×price` 순위를 계산한다.
**Architecture:** 본인 입력 seed + 공개 identity metadata → 비공개 listing manifest → 본인 인증 Worker의 고정 SEC/가격 relay → 기기의 identity/shares/가격 검사 → 개인 부분집합 결과. 공개 산출물로 반환하는 edge는 없다.
**Stack:** 기존 vanilla JS/Node test runner/Worker ES modules. 첫 PR은 pure input/계산 계약, 둘째 PR은 본인 인증 relay·기기 연결로 분리한다. 아래 code write-set은 **후속 구현 제안**이며 이번 작업은 .md만 변경한다.

약100개는 계획 규모이며 확정 roster·최소 표본·전 미국 상위100/500이 아니다. 전체500과 Official/P02 중간 시점 정책은 후속이다. 새 투자 방법론·가중치·FX 변환·share-class/ADR 보정·QGV 점수식을 만들지 않는다. Yahoo 비공식 자동 조회의 **무허가 부적합** 판정과 공급자 허가 미확인은 GSQ-007대로 유지한다. 본인용·무저장·Free가 공급자 허가를 대신하지 않는다.

## 1. 코드 PR 분할과 파일/함수

| PR | 후속 write-set | 구현 책임 |
| --- | --- | --- |
| A 순수 부분집합 경계 | 신규 `implementation/src/investment_system/product/private_subset_core.js` | UMD export `PrivateSubset`; 아래 roster/SEC shares/price/candidate/rank/controller 함수. 실제 HTTP·DOM mount·저장 없이 injected inputs만 처리. 자동 public asset copy 대상인 `web_assets` 밖에 둠 |
| A | 신규 `implementation/tools/private_subset_node_test.js` | 합성 Node 계약 테스트 §7 A |
| A | 신규 `implementation/tests/test_private_subset_mcap_contract.py` | 합성 JS 결과와 기존 Python mcap ordering/report 계약의 비교. 저장/provider/runner import 없음 |
| A | 신규 `implementation/docs/daily_data_pipeline/M3_SUBSET_VERIFICATION.md` | 실제 명령·결과·미완료와 synthetic-only 검증 기록 |
| B 본인 relay | 신규 `implementation/worker/src/private-subset.js`; 제한 수정 `implementation/worker/src/index.js`, `implementation/worker/tests/worker.test.mjs` | 고정 SEC request plan·private manifest validator·M3 query/response validator. 기존 authenticate/admit/release 및 exact Origin/Free 경계 아래 dispatch |
| B 기기 연결 | 제한 수정 `implementation/src/investment_system/product/web_assets/google-sheet-quotes.js`, `app.js`, `index.html`; 신규 같은 폴더 `private-subset-view.js` | session closure 안에 `fetchSubset`; `app.js::leaderboard`의 별도 개인 패널·`renderRoute` mount/dispose; token 외부 export 금지, foreground controller/view·취소/로그아웃 정리 |
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

2. **관심 기업/대형주 seed:** 본인이 명시한 listing/issuer 후보를 입력한다. ‘대형주 일부’는 확인된 선택 목록의 origin tag이며 parser가 `SEC 순서 앞81개`, 무작위, 현재 public Frozen 순위, Yahoo 시총 필드, 임의 S&P 목록으로 채우지 않는다. 자동 전체-pool 시총 선정은 이 1차 scope가 아니다. 구체 관심/대형주 목록이 없으면 TARGET19까지만 roster를 만들고 나머지는 `SEED_SELECTION_PENDING`; 100개를 가짜로 채우지 않는다.
3. **동일 listing dedup:** `listing_id`로 TARGET/관심/대형주 출처 tags를 합친다. 같은 symbol의 다른 issuer/security를 합치지 않는다. CIK/issuer 관계·상장기간·심볼 변경·MIC·통화·provider symbol·share class를 대조한다. 동일 issuer의 여러 class/listing은 가격을 자동 합산하지 않고 기존 CA-UNIT/issuer-wide basis의 검증 receipt가 없으면 ranking 후보에서 차단한다.
4. **SEC 후보 lookup:** `https://www.sec.gov/files/company_tickers.json`의 `cik_str/ticker/title`를 identity lookup용으로 사용한다. 필요 시 `company_tickers_exchange.json`의 `fields/data`로 거래소 후보를 보조 확인한다. current catalog는 dated membership·거래소 적격성·security type·share-class·ADR ratio·전체 pool 완전성을 보장하지 않는다. 이름 유사도·티커 접미사·해외 OTC로 자동 resolve하지 않는다. canonical 기존 SEC source 경로와 [공식 API 설명](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)을 따른다. 두 catalog의 이번 실제 응답/현재 schema/범위는 미실측이며 위 schema는 후속 validator target이다.
5. **비공개 manifest:** 관심/선택 정보는 본인 기기 입력과 본인 Worker의 비공개 config에서만 취급한다. typed manifest의 version/hash와 listing별 허용 source mapping을 결속한다. 기기의 요청만으로 Worker allowlist를 늘리지 않는다. 약100개를 위해 기존 19개 `/history` allowlist를 wildcard로 바꾸지 않는다. manifest를 public Git/Pages/설정 JSON에 올리지 않는다.

TARGET 한국/일본2개는 roster에 유지한다. **SEC는 두 본상장의 주식 수 보완 출처가 아니다.** 미국 ADR/OTC·다른 회사 CIK로 대체하지 않는다. ASML NASDAQ ADR도 ordinary shares와 가격단위의 관계를 확인해야 한다. 1차의 SEC-only shares로 검증되지 않는 대상은 `SHARES_NOT_AVAILABLE`/`BASIS_UNCONFIRMED`; DART/EDINET·사용자 확인 보완의 별도 승인/근거가 필요하다. USD/KRW/JPY를 숫자만 비교한 전체 순위는 만들지 않는다.

## 3. source request와 Worker 경계(PR B)

| source | 고정 upstream | 반환/처리 경계 |
| --- | --- | --- |
| SEC identity | 위 `company_tickers.json` (optional exchange catalog는 별도 명시 선택) | 가격 없는 public metadata지만 관심 목록을 결합한 작업 결과는 개인 RAM에 유지. whole-US pool 채택으로 해석 안 함 |
| SEC shares facts | `https://data.sec.gov/api/xbrl/companyfacts/CIK<10digits>.json` | manifest CIK만 허용. `dei:EntityCommonStockSharesOutstanding`, 대체 `us-gaap:CommonStockSharesOutstanding`, units=`shares` 검사 |
| SEC accession metadata | `https://data.sec.gov/submissions/CIK<10digits>.json` | CIK·accession/form/filingDate/acceptanceDateTime 결속. recent에 없는 accession은 실패; files 자동 전이/전체 archive crawl은 1차 제외 |
| 개인 가격 | 기존 고정 Yahoo chart host, `interval=1d`, range=`1mo`; explicit private manifest provider symbol만 | 비공식 source label·RAW_CLOSE·원 bar 시각/read_at/session status/basis를 보존. actual 권리·session/basis 확인 전 활성화하지 않음 |

SEC의 data.sec.gov는 **CORS 미지원**이다. 브라우저 직접 fetch가 가능하다고 설계하지 않는다. B는 본인 Worker relay를 추가하는 후속 구현이며 기존 Worker에 SEC proxy가 이미 있는 것은 아니다. SEC는 연락 가능한 runtime User-Agent와 총10req/sec 이하 정책을 요구한다. 값/연락정보는 private 설정이며 문서/코드에 실값을 넣지 않는다. 원 endpoint를 URL parameter로 받아 public proxy가 되는 경로는 없다.

B의 route contract:

- `GET /m3/sec-catalog?job_id=<opaque>`: 고정 기본 company_tickers 하나만.
- `GET /m3/sec?listing_id=<opaque>&kind=companyfacts|submissions&job_id=<opaque>`: manifest lookup 뒤 고정 CIK URL 하나만.
- `GET /m3/history?listing_id=<opaque>&job_id=<opaque>`: manifest lookup 뒤 fixed `range=1mo`의 Yahoo 요청 하나만. response는 legacy `/history`와 구별된 `private-subset-source/1` envelope로 manifest hash·job/listing/company·body/read_at를 결속한다.

추가 query·중복 query·임의 host/url·CIK/symbol/통화 override·fragment·비정상 encoding을 거부한다. opaque ID는 nonempty ASCII `[A-Za-z0-9_-]`와 허용된 manifest 값으로 검증하고 job ID도 같은 안전 문자·최대128자다. listing_id/hash/version의 충돌은 거부한다. private manifest가 없으면 `CONFIG_UNAVAILABLE`, 권리/feature grant 미확인이면 `SOURCE_NOT_CLEARED`다. 옵션으로 raw source body를 정상화해도 token·authorization·개인 config를 응답에 echo하지 않는다.

성공 envelope의 공통 필드는 `schema="private-subset-source/1"`, `kind=sec_catalog/companyfacts/submissions/history`, `job_id`, `manifest_hash`, `listing_id`, `company_id`, `acquired_at`, `synthetic=false`다. catalog만 listing/company가 null이다. SEC 응답에는 `body_base64`와 원 bytes의 `response_sha256`를 넣고 기기에서 decoded byte limit·digest를 대조한다. facts/submissions의 두 acquisition 중 늦은 시각을 SecReceipt.acquired_at로 사용하며 두 원 receipt도 작업 RAM에 유지한다. history에는 원 JSON dump 대신 검증된 `PriceReceipt` 후보를 `data`에 넣고 미확인 finality/basis를 그대로 남긴다. 전체 envelope의 identity/job/hash와 data 안의 값이 다르면 실패다. upstream 취득이 끝난 실제 시각만 acquired_at로 기록한다. 실패 envelope는 고정 reason만 반환하며 raw upstream body/요청 query를 반환하지 않는다.

기존 `createHandler`의 **exact Origin, authenticate(request,env), tokeninfo aud/email/email_verified/expiry, admit/release lease**를 모든 M3 GET에 적용한다. OPTIONS는 실제 GET grant가 아니며 기존 방식으로 preflight만 처리한다. M3 dispatch는 authenticate/admit 전 source fetch를 못 한다. 권한 없는 요청에서 manifest/CIK/관심 목록이 노출되지 않게 한다. `google-sheet-quotes.js`의 session 내부 `fetchSubset(origin, path, options)`가 Bearer를 본인 Worker에만 붙이고 공급자에는 전달하지 않는다. 외부 module에 token getter·공개 일반 URL fetch를 export하지 않는다.

운영 제한은 투자 방법론/표본 기준이 아니다. 가격은 기존 **512KiB/1500bar** 경계를 유지하고 SEC body는 bounded **8MiB**까지만 reader로 제한한다(초과 `SOURCE_TOO_LARGE`). 한 요청·한 upstream source, 동시1·기존 전체 owner5초 간격/일일 admission·lease·timeout·abort를 공유한다. catalog/facts/가격을 한 요청에서100개 fetch하는 batch는 없다. Free CPU/메모리·payload·폰 latency 실측 전 실제 연결을 완료로 보고하지 않으며 한도 확장·유료 전환/카드 등록·proxy/key 회전으로 우회하지 않는다.

100개의 모두 서로 다른 US issuer라고 가정하면 catalog1+facts100+submissions100+price100=**약301개 source request**이며 tokeninfo 호출·재시도·기존 차트 사용은 별도다. 5초 간격이면 대기만 약25분이다. 이는 budget 예시이며 동시 시세/정확한 EOD/공급자 허용 또는 실제 Free 적합 증명이 아니다. 실제 roster count/중복issuer·기존 shared limit에 따라 달라진다. 결과를 지속 저장해 다음 날 이어 가는 방식은 없다.

## 4. 기기 순수 함수와 sidecar 타입(PR A)

아래 JS object는 공유 production schema를 바꾸지 않는 private sidecar다. 시각은 명시 ISO aware 문자열이며 validation 후 epoch 비교한다. 불명 시각/통화/identity를 현재시간/USD로 채우지 않는다.

| 타입 | 필수 필드 |
| --- | --- |
| `ListingSeed` | `listing_id, company_id, issuer_id, security_id, symbol, mic, currency, timezone, provider_symbol`; `cik: 10digits|null`; `origin_tags: TARGET/INTEREST/LARGE_CAP_MANUAL[]`; `valid_from, valid_to|null`; `identity_evidence_ref`; `synthetic: boolean` |
| `SubsetManifest` | `schema="private-subset-manifest/1"`, `version`, `manifest_hash`, `listings: ListingSeed[]`, `selection_status`, `synthetic` |
| `SecReceipt` | `cik`, `companyfacts_body: Uint8Array`, `submissions_body: Uint8Array`, `acquired_at`, `facts_sha256`, `submissions_sha256`, `synthetic` (payload log/외부 serialize 금지) |
| `ShareBasisReceipt` | `listing_id,company_id,security_id`, `basis_status=SINGLE_CLASS_CONFIRMED/CA_UNIT_APPROVED/UNKNOWN`; `source_evidence_ref`, `source_sha256`, `available_at`; `share_unit="shares"`, `price_basis="RAW_CLOSE"`, `currency`, `synthetic` |
| `SharesInput` | `state=INPUT_RESEARCH/NOT_AVAILABLE`, `company_id,listing_id`, `shares:number|null`, `shares_available_at`, `measurement_date`, `accn`, `concept`, `basis_status`, `reason_codes[]`, `historical_first_publication=false` |
| `PriceReceipt` | `job_id,manifest_hash,listing_id,company_id,provider_symbol,currency,timezone`, `price:number|null`, `basis="RAW_CLOSE"`, `bar_timestamp`, `price_observed_at`, `available_at`, `read_at`, `session`, `session_status`, `finality_evidence_ref|null`, `basis_evidence_ref|null`, `synthetic` |
| `SessionEvidence` | `listing_id,session`, `bar_start_at`, `close_at`, `available_at`, `finality_status=CONFIRMED/UNKNOWN`, `basis_status=CONFIRMED/UNKNOWN`, `source_evidence_ref`, `source_sha256`, `synthetic` |
| `SubsetResult` | `schema="private-subset-result/1"`, `state=PERSONAL_REFERENCE/NOT_AVAILABLE`, `scope="SUPPORTED_USD_ROWS"`, `official=false`, `candidate_pool_complete=false`; `job_id,manifest_hash,as_of`, `configured_count,ranked_count,missing_count`, `rows[]`, `missing[]`, `full_configured_rank_status=UNKNOWN`, `pit_status=OBSERVED_BOUND_ONLY/NOT_VERIFIED`, `model_status=NOT_PROMOTED` |

manifest hash는 canonical JSON(version + listing identity/allowlist/source/evidence 필드)의 SHA-256이다. 가격·rank·holdings·token을 포함하지 않는다. A는 WebCrypto digest를 주입할 수 있게 하며 실제 private manifest를 공개 fixture에 넣지 않는다. SharesInput·결과 행·payload는 private RAM에만 유지한다.

```text
buildSubsetManifest(targetSeeds, interestSeeds, largeCapSeeds, {identityLookup, asOf, digest}) -> Promise<ManifestResult>
parseSecCatalog(payload, {acquiredAt, synthetic}) -> CatalogResult
prepareSecShares(listing, secReceipt, basisReceipt, {asOf, digest}) -> Promise<SharesInput>
prepareWorkerPrice(listing, envelope, sessionEvidence, {jobId, manifestHash, asOf}) -> PriceInput
prepareSubsetCandidates(manifest, sharesByListing, pricesByListing, {asOf}) -> CandidateResult
rankSupportedUsdSubset(candidateResult, {jobId, manifestHash, asOf}) -> SubsetResult
createSubsetJobController({fetchSource, clock}) -> {start(manifest), cancel(), clear(), onSessionChanged(), snapshot()}
```

함수 options key는 위 서명을 따르며 기존 private-history API를 변경하지 않는다. 불량 입력은 고정 reason의 result로 반환하고 raw 예외·source payload를 진단에 넣지 않는다. A의 `fetchSource`는 합성 test stub만 주입한다. clock은 명시 취득/작업 시각을 기록하는 의존성이며 거래시각·누락 timestamp를 만드는 fallback이 아니다.

`prepareSecShares`는 injected async digest로 원 bytes 두 개와 SHA를 대조한 뒤 UTF-8 JSON을 parse한다. bytes가 없거나 digest/JSON/CIK가 다르면 usable shares를 만들지 않는다. `parseSecCatalog`는 supplied JSON metadata만 처리한다. `ManifestResult/CatalogResult/CandidateResult/PriceInput`도 `state`, `reason_codes[]`, 정상 `data` 또는 null을 가지며 불량 입력의 정상 data를 만들지 않는다. CandidateResult는 `configured_count`, `candidates[]`, `missing[]`를 보존한다. candidate 필드는 기존 helper의 `company_id,ticker,shares,shares_available_at,price,price_observed_at`와 동일하며 private lineage metadata는 sidecar에 둔다.

session/basis receipt에는 실제 source metadata·상장/단위/시간과 내용 hash가 결속돼야 한다. owner 검토가 필요한 외부 증거의 실증을 이 순수 함수가 수행했다고 주장하지 않는다. 단순 status 변경/임의 reference로 검증을 우회하지 않고 미확인 receipt는 실패로 남긴다. first A의 confirmed receipt는 명시 합성 fixture에만 있다.

controller는 source 취득이 끝나면 `clock`의 실제 `completed_at`을 작업 `as_of`로 고정하고 입력별 available_at를 대조한다. 이는 취득을 마친 지식 시점이며 서로 다른 source의 원 가격시각을 동시 시각으로 만들지 않는다. 순수 함수의 asOf는 명시 입력이고 `now()`로 누락 시각을 채우지 않는다. 화면에 작업 완료시각과 원 가격/session 시각·미확인을 분리한다.

## 5. shares·price·후보 검증과 기존 계산

- **SEC shares:** CIK/hash/receipt 취득·submissions accession/form/acceptance를 결속한다. dei cover shares가 우선이며 eligible dei가 없을 때만 기존 us-gaap fallback을 쓴다. units=shares, 양수 finite, cutoff 당시 취득한 filing만 사용한다. 같은 concept의 최신 eligible filing 및 그 안의 최신 measurement end를 선택하고 같은 end의 다른 val은 `MULTI_CLASS_AMBIGUOUS`다. 결측·단위 불일치·미확인 accession을 0/추정값으로 채우지 않는다.
- **가용성:** filed 날짜를 UTC 자정 가용 시각으로 만들지 않는다. 첫 경계는 `shares_available_at=acquired_at`이라는 보수적 관측 상한이며 known acceptance>acquired 또는 acquired>as_of는 실패다. 현재 companyfacts의 과거 행을 이전 as_of에 백필하지 않는다. 기존 M1의 US17 allowlist를 100개로 바꾸지 않고 새 private sidecar로 검증한다.
- **basis/기업행위:** SEC companyfacts는 dimension/class 정보가 누락될 수 있다. 값이 하나라도 전체 shares와 선택 listing 가격의 경제적 단위가 같다는 증거는 아니다. ShareBasisReceipt의 identity/content/available_at와 기존 single-class/CA-UNIT 검토 근거를 확인한다. `CONFIRMED` label만으로 승인하지 않는다. ADR 배율·여러 class 합산·과거 CA-UNIT의 미래 split factor를 새로 계산/적용하지 않는다. 근거가 없으면 `BASIS_UNCONFIRMED`다.
- **가격:** listing/company/symbol/currency/timezone/basis/job/hash 정확 일치, 양수 finite, 명시 source 시각/available/read 및 cutoff를 검증한다. daily bar timestamp는 시작 시각일 수 있으며 최초 공개·확정 close 시각과 동일하지 않다. 현재 Worker의 `COMPLETE`는 공급자 추정이다. 명시 session close·finality/basis 근거가 없으면 `FINALITY_UNCONFIRMED`/`BASIS_UNCONFIRMED`다. 진행/unknown, adjusted→raw fallback, 전일/다른 상장 대체는 없다.
- **범위:** USD의 검증된 후보만 기존 mcap 정렬에 전달한다. KRW/JPY를 USD 숫자와 비교하지 않고 `CURRENCY_SCOPE_NOT_SUPPORTED`를 남긴다. 적격 US security가 미확인이면 `IDENTITY_UNCONFIRMED`다. 결측/실패 대상을 configured roster에서 지우지 않고 missing에 유지한다.
- **계산:** 기존 `universe/sources.py::mcap_top_n_snapshot`의 `shares*price`, mcap 내림차순·동률 company_id 오름차순을 재현한다. rank 전에 반올림/normalize/localeCompare를 하지 않는다. company_id는 canonical ASCII ID이며 같은 issuer의 중복 후보는 자동 집계하지 않는다. 양수 finite 입력의 곱이 nonfinite여도 `NONFINITE_MCAP`다. n은 유효 USD 행 수이며 상위100/500으로 자르지 않는다.
- **표시:** rows는 `SUPPORTED_USD_ROWS`의 **개인 참고 부분순위**다. configured19/약100 전원의 완전순위·미국 전체 순위·Official·정확 EOD가 아니다. 유효 행이 있으면 PERSONAL_REFERENCE, 0이면 NOT_AVAILABLE이며 configured_count/missing_count를 표시하고 full_configured_rank_status=UNKNOWN을 유지한다. 전체 후보 완전성 근거가 없어 candidate_pool_complete=false다.
- **QGV:** 첫 구현에 QGV/V 재점수·새 가중치·score 순위를 넣지 않는다. 이후 기존 QGV snapshot을 개인 view에 연결해도 대상 전원의 snapshot·score/coverage·cutoff/PIT/현재성 근거가 별도로 필요하다. 기존 leaderboard는 null/오래된 snapshot을 검증하지 않는다. mcap 성공을 현재 QGV 순위 성공으로 표시하지 않는다.

ShareBasisReceipt/sessionEvidence 검증은 입력 경계다. 실제 증거가 없으면 NOT_AVAILABLE이며 테스트를 통과시키려고 실제 값에 synthetic 표지·가짜 확인 receipt를 붙이지 않는다.

## 6. 작업 수명과 공개 금지

controller가 foreground 한 작업을 관리하며 start에서 manifest hash/unique job ID를 고정한다. login/session epoch·job·manifest version·listing이 다른 늦은 응답은 버린다. logout/인증 실패·다른 owner·cancel·clear·pagehide/화면 파기·manifest 변경에서 abort하고 source/shares/prices/candidates/rows/missing의 RAM 참조를 해제한다. 다른 작업 결과를 재사용하지 않는다.

가격/returns/시총/가격 의존 V·QGV/순위 및 그 순위로 선정한 membership, 실제 interest/선택 manifest를 public Git/Pages/JSON/Actions log/artifact/PR/telemetry로 보내지 않는다. localStorage/IndexedDB/Cache API/KV/D1/R2/file/backup/service-worker cache/log/crash에도 가격/파생값을 저장하지 않는다. Worker module-global price cache는 없다. 허용된 비가격 rate state 저장은 가격 보관의 예외가 아니다.

기존 holdings/Sheets/Worker origin 저장을 private subset 가격·결과·manifest의 자동 backup에 사용하지 않는다. 오류는 고정 code/count만 쓰고 입력값·개인 listing/CIK/URI query/token을 echo하지 않는다. response/upstream은 no-store, redirect=error다. 로그가 없다는 사실이 공급자 권리 증명은 아니다.

가격을 유지하지 않아 종료 후 완전 replay·과거 시총 순위·historical PIT/OOS/Calibration을 보장하지 않는다. Holdout/v2를 실행하지 않는다. SEC 공개 자료/metadata 권리를 개인 가격·선택 membership의 공개 권리로 확장하지 않는다.

## 7. 합성 테스트와 리뷰

PR A는 실제 가격/주식 수·개인 관심 목록을 fixture에 넣지 않는다. TARGET19 public identity는 기존 mapping/hash로 대조하고 계산 비교는 `synthetic_a/b/...`와 가상 issuer의 합성값만 쓴다.

| test 이름(A Node) | assertions |
| --- | --- |
| `target19_identity_is_preserved_without_weights_or_holdings` | 19 identity, stry→SYK, KR/JP 본상장, weight/holdings 입력 변경 없음 |
| `explicit_seed_union_deduplicates_listing_and_keeps_origin_tags` | 같은 listing만 dedup, 다른 security/issuer 병합 없음, 관심 seed 없으면19·pending |
| `large_cap_tag_never_selects_by_sec_order_or_public_rank` | 입력/SEC 순서가 바뀌어도 선택집합 동일, 100으로 자동 채우지 않음 |
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
| `job_controller_drops_late_response_and_clears_all_ram` | logout/cancel/pagehide/hash/session 변경 후late결과 없음, abort·RAM정리 |
| `pure_boundary_has_no_io_mutation_storage_or_diagnostics` | input deepcopy동일, 순수함수 fetch/storage/loggingspy0, stdout/sentinel 노출없음 |

PR A Python test `test_js_subset_mcap_matches_existing_candidate_order`는 기존 `mcap_top_n_snapshot`에 **합성 입력만** 전달해 Node의 같은 fixture company 순서/곱/selected count와 비교한다. shares/price gate에서 미리 제외된 대상은 sidecar 전용 reason이므로 기존 helper의 raw excluded.reason과 동일하다고 주장하지 않는다. 양쪽에 같은 invalid 후보를 전달한 별도 사례에서는 기존 `MISSING_INPUT`, `NOT_AVAILABLE_AT_AS_OF`, `NON_POSITIVE`도 그대로 비교한다. Official constructor/store/historical runner는 호출하지 않는다. candidate_pool_complete=false를 확인한다. Node가 없으면 새 runner/dependency를 임의 설치하지 않고 제한을 기록한다.

PR B 추가 테스트(기존 Worker/Google session harness에 합성 fetch 주입):

- `m3_routes_require_exact_origin_owner_audience_email_and_expiry`: 다른Origin/owner·token 결측/만료/Google 실패에서 sourcecalls0. 인증 전 manifest 목록 노출 없음.
- `m3_routes_use_private_manifest_and_fixed_upstream_only`: query/encoding/CIK/symbol/URLoverride·미등록 manifest 거부. legacyhistory19 allowlist/response 유지.
- `m3_sec_headers_limits_stream_and_redirect_fail_closed`: 합성 SEC 연락User-Agent, Bearer 전달없음, bodylimit/timeout/redirect/HTTPerror 차단.
- `m3_sources_share_existing_owner_admission_and_release`: 기존 history와 동시/5초/daily/lease 공유, 실패/abort도release, rate metadata에 가격/CIK/token 없음.
- `m3_responses_are_private_no_store_and_have_no_credentials`: response/upstream no-store, 관측/오류/log/response에 auth/config sentinel 없음.
- `fetch_subset_keeps_token_inside_existing_session`: tokengetter 없음, approvedOrigin만 호출, logoutepoch/abort·401/403에서 결과 폐기.
- `m3_view_is_foreground_only_and_never_writes_public_or_backup`: 자동poll/시작fetch 없음, 다른 화면/job과 혼합 없음, storage/backup/svcworker호출0. public builder에 private manifest/가격/result를 입력하면 privacy guard가 거부함.

고정 reason: `INVALID_INPUT`, `SEED_SELECTION_PENDING`, `IDENTITY_UNCONFIRMED`, `MANIFEST_MISMATCH`, `CIK_MISMATCH`, `ACCESSION_UNCONFIRMED`, `SHARES_NOT_AVAILABLE`, `MULTI_CLASS_AMBIGUOUS`, `BASIS_UNCONFIRMED`, `INVALID_TIMESTAMP`, `INVALID_TIME_ORDER`, `AVAILABLE_AFTER_AS_OF`, `PRICE_NOT_AVAILABLE`, `FINALITY_UNCONFIRMED`, `CURRENCY_SCOPE_NOT_SUPPORTED`, `DUPLICATE_ISSUER`, `NONFINITE_MCAP`, `MIXED_SYNTHETIC_INPUT`, `CANCELED`. transport는 기존 auth/rate code 및 `SOURCE_NOT_CLEARED`, `SOURCE_TOO_LARGE`, `SEC_UNAVAILABLE`, `SEC_FORMAT_CHANGED`를 쓰며 raw 예외는 숨긴다. 복수 오류는 identity→time→shares→basis→price→currency→product 순서의 첫 code를 검사한다.

후속 구현의 검증 명령(cwd=repo root):

```bash
node --test implementation/tools/private_subset_node_test.js
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=implementation/src python -m pytest -p no:cacheprovider -q implementation/tests/test_private_subset_mcap_contract.py
node --test implementation/worker/tests/worker.test.mjs
node --test implementation/tools/google_sheet_auth_node_test.js
git diff --name-status
git diff --check
```

이번에는 신규 tests/코드를 **구현·실행하지 않았다**. A 완료는 합성 개인 입력·기존 계산·결측·수명 계약이며 B 연결/실데이터/약100개 free coverage 완료가 아니다. B에는 권리·Free/private manifest·basis/session 근거·auth/privacy 회귀와 제한된 foreground 확인이 필요하다. workflow/Frozen/public data를 바꾸어 검사 통과를 만들지 않는다. static code asset 변경도 명시된 owner review 범위 안에서만 검증한다.

## 8. 후속 사용자 입력과 의존성

이번 문서 PR에는 추가 승인이 필요하지 않다. A는 합성 입력으로 착수할 수 있다. 실제 약100개 선정/연결에는 **본인이 명시한 관심/대형주 seed**, 비공개 manifest의 owner 설정, 추가 provider symbol/security class, 가격 source 권리, KR/JP/ADR의 basis/shares 근거가 필요하다. 이를 확정100개 roster나 사용 가능한 가격/API 키로 추정하지 않는다.

근거: [기존 M3 설계](M3_PRIVATE_UNIVERSE_DESIGN.md), [universe/sources.py](../../src/investment_system/universe/sources.py), [SEC M1](../../src/investment_system/providers/sec_m1.py), [listing 계약](../../src/investment_system/contracts/global_universe.py), [Worker](../../worker/src/index.js), [기존 session](../../src/investment_system/product/web_assets/google-sheet-quotes.js), [SEC API/CORS](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [SEC Fair Access](https://www.sec.gov/about/developer-resources). 외부 설명2개는 2026-10-10 HTTP200으로 확인했으며 company catalog/회사 facts/submissions/가격 endpoint는 호출하지 않았다. SEC 직접 경로는 FRED를 사용하지 않는다.
