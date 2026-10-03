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

## CDR-004 · IF-1 resolved: Option A1 + Technical/Macro owner adoption

| Field | Value |
|---|---|
| Status | **USER_DECIDED** |
| Decided at | 2026-10-03 (user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after GIE-002) |
| Supersedes | the open A/B item of CDR-002. CDR-002's audit requirement was satisfied by GIE-002 |
| Scope | integration target and repin procedure. **Not** a formula, value, regime, zone, Macro state, QGV or ranking change. **Not** canonical-merge approval |

User wording (verbatim):

> IF-1은 A1 + Technical/Macro owner adoption으로 승인한다.
> Track C 2137883의 additive lineage/schema 변경을 integration target으로 유지한다. Technical은 canonical C-28의 upstream ownership과 정합시키고, Macro는 동일 변경에 대한 별도 additive owner adoption record를 작성한다.
> 이 승인은 기존 Technical/Macro 계산식, 값, regime, zone, Macro state, QGV, ranking을 변경하는 승인이 아니다.
> Producer owners는 새 schema를 대상으로 기존 numerical/semantic invariance를 다시 검증한 뒤 필요한 byte constants/fingerprints를 history-preserving 방식으로 repin한다.
> 단순히 테스트를 통과시키기 위해 pin을 변경하지 말고, 이전/이후 기존 필드 값과 계산 결과가 동일하다는 independent comparison을 먼저 PASS해야 한다.
> Track C Frozen chain은 rewrite하지 않는다.
> #10/#14 및 dependency-not-merged sentinel은 실제 integration context에 맞게 별도 compatibility repair 대상으로 처리한다.
> Macro의 이 adoption을 과거 승인으로 소급하지 말고 현재 owner adoption으로 기록한다.
> canonical merge는 아직 수행하지 않는다.

Effect:

- Integration target: Track C `2137883` additive lineage/schema change (`contracts/lineage.py`, 4 optional fields on TechnicalSnapshot/MacroSnapshot, `evaluate_stamped` on both engines). Track C Frozen chain is not rewritten.
- Technical: owner adoption aligned with canonical C-28 (Contract Conflict Register 2026-09-23 L348-353: "Fix belongs to the Technical system (upstream PATCH: add available_at from input data stamps)").
- Macro: a **separate, additive, current-dated** owner adoption record. Not retroactive.
- Producer repin order: (1) independent before/after comparison of existing field values and computed results PASS; (2) history-preserving repin of byte constants/fingerprints (prior pin retained in the record; new pin added with reason and authority). A pin change without a recorded PASS comparison is not allowed.
- #10/#14 CI-mode `models.py` compare and the dependency-not-merged sentinels (#10, #13, #14): separate compatibility-repair items in the actual integration context.
- Execution: the Primary Integration Writer prepares the adoption records and repins as **stacked proposal branches with Draft PRs into each owner branch**. No owner branch is committed to or rewritten. Owner branches without an active owner session are noted in each PR.

## CDR-005 · Track C C8: evidence recording, fail-open repair, M-B vs kernel counterexample

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (routing record. The Track C scoped Decision Register remains the policy authority) |
| Decided at | 2026-10-03, same message |

User wording (verbatim):

> GIE-004와 독립 분석 결과를 Track C Decision Register에 history-preserving evidence로 기록하라. 분석 결과 자체를 승인으로 기록하지 않는다.
> 기존 승인 정책을 우회하는 두 fail-open 경로는 LOCAL_FIXABLE implementation defect로 처리하고 수정·negative regression을 추가하라.
> CAL_VERIFY one-shot identity는 단순 campaign_id 변경으로 우회할 수 없어야 하며, Development-only evidence gate는 provenance/type label을 신뢰하는 것이 아니라 승인된 source identity와 lineage를 검증해야 한다.
> 수정으로 새로운 method policy를 만들지 않는다.
> 이후 M-B approved simulation과 current G-SUP kernel의 정확한 차이를 최소 반례로 제시하고, 어느 쪽을 authoritative method로 할지 별도 USER_DECISION_REQUIRED로 올려라.
> α/B/L/seed/effect floor/minimum support 등 numeric configuration은 계속 미승인이다.
> CAL_VERIFY/Holdout은 접근하지 않는다.

Effect:

- Work is prepared on a stacked branch off the Track C tip `ccr-22e3ff16-p7n5k5` @ `97d1b94`, with a Draft PR into that owner branch. The Track C owner session is notified. No C0–C7 Frozen blob is changed.
- GIE-004 is recorded in the Track C Decision Register as evidence only, with status "NOT_AN_APPROVAL".
- The two fail-open repairs apply existing approved policy (Q3 Development-only; Q4 / A6-S4 one-shot no-retest) and add negative regressions. No new method policy, no numeric value.
- The M-B simulation vs implemented kernel difference is presented as a minimal counterexample, and the authoritative-method choice is a separate USER_DECISION_REQUIRED.
- Numeric configuration stays unapproved. CAL_VERIFY and Holdout are not accessed.

## CDR-006 · Track C G-SUP authoritative method = M (approved M-B convention; additive v2)

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (routing record. The Track C scoped Decision Register is the policy authority and must record this itself) |
| Decided at | 2026-10-03 (user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after the owner's K/M/C item at `b9e01a9`) |
| Resolves | the USER_DECISION_REQUIRED in `implementation/reports/track_c_c8_gsup_mb_vs_kernel_counterexample_2026-10-03.md` (owner branch `ccr-22e3ff16-p7n5k5` @ `b9e01a9`) |

User wording (verbatim):

> M 승인. 승인된 M-B simulation convention을 authoritative G-SUP method로 유지한다. 별도 v2를 additive 구현한다. 현재 G-SUP v1은 history-preserving 방식으로 보존하며 rewrite/delete하지 않는다. v2는 승인된 M-B와: statistic / replicate construction / variance convention / degenerate handling / tie handling 을 exact하게 일치시켜야 한다. independent oracle과 counterexample로 v1/v2 차이를 고정한다. 기존 v1 결과를 v2 결과로 소급 재작성하지 않는다.

## CDR-007 · G-SUP one-shot source identity: source descriptor (synthetic/software-validation scope)

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (routing record; Track C register is the authority) |
| Decided at | 2026-10-03, same message |

User wording (verbatim):

> synthetic/software-validation 범위에서 source descriptor 구현을 승인한다. one-shot identity는 content serialization hash만으로 정의하지 않는다. outcome 접근 전에 등록된: source identity / vintage identity / sample identity 에 bind한다. 2.0 → 2 같은 의미 보존 재인코딩, campaign/root/label 변경으로 동일 검증 대상을 재소비할 수 없어야 한다. source descriptor 또는 lineage가 불완전하면 fail-closed한다.

Explicitly NOT approved by CDR-006/007 (user wording, verbatim list): α, B, L / block rule, seed, effect floor, minimum support, size tolerance, dependence envelope / margin, 실제 source taxonomy/default, 실제 CAL_VERIFY 접근, C8 foundation registry와 G-SUP registry 통합, Holdout 소비, C8 SOFTWARE FROZEN 선언, publication grant, Official, LIVE, canonical merge.

## CDR-008 · Ownership boundary for CDR-006/007 implementation (Codex) and integration-owner verification

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (routing) |
| Decided at | 2026-10-03, same message |

User wording (verbatim):

> 현재 Codex가 별도 worker로 Track C C8의 사용자 승인 범위를 구현 중일 수 있다. 그 작업을 중단하거나 인수하거나 중복 구현하지 마라.
> Codex가 이미 위 승인 범위의 Track C 작업을 시작했거나 branch/commit/PR을 만들었다면 그 branch를 READ-ONLY upstream으로 취급하라. Claude Code Main은: 같은 G-SUP v2를 다시 구현하지 않는다. 같은 source descriptor를 다시 구현하지 않는다. Codex branch를 rewrite/rebase/force-push하지 않는다. Codex scoped STATUS/evidence를 대신 작성하지 않는다.
> Claude Code Main만 Global Handoff shared routing/index를 관리한다. Capability worker와 Codex는 Global Handoff writer가 아니다.

Effect:

- The Primary Integration Writer does not implement G-SUP v2 or the source descriptor. As of the fetch at 2026-10-03T06:58Z, no Codex Track C branch, PR or commit exists; Codex branches present are `codex/takeover-integration-2026-10-03` (#28), `codex/web-producer-integration-readiness-2026-10-03` (#29), `codex/combined-integration-2026-10-03` (#30).
- When a Codex Track C result appears, the Primary Integration Writer verifies it read-only against the user's 13-point list (exact HEAD, approval record, changed files, v1 preservation, M-B↔v2 exact agreement, p=0.10/0.15 counterexample, source/vintage/sample negative cases, 2.0→2 re-encoding rejection, campaign/root/label bypass rejection, targeted regression, full regression, Actions, CAL_VERIFY/Holdout untouched) before reflecting it here.
- The Track C Claude owner session is informed of CDR-006/007/008 so that it does not start a duplicate implementation.

## CDR-009 · Codex active-write exclusion on Track C C8 paths

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (routing / write-set rule) |
| Decided at | 2026-10-03 (user message in session `session_019znshzTYgyBnuuBmSxdPFN`, ~07:03Z) |
| Lifts when | Codex checkpoint for that work is DONE or HANDOFF_READY |

User wording (verbatim):

> Codex active-write exclusion: Codex가 현재 작업 중인 Track C C8 owner branch에서 변경 중이거나 변경 예정인 evl/superiority*, G-SUP v2, source-descriptor, 관련 C8 oracle/test/acceptance/evidence 경로는 Codex checkpoint가 DONE 또는 HANDOFF_READY가 될 때까지 Claude Code Main의 write set에서 제외한다. Integration trial에서 해당 파일을 읽거나 임시 merge하여 검증하는 것은 허용하지만 commit으로 수정·repin·resolve하지 않는다. 충돌이 발견되면 Codex 작업을 덮어쓰지 말고 integration evidence로 기록한다.

Effect on the Primary Integration Writer's write set (until Codex DONE/HANDOFF_READY):

- Excluded from any commit by the Primary Integration Writer or its agents: `implementation/src/investment_system/evl/superiority*`, any G-SUP v2 module, any source-descriptor module, and the related C8 oracle/test/acceptance/evidence paths on the Track C owner branch (including `tests/test_evl_c8*`, `tests/evl_c8*`, `tools/track_c_c8*`, `implementation/reports/track_c_c8*`, and the Track C decision register).
- Allowed: reading these files; temporary (uncommitted / never-pushed) merges in integration trials for verification.
- Not allowed: committing a modification, repin or conflict resolution touching them. A conflict found in an integration trial is recorded as integration evidence, not resolved.
- State at recording: no Codex commit on `ccr-22e3ff16-p7n5k5` (tip `b9e01a9`) and no Codex Track C branch at the 07:03Z fetch. None of the Primary Integration Writer's in-flight tasks write these paths.
