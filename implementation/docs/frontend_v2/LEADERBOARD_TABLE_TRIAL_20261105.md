# QGV 리더보드 표 시험: Tabulator와 지금 표 (2026-11-05)

작성 2026-11-05 · Main. 브랜치 `claude/leaderboard-tabulator-trial` (기준 `ab6a83c3`).

- 근거: 오너 지시 "격리된 개발 페이지에서 Tabulator를 QGV 리더보드에 시험하고, 증거로 채택 / 현재 표 유지를 정할 것".
- 상태: **TESTED**. 합성 자료, 로컬 개발 페이지에서만 시험했다. 병합·배포·화면 변경 승인이 아니다.
- 이 브랜치는 출하 리더보드(`web_app/screen-qgv-live.js`)를 바꾸지 않는다. web_app·loader·Pages 빌드에 Tabulator를 넣지 않았다.

## 0. 결론

**지금 표를 유지한다. Tabulator는 지금 채택하지 않는다.**

이유는 아래 다섯 가지다. 앞의 셋은 어느 하나만으로도 채택을 막는다.

1. **정책 충돌(고정 정책 위반).** Tabulator는 그린 요소마다 `style` 속성을 단다. 합성 504행에서 요소 743개(폰 257개)에 달렸다. web_app 화면 시험 9개가 모두 `[style]` 0개를 확인한다. 또 `web_app_reuse_node_test.js` RULES 7개 규칙에 걸린다. 정책을 풀지 않고는 붙일 수 없다(5절).
2. **순위 규칙 위반.** QGV 머리글을 한 번 누르면 종합점수만으로 줄을 세운다. 그래서 QG 참고 행이 순위 행 사이에 섞인다. 합성 504행에서 첫 비순위 행이 4번째 자리에 나오고, 그 뒤로 순위 행 380개가 이어졌다. 같은 점수 행의 순서도 티커 순이 아니다. 지금 표의 D11 규칙(순위 행 → QG 참고 → NA, 섞지 않음; 동점은 순위 번호·티커 순)과 다르다. 바꾸려면 정렬 함수를 따로 짜야 한다(2.6절).
3. **키보드로 정렬할 수 없다.** 머리글이 포커스를 받지 못한다(포커스 가능한 머리글 0개). 탭으로 닿는 스크롤 칸에는 포커스 테두리가 없다(`outline: none`). 머리글 높이는 29px로, 앱 규칙 44px에 못 미친다(3절).
4. **크기.** gzip 기준 +107.6 KB다. 지금 표 코드(4.1 KB)의 약 26배이고, web_app 자체 파일 전체(274.8 KB)의 39%에 해당한다(4절).
5. **이득이 없다.** 실제 모집단은 Universe504 고정 504행이다(DC-01). 지금 표(처음 50행 + 더 보기)는 1440에서 렌더 10~39 ms, 폰(CPU ×4)에서 99~157 ms로 이미 빠르다. Tabulator의 가상 스크롤이 이기는 곳은 "모든 행을 한 번에 그릴 때"뿐이다. 지금 화면은 그렇게 하지 않는다.

**나중에 다시 볼 조건(모두 충족할 때만):**
- (a) 한 표에 2,000행 넘게 한 번에 보여야 하는 화면이 생긴다. 예: 확장 모집단을 한 표로 보기. 이것은 결정 대기 항목이다.
- (b) 그 화면의 `[style]` 규칙을 바꿀지 오너가 따로 결정한다. 예: Tabulator 영역만 예외로 두기. 이것은 가드 변경이다.
- (c) D11 정렬을 그대로 하는 사용자 정렬 함수, 머리글 키보드 정렬, 포커스 테두리, 44px를 직접 보완하고 시험으로 고정한다.
- (d) 필요한 모듈만 묶은 빌드(ESM 코어 + Sort/Filter/Format)로 크기를 다시 잰다.

(a)가 없으면 현재 표에 가상 스크롤이나 "더 보기" 크기 조정을 더하는 편이 싸다.

## 1. 무엇을 어떻게 쟀나

### 시험 도구

위치는 `implementation/tools/leaderboard_tabulator_trial/`이다. 개발용이고 CI 목록(`ci_*_tests.txt`)에 없다.

| 파일 | 역할 |
| --- | --- |
| `trial.html` | 시험 페이지. CSP 자리표시는 실행기가 `web_app/index.html`의 CSP 원문으로 바꾼다. |
| `trial.js` | 세 방식의 렌더러와 측정 API(`window.TRIAL`) |
| `trial.css` | 시험 페이지 배치 |
| `synthetic.js` | 시드 고정 합성 행 생성기 |
| `run_trial.js` | Playwright 실행기 |

### 설치와 실행

- Tabulator는 저장소 밖 스크래치 폴더에 설치했다: `npm i --ignore-scripts tabulator-tables@6.7.1`
- 실행기가 그 dist 파일 두 개를 SHA-256으로 확인한 뒤 임시 폴더에 복사하고, 127.0.0.1 정적 서버로 낸다.
- 같은 폴더에 web_app의 `core.js`·`screen-qgv-live.js`·`app.css`·Jua 글꼴을 고치지 않고 복사한다.

### 같은 행 만들기

1. **layer504.** 실제 앱 빌드(`web_app_test_site.js`)에 `qgv_v2_fixture.strictPayload()`, 분류 fixture, 합성 중앙 V 게시본(`qgv_official_vectors_v1.json`)을 넣는다(`web_app_qgv_browser_test.js`와 같은 구성). 그 상태로 `#/qgv`를 열고, `IS2.qgv.page()`의 Universe 행 504개에서 표시용 칸만 덤프한다.
   - 덤프 칸: 순위 문구, 종합·Q·G·V, 사유 문구, SIC, 업종군, 유형, 수집일
   - SIC와 업종군은 출하 helper `sicOf`·`industryOf`로 구했다.
   - 순위 행 15, QG 참고 11, 순위 없음 478이다.
2. **synthetic504 / 2000 / 10000.** `synthetic.js`가 만든다.
   - 식별자는 `SYNTHETIC:S00001`, `SYN00001`, `합성기업 00001`, `합성 업종 A~E` 형식이다.
   - 값의 약 8~12%는 NA다.
   - 순위는 생성기가 한 번만 매긴다(엔진 역할).
   - 입력 순서는 섞는다.

### 세 방식

| 방식 | 내용 |
| --- | --- |
| existing50 | 출하 표와 같은 방식이다. `IS2.h`, 출하 `helpers.sortRows`(D11), `app.css` 클래스(`.tbl`·`.th-btn`·`.pc-col`·`.m-only`·`details.na`)를 쓴다. 정렬·필터 때마다 표 전체를 다시 만들고, `data-k`로 포커스를 복구한다. 처음 50행과 "더 보기"를 둔다. |
| existingAll | existing50과 같은 방식으로 모든 행을 그린다(참고용). |
| tabulator | Tabulator 6.7.1 기본 테마, 가상 DOM(고정 높이 600px / 폰 70vh)이다. 열은 같고, 폰에서 숨기는 열(SIC·유형·Q·G·V·수집일)도 같다. 순위 칸은 행의 `rank_text`를 그대로 보인다(행 번호 매김 없음). |

열 범위는 순위·기업·SIC·유형·QGV·Q·G·V·자료 기준일이다. M3·수익률·1.1.8은 범위 밖이다.

### 같은 조건

- **정렬:** Q 머리글과 G 머리글을 번갈아 6번 누른다. 두 방식 모두 첫 클릭이 높은 순이다.
- **필터:** 업종 셀렉트에서 두 업종을 번갈아 6번 고른다.
- 뷰포트마다 새 페이지 5개(RUNS=5)를 쓴다. 렌더는 5개 표본, 정렬·필터는 각 30개 표본의 중앙값이다.
- 시간은 동작 직전부터, 표가 바뀐 뒤 다음 그림이 그려질 때까지(rAF + setTimeout 0)다. Tabulator는 `renderComplete`를 기다린 뒤 잰다.

### 화면과 기록

- 화면: 1440×1000(CPU ×1), 390×844(CPU ×4, `web_app_first_paint_browser_test.js`와 같은 폰 조건)
- 메모리: CDP로 GC를 실행한 뒤 `JSHeapUsedSize`와 `Nodes`를 렌더 전·후로 비교한다.
- 바깥 요청은 모두 막고 셌다. 결과는 0건이다.

### 출하 표 대조

실제 앱에서 출하 표가 그린 첫 50행(id·순위 문구)을 시험 페이지 existing50의 결과와 비교했다.

| 조건 | 결과 |
| --- | --- |
| 기본 정렬 | 같음 |
| Q 높은 순 | 같음 |
| 업종 필터(`finance_real_estate`) + Q 높은 순 | 같음 |

따라서 existing 방식은 출하 표와 같은 순서와 순위를 낸다.

## 2. 결과 수치 (중앙값, ms)

### 2.1 실제 앱 (출하 코드, layer504)

| 화면 | `#/qgv` 열기 → 첫 표 행 | 머리글 정렬 | 업종 필터 |
| --- | --- | --- | --- |
| 1440 | 855 (749–896) | 61 (49–125) | 32 (12–47) |
| 390 ×4 | 1687 (1484–1749) | 238.5 (69–307) | 111.5 (28–153) |

- 출하 코드는 정렬·필터 때 2.1.1~2.1.7 일곱 칸을 모두 다시 그린다. 그래서 아래 시험 페이지의 표만 그린 수치보다 크다.
- `[style]` 0개, CSP 위반 0건이다. 콘솔 오류 1건은 의도한 404(`sec-public-inputs.json` 미게시)다.

### 2.2 첫 렌더

| 자료 | 1440 existing50 | 1440 existingAll | 1440 tabulator | 390 existing50 | 390 existingAll | 390 tabulator |
| --- | --- | --- | --- | --- | --- | --- |
| layer504 | 39 | 386 | 89 | 157 | 1176 | 260 |
| synthetic504 | 10 | 147 | 75 | 99 | 550 | 239 |
| synthetic2000 | 33 | 573 | 82 | 89 | 2129 | 276 |
| synthetic10000 | 31 | 2711 | 95 | 121 | 11299 | 385 |

- Tabulator 파일을 읽고 실행하는 시간은 따로 더해야 한다. 1440에서 26~37 ms, 390에서 48~118 ms다.
- existing50은 그리는 행이 늘 50개라서 행 수와 거의 무관하다.

### 2.3 정렬 반응 (머리글 클릭)

| 자료 | 1440 ex50 | 1440 exAll | 1440 tab | 390 ex50 | 390 exAll | 390 tab |
| --- | --- | --- | --- | --- | --- | --- |
| layer504 | 25 | 322.5 | 31.5 | 91 | 1060.5 | 49.5 |
| synthetic504 | 22 | 138.5 | 33 | 61.5 | 501.5 | 53.5 |
| synthetic2000 | 22 | 572 | 33 | 74.5 | 2247.5 | 71.5 |
| synthetic10000 | 29 | 2873 | 54 | 106 | 11814 | 186 |

### 2.4 필터 반응

| 자료 | 1440 ex50 | 1440 exAll | 1440 tab | 390 ex50 | 390 exAll | 390 tab |
| --- | --- | --- | --- | --- | --- | --- |
| layer504 | 13 | 14 | 14 | 26 | 26 | 32 |
| synthetic504 | 15.5 | 29 | 25 | 58.5 | 97 | 54.5 |
| synthetic2000 | 21 | 105.5 | 29 | 56.5 | 461 | 55 |
| synthetic10000 | 20.5 | 485.5 | 31.5 | 74.5 | 2155 | 85 |

### 2.5 메모리 (렌더 후 − 전, GC 뒤)

| 자료 | JS 힙 ex50 / tab (KB) | DOM 노드 ex50 / exAll / tab |
| --- | --- | --- |
| synthetic504 (1440) | 134 / 844 | 2,052 / 23,222 / 2,242 |
| synthetic2000 (1440) | 130 / 1,215 | 2,052 / 93,930 / 2,386 |
| synthetic10000 (1440) | 93 / 3,148 | 2,052 / 466,202 / 2,482 |
| synthetic10000 (390) | 90 / 3,058 | 2,052 / 466,202 / 1,319 |

- Tabulator는 행마다 Row·Cell 객체를 JS 힙에 둔다. 10,000행에서 약 3 MB다.
- existingAll의 비용은 JS 힙이 아니라 DOM 노드에 있다.

### 2.6 순위·NA·정렬 의미

- **순위 문구 불변:** 방식 × 자료 × 화면 24조합 각각에서 65회(렌더 1회와 정렬·필터 12회, 5페이지) 확인했다. 그린 행의 순위 문구가 원래 값과 다른 경우는 0건이다.
- Tabulator의 active 데이터 순위 불일치 0건, NA를 0으로 그린 칸 0개다.
- 필터는 행을 숨기기만 하고 번호를 다시 매기지 않는다. 두 방식 모두 같다.
- **동점 순서:** G 높은 순 한 번 뒤의 전체 순서를 비교했다.
  - 값 순서는 두 방식이 같다(`sameValues` 모두 참).
  - 동점 행의 id 순서는 Tabulator에서 다르다. 어긋난 행은 504행 중 146개, 2,000행 중 1,252개, 10,000행 중 9,067개, layer504(NA가 많음)에서 474개다.
  - 지금 표는 동점을 티커 순으로 놓는다. Tabulator는 이전 순서를 그대로 둔다(안정 정렬).
- **QGV 머리글 정렬(D11):**

  | 자료 | 지금 표: 첫 비순위 행 위치 / 그 뒤 순위 행 수 | Tabulator: 첫 비순위 행 위치 / 그 뒤 순위 행 수 |
  | --- | --- | --- |
  | synthetic504 | 385 / 0 | 5 / 380 |
  | synthetic10000 | 7423 / 0 | 2 / 7421 |
  | layer504 | 16 / 0 | 3 / 13 |

  지금 표는 순위 행이 모두 끝난 뒤에야 비순위 행이 나온다. Tabulator는 QG 참고 행과 순위 행을 섞는다. 이는 "산출 상태별 목록을 순위에 섞지 않음"(2.1.5) 규칙에 어긋난다. `aria-sort`는 두 방식 모두 `descending`으로 맞게 단다.

## 3. 키보드 · 스크린리더 · 폰 (synthetic504)

| 항목 | 지금 표 1440 / 390 | Tabulator 1440 / 390 |
| --- | --- | --- |
| Tab으로 Q(폰: QGV) 정렬 버튼 도달 | 4번째 / 3번째 Tab | **도달 못 함**(머리글 포커스 가능 0개) |
| Enter로 정렬 | 됨 | 해당 없음(마우스·터치만) |
| Tab으로 행 안 항목 도달 | 8 / 4 (기업 링크) | 3 / 3 (기업 링크. 링크를 넣었기 때문이고, 없으면 행에 못 닿는다) |
| 포커스 테두리 | 모든 정지점 3px | 스크롤 칸(`tabulator-tableholder`, 2번째 Tab)이 `outline: none`. **보이지 않음** |
| 역할·이름 | `table` + caption("합성 자료 · 정렬: … · 표시 50개"), 머리글 버튼 이름 "Q ↓", `aria-sort` | `grid` / `columnheader` / `gridcell`. caption 없음, 정렬 상태 문장 없음, 전체 행 수(`aria-rowcount`) 없음. 가상 DOM이라 보조기술에는 그려진 20~50행만 보인다 |
| 정렬 머리글 높이 | 44 px | **29 px** (앱 규칙 44 px 미달) |
| 폰 가로 넘침 / 표 가로 스크롤 | 없음 / 없음 | 없음 / 없음 |
| 최소 글자 | 13 px (폰) · 14 px | 13 px · 14 px |
| 폰에서 보이는 열 | 3 (순위·기업·QGV) | 3 (같은 설정) |
| 행 높이 | 82 px (폰, 기업 칸 두 줄) · 43 px | 68 px · 29 px |

폰 가독성은 같은 열 설정에서 비슷하다. 차이는 키보드·스크린리더와 탭 크기에 있다.

## 4. 크기 (gzip -9)

| 파일 | 원래 | gzip |
| --- | --- | --- |
| `tabulator.min.js` 6.7.1 | 455,489 B | 103,699 B |
| `tabulator.min.css` 6.7.1 | 28,383 B | 3,926 B |
| **Tabulator 합계** | | **107,625 B** |
| 지금 표 코드 (`screen-qgv-live.js`의 `table()`~`row()` 부분, 압축 안 함) | 9,804 B | 4,107 B |
| `screen-qgv-live.js` 전체 (출하 그대로) | 55,163 B | 20,320 B |
| web_app 자체 js·css 전체 | | 274,834 B |
| 참고: 이미 들인 `lightweight-charts-5.2.1.standalone.js` | 197,922 B | 62,145 B |

Tabulator는 지금 표를 대체하지 않고 더해진다. 2.1.2~2.1.7과 정렬 helper는 그대로 남는다. 늘어나는 양은 약 +107.6 KB(gz)다.

## 5. 호환성

| 항목 | 결과 | 판정 |
| --- | --- | --- |
| CSP (`style-src 'self'`, `'unsafe-inline'` 없음) | Tabulator는 스타일을 CSSOM(`el.style.x=`)으로만 쓴다. `<style>` 주입과 `setAttribute('style')`는 없다. 시험 페이지(앱 CSP 그대로)에서 위반 **0건**. | 통과 |
| `[style]` 속성 금지 (web_app 화면 시험 9개: home·qgv·shell·macro·prompts·tree·technical·news·lab, 공통 패널 시험) | CSSOM 쓰기도 `style` 속성을 만든다. 1440에서 743개(504행), 폰에서 257개. 속성 종류는 height·width·text-align·min-width·display·max-height·padding-top. layer504에서도 293개(폰 197개). | **충돌** |
| `web_app_reuse_node_test.js` RULES (web_app의 모든 `.js`) | `tabulator.min.js`에 걸리는 규칙: console 201, innerHTML 등 HTML 문자열 66, NA를 0으로 채움 형태(`\|\|0`) 29, `.style.` 쓰기 261, localStorage·sessionStorage 4, `fetch(` 2, 계산된 태그 createElement 9. 걸리지 않는 규칙: eval·script 요소·style 문자열. | **충돌** (web_app에 두면 시험 실패) |
| loader 경로 | 이름 `tabulator.min.js`는 loader NAME 규칙을 통과한다. 옛 lightweight-charts처럼 `web_assets`에 두고 LOAD_ORDER에 넣으면 RULES는 피한다. 다만 `web_app_reuse_node_test.js`의 "reuse list is the design list" 단언을 바꿔야 한다. CSS는 loader가 싣지 않으므로 `index.html`에 `<link>`를 하나 더하거나 DOM으로 붙여야 한다. script 요소는 loader 밖에서 만들 필요가 없다. | 가능하나 시험 단언 변경 필요 |
| 자체 호스팅 · 외부 요청 | npm dist 파일을 그대로 쓸 수 있다. 시험 중 바깥 요청 0건. `fetch`·XHR(ajax 모듈)·localStorage(persistence 모듈)는 옵션을 켜야만 쓰이며 이번 설정에서는 쓰이지 않았다. | 통과 (설정 조건부) |
| Pages 가드 (`pages_artifact_guard.py`) | 두 파일은 `ALLOWED_NAMES`에 없어 `unexpected_entries`가 된다. `APPROVED_SHA256`에 SHA를 고정하는 가드 변경이 필요하다. 가드 프로세스 안에서만 SHA를 넣어 본 내용 검사(SECRET_PATTERNS·KIS 표지·비공개 경로·형식)는 위반 0, 2 MiB 이하다. 참고로 지금 새 앱 개발 빌드는 이미 가드 FAIL(`unexpected_entries` 36 · `missing_files` 52 · `unapproved_content` 2)이며, 이는 P3 전환 4번 항목이다. | 가드 고정값 변경 필요 → 오너 승인 |
| 시각 양식 (VISUAL_STYLE) | 기본 테마에 회색 머리글(`#e6e6e6`), 줄무늬, `#1d68cd` 포커스, 그림자 1곳(`box-shadow:0 0 5px`), 12~20px 글자가 있다. 테마를 다시 써야 한다. | 추가 작업 |
| 라이선스 | MIT. `package.json`과 `LICENSE`("Copyright (c) 2015-2026 Oli Folkerd")를 확인했다. 의존성 0, install 계열 스크립트 없음. | 통과 |

정책은 하나도 풀지 않았다. 위 충돌은 그대로 이번 시험의 결과다.

## 6. 아이콘

리더보드와 기업 흐름은 아이콘 대신 글자 기호를 쓴다.
- 정렬 화살표 `↑`·`↓`, 사유 펼치기 `▸`, 필터 `▾`, `★`·`☆`, 이동 `→`, 외부 링크 `↗`, 단계 `①②③`
- 선화 SVG는 `core.js` `icon()`과 `parts.js` `mascot()`으로 그린다.

**새 아이콘 묶음이 필요한 빈자리는 없다.** 확인한 작은 불일치는 하나다.
- 리더보드 기준 칩의 "IEX 약관" 링크(`screen-qgv-live.js` `central()`, `target=_blank`)에는 외부 표시가 없다.
- 기업 화면의 "원문 보기 ↗"에는 있다.

이 불일치는 기존 `↗` 글자로 맞출 수 있어 Tabler Icons를 들일 이유가 아니다. 따라서 들이지 않는다. 나중에 정말 필요해지면 후보는 `@tabler/icons` 3.50.0(MIT, 2026-10-27 게시)의 `arrows-sort`·`external-link`·`filter`·`star`이고, 그때 버전을 다시 고정한다.

Lightweight Charts 5.2.1(Apache-2.0)은 이미 `web_assets`에 자체 호스팅되어 있다. 가드 SHA, LICENSE·NOTICE, `third-party-notices.txt`도 갖췄다. 차트가 필요하면 그것을 다시 쓴다. 새 앱 LOAD_ORDER에는 아직 없다.

## 7. 후속 후보 (후보일 뿐, 채택 아님)

| 도구 | 화면 필요 | 입력 준비 |
| --- | --- | --- |
| **ECharts** 6.1.0 (Apache-2.0) | 히트맵·분포·다축처럼 Lightweight Charts(시계열 전용)가 못 하는 그림. 4.2 순환매(섹터 ETF 12 + SPY 상대강도 표), 4.3 SIC 산업 사이클, 9.1 Lab 지표 비교. 2.4.5 레이더는 `stat-radar.js`가 이미 그린다. | **미준비**: 4.2는 `PRIV-ETF` 수집이 승인됐으나 비공개 칸만 있고 모델 승인 전이다. 4.3은 위치·확률이 미산출이다. 9.1 공개 결과는 `LAB-PUBLISH` 결정 대기이고, 비공개 `lab-backtest-v1` 자산 곡선은 시계열이라 Lightweight Charts로 된다. |
| **Cytoscape.js** 3.34.4 (MIT) | 5.1 관계망(가운데 기업과 공급망·고객·경쟁), 4.5 나비효과(영향 경로) | **미준비**: 관계 자료원 `REL-SOURCE` 결정 대기(USER_DECISIONS_PENDING). 5.1은 "관계 자료 미연결", 4.5는 준비 중(NOT_AVAILABLE)이다. 8.1 구조 트리는 WAI-ARIA 트리로 이미 있어 필요 없다. |
| **GridStack** 14.1.0 (MIT) | 사용자가 카드를 끌어 배치하는 대시보드(홈·기업 화면 카드 순서) | **필요 자체가 미정**: 배치는 시안 고정이고, 끌어 놓기 배치를 정한 결정이 없다. 오너는 폰만 쓰므로 끌기 격자의 이득이 작다. 배치를 저장하려면 P1 store 키를 새로 정해야 한다. |

## 8. 재현

```sh
P=<scratch>   # 저장소 밖
mkdir -p $P/tools-tabulator && cd $P/tools-tabulator && npm init -y && npm i --ignore-scripts --no-audit --no-fund tabulator-tables@6.7.1
cd <worktree>
TRIAL_RUNS=5 TRIAL_OUT=$P/tab-trial/full TABULATOR_DIR=$P/tools-tabulator/node_modules/tabulator-tables \
  NODE_PATH=$P/pw158/node_modules PLAYWRIGHT_BROWSERS_PATH=$P/pw158/browsers \
  node implementation/tools/leaderboard_tabulator_trial/run_trial.js
```

- 도구: Playwright 1.58.2 + Chrome Headless Shell(CI와 같음), Node 22.22.0.
- 실행 시간은 약 30분이다. 대부분이 390 existingAll 10,000행이다.
- 결과 `results.json`은 스크래치에만 두고 올리지 않는다.
