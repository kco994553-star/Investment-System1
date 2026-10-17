# 기업 유형 비중의 운영 적용 범위 — TARGET 전용 → 같은 자격의 모든 기업 (2026-10-17)

소유자 지시(2026-10-17, TARGET v1 확정 전 처리): 유형(유형별 Q·G·V 비중)이 실제로 어느 기업에 적용되는지 확인하고, **같은 자격의 모든 기업에 같은 승인 규칙**을 적용한다. 규칙이 미정인 유형은 지금처럼 미분류/NA로 둔다.

**결론.** 수정 전에는 유형 소속도가 **기존 TARGET id에만** 연결됐다. Universe 504의 다른 기업은 같은 공개 입력이어도 미분류 34/33/33으로 계산됐다. 이 브랜치는 기기 점수 경로가 모든 행(Universe 코드·TARGET 행)의 공개 `sec-qgv2.json` `metrics`에서 같은 규칙으로 소속도를 얻도록 바꿨다. 공개 파일 형식·calc_version·type_config 버전은 바뀌지 않는다. 대신 기기 점수 산정 기준에 유형 적용 범위 식별값 `qgv2-type-scope/2026-10-17.1`을 기록한다(5절). 실제 점수·상위 30 변화는 가격이 필요하므로 기기에서 확인한다(7절). **그 비교 전까지 실제 영향은 미검증이다.**

## 0. 소유자 결정 반영 (2026-10-17, 4번 "TYPE-SCOPE #284 승인")

| 결정 | 반영 |
|---|---|
| 기존 승인 성장 규칙을 같은 자격의 모든 행에 적용 | 5절. 기기가 점수를 매기는 모든 행(Universe 504 코드·TARGET 행)이 같은 함수 `QgvV2.pricefreeMemberships`를 쓴다. |
| 미정 유형 규칙·금융업 예외를 새로 만들지 않음 | 새 규칙 없음. FINANCIAL 프로필(10/17 기준 16곳)도 같은 성장 규칙을 받는다. 6절 남김 1번은 이 결정으로 종결. |
| calc_version은 유지하되 기기 점수 산정 기준에 유형 적용 범위 식별값 기록 | `TYPE_SCOPE = qgv2-type-scope/2026-10-17.1`. `QgvScores` 산정 기준(`basis.type_scope`·`profile.type_scope`)과 S05·S06 기준 배지에 기록(5절). |
| TARGET 초안 입력 기준 비교에 포함. 기준 변경 시 초안 재생성, 같은 기업 카드 응답만 이어받기 | 비교 코드는 기준 브랜치와 #248에 없고 #263에만 있다. #284는 식별값을 내보낸다. #263이 넣을 변경과 확인 결과는 9절. |
| 플레이북 성장 정보도 같은 입력·규칙. 다른 플레이북 유형 판정은 유지 | `factsFor`가 점수와 같은 행·같은 규칙(`QgvScores.typeMemberships`)에서 성장을 읽는다. 우량·경기민감·경기방어 v0 판정은 그대로(6절). |
| 실제 순위 변화는 같은 입력·같은 가격·같은 설정으로 비교. 비교 전에는 검증 완료로 보고하지 않음 | 7절 기기 절차. 이 문서의 건수(2절)와 합성 비교(3절)는 가격 없이 센 것이다. |

## 1. 수정 전 코드 경로 (기준 커밋 `46574050`)

| 단계 | 위치 | 내용 |
|---|---|---|
| 공개 유형 파일 생성 | `product/public_engine_screens.py:480` | `types={cid:... for cid in OFFICIAL_V11_TARGETS}`: 행 자체가 TARGET 19개뿐이다. 검증기(`:98`, `:161`)도 `set(companies)==set(OFFICIAL_V11_TARGETS)`를 요구한다. |
| 소속도 계산 | `public_engine_screens.py:516-521` | manifest `sec`(미국 TARGET 17개)마다 `calculate_company_types({revenue_cagr_3y, roic})`. 4개 유형(growth·quality·cyclical·defensive)만 싣고, 넷 다 null이면 행 `state=NOT_AVAILABLE`. |
| 기기 연결 | `web_assets/qgv-scores.js:54` | 표시할 identity마다 `company-types-pricefree.json`의 `companies[company_id]`를 찾고, `state!=='NOT_AVAILABLE'`이면 `memberships[codeFor(c)]`에 넣는다. Universe 코드 identity(`company_id`가 `NASDAQ:...`)는 그 파일에 행이 없어 항상 빠진다. |
| 행 선택 | `qgv-scores.js:31-32` | TARGET identity는 TARGET 행에 자료가 있으면 `TARGET:<id>`, 없으면 티커로 Universe 코드. 소속도는 이렇게 고른 코드에만 붙는다. |
| 점수 입력 | `qgv-scores.js:44` | `companies[code].memberships = memberships[code] ?? null`. |
| 비중 결정 | `web_assets/qgv-v2.js:101` → `:30-40` | `typeAxisWeights`: 소속도 객체가 없으면 미분류 34/33/33 + `TYPE_UNCONFIRMED`(`:32`), 0.3 이상 유형이 없으면 미분류 + `NO_RECOGNIZED_TYPE`(`:37`). |
| 종합 | `qgv-v2.js:112`, `:117` | `compositeWeights(프리셋, 유형, 미분류)`(균형 프리셋이면 유형 비중 그대로) → 쓸 수 있는 축의 가중 평균. |
| TARGET v1 후보 순위 | `web_assets/playbook-screen.js:74`, `:102-105` | identity = Universe 504 코드, 단 TARGET 티커 17개는 `company_id`가 TARGET id → `TARGET:<id>` 행의 총점으로 순위. |

참고: 경기민감 **V 이익 기준**(정상화 이익, `qgv-scores.js:55`)은 플레이북 v0 규칙으로 이미 **모든 행**에 적용된다. 이것은 비중이 아니라 V 계산 기준이며 TARGET 제한이 없다.

## 2. 건수 — 10/17 원자료로 게시본과 같은 계산을 다시 만든 결과

입력: 비공개 raw 릴리스 `sec-universe-raw-2026-10-17-all-shard{0..6}`(1차 실행, 00:04~00:34 UTC 취득)에 현재 코드(`sec_qgv2.build_issuer_records`·`build_target_rows`·`merge`, `public_engine_screens.generate_screen_bundle`)를 그대로 적용했다. 집계는 게시 실행 로그와 같다: calc_version `qgv2-calc/2026-10-17.1`, Q 485 / G 493, 단면 498. TARGET 행은 같은 CIK의 Universe 원자료로 만들었다(게시 TARGET 파이프라인의 취득 시각과는 다를 수 있다). 기기 계산은 실제 JS(`QgvScores.compute`, 플레이북 `prepareScores`와 같은 identity 목록, 가격 없음)로 셌다.

| 질문 | 건수 | 근거 |
|---|---:|---|
| Universe 504 코드 ∩ 기존 TARGET id | **17** | 기기 티커 키로 17개 코드(ASML LRCX KLAC NVDA AMD AVGO QCOM INTC MSFT GOOGL AMZN RTX SYK ETN HUBB GEV ROK). CIK로는 18개 코드(GOOG가 Alphabet CIK를 공유하지만 기기에서 TARGET에 연결되지 않음). tokyo_electron·hanmi는 Universe에 없다. |
| 그중 유형 정보가 기기 점수 경로에 연결된 수 | **17** (TARGET 행 `TARGET:<id>` 17개) | 소속도가 붙은 레코드는 `TARGET:<id>` 17개뿐이고, **Universe 코드 레코드는 504개 모두 0개**다. 17개 TARGET 티커는 후보 순위에서 TARGET 행으로 표시되므로 화면상 17/17이 연결된다. |
| 유효한 소속도(승인 규칙상 null 아님) | **17** | 17개 모두 성장(growth) 값이 있다. 나머지 6개 QGV 유형은 규칙 미정·가격 필요라 모두 null(3절). |
| 실제로 유형 비중이 적용된 수(성장 ≥ 0.3) | **5** | ASML 0.555 · NVDA 1.0 · AMD 0.364 · AVGO 1.0 · MSFT 0.612 → 30/50/20. |
| 미분류 34/33/33으로 계산된 수 | **499 / 504** | TARGET 12개(`NO_RECOGNIZED_TYPE`, 성장 < 0.3: LRCX 0.006, GOOGL 0.251, AMZN 0.173, SYK 0.083, KLAC·QCOM·INTC·RTX·ETN·HUBB·GEV·ROK 0) + 비TARGET 487개(`TYPE_UNCONFIRMED`, 소속도 미연결). TARGET 비미국 2개는 v2 행 자체가 없다. |

같은 규칙을 모든 행에 적용하면(같은 재계산): 자료가 있는 Universe 501개 중 491개가 성장 소속도를 가진다. 0.3 이상은 **92개**(TARGET 5 + **비TARGET 87**, 발행사 87, 그중 FINANCIAL 프로필 16)다. 0~0.3은 45, 0은 354, CAGR 없음 10, 자료 없음 3이다. TARGET 행의 결과(5 유형 / 12 미분류)는 그대로다.

새로 성장 비중(30/50/20)을 받는 비TARGET 87개(10/17 원자료 기준, 가격 미사용): ABNB ACGL AJG AMCR ANET APH APO APP ARES AXON BKNG BLK BRO BSX BX CCL CDNS CI CINF COF COIN CPT CRWD CSGP CVNA DASH DDOG DECK DXCM EG EME EXR FANG FICO FIX FSLR FTNT GE GEN GIS GRMN HOOD HWM IBKR INCY INTU ISRG KKR LITE LLY LVS LYV MA MCK META MPWR MU NCLH NEM NOW O OKE PANW PGR PLD PLTR PODD PWR RCL RDDT ROP SMCI SNDK STX SW TDG TKO TTD UBER VEEV VICI VRT WDAY WDC WELL WYNN XYL. 이 중 FINANCIAL 프로필은 ACGL AJG APO ARES BLK BRO BX CI CINF COF COIN EG HOOD IBKR KKR PGR이다. 다음 수집에서 원자료가 바뀌면 목록도 바뀐다. 17개 모두 TARGET 파일·TARGET 행·Universe 행의 `revenue_cagr_3y`가 같다.

## 3. 가격 없는 합성 비교 (수정 전 코드)

같은 재무 입력·같은 유형 조건의 두 회사(`NASDAQ:NVDA` = TARGET id nvda, `NASDAQ:TWIN` = 비TARGET, 서로 다른 CIK), 동업종 12개 모집단. V와 총점을 만들려고 모든 코드에 고정 합성 가격 100 USD만 썼다(실제 가격 아님).

| 경우 | TARGET nvda | 비TARGET twin | 차이 |
|---|---|---|---|
| CAGR 25% (성장 1.0) | growth · 30/50/20 · 총점 64.35 | `TYPE_UNCONFIRMED` · 34/33/33 · 총점 72.57 | 비중 Q −4 · G +17 · V −13, 총점 −8.22, 순위 뒤바뀜 |
| CAGR 14% (성장 0.4) | 같은 30/50/20 | 34/33/33 | 같음 |
| TARGET 행 없음(Universe 코드로 대체) | 30/50/20 | 34/33/33 | 같음 |
| CAGR 12% (성장 0.2) | `NO_RECOGNIZED_TYPE` 34/33/33 | `TYPE_UNCONFIRMED` 34/33/33 | 비중·총점 같음, 사유만 다름 |
| CAGR 없음 | `TYPE_UNCONFIRMED` | `TYPE_UNCONFIRMED` | 없음 |

Q·G·V 축 점수는 모든 경우 두 회사가 같다(Q 77.9 · G 43.5 · V 96.15). 차이는 비중에서만 생긴다. 이 비교는 `tools/type_scope_node_test.js`에 고정했다. 수정 전 코드에서는 12개 중 9개가 실패하고, 수정 후에는 모두 통과한다.

## 4. 승인된 규칙과 미정 규칙 (QGV 비중에 쓰는 것)

| 유형 | type_config/1 규칙 | 가격 | 이번 적용 |
|---|---|---|---|
| 성장 | 램프 `revenue_cagr_3y` 0.10→0.20, 비중 30/50/20 | 불필요 | **모든 행에 적용** |
| 배당 | `dividend_yield` 1.5%→3% + 5년 연속 지급 관문 | 필요 | null 유지(공개 경로에 가격 없음) |
| 주도 | 업종 시총 순위 ≤ 3 | 필요 | null 유지 |
| 가치 | 미정(DISCOUNT_RAMPS 등) | 필요 | null 유지 |
| 우량 | 미정(마진 변동·부채 임계·결합). ROIC 램프는 구성요소만 | — | null 유지 |
| 경기민감·경기방어 | 미정(SIC 승인·변동성 램프·결합) | — | null 유지 |
| 테마 | EXPOSURE_ONLY, QGV 비중 없음 | — | 해당 없음 |

플레이북 6-2의 v0 판정(우량·가치·경기민감·경기방어)은 "플레이북 기준에만 쓰고 QGV 가중치는 바꾸지 않는다"(PLAYBOOK_V1 6-2). 그래서 비중에는 쓰지 않았다.

## 5. 운영 수정 — 범위·형식·버전

- **범위:** 기기가 점수를 매기는 모든 행(Universe 504 코드 + TARGET 행)에 같은 함수 `QgvV2.pricefreeMemberships(row.metrics)`(Python 참조 `qgv_v2.pricefree_memberships`)를 적용한다. 계산하는 것은 type_config `ramp` 규칙 중 허용된 가격 불필요 지표(`revenue_cagr_3y`)뿐이다. TARGET 여부는 입력이 아니다. calc_version이 다른 행은 지금처럼 순위 모집단에서 빠진다.
- **게시 위치·형식:** 새로 게시하는 것은 없다. `sec-qgv2.json`이 이미 504 코드와 TARGET 행 모두에 `metrics.revenue_cagr_3y`를 싣고 있다(`company-types-pricefree.json`과 같은 규칙·같은 유효숫자 6자리). `company-types-pricefree.json`은 TARGET 전용 표시 파일로 그대로 두고, 기기 비중은 더 이상 이 파일을 읽지 않는다. 형식 변경과 검증기 변경은 없다.
- **버전:** 원지표 calc_version은 올리지 않는다. 규칙(QGV_V2_QG_METHOD.md 5절)은 "요인 규칙(1~3절) 또는 공개 `v_inputs_v2` 규칙이 바뀔 때"만 올린다. 이번 변경은 공개 값을 하나도 바꾸지 않는다. 올리면 오히려 바뀐 것 없는 행이 최대 7일 순위 모집단에서 빠진다. type_config도 `type_config/1` 그대로다(램프 경계·비중·혼합 규칙 불변, 적용 대상만 넓힘). 바뀌는 것은 기기 종합 비중이다.
- **유형 적용 범위 식별값(결정 4번):** `TYPE_SCOPE = 'qgv2-type-scope/2026-10-17.1'`. JS `QgvV2.TYPE_SCOPE`와 Python `qgv_v2.TYPE_SCOPE`가 같은 상수다. 형식은 calc_version(`qgv2-calc/…`)과 같지만 별개의 값이다.
  - 뜻: 소속도를 받는 행(점수를 매기는 모든 행), 입력(그 행의 `sec-qgv2.json` `metrics`), 규칙(type_config/1의 가격 불필요 램프 = `PRICEFREE_TYPE_METRICS`). 셋 중 하나라도 바뀌면 새 식별값을 쓴다. 공유 벡터(`tests/fixtures/type_pricefree_memberships_v1.json`)가 식별값·지표 목록·type_config 버전을 함께 고정한다. 하나만 바꾸면 Python·노드 테스트가 실패한다.
  - 기록 위치: `QgvScores.compute()` 결과의 `basis.type_scope`(점수 산정 기준)와 `profile.type_scope`, `QgvScores.basis()`. 기준 배지(`basisText`: S05 기업 배지, S06 상단 배지)에 "· 유형 범위 qgv2-type-scope/2026-10-17.1"로 보인다. 이전 범위(TARGET id만)에는 식별값이 없다. 배지 유무로 기기가 어느 범위로 계산했는지 알 수 있다.
  - 프로필 id(`qgv-v2/<preset>/gate-…`)는 바꾸지 않는다. V 이력(`virtual-trading-v-scores`)의 키이고 V만 저장한다. 성장 소속도는 V를 바꾸지 않으므로(경기민감만 V 기준을 바꿈) 이력 연속성은 유지된다.
  - TARGET 초안은 이 식별값을 입력 기준에 넣어야 한다(9절).
- **영향:** 같은 자료 기준으로 비TARGET 87개 기업의 비중이 34/33/33에서 30/50/20으로 바뀐다. 이 기업들의 S05 종합 점수와 TARGET v1 후보 순위(504)가 바뀐다. TARGET 19의 점수(S04/S05/S06, 일일보고서, 가상매매 판단 행)는 바뀌지 않는다. 기준 배지에는 유형 범위 식별값이 붙는다. 총점 변화는 축이 모두 있으면 (−4·Q + 17·G − 13·V)/100이다. V는 기기 가격이 필요하므로 부호는 기기에서만 정해진다. 가치 함정 관문으로 V가 빠지면 Q·G만 재정규화된다.

## 6. 구현한 것 / 남긴 것

구현(이 브랜치, 병합 안 함):
- `qgv-v2.js` `PRICEFREE_TYPE_METRICS`·`pricefreeMemberships`, `qgv-scores.js` `universeScores`가 모든 행에 적용하고 `company-types-pricefree.json` 읽기를 제거했다.
- Python 참조 `qgv/qgv_v2.py` `pricefree_memberships`.
- 결정 4번 반영: 식별값 `TYPE_SCOPE`(JS·Python)와 산정 기준 기록(`qgv-scores.js` `basis`·`profile`·`basisText`).
- `QgvScores.typeMemberships({identity, publicScreens})`: 한 기업의 점수가 쓰는 행(`TARGET:<id>` 행에 자료가 있으면 그 행, 없으면 티커의 Universe 코드)에서 같은 규칙으로 소속도를 돌려준다. 점수 계산(`universeScores`)과 같은 내부 함수(`rowMemberships`)를 쓴다. calc_version이 다른 행은 점수가 없으므로 소속도도 null이다.
- 플레이북 `playbook-screen.js` `factsFor`: 성장 소속도를 `company-types-pricefree.json` 대신 `QgvScores.typeMemberships`에서 읽는다. 행이 없으면 성장은 null(NA)이며 0으로 채우지 않는다. 우량·경기민감·경기방어는 기존 v0 판정(`playbookTypeFacts`) 그대로다.
- 공유 벡터 `tests/fixtures/type_pricefree_memberships_v1.json`, `tests/test_type_scope.py`(TARGET 파일 경로 `calculate_company_types`와 같은 값인지 확인), `tools/type_scope_node_test.js`(합성 쌍둥이, CI 목록에 추가).
- `pages_artifact_guard.py`의 `qgv-v2.js`·`qgv-scores.js`·`playbook-screen.js` 해시.
- 테스트 추가(결정 4번): 식별값이 JS·Python·벡터에서 같고 지표 목록·type_config와 묶였는지, 산정 기준·배지에 기록되는지, 프로필 id·calc_version이 그대로인지. 플레이북 성장 = 점수 쪽 소속도(경계 0.10 → 0, 0.20 → 1, NA → null, TARGET 행 우선, calc_version 불일치 행 null, TARGET 파일 무시), 다른 플레이북 유형 판정 불변.

플레이북 성장 연결 — 전후:

| 대상 | 전 | 후 |
|---|---|---|
| TARGET 종목 | `company-types-pricefree.json`의 성장(TARGET 파일 수치) | 점수와 같은 `TARGET:<id>` 행(없으면 Universe 행) 수치, 같은 규칙 |
| 비TARGET 보유·관심 종목 | 성장 NA(파일에 행 없음) | 점수와 같은 Universe 행 수치, 같은 규칙 |
| calc_version이 다른 행 | TARGET이면 파일 값 | null(점수도 없음) |
| 우량·경기민감·경기방어 | 플레이북 v0 판정 | 그대로 |
| 가치·배당·주도 | NA | 그대로 NA |

남김(결정 또는 후속):
1. ~~FINANCIAL 프로필의 성장 적용~~ — 종결. 결정 4번이 "금융업 예외를 새로 만들지 않는다"고 정했다. type_config/1 성장 규칙에는 프로필 제한이 없으므로 그대로 적용한다(10/17 기준 16개). FINANCIAL은 V가 정의되지 않아(`FINANCIAL_PROFILE_V_NOT_DEFINED`) 성장 비중은 Q:G 비율만 34:33에서 30:50으로 바꾼다.
2. ~~플레이북 유형 기준~~ — 반영(위 전후 표).
3. TARGET 초안 입력 기준 비교 — #263에서 반영(9절).
4. 실제 총점·순위 변화 — 기기 비교(7절). 비교 전까지 미검증.
5. `company-types-pricefree.json`을 읽는 다른 화면은 TARGET 전용 표시로 남는다: S05 유형 칩(`company-screen.js`), 포트폴리오 유형 노출(`portfolio-screen.js`), 프로필 초안(`device-profiles.js`), 가상매매 비교(`virtual-trading-compare.js`). 점수 비중과 플레이북 판정에는 쓰이지 않는다. 그래서 비TARGET 기업은 S05 점수에는 성장 비중이 들어가도 유형 칩은 NA로 보일 수 있다. 결정 범위(점수·초안·플레이북) 밖이라 바꾸지 않았다.

## 7. 실제 순위 변화 비교 — 기기 절차 (가격 필요, 병합·배포는 소유자 승인 후)

**실제 영향(총점·순위 변화)은 아직 검증하지 않았다.** 2절 건수와 3절 합성 비교는 가격 없이 센 것이다. 실제 순위는 기기 가격이 있어야 나온다. 이 비교를 마치기 전에는 "실제 영향 검증 완료"로 보고하지 않는다. 레포에서는 가격으로 아무것도 계산하지 않는다.

비교는 같은 입력·같은 가격·같은 설정에서 유형 적용 범위 하나만 바꾼다.

| 조건 | 맞추는 방법 | 확인(전후 모두) |
|---|---|---|
| 같은 입력 | 전후를 일일 수집 실행 사이에 모두 끝낸다(한 실행이 끝난 뒤, 다음 실행 전). | 브라우저로 `<Pages 주소>/sec-qgv2.json`을 열어 맨 앞의 `as_of`·`calc_version`을 적는다. 다르면 무효다(자료 효과가 섞임). |
| 같은 가격 | 주말이나 미국 장 마감 후, 같은 기기·같은 유니버스 시트. 사이에 시트 가격을 새로 고치지 않는다. | S06 상단 "가격 N (이 기기·메모리)"의 N이 같아야 한다. 가격 값은 적지 않는다. |
| 같은 설정 | 프리셋 균형, 가치 함정 관문 켬. | S06 상단 "균형 · 관문 켬". |
| 바꾸는 것: 유형 적용 범위 | 전 = 현재 배포본(TARGET id만, 식별값 없음). 후 = #284 배포본. | S06 상단·S05 기준 배지. 후에는 "유형 범위 qgv2-type-scope/2026-10-17.1"이 보여야 한다. 안 보이면 이전 파일이다(완전히 새로 고침). |

절차:
1. **전(현재 배포본).** 위 조건을 맞추고 확인값을 적는다. 앱 → 플레이북 → "TARGET v1 작성". "v2 입력 연결"이 뜰 때까지 기다린다. "QGV v2 총점·업종 내 순위로 후보 추림" 표(최대 30행: 종목·QGV v2·업종·업종 내 순위)를 기기에 남긴다(스크린숏 가능). 기업 상세(S05) 세 곳의 "종합 매력도"도 남긴다: 비TARGET 성장 후보 1곳(예: ANET 또는 META), TARGET 성장 1곳(NVDA), TARGET 미분류 1곳(KLAC).
2. **병합·배포**(소유자 승인 후). 앱을 완전히 새로 고친다. 기준 배지에 유형 범위 식별값이 보이는지 확인한다.
3. **후.** 1을 같은 조건으로 반복한다. 먼저 `as_of`·`calc_version`·가격 개수·프리셋·관문이 1과 같은지 본다. 하나라도 다르면 비교를 멈추고 "조건 불일치"로 기록한다.
4. **판정.**
   - TARGET 19의 총점은 1과 **같아야** 한다. TARGET 행은 전에도 같은 성장 규칙을 받았다(공개 TARGET 유형 파일과 TARGET 행의 `revenue_cagr_3y`가 같을 때. 10/17 기준 17개 모두 같음).
   - 총점이 바뀌는 기업은 그날 원자료 기준 성장 소속도 0.3 이상인 비TARGET 기업뿐이다(10/17 원자료로 87개, 2절). 비중은 Q 30 · G 50 · V 20이고, 변화량은 (−4·Q + 17·G − 13·V)/100이다(관문으로 V가 빠지면 Q·G 30:50).
   - 그 밖의 기업 총점이 바뀌면 결함이다.
   - 순위는 총점이 바뀐 기업 때문에 다른 기업도 움직일 수 있다. 이것은 결함이 아니다.
5. **기록.**
   - 레포·PR·로그에는 **개수와 조건 확인값만** 적는다: 총점이 바뀐 기업 수, 그중 예상 범위(성장 0.3 이상 비TARGET) 밖의 수(0이어야 함), TARGET 19 중 총점이 바뀐 수(0이어야 함), 순위가 바뀐 기업 수, 상위 30 진입 수·이탈 수, 그리고 `as_of`·`calc_version`·프리셋·관문·유형 범위 식별값.
   - 기업별 순위 이동(종목·전후 순위)과 총점은 가격에서 나온 값이다. 기기나 소유자 개인 기록에만 둔다. TARGET v1 결정 자료로 쓸 때도 레포에 넣지 않는다. 가격 값은 어디에도 적지 않는다.
   - 결함이 있으면 종목·전후 값은 개인 기록에 두고, 레포에는 "결함 n건"과 원인 추정만 적는다.
6. 이 기록이 생긴 뒤에만 "실제 영향 검증 완료"로 보고한다.

## 8. 재현

스크립트는 세션 스크래치에만 있고 레포에 넣지 않았다(`python3 -I`, 원자료 미커밋). `rebuild.py`(504 + TARGET 재계산, 유형 파일 생성), `device_counts.js`·`after_counts.js`(기기 경로 건수, 가격 없음), `synth.js`(합성 쌍둥이), `intersect.py`(교집합).

## 9. TARGET 초안의 입력 기준 비교 (결정 4번 넷째 항목)

- **기준 브랜치(8a055bae)에는 초안 입력 기준 비교가 없다.** 플레이북 "TARGET v1 작성"(`playbook-screen.js` `mountTargetWriter`)은 `target_draft`(행·현금·전환 계획)만 저장한다. 입력 기준과 카드 응답이 없다.
- **#248(`claude/target-v1-builder`)에도 없다.** 비교는 #263(`claude/target-v1-followups`, #248 위)에만 있다: `target-v1-builder.js` `inputBasis`(calc_version·as_of·샤드별 최신 수집 시각) → `basisChanged` → 확정 시 `DRAFT_BASIS_CHANGED` → `regenerateDraft`.
- **기존 동작 확인(#263 머리 0661f999):** `regenerateDraft`는 새 후보 풀에 남은 종목의 카드 응답만 이어받는다. 풀에서 빠진 종목의 응답은 버리고, 새 종목은 새 카드 대기다. #263 노드 테스트 "draft regeneration: answers carry over only for the same symbols"가 이를 검사한다.
- **#284가 내보내는 것:** `QgvV2.TYPE_SCOPE`, `QgvScores` `basis.type_scope`·`profile.type_scope`. 이 브랜치는 #248·#263을 고치지 않는다.
- **#263이 넣을 것:**
  1. `inputBasis(payload,{digest,typeScope})`: 결과에 `type_scope`를 넣는다. 기본값은 기기 코드의 `QgvV2.TYPE_SCOPE`이고 공개 파일에서 읽지 않는다(`qgv-v2.js` 지연 로드, 없으면 null).
  2. `basisChanged`: `type_scope`가 다르면 변경이다. 식별값 없이 만든 예전 초안도 변경으로 본다.
  3. `validateState`: `draft.basis.type_scope`는 없음·null·100자 이하 문자열만 허용한다.
  4. `finalize`: 확정 버전에 `type_scope`를 기록한다(calc_version 옆).
  5. 화면 문구: 재생성 안내에 "유형 적용 범위", 원자료 보기에 "유형 범위".
  6. 테스트: 입력 기준 deepEqual에 `type_scope`를 더한다. 새 테스트 — 같은 파일·같은 calc_version·같은 수집 시각에서 범위만 다르면 `DRAFT_BASIS_CHANGED` 하나만 나온다. 재생성하면 같은 종목 응답(반대 포함)만 이어받고, 풀에서 빠진 종목 응답은 버리며, 새 종목은 카드 대기다. 새 카드 응답 뒤 확정되고 버전에 `type_scope`가 남는다.
- **확인:** 위 변경을 #263 머리(0661f999)에 적용하고 #284의 `qgv-v2.js`를 함께 둔 상태에서 #263 노드 테스트 21/21이 통과했다. 패치는 레포 밖(세션 스크래치)에 있고, #263 담당이 적용한다. #284 병합 전이면 `type_scope`는 양쪽 모두 null이라 비교 결과가 바뀌지 않는다.
