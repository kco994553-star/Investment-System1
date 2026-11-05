# 보안 검사 도구 시험 (2026-11-05, Main)

기준: canonical `ab6a83c3`, 가지 `claude/security-scan-trial-1105`. 모든 실행은 이 작업 트리를 **로컬에서만** 읽었다. 도구·보고서는
작업 트리 밖 임시 폴더(아래 `$P` = 세션 scratchpad)에만 두었고 저장소에 넣지 않았다. 워크플로는 추가·변경·실행하지 않았다.

상태 표기: 이 문서의 모든 결과는 **TESTED**(로컬·개발 빌드·합성 입력)다. CI 연결(INTEGRATED)·배포·실서비스 확인은 하지 않았다.

## 1. 기존 검사 목록 (무엇을 이미 막고 있나)

| 검사 | 어디서 | 보는 것 | 비밀값 관련 범위 |
| --- | --- | --- | --- |
| `implementation/tools/autonomy_gate_a_guard.py` (`autonomy-gate-a.yml`) | PR diff·HEAD·index·추적 파일 | 기기 보유·시세 내보내기 모양, 이메일, Google OAuth 토큰(`ya29.`)·시트 URL·시트 ID | 구조화 자료(JSON/YAML/CSV, md 안 코드 블록)의 **채워진** 자격 키(`apikey`·`accesstoken`·`clientsecret`…)와 Google 패턴만. `.py`·`.js` 소스 속 일반 토큰 문자열은 보지 않는다 |
| `implementation/tools/pages_artifact_guard.py` (Pages 게시 직전) | **Pages 산출물만** | 허용 파일 목록·크기·스키마·가격 키, KIS 표지, 비공개 경로 | `SECRET_PATTERNS` 6개: 이메일, `ya29.`, 시트 URL, PEM 개인키 머리, `api_key/token/secret/password = "…"` 꼴, `Authorization: Bearer …` |
| `implementation/tests/test_private_boundary_static.py` (`private-boundary-push.yml`) | 저장소 전체 파일 | KIS 스키마·호스트·TR ID·KIS Secret 이름, 공개 워크플로의 KIS 접근, 웹의 비공개 Worker 경로 | KIS Secret **이름**만(값 형식 아님) |
| `implementation/src/investment_system/public_price_boundary.py` | 런타임(공개 번들·출처 URL) | 원시 가격·재무 출처 경계 | 비밀값 검사 아님 |
| `implementation/tools/web_app_reuse_node_test.js` `RULES` | `web_app/*.js` 소스 | HTML 문자열 싱크(`innerHTML` 등)·`eval`·`new Function`·`fetch(` 위치·저장소 위치·스크립트 요소 등 정규식 규칙 | 해당 없음 |
| GitHub 비밀 스캔 | 저장소 설정 | — | 워크플로에서는 보이지 않는다. 이 세션은 GitHub API가 막혀 있어 설정(비밀 스캔·push protection) 상태를 확인하지 못했다 |

의존성 쪽: 저장소의 잠금 파일은 `implementation/experiments/chart-contract-v0.1/package-lock.json` 하나다. Worker(`implementation/worker/package.json`)는
의존성이 없다. Python에는 requirements·잠금 파일이 없고, CI는 워크플로 안에서 `pip install pytest==9.1.1 jsonschema==4.26.0`(최상위만 고정,
하위 의존성은 실행마다 새로 해석)을 하며, `deploy_private_history_worker.py`는 `npx --yes wrangler@4.149.0`, 폰트 도구는
`fonttools==4.67.0 brotli==1.2.0`을 쓴다. 의존성 취약점 검사(Dependabot·`npm audit`·`pip-audit`·Trivy)는 워크플로에 없다.

## 2. 실제 공백 (gap)

1. **공급자별 토큰 형식이 소스·이력에서 검사되지 않는다.** 아래 합성 문자열(무작위 생성, 저장소에 넣지 않음)을 기존 가드의 텍스트 검사 함수에
   직접 넣었다(`$P/secscan-scripts/gapdemo.py`).

   | 합성 입력 | `autonomy_gate_a_guard.contains_device_actual` | `pages_artifact_guard.SECRET_PATTERNS` | Betterleaks |
   | --- | --- | --- | --- |
   | GitHub PAT(`ghp_` + 36자, `.py` 상수) | miss | miss | `github-pat` |
   | GitHub fine-grained PAT(따옴표 상수) | miss | miss | `github-fine-grained-pat` |
   | Slack bot token | miss | miss | `slack-bot-token` |
   | Anthropic API key 모양 | miss | miss | `anthropic-api-key` |
   | PEM 개인키 머리(`.py`) | miss | HIT | (검사 안 함) |
   | `api_key = '…'`(`.js`) | miss | HIT | (검사 안 함) |

   즉 Pages 산출물 밖(소스·문서·시험·Actions가 만든 커밋)과 **git 이력**에는 공급자 토큰 형식 검사가 없다. Pages 가드의 일반 패턴은 Pages
   산출물 안에서만 돈다. (AWS 키 모양 합성 입력은 Betterleaks도 잡지 않았다. 기본 규칙의 추가 조건 때문으로 보이며, 이 시험에서는 더 보지 않았다.)
2. **의존성 취약점 검사가 없다.** 아래 4절처럼 실제 공지가 있는 고정 버전이 있다.
3. 워크플로 두 개(`raw-artifact-restore-check.yml`, `qgv-common-contract-vnext.yml`)는 `actions/checkout@v4`·`actions/setup-python@v5`처럼
   **태그**로 액션을 참조한다(나머지는 커밋 SHA 고정). 워크플로 변경이라 이 PR에서는 고치지 않았다(오너 승인 필요).
4. `web_assets/`의 옛 모듈(새 앱 `loader.js` LOAD_ORDER가 61개를 읽는다)에는 `innerHTML` 문자열 싱크가 23개 파일에 있다.
   `web_app` 전용 `RULES`는 이 폴더를 보지 않는다. 표본 확인(`news-signals.js`·`price-store.js`·`playbook-screen.js`)에서는 `esc()`/`escHtml()`로
   감싸고 있었고, 확인된 결함은 없다. 전수 검토는 하지 않았다(남은 일).

## 3. 비밀값 검사기: Betterleaks (Gitleaks 대신)

- **도구**: Betterleaks **v1.9.0**(2026-09-29 태그, 커밋 `81aff7a638638aae3a659845d089043e1d8fe9ac`). Gitleaks 원작자의 후속 도구.
  v1.10.0(2026-11-04)은 하루밖에 안 돼 쓰지 않았다. **라이선스 MIT**(모듈 zip의 `LICENSE`, "Copyright (c) 2026 Zachary Rice").
  기본 규칙 463개(`config/betterleaks.toml`, 바이너리에 내장).
- **설치**: GitHub 릴리스 페이지는 이 환경에서 막혀 있어(403) Go 모듈 프록시로 소스를 받아 빌드했다.
  `go install`은 `sum.golang.org` 체크섬 DB로 모듈 해시를 검증한다(`h1:mYAZBNUGBww1ihIwcb68Z2QmLh5hZwKbLG0jsf4PfpE=`).
  Go에는 설치 훅(postinstall)이 없다. 빌드 도구체인 go1.26.10(모듈의 `toolchain` 지시로 자동 다운로드, 같은 체크섬 검증).
  바이너리 sha256 `b145909a5f619d19d948d94066b5a267e647cc0873a180d2d1b7fb98cd58dc3c`(로컬 빌드값, 재현 빌드 기준값은 아님).
- **네트워크**: 탐지 모드에서는 없음. 키 검증(`--validation`)은 기본 꺼짐이고 켜지 않았다. `validate` 하위 명령·GitHub/GitLab/S3 소스는
  쓰지 않았다. 원격 측정 코드 없음(소스 확인: `net/http`는 validation·원격 소스·진단 패키지에만 있다). 토크나이저 자료는 바이너리에 내장.
- **명령**(보고서는 `$P/secscan-reports/`, 값은 `--redact=100`으로 `REDACTED` 처리):

```
B=$P/tools-betterleaks/bin/betterleaks
$B dir  <worktree> --redact=100 --no-banner --no-color -f json -r $P/secscan-reports/bl-dir.json --exit-code 0 -l warn
$B git  <worktree> --log-opts="-n 500" --redact=100 --no-banner -f json -r $P/secscan-reports/bl-git500.json --exit-code 0
$B git  <worktree> --redact=100 --no-banner -f json -r $P/secscan-reports/bl-gitall.json --exit-code 0
```

- **결과**

  | 대상 | 시간 | 발견 | 규칙별 |
  | --- | --- | --- | --- |
  | 작업 트리(`dir`) | 3.3초 | 37 | generic-api-key 34 · generic-password 1 · gcp-api-key 1 · generic-credential-uri 1 |
  | 최근 500 커밋 | 0.9초(6.7 MB) | 0 | — |
  | 전체 이력 2,083 커밋 | 7.1초(230 MB) | 108 | generic-api-key 102 · generic-password 3 · generic-credential-uri 2 · gcp-api-key 1 |

- **분류**(값은 출력하지 않고, 값의 길이·문자 종류·키 이름만 보는 스크립트 `$P/secscan-scripts/shape.py`·`shape_git.py`로 판정):

  | 묶음 | 건수(트리/이력) | 판정 |
  | --- | --- | --- |
  | 자동화 기록의 `*_lease_token` 등(`qgv-…` 꼴 사람이 읽는 임대 ID) | 16 / 36 | 거짓 양성: 자격증명 아님 |
  | 40자·64자 16진수(`api_commit`·`auth_audit_head`·`*_sha256`·`*.py` 해시 등) | 10 / 52 | 거짓 양성: git SHA·SHA-256 |
  | Figma `file_key` | 3 / 5 | 거짓 양성: 파일 식별자(접근에는 별도 인증 필요) |
  | 수집 원본 HTML 속 제3자 브라우저 비컨 키(Akamai mPulse·New Relic 브라우저 에이전트, `experiments/.../market-identity-time/*.html`, 같은 파일의 `.gz`, 축약 JS의 `password:!1` 1건 포함) | 5 / 4 | 제3자 웹페이지에 공개로 박힌 값·축약 코드. 이 저장소의 비밀 아님 |
  | `daily_report_node_test.js:96` | 1 / 1 | 거짓 양성: `sha256('abc')` 시험 벡터 |
  | `private_history_browser_test.js:290`, `tests/test_integration_fpia_fix2.py`, `tests/product_platform/test_api.py`·`test_web.py`, `display_widgets_node_test.js`(`pk_ABCDEFGH…`) | 1 / 7 | 거짓 양성: 합성 시험 값 |
  | `tests/test_sec_once_collect.py`(이력) | 0 / 2 | 거짓 양성: 저장소 객체 경로 |
  | `web_assets/app-config.js:4` (`gcp-api-key`) | 1 / 1 | **형식상 참 양성, 의도된 공개값**: Google Picker 브라우저 키. 파일 머리말과 `HANDOFF_HISTORY_THROUGH_20261013.md`에 "API/리퍼러 제한 키, 공개 설정"으로 기록돼 있다. 제한 설정은 네트워크 확인 금지라 재확인하지 않았다 |

  합계 37 / 108. **유출된 비공개 비밀값: 0건.** 멈춤 조건(실제 비밀 발견)은 일어나지 않았다.

## 4. Semgrep · Trivy (기존 검사가 없는 곳만)

### 4.1 Semgrep

- **도구**: Semgrep CE **1.181.0**(PyPI 2026-10-14, 22일 경과), **LGPL-2.1-or-later**. 휠만 설치(`--only-binary :all:`, setup 스크립트 실행 없음)
  `$P/tools-semgrep/venv`. `semgrep-core` 바이너리가 휠에 들어 있다.
- **네트워크**: 로컬 규칙 파일만(`--config <파일>`), `--metrics=off`, `--disable-version-check`, `SEMGREP_ENABLE_VERSION_CHECK=0`,
  로그인 없음(Pro 규칙·레지스트리 `p/…` 안 씀). OpenTelemetry 추적은 `--trace`를 줄 때만 켜진다(주지 않음).
- **규칙**: 직접 쓴 16개(부록 A). `web_app` RULES가 이미 막는 HTML 문자열·eval은 제외하고, 그 정규식이 못 보는 곳을 겨눴다:
  `h()`의 URL 속성(href/src/action)에 비리터럴 값, `setAttribute`로 URL·이벤트 속성, URL 속성 대입, 비리터럴 이동(location·window.open),
  `target=_blank`에 rel 없음, 문자열 타이머, 비리터럴 RegExp, postMessage, `__proto__` 쓰기, 쿠키·credentials, `Math.random`,
  Worker의 CORS `*`/반사, 문자열 SQL, 응답 본문의 예외 메시지, 요청 헤더·Secret 로그, 토큰 이름의 `===` 비교.
  양성 대조 파일(`$P/secscan-semgrep-controls/controls.js`)에서 16개 규칙이 모두 걸리는 것을 먼저 확인했다(오류 0).
- **명령**

```
export SEMGREP_ENABLE_VERSION_CHECK=0 HOME=$P/tools-semgrep/home
$P/tools-semgrep/venv/bin/semgrep scan --config $P/secscan-scripts/semgrep-local.yml --metrics=off --disable-version-check \
  --json -q implementation/src/investment_system/product/web_app implementation/worker/src -o $P/secscan-reports/semgrep-main.json
```

- **결과**: 37개 파일, 11.5초, 발견 20, 오류 0. **참 양성 0.**

  | 규칙 | 건수 | 판정 |
  | --- | --- | --- |
  | is2-url-attr-from-value | 11 | 모두 안전: 내부 경로(`IS2.href`/`href()` 결과를 변수로 넘김: `parts.js`·`screen-tree-live.js`·`screen-prompts-live.js`), 코드 상수(IEX 약관 URL `qgv-official.js` ATTRIBUTION, `home-quotes.js` 출처 URL), 옛 판독기가 `^(https?)://` 형식을 검증한 뉴스·공시 링크(`news-signals.js` `linkHost`). 게다가 CSP `script-src`에 `'unsafe-inline'`이 없어 `javascript:` URL은 실행되지 않는다 |
  | dom-url-property-assignment | 4 | 거짓 양성: `IS2.action=` 모듈 내보내기, 상태 객체 `ctx.src`, `loader.js`의 LOAD_ORDER 고정 목록 스크립트 |
  | navigation-from-value | 3 | 거짓 양성: `indexedDB.open(name, version)` |
  | insecure-random | 2 | 위험 없음: 기기 안 노트 ID의 `crypto.getRandomValues` 대체 경로(`store.js:161`), TARGET v1 초안 행 ID(`engines.js:91`). 둘 다 비밀·추측 방지 용도 아님 |

  Worker(`implementation/worker/src/index.js`)는 0건: CORS는 고정 `ORIGIN`과 같을 때만 허용, 오류 응답은 고정 코드만, SQL·로그 없음.
- 보조로 옛 `web_assets/`(93개 파일, 번들 `lightweight-charts` 제외)도 돌렸다: 36건(WARNING 20 · INFO 16, ERROR 0). 이 시험에서는 분류하지 않았다(2절 4번과 함께 남은 일).

### 4.2 Trivy

- **도구**: Trivy **0.76.1**(태그 2026-10-21), **Apache-2.0**. GitHub 릴리스가 막혀 있고 원본 빌드는 디스크가 모자라(공유 디스크 100% 도달, 즉시 정리함)
  공식 이미지에서 바이너리만 꺼냈다: `ghcr.io/aquasecurity/trivy:0.76.1` 색인 digest `sha256:790fd66d…eca6c06c` → linux/amd64 매니페스트
  `sha256:2e6c00d7…3df` → 레이어 `sha256:2e51b4bf…808`(`usr/local/bin/trivy` 하나). 세 digest를 모두 sha256으로 대조했다.
  바이너리 `go version -m`: go1.27.3, 모듈 `v0.76.1+dirty`(공식 빌드 표기, cosign 서명 검증은 도구가 없어 못 함).
- **네트워크**: 취약점 DB는 **다운로드가 필요했고 성공했다**: `mirror.gcr.io/aquasec/trivy-db:2`, 11초, 압축 해제 1.6 GB, DB `UpdatedAt 2026-11-05T01:19Z`.
  검사 자체는 `--skip-db-update --offline-scan --disable-telemetry --skip-version-check`로 외부 요청 없이 돌렸다. 검사 후 DB는 지웠다.
- **명령**

```
T=$P/tools-trivy/bin/trivy; C="--cache-dir $P/tools-trivy/cache --disable-telemetry --skip-version-check --no-progress"
$T fs --download-db-only $C
$T fs <worktree> --scanners vuln --include-dev-deps --list-all-pkgs --skip-db-update --offline-scan $C -f json -o $P/secscan-reports/trivy-wt-pkgs.json
# CI·도구 고정값을 잠금 파일로 풀어(설치 없이) 같은 방식으로 검사
pip install --dry-run --ignore-installed --only-binary :all: --report r.json pytest==9.1.1 jsonschema==4.26.0 fonttools==4.67.0 brotli==1.2.0
npm i --package-lock-only --ignore-scripts --no-audit --no-fund wrangler@4.149.0 playwright@1.58.2
$T fs $P/secscan-manifests --scanners vuln --include-dev-deps --skip-db-update --offline-scan $C -f json -o $P/secscan-reports/trivy-cipins.json
```

- **결과**

  | 대상 | 패키지 | 취약점 |
  | --- | --- | --- |
  | 작업 트리(잠금 파일 1개: chart-contract 실험, lightweight-charts 5.2.1·playwright 1.58.2 등) | 6 | 0 |
  | Python CI·도구 고정값(하위 의존성 포함) | 12 | **1**: `brotli 1.2.0` CVE-2026-111497 CRITICAL(디코더 범위 밖 쓰기, 수정 1.2.1) |
  | npm 도구 고정값(`wrangler@4.149.0`·`playwright@1.58.2`) | 94 | **8**: `undici 7.29.1`(wrangler 4.149.0 → miniflare 5.20261006.1-alpha가 정확히 고정) HIGH 4·MEDIUM 4, 수정 7.30.1 |

  - `undici`: 영향 경로는 Worker 배포 도구(`deploy_private_history_worker.py` → `private-history-deploy.yml`, Cloudflare 토큰이 있는 작업)다.
    Worker 런타임 코드에는 들어가지 않는다. 수정된 undici를 쓰는 첫 wrangler는 **4.153.0**(2026-10-26, miniflare 5.20261023.0-beta → undici 7.30.1).
    고정값은 `deploy_private_history_worker.py`·`implementation/worker/deployment-prerequisites.json`(배포 기록)·`tests/test_worker_deployment_diagnostics.py`
    세 곳에 묶여 있고 배포 절차에 영향을 주므로 이 PR에서 바꾸지 않았다. **남김**(배포 승인과 함께 올릴 것).
  - `brotli`: `font_subset_ksx1001.py`의 수동 재현 절차에만 쓰인다. 입력은 해시 고정된 Google Fonts 원본이고 도구는 압축(인코더)만 한다.
    버전을 바꾸면 출력 바이트가 Pages 가드에 고정된 SHA-256과 달라질 수 있어 바꾸지 않았다. **남김**(폰트를 다시 만들 때 1.2.1로 재현·재고정).
  - 옛 화면 번들 `web_assets/lightweight-charts-5.2.1.standalone.js`는 잠금 파일이 아니라 Trivy가 보지 못한다(같은 버전이 실험 잠금 파일에 있어 간접 확인: 0건).

## 5. ZAP 기준선(수동·passive) 검사

- **가능 여부**: Docker 데몬 없음(클라이언트만, `/var/run/docker.sock` 없음), Java 21 있음, ZAP 설치 없음. GitHub 릴리스 zip은 막혀 있다.
  공식 이미지 `zaproxy/zap-stable:2.17.0`(Docker Hub, 색인 digest `sha256:9624669d…f328af`, amd64 `sha256:c2d63bbb…2882`)에서 `/zap` 레이어
  (`sha256:6173fb42…acab`, 481 MB)와 스크립트 레이어(`sha256:41737c9a…a554`)만 받아 digest 대조 후 풀었다. ZAP **2.17.0**, **Apache-2.0**.
  `zap-baseline.py`는 Docker 밖에서는 스스로 Docker를 띄우려 하므로, `--plan-only`로 **같은 기준선 계획(Automation Framework)**을 만들고
  `zap.sh -cmd -silent -autorun`으로 실행했다. 파이썬 클라이언트 `zaproxy==0.6.0`(Apache-2.0)·`pyyaml==6.0.3`은 휠로 scratch venv에 설치.
- **격리**: 개발 사이트(`web_app_test_site.js`가 `build_web_app.py`로 만든 개발 빌드, 고정 자료 없음)와 ZAP을 **`unshare -n` 네트워크 이름공간**
  안에서 함께 돌렸다. 이 안에는 loopback만 있다(외부 연결 시험: `Network is unreachable`). `-silent`로 업데이트 확인·뉴스·callhome도 끈다.
  즉 대상은 `127.0.0.1` 하나이고 외부 대상은 물리적으로 닿을 수 없다. 능동 공격 검사(active scan)·AJAX 스파이더는 돌리지 않았다.
- **명령**

```
cd $P/tools-zap/wrk && $P/tools-zap/venv/bin/python $P/tools-zap/root/zap/zap-baseline.py -t http://127.0.0.1:8765/ --plan-only \
  -J zap-baseline.json -r zap-baseline.html -m 1          # zap.yaml: passiveScan-config → spider(1분) → passiveScan-wait → 보고서
unshare -n $P/secscan-scripts/zap_run.sh $P <worktree>   # lo 올림 → 개발 사이트 시작 → URL 바꿔 넣은 plan.yaml로
                                                          # ./zap.sh -cmd -silent -dir $P/tools-zap/home -config database.recoverylog=false -autorun plan.yaml
```

- **결과**(31초, URL 21개): FAIL 0 · WARN 5 · PASS 57.

  | 경고 | 판정 |
  | --- | --- |
  | 10055 CSP: `frame-ancestors` 미정의 / 10020 클릭재킹 헤더 없음 | 참이지만 호스팅 한계: CSP는 `<meta>`로 주는데 `frame-ancestors`는 meta에서 무시된다. GitHub Pages는 응답 헤더(`X-Frame-Options`·CSP 헤더)를 정할 수 없다. 고치려면 호스팅 변경 또는 화면 안 프레임 차단 코드가 필요하다 → 오너 결정. **남김** |
  | 10021 `X-Content-Type-Options` 없음(5) | 로컬 시험 서버의 헤더다. 실제 Pages 응답 헤더는 네트워크 확인을 하지 않아 미확인. **남김** |
  | 10027 의심 주석(8) | 거짓 양성: 코드 주석의 `FROM` 등 영어 단어 |
  | 10109 최신 웹앱 | 정보 |

## 6. 고친 것

없음. 확인된 결함 중 "작고 분명한 Main 담당 수정"에 해당하는 것이 없었다: Semgrep 참 양성 0, 유출 0, Trivy 두 건은 배포 기록·Pages 고정 바이트에
묶여 있고, ZAP 두 건은 호스팅 결정이다. 기존 시험·가드·CSP는 바꾸지 않았다.

## 7. CI에 넣으려면 (모두 워크플로 변경 → 오너 승인)

1. **Betterleaks**(권장): PR마다 `betterleaks git --log-opts="<base>..HEAD" --redact --no-banner --exit-code 1`, 주기적으로 `dir` 전체.
   설치는 `go install github.com/betterleaks/betterleaks@v1.9.0`(sumdb 검증) 또는 체크섬 확인한 릴리스 바이너리. `--validation`은 절대 켜지 않는다.
   현재 37건 거짓 양성은 `.betterleaksignore`(지문 목록) 또는 경로 허용 규칙으로 기준선을 만든다. 보고서는 `--redact`로만 만들고 아티팩트로
   올리지 않는다(Pages 가드처럼 건수만 로그). 필수 CI 6개에 넣을지는 오너 결정.
2. **Trivy**(선택, 주기 실행): DB를 실행 때마다 `mirror.gcr.io`에서 받아야 한다(네트워크 필요). 그 전에 CI 고정값을 잠금 파일로 옮겨야
   검사·Dependabot이 볼 수 있다(예: 해시 고정 `requirements-ci.txt`, 도구용 `package-lock.json`). 지금은 하위 Python 의존성이 실행마다 바뀐다.
3. **Semgrep**: 새 CI 작업보다, 쓸모 있는 두 규칙(URL 속성·이동 대상이 비리터럴)을 기존 `web_app_reuse_node_test.js` `RULES`에 정규식으로
   옮기는 쪽이 싸다. 도구 자체는 큰 감사 때 로컬에서만.
4. **ZAP**: GitHub 러너에는 Docker가 있어 `zap-baseline.py`를 이미지 digest 고정으로 돌릴 수 있다. 그러나 정적 Pages에서 나오는 경고는 호스팅
   헤더뿐이라 CI 가치가 낮다. 넣지 않는 것을 권한다.
5. 태그로 참조된 액션 2곳을 SHA 고정으로 바꾸는 것(2절 3번).

## 8. 권고

- **유지: Betterleaks** — 실제 공백(소스·이력의 공급자 토큰 형식)을 메운다. 빠르고(트리 3초, 전체 이력 7초), MIT, 탐지 모드는 네트워크 없음.
  위치: PR 사전 검사(오너 승인 뒤) + Main 로컬 커밋 전 점검.
- **가끔: Trivy** — 의존성 면이 작아 주기 실행이면 충분. 이번에 실제 공지 2건(undici·brotli)을 찾았다.
- **보류: Semgrep·ZAP** — 이번 범위에서 참 양성 0. 기존 정규식 규칙과 CSP가 이미 넓게 막고 있다.
- 남은 일: wrangler ≥ 4.153.0 상향(배포 승인과 함께), brotli 1.2.1 재현(폰트 재생성 때), 옛 `web_assets` HTML 문자열 싱크 전수 검토,
  `frame-ancestors`(호스팅) 결정, GitHub 비밀 스캔·push protection 설정 확인(오너 화면에서).

## 부록 A. Semgrep 로컬 규칙 (`$P/secscan-scripts/semgrep-local.yml`)

<details><summary>16개 규칙 원문</summary>

```
rules:
  - id: is2-url-attr-from-value
    languages: [javascript]
    severity: WARNING
    message: URL-bearing attribute set from a non-literal value through h().
    patterns:
      - pattern-either:
          - pattern: '$H($TAG, {..., href: $V, ...}, ...)'
          - pattern: '$H($TAG, {..., src: $V, ...}, ...)'
          - pattern: '$H($TAG, {..., action: $V, ...}, ...)'
          - pattern: '$H($TAG, {..., formaction: $V, ...}, ...)'
          - pattern: '$H($TAG, {..., ''xlink:href'': $V, ...}, ...)'
      - metavariable-regex: {metavariable: $H, regex: '^(h|IS2\.h|\w+\.h)$'}
      - metavariable-pattern:
          metavariable: $V
          patterns:
            - pattern-not: '"..."'
            - pattern-not: $X.href(...)
            - pattern-not: href(...)
            - pattern-not: '`...`'
  - id: dom-set-url-or-handler-attribute
    languages: [javascript]
    severity: WARNING
    message: setAttribute on a URL or event-handler attribute with a non-literal value.
    patterns:
      - pattern: $E.setAttribute($K, $V)
      - metavariable-regex: {metavariable: $K, regex: '^[''"`](on\w+|href|src|action|formaction|xlink:href|srcdoc)[''"`]$'}
      - pattern-not: $E.setAttribute($K, "...")
  - id: dom-url-property-assignment
    languages: [javascript]
    severity: WARNING
    message: URL property assigned from a non-literal value.
    patterns:
      - pattern-either:
          - pattern: $E.href = $V
          - pattern: $E.src = $V
          - pattern: $E.action = $V
      - pattern-not: $E.href = "..."
      - pattern-not: $E.src = "..."
  - id: navigation-from-value
    languages: [javascript]
    severity: WARNING
    message: Navigation (location / window.open) to a non-literal URL.
    patterns:
      - pattern-either:
          - pattern: location.href = $V
          - pattern: $W.location.href = $V
          - pattern: location.assign($V)
          - pattern: $W.location.assign($V)
          - pattern: location.replace($V)
          - pattern: $W.location.replace($V)
          - pattern: window.open($V, ...)
          - pattern: $W.open($V, ...)
          - pattern: location = $V
      - metavariable-pattern:
          metavariable: $V
          patterns:
            - pattern-not: '"..."'
  - id: blank-target-without-rel
    languages: [javascript]
    severity: INFO
    message: target=_blank without rel=noopener.
    patterns:
      - pattern: '$H($TAG, {..., target: ''_blank'', ...}, ...)'
      - pattern-not: '$H($TAG, {..., rel: $R, ...}, ...)'
  - id: string-timer-or-function
    languages: [javascript]
    severity: ERROR
    message: setTimeout/setInterval with a string, or code from a string.
    pattern-either:
      - pattern: setTimeout("...", ...)
      - pattern: setInterval("...", ...)
      - pattern: $W.setTimeout("...", ...)
      - pattern: Function(...)
      - pattern: new Function(...)
      - pattern: eval(...)
      - pattern: $W.eval(...)
  - id: regexp-from-value
    languages: [javascript]
    severity: INFO
    message: RegExp built from a non-literal value.
    patterns:
      - pattern-either:
          - pattern: new RegExp($V, ...)
          - pattern: RegExp($V, ...)
      - pattern-not: new RegExp("...", ...)
      - pattern-not: RegExp("...", ...)
  - id: postmessage-handling
    languages: [javascript]
    severity: WARNING
    message: postMessage to '*' or a message listener.
    pattern-either:
      - pattern: $W.postMessage($M, "*")
      - pattern: $W.addEventListener("message", ...)
      - pattern: addEventListener("message", ...)
  - id: prototype-key-write
    languages: [javascript]
    severity: WARNING
    message: Write through a prototype key.
    pattern-either:
      - pattern: $O["__proto__"] = $V
      - pattern: $O.__proto__ = $V
      - pattern: Object.setPrototypeOf($O, $P)
  - id: cookie-or-credentials
    languages: [javascript]
    severity: INFO
    message: document.cookie or credentials include.
    pattern-either:
      - pattern: document.cookie
      - pattern: '{..., credentials: "include", ...}'
  - id: insecure-random
    languages: [javascript]
    severity: INFO
    message: Math.random().
    pattern: Math.random()
  - id: worker-cors-wildcard-or-reflect
    languages: [javascript]
    severity: ERROR
    message: CORS allow-origin wildcard or reflected without a check.
    pattern-either:
      - pattern: '{..., "Access-Control-Allow-Origin": "*", ...}'
      - pattern: $H.set("Access-Control-Allow-Origin", "*")
      - pattern: |
          $O = $REQ.headers.get("Origin");
          ...
          $H.set("Access-Control-Allow-Origin", $O);
  - id: worker-sql-built-from-string
    languages: [javascript]
    severity: ERROR
    message: SQL text built by concatenation or template.
    pattern-either:
      - pattern: '$DB.prepare(`...${$X}...`)'
      - pattern: $DB.prepare("..." + $X)
      - pattern: '$DB.exec(`...${$X}...`)'
  - id: worker-error-detail-in-response
    languages: [javascript]
    severity: WARNING
    message: Exception text in a Response body.
    pattern-either:
      - pattern: new Response(<... $E.message ...>, ...)
      - pattern: new Response(<... $E.stack ...>, ...)
      - pattern: new Response(String($E), ...)
  - id: worker-log-of-request-or-secret
    languages: [javascript]
    severity: WARNING
    message: console output with request headers or an env value.
    patterns:
      - pattern-either:
          - pattern: console.$F(..., <... $R.headers ...>, ...)
          - pattern: console.$F(..., <... $ENV.$S ...>, ...)
          - pattern: console.$F(..., <... $AUTH ...>, ...)
      - metavariable-regex: {metavariable: $F, regex: '^(log|info|warn|error|debug)$'}
  - id: secret-compare-not-constant-time
    languages: [javascript]
    severity: INFO
    message: equality on a token-named value.
    patterns:
      - pattern-either:
          - pattern: $A === $B
          - pattern: $A !== $B
      - metavariable-regex: {metavariable: $A, regex: '(?i)^[\w.]*(token|secret|signature|apikey|api_key|hmac|password)$'}
```

</details>
