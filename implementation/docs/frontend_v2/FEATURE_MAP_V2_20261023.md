# 새 프론트엔드 기능 대응표 (B-4) — 2026-10-23

작성: 2026-10-23 12:30 UTC / 21:30 KST. 담당: 하위 작업자 B-4. 코드 변경 없음(이 문서 1개만 추가).

기준:

- 현재 웹앱: canonical `claude/investment-system-top500-validation-alrugm` @ `99b99de4` (#388 병합, #387·#389 포함). 화면 코드 `implementation/src/investment_system/product/web_assets/`(아래 `WA/`), 빌드 `implementation/tools/build_pages_cockpit.py`.
- 새 화면 초안: `origin/claude/frontend-v2-p0` @ `ea56a748` (PR #385). `docs/frontend_v2/FRONTEND_V2_PLAN.md`(아래 `PLAN`), `product/web_app/*`(아래 `V2/`). P0는 뼈대다. 모든 절이 "연결 전"이다.
- 시안: Claude 아티팩트 "투자시스템 화면 시안 (손그림 칠판)" https://claude.ai/artifact/44Gm4mhXzXUDTm7svbAvGs, 판 `1792560465-a9fc`. 이 작업에서 Artifact 도구로 18개 보드 원본을 모두 읽었다(§4).
- 참고 문서: `PRODUCT_FEATURE_MAP_20261018.md`, `PRODUCT_FRONTEND_REDESIGN_20261018.md`, `FRONTEND_INTERACTION_CONTRACT_20261019.md`(조작 목록 S·H·L·C·E·W·F·T·M·N·P·R·B·G 번호), `FRONTEND_DATA_CONTRACT.md`.

소유자 결정(2026-10-23, B-4 지시):

- 화면 층만 시안대로 다시 쓴다.
- 계산·저장·자료·가드 모듈은 그대로 재사용한다. 기존 계약 시험도 유지한다.
- 새 화면은 별도 경로로 게시한다.
- 기본 화면 전환 조건은 세 가지다. 이 표 100%(빠진 기능 0), 새 화면 시험 통과, 소유자 승인.
- 옛 화면은 2주간 대체 경로로 남긴다.
- TARGET v1 작업이 새 화면보다 우선이다.

상태 뜻:

| 상태 | 뜻 |
| --- | --- |
| MAPPED | 시안 보드 또는 V2 경로(메뉴 0~n+1·세부 화면 7개)에 이 기능의 자리가 있다. 구현됐다는 뜻은 아니다. P0는 모두 "연결 전"이다. |
| MISSING_IN_DRAFT | 현재 기능인데 시안과 V2 어디에도 자리가 없다. 오늘 전환하면 사라진다. |
| NEEDS_OWNER_DECISION | 자리는 있을 수 있다. 다만 시안·V2가 현재 보호 규칙이나 기능과 충돌하거나, 빠뜨린 것이 의도인지 소유자가 정해야 한다. 커버리지에서는 미확보로 센다. |
| DRAFT_ONLY_NEW | 시안에만 있는 새 기능이다. 현재 기능이 아니므로 커버리지 분모에 넣지 않는다. |

---

## 0. 결론 먼저

- **커버리지(자리 기준): 현재 기능 108개 중 MAPPED 95개 = 88.0%.** 미확보 13개 = MISSING_IN_DRAFT 7 + NEEDS_OWNER_DECISION 6. DRAFT_ONLY_NEW 11개는 분모에서 뺐다. 집계는 §3-9에 있고, 표 행을 그대로 세면 같은 값이 나온다.
- **연결 기준 커버리지는 0%다.** V2 P0의 모든 절이 "연결 전"이고 실제 자료·저장·요청이 하나도 연결되지 않았다. 그래서 오늘 기본 화면을 바꾸면 사실상 **전부** 사라진다(§5). 자리까지 없는 13개는 §5-1에 따로 적었다.
- **계획 문서와 이번 결정이 서로 다르다(소유자 확인 필요).**
  - `PLAN` §0·§1은 "브라우저 코드 전부 새로 작성(계산·연결 모듈 포함)", "한 번에 전환, 그때 옛 화면 삭제"다.
  - 이번 결정은 "화면 층만 재작성, 계산·저장·자료·가드 재사용, 별도 경로 게시, 옛 화면 2주 유지"다.
  - `V2` 개발 빌드(`tools/build_web_app.py`, 브랜치 파일 17~30행)는 `web_assets`의 .js/.css/.html 파일을 **모두 지운다**. 계산·저장 모듈(`qgv-v2.js`, `price-store.js`, `target-v1-builder.js` 등)과 `research.html`·`network.html`·`manifest.json`도 함께 지운다. 이번 결정대로라면 빌드가 이 모듈들을 남기고 새 화면이 불러 써야 한다.
- 시안 확보: 원본 아티팩트의 **18개 보드(PC 9 + 모바일 9) 원본을 모두 읽었다.** 18쪽 PDF 파일 자체는 저장소에 없다. 소유자 Drive에 `투자시스템 화면 시안 (손그림 칠판) (1).pdf`(13,568,024 bytes, 2026-10-21 10:18 UTC 생성)가 있다. 내용과 쪽수는 열어 보지 않았다. 자세한 내용은 §4.

---

## 1. 보호 규칙 (새 화면이 그대로 지켜야 하는 것)

표의 "규칙" 칸은 아래 번호를 쓴다. 근거는 canonical `99b99de4`의 file:line이다.

| 번호 | 규칙 | 근거 (file:line) | 새 화면에서 주의할 점 |
| --- | --- | --- | --- |
| R1 | **클릭 요청만.** 화면을 열 때 가격 요청 0건. Worker·시트 가격 요청은 사용자의 버튼으로만 한다. | `WA/price-store.js:8-11`(CLICK-ONLY), `WA/virtual-trading-runner.js:6-8`, `WA/worker-quote-fallback.js:3`, `WA/private-history.js:1`, `WA/forward-validation.js:2-3`, `docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md:532`(GSQ-024 기기 V: 자동 요청 0건) | `PLAN` §2-3에 있다. 시안 1.1 "수익률 기간", 4.2 "주가 반영", 스탯창 변동성·낙폭은 가격이 있어야 한다. 버튼 없이 자동으로 계산하면 안 된다. |
| R2 | **가격·가격 파생값·보유·거래·시트 ID·토큰·환율은 기기 RAM, 사용자 개인 시트, 기기 저장소(허용 항목)에만 둔다.** 서버·공개 파일·로그에는 넣지 않는다. | `implementation/tools/pages_artifact_guard.py:196-216`(SENSITIVE_KEYS·SECRET_PATTERNS), `WA/price-store.js:10-12`, `WA/virtual-ledger-sheets.js:6-7`, `WA/device-actual.js:1`, `WA/google-sheet-quotes.js:1`, `WA/google-sheet-setup.js:1`, `WA/private-trades.js:1`, `WA/device-valuation.js:3`, `GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md:526`(GSQ-024에서도 GSQ-010 유지) | `PLAN` §2-1에 있다. 시안의 "로그인 계정에 저장"(Technical·News·Prompt 보드)은 아직 없는 백엔드라 결정 대기다. |
| R3 | **NA는 0으로 채우지 않는다.** 사유 코드를 보이고 정렬에서는 맨 뒤에 둔다. | `WA/qgv-scores.js:8,50`, `WA/qgv-v2.js:4,86`, `WA/stat-radar.js:59`, `WA/leaderboard-screen.js:37,96-98`(V 0/5, 채우지 않음), `WA/virtual-trading-compare.js:6`, `WA/chart-bars.js:4`, `WA/table-sort.js:3`, `WA/universe-company.js:9` | `PLAN` §2-2에 있다. 시안 QGV 표의 "NA는 이유를 눌러서 봄 · 0으로 채우지 않음"과 같다. |
| R4 | **매수·매도·주문·이체 기능과 지시 문구가 없다.** 허용 문구는 부정형("매수·매도 지시 아님", "주문 기능 없음")뿐이다. | `WA/target-v1-builder.js:19`, `WA/chart-workbench.js:1`, `WA/virtual-trading.js:3`, `WA/virtual-ledger-sheets.js:8`, `WA/app.js:195`(설정 배지 "주문 기능 없음"), 시험 `tools/home_search_result_browser_test.js:73`, `tools/chart_workbench_browser_test.js:153`, `tools/judgement_labels_node_test.js:55`, `tools/design_canvas_browser_test.js:13` | `PLAN` §2-6에 있다. 시안 Portfolio 보드에도 "매수·매도 지시 아님"이 있다. |
| R5 | **공식이 아닌 확률·승률·점수 표현이 없다.** 기술 패턴과 매크로 국면에는 확률이 없다. 매크로 근거선은 "v0 · 미검증"이다. | `WA/pattern-engine.js:5-6`, `tools/chart_workbench_browser_test.js:153`(확률·승률·점수·신뢰도 문구 금지), `WA/macro-cycle-ring.js:3-5`(미정·소유자 결정), `WA/macro-evidence.js:1-4` | 시안 2.1 시나리오 확률(30/50/20%), 2.2 "일치도 0.81", 3.2·3.3 조정 확률이 이 규칙과 부딪친다(§3 NEEDS_OWNER_DECISION). |
| R6 | **calc_version 관문.** 다른 calc_version 행은 점수를 매기지 않는다. 전진검증 평가 구간은 이어 붙이지 않는다. 숫자 검증은 같은 calc_version에서만 유효하다. | `WA/qgv-scores.js:50-51,67-71`, `WA/leaderboard-screen.js:161`, `WA/forward-validation.js:117,219`, `WA/target-v1-builder.js:290-292`, `WA/target-v1-screen.js:105,165`(NUMBER_CHECK_CALC_VERSION_MISMATCH) | 재사용 모듈이 이미 처리한다. 화면은 사유를 감추지 말아야 한다. |
| R7 | **V n/5 표시**와 **V_FACTORS_V3_V4_MISSING 확정 차단**. V3·V4가 빠진 V로 고른 종목은 초안에만 둘 수 있고 확정할 수 없다. | `WA/leaderboard-screen.js:96-99`, `WA/target-v1-builder.js:70,73,303`, `WA/target-v1-screen.js:23,28-29` | 시안 QGV 표에는 n/5 칸이 없다. 리더보드와 TARGET 후보 표에 넣어야 한다. |
| R8 | **number_check 관문.** 같은 calc_version의 10개 기업 숫자 검증을 통과하기 전에는 TARGET v1을 확정하지 못한다. | `WA/target-v1-builder.js:290-292,318`, `WA/target-v1-screen.js:105,142,165`, `WA/target-v1-config-defaults.js:2` | 세부 화면 `#/detail/target-v1`에 그대로 둔다. |
| R9 | **CSP.** 인라인 스크립트·스타일이 없다. 외부 원본은 구글 로그인·시트·Worker·TradingView 틀만 허용한다. | `WA/index.html:5`, `V2/index.html:5`(같은 CSP), `V2/core.js:14-15`(CSSOM만), `tools/web_app_shell_browser_test.js:36`(V2: style 속성 0) | V2는 이미 지킨다. 시안 원본은 Google Fonts `<link>`와 인라인 style을 쓴다. 그대로 옮기면 안 된다(V2는 글꼴을 자체 호스팅). |
| R10 | **Pages 자산 고정 해시와 한도.** 파일별 sha256, 파일당 2 MiB, 192개, 아카이브 8 MiB. | `tools/pages_artifact_guard.py:47`(APPROVED_SHA256), `:184-193`(한도), `:297,306,381`(해시 검사) | `PLAN` §2-5에 있다. 별도 경로 게시라면 옛 파일과 새 파일이 함께 올라간다. 192개와 8 MiB 한도 안에 드는지 먼저 재야 한다(현재 게시 138~141개). |
| R11 | **IEX 출처 문구.** 중앙 V를 보일 때 "Data provided for free by IEX. By accessing or using IEX Historical Data, you agree to the IEX Historical Data Terms of Use."(약관 링크)와 "IEX 마지막 체결가 기준(공식 종가 아님)"을 함께 보인다. | `GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md:530` | **규칙 있음 / 코드 없음(후속 PR 예정).** `web_assets`에서 IEX는 시세 종목 목록의 티커 문자열(`WA/google-sheet-quotes.js:32`)뿐이다. 중앙 V 읽기 경로도 아직 없다(Main 확인). |
| R12 | **"임시 V" 표시.** TARGET v1 확정까지 중앙 V가 게시되지 않으면 임시 경로 V로 하고 "임시 V"를 남긴다. | `GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md:534` | **규칙 있음 / 코드 없음(후속 PR 예정).** `web_assets` 검색 0건. |
| R13 | **기기 V는 공식값이 아니다.** 공식 순위에 섞지 않는다. 개인 설정은 공식 순위를 다시 매기지 않는다. | `GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md:532`, `WA/leaderboard-screen.js:2-3,39`, `WA/device-profiles.js:1,198` | 시안 1.2 "공식 점수는 그대로"와 같다. |
| R14 | **IA-7 화면 상태 키.** 관심·메모·뉴스는 Issuer(`sec:`+CIK10), 차트 그림은 Listing(Universe 코드), `company_id`는 TARGET 별칭. TARGET v0(19)와 관심·메모·차트를 떼어 놓는다. | `docs/PRODUCT_IA_ONTOLOGY_CHECK_20261018.md:397`. 현재 코드: 관심은 `company_id` 19개(`WA/watchlist.js:3`, `WA/app.js:3,58`), 차트 그림은 listing symbol(`WA/chart-workbench.js:199`), 가격 차트 종목은 19개만(`WA/private-history.js:9`), 시트 거래 종목도 19개만(`WA/private-trades.js:4`). | 떼어 놓는 작업은 `origin/claude/target-v0-decoupling`(미병합, 이번 작업에서 건드리지 않음)에 있다. 새 화면은 이 키를 써야 한다. 시안의 ★ 즐겨찾기는 Universe 504 기업 전체가 대상이다. |
| R15 | **"사용자 작성" 층을 분리한다.** 노트·시나리오·내 위치는 공식 이력과 판정에 섞지 않고 늘 "사용자 작성 / 사용자 추정 · 공식 판정 아님"으로 표시한다. | `WA/chart-workbench.js:7-9`, `WA/pattern-history.js:4-5`, `WA/macro-cycle-ring.js:6-9` | 시안 보라 펜·"내 위치 저장"과 맞는다. |
| R16 | **추가만(append-only), 소급 채움 없음.** | `WA/pattern-history.js:3`, `WA/virtual-ledger-sheets.js:2-5`, `WA/virtual-trading-v-history.js:7-9`, `WA/macro-cycle-ring.js:6-9`, `WA/price-store.js:3-4` | 시안 Lab "기록은 추가만", 5.3 "장부는 추가만"과 같다. |
| R17 | **금액 숨김이 기본값이다.** 화면과 내보내기가 같은 함수를 쓴다. | `WA/daily-report.js:4` | 시안 "금액은 내 기기에만"과 같다. |
| R18 | **TradingView는 켤 때만, 보기만 한다.** 값을 읽어 오지 않는다. | `WA/tradingview-widgets.js:1-4` | 시안에는 TradingView가 없다. CSP의 frame-src는 V2에도 남아 있다. |
| R19 | **공개 자료 새로고침은 전부 성공했을 때만 바꾼다.** 실패하면 옛 값과 기준 시각을 보이고, 보던 화면 상태를 유지한다. | `WA/data-refresh.js:9-10,17-18` | V2는 머리말의 새로고침 버튼을 없애고 세부 화면 `data-status`로 옮겼다. |
| R20 | **가격 시각은 둘(읽은 시각과 가격 자체 시각)이고 서로 대신하지 않는다.** | `WA/price-time.js:1-5` | 시안에는 "자료 기준일" 칸만 있다. |
| R21 | **기기 백업에서 시세·토큰·시트 ID·Worker 주소를 뺀다.** 사용자 그림은 선택해야만 포함한다. | `WA/app.js:200`, `WA/device-backup.js:1-5`, `WA/private-subset-view.js:9` | 시안 모바일 트리 "설정 · 로그인 · 내보내기"가 자리다. |
| R22 | **사용자 그림에는 사용자 좌표와 글만 저장한다.** 가격 시계열·OHLC·공급자 필드가 있으면 무효다. | `WA/chart-workbench.js:12-15,194-198` | — |
| R23 | **검색 순서는 추천 순위가 아니다.** | `WA/home-screen.js:4`, `WA/entity-search.js:1` | 시안·V2 바닥글에 같은 문구가 있다(`V2/shell.js:43`). |
| R24 | **시안 숫자는 예시다.** 새 화면에는 실제 공개 자료, 기기 RAM 값, NA와 사유만 보인다. | `PLAN` §1, `V2/parts.js:2-3` | 시안 보드 머리마다 "숫자는 모두 예시"가 있다. |

---

## 2. 현재 화면·경로 목록 (요약)

현재 메뉴와 경로 표는 `WA/app-shell.js:16-63`에 있고, 라우터는 `WA/app.js:922-1010`(`routes` 950행)이다.

| 메뉴 | 현재 경로 | V2 경로 |
| --- | --- | --- |
| 0 홈 | `#home`, `#brief` | `#/` |
| 기업 | `#company/<id>`, `#analysis/<id>/<tab>`, `#entity/<key>` | `#/company/<코드>` |
| 1 QGV | `#leaderboard`, `#companies`, `#watchlist`, `#profiles`, `#types`, `#lab-13f`, `#thirteenf`, `#tree/qgv`, `#qgv` | `#/qgv` (1.1~1.4) |
| 2 기술 | `#technical[-chart/-state/-execution/-record/-pattern/-notes]`, `#tree/technical` | `#/technical` |
| 3 매크로 | `#macro`, `#macro-cycle/-rotation/-industry/-mine/-chain`, `#tree/macro` | `#/macro` |
| 4 뉴스 | `#news`, `#news-network`, `#tree/news`, `network.html` | `#/news` |
| 5 포트폴리오 | `#portfolio`, `#model`, `#actual`, `#playbook`, `#report/real`, `#report/mock[-set_b/c/d/-compare]`, `#tree/portfolio` | `#/portfolio`, `#/detail/playbook`, `#/detail/virtual-trading`, `#/detail/target-v1` |
| 6 프롬프트 | `#research`, `research.html` | `#/prompts` |
| n | `#system` | `#/tree` |
| n+1 | `#validation[-backtest/-forward]` | `#/lab` |
| 설정 | `#settings` | `#/detail/settings`, `#/detail/data-status`, `#/detail/financials`, `#/detail/sec-cover` |

---

## 3. 기능 대응표

현재 위치는 `WA/` 기준이다. "새 화면"은 시안 보드 이름(PC/모바일)과 V2 경로다. 조작 ID는 `FRONTEND_INTERACTION_CONTRACT_20261019.md` §1의 번호다.

### 3-0. 공통 셸

| # | 기능 | 현재 위치 | 보호 규칙 | 새 화면 (시안 / V2) | 상태 | 비고 |
| --- | --- | --- | --- | --- | --- | --- |
| F01 | 주 메뉴(번호 메뉴, 폰 아래 탭) S1 | `index.html:34`, `app-shell.js:16-63` | — | Main 머리말 메뉴 · 모바일 탭(홈·QGV·포트폴리오·뉴스·전체) / `V2/shell.js:11-33` | MAPPED | V2 셸 시험이 있다. |
| F02 | 전체 메뉴 시트(구조 트리 모양, Esc·포커스 순환) S2 | `index.html:44`, `app-shell.js:211-216` | — | MTree "전체 메뉴" / `V2/shell.js:18-36` drawer | MAPPED | V2 drawer에는 세부 화면 7개도 있다. |
| F03 | 메뉴별 번호 줄(1.1·1.2…) S3 | `app-shell.js:157`(`subNavHtml`) | — | MQGV 위 번호 칩 / V2 절 도장(`parts.js:10`) | MAPPED | 폰에서 현재 절로 줄 맞춤은 다시 만들어야 한다. |
| F04 | 테마(라이트·다크·시스템) S4 | `index.html:49`, `theme-boot.js:3`, `app-shell.js:112` | 기기 저장(가격 없음) | 없음. 시안은 흰 바탕 한 가지, `V2/app.css`에 다크 규칙 0개 | NEEDS_OWNER_DECISION | 다크 모드를 없앨지 결정이 필요하다. |
| F05 | 표시 언어 한국어↔English S5, 설정 `#display-locale` | `index.html:47`, `locale.js:8`, `app.js:196` | 원자료는 번역하지 않음(`locale.js:1`) | 없음. V2는 한국어만 쓴다 | NEEDS_OWNER_DECISION | 영어 화면 계약 시험(`global_language_search`)을 어떻게 할지 정해야 한다. |
| F06 | 자료 새로고침 버튼(머리말, 전부 성공일 때만 교체, 화면 상태 보존) S6 | `data-refresh.js:239`, `app.js:923-926,1327` | R19 | `#/detail/data-status` "자료 상태 · 새로고침" | MAPPED | 모든 화면 머리말에서 세부 화면으로 옮겨진다. 접근 경로를 확인해야 한다. |
| F07 | 전역 검색 콤보박스(모든 화면, `/` 단축키, 한글 조합, ↑↓) S7 | `home-screen.js:2-6`, `index.html:61`, `entity-search.js` | R23 | Main 검색창 / `V2/screen-search.js:7-17`(홈에만) | MAPPED | V2는 홈에만 검색창이 있다. 다른 화면 머리말 검색과 지표·산업 결과(INDUSTRY/MACRO)는 비고로 남긴다. |
| F08 | 입력 중 아래 메뉴 숨김 S8 | `app-shell.js:180-190` | — | 모바일 탭바 / `V2/shell.js:29` | MAPPED | 동작은 다시 만들어야 한다. |
| F09 | 관심 ★ 단추(모든 기업 행·화면) S9 | `app.js:354` | R14(현재 `company_id` 19개) | Main "★ 즐겨찾기 기업", News "★ 즐겨찾기 12곳" | MAPPED | 키를 Issuer로 바꾸는 일은 decoupling 브랜치에서 한다. |
| F10 | PC 표 머리글 정렬(NA 맨 뒤) S10 | `table-sort.js:1-7` | R3 | 시안 표(`.tbl`) | MAPPED | 리더보드는 정렬 상자만 쓴다(G6 정정). |
| F11 | PWA 설치·오프라인 셸(service worker, manifest) G10s | `pwa.js:1-12`, `service-worker.js:1-3`, `offline.html` | 자격 증명·앱 자료는 캐시하지 않음(`pwa.js:1`, `service-worker.js:1`) | 없음. `build_web_app.py`가 `manifest.json`도 지운다 | MISSING_IN_DRAFT | — |
| F12 | 바닥 안내(추천 아님·가격 기기 계산·투자 권유 아님) | `app.js`(홈·설정 배지) | R4·R23 | 시안 바닥글 / `V2/shell.js:43` | MAPPED | — |

### 3-1. 0 홈 · 기업 검색 결과

| # | 기능 | 현재 위치 | 보호 규칙 | 새 화면 (시안 / V2) | 상태 | 비고 |
| --- | --- | --- | --- | --- | --- | --- |
| F13 | 홈 검색 시작 화면 | `app.js:379`, `home-screen.js` | R23 | Main·MMain "어떤 기업을 볼까요?" / `#/` | MAPPED | — |
| F14 | 최근 검색과 지우기 H1 | `home-screen.js:24,324` | 기기 저장(가격 없음) | Main "최근 →" 칩 / `#/` "최근 · ★" pending | MAPPED | — |
| F15 | 투자자 이야기(버핏 서한 인용, 다른 이야기, 출처 시트) H2·H3 | `home-quotes.js:1-5`, `home-screen.js:339` | 원문 대조 인용만, 추천 아님 | 없음 | MISSING_IN_DRAFT | — |
| F16 | 내 관심 기업 소식(홈) H4 | `home-screen.js:275` | R14 | 검색 결과 "4. 이 기업 소식" · News "★ 즐겨찾기만" | MAPPED | 홈의 묶음 소식이 기업별·뉴스 메뉴로 나뉜다. |
| F17 | 오늘의 투자 화면 `#brief`(통합 판단 카드 "매수·매도 지시 아님", Attention, 일일보고서 칩, 플레이북 오늘 요약, TARGET 버전) | `app.js:380-392,971,994`, `playbook-screen.js`(`todayHtml`) | R4 | 없음. 시안 Main은 검색만 있다 | MISSING_IN_DRAFT | 5.2 일일 보고로 합칠지 정해야 한다. |
| F18 | TradingView 시세 띠(ticker tape) | `app.js:994`, `tradingview-widgets.js:1-4` | R18 | 없음 | MISSING_IN_DRAFT | — |
| F19 | 기업 요약 화면 `#company`(QGV 카드, 분류 칩, 보유, 가격 차트, 공시) | `app.js:476`, `company-screen.js:1-10` | R3·R13 | Main 검색 결과 다섯 칸 / `#/company/<코드>`(`screen-search.js:18-29`) | MAPPED | — |
| F20 | 기업 분석 탭 `#analysis`(요약·요인·가치·공시…, ←/→ 순환, 해시 반영) E1 | `app.js:491,977`, `company-screen.js:241` | R3·R6 | 검색 결과 카드 "→ 자세히" + `#/detail/financials` | MAPPED | — |
| F21 | 커버리지 펼침(다시 그려도 열림 유지) E2 | `app.js`(repaintScores) | R3 | 1.4 예시 값 · `#/detail/financials` | MAPPED | — |
| F22 | Universe504 기업 화면(TARGET 밖 기업, 공개 QGV v2 행) | `universe-company.js:1-9`, `app.js:974` | R3·R6 | `#/company/<코드>` | MAPPED | — |
| F23 | 산업(SIC 업종군)·전략 테마 칩 | `classification-screens.js:1-5`, `company-screen.js:3` | R3 | 검색 결과 머리 "회사명 · SIC · 유형" | MAPPED | — |
| F24 | 기업 화면 내 보유(이 기업 보유·평단) | `company-screen.js:192`, `app.js:975` | R2·R17 | 검색 결과 "5. 내 포트폴리오에서" | MAPPED | — |
| F25 | 개별 기업 가격 일봉 불러오기 + 기간 + 이동평균 + 내 매매 표시 E5 | `private-history.js:1,128,219`, `private-trades.js:1-4`, `app.js:996` | R1·R2·R14(19개만)·R20 | 검색 결과 "2. 기술적 분석" 카드, 2.1 | MAPPED | — |
| F26 | 기업 화면 가격 저장(Prices_M 월말가 읽기·받기 버튼) | `price-store.js:489`(`mountCompany`), `app.js:998` | R1·R2·R16 | `#/detail/settings`(가격 저장) | MAPPED | — |
| F27 | TradingView 미니 차트·고급 차트 켜기 E6 | `tradingview-widgets.js:4,56`, `app.js:987,995` | R18 | 없음 | MISSING_IN_DRAFT | 시안은 자체 차트만 쓴다. |
| F28 | 목록으로 돌아가기(연 목록·스크롤 복원) E7·L9 | `app.js:954-962`, `company-screen.js` | — | 시안 "← 검색" / `V2/parts.js:8` | MAPPED | 리더보드 스크롤 복원은 다시 만들어야 한다. |
| F29 | 엔터티 화면 `#entity`(산업·매크로 지표 상세, 검색 결과에서 연결) | `app.js:260` | — | 없음 | MISSING_IN_DRAFT | 검색이 기업만 다루면 사라진다. |
| F30 | 기업 로고(번들 PNG, 없으면 이니셜) | `company-logos.js:1-5` | 외부 로고 요청 0 | 시안에는 로고가 없다 | NEEDS_OWNER_DECISION | 설정의 로고 표시 토글(G8s)도 같이 정해야 한다. |

### 3-2. 1 QGV

| # | 기능 | 현재 위치 | 보호 규칙 | 새 화면 (시안 / V2) | 상태 | 비고 |
| --- | --- | --- | --- | --- | --- | --- |
| F31 | 리더보드 표(Universe504, 공식 QGV v2 순위) | `leaderboard-screen.js:1-13`, `app.js:516-519` | R3·R6·R13 | QGV 1.1 / `#/qgv` 1-1 | MAPPED | — |
| F32 | 리더보드 검색 L1 | `app.js:397` `#leader-query` | — | 1.1 | MAPPED | 시안에는 검색칸이 없다. |
| F33 | 관심기업만·그룹·TARGET만 L2 | `app.js:397,647` | R14 | 1.1 | MAPPED | "TARGET만"은 TARGET v0 결합이다(R14). |
| F34 | SIC 업종군·SIC 2자리·4자리·기업 유형 필터와 SIC 열 L14 | `leaderboard-screen.js:13,63-93,282` | R3(분류 없음=NA) | 1.1 "SIC · 기업 유형" 칩 | MAPPED | — |
| F35 | 정렬·방향·기본 정렬 L3 | `app.js:623-636`, `leaderboard-screen.js:32` | R3 | 1.1 | MAPPED | — |
| F36 | 보기 탭(기본·내 프로필·내 기기) L4 | `leaderboard-screen.js:220` | R13 | 1.1, 1.2 "바꾸기 전 ↔ 후" | MAPPED | — |
| F37 | 프리셋 칩 + 가치 함정 관문(RAM) L5 | `leaderboard-screen.js:223-225` | R13, RAM만 | 1.2 공격형·균형형·수비형 | MAPPED | 시안에도 "세 프리셋 수치 미정"이 있다. |
| F38 | 탐색 필터(공식 순위·QG 참고·일부 축·자료 확인) L7 | `leaderboard-screen.js:247` | R3·R13 | 1.1 | MAPPED | — |
| F39 | 폰 행 상세 펼침 L8 | `leaderboard-screen.js:15,308` | — | MQGV 1.1 행 | MAPPED | — |
| F40 | V 요인 수 n/5 표시 | `leaderboard-screen.js:96-99` | R7 | 1.1 표 | MAPPED | 시안 표에는 n/5 칸이 없다. 넣어야 한다. |
| F41 | 내 기기 Universe 읽기·지우기, 시총 순위(M3) L10 | `private-subset-view.js:1-9,61`, `app.js:969` | R1·R2·R21 | 1.1 + `#/detail/settings` | MAPPED | — |
| F42 | V 산출 현황·이 기기 L12 | `v-coverage.js:1-6`, `v-coverage.js:59` | R3·R13 | 1.1 또는 `#/detail/data-status` | MAPPED | 자리를 정해야 한다(시안에 없음). |
| F43 | 모델 포트폴리오 N10·N15·N20 참고 L11 | `leaderboard-screen.js:330` | R13 | Portfolio 5.1 "모델 적합 포트폴리오" | MAPPED | — |
| F44 | 2단계 가중치 편집(축·요인 슬라이더·숫자·잠금·저장) W1 | `device-profiles.js:1,140,247`, `app.js:561,1001` | R13(공식 불변) | QGV 1.2 슬라이더·잠금·"내 설정 저장" | MAPPED | — |
| F45 | 기업 유형 커스텀 `#types` W2 | `device-profiles.js:83`, `app.js:562,1005` | 기기 저장 사본 | 1.2 | MAPPED | 시안 1.2에는 유형 편집이 없다. 1.2 안에 둔다. |
| F46 | 13F 가중치 연구(준비 중 안내) | `app-shell.js`(`pendingHtml('lab-13f')`) | 공식 기본값을 자동으로 바꾸지 않음 | QGV 1.3 ①~④ | MAPPED | — |
| F47 | 투자자 13F 보유(투자자별·종목별·겹침, 유형 필터, 투자자 ★, 전체 보유 100개씩) F1~F5 | `app.js:605`, `thirteenf-quarter.js:1-4` | 단가·거래 없음(`thirteenf-quarter.js:1`) | QGV 1.3 / `#/qgv` 1-3 "기관 보유 변화" | MAPPED | 시안 1.3은 가중치 연구만 그렸다. 보유 조회는 V2 문구에만 있다. |
| F48 | 1.4 QGV 구조 트리 + 공개 자료 예시 값 | `ia-screens.js:43-80` | R3·R24 | QGV 1.4 트리 + 예시 값 | MAPPED | — |
| F49 | 스탯창(Q·G·V + 후보 가격 축 3개, 비교군, 보조 축 토글, 구성원 목록) E3·E4 | `stat-radar.js:1-5,59,385,416` | R1·R3(꼭짓점 없음), 후보 축 표시 | QGV 1.4 스탯창 | MAPPED | 시안 축 "변동성·낙폭·이익률 안정성"과 현재 후보 축 "가격 안정성·낙폭 방어력·상대 강도"가 다르다(이름만 맞추면 된다). |
| F50 | QGV 허브 `#qgv` | `app.js:538` | — | `#/qgv` | MAPPED | — |
| F51 | 기업 목록 `#companies`(검색·관심만·그룹·정렬·30개씩 더) C1·C2 | `app.js:414-415`, `watchlist.js:3-4` | R14 | 없음. 리더보드와 검색 결과만 있다 | MISSING_IN_DRAFT | 리더보드 필터로 합칠 수 있다. 소유자 확인이 필요하다. |
| F52 | 관심 기업 화면 `#watchlist`(그룹·정렬, 그룹 만들기·이름 바꾸기·삭제·구성원) C3·C4 | `app.js:413,418` | R14 | News 4.1 "개인 설정 · ★ 즐겨찾기 · 그룹" | MAPPED | 시안은 그룹을 4.1 개인 설정에 둔다. |
| F53 | 관심 목록 내보내기·가져오기 C5 | `app.js:418` | R21 | `#/detail/settings` | MAPPED | — |

### 3-3. 2 기술적 분석

| # | 기능 | 현재 위치 | 보호 규칙 | 새 화면 (시안 / V2) | 상태 | 비고 |
| --- | --- | --- | --- | --- | --- | --- |
| F54 | 종목 선택(TARGET 19개)과 일봉 불러오기·기간·이동평균 T2·T3 | `private-history.js:9,219`, `app.js:984-999` | R1·R2·R14·R20 | Technical 2.1 / `#/technical` 2-1 | MAPPED | 시안은 검색한 아무 기업이나 대상이다(19개 제한이 R14 과제). |
| F55 | 지표 카드(모델·연구 구분) T4 | `technical-cards.js:1-3,34` | R3, RESEARCH_DISPLAY_ONLY | 2.1 지표 칩 | MAPPED | — |
| F56 | 차트 작업대(표시 설정, 지표 묶음, 주봉) | `chart-workbench.js:1-5,22` | R2(설정에 가격 없음) | 2.1 | MAPPED | — |
| F57 | 패턴 감지(공식 규칙)와 공식 감지 이력(RAM, 추가만) | `pattern-engine.js:1-8`, `pattern-history.js:1-7`, `chart-workbench.js:5-6` | R5·R15·R16 | 2.2 패턴 카드 | NEEDS_OWNER_DECISION | 시안은 "일치도 0.81"과 "정도 = 일치도 문턱값"이다. 엔진은 점수·백분율을 내지 않는다(R5). 표시 방식을 정해야 한다. |
| F58 | 패턴 사용자 설정 실행(정도 설정, 공식 이력 밖) | `pattern-engine.js:8`, `chart-workbench.js` | R15 | 2.1·2.2 정도 칩(민감·보통·둔감) | MAPPED | 시안의 "민감·보통·둔감" 묶음 값은 정해지지 않았다. |
| F59 | 차트 위 내 노트(펜·추세선·수평선·구간 상자·메모, 되돌리기 30) | `chart-workbench.js:180-199`(NOTE_KINDS 186, UNDO 188) | R2·R14(Listing)·R15·R22 | 2.3 도구 줄(펜·추세선·수평선·구간 상자·메모·지우개·되돌리기) | MAPPED | — |
| F60 | 시나리오(방향·수준·조건·무효화) | `chart-workbench.js:197`(SCENARIO_FIELDS) | R5·R15·R22 | 2.1 시나리오 선 | NEEDS_OWNER_DECISION | 시안은 "상승 30% · 기본 50% · 하락 20%"이다. 현재 규칙은 확률 표시 금지다(R5, `chart_workbench_browser_test.js:153`). |
| F61 | 사용자 그림 내보내기·가져오기(파일, 중복 없이 합치기) | `chart-workbench.js:12-15,962` | R21·R22 | 2.3 / `#/detail/settings` | MAPPED | — |
| F62 | 스윙 보기(그림 없는 시나리오 칸) | `chart-workbench.js`(swing mode), `tools/chart_workbench_browser_test.js:149` | R5 | 2.1 | MAPPED | — |
| F63 | 기술 화면 절 탭(차트·상태·실행·기록) T1 | `app.js:928-937,992` | — | V2 절 2-1~2-4 | MAPPED | — |
| F64 | 2.4 기술 구조 트리 | `ia-screens.js`(`tree/technical`) | R24 | 2.4 트리 + 예시 값 | MAPPED | — |

### 3-4. 3 매크로

| # | 기능 | 현재 위치 | 보호 규칙 | 새 화면 (시안 / V2) | 상태 | 비고 |
| --- | --- | --- | --- | --- | --- | --- |
| F65 | 매크로 경고등 5개(공개 3개 + 기기 계산 2개, 불러오기 버튼, 이전 기준 펼침) M1·M2 | `macro-lights.js:1-6,259-261` | R1·R2, 매도 판단에 쓰지 않음(`macro-lights.js:6`) | 3.1 "기존 매크로 경고등 5개 · 참고 모드 유지", 3.6 트리 | MAPPED | — |
| F66 | 순환 국면 링 3개(경기·주식시장·SIC 산업) | `macro-cycle-ring.js:1-5`, `app.js:1007` | R5(위치 미정) | 3.1 위치 그래프, 3.3 산업 사이클 | MAPPED | 시안은 위치 점과 확률을 그린다. 현재 "미정(소유자 결정)" 상태를 유지해야 한다. |
| F67 | 내가 고른 위치(사용자 추정 이력, 추가만, 내보내기) M6 | `macro-cycle-ring.js:6-9,19,173` | R15·R16·R21 | 3.4 "내 위치 저장" | MAPPED | — |
| F68 | 근거선 그래프(MEV-1 13계열, 경기·시장·산업 탭, 재구성 층 끔) | `macro-evidence.js:1-6` | R5("v0 · 미검증") | 3.1 근거 세로선 ①~⑨ · "근거 더 보기(전체 54)" | MAPPED | — |
| F69 | 상태판 "현재 국면" 자리표시 M8, 국면 이력·영향 전달 NA 카드 M9 | `app.js:599`, `screen-detail.js:1-4` | R3·R5 | 3.1 | MAPPED | — |
| F70 | 3.2 순환매 자리표시(NOT_AVAILABLE) | `app-shell.js:31`(pending) | R5 | 3.2 상향·유지·하향 조건과 확률 | NEEDS_OWNER_DECISION | 시안은 확률 35/50/15%다. 국면·확률은 Lab 검증 전 "미산출"이다(R5). |
| F71 | 3.5 연쇄 효과 지도 자리표시 | `app-shell.js:32`(pending) | — | 3.5 예 1·예 2 | MAPPED | 양쪽 모두 엔진이 없다. |
| F72 | 3.6 매크로 구조 트리 | `ia-screens.js`(`tree/macro`) | R24 | 3.6 | MAPPED | — |

### 3-5. 4 뉴스

| # | 기능 | 현재 위치 | 보호 규칙 | 새 화면 (시안 / V2) | 상태 | 비고 |
| --- | --- | --- | --- | --- | --- | --- |
| F73 | 공시·뉴스 한 목록(SEC 8-K·DART·GDELT·IR, 공시·확정과 뉴스·신호 구분, GDELT 출처 표시) | `news-signals.js:1-5`, `sec-disclosures.js:1-3`, `dart-disclosures.js:1-3` | 점수를 바꾸지 않음, textContent만 | 4.2 / `#/news` 4-2 | MAPPED | 시안의 5줄 요약(Q·G 예상·주가 반영)은 N03 참조. |
| F74 | 뉴스 필터 4개 + 초기화(탭 단위 sessionStorage) N4 | `news-signals.js:155,219` | — | 4.2 "★ 즐겨찾기만 · 보유 기업 전체" | MAPPED | — |
| F75 | 근거 보기(발표·수집 시각) N5 | `news-signals.js:231` | R20 | 4.2 | MAPPED | — |
| F76 | 관계망 화면(`network.html`: 확대·축소, 관계 필터 Fact/추론, 선택 기업 집중) N1·N6 | `network-bridge.js:1-4`, `app.js:525` | 관계 계산 없음 | 4.1 관계망(확인 ━, 추론 ╍) | MAPPED | `build_web_app.py`가 `network.html`을 지운다. 4.1에서 다시 만들어야 한다. |
| F77 | 뉴스 범위 선택·범위 칩(옛 `D.news`, 늘 빈 목록) N2·N3 | `app.js:525` | — | 4.2 | MAPPED | 현재도 자리표시뿐이다(G7). |
| F78 | 4.3 뉴스 구조 트리 | `ia-screens.js`(`tree/news`) | R24 | 4.3 | MAPPED | — |
| F79 | SEC 보고 관측(sec-reported, 고정 안내) | `sec-reported.js:1`, `app.js:742` | 가격 없음 | `#/detail/sec-cover` | MAPPED | — |

### 3-6. 5 포트폴리오 · 보고

| # | 기능 | 현재 위치 | 보호 규칙 | 새 화면 (시안 / V2) | 상태 | 비고 |
| --- | --- | --- | --- | --- | --- | --- |
| F80 | 포트폴리오 S03(배지, 필수 그림 3개, 테마 TARGET 대 ACTUAL 표, 업종 구성, 테마 집중 경고 >40%) | `portfolio-screen.js:1-4`, `app.js:497-511`, `classification-screens.js:3-4` | R2·R3, TARGET을 ACTUAL로 쓰지 않음 | 5.1 세 가지 포트폴리오 | MAPPED | — |
| F81 | 실제 보유 입력 `#actual`(IndexedDB 저장·내보내기·가져오기·삭제, API 설정) P1 | `device-actual.js:1-13,541`, `app.js:54,972` | R2·R17·R21 | 5.1 "내 포트폴리오 · 실제 보유 (내 기기 / 비공개 시트)" | MAPPED | — |
| F82 | 시트 보유 캡처 + 개인 AI 변환 프롬프트(Holdings 탭) P3 | `holdings-capture.js:1-13`, `holdings-capture-view.js:1-2,183` | R1·R2(행·가격·손익 RAM) | 5.4 트리 "보유 캡처 · 비공개 시트", 5.1 | MAPPED | — |
| F83 | Worker 시세 채우기(시트 #N/A → Worker 종가, RAM) P2 | `worker-quote-fallback.js:1-3,173` | R1·R2·R20 | 5.1 | MAPPED | — |
| F84 | 모델 포트폴리오 화면 `#model`(생성기 없음 안내) P8 | `app.js:563-578` | R13 | 5.1 "모델 적합 포트폴리오" | MAPPED | — |
| F85 | 플레이북(논지·근거·결정·보류, 프롬프트 복사) P4 | `playbook-screen.js:1-5,54,111` | R2·R4·R16 | `#/detail/playbook` | MAPPED | — |
| F86 | TARGET v1 빌더(후보 30 → 최종 15, 카드 동의·반대·모름, R-B·R-C, 확정 관문, T-PRICE) P5 | `target-v1-builder.js:1-19`, `target-v1-screen.js:1-34,105,165` | R1·R2·R4·R6·R7·R8·R12 | `#/detail/target-v1` | MAPPED | 우선 작업(TARGET v1). R12 "임시 V"는 코드가 없다. |
| F87 | 투자 일일보고서 `#report/real`(템플릿 v1 내보내기, 보고 불가 → 프롬프트, 답변 저장·검토) P6 | `daily-report.js:1-7,218-231,524`, `app.js:752-763` | R4(과장 문구 금지 `daily-report.js:218`)·R17 | 5.2 일일 보고 · "보고 불가 → 프롬프트" | MAPPED | — |
| F88 | 금액 숨김(기본 숨김) | `daily-report.js:4,486` | R17 | 5.2·5.3 | MAPPED | — |
| F89 | 보고 우편함(ReportInbox/Outbox, 사용자 시트) | `daily-report.js:3,530` | R1·R2 | 5.2 "답 붙여넣고 검토" | MAPPED | — |
| F90 | 모의투자 일일보고서 Set A + 사용자 세트 B/C/D + 비교 | `daily-report.js:6`, `app.js:754`, `virtual-trading-compare.js:1-9,127` | R3·R4·R16 | 5.3 모의 일일 보고 | MAPPED | 시안은 세트 A·B만 그렸다. |
| F91 | 리허설(기록 없음) 실행 | `daily-report.js:496`, `virtual-trading-signals.js:1-6` | R1, 장부를 쓰지 않음 | `#/detail/virtual-trading` | MAPPED | — |
| F92 | 보고 ⑪ 기록·⑫ 기간 수익률·⑬ 상대 지수(기간·기준 통화 선택) | `report-benchmarks.js:1-6`, `daily-report.js:309` | R1·R3(빈칸, 보간 없음)·R17 | 5.2·5.3 | MAPPED | — |
| F93 | 가상 장부 시트 저장(VirtualA~D·Mine·Meta·Flags, 추가만, 클릭 때만) + 세트 비중 저장·삭제 P7 | `virtual-ledger-sheets.js:1-8,527` | R1·R2·R4·R16 | `#/detail/virtual-trading` · 5.3 | MAPPED | — |
| F94 | 기기 V 이력(가상매매 V 기울기용, localStorage, 추가만) | `virtual-trading-v-history.js:1-9,79` | R13·R16(가격 없음) | `#/detail/virtual-trading`(화면 없는 기록) | MAPPED | — |
| F95 | 5.4 포트폴리오 구조 트리 | `ia-screens.js`(`tree/portfolio`) | R24 | 5.4 | MAPPED | — |

### 3-7. 6 프롬프트 · n 트리 · n+1 Lab · 설정

| # | 기능 | 현재 위치 | 보호 규칙 | 새 화면 (시안 / V2) | 상태 | 비고 |
| --- | --- | --- | --- | --- | --- | --- |
| F96 | 프롬프트 라이브러리(`research.html`: 목록·변수·도메인·★·내 사본, 선택 기업 가져오기) R1 | `research-bridge.js:1-10,189`, `app.js:529` | 공식 카탈로그 불변, 자동 공식 적용 없음 | Prompt 6.1 / `#/prompts` | MAPPED | `build_web_app.py`가 `research.html`을 지운다. 다시 만들어야 한다. |
| F97 | n 구조 트리(전체 시스템 한 장) | `ia-screens.js`(`system`), `app.js:950` | R24 | SystemTree·MTree / `#/tree` | MAPPED | — |
| F98 | n+1.2 전진 검증(공개 원장 + 클릭 시 기기 수익률, 평가 구간 분리) B1 | `forward-validation.js:1-3,117,219,230` | R1·R2·R6·R16 | Lab n+1.2 | MAPPED | — |
| F99 | n+1.1 백테스트(비활성) + 9.1 준비 목록 B2 | `screen-detail.js:1-4` | 결과 숫자 없음 | Lab n+1.1 | MAPPED | — |
| F100 | Google 첫 설정(로그인·Picker·시트 만들기·확인·Universe 채우기) G4s | `google-sheet-setup.js:1-3,40` | R1·R2(토큰은 세션 안) | `#/detail/settings` | MAPPED | — |
| F101 | 시세 시트(저장·붙여넣기·읽기) G5s | `google-sheet-quotes.js:1,462` | R1·R2·R20 | `#/detail/settings` | MAPPED | — |
| F102 | 가격 저장 켜기·끄기·핵심·Universe504 저장(클릭, 진행·중단) G6s | `price-store.js:1-12,133,447,465` | R1·R2·R16 | `#/detail/settings` | MAPPED | — |
| F103 | Worker 주소·거래 시트·Universe 시트 ID 저장 G7s | `private-history.js:8,80`, `private-trades.js:3`, `private-subset-view.js:3,9` | R2·R21 | `#/detail/settings` | MAPPED | — |
| F104 | 기기 백업·불러오기(+사용자 그림 선택 포함) G3s | `device-backup.js:1-5,10,68`, `app.js:200` | R21 | `#/detail/settings` · MTree "내보내기" | MAPPED | — |
| F105 | 캔들 색(한국식·미국식) G1s | `theme-boot.js:6`, `app-shell.js:115` | — | Technical 범례 "설정에서 미국식으로" / `#/detail/settings` | MAPPED | — |
| F106 | 뉴스 원문 언어 G2s | `app.js:197` | — | `#/detail/settings` | MAPPED | — |
| F107 | 운영 상태(공개 파일 STALE은 파일별 기준) | `ops-status.js:1`, `app.js:1030,1339` | 새 임계값 없음 | `#/detail/data-status` | MAPPED | — |
| F108 | 원자료 보기(개발자용, 기업 선택) G9s | `app.js:206-211` | 가격 없음 | `#/detail/financials` | MAPPED | — |

### 3-8. 시안에만 있는 새 기능 (DRAFT_ONLY_NEW, 분모 제외)

| # | 기능 | 시안 위치 | 관련 규칙 | 상태 | 비고 |
| --- | --- | --- | --- | --- | --- |
| N01 | 리더보드 수익률 기간 고르기(1D·5D·20D·60D·YTD·1Y)와 수익률 열 | QGV·MQGV 1.1 | R1·R2(기기 시세로만) | DRAFT_ONLY_NEW | G10이다. 기간 정의 결정이 필요하다. |
| N02 | 1.2 세부 요인 비중 "0 = 제외(결측 아님)", "공식값으로 되돌리기" 버튼, "내 설정 저장 (v3)" | QGV 1.2 | R13 | DRAFT_ONLY_NEW | 일부는 기존 W1과 겹친다. |
| N03 | 4.2 공시·뉴스 5줄 요약(Q 예상·G 예상·성격·주가 반영 초과수익) | News·MNews 4.2, Main 4번 칸 | R1·R2·R4·R5 | DRAFT_ONLY_NEW | 주가 반영은 가격이 필요하다. 생산자도 없다. |
| N04 | 검색어가 없을 때 매크로가 고른 기업을 무작위로 보이기 | News 4.1·4.2, MNews | R23 | DRAFT_ONLY_NEW | 고르는 규칙이 없다. |
| N05 | 3.3 SIC 산업 고르기(대분류 10·2자리 54·4자리 183, 5곳 미만이면 상위 분류) + ★ 산업 고정 카드 | Macro 3.3 | R3·R5 | DRAFT_ONLY_NEW | 산업 링(F66) 위에 고르기 칸을 더한다. |
| N06 | 3.2·3.3 조정 조건과 확률(과거 전환 빈도) | Macro 3.2·3.3 | R5 | DRAFT_ONLY_NEW | Lab 검증 전에는 미산출이다(F70과 같은 결정). |
| N07 | 기술 지표 정도 묶음(민감·보통·둔감) | Technical 2.1 | R5 | DRAFT_ONLY_NEW | 묶음 값이 정의되지 않았다. |
| N08 | 일일·주간 보고 전환(주간 보고) | Portfolio 5.2 | R17 | DRAFT_ONLY_NEW | 주간 집계는 결정 대기다(10/21 인수인계 6.2~6.3). |
| N09 | 로그인 계정 저장·동기화(즐겨찾기·가중치·노트·내 위치·프롬프트 사본) | Prompt 개인화 ①, Technical·News 문구 | R2 | DRAFT_ONLY_NEW | 로그인 백엔드는 결정 대기다(IA-5). |
| N10 | 머리말 기기 칩 "로그인 안 함 · 이 기기 기준" | Main 머리말 | — | DRAFT_ONLY_NEW | V2 `shell.js:16`에 이미 있다. |
| N11 | 트리의 "서로 이어지는 선"(한 기업으로 따라가기), Lab "다른 메뉴로" 연결 | SystemTree, Lab | R24 | DRAFT_ONLY_NEW | — |

### 3-9. 집계

| 상태 | 개수 | 번호 |
| --- | --- | --- |
| MAPPED | 95 | F01~F108 중 아래 13개를 뺀 나머지 |
| MISSING_IN_DRAFT | 7 | F11 PWA, F15 투자자 이야기, F17 오늘의 투자 화면, F18 시세 띠, F27 TradingView 미니·고급 차트, F29 엔터티 화면, F51 기업 목록 |
| NEEDS_OWNER_DECISION | 6 | F04 다크 테마, F05 영어 화면, F30 로고, F57 패턴 일치도, F60 시나리오 확률, F70 순환매 확률 |
| DRAFT_ONLY_NEW | 11 | N01~N11 (분모 제외) |

**커버리지 = MAPPED 95 / 현재 기능 108 = 88.0%.** 전환 조건은 100%(빠진 기능 0)이므로 13개가 남는다.

---

## 4. 시안 확보 현황 (18쪽 중 몇 쪽인가)

결론: **18개 보드(PC 9 + 모바일 9) 모두 원본 소스로 확보(열람)했다.** 다만 18쪽 PDF 파일 자체는 저장소에 없다.

- 아티팩트 `44Gm4mhXzXUDTm7svbAvGs`(Design 캔버스, 판 `1792560465-a9fc`)를 Artifact 도구 `read`로 열었다. 소유자 본인 아티팩트이고 링크 공유 상태다.
- `project/canvas.json` 제목은 "투자시스템 화면 시안 (손그림 칠판)", 생성 2026-10-18 04:45 UTC, 보드 18개다.
- 보드 원본 18개를 작업 임시 폴더로 받아 읽었다. 저장소에는 넣지 않았다(시안 숫자는 예시이고, 소유자 비공개 캔버스).

| 순서 | 보드 | 제목 | 크기 | V2 경로 |
| --- | --- | --- | --- | --- |
| 1 | `Main.dc.html` | 0. 기업 검색 · 검색 결과 | 1440×1700 | `#/`, `#/company/<코드>` |
| 2 | `QGV.dc.html` | 1. QGV | 1440×2900 | `#/qgv` |
| 3 | `Technical.dc.html` | 2. 기술적 분석 | 1440×2500 | `#/technical` |
| 4 | `Macro.dc.html` | 3. 매크로 | 1440×3400 | `#/macro` |
| 5 | `News.dc.html` | 4. 뉴스 (공시·뉴스·관계망) | 1440×2300 | `#/news` |
| 6 | `Portfolio.dc.html` | 5. 포트폴리오 | 1440×2400 | `#/portfolio` |
| 7 | `Prompt.dc.html` | 6. 프롬프트 라이브러리 · 개인화 | 1440×1500 | `#/prompts` |
| 8 | `SystemTree.dc.html` | n. 투자시스템 내용구성 트리 | 1440×1900 | `#/tree` |
| 9 | `Lab.dc.html` | n+1. Lab | 1440×1500 | `#/lab` |
| 10 | `m/MMain.dc.html` | 모바일 0. 검색 | 390×1500 | 같음(폭 ≤720px) |
| 11 | `m/MQGV.dc.html` | 모바일 1. QGV | 390×2300 | 같음 |
| 12 | `m/MTechnical.dc.html` | 모바일 2. 기술적 분석 | 390×1700 | 같음 |
| 13 | `m/MMacro.dc.html` | 모바일 3. 매크로 | 390×2300 | 같음 |
| 14 | `m/MNews.dc.html` | 모바일 4. 뉴스 | 390×1700 | 같음 |
| 15 | `m/MPortfolio.dc.html` | 모바일 5. 포트폴리오 | 390×1800 | 같음 |
| 16 | `m/MPrompt.dc.html` | 모바일 6. 프롬프트 | 390×1300 | 같음 |
| 17 | `m/MTree.dc.html` | 모바일 n. 구조 트리 | 390×1700 | 같음(전체 메뉴) |
| 18 | `m/MLab.dc.html` | 모바일 n+1. Lab | 390×1300 | 같음 |

- 보드 수와 이름은 `PLAN` §0("PC 9장 + 모바일 9장")과 §4 메뉴 표(Main·MMain … Lab·MLab)와 맞는다. 소유자가 말한 "18쪽"은 이 18개 보드로 보인다. 다만 PDF의 쪽 순서·내용은 PDF를 열어 대조하지 않았으므로 **같다고 확인하지는 않았다**.
- 저장소 안: 시안 PDF·PNG가 없다(`git ls-files`의 PDF·PNG는 옛 실사이트 캡처와 실험 자료뿐). 저장소 문서에 보드 내용을 옮겨 적은 것도 없다.
- 예전 "6쪽": `docs/handoff/HANDOFF_HISTORY_20261021.md:21`의 Drive 파일 `투자시스템 화면 시안 (손그림 칠판).pdf`(8,525,413 bytes, 2026-10-21 05:55 UTC)다. Codex가 6쪽을 이미지로 열람했다. 어느 6개 보드였는지는 기록에 없다.
- 18쪽 후보: 소유자 Drive에 `투자시스템 화면 시안 (손그림 칠판) (1).pdf`(13,568,024 bytes, 2026-10-21 10:18 UTC 생성)가 있다(메타데이터만 확인). 내려받거나 쪽수를 세지 않았다.
- 화면에 넣지 말아야 할 시안 요소(규칙 충돌): 예시 숫자 전부(R24), 시나리오·국면 확률(R5), 패턴 일치도(R5), Google Fonts 링크와 인라인 style(R9), "로그인 계정 저장"(결정 대기).

---

## 5. 오늘 전환하면 잃는 것

### 5-1. 자리 자체가 없는 기능 (13개)

1. F11 PWA 설치·오프라인 셸(`manifest.json`까지 빌드에서 지워짐)
2. F15 홈 투자자 이야기(버핏 서한 인용·출처 시트)
3. F17 오늘의 투자 화면 `#brief`(통합 판단·Attention·보고서 칩·플레이북 오늘 요약)
4. F18 TradingView 시세 띠
5. F27 TradingView 미니·고급 차트
6. F29 엔터티 화면(산업·매크로 지표 상세)
7. F51 기업 목록 `#companies`
8. F04 다크·시스템 테마(결정 대기)
9. F05 영어 화면·언어 전환(결정 대기)
10. F30 기업 로고(결정 대기)
11. F57 공식 패턴 감지 표시 방식(시안 일치도와 충돌, 결정 대기)
12. F60 시나리오(시안 확률과 충돌, 결정 대기)
13. F70 3.2 순환매(시안 확률과 충돌, 결정 대기)

### 5-2. 자리는 있으나 V2 P0에 연결되지 않은 것

**MAPPED 95개 모두**다. V2 P0의 모든 절이 `pending('…')`("연결 전")이다(`V2/screen-menus.js:43`, `V2/screen-search.js:16-28`, `V2/screen-detail.js:7`). 게다가 V2 P0는 저장소를 쓰지 않고, 같은 출처의 공개 JSON도 읽지 않는다(`tools/web_app_shell_browser_test.js:7,31,78`). 오늘 기본 화면을 바꾸면 다음이 즉시 사라진다.

- 가격 클릭 요청과 시트 연결 전부(F25·F26·F41·F54·F65·F83·F98·F100~F103)
- 기기 저장 자료 화면 전부: 관심·그룹·프로필·노트·시나리오·내 위치·플레이북·TARGET v1 초안·보유(F09·F44·F52·F59~F61·F67·F81·F85·F86). 저장된 자료는 기기에 남지만 볼 화면이 없다.
- 리더보드·스탯창·트리·뉴스 목록 등 공개 자료 화면 전부

### 5-3. 새 화면이 잃기 쉬운 보호 규칙 (꼭 옮길 것)

1. R1 클릭 요청만. 시안의 수익률 기간·주가 반영·스탯창 가격 축이 자동 요청을 부르기 쉽다.
2. R2·R21 가격·보유·시트 ID·토큰·환율은 기기에만. 시안의 "로그인 계정 저장"은 결정 전까지 만들지 않는다.
3. R3 NA≠0. 시안 표의 "NA는 이유를 눌러서 봄"을 지킨다.
4. R4·R5 주문·지시 문구 금지. 확률·승률·점수 표현 금지(시안 확률 숫자는 옮기지 않는다).
5. R6·R7·R8 calc_version, V n/5, V_FACTORS_V3_V4_MISSING, number_check. 시안 QGV 표에 n/5 칸을 더한다. TARGET v1 세부 화면은 관문을 그대로 쓴다.
6. R9·R10 CSP(인라인 없음, 글꼴 자체 호스팅)와 가드 고정 해시. 별도 경로 게시라면 옛 파일과 새 파일 합계가 192개·8 MiB 안에 들어야 한다.
7. R11·R12 IEX 출처 문구와 "임시 V". **규칙 있음 / 코드 없음(후속 PR 예정).** 중앙 V 표시가 들어오는 화면(1.1, 검색 결과 QGV 칸, TARGET v1)에 자리를 미리 둔다.
8. R14 IA-7 키. 관심·메모·뉴스 = Issuer, 차트 그림 = Listing. 새 화면이 `company_id`(TARGET 19)를 키로 새로 쓰지 않게 한다.
9. R15·R16·R17 사용자 작성 층 분리, 추가만, 금액 숨김 기본.

---

## 6. 소유자 확인이 필요한 것 (모음)

1. `PLAN` §0·§1(전부 재작성, 한 번에 전환, 옛 화면 삭제)과 이번 결정(화면만 재작성, 모듈 재사용, 별도 경로, 2주 유지)이 다르다. `PLAN`과 `build_web_app.py`를 이번 결정에 맞춰 고칠지 정해야 한다.
2. 다크 테마·영어 화면·로고(F04·F05·F30)를 유지할지 정해야 한다.
3. 시안의 확률·일치도 숫자(F57·F60·F70·N06)는 R5와 충돌한다. "미산출"로 둘지 정해야 한다.
4. 자리가 없는 7개(F11·F15·F17·F18·F27·F29·F51)를 세부 화면으로 옮길지, 없앨지 정해야 한다.
5. 18쪽 PDF와 아티팩트 18보드가 같은 것인지 확인해야 한다(§4).

---

## 7. 이 문서가 하지 않은 것

- 코드·웹 자산·가드·워크플로를 바꾸지 않았다. 중앙 V 파일, TARGET v0 decoupling 브랜치, #389 코드, 정기 워크플로는 읽기만 하거나 열지 않았다.
- 시안 보드 원본을 저장소에 넣지 않았다.
- 가격·보유·시트 ID·토큰은 이 문서에 없다. 시안의 예시 숫자도 옮기지 않았다.
- 상태 MAPPED는 "자리가 있다"는 뜻이다. 구현·시험·게시가 됐다는 뜻이 아니다.
