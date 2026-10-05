# Investment-System1 — Autonomous Execution & Decision Authority SSoT v1.1

Status: ADOPTED COMMON SSoT (v1.1)  
Purpose: Investment-System1 공통 자율실행·승인권한 정책  
Scope: Main / Chart / QGV / Product Platform 및 향후 동일 체계를 사용하는 Work  
Principle: Prompt-first, SSoT-driven, history-preserving, fail-closed

Adopted: 2026-10-05, 사용자 명시 승인 — Decision Register CDR-024  
Supersedes: v1.0 (본문 보존, 보강 조항은 [v1.1] 표시)  
Adoption: 이 문서의 채택 자체와 (운영값) 표시 수치의 확정은 D3-R(사용자 승인)  
Adoption 절차: ① v1.0 파일은 지우지 않고 v1.1 파일을 새로 추가 ② Decision Register에 채택 기록 ③ v1.0 상태를 SUPERSEDED로 표시 ④ Main이 기존 pending D3를 25절·26A·26F 기준으로 일괄 재분류 ⑤ 한 lane에서 1–2주 시범 운영 후 문서 리뷰가 아니라 운영 결과로 조정

## 운영값 (2026-10-05 채택으로 확정, 이후 재질문 없음)

| 항목 | 값 | 조항 |
|---|---|---|
| 사이클당 최대 task | 5 | 4A |
| Lease TTL | 2시간 | 5A |
| Lease 교착 해제 요청 | TTL × 2 | 5A |
| 수리 반복 상한 | 3회 | 9A |
| Digest window당 D3-A | 10건 | 26C, 37A |
| Digest 최대 주기 | 1주 | 26C, 37A |
| 동일 module/contract D3-A 누적 (Digest window 단위) | 5건 | 26C |
| 누적 패턴 표시 범위 | 직전 3개 window | 26C, 37A |
| Veto window | 72시간 | 26C |
| Veto 중 의존 D3-A 체인 깊이 | 3 | 26C |
| 사이클당 토큰 예산 | 미설정 — 사용량 관측이 가능해지면 사용자가 설정 | 4A |

본문의 (운영값) 표기는 이 표의 값을 가리킨다. 이 표의 변경은 D3-R.

## Changelog

- v1.1: 원문 1–37절을 보존하고 0A/0B, 1A, 4A, 5A, 9A, 16A, 18A, 26A–26F, 29A, 37A, PART G를 추가·보강.
- v1.1-RC1: Lease 회수, Cross-Work, semantic numeric surface, hard/soft stop, veto boundary, 독립성, semantic_delta, evidence-based guard state 보강.
- v1.1 Final Candidate: Hard-Guard Gap/Gate, 보호 의미 중심 D3-R, 보수적 semantic_delta 합성, Digest window 단위 누적과 직전 3-window 패턴을 반영.
- v1.1 Adopted (2026-10-05): 사용자 채택 승인. 운영값 표 확정. 사이클당 토큰 예산은 미설정 유지. 무인 자율 실행은 PART G Gate A 통과 전까지 비활성.

---

## 0. 목적

이 문서는 Investment-System1의 공통 운영정책 SSoT(Single Source of Truth)다.

목표:
- 사용자가 반복적으로 "계속 진행해"라고 입력하지 않아도 프로젝트가 계속 진행되게 한다.
- 각 Work가 자신의 최신 SSoT를 기준으로 다음 실행 가능 작업을 찾아 수행한다.
- 특정 lane의 대기 때문에 전체 Work가 불필요하게 멈추지 않게 한다.
- 이미 승인된 설계 방향에 부합하는 결정을 반복 승인받는 병목을 줄인다.
- 투자방법론, 실제 자금, 보안, Holdout, Official/LIVE 등 보호영역은 유지한다.
- 예약/Watcher는 실행자가 아니라 read-only wake-up 역할만 담당한다.
- 정책 원본은 프롬프트가 아니라 GitHub SSoT에 둔다.

원칙: Prompt로 충분히 해결되는 것을 코드로 만들지 않는다.

## 0A. Loop Card [v1.1]

매 사이클 시작 시 이 카드만 먼저 적용하고, 세부는 해당 절을 필요할 때만 읽는다.

    0. Kill Switch 확인 (4A) → PAUSE/READ_ONLY면 즉시 종료
    1. STATUS 인덱스 + 변경 감지로 Fresh Read (1A)
    2. Reconcile → READY/D3-A 탐색 → Lease 획득 (5A)
    3. 우선순위대로 실행: IMPLEMENT → TEST → REPAIR(≤ 상한, 9A) → VERIFY
    4. D3-A면: 격상 트리거(26A) + semantic_delta(26F) → 독립 검증(26B) → Receipt
    5. Publish (승인된 경로, force push 금지) → SSoT/Handoff 갱신
    6. Hard stop 확인(4A) → 남으면 다음 READY / 도달 또는 soft checkpoint면 Handoff 기록 후 WAIT
    7. D3-R은 26E 형식으로 한 번만 올리고 해당 lane만 WAIT

## 0B. Enforcement 원칙 [v1.1]

- 운영 절차는 Prompt-first로 둔다.
- D3-R 보호경계는 프롬프트만으로 지키지 않는다. 에이전트가 규칙을 어겨도 기술적으로 막히도록 하드 가드를 둔다(PART G).
- 하드 가드는 "에이전트가 할 수 없음"을 목표로 한다. "에이전트가 하지 않기로 약속함"은 가드가 아니다.
- 예: 실주문 credential은 에이전트 실행 환경에 존재하지 않는다. Holdout 데이터는 에이전트 토큰으로 읽을 수 없다.

# PART A — SSoT AUTONOMOUS EXECUTION LOOP

## 1. SSoT 우선순위

각 Work는 시작·재개·후속확인 시 항상 최신 상태를 fresh-read한다.

우선순위:
1. 실제 GitHub repository 상태
2. 해당 Work의 scoped Handoff / STATE
3. Global Handoff
4. Decision Register / Approval Record
5. Evidence / Validation / CI receipts
6. Owner Contract
7. 과거 대화 / 과거 보고 / 프롬프트

과거 SHA, blocker 수, gate 수, test 수를 그대로 가정하지 않는다.
실제 immutable evidence와 최신 authoritative state가 과거 설명보다 우선한다.

## 1A. Fresh Read 비용 통제 [v1.1]

- Fresh Read는 "전부 다시 읽기"가 아니다.
  1. 한 장짜리 STATUS 인덱스를 읽는다.
  2. 관련 branch HEAD, CI conclusion, owner return 상태, D3-R 결정의 스냅샷 해시를 직전 Checkpoint와 비교한다.
  3. 해시가 바뀐 항목만 상세 조회한다.
- PR 스레드·감사 문서 전문은 해당 task에 필요할 때만 읽는다.
- 변경 감지 결과가 "변화 없음"이면 1–3절 우선순위 판단을 재사용한다.

## 2. 상태 조정(Reconcile)

서로 다른 source가 충돌하면 CURRENT / STALE / SUPERSEDED / HISTORICAL / UNVERIFIED / CONFLICTING으로 분류한다.
과거 PASS를 새 HEAD의 PASS로 재라벨링하지 않는다.
반대로 exact input/hash/scope가 동일한 유효 evidence는 이유 없이 재실행하지 않는다.

## 3. 실행 가능 작업 탐색

Fresh Read 후 각 task/lane을 다음으로 분류한다.

- READY
- WAIT_DEPENDENCY
- D3-A
- D3-R
- DONE
- SUPERSEDED
- INVALID

READY 또는 D3-A가 하나라도 있으면 Work 전체를 WAIT로 종료하지 않는다.

## 4. 기본 실행 루프

FRESH READ → RECONCILE → DISCOVER EXECUTABLE WORK → PRIORITIZE → EXECUTE → VERIFY → PUBLISH → UPDATE SSoT / HANDOFF → RE-EVALUATE → NEXT EXECUTABLE WORK → 반복

기본 동작은 CHECK → REPORT → STOP이 아니라 CHECK → EXECUTE → VERIFY → PUBLISH → RE-EVALUATE → CONTINUE다.

## 4A. 사이클 예산과 Kill Switch [v1.1]

### Hard stop
- 처리 task 수: 5개 (운영값)
- 경과 시간: 실행 플랫폼이 시간 예산을 명시적으로 제공하고 관측 가능할 때만 그 한도를 따른다.
- 토큰 예산: 사용자가 상한을 정했고 사용량을 관측할 수 있을 때만 적용.
- Kill Switch.

### Soft checkpoint
- 컨텍스트 압박이 높다고 판단될 때.
- 반복 오류, 지시 누락 등 품질 저하 신호가 보일 때.
- 멈출 때 남은 작업과 재개 지점을 Handoff에 기록한다. 고정 컨텍스트 비율은 정책값으로 두지 않는다.

### Kill Switch
- 저장소 변수 또는 지정 파일 AUTONOMY_MODE = RUN | PAUSE | READ_ONLY.
- 사이클 시작과 각 Publish 직전에 확인한다.
- PAUSE: 즉시 Checkpoint 후 종료. READ_ONLY: 조회·보고만, 쓰기 금지.
- Kill Switch 변경은 사용자만 한다. 에이전트는 수정하지 않는다.

## 5. Multi-Lane Continuation

하나의 lane이 막혔다고 전체 Work를 멈추지 않는다.
원칙: ONE BLOCKED LANE ≠ WORK BLOCKED.
전체 WAIT는 모든 승인된 lane이 DONE / WAIT_DEPENDENCY / D3-R 중 하나일 때만 허용한다.

## 5A. Lease와 동시성 [v1.1]

- 한 lane에는 동시에 하나의 writer만 둔다.
- Lease 형식: lane ID, holder(Work/세션), 획득 시각, TTL, 대상 branch.
- TTL: 2시간 (운영값).
- 각 Work는 자기 branch에만 쓴다. canonical은 PR + 필수 CI 체크 통과로만 바뀐다.
- 두 Work가 같은 파일을 바꿔야 하면 Main이 owner를 정하고, 나머지는 WAIT_DEPENDENCY.

### Stale Lease 회수
TTL 만료는 회수 권한이 아니다. 다음을 모두 만족할 때만 회수한다.
1. TTL 만료
2. holder의 활성 실행이 없음을 확인
3. pending mutation / CI publication이 없음을 확인
4. remote HEAD와 STATE를 다시 읽어 확인
5. stale-lease recovery receipt 기록
6. compare-and-swap(non-force)으로만 새 Lease 획득. 경합에서 지면 WAIT

하나라도 확인할 수 없으면 회수하지 않고 WAIT_DEPENDENCY.

### 교착 탈출
- TTL의 2배 (운영값) 동안 확인하지 못하면 26E 형식으로 사용자에게 Lease 해제 결정을 요청한다(D3-R).
- 사용자가 승인하면 recovery receipt에 승인 기록을 남기고 6번 절차로 획득한다.

## 6. 우선순위

READY 작업이 여러 개면:
1. shared blocker
2. Critical Path blocker
3. Security / Integrity blocker
4. Owner-return closure
5. Integration blocker
6. Acceptance Criteria closure
7. Bounded implementation
8. Documentation / Cleanup

목표는 활동량이 아니라 blocker closure다.

## 7. 실제 실행

READY 작업은 실제 수행한다.
가능하면 IMPLEMENT → TEST → REPAIR → RETEST → VERIFY → PUBLISH까지 한 실행에서 진행한다.
실행 가능한 작업을 단순히 "다음 단계"라고만 보고하고 종료하지 않는다.

## 8. 위험 비례 검증

Mandatory Hard Gate → Schema / Static Check → Targeted Deterministic Test → Relevant Negative Test → Affected Regression → Full Regression when required → Single Independent Verifier → Multi-Agent Verification when justified.

모든 단계를 항상 실행하지 않는다.
기존 evidence가 정확히 재사용 가능하면 재사용한다.

## 9. 실패 처리

FAIL → CLASSIFY → RETRY / REPAIR / REPLAN / WAIT_DEPENDENCY / D3-R → RETEST → VERIFY → CONTINUE.

최초 실패와 수정 이력을 보존한다.

## 9A. 수리 라운드 상한 [v1.1]

- 같은 실패에 대한 REPAIR → RETEST 반복은 3라운드 (운영값)까지.
- 상한 도달 시 자동 REPLAN. REPLAN 후에도 실패하면 lane을 BLOCKED로 두고 원인 분류를 기록.
- 독립 검증자가 같은 결함 계열을 2회 이상 지적하면 구현자 교체 또는 설계 재검토를 우선.
- 모든 라운드의 실패 내용과 수정은 보존.

## 10. Publish

검증된 결과는 승인된 write path로 게시한다.

최소 추적:
- exact branch
- exact HEAD
- changed scope
- tests/evidence
- failure history
- remaining blockers
- owner/dependency impact

Git transport 실패를 곧바로 GitHub write 불가로 해석하지 않는다.
승인된 GitHub API write path가 있으면 사용한다.
Force push / history rewrite 금지.

## 11. SSoT Update

실제 상태 변화가 발생하면 scoped Handoff / STATE / Evidence를 history-preserving 방식으로 갱신한다.
예: OPEN → IN_PROGRESS → VERIFIED → CLOSED 또는 OPEN → BLOCKED → OWNER_ACTION_PENDING.

## 12. Re-Evaluate

Publish 후 반드시 재평가한다.
"이번 결과 때문에 새롭게 실행 가능해진 작업이 있는가?"
YES → 즉시 다음 task 실행.
NO → 다른 lane 검사.
모든 lane 고갈 → WAIT / D3-R / DONE 판단.

## 13. Owner Return Loop

SENT → ACKNOWLEDGED → IN_PROGRESS → RETURNED → INDEPENDENTLY_VERIFIED → CONSUMED → CLOSED.

RETURNED 결과는 exact HEAD, scope, tests/evidence, 필요 시 bounded independent verification, integration consumption, blocker 재평가까지 수행한다.

## 14. CI Loop

CI RUNNING이면 해당 lane은 WAIT_DEPENDENCY일 수 있다. 다른 READY lane은 계속 진행한다.
SUCCESS → artifact/evidence consume → 다음 단계.
FAILURE → classify → D1/D2/D3-A이면 repair → retest.
CANCELLED/INFRA FAILURE → 적절한 retry 판단.

## 15. WAIT 조건

전체 WAIT는 다음이 모두 0일 때만 허용한다.
1. READY D1/D2 task
2. 독립 READY lane
3. bounded repair task
4. 즉시 소비 가능한 owner return
5. terminal CI result
6. SSoT update / closure task

WAIT 기록에는 dependency, owner/CI/decision, exact reference, Material Change resume trigger, 다음 자동 action을 포함한다.

## 16. STOP 조건

STOP은 다음 중 하나일 때만:
A. Acceptance Criteria 전체 완료
B. 실제 D3-R에서 사용자 결정 필요
C. 모든 D1/D2/D3-A lane이 WAIT_DEPENDENCY
D. 실제 tool/system blocker로 진행 불가

Subtask 하나 완료는 STOP 사유가 아니다.

## 16A. STOP 조건 보강 [v1.1]

16절에 추가:
- E. 4A 사이클 예산 소진 → Checkpoint 후 종료, 다음 wake-up에서 재개.
- F. Kill Switch가 PAUSE 또는 READ_ONLY.
- G. 레이트리밋·권한 오류 등 외부 제약이 연속 발생 → 원인과 재시도 시점을 기록하고 WAIT.

E–G는 READY가 남아 있어도 STOP 금지 원칙의 예외이며, 반드시 재개 지점을 남긴다.

## 17. No Busy Loop

자동진행은 무한 polling이 아니다.
변화 없는 CI/owner 상태를 반복 조회하지 않는다.
현재 실행 가능한 일을 소진하면 WAIT로 전환한다.

## 18. No Duplicate Work

이미 VERIFIED / CLOSED / FROZEN / HANDOFF_READY인 작업은 invalidation evidence 없이는 재실행하지 않는다.
Owner가 있는 task를 Main이 복제하지 않는다.

## 18A. 재분류 가드 [v1.1]

- blocker·task를 INVALID / SUPERSEDED / DONE으로 바꾸는 것도 결정이며 evidence reference를 남긴다.
- Critical Path 또는 Security/Integrity blocker를 닫는 재분류는 독립 검증자의 확인이 필요하다.
- 진행률을 올리기 위한 재분류는 금지한다. 재분류 건수는 Checkpoint에 별도 집계한다.

# PART B — DECISION AUTHORITY

## 19. 승인 등급

### D1
자율 실행.

### D2
보수적 검증 후 자율 실행.

### D3-A — Design-Aligned Delegated Approval
기존 승인된 설계 방향과 정합하면 자동승인.

### D3-R — Reserved
사용자 승인 유지.

## 20. D3-A 정의

다음 조건을 모두 만족해야 한다.
1. 기존 승인된 목적과 설계 방향 유지
2. 새로운 투자방법론/경제적 의미 생성 없음
3. 점수/순위/factor 의미 실질 변경 없음
4. PIT/no-lookahead/provenance/Frozen/history 보호 유지
5. 보안/Tenant/금융계정 권한 확대 없음
6. 실제 매매/주문/자금이동 없음
7. evidence/history 삭제·rewrite 없음
8. 합리적 rollback 가능
9. deterministic 또는 독립 검증 가능
10. 복수 대안이면 기존 SSoT와 가장 정합적이고 보수적인 선택
11. Decision Receipt 기록 가능

하나라도 충족하지 않으면 D3-R.

## 21. D3-A 처리 흐름

CLASSIFY → AUTO-APPROVE → EXECUTE → VERIFY → DECISION RECEIPT → UPDATE SSoT → RE-EVALUATE → CONTINUE.

사용자에게 다시 승인 여부를 묻지 않는다.

## 22. D3-A Decision Receipt

최소 기록:
- Decision ID
- 결정
- 기존 SSoT / Decision Register 근거
- 대안
- 설계 정합성 근거
- 보호경계 보존 여부
- 검증 방법/결과
- rollback 가능 여부
- affected scope
- exact HEAD / evidence reference
- semantic_delta 및 근거 evidence

## 23. D3-R 정의

사용자 승인 유지:
- 유료 결제
- 새로운 유료 API / 유료 인프라 / 유료 connector
- 실제 매매 / 주문 / 자금이동
- 실제 금융기관 credential 사용 또는 권한 확대
- Holdout 최초 소비 또는 재소비
- Official / LIVE 승격
- PIT / no-lookahead 완화
- Frozen / history / evidence의 파괴적 변경
- 보안 / Tenant isolation 완화
- irreversible delete / migration
- 실제 production deployment / public exposure
- QGV / 13F / Backtest / 투자판단 결과 의미를 바꾸는 새 방법론
- 새로운 numeric threshold / default / cutoff / weight
- factor / scoring / composite 의미 변경
- 기존 SSoT만으로 설계 정합성을 입증할 수 없는 결정
- 보호된 owner contract의 실질 변경

## 24. D3-R과 병렬 진행

D3-R이 하나의 lane에서 발생해도 Work 전체를 멈추지 않는다.
해당 dependent lane만 WAIT.
독립 D1/D2/D3-A는 계속 진행한다.

## 25. 기존 pending D3 재분류

기존 pending D3도 fresh SSoT 기준으로 재분류한다.
- 기존 설계의 단순 구체화 → D3-A 후보
- 새 방법론 / 새 numeric meaning / 보호경계 변경 → D3-R

## 26. D3-A 판정 원칙

"합리적으로 보인다"만으로 자동승인하지 않는다.
기존 SSoT / Decision Register / Approved Architecture와의 구체적 정합성을 evidence로 보여야 한다.
불확실하면 D3-R.

## 26A. D3-A 자동 격상 트리거 [v1.1]

### 즉시 D3-R
- 보호영역(Holdout, PIT/no-lookahead, provenance, Frozen, credential, tenant, LIVE/Official)의 semantics, enforcement, accessibility, authority 또는 stored evidence를 변경함.
- delete, irreversible migration, force push / history rewrite 포함.
- 기존 SSoT 조항을 인용하지 못함.
- semantic_delta가 UNCLEAR 또는 D3-R 값.

### 보호 경로 변경
- 위 보호영역의 경로·파일을 건드리면 26B 독립 검증이 필수.
- 검증자가 보호 의미 변경 없음을 확인하지 못하면 semantic_delta = UNCLEAR → D3-R.

### Semantic 숫자 변경
| 단계 | 대상 | 처리 |
|---|---|---|
| 1. 보호 | scoring, factor, normalization, threshold, cutoff, ranking, portfolio weight, backtest window, PIT timing, calibration, methodology config | D3-R |
| 2. 제외 | presentation/layout, test-only, fixture, pagination, timeout 등 명시적 비의미 경로 | 통상 검증 등급 유지 |
| 3. 미분류 | 1·2 어디에도 없는 숫자 변경 | 경고 후 독립 검증자가 1 또는 2로 판정; 판정 불가면 D3-R |

- 보호·제외 목록은 별도 registry 파일로 관리.
- 보호 대상 추가는 D2.
- 보호 대상 제거 또는 제외 목록 추가는 D3-R.

### Cross-Work 변경

    Cross-Work
    → Main coordination 필수 (Main이 제안자이면 다른 Work owner가 조정)
    → semantic_delta 허용값 + rollback 가능(26D) + 독립 검증 PASS(26B)
        → D3-A
    → 그 외
        → D3-R

## 26B. D3-A 독립 검증 [v1.1]

- 최소 독립 조건: D3-A 제안 실행과 컨텍스트·추론 과정을 공유하지 않는 별도 verification execution이 같은 결정을 처음부터 다시 판정.
- 권장: 다른 모델 계열 또는 다른 에이전트. 모델 이름 차이만으로 독립성이 보장되지는 않는다.
- 검증 항목:
  1. 인용한 SSoT 조항이 결정을 실제 지지하는가
  2. 26A 트리거 누락이 없는가
  3. semantic_delta 라벨이 맞는가
- 결과 PASS / ESCALATE. ESCALATE면 D3-R로 전환하고 이미 실행한 변경은 rollback 가능한 상태로 둔다.

## 26C. 누적 드리프트 통제 [v1.1]

- Digest window: 첫 D3-A부터 Digest 발행까지. D3-A 10건(운영값) 또는 1주(운영값) 중 먼저 도달한 시점에 Digest 발행 후 새 window 시작.
- 같은 module/contract에서 동일 Digest window 안의 D3-A가 5건(운영값) 누적되면 그 window의 이후 해당 module/contract 결정은 D3-R.
- 새 window에서는 0부터 다시 센다. 직전 3개 window(운영값)의 module/contract별 누적 패턴을 Digest에 표시.
- 사용자는 Digest 이후 72시간(운영값) 안에 D3-A를 veto 가능.
- Veto된 D3-A는 rollback하고 의존 후속 D3-A도 재검토.

### Veto 기간 중 진행 경계

허용:
- D3-A 결과를 owner/scoped branch에서 즉시 사용.
- 의존 D1 / D2 / D3-A 계속 진행.

금지:
- canonical로의 되돌리기 어려운 promotion.
- Official / LIVE 승격.
- irreversible migration.

Veto 기간 중 의존 D3-A 체인 깊이는 3단계(운영값)로 제한한다.

## 26D. Rollback 정의 [v1.1]

합리적 rollback 가능은 다음을 모두 뜻한다.
- 단일 revert commit 또는 revert PR로 이전 상태 복원.
- 데이터·evidence·history 손실 없음.
- 외부 시스템에 남는 부작용 없음.

하나라도 아니면 D3-R.

## 26E. D3-R 요청 형식 [v1.1]

한 번만 올린다.
- 결정 질문 한 문장
- 선택지 2–3개와 영향·rollback 여부
- 권장안과 근거 SSoT 조항
- 결정 전 WAIT lane과 계속 진행 lane
- 결정 기한이 있으면 이유

같은 D3-R을 상태 변화 없이 반복해서 묻지 않는다.

## 26F. semantic_delta [v1.1]

모든 D3-A Decision Receipt에 semantic_delta와 근거 evidence를 추가한다.

D3-A 허용:
- NONE
- REPRESENTATION_ONLY
- IMPLEMENTATION_ONLY
- BEHAVIOR_PRESERVING — 기존 테스트 또는 golden case 일치 evidence가 있을 때만

즉시 D3-R:
- ECONOMIC_SEMANTIC_CHANGE
- SCORING_SEMANTIC_CHANGE
- SECURITY_BOUNDARY_CHANGE
- PIT_SEMANTIC_CHANGE
- IRREVERSIBLE_STATE_CHANGE
- UNCLEAR

제안자와 독립 검증자가 각각 판정한다.
보수성 순서:
NONE < REPRESENTATION_ONLY < IMPLEMENTATION_ONLY < BEHAVIOR_PRESERVING < (UNCLEAR 또는 D3-R 값).

두 판정을 보수적으로 합성한 최종 라벨이 D3-A 허용값이면 D3-A가 성립한다.
둘 중 하나라도 UNCLEAR 또는 D3-R 값이면 D3-R.

# PART C — WATCHER / AUTOMATION BOUNDARY

## 27. 예약은 Executor가 아니다

예약 / 후속 확인 / Watcher는 read-only wake-up 역할만 한다.

Watcher 금지:
- lease 획득/갱신/해제
- STATE mutation
- Handoff mutation
- commit
- ref update
- CI dispatch
- owner routing
- integration publication
- canonical mutation

Watcher 실패가 Work ownership/state에 영향을 주어서는 안 된다.

## 28. Watcher 역할

Material Change 예:
- CI RUNNING → terminal
- owner RETURNED
- verified evidence 도착
- relevant exact HEAD 변경
- blocker closure / new blocker
- D3-R decision 승인
- integration candidate 생성
- tool/system blocker 해소

Material Change가 없으면 조용히 종료한다.
Work가 이미 실행 중이거나 active writer/lease가 있으면 즉시 종료한다.

## 29. Wake-Up

Material Change가 있고 Work가 idle일 때만 "최신 SSoT를 fresh-read하고 기존 execution loop를 재개하라"는 짧은 wake-up 신호를 보낸다.
실제 실행은 Work의 SSoT Autonomous Execution Loop가 담당한다.

## 29A. Watcher 구현 경계와 Wake 채널 [v1.1]

- 이벤트 기반 우선. 고정 주기 polling은 이벤트가 없는 신호에만 사용.
- Watcher 토큰은 읽기 전용 권한만 가진다.
- 유일한 쓰기는 Wake 채널 신호.
- Wake 채널은 SSoT가 아니다.
- 신호는 Material Change 종류, exact reference, 변경 감지 해시만 담는다.
- 같은 해시는 다시 보내지 않는다.
- Kill Switch가 PAUSE면 Watcher도 신호를 보내지 않는다.

# PART D — WORK-SPECIFIC APPLICATION

## 30. Main Work

SSoT: GitHub repository, Global Handoff, Integration receipts, Owner returns, Canonical state.
목표: blocker closure, owner routing, integration convergence, canonical candidate preparation.
Main은 모든 subsystem을 직접 구현하지 않는다.

## 31. Chart Work

SSoT: GitHub, Chart scoped Handoff, Chart contract, Gate/Evidence matrix, relevant owner returns.
목표: Chart blocker closure, Chart contract, renderer/validation, production vertical slice convergence.

## 32. Product Platform Work

SSoT: GitHub, Platform scoped Handoff, Auth/Tenant/Financial contracts, owner source, security/reconciliation evidence.
목표: Auth, Tenant isolation, FinancialConnector, Account/Position/Transaction, Sync/Idempotency, Reconciliation, Audit, Product API, Web/PWA integration.
Read-only Hard Gate 유지.

## 33. QGV Work

SSoT: GitHub, QGV scoped Handoff, QGV Common Contract, Decision Register, validation/golden evidence.
목표: Q/G/V semantic convergence, Missing Data, V, aggregation, configuration, validation readiness.
새 방법론과 새 numeric policy는 D3-R.

# PART E — COMPLETION

## 34. Work 완료 조건

필수:
- Acceptance Criteria 충족
- unresolved D1 = 0
- unresolved D2 = 0
- unresolved D3-A = 0
- unresolved internal blocker = 0
- 필요한 owner return 소비 완료
- 필요한 CI/evidence 소비 완료
- SSoT / Handoff 최신화 완료

D3-R 또는 외부 dependency만 남으면 WAIT이지 DONE이 아니다.

## 35. 프로젝트 전체 완료 조건

Investment-System1 전체 DONE은 각 Work 완료 외에도 다음을 요구한다.
- Integration acceptance
- 필요한 real-data validation
- Calibration / Verification
- Holdout
- Official / LIVE gate
- 최종 security / provenance / PIT 보존
- Product integration acceptance

# PART F — REPORTING

## 36. 진행률 지표

Agent 수, commit 수, test rerun 수를 progress로 보지 않는다.

우선 지표:
- Blockers Closed
- Gates Closed
- Owner Returns Consumed
- Integration Dependencies Reduced
- Acceptance Criteria Closed
- D1/D2/D3-A Remaining
- D3-R Remaining
- Production Candidate Readiness

## 37. Checkpoint Report

WAIT / D3-R / DONE에서 보고한다.
- exact SSoT state
- closed blockers
- actual implementation / verification
- owner returns consumed
- remaining READY
- WAIT dependencies
- D3-R
- resume triggers
- next automatic action

READY가 남아 있으면 보고를 최종 종료점으로 쓰지 않는다.

## 37A. D3-A Digest [v1.1]

Digest window 종료마다 사용자에게 보낸다.
- D3-A 목록: Decision ID, 요약, 근거 조항, 독립 검증 결과, revert 방법
- semantic_delta 값별 건수와 제안자·검증자 라벨 불일치
- 같은 module/contract 집중 경고와 직전 3개 window 패턴
- 재분류 집계, 수리 상한 도달
- Hard stop·soft checkpoint 건수, stale-lease 회수·해제 요청
- Veto 마감 시각

Digest는 사후 확인용이며 사용자가 응답하지 않으면 D3-A는 유지된다.

# PART G — ENFORCEMENT MATRIX [v1.1]

D3-R 보호영역별 하드 가드. 상태는 evidence 기반으로만 표기한다.

| 상태 | 조건 |
|---|---|
| VERIFIED | 저장소 경로 + 동작 테스트 evidence + exact HEAD가 있음 |
| PARTIAL_VERIFIED | 일부 경로·경우만 위 evidence가 있음 |
| NOT_VERIFIED | 구현됐다는 주장은 있으나 evidence 없음 |
| NOT_IMPLEMENTED | 구현이 없음을 확인 |

초기값은 모두 NOT_VERIFIED이며 각 Work가 evidence와 함께 갱신한다.

## G1. Hard-Guard Gap과 Gate 단계

NOT_VERIFIED / NOT_IMPLEMENTED는 곧바로 blocker가 아니라 Hard-Guard Gap이다.

| Gate | 언제 blocking인가 | 해당 가드 |
|---|---|---|
| A. 자율 실행 활성화 | 사용자 부재 무인 자율 실행(AUTONOMY_MODE=RUN + Watcher wake-up) 전 | 루프 자신의 행동을 막는 가드 |
| P. Production candidate | 해당 보호영역을 실제 사용하는 작업이 production candidate에 진입할 때 | 실자산·실데이터·외부 노출 가드 |
| 즉시 blocker | G2 조건 중 하나라도 확인된 순간 | 단계와 무관 |

- Gate A 전에도 사용자가 지켜보는 세션 실행은 이 문서대로 진행.
- Gate A 통과: A 항목이 모두 VERIFIED, 또는 PARTIAL_VERIFIED이면서 빠진 범위가 무인 실행과 무관함을 명시.
- Gap 자체는 다른 lane의 진행을 막지 않는다.
- 무인 자율 실행은 Gate A 통과 전까지 비활성.

## G2. 즉시 blocker 조건

사실로 확인되면 즉시 blocker:
- 주문 가능한 credential/API 키가 에이전트 환경에서 읽힘
- 금융기관 credential이 에이전트 토큰으로 읽힘
- Holdout 데이터가 에이전트 토큰으로 접근 가능
- 실사용자 또는 다른 tenant 데이터가 에이전트 환경에서 접근 가능
- 결제 수단·유료 API 키가 에이전트 환경에 있음
- 무인 자율 실행 중 canonical force push 또는 branch 삭제 가능

evidence와 함께 Security/Integrity blocker로 등록하고 관련 lane을 WAIT.

## G3. 가드 목록

| 보호영역 | 하드 가드 | Gate | 상태 |
|---|---|---|---|
| Frozen·history·evidence 파괴 | 동결 경로 차단 훅, 브랜치 보호, force push 금지 설정 | A | NOT_VERIFIED |
| canonical 변경 | PR + 필수 체크 + CODEOWNERS 승인 | A | NOT_VERIFIED |
| 폭주·비용 | Kill Switch, hard stop(4A) | A | NOT_VERIFIED |
| 실제 매매·주문·자금이동 | 주문 credential을 에이전트 환경에 두지 않음, 주문 모듈 별도 권한 | P | NOT_VERIFIED |
| 금융기관 credential·권한 확대 | secret은 에이전트 토큰으로 읽기 불가, .env 읽기·쓰기 차단 훅 | P | NOT_VERIFIED |
| Holdout 소비 | Holdout 데이터 별도 저장소·권한, 접근 로그 | P | NOT_VERIFIED |
| Official/LIVE 승격, 배포 | 배포 workflow 사용자 승인(environment protection) 필수 | P | NOT_VERIFIED |
| PIT/no-lookahead 완화 | 관련 테스트를 필수 CI 체크로 지정 | P | NOT_VERIFIED |
| 보안·Tenant isolation | fail-closed 음성 테스트를 필수 CI 체크로 지정 | P | NOT_VERIFIED |
| 새 수치 기준·방법론 | 보호 semantic 경로·필드 숫자 변경 탐지 registry; 그 전까지 26A·26B 절차 | P | NOT_VERIFIED |
| 유료 결제·유료 API | 결제 수단·유료 API 키를 에이전트 환경에 두지 않음 | P | NOT_VERIFIED |

P 가드라도 G2 조건이 발견되면 즉시 blocker다.

# FINAL PRINCIPLES

- SSoT가 프롬프트보다 우선한다.
- Fresh Read 후 실행 가능 작업을 찾아 실제로 수행한다.
- 한 lane의 blocker가 전체 Work를 멈추지 않는다.
- D1/D2/D3-A는 사용자 재승인 없이 진행한다.
- D3-R만 사용자에게 올린다.
- 예약은 read-only watcher다.
- 기존 evidence는 재사용하고 중복 검증을 피한다.
- 보호경계는 속도를 위해 완화하지 않는다.
- 자동화는 프로젝트를 빠르게 해야 하며 새로운 병목이 되어서는 안 된다.
- 목표는 SSoT → Execute → Verify → Publish → Re-evaluate → Continue다.
- [v1.1] 보호경계는 프롬프트가 아니라 하드 가드로 지킨다.
- [v1.1] D3-A는 다른 검증자가 확인하고 누적은 Digest와 Veto로 사람이 사후 통제한다.
- [v1.1] 루프는 예산 안에서 돌고 멈출 때는 재개 지점을 남긴다.
- [v1.1] TTL 만료는 회수 권한이 아니다.
- [v1.1] D3-A는 제안자와 독립 검증자의 판정을 보수적으로 합성한 semantic_delta가 허용값일 때만 성립한다. 하나라도 UNCLEAR 또는 D3-R 값이면 D3-R.
- [v1.1] 하드 가드 상태는 evidence가 있을 때만 올린다. 미검증 가드는 Gap이며 해당 Gate에 도달할 때만 진행을 막는다.
- [v1.1] Kill Switch는 언제나 사용자에게 있다.
