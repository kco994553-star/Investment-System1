# SEC daily 실패 진단·부분 성공·행 단위 제외

2026-10-10 사용자 긴급 승인: 회사별 실패를 격리하고, 형식이 다른 개별 fact는 해당 행만 제외한다. 유효한 outstanding-share fact가 남으면 회사는 유지한다. 진단에는 고정 코드·HTTP 상태·단계·회사 순번·제외 사유별 개수만 출력한다. 값·URL·UA·이메일·키·회사명·원문 exception은 출력하지 않는다.

## 수집·실패 경계

`public_sec_inputs.py --live --output ...`는 US17을 `sorted(US_LISTINGS)` 순서로 시도한다. 회사 index는1~17, client 초기화/설정 실패는0이다. `SEC_FAILURE company_index=4 stage=normalize code=SEC_NO_ELIGIBLE_SHARE_FACTS http_status=None`처럼 고정 형식만 출력한다. retry 소진은 `SEC_HTTP_RETRIES_EXHAUSTED`와 마지막429/5xx 상태를 함께 출력한다. 알 수 없는 예외는 고정 fallback으로 바꾸며 원문을 출력하지 않는다.

- JSON/CIK·취득시각·수집 실패는 여전히 회사별 NOT_AVAILABLE다. 취득 원문은32MiB 상한, 공개 투영은2MiB 상한이다.
- 허용된 주식 수 개념의 잘못된 행만 제외한다. 유효한 행이0개면 `SEC_SHARE_CONCEPT_MISSING`(개념 없음), `SEC_SHARE_UNIT_MISMATCH`(shares 단위 없음), `SEC_NO_ELIGIBLE_SHARE_FACTS`(모두 제외)로 회사 실패한다. 가짜0이나 과거 파일의 수치를 채우지 않는다.
- submissions의 잘못된 개별 filing은 제외한다. 배열 구조가 깨져 행을 안전하게 결합할 수 없으면 filings를 비우고 `FILING_SCHEMA_INVALID=1`로 구조 오류 한 건을 기록한다. 유효한 주식 수 fact를 버리지 않는다. 제출 패턴·M3 accession 연결은 해당 filing 근거가 없으면 별도로 NOT_AVAILABLE다.
- 일부 회사 실패도 exit0·`SEC_PUBLIC_BUILD_OK failed_companies=N`; 모든 회사 실패는exit1·새 파일 미작성·기존 파일 보존이다. 공개 경계/저장 자체의 전역 오류는 성공으로 처리하지 않는다.

## 개념·서류·주식 종류

허용 개념은 `dei:EntityCommonStockSharesOutstanding`, `us-gaap:CommonStockSharesOutstanding`, `ifrs-full:NumberOfSharesOutstanding`다. IFRS weighted-average EPS 분모·발행주식 수·자기주식은 대응 개념으로 취급하지 않는다. IFRS outstanding 정의는 발행 주식에서 자기주식을 차감한 수이며 [ESMA ESEF taxonomy 부록](https://www.esma.europa.eu/sites/default/files/2024-05/ESMA32-2009130576-3011_Final_Report_amending_RTS_on_ESEF_-_2024.pdf)의 해당 개념 설명을 확인했다. 보고된 수만 투영하며 ADR/종류/통화 basis를 자동 확인하지 않는다.

10-K·10-Q와 수정 보고서, **10-KT·10-QT 및 /A**, 20-F·40-F·6-K·8-K 및 /A를 그대로 보존한다. 전환 보고서를 일반 연간/분기 보고서로 바꾸거나 짧은 기간을 연환산하지 않는다. Q/G·유형 엔진의 기간 채택 규칙을 바꾸지 않는다. [SEC Form 10-K](https://www.sec.gov/files/form10-k.pdf)·[Form 10-Q](https://www.sec.gov/files/form10-q.pdf)의 transition-report 구분에 해당한다.

optional start/fy/fp/frame의 JSON null은 필드 미제공으로 투영한다. 날짜·회계연도·기간을 추정하거나0으로 바꾸지 않는다. 비-null 값이 규격과 다르면 해당 행을 제외한다.

명시적 `dimensions`의 `us-gaap:StatementClassOfStockAxis`와 QName member가 있는 행은 `CLASS_SPLIT`로 제외하며 회사에 `share_class_notice=SHARE_CLASS_BASIS` **주의 표시만** 붙인다. member·개별 종류 수치는 공개하지 않고 **합산·보정하지 않는다**. 다른 dimension/segment/context는 `UNKNOWN_DIMENSION`로 제외한다. SEC companyfacts는 보통 비차원 표준 개념만 제공하므로 이 marker가 없다는 사실은 단일 종류의 증거가 아니다. 일반 수치 불일치만으로 CLASS_SPLIT를 추론하지 않는다. 이 notice는 종류별 보고가 있다는 주의 정보이며 선택 listing과 같은 filing의 경제적 basis 차이를 확정하지 않는다. 같은 개념·단위·측정일·accession·form·filed의 다른 값은 모든 충돌 행을 `FACT_CONFLICT`로 제외한다. 다른 시점·다른 accession 값은 충돌로 취급하지 않는다.

이 공개 marker는 #134 cover binding·#110 SHARE_CLASS_BASIS 검증을 대체하지 않는다. 실제 기기 시총 계산에는 동일 filing의 security/cover 근거가 필요하며, 종류 기준 차이는 표시만 한다.

## 공개 계약 v3·로그

2026-10-17 이전 생성기는 항상 `public-sec-reported-inputs/3`를 썼다(지금은 아래 v4). scope·정확한 US17 순서는 유지한다. strict guard는 이전 /1·/2·/3도 계속 읽는다.

| 행 | 필드 |
| --- | --- |
| LIVE | company_id,cik,acquired_at,sources,reported_shares,filings,status,excluded_fact_counts,share_class_basis,share_class_notice |
| NOT_AVAILABLE | company_id,cik,status,reason_codes,failure_stage,company_index,http_status,excluded_fact_counts,share_class_basis,share_class_notice |

`excluded_fact_counts`는 고정 코드→양의 정수인 객체다. 0인 코드는 생략한다. 주식 수/filing 행은 첫 실패 사유 하나만 센다. 단위별 rows는 UNIT_MISMATCH 개수로 센다. 구조를 읽을 수 없는 bucket/filing 배열은 구조 오류 한 건이다. 개인정보·임의 문자열·추가 필드는 허용하지 않는다. 가능한 코드:

- FORM_NOT_ALLOWED, UNIT_MISMATCH, DATE_INVALID, DATE_AFTER_ACQUISITION, VALUE_INVALID, FACT_SCHEMA_INVALID, ACCESSION_INVALID, PERIOD_METADATA_INVALID.
- CLASS_SPLIT, FACT_CONFLICT, UNKNOWN_DIMENSION.
- FILING_DATE_INVALID, FILING_TIMESTAMP_INVALID, FILING_ACCESSION_INVALID, FILING_REPORT_DATE_INVALID, FILING_AFTER_ACQUISITION, FILING_SCHEMA_INVALID.

예: `SEC_EXCLUDED company_index=4 code=FORM_NOT_ALLOWED count=2`. 실패/성공 회사의 제외 개수가 동일한 고정 형식으로 출력된다. core fact가 없어서 모든 회사 실패한 경우에도 실패 diagnostics에 제외 개수를 남긴다. source URL·SHA는 기존 고정 SEC 공개 출처 계약에만 남고 진단 stdout에는 출력하지 않는다.

코덱1 consumer는 schema /1·/2·/3를 읽고 NOT_AVAILABLE 행을 **먼저 건너뛴 다음** sources/reported_shares/filings를 접근해야 한다. 새 notice는 증거 확정이 아니다. `share_class_basis`는 공개 데이터만으로 확인할 수 없어 항상 `UNCONFIRMED`이며 단일 종류로 해석하지 않는다. 유효한 종류 차원 행에만 notice를 붙이며 값·날짜·form이 잘못된 행은 해당 기본 사유로 제외하고 종류 근거로 쓰지 않는다. 워크플로·Worker·웹은 코덱2가 바꾸지 않는다.

## 공개 계약 v4 (사용자 결정 2026-10-17, TARGET NA 스키마 보완)

생성기는 `public-sec-reported-inputs/4`를 쓴다. 성공한 수집의 시각만 `acquired_at`이다. 실패 시각(`checked_at`)·식별 충돌 감지 시각(`detected_at`)은 `acquired_at`에 넣지 않는다.

| 행 status | 뜻 | 필드(공통: company_id,cik,status,excluded_fact_counts,share_class_basis,share_class_notice,preserved_previous) |
| --- | --- | --- |
| LIVE | 성공한 수집, 주식 수 있음 | acquired_at,sources,reported_shares,filings |
| NOT_AVAILABLE | 성공한 수집의 정책상 NA(normalize 단계) | acquired_at(실제 수집 시각),sources,reason_codes,failure_stage=normalize,company_index,http_status=null |
| COLLECTION_FAILED | 수집 실패, 유지할 이전 행 없음 | checked_at,reason_codes,failure_stage,company_index,http_status |
| WITHDRAWN | 식별 충돌(SEC_CIK_MISMATCH·SEC_ISSUER_NOT_ALLOWED), 이전 관측 사용 중지 | detected_at,withdrawn_acquired_at(중지한 관측의 acquired_at, 없으면 null),reason_codes,failure_stage,company_index,http_status |

- `preserved_previous`: 이번 실행에서 만든 행은 null. 일시적 수집 실패로 이전 사본의 행(LIVE·NOT_AVAILABLE·WITHDRAWN)을 그대로 둔 행은 `{checked_at, reason_codes, failure_stage, http_status}`(이번 실패). 관측 내용(acquired_at·sources·값)은 바꾸지 않는다.
- 최상위 `collection`: `checked_at`, `run_day`(뉴욕 날짜), `trigger`(SCHEDULED·MANUAL·OTHER, `GITHUB_EVENT_NAME`), `previous`(LOADED·NO_LIVE·UNAVAILABLE·NOT_REQUESTED), `stale_after_seconds`(일일 주기 86400), `scheduled_streak {count, since, last_run_day}`.
- `scheduled_streak`: 정기 실행이 전날 정기 실행의 게시본을 읽으면 이어 세고, 아니면 1부터 다시 센다. 파일은 배포에 성공해야만 공개되므로 공개된 수는 배포 성공을 스스로 증명한다. 수동 실행은 세지 않고 그대로 옮긴다. 이전 사본을 읽지 못하면 null(확인 불가).
- 로그: `SEC_WITHDRAWN company_index=… code=… previous=LIVE|NOT_AVAILABLE|WITHDRAWN|NONE`, `SEC_PRESERVED … previous=…`, `SEC_PUBLIC_COLLECTION … previous=… policy_na=… withdrawn=… collection_failed=… scheduled_streak=…`(기존 토큰 뒤에 붙임, 기존 토큰 뜻은 그대로).
- 배포 직전 신선도 검사(`tools/pages_freshness_guard.py`)는 이 파일을 strict validator로 읽는다. 정책상 NA·새 수집은 acquired_at이 같거나 늦으면 통과, WITHDRAWN은 라이브 관측의 acquired_at을 정확히 가리키고 그 뒤에 감지됐을 때만 통과한다. 유지 행이 라이브 행과 다르거나(PRESERVED_MISMATCH), 같은 시각에 값만 바뀌거나(CHANGED), 행 손실·이전 시각은 거부한다. 라이브가 /3이어도 같은 규칙으로 비교한다(/3 NOT_AVAILABLE은 기록 없음).
- 웹(`sec-reported.js`·`ops-status.js`)은 /1~/4를 읽는다. WITHDRAWN·COLLECTION_FAILED 행은 acquired_at을 보이지 않으며 값으로 쓰지 않는다.

## 실제 조사 상태

Actions run38036368523(head78180443)의 고정 로그에서 normalize 실패3개(index4 AVGO,8 HUBB,12 MSFT)·BUILD_OK를 확인했다. ASML은 실패하지 않았다. 기존20-F는 이미 허용했고, 누락 개념만으로는 기존 코드가 실패하지 않았다. 따라서 IFRS 누락을 이번 세 회사의 확정 원인으로 보고하지 않는다.

실행 환경 SEC_USER_AGENT는 미설정이며 연결 도구의 SEC companyfacts/submissions 접근도 차단됐다. 실제 세 회사의 원문 fact를 로컬 재현하지 못했고 잘못된 행의 form/날짜/metadata를 확정하지 않았다. Secret을 읽거나 임의 연락처를 만들지 않았다. 합성 회귀 검증과 실제 원인 확인은 별개다. 코덱1이 workflow_dispatch로 재실행하여 `failed_companies=0` 및 SEC_EXCLUDED 고정 코드/개수를 확인한다. 이 로그를 실제 해결 증거로 사용한다.
