# TARGET v0 결합 해소 — 목록과 변경 (2026-10-23)

## 결정 (원문)

> [결정 · 2026-10-23 · TARGET v0 결합 해소] TARGET v0(19종목)은 QGV와 무관하게 고른 비교 기준이다(10/13 결정). 화면·시세·차트·관심 기업의 기준 목록으로 쓰지 않는다.
> 1. 관심 기업·즐겨찾기·차트·메모의 종목 범위를 TARGET 19 id에서 분리한다. 키는 IA-7 결정(관심·메모 = Issuer, 차트 그림 = Listing)을 따른다.
> 2. 기기 시세·차트 범위(TA G2)는 다음 합집합으로 한다: 실제 보유(ACTUAL) + 사용자 관심 기업 + TARGET v1 후보(초안 포함). V 계산용 504 가격은 앞서 보낸 기기 가격 지시대로 별도 처리.
> 3. TARGET v0은 가상매매 세트 A와 v0 비교 화면에서만 쓴다. 기존 v0 데이터·기록은 삭제하지 않는다.
> 4. 'TARGET 19'를 기준으로 남아 있는 다른 곳(코드·문구·시험)을 찾아 목록으로 보고하고, 위 원칙에 맞게 바꾼다.

## 근거로 쓴 기존 결정

- **IA-7** (`implementation/docs/PRODUCT_IA_ONTOLOGY_CHECK_20261018.md:397`): "관심·메모·뉴스 = Issuer(`sec:` + CIK10). 차트 그림 = Listing(Universe 코드). `company_id`는 TARGET 별칭." 관계망 그래프 키도 Issuer다.
- **TA G2** (`implementation/docs/technical/TA_PREP_STATUS_20261017.md:204`, `USER_DECISIONS_PENDING.md:46`): "관심·보유 종목 확장 경로 미정 … 19종목 신원 카탈로그에 묶여 있다." 미결 상태의 기본값은 "기존 19종목 범위"였다. 이 결정으로 닫는다.
- 격차 3 (`PRODUCT_IA_ONTOLOGY_CHECK_20261018.md:41`, `:215`): `watchlist.js`가 TARGET 19 id만 받는다.

## 새 규칙 (구현)

| 대상 | 키 | 범위 |
|---|---|---|
| 관심 기업 · ★ · 그룹 | Issuer `sec:`+CIK10. CIK가 없는 TARGET 발행인 2곳(hanmi, tokyo_electron)은 TARGET 별칭을 그대로 Issuer 키로 쓴다 | 아무 기업(TARGET 별칭, Universe504 코드). Issuer 키를 못 정하면 ★를 끈다(추정 없음) |
| 차트 그림(노트·선·구간·시나리오) | Listing `EXCHANGE:SYMBOL` (Universe 코드. 한국·일본은 `KRX:042700`, `TSE:8035`) | 차트를 연 상장 |
| 기기 시세·차트 범위(TA G2) | 기업 페이지 id(TARGET 별칭 또는 Universe 코드) → Worker 기호 | ACTUAL 보유 ∪ 관심 기업(발행인의 모든 상장) ∪ TARGET v1 후보(초안 후보표 + 확정 버전). Worker 허용 목록 밖은 요청하지 않음 |
| 가격 요청 | — | 누를 때만. 앱 열기 자동 경로(`PriceStore.autoSync`)에는 새 기호를 더하지 않는다 |
| TARGET v0 | `company_id` 별칭 | 가상매매 세트 A, v0 비교 화면(Forward validation, S06 TARGET 목록), 기존 기록 |

Universe 코드의 CIK는 검토된 `company-names-ko.json`의 `cik` 칸에서 읽는다. TARGET 행은 코드 안의 TARGET CIK(=`SecQgv2.TARGET_CIKS`)와 상장이 같을 때만 쓰고, 다르면 그 행을 쓰지 않는다. Universe504 504개 코드 모두 CIK가 있다(시험으로 고정).

## 이전 기록 이전(migration)

- `investment.web.v1.personal`(관심·그룹): 읽을 때 옛 키(TARGET `company_id`, Universe 코드)를 Issuer 키로 바꿔 쓴다(`DeviceWatchlist.migrate`, 순서 유지·중복 제거·모르는 키 보존). 읽기만으로는 쓰지 않는다. 첫 쓰기 직전에 원본 문자열을 `investment.web.v1.personal-v0`에 한 번만 복사하고 다시 덮어쓰지 않는다. 가져오기(옛 형식 파일)도 같은 변환을 거친다. 백업 스키마(version 1, 문자열 배열)는 그대로다.
- `investment.web.v1.chart-user-objects`(차트 그림): 새 객체의 `symbol`은 Listing(`NYSE:SYK`)이다. 옛 객체(`SYK`, `042700.KS`)는 그 상장을 열 때 그대로 함께 읽고 고치거나 지우지 않는다.
- v0 데이터(`actual-catalog.json`, `sec-valuation-inputs.json`, 가상매매 장부, Forward validation 기록)는 손대지 않았다.

## 목록 (기준 커밋 5147e3b7의 위치)

판정: **바꿈** = 이 브랜치에서 새 규칙으로 바꿈 · **유지(A)** = 가상매매 세트 A · **유지(v0)** = v0 비교 화면 · **유지(보존)** = v0 데이터·기록 보존 · **미결** = 결정 범위 밖이라 열린 결정으로 보고

### 관심 기업 · ★ · 그룹 · 메모

| 위치 | 지금 역할 | 판정 | 새 규칙 |
|---|---|---|---|
| `WA/watchlist.js:3-5` `IDS`, `identities()` 19행 검사 | 관심 목록의 유일한 기업 표 | 바꿈 / 유지(A·v0) | `identities()`는 v0 목록용으로 유지. 새 `issuerOf`·`listingOf`·`providerSymbol`·`migrate`·`directory`·`watchRows`·`filter`(Issuer 기준) |
| `WA/app.js:353` `star(id)` | `prefs.interests.includes(company_id)` | 바꿈 | Issuer 키로 판정·저장. Issuer 미정이면 비활성 ★ |
| `WA/app.js:1109-1122` ★ 클릭 | `company(id)`(TARGET 행)만 허용 | 바꿈 | `toggleInterest` — 아무 기업. 같은 발행인의 모든 ★ 갱신 |
| `WA/app.js:1257-1272` 관계망 브리지 | `company_id`↔`issuer_id`(Pages에서는 비어 있음) | 바꿈 | Issuer 키 그대로 주고받음 |
| `WA/app.js:399`, `:418` 그룹 체크박스 | 멤버 = `company_id` | 바꿈 | 멤버 = Issuer 키 |
| `WA/app.js:335-347` `load()`·`save()` | 그대로 읽고 씀 | 바꿈 | 읽을 때 migrate, 첫 쓰기 전 v0 원본 보존 |
| `WA/app.js:413`, `:628` 관심 기업 화면 | TARGET 19행에서 ★만 거름 | 바꿈 | 관심 발행인 행(아무 기업) |
| `WA/app.js:624` 기업 목록(`#companies`) | TARGET 19행 | 바꿈 | TARGET 별칭 + Universe504 전체(`DeviceWatchlist.directory`) |
| `WA/app.js:400`, `:409`, `:743`, `:962`, `:963`, `:1063`, `:1321`, `:1326` | 관심 목록을 `company_id`로 넘김(이번 주 실적, 뉴스 등급·필터, 비공개 순위 명단, 플레이북, 홈 개인 소식, 13F) | 바꿈 | `pageIds`(발행인당 1개 페이지 id) 또는 `allIds`(발행인의 모든 id) |
| `WA/news-signals.js:167` `readInterests` | 저장된 `company_id` 그대로 | 바꿈 | Issuer 키를 모든 id로 펼침, 개수는 발행인 수 |
| `WA/universe-company.js:149-157` | Universe504 페이지에 ★ 없음 | 바꿈 | 제목 옆 ★(`ctx.starHtml`) |
| `WA/playbook-screen.js:5,18` 플레이북 기록 `symbol`·`memo` | 티커 키(TARGET 제한 없음) | 미결 | 기업 메모를 Issuer로 다시 키울지(IA-7 "메모 = Issuer")는 플레이북 기록 스키마 변경이라 별도 결정 |
| `WA/device-backup.js:16-19` | 관심 문자열 배열 검증 | 유지 | 형식 같음(문자열). 바꿀 것 없음 |

### 차트 그림 · 기기 시세 · 차트 범위 (TA G2)

| 위치 | 지금 역할 | 판정 | 새 규칙 |
|---|---|---|---|
| `WA/private-history.js:9,14` `TARGETS`, `symbolFor` | 가격 이력 = TARGET 19만 | 바꿈 / 유지(v0) | `symbolFor`는 v0 별칭표로 남김(Forward validation이 씀). 차트는 `setScope`로 받은 범위 + Worker 허용 목록(`chartSymbol`) |
| `WA/private-history.js:24` 응답 검증 | 기호가 TARGET 19 중 하나 | 바꿈 | 요청한 기호와 같고 형식이 맞을 것(허용 목록은 요청 전에 검사) |
| `WA/private-history.js:92` 설정 링크 | TARGET 19 링크 | 바꿈 | 기기 범위 링크, 비면 ☆ 안내 |
| `WA/private-history.js:217-230` `mountTechnical` | 선택지 = TARGET 19, 기본 `asml`, "가격 이력 지원 19종목" 문구 | 바꿈 | 선택지 = 기기 범위, 기본 = 범위 첫 기업, 범위 밖 문구(☆ 안내) |
| `WA/universe-company.js:131`, `:189` | 일봉 차트 = TARGET 발행인만, "TARGET 19개 … TA G2 결정 전" | 바꿈 | 범위 안이면 아무 코드나 차트, 밖이면 ☆ 안내 |
| `WA/chart-workbench.js:195`, `:662`, `:1026` 그림 키 | `symbol` = 공급자 티커 | 바꿈 | Listing 키로 쓰고 옛 티커 키도 읽음 |
| `WA/app.js:18` `priceStoreCore` | 러너 기호 + TARGET ★만 | 바꿈 | 누를 때: + 기기 범위 전체. 자동(앱 열기): 이전과 같은 집합 |
| `WA/price-store.js:354` `starred` | ★ 중 TARGET만 | 유지 | 이 브랜치는 price-store 내부를 건드리지 않음(claude/price-click-only와 충돌 회피). 범위 확장은 app.js에서 더함 |
| `WA/tradingview-widgets.js:10-19` 시세 띠 | "TARGET 19 시세 띠" | 바꿈 | 기기 범위 시세 띠, 비면 위젯 없음. Universe 코드도 TradingView 기호 |
| `WA/google-sheet-quotes.js:11` `HISTORY_SYMBOLS` / `worker/src/index.js:7-58` | Worker 허용 목록 = Universe504 + ASML·042700.KS·8035.T + ETF 17 + FX 2 | 유지(확인) | 504 코드와 TARGET 19 모두 들어 있음을 시험으로 고정. 넓히지 않음 |
| `WA/price-store.js:412` Worker 범위 문구 "Universe504 · TARGET 19 · ETF 17 · 환율" | 허용 목록 설명 | 유지 | 허용 목록 사실 설명(기준 목록 아님) |
| `WA/device-actual.js:77` ACTUAL 카탈로그(19행), 수동 시세·시트 시세(`google-sheet-quotes.js`, `google-sheet-setup.js:6,17`) | ACTUAL 보유 입력·시세 = 카탈로그 19행 | 미결 | ACTUAL 보유 자체가 v0 카탈로그에 묶여 있다. 보유를 카탈로그 밖으로 넓히는 것은 보유 스키마·백업·시트 형식 변경이라 별도 결정 |

### TARGET v0 유지 (세트 A · v0 비교 · 보존)

| 위치 | 역할 | 판정 |
|---|---|---|
| `WA/virtual-trading-runner.js:13-20`, `:82` `TARGETS`·`requiredSymbols` | 세트 A(v1.1 예시 = TARGET v0) 가격 | 유지(A) |
| `WA/virtual-ledger-sheets.js:513-519`, `WA/virtual-trading.js:351` 세트 B–D 구성 = TARGET 19 + ETF | 가상매매 세트 구성 후보 | 미결 — 세트 B–D가 아직 TARGET 19 + ETF에서만 고름. Worker는 504를 허용하지만 러너·장부 형식 변경이 필요 |
| `WA/forward-validation.js:243` "Worker는 TARGET 19종목만 제공" | v0 비교 화면 | 유지(v0), 문구만 사실대로 고침(SPY는 허용 목록에 있음) |
| `WA/app.js:736` S06 TARGET 목록(D12), `WA/leaderboard-screen.js:250` | v0 비교 목록·필터 | 유지(v0) |
| `WA/private-subset-view.js:4,6,77` 비공개 순위 명단 TARGET ∪ ★ ∪ Universe | 기기 순위 명단 | 유지(문구 "TARGET v0"로), ★는 페이지 id로. 명단에서 v0를 뺄지는 미결 |
| `WA/device-valuation.js:8` `IDS`(19), `sec-valuation-inputs.json` | TARGET V 입력 | 유지(보존). 504 V 가격은 별도 지시 |
| `WA/sec-qgv2.js:20` `TARGET_CIKS`, `WA/qgv-scores.js:345` | TARGET 행 점수·중복 제거 | 유지(보존) |
| `WA/target-v1-screen.js:83`, `target_v1_builder_v0.json:209` "기존 19종목은 …" | v1 채점 가격 경로 설명 | 유지 — claude/v-factor-count 담당 파일 |
| `S/universe/company_names_ko.py:47`, `S/product/public_classification.py:39`, `S/qgv/virtual_trading_inputs.py:36`, `S/qgv/html_sample.py:67`, `S/product/render_app.py:121` | v0 신원·세트 A 입력·옛 표본 문구 | 유지(보존) |

### 시험

| 위치 | 지금 단정 | 판정 | 새 단정 |
|---|---|---|---|
| `tools/watchlist_node_test.js` | 19행 투영·필터 | 바꿈(추가) | Issuer/Listing 키, 504 코드 전부 CIK, 옛 기록 이전(멱등·원본 불변·모르는 키 보존), Worker 허용 목록이 504 + TARGET 포함 |
| `tools/watchlist_browser_test.js` | ★ = TARGET 19, `company_id` 저장 | 바꿈 | Issuer 키 저장, Universe504 ★, 관심 화면 = 관심 기업, 기업 목록에 504, 옛 기록 읽기·v0 원본 보존 |
| `tools/private_history_node_test.js:17` "TARGET19 identities" | 범위 = 19 | 바꿈 | `symbolFor` = v0 별칭, 범위 = `setScope`(없으면 비어 있음) + 허용 목록 |
| `tools/private_history_browser_test.js:250,400,421,445` | 설정 링크 19, 선택지 19, "지원 19종목", 기본 `asml` | 바꿈 | 기기 범위(관심 3곳), v0 기업 미제공, 범위 밖 문구, 기본 = 범위 첫 기업 |
| `tools/pages_cockpit_browser_test.js:129`, `manual_quotes_browser_test.js:167-169`, `google_sheet_quotes_browser_test.js:109`, `virtual_ledger_sheets_browser_test.js:365`, `tests/test_pages_cockpit_build.py:41` | ACTUAL 카탈로그·시세 19행, 세트 A 19종목 | 유지 | ACTUAL 카탈로그·세트 A 시험 |
| `tools/universe_leaderboard_*`, `qgv_v2_screens_browser_test.js` | D12 공식 리더보드 = Universe | 유지 | — |

### 문서

| 위치 | 판정 |
|---|---|
| `docs/USER_DECISIONS_PENDING.md:46` TA-G2 "기존 19종목 범위" | 바꿈 — G2는 이 결정으로 닫힘 표시 |
| `docs/technical/TA_PREP_STATUS_20261017.md:204` G2 | 바꿈 — 닫힘 한 줄 추가 |
| `docs/PRODUCT_IA_ONTOLOGY_CHECK_20261018.md:41,215` 격차 3, Watchlist 행 | 기록 문서(시점 고정) — 이 문서가 후속 |

## 열린 결정

1. **ACTUAL 보유의 범위.** 보유 입력·시세는 `actual-catalog.json`(TARGET v0 19행)에 묶여 있다. 결정 2의 "ACTUAL"은 지금 그 19행 중 보유분이다. 카탈로그 밖 보유를 받으려면 보유 스키마·백업·시트 형식을 바꿔야 한다.
2. **가상매매 세트 B–D 구성 후보**가 TARGET 19 + ETF다(`virtual-trading-runner.js` `MEMBERS`). 결정 3에 따르면 v0은 세트 A에만 쓴다. 504로 넓히려면 러너·장부 변경이 필요하다.
3. **CIK 없는 발행인의 Issuer 키.** hanmi·tokyo_electron은 TARGET 별칭을 Issuer 키로 쓴다. 별도 이름공간(예: DART 고유번호)을 둘지.
4. **Universe 코드의 CIK 출처.** `company-names-ko.json`의 `cik` 칸(SEC 대조값)을 쓴다. KR-NAMES 결정은 이 표를 "표시·검색 전용"이라 했다. 표의 이름은 쓰지 않고 식별자 칸만 쓰지만, 공식 출처를 `sec-qgv2.json` 행의 `cik`로 바꿀지 확인이 필요하다.
5. **플레이북 기업 메모**(`playbook-screen.js`, 티커 키)를 Issuer 키로 옮길지.
6. **비공개 순위 명단**(`private-subset-view.js`)에 TARGET v0를 계속 넣을지.
7. **S06 TARGET 목록·필터**(D12)는 v0 비교 목록으로 남겼다. 이 결정과 함께 없앨지.
