# 1인 비공개 구역 — 오너 폰 설정 절차 (2026-10-31, 설계 승인 뒤 진행)

설계: [PRIVATE_AREA_KIS_DESIGN_20261031](PRIVATE_AREA_KIS_DESIGN_20261031.md). 모든 단계는 폰 브라우저로 한다.
- GitHub 모바일 앱은 Secrets·토큰 화면이 없으니 브라우저를 쓴다.
- 키·토큰·이메일 값은 화면에 넣기만 한다. 채팅·문서·Notion에는 적지 않는다.

**먼저 알아 둘 것**

| 질문 | 답 |
| --- | --- |
| 도메인이 필요한가 | **아니오.** `workers.dev` 주소를 그대로 쓴다 |
| 결제 수단 등록이 필요한가 | **Cloudflare Zero Trust 가입 때만 필요하다.** 무료 요금제를 고르면 청구되지 않는다(Cloudflare 안내: "this step is still needed but you will not be charged"). GitHub와 KIS는 결제 수단이 필요 없다. GitHub에는 결제 수단을 넣지 않는다. 그래야 한도를 넘어도 청구 대신 실행이 멈춘다 |
| 비용 | 0원(설계 10절) |
| 걸리는 시간 | 1~6단계 합쳐 약 30~40분 |
| 순서 | 1·2·4는 지금 해도 된다. 3은 가지·로그 삭제만 지금, 공개 저장소 KIS Secrets 삭제는 Codex KIS 자료를 비공개 구역으로 옮긴 뒤(10/31 오너 방침). 5·6은 Main이 `kis-auth` Worker를 배포한 뒤(구현 3번째 PR) |

## 1. 새 비공개 저장소 만들기 (GitHub, 약 3분)

1. github.com 로그인 → 오른쪽 위 `+` → **New repository**.
2. 이름: `investment-system1-kis`(다른 이름이면 Main에게 알려 준다). **Private** 선택. **Add a README file** 체크. **Create repository**.
3. Claude가 이 저장소에 워크플로를 넣을 수 있게, Claude GitHub 앱 설치에 이 저장소를 추가한다.
   - 경로: github.com → Settings → Applications → Claude → Configure → Repository access → `investment-system1-kis` 추가 → Save.
   - 이 단계를 건너뛰면 워크플로 파일을 오너가 직접 붙여 넣어야 한다.

## 2. 새 저장소에 KIS 키 넣기 (GitHub, 약 3분)

1. KIS Developers(apiportal.koreainvestment.com) 로그인 → 마이페이지/API 신청 정보에서 앱키·앱시크릿을 확인한다.
   - GitHub에 이미 넣은 Secret 값은 다시 볼 수 없으니 KIS에서 다시 확인한다.
2. `investment-system1-kis` → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:
   - 이름 `KIS_APP_KEY`, 값: 앱키 → Add secret.
   - 이름 `KIS_APP_SECRET`, 값: 앱시크릿 → Add secret.
   - 이름만 정확히 맞추면 된다. 값은 앞뒤 공백 없이 넣는다.

## 3. 공개 저장소의 KIS 흔적 지우기 (GitHub, 약 5분)

1. **(이관 뒤)** `Investment-System1` → **Settings** → **Secrets and variables** → **Actions** → `KIS_APP_KEY` 줄의 휴지통(삭제) → 확인. `KIS_APP_SECRET`도 같은 방법으로 지운다.
   - 지금 지우지 않는다. Codex 연구 KIS 자료를 비공개 구역으로 옮긴 뒤 Main이 "Secrets 지워도 됨"이라고 알린다(그때 Codex KIS 워크플로와 원자료 저장소의 KIS release도 지운다).
2. 가지 삭제: `Investment-System1` → **Branches** → `claude/kis-verify-once` 휴지통.
   - 세션은 가지를 지울 권한이 없다(403).
   - 같은 화면에서 `claude/iex-expansion-measure-once`도 지운다.
3. (권장, `PRIV-LOGS`) 지난 KIS 검증 실행 로그 3건을 지운다.
   - 경로: `Investment-System1` → **Actions** → 왼쪽 `kis-verify-once` → 각 실행(41165294743, 41165951277, 41169962364) → 오른쪽 위 `…` → **Delete workflow run**.

## 4. Cloudflare Zero Trust 켜기 (약 10분, 결제 수단 입력)

1. dash.cloudflare.com 로그인 → 왼쪽 메뉴 **Zero Trust**.
2. 팀 이름을 정한다(예: `kco-invest`).
   - 로그인 주소 `kco-invest.cloudflareaccess.com`이 된다. 이 팀 이름을 Main에게 알려 준다(비밀 아님).
3. 요금제: **Free** → 결제 수단 입력(카드. 화면에 PayPal이 있으면 PayPal도 된다) → 완료.
   - 무료 요금제는 청구되지 않는다.
4. **Integrations** → **Identity providers** → **Add new identity provider** → **One-time PIN** → 저장.
5. **Access controls** → **Policies** → **Add a policy**:
   - Policy name: `owner-only`.
   - Action: **Allow**.
   - Include: Selector **Emails** → 오너 이메일 1개만.
   - (권장) Require: Selector **Login Methods** → **One-time PIN**.
   - Session duration: 24 hours(원하면 1주).
   - 저장한다. **Everyone·Emails ending in·Bypass는 쓰지 않는다.**

## 5. 로그인 Worker에 Access 걸기 (Main이 `kis-auth` 배포 뒤, 약 5분)

1. dash.cloudflare.com → **Workers & Pages** → `kis-auth` → **Access** 탭으로 간다.
   - 화면에 따라 Settings → Domains & Routes → **Enable Cloudflare Access**일 수 있다.
2. **All traffic**을 고른다. 정책은 **select an existing policy** → `owner-only` → 켠다.
3. 켤 때 나오는 창의 **AUD 태그**(긴 문자열)와 **팀 도메인**을 복사해 둔다. 6단계에서 쓴다.
4. **Zero Trust** → **Access** → **Applications** → `kis-auth` 앱 → **Login methods**:
   - **One-time PIN만** 켠다.
   - 기본 `Cloudflare` 로그인은 끈다.
   - 저장한다.

## 6. 자료 Worker에 설정 넣기 (Cloudflare + GitHub, 약 10분)

1. 읽기 전용 토큰 만들기(GitHub):
   - 경로: github.com → 프로필 → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
   - 이름: `kis-worker-read`.
   - Expiration: 366 days. 만료일을 Main에게 알려 주면 교체일을 기록한다.
   - Repository access: **Only select repositories** → `investment-system1-kis` 하나.
   - Permissions → Repository → **Contents: Read-only**(나머지는 손대지 않음).
   - **Generate token** → 표시된 토큰을 복사한다. 한 번만 보인다.
2. dash.cloudflare.com → **Workers & Pages** → `private-investment-history` → **Settings** → **Variables and Secrets** → **Add**:
   - `KIS_STORE_TOKEN`(Secret) = 1의 토큰.
   - `ACCESS_AUD`(Secret) = 5-3의 AUD 태그.
   - `ACCESS_TEAM_DOMAIN`(Text) = `https://<팀 이름>.cloudflareaccess.com`.
   - `ALLOWED_EMAIL`은 이미 있다. 그대로 둔다.
3. 같은 방법으로 `kis-auth` Worker에도 `ACCESS_AUD`·`ACCESS_TEAM_DOMAIN`을 넣는다.
4. Main에게 "6단계 끝"이라고만 알려 준다. 값은 보내지 않는다.

## 끝난 뒤 확인 (Main이 한다)

- 익명 요청이 401과 `no-store`를 받는지 확인한다(배포 확인 단계).
- 오너 폰 Safari에서 로그인 → 일회용 코드 → 앱으로 돌아오기 → 비공개 칸 표시를 확인한다(오너가 1회 눌러 봄).
- 수집기 첫 수동 실행: 개수·오류 코드만 확인한다. 이때 토큰 발급 알림(카카오톡) 1건이 간다.
