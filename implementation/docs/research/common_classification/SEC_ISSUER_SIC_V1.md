# SEC 발행사 SIC 입력 계약 v1

Main의 SEC 워크플로가 동일 수집 회차의 공개 SEC submissions 자료로 아래 두 파일을 작성한다. 대상은 종목코드 보유 여부와 무관하게 그 회차의 모든 발행사다. SIC 또는 상장 정보가 비어도 발행사 행을 보존한다. Codex가 소비하는 이 목록에는 명부와의 대응 결과를 넣지 않는다.

| 파일 | 형식과 규칙 |
| --- | --- |
| issuers.ndjson | UTF-8, LF, 마지막 LF 포함. CIK 오름차순, CIK당 한 JSON 객체. 동일 CIK의 상충 관측은 자동 병합하지 않고 회차를 검증 실패 처리한다. |
| manifest.json | JSON 객체. schema_version은 sec-issuer-sic/1, snapshot_id는 불변 회차 ID. collected_at은 UTC RFC 3339. issuers_sha256은 NDJSON 파일 바이트의 SHA-256. issuer_count, listing_count, missing_sic_count, no_listing_count는 정수. source_url, source_sha256은 원본 스냅샷 위치와 바이트 해시. 부분 수집은 complete=false로 기록하며 전체 시장 집계에 사용하지 않는다. |

| NDJSON 필드 | 자료형 및 의미 |
| --- | --- |
| cik | 선행 0을 포함한 ASCII 숫자 10자리 문자열 |
| issuer_name | SEC 발행사 원문 이름 |
| sic | 정확한 ASCII 숫자 4자리 문자열 또는 null |
| sic_description | SEC 설명 문자열 또는 null |
| listings | 배열. 각 객체의 ticker와 exchange는 SEC가 같은 위치에서 제공한 문자열 쌍. 거래소 누락 시 null, 상장 정보가 없으면 빈 배열. 서로 길이가 다른 원천 배열을 임의로 짝짓지 않는다. 짝을 확정할 수 없는 티커의 exchange는 null로 보존한다. |
| observed_at | 이 발행사 원문을 획득한 UTC RFC 3339 시각 |
| source_url | SEC 원문 URL 또는 SEC 원본 묶음 URL |
| source_member | 묶음 안의 정확한 경로. 개별 파일이면 null |
| source_sha256 | 개별 원문 파일 또는 압축 해제된 멤버의 원래 바이트 SHA-256, 소문자 64자리 hex |

검증은 내용 해시, CIK 유일성, 형식, 집계, 완료 여부를 확인한다. SIC·거래소·종목 종류를 이름에서 보충하지 않는다. 시각은 자료 관측 시각이며 과거 유효 시작일을 뜻하지 않는다.

## 비공개 소비

11/23 고정 3시장 명부와 이 목록의 manifest 해시를 함께 고정한다. 거래소 대응은 NAS/Nasdaq, NYS/NYSE, AMS/NYSE American 계열의 명시적 동의어만 허용한다. 거래소와 대문자 티커의 정확한 쌍으로 대응한다. 공백은 양 끝만 제거하고 종류주 구두점은 보존한다. 복수 발행사 충돌, 거래소 미상, 발행사 부재, 명부 키 중복은 각각 이유를 남긴다. 종류·통화·동일 증권 식별이 모호하면 후보에서 제외한다. 복수 종류주가 같은 CIK에 연결되면 증권은 각 행, 기업 분포는 고유 CIK로 센다.

고정 명부 주식 6,667행에서 시작해 보통주가 아닌 증권과 SIC 6770 등 사업 없는 껍데기 근거가 있는 발행사를 별도 집계한다. 명부의 다른 증권 종류는 분모 밖에서 센다. 입력 누락과 제외를 구분한다. 출력의 근거 등급은 CANDIDATE, 회계모형은 UNKNOWN이다. 운영 504의 평가일 확정 소속과 합치지 않는다. 종목별 결과는 비공개에만 두고 공개 인계에는 집계와 링크만 남긴다.
