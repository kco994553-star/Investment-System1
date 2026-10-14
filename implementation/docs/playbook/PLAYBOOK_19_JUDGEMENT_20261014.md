# 플레이북 19종목 판정표 — 2026-10-14

**레포에 기록된 값만 넣은 오프라인 실행. 가격·보유 내역 없음. 플레이북 v0 · UNCALIBRATED.**

## 0. 계산 방법

- 엔진: `qgv/playbook.py`의 `evaluate`(모드 `CORE_V0`)와 `classify_types_v0`를 그대로 호출했습니다. 설정은 `qgv/playbook_v1.json`입니다.
- JS 미러 `web_assets/playbook-engine.js`에 같은 입력 57건(19종목 × 3)을 넣었습니다. Python 결과와 모두 같았습니다.
- 입력 출처는 `docs/qgv_scoring_standard/QGV_V2_QUALITY_20261014.md` 하나입니다.
  - Q·G: 1절 상위 10·이상 사례 표, 3절 TARGET 초안 표.
  - 우량(#19) 입력: 2절 표(영업이익률 σ, 3년 평균 ROIC, 순부채/EBITDA).
  - 업종: `playbook_v1.json` `assignments`(§7-2).
- 원 SEC 사본은 이 환경에 없습니다. `data/raw/blobs`가 비어 있습니다. 그래서 v2를 다시 계산하지 않았습니다.
- 공개 `sec-qgv2.json`·`macro-screen.json`은 레포에 커밋되지 않습니다. 작업 경로에 있던 사이트 사본은 테스트용 합성 입력으로 만든 것이라 쓰지 않았습니다.
- 앱의 입력 조립(`playbook-screen.js` `factsFor`)을 따랐습니다. 앱이 넣지 않는 키는 넣지 않았습니다.
- 모르는 값은 `null`(NA)입니다. 0으로 채우지 않았습니다.

두 상황을 계산했습니다.

| 상황 | 내용 |
|---|---|
| A. 현재 | 기기 자료가 없는 앱 기본값입니다. `held=false`. 기기 시세가 없어서 `price_missing=true`(앱 v2 규칙). |
| B. 보유 가정 | `held=true`, `price_missing=false`. 실제 보유 내역은 쓰지 않았습니다. 가격 값도 넣지 않았습니다. 다른 입력은 A와 같습니다. |

공통 입력: `basis='v2'`, `quarterly_check_due=true`(앱 고정값), `macro_state=null`, `macro_available_count=0`, `target_pct=null`.
`target_pct`는 TARGET v1 전에는 판정에 쓰이지 않습니다(T2·U2 비활성). 그래서 값을 넣지 않았습니다.

## 1. 판정표

매크로는 19종목 모두 **확인 불가**(`매크로 확인 불가`)입니다. 2절을 보세요.

| 종목 | 업종(§7-2) | 주 유형 | 소속 유형 | 우량 #19 (문서값) | 우량 (앱 현재) | 경기민감 | A 주 코드 | A 보조 | B 주 코드 | B 보조 |
|---|---|---|---|:-:|:-:|:-:|---|---|---|---|
| ASML | semi_equipment | 경기민감 | 경기민감 · 우량 | 통과 | NA | 해당 | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| LRCX | semi_equipment | 경기민감 | 경기민감 · 우량 | 통과 | NA | 해당 | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| KLAC | semi_equipment | 경기민감 | 경기민감 | NA | NA | 해당 | X1 PRICE_MISSING | E3 COVERAGE_PARTIAL | E3 COVERAGE_PARTIAL | — |
| 8035 | semi_equipment | 경기민감 | 경기민감 | NA | NA | 해당 | X1 PRICE_MISSING, SNAPSHOT_MISSING | E3 COVERAGE_PARTIAL | X1 SNAPSHOT_MISSING | E3 COVERAGE_PARTIAL |
| 042700 | semi_equipment | 경기민감 | 경기민감 | NA | NA | 해당 | X1 PRICE_MISSING, SNAPSHOT_MISSING | E3 COVERAGE_PARTIAL | X1 SNAPSHOT_MISSING | E3 COVERAGE_PARTIAL |
| NVDA | semiconductors | 경기민감 | 경기민감 | 불통과 | NA | 해당 | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| AMD | semiconductors | 경기민감 | 경기민감 | 불통과 | NA | 해당 | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| AVGO | semiconductors | 경기민감 | 경기민감 | 불통과 | NA | 해당 | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| QCOM | semiconductors | 경기민감 | 경기민감 | 불통과 | NA | 해당 | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| INTC | semiconductors | 경기민감 | 경기민감 | 불통과 | NA | 해당 | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| MSFT | software_internet | 기본(유형 불명) | — | NA | NA | NA | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| GOOGL | software_internet | 기본(유형 불명) | — | NA | NA | NA | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| AMZN | ecommerce_consumer | 기본(유형 불명) | — | 불통과 | NA | NA | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| RTX | defense | 기본(유형 불명) | — | 불통과 | 불통과 | NA | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| SYK | medical_devices | 기본(유형 불명) | — | 불통과 | 불통과 | NA | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| ETN | power_equipment | 기본(유형 불명) | — | NA | NA | NA | X1 PRICE_MISSING | E3 COVERAGE_PARTIAL | E3 COVERAGE_PARTIAL | — |
| HUBB | power_equipment | 기본(유형 불명) | — | 불통과 | NA | NA | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| GEV | power_equipment | 기본(유형 불명) | — | NA | NA | NA | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |
| ROK | industrial_automation | 기본(유형 불명) | — | NA | NA | NA | X1 PRICE_MISSING | — | H1 QUARTERLY_CHECK | — |

- 유형 v0: 경기방어는 19종목 모두 NA입니다. 성장·가치·배당·주도는 입력이 없어 NA입니다.
- "우량 (앱 현재)"는 앱이 읽는 키만으로 다시 판정한 값입니다. `sec-qgv2.json` `metrics`에 `roic_avg_3y`·`operating_margin_std_5y_pp`가 없습니다(품질 보고 4절 6번). 그래서 순부채/EBITDA만 남습니다.
- A 선택지: X1_WAIT·X1_CAUSE·X1_IDENTITY만 켜집니다. 늘리기·줄이기·팔기·편입은 모두 `BLOCKED`입니다.
- B 선택지: H1은 H1_BROKEN·H1_WEAKENED·H1_MAINTAIN, E3는 E3_MAINTAIN·E3_ALT_SOURCE가 켜집니다.
- 전체 모드(`ALL`)로 돌려도 후보 코드(T1·T3·U1·E2·H2·W2) 신호는 없습니다.

B에서 꺼지는 선택지와 사유:

| 대상 | 사유 | 종목 |
|---|---|---|
| U1·U3 늘리기, W2 편입 | `CORE_UNVERIFIABLE`(업종 V 백분위·기대 점검 NA) | 19종목 |
| U1·U3 늘리기 | `SPECIAL_RULE_UNVERIFIABLE`(v2 가치 함정 관문 NA) | 19종목 |
| W2 편입 | `SPECIAL_RULE_UNVERIFIABLE`(테마 비중 NA) | 19종목 |
| U2 늘리기 | `SPECIAL_RULE_UNVERIFIABLE`(경기민감 고점 이익 규칙 NA) | 반도체·장비 10종목 |
| 늘리기 전체 | `E3_DISABLES_EXPANSION` | KLAC, ETN, 8035, 042700 |
| 모든 매매 | `BLOCKED`(X1) | 8035, 042700 |

적용 기준값(v2): 경기민감 주 유형은 R2 QG 16점, 업종 V 백분위 70, 분할 4회입니다. ASML·LRCX는 우량 소속이 더해져 R2 Q 6점이 추가되고 확대 V 임계가 15로 올라갑니다. 기본 유형은 R2 QG 10점, V 백분위 60, 분할 3회입니다.

## 2. 매크로 — 현재 동작(#239 병합 전)

- #239(매크로 참고 표시만)는 아직 열려 있습니다. 현재 설정에는 `gate_active`가 없습니다. 상태를 알면 게이트가 작동합니다.
  - 경고: 경기민감 확대를 끄고 분할 횟수를 2배로 합니다.
  - 위기: 확대·편입을 끕니다. U3 조건 2~5가 모두 참이면 편입만 예외입니다.
- 이번 실행에서는 상태를 알 수 없습니다. 공개 매크로 파일이 레포에 없습니다. 시장·신용 경고등은 기기 가격이 필요합니다.
- 그래서 `macro_available_count=0`이고 상태는 `null`입니다. 엔진은 확대를 제한하지 않습니다. 분할 배수는 1입니다. U3는 조건 1을 확인할 수 없어 뜨지 않습니다(§4 15번 해석).
- **#239 병합 후(참고 전용)**: #239 헤드(`c2f4d2a`)의 엔진·설정으로 같은 입력을 다시 돌렸습니다. 주·보조 코드, 선택지, 꺼진 사유는 모두 같았습니다. 확인 불가 목록에서 `macro_state`와 U3 항목만 빠지고, `gate: REFERENCE_ONLY`가 붙습니다.

## 3. 사용한 입력 값

| 종목 | Q | G | 영업이익률 σ(%p) | ROIC 3년 평균 | 순부채/EBITDA | coverage | snapshot_missing |
|---|---:|---:|---:|---:|---:|---|---|
| ASML | 80.4 | 68.2 | 1.97 | 81.7% | −0.69 | NA | false |
| LRCX | 73.4 | 67.4 | 2.29 | 64.7% | −0.21 | NA | false |
| KLAC | 38 | 37 | NA | NA | NA | PARTIAL | false |
| 8035 | NA | NA | NA | NA | NA | PARTIAL | true |
| 042700 | NA | NA | NA | NA | NA | PARTIAL | true |
| NVDA | 72.8 | 73.8 | 17.54 | 95.0% | −0.02 | NA | false |
| AMD | NA | NA | 6.99 | 3.3% | NA | NA | NA |
| AVGO | NA | NA | 7.28 | 20.0% | NA | NA | NA |
| QCOM | NA | NA | 4.63 | 26.8% | 0.67 | NA | NA |
| INTC | NA | NA | 14.97 | −2.4% | NA | NA | NA |
| MSFT | 63 | 66 | 1.97 | 32.4% | NA | NA | false |
| GOOGL | NA | NA | 2.35 | 29.5% | NA | NA | NA |
| AMZN | 41 | 70 | 3.34 | 20.6% | −0.12 | NA | false |
| RTX | NA | NA | 1.69 | 5.5% | 2.23 | NA | NA |
| SYK | NA | NA | 1.82 | 11.1% | 1.83 | NA | NA |
| ETN | 38 | 74 | NA | NA | NA | PARTIAL | false |
| HUBB | NA | NA | 3.14 | 19.0% | 1.30 | NA | NA |
| GEV | 25 | 70 | NA | 21.3% | NA | NA | false |
| ROK | NA | NA | NA | 23.5% | 1.36 | NA | NA |

- 경기민감: 반도체·장비 10종목은 `sector_subgroup` 조건으로 "해당"입니다. SIC·매출 변동성이 NA여도 결과가 같습니다.
- coverage: KLAC·ETN은 Q가 3/5 요인이라 앱 규칙상 `PARTIAL`입니다. 8035·042700은 Q·G가 없어 `PARTIAL`입니다. 나머지는 요인 수가 기록되지 않아 NA입니다.

## 4. NOT_AVAILABLE 입력과 사유

19종목 공통:

| 입력 | 막히는 판정 | 사유 |
|---|---|---|
| `v_now`, `v_prev20`, `v_industry_pct`, `expectation_check_passed` | T1·U1·W2, U1·W2 선택지 | V는 기기 가격이 필요합니다. 20세션 V 기록도 없습니다(`V2_FORWARD_V_HISTORY_NOT_AVAILABLE`). |
| `value_trap_gate` | U1·U3 늘리기 | V 모듈 출력이라 가격이 필요합니다. |
| `q_prev`, `g_prev`, `q_prev2`, `g_prev2` | R2 | 직전·2분기 전 Q·G 스냅샷이 없습니다. 소급해서 만들지 않습니다. |
| `excess_20`, `excess_mean_252`, `excess_sd_252`, `market_explained_ratio_60` | R3, U3 | 업종 ETF 대비 수익률은 가격이 필요합니다. |
| `actual_pct` | T2·U2(현재 비활성) | 기기 보유 비중입니다. 이 보고에 넣지 않습니다. |
| `macro_state` | 매크로 제한, U3 | 공개 매크로 파일이 레포에 없습니다. 시장·신용 경고등은 기기 가격이 필요합니다. |
| `q_industry_pct`, `net_debt_to_ebitda`·`interest_coverage`(U3용) | U3 조건 3·4 | 앱 `factsFor`가 U3용으로 넣지 않는 키입니다. |
| `operating_margin_5y_position` | 경기민감 확대 | 공급하는 코드가 레포에 없습니다. |
| `theme_weight_pct` | W2 편입 | TARGET v1 초안이 없습니다. |
| `memberships.growth` | 성장 소속 | 3년 매출 CAGR이 19종목별로 기록되지 않았습니다. |
| `sic`, `revenue_volatility_5y_rank_pct` | 비반도체의 경기민감·경기방어 | 전체 단면 값이 레포에 기록되지 않았습니다. 10-13 부분 보고(3/7 샤드) 값은 섞지 않았습니다. |
| `leaderboard_rank`, `earnings_days_until`, `structural_news`, 13F 전량 매도 | W2, E1, E4 | 오프라인 공개 파일이 없습니다. |

종목별:

| 종목 | NA 입력 | 사유 |
|---|---|---|
| 8035, 042700 | Q, G, #19 3개 | 미국 SEC 자료가 없습니다. DART·EDINET 경로가 v2 계산에 없습니다. |
| KLAC | #19 3개 | FY2014 이후 `OperatingIncomeLoss`를 보고하지 않습니다. |
| ETN | #19 3개 | FY2019 이후 `OperatingIncomeLoss`를 보고하지 않습니다. |
| ROK | 영업이익률 σ | 영업이익 태그가 3년치뿐입니다(5년 필요). |
| GEV | 영업이익률 σ, 순부채/EBITDA | 2024년 분사라 이력이 4년입니다. |
| MSFT, GOOGL, AMD, AVGO, INTC | 순부채/EBITDA | D&A 태그가 없습니다. |
| AMD, AVGO, QCOM, INTC, GOOGL, RTX, SYK, HUBB, ROK | Q, G | 품질 보고에 순위만 있고 점수가 없습니다. |

## 5. 직관과 다른 결과 5건

1. **ASML — 우량 3조건을 통과했는데 주 유형은 경기민감입니다.**
   우량과 경기민감 소속도가 모두 1입니다. §6-3 동률 순서(`type_tie_order`: 경기민감 → 성장 → 우량)가 경기민감을 고릅니다.
   그래서 재확인 14일·분할 4회·업종 V 백분위 70이 적용됩니다. 우량 기준(30일·3회·50)이 아닙니다. LRCX도 같습니다.
2. **NVDA — ROIC 95%인데 우량 불통과입니다.**
   우량은 3조건 `ALL`입니다. 5년 영업이익률 σ 17.54%p가 `operating_margin_std_5y_pp < 3`을 넘습니다.
   이익률이 크게 오른 것도 "변동"으로 셉니다. INTC(σ 14.97%p)와 같은 이유로 떨어집니다.
3. **KLAC — 장비 대형사인데 보유 가정에서 주 코드가 E3(커버리지 부분)입니다.**
   `OperatingIncomeLoss` 미보고로 Q가 3/5 요인입니다. 축 상태가 `PARTIAL`이 되어 `coverage='PARTIAL'` → E3가 뜹니다.
   E3는 늘리기를 끕니다(`E3_DISABLES_EXPANSION`). H1은 다른 코드가 없을 때만 떠서 분기 점검도 빠집니다. ETN도 같습니다.
4. **INTC — ROIC −2.4%인데 보유 가정 결과가 ASML과 같은 H1입니다.**
   R2(분기 하락)는 `q_prev`·`g_prev`가 있어야 판정합니다. 분기 스냅샷이 없어 R2는 "확인 불가"로만 남고 뜨지 않습니다.
   그 결과 H1(`quarterly_check_due`이고 다른 신호 없음)만 뜹니다. 약한 종목과 강한 종목을 지금은 구분하지 못합니다.
5. **앱 화면에서는 ASML·LRCX도 우량 NA이고, RTX·SYK만 "불통과"로 확정됩니다.**
   앱은 `roic_avg_3y`·`operating_margin_std_5y_pp` 키를 읽지만 공개 파일에 없습니다. 남은 조건은 `net_debt_to_ebitda < 1.5`뿐입니다.
   `ALL` 결합에서는 불통과 하나면 확정이고 결측이면 NA입니다. 그래서 RTX(2.23배)·SYK(1.83배)만 판정이 나옵니다. SYK는 구 규칙에서 유일한 통과였습니다.

## 6. 확인 불가 — 완전한 표를 막는 것

- 원 SEC 사본이 이 환경에 없습니다(`data/raw/blobs` 비어 있음). v2를 다시 계산할 수 없어 9종목 Q·G가 NA입니다.
- 공개 `sec-qgv2.json`·`macro-screen.json`·뉴스·13F 파일의 실제 사본이 레포에 없습니다. 앱이 지금 보는 값과 이 표는 다를 수 있습니다(공개 v2는 샤드 일부만 담고 있음).
- 가격이 없어서 V·R3·T1·U1·가치 함정 관문·업종 V 백분위를 판정할 수 없습니다. 기기 가격이 없는 상태에서는 X1이 모든 매매를 막습니다.
- Q·G 분기 스냅샷이 없어서 R2를 판정할 수 없습니다. 첫 실제 준비일 이후에만 쌓입니다.
- 8035·042700의 Q·G 경로(DART·EDINET)가 v2에 연결되지 않았습니다.
- 앱의 우량 판정 키 2개가 공개 파일에 없습니다.
- `operating_margin_5y_position`을 공급하는 코드가 없습니다. 경기민감 종목의 확대는 항상 꺼집니다.
- 비반도체 9종목의 경기민감·경기방어는 SIC·5년 매출 변동성 백분위가 없어 NA입니다.

가격, 가격 파생값, 보유 내역, 비밀값은 넣지 않았습니다. 계산 코드·방법·가중치·TARGET은 바꾸지 않았습니다.
