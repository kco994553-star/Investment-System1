# 공식 V 중앙 계산·게시 설계와 재사용 지도 (2026-10-18)

> **2026-10-23 갱신:** 가격 공급자는 IEX HIST로 정해졌다(소유자 결정, GSQ-024). 이 설계대로 구현한다. 공개 필드·가격 의존 사유 묶음·최신본만 공개(D-CV14 (a))는 결정과 같다. 가드 변경은 별도 PR, 소유자 승인 후 병합.

> **상태: 설계 문서(DESIGN ONLY).** 워크플로·가드·엔진·화면 코드는 바꾸지 않는다.
> 가격 출처는 정하지 않는다. 형제 작업자 두 명이 출처와 사용권을 따로 조사한다.
> 이 문서는 출처를 **가격 공급자(price provider)** 로만 부른다.
> 가격 값·가격 파생값·개인 자료는 이 문서에 없다.

- 작성: 2026-10-18 23:41 UTC / 2026-10-19 08:41 KST.
- 기준: `claude/investment-system-top500-validation-alrugm` `c948569e`(#322 병합 뒤). 화면 새로고침은 #321(`claude/fe-data-refresh` `a18ee6da`)을 읽었다.
- 소유자 승인(원문 취지): 공식 QGV의 V를 기기별 계산에서 중앙 계산으로 옮긴다. PC·모바일·비로그인 방문자에게 **같은 값의 공식 게시본 하나**를 보인다.
- 인용은 `파일:줄`이다. 경로 앞부분 `implementation/src/investment_system/`은 `src/`로, `implementation/`은 생략한다.

## 요약

- **엔진은 새로 만들지 않는다.** `qgv/qgv_v2.py` `score_universe`(:590-716)와 JS 쌍둥이 `qgvV2.scoreUniverse`(`web_assets/qgv-v2.js:195`)를 그대로 쓴다. 벡터 시험 `tests/fixtures/qgv_v2_vectors_v1.json`·`tools/qgv_v2_node_test.js`도 그대로다.
- **새로 필요한 것은 얇은 층 셋이다.** ① 가격 공급자 어댑터(일관성 검사 포함) ② `sec-qgv2.json` → 엔진 입력 변환의 Python 쌍둥이(지금은 JS `qgv2-inputs.js:65-77`에만 있음) ③ 게시본 파일 `qgv-official.json`과 엄격 검증기.
- **게시마다 Universe 전체를 다시 계산한다.** 같은 날짜 종가 한 벌로만 계산한다. 섞지 않는다.
- **공개 필드는 점수·순위·사유·커버리지·기준 시각뿐이다.** 가격·EV·수익률·내재 성장률·자기 과거 수익률은 싣지 않는다.
- **복원 위험 결론:** 점 복원은 안 된다. 하지만 구간 추정은 된다. 특히 가격 의존 사유 코드 두 개(`EV_NON_POSITIVE`, `ROOT_NOT_BRACKETED`)는 공개 SEC 입력과 합치면 가격의 상한·하한을 바로 준다(§4-4).
- **개인 미리보기 결론:** 공개 V 요인 점수를 그대로 쓰면 엔진과 **정확히 같게** 만들 수 있다. 단, 엔진에 "게시된 V 요인 점수" 입력 한 가지를 더해야 한다. 그 전에는 V 비중을 바꾸는 미리보기를 "근사"로 표시하거나 막아야 한다(§9).
- **경계 변경은 제안만 한다.** 출처와 사용권이 확인된 뒤에만 유효하다. 지금 가드는 바꾸지 않는다(§12).
- **중앙화가 해결하지 않는 것:** 금융업 V(67곳, `FINANCIAL_PROFILE_V_NOT_DEFINED`)와 일반 기업 입력 결측(가격 무관 상한 360/434, `V_GENERAL_COVERAGE_20261018.md:8-9`)은 그대로다. 별도 과제다.

## 1. 입력 분해 A/B/C/D

| 묶음 | 무엇 | 가격 입력 | 지금 위치 | 중앙화 범위 |
| --- | --- | --- | --- | --- |
| **A. 현재 V** | V 요인 5개(이익 수익률·FCF 수익률·업종 대비·자기 과거 대비·기대 점검), V 축, 종합, 관문 | 종목별 **종가 1개**(기준일 하나). 자기 과거 대비는 회계연도 말월 **월말 종가 최대 5개** | 기기 RAM(`qgv-scores.js:222-236` 수집, `:64-74` 계산) | **이번 중앙화 대상** |
| **B. 가격·주식수·기업행사 정합** | 같은 증권·주식 종류, ADR 비율, 통화·단위, 분할 기준, 같은 날짜 | A와 같은 기록 + 분할 정보 | 일부만 있음: 통화 비교(`qgv_v2.py:355-356`), 주식수 단위 검사 V-SHARES-SCALE(`v2_factors.py:235-252`), 분할 규칙 SPLIT(`v2_factors.py:225-233`) | **A의 전제 조건**. 어댑터 검사로 넣는다(§7) |
| **C. 차트·레이더·TA** | 일봉 OHLC, 252세션 창, 모멘텀 등 가격 축 | 일봉 계열 | 기기(`stat-radar.js`, #311), 차트 모듈 | 대상 아님. 기기 전용 유지 |
| **D. 백테스트** | 과거 시점 가격·주식수·기업행사·공시 시각 묶음 | PIT 과거 기록 전체 | 연구(#286 어댑터, `BACKTEST_RESEARCH_PLAN.md`) | 대상 아님 |

**C·D 과거 기록이 A의 전제가 아닌 이유.**
- A는 "지금" 점수다. 게시일부터 앞으로만 낸다. 과거로 소급하지 않는다. 그래서 과거 가격 보관소가 필요 없다.
- A의 가격 입력은 종목당 종가 1개다(`qgv_v2.py:352-354`). OHLC 계열·세션 창은 쓰지 않는다.
- 자기 과거 대비만 월말 종가를 쓴다(`qgv_v2.py:363-383`, `month_close` :313-318). 많아야 5개다(`v2_factors.HISTORY_YEARS`). 차트 계열이 아니다.
- 그 종가가 없어도 A는 멈추지 않는다. 그 요인만 `PRICE_HISTORY_NOT_AVAILABLE`로 NA다. 남은 비중 85%로 V 축 50% 규칙(`qgv_v2.py:41,100`)을 넘을 수 있다.
- D는 PIT 접수 시각·생존 편향·기업행사 이력이 필요하다. A의 게시 규칙과 무관하다. A의 게시본을 D의 증거로 쓰지 않는다.
- C의 가격 축은 소유자 결정 RADAR-AXES대로 기기 계산만 한다(`USER_DECISIONS_PENDING.md:21`).

## 2. 현재 경로(입력 → 화면)

1. **SEC 수집(샤드).** `tools/sec_universe_shares.py` `collect`(:178-271)가 뉴욕 날짜로 고른 샤드 하나를 받는다(`src/universe/sec_universe_shares.py:77-90` `shard_day`·`shard_index_for`). 같은 바이트로 `sec_qgv2.build_issuer_records`(:184-188) → `build_row`(:152-181) → `v2_factors.compute` → `_v_inputs`(:1177-1295)를 만든다.
2. **TARGET 행.** `tools/public_screens_pipeline.py` `stage_qgv2_target`(:66-104)가 TARGET SEC 바이트로 행을 만든다(`sec_qgv2.build_target_rows` :191-202). 같은 폴더에 둔다.
3. **병합과 전체 재계산.** `sec_qgv2.merge`(:276-333)가 이전 Pages 사본과 합친다. `publish`(:336-359)가 Q·G 백분위를 **Universe 전체로 다시 계산**한다(`vs.score_rows` :339). 단면 규칙은 `UNIVERSE504_LIVE_STALE_ONE_POINT_PER_CIK`(:64)다. 신선도는 행 `acquired_at` 기준(`restate` :238-249)이다.
4. **검증.** `require_qgv2`(:505-560)가 게시 지표에서 점수를 다시 계산해 비교한다(:539-557). 이 파일에는 가격·순위가 없다(:22).
5. **워크플로.** `.github/workflows/sec-daily-public-inputs.yml`
   - collect(:48-158): TARGET(:83) → 샤드(:101) → 원장(:114) → 분류·로고·13F·공시·뉴스 → 커버리지 줄(:151-153) → 업로드(:154-158). 매 단계 뒤 `pages_artifact_guard.py`.
   - verify(:160-208): 같은 아티팩트를 다시 검사하고 화면 시험을 돈다. 실패하면 배포만 막는다.
   - deploy(:209-249): `pages_freshness_guard.py`(:242-246) 뒤 배포.
   - 동시 실행: 워크플로 그룹 하나, 취소 없음(:21-23). 배포 그룹 `checked-cockpit-pages`(:220-222).
6. **브라우저 읽기.** `app.js:1180-1198`이 페이지를 열 때 한 번 읽는다. `Qgv2Inputs.load` → 엄격 판독기 → `Qgv2Inputs.fromInputs`(`qgv2-inputs.js:65-77`). 한 CIK 한 점은 정렬된 첫 코드다(:70). TARGET 행은 점이 아니다(:72).
7. **기기 가격.** `QgvScores.collectQuotes`(`qgv-scores.js:222-236`): Universe 시트 탭(가격 시각 미확인, :242) → 기기 시세(`DeviceValuation.deviceQuote`) → `PriceStore.monthEndCloses`. `app.js:670-672`가 이 페이지 세션 동안 쌓는다.
8. **기기 계산.** `QgvScores.compute`(`qgv-scores.js:169-208`)
   - 경기민감 기준: `PlaybookEngine.classifyTypesV0`(:173).
   - 가격 식별 충돌 코드 가격 제거(:176-177).
   - `universeScores`(:64-74) → `qgvV2.scoreUniverse`.
   - 순위: 넘겨받은 식별자 안에서만(:195-196). 기본 식별자는 TARGET 19(`app.js:669`, `app.js:1184`, `watchlist.js:4`).
9. **공유 페이지 결과.** `pageResult`(:245-253)가 Universe 전체 코드로 한 번 계산한다. V 커버리지 패널(`vCoverage` :260-287)과 레이더가 같이 쓴다.
10. **리더보드.** `app.js:678` `paintLeaderboardScreen` → `LeaderboardScreen.mount`(`leaderboard-screen.js:73-`). 분석 모집단 수는 `populationOf`(:59-60).

**왜 기기마다 V가 다른가(코드 근거).**
- V 백분위 모집단이 "이 기기에서 가격이 있는 행"이다(`QGV_V2_V_DEVICE.md:22`, `qgv-scores.js:240`).
- 가격 출처가 섞인다. 시트 탭은 가격 시각이 없다(`qgv-scores.js:242`). 기기 시세는 출처마다 `as_of`가 다르다(:229).
- 순위 모집단이 화면 식별자(19)다(:195-196).

## 3. 목표 파이프라인

### 3-1. 단계

```
collect 잡 (기존 순서 유지)
  :83  TARGET 공개 입력  ─┐
  :101 Universe 샤드     ─┼─ sec-qgv2.json (최종, 가격 없음)
  :105 DART 투영          │
  :114 원장               │   ← V 실패와 무관하게 먼저 끝난다
  [새 단계] 공식 V 게시 ──┘
     1) 직전 공식 게시본(라이브) 확인 → 아티팩트에 그대로 복사(마지막 정상본)
     2) 가격 공급자에서 기준일 종가 받기 (RAM)
     3) 일관성 검사 (§7) → 종목별 가격 상태
     4) sec-qgv2.json → 엔진 입력 (Python 쌍둥이)
     5) score_universe 전체 재계산 (공식 기본 프로필)
     6) 검증: 엄격 검증기 + (결정 D-CV12) JS 쌍둥이 대조
     7) 통과하면 qgv-official.json 교체, 아니면 1)의 사본 유지
     8) qgv-official-status.json 기록 (시도 결과)
     9) 가격을 RAM에서 버림
  이후 :122~:147 단계 그대로
  :151 커버리지 줄 (+ V 개수 줄)
verify 잡: 게시본 공개 자기 일관성 + 화면 시험 (가격 없이)
deploy 잡: 신선도 검사에 게시본 규칙 추가 → 배포
```

### 3-2. 기존 잡에 붙는 위치와 이유

- **원장 뒤(:115 다음), 분류 단계(:118) 앞**에 둔다.
  - W-F1 규칙(:116-117)과 같다. 원장에 쓰지 않는 단계는 원장 뒤에 둔다. V 실패가 원장을 막지 않는다.
  - 최종 `sec-qgv2.json`은 샤드 단계(:101)에서 정해진다. DART 투영(:105)은 그 파일을 바꾸지 않는다. 그래서 원장 뒤에서 읽어도 같은 입력이다.
- **`continue-on-error: true`** 로 둔다. 공시(:139)·뉴스(:145) 단계와 같다. 공급 실패는 단계 실패가 아니다. 종료 코드 0과 고정 코드 한 줄로 끝낸다.
- **먼저 직전 정상본을 복사한다.** `sec_universe_shares.py` `run`이 수집 전에 이전 사본을 먼저 쓰는 방식(:368-395, `PREVIOUS_RESTORED`)을 그대로 따른다. 도구가 중간에 죽어도 아티팩트에는 정상본이 남는다.
- **원자적으로 쓴다.** 검증을 통과한 바이트만 임시 파일 → `replace`로 넣는다(`public_screens_pipeline.py:19-40`의 방식). 다음 단계의 `pages_artifact_guard`가 깨진 파일 때문에 전체 아티팩트를 막는 일을 막는다.
- **verify 잡**은 가격이 없다. 가격을 다시 받지 않는다. 다시 받으면 값이 달라져 대조가 무너진다. 그래서 가격이 필요한 재계산 대조는 collect 안에서 끝낸다. verify는 가격 없이 되는 검사만 한다(축 = 요인의 가중 평균, 종합 = 축과 비중, 순위 = 종합 순서, 커버리지 수 = 행 상태 합).
- **deploy 잡**은 신선도 검사(:242-246)에 게시본 규칙을 더한다(§12-5). 배포 그룹(:220-222)은 그대로다.
- **동시 실행.** 워크플로 그룹(:21-23) 덕에 한 번에 한 실행만 돈다. 그래서 "직전 정상본 = 마지막으로 배포된 라이브 사본"이 성립한다.
- **기준일과 뉴욕 날짜.** 가격 기준일 = `shard_day(시작 시각)`(`sec_universe_shares.py:77-84`) 이하의 마지막 완료 뉴욕 거래일. 예약 22:17 UTC는 EDT 18:17, EST 17:17로 장 마감 뒤다. 00:00 UTC 뒤 대체 실행도 전날 뉴욕 날짜로 간다. 같은 함수를 재사용한다.
- **수동 배포 경로.** `cockpit-pages.yml:33-41`의 보존 단계에 게시본 보존(`--preserve-only`, 바이트 그대로 복사)을 더해야 한다. 그 경로는 가격이 없으니 다시 계산하지 않는다. `sec_universe_shares.py --preserve-only`(:35)는 `sec-qgv2.json`을 다시 점수 매기지만(`run` :390-392) 게시본은 따로 자기 완결이라 섞이지 않는다.

### 3-3. 가격이 로그·아티팩트·git에 닿지 않게

| 경로 | 막는 방법 | 근거·재사용 |
| --- | --- | --- |
| 아티팩트 | 가격은 파일로 쓰지 않는다. RAM dict만. 게시본 검증기는 정확한 키 집합만 허용한다(가격 키 없음). 아티팩트 가드의 민감 키 검사(`pages_artifact_guard.py:149-159`)는 그대로 돈다 | `require_qgv2` 방식(:505-560) |
| `RUNNER_TEMP` | 가격 임시 파일을 만들지 않는다. JS 대조가 필요하면 표준 입력 파이프로 넘긴다 | — |
| 로그 | 고정 코드와 개수만 출력한다. 종목명·값·URL·키 없음 | `tools/sec_universe_shares.py:11` 원칙 |
| 예외 메시지 | 고정 코드로 바꾸고 `from None`. 원 메시지(값 조각 포함 가능)를 버린다 | `sec_qgv2.py:559-560`, `:578-579` |
| 원자료 업로드 | 가격 원자료는 비공개 릴리스에도 올리지 않는다. 이 단계에 `RAW_REPO_TOKEN`을 주지 않는다 | SEC raw 업로드(`:98`)와 분리 |
| git | 체크아웃이 `persist-credentials: false`(:57-58)다. 이 단계에 push 경로 없음. `actions/cache` 없음 | `test_public_price_boundary.py:133-151`과 같은 정적 시험을 이 단계에도 둔다 |
| Secret | 공급자 키는 이 단계 `env`에만 둔다 | 기존 SEC·DART 패턴(:79-81, :87-88) |
| 지문 | 종목별 가격 해시를 싣지 않는다. 가격 묶음 전체의 **키 있는 지문**(HMAC, 키는 Secret)만 `publication_id` 계산에 쓴다. 비밀 키 없는 해시는 추측 대조 공격에 약하다 | §5 |

## 4. 게시본 스키마 — `qgv-official.json` (`qgv-official/1`)

> **2026-10-24 갱신(PR-A, `claude/central-v-core`):** 아래 4-1~4-3 표를 코드 스키마(`src/qgv/qgv_official.py` `TOP_KEYS`·`ROW_KEYS`·`STATUS_KEYS`, 검증기 `require_qgv_official`·`require_status`)에 맞췄다. 결정은 바꾸지 않았다. 2026-10-18 표와 다른 점(이력):
> - 최상위 `price` → **`price_source`**. 키 `price`는 Pages 가드의 민감 키이고 검증기 `FORBIDDEN_KEYS`에도 있다. 내용도 IEX 기준으로 바뀌었다: `basis_kind` `SESSION_CLOSE` → `IEX_LAST_REGULAR_SESSION_TRADE`(공식 종가 아님, GSQ-024), `requested_basis_date`·`supply`·`month_end` 추가(D3·D4·V4 월말가).
> - 최상위 **`attribution`** 추가(GSQ-024 출처 문구 의무, 상태 파일에도 같은 값).
> - `v_calc_version` 행 삭제: D-CV7 (b)(2026-10-23 소유자 지시, §15-2). 그 전 표는 취소선으로 남겼었다.
> - `engine`에 `publisher_sha256`(게시기·어댑터·입력 변환 원본 해시) 추가. `population`·`weights` 필드 이름을 코드와 맞춤(`universe_code_count`·`row_count`, `type_weights`).
> - 행에 **`rank_row`** 추가(한 CIK 한 순위의 대표 행 키, D-CV8·D-CV9). `price_status` 어휘를 IEX 어댑터 코드로 고정.
> - 상태 파일에 `schema`·`kind`·`attribution` 추가.
> - `publication_id` 매니페스트(§5-3)의 실제 항목: `calc_version`, `inputs_sha256`, `provider`, `feed`, `basis_date`, `adjustment_basis`, `price_hmac`(가격 묶음 HMAC, 비공개), `population`, `weights`, `type_scope`, `config_versions`, `engine`, `month_end`. 시각 없음, `v_calc_version` 없음.

### 4-1. 최상위 필드

| 필드 | 뜻 | 공개 | 비고 |
| --- | --- | --- | --- |
| `schema`, `kind` | `qgv-official/1`, `QGV_OFFICIAL` | 예 | |
| `publication_id` | `qgvpub-` + 매니페스트 sha256 | 예 | §5. 시각이 아니라 입력 내용에서 나온다 |
| `state` | `OFFICIAL` | 예 | 실패 상태는 상태 파일에 둔다(§6) |
| `calc_version` | 입력 `sec-qgv2.json`의 `calc_version` 그대로(`qgv2-calc/2026-10-23.1` 이상, 그 전 파일이면 게시하지 않음 `NOT_RUN SEC_QGV2_CALC_VERSION_BEFORE_U7`) | 예 | U7 게시 규칙도 이 번호가 덮는다(D-CV7 (b), §15-2). `v_calc_version`은 없다 |
| `engine` | `{version:'qgv-v2', status:'PROVISIONAL', python_sha256, js_sha256, publisher_sha256}` | 예 | 엔진·게시기 원본 해시 |
| `population` | `{version, universe_code_count, registry_sha256, row_count, pooled_count, pooled_digest}` | 예 | `version` = `sec-universe-shares` 설정 버전, `registry_sha256`은 `sec-qgv2.json`에서 |
| `weights` | `{default_preset:'balanced', gate:true, type_weights:true, profile_id:'qgv-v2/balanced/gate-on', weights_version}` | 예 | `weights_version` = `weights_id(official_weights())` |
| `type_scope` | 엔진 `TYPE_SCOPE` | 예 | |
| `config_versions` | `{type_config, dcf_parameters}` | 예 | |
| `price_source` | `{provider:'IEX_HIST', feed:'TOPS 1.6', basis_kind:'IEX_LAST_REGULAR_SESSION_TRADE', adjustment_basis:'AS_TRADED', currency:'USD', basis_date, requested_basis_date, supplied, rejected:{사유:개수}, supply:{eligible, supplied, minimum_share:0.95, met:true}, month_end:{store:'iex-monthend/1', stamp, months, basis:'RAW_DIVIDED_BY_SHARE_BASIS_FACTOR'}}` | 예(값 없음) | `requested_basis_date` = 실행의 뉴욕 날짜, `basis_date` = 실제 IEX 파일 날짜(≤ 요청일, D3). `supply` = D-CV5/D4 95%. `eligible` = 가격 없이 V 축 가중치 50%에 닿을 수 있는 GENERAL 단면 Universe 행(USD, ADR·분할 규칙 밖; `V_GENERAL_COVERAGE_20261018.md` 2-2 (b)의 엔진 가격 무관 조건, `qgv_official.supply_eligible`; 2026-10-24 검토로 "V 입력 블록이 있는 행"에서 바로잡음 — 공개 `sec-qgv2.json`(as_of 2026-10-24T00:50Z, calc_version 2026-10-17.1)으로 측정: 옛 정의 430, 새 정의 358(모든 해에 F_k가 있다고 둘 때; 그 파일에는 F_k가 없어 실제로는 345). 합성 가격으로 돌린 엔진의 V 산출 행은 모두 새 정의 안에 있었다) |
| `attribution` | `{text, terms_url, label_ko}` = IEX 출처 문구, 약관 링크, "IEX 마지막 체결가 기준(공식 종가 아님)" | 예 | 검증기가 정확히 같은 값을 요구한다. 화면은 그대로 보인다 |
| `inputs` | `[{file:'sec-qgv2.json', sha256, as_of, calc_version, acquired_oldest, acquired_newest}]` | 예 | 같은 실행 아티팩트의 파일 바이트 해시 |
| `times` | `{price_basis_date, price_collected_from, price_collected_to, inputs_as_of, generated_at, verified_at}` | 예 | `price_basis_date` = `price_source.basis_date`. 배포 시각은 없다(§8-3) |
| `coverage` | `{basis:'UNIVERSE_CODES', population, v, qgv, qg_only_total, ranked, qg_reference, price_status, not_computed, reasons, factor_reasons, target}` | 예 | 개수만. 검증기가 행에서 다시 세어 같아야 한다 |
| `rows` | Universe 504 코드 + `TARGET:<id>` | 예 | 아래 |

### 4-2. 행 필드

| 필드 | 공개 | 출처 |
| --- | --- | --- |
| `cik`, `profile`, `industry_group`, `in_cross_section`, `state`, `source_reason_codes`, `acquired_at`, `fiscal_year_end` | 예 | 같은 실행 `sec-qgv2.json` 행(Python 쌍둥이 `qgv2_inputs` 정규화) |
| `factors.<15개>.{score, reason, basis}` | 예 | `score_universe` 결과. Q·G 10개는 공개 파일 값, V 5개는 이번 계산. 가격 의존 사유 4개는 `PRICE_DEPENDENT_NOT_COMPUTABLE`(D-CV2) |
| `axes.{Q,G,V}.{score, state, weight_available, factors_available, reason}` | 예 | 결과 `axes`. 검증기: V 축 = 공개 V 요인의 가중 평균 |
| `weights`, `type_weights`, `type_reason`, `selected_types` | 예 | 결과. 가격 무관 |
| `q_industry_percentile`, `value_trap_gate`, `v_excluded`, `flags` | 예 | 결과 |
| `total`, `total_reason` | 예 | 공식 기본 프로필(균형·관문 켬). 검증기: 종합 = 축 × 비중(관문) |
| `price_status` | 예 | `SUPPLIED`, `ODD_LOT_ONLY`, `NO_IEX_TRADE`, `PRICE_SYMBOL_UNMAPPED`, `ADR_RATIO_UNCONFIRMED`(D7), `SPLIT_AFTER_SHARE_COUNT`(D6 (a)·D6 (b), §7; D6 (b) 적중은 가격에서 나온 공개 1비트다), `PRICE_IDENTITY_CONFLICT`, `IDENTITY_CONFLICT_WITHDRAWN`(`providers/iex_hist.py` `STATUS_CODES`). 값 없음 |
| `rank` | 예 | 공식 QGV 순위. D11: 종합과 V가 모두 있는 행만. 한 CIK 한 순위(D-CV8·D-CV9). 동점은 기호, 그다음 키 순 |
| `qg_reference_order` | 예 | Q·G만 있는 종합의 별도 순서. 공식 순위 아님 |
| `rank_row` | 예 | 그 CIK의 순위(또는 Q·G 참고 순서)를 가진 대표 행 키. 순위가 없으면 `null` |
| `detail.*`(수익률·내재 성장률·기대 차이·실현 성장·업종 동료) | **아니오** | 가격 또는 가격 역산 가능. 검증기 `FORBIDDEN_KEYS`가 어디서든 거부 |
| `reference_range` | **아니오** | 주당 가치 금액. 공개 범위 밖 |
| 가격·월말가·EV·시가총액·수익률·자기 과거 수익률·종목별 가격 시각·가격 해시·HMAC | **절대 아니오** | 같은 `FORBIDDEN_KEYS` |

- 가격 의존 사유 코드의 공개 형태는 결정 D-CV2를 따른다(§4-4). 원 코드가 공개본에 있으면 검증기가 거부한다.
- 크기 추정(2026-10-18): 약 520행 × 1~1.3KB ≈ 0.6~0.7MB. **2026-10-23 실측:** 504+19행 1,109,234 B(1.06 MiB), gzip 114,962 B(`CENTRAL_V_U4_U5_NEEDS_20261023.md` §4). 상한은 `sec-qgv2.json`과 같은 2 MiB다.
- 게시본은 **자기 완결**이다. Q·G 점수도 이 게시본 안의 값을 쓴다. 그래서 같은 날 새 `sec-qgv2.json`이 나와도 공식 순위가 섞이지 않는다.

### 4-3. 상태 파일 — `qgv-official-status.json`

- 마지막 정상 게시본 바이트를 바꾸지 않고 실패를 알리려고 따로 둔다.
- 필드(`STATUS_KEYS`): `schema`(`qgv-official-status/1`), `kind`(`QGV_OFFICIAL_STATUS`), `last_attempt_at`, `attempt_state`(`OK` / `SUPPLY_FAILED` / `VERIFY_FAILED` / `NOT_RUN` / `NO_OFFICIAL_YET`), `reason_code`, `official_publication_id`, `official_price_basis_date`, `official_verified_at`, `latest_inputs:{sha256, as_of}`, `attribution`.
- 게시본이 하나도 없으면 실패 시도도 `NO_OFFICIAL_YET`이고 `reason_code`에 실패 코드를 둔다. Secret이 없으면(`HMAC_KEY_MISSING`, `MONTHEND_TOKEN_MISSING`) 내려받기 전에 `NOT_RUN`이다.
- 값·종목 목록·가격 없음.

### 4-4. 복원 분석 — 공개 점수 + 공개 SEC 입력 + 이력으로 가격을 되살릴 수 있나

공개 SEC 입력: `sec-qgv2.json` `v_inputs_v2`에 EBIT·FCF·총부채·현금·희석 주식수·주당 EBIT 이력이 이미 있다(`v2_factors.py:1145-1157`). 그래서 아래 경로를 점검했다.

| 공개 후보 | 복원 결과 | 판정 |
| --- | --- | --- |
| `detail.ebit_yield` 또는 `fcf_yield` | 가격 = (EBIT/수익률 − 부채 + 현금)/주식수. **정확 복원** | 금지 |
| `detail.implied_growth` 또는 `expectation_gap`(실현 성장은 공개) | 공개 FCF/주와 공개 DCF 설정으로 2단계 DCF를 돌리면 가격이 나온다(`qgv/dcf.py:81-120`). **정확 복원** | 금지 |
| 사유 `EV_NON_POSITIVE`(`qgv_v2.py:402-404`) | EV ≤ 0 ⇒ 가격 ≤ (현금 − 부채)/주식수. **상한이 바로 나온다** | 그대로 공개 금지(결정 D-CV2) |
| 사유 `ROOT_NOT_BRACKETED`(`dcf.py:102-103`) | 가격이 해법 구간 밖 ⇒ 가격 ≤ DCF(하한 성장) 또는 ≥ DCF(상한 성장). 두 값 모두 공개 입력으로 계산된다. **한쪽 경계가 나온다** | 그대로 공개 금지(결정 D-CV2) |
| 사유 `ROOT_NOT_CONVERGED`, `NUMERIC_OVERFLOW` | 정보가 약하지만 가격에 따라 갈린다 | 같은 묶음으로 처리 |
| V 요인 백분위(전체 정밀도) | 백분위 = 순위다(`qgv_v2.py:58-70`). 단면 안 EBIT/EV 순서가 드러난다. 다른 종목 가격을 시장에서 알면 이웃 사이 **구간**이 나온다. 점 복원은 안 된다(순서 정보만으로는 모든 가격을 같이 키운 해도 성립한다) | 공개(파생값). 사용권 판단은 형제 작업 |
| 자기 과거 대비 백분위 | 점이 6개 이하다. 현재 수익률이 과거 몇 번째 사이인지 드러난다. 과거 월말 종가는 시장 공개 정보다. 그래서 가격이 두 과거 값 사이 **구간**으로 좁혀진다. 이 요인이 가장 강한 구간 정보다 | 공개(파생값). 한계를 명시 |
| V 축 점수 + 나머지 요인 4개 | 축 = 가중 평균이라 빠진 요인 하나는 역산된다(`qgv_v2.py:73-104`) | 요인 하나만 숨기는 방어는 효과 없음 |
| 게시 이력(날짜별 순위 변화) | SEC 입력이 같은 날끼리 순위 변화 = 상대 가격 변화의 방향 | 공개 이력은 최신본만(결정 D-CV14) |
| `price_status`·`rejected` 개수 | 가격 값과 무관 | 공개 |
| 종목별 가격 해시 | 후보 가격을 넣어 맞춰 볼 수 있다 | 금지. 전체 묶음 HMAC만, 공개하지 않는 키로 |

**막는 방법(권장).**
1. 가격·EV·시가총액·수익률·내재 성장률·기대 차이·자기 과거 수익률·`detail` 전체를 싣지 않는다. 엄격 검증기의 정확한 키 집합으로 막는다.
2. 가격 의존 사유 4개(`EV_NON_POSITIVE`, `ROOT_NOT_BRACKETED`, `ROOT_NOT_CONVERGED`, 가격 계산 중 `NUMERIC_OVERFLOW`)는 공개 사유 `PRICE_DEPENDENT_NOT_COMPUTABLE` 하나로 묶는다. 원 코드는 실행 RAM 진단에만 둔다. 점수·규칙은 그대로다(표시 어휘만 바뀜). 결정 D-CV2.
3. 백분위만 싣는다(이미 그렇다). 종목별 수익률은 싣지 않는다.
4. **반올림은 방어로 기대하지 않는다.** 단면이 약 400점이면 백분위 한 칸이 약 0.25다. 소수 1자리 반올림은 순서를 거의 그대로 남긴다. 정수 반올림도 이웃 4칸 정도만 합친다. 대신 개인 미리보기 정확성과 공개 자기 검증을 깬다(§9). 그래서 전체 정밀도 공개를 권장한다. 결정 D-CV3.
5. 공개 이력은 최신 게시본 하나만 둔다. 과거 게시본 공개 누적은 하지 않는다. 결정 D-CV14.
6. 남는 위험: 순위·백분위 자체가 가격 파생 정보다. 이것을 공개해도 되는지는 공급자 사용권 문제다. 형제 작업 결과로 판단한다. 이 문서는 허용을 가정하지 않는다.

> **2026-10-24 검토 정정(PR-A, 결정은 바꾸지 않음 — 소유자 재결정 필요).** 위 2번(D-CV2 (b) 묶음)은 **가격 경계를 숨기지 못한다.** 위 표와 §13 D-CV2 행은 "묶으면 경계가 사라진다"는 전제로 (b)를 권장했고 소유자는 그 전제로 (b)를 골랐다. 그 전제가 틀렸다.
> - 엔진 원 코드는 정해진 요인 칸에만 나온다. `EV_NON_POSITIVE`는 `v_earnings_yield`·`v_fcf_yield`·`v_vs_industry`에만(`qgv_v2._metrics` `fail('EV_NON_POSITIVE', ('ebit_yield', 'fcf_yield'))`), `ROOT_NOT_BRACKETED`·`ROOT_NOT_CONVERGED`·`NUMERIC_OVERFLOW`는 `v_expectation_check`에만(역DCF `dcf.py:103,114,115`) 나온다. 그래서 공개 칸 + `PRICE_DEPENDENT_NOT_COMPUTABLE`이 원 코드를 일대일로 되돌려 준다.
> - 경계는 공개 입력만으로 계산된다: EV ≤ 0 ⇔ 가격 ≤ (현금 − 부채) ÷ 희석 주식수, 역DCF 근 없음 ⇔ 가격이 공개 FCF/주·공개 DCF 설정의 [DCF(하한 성장), DCF(상한 성장)] 밖. 합성 시험(검토 스크립트, 가격은 합성): 경계의 0.9배에서 세 칸이 묶음 사유, 1.1배에서 세 칸 모두 점수; DCF 구간 하단 0.98배·상단 1.02배에서 묶음 사유, 안쪽에서 점수.
> - 사유가 없어도 같은 사실이 드러난다: 세 요인의 null 무늬, V 축 점수·상태·`weight_available`, `rank`와 `qg_reference_order` 중 어느 쪽인지(합성 예: 경계 이하 V 없음·`qg_reference_order` 3, 경계 위 V 100·`rank` 2). **즉 이 누출은 V를 공개하는 것 자체에 딸려 온다.** 사유 어휘를 바꾸는 방법으로는 막을 수 없다.
> - 시험 `test_price_dependent_codes_sit_in_fixed_factor_slots_known_residual`이 이 칸 대응을 고정한다(어휘를 바꿔도 문서가 다시 틀려지지 않게).
> - 소유자 선택지(첫 게시 전): (i) 남는 누출을 수락하고 V를 게시 / (ii) 해당 행의 V를 통째로 비공개(규칙 변경·승인 필요; V가 NA인 것 자체가 신호라 누출을 다 없애지 못한다 — NA 사유를 다른 NA와 같은 일반 코드로 묶어야 줄어든다) / (iii) 다른 규칙. 결정 전에는 (b) 묶음을 표시 어휘로만 유지한다. 감사 기록 `public_price_boundary/AUDIT.md` §10-6(PR-B).

## 5. 재계산·의존 규칙, `publication_id`와 `calc_version`

### 5-1. 전체 재계산

- 게시마다 Universe 전체를 다시 계산한다. 한 샤드만 새로 받아도 같다. `sec_qgv2.publish`가 Q·G에서 이미 하는 방식(:336-359)과 같다.
- 입력: 같은 실행의 최종 `sec-qgv2.json` 전체 + 같은 기준일 종가 한 벌.
- 다른 회사의 입력·모집단·분류·철회·비중이 바뀌면 모든 회사의 백분위·순위가 바뀐다. 그래서 행 단위 캐시나 부분 갱신을 하지 않는다.
- 단면에서 빠지는 행: 철회(`stopped`, `qgv2-inputs.js:62`), calc_version 불일치(`:68`), 같은 CIK 두 번째 코드(`:70`), TARGET 행(`:72`), 가격 상태가 `SUPPLIED`가 아닌 행(V 단면만).
- 경기민감 기준(`cyclical_basis`)은 Python `qgv/playbook.py` `classify_types_v0`(:598)·`sector_for`(:670)로 만든다. JS `qgv-scores.js:173`와 같은 함수다(대조 fixture `tests/fixtures/playbook_reference_v1.json`).

### 5-2. 의존 그래프

```
sec-qgv2.json(같은 실행, sha256) ─┐
가격 묶음(기준일 D, HMAC 지문) ───┼─→ score_universe ─→ qgv-official.json
설정(type_config, dcf, 비중, SIC 그룹)┤
엔진 원본 해시(py, js) ────────────┘
```

- 위 입력 중 하나라도 바뀌면 새 게시본이다.
- 하나라도 준비되지 않으면 새 게시본을 만들지 않는다. 직전 정상본을 유지한다(§6).

### 5-3. `publication_id`

- `publication_id = 'qgvpub-' + sha256(정규 JSON 매니페스트)`.
- 매니페스트: `calc_version`, `v_calc_version`, `inputs[].sha256`, `price.provider`, `price.basis_date`, `price.adjustment_basis`, 가격 묶음 HMAC, `population.version`·`pooled_digest`, `weights_version`, `type_scope`, `config_versions`, `engine.*_sha256`.
- 시각은 넣지 않는다. 같은 입력을 다시 돌리면 같은 id다. 그때는 라이브 바이트를 그대로 둔다(불필요한 교체 없음).
- **2026-10-23 메모(D-CV7 (b)):** 아래 표의 `v_calc_version` 열은 쓰지 않는다. V 게시 규칙(U7)이 바뀌면 `calc_version`을 올린다. 매니페스트에서도 `v_calc_version`을 뺀다(§15-2).

| 바뀐 것 | `publication_id` | `calc_version` | `v_calc_version` |
| --- | --- | --- | --- |
| 새 거래일 종가 | 새 값 | 그대로 | 그대로 |
| 같은 날 종가 정정 | 새 값(HMAC이 바뀜) | 그대로 | 그대로 |
| 새 샤드 SEC 행, TARGET 행 | 새 값 | 그대로 | 그대로 |
| 철회·식별 복구·Universe 구성 | 새 값(`population.version`) | 그대로 | 그대로 |
| 공급자 교체(조정 기준 같음) | 새 값 | 그대로 | 그대로 |
| V 엔진 규칙·어댑터 일관성 규칙·DCF·유형 설정·SIC 그룹 설정 | 새 값 | 그대로 | **올림** |
| `v2_factors` 행 규칙 | 새 값 | **올림**(기존 규칙, `v2_factors.py:26-29`) | 그대로 |
| 같은 입력 재실행 | 같음 | 그대로 | 그대로 |

- `calc_version` 불일치 행은 지금처럼 단면 밖이다(`CALC_VERSION_MISMATCH`, `sec_qgv2.py:68-73`). 게시본에 사유로 싣는다.

## 6. 실패 상태와 마지막 정상본 규칙

| 상태 | 조건 | 게시본 | 상태 파일 | 화면 |
| --- | --- | --- | --- | --- |
| 정상 | 공급·검증 통과 | 새 게시본 | `OK` | 공식 결과 |
| 종목별 NA | 한 종목 가격 거부·입력 결측 | 새 게시본 안에 그 행 NA + 사유 | `OK` | 행마다 사유 |
| 공급 전체 실패 | 공급자 연결·인증·한도 실패, 또는 같은 기준일 공급 비율 < 기준(결정 D-CV5), 또는 기준일이 아직 없음 | **직전 정상본 그대로** | `SUPPLY_FAILED` + 코드 | "가격 갱신 실패 · 공식 결과 기준일 D 유지" |
| 검증 실패 | 엄격 검증기, 일관성 검사의 전역 실패(예: 통화 단위 전체 불일치), JS 대조 불일치 | **직전 정상본 그대로** | `VERIFY_FAILED` + 코드 | 같음 |
| 정상본 없음 | 첫 게시 전 | 없음 | `NO_OFFICIAL_YET` | "공식 QGV 아직 없음" + 최신 Q·G 참고 |
| 라이브 정상본이 깨짐 | 라이브 사본이 검증기 실패 | 복사하지 않음. 새 계산이 통과하면 새 게시본 | `OK` 또는 실패 코드 | 결정 D-CV16 |

- 마지막 정상본은 바이트 그대로 둔다. 기준일·`publication_id`·`verified_at`이 그대로다.
- 오래된 정상본은 경과 거래일로 표시한다(예: 2거래일 넘으면 "오래된 공식 결과"). 숫자는 결정 D-CV6.
- **최신 Q·G는 따로 참고로만 보인다.** 출처는 같은 시점의 `sec-qgv2.json`이다. 라벨: "최신 Q·G 참고 · 공식 QGV 아님". 옛 V와 합쳐 새 공식 순위를 만들지 않는다.
- **V 실패는 다른 파이프라인을 멈추지 않는다.** 원장(:114)은 V 단계 앞에서 끝난다. 원장 비공개 사본도 그 단계 안에서 끝난다(:107-108). 뉴스·공시 단계는 독립이다. V 단계는 종료 코드 0이다.

## 7. 일관성 검사(어댑터 단계, 엔진 앞)

가격 공급자 기록 필드: `close`, `basis_date`, `provider`, `adjustment_basis`, `symbol_key`. 검사에 실패한 기록은 그 종목 가격으로 쓰지 않는다. 엔진에는 가격이 없는 것으로 들어간다. 게시본 `price_status`에 아래 사유를 싣는다. 엔진 사유 `NO_DEVICE_PRICE`(`qgv_v2.py:353-354`)는 "기기" 표현이라 공식 화면에서는 `price_status`로 대신 보인다(엔진 코드는 그대로).

| 검사 | 규칙 | 실패 사유 | 근거·재사용 |
| --- | --- | --- | --- |
| 같은 증권·주식 종류 | `symbol_key` = 그 Universe 코드(거래소:티커) 그대로. 발행사 단위로 고르지 않는다. 다중 종류는 그 코드 종류의 가격 × 회사 전체 희석 주식수(기존 근사 규칙) | `PRICE_SYMBOL_UNMAPPED` | `QGV_V2_V_DEVICE.md:16`, 한 CIK 한 점 `qgv2-inputs.js:70` |
| 식별 충돌 | 철회된 Universe 코드의 기호와 같은 기호의 TARGET 행에는 가격을 주지 않는다 | `PRICE_IDENTITY_CONFLICT`(기존) | `qgv-scores.js:33-40,176-177` 규칙을 그대로 옮김 |
| ADR·보통주 | 해외 민간 발행인(20-F·40-F 제출) 행은 상장 증권이 보통주인지 ADS인지, ADS 비율이 확인된 표가 있을 때만 쓴다. 비율을 곱하지 않는다 | `ADR_RATIO_UNCONFIRMED` | `v2_factors.ANNUAL_FORMS`(:40). 결정 D-CV10 |
| 통화 | `close` 통화 = `v_inputs_v2.currency`. 환산하지 않는다 | 엔진 `CURRENCY_BASIS_UNCONFIRMED`(기존) | `qgv_v2.py:355-356` |
| 단위 | 통화 주단위(ISO 3자리)만. 센트·펜스(예: GBp)·천 단위 기록은 거부 | `PRICE_UNIT_INVALID` | V-SHARES-SCALE "곱하지 않음"(`v2_factors.py:235-252`) |
| 분할 기준(현재가) | 주식수 기간 끝(`diluted_shares.period_end`) 이후 기준일까지 분할이 있으면 그 종목 NA. 공급자는 분할 사건 또는 분할 계수를 줘야 한다 | `SPLIT_AFTER_SHARE_COUNT` | 주식수와 가격의 같은 기준. 결정 D-CV11 |
| 분할 기준(월말 종가) | 자기 과거 대비용 월말 종가는 **분할만 조정**된 값이어야 한다. 배당 조정·총수익 계열은 거부. 주당 EBIT 이력은 최신 주식수 기준이다 | `PRICE_ADJUSTMENT_BASIS_INVALID`(그 요인만 NA) | `v2_factors.py:1253-1281` |
| 조정 기준(현재가) | 현재가는 원 종가(분할 반영 시점 기준)만. 배당 조정 금지 | `PRICE_ADJUSTMENT_BASIS_INVALID` | EV = 가격 × 주식수(`qgv_v2.py:402`) |
| 같은 날짜 단면 | 모든 현재가 `basis_date` = 게시본 기준일 D. 다른 날짜 기록은 섞지 않고 그 종목 NA | `PRICE_BASIS_DATE_MISMATCH` | 기기의 출처 혼합(`qgv-scores.js:226-229`)을 없앰 |
| 임의 배수 금지 | 가격·주식수·부채·현금에 100·1,000·ADS 비율·추정 분할 비율을 곱하거나 나누지 않는다 | (위 사유로 NA) | `v2_factors.py:236-252` 원칙 |
| 계산별 NA + 사유 | 요인마다 엔진 사유를 싣는다. 가격 의존 사유는 D-CV2 형태로 | 엔진 사유 | `qgv_v2.py:344-347`, `qgv-scores.js:85-111` |

- 어떤 종목이 빠지면 다른 종목 백분위도 바뀐다. 그래서 거부 개수를 사유별로 `price.rejected`에 싣는다.
- 전역 실패: 한 사유가 거의 모든 행에서 나오면(예: 공급자가 전부 센트 단위) 검증 실패로 보고 직전 정상본을 유지한다. 기준은 D-CV5와 같이 정한다.
- PIT: 기준일 D 종가와 D 22시대 UTC에 받은 SEC 자료를 함께 쓴다. "지금" 점수이므로 허용한다. 그러나 백테스트 증거로는 쓰지 않는다(접수 시각 규칙은 D 영역).
- **2026-10-24 메모(PR-A, 소유자 결정 D3·D6·D7):** 위 표는 2026-10-18 설계(종가 공급자 가정)다. IEX 단일 날짜 출처로 구현한 실제 동작은 아래와 같고, 표의 일부 규칙은 구현되지 않았다(2026-10-24 검토로 "표의 규칙은 그대로"라는 처음 문구를 고침):
  - 가격 기록은 IEX 마지막 정규장 체결(`price_source`, 공식 종가 아님)이다. 기준일 D = 실행의 뉴욕 날짜 이하 마지막 TOPS 파일 날짜(D3). 주말·휴장일은 파일이 없어 직전 거래일, 반일 장은 확장 시간 표시(0x40) 체결을 버려 조기 마감 전 마지막 체결이다. 요청일과 실제 기준일을 둘 다 싣는다.
  - ADR·보통주(D7): `ifrs-full` 행 + 알려진 20-F·40-F 제출자(CIK 표 `qgv_official.FOREIGN_ANNUAL_FILERS`, 지금 ASML 1곳, 근거 `DCV_OPEN_ITEMS_20261019.md` D-CV10)를 분류 체계와 무관하게 `ADR_RATIO_UNCONFIRMED`로 둔다. `sec-qgv2.json`에는 서식 종류가 없어 표로 둔다.
  - 분할 기준(현재가, D6 (a)) — **표의 규칙(기간 끝 뒤~기준일 분할이면 NA)은 D6 (a)만으로는 구현되지 않는다(아래 D6 (b)가 일부를 맡는다).** 새 출처 없이 F_k 근거만 쓴다: 주식수 기간 끝 이후의 이력 항목이 `SPLIT_TIMING_UNCONFIRMED`면 `SPLIT_AFTER_SHARE_COUNT`. 그러나 그 근거는 주식수를 실은 서류 **접수 전** 분할이고, 그 서류는 주식수를 분할 뒤 기준으로 고쳐 싣는다(ASC 260). 그래서 이 규칙은 보수 규칙일 뿐이다. D6 (a)만으로는 주식수와 가격이 실제로 어긋나는 **접수 뒤~기준일** 구간을 근거가 없어 잡지 못한다: 그 구간에 분할이 있으면 행은 `SUPPLIED`로 남고 공식 V·순위가 분할 비율만큼 틀린다(다음 10-Q·10-K까지, 예: NVDA 2024 약 2.5개월). 이 구간은 아래 D6 (b)(2026-10-24 밤 소유자 결정 CV-SPLIT (ii))가 맡는다 — 저장소에 주식수 기간 끝 뒤 짧은 간격이 있는 종목만이고, 나머지는 잔여다. 검증된 분할 표 `SPLITS`는 비어 있다.
  - **2026-10-24 밤 메모(PR-A #400 `claude/central-v-core`, 소유자 결정 CV-SPLIT (ii) "보조 검사 추가: #400에 넣고 시험한다") — 분할 보조 검사 D6 (b).** `SUPPLIED` 행(식별·ADR·D6 (a) 규칙 뒤, 엔진 가격 전)에서 RAM 안에서만 IEX 원가격(체결 그대로, F_k로 나누지 않음)을 비교한다(`qgv_official.split_check`, `iex_monthend.raw_series`). 값을 바꾸지 않고, 걸리면 내지 않을 뿐이다.
    - 창: 주식수 기간 끝(`v_inputs_v2.diluted_shares.period_end`, D6 (a)와 같은 칸)이 든 달의 월말 체결부터 기준일까지(기간 끝이 주말 월말이면 그 달 마지막 거래일 체결이 첫 점이다; 문자 그대로 "기간 끝 이후 체결"로 읽으면 그 달이 빠져 기간 끝 다음 달의 분할을 놓치므로 이렇게 정했다). 기간 끝이 없으면 검사하지 않는다(미점검).
    - 계열: 비공개 월말가 저장소의 그 종목 원 월말 체결(기호·별칭·ROUND 규칙은 `month_closes`와 같다. 체결이 없거나 기호가 다른 달은 빼고 0으로 두지 않는다. 기준일 뒤 달은 읽지 않는다) + 기준일의 오늘 IEX 원가격(`day.quotes`).
    - 판정: 이웃한 두 점의 달력 간격이 **45일 이하**인 쌍만 본다. r = 뒤/앞이 분할 배수 n의 대역 안이면 걸린다: 정분할 |ln r + ln n| ≤ ln 1.25, 역분할 |ln r − ln n| ≤ ln 1.25, n ∈ {2, 3, 4, 5, 6, 8, 10, 15, 20, 25, 30, 40, 50}; 3:2(n = 1.5)는 허용폭 ln 1.10. 걸리면 `SPLIT_AFTER_SHARE_COUNT`(기존 상태 코드라 JS 판독기·벡터·가드는 그대로, V NA, D4 분모 밖). 45일을 넘는 쌍은 건너뛴다. 본 쌍이 하나도 없으면 미점검이고, 이 규칙 때문에 NA가 되지는 않는다.
    - **점검 ≠ 접수 뒤 분할 없음(2026-10-25 검토).** 기간 끝이 든 달의 월말 점이 없거나(저장소에 그 달이 없음, 체결 없음, 기호 불일치) 45일을 넘는 간격이 있으면 그 구간은 비교하지 않은 채로 남는다. 그 행이 다른 짧은 쌍을 봐서 `split_checked`에 들어가도 그렇다. 기간 끝 달 점이 없는 점검 행은 `split_lead_unchecked`로 센다(긴 간격 쌍은 `split_gap_skipped`). 지금 저장소(회계연도 말월만)에서 `split_checked`에 들어올 행의 다수가 이 모양이다: 9월 결산 종목의 주식수가 6월 10-Q에서 오면 저장소에는 09-30 점만 있어 09-30 → 기준일만 보고, 10-Q 접수 → 09-30 사이(접수 뒤 분할이 있을 자리)는 보지 않는다. 시험 `test_d6b_a_checked_row_without_the_period_end_month_counts_its_lead_stretch_unchecked`.
    - 대역 전체는 r ∈ [0.016, 0.733] 또는 [1.364, 62.5]다. 그래서 45일 안의 진짜 큰 움직임(약 −27% 이하, +36% 이상)도 걸린다(보수적 오탐, 예: 한 달 −45%; 그 행은 다음 서류의 주식수 기간 끝이 그 달을 지날 때까지 V NA). 3:2 분할에 10%를 넘는 움직임이 겹치면 놓친다(예: +15%). 1:50·50:1 대역 밖 비율도 놓친다. 기간 끝~서류 접수 사이 분할(주식수가 이미 고쳐 실림)도 D6 (a)처럼 예방으로 걸린다.
    - 결과는 게시기 한 줄에 개수만 남긴다: `split_checked`·`split_flagged`·`split_unchecked`(그중 `split_unchecked_no_period`)·`split_lead_unchecked`(`split_checked` 중) 행 수와 `split_gap_skipped` 쌍 수(Universe 코드 기준, 가격을 읽은 실행에서만). 게시본에는 새 필드가 없다(행 `price_status`가 이미 말한다). 로그와 파일에는 종목·가격·비율·날짜를 남기지 않는다(공개되는 것은 아래 행 상태 하나). JS 쌍둥이 대조는 바뀌지 않는다(상태는 Python이 정하고, 걸린 행은 두 쪽 모두 가격이 없다).
    - **공개되는 가격 유래 1비트(2026-10-25 검토).** D6 (b) 적중은 그 행의 공개 `price_status` `SPLIT_AFTER_SHARE_COUNT`로 나간다. D6 (a)는 공개 `sec-qgv2.json`과 빈 `SPLITS`만으로 누구나 다시 계산할 수 있으므로, D6 (a) 근거 없이 이 상태인 행은 D6 (b) 적중임이 드러난다. 그것은 종목별로 "45일 안의 IEX 원가격 비율이 분할 대역에 들었다"(분할, 또는 약 −26.7% 이하·+36.4% 이상의 진짜 움직임)는 가격에서 나온 사실이다. 가격·비율 값 자체는 나가지 않는다. 이 비트는 V 공개에 딸린 누출(CV-LEAK, 첫 게시 점검표 0절, `public_price_boundary/AUDIT.md` §10-6-4)과 같은 결정 범위에 둔다.
    - **저장소 한계(사실):** 지금 U8 저장소(stamp 20261023, `iex-monthend/1`, 2021-06~2026-09의 62개월, 달마다 기호 1~310개)는 달마다 **그 달이 회계연도 말월인 종목만** 갖는다. 그래서 한 종목의 "최신 원 월말가"는 지난달이 아니라 최신 회계연도 말월(0~15개월 전)이다. 긴 간격 한 번의 비교는 큰 진짜 움직임과 분할을 헷갈리므로 짧은 간격만 본다. 지금 저장소로는 대부분의 행에 주식수 기간 끝 뒤 짧은 간격이 없어 미점검이고, 그 행의 접수 뒤 분할은 여전히 잡지 못한다(잔여). 전 종목에 효과가 나려면 Universe 전 종목의 최근 월말가를 저장소에 보충해야 한다(별도 작업, 소유자 승인 필요; 이번 변경에 없음).
    - 시험: `tests/test_qgv_official.py` `test_d6b_*`(2:1·10:1·역 1:4·3:2 ±10% 걸림, 3:2 +15% 놓침, −45% 걸림, +30% 안 걸림, 60일 건너뜀, 기간 끝 없음, 창 앞 달 무시, PSKY→SKYD 별칭, NA는 0이 아님, D6 (a) 그대로, 끝에서 끝까지 게시·JS 대조·한 줄; 2026-10-25: 기간 끝 달 점 없는 점검 행 `split_lead_unchecked`, 달력에 없는 저장소 날짜는 그 달만 빼고 계속), 잔여 `test_residual_without_short_store_steps_a_split_after_the_count_filing_is_not_detected`.
  - 구현하지 않은 표의 사유 코드: `PRICE_UNIT_INVALID`(IEX TOPS 가격은 1/10,000 달러 정수 하나로만 오고 센트·천 단위 변종이 없다; 파서가 범위 밖 값을 거부한다 `PARSER_PRICE_INVALID`), `PRICE_BASIS_DATE_MISMATCH`(가격은 TOPS 파일 하루치 하나에서만 나와 날짜가 섞일 수 없다), `PRICE_ADJUSTMENT_BASIS_INVALID`(현재가는 체결 그대로 `AS_TRADED`, 월말가는 아래 F_k 규칙으로 대신한다). 셋 다 `iex_hist.STATUS_CODES`에 없고, 단일 날짜 IEX 출처에는 해당이 없다. 다른 출처를 붙이면 다시 정해야 한다.
  - 분할 기준(월말 종가): IEX 월말가는 분할 **미조정**이다. 그래서 위 "분할만 조정" 줄 대신 §15-1의 `원 종가 ÷ F_k`를 쓴다(F_k `null`이면 그 달 제외).

## 8. 프론트엔드 버전 관리(#321 재사용, 네 가지 시각)

### 8-1. 읽기·교체

- `DataRefresh`(#321 `data-refresh.js`)의 `readCore`(:58-66) 묶음에 `qgv-official.json`·`qgv-official-status.json` 판독기를 더한다.
- 새로고침은 **전부 아니면 전무**다(:88-104). 하나라도 읽기 실패면 아무것도 바꾸지 않는다. 그대로 쓴다.
- 성공하면 `public-data-updated`(:23, :106-110)가 나간다. `QgvScores` 메모는 입력 객체 동일성으로 판정한다(`qgv-scores.js:65-66`, `:249`). 새 묶음은 새 객체라 메모가 저절로 버려진다.
- 신선도 재판정(`rejudge` :128-137)에 게시본 규칙(기준일 경과 거래일)을 더한다.

### 8-2. 같은 게시본 보장

- 리더보드·기업 화면·레이더·커버리지가 **같은 묶음 세대(G)** 의 같은 게시본 객체를 읽는다.
- 각 화면은 그린 `publication_id`를 `data-publication-id`로 남긴다. `DataRefresh.publication()`(:140-141)의 id와 다르면 다시 그린다. 브라우저 시험이 네 화면의 id 일치를 확인한다(기존 `update_propagation` 시험 확장).
- 공식 결과는 게시본 행만 쓴다. 기기 가격은 공식 결과에 들어가지 않는다.
- 다시 그리기 규칙은 #321 그대로다. 개인 작업이 있는 화면은 다시 그리지 않고 알림만 띄운다(:27-29, :111-116, :181-184). 열린 상세는 유지한다(`app.js:662-664`). 가중치 편집기에서 입력 중인 값과 메모는 덮어쓰지 않는다. 미리보기 결과만 "새 게시본으로 다시 계산됨"으로 표시한다.

### 8-3. 네 가지 시각을 나눈다

| # | 시각 | 출처 | 화면 문구 예 |
| --- | --- | --- | --- |
| 1 | 자료·가격 기준 | `times.price_basis_date`(뉴욕 거래일), `inputs[].as_of`, 행 `fiscal_year_end` | "가격 기준 D 종가 · 공시 기준 …" |
| 2 | 수집 | `times.price_collected_from/to`, 행 `acquired_at` | "가격 수집 … UTC · 공시 수집 …" |
| 3 | 검증·실제 게시 | `times.verified_at`(실행 안 검증). 실제 배포 시각은 파일에 없다 | "검증 … UTC · 배포 시각은 실행 기록 기준" 또는 "이 기기 첫 확인 …"(결정 D-CV13) |
| 4 | 화면 확인 | `DataRefresh` `checked_at`(:94, :167) | "마지막 확인 …" |

- `generated_at`을 배포 성공처럼 쓰지 않는다. 운영 보고도 같다(`CURRENT_HANDOFF.md:8`).
- 아티팩트는 verify 뒤에 바뀌지 않는다. 그래서 배포 시각을 파일 안에 넣을 수 없다. 이 한계를 숨기지 않는다.

### 8-4. 기존 작업 유지

| PR | 유지 방법 |
| --- | --- |
| #317 V 커버리지·사유(병합) | `vCoverage`(`qgv-scores.js:260-287`) 정의를 그대로 쓴다. 입력만 "기기 가격" 대신 행 `price_status`. 라벨 "이 기기" → "공식 게시본". 같은 정의의 집계를 게시본 `coverage`에도 싣는다(Python 쌍둥이 + JS 대조) |
| #311 레이더 | 핵심 Q·G·V는 게시본에서. 가격 축은 기기 전용(C 영역) |
| #318 QGV/QG 분리 | 게시본 `rank`(V 있는 행)와 `qg_reference_order`(Q·G만)를 따로 싣는다. 화면 규칙과 같다 |
| #319 가격 시각 | 개인 가격 미리보기에 그대로 둔다. 읽은 시각과 가격 시각 분리 유지 |
| #320 각주 범위 | 각주가 순위 모집단을 게시본 `population.pooled_count` 기준으로 쓴다. TARGET 보기는 "TARGET 안 순위" |
| #321 새로고침 | 위 8-1 |

## 9. 개인 미리보기 동등성

### 9-1. 결론

- 공개 V 요인 점수를 그대로 쓰면 **엔진과 정확히 같다.** 조건이 셋 있다.
  1. V 요인 점수를 **전체 정밀도**(JSON 왕복이 정확한 배정밀도)로 싣는다.
  2. 엔진에 "게시된 V 요인 점수" 입력 경로를 하나 더한다(엔진 변경, 다음 라운드).
  3. 벡터 시험으로 두 경로가 같음을 고정한다.
- 조건 2 전까지 V 내부 비중을 바꾸는 미리보기는 **"근사"** 로 표시하거나 막는다. 지금 엔진은 V 요인을 가격에서만 만든다(`qgv_v2.py:635-664`). 가격 없이 같은 V를 만들 방법이 없다. 가짜 가격을 만들어 넣는 것은 금지다.

### 9-2. 항목별 대조(`score_universe` 개인 경로)

| 엔진 규칙 | 엔진 코드 | 공개 필드만으로 같게 되나 | 필요한 공개 필드 |
| --- | --- | --- | --- |
| V 요인 점수 | `_metrics`·`_cross`(:336-420, :446-471, :635-664) | 예. 요인 점수는 가중치·프리셋·관문·유형 토글과 무관하다. 경기민감 기준은 소속도와 `cyclical_basis`로만 정해지고 개인 설정에 따라 바뀌지 않는다(:634-635) | `factors.v_*.{score,reason,basis}` |
| 결측 재정규화 | `axis_score`·`_custom_axis_score`(:73-140) | 예. 있는 요인과 없는 요인만 알면 된다 | 요인 `score` null 여부 |
| 축 50% 규칙 | `MIN_AXIS_WEIGHT`(:41, :100, :136) | 예. 개인 비중 기준으로 다시 판정 | 같음 |
| Q·G 축(공식 내부 비중) | `_published_axis`(:474-482, :622-626) | 예 | `axes.Q/G.score` |
| Q·G 축(개인 내부 비중) | 요인에서 다시 계산(:620-624) | 예 | Q·G 요인 10개(이미 공개) |
| 유형 비중 | `type_axis_weights`·`composite_weights`(:237-275, :304-310) | 예. 소속도는 공개 지표 `revenue_cagr_3y`에서 나온다(:286-301) | `metrics.revenue_cagr_3y` 또는 `type_weights`·`selected_types` |
| 관문(Q 업종 백분위) | `_cross(Q)`(:631), `GATE_PERCENTILE`(:38, :672) | 예. 개인 Q 내부 비중이면 전체 단면 Q를 다시 계산한다. 모든 단면 행의 Q 요인이 공개라 된다 | `in_cross_section`, `industry_group`, `cik`(행 전부) |
| 종합 | :679-694 | 예 | 축 점수와 비중 |
| 반올림을 고르면(D-CV3 (b)(c)) | — | **아니오.** 축·종합 끝자리가 달라지고 동점 순서가 바뀔 수 있다 | 미리보기 "근사" 표시 필요 |

### 9-3. 필요한 엔진 확장(제안, 다음 라운드)

- `companies[i].v_factors`(게시본의 V 요인 5개 `{score, reason, basis}`)를 받으면 `_metrics`·`_cross`를 건너뛰고 그 값을 쓴다. JS도 같은 줄에서 같게 한다.
- Q·G가 이미 공개 축을 받는 방식(`_published_axis`)과 같은 모양이다. 새 계산 규칙이 아니다. 그래서 `v_calc_version`을 올리지 않는다.
- 시험: 모든 벡터 사례에서 `score_universe(가격 경로)`와 `score_universe(게시 V 요인 경로)`의 결과가 `detail` 가격 값(null)만 빼고 같아야 한다. 프리셋 4개·관문 켬/끔·유형 켬/끔·개인 비중(`qgv_v2_custom_vectors_v1.json`) 전부.

### 9-4. 개인 가격 미리보기(#319)와 섞지 않기

- 사용자 기기 가격으로 계산하는 미리보기는 기존 기기 경로 그대로다. 라벨 "개인 가격 미리보기 · 공식 아님".
- 한 회사만 기기 가격으로 바꾸고 나머지는 공식 V를 쓰는 혼합은 하지 않는다. 다른 게시본의 값을 섞는 것과 같다. 기기 가격 미리보기는 단면 전체를 기기 가격으로 계산한다.

## 10. D12 재설계(Universe 전체 리더보드)

기기 가격 확장만 멈춘다. 아래는 게시본 위에서 설계한다.

### 10-1. 게시본 리더보드

- 행 = 게시본 `rows`. 순서 = `rank`. 화면은 공급자를 모른다. 공급자 이름은 출처 표시 문자열로만 보인다. 공급자를 바꿔도 화면 코드는 그대로다.
- 정렬·필터는 `leaderboard-screen.js` `sortRows`(:45-57)를 재사용한다. 순위 칸은 언제나 공식 `rank`다.
- 프리셋 칩(우량·성장·가치)과 관문 끔은 게시 요인·축 점수로 기기에서 다시 계산한다(§9-3 확장 뒤 정확). 라벨에 프로필 id를 보인다. 공식 기본은 균형·관문 켬이다.

### 10-2. TARGET v0와 모집단 분리

- 모집단 = 게시본 단면(Universe504, LIVE/STALE, 한 CIK 한 점). `population.pooled_count`로 보인다. `populationOf`(:59-60) 정의와 같다.
- TARGET v0 19종목(`app.js:1184`, `watchlist.js:4`)은 **보기 범위**다. 모집단이 아니다. TARGET 행은 단면에 점으로 들어가지 않는다(`qgv2-inputs.js:72`).
- TARGET 회사의 행: 자료가 있으면 TARGET 행을 쓴다(현재 규칙 `qgv-scores.js:42`). 그 회사의 전체 순위는 TARGET 행 종합을 전체 순서에 넣되 같은 CIK의 Universe 점을 바꿔 넣어 정한다. 백분위의 "자기 CIK 점 교체"(`qgv_v2.py:446-471`, `QGV_V2_V_DEVICE.md:82`)와 같은 뜻이다. 결정 D-CV8.

### 10-3. 전체 순위와 필터·포트폴리오 순위

| 순위 | 정의 | 출처 |
| --- | --- | --- |
| 전체 순위 `rank` | 게시본 단면 전체에서 공식 종합 순(동점은 티커, `qgv-scores.js:195`). V 있는 행만(#318). 한 CIK 한 순위(D-CV9) | 게시본 |
| 필터 안 순위 | 같은 순서를 필터(업종·관심·검색)로 줄인 뒤 1부터 | 기기 계산(가격 없음) |
| TARGET·포트폴리오 안 순위 | 같은 순서를 TARGET 19로 줄인 것 | 기기 계산 |

- 세 순위는 이름을 따로 쓴다. 필터 순위가 전체 순위를 대신하지 않는다.

### 10-4. N10/N15/N20 모델 포트폴리오 선정 흐름

1. 입력: 게시본 하나(`publication_id`, `v_calc_version`, 기준일 기록).
2. 자격: 공식 `rank`가 있음(V 포함). 축 50% 규칙 통과. 가치 함정 관문 행 제외. 재무 안전 미달 제외(순부채/EBITDA ≥ 3 또는 이자보상 < 3). 업종 하위 묶음당 최대 4. 기존 TARGET v1 규칙 그대로(`USER_DECISIONS_PENDING.md:491-492`).
3. 선정: 자격 행을 전체 순위 순으로 N개. N15 주검정, N10·N20 민감도(`USER_DECISIONS_PENDING.md:135`).
4. 비중: 동일 비중(세트 B 규칙, :493).
5. 기록: 선정 결과에 `publication_id`·규칙 버전·선정일을 붙인다. 소급하지 않는다. 분기 재선정.
6. 금융사는 V가 없어서 공식 순위가 없다(#318). 그래서 자동으로 빠진다. 이것은 금융 V 미지원의 결과다. 중앙화로 풀리지 않는다.
7. 계산 위치: 게시본만으로 결정적으로 나온다. 먼저 기기 계산으로 두고, 공개 파일은 만들지 않는다. 결정 D-CV15.

## 11. 재사용 지도

| 파일 | 재사용 | 바꿈(다음 라운드, 승인 뒤) | 새로 |
| --- | --- | --- | --- |
| `src/qgv/qgv_v2.py` | `score_universe`·`axis_score`·`type_axis_weights`·`weights_id`·`TYPE_SCOPE` 전부 | `v_factors` 입력 경로(§9-3) | — |
| `web_assets/qgv-v2.js` | `scoreUniverse` 쌍둥이 | 같은 확장 | — |
| `tests/fixtures/qgv_v2_vectors_v1.json`, `qgv_v2_custom_vectors_v1.json`, `tools/qgv_v2_reference.py`, `tools/qgv_v2_node_test.js` | 그대로 | 게시 V 요인 경로 동등 사례 추가 | — |
| `src/qgv/v2_factors.py` | `v_inputs_v2`(:1177-1295), `CALC_VERSION`, V-SHARES-SCALE, SPLIT | 없음 | — |
| `src/universe/sec_qgv2.py` | `merge`·`publish`·`require_qgv2`·`encode`. 파일 형태·"가격·순위 없음" 규칙 그대로 | 없음 | — |
| `src/universe/sec_universe_shares.py` | `shard_day`(기준일), `_iso`, `_clock` | 없음 | — |
| `tools/sec_universe_shares.py` | 이전 사본 먼저 쓰기 패턴(:368-395), `fetch_previous_qgv2` 방식(:130-133) | 없음 | — |
| `tools/public_screens_pipeline.py` | 원자적 쓰기(:19-40) | 없음 | — |
| `web_assets/qgv2-inputs.js` | `fromInputs`·`normalize` 규칙(정답) | 없음 | Python 쌍둥이 `qgv/qgv2_inputs.py` + JS 대조 시험 |
| `src/qgv/playbook.py` | `classify_types_v0`, `sector_for`(경기민감 기준) | 없음 | — |
| `src/qgv/dcf_parameters.py`, `type_config.py` | 기본 설정 로더 | 없음 | — |
| `web_assets/qgv-scores.js` | `REASON`·`coverageFor`·`vCoverage`·`exploreGroup`·순위 규칙 | 게시본 모드: 행을 게시본에서 읽음. 기기 가격 경로는 개인 미리보기로만 | — |
| `web_assets/leaderboard-screen.js` | `sortRows`, `populationOf` | 순위 열을 게시본 `rank`로. 필터 순위 별도 칸 | — |
| `web_assets/app.js` | `identityCompanies`(TARGET 보기), `repaintScores` | 공식 점수에 기기 시세(`refreshQgv2Quotes` :670-672)를 넣지 않음 | — |
| `data-refresh.js`(#321) | 묶음 읽기·전부 아니면 전무·이벤트·재판정 | 판독기 목록에 게시본 2개 추가, 기준일 경과 재판정 | — |
| `tools/pages_artifact_guard.py` | 민감 키 검사·파일 허용 목록·파일별 검증기 | §12-3 제안 | — |
| `tools/pages_freshness_guard.py` | 라이브 대조 구조(`ROW_FILES` :179-187, `compare` :414-) | §12-5 제안 | — |
| `tools/published_coverage.py` | 개수만 출력 원칙 | V 개수 줄 추가(`PUBLISHED_V_COVERAGE`) | — |
| `src/public_price_boundary.py` | `block_public_route`, 출처 허용 목록 방식 | §12-1 제안 | — |
| `tests/test_public_price_boundary.py` | 모든 기존 시험 그대로 | 새 시험 추가만 | — |
| `.github/workflows/sec-daily-public-inputs.yml` | collect·verify·deploy 구조, 동시 실행 | V 단계 1개, verify 시험, deploy 검사 | — |
| `.github/workflows/cockpit-pages.yml` | 보존 단계(:33-41) | 게시본 보존 한 줄 | — |
| — | — | — | `providers/price_provider.py`(추상 + 공급자 1개), `tools/qgv_official_publish.py`, `src/qgv/qgv_official.py`(스키마·`require_qgv_official`·`publication_id`), `web_assets/qgv-official.js`(판독기) |

## 12. 기존 Actions 가격·공개 가격 경계의 좁은 변경 — **제안(PROPOSAL)**

> **유효 조건:** 가격 공급자와 그 사용권(수집·계산·파생 순위 공개)이 확인된 뒤. 지금은 아무 가드도 바꾸지 않는다. GSQ 결정 등록부(`pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md`)에 새 항목을 append-only로 기록하고 승인받은 뒤 별도 PR로 한다.

### 12-1. 지금 경계(사실)

- Actions 도구의 네트워크 출처는 SEC URL 허용 목록뿐이다(`src/public_price_boundary.py:42-61`, `:77-80`). 가격 엔드포인트는 막힌다(`test_public_price_boundary.py:93-98`, `:189-201`, `:246-249`).
- 옛 가격 수집기는 진입 즉시 막힌다(`BLOCKED` :59-77, 시험 :80-90). 감사 경로 27+1개(`AUDITED_ROUTES` `public_price_boundary.py:82-111`)는 AUDIT.md 표와 같아야 한다(시험 :123-129).
- 공개 아티팩트는 민감 키(`rank`, `vscore`, `totalscore`, `price`, `marketcap` 등, `pages_artifact_guard.py:149-159`)를 막는다. 파일 허용 목록(:143)과 파일별 검증기(:223-300)가 있다.
- `sec-qgv2.json`은 가격·순위가 없어야 한다(`sec_qgv2.py:22`). 판독기도 그 키가 있으면 거부한다(`qgv2-inputs.js:78-80`).
- 문서 규칙: V 점수·순위는 공개 파일에 남기지 않는다(`QGV_V2_V_DEVICE.md:3`). 이번 중앙화 승인이 이 문장을 바꾸는 근거가 된다(문서 개정은 승인 기록 뒤).
- AUDIT.md §1은 실제 가격·가격 기반 파생값을 공개하는 경로를 "정리 필요"로 본다(:13-17). §6-2는 가격 기반 순위의 공개 범위를 사용자 결정으로 남겼다(:79).

### 12-2. 바꾸지 않는 것

- `AUDITED_ROUTES`·`BLOCKED`·기존 시험 전부. 옛 가격 수집기(`fetch_tiingo_prices.py` 등)는 계속 막는다. 공급자가 같아도 새 어댑터로 간다.
- `sec-qgv2.json`의 가격·순위 없음 규칙과 `qgv2-inputs.js:78-80`.
- 민감 키 목록 자체.
- 원장·뉴스·공시·기존 파일의 검증기.

### 12-3. 가장 좁은 변경(제안)

1. **출처 한 개.** `public_price_boundary.py`에 `PRICE_PROVIDER_URL_PATTERNS`(공급자 1개의 정확한 URL 형태)와 `require_price_source(kind, url)`를 더한다. 허용 호출자는 `ACTIONS_PRICE_ROUTES = ('implementation/tools/qgv_official_publish.py',)` 한 개. 기존 `AUDITED_ROUTES`와 따로 둔다(감사 표 시험 :123-129이 깨지지 않게).
2. **RAM 전용.** 어댑터는 읽은 기록을 고정된 메모리 객체로만 돌려준다. 저장·캐시·업로드 함수가 없다. 시험: 가격을 받는 동안 `Path.write_*`·`mkdir`를 실패하게 패치해도 통과해야 한다(:85-86 방식). 표준 출력에 가짜 가격 카나리아가 없어야 한다.
3. **게시본 파일 두 개만 허용.** `ALLOWED_NAMES`(:143)에 `qgv-official.json`·`qgv-official-status.json`을 더한다. 검증기 `require_qgv_official`로 정확한 키 집합을 강제한다.
4. **민감 키 예외는 경로 한정.** 키 이름을 바꿔 검사를 피하지 않는다. 대신 `qgv-official.json` 안의 정확한 경로(`rows.*.rank` 등 순위·점수 경로)만 예외 목록 `PUBLIC_SCORE_PATHS`로 둔다. `price`·`marketcap`·`cost` 등 가격 키는 예외 없이 그대로 막는다. 검증기는 추가로 `close`, `ev`, `enterprise_value`, `ebit_yield`, `fcf_yield`, `implied_growth`, `expectation_gap`를 어디서든 금지한다.
5. **워크플로 정적 시험.** V 단계에 `actions/upload`·`actions/cache`·`git push`·`RAW_REPO_TOKEN`이 없고, 공급자 Secret은 그 단계 `env`에만 있음을 확인한다(:133-151 방식).
6. **감사 기록.** AUDIT.md에 새 절을 append-only로 더한다. 새 경로 한 개, 게시본에 가격 값 없음, 복원 분석(§4-4) 요약.

### 12-4. 프론트 쪽

- 새 판독기 `qgv-official.js`는 `sec-qgv2.js`처럼 엄격 검증 후에만 값을 쓴다. 가격 키가 있으면 거부한다.

### 12-5. 신선도 검사(제안)

- 게시본: 아티팩트 `price_basis_date`가 라이브보다 이르면 거부(`OLDER`). 같은 `publication_id`면 바이트가 같아야 한다(`EQUAL`). 다른 id인데 기준일이 같으면 입력 해시가 바뀌었는지 확인한다.
- 상태 파일: 비교하지 않는다(시도 기록일 뿐).
- 라이브 게시본이 깨졌을 때 전체 배포를 막을지(지금 패턴 `PAGES_FRESHNESS_LIVE_INVALID`) 게시본만 실패로 볼지는 결정 D-CV16.

## 13. 소유자 결정 필요

| 번호 | 무엇 | 선택지 | 권장안 | 근거 |
| --- | --- | --- | --- | --- |
| D-CV1 | 가격 공급자·사용권 | 형제 작업 결과 | 사용권 확인 전 구현 착수 안 함 | 파생 순위 공개까지 포함한 권리가 전제다 |
| D-CV2 | 가격 의존 사유 공개 형태 | (a) 원 코드 공개 (b) `PRICE_DEPENDENT_NOT_COMPUTABLE` 하나로 묶음 (c) 축 사유만 | **(b)** | `EV_NON_POSITIVE`·`ROOT_NOT_BRACKETED`는 가격 경계를 바로 준다(§4-4). 점수는 그대로다 |
| D-CV3 | V 요인 점수 정밀도 | (a) 전체 정밀도 (b) 소수 1자리 (c) 정수 | **(a)** | 반올림은 순서 정보를 거의 못 가린다. 대신 미리보기 정확성과 자기 검증을 깬다 |
| D-CV4 | 개인 미리보기 | (a) 엔진에 게시 V 요인 입력 추가 + 벡터 (b) "근사" 표시 (c) V 비중 미리보기 막기 | **(a)**, 그 전까지 (b) | 중복 엔진 없이 정확히 같아진다(§9) |
| D-CV5 | 공급 전체 실패 기준 | (a) 가격 무관 V 자격 행의 95% 이상 같은 기준일 (b) 90% (c) 기준 없음(부분 게시) | **(a)** | 빠진 행이 많으면 모든 회사 백분위가 흔들린다. 숫자는 고정값으로 게시본에 싣는다 |
| D-CV6 | 오래된 정상본 표시 | (a) 2거래일 넘으면 "오래된 공식 결과" (b) 5거래일 (c) 숨김 | **(a)**, 숨기지 않음 | 값은 정상이고 기준일이 오래됐을 뿐이다. 기준일을 크게 보인다 |
| D-CV7 | 버전 필드 | (a) `v_calc_version` 새로, `calc_version`은 입력 규칙 그대로 (b) `calc_version` 하나로 합침 | ~~(a)~~ → **(b)** | **메모: 2026-10-23 소유자 지시로 v_calc_version 없이 calc_version 하나로 통합.** 「calc_version은 U7과 묶어 한 번만 올리고, 원장 구간도 한 번만 나눈다」. `qgv2-calc/2026-10-23.1`이 그 한 번이다(§15-2) |
| D-CV8 | TARGET 회사 순위 | (a) TARGET 행을 CIK 점 교체로 전체 순서에 넣음 (b) Universe 행만 (c) 둘 다 표시 | **(a)** | 화면마다 같은 행을 쓰고, 기존 "자기 CIK 점 교체" 규칙과 같다 |
| D-CV9 | 다중 종류 순위 | (a) 한 CIK 한 순위(대표 코드) (b) 코드마다 순위 | **(a)** | 단면이 한 CIK 한 점이다. 같은 회사가 두 번 오르지 않는다 |
| D-CV10 | ADR·해외 발행인 | (a) 상장 증권·비율 표 확인 전 NA (b) 보고 통화 = 가격 통화면 허용 | **(a)** | 희석 주식수는 보통주 기준이다. 비율을 모르면 EV가 틀린다. 건수는 이번에 세지 않았다 |
| D-CV11 | 분할 확인 근거 | (a) 공급자 분할 사건·계수 필수 (b) 원 종가/조정 종가 비율 변화로 감지 (c) 확인 생략 | **(a)**, 없으면 (b) | 가격과 주식수의 기준이 같아야 한다. (c)는 금지 권장 |
| D-CV12 | 실행 안 JS 대조 | (a) collect에 node 설치 후 같은 RAM 입력으로 Python·JS 대조 (b) 벡터 시험만 | **(a)** | 실제 입력에서 두 엔진이 같음을 매번 확인한다. 가격은 파이프로만 넘긴다 |
| D-CV13 | 게시 시각 표시 | (a) `verified_at` + "이 기기 첫 확인" (b) HTTP `Last-Modified` (c) 다음 실행이 직전 배포 시각 기록 | **(a)** | 파일 안에 배포 시각을 넣을 수 없다. 생성 시각을 배포 성공처럼 쓰지 않는다 |
| D-CV14 | 게시본 이력 | (a) 공개는 최신본만 (b) 공개 이력 누적 (c) 최신본 + 비공개 보관 | **(a)**, (c)는 권리 확인 뒤 | 이력이 길수록 순위 변화로 상대 가격 정보가 쌓인다. Frozen·원장은 바꾸지 않는다 |
| D-CV15 | 모델 포트폴리오 위치 | (a) 게시본에서 기기 계산 (b) 중앙 파일 | **(a)** 먼저 | 게시본만으로 결정적이다. 새 공개 파일 없이 시작한다 |
| D-CV16 | 라이브 게시본 손상 | (a) 게시본만 실패 처리, 다른 파일 배포 계속 (b) 지금 패턴대로 전체 배포 거부 | **(a)** | V 실패가 뉴스·원장 공개를 멈추면 안 된다는 소유자 규칙 |

## 14. 하지 않은 것

- 코드·워크플로·가드·엔진·화면 변경 없음. 시험 실행 없음(문서만).
- 가격 조회 없음. 공급자 호출 없음.
- 금융업 V·일반 기업 입력 결측은 다루지 않았다. 각각 `FINANCIAL_V_RESEARCH_PREP_20261018.md`, `V_GENERAL_COVERAGE_20261018.md`의 과제다.

## 15. 2026-10-23 추가: 분할 기준 계수 F_k, calc_version 통합, 원장 구간 분할(설계)

- 작성: 2026-10-23 UTC / 2026-10-24 KST. lane cv-fk. 근거: 소유자 결정 GSQ-024 계획 A, Main 지시 2026-10-23.
- 계산 변경 PR(병합은 소유자 승인 뒤). 엔진(`qgv_v2.py`·`qgv-v2.js`)은 바꾸지 않는다.

### 15-1. F_k(`share_basis_factor`)와 적용 위치

- 문제: `ebit_per_share_history` 값은 최신 주식수 기준이다(분할 반영, `v2_factors._v_inputs` 규칙 SPLIT). IEX HIST 월말 종가는 분할 **미조정**이다.
- 게시: `sec-qgv2.json` 각 `ebit_per_share_history` 항목에 `share_basis_factor` F_k를 싣는다. 가격 없이 SEC 자료만 쓴다.
- 뜻: 그 회계연도 말월 월말의 거래 기준 주식수 × F_k = 게시 기준 주식수. 그래서 **게시 기준 가격 = IEX 원 월말 종가 ÷ F_k**.
- 예: FY-2 뒤 10:1 분할 → FY-4~FY-2는 F=10, FY-1·FY0은 F=1. 원 종가 1,000 → 100.
- 각 항목의 **자기 보고 기준**에서 나온다. 분할 날짜만으로 정하지 않는다. 가격 없는 확인식: F = (EBIT ÷ 그해 10-K 보고 주식수) ÷ 게시값. WSM(2:1, 2024-07)은 FY2022~2024가 정확히 2.0이다.
- NA: `null` + `share_basis_factor_reason`. `SHARE_BASIS_UNCONFIRMED`(보고 기준을 잇지 못함), `SPLIT_TIMING_UNCONFIRMED`(월말 뒤·10-K 접수 전 분할 가능성). 1.0으로 가정하지 않는다.
- 규칙 전문·실데이터 결과: `QGV_V2_QG_METHOD.md` V-PRICE-BASIS.
- **적용 위치(Main 결정 2026-10-23):** 중앙 V 어댑터(cv-core lane)가 IEX 원 종가로 `month_closes`를 만들 때 `원 종가 ÷ F_k`를 넣는다. 엔진은 그대로 `month_close`를 읽는다.
  - F_k가 `null`인 달은 `month_closes`에 넣지 않는다. 그 해는 자기 과거 대비에서 빠진다(`HISTORY_TOO_SHORT` 규칙 그대로). 0이나 1로 채우지 않는다.
  - `fcf_per_share_history`에는 싣지 않는다(파일 크기). 같은 `fiscal_year_end`의 F를 쓴다. 지금 가격과 짝짓는 소비자는 없다.
- **기기 경로는 F_k를 쓰지 않는다.** Yahoo 등 기기 가격은 이미 분할 **조정** 가격이다. `qgv2-inputs.js`·`qgv-scores.js`·`PriceStore` 경로는 바꾸지 않는다. 기기에서 F_k를 나누면 분할 전 연도가 F배 틀린다.

### 15-2. calc_version 하나로 통합(D-CV7 (b))

- `v2_factors.CALC_VERSION = 'qgv2-calc/2026-10-23.1'`. 이번 라운드의 **유일한** 올림이다.
- 이 번호가 덮는 것: (1) V-PRICE-BASIS(`sec-qgv2.json` 행 규칙) (2) U7 중앙 V 게시 규칙 `qgv-official/1` 전체 — §4 스키마(`v_calc_version` 열 제외), §5 재계산·의존, §6 실패·마지막 정상본, §7 일관성 검사, D-CV2·D-CV5·D-CV10·D-CV11.
- `qgv-official.json`의 `calc_version`은 입력 `sec-qgv2.json`의 값을 그대로 싣는다. U7 규칙이 나중에 바뀌면 그때 `calc_version`을 올린다(새 원장 구간).
- 전환: 첫 샤드 게시 뒤 최대 7일(샤드 7개) 옛 버전 행은 순위 밖이다(`CALC_VERSION_MISMATCH`, 기존 규칙). 504 전체 샤드 수동 실행(`all_shards=true`) 한 번이면 하루로 줄어든다.
- 옛 `sec-qgv2.js`는 새 행(`share_basis_factor`)을 파일째 거부한다. `sec-qgv2.json`과 `sec-qgv2.js`는 같은 배포로 나가야 한다(`test_old_screens_block_new_files_as_a_whole_and_show_no_value`).

### 15-3. 전진 검증 원장 구간 분할(설계만, 코드·워크플로 변경 없음)

- 지금 규칙으로 충분하다. 원장 기록의 `segment`는 입력 파일의 `calc_version`이다(`forward_ledger.py:190-232`). 값이 바뀐 날부터 새 구간이다(`evaluation_segments` :562-577, JS `forward-validation.js:115-122`). 구간은 잇지 않는다.
- 그래서 `calc_version`을 **한 번** 올리면 구간도 **한 번** 나뉜다. 원장 코드를 바꿀 필요가 없다. 기존 기록은 고치지 않는다(추가 전용).
- 전환 중 기록: 파일에 옛 버전 행이 남아 있으면 `CALC_VERSION_MIXED`, Q·G 454 미만이면 `Q_BELOW_454`·`G_BELOW_454`로 `PREPARATORY`다. 새 구간 안에 남지만 1차 평가에서 빠진다. 전 샤드 재수집 뒤 `PRIMARY`가 된다.
- 시점(Main 결정): (a) 병합 직후 전체 샤드 수동 실행 → 다음 날 원장부터 새 구간 PRIMARY 가능 (b) 7일 자연 순환. 권장 (a). U7 게시 코드가 이 버전과 같은 배포 창에 들어가면 구간이 두 번 나뉘지 않는다.
- 피할 것: 이 PR을 되돌리면 버전이 `2026-10-17.1`로 돌아가 구간이 또 나뉜다(세 번째 구간). 되돌림 대신 앞으로 고친다.
- 시험 계획(코드 변경 없이 기존 시험·벡터로 확인, 시점 확정 뒤 Main이 실행):
  1. 합성 원장: day N `2026-10-17.1` PRIMARY → day N+1 혼합 파일 → 새 구간 `qgv2-calc/2026-10-23.1`, `PREPARATORY`·`CALC_VERSION_MIXED`. 이전 기록 바이트 동일.
  2. 전 샤드 재수집 뒤 같은 구간에서 `PRIMARY`. `evaluation_segments` 결과 구간 2개.
  3. JS `segments`와 Python이 같은 결과(`forward_validation_reference_v1.json`에 새 버전 문자열 벡터 추가).
  4. 추가 전용: 병합 전후 기존 원장 기록 해시 동일(가드의 기존 비교).
  5. U7 첫 게시(`qgv-official/1`)는 `calc_version`을 바꾸지 않으므로 구간이 더 나뉘지 않음.
  - 기존 근거 시험: `test_a_calc_version_change_starts_a_separate_segment_and_preparatory_rows_stay_out`(`tests/test_forward_validation_v2.py:284`).
