# GSQ-011 Macro 1차 4축 — 코덱1 구현 명세

작성: **2026-10-10 UTC**, 읽기 기준 canonical `8d7fcb55728920a4d9d8f39023c1b4d566cd3e13`. 채택 근거: [26E GSQ-011](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md#gsq-011--26e-원기관-macro-4축holdout-보호-확인개인-m3-부분집합-결정-2026-10-10-utc).

**Goal:** BLS CPI/Labor, Treasury 금리, BEA GDP의 직접 입력을 정규화하고 가용 시각·빈티지를 분리해 8축×6상태에 원자료 근거와 미구현 상태를 전달한다.
**Architecture:** 고정 source registry → 순수 request plan → supplied body parser → 취득/발표/빈티지 sidecar → cutoff selector → 48칸 evidence view. 첫 PR은 offline 합성 입력 경계이며 네트워크 transport·저장·운영/공개 연결은 후속이다.
**Stack:** 기존 Python, frozen dataclass, `Decimal`, `datetime/zoneinfo`, `json`, `hashlib`, `xml.etree.ElementTree`, pytest. 기존 dependency만 사용한다.

사용자가 원기관 4축을 채택했지만 새 Direction/Momentum/Surprise/Stress/Confidence 규칙·가중치를 승인하지 않았다. 기존 Macro v0.1.1과 v0.1.4-CANDIDATE를 바꾸지 않는다. FRED/ALFRED는 서면 허가 전 차단하며 fallback·import·request plan도 만들지 않는다. QGV v2는 보류이며 Holdout을 선택/조회/사용하지 않는다. 아래는 **후속 code PR의 작업 명세**이고 이번 문서 작성은 코드·테스트·워크플로·실제 API를 실행/수정하지 않는다.

## 1. 파일과 구현 순서

| 단계 | 후속 code PR write-set | 함수/책임 |
| --- | --- | --- |
| A | 신규 `implementation/src/investment_system/macro/primary_contract.py` | 아래 불변 타입·고정 axis/dimension/series registry·reason codes |
| B | 신규 `implementation/src/investment_system/providers/macro_primary.py` | `build_bls_plan`, `build_bea_plan`, `build_treasury_plan`; `parse_bls`, `parse_bea_nipa`, `parse_treasury_yields` |
| C | 신규 `implementation/src/investment_system/macro/primary_input.py` | `select_observed_vintages`, `build_evidence_grid` |
| D | 신규 `implementation/tests/test_macro_primary_input.py` | §7의 합성 요청/응답·PIT·48칸·무부작용 테스트 |
| E | 신규 `implementation/docs/macro_data_rights/PHASE1_VERIFICATION.md` | 실행 명령·결과·범위·미완료를 기록. 값/키/원 payload dump 없음 |

기존 `macro/engine.py`, `providers/fred_*`, shared `contracts/models.py`, `versions.py`, producer/adapter/registry, public builder, Web, workflow, 기존/frozen test는 수정하지 않는다. 새 모듈을 직접 import한다. 저장·HTTP client·실제 BEA 키 등록/확인·Secrets·외부 builder 연결을 새 모듈에 숨겨 넣지 않는다. 별도 review를 거친 code PR은 병합 대기로 인계하며 문서 자체 병합 권한을 적용하지 않는다.

## 2. 확정 request contract와 입력 식별

이 표의 endpoint는 **요청 설계**다. 이번에 실제 통계 endpoint를 호출하지 않았다. 선택 연도는 후속 호출자가 명시하며 `now()`·전체 이력·Holdout 기간을 default로 정하지 않는다.

| 입력/축 | endpoint·요청 | 정확한 ID와 해석 |
| --- | --- | --- |
| BLS Inflation | `POST https://api.bls.gov/publicAPI/v1/timeseries/data/`; JSON `seriesid`, `startyear`, `endyear` | `CUSR0000SA0`: CPI-U All items, U.S. city average, **SA**, index `1982-84=100`. `CUUR0000SA0`: 동일 **NSA**. 서로 다른 series이며 혼합·자동 대체하지 않는다. |
| BLS Labor | 위 같은 batch | `CES0000000001`: Total nonfarm all employees, **SA, thousands**. `LNS14000000`: CPS unemployment rate, **SA, percent**. 두 통계는 단위/조사 범위가 다르며 합성 Labor 수치를 만들지 않는다. |
| BEA Growth | `GET https://apps.bea.gov/api/data`; `UserID=<runtime injected>`, `method=GetData`, `DataSetName=NIPA`, `TableName=T10106`, `Frequency=Q`, `Year=<explicit years>`, `ResultFormat=JSON` | Table 1.1.6 Real GDP, `LineNumber="1"`. `SeriesCode`와 `LineDescription`, `Metric_Name`, `CL_UNIT`, `UNIT_MULT`, Notes를 response에서 보존/검사한다. GDP의 기준연도·scale를 고정 추정하지 않는다. |
| BEA GDP 공표 변동 근거 | 별도 `TableName=T10101`, 나머지 동일 | Table 1.1.1, `LineNumber="1"`: BEA가 공표하는 real GDP change. Q의 annualized percent와 YoY·fraction은 다르다. 공식 값 그대로 보조 근거로 보존하며 Growth score/Direction 계산에 자동 연결하지 않는다. |
| Treasury Monetary Policy/금리 | `GET https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml`; `data=daily_treasury_yield_curve`, `field_tdr_date_value=<explicit year>` | Daily Treasury Par Yield Curve의 `NEW_DATE`와 `BC_10YEAR`, percent. 이것은 정책목표/Fed funds 금리가 아니다. `DGS10`을 이름만 바꾼 동일 입력이라고 claim하지 않는다. |

**Source ID**는 각각 `BLS:<seriesID>`, `BEA:NIPA:<TableName>:1:Q`, `TREASURY:daily_treasury_yield_curve:BC_10YEAR`다. BEA `LineNumber`는 **반환된 table의 선택 필드**이며 NIPA GET 요청의 parameter로 추가하지 않는다. obsolete `TableID`, 암묵적 `Year=ALL/X`, 여러 table 한 요청은 금지한다. 연도 범위/목록은 정수·중복·순서·provider 한도를 검증해 fixed plan을 만든다.

BLS 1차는 키 없는 v1이다: 25 queries/day·25 series/query·10 years/query, 공통 50 requests/10sec 조건을 유지한다. 네 series를 한 batch로 요청할 수 있으나 parser가 누락 series를 성공으로 채우지 않는다. 등록 v2(`.../v2/timeseries/data/`, `registrationkey`)는 후속 경로이며 자동 전환/키 탐색은 없다. BEA는 무료 등록 UserID가 필요하고 미주입은 `KEY_NOT_CONFIGURED`; 값·존재 여부를 이번 작업에서 확인하지 않는다. 문서상 100 requests/min·100MB/min·30 errors/min 등 동적 제한과 HTTP429/Retry-After를 후속 transport가 준수한다. 무한 재시도·계정 분산·FRED 대체는 없다.

Treasury 공식 developer 문서는 위 **`resource-center/data-chart-center`** 경로를 안내한다. ‘all’에는 page 증가 및 빈 `entry` 종료가 필요하지만 1차 plan은 **연도 하나만 명시**하고 자동 전 기간 pagination을 만들지 않는다. namespace URI는 Atom `http://www.w3.org/2005/Atom`, data `http://schemas.microsoft.com/ado/2007/08/dataservices`, metadata `http://schemas.microsoft.com/ado/2007/08/dataservices/metadata`로 다룬다. prefix 문자 `d/m`에 의존하지 않는다. `m:null=true`·`N/A`·누락은 결측이며 0%로 바꾸지 않는다. `NEW_DATE`/`BC_10YEAR`·namespace는 명세의 parser target으로 고정하되 현재 feed 응답/전체 필드 coverage는 미실측이다. 후속 schema 확인에서 다른 형태이면 `SCHEMA_MISMATCH`로 중단하고 실제 값 fixture를 공개하지 않는다.

## 3. 타입과 정확한 함수 경계

아래는 새 sidecar이며 기존 MacroSnapshot이나 DataStamp에 필드를 추가하지 않는다. 타입은 `@dataclass(frozen=True)`, payload/values는 `repr=False`다. timestamp는 모두 aware이며 URL은 credential/query 값 없는 source endpoint만 보존한다.

| 타입 | 필드 |
| --- | --- |
| `SourceReceipt` | `provider: Literal["BLS","BEA","TREASURY"]`; `source_url, response_sha256: str`; `acquired_at: datetime`; `synthetic: bool`; `rights_status: Literal["CLEARED_SCOPE","UNCONFIRMED"]` |
| `ReleaseMetadata` | `release_at: datetime | None`, `release_evidence_ref: str | None`, `evidence_kind: Literal["PUBLISHED_ARTIFACT","SCHEDULE","UNVERIFIED"]`; `estimate_kind: Literal["INITIAL","ADVANCE","SECOND","THIRD","REVISED","UNKNOWN"]`; `revision_parent: str | None` |
| `MacroObservation` | `observation_id, source_id, axis, observation_period, frequency, unit, seasonal_adjustment: str`; `value: Decimal`; `unit_multiplier: int | None`; `metric_name: str | None`; `source_series_code: str | None`; `source_notes: tuple[str,...]`; `source_response_sha256: str`; `available_at, vintage_at, ingested_at: datetime`; `release: ReleaseMetadata`; `availability_basis: Literal["OBSERVED_CAPTURE_UPPER_BOUND"]`; `vintage_kind: Literal["OBSERVED_CAPTURE"]`; `synthetic: bool`; `quality_flags: tuple[str,...]` |
| `ParseResult` | `state: Literal["INPUT_RESEARCH","NOT_AVAILABLE"]`, `observations: tuple[MacroObservation,...]`, `reason_codes: tuple[str,...]`, `missing_source_ids: tuple[str,...]`, `synthetic: bool` |
| `RequestPlan` | `provider, method, endpoint: str`; `public_parameters: tuple[tuple[str,str],...]`; `body: bytes | None` (`repr=False`); `credential_slot: Literal["BEA_USERID"] | None`; `state: Literal["PLANNED","NOT_AVAILABLE"]`; `reason_codes: tuple[str,...]` |
| `MacroCell` | `axis, dimension: str`; `state: Literal["RAW_EVIDENCE","NOT_AVAILABLE"]`; `evidence_ids: tuple[str,...]`; `reason_codes: tuple[str,...]`; `value: None = None` (축 합성 점수 없음) |
| `MacroEvidenceGrid` | `contract: Literal["MACRO_PRIMARY_INPUT/1"]`, `as_of: datetime`, `state: Literal["INPUT_RESEARCH","NOT_AVAILABLE"]`; `cells: tuple[MacroCell,...]`; `observations: tuple[MacroObservation,...]`; `pit_status: Literal["OBSERVED_BOUND_ONLY","NOT_VERIFIED"]`; `model_status: Literal["NOT_APPLIED"]`; `missing_source_ids, reason_codes: tuple[str,...]` |

```python
def build_bls_plan(series_ids: tuple[str, ...], start_year: int, end_year: int) -> RequestPlan: ...
def build_bea_plan(table_name: str, years: tuple[int, ...]) -> RequestPlan: ...
def build_treasury_plan(year: int) -> RequestPlan: ...
def parse_bls(body: bytes, receipt: SourceReceipt, *, expected_series_ids: tuple[str, ...], release: ReleaseMetadata | None = None) -> ParseResult: ...
def parse_bea_nipa(body: bytes, receipt: SourceReceipt, *, expected_table: str, release: ReleaseMetadata | None = None) -> ParseResult: ...
def parse_treasury_yields(body: bytes, receipt: SourceReceipt, *, release: ReleaseMetadata | None = None) -> ParseResult: ...
def select_observed_vintages(observations: tuple[MacroObservation, ...], as_of: datetime, *, strict_historical: bool = False) -> ParseResult: ...
def build_evidence_grid(results: tuple[ParseResult, ...], as_of: datetime) -> MacroEvidenceGrid: ...
```

BEA plan은 **키 값이 없는 descriptor**다. 후속 transport가 `credential_slot`에 runtime 키를 주입하며 실제 인증 URL·Request echo·body를 log/store하지 않는다. first PR은 transport를 구현하지 않고 credential slot만 테스트한다. parse 반환은 `BEAAPI.Request` 등 인증 echo를 내보내지 않는다. source response hash는 transient body의 digest이며 hash만으로 publication/권리/모델 유효성을 입증하지 않는다.

관측 ID는 정렬된 canonical JSON(`source_id, observation_period, value`의 Decimal 문자열, `unit/seasonal_adjustment, source_response_sha256, acquired_at` ISO)의 SHA-256으로 생성한다. input position이나 UUID로 값/빈티지를 덮지 않는다. source receipt와 관측 타입의 잘못된 값은 raw 예외 대신 결과 reason으로 처리하며 request plan 실패는 `NOT_AVAILABLE`, body=None이다. grid의 source별 synthetic 표지가 섞이면 `MIXED_SYNTHETIC_INPUT`으로 거부한다.

| 실패 조건 | 고정 reason |
| --- | --- |
| 불명 provider/ID/endpoint/table/year/동시 중복 plan·v1 span 초과 | `INVALID_REQUEST` |
| receipt/provider/body hash/필수 metadata 불일치 | `INVALID_RECEIPT` |
| naive/불명/불가능 timestamp 순서 | `INVALID_TIMESTAMP` / `INVALID_TIME_ORDER` |
| source rights 미확인 | `RIGHTS_UNCONFIRMED` |
| provider status/error 실패 | `PROVIDER_ERROR` |
| body/namespace/series/table/period/필수 unit 형태 불일치 | `SCHEMA_MISMATCH` |
| invalid/nonfinite 숫자 | `INVALID_VALUE` |
| 예상 source 결측 / annual row 명시 제외 | `MISSING_SOURCE` / `ANNUAL_AVERAGE_EXCLUDED` |
| 같은 응답의 상충 row / 같은 capture의 상충값 | `CONFLICTING_DUPLICATE` / `CONFLICTING_VINTAGE` |
| cutoff보다 뒤인 capture / strict 과거 빈티지 미증명 | `AVAILABLE_AFTER_AS_OF` / `HISTORICAL_VINTAGE_NOT_PROVEN` |
| release가 일정이거나 실제근거 없는 시각 | `RELEASE_EVIDENCE_UNCONFIRMED` |
| XML DTD/entity / 혼합 synthetic / ID 충돌 | `UNSAFE_XML` / `MIXED_SYNTHETIC_INPUT` / `OBSERVATION_ID_COLLISION` |

복수 오류는 plan→receipt/rights→schema→값→중복→release 순서의 첫 실패로 고정한다. BLS/BEA 숫자는 provider가 정의한 문자열 문법만 허용한다. BEA comma는 올바른 천단위 grouping일 때만 제거하며 `1,2` 같은 불량값을 12로 고치지 않는다. None/marker와 실제 0을 구별한다. 6상태/후속축 reason은 §6을 따른다.

## 4. parser 계약

1. receipt provider/고정 endpoint와 body SHA-256, aware acquisition, nonempty metadata를 먼저 검증한다. `rights_status=UNCONFIRMED`이면 body를 usable observations로 변환하지 않고 `RIGHTS_UNCONFIRMED`를 반환한다. 합성 테스트의 CLEARED_SCOPE는 실제 공급자 권리 확인 증거가 아니다.
2. BLS `status==REQUEST_SUCCEEDED`, `Results.series[].seriesID`와 요청 allowlist를 확인한다. `year`+`M01..M12`를 `YYYY-MM`으로 보존한다. `M13`은 annual-average로 명시 제외하며 월 관측치로 섞지 않는다. `value`는 유한 Decimal로 파싱한다. CPI SA/NSA, CES thousands, CPS percent는 registry에서 구별한다. footnote code/text는 원 근거로 보존하되 revision vintage라고 추정하지 않는다.
3. BEA `BEAAPI.Results.Error`/error 응답을 성공으로 해석하지 않는다. 반환 `TableName`, `LineNumber=1`, `TimePeriod=YYYYQ1..Q4`, `SeriesCode`, `Metric_Name`, `CL_UNIT`, `UNIT_MULT`를 검증한다. `DataValue`의 공식 comma formatting만 제거해 Decimal로 파싱한다. 숫자 아닌 suppressed/missing marker는 결측이다. unit multiplier를 metadata로 보존하며 임의 base-year 변경·annualization·/100·YoY 계산은 없다. `SeriesCode`는 응답 고유 ID를 보존하고 TableName/LineNumber 대신 추측하지 않는다.
4. Treasury XML은 DTD/ENTITY 포함 입력을 `UNSAFE_XML`로 거부하고 namespace-aware로 Atom `entry/content/m:properties`를 읽는다. `NEW_DATE`의 날짜는 관측 거래일이며 자정이 발표시각은 아니다. `BC_10YEAR`가 finite percent인지 확인하되 음수 금리 자체를 불량으로 규정하지 않는다. 0%와 null을 구별한다. 알려지지 않은 날짜/중복 상충 row·missing field는 실패/결측 상태로 보존한다.
5. 공통: source ID/관측기간의 중복 동일 row는 동일 observation ID로 합치되 서로 다른 값·metadata는 `CONFLICTING_DUPLICATE`로 거부한다. input을 수정하지 않는다. 값 하나라도 malformed인 expected series는 해당 series 전체를 실패로 격리하고 나머지 source의 정상 관측을 지우지 않는다. 결측을 0/전일/다른 출처로 채우지 않는다. source 간 observation ID 충돌은 실패다.
6. `INPUT_RESEARCH`는 **최소 한 source의 정상 raw observation 존재**라는 뜻이며 요청한 4축·48칸·모델 전체 READY가 아니다. 누락 series는 `missing_source_ids`와 해당 cell 이유에 남긴다. 모든 실패는 고정 reason code, usable observation 부재일 때 `NOT_AVAILABLE`다. payload·값·키·raw exception을 진단에 넣지 않는다.

## 5. 발표일·빈티지·PIT의 1차 처리

**현재 API 응답은 현재 수정 history다.** BLS `year/period`, BEA `TimePeriod`/Notes/UTCProductionTime, Treasury `NEW_DATE`/Atom updated, HTTP Last-Modified를 최초 발표·전체 데이터의 가용 시각으로 사용하지 않는다. 예정 release calendar의 시각도 실제 발표본 증거가 아니다.

- 각 capture에서 `available_at = vintage_at = ingested_at = receipt.acquired_at`, basis=`OBSERVED_CAPTURE_UPPER_BOUND`, kind=`OBSERVED_CAPTURE`로 기록한다. `release_at`은 근거가 없으면 None이다. 이 시각은 당시 관측값을 취득해 알고 있던 **보수적 상한**이며 최초 공개/최초 추정치가 아니다.
- supplied release metadata가 있으면 aware timestamp·nonempty evidence reference·known release_at<=acquired_at를 검증한다. 예정 일정만 supplied이면 release metadata로 받아들이지 않는다. reference 자체로 역사 PIT를 승인하지 않으며 available_at를 과거 release 시각으로 당기지 않는다. estimate kind는 근거 없으면 UNKNOWN, 나중 정정에서 이전 observation을 덮지 않는다.
- selector는 `(source_id, observation_period)`별 **`available_at<=as_of`인 capture 중 가장 최신 capture**만 고른다. 동일 capture 시각의 상충값은 `CONFLICTING_VINTAGE`로 거부한다. 나중 취득한 수정 history를 이전 as_of에 적용하지 않는다. 명시 cutoff보다 후인 source는 `AVAILABLE_AFTER_AS_OF`다.
- `strict_historical=True`는 1차에서 `HISTORICAL_VINTAGE_NOT_PROVEN / NOT_AVAILABLE`다. archive/초기·2차·3차 발표본 parser, 실제 publication+revision content binding과 원자료 보존/replay는 다음 구현 범위다. 이 첫 입력 경계로 backward strict PIT/OOS/calibration을 완성했다고 표시하지 않는다. 합성 timestamp도 실제 보호/미소비 증거가 아니다.
- GDP의 advance/second/third·연간개정, CPI SA 이전 5년 재산정, CES revision/benchmark, CPS 개정, Treasury 수정/backfill을 source별 품질 flags에 설명한다. ‘latest’ 응답을 INITIAL로 붙이지 않는다. release archive 후보 URL은 [원기관 조사](PRIMARY_AGENCY_EVIDENCE.md)의 BLS/BEA/Treasury 근거를 따르되 첫 PR에서 archive/실제 발표파일을 수집하지 않는다.

Treasury quote input은 약 15:30 ET, yield 게시 예정은 영업일 18:00 ET 이전이나 지연 가능하다. 둘을 실제 publication으로 사용하지 않는다. 실제 별도 검증은 `America/New_York`의 DST와 발표 지연·정정 history를 고려해야 한다. Monthly CPI/Labor의 08:30 ET 및 GDP의 08:30 ET 일정 역시 release-specific 실제 근거 없이 available_at으로 백필하지 않는다.

## 6. 8축×6상태 mapping — 48칸을 모두 표현

axis 순서: `Growth, Inflation, Liquidity, Monetary Policy, Credit, Labor, Fiscal, FX`; dimension 순서: `Level, Direction, Momentum, Surprise, Stress, Confidence`. 각 cell key가 정확히 한 번 존재해야 한다. **Level도 축 점수/종합 수준을 새로 계산하지 않고 raw observation ID를 참조하는 evidence 칸**이다.

| 축 | Level | Direction | Momentum | Surprise | Stress | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| Growth | BEA T10106:1:Q의 raw level evidence; T10101:1:Q는 별도 공표 change 근거 | N/A `NO_APPROVED_STATE_RULE` | 동일 | N/A `EXPECTATIONS_NOT_CONFIGURED` | N/A `NO_APPROVED_STATE_RULE` | N/A `NO_APPROVED_CONFIDENCE_RULE` |
| Inflation | 두 CPI series를 구별한 raw level evidence | N/A `NO_APPROVED_STATE_RULE` | 동일 | N/A `EXPECTATIONS_NOT_CONFIGURED` | N/A `NO_APPROVED_STATE_RULE` | N/A `NO_APPROVED_CONFIDENCE_RULE` |
| Monetary Policy | Treasury BC_10YEAR **금리 context** evidence; 정책 목표/stance는 미확인 | N/A `NO_APPROVED_STATE_RULE` | 동일 | N/A `EXPECTATIONS_NOT_CONFIGURED` | N/A `NO_APPROVED_STATE_RULE` | N/A `NO_APPROVED_CONFIDENCE_RULE` |
| Labor | CES/CPS를 구별한 raw level evidence | N/A `NO_APPROVED_STATE_RULE` | 동일 | N/A `EXPECTATIONS_NOT_CONFIGURED` | N/A `NO_APPROVED_STATE_RULE` | N/A `NO_APPROVED_CONFIDENCE_RULE` |
| Liquidity | N/A `DEFERRED_GSQ011` | 동일 | 동일 | 동일 | 동일 | 동일 |
| Credit | N/A `DEFERRED_GSQ011` | 동일 | 동일 | 동일 | 동일 | 동일 |
| Fiscal | N/A `DEFERRED_GSQ011` | 동일 | 동일 | 동일 | 동일 | 동일 |
| FX | N/A `DEFERRED_GSQ011` | 동일 | 동일 | 동일 | 동일 | 동일 |

active Level의 source가 없거나 cutoff/권리 검사 실패이면 `NOT_AVAILABLE`이고 해당 source 이유를 보존한다. 나머지 cell의 `value`는 None·evidence_ids=()다. source quality flag·숫자 format 검증을 model Confidence 점수로 바꾸지 않는다. 임의 growth/inflation fraction을 v0.1.1 threshold에 넣으면 index/GDP 단위가 달라 잘못된 regime가 되므로 **MacroEngine.evaluate를 호출하지 않는다**. producer Macro shape가 현재 incompatible인 상태도 유지한다. QGV/Technical 원 snapshot·scenario·점수·주문은 수정하지 않는다.

Level 필수 source는 Growth=`BEA:NIPA:T10106:1:Q`, Inflation=두 CPI ID, Labor=CES/CPS 두 ID, Monetary Policy=Treasury BC_10YEAR다. 각 cell은 필수 source가 모두 존재할 때만 RAW_EVIDENCE이며 일부만 있으면 NOT_AVAILABLE/MISSING_SOURCE로 남긴다. T10101의 GDP 공표 변동은 별도 observation으로 보존하지만 raw GDP Level을 대신하지 않는다. grid는 registry의 7개 source ID에 대한 실제 누락을 기록하고, 원기관 raw observations가 있다는 것과 해당 Level 필수 집합이 충족됐다는 것을 구분한다.

`build_evidence_grid`는 supplied 결과의 observations를 합친 후 `select_observed_vintages(..., as_of)`를 호출해 cutoff를 다시 적용한다. parser 성공만으로 미래 capture를 cell에 넣지 않는다. source별 실패/누락 reason을 유지하고 ID 충돌·synthetic 혼합은 전체 grid를 NOT_AVAILABLE로 반환한다.

## 7. 합성 테스트 목록과 assertions

모든 payload는 테스트 작성자가 만든 최소 합성 JSON/XML이다. 공식 문서의 실제 관측값을 복사하거나 실제 응답에 SYNTHETIC 표지만 붙이지 않는다. bytes SHA를 fixture에서 생성한다. 네트워크·provider runner·archive·Holdout imports는 없다.

| test 이름 | 핵심 assertions |
| --- | --- |
| `test_fixed_request_plans_have_exact_official_hosts_and_parameters` | BLS batch/BEA 단일 table/Q/Treasury 단일 연도 계약, FRED plan 없음; redirect/임의 URL·TableID·ALL/X 거부 |
| `test_bls_plan_enforces_v1_allowlist_and_span` | 4개 ID·10년 이하 명시 range·no key; unsupported/duplicate series·불량/역순 year 거부 |
| `test_bea_plan_has_credential_slot_without_secret_or_network` | UserID 슬롯만·값 없는 public descriptor; signature/Year/TableName 일치; no transport |
| `test_receipt_hash_provider_rights_and_time_are_required` | SHA/provider/endpoint mismatch·naive/acquisition missing·RIGHTS_UNCONFIRMED 차단; fixed reasons |
| `test_cpi_seasonal_and_nonseasonal_are_not_interchangeable` | 두 source ID/SA/NSA/index basis 보존; 다른 series를 missing 대체 불가 |
| `test_labor_payroll_and_unemployment_keep_distinct_units` | thousands와percent·CES/CPS identity 보존; 합성 Labor 값 없음 |
| `test_bls_status_missing_series_and_annual_average` | status 실패→없음; missing_source_ids exact; M13 명시 제외·M01~12만 월관측 |
| `test_bls_invalid_values_duplicates_and_footnotes` | None/empty/nonfinite/boolean/상충 duplicate 거부; 동일 row dedup; footnotes 유지·vintage 승격 없음 |
| `test_bea_nipa_selects_line_one_and_keeps_unit_metadata` | T10106/T10101·line1·Q·SeriesCode/Metric_Name/CL_UNIT/UNIT_MULT/Notes exact; 다른 line을GDP로 대체 안 함 |
| `test_bea_format_missing_error_and_request_echo` | comma-format Decimal 보존, missing marker/Error/mismatchedtable/invalidQ 거부; UserID echo/원Request·sentinel 진단에 없음 |
| `test_treasury_namespace_null_zero_and_schema` | 다른prefix도 같은namespace 정상; NEW_DATE+BC_10YEAR; zero/negativepercent 정상, m:null/missing/N/A 결측; namespace/schema mismatch 차단 |
| `test_xml_dtd_and_external_entities_are_rejected` | DOCTYPE/ENTITY 입력 거부·file/network read 0; raw 예외/sentinel 없음 |
| `test_capture_time_is_not_observation_or_release_time` | 모든 source available/vintage/ingested=acquired, 원관측기간 분리; release None·UNKNOWN 보존; date 자정/schedule/UTCProductionTime backfill 없음 |
| `test_release_metadata_requires_evidence_and_time_order` | evidence 없는/naive/미래 release 거부; 근거 있는 supplied 시각도 available을 앞당기지 않음 |
| `test_cutoff_does_not_use_future_or_revised_capture` | 동일기간 첫capture+후기수정, cutoff에 따라 해당 known capture선택; firstcapture 이전 N/A, 동시 상충capture 차단 |
| `test_strict_historical_is_blocked_without_release_vintage_proof` | strict flag는 NOT_AVAILABLE/HISTORICAL_VINTAGE_NOT_PROVEN; current historical row/footnote/metadata가 우회 안 함 |
| `test_grid_has_exact_48_keys_and_four_deferred_axes` | axis×dimension 각1개, rawLevel근거만; 후속24칸 DEFERRED, duplicate/sourcecollision 거부 |
| `test_grid_missing_input_remains_missing_and_never_scores` | active source 부족/미가용 이유 유지; 모든 composite valueNone; Surprise/Confidence 규칙 부재; ENGINE spy calls0 |
| `test_partial_input_research_does_not_claim_model_or_pit_ready` | 한source 정상이어도 INPUT_RESEARCH/NOT_APPLIED/OBSERVED_BOUND_ONLY; 실증·LIVE·Official/calibrated 필드 없음 |
| `test_parsers_and_grid_have_no_io_mutation_or_diagnostic_leaks` | fixture/import후 open/socket/logging spy calls0; inputdeepcopy same; stdout/stderr empty; body/키sentinel 부재 |

작업 순서: A 타입·registry → B 각 request/parser의 테스트·구현 → C cutoff·grid 테스트·구현 → D 전체 계약 검사 → E 검증 기록/리뷰. 새 state/weight를 만들어 테스트를 통과시키지 않는다. 후속 구현에서 실행할 명령(cwd=repo root):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=implementation/src python -m pytest -p no:cacheprovider -q implementation/tests/test_macro_primary_input.py
git diff --name-status
git diff --check
```

이번 문서 작업에서 위 신규 tests는 **미구현·미실행**이다. code PR 완료는 요청/정규화/보수적 cutoff/미결 48칸/무부작용 계약까지만 뜻한다. 실제 공급자 응답·발표본/빈티지·운영 저장·producer/web·Macro 모델·OOS/calibration은 별도 결과로 검증해야 한다.

## 8. 공식 근거 및 activation 전에 남는 확인

2026-10-10에 API 설명·series dictionary·GDP metadata·Treasury/SEC 설명만 읽었다. **통계·가격 관측 endpoint, 계정/Secret, release dataset 파일은 호출/열람하지 않았다.** BLS `cu.series`·`ce.series`·`ln.series`는 ID/설명/단위 metadata이며 값 시계열이 아니다. ln.series는 12MiB 제한 읽기에서 위 exact ID를 찾았으며 전체 dictionary 완전성은 주장하지 않는다.

- BLS [v1 API signature](https://www.bls.gov/developers/api_signature.htm), [v2 signature](https://www.bls.gov/developers/api_signature_v2.htm), [CPI metadata](https://download.bls.gov/pub/time.series/cu/cu.series), [CES metadata](https://download.bls.gov/pub/time.series/ce/ce.series), [CPS metadata](https://download.bls.gov/pub/time.series/ln/ln.series): 모두 HTTP200. 추정 URL `/developers/api_signature_v1.htm`, `/ces/data.htm`는404였으며 근거로 쓰지 않는다. 공식 CES 데이터 안내는 [data/home.htm](https://www.bls.gov/ces/data/home.htm)200이다.
- BEA [API guide](https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf) April20,2026·AppendixB NIPA의 endpoint/parameter/TimePeriod/unit 계약, [GDP metadata](https://www.bea.gov/data/gdp/gross-domestic-product): HTTP200. guide는 T10101/T10106 존재를 문서화하며 현재 실제 GDP response·개별LineDescription/기준연도는 미실측이다. parser가 이를 검증하고 mismatch를 거부한다.
- Treasury [XML developer notice](https://home.treasury.gov/developer-notice-xml-changes), [금리 정의](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics), [site policies](https://home.treasury.gov/subfooter/site-policies-and-notices): HTTP200. 직접 경로 채택과 **Daily Yields 독립 재사용 license 원문 미확인**은 구분한다. FiscalData의 명시 copy/adapt/redistribute 허가를 다른 Treasury feed에 이식하지 않는다. 정부 공공 자료라는 사용자 선택만으로 개별 외부자료 조건을 확정하지 않는다.
- [기관별 권리 근거](PRIMARY_AGENCY_EVIDENCE.md), [8축 조사](RESEARCH.md): BLS 조회일/지정 면책문구, BEA 지정 비후원 notice와 제3자 예외를 적용한다. BEA key·Treasury feed 실제 schema/권리·당시 발표본의 확인은 activation 전 남은 운영 의존성이다. 확인 전에도 이 명세의 offline 합성 입력 경계는 구현할 수 있다.
