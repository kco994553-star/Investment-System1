# US17 SEC 수집 모듈과 수동 진입점

최신 사용자 대기열 3번. TARGET 원본은 변경하지 않고 `markets/us.py::US_LISTINGS`의 미국 상장17개만 다룬다. `stry`의 기존 SYK 결속, ASML ADR의 기존 CIK를 그대로 사용한다. 한국·일본2개, 임의 CIK·가격·추가 archive/submissions 페이지는 수집 범위 밖이다.

`providers/sec_collection.py::SecCollectionClient.collect(company_id, cik)`는 기존 companyfacts·submissions **두 고정 URL**의 bytes와 둘을 취득한 뒤의 aware UTC 시각을 반환한다. 기존 `sec_m1_inputs.run_batch`, `ingestion/sec_m1.retain_input`을 재사용해 회사별 실패 격리·이전 READY 보존·원문 무결성을 유지한다. 작은 코드 변경용 운영 GSQ/receipt는 추가하지 않는다. 실제 수집의 기존 원문 custody는 별개 기능이다.

## 실행 계약

설정 이름은 **SEC_USER_AGENT**다. 값은 런타임 환경에서만 읽고 CLI 인자·기본 연락처·로그·예외·보존 metadata에 넣지 않는다. 이 작업에서는 실제 환경 값·Secret 등록 여부를 조회하지 않았고 실제 요청도 수행하지 않았다.

```bash
# cwd: implementation. 사용자가 명시적으로 실행하는 수동 경로.
python tools/sec_collect_inputs.py --all-us17 --store /path/to/local-sec-inputs --live
# 일부만 실행하려면 --all-us17 대신 --companies nvda,amd
```

일일 Actions·스케줄·공개 JSON 앱 연결은 코덱1 담당이며 이번 PR에 워크플로·배포·public producer를 추가하지 않는다. 로컬 raw store를 Pages로 복사하면 안 된다. 공개 재무 연결은 기존 허용 계정 투영·공개 경계를 적용하는 별도 작업이다.

## 전송·PIT 경계

- 한 client의 모든 요청·재시도 시작 간격은 최소0.2초(최대5req/s)다. SEC의 [자동 접근 안내](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)의 전체10req/s 제한보다 보수적이다. 다른 Worker/프로세스와 합산해야 하므로 여러 수집기를 동시에 실행하는 스케줄은 제공하지 않는다.
- redirect는 전부 거부한다. 성공 status·JSON 객체·finite 숫자·승인 CIK 결속을 확인하고 두 본문 완료 후에만 기존 보존 함수로 넘긴다. 응답 크기·timeout을 제한한다.
- 429·일시적5xx·timeout에 최대5시도, 2/4/8/16초 backoff. Retry-After는 초 및 HTTP-date를 처리하고 서버 요구 대기를 줄이지 않는다.60초 초과 대기는 재시도 종료로 처리한다.4xx/redirect/잘못된 본문은 즉시 실패한다.
- 취득시각은 **OBSERVED_PUBLIC_API_UPPER_BOUND**이며 최초 공표시각이 아니다. `published_at=null`, `full_pit_historical=false`와 기존 as-of 가드를 유지한다. latest/revised companyfacts를 과거 vintage로 소급하지 않는다.
- ASML 원문 취득은 지원하지만 20-F를 10-K로 바꾸지 않는다. legacy M1의 `--form-filter 10-K/10-Q`에서 READY 여부는 원문 취득 성공과 별개이며 실제17개 READY를 주장하지 않는다.

모의 transport·clock·sleep·환경 mapping으로 속도 제한, Retry-After, 오류 소진/격리, CIK·redirect·JSON 차단, Secret canary·CLI 보고를 검증한다. 실제 회사 응답 fixture·가격·개인 계정·Holdout은 사용하지 않는다.
