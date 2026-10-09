# SEC M1 — 입력 PIT 시각·정정 lineage·보존 receipt

기준일: **2026-10-09 UTC**. 작업 출발점은 문서 PR #78 병합
`c31b9556ad584d2132268f77bb98445416c7bca6`이다. PR 생성 전 원격에 한국·일본
조사 문서 1개가 추가되어 최신 canonical `36c8982dd1d95075879899a770704dcaf853be24`
기준으로 rebase했다. 기존 구현 코드·테스트에는 차이가 없었다. 사용자 결정은
[GSQ-005](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md#gsq-005--26e-가격-경로-결정-및-sec-m1-구현-승인-2026-10-09)에 append-only로 기록한다.

M1은 **이미 확보한 SEC 입력의 오프라인 검증·보존**부터 시작한다. 명시적으로
선택한 TARGET 미국 17종목 안의 최대 3 issuer만 한 번에 처리한다. 기본 전체
종목 수집이나 새로운 종목군 선택은 없다. `companyfacts`·`submissions`의 기존
parser와 `RawDatasetStore`를 재사용하고 기존 provider·replay 동작은 보존한다.

가격 수집, QGV 재점수, 예약 workflow, Pages 자동 공개, 실제 SEC 수집 실행,
Holdout 선택/사용, 투자 방법론·가중치·TARGET 변경은 포함하지 않는다.
공개 앱·CSP·Frozen 종목군·승인 산출물은 유지하고 `AUTONOMY_MODE=READ_ONLY`로
남는다. 이 PR 병합은 사용자 승인을 기다린다.

## 시각을 나누어 보존하는 이유

SEC 접수 시각(`acceptanceDateTime`)과 최초 공개 시각은 다르다. 공식 FAQ는
보통 1~3분 지연을 설명하지만 예측 가능한 상한이나 최초 공개 타임스탬프를
보장하지 않는다. 따라서 접수+3분, 공시일 UTC 자정, 다음 영업일 자정으로
공개 시각을 만들지 않는다. 회계 기간·공시일·접수 시각·원본 관측 시각·이번
수입 시각·판단 기준 시각을 각각 보존한다.

- `as_of`와 평가 시계는 명시적인 시간대가 있어야 하며 미래 기준일은 거부한다.
- 접수 시각은 `Z` 또는 UTC offset이 있는 형식만 해석한다. 무시간대 문자열을
  UTC/뉴욕 시간으로 추측하지 않고 미확인으로 남긴다.
- 정확한 최초 공개 시각은 `first_public_at=null`이다. 공시일 또는 접수 시각만
  있으면 `NOT_AVAILABLE / AVAILABILITY_UNPROVEN`으로 남긴다.
- 선택적인 관측 receipt는 issuer·원본 종류·공식 URL·전체 SHA256·바이트 수·
  HTTP 200·시간대가 있는 관측 시각을 정확한 원본에 연결한다. 두 필수 원본의
  관측 중 늦은 시각 이후에만 해당 입력을 허용한다. 근거 이름은
  `FIRST_VERIFIED_OBSERVATION_UPPER_BOUND`이며 최초 공개 시각을 뜻하지 않는다.
- receipt는 오프라인으로 전달된 운영자 근거의 형식·바이트 연결을 검증한다.
  SEC 전자서명 검증이나 외부 HTTP 관측의 진위 증명은 제공하지 않는다. 이
  단계만으로 `full_pit_pass`, `real_data_verified`, `publication_approved`를
  true로 바꾸지 않는다. 합성 입력은 계속 synthetic이다.

오늘 받은 companyfacts는 과거에도 그 내용이 존재했다는 증거가 아니다. 이전
기간의 수치라도 원본 관측이 기준 시각보다 늦으면 보류한다. 최초 근거가 없는
입력·연결되지 않는 accession은 제외 이유를 기록하며 결측을 0으로 바꾸지 않는다.
최근 submissions만 제공되면 추가 이력까지 완전하다는 주장을 하지 않는다.

## 정정·변경의 의미

`/A`는 정정 양식 표지다. 같은 회계 기간·이웃 accession·시간순 배열만으로
무엇을 대체했는지 추정하지 않는다. 대체 관계는 `UNPROVEN`,
`replaces_accession=null`로 남긴다. 동일 accession의 원본 바이트가 바뀌어도
새 해시의 관측 generation으로 보존하고 이전 원본을 덮어쓰지 않는다.

issuer CIK는 원본 본문과 맞아야 한다. accession 앞부분은 제출 대행자의 CIK일
수 있어 issuer CIK와 같다는 추가 조건을 만들지 않는다. 기존 `stry`→SYK,
ASML의 미국 ADR 및 20-F 양식을 그대로 존중한다.

## 원본과 보존 receipt

전체 SHA256·바이트 수·고정 SEC URL·issuer를 JSON 해석 전에 검증한다. 중복
JSON key, NaN/Infinity, 숫자 대신 bool, 길이가 다른 submissions 배열,
서로 충돌하는 같은 fact/accession은 모호한 입력으로 거부한다. 임의 호스트·
URL 자격 증명·query·경로 우회도 허용하지 않는다. 로그는 코드·개수·해시만
내보내고 원본 값이나 예외에 포함된 사용자 문자열을 출력하지 않는다.

보존 위치는 Git checkout과 Pages 밖의 명시적인 디렉터리다. `RawDatasetStore`를
staging에서 사용한 뒤 원본·manifest·receipt 연결을 재검증한다. 쓰기를 직렬화하고
완전한 generation 하나를 원자적으로 공개한다. 두 개 파일을 따로 바꾼 것을
트랜잭션으로 주장하지 않는다. 독자는 완료된 generation만 읽고 해시·크기를
다시 검사한다. 누락·손상·중단 시 실패로 남기며 이전 완료 generation은 보존한다.

운영자는 공개 서버·업로드 대상 밖의 전용 비공개 runtime 디렉터리를 선택한다.
기존 Git marker·cockpit 산출물 marker·symlink를 거부하고 협력하는 writer는 lock으로
직렬화한다. 같은 사용자 권한의 비협력 프로세스가 실행 도중 디렉터리를 바꾸거나,
임의 runtime을 나중에 공개 서버로 지정하는 것까지 격리하는 저장소는 아니다.
저장 API는 lock·fsync·동일 파일시스템 rename을 지원하는 로컬 POSIX 환경을
대상으로 한다. 중단된 staging은 미완료로 남을 수 있고 완료 generation 독자는
이를 사용하지 않는다. Windows·분산 저장소·실제 전원 장애는 검증하지 않았다.

같은 입력·기준 시각·근거·계약 버전의 재시도는 같은 전체 SHA256 generation을
반환하며 최초 receipt를 다시 쓰지 않는다. 바이트·근거·기준 시각이 바뀌면
새 generation이다. 평가/수입 시계만 달라졌다는 이유로 내용 변경을 만들지 않는다.

## 명시적 오프라인 실행

CLI는 `implementation/tools/sec_m1_audit.py`다. 입력 manifest와 원본·관측
receipt는 Git checkout·Pages 밖의 같은 디렉터리에 둔다. 원본 경로는 해당
디렉터리 안의 단일 파일명만 받으며 symlink·상위 경로·임의 URL 읽기는 없다.
입력마다 최대 16 MiB, 각 원본의 fact/submissions 처리 행 수는 100,000으로 제한한다.

manifest의 `schema`는 `SEC_M1_OFFLINE_IMPORT/1`이며 다음 항목을 제공한다.

| 항목 | 내용 |
| --- | --- |
| `issuer_ids` | 기존 company ID의 명시적 목록, 1~3개. 예: `nvda`, `msft`, `googl`; SYK는 `stry`. |
| `synthetic` | 합성 입력이면 true. false로 입력해도 전체 PIT·실데이터 검증·공개 승인을 부여하지 않는다. |
| `artifacts` | issuer마다 companyfacts/submissions 한 쌍. 각 항목은 `issuer_id`, `cik`, `source_kind`, `source_url`, `path`, `sha256`, `bytes`. |
| `observation_receipts` | 선택 목록. 각 항목은 `path`, `sha256`, `bytes`. 없으면 입력은 관측 근거 미확인으로 보존한다. |

원본 종류는 `SEC_COMPANYFACTS` 또는 `SEC_SUBMISSIONS`만 허용한다. 관측
receipt 본문의 `schema`는 `SEC_M1_OFFICIAL_OBSERVATION/1`이며 `issuer_id`,
`cik`, `source_kind`, `source_url`, `artifact_sha256`, `artifact_bytes`,
`http_status`, `observed_at`을 갖는다. 자기 신고 공개일 또는 접수일을 이
receipt로 대체하지 않는다. 원본과 receipt 해시는 각각 정확한 파일 바이트의
전체 SHA256이다.

아래 두 시각 변수에는 실제 판단 기준 시각과 이번 평가 시각을 각각 명시적인
UTC offset이 있는 ISO 문자열로 지정한다. 기본 날짜나 현재 시각을 추측하는
옵션은 없다. 이 명령은 수집을 시작하지 않는다.

```sh
python implementation/tools/sec_m1_audit.py \
  --input-manifest /tmp/sec-m1-inputs/import.json \
  --as-of "$SEC_M1_AS_OF" --now "$SEC_M1_EVALUATED_AT" \
  --output /tmp/sec-m1-runtime
```

종료 0의 `PASS`는 **입력 감사·보존 절차의 성공**이다. 모든 fact가 사용
가능하다는 뜻이 아니므로 `fact_counts`와 제외 이유 `codes`를 함께 확인한다.
각 fact는 `ELIGIBLE` 또는 `NOT_AVAILABLE`이며 web의 LIVE 상태를 생성하지 않는다.
오류는 종료 2와 정해진 코드만 출력한다. `--now`는 실행자가 제공한 평가 시계이며
SEC 관측의 진위를 증명하지 않는다.

Python API는 `audit_sec_m1(M1Request, artifacts, observation_receipts)`와
`persist_m1_generation(audit, output_root=..., imported_at=...)`다.
저장 독자는 `read_m1_generation` 또는 `list_m1_generations`로 완료 generation만
검증해 읽는다. 원본 수치·receipt를 저장소나 Pages 산출물에 추가하지 않는다.

## 검증 영수증

2026-10-09 로컬 native pytest 전체 **958개 + subtests 345개 PASS**. 신규 M1
97개가 포함된다. 최초 72개 계약 테스트를 구현 전에 RED로 확인하고, 기간·
관측 연결·변조 receipt 경로·CLI 읽기 전 검증·staging 교체·cockpit 하위 저장
회귀도 실패를 재현한 뒤 수정했다. 모든 신규 입력은 합성 메모리/임시 파일이다.

```sh
cd implementation
python -m pytest -q
```

기존 SEC 선택 fetch 테스트는 모의 실패/합성 응답으로 바꿨다. native pytest의
FRED 기본 fixture는 키 탐색을 비활성화하고 CSV transport를 모의 실패로
설정한다. 실제 SEC/FRED/가격 API·사용자 키·기기 데이터를 테스트하지 않는다.
기존 수동 C21 workflow/mini runner는 수정·실행하지 않으며 이 PR의 검증은
native pytest와 기존 PR CI를 기준으로 한다.

로컬 공개 build는 #78 실제 배포본과 **16파일 모두 바이트 동일**하고
`pages_artifact_guard` 위반 0이다. 웹 자산·CSP·외부 요청 경로·Frozen 카탈로그·
기존 QGV 함수·TARGET·workflow에는 diff가 없다. GSQ-001~004의 기존 바이트를
보존하고 GSQ-005만 추가했다. `AUTONOMY_MODE` readback은 `READ_ONLY`다.
GitHub CI의 최종 결과는 이 PR Checks에 기록하며 통과를 병합 승인으로 해석하지 않는다.

## 다음 단계 경계

이 변경은 일일 자동 공급의 구현 완료가 아니라 입력 증거를 보존하는 M1의 첫
단계다. 실제 SEC 확보 runner·최근 밖 추가 history·원본 XBRL과 정정 관계 검증·
일일 품질 승인·web adapter 연결은 후속 승인 범위다. 가격 권리와 M2 재판단은
별개이며 이 PR의 receipt로 가격 수집 또는 공개 배포를 허용하지 않는다.

Tiingo 사용자 키·무저장 표시 조사 결과는
[별도 1~2쪽 문서](TIINGO_DEVICE_DIRECT_REVIEW_M1.md)에 기록한다.

## 공식 근거

조회일은 모두 **2026-10-09 UTC**이며 실제 SEC 데이터 호출은 하지 않았다.

- [SEC FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions):
  접수와 공개의 지연·최초 공개 시각 부재·제출 대행자 accession.
- [EDGAR 데이터 접근](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data):
  접근 한도·선언 User-Agent·영업일 공개·PAC 정정/제거.
- [SEC API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces):
  companyfacts/submissions·추가 history·표준 taxonomy 범위·브라우저 CORS 미지원.
