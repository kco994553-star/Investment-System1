# Investment-System1 · COORDINATION_DECISION_REGISTER

Append-only register of user decisions about **coordination and routing**: the operating contract, integration order, and worker routing. Single writer: the Primary Integration Writer.

This register is not a methodology or policy authority. Capability policy decisions (Track C, QGV, Technical, Macro, P01, …) stay in their scoped Decision Registers. When a decision here touches a capability (for example CDR-003), the scoped register of that capability remains the authority, and this entry only records routing.

Rules: never edit or delete an entry. A later decision that changes an earlier one is a new entry naming the entry it supersedes. User wording is quoted verbatim.

---

## CDR-001 · Worker Contract SSoT selection

| Field | Value |
|---|---|
| Status | **USER_DECIDED** |
| Decided at | 2026-10-03 (user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after GCH-001) |
| Scope | coordination routing only. **Not** canonical-merge approval |

User wording (verbatim):

> Worker Contract SSoT는 PR #21로 결정한다. PR #20은 superseded duplicate로 처리하되 merge하지 않는다. #20의 history는 삭제하거나 rewrite하지 말고, #21이 canonical에 통합되기 전까지 #21 exact HEAD의 contract를 operational routing SSoT로 사용한다. canonical merge는 아직 수행하지 않는다.

> PR #21을 repository-wide Claude Code Worker Contract의 단일 SSoT 후보로 선택한다. PR #20은 superseded duplicate로 분류하되 삭제·rewrite하지 않고 merge하지 않는다. #21의 PIT/no-lookahead 문구를 유지하며 #20 §J의 추가 예외 문구를 채택하지 않는다. 이 결정은 #21의 canonical merge 승인이 아니다.

Effect:

- The operational routing SSoT is the contract blob at PR #21's exact HEAD: `ccr-2e16018a-qukwmg` @ `f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798`, path `implementation/docs/coordination/CLAUDE_CODE_WORKER_CONTRACT.md`, git blob `617ef6d485db85cbe4d22376d06c472902ed10e8`. Read it with:
  `git show f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798:implementation/docs/coordination/CLAUDE_CODE_WORKER_CONTRACT.md`
- If PR #21's HEAD changes, the new HEAD becomes operational only under the contract's own §R change control (reason, approval basis, effective_from), and the new SHA is recorded here.
- PR #20 (`integration/claude-worker-contract-v1` @ `d87d4cd14c7e31d0d0fc17a447ee37346102e0ff`) is **SUPERSEDED_DUPLICATE**:
  - not merged;
  - branch and commits retained (no delete, no rewrite);
  - its §J exception wording ("unless an approved contract explicitly permits it") is **not adopted**.
- Canonical merge of #21: **not approved**. CANONICAL_STATE stays NOT_MERGED until a separate user decision.

## CDR-002 · Track C ↔ Producer integration order deferred; compatibility audit first

| Field | Value |
|---|---|
| Status | **USER_DECIDED (defer + audit)** |
| Decided at | 2026-10-03, same message |
| Scope | integration routing for finding IF-1 (GIE-001) |

User wording (verbatim):

> Track C와 Producer의 merge order는 아직 결정하지 않는다. 먼저 두 선택지 사이에 결과 불변의 compatibility solution이 가능한지 감사하라. Track C 2137883의 4개 cross-track additive 변경 각각에 대해: 왜 Track C가 그 필드를 필요로 하는지 / core snapshot schema에 반드시 존재해야 하는지 / adapter/wrapper/sidecar evidence로 이동 가능한지 / C0–C7 Frozen blob을 수정하지 않고 해결 가능한지 / Producer byte pins를 변경하지 않고 해결 가능한지 / serialized numerical values와 semantic outputs가 완전히 동일한지 를 조사하라. Track C Frozen source 수정 또는 producer repin 중 하나가 실제로 불가피한 경우에만 두 대안을 다시 사용자 결정으로 올려라. 단순 merge order로 schema ownership 문제를 숨기지 마라.

> core Technical/Macro snapshot을 수정하지 않는 adapter/wrapper/sidecar 방식까지 검토한다. Track C C0–C7 Frozen source와 Producer protected source를 모두 보존할 수 있는 방법이 있으면 그것을 우선한다. 어느 쪽의 Frozen/protected contract 변경도 피할 수 없다는 것이 증명될 경우에만 정확한 A/B 선택과 결과 영향을 다시 보고하라.

Effect: the A/B merge-order question in GCH-001 §4.2 is withdrawn pending the compatibility audit (evidence GIE-002). Neither option is selected.

## CDR-003 · Track C C8: method policy separated from numeric configuration

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (routing record. The Track C scoped Decision Register remains the authority) |
| Decided at | 2026-10-03, same message |

User wording (verbatim):

> Method policy와 real numeric configuration을 분리한다. 이미 승인된 method 범위와 synthetic/software validation은 Autonomous Execution으로 계속한다. 아직 미승인인 method choice는 각각 결과 영향과 근거를 제시한다. α, B, block length, seed, effect floor, minimum support, 실제 calibration configuration은 method approval과 묶지 않는다. 실제 CAL_VERIFY 접근 전에 별도의 preregistered numeric configuration 승인 지점으로 유지한다. CAL_VERIFY와 Holdout은 접근하지 않는다.

Effect:

- Owner work stays on the Track C owner branch (`ccr-22e3ff16-p7n5k5` / `feature/track-c-evl`). The Primary Integration Writer relays this decision to the Track C owner session and does not implement on the Track C branch.
- The Primary Integration Writer produces a read-only impact analysis of the unapproved method choices.
- Numeric configuration is a separate, preregistered approval gate before any real CAL_VERIFY access.

## Standing constraints restated by the user in the same message

> 이 세 결정 처리 후 다른 READY integration/audit 작업은 계속 진행한다. 단순 checkpoint 때문에 멈추지 않는다. canonical merge, publication grant, Official/LIVE promotion은 수행하지 않는다.
