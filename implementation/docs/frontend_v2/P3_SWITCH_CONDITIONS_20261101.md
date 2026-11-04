# P3 전환 조건 정리 (2026-11-01, Main — DC-42 "P3 전환 조건" 이행)

새 앱(`web_app/`)으로 옛 공개 화면(`web_assets/`)을 한 번에 바꾸는 **P3 전환**의 조건을 한곳에 모은다. 이 문서는 조건과 현재 상태 정리이며 **전환·병합·배포 승인이 아니다.** P3 전환은 오너 승인으로 한다.

- 근거 구분: Main 하위 조사(읽기 전용, 2026-11-01). 직접 실행한 것은 `build_web_app.py`로 스크래치 폴더에 로컬 빌드 1회와 그 결과에 `pages_artifact_guard.py` 1회다. 네트워크 요청은 없었다. Main이 일부(포트폴리오 자리표시 344바이트, QGV 2.2~2.4 "다음 단계에서 연결", 배포 빌드가 `web_assets`를 내보냄, 계획 표 P3 줄)를 다시 확인했다.
- 줄 번호는 이 문서를 넣은 커밋(#457 가지) 기준이다. 뒤 커밋에서 밀릴 수 있다.
- **요지:** 전환을 막는 것은 비공개 자료나 경계 시험이 아니라 **새 앱에 아직 없는 화면**(포트폴리오 6, QGV 2.2~2.4, 세부 화면 7개)과 배포 빌드·가드 고정값 교체, 옛 모듈 61개 처리 방침, PWA 처리 방침이다. 실자료 백테스트·회원 DB는 전환 조건이 아니다(DC-42).

## 0. P3 정의 원문

- `implementation/docs/frontend_v2/FRONTEND_V2_PLAN.md:73` — "P3 전환 | 경계 시험 이식(가격 비공개, NA, 요청 원칙, CSP, 저장소 사용), 가드 고정값 교체, 옛 화면 삭제, 한 번에 배포·실사이트 확인 | 전환 PR 1개".
- 같은 문서 `:11-15` — 한 번에 전환한다. 메뉴 0~n+1과 모바일을 다 만든 뒤, 경계 시험을 옮겨 통과시키고 한 번에 배포한다. 그때 옛 화면을 지운다. 그때까지 실사이트는 그대로다.
- `:27-34` — "2. 유지할 경계 (전환 PR의 통과 조건)" 6개(아래 1-a·1-b).
- `implementation/docs/handoff/HANDOFF_HISTORY_20261024.md:17` — P3 전환은 사용자 승인으로 한다.
- `docs/SPEC/DIRECTION_CHANGES.md:33`(DC-20) — "별도 P3 승인 조건은 유지".
- grep 거짓 양성: `FRONTEND_INTERACTION_CONTRACT_20261019.md:183,462-465`, `FRONTEND_DATA_CONTRACT.md:400-403`의 "P3"는 우선순위 표시다. 매크로·백테스트·QGV 문서의 P3도 이 전환과 무관하다.

## 1. 이미 적힌 전환 조건

### (a) 옮길 경계 시험

계획 원문: 경계 1~4·6은 `FRONTEND_V2_PLAN.md:29-34`. 새 앱 시험은 `tools/web_app_*_test.js`이고, 스스로 개발 빌드를 만든다. CI 목록에 들어 있어 매 PR에서 돈다(`:47`).
CI 목록: `ci_browser_tests.txt`는 101개 중 web_app 12개, `ci_node_tests.txt`는 78개 중 web_app 11개.

| 경계 | 옛 화면 시험·가드 | 새 앱에 같은 시험 | 판정 |
| --- | --- | --- | --- |
| 가격 비공개 (`:29`) | `pages_artifact_guard.py`(산출물 검사, SENSITIVE_KEYS·SECRET_PATTERNS·KIS 표지). `src/investment_system/public_price_boundary.py:89` AUDITED_ROUTES에 `web_assets/app.js`. `tests/test_public_price_boundary.py`. `pages_cockpit_browser_test.js`(배포 워크플로의 "price-free pages" 단계, `cockpit-pages.yml:182-196`). `price_store_*`, `chart_network_recording_browser_test.js` | `web_app_data_layer_browser_test.js`(sentinel 가격이 저장소·콘솔·URL·본문에 없음, `[data-ram-price]` 밖 금지). 각 화면 시험의 boundaries 단계. `tests/test_private_boundary_static.py:61-62`가 web_app·web_assets 둘 다 검사. `web_app_reuse_node_test.js:442-449`는 Pages 가드의 SECRET_PATTERNS만 web_app 원본에 적용 | **부분**. 새 빌드 산출물 전체에 Pages 가드를 돌리는 시험이 없다. `public_price_boundary.py` AUDITED_ROUTES에 web_app 경로가 없다 |
| NA를 0으로 안 채움 (`:30`) | `tests/test_target_na_schema_v4.py`, `tests/test_universe_conflict_na_priority.py`, `qgv_v2_screens_browser_test.js`, `v_coverage_browser_test.js`, `official_personal_labels_browser_test.js` | 화면 시험 15개가 NA 단언을 가진다(grep). 예: `web_app_qgv_browser_test.js`(NA와 사유), `web_app_lab_node_test.js`(`nullText`). 기준 벡터: `tools/fixtures/web_app_qgv_screen_expected.json` | **있음**(만든 화면 한정). 포트폴리오·세부 화면은 화면이 없어 시험도 없다 |
| 클릭 요청 원칙 (`:31`) | `price_store_browser_test.js`, `google_sheet_quotes_browser_test.js`, `chart_network_recording_browser_test.js`, `worker_quote_fallback_node_test.js`, `data_refresh_browser_test.js` | `web_app_data_layer_browser_test.js` A·B·C·C2(행동 없이 요청 0, 흉내 이벤트 거절 `CLICK_REQUIRED`, 진짜 클릭만), `web_app_prices_node_test.js`, 각 화면 "click-only" 단계 | **있음** |
| CSP (`:32`) | `tests/test_app_nav_ia.py:20-45`가 **`web_assets/index.html`**의 CSP를 정확히 고정 | `web_app_reuse_node_test.js:199-206`은 새 CSP가 **옛 index.html CSP와 같음**만 본다. 로컬 확인: 지금 두 CSP는 같다. 셸 시험은 CSP 위반 콘솔 오류 0 | **부분**. 옛 파일을 지우면 두 시험 다 기준이 사라진다. 새 index.html에 직접 고정해야 한다. 옛 CSP에는 TradingView `frame-src`가 있다. 계획 `:32`의 "구글 로그인·시트·Worker만"과 맞출지는 미확인 |
| 저장소 사용 (계획 표 `:73`, DC-18) | `device_backup_*`, `settings_import_browser_test.js`, `watchlist_*`, `device_actual_*`, `device_market_node_test.js` | `web_app_shell_browser_test.js:92`(열기만 해도 localStorage·sessionStorage·IndexedDB 0), 데이터층 시험 A(저장 0)·`MARKET_STORE_STOPPED`, `web_app_private_panel_browser_test.js`(요청·저장 없음) | **부분**. 쓰기 정책은 시험됨. "저장된 시세 삭제"는 `store.js`·`action.js` API만 있고 버튼이 없다(설정 세부 화면이 자리표시). `P1_DATA_LAYER.md:416` |
| 매수·매도·주문 없음 (`:34`) | `spec_direction_guard.py`, Pages 가드 KIS 주문 TR 패턴 | 새 앱 전용 시험은 못 찾음 | **미확인** |

### (b) 바꿀 가드 고정값

- 원문: `FRONTEND_V2_PLAN.md:33` — 2 MiB·192개·sha256 고정은 완화하지 않는다. 전환 PR에서 새 파일 목록으로 고정값을 바꾼다.
- `tools/pages_artifact_guard.py:56` `APPROVED_SHA256` — 121개 이름 고정(옛 화면 JS·CSS·html·아이콘·글꼴). `:191` `FONT_FILES`에 옛 `gaegu-regular-ksx1001.woff2`. `:194` `ALLOWED_NAMES`. 한도 `:195`(2 MiB)·`:204`(192개)는 그대로 둔다.
- 로컬 실측: 새 빌드는 파일 119개, 2 MiB 넘는 파일 없음, 3.3 MB. 가드는 FAIL(`unexpected_entries` 34, `missing_files` 52, `unapproved_content` 2).
  - 고정에 없는 이름 34개: `action.js`·`app.css`·`boot.js`·`core.js`·`loader.js`·`screen-*.js` 등 web_app 파일 전부.
  - 같은 이름인데 해시가 다른 것: `index.html`·`screen-detail.js`(+ 로컬 자료 JSON 4개. 실제 배포에서는 파이프라인 자료라 다를 수 있음, 미확인).
  - 실제 공개 자료까지 넣은 배포의 파일 수는 미확인.
- 재사용 옛 모듈 61개(P1 A안, `build_web_app.py:8-10`, `tools/web_app_reuse.js`)는 바이트 그대로라 기존 고정을 유지한다. 이 고정은 그대로 써도 된다.
- 다른 고정:
  - `tests/test_pages_cockpit_build.py:35` "only web_assets … exported".
  - `tests/test_app_nav_ia.py` CSP.
  - `public_price_boundary.py` AUDITED_ROUTES.
  - `web_app_reuse_node_test.js`의 `REUSED.length === 61`, CSP가 옛 것과 같음.
  - `pages_freshness_guard.py`(자료 신선도, 배포 직전 `cockpit-pages.yml:250`)는 화면 파일과 무관해 보인다(미확인).

### (c) 지울 옛 화면과 아직 기대는 것

| 기대는 것 | 근거 | P3에 주는 영향 |
| --- | --- | --- |
| 배포 빌드 자체 | `tools/build_pages_cockpit.py:23`이 `web_assets`를 내보냄. 배포 경로 둘: `cockpit-pages.yml:149-150,256`, `sec-daily-public-inputs.yml:83-84,326`(야간). `build_web_app.py:1-6`은 "전환 전까지 배포에 안 쓰임" | 두 워크플로를 새 빌드로 바꿔야 한다 |
| 재사용 옛 모듈 61개 | `build_web_app.py:8-10`. 예: `target-v1-builder.js`, `qgv-official.js`, `device-actual.js`, `playbook-engine.js`, `virtual-trading*.js`, `google-sheet-*.js` | `web_assets`를 통째로 지울 수 없다. 61개를 web_app으로 옮기거나 남겨야 한다. 계획 문서에 어느 쪽인지 없음(미확인) |
| 옛 함수 실시간 대조 시험 | `P1_DATA_LAYER.md:175,488` — "P3가 옛 파일을 지우면 사본은 하나만 남는다 / 실시간 비교만 뺀다" | `web_app_qgv_screen_node_test.js` 등에서 실시간 비교를 빼고 고정 벡터만 남긴다 |
| TARGET v1 빌더 옛 V 출처 | `START_HERE.md:20`, `CURRENT_HANDOFF.md:97,112`, DC-31 `DIRECTION_CHANGES.md:44` — 11/09~11/15 확정 기간에는 V 출처를 안 바꾼다. 11/16 PR에서 기기 V 경로를 지운다 | 새 앱의 TARGET v1 빌더 세부 화면은 자리표시다(`web_app/core.js:54`, `screen-detail.js`). 확정은 옛 화면에서 한다. 그래서 P3는 11/16 PR 뒤가 안전하다(추론, 문서에 명시 없음) |
| `device-valuation.js` 정리 | `FUNCTION_STATUS.md:57` — "11/16 뒤 정리 PR" | 재사용 61개에 들어 있다. P3와 묶을지는 미확인 |
| 기기 V 폐지 DC-31 | #435(새 앱)·#439(옛 화면) 병합. 남은 것: S06 GOOG 후속 PR, 11/16 TARGET PR(`CURRENT_HANDOFF.md:13`) | direction guard 규칙 DC-31a·b의 TARGET 예외 단어는 11/16 PR에서 지운다(`DIRECTION_CHANGES.md:44`) |
| TV0-RANKLIST·TV0-S06 | `USER_DECISIONS_PENDING.md:792-793` — 새 앱은 뺌 방향, 옛 화면·옛 S06은 P3에서 교체. 결정 전 동작 "남김(옛 화면)" | P3가 사실상 "뺌"이 된다. 결정 닫기가 필요하다 |
| IndexedDB `market` 시세 | `P1_DATA_LAYER.md:137,416`, DC-18 — 옛 화면은 P3까지 계속 쓴다 | 지운 뒤 남은 기록은 "저장된 시세 삭제"로만 지운다. 버튼은 아직 없다 |
| 손 입력 시세·환율 | `USER_DECISIONS_PENDING.md:786` MANUAL-QUOTE — 옛 화면은 P3까지 그대로, P2-6 전에 정한다 | 결정 전에 P3를 하면 기능이 없어진다 |
| PWA(설치·오프라인) | `web_assets/index.html:10` manifest, `web_assets/pwa.js:15`가 `service-worker.js` 등록. 새 빌드에는 manifest·service-worker·offline.html·아이콘이 없다(로컬 실측) | 계획 문서에 언급 없음. 폰에 설치된 옛 서비스 워커를 둘지·지울지는 미확인. `pwa_browser_test.js`·`pwa_node_test.js`(CI 등록)의 처리도 미확인 |
| 옛 시험 | `tests/*.py` 46개, `tools/*` 103개가 `web_assets`를 언급. 옛 화면 시험은 브라우저 약 89개·노드 약 67개 | 지우기·옮기기 목록이 필요하다. 재사용 모듈 시험(예: `qgv_official_node_test.js`)은 남긴다 |
| 비공개 칸 | `private_area/PRIVATE_AREA_KIS_DESIGN_20261031.md:163` — 새 앱은 P3 전까지 배포 안 됨. 비공개 칸도 P3 때 같이 보인다 | 배포 뒤 모든 칸은 "비공개 기능 준비 중"으로 보인다 |

### (d) 배포·실사이트 확인

- 원문은 "한 번에 배포·실사이트 확인"(`:73`)뿐이다. 구체 절차 문서는 못 찾았다(미확인).
- 기존 배포 관문:
  - CI 목록 전체 실행(`cockpit-pages.yml:191,196`).
  - Pages 가드(`:150,166`).
  - 신선도 가드(`:250`).
  - `deploy-pages`(`:256`). 야간 워크플로도 같은 사슬이다(`sec-daily-public-inputs.yml:270-275,326`).
- 이전 실사이트 확인 관례:
  - "처음 쓰는 기기에서 공개 자료가 같게 보임"(DC-22, `FUNCTION_STATUS.md:98`).
  - 10-29 TARGET 실기기 확인(`FUNCTION_STATUS.md:50`).
- 승인: 병합·배포는 오너 승인 범위에서만 한다(`START_HERE.md:32`, `HANDOFF_HISTORY_20261024.md:17`).
- 첫 화면 목표: 390×844, 첫 화면 2,000 ms 이하, 첫 전송 100 KB 이하(`FUNCTION_STATUS.md:107`, `web_app_first_paint_browser_test.js`). 실사이트 측정은 미확인.

### (e) 기능 1~9 준비 상태 (새 앱)

| 기능 | 새 앱 화면 병합 | 공개 층 완결을 막는 것 |
| --- | --- | --- |
| 1 기업 검색·진입 | 병합: #408·#419·#420(`FUNCTION_STATUS.md:98`) | 없음(확인 범위). 기본 목록은 TARGET v1 공개본 게시 전까지 v0 표시(`P1_DATA_LAYER.md:449`) |
| 2 QGV | 2.1만 병합(#415, `:99`). 2.2 가중치·2.3 13F·2.4 QGV 상세·QGV 안 2.5 트리는 "다음 단계에서 연결"(`web_app/screen-qgv.js:23-33`). 2.1.7 TARGET 빌더는 세부 화면 자리표시 | 2.2(공개 층은 "그대로 완전히 동작", `FUNCTION_STATUS.md:123`)와 2.4 없음. `CURRENT_HANDOFF.md:15` "V가 필요한 화면 2.2, 2.4·레이더, 6: 대기" |
| 3 기술적 분석 | 병합 #450(`:100`) | 공개 쪽은 합성 봉. 판정 보류가 설계대로다 |
| 4 매크로 | 병합 #445(4.1~4.4, `:101`) | 4.5·4.6 새 앱 상태는 문서에 따로 없음(미확인) |
| 5 뉴스 | 병합 #450(5.1~5.3, `:102`) | 5.1 관계 자료 미연결(REL-SOURCE) |
| 6 포트폴리오 | **미병합**. `web_app/screen-portfolio.js`는 344바이트 자리표시(P2-6). 6.2·6.3 보고(`daily-report.js`)는 재사용 목록에 없다 | 6.1~6.4 공개 층이 통째로 없다. MANUAL-QUOTE 결정, #392 미정 |
| 7 프롬프트 | 병합 #445(`:105`) | 없음 |
| 8 구조 트리 | 병합 #445(`:105`) | 8.1.3 상태 표시와 이 문서 맞추기(`:87`) |
| 9 Lab | 병합 #450(9.1 문구·준비 목록, 9.2 원장 v1·v2, `:104`) | 공개 결과 없음은 설계대로(LAB-PUBLISH 전) |
| 세부 화면 7개 | **전부 자리표시**(`core.js:47-55`, `screen-detail.js`): 설정·시트 연결, 자료 상태, 재무 상세, SEC 표지, 플레이북, 가상매매, TARGET v1 빌더 | 계획 `:10`이 이 기능들을 세부 화면으로 옮기라고 했다. 시트 출처 저장 UI가 새 앱 어디에 있는지 미확인 |

2층 경계: 모든 새 화면의 비공개 칸은 `IS2.parts.privatePanel` 하나다. 공개 부분은 그 칸을 기다리지 않는다(`COMMON_BASE_20261031.md:61-69`, `web_app_private_panel_browser_test.js`). 확인 범위에서는 비공개 자료 때문에 공개 층이 막힌 곳이 없다. 막는 것은 **화면이 아직 없는 것**(2.2·2.3·2.4·6·세부 7개)이다.

## 2. P3·옛 화면·새 앱·화면에 걸린 남은 오너 결정

출처: `USER_DECISIONS_PENDING.md` "남아 있는 결정만"(이 커밋 기준 763줄~).

| 번호 | 줄 | P3와의 관계 |
| --- | --- | --- |
| MANUAL-QUOTE | 786 | 손 입력 시세·환율을 새 앱 어디에 둘지. "P2-6 전에 정한다", 옛 화면은 P3까지 그대로 |
| TV0-RANKLIST | 792 | 옛 화면은 P3에서 교체. 새 앱은 뺌 방향 |
| TV0-S06 | 793 | 옛 S06은 P3에서 교체. 새 리더보드는 이미 뺌 |
| EXP-OFFICIAL | 778 | "P3 승인 전 승격 안 함". 이 P3가 프론트엔드 P3인지 정의가 없다(미확인) |
| PRICE-DISPLAY (#433) | 777 | 간접: 승인되면 경계 3(클릭 요청)과 가격 비공개 시험의 기준이 바뀐다 |
| LISTING-ENDED-CODE | 783 | 화면의 'CIK 미해결' 표기. 11/9 창 뒤 별도 PR |
| FIN-NA-CODE | 805 | 화면 NA "해당 없음" 구분. NA 표시 시험에 영향 |
| NEWS-CAP | 802 | 공시 목록 정책. 결정 뒤 화면 PR |
| IA-2~18 | 801 | 새 내용구조 구현 결정(로그인 백엔드, 글꼴, 레이더 축 등) |

관련 지시(결정 아님): `USER_DECISIONS_PENDING.md:70,92`(11/01 3차) "P3 전환 조건 정리"가 Main 다음 일이다. `CURRENT_HANDOFF.md:109`도 같다.

## 3. 전환 PR 1개 점검표 (제안 순서)

| # | 항목 | 상태 | 근거 |
| --- | --- | --- | --- |
| 0 | 선행: 메뉴 0~n+1·모바일·세부 화면 완성(계획 `:12`) | **부분** | 6 포트폴리오·2.2~2.4·세부 7개 없음(1-e) |
| 0a | 선행 결정: MANUAL-QUOTE, TV0-RANKLIST·TV0-S06 닫기, #392 처리 | **없음** | 2절 |
| 0b | 시기: 11/16 TARGET 경로 PR 뒤, 11/09~11/15 확정 창 밖 | **미확인**(추론) | DC-31, `CURRENT_HANDOFF.md:112,140` |
| 0c | 오너 승인(병합·배포) | **없음** | `HANDOFF_HISTORY_20261024.md:17` |
| 1 | 배포 빌드 전환: `build_pages_cockpit.py`를 새 빌드로(또는 `build_web_app.py` 통합). 두 워크플로 모두 | **없음** | `cockpit-pages.yml:149`, `sec-daily-public-inputs.yml:83` |
| 2 | 재사용 61개 처리(web_app으로 옮김 또는 유지)와 `web_app_reuse.js` 경로 정리 | **없음**(방침 미확인) | `build_web_app.py:8-10` |
| 3 | 옛 화면 파일 삭제(`web_assets` 중 재사용 밖, `research.html`·`network.html` 생성 포함) | **없음** | `build_web_app.py:29` GENERATED_OLD_PAGES |
| 4 | Pages 가드 고정값 교체: `APPROVED_SHA256` 새 목록, `FONT_FILES`에서 gaegu 제거, 한도 그대로 | **없음** | `pages_artifact_guard.py:56,191,195,204`. 로컬 FAIL 34/52/2 |
| 5 | 새 빌드 산출물 전체에 Pages 가드를 돌리는 시험 추가 | **없음** | 지금은 SECRET_PATTERNS만(`web_app_reuse_node_test.js:442`) |
| 6 | 가격 비공개: `public_price_boundary.py` AUDITED_ROUTES를 web_app으로, `test_public_price_boundary.py` 맞춤 | **부분** | `public_price_boundary.py:89`. 새 앱 sentinel 시험은 있음 |
| 7 | NA: 새 화면 NA 시험 유지, 옛 NA 시험 중 화면용은 이식 확인 | **있음**(만든 화면) | 1-a 표 |
| 8 | 클릭 요청 원칙: 데이터층·화면 시험 유지 | **있음** | `web_app_data_layer_browser_test.js`, `web_app_prices_node_test.js` |
| 9 | CSP: `test_app_nav_ia.py`와 `web_app_reuse_node_test.js:205`를 `web_app/index.html` 고정으로. TradingView 허용을 둘지 결정 | **부분** | 1-a 표 |
| 10 | 저장소: 셸 저장 0 시험 유지. "저장된 시세 삭제" 버튼 구현과 시험 | **부분** | `web_app_shell_browser_test.js:92`, `P1_DATA_LAYER.md:416` |
| 11 | PWA·서비스 워커 처리 결정(유지·제거·해제)과 `pwa_*` 시험 처리 | **없음**(문서 없음) | `web_assets/pwa.js:15`, 새 빌드에 없음 |
| 12 | 옛 화면 시험 정리: `ci_*_tests.txt`에서 옛 화면 시험 삭제·이식. 실시간 대조를 고정 벡터로 | **없음** | `P1_DATA_LAYER.md:175,488`, `test_pages_cockpit_build.py:35` |
| 13 | direction guard·FUNCTION_STATUS "구현" 열을 새 앱 기준으로 다시 매김 | **없음** | `FUNCTION_STATUS.md:15` |
| 14 | 매수·매도·주문 없음 시험(새 앱) | **미확인** | 계획 `:34` |
| 15 | 전체 시험·CI 녹색 → 오너 승인 → 병합 → 배포 실행 | **없음** | 기존 사슬 1-d |
| 16 | 실사이트 확인: 처음 쓰는 기기(폰 390폭)에서 메뉴별 공개 자료, 첫 화면 시간·전송량, 가격 요청 0(클릭 전), 저장 0, CSP 오류 0, 비공개 칸 "준비 중" | **미확인**(절차 문서 없음) | DC-22, `FUNCTION_STATUS.md:107` |
| 17 | 기존 기기 저장분 안내(옛 IndexedDB 시세는 수동 삭제만) | **부분** | DC-18 |
