# 내 시트 V 계산 계약 /1

2026-11-14 오너 확정 지시. 공개 공식 calc23.1, 저장된555 연구 및 KIS 비공개 결과를
덮어쓰지 않는 개인 현재 평가다. Main은 화면·Google 인증·시트 연결·실행/전달을,
Codex는 공통 계산 연결·입력/결과 검증을 담당한다. KIS 신규 V 연결과 Public Float
가격/시총 대체는 보류한다. 기보유 구현은 보존한다.

## 기존 계산과 연결 범위

- 공식 중앙 JS: web_assets/qgv-v2.js `scoreUniverse`, Python qgv_v2의 같은 원시 계산.
- 기존555: U1 산업/전체 fallback8, S1 섹터×회계모형/no fallback8, 역할 유효비중50%.
- 현재 연결 대상은555 0.2~0.5의 central::ebit_yield/fcf_yield/own_history/gap다.
  원시 산식은 REPORTED flow/WAD 변형이며 실제 종류별 시총·EV가 아니다.
- 공식 calc23.1의 타입 보정/직접 own-history 역할과555의 별도 참조집단·공식 Q 관문을 같다고 취급하지 않는다. JS 어댑터는 기존 raw·percentile·
  axisScore를 사용하며 기존 Python555의 비교집단/역할 orchestration에 대응한다.
- 다른 선택 variant는 조용히 다른 산식으로 바꾸지 않는다. 개인 가격에 맞춘 연결이
  없으면 `PERSONAL_VARIANT_NOT_CONNECTED`. 금융 임시 V의 미정의도 유지한다.

## 요청과 입력

`personal-sheet-v-request/1`: `context`, `configuration`, 평가/참조 입력과 각각의
독립 expected identity, `financial_records`, `prices`. context에는 비밀이 아닌
`context_id`, `evaluation_day`, `evaluated_at`, `input_cutoff`, `provider`,
`price_definition`이 필요하다. 과거 snapshot 날짜를 현재 가격에 맞춰 바꾸지 않는다.
새 평가 입력은 caller가 새 버전과 재무 기준/가용시각을 명시해 제공한다.

가격 행: company_id/issuer_id, provider_symbol, status(AVAILABLE/MISSING/INVALID/
READ_FAILED/NO_TRADE), trade_day, price_timestamp(nullable), time_status(CONFIRMED/
DATE_ONLY/UNCONFIRMED), query_started_at, received_at, currency, provider,
price_definition, adjustment_status(AS_TRADED/SPLIT_ADJUSTED/UNKNOWN), source_refs,
price 및 별도 mapping/share_basis/corporate_actions/ADR/history 근거.
티커나 issuer ID를 검증된 security ID로 만들지 않는다. 검증된 고정 증권 ID가 없는
경우에도 기존 documentary mapping record로 같은 증권·종류·유효기간을 입증해야 한다.

GOOGLEFINANCE_CURRENT의 안내 UP_TO_20_MINUTES와 실제 timestamp 차이는 별개다.
가격 시각이 없으면 actual_delay_seconds=null/freshness=UNDETERMINED이며 조회/입수
시각을 대신 쓰지 않는다. 알려진 과거 거래 시각은 DELAYED로 표시할 수 있지만,
시장 휴장 원인을 추정하지 않는다. 지연 표시 자체로 새 제외 문턱을 만들지 않는다.
trade_day가 없으면 해당 평가의 수치 채택을 보류한다. Google 조정 방식 UNKNOWN은
AS_TRADED가 아니며, RAW가 필요한 현재 변형은 미산출이다. 분할조정 가격도 적격
동일 주식 기준 변환이 없으면 그대로 넣지 않는다.

매핑 근거는 동일 코드/issuer/security(확인된 경우)/종류/provider_symbol, 적용기간,
가용시각을 고정한다. WAD 기준 및 기업행사 근거는 실제 사용된 주식수 기간부터
가격일/평가일까지 이어져야 한다. ADR은 비율과 분모 단위가 확인돼야 하며 원주
주식수와 ADR 가격을 그대로 곱하지 않는다. 이미 같은 단위로 정규화된 입력만 사용한다.
EV의 차입금·현금 결손은0이 아니며, 자기 과거 대비 역할은 별도 적격 이력이 필요하다.
GOOGLEFINANCE 과거 API를 사용하지 않는다.

## 결과와 개인 범위

`personal-sheet-v-result/1`: namespace=PERSONAL_SHEET_V, storage=EPHEMERAL_ONLY,
configuration/model/formula/evaluation/reference/input/price-snapshot 구분, 원래 분모,
행별 가격/비가격/원시 비율/요소/역할/V축/부분 및 적격 개인 총점과 이유를 반환한다.
가격 원값·금융 원문·인증값은 결과에 되돌려주지 않는다. 현재 가격과 재무 기간은
별도 표시한다. 실제 원시 비율과 미검증 진단 숫자를 합치지 않는다.

전수 평가/참조 명부는 유지하고 해당 요소의 유효 표본만 따로 센다. 평가/참조 원본
identity와 개인 가격 적용 후 identity를 각각 보존한다. 화면 필터는 저장된 점수·순위·
분모·D1~D10을 변경하지 않는다. 개인 그룹은 입력 payload SHA·문맥·모형·요소·범위로
구분하며 공식/연구 그룹 ID를 재사용하지 않는다. 기존 D10 상위/D1 하위·동점 code순
분할·N<10 분위 미산출을 유지하고10개 구간 전체를 조회한다.

개인 입력은 일반555 run/연구 delivery에서 거부한다. 명시적 개인 계산 호출만 허용한다.
연구95% target/성공 원장으로 내보내지 않는다. 개인 카운트는 고정 분모의 단계별 관측일
뿐이며 공식·연구 커버리지 실적이 아니다. 원시 자료·실제 개인 결과는 공개 fixture나
영구 연구 보관본에 기록하지 않는다. CLI는 합성 실행만 파일로 쓰며 실제 실행은 호출자
메모리 인터페이스로 제공한다.

## JS 전달 경계

Python 준비기가 독립 anchor와 가격/재무/증권 근거를 검증한 현재 packet을 만들며,
JS는 정확한 입력 bytes의 외부 SHA와 평가/참조/config anchor를 별도로 확인한다.
같은 packet의 Q/G는 같은555 설정에서 계산한 가격 독립 축이다. JS는 공식 Q/G 점수로
대신하지 않고 이 공통555 축을 받아 V 및 개인 총점을 계산한다. 원시 V는 기존
QgvV2.scoreUniverse(REPORTED/type off/빈 cyclical membership)의 detail로 계산한다.
일반 공식 scoreUniverse의 V 총점을555 총점으로 복사하지 않는다. 추가 orchestration은
같은555 비교집단·역할·순위 규칙의 JS 연결이며 새 원시 산식 엔진이 아니다. 자기 과거 대비는 기존처럼 자체 역사 백분위를 직접
역할 점수로 쓰고 다시 참조집단 백분위화하지 않는다. 해당 요소의 최소 이력3과
다른 요소의 최소 참조8, 표시 분위의 최소 평가10을 각각 구분한다.

## 구현·변경 검증 계획

1. `research/personal_sheet_v.py`: 입력 검증·현재 packet·공통555 호출·개인 페이지/그룹.
   `qgv_555.py`는 명시적 개인 범위 guard/target 제거만, central_v는 reported raw helper만
   추출한다. 중앙 IEX 계약은 그대로다. 일반 research delivery는 개인 결과를 거부한다.
2. `research/personal_sheet_v.js`: 기존 JS helper로 같은 packet의 V 역할·축·총점·개인
   분위 연결. Main 소유 JS·화면·가드·워크플로는 수정하지 않는다.
3. 합성 기대값은 EBIT200/EV1030, FCF120/EV1030; 부채 결손은 EV두 요소만 차단한다.
   정상/빈값/일부가격/시각미확인/지연/조정UNKNOWN/신원·ADR·종류·기업행사 불일치,
   날짜/가용시각/독립anchor 불일치, 표본7/8/10/23, 동점, 세션 분리, 전체10분위를 시험한다.
4. 실제 기존 JS를 Node에서 실행해 원시 비율/요소/역할/V축/개인총점/순위/분위를 대사한다.
   기존 계산 재실행은 하지 않고 변경 경계와 필요한 중앙 helper 회귀만 실행한다.
5. 합성 입력·출력/manifest/명령·전체 SHA를 Draft PR과 Main에 전달한다. 실제 시트 연결,
   Google 인증, 브라우저 및 배포 확인은 별도다. 신규 취득·병합·배포는 실행하지 않는다.

## Main 호출·인수

- Python: `prepare_personal(request, evaluation, reference, financial_records, prices,
  expected_evaluation=..., expected_reference=...)` → 민감한 RAM 준비 객체.
  `personal_result(prepared)` → 가격 원값 없는 개인 결과.
  `personal_page(result, offset=0, limit=20, company_ids=None)`와
  `personal_group_page(result, group_id, decile=None, offset=0, limit=50)`는 저장 순위를
  투영하며 재계산하지 않는다. 반환 payload는 기존1,800,000 bytes 상한 안이다.
- JS: 공통 QgvV2를 먼저 로드하고 `personal_sheet_v.js`를 같은 코드로 연결한다.
  `await PersonalSheetV.calculate(packetText, {expected_payload_sha256,
  expected_evaluation, expected_reference, expected_configuration_hash})`.
  준비 packet은 검증된 입력이어야 한다. 원시 시트 응답을 이 진입점에 곧바로 넣거나,
  같은 packet 안의 값만으로 독립 pin을 만들지 않는다. Main은 실제 준비/호출 위치를
  선택하고 기존 인증·전달과 연결한다. 별도 Python 서버 도입을 전제하지 않는다.
- `price_metadata.actual_delay_seconds`는 receipt 당시 가격 나이이며 공급자 피드 지연의
  실측값이 아니다. `price_age_at_evaluation_seconds`가 현재 평가시점 나이이고, 신선도는
  이 값으로 판단한다. 둘 다 price timestamp 없으면null이다. 읽은 시각을 대신 쓰지 않는다.
- 단위: counts와 variant 집계는 UNIQUE_ISSUER, groups의 순위/분위 구성원은 CODE_ROW다.
  nonprice_any/nonprice_all 및 variant별 nonprice_complete를 구분한다. 하나의 비율이
  준비됐다는 사실을 모든 V 입력이나 V5역할 완결로 표시하지 않는다.
- financial_periods와 행별 provenance는 원 record hash/가능한 원문 hash/취득시각 및
  mapping/share/action/ADR/history의 출처·적용 범위를 보존한다. 원문 hash가 없으면null로
  남기며 record hash나 payload SHA를 원문 확인의 대체 증거로 부르지 않는다.
- IEX_HIST는 기보유/합성 비교 source로도 허용한다. Google과 같은 batch에 섞지 않으며
  개인 namespace에 한정한다. 이 허용은 중앙 IEX 입력/게시 계약이나 새 취득 승인이 아니다.
- 개인 결과를 연구용 `qgv_555_delivery.artifacts`에 전달하면 거부된다. Main도 namespace와
  schema를 분기하고 연구·공식·KIS 저장소/공유/로그 경로에 넣지 않는다. 실제 시트 결과는
  이 합성 예시 생성기에 입력할 수 없으며 repo에는 SYN 코드의 예시만 보존한다.

Wire schema: [personal-sheet-v-contract.json](personal-sheet-v-contract.json).
합성 생성: `PYTHONPATH=implementation/src python implementation/tools/generate_personal_sheet_v_examples.py --synthetic --output <new-dir>`.
개발용 생성기는 기존 합성 시험 fixture를 재사용하며 pytest는 개발 의존성이다. 실행 라이브러리는 pytest를 import하지 않는다.
