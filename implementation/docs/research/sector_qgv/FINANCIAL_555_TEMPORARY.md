# 공식 FINANCIAL 원지표의 555 임시 매핑

코덱스 · 2026-11-14

정의 버전은 `financial-555-temporary-official/0.1.0`, 상태는
`TEMPORARY_OFFICIAL_FINANCIAL`이다. 공식 `qgv2-calc/2026-10-23.1`을 유지하고
그 FINANCIAL 원지표를 별도 555 연구 변형에 연결한다. 금융 전용 모형의 완결·채택이나
기존 금융 후보 `financial-555-candidates/0.1.0`의 정의 변경을 뜻하지 않는다.
GENERAL·REIT의 기존 정의와 공식 점수는 바꾸지 않는다.

매핑은 커버리지 측정 전에 고정했다. 하나의 공식 원지표를 둘 이상의 역할에
배정하지 않는다. 역할에 맞는 공식 정의가 없으면 예산을 유지하고 원값·점수를 null로
둔다. 공식 역할·축 점수를 555 점수로 복사하지 않는다.

|555 역할|기존 역할 예산|공식 원지표와 방향|경제적 범위|
|---|---:|---|---|
|q_profitability|25|roe ↑, roa ↑, net_interest_income_to_assets ↑|현재 FY 자본·자산 수익성 대리|
|q_moat_proxy|20|moat_proxy ↑|ROE 수준과 변동성을 결합한 지속성 대리|
|q_earnings_quality|20|null|금융 현금흐름·충당·준비금의 질 정의 없음|
|q_financial_safety|20|equity_to_assets ↑|장부자본 완충 대리; 규제자본·유동성 아님|
|q_capital_allocation|15|dilution_3y ↓, incremental_roe_5y ↑|희석주식수 변화·5년 추가자본 수익 대리|
|g_revenue_growth|25|revenue_cagr_3y ↑|공식 매출 정의의 3년 성장|
|g_per_share_growth|25|eps_cagr_3y ↑, book_value_per_share_cagr_3y ↑|공식 희석 EPS·자본/희석주식수 성장|
|g_growth_efficiency|20|incremental_roe_3y ↑|3년 추가 자기자본 대비 추가 이익|
|g_consistency|15|revenue_positive_growth_share ↑, revenue_growth_volatility ↓|연간 성장 빈도·변동성|
|g_recent_acceleration|15|revenue_acceleration ↑|TTM 성장과 3년 FY CAGR의 차이|
|v_earnings_yield|25|null|FINANCIAL_PROFILE_V_NOT_DEFINED|
|v_fcf_yield|25|null|FINANCIAL_PROFILE_V_NOT_DEFINED|
|v_vs_industry|20|null|FINANCIAL_PROFILE_V_NOT_DEFINED|
|v_vs_own_history|15|null|FINANCIAL_PROFILE_V_NOT_DEFINED|
|v_expectation_check|15|null|FINANCIAL_PROFILE_V_NOT_DEFINED|

15역할 중 9개에 고유 원지표 14개를 배정한다. 각 축의 예산 합계는 100이며
Q의 정의된 예산은 80, G는 100, V는 0이다. 원값 존재와 적격 점수 산출은 별개다.
V와 이익의 질을 억지로 채워 15역할 완결로 표시하지 않는다.

## 정확한 공식 정의와 귀속

원천은 `qgv/v2_factors.py`의 `_metrics_financial`, `_growth_common`,
`_Company.roe`, `eps`, `shares`, `per_share`, `_moat`, `_incremental`이며 방향과
Q/G 역할은 `v2_scoring.SUBMETRICS['FINANCIAL']`과 같다. 다음 `avg_pair`는
기말 잔액이 있어야 하며 기초가 없으면 기말만 사용한다.

|원지표|산식·기간·결측 규칙|
|---|---|
|roe|FY NI / avg_pair(FY0 equity, FY−1 equity). 기말 자본>0, 존재하는 기초 자본>0|
|roa|FY NI / avg_pair(FY0 assets, FY−1 assets); 최종 분모>0|
|net_interest_income_to_assets|FY 순이자수익 / 위 평균자산; 최종 분모>0|
|equity_to_assets|FY0 기말 자본 / FY0 기말 자산; 자산>0. 음수 자본을 0으로 바꾸지 않음|
|incremental_roe_5y / 3y|(NI0−NI−n)/(equity0−equity−n), n=5/3; 자본 증가분>0. ROE 차이·CAGR 아님|
|moat_proxy|FY0…FY−4의 적격 ROE 중 최소3개. μ>0이면 μ×max(0,1−모집단σ/μ), μ≤0이면 μ. 연속5년 필수 아님|
|dilution_3y|(FY0/FY−3 가중평균 희석주식수)^(1/3)−1; 양수 끝값, 공식 FY0 분할 기준. 실제 발행·매입 수량 아님|
|eps_cagr_3y|(공시 희석 EPS0/EPS−3)^(1/3)−1; 양수 끝값, 공식 분할 기준. NI/주식수로 EPS 재구성 안 함|
|book_value_per_share_cagr_3y|((equity0/shares0)/(equity−3/shares−3))^(1/3)−1; 양수 자본·주식수 끝값. 분모는 가중평균 희석주식수|
|revenue_cagr_3y|(매출0/매출−3)^(1/3)−1; 양수 끝값. 중간연도 필수 아님|
|revenue_positive_growth_share|FY0…FY−4 각각 직전 FY 대비 성장률 중 >0인 비율. 직전 매출>0인 유효 관측 최소3/최대5개|
|revenue_growth_volatility|위 유효 연간 성장률의 모집단 표준편차. 현재 매출 음수는 허용|
|revenue_acceleration|TTM 매출 전년동기 성장률−3년 FY 매출 CAGR; 이전 TTM>0. TTM은 공식 FY+당기누적−전년누적, 이후 분기 없으면 FY 비교|

연간 관측은 공식 커널의 350…380일과 FY 목표일 ±10일을 따른다. FY0 anchor는
NI·매출·CFO·EBIT 중 최신 연간 종료일이다. 기간을 TTM으로 바꾸거나 중간연도
추가조건을 붙이면 이 임시 공식 재사용과 다른 변형이다.

US GAAP NI 우선순위는 `NetIncomeLoss`→`ProfitLoss`, 자본은
`StockholdersEquity`→비지배지분 포함 자본이다. IFRS는 모회사 귀속 NI·자본을
우선하고 각각 전체 `ProfitLoss`·`Equity`로 돌아간다. 두 선택은 독립적이다.
공식 NI·자본의 귀속 일치를 추가 입증하거나 우선주·비지배지분을 조정한 보통주
ROE/BPS라고 부르지 않는다. 매출 concept도 연도별로 달라질 수 있으며 순이자수익과
매출 기반 성장의 분자가 같다고 가정하지 않는다.

## 적용과 중복 노출

산식 적용은 공식 source record의 `profile=FINANCIAL`, calc23.1, LIVE/STALE로
한정한다. 임시 산식 profile과 비교집단의 회계모형은 별도 필드다. S1에서는 기존
BANK·INSURANCE·BROKER·ASSET_MANAGER·MORTGAGE_REIT 등 확인된 회계모형을
유지한다. 미확인 하위모형을 표본 확보를 위해 공통 FINANCIAL 집단에 자동 편입하지
않는다. 분류 미확인·원자료 결측·비교표본 부족을 구별한다.

ROE와 moat는 같은 수익성의 수준·지속성을 본다. 3년/5년 incremental ROE는
겹치는 이익·자본 끝값을 사용하고, 매출 성장·일관성·가속도도 공통 매출 역사를 쓴다.
자본과 희석주식수는 ROE·자본완충·BPS·EPS·희석 등에 걸쳐 겹친다. 각각을 독립 신호로
주장하지 않는다. `input_family_contributions`는 하나의 주계열로 분할한 기여도이며,
`shared_input_exposures`는 여러 원입력에 대한 중복 노출로 **합산하지 않는다**.
같은 원지표의 역할 중복은 검증 오류다.

주당 지표 세 개는 각각 FY0/FY−3의 공식 share-basis 경로 검사가 필요하다.
EPS·dilution의 검사가 BVPS에 자동 승계되지 않으며 BVPS는 자본 끝값의 원문·기간도
필요하다. 공식 FY0 기준 변환의 가정·충돌·추가확인 상태를 보존한다. Q/G의 `shares()`는
V의 cover-share scale 검사를 자동 수행하지 않는다. 가격·종류주 검증도 별도다.

## 함수 계약과 검증

`research/qgv_555_financial_temporary.py`가 제공하는 함수는 다음과 같다.

- `financial_catalog()`: `financial::` namespace의 정의 14개. `source_metric`은 공식 raw
  key이며 방향·기간·귀속·적용범위·주식근거 요구·공통입력계열을 반환한다.
- `financial_role_recipes()`: 15역할 모두의 `axis`, 기존 `weight`, `metrics`를 반환한다.
  미정의 6역할은 `metrics={}`와 `null_reason`을 유지한다.
- `validate_role_recipes(recipes)`: 고정 매핑·예산·고유 원지표·공식 정의 버전을 확인한다.
- `validate_official_financial_record(record)`: calc/profile/state와 적격 raw key의 유한 수만
  확인한다. issuer·cutoff·원문 결합·주식 기준·비교집단 확정은 입력 어댑터 책임이다.
- `contribution_metadata(roles, axis_weights=..., included_axes=..., total_available=...)`:
  555가 재계산한 역할 출력의 명목·유효 역할/원지표 기여와 중복 노출을 반환한다.
  점수·백분위·비교집단은 만들지 않는다. 미정의 역할도 명목 예산은 남고 유효 기여는0이다.

정규화는 기존 555의 issuer 단위 pool·동률·최소8 정책을 재사용하고 각 축은 적격
역할 예산 최소50%를 요구한다. 산식 원값에 비교표본 문턱을 붙이지 않는다.
명목 기여는 축비중×역할비중×요소비중, 유효 기여는 실제 적격 축·역할·요소의
가용 비중으로 재정규화한다. 총점이 없으면 총점 유효 기여는0이다. 기본 축비중
Q34/G33/V33에서 미정의 역할의 명목 비중은39.8%이며, S1의 실제 축비중은 엔진에서
전달한다. 이 비중은 성과 최적값이 아니다.

합성 시험은 14개 공식 원값의 수작업 기대값, 기초잔액 결측·음수·실제0·비양수 분모,
CAGR 끝값, 역할 중복·이동 차단, BVPS 주식근거 요구, 공식 점수 미열람, 명목·유효
기여와 정확히50인 축 경계를 확인한다. 실제 회사값·비공개 입력 경로는 이 문서와
fixture에 넣지 않는다. 과거 시스템 PIT 완결이나 투자성과 검증으로 해석하지 않는다.

검증 명령: `PYTHONPATH=implementation/src python -m pytest -q implementation/tests/research/test_qgv_555_financial_temporary.py`.

## 보존 원자료 연결

`qgv_555_financial_inputs.apply_temporary_financial_inputs(snapshot,
source_review_file, source_review_sha256, reviewed_at, input_cutoff,
book_value_reviews=...)`는 새 입력·감사를 반환한다. 검토 파일의 전체 SHA와 공식
record digest, issuer·통화·FY·취득시각·회사공시 body SHA를 대조한다. 기존
owner source의 공식 파일 SHA와 회사공시 body SHA는 다른 근거이며 혼동하지 않는다.
원래 회계모형·섹터·공식 점수 참고·가격·일반기업 원지표는 보존하고 `financial::`
원값·근거와 임시 profile/peer 필드만 추가한다.

EPS와 희석은 같은 source context의 0.4 검토 claim을 사용한다. BVPS는
`review_official_book_value_history(payload, record, source_ref)`에서 별도로
`_TracedCompany`, `_route`, `shares`, `per_share`와 공식 자본 instant picker를
실행한다. 자본/연간주식수 끝일 일치, 최신 공시 충돌, 비양수 자본·주식수,
공식 분할 경로·불연속·cover scale 상태를 확인한다. EPS 결측은 BVPS를 자동
차단하지 않으며 EPS 검토 성공도 BVPS를 자동 승인하지 않는다. 일치하는 cover
참조가 없으면 기존 공식 재사용의 `NO_REFERENCE` 제한을 보존한다.

각 proof의 `available_at`은 새 연구 채택 검토시각, `source_available_at`과
`retrieved_at`은 원래 record 취득시각이다. 기존 검토 작성시각은
`source_review_created_at`으로 구별하고 검토 파일 수령시각이 미입증이면
`review_file_received_at=null`이다. 새 cutoff는 기존 입력 cutoff와 새 검토시각
이후여야 한다. 원공시·가격의 시각은 갱신하지 않는다.

share claim의 가정·충돌·추가확인·evidence-only 적격 상태를 각 지표에 보존한다.
미채택 원값은 `diagnostic_raw`에만 두고 산출용 원값은 null이다. BVPS 검토는 원
record와 body SHA에 묶인 별도 검토 hash를 남긴다. 새 proof는
`TEMPORARY_OFFICIAL_FINANCIAL_RAW`, 정책은 `official-financial-role-bridge/1`이다.
추가 시험은 `tests/research/test_qgv_555_financial_inputs.py`에서 재현한다.
