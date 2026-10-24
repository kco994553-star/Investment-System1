# 프론트 v2 P1 자료·계산 층: P2 레인용 API 계약

P2 화면 레인이 쓰는 함수, 기록 모양, 사유 코드, 지켜야 할 규칙을 정한다. 근거는 P1 구현 사양(Main 결정 2026-10-24)이다. 기능 번호는 사양 v1.0 번호(1~9)다.

## 1. 파일과 화면 등록

- 위치는 `implementation/src/investment_system/product/web_app/`이고, 전역은 `IS2` 하나다.
- `index.html` 순서: P0 기반(core·shell·parts) → 옛 모듈 57개(web_assets 바이트 그대로, 빌드 A안) → `action` → `data` → `prices` → `store` → `qgv` → `engines` → 레인 파일 8개(`screen-qgv/technical/macro/news/portfolio/prompts/tree/lab.js`) → P0 화면 → `boot.js`. 모두 `defer`다. 레인은 index.html을 고치지 않고 자기 파일만 채운다.
- 등록:
  - `IS2.register(id, render)`: 자리표시를 실제 화면이 대신한다. 실제 화면을 두 번 등록하면 `SCREEN_DUPLICATE`다.
  - `IS2.registerDetail(name, render)`: `#/detail/<name>`에 쓴다. 이름은 `IS2.DETAILS`에 있어야 한다(`DETAIL_UNKNOWN`).
- `render(route)`는 Node를 동기로 돌려준다.
  - 비동기 값은 자리를 먼저 그리고 나중에 채운다.
  - `route.signal`은 렌더마다 새로 만드는 AbortController의 signal이다. 다음 렌더 때 abort된다.
  - 모든 `subscribe(fn, {signal: route.signal})`는 abort되면 저절로 풀린다. 늦게 온 값은 `signal.aborted`를 보고 버린다.
- 오류는 값이 들어가지 않은 고정 코드로만 던진다. 셸이 `e.message`를 화면에 그대로 띄우기 때문이다.
- 페이지를 열기만 해서는 아무것도 읽지 않는다. 공개 파일은 화면이 `IS2.data.ready()`나 `IS2.qgv.page()`를 부를 때 처음 읽는다.

## 2. 모든 화면이 지킬 규칙

- **클릭 규칙**
  - 비공개 요청(시트·Worker·OAuth)과 기기 저장 쓰기는 첫 인자로 받은 **진짜 사용자 이벤트**로만 실행한다.
    - 조건: `event instanceof window.Event && event.isTrusted`이고, 형식이 click, submit, Enter/Space keydown 중 하나.
    - 클릭 처리기 안에서 바로 부른다. `login`은 같은 틱이어야 한다.
  - 이벤트가 없거나, 합성이거나(`dispatchEvent`, `el.click()`), `{isTrusted:true}` 같은 일반 객체면 `CLICK_REQUIRED`다.
- **RAM 가격 표시**
  - 기기 가격과 가격 파생값(시총, EV, 수익률, 배수, 내재 성장, 월말 종가)은 RAM에만 둔다.
  - 화면에는 `[data-ram-price]` 요소의 글자로만 낸다. 속성, 입력 value, 제목, 저장소, 콘솔, URL에는 넣지 않는다.
  - 값을 내주는 곳은 `prices.quote()`, `prices.history()/held()`, 가상매매·세트 비교 결과뿐이다.
  - 시험 도우미: `tools/web_app_test_site.js`의 `assertRamOnly(page, sentinels)`.
- **NA 규칙**
  - 값이 없으면 null이고 사유 코드가 반드시 붙는다. 0이나 평균으로 채우지 않는다(`?? 0`, `|| 0` 금지).
  - 글은 `IS2.qgv.reasonText(code, en)`로 만든다.
- **V 출처**: 화면 글자에는 `row.source_label`(지금은 '임시 V')만 쓴다. 출처 낱말은 `qgv.js`에만 있다(소스 검사).
- **그 밖의 금지**
  - `console.*`, `innerHTML`, 주문·거래 기능과 문구.
  - `[style]` 속성. P0 시험이 금지하므로 막대는 SVG 속성이나 클래스 단계로 그린다.
  - Universe504는 universe-codes.json의 고정 504코드 목록이다. 다른 성격으로 설명하지 않는다.

## 3. 클릭 관문: `IS2.action`

- `run(event, kind, fn)`: `fn(signal)`을 같은 틱에 부르고, fn이 끝날 때까지 그 kind를 진행 중으로 둔다. 화면은 직접 부르지 않고 아래 함수들에 event를 넘긴다.

  | kind | 갈 수 있는 비공개 목적지 | 기기 저장 쓰기 |
  | --- | --- | --- |
  | `PUBLIC_REFRESH` | 없음(공개 파일만) | 안 됨 |
  | `LOGIN` | GIS 스크립트·OAuth | 됨 |
  | `UNIVERSE_READ` | 시트 values GET | 됨 |
  | `HISTORY` | Worker `/history` | 됨 |
  | `SYNC` | Worker, 시트 읽기·추가·갱신 | 됨 |
  | `WRITE` | 없음 | 됨 |

- 클릭 밖의 쓰기와 요청은 이렇게 막힌다.
  - 비공개 요청: `CLICK_REQUIRED`. 알 수 없는 목적지는 `DESTINATION_UNKNOWN`이다.
  - 옛 모듈의 저장 쓰기: `ACTION_REQUIRED`. 저장소는 그대로 남는다.
  - 둘 다 `blocked()` 수가 늘어난다.
- IndexedDB는 이미 있는 DB(`stores()`)나 쓰기 클릭 안에서만 연다. 읽기는 DB를 만들지 않는다. 거절 코드 `DEVICE_STORE_NOT_OPENED`는 '아직 저장된 것 없음'이라는 뜻이다.

## 4. 공개 자료: `IS2.data`

- `FILES` 20개
  - 세대 묶음: macro-screen, sec-13f-changes, sec-filing-windows, sec-qg-factors, company-types-pricefree, company-classification, sec-qgv2, sec-public-inputs, dart-financials, macro-evidence, 목록 3개(sec-disclosures, news-signals, dart-disclosures), sec-universe-shares
  - 정적: actual-catalog, entities, company-names-ko, universe-codes, sec-valuation-inputs, forward-validation-ledger
- 모든 view가 `strictFetch` 하나로 읽는다.
  - 같은 출처, `FILES`만, GET만, 2 MiB 상한.
  - credentials omit, redirect error, no-referrer.
  - HTTP 상태는 그대로 둔다.
  - 오류: `PUBLIC_FILE_UNKNOWN`, `PUBLIC_FILE_METHOD`, `PUBLIC_FILE_TOO_LARGE`.
- `ready()`
  - 첫 호출에 `DataRefresh.load`를 부르고 publication을 돌려준다. 이후 호출은 같은 Promise를 받는다.
  - 읽기 모듈이 빠져 있으면 `READER_MISSING`이다. 가벼운 경로로 빠지지 않는다.
- `get(name)`: 현재 세대의 검증된 값 또는 null. `sec-qgv2.json`은 Qgv2Inputs 출력이다. `screens()`는 묶음 전체이고 엔진용이다.
- `state(name)` → `{state:'OK'|'NOT_PUBLISHED'|'FAILED'|'NOT_READ', why, as_of, text}`
  - why: `INVALID`, `NETWORK`, `HTTP`, `SCHEMA_NEWER`, `READER_MISSING`.
  - 미게시(404)와 읽기 실패는 다른 문장을 쓴다.
- `list('sec'|'news'|'dart')`, `shares()`, `financials()`: 세대마다 한 번 읽고 모든 화면이 함께 쓴다.
- `static(name)`: 정적 파일을 페이지당 한 번 읽는다. 값 또는 null이고, 사유는 `state(name)`에 있다.
- `universe()`: 고정 504코드 목록이다.
- `refresh(event)` [PUBLIC_REFRESH]
  - 결과: `'APPLIED'|'UNCHANGED'|'FAILED'|'LOADING'`.
  - 전부 아니면 전무다. 실패하면 이전 값을 유지한다.
- `subscribe(fn, {signal})`: `fn({reason:'REFRESH'|'REJUDGE', generation, …})`. 부를 때 `get()`은 이미 새 값이다.
  - 신선도 재판정은 네트워크 없이 1분마다, 다시 보일 때, 화면을 바꿀 때 한다.
- `peek('sec-qgv2.json')`: TARGET 확정 전용이다. 세대를 바꾸지 않고, SecQgv2.validate를 통과한 원본 JSON을 돌려준다.

## 5. 점수: `IS2.qgv` (QGV v2 하나)

- `page({preset, gate, signal})` → Page.
  - 같은 입력이면 모든 화면이 같은 객체를 받는다.
  - 계산은 `QgvScores.pageResult(scoreView, …)`가 한다. scoreView는 네트워크를 쓰지 않는다(`SCORE_PATH_NO_NETWORK`).
  - 가격은 클릭으로 읽은 Universe 탭과 가격 탭, 이미 있는 기기 DB에서만 온다.
- 접근 함수
  - `rows(page, {scope:'ALL'|'UNIVERSE'|'TARGET'})`: QgvScores 순서 그대로 준다. 정렬, 모집단, 분류 필터, 레이더는 P2-2가 옛 함수(LeaderboardScreen, StatRadar `compute(spec,{result})`)로 붙인다.
  - `row(page, idOrCode)`, `coverage(page)`(수만).
  - `preview(page, weights)`: 개인 가중치다. 결과는 늘 `weights:'PERSONAL'`이고 공식 순위가 없다.
  - `setProfile({preset, gate})`(RAM만), `profile()`, `constants()`(2.5 트리용), `subscribe(fn(why), {signal})`. why는 DATA·PRICES·DEVICE·PROFILE이다.
  - `reasonText(code, en)`, `V_SOURCES`, `vSource()`.
- `forEngines`, `engineInputs`, `scoreView`는 engines 전용이다(소스 검사로 막는다).

```
Page { v_source{id,ko,note}, engine_v_source{…}, state: READY|NO_DATA|DATA_FORMAT_NEWER|READ_FAILED, reason,
  as_of, calc_version, type_scope, profile_id, preset, gate, generation, basis_id,
  price_basis{kind:'DEVICE_RAM', connected, source, read_id, read_at, time_status: CONFIRMED|UNCONFIRMED|PARTIAL|null, freshness, times[]},
  coverage, rows[] }
RowRecord { id, ticker, code, record, scope: UNIVERSE|OUTSIDE_UNIVERSE, target, reference_only, source, source_label,
  score{total,q,g,v}, na_reason{total,q,g,v,rank}, rank{official, personal, qg_reference_order, group, of, weights: OFFICIAL|PERSONAL},
  coverage{v_factors{n,total:5,missing,required_ok}, axes{Q,G,V}, factors{available,total}, states, v_inputs_missing},
  flags, value_trap_gate, v_excluded, types{selected,reason}, row_state, acquired_at, fiscal_year_end, profile, source_reason_codes }
```

- Page와 행에는 가격과 가격 파생값이 없다. 빠지는 것은 quotes, quote_meta, 월말 종가, EV, 수익률, `detail`, `reference_range`다.
- `read_at`은 기기가 시트를 읽은 시각이고 가격 시각이 아니다.
- `v_factors`는 `TargetV1Builder.vFactors` 값이다.

## 6. 가격: `IS2.prices` (클릭 때만 요청, RAM에만 보관)

- `status()`: 코드와 수만 준다. 가격, 시트 ID, Worker 주소는 없다.
  ```
  { google{enabled, ready, connected, pending, preparing, error}, sheet{set}, universe_source{set}, store (+tabs_loaded{daily, monthly}), universe{state, read_at, failure}, worker{state}, history{held} }
  ```
- `subscribe(fn, {signal})`: 로그인, Universe 읽기, 가격 탭이 바뀌면 알린다. 셸 기기 칩도 이것을 쓴다.
- 로그인 [LOGIN]: 두 번 누른다.
  - `prepare(event)`: 세션을 켜고 GIS를 준비한다.
  - `login(event)`: 클릭 안에서 동기로 토큰을 요청한다.
  - `logout(event)`.
  - `deviceSettings()`: 기기 DB가 있을 때만 저장된 켬/끔을 읽는다.
- `readUniverse(event)` [UNIVERSE_READ]
  - `PrivateSubsetView.mount` 클릭 처리와 같은 호출을 같은 순서로 부른다.
  - 공개 주식수는 읽은 시각 기준으로 다시 판정한다.
  - 결과: `{state, read_id, read_at, inputs, config_status, selection{…수}, ranks{…수}}`.
  - 코드: `UNIVERSE_SOURCE_NOT_SET`, `UNIVERSE_SOURCE_INVALID`, `AUTH_REQUIRED`, `SOURCE_TOO_LARGE`, `CANCELED`, `UNIVERSE_READ_FAILED`.
  - 로그아웃하면 지워지고, 토큰 만료로는 남는다.
- `universeRanks()`, `rankFor({company_id, ticker})`: 개인 M3 순위(2.1.1). 순위와 사유만 있고 시총은 없다.
- 가격 탭 [SYNC]: 결과는 수와 코드뿐이다.
  - `useTabs(event)`, `loadTabs(event)`.
  - `syncSymbols(event, symbols, '1d'|'1mo', {kind})`: Worker 허용 목록만.
  - `syncUniverse(event)`.
- `history(event, company, {range})` [HISTORY]와 `held(company, {range})`: 검증된 일별 이력이다. RAM에만 있고 가격을 포함한다.
- `quote(company)` → `{state:'OK', price, currency, source, read_at, as_of, time_status, freshness}` 또는 `{state:'NA', reason:'NO_DEVICE_PRICE'}`. `[data-ram-price]` 표시 전용이다.
- `priceView`, `storeFacade`, `universeView`는 qgv·engines 전용이다.
  - 가격 view는 하나뿐이다. 세션과 PriceStore가 view를 키로 상태를 두기 때문이다.
  - facade는 클릭으로 탭을 읽기 전에는 `{}`나 null을 준다.

## 7. 기기 저장: `IS2.store` (옛 키·스키마 그대로)

- 읽기는 자유롭다. 쓰기는 `WRITE` 클릭 안에서만 한다.
- `KEYS`: personal, settings, profile-drafts(-v2), playbook, investor-stars, backup-restored, virtual-trading-v-scores(v1·v2), unified-sheet-source, universe-source, private-history-origin, price-store-enabled, 그리고 IndexedDB `investment-device-actual-v1`.
- 함수
  - 관심 기업(1.1.4): `prefs()` → `{state:'OK'|'EMPTY'|'INVALID', value}`. `savePrefs(event, next)`. 코드는 `PREFS_INVALID`, `PREFS_STORAGE_INVALID`다.
  - 가중치(2.2): `weights()`, `saveWeights(event, spec)`, `PRODUCT_PRESETS`.
  - 보유(6.1): `holdings()` → `{state:'OK'|'EMPTY'|'NOT_AVAILABLE', reason, snapshot, source, as_of}`. DB가 없으면 `DEVICE_STORE_NOT_OPENED`이고 DB를 만들지 않는다.
  - 플레이북: `playbook()`, `saveThesis/saveHold/saveRecord(event, …)`.
  - 투자자 별표: `stars()`, `toggleStar(event, cik)`.
  - V 기록: `vHistory()`(읽기 전용).
  - 백업
    - `backup.create()`는 늘 /4로 만든다. `backup.download(event)`.
    - `backup.restore(event, text)`는 /1~/4만 받는다.
    - /5는 `BACKUP_USER_OBJECTS_UNSUPPORTED`다. 그 밖의 거절은 `BACKUP_INVALID`, `BACKUP_TOO_LARGE`다.
  - 출처: `sheetSource`, `universeSource`, `workerOrigin`의 `has()`, `set(event, url)`(`workerOrigin`만 `approved()`도 있다). ID와 주소는 돌려주지 않는다.
  - `subscribe(fn(key), {signal})`.

## 8. 엔진: `IS2.engines` (옛 엔진 그대로, 기기 결과로 계산)

- 공통
  - 점수는 공유 Page의 기기 결과다. 저장하는 기록에는 `page.engine_v_source`를 남긴다.
  - 쓰기는 모두 클릭 안에서만 한다. 결과는 얼린 복사본이다.
  - 가격이 든 결과(가상매매, 세트 비교)는 RAM 전용이다.
- **target**(2.1.7)
  - 읽기: `state()`, `basis()`, `draft({date, basis})`, `blockers()`, `ruleBDue(date)`, `scoringPending()`, `refreshScoring()`.
  - 쓰기·요청
    - `build(event, {reset})` [WRITE]. 카드 응답이 있으면 `reset:true`가 필요하다.
    - `finalize(event)` [WRITE]. outcome은 `FINALIZED`, `BLOCKED`, `DRAFT_REGENERATED`, `RELOAD_REQUIRED` 중 하나다. `FINALIZED`면 버전에 `v_source`를 기록한다.
    - `answer(event, …)`, `selectRuleB(event)` [WRITE].
    - `compare(event)`, `syncScoringPrices(event)` [SYNC].
- **playbook**
  - `facts(symbol)`.
  - `judge({symbol, situation, date})`: 읽기 전용이다.
  - `record(event, judged)` [WRITE]: 발생 기록을 쓴다. `judge()` 결과만 받는다(`JUDGEMENT_UNKNOWN`).
  - `due(date)`, `limits(rows, cash)`.
- **virtual**
  - `stored({reportDate})`(fetch:false)
    - 시작일 전: `NOT_STARTED`.
    - 로그인과 승인된 Worker가 없으면: `NOT_AVAILABLE`.
    - 그 밖에 탭을 읽기 전이면 종목별로 `PRICE_NOT_FETCHED`.
  - `compare(result, {defs})`, `forward()`(9.2, 가격 없음), `rehearse()`(RAM만).
  - `run()`은 늘 `NOT_IN_P1`이다. 기록 실행은 P2-6에서 붙인다.
  - 세트 B/C/D(장부 시트)도 P2-6이다. 대응: `VirtualLedgerSheets.load` / `active(meta,k)` / `apply` / `definitions`(virtual-ledger-sheets.js:696-699).
- **macro**(4.1.4): `current()`. 세대마다 `MacroLights.setPublic`을 부른다.

## 9. 사유 코드 요약

- 행 NA
  - V: coverage V 사유와 같다(`vCoverage` 규칙). 예: `NO_DEVICE_PRICE`, `SOURCE_NOT_AVAILABLE`, `FINANCIAL_PROFILE_V_NOT_DEFINED`, `CROSS_SECTION_TOO_SMALL`, `AXIS_WEIGHT_INSUFFICIENT`.
  - total: `DATA_FORMAT_NEWER` → `CALC_VERSION_MISMATCH` → 엔진 total_reason 순서로 정한다.
  - rank: `QG_REFERENCE`, `OUTSIDE_UNIVERSE`, `REFERENCE_ONLY`, `NOT_RANKED`, 또는 total 사유다.
- Page: `SEC_QGV2_NOT_PUBLISHED`, `SEC_QGV2_NOT_AVAILABLE`, `SEC_QGV2_SCHEMA_NEWER`, `SEC_QGV2_INVALID`, `SEC_QGV2_UNAVAILABLE`, `V2_SCORES_NOT_AVAILABLE`, `READER_MISSING`.
- 관문: `CLICK_REQUIRED`, `ACTION_REQUIRED`, `DESTINATION_UNKNOWN`, `DEVICE_STORE_NOT_OPENED`, `ACTION_KIND_UNKNOWN`.
- 중앙 V(미리 등록, 초안 문구): `NO_OFFICIAL_YET`, `SUPPLY_FAILED`, `VERIFY_FAILED`, `PRICE_DEPENDENT_NOT_COMPUTABLE`.

## 10. V 출처 전환점(중앙 V가 게시될 때 바꿀 곳 전부)

화면은 바꾸지 않는다. 페이지 전체가 한 번에 바뀐다.

1. `qgv.js`: `OFFICIAL_READER`(유일한 스위치)를 설정하고 `centralPage`를 구현한다. Q·G도 게시본에서 읽고 sec-qgv2.json과 섞지 않는다.
2. `data.js`: `FILES`에 넣고 엄격 리더를 붙인다.
3. Pages 가드 허용 목록에 넣는다(Main).
4. `TargetV1Builder.finalize`는 #391에서 `v_source`를 직접 박는다. 옵션이 필요하다(Main이 #391에 요청). 그전까지는 engines가 기록하고, 병합 뒤에는 값이 일치하는지만 확인한다.
5. 엔진 중앙 모드 계약: `forEngines`는 늘 기기 결과를 주므로 기록은 `engine_v_source`(DEVICE_TEMPORARY)를 남긴다. 어댑터를 둘지, 엔진은 기기 V로 고정할지 그때 정한다(`qgv.js` engine_v_source·forEngines, `engines.js` finalize). TARGET 카드 판정과 R-B 기록에는 출처 필드가 없다(옛 형식, 모두 기기 V).
6. `OFFICIAL_CENTRAL` 문구는 초안이다. 전환할 때 사용자 확인을 받는다.

## 11. 사용자 결정 대기

- V 기록(D-21): P1은 기록하지 않는다. 클릭 때만 기록할지 정한다.
- 플레이북 판정 기록: 옛 앱은 판정할 때 자동으로 기록했다. 새 앱은 `record(event)`를 누를 때만 기록한다.
- R-B 선정: 옛 화면은 열 때 자동으로 했다. 새 앱은 `selectRuleB(event)`를 누를 때만 한다.
- IndexedDB 'market' 시세 저장을 계속할지 정한다. 계획 §2.1과 충돌한다.
- 일일 보고서·보고서 모델, 가상매매 기록 실행, 세트 B/C/D는 P2-6에서 정한다(daily-report.js는 불러오지 않음).
- 로그인 두 번 누르기(준비 → 로그인)를 유지할지 정한다.
- 중앙 V 모드의 엔진 계약(10절 5).
- 백업 /5: 지금은 고정 코드로 거절한다. 검증기를 재사용할지 정한다.
- 남은 항목
  - 임시 V 기준 순위 문구
  - Universe 출처를 통합 시트와 따로 둘지
  - 구글 켬/끔을 기기에 저장할지(P1은 sheetSettings를 쓰지 않음)

## 12. 시험

- 노드 시험(`node implementation/tools/<파일>`)
  - `web_app_reuse_node_test.js`: 재사용 목록, 빌드, 소스 규칙.
  - `web_app_qgv_node_test.js`: action, data, qgv.
  - `web_app_prices_node_test.js`: prices, store.
  - `web_app_engines_node_test.js`.
- 브라우저 시험: `web_app_data_layer_browser_test.js`. Playwright가 필요하다(`NODE_PATH`, `PLAYWRIGHT_BROWSERS_PATH`).
  - 빌드 출력: 재사용 파일이 바이트 그대로이고, 부르지 않는 옛 파일이 없다.
  - A: 행동 없이 읽으면 공개 파일만 읽고, 저장 0, blocked 0이다.
  - B: 흉내 낸 행동은 모두 거절되고 요청이 0건이다.
  - C: 실제 클릭이면 정해진 요청만 나가고 V가 계산되며, 표지 가격이 새지 않는다.
  - D: 새로고침하면 RAM이 비워진다.
- `web_app_shell_browser_test.js`(P0)는 고치지 않고 통과한다.
- 도우미: `web_app_reuse.js`(옛 모듈 경로 한 곳), `web_app_test_site.js`(빌드·서빙·fixture·`watch`·`storage`·`leaks`·`assertRamOnly`).
- CI 목록 등록은 Main이 한다.
