# 품질 점검 1차 — 기업 검색 → QGV 리더보드 → 기업 화면 (오픈소스 도구)

작성 2026-11-05 · Main. 가지 `claude/quality-a11y-perf`(기준 ab6a83c3).

- 범위: 새 프론트엔드의 첫 흐름 하나. `#/`(0. 기업 검색) → `#/qgv`(1.1 리더보드) → `#/company/<id>`(검색 결과 = 기업 화면).
- 자료: 기존 합성 fixture만 썼다(`qgv_v2_fixture.js` strictPayload·missingPayload, `company_classification_v0_payloads.json` live, `qgv_official_vectors_v1.json` base_text, `qgv_v2_custom_vectors_v1.json`). 실자료는 읽지 않았다.
- 상태 표시: 결과는 모두 **TESTED**(로컬 합성 자료)다. CI 등록은 목록 한 줄이며 워크플로는 바꾸지 않았다. 배포·실기기 확인은 하지 않았다.
- 이 문서는 병합·배포·워크플로 변경 승인이 아니다.

## 1. 요약

| 항목 | 결과 |
| --- | --- |
| 새 시험 | `implementation/tools/web_app_flow_quality_browser_test.js` — 1440 · 390 · 200% 확대(720z), 상태 9종, axe 45회 검사, 키보드 흐름. 약 50초(axe 있음) / 약 30초(axe 없음) |
| axe-core 4.14.0 (wcag2a·wcag2aa·wcag21aa) | 위반 2건(같은 규칙 1개: `aria-required-children`, 검색 결과 없음 목록). 기존 결함으로 기준선에 넣었다 |
| 키보드·초점·확대·상태 | 확인된 결함 5건을 고쳤다(5절). 고친 뒤 모두 통과 |
| Lighthouse 13.5.0 | 접근성 98~100, 권장 사항 96~100, 성능 모바일 35~90 · 데스크톱 54~77(합격 기준 아님, 6절) |
| Impeccable 4.7.0 (엔진 0.1.16) | 오프라인 `detect`만 실행. 경고 9 · 권고 1. 시각 양식과 맞서는 제안은 받지 않았다(7절) |
| 기존 시험 | 바꾼 파일과 관련된 web_app 시험 통과(home·qgv·tech_filter·first_paint·shell·news·technical·macro·prompts·tree·lab·private_panel, 노드 reuse·qgv·qgv_screen·common_base·search_part, pytest 경계·매니페스트). 기존 단언은 하나도 바꾸지 않았다. `web_app_data_layer_browser_test.js`는 이 샌드박스에서 **바꾸기 전 ab6a83c3에서도 똑같이** 실패한다(`READS_NOT_ANSWERED fresh #/qgv`, `qgv-official.json` 요청이 30초 열린 채) — 이번 변경과 무관, CI에서 확인 필요 |

## 2. 기존 검사 목록 (이번 작업 전)

| 종류 | 있는 것 | 이 흐름에 대해 |
| --- | --- | --- |
| CI 목록 | `tools/ci_browser_tests.txt`(브라우저 시험 102개), `tools/ci_node_tests.txt`(노드 시험 79개), 실행기 `tools/run_js_tests.sh`. 워크플로 `cockpit-pages.yml` build 작업이 playwright@1.58.2와 chromium을 설치하고 두 목록을 돌린다 | 새 시험은 목록 한 줄로 들어간다 |
| 화면 시험 | `web_app_home_browser_test.js`(검색 combobox, ★, 회사 카드), `web_app_qgv_browser_test.js`(리더보드 값·정렬·필터·미리보기·실패), `web_app_first_paint_browser_test.js`(폰 조건 첫 그림), `web_app_tech_filter_browser_test.js` 등 | 값·경계·상태는 이미 깊게 본다 |
| 접근성(손으로 쓴 검사) | Tab 도달·초점 고리·버튼 이름: macro·news·technical·prompts·tree·lab 화면 시험. 44px 누름 영역: home·qgv·tree·tech filter. combobox ARIA: home | **검색·리더보드·기업 화면에는 Tab 흐름·초점 고리 검사가 없었다.** news 시험은 검색 입력을 "상자가 보이므로" 예외로 셌다 |
| 규칙 검사기 | 없음(axe·Lighthouse·pa11y 없음) | 이번에 axe·Lighthouse를 시험 도입했다 |
| 성능 | `web_app_first_paint_browser_test.js`(390×844, 150ms, 1.6Mbps, CPU×4, 3회 중앙값, 첫 그림 2초·첫 KB 100 이하) | 첫 그림만 본다. 자료가 채워진 뒤의 LCP·CLS·TBT는 보지 않았다 |
| 경계·비밀 | `test_private_boundary_static.py`, `pages_artifact_guard.py`, `pages_freshness_guard.py`, `public_price_boundary.py`, `autonomy_gate_a_guard.py`, `spec_direction_guard.py`, 워크플로 `private-boundary-push.yml`(모든 push에 정적 경계 검사) | 이번 변경과 무관하게 유지 |
| web_app 규칙 | `web_app_reuse_node_test.js` RULES(fetch 위치, `\|\|0`·`??0` 금지, CSS 주석의 hex 모양 금지, script 요소 금지, 저장소는 P1 층만, style 속성 금지) | 이번 변경도 통과 |
| 의존성 | playwright@1.58.2·pytest==9.1.1 등은 버전 고정. npm audit·Dependabot·비밀 스캐너(gitleaks 등)는 없다 | 이번 범위 밖(기록만) |

## 3. 도구 — 버전·라이선스·설치·네트워크·보고서 위치

모두 작업 트리 밖 임시 폴더(`$P/tools-*`, `$P` = 세션 scratchpad)에 설치했다. 저장소·web_app·Pages 빌드에는 아무것도 넣지 않았다.

| 도구 | 버전·라이선스 | 설치 | 실행 중 네트워크 | 보고서 |
| --- | --- | --- | --- | --- |
| axe-core | 4.14.0 (2026-10-05), MPL-2.0 | `npm i --ignore-scripts axe-core@4.14.0` → 패키지 1개, 설치 훅 없음 | 없음. `page.evaluate(소스)`로 DevTools 프로토콜에서 실행한다(페이지 CSP를 풀지 않음, script 요소를 넣지 않음). 시험은 CSP 위반 0을 함께 확인한다 | 시험 출력(콘솔)과 `AXE_WRITE_BASELINE=<scratch 파일>` |
| Lighthouse | 13.5.0 (2026-09-18), Apache-2.0 | `npm i --ignore-scripts lighthouse@13.5.0` → 114개 패키지, install·postinstall 훅 없음(전수 확인) | 로컬 서버(127.0.0.1)만. `--no-enable-error-reporting`, 업로드 옵션 없음, Chrome `--no-proxy-server`. Chrome = pw158의 chromium-1208(`CHROME_PATH`) | `$P/qa/lh/*.report.{json,html}` (저장소 밖) |
| Impeccable | npm `impeccable` 4.7.0(Apache-2.0, 2026-10-19) + 엔진 `@impeccable/cli-linux-x64` 0.1.16(LICENSE = Apache-2.0 본문) | `npm pack`으로 받아 풀고 읽기만 했다(설치 안 함). npm 셸은 엔진이 없으면 GitHub 릴리스에서 내려받는다(sha256 확인). 엔진 문자열에 `api.openai.com`, `impeccable.style/api/roll`(익명 사용 통계), live 모드·`install`(하네스에 skill·hook 설치)이 있다 | **`unshare -n`(네트워크 없는 이름공간)**에서 엔진을 직접 실행. `HOME`을 scratch로 돌리고 `telemetry off` 먼저. `detect --json --no-config`만 썼다. live·install·init·document(PRODUCT.md/DESIGN.md 작성)는 쓰지 않았다 | `$P/qa/impeccable.json`. 입력은 렌더한 DOM 사본(scripts·CSP meta 제거)과 빌드한 app.css를 scratch에 둔 것 |
| Playwright | 1.58.2 + Chrome Headless Shell (CI와 같음) | 기존 `$P/pw158` | 테스트 서버(127.0.0.1)만 | — |

Impeccable이 무엇인가: 디자인 "skill pack"(AI 코딩 도구에 넣는 명령 24개)과 결정적 검출기 CLI(규칙 61개)를 묶은 것이다. skill(critique 등)은 에이전트 하네스에 설치해야 하고 저장소에 PRODUCT.md·DESIGN.md를 만들게 이끈다. 그래서 **검출기(`detect`)만 오프라인으로 썼고, 비평은 VISUAL_STYLE.md 기준으로 직접 했다**(7절).

## 4. 실행 명령

```sh
P=<세션 scratchpad>   # 도구 설치 위치
# 새 시험 (axe 포함)
AXE_CORE_PATH=$P/tools-axe/node_modules/axe-core/axe.min.js \
NODE_PATH=$P/pw158/node_modules PLAYWRIGHT_BROWSERS_PATH=$P/pw158/browsers \
node implementation/tools/web_app_flow_quality_browser_test.js
# axe 없이 (CI 현재 상태와 같음: 규칙 검사는 건너뛰고 그렇게 출력, 나머지 검사는 실행)
NODE_PATH=... PLAYWRIGHT_BROWSERS_PATH=... node implementation/tools/web_app_flow_quality_browser_test.js
# 관찰값을 기준선 형식으로 쓰기
AXE_WRITE_BASELINE=$P/qa/axe_observed.json ... node implementation/tools/web_app_flow_quality_browser_test.js
# Lighthouse (개발 사이트 = tools/web_app_test_site.js + 같은 합성 fixture, 127.0.0.1)
CHROME_PATH=$P/pw158/browsers/chromium-1208/chrome-linux64/chrome \
node $P/tools-lighthouse/node_modules/lighthouse/cli/index.js "<base>#/qgv" [--preset=desktop] \
  --only-categories=performance,accessibility,best-practices --output=json --output=html \
  --output-path=$P/qa/lh/qgv-mobile --no-enable-error-reporting \
  --chrome-flags="--headless=new --no-sandbox --no-proxy-server"
# Impeccable (네트워크 없음)
HOME=$P/tools-impeccable/home unshare -n $P/tools-impeccable/bin16/package/bin/impeccable telemetry off
HOME=$P/tools-impeccable/home unshare -n $P/tools-impeccable/bin16/package/bin/impeccable detect --json --no-config $P/qa/snap
```

## 5. 새 시험이 보는 것과 결함

### 5.1 검사

- **폭:** 1440×1000, 390×844, **200% 확대 = 1440의 절반인 720×500 CSS px + deviceScaleFactor 2**(브라우저 확대와 같은 CSS 폭이라 화면의 미디어 쿼리가 그대로 반응한다. CSS zoom은 쓰지 않았다).
- **키보드만으로 흐름:** Tab으로 검색창 → `nvda` 입력 → ArrowDown → Enter(기업 화면) → Tab으로 QGV 카드 링크 → Enter(리더보드) → Tab으로 첫 기업 링크 → Enter(그 기업 화면). 모든 정지점에 2px 이상 초점 고리(검색 입력은 상자 고리)가 있어야 하고, 폰 아래 탭 막대 밑에 숨으면 안 된다. 경로 이동 뒤 초점은 main.
  - Tab 횟수(고친 뒤): 1440 = 검색창 10 · QGV 카드 4 · 첫 기업 15, 390 = 2 · 4 · 11. 건너뛰기 링크는 없다(1440에서 검색창까지 메뉴 9개를 지난다. 기록만).
- **모든 화면·상태:** style 속성 0, CSP 위반 0(axe 실행 뒤에도), 가로 넘침 0, main이 비지 않음, aria-label이 보이는 낱말을 담음(WCAG 2.5.3), main의 h1 하나·제목 단계 건너뜀 없음, 바깥 요청 0, 저장 0, 처리 안 된 오류 0.
- **200%:** 위에 더해 화면 가장자리에서 잘린 조작 요소 0, 상자 안에서 글이 잘린 버튼·칩 0(가로 스크롤 상자 안은 허용).
- **상태(1440·390 모두):** 정상 · 읽는 중(`sec-qgv2.json`을 page.route로 붙잡음) · 빈 상태(게시본 없이 종합 순위, 검색 결과 없음, 없는 기업) · 미게시(점수 파일·게시본 404) · 읽기 실패(검증 실패 점수 파일) · STALE(기준일 뒤 뉴욕 정규장 3회 지난 시계) · 일부 누락(missingPayload: amd Q 50% 미만 NA, msft STALE, 게시본 없어 V 전부 NA) · 진짜 0 대 NA · 개인 미리보기(시험 전용 버튼의 실제 클릭으로 가중치 저장 뒤 미리보기).
- **진짜 0:** 게시본에서 NYSE:ABBV의 마지막 V 요인을 0으로 두고 축·종합·순위·coverage를 판독기 자신의 엔진으로 다시 만든 뒤 판독기 `validate()`를 통과한 합성 게시본. 리더보드 V 칸 `0.0`(NA 표시 없음) 대 NYSE:MO `NA…`(이유), 기업 화면 V 막대 `0.0` 실선 대 NA 점선.
- **구분:** 기업 머리 `Universe504`, QGV 카드 `V 출처: 공식 V` · `가격 기준일 2026-10-13` · `점수 갱신 … UTC`, 리더보드 `평가: Universe504 중 점수 행 n` · 기준 칩의 가격 기준일 · 2.1.6의 `공식 가중치 결과` / `내 설정 결과(미리보기)` / `공식 점수 아님` · 필터를 켜면 표 제목에 `필터 적용 중` · 미리보기 표 머리가 공식 순위가 아님.
- **axe:** 위 화면·상태마다(45회) wcag2a·wcag2aa·wcag21aa. `page|폭|규칙`별 개수를 `tools/fixtures/web_app_flow_axe_baseline.json`과 비교해 **늘어난 것만** 실패로 한다.

### 5.2 결함 — 찾음 / 고침 / 남김

| # | 결함 | 근거 | 처리 |
| --- | --- | --- | --- |
| D1 | 검색 입력에 초점 표시가 없다(`.search-box input{outline:none}`, 상자는 늘 같은 2px 테두리) — 키보드 사용자가 초점 위치를 못 본다 | 새 시험 1440·390 실패. WCAG 2.4.7 | **고침** `app.css`: `.search-box:has(input:focus-visible){outline:3px solid var(--ink);outline-offset:2px}` — 다른 조작 요소와 같은 고리. 모든 화면의 공용 검색창에 적용 |
| D2 | 폰(390)에서 Tab 초점이 고정 탭 막대 밑에 숨는다(리더보드 하위 메뉴 1.2·1.3·1.4 버튼) | 새 시험 390 실패. WCAG 2.4.11 | **고침** `app.css` 폰 구간: `html{scroll-padding-bottom:calc(var(--tabbar) + 12px)}` |
| D3 | 리더보드에서 필터를 켜도 표 제목은 `전체 · … · 표시 n개`뿐이다. 필터 칸(2.1.3)은 표 아래에 있어 표만 보면 걸러진 줄 모른다 | 오너 규칙(필터 상태 구분) | **고침** `screen-qgv-live.js`: 필터가 하나라도 켜지면 제목 끝에 ` · 필터 적용 중` |
| D4 | 정렬 방향 버튼: 보이는 글 `↓ 내림`(폰) / 이름 `내림차순`(aria-label) 불일치 | Lighthouse `label-content-name-mismatch`(qgv 모바일). WCAG 2.5.3. axe 태그 실행에서는 실험 규칙이라 꺼져 있어 새 시험에 직접 검사를 넣었다 | **고침** aria-label 제거, 화살표 `aria-hidden`. 이름 = 보이는 낱말(폰 `내림`, PC `내림차순`) |
| D5 | 기업 화면 제목 단계 h1 → h3 건너뜀(카드 제목) | Lighthouse `heading-order`(기업 화면 98점) | **고침** `parts.js` card() 제목 h3 → h2(이 부품은 기업 화면만 쓴다. 글꼴·크기는 `.card-title` 그대로라 겉모습 같음) |
| D6 | 검색 목록(listbox)이 "일치하는 기업이 없습니다"·한글 안내·"불러오는 중"일 때 option 없이 presentation 줄만 가진다 | axe `aria-required-children`(home@no-match, 1440·390 각 1) | **남김(기준선)**. 화면 읽기 프로그램에는 같은 말이 sr-only status로 이미 나간다. 고치려면 공용 검색 부품의 계약(메시지가 `#q-list` 안, 읽는 중에도 `aria-expanded=true`)을 바꿔야 하고 home·news·technical 시험의 단언이 그 계약을 고정한다 → 제안: 메시지 때는 목록을 닫고(`aria-expanded=false`) 메시지를 목록 밖 같은 자리에 보이기. 오너 결정 뒤 별도 PR |
| D7 | axe "needs review"(판정 보류) 131 노드(44 항목, 모두 color-contrast): 노란 형광 그라디언트 위 글(현재 메뉴·`.here`)과 기호만 있는 span | axe incomplete(color-contrast) | **손으로 확인, 결함 아님**: 잉크 #161616 대 노랑 #FFE45C 대비 약 15:1, 흰 바탕 약 18:1 |

고친 뒤 새 시험·관련 기존 시험이 모두 통과한다. D1~D5의 고침 전 상태에서 새 시험이 실패하는 것을 각각 확인했다(D5는 parts.js만 되돌려 `no heading level skipped` 실패 확인).

### 5.3 axe 기준선 (`tools/fixtures/web_app_flow_axe_baseline.json`)

```json
{"axe":"4.14.0","tags":["wcag2a","wcag2aa","wcag21aa"],
 "counts":{"home@no-match|1440|aria-required-children":1,"home@no-match|390|aria-required-children":1}}
```

- 검사한 화면 이름: home, home-list(옵션 열림), company, qgv, qgv-filtered, qgv-preview, qgv@loading, company@loading, qgv@empty-ranking, home@no-match, company@not-found, qgv@unpublished, company@unpublished, qgv@read-failed, company@read-failed, qgv@stale, company@stale, qgv@partial, company@partial, qgv@zero, company@zero(각 1440·390), 그리고 home·qgv·company @720z. 합계 45회.
- 그 밖의 위반은 0이다. 고친 결함(D1~D5)은 axe 태그 실행이 잡지 않는 종류였다(초점 표시·가려짐·필터 문구·실험 규칙·best-practice).

## 6. Lighthouse 기준값 (참고용, 합격 기준 아님)

개발 사이트(`tools/web_app_test_site.js` 빌드 + 같은 합성 fixture, 127.0.0.1, 캐시 헤더 없음), Lighthouse 기본 시뮬레이션 조절. 고친 뒤 실행. 점수: 성능 / 접근성 / 권장 사항.

| 화면 | 모바일 | FCP · LCP · TBT · CLS | 데스크톱 | FCP · LCP · TBT · CLS |
| --- | --- | --- | --- | --- |
| `#/` | 90 / 100 / 100 | 2.0s · 2.7s · 120ms · 0.124 | 77 / 100 / 100 | 0.4s · 0.6s · 0ms · 0.656 |
| `#/qgv` | 71 / 100 / 96 | 2.0s · 2.7s · 360ms · 0.316 | 54 / 100 / 96 | 0.4s · 4.2s · 50ms · 1.874 |
| `#/company/nvda` | 35 / 98 / 96 | 2.0s · 24.6s · 640ms · 0.61 | 55 / 98 / 96 | 0.5s · 4.4s · 0ms · 0.762 |

- 기업 화면 접근성 98은 D5(heading-order) 때문이고, 이 표를 잰 뒤 고쳤다(새 시험의 제목 단계 검사 통과).
- 권장 사항 96은 `errors-in-console` 하나: 시험 서버가 게시하지 않은 `sec-public-inputs.json`·`qgv-official-status.json`의 404다(PR 빌드와 같은 상태, 화면 결함 아님).
- 모바일 성능은 실행마다 크게 흔들린다. 첫 실행(다른 브라우저 시험과 동시에 돌아 CPU 경합) 홈 52 · 리더보드 59 · 기업 39였다. 위 표가 단독 실행 값이다.

주요 개선 기회(크기 순):
1. **모든 화면의 모듈을 경로와 상관없이 첫 그림 뒤 한꺼번에 읽는다**(loader.js LOAD_ORDER, 총 3.0~3.9MB: `screen-prompts-live.js` 240KiB, `chart-workbench.js` 134KiB 등). 미사용 JS 1.05~1.24MB, 기업 화면 LCP(QGV 카드 글)가 층이 다 온 뒤라 모바일 24.6s. → 경로별 지연 로딩. LOAD_ORDER가 빌드 규칙의 "하나의 목록"이라 설계 결정이 필요하다(오너).
2. **CLS 0.12~1.87**: 첫 그림 뼈대(연결 전 블록) → 자료 채움으로 main이 밀린다(P2-1a 분할 첫 그림의 결과). 블록 높이를 미리 잡으면 줄어든다.
3. 압축 안 된 JS 377KiB, 미사용 CSS 12~16KiB, `sec-qgv2.json` 693KiB(리더보드·기업 화면).
4. 캐시 정책(시험 서버가 헤더를 주지 않음 — GitHub Pages에서는 다르다. 기록만).
5. 렌더 차단: app.css(모바일 추정 1.3s 절감, 시뮬레이션 값).

## 7. Impeccable 검출 결과와 VISUAL_STYLE 기준 비평

`detect` 결과(오프라인, 렌더한 home·qgv·company DOM + app.css): 경고 9, 권고 1.

| 검출 | 자리 | 판단 |
| --- | --- | --- |
| side-tab ×2 | `.drawer-panel` 왼쪽 3px 선, `.mbox.blue` 왼쪽 4px 잉크 선 | **받지 않음.** 서랍의 가장자리 선과 선화 구분선이다. VISUAL_STYLE(흰 바탕 선화, 2~2.5px 잉크 선)이 도구 제안보다 우선 |
| repeated-container-text ×7 | 2.1.7 후보 선정 상자에 같은 기업 줄이 세 번(모델 상자 셋) | 내용 반복은 모델 상자 구조 때문. 화면 결함으로 보지 않음(기록) |
| em-dash-overuse(권고) | 리더보드 표의 `—` 182개 | `—` = 가격을 아직 안 불러옴(M3·수익률, 클릭 전), `NA` = 자료 없음. 뜻이 다르고 둘 다 회색이다. 다만 아래 혼동 목록 C4 참고 |

직접 비평(VISUAL_STYLE.md 기준, 고치지 않은 것):
- 흰 바탕·잉크 선·Jua 제목·기기 고딕 본문·그림자 없음·뜻 색 6개는 세 화면에서 지켜진다. 상태 캐릭터(로봇)는 빈·실패 상태에 한 장씩 있다.
- 로고 점의 빨강이 `shell.js`에 `#D7322A`로 직접 적혀 있다(문제 빨강 토큰 `--problem` #B4231C와 다름). 겉모습 차이는 작다. 토큰으로 옮길지 결정 필요(기록).
- 리더보드 폰 화면 높이 약 13,400px: 8개 블록이 모두 펼쳐진다. 표로 가는 "↑ 목록에서 보기" 링크가 있지만 길다(기록).

## 8. 혼동 가능 지점 (모집단·기준일·필터·공식/개인·0/NA)

| # | 화면 | 무엇이 헷갈리나 | 처리 |
| --- | --- | --- | --- |
| C1 | 리더보드 | 필터 상태가 표 옆에 없었다 | D3로 고침 |
| C2 | 기업 화면 NVDA(정상 상태) | Q·G·V·종합이 모두 숫자인데 순위 줄이 `순위 NA · 순위 없음`. 리더보드에서는 NVDA가 "일부 축만 가능" 목록(PARTIAL_AXES)에 있어 첫 50줄에 안 보인다. 카드 값은 게시본의 `TARGET:nvda` 행, 순위 판정은 Universe 행 기준으로 보인다 | **남김 — Codex 확인 필요**(층·게시본 의미). 이유 문구 "순위 없음"은 어느 목록인지 말하지 않는다 |
| C3 | 기업 화면 NVDA(점수 파일 404, 게시본만 있음) | 머리는 `NASDAQ:NVDA · Universe504`인데 QGV 카드는 `Universe 밖 TARGET이라 공식 순위 대상이 아닙니다` | **남김 — Codex/층 확인 필요** |
| C4 | 리더보드 표 | `—`(가격 불러오기 전)와 `NA`(자료 없음)가 같은 회색이다. 칸 안에 이유 글이 함께 있어 구분은 된다 | 기록 |
| C5 | 리더보드 기준 칩 | `점수 갱신 2026. 10. 13. 22:30 UTC · 마지막 확인 03:00` — 한 칩에 UTC 시각과 시간대 없는 이 기기 시각이 섞인다 | 기록(문구 결정 필요) |
| C6 | 리더보드 미게시 | 점수 파일 404는 "화면 상태 · 미게시"(plain 캐릭터)로, 내용 검증 실패만 "읽기 실패"로 보인다. 게시돼야 할 파일이 사라져도 "아직 게시 안 됨"으로 읽힌다 | 기록(PR 빌드 동작과 묶인 설계) |
| — | 공식/개인 | 2.1.6 배지(`공식 가중치 결과` / `내 설정 결과(미리보기)` · `공식 점수 아님`), 미리보기 때 표 머리·목록 잠금이 따로 보인다 | 구분됨(시험) |
| — | 진짜 0 / NA | 표 `0.0` 대 `NA` + 이유, 막대 실선 대 점선 | 구분됨(시험) |
| — | 모집단·기준일 | `Universe504` 표기, 가격 기준일·게시 시각(UTC)·STALE 칩이 리더보드와 기업 카드에 같은 말로 | 구분됨(시험) |

## 9. 미구현 (이 흐름 안)

- QGV **1.2 가중치 · 1.3 13F(연구 단계) · 1.4 구조 트리** 구역: "연결 전 · 다음 단계에서 연결". **1.5 QGV 상세**: "연결 전" 칩.
- 기업 화면 QGV 카드의 "→ 리더보드 · 가중치 · **스탯창**": 링크는 리더보드뿐이고 스탯창 화면은 없다.
- 리더보드 기간 **60D·120D·YTD·1Y**: "결정 대기 (IA-12)". **산업 단위**: "결정 대기 (IA-5)".
- 기간 수익률·M3 정렬은 구글 로그인·가격 시트 클릭 뒤에만 켜진다(이 시험은 클릭 경로를 다루지 않음 — `web_app_qgv_browser_test.js`가 대역으로 본다).
- 세부 화면(`#/detail/*`)은 P0 뼈대("이 세부 화면의 기능" 연결 전).
- 빈 점수 파일(유효한 `sec-qgv2.json`에 점수 행 0): 판독기 검증을 통과하는 합성본을 만들지 못해 다루지 못했다(10절 Codex 입력).

## 10. CI 연결에 필요한 것

- 이번 PR: `tools/ci_browser_tests.txt`에 새 시험 한 줄(목록 추가는 허용 범위). CI에는 axe가 없으므로 **규칙 검사는 건너뛰고 그렇게 출력하며, 키보드·초점·확대·상태·구분 검사만 돈다**(약 30초).
- axe까지 CI에서 돌리려면 **워크플로 변경(오너 승인 필요)**: `cockpit-pages.yml` build 단계에서 `npm install --prefix "$RUNNER_TEMP/pages-browser" axe-core@4.14.0`(--ignore-scripts)과 환경 변수 `AXE_CORE_PATH=$RUNNER_TEMP/pages-browser/node_modules/axe-core/axe.min.js`, `QUALITY_REQUIRE_AXE=1`. axe는 시험 러너에만 설치되고 Pages 산출물·web_app에는 들어가지 않는다.
- Lighthouse는 합격 기준으로 쓰지 않는다. 쓴다면 별도 수동 워크플로로 보고서만 산출물에 남기는 방식을 권한다(업로드 없음). 이것도 워크플로 변경이다.
- Impeccable은 CI에 넣지 않는다(엔진 바이너리 내려받기·사용 통계 API·live 모드가 있는 도구. 오프라인 `detect`의 이득이 작다).

## 11. Codex 입력이 필요한 것

- C2·C3: 기업 카드(게시본 `TARGET:<id>` 행)와 리더보드 목록(Universe 행) 사이의 순위·목록 판정이 같은 기업에서 다르게 보이는 이유와 의도된 문구.
- `sec-qgv2.json` 빈 상태(점수 행 0, `state: NOT_AVAILABLE`)의 판독기 검증을 통과하는 합성 벡터 하나(빈 상태 화면 시험용).
