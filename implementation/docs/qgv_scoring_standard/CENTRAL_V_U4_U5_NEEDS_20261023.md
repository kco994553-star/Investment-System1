# 중앙 V 게시 — U4(워크플로)·U5(가드) 승인 요청에 필요한 것 (2026-10-23)

> **상태: 기록 문서.** 이 브랜치(`claude/cv-core-publisher`)는 워크플로·가드를 바꾸지 않는다.
> U1~U3 코드만 있다. 아래는 U4·U5가 그대로 옮겨 쓸 요구 사항이다. 가격 값은 없다.

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
- 표준 출력은 한 줄뿐이다: `QGV_OFFICIAL attempt=… reason=… published=… basis=… rows=… ranked=… supplied=n/m`. 가격·URL·키는 없다.

### 1-2. Secret(새로 필요) — **소유자 결정**
| 이름(기본값) | 용도 | 도구 인자 | 결정 |
| --- | --- | --- | --- |
| `QGV_OFFICIAL_HMAC_KEY` | 가격 묶음 HMAC → `publication_id`에만 쓴다(`src/qgv/qgv_official.py:359`). 공개하지 않는다 | `--hmac-key-env` | **새 Secret 승인 필요**(C). 16바이트 이상. 없으면 `NOT_RUN HMAC_KEY_MISSING` |
| `RAW_REPO_READ_TOKEN` | V4 월말가 비공개 저장소 읽기(`src/providers/iex_monthend.py:50`, `:142`) | `--raw-token-env` | **(B) 선택지 둘** 아래 |

**(B) RAW_REPO_TOKEN 충돌.** 설계 §3-3은 "이 단계에 `RAW_REPO_TOKEN`을 주지 않는다"였다. V4 월말가를 읽으려면 비공개 저장소 읽기 권한이 필요하다.
- **(a) 권장:** 비공개 원자료 저장소 `kco994553-star/investment-system1-raw` **읽기 전용** fine-grained 토큰을 새 Secret `RAW_REPO_READ_TOKEN`으로 둔다. 게시 단계 `env`에만 준다. Contents: read 하나만 준다.
- **(b)** 기존 `RAW_REPO_TOKEN`을 이 단계에만 준다. 쓰기 권한까지 같이 간다.
- 쓰지 않는 방식: 가격 임시 파일을 만드는 "별도 단계". 설계 §3-3 위반이다.
- 코드는 토큰 **이름**을 인자로 받는다(`--raw-token-env`). 어느 쪽이든 코드 변경은 없다.
- 토큰은 `api.github.com` 요청에만 붙는다. 자산 다운로드 리디렉트에는 붙이지 않는다(`src/providers/iex_monthend.py:59-61`, `:96`). 시험: `tests/test_iex_hist.py` `_release_call`.
- 토큰이 없으면 `SUPPLY_FAILED MONTHEND_TOKEN_MISSING`이고 직전 정상본을 유지한다.

### 1-3. 기준일·공급 기준 — **소유자 확인 필요**(D)
- **기준일:** IEX 색인에 있는 마지막 TOPS 1.6 날짜 중 `shard_day(시작 시각)` 이하(`src/providers/iex_hist.py:155`). T+1이라 22:17 UTC 실행에서는 보통 **전 거래일**이다. 게시본에는 `price_source.requested_basis_date`(shard_day)와 `basis_date`(실제 IEX 날짜)를 따로 싣는다.
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
- 가격 의존 사유 4개는 `PRICE_DEPENDENT_NOT_COMPUTABLE`로 묶는다(`src/qgv/qgv_official.py:46`). 원 코드가 공개본에 있으면 검증기가 거부한다.
- **F_k 처리:**
  - 원가격 ÷ `share_basis_factor`(`src/providers/iex_monthend.py:157`)로 월말가를 맞춘다.
  - F_k가 없거나 null이면 그 달을 뺀다. 공개 사유는 `share_basis_factor_reason`(형식 `[A-Z0-9_]+`)이고, 아니면 `SHARE_BASIS_FACTOR_NOT_AVAILABLE`이다. 1.0으로 보지 않는다.
  - F_k는 원본 행에서 읽는다. `qgv2_inputs.normalize`는 그대로다.
- PSKY: 2025-08-07 전 회계연도 월은 뺀다. V4가 NA가 되면 공개 사유는 `MERGER_PRE_BASIS_UNCONFIRMED`다(`src/providers/iex_hist.py:75`).
- PSKY→SKYD 별칭은 2026-10-06부터다. CONFIRMED: IEX TOPS probe run 39944426209(`src/providers/iex_hist.py` `SYMBOL_ALIASES`). U8 `monthend_plan.py`(7bca307d)에도 같은 항목이 있다.
- WBD: 2026-10-06부터 기호 None이다(같은 probe에서 IEX 상태·체결 없음). `NO_IEX_TRADE`로 두고 V는 NA다. 채우지 않는다.

## 4. 열린 항목(소유자)
- **분할(D-CV11).** IEX HIST에는 기업행사가 없다.
  - 현재가 분할 검사 표 `SPLITS`(`src/providers/iex_hist.py:82`)는 비어 있다. 검증된 분할 출처를 연결할지 결정이 필요하다.
  - 후보: U8 `split_check.py`의 `VERIFIED_SPLIT_ROWS`, 또는 cv-fk의 F_k 근거.
  - 연결 전에는 주식수 기간 끝 뒤 분할이 있는 종목도 EV를 그대로 계산한다(V-SHARES-SCALE만 적용).
- **ADR(D-CV10).** `taxonomy == ifrs-full` 행은 `ADR_RATIO_UNCONFIRMED`(NA)다. US-GAAP로 20-F를 내는 발행인은 이 규칙으로 걸러지지 않는다.
- **크기.** 공개 `sec-qgv2.json`(2026-10-23 as_of)과 합성 가격으로 측정했다.
  - 504+19행, **1,109,234 B(1.06 MiB)**, gzip 114,962 B. 한도 2 MiB 안이다.
  - 설계 추정 0.6~0.7 MB보다 크다. 행당 약 2.1 KB이고, 요인 15개 `{score, reason, basis}`가 1.2 KB다.
