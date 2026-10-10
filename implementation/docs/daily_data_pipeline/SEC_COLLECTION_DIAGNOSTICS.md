# SEC daily 실패 진단·부분 성공

사용자 긴급 승인: 내부 고정 코드·HTTP 상태·fetch/parse/normalize 단계·실패 회사 순번만 출력하고 한 회사 실패로 나머지를 중단하지 않는다. 값·URL·User-Agent·이메일·키·회사명은 진단 로그에 없다.

`public_sec_inputs.py --live --output ...`는 17개를 기존 정렬 순서로 시도한다. index는1~17, client 초기화/설정 실패는0이다. 실패별 예: `SEC_FAILURE company_index=1 stage=fetch code=SEC_HTTP_403 http_status=403`. retry 소진은 `SEC_HTTP_RETRIES_EXHAUSTED`와 마지막429/5xx 상태를 함께 출력한다. 원문/알 수 없는 exception text는 SEC_COLLECTION_FAILED로 바꾸고 절대 출력하지 않는다. 200응답 JSON 검증은parse, 공개 allowlist 투영/날짜/배열 검증은normalize다.

- 모든 성공: 기존 `public-sec-reported-inputs/1`·필드 그대로, `failed_companies=0`.
- 일부 실패: `public-sec-reported-inputs/2`, 동일 scope·정확한 TARGET US17 순서. 성공 행은 기존 필드+`status=LIVE`; 실패 행은 `company_id,cik,status=NOT_AVAILABLE,reason_codes,failure_stage,company_index,http_status`만. 실패 행에 가짜 source/hash·0 주식 수·구 데이터 재사용을 넣지 않는다.
- 전부 실패: exit1·실패 수17, 새 파일을 쓰지 않고 기존 파일을 보존. 누락/invalid UA는 수집 전 종료하며 기존 파일을 보존한다. 저장/경계 검증 자체의 전역 오류는 성공으로 처리하지 않는다.
- CLI 성공 exit0은 부분 성공도 포함한다. 공개 파일은 새 성공 행과 명시NA만 제공한다. 실패 회사가 나중에 자동 정상 판정되거나 기존 source와 혼합되지 않는다.

코덱1 consumer는 schema /1·/2를 읽고 /2의 NOT_AVAILABLE 행을 **먼저 건너뛴 다음** sources/reported_shares/filings를 접근해야 한다. `.github/workflows`·Worker·웹을 바꾸지 않는다. 기존 Pages guard는 동적 파일의 strict 의미 검증으로 두 버전을 검사한다; 허용 가격/산출물 범위를 확대하지 않았다.

client 원문 상한32MiB와 public parser 상한을 일치시켰다(기존 public parser8MiB). 큰 정상 companyfacts가 공개 투영 전에 제한에 걸릴 가능성을 제거하며 최종 공개 파일2MiB 상한은 유지한다. **현재 Actions 실패의 원인으로 확정한 것은 아니다.** 실행 환경 SEC_USER_AGENT 미설정으로 실제 한 회사 companyfacts/submissions 취득을 재현하지 못했다; Secret 값을 가져오거나 연락처를 임의 작성하지 않았다. 고정 코드가 노출된 다음 실제 Actions 실행 결과로 원인을 확정한다. UA 재설정 성공이나 네트워크403 해결을 주장하지 않는다.
