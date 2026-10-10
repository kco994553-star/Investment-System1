# 정부 원자료 화면 경계와 나머지4축 입력

사용자 연속 대기열7번. 실제 수집 없이 supplied bytes 파서·합성 테스트를 구현한다. FRED/ALFRED·fallback·키/환경변수 접근·공개 producer/앱/워크플로 연결은 없다.

## 화면 함수와 국면 연결

`macro/government_screen.py::build_government_macro_screen(primary_results, as_of, remaining_results=())`는 기존1차4축 파서 결과와 나머지4축 파서 결과의 cutoff 이전 관측 취득본을 JSON-safe **RAM 결과**로 만든다.8축×6칸의 Level은 RAW_EVIDENCE, 승인되지 않은 상태 규칙은 null/NOT_AVAILABLE다. 단위·관측기간·실제 취득시각·응답 hash를 보존하고 Decimal을 정확한 문자열로 전달한다. 임의 provider request·키·URL·원문 note는 출력하지 않는다. 정부 자료 재사용 범위이며 FX 통계환율의 지속 보관·가격 환산 승인으로 확대하지 않는다.

BEA GDP **수준**과 BLS CPI **지수**를 기존 `MacroEngine`의 `growth`/`inflation` fractional 입력으로 바꾸는 정의가 아직 없다. GDP 분기/전년·연율, CPI SA/NSA·전년/전월 선택과 단위 전환을 임의로 만들지 않는다. 국면은 `UNAPPROVED_ENGINE_INPUT_MAPPING`/NOT_AVAILABLE다. Labor/Treasury 수익률을 새 국면 변수로 쓰지 않는다.

별도 `evaluate_synthetic_macro_inputs(indicators, as_of)`는 명시적 합성 growth/inflation의 기존 v0.1.1 엔진 연결을 검증한다. 두 입력이 모두 유한 수치이고 cutoff가 aware여야 하며 누락을0/NORMAL로 만들지 않는다. 기존0.08/0.05/0.03 임계와 판정순서를 변경하지 않는다. 이 SYNTHETIC_CHECK는 원기관→실제 국면 채택이나 원본28/28 검증 근거 복원이 아니다. Model/QGV·새 가중치·Holdout과 연결하지 않는다.

## 나머지4축 파서의 선택 계약

`providers/macro_remaining.py`는 Liquidity=Fed H.4.1, Credit=Fed H.8, FX=Fed H.10의 공식 compact XML과 Fiscal=Treasury MTS JSON supplied payload를 읽는다. [#112 출처 조사](REMAINING_FOUR_AXES_PRIMARY_SOURCES.md)는 정확한 series/표 항목 채택이 아니므로 **기본 시리즈는 없다**. 호출자는 axis/provider, exact series 또는 표/행 필터·값/기간 필드, 단위·빈도·SA·측정 basis를 명시해야 한다. H.4.1 수요일 잔액/주간 평균, H.8 은행 집단/대출군, MTS flow/month·계층, H.10 pair 방향/index 종류를 자동 선택·합성하지 않는다. SLOOS·DTS·Debt-to-the-Penny 보조 후보는 이 v1 구현 범위 밖이다.

파서의 RAW_EVIDENCE는 입력 형식 확인이며 사용자 지표 채택·6상태 산출·READY 승격이 아니다. 단위·UNIT_MULT를 보존하고 곱셈·환산·HY spread 대체·순유동성·재정/GDP·FX 반전을 하지 않는다. 빈칸/ND/NaN/충돌/partial 응답은 정상0으로 만들지 않는다. Treasury `record_date`는 일 단위 발표 후보일뿐 관측월/실제 발표시각과 같다고 가정하지 않는다.

호출은 `parse_fed_sdmx(payload, receipt, binding)`, `parse_treasury_mts(payload, receipt, binding)`, `select_remaining_observed(results, as_of)`다. Fed binding은 `dataset_id`, raw `source_frequency`, Decimal `unit_multiplier`와 exact family 속성·통화를 포함한다. Fiscal의 실제 관측월 필드/basis가 확인되지 않으면 publication date를 대신 넣지 않아 입력이 미제공일 수 있다. supplied XML fragment hash는 그 bytes에만 결속하며 원 ZIP 응답 hash·원본 추출 계보의 증거가 아니다.

빈티지는 취득시각 기준 `OBSERVED_CAPTURE_UPPER_BOUND`이며 cutoff 이후 취득본은 제외한다. 최신 응답의 과거 관측행을 역사 PIT 빈티지로 소급 인증하지 않는다. 발표 schedule·파일 수정시각을 `available_at`으로 대신 쓰지 않는다. parser 결과는 불변이며 함수는 네트워크/저장/공개 출력을 하지 않는다.

## 공식 schema 근거

2026-10-10 공식 **설명·schema·dataset metadata만** 확인했다. XML 관측파일/API data records/zip은 받지 않았다.

- Fed 공통 schema: <https://www.federalreserve.gov/datadownload/Output/Common/Metadata/frb_common.xsd>; namespace `http://www.federalreserve.gov/structure/compact/common`, 공통 DataSet/Obs.
- Release별 schema: <https://www.federalreserve.gov/datadownload/Output/H41/Metadata/H41_H41.xsd>, <https://www.federalreserve.gov/datadownload/Output/H8/Metadata/H8_H8.xsd>, <https://www.federalreserve.gov/datadownload/Output/H10/Metadata/H10_H10.xsd>. Series에 SERIES_NAME/FREQ/UNIT/UNIT_MULT, Obs에 TIME_PERIOD와 OBS_VALUE/OBS_STATUS를 정의한다. 일반 SDMXv2 namespace를 추측하지 않는다.
- Fed code list에서 FREQ는 원 numeric code이며 UNIT_MULT는 실제 multiplier(예:1000000)다. BEA의10진 exponent와 같다고 처리하지 않는다. H.4.1의 SERIESTYPE(level/average/change), H.8의 LEVEL/RATE·SA, H.10의 통화/방향 metadata를 caller binding과 대조한다.
- Fed global common:DataSet와 release별 Series/Obs **fragment**만 공식 XSD로 확인했다. common XSD가 import하는 SDMXMessage/CompactData의 직접 XSD는404 또는 유효 XML이 아닌 응답이어서 full-feed wrapper를 확인하지 못했다. parser는 확인된 DataSet fragment만 받으며 실제 feed envelope 추출·자동 수집은 미구현이다. 추측한 wrapper를 허용하지 않는다.
- MTS official dataset/data dictionary: <https://fiscaldata.treasury.gov/datasets/monthly-treasury-statement/>. 직접 endpoint 후보 `https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/mts/mts_table_1`; gross receipt/outlay/deficit-surplus fields와 millions USD를 확인했다. 정확한 값 필드·기간 basis의 사용자 채택은 별도다.

Fed DDP 전환 공지가 있어 직접 제공 경로의 지속성은 미확정이다. 직접 경로가 중단되면 미제공이며 FRED로 대체하지 않는다. XML DTD/entity·잘못된 namespace·JSON 중복 key/nonfinite·서로 다른 synthetic·충돌 취득본/응답·불완전 page와 source URL lookalike를 합성 테스트한다.

## 미확정 정의

1차 growth/inflation 정규화와 나머지4축의 정확한 series/필드·basis 채택, 모든 새 Direction/Momentum/Surprise/Stress/Confidence 규칙은 미확정이다. 정의 승인 없이 원자료를 기존 엔진 수치로 자동 연결하지 않는다.
