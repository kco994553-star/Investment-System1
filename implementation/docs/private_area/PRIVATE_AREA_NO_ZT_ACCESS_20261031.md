# 1인 비공개 구역 — Cloudflare Zero Trust 없이 본인 전용 접근 (조사·설계·검증, 2026-10-31)

상태: **설계 승인(10/31 `PRIV-AUTH-GOOGLE`: Google 토큰 + Worker 확인으로 시작, 패스키는 나중).** 배포, KIS 호출, 운영 설정 변경(Cloudflare·GitHub Secrets·워크플로)은 구현 PR마다 오너 승인 뒤에 한다. **KIS 키는 비공개 저장소 `investment-system1-kis-private`의 Actions Secrets에만 둔다**(10/31 오너). 공개 저장소의 KIS Secrets(`KIS_APP_KEY`·`KIS_APP_SECRET`)는 오너가 지웠다(10/31). 공개 저장소의 코드·설정·워크플로·자료 파일은 KIS Secret 이름을 쓰지 못한다(가드, 문서만 허용).

원문(사용자, 2026-10-31): 「투자시스템의 GitHub 비공개 저장소 생성, KIS_APP_KEY 및 KIS_APP_SECRET 등록, 기존 브랜치·로그 정리를 완료했다. Cloudflare Zero Trust는 결제 수단이 없어 보류한다. 대신 기존 Cloudflare Workers 무료 환경에서 개인 전용 접근 제어를 구현하는 방향으로 진행한다. … 특히 인증 우회, 토큰 노출, 비밀값의 클라이언트 전달, 공개 API를 통한 비인가 데이터 접근을 중점 검증하라. 현재 단계에서는 조사·설계·검증까지만 진행하고, 실제 배포와 KIS 호출 및 운영 설정 변경은 오너의 승인을 받은 뒤 수행하라.」

이 문서는 [설계](PRIVATE_AREA_KIS_DESIGN_20261031.md) 5절(Cloudflare Access)·11절 4~6단계·17.5절(로그인 빈도)을 **대체한다(10/31 승인).** 나머지(수집·저장·차트 계약·가드·원칙)는 그대로다. `PRIV-PAYMENT`(Zero Trust 결제 수단)는 불필요하다.

## 1. 지금 구조 (조사)

| 구성 | 사실 |
| --- | --- |
| 공개 저장소 `Investment-System1` | canonical 워크플로에 `secrets.KIS_`를 쓰는 곳이 없다. KIS를 부르는 워크플로는 Codex 연구 가지 2곳(`research/bt-data-pilot-alpaca-probe-20261031`, `research/lab-contract-private-pilot-20261031`)의 `bt-data-pilot-kis.yml`·`bt-data-pilot-pre2016.yml`뿐이다. 둘 다 **그 연구 가지에 워크플로 파일 자체를 바꾸는 push**가 있을 때만 돈다. 10/31 07:17 UTC 이후 실행 없음(총 10회, 로그에 값 없음은 앞서 확인). 공개 저장소의 KIS Secrets는 오너가 지웠다(10/31) |
| 새 비공개 저장소 | **`investment-system1-kis-private`**(10/31 오너가 앞 하이픈을 빼고 이름을 바꿈. 문서·설정은 새 이름만 쓰고 옛 주소 자동 연결에 기대지 않는다). 지금 내용은 `README.md` 하나. 워크플로·자료 없음. Secrets(`KIS_APP_KEY`·`KIS_APP_SECRET`)는 오너가 등록했다고 했고, 세션은 값은 물론 목록도 읽지 않았다 |
| 기존 Worker `private-investment-history` | `implementation/worker/src/index.js`. 경로는 `/history` 하나. **이미 본인 전용 인증이 있다:** 브라우저가 보낸 Google OAuth 접근 토큰을 Worker가 Google `tokeninfo`로 서버에서 확인하고, `aud`(앱의 OAuth 클라이언트 ID)·`email`(Worker 비밀값 `ALLOWED_EMAIL`)·`email_verified`·만료를 본다. 그 밖에 출처(`Origin`) 확인, 요청 한도(Durable Object, 분당 12회), `Cache-Control: private, no-store`, 로그 끔(`observability enabled=false`). Worker 비밀값: `ALLOWED_EMAIL`·`GOOGLE_CLIENT_ID`·`TIINGO_API_KEY`·`KRX_API_KEY`(KIS 없음). 배포는 공개 저장소의 수동 `private-history-deploy.yml`(기본 가지에서만). 코드를 읽어 확인한 점: 인증이 위쪽(Yahoo 등) 요청보다 먼저 돌고, 실패하면 닫힌다(403/503). 사전 요청(OPTIONS)은 자료 없이 CORS 헤더만 준다. Worker 시험 169개 통과(10/31 전체 시험) |
| 앱 | 공개 Pages(`kco994553-star.github.io`). CSP `connect-src`에 이 Worker 주소와 Google이 이미 있다. 옛 화면의 Google 로그인은 GIS 토큰 방식(`google-sheet-quotes.js`, 시트용) |

## 2. KIS 키 노출 검증 (10/31, 값은 보지 않음)

| 경로 | 확인 방법 | 결과 |
| --- | --- | --- |
| 공개 저장소 파일 | 가지 491개 전부에서 워크플로의 `secrets.KIS_` 검색, canonical·두 연구 가지에서 KIS 앱키 모양(`PS`+영숫자 34자) 검색 | 앱키 모양 일치는 글꼴 CSS의 base64 3건뿐(오탐). 키 값 없음 |
| 빌드 산출물(Pages) | 로컬 빌드 사이트 137개 파일과 라이브 `index.html`·`app.js`에서 KIS 호스트·TR 번호·Secret 이름·앱키 모양 검색 | 없음. `app.js`의 `appsecret`은 민감 키 이름 차단 목록(가드) |
| 브라우저 | 새 앱·옛 화면 코드에 KIS 호출·키 없음. Worker도 KIS 키를 갖지 않는다 | 노출 경로 없음 |
| 공개 Actions 로그 | Codex 10회는 값 없음(앞서 확인). Main의 `kis-verify-once` 3회 로그는 오너가 지움 | 남은 값 없음 |
| 비공개 저장소 | README 하나 | 노출 없음 |

**지난 위험(10/31 해소):** 공개 저장소의 KIS Secrets는 공개 저장소에 쓰기 권한이 있는 사람(오너·Claude 앱)이 워크플로를 바꾸면 읽힐 수 있었다. 확인 결과 그 Secrets를 쓰던 것은 위 두 Codex 연구 가지 워크플로뿐이었고, 오너가 Secrets를 지웠다(10/31). 두 워크플로는 이제 돌면 KIS 단계에서 실패한다. **Disable workflow**로 꺼 두는 것은 그대로 권장한다(삭제 아님, `PRIV-CODEX-WF-OFF`). 같은 쓰기 권한 경로가 공개 저장소의 Cloudflare 토큰에는 아직 남아 있다(4.3절 남은 위험, `private-worker` 환경으로 막는다).

## 3. 실행 경로 — 비공개 저장소의 Secrets만 쓴다

공개 저장소와 Secrets를 자동으로 공유한다고 가정하지 않는다. KIS 키는 **비공개 저장소의 Actions 실행기 메모리 안에서만** 쓰인다.

```
[비공개 저장소 Actions]  kis-collect.yml (일정 / 수동)
   ├ 공개 저장소를 고정 커밋 SHA로 checkout(읽기, 토큰 불필요) → 기본 가지 조상 확인 → 수집기 모듈 실행
   ├ KIS_APP_KEY / KIS_APP_SECRET: 수집 한 단계의 env로만, 자식 프로세스에 넘기지 않음
   ├ 토큰 1회 발급 → 시세 호출(허용 목록) → 끝에 폐기
   └ 결과: 비공개 저장소 data 가지에 커밋(GITHUB_TOKEN, contents: write) · 로그는 개수·코드만
[Cloudflare Worker]  /kis/* (읽기 전용)
   └ 비공개 저장소를 읽기 전용 토큰(Worker 비밀값)으로 읽어 본인에게만 전달 — KIS 키는 Worker에 없다
[브라우저]  로그인한 오너만 /kis/* 호출 → 비공개 칸(privatePanel)에 표시
```

- **KIS 키를 읽는 코드는 비공개 저장소에만 둔다(10/31 오너).** 비공개 저장소의 실행 스크립트가 Secrets를 환경에서 읽어, 공개 저장소 수집기 모듈에 함수 인자로 넘긴다. 공개 모듈은 Secret 이름을 쓰지 않는다(가드가 막는다).
- 수집기 코드는 공개 저장소에 두고 가드·시험으로 검사한다. 비공개 워크플로는 그 코드를 **전체 커밋 SHA로 고정**해 쓴다. SHA를 바꾸는 것은 비공개 저장소의 PR(Main 작성·오너 승인)이다. 공개 저장소에서 수집기를 실행하면 스스로 멈춘다(`GITHUB_REPOSITORY` 확인).
- 비공개 워크플로 규칙: 외부 action은 SHA 고정, `pull_request_target` 없음, 결과물(artifact) 없음, `set -x` 없음, 응답 본문·가격 출력 없음, 토큰 발급은 실행마다 1회(카카오톡 알림 1회).
- **고정 SHA가 검토된 공개 코드인지 확인한다(보안 검토 A2, 10/31).** GitHub는 포크 네트워크 전체에서 SHA로 커밋을 찾아 주므로, SHA 고정만으로는 그 코드가 공개 기본 가지에서 왔다는 증거가 안 된다. `kis-collect.yml`(수집기 PR에서 Main이 쓴다)은:
  1. 공개 저장소를 `fetch-depth: 0`, `filter: blob:none`, **`persist-credentials: false`**로 checkout한다(비공개 저장소의 쓰기 `GITHUB_TOKEN`이 공개 쪽 `.git/config`에 남지 않게).
  2. 바로 다음 단계에서 공개 기본 가지 `claude/investment-system-top500-validation-alrugm`을 받아(`git -C pub fetch --no-tags --filter=blob:none origin '+refs/heads/claude/investment-system-top500-validation-alrugm:refs/remotes/origin/default'`) `git -C pub merge-base --is-ancestor "$PINNED_SHA" refs/remotes/origin/default || exit 1`로 고정 SHA가 그 가지의 조상인지 확인한다. 아니면 KIS 단계 전에 멈춘다. `PINNED_SHA`는 워크플로 파일 안에만 둔다(다른 파일에서 읽지 않는다).
  3. action은 `actions/*`만 쓰고 SHA로 고정한다. 각 SHA가 어느 릴리스 태그인지 PR에 적는다(SHA ↔ 태그).
  4. 수집 잡에는 `pip install`이 없다. 수집기는 표준 라이브러리만 쓰고(수집기 PR에서 `kis_collector.py`를 import 고정 시험에 넣는다. 네트워크 표준 모듈은 허용, 제3자 패키지 금지), `python -I`(사용자·현재 폴더 경로 무시)와 checkout 경로를 명시한 `sys.path`로 실행한다.
- **비공개 저장소의 쓰기 권한 = KIS 키 접근(보안 검토 A3, 10/31).** GitHub Free 비공개 저장소에는 보호 가지·규칙·환경 보호가 없다. 그래서 쓰기 권한이 있는 자격 증명은 무엇이든 워크플로나 워크플로가 읽는 파일을 바꿔 KIS Secrets를 읽을 수 있고, "Main 작성·오너 승인"(DC-35)은 GitHub가 강제하지 않는다. 그래서:
  1. Claude GitHub 앱은 워크플로를 처음 넣을 때만 이 저장소에 추가하고, 넣은 뒤 **바로 뺀다**(폰 설정 1.3단계). 오너가 파일을 직접 붙여 넣는 방법도 된다.
  2. KIS Secrets를 읽는 코드는 **워크플로 YAML 안에 직접**(inline) 두거나, 위 조상 확인을 거친 공개 SHA의 코드에만 둔다. 워크플로가 읽는 비공개 저장소의 `.py`·설정 파일이 Secrets를 다루지 않게 한다(Contents 쓰기만 있으면 Workflows 권한 없이도 그런 파일을 바꿀 수 있기 때문이다).
  3. Codex는 이 저장소에 **Contents: Read-only + Issues: Read and write**만 받는다. 요청은 이슈로 낸다(설계 20절). `issues: types: [opened]` 워크플로가 이슈 본문을 env 변수로 받아(`run:` 안에 `${{ github.event.issue.body }}`를 쓰지 않는다) `research_request.parse_request`로 검사하고, 결과는 그 워크플로의 `GITHUB_TOKEN`이 쓴다.
  4. 비공개 저장소 워크플로의 실행 조건은 `schedule`·`workflow_dispatch`·`issues`뿐이다. **`push`·`pull_request`는 쓰지 않는다**(push 워크플로는 아무 가지에서나 Secrets를 받는다).
- 1단계에는 장중가가 없으므로(PRIV-INTRADAY (a)) Worker가 KIS를 부를 일이 없다. 그래서 KIS 키를 Cloudflare에 넣지 않는다.
- 저장: 비공개 저장소의 `data` 가지(설계 4절·17.2절 파일 배치). **R2·KV는 쓰지 않는다:** R2는 켤 때 결제 수단이 필요하고, KV 무료는 하루 쓰기 1,000회라 매일 약 3,100종목 갱신에 모자란다.
- 저장소 크기: 연도별 파일에 하루 한 줄씩 더하는 구조라 git 차이 압축으로 늘어나는 양이 작다. 1 GB를 넘기 전에 연 단위 정리를 제안한다(강제 push는 쓰지 않는다).

### 3.1 첫 시험 실행 — 인증 확인 1회 (10/31 오너 지시, 결과)

| 항목 | 결과 |
| --- | --- |
| 워크플로 | 비공개 저장소 `.github/workflows/kis-auth-check.yml`(수동 실행만) + `tools/kis_auth_check.py`. 토큰 발급(`/oauth2/tokenP`)과 폐기(`/oauth2/revokeP`) 두 경로만 허용, 시세·주문·계좌·잔고 호출 없음. 다른 저장소에서 돌면 멈춤 |
| 실행 | run 41191280649 (10/31 10:05 UTC), 성공 |
| Secret 이름 | `KIS_APP_KEY=present`, `KIS_APP_SECRET=present` — 설계 문서 이름과 같음(값은 보지 않음) |
| 인증 | 토큰 발급 HTTP 200(유효 86,400초) · 폐기 HTTP 200 |
| 로그 | 정해진 세 줄뿐. 키·토큰·응답 본문 없음. 카카오톡 토큰 알림 1건 |
| 후속(보안 검토 A3, 10/31) | 지금은 `kis-auth-check.yml`이 Secrets를 다루는 `tools/kis_auth_check.py`를 읽는다. 위 3절 규칙 2에 맞게 **Main이 비공개 저장소에서 그 스크립트 내용을 워크플로 YAML 안으로 옮기고 `.py`를 지운다**(이 공개 PR에서는 하지 않는다. 비공개 저장소 변경이라 오너 승인 뒤 Main이 한다) |

## 4. 본인 전용 인증 — Zero Trust 없이 서버에서 검증

### 4.1 후보 비교

| 방식 | 서버 검증 | 무료·결제 수단 | 아이폰 | 구현 부담 | 판단 |
| --- | --- | --- | --- | --- | --- |
| **A. Google 로그인 토큰 + Worker의 Google `tokeninfo` 확인** | Google이 토큰을 확인하고, Worker가 `aud`·`email`·만료를 본다 | 무료, 결제 수단 없음 | 됨(지금 시트 로그인과 같은 방식) | 작다. **이미 `/history`에서 쓰는 코드**를 그대로 쓴다. 단 그 코드의 `redirect: 'error'` 버그(운영에서 로그인 요청이 503으로 닫힘)를 Worker PR 첫 항목으로 먼저 고친다(7절 3-1, 보안 검토 A4) | **권장(1단계)** |
| B. 패스키(WebAuthn, Face ID) | Worker가 서명을 확인 | 무료 | 좋음 | 중간. 등록 절차·공개키 보관·분실 복구 | 2단계 후보 |
| C. 이메일 일회용 코드(Worker 직접) | 가능 | 메일 발송 서비스 별도 필요 | 됨 | 큼 | 권장 안 함 |
| D. 고정 비밀번호 | 가능 | 무료 | 됨 | 작음 | 권장 안 함(입력·유출·대입 위험) |
| E. GitHub 로그인 | 가능 | 무료 | 됨 | 중간(Worker에 client secret) | A보다 나은 점 없음 |
| Cloudflare Access(원안) | — | Zero Trust 가입에 결제 수단 필요 | — | — | 보류(오너 10/31) |

### 4.2 권장안 A의 동작

1. 오너가 앱에서 "비공개 연결"을 누른다(사용자 클릭일 때만). Google 로그인 창이 뜨고 앱의 OAuth 클라이언트로 **접근 토큰**을 받는다. 범위는 `openid email`만(시트 쓰기 범위를 넣지 않는다). 토큰은 **페이지 메모리에만** 둔다.
   - **토큰 요청은 `scope: 'openid email'`, `include_granted_scopes: false`로 한다(보안 검토 A6, 10/31).** GIS의 기본값은 `true`라서, 같은 OAuth 클라이언트가 시트 로그인으로 이미 받은 `drive.file` 권한이 이 토큰에도 붙는다. 응답의 범위 집합이 `userinfo.email`을 `email`로 바꾼 뒤 **정확히 {openid, email}**이 아니면 토큰을 버린다(`google-sheet-quotes.js`의 `validScope()`와 같은 구조). 선택: Worker가 `/kis/*`에서 tokeninfo 범위에 `drive.file`이 있는 토큰을 거부한다.
   - 기록: 시트의 "연결 끊기"(`google.accounts.oauth2.revoke`)는 이 앱에 준 **모든** 범위를 취소하므로 비공개 연결도 함께 끊긴다.
2. 앱은 `/kis/*`를 부를 때 `Authorization: Bearer <토큰>` 헤더로만 보낸다. 주소·쿼리·저장소(localStorage 등)에는 넣지 않는다.
3. Worker는 모든 `/kis/*` 요청에서 자료를 읽기 **전에** 인증한다.
   - Google `tokeninfo`에 토큰을 보내 확인한다(위조 불가).
   - `aud`가 Worker 비밀값 `GOOGLE_CLIENT_ID`와 같은지 본다. 다른 앱용 토큰은 거부한다.
   - `email`이 Worker 비밀값 `ALLOWED_EMAIL`과 같고 `email_verified`인지 본다.
   - 만료(`exp`·`expires_in`)를 본다.
   - 하나라도 틀리면 403이다. Google이 응답하지 않으면 503으로 막는다(열어 주지 않음).
4. 통과하면 요청 한도(본인 전용 Durable Object)를 거친다. 그다음 허용 목록에 있는 경로·종목만 비공개 저장소에서 읽어 `Cache-Control: private, no-store`로 돌려준다.

- Worker는 기존 Worker에 경로를 더한다. 새 Worker를 만들면 CSP에 주소를 더해야 하므로(CSP 완화) 피한다.
- 로그인 빈도: 접근 토큰은 1시간이다. 새로고침하면 메모리 토큰이 사라진다. 그때 "비공개 다시 연결"을 한 번 누르면 된다. Google에 로그인된 브라우저라면 비밀번호 없이 창이 열렸다 닫힌다. 시크릿 모드는 창을 닫으면 Google 로그인부터 다시 한다. 아이폰 Safari·안드로이드 Chrome·삼성 인터넷 모두 같은 방식이다(제3자 쿠키를 쓰지 않음). 실제 기기 확인은 배포 뒤 점검표로 한다.
- 원안(Access)의 "7일에 한 번 코드"보다 자주 누르게 된다. 줄이려면 2단계에서 B(패스키)를 더한다.

### 4.4 Worker 읽기 토큰 — 저장소 하나·읽기 전용·최소 권한, 만료 경고 (10/31 오너)

- 토큰: GitHub **fine-grained** 토큰. Repository access는 `investment-system1-kis-private` 하나, Repository permissions는 **Contents: Read-only**만(Metadata 읽기는 자동). Account 권한 없음. 만료 90일 권장(최대 1년). 폰 절차는 [폰 설정 4~6단계](OWNER_PHONE_SETUP_PRIVATE_AREA_20261031.md).
- 보관: Cloudflare Worker 비밀값 `PRIVATE_REPO_READ_TOKEN`(이름에 `KIS_`를 쓰지 않음). 만료 날짜는 비밀이 아니므로 Worker 텍스트 변수 `PRIVATE_REPO_READ_TOKEN_EXPIRES_ON`과 비공개 저장소 Actions 변수 `WORKER_READ_TOKEN_EXPIRES_ON`에 적는다.
- **만료일을 어디서 아나:** GitHub 응답 헤더 `GitHub-Authentication-Token-Expiration`은 fine-grained 토큰에서 실제 만료가 아니라 현재 시각을 돌려준다는 보고가 있어(google/go-github#3708) 쓰지 않는다. 오너가 적은 날짜를 기준으로 미리 경고하고, 실제 거부(GitHub 401)로 만료를 확정한다.
- **만료일 값 검사(보안 검토 A5, 10/31):** Worker는 `PRIVATE_REPO_READ_TOKEN_EXPIRES_ON`을 `^\d{4}-\d{2}-\d{2}$`이고 실제 달력 날짜이며 오늘(KST)+367일 이하일 때만 받는다. 응답·화면에는 **Worker가 다시 만든 날짜**만 넣고 변수 원문은 어디에도 넣지 않는다. 그 밖의 값은 `UNSET`(코드 `TOKEN_DATE_INVALID`)이고, `github_pat_`·`ghp_`로 시작하는 값(두 칸을 바꿔 넣어 토큰이 평문 변수에 들어간 경우)은 따로 `TOKEN_DATE_IS_TOKEN`이다. 이때 오너는 그 토큰을 지우고 폰 설정 4단계로 새로 만든다(폰 설정 5단계).
- 상태와 화면 — **아래 순서대로 처음 맞는 줄 하나**로 정한다(보안 검토 A4, 10/31). "오늘"과 남은 날은 **Asia/Seoul 날짜**로 센다. 만료 경고(`EXPIRING`)는 1~2번에 걸리지 않고 3~7번 응답도 없을 때 남은 날로 정한다:

| 순서 | 조건 | 상태·코드 | 화면(비공개 칸) | 상태 파일 |
| --- | --- | --- | --- | --- |
| 1 | 비밀값이 없음, 또는 날짜가 없거나 위 검사에 실패 | `UNSET`(`TOKEN_UNSET` / `TOKEN_DATE_INVALID` / `TOKEN_DATE_IS_TOKEN`) | 오류 상태 "오류(설정 없음)" | `state: UNSET` |
| 2 | 오늘(KST) ≥ 적어 둔 만료일 | `EXPIRED`(`TOKEN_EXPIRED`) | **오류 상태 "오류(토큰 만료)"**(`privatePanel` ERROR) | `state: EXPIRED` |
| 3 | GitHub 401 | 남은 날 ≤ 2이면 `EXPIRED`(`TOKEN_EXPIRED`), 아니면 `REJECTED`(`TOKEN_REJECTED`) | "오류(토큰 만료)" / "오류(토큰 거부)"(잘못 붙여 넣음·취소된 토큰) | `EXPIRED` / — |
| 4 | `GET /repos/kco994553-star/investment-system1-kis-private` 확인 요청이 404(토큰이 이 저장소를 못 봄: 4단계에서 다른 저장소를 고름 등) | `REJECTED`(`TOKEN_NO_ACCESS`) | "오류(토큰 거부)" | — |
| 5 | 403·429이고 `x-ratelimit-remaining: 0`, `retry-after` 헤더 또는 2차 한도 문구가 있음 | `RATE_LIMITED`(`UPSTREAM_RATE_LIMITED`) | "오류(자료 서버 한도)" | — |
| 5b | 그 밖의 403 | `REJECTED`(`TOKEN_REJECTED`) | "오류(토큰 거부)" | — |
| 6 | 3xx(저장소 이름이 바뀌는 등). **따라가지 않는다**(`redirect: 'manual'`) | `ERROR`(`REPO_MOVED`) | "오류(저장소 이름 바뀜)" | — |
| 7 | 네트워크 오류·시간 초과·5xx | `ERROR`(`UPSTREAM_UNAVAILABLE`) | "오류(자료 서버 응답 없음)" — 만료로 보지 않는다 | — |
| — | 위에 해당 없음 | 만료 15일 이상 남음 `OK` / 14일 이내 `EXPIRING` | 평소대로 / 자료는 그대로 보이고, 칸 위에 "비공개 읽기 토큰이 n일 뒤(YYYY-MM-DD) 만료됩니다 · 폰 설정 4~6단계로 바꿔 주세요" | `state: OK` / `state: EXPIRING`, 실행 로그에 경고 한 줄(날짜만) |

  - Worker는 `/kis/status`(인증 필요)에서 위 4번의 확인 요청을 **한 번** 보내고 `{state, code, expires_on, days_left}`만 준다(`expires_on`은 Worker가 다시 만든 날짜). 토큰 값·일부·변수 원문은 어디에도 넣지 않는다. 같은 호출에서 `status/private-area.json`의 `worker_read_token.expires_on`을 읽어 Worker 날짜와 다르면 경고(`EXPIRES_ON_MISMATCH`)를 붙인다(두 곳에 따로 적는 날짜가 어긋나는 것을 잡는다).
  - 시험(Worker PR): 위 표의 줄마다 하나씩, 그리고 가짜 `github_pat_` 값이 어떤 `/kis/*` 본문에도 나오지 않는 시험.
  - 상태 파일: 비공개 저장소의 매일 수집 실행이 `status/private-area.json`에 `worker_read_token`(만료일·남은 날·상태)과 수집 결과(개수·코드)를 쓴다. 공개 저장소·Pages에는 상태 파일을 두지 않는다.
  - 화면 문구는 공통 기반 `privateArea.panelText`의 오류 코드 문구로 둔다(Worker·화면 PR에서 `TOKEN_EXPIRED` → "오류(토큰 만료)" 등을 더한다).
- 나중 대안(기록): GitHub App 설치 토큰은 1시간짜리를 매번 만들고 앱 개인키는 만료되지 않아 교체가 없다. 대신 Worker가 앱 개인키를 갖고 서명해야 한다.

### 4.3 중점 검증 (설계 기준, 구현 시험으로 고정)

| 위험 | 막는 방법 | 시험(구현 PR) |
| --- | --- | --- |
| **인증 우회** | 경로 허용 목록 밖은 404. `/kis/*`는 인증 함수를 거치지 않고는 자료를 읽지 못하게 구조를 나눈다. `Origin` 확인은 보조일 뿐이고 인증이 관문이다. Google 장애 때 닫힘(503) | 토큰 없음·형식 틀림·다른 `aud`·다른 이메일·`email_verified` 거짓·만료·Google 4xx/5xx·느림 → 모두 403/503이고 자료 요청 0회. 쿼리에 토큰 → 거부 |
| **토큰 노출** | 토큰은 메모리·헤더에만 둔다. Worker 로그는 끔. 오류 응답은 고정 코드만. CSP는 `self`+Google만, innerHTML 없음 | 응답·오류 본문에 토큰·비밀값 일부가 없음. 앱이 토큰을 저장소·주소에 쓰지 않음 |
| **비밀값이 클라이언트로** | KIS 키는 Worker에 없다. GitHub 읽기 토큰·`ALLOWED_EMAIL`은 Worker 비밀값으로만 쓰고 응답에 넣지 않는다. 위쪽 오류 메시지는 고정 코드로 바꾼다 | 모든 응답에 env 값 부분 문자열이 없음(가짜 값으로 시험) |
| **공개 경로로 비인가 접근** | KIS 자료는 공개 저장소·Pages·공개 Actions에 없다(가드: #436 첫 구현 PR). 비공개 저장소 원본 주소는 인증 없이 열리지 않는다. 비공개 저장소의 Pages를 켜지 않는다. Worker는 임의 경로를 GitHub로 넘기지 않고, 종목 이름은 정규식과 목록으로 확인한다(경로 이동 차단) | `../`·인코딩 우회·모르는 종목 → 404이고 위쪽 요청 0회. 익명 요청 → 403과 `no-store` |
| 무차별 요청·비용 | 본인 전용 요청 한도(분당 상한, 인증된 요청만 센다). **익명 요청 폭주는 막을 수 없다(계정 전체 하루 10만, 넘으면 UTC 자정까지 `/history`·`/kis` 모두 Cloudflare 오류 1027) — 가용성 위험으로 수용(보안 검토 A7, 10/31).** 비용·자료 노출은 없다. 싼 거부(Origin·경로·쿼리·헤더 모양·길이)는 지금처럼 `tokeninfo` 앞에 둔다. 앱은 JSON이 아니거나 CORS로 실패한 응답을 인증 오류가 아니라 따로 "오류(Worker 하루 한도 또는 응답 없음)"로 보인다 | 인증된 한도 초과 → 429. 싼 거부가 `tokeninfo`보다 먼저인지(요청 0회). 앱: 비JSON·CORS 실패 → 그 상태 |

**남은 위험:**
- Google 계정이 털리면 비공개 자료도 열린다. Google 2단계 인증 또는 패스키를 켜 둘 것을 권장한다.
- `kco994553-star.github.io`는 오너의 모든 Pages가 함께 쓰는 출처다. 다른 Pages 사이트를 같은 계정에 두지 않는 것이 안전하다(XSS가 생기면 메모리 토큰을 읽을 수 있다).
- 비공개 저장소에 쓰기 권한이 있는 쪽은 워크플로나 워크플로가 읽는 파일을 바꿔 KIS Secrets를 읽을 수 있다. **GitHub Free 비공개 저장소는 DC-35("Main 작성·오너 승인")를 강제하지 못하므로, 쓰기 자격 증명 하나하나가 KIS 키 접근과 같다**(보안 검토 A3, 10/31). 줄이는 방법(3절): Claude 앱은 워크플로 설치 뒤 뺀다, Secrets를 읽는 코드는 워크플로 YAML 안이나 조상 확인을 거친 공개 SHA에만, Codex는 읽기 + 이슈만, `push` 실행 조건 금지.
- **공개 저장소에 워크플로를 push할 수 있는 쪽은 Worker를 다시 배포해 `PRIVATE_REPO_READ_TOKEN`을 읽을 수 있다**(보안 검토 A1, 10/31). `CLOUDFLARE_API_TOKEN`·`CLOUDFLARE_ACCOUNT_ID`가 공개 저장소의 저장소 Secrets라서, 아무 가지에 `on: push` 워크플로를 올리면 배포 워크플로의 `if:`(기본 가지만)를 거치지 않고 `wrangler deploy`를 할 수 있고, Worker 비밀값은 배포 뒤에도 남는다. 막는 방법: 두 Secrets를 GitHub 환경 `private-worker`(배포 가지 = 기본 가지 `claude/investment-system-top500-validation-alrugm` 하나, 필수 검토자 = 오너)로 옮기고 저장소 단위 사본을 지운다(폰 설정 7단계), 배포 잡에 `environment: private-worker`(Worker PR), Cloudflare 토큰을 이 계정의 Workers Scripts 편집·계정 설정 읽기만으로 다시 만든다. 환경 Secrets는 그 규칙을 통과한 뒤에만 잡에 넘어간다(공개 저장소는 무료로 쓸 수 있다).
- 감지(보안 검토 B2, 10/31): 공개 저장소의 모든 가지 push에 경계 정적 시험을 돌리는 워크플로(`private-boundary-push.yml`, 10/31 오너 승인 ①)가 돈다. 노출 **뒤** 알리는 것이지 막는 것은 아니다. 봇이 push한 실행의 실패는 오너에게 알림이 안 갈 수 있어 Main이 매일 점검에서 실패한 실행을 확인한다.

## 5. 무료 한도·약관·재배포

| 항목 | 한도·조건(출처 확인 10/31) | 이 설계의 사용 |
| --- | --- | --- |
| Cloudflare Workers Free | 하루 10만 요청, 호출당 CPU 10 ms, 하위 요청 50개, 메모리 128 MB | 본인 사용 하루 수백 요청. `tokeninfo` 1회 + GitHub 읽기 몇 회. CPU는 대부분 네트워크 대기라 10 ms 안 |
| Durable Objects(무료, SQLite) | 기존 Worker가 이미 사용 | 요청 한도 1개 더 |
| R2 / KV | R2는 결제 수단 필요, KV 무료 쓰기 하루 1,000회 | 쓰지 않음 |
| GitHub Actions(비공개 저장소, Free) | 월 $12 포함(리눅스 약 2,000분), 결과물 저장 500 MB. 결제 수단이 없으면 넘을 때 **청구 대신 실행이 막힌다** | 매일 10~15분 × 22일 ≈ 330분, 처음 채우기 약 270분(1회). 결과물 저장 안 씀 |
| GitHub API(읽기 토큰) | 시간당 5,000회 | Worker 읽기 |
| KIS | 계정당 초당 18건(새 키는 3일간 초당 3건), 토큰 발급마다 카카오톡 알림, 토큰 24시간 | 실행마다 토큰 1회 발급·끝에 폐기, 초당 10건 이하 |
| KIS 약관 제5조 ② | 「보안코드(앱키, 시크릿키)가 유출 및 도용되지 않도록 관리해야 하고, 제3자에게 대여, 위임, 양도 또는 본인 이외의 제3자에게 누설해서는 아니 된다」 | 키는 비공개 저장소 Secrets에만. 출력·저장·전달 없음 |
| KIS 약관 제5조 ③ | 「시세 … 정보를 고객이 직접 개발한 프로그램 등 개인의 업무에 한하여 이용해야 하며, 제3자에게 제공해서는 아니 된다」 | 로그인한 오너 화면에만. 공개 파일·Pages·공개 로그·복사용 프롬프트에 넣지 않음. Lab 공개 투영(`lab-results/1`)에 KIS 파생 수치 없음. **Codex 흐름(보안 검토 A9, 10/31):** 연구 요청(설계 20절)의 결과를 Codex(제3자가 운영하는 AI 작업 공간)가 읽는 것이 "제3자 제공"인지는 약관에 답이 없어 KIS 서면 문의 ⑥(설계 12절)에 넣었다. **회신 전까지 원 KIS 계열(가격·거래량 행)은 비공개 저장소 Actions 안에만 두고, Codex에는 가격이 아닌 파생 통계(개수·범위·일치율·백테스트 요약 수치 등)만 준다.** KIS 파생 lab 파일은 `kis-` 스키마를 달아 가드가 잡게 한다 |

## 6. 기존 확정 설계·기능계층과의 충돌

| 위치 | 지금 내용 | 처리 |
| --- | --- | --- |
| #436 설계 5절·11절 4~6단계·17.5절 | Cloudflare Access 일회용 코드, `kis-auth` Worker, 7일 세션 | **대체됨(10/31 승인)**. 해당 절에 "대체됨"을 적었다. 다른 절에 남아 있던 Access·`kis-auth`·JWT·`PRIV-PAYMENT` 줄(0·2·4·5.5·7·10·11·13·14·17·17.2·17.3·18.4·18.6절)에도 "대체됨(10/31) → NO_ZT §4"를 적었다(보안 검토 A10) |
| PRIV 결정 | `PRIV-PAYMENT`(Zero Trust 결제 수단 등록 허용) 승인됨 | **불필요**로 기록(10/31). `PRIV-AUTH-GOOGLE` 승인 |
| 폰 설정 절차 | 옛 저장소 이름(하이픈 없는 짧은 이름)·4~6단계 Zero Trust | 새 이름 `investment-system1-kis-private`로 고침. 4~6단계를 Worker 읽기 토큰·만료일 단계로 바꿈 |
| FUNCTION_STATUS 1-3절(#440) | 비공개 층 = #436 설계, "로그인 필요" 두 종류(시트 / 비공개 Access) | 둘 다 Google 로그인이 된다. 문구 구분("시트 연결 필요" / "비공개 로그인 필요")은 그대로 쓸 수 있다. 토큰은 범위가 달라 따로 받는다 |
| Notion 관리자 페이지 | "Cloudflare Access 이메일 일회용 코드 + Worker가 Access JWT 직접 검증" | 고침(10/31, Google 토큰 + Worker 확인) |
| Notion 9. Lab 공통 규칙 | "개인화: 로그인 시 계정 설정, 비로그인 시 기기 설정" | DC-22·2층 표(개인 자료는 기기에만)와 어긋나서 고침(10/31) |
| 기능계층 v1.0 | 화면·기능 번호 | 충돌 없음(비공개 칸은 기능을 더하지 않는다) |
| 가드(#436 첫 구현 PR) | KIS 표지·`/kis/` 경로 공개 금지 | 그대로 맞는다 |

## 7. 승인 뒤 순서 (지금은 하지 않음)

1. 가드 PR(진행 중, KIS 표지·공개 경계·연구 요청 형식).
2. 수집기 PR(공개 저장소, 가상 자료 시험) → 비공개 저장소에 워크플로 1개(오너 승인, 세션에 그 저장소 쓰기 권한 필요) → 수동 1회 실행(개수·코드만).
3. Worker PR(순서대로):
   1. **기존 Worker 버그 먼저(보안 검토 A4, 10/31):** `implementation/worker/src/index.js`의 모든 외부 fetch가 `redirect: 'error'`(`NO_CACHE`, index.js:65)를 쓰는데, Cloudflare Workers는 이 값을 받지 않아 Request를 만들 때 TypeError를 낸다. 그래서 운영에서는 로그인한 `/history` 요청이 Google 확인 전에 닫혀 503(`AUTH_UNAVAILABLE`)이 된다(검증자가 실제 workerd로 재현). 고칠 것: `redirect: 'manual'`로 바꾸고 300~399 응답은 고정 실패 코드로 처리한다(따라가지 않는다). Node 시험의 `init.redirect === 'error'` 단언 두 곳(`worker/tests/worker.test.mjs:240`, `worker/tests/fallback.test.mjs:26`)을 `'manual'`과 3xx 실패 시험으로 바꾼다. 배포 확인 단계(`deploy_private_history_worker.py verify`)에 **가짜 Bearer 한 번을 보내 503이 아니라 403 `AUTH_FORBIDDEN`인지** 확인하는 요청을 더한다(Secret 없이, tokeninfo 1회). 이 PR에서는 Worker 코드를 바꾸지 않았다.
   2. 배포 잡에 `environment: private-worker`(보안 검토 A1). 다른 워크플로가 `CLOUDFLARE_` Secret을 쓰거나 배포 잡에 이 환경이 없으면 실패하는 정적 시험. 오너가 먼저 폰 설정 7단계를 한다.
   3. `/kis/*` 경로, 인증 공용화, 비공개 저장소 읽기, 4.4절 상태 순서·만료일 검사(줄마다 시험), 시험 → 오너가 Worker 비밀값(읽기 토큰) 등록 → 수동 배포 워크플로(오너 승인).
4. 화면 PR: "비공개 연결" 버튼(`include_granted_scopes: false`, 범위 정확히 {openid, email} 확인, 4.2절), privatePanel 상태 연결(4.4절 코드 문구, 비JSON·CORS 실패 상태), 시험.
5. ~~이관(설계 20절) 뒤 공개 저장소 KIS Secrets 삭제.~~ Secrets 삭제는 끝남(10/31 오너). 남은 것: 이관 뒤 Codex 연구 가지의 KIS 워크플로·KIS 파생 요약 파일 정리(설계 20절).

## 8. 결정 (10/31 오너 승인)

| ID | 결정 |
| --- | --- |
| PRIV-AUTH-GOOGLE | A(Google 토큰 + Worker 확인)로 시작. 패스키는 나중 |
| PRIV-REPO-NAME | `investment-system1-kis-private`로 변경(오너가 함). 문서·워크플로·Worker 설정은 새 이름만 쓴다 |
| PRIV-CODEX-WF-OFF | Codex KIS 워크플로 2개를 오너가 끈다(삭제 아님) |
| PRIV-PAYMENT | 불필요(Zero Trust를 쓰지 않음) |
| 공개 저장소 KIS Secrets | 쓰는 곳은 Codex 연구 가지 워크플로 2개뿐 → 오너가 지움(10/31). KIS 키는 비공개 저장소에만. 두 워크플로는 이제 돌면 KIS 단계에서 실패하며, 고치지 않고 비공개 저장소 이관 작업에 포함한다 |
