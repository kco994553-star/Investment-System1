# 기업 유형 비중의 운영 적용 범위 — TARGET 전용 → 같은 자격의 모든 기업 (2026-10-17)

소유자 지시(2026-10-17, TARGET v1 확정 전 처리): 유형(유형별 Q·G·V 비중)이 실제로 어느 기업에 적용되는지 확인하고, **같은 자격의 모든 기업에 같은 승인 규칙**을 적용한다. 규칙이 미정인 유형은 지금처럼 미분류/NA로 둔다.

**결론.** 수정 전에는 유형 소속도가 **기존 TARGET id에만** 연결됐다. Universe 504의 다른 기업은 같은 공개 입력이어도 미분류 34/33/33으로 계산됐다. 이 브랜치는 기기 점수 경로가 모든 행(Universe 코드·TARGET 행)의 공개 `sec-qgv2.json` `metrics`에서 같은 규칙으로 소속도를 얻도록 바꿨다. 공개 파일 형식·calc_version·type_config 버전은 바뀌지 않는다. 실제 점수·상위 30 변화는 가격이 필요하므로 기기에서 확인한다(7절).

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
- **버전:** calc_version은 올리지 않는다. 규칙(QGV_V2_QG_METHOD.md 5절)은 "요인 규칙(1~3절) 또는 공개 `v_inputs_v2` 규칙이 바뀔 때"만 올린다. 이번 변경은 공개 값을 하나도 바꾸지 않는다. 올리면 오히려 바뀐 것 없는 행이 최대 7일 순위 모집단에서 빠진다. type_config도 `type_config/1` 그대로다(램프 경계·비중·혼합 규칙 불변, 적용 대상만 넓힘). 바뀌는 것은 기기 종합 비중이다. 기기 프로필 id(`qgv-v2/<preset>/gate-…`)에 기록되는 V 이력(`virtual-trading-v-scores`)은 V만 저장한다. 성장 소속도는 V를 바꾸지 않으므로(경기민감만 V 기준을 바꿈) 이력 연속성은 유지된다.
- **영향:** 같은 자료 기준으로 비TARGET 87개 기업의 비중이 34/33/33에서 30/50/20으로 바뀐다. 이 기업들의 S05 종합 점수와 TARGET v1 후보 순위(504)가 바뀐다. TARGET 19의 화면(S04/S05/S06, 일일보고서, 가상매매 판단 행)은 바뀌지 않는다. 총점 변화는 축이 모두 있으면 (−4·Q + 17·G − 13·V)/100이다. V는 기기 가격이 필요하므로 부호는 기기에서만 정해진다. 가치 함정 관문으로 V가 빠지면 Q·G만 재정규화된다.

## 6. 구현한 것 / 남긴 것

구현(이 브랜치, 병합 안 함):
- `qgv-v2.js` `PRICEFREE_TYPE_METRICS`·`pricefreeMemberships`, `qgv-scores.js` `universeScores`가 모든 행에 적용하고 `company-types-pricefree.json` 읽기를 제거했다.
- Python 참조 `qgv/qgv_v2.py` `pricefree_memberships`.
- 공유 벡터 `tests/fixtures/type_pricefree_memberships_v1.json`, `tests/test_type_scope.py`(TARGET 파일 경로 `calculate_company_types`와 같은 값인지 확인), `tools/type_scope_node_test.js`(합성 쌍둥이, CI 목록에 추가).
- `pages_artifact_guard.py`의 `qgv-v2.js`·`qgv-scores.js` 해시.

남김(결정 또는 후속):
1. **FINANCIAL 프로필의 성장 적용.** type_config/1 성장 규칙에는 프로필 제한이 없어 그대로 적용했다(16개). FINANCIAL은 V가 정의되지 않아(`FINANCIAL_PROFILE_V_NOT_DEFINED`) 성장 비중은 Q:G 비율만 34:33에서 30:50으로 바꾼다. 제외하려면 새 규칙이므로 소유자 결정이 필요하다.
2. **플레이북 유형 기준(비중 아님).** `playbook-screen.js` `factsFor`는 성장 소속도를 여전히 `company-types-pricefree.json`(TARGET 전용)에서 읽는다. 그래서 보유 중인 비TARGET 종목의 플레이북 유형 임계(R2·V 임계 등)는 성장이 NA다. 같은 원칙이면 같은 함수로 바꾸는 것이 맞다. 다만 비중이 아닌 판정 기준이라 이번 범위에서 뺐다.
3. 실제 총점·상위 30 변화는 기기 확인(7절).

## 7. 기기 확인 절차 (가격 필요, 병합·배포는 소유자 승인 후)

가격이 같아야 비교가 된다. **주말이나 미국 장 마감 후**(Universe 탭 가격이 그대로일 때) 같은 기기에서 연속으로 진행한다.

1. **기준(현재 배포본).** 앱 → 플레이북 → "TARGET v1 작성". 프리셋 **균형**, 가치 함정 관문 **켬**인지 확인하고 "v2 입력 연결"이 뜰 때까지 기다린다. "QGV v2 총점·업종 내 순위로 후보 추림" 표의 상위 30행(종목·QGV v2·업종·업종 내 순위)을 기록한다(스크린숏 가능).
2. 같은 화면에서 기업 상세(S05) 세 곳의 "종합 매력도"를 기록한다: 비TARGET 성장 후보 1곳(예: ANET 또는 META), TARGET 성장 1곳(NVDA), TARGET 미분류 1곳(KLAC).
3. **배포 확인.** 병합·배포 뒤 앱을 완전히 새로 고친다. 브라우저에서 `<Pages 주소>/qgv-v2.js`를 열고 `pricefreeMemberships`가 있는지 확인한다(없으면 이전 파일).
4. **변경 후.** 1~2를 같은 설정으로 반복한다.
5. **판정.**
   - NVDA·KLAC 등 TARGET 19의 총점은 1과 **같아야** 한다.
   - 2절의 비TARGET 87개(그날 원자료 기준) 중 표에 보이는 기업만 총점이 바뀐다. 성장 비중은 G 50 / Q 30 / V 20이고, 변화량은 (−4·Q + 17·G − 13·V)/100이다(관문으로 V가 빠지면 Q·G 비율 30:50).
   - 그 밖의 기업 총점이 바뀌면 결함이다. 종목·전후 값을 기록해 보고한다.
   - 상위 30의 진입·이탈 목록을 TARGET v1 결정 자료에 붙인다. "v0 대비" 비교의 "유형 구성"에 성장이 새로 보이는 것은 정상이다.

## 8. 재현

스크립트는 세션 스크래치에만 있고 레포에 넣지 않았다(`python3 -I`, 원자료 미커밋). `rebuild.py`(504 + TARGET 재계산, 유형 파일 생성), `device_counts.js`·`after_counts.js`(기기 경로 건수, 가격 없음), `synth.js`(합성 쌍둥이), `intersect.py`(교집합).
