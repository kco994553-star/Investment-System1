# M1 SEC 입력: PIT 경계·정정 계보·보존 receipt

이 PR은 승인된 TARGET 미국 17종목의 **명시적 부분집합**만 처리하는 수동 SEC 입력 경로다.
기존 `sec_companyfacts.facts_to_raw` 계정 변환기, `RawDatasetStore`, SEC 요청/retry 도구를 재사용한다.
가격·QGV 계산·예약 workflow·Pages 공개 연결은 추가하지 않는다. 실제 수집은 이번 검증에서 실행하지 않았다.

## 시각과 데이터 범위

- `filing_date`: 원래 SEC 제출 날짜. UTC 자정의 공개 시각으로 쓰지 않는다.
- `accepted_at`: timezone이 있는 접수 메타데이터. 최초 공개 시각이라는 의미는 아니다.
- `published_at`: 이 버전에서는 **null**. 최초 공개 시각이 증명됐다고 표시하지 않는다.
- `acquired_at`: 두 원문을 확보한 시각. 오프라인 import에서는 운영자가 제공한 취득 시각이며 독립 증명이 아니다.
- `available_at`: 취득을 근거로 기록한 **보수적 관측 상한**. 그 이전 cutoff에서 신규 원문을 사용하지 않는다.
  basis는 `OBSERVED_PUBLIC_API_UPPER_BOUND`, precision은 `CONSERVATIVE`, `estimated=true`다.

이는 정확한 과거 최초 공개 시각이나 과거 빈티지를 복원하는 기능이 아니다.
M1 JSON의 `published_at=null`은 기존 필수 datetime `DataStamp` 소비 형식과 구분된다.
현행 분석/QGV replay에 자동 투입하지 않으며 `real_data_verified`와 `full_pit_historical`은 false다.

회사 식별은 기존 `markets.us.US_LISTINGS`의 17개로 고정한다. 본문 두 곳의 CIK와 accession·form·제출 날짜를 대조한다.
미래/naive/잘못된 시각, 인덱스에 없는 accession, 잘못된 기간·값은 제외한다.
`end`를 누락된 제출일 대신 쓰지 않으며 제외된 값이 기존 converter fallback으로 다시 들어가지 않는다.
기본은 10-K 계열(20-F 포함), `--form-filter 10-Q`는 분기 계열이다.
현재는 submissions **recent**와 일치하는 입력만 처리한다. 과거 추가 페이지·개별 filing XBRL 수집은 범위 밖이다.

경제적 기간 키는 taxonomy/concept/unit/start/end다. FY 표시가 달라진 비교기간을 전년 데이터로 중복 계산하지 않는다.
같은 날의 정정 후보를 접수 시각으로 구별할 수 없거나 최신 filing에 상충하는 값이 있으면 해당 기간을 보류한다.
충돌한 최신 값을 버리고 과거 값으로 되돌리지 않는다. 제출 날짜나 접수 시각으로 더 늦음이 입증된 명확한 후속 revision은 충돌을 해소할 수 있다.
receipt의 `selected_input_facts`는 converter에 전달한 기간별 입력이며, 모든 정규화 필드의 정확한 추출 trace라는 뜻은 아니다.
원래 후보와 제외 사유도 보존한다. `/A` 표기는 formal amendment 메타데이터로 유지하되 부모 accession을 추정하지 않는다.

## 보존과 재실행

저장 위치는 사용자가 지정한 store 아래다. 원문 ID는 종류·CIK·전체 SHA256으로 구성해 갱신으로 덮어쓰지 않는다.

| 위치 | 내용 |
| --- | --- |
| `blobs/`, `manifests/` | 기존 RawDatasetStore 형식의 불변 SEC 원문과 출처·해시·크기 |
| `m1/receipts/<id>.json` | 입력 원문 결속, cutoff·취득 경계, 선택/제외 후보, 원문 revision과 자체 digest |
| `m1/latest/<company>.json` | 완전히 저장·검증된 READY receipt 포인터 |

같은 원문·취득 경계·cutoff·form filter는 같은 receipt를 재사용한다. 후속 원문 변화는 이전 READY receipt를 연결하되
같은 accession의 값 변경을 공식 `/A` 정정으로 승격하지 않는다. 오래된 취득 입력을 늦은 cutoff로 import해도 최신 포인터를 되돌리지 않는다.
원문·manifest·receipt를 읽을 때마다 해시/크기/회사 결속을 검증한다. 실패·NOT_AVAILABLE·쓰기 중단은 이전 포인터를 유지한다.
회사별 lock과 원자적 receipt/포인터 교체로 동시 갱신을 분리한다. 검증은 지정 로컬 store의 보존 상태이며 독립 백업 존속의 증명은 아니다.

## 수동 사용

오프라인 입력은 `<company>.companyfacts.json`와 `<company>.submissions.json` 파일 쌍이다.
예시는 기기 로컬 경로이며 Secret 값이나 공개 Pages 경로를 사용하지 않는다.

```sh
python tools/sec_m1_inputs.py --companies nvda,asml --store /local/sec-m1-store \
  --input-dir /local/sec-imports --acquired-at 2026-10-09T10:00:00Z \
  --as-of 2026-10-09T10:00:00Z
```

`--live`는 명시적으로 선택할 때만 회사별 SEC companyfacts/submissions 두 URL을 요청한다.
실행자가 유효한 연락처를 포함한 설명형 `--user-agent`를 제공해야 한다. 요청 사이 0.2초와 기존 429/5xx retry를 사용한다.
기본 cutoff는 각 회사의 취득 경계다. 회사 하나의 transport/schema 실패는 다른 회사를 중단시키지 않는다.
CLI 출력은 회사 ID·상태·receipt ID뿐이며 원문·값·헤더·User-Agent·예외 본문을 출력하지 않는다.

가격이나 전체 후보 풀을 선택하는 flag는 없다. 임의 CIK·US17 외 회사·빈 목록·중복·17개 초과 목록을 요청 전에 거부한다.
모든 실제 운영·주기 실행·공개 연결은 후속 결정이며 이 PR은 병합 승인 대기한다.

## 검증

새 테스트는 synthetic 원문·임시 store·모의 transport만 사용한다. 취득 cutoff 전후, 정정/동일 accession revision,
경제적 기간 중복, naive 시각·CIK·입력 오류, 원문/manifest/receipt 변조, 쓰기 중단, 재실행과 batch 격리를 검증한다.
기존 전체 회귀 테스트와 repository/privacy guard도 PR 생성 전에 확인한다.
