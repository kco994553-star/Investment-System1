# DART 연결 준비 — 한미반도체 숫자 재무제표 입력

조회일: **2026-10-09 UTC**. 구현 담당은 **코덱1**이며 이 문서는 입력 계약과 검증 기준만 제안한다.
구현 코드·인증 호출·키 발급/등록·실제 재무 데이터 수집은 이번 작업에 포함하지 않았다.
대상은 기존 `hanmi` / **KRX 042700** / DART **00161383** 한 회사다.
기존 `markets/kr.py`의 `KR_DEFERRED`와 `markets/us.py`의 US17 범위를 변경하거나 QGV를 실행하지 않는다.

## 준비 상태와 인수 조건

사용자는 OpenDART 점검 종료 예정 **2026-10-11 18:00 이후** 저장소 Secret **`DART_API_KEY`**를 등록할 예정이다.
이는 사용자 안내이며 이번 조사에서는 Secret 값과 저장소 등록 상태를 조회하지 않았다.
[공식 점검 공지](https://opendart.fss.or.kr/)의 시각에는 시간대가 명시되지 않았다.
예정 시각 도달만으로 재개·키 등록·호출 성공을 간주하지 말고 실제 서비스 재개와 등록 여부를 확인한다.
숫자 API 전체가 점검 동안 중단된다고 단정하지 않는다. 미등록·점검 중에는 인증 요청을 시작하지 않는다.

연결 기준은 병합된 [SEC M1 #81](https://github.com/kco994553-star/Investment-System1/pull/81)의
[시각·lineage·receipt 설명](M1_SEC_INPUTS.md)과 기존 [D6 계획](PIPELINE_DESIGN.md#d6--한미반도체도쿄일렉트론-재무)이다.
SEC의 보수적 취득 경계, 불변 원문, 실패 시 READY 포인터 보존을 재사용할 수 있다.
SEC CIK·form·US17 검증기와 `facts_to_raw`에 DART JSON을 그대로 넣는 방식은 맞지 않는다.
후속 DART adapter는 별도 회사 검증·계정 변환을 가지며, 공통 보존 원칙과 `RawDatasetStore` 재사용을 검토한다.
가격·QGV 재점수·예약 workflow·Pages 자동 공개 연결은 이 준비 문서의 범위 밖이다.
2026-10-09 변경된 전제에서 주가 원자료·가격 기반 V/시총 순위는 개인 경로로만 취급하며,
**SEC·DART 공개 재무 자료의 기존 공개 입력 경로는 유지**한다. 이 문서의 공개 조건은 재무 자료에 관한 것이다.

## 1. 공식 API와 회사 결속

아래 사실은 공개 개발가이드에서 확인했다. **실제 한미 API 응답·계정 ID·금액은 미검증**이다.
[기업개황](https://dart.fss.or.kr/dsae001/selectPopup.ax?selectKey=00161383)은 한미반도체(주), 042700, 유가증권시장, 12월 결산을 표시한다.
후속 구현은 [고유번호 목록](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019018)의
`corp_code`↔`stock_code`를 대조하고 그 근거를 보존한다. 공개 웹 확인을 인증 API 검증으로 승격하지 않는다.

| 용도 | API와 공식 계약 | 준비 문서의 사용 규칙 |
| --- | --- | --- |
| 정기공시·정정 목록 | [공시검색](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001), `/api/list.json`; `corp_code`, 접수 기간, `last_reprt_at`, 공시 종류와 페이지 조건 | 회사 고정, `last_reprt_at=N`으로 정정 포함 전체 목록. 선택 범위의 모든 페이지를 확인하며 부분 목록을 전체 이력으로 표시하지 않는다. |
| 숫자 원문 | [단일회사 전체 재무제표](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020), `/api/fnlttSinglAcntAll.json` | 필수 입력은 `crtfc_key`, `corp_code`, `bsns_year`, `reprt_code`, `fs_div`. 2015년 이후. BS/IS/CIS/CF/SCE 계정과 통화를 받는다. |
| 보완 숫자 근거 | [단일회사 주요계정](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019016), `/api/fnlttSinglAcnt.json` | key/corp/year/report 입력, `fs_div` 입력 없음. 응답에는 연결/별도·종목코드·당기일자 등이 있으나 `account_id`는 없다. 보완 시 전체 API와 접수번호·기준을 대조하고 별도 snapshot으로 결속한다. |
| 계정 정의 | [XBRL 택사노미](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2020001), `/api/xbrlTaxonomy.json` | 입력은 key와 양식별 `sj_div`. 응답의 `bsns_de`는 적용 기준일이며 날짜 선택 입력이 아니다. 취득 taxonomy·mapping 버전을 보존한다. |
| 제출본 확인 | [DART 공시 원문](https://dart.fss.or.kr/), 접수번호별 열람 | 숫자·기간 근거 확인과 출처 링크에 사용한다. XBRL/주석 parser·전문 복제는 첫 숫자 adapter 범위에 넣지 않는다. |

**숫자 API에는 `rcept_no` 요청 인자가 없다.** 반환되는 `rcept_no`를 공시 목록에 결속해야 한다.
목록의 과거 접수번호를 알고 있어도 숫자 API로 그 제출본을 지정해 다시 받을 수 있다고 가정하지 않는다.
항상 최신 정정본을 반환한다는 상세 선택 규칙도 공개 가이드에서 확인되지 않았다.
원문/XBRL API의 접수번호 입력과 숫자 API의 계약을 혼동하지 않는다. 관측한 숫자 원문을 보존하는 방식으로 시작한다.

공시검색 `rcept_no`는 14자리, `rcept_dt`는 YYYYMMDD **일자**다.
`report_nm`의 `[기재정정]`·`[첨부정정]`·`[첨부추가]`, `rm`의 `정`(후속 정정 존재)·`철`(철회)을 원문 그대로 남긴다.
`last_reprt_at=Y`는 전체 정정 이력을 보존하는 검색으로 쓰지 않는다. A001/A002/A003 공시검색 분류는 아래 숫자 보고서 코드와 다른 체계다.
숫자 응답의 접수번호가 선택 목록에 없거나 회사·보고서 종류·사업연도 결속이 모호하면 `NOT_AVAILABLE`이다.

## 2. 제안 입력 계약과 PIT

`DART_M1_INPUT`, `DART_M1_RETENTION`, 아래 상태·키 이름은 **후속 구현용 후보 계약**이며 현재 런타임에 등록된 형식이 아니다.
SEC M1과 같은 envelope 구조를 사용하되 DART 고유번호를 SEC CIK로 바꾸거나 `hanmi`를 US17에 추가하지 않는다.
모든 정규화 datetime은 timezone이 있는 UTC ISO8601이며, 원래 일자/기간명 문자열도 별도로 보존한다.

| 계약 부분 | 필드와 의미 |
| --- | --- |
| 버전·회사 | `contract`, `version=1`, `company_id=hanmi`, `exchange=KRX`, `stock_code=042700`, `corp_code=00161383`. 문자열의 선행 0 보존. |
| 안전한 요청 문맥 | `request.bsns_year`, `request.reprt_code`, `request.fs_div` 및 선택한 목록 범위·페이지 완전성. `crtfc_key`와 인증 요청 URL은 포함하지 않는다. |
| 상태 | `status=READY / NOT_AVAILABLE`. READY는 지정 묶음의 **입력·보존 검증 완료**이며 QGV 완료가 아니다. 필드별 `MAPPED / NOT_AVAILABLE / NOT_COMPARABLE`과 사유를 별도 기록한다. |
| 시각 | `as_of`, `acquired_at`, `availability.available_at`, `availability.published_at=null`, `availability.basis=OBSERVED_PUBLIC_API_UPPER_BOUND`, `precision=CONSERVATIVE`, `historical_first_publication=false`. |
| 원문·정정 | `filings`, `revision_candidates`, `selected_input_facts`, `excluded`. 접수번호·접수일·정정 표기·원래 행·선택/제외 사유를 보존한다. |
| QGV 입력 후보 | `raw_fundamentals`: 아래 매핑을 검증한 nullable 필드. `source_kind=OBSERVED_RAW_INPUT`, `reporting_currency=KRW`, 검증된 `period_quality`와 mapping 버전. 전체 묶음 실패 시 null. |
| 검증 수준 | receipt의 `real_data_verified=false`, `full_pit_historical=false` 유지. 보존 검증을 전체 과거 빈티지나 자동 QGV 연결 성공으로 표시하지 않는다. |

`acquired_at`은 결속된 숫자·목록·필수 보완 근거의 취득 완료 시각 중 가장 늦은 값이다.
READY의 `availability.available_at`과 선택 가능한 fact별 `available_at`은 이 `acquired_at`으로 둔다.
NOT_AVAILABLE 묶음의 envelope `available_at`은 null로 남기고 후보의 취득 경계는 제외 trace에 보존한다.
오프라인 import의 취득 시각은 운영자가 제공한 주장으로 표시하며 독립적인 최초 공개 증명이 아니다.
`observed_at=acquired_at`, 입력 stamp의 `estimated=true`, `estimation_method=OBSERVED_PUBLIC_API_UPPER_BOUND`로 둔다.
`rcept_dt`를 00:00 공개 시각으로 만들지 않는다. 공개 가이드에 없는 접수 시각을 `accepted_at`에 추정해 채우지 않는다(null).
`as_of < acquired_at`이면 해당 원문은 사용할 수 없다. 제출일·재무 기간이 과거여도 취득 이전 cutoff로 소급하지 않는다.
필요 근거 중 하나가 cutoff 이후이면 파생값도 사용할 수 없다. 순서가 모호한 정정은 접수번호 숫자 크기로 정렬해 확정하지 않는다.

legacy [DataStamp](../../src/investment_system/contracts/models.py)는 `published_at`에 datetime을 요구한다.
SEC M1처럼 이 준비 JSON의 null 공개 시각은 legacy 객체와 구분한다. 편의상 취득 시각을 `published_at`에 복사해 연결하지 않는다.

### 재무 범위·기간·금액

| 원본/문맥 | 보존·정규화 규칙 |
| --- | --- |
| `reprt_code` | Q1 `11013`, 반기 `11012`, Q3 `11014`, 사업 `11011`. `bsns_year`는 보고서 사업연도이며 비교열의 경제적 기간을 대신하지 않는다. |
| `fs_div` | CFS=연결, OFS=별도. 처음 검증할 묶음은 연간 CFS를 제안한다. CFS 결측을 OFS로 자동 대체하지 않는다. OFS는 별도 묶음·별도 포인터이며 명확한 기준 표시가 필요하다. |
| 전체 API의 scope | `fs_div`, `stock_code`, `rcept_dt`, `thstrm_dt`는 전체 API의 문서화된 응답 필드가 아니다. `fs_div`는 검증한 요청 문맥에서 기록하고 `scope_source=REQUEST_PARAMETER`로 표시한다. 날짜·종목을 없는 응답 필드에서 읽지 않는다. |
| 계정 | `sj_div`, `sj_nm`, `account_id`, `account_nm`, `account_detail`, `ord` 보존. `account_detail`은 SCE에만 출력하는 계약이다. 행 순서를 항목 ID로 사용하거나 IS/CIS 중복을 합산하지 않는다. |
| 당기 | `thstrm_nm`, `thstrm_amount`, `thstrm_add_amount`. 분·반기 IS/CIS의 `thstrm_amount`는 3개월, add는 누적이라는 가이드 구분을 적용한다. CF와 BS를 같은 3개월 값으로 간주하지 않는다. |
| 비교열 | `frmtrm_nm`, `frmtrm_amount`, `frmtrm_q_nm`, `frmtrm_q_amount`, `frmtrm_add_amount`, `bfefrmtrm_nm`, `bfefrmtrm_amount`. 전전기 금액은 사업보고서 출력이다. 현재 보고서에 실린 재작성 비교값의 vintage는 현재 취득본이며 과거 최초 보고값이 아니다. |
| 기간 근거 | `period_start/end`, `period_basis=ANNUAL / QUARTER_STANDALONE / YTD / INSTANT`, `fiscal_year`, `fiscal_period`, `period_evidence`를 각 fact에 붙인다. 12월 결산과 보고서 코드만으로 모든 역사 기간을 확정하지 않는다. 해당 제출본 또는 접수번호가 일치하는 보완 응답에서 기간을 검증하지 못하면 `PERIOD_UNVERIFIED`로 매핑 보류한다. |
| 분기 파생 | CF YTD→단독 분기, Q4=연간−Q1~Q3는 최초 매핑에서 자동 생성하지 않는다. 필요하면 동일 기준·기간·통화·정정 vintage의 모든 피연산자와 차감 규칙을 별도 검증·결속한다. |
| 금액·단위 | 원래 문자열, 부호, `currency`, `unit`, `scale`, 정규화값과 근거를 보존한다. KRW·원 단위 기대를 실제 보장으로 쓰지 않는다. 천원/백만원·주당/주식수와 KRW 금액을 혼합하지 않으며 scale/통화 미확인 항목은 null이다. 통화 변환·USD 기본값 사용은 금지한다. |
| 숫자 문법 | 확인된 쉼표·부호·소수 표기만 파싱하고 원문을 보존한다. 괄호 음수 지원은 실제 계약 확인 없이 추정하지 않는다. 빈칸·`-`·N/A는 결측, 명시적 0은 유효한 0. 비유한수·잘못된 문법은 제외한다. |

경제적 fact 키는 회사/scope/통화·단위/statement/계정 ID·승인한 확장계정/detail/**실제 기간·period_basis**다.
접수번호는 revision 식별이며 경제적 키에 넣어 정정 전후를 서로 다른 항목으로 숨기지 않는다.
같은 사실의 복수 값이 상충하면 오래된 값으로 fallback하지 말고 해당 항목을 보류한다.
IS/CIS·연결/별도·당기/누적의 우선순위는 명시적인 mapping 버전으로 관리한다.

## 3. 계정과목 → QGV 입력 매핑 후보

대상 필드명은 기존 [RawFundamentals](../../src/investment_system/contracts/raw.py)와
[SEC 변환기](../../src/investment_system/providers/sec_companyfacts.py)를 따른다.
아래 **계정 의미는 후보이며 한미의 실제 account_id 허용 목록은 아직 0개**다.
계정명 단순 포함 검색으로 승인하지 않는다. 공식 taxonomy·실제 응답의 ID/label/기준일·표·scope·단위·기간을 함께 대조한 mapping manifest가 필요하다.
비표준 ID `-표준계정코드 미사용-`는 모든 확장계정을 하나로 묶는 ID가 아니다. 검증한 회사별 이름·상세·표·정의에만 별도 매핑한다.
택사노미의 BS1 등 양식 코드와 숫자 응답의 BS/IS/CIS/CF/SCE는 다른 체계다. taxonomy 취득만으로 모든 역사 계정 정의가 검증되지는 않는다.

| QGV raw 필드 | 계정 의미·statement 후보 | 수락 조건 / 보류 규칙 |
| --- | --- | --- |
| `revenue`, `revenue_prev` | IS/CIS 매출액·수익과 비교기간 매출 | 승인한 동일 개념·연결 기준·통화·동일 길이의 실제 기간. FY/YTD/단독 분기를 교차 비교하지 않는다. 비교열의 재작성 여부와 vintage를 명시한다. |
| `ebit`, `ebit_prev` | IS/CIS 영업이익(손실) | 현행 SEC의 OperatingIncomeLoss 입력에 대응하는 **영업이익 proxy**로만 표시한다. 이를 세전손익이나 정확한 EBIT로 바꾸지 않는다. 당기/전기 동일 정의가 검증되지 않으면 각각 null. |
| `net_income` | IS/CIS 당기순이익(손실) | 지배기업 소유주 귀속 vs 비지배지분 포함 전체를 기록한다. 계정명만으로 귀속 범위를 선택하지 않는다. `equity`와 scope 정합성 검증 전 사용 보류. |
| `equity` | BS 자본총계 또는 소유주 귀속 자본 | 시점 값이며 선택한 귀속 범위를 명시한다. 총자본과 부모 소유주 지분을 혼합하지 않는다. |
| `cash` | BS 현금및현금성자산 | 시점·KRW 단위 검증. 단기금융상품 등 별도 자산을 임의 합산하지 않는다. |
| `fcf` | CF 영업활동 현금흐름과 유형자산 취득 현금유출 | 현행 SEC 후보 정의 `CFO − abs(PPE 취득 capex)`와 동일한 기간·scope·단위일 때만 계산한다. capex가 취득 유출인지 검증하고 처분액/net 투자현금흐름·M&A·무형 취득을 자동 섞지 않는다. 피연산자 중 하나라도 없으면 null, 식·fact ID·최대 available_at을 trace로 남긴다. |
| `total_debt` | BS 차입금·사채·유동성 장기부채·리스 등 후보 구성 | **초기 매핑은 null / DEBT_BASIS_UNRESOLVED**. 총부채를 넣지 않는다. 현행 SEC는 LongTermDebt/LongTermDebtNoncurrent 선택값이므로 DART의 전체 이자부채와 동등하다고 가정하지 않는다. 비교 범위 확정 전 financial_health에 연결하지 않는다. |
| `invested_capital` | 자본·채무 기반 파생 후보 | **초기 null**. 현행 SEC의 equity+debt 또는 equity fallback을 정확한 투하자본으로 승격하지 않는다. 채무·귀속 범위와 적용 정의 검증 전 ROIC 연결 보류. |
| `shares` | 기말 보통주 유통주식수 후보 | **검증 전 null**. 발행주식·자기주식·기말 유통·EPS 가중평균주식수를 구분한다. EPS의 가중평균 분모를 기말 shares로 넣거나 미검증 차감으로 만들지 않는다. |
| `eps`, `eps_prev` | IS/CIS 기본/희석 주당이익 | KRW/주·주식 종류·기본/희석·기간·split/재작성 기준을 동일하게 검증한다. 기본과 희석을 비교기간 사이에 조용히 교체하지 않는다. 확인 불가 시 null. |
| `reporting_currency`, `period_quality`, `source_kind`, `profile_kind` | 재무 문맥 | KRW, 검증된 기간 상태, OBSERVED_RAW_INPUT, 기존 GENERAL_CORPORATE 후보. RawFundamentals의 USD/SYNTHETIC 기본값을 사용하지 않는다. |
| 나머지 nullable raw 필드 | 시장/금리·동종업계·루브릭·밸류에이션·금융업 전용 입력 | 가격, DCF, WACC, market share, peer/industry, rubric, multiples, FINANCIAL 확장 등은 이 API만으로 채우지 않는다. null과 사유 유지. DART 수치가 생겨도 완전한 Q/G/V 입력이 아니다. |

각 선택 fact의 trace는 `rcept_no`, request scope, 원본 row 위치·`ord`, 계정 식별/상세, 선택 금액 열,
원문값·단위·scale·기간·귀속 범위, mapping 버전, 원문 SHA256, available_at과 변환/파생식을 포함한다.
직접값과 파생값, 정정으로 바뀐 값과 mapping만 바뀐 값을 구분한다.

**QGV 소비 gate는 열지 않는다.** 현행 [raw_map](../../src/investment_system/qgv/raw_map.py)은 통화·period_quality·estimated를 자체 검증하지 않고 비율을 계산한다.
EPS 미확보 시 `_yoy(raw.fcf, raw.revenue_prev)` fallback도 있어 이를 올바른 FCF 성장으로 간주하면 안 된다.
이 문서는 수식/소비기를 수정하지 않는다. 코덱1은 준비 JSON을 검증 없이 `map_raw`에 넘기거나 공개 점수로 재계산하지 않는다.

## 4. 정정 lineage와 보존 receipt

`filings`에는 원래 목록 행을 보존하고, `revision_candidates`에는 formal correction 종류·철회·숫자 원문 변화의 근거와 제외 사유를 둔다.
`formal_amendment`는 실제 `[기재정정]`/`[첨부정정]` 표기 근거로만 기록한다.
`rm=정`만으로 그 행 자체를 정정본으로 바꾸거나 `[첨부추가]`를 숫자 정정으로 승격하지 않는다.
원본 부모 접수번호 필드는 목록 계약에 없으므로 `parent_rcept_no=null`을 기본으로 둔다.
같은 회사·제목·사업연도 또는 접수번호 순서만으로 부모를 만들지 않는다. 같은 접수번호의 payload 변경은 `OBSERVED_PAYLOAD_REVISION`이며 공식 정정이라는 증거가 아니다.
철회된 제출본은 역사 원문을 유지하되 새 READY 선택에서 제외한다. 같은 날 정정의 순서를 입증하지 못하면 선택을 보류한다.

| 보존 요소 | SEC M1과 같은 원칙을 적용한 DART 제안 |
| --- | --- |
| immutable inputs | 숫자 JSON과 목록의 원래 응답 byte·모든 필요한 페이지, 회사 매핑·기간/단위·taxonomy 보완 근거를 결속한다. 원문 ID는 `dart_m1_{kind}:{corp_code}:{full_sha256}` 계열로 SEC와 분리한다. |
| descriptor | `artifact_id`, `sha256`, `bytes`, `source_kind`, key 없는 `source_url`, 안전한 `source_params`, 개별 취득 시각. 저장/읽기 모두 ID 형식·필드 타입·hash·크기·회사 결속을 확인한다. |
| receipt core | `contract`, `version`, `input`, `inputs`를 결정적 직렬화하여 receipt ID를 만든다. input에 request·as_of·취득 경계·mapping 버전을 포함한다. 같은 byte라도 기준/버전이 달라지면 다른 receipt다. |
| lineage | `revision_parent_receipt_id`는 이전의 **검증된 READY 관측 receipt**와 연결한다. 이는 부모 공시 접수번호와 다른 관계다. 변경 종류는 초기/원문 revision/cutoff·관측 변경/mapping 변경/사용 불가 시도로 구분하고 before/after fact trace를 보존한다. |
| 저장·포인터 | 기존 blobs/manifests 보존 형태를 검토하되 DART receipt/포인터는 별도 namespace로 둔다. 회사·bsns_year·실제 기간 키·CFS/OFS·보고서 코드·period_mode별 포인터로 서로를 덮어쓰지 않는다. lock → 전체 원문 저장/검증 → receipt 원자적 기록/검증 → READY 포인터 원자적 교체 순서다. |
| 재실행·회귀 | 동일한 원문·안전한 요청 문맥·취득/cutoff·mapping 버전은 기존 receipt를 검증해 재사용한다. 오래된 취득 또는 cutoff가 최신 포인터를 되돌리지 않도록 두 시각을 모두 비교한다. mapping rollback도 명시적으로 승인한 버전 정책 없이 최신 포인터에 반영하지 않는다. |
| replay | 최신 API 재조회 대신 보존한 byte와 당시 mapping으로 재생한다. mapping이 변하면 새 receipt를 만들고 이전 결과를 덮어쓰지 않는다. 취득 이전 cutoff는 NOT_AVAILABLE. 부분/변조된 원문·manifest·receipt·쓰기 중단은 이전 READY 포인터를 보존한다. |

로컬 receipt 검증은 byte 보존·결속의 증거이며 독립 백업 존속이나 과거 최초 공개의 증거가 아니다.
숫자 API에 과거 접수번호를 지정할 수 없고 정정 전 값의 복원을 확인하지 못했으므로, 첫 취득 이전 vintage의 Full PIT historical 복원을 약속하지 않는다.
입력 검증을 통과해 일부 raw 필드가 있어도 metric별 결측을 유지하며 READY를 모든 QGV 필드 완전성으로 해석하지 않는다.

## 5. 실패 처리와 Secret 경계

HTTP 성공과 DART body `status=000`을 **함께** 확인한 뒤 schema·목록 결속·단위/기간/매핑을 검증한다.
HTTP 200만으로 성공하지 않으며, 공개 가이드는 HTTP 코드와 body status의 대응이나 retry 간격을 보장하지 않는다.
아래 대응은 공식 status 의미에 근거한 **후속 구현 정책 제안**이다.

| 실패 | 대응 |
| --- | --- |
| 키 미등록, `010`/`011`/`012`/`901` | 미등록 키/사용 불가 키/IP 거부/보유기간 만료. 중단하고 등록·권한·IP 조건을 확인한다. 무한 retry·다른 키/프록시로 우회하지 않는다. |
| `013`/`014`, 또는 정상 status지만 필요한 행 없음 | 조회 데이터 없음/파일 없음. NOT_AVAILABLE과 사유를 남긴다. 0·합성값·다른 회사·표시 없는 OFS로 채우지 않는다. |
| `020` | 한도 초과. 작업 중단·재개 시각 확인. 키별/전체 호출 예산을 관리하고 단순 즉시 retry하지 않는다. |
| `021`/`100`/`101` | 회사 수/필드 값/접근 부적절. 요청·권한 오류로 분류하고 수정 전 반복하지 않는다. 한 회사 범위를 확장해 해결하지 않는다. |
| `800` | 시스템 점검. 중단/후속 확인. 예정 종료 시각을 호출 성공으로 기록하지 않는다. |
| transport/429/5xx, `900` | 정의되지 않은 오류는 transient라고 단정하지 않는다. 원인 분류 후 bounded backoff·Retry-After·총 시도 제한을 검토한다. 한도/인증 실패와 같은 retry 정책으로 묶지 않는다. |
| malformed JSON/회사 결속 오류/혼합 접수번호/부분 목록/기간·단위·계정 충돌 | 전체 또는 해당 metric을 fail closed. 결속 자체가 실패하면 READY 생성 금지. 기존 포인터와 안전한 역사 원문 보존, 제외 사유 명시. |
| 원문/receipt 변조·쓰기 중단·lock 충돌 | 기존 READY 유지. 손상된 보존 기록을 자동 덮어쓰지 않는다. 실패 한 건이 다른 기간의 처리 상태를 성공으로 바꾸지 않는다. |

일반 개인 한도는 전체 API 합산 일 20,000건이며 키별 설정이 다를 수 있다.
[한도 FAQ](https://opendart.fss.or.kr/cop/bbs/selectArticleDetail.do?bbsId=B0000000000000000002&nttId=29)의 분당 1,000회 제한 가능성을 안전한 허용 속도로 간주하지 않는다.
키 소유자·기업 IP/hosted runner 조건은 기존 조사에서 미확인으로 남아 있다. 이 문서는 가입·runner 설정·예약 실행을 승인하지 않는다.

`DART_API_KEY`는 후속 실행의 runtime Secret에서만 사용하고 CLI 인자·정적 웹·파일·커밋·PR에 넣지 않는다.
API 필수 `crtfc_key`가 들어간 실제 요청 URL·headers·환경·예외 repr·response message를 로그나 receipt에 복사하지 않는다.
출처에는 key 없는 endpoint와 허용된 회사/연도/보고서/scope 파라미터만 남긴다.
Secret이 포함될 가능성이 있는 에러 body는 원문 아카이브 대상에서 제외하고 안전한 코드/상태만 기록한다.
정상 후보 body도 저장 전에 Secret 노출 여부를 검사하고 검출되면 보존·출력을 차단한다.
transport/인증 실패는 원문 없는 구조화 실패 결과로 남기며 보존 검증 완료 receipt를 위조하지 않는다.
로그·CI·PR·공개 산출물은 Secret **이름·존재 여부** 외 값을 절대 출력하지 않는다. 실제 키로 테스트 fixture를 만들지 않는다.

## 6. 출처 표시와 공개 경계

출처·가공 권리의 기본 근거는 [병합된 KR/JP 조사](../fundamentals_sources/KR_JP_FILINGS_RESEARCH.md)의 DART 절을 재사용한다.
[공개·활용 FAQ](https://opendart.fss.or.kr/cop/bbs/selectArticleDetail.do?bbsId=B0000000000000000002&nttId=26)는
“공익이나 타인의 권리를 침해하지 않는 선에서 데이터의 공개 및 활용은 제한되지 않습니다.”라고 설명한다.
[이용약관](https://opendart.fss.or.kr/intro/terms.do) 제19조의 제3자 인증키 이용 금지와 데이터 재이용은 구분한다.
이 근거는 주석·사진·제3자 표현 전체의 무제한 복제 허가가 아니다. 이번 준비 PR은 가공 데이터 공개를 실행하지 않는다.

후속 표시/가공 JSON에는 **금융감독원 DART/OpenDART**, 한미반도체·KRX 042700·고유번호,
접수번호·보고서명·접수일, 사업연도/기간·연결/별도·계정·통화/단위/scale,
취득 시각·보수적 available_at·공개 시각 미확인·mapping 버전·가공 주체·정정/재작성/결측 상태를 표시한다.
출처 링크는 `https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}` 계열의 key 없는 공시 열람 링크다.
현재 취득본의 재작성 비교열을 과거 당시 값으로 표기하지 않고, 원문값과 파생 FCF/proxy 영업이익을 구분한다.
이는 프로젝트의 추적 가능성 규칙이며 FAQ의 별도 표시 의무라고 과장하지 않는다.
공개 여부는 별도 산출물/권리 gate를 거치며 원문 아카이브·개인 Secret을 Pages에 연결하지 않는다.

## 7. 코덱1 인수 검증 목록

문서 PR 병합 이후에도 구현은 코덱1 작업이며 아래는 구현 PR에서 검증할 항목이다. 실제 수집 성공이나 구현 완료를 선언하는 목록이 아니다.

- 점검 실제 종료와 사용자의 `DART_API_KEY` 등록 확인; 이름·존재만 확인하고 값 노출 금지.
- 회사 매핑·CFS/OFS·연간/분기/누적·KRW/scale·계정 ID와 확장계정의 실제 근거 확보. 검증된 mapping manifest와 미확인 항목 목록 제시.
- 취득 직전 cutoff 차단, 같은 날 정정 순서 모호함, 동일 접수번호 payload 변경, 철회·정정 후보와 부모 미확정 테스트.
- 비교열 재작성·중복 IS/CIS·CFS/OFS 오염·누적/단독 혼합·명시적 0/결측·unit/sign/ownership 오류 검증.
- deterministic receipt/replay, mapping 변경, 원문/manifest/receipt 변조, 부분 목록·쓰기 중단·오래된 import의 포인터 보존 검증.
- 실제 Secret 없는 synthetic fixture와 mock transport로 인증/한도/점검/transport 실패·민감 URL/예외 로그 차단 검증.
- 준비 JSON과 legacy DataStamp/QGV 소비 경계를 확인하고, KR_DEFERRED·US17·가격·예약·Pages 연결을 이번 adapter 범위와 분리.

공식 웹 재조회: 2026-10-09. 숫자·목록·택사노미 가이드와 기업개황을 키 없이 읽었다.
공식 계정표 연결은 금감원 홈페이지 중단 안내로 이동했으며 한미 실제 account_id·금액·인증 성공은 검증하지 않았다.
최초 준비 문서의 불확실한 계정·단위·운영 조건을 승인된 사실로 채워 구현하지 않는다.
