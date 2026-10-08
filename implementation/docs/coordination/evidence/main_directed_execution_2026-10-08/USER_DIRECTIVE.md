[Main 실행 지시 — v1.1(CDR-024) 범위 안에서 진행. 이 프롬프트 하나로 끝까지 진행하라]

사용자 결정·승인 (2026-10-08, Decision Register에 원문과 함께 append-only 기록)
- 기준 브랜치 Ruleset "HG-02 canonical hard guard"를 Active로 설정함:
  Bypass list 비움, Restrict deletions, Require a pull request(승인 0),
  Require status checks(repository-guard), Block force pushes.
- PR #51(Gate A guard를 기준 브랜치에 도입) 병합을 승인함. 이 승인은 #51에만 해당한다.

0. 시작
- Loop Card(0A)대로 fresh-read 후 lane별 Lease 획득. AUTONOMY_MODE는 READ_ONLY 유지.
- 사이클당 task 5개 도달 시 Checkpoint 후 다음 사이클로 이어서 진행.
- 막히는 lane만 WAIT, 나머지 lane은 계속 진행한다.

1. 자동화 확장 동결
- Gate A OPEN + 제품 blocker 1개 이상 종료 전까지 자동화·컨트롤러·트리거·쓰기 범위를 늘리는 PR 금지.
- 이미 병합된 #55–#60의 버그 수정만 허용.

2. #51 병합과 HG-02 검증
- #51을 최신 상태로 맞추고 repository-guard 체크 통과를 확인한 뒤 PR로 병합한다(force push 금지).
  체크가 "Waiting for status"로 멈추면 원인을 확인하고, Ruleset 조정이 필요하면
  26E 형식으로 사용자에게 한 번만 요청하고 이 lane만 WAIT.
- 실행자 신원 확인: Codex·Claude 등 자동 실행자가 GitHub에 어떤 신원(앱/개인 토큰)으로
  push하는지 확인해 기록한다.
- 설정 evidence: GET /repos/{owner}/{repo}/rules/branches/{기준 브랜치}로 적용 규칙을 조회해 저장한다.
- 행동 evidence (각 실행자 신원으로, 기대 결과는 모두 "거부"):
  · 기준 브랜치: 무해한 표시 파일 커밋을 PR 없이 직접 push (비파괴 시험만)
  · rules API로 hg02-canary 브랜치에도 같은 규칙이 적용되는지 확인하고, 적용되면 그 브랜치에서
    PR 없는 직접 push / force push / 브랜치 삭제를 시험한다.
  · 기준 브랜치에서 force push·삭제 시험은 절대 하지 않는다.
- 하나라도 거부되지 않으면 즉시 중단하고, 기준 브랜치가 바뀌었으면 PR로 되돌린 뒤 HG-02 FAIL과
  우회 경로를 보고한다.
- 판정: 모든 시험이 거부되면 VERIFIED. force push·삭제를 시험할 브랜치가 없으면
  PARTIAL_VERIFIED로 두고, 사용자에게 "Ruleset Target에 hg02-canary 추가"를 26E로 한 번 요청한다.

3. Gate A 판정
- HG-01·HG-03 기존 evidence + HG-02 결과 + Watcher→Work E2E 1회 성공을 합쳐 PART G 기준으로 판정.
- Watcher→Work E2E: 무해한 문서 변경으로 GitHub 변화 → Watcher 감지 → Work wake → Lease →
  커밋 → Handoff 갱신이 실제로 이어지는지 1회 확인. PAUSE일 때 wake 신호가 안 나가는지도 확인.
- Gate A가 OPEN이어도 AUTONOMY_MODE는 바꾸지 않는다. RUN 전환은 사용자가 한다.

4. PPA-F08 수정 (첫 제품 blocker)
- #36에서 발견된 app.js의 ACTUAL→TARGET 비중 대체(head fb086ea 기준 303·307행 부근).
- ACTUAL이 없거나 사용할 수 없으면 NOT_AVAILABLE로 표시하고 TARGET으로 대체하지 않는다.
- 완료 조건: 대체를 재현하는 negative test 추가, 기존 테스트 유지, 브라우저 검증 1회
  (390px, ko/en, ACTUAL NOT_AVAILABLE).
- 표시 계층만 수정. 계산식·임계값·계약 변경 금지.

5. TARGET 결정 패키지 (#54)
- Portfolio TARGET, Security identity, Strategy Theme에 대해 26E 형식 D3-R 요청을 하나로 묶는다.
- 목표 테마·비중은 사용자가 정의하는 값이다. 에이전트가 값을 제안하거나 채우지 않고 입력 양식만 준비한다.
- Security 0/19는 승인된 식별 계약으로 처리 가능한 종목과 사용자 결정이 필요한 종목으로 나눈다.

6. FPIA B1–B4
- 저장소와 열린 PR(#42, #46, #47 등)에서 Claude 감사 파일 묶음(감사 보고서, 재현 반례, 회귀 테스트)을
  찾아 그대로 인수한다. 반례를 새로 만들지 않는다.
- 찾지 못하면 이 lane만 WAIT_DEPENDENCY로 두고 보고한다.
- 범위는 B1–B4와 직접 연결된 공통 원인만. 완료 조건: 반례 차단, 정상 사례 보존, 관련 회귀 통과.
- 같은 방식 수정 3회 실패 시 재계획(9A). 미해결 동안 해당 통합 승인은 차단.

7. 보고 (Checkpoint마다)
- 닫힌 제품 blocker 수와 ID (목표: 1개 이상)
- 수정 커밋(branch, exact HEAD)과 테스트·CI·브라우저 evidence
- HG-01/02/03 상태, Gate A 판정, E2E 결과
- 사용자 D3-R 묶음 (있을 때만, 한 번에)
- 남은 blocker와 의존성

포함하지 않는 것
- #51 외의 기준 브랜치 병합, 새 투자 계산법, Holdout 기간 선택·소비,
  AUTONOMY_MODE 변경, Ruleset 변경, 실 credential 사용.
