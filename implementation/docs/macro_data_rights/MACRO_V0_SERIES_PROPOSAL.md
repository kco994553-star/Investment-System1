# Macro v0 나머지 6축 정확한 series 제안 — 한 번에 승인용

작성: 2026-10-11 UTC. 상태: **원자료 표시만 승인 (2026-10-11), 국면 판정 보류**. 구현 내용과 첫 Actions 실행에서 확인할 항목은 [§5](#5-2026-10-11-결정-반영--원자료-표시-구현)에 있다. FX는 공개 가격 경계 때문에 값을 공개하지 않는다.

## 0. 이미 결정·구현된 2축 (참고)

2026-10-11 사용자 결정: "Growth는 발표된 연율 %, Inflation은 CPI NSA YoY. 나머지 축은 한 번에 승인할 수 있게 정확한 series를 제안하라."

| 축 | 기관 · series | 빈도 · 조정 | v0 변환 | 구현 위치 |
| --- | --- | --- | --- | --- |
| Growth | BEA NIPA Table 1.1.1 (`T10101`) line 1, series code `A191RL`. Real GDP, percent change from preceding period | 분기 · SAAR | 발표값 그대로 ÷100. 재계산하지 않음 | `macro/growth_inflation_v0.py` |
| Inflation | BLS CPI-U all items, `CUUR0000SA0` | 월 · NSA | index_t / index_{t−12개월} − 1. 결측 월은 채우지 않음 | 같은 파일 |

- 두 값은 **기존 MacroEngine v0.1.1 임계값에만** 들어간다. 새 임계값·가중치·국면 대응표는 없다.
- 8축 국면은 대응표가 채택될 때까지 `NOT_AVAILABLE`(`EIGHT_AXIS_MAPPING_NOT_ADOPTED`)이다.
- 모든 값에는 `v0 · UNCALIBRATED` 표시가 붙는다. 기본값이며 나중에 바꿀 수 있다.
- BEA 자료는 키가 필요 없는 공개 flat file(`NipaDataQ.txt`)로 받는다. 이 경로가 실패하고 선택 설정 `BEA_USERID`가 있을 때만 BEA API를 쓴다.

## 1. 선정 원칙

- **원기관만** 쓴다(BLS, BEA, Federal Reserve Board, Treasury). FRED는 원기관 series를 다시 올린 경우 **참고 표기로만** 이름을 적는다. FRED/ALFRED에서 수집하지 않는다(GSQ-011).
- 축마다 **series 하나**와 **변환 하나**만 둔다. 여러 series를 섞은 합성 점수는 없다.
- 결측은 0으로 채우지 않는다. 결측이면 `NOT_AVAILABLE`과 이유 코드를 남긴다.
- 이 제안을 승인하면 **입력 series와 변환만** 확정된다. 축별 상태 판정 임계값, 6상태(Direction·Momentum·Surprise·Stress·Confidence), 8축 국면 대응표는 따로 승인해야 한다. 승인 전에는 계속 `NOT_AVAILABLE`이다.
- 아래 시각과 주기는 정기 일정이다. 실제 최초 공개 시각의 증거는 아니다. 공개 JSON은 지금처럼 `release_basis=NOT_VERIFIED`, 수집 시각을 상한으로 둔다.

## 2. 축별 제안

| 축 | 기관 · 발표 | 정확한 series | 빈도 | SA/NSA | v0 변환 |
| --- | --- | --- | --- | --- | --- |
| Labor | BLS, Employment Situation (CPS) | `LNS14000000`: Unemployment rate, 16 years and over | 월 | SA | 발표된 %를 그대로 ÷100 (수준) |
| Monetary Policy | Federal Reserve Board H.15 (Selected Interest Rates). 산출 원기관은 FRBNY(EFFR) | `RIFSPFF_N.B`: Federal funds effective rate, business day. 공식 파일 `releases/h15/data/Business_day/H15_FF_O.txt` | 영업일 | NSA | 해당 월 영업일 값의 단순 평균 ÷100. 영업일이 하나라도 빠지면 그 달은 NA |
| Liquidity | Federal Reserve Board H.4.1, Table 5 "Consolidated Statement of Condition of All Federal Reserve Banks" | line "Total assets", **Wednesday level**, 백만 USD. FRED 재게시 ID `WALCL`(참고 표기만) | 주(수요일) | NSA | 수요일 잔액 / 정확히 52주 전 수요일 잔액 − 1. 그 수요일 자료가 없으면 NA |
| Credit | Federal Reserve Board H.8, Table 2 (All commercial banks, SA) | line 1 "Bank credit", **월간 수준**, 십억 USD. FRED 재게시 ID `LOANINV`(참고 표기만) | 월 | SA | level_t / level_{t−12개월} − 1 |
| Fiscal | Treasury FiscalData, Monthly Treasury Statement Table 1 (`/v1/accounting/mts/mts_table_1`) | 월별 행의 `current_month_dfct_sur_amt` (당월 재정수지, 적자는 음수) | 월 | NSA | 최근 12개월 합계(12개월이 모두 있어야 함). 단위는 dataset dictionary를 그대로 따름 |
| FX | Federal Reserve Board H.10 | `JRXWTFB_N.M`: Nominal Broad U.S. Dollar Index, 월평균 (일간 원series `JRXWTFB_N.B`). FRED 재게시 ID `TWEXBGSMTH`(참고 표기만) | 월 | NSA | index_t / index_{t−12개월} − 1 |

### 축별 근거와 알려진 한계

| 축 | 근거 (한 줄) | 알려진 한계 |
| --- | --- | --- |
| Labor | BLS가 공표한 비율이라 변환이 필요 없고, 이미 등록된 source ID(`BLS:LNS14000000`)와 파서를 그대로 쓴다. | CPS 표본오차(대략 ±0.2%p). 2025년 10월은 예산 공백으로 조사되지 않아 원기관 값이 없다(NA로 유지). 매년 1월 인구 통제치 변경으로 단절이 생긴다. |
| Monetary Policy | 정책금리 목표범위 안에서 실제 거래되는 대표 금리다. 기존 Treasury 10년물(시장 금리 맥락)과 역할이 겹치지 않는다. | 수준만으로는 완화·긴축 판단이 불가능하다(중립금리 기준 없음). 다음 영업일에 공표된다. 이 series를 포함해 Fed DDP 경로는 축소 예고가 있어(“Build Your Package” 제거 공지) 공식 txt 파일 경로가 바뀌면 NA가 된다. |
| Liquidity | 연준 대차대조표 규모는 가장 직접적인 공식 유동성 공급 지표이고, 주간 수요일 잔액은 평균값과 달리 시점이 명확하다. | 총자산은 TGA·역레포 같은 흡수 요인을 빼지 않으므로 “순유동성”이 아니다. DDP 고유 mnemonic은 활성화 때 원기관 metadata에서 description(“Total assets (less eliminations from consolidation): Wednesday level”)으로 대조한다. 맞지 않으면 `SCHEMA_MISMATCH`로 중단한다. |
| Credit | 상업은행 신용 총량은 실물 신용 공급을 공식 집계로 바로 보여 준다. 월간 SA 수준이라 계절성 없이 전년 대비 비교가 된다. | 회사채 spread·대출기준(SLOOS)과 다른 개념이며 신용 위험 가격을 반영하지 않는다. 계절요인 연례 갱신과 벤치마크 수정으로 과거 값이 바뀐다. DDP mnemonic은 Liquidity와 같은 방식으로 활성화 때 대조한다. |
| Fiscal | 공식 월간 결산이고 FiscalData는 키 없이 재배포를 허용한다. 12개월 합계는 월별 지급일 이동을 줄인다. | GDP 대비 비율이 아니다(정규화는 별도 결정). 지급일이 주말이면 다른 달로 옮겨져 월별 값이 흔들린다. 회계연도 행·소계 행이 섞여 있어 월 행만 고르는 필터를 활성화 때 dictionary로 확정해야 한다. |
| FX | 무역가중 명목 달러지수는 Fed가 공식 산출하는 대표 달러 지표이며 통화쌍 하나를 고르는 자의성이 없다. | 가격 성격의 지수라서 현재 공개 화면에서 FX는 제외된다(`PUBLIC_FX_EXCLUDED`). 이 series를 승인해도 **공개 승인은 아니다**. 공개 여부는 따로 결정해야 하며, 그 전에는 Actions 메모리에서만 쓰고 공개하지 않는다. 2006-05~2009-01 주간 H.10 발행 중단 구간이 있다. |

## 3. 활성화 때 공통 확인 (승인 후 구현 PR에서)

- 수집은 GitHub Actions에서만 한다. 원본 응답은 runner의 임시 디렉터리에만 두고, 공개 JSON에는 값·기간·series ID·수집 시각·sha256·상태·`v0 · UNCALIBRATED`만 넣는다.
- 각 series의 식별자·단위·SA/NSA를 원기관 metadata와 대조한다. 맞지 않으면 `SCHEMA_MISMATCH`로 NA를 낸다.
- 비교 기준 시점(12개월 전 등)의 값이 없으면 NA다. 보간하거나 가장 가까운 값으로 대체하지 않는다.
- 키가 필요한 경로는 없다. BLS v1과 FiscalData, Fed 공식 파일은 키 없이 읽을 수 있다. BLS v1의 하루 요청 한도에 걸리면 그날은 NA가 된다.

## 4. 한 번에 승인할 목록

아래 6줄을 한 번에 승인하면 **입력 series와 v0 변환만** 확정된다. 축별 상태 임계값, 6상태 규칙, 8축 국면 대응표는 포함되지 않으며 계속 `NOT_AVAILABLE`이다. 모든 값은 `v0 기본값 · UNCALIBRATED`로 표시되고 나중에 바꿀 수 있다.

| # | 축 | 승인할 series (원기관 · ID) | 빈도 · 조정 | v0 변환 | 비고 |
| --- | --- | --- | --- | --- | --- |
| 1 | Labor | BLS `LNS14000000` 실업률 | 월 · SA | %÷100 | 기존 파서 재사용 |
| 2 | Monetary Policy | Fed H.15 `RIFSPFF_N.B` 연방기금 실효금리 | 영업일 · NSA | 월평균 ÷100, 빠진 영업일이 있으면 NA | 산출 원기관 FRBNY |
| 3 | Liquidity | Fed H.4.1 Table 5 Total assets, Wednesday level | 주 · NSA | 52주 전 대비 변화율 | 순유동성 아님 |
| 4 | Credit | Fed H.8 Table 2 Bank credit, all commercial banks | 월 · SA | 12개월 전 대비 변화율 | spread 아님 |
| 5 | Fiscal | Treasury MTS Table 1 `current_month_dfct_sur_amt` | 월 · NSA | 최근 12개월 합계 | GDP 대비 아님 |
| 6 | FX | Fed H.10 `JRXWTFB_N.M` 명목 광의 달러지수 | 월 · NSA | 12개월 전 대비 변화율 | 공개는 별도 결정, 그 전에는 비공개 |

승인 방식 예시: "1~6 모두 승인" 또는 "1·2·5만 승인, 6은 보류".

## 5. 2026-10-11 결정 반영 — 원자료 표시 구현

사용자 결정: "매크로 나머지 6축: 원자료 표시만 승인, 국면 판정은 보류."

- 구현: `macro/raw_axes_v0.py`(파서·변환), `providers/macro_v0_collection.py`(수집), `product/public_engine_screens.py`의 `macro-screen.json` → `data.raw_axes_v0` 블록, `web_assets/public-screens.js`(검증·S09 공개 매크로 카드), `web_assets/screen-detail.js`(S09 series 안내).
- 표시 내용: 축마다 값, 기간(비교 기준 기간), 발표값·기준값, series ID, 기관, 변환, 수집 시각, 원본 sha256, `LIVE`/`STALE`/`NOT_AVAILABLE`와 이유 코드. 표시 문구 `v0 · 원자료 표시 · 국면 판정 보류`.
- 없는 것: 축별 상태, 임계값, 점수, Direction·Momentum·Surprise·Stress·Confidence, 국면. 블록의 국면은 항상 `NOT_AVAILABLE`(`REGIME_JUDGEMENT_DEFERRED`)이다. 기존 Growth·Inflation 엔진 블록은 바뀌지 않는다.
- 결측: 채우지 않고 0을 넣지 않는다. 비교 기준(12개월 전·52주 전·12개월 창)이 하나라도 없으면 `BASE_PERIOD_MISSING`, H.15 월에 평일 행이 빠지면 `INCOMPLETE_PERIOD`.
- 수집: GitHub Actions의 기존 SEC daily 단계에서 `public_screens_pipeline.py --live --macro-v0`가 함께 수집한다. 워크플로·secret 변경은 필요 없다(키 없는 경로만 사용). BLS는 `CUUR0000SA0`과 `LNS14000000`을 **한 요청**으로 받는다.

| 축 | 실제 요청 (키 없음) | 선택 규칙 | 변환 | 확인 상태 |
| --- | --- | --- | --- | --- |
| Labor | BLS API v1 POST, `seriesid=[CUUR0000SA0, LNS14000000]` | `LNS14000000` 최신 발표월 | % ÷ 100 | 기존 파서·series ID 확인됨 |
| Monetary Policy | ① 공식 안내 파일 `https://www.federalreserve.gov/releases/h15/data/Business_day/H15_FF_O.txt`에서 DDP 링크의 `series` 해시 1개를 읽고 ② `https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&series=<해시>&from=01/01/<전년>&filetype=csv&label=include&layout=seriescolumn` | Unique Identifier가 정확히 `H15/H15/RIFSPFF_N.B`, 단위 Percent, multiplier 1 | 완결된 최신 월(진행 중인 달 제외)의 영업일 평균 ÷ 100. `ND`(휴일)는 관측에서 제외, 평일 행이 없으면 NA | **첫 실행에서 확인**: 안내 파일이 DDP 링크를 정확히 1개 담는지, CSV가 휴일을 `ND` 행으로 주는지 |
| Liquidity | `Output.aspx?rel=H41&series=efce2c1a8744855f2623889dffb2b39a&filetype=csv&label=include&layout=seriescolumn` | 식별자 `H41/H41/…` 중 설명에 "total assets", "less eliminations from consolidation", "wednesday level"이 모두 있는 열 정확히 1개, 날짜는 수요일 | 수요일 잔액 ÷ 364일 전 잔액 − 1 | **미확인 후보 해시**. 이 패키지에 해당 series가 없으면 `SERIES_NOT_FOUND`. 맞는 패키지 해시는 `Choose.aspx?rel=H41`에서 골라 `FED_DDP_PACKAGES`를 고친다 |
| Credit | `Output.aspx?rel=H8&series=9a538c893f62322f942501e38030aed5&filetype=csv&label=include&layout=seriescolumn&type=package` | 식별자 `H8/H8/…` 중 설명에 "bank credit", "all commercial banks", "seasonally adjusted"가 있고 "not seasonally adjusted"가 없는 열 정확히 1개, 월 기간 | 월 수준 ÷ 12개월 전 − 1 | **미확인 후보 해시**. Liquidity와 같은 방식으로 첫 실행에서 확인 |
| Fiscal | `https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/mts/mts_table_1?filter=record_date:gte:<2년 전>-01-01&sort=record_date&format=json&page[number]=1&page[size]=10000` | 각 월 보고서(`record_date`)에서 그 달 이름의 행 1개. 전 회계연도 같은 달 행이 함께 있으면 `parent_id` 상위 행의 "FY yyyy"가 `record_fiscal_year`와 같은 행만. 여러 페이지면 NA | 최신 12개월 연속 합계, 단위는 발표 그대로(`CURRENCY_AS_PUBLISHED`) | **첫 실행에서 확인**: 월 행의 `classification_desc` 표기와 상위 행 구조. 맞지 않으면 `SCHEMA_MISMATCH` |
| FX | 수집하지 않음 | — | — | 공개 JSON에서 항상 `NOT_AVAILABLE`(`PUBLIC_FX_EXCLUDED`) |

- Fed DDP는 "Build Your Package" 제거와 장차 종료가 예고되어 있다. 경로가 바뀌면 NA가 되며 FRED로 대체하지 않는다.
- 허용 URL: 수집기는 위 고정 호스트·경로만 요청하고, DDP는 `rel`∈{H15,H41,H8}·32자리 16진 `series`·`filetype=csv`만, FiscalData는 `filter/sort/format/page[...]` 키만 허용한다(`macro_v0_collection._query_allowed`). 리디렉트는 거부한다.
- 첫 실행 로그 확인: `MACRO_V0 axis=<축> state=<상태> reasons=<코드>` 줄만 출력된다(URL·값 없음). `SERIES_NOT_FOUND`/`SCHEMA_MISMATCH`가 나오면 해당 행의 확인 항목을 본다.

### FX 공개는 별도 결정이 필요하다

저장소 상시 규칙은 가격과 가격에서 파생한 값을 공개 저장소·Pages·로그에 두지 않는다. 명목 광의 달러지수는 환율(가격)에서 만든 지수라 이 경계와 충돌한다. 그래서 FX는 수집하지도 공개하지도 않고, 공개 JSON의 FX 행은 검증기가 `NOT_AVAILABLE`·`PUBLIC_FX_EXCLUDED`·출처 없음만 허용한다. FX 값을 공개하려면 가격 경계에 대한 명시적인 사용자 결정이 먼저 필요하다.
