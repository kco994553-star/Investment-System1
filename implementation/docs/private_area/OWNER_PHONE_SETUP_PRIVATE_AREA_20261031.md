# 1인 비공개 구역 — 오너 폰 설정 절차 (2026-10-31, 설계 승인 뒤 진행)

> **10/31 진행 상황(오너):** 1단계(비공개 저장소 `investment-system1-kis-private`, 오너가 이름에서 앞 하이픈을 뺌)·2단계(KIS Secrets)·3단계(가지·로그 정리) 완료. **Cloudflare Zero Trust·Access는 쓰지 않는다(대체됨, `PRIV-AUTH-GOOGLE` 10/31 승인).** 옛 4~6단계는 아래 새 4~6단계(Worker 읽기 토큰)로 바뀌었다. 결제 수단은 어디에도 필요 없다.

설계: [PRIVATE_AREA_KIS_DESIGN_20261031](PRIVATE_AREA_KIS_DESIGN_20261031.md). 모든 단계는 폰 브라우저로 한다.
- GitHub 모바일 앱은 Secrets·토큰 화면이 없으니 브라우저를 쓴다.
- 키·토큰·이메일 값은 화면에 넣기만 한다. 채팅·문서·Notion에는 적지 않는다.

**먼저 알아 둘 것**

| 질문 | 답 |
| --- | --- |
| 도메인이 필요한가 | **아니오.** `workers.dev` 주소를 그대로 쓴다 |
| 결제 수단 등록이 필요한가 | **아니오(10/31부터).** Zero Trust를 쓰지 않으므로 필요 없다(`PRIV-PAYMENT` 불필요). 옛 안내: Cloudflare Zero Trust 가입 때만 필요했다. 무료 요금제를 고르면 청구되지 않는다(Cloudflare 안내: "this step is still needed but you will not be charged"). GitHub와 KIS는 결제 수단이 필요 없다. GitHub에는 결제 수단을 넣지 않는다. 그래야 한도를 넘어도 청구 대신 실행이 멈춘다 |
| 비용 | 0원(설계 10절) |
| 걸리는 시간 | 4~6단계 합쳐 약 12분 |
| 순서 | 1~3은 끝났다. 공개 저장소 KIS Secrets는 Codex 연구 가지의 워크플로 2개만 쓰고 Codex 자료 이관에는 필요 없으므로 지워도 된다(10/31 확인). 4~6은 Main이 Worker PR을 배포하기 직전에 한다 |

## 1. 새 비공개 저장소 만들기 (GitHub, 약 3분)

1. github.com 로그인 → 오른쪽 위 `+` → **New repository**.
2. 이름: `investment-system1-kis-private`(다른 이름이면 Main에게 알려 준다). **Private** 선택. **Add a README file** 체크. **Create repository**.
3. Claude가 이 저장소에 워크플로를 넣을 수 있게, Claude GitHub 앱 설치에 이 저장소를 추가한다.
   - 경로: github.com → Settings → Applications → Claude → Configure → Repository access → `investment-system1-kis-private` 추가 → Save.
   - 이 단계를 건너뛰면 워크플로 파일을 오너가 직접 붙여 넣어야 한다.

## 2. 새 저장소에 KIS 키 넣기 (GitHub, 약 3분)

1. KIS Developers(apiportal.koreainvestment.com) 로그인 → 마이페이지/API 신청 정보에서 앱키·앱시크릿을 확인한다.
   - GitHub에 이미 넣은 Secret 값은 다시 볼 수 없으니 KIS에서 다시 확인한다.
2. `investment-system1-kis-private` → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:
   - 이름 `KIS_APP_KEY`, 값: 앱키 → Add secret.
   - 이름 `KIS_APP_SECRET`, 값: 앱시크릿 → Add secret.
   - 이름만 정확히 맞추면 된다. 값은 앞뒤 공백 없이 넣는다.

## 3. 공개 저장소의 KIS 흔적 지우기 (GitHub, 약 5분)

1. `Investment-System1` → **Settings** → **Secrets and variables** → **Actions** → `KIS_APP_KEY` 줄의 휴지통(삭제) → 확인. `KIS_APP_SECRET`도 같은 방법으로 지운다. `KIS_APPKEY`·`KIS_APPSECRET`이라는 이름이 있으면 그것도 지운다.
   - 10/31 확인: 이 Secrets를 쓰는 것은 Codex 연구 가지 2곳(`research/bt-data-pilot-alpaca-probe-20261031`, `research/lab-contract-private-pilot-20261031`)의 워크플로 2개(`bt-data-pilot-kis.yml`·`bt-data-pilot-pre2016.yml`)뿐이다. canonical과 다른 가지에는 없다. Codex 자료 이관은 원자료 저장소 토큰만 쓰므로 KIS 키가 필요 없다. **지워도 된다.** 지운 뒤 그 두 워크플로가 돌면 KIS 단계에서 실패한다(오너가 꺼 둠, `PRIV-CODEX-WF-OFF`).
2. 가지 삭제: `Investment-System1` → **Branches** → `claude/kis-verify-once` 휴지통.
   - 세션은 가지를 지울 권한이 없다(403).
   - 같은 화면에서 `claude/iex-expansion-measure-once`도 지운다.
   - 10/31 10:00 UTC 확인: 두 가지가 아직 원격에 있다. `claude/kis-verify-once`의 KIS 워크플로는 마지막 커밋에서 이미 지워져 Secrets를 쓰지 않는다.
3. (권장, `PRIV-LOGS`) 지난 KIS 검증 실행 로그 3건을 지운다.
   - 경로: `Investment-System1` → **Actions** → 왼쪽 `kis-verify-once` → 각 실행(41165294743, 41165951277, 41169962364) → 오른쪽 위 `…` → **Delete workflow run**.

## 4. Worker 읽기 토큰 만들기 (GitHub, 약 5분, Worker PR 배포 직전에 한다)

Worker가 비공개 저장소의 자료를 **읽기만** 하는 토큰이다. 저장소 하나, 읽기 전용, 최소 권한.
1. github.com(폰 브라우저) → 오른쪽 위 프로필 → **Settings** → 맨 아래 **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. 칸 채우기:
   - Token name: `worker-private-repo-read`.
   - Expiration: **90 days**(권장. 최대 1년까지 고를 수 있다). 화면에 보이는 만료 날짜(YYYY-MM-DD)를 적어 둔다.
   - Resource owner: `kco994553-star`.
   - Repository access: **Only select repositories** → `investment-system1-kis-private` **하나만**.
   - Permissions → **Repository permissions** → **Contents: Read-only**. 다른 권한은 모두 그대로 둔다(No access). Metadata: Read-only는 자동으로 붙는다.
   - Account permissions는 아무것도 켜지 않는다.
3. **Generate token** → 토큰을 복사한다. 한 번만 보인다. 채팅·문서·Notion에 붙여 넣지 않는다.

## 5. Worker에 토큰과 만료일 넣기 (Cloudflare, 약 5분)

1. dash.cloudflare.com → **Workers & Pages** → `private-investment-history` → **Settings** → **Variables and Secrets** → **Add**:
   - Type **Secret**, 이름 `PRIVATE_REPO_READ_TOKEN`, 값 = 4단계 토큰. (이름에 `KIS_`를 쓰지 않는다. 공개 가드가 막는다.)
   - Type **Text**, 이름 `PRIVATE_REPO_READ_TOKEN_EXPIRES_ON`, 값 = 4단계 만료 날짜(예: `2027-01-29`). 비밀이 아니다.
   - `ALLOWED_EMAIL`·`GOOGLE_CLIENT_ID`는 이미 있다. 그대로 둔다.
2. **Deploy**(저장)를 누른다.

## 6. 비공개 저장소에 만료일 적기 (GitHub, 약 2분)

상태 파일이 만료 경고를 낼 수 있게 날짜만 적는다(비밀 아님).
1. `investment-system1-kis-private` → **Settings** → **Secrets and variables** → **Actions** → **Variables** 탭 → **New repository variable**.
2. 이름 `WORKER_READ_TOKEN_EXPIRES_ON`, 값 = 4단계 만료 날짜.
3. Main에게 "6단계 끝"이라고만 알려 준다. 값은 보내지 않는다.

**토큰을 바꿀 때(만료 14일 전 경고가 뜨면):** 4단계로 새 토큰을 만든다 → 5단계에서 `PRIVATE_REPO_READ_TOKEN` 값과 만료일을 바꾼다 → 6단계 날짜를 바꾼다 → 옛 토큰은 GitHub 토큰 목록에서 **Delete**.

## 끝난 뒤 확인 (Main이 한다)

- 익명 요청이 403과 `no-store`를 받는지 확인한다(배포 확인 단계).
- 오너 폰 Safari에서 "비공개 연결" → Google 로그인 → 비공개 칸 표시를 확인한다(오너가 1회 눌러 봄).
- 수집기 첫 수동 실행: 개수·오류 코드만 확인한다. 이때 토큰 발급 알림(카카오톡) 1건이 간다.
