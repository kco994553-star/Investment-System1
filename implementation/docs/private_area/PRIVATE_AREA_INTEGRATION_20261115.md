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
| 검증 표지 | 칸마다 짧은 표지 하나: 「검증됨」(칸의 모든 파일이 자기 필드로 검증을 밝힐 때: 일봉 `price_scope_status` CONFIRMED, 분석·측정 `pit_status` VERIFIED, QGV `historical_pit_proven` true) 또는 「검증 전(참고)」. 보류 항목은 사유 한 줄만 | 오너 2026-11-15 |
| KIS V 1단계 | 공식 방법(calc 23.1)에 KIS 종가를 넣은 결과를 `kis-qgv/1`로 읽어 계산 판·가격 기준일·출처를 보인다. 필드는 Codex와 #437에서 맞추는 중이라 #493 판독 모양을 쓰고 목록을 한 곳(`QGV_FIELDS`·`QGV_OPTIONAL`)에 둔다. 555는 2단계(범위 밖) | 오너 2026-11-15 |
| 가격 이력 기능 | 새 앱의 공개 가격 이력 기능 둘을 오너 비공개로 옮김(오너 2026-11-15): 기술 3.1.1 「일봉 불러오기」(Worker `/history`)와 QGV 2.1.4 기간별 수익률 1D/5D/20D(구글 시트 `Prices_D`). 로그인 전에는 그 자리에 「비공개 로그인 필요」만(`data-private-gate`, 버튼·요청 없음, 수익률 칸은 「— 비공개」), 로그인 뒤에는 전과 같이 동작. `/history`는 Worker가 매번 오너를 확인하고, 2.1.4는 로그인한 사용자 자신의 시트만 읽으므로 화면 쪽 구분이다. 지금 사이트(web_assets)는 바꾸지 않음 | 오너 2026-11-15 |

빠진 것: `/kis/classification`·`/kis/macro`·`/kis/news`와 QGV 333/555·Top500·두 모형·섹터·관계·매크로 관측·뉴스 갱신 전부. 화면은 점수·순위를 다시 계산하지 않는다.

## Pages 미리보기에는 아직 게시하지 않음

Pages 가드(`pages_artifact_guard.py`)는 게시 파일 코드 안의 비공개 Worker 경로(`private_area_paths`)와 비공개 스키마 이름(`private_area_schema`)을 막는다. `kis-private.js`는 둘 다 담는다(경로 5, 스키마 이름 9). 설계 §20.1은 이때 "파일 하나·주소 하나로 좁힌 예외를 오너 승인과 함께 더한다"고 정했지만 Pages 가드 예외는 아직 승인되지 않았고, 이 가지는 가드를 풀지 않는다. 그래서 미리보기(`web_app_preview.py` `OWNER_PRIVATE`)는 두 파일을 게시하지 않고 `loader.js`의 그 한 줄만 뺀 판을 게시한다. 공개 화면은 지금과 같고 비공개 칸은 「비공개 기능 준비 중」이다. 개발 빌드(`build_web_app.py`)와 시험에는 두 파일이 있다.

실사용 전 남은 일: ① Pages 가드의 좁은 예외(파일 `kis-private.js` 하나, 경로·스키마 이름 고정) 오너 승인과 그 PR ② 미리보기의 `OWNER_PRIVATE` 제외 해제 ③ Worker Secret/Text 반영과 `private-worker` 승인 배포 ④ 비공개 저장소 `data` 가지의 `chart/`·`technical/`·`measures/`·`qgv/latest.json`·`status/private-area.json` 게시(수집기·상태 산출기, 별도 승인).

## 시험

- Worker: `implementation/worker/tests/kis.test.mjs`(익명·다른 계정·만료 거부, `NEVER`/`NO_EXPIRY`, 거부와 불일치 구분, `no-store`, 스키마 검사, 빠진 경로 404).
- 노드: `web_app_kis_private_node_test.js`. 브라우저: `web_app_kis_private_browser_test.js`(개발 빌드), `web_app_private_isolation_browser_test.js`(Pages 빌드와 임시 복사본: 공개 방문자 Worker 요청 0, 비공개 스크립트·자료 실패에도 공개 화면 같음).
- 경계: `tests/test_private_boundary_static.py`의 좁은 예외는 다섯 경로로 줄였다. `tests/test_web_app_preview.py`는 두 파일이 게시되지 않음을 확인한다.
