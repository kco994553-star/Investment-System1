# 프론트엔드 데이터 계약 — 화면 요소별 출처·갱신·신선도 (2026-10-18)

상태: **계약 문서 + 검증 시험.** 화면 코드·엔진·스키마·가드·워크플로는 바꾸지 않았다.
기준 커밋: canonical `e1b98ba6` (`claude/investment-system-top500-validation-alrugm`, #312 병합). 이후 #313(문서만)을 받아 다시 얹었다. 인용한 코드 줄은 같다.
근거: 사용자 질문 "업데이트에 따라 변해야 하는 걸 인지하고 있는 거지?"(2026-10-18)와 코디네이터 지시(같은 날).
검증 시험: `implementation/tools/update_propagation_browser_test.js` (§7).

경로는 따로 적지 않으면 `implementation/src/investment_system/product/web_assets/` 아래다. `파일:줄`은 기준 커밋의 줄이다.

**2026-10-21 정정 범위:** Main 통합 source `fa6dd669`를 기준으로 메뉴 연결, QGV 분류 표시 필터, 목록 복귀·홈 갱신, 프롬프트 선택 기업 계약을 아래 해당 절에 추가했다. 초판 행과 줄 번호는 당시 기록이며, 같은 항목은 날짜가 붙은 정정을 우선한다. 로컬 구현·시험 상태를 기록하며 게시·실사이트 완료를 뜻하지 않는다. 시험 근거와 통합 상태는 §7-6을 따른다.

## 0. 읽는 법

### 0-1. 다른 문서와의 관계

- [PRODUCT_FEATURE_MAP_20261018](PRODUCT_FEATURE_MAP_20261018.md): 기능 단위 구현 상태(엔진·계약·화면·검증 근거). 이 문서는 그 표를 되풀이하지 않는다.
- [PRODUCT_IA_ONTOLOGY_CHECK_20261018](PRODUCT_IA_ONTOLOGY_CHECK_20261018.md): 메뉴 대응·엔티티·결정 후보 IA-1~IA-18.
- 관련: [FRONTEND_INTERACTION_CONTRACT_20261019](FRONTEND_INTERACTION_CONTRACT_20261019.md) — 화면 조작 요소 목록, 조작 × 갱신(새 게시본 뒤 보기 상태), 순환 국면 링 명세.
- 이 문서: **화면 요소 하나하나**가 어디서 값을 읽고, 언제 바뀌고, 언제 바뀌면 안 되는지. 같은 역할의 기존 문서는 없었다(`implementation/docs` 안 data/screen contract 문서 없음, `daily_data_pipeline/PUBLIC_ENGINE_SCREENS.md`는 생산 쪽 계약).

### 0-2. 칸의 뜻

- **상태**: 연결 완료 / 부분 연결 / 설계만 / 미구현.
- **저장**: 공개(GitHub Pages 공개 파일) / 기기 계산(이 브라우저 메모리에서 계산, 저장 안 함) / 기기 저장(이 브라우저 localStorage·sessionStorage·IndexedDB) / 비공개 시트(사용자 본인 Google 시트, drive.file 권한) / 계정 저장(로그인 계정에 저장).
  - 비공개 시트는 "기기 안에서만 저장"이 아니다. 사용자 Google 계정의 파일이다.
  - 계정 저장은 지금 **없다**(§1-6).
- **갱신 계기**: 일일 실행 / 샤드 순환(뉴욕 날짜마다 7개 중 1개) / 발표 기준(매크로) / 분기(13F) / calc_version 변경 / 기기 가격 갱신 / 사용자 조작 / 수동 검토 표(company-names-ko.json).
- **재취득**: 아래 §2-3의 공통 규칙 R을 따른다. 다르면 따로 적는다.

## 1. 바로잡을 점

### 1-1. "예약 실행 성공 = 화면 반영"이 아니다. 세 단계는 따로다

1. **예약 실행(collect)**: `.github/workflows/sec-daily-public-inputs.yml:4` cron `17 22 * * *`(UTC). 단계마다 파일을 만들고 `pages_artifact_guard.py`로 검사한다(:75-153). 끝에 Pages 산출물을 올린다(:156).
2. **검증(verify) → 배포(deploy)**: verify가 같은 산출물로 브라우저 시험 목록을 돌린다(:160-207). 실패하면 배포만 막는다. deploy는 `pages_freshness_guard.py`로 공개 사본과 행 단위로 비교한다(:236-246). 공개 사본보다 오래된 acquired_at, 사라진 행, 바뀐 장부 기록이 있으면 배포를 거부한다. 그다음 `deploy-pages`(:249).
3. **브라우저 반영**: 배포 뒤에도 이미 열린 탭은 바뀌지 않는다. 앱은 공개 파일을 **페이지를 열 때 한 번** 읽는다(`app.js:1180-1198`). 새로고침(또는 새로 열기)해야 새 게시본을 읽는다(§2-3, 결함 D1).

그러므로 "실행 성공"은 수집 성공일 뿐이다. 배포 성공은 Actions의 deploy 잡으로, 화면 반영은 화면의 as_of로 확인한다.

### 1-2. 샤드 수집 범위와 점수 재계산 범위는 다르다

- 수집: Universe504는 뉴욕 날짜 서수 mod 7로 고른 샤드 하나만 SEC에서 다시 받는다(`universe/sec_universe_shares.py:77-90 shard_day/shard_index_for`, 설정 `universe/sec_universe_shares_config_v0.json` shard_count 7). TARGET 19개는 매일 TARGET 파이프라인이 다시 받는다(workflow :83, `universe/sec_qgv2.py:12-14`).
- 재계산: 게시할 때마다 **모든** LIVE/STALE 행의 요인 백분위와 Q·G 축 점수를 단면 전체로 다시 계산한다(`universe/sec_qgv2.py:336-349 publish → v2_scoring.score_rows`, 독스트링 :15-17).
- 결과: 다시 수집하지 않은 행도 점수가 바뀔 수 있다. 그 행의 acquired_at은 그대로다(`restate`는 상태만 바꾼다, :238-249). 파일을 새로 만들었다고 옛 행이 새 자료처럼 보이면 안 된다.
- 시험으로 확인: 2일차에 NASDAQ:AKAM만 다시 수집하면, 수집하지 않은 NASDAQ:ABNB의 Q가 11.76 → 11.02로 바뀌고 화면의 "수집" 시각은 1일차 그대로다(§7).

### 1-3. 매크로 경고등: 공개 3개 + 기기 계산 2개

- 공개(macro-screen.json `data.macro_lights_v1`): 고용(BLS LNS14000000), 물가(BLS CUUR0000SA0), 금리 곡선(재무부 10년−3개월). `macro-lights.js:16 PUBLIC_LIGHTS`, 빌드 `macro/macro_lights_public.py:31,170-171`.
- 기기 계산(RAM만): 시장(SPY, 비공개 Worker 일봉), 신용(HYG÷IEF, 추정). `macro-lights.js:16 DEVICE_LIGHTS`, :3-5. 신용은 Worker 허용 목록에 HYG·IEF가 없으면 "확인 불가"다(:28-29, :176-180).
- 공개 경고등의 기준 시각은 **관측 기간**(고용·물가 = 월, 곡선 = 일)이다. 파일 as_of가 아니다(`macro-lights.js:27 AS_OF_KEY`, 화면 :249). 새 발표가 없으면 파일이 매일 새로 나와도 경고등 기준은 그대로다.

### 1-4. 13F 날짜는 셋이다

- **보유 기준일(분기말)**: `sec-13f-changes.json` 행의 `previous_quarter → current_quarter`(`public-screens.js:121`, 화면 "기준 분기" `thirteenf-quarter.js:49`).
- **제출일**: `details.current.filing_date`(날짜만, `providers/sec_13f_managers.py:344`). 화면 "제출일" `thirteenf-quarter.js:50`. SEC **접수 시각(acceptance time)은 공개 파일에 없다.**
- **우리 수집 시각**: 같은 행의 acquired_at과 파일 `sources[].acquired_at`(`sec_13f_managers.py:344`, `public-screens.js:92-97`).
- 일일 실행이 매일 돌아도 13F 내용은 분기마다만 바뀐다(최근 두 분기 비교, `providers/sec_13f_managers.py:182 select_quarters`). 분기말 뒤 최대 45일까지 제출이 이어진다.

### 1-5. calc_version 변경 ≠ 값 변경

- calc_version은 **계산 규칙**의 버전이다(`sec-qgv2.js:29-33`, Python `qgv/v2_factors.py CALC_VERSION`).
- 새 SEC 자료로 값이 바뀌어도 calc_version은 그대로다. 규칙이 바뀌어도 어떤 행의 값은 같을 수 있다.
- 규칙이 바뀐 날, 그 규칙으로 다시 수집되지 않은 행은 값을 지우지 않고 남기되 비교 모집단에서 뺀다(CALC_VERSION_MISMATCH, `qgv2-inputs.js:23-26,68`; `universe/sec_qgv2.py:337-338`). 그 행은 자기 샤드 차례(최대 7일) 또는 1회성 전체 샤드 실행(workflow 입력 `all_shards`, :5-11) 뒤에 돌아온다.
- 화면: Universe 기업 화면은 "calc_version 파일과 다름"을 쓰고 점수를 NA로 둔다(`universe-company.js:50,61`).

### 1-6. 로그인·계정 동기화는 연결되지 않았다(계획)

- 지금의 "구글 로그인"은 사용자 Google 시트를 읽고 쓰는 권한(drive.file)뿐이다. 토큰은 메모리에만 있고 약 1시간 뒤 다시 연결한다(`google-sheet-quotes.js:1,8-9,69`).
- 설정·프로필·관심 기업을 계정에 저장하거나 기기 사이에 동기화하는 기능은 **없다**. 화면도 "로그인 저장은 결정 대기"라고 쓴다(`ia-screens.js:129`).
- 기기 사이 이동은 수동 백업 파일뿐이다(`device-backup.js:1-7,63`).

### 1-7. STALE은 "7일"이 아니다. 파일마다 자기 기준을 쓴다

- sec-qgv2.json: 행마다 acquired_at 기준 **14일**(`stale_after_seconds` 1,209,600, 설정 `stale_after_days: 14`). 샤드가 7일 주기라 한 번 놓쳐도 STALE이 아니다.
- sec-disclosures.json · news-signals.json · dart-disclosures.json: 파일 as_of 기준 **48시간**(`sec-disclosures.js:99`, `news-signals.js:7,132`, `dart-disclosures.js:6`).
- macro-screen.json · sec-13f-changes.json 등 공개 화면 파일: 파일의 `stale_after_seconds`(`public-screens.js:92-94`).
- 7일 규칙은 전진 검증 장부의 ROW_DATA_STALE뿐이다(`forward-validation.js:17 FRESH_DAYS=7`).
- 운영 화면은 새 숫자를 만들지 않고 각 파일의 기준을 쓴다(`ops-status.js:1,13`).

### 1-8. 가격에는 시각이 둘이다: 읽은 시각과 가격 자체의 시각

- 가격마다 두 칸을 따로 둔다. **읽은 시각**(시트·Worker에서 이 기기가 읽은 때)과 **가격 기준 시각**(그 가격의 거래일·거래 시각).
- 비공개 시트 Universe 탭(GOOGLEFINANCE "price")에는 거래 시각이 없다. 그래서 가격 기준 시각은 **'미확인'**이다. 코드도 `price_kind:'GOOGLEFINANCE_CURRENT'`, `trade_time:null`, `exact_eod:false`로 둔다(`private-subset.js:78`).
- Worker 일봉은 세션 종가라 거래일이 있다(`device-market.js:103-104 WORKER_CLOSE`, `SESSION_CLOSE`). 가격 탭 Prices_D는 행마다 `date`(거래일)와 `fetched_at`(읽은 시각)을 따로 둔다(`price-store.js:13`).
- 방금 읽었다고 오래된 가격이 현재 가격처럼 보이면 안 된다. 지금 코드는 이 점이 어긋난다(결함 D10).

## 2. 갱신 계기 한눈에

### 2-1. 공개 파일과 주기

| 공개 파일 | 생산 단계(workflow 줄) | 계기·주기 | 바뀌는 범위 | 신선도 표시 |
|---|---|---|---|---|
| sec-qgv2.json | :101 Universe 샤드 + :83 TARGET | 일일 실행. Universe는 샤드 순환(7일에 한 번), TARGET은 매일. 게시마다 전체 재계산 | 다시 받은 행의 값·acquired_at. 모든 행의 백분위·축 점수 | 파일 as_of, 행 acquired_at, 행 상태 LIVE/STALE(14일), calc_version |
| sec-universe-shares.json / sec-universe-qg.json | :101 | 샤드 순환 | 다시 받은 행 | 행 acquired_at |
| sec-disclosures.json | :142 | 일일 실행 | 최근 90일 8-K | 파일 as_of, 48시간 STALE |
| news-signals.json | :147 | 일일 실행 | 최근 14일 뉴스·IR | 파일 as_of, 48시간 STALE. schema 2: 회사별 이번 결과(UPDATED/NO_NEW_ITEMS/FAILED/NOT_RUN)와 출처별 `refresh`(마지막 시도·성공, 이월 시작). 실패는 state를 바꾸지 않고 reason_codes `REFRESH_FAILED`·`REFRESH_PARTIAL_FAILED`로 적는다 |
| dart-disclosures.json / dart-financials.json | :90 | 일일 실행 | 한국 공시 | 파일 as_of |
| macro-screen.json | :83 (`--macro-v0`) | 일일 실행, 값은 발표 기준 | 새 발표가 있는 계열만 | 관측 기간, 수집 상한 시각(available_at), 파일 as_of |
| macro-evidence.json | 일일 P1 근거 수집 (#352) | 일일 실행, 재취득은 규칙 R | 정부통계 관측·발표/수정 기록·현재 빈티지 재생(서로 구분) | generated_at, 계열 acquired_at/last_success_at, NOT_AVAILABLE 사유·자료 지연. 공식 국면/확률/게이트 아님 |
| sec-13f-changes.json | :135 | 일일 실행, 내용은 분기 | 최근 두 분기 | 분기말, 제출일, 수집 시각 |
| forward-validation-ledger.json | :114 | 일일 실행, 추가만 | 새 기록 행만 | 기록 세션 날짜 |
| company-classification.json | :122 | 일일 실행 | 분류 | 파일 as_of |
| company-logos.json | :128-129 | 일일 실행 | 표시만 | — |
| company-names-ko.json | 빌드에 포함(수동 검토 표, `reviewed_at`) | 수동 검토 | 이름 표시·검색만 | reviewed_at |
| actual-catalog.json (TARGET 목록) | 빌드에 포함 | 코드 변경 | TARGET 구성 | target_root_version |

### 2-2. 기기·사용자 쪽

| 자료 | 저장 | 계기 |
|---|---|---|
| 기기 시세(V 계산용) | 비공개 시트(Universe 탭) → 기기 계산 | 사용자가 승인된 "Universe 읽기" 버튼을 누를 때만. RAM에만 둔다(`qgv-scores.js:1-8`). 읽은 시각 있음, 가격 기준 시각 '미확인'(§1-8) |
| 일봉(가격 탭 Prices_D/Prices_M) | 비공개 시트 | 앱을 열 때 자동 추가(`app.js:1197`, `price-store.js:1,12`) |
| 비공개 Worker 일봉 | 기기 계산(RAM) | 사용자가 누를 때(`private-history.js`, `forward-validation.js:1-3`) |
| 실제 보유(ACTUAL) | 기기 저장(IndexedDB) | 사용자 입력(`device-actual.js:18,187`) |
| 가상 장부·세트 정의·보고 우편함 | 비공개 시트 | 사용자 조작·러너 실행 |
| 설정·프로필·★·노트 | 기기 저장 | 사용자 조작(§6) |

### 2-3. 공통 재취득 규칙 R

- 같은 출처 공개 JSON은 모두 `cache:'no-store'` 또는 `'no-cache'`로 읽는다(HTTP 캐시를 거치지 않거나 재검증). 예외는 Google API·Worker 호출뿐이다. 시험이 모든 `fetch(`를 정적으로 검사한다(§7).
- 서비스 워커는 정적 셸 5개(offline.html, style.css, manifest.json, 아이콘 2개)만 캐시한다. 데이터 JSON은 손대지 않고 네트워크로 보낸다(`service-worker.js:1-4,17`). 워커 스크립트도 HTTP 캐시를 쓰지 않는다(`pwa.js:15 updateViaCache:'none'`).
- 앱은 공개 파일을 페이지를 열 때 한 번 읽어 RAM에 둔다(`app.js:1180-1198`). 공시·뉴스 목록도 페이지당 한 번이다(`app.js:401-403`). 해시 이동(SPA 화면 전환)은 다시 읽지 않는다. 다시 읽는 때는 새로고침뿐이다.
- (2026-10-18 `claude/fe-data-refresh`) 열린 탭에서는 **'자료 새로고침' 버튼**(`data-refresh.js`)이 같은 판독기로 공개 파일 묶음 전체를 다시 읽는다. 하나라도 읽기 실패면 아무것도 바꾸지 않고 '갱신 실패 · 이전 값 유지'와 옛 기준 시각을 쓴다. 성공하면 묶음을 한 번에 바꾸고 열린 화면을 제자리에서 다시 그린 뒤 `public-data-updated` 이벤트를 보낸다. 비공개 Worker·시트 요청과 설정 변경은 없다. 새 게시가 없어도 파일마다 자기 기준(행 acquired_at 또는 파일 as_of + stale_after_seconds)의 경계를 지나면 이미 읽은 본문으로 상태를 다시 판정한다(1분마다, 탭 복귀, 화면 이동, 버튼). 자동 재취득(폴링)은 하지 않는다.
- (2026-10-19 `claude/refresh-keeps-view-state`, G2) 버튼 새로고침·경계 재판정이 화면 전체를 다시 그려도(QGV 허브·13F·뉴스·관심 기업·매크로·구조 트리·전체 트리·기업 목록·엔티티) **보기 상태는 남는다**: 페이지 위치(창 안 같은 요소가 같은 높이), 포커스(같은 요소가 남아 있을 때), 펼친 details, 검색·필터·정렬 입력, 고른 보기 버튼(13F 보기·유형, 뉴스/관계망), 표 안 가로 스크롤, 기업 목록 '더 보기' 개수. 값은 늘 새 묶음에서 다시 그린다(옛 DOM을 두지 않음). 사용자가 화면을 여는 이동(해시 변경)은 전처럼 맨 위에서 시작한다. ★(관심 기업·투자자)은 설정이라 건드리지 않는다. `data-refresh.js` captureView/restoreFields/restoreView, 시험 `refresh_view_state_browser_test.js`.
- (2026-10-21) `macro-evidence.json`도 같은 공개 묶음에서 읽기·검증 후 함께 적용한다. 근거 파일만 바뀌어도 새 게시로 인식한다. 404는 첫 읽기에서 미게시이며, 이전 유효 파일이 사라진 새로고침에서는 실패로 처리하여 이전 묶음을 보존한다. 초기 묶음 읽기가 끝날 때까지 새로고침을 막아 응답 경합을 피한다. 근거 탭·지표·재구성 선택은 탭 RAM에서 이동/다시 그리기 후 유지하며 관측값을 저장하지 않는다.
- (2026-10-21, G3·G8 정정) 기업 목록·관심 목록의 검색·필터·정렬·더 보기 개수는 목록별 RAM에 남는다. 원래 목록에서 연 기업 상세/분석에서 돌아올 때 스크롤·포커스·커서도 복원한다. 다른 화면에서 목록으로 들어올 때는 상단에서 시작한다. 현재 공개 자료와 관심·그룹 설정으로 다시 그리며, 상세에서 바꾼 그룹 소속·이름을 옛 입력으로 덮지 않는다. 홈은 성공한 묶음 적용·시간 재판정 뒤 관심 소식만 제자리 갱신하고 검색 DOM·입력 상태는 유지한다. 실패한 묶음 읽기는 홈 소식 DOM도 유지한다.
- (2026-10-21, QGV 분류 표시 필터) 선택한 SIC 업종군·기업 유형은 모듈 RAM에서 새 공개 묶음에 다시 적용한다. 선택 업종군이 새 게시본에 없으면 선택과 0건 결과를 유지하고 사유를 표시한다. 전체로 자동 확장하지 않는다. 페이지 자체를 다시 로드하면 선택은 초기화된다. 공식 계산 모집단·점수·순위·모델 후보는 표시 필터로 바뀌지 않는다(§3-1).
- 읽기에 실패하면 그 파일의 값은 RAM에 남기지 않는다(`qgv2-inputs.js:82-94`). 화면은 NOT_AVAILABLE을 쓴다. 옛 값을 현재 값처럼 보여 주지 않는다.
- 더 새 스키마(schema_version > 2)는 값으로 쓰지 않고 새로고침을 요구한다(`sec-qgv2.js:41-43`, `universe-company.js:38`).
- GitHub Pages CDN 자체의 짧은 캐시(배포 직후 몇 분)는 앱이 통제하지 못한다. 배포 직후 새로고침에도 옛 as_of가 보이면 몇 분 뒤 다시 연다.

## 3. 화면 요소 계약

열: 요소(ID·뜻) | 출처(파일·필드·함수) → 소비 화면 | 상태·저장 | 계기·재취득 | 시각·버전·모집단 | 없음·STALE·철회·실패 때 | 바뀌면 안 되는 것 | 시험·미검증.
재취득이 R과 같으면 "R"이라 쓴다.

### 3-0. 홈 검색과 기업 화면

| 요소 | 출처 → 소비 | 상태·저장 | 계기·재취득 | 시각·버전·모집단 | 없음·STALE·실패 | 바뀌면 안 되는 것 | 시험 |
|---|---|---|---|---|---|---|---|
| 0 검색 목록 · 기업을 찾는다 | entities.json + TARGET 식별자(actual-catalog.json) + universe-codes.json + company-names-ko.json(`entity-search.js:120-158`, `home-screen.js:1-11`) → 모든 화면 검색칸 | 연결 완료 · 공개 | 코드 변경·수동 검토 표 · R | names `reviewed_at` | 이름 없으면 SEC 영문명, 둘 다 없으면 티커(company-names-ko.json policy) | 이름은 점수·순위·식별에 쓰지 않음 | company_names_browser_test, global_language_search_browser_test |
| 0 최근 검색 | localStorage `investment.web.v1.recent-search`(`home-screen.js:21-25`) | 연결 완료 · 기기 저장 | 사용자 조작 | — | 없으면 비움(지어내지 않음) | 공개 자료 | app_nav_ia_browser_test |
| 0 관심 기업 뉴스 | sec-disclosures.json · news-signals.json · dart(`home-screen.js:162-172`, 페이지당 한 번) | 연결 완료 · 공개+기기 저장(★) | 일일 실행 · R | 파일 as_of | 관심 기업 없으면 영역 없음 | 점수 | news_signals_browser_test |
| 기업 화면(TARGET) · 점수 기준 배지 | `QgvScores.compute → v2_as_of` = sec-qgv2.json as_of(`qgv-scores.js:207`, `company-screen.js:46-48`) | 연결 완료 · 공개 | 일일 실행 · R | as_of 원문 그대로 | 파일 없음 → "점수 기준 NOT_AVAILABLE" | — | **update_propagation**(값 일치) |
| 기업 화면(TARGET) · QGV·Q·G·V | 공개 Q·G(sec-qgv2.json target) + 기기 V(`company-screen.js:81-92`) | Q·G 연결 완료 · 공개 / V 부분 연결 · 기기 계산 | Q·G 일일 실행(TARGET 매일) · V 기기 가격 갱신 | calc_version, 단면 = Universe504 LIVE/STALE 발행사당 한 점 | NA는 0이 아니라 "—"와 사유(`company-screen.js:85`) | 이름·개인 프로필로 바뀌지 않음 | update_propagation, qgv_v2_screens |
| 기업 화면(TARGET) · 산출 상태·수집 시각 | 행 acquired_at·fiscal_year_end·상태(`company-screen.js:131-137`) | 연결 완료 · 공개 | TARGET 매일 | 수집 시각 UTC, FY | STALE → "반영 · 오래된 자료(마지막 유효 값)" + STALE 배지 | — | update_propagation(수집 시각 일치) |
| 기업 화면(TARGET) · 리더보드 순위 | 기기 표시 순서(`company-screen.js:173`) | 연결 완료 · 기기 계산 | 데이터·프리셋 | 19개 식별자 기준 | 총점 없으면 "—"와 제외 사유(:134) | "공식 순위 아님" 표기 유지 | update_propagation |
| 기업 화면(TARGET) · v1 미리보기 배지 | sec-qg-factors.json as_of(`company-screen.js:46-49`) | 부분 연결 · 공개 | 일일 실행 | v1 as_of | 오래되면 "STALE" 배지(결함 D4) | v2 점수와 섞지 않음 | web_state_presentation |
| 기업 화면(Universe504) · 축 Q·G·V | sec-qgv2.json records[코드](`universe-company.js:44-53,63-80`) | 연결 완료 · 공개(+V 기기 계산) | 샤드 순환 + 매일 재계산 · R | 출처 줄: as_of · 수집 · 수집 후 일수 · 상태 · calc_version(`universe-company.js:59-61`) | 정책상 NA(축 50% 미만), 미수집·CIK 미확인, 식별 충돌 철회, 계산 규칙 다름을 서로 다르게 씀 | 다시 수집 안 한 행의 수집 시각 | **update_propagation**(줄 전체 일치), universe_company |
| 기업 화면(Universe504) · 요인 Q1~G5 | 같은 행 factors(`universe-company.js:75-80`) | 연결 완료 · 공개 | 게시마다 재계산 | 같은 단면 | NA는 "—"와 사유 | — | update_propagation, universe_company |
| 기업 화면 · 분류·SIC·프로필 | 같은 행 sic·industry_group·profile + company-classification.json | 연결 완료 · 공개 | 샤드 순환 · 일일 | — | 행 없으면 NA | — | universe_company |
| 기업 화면 · 스탯창(레이더) | **병합 대기**(PR #311 `claude/fe-stat-radar`, `stat-radar.js`) | 설계 결정됨 · 브랜치에만 | Q·G 일일, V·가격 축 기기 가격 갱신 | 상세표 as_of = sec-qgv2.json as_of, 가격 축 = 기기 SPY 252세션 창(`stat-radar.js:255-262,330-341`) | 미산출 축은 점을 찍지 않음(0·평균 채움 없음) | 공식 점수·비중·순위 | update_propagation이 레이더가 있으면 Q·G 꼭짓점 확인(브랜치 빌드에서 6페이지 통과), 없으면 기록만 |
| 기업 화면 · 시세 배지 | 기기 시세(`company-screen.js:39-43,274`) | 부분 연결 · 기기 계산 | 기기 가격 갱신 | 지금은 `as_of` 하나만 보임. 읽은 시각과 가격 기준 시각을 나눠야 함(§1-8) | 없으면 "시세 NOT_AVAILABLE · 사유" | 공개 파일에 가격 없음 | 미검증(결함 D10) |
| 기업 화면 · V(금융업) | 프로필 FINANCIAL(`universe-company.js:90`, 문구 `qgv-scores.js:83-86`) | 연결 완료 | — | — | 지금 문구 "해당 없음". **바뀔 문구: '현재 금융업 가치평가 모델 미지원'**(진행 중, 아래 V 산출 현황과 같은 브랜치). 실패가 아니라 미지원이다 | 0으로 채우지 않음 | universe_company |

**2026-10-21 정정 — 홈과 목록 연속성:** 초판의 홈 관심 뉴스 행에 더해, `app.js`의 `DataRefresh.inPlace` → `HomeScreen.refreshPersonal`이 성공한 공개 묶음/시간 재판정으로 소식을 갱신한다. 검색 결과 자료도 기존 `apply → paintGlobalSearch` 경로로 새 묶음을 반영한다. 검색어·범위·선택 결과·포커스·커서와 검색 호스트 DOM은 유지한다. 실패 시 새 자료나 빈 목록으로 대체하지 않는다.

기업 목록·관심 목록은 `app.js`의 `directoryViews`에 목록별 보기 상태를 RAM으로 보관한다. 저장 입력은 검색·관심만·그룹 필터·정렬 6개에 한정하며 그룹 편집값은 포함하지 않는다. 더 보기 개수와 원래 목록 복귀 위치도 보관한다. 같은 기업 상세/분석에서 원래 목록 링크 또는 브라우저 뒤로 돌아오면 현재 자료로 그린 뒤 위치·포커스·커서를 복원한다. 페이지 reload는 이 RAM을 지운다. 시험: `search_continuity_browser_test.js`(§7-6).

### 3-1. QGV (1.1 리더보드 · 1.2 가중치 · 1.3 13F · 1.4 구조 트리)

| 요소 | 출처 → 소비 | 상태·저장 | 계기·재취득 | 시각·버전·모집단 | 없음·STALE·실패 | 바뀌면 안 되는 것 | 시험 |
|---|---|---|---|---|---|---|---|
| 1.1 순서·순위 | `QgvScores.compute`(`qgv-scores.js:169-207`) → `leaderboard-screen.js:140` | 연결 완료 · 기기 계산(공개 Q·G + 기기 V) | 데이터 변경·기기 가격·프리셋 칩 · R | 19개 식별자 전체 기준 순위, 동점은 티커 | 총점 없으면 순위 "—", 맨 뒤(:133-140) | 이름(표시만, :120-121), 저장한 개인 프로필, 테마·봉 색 | **update_propagation**(순서·순위·총점 일치), qgv_v2_screens |
| 1.1·기업 화면 · V 산출 현황(기기) | **미병합 · 진행 중**: 브랜치 `claude/fe-v-coverage`(아직 원격에 없음). 공용 `QgvScores.pageResult` / `vCoverage`를 레이더와 이 패널이 같이 써서 어느 화면에서나 V가 같다 | 진행 중 · 기기 계산 | 기기 가격 갱신("Universe 읽기") · 공개 파일 재취득 R | 불러온 파일에서 바로 셈: GENERAL n과 ceil(n×0.9)는 **관찰 지표**이지 TARGET 조건이 아니다. 전체 / 금융업 미지원 / 프로필 미상 수를 따로 보인다 | 가격 없음 → V 미산출 사유 | 공식 Q·G, 순위 규칙 | 브랜치 병합 시 그 시험 |
| 1.1 점수 기준 배지 | v2_as_of(`leaderboard-screen.js:77-79`) | 연결 완료 · 공개 | 일일 실행 · R | as_of 원문 | 파일 없음 → NOT_AVAILABLE | — | update_propagation |
| 1.1 가중치 프로필 칩(균형·우량·성장·가치)·가치 함정 관문 | 코드 프리셋(`leaderboard-screen.js:83-87`) | 연결 완료 · RAM(`app.js:657`) | 사용자 조작. 새로고침하면 기본(균형)으로 돌아감 | 배지에 프로필 이름 표시 | — | 저장되지 않음. 공식 기본값을 바꾸지 않음 | qgv_v2_screens |
| 1.1 수익률 기간 열 | 없음 | **미구현** | — | — | 열 자체가 없음(`leaderboard-screen.js:27-28`, 미연결 열 안내 :150) | — | — |
| 1.1 M3 시총 순위 | 비공개 시트 Universe 탭(`leaderboard-screen.js:62-63,80-81`) | 연결 완료 · 비공개 시트 → RAM | 사용자 "읽기" | 검증 행 수 | 읽기 전 NOT_AVAILABLE | "공식 순위 아님" | qgv_v2_screens, private_subset |
| 1.1 분석 모집단·순위 가능·표시 수 | `populationOf`(`leaderboard-screen.js:59-60,114-115`) | 연결 완료 · 공개 | 일일 실행 | 세 범위를 같다고 하지 않음 | — | — | qgv_v2_screens |
| 1.1 각주 "N개 기업 전체 기준" | 고정 문자열 19(`leaderboard-screen.js:149`) | 부분 연결 | **코드 고정** | — | — | — | update_propagation이 식별자 수와 비교해 다르면 기록(결함 D3) |
| 1.2 가중치 편집·사용자 프로필 | localStorage `profile-drafts-v2`(`device-profiles.js:136-140,175-176`), 후보 프리셋 v0.1(:143-148) | 연결 완료 · 기기 저장(백업 제외) | 사용자 조작 | 프로필 id·version·saved_at | — | 공식 점수·순위·게시 파일·장부(`personal` 키에만, :137-139) | **update_propagation**(저장해도 공식 순위 같음), qgv_v2_screens, preset_candidates |
| 1.2 기업 유형 커스텀 | `type-config-defaults.js` 복사본, 기기 저장 | 부분 연결 · 기기 저장 | 사용자 조작 | TYPE_SCOPE 버전 | 대부분 기본 34/33/33 | 공식 기본값 | device_profiles |
| 1.3 13F 투자자 보유 | sec-13f-changes.json(`public-screens.js:121`, `thirteenf-quarter.js:49-50`) | 연결 완료 · 공개 | 일일 실행, 내용은 분기 · R | 분기말·제출일·수집 시각(§1-4) | 비교 불가 사유를 고정 코드로 표시 | 13F는 점수를 바꾸지 않음 | thirteenf_filings, thirteenf_managers. 날짜 셋 구분 표시는 **미검증** |
| 1.3 투자자 ★ | localStorage `investor-stars`(`public-screens.js:143-144`) | 연결 완료 · 기기 저장 | 사용자 조작 | — | — | — | thirteenf_managers |
| 1.3 13F 가중치 연구 | 없음 | 설계만(메뉴 NA, `app-shell.js` items pending) | — | — | NOT_AVAILABLE | — | app_nav_ia |
| 1.4 구조 트리(축·요인·비중·규칙) | 엔진 상수 `QgvV2.WEIGHTS`·`SecQgv2.SUBMETRICS`(`ia-screens.js:44-63`) | 연결 완료 · 코드 | calc_version·코드 변경 | 엔진 값 그대로 | — | 숫자를 따로 적지 않음(:3-4) | app_nav_ia |
| 1.4 예시 값 | sec-qgv2.json에서 코드 순서 첫 LIVE 행(`ia-screens.js:64-84`) | 연결 완료 · 공개 | 일일 실행(재계산 포함) · R | 파일 as_of · 수집 · FY, 동종 기준·수 | 파일 없음·LIVE 행 없음 → NA와 이유 | 예시는 추천 아님 | **update_propagation**(행·값·as_of 일치) |

**2026-10-21 추가 — SIC 업종군·기업 유형 표시 필터:** `leaderboard-screen.js`의 `classificationOf/filterClassifications`를 `app.js`의 기존 검색·관심·그룹·TARGET 필터와 AND로 연결했다. TARGET은 `company-classification.json`의 업종군과 `company-types-pricefree.json`의 소속도, Universe 코드는 정규화된 `sec-qgv2.json`의 게시 업종군과 기존 `QgvScores.typeMemberships`를 쓴다. 유형 선택은 기업 화면과 같은 `CompanyScreen.selectTypes` 규칙이다. 산업·전략 테마·투자 유형 및 재무 프로필을 서로 대체하지 않으며 새 매핑·임계값을 만들지 않는다.

원래 행 객체의 부분 배열만 표시한다. 전체 모집단·공식 점수·순위·N10/N15/N20 모델 후보 계산은 그대로다. 자료 없음, 확보된 소속도 기준 선택 유형 없음, 식별 철회 행을 구분한다. 선택은 RAM이며 APPLIED/REJUDGE 뒤 새 자료에 적용하고 FAILED 때 이전 자료를 유지한다. 필터 요약에도 선택을 표시한다. 시험: `qgv_classification_filters_node_test.js`, `qgv_classification_filters_browser_test.js`(§7-6). 수익률 기간 선택과 별도 SIC·유형 표 열까지 구현했다는 뜻은 아니다.

### 3-2. 기술적 분석(2.x)

| 요소 | 출처 → 소비 | 상태·저장 | 계기·재취득 | 시각·버전 | 없음·실패 | 바뀌면 안 되는 것 | 시험 |
|---|---|---|---|---|---|---|---|
| 2.1 일봉 차트·지표 | 비공개 Worker 일봉(누를 때, RAM) 또는 비공개 시트 Prices_D(`app.js:899`, `private-history.js:69`, `price-store.js:12`) | 연결 완료 · 기기 계산 / 비공개 시트 | 기기 가격 갱신·사용자 조작 | 가격 기준 RAW_CLOSE / PROVIDER_ADJUSTED_CLOSE, 마지막 봉 날짜 | Worker 미설정·로그인 필요 사유 | 공개 파일에 가격 없음 | technical_chart, private_history |
| 2.1 봉 색(한국식·미국식) | localStorage `candle-style`(`theme-boot.js:23-27`) | 연결 완료 · 기기 저장 | 사용자 조작(설정) | — | 기본 한국식 | 자료·점수 | app_nav_ia, update_propagation(바꿔도 순위 같음) |
| 2.2 차트 패턴 · 2.3 내 노트 | 없음(`ia-screens.js:213-219`) | 설계만 | — | — | NOT_AVAILABLE과 필요한 결정 | — | app_nav_ia |
| 2.4 구조 트리 | 코드 상수(`ia-screens.js:86-97`) | 연결 완료 | 코드 변경 | — | 예시 값 없음(가격은 공개 안 함) | — | app_nav_ia |

**2026-10-21 정정 — 기존 차트 기능으로 메뉴 연결:** 위 2.2·2.3의 “설계만”은 초판 기록이다. 현재 `#technical-pattern/<id>`는 기존 Workbench의 `[data-pattern-panel]`, `#technical-notes/<id>`는 `[data-user-panel]`로 초점·스크롤을 옮긴다. 같은 명시적 기업의 2.1↔2.2↔2.3 이동은 차트 마운트와 RAM 자료·결과를 유지하며, 선택기 변경 뒤 링크도 새 기업을 따른다. 다른 기업·다른 화면·비공개 세션 정리와 bare `#technical` 진입은 기존 정리 경로를 따른다. 이 연결 자체는 가격을 새로 요청하지 않는다.

지표 표시 켜기/끄기와 패턴 매개변수·정도 설정을 구분한다. 기존 패턴·감지 이력·내 노트로의 연결이며, 형태 적합도를 상승 확률로 해석하거나 확률 시나리오를 새로 산출하지 않는다. 시험: `implemented_navigation_browser_test.js` 및 기존 `private_history_browser_test.js`; 메뉴·RAM 유지 근거는 §7-6.

### 3-3. 매크로(3.x)

| 요소 | 출처 → 소비 | 상태·저장 | 계기·재취득 | 시각·버전 | 없음·STALE·실패 | 바뀌면 안 되는 것 | 시험 |
|---|---|---|---|---|---|---|---|
| 3 경고등 공개 3개 | macro-screen.json `macro_lights_v1`(`macro-lights.js:148-165,168-185,231-258`) | 연결 완료 · 공개 | 일일 실행, 값은 발표 기준 · R | 관측 기간(월·일), 규칙 v1 · UNCALIBRATED | 자료 없음 + 사유 코드, 판정에서 뺌 | 매도 판단에 쓰지 않음(:6) | **update_propagation**(곡선 관측 변경 반영, 고용·물가 그대로), macro_lights |
| 3 경고등 기기 2개 | SPY·HYG·IEF Worker 일봉(`macro-lights.js:203-221`) | 부분 연결 · 기기 계산 | 사용자 "불러오기" | 마지막 봉 날짜 | 신용은 허용 목록 전 확인 불가 | 저장·전송 없음 | macro_lights |
| 3 정상·경고·위기 판정 | 위 5개 합(`macro-lights.js:127,177-185`) | 연결 완료 · 기기 계산 | 위 둘 중 하나가 바뀔 때 | v1 · UNCALIBRATED | 가용 3개 미만이면 "판정 신뢰도 낮음" | 플레이북 관문은 꺼져 있어 참고 표시 | macro_lights |
| 3 상태판 8축 · 예시 값 | macro-screen.json observations(`ia-screens.js:113-120`) | 부분 연결 · 공개 | 일일 실행, 발표 기준 | 관측 기간, available_at = **수집 상한**(실제 발표 시각 아님, IA-16) | 관측 없으면 NA | 하나로 합치지 않음 | app_nav_ia |
| 3.1~3.5 | 없음(`ia-screens.js:220-229`) | 설계만 | — | — | NOT_AVAILABLE · 점·선·확률 그리지 않음 | — | app_nav_ia |

**2026-10-21 정정 — 3.1·3.3·3.4 메뉴 연결:** 초판의 “3.1~3.5 설계만”을 모든 조작의 현재 상태로 읽지 않는다. `app.js`의 `focusImplementedSection`이 3.3을 기존 산업 링, 3.4를 현재 링의 내 위치 입력으로 연결한다. 3.1 복귀는 산업에서 경기 보기로 바꾸되 이미 시장 보기이면 유지하며, MacroEvidence도 같은 경기/시장 선택을 따른다. 근거 영역은 `#macro-cycle` 안에 있다. 이는 기존 화면·선택 연결이며 새로운 공식 국면·확률·게이트 활성화가 아니다. 3.2 순환매·3.5 연쇄 효과를 구현했다는 뜻도 아니다. 시험: `implemented_navigation_browser_test.js`(§7-6).

### 3-4. 뉴스·공시·관계(4.x)

| 요소 | 출처 → 소비 | 상태·저장 | 계기·재취득 | 시각 | 없음·STALE | 바뀌면 안 되는 것 | 시험 |
|---|---|---|---|---|---|---|---|
| 4.2 공시·뉴스 목록 | sec-disclosures.json + news-signals.json + dart(`news-signals.js:123-132`, `app.js:401-404`) | 연결 완료 · 공개 | 일일 실행 · 페이지당 한 번 | 파일 as_of, 행마다 발표·수집 시각(근거 보기) | 48시간 지나면 "STALE · 수집 갱신 시각 경과". 출처마다 '새 뉴스 없음 · 확인 t' 또는 '이전 자료 유지 · 마지막 성공 t · 최근 갱신 실패(출처 코드, t)'(`news-signals.js` refreshText) | score_effect NONE: 점수에 반영 안 함 | **update_propagation**(목록·as_of 일치, 삭제 반영), news_signals, sec_disclosures |
| 4.2 필터 | sessionStorage `news-filters`(`news-signals.js:103`) | 연결 완료 · 기기 저장(탭) | 사용자 조작 | — | — | 자료 | news_signals |
| 4.3 트리 예시 | 같은 두 파일을 **매번 다시 읽음**(`ia-screens.js:132-141`) | 연결 완료 · 공개 | 화면을 열 때마다 | 파일 as_of | 읽기 실패 → NA | — | app_nav_ia |
| 4.1 관계망 | 없음(`ia-screens.js:126`) | 설계만(REL-SOURCE) | — | — | NOT_AVAILABLE | — | app_nav_ia |

### 3-5. 포트폴리오·보고(5.x)

| 요소 | 출처 → 소비 | 상태·저장 | 계기 | 시각 | 없음 | 바뀌면 안 되는 것 | 시험 |
|---|---|---|---|---|---|---|---|
| 5.1 확정 목표(TARGET) | actual-catalog.json(`ia-screens.js:154-160`) | 연결 완료 · 공개 | 코드 변경 | target_root_version | 읽기 실패 → NA | 보유가 아님 | app_nav_ia |
| 5.1 실제 보유 | IndexedDB(`device-actual.js:18,187`) | 연결 완료 · 기기 저장 | 사용자 입력 | 입력 시각 | 없으면 비움 | 공개하지 않음·예시로 쓰지 않음(`ia-screens.js:156`) | device_actual, holdings_capture |
| 5.1 모의(세트 A~D, SHADOW) | 비공개 시트 VirtualMeta·장부 + 기기 가격 | 연결 완료 · 비공개 시트 | 러너 실행·사용자 조작 | 장부 세션 날짜 | 장부 없으면 보고 불가 사유 | 실거래 아님. 장부는 추가만 | virtual_trading_* |
| 5.1 모델 포트폴리오 | 없음 | 미구현 | — | — | NOT_AVAILABLE | — | — |
| 5.2·5.3 일일 보고 | 장부·가격·보유·공개 Q·G(`daily-report.js:1-4`) | 연결 완료 · 기기 계산 + 비공개 시트 | 사용자 조작·장부 갱신 | 템플릿 v1 · 지침 v1 | — | 금액 기본 숨김(`report-amounts-hidden`) | daily_report |
| 5.2 보고 불가 카드 | 모델의 상태·사유 코드(`daily-report.js:329-345,446`) | 연결 완료 · 기기 계산 | 같은 모델이 바뀔 때 | 사유 코드·날짜·버전만 | 숫자를 채우지 않음("숫자를 채우지 않음" 배지) | 금액·수량·수익률을 만들지 않음 | daily_report |
| 5.2 AI 답변 보관 | localStorage `report-ai-answers` | 연결 완료 · 기기 저장 | 사용자 조작 | 보관 시각 | — | 공식 증거로 쓰지 않음 | daily_report |

**2026-10-21 정정 — 모델 안내:** 위 “모델 포트폴리오 미구현” 행의 생성기 없음 안내는 `portfolio-screen.js`의 기존 QGV N10·N15·N20 공식 평가 참고와 리더보드 링크로 바뀌었다. `REFERENCE`는 참고 연결 상태이며 이 화면에서 실제 선정·READY·확정 포트폴리오를 판정하지 않는다. 가격/V·공식 순위와 기존 자격 요건이 부족하면 선정하지 않으며 개인 프리셋·표시 필터는 공식 후보를 바꾸지 않는다. TARGET 확정이나 MODEL/TARGET/ACTUAL 대체는 이 변경에 포함하지 않는다. 시험: `qgv_classification_filters_*`(§7-6).

### 3-6. 프롬프트(6) · 구조 트리(n) · Lab(n+1) · 설정

| 요소 | 출처 → 소비 | 상태·저장 | 계기 | 시각·버전 | 없음 | 바뀌면 안 되는 것 | 시험 |
|---|---|---|---|---|---|---|---|
| 6 공식 카탈로그 | research.html 동결본(PLV1, `research-bridge.js:46,60`, `ia-screens.js:191`) | 연결 완료 · 코드 | 새 카탈로그 버전(소유자 승인) | 카탈로그 버전 | 영역 없으면 안내(:145) | 원문은 개인 사본으로 바뀌지 않음 | prompt_field_guide, web_research_guard |
| 6 ★ · 내 사본 | localStorage `prompt-favorites` · `prompt-personal-copies`(`research-bridge.js:138`) | 연결 완료 · 기기 저장 | 사용자 조작 | — | — | 공식 카탈로그 | web_research_guard |
| n 전체 트리 예시 | 공개 파일 수·as_of(`ia-screens.js:181-195`) | 연결 완료 · 공개 | 일일 실행 · R(공시만 매번) | 파일 as_of | NA와 이유 | — | app_nav_ia |
| n+1.2 전진 검증 장부 | forward-validation-ledger.json(`forward-validation.js:6,17`) | 연결 완료 · 공개(가격 없음) + 기기 계산(수익률) | 일일 실행, **추가만**(배포 가드가 기존 기록 불변 확인) | 세션 날짜, calc_version, 시작 2026-10-19 | 7일 넘은 행 ROW_DATA_STALE | 과거 기록을 고치지 않음. 수익률 저장·전송 안 함 | forward_validation |
| n+1.1 백테스트 | 없음(`screen-detail.js:36-46` 비활성) | 설계만 | — | — | 비활성 | — | screens_gaps |
| 설정 · 언어 | localStorage `settings`(`locale.js:8`) | 연결 완료 · 기기 저장(백업 포함) | 사용자 조작 | — | 저장 불가 시 내보내기 안내 | 자료 | settings_import |
| 설정 · 테마 | localStorage `theme`(`theme-boot.js:1-7`) | 연결 완료 · 기기 저장 | 사용자 조작 | — | 시스템 설정 | 자료·계산 | update_propagation, design_* |
| 설정 · Google 시트 연결·Universe 시트 ID·가격 저장 켜기 | localStorage `unified-sheet-source` · `universe-source` · `price-store-enabled`(백업 제외) | 연결 완료 · 기기 저장(설정) + 비공개 시트(내용) | 사용자 조작 | — | 연결 전 NOT_AVAILABLE | 공개 파일 | google_sheet_* |
| 설정 · Worker 주소 | localStorage `private-history-origin`(`private-history.js:69`) | 연결 완료 · 기기 저장 | 사용자 조작 | — | 허용 주소와 다르면 ORIGIN_UNAPPROVED | — | private_history |
| 설정 · 운영 상태 | 공개 파일 메타(`ops-status.js:1-48`) | 연결 완료 · 공개 | 일일 실행 · R | 파일마다 as_of·stale 기준 | 파일 없음 | 새 기준을 만들지 않음 | ops_status |

**2026-10-21 추가 — 7.1.2 선택 기업:** `app.js`는 명시적 기업/분석/기술 경로와 기술 기업 선택기의 ID만 탭 RAM에 기억한다. 기존 `research_public_context` 요청·응답은 양쪽 모두 같은 origin과 정확한 부모/현재 iframe source를 확인한다. 공개 회사 목록·identity catalog 또는 검토된 Universe 이름표에서 확인한 `company_id/ticker/name`만 `selection.company`로 보낸다. 알 수 없는 ID·상충한 identity는 null이며, 암묵적 기본 ASML이나 첫 목록 행으로 추정하지 않는다. 회사명이 없으면 회사명·티커 쌍의 가져오기는 막고, 티커만 선언된 프롬프트는 확인된 티커를 쓸 수 있다.

`research-bridge.js`의 “선택 기업 가져오기”는 선택한 Frozen 프롬프트에 선언된 company/ticker 또는 seed_company/seed_ticker의 빈 칸만 한 쌍으로 채운다. 둘 중 하나라도 입력되어 있으면 쌍 전체를 보존한다. context 도착·갱신·기업 변경은 자동 입력하지 않는다. 미리보기는 기존 input 검증 경로를 쓰며 기준일·분석 JSON·입력 모드는 채우지 않는다. 사용자 입력을 부모로 보내거나 새 저장소에 저장하지 않는다. iframe 이탈·프롬프트 전환 시 기존 form 초기화는 그대로다.

기간은 수동 입력이다. 화면 문구: “프롬프트마다 기간의 뜻이 달라 자동으로 옮기지 않습니다. 필요한 기간은 직접 입력합니다.” Frozen의 기술 자료 `period`, 거시 전망 `horizon`, 회계 `earnings_period`, PIT `as_of/prior_cutoff`와 차트 표시 범위 사이의 자동 매핑은 없다. `selection.period`는 null이다. 기존 카탈로그·필드 안내·공개 분석 6개 가져오기·필수 검사·복사는 유지하며, 가격·보유·개인 입력 전달이나 AI 호출·계정 연결을 추가하지 않는다. 시험: `prompt_selected_context_test.js`, `prompt_selected_context_browser_test.js`(통합 상태는 §7-6).

**2026-10-21 추가 — Lab 메뉴:** `#validation-backtest`와 `#validation-forward`는 각각 기존 9.1·9.2 영역으로 초점·스크롤을 옮긴다. 전진 장부는 9.2 안에 유지한다. 이 메뉴 연결이 백테스트 엔진·새 실험·판정의 구현을 뜻하지 않는다. 시험: `implemented_navigation_browser_test.js`.

## 4. 아직 안 만든 것 — 만들 때 동적이어야 하는 것

새 계산 방법·수집 확장은 여기서 하지 않는다. 기존 결정 대기 항목(USER_DECISIONS_PENDING, IA 후보)에 묶는다.

**2026-10-21 읽기 정정:** 아래는 초판의 설계·미구현 목록이다. 기존 패턴/노트·매크로 링으로의 메뉴 연결과 모델 참고 안내의 현재 상태는 §3-2·§3-3·§3-5를 우선한다. 연결 완료를 새로운 확률·모델·TARGET 확정 완료로 확대하지 않는다.

- **3.1 경기·시장 위치 + 근거선**(IA-4, IA-16):
  - 위치·근거선·조건·확률을 **실행마다 다시 계산**한다. 화면에 고정 좌표를 쓰지 않는다.
  - 표시점(마커)은 곡선 위에서 규칙 출력으로 계산한다. 그림 좌표를 손으로 정하지 않는다.
  - 지난 위치는 장부에 **추가만** 한다. 새 규칙이나 새 자료로 과거 위치를 다시 쓰지 않는다(back-fill 금지). 규칙이 바뀌면 새 버전 열을 따로 쌓는다.
  - 근거선의 시각은 실제 발표 시각이어야 한다. 지금 공개 파일은 수집 상한(available_at)만 있다(IA-16).
  - 근거선 후보 지표·결정(MEV-1 등)은 [MACRO_EVIDENCE_LINES_CATALOG_20261018](macro/MACRO_EVIDENCE_LINES_CATALOG_20261018.md)을 따른다. 문서 병합만으로 어떤 지표도 화면에 켜지지 않는다.
- **3.2 순환매**(IA-5) · **3.3 산업 사이클(SIC)**:
  - 3.3의 키는 QGV와 같은 industry_group(`sic_industry_groups/v0`)이다(`ia-screens.js:226`). SIC 그룹 선택은 사용자 조작, 값은 매 실행 계산이다.
  - 확률 근거는 과거 국면 전환 빈도와 표본 수다. Lab 검증 전에는 미산출로 둔다.
- **3.4 내가 고른 위치**(IA-6, DRAW-STORE): 시스템 값과 따로 저장한다. 점수에 쓰지 않는다. 저장 위치(이 브라우저 / 비공개 시트 / 계정)는 결정 대기다.
- **3.5 연쇄 효과 지도**(REL-SOURCE): 확인된 관계·추론·가설을 나눈다. 고리마다 근거·시차·반증 필드. 방향·크기·확률을 만들지 않는다.
- **2.2 차트 패턴**(TA-G1~G3): 상태 FORMED·CONFIRMED·FAILED·INVALIDATED·EXPIRED는 새 봉이 올 때마다 다시 판정한다. 확률은 같은 패턴·정도의 과거 결과 빈도뿐이다.
- **2.3 내 노트**(DRAW-STORE): 좌표 기준은 종목·봉 주기·가격 기준·시간/가격(chart-annotation/1). 봉 주기나 가격 기준이 바뀌면 다시 그린다. 공식 증거가 아니다.
- **4.1 관계망**(REL-SOURCE): 관계 자료에도 as_of·출처·수집 시각을 붙인다. 관계가 사라지면 지우지 않고 종료 시각을 남긴다.
- **1.1 수익률 기간 열**(기간 정의 결정 필요): 기기 가격에서만 계산한다. 마지막 봉 날짜와 가격 기준을 같이 쓴다.
- **5.1 모델 포트폴리오**: 생성기가 없다. 만들 때 입력 as_of와 생성 규칙 버전을 같이 보여 준다.
- **스탯창(레이더)**: 코드는 PR #311에 있다(병합 대기). 병합되면 §3-0 표의 계약이 그대로 적용된다.

## 5. 매크로 위치 — 네 층을 나눈다

데이터로 계산한 좌표는 검증된 국면 추정이 아니다. 화면은 아래 네 층을 섞지 않는다.

| 층 | 뜻 | 지금 | 갱신 | 필요한 표시 |
|---|---|---|---|---|
| 교육용 개념도 | 경기 순환 곡선 그림. 특정 날짜 판단이 아님 | 없음 | 바뀌지 않음 | "개념도 · 현재 위치 아님" |
| 시스템 추정 | 규칙이 계산한 현재 위치 | **없음**(3.1 NOT_AVAILABLE, `ia-screens.js:223`) | 실행마다 다시 계산 | 규칙 id·버전, 입력 계열과 관측 기간·발표 시각, 불확실성(표본 수·전환 빈도), UNCALIBRATED 표시 |
| 사용자 판단 | 사용자가 고른 위치 | 없음(3.4) | 사용자 조작 | 저장 위치·시각, "점수에 쓰지 않음" |
| 과거 기록 | 지난 실행의 시스템 추정 | 없음 | 추가만 | 그 당시 규칙 버전과 입력 as_of 그대로 |

- 위치 규칙·버전·근거·불확실성은 한 묶음으로 게시한다. 근거 없는 위치나 불확실성 없는 확률은 그리지 않는다.
- 지금 있는 것은 경고등 v1과 상태판뿐이다. 이것을 위치처럼 그리지 않는다.

## 6. 개인화 — 목표 구조와 현재

### 6-1. 목표 조회 순서

1. 계정 설정이 있으면 그것.
2. 없으면 이 브라우저 설정.
3. 없으면 개발자 기본값.

- 로그인할 때 이 브라우저 설정으로 계정을 자동 덮어쓸지는 **별도 동기화 정책**이다. 결정되지 않았다.
- 개발자 기본값은 보유·잔고·거래를 지어내지 않는다. 예시 포트폴리오는 "예시"라고 분명히 표시한다.

### 6-2. 현재

- 계정 층이 없다(§1-6). 실제 순서는 **이 브라우저 → 개발자 기본값** 두 단계다.
- 개발자 기본값: `profile-defaults.js`, `type-config-defaults.js`, `playbook-config-defaults.js`, `dcf-parameters-defaults.js`, `scoring-default.js`, 프리셋 후보 v0.1(`device-profiles.js:143-148`). 보유·거래 기본값은 없다. 실제 보유는 사용자가 입력하기 전까지 비어 있다.
- 모의 세트 A~D는 "모의"로, 확정 목표(TARGET)는 "확정 목표 · 보유 아님"으로 표시한다(`ia-screens.js:146-159`).
- 리더보드 프리셋 칩은 저장되지 않는다(RAM, `app.js:657`). 새로고침하면 균형으로 돌아간다.
- 저장한 개인 v2 프로필은 공식 결과와 다른 키(`personal`)로만 계산한다(`device-profiles.js:136-139`). 백업에 들어가지 않는다.
- 비공개 시트에 있는 것: Universe 시세 탭, 가격 탭 Prices_D/Prices_M, 가상 장부·VirtualMeta, 보고 우편함, 거래 원천. 이것은 사용자 Google 계정의 파일이다.

## 7. 검증 — `update_propagation_browser_test.js`

### 7-1. 무엇을 하나

같은 빌드에 합성 "게시일" 두 개를 경로 가로채기로 준다. 브라우저 시계는 날마다 고정한다. 가격·실제 자료·외부 요청은 없다.

- 1일차: 엄격 합성 sec-qgv2.json(`qgv_v2_fixture.strictPayload`) + NYSE:ABT 수집 시각 2026-09-30(아직 LIVE).
- 2일차(Python merge와 같은 방식으로 만든 다음 게시본):
  - as_of +1일, last_shard_index +1.
  - TARGET msft 재수집(acquired_at = 2일차 as_of), SEC 지표 개선 → 순위 3 → 1.
  - NASDAQ:AKAM 재수집, Q 세부 지표 다섯 개 없음 → Q 정책상 NA(AXIS_COVERAGE_BELOW_50).
  - 전체 재계산(`SecQgv2.scoreRows`) → 재수집 안 한 NASDAQ:ABNB의 Q가 바뀌고 수집 시각은 그대로.
  - NYSE:ABT는 수집 없이 14일을 넘겨 STALE.
  - 공시 파일에서 AMD 8-K, 뉴스 파일에서 AMD 기사 하나 삭제.
  - macro-screen.json 곡선 관측 변경(켜짐 → 꺼짐). 고용·물가는 새 발표 없음.

### 7-2. 증명 범위 — 세 수준

이 시험이 증명하는 것과 증명하지 않는 것을 나눈다. **checks=207은 자동 갱신이 완성됐다는 뜻이 아니다.**

| 수준 | 내용 | 이 시험 |
|---|---|---|
| (a) 시험이 넣은 새 자료 | 하네스가 제공 파일(게시본)을 1일차에서 2일차로 바꿔 끼운다. 실제 수집·배포를 거치지 않는다 | 증명함(합성 자료 기준) |
| (b) 실제 새로고침 경로 | 실제 브라우저가 새로고침(`reload`)·이동(`goto`)으로 파일을 다시 받는다. 서비스 워커를 켠 상태에서 Cache Storage에 데이터 JSON이 없는지도 본다 | 증명함 |
| (c) 탭 안 갱신 | 탭 안 새로고침, 새로고침 없는 캐시 무효화, 자동 갱신 | **증명하지 않음.** 이 기능들은 아직 없다(D1, D2). 시험은 지금 상태를 기록만 한다(`SPA_REFRESH … KEPT_UNTIL_RELOAD`, `GAP in-tab state frozen at load`) |

### 7-3. 확인하는 것(값이 **같아야** 함, 문자열 존재만 보지 않음)

- 리더보드: 순서·순위·총점이 Node에서 같은 엔진으로 계산한 기대값과 같다. 점수 기준 배지 = 파일 as_of.
- TARGET msft 화면: 점수 기준 배지, Q·G 숫자, 수집 시각, 순위.
- Universe 화면 3개: 출처 줄 전체(as_of · 수집 · 수집 후 일수 · 상태 · calc_version)가 원천 값과 같다. Q·G·요인 10개 일치. 정책상 NA는 사유가 있고 숫자가 없다. STALE 표시.
- 1.4 예시: 고른 행·Q·G·요인·as_of·수집·FY.
- 레이더: 페이지에 있으면 Q·G 꼭짓점 = 공개 축 점수(NA 포함). 기준 브랜치에는 없어서 건너뛰고 기록한다. `claude/fe-stat-radar` 빌드에서는 6페이지 모두 통과했다.
- 공시·뉴스 목록 = 그날 파일의 타임라인, 두 파일 as_of 일치, 삭제된 항목 사라짐.
- 매크로 곡선 경고등 상태·값·관측일. 고용·물가 관측 기간은 그대로.
- 1일차 값이 남지 않음: msft 1일차 총점, ABNB의 1일차 Q·as_of, 삭제된 공시.
- 탭을 연 채 새 게시: 화면이 한 게시본(as_of와 순위가 같은 날)만 보여 주는지. 새 게시본으로 바뀌는지는 보지 않는다(수준 c).
- 새 파일 읽기 실패(503) 뒤 새로고침: 점수 기준 NOT_AVAILABLE, 순위 0개, 기업 화면 NO_FILE·NA. 옛 값 없음.
- 이름 표 변경 + 테마·봉 색 + 저장한 개인 프로필: 공식 순위·총점·as_of가 그대로이고 바뀐 이름만 보인다.
- 실제 서비스 워커를 켠 상태: 새로고침 뒤 2일차 as_of, Cache Storage에 데이터 JSON 없음.
- 정적: 서비스 워커 사전 캐시에 데이터 파일 없음, 다른 요청은 그대로 통과, `updateViaCache:'none'`, 모든 같은 출처 `fetch(`에 no-store/no-cache.

### 7-4. 결과(이 브랜치)

- 기준 빌드: `UPDATE_PROPAGATION_BROWSER_OK checks=207 radar_pages=0`.
- `claude/fe-stat-radar` 빌드: `checks=219 radar_pages=6`.
- 함께 돌린 기존 시험 통과: app_nav_ia, universe_company, company_names, qgv_v2_screens.

### 7-5. 남은 미검증

- 수준 (c) 전체: 탭 안 새로고침, 새로고침 없는 캐시 무효화, 자동 갱신, 시간 경과에 따른 STALE 재판정(D1, D2, D5, D6).
- 실제 GitHub Pages CDN 캐시 시간(배포 직후 몇 분).
- 13F 날짜 세 가지가 화면에서 서로 구분되는지(파일 검증은 있음, 화면 문구 시험 없음).
- 기기 V·가격 축의 기기 가격 갱신 경로(합성 시세 시험은 qgv_v2_screens에 있음, 날짜 전환 시험은 없음).
- DART·분류·로고 파일의 날짜 전환.
- calc_version이 바뀌는 날의 화면(CALC_VERSION_MISMATCH 표시는 다른 시험이 다룸, 두 날 전환은 없음).

### 7-6. 2026-10-21 추가 — 이번 연결의 시험 상태

초판 §7-1~7-5의 결과와 미검증 기록은 당시 범위다. 아래는 Main 통합 source `fa6dd669`의 별도 기록이다. `/workspace/investment-frontend-final`은 production 빌드에 고정 10/20 공개 자료를 결합했으며, 통합 검사는 그 빌드가 실제 생성한 `research.html`을 사용했다. 문서 작업에서 시험을 재실행하지 않았다.

| 범위 | 시험과 확인 근거 | 상태 |
|---|---|---|
| 기존 메뉴 → 차트·링·Lab, 같은 기업 RAM 유지 | `implemented_navigation_browser_test.js` 390/1280 × light/dark; frontend links 독립 리뷰의 40 checks 및 좁은 RAM 검사 6개 | 검토한 연결에서 PASS. 전체 최신 통합·실사이트 결과로 확대하지 않음 |
| G3 목록 복귀·G8 홈 갱신 | `search_continuity_browser_test.js`: 목록별 상태, 30→60개 더 보기, 그룹 변경, 홈 APPLIED/FAILED와 활성 검색 상태 | Main 통합 결과 12 시나리오 / 120 assertions PASS |
| QGV 분류 표시·모델 참고 안내 | `qgv_classification_filters_browser_test.js`: 필터 교집합, 결측, 공식 결과 불변, 선택 소멸, APPLIED/FAILED/REJUDGE; Node 시험은 기존 규칙과 25개 필터 조합 불변 확인 | Main 통합 브라우저 60 PASS. 작업자 Node 관련 24 PASS |
| 프롬프트 선택 기업 | `prompt_selected_context_test.js`: 공개 identity·충돌·결측·접근 경계; `prompt_selected_context_browser_test.js`: 390/1280 × ko/en, 실제 선택·가져오기·편집 보존·origin/source 거부 | Main 통합 projection 15 PASS·브라우저 152 checks / 4조합 PASS. Darwin 독립 APPROVE(작업자 코드 + app 제안에서 독립 15·152 및 추가 9 checks PASS) |
| 기존 프롬프트 기능 | `prompt_field_guide_browser_test.js`, `test_prompt_field_guide.py`, `test_prompt_library_v1.py` | Main 통합 관련 Python 41 PASS. 이전 작업자 검사: 안내 16,833 checks·변수/카탈로그 Python 26 PASS. 최종 안내 문구는 통합 브라우저 152 checks에 포함 |

통합 검사는 위 production 빌드 + 고정 공개 자료와 시험별 합성 fixture로 수행됐다. Darwin 독립 결과는 `/workspace/prompt-context-review-20261021.md`의 범위이며, 전체 통합판에 대한 독립 승인으로 확대하지 않는다. 실제 가격·개인 보유·계정 연결, 배포 및 운영 사이트 완료를 증명하지 않는다. 새 기간 매핑·방법론·TARGET 확정을 추가하지 않는다.

## 8. 발견된 결함

화면만 바꾸면 되는 작은 결함도 이번에는 고치지 않았다. D3 수정을 시도했지만 `pages_artifact_guard.py`의 자산 해시 재고정이 권한 검사에서 거부되어 되돌렸다. 아래는 모두 보고만 한다.

### 8-1. 우선순위·담당·완료 조건(Main 결정, 2026-10-18)

| 결함 | 우선순위 | 담당(PR·브랜치) | 완료 조건 |
|---|---|---|---|
| D10 | P1 | 새 PR `claude/fe-price-time` | 모든 가격 배지에서 읽은 시각과 가격 거래일·거래 시각이 따로 보인다. 거래 시각이 없으면 '가격 기준 시각 미확인'이라 쓴다. 신선도 판정에 읽은 시각을 쓰지 않는다. 실제 "Universe 읽기"와 Worker 가격 경로를 움직이는 브라우저 시험으로 **실제 사용자 경로 검증**을 한다 |
| D11 | P1 | 새 PR `claude/fe-qgv-rank-split` | 승인된 규칙의 구현 결함이다. 새 결정이 아니다. 공식 QGV 순위에는 V가 계산된 행만 들어간다. 따로 'QG 참고 목록'이 있다. 모든 기업은 검색·상세로 계속 찾아갈 수 있다. 개인 V 비중 0 결과는 '개인'으로 표시한다. 공식 공식은 그대로다(엔진 출력 동일). 브라우저 시험으로 **실제 사용자 경로 검증**을 한다 |
| D1, D2, D5, D6 | P2 | 새 PR `claude/fe-data-refresh` | 사용자 '자료 새로고침' 버튼이 공개 파일만 다시 읽는다(비공개 가격 요청 없음, 설정 초기화 없음). 모든 화면과 캐시가 한 게시본을 쓴다. 실패하면 옛 값을 두고 실패와 옛 기준 시각을 보인다. 새 게시 없이도 시간이 지나면 파일마다 자기 규칙으로 STALE을 다시 판정한다. 페이지 새로고침 없이 실제 브라우저에서 **실제 사용자 경로 검증**을 한다 |
| D3 | P3 | Main · 자산 해시 재고정은 소유자 승인 대기(제품 방향 "개수는 자료에서 계산"은 승인됨) | 각주 개수가 자료에서 계산되고 해시 재고정이 승인·반영된다 |
| D4 | P3 | `claude/fe-data-refresh` | 배지가 입력(v1)을 밝히거나, v2 배지 옆에서 없어진다 |
| D7 | P4 | 나중의 작은 화면 PR | 검색 라벨이 수동 검토 표를 따른다 |
| D8 | P3 | IA-16 / #313 수집기에 연결(이번 회차 아님) | 근거 시각이 실제 발표 시각이 된다 |
| D9 | P4 | 수집 변경 · 대기열 항목 · 소유자 승인 필요 | 13F 접수 시각이 공개 파일에 들어간다 |

### 8-2. 결함 내용


- **D1 · 열린 탭은 새 게시를 다시 읽지 않고 알리지도 않는다.** 공개 파일은 페이지당 한 번 읽는다(`app.js:1180-1198`, `app.js:401-403`). 각 화면의 as_of는 맞게 보이므로 거짓 표시는 아니다. 다만 "새 자료가 있음"이나 "마지막 확인 시각" 표시가 없다. 시험 기록: `SPA_REFRESH qgv=KEPT_UNTIL_RELOAD news=KEPT_UNTIL_RELOAD`. 앱 단위 재취득 설계가 필요하다. **고침(fe-data-refresh)**: '자료 새로고침' 버튼과 마지막 확인 시각(`data-refresh.js`).
- **D2 · 열린 탭에서는 sec-qgv2 행 상태가 읽은 시점에 굳는다.** LIVE/STALE는 읽을 때 계산한다(`sec-qgv2.js:167-180 restate/toInputs`). "수집 후 N일"은 화면 시각으로 늘어난다(`universe-company.js:41,60-61`). 그래서 14일을 넘긴 뒤에도 "수집 후 14일 · 상태 LIVE"가 보일 수 있다(시험 기록 `GAP in-tab state frozen at load`, 실제 경과 14.9일). 새로고침하면 STALE이 된다. 고치려면 판독기가 stale 기준을 넘겨줘야 해서 화면만의 수정이 아니다. **고침(fe-data-refresh)**: 경계를 지나면 같은 판독기로 다시 판정하고 제자리에서 다시 그린다.
- **D3 · 리더보드 각주의 "19개 기업"이 고정 문자열이다**(`leaderboard-screen.js:149`, 주석 `app.js:646`). 지금은 식별자 19개와 같아 오표시는 아니다. TARGET 구성이 바뀌면 틀린다. 제안: 문구의 19를 `all.length`로 바꾸고 `pages_artifact_guard.py`의 `leaderboard-screen.js` 해시를 다시 고정한다. 같은 고정값이 `universe-company.js:122,124`("TARGET 19개")에도 있다.
- **D4 · TARGET 기업 화면의 "STALE" 배지가 v1 미리보기 입력(sec-qg-factors.json) 기준인데 배지에는 "STALE"만 쓴다**(`company-screen.js:46-49`). 바로 옆이 v2 "점수 기준" 배지라 v2 점수가 오래된 것으로 읽힐 수 있다. 제안: "v1 입력 STALE"로 쓴다(해시 재고정 필요). **고침(fe-data-refresh)**: 배지가 'v1 입력 STALE'이라고 쓴다. 기존 v1 STALE 규칙은 그대로다.
- **D5 · 읽기 실패와 미게시를 구분하지 않는다.** 503이든 404든 리더보드는 "v2 · NOT_AVAILABLE · SEC_QGV2_NOT_AVAILABLE", 기업 화면은 "상태 NO_FILE"이다(`qgv2-inputs.js:82-94`, `universe-company.js:38`). 옛 값을 보여 주지 않는 점은 맞다. "새로 읽기 실패"라는 말은 없다. 판독기의 사유 코드를 나눠야 해서 화면만의 수정이 아니다. **고침(fe-data-refresh)**: 막대와 Universe 기업 화면이 '읽기 실패(HTTP n)'와 '아직 게시되지 않음(HTTP 404)'을 따로 쓴다. 리더보드 사유 코드(qgv-scores.js)는 그대로다.
- **D6 · 같은 탭에서 4.3 트리 예시와 4.2 목록이 서로 다른 게시본을 보일 수 있다.** 예시는 열 때마다 다시 읽고(`ia-screens.js:134`), 목록은 페이지당 한 번이다(`app.js:401-403`). 둘 다 자기 as_of를 쓰므로 거짓 표시는 아니다. **고침(fe-data-refresh)**: 목록 파일은 게시본마다 한 번 읽고 4.2·4.3·홈·플레이북이 같이 쓴다.
- **D7 · 검색 라벨의 한국어 이름 두 개가 코드에 고정돼 있다**(`home-screen.js:30,42`: 한미반도체·도쿄일렉트론). 수동 검토 표(company-names-ko.json)와 출처가 둘이다. 표를 고쳐도 이 라벨은 따라가지 않는다. 표시 전용이라 점수에는 영향이 없다.
- **D8 · 매크로 근거 시각은 실제 발표 시각이 아니다**(release_basis NOT_VERIFIED, `macro/growth_inflation_v0.py:166,178`; 화면은 "수집 상한 시각", `ia-screens.js:118`). 기존 IA-16.
- **D9 · 13F 접수 시각이 공개 파일에 없다.** 제출일(날짜)만 있다(§1-4).
- **D10 · 가격의 읽은 시각이 가격 시각처럼 보일 수 있다.** GOOGLEFINANCE 시세는 거래 시각을 모르면(`time_status` UNKNOWN) `as_of`를 읽은 시각과 같게 둔다(`device-market.js:105-107`). 시세 배지는 `time_status`를 버리고 `as_of`만 쓴다(`company-screen.js:41,274`). 그래서 방금 읽은 옛 가격이 "시세 … · 지금 시각"으로 보인다. Universe 탭 가격(`private-subset.js:78-79`)은 `observed_at`도 읽은 시각이고 화면에 가격 시각 표시가 없다. 제안: 배지·패널에 "읽은 시각"과 "가격 기준 시각(미확인)"을 따로 쓴다(해시 재고정 필요). 에이전트는 시트를 직접 읽지 않는다. 기기 확인은 승인된 "Universe 읽기" 버튼으로만 한다.
- **D11 · Q·G만 있는 총점과 Q·G·V 총점이 한 순위에 섞인다(승인된 규칙의 구현 결함, 새 결정 아님).** 기기 가격이 없는 행·금융업 행은 V 없이 총점이 나와 V가 있는 행과 같이 순위가 매겨진다(`qgv-scores.js:169-207`; 합성 시험에서 가격 없이 nvda·amd·msft가 1~3위). 순위 문구는 "공식 순위 아님"이지만 비교 기준이 다르다는 표시는 없다. 이 문서 브랜치에서는 고치지 않는다(§8-1, `claude/fe-qgv-rank-split`).

## 9. 진행 중·미병합 요소

- 스탯창(레이더): PR #311 `claude/fe-stat-radar`, 병합 대기.
- V 산출 현황(기기) + 공용 `QgvScores.pageResult` / `vCoverage` + 금융업 V 문구 변경: `claude/fe-v-coverage`, 진행 중(이 문서 작성 시 원격 브랜치 없음). 병합되면 §3-0·§3-1 행의 계약을 적용하고 update_propagation에 V 일치 확인을 더한다.

## 10. CI 제안

`implementation/tools/ci_browser_tests.txt` 끝에 다음 줄이 들어갔다(Main 커밋 `1a908691`).

```
update_propagation_browser_test.js
```

이 시험은 필요한 공개 파일을 모두 경로로 바꿔 주므로 PR 빌드와 일일 verify(실제 산출물) 양쪽에서 같은 결과를 낸다. 실행 시간은 1분 안팎이다.
