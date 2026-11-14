# 금융 555 회계모형별 연구 후보

버전: `financial-555-candidates/0.1.0` / 계약: `financial-555-candidates/1`.

이 등록은 금융 전용 기본값 확정이나 운영 채택이 아니다. 기존 U1/S1·공식 calc 23.1·REIT 임시 일반기업 정책을 변경하지 않는다. 모든 회계모형은 같은 15역할 질문과 역할 예산을 유지한다. 정확한 정의가 없는 역할은 `PREPARING`이며 원값·요소 점수·역할 점수·축·총점·순위에 값을 만들지 않는다. 원시 비율 계산은 최소 비교표본을 선행 조건으로 요구하지 않는다.

`DIRECT`는 완결된 직접 측정 산식, `PROXY`는 역할의 일부만 측정하는 대리 지표, `PREPARING`은 정의 미완결이다. 이는 근거의 VERIFIED 판정과 다른 상태다. 현재 구현은 완결된 원시 산식만 기존 `sector_qgv.calculate_factor`로 실행한다. 정규화·관문·역할 합산은 연결하지 않았으므로 부분 비율을 금융 555 산출·채택으로 세지 않는다.

## 공통 계약과 근거

- 원천과 공식: 기존 `sector_qgv_registry.CATALOG`, `sector_qgv.calculate_factor`, `sector_qgv_held.held_observations`, `financial_v.CONFIG`의 정의·회계기간·귀속·가격 검사를 재사용한다. 이는 시스템의 연구 적용 규칙이며 책이나 기관이 이 555 배점의 성과를 입증했다는 뜻이 아니다.
- 후보 선정: 수익성·자본 완충·성장·가격의 경제적 역할과 회계 적용성을 기준으로 먼저 고정했다. 수익률에 따라 후보를 고르거나 바꾸지 않았다. 보험의 생명/손해보험은 다른 준비금·부채·손해비용 구조를 별도로 검토한다. SIC만으로 하위 사업모형을 확정하지 않는다.
- 축 초기 비중은 금융 상위의 Q40/G15/V45다. Q역할 비중25/20/20/20/15, G와V25/25/20/15/15는 기존555의 초기 역할 예산을 보존한다. 수치 자체는 최적값이 아니다. 준비 중 역할을 뺀 뒤 남은 역할로 완결 모형을 가장하지 않는다.
- 비교집단 연구 정책은 같은 평가일·회계모형·variant·대표 발행사 기준 최소8이다. 은행/보험/브로커/자산운용/모기지REIT/지분형REIT를 표본 확보를 위해 합치지 않는다. 원시 비율에는 비교집단 문턱이 없다. 금융 후보의 상대점수는 아직 미연결이다.
- 같은 역할의 후보는 자동 대체가 아니다. 기본 후보 교체는 고정 설정과 새 결과 버전으로 구분한다. 같은 원입력 계열은 중복 위험을 표시하고 역할 예산을 늘리지 않는다. 공통 ROE수준·BPS성장·B/P는 모두 보통주 자본에 노출되며, ROA개선과 ROA수준도 별개 독립 정보라고 단정하지 않는다.
- 매출/수익 정의, 보통주 귀속, 총액/순액, 통화·단위, 회계기간, 최신 공시 충돌, 공시 가용시각을 검증한다. 결측 자본·우선주·비지배지분·현금흐름을0으로 채우지 않는다. 음수·실제0·결측은 커널의 별도 상태를 보존한다.
- 주당 성장의 역사 기준 검증과 평가일 EPS/가격·BPS/가격의 증권 결합은 별도다. 가격은 같은 평가일·같은 증권·통화·종류주·기업행사 기준이어야 한다. 검증된 TTM EPS를 연간/누적 EPS의 임의 산술로 대체하지 않는다.
- 은행의 CFO를 주주 잉여현금흐름으로 부르지 않는다. 대손·충당·손해비용이 낮다는 이유만으로 이익의 질이 높다고 확정하지 않는다. 공통자본/자산은 CET1/RBC/규제 순자본의 대체가 아니다. REIT CFO·Nareit FFO·AFFO는 다른 정의다.

## 완결된 원시 variant

산식은 기존 커널 연산을 입력 이름으로 펼친 것이다. FY_3Y는 지정된 모든 연간 입력을 보유해야 하며, 성장률의 양수 기초·기말 조건과 각 기간/통화/귀속 검사는 유지한다.

|variant|산식|기간·단위·방향|필수 입력과 범위|
|---|---|---|---|
|`accruals_assets_ttm`|(net_income - cfo) / mean(assets_begin, assets_end)|TTM / decimal / LOWER|net_income (TTM, currency); cfo (TTM, currency); assets_begin (INSTANT, currency); assets_end (INSTANT, currency)|
|`cfo_assets_improvement_3y`|cfo_assets_fy - cfo_assets_fy3|FY_3Y / decimal / HIGHER|cfo_assets_fy (FY, decimal); cfo_assets_fy3 (FY_MINUS_3, decimal)|
|`cfo_assets_ttm`|cfo / mean(assets_begin, assets_end)|TTM / decimal / HIGHER|cfo (TTM, currency); assets_begin (INSTANT, currency); assets_end (INSTANT, currency)|
|`common_bp`|common_bps / price|LATEST_QUARTER / decimal / HIGHER|common_bps (INSTANT, currency/share); price (PRICE, currency/share)|
|`common_bps_cagr_3y`|(common_bps_fy / common_bps_fy3)^(1/3) - 1; positive endpoints; all specified FY inputs required|FY_3Y / decimal / HIGHER|common_bps_fy (FY, currency/share); common_bps_fy1 (FY_MINUS_1, currency/share); common_bps_fy2 (FY_MINUS_2, currency/share); common_bps_fy3 (FY_MINUS_3, currency/share)|
|`common_equity_assets`|common_equity_end / assets_end|LATEST_QUARTER / decimal / HIGHER|common_equity_end (INSTANT, currency); assets_end (INSTANT, currency)|
|`debt_assets`|debt / assets_end|LATEST_QUARTER / decimal / LOWER|debt (INSTANT, currency); assets_end (INSTANT, currency)|
|`ep_ttm_diluted`|eps_ttm_diluted / price|TTM / decimal / HIGHER|eps_ttm_diluted (TTM, currency/share); price (PRICE, currency/share)|
|`eps_diluted_cagr_3y`|(eps_diluted_fy / eps_diluted_fy3)^(1/3) - 1; positive endpoints; all specified FY inputs required|FY_3Y / decimal / HIGHER|eps_diluted_fy (FY, currency/share); eps_diluted_fy1 (FY_MINUS_1, currency/share); eps_diluted_fy2 (FY_MINUS_2, currency/share); eps_diluted_fy3 (FY_MINUS_3, currency/share)|
|`fcf_mcap`|(cfo - capex) / issuer_mcap|TTM / decimal / HIGHER|cfo (TTM, currency); capex (TTM, currency); issuer_mcap (PRICE, currency)|
|`nareit_ffo_mcap`|nareit_ffo / issuer_mcap|TTM / decimal / HIGHER|nareit_ffo (TTM, currency); issuer_mcap (PRICE, currency)|
|`operating_margin_ttm`|operating_income / revenue|TTM / decimal / HIGHER|operating_income (TTM, currency); revenue (TTM, currency)|
|`revenue_cagr_3y`|(revenue_fy / revenue_fy3)^(1/3) - 1; positive endpoints; all specified FY inputs required|FY_3Y / decimal / HIGHER|revenue_fy (FY, currency); revenue_fy1 (FY_MINUS_1, currency); revenue_fy2 (FY_MINUS_2, currency); revenue_fy3 (FY_MINUS_3, currency)|
|`revenue_growth_consistency_3y`|count(positive adjacent FY changes in revenue_fy, revenue_fy1, revenue_fy2, revenue_fy3) / 3|FY_3Y / decimal / HIGHER|revenue_fy (FY, currency); revenue_fy1 (FY_MINUS_1, currency); revenue_fy2 (FY_MINUS_2, currency); revenue_fy3 (FY_MINUS_3, currency)|
|`roa_improvement_3y`|roa_fy - roa_fy3|FY_3Y / decimal / HIGHER|roa_fy (FY, decimal); roa_fy3 (FY_MINUS_3, decimal)|
|`roe_common_ttm`|net_income_common / mean(common_equity_begin, common_equity_end)|TTM / decimal / HIGHER|net_income_common (TTM, currency); common_equity_begin (INSTANT, currency); common_equity_end (INSTANT, currency)|
|`tangible_common_bp`|tangible_common_bps / price|LATEST_QUARTER / decimal / HIGHER|tangible_common_bps (INSTANT, currency/share); price (PRICE, currency/share)|

## 회계모형별 고정 후보표

빈 역할은 모형의 미완결 정의를 표시한다. 사용자 후보는 같은 역할 안의 선택 후보이며 회사마다 자료가 있는 지표를 자동 선택하지 않는다. 필수 입력·귀속·중복 그룹·가중치·제한은 `registry()` 결과에도 존재한다. 생명·손해보험 외 보험 및 하위 유형 미확인은 별도 모델로 유지한다.

### BANK

회계 적용: `BANK`. 상태: `RESEARCH_INCOMPLETE_NOT_DEFAULT`.

|역할(경제적 질문)|예산|기본·사용자 후보|근거 상태와 적용 한계|
|---|---:|---|---|
|q_profitability: 현재 자본 또는 영업기반에서 얼마의 이익을 얻는가|25|`roe_common_ttm`; 선택 후보 `roa_ttm`|DIRECT: ROA는 다른 분모의 선택 후보이며 ROE의 자동 대체가 아님.|
|q_moat_proxy: 수익성이 여러 회계기간에 걸쳐 유지되는가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 수익성 역사·손실 처리·지속성 산식 미완결|
|q_earnings_quality: 보고이익의 현금·추정·위험 인식 근거가 적절한가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 충당·준비금·현금흐름 의미와 이익의 질 산식 미완결|
|q_financial_safety: 사업모형에 맞는 자본·유동성 완충력이 있는가|20|`common_equity_assets`; 선택 후보 없음|PROXY: 장부 자본 완충 대리값; CET1/RBC/규제 순자본·유동성·금리 위험을 입증하지 않음.|
|q_capital_allocation: 주주 자본을 어떻게 배분하고 보전하는가|15|준비 중; 선택 후보 없음|PREPARING: 보통주 배당·실제 매입·자본 유지·희석 기준과 평가 산식 미완결|
|g_revenue_growth: 일관된 사업 수익기반이 얼마나 성장했는가|25|준비 중; 선택 후보 없음|PREPARING: 모형별 순이자·보험료·수수료·투자 수익의 동일 정의 연결 필요|
|g_per_share_growth: 동일 보통주 기준의 주당 성과가 성장했는가|25|`common_bps_cagr_3y`; 선택 후보 없음|PROXY: 분모와 배당·환매 영향을 별도 확인; 이익·FCF 성장과 동일하지 않음.|
|g_growth_efficiency: 성장과 함께 수익 창출 효율이 개선됐는가|20|`roa_improvement_3y`; 선택 후보 없음|PROXY: 수익성 변화 대리값; ROIC 또는 추가 자본의 인과 수익으로 부르지 않음.|
|g_consistency: 성장이 기간별로 얼마나 일관됐는가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 성장 수익기반과 전체 비교기간 정의 필요|
|g_recent_acceleration: 최근 성장과 장기 성장의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 TTM/FY 성장 수익기반의 동일 정의 연결 필요|
|v_earnings_yield: 가격 대비 적격 회계이익 또는 사업모형 이익은 얼마인가|25|`ep_ttm_diluted`; 선택 후보 `ep_fy_diluted`|DIRECT: TTM·연간 variant를 혼합하거나 순이익/현재 주식수로 EPS를 만들지 않음.|
|v_fcf_yield: 가격 대비 주주에게 귀속될 현금흐름은 얼마인가|25|준비 중; 선택 후보 없음|PREPARING: 금융 CFO를 배당가능 현금흐름으로 간주하지 않음; 모형별 정의 미완결|
|v_vs_industry: 동일 정의·회계모형의 동종기업 대비 가격은 어떤가|20|`tangible_common_bp`; 선택 후보 `common_bp`|PROXY: 원시 B/P 계열만 계산; 동일 모형·정의의 비교집단과 정규화 연결 전 상대가치 점수 없음.|
|v_vs_own_history: 동일 기준의 자기 과거 가치 대비 현재 가격은 어떤가|15|준비 중; 선택 후보 없음|PREPARING: 같은 증권·분할 기준·지표 정의의 적격 가격 역사 필요|
|v_expectation_check: 가격이 요구하는 성장과 적격 실적의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 주주 현금흐름·자본 요구·성장 기대 산식 미완결|

### LIFE_INSURANCE

회계 적용: `INSURANCE`. 상태: `RESEARCH_INCOMPLETE_NOT_DEFAULT`.

|역할(경제적 질문)|예산|기본·사용자 후보|근거 상태와 적용 한계|
|---|---:|---|---|
|q_profitability: 현재 자본 또는 영업기반에서 얼마의 이익을 얻는가|25|`roe_common_ttm`; 선택 후보 `roa_ttm`|DIRECT: ROA는 다른 분모의 선택 후보이며 ROE의 자동 대체가 아님.|
|q_moat_proxy: 수익성이 여러 회계기간에 걸쳐 유지되는가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 수익성 역사·손실 처리·지속성 산식 미완결|
|q_earnings_quality: 보고이익의 현금·추정·위험 인식 근거가 적절한가|20|준비 중; 선택 후보 없음|PREPARING: 보험부채·보증·할인·해약·경험차의 모형별 검증 정의 준비 중|
|q_financial_safety: 사업모형에 맞는 자본·유동성 완충력이 있는가|20|`common_equity_assets`; 선택 후보 없음|PROXY: 장부 자본 완충 대리값; CET1/RBC/규제 순자본·유동성·금리 위험을 입증하지 않음.|
|q_capital_allocation: 주주 자본을 어떻게 배분하고 보전하는가|15|준비 중; 선택 후보 없음|PREPARING: 보통주 배당·실제 매입·자본 유지·희석 기준과 평가 산식 미완결|
|g_revenue_growth: 일관된 사업 수익기반이 얼마나 성장했는가|25|준비 중; 선택 후보 없음|PREPARING: 모형별 순이자·보험료·수수료·투자 수익의 동일 정의 연결 필요|
|g_per_share_growth: 동일 보통주 기준의 주당 성과가 성장했는가|25|`common_bps_cagr_3y`; 선택 후보 없음|PROXY: 분모와 배당·환매 영향을 별도 확인; 이익·FCF 성장과 동일하지 않음.|
|g_growth_efficiency: 성장과 함께 수익 창출 효율이 개선됐는가|20|`roa_improvement_3y`; 선택 후보 없음|PROXY: 수익성 변화 대리값; ROIC 또는 추가 자본의 인과 수익으로 부르지 않음.|
|g_consistency: 성장이 기간별로 얼마나 일관됐는가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 성장 수익기반과 전체 비교기간 정의 필요|
|g_recent_acceleration: 최근 성장과 장기 성장의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 TTM/FY 성장 수익기반의 동일 정의 연결 필요|
|v_earnings_yield: 가격 대비 적격 회계이익 또는 사업모형 이익은 얼마인가|25|`ep_ttm_diluted`; 선택 후보 `ep_fy_diluted`|DIRECT: TTM·연간 variant를 혼합하거나 순이익/현재 주식수로 EPS를 만들지 않음.|
|v_fcf_yield: 가격 대비 주주에게 귀속될 현금흐름은 얼마인가|25|준비 중; 선택 후보 없음|PREPARING: 금융 CFO를 배당가능 현금흐름으로 간주하지 않음; 모형별 정의 미완결|
|v_vs_industry: 동일 정의·회계모형의 동종기업 대비 가격은 어떤가|20|`common_bp`; 선택 후보 `tangible_common_bp`|PROXY: 원시 B/P 계열만 계산; 동일 모형·정의의 비교집단과 정규화 연결 전 상대가치 점수 없음.|
|v_vs_own_history: 동일 기준의 자기 과거 가치 대비 현재 가격은 어떤가|15|준비 중; 선택 후보 없음|PREPARING: 같은 증권·분할 기준·지표 정의의 적격 가격 역사 필요|
|v_expectation_check: 가격이 요구하는 성장과 적격 실적의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 주주 현금흐름·자본 요구·성장 기대 산식 미완결|

### PROPERTY_CASUALTY_INSURANCE

회계 적용: `INSURANCE`. 상태: `RESEARCH_INCOMPLETE_NOT_DEFAULT`.

|역할(경제적 질문)|예산|기본·사용자 후보|근거 상태와 적용 한계|
|---|---:|---|---|
|q_profitability: 현재 자본 또는 영업기반에서 얼마의 이익을 얻는가|25|`roe_common_ttm`; 선택 후보 `roa_ttm`|DIRECT: ROA는 다른 분모의 선택 후보이며 ROE의 자동 대체가 아님.|
|q_moat_proxy: 수익성이 여러 회계기간에 걸쳐 유지되는가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 수익성 역사·손실 처리·지속성 산식 미완결|
|q_earnings_quality: 보고이익의 현금·추정·위험 인식 근거가 적절한가|20|준비 중; 선택 후보 없음|PREPARING: 합산비율·손해준비금 발전은 별도 지표; 순경과보험료·손해액·사업비의 총액/순액·재보험 범위 정의 준비 중. 낮은 대손/손해비용만으로 고품질 판정 금지.|
|q_financial_safety: 사업모형에 맞는 자본·유동성 완충력이 있는가|20|`common_equity_assets`; 선택 후보 없음|PROXY: 장부 자본 완충 대리값; CET1/RBC/규제 순자본·유동성·금리 위험을 입증하지 않음.|
|q_capital_allocation: 주주 자본을 어떻게 배분하고 보전하는가|15|준비 중; 선택 후보 없음|PREPARING: 보통주 배당·실제 매입·자본 유지·희석 기준과 평가 산식 미완결|
|g_revenue_growth: 일관된 사업 수익기반이 얼마나 성장했는가|25|준비 중; 선택 후보 없음|PREPARING: 모형별 순이자·보험료·수수료·투자 수익의 동일 정의 연결 필요|
|g_per_share_growth: 동일 보통주 기준의 주당 성과가 성장했는가|25|`common_bps_cagr_3y`; 선택 후보 없음|PROXY: 분모와 배당·환매 영향을 별도 확인; 이익·FCF 성장과 동일하지 않음.|
|g_growth_efficiency: 성장과 함께 수익 창출 효율이 개선됐는가|20|`roa_improvement_3y`; 선택 후보 없음|PROXY: 수익성 변화 대리값; ROIC 또는 추가 자본의 인과 수익으로 부르지 않음.|
|g_consistency: 성장이 기간별로 얼마나 일관됐는가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 성장 수익기반과 전체 비교기간 정의 필요|
|g_recent_acceleration: 최근 성장과 장기 성장의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 TTM/FY 성장 수익기반의 동일 정의 연결 필요|
|v_earnings_yield: 가격 대비 적격 회계이익 또는 사업모형 이익은 얼마인가|25|`ep_ttm_diluted`; 선택 후보 `ep_fy_diluted`|DIRECT: TTM·연간 variant를 혼합하거나 순이익/현재 주식수로 EPS를 만들지 않음.|
|v_fcf_yield: 가격 대비 주주에게 귀속될 현금흐름은 얼마인가|25|준비 중; 선택 후보 없음|PREPARING: 금융 CFO를 배당가능 현금흐름으로 간주하지 않음; 모형별 정의 미완결|
|v_vs_industry: 동일 정의·회계모형의 동종기업 대비 가격은 어떤가|20|`common_bp`; 선택 후보 `tangible_common_bp`|PROXY: 원시 B/P 계열만 계산; 동일 모형·정의의 비교집단과 정규화 연결 전 상대가치 점수 없음.|
|v_vs_own_history: 동일 기준의 자기 과거 가치 대비 현재 가격은 어떤가|15|준비 중; 선택 후보 없음|PREPARING: 같은 증권·분할 기준·지표 정의의 적격 가격 역사 필요|
|v_expectation_check: 가격이 요구하는 성장과 적격 실적의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 주주 현금흐름·자본 요구·성장 기대 산식 미완결|

### OTHER_INSURANCE

회계 적용: `INSURANCE`. 상태: `RESEARCH_INCOMPLETE_NOT_DEFAULT`.

|역할(경제적 질문)|예산|기본·사용자 후보|근거 상태와 적용 한계|
|---|---:|---|---|
|q_profitability: 현재 자본 또는 영업기반에서 얼마의 이익을 얻는가|25|`roe_common_ttm`; 선택 후보 `roa_ttm`|DIRECT: ROA는 다른 분모의 선택 후보이며 ROE의 자동 대체가 아님.|
|q_moat_proxy: 수익성이 여러 회계기간에 걸쳐 유지되는가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 수익성 역사·손실 처리·지속성 산식 미완결|
|q_earnings_quality: 보고이익의 현금·추정·위험 인식 근거가 적절한가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 충당·준비금·현금흐름 의미와 이익의 질 산식 미완결|
|q_financial_safety: 사업모형에 맞는 자본·유동성 완충력이 있는가|20|`common_equity_assets`; 선택 후보 없음|PROXY: 장부 자본 완충 대리값; CET1/RBC/규제 순자본·유동성·금리 위험을 입증하지 않음.|
|q_capital_allocation: 주주 자본을 어떻게 배분하고 보전하는가|15|준비 중; 선택 후보 없음|PREPARING: 보통주 배당·실제 매입·자본 유지·희석 기준과 평가 산식 미완결|
|g_revenue_growth: 일관된 사업 수익기반이 얼마나 성장했는가|25|준비 중; 선택 후보 없음|PREPARING: 모형별 순이자·보험료·수수료·투자 수익의 동일 정의 연결 필요|
|g_per_share_growth: 동일 보통주 기준의 주당 성과가 성장했는가|25|`common_bps_cagr_3y`; 선택 후보 없음|PROXY: 분모와 배당·환매 영향을 별도 확인; 이익·FCF 성장과 동일하지 않음.|
|g_growth_efficiency: 성장과 함께 수익 창출 효율이 개선됐는가|20|`roa_improvement_3y`; 선택 후보 없음|PROXY: 수익성 변화 대리값; ROIC 또는 추가 자본의 인과 수익으로 부르지 않음.|
|g_consistency: 성장이 기간별로 얼마나 일관됐는가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 성장 수익기반과 전체 비교기간 정의 필요|
|g_recent_acceleration: 최근 성장과 장기 성장의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 TTM/FY 성장 수익기반의 동일 정의 연결 필요|
|v_earnings_yield: 가격 대비 적격 회계이익 또는 사업모형 이익은 얼마인가|25|`ep_ttm_diluted`; 선택 후보 `ep_fy_diluted`|DIRECT: TTM·연간 variant를 혼합하거나 순이익/현재 주식수로 EPS를 만들지 않음.|
|v_fcf_yield: 가격 대비 주주에게 귀속될 현금흐름은 얼마인가|25|준비 중; 선택 후보 없음|PREPARING: 금융 CFO를 배당가능 현금흐름으로 간주하지 않음; 모형별 정의 미완결|
|v_vs_industry: 동일 정의·회계모형의 동종기업 대비 가격은 어떤가|20|`common_bp`; 선택 후보 `tangible_common_bp`|PROXY: 원시 B/P 계열만 계산; 동일 모형·정의의 비교집단과 정규화 연결 전 상대가치 점수 없음.|
|v_vs_own_history: 동일 기준의 자기 과거 가치 대비 현재 가격은 어떤가|15|준비 중; 선택 후보 없음|PREPARING: 같은 증권·분할 기준·지표 정의의 적격 가격 역사 필요|
|v_expectation_check: 가격이 요구하는 성장과 적격 실적의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 주주 현금흐름·자본 요구·성장 기대 산식 미완결|

### INSURANCE_UNSPECIFIED

회계 적용: `INSURANCE`. 상태: `RESEARCH_INCOMPLETE_NOT_DEFAULT`.

|역할(경제적 질문)|예산|기본·사용자 후보|근거 상태와 적용 한계|
|---|---:|---|---|
|q_profitability: 현재 자본 또는 영업기반에서 얼마의 이익을 얻는가|25|`roe_common_ttm`; 선택 후보 `roa_ttm`|DIRECT: ROA는 다른 분모의 선택 후보이며 ROE의 자동 대체가 아님.|
|q_moat_proxy: 수익성이 여러 회계기간에 걸쳐 유지되는가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 수익성 역사·손실 처리·지속성 산식 미완결|
|q_earnings_quality: 보고이익의 현금·추정·위험 인식 근거가 적절한가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 충당·준비금·현금흐름 의미와 이익의 질 산식 미완결|
|q_financial_safety: 사업모형에 맞는 자본·유동성 완충력이 있는가|20|`common_equity_assets`; 선택 후보 없음|PROXY: 장부 자본 완충 대리값; CET1/RBC/규제 순자본·유동성·금리 위험을 입증하지 않음.|
|q_capital_allocation: 주주 자본을 어떻게 배분하고 보전하는가|15|준비 중; 선택 후보 없음|PREPARING: 보통주 배당·실제 매입·자본 유지·희석 기준과 평가 산식 미완결|
|g_revenue_growth: 일관된 사업 수익기반이 얼마나 성장했는가|25|준비 중; 선택 후보 없음|PREPARING: 모형별 순이자·보험료·수수료·투자 수익의 동일 정의 연결 필요|
|g_per_share_growth: 동일 보통주 기준의 주당 성과가 성장했는가|25|`common_bps_cagr_3y`; 선택 후보 없음|PROXY: 분모와 배당·환매 영향을 별도 확인; 이익·FCF 성장과 동일하지 않음.|
|g_growth_efficiency: 성장과 함께 수익 창출 효율이 개선됐는가|20|`roa_improvement_3y`; 선택 후보 없음|PROXY: 수익성 변화 대리값; ROIC 또는 추가 자본의 인과 수익으로 부르지 않음.|
|g_consistency: 성장이 기간별로 얼마나 일관됐는가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 성장 수익기반과 전체 비교기간 정의 필요|
|g_recent_acceleration: 최근 성장과 장기 성장의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 TTM/FY 성장 수익기반의 동일 정의 연결 필요|
|v_earnings_yield: 가격 대비 적격 회계이익 또는 사업모형 이익은 얼마인가|25|`ep_ttm_diluted`; 선택 후보 `ep_fy_diluted`|DIRECT: TTM·연간 variant를 혼합하거나 순이익/현재 주식수로 EPS를 만들지 않음.|
|v_fcf_yield: 가격 대비 주주에게 귀속될 현금흐름은 얼마인가|25|준비 중; 선택 후보 없음|PREPARING: 금융 CFO를 배당가능 현금흐름으로 간주하지 않음; 모형별 정의 미완결|
|v_vs_industry: 동일 정의·회계모형의 동종기업 대비 가격은 어떤가|20|`common_bp`; 선택 후보 `tangible_common_bp`|PROXY: 원시 B/P 계열만 계산; 동일 모형·정의의 비교집단과 정규화 연결 전 상대가치 점수 없음.|
|v_vs_own_history: 동일 기준의 자기 과거 가치 대비 현재 가격은 어떤가|15|준비 중; 선택 후보 없음|PREPARING: 같은 증권·분할 기준·지표 정의의 적격 가격 역사 필요|
|v_expectation_check: 가격이 요구하는 성장과 적격 실적의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 주주 현금흐름·자본 요구·성장 기대 산식 미완결|

### BROKER

회계 적용: `BROKER`. 상태: `RESEARCH_INCOMPLETE_NOT_DEFAULT`.

|역할(경제적 질문)|예산|기본·사용자 후보|근거 상태와 적용 한계|
|---|---:|---|---|
|q_profitability: 현재 자본 또는 영업기반에서 얼마의 이익을 얻는가|25|`roe_common_ttm`; 선택 후보 `roa_ttm`|DIRECT: ROA는 다른 분모의 선택 후보이며 ROE의 자동 대체가 아님.|
|q_moat_proxy: 수익성이 여러 회계기간에 걸쳐 유지되는가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 수익성 역사·손실 처리·지속성 산식 미완결|
|q_earnings_quality: 보고이익의 현금·추정·위험 인식 근거가 적절한가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 충당·준비금·현금흐름 의미와 이익의 질 산식 미완결|
|q_financial_safety: 사업모형에 맞는 자본·유동성 완충력이 있는가|20|`common_equity_assets`; 선택 후보 없음|PROXY: 장부 자본 완충 대리값; CET1/RBC/규제 순자본·유동성·금리 위험을 입증하지 않음.|
|q_capital_allocation: 주주 자본을 어떻게 배분하고 보전하는가|15|준비 중; 선택 후보 없음|PREPARING: 보통주 배당·실제 매입·자본 유지·희석 기준과 평가 산식 미완결|
|g_revenue_growth: 일관된 사업 수익기반이 얼마나 성장했는가|25|준비 중; 선택 후보 없음|PREPARING: 모형별 순이자·보험료·수수료·투자 수익의 동일 정의 연결 필요|
|g_per_share_growth: 동일 보통주 기준의 주당 성과가 성장했는가|25|`common_bps_cagr_3y`; 선택 후보 없음|PROXY: 분모와 배당·환매 영향을 별도 확인; 이익·FCF 성장과 동일하지 않음.|
|g_growth_efficiency: 성장과 함께 수익 창출 효율이 개선됐는가|20|`roa_improvement_3y`; 선택 후보 없음|PROXY: 수익성 변화 대리값; ROIC 또는 추가 자본의 인과 수익으로 부르지 않음.|
|g_consistency: 성장이 기간별로 얼마나 일관됐는가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 성장 수익기반과 전체 비교기간 정의 필요|
|g_recent_acceleration: 최근 성장과 장기 성장의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 TTM/FY 성장 수익기반의 동일 정의 연결 필요|
|v_earnings_yield: 가격 대비 적격 회계이익 또는 사업모형 이익은 얼마인가|25|`ep_ttm_diluted`; 선택 후보 `ep_fy_diluted`|DIRECT: TTM·연간 variant를 혼합하거나 순이익/현재 주식수로 EPS를 만들지 않음.|
|v_fcf_yield: 가격 대비 주주에게 귀속될 현금흐름은 얼마인가|25|준비 중; 선택 후보 없음|PREPARING: 금융 CFO를 배당가능 현금흐름으로 간주하지 않음; 모형별 정의 미완결|
|v_vs_industry: 동일 정의·회계모형의 동종기업 대비 가격은 어떤가|20|`common_bp`; 선택 후보 `tangible_common_bp`|PROXY: 원시 B/P 계열만 계산; 동일 모형·정의의 비교집단과 정규화 연결 전 상대가치 점수 없음.|
|v_vs_own_history: 동일 기준의 자기 과거 가치 대비 현재 가격은 어떤가|15|준비 중; 선택 후보 없음|PREPARING: 같은 증권·분할 기준·지표 정의의 적격 가격 역사 필요|
|v_expectation_check: 가격이 요구하는 성장과 적격 실적의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 주주 현금흐름·자본 요구·성장 기대 산식 미완결|

### ASSET_MANAGER

회계 적용: `ASSET_MANAGER`. 상태: `RESEARCH_INCOMPLETE_NOT_DEFAULT`.

|역할(경제적 질문)|예산|기본·사용자 후보|근거 상태와 적용 한계|
|---|---:|---|---|
|q_profitability: 현재 자본 또는 영업기반에서 얼마의 이익을 얻는가|25|`operating_margin_ttm`; 선택 후보 없음|DIRECT: 수수료 사업 회계모형이 확인된 자산운용에 한정; 브로커·자기계정 투자·보험으로 자동 확장하지 않음.|
|q_moat_proxy: 수익성이 여러 회계기간에 걸쳐 유지되는가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 수익성 역사·손실 처리·지속성 산식 미완결|
|q_earnings_quality: 보고이익의 현금·추정·위험 인식 근거가 적절한가|20|`accruals_assets_ttm`; 선택 후보 없음|PROXY: 수수료 사업 회계모형이 확인된 자산운용에 한정; 브로커·자기계정 투자·보험으로 자동 확장하지 않음.|
|q_financial_safety: 사업모형에 맞는 자본·유동성 완충력이 있는가|20|`debt_assets`; 선택 후보 없음|PROXY: 수수료 사업 회계모형이 확인된 자산운용에 한정; 브로커·자기계정 투자·보험으로 자동 확장하지 않음.|
|q_capital_allocation: 주주 자본을 어떻게 배분하고 보전하는가|15|준비 중; 선택 후보 없음|PREPARING: 보통주 배당·실제 매입·자본 유지·희석 기준과 평가 산식 미완결|
|g_revenue_growth: 일관된 사업 수익기반이 얼마나 성장했는가|25|`revenue_cagr_3y`; 선택 후보 없음|DIRECT: 수수료 사업 회계모형이 확인된 자산운용에 한정; 브로커·자기계정 투자·보험으로 자동 확장하지 않음.|
|g_per_share_growth: 동일 보통주 기준의 주당 성과가 성장했는가|25|`eps_diluted_cagr_3y`; 선택 후보 없음|DIRECT: 수수료 사업 회계모형이 확인된 자산운용에 한정; 브로커·자기계정 투자·보험으로 자동 확장하지 않음.|
|g_growth_efficiency: 성장과 함께 수익 창출 효율이 개선됐는가|20|`roa_improvement_3y`; 선택 후보 없음|PROXY: 수수료 사업 회계모형이 확인된 자산운용에 한정; 브로커·자기계정 투자·보험으로 자동 확장하지 않음.|
|g_consistency: 성장이 기간별로 얼마나 일관됐는가|15|`revenue_growth_consistency_3y`; 선택 후보 없음|DIRECT: 수수료 사업 회계모형이 확인된 자산운용에 한정; 브로커·자기계정 투자·보험으로 자동 확장하지 않음.|
|g_recent_acceleration: 최근 성장과 장기 성장의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 TTM/FY 성장 수익기반의 동일 정의 연결 필요|
|v_earnings_yield: 가격 대비 적격 회계이익 또는 사업모형 이익은 얼마인가|25|`ep_ttm_diluted`; 선택 후보 없음|DIRECT: 수수료 사업 회계모형이 확인된 자산운용에 한정; 브로커·자기계정 투자·보험으로 자동 확장하지 않음.|
|v_fcf_yield: 가격 대비 주주에게 귀속될 현금흐름은 얼마인가|25|`fcf_mcap`; 선택 후보 없음|PROXY: 수수료 사업 회계모형이 확인된 자산운용에 한정; 브로커·자기계정 투자·보험으로 자동 확장하지 않음.|
|v_vs_industry: 동일 정의·회계모형의 동종기업 대비 가격은 어떤가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 정확한 산식·귀속·입력 계약 미완결|
|v_vs_own_history: 동일 기준의 자기 과거 가치 대비 현재 가격은 어떤가|15|준비 중; 선택 후보 없음|PREPARING: 같은 증권·분할 기준·지표 정의의 적격 가격 역사 필요|
|v_expectation_check: 가격이 요구하는 성장과 적격 실적의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 주주 현금흐름·자본 요구·성장 기대 산식 미완결|

### MORTGAGE_REIT

회계 적용: `MORTGAGE_REIT`. 상태: `RESEARCH_INCOMPLETE_NOT_DEFAULT`.

|역할(경제적 질문)|예산|기본·사용자 후보|근거 상태와 적용 한계|
|---|---:|---|---|
|q_profitability: 현재 자본 또는 영업기반에서 얼마의 이익을 얻는가|25|`roe_common_ttm`; 선택 후보 `roa_ttm`|DIRECT: ROA는 다른 분모의 선택 후보이며 ROE의 자동 대체가 아님.|
|q_moat_proxy: 수익성이 여러 회계기간에 걸쳐 유지되는가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 수익성 역사·손실 처리·지속성 산식 미완결|
|q_earnings_quality: 보고이익의 현금·추정·위험 인식 근거가 적절한가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 충당·준비금·현금흐름 의미와 이익의 질 산식 미완결|
|q_financial_safety: 사업모형에 맞는 자본·유동성 완충력이 있는가|20|`common_equity_assets`; 선택 후보 없음|PROXY: 장부 자본 완충 대리값; CET1/RBC/규제 순자본·유동성·금리 위험을 입증하지 않음. 담보·repo·헤지·듀레이션/금리 위험은 별도 결손.|
|q_capital_allocation: 주주 자본을 어떻게 배분하고 보전하는가|15|준비 중; 선택 후보 없음|PREPARING: 보통주 배당·실제 매입·자본 유지·희석 기준과 평가 산식 미완결|
|g_revenue_growth: 일관된 사업 수익기반이 얼마나 성장했는가|25|준비 중; 선택 후보 없음|PREPARING: 모형별 순이자·보험료·수수료·투자 수익의 동일 정의 연결 필요|
|g_per_share_growth: 동일 보통주 기준의 주당 성과가 성장했는가|25|`common_bps_cagr_3y`; 선택 후보 없음|PROXY: 분모와 배당·환매 영향을 별도 확인; 이익·FCF 성장과 동일하지 않음.|
|g_growth_efficiency: 성장과 함께 수익 창출 효율이 개선됐는가|20|`roa_improvement_3y`; 선택 후보 없음|PROXY: 수익성 변화 대리값; ROIC 또는 추가 자본의 인과 수익으로 부르지 않음.|
|g_consistency: 성장이 기간별로 얼마나 일관됐는가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 성장 수익기반과 전체 비교기간 정의 필요|
|g_recent_acceleration: 최근 성장과 장기 성장의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 TTM/FY 성장 수익기반의 동일 정의 연결 필요|
|v_earnings_yield: 가격 대비 적격 회계이익 또는 사업모형 이익은 얼마인가|25|`ep_ttm_diluted`; 선택 후보 `ep_fy_diluted`|DIRECT: TTM·연간 variant를 혼합하거나 순이익/현재 주식수로 EPS를 만들지 않음.|
|v_fcf_yield: 가격 대비 주주에게 귀속될 현금흐름은 얼마인가|25|준비 중; 선택 후보 없음|PREPARING: 금융 CFO를 배당가능 현금흐름으로 간주하지 않음; 모형별 정의 미완결|
|v_vs_industry: 동일 정의·회계모형의 동종기업 대비 가격은 어떤가|20|`common_bp`; 선택 후보 `tangible_common_bp`|PROXY: 원시 B/P 계열만 계산; 동일 모형·정의의 비교집단과 정규화 연결 전 상대가치 점수 없음.|
|v_vs_own_history: 동일 기준의 자기 과거 가치 대비 현재 가격은 어떤가|15|준비 중; 선택 후보 없음|PREPARING: 같은 증권·분할 기준·지표 정의의 적격 가격 역사 필요|
|v_expectation_check: 가격이 요구하는 성장과 적격 실적의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 주주 현금흐름·자본 요구·성장 기대 산식 미완결|

### EQUITY_REIT

회계 적용: `EQUITY_REIT`. 상태: `RESEARCH_INCOMPLETE_NOT_DEFAULT`.

|역할(경제적 질문)|예산|기본·사용자 후보|근거 상태와 적용 한계|
|---|---:|---|---|
|q_profitability: 현재 자본 또는 영업기반에서 얼마의 이익을 얻는가|25|`cfo_assets_ttm`; 선택 후보 없음|PROXY: Nareit FFO 조정표·연결범위 별도 확인; CFO/자산은 FFO 또는 AFFO가 아님.|
|q_moat_proxy: 수익성이 여러 회계기간에 걸쳐 유지되는가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 수익성 역사·손실 처리·지속성 산식 미완결|
|q_earnings_quality: 보고이익의 현금·추정·위험 인식 근거가 적절한가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 충당·준비금·현금흐름 의미와 이익의 질 산식 미완결|
|q_financial_safety: 사업모형에 맞는 자본·유동성 완충력이 있는가|20|`debt_assets`; 선택 후보 없음|PROXY: Nareit FFO 조정표·연결범위 별도 확인; CFO/자산은 FFO 또는 AFFO가 아님.|
|q_capital_allocation: 주주 자본을 어떻게 배분하고 보전하는가|15|준비 중; 선택 후보 없음|PREPARING: 보통주 배당·실제 매입·자본 유지·희석 기준과 평가 산식 미완결|
|g_revenue_growth: 일관된 사업 수익기반이 얼마나 성장했는가|25|`revenue_cagr_3y`; 선택 후보 없음|DIRECT: Nareit FFO 조정표·연결범위 별도 확인; CFO/자산은 FFO 또는 AFFO가 아님.|
|g_per_share_growth: 동일 보통주 기준의 주당 성과가 성장했는가|25|준비 중; 선택 후보 `ffo_per_share_growth`|PREPARING: FFO/주 성장의 기간·보통주 분모·조정표 정의 준비 중|
|g_growth_efficiency: 성장과 함께 수익 창출 효율이 개선됐는가|20|`cfo_assets_improvement_3y`; 선택 후보 없음|PROXY: Nareit FFO 조정표·연결범위 별도 확인; CFO/자산은 FFO 또는 AFFO가 아님.|
|g_consistency: 성장이 기간별로 얼마나 일관됐는가|15|`revenue_growth_consistency_3y`; 선택 후보 없음|DIRECT: Nareit FFO 조정표·연결범위 별도 확인; CFO/자산은 FFO 또는 AFFO가 아님.|
|g_recent_acceleration: 최근 성장과 장기 성장의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 TTM/FY 성장 수익기반의 동일 정의 연결 필요|
|v_earnings_yield: 가격 대비 적격 회계이익 또는 사업모형 이익은 얼마인가|25|`nareit_ffo_mcap`; 선택 후보 없음|DIRECT: Nareit FFO 조정표·연결범위 별도 확인; CFO/자산은 FFO 또는 AFFO가 아님.|
|v_fcf_yield: 가격 대비 주주에게 귀속될 현금흐름은 얼마인가|25|준비 중; 선택 후보 `affo_mcap`|PREPARING: AFFO/유지보수 투자·임대 조정의 회사별 조정표 정의 준비 중|
|v_vs_industry: 동일 정의·회계모형의 동종기업 대비 가격은 어떤가|20|준비 중; 선택 후보 없음|PREPARING: 모형별 정확한 산식·귀속·입력 계약 미완결|
|v_vs_own_history: 동일 기준의 자기 과거 가치 대비 현재 가격은 어떤가|15|준비 중; 선택 후보 없음|PREPARING: 같은 증권·분할 기준·지표 정의의 적격 가격 역사 필요|
|v_expectation_check: 가격이 요구하는 성장과 적격 실적의 차이는 무엇인가|15|준비 중; 선택 후보 없음|PREPARING: 모형별 주주 현금흐름·자본 요구·성장 기대 산식 미완결|

## 실행과 인계

생산자 함수: `registry()` 및 `evaluate_raw(model, inputs, context)`. 입력은 기존 공통 요소의 필드·provenance 객체와 계산 문맥을 그대로 사용한다. 출력 `financial-555-raw-result/1`은 후보 버전·입력/recipe 해시·평가일·가용 cutoff·원시 상태·입력 존재·raw_valid·미완결 사유를 제공한다. `factor_score`, `role_score`, `axes`, `total`, `rank`는 이 단계에서 null이다. `candidate_adopted=false`, `official=false`다.

화면은 직접 측정/대리/준비 중, 숫자 입력 존재/적격 원시 산출/점수 미연결을 구분해야 한다. `PREPARING`, `MISSING_INPUT`, `COMMON_ATTRIBUTION_UNCONFIRMED`, 기간·단위·가용시각 검증 실패를 같은0점으로 표시하지 않는다. 보험 하위유형이 SIC 진단뿐이면 임시 연구 유형임을 별도로 표시한다.

합성 재현: `PYTHONPATH=implementation/src python -m pytest -q implementation/tests/research/test_qgv_555_financial_candidates.py`. 수작업 ROE·자본비율 기대값, 음수 유지, 귀속·기간·통화·시점 실패, 보험/REIT 분리, 역할 예산 유지와 축/총점 미산출을 검증한다.

보관 실자료의 회사별 값·계수·입력/결과manifest는 승인된 비공개 보존 경로에만 둔다. 공개 문서·fixture에는 실제 회사 값·가격·개인 자료를 넣지 않는다. 실제 가용성과 커버리지는 비공개 결과의 원래 모집단·평가일·입력 버전으로 보고하며 합성 시험을 실자료 채택이나 투자성과 검증으로 부르지 않는다.
