# 중앙 V 게시 — U4(워크플로)·U5(가드) 승인 요청에 필요한 것 (2026-10-23)

> **상태: 기록 문서.** 이 브랜치(`claude/cv-core-publisher`)는 워크플로·가드를 바꾸지 않는다.
> U1~U3 코드만 있다. 아래는 U4·U5가 그대로 옮겨 쓸 요구 사항이다. 가격 값은 없다.

> **2026-10-24 갱신(PR-A `claude/central-v-core` = #393 + canonical + 이 브랜치):** 소유자 결정(계획 [CENTRAL_V_DC02_PLAN_20261024](CENTRAL_V_DC02_PLAN_20261024.md) 4절, 2026-10-24)이 반영됐다. 아래 본문의 해당 줄도 고쳤다.
> - D2 (a): Secret 두 개 모두 새로 둔다 — `RAW_REPO_READ_TOKEN`(fine-grained, `investment-system1-raw` Contents: read 하나), `QGV_OFFICIAL_HMAC_KEY`. 값은 어디에도 적지 않는다.
> - Secret이 없으면 **`NOT_RUN`**(내려받기 전, 종료 코드 0, 직전 정상본 유지): `HMAC_KEY_MISSING`(16바이트 미만 포함), `MONTHEND_TOKEN_MISSING`(전에는 `SUPPLY_FAILED`였다).
> - 입력 `sec-qgv2.json`의 `calc_version`이 `2026-10-23.1`보다 이르면 `NOT_RUN SEC_QGV2_CALC_VERSION_BEFORE_U7`(U7 규칙은 그 한 번의 올림이 덮는다, D-CV7 (b)·D1 (ii)).
> - D3 수용(전 거래일 기준, 요청일·실제 기준일 둘 다 게시), D4 95% 확정, D6 (a) 현재가 분할 검사 = F_k 근거(§4), D7 ADR = 20-F 제출자까지(§4).
> - C 파서 한 벌(`tools/iex_tops/iex_last_trade.c`), 별칭 표 하나(`providers/iex_hist.SYMBOL_ALIASES`). 프로브·U8 실행 사실: [CENTRAL_V_PROBE_U8_FACTS_20261024](CENTRAL_V_PROBE_U8_FACTS_20261024.md).
> - 아래 `파일:줄` 인용은 cef0748e 기준이다. 줄이 밀렸으면 같은 함수 이름을 본다.

> **2026-10-24 갱신(PR-B `claude/central-v-guard`, PR-A 위):** 2절(U5)과 1-5절의 deploy 신선도를 구현했다. 설계 §12 머리의 구현 메모와 `public_price_boundary/AUDIT.md` §10에 자세히 적었다. 본문과 다른 점:
> - 허용 출처는 정확한 URL 형태로 고정했다(색인, `iex` 버킷의 JSON API·XML API). V4 월말가 저장소 읽기도 같은 경로 규칙을 따른다(저장소 릴리스 API 두 형태, 토큰은 그 URL에만).
> - 호출자 검사는 실행 시점에도 한다: 진입 스크립트가 `tools/qgv_official_publish.py`가 아니면 요청 전에 `SOURCE_ROUTE_NOT_ALLOWED`(게시기 결과는 `SUPPLY_FAILED IEX_SOURCE_ROUTE_NOT_ALLOWED`, 종료 코드 0). 정적 시험이 IEX 호스트·어댑터를 쓰는 파일을 고정한다. U8 도구(PR-E)가 어댑터를 import하면 그 시험의 허용 목록을 소유자 승인과 함께 넓혀야 한다.
> - 신선도: 같은 기준일이면 `inputs_as_of`로 판정한다. 라이브 게시본이 유효한데 아티팩트에 없으면(`MISSING`) D-CV16 (a)와 같게 게시본만 빠지고 배포는 계속한다(거부하지 않음).
> - PR-C에 남은 것: collect "Offline public boundary regression" 단계와 verify에 `tests/test_qgv_official_guards.py` 추가, deploy 단계 주석에 게시본 규칙 추가, D9 이력 업로드 단계가 `RAW_REPO_TOKEN`을 새로 가지면 `test_public_price_boundary.py`의 고정 목록 갱신.

> **2026-10-24 갱신(PR-C `claude/central-v-workflow`, PR-B 위):** 1절(U4)을 구현했다. 1-1~1-6의 요구대로이고, 다른 점은 이렇다.
> - V 단계: C 파서 빌드 실패는 고정 줄 `QGV_OFFICIAL_PARSER_BUILD_FAILED`로 남기고 게시기는 그대로 돈다(`NOT_RUN PARSER_MISSING`, 직전 정상본은 먼저 복사됨). 게시기는 `timeout 12m`, 단계는 15분 한도다. 멈추면 `QGV_OFFICIAL_STEP_STOPPED exit=<코드>`, 반쯤 쓴 파일 삭제, 가드 실행. 월말가 날짜는 단계 `env`의 `QGV_MONTHEND_STAMP: '20261023'`(1-4).
> - 비공개 점수 이력(D9): V 단계 다음 별도 단계(`tools/qgv_official_history.py`, `RAW_REPO_TOKEN`). V 단계가 아티팩트 가드까지 성공했을 때만 돈다(`if: steps.central_v.outcome == 'success'`). 새 게시본 판정은 상태 파일이 OK이고 게시본을 가리키며 `verified_at`이 그 시도 시작 이후인 것이다. 같은 기준일 두 번째 게시본도 같은 태그에 나란히 남는다.
> - verify(1-5): `tools/qgv_official_check.py` + `tests/test_qgv_official.py tests/test_iex_hist.py tests/test_qgv_official_guards.py`. 새 단계라 `continue-on-error`다. collect의 "Offline public boundary regression" 목록에는 더하지 않았다(필수 단계라 실패하면 그날 수집·원장까지 멈춘다).
> - 정적·실행 시험: `tests/test_qgv_official_workflow.py`(단계 위치·`env`·한도, V 단계 셸을 로컬에서 그대로 실행: Secret 없음 → `NOT_RUN`, Secret 있고 출처 없음 → `SUPPLY_FAILED`, 멈춘 게시기 → 단계 종료 코드 0). 첫 게시 절차: [CENTRAL_V_GO_LIVE_CHECKLIST_20261024](CENTRAL_V_GO_LIVE_CHECKLIST_20261024.md).

- 작성: 2026-10-23 11:34 UTC / 2026-10-23 20:34 KST.
- 근거: 설계 [CENTRAL_V_PUBLICATION_DESIGN_20261018](CENTRAL_V_PUBLICATION_DESIGN_20261018.md) §3·§6·§12, GSQ-024.
- 인용은 `파일:줄`이다. `src/`는 `implementation/src/investment_system/`, `tools/`는 `implementation/tools/`다.

## 1. U4 — 워크플로 단계(`sec-daily-public-inputs.yml` collect 잡)

### 1-1. 위치·형태
- 원장 단계 뒤, 분류 단계 앞에 둔다(설계 §3-2, W-F1 규칙 `sec-daily-public-inputs.yml:120-121`).
- `continue-on-error: true`. 도구는 공급·검증 실패에도 종료 코드 0이다(`tools/qgv_official_publish.py` `main`). 사용 오류만 2다.
- 단계 순서:
  1. C 파서 빌드: `cc -O2 -o "$RUNNER_TEMP/iex_last_trade" implementation/tools/iex_tops/iex_last_trade.c`.
  2. `python implementation/tools/qgv_official_publish.py --out "$RUNNER_TEMP/public-cockpit" --parser "$RUNNER_TEMP/iex_last_trade" --monthend-stamp <U8 날짜> --monthend-shards 6`.
  3. 다음 단계의 `pages_artifact_guard.py`가 그대로 돈다.
- node는 이미 collect 잡에 있어야 한다. JS 대조(D-CV12)에 쓴다(`tools/qgv_official_js_check.js`). 없으면 `VERIFY_FAILED JS_TWIN_UNAVAILABLE`이고 직전 정상본을 유지한다.
- 표준 출력은 한 줄뿐이다: `QGV_OFFICIAL attempt=… reason=… published=… basis=… rows=… ranked=… supplied=n/m`. 가격을 읽어 계산까지 간 실행이면 끝에 분할 보조 검사(D6 (b), §4) 개수가 붙는다: `split_checked=… split_flagged=… split_unchecked=… split_unchecked_no_period=… split_gap_skipped=… split_lead_unchecked=…`(2026-10-24 밤, #400; `split_lead_unchecked` 2026-10-25). 가격·URL·키·종목은 없다.

### 1-2. Secret(새로 필요) — **소유자 결정**
| 이름(기본값) | 용도 | 도구 인자 | 결정 |
| --- | --- | --- | --- |
| `QGV_OFFICIAL_HMAC_KEY` | 가격 묶음 HMAC → `publication_id`에만 쓴다(`src/qgv/qgv_official.py` `price_hmac`). 공개하지 않는다 | `--hmac-key-env` | **승인됨(D2, 2026-10-24).** 16바이트 이상. 없으면 `NOT_RUN HMAC_KEY_MISSING` |
| `RAW_REPO_READ_TOKEN` | V4 월말가 비공개 저장소 읽기(`src/providers/iex_monthend.py` `github_call`, `read_store`) | `--raw-token-env` | **(a)로 결정(D2, 2026-10-24).** 없으면 `NOT_RUN MONTHEND_TOKEN_MISSING` |

**(B) RAW_REPO_TOKEN 충돌.** (2026-10-24 소유자 결정 D2: (a).) 설계 §3-3은 "이 단계에 `RAW_REPO_TOKEN`을 주지 않는다"였다. V4 월말가를 읽으려면 비공개 저장소 읽기 권한이 필요하다.
- **(a) 권장:** 비공개 원자료 저장소 `kco994553-star/investment-system1-raw` **읽기 전용** fine-grained 토큰을 새 Secret `RAW_REPO_READ_TOKEN`으로 둔다. 게시 단계 `env`에만 준다. Contents: read 하나만 준다.
- **(b)** 기존 `RAW_REPO_TOKEN`을 이 단계에만 준다. 쓰기 권한까지 같이 간다.
- 쓰지 않는 방식: 가격 임시 파일을 만드는 "별도 단계". 설계 §3-3 위반이다.
- 코드는 토큰 **이름**을 인자로 받는다(`--raw-token-env`). 어느 쪽이든 코드 변경은 없다.
- 토큰은 `api.github.com` 요청에만 붙는다. 자산 다운로드 리디렉트에는 붙이지 않는다(`src/providers/iex_monthend.py:59-61`, `:96`). 시험: `tests/test_iex_hist.py` `_release_call`.
- 토큰이 없으면 `NOT_RUN MONTHEND_TOKEN_MISSING`이고(2026-10-24 전에는 `SUPPLY_FAILED`) 직전 정상본을 유지한다. 내려받기 전에 멈춘다.

### 1-3. 기준일·공급 기준 — **소유자 결정 D3·D4(2026-10-24): 수용**
- **기준일:** IEX 색인에 있는 마지막 TOPS 1.6 날짜 중 `shard_day(시작 시각)` 이하(`src/providers/iex_hist.py` `select_day`). T+1이라 22:17 UTC 실행에서는 보통 **전 거래일**이다. 게시본에는 `price_source.requested_basis_date`(shard_day)와 `basis_date`(실제 IEX 날짜)를 따로 싣는다. 휴장일·주말·T+1·반일 장 시험: `tests/test_iex_hist.py` basis day 절, `tests/test_qgv_official.py` `test_tool_holiday_run_…`.
- **공급 실패 기준(D-CV5):** 95%(`src/qgv/qgv_official.py:45`, `:184`).
  - 분모는 가격과 무관하게 V 자격이 있는 Universe 행이다. 조건: 단면 안, GENERAL, V 입력 있음, USD, ADR·분할 NA 아님.
  - 미달이면 `SUPPLY_FAILED SUPPLY_BELOW_THRESHOLD`이고 직전 정상본을 유지한다.
- 새 IEX 날짜가 라이브 게시본 기준일보다 이르면 교체하지 않는다(`BASIS_OLDER_THAN_OFFICIAL`).

### 1-4. U8 월말가 저장소 날짜
- `--monthend-stamp YYYYMMDD`는 U8 백필 실행일이다(태그 `iex-v4-monthend-YYYYMMDD-shard0..5`). 워크플로 변수로 고정한다.
- 저장소를 읽지 못하면 `SUPPLY_FAILED MONTHEND_<코드>`이고 직전 정상본을 유지한다. V4만 NA로 게시하지 않는다. 그렇게 하면 모든 V 축이 함께 바뀌기 때문이다. 바꾸려면 소유자 결정이 필요하다.
- **남는 과제(U8):** 백필 뒤 새로 끝나는 회계연도 말월은 저장소에 없다. 그 달은 `MONTH_END_PRICE_NOT_AVAILABLE`로 빠진다(공개 사유는 엔진 사유). 주기적 재백필이나 일일 추가가 필요하다. 이번 범위 밖이다.
- U8 계획 도구(`tools/iex_hist/monthend_plan.py` `SYMBOL_ALIASES`)에는 자체 별칭 표가 있다. 단일 표 원칙에 따라 `src/providers/iex_hist.py:63` `SYMBOL_ALIASES`를 import하게 바꿔야 한다(U8 lane). 저장소 기호와 이 표가 다르면 그 달은 `MONTH_END_SYMBOL_MISMATCH`로 빠진다(실패 쪽).

### 1-5. verify·deploy 잡
- verify(가격 없음): `qgv_official.parse(bytes)`(`src/qgv/qgv_official.py:599`, 내부에서 `require_qgv_official` :547)와 `require_status`(:639). 둘 다 가격 없이 돈다. 검사 내용:
  - V 축 = 요인 가중 평균, 종합 = 축·비중·관문
  - 순위 = 종합 순서, CIK당 하나
  - coverage = 행 합계, 크기 ≤ 2 MiB
- 시험 목록에 `tests/test_qgv_official.py tests/test_iex_hist.py`를 더한다. `cc`가 없으면 C 파서 시험은 skip된다.
- deploy 신선도(설계 §12-5): 아티팩트 `times.price_basis_date` < 라이브면 `OLDER`로 거부한다. 같은 `publication_id`면 바이트가 같아야 한다. 상태 파일은 비교하지 않는다. 라이브 게시본 손상은 D-CV16 (a)로 처리한다(게시본만 실패).
- 수동 배포(`cockpit-pages.yml` 보존 단계): `python implementation/tools/qgv_official_publish.py --out "$RUNNER_TEMP/public-cockpit" --preserve-only`. 검증된 라이브 바이트만 복사하고 다시 계산하지 않는다.

### 1-6. 워크플로 정적 시험(설계 §12-3-5)
- 게시 단계에 `actions/upload*`·`actions/cache`·`git push`·`GITHUB_STEP_SUMMARY` 가격 출력이 없어야 한다.
- HMAC·읽기 토큰은 그 단계 `env`에만 있어야 한다.

## 2. U5 — 가드(`tools/pages_artifact_guard.py`)·경계

- `ALLOWED_NAMES`(`pages_artifact_guard.py:183`)에 `qgv-official.json`, `qgv-official-status.json`을 더한다.
- 파일별 검증기(`:355` 패턴):
  - `qgv-official.json` → `qgv_official.require_qgv_official`
  - `qgv-official-status.json` → `qgv_official.require_status`
- **민감 키 예외는 경로 한정이다.** 실제 산출물을 지금 가드 `_inspect_json`(`:247-263`)으로 돌리면 걸리는 키는 `rank` 하나뿐이다(행마다, 시험 universe에서 18건).
  - 예외는 `qgv-official.json`의 `rows.<code>.rank`에만 둔다.
  - `price`·`marketcap`·`cash` 등은 예외 없이 그대로 막는다.
  - 공개 객체 이름은 `price_source`·`price_status`다(키 `price` 아님).
- 검증기는 추가 금지 키를 어디서든 거부한다(`src/qgv/qgv_official.py:57` `FORBIDDEN_KEYS`). 예: `close`, `month_closes`, `ev`, `ebit_yield`, `fcf_yield`, `implied_growth`, `expectation_gap`, `detail`, `reference_range`, `price_e4`.
- `public_price_boundary.py`(설계 §12-3-1):
  - 허용 출처는 `https://iextrading.com/api/1.0/hist`(색인), `https://www.googleapis.com/…/b/iex/o/…`(파일·메타데이터) 두 형태다.
  - 어댑터 자체도 호스트를 막는다(`src/providers/iex_hist.py:125` `fetch_json`, `:150` `_link_ok`).
  - 허용 호출자는 `tools/qgv_official_publish.py` 하나다.
- 프론트 판독기 `qgv-official.js`는 U6 몫이다. 출처 문구 `attribution.text`·`terms_url`·`label_ko`를 화면에 그대로 보인다.

## 3. 결정이 반영된 것(이번 브랜치)
- `v_calc_version`은 없다. `calc_version`은 `sec-qgv2.json`의 값 하나다.
- 가격 의존 사유 4개는 `PRICE_DEPENDENT_NOT_COMPUTABLE`로 묶는다(`src/qgv/qgv_official.py` `PRICE_DEPENDENT`). 원 코드가 공개본에 있으면 검증기가 거부한다. **2026-10-24 검토: 이름만 바뀐다.** 원 코드는 정해진 요인 칸에만 나와(`EV_NON_POSITIVE`는 수익률·업종 대비 세 칸, 역DCF 사유는 기대 점검 칸) 칸이 원 코드를 되돌려 주고, V 축·순위도 같은 사실을 보인다. 가격 경계 누출은 V 공개 자체에 딸려 온다 — 소유자 재결정 필요(설계 §4-4 정정 메모, `public_price_boundary/AUDIT.md` §10-6(PR-B)).
- **F_k 처리:**
  - 원가격 ÷ `share_basis_factor`(`src/providers/iex_monthend.py:157`)로 월말가를 맞춘다.
  - F_k가 없거나 null이면 그 달을 뺀다. 공개 사유는 그 항목의 `share_basis_factor_reason`이 `v2_factors.SHARE_BASIS_REASONS`(`SHARE_BASIS_UNCONFIRMED`, `SPLIT_TIMING_UNCONFIRMED`) 중 하나일 때만 그 값이고, 아니면 `SHARE_BASIS_FACTOR_NOT_AVAILABLE`이다(`iex_monthend._factor`; 2026-10-24 검토로 문구 정정 — 처음 판의 "형식 `[A-Z0-9_]+`면 게시"는 코드와 달랐다). 1.0으로 보지 않는다.
  - F_k는 원본 행에서 읽는다. `qgv2_inputs.normalize`는 그대로다.
- PSKY: 2025-08-07 전 회계연도 월은 뺀다. V4가 NA가 되면 공개 사유는 `MERGER_PRE_BASIS_UNCONFIRMED`다(`src/providers/iex_hist.py:75`).
- PSKY→SKYD 별칭은 2026-10-06부터다. CONFIRMED: IEX TOPS probe run 39944426209(`src/providers/iex_hist.py` `SYMBOL_ALIASES`). U8 `monthend_plan.py`(7bca307d)에도 같은 항목이 있다.
- WBD: 2026-10-06부터 기호 None이다(같은 probe에서 IEX 상태·체결 없음). `NO_IEX_TRADE`로 두고 V는 NA다. 채우지 않는다.

## 4. 열린 항목(소유자)
- **분할(D-CV11) — 2026-10-24 결정 D6 (a): F_k 근거 재사용, 새 출처 없음. 같은 날 밤 결정 CV-SPLIT (ii): 보조 검사 D6 (b)를 더함(#400).** IEX HIST에는 기업행사가 없다.
  - 연결한 것(`src/qgv/qgv_official.py` `split_after_share_count`): 주식수 기간 끝(`diluted_shares.period_end`) 이후의 `ebit_per_share_history` 항목이 F_k `null` + `SPLIT_TIMING_UNCONFIRMED`면 `SPLIT_AFTER_SHARE_COUNT`(가격 없음, V NA, D-CV5 분모 밖). 그 사유는 그 회계연도 말월 월말 뒤~연간 서류 접수 사이의 분할 비율 사실 또는 표지 주식수 점프다.
  - **2026-10-24 검토 정정: 이 규칙은 현재가 분할 점검이 아니라 보수 규칙일 뿐이다.** 서류 접수 **전**에 일어난 분할은 그 서류가 주식수를 분할 뒤 기준으로 고쳐 싣는다(US GAAP ASC 260 소급 조정; #393 V-PRICE-BASIS의 WMT 예). 그 기준은 오늘 IEX 가격과 같으므로 이 규칙에 걸리는 행은 대개 바르게 값이 매겨질 행이다. 고쳐 싣지 않은 XBRL 주식수에 대비해 빼 둘 뿐이다.
  - D6 (a)로 연결할 수 없는 것과 이유(아래 D6 (b)가 맡음): 주식수를 실은 서류의 **접수 뒤~IEX 기준일** 구간. 주식수와 가격이 실제로 어긋나는 구간은 여기뿐이다. 이 구간의 분할이 있으면 그 행은 `SUPPLIED`로 남고 공식 V와 순위가 분할 비율만큼 틀린다. 다음 10-Q·10-K가 주식수를 고쳐 실을 때까지다(예: NVDA 10:1 2024-06-10, 1분기 10-Q 2024-05-29 → 약 2.5개월; CTAS 4:1 2024-09, FY 2024-05 10-K 뒤). 시험 `test_residual_without_short_store_steps_a_split_after_the_count_filing_is_not_detected`가 D6 (b)로도 남는 잔여를 고정한다. F_k·SPLIT 사슬은 수집 시점까지 접수된 companyfacts(정기 10-K·10-Q XBRL)로만 계산된다. 8-K로 알린 분할이나 마지막 10-Q 뒤 분할은 다음 정기 서류가 주식수를 고쳐 실을 때까지 사실이 없다. `sec-qgv2.json`에는 주식수 서류의 접수일이 없고, 실행은 그날 샤드 하나의 companyfacts만 갖고 있다. 그래서 그 구간의 분할은 다음 정기 서류 전까지 보이지 않는다.
  - 검증된 분할 창 표 `SPLITS`(`src/providers/iex_hist.py`)는 계속 비어 있다. 소유자가 나중에 다른 출처(U8 `VERIFIED_SPLIT_ROWS` 등)를 승인할 때의 연결 지점이다. 손으로 채우지 않는다.
  - **D6 (b) — 2026-10-24 밤 소유자 결정 CV-SPLIT (ii) "보조 검사 추가: #400에 넣고 시험한다", 구현 #400(`qgv_official.split_check`, `iex_monthend.raw_series`).** V 단계 RAM 안에서 주식수 기간 끝이 든 달의 원 월말 체결부터 기준일 오늘 IEX 원가격까지(F_k로 나누지 않음) 이웃한 두 점 중 간격 45일 이하인 쌍의 비율이 분할 배수 대역(n ∈ {2, 3, 4, 5, 6, 8, 10, 15, 20, 25, 30, 40, 50}은 ±25%, 3:2는 ±10%)에 들면 `SPLIT_AFTER_SHARE_COUNT`(V NA, D-CV5 분모 밖, 새 상태 코드 없음). 값은 바꾸지 않고 내지 않을 뿐이다. 가격·비율은 RAM에만 있고, 게시기 한 줄에는 개수만 남는다(`split_checked`·`split_flagged`·`split_unchecked`·`split_unchecked_no_period`·`split_gap_skipped`·`split_lead_unchecked`). 45일 안의 진짜 큰 움직임(약 −27% 이하, +36% 이상)도 걸리고(보수적 오탐), 3:2에 10% 넘는 움직임이 겹치면 놓친다. 점검 ≠ 접수 뒤 분할 없음: 기간 끝이 든 달의 월말 점이 없거나 45일 넘는 간격이 있으면 그 구간은 비교하지 않은 채로 남는다(행이 `split_checked`에 들어가도; 기간 끝 달 점이 없는 점검 행 수가 `split_lead_unchecked`). 공개 `SPLIT_AFTER_SHARE_COUNT` 중 D6 (a)로 설명되지 않는 행은 가격에서 나온 1비트를 드러낸다(설계 §7, `AUDIT.md` §10-6-4). 자세한 규칙·시험: 설계 §7 2026-10-24 밤 메모.
  - **저장소 한계:** 지금 U8 저장소(stamp 20261023)는 달마다 그 달이 회계연도 말월인 종목만 갖는다(62개월 2021-06~2026-09, 달마다 기호 1~310개). 한 종목의 최신 원 월말가는 지난달이 아니라 최신 회계연도 말월(0~15개월 전)이라, 지금은 대부분의 행에 기간 끝 뒤 짧은 간격이 없어 미점검이다(잔여: 그 행의 접수 뒤 분할은 여전히 못 잡는다). Universe 전 종목의 최근 월말가 보충(별도, 소유자 승인 필요) 뒤에 전 종목에 효과가 난다.
- **ADR(D-CV10) — 2026-10-24 결정 D7: 20-F 제출자도 NA(보수적).** `sec-qgv2.json`에는 서식 종류가 없다(`v_inputs_v2.taxonomy`만). 그래서 `taxonomy == ifrs-full` 규칙에 더해 Universe504의 알려진 20-F·40-F 제출자를 CIK 표 `qgv_official.FOREIGN_ANNUAL_FILERS`로 둔다(분류 체계와 무관하게 `ADR_RATIO_UNCONFIRMED`). 근거는 기존 공개 자료 `DCV_OPEN_ITEMS_20261019.md` D-CV10: 498 CIK의 최신 연간 서식 중 20-F 1(ASML), 40-F 0. **2026-10-24 검토 정정:** 처음 판의 "ASML은 이미 `ifrs-full`이라 지금 산출 변화는 0"은 틀렸다. 공개 `sec-qgv2.json`(as_of 2026-10-24T00:50Z)에서 `NASDAQ:ASML`·`TARGET:asml`의 분류 체계는 `us-gaap`(통화 EUR)이고, Universe 행 중 `ifrs-full`은 없다(`us-gaap` 502, 없음 2). 그래서 ASML을 잡는 것은 `ifrs-full` 규칙이 아니라 CIK 표 `FOREIGN_ANNUAL_FILERS`뿐이다. 공개 `price_status`는 `SUPPLIED` → `ADR_RATIO_UNCONFIRMED`로 바뀐다. V는 원래도 NA다(EUR 공시 통화라 `CURRENCY_BASIS_UNCONFIRMED`, `DCV_OPEN_ITEMS_20261019.md`가 맞게 적은 대로). 따라서 V·순위 산출 변화는 0이고 바뀌는 것은 공개 상태 코드 하나다. Universe에 새 20-F·40-F 제출자가 생기면 이 표에 넣어야 한다. 자동으로 잡으려면 같은 아티팩트의 `sec-universe-shares.json` 행 `form`을 두 번째 입력으로 읽어야 한다(입력 목록·`publication_id`가 바뀌므로 별도 결정).
- **크기.** 공개 `sec-qgv2.json`(2026-10-23 as_of)과 합성 가격으로 측정했다.
  - 504+19행, **1,109,234 B(1.06 MiB)**, gzip 114,962 B. 한도 2 MiB 안이다.
  - 설계 추정 0.6~0.7 MB보다 크다. 행당 약 2.1 KB이고, 요인 15개 `{score, reason, basis}`가 1.2 KB다.
