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
- 최상위 `collection`: `checked_at`, `run_day`(뉴욕 날짜), `trigger`(SCHEDULED·MANUAL·OTHER, `GITHUB_EVENT_NAME`), `previous`(LOADED·NO_LIVE·UNAVAILABLE·NOT_REQUESTED), `stale_after_seconds`(일일 주기 86400), `scheduled_streak {start_day, count, since, last_run_day}`.
- `scheduled_streak`(차트 착수 조건 7회, 대기열 §9·사용자 지시 2026-10-17 2항): `start_day`는 고정 2026-10-19다. 10/19 미국 거래일을 관측하는 정기 실행(22:17 UTC = 뉴욕 18:17, 같은 날)이다. 날짜는 실행의 뉴욕 날짜(`run_day`)다. 주말 실행도 평일처럼 센다(관측일 NONE이어도 일일 workflow 기준).
  - 시작일 전 정기 실행: 0. `since`가 되지 않는다.
  - 시작일 정기 실행, 또는 게시본이 아직 없음(404): 1.
  - 게시본이 같은 뉴욕 날짜의 정기 실행이면(재실행): 그대로 둔다. 두 번 세지 않는다.
  - 게시본의 마지막 정기 날짜가 전날이면 +1. 전날보다 이전이면(그날 배포 실패·거부·누락) 1부터 다시 센다.
  - 게시본을 읽지 못했거나 /3이거나 수가 null이면 null(확인 불가). 추정하지 않는다. 이후 하루가 빠지면 1부터 다시 알려진 수가 된다.
  - 수동 실행(대체·일회성)은 세지도 끊지도 않는다. 게시본 값을 그대로 옮긴다(첫 게시면 0, 읽지 못하면 null).
  - 파일은 배포에 성공해야만 공개되므로 공개된 수는 게시본 기준 추정이다. 실제 배포 성공은 보고 때 Actions 실행 기록으로 확인한다.
- 로그: `SEC_WITHDRAWN company_index=… code=… previous=LIVE|NOT_AVAILABLE|WITHDRAWN|NONE`, `SEC_PRESERVED … previous=…`, `SEC_PUBLIC_COLLECTION … previous=… policy_na=… withdrawn=… collection_failed=… scheduled_streak=…`(기존 토큰 뒤에 붙임, 기존 토큰 뜻은 그대로).
- 배포 직전 신선도 검사(`tools/pages_freshness_guard.py`)는 이 파일을 strict validator로 읽는다. 정책상 NA·새 수집은 acquired_at이 같거나 늦으면 통과, WITHDRAWN은 라이브 관측의 acquired_at을 정확히 가리키고 그 뒤에 감지됐을 때만 통과한다. 유지 행이 라이브 행과 다르거나(PRESERVED_MISMATCH), 같은 시각에 값만 바뀌거나(CHANGED), 행 손실·이전 시각은 거부한다. 라이브가 /3이어도 같은 규칙으로 비교한다(/3 NOT_AVAILABLE은 기록 없음).
- 웹(`sec-reported.js`·`ops-status.js`)은 /1~/4를 읽는다. WITHDRAWN·COLLECTION_FAILED 행은 acquired_at을 보이지 않으며 값으로 쓰지 않는다.

## Universe 식별 충돌 철회 (사용자 결정 UNI-WITHDRAWN (a)·#289, 2026-10-17)

대상: `sec-universe-shares.json`, `sec-universe-qg.json`, `sec-qgv2.json`의 `records`. 세 파일은 `schema_version` 2로 바뀐다.

- **구분**: 단순 조회 실패·기호 미해석·식별 미확인(같은 CIK)은 #278 보존이고, 수집 성공의 자료 없음은 #287 새 NA다. 둘 다 철회가 아니다. 식별 충돌만 철회한다: 한 티커를 여러 CIK가 주장, SEC 응답이 다른 CIK(`SEC_CIK_MISMATCH`·`SEC_ISSUER_NOT_ALLOWED`), 다른 CIK가 자기 수집 기록 없이 나타남.
- **대상 식별**: 그 파일·그 코드의 라이브 행이 관측 하나를 정확히 가리킬 때만 철회한다(발행사 CIK, 자기 `acquired_at`, SEC 원자료 해시 두 개). 아니면 기존대로 `CIK_UNRESOLVED`(또는 이번 실행의 NA 행)이며, 다른 행은 철회하지 않고 시각을 만들지 않는다.
- **철회 행**: NOT_AVAILABLE, 사유 `IDENTITY_CONFLICT_WITHDRAWN` 하나, CIK·`acquired_at`·해시·값 없음. `detected_at`(감지 시각), `withdrawn_acquired_at`·`withdrawn_cik`(그 파일 라이브 행의 수집 시각·CIK). 파일마다 자기 행을 가리킨다.
- **감지 시각의 뜻이 TARGET과 다르다.**
  - TARGET(`sec-public-inputs.json` WITHDRAWN, `sec-qgv2.json` `target`): 다시 감지하면 `detected_at`을 그 감지 시각으로 갱신한다(같은 관측을 가리킴).
  - Universe: 처음 감지한 시각을 유지한다. 충돌이 이어지는 동안 행은 그대로다.
  - 마지막 재확인은 행에 넣지 않고 실행 로그 `SEC_UNIVERSE_WITHDRAWALS <scope> new_shares=… kept_shares=… new_qg=… kept_qg=… new_qgv2=… kept_qgv2=…`(이번 실행 신규 철회·유지된 철회 코드 수)로만 남긴다.
  - 감지·재확인 시각으로 `acquired_at`이나 최신성을 바꾸지 않는다.
- **복구**: 이번 실행의 수집 기록, 감지 이후 수집, 이번 실행 충돌 증거 없음이 모두 맞을 때만 새 행이 철회를 대체한다. 새 보유자는 자기 행으로 시작한다.
- **스키마 전환 1→2**: 철회 행이 사유 코드와 행 키를 계약에 더하므로(각 검증기는 사유 목록과 행 키 집합을 고정한다) 세 파일을 2로 올린다. 생성기는 2를 쓴다. 검증기·이전 사본 읽기·`--preserve-only` 수동 배포·신선도 검사는 1과 2를 읽고, 철회 행은 2에서만 유효하다. 1만 아는 구버전 화면은 2 파일 전체를 거부한다(안전 차단이며 하위 호환이 아니다). 새 화면은 아는 것보다 높은 버전이면 "자료 형식이 새 버전입니다. 새로고침하세요"를 보인다.
- **UNI-TARGET(조건부 독립)**: TARGET 고정 CIK 재무 관측은 유지한다. 철회 코드가 TARGET에 점수를 빌려주지 않는다. TARGET의 기기 가격은 티커 심볼로 읽으므로(Universe 시트 행, `DeviceValuation.deviceQuote`, PriceStore), 그 심볼이 철회된 Universe 코드의 심볼이면 가격·V·종합 점수·후보를 막고 "가격 식별 충돌로 가격·V·종합 점수 사용 중지"를 보인다. 다른 심볼의 TARGET은 그대로다.
- 검증: `tests/test_universe_withdrawal_e2e.py`.

## Universe 상장 종료 항목 (2026-10-25 조사 B-a 안, PR-2 · 소유자 승인 뒤 병합)

대상: `sec-universe-shares.json`, `sec-universe-qg.json`, `sec-qgv2.json`의 `records`. 표: `universe/sec_universe_shares.py`의 `LISTING_ENDED_CODES`.

- **왜 따로 두나**: 10-17 결정 (a)의 보존(PRESERVE)은 기호가 SEC 거래소 기호표에서 잠깐 빠져도 같은 CIK의 확인된 이전 행을 그대로 다시 게시한다. 영구히 상장이 끝난 코드도 이 규칙에 걸려, 10-17 값과 acquired_at이 기한 없이 남는다(14일 뒤 STALE이 되어도 값이 있는 행이라 단면에 남고 TARGET v1 확정을 막는다).
- **항목이 되는 조건**: 기호표에서 빠졌다는 사실만으로는 넣지 않는다(일시적 누락, PSKY→SKYD 같은 기호 변경과 구별되지 않는다). SEC 공시로 상장 종료가 확인되고 소유자가 승인한 항목만 넣는다. 항목 칸: 코드, CIK, 발효일, 사유, 근거.
- **현재 항목(1개)**

| 코드 | CIK | 발효일 | 사유 | 근거 |
| --- | --- | --- | --- | --- |
| `NASDAQ:WBD` | 0001437107 | 2026-10-06 | 현금 인수 후 상장 폐지(`ACQUIRED_FOR_CASH_DELISTED`). 인수자는 Skydance(구 PSKY) | 8-K(2026-10-06, Item 2.01 완료·3.01 상장 폐지, 접수번호 `0001193125-26-415055`) · Form 25(2026-10-06, `0001193125-26-415091`) · Nasdaq 25-NSE(2026-10-06, `0001354457-26-000951`) · 15-12G(2026-10-16, `0001193125-26-423513`) · SEC 원문: [8-K](https://www.sec.gov/Archives/edgar/data/1437107/000119312526415055/d200872d8k.htm), [15-12G](https://www.sec.gov/Archives/edgar/data/1437107/000119312526423513/d188095d1512g.htm) · 참고(병합 안 됨): 닫힌 PR #390, 브랜치 `claude/universe-membership-audit` 커밋 `12785304`의 `UNIVERSE_INDEX_FOLLOWING_20261023.md` §2-2 |

- **판정 순서**: `previous_decision`이 PRESERVE보다 먼저 표를 본다. 표에 있는 코드이고 그 파일의 이전 행이 **표의 CIK**에 대한 확인된 관측(CIK, 자기 acquired_at, SEC 원자료 해시 두 개)이면, 이번 실행이 무엇을 가져오든 상장 종료 NA 행을 게시한다. 이전 행이 다른 CIK이거나 확인된 관측이 아니면 표는 그 행을 건드리지 않고 기존 규칙을 따른다. 다른 미해석 코드(예: PSKY)는 그대로 PRESERVE다.
  - 표는 모든 규칙보다 먼저다. 그래서 표에 있는 코드에는 식별 충돌 철회(UNI-WITHDRAWN (a))와 이번 실행의 새 행(다른 CIK의 행 포함)도 적용되지 않는다. NASDAQ:WBD 기호를 나중에 다른 CIK가 쓰거나 여러 CIK가 주장해도, 철회 행이나 새 발행사 행 대신 CIK 0001437107의 상장 종료 NA 행이 남는다. 두 행 모두 값이 없으므로 점수 효과는 같다.
  - 되돌리는 방법은 표에서 항목을 빼는 것뿐이다. 빼도 안전하다. 상장 종료 행 자체가 확인된 관측이라 그 뒤에는 PRESERVE가 그 행을 그대로 두고, 신선도 검사도 EQUAL로 통과한다.
- **상장 종료 NA 행**: 그 파일의 빈 행에 기존 사유 `CIK_UNRESOLVED` 하나. 값·점수·지표·식별 결합(shares의 listing_id)·`calc_version`은 지운다(0으로 채우지 않는다). 마지막 관측의 `cik`, `acquired_at`, 원자료 해시(shares는 cover 해시 포함)는 남긴다. 다음 실행에서도 같은 행이 그대로 나온다. 철회 행(`detected_at`)이 아니다.
- **acquired_at을 남기는 이유(확인함)**: 배포 직전 신선도 검사는 라이브 행에 acquired_at이 있는데 산출물 행에 없으면 `LOST_RECORD`로 배포를 거부한다. 같은 acquired_at이면 값과 무관하게 `EQUAL`로 통과한다. 그래서 이 행의 acquired_at은 "끝난 상장의 마지막 실제 관측"을 뜻한다.
- **바꾸지 않은 것**: 사유 코드 목록, 스키마 버전(2), 세 검증기(Python·JS), 신선도 검사, `calc_version`(`qgv2-calc/2026-10-17.1`), Universe504 목록(UNI-DEF (a)·UNI-FOLLOW (a), 분모 504).
- **화면 표기**: 사유가 `CIK_UNRESOLVED`라 정확한 표기가 아니다(CIK는 알고 있다). 화면별 문구는 다음과 같다.
  - 목록(`qgv-scores.js`, `v-coverage.js`): 'CIK 미해결'.
  - Universe 기업 화면(`universe-company.js`): QGV 칸에 'CIK 미확인: 이 코드의 SEC 등록번호를 찾지 못했습니다'와 함께 '수집 2026-10-17 03:15 UTC · 수집 후 N일'이 나온다. 같은 화면의 SEC 주식수 칸에는 상태 `NOT_AVAILABLE · CIK_UNRESOLVED`, 'CIK 0001437107', '수집 2026-10-17 03:15 UTC'가 나온다. 즉 알려진 CIK 옆에 '등록번호를 찾지 못했다'는 문구가 함께 보인다.
  - 대안: 화면 전용 설명을 따로 승인받아 넣을 수 있다(web_assets 변경과 APPROVED_SHA256 재고정이 필요하다).
  - 전용 사유 `LISTING_ENDED`는 사유 목록·스키마를 바꾸는 일이라 11/9 뒤 별도 PR로 미룬다.
- **정책 관계**: 점수 효과는 UNI-FOLLOW (a)를 고를 때 소유자가 받지 않은 '10/6 WBD 제외'와 같다. 근거가 다르다. 지수 편출이 아니라 공시로 확인된 상장 종료이고, 그래서 자료를 다시 모을 수 없다. 지수 구성은 이 표의 근거가 아니므로 같은 날 S&P 500에서 빠진 CTVA(계속 상장)를 비롯한 다른 지수 변경은 건드리지 않는다. 표는 지수를 따라가지 않는다.
- **효과(공개 파일 2026-10-25T00:26Z 재계산)**: 단면 499→498(GENERAL 431→430), Q 점수 행 486→485, G 494→493, telecommunications 그룹 9→8 CIK(`MIN_PEERS` 8 경계). Q는 15행이 바뀐다(FOX·FOXA −8.78, CHTR −7.20, CMCSA −6.04, VZ −5.70). G는 최대 −0.16, TARGET 17종목은 Q 그대로·G 최대 0.08. TARGET v1 확정 검사(`publishedCheck`)는 이 행을 정상 NA로 센다(값이 있는 행만 신선도 검사). 전진 검증 원장은 이 행을 쓰지 않는다(모집단 n·해시만 바뀌고 구간은 그대로).
- **실행 로그**: `SEC_UNIVERSE_COLLECTION … listing_ended=<n>`(이번 실행에서 상장 종료 NA로 게시한 코드 수). 조사 B-a 안이 요구한 범위 밖의 추가다. 줄 끝에 붙였고 앞 토큰은 그대로지만, 이 줄을 완전 일치로 읽는 저장소 밖 점검이 있으면 고쳐야 한다(저장소 안에서는 시험만 이 줄을 읽는다). 표 결합은 바꾸지 않으므로 WBD는 계속 `unresolved_codes`에 들어간다. 상장 종료 행은 이전 acquired_at을 그대로 가지므로 `preserved_previous_<file>`에도 계속 1로 잡힌다. 매일 점검의 기준선은 승인된 항목 수(지금 1)다. `preserved_unconfirmed`에서는 빠진다.
- **`PUBLISHED_COVERAGE` 줄**: `stale_7d_rows`·`acquired_oldest`·`shard_acquired`는 값 유무와 무관하게 cik와 acquired_at이 있는 행을 모두 센다(`tools/published_coverage.py`). 그래서 WBD 상장 종료 행 때문에 `stale_7d_rows`는 1 이상, `acquired_oldest`는 2026-10-17, 샤드 5 최솟값은 2026-10-17로 계속 남는다. 알려진 값이다. 값이 있는 행만 세도록 바꾸는 일은 사전 점검 PR(PR-3)에서 다룬다. 중앙 V(PR-A)가 들어오면 `qgv-official.json`의 `inputs[0].acquired_oldest`도 NA 행을 포함한 모든 행의 acquired_at으로 정하므로 2026-10-17에 머문다(정보용, 차단 아님). PR-3의 '값이 있는 행만' 변경이 이 칸도 다뤄야 한다.
- **TARGET v1 초안 기준(inputBasis)**: 기준은 calc_version, type_scope, 철회 행, 샤드별 최신 acquired_at으로 정한다. 상장 종료 행은 이 중 어느 것도 바꾸지 않는다. 보통은 같은 날 정기 실행이 샤드를 갱신해 기준이 바뀌지만, 두 경우는 다르다.
  - staged TARGET이 있는 `--preserve-only` 배포: `sec-qgv2.json`만 다시 merge되고 shares·qg는 바이트 그대로 복사된다. 그래서 다음 정기 실행 전까지 WBD는 `sec-qgv2.json`에서만 NA로 바뀐다.
  - 수집이 돌지 않은 날(`COLLECTION_NOT_RUN`): 시작 복원 merge가 이미 WBD를 NA로 바꿨는데 샤드 시각은 그대로다.
  - 두 경우 모두 점수는 바뀌는데(FOX·FOXA Q 최대 −8.78) 열려 있는 초안의 기준은 그대로다. 병합 뒤 첫 배포 다음에 열린 TARGET v1 초안을 다시 만들기를 권한다. 상장 종료 코드를 기준에 넣는 일은 web_assets 변경(재고정 필요)이라 나중에 한다.
- 검증: `tests/test_universe_listing_ended.py`(세 파일 NA, 검증기·신선도 검사 통과, acquired_at을 지우면 LOST_RECORD, 단면·Q·G 정확히 1 감소, 다른 코드 상태 불변, PRESERVE 유지, 원장·`publishedCheck` 정상 NA), `tools/target_v1_builder_node_test.js`.

## 실제 조사 상태

Actions run38036368523(head78180443)의 고정 로그에서 normalize 실패3개(index4 AVGO,8 HUBB,12 MSFT)·BUILD_OK를 확인했다. ASML은 실패하지 않았다. 기존20-F는 이미 허용했고, 누락 개념만으로는 기존 코드가 실패하지 않았다. 따라서 IFRS 누락을 이번 세 회사의 확정 원인으로 보고하지 않는다.

실행 환경 SEC_USER_AGENT는 미설정이며 연결 도구의 SEC companyfacts/submissions 접근도 차단됐다. 실제 세 회사의 원문 fact를 로컬 재현하지 못했고 잘못된 행의 form/날짜/metadata를 확정하지 않았다. Secret을 읽거나 임의 연락처를 만들지 않았다. 합성 회귀 검증과 실제 원인 확인은 별개다. 코덱1이 workflow_dispatch로 재실행하여 `failed_companies=0` 및 SEC_EXCLUDED 고정 코드/개수를 확인한다. 이 로그를 실제 해결 증거로 사용한다.
