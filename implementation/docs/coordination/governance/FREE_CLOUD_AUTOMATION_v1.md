# Investment-System1 — PC 없는 무료 자동화 v1

Status: INACTIVE CONTROL-PLANE CANDIDATE
Authority: CDR-024 / Autonomous Execution & Decision Authority SSoT v1.1
Cost policy: NEW PAID RESOURCE NOT AUTHORIZED

## 목표

개인 PC, self-hosted runner, OpenAI API, 유료 LLM/API 없이 GitHub-hosted Actions만으로
가능한 자동화를 먼저 수행한다.

## 현재 허용 범위

1. GitHub event / workflow terminal 변화에서 자동 wake
2. 최신 Global checkout
3. AUTONOMY_MODE / Gate A / runtime state fail-closed 판정
4. deterministic tests / CI / 상태 분류
5. 유료 AI credential 미사용 검증

## 현재 비허용 범위

- Gate A CLOSED 상태에서 mutation
- AI가 필요한 설계/코드생성/복합 추론을 무료라고 가정
- canonical merge
- Holdout / Official/LIVE / paid API / credential 확장
- 실제 매매·주문·자금이동
- 보호 의미를 바꾸는 numeric/methodology 결정

## 무료 완전자동화의 현실적 경계

GitHub Actions만으로 deterministic 작업은 완전 자동화할 수 있다.
그러나 현재 공개된 무료 cloud 환경만으로 ChatGPT Main 수준의 범용 reasoning/code
generation을 무제한·무비용으로 보장할 수는 없다.

따라서 v1은 다음 구조다.

GitHub event
→ free-cloud-controller (read-only)
→ Gate A / RUN / IDLE 확인
→ deterministic D1/D2/D3-A eligible signal
→ [future bounded executor]
→ PR / CI / evidence

future bounded executor는 Gate A가 OPEN으로 증명된 뒤에만 별도 활성화한다.

## 비용 방어

- schedule polling 없음
- push/workflow_run/workflow_dispatch event만 사용
- external paid AI API 없음
- workflow timeout 5분
- concurrency cancel-in-progress
- repository credential은 GitHub 기본 read token만 사용

## 다음 Gate

1. 이 control-plane CI PASS
2. no-paid credential assertion PASS
3. Gate A의 watcher→executor 연결을 GitHub-native deterministic executor로 재정의할 수 있는지
   별도 검증
4. 실제 mutation executor를 추가할 경우 write-set/branch/lease/rollback/required-check를
   독립 검증
5. 그 전까지 AUTONOMY_MODE=READ_ONLY 유지

이 문서는 무료 경로를 승인하거나 RUN을 켜는 문서가 아니다.
비용이 생기는 API/서비스 추가는 여전히 D3-R이다.
