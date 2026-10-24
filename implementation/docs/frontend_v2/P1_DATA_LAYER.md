# 프론트 v2 P1 자료·계산 층: P2 레인용 API 계약

P2 화면 레인이 쓰는 함수와 기록 모양을 정한다. 근거는 P1 구현 사양(Main 결정 2026-10-24)이다. P1 자료·계산 층 여섯 파일(`action`, `data`, `qgv`, `prices`, `store`, `engines`)을 모두 적었다.

## 1. 파일과 순서

- 위치: `implementation/src/investment_system/product/web_app/`. 전역은 `IS2` 하나다.
- `index.html` 순서: P0 기반 → 옛 모듈 57개(web_assets 바이트 그대로) → `action` → `data` → `prices` → `store` → `qgv` → `engines` → 레인 자리 파일 → P0 화면 → `boot.js`.
- 모든 오류는 고정 코드로 던진다(예: `CLICK_REQUIRED`). 셸이 `e.message`를 화면에 그대로 띄우기 때문이다.
- 페이지를 열기만 해서는 아무것도 읽지 않는다. 공개 파일은 화면이 `IS2.data.ready()`나 `IS2.qgv.page()`를 부를 때 처음 읽는다.

## 2. 클릭 규칙: `IS2.action`

- `run(event, kind, fn)`: `event`가 `window.Event`이고 `isTrusted`이며, click·submit·Enter/Space keydown일 때만 `fn(signal)`을 같은 틱에서 부른다. 그 밖에는 `CLICK_REQUIRED`다. 합성 이벤트나 `{isTrusted:true}` 객체도 거부한다.
- kind와 갈 수 있는 비공개 목적지:

  | kind | 목적지 | 기기 저장 쓰기 |
  | --- | --- | --- |
  | `PUBLIC_REFRESH` | 없음(공개 파일만) | 안 됨 |
  | `LOGIN` | OAuth(GIS) | 됨 |
  | `UNIVERSE_READ` | 시트 values GET | 됨 |
  | `HISTORY` | Worker `/history` | 됨 |
  | `SYNC` | Worker, 시트 읽기·추가·갱신 | 됨 |
  | `WRITE` | 없음 | 됨 |

- `guard(url, init)`: 비공개 요청이 부르는 확인. 허용되지 않으면 `blocked()`가 늘고 `CLICK_REQUIRED`를 던진다. 알 수 없는 목적지는 `DESTINATION_UNKNOWN`이다.
- `gatedStorage`: 읽기(`getItem`·`key`·`length`)는 통과한다. 쓰기(`setItem`·`removeItem`·`clear`)는 저장 쓰기 kind 안에서만 되고, 아니면 `ACTION_REQUIRED`다.
- `gatedIndexedDB`: 이미 있는 DB(`stores()`가 `indexedDB.databases()`로 확인)나 저장 쓰기 action 안에서만 연다. 점수 경로는 읽기 전용이라 action 안에서도 DB를 만들지 않는다. 거절 코드는 `DEVICE_STORE_NOT_OPENED`이고, 이것은 '아직 저장된 것 없음'이지 막힌 쓰기가 아니다.
- `view(overrides)`: 옛 모듈에 넘기는 window. 소문자 window 함수는 실제 window에 묶는다(`DataRefresh.proxy`와 같은 규칙). 저장소 3종은 위의 gated 판으로 바뀐다. window 전역 쓰기는 거절한다. `fetch`는 반드시 넘겨야 한다.

## 3. 공개 자료: `IS2.data`

- `FILES`: 고정 허용 목록 20개.
  - 세대 묶음: PublicScreens 5개, company-classification, sec-qgv2, sec-public-inputs, dart-financials, macro-evidence, 목록 3개, sec-universe-shares
  - 정적: actual-catalog, entities, company-names-ko, universe-codes, sec-valuation-inputs, forward-validation-ledger
- `strictFetch(name, init)`: 모든 view의 공개 요청 함수다. 같은 출처, `FILES`만 허용, `credentials:'omit'`, `redirect:'error'`, `referrerPolicy:'no-referrer'`, GET만, 2 MiB 상한. HTTP 상태는 그대로 둔다. 코드는 `PUBLIC_FILE_UNKNOWN`, `PUBLIC_FILE_METHOD`, `PUBLIC_FILE_TOO_LARGE`이다.
- `ready()`: 첫 호출에 `DataRefresh.load`로 세대 묶음을 읽고 publication을 돌려준다. 이후 호출은 같은 Promise다.
  - SecQgv2, Qgv2Inputs, PublicScreens, MacroLights, PlaybookEngine, PlaybookConfigDefaults, DataRefresh 가운데 하나라도 없으면 `READER_MISSING`으로 닫는다. 가벼운 경로로 조용히 빠지지 않게 하기 위해서다.
- `get(name)`: 현재 세대의 검증된 값이고, 없으면 null이다. `sec-qgv2.json`은 Qgv2Inputs 출력이다.
- `screens()`: 현재 세대의 검증된 묶음 전체다(옛 app.js의 `publicScreens`). 옛 엔진이 이 묶음 하나를 인자로 받는다(`MacroLights.setPublic`, `PlaybookScreen.prepareScores`·`factsFor`, `VirtualTradingCompare.typesFrom`). 화면은 `get(name)`을 쓴다.
- `state(name)`: `{state:'OK'|'NOT_PUBLISHED'|'FAILED'|'NOT_READ', why, as_of, text}`. 읽기 실패와 미게시(404)는 같은 문장을 쓰지 않는다. why는 `INVALID`·`NETWORK`·`HTTP`·`SCHEMA_NEWER`·`READER_MISSING`이다.
- `list('sec'|'news'|'dart')`, `shares()`, `financials()`: 세대마다 한 번 읽고 모든 화면이 공유한다.
- `refresh(event)`: `PUBLIC_REFRESH` 클릭으로만 부른다. 결과는 `'APPLIED'|'UNCHANGED'|'FAILED'|'LOADING'`이다. 전부 아니면 전무이고, 실패하면 이전 값을 유지한다.
- `subscribe(fn, {signal})`: 새 세대 적용(REFRESH)이나 신선도 재판정(REJUDGE) 뒤에 `fn(detail)`을 부른다. 이때 `get()`은 이미 새 값을 돌려준다.
- 재판정: 보이는 동안 1분마다, 탭이 다시 보일 때, 화면을 바꿀 때 부른다. 네트워크는 쓰지 않는다.
- `static(name)`: 정적 파일을 페이지당 한 번 읽는다. 값 또는 null을 돌려주고, 이유는 `state(name)`에 있다.
- `universe()`: universe-codes.json의 고정 504코드 목록이다.
- `peek('sec-qgv2.json')`: 세대를 바꾸지 않는 단독 엄격 읽기다. TARGET 확정 직전 재확인용이고, SecQgv2.validate를 통과한 원본 JSON을 돌려준다(404이면 null).
- 구현 메모: DataRefresh는 확정한 묶음을 attach 훅에만 넘긴다. 그래서 `data.js`는 공개 view를 통해 핵심 리더의 결과를 읽기마다 보관하고, DataRefresh 자신의 `public-data-updated` 이벤트 때 반영한다.

## 4. 점수: `IS2.qgv`

- `page({preset, gate, signal})`는 Page를 돌려준다. 같은 입력이면 모든 화면이 같은 객체를 받는다.
  - 계산은 `QgvScores.pageResult(scoreView, …)`가 한다.
  - scoreView의 fetch는 늘 `SCORE_PATH_NO_NETWORK`로 실패한다.
  - Universe 읽기는 `prices.universeView`, 가격 탭은 `prices.storeFacade`에서 온다. 둘 다 클릭으로 읽기 전에는 없다.
  - 저장 시세는 이미 있는 IndexedDB에서만 읽는다.
- `rows(page, {scope:'ALL'|'UNIVERSE'|'TARGET'})`: QgvScores 순서 그대로 돌려준다. 정렬·모집단·분류 필터·레이더는 P2-2에서 옛 함수(LeaderboardScreen, StatRadar의 `compute(spec,{result})`)로 붙인다.
- `row(page, idOrCode)`: Universe 안의 TARGET은 그 코드의 행이다.
- `coverage(page)`: 수만 돌려준다. `preview(page, weights)`, `setProfile({preset, gate})`, `profile()`, `reasonText(code, en)`, `constants()`, `subscribe(fn, {signal})`, `vSource()`, `V_SOURCES`도 있다.
- `forEngines(page)`, `engineInputs(page)`, `scoreView`: `engines.js` 전용이다(소스 검사로 막는다). 각각 QgvScores가 만든 기기 결과 원형, 그 결과를 계산한 sec-qgv2.json 값(재판정 뒤 `data.get`과 다를 수 있음), 점수 view다.

**Page**
```
{ v_source{id,ko,note}, engine_v_source{…}, state: READY|NO_DATA|DATA_FORMAT_NEWER|READ_FAILED, reason,
  as_of, calc_version, type_scope, profile_id, preset, gate, generation, basis_id,
  price_basis{kind:'DEVICE_RAM', connected, source, read_id, read_at, time_status, freshness, times[]},
  coverage (QgvScores.vCoverage), rows[] }
```

**RowRecord**
```
{ id, ticker, code (Universe 코드|null), record (v2 레코드 키), scope: UNIVERSE|OUTSIDE_UNIVERSE, target, reference_only,
  source, source_label, score{total,q,g,v}, na_reason{total,q,g,v,rank},
  rank{official, personal, qg_reference_order, group, of, weights: OFFICIAL|PERSONAL},
  coverage{v_factors{n,total:5,missing,required_ok}, axes{Q,G,V}, factors{available,total}, states, v_inputs_missing},
  flags, value_trap_gate, v_excluded, types{selected,reason}, row_state, acquired_at, fiscal_year_end, profile, source_reason_codes }
```

- 값이 null이면 그 사유 코드가 반드시 있다. 0이나 평균으로 채우지 않는다.
  - V 사유는 coverage V 사유이고, `vCoverage`와 같은 규칙이다.
  - total 사유는 `DATA_FORMAT_NEWER` → `CALC_VERSION_MISMATCH` → engine total_reason 순으로 정한다.
  - rank 사유는 `QG_REFERENCE`, `OUTSIDE_UNIVERSE`, `REFERENCE_ONLY`, 또는 total 사유다.
- `v_factors`는 `TargetV1Builder.vFactors`를 그대로 부른 값이다.
- 가격과 가격 파생값은 Page에 없다. quotes, quote_meta, 월말 종가, EV, 수익률, 내재 성장, `detail`, `reference_range`가 모두 빠진다.
- 화면 글자에는 `source_label`만 쓴다. '임시 V'라는 낱말은 `qgv.js`에만 있다.
- 중앙 V 사유 코드는 미리 등록해 두었다(초안 문구): `NO_OFFICIAL_YET`, `SUPPLY_FAILED`, `VERIFY_FAILED`, `PRICE_DEPENDENT_NOT_COMPUTABLE`.
- RAM 가격 표시: 기기 가격을 화면에 낼 때는 `[data-ram-price]` 요소의 글자로만 낸다. 속성·값·제목에는 넣지 않는다. 시험 도우미는 `tools/web_app_test_site.js`의 `assertRamOnly`다.

## 5. 가격: `IS2.prices`

- 시트·Worker·OAuth 요청은 그 kind의 클릭 안에서만 나간다. 가격은 RAM에만 둔다. 화면에 가격을 낼 수 있는 값은 `quote()`와 `history()`뿐이고, `[data-ram-price]` 요소의 글자로만 낸다.
- 가격 view는 하나다(`priceView`, qgv·engines 내부용). `GoogleSheetQuotes.sessionFor`와 PriceStore가 view를 키로 상태를 두기 때문이다. 공개 이름은 `data.strictFetch`로, 비공개 목적지는 `action.guard`를 거쳐 나간다. IndexedDB는 읽기 전용이라 클릭 안에서도 DB를 만들지 않는다.
- `status()`: 코드와 수만 있다. 가격·시트 ID·Worker 주소는 없다.
  ```
  { google{enabled, ready, connected, pending, preparing, error}, sheet{set}, universe_source{set},
    store (PriceStore.status + tabs_loaded{daily, monthly}), universe{state, read_at, failure}, worker{state}, history{held} }
  ```
- `subscribe(fn, {signal})`: 로그인 상태, Universe 읽기, 가격 탭이 바뀌면 알린다. 셸의 기기 칩도 이것으로 글자를 바꾼다.
- 로그인(`LOGIN`):
  - `prepare(event)`: 세션을 켜고(`setEnabled(true)`) GIS 스크립트를 준비한다.
  - `login(event)`: 클릭 안에서 동기로 토큰을 요청한다.
  - `logout(event)`: `session.disconnect`.
  - `deviceSettings()`: 기기 DB가 이미 있을 때만 `DeviceActual.sheetSettings`를 읽는다. 저장된 '켬'이면 세션을 켠다(요청 없음). 저장된 '끔'은 사용자가 클릭으로 켠 세션을 끄지 않는다. P1은 sheetSettings를 쓰지 않는다.
- `readUniverse(event)`(`UNIVERSE_READ`): `PrivateSubsetView.mount` 클릭 처리와 같은 호출을 같은 순서로 부른다. 공개 주식수는 `SecUniverseShares.loadInputs(priceView, {now: 읽은 시각})`로 다시 판정한다.
  - 결과: `{state, read_id, read_at, inputs, config_status, selection{state, status, selected_n, verified_count, missing_count}, ranks{state, status, verified_count, row_count, reason_codes}}`. 가격과 시가총액은 없다.
  - 코드: `UNIVERSE_SOURCE_NOT_SET`, `UNIVERSE_SOURCE_INVALID`, `AUTH_REQUIRED`, `SOURCE_TOO_LARGE`, `CANCELED`, `UNIVERSE_READ_FAILED`.
  - 실패해도 마지막 성공 읽기는 남고, `readStatus().failure`에 `{code, at}`이 기록된다. 로그아웃하거나 구글을 끄면 지워진다. 토큰 만료(`AUTH_REQUIRED`)로는 지워지지 않는다(옛 규칙).
  - 출처는 PrivateSubsetView 자신의 키(`universe-source`)다. 통합 시트(`sheetSource`)와 별개인 옛 동작을 그대로 둔다.
- `universeView`: `{prices(), priceBasis(), readStatus(), ranks()}`. PrivateSubsetView와 같은 계약이고 qgv·engines 내부용이다(`prices()`에는 가격이 있다).
- `universeRanks()`, `rankFor({company_id, ticker})`: 개인 M3 순위(2.1.1). 순위·품질·그룹·사유만 있다.
- 가격 탭(`SYNC`): 옛 PriceStore를 가격 view로 부른다. 결과는 수와 코드뿐이고, 실패한 쓰기에 붙던 Worker 응답은 뺀다.
  - `useTabs(event)`: `PriceStore.enable`. Prices_D·Prices_M을 만들고 이 기기에서 켠다.
  - `loadTabs(event)`: 두 탭을 RAM으로 읽는다.
  - `syncSymbols(event, symbols, '1d'|'1mo', {kind})`: `PriceStore.syncMany`, Worker 허용 목록만.
  - `syncUniverse(event)`: `PriceStore.syncUniverse`.
- `storeFacade`(qgv·engines 내부용): PriceStore 자리에 넣는 객체다. 모든 호출에 가격 view와 `fetch:false`를 넣는다. 이번 로그인과 이 시트에서 클릭으로 탭을 읽기 전에는 `monthEndCloses`·`dailyCloses`가 `{}`, `runnerHistories`가 null이다. sync·enable은 없다.
- `history(event, company, {range})`(`HISTORY`): TARGET 회사 id나 그 Worker 심볼을 받는다. 검증된 일별 이력(가격 포함)을 RAM에 두고 돌려준다. `held(company, {range})`로 다시 꺼낸다. 로그아웃하면 지운다. 코드: `OFF`, `HISTORY_UNAVAILABLE`, `REQUEST_INVALID`, `ORIGIN_UNAPPROVED`, `AUTH_REQUIRED`, `CANCELED`, Worker 코드.
- `quote(company)`: `{state:'OK', price, currency, source, read_at, as_of, time_status, freshness}` 또는 `{state:'NA', reason:'NO_DEVICE_PRICE'}`. 보관된 Universe 읽기를 먼저 보고, 다음으로 이미 있는 기기 DB의 저장 시세를 본다. 표시 전용이다.

## 6. 기기 저장: `IS2.store`

- 모든 읽기·쓰기는 그 자료를 가진 옛 모듈을 거친다. 쓰기는 `WRITE` 클릭 안에서만 하고 값을 동기로 돌려준다(백업만 비동기).
  - 클릭이 아니면 `CLICK_REQUIRED`다.
  - gated storage를 받은 옛 모듈이 클릭 밖에서 쓰면 `ACTION_REQUIRED`이고, 저장소는 그대로다.
- `KEYS`(옛 키 그대로, 노드 시험이 옛 상수와 대조한다):

  | 이름 | 키 | 주인 |
  | --- | --- | --- |
  | PERSONAL | investment.web.v1.personal | 관심 기업·그룹 |
  | SETTINGS | investment.web.v1.settings | AppLanguage |
  | PROFILES / PROFILES_V2 | investment.web.v1.profile-drafts(-v2) | DeviceProfiles |
  | PLAYBOOK | investment.web.v1.playbook | PlaybookScreen(TARGET v1 상태 포함) |
  | INVESTOR_STARS | investment.web.v1.investor-stars | PublicScreens·DeviceBackup |
  | BACKUP_RESTORED | investment.web.v1.backup-restored | DeviceBackup 복원 표시 |
  | V_HISTORY / V_HISTORY_V2 | investment.web.v1/v2.virtual-trading-v-scores | VirtualTradingVHistory |
  | SHEET_SOURCE | investment.web.v1.unified-sheet-source | GoogleSheetSetup |
  | UNIVERSE_SOURCE | investment.web.v1.universe-source | PrivateSubsetView |
  | WORKER_ORIGIN | investment.web.v1.private-history-origin | PrivateHistory·PriceStore |
  | PRICE_STORE_ENABLED | investment.web.v1.price-store-enabled | PriceStore |
  | DEVICE_DB | investment-device-actual-v1 | DeviceActual(IndexedDB) |

- 관심 기업(1.1.4): `prefs()`는 `{state:'OK'|'EMPTY'|'INVALID', value}`이고, 검증은 `DeviceBackup.preferences`다. `savePrefs(event, next)`는 읽을 수 없는 저장 값을 덮어쓰지 않는다(`PREFS_STORAGE_INVALID`, app.js 규칙). 잘못된 값은 `PREFS_INVALID`다.
- 가중치(2.2): `weights()`, `saveWeights(event, {id, name, weights, type_weights, gate})`, `PRODUCT_PRESETS`. 열린 프로필을 저장하면 다음 버전이 된다. 코드: `WEIGHTS_INVALID`, `WEIGHTS_STORAGE_INVALID`.
- 보유(6.1): `holdings()`는 `{state:'OK'|'EMPTY'|'NOT_AVAILABLE', reason, snapshot, source, as_of}`. DB가 없으면 `DEVICE_STORE_NOT_OPENED`이고, 읽기가 DB를 만들지 않는다.
- 플레이북: `playbook()`, `saveThesis(event, symbol, thesis, invalidation, ev)`, `saveHold(event, symbol, row)`, `saveRecord(event, row)`.
- 투자자 별표(2.3.1): `stars()`, `toggleStar(event, cik)`.
- 백업:
  - `backup.create()`: 늘 /4다(user objects 없음).
  - `backup.download(event)`.
  - `backup.restore(event, text)`: /1~/4를 받는다. /5는 `BACKUP_USER_OBJECTS_UNSUPPORTED`로 거절한다. 그 밖의 코드는 `BACKUP_INVALID`, `BACKUP_TOO_LARGE`, `BACKUP_RESTORE_FAILED`다. 보유가 없는 백업을 DB 없는 기기에 복원해도 DB를 만들지 않는다.
  - `backup.restored()`: 복원 표시(시각과 schema).
- V 기록(6.3): `vHistory()`는 `{v1, v2}`이고 읽기 전용이다.
- 출처와 주소: `sheetSource.has()/set(event, url)`, `universeSource.has()/set(event, url)`, `workerOrigin.has()/approved()/set(event, url)`. ID와 주소는 돌려주지 않는다. 코드: `SHEET_SOURCE_INVALID`, `UNIVERSE_SOURCE_INVALID`, `REQUEST_INVALID`.
- `storage`(engines 내부용 gated localStorage), `subscribe(fn, {signal})`(쓰기 뒤 키 이름, 예: `'PERSONAL'`).

## 7. 엔진: `IS2.engines`

- 옛 엔진을 바이트 그대로 쓰고, 옛 화면이 넘기던 인자를 그대로 넘긴다. 옛 화면 안에만 있던 연결 코드만 다시 썼다(Universe 읽기와 같은 방식). 노드 시험이 spy로 같은 함수·같은 인자를 확인한다.
- 점수는 공유 Page의 기기 결과(`qgv.forEngines`)다. 엔진이 저장하는 기록에는 `page.engine_v_source`를 남긴다. `page.v_source`가 아니다.
- 쓰기는 모두 클릭 안에서만 한다(`WRITE`, 사용자 시트에도 쓰면 `SYNC`). 저장소는 `store.storage`(gated)다. 가격은 가격 view와 facade로만 오간다.
- 반환값은 얼린 복사본이다. 가상매매 `stored`·`rehearse`의 결과만 옛 엔진 결과 그대로 돌려준다(`compare`가 다시 받는다). 가상매매 결과와 TARGET 세트 비교에는 가격과 가격 파생값이 있다. RAM 전용이고 `[data-ram-price]` 안에만 표시한다.

**TARGET v1 (`engines.target`, 2.1.7)** — 상태는 플레이북 저장소 안(`TargetV1Screen.readState/writeState`)에 있다.
- `state()`: 저장된 상태. 읽을 수 없으면 `TARGET_V1_STATE_INVALID`이고, 덮어쓰지 않는다.
- `basis({page})`: 지금 다시 읽은 공개 파일(`data.peek`, SecQgv2를 통과한 원본 JSON)의 입력 기준(`TargetV1Builder.inputBasis`). Page 점수의 파일과 as_of가 같을 때만 값이고, 아니면 null이다.
- `draft({date, basis, page})`: 쓰지 않고 초안만 만든다(`buildDraft`에 computed·inputs·universeCodes·existing·date·basis·cfg). Page에 결과가 없으면 `QGV2_NOT_READY`다.
- `build(event, {date, page, reset})` [WRITE]: 초안을 저장하고 카드 응답을 비운다. 응답이 있으면 `reset:true`가 있어야 한다(아니면 `TARGET_V1_ANSWERS_RESET`, 옛 버튼의 두 번 누르기).
- `blockers({date})`: 지금 다시 읽은 원본 파일로 `finalizeBlockers`를 돌린 결과(차단 코드, 확인 수).
- `finalize(event, {date, page})` [WRITE]: 원본 파일을 다시 읽어 모두 재검사한다. 결과 `outcome`은 다음 넷 중 하나다.
  - `FINALIZED`: 새 버전을 저장했다. 버전에 `v_source: page.engine_v_source.id`를 기록한다. #391이 병합되면 builder가 같은 값을 직접 쓰고, 값이 다르면 `V_SOURCE_MISMATCH`로 저장하지 않는다.
  - `BLOCKED`: `blockers`(코드 목록)와 `check`. 아무것도 쓰지 않는다.
  - `DRAFT_REGENERATED`: 입력 기준이 바뀌어 초안을 다시 만들었다(같은 종목의 응답만 유지, `carried`·`fresh`).
  - `RELOAD_REQUIRED`: 입력 기준이 바뀌었는데 Page 점수가 그 파일의 것이 아니다. 새로 고친 뒤 다시 확정한다.
- `answer(event, {symbol, answer, reason, date})` [WRITE]: 판정 기록 1건(`TV1-…`, 옛 형식 그대로)과 최신 응답. 결과는 `{symbol, answer, added, limits_ok}`. 코드는 builder 것이다(`DISAGREE_REASON_REQUIRED`, `TARGET_V1_NOT_SELECTED` 등).
- `ruleBDue(date)`, `selectRuleB(event, {date, page})` [WRITE]: R-B(규칙 지수) 선정. 결과 `state`는 `SELECTED`·`NOT_READY`(통과 종목 부족이나 한도 위반, 부분 시작 없음)·`NOT_DUE`·`QGV2_NOT_READY`이고, `SELECTED`일 때만 쓴다. 옛 화면은 열 때 이것을 자동으로 했다.
- `compare(event, {date})` [SYNC]: A·R-B·R-C·S&P 500 종가를 가격 탭에서 읽고, 빠진 끝부분은 Worker로 받아 덧붙인다(`PriceStore.dailyCloses` fetch:true, 가격 view). 결과는 `{compare, review}`이고 지수 값이 들어 있어 RAM 전용이다.
- T-PRICE(판정 채점용 가격):
  - `scoringPending()`: `{pending, tracked, confirm_text}`. `confirm_text`는 `TargetV1Screen.confirmText`이고 종목 기호만 들어 있다. 화면은 이 글로 사용자 확인을 받은 뒤 다음 함수를 부른다.
  - `syncScoringPrices(event)` [SYNC]: `PriceStore.syncMany(priceView, 기호, '1d', {kind:'TV1', allowlistOnly:true})`. `READY`일 때만 기호를 기기에 남기고(허용 목록 밖은 빼고) 채점 시계열을 RAM에 읽는다. 결과는 `{state, sync, scored}`(수와 코드). 할 일이 없으면 `NOTHING_PENDING`이다.
  - `refreshScoring()`: 추적 종목의 시계열을 facade로 읽어 플레이북 채점 RAM에 넣는다. 클릭으로 탭을 읽기 전에는 0이다.

**플레이북 (`engines.playbook`, 상세 화면 playbook, 6.1.x)**
- `facts(symbol, {date})`: 옛 조립 그대로다. 뉴스 목록을 공개 view로 먼저 읽고, `PlaybookScreen.prepareScores(scoreView, …)`, `heldSymbolsFor`, `DeviceActual.ramView`, `factsFor`를 부른다. 점수는 공유 Page 결과(Page 프로필)다. `actual_pct`는 기기 가격에서 나온 비중이라 표시 전용이다. 옛 화면 모듈 `CompanyScreen`은 불러오지 않으므로, `factsFor`의 v1 Q·G 대체값(sec-qg-factors.json)은 없고 Q·G는 v2 결과에서만 온다.
- `judge({symbol, situation, date})`: openPanel의 판정 단계만 옮겼고, 쓰지 않는다. 기기 기록의 무효화 사건·보류·확인일, `MacroLights.current()`, `PlaybookEngine.evaluate`, R1_FILING 제한(사건 등급이 EVIDENCE가 아니면 막음)을 거친다. `situation`이 없으면 `facts()`를 쓴다. 결과는 `{symbol, date, situation, judgement, code}`다.
- `record(event, judged)` [WRITE]: openPanel이 열 때 쓰던 발생 기록(후보 신호, 구조적 뉴스 E4, 13F 기관 3곳 이상 전량 이탈 E4)을 `judge()` 결과로만 쓴다(`JUDGEMENT_UNKNOWN`). 그날 그 종목의 발생 기록(코드·사유)을 돌려준다.
- `due(date)`: E5 확인일이 된 기록. `limits(rows, cash)`: 16절 한도(`PlaybookEngine.portfolioLimits`).

**가상매매 (`engines.virtual`, 6.1.5·6.2·6.3)**
- `stored({reportDate, signal})`: 옛 보고서 화면이 열 때 하던 실행이다. `VirtualTradingRunner.run(priceView, {config, catalog, reportDate, signal, fetch:false})` 뒤 `PlaybookScreen.ingestRunner`를 부른다.
  - 시작일 전: `NOT_STARTED`. 요청 0건.
  - 개인 이력 꺼짐, 승인된 Worker 주소 없음, 구글 미로그인: `NOT_AVAILABLE`, 사유 `OFF`·`REQUEST_INVALID`·`ORIGIN_UNAPPROVED`·`AUTH_REQUIRED`. 요청 0건.
  - 준비됨: 종목마다 이번 로그인의 RAM 이력이나 클릭으로 읽은 가격 탭(facade)을 쓰고, 없으면 `PRICE_NOT_FETCHED`다. 공개 파일(전진 검증 원장, 분류)만 읽고 비공개 요청은 0건이다.
  - 세트 B/C/D는 사용자 장부 시트에서 오므로 P1에는 없다. P2-6에서 붙일 대응(옛 mount 안의 연결, virtual-ledger-sheets.js:696-699): 시트 읽기는 클릭으로 `VirtualLedgerSheets.load(session, id)`, 실행 옵션은 `{sets:{SET_A~D: active(meta,k)의 target_weights 또는 null}, user_target, flags}`, 결과 반영은 `apply(result, sheet)`, 비교 표의 `defs`는 `definitions(sheet, catalog)`다.
- `compare(result, {config, basis, defs})`: 비교 표(`VirtualTradingCompare.build`). 세트가 A 하나뿐이면 `COMPARE_NEEDS_TWO_SETS`다. 이름표는 세트 kind이고 문구는 P2-6이 정한다.
- `forward()`: 9.2 전진 검증. 공개 원장의 일별 Q·G 요약, 평가 구분, calc_version 구간(잇지 않음), 운영 증거다. 가격은 없다. 원장이 없으면 `NOT_PUBLISHED`다.
- `rehearse({reportDate, page, signal})`: 리허설. Page의 Q·G 행으로 RAM에서만 돌리고 기록하지 않는다(fetch:false).
- `run()`: 항상 `NOT_IN_P1`이다. 기록 실행(Worker 이력, V 기록, 장부 시트 쓰기, 일일 보고서 모델)은 보고서 모델(daily-report.js 미반입)과 V 기록 시점(D-21)을 P2-6에서 정한 뒤 붙인다.

**매크로 (`engines.macro`, 4.1.4)**
- `current()`: `MacroLights.current()`. 공개 자료 세대마다 한 번 `MacroLights.setPublic(data.screens())`를 부른다(옛 app.js의 시작·적용 시점). 재판정은 세대를 바꾸지 않는다. 기기 신호등(SPY Worker)은 P2-4의 클릭이다.

## 8. V 출처 전환점(중앙 V가 게시될 때 바꿀 곳, 전부)

1. `qgv.js`: `OFFICIAL_READER`(유일한 스위치)를 설정하고 `centralPage`를 구현한다. 중앙 V일 때는 Q·G도 게시본에서 읽고, sec-qgv2.json과 섞지 않는다.
2. `data.js`: `FILES`에 게시 파일을 넣고 엄격 리더를 붙인다.
3. Pages 가드 허용 목록에 넣는다(Main).
4. `TargetV1Builder.finalize`가 `v_source`를 `DEVICE_TEMPORARY`로 직접 박는다(#391). 옵션을 추가해야 한다(Main이 #391에 요청). #391 병합 전에는 `engines.js` finalize가 같은 값을 버전에 넣고, 병합 뒤에는 builder 값이 엔진 값과 같은지만 확인한다.
5. 엔진의 중앙 모드 계약: `forEngines`는 늘 기기 결과를 준다. 그래서 엔진 기록(TARGET 버전의 `v_source`)은 `engine_v_source`(지금은 DEVICE_TEMPORARY)를 남긴다. 중앙 행을 computed 모양으로 바꾸는 어댑터를 둘지, 엔진은 DEVICE_TEMPORARY로 둘지는 그때 정한다. 바꿀 곳은 `qgv.js`의 `engine_v_source`와 `forEngines`, `engines.js` finalize다. TARGET 카드 판정 기록과 R-B 기록에는 출처 필드가 없다(옛 형식 그대로, 모두 기기 V).
6. `OFFICIAL_CENTRAL` 문구는 초안이다. 전환할 때 사용자 확인을 받는다.

## 9. 사용자 결정 대기 항목

- V 기록(D-21)을 클릭할 때만 남길지
- 플레이북 판정 기록: 옛 앱은 판정할 때 기록했고, 새 앱은 `record(event)`를 누를 때만 기록한다
- R-B(규칙 지수) 선정: 옛 화면은 열 때 자동으로 기록했고, 새 앱은 `selectRuleB(event)`를 누를 때만 기록한다
- 가상매매 세트 B/C/D(사용자 장부 시트 읽기)와 기록 실행(`virtual.run`): P2-6 보고서 모델과 함께 정한다
- IndexedDB 'market'에 시세를 계속 저장할지(계획 §2.1과 충돌)
- 일일 보고서·보고서 모델(P2-6)
- 로그인 두 번 누르기(준비 → 로그인)
- 중앙 V 모드의 엔진 계약
- 백업 /5(user_objects)는 고정 코드로 거절한다
- 임시 V 기준 순위 문구
- Universe 출처를 통합 시트와 따로 둘지(지금은 옛 동작대로 따로 둔다)
- 구글 켬/끔을 기기에 저장할지(P1은 sheetSettings를 쓰지 않는다. 준비 버튼이 그 페이지에서 켠다)
