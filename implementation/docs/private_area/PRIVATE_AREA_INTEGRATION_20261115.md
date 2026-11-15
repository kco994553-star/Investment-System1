# 비공개 구역 통합 — Worker `/kis/*`와 새 앱 비공개 칸 (2026-11-15)

오너 2026-11-15: #536→#538→#550 묶음은 통째로 병합하지 않고, 비공개 구역에 필요한 부분만 기본 가지 위 가지 하나(`claude/private-area-integration`)로 옮긴다. 기준: DC-44·DC-52·DC-53, [읽기 토큰 만료 계약](WORKER_READ_TOKEN_EXPIRY_20261115.md). 같은 날 오너 보완: 최소 기능(숫자·표·기준일·짧은 표지), 운영 정보는 상태 칸으로.

## 들어온 것

| 부분 | 내용 | 출처 |
| --- | --- | --- |
| Worker | `/kis/status`·`chart`·`analysis`·`technical`·`qgv` 다섯 경로. 기존 Google tokeninfo 확인(aud, 검증된 이메일과 `ALLOWED_EMAIL`, email_verified, 만료)과 요청 제한을 그대로 거침. 비공개 저장소 `data` 가지를 읽기 토큰으로 읽고 바이트를 그대로 넘김, `no-store` | #493, #550 |
| 읽기 토큰 | `PRIVATE_REPO_READ_TOKEN_EXPIRES_ON`의 정확한 `NEVER`만 `NO_EXPIRY`(날짜·남은 일수 `null`). 누락·오류는 설정 오류. `/kis/status`는 `status/private-area.json`을 Contents API로 읽어 캡처 시각 기준으로 다시 검증, 날짜·`NEVER`가 다르면 `TOKEN_EXPIRY_MISMATCH`. 무기한 토큰의 GitHub 401은 `TOKEN_REJECTED`(만료로 추측 안 함) | #550, DC-53 |
| 새 앱 | `kis-private.js`(읽기·검증·인증 연결), `private-expand-live.js`(공통 칸 부품). 기술 2-1(`tech-kis-chart`): 표지 「KIS · 비공개」, 가격 기준일, 원주가/확인된 분할 반영, 채택값만, 기준 불일치(BASIS_MISMATCH)면 지표를 붙이지 않음. QGV(`qgv-kis`): 「KIS · 비공개 · 공식 아님」, 가격 기준일·출처, Q·G·V(미산출은 0이 아님), V 없으면 총점 없음, 순위 없음 | #493, #550 |
| 상태 | 준비 중 · 로그인 필요 · 불러오는 중 · 표시 · 자료 없음 · 오류, 서버 403·Google 만료는 다시 로그인. 수집 시각·증거·설정 판·기준일 비교와 읽기 토큰 상태 확인(「만료일 없음」)은 칸의 「상태」 상자에. 문제가 있을 때만 칸에 한 줄 | 오너 2026-11-15 |
| 격리 | 로더는 두 비공개 파일이 없거나 실행 중 오류가 나도 공개 층을 실패시키지 않는다(`IS2.loadSkipped()`에 이름만 남김). 칸은 준비 중으로 남는다 | 오너 2026-11-15 |
| 기호 | Worker와 읽기 모두: Universe504 목록에 승인 ETF 15개(SPY, HYG, IEF, SMH, XLK, XLV, XLE, XLB, XLP, XLY, XLC, XLU, XLRE, XLF, XLI)를 더함. 종류주 둘은 앱이 `BRK-B`·`BF-B`로 묻고 Worker가 저장 폴더 키 `BRK_B`·`BF_B`를 읽으며, 파일의 `BRK/B`·`BF/B`는 요청 기호와 Universe 코드(`NYSE:BRK.B`·`NYSE:BF.B`)로 맞춘다. 그 밖은 거부 | 오너 2026-11-15 |
| 검증 표지 | Codex #556(`research/private_kis_reference.py`)의 표시 필드만 읽는다. 지표마다 `validation_tier`가 VERIFIED이면 채택값과 「검증됨」, UNVERIFIED_REFERENCE이면 `reference_value`와 「검증 전(참고)」(채택값 자리에 올리지 않음). 파일 `display.state`가 WITHHELD이면 참고값·차트 없이 보류 사유 한 줄. 표시 필드가 없거나 모르는 값이면 값 없이 「검증 표시 없음」 한 줄(검증됨 없음). 화면은 검증을 스스로 판정하지 않는다. 시험 자료는 Codex 코드(2abdd286)를 합성 계약에 돌린 출력(`tests/fixtures/kis_private_reference_556_synthetic.json`) | 오너 2026-11-15, #556 |
| KIS V 1단계 | 공식 방법(calc 23.1)에 KIS 종가를 넣은 `official_reference` 결과(`kis-qgv/1`)를 그대로 읽어 계산 판·가격 기준일·출처·표지를 보이고, 순위는 없음(`rank` null). 총점은 세 축이 다 있을 때만 보이고, 산출기가 가린 부분 총점(`total_policy` THREE_AXES_REQUIRED_PRIVATE_OUTPUT, 행 `total_reason` THREE_AXES_REQUIRED)은 「총점 미산출 · 세 축 필요」 한 줄. `coverage.total`·`diagnostics`는 받은 그대로 보이고 다시 세지 않으며, 정책과 어긋나는 파일은 거부. 단계 수·주식수/신원 기준은 상태 상자. 필드 목록은 한 곳(`QGV_FIELDS`·`QGV_OPTIONAL`). 크기: 합성 출력 523행(`private_raw_detail` 포함) 1,153,835바이트, 행당 약 1.9 KB라 실자료도 약 1.2~1.4 MB로 Worker 파일 한도 2 MiB 안(한도 변경 없음). 555는 2단계(범위 밖) | 오너 2026-11-15, #556 |
| 가격 이력 기능 | 새 앱의 공개 가격 이력 기능 둘을 오너 비공개로 옮김(오너 2026-11-15): 기술 3.1.1 「일봉 불러오기」(Worker `/history`)와 QGV 2.1.4 기간별 수익률 1D/5D/20D(구글 시트 `Prices_D`). 로그인 전에는 그 자리에 「비공개 로그인 필요」만(`data-private-gate`, 버튼·요청 없음, 수익률 칸은 「— 비공개」), 로그인 뒤에는 전과 같이 동작. `/history`는 Worker가 매번 오너를 확인하고, 2.1.4는 로그인한 사용자 자신의 시트만 읽으므로 화면 쪽 구분이다. 지금 사이트(web_assets)는 바꾸지 않음 | 오너 2026-11-15 |

빠진 것: `/kis/classification`·`/kis/macro`·`/kis/news`와 QGV 333/555·Top500·두 모형·섹터·관계·매크로 관측·뉴스 갱신 전부. 화면은 점수·순위를 다시 계산하지 않는다.

## Pages 미리보기 게시 — 좁은 가드 예외 (오너 승인 2026-11-15)

Pages 가드(`pages_artifact_guard.py`)는 게시 파일 코드 안의 비공개 Worker 경로(`private_area_paths`)와 비공개 스키마 이름(`private_area_schema`)을 막는다. `kis-private.js`는 둘 다 담는다(경로 5개, 스키마 이름 5개가 가드 패턴에 10번 걸림). 설계 §20.1의 "파일 하나·주소 하나로 좁힌 예외"를 오너가 2026-11-15에 승인했고, 가드의 `PAGES_PRIVATE_EXCEPTIONS`가 그 예외 하나만 담는다.

| 조건 | 내용 |
| --- | --- |
| 파일 | 산출물 맨 위의 `kis-private.js` 하나(전체 상대 이름). 하위 폴더·다른 이름이면 예외 없음(허용 목록 밖 파일로 실패). `private-expand-live.js`는 가드 규칙에 걸리는 문자열이 없어(경로·스키마·KIS 표지 0) 예외가 필요 없다 |
| 바이트 고정 | 게시 바이트의 sha256을 예외 기록에 따로 고정(`APPROVED_SHA256`과 같은 값). 바이트가 다르면 예외가 전혀 적용되지 않아 경로 5·스키마 10과 `unapproved_content`로 실패. 바꿀 때는 두 고정값을 같은 PR에서 다시 맞춤 |
| 허용 경로(정확히 5) | `/kis/status`, `/kis/chart`, `/kis/analysis`, `/kis/technical`, `/kis/qgv` — 각각 작은따옴표 문자열로 정확히 한 번. 빠지거나 두 번이거나 다른 따옴표면 하나도 면제하지 않음. 그 밖의 `/kis/`·`/lab/`·`/private/`는 그대로 실패 |
| 허용 스키마 이름(파일에 있는 그대로 5) | `kis-bars/1`, `kis-bars/1/analysis`, `kis-technical-measures/1`, `kis-qgv/1`, `kis-status/1` — 정확한 철자의 온전한 낱말(앞뒤에 글자·숫자·`_ . / -`가 붙지 않음)만. 다른 `kis-`·`private-` 이름, 다른 대소문자는 그대로 실패 |
| 그대로인 것 | 한도(파일당 2 MiB, 192개), CSP, KIS 표지·비밀 패턴·민감 키·JSON 검사, 다른 모든 파일의 규칙. JSON에는 예외 없음 |

미리보기(`web_app_preview.py`)는 `OWNER_PRIVATE` 제외를 없애고 두 파일과 `loader.js` 전체를 web_app과 같은 바이트로 게시한다. 바뀐 게시 파일의 고정값: `kis-private.js`·`private-expand-live.js`(새로 더함), `loader.js`(다시 맞춤). Pages 파일 수: 로컬 빌드 176 → **178**, 라이브 전용 공개 자료 7개를 더한 배포 183 → **185**(한도 192).

공개 방문자는 로그인 전 KIS 칸에 「로그인 필요」만 보고 Worker에 아무 요청도 보내지 않는다(읽기는 로그인 클릭 뒤, Worker가 매번 오너 확인). 두 파일이 없거나 실행 중 오류가 나도 공개 화면은 같다(로더 `IS2.loadSkipped()`).

실사용 전 남은 일: ① Worker Secret/Text 반영과 `private-worker` 승인 배포 ② 비공개 저장소 `data` 가지의 `chart/`·`technical/`·`measures/`·`qgv/latest.json`·`status/private-area.json` 게시(수집기·상태 산출기, 별도 승인). (Pages 가드 예외와 `OWNER_PRIVATE` 해제는 `claude/pages-guard-kis-private-exception`에서 끝남.)

## 시험

- Worker: `implementation/worker/tests/kis.test.mjs`(익명·다른 계정·만료 거부, `NEVER`/`NO_EXPIRY`, 거부와 불일치 구분, `no-store`, 스키마 검사, 빠진 경로 404).
- 노드: `web_app_kis_private_node_test.js`. 브라우저: `web_app_kis_private_browser_test.js`(개발 빌드와 게시된 Pages 산출물 `app.html` 둘 다), `web_app_private_isolation_browser_test.js`(게시된 Pages 산출물 — 가드 PASS, 두 파일 포함 — 과 그 임시 복사본: 공개 방문자 Worker 요청 0, Worker 403·500·잘못된 JSON·스키마 불일치, 비공개 스크립트 오류·누락에도 공개 화면 같음).
- 가드: `tests/test_pages_artifact_guard.py`가 예외의 실패 경우를 확인한다 — 다시 고정해도 실패하는 추가 `/kis/` 경로와 추가 스키마 이름, 고정값을 안 바꾼 바이트 변경, 같은 문자열을 담은 다른 파일(JSON 포함), 다른 위치(하위 폴더·다른 이름·tar 하위 항목)의 예외 파일.
- 경계: `tests/test_private_boundary_static.py`의 좁은 예외는 다섯 경로로 줄였다. `tests/test_web_app_preview.py`는 두 파일과 `loader.js` 전체가 같은 바이트로 게시되고 파일 수가 178(+라이브 전용 7 = 185 ≤ 192)임을 확인한다.
