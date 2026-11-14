# 오너 비공개 공통 가격 V /1 — KIS 종가·Google 시트

2026-11-14 저녁 오너 결정. **KIS V 신규 연결 보류는 비공개 구역에서 해제**됐다.
이 문서가 같은 날 오전의 보류 문구를 해당 범위에서 대체한다. 현재 공식 모집단은
Universe504이며 시총 Top500 전환은 별도 승인·전환 검증 대상이다.

## 같은 계산 구조, 명시적인 통로

기존 `personal_sheet_v.prepare_personal` 및 personal-sheet-v/1 wire는 유지한다.
공통 `prepare_owner`는 owner-price-v-request/1 → owner-price-v-packet/1 →
owner-price-v-result/1을 사용한다. Google은 PERSONAL_SHEET_V + CURRENT,
KIS는 OWNER_PRIVATE_KIS_V + EXPLICIT_EOD_ASOF다. 임의 provider/namespace 조합은 거부한다.
같은 기존 `reported_raw`, Python555와 JS QgvV2 원시 산식·분위·역할·축 함수를 재사용한다.
별도 가격 엔진·주식수 추정·원문 수집·스케줄러를 만들지 않는다.

Main이 호출할 항목:
- `prepare_owner(request, evaluation, reference, financial_records, expected_evaluation=..., expected_reference=..., contracts=..., expected_contract_hashes=...)` (KIS)
- 같은 함수에 `prices=[...]` (Google), contracts는 전달하지 않는다.
- `owner_result(prepared)`, `owner_page(result, ...)`, `owner_group_page(result, group_id, decile=1..10, ...)`.
- JS `OwnerPriceV.calculate(packetText, {expected_payload_sha256, expected_evaluation, expected_reference, expected_configuration_hash})`.
- 공통 JSON 규격: `owner-price-v-contract.json`. 기존 raw/관문/역할 정의는 #541 계약을 따른다.

## KIS 입력·시각

기존 `normalize_page`가 검증한 kis-bars/1을 company_id별로 연결한다.
공급처 응답 바이트·receipt·manifest는 Main이 승인된 비공개 입력 경로에서 먼저 대사한다.
expected_contract_hashes는 **그 원문 검증에 결속된 외부 고정값**이다.
정규화 객체의 canonical digest와 raw_bars[].source_sha256(원응답 바이트 SHA256)는 다른 해시다.
같은 객체에서 계산한 digest만 서로 맞는 것으로 원문 독립 검증 완료를 주장하지 않는다.

가격은 MODP0/GUBN0 원시 raw_bars의 정확한 평가일 S 종가다. 조정 차트 bars와 마지막
보유일을 대신 쓰지 않는다. price_definition=KIS_DAILY_CLOSE는 공급처 일봉 종가이며
거래소 공식 종가나 실제 마지막 체결시각을 의미하지 않는다.
time_status=DATE_ONLY, price_timestamp=null. 평가일 S, 실제 취득일, 입력 마감,
계산일은 별도다. 일봉의 예정 장마감/자정을 체결시각으로 만들지 않는다.
query_started_at이 보존되지 않았다면 null/UNRECORDED로 표시한다.
Google의 최대20분 지연 안내와 날짜 없는 가격의 지연 미확인을 혼용하지 않는다.
실제 row.collected_at을 유지하며 merge header의 새 시각으로 오래된 관측을 갱신하지 않는다.

신원은 같은 코드 행·발행사·종류주·KIS 기호·거래소·유효기간의 검증된 mapping과
기존 identity 범위가 필요하다. 티커/CIK를 고정 증권 ID로 채우지 않는다.
USD 근거, 완료된 거래일, held range, 알려진 분할 충돌을 검사한다.
조정 가격에 자체 분할 보정을 중복 적용하지 않는다.

## 주식수·시총/EV 표시

현재 연결된 central 변형의 주식수는 **기간 가중평균 희석주식수(WAD)**다.
가격×WAD는 대리 시총이며 실제 종류별 평가일 발행주식수의 시총이 아니다.
EBIT/EV·FCF/EV도 그 proxy EV를 쓴다. 아래 표시 필드는 결과 행마다 반환한다.

- share_count_definition=WEIGHTED_AVERAGE_DILUTED
- capital_basis=WEIGHTED_AVERAGE_DILUTED_PROXY
- share_period_end / share_unit / share_class_id
- actual_class_outstanding_status=NOT_CONNECTED
- actual_class_outstanding_variant=SEPARATE_VARIANT_REQUIRED
- actual_all_class_market_cap=false / actual_all_class_ev=false
- label: 기간 가중평균 희석주식수 기반 proxy · 실제 종류별 시총/EV 아님

실제 주식수가 들어와도 diluted_shares에 대입하지 않는다.
실제 종류별 방식은 별도 variant·모든 해당 종류주/ADR·가격·기간·자본 구성 근거가 필요하다.
기간 종료일을 주식단위 기준일로 단정하지 않는다. 이미 소급 조정된 record에 또 비율을
곱하지 않는다. 알려진 분할 뒤 주식 기준의 record-bound 근거가 없으면 보류한다.
SOURCE_ALREADY_NORMALIZED 증거는 사용 record 해시·주식단위 기준·목표일·사건
참조와 검토/가용시각을 결속한다. 선언/해시 일치는 원문 독립 열람과 구분한다.

## 결과 경계와 미산출 사유

가격 확보 / 비가격 입력 완결(variant별) / 원시 비율 / 요소 점수 /
역할 / V축 / 부분 총점 / 적격 총점을 구분한다.
가격이 없어도 분모·평가/참조 명부를 보존한다. 원시 비율에 최소 표본을 미리 요구하지
않으며 요소/축의 기존 최소 표본·유효비중·공식Q 관문은 유지한다.
자기 과거 대비 역할은 적격 가격 이력이 없으면 미산출이다. 신규 KIS 종가 한 점으로
그 역할이나 V15역할 완결을 주장하지 않는다.

모든 통로는 EPHEMERAL_ONLY이고 연구 delivery가 거부한다. 서버 로그·공개 파일·URL·
서비스워커·기기 저장소·공식/연구 원장에 넣지 않는다. Main이 계정·입력 변경 시 RAM을
비우고 인증 경계를 유지한다. KIS 결과는 공식 Top500 선정·공식95% 달성에 쓰지 않는다.
개인 D1~D10·고정 순위와 공식/연구 분위는 별개다. 필터는 재순위를 만들지 않는다.
과거 S에 현재 보유 재무/근거를 쓴 결과는 실제 input_cutoff 기준 재구성이며 역사PIT 아님.

## 기술 전처리 인계

#542의 prepare_technical 계약을 재사용한다.
`include_split_assessment=True`에 새 분할 설명/충돌 검사를 추가했다.
기본 False는 기존 #542 예시·manifest를 보존한다.
공통 `assess_splits`가 ratio(새 주식/옛 주식), 효력일, 신원 충돌, MODP1,
이미 조정된 RAW, 행사 범위와 보류 사유를 제공한다. 빈 splits는 무분할 증거가 아니다.
전 지표를 한꺼번에 막지 않고 기존 각 rolling/재귀 지표의 준비기간 관문을 유지한다.
원문 직접 검증 여부와 caller 선언·참조 승계를 구분한다.

## 합성 예시·실행과 미검증 범위

`tools/owner_price_v_fixture.py`의 fixture/prepared/examples가 기존 생산자를 호출하는
공개 가능한 가상 기업 예시다. 네트워크나 real-input mode가 없고 RAM만 사용한다.
KIS 원자료 JSON/실제 가격은 공개 fixture에 저장하지 않는다.
기술 분할 상태 예시는 tests/fixtures/kis-technical-handoff/split-evidence-*다.
기존 #541/#542 자료를 새 실자료 성과로 재계산하지 않았다.

재현(환경 사용 가능 시):
```text
cd implementation
PYTHONPATH=src pytest -q tests/research/test_owner_price_v.py tests/research/test_owner_price_v_js.py tests/research/test_kis_owner_price.py tests/research/test_kis_technical_handoff.py
```
일시적인 환경 단절 뒤 복구된 로컬에서 신규 연결과 변경 경계 시험을 수행했다.
원격 최종 CI는 Draft PR에서 별도로 수집하며 로컬 일부 성공과 구분한다.
코드 보존/정적 검토·합성 실행·보관 실자료·브라우저·배포를 별도 상태로 보고한다.
실제 KIS 취득·신규 실자료 V 계산·공식 채택은 이 계약 구현에 포함되지 않는다.

합성 메모리 예시: `wire_files()`는 packet/pins/result/page와 D1~D10의 14개 파일을
바이트로 반환한다. `tests/fixtures/owner-price-v/memory-manifest.json`에 파일별 크기·
SHA256을 고정하고 `states.json`에 정상·가격 없음·정확일 없음·신원 미확인·분할 미확인·
EV 구성 결손·관문 미확인의 7상태를 제공한다. 전체 파일은 RAM에서만 생성하며 공개
저장소에는 실제 가격 없는 합성 상태·manifest만 둔다.
결과의 `V_roles_complete`는 모든 다섯 V역할 완결이고 `V_axis`와 구분한다.
`three_axes`, `gate_judgeable`, `gate_pass`, `gate_value_excluded`,
`owner_partial_total`, `owner_eligible_total`도 별도로 반환한다.
