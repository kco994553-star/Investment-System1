# 프론트 v2 P1 자료·계산 층: P2 레인용 API 계약

P2 화면 레인이 쓰는 함수, 기록 모양, 사유 코드, 지켜야 할 규칙을 정한다. 근거는 P1 구현 사양(Main 결정 2026-10-24)과 같은 날 오후의 소유자 결정(P1 동작, 11절)이다. 기능 번호는 사양 v1.0 번호(1~9)다.

## 1. 파일과 화면 등록

- 위치는 `implementation/src/investment_system/product/web_app/`이고, 전역은 `IS2` 하나다.
- 불러오는 순서(P2-1a, 1.1절)
  - `index.html`(첫 화면만, 모두 `defer`): P0 기반(core·shell·parts) → `loader.js` → 레인 파일 8개(`screen-qgv/technical/macro/news/portfolio/prompts/tree/lab.js`) → P0 화면 → `boot.js`. web_app 파일만 둔다(옛 모듈이 있으면 빌드 실패).
  - 첫 그림 뒤 `loader.js`의 `LOAD_ORDER`: 옛 모듈 60개(web_assets 바이트 그대로, 빌드 A안. 설계 57개 + 백업 /5 검증기인 `chart-workbench.js`·`macro-cycle-ring.js` + 홈 명언·이야기 `home-quotes.js`) → `action` → `data` → `prices` → `store` → `qgv` → `engines` → 공용 부품 `search-part-live.js`(DC-23 공용 기업 검색) → 화면 논리 파일(web_app 파일, 지금은 `screen-search-live.js`(P2-1)·`screen-qgv-live.js`(P2-2a) 2개).
    - `home-quotes.js`(P2-1, Main 승인): 옛 페이지 순서 그대로 `virtual-trading-compare.js`와 `data-refresh.js` 사이에 둔다(옛 상대 순서 시험). 불러올 때 부작용이 없다(자기 전역 `HomeQuotes`만 둠, 노드 시험).
    - 화면 논리 파일(P2-1, Main 결정 2026-10-25): 첫 그림 예산은 메뉴 9개가 함께 쓰므로, 화면의 첫 그림 파일(index.html의 `screen-*.js`)은 뼈대만 두고 `IS2.ready` 뒤에만 도는 논리는 `engines.js` 뒤의 web_app 파일로 옮긴다(1.1절 화면 규칙). web_app에 있는 이름이라 빌드는 web_app에서 가져온다(A안 재사용 아님, 옛 파일과 같은 이름 금지). 이름·중복·순서 규칙은 다른 `LOAD_ORDER` 이름과 같다.
      - 화면 논리 파일도 `LOAD_ORDER`의 파일이다. 그래서 그 파일이 오지 않거나(404) 불러올 때 오류를 내면 `IS2.ready`가 `LOADER_FAILED <파일>`로 거절되고, **메뉴 9개 모두** 층을 쓰지 못한다(대리 객체가 거절, 행동 버튼 꺼짐, 셸의 실패 안내). 한 레인의 파일이 모든 메뉴의 층을 막을 수 있다는 이 대가는 P2-1 PR 본문에서 Main 확인을 요청했다. P2-2a의 `screen-qgv-live.js`도 같다(404나 불러올 때 오류면 `LOADER_FAILED screen-qgv-live.js`로 메뉴 9개 모두, Main 승인 2026-10-25). 그러므로 논리 파일은 불러올 때 `IS2.<이름>`에 채우는 함수만 두고, 던질 수 있는 최상위 작업을 하지 않는다(노드 시험 `web_app_reuse_node_test.js`가 불러올 때 층을 건드리지 않고 그 이름만 두는지 본다).
  - 레인은 index.html도 `LOAD_ORDER`도 고치지 않고 자기 파일만 채운다(바꿀 때는 Main 승인. 자기 화면 논리 파일을 `LOAD_ORDER` 끝에 더하는 것도 Main 승인).
- 등록:
  - `IS2.register(id, render)`: 자리표시를 실제 화면이 대신한다. 실제 화면을 두 번 등록하면 `SCREEN_DUPLICATE`다.
  - `IS2.registerDetail(name, render)`: `#/detail/<name>`에 쓴다. 이름은 `IS2.DETAILS`에 있어야 한다(`DETAIL_UNKNOWN`).
- 선택 기업(기능 1.1.2 "화면을 이동해도 선택 기업을 유지", P2-1): `IS2.selection`(core.js, 첫 화면 파일).
  - `get()` → `{id}`(얼린 값) 또는 null. `set(id)`: 빈 값이면 지운다. `subscribe(fn, {signal})`: 바뀔 때 `fn({id}|null)`, abort되면 풀린다.
  - id는 TARGET company_id 또는 Universe 코드다. 기업 화면이 id를 찾으면 정한다. RAM에만 두고 새로고침하면 사라진다. 저장·요청 없음.
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
  - 이름 규칙은 로더의 `NAME` 하나다(소문자·숫자·`-`·`.`, `.js`로 끝남). 빌드와 도우미도 같은 규칙으로 거르고 같은 이름 두 번도 거른다. 빌드는 loader.js의 `NAME` 줄이 자기 줄과 글자까지 같지 않으면 실패한다. 그래서 빌드를 통과한 목록은 실행 때 `LOADER_NAME_INVALID`를 만나지 않는다.
  - 스크립트 요소는 loader.js만 만든다. `h()`는 `'script'`·`'svg:script'`를 대소문자 없이 거절한다(`TAG_INVALID`). 소스 규칙이 막는 것: createElement·createElementNS·`h()`에 준 `'script'`(loader.js 밖), 계산된 태그나 createElement(NS)를 따로 잡아 두고 부르기(core.js `h()` 밖), HTML 문자열 해석.
- **`IS2.ready`**: 모든 파일이 실행되고 층이 자리를 잡으면(`IS2.action`과 다섯 이름공간) 풀린다. 표시 `is2-ready`. 실패하면 목록 순서로 첫 실패 파일을 담아 `LOADER_FAILED <파일>`(`err.code`·`err.file`)로 거절된다. 파일이 오지 않음, 실행 중 오류, 이름공간을 놓지 않음이 실패다. 다시 시도하지 않는다(새로고침이 한다). 표시 `is2-load-failed`.
  - 실패하면 셸이 기기 칩을 '연결 실패'로 바꾸고, 모든 화면의 main 위에 고정 문구 "일부 파일을 불러오지 못했습니다 · 새로고침해 주세요"와 [새로고침] 버튼을 띄운다(`role="alert"`). 파일 이름은 보이지 않는다. 버튼은 `location.reload()`만 부르고 자기 요청은 없다. `IS2.loadState()`는 `WAITING` → `LOADING` → `READY`/`FAILED`다.
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
  - 화면 파일은 불러올 때 층을 건드리지 않는다(노드 시험). 층 값은 렌더 때 읽는다. 화면 논리 파일도 불러올 때는 `IS2`에 자기 함수만 놓는다.
  - **화면의 첫 그림 파일은 뼈대만 둔다**(P2-1, Main 결정 2026-10-25). 첫 그림 파일에는 동기로 그리는 자리(제목, 입력 요소, 머리, 카드 틀과 `parts.pending`)와, 층 없이 되는 최소 동작(예: 검색 상자에 입력하면 '불러오는 중')만 둔다. 색인 만들기·목록 논리·칩·카드 채우기·저장 버튼처럼 `IS2.ready` 뒤에만 도는 논리는 `LOAD_ORDER`의 화면 논리 파일에 둔다.
    - 넘겨주기: 논리 파일은 불러올 때 `IS2`에 채우는 함수만 놓는다(메뉴 0: `IS2.searchLive = {home, company}`, 메뉴 1(P2-2a): `IS2.qgvLive = {leaderboard, helpers}`, helpers는 노드 대조 시험용 순수 함수). 뼈대는 렌더 때 자리 참조를 만들고, `IS2.ready`가 풀린 뒤 그 경로의 `route.signal`이 살아 있으면 그 함수를 부른다. 함수는 동적 자리만 그 자리에서 바꾼다. 입력 요소는 다시 만들지 않는다(IME·초점 유지). `route.signal` 처리는 렌더와 같다.
    - 준비 전에도 입력은 된다. 메뉴 0 검색 상자는 준비 전 입력·초점에 '불러오는 중'을 보이고, Escape는 목록만 닫고 글자를 남기며(type=search의 기본 지우기 막음), 초점이 상자를 떠나면 목록을 숨긴다(분리 전과 같은 동작). 준비 전 제출은 P0처럼 `#/company/<검색어>`로 간다. 준비 뒤 논리 파일이 자기 처리기로 바꾸고(뼈대 처리기는 AbortController로 한꺼번에 뗀다) 이미 입력된 글자로 목록을 다시 그린다. 준비 전에 떠난 경로는 채우지 않는다.
    - 불러오기 실패(`LOADER_FAILED`) 뒤: 기업 화면 머리는 분리 전처럼 고정 문구 '기업 목록을 불러오지 못했습니다'(`data-na=INDEX_FAILED`)로 바꾼다. 홈의 칩·이야기, 카드 4개, 준비 전 목록의 '불러오는 중'은 분리 전처럼 그대로 두고, 실패 신호는 셸의 '연결 실패' 칩과 새로고침 안내다. 채우는 함수 안의 오류는 삼키지 않는다(콘솔에 남아 시험이 잡는다).
    - 목록 위의 마우스는 옵션을 강조만 한다. 검색 버튼·Enter는 방향키로 고른 옵션만 따른다(휴대폰 초점 스크롤로 목록이 멈춘 포인터 아래로 오거나 포인터가 목록을 지나가도 제출 대상이 바뀌지 않음).
    - 크기: `screen-search.js`·`screen-qgv.js` ≤ 5 KB(노드 시험 `web_app_reuse_node_test.js`의 `SKELETON_MAX_BYTES`). 다른 레인도 같은 방식으로 첫 그림 파일을 작게 둔다.
  - 렌더는 기다리지 않는다. 자리를 먼저 그리고(`parts.pending`) 약속 함수의 값이 오면 채운다(1절). 동기 값이 `IS2.NOT_READY`면 연결 전으로 그린다.
  - 행동 버튼은 `IS2.ready`가 풀린 뒤 켠다. 실패하면 꺼 둔다(새로고침 안내는 셸이 한다).
  - 기기 칩은 `IS2.ready` 전까지 '연결 전', 실패하면 '연결 실패'다(셸).
- **목표와 시험**(390×844, 150 ms RTT·1.6 Mbps·CPU ×4, 콜드 캐시): 첫 화면 2,000 ms 이하, 첫 전송 100 KB 이하. `tools/web_app_first_paint_browser_test.js`가 3번 재어 중앙값으로 확인한다(12절). 다른 화면 PR은 이 구조 위에서 만든다. 첫 화면 파일을 늘려 목표를 넘으면 이 시험이 막는다.
  - 제한이 실제로 걸렸는지 시험이 매번 확인하고, 아니면 이유를 적고 실패한다: 같은 CPU 고정 루프가 제한 뒤 CPU × 0.6배(2.4배) 이상 오래 걸린다(제한 전후 빈 페이지에서, 그리고 `IS2.ready` 뒤 불러온 페이지에서 한 번 더. 이동 뒤에도 제한이 남았다는 확인), 문서 요청이 지연(150 ms) 이상 걸린다, 그 실행에서 가장 큰 응답(서버가 보낸 크기)이 그 바이트를 1.6 Mbps로 받는 시간 + 지연 이상 걸린다. 측정값: CPU 비 4.2~5.2, 문서 156~162 ms, 손글씨 글꼴 365.9 KB가 6.7초(하한 2,023 ms).
  - **측정 모형이 빼는 것**: 루프백 HTTP/1.1 서버라 연결 준비(DNS·TCP·TLS 왕복)가 없고, 기기 배율은 1이다. Pages는 HTTPS + HTTP/2다. 그래서 실제 첫 방문은 이 숫자보다 느리다. 150 ms 왕복이면 HTML이 오기 전에 연결 준비로 약 3번(약 450 ms)이 더 든다(첫 화면 중앙값 + 450 ms ≈ 1.3초, 여전히 2,000 ms 안). HTTP/1.1의 연결 6개 대기열 때문에 준비 시간 숫자는 Pages보다 나쁘게 나온다. 실제 휴대폰 확인(iOS Safari·Android Chrome)은 P2-1 계획대로 한다.
  - 측정(P2-1 메뉴 0 화면, 2026-10-25, 같은 조건 3번 중앙값, 같은 기계에서 연달아): canonical 4c3d8142 첫 화면 933 ms·첫 전송 25.4 KB·`IS2.ready` 7,234 ms·그때까지 889.6 KB → 뼈대 분리 전(논리가 모두 `screen-search.js`, 28,745 B·gzip 11.1 KB) 940 ms·36.5 KB·7,363 ms·905.3 KB → 분리 뒤(`screen-search.js` 4,673 B·gzip 2.3 KB, 논리 `screen-search-live.js` 25,492 B·gzip 10.0 KB는 첫 그림 뒤) 967 ms·27.5 KB·7,438 ms·906.5 KB. 첫 전송의 남은 증가(+2.1 KB)는 `screen-search.js` 뼈대 +0.95 KB(콤보 상자 속성·준비 전 입력 처리·카드 틀), `app.css` 화면 규칙 +0.8 KB, `core.js` `IS2.selection` +0.3 KB, `loader.js` 목록 +0.05 KB(gzip)다. 리뷰 수정(준비 전 Escape·초점·초점 떠남 처리, 실패 문구) 뒤 `screen-search.js` 5,100 B·gzip 2.5 KB(canonical 대비 +1.18 KB), `screen-search-live.js` 25,834 B·gzip 10.2 KB, 976 ms·27.7 KB(+2.3 KB)·7,432 ms·906.8 KB.
  - 측정(2026-10-24 리뷰 수정 뒤, Pages처럼 gzip, 시험 3번 실행 × 각 3번): 실행별 중앙값 첫 화면 891·894·862 ms(9번 863~899, 9번 중앙값 887), 첫 전송 25.2 KB(18건, 글꼴 3개는 전송 중), `IS2.ready` 7,213·7,215·7,205 ms, 그때까지 888.8 KB(85건), 글꼴까지 모두 1,254.9 KB. 수정 전(같은 날): 848 ms, 24.4 KB, 7,190 ms, 888.1 KB. 압축 없이(수정 전): 948 ms, 48.2 KB, 13,493 ms, 2,430.4 KB. 결정 전 검토 측정은 첫 화면 4,119 ms, 전송 569 KB였다.
  - 남은 비용(목표 없음): 첫 그림 뒤 층이 준비될 때까지(`IS2.ready`, 행동 버튼) 제한 프로필에서 약 7초다. 글꼴 3개(약 620 KB)가 첫 그림 때부터 같은 대역폭을 나눠 쓰기 때문이다(검토 측정: 글꼴 응답을 붙잡아 두면 약 6.0초, 648.7 KB). 후속 방법 두 가지(결정 필요, 이번에는 글꼴을 바꾸지 않음): (1) 375 KB 손글씨 글꼴을 `font-display: optional`로 하거나 첫 화면 글자만 담은 부분집합을 먼저 쓰기, (2) 화면별 모듈 목록(P2 레인마다 자기 `LOAD_ORDER` 조각, 화면이 쓰는 옛 모듈만 그 화면에서). 목표가 생기면 `ready_ms` 예산을 시험에 더한다.

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
  - 값을 내주는 곳은 `prices.quote()`, `prices.history()/held()`, `prices.periodReturns()`(기간 수익률, P2-2a), `prices.rankFor()`(M3 순위, 시총 순서라 가격 파생으로 취급, P2-2a), 가상매매·세트 비교 결과뿐이다.
  - 시험 도우미: `tools/web_app_test_site.js`의 `assertRamOnly(page, sentinels)`.
- **NA 규칙**
  - 값이 없으면 null이고 사유 코드가 반드시 붙는다. 0이나 평균으로 채우지 않는다(`?? 0`, `|| 0` 금지).
  - 글은 `IS2.qgv.reasonText(code, en)`로 만든다.
- **V 출처**
  - 점수 행: 화면 글자에는 `row.source_label`(DC-31부터 '공식 V')만 쓴다.
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
  - **기기 V 이력 키도 멈췄다(소유자 결정 2026-10-31, DC-31).** `STOPPED.localStorage`: `investment.web.v1.virtual-trading-v-scores`, `investment.web.v2.virtual-trading-v-scores`. 뷰의 `getItem`은 null, 키로 쓰거나 지우면 클릭 안에서도 `V_HISTORY_STOPPED`다. `key()`·`length`는 이름만 센다(값 없음). 지우는 길은 `store.vHistoryKeys.clear(event)`(`stoppedKeys.clear`, WRITE 신호) 하나다.
  - **기기 시세 기록은 멈췄다(소유자 결정 2026-10-24, DC-18).** `STOPPED.indexedDB`: DB `investment-device-actual-v1`의 `snapshots` 저장소 안 기록 `market`(저장된 시세)과 `market-import-history`(가져올 때마다의 시세·환율). 계획서가 'market 저장소'라고 부른 것은 별도 저장소가 아니라 이 두 기록이다(device-actual.js:9-10).
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

- `page({signal})` → Page (DC-31, 10절).
  - 같은 입력이면 모든 화면이 같은 객체를 받는다.
  - 점수는 `QgvScores.officialPage`가 `data.official()`의 게시본으로 만든다. 공식 기본 프로필이고, 엔진 호출도 가격도 없다.
  - 숨은 TARGET 결과(`forEngines`, 11/16까지)만 `QgvScores.pageResult(scoreView, …)`로 계산한다. scoreView는 네트워크를 쓰지 않는다(`SCORE_PATH_NO_NETWORK`). 가격은 RAM에 있는 것만 쓰고, 기기 DB에 저장된 시세는 읽지 않는다(DC-18, 3절 STOPPED).
- 접근 함수
  - `rankLabel(x, en)`: 순위 옆에 붙이는 글. x는 Page, 미리보기, 행, V 출처 id다. 공식 Page는 '공식 순위 · 중앙 게시 V', 미리보기와 그 행은 '내 설정 순위 · 공식 V로 다시 계산 · 공식 순위 아님'이다(DC-31). 모르는 출처는 공식이라고 부르지 않는다. Page와 미리보기에는 같은 글이 `rank_label`로 들어 있다.
  - `rows(page, {scope:'ALL'|'UNIVERSE'|'TARGET'})`: QgvScores 순서 그대로 준다. 정렬, 모집단, 분류 필터는 P2-2a가 `screen-qgv-live.js`의 작은 순수 이식(옛 `leaderboard-screen.js`의 `sortRows`·`sicOf`·`populationOf`·`classificationOf` 업종 부분·`filterClassifications`, 각 줄에 원래 함수와 줄 번호)으로 붙였다(Main 결정 2026-10-25). `LeaderboardScreen`(67 KB)과 `StatRadar`는 불러오지 않는다. 같은 결과는 노드 대조 시험(`web_app_qgv_screen_node_test.js`)과 고정 벡터가 묶고, P3가 옛 파일을 지우면 사본은 하나만 남는다. 레이더는 P2-2c에서 정한다.
  - `model(page)`(P2-2a, Main 결정 2026-10-25): 그 Page가 쥔 결과로 `QgvScores.officialModel`을 부른 N10·N15·N20 후보의 가격 없는 투영이다(공식 기본 프로필·관문 켬, D12). `{v_source, official_profile, primary:'N15', ns, as_of, checked, ranked, provisional, excluded, unknown:{subgroup}, sets:{N10|N15|N20:{n, complete, status, weight_pct, shortfall_pct, causes, skipped, group_capped:[{id,ticker,rank,group}], selected:[{id,ticker,rank,total,group}], issuer_check:{status, applied, issuers_n}}}}`. 순위·묶음 id·수·비중만 있고 지표 값·시세·가격은 없다. 공식 순위가 없으면 null, 결과 없는 Page는 `PAGE_NOT_READY`. Page마다 한 번 만들고 얼린다.
  - `row(page, idOrCode)`, `coverage(page)`(수만).
  - `preview(page, weights, {typeWeights, gate})`: 개인 가중치다. 게시된 요인 점수로 다시 계산한다(10절). 결과는 늘 `weights:'PERSONAL'`이고 공식 순위가 없다. `weight_stages`는 NA(`WEIGHT_STAGES_NOT_REBUILT`)다.
    - 2.2 개인 계산과 같은 호출이다(device-profiles.js). preset 없이, 그 가중치 프로필의 `gate`를 넘긴다(null이면 기본값 켬). 저장된 프로필의 gate를 꼭 넘긴다.
  - `isPage(page)`: 이 접근자가 만든 Page인지.
  - `setProfile({preset, gate})`(RAM만), `profile()`, `constants()`(2.5 트리용), `subscribe(fn(why), {signal})`. why는 DATA·PRICES·DEVICE·PROFILE이다.
  - `reasonText(code, en)`, `V_SOURCES`, `vSource()`.
    - P2-2a가 더한 글(qgv.js `TEXT`, Main 결정 2026-10-25, 보드 문구가 있으면 그대로): 가격 버튼·M3 코드 `UNIVERSE_SOURCE_NOT_SET`·`UNIVERSE_SOURCE_INVALID`·`AUTH_REQUIRED`·`CANCELED`·`PREPARE_TIMEOUT`·`SOURCE_TOO_LARGE`·`UNIVERSE_READ_FAILED`·`SHEET_NOT_CONNECTED`(PriceStore 자기 코드)·`PRICE_TABS_OFF`·`UNIVERSE_NOT_READ`·`NOT_IN_UNIVERSE`·`NO_VERIFIED_ROWS`, 수익률 코드 `PRICE_TABS_NOT_LOADED`·`RETURN_SESSIONS_NOT_AVAILABLE`·`RETURN_HISTORY_TOO_SHORT`·`RETURN_BASE_CLOSE_MISSING`·`RETURN_LAST_CLOSE_MISSING`·`PERIOD_PENDING`·`PRICE_BASIS_CONTINUITY_UNCONFIRMED`(TA-G1 코드). `RETURN_*`는 V 이력 규칙의 `HISTORY_TOO_SHORT`와 구별하려고 따로 둔다. 어느 글에도 V 출처 낱말은 없다.
    - 화면은 표에 없는 코드(M3 `reason_codes`의 `GOOGLE_MCAP_MISSING` 등, 클릭 오류 `CLICK_REQUIRED` 등)를 글로 찍지 않는다. 그 자리의 고정 한국어 문구를 쓰고 코드는 `data-reason`·`data-na`에만 둔다.
- `forEngines`(숨은 TARGET 기기 결과, Promise), `centralComputed`, `engineInputs`, `scoreView`는 engines 전용이다(소스 검사로 막는다).

```
Page { v_source{id,ko,note}, engine_v_source{…}, rank_label, state: READY|NO_DATA|DATA_FORMAT_NEWER|READ_FAILED, reason,
  as_of, calc_version, type_scope, profile_id, preset, gate, generation, basis_id,
  price_basis{kind:'CENTRAL_IEX', label, reason, price_basis_date, generated_at, verified_at, publication_id, calc_version, sessions, stale, calc_differs, inputs_match, attempt, attribution},
  identities{state: OK|NOT_AVAILABLE, reason: null|CATALOG_NOT_AVAILABLE, count} | null, coverage, rows[] }
RowRecord { id, ticker, code, record, scope: UNIVERSE|OUTSIDE_UNIVERSE, target, reference_only, source, source_label,
  score{total,q,g,v}, na_reason{total,q,g,v,rank}, rank{official, personal, qg_reference_order, group, of, weights: OFFICIAL|PERSONAL},
  coverage{v_factors{n,total:5,missing,required_ok}, axes{Q,G,V}, factors{available,total}, states, v_inputs_missing},
  flags, value_trap_gate, v_excluded, types{selected,reason}, price_status, rank_row, row_state, acquired_at, fiscal_year_end, profile, source_reason_codes }
```

- Page와 모든 행의 `v_source`는 늘 공식 V(`OFFICIAL_CENTRAL`)다. 게시본이 없으면 V가 그 사유와 함께 NA일 뿐, 기기 V로 채우지 않는다(DC-31).
- `identities`: 기업 목록 파일을 못 읽으면 `NOT_AVAILABLE`/`CATALOG_NOT_AVAILABLE`이고 TARGET 행이 없다. 다음 `page()`가 다시 읽는다. 결과가 없는 Page는 null이다.
- Page와 행에는 가격과 가격 파생값이 없다. 빠지는 것은 quotes, quote_meta, 월말 종가, EV, 수익률, `detail`, `reference_range`다.
- `price_basis_date`는 IEX 마지막 정규장 체결의 기준일이다(공식 종가 아님). `generated_at`은 게시 시각이다.
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
- `universeRanks()`, `rankFor({company_id, ticker})`: 개인 M3 순위(2.1.1). 순위와 사유만 있고 시총은 없다. M3 순위는 기기 시총의 순서라 가격 파생값으로 다룬다(P2-2a, Main 결정): `[data-ram-price]` 글자로만, 속성·정렬 값·저장소에는 넣지 않는다.
- 가격 탭 [SYNC]: 결과는 수와 코드뿐이다.
  - `useTabs(event)`, `loadTabs(event)`.
  - `syncSymbols(event, symbols, '1d'|'1mo', {kind, parent})`: Worker 허용 목록만. 다른 action의 다음 단계로 부를 때 `parent`에 그 action의 signal을 넘긴다.
  - `syncUniverse(event)`.
- `history(event, company, {range})` [HISTORY]와 `held(company, {range})`: 검증된 일별 이력이다. RAM에만 있고 가격을 포함한다.
- `quote(company)` → `{state:'OK', price, currency, source, read_at, as_of, time_status, freshness}` 또는 `{state:'NA', reason}`. `[data-ram-price]` 표시 전용이다.
  - company: `{code}`(Universe 코드) 또는 `{company_id, ticker}`(TARGET).
  - 기기 DB에 저장된 시세는 읽지 않는다(3절 STOPPED).
  - reason: `NO_DEVICE_PRICE`, 그리고 `QgvScores.collectQuotes`와 같은 규칙의 `IDENTITY_CONFLICT_WITHDRAWN`(식별 충돌로 멈춘 코드), `PRICE_IDENTITY_CONFLICT`(철회된 Universe 코드와 같은 티커의 TARGET). 점수 경로가 V를 내지 않는 기업에는 가격도 보이지 않는다.
- `periodReturns(period, companies)`(P2-2a, Main 결정 2026-10-25): `async` 함수다(대리 객체 'p'). companies는 `[{id, ticker, code}]`(code는 Universe 코드나 null). 결과는 얼린 `{state:'READY'|'NOT_LOADED', as_of, period, rows:{[id]: {state:'OK', value, end} | {state:'NA', reason}}}`.
  - 기간은 1D·5D·20D만이다. 그 밖(60D·120D·YTD·1Y·SINCE_START)은 `PERIOD_PENDING`, 배열이 아니면 `COMPANIES_INVALID`로 거절한다.
  - 식별 정지 규칙을 층 안에서 맨 먼저 적용한다(`quote()`와 같은 `stopped()`): `IDENTITY_CONFLICT_WITHDRAWN`·`PRICE_IDENTITY_CONFLICT` 행은 탭을 읽기 전이든 뒤든 값이 없다.
  - 클릭(`loadTabs`)으로 가격 탭을 읽기 전에는 `NOT_LOADED`, 다른 행은 `PRICE_TABS_NOT_LOADED`이고 요청하지 않는다.
  - 정의는 보고서 정의를 다시 쓴다: `ReportBenchmarks.periodWindow`(RAM 일별 탭의 S&P 500(SPY) 세션 N개, 기준은 기간 앞 세션 종가)와 `priceIndex(closes, {}, window, 'USD')`. value는 비율(0.012 = 1.2%). SPY가 없으면 `RETURN_SESSIONS_NOT_AVAILABLE`, 세션이 모자라면 `RETURN_HISTORY_TOO_SHORT`, 기준·마지막 종가가 없으면 `RETURN_BASE_CLOSE_MISSING`·`RETURN_LAST_CLOSE_MISSING`, 그 종목 종가가 없으면 `NO_DEVICE_PRICE`.
  - 종목 기호: Universe 코드가 있으면 `PriceStore.universeSymbol(code)`('NYSE:BRK.B' → 'BRK-B'), 없으면 티커의 '.'을 '-'로 바꾸고 대문자(`key()` 규칙).
  - 분할·배당 조정 없는 종가다(TA-G1 결정 대기). 화면은 값마다 '분할 미확인'을 보인다. 요청·저장·로그 없음, RAM만.
- `priceView`, `storeFacade`, `universeView`는 qgv·engines 전용이다(P2-2a부터 소스 규칙이 `storeFacade`도 막는다: prices.js·qgv.js·engines.js 밖 금지).
  - 가격 view는 하나뿐이다. 세션과 PriceStore가 view를 키로 상태를 두기 때문이다.
  - facade는 클릭으로 탭을 읽기 전에는 `{}`나 null을 준다.

## 7. 기기 저장: `IS2.store` (옛 키·스키마 그대로)

- 읽기는 자유롭다. 쓰기는 `WRITE` 클릭 안에서만 한다.
- `KEYS`: personal, settings, profile-drafts(-v2), playbook, investor-stars, backup-restored, virtual-trading-v-scores(v1·v2), unified-sheet-source, universe-source, private-history-origin, price-store-enabled, chart-user-objects, macro-cycle-user-estimate(백업 /5), recent-search(P2-1), 그리고 IndexedDB `investment-device-actual-v1`.
- 함수
  - 관심 기업(1.1.4): `prefs()` → `{state:'OK'|'EMPTY'|'INVALID', value}`. `savePrefs(event, next)`. 코드는 `PREFS_INVALID`, `PREFS_STORAGE_INVALID`다.
  - 최근 검색(1.1.4, P2-1 Main 결정): 옛 홈(home-screen.js)의 기기 목록을 키·모양 그대로 쓴다(`investment.web.v1.recent-search`, 엔티티 키만, 최신 먼저, 최대 6개, 검색어는 저장하지 않음).
    - `recent()` → 얼린 키 배열. 읽기는 자유롭다. 옛 readRecent처럼 잘못된 항목은 버린다(옛 KEY_SHAPE `COMPANY|INDUSTRY|INVESTOR|MACRO:…`를 받는다).
    - `pushRecent(event, key)` [WRITE]: 고른 기업을 맨 앞에 두고 같은 키는 지운 뒤 6개까지 저장하고 목록을 돌려준다. 새 화면은 `COMPANY:<id>`만 쓴다(그 밖은 `RECENT_KEY_INVALID`, 아무것도 바꾸지 않음).
    - `clearRecent(event)` [WRITE]: 목록을 지운다(홈의 '최근 지우기').
    - 검색 화면은 목록에서 기업을 고른 클릭(옵션 클릭, 또는 옵션을 고른 채 Enter → 기본 버튼의 click)에서만 부른다. 고른 옵션 없이 제출하면 저장하지 않는다. 저장이 거절되거나 실패해도 이동은 한다.
  - 가중치(2.2): `weights()`, `saveWeights(event, spec)`, `PRODUCT_PRESETS`.
  - 보유(6.1): `holdings()` → `{state:'OK'|'EMPTY'|'NOT_AVAILABLE', reason, snapshot, source, as_of}`. DB가 없으면 `DEVICE_STORE_NOT_OPENED`이고 DB를 만들지 않는다.
    - `indexedDB.databases()`가 없는 브라우저는 저장소 쓰기 클릭 안에서만 DB를 연다(그래서 그 안의 백업 내려받기에는 보유가 들어간다). 클릭 밖에서는 `DEVICE_STORE_NOT_OPENED`다.
  - 플레이북: `playbook()`, `saveThesis/saveHold/saveRecord(event, …)`.
  - 투자자 별표: `stars()`, `toggleStar(event, cik)`.
  - 기기 V 이력(DC-31): 읽지도 쓰지도 않는다. 두 키는 관문에서 멈춘다(3절 `STOPPED.localStorage`). 남은 값은 `vHistoryKeys.count()`(개수만)와 `vHistoryKeys.clear(event)`(WRITE 클릭)로만 다룬다. P1 층 어디에서도 `VirtualTradingVHistory.capture/captureV2/record/recordV2`를 부르지 않는다(소스 검사).
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
  - V가 든 결과에는 `v_source`(계산에 쓴 출처 id)가 있다: `target.draft/build/blockers/selectRuleB`는 11/16까지 `DEVICE_TEMPORARY`, `playbook.facts/judge`는 `OFFICIAL_CENTRAL`(DC-31, 10절).
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
| 불러오기(`loader.js`, 1.1절) | `LAYER_NOT_READY`(준비 전 행동), `LOADER_FAILED <파일>`(`IS2.ready` 거절, 실패 뒤 약속·행동), `LOADER_NAME_INVALID`(목록 이름, 빌드도 같은 이름을 거절), `TAG_INVALID`(core.js `h()`에 script 태그) | `IS2.NOT_READY`(state `NOT_READY`, reason `LAYER_NOT_READY`), `IS2.LOAD_FAILED`(reason `LOADER_FAILED`); `loadState()` `WAITING`/`LOADING`/`READY`/`FAILED`; 칩 '연결 전'/'연결 실패' |
| 관문(모든 action) | `CLICK_REQUIRED`(버튼류의 keydown, 자동 반복 keydown 포함), `ACTION_ALREADY_STARTED`(한 이벤트의 두 번째 최상위 action), `ACTION_KIND_NOT_COVERED`(부모가 갈 수 없는 kind의 중첩 실행), `ACTION_REQUIRED`(클릭 밖 쓰기, IndexedDB 쓰기 트랜잭션 포함), `DESTINATION_UNKNOWN`, `DEVICE_STORE_NOT_OPENED`, `ACTION_KIND_UNKNOWN`, `MARKET_STORE_STOPPED`(저장된 시세 기록 쓰기·범위 질의·색인, 그 저장소 삭제·이름 바꾸기, 클릭 안에서도) | — |
| `data` | `READER_MISSING`, `PUBLIC_FILE_UNKNOWN`, `PUBLIC_FILE_METHOD`, `PEEK_UNSUPPORTED`, `SEC_QGV2_UNAVAILABLE`/`SEC_QGV2_INVALID`(peek) | state `OK`/`NOT_PUBLISHED`/`FAILED`/`NOT_READ`, why `INVALID`/`NETWORK`/`HTTP`/`SCHEMA_NEWER`/`READER_MISSING`; refresh `APPLIED`/`UNCHANGED`/`FAILED`/`LOADING` |
| `qgv.page` | `READER_MISSING`, `ABORTED`(signal) | Page state `READY`/`NO_DATA`/`DATA_FORMAT_NEWER`/`READ_FAILED`, reason `SEC_QGV2_NOT_PUBLISHED`/`SEC_QGV2_NOT_AVAILABLE`/`SEC_QGV2_SCHEMA_NEWER`/`SEC_QGV2_INVALID`/`SEC_QGV2_UNAVAILABLE`/`V2_SCORES_NOT_AVAILABLE`; identities `CATALOG_NOT_AVAILABLE` |
| `qgv` 그 밖 | `PAGE_UNKNOWN`, `PAGE_NOT_READY`(결과 없는 Page), `SCOPE_UNKNOWN`, `PRESET_UNKNOWN`, `GATE_INVALID` | preview state `READY`/`INVALID`, reason `WEIGHTS_INVALID` |
| 행 NA | — | V: coverage V 사유(`NO_DEVICE_PRICE`, `SOURCE_NOT_AVAILABLE`, `FINANCIAL_PROFILE_V_NOT_DEFINED`, `CROSS_SECTION_TOO_SMALL`, `AXIS_WEIGHT_INSUFFICIENT` 등); total: `DATA_FORMAT_NEWER` → `CALC_VERSION_MISMATCH` → 엔진 total_reason; rank: `QG_REFERENCE`, `OUTSIDE_UNIVERSE`, `REFERENCE_ONLY`, `NOT_RANKED` 또는 total 사유 |
| `prices` 로그인 | `OFF`, `NOT_READY`, `PREPARE_TIMEOUT`, `CANCELED`, `AUTH_FAILED` | status google.error(`AUTH_REQUIRED`, `AUTH_POPUP_CLOSED` 등) |
| `prices.readUniverse` | `UNIVERSE_SOURCE_NOT_SET`, `UNIVERSE_SOURCE_INVALID`, `AUTH_REQUIRED`, `SOURCE_TOO_LARGE`, `CANCELED`, `UNIVERSE_READ_FAILED` | inputs `READY`/`SEC_INPUTS_UNAVAILABLE`/`SEC_UNIVERSE_SHARES_INVALID`/`SEC_UNIVERSE_SHARES_SCHEMA_NEWER`/`SEC_INPUTS_NOT_CONNECTED` |
| `prices.history` | `OFF`, `HISTORY_UNAVAILABLE`, `REQUEST_INVALID`, `ORIGIN_UNAPPROVED`, `AUTH_REQUIRED`, `CANCELED` | — |
| `prices` 탭·동기화 | `SYMBOLS_INVALID`, `INTERVAL_INVALID` | 결과 state·reason_codes(옛 PriceStore 코드), 종목별 code(`WORKER_ALLOWLIST` 등) |
| `prices.quote` | — | NA `NO_DEVICE_PRICE`, `IDENTITY_CONFLICT_WITHDRAWN`, `PRICE_IDENTITY_CONFLICT` |
| `store` | `PREFS_INVALID`, `PREFS_STORAGE_INVALID`, `RECENT_KEY_INVALID`(pushRecent), `WEIGHTS_INVALID`, `WEIGHTS_STORAGE_INVALID`, `SHEET_SOURCE_INVALID`, `SHEET_SOURCE_NOT_SET`(useSheet), `UNIVERSE_SOURCE_INVALID`, `REQUEST_INVALID`(Worker 주소), `BACKUP_INVALID`, `BACKUP_TOO_LARGE`(지나가는 옛 코드: `BACKUP_USER_OBJECTS_UNAVAILABLE`/`_UNREADABLE`/`_WRITE_FAILED`, `BACKUP_RESTORE_FAILED`) | marketQuotes.count null(알 수 없음); holdings `NOT_AVAILABLE` + `CATALOG_NOT_AVAILABLE`/`DEVICE_STORE_NOT_OPENED`/`DEVICE_STORAGE_UNAVAILABLE`; prefs·weights·playbook state `OK`/`EMPTY`/`INVALID` |
| `engines.target` | `PAGE_UNKNOWN`, `QGV2_NOT_READY`, `CATALOG_NOT_AVAILABLE`, `TARGET_V1_STATE_INVALID`, `TARGET_V1_ANSWERS_RESET`(두 번째 누름 필요), `V_SOURCE_MISMATCH` | finalize outcome `FINALIZED`/`BLOCKED`/`DRAFT_REGENERATED`/`RELOAD_REQUIRED`(+ blockers 코드); selectRuleB `SELECTED`/`NOT_READY`/`NOT_DUE`/`QGV2_NOT_READY`; syncScoringPrices `NOTHING_PENDING` 또는 동기화 state |
| `engines.playbook` | `PLAYBOOK_INVALID`, `JUDGEMENT_UNKNOWN` | 판정 코드(PlaybookEngine); recorded_reason `JUDGEMENT_NOT_RECORDED`('기록 안 됨'), `NOTHING_TO_RECORD`('기록할 발생 신호 없음') |
| `engines.virtual` | `NOT_IN_P1`(run), `PAGE_UNKNOWN`(rehearse) | stored state `NOT_STARTED`/`NOT_AVAILABLE`(+ `OFF`/`REQUEST_INVALID`/`ORIGIN_UNAPPROVED`/`AUTH_REQUIRED`/`PUBLIC_CATALOG_UNAVAILABLE`), 종목별 `PRICE_NOT_FETCHED`; compare `COMPARE_NEEDS_TWO_SETS`; forward `LOADED`/`NOT_PUBLISHED`/`NOT_AVAILABLE` |
| 중앙 V(DC-31, 10절) | `V_HISTORY_STOPPED`(관문, V 이력 키) | Page reason / price_basis.reason `OFFICIAL_NOT_PUBLISHED`/`OFFICIAL_INVALID`/`OFFICIAL_UNAVAILABLE`/`OFFICIAL_INPUTS_DIFFER`; 행 V `NO_IEX_TRADE`·`ODD_LOT_ONLY`·`PRICE_SYMBOL_UNMAPPED`·`ADR_RATIO_UNCONFIRMED`·`SPLIT_AFTER_SHARE_COUNT`·`PRICE_DEPENDENT_NOT_COMPUTABLE`·`OFFICIAL_MONTH_END_NOT_AVAILABLE`; 순위 `ISSUER_RANKED_ONCE`; 상태 파일 attempt `SUPPLY_FAILED`/`VERIFY_FAILED`/`NOT_RUN`/`NO_OFFICIAL_YET`, `OFFICIAL_STATUS_INVALID`; facts `V_HISTORY_NOT_PUBLISHED`; preview `WEIGHT_STAGES_NOT_REBUILT` |

## 10. V 출처 전환: 공식 V만 표시 (DC-31, 소유자 결정 2026-10-31, PR-1a)

소유자 결정(DC-31, 기기 V 폐지): 화면은 기기 V를 계산하지도 보이지도 않는다. 중앙 게시 V(`qgv-official.json`)만 보인다. 기기 V 이력은 없다. 중앙 V가 없거나 늦으면 기기 V로 채우지 않는다. 마지막 공식 V를 그 갱신 시각과 함께 보이고, 기준을 넘으면 STALE로 표시한다. TARGET v1 빌더의 V 출처는 11/16 PR까지 그대로다.

이 PR(PR-1a)은 새 앱과 `qgv-scores.js` 게시본 모드다. 옛 화면(라이브 사이트)은 PR-1b에서 바꾼다. 그래서 라이브 사이트 동작은 이 PR로 바뀌지 않는다.

**판독기와 자료**
- `data.js`
  - `FILES`에 `qgv-official.json`, `qgv-official-status.json`을 넣었다.
  - `official()`은 게시본을 `QgvOfficial.load(publicView)`로 읽는다. 옛 `web_assets/qgv-official.js`를 바이트 그대로 쓴다(`loader.js` LOAD_ORDER, `sec-qgv2.js` 뒤). 검증은 그 판독기의 엄격 검증이다.
  - 상태 파일은 `requireStatus`로 검사한다. Python `require_status`와 같은 규칙, 같은 순서다. 깨지면 `OFFICIAL_STATUS_INVALID`다.
  - 한 페이지에 한 번 읽는다. "공개 자료 다시 읽기"(`refresh`) 뒤에 다시 읽는다(구독자는 `{reason:'OFFICIAL'}`을 받는다). 기기에 아무것도 저장하지 않는다. 마지막 좋은 게시본은 서버가 지킨다.
- `qgv.js`
  - `OFFICIAL_READER`는 `QgvOfficial`이다. `vSource()`는 늘 `OFFICIAL_CENTRAL`이다.
  - `V_SOURCES`는 바꾸지 않았다. `QgvOfficial`·`TargetV1Builder`와 같아야 한다는 시험이 11/16까지 있다. `DEVICE_TEMPORARY`는 숨은 TARGET 엔진 결과(`engine_v_source`)에만 붙는다. Page나 행에는 붙지 않는다.

**점수 접근자 `qgv-scores.js` 게시본 모드** (계산 논리, 독립 검토 대상)
- `officialPage(win, {publication, v2Inputs, identities, reason})`: 화면이 함께 쓰는 결과다. `publication_id`(와 입력 객체·페이지 식별자·참고 행)로 기억한다. `QgvOfficial.validate`를 통과한 게시본만 받는다.
- `compute({publication, ...})`
  - 게시된 행을 엔진 모양 행으로 바꾼다. 엔진을 부르지 않고 가격도 쓰지 않는다. Q·G·V·종합 점수·플래그는 게시본 값 그대로다.
  - 순위도 게시본 것이다(D11). 한 CIK에 공식 순위 한 자리다(D-CV8/9). 그 CIK의 `rank_row` 코드 행에만 순위가 붙는다. 같은 CIK의 다른 코드 행은 `rank_row`를 들고, 순위 사유는 `ISSUER_RANKED_ONCE`다.
  - `rank_row`가 가리키는 TARGET 행이 페이지에 없으면(기업 목록을 못 읽음) 그 CIK의 첫 횡단면 Universe 코드 행에 게시 순위를 붙인다. 게시된 자리가 빠지지 않는다.
- 점수 파일과 게시본이 다를 때
  - 불러온 `sec-qgv2.json`이 게시본의 입력(같은 `as_of`)일 때만 그 파일로 커버리지와 모델 지표를 보탠다.
  - 다른 파일이면 게시본만으로 행을 만든다. Page 사유는 `OFFICIAL_INPUTS_DIFFER`이고 모델 후보는 고르지 않는다.
- V가 없는 이유
  - 게시본의 `price_status`(`NO_IEX_TRADE`, `ODD_LOT_ONLY`, `PRICE_SYMBOL_UNMAPPED`, `ADR_RATIO_UNCONFIRMED`, `SPLIT_AFTER_SHARE_COUNT`)를 쓴다.
  - 그 밖에 `PRICE_DEPENDENT_NOT_COMPUTABLE`, 월말 체결가가 없으면 `OFFICIAL_MONTH_END_NOT_AVAILABLE`이다. 기기 문구(`NO_DEVICE_PRICE` 등)는 화면에 나오지 않는다.
  - 데이터 상태는 `CENTRAL_V_MISSING`(공식 V 없음)이다.
- 게시본이 없을 때: `OFFICIAL_NOT_PUBLISHED`, `OFFICIAL_INVALID`, `OFFICIAL_UNAVAILABLE` 중 하나다.
  - 가격 없는 Q·G 계산을 쓴다. 모든 V는 그 사유와 함께 NA다.
  - Q·G 종합 점수는 QG 참고 목록으로만 간다. 기기 V는 절대 쓰지 않는다.
- 개인 미리보기 = 게시된 요인 점수로 다시 계산한다(가격 없음).
  - 축마다: 개인 안쪽 가중치가 공식과 같으면 게시된 축을 쓴다. 다르면 `QgvV2.axisScore(게시 요인 점수, 축, 안쪽 가중치)`다. 요인 백분위는 가중치와 무관하므로 정확하다.
  - 축 가중치는 `compositeWeights(tree.axis, 게시 유형 가중치, 유형 설정 기본값)`이다. 유형 가중치를 끄면 축 가중치를 정규화한다.
  - 가치 함정 관문은 게시된 Q 산업 백분위로 판정한다. Q를 다시 계산하면 엔진 규칙(`cross`, 산업 8곳 이상)으로 백분위도 다시 낸다.
  - 종합은 `qgv-v2.js` scoreUniverse 식 그대로다. 같은 합성 입력에서 기기 엔진과 정확히 같다는 시험이 있다(`qgv_scores_node_test.js`).
  - 개인 순위와 개인 QG 참고 순서도 한 CIK에 한 자리다. 대표 코드는 Python `assign_ranks`와 같은 규칙이다(Universe CIK의 LIVE/STALE TARGET 행, 없으면 그 CIK의 첫 횡단면 Universe 코드). 같은 CIK의 다른 코드 행은 `rank_row`(개인)를 들고 사유는 `ISSUER_RANKED_ONCE`다. 공식 가중치로 미리보면 모든 행의 개인 순위·QG 순서가 게시본과 같다(시험).
  - 가중치 단계 표는 NA다(`WEIGHT_STAGES_NOT_REBUILT`). `qgv-v2.js`는 고치지 않는다.
- 기기 경로 `collectQuotes` / `pageResult`는 그대로 둔다. 옛 앱과 TARGET이 아직 쓴다(PR-1b와 11/16에 걷어낸다).
- `qgv-scores.js`는 해시 고정 파일이다. `pages_artifact_guard.py` `APPROVED_SHA256`에서 이 파일 하나만 다시 고정했다.

**Page 기준(`price_basis`)과 화면 문구**
- `price_basis` = `{kind:'CENTRAL_IEX', label, reason, price_basis_date, generated_at, verified_at, publication_id, calc_version, sessions, stale, calc_differs, inputs_match, attempt, attribution}`.
  - `sessions`: 가격 기준일 뒤 끝난 뉴욕 정규장 수다(`QgvOfficial.sessionsAfter`, 16:00 뉴욕 마감).
  - **STALE**: `FRESH_SESSIONS`=2를 넘으면 `stale`이다(D-CV6, 소유자 확인 기본값). 셀 수 없으면(기준일이 기기 시계보다 뒤, 달력 범위 밖) `stale`은 null이고 화면은 "STALE 판정 불가"를 보인다(새것으로 보이지 않게).
  - `calc_differs`: 불러온 `sec-qgv2.json`의 계산 버전이 다르면 "계산 버전 다름" 표시를 한다. 값은 게시본 그대로다.
  - `attempt`: 상태 파일의 마지막 게시 시도다.
- 1.1 리더보드와 검색 카드(`screen-qgv-live.js`, `screen-search-live.js`)가 보이는 것
  - "공식 V · IEX 마지막 체결가 기준(공식 종가 아님)", 가격 기준일, 게시 시각(날짜와 UTC).
  - STALE 칩(또는 STALE 판정 불가), 계산 버전 다름 칩, 마지막 실패한 게시 시도(날짜와 UTC).
  - 검색(기업) 카드도 같은 게시 시각·마지막 실패 시도·IEX 출처 문장과 약관 링크를 V 출처 줄 아래에 보인다.
  - IEX 출처 문장과 약관 링크(IEX HIST 약관 01조, DC-29). 문장과 링크는 게시본에서 읽는다.
- 순위 이름: 공식 순위는 "공식 순위 · 중앙 게시 V"다. 개인 미리보기는 "내 설정 순위 · 공식 V로 다시 계산 · 공식 순위 아님"이다. 출처를 모르면 "공식 순위 아님"이다.
- 가격 버튼
  - Universe 가격 읽기는 이제 M3 시총 순위에만 쓴다. 버튼 이름은 "시총 순위(M3)용 가격 불러오기 · 이 기기에서만"이다(`prices.universeView`, 소유자 확인 기본값).
  - V를 위한 "가격 불러오기" 미러 버튼은 지웠다.

**엔진(`engines.js`)**
- 플레이북 사실과 리허설은 Page의 중앙 결과(`qgv.centralComputed`)를 읽는다. `v_source`는 `OFFICIAL_CENTRAL`이다.
  - 기기 V 이력이 없으므로 `v_prev20`은 NA다(`V_HISTORY_NOT_PUBLISHED`). V 변화 규칙은 그 값이 없다고 보고한다. 엔진은 고치지 않았다.
  - `prepareScores`는 뉴스 RAM을 채우는 데만 부른다. `sec-qgv2.json` 없이 부르므로 기기 V를 계산하지 않는다.
- TARGET v1(초안, R-B, 확정)은 11/16까지 숨은 기기 결과를 읽는다. `await qgv.forEngines(pg)`로, 빌더가 물을 때마다 `QgvScores.pageResult`를 부르고(그 기억이 Universe 읽기·기기 입력·preset/gate별로 같은 결과를 돌려준다) 화면에는 쓰지 않는다. 중앙 Page는 게시본으로 기억하므로 같은 객체로 남지만, 뒤의 Universe 읽기나 `setProfile`은 빌더 결과에 반영된다. 기록은 `engine_v_source`(`DEVICE_TEMPORARY`)다.

**기기 V 이력**
- `store.vHistory`를 지웠다.
- 두 키(`investment.web.v1.virtual-trading-v-scores`, `investment.web.v2.virtual-trading-v-scores`)는 `action.js` `STOPPED.localStorage`에 넣었다. 뷰로 읽으면 없음이고, 키로 쓰거나 지우면 클릭 안에서도 `V_HISTORY_STOPPED`다. 러너의 V 저장소는 비어 있어 V 기울기 신호가 나지 않는다.
- 이미 저장된 값은 사용자가 지울 때까지 남는다. `store.vHistoryKeys.count()`(개수만)와 `clear(event)`(WRITE 클릭, DC-18 선례)가 그 수동 설정 동작이다. 자동 삭제는 하지 않는다(소유자 확인 기본값).

**남은 것**: PR-1b(옛 화면, 방향 규칙 DC-31a–d, 문서), 11/16 PR(TARGET V 출처, `V_SOURCES`에서 `DEVICE_TEMPORARY` 정리, 기기 경로 삭제).

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
  - 순위 문구: '공식 순위 · 중앙 게시 V'(DC-31로 바뀜, 그전에는 '임시 V 기준 순위 · 공식 순위 아님'). `qgv.rankLabel()`과 `rank_label`로 준다.
  - Universe 출처: 통합 시트와 따로 둔다(옛 동작). P2 설정은 '통합 시트와 같게'를 클릭(`universeSource.useSheet(event)`)으로 줄 수 있다. 이 출처는 기기 가격을 읽는 사용자 가격 시트다. Universe504 목록 자체는 공개 파일(`universe-codes.json`)이다(2026-10-27 경계, 아래).
  - 구글 켬/끔: 옛 동작대로. 기기 DB가 이미 있을 때만 읽고, 로그인 준비 클릭 안에서만 쓴다(옛 로그인 클릭이 켬을 썼다). 로그아웃은 바꾸지 않는다(옛 연결 해제와 같음). 클릭 없이는 아무것도 쓰지 않는다. GIS 스크립트는 클릭 안에서만 받으므로 다시 온 사용자도 페이지마다 준비 탭은 필요하다.
- 휴대폰 첫 화면 비용: 미루지 않고 P2-1의 첫 작업으로 한다. boot.js·셸을 먼저 그리고 엔진·P1 층은 첫 그림 뒤에 불러온다. 목표(390×844, 150 ms RTT·1.6 Mbps·CPU ×4): 첫 화면 2,000 ms 이하, 첫 전송 100 KB 이하. 측정을 시험으로 고정한다. 다른 화면 PR은 그 구조 위에서 만든다. 검토 측정(결정 전): 첫 화면 1,558 → 4,119 ms, 전송 13 KB → 569 KB, 스크립트 7 → 78개(이번 두 검증기로 80개).

### Main 결정 2026-10-25 (P2-2a 메뉴 1 QGV · 1.1 리더보드, 소유자 확인 항목은 PR 본문)

- `screen-qgv-live.js`를 `LOAD_ORDER`의 화면 논리 파일로 더한다(`screen-search-live.js` 뒤). 404·불러올 때 오류는 메뉴 9개 모두의 `LOADER_FAILED`다.
- `leaderboard-screen.js`(67 KB)는 불러오지 않고 작은 순수 부분만 이식한다(위 5절 `rows`). 이 결정은 P1의 'P2-2가 옛 함수로 붙인다' 계약을 바꾼다(소유자 확인 13).
- `qgv.model(page)`, `prices.periodReturns()`, 새 사유 글(5절, 6절). 수익률 기간은 보고서 정의(`ReportBenchmarks`) 재사용, 60D·120D·YTD·1Y는 결정 대기(IA-12).
- M3 순위는 가격 파생값으로 다룬다(`[data-ram-price]` 글자만).
- 화면은 기본 프로필의 공유 Page만 쓰고 `setProfile`·`page({preset|gate})`를 부르지 않는다(공유 메모 보호). 개인 결과는 `preview`로만 본다.

### 결정됨 2026-10-27 (소유자: 공개/개인 경계 · 기업 검색 · 바뀌는 화면, DC-22 · DC-23)

- **공개 데이터**(처음 쓰는 기기·로그인 안 한 상태에서도 같게): Universe504 목록, 기업 검색, QGV v2 점수·순위, 기본 프리셋, 중앙 V 점수·순위(게시 후), TARGET(**확정된 TARGET v1만**. TARGET v0(카탈로그 19)은 QGV와 전혀 무관해 공개 TARGET이 아니다 — DC-24), 갱신 시각·calc_version. 모두 공개 파일(4절 `IS2.data`)에서 읽는다. 기기 저장(7절 `IS2.store`)이나 로그인이 있어야만 보이는 공개 자료 화면은 고친다(DC-22).
- **개인 데이터**(로그인에 따라 다름): 포트폴리오, 사용자 QGV 가중치. 저장은 당분간 (a) 그 기기에만(7절). 기기 간 동기화 (b)는 별도 결정 전까지 만들지 않는다. 그 밖에 개인으로 둘 후보는 USER_DECISIONS_PENDING `PRIVATE-LIST`(목록만 제안).
- **공개도 저장도 하지 않음**: 원시 가격, 보유 원본, 기기 가격으로 계산한 임시 V. 6절 그대로(GSQ-024, 클릭할 때만 요청, RAM에만).
- **기업 검색(DC-23)**: 공용 부품 하나. 검색창 하나에서 티커·영문 회사명으로 찾고 입력하는 대로 후보를 보인다. 범위는 공개 파일에서 받아 메모리에 올린 Universe504 목록뿐이다(입력마다 네트워크 요청 없음). 결과 없음과 상장 종료(WBD 등) 표시를 둔다. 키보드와 모바일 화면 키보드로 쓴다. 기업을 고르는 모든 화면이 같은 부품을 쓴다. 이에 따라 Universe504 밖 기업과 한글명은 검색 대상이 아니다.
  - 구현(검색 부품 PR, #415 위): 첫 그림 절반은 `IS2.parts.searchBox(id, label)`(parts.js, P2-1 `screen-search.js`의 상자를 옮김; `inputmode=search`·`enterkeyhint=search`·`autocorrect=off`·`autocapitalize=characters`, 자리 글 '티커 · 영문 회사명'), 논리 절반은 `IS2.searchPart`(`search-part-live.js`, `LOAD_ORDER`의 P1 층 뒤·화면 논리 파일 앞).
  - `IS2.searchPart.index()`: `IS2.data.universe()`(504코드)와 `company-names-ko.json`(영문 SEC 이름, 코드 → company_id 연결)을 페이지당 한 번 읽어 메모리에 둔다. 빠진 파일이 있으면 다음 attach 때 다시 읽는다. 순서: 티커·코드 정확 → 티커 앞부분 → 회사명 앞부분 → 회사명 낱말 앞부분 → 티커 일부 → 회사명 일부, 같으면 티커 순. 후보 8개까지. 한글 입력은 '티커나 영문 회사명으로 찾아 주세요'. 카탈로그(TARGET v0)는 읽지 않는다(DC-24).
  - `IS2.searchPart.attach(route, box, {onPick})`: 콤보 상자(P2-1 방식: 방향키·Home/End·Enter·Escape, IME 중 키 무시, 마우스는 강조만). 고른 항목은 `onPick(event, entry, {chosen})`로 화면에 넘긴다(홈·기업 화면은 고른 항목만 최근 검색으로 저장하고 `#/company/<id>`로 이동). 고르지 않은 제출은 정확히 하나인 일치로 가고, 없으면 목록에 '일치하는 기업이 없습니다 · Universe504 안에서만 찾습니다'를 보이고 이동하지 않는다(P2-1의 `#/company/<입력>` 이동은 없앰). 목록이 오기 전(준비 전 포함)의 제출은 목록이 오면 그때 입력으로 한 번 돈다.
  - 상장 종료: `IS2.searchPart.LISTING_ENDED`(코드 → 날짜, 표시 전용). 서버 표 `sec_universe_shares.LISTING_ENDED_CODES`와 같아야 한다(파이썬 대조 시험). 후보와 기업 화면에 '상장 종료 2026-10-06 · 점수 없음'. 공개 사유 코드(`LISTING-ENDED-CODE`)가 정해지면 공개 파일에서 읽도록 바꾼다.
  - 기업 화면의 소속 표시는 'Universe504'·'Universe504 밖'만 쓴다(TARGET v0 소속은 표시하지 않음, DC-24).
  - 시험: 새 `web_app_search_part_node_test.js`(실제 504코드·이름표로 범위·순서·정확 일치·상장 종료·한 번 만들기), 새 `test_web_app_search_part.py`(상장 종료 표 대조), `web_app_reuse_node_test.js`(콤보 상자는 parts.js·search-part-live.js에만, 모바일 키보드 속성, `IS2.searchPart` 키), `web_app_home_browser_test.js`(영문 이름·한글 안내·Universe504 밖 기업 없음·WBD 표시·제출 일치 없음 그대로·기업 화면 상장 종료 줄·QGV 카드 갱신 시각·관심 기업 저장 오류에도 개발자 기본 목록), `web_app_shell_browser_test.js`(제출은 `IS2.ready` 뒤).
- **바뀌는 화면(DC-23)**: 기준 기업·갱신 시각·자료 버전에 따라 내용이 바뀌는 화면은 갱신 시각과 calc_version을 화면에 표시하고, 상태(기준 기업 선택 전·후, 갱신 중, 데이터 없음/STALE, 실패)를 시안 보드로 그린다.
- **P2-2a 반영(#415)**: 리더보드의 모든 화면 상태(READY·NO_DATA·READ_FAILED·DATA_FORMAT_NEWER)에 기준 칩을 둔다. 내용은 점수 갱신(`page.as_of`, UTC 날짜·시각) · 마지막 확인(`data.publication().checked_at`) · 계산 버전(`page.calc_version`)이고, 파일이 `stale_after_seconds`를 넘으면 'STALE · 점수 파일 기한 지남'을 붙인다. '공개 자료 다시 읽기' 버튼은 `data.refresh(event)`(PUBLIC_REFRESH, 공개 파일만, 클릭 1번 = action 1개)를 부르고 결과를 보인다: 갱신 중 · 새 게시본 없음 · 새 게시본 적용 · 갱신 실패(이전 값 유지). 2.1.7 모델 후보에도 갱신 시각·계산 버전을 적는다. 가격 시트 코드의 글은 '가격 시트'로 고쳤다(`UNIVERSE_SOURCE_NOT_SET` = '가격 시트 없음 · Universe 목록은 공개 파일', `UNIVERSE_NOT_READ`·`NOT_IN_UNIVERSE`·`UNIVERSE_READ_FAILED`·`UNIVERSE_SOURCE_INVALID`도 같은 뜻으로).
- **TARGET v0 제외(DC-24, 사용자 2026-10-27)**: QGV 화면에 v0을 쓰지 않는다. #415 리더보드는 Universe504 행만 그린다(v0 범위 칩·'Universe 밖 TARGET' 상자·TARGET 표지·'TARGET만' 필터·포트폴리오 내 순위 열을 뺐다. D12와 부딪혔고 2026-10-28 `D12-V0` (a)로 확정). 층(5절 `qgv.page`)은 옛 엔진 계약 때문에 카탈로그 행(`target`, `OUTSIDE_UNIVERSE`, `reference_only`)을 아직 들고 있다. 화면은 `rows(page,{scope:'UNIVERSE'})`만 쓴다.
- **남은 불일치**: 기업 페이지 QGV 카드에 갱신 시각·calc_version이 없고, 홈의 개발자 기본 목록이 관심 기업 저장 자료를 읽지 못하면 같이 숨는다 → 검색 부품 PR에서 고침(QGV 카드 아래 '점수 갱신 … UTC · 계산 버전 …', 저장 오류 안내와 함께 기본 목록. 기본 목록은 `HOME-DEFAULT-V0` (c), 2026-10-28: 확정된 TARGET v1이 공개 파일로 게시되면 그 목록으로 바꾸고 그 전까지 그대로). TARGET v1 확정본을 공개 파일로 게시하는 길이 아직 없다(DC-24: 확정되면 게시, 파일·검증기 PR은 별도 승인). QGV 종합·순위는 V가 필요해 중앙 V 게시 전에는 처음 쓰는 기기에 없다(QG 참고 목록만). 저장 문제가 아니며 10절 전환점에서 풀린다.

### 아직 정할 것

- 일일 보고서·보고서 모델, 가상매매 기록 실행, 세트 B/C/D는 P2-6에서 정한다(daily-report.js는 불러오지 않음).
- 중앙 V 모드의 엔진 계약(10절 7)과 출처 없는 기록(10절 8).
- P2-6 보유 쓰기(Main): 보유만 쓰는 store 함수(`WRITE`, 옛 `DeviceActual.restoreHoldings`로 `actual`만 커밋)를 붙인다. 옛 `DeviceActual.mount` 화면(저장·가져오기·삭제)은 시세 기록을 함께 쓰고 진짜 window에서 돌아 다시 쓰지 않는다(3절 STOPPED).
- 손으로 넣는 시세·환율(소유자 또는 Main): 옛 기기 보유 화면은 그 값을 시세 기록(`market`)에 저장했다. DC-18 뒤에는 둘 곳이 없다. 선택지: RAM에만 두기(새로고침하면 사라짐), 사용자 시트에 쓰기, 기능 빼기. P2-6 전에 정한다(USER_DECISIONS_PENDING `MANUAL-QUOTE`).

## 12. 시험

- 노드 시험(`node implementation/tools/<파일>`)
  - `web_app_reuse_node_test.js`: 불러오기 목록(index.html 첫 화면 + `LOAD_ORDER`, 빌드·도우미·로더가 같은 목록), 빌드 실패 규칙, 이름 규칙(한 표의 이름을 로더·빌드·도우미에 모두 넣어 받고 거르는 것이 같음, loader.js `NAME` 줄이 빌드와 다르면 빌드 실패), 로더(가짜 window: 첫 그림 전에는 넣지 않음, `async=false` 순서, `IS2.ready`·`LOADER_FAILED`, 대리 객체 종류별 동작과 실패 뒤 복원, 대리 객체 API = 실제 층 API), 화면 파일이 불러올 때 층을 건드리지 않음, 소스 규칙(스크립트 요소: createElement·createElementNS·`h()`의 'script', 계산된 태그, 간접 호출의 예를 잡는지도 확인), `h()`의 `TAG_INVALID`.
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
- `web_app_first_paint_browser_test.js`(P2-1a): 개발 빌드를 Pages처럼(gzip) 띄우고 CDP로 390×844, 150 ms·1.6 Mbps·CPU ×4, 콜드 캐시에서 3번 잰다. 첫 화면(`is2-first-paint`와 FCP 중 늦은 것) ≤ 2,000 ms, 첫 전송(그때까지 끝난 요청의 encodedDataLength 합) ≤ 100 KB를 중앙값으로 확인하고 `FIRST_PAINT ms=… first_kb=… ready_ms=… total_kb=…`를 찍는다. 실행마다 제한이 실제로 걸렸는지(CPU 고정 루프 비, 문서 요청 ≥ 지연, 가장 큰 응답 ≥ 대역폭 시간) 먼저 확인하고 `FIRST_PAINT_CONTEXT`에 잰 값과 모형(루프백 HTTP/1.1, 연결 준비 없음, 배율 1)을 찍는다. 첫 그림 순간의 구조(검색창·메뉴·탭, 칩 '연결 전', 실패 안내 없음, 옛 모듈 없음, 대리 객체 `NOT_READY`, `LOAD_ORDER` 요청 없음)와, 제한 없이 대리 객체 계약(첫 파일을 붙잡아 둔 채 확인)·실패(404, 실행 중 오류 → `LOADER_FAILED`, 칩 '연결 실패', 고정 안내와 새로고침 버튼이 390×844 화면 안에 보이고 다음 경로에도 남음, 404 경우 버튼을 누르면 페이지 새로고침 말고는 요청이 없고 다시 실패해 안내가 다시 뜸)도 본다. `FIRST_PAINT_ENCODING=identity`면 압축 없이 잰다.
- `web_app_shell_browser_test.js`(P0): P2-1 전까지는 고치지 않고 통과했다. P2-1에서 한 군데만 바꿨다(아래, Main 결정 2026-10-25).
- `web_app_home_browser_test.js`(P2-1 메뉴 0): 1440·390에서 홈(첫 그림의 검색 상자, 준비 전 '불러오는 중', 콤보 상자 ARIA, 한글명 검색, IME 중 키 무시·조합 중에도 목록 갱신·입력 요소 유지), 선택(방향키+Enter·포인터 클릭은 진짜 클릭으로만 최근 검색 저장, 합성 `el.click()`·dispatchEvent는 이동만, 고른 옵션 없는 제출은 정확히 하나 맞는 기업 또는 `#/company/<검색어>`), 최근 칩·지우기(초점 유지), 개발자 기본값 표시와 ★ 토글(이름은 '즐겨찾기'로 고정·상태는 aria-pressed, 진짜 클릭으로만 prefs 저장, 해제하면 그룹 구성원에서도 뺌), 기업 화면 카드(QGV 숫자는 층의 행 그대로, NA는 reasonText, 매크로는 `IS2.engines.macro.current()`와 같은 값, 소식은 fixture의 최신 공시와 같은 줄), 이 화면의 누름 대상 44 px, 모르는 id, `IS2.selection` 유지, 명언 출처 링크, 경계(같은 출처·FILES만, 클릭 없는 저장 0, 콘솔 오류 0, `[style]` 0, 390 가로 넘침 없음)를 본다. 준비 전(층 파일을 붙잡아 둠): Escape는 글자를 남김, 초점이 떠나면 목록 숨김, 같은 렌더의 넘겨주기(같은 입력 요소·초점 유지·입력한 글자의 옵션·키 하나에 목록 한 번만 다시 그림), 준비 전에 떠난 경로는 채우지 않음. 마우스로 강조한 옵션이 있어도 검색 버튼은 입력한 글자로 간다. 따로 두 문맥: 시험이 기기 저장소에 보유 기록을 넣어 포트폴리오 카드 있음(nvda 수량 10)·없음(amd 수량 0, qcom 기록 없음), `screen-search-live.js`가 404일 때 `LOADER_FAILED`(기업 머리 고정 문구, ★ 꺼짐, 셸 안내, 다른 메뉴의 층도 거절, 잡히지 않은 오류 0).
- P2-1이 바꾼 기존 시험(화면이 공개 자료를 읽기 시작해서):
  - `web_app_data_layer_browser_test.js` A: 경로를 열 때 읽는 파일을 화면별로 본다. 자리표시 메뉴는 0개, 홈은 색인 정적 파일 3개(`actual-catalog.json`·`company-names-ko.json`·`universe-codes.json`)만, 기업 화면은 `FILES` 안의 이름만. 재사용 수 60.
  - `web_app_shell_browser_test.js`(**Main 결정 2026-10-25, 승인**: P2-1 명세는 이 시험을 그대로 두라고 했지만, 같은 명세가 기업 화면에 `IS2.data.ready()`를 요구해 그대로는 통과할 수 없다): 다른 확인은 그대로 두고, `IS2.data.ready()`가 읽는 핵심 파일 중 오프라인 빌드에 없는 실사이트 전용 공개 파일 정확히 2개(`sec-qgv2.json`·`sec-public-inputs.json`)의 404만 콘솔 오류에서 뺀다. 시험은 먼저 두 파일이 오프라인 빌드에 없음을 확인하고(있으면 실패), 그 밖의 404·오류는 그대로 실패다. 기업 화면이 `IS2.data.ready()`를 부르면 브라우저가 그 404를 콘솔에 남기기 때문이다.
  - 기업 검색 색인(**Main 결정 2026-10-25, 승인**): 명세 초안의 `IS2.data.shares()` 대신 정적 `universe-codes.json`(`IS2.data.universe()`)과 이름표의 `codes()`(코드 → company_id)로 만든다. 더 가볍고, 홈이 검색만 하려고 핵심 파일 묶음을 읽지 않는다(시험 A: 홈은 정적 파일 3개만).
  - `web_app_reuse_node_test.js`: 재사용 60개, `LOAD_ORDER` = 옛 60 + P1 6 + 화면 논리 2(`screen-search-live.js`·`screen-qgv-live.js`, web_app 파일, P1 뒤; P2-2a), `screen-search.js` ≤ 5 KB, 논리 파일도 불러올 때 층을 건드리지 않고 `IS2.searchLive`만 둠, `home-quotes.js` 부작용 없음, `IS2.selection`. `web_app_prices_node_test.js`: 최근 검색(옛 키·모양, 클릭에서만 쓰기, 한 클릭 한 action).
- 도우미: `web_app_reuse.js`(옛 모듈 경로 한 곳), `web_app_test_site.js`(빌드·서빙·fixture·`watch`·`storage`·`leaks`·`assertRamOnly`).
- P2-2a(메뉴 1 QGV · 1.1 리더보드)가 더하고 바꾼 시험:
  - 새 `web_app_qgv_browser_test.js`(1440·390): 준비 전 뼈대(구역 1-1~1-4, 블록 7개, 버튼 모두 꺼짐, 숫자 없는 대기 글, 자료 요청 없음, 떠났다 돌아온 렌더의 블록이 그 자리에서 채워짐), 층과 같은 값(순위·QGV·Q·G·V·SIC·유형·자료 기준일, V 머리 = `pg.v_source.ko`, 순위 머리 = `rankLabel(pg)`, nvda·amd = 기업 카드, `page()` 같은 객체), 범위·목록 칩(수는 층 행의 `listOf`), Universe 밖 상자·범위, 종합 순위 빈 상태와 QG 참고 버튼, 정렬(모든 선택지가 층 행 위의 이식 규칙과 같고 순위 글자 불변, NA 맨 뒤, QGV 층 구분, 머리 단추 = 선택, `aria-sort`, 한 방향 정렬은 방향 단추 꺼짐, 기본 정렬 복귀, 시총은 Universe 읽기 전 꺼짐), 모집단 상자, 필터(줄만 숨김, 분류 자료 없음, nvda는 TARGET 분류, 유형 선택지 = type_config 이름, 모두 풀기, 휴대폰 패널), 수익률(읽기 전 문구, 결정 대기 칩, 불러오기 단추의 이유 PRICE_TABS_OFF·AUTH_REQUIRED·SHEET_NOT_CONNECTED), 합성 클릭(요청·저장 없음, 코드 글자 없음), 실제 클릭 ①→②→③(③은 Enter 한 번 = 읽기 한 번, M3는 `[data-ram-price]` 글자만, `assertRamOnly`, `leaks()` 없음, 클릭이 쓴 키만 저장), 2.1.6 배지(`provenanceAttrs`)와 저장한 가중치의 미리보기, 2.1.7(`qgv.model`), 다시 온 사용자의 가격 탭으로 수익률(`ReportBenchmarks.priceIndex`와 같음, '분할 미확인', 수익률 순 정렬은 순위 불변), 새로고침 뒤 NA, 실패(404·잘못된 파일·논리 파일 404·계산 중 떠남), 경계(같은 출처, FILES만, 열 때 CORE + 카탈로그 + 이름표만, 클릭 없는 저장 0, blocked 0, 콘솔 오류 0, CSP 0, `[style]` 0, 390 넘침 없음, 누름 대상 44 px, 선택 기업 불변, 보드 예시 값·보이는 사유 코드 없음).
    - 보드의 '바깥 TARGET인데 Q·G 종합만 있는 행' 사례는 브라우저 fixture로 만들 수 없다: 엄격한 sec-qgv2.json 검증기가 504코드를 모두 요구하고 SEC 밖 TARGET(CIK 없음)에는 자료를 주지 않으므로, 자료가 있는 TARGET은 늘 Universe 코드의 행이다. 그래서 노드 시험(`web_app_qgv_screen_node_test.js`)이 `QgvScores.compute`의 공식 분할로 그 행을 만들어 `exploreGroup` QG_REFERENCE·참고 순서 없음·`listOf` null을 확인한다.
  - 새 `web_app_qgv_screen_node_test.js`: `screen-qgv-live.js`를 vm에서 불러 이식 함수가 옛 `LeaderboardScreen.sortRows`(qgv·q·g·v·asof·cap 양방향, cap은 READY M3 색인 대역)·`DeviceWatchlist.filter`(ticker·favorites)·`sicOf`·`populationOf`·`classificationOf` 업종·`filterClassifications`와 같은지(리더 출력에 STALE·WITHDRAWN·계산 버전 불일치·단면 밖·SIC '0000'·업종군 null 편집, 각 가지 도달 먼저 확인), `name`은 자기 규칙(보이는 제목, `localeCompare 'ko'`, 동점 티커), 방향 단추는 한 방향 정렬에 null. 결과는 `tools/fixtures/web_app_qgv_screen_expected.json`(옛 함수로 `--write`)과도 비교한다. P3가 옛 파일을 지우면 실시간 비교만 뺀다.
  - `web_app_qgv_node_test.js`: `model(page)`(순위 없으면 null, 가격으로 순위가 생기면 `officialModel` 투영과 같음, 가격 같은 키 없음, `PAGE_NOT_READY`, 얼림), 새 사유 글(한국어·영어, V 출처 낱말 없음).
  - `web_app_prices_node_test.js`: `periodReturns`(async, 탭 전 NOT_LOADED·요청 없음, PERIOD_PENDING, ReportBenchmarks와 같은 값, 종목 기호 규칙, 식별 정지가 먼저, SPY 없음·짧은 달력, 얼림, 저장 쓰기 없음, PriceStore 꺼짐이면 탭 없음).
  - `web_app_reuse_node_test.js`: `LIVE`에 `screen-qgv-live.js`, `SKELETON_MAX_BYTES`에 `screen-qgv.js` 5 KB, 불러올 때 `IS2.qgvLive` = `['leaderboard','helpers']`만, 소스 규칙 'the price view / store facade outside the layer'(`priceView`·`storeFacade`, 허용 prices.js·qgv.js·engines.js; 지금까지 `storeFacade`를 막는 규칙이 없었다).
  - `web_app_data_layer_browser_test.js` A: `#/qgv`를 열 때 읽는 파일은 `IS2.data.CORE` + `actual-catalog.json` + `company-names-ko.json`만. 경로마다 그 화면이 시작한 읽기가 끝난 뒤(`#/qgv`는 리더보드 표가 그려진 뒤, 그리고 네트워크가 쉰 뒤) 다음 경로로 넘어간다: 늦게 끝난 읽기가 다음 경로의 몫으로 잡히던 경합(`#/technical`에 `actual-catalog.json`, 설정 세부에 CORE 파일)을 막는다.
  - 측정(P2-2a, 2026-10-26, 같은 조건 3번 중앙값): 첫 화면 929 ms·첫 전송 30.4 KB·`IS2.ready` 7,598 ms·그때까지 930.5 KB(P2-1 기록 976 ms·27.7 KB·7,432 ms·906.8 KB, 다른 날 다른 실행). 첫 그림 파일 증가는 `screen-qgv.js` 뼈대(326 B → 3,952 B, gzip 245 B → 1,993 B)와 `app.css` 리더보드 규칙(12,479 B → 16,331 B, gzip 3,542 B → 4,449 B), 합쳐 gzip +2.7 KB. 논리 `screen-qgv-live.js`는 첫 그림 뒤에 온다.
- CI 목록 등록은 Main이 한다(P2-2a는 Main을 대신해 `web_app_qgv_browser_test.js`·`web_app_qgv_screen_node_test.js`를 등록했다).
