# SEC 제출 패턴 기반 예상 시기

최신 사용자 대기열4번. [sec_filing_timing.py](../../src/investment_system/providers/sec_filing_timing.py)의 `build_filing_timing_pattern(company_id, submissions, acquired_at, as_of)`는 제공된 SEC submissions `recent`에서 정확히 **10-Q·10-K 원 제출**의 관측 패턴만 만든다. 실제 요청·실적 calendar·가격·Holdout은 사용하지 않는다.

화면 표시는 **“제출 패턴 기반 예상 시기 · 확정 실적 발표일 아님”**이다. SEC 정기보고 제출과 회사 IR 실적 발표는 다르며, `confirmed_earnings_date`와 `estimated_exact_date`는 항상 null이다. 예상 시기라는 명칭을 확정일·D-day·다음 해/분기 날짜로 바꾸면 안 된다.

## 패턴 표현

- `(form, reportDate의 MM-DD)`별로 관찰된 제출 월을 나누고, 각 월의 day_min/day_max·관측수와 실제 제출 metadata를 보존한다. 평균·중앙값·회계분기 추정·미래 날짜를 추가하지 않는다.
- 예: 03-31 보고기간 10-Q가 합성 사례의 2023-05-08·2024-05-07·2025-05-09에 제출됐으면 **관측5월7~9일·3건**이다. 이것이 다음 실적일의 5월7~9일 확정/예측이라는 뜻은 아니다.
- 월을 가로지른 제출은 월별 창을 따로 둔다. 주차형 결산의 서로 다른 MM-DD를 자동으로 같은 분기로 합치지 않는다. 표본1건도 개수를 표시하고 새 최소 표본 임계값을 만들지 않는다.
- 10-K/A·10-Q/A·8-K·6-K·20-F·40-F는 제외한다. ASML20-F를 10-K로 대체하지 않으며 이 범위에서 패턴 부재를 그대로 표시한다.

## 가용성·오류 경계

미국17개 기존 TARGET company/CIK를 정확히 묶고 병렬 배열 길이·형식, reportDate≤filingDate≤취득일, 제공된 acceptanceDateTime≤취득시각을 확인한다. aware 취득시각≤as-of가 필수다. 접수시각이 없으면 null로 남기며 filingDate를 UTC 자정 이용 가능 시각으로 만들지 않는다.

동일 accession/내용 중복은 관측수를 늘리지 않는다. accession 상충·같은 form/reportDate의 여러 원 제출은 자동으로 하나를 골라 해결하지 않는다. accession 접두를 기업CIK와 일치해야 한다고 가정하지 않는다(제출 대행자 가능).

`available_at=acquired_at`, `published_at=null`, `historical_first_publication=false`, `SUPPLIED_RECENT_ONLY`를 표시한다. 제공된 recent 전체를 사용하고 에이전트가 기간/최근N을 선택하거나 별도 페이지를 수집하지 않는다. 오늘 취득한 과거 제출을 과거 cutoff의 당시 지식으로 소급하지 않는다.

합성 테스트는 월별 범위·윤일·다른 결산일/양식·amendment 제외·CIK·길이·시각·중복/상충·입력 불변성을 확인한다. 공시 패턴 생성이 실제 발표일 출처 확보나 QGV v2/forward 착수를 뜻하지 않는다.
