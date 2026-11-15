# 읽기 토큰 만료 계약 — 2026-11-15 오너 변경

오너가 `worker-private-repo-read`를 만료일 없이 재발급했다. 날짜 누락을 무기한으로 해석하지 않는다. 이 문서는 NO_ZT 설계 4.4절과 폰 설정의 날짜 필수 방침을 다음으로 바꾼다. 토큰 값·권한·오너 인증은 이 계약의 입력이나 출력이 아니다.

| 설정값 | 만료 상태 | 날짜 / 남은 일수 |
| --- | --- | --- |
| 정확한 `NEVER` | `NO_EXPIRY` | 둘 다 `null` |
| 실제 `YYYY-MM-DD`, 오늘보다 15일 이상 뒤 | `OK` | 다시 만든 날짜 / 정수 |
| 실제 날짜, 1~14일 뒤 | `EXPIRING` | 다시 만든 날짜 / 정수 |
| 실제 날짜, 오늘 또는 과거 | `EXPIRED`, `TOKEN_EXPIRED` | 다시 만든 날짜 / 0 이하 정수 |
| 누락·빈 값·다른 대소문자·공백 포함·잘못된 날짜·367일보다 먼 미래 | `UNSET`, `TOKEN_DATE_INVALID` | 둘 다 `null` |
| 토큰처럼 생긴 설정값 | `UNSET`, `TOKEN_DATE_IS_TOKEN` | 둘 다 `null`; 원문을 반환하거나 기록하지 않음 |

오늘과 남은 일수는 Asia/Seoul 달력으로 센다. 무기한은 토큰이 유효하다는 뜻이 아니다. 취소·잘못된 토큰·GitHub 인증 실패·권한 부족·요청 제한·리다이렉트·장애를 날짜와 별도로 검사한다. GitHub 401은 무기한 토큰에서 `TOKEN_REJECTED`이며 만료로 추측하지 않는다. 유기한 토큰의 기존 401 근접 만료 판정과 사전 만료 차단을 유지한다.

## 실제 설정

- 비공개 저장소 Actions 변수 `WORKER_READ_TOKEN_EXPIRES_ON`: 기존 `2027-02-13`을 **`NEVER`로 교체**한다. 변수 삭제나 빈 값으로 무기한을 표현하지 않는다.
- Worker Secret `PRIVATE_REPO_READ_TOKEN`: 오너가 재발급한 값을 Secret 입력란에만 넣는다. 에이전트에게 값이 전달됐다고 가정하지 않는다.
- Worker Text `PRIVATE_REPO_READ_TOKEN_EXPIRES_ON`: **`NEVER`**. 가짜 날짜·옛 날짜를 넣지 않는다.
- 유기한 토큰으로 다시 바꿀 때는 두 설정에 실제 날짜를 적는다.

현재 세션은 GitHub 변수 API와 Secrets API에서 403을 받았다. Cloudflare MCP는 등록됐지만 인증 전이다. 따라서 이 문서나 코드 변경만으로 실설정이 바뀌었다고 보고하지 않는다.

## 산출·전달·표시

기존 `kis_collector.py`의 `store`가 `data` 가지의 `status/private-area.json`도 쓴다. 별도 `token-status --data <경로>`는 가격 수집이나 KIS 인증 없이 만료 설정만 갱신한다. 기존 KIS 파일은 바꾸지 않는다.

상태 파일은 `private-area-status/1`, `publication_scope: OWNER_PRIVATE_ONLY`, `run_at`, `worker_read_token`, `collection`으로 구성한다. `worker_read_token`은 `state`, `code`, `expires_on`, `days_left`, **`verification: NOT_CHECKED`**만 갖는다. 산출기는 읽기 토큰을 받지 않으므로 GitHub 권한 확인을 주장하지 않는다. `collection`은 기존 수집 상태의 허용된 정수 개수만 담으며, 확인할 수 없으면 `null`이다. 공개 저장소·Pages에는 이 파일을 넣지 않는다.

Worker의 오너 인증 `/kis/status`는 GitHub Contents API로 이 파일을 읽는다. Metadata 권한만으로 성공을 선언하지 않는다. 404는 권한이나 상태 파일 부재를 확인해야 하는 거부 상태다. 상태 파일의 캡처 시각을 기준으로 날짜 상태를 다시 검증하고, 두 곳의 날짜 또는 `NEVER` 설정이 다르면 `TOKEN_EXPIRY_MISMATCH`로 닫는다. 원문이나 임의의 GitHub 본문은 반환하지 않는다.

화면은 로그인 후 사용자가 누르는 “읽기 토큰 상태 확인”으로만 이 경로를 읽는다. `NO_EXPIRY`는 “만료일 없음”, 유기한은 실제 날짜·14일 경고, 거부·오류는 별도 문구다. 로그인하지 않음·다른 오너·Google 세션 만료는 기존 서버 검사로 거부한다.

## 반영 순서

1. 산출기 변경을 기본 가지에 병합하고, 비공개 수집 워크플로의 고정 공개 SHA를 검토한 커밋으로 옮긴다.
2. 비공개 워크플로의 키 없는 단계에만 만료 변수를 전달하고 `status` 폴더도 커밋한다. 수집은 여전히 수동이며 이 변경으로 실행하지 않는다.
3. 변수 교체 뒤 메타데이터 전용 수동 워크플로로 상태 파일을 갱신한다. KIS 가격 수집이나 토큰 발급은 하지 않는다.
4. 기존 Draft의 Worker·화면 변경과 이번 계약을 승인된 기본 가지에 통합한다. 승인 환경 연결 PR #548도 필요하다.
5. Worker Secret/Text 저장·반영을 확인한 뒤 기존 `private-worker` 승인 절차로 배포한다. MCP 직접 배포로 우회하지 않는다.
6. 실환경의 오너 조회·비오너/만료 거부·비공개 파일 읽기를 확인한다. 성공 전에는 옛 토큰·비밀값을 삭제하지 않는다.
