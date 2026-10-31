# 새 앱 공통 기반 (2026-10-31)

가지 `claude/web-app-common-base` (PR #435 가지 ec5fc8ac 위). 묶음 1·2 화면이 기대는 세 계약과 공용 부품입니다. 화면은 만들지 않았습니다.

## 1. 세 계약

### IS2.companies — 기업 목록은 이것 하나 (`web_app/companies.js`)

- 범위: Universe504. `scope()` → `{id:'UNIVERSE504', label:'Universe504', as_of:null}` (universe-codes/1 파일에 날짜가 없어 `as_of`는 null, 추측하지 않음).
- 자료: 홈 검색이 이미 읽던 공개 파일 두 개 — `universe-codes.json`(IS2.data.universe), `company-names-ko.json` — 를 IS2.data로 페이지당 한 번 읽고 메모리에 둡니다. 새 공개 파일·새 요청 방식 없음. 홈이 여는 파일은 그대로 HOME_READS 세 개입니다(`actual-catalog.json`은 칩·기업 화면 색인이 TARGET 기업을 더할 때 읽음, 이전과 같음).
- 행(깊게 얼림, 코드 목록 순서): `{code, id, ticker, name_en, name_ko|null, status:'ACTIVE'|'WITHDRAWN', withdrawn_on, official:true}`. `id`는 코드에 연결된 TARGET company_id, 없으면 코드(`#/company/<id>`의 키).
- 상장 종료: `search-part-live.js`의 `LISTING_ENDED` 표(서버 표와 같음을 Python 시험이 확인)에서 `WITHDRAWN`. WBD는 목록·검색에 남고 화면은 "상장 종료 2026-10-06 · 점수 없음". 표가 없으면 목록을 만들지 않습니다(FAILED) — 상장 종료 기업을 정상으로 보이지 않기 위해.
- 함수: `ready()`(거부하지 않음, `{state:'OK'|'PARTIAL'|'FAILED', size, missing}`; 빠진 부분이 있으면 다음 호출에서 다시 읽음), `list()`, `get(코드 또는 id)`, `find(query, limit)`, `exact(query)`, `korean(query)`, `scope()`. 검색 규칙은 DC-23 그대로(티커·영문명, 한글명·별칭은 찾지 않음).
- 홈 검색(`search-part-live.js`)과 기업 화면 색인(`screen-search-live.js`)은 이 계약만 거칩니다 — 코드 경로 하나.
- 범위 확장(IEX 확장)은 이 계약으로만 들어옵니다: `official:false` 행과 별도 `scope()`. 범위가 바뀌어도 공식 점수·순위·TARGET은 바뀌지 않습니다(그것들은 이 목록을 읽지 않음).

### IS2.lab — lab-backtest-v1 판독기 (`web_app/lab.js`)

- `validate(json)` → `{ok:true, value}`(깊게 얼린 사본, 인자는 그대로) 또는 `{ok:false, code, path}`. 첫 오류에서 파일 전체를 거부합니다. 규칙과 코드는 파일 머리 주석에 전부 있습니다(브리프 §5 + Main 검토 #437 확인 규칙: 첫 점 = 시작 월 100/100, 마지막 점 = 끝 월(부분 월 허용), 월 오름차순·중복 없음, 수익률 지표가 있으면 2점 이상, 값 > 0, 허용 오차 excess 1e-6 · total 1e-4 · CAGR 0.002(실제 일수/365.25) · 낙폭 1e-4).
- `status(run)` 오너 문구: 결과 없음 "연구 결과가 아직 없습니다", REAL+NOT_VALIDATED 파일럿 "실데이터 파일럿 · 미검증", SYNTHETIC "합성 데이터 · 시험용", MIXED "실데이터와 합성 데이터 혼합 · 파일럿 · 미검증", 모집단 시점 미충족이면 끝에 "· 모집단 시점 정합성 미확인", PIT_VERIFIED "입력 시점 검증됨", REVIEWED "검토 완료", FORMAL은 "정식 실행".
- `nullText(run, 지표)` → "– · <null_reasons 문구>" (null을 0으로 보이지 않음).
- `source()` → 오늘은 `{state:'NONE', code:'LAB_NO_PUBLIC_RESULT', payload:null, private:'PRIVATE_NOT_READY', text:'연구 결과가 아직 없습니다', private_text:'비공개 기능 준비 중'}`. 요청 없음, IS2.data를 건드리지 않음, 공개 Lab 파일 없음.

### IS2.privateArea — 비공개 영역 상태 (`web_app/private.js`)

- `state()` → `'NOT_READY'`(나중에 `'LOGIN_REQUIRED'`, `'SIGNED_IN'`).
- `text(state, area)`: NOT_READY "비공개 기능 준비 중", LOGIN_REQUIRED "로그인 필요"(area `'lab'`이면 "비공개 연구 결과 · 로그인 필요"), SIGNED_IN "비공개 영역 연결됨"(나중용). 네트워크·저장·로그인 흉내 없음.

## 2. 파일

| 파일 | 내용 |
|---|---|
| `web_app/companies.js` · `private.js` · `lab.js` | 새 계약 세 개 |
| `web_app/loader.js` | LOAD_ORDER: engines.js 뒤, search-part-live.js 앞에 companies → private → lab. NAMESPACES·API 표에 세 이름공간(IS2.ready 전 facade) |
| `web_app/search-part-live.js` · `screen-search-live.js` | 홈 검색·기업 화면 색인을 IS2.companies로 |
| `web_app/parts.js` | `notReady(text, missing)` — "준비 중" 한 줄 |
| `web_app/app.css` | `.lab-status`(`.checked`), `.curve*`, `.tbl .num`, `.not-ready-why` (선·점선만, 새 색 없음) |
| `tools/lab_backtest_fixture.js` | 합성 값 fixture: 유효 2실행(REAL 파일럿·현금 기준·sharpe null, SYNTHETIC), 빈 결과, MIXED, PIT 미충족, 규칙별 무효 변형 |
| `tools/web_app_common_base_node_test.js` | 세 계약 시험 (ci_node_tests.txt 등록) |
| `tools/web_app_reuse_node_test.js` · `web_app_search_part_node_test.js` | LOAD_ORDER·facade 기대값에 새 이름공간, 검색 시험은 companies.js를 먼저 올림(기존 단언 그대로) |

`build_web_app.py`는 LOAD_ORDER를 loader.js에서 읽으므로 바꿀 것이 없습니다(같은 NAME 줄 유지).

## 3. 나중 묶음이 부르는 것

- 기술적 분석·뉴스: `await IS2.companies.ready()` 뒤 `find(q, 8)` · `get(code)` · `list()`. `WITHDRAWN` 행은 "상장 종료 <withdrawn_on>".
- Lab: `IS2.lab.source()` → NONE이면 `text` + `private_text`; 파일이 생기면 `validate()` 결과만 그리고, 실행마다 `status(run)`, null 지표는 `nullText()`.
- 비공개 기능(KIS, Lab 곡선): `IS2.parts.notReady(IS2.privateArea.text())`.
- IS2.ready 전에는 facade: `ready()`·`source()`는 기다리고, 나머지는 `IS2.NOT_READY`를 돌려줍니다.

## 4. 하지 않은 것

- Lab·기술적 분석·뉴스 화면(묶음 2), 공개 Lab 결과 파일, 비공개 경로·로그인(오너 승인 뒤 별도 PR).
- `LISTING_ENDED` 표를 companies.js로 옮기기: `implementation/tests/test_web_app_search_part.py`가 search-part-live.js의 표를 고정하므로 그대로 두고 companies.js가 그 표를 씁니다.
- IEX 확장 행(`official:false`), P1_DATA_LAYER.md 갱신.

페이지가 읽는 파일 크기 변화: +26,434 바이트(gzip -9 기준 +11,050), 그중 첫 화면 파일(loader.js·parts.js·app.css) +2,635 바이트(gzip +980). 첫 화면 시험 중앙값 first_kb=33.4 (목표 100 이하).

## 비공개 칸 하나의 모양 (공개 + 비공개 2층 구조, 오너 10/31)

- 모든 화면은 비공개 추가분을 `IS2.parts.privatePanel({id, title, area})` 하나로 붙인다. 공개 부분은 그 칸을 기다리지도 읽지도 않는다.
- 상태와 문구는 `IS2.privateArea.PANEL_STATES`·`panelText`가 정한다.
  - `NOT_READY`: 비공개 기능 준비 중. 지금은 모든 칸이 이 상태로 시작한다.
  - `LOGIN_REQUIRED`: 로그인 필요(Lab: 비공개 연구 결과 · 로그인 필요).
  - `LOADING`: 비공개 자료 불러오는 중.
  - `ERROR`: 비공개 자료를 불러오지 못했습니다 · 고정 코드.
  - `EMPTY`: 비공개 자료가 아직 없습니다.
  - `READY`: 화면이 자기 내용을 그린다.
- 칸은 "비공개" 표시, `role=status` 한 줄, 오류·빈 상태의 캐릭터를 같은 모양으로 보인다. 요청·저장·스타일 속성은 없다(`web_app_private_panel_browser_test.js`).
- 화면별 공개/비공개 추가분 표: `docs/SPEC/FUNCTION_STATUS.md` "공개 + 비공개 2층 구조"(비공개 추가분은 오너 승인 뒤 확정).

- 10/31 보완: 로더가 준비되기 전(또는 실패 뒤) `privateArea`는 외관이라 상태 대신 객체를 준다. 그때 칸은 "비공개 기능 준비 중"을 보이고 객체를 글자로 찍지 않는다. 모르는 상태는 준비 전에도 거부한다(`PRIVATE_PANEL_STATE_UNKNOWN`). 브라우저 시험에 외관 상황을 더했다.
