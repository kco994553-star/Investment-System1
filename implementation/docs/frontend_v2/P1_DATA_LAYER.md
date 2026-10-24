# 프론트 v2 P1 자료·계산 층: P2 레인용 API 계약

P2 화면 레인이 쓰는 함수와 기록 모양을 정한다. 근거는 P1 구현 사양(Main 결정 2026-10-24)이다. 이 문서는 P1 단계마다 늘어난다. 지금은 2단계(`action`, `data`, `qgv`)까지 적었고, `prices`·`store`·`engines`는 3·4단계에서 채운다.

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
  - Universe 읽기와 가격 탭은 prices 층에서 온다. 가격 층이 들어오기 전에는 둘 다 없다.
  - 저장 시세는 이미 있는 IndexedDB에서만 읽는다.
- `rows(page, {scope:'ALL'|'UNIVERSE'|'TARGET'})`: QgvScores 순서 그대로 돌려준다. 정렬·모집단·분류 필터·레이더는 P2-2에서 옛 함수(LeaderboardScreen, StatRadar의 `compute(spec,{result})`)로 붙인다.
- `row(page, idOrCode)`: Universe 안의 TARGET은 그 코드의 행이다.
- `coverage(page)`: 수만 돌려준다. `preview(page, weights)`, `setProfile({preset, gate})`, `profile()`, `reasonText(code, en)`, `constants()`, `subscribe(fn, {signal})`, `vSource()`, `V_SOURCES`도 있다.
- `forEngines(page)`: `engines.js` 전용이다(소스 검사로 막는다).

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

## 5. V 출처 전환점(중앙 V가 게시될 때 바꿀 곳, 전부)

1. `qgv.js`: `OFFICIAL_READER`(유일한 스위치)를 설정하고 `centralPage`를 구현한다. 중앙 V일 때는 Q·G도 게시본에서 읽고, sec-qgv2.json과 섞지 않는다.
2. `data.js`: `FILES`에 게시 파일을 넣고 엄격 리더를 붙인다.
3. Pages 가드 허용 목록에 넣는다(Main).
4. `TargetV1Builder.finalize`가 `v_source`를 `DEVICE_TEMPORARY`로 직접 박는다(#391). 옵션을 추가해야 한다(Main이 #391에 요청).
5. 엔진의 중앙 모드 계약: `forEngines`는 늘 기기 결과를 준다. 그래서 엔진 기록은 `engine_v_source`(지금은 DEVICE_TEMPORARY)를 남긴다. 중앙 행을 computed 모양으로 바꾸는 어댑터를 둘지는 그때 정한다.
6. `OFFICIAL_CENTRAL` 문구는 초안이다. 전환할 때 사용자 확인을 받는다.

## 6. 사용자 결정 대기 항목

- V 기록(D-21)을 클릭할 때만 남길지
- 플레이북 판정 기록: 옛 앱은 판정할 때 기록했고, 새 앱은 `record(event)`를 누를 때만 기록한다
- IndexedDB 'market'에 시세를 계속 저장할지(계획 §2.1과 충돌)
- 일일 보고서·보고서 모델(P2-6)
- 로그인 두 번 누르기(준비 → 로그인)
- 중앙 V 모드의 엔진 계약
- 백업 /5(user_objects)는 고정 코드로 거절한다
- 임시 V 기준 순위 문구
