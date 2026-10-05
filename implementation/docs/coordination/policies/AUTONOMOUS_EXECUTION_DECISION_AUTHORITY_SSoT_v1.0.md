# Investment-System1 — Autonomous Execution & Decision Authority SSoT v1.0

> **SUPERSEDED** (2026-10-05) by `Investment-System1_Autonomous_Execution_Decision_Authority_SSoT_v1_1.md` — CDR-024.
> 이 문서는 이력 보존용이며 운영 기준이 아니다. 본문 1–37절은 v1.1에 그대로 포함되어 있다.

Status: PROPOSED COMMON SSoT  
Purpose: Investment-System1 공통 자율실행·승인권한 정책  
Scope: Main / Chart / QGV / Product Platform 및 향후 동일 체계를 사용하는 Work  
Principle: Prompt-first, SSoT-driven, history-preserving, fail-closed

---

## 0. 목적

이 문서는 Investment-System1의 공통 운영정책 SSoT(Single Source of Truth)다.

목표:
- 사용자가 반복적으로 `계속 진행해`라고 입력하지 않아도 프로젝트가 계속 진행되게 한다.
- 각 Work가 자신의 최신 SSoT를 기준으로 다음 실행 가능 작업을 찾아 수행한다.
- 특정 lane의 대기 때문에 전체 Work가 불필요하게 멈추지 않게 한다.
- 이미 승인된 설계 방향에 부합하는 결정을 반복 승인받는 병목을 줄인다.
- 투자방법론, 실제 자금, 보안, Holdout, Official/LIVE 등 보호영역은 유지한다.
- 예약/Watcher는 실행자가 아니라 read-only wake-up 역할만 담당한다.
- 정책 원본은 프롬프트가 아니라 GitHub SSoT에 둔다.

원칙: `Prompt로 충분히 해결되는 것을 코드로 만들지 않는다.`

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
FRESH READ
→ RECONCILE
→ DISCOVER EXECUTABLE WORK
→ PRIORITIZE
→ EXECUTE
→ VERIFY
→ PUBLISH
→ UPDATE SSoT / HANDOFF
→ RE-EVALUATE
→ NEXT EXECUTABLE WORK
→ 반복

기본 동작은 `CHECK → REPORT → STOP`이 아니라 `CHECK → EXECUTE → VERIFY → PUBLISH → RE-EVALUATE → CONTINUE`다.

## 5. Multi-Lane Continuation
하나의 lane이 막혔다고 전체 Work를 멈추지 않는다.

원칙: `ONE BLOCKED LANE ≠ WORK BLOCKED`

전체 WAIT는 모든 승인된 lane이 DONE / WAIT_DEPENDENCY / D3-R 중 하나일 때만 허용한다.

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

가능하면 한 실행 안에서:
IMPLEMENT → TEST → REPAIR → RETEST → VERIFY → PUBLISH

현재 권한과 도구로 실행 가능한 작업을 단순히 “다음 단계”라고만 보고하고 종료하지 않는다.

## 8. 위험 비례 검증
Mandatory Hard Gate
→ Schema / Static Check
→ Targeted Deterministic Test
→ Relevant Negative Test
→ Affected Regression
→ Full Regression when required
→ Single Independent Verifier
→ Multi-Agent Verification when justified

모든 단계를 항상 실행하지 않는다.
기존 evidence가 정확히 재사용 가능하면 재사용한다.

## 9. 실패 처리
FAIL
→ CLASSIFY
→ RETRY / REPAIR / REPLAN / WAIT_DEPENDENCY / D3-R
→ RETEST
→ VERIFY
→ CONTINUE

최초 실패와 수정 이력을 보존한다.

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

예:
OPEN → IN_PROGRESS → VERIFIED → CLOSED
또는
OPEN → BLOCKED → OWNER_ACTION_PENDING

## 12. Re-Evaluate
Publish 후 반드시 재평가한다.

`이번 결과 때문에 새롭게 실행 가능해진 작업이 있는가?`

YES → 즉시 다음 task 실행
NO → 다른 lane 검사
모든 lane 고갈 → WAIT / D3-R / DONE 판단

## 13. Owner Return Loop
SENT → ACKNOWLEDGED → IN_PROGRESS → RETURNED → INDEPENDENTLY_VERIFIED → CONSUMED → CLOSED

RETURNED 결과는 exact HEAD, scope, tests/evidence, 필요 시 bounded independent verification, integration consumption, blocker 재평가까지 수행한다.

## 14. CI Loop
CI RUNNING이면 해당 lane은 WAIT_DEPENDENCY일 수 있다.
다른 READY lane은 계속 진행한다.

SUCCESS → artifact/evidence consume → 다음 단계
FAILURE → classify → D1/D2/D3-A이면 repair → retest
CANCELLED/INFRA FAILURE → 적절한 retry 판단

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

## 17. No Busy Loop
자동진행은 무한 polling이 아니다.
변화 없는 CI/owner 상태를 반복 조회하지 않는다.
현재 실행 가능한 일을 소진하면 WAIT로 전환한다.

## 18. No Duplicate Work
이미 VERIFIED / CLOSED / FROZEN / HANDOFF_READY인 작업은 invalidation evidence 없이는 재실행하지 않는다.
Owner가 있는 task를 Main이 복제하지 않는다.

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
CLASSIFY
→ AUTO-APPROVE
→ EXECUTE
→ VERIFY
→ DECISION RECEIPT
→ UPDATE SSoT
→ RE-EVALUATE
→ CONTINUE

사용자에게 다시 `승인할까요?`라고 묻지 않는다.

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

## 23. D3-R 정의
다음은 사용자 승인 유지:
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
`합리적으로 보인다`만으로 자동승인하지 않는다.
반드시 기존 SSoT / Decision Register / Approved Architecture와의 구체적 정합성을 evidence로 보여야 한다.
불확실하면 D3-R.

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
Material Change가 있고 Work가 idle일 때만:
`최신 SSoT를 fresh-read하고 기존 execution loop를 재개하라`
라는 짧은 wake-up 신호를 보낸다.

실제 실행은 Work의 SSoT Autonomous Execution Loop가 담당한다.

# PART D — WORK-SPECIFIC APPLICATION

## 30. Main Work
SSoT:
- GitHub repository
- Global Handoff
- Integration receipts
- Owner returns
- Canonical state

목표:
- blocker closure
- owner routing
- integration convergence
- canonical candidate preparation

Main은 모든 subsystem을 직접 구현하지 않는다.

## 31. Chart Work
SSoT:
- GitHub
- Chart scoped Handoff
- Chart contract
- Gate / Evidence matrix
- relevant owner returns

목표:
- Chart blocker closure
- Chart contract
- renderer / validation
- production vertical slice convergence

## 32. Product Platform Work
SSoT:
- GitHub
- Platform scoped Handoff
- Auth / Tenant / Financial contracts
- owner source
- security / reconciliation evidence

목표:
- Auth
- Tenant isolation
- FinancialConnector
- Account / Position / Transaction
- Sync / Idempotency
- Reconciliation
- Audit
- Product API
- Web/PWA integration

Read-only Hard Gate 유지.

## 33. QGV Work
SSoT:
- GitHub
- QGV scoped Handoff
- QGV Common Contract
- Decision Register
- validation / golden evidence

목표:
- Q/G/V semantic convergence
- Missing Data
- V
- aggregation
- configuration
- validation readiness

새 방법론과 새 numeric policy는 D3-R.

# PART E — COMPLETION

## 34. Work 완료 조건
Work DONE은 단순히 현재 할 일이 없는 상태가 아니다.

필수:
- Acceptance Criteria 충족
- unresolved D1 = 0
- unresolved D2 = 0
- unresolved D3-A = 0
- unresolved internal blocker = 0
- 필요한 owner return 소비 완료
- 필요한 CI/evidence 소비 완료
- SSoT / Handoff 최신화 완료

D3-R 또는 외부 dependency만 남는 경우는 WAIT이지 DONE이 아니다.

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
실제 WAIT / D3-R / DONE에 도달했을 때 보고한다.

포함:
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
- 목표는 `SSoT → Execute → Verify → Publish → Re-evaluate → Continue`다.
