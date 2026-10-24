# 중앙 V 첫 게시 점검표 (go-live, 2026-10-24)

> **상태: 절차 문서.** 첫 게시 하루에 소유자가 순서대로 따라 하는 점검표다. 값(토큰·키·가격)은 이 문서에 없고, 어디에도 적지 않는다.
> 근거: [계획](CENTRAL_V_DC02_PLAN_20261024.md) 2절 "첫 게시"·4절 결정 D1~D10·5절 재대조, [설계](CENTRAL_V_PUBLICATION_DESIGN_20261018.md) §3·§6·§12, [U4·U5 요구](CENTRAL_V_U4_U5_NEEDS_20261023.md), [프로브·U8 사실](CENTRAL_V_PROBE_U8_FACTS_20261024.md), GSQ-024.

- 작성: 2026-10-24 UTC, PR-C(`claude/central-v-workflow`, PR-B `claude/central-v-guard` 위). 같은 날 Gate A 이메일 검사 때문에 두 브랜치를 같은 트리의 새 브랜치로 다시 올렸다: PR-B #403 `claude/central-v-guard-r2`, PR-C #404 `claude/central-v-workflow-r2`(옛 #401·#402는 닫음).
- 목표일: **2026-11-04 전 첫 게시.** 넘길 것 같으면 그 전에 D1을 (iii)(TARGET v1 확정 11-15 뒤 #393 병합, TARGET v1은 "임시 V")로 바꾸자고 Main이 먼저 보고한다.
- 휴대폰 브라우저만으로 할 수 있다. GitHub 화면에서 메뉴가 안 보이면 브라우저 메뉴의 "데스크톱 사이트"를 켠다.

## 0. 첫 게시 전에 소유자가 정할 것 (2026-10-24 검토에서 나온 것)

아래 두 가지는 **지금 규칙대로 게시하면 남는 한계**다. 첫 게시(3단계) 전에 소유자가 수락하거나 바꾸는 규칙을 승인해야 한다. Main은 이 두 줄을 `USER_DECISIONS_PENDING`의 남은 결정 표로 옮긴다.

| 번호 | 무엇이 남나 | 선택지 | 결정 전 동작 |
| --- | --- | --- | --- |
| CV-LEAK | **사유 묶음(D-CV2 (b))은 가격 경계를 숨기지 못한다.** 원 사유는 정해진 요인 칸에만 나와 칸이 원 사유를 되돌려 준다. 예: 수익률 세 칸이 묶음 사유면 "가격 ≤ (현금 − 부채) ÷ 주식수", 기대 점검 칸이면 "가격이 공개 DCF 구간 밖". 사유가 없어도 V 축 점수 유무와 `rank`/`qg_reference_order`가 같은 사실을 보인다. 즉 V를 공개하는 것 자체에 딸린 누출이다(설계 §4-4 정정 메모, `public_price_boundary/AUDIT.md` §10-6-1) | (i) 수락하고 게시 / (ii) 해당 행 V 비공개(규칙 변경, 누출을 다 없애지는 못함) / (iii) 다른 규칙 | 묶음은 표시 어휘로만 유지, 게시 안 함(3단계 보류) |
| CV-SPLIT | **주식수를 실은 서류의 접수 뒤~기준일에 일어난 주식분할은 잡지 못한다.** 그 행의 공식 V·순위가 분할 비율만큼 틀린 채 다음 10-Q·10-K까지 남는다(예: NVDA 2024 10:1, 약 2.5개월). 결정 D6 (a)(F_k 근거 재사용)로 연결한 규칙은 접수 **전** 분할만 보는 보수 규칙이다(설계 §7 메모, `U4_U5` §4) | (i) 수락하고 게시 / (ii) 새 장치 승인(D6 (b): V 단계 RAM에서 오늘 IEX 원가격을 비공개 최신 원 월말가와 비교해 분할 비율 대역이면 `SPLIT_AFTER_SHARE_COUNT`) | 게시 안 함(3단계 보류) |
| CV-CARRY(선택) | V 단계가 라이브 게시본을 3번 다 못 읽고 배포는 읽는 날, 그날 배포에서 게시본이 사이트에서 하루 빠진다(`NOT_RUN LIVE_UNREACHABLE` → 배포 `MISSING` → `WITHHELD`). 다음 성공 실행이 다시 낸다 | (i) 수락 / (ii) 배포 잡이 검증된 라이브 바이트를 다시 넣어 올리기(배포 잡 새 업로드 = 게시 경로 정적 시험 변경) | (i)처럼 동작 |

## 한눈에

| 순서 | 누가 | 할 일 | 끝난 표시 |
| --- | --- | --- | --- |
| 0 | 소유자 | 0절 CV-LEAK·CV-SPLIT 결정 | 결정 기록 |
| 1 | 소유자 | Secret 2개 등록(`RAW_REPO_READ_TOKEN`, `QGV_OFFICIAL_HMAC_KEY`) | Secrets 목록에 이름 2개 |
| 2 | 소유자 승인 → Main | 같은 날 병합: #393 → PR-A → PR-B → PR-C | 네 PR 모두 Merged, 각 최종 HEAD 필수 체크 녹색 |
| 3 | 소유자 | `SEC daily public reported inputs`를 `all_shards=true`로 1회 실행 | 실행 1건이 시작됨 |
| 4 | 소유자 | 그 실행의 한 줄 `QGV_OFFICIAL …` 확인 | `attempt=OK … published=NEW` |
| 5 | 소유자 | 실사이트에 `qgv-official.json`이 있는지 확인 | 파일이 열리고 가격 칸이 없음 |
| 6 | Main | #393 숫자 재대조(계획 5절) | 재기록 PR 승인 요청 |
| 7 | 소유자(폰) | PR-D 병합 뒤 TARGET v1에서 초안을 만들어 공식 V 확인(5-1절) | 후보 표 머리 `V(공식 V)`, IEX 출처 문구·약관 링크·가격 기준일 |

## 1. Secret 2개 등록 (소유자, 결정 D2 (a))

값은 만든 화면에서 복사해 Secret 입력 칸에 바로 붙여 넣는다. 메모·대화·문서·사진에 남기지 않는다. 등록한 값은 GitHub에서도 다시 보이지 않는다(이름만 보인다).

### 1-1. `RAW_REPO_READ_TOKEN` — 비공개 원자료 저장소 읽기 전용 토큰

1. github.com 로그인 → 오른쪽 위 프로필 사진 → **Settings** → 맨 아래 **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. 입력:
   - Token name: 알아볼 이름(예: `qgv-official-read`). 이름은 비밀이 아니다.
   - Resource owner: `kco994553-star`.
   - Expiration: 원하는 기간. 끝나면 V 단계가 `SUPPLY_FAILED MONTHEND_…`로 멈추고 직전 정상본을 유지한다. 그때 새로 만들어 같은 이름으로 바꿔 넣는다.
   - Repository access: **Only select repositories** → `kco994553-star/investment-system1-raw` **하나만**.
   - Permissions → Repository permissions → **Contents: Read-only** 하나만(Metadata: Read-only는 자동). 다른 권한은 주지 않는다.
3. **Generate token** → 한 번만 보이는 토큰을 복사한다.
4. 저장소 `kco994553-star/Investment-System1` → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
   - Name: `RAW_REPO_READ_TOKEN`(정확히 이 철자)
   - Secret: 복사한 토큰 붙여 넣기 → **Add secret**.

### 1-2. `QGV_OFFICIAL_HMAC_KEY` — 게시본 지문용 비밀 키

- 아무 의미 없는 임의 문자열이면 된다. **16바이트 이상**이어야 하고, 32자 이상을 권한다. 짧으면 `NOT_RUN HMAC_KEY_MISSING`이다.
- 만드는 법: 휴대폰 비밀번호 관리자의 "강력한 비밀번호 생성"(iOS 암호 제안, Chrome 비밀번호 생성 등)으로 만든 값을 복사한다. 저장하라는 제안은 거절한다.
- 같은 화면(**Secrets and variables → Actions → New repository secret**)에서 Name `QGV_OFFICIAL_HMAC_KEY`, Secret에 붙여 넣기 → **Add secret**.
- 이 키는 `publication_id` 계산에만 쓰이고 공개되지 않는다. 잃어버려도 새로 만들어 바꿔 넣으면 된다(다음 게시본의 `publication_id`만 달라진다. 같은 기준일·같은 입력이면 배포 신선도 검사는 `REPLACED`로 통과한다).

### 1-3. 확인

- **Settings → Secrets and variables → Actions** 목록에 `RAW_REPO_READ_TOKEN`, `QGV_OFFICIAL_HMAC_KEY` 두 이름이 있다. 기존 `RAW_REPO_TOKEN`·`SEC_USER_AGENT` 등은 그대로다.
- Secret이 없거나 비어 있으면 V 단계는 `NOT_RUN`(내려받기 전, 종료 코드 0)이고 다른 단계·배포는 그대로 돈다. 연속 실행 기록은 끊기지 않는다.

## 2. 같은 날 병합 (결정 D1 (ii): #393은 중앙 V 첫 게시와 같은 배포 창)

| 순서 | PR | 내용 | 승인 |
| --- | --- | --- | --- |
| 1 | #393 `claude/cv-fk-calc-version` | F_k(분할 기준 계수), calc_version `qgv2-calc/2026-10-23.1` | 계산 변경 |
| 2 | PR-A #400 `claude/central-v-core` | IEX 어댑터·C 파서·게시기·검증기(#393 위) | 계산 코드 |
| 3 | PR-B #403 `claude/central-v-guard-r2` | 가드: 허용 파일·`rows.<code>.rank` 한 경로 예외·IEX 경로·신선도 규칙 | GSQ-024: 가드는 별도 승인 |
| 4 | PR-C #404 `claude/central-v-workflow-r2` | 워크플로: collect V 단계·비공개 이력·verify 검사·수동 배포 보존 | 워크플로 변경 |

- 각 PR은 최종 HEAD에서 필수 체크가 모두 녹색일 때만 병합한다. 앞 PR이 병합되면 다음 PR의 차이가 줄어든다(같은 사슬이라 텍스트 충돌은 없어야 한다. 생기면 Main이 병합 커밋으로 맞추고 체크를 다시 돌린다).
- **시각:** 그날 정기 실행(00:37 UTC 무렵 시작 = 09:37 KST, 약 40분)이 끝난 뒤 병합하고, 마지막 병합 직후 3단계를 한다. 정기 실행이 먼저 새 코드로 돌면 행 대부분이 옛 calc_version이라 `CALC_VERSION_MISMATCH` NA가 많은 게시본이 나온다(틀린 값은 아니고 비어 있을 뿐이다). 그래도 같은 날 `all_shards` 실행이 같은 기준일·더 늦은 입력으로 바꾼다(신선도 `NEWER`/`REPLACED`).

## 3. `all_shards` 1회 실행 (소유자 승인)

- 저장소 → **Actions** → 왼쪽 목록 **SEC daily public reported inputs** → **Run workflow** → Branch는 기본 브랜치 그대로 → **`1회성: 504종목 전체 샤드를 한 번에 수집(새 계산 규칙 게시용)`** 체크 → **Run workflow**.
- 진행 중이거나 대기 중인 실행이 있으면 기다린다(한 번에 하나만 돌고, 대기는 하나만 남는다).
- 걸리는 시간(추정): collect 약 60~75분(샤드 7개 약 40분 + V 단계 약 4~7분, 한도 120분) + verify 약 23분 + deploy 1분.
- 504행이 하루에 새 calc_version이 되어 혼합 기간이 하루로 줄어든다.

## 4. 한 줄 결과 확인

실행 화면 → **collect** 잡 → 단계 **Publish the central QGV from one IEX HIST day (…)** 를 펼친다. 가격·URL·키는 출력되지 않는다.

```
QGV_OFFICIAL attempt=OK reason=- published=NEW basis=YYYY-MM-DD rows=523 ranked=<n> supplied=<n>/<m>
```

- `basis`는 실제 IEX 기준일이다. T+1이라 보통 실행일 기준 **전 거래일**이다(결정 D3). 요청 기준일은 게시본 `price_source.requested_basis_date`에 따로 있다.
- `supplied=n/m`: m은 **가격 없이도 V 축 가중치 50%에 닿을 수 있는** GENERAL 단면 Universe 행 수(USD, ADR·분할 규칙 밖; `qgv_official.supply_eligible`), n은 그중 그날 IEX 가격을 얻은 행 수다. n < ceil(0.95 × m)이면 게시하지 않는다(결정 D4). V 입력 블록만 있고 가격이 있어도 V가 나올 수 없는 행은 m에 넣지 않는다(2026-10-24 검토로 바로잡음; 공개 10-24 파일로 측정하면 옛 정의 430, 지금 정의 358).
- 같은 잡의 다음 단계 **Copy a new central QGV publication to the private dated history (…)**: `QGV_OFFICIAL_HISTORY RAW_UPLOADED tag=qgv-official-<기준일> …`(결정 D9, 비공개 저장소에 점수만).
- **verify** 잡 → **Check the central QGV publication without prices (…)**: `QGV_OFFICIAL_CHECK publication=VALID status=VALID consistent=YES new=YES …`와 시험 통과. 이 단계가 실패하면 `QGV_OFFICIAL_VERIFY_FAILED` 주석이 붙지만 배포는 막지 않는다(게시본 자체가 틀리면 그 위 단계의 아티팩트 가드가 막는다).
- **deploy** 잡 → 신선도 단계: `PAGES_FRESHNESS file=qgv-official.json section=publication verdict=NO_LIVE kind=NEW …`(첫 게시).

| 첫 줄이 이렇다면 | 뜻 | 할 일 |
| --- | --- | --- |
| `attempt=NO_OFFICIAL_YET reason=HMAC_KEY_MISSING` | 키 Secret이 없거나 16바이트 미만 | 1-2 다시, 그다음 3단계 다시 |
| `reason=MONTHEND_TOKEN_MISSING` | 읽기 토큰 Secret 없음 | 1-1 다시 |
| `reason=SEC_QGV2_CALC_VERSION_BEFORE_U7` | 입력이 23.1 전(#393 미병합 또는 옛 파일) | 2단계 확인 |
| `reason=SEC_QGV2_NOT_AVAILABLE` | 그 실행의 `sec-qgv2.json`을 못 읽음 | Main에 보고 |
| `reason=PARSER_MISSING` (위에 `QGV_OFFICIAL_PARSER_BUILD_FAILED`) | C 파서 빌드 실패 | Main에 보고 |
| `reason=IEX_…` | IEX 색인·파일·검사 실패(공급) | 다음 날 정기 실행이 다시 시도. 이틀 연속이면 Main에 보고 |
| `reason=MONTHEND_…` | 월말가 저장소 읽기 실패(토큰 권한·만료 포함) | 1-1의 저장소·권한 확인 |
| `reason=SUPPLY_BELOW_THRESHOLD` | 가격 확보 95% 미만 | 직전 정상본 유지. Main에 보고 |
| `reason=JS_TWIN_…` 또는 `OFFICIAL_…` | 검증 실패(Python·JS 결과 불일치 등) | 직전 정상본 유지. Main에 보고 |
| `QGV_OFFICIAL_STEP_STOPPED exit=124` | 단계 시간 한도(12분) 초과 | 다음 날 다시. 반복되면 Main에 보고 |
| `attempt=NOT_RUN reason=LIVE_UNREACHABLE` | 라이브 `qgv-official.json`을 3번 다 읽지 못함(404가 아닌 실패). 아무것도 계산하지 않았고 그날 아티팩트에 게시본이 없다. 배포가 라이브를 읽으면 그날 사이트에서 게시본이 빠진다(0절 CV-CARRY) | 다음 날 정기 실행이 다시 낸다. 이틀 연속이면 Main에 보고 |
| `QGV_OFFICIAL_GUARD_REFUSED` | V 단계의 아티팩트 가드가 V 파일을 거부. 두 파일을 지우고 단계만 실패로 끝남(이력 단계 건너뜀, 나머지 파일은 다음 필수 단계의 가드가 확인). 다른 단계·배포는 계속 | Main에 즉시 보고(검증기와 가드의 어긋남) |
| `published=KEPT_SAME_ID` | 입력(`sec-qgv2.json` 바이트)과 가격이 모두 같아 기존 게시본 유지. 같은 날 같은 입력으로 다시 돌린 경우에만 나온다 | 정상 |

어떤 경우든 V 단계는 종료 코드 0이고 `continue-on-error`라 원장·뉴스·SEC 파일 배포와 연속 실행 기록에는 영향이 없다.

## 5. 실사이트 확인

- `https://kco994553-star.github.io/Investment-System1/qgv-official.json`을 연다(배포 몇 분 뒤).
  - `"schema":"qgv-official/1"`, `price_source.basis_date`·`requested_basis_date`, `attribution`(IEX 표시 문구와 "IEX 마지막 체결가 기준(공식 종가 아님)"), `rows`의 점수·순위·사유·`coverage`.
  - `price`·`close`·`ev`·`market_cap`·수익률 같은 칸이 **없어야** 한다(검증기와 가드가 거부한다).
- `…/qgv-official-status.json`: `attempt_state` `OK`, `official_publication_id`가 게시본과 같다.
- 화면 반영은 화면 판독기 PR(PR-D 새 프론트엔드, 결정 D8 (b) 옛 화면 작은 판독기) 뒤다. 그 전에는 파일만 있고 화면 V는 그대로다.

### 5-1. TARGET v1 화면 확인 (소유자, 폰, PR-D 병합 뒤 · 2026-10-24 추가)

1. 사이트 → 플레이북(`#playbook`) → TARGET v1 빌더. 누르기 전 빌더 칸에는 출처를 정하지 않은 문구 "V 출처: 초안 만들 때 확인 · 유효한 중앙 게시본이 있으면 공식 V, 없으면 임시 V"만 있다(화면을 여는 것만으로는 게시본을 읽지 않는다). 전에 만든 초안이 있으면 그 아래 후보 표·확정 칸은 그 초안의 출처(대개 `V(임시 V)`)를 그대로 보인다. 그 초안은 "규칙으로 초안 다시 만들기"를 누른 뒤에 다시 판정된다(카드 응답이 있으면 한 번 더 누르라는 확인이 나온다).
2. "규칙으로 초안 만들기"를 누른다(이 기기 가격이 없으면 "중앙 V 게시본으로 초안 만들기").
3. 확인(다시 만든 뒤): 후보 표 머리가 `V(공식 V)`, 출처 줄이 "공식 V (중앙 게시 · IEX 마지막 체결가 기준(공식 종가 아님)) · 가격 기준일 D · 게시본 qgvpub-…", 그 아래 "IEX 마지막 체결가 기준(공식 종가 아님) · 가격 기준일 D · Data provided for free by IEX. …"와 "이용 약관" 링크. 게시 다음 거래일 안에 확인한다(기준일 뒤 마감된 뉴욕 거래일이 2일을 넘으면 `OFFICIAL_STALE`로 임시 V; 오늘 거래일은 뉴욕 16:00 마감 뒤부터 센다).
4. 공식 V가 아니면 빌더 아래 한 줄(`공식 V 사용 안 함 · <코드> · …`)의 코드를 Main에 알려 준다. 가격·숫자는 적지 않는다.
5. **확정은 아직 안 된다.** 6절 재기록 PR 병합 전에는 `NUMBER_CHECK_CALC_VERSION_MISMATCH`, `all_shards=true` 실행 전에는 `CALC_VERSION_MIXED`로 막힌다. 초안·카드 응답은 미리 해 둘 수 있다(확정 때 게시본이 바뀌었으면 `V_SOURCE_CHANGED`로 초안을 다시 만들고 같은 종목 응답은 유지).

## 6. #393 숫자 재대조 (Main, 계획 5절)

- 첫 게시 실행의 `sec-qgv2.json`: 최상위 calc_version `qgv2-calc/2026-10-23.1`, 504행, 값 있는 행의 `CALC_VERSION_MIXED` 0, sha256·as_of 기록.
- 마지막 17.1 게시본과 첫 23.1 게시본의 504행 비교(F_k 키 제외 같음), 10종목 40칸, FCF 수익률 7칸(합성 가격, 메모리에서만).
- 재기록 PR은 #391 병합 뒤에 만들고 승인 뒤 병합한다. 그 전까지 TARGET 확정 버튼은 `NUMBER_CHECK_CALC_VERSION_MISMATCH`로 막힌다(약 1~2일, 확정 창 11-09~11-15 전).

## 7. 다음 날부터

- 매일 정기 실행에서 같은 한 줄을 본다. **보통은 매일(주말 포함) `published=NEW`다.** 샤드 단계가 매 실행 `sec-qgv2.json`을 새 `as_of`로 다시 쓰므로 입력 해시가 매일 바뀌고, 그래서 `publication_id`도 매일 바뀐다. 기준일이 새 날이든, 주말처럼 기준일은 같고 입력만 더 늦든 `NEW`이고 배포 신선도는 `NEWER`로 통과한다. 비공개 이력 단계도 매 실행 `qgv-official-<기준일>` 태그에 자산 한 쌍을 더한다(주말에는 금요일 기준일 태그에 날마다 하나씩).
  - `KEPT_SAME_ID`는 같은 입력 바이트로 다시 돌린 경우(같은 날 재실행)에만 나온다.
  - 실패하면 `KEPT_LAST_GOOD`(공개 파일은 직전 정상본 그대로), 라이브를 못 읽으면 `NOT_RUN LIVE_UNREACHABLE`(그날만 게시본 없음, 위 표).
  - 연속 기록을 볼 때는 `attempt=OK`인지 보면 된다. `published` 값이 날마다 `NEW`인 것은 정상이다.
- 월말가 저장소는 U8(2026-10-23) 한 번뿐이다. 그 뒤 끝나는 회계연도 말월은 `MONTH_END_PRICE_NOT_AVAILABLE`로 빠진다. 갱신 방식 D5 (b)는 읽기 전용 토큰과 충돌해 이번 PR에 없다(Main이 따로 올린다).
- 첫 반일 장 2026-11-27: 그날 기준 실행의 `supplied`·`ranked` 개수를 평소와 비교한다(가격은 보지 않는다).
- 멈추려면: Secret 두 개 중 하나를 지우면 다음 실행부터 `NOT_RUN`이고 마지막 정상본이 계속 실린다(그 사본도 매일 V 단계의 가드를 다시 거친다. 가드가 거부하면 `QGV_OFFICIAL_GUARD_REFUSED`로 그 단계 안에서 빠지고 잡은 계속된다). 공개 파일 자체를 내리는 것은 별도 PR이 필요하다(자동으로 지우지 않는다).
- 규칙(엔진·가중치·설정 버전)을 바꾸는 PR이 병합되면, 그 전 코드로 만든 라이브 게시본은 새 검증기에서 무효라 다음 성공 실행까지 사이트에서 빠진다(`AUDIT.md` §10-6-2). 그런 PR은 정기 실행 직전보다 직후에 병합하는 편이 빠지는 시간이 짧다.
