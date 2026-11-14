# 금융 임시 역할 연결 연구0.5

모형은 `unified-555-financial-temporary/0.5.0`와
`sector-555-financial-temporary/0.5.0`이다. 공식 calc23.1, 공개 파일, 연구0.1~0.4,
금융 전용 후보 정의와 기존 저장 설정을 자동 교체하지 않는다.

`financial_temporary_policy=official-financial-role-bridge/1`과 고정
`financial_roles`를 설정·캐시·재현 해시에 포함한다. 임시 산식은 공식 FINANCIAL의
FY 정의이며, 보통주 귀속 TTM ROE 등 금융 전용 후보의 정의와 다르다.
[고정 역할표](FINANCIAL_555_TEMPORARY.md)의14개 원지표는 각각 한 역할에만 배정한다.
ROE 수준/지속성·증분3/5년·매출 성장/지속/가속의 공유 원입력 노출은 별도 표시한다.
정보가 독립적이라거나 중복 문제가 해결됐다고 선언하지 않는다.

## 계산과 가용성

- 기존 `_Pool`·백분위·`axis_score`를 재사용한다. 공식 점수·순위를 복사하지 않는다.
- Q/G/V 명목 축 비중과 역할 예산을 유지한다. 미정의 Q이익의 질·V5역할은
  빈 metrics와 null score/null_reason으로 남긴다. `raw_all`도0이다.
- 축은 유효 역할 비중50% 이상일 때만 산출한다. 원값이 있다는 사실만으로
  요소·역할·축을 산출하지 않는다. 표본은 기존 최소8을 적용한다.
- `financial_temporary_contributions`는 모든 역할의 명목 배점, 가용 역할 안에서의
  재정규화 비중, 총점이 있을 때의 실효 기여를 구분한다. 누락 예산은 삭제하지 않는다.
- GENERAL·REIT 임시GENERAL 경로는 기존0.4와 같은 원지표·설정·계산을 유지한다.
  단, 통합 연구 목록에 금융 결과가 추가되면 저장 역할 순위의 구성은 달라질 수 있다.

`financial::` namespace로 GENERAL 지표와 분리한다. EPS·WAD 희석률·장부자본/WAD
성장은 각각의 공식 주식 기준 근거를 검사한다. 장부가 성장의 분자는 보통주 귀속
확정값이 아닌 공식 equity이며, 현재 실제 종류별 발행주식수를 뜻하지 않는다.
`ALL_OFFICIAL_REUSE`와 `EVIDENCE_ONLY`를 평가·참조 양쪽에 동일 적용한다.
둘 다 엄격0.3 통과와 구분한다.

## 분류와 참조집단

U1 임시 변형은 보관 공식 FINANCIAL 프로필의 근거가 있는 행을 명시적으로 허용한다.
원 공통 분류가 미확인이면 임시 프로필과 미확인 상태를 함께 보존한다.

S1은 확인된 섹터×기존 회계모형으로 비교한다. BANK/INSURANCE/BROKER/
ASSET_MANAGER/MORTGAGE_REIT를 표본 확보를 위해 합치지 않는다.
원 분류 record ID·해시·버전·적용 기간·가용시각을 평가/참조에서 검사하고, 미확인
모형은 보류한다. 산업 하위유형이 다르면 전용 정의 연구에서 따로 검토한다.
공식 FINANCIAL 산식을 임시 사용했다는 이유로 원 분류를 재확정하지 않는다.

## 입력과 화면 계약

생산자는 `qgv_555_financial_inputs.apply_temporary_financial_inputs`로 원 record·CIK·
FY·통화·원문 해시·취득/검토 시각을 검증한다. core의 직접 JSON 호출도64자리 해시와
시각 순서를 검사한다. 새 입력의 available/reviewed 시각을 과거로 옮기지 않는다.
분류·가격·비금융 원지표·기존 input version은 그대로 보존한다.

- 행 `temporary_model_status=TEMPORARY_OFFICIAL_FINANCIAL`,
  `display_label=금융 임시(공식 FINANCIAL 원지표)`.
- `financial_calculation_profile`은 산식 프로필,
  `peer_accounting_template`은 비교 회계모형이다. 둘은 같은 필드가 아니다.
- `financial_reference`는 원 참고 기록이며 임시 점수에 복사하지 않는다.
- 요소 `financial_raw_evidence`는 산식·기간·귀속·출처·시각을 표시한다.
- `defined_roles`와 실제 활성 역할·산출 역할을 구분한다.
- 집계 `financial_temporary_issuers`와 `financial_temporary_code_rows`의 단위를 구분한다.
- 임시 결과·금융 전용 원시 후보·엄격 검증 결과를 합쳐 커버리지로 보고하지 않는다.

기존 bounded delivery/1과 전체D1~D10을 사용한다. Main은 새 모형 ID·설정·평가/참조
입력·원결과 해시를 확인하고 같은 배치만 읽는다. 공개 승격·인증·브라우저·배포는 별도다.

## V와 신규 원문 경계

공식 FINANCIAL 커널에는 금융 V5역할이 정의되지 않았으므로 가격만으로 채우지 않는다.
금융 전용 V 후보는 별도 정의·출처·가격·증권 조건을 갖춰 비교해야 한다.
공개 중앙 V 복구와 승인 보관 가격을 쓰는 비공개 연구는 별도 경로다.
다른 평가일의 가격·주식수·증권 기준을 혼합하지 않는다.

신규 공시 수령, 추출, 귀속·단위·기간 확인, 적격 채택, 원시/요소/축 증가를 구분한다.
기존 원문에서 새로 추출한 값과 새로 취득한 과거 문서는 가용시각이 다르다.
새 현재일 진단을 과거 평가일 커버리지에 합치지 않는다. SEC 표본의 요청 수·바이트·
실패·중복 재사용과 다음 확대 조건은 승인된 비공개 receipt/manifest에서 인계한다.
