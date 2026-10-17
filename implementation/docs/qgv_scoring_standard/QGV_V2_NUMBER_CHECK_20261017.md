# QGV v2 숫자 재대조 — 수정 후 같은 10종목 (대기열 §6, 2026-10-17)

**결론: 40칸은 오류 없음. 전체 통과는 아직 아님.** 4지표 × 10종목 = 40칸 중 **수치 일치 34칸, 정책상 NA 유지 6칸, 오류 0칸, 미검증 0칸**입니다. 10/14 보고의 차이 12칸은 모두 처리됐습니다. 6칸은 승인된 결정 Q-NODEBT-INT에 따라 NA로 남았고, 나머지 6칸은 이제 10-K 원값과 같습니다. 다만 **FCF 수익률 10칸은 미검증(기기 전용)**이고, **10-K HTML 본문 대조 3종목은 원문을 확보하지 못했습니다**. 또 FCF 수익률의 분모(EV)에서 **오래된 부채값이 쓰이는 결함**을 찾았습니다(4-2절). 그래서 `number_check.result`를 통과로 올릴 근거는 아직 부족합니다(8절).

- 대상: 10/14 보고와 같은 10종목입니다. FIX, EME, INCY, RL, DECK, MA, RSG, MNST, CMG, EXPE.
- 기준 calc_version: `qgv2-calc/2026-10-15.1`입니다. 10종목 행 모두 이 버전입니다.
- 입력: 504종목 일괄 실행 [run 38984332754](https://github.com/kco994553-star/Investment-System1/actions/runs/38984332754)(실행 커밋 `a3dbec94`, 시작 2026-10-17 00:00 UTC / 09:00 KST)이 비공개 raw 레포에 올린 SEC 원자료 사본입니다.
- 이 문서는 **생성 산출물 기준**입니다. 같은 실행의 collect는 성공했지만 **verify가 실패했고 deploy는 건너뛰었습니다**(00:46 UTC / 09:46 KST, `sec_disclosures_browser_test.js` S07 CONTRACT 실패. QGV 계산과 무관한 공시 화면 테스트). 그래서 이 값들은 **아직 게시되지 않았습니다.** 같은 calc_version으로 배포가 성공하면, 게시 파일이 같은 원자료에서 왔는지(취득 시각·sha256) 확인하고 2절 표를 다시 대조해야 합니다(원자료가 같으면 스크립트로 그대로 재현됩니다).
- 10/14 보고([QGV_V2_NUMBER_CHECK_20261014.md](QGV_V2_NUMBER_CHECK_20261014.md))는 역사로 그대로 둡니다. 이 문서는 수정 후 결과입니다.
- 가격, 시가총액, 가격 파생값은 없습니다. 금액은 SEC에 보고된 그대로이고 단위는 USD 백만입니다.

## 1. 방법

1. **원자료.** 비공개 레포 `investment-system1-raw`의 릴리스 7개입니다. 태그는 `sec-universe-raw-2026-10-17-all-shard{0..6}`입니다(UTC 날짜 기준. 10-16 태그는 없음). REST API(`releases/assets/{id}`, `Accept: application/octet-stream`)로 받았습니다. `gh release download`는 GraphQL 차단으로 실패합니다. 각 파일의 sha256은 릴리스 digest, 동봉 `.sha256`, 실행 로그의 `RAW_UPLOADED sha256`과 모두 같습니다. 새 빈 디렉터리에 풀었고, 스크립트는 따로 두었고, `python3 -I`로만 읽었습니다. 원자료와 스크립트는 레포에 넣지 않았습니다.

| 릴리스 태그 | 자산 | sha256 | 내려받은 시각(UTC) |
|---|---|---|---|
| `…-all-shard0` | `sec-universe-raw-2026-10-17-all-shard0.tar.gz` | `3bdc879717ac4fb417e140c2d52b72345a0c509e7d4837ad9593d085e64d56c6` | 2026-10-17 00:13:46 |
| `…-all-shard1` | `…-all-shard1.tar.gz` | `fd86d98288e15f92cd8f1a9abc1f4972981e72fa3aab100d73fe7358391cf823` | 00:13:57 |
| `…-all-shard2` | `…-all-shard2.tar.gz` | `b02f9bc804262ec647ca6cc11fab2dba422d49c77629912ead65e05a439d1b38` | 00:17:59 |
| `…-all-shard3` | `…-all-shard3.tar.gz` | `8f530e01c4861435af47a087401db1e9c610fdbeb3bf98cdbca46b018df6ec16` | 00:22:29 |
| `…-all-shard4` | `…-all-shard4.tar.gz` | `c3090065a1cb1685dc416381604a76c74bb0b9db30f93f52262d8f8aeca8d926` | 00:27:07 |
| `…-all-shard5` | `…-all-shard5.tar.gz` | `4abf877023097805340a5a880ff4fa4608511804fb85e1b1dad881902f924cc9` | 00:30:54 |
| `…-all-shard6` | `…-all-shard6.tar.gz` | `17c3dbc9f2b276c3f8d9870f6a570420f91f6dd6feeedc63bd3c8c1b22eea8bd` | 00:34:21 |

2. **수집 기준.** 각 회사의 취득 시각은 샤드 `manifest.json`의 `acquired_at`입니다. 이것을 production cutoff로 그대로 썼습니다(실행과 같음). 10종목의 취득 시각과 companyfacts sha256은 부록 첫 표에 있습니다.
3. **production 값.** `sec_qgv2.build_row` → `v2_factors.compute`를 그대로 호출했습니다(코드 = `a3dbec94`. 현재 기준 브랜치 `f2be1153`과 `src`·`tests` 차이 없음). 10행 모두 `calc_version = qgv2-calc/2026-10-15.1`, `state = LIVE`, 행 `reason_codes` 없음입니다. 지표가 NA인 칸의 사유는 2·3절에 적었습니다.
4. **손계산(독립 스크립트, 10/14의 방법 B).** `v2_factors`를 import하지 않습니다. companyfacts에서 **form 10-K 사실만** 골랐고, 기간마다 그 기간을 보고한 가장 최근 10-K의 값을 썼습니다. 줄 선택은 10-K 재무제표 표시 그대로입니다. 승인된 정의가 줄을 정하는 곳(Q-SW 소프트웨어 설비투자, Q-RSG 손익계산서 매출, F1 세전이익, F2 D&A, F3 설비투자 줄)은 그 정의를 따랐습니다. 부채가 없는 회사는 따로 **정책 확인**을 했습니다. 같은 10-K에서 0이 아닌 차입 개념, 이자비용, 금융리스·리스이자를 직접 찾아 Q-NODEBT 조건을 판정했습니다.
5. **판정.**
   - **수치 일치**: 상대 차이 < 5%.
   - **정책상 NA 유지**: production NA이고, 승인된 결정이 같은 원자료에서 NA를 요구함. 10-K 기준 값은 참고로만 적고 일치로 세지 않습니다.
   - **오류**: 위 둘이 아닌 차이.
   - **미검증**: 입력이 없어 대조하지 못함.
6. **실행 로그와 대조.** 같은 원자료로 504종목을 production 코드로 다시 계산했습니다(7절). 결과 개수가 실행 로그와 같습니다: `q_scored=485 g_scored=493 qg_both=477 cross_section=498 not_available=3`, `kept_previous_rows=0`, 수집 실패 2(`SEC_CIK_MISMATCH`). 게시 산출물(`github-pages` artifact)은 내려받지 못했습니다. artifact 저장소(`*.blob.core.windows.net`)가 프록시에서 403입니다. 그래서 행 단위 대조는 원자료 재계산으로 대신했습니다.

## 2. 판정표

P = production, H = 10-K 원값 손계산(B). ROIC·CAGR은 %, 순부채/EBITDA는 배, FCF는 FY 기준 USD 백만입니다.

| 종목 (FY0) | ROIC P / H | 판정 | 매출 CAGR 3y P / H | 판정 | 순부채/EBITDA P / H | 판정 | FCF 분자 P / H | 판정 | FCF 수익률 |
|---|---|---|---|---|---|---|---|---|---|
| FIX (2025-12) | 73.31 / 73.31 | 일치 | 30.03 / 30.03 | 일치 | −0.574 / −0.574 | 일치 | 1,031.5 / 1,031.5 | 일치 | 미검증 (기기 전용) |
| EME (2025-12) | NA / (60.90) | **정책상 NA (Q-NODEBT-INT)** | 15.32 / 15.32 | 일치 | NA / (−0.585) | **정책상 NA (Q-NODEBT-INT)** | 1,189.3 / 1,189.3 | 일치 | 미검증 (기기 전용, 분모 결함 4-2) |
| INCY (2025-12) | NA / (61.16) | **정책상 NA (Q-NODEBT-INT)** | 14.84 / 14.84 | 일치 | NA / (−1.926) | **정책상 NA (Q-NODEBT-INT)** | 1,354.6 / 1,354.6 | 일치 | 미검증 (기기 전용, 분모 결함 4-2) |
| RL (2026-03) | 48.31 / 48.31 | 일치 | 7.99 / 7.99 | 일치 | −0.530 / −0.530 | 일치 | 746.1 / 746.1 | 일치 | 미검증 (기기 전용) |
| DECK (2026-03) | NA / (160.35) | **정책상 NA (Q-NODEBT-INT)** | 14.69 / 14.69 | 일치 | NA / (−1.425) | **정책상 NA (Q-NODEBT-INT)** | 1,097.3 / 1,097.3 | 일치 | 미검증 (기기 전용, 분모 결함 4-2) |
| MA (2025-12) | 93.87 / 93.87 | 일치 | 13.82 / 13.82 | 일치 | 0.421 / 0.421 | 일치 | 16,433 / 16,433 | 일치 (Q-SW 반영) | 미검증 (기기 전용) |
| RSG (2025-12) | 10.94 / 10.94 | 일치 | 7.08 / 7.08 | 일치 | 2.665 / 2.665 | 일치 | 2,409 / 2,409 | 일치 | 미검증 (기기 전용) |
| MNST (2025-12) | 33.87 / 33.87 | 일치 | 9.54 / 9.54 | 일치 | −0.824 / −0.824 | 일치 | 1,965.9 / 1,965.9 | 일치 | 미검증 (기기 전용) |
| CMG (2025-12) | 54.92 / 54.92 | 일치 | 11.36 / 11.36 | 일치 | −0.153 / −0.153 | 일치 | 1,447.6 / 1,447.6 | 일치 | 미검증 (기기 전용) |
| EXPE (2025-12) | 53.95 / 53.95 | 일치 | 8.09 / 8.09 | 일치 | 0.271 / 0.271 | 일치 | 3,110 / 3,110 | 일치 | 미검증 (기기 전용) |

괄호 안 H는 10-K 표시대로 부채를 0으로 본 참고값입니다. 승인된 정책은 이 값을 쓰지 않습니다.

- **집계(40칸):** 수치 일치 **34** / 정책상 NA 유지 **6** / 오류 **0** / 미검증 **0**. 일치 34칸의 최대 상대 차이는 2.3×10⁻⁶입니다(6자리 반올림 수준).
- **FCF 수익률 10칸:** 모두 미검증(기기 전용)입니다. 40칸에 넣지 않았습니다. 이 중 3칸은 분모 결함이 있습니다(4-2절).
- **FCF TTM**(기기가 V에 우선 쓰는 값): production 값이 있는 9개는 손계산과 0.0% 차이입니다. RL은 production TTM이 NA입니다. 10-K는 `PaymentsToAcquireMachineryAndEquipment`, 10-Q는 `PaymentsToAcquireProductiveAssets`로 태그해서 F3의 '한 개념' 규칙(METHOD 1절)상 TTM을 만들지 않습니다. 기기는 FY 746.1을 씁니다. 두 개념을 섞은 참고값은 1,043.2입니다.
- **INCY TTM 공백(원자료 쪽):** 10/17 companyfacts에도 2026-07-28 10-Q(`0000879169-26-000056`)가 없습니다. 그래서 TTM이 2026-03-31 기준(1,450.9)에 머뭅니다. 같은 릴리스의 표지 파일에는 그 10-Q의 XBRL instance가 있지만, production은 companyfacts만 읽습니다. SEC 쪽 반영 지연이고 계산 오류는 아닙니다.
- **Q-EBIT:** 10종목 모두 `OperatingIncomeLoss`를 보고합니다. 대체 계산(세전이익 + 이자비용)과 "추정(대체 계산)" 표시는 이 10종목에 해당하지 않습니다(`ebit_estimated_years` 없음).

## 3. 10/14 차이 12칸 — 지금 결과와 원인

같은 10/17 원자료에 수정 전 코드(#247 병합 직전 `d7109309`)를 돌리면 10/14 값이 그대로 나옵니다(FIX −0.6076, MA FCF 17,159, INCY·MNST NA 등). 그래서 아래 변화는 **원자료 변화가 아니라 규칙 변화** 때문입니다.

### 3-1. 수치 차이 ≥ 5% 2칸 → 모두 일치

| 종목·지표 | 10/14 P / H | 지금 P / H | 판정 | 원인(수정·결정) |
|---|---|---|---|---|
| FIX 순부채/EBITDA | −0.6076 / −0.5744 | −0.5744 / −0.5744 | 일치 | **F2(b) D&A 보강**(#247, Q-247·Q-DA). `DepreciationAndAmortization` 62.4가 `Depreciation` 62.379와 같고 무형상각 79.6이 더 커서, D&A = 62.4 + 79.6 = 142.0을 씁니다. EBITDA 1,456.5. |
| RSG 매출 3년 CAGR | 6.74% / 7.08% | 7.08% / 7.08% | 일치 | **Q-RSG 발행사 예외**(#264). RSG(CIK 0001060391)만 `RevenueFromContractWithCustomerExcludingAssessedTax`를 읽습니다. FY0 16,591 / FY−3 13,511. |

### 3-2. production NA·10-K 값 있음 10칸 → 일치 4, 정책상 NA 유지 6

| 종목·지표 | 지금 P | 판정 | 원인(수정·결정) |
|---|---|---|---|
| INCY FCF | 1,354.6 | 일치 | **F3 설비투자 대체 줄**(#247). `PaymentsToAcquireOtherProductiveAssets` 58.9 하나만 보고하므로 설비투자로 씁니다. |
| RL FCF | 746.1 | 일치 | **F3**(#247). FY2026 10-K의 `PaymentsToAcquireMachineryAndEquipment` 408.1. TTM은 위 2절대로 NA 유지. |
| MNST ROIC | 33.87% | 일치 | **Q-NODEBT 조건부 0**(#264). FY0에 0이 아닌 차입 개념 없음, 이자비용 미보고, 금융리스 없음 → FY0 부채 0. FY−1은 `LongTermDebt` 374.0 그대로. |
| MNST 순부채/EBITDA | −0.824 | 일치 | 같은 이유(부채 0, 현금 2,088.1, EBITDA 2,533.8). `total_debt`도 FY0 기준 0입니다(옛 FY−1 값을 쓰지 않음). |
| EME ROIC | NA | 정책상 NA 유지 | **Q-NODEBT-INT(그대로 NA, 중요성 기준 없음).** 차입 개념은 없지만 `InterestExpense` 12.0이 금융리스 이자 0.3으로 설명되지 않습니다. |
| EME 순부채/EBITDA | NA | 정책상 NA 유지 | 같은 이유. D&A 공백은 **F2(a)**로 풀렸습니다(67.4 + 119.1 = 186.4, EBITDA 1,899.8). 남은 원인은 부채뿐입니다. |
| INCY ROIC | NA | 정책상 NA 유지 | **Q-NODEBT-INT.** `InterestExpenseNonoperating` 2.4 > `FinanceLeaseInterestExpense` 1.3. |
| INCY 순부채/EBITDA | NA | 정책상 NA 유지 | 같은 이유. |
| DECK ROIC | NA | 정책상 NA 유지 | **Q-NODEBT-INT.** `InterestExpenseNonoperating` 2.5, 금융리스 없음. 세전이익은 **F1**(국내 1,084.4 + 해외 241.9)로 풀려 세율이 21% → 22.79%가 됐습니다. |
| DECK 순부채/EBITDA | NA | 정책상 NA 유지 | 같은 이유. |

- 정책상 NA 6칸의 손계산 정책 확인은 부록 각 회사의 "정책 확인(Q-NODEBT)" 줄에 있습니다. 세 회사 모두 FY0와 FY−1 둘 다 NA 조건입니다.
- **결과적으로 EME·INCY·DECK는 재무 안전 지표(순부채/EBITDA)가 NA입니다.** 10/15 결정("재무 안전 지표가 NA인 회사는 후보에서 뺀다, 핵심·일반 모두")에 따라 TARGET 후보에서 빠집니다. Q·G 점수는 남은 요인으로 계산됩니다.

### 3-3. 그 밖의 변화(10/14에서 일치였던 칸)

- **MA FCF 17,159 → 16,433(−4.2%).** **Q-SW**(#264)로 `PaymentsToAcquireSoftware` 726이 설비투자에 들어갔습니다(489 + 726 = 1,215). 손계산도 같은 정의로 16,433이고, 10-K 현금흐름표의 두 줄 그대로입니다. TTM 15,975.
- **Q-SPLIT 영향 없음.** 분할이 있었던 CMG(2024 50:1)·DECK(2024 6:1)·MNST(2023 2:1)의 `dilution_3y`, `eps_cagr_3y`, `fcf_per_share_cagr_3y`는 10/14와 같습니다. 이미 재작성된 값을 다시 조정하지 않았습니다(6절 테스트와 같은 결과).
- **주당 지표 새 값:** INCY·RL의 `fcf_per_share_cagr_3y`가 FCF가 풀리면서 새로 생겼습니다(19.2%, 62.2%). 이 문서의 대조 범위 밖입니다.

## 4. FCF 수익률 — 미검증(기기 전용)

이 환경에는 가격이 없습니다. 그래서 FCF 수익률 10칸은 모두 **미검증(기기 전용)**입니다. 2절의 FCF 일치는 분자만 확인한 것입니다. 수익률 검증으로 세지 않습니다.

### 4-1. 기기에서 맞출 정의와 절차

기기에서 대조할 때 맞출 정의는 코드 그대로입니다(`qgv2-inputs.js` `vInputs`, `qgv-v2.js` `metrics`).

| 항목 | 시스템 정의 |
|---|---|
| 분자 FCF | `v_inputs_v2.fcf.ttm_value`가 있으면 TTM, 없으면 `fy_value`(FY). 기간 표시는 `TTM <ttm_end>` 또는 `FY <fy_end>`. TTM = FY0 + 당기 10-Q YTD − 전년 같은 YTD(같은 개념). |
| 분모 EV | 가격 × `diluted_shares.value` + `total_debt.value` − `cash_and_equivalents.value`. EV ≤ 0이면 NA(`EV_NON_POSITIVE`). |
| 주식수 | `diluted_shares` = 가장 최근 기간의 가중평균 희석주식수(`WeightedAverageNumberOfDilutedSharesOutstanding`). 기말 발행주식수가 아닙니다. 기준일은 `diluted_shares.period_end`. |
| 부채·현금 | 각자 가장 최근 날짜의 값(`period_end`가 서로 다를 수 있음). 부채나 현금이 NA면 수익률 NA(`DEBT_CASH_NOT_AVAILABLE`). |
| 통화 | `v_inputs_v2.currency`(10개 모두 USD)와 시세 통화가 같아야 합니다. 다르면 NA(`CURRENCY_BASIS_UNCONFIRMED`). 환산하지 않습니다. |
| 가격 | 기기 시세 시트의 `quote.price`. 기준 시각은 `quote.as_of`. STALE 표시가 있으면 기록합니다. |

**기기 절차(최소).**
1. 같은 calc_version(`qgv2-calc/2026-10-15.1`)의 게시 `sec-qgv2.json`을 연 기기에서 10종목의 시세를 한 시각에 받습니다. `quote.as_of`와 통화를 적습니다.
2. 화면의 `fcf_yield`(회사 화면 V 상세)를 적습니다.
3. 같은 가격으로 위 표의 EV를 손으로 계산하고, 부록의 FCF(TTM 우선)를 나눕니다. 주식수·부채·현금·FCF의 기준일을 함께 적습니다.
4. 상대 차이 < 5%면 일치입니다. 가격 값은 레포에 넣지 않고 비공개 기록에만 둡니다.

- EME·INCY·DECK는 정책상 부채가 NA이므로 수익률도 NA(`DEBT_CASH_NOT_AVAILABLE`)가 맞습니다. 지금은 4-2의 결함 때문에 옛 부채값으로 계산됩니다. 그래서 기기 대조는 4-2를 고친 calc_version에서 하는 것이 맞습니다. 지금 버전에서 하면 이 3칸은 '오류'로 기록됩니다.

### 4-2. 분모 결함: 오래된 부채값이 `total_debt`로 남음 (오류, 수정 필요)

FCF 수익률은 미검증이지만, 분모 입력을 읽다가 결함을 찾았습니다.

- `v_inputs_v2.total_debt`는 "부채 줄이 있는 가장 최근 날짜"의 값입니다. 날짜가 FY0보다 오래돼도 버리지 않습니다. 무차입 규칙(NODEBT)이 FY0에서 0을 주면 그 값으로 바꾸지만, **NODEBT가 NA(Q-NODEBT-INT)이면 옛 값이 그대로 남습니다.** 기기는 이 값을 EV에 씁니다(`qgv-v2.js` `metrics`). 부채가 NA면 수익률도 NA가 되어야 하는데, 지금은 옛 값으로 계산됩니다.
- 10종목 중 3개가 해당합니다.

| 종목 | FY0 | `total_debt` 날짜 | 값 (USD 백만) | 비고 |
|---|---|---|---:|---|
| INCY | 2025-12-31 | 2018-12-31 | 19,094.0 | FY2018 10-K(`0001558370-19-000682`)의 `LongTermDebt`. 같은 회사의 앞뒤 해(2017년 26.8)와 비교하면 단위 오기로 보입니다. EV가 약 191억 달러 부풀려집니다. |
| EME | 2025-12-31 | 2023-12-31 | 5.3 | 2년 전 값. |
| DECK | 2026-03-31 | 2021-03-31 | 0.0 | 5년 전 값. 정책상 부채는 NA입니다. |

- 504종목 GENERAL 중 **13곳**이 같은 상태입니다: DXCM, INCY, PANW, SMCI, VRSN, VRTX, DE, DECK, DLR, EME, EXR, F, ORCL. 금융 프로필 10곳(IBKR, NTRS, AIZ, AMP, EG, GS, KKR, PGR, RJF, STT)도 옛 값이 있지만, 금융 프로필은 V를 정의하지 않아 쓰이지 않습니다. 10/14 기준선에도 같은 결함이 있었습니다(32곳). 이번 수정으로 생긴 문제가 아닙니다.
- Q·G 점수와 40칸에는 영향이 없습니다. `net_debt_to_ebitda`·ROIC는 FY0 부채만 쓰기 때문입니다.
- **필요한 조치(이 PR에서는 코드 변경 없음):** `total_debt`의 날짜가 FY0보다 이르면 NA로 두는 최소 수정입니다. 게시 값(`v_inputs_v2`)이 바뀌므로 대기열 §6에 따라 새 calc_version을 붙이고 504종목을 같은 버전으로 다시 계산해야 합니다. 수정 전에는 해당 13곳의 기기 V(FCF 수익률·이익 수익률)를 믿을 수 없습니다.

## 5. 10-K HTML 본문 대조 — 미확보

- 비공개 릴리스 7개에는 회사마다 `companyfacts.json`, `submissions.json`, 그리고 **최신 정기보고서의 XBRL instance**(`cover-<접수번호>.xml`)만 있습니다. 10종목 모두 최신 보고서가 10-Q라서 **10-K 본문(HTML)은 없습니다.**
- sec.gov는 이 컨테이너에서 막혀 있습니다(프록시 `CONNECT` 403). 한 번만 확인하고 다시 시도하지 않았습니다.
- 대조하려던 3종목은 태그·무차입·대체 계산 문제가 있었던 사례입니다(10/15 결정). 같은 접수번호의 주 문서는 아래와 같습니다(`submissions.json`의 `primaryDocument`).

| 종목 | 쟁점 | 10-K 접수번호 | 주 문서 |
|---|---|---|---|
| DECK | F1 세전이익, Q-NODEBT-INT | `0001628280-26-037664` | `https://www.sec.gov/Archives/edgar/data/910521/000162828026037664/deck-20260331.htm` |
| INCY | F3 설비투자, Q-NODEBT-INT, 4-2 부채 | `0000879169-26-000010` | `https://www.sec.gov/Archives/edgar/data/879169/000087916926000010/incy-20251231.htm` |
| RSG | Q-RSG 매출 | `0001060391-26-000094` | `https://www.sec.gov/Archives/edgar/data/1060391/000106039126000094/rsg-20251231.htm` |

- **최소 사용자 조치:** 위 3개 HTML을 기기에서 내려받아 비공개 raw 레포에 릴리스 자산으로 올리면 됩니다(예: 태그 `sec-10k-html-20261017`). 공개 레포에는 올리지 않습니다. 그 뒤 이 컨테이너에서 iXBRL 표시값(× scale, 부호)을 같은 접수번호·개념·기간의 companyfacts와 비교하고, 위 손계산 입력을 본문 숫자와 직접 맞춥니다(10/14 `doccheck` 방식).
- **보조 확인(10-K HTML 대조가 아님):** 같은 릴리스의 10-Q XBRL instance를 같은 접수번호·개념·기간의 companyfacts와 비교했습니다. 9개 회사 **392건 중 384건 일치**입니다. RSG 8건은 같은 사실을 백만 단위(`decimals=-6`)와 천 단위(`decimals=-3`)로 두 번 보고한 것이고, companyfacts는 천 단위 값입니다(순이익·희석주식수, 4지표 입력 아님). INCY는 그 10-Q가 companyfacts에 아직 없어 비교 대상이 없습니다(2절). 이 확인은 production이 FY0 재무상태표 값을 10-Q 비교 열에서 읽는 경우(부록 production 접수번호 표)의 원천 일치를 보여 줍니다.

## 6. Q-NODEBT·Q-SPLIT 테스트

`v2_factors.py`의 마지막 변경(`6a380e69`)은 실행 커밋 `a3dbec94`의 조상이고, `a3dbec94`와 현재 기준 브랜치(`f2be1153`) 사이에 `src`·`tests` 변경이 없습니다. 그래도 `f2be1153`에서 다시 돌렸습니다: `PYTHONPATH=src python3 -m pytest tests/test_sec_qgv2.py -k "…"` → **12 passed**.

- Q-NODEBT(다른 부채 태그를 무차입으로 보지 않음): `test_nodebt_issuers_reporting_debt_under_other_tags_are_never_zero_debt`, `test_debt_is_zero_only_without_any_debt_concept_and_without_interest_expense`
- Q-SPLIT(이미 조정된 값을 다시 조정하지 않음): `test_split_adjustment_never_adjusts_already_restated_values_twice`, `test_per_share_histories_are_split_adjusted_only_when_sec_facts_establish_the_ratio`, `test_split_after_fy0_blocks_per_share_history_until_the_basis_is_established`
- 같이 확인: `test_da_from_depreciation_plus_intangible_amortization_only_when_no_double_count`, `test_capex_includes_capitalized_software_without_double_count`, `test_reit_capital_improvements_are_never_the_capex_fallback`, `test_rsg_issuer_exception_uses_income_statement_revenue_only_for_the_listed_cik`, `test_ebit_substitute_is_pretax_plus_interest_and_is_flagged_as_an_estimate`, `test_calc_version_rows_of_another_version_never_share_a_percentile`, `test_normal_na_rows_keep_an_explicit_source_reason_and_are_never_calc_version_mismatch`
- 실제 자료 근거: 2절 정책 확인에서 RL·MA·RSG·EXPE·FIX는 차입 개념이 있어 무차입 규칙을 타지 않았습니다. MNST·CMG만 부채 0입니다(CMG는 `LongTermDebt` 0을 직접 보고). 분할 3사(CMG·DECK·MNST)의 주당 지표는 그대로입니다(3-3절).

## 7. 전후 변화 (가격 미사용 Q·G만)

**QGV 총점 순위는 기기 가격이 필요해서 여기서 계산하지 않았습니다(미검증, 기기 전용).** 아래는 Q·G 합성값 QG = (34·Q + 33·G) / 67(10/14 품질 보고 3절과 같은 방식, CIK당 1개)입니다.

비교 세 가지:
- **P0** = 10/14 기준선(품질 보고가 쓴 혼합 사본, 수정 전 코드). 수정 전 코드 `d7109309`로 다시 계산해 504행이 모두 같음을 확인했습니다.
- **P1** = 수정 전 코드 + 10/17 원자료. P0 → P1 차이는 **회사 원자료 변화**입니다.
- **P2** = 현재 코드(`qgv2-calc/2026-10-15.1`) + 10/17 원자료 = 이번 실행의 생성 산출물과 같은 계산. P1 → P2 차이는 **계산 규칙 변화**입니다.

| | 순위 모집단 | Q 산출 | G 산출 | Q·G 둘 다 |
|---|---:|---:|---:|---:|
| P0 (10/14) | 496 | 470 | 488 | 462 |
| P1 | 498 | 471 | 488 | 462 |
| P2 (10/17) | 498 | 483 | 490 | 475 |

(발행사 단위. 순위 모집단 = `cross_section_size`.)

(코드 단위로는 P2가 Q 485 / G 493 / 둘 다 477, 분모 504입니다. 실행 로그와 같습니다.)

**점수가 바뀐 종목 수.** 두 시점에 모두 있는 495개 발행사는 소수점 아래까지 보면 모두 바뀌었습니다(모집단 백분위 재계산). **Q나 G가 1점 이상 바뀌었거나 NA 여부가 바뀐 곳은 175개**입니다.

| 원인 | 1점 이상 변화 | 판정 방법 |
|---|---:|---|
| 계산 규칙 변화 | 102 | 자기 원지표가 P1 → P2에서 바뀜 |
| 회사 원자료 변화 | 5 | 자기 원지표가 P0 → P1에서 바뀜(새 10-K·10-Q 반영: STZ, MKC, NKE, DRI, DPZ) |
| 원자료 + 규칙 | 2 | 둘 다(CPRT, ACN) |
| 비교 모집단 변화 | 66 | 자기 원지표는 그대로, 다른 회사 변화로 백분위만 이동 |

- NA 여부가 바뀐 13곳은 모두 규칙 변화입니다(XEL, DE, O, VTR, DOC, OXY, HCA, MAA, DTE, SRE, DVN, PSA, FOXA).
- 규칙 변화로 원지표가 바뀐 142개 발행사의 내용(겹침 있음): 순부채/EBITDA NA → 값 82, ROIC NA → 값 55, EBIT 대체 계산 사용 53, FCF 변화(SW·F3·MAA) 27, 주당 지표(SPLIT) 10, 매출 CAGR 변화 3.
- 모집단 구성 변화: 3곳 빠짐(CBOE, XOM, HONA. 이번 실행에서 수집 실패 2 `SEC_CIK_MISMATCH` + CIK 미해결 1로 NA), 3곳 들어옴(FDXF, FLEX, Q. 10/14에는 CIK 미해결). 순위 모집단은 496 → 498 발행사입니다(10/14에는 일부 행이 STALE·NA).

**상위 30 진입·이탈 (P0 → P2).**

| 구분 | 종목 | 순위 P0 → P1 → P2 | Q / G (P0 → P2) | 원인 |
|---|---|---|---|---|
| 진입 | RDDT | 51 → 50 → 4 | 53.5 → 74.5 / 81.8 → 81.8 | 규칙(Q-NODEBT: ROIC·순부채/EBITDA 새로 산출) |
| 진입 | ANET | 55 → 53 → 8 | 52.2 → 75.3 / 82.3 → 79.7 | 규칙(Q-NODEBT: ROIC·해자·증분 ROIC 새로 산출) |
| 진입 | FFIV | 40 → 41 → 13 | 69.9 → 79.2 / 67.4 → 73.0 | 규칙(Q-NODEBT) |
| 진입 | MPWR | 50 → 49 → 21 | 58.7 → 74.4 / 76.7 → 71.9 | 규칙(Q-NODEBT) |
| 이탈 | CMG | 27 → 27 → 39 | 75.6 → 72.0 / 68.0 → 67.9 | 모집단(자기 원지표 변화 없음) |
| 이탈 | EXPE | 28 → 28 → 33 | 80.8 → 80.4 / 61.6 → 61.5 | 모집단 |
| 이탈 | CTAS | 29 → 29 → 34 | 71.5 → 71.8 / 70.3 → 70.2 | 모집단 |
| 이탈 | LRCX | 30 → 30 → 35 | 73.4 → 73.9 / 67.4 → 67.2 | 모집단 |

- 원자료 변화만으로는(P0 → P1) 상위 30 구성이 바뀌지 않았습니다. 순서만 8곳이 한 칸씩 바뀌었습니다.
- 대조 10종목의 QG 순위 P0 → P2: FIX 1 → 1, EME 2 → 3, INCY 3 → 12, RL 4 → 9, DECK 5 → 5, MA 9 → 11, MNST 12 → 2, RSG 15 → 28, CMG 27 → 39, EXPE 28 → 33.
- 이 표는 Q·G 순위 변화일 뿐입니다. TARGET 후보 30은 재무 안전 NA 제외(EME·INCY·DECK 등), 가격이 필요한 V, 업종 한도를 거쳐야 정해집니다.

## 8. `number_check.result`를 통과로 둘 수 있는가 — 근거만 (결정하지 않음)

오너 규칙은 "오류가 없고, 남은 것이 정책상 NA나 기기 전용뿐일 때만 통과", "미검증이 있으면 전체 통과로 표시하지 않음"입니다.

- **충족:** 40칸은 오류 0, 미검증 0입니다. NA 6칸은 모두 승인된 Q-NODEBT-INT에 따른 정책상 NA입니다.
- **미충족 1 — FCF 수익률 10칸 미검증(기기 전용).** 기기 대조(4절 절차)가 끝나야 합니다.
- **미충족 2 — 10-K HTML 3종목 미확보.** 이것은 기기 전용 항목이 아니라 원문 확보 문제입니다(5절, 최소 사용자 조치 있음).
- **미충족 3 — 분모 결함(4-2절).** FCF 수익률의 시스템 분모에 오류가 있습니다. 수정에는 새 calc_version과 504 재계산이 필요하고, 그러면 같은 calc_version으로 이 재대조를 다시 해야 합니다(영향 범위: `v_inputs_v2`만. Q·G 40칸은 다시 계산해도 같아야 합니다).
- **미충족 4 — 게시본 아님.** 이번 실행은 verify 실패로 배포되지 않았습니다. 오너 결정은 "게시된 calc_version과 입력 파일 기준"입니다. 같은 calc_version의 게시본이 생긴 뒤 그 입력과 연결해야 합니다.
- **따라서 지금 `number_check.result`를 passed로 둘 근거는 없습니다.** 권장 순서: 4-2 수정 → 새 calc_version 504 일괄 실행 → 40칸 재확인(자동 재현) → 3종목 HTML 대조 → 기기 FCF 수익률 대조.

## 9. 재현

스크립트는 세션 스크래치(`nc2_scripts/`)에만 있고 레포에는 넣지 않았습니다. 모두 `python3 -I`로 실행했습니다.
- `dl.sh`: 릴리스 자산을 REST로 받고 시각·sha256을 기록합니다.
- `extract.py`: 샤드 tar를 새 빈 디렉터리에 풉니다(실행 파일 없음, 이름 검사).
- `prod10.py`: production `build_row`로 10종목을 계산하고, production이 쓴 줄과 접수번호를 남깁니다.
- `hand2.py`: 독립 손계산 B, 정책 확인(Q-NODEBT), TTM.
- `old10.py`: 같은 원자료에 수정 전 코드를 돌립니다.
- `covercheck.py`: 10-Q instance와 companyfacts 비교(보조).
- `all504.py`, `compare.py`, `stale.py`: 504 재계산, 전후 비교, 오래된 `total_debt` 검사.
- `gen2.py`, `prodacc.py`: 부록 표.

## 부록. 회사별 입력과 접수번호

### A-1. production 행 식별자

| 종목 | 릴리스 태그 | 취득 시각(UTC) | companyfacts sha256 (앞 16자) | calc_version | FY0 |
|---|---|---|---|---|---|
| FIX | `sec-universe-raw-2026-10-17-all-shard1` | 2026-10-17T00:11:19 | `7c39703c55f5115c` | `qgv2-calc/2026-10-15.1` | 2025-12-31 |
| EME | `sec-universe-raw-2026-10-17-all-shard6` | 2026-10-17T00:31:46 | `84c31781c9a72f54` | `qgv2-calc/2026-10-15.1` | 2025-12-31 |
| INCY | `sec-universe-raw-2026-10-17-all-shard2` | 2026-10-17T00:15:18 | `9bbd2db86b80214c` | `qgv2-calc/2026-10-15.1` | 2025-12-31 |
| RL | `sec-universe-raw-2026-10-17-all-shard5` | 2026-10-17T00:28:46 | `9941afcadb20bb4e` | `qgv2-calc/2026-10-15.1` | 2026-03-28 |
| DECK | `sec-universe-raw-2026-10-17-all-shard0` | 2026-10-17T00:05:55 | `4b5b5238bd4a48c7` | `qgv2-calc/2026-10-15.1` | 2026-03-31 |
| MA | `sec-universe-raw-2026-10-17-all-shard3` | 2026-10-17T00:21:02 | `78082e9cbae91bfa` | `qgv2-calc/2026-10-15.1` | 2025-12-31 |
| RSG | `sec-universe-raw-2026-10-17-all-shard6` | 2026-10-17T00:32:59 | `f67b0cf72f216d6d` | `qgv2-calc/2026-10-15.1` | 2025-12-31 |
| MNST | `sec-universe-raw-2026-10-17-all-shard1` | 2026-10-17T00:10:41 | `64144475e8bf6500` | `qgv2-calc/2026-10-15.1` | 2025-12-31 |
| CMG | `sec-universe-raw-2026-10-17-all-shard5` | 2026-10-17T00:29:05 | `93c81e4ccae99f04` | `qgv2-calc/2026-10-15.1` | 2025-12-31 |
| EXPE | `sec-universe-raw-2026-10-17-all-shard4` | 2026-10-17T00:25:38 | `4af44d83f624debf` | `qgv2-calc/2026-10-15.1` | 2025-12-31 |

### A-2. production이 읽은 줄과 접수번호

production은 같은 기간을 보고한 가장 최근 제출물을 씁니다. 그래서 FY0 재무상태표 값은 다음 10-Q의 비교 열에서 올 수 있습니다(값은 10-K와 같음, 5절 보조 확인).

| 종목 | 줄: 개념 접수번호 (기간 끝) |
|---|---|
| FIX | 매출0 `Revenues` `0001104659-26-017530` (2025-12-31); 매출−3 `Revenues` `0001558370-25-001222` (2022-12-31); EBIT `OperatingIncomeLoss` `0001104659-26-017530` (2025-12-31); 세전 `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` `0001104659-26-017530` (2025-12-31); 법인세 `IncomeTaxExpenseBenefit` `0001104659-26-017530` (2025-12-31); D&A `DepreciationAndAmortization` `0001104659-26-017530` (2025-12-31); 감가상각 `Depreciation` `0001104659-26-017530` (2025-12-31); 무형상각 `AmortizationOfIntangibleAssets` `0001104659-26-017530` (2025-12-31); OCF `NetCashProvidedByUsedInOperatingActivities` `0001104659-26-017530` (2025-12-31); 설비투자 `PaymentsToAcquirePropertyPlantAndEquipment` `0001104659-26-017530` (2025-12-31); 자본0 `StockholdersEquity` `0001104659-26-086258` (2025-12-31); 자본−1 `StockholdersEquity` `0001104659-26-086258` (2024-12-31); 현금0 `CashAndCashEquivalentsAtCarryingValue` `0001104659-26-086258` (2025-12-31); 현금−1 `CashAndCashEquivalentsAtCarryingValue` `0001104659-26-017530` (2024-12-31); 부채0 `LongTermDebt` `0001104659-26-086258` (2025-12-31); 부채0(비유동) `LongTermDebtNoncurrent` `0001104659-26-086258` (2025-12-31); 부채0(유동) `LongTermDebtCurrent` `0001104659-26-086258` (2025-12-31); 부채−1 `LongTermDebt` `0001104659-26-017530` (2024-12-31); 부채−1(비유동) `LongTermDebtNoncurrent` `0001104659-26-017530` (2024-12-31); 부채−1(유동) `LongTermDebtCurrent` `0001104659-26-017530` (2024-12-31) |
| EME | 매출0 `Revenues` `0000105634-26-000025` (2025-12-31); 매출−3 `Revenues` `0000105634-25-000015` (2022-12-31); EBIT `OperatingIncomeLoss` `0000105634-26-000025` (2025-12-31); 세전 `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` `0000105634-26-000025` (2025-12-31); 법인세 `IncomeTaxExpenseBenefit` `0000105634-26-000025` (2025-12-31); 감가상각 `Depreciation` `0000105634-26-000025` (2025-12-31); 무형상각 `AmortizationOfIntangibleAssets` `0000105634-26-000025` (2025-12-31); OCF `NetCashProvidedByUsedInOperatingActivities` `0000105634-26-000025` (2025-12-31); 설비투자 `PaymentsToAcquireProductiveAssets` `0000105634-26-000025` (2025-12-31); 자본0 `StockholdersEquity` `0000105634-26-000110` (2025-12-31); 자본−1 `StockholdersEquity` `0000105634-26-000025` (2024-12-31); 현금0 `CashAndCashEquivalentsAtCarryingValue` `0000105634-26-000110` (2025-12-31); 현금−1 `CashAndCashEquivalentsAtCarryingValue` `0000105634-26-000025` (2024-12-31) |
| INCY | 매출0 `RevenueFromContractWithCustomerExcludingAssessedTax` `0000879169-26-000010` (2025-12-31); 매출−3 `Revenues` `0000879169-23-000008` (2022-12-31); EBIT `OperatingIncomeLoss` `0000879169-26-000010` (2025-12-31); 세전 `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` `0000879169-26-000010` (2025-12-31); 법인세 `IncomeTaxExpenseBenefit` `0000879169-26-000010` (2025-12-31); D&A `DepreciationDepletionAndAmortization` `0000879169-26-000010` (2025-12-31); OCF `NetCashProvidedByUsedInOperatingActivities` `0000879169-26-000010` (2025-12-31); 설비투자(F3) `PaymentsToAcquireOtherProductiveAssets` `0000879169-26-000010` (2025-12-31); 자본0 `StockholdersEquity` `0000879169-26-000026` (2025-12-31); 자본−1 `StockholdersEquity` `0000879169-26-000026` (2024-12-31); 현금0 `CashAndCashEquivalentsAtCarryingValue` `0000879169-26-000026` (2025-12-31); 현금−1 `CashAndCashEquivalentsAtCarryingValue` `0000879169-26-000010` (2024-12-31) |
| RL | 매출0 `Revenues` `0001628280-26-037074` (2026-03-28); 매출−3 `Revenues` `0001037038-25-000011` (2023-04-01); EBIT `OperatingIncomeLoss` `0001628280-26-037074` (2026-03-28); 세전 `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` `0001628280-26-037074` (2026-03-28); 법인세 `IncomeTaxExpenseBenefit` `0001628280-26-037074` (2026-03-28); D&A `DepreciationDepletionAndAmortization` `0001628280-26-037074` (2026-03-28); OCF `NetCashProvidedByUsedInOperatingActivities` `0001628280-26-037074` (2026-03-28); 설비투자(F3) `PaymentsToAcquireMachineryAndEquipment` `0001628280-26-037074` (2026-03-28); 자본0 `StockholdersEquity` `0001628280-26-053992` (2026-03-28); 자본−1 `StockholdersEquity` `0001628280-26-053992` (2025-03-29); 현금0 `CashAndCashEquivalentsAtCarryingValue` `0001628280-26-053992` (2026-03-28); 현금−1 `CashAndCashEquivalentsAtCarryingValue` `0001628280-26-037074` (2025-03-29); 부채0(비유동) `LongTermDebtNoncurrent` `0001628280-26-053992` (2026-03-28); 부채0(유동) `LongTermDebtCurrent` `0001628280-26-037074` (2026-03-28); 부채−1(비유동) `LongTermDebtNoncurrent` `0001628280-26-037074` (2025-03-29); 부채−1(유동) `LongTermDebtCurrent` `0001628280-26-037074` (2025-03-29) |
| DECK | 매출0 `RevenueFromContractWithCustomerExcludingAssessedTax` `0001628280-26-037664` (2026-03-31); 매출−3 `RevenueFromContractWithCustomerExcludingAssessedTax` `0000910521-25-000017` (2023-03-31); EBIT `OperatingIncomeLoss` `0001628280-26-037664` (2026-03-31); 법인세 `IncomeTaxExpenseBenefit` `0001628280-26-037664` (2026-03-31); D&A `DepreciationAmortizationAndAccretionNet` `0001628280-26-037664` (2026-03-31); OCF `NetCashProvidedByUsedInOperatingActivities` `0001628280-26-037664` (2026-03-31); 설비투자 `PaymentsToAcquirePropertyPlantAndEquipment` `0001628280-26-037664` (2026-03-31); 자본0 `StockholdersEquity` `0000910521-26-000022` (2026-03-31); 자본−1 `StockholdersEquity` `0000910521-26-000022` (2025-03-31); 현금0 `CashAndCashEquivalentsAtCarryingValue` `0000910521-26-000022` (2026-03-31); 현금−1 `CashAndCashEquivalentsAtCarryingValue` `0001628280-26-037664` (2025-03-31) |
| MA | 매출0 `Revenues` `0001141391-26-000013` (2025-12-31); 매출−3 `Revenues` `0001141391-25-000011` (2022-12-31); EBIT `OperatingIncomeLoss` `0001141391-26-000013` (2025-12-31); 세전 `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` `0001141391-26-000013` (2025-12-31); 법인세 `IncomeTaxExpenseBenefit` `0001141391-26-000013` (2025-12-31); D&A `DepreciationAmortizationAndAccretionNet` `0001141391-26-000013` (2025-12-31); OCF `NetCashProvidedByUsedInOperatingActivities` `0001141391-26-000013` (2025-12-31); 설비투자 `PaymentsToAcquirePropertyPlantAndEquipment` `0001141391-26-000013` (2025-12-31); 소프트웨어 `PaymentsToAcquireSoftware` `0001141391-26-000013` (2025-12-31); 자본0 `StockholdersEquity` `0001141391-26-000083` (2025-12-31); 자본−1 `StockholdersEquity` `0001141391-26-000013` (2024-12-31); 현금0 `CashAndCashEquivalentsAtCarryingValue` `0001141391-26-000083` (2025-12-31); 현금−1 `CashAndCashEquivalentsAtCarryingValue` `0001141391-26-000013` (2024-12-31); 부채0(비유동) `LongTermDebtNoncurrent` `0001141391-26-000083` (2025-12-31); 부채0(유동) `LongTermDebtCurrent` `0001141391-26-000083` (2025-12-31); 부채−1(비유동) `LongTermDebtNoncurrent` `0001141391-26-000013` (2024-12-31); 부채−1(유동) `LongTermDebtCurrent` `0001141391-26-000013` (2024-12-31) |
| RSG | 매출0 `RevenueFromContractWithCustomerExcludingAssessedTax` `0001060391-26-000094` (2025-12-31); 매출−3 `RevenueFromContractWithCustomerExcludingAssessedTax` `0001060391-25-000091` (2022-12-31); EBIT `OperatingIncomeLoss` `0001060391-26-000094` (2025-12-31); 세전 `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` `0001060391-26-000094` (2025-12-31); 법인세 `IncomeTaxExpenseBenefit` `0001060391-26-000094` (2025-12-31); D&A `DepreciationDepletionAndAmortization` `0001060391-26-000094` (2025-12-31); OCF `NetCashProvidedByUsedInOperatingActivities` `0001060391-26-000094` (2025-12-31); 설비투자 `PaymentsToAcquirePropertyPlantAndEquipment` `0001060391-26-000094` (2025-12-31); 자본0 `StockholdersEquity` `0001060391-26-000275` (2025-12-31); 자본−1 `StockholdersEquity` `0001060391-26-000094` (2024-12-31); 현금0 `CashAndCashEquivalentsAtCarryingValue` `0001060391-26-000275` (2025-12-31); 현금−1 `CashAndCashEquivalentsAtCarryingValue` `0001060391-26-000275` (2024-12-31); 부채0 `LongTermDebt` `0001060391-26-000094` (2025-12-31); 부채0(비유동) `LongTermDebtAndCapitalLeaseObligations` `0001060391-26-000275` (2025-12-31); 부채0(유동) `LongTermDebtAndCapitalLeaseObligationsCurrent` `0001060391-26-000275` (2025-12-31); 부채−1 `LongTermDebt` `0001060391-25-000091` (2024-12-31); 부채−1(비유동) `LongTermDebtAndCapitalLeaseObligations` `0001060391-26-000094` (2024-12-31); 부채−1(유동) `LongTermDebtAndCapitalLeaseObligationsCurrent` `0001060391-26-000094` (2024-12-31) |
| MNST | 매출0 `RevenueFromContractWithCustomerExcludingAssessedTax` `0001104659-26-020831` (2025-12-31); 매출−3 `RevenueFromContractWithCustomerExcludingAssessedTax` `0001410578-25-000248` (2022-12-31); EBIT `OperatingIncomeLoss` `0001104659-26-020831` (2025-12-31); 세전 `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` `0001104659-26-020831` (2025-12-31); 법인세 `IncomeTaxExpenseBenefit` `0001104659-26-020831` (2025-12-31); D&A `DepreciationDepletionAndAmortization` `0001104659-26-020831` (2025-12-31); OCF `NetCashProvidedByUsedInOperatingActivities` `0001104659-26-020831` (2025-12-31); 설비투자 `PaymentsToAcquirePropertyPlantAndEquipment` `0001104659-26-020831` (2025-12-31); 자본0 `StockholdersEquity` `0001104659-26-092193` (2025-12-31); 자본−1 `StockholdersEquity` `0001104659-26-092193` (2024-12-31); 현금0 `CashAndCashEquivalentsAtCarryingValue` `0001104659-26-092193` (2025-12-31); 현금−1 `CashAndCashEquivalentsAtCarryingValue` `0001104659-26-020831` (2024-12-31); 부채−1 `LongTermDebt` `0001104659-26-020831` (2024-12-31); 부채−1(비유동) `LongTermDebtNoncurrent` `0001104659-26-020831` (2024-12-31); 부채−1(유동) `LongTermDebtCurrent` `0001104659-25-107944` (2024-12-31) |
| CMG | 매출0 `Revenues` `0001058090-26-000009` (2025-12-31); 매출−3 `Revenues` `0001058090-25-000014` (2022-12-31); EBIT `OperatingIncomeLoss` `0001058090-26-000009` (2025-12-31); 세전 `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` `0001058090-26-000009` (2025-12-31); 법인세 `IncomeTaxExpenseBenefit` `0001058090-26-000009` (2025-12-31); D&A `DepreciationDepletionAndAmortization` `0001058090-26-000009` (2025-12-31); OCF `NetCashProvidedByUsedInOperatingActivities` `0001058090-26-000009` (2025-12-31); 설비투자 `PaymentsToAcquirePropertyPlantAndEquipment` `0001058090-26-000009` (2025-12-31); 자본0 `StockholdersEquity` `0001058090-26-000066` (2025-12-31); 자본−1 `StockholdersEquity` `0001058090-26-000066` (2024-12-31); 현금0 `CashAndCashEquivalentsAtCarryingValue` `0001058090-26-000066` (2025-12-31); 현금−1 `CashAndCashEquivalentsAtCarryingValue` `0001058090-26-000009` (2024-12-31); 부채0 `LongTermDebt` `0001058090-26-000009` (2025-12-31); 부채−1 `LongTermDebt` `0001058090-25-000014` (2024-12-31) |
| EXPE | 매출0 `RevenueFromContractWithCustomerExcludingAssessedTax` `0001324424-26-000008` (2025-12-31); 매출−3 `RevenueFromContractWithCustomerExcludingAssessedTax` `0001324424-25-000008` (2022-12-31); EBIT `OperatingIncomeLoss` `0001324424-26-000008` (2025-12-31); 세전 `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` `0001324424-26-000008` (2025-12-31); 법인세 `IncomeTaxExpenseBenefit` `0001324424-26-000008` (2025-12-31); D&A `DepreciationDepletionAndAmortization` `0001324424-26-000008` (2025-12-31); OCF `NetCashProvidedByUsedInOperatingActivities` `0001324424-26-000008` (2025-12-31); 설비투자 `PaymentsToAcquirePropertyPlantAndEquipment` `0001324424-26-000008` (2025-12-31); 자본0 `StockholdersEquity` `0001324424-26-000053` (2025-12-31); 자본−1 `StockholdersEquity` `0001324424-26-000008` (2024-12-31); 현금0 `CashAndCashEquivalentsAtCarryingValue` `0001324424-26-000053` (2025-12-31); 현금−1 `CashAndCashEquivalentsAtCarryingValue` `0001324424-26-000008` (2024-12-31); 부채0 `LongTermDebt` `0001324424-26-000053` (2025-12-31); 부채0(비유동) `LongTermDebtNoncurrent` `0001324424-26-000053` (2025-12-31); 부채0(유동) `LongTermDebtCurrent` `0001324424-26-000053` (2025-12-31); 부채−1 `LongTermDebt` `0001324424-26-000008` (2024-12-31); 부채−1(비유동) `LongTermDebtNoncurrent` `0001324424-26-000008` (2024-12-31); 부채−1(유동) `LongTermDebtCurrent` `0001324424-26-000008` (2024-12-31) |

### A-3. 10-K 원값 (손계산 B 입력)

접수번호는 각 사실을 보고한 가장 최근 10-K입니다. FY−3 매출은 보통 직전 해 10-K에서 왔습니다. TTM 줄의 YTD는 10-Q 사실입니다(10-K 아님).

#### FIX — 최신 10-K `0001104659-26-017530` (제출 2026-02-19), FY0 = 2025-12-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `Revenues` | 9,101.6 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 매출 FY−3 | `Revenues` | 4,140.4 | 2022-01-01~2022-12-31 | `0001558370-25-001222` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 1,314.6 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 1,293.5 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 270.9 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| D&A | `Depreciation` | 62.4 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| D&A | `AmortizationOfIntangibleAssets` | 79.6 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 이자비용 | `InterestExpense` | 9.0 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 1,186.4 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 설비투자 | `PaymentsToAcquirePropertyPlantAndEquipment` | 154.9 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 2,448.8 | 2025-12-31 | `0001104659-26-017530` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 981.9 | 2025-12-31 | `0001104659-26-017530` (10-K) |
| 부채 FY0 | `LongTermDebt` | 145.2 | 2025-12-31 | `0001104659-26-017530` (10-K) |
| 자기자본 FY−1 | `StockholdersEquity` | 1,704.7 | 2024-12-31 | `0001104659-26-017530` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 549.9 | 2024-12-31 | `0001104659-26-017530` (10-K) |
| 부채 FY−1 | `LongTermDebt` | 68.3 | 2024-12-31 | `0001104659-26-017530` (10-K) |

손계산(B): 세율 20.94%, IC0 1,612.1, IC−1 1,223.1, EBITDA 1,456.5

TTM(10-Q, 2026-06-30): `NetCashProvidedByUsedInOperatingActivities`: FY 1,186.4 + YTD 1,528.3 − 전년 YTD 164.5 (`0001104659-26-086258`); `PaymentsToAcquirePropertyPlantAndEquipment`: FY 154.9 + YTD 288.8 − 전년 YTD 53.5 (`0001104659-26-086258`) → FCF TTM 2,159.8

#### EME — 최신 10-K `0000105634-26-000025` (제출 2026-02-26), FY0 = 2025-12-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `Revenues` | 16,986.4 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 매출 FY−3 | `Revenues` | 11,076.1 | 2022-01-01~2022-12-31 | `0000105634-25-000015` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 1,713.4 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 1,721.6 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 448.8 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| D&A | `Depreciation` | 67.4 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| D&A | `AmortizationOfIntangibleAssets` | 119.1 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 이자비용 | `InterestExpense` | 12.0 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 1,302.1 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 설비투자 | `PaymentsToAcquireProductiveAssets` | 112.8 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 3,673.9 | 2025-12-31 | `0000105634-26-000025` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 1,112.0 | 2025-12-31 | `0000105634-26-000025` (10-K) |
| 부채 FY0 | (10-K에 차입 항목 없음 → 10-K 표시 기준 0, 금융리스 제외. 정책 판단은 아래 줄) | 0.0 | | |
| 자기자본 FY−1 | `StockholdersEquity` | 2,937.7 | 2024-12-31 | `0000105634-26-000025` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 1,339.5 | 2024-12-31 | `0000105634-26-000025` (10-K) |
| 부채 FY−1 | (10-K에 차입 항목 없음 → 10-K 표시 기준 0, 금융리스 제외. 정책 판단은 아래 줄) | 0.0 | | |

손계산(B): 세율 26.07%, IC0 2,562.0, IC−1 1,598.1, EBITDA 1,899.8

정책 확인(Q-NODEBT) FY−0: 0이 아닌 차입 개념 없음, 이자비용 `InterestExpense` 12.0, 금융리스 `FinanceLeaseLiability` 6.3, `FinanceLeaseLiabilityNoncurrent` 3.9, `FinanceLeaseLiabilityCurrent` 2.4 → 부채 NA (Q-NODEBT-INT)

정책 확인(Q-NODEBT) FY−1: 0이 아닌 차입 개념 없음, 이자비용 `InterestExpense` 3.8, 금융리스 `FinanceLeaseLiability` 6.1, `FinanceLeaseLiabilityNoncurrent` 3.8, `FinanceLeaseLiabilityCurrent` 2.2 → 부채 NA (Q-NODEBT-INT)

TTM(10-Q, 2026-06-30): `NetCashProvidedByUsedInOperatingActivities`: FY 1,302.1 + YTD 289.9 − 전년 YTD 302.2 (`0000105634-26-000110`); `PaymentsToAcquireProductiveAssets`: FY 112.8 + YTD 59.9 − 전년 YTD 54.2 (`0000105634-26-000110`) → FCF TTM 1,171.4

#### INCY — 최신 10-K `0000879169-26-000010` (제출 2026-02-10), FY0 = 2025-12-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 5,141.2 | 2025-01-01~2025-12-31 | `0000879169-26-000010` (10-K) |
| 매출 FY−3 | `Revenues` | 3,394.6 | 2022-01-01~2022-12-31 | `0000879169-23-000008` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 1,514.9 | 2025-01-01~2025-12-31 | `0000879169-26-000010` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 1,664.5 | 2025-01-01~2025-12-31 | `0000879169-26-000010` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 377.8 | 2025-01-01~2025-12-31 | `0000879169-26-000010` (10-K) |
| D&A | `DepreciationDepletionAndAmortization` | 93.3 | 2025-01-01~2025-12-31 | `0000879169-26-000010` (10-K) |
| 이자비용 | `InterestExpenseNonoperating` | 2.4 | 2025-01-01~2025-12-31 | `0000879169-26-000010` (10-K) |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 1,413.5 | 2025-01-01~2025-12-31 | `0000879169-26-000010` (10-K) |
| 설비투자 | `PaymentsToAcquireOtherProductiveAssets` | 58.9 | 2025-01-01~2025-12-31 | `0000879169-26-000010` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 5,167.5 | 2025-12-31 | `0000879169-26-000010` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 3,097.8 | 2025-12-31 | `0000879169-26-000010` (10-K) |
| 부채 FY0 | (10-K에 차입 항목 없음 → 10-K 표시 기준 0, 금융리스 제외. 정책 판단은 아래 줄) | 0.0 | | |
| 자기자본 FY−1 | `StockholdersEquity` | 3,447.6 | 2024-12-31 | `0000879169-26-000010` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 1,687.8 | 2024-12-31 | `0000879169-26-000010` (10-K) |
| 부채 FY−1 | (10-K에 차입 항목 없음 → 10-K 표시 기준 0, 금융리스 제외. 정책 판단은 아래 줄) | 0.0 | | |

손계산(B): 세율 22.70%, IC0 2,069.7, IC−1 1,759.8, EBITDA 1,608.1

정책 확인(Q-NODEBT) FY−0: 0이 아닌 차입 개념 없음, 이자비용 `InterestExpenseNonoperating` 2.4, 금융리스 `FinanceLeaseLiability` 34.7, `FinanceLeaseLiabilityNoncurrent` 30.2, `FinanceLeaseLiabilityCurrent` 4.5 → 부채 NA (Q-NODEBT-INT)

정책 확인(Q-NODEBT) FY−1: 0이 아닌 차입 개념 없음, 이자비용 `InterestExpenseNonoperating` 2.3, 금융리스 `FinanceLeaseLiability` 38.0, `FinanceLeaseLiabilityNoncurrent` 33.5, `FinanceLeaseLiabilityCurrent` 4.4 → 부채 NA (Q-NODEBT-INT)

TTM(10-Q, 2026-03-31): `NetCashProvidedByUsedInOperatingActivities`: FY 1,413.5 + YTD 369.4 − 전년 YTD 266.1 (`0000879169-26-000026`); `PaymentsToAcquireOtherProductiveAssets`: FY 58.9 + YTD 10.2 − 전년 YTD 3.2 (`0000879169-26-000026`) → FCF TTM 1,450.9

#### RL — 최신 10-K `0001628280-26-037074` (제출 2026-05-21), FY0 = 2026-03-28

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `Revenues` | 8,114.5 | 2025-03-30~2026-03-28 | `0001628280-26-037074` (10-K) |
| 매출 FY−3 | `Revenues` | 6,443.6 | 2022-04-03~2023-04-01 | `0001037038-25-000011` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 1,179.2 | 2025-03-30~2026-03-28 | `0001628280-26-037074` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 1,177.7 | 2025-03-30~2026-03-28 | `0001628280-26-037074` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 236.6 | 2025-03-30~2026-03-28 | `0001628280-26-037074` (10-K) |
| D&A | `DepreciationDepletionAndAmortization` | 233.0 | 2025-03-30~2026-03-28 | `0001628280-26-037074` (10-K) |
| 이자비용 | `InterestExpense` | 54.2 | 2025-03-30~2026-03-28 | `0001628280-26-037074` (10-K) |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 1,154.2 | 2025-03-30~2026-03-28 | `0001628280-26-037074` (10-K) |
| 설비투자 | `PaymentsToAcquireMachineryAndEquipment` | 408.1 | 2025-03-30~2026-03-28 | `0001628280-26-037074` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 2,841.4 | 2026-03-28 | `0001628280-26-037074` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 1,988.0 | 2026-03-28 | `0001628280-26-037074` (10-K) |
| 부채 FY0 | `LongTermDebtNoncurrent` | 1,238.9 | 2026-03-28 | `0001628280-26-037074` (10-K) |
| 부채 FY0 | `LongTermDebtCurrent` | 0.0 | 2026-03-28 | `0001628280-26-037074` (10-K) |
| 부채 FY0 | `CommercialPaper` | 0.0 | 2026-03-28 | `0001628280-26-037074` (10-K) |
| 자기자본 FY−1 | `StockholdersEquity` | 2,588.5 | 2025-03-29 | `0001628280-26-037074` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 1,922.5 | 2025-03-29 | `0001628280-26-037074` (10-K) |
| 부채 FY−1 | `LongTermDebtNoncurrent` | 742.9 | 2025-03-29 | `0001628280-26-037074` (10-K) |
| 부채 FY−1 | `LongTermDebtCurrent` | 399.7 | 2025-03-29 | `0001628280-26-037074` (10-K) |
| 부채 FY−1 | `CommercialPaper` | 0.0 | 2025-03-29 | `0001628280-26-037074` (10-K) |

손계산(B): 세율 20.09%, IC0 2,092.3, IC−1 1,808.6, EBITDA 1,412.2

TTM(10-Q, 2026-06-27): `NetCashProvidedByUsedInOperatingActivities`: FY 1,154.2 + YTD 339.3 − 전년 YTD 176.1 (`0001628280-26-053992`); 설비투자 FY 408.1(`PaymentsToAcquireMachineryAndEquipment`, 10-K) + 10-Q `PaymentsToAcquireProductiveAssets` YTD 53.4 − 전년 YTD 187.3 (`0001628280-26-053992`) → FCF TTM 1,043.2 (참고값. 두 개념을 섞은 값이라 production은 F3 단일 개념 규칙대로 TTM NA, 기기는 FY 746.1 사용)

#### DECK — 최신 10-K `0001628280-26-037664` (제출 2026-05-22), FY0 = 2026-03-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 5,472.3 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 매출 FY−3 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 3,627.3 | 2022-04-01~2023-03-31 | `0000910521-25-000017` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 1,262.9 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic` | 1,084.4 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesForeign` | 241.9 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 302.3 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| D&A | `DepreciationAmortizationAndAccretionNet` | 75.8 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 이자비용 | `InterestExpenseNonoperating` | 2.5 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 1,182.0 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 설비투자 | `PaymentsToAcquirePropertyPlantAndEquipment` | 84.6 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 2,499.6 | 2026-03-31 | `0001628280-26-037664` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 1,907.2 | 2026-03-31 | `0001628280-26-037664` (10-K) |
| 부채 FY0 | (10-K에 차입 항목 없음 → 10-K 표시 기준 0, 금융리스 제외. 정책 판단은 아래 줄) | 0.0 | | |
| 자기자본 FY−1 | `StockholdersEquity` | 2,513.0 | 2025-03-31 | `0001628280-26-037664` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 1,889.2 | 2025-03-31 | `0001628280-26-037664` (10-K) |
| 부채 FY−1 | (10-K에 차입 항목 없음 → 10-K 표시 기준 0, 금융리스 제외. 정책 판단은 아래 줄) | 0.0 | | |

손계산(B): 세율 22.79%, IC0 592.4, IC−1 623.8, EBITDA 1,338.7

정책 확인(Q-NODEBT) FY−0: 0이 아닌 차입 개념 없음, 이자비용 `InterestExpenseNonoperating` 2.5, 금융리스 없음 → 부채 NA (Q-NODEBT-INT)

정책 확인(Q-NODEBT) FY−1: 0이 아닌 차입 개념 없음, 이자비용 `InterestExpenseNonoperating` 3.5, 금융리스 없음 → 부채 NA (Q-NODEBT-INT)

TTM(10-Q, 2026-06-30): `NetCashProvidedByUsedInOperatingActivities`: FY 1,182.0 + YTD 47.9 − 전년 YTD 36.1 (`0000910521-26-000022`); `PaymentsToAcquirePropertyPlantAndEquipment`: FY 84.6 + YTD 15.2 − 전년 YTD 23.9 (`0000910521-26-000022`) → FCF TTM 1,117.8

#### MA — 최신 10-K `0001141391-26-000013` (제출 2026-02-11), FY0 = 2025-12-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `Revenues` | 32,791.0 | 2025-01-01~2025-12-31 | `0001141391-26-000013` (10-K) |
| 매출 FY−3 | `Revenues` | 22,237.0 | 2022-01-01~2022-12-31 | `0001141391-25-000011` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 18,897.0 | 2025-01-01~2025-12-31 | `0001141391-26-000013` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 18,578.0 | 2025-01-01~2025-12-31 | `0001141391-26-000013` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 3,610.0 | 2025-01-01~2025-12-31 | `0001141391-26-000013` (10-K) |
| D&A | `DepreciationAmortizationAndAccretionNet` | 1,143.0 | 2025-01-01~2025-12-31 | `0001141391-26-000013` (10-K) |
| 이자비용 | `InterestExpenseNonoperating` | 722.0 | 2025-01-01~2025-12-31 | `0001141391-26-000013` (10-K) |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 17,648.0 | 2025-01-01~2025-12-31 | `0001141391-26-000013` (10-K) |
| 설비투자 | `PaymentsToAcquirePropertyPlantAndEquipment` | 489.0 | 2025-01-01~2025-12-31 | `0001141391-26-000013` (10-K) |
| 설비투자 | `PaymentsToAcquireSoftware` | 726.0 | 2025-01-01~2025-12-31 | `0001141391-26-000013` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 7,737.0 | 2025-12-31 | `0001141391-26-000013` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 10,566.0 | 2025-12-31 | `0001141391-26-000013` (10-K) |
| 부채 FY0 | `LongTermDebtNoncurrent` | 18,251.0 | 2025-12-31 | `0001141391-26-000013` (10-K) |
| 부채 FY0 | `LongTermDebtCurrent` | 749.0 | 2025-12-31 | `0001141391-26-000013` (10-K) |
| 자기자본 FY−1 | `StockholdersEquity` | 6,485.0 | 2024-12-31 | `0001141391-26-000013` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 8,442.0 | 2024-12-31 | `0001141391-26-000013` (10-K) |
| 부채 FY−1 | `LongTermDebtNoncurrent` | 17,476.0 | 2024-12-31 | `0001141391-26-000013` (10-K) |
| 부채 FY−1 | `LongTermDebtCurrent` | 750.0 | 2024-12-31 | `0001141391-26-000013` (10-K) |

손계산(B): 세율 19.43%, IC0 16,171.0, IC−1 16,269.0, EBITDA 20,040.0

TTM(10-Q, 2026-06-30): `NetCashProvidedByUsedInOperatingActivities`: FY 17,648.0 + YTD 6,772.0 − 전년 YTD 6,983.0 (`0001141391-26-000083`); `PaymentsToAcquirePropertyPlantAndEquipment`: FY 489.0 + YTD 445.0 − 전년 YTD 199.0 (`0001141391-26-000083`); `PaymentsToAcquireSoftware`: FY 726.0 + YTD 368.0 − 전년 YTD 367.0 (`0001141391-26-000083`) → FCF TTM 15,975.0

#### RSG — 최신 10-K `0001060391-26-000094` (제출 2026-02-18), FY0 = 2025-12-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 16,591.0 | 2025-01-01~2025-12-31 | `0001060391-26-000094` (10-K) |
| 매출 FY−3 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 13,511.0 | 2022-01-01~2022-12-31 | `0001060391-25-000091` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 3,302.0 | 2025-01-01~2025-12-31 | `0001060391-26-000094` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 2,594.0 | 2025-01-01~2025-12-31 | `0001060391-26-000094` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 455.0 | 2025-01-01~2025-12-31 | `0001060391-26-000094` (10-K) |
| D&A | `DepreciationDepletionAndAmortization` | 1,814.0 | 2025-01-01~2025-12-31 | `0001060391-26-000094` (10-K) |
| 이자비용 | `InterestExpenseNonoperating` | 574.0 | 2025-01-01~2025-12-31 | `0001060391-26-000094` (10-K) |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 4,296.0 | 2025-01-01~2025-12-31 | `0001060391-26-000094` (10-K) |
| 설비투자 | `PaymentsToAcquirePropertyPlantAndEquipment` | 1,887.0 | 2025-01-01~2025-12-31 | `0001060391-26-000094` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 11,968.0 | 2025-12-31 | `0001060391-26-000094` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 76.0 | 2025-12-31 | `0001060391-26-000094` (10-K) |
| 부채 FY0 | `LongTermDebt` | 13,710.0 | 2025-12-31 | `0001060391-26-000094` (10-K) |
| 자기자본 FY−1 | `StockholdersEquity` | 11,405.0 | 2024-12-31 | `0001060391-26-000094` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 74.0 | 2024-12-31 | `0001060391-26-000094` (10-K) |
| 부채 FY−1 | `LongTermDebt` | 12,840.0 | 2024-12-31 | `0001060391-25-000091` (10-K) |

손계산(B): 세율 17.54%, IC0 25,602.0, IC−1 24,171.0, EBITDA 5,116.0

TTM(10-Q, 2026-06-30): `NetCashProvidedByUsedInOperatingActivities`: FY 4,296.0 + YTD 2,380.0 − 전년 YTD 2,134.0 (`0001060391-26-000275`); `PaymentsToAcquirePropertyPlantAndEquipment`: FY 1,887.0 + YTD 868.0 − 전년 YTD 866.0 (`0001060391-26-000275`) → FCF TTM 2,653.0

#### MNST — 최신 10-K `0001104659-26-020831` (제출 2026-02-27), FY0 = 2025-12-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 8,294.3 | 2025-01-01~2025-12-31 | `0001104659-26-020831` (10-K) |
| 매출 FY−3 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 6,311.1 | 2022-01-01~2022-12-31 | `0001410578-25-000248` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 2,419.4 | 2025-01-01~2025-12-31 | `0001104659-26-020831` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 2,482.5 | 2025-01-01~2025-12-31 | `0001104659-26-020831` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 577.1 | 2025-01-01~2025-12-31 | `0001104659-26-020831` (10-K) |
| D&A | `DepreciationDepletionAndAmortization` | 114.4 | 2025-01-01~2025-12-31 | `0001104659-26-020831` (10-K) |
| 이자비용 | (10-K에 해당 개념 없음) | NA | | |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 2,098.2 | 2025-01-01~2025-12-31 | `0001104659-26-020831` (10-K) |
| 설비투자 | `PaymentsToAcquirePropertyPlantAndEquipment` | 132.3 | 2025-01-01~2025-12-31 | `0001104659-26-020831` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 8,254.1 | 2025-12-31 | `0001104659-26-020831` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 2,088.1 | 2025-12-31 | `0001104659-26-020831` (10-K) |
| 부채 FY0 | (10-K에 차입 항목 없음 → 10-K 표시 기준 0, 금융리스 제외. 정책 판단은 아래 줄) | 0.0 | | |
| 자기자본 FY−1 | `StockholdersEquity` | 5,957.7 | 2024-12-31 | `0001104659-26-020831` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 1,533.3 | 2024-12-31 | `0001104659-26-020831` (10-K) |
| 부채 FY−1 | `LongTermDebt` | 374.0 | 2024-12-31 | `0001104659-26-020831` (10-K) |

손계산(B): 세율 23.25%, IC0 6,166.0, IC−1 4,798.4, EBITDA 2,533.8

정책 확인(Q-NODEBT) FY−0: 0이 아닌 차입 개념 없음, 이자비용 없음, 금융리스 없음 → 부채 0

TTM(10-Q, 2026-06-30): `NetCashProvidedByUsedInOperatingActivities`: FY 2,098.2 + YTD 1,114.2 − 전년 YTD 973.6 (`0001104659-26-092193`); `PaymentsToAcquirePropertyPlantAndEquipment`: FY 132.3 + YTD 69.0 − 전년 YTD 60.5 (`0001104659-26-092193`) → FCF TTM 2,097.9

#### CMG — 최신 10-K `0001058090-26-000009` (제출 2026-02-04), FY0 = 2025-12-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `Revenues` | 11,925.6 | 2025-01-01~2025-12-31 | `0001058090-26-000009` (10-K) |
| 매출 FY−3 | `Revenues` | 8,634.7 | 2022-01-01~2022-12-31 | `0001058090-25-000014` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 1,935.8 | 2025-01-01~2025-12-31 | `0001058090-26-000009` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 2,009.5 | 2025-01-01~2025-12-31 | `0001058090-26-000009` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 473.8 | 2025-01-01~2025-12-31 | `0001058090-26-000009` (10-K) |
| D&A | `DepreciationDepletionAndAmortization` | 361.4 | 2025-01-01~2025-12-31 | `0001058090-26-000009` (10-K) |
| 이자비용 | (10-K에 해당 개념 없음) | NA | | |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 2,113.9 | 2025-01-01~2025-12-31 | `0001058090-26-000009` (10-K) |
| 설비투자 | `PaymentsToAcquirePropertyPlantAndEquipment` | 666.3 | 2025-01-01~2025-12-31 | `0001058090-26-000009` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 2,830.6 | 2025-12-31 | `0001058090-26-000009` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 350.5 | 2025-12-31 | `0001058090-26-000009` (10-K) |
| 부채 FY0 | `LongTermDebt` | 0.0 | 2025-12-31 | `0001058090-26-000009` (10-K) |
| 자기자본 FY−1 | `StockholdersEquity` | 3,655.5 | 2024-12-31 | `0001058090-26-000009` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 748.5 | 2024-12-31 | `0001058090-26-000009` (10-K) |
| 부채 FY−1 | `LongTermDebt` | 0.0 | 2024-12-31 | `0001058090-25-000014` (10-K) |

손계산(B): 세율 23.58%, IC0 2,480.1, IC−1 2,907.0, EBITDA 2,297.2

정책 확인(Q-NODEBT) FY−0: 0이 아닌 차입 개념 없음, 이자비용 없음, 금융리스 없음 → 부채 0

정책 확인(Q-NODEBT) FY−1: 0이 아닌 차입 개념 없음, 이자비용 없음, 금융리스 없음 → 부채 0

TTM(10-Q, 2026-06-30): `NetCashProvidedByUsedInOperatingActivities`: FY 2,113.9 + YTD 1,332.0 − 전년 YTD 1,118.4 (`0001058090-26-000066`); `PaymentsToAcquirePropertyPlantAndEquipment`: FY 666.3 + YTD 397.6 − 전년 YTD 305.4 (`0001058090-26-000066`) → FCF TTM 1,569.0

#### EXPE — 최신 10-K `0001324424-26-000008` (제출 2026-02-13), FY0 = 2025-12-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 14,733.0 | 2025-01-01~2025-12-31 | `0001324424-26-000008` (10-K) |
| 매출 FY−3 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 11,667.0 | 2022-01-01~2022-12-31 | `0001324424-25-000008` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 1,871.0 | 2025-01-01~2025-12-31 | `0001324424-26-000008` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 1,591.0 | 2025-01-01~2025-12-31 | `0001324424-26-000008` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 290.0 | 2025-01-01~2025-12-31 | `0001324424-26-000008` (10-K) |
| D&A | `DepreciationDepletionAndAmortization` | 887.0 | 2025-01-01~2025-12-31 | `0001324424-26-000008` (10-K) |
| 이자비용 | `InterestExpenseNonoperating` | 299.0 | 2025-01-01~2025-12-31 | `0001324424-26-000008` (10-K) |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 3,880.0 | 2025-01-01~2025-12-31 | `0001324424-26-000008` (10-K) |
| 설비투자 | `PaymentsToAcquirePropertyPlantAndEquipment` | 770.0 | 2025-01-01~2025-12-31 | `0001324424-26-000008` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 1,284.0 | 2025-12-31 | `0001324424-26-000008` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 5,413.0 | 2025-12-31 | `0001324424-26-000008` (10-K) |
| 부채 FY0 | `LongTermDebt` | 6,161.0 | 2025-12-31 | `0001324424-26-000008` (10-K) |
| 자기자본 FY−1 | `StockholdersEquity` | 1,557.0 | 2024-12-31 | `0001324424-26-000008` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 4,183.0 | 2024-12-31 | `0001324424-26-000008` (10-K) |
| 부채 FY−1 | `LongTermDebt` | 6,266.0 | 2024-12-31 | `0001324424-26-000008` (10-K) |

손계산(B): 세율 18.23%, IC0 2,032.0, IC−1 3,640.0, EBITDA 2,758.0

TTM(10-Q, 2026-06-30): `NetCashProvidedByUsedInOperatingActivities`: FY 3,880.0 + YTD 5,409.0 − 전년 YTD 4,073.0 (`0001324424-26-000053`); `PaymentsToAcquirePropertyPlantAndEquipment`: FY 770.0 + YTD 383.0 − 전년 YTD 396.0 (`0001324424-26-000053`) → FCF TTM 4,459.0
