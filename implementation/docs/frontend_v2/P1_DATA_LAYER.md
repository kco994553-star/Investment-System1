# 프론트 v2 P1 자료·계산 층: P2 레인용 API 계약

P2 화면 레인이 쓰는 함수, 기록 모양, 사유 코드, 지켜야 할 규칙을 정한다. 근거는 P1 구현 사양(Main 결정 2026-10-24)과 같은 날 오후의 소유자 결정(P1 동작, 11절)이다. 기능 번호는 사양 v1.0 번호(1~9)다.

## 1. 파일과 화면 등록

- 위치는 `implementation/src/investment_system/product/web_app/`이고, 전역은 `IS2` 하나다.
- 불러오는 순서(P2-1a, 1.1절)
  - `index.html`(첫 화면만, 모두 `defer`): P0 기반(core·shell·parts) → `loader.js` → 레인 파일 8개(`screen-qgv/technical/macro/news/portfolio/prompts/tree/lab.js`) → P0 화면 → `boot.js`. web_app 파일만 둔다(옛 모듈이 있으면 빌드 실패).
  - 첫 그림 뒤 `loader.js`의 `LOAD_ORDER`: 옛 모듈 59개(web_assets 바이트 그대로, 빌드 A안. 설계 57개 + 백업 /5 검증기인 `chart-workbench.js`·`macro-cycle-ring.js`) → `action` → `data` → `prices` → `store` → `qgv` → `engines`.
  - 레인은 index.html도 `LOAD_ORDER`도 고치지 않고 자기 파일만 채운다.
- 등록:
  - `IS2.register(id, render)`: 자리표시를 실제 화면이 대신한다. 실제 화면을 두 번 등록하면 `SCREEN_DUPLICATE`다.
  - `IS2.registerDetail(name, render)`: `#/detail/<name>`에 쓴다. 이름은 `IS2.DETAILS`에 있어야 한다(`DETAIL_UNKNOWN`).
- `render(route)`는 Node를 동기로 돌려준다.
  - 비동기 값은 자리를 먼저 그리고 나중에 채운다.
  - `route.signal`은 렌더마다 새로 만드는 AbortController의 signal이다. 다음 렌더 때 abort된다.
  - 모든 `subscribe(fn, {signal: route.signal})`는 abort되면 저절로 풀린다. 늦게 온 값은 `signal.aborted`를 보고 버린다.
- 오류는 값이 들어가지 않은 고정 코드로만 던진다. 셸이 `e.message`를 화면에 그대로 띄우기 때문이다.
- 페이지를 열기만 해서는 아무것도 읽지 않는다. 공개 파일은 화면이 `IS2.data.ready()`나 `IS2.qgv.page()`를 부를 때 처음 읽는다.

### 1.1 첫 화면과 불러오기(P2-1a, 소유자 결정 2026-10-24)

- **셸이 먼저다.** `boot.js`가 셸과 첫 화면을 그리고(`IS2.start()`), `IS2.load()`를 부른다. 셸은 첫 렌더 때 표시 `is2-shell-render`를 남기고, 그 프레임이 그려지면 `IS2.firstPaint`를 푼다(애니메이션 프레임 2개 뒤, 브라우저가 알려 주면 first-contentful-paint 뒤. 표시 `is2-first-paint`).
- **나머지는 첫 그림 뒤.** `loader.js`가 `IS2.firstPaint`와 한가한 틈(requestIdleCallback, 없으면 다음 틱)을 기다린 뒤 `LOAD_ORDER`의 파일을 한꺼번에 넣는다. 숨은 페이지는 그림이 없으므로 바로 넣는다. 첫 그림이 3초 안에 오지 않아도 넣는다.
  - 같은 출처의 평범한 파일 이름만 `<script src>`로 넣는다. `async=false`라 내려받기는 동시에, 실행은 목록 순서대로다. 인라인 코드·eval은 없고 CSP는 그대로다.
  - `LOAD_ORDER`가 하나뿐인 불러오기 목록이다. 빌드(`build_web_app.py` A안 규칙)와 시험 도우미(`web_app_reuse.js`)가 이 리터럴을 읽는다. 따옴표 이름만 쓴다(그 밖이면 빌드 실패).
- **`IS2.ready`**: 모든 파일이 실행되고 층이 자리를 잡으면(`IS2.action`과 다섯 이름공간) 풀린다. 표시 `is2-ready`. 실패하면 목록 순서로 첫 실패 파일을 담아 `LOADER_FAILED <파일>`(`err.code`·`err.file`)로 거절된다. 파일이 오지 않음, 실행 중 오류, 이름공간을 놓지 않음이 실패다. 다시 시도하지 않는다(새로고침이 한다). 표시 `is2-load-failed`. `IS2.loadState()`는 `WAITING` → `LOADING` → `READY`/`FAILED`다.
- **그전의 `IS2.data`·`qgv`·`prices`·`store`·`engines`는 대리 객체다.** 층과 같은 멤버를 갖는다(`loader.js` API, 노드 시험이 실제 층과 맞춰 본다).

  | 멤버 종류 | 준비 전 | 실패 뒤 |
  | --- | --- | --- |
  | 약속을 돌려주는 함수(`qgv.page()`, `data.ready()`, `store.marketQuotes.count()` 등) | `IS2.ready`를 기다렸다가 층을 부른다 | `LOADER_FAILED <파일>`로 거절 |
  | 행동(첫 인자가 사용자 이벤트) | `LAYER_NOT_READY`를 던진다. 관문은 전달 중인 이벤트가 필요해 클릭을 기다리게 할 수 없다. **화면은 `IS2.ready` 전에는 행동 버튼을 꺼 둔다.** | `LOADER_FAILED <파일>`을 던진다 |
  | 동기 함수·값(`prices.status()`, `qgv.rankLabel()`, `data.FILES` 등) | `IS2.NOT_READY`(`{state:'NOT_READY', reason:'LAYER_NOT_READY'}`) | `IS2.LOAD_FAILED`(`reason:'LOADER_FAILED'`) |
  | `subscribe(fn, {signal})` | 맡아 두었다가 준비되면 층에 붙인다(그전에 signal이 abort되면 버린다) | 아무것도 붙이지 않는다 |

  - 층 파일이 실행되면 IS2의 대리 객체를 진짜로 바꾼다. 화면이 미리 잡아 둔 대리 객체도 준비 뒤에는 모든 호출을 층으로 넘긴다. 실패하면 대리 객체를 IS2에 다시 놓는다(반쯤 만든 층에 닿지 않게).
  - 옛 모듈과 engines에만 넘기는 view·결과(`prices.priceView`·`storeFacade`, `store.storage`, `qgv.scoreView`·`forEngines`·`engineInputs`)는 대리 객체에 없다.
- **화면 규칙**
  - 화면 파일은 불러올 때 층을 건드리지 않는다(노드 시험). 층 값은 렌더 때 읽는다.
  - 렌더는 기다리지 않는다. 자리를 먼저 그리고(`parts.pending`) 약속 함수의 값이 오면 채운다(1절). 동기 값이 `IS2.NOT_READY`면 연결 전으로 그린다.
  - 행동 버튼은 `IS2.ready`가 풀린 뒤 켠다. 실패하면 꺼 둔 채 새로고침을 안내한다.
  - 기기 칩은 `IS2.ready` 전까지 '연결 전'이다(셸).
- **목표와 시험**(390×844, 150 ms RTT·1.6 Mbps·CPU ×4, 콜드 캐시): 첫 화면 2,000 ms 이하, 첫 전송 100 KB 이하. `tools/web_app_first_paint_browser_test.js`가 3번 재어 중앙값으로 확인한다(12절). 다른 화면 PR은 이 구조 위에서 만든다. 첫 화면 파일을 늘려 목표를 넘으면 이 시험이 막는다.
  - 측정(2026-10-24, Pages처럼 gzip, 3번 중앙값): 첫 화면 848 ms(3번 883·848·813, FCP 중앙값 840), 첫 전송 24.4 KB(18건), `IS2.ready` 7,190 ms, 그때까지 888.1 KB(85건), 글꼴까지 모두 1,254.2 KB. 압축 없이: 948 ms, 48.2 KB, 13,493 ms, 2,430.4 KB. 결정 전 검토 측정은 첫 화면 4,119 ms, 전송 569 KB였다.
  - 남은 비용: 첫 그림 뒤 층이 준비될 때까지 7초쯤 걸린다. 글꼴 3개(620 KB, 첫 그림 때 이미 내려받는 중)가 같은 대역폭을 쓴다. 줄일 방법(제안, 결정 필요): 손글씨 글꼴(375 KB)을 `font-display: optional`로 바꾸거나 첫 화면 글자만 담은 작은 부분집합을 먼저 쓰기, 화면이 쓰는 옛 모듈만 그 화면에서 불러오기(P2 레인별 목록).

## 2. 모든 화면이 지킬 규칙

- **클릭 규칙**
  - 비공개 요청(시트·Worker·OAuth)과 기기 저장 쓰기는 첫 인자로 받은 **진짜 사용자 이벤트**로만 실행한다.
    - 조건: window의 진짜 이벤트이고(`isTrusted`·`type`·`eventPhase`를 window의 원래 접근자로 읽는다), 형식이 click 또는 Enter/Space keydown이다.
    - **버튼은 click 이벤트만 넘긴다.** keydown은 활성화 동작이 없는 요소(예: `tabindex`를 준 div)에서만 받는다. 버튼, 링크(href), summary, input은 같은 키 누름을 브라우저가 진짜 click으로 한 번 더 보낸다(폼 안 input의 Enter는 암묵 제출로 기본 버튼을 누른다). 그래서 그런 요소의 keydown과 키를 누르고 있을 때 오는 자동 반복 keydown(`repeat`)은 `CLICK_REQUIRED`다. 한 번 누르면 action 하나다.
    - 그 이벤트가 **지금 전달 중**이어야 하고(처리기 안), 브라우저가 알려 주면 사용자 활성화(`navigator.userActivation.isActive`)도 있어야 한다.
    - 클릭 처리기 안에서 기다리지 말고 바로 부른다. `login`은 같은 틱이어야 한다.
  - `CLICK_REQUIRED`가 되는 경우:
    - 이벤트가 없음, 합성(`dispatchEvent`, `el.click()`), `{isTrusted:true}` 같은 일반 객체.
    - 위조(`Object.create(Event.prototype, …)`, isTrusted를 속이는 Proxy).
    - **submit 이벤트.** 브라우저는 `form.requestSubmit()`과 스크립트의 `submitter.click()`이 만든 submit도 trusted로 표시한다. 폼은 제출 버튼의 click 이벤트를 넘긴다.
    - 저장해 둔 이벤트를 나중에 다시 쓰는 경우(타이머, 다른 처리기, 다른 kind).
  - **한 이벤트로는 최상위 action을 하나만 시작한다(소유자 결정 2026-10-24).** 같은 이벤트로 두 번째 action을 시작하면 `ACTION_ALREADY_STARTED`다(그 이벤트가 아직 전달 중일 때. 전달이 끝났으면 `CLICK_REQUIRED`). 한 클릭에 두 함수를 부르지 않는다.
  - 그 action 안의 다음 단계(중첩 실행)는 부모 action의 signal을 내민다: `run(event, kind, fn, {parent: signal})`. 같은 이벤트로 시작한 부모가 아직 진행 중일 때만 통과하고, 부모가 취소되면 함께 끝난다. signal 없이 부르면 위 규칙대로 거절된다. 예: `engines.target.syncScoringPrices` → `prices.syncSymbols(event, …, {parent: signal})`.
    - 중첩 실행은 부모가 갈 수 있는 곳까지만 간다. 부모와 같은 kind이거나, 기기 저장을 쓰는 부모(`PUBLIC_REFRESH` 말고 모두) 아래의 `WRITE`만 된다. `PUBLIC_REFRESH` 아래에는 아무것도 중첩하지 않고, `WRITE` 클릭 아래의 `SYNC`도 안 된다. 어기면 `ACTION_KIND_NOT_COVERED`다.
- **RAM 가격 표시**
  - 기기 가격과 가격 파생값(시총, EV, 수익률, 배수, 내재 성장, 월말 종가)은 RAM에만 둔다.
  - 화면에는 `[data-ram-price]` 요소의 글자로만 낸다. 속성, 입력 value, 제목, 저장소, 콘솔, URL에는 넣지 않는다.
  - 값을 내주는 곳은 `prices.quote()`, `prices.history()/held()`, 가상매매·세트 비교 결과뿐이다.
  - 시험 도우미: `tools/web_app_test_site.js`의 `assertRamOnly(page, sentinels)`.
- **NA 규칙**
  - 값이 없으면 null이고 사유 코드가 반드시 붙는다. 0이나 평균으로 채우지 않는다(`?? 0`, `|| 0` 금지).
  - 글은 `IS2.qgv.reasonText(code, en)`로 만든다.
- **V 출처**
  - 점수 행: 화면 글자에는 `row.source_label`(지금은 '임시 V')만 쓴다.
  - 엔진 결과: V가 든 결과에는 `v_source`(출처 id)가 있다. 글자는 `IS2.qgv.V_SOURCES[x.v_source].ko`로 만든다. `v_source`가 null이면 출처 기록이 없는 기기 V다(옛 초안, 화면이 넘긴 상황).
  - 출처 낱말('임시 V', '공식 V', `DEVICE_TEMPORARY`, `OFFICIAL_CENTRAL`, 안내 문구)은 `qgv.js`에만 있다. 소스 검사가 다른 파일의 코드에서 막는다.
- **그 밖의 금지**
  - `console.*`, `innerHTML`, 주문·거래 기능과 문구.
  - `[style]` 속성과 style 문자열. CSP가 조용히 버리므로 `h(tag, {style:'…'})`는 `STYLE_INVALID`를 던진다. 막대는 SVG 속성이나 클래스 단계로 그린다.
  - Universe504는 universe-codes.json의 고정 504코드 목록이다. 다른 성격으로 설명하지 않는다.

## 3. 클릭 관문: `IS2.action`

- `run(event, kind, fn, {parent})`: `fn(signal)`을 같은 틱에 부르고, fn이 끝나거나 `cancel(kind)`될 때까지 그 kind를 진행 중으로 둔다. 화면은 직접 부르지 않고 아래 함수들에 event를 넘긴다. 이벤트 조건과 한 이벤트 한 action 규칙, `parent`는 2절 클릭 규칙이다.

  | kind | 갈 수 있는 비공개 목적지 | 기기 저장 쓰기 |
  | --- | --- | --- |
  | `PUBLIC_REFRESH` | 없음(공개 파일만) | 안 됨 |
  | `LOGIN` | GIS 스크립트·OAuth | 됨 |
  | `UNIVERSE_READ` | 저장한 시트의 values GET | 됨 |
  | `HISTORY` | Worker `/history` | 됨 |
  | `SYNC` | Worker, 저장한 시트의 읽기·추가·갱신·탭 목록 | 됨 |
  | `WRITE` | 없음 | 됨 |

  - 시트는 이 기기가 저장한 시트(통합 시트, Universe 탭 출처)만 간다. 다른 시트와 새 시트 만들기는 `DESTINATION_UNKNOWN`이다.
  - 비공개 요청은 문자열 URL만 받는다. Request 객체 등은 `DESTINATION_UNKNOWN`이다.
- 클릭 밖의 쓰기와 요청은 이렇게 막힌다.
  - 비공개 요청: `CLICK_REQUIRED`. 알 수 없는 목적지는 `DESTINATION_UNKNOWN`이다.
  - 옛 모듈의 저장 쓰기: `ACTION_REQUIRED`. 저장소는 그대로 남는다.
  - 둘 다 `blocked()` 수가 늘어난다.
- **허용 범위는 페이지 전체다.** action이 진행 중인 동안에는 그 클릭과 무관한 코드도 그 kind의 목적지에 가고 저장소에 쓸 수 있다(사양이 정한 관문 방식). 그래서 다음을 지킨다.
  - 오래 걸릴 수 있는 단계에는 끝이 있다. GIS 준비는 30초 뒤 `PREPARE_TIMEOUT`, `cancel(kind)`는 곧바로 관문을 닫는다.
  - P2 레인은 `IS2.action.view()`로 view를 새로 만들지 않는다. view의 IndexedDB는 쓰기 action 중에 DB를 만들 수 있다.
- **관문이 막는 범위.** 관문은 view만 받는 옛 모듈의 호출을 막는다. 진짜 window를 쥔 페이지 코드까지 가두는 장치는 아니다. 그래서 P2 화면 코드는 저장소(`localStorage`·`sessionStorage`·`indexedDB`)를 직접 쓰지 않는다. 소스 검사가 P1 층 밖에서 막는다.
- IndexedDB는 이미 있는 DB(`stores()`)나 쓰기 클릭 안에서만 연다. 읽기는 DB를 만들지 않는다. 거절 코드 `DEVICE_STORE_NOT_OPENED`는 '아직 저장된 것 없음'이라는 뜻이다. `stores()` → `{supported, available, names}`.
  - 쓰기 트랜잭션(`readwrite`)도 쓰기 action 안에서만 연다. 밖에서는 `ACTION_REQUIRED`다(이미 있는 DB에도 클릭 없이 쓰지 않는다).
  - 버전 변경(DB가 그사이 지워져 새로 만들어지는 경우 포함)도 쓰기다. 쓰기 action 밖이거나 읽기 전용 view(점수 경로)면 중단한다(blocked 수가 는다).
  - view가 내준 IndexedDB 객체에서 닿는 객체는 모두 관문을 거친 객체다. 요청의 `source`·`transaction`·`result`, 커서, 색인, 처리기가 받는 이벤트의 `target`이 그렇다. 그래서 옛 모듈이 받은 객체를 거쳐 관문 뒤로 가지 못한다.
  - **기기 시세 기록은 멈췄다(소유자 결정 2026-10-24, DC-18).** `STOPPED`: DB `investment-device-actual-v1`의 `snapshots` 저장소 안 기록 `market`(저장된 시세)과 `market-import-history`(가져올 때마다의 시세·환율). 계획서가 'market 저장소'라고 부른 것은 별도 저장소가 아니라 이 두 기록이다(device-actual.js:9-10).
    - 쓰기: 클릭 안에서도 `MARKET_STORE_STOPPED`(blocked 수가 는다). 그 기록을 다른 기록과 한 트랜잭션에 묶어 쓰는 옛 쓰기는 트랜잭션째 실패한다.
      - `DeviceActual.applyMarketImport`(시세 가져오기).
      - `DeviceActual.mount` 화면의 저장·JSON 가져오기·'기기 보유 삭제'. 보유(`actual`)와 시세 기록을 늘 함께 쓰거나 지운다. 게다가 mount는 진짜 window(`host.ownerDocument.defaultView`)에서 돌아 관문을 거치지 않는다. 그래서 새 앱은 이 둘을 다시 쓰지 않는다(소스 검사가 `DeviceActual.mount*`·`applyMarketImport` 호출을 막는다).
      - 보유만 쓰는 길은 옛 `DeviceActual.restoreHoldings`다(`actual`만 쓴다, 백업 복원이 이미 쓴다). P2-6의 보유 저장은 이것으로 store에 붙인다. 손으로 넣던 시세·환율은 새 앱에 둘 곳이 없다(11절 아직 정할 것).
    - 읽기: 없는 기록으로 읽힌다(없는 키로 바꿔 묻는다). 그래서 `DeviceActual.ramQuote`·`ramView`, `DeviceValuation.deviceQuote`, `QgvScores.collectQuotes`가 저장된 시세를 쓰지 않는다. 기기 V는 RAM 가격(Universe 탭 읽기, 가격 탭)만 쓴다.
    - 그 기록에 닿을 수 있는 범위 질의·커서·색인·`clear()`와, 그 저장소 지우기·이름 바꾸기는 거절한다(`MARKET_STORE_STOPPED`).
    - 이미 저장된 것은 저절로 지우지 않는다. 지우는 길은 `store.marketQuotes.clear(event)` 하나다(7절). `stoppedRecords.count()`/`clear(signal)`은 그 뒤의 구현이고, `clear`는 진행 중인 WRITE action의 signal만 받는다.
    - 옛 화면(아직 게시 중)은 P3 전환 때까지 계속 쓴다.

## 4. 공개 자료: `IS2.data`

- `FILES` 20개
  - 세대 묶음: macro-screen, sec-13f-changes, sec-filing-windows, sec-qg-factors, company-types-pricefree, company-classification, sec-qgv2, sec-public-inputs, dart-financials, macro-evidence, 목록 3개(sec-disclosures, news-signals, dart-disclosures), sec-universe-shares
  - 정적: actual-catalog, entities, company-names-ko, universe-codes, sec-valuation-inputs, forward-validation-ledger
- 모든 view가 `strictFetch` 하나로 읽는다.
  - 같은 출처, `FILES`만, GET만, 2 MiB 상한.
  - credentials omit, redirect error, no-referrer.
  - HTTP 상태는 그대로 둔다.
  - 오류: `PUBLIC_FILE_UNKNOWN`, `PUBLIC_FILE_METHOD`.
  - 2 MiB를 넘는 답은 원래 상태 코드에 빈 본문으로 넘긴다. 리더는 이를 내용이 잘못된 파일로 판정한다(`FAILED`/`INVALID`, 네트워크 오류가 아님).
- `ready()`
  - 첫 호출에 `DataRefresh.load`를 부르고 publication을 돌려준다. 이후 호출은 같은 Promise를 받는다.
  - 읽기 모듈이 빠져 있으면 `READER_MISSING`이다. 가벼운 경로로 빠지지 않는다.
- `get(name)`: 현재 세대의 검증된 값 또는 null. `sec-qgv2.json`은 Qgv2Inputs 출력이다. `screens()`는 묶음 전체이고 엔진용이다.
- `state(name)` → `{state:'OK'|'NOT_PUBLISHED'|'FAILED'|'NOT_READ', why, as_of, text}`
  - why: `INVALID`, `NETWORK`, `HTTP`, `SCHEMA_NEWER`, `READER_MISSING`.
  - 미게시(404)와 읽기 실패는 다른 문장을 쓴다.
- `list('sec'|'news'|'dart')`, `shares()`, `financials()`: 세대마다 한 번 읽고 모든 화면이 함께 쓴다.
- `static(name)`: 정적 파일을 페이지당 한 번 읽는다. 값 또는 null이고, 사유는 `state(name)`에 있다. 실패한 읽기는 남기지 않는다. 다음 호출이 다시 읽는다(옛 app.js와 같음).
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
  - 가격은 RAM에 있는 것만 쓴다: 클릭으로 읽은 Universe 탭, 가격 탭, RAM의 Worker 종가. 기기 DB에 저장된 시세는 읽지 않는다(DC-18, 3절 STOPPED).
- 접근 함수
  - `rankLabel(x, en)`: 순위 옆에 붙이는 글. x는 Page, 미리보기, 행, V 출처 id다. 기기 Page와 미리보기는 늘 '임시 V 기준 순위 · 공식 순위 아님'이다(소유자 결정 2026-10-24, Main 결정. 옛 화면도 '공식 순위 아님'이라고 쓴다). 모르는 출처도 공식이라고 부르지 않는다. Page와 미리보기에는 같은 글이 `rank_label`로 들어 있다. 중앙 V 문구는 초안이다.
  - `rows(page, {scope:'ALL'|'UNIVERSE'|'TARGET'})`: QgvScores 순서 그대로 준다. 정렬, 모집단, 분류 필터, 레이더는 P2-2가 옛 함수(LeaderboardScreen, StatRadar `compute(spec,{result})`)로 붙인다.
  - `row(page, idOrCode)`, `coverage(page)`(수만).
  - `preview(page, weights, {typeWeights, gate})`: 개인 가중치다. 결과는 늘 `weights:'PERSONAL'`, `v_source` 임시 V이고 공식 순위가 없다.
    - 2.2 개인 계산과 같은 호출이다(device-profiles.js). preset 없이, 그 가중치 프로필의 `gate`를 넘긴다(null이면 기본값 켬). 저장된 프로필의 gate를 꼭 넘긴다.
  - `isPage(page)`: 이 접근자가 만든 Page인지.
  - `setProfile({preset, gate})`(RAM만), `profile()`, `constants()`(2.5 트리용), `subscribe(fn(why), {signal})`. why는 DATA·PRICES·DEVICE·PROFILE이다.
  - `reasonText(code, en)`, `V_SOURCES`, `vSource()`.
- `forEngines`, `engineInputs`, `scoreView`는 engines 전용이다(소스 검사로 막는다).

```
Page { v_source{id,ko,note}, engine_v_source{…}, rank_label, state: READY|NO_DATA|DATA_FORMAT_NEWER|READ_FAILED, reason,
  as_of, calc_version, type_scope, profile_id, preset, gate, generation, basis_id,
  price_basis{kind:'DEVICE_RAM', connected, source, read_id, read_at, time_status: CONFIRMED|UNCONFIRMED|PARTIAL|null, freshness, times[]},
  identities{state: OK|NOT_AVAILABLE, reason: null|CATALOG_NOT_AVAILABLE, count} | null, coverage, rows[] }
RowRecord { id, ticker, code, record, scope: UNIVERSE|OUTSIDE_UNIVERSE, target, reference_only, source, source_label,
  score{total,q,g,v}, na_reason{total,q,g,v,rank}, rank{official, personal, qg_reference_order, group, of, weights: OFFICIAL|PERSONAL},
  coverage{v_factors{n,total:5,missing,required_ok}, axes{Q,G,V}, factors{available,total}, states, v_inputs_missing},
  flags, value_trap_gate, v_excluded, types{selected,reason}, row_state, acquired_at, fiscal_year_end, profile, source_reason_codes }
```

- 기기 Page는 기기 시세로 계산하므로 `v_source`와 모든 행이 늘 임시 V다. 계산 도중 스위치가 바뀌어도 같다.
- `identities`: 기업 목록 파일을 못 읽으면 `NOT_AVAILABLE`/`CATALOG_NOT_AVAILABLE`이고 TARGET 행이 없다. 다음 `page()`가 다시 읽는다. 결과가 없는 Page는 null이다.
- Page와 행에는 가격과 가격 파생값이 없다. 빠지는 것은 quotes, quote_meta, 월말 종가, EV, 수익률, `detail`, `reference_range`다.
- `read_at`은 기기가 시트를 읽은 시각이고 가격 시각이 아니다.
- `v_factors`는 `TargetV1Builder.vFactors` 값이다.

## 6. 가격: `IS2.prices` (클릭 때만 요청, RAM에만 보관)

- `status()`: 코드와 수만 준다. 가격, 시트 ID, Worker 주소는 없다.
  ```
  { google{enabled, ready, connected, pending, preparing, error}, sheet{set}, universe_source{set}, store (+tabs_loaded{daily, monthly}), universe{state, read_at, failure}, worker{state}, history{held} }
  ```
- `subscribe(fn, {signal})`: 로그인, Universe 읽기, 가격 탭이 바뀌면 알린다. 셸 기기 칩도 이것을 쓴다.
- 로그인 [LOGIN]: 두 번 누른다(소유자 결정 2026-10-24: 지금은 유지. P2-1에서 iOS Safari·안드로이드 Chrome 실측 뒤 한 번으로 줄일 수 있으면 줄인다).
  - `prepare(event)`: 세션을 켜고 GIS를 준비한다. 30초 안에 끝나지 않으면 `PREPARE_TIMEOUT`, 취소되면 `CANCELED`다. 늦게 끝난 준비는 다음 로그인 클릭이 쓴다.
    - 같은 클릭 안에서 '구글 켬'을 기기 DB에 저장한다(옛 로그인 클릭과 같음, google-sheet-setup.js:45). DB가 없으면 이 클릭이 만든다. 저장이 실패해도 로그인 준비는 계속한다.
  - `login(event)`: 클릭 안에서 동기로 토큰을 요청한다.
  - `logout(event)`: 메모리 토큰을 지운다. 저장된 켬/끔은 그대로 둔다(옛 연결 해제와 같음).
  - `deviceSettings()`: 기기 DB가 있을 때만 저장된 켬/끔을 읽는다. 저장된 '켬'은 세션을 켠다(표시만, 요청 없음). GIS 스크립트는 클릭 안에서만 받으므로 페이지를 열 때마다 준비 탭은 필요하다.
- `readUniverse(event)` [UNIVERSE_READ]
  - `PrivateSubsetView.mount` 클릭 처리와 같은 호출을 같은 순서로 부른다.
  - 공개 주식수는 읽은 시각 기준으로 다시 판정한다.
  - 결과: `{state, read_id, read_at, inputs, config_status, selection{…수}, ranks{…수}}`.
  - 코드: `UNIVERSE_SOURCE_NOT_SET`, `UNIVERSE_SOURCE_INVALID`, `AUTH_REQUIRED`, `SOURCE_TOO_LARGE`, `CANCELED`, `UNIVERSE_READ_FAILED`.
  - 로그아웃하면 지워지고, 토큰 만료로는 남는다.
- `universeRanks()`, `rankFor({company_id, ticker})`: 개인 M3 순위(2.1.1). 순위와 사유만 있고 시총은 없다.
- 가격 탭 [SYNC]: 결과는 수와 코드뿐이다.
  - `useTabs(event)`, `loadTabs(event)`.
  - `syncSymbols(event, symbols, '1d'|'1mo', {kind, parent})`: Worker 허용 목록만. 다른 action의 다음 단계로 부를 때 `parent`에 그 action의 signal을 넘긴다.
  - `syncUniverse(event)`.
- `history(event, company, {range})` [HISTORY]와 `held(company, {range})`: 검증된 일별 이력이다. RAM에만 있고 가격을 포함한다.
- `quote(company)` → `{state:'OK', price, currency, source, read_at, as_of, time_status, freshness}` 또는 `{state:'NA', reason}`. `[data-ram-price]` 표시 전용이다.
  - company: `{code}`(Universe 코드) 또는 `{company_id, ticker}`(TARGET).
  - 기기 DB에 저장된 시세는 읽지 않는다(3절 STOPPED).
  - reason: `NO_DEVICE_PRICE`, 그리고 `QgvScores.collectQuotes`와 같은 규칙의 `IDENTITY_CONFLICT_WITHDRAWN`(식별 충돌로 멈춘 코드), `PRICE_IDENTITY_CONFLICT`(철회된 Universe 코드와 같은 티커의 TARGET). 점수 경로가 V를 내지 않는 기업에는 가격도 보이지 않는다.
- `priceView`, `storeFacade`, `universeView`는 qgv·engines 전용이다.
  - 가격 view는 하나뿐이다. 세션과 PriceStore가 view를 키로 상태를 두기 때문이다.
  - facade는 클릭으로 탭을 읽기 전에는 `{}`나 null을 준다.

## 7. 기기 저장: `IS2.store` (옛 키·스키마 그대로)

- 읽기는 자유롭다. 쓰기는 `WRITE` 클릭 안에서만 한다.
- `KEYS`: personal, settings, profile-drafts(-v2), playbook, investor-stars, backup-restored, virtual-trading-v-scores(v1·v2), unified-sheet-source, universe-source, private-history-origin, price-store-enabled, chart-user-objects, macro-cycle-user-estimate(백업 /5), 그리고 IndexedDB `investment-device-actual-v1`.
- 함수
  - 관심 기업(1.1.4): `prefs()` → `{state:'OK'|'EMPTY'|'INVALID', value}`. `savePrefs(event, next)`. 코드는 `PREFS_INVALID`, `PREFS_STORAGE_INVALID`다.
  - 가중치(2.2): `weights()`, `saveWeights(event, spec)`, `PRODUCT_PRESETS`.
  - 보유(6.1): `holdings()` → `{state:'OK'|'EMPTY'|'NOT_AVAILABLE', reason, snapshot, source, as_of}`. DB가 없으면 `DEVICE_STORE_NOT_OPENED`이고 DB를 만들지 않는다.
    - `indexedDB.databases()`가 없는 브라우저는 저장소 쓰기 클릭 안에서만 DB를 연다(그래서 그 안의 백업 내려받기에는 보유가 들어간다). 클릭 밖에서는 `DEVICE_STORE_NOT_OPENED`다.
  - 플레이북: `playbook()`, `saveThesis/saveHold/saveRecord(event, …)`.
  - 투자자 별표: `stars()`, `toggleStar(event, cik)`.
  - V 기록: `vHistory()`(읽기 전용). 새 앱은 V 기록을 남기지 않는다(소유자 결정 2026-10-24). 중앙 V 이력은 서버 비공개 저장(D9)이다. P1 층 어디에서도 `VirtualTradingVHistory.capture/captureV2/record/recordV2`를 부르지 않는다(소스 검사).
  - 백업(소유자 결정 2026-10-24: /5는 옛 검증기 재사용, 다시 쓰지 않음)
    - `backup.create({userObjects})`: 기본 /4(이전과 바이트 같음). `userObjects:true`면 /5(차트 메모·시나리오, 매크로 사용자 추정 전부). `backup.download(event, {userObjects})`.
    - `backup.restore(event, text)`는 /1~/5를 받는다. /5의 사용자 작성 객체는 이 기기 기록에 합친다(지우지 않음, 중복 없음).
    - /5 검증은 `ChartWorkbench`·`MacroCycleRing`의 검증기다. DeviceBackup이 직접 찾는다(device-backup.js:26-32). 두 파일은 불러올 때 부작용이 없다(DOM·요청·저장·타이머·리스너 없음, 소스 검사로 고정).
    - 거절: `BACKUP_INVALID`(잘못된 /5 섹션 포함), `BACKUP_TOO_LARGE`. 옛 모듈 코드 `BACKUP_USER_OBJECTS_UNAVAILABLE`/`_UNREADABLE`/`_WRITE_FAILED`, `BACKUP_RESTORE_FAILED`는 그대로 지나간다.
  - 출처: `sheetSource`, `universeSource`, `workerOrigin`의 `has()`, `set(event, url)`(`workerOrigin`만 `approved()`도 있다). ID와 주소는 돌려주지 않는다.
    - Universe 출처는 통합 시트와 따로 둔다(옛 PrivateSubsetView와 같음, 소유자 결정 2026-10-24 중 Main 결정). `universeSource.useSheet(event)` [WRITE]: '통합 시트와 같게'. 통합 시트 ID를 이 키에 복사한다(돌려주지 않음). 통합 시트가 없으면 `SHEET_SOURCE_NOT_SET`.
  - 저장된 시세(DC-18): `marketQuotes.count()` → 남은 시세 기록 수(0~2, 숫자만. 키로만 세고 값은 읽지 않는다). DB가 없으면 0이고 열지도 만들지도 않는다. `indexedDB.databases()`가 없거나 IndexedDB가 없으면 null(알 수 없음). `marketQuotes.clear(event)` [WRITE]: 설정의 '저장된 시세 삭제' 버튼. 두 기록만 지우고 지운 수를 돌려준다. 보유와 구글 설정은 남는다. `databases()`가 없는 브라우저에서도 클릭 안에서 DB를 이름으로 열어 지운다. DB가 없으면 만들지 않는다(만들기를 중단한다). IndexedDB가 아예 없으면 null이다.
  - `subscribe(fn(key), {signal})`.

## 8. 엔진: `IS2.engines` (옛 엔진 그대로, 기기 결과로 계산)

- 공통
  - 점수는 공유 Page의 기기 결과다. 결과는 얼린 복사본이다.
  - `page` 인자는 `qgv.page()`가 준 Page만 받는다. 다른 것은 `PAGE_UNKNOWN`이다.
  - V가 든 결과에는 `v_source`(계산에 쓴 출처 id, P1에서는 늘 `DEVICE_TEMPORARY`)가 있다: `target.draft/build/blockers/selectRuleB`, `playbook.facts/judge`.
  - V 출처를 남기는 저장 기록: 초안(`draft.v_source`), R-B 행(`rule_b[].v_source`), 확정 버전(`versions[].v_source`, 초안의 출처). 옛 상태 검사(`validateState`)가 받아들이는 자리다.
  - **출처 필드가 없는 저장 기록**(형식이 정확한 키만 받음, 모두 기기 V): TARGET 카드 판정 기록(`thresholds.v`), 플레이북 발생 기록(T1 V_DETERIORATED 같은 V 변화 신호 포함), 출처 이전의 옛 초안.
  - 쓰기는 모두 클릭 안에서만 한다.
  - 가격이 든 결과(가상매매, 세트 비교)는 RAM 전용이다.
- **target**(2.1.7)
  - 읽기: `state()`, `basis()`, `draft({date, basis})`, `blockers()`, `ruleBDue(date)`, `scoringPending()`, `refreshScoring()`.
  - 쓰기·요청
    - `build(event, {reset})` [WRITE]. 카드 응답이 있으면 `reset:true`가 필요하다.
    - `finalize(event)` [WRITE]. outcome은 `FINALIZED`, `BLOCKED`, `DRAFT_REGENERATED`, `RELOAD_REQUIRED` 중 하나다.
      - `FINALIZED`면 버전에 `v_source`를 기록한다. 값은 초안의 출처이고, 초안에 없으면 Page의 `engine_v_source.id`다.
      - 빌더(#391)가 직접 박은 `v_source`가 그 값과 다르면 `V_SOURCE_MISMATCH`를 던지고 아무것도 저장하지 않는다.
    - `answer(event, …)`, `selectRuleB(event)` [WRITE].
    - `compare(event)`, `syncScoringPrices(event)` [SYNC]. syncScoringPrices의 탭 동기화는 자기 signal을 내미는 중첩 실행이다.
    - R-B 선정은 누를 때만 한다(소유자 결정 2026-10-24, 그대로).
- **playbook**
  - `facts(symbol)`: `v_now`·`v_prev20`과 함께 `v_source`를 준다.
  - `judge({symbol, situation, date})`: 읽기 전용이다. `v_source`는 facts의 출처이고, 화면이 넘긴 상황에 출처가 없으면 null이다. 엔진에는 옛 상황 키만 넘긴다.
    - `recorded`(불리언)와 `recorded_reason`(소유자 결정 2026-10-24: 누를 때만 기록). 읽을 때마다 이 기기의 플레이북 저장소에서 정한다. 그래서 다시 판정해도, 새로고침 뒤에도, 다른 화면에서도 같게 나온다.
      - `true`/null: `record()`가 쓸 발생 기록(후보 신호, 구조 뉴스 E4, 13F 전량 매도 E4)이 그날·그 이름으로 모두 저장돼 있다(같은 코드, 사유 포함).
      - `false`/`JUDGEMENT_NOT_RECORDED`: 아직 아니다. 화면은 `qgv.reasonText('JUDGEMENT_NOT_RECORDED')`('기록 안 됨')을 보인다.
      - `false`/`NOTHING_TO_RECORD`: 쓸 발생 기록이 없다('기록할 발생 신호 없음'). '기록됨'으로 보이지 않는다.
  - `record(event, judged)` [WRITE]: 발생 기록을 쓴다. `judge()` 결과만 받는다(`JUDGEMENT_UNKNOWN`). 그날 같은 이름·코드의 기록에 합치므로 다시 눌러도 바뀌지 않는다.
  - `due(date)`, `limits(rows, cash)`.
- **virtual**
  - `stored({reportDate})`(fetch:false)
    - 시작일 전: `NOT_STARTED`.
    - 로그인과 승인된 Worker가 없으면: `NOT_AVAILABLE`.
    - 그 밖에 탭을 읽기 전이면 종목별로 `PRICE_NOT_FETCHED`.
  - `compare(result, {defs})`, `forward()`(9.2, 가격 없음), `rehearse()`(RAM만).
    - `rehearse()`: 옛 app.js처럼 늘 Q·G 행과 `snapshot_basis`(v2)를 넘긴다. Page에 결과가 없으면(sec-qgv2.json 없음) 옛 compute로 TARGET 19행(Q·G null, BLOCKED 스냅숏)을 만든다. 그 밖의 Page 오류는 던진다.
  - `run()`은 늘 `NOT_IN_P1`이다. 기록 실행은 P2-6에서 붙인다.
  - 세트 B/C/D(장부 시트)도 P2-6이다. 대응: `VirtualLedgerSheets.load` / `active(meta,k)` / `apply` / `definitions`(virtual-ledger-sheets.js:696-699).
- **macro**(4.1.4): `current()`. 세대마다 `MacroLights.setPublic`을 부른다.

## 9. 고정 코드

던지는 코드(오류)와 값 안의 사유(NA·상태)를 함께 적는다. 글은 `IS2.qgv.reasonText(code, en)`로 만든다. 옛 모듈이 던진 코드는 그대로 지나간다(예: `DATE_INVALID`, `DISAGREE_REASON_REQUIRED`, `BACKUP_RESTORE_FAILED`, `READ_FAILED`, `DRIVE_FILE_PERMISSION_REQUIRED`).

| 어디 | 던지는 코드 | 값 안의 사유·상태 |
| --- | --- | --- |
| 불러오기(`loader.js`, 1.1절) | `LAYER_NOT_READY`(준비 전 행동), `LOADER_FAILED <파일>`(`IS2.ready` 거절, 실패 뒤 약속·행동), `LOADER_NAME_INVALID`(목록 이름) | `IS2.NOT_READY`(state `NOT_READY`, reason `LAYER_NOT_READY`), `IS2.LOAD_FAILED`(reason `LOADER_FAILED`); `loadState()` `WAITING`/`LOADING`/`READY`/`FAILED` |
| 관문(모든 action) | `CLICK_REQUIRED`(버튼류의 keydown, 자동 반복 keydown 포함), `ACTION_ALREADY_STARTED`(한 이벤트의 두 번째 최상위 action), `ACTION_KIND_NOT_COVERED`(부모가 갈 수 없는 kind의 중첩 실행), `ACTION_REQUIRED`(클릭 밖 쓰기, IndexedDB 쓰기 트랜잭션 포함), `DESTINATION_UNKNOWN`, `DEVICE_STORE_NOT_OPENED`, `ACTION_KIND_UNKNOWN`, `MARKET_STORE_STOPPED`(저장된 시세 기록 쓰기·범위 질의·색인, 그 저장소 삭제·이름 바꾸기, 클릭 안에서도) | — |
| `data` | `READER_MISSING`, `PUBLIC_FILE_UNKNOWN`, `PUBLIC_FILE_METHOD`, `PEEK_UNSUPPORTED`, `SEC_QGV2_UNAVAILABLE`/`SEC_QGV2_INVALID`(peek) | state `OK`/`NOT_PUBLISHED`/`FAILED`/`NOT_READ`, why `INVALID`/`NETWORK`/`HTTP`/`SCHEMA_NEWER`/`READER_MISSING`; refresh `APPLIED`/`UNCHANGED`/`FAILED`/`LOADING` |
| `qgv.page` | `READER_MISSING`, `ABORTED`(signal), `NO_OFFICIAL_YET`(중앙 경로, 아직 없음) | Page state `READY`/`NO_DATA`/`DATA_FORMAT_NEWER`/`READ_FAILED`, reason `SEC_QGV2_NOT_PUBLISHED`/`SEC_QGV2_NOT_AVAILABLE`/`SEC_QGV2_SCHEMA_NEWER`/`SEC_QGV2_INVALID`/`SEC_QGV2_UNAVAILABLE`/`V2_SCORES_NOT_AVAILABLE`; identities `CATALOG_NOT_AVAILABLE` |
| `qgv` 그 밖 | `PAGE_UNKNOWN`, `PAGE_NOT_READY`(결과 없는 Page), `SCOPE_UNKNOWN`, `PRESET_UNKNOWN`, `GATE_INVALID` | preview state `READY`/`INVALID`, reason `WEIGHTS_INVALID` |
| 행 NA | — | V: coverage V 사유(`NO_DEVICE_PRICE`, `SOURCE_NOT_AVAILABLE`, `FINANCIAL_PROFILE_V_NOT_DEFINED`, `CROSS_SECTION_TOO_SMALL`, `AXIS_WEIGHT_INSUFFICIENT` 등); total: `DATA_FORMAT_NEWER` → `CALC_VERSION_MISMATCH` → 엔진 total_reason; rank: `QG_REFERENCE`, `OUTSIDE_UNIVERSE`, `REFERENCE_ONLY`, `NOT_RANKED` 또는 total 사유 |
| `prices` 로그인 | `OFF`, `NOT_READY`, `PREPARE_TIMEOUT`, `CANCELED`, `AUTH_FAILED` | status google.error(`AUTH_REQUIRED`, `AUTH_POPUP_CLOSED` 등) |
| `prices.readUniverse` | `UNIVERSE_SOURCE_NOT_SET`, `UNIVERSE_SOURCE_INVALID`, `AUTH_REQUIRED`, `SOURCE_TOO_LARGE`, `CANCELED`, `UNIVERSE_READ_FAILED` | inputs `READY`/`SEC_INPUTS_UNAVAILABLE`/`SEC_UNIVERSE_SHARES_INVALID`/`SEC_UNIVERSE_SHARES_SCHEMA_NEWER`/`SEC_INPUTS_NOT_CONNECTED` |
| `prices.history` | `OFF`, `HISTORY_UNAVAILABLE`, `REQUEST_INVALID`, `ORIGIN_UNAPPROVED`, `AUTH_REQUIRED`, `CANCELED` | — |
| `prices` 탭·동기화 | `SYMBOLS_INVALID`, `INTERVAL_INVALID` | 결과 state·reason_codes(옛 PriceStore 코드), 종목별 code(`WORKER_ALLOWLIST` 등) |
| `prices.quote` | — | NA `NO_DEVICE_PRICE`, `IDENTITY_CONFLICT_WITHDRAWN`, `PRICE_IDENTITY_CONFLICT` |
| `store` | `PREFS_INVALID`, `PREFS_STORAGE_INVALID`, `WEIGHTS_INVALID`, `WEIGHTS_STORAGE_INVALID`, `SHEET_SOURCE_INVALID`, `SHEET_SOURCE_NOT_SET`(useSheet), `UNIVERSE_SOURCE_INVALID`, `REQUEST_INVALID`(Worker 주소), `BACKUP_INVALID`, `BACKUP_TOO_LARGE`(지나가는 옛 코드: `BACKUP_USER_OBJECTS_UNAVAILABLE`/`_UNREADABLE`/`_WRITE_FAILED`, `BACKUP_RESTORE_FAILED`) | marketQuotes.count null(알 수 없음); holdings `NOT_AVAILABLE` + `CATALOG_NOT_AVAILABLE`/`DEVICE_STORE_NOT_OPENED`/`DEVICE_STORAGE_UNAVAILABLE`; prefs·weights·playbook state `OK`/`EMPTY`/`INVALID` |
| `engines.target` | `PAGE_UNKNOWN`, `QGV2_NOT_READY`, `CATALOG_NOT_AVAILABLE`, `TARGET_V1_STATE_INVALID`, `TARGET_V1_ANSWERS_RESET`(두 번째 누름 필요), `V_SOURCE_MISMATCH` | finalize outcome `FINALIZED`/`BLOCKED`/`DRAFT_REGENERATED`/`RELOAD_REQUIRED`(+ blockers 코드); selectRuleB `SELECTED`/`NOT_READY`/`NOT_DUE`/`QGV2_NOT_READY`; syncScoringPrices `NOTHING_PENDING` 또는 동기화 state |
| `engines.playbook` | `PLAYBOOK_INVALID`, `JUDGEMENT_UNKNOWN` | 판정 코드(PlaybookEngine); recorded_reason `JUDGEMENT_NOT_RECORDED`('기록 안 됨'), `NOTHING_TO_RECORD`('기록할 발생 신호 없음') |
| `engines.virtual` | `NOT_IN_P1`(run), `PAGE_UNKNOWN`(rehearse) | stored state `NOT_STARTED`/`NOT_AVAILABLE`(+ `OFF`/`REQUEST_INVALID`/`ORIGIN_UNAPPROVED`/`AUTH_REQUIRED`/`PUBLIC_CATALOG_UNAVAILABLE`), 종목별 `PRICE_NOT_FETCHED`; compare `COMPARE_NEEDS_TWO_SETS`; forward `LOADED`/`NOT_PUBLISHED`/`NOT_AVAILABLE` |
| 중앙 V(미리 등록, 초안 문구) | — | `NO_OFFICIAL_YET`, `SUPPLY_FAILED`, `VERIFY_FAILED`, `PRICE_DEPENDENT_NOT_COMPUTABLE` |

## 10. V 출처 전환점(중앙 V가 게시될 때 바꿀 곳)

화면은 바꾸지 않는다. 페이지 전체가 한 번에 바뀐다. 아래가 지금 아는 전부다. P1 층 밖(옛 모듈)도 적었다.

1. `qgv.js`: `OFFICIAL_READER`(유일한 스위치)를 설정하고 `centralPage`를 구현한다. Q·G도 게시본에서 읽고 sec-qgv2.json과 섞지 않는다.
2. `data.js`: `FILES`에 넣고 엄격 리더를 붙인다.
3. **옛 DataRefresh 판독기 목록(옛 모듈 수정, Main 승인).** `data-refresh.js` readCore는 판독기 목록이 고정이다(:62-66). `vSource(pub)`가 보는 `DataRefresh.publication()`이 sec-qgv2.json과 중앙 게시본을 '전부 아니면 전무'로 함께 바꾸려면 readCore 또는 `public-screens.js` FILES가 게시본을 읽어야 한다(중앙 V 설계 재사용 표 :401).
4. **옛 `qgv-scores.js` 게시본 모드(옛 모듈 수정).** 중앙 V 설계 §11(:404): 게시본 모드를 넣고, 기기 가격 경로는 개인 미리보기로만 쓴다.
5. Pages 가드 허용 목록에 넣는다(Main).
6. `TargetV1Builder.finalize`는 #391에서 `v_source`를 직접 박는다. 옵션이 필요하다(Main이 #391에 요청). 그전까지는 engines가 초안의 출처를 기록하고, 병합 뒤에는 빌더 값과 다르면 `V_SOURCE_MISMATCH`로 저장을 막는다.
7. **엔진 중앙 모드 계약.** 지금 `held`(엔진용 결과)는 `devicePage`만 채운다. 중앙 Page에는 결과가 없어 `forEngines`가 `PAGE_NOT_READY`를 던진다. 그래서 둘 중 하나를 정해야 한다.
   - `centralPage`가 `devicePage`도 돌려 `held`를 채운다. 엔진 기록은 `engine_v_source`(DEVICE_TEMPORARY)로 남는다.
   - 또는 중앙 V 행을 computed 모양으로 바꾸는 어댑터를 두고 `engine_v_source`를 바꾼다.
   - 이 계약에 기대는 곳: `engines.js`의 `scored`/`basis`/`builderArgs`(TARGET 초안, R-B), `finalize`의 재생성, `rehearse`(결과가 없으면 옛 compute로 대신함), `playbook.facts`(scoreView의 기기 결과).
8. **출처 필드가 없는 저장 기록**(8절): TARGET 카드 판정, 플레이북 발생 기록, 옛 초안. 중앙 V 뒤에는 기기 V 기록과 구별되지 않는다. 기록 형식에 출처를 넣을지 정한다.
9. **미리보기.** `qgv.preview`는 기기 시세로 다시 계산하므로 늘 임시 V로 표시한다(지금 고정). 중앙 모드에서 개인 미리보기를 어떻게 보일지 정한다.
10. **문구.** `OFFICIAL_CENTRAL` 문구와 중앙 V 사유 4개(`NO_OFFICIAL_YET` 등)의 글은 초안이다. 지금 글에는 '(초안 문구)'가 붙어 있다. 전환할 때 사용자 확인을 받고 고친다.

## 11. 사용자 결정

### 결정됨 2026-10-24 (오후, 소유자. Main 결정은 그렇게 적었다)

- V 기록: 기록하지 않는다(P1 그대로). 중앙 V 이력은 서버 비공개 저장(D9)이다. P1 층은 VHistory 기록 함수를 부르지 않는다(소스 검사).
- 플레이북 판정 기록: 누를 때만 한다(`record(event)`). 기록하지 않은 판정은 `recorded:false`, `JUDGEMENT_NOT_RECORDED`('기록 안 됨')다. 기록 여부는 저장소에서 읽으므로 다시 판정하거나 새로고침해도 같다(8절).
- R-B 선정: 누를 때만 한다(`selectRuleB(event)`, 그대로).
- IndexedDB 'market' 시세 저장: 중단한다(계획 §2.1, DC-18). 새 앱은 쓰지도 읽지도 않는다(3절 STOPPED). 기존 저장분은 자동으로 지우지 않고 설정의 '저장된 시세 삭제'(`store.marketQuotes.clear(event)`)로만 지운다. 옛 화면은 P3 전환 때까지 계속 쓴다.
- 로그인 준비 → 로그인 2단계: 지금은 유지한다. P2-1에서 폰 실측(iOS Safari·안드로이드 Chrome) 뒤 한 번으로 줄일 수 있으면 줄인다.
- 한 이벤트로 시작하는 최상위 action: 1개(`ACTION_ALREADY_STARTED`). 중첩 실행은 부모 signal을 내밀고, 부모가 갈 수 있는 곳까지만 간다(`ACTION_KIND_NOT_COVERED`). 한 번의 키 누름도 action 하나다(버튼류는 click만, 자동 반복 keydown 거절, 2절).
- 백업 /5: 옛 검증기(ChartWorkbench·MacroCycleRing)를 재사용한다. 두 파일을 재사용 목록에 넣었다(불러올 때 부작용 없음 확인). 다시 쓴 코드 없음.
- 남은 항목(Main 결정, 기존 동작과 경계에 맞춤)
  - 임시 V 순위 문구: '임시 V 기준 순위 · 공식 순위 아님'. `qgv.rankLabel()`과 `rank_label`로 준다.
  - Universe 출처: 통합 시트와 따로 둔다(옛 동작). P2 설정은 '통합 시트와 같게'를 클릭(`universeSource.useSheet(event)`)으로 줄 수 있다.
  - 구글 켬/끔: 옛 동작대로. 기기 DB가 이미 있을 때만 읽고, 로그인 준비 클릭 안에서만 쓴다(옛 로그인 클릭이 켬을 썼다). 로그아웃은 바꾸지 않는다(옛 연결 해제와 같음). 클릭 없이는 아무것도 쓰지 않는다. GIS 스크립트는 클릭 안에서만 받으므로 다시 온 사용자도 페이지마다 준비 탭은 필요하다.
- 휴대폰 첫 화면 비용: 미루지 않고 P2-1의 첫 작업으로 한다. boot.js·셸을 먼저 그리고 엔진·P1 층은 첫 그림 뒤에 불러온다. 목표(390×844, 150 ms RTT·1.6 Mbps·CPU ×4): 첫 화면 2,000 ms 이하, 첫 전송 100 KB 이하. 측정을 시험으로 고정한다. 다른 화면 PR은 그 구조 위에서 만든다. 검토 측정(결정 전): 첫 화면 1,558 → 4,119 ms, 전송 13 KB → 569 KB, 스크립트 7 → 78개(이번 두 검증기로 80개).

### 아직 정할 것

- 일일 보고서·보고서 모델, 가상매매 기록 실행, 세트 B/C/D는 P2-6에서 정한다(daily-report.js는 불러오지 않음).
- 중앙 V 모드의 엔진 계약(10절 7)과 출처 없는 기록(10절 8).
- P2-6 보유 쓰기(Main): 보유만 쓰는 store 함수(`WRITE`, 옛 `DeviceActual.restoreHoldings`로 `actual`만 커밋)를 붙인다. 옛 `DeviceActual.mount` 화면(저장·가져오기·삭제)은 시세 기록을 함께 쓰고 진짜 window에서 돌아 다시 쓰지 않는다(3절 STOPPED).
- 손으로 넣는 시세·환율(소유자 또는 Main): 옛 기기 보유 화면은 그 값을 시세 기록(`market`)에 저장했다. DC-18 뒤에는 둘 곳이 없다. 선택지: RAM에만 두기(새로고침하면 사라짐), 사용자 시트에 쓰기, 기능 빼기. P2-6 전에 정한다(USER_DECISIONS_PENDING `MANUAL-QUOTE`).

## 12. 시험

- 노드 시험(`node implementation/tools/<파일>`)
  - `web_app_reuse_node_test.js`: 불러오기 목록(index.html 첫 화면 + `LOAD_ORDER`, 빌드·도우미·로더가 같은 목록), 빌드 실패 규칙, 로더(가짜 window: 첫 그림 전에는 넣지 않음, `async=false` 순서, `IS2.ready`·`LOADER_FAILED`, 대리 객체 종류별 동작과 실패 뒤 복원, 대리 객체 API = 실제 층 API), 화면 파일이 불러올 때 층을 건드리지 않음, 소스 규칙.
  - `web_app_qgv_node_test.js`: action, data, qgv.
  - `web_app_prices_node_test.js`: prices, store.
  - `web_app_engines_node_test.js`.
- 브라우저 시험: `web_app_data_layer_browser_test.js`. Playwright가 필요하다(`NODE_PATH`, `PLAYWRIGHT_BROWSERS_PATH`). 페이지를 열거나 새로고침할 때마다 `IS2.ready`를 기다린다.
  - 빌드 출력: 재사용 파일이 바이트 그대로이고, 부르지 않는 옛 파일이 없다.
  - A: 행동 없이 읽으면 공개 파일만 읽고, 저장 0, blocked 0이다.
  - B: 흉내 낸 행동은 모두 거절되고 요청이 0건이다.
  - A에는 경로마다 새로 열기, 경로 바꾸기, `route.signal` 해제, 칩 구독 수 확인이 들어 있다.
  - B에는 위조 이벤트, `requestSubmit()`·`submitter.click()` submit이 들어 있다.
  - C: 실제 클릭이면 정해진 요청만 나가고 V가 계산되며, 표지 가격이 새지 않는다.
  - C2: 저장해 둔 진짜 클릭 이벤트를 나중에(타이머, 다른 kind) 다시 쓰면 거절되고 요청이 없다. 부모 signal을 내민 중첩 실행만 통과하고, signal 없는 다음 단계는 `CLICK_REQUIRED`, 한 클릭의 두 번째 최상위 action은 `ACTION_ALREADY_STARTED`다. 버튼에서 Enter·Space를 누르면 click만 action을 시작하고(keydown은 거절), 키를 누르고 있어도 자동 반복 keydown은 시작하지 못한다. 활성화 동작이 없는 요소는 keydown으로 한 번 시작한다.
  - C3: 옛 화면이 저장한 것처럼 넣은 유효한 `market` 기록을 옛 경로는 읽지만 새 층(quote, 점수 경로)은 읽지 않는다. view를 거친 쓰기는 클릭 안에서도 거절된다(실제 IndexedDB 객체). 요청이 내준 객체(`source`, `transaction`, 처리기의 `event.target`)를 거쳐도 쓰기는 거절되고 읽기는 없는 기록이다. 쓰기 action 밖의 버전 변경은 중단된다. count는 숫자, 진짜 클릭의 clear는 시세 기록만 지운다.
  - C4: 브라우저에서 /5 백업이 옛 검증기로 복원되고 다시 백업에 나온다. 잘못된 섹션은 `BACKUP_INVALID`이고 아무것도 쓰지 않는다.
  - D: 새로고침하면 RAM이 비워진다. 클릭으로 저장한 것(Universe 출처, 구글 켬 기록)만 남고, 켬 기록은 클릭 없이 읽힌다.
- `web_app_first_paint_browser_test.js`(P2-1a): 개발 빌드를 Pages처럼(gzip) 띄우고 CDP로 390×844, 150 ms·1.6 Mbps·CPU ×4, 콜드 캐시에서 3번 잰다. 첫 화면(`is2-first-paint`와 FCP 중 늦은 것) ≤ 2,000 ms, 첫 전송(그때까지 끝난 요청의 encodedDataLength 합) ≤ 100 KB를 중앙값으로 확인하고 `FIRST_PAINT ms=… first_kb=… ready_ms=… total_kb=…`를 찍는다. 첫 그림 순간의 구조(검색창·메뉴·탭, 칩 '연결 전', 옛 모듈 없음, 대리 객체 `NOT_READY`, `LOAD_ORDER` 요청 없음)와, 제한 없이 대리 객체 계약(첫 파일을 붙잡아 둔 채 확인)·실패(404, 실행 중 오류 → `LOADER_FAILED`)도 본다. `FIRST_PAINT_ENCODING=identity`면 압축 없이 잰다.
- `web_app_shell_browser_test.js`(P0)는 고치지 않고 통과한다.
- 도우미: `web_app_reuse.js`(옛 모듈 경로 한 곳), `web_app_test_site.js`(빌드·서빙·fixture·`watch`·`storage`·`leaks`·`assertRamOnly`).
- CI 목록 등록은 Main이 한다.
