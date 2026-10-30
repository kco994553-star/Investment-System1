# E1-B / E2 연결 설계 — 실행하지 않음

E1-A는 합성 입력을 처리하는 라이브러리다. 실제 수집기·checkpoint 파일·DB·정기 작업·
게시 파일·새 백테스트 엔진을 추가하지 않았다. 공급원/권리/운영 승인 전 상태는
E1-B **BLOCKED_ON_LICENSE**, E2 **BLOCKED_ON_LICENSE + BLOCKED_ON_DATA**다.

## E1-B collector adapter 계약

Main이 공급원을 선택하고 [권리 표](SOURCE_RIGHTS.md)의 F/S/R와 공개 용도별 권한을
확인한 뒤 기존 `providers/sec_collection.py` bounded client를 재사용한다.
`UniverseRegistry`는 504 전용이므로 확장 카탈로그를 위해 그 allowlist를 바꾸면 안 된다.

어댑터 입력은 source_id, terms_version/evidence_ref, authorized_purposes,
license_expires_at, source_cursor, expected_previous_snapshot_version,
run_attempted_at, bounded request budget이다. 비밀값/실제 연락처는 런타임 비공개 설정이고
원장/로그/PR에는 쓰지 않는다.

어댑터 출력은 다음을 포함하는 **완료 batch**다.

- events: 영구 issuer/security ID와 검증한 종류·상장거래소·효력 시각·최초 이용 가능 시각.
  event_id는 source namespace 안의 안정 ID이며 재수집 시 바뀌지 않는다.
- source_manifest: 원본 bytes의 무결성 hash, 크기·스키마·필수 열·전체 page 수/행 수,
  source cut-off/vintage·공개 시각 근거, complete/incomplete, source cursor.
- collection receipt: 실제 collected_at·HTTP 상태(고정 코드)·source rights 상태.

원본 bytes는 허용된 비공개 경로에만 보관한다. Secret·보유·원가격·Sheet 설정은 이
카탈로그 어댑터의 허용 입력이 아니다. 네트워크 예외 원문·응답 body를 로그로 넘기지 않는다.

`available_at`은 collected_at/as_of로 덮어쓰지 않는다. 최초 공개가 확인되지 않는
현재 디렉터리 관측은 `OBSERVED_PUBLIC_API_UPPER_BOUND`로 별도 기록하고 역사 PIT 증거로
승격하지 않는다. 증거가 없어 엄격 Event를 만들 수 없으면 staging에서 보류한다.
API의 현재 company name/ticker/SIC로 과거 구간을 덮어쓰지 않는다.

## 주기·증분·실패 복구 제안

| 대상 | 승인 후 갱신 제안 | 불완전/실패 처리 |
| --- | --- | --- |
| 상장 디렉터리 | 미국 거래일 단위 complete snapshot 대조 + 공식 사건 feed | 목록에서 빠졌다는 이유만으로 DELISTED 생성 금지. 페이지 누락·test issue·지연·휴장을 구분하고 종료 증거 요구 |
| SEC 공시 | accession 단위 변경/정정 이벤트, 필요한 issuer만 수집; 새 issuer 초기 입력은 별도 예산 | 새 공시가 없다는 뜻과 수집 실패를 구별. 과거 filings·available_at 보존 |
| CPI | 월간 실제 공표 뒤 vintage 추가 | 관측 월을 발표일로 사용 금지. 수정·발표 전 기간은 기존 이용 가능 vintage 유지 |
| 가격/시총 | 라이선스와 오너 승인 후 허용된 EOD만 | E1-A에 가격 수집을 붙이지 않음. NA를 0/평균/최근가로 채우지 않음 |

429/5xx는 기존 Retry-After/제한된 exponential backoff+jitter 계약을 사용한다.
프로세스별 pacing만으로 전체 10 requests/s를 초과하지 않도록 Main이 다른 SEC 작업과
요청 예산을 조정한다. 재시도 횟수·전체 작업 기한을 넘으면 FAILED와 마지막 성공 시각을
그대로 남긴다. 스케줄·시작일·자동 실행은 이번에 승인되지 않았다.

checkpoint는 source_id/cursor·권리 버전·source manifest hash·마지막 완결 batch·
expected previous version에 묶는다. 미완료 cursor는 resume staging으로만 남기고
공식 current pointer를 갱신하지 않는다. event_id 내용 충돌·ID 혼동·시간 역전은
재시도로 덮지 않고 격리한다. 같은 시각 상충 사건에는 공급원 순서 증거/다음 스키마가 필요하다.

파일 기반 저장을 선택한다면 Main은 새 별도 서비스를 만들지 말고 기존 비공개 저장
방식을 먼저 검토한다. candidate 생성 → schema/replay/hash 검사 → private 임시 파일과
디렉터리 fsync → expected previous hash 대조 → atomic rename/CAS → checkpoint commit
순서로 연결한다. 원장과 pointer가 하나의 transaction이 아니라면 committed manifest를
최종 기준으로 하고, 재시작 때 hash와 complete marker를 대조해 미완료 staging을 버린다.
동시 작업에서 늦게 끝난 옛 batch가 새 pointer를 덮지 못하도록 compare-and-swap이 필요하다.
디스크 부족·손상·publish 실패는 이전 정상 pointer를 보존한다.

E1-A `dry_run_refresh`가 보장하는 것은 **메모리 안의 전체 batch 성공/실패**다.
전원 중단·파일 atomicity·실 API 429 재시도·cursor resume는 아직 운영 검증하지 않았다.
합성 HTTP_429 코드를 주입한 시험을 실제 HTTP 요청 성공으로 보고하지 않는다.

## E2 시총 판정 계약 초안

실제 계산 구현/수집 없음. 다음 인터페이스는 설계 이름이다.
`assess_cap_floor(catalog_interval, eod_price, outstanding_shares, cpi_vintage,
policy, as_of) -> eligibility + reason_codes + basis_refs`.

가격은 currency·security_id·session·raw/adjusted basis·available_at·rights_ref가 필요하다.
주식수는 issuer/security/class·measurement_date·filing/accession·available_at·단위·
종류별 경제권·동일 기준 변환 증거가 필요하다. EPS 희석 가중평균 shares를 기발행 주식수로
바꾸어 쓰지 않는다. 비상장 종류·다중 종류의 회사 시총 합산은 기존 M3 계약과 대사한
명시적 정책이 필요하며 카탈로그 security_count를 곧바로 발행사 수나 분모로 쓰지 않는다.

CPI는 관측월·계열·발표 시각·빈티지·기준연도·기준값 확정 시각을 보존한다.
2009 CPI-U 연평균을 구매력 단위로 선택한 #418 가정과 당시 투자자가 이용한 CPI를
구분한다. U-US-CAP200-REF는 현재 참고 판정, U-BOOK200/U-SPX-HIST는 별도 역사 연구다.

후속 합성 시험 설계(이번 실제 실행 없음):

| 반례 | 기대 상태 |
| --- | --- |
| 가격 세션과 shares 단위/기업행사 기준 불일치 | CAP_BASIS_MISMATCH |
| CPI 관측월은 과거지만 발표 시각이 as_of 뒤 | 당시 미가용, 후일 vintage 소급 금지 |
| 기준을 정한 뒤 정확히 $200m·바로 아래/위 | 명시한 경계(>=)만 통과, 성과 확인 후 임계 조정 금지 |
| 동일 CIK 두 종류주·비상장 종류 누락 | 회사당 한 번만 집계, 불완전 합산 보류 |
| shares/price/상폐 정산 자료 결측 | NOT_VERIFIED / BLOCKED_ON_DATA, 0으로 채우지 않음 |
| license 만료/보관 제한/공개권 미확인 | BLOCKED_ON_LICENSE, 자동 저장/공개 없음 |

## 연구·웹 인계

#417 runner와 #418 등록 명세를 재사용하고 엔진을 복제하지 않는다.
카탈로그 interval→연구 membership adapter는 Main/연구 담당자가 독립적으로 검토한다.
각 의사결정 시점에 available_at으로 필터한 원장 재생 결과만 소비해야 한다.
최신 snapshot의 수정된 과거 구간을 모든 과거 시점에 그대로 쓰면 look-ahead다.
특정 과거 cutoff 재현은 그 시점 이하로 보존 원장을 새 스냅샷에서 재생한다.
현재 core의 기존 snapshot을 과거로 되돌리는 API는 CUTOFF_REGRESSION으로 거절한다.

카탈로그 범위를 넓혀도 기존 504 QGV 점수를 복사하지 않는다. 연구 비교군 전체를
동일 as_of/score_universe/score_basis로 재산정하는 계약은 #417/#418 소유다.
백테스트 실행은 로컬/비공개 연구 환경이다. 웹 9.1은 사용권을 확인한 사전 계산
집계 결과만 읽는다. 이번에 웹 화면·가격 다운로드·백테스트 실행 버튼을 만들지 않는다.
