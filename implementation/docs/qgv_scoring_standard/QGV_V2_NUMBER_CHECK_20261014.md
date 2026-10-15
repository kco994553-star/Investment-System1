# QGV v2 숫자 대조 — 10-K 원값 vs production (오너 과제 3a, 2026-10-14)

**결론: 조건부 통과.** production 코드는 문서 정의를 그대로 계산합니다. production에 값이 있는 30칸은 모두 문서 정의대로 한 10-K 원값 손계산과 반올림 오차 안에서 같습니다. 다만 10-K 재무제표에 나온 그대로 계산하면 **2칸이 5% 이상 다르고**(FIX 순부채/EBITDA, RSG 매출 CAGR), **10칸은 production이 NA인데 10-K에는 값이 있습니다**. 원인은 모두 계산 오류가 아니라 **태그 선택과 무차입 처리 규칙**입니다. 아래 7절의 수정·결정 전에는 해당 7개 후보를 확정하지 않는 것이 맞습니다.

- 대상: v2 Q·G 상위 30 초안([QGV_V2_QUALITY_20261014.md](QGV_V2_QUALITY_20261014.md) 3절) 중 10개입니다. 상위 5개(FIX, EME, INCY, RL, DECK)에 서로 다른 업종군 5개(MA 서비스, RSG 유틸리티·폐기물, MNST 식음료, CMG 도소매, EXPE 운송)를 더했습니다. 금융 프로필(ERIE, PGR)은 ROIC 대신 ROE를 쓰므로 뺐습니다. 모두 8개 업종군에서 골랐습니다.
- 지표: ROIC, 3년 매출 CAGR, FCF 수익률, 순부채/EBITDA.
- **FCF 수익률은 '기기 전용'입니다.** 가격(EV)이 필요해서 레포와 이 환경에서는 계산하지 않습니다. 분자 FCF(영업현금흐름 − 설비투자)만 FY(10-K)와 TTM(10-Q)으로 대조했습니다.
- 가격, 시가총액, 가격 파생값은 이 문서에 없습니다. 금액은 SEC에 보고된 그대로이고 단위는 USD 백만입니다.

## 1. 방법

1. **원자료.** 공개 SEC companyfacts의 비공개 사본입니다. 10-14 품질 보고서가 실제로 쓴 사본과 같습니다. FIX·MNST는 10-12 샤드, INCY는 10-13 샤드, DECK는 10-11 샤드, 나머지 6개는 `c21`(2026-09-25)입니다. 각 사본의 취득일을 cutoff로 썼습니다. 네 샤드 회사는 `c21` 사본으로 다시 계산해도 네 지표가 모두 같습니다. 원자료는 새 빈 디렉터리에 풀었고, 스크립트는 따로 두었고, `python3 -I`로만 읽었습니다. 원자료와 스크립트는 레포에 넣지 않았습니다.
2. **production 재현.** `sec_qgv2.build_row` → `v2_factors.compute`를 그대로 호출했습니다. 10개 모두 보고서 값(`ROIC`, `revenue_cagr_3y`, `net_debt_to_ebitda`, `v_inputs_v2.fcf`)과 비트 단위로 같습니다.
3. **손계산(독립 스크립트).** `v2_factors`를 import하지 않습니다. JSON에서 **form 10-K 사실만** 골랐고, 기간마다 그 기간을 보고한 가장 최근 10-K의 값을 썼습니다. 정의는 [QGV_V2_QG_METHOD.md](QGV_V2_QG_METHOD.md) 1·2절을 따랐습니다. ROIC = EBIT₀·(1 − 세율) / 평균(IC₀, IC₋₁), 세율 = 법인세/세전이익(0~50%로 제한, 세전이익 ≤ 0이거나 없으면 21%), IC = 자기자본 + 부채 − 현금입니다. 손계산은 두 가지로 했습니다.
   - **A (문서 정의)**: 문서의 개념 우선순위를 그대로 적용했습니다. 코드가 문서대로 계산하는지 확인하는 용도입니다.
   - **B (10-K 표시)**: 10-K 재무제표 항목 그대로입니다. 문서 목록 밖의 태그로 보고된 항목은 회사별로 직접 골랐고, 근거는 3절과 부록에 있습니다. **판정은 B 기준입니다.**
4. **판정.** 상대 차이 < 5%면 **일치**, ≥ 5%이거나 한쪽만 NA면 **차이(원인)**, 입력이 없어 대조할 수 없으면 **확인 불가**입니다.

### '원문'의 뜻 — HTML 아님, 10-K에 첨부된 XBRL 사실

- 이 컨테이너는 sec.gov에 접속할 수 없습니다(프록시 차단).
- 비공개 raw 레포 클론 `/home/user/investment-system1-raw`의 작업 트리에는 `README.md` 하나뿐입니다. 10-K HTML이나 primary document는 **없습니다**(태그 `raw-c21-store-…`만 있음).
- 그 레포의 릴리스 사본(`c21.zip`)에도 **10개 회사의 최신 10-K 원문은 없습니다**. 있는 것은 MA의 2024년 10-Q HTML 3건, RL의 FY2024 10-K XBRL instance 1건(과 10-Q 2건), 다른 회사의 2024년 10-K HTML 29건입니다.
- 따라서 이 문서에서 '10-K 원값'은 **10-K에 첨부된 XBRL 사실**(companyfacts의 `form=10-K` 행: 개념, 값, 기간, 접수번호)이고, **HTML 본문이 아닙니다**.
- 보조로 companyfacts가 제출 문서와 같은지 확인했습니다. 문서에 보이는 숫자(iXBRL 표시값 × scale, 부호)나 instance 값을 같은 접수번호·개념·기간의 companyfacts 값과 비교했습니다. 결과는 **5건 191/191 일치**입니다.

| 문서 | 형식 | 비교 | 일치 |
|---|---|---:|---:|
| MA 10-Q 2024-09-30 `0001141391-24-000202` (HTML) | iXBRL 표시값 | 36 | 36 |
| RL FY2024 10-K `0001037038-24-000014` (XBRL instance) | instance 값. 이번 RL FY−3 매출 6,443.6 포함 | 37 | 37 |
| A. O. Smith FY2023 10-K `0000091142-24-000041` (HTML) | iXBRL 표시값 | 41 | 41 |
| Mettler-Toledo FY2023 10-K `0001037646-24-000007` (HTML) | iXBRL 표시값 | 39 | 39 |
| Coca-Cola Consolidated FY2023 10-K `0000317540-24-000009` (HTML) | iXBRL 표시값 | 38 | 38 |

## 2. 판정표

P = production(보고서 값), H = 10-K 원값 손계산(B). ROIC·CAGR은 %, 순부채/EBITDA는 배, FCF는 FY 기준 USD 백만입니다.

| 종목 (FY0) | ROIC P / H | 판정 | 매출 CAGR 3y P / H | 판정 | 순부채/EBITDA P / H | 판정 | FCF 분자 P / H | 판정 | FCF 수익률 |
|---|---|---|---|---|---|---|---|---|---|
| FIX (2025-12) | 73.31 / 73.31 | 일치 | 30.03 / 30.03 | 일치 | −0.608 / −0.574 | **차이 5.5% (D&A 태그)** | 1,031.5 / 1,031.5 | 일치 | 확인 불가 (기기 전용) |
| EME (2025-12) | NA / 60.90 | **차이 (무차입 → NA)** | 15.32 / 15.32 | 일치 | NA / −0.585 | **차이 (무차입 + D&A 태그 없음)** | 1,189.3 / 1,189.3 | 일치 | 확인 불가 (기기 전용) |
| INCY (2025-12) | NA / 61.16 | **차이 (무차입 → NA)** | 14.84 / 14.84 | 일치 | NA / −1.926 | **차이 (무차입 → NA)** | NA / 1,354.6 | **차이 (설비투자 태그)** | 확인 불가 (기기 전용) |
| RL (2026-03) | 48.31 / 48.31 | 일치 | 7.99 / 7.99 | 일치 | −0.530 / −0.530 | 일치 | NA / 746.1 | **차이 (설비투자 태그)** | 확인 불가 (기기 전용) |
| DECK (2026-03) | NA / 160.35 | **차이 (무차입 → NA, 세전이익 태그)** | 14.69 / 14.69 | 일치 | NA / −1.425 | **차이 (무차입 → NA)** | 1,097.3 / 1,097.3 | 일치 | 확인 불가 (기기 전용) |
| MA (2025-12) | 93.87 / 93.87 | 일치 | 13.82 / 13.82 | 일치 | 0.421 / 0.421 | 일치 | 17,159 / 17,159 | 일치 (소프트웨어 투자 포함 시 −4.2%) | 확인 불가 (기기 전용) |
| RSG (2025-12) | 10.94 / 10.94 | 일치 | 6.74 / 7.08 | **차이 5.1% (매출 태그)** | 2.665 / 2.665 | 일치 | 2,409 / 2,409 | 일치 | 확인 불가 (기기 전용) |
| MNST (2025-12) | NA / 33.87 | **차이 (FY0 부채 상환 → NA)** | 9.54 / 9.54 | 일치 | NA / −0.824 | **차이 (FY0 부채 상환 → NA)** | 1,965.9 / 1,965.9 | 일치 | 확인 불가 (기기 전용) |
| CMG (2025-12) | 54.92 / 54.92 | 일치 | 11.36 / 11.36 | 일치 | −0.153 / −0.153 | 일치 | 1,447.6 / 1,447.6 | 일치 | 확인 불가 (기기 전용) |
| EXPE (2025-12) | 53.95 / 53.95 | 일치 | 8.09 / 8.09 | 일치 | 0.271 / 0.271 | 일치 | 3,110 / 3,110 | 일치 | 확인 불가 (기기 전용) |

- **집계(4지표 × 10 = 40칸):** 일치 28 / 차이 12(수치 ≥ 5% 2, production NA·10-K 값 있음 10) / 확인 불가 0. FCF 수익률 10칸은 따로 모두 '확인 불가(기기 전용)'입니다.
- **A(문서 정의) vs production:** 40칸 모두 같습니다(값 30칸은 상대 오차 < 3×10⁻⁶로 6자리 반올림 수준이고, NA 10칸도 같습니다). **코드 버그·기간 정렬·평균·세율·부호 오류는 없습니다.** 차이는 전부 문서 정의(태그 목록·무차입 규칙)와 10-K 표시 방식의 차이입니다.
- **FCF TTM**(기기가 V에 쓰는 값): production 값이 있는 8개는 손계산(FY + 당기 YTD − 전년 YTD, 10-Q)과 0.0% 차이입니다. INCY·RL은 production이 NA이고, 10-K/10-Q 기준으로는 각각 1,450.9(2026-03 기준)와 1,043.2입니다.
- **회사별:** 차이 없음 3개(MA, CMG, EXPE), 1칸 차이 3개(FIX, RL, RSG), 2~3칸 차이 4개(EME, INCY, DECK, MNST)입니다.

## 3. 차이별 원인

### 3-1. 수치 차이 ≥ 5%

| 종목·지표 | P | H | 차이 | 원인 |
|---|---:|---:|---:|---|
| FIX 순부채/EBITDA | −0.6076 | −0.5744 | 5.5% | **D&A 태그 선택.** 문서 우선순위 3번째 `DepreciationAndAmortization` = 62.4는 **감가상각만**(`Depreciation` 62.379의 반올림)입니다. 10-K 현금흐름표에는 무형자산 상각 `AmortizationOfIntangibleAssets` 79.6이 따로 있습니다. EBITDA가 1,377.0 → 1,456.6이 됩니다. 순현금 회사라 방향은 '덜 음수'입니다(순현금 836.7은 같음). |
| RSG 매출 3년 CAGR | 6.74% | 7.08% | 5.1% | **매출 태그 선택.** 문서 1순위 `Revenues`(FY0 19,027 / FY−3 15,645)는 세그먼트 주석의 **내부거래 제거 전 총매출**입니다. 손익계산서 매출은 `RevenueFromContractWithCustomerExcludingAssessedTax`(16,591 / 13,511)입니다. 매출 수준 자체가 14.7% 큽니다. 같은 원인으로 범위 밖 지표도 왜곡됩니다. `gross_profit_to_assets`는 0.273 vs 0.203이고(GrossProfit 태그가 없어 매출 − 원가로 계산), `operating_margin_history` FY0은 17.4% vs 19.9%입니다. |

### 3-2. production NA, 10-K에는 값 있음

| 원인 | 종목·지표 | 설명 | 10-K 기준 값 |
|---|---|---|---|
| **무차입(부채 태그 없음) → 문서 규칙상 NA** | EME·INCY·DECK ROIC·순부채/EBITDA, MNST(FY0) ROIC·순부채/EBITDA | 최신 10-K의 부채성 instant 사실을 모두 훑었습니다. EME·INCY·DECK에는 차입 항목이 전혀 없고 금융리스만 있습니다(문서 정의상 제외). MNST는 FY−1 `LongTermDebt` 374.0이 FY0에는 사라졌습니다(상환). 문서 1절 "If none of these lines is reported, debt is NA"를 그대로 따른 결과이며, 문서 7절 열린 항목입니다. | 부채 = 0으로 보면 ROIC EME 60.9%, INCY 61.2%, DECK 160.3%, MNST 33.9% / 순부채/EBITDA EME −0.585, INCY −1.926, DECK −1.425, MNST −0.824 |
| **D&A 합계 태그 없음** | EME 순부채/EBITDA(부채 NA와 겹침) | 10-K는 `Depreciation` 67.4와 `AmortizationOfIntangibleAssets` 119.1만 보고합니다. 합계 태그 3종이 모두 없습니다. 10-13 보고의 "D&A 태그 부족 49곳"에 EME가 들어 있습니다. | EBITDA 1,899.8 |
| **설비투자 태그가 목록 밖** | INCY FCF | 현금흐름표 설비투자가 `PaymentsToAcquireOtherProductiveAssets`(58.9)입니다. `PaymentsToAcquirePropertyPlantAndEquipment`는 2024-05 건물 매입 1개월치 사실만 있습니다. | FCF 1,354.6 |
| | RL FCF | FY2026 10-K(접수번호 접두가 `0001628280-`로 바뀜)부터 `PaymentsToAcquireMachineryAndEquipment`(408.1)로 태그합니다. FY2024(instance로 확인)·FY2025 10-K와 모든 10-Q는 `PaymentsToAcquireProductiveAssets`입니다. FY0 값이 없어서 FY와 TTM이 모두 NA가 됩니다. | FCF 746.1 (TTM 1,043.2) |
| **세전이익 합계 태그 없음** (ROIC NA와 겹침) | DECK | 세전이익이 국내·해외(`…Domestic` 1,084.4 + `…Foreign` 241.9)로만 보고됩니다. production 세율은 기본값 21%이고 실제 세율은 22.79%입니다. 지금은 ROIC가 무차입으로 NA라 드러나지 않지만, `incremental_roic_*`의 NOPAT에는 이미 영향이 있습니다. | 세율 22.79% |

### 3-3. 5% 미만이지만 기록해 둘 점

- **MA FCF:** 문서 정의의 설비투자는 유형자산(489)뿐입니다. 10-K 현금흐름표에는 소프트웨어 자본화 `PaymentsToAcquireSoftware`(726)가 따로 있습니다. 넣으면 FCF가 17,159 → 16,433(−4.2%), TTM은 −4.4%입니다. 정의 결정이 필요한 사항이고 계산 오류는 아닙니다.
- **RSG 부채:** 1순위 `LongTermDebt`(13,710)는 주석의 장부가 합계입니다. 재무상태표 행(`LongTermDebtAndCapitalLeaseObligations` 12,985 + 유동 596 = 13,581)과 0.9% 다릅니다.
- **EXPE 자기자본:** 문서 1순위 `StockholdersEquity`(지배주주 1,284)를 썼습니다. 비지배지분 포함 자기자본(2,547)이면 ROIC가 53.9% → 37.4%가 됩니다. 문서 정의와 같은 값이며, 비지배지분이 큰 회사의 민감도로만 기록합니다.
- **INCY 매출 개념 전환:** FY0(2025)는 `RevenueFromContract…`(5,141.2), FY−3(2022)는 `Revenues`(3,394.6)입니다. 둘 다 각 10-K의 '총매출' 행이라 같은 항목입니다. 수치 영향은 없습니다.
- **INCY TTM 공백:** submissions에는 2026-07-28 10-Q(`0000879169-26-000056`)가 있지만 companyfacts 사본에는 아직 없습니다. TTM이 2026-03 기준에 머뭅니다.

## 4. KLAC(주식분할)·D&A 공백 — 10개 중 해당 여부

- **KLAC 형 주식분할 미조정: 해당 없음.** 대조한 네 지표는 주당 값을 쓰지 않습니다. 10개 중 최근 3년 안에 분할이 있었던 CMG(2024 50:1), DECK(2024 6:1), MNST(2023 2:1)도 production `dilution_3y`가 −1.5%, −3.1%, −2.6%로 정상 범위입니다. 최신 10-K의 FY−3 주식수가 분할 후 기준으로 재작성되어 있기 때문입니다. KLAC(OperatingIncomeLoss 미보고 + 분할 불연속)는 상위 30에 없고 이번 표본에도 없습니다.
- **D&A 공백: EME가 해당합니다**(합계 태그 없음, 10-13 보고의 49곳 목록에 있음). **FIX는 형태가 다른 D&A 과소**입니다(합계 태그가 감가상각만 담음, 3-1). 나머지 8개는 D&A 합계 태그가 있고 10-K 현금흐름표 값과 같습니다.

## 5. 같은 원인의 전체 규모 (Universe504 GENERAL us-gaap 428 발행사, 같은 사본, 참고용)

| 원인 | 건수 | 상위 30 해당 |
|---|---:|---|
| FY0 부채 NA(자기자본·EBIT는 있음) → ROIC·순부채/EBITDA NA | 35 | DECK, DXCM, EME, INCY, MNST |
| D&A: 감가상각 + 무형상각 합이 production D&A보다 5% 넘게 크거나 production NA | 46 | EME, FIX |
| 설비투자 NA인데 대체 설비투자 태그 있음 | 29 | INCY, RL |
| `Revenues`가 `RevenueFromContract…`보다 5% 넘게 큼 | 19 | RSG |

**주의:**
- 부채 NA 35곳이 모두 무차입은 아닙니다. 상위 30의 DXCM과 ORCL, F, GM, DLR, EQIX처럼 전환사채나 다른 태그로 부채를 보고하는 곳이 섞여 있습니다. 그래서 'NA → 0' 일괄 규칙은 틀린 값을 만듭니다.
- 매출 19곳의 대부분(AMT, CCI, ESS, UDR 등 리츠)은 `Revenues`가 맞고 `RevenueFromContract…`가 일부 매출일 뿐입니다. '작은 쪽 우선' 같은 일괄 규칙도 틀립니다.

## 6. 종합 판정: **조건부 통과**

| 구분 | 종목 | 근거 |
|---|---|---|
| 통과 | MA, CMG, EXPE | 4지표 모두 10-K 원값과 일치(FCF 수익률은 기기 전용) |
| 조건부 통과 (1칸, 원인 확인) | FIX, RL, RSG | 차이 원인이 태그 하나이고 방향과 크기가 확인됐습니다. Q/G 순위 영향은 재계산 후 확인이 필요합니다. |
| 조건부 통과 (NA 요인으로 계산) | EME, INCY, DECK, MNST | 값이 있는 칸은 모두 일치합니다. 다만 ROIC와 순부채/EBITDA가 NA라서 Q가 일부 하위지표 없이 계산됐습니다(INCY·DECK·MNST는 `q_moat_proxy`도 NA, MNST는 `q_financial_safety`도 NA). |

production 계산 자체는 정확합니다. 그래도 **상위 30 확정 전에** 아래 7절의 1~4를 결정하거나 반영하고, Q·G를 다시 계산해서 위 7개 종목의 순위를 다시 봐야 합니다.

## 7. 고칠 것 (이 PR에서는 코드 변경 없음, 오너 결정 필요)

1. **무차입 처리 규칙(가장 큰 영향).** 문서 7절 열린 항목을 결정해야 합니다. 제안은 "그 10-K에 부채성 개념(문서 목록 + `ConvertibleNotesPayable`·`SeniorNotes`·`LongTermLineOfCredit`·`DebtInstrumentCarryingAmount` 등)이 하나도 없고, 직전 연도 대비 상환 흐름이나 이자비용이 작을 때만 0"입니다. 5절 주의처럼 일괄 0은 안 됩니다. 영향 종목은 EME, INCY, DECK, MNST(+ DXCM은 별도 태그 보강)입니다.
2. **D&A 보강.** 합계 태그가 없으면 `Depreciation` + `AmortizationOfIntangibleAssets`로 보충합니다(EME 등 NA 해소). 합계 태그가 그 합보다 작으면 합을 쓸지 결정해야 합니다(FIX).
3. **설비투자 목록 보강.** `PaymentsToAcquireOtherProductiveAssets`, `PaymentsToAcquireMachineryAndEquipment`, `PaymentsForCapitalImprovements` 등을 뒤 순위로 추가합니다(INCY, RL). 소프트웨어 자본화(`PaymentsToAcquireSoftware`)를 FCF에 넣을지도 결정이 필요합니다(MA −4.2%).
4. **매출 태그 예외.** `Revenues`가 내부거래 제거 전 총매출인 경우(RSG)를 처리해야 합니다. 제안은 "같은 10-K에 두 개념이 함께 있고 `Revenues` − `RevenueFromContract…`가 세그먼트 내부거래 금액과 같으면 손익계산서 쪽"이거나 발행사별 예외 목록입니다. 일괄 규칙은 리츠를 깨뜨립니다.
5. (작음) **세전이익 보강.** 합계 태그가 없으면 `…Domestic` + `…Foreign`을 씁니다(DECK 세율 21% → 22.8%).

## 8. 재현

스크립트는 세션 스크래치(`nc_scripts/`)에만 있고 레포에는 넣지 않았습니다.
- `extract.py`: 10개 CIK를 새 빈 디렉터리에 풉니다.
- `prod_run.py`: production `build_row`로 재현하고, 보고서 값과 비교하고, `c21`과 교차합니다.
- `hand.py`: 독립 손계산 A/B와 TTM을 계산합니다.
- `doccheck.py`: 문서 표시값과 companyfacts를 비교합니다.
- `scan.py`: 5절 규모 집계입니다.
- `gen.py`: 부록 표를 만듭니다.

모두 `python3 -I`로 실행했습니다.

## 부록. 회사별 10-K 원값 (손계산 입력)

같은 항목에서 A와 B가 다르면 두 줄로 적었습니다(`[문서 정의]` / `[10-K 표시]`). 접수번호는 각 사실을 보고한 가장 최근 10-K입니다. FY−3 매출은 보통 직전 해 10-K에서 왔습니다. TTM 줄의 YTD는 10-Q 사실입니다(10-K 아님).

#### FIX — 최신 10-K `0001104659-26-017530` (제출 2026-02-19), FY0 = 2025-12-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `Revenues` | 9,101.6 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 매출 FY−3 | `Revenues` | 4,140.4 | 2022-01-01~2022-12-31 | `0001558370-25-001222` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 1,314.6 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 1,293.5 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 270.9 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| [문서 정의] D&A | `DepreciationAndAmortization` | 62.4 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| [10-K 표시] D&A | `Depreciation` | 62.4 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| [10-K 표시] D&A | `AmortizationOfIntangibleAssets` | 79.6 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 이자비용 | `InterestExpense` | 9.0 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 1,186.4 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 설비투자 | `PaymentsToAcquirePropertyPlantAndEquipment` | 154.9 | 2025-01-01~2025-12-31 | `0001104659-26-017530` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 2,448.8 | 2025-12-31 | `0001104659-26-017530` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 981.9 | 2025-12-31 | `0001104659-26-017530` (10-K) |
| 부채 FY0 | `LongTermDebt` | 145.2 | 2025-12-31 | `0001104659-26-017530` (10-K) |
| 자기자본 FY−1 | `StockholdersEquity` | 1,704.7 | 2024-12-31 | `0001104659-26-017530` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 549.9 | 2024-12-31 | `0001104659-26-017530` (10-K) |
| 부채 FY−1 | `LongTermDebt` | 68.3 | 2024-12-31 | `0001104659-26-017530` (10-K) |

문서 정의(A): 세율 20.94%, IC0 1,612.1, IC−1 1,223.1
10-K 표시(B): 세율 20.94%, IC0 1,612.1, IC−1 1,223.1

TTM(10-Q, 2026-06-30): NetCashProvidedByUsedInOperatingActivities: FY 1,186.4 + YTD 1,528.3 − 전년 YTD 164.5 (`0001104659-26-086258`); PaymentsToAcquirePropertyPlantAndEquipment: FY 154.9 + YTD 288.8 − 전년 YTD 53.5 (`0001104659-26-086258`) → FCF TTM 2,159.8

#### EME — 최신 10-K `0000105634-26-000025` (제출 2026-02-26), FY0 = 2025-12-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `Revenues` | 16,986.4 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 매출 FY−3 | `Revenues` | 11,076.1 | 2022-01-01~2022-12-31 | `0000105634-25-000015` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 1,713.4 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 1,721.6 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 448.8 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| [문서 정의] D&A | (10-K에 해당 개념 없음) | NA | | |
| [10-K 표시] D&A | `Depreciation` | 67.4 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| [10-K 표시] D&A | `AmortizationOfIntangibleAssets` | 119.1 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 이자비용 | `InterestExpense` | 12.0 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 1,302.1 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 설비투자 | `PaymentsToAcquireProductiveAssets` | 112.8 | 2025-01-01~2025-12-31 | `0000105634-26-000025` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 3,673.9 | 2025-12-31 | `0000105634-26-000025` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 1,112.0 | 2025-12-31 | `0000105634-26-000025` (10-K) |
| [문서 정의] 부채 FY0 | (10-K에 해당 개념 없음) | NA | | |
| [10-K 표시] 부채 FY0 | (10-K에 차입 항목 없음 → 0, 금융리스는 문서 정의대로 제외) | 0.0 | | |
| 자기자본 FY−1 | `StockholdersEquity` | 2,937.7 | 2024-12-31 | `0000105634-26-000025` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 1,339.5 | 2024-12-31 | `0000105634-26-000025` (10-K) |
| [문서 정의] 부채 FY−1 | (10-K에 해당 개념 없음) | NA | | |
| [10-K 표시] 부채 FY−1 | (10-K에 차입 항목 없음 → 0, 금융리스는 문서 정의대로 제외) | 0.0 | | |

문서 정의(A): 세율 26.07%, IC0 NA, IC−1 NA
10-K 표시(B): 세율 26.07%, IC0 2,562.0, IC−1 1,598.1

TTM(10-Q, 2026-06-30): NetCashProvidedByUsedInOperatingActivities: FY 1,302.1 + YTD 289.9 − 전년 YTD 302.2 (`0000105634-26-000110`); PaymentsToAcquireProductiveAssets: FY 112.8 + YTD 59.9 − 전년 YTD 54.2 (`0000105634-26-000110`) → FCF TTM 1,171.4

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
| [문서 정의] 설비투자 | (10-K에 해당 개념 없음) | NA | | |
| [10-K 표시] 설비투자 | `PaymentsToAcquireOtherProductiveAssets` | 58.9 | 2025-01-01~2025-12-31 | `0000879169-26-000010` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 5,167.5 | 2025-12-31 | `0000879169-26-000010` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 3,097.8 | 2025-12-31 | `0000879169-26-000010` (10-K) |
| [문서 정의] 부채 FY0 | (10-K에 해당 개념 없음) | NA | | |
| [10-K 표시] 부채 FY0 | (10-K에 차입 항목 없음 → 0, 금융리스는 문서 정의대로 제외) | 0.0 | | |
| 자기자본 FY−1 | `StockholdersEquity` | 3,447.6 | 2024-12-31 | `0000879169-26-000010` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 1,687.8 | 2024-12-31 | `0000879169-26-000010` (10-K) |
| [문서 정의] 부채 FY−1 | (10-K에 해당 개념 없음) | NA | | |
| [10-K 표시] 부채 FY−1 | (10-K에 차입 항목 없음 → 0, 금융리스는 문서 정의대로 제외) | 0.0 | | |

문서 정의(A): 세율 22.70%, IC0 NA, IC−1 NA
10-K 표시(B): 세율 22.70%, IC0 2,069.7, IC−1 1,759.8

TTM(10-Q, 2026-03-31): NetCashProvidedByUsedInOperatingActivities: FY 1,413.5 + YTD 369.4 − 전년 YTD 266.1 (`0000879169-26-000026`); PaymentsToAcquireOtherProductiveAssets: FY 58.9 + YTD 10.2 − 전년 YTD 3.2 (`0000879169-26-000026`) → FCF TTM 1,450.9

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
| [문서 정의] 설비투자 | (10-K에 해당 개념 없음) | NA | | |
| [10-K 표시] 설비투자 | `PaymentsToAcquireMachineryAndEquipment` | 408.1 | 2025-03-30~2026-03-28 | `0001628280-26-037074` (10-K) |
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

문서 정의(A): 세율 20.09%, IC0 2,092.3, IC−1 1,808.6
10-K 표시(B): 세율 20.09%, IC0 2,092.3, IC−1 1,808.6

TTM(10-Q, 2026-06-27): NetCashProvidedByUsedInOperatingActivities: FY 1,154.2 + YTD 339.3 − 전년 YTD 176.1 (`0001628280-26-053992`); 설비투자: FY 408.1(`PaymentsToAcquireMachineryAndEquipment`, 10-K) + 10-Q는 `PaymentsToAcquireProductiveAssets`로 태그, YTD 53.4 − 전년 YTD 187.3 (`0001628280-26-053992`) → FCF TTM 1,043.2

#### DECK — 최신 10-K `0001628280-26-037664` (제출 2026-05-22), FY0 = 2026-03-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| 매출 FY0 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 5,472.3 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 매출 FY−3 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 3,627.3 | 2022-04-01~2023-03-31 | `0000910521-25-000017` (10-K) |
| 영업이익(EBIT) | `OperatingIncomeLoss` | 1,262.9 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| [문서 정의] 세전이익 | (10-K에 해당 개념 없음) | NA | | |
| [10-K 표시] 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic` | 1,084.4 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| [10-K 표시] 세전이익 | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesForeign` | 241.9 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 법인세 | `IncomeTaxExpenseBenefit` | 302.3 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| D&A | `DepreciationAmortizationAndAccretionNet` | 75.8 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 이자비용 | `InterestExpenseNonoperating` | 2.5 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 영업현금흐름 | `NetCashProvidedByUsedInOperatingActivities` | 1,182.0 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 설비투자 | `PaymentsToAcquirePropertyPlantAndEquipment` | 84.6 | 2025-04-01~2026-03-31 | `0001628280-26-037664` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 2,499.6 | 2026-03-31 | `0001628280-26-037664` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 1,907.2 | 2026-03-31 | `0001628280-26-037664` (10-K) |
| [문서 정의] 부채 FY0 | (10-K에 해당 개념 없음) | NA | | |
| [10-K 표시] 부채 FY0 | (10-K에 차입 항목 없음 → 0, 금융리스는 문서 정의대로 제외) | 0.0 | | |
| 자기자본 FY−1 | `StockholdersEquity` | 2,513.0 | 2025-03-31 | `0001628280-26-037664` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 1,889.2 | 2025-03-31 | `0001628280-26-037664` (10-K) |
| [문서 정의] 부채 FY−1 | (10-K에 해당 개념 없음) | NA | | |
| [10-K 표시] 부채 FY−1 | (10-K에 차입 항목 없음 → 0, 금융리스는 문서 정의대로 제외) | 0.0 | | |

문서 정의(A): 세율 21.00%, IC0 NA, IC−1 NA
10-K 표시(B): 세율 22.79%, IC0 592.4, IC−1 623.8

TTM(10-Q, 2026-06-30): NetCashProvidedByUsedInOperatingActivities: FY 1,182.0 + YTD 47.9 − 전년 YTD 36.1 (`0000910521-26-000022`); PaymentsToAcquirePropertyPlantAndEquipment: FY 84.6 + YTD 15.2 − 전년 YTD 23.9 (`0000910521-26-000022`) → FCF TTM 1,117.8

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
| [문서 정의] 설비투자 | `PaymentsToAcquirePropertyPlantAndEquipment` | 489.0 | 2025-01-01~2025-12-31 | `0001141391-26-000013` (10-K) |
| [10-K 표시] 설비투자 | `PaymentsToAcquirePropertyPlantAndEquipment` | 489.0 | 2025-01-01~2025-12-31 | `0001141391-26-000013` (10-K) |
| [10-K 표시] 설비투자 | `PaymentsToAcquireSoftware` | 726.0 | 2025-01-01~2025-12-31 | `0001141391-26-000013` (10-K) |
| 자기자본 FY0 | `StockholdersEquity` | 7,737.0 | 2025-12-31 | `0001141391-26-000013` (10-K) |
| 현금 FY0 | `CashAndCashEquivalentsAtCarryingValue` | 10,566.0 | 2025-12-31 | `0001141391-26-000013` (10-K) |
| 부채 FY0 | `LongTermDebtNoncurrent` | 18,251.0 | 2025-12-31 | `0001141391-26-000013` (10-K) |
| 부채 FY0 | `LongTermDebtCurrent` | 749.0 | 2025-12-31 | `0001141391-26-000013` (10-K) |
| 자기자본 FY−1 | `StockholdersEquity` | 6,485.0 | 2024-12-31 | `0001141391-26-000013` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 8,442.0 | 2024-12-31 | `0001141391-26-000013` (10-K) |
| 부채 FY−1 | `LongTermDebtNoncurrent` | 17,476.0 | 2024-12-31 | `0001141391-26-000013` (10-K) |
| 부채 FY−1 | `LongTermDebtCurrent` | 750.0 | 2024-12-31 | `0001141391-26-000013` (10-K) |

문서 정의(A): 세율 19.43%, IC0 16,171.0, IC−1 16,269.0
10-K 표시(B): 세율 19.43%, IC0 16,171.0, IC−1 16,269.0

TTM(10-Q, 2026-06-30): NetCashProvidedByUsedInOperatingActivities: FY 17,648.0 + YTD 6,772.0 − 전년 YTD 6,983.0 (`0001141391-26-000083`); PaymentsToAcquirePropertyPlantAndEquipment: FY 489.0 + YTD 445.0 − 전년 YTD 199.0 (`0001141391-26-000083`); PaymentsToAcquireSoftware: FY 726.0 + YTD 368.0 − 전년 YTD 367.0 (`0001141391-26-000083`) → FCF TTM 15,975.0

#### RSG — 최신 10-K `0001060391-26-000094` (제출 2026-02-18), FY0 = 2025-12-31

| 항목 | 개념 (us-gaap) | 값 (USD 백만) | 기간 | 접수번호 (form) |
|---|---|---:|---|---|
| [문서 정의] 매출 FY0 | `Revenues` | 19,027.0 | 2025-01-01~2025-12-31 | `0001060391-26-000094` (10-K) |
| [10-K 표시] 매출 FY0 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 16,591.0 | 2025-01-01~2025-12-31 | `0001060391-26-000094` (10-K) |
| [문서 정의] 매출 FY−3 | `Revenues` | 15,645.0 | 2022-01-01~2022-12-31 | `0001060391-25-000091` (10-K) |
| [10-K 표시] 매출 FY−3 | `RevenueFromContractWithCustomerExcludingAssessedTax` | 13,511.0 | 2022-01-01~2022-12-31 | `0001060391-25-000091` (10-K) |
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

문서 정의(A): 세율 17.54%, IC0 25,602.0, IC−1 24,171.0
10-K 표시(B): 세율 17.54%, IC0 25,602.0, IC−1 24,171.0

TTM(10-Q, 2026-06-30): NetCashProvidedByUsedInOperatingActivities: FY 4,296.0 + YTD 2,380.0 − 전년 YTD 2,134.0 (`0001060391-26-000275`); PaymentsToAcquirePropertyPlantAndEquipment: FY 1,887.0 + YTD 868.0 − 전년 YTD 866.0 (`0001060391-26-000275`) → FCF TTM 2,653.0

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
| [문서 정의] 부채 FY0 | (10-K에 해당 개념 없음) | NA | | |
| [10-K 표시] 부채 FY0 | (10-K에 차입 항목 없음 → 0, 금융리스는 문서 정의대로 제외) | 0.0 | | |
| 자기자본 FY−1 | `StockholdersEquity` | 5,957.7 | 2024-12-31 | `0001104659-26-020831` (10-K) |
| 현금 FY−1 | `CashAndCashEquivalentsAtCarryingValue` | 1,533.3 | 2024-12-31 | `0001104659-26-020831` (10-K) |
| 부채 FY−1 | `LongTermDebt` | 374.0 | 2024-12-31 | `0001104659-26-020831` (10-K) |

문서 정의(A): 세율 23.25%, IC0 NA, IC−1 4,798.4
10-K 표시(B): 세율 23.25%, IC0 6,166.0, IC−1 4,798.4

TTM(10-Q, 2026-06-30): NetCashProvidedByUsedInOperatingActivities: FY 2,098.2 + YTD 1,114.2 − 전년 YTD 973.6 (`0001104659-26-092193`); PaymentsToAcquirePropertyPlantAndEquipment: FY 132.3 + YTD 69.0 − 전년 YTD 60.5 (`0001104659-26-092193`) → FCF TTM 2,097.9

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

문서 정의(A): 세율 23.58%, IC0 2,480.1, IC−1 2,907.0
10-K 표시(B): 세율 23.58%, IC0 2,480.1, IC−1 2,907.0

TTM(10-Q, 2026-06-30): NetCashProvidedByUsedInOperatingActivities: FY 2,113.9 + YTD 1,332.0 − 전년 YTD 1,118.4 (`0001058090-26-000066`); PaymentsToAcquirePropertyPlantAndEquipment: FY 666.3 + YTD 397.6 − 전년 YTD 305.4 (`0001058090-26-000066`) → FCF TTM 1,569.0

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

문서 정의(A): 세율 18.23%, IC0 2,032.0, IC−1 3,640.0
10-K 표시(B): 세율 18.23%, IC0 2,032.0, IC−1 3,640.0

TTM(10-Q, 2026-06-30): NetCashProvidedByUsedInOperatingActivities: FY 3,880.0 + YTD 5,409.0 − 전년 YTD 4,073.0 (`0001324424-26-000053`); PaymentsToAcquirePropertyPlantAndEquipment: FY 770.0 + YTD 383.0 − 전년 YTD 396.0 (`0001324424-26-000053`) → FCF TTM 4,459.0
