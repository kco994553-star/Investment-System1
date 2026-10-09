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

## CDR-010 · Track C G-SUP M-B v2 authoritative arithmetic contract

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (method arithmetic convention for the CDR-006 v2 only) |
| Decided at | 2026-10-03 (user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after GCH-007 / `50b2a13`) |
| Resolves | USER_DECISION_REQUIRED_ARITHMETIC_REDUCTION raised by Codex in PR #31 and independently reproduced in GIE-008 §2 |
| Implementer | Codex, in PR #31 (CDR-008 unchanged) |

User wording (verbatim):

> Track C G-SUP M-B v2 arithmetic convention에 대한 사용자 결정을 기록한다.
>
> 승인된 authoritative arithmetic contract:
>
> Arithmetic = math.fsum
> Replicate aggregation = block grouping
> Block sums = direct summation
> Replicate mean = (Σ full block sums + partial) / n
> Degeneracy predicate = 기존 승인된 run() 의미와 동일하게
> sqrt(v/n) > 0 이 false이면 degenerate
>
> 즉 다음 세 축을 함께 승인한다.
>
> 1. reducer = math.fsum
> 2. replicate grouping = block grouping
> 3. block-sum construction = direct block sums
>
> 기존 G-SUP v1과 historical evidence/result는 보존한다.
> v2는 additive version이며 v1 결과를 소급 변경하지 않는다.

Scope of this decision, as recorded by the routing writer:

- It fixes the four arithmetic fields that GIE-008 §2 said must be pinned together: reducer, replicate grouping, block-sum construction and degeneracy predicate.
- It does not change any other CDR-006 field (statistic, replicate construction, variance convention, tie handling) or CDR-007.
- In GIE-008 §2 terms this is the "fsum / blocks" column. On the five recorded fixtures that column gives CE4 .10, FLIP .10, LEFT_SUM .35, TIE .45, seed 275 .55. These are evidence values to be re-checked against Codex's v2, not acceptance thresholds set by this register.

Not approved by this decision, per the user's same message (verbatim list):

> - numeric calibration configuration
> - α / B / L / seed
> - effect floor
> - minimum support
> - size tolerance
> - dependence envelope / margin
> - 실제 CAL_VERIFY 접근
> - Holdout
> - C8 Freeze
> - publication grant
> - Official / LIVE
> - canonical merge
> - validator hardening이 요구하는 #17 protected digest repin

The user also stated that this decision is not to be read as C8 FROZEN, CAL_VERIFY approval, numeric configuration approval, Holdout approval, Official or publication.

## CDR-011 · CDR-009 exclusion renewed until PR #31's next HANDOFF_READY; re-verification and next-trial rules

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (routing / write-set rule and verification scope) |
| Decided at | 2026-10-03, same user message as CDR-010 |
| Lifts when | PR #31 reaches a new HANDOFF_READY checkpoint after implementing CDR-010 |

User wording (verbatim, excerpts):

> Codex가 PR #31에서 authoritative M-B v2를 구현한다.
>
> Claude Main은 해당 Track C C8 active-write 경로를 수정하지 않는다.
>
> CDR-009 active-write exclusion을 유지한다.
>
> PR #31이 새 HANDOFF_READY checkpoint에 도달할 때까지:
>
> - G-SUP v2 source 수정 금지
> - source identity 수정 금지
> - 관련 C8 oracle/test 수정 금지
>
> read-only tracking만 수행한다.
>
> Codex 구현을 중복하지 않는다.

> PR #31이 새로운 HANDOFF_READY에 도달하면 fresh fetch 후
> 기존 13-point verification을 이어서 수행한다.
>
> 특히 이전에 DEFERRED였던:
>
> item 5
> item 6b
>
> 를 반드시 다시 검증한다.

> Codex의 PASS 주장을 그대로 복사하지 않는다.

> Codex #31의 v2 구현과 독립 검증이 완료되면:
>
> 현재 검증된 integration trial
> +
> PR #31
> +
> PR #35
>
> 를 기준으로 새로운 combined trial을 만든다.
>
> fresh HEAD를 사용한다.
>
> 기존 #38 결과를 최신 trial 결과처럼 재사용하지 않는다.

> canonical merge는 하지 않는다.

Additional verification scope named by the user for the new checkpoint: exact HEAD, approved arithmetic contract, v1 preservation, M-B v2 implementation, independent oracle, CE4, FLIP, LEFT_SUM, TIE, seed 275, exact decimal comparison, degeneracy handling, targeted regression, full regression, Actions, source identity preservation. Next combined trial checks named by the user: merge conflicts, full regression, browser/E2E, producer contracts, engine fingerprints, protected paths, Track C preservation, source/provenance, no publication/Official/LIVE escalation.

Effect: CDR-009's write exclusion, which had reached its end condition at `29c2c20`, applies again to the same paths until PR #31's next HANDOFF_READY. Read-only tracking and temporary, never-pushed trial merges stay allowed.

## CDR-012 · G-SUP M-B v2: squaring = d*d (F1); all-degenerate replicates fail closed as NOT_RUN (F3)

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (supplement to the CDR-010 arithmetic contract, v2 only) |
| Decided at | 2026-10-04 (user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after GCH-009 / `a267917`) |
| Resolves | F1 and F3 raised in GIE-010 §2 |
| Implementer | Codex, additive and history-preserving (CDR-008 unchanged) |
| Verifier | Primary Integration Writer, after Codex's next HANDOFF_READY |

User wording (verbatim):

> F1: G-SUP M-B v2의 squaring은 d*d로 고정한다. ** 2/libm pow를 authoritative v2에서 사용하지 않는다. 이는 arithmetic reproducibility 계약의 보완이며 기존 v1/history를 변경하지 않는다.
> F3: bootstrap replicate가 모두 degenerate인 경우 G-SUP은 statistical PASS를 생성하지 않고 NOT_RUN으로 fail-closed한다. 이 승인은 float residual을 판정하기 위한 새로운 epsilon/tolerance/threshold를 승인하지 않는다.
> Codex가 두 변경을 additive/history-preserving 방식으로 구현하고 independent oracle·negative regression·full regression·Actions·scoped handoff까지 진행한다. Claude Main은 Codex HANDOFF_READY 후 F1/F3를 독립 재검증하고 PR #39의 fresh successor combined trial을 수행한다.
> numeric configuration, CAL_VERIFY, Holdout, C8 Freeze, publication/Official/LIVE, canonical merge는 여전히 승인하지 않는다.

Scope of this decision, as recorded by the routing writer:

- F1 fixes the squaring operator inside v2 as correctly rounded multiplication (`d*d`), the reading used by the GIE-009 reference oracle's default and by the approved simulation's NumPy squares. `** 2` and libm `pow` are excluded from authoritative v2. v1 and every historical record stay unchanged.
- F3 applies when every bootstrap replicate is degenerate (degenerate means `sqrt(v/n) > 0` is false, per CDR-010). G-SUP then produces no statistical PASS and fails closed as NOT_RUN.
- F3 does not add any epsilon, tolerance or threshold. Consequently a near-undefined original statistic whose replicates are not all degenerate (GIE-010 §2 example `[0.05]*12`) keeps the CDR-010-literal result; it is not covered by this decision.
- Until Codex's next HANDOFF_READY, the CDR-009/CDR-011 write exclusion applies to the same Track C C8 paths; the Primary Integration Writer tracks read-only and does not duplicate the implementation.

Still not approved (user's same message): numeric configuration, CAL_VERIFY, Holdout, C8 Freeze, publication/Official/LIVE, canonical merge.

## CDR-013 · CDR-012 F1 scope = M-B statistic only — RESOLVED — NO ADDITIONAL CHANGE; MAC-X1 prioritized

| Field | Value |
|---|---|
| Status | **USER_DECIDED** |
| Decided at | 2026-10-04 (user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after GCH-011 / `dc958a8`) |
| Resolves | the F1 scope question in GIE-011 §1 |

User wording (verbatim, excerpt):

> F1 범위는 CDR-012 승인 의도대로 M-B 통계량으로 한정한다.
>
> frozen v1 Development dependence estimator의 "(v - m) ** 2"는 이번 CDR-012 범위 밖으로 유지한다.
>
> 현재 evidence상 해당 값은 feasibility envelope에만 사용되고 M-B p-value에는 사용되지 않으므로, 이를 이유로 v1을 수정하거나 v2 전용 estimator를 새로 만들지 마라.
>
> 따라서 F1 scope question은:
> "RESOLVED — NO ADDITIONAL CHANGE"
> 로 history-preserving 방식으로 기록한다.
>
> 그 다음 canonical merge를 진행하지 말고 MAC-X1을 최우선 integration blocker로 처리한다.

Recorded effect:

- **F1 scope question: RESOLVED — NO ADDITIONAL CHANGE.** CDR-012 F1 covers the M-B statistic only. The frozen v1 `development_dependence_estimate` (`superiority.py:247`, `(v - m) ** 2`) stays as it is; no v1 change and no v2-only estimator.
- **MAC-X1** (Track C Frozen acceptance tooling on an advanced or integrated canonical; GIE-009 §2.4, GIE-011 §3) becomes the top integration blocker. The user's constraints for that work, in the same message: no temporary PR-specific or hard-coded SHA exception; do not weaken Frozen acceptance meaning, PIT/no-lookahead, Frozen history, provenance or Holdout isolation; preserve PR #40 as exact-tree historical evidence without relabelling; do not modify #21, RIG or other owner branches without ownership; prefer deterministic verification. A D1/D2 implementation within approved scope proceeds through verification; a new Frozen acceptance meaning, a policy relaxation, a canonical merge ordering policy or another D3 is presented as options with a recommendation, not implemented.
- Still prohibited (same message): canonical merge, CAL_VERIFY, Holdout consumption, C8 Freeze, numeric configuration, publication grant, Official/LIVE promotion, #17 protected digest repin.

## CDR-014 · MAC-X1 resolved by a hardened Frozen Projection Identity Audit (FPIA); GIE-012 §5 decisions

| Field | Value |
|---|---|
| Status | **USER_DECIDED** |
| Decided at | 2026-10-04 (user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after GCH-013 / `818bd69`) |
| Resolves | MAC-X1 D3 items GIE-012 §5-1 … §5-5 |
| Implementer / verifier | Primary Integration Writer (additive integration tooling on a PIW branch; no owner or Codex branch is modified) |

User wording (verbatim):

> MAC-X1 GIE-012의 D3 결정을 다음과 같이 승인한다.
>
> 1. Integration acceptance
>
> §5-1은 (a) 를 승인한다.
>
> Track C의 기존 Frozen 기록과 exact-tree identity는 역사적 evidence로 그대로 보존한다.
>
> 이를 rewrite하거나 현재 canonical에 맞추어 재해석하지 않는다.
>
> 대신 canonical/integration merge-result SHA마다 별도의:
>
> "Frozen Projection Identity Audit (FPIA)"
>
> 를 수행하여 Track C integration acceptance를 판정한다.
>
> 단, 적대적 리뷰에서 첫 FPIA 설계가 반박되었으므로 그 초안을 그대로 구현하는 것은 승인하지 않는다.
>
> 아래 조건을 충족하는 hardened FPIA로 수정한 뒤 구현·검증한다.
>
> 2. Code identity
>
> 통합 tree에서 package-level code identity가 기존 Frozen identity와 달라졌다면 이를 PASS 또는 SAME으로 정규화하지 마라.
>
> 반드시:
>
> "DIVERGED"
>
> 로 사실 그대로 기록한다.
>
> DIVERGED 자체는 다른 capability의 정상적인 additive Python 변경 때문에 발생할 수 있으므로 자동 Frozen violation으로 간주하지 않는다.
>
> 대신 FPIA가 Track C projection의 보존과 비간섭을 별도로 증명해야 한다.
>
> 3. Historical Frozen evidence
>
> 기존:
>
> - Frozen evidence
> - Frozen hashes
> - Frozen acceptance
> - historical registration
> - Decision history
> - v1 history
>
> 를 rewrite하지 않는다.
>
> Frozen identity는 당시 exact tree에 대한 historical statement로 유지한다.
>
> 4. Reference authentication
>
> FPIA가 사용하는 모든 reference head/evidence는 명시적으로 인증한다.
>
> 임의의 reference SHA나 caller-supplied reference를 신뢰하지 않는다.
>
> 승인된 Decision Register / scoped evidence / immutable Git ancestry와 연결되지 않은 reference는 fail-closed한다.
>
> 5. Track C projection
>
> Integration tree에서 Track C-owned/protected projection을 구성하고 다음을 검증한다.
>
> - protected source byte identity
> - protected test byte identity
> - Frozen evidence identity
> - approved additive history
> - provenance
> - no unauthorized mutation
> - no deletion/substitution
>
> Projection 정의 자체가 새로운 Frozen contract 의미를 만들지 않도록 기존 ownership/evidence에서 도출한다.
>
> 6. CDR-012 / v2 binding
>
> v2 파일은 현재 검증된 CDR-012 head:
>
> "c9e0fa7e4078290b5db9cb798cf52c0d0cd66240"
>
> 및 승인된 GIE/CDR evidence에 cryptographically/byte-wise binding한다.
>
> Integration tree에서 동일성을 확인하고 CDR-012/v2 targeted tests 및 필요한 oracle replay를 다시 실행한다.
>
> Hard-coded PR-specific exception을 만들지 않는다.
>
> 7. Runtime/test integrity
>
> 적대적 리뷰에서 확인된 우회경로를 반드시 차단한다.
>
> 최소한 다음을 검증한다.
>
> - committed ".pyc" 또는 다른 bytecode substitution
> - pytest plugin injection
> - pytest configuration manipulation
> - environment/configuration을 통한 test suppression
> - collection 변경
> - required test deselection
> - 실행 source와 audited source 불일치
>
> 검증 환경/provenance가 확인되지 않으면 fail-closed한다.
>
> 8. Decision Register provenance
>
> Track C Decision Register의 append를 단순히 "append-only"라는 이유만으로 신뢰하지 않는다.
>
> 새 append가 승인된 decision/evidence와 연결되는지 provenance를 검증한다.
>
> 출처 없는 append 또는 승인 경계를 확장하는 append는 integration acceptance를 만들 수 없다.
>
> 9. Shared overlay / merge result
>
> shared overlay conflict를 사전 추론으로 PASS시키지 않는다.
>
> history-preserving merge 후 실제 merge-result tree를 대상으로 audit한다.
>
> 충돌, unauthorized resolution 또는 Track C protected content 변화가 있으면 fail-closed한다.
>
> 10. FPIA 결과 상태
>
> 최소한 다음 개념을 구분한다.
>
> - HISTORICAL_FROZEN_IDENTITY_PRESERVED
> - CODE_IDENTITY_SAME / DIVERGED
> - TRACK_C_PROJECTION_PRESERVED
> - INTEGRATION_INTERFERENCE_NONE / FOUND
> - FPIA_PASS / FAIL / NOT_RUN
>
> "DIVERGED"를 "SAME" 또는 기존 Frozen PASS로 위장하지 않는다.
>
> 11. Registration
>
> §5-2 추천안을 승인한다.
>
> Python code 변경이 있는 중간 merge에서 기존 registration이 fail-closed되는 것을 수용한다.
>
> 새 registration은 필요한 capability/code integration이 끝난 최종 canonical candidate에서 생성한다.
>
> 중간 tree마다 기존 registration을 억지로 유효하게 만들지 않는다.
>
> 12. v2 인증
>
> §5-3 추천안을 승인한다.
>
> 검증된 head와 byte identity를 binding하고 v2 tests/oracle을 재실행한다.
>
> 13. Shared overlay
>
> §5-4 추천안을 승인한다.
>
> fail-closed를 유지하고 history-preserving merge-result를 audit한다.
>
> 14. Track C branch CI
>
> §5-5 추천안을 승인한다.
>
> canonical 이동으로 기존 Track C branch acceptance가 red가 되는 것을 숨기거나 acceptance 조건을 완화하지 않는다.
>
> Branch/Frozen historical validation과 canonical integration acceptance를 별개의 evidence class로 유지한다.
>
> 15. 구현/검증
>
> 위 승인 범위 안에서 hardened FPIA를 구현한다.
>
> 순서:
>
> PLAN
> → adversarial findings를 acceptance criteria로 변환
> → implementation
> → targeted negative tests
> → baseline "b9e01a9" 검증
> → PR #40 "acaf1b5" 검증
> → tamper/adversarial probes
> → full regression where applicable
> → completeness review
> → evidence 기록
>
> 첫 FPIA 설계를 반박했던 adversarial cases는 반드시 regression으로 고정한다.
>
> 새로운 수치 threshold/default/tolerance를 만들지 않는다.
>
> 16. 계속 금지
>
> 이번 승인은 다음을 승인하지 않는다.
>
> - canonical merge
> - C8 Freeze
> - numeric configuration
> - CAL_VERIFY
> - Holdout 접근/소비
> - publication grant
> - Official/LIVE promotion
> - #17 protected digest repin
> - Frozen evidence rewrite
> - 기존 Track C acceptance 완화
> - 다른 owner branch의 임의 수정
>
> 새로운 D3가 없다면 hardened FPIA 구현·검증과 integration-order 분석까지 자율적으로 계속 진행한다.
>
> 새 D3가 발생하면 그 지점에서만 중단한다.

FPIA reference manifest (machine-readable; written by the routing writer). FPIA must accept a reference only if its value, or the short form quoted, appears inside the user-verbatim (`> `) lines of this CDR entry, this register commit is an ancestor of `origin/integration/global-handoff-v1`, and the register at that commit is a byte prefix of the register at the branch tip:

```fpia-reference-manifest
{"cdr": "CDR-014",
 "track_c_reference": {"sha": "b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565", "quoted_as": "b9e01a9", "role": "Track C accepted head (baseline); Frozen evidence heads must be its ancestors"},
 "v2_reference": {"sha": "c9e0fa7e4078290b5db9cb798cf52c0d0cd66240", "quoted_as": "c9e0fa7e4078290b5db9cb798cf52c0d0cd66240", "role": "verified CDR-012 v2 head (GIE-011)"},
 "verification_subjects": [{"sha": "acaf1b5a82859ac2750a130ebe88f8b4d272ac66", "quoted_as": "acaf1b5", "role": "PR #40 tree to audit; not a reference"}]}
```

## CDR-015 · Decision Authority delegation (D1/D2 self-decision; D3 = cost only); supersedes re-approval requirements

| Field | Value |
|---|---|
| Status | **USER_DECIDED** |
| Decided at | 2026-10-05 12:15 KST (2026-10-05T03:15Z; user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after GCH-014b / `b5b4ca6`) |
| Supersedes | the user re-approval requirements in CDR-001 … CDR-014, within the scope below. Every earlier entry and approval record is preserved unchanged |
| Applies to | every Investment-System1 Work (owners, Codex, Claude Code workers, the Primary Integration Writer), including automatic resumption |

User wording (verbatim):

> Investment-System1의 Decision Authority를 다음과 같이 변경·승인한다.
>
> 이 지시는 기존의 사용자 재승인 요구를 아래 범위에서 대체한다. 실제 KST 시각과 사용자 원문을 Decision Register에 append하고 Global/scoped Handoff에 반영하라. 과거 승인 기록은 보존한다.
>
> D1:
> 일반 구현·문서·테스트·CI·자동화는 자율 실행한다.
>
> D2:
> 프로젝트 목표에 필요한 정책 선택, 수치 configuration, 계약 변경, versioned successor, migration, canonical merge, publication, 배포는 근거와 검증을 갖춰 자체 결정·실행한다. D3로 분류됐다는 이유만으로 사용자 승인을 다시 요청하지 않는다.
>
> D3:
> 유료 결제·유료 구독·추가 과금·무료 quota 초과만 사용자 승인을 요청한다. 비용 발생 여부를 확인할 수 없으면 해당 자원 사용만 보류한다.
>
> 실제 증권 주문·자금 이동과 프로젝트 밖의 행동은 위임 범위에 포함되지 않는다.
>
> 권한 확대는 검증 면제가 아니다. PIT, provenance, evidence 무결성과 결과의 정직한 표시는 유지한다. 실패를 숨기거나 테스트를 skip하여 PASS를 만들지 않는다. 기존 Frozen/history는 rewrite하지 않고 후속 버전으로 변경한다.
>
> 현재 미결정 사항은 새 권한 기준으로 재분류한다. FPIA D3-a~e도 요구사항·대안·영향을 검토하여 자체 해결한다. 탐지·검증하지 못한 범위를 숨기고 전체 PASS로 확대하지 않는다.
>
> 각 자체 결정에는 이유·영향·검증·복구 방법을 기록한다. 전체 프로젝트 완성을 기다리지 말고 검증된 작은 기능 묶음부터 단계적으로 통합한다.
>
> 각 Work의 자동 재개에도 이 권한 기준을 적용한다. 실행 가능한 backlog가 있으면 계속 진행하고, 실제 외부 입력 부재나 해결 불가능한 blocker가 있을 때만 대기한다. 다른 owner의 변경은 기존 routing과 단일 작성자 규칙을 따른다.
>
> 현재 작업을 중단하거나 처음부터 다시 시작하지 말고, 이 결정을 기록한 뒤 이어서 진행하라.

Recorded effect (routing writer's reading; the user wording above governs):

- **D1** (autonomous): implementation, documentation, tests, CI and automation.
- **D2** (decide and execute with evidence and verification, without asking the user again): policy choices needed for the project goal, numeric configuration, contract changes, versioned successors, migrations, canonical merges, publication and deployment. An item previously listed as "not approved" or as a D3 in CDR-003 … CDR-014 (for example canonical merge, numeric configuration, C8 Freeze, CAL_VERIFY, Holdout access, publication grants, Official/LIVE promotion, the #17 digest repin, FPIA D3-a … D3-e, the G7 interpretation) is now D2: it needs a recorded decision with reason, impact, verification and recovery, and the evidence that supports it, not a new user approval.
- **D3** (ask the user): only paid payment, paid subscription, extra charges, or exceeding a free quota. If whether a cost arises cannot be established, only the use of that resource is held.
- **Outside the delegation:** real securities orders, movements of funds, and actions outside the project.
- **Unchanged obligations:** PIT/no-lookahead, provenance, evidence integrity and honest reporting of results; no hidden failure and no skipped test to reach PASS; Frozen records and history are changed only by successor versions, never rewritten; undetected or unverified scope is disclosed and never folded into an overall PASS.
- **Self-decision records:** decisions taken under this delegation are recorded with reason, impact, verification and recovery. The Primary Integration Writer records its own in `PIW_DECISION_RECORDS.md` (this directory); capability owners record theirs in their scoped Decision Registers.
- **Integration cadence:** verified small bundles are integrated step by step, without waiting for the whole project.
- **Ownership:** changes to another owner's branch or scoped records still follow the existing routing and single-writer rules. Scoped owners adopt this entry at their next fresh read; the Primary Integration Writer does not write their scoped registers or handoffs.

## CDR-016 · Chart PR #41 production blockers: owner routing directive; protected boundaries for this Work

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (operating directive for the Integration / Claude Main Work) |
| Decided at | 2026-10-05 12:43 KST (2026-10-05T03:43Z; user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after GCH-015 / `d92363f`) |
| Relates to | CDR-015 (decision authority), CDR-014 (FPIA), PR #41 (Chart) |

User wording (verbatim):

> Investment-System1 Integration / Claude Main Work를 최신 GitHub 실제 상태에서 계속 진행한다.
>
> 이번 작업의 추가 목표는 Chart PR #41이 확인한 production blocker 6개를
> 각 authoritative owner에게 정확히 routing하고,
> 이미 해결 가능한 것은 Integration에서 검증하여 Chart Work가 다시 진행될 수 있게 만드는 것이다.
>
> 새 Chart 기능을 Integration Work에서 직접 구현하는 것이 목적이 아니다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 0. FRESH GITHUB / HANDOFF FIRST
> ━━━━━━━━━━━━━━━━━━━━
>
> 시작 시 반드시 GitHub를 fresh fetch/read한다.
>
> 다음 순서로 실제 상태를 복원한다.
>
> 1. canonical/default + exact HEAD
> 2. integration/global-handoff-v1
> 3. GLOBAL_CURRENT_HANDOFF
> 4. GLOBAL_STATUS_INDEX
> 5. COORDINATION_DECISION_REGISTER
> 6. Integration/FPIA scoped handoff
> 7. Chart PR #41 + Chart scoped handoff
> 8. Portfolio owner handoff
> 9. Identity owner handoff
> 10. Product/P01 handoff
> 11. Web owner handoff
> 12. QGV owner handoff
> 13. Decision / Approval / Evidence / Conflict registers
> 14. 관련 PR / branch / Actions / reviews
> 15. ownership / write-set / dependency
>
> 과거 SHA보다 실제 GitHub가 우선한다.
>
> 다른 owner의 구현을 중복하지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 1. CHART CURRENT CHECKPOINT
> ━━━━━━━━━━━━━━━━━━━━
>
> 마지막 Chart 보고 기준:
>
> PR #41
> last observed HEAD:
> 74df6784071137bdca911964af94c8e1b6928c92
>
> 단 반드시 fresh-read한다.
>
> Chart Lane A:
> IMPLEMENTATION_NOT_READY
>
> production blockers:
> 정확히 6개
>
> 1. authoritative TARGET root
> 2. Security mapping
> 3. Theme revision/version
> 4. Product authority
> 5. owner write-set acceptance
> 6. FPIA governance/admissibility
>
> 마지막 분류:
>
> 1~5 = OWNER_ACTION_REQUIRED
> 6 = USER_D3_REQUIRED / existing Integration D3/G7 dependency
>
> Chart Work 자체에서 가능한 독립 검증은 현재 소진된 것으로 보고됐다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 2. OBJECTIVE
> ━━━━━━━━━━━━━━━━━━━━
>
> 6개 blocker를 단순히 Global Handoff에 다시 나열하지 않는다.
>
> 각 blocker에 대해:
>
> - authoritative owner를 확정
> - owner가 제공해야 할 exact artifact/evidence 결정
> - 이미 repository에 존재하는지 fresh 확인
> - 존재하면 Chart-compatible 여부 검증
> - 없으면 owner action으로 routing
> - 완료 조건 정의
> - dependency ordering 정의
>
> 를 수행한다.
>
> 목표는 Chart Work가 다음 실행에서
> 6개 blocker를 실제로 줄일 수 있도록 만드는 것이다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 3. BLOCKER 1 — AUTHORITATIVE TARGET ROOT
> ━━━━━━━━━━━━━━━━━━━━
>
> Portfolio owner를 확인한다.
>
> Chart가 요구하는 최소 receipt:
>
> - portfolio_id
> - portfolio_version
> - effective_at
> - current TARGET constituent set
> - security reference
> - target_weight
> - denominator
> - completeness
> - provenance/source
> - authoritative-root declaration
>
> 현재 repository에 이미 equivalent authoritative object가 있으면
> 새 object를 만들지 말고 재사용 가능성을 검증한다.
>
> 없다면 Portfolio owner action으로 routing한다.
>
> 현재 Strategy Theme target:
>
> 반도체 장비 30
> AI·반도체 25
> Big Tech 20
> 기타산업 25
>
> 는 Chart에서 Decimal 합계 100.000%까지 검증됐지만,
> 이 사실만으로 authoritative root가 되는 것은 아니다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 4. BLOCKER 2 — SECURITY MAPPING
> ━━━━━━━━━━━━━━━━━━━━
>
> Identity owner를 확인한다.
>
> 기존 공통:
>
> Issuer → Security → dated Listing
>
> contract를 재사용한다.
>
> Chart Target constituents 전체에 대해 최소:
>
> portfolio constituent
> → internal security_id
> → correct share/security form
> → dated listing
>
> binding을 제공해야 한다.
>
> ticker-only identity는 허용하지 않는다.
>
> 19개 전체에 대한 mapping receipt 또는
> Chart가 deterministic하게 조회할 authoritative path를 제공한다.
>
> 새 Chart 전용 identity layer를 만들지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 5. BLOCKER 3 — STRATEGY THEME REVISION
> ━━━━━━━━━━━━━━━━━━━━
>
> Portfolio/Classification owner를 확정한다.
>
> Strategy Theme는 GICS가 아니다.
>
> User-defined Strategy Theme / Portfolio Bucket이다.
>
> 필요한 최소 contract:
>
> - theme taxonomy/catalog id
> - version
> - effective_at
> - assignment
> - completeness
> - provenance
> - TARGET root binding
>
> 현재 네 bucket의 경제적 의미를 새로 바꾸지 않는다.
>
> 단순 version/provenance 구조라면 기존 승인 범위에서
> D1/D2로 해결 가능한지 먼저 판단한다.
>
> 새 정책 결정이 아니라 기존 Target classification의 identity/version 문제라면
> 불필요하게 D3로 올리지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 6. BLOCKER 4 — PRODUCT AUTHORITY
> ━━━━━━━━━━━━━━━━━━━━
>
> P01/Product owner에게 다음 질문을 명시적으로 routing한다.
>
> "현재 P01 research-display/publication authority contract가
> user-authored TARGET Portfolio visualization에 적용 가능한가?"
>
> 가능한 답은 최소:
>
> A. 기존 P01 authority 재사용 가능
> B. 별도 Target/Product authority 필요
> C. 현재 contract로는 판단 불가
>
> 중 하나여야 한다.
>
> A라면 exact authority/read route와 predicate를 evidence로 남긴다.
>
> B/C라면 필요한 최소 contract를 owner가 제시한다.
>
> Chart Work가 임의로 publication policy를 만들게 하지 않는다.
>
> Source/data rights와 Product authority를 분리한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 7. BLOCKER 5 — OWNER WRITE-SET ACCEPTANCE
> ━━━━━━━━━━━━━━━━━━━━
>
> Chart Target Strategy Theme vertical slice의 최소 write-set을
> Chart scoped handoff에서 읽는다.
>
> 각 파일/경로에 대해 owner matrix를 만든다.
>
> 최소:
>
> - Chart owner
> - Portfolio owner
> - Product owner
> - Web/P01 owner
> - Integration owner
> - Track C/FPIA impact
>
> 를 판정한다.
>
> 목표는:
>
> "누가 어떤 파일을 수정해도 되는지"
>
> 를 명시적으로 확정하는 것이다.
>
> 가능하면 Chart owner가 자신의 branch에서 구현하고,
> 다른 owner는 contract/acceptance만 제공하는 구조를 우선한다.
>
> 다른 owner가 Chart 기능 자체를 중복 구현하게 하지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 8. BLOCKER 6 — FPIA GOVERNANCE / ADMISSIBILITY
> ━━━━━━━━━━━━━━━━━━━━
>
> 이 항목은 현재 Integration critical path다.
>
> PR #42 및 successor/FPIA work를 fresh-read한다.
>
> 특히 최신 Global에 기록된:
>
> - adversarial findings
> - environment-dependent judgement
> - round-3 fix
> - existing D3
> - G7
> - GIE closure
>
> 상태를 정확히 복원한다.
>
> 다음을 구분한다.
>
> FPIA implementation
> CI PASS
> independent review
> adversarial review
> D3 closure
> G7 closure
> GIE closure
> canonical applicability
> Chart exact-result FPIA
>
> 현재 owner 수정/검증으로 해결 가능한 것은 자동 진행한다.
>
> 실제 새로운 semantic/governance D3만 사용자에게 요청한다.
>
> 과거 D3라는 이유만으로 재질문하지 말고
> 이미 사용자가 승인한 것이 있는지 Decision Register와 현재 대화를 대조한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 9. ROUTING OUTPUT
> ━━━━━━━━━━━━━━━━━━━━
>
> 각 blocker를 다음 형태로 기록한다.
>
> BLOCKER
> OWNER
> CURRENT STATE
> REQUIRED ARTIFACT
> EXACT PATH/PR
> ACCEPTANCE CRITERIA
> DEPENDENCY
> CAN PROCEED NOW?
> NEXT OWNER ACTION
>
> 가능하면 owner가 바로 소비할 수 있는 작은 packet/receipt 형태로 만든다.
>
> 단순 prose 요청보다 machine/checkable evidence를 우선한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 10. PARALLELISM
> ━━━━━━━━━━━━━━━━━━━━
>
> 독립적인 owner action은 병렬 routing한다.
>
> 예:
>
> Portfolio:
> TARGET root + Theme revision
>
> Identity:
> Security mapping
>
> Product/P01:
> authority applicability
>
> Web/Product:
> write-set acceptance
>
> Integration:
> FPIA closure
>
> 서로 dependency가 없는 것은 순차적으로 기다리지 않는다.
>
> 하지만 같은 파일을 여러 owner가 수정하게 만들지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 11. CHART AUTOMATION GAP
> ━━━━━━━━━━━━━━━━━━━━
>
> Chart Work가 확인한 automation gap도 Integration coordination 관점에서 처리한다.
>
> 확인된 문제:
>
> PR dependency 변화는 wake-up 대상이지만
> Global branch에만 기록된 material dependency 변화는
> Chart Work를 즉시 깨우지 못할 수 있다.
>
> 새 automation framework를 만들지 않는다.
>
> 대신 가능한 최소 해결책을 판단한다.
>
> 우선순위:
>
> 1. 기존 Chart event automation이 Global material dependency change를 소비할 수 있는지
> 2. 불가능하면 Global writer가 Chart-relevant owner receipt/decision을
>    Chart가 감시하는 기존 경로에 전달할 수 있는지
> 3. 그래도 불가능하면 최소 polling/watch 보완
>
> 모든 Global commit마다 Chart를 재실행하는 방식은 피한다.
>
> Chart blocker와 관련된 material semantic delta만 trigger 대상이어야 한다.
>
> automation 자체가 프로젝트 병목이 되지 않게 한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 12. AUTO-CONTINUE
> ━━━━━━━━━━━━━━━━━━━━
>
> D1/D2에서는 owner routing만 하고 멈추지 않는다.
>
> 현재 Work가 직접 해결 가능한:
>
> - FPIA repair
> - regression
> - review response
> - evidence
> - routing packet
> - coordination record
> - owner handoff
>
> 는 계속 수행한다.
>
> 장시간 Actions는 run_id/head_sha/attempt를 기록하고
> 다음 check로 넘긴다.
>
> 실제 D3에서만 사용자에게 돌아온다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 13. PROTECTED BOUNDARIES
> ━━━━━━━━━━━━━━━━━━━━
>
> 명시적 승인 없이:
>
> - canonical merge
> - Frozen semantics 변경
> - Holdout 소비
> - PIT/no-lookahead 완화
> - Official/LIVE 승격
> - 유료 결제
> - 다른 owner의 protected contract 임의 변경
>
> 을 하지 않는다.
>
> Global Handoff는 Primary Integration Writer 권한을 따른다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 14. COMPLETION CONDITION
> ━━━━━━━━━━━━━━━━━━━━
>
> 이번 작업은 다음 중 하나까지 계속한다.
>
> A.
> 6개 Chart blocker 중 owner evidence로 실제 blocker가 감소
>
> B.
> 각 blocker가 정확한 owner에게 routing되고
> machine/checkable acceptance artifact가 준비됨
>
> C.
> Integration/FPIA의 실제 D3가 남아 사용자 결정 필요
>
> 단순히:
>
> "Chart는 6개 blocker를 기다리고 있다"
>
> 라고 다시 보고하고 종료하지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 15. FINAL REPORT
> ━━━━━━━━━━━━━━━━━━━━
>
> 다음 순서로 보고한다.
>
> 1. Fresh canonical / Global / Integration HEAD
> 2. FPIA 현재 상태
> 3. Chart #41 현재 HEAD
> 4. 6 blocker owner-routing matrix
> 5. 이번에 즉시 해결한 blocker
> 6. owner에게 전달한 action
> 7. 병렬 진행 중인 owner action
> 8. 남은 blocker count
> 9. FPIA D3/G7/GIE 상태
> 10. Chart automation gap 처리 결과
> 11. Chart Work 자동 재개 조건
> 12. 새로운 USER_D3_REQUIRED
> 13. next exact integration step
>
> 마지막에 반드시 답한다.
>
> - Chart blocker가 6개에서 몇 개로 줄었는가?
> - 줄지 않았다면 각 blocker를 실제로 누가 해결 중인가?
> - Chart Work가 다시 자동/수동 재개되어야 하는 정확한 trigger는 무엇인가?
> - 사용자 결정 없이 지금 더 진행할 수 있는 Integration 작업이 남아 있는가?
>
> 사용자 결정 없이 진행 가능한 일이 남아 있다면 자동으로 계속 진행한다.

Recorded effect (routing writer's reading; the user wording above governs):

- The Integration Work routes each of Chart PR #41's six production blockers to its authoritative owner with an exact, machine-checkable request and acceptance criteria, verifies any artifact that already exists in the repository for Chart compatibility, and does not implement Chart features or duplicate another owner's implementation.
- Fixed meanings for the routing: the Strategy Theme is a user-defined Strategy Theme / Portfolio Bucket, not GICS, and the economic meaning of the four buckets (반도체 장비 30, AI·반도체 25, Big Tech 20, 기타산업 25) is not changed; a Chart-side Decimal sum of 100.000% does not make an authoritative root; security identity reuses Issuer → Security → dated Listing and ticker-only identity is not accepted; no Chart-only identity layer; Product authority is separate from source/data rights, and the Product/P01 owner answers the applicability question with A, B or C.
- Blocker 6 (FPIA governance/admissibility) is the Integration critical path. Items previously labelled D3 are not re-asked when CDR-015 already delegates them.
- **Protected boundaries (§13) for this Work.** CDR-015 delegated canonical merges, numeric configuration, publication and deployment as D2; §13 of this later directive lists canonical merge, a Frozen semantics change, Holdout consumption, PIT/no-lookahead relaxation, Official/LIVE promotion, paid payment and arbitrary change of another owner's protected contract as actions not taken without explicit approval. Until the user reconciles the two, the Primary Integration Writer applies the narrower rule: none of those actions is taken in this Work without an explicit user approval naming it. CDR-015 otherwise stays in force (D1/D2 self-decision for everything else, D3 = cost).

## CDR-017 · Claude Main = Primary Integration Coordinator for all audit/implementation Works (standing)

| Field | Value |
|---|---|
| Status | **USER_DECIDED** (standing operating directive) |
| Decided at | 2026-10-05 13:05 KST (2026-10-05T04:05Z; user message in session `session_019znshzTYgyBnuuBmSxdPFN`, after CDR-016 / `5e33b30`) |
| Relates to | CDR-001 (Worker Contract routing), CDR-015 (authority), CDR-016 (Chart routing, protected boundaries) |

User wording (verbatim):

> Investment-System1 Claude Main / Integration Work를 앞으로 전체 감사·구현 Work의
> Primary Integration Coordinator로 계속 운영한다.
>
> 이 지시는 QGV / Chart / Product Platform 작업을 Main이 중복 구현하라는 뜻이 아니다.
>
> 각 scoped Work는 자기 영역을 독립적으로 계속 진행하며,
> Claude Main의 책임은 scoped Work 사이의 cross-owner dependency를 실제로 해소하고,
> Global Handoff와 Integration/FPIA를 통해 전체 시스템이 앞으로 진행되게 만드는 것이다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 1. FRESH GITHUB FIRST
> ━━━━━━━━━━━━━━━━━━━━
>
> 매 실행/재개 시 실제 GitHub를 fresh-read한다.
>
> 최소 확인:
>
> - canonical/default + exact HEAD
> - integration/global-handoff-v1
> - GLOBAL_CURRENT_HANDOFF
> - GLOBAL_STATUS_INDEX
> - COORDINATION_DECISION_REGISTER
> - Decision / Approval / Evidence / Conflict registers
> - Integration/FPIA scoped handoff
> - QGV scoped handoff
> - Chart scoped handoff
> - Product Platform scoped handoff
> - Portfolio/Identity handoff
> - Product/P01 handoff
> - Web handoff
> - open PR / Actions / reviews
> - owner branch/HEAD
> - active lease/write-set
>
> 실제 GitHub와 명시적 사용자 approval/decision evidence를
> 과거 대화나 오래된 Handoff보다 우선한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 2. PRIMARY ROLE
> ━━━━━━━━━━━━━━━━━━━━
>
> Main은 다음을 담당한다.
>
> 1. cross-owner dependency routing
> 2. Global Handoff coordination
> 3. Integration/FPIA
> 4. owner write-set 충돌 방지
> 5. scoped Work 결과의 integration readiness 판정
> 6. D1/D2 자동 진행 조율
> 7. 실제 D3만 사용자에게 escalation
> 8. canonical integration 준비
>
> Main은 각 scoped Work의 전문 업무를 불필요하게 다시 수행하지 않는다.
>
> 예:
>
> QGV scoring 연구
> → QGV Work 소유
>
> Chart contract/rendering
> → Chart Work 소유
>
> Auth/Tenant/Connector/Reconciliation
> → Product Platform Work 소유
>
> Portfolio Target
> → Portfolio owner
>
> Security/Listing identity
> → Identity owner
>
> Product publication authority
> → Product/P01 owner
>
> Main은 이들을 연결한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 3. THREE CONTINUOUS AUDIT WORKS
> ━━━━━━━━━━━━━━━━━━━━
>
> 현재 다음 세 Work가 독립 자동진행 중인 것으로 취급한다.
>
> A. QGV 구조 재감사
> B. Chart 구현 감사
> C. Product Platform 구현 감사
>
> 각 Work의 최신 scoped Handoff를 dependency input으로 사용한다.
>
> 각 Work에서:
>
> OWNER_ACTION_REQUIRED
>
> 가 발생하면 단순 기록하고 기다리지 않는다.
>
> Main이 authoritative owner를 확인하고 해당 owner에게 routing한다.
>
> 가능하면 machine/checkable receipt / evidence / acceptance criteria 형태로 전달한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 4. OWNER ROUTING LOOP
> ━━━━━━━━━━━━━━━━━━━━
>
> 각 OWNER_ACTION_REQUIRED에 대해:
>
> Finding
> ↓
> Authoritative Owner
> ↓
> Required Artifact
> ↓
> Exact Path / PR / Branch
> ↓
> Acceptance Criteria
> ↓
> Owner Action
> ↓
> Evidence Receipt
> ↓
> Scoped Work 재소비
> ↓
> Blocker 재판정
>
> 루프를 유지한다.
>
> "다른 owner가 해야 한다"
>
> 라고 기록하는 것만으로 완료 처리하지 않는다.
>
> 실제 routing 또는 owner-consumable handoff packet까지 만든다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 5. GLOBAL-ONLY CHANGE PROPAGATION
> ━━━━━━━━━━━━━━━━━━━━
>
> 중요:
>
> 어떤 dependency 변화가 owner PR HEAD 변경 없이
> Global Handoff / Status / Decision Register에만 기록될 수 있다.
>
> 이 경우에도 영향받는 scoped Work가 이를 소비할 수 있도록 routing한다.
>
> 특히:
>
> - QGV decision/approval
> - Chart Portfolio/Identity/Product/FPIA dependency
> - Platform Auth/Tenant/Connector dependency
>
> 의 material semantic delta를 확인한다.
>
> 모든 Global commit을 모든 Work에 broadcast하지 않는다.
>
> 해당 Work의 blocker/dependency에 실제 영향을 주는 변화만 전달한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 6. CHART CURRENT ROUTING
> ━━━━━━━━━━━━━━━━━━━━
>
> Chart PR #41의 최신 scoped handoff를 fresh-read한다.
>
> 마지막 확인 기준 Lane A에는 다음 6 gate가 있었다.
>
> 1. authoritative TARGET root
> 2. Security mapping
> 3. Theme revision/version
> 4. Product authority
> 5. owner write-set acceptance
> 6. FPIA governance/admissibility
>
> 이를 최신 evidence로 다시 확인한다.
>
> 각 gate의 owner를 명시적으로 routing한다.
>
> 예상 ownership은 참고일 뿐이며 fresh-read가 우선한다.
>
> TARGET root
> → Portfolio
>
> Security mapping
> → Identity
>
> Theme revision
> → Portfolio / Classification
>
> Product authority
> → Product/P01
>
> write-set
> → Web/Product/Integration
>
> FPIA
> → Integration
>
> 기존 사용자 결정으로 D3→D2 범위가 완화된 항목은
> 과거 D3 상태를 관성적으로 유지하지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 7. QGV ROUTING
> ━━━━━━━━━━━━━━━━━━━━
>
> QGV Work의 최신 unresolved items를 읽는다.
>
> 예:
>
> - Missing-Data
> - requiredness/applicability
> - method/version identity
> - G 3–5Y
> - EPS→FCF
> - V normalization/metadata
> - Composite
> - WeightOverride
>
> QGV Work 자체가 수행 가능한 연구/감사/검증은 맡기고,
> 다른 owner consumer/integration dependency만 Main이 routing한다.
>
> QGV production semantics를 Main이 임의로 결정하지 않는다.
>
> 실제 numeric/method/policy D3만 사용자에게 올린다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 8. PRODUCT PLATFORM ROUTING
> ━━━━━━━━━━━━━━━━━━━━
>
> Product Platform Work의 최신 capability matrix와 blockers를 읽는다.
>
> 범위:
>
> - Auth
> - Tenant isolation
> - Financial Connector
> - financial record sync/import
> - Reconciliation
> - immutable/auditable records
> - Read-only hard gate
> - Product API
> - Web/PWA
> - investment-engine integration
>
> 보안/tenant/read-only 문제는 fail-closed로 처리한다.
>
> Platform Work에서 다른 owner dependency가 발견되면
> Main이 routing한다.
>
> 실제 credential/금융계정/production auth/유료 connector는
> 사용자 승인 없는 자동 진행 대상이 아니다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 9. D1 / D2 / D3
> ━━━━━━━━━━━━━━━━━━━━
>
> 현재 승인된 authority policy를 fresh-read하여 적용한다.
>
> D1:
> 자동 진행
>
> D2:
> 근거·검증·복구계획을 남기고 보수적으로 자동 진행
>
> D3:
> 실제 사용자 결정 필요
>
> 과거 D3 label만 보고 멈추지 않는다.
>
> 최신 Decision Register에서 D2로 재분류되었으면 자동 진행한다.
>
> 반대로 protected semantic 변경을 D2로 임의 낮추지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 10. INTEGRATION / FPIA
> ━━━━━━━━━━━━━━━━━━━━
>
> FPIA는 Main의 핵심 책임이다.
>
> 구분:
>
> - implementation
> - CI
> - independent review
> - adversarial review
> - governance closure
> - GIE closure
> - canonical applicability
> - exact merge-result FPIA
>
> CI PASS만으로 전체 closure를 선언하지 않는다.
>
> 발견된 우회/환경 의존성은 승인 범위에서:
>
> repair
> → targeted regression
> → full/affected regression
> → independent/adversarial verification
> → evidence
> → closure
>
> 까지 자동 진행한다.
>
> 실제 D3만 사용자에게 escalation한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 11. LEASE / CONCURRENCY
> ━━━━━━━━━━━━━━━━━━━━
>
> 각 scoped Work/owner branch의 lease를 존중한다.
>
> active writer가 있으면 같은 branch에 쓰지 않는다.
>
> Main이 다른 owner branch를 직접 덮어쓰지 않는다.
>
> Global Handoff는 Primary Integration Writer 규칙을 따른다.
>
> force push / history rewrite 금지.
>
> 장시간 CI를 기다리며 write lease를 붙잡지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 12. AUTO-CONTINUATION
> ━━━━━━━━━━━━━━━━━━━━
>
> 사용자에게 매 단계마다 "계속할까요?"라고 묻지 않는다.
>
> D1/D2 범위에서:
>
> - routing
> - retry
> - repair
> - retest
> - regression
> - evidence collection
> - review
> - owner handoff
> - dependency propagation
> - integration trial
>
> 은 자동으로 계속한다.
>
> 한 Work가 D3에 막혀도 다른 독립 Work와 owner routing은 계속한다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 13. COMPLETION CRITERION
> ━━━━━━━━━━━━━━━━━━━━
>
> Main의 성공 기준은 문서량이나 PR 수가 아니다.
>
> 다음이 개선되어야 한다.
>
> - unresolved owner dependencies ↓
> - duplicate work ↓
> - stale WAITING ↓
> - D1/D2 autonomous completion ↑
> - cross-owner propagation ↑
> - integration readiness ↑
> - production blockers ↓
>
> scoped Work가 OWNER_ACTION_REQUIRED를 반복해서 보고하는데
> 아무 owner도 실제 action을 받지 않는 상태를 허용하지 않는다.
>
> ━━━━━━━━━━━━━━━━━━━━
> 14. REPORT
> ━━━━━━━━━━━━━━━━━━━━
>
> 의미 있는 변화가 있을 때 다음만 보고한다.
>
> 1. canonical / Global exact HEAD
> 2. Integration/FPIA 상태
> 3. QGV blockers / owner routing
> 4. Chart blockers / owner routing
> 5. Platform blockers / owner routing
> 6. 이번에 해결된 dependency
> 7. 진행 중 owner actions
> 8. D1/D2 자동 진행 결과
> 9. 실제 USER_D3_REQUIRED
> 10. 다음 critical path
>
> No material change면 불필요한 장문 보고를 만들지 않는다.
>
> 최종 원칙:
>
> Scoped Work는 전문 업무를 수행한다.
> Claude Main은 서로 연결한다.
> OWNER_ACTION_REQUIRED는 routing한다.
> D1/D2는 자동 진행한다.
> 실제 D3만 사용자에게 돌아온다.
> Global Handoff는 전체 시스템의 dependency routing SSoT 역할을 한다.

Recorded effect (routing writer's reading; the user wording above governs):

- The Integration / Claude Main Work is the Primary Integration Coordinator: cross-owner dependency routing, Global Handoff coordination, Integration/FPIA, write-set conflict prevention, integration-readiness judgement of scoped results, D1/D2 coordination, escalation of real D3 only, and canonical integration preparation. It does not redo scoped Works' specialist work (QGV scoring research, Chart contract/rendering, Product Platform auth/tenant/connector/reconciliation, Portfolio Target, Security/Listing identity, Product publication authority).
- Three continuous audit Works are treated as running independently: QGV structural re-audit, Chart implementation audit, Product Platform implementation audit. Every OWNER_ACTION_REQUIRED they report is routed to its authoritative owner as an owner-consumable, machine-checkable packet and tracked through the loop Finding → Owner → Artifact → Path → Acceptance → Owner action → Evidence receipt → Scoped re-consumption → Blocker re-judgement. Recording "another owner must act" alone does not close an item.
- The Global Handoff is the dependency-routing SSoT. Material semantic deltas recorded only on the Global branch are propagated to the affected scoped Work through a channel it consumes; non-material Global commits are not broadcast.
- QGV production semantics are not decided by Main; QGV research/audit/verification stays with the QGV Work. Product Platform security, tenant and read-only issues fail closed; real credentials, financial accounts, production auth and paid connectors are not progressed automatically without user approval.
- D1/D2/D3 follow the current authority policy (CDR-015 as narrowed by CDR-016 §13 and this entry); a past D3 label is not a reason to stop, and a protected semantic change is not lowered to D2.
- Leases and concurrency: active writers' branches are not written; no other owner's branch is overwritten; no force push or history rewrite; no write lease is held while waiting on long CI.


## CDR-018 · User-directed GPT Work Main transfer (coordination only)

- Status: USER_DECIDED; recorded at 2026-10-05T13:35:27+09:00.
- Source: current user message, received 2026-10-05T13:31:19+09:00, plus explicitly applied attachment preserved at `evidence/main_takeover_2026-10-05/USER_EXECUTION_DIRECTIVE.md` (SHA-256 `e82ca6832c553f1f4cb7bf12c9a5e657e5d9b2b892c659417ef35ebc664f8667`).
- User wording (verbatim):

> 첨부 파일을 실행 지시로 적용해 Claude Main의 통합 담당 역할을 인수하고 계속 진행해. 최신 GitHub부터 확인하고, 이전 writer와의 충돌을 방지한 뒤 FPIA·owner routing·자동 재개를 이어가.

Effect, within the attachment's exact scope:

- This GPT Work (`gpt-work-main-2026-10-05-3a80dcef6444`) is the designated successor Primary Integration Coordinator / Primary Integration Writer. Previous session `session_019znshzTYgyBnuuBmSxdPFN` must not automatically resume shared integration writes; it must fresh-read this transfer and route unpublished outputs to the successor. This is an authority transfer, not proof that an external runtime/scheduler was terminated.
- Inherited Global exact HEAD `b3532a2ebbe95310bbf222937466eb04a0211263`. Fresh remote checks agreed; no active Global lease artifact or accessible old Main automation was found. One FPIA Actions audit (37260997788, attempt 1, 11d2f25) was still running; that job audits, it does not authorize a second writer. Claude internal runtime/scheduler and unpublished scratch remain UNAVAILABLE/UNKNOWN.
- Publish only a descendant of the immediately re-read Global parent with non-force ref advancement. A remote movement is a conflict requiring fresh reconciliation; never overwrite another update. Long CI holds no shared write lease. Other owners' scopes, leases and independent automations are preserved.
- CDR-015 D1/D2 remains narrowed by CDR-016 §13 and CDR-017. No canonical merge, Frozen semantic rewrite, Holdout, PIT relaxation, Official/LIVE, protected owner contract changes, real account/credential/production-auth activation, paid resources or trade execution is newly approved by this transfer. Main does not decide QGV production semantics.
- Routing comments/packets on relevant repository owner PRs and new Main-only automatic continuation are authorized by attachment §§8–9. Delivery is not receipt; activation is not end-to-end execution.


## CDR-019 · Supplemental tool use and first-use constraints

- Status: USER_DECIDED; recorded 2026-10-05T14:32:45.200094+09:00.
- Source: two current user directives, preserved verbatim in `evidence/main_tools_2026-10-05/USER_TOOL_USAGE_DIRECTIVES.md`; SHA-256 `c29ae2c08e97dd28414fb8d8e17f33d275a5fd9b1607bf2441d6fc312ce1a25e`. They apply at the existing safe checkpoint and do not restart completed work.
- Effect: GitHub remains code/contract/approval/evidence authority. Verify callable tool access and exact service target; connection is not a configured project or completion. Context7 uses actual dependency versions; Superpowers applies only the current debugging/test/review phase; Linear first reads existing projects/issues and does not invent a target or close a GitHub gate. First use states purpose, target and read/write scope.
- CDR-015 D1/D2 as narrowed by CDR-016 §13/CDR-017/CDR-018 remains unchanged. No new owner takeover, protected scope, paid resource, real credential/auth, tenant-policy change, backend replacement or deployment authority. Figma/MagicPath use one design authority per screen when an actual task needs it. Independent authorized work proceeds if an optional service target is unavailable.
- Applied evidence: Context7 exact-version primary-doc fallback, read-only Linear discovery with no repository project found, current PIW-D002 TDD/review only; no redesign, full-audit repeat or new service resource.


## CDR-020 · Main blocker closure and canonical convergence directive

- USER_DECIDED; recorded2026-10-05T15:33:50.329322+09:00. Source: current user Main convergence directive after7a29 checkpoint. Continue existing project; exact GitHub wins over referenceSHA. Priority#46exactCI/artifact/verifier receipt chain; consume Platform/Web/Chart/QGV owner returns without duplicateimplementation or spam; prepare exact owner set,merge ordering and postmerge checks. Canonical remains user decision. OldHEADPASS is not currentHEADPASS. Currentcandidate/receipt pins are in evidence/main_convergence_2026-10-05/. Protectedowner scopes and current D3 limits unchanged.

## CDR-021 · Verification & Execution Acceleration Policy v1.0

- USER_DECIDED; recorded2026-10-05T15:33:50.329322+09:00. Source: current user24-section policy, operational summary evidence/main_convergence_2026-10-05/EXECUTION_POLICY.md (explicitly nonverbatim). Applied at safe existing checkpoint, no architecture restart. FAST targeted, STANDARD proportional targeted/negative/affected/integration,max1verifier, CRITICAL rigorousfailclosed/proportionate. Valid exact specialist audits reused asAUDIT_VERIFIED_EXTERNAL; no default duplicateaudit/fullregression/completeness panels. Default1owner,+1verifierwhenneeded. Main implementation/integration; QGV/Platform/Chartspecialistaudits andClaudeindependentmonitor remain distinct. Netblockerreduction tracked with scope; no findings/comment/agent count ascompletion. CDR-015 narrowed016§13/017/018 qualityfloors,ownership and D3boundaries remain. Existing validownerwork preserved; no newapprovals or paid/productionactivation.

## CDR-022 · SSoT Autonomous Execution Loop v1.0

- USER_DECIDED; source current user25-section directive received2026-10-05T16:15:56+09:00; recorded2026-10-05T07:22:30.181Z. This operational summary is not a verbatim quote. Existing SSoT/owner contracts/authority and risk-proportional CDR-021 remain; no new architecture or protected authority.
- Main runs FRESH_READ→RECONCILE→DISCOVER_READY→PRIORITIZE→EXECUTE→VERIFY→PUBLISH→UPDATE_SSoT→RE_EVALUATE→NEXT_READY. Repository/scoped evidence beats historical dialogue; classify CURRENT/STALE/SUPERSEDED/HISTORICAL/UNVERIFIED/CONFLICTING. Preserve initial failures; reuse valid exact input/hash/scope evidence.
- Discover READY/WAIT_DEPENDENCY/D3_REQUIRED/DONE/SUPERSEDED/INVALID. Shared/critical/security blockers and owner-return closure outrank docs. One blocked lane does not stop independent READY lanes. D1/D2 implementation, repair, retry, receipt/CI consumption, integration and handoff require no further user permission. Ownership, leases and non-force publication remain; no duplicate implementation/audit/polling.
- WAIT/STOP only if acceptance complete, real D3/system blocker, or READY=0 across independent lanes, bounded repair, immediate owner return/terminal CI consumption and pending SSoT closure. Checkpoint publication itself is not a stop condition. WAIT identifies exact owner/run/decision dependency and material resume trigger. Return status SENT→ACKNOWLEDGED→IN_PROGRESS→RETURNED→INDEPENDENTLY_VERIFIED→CONSUMED→CLOSED is scope-specific; delivery never implies receipt/execution.
- Main maintains integration convergence/canonical candidate; Chart/Platform/QGV keep scoped implementation/decision authority. Real D3 boundaries, fail-closed security/PIT/Frozen/provenance/financial integrity/read-only, canonical user decision, no trading/credentials/paid activation remain unchanged.


## CDR-023 · D3 Delegated Approval Policy v1.0

- Status: USER_DECIDED_EXPLICIT_DIRECTIVE. Recorded 2026-10-05T09:23:18Z; user submission timestamp not available, not fabricated.
- Source: exact [user directive](evidence/main_d3_delegation_2026-10-05/USER_DIRECTIVE.md), SHA-256 `07580cceb0e3f9cc8a6f9ecf84d298e208685fae1812a99d64db74361a6886a1`.
- Effective operational classification is **D1 / D2 / D3-A / D3-R**. This supersedes conflicting unqualified CDR-015 “D3 = cost only” live summaries, preserving all prior entries and narrowing CDR-016§13/017/018 owner and Main boundaries.
- D3-A requires all ten conditions with concrete approved goal/Architecture/SSoT/Decision Register pins; reasonable appearance alone is insufficient. Unknown alignment or any reserved exclusion is D3-R. No wholesale product/methodology authority is granted.
- D3-A loop: CLASSIFY → AUTO-APPROVE → EXECUTE → VERIFY → DECISION RECEIPT → UPDATE SSoT → RE-EVALUATE → CONTINUE. Do not ask repeated approval for an evidenced design-aligned decision. Receipt requires decision, approved SSoT/authority, alternatives, alignment, protection preservation, verification and rollback.
- Reserved: all twelve categories in the verbatim directive; paid resources; actual trades/orders/funds; real financial credentials/expanded rights; Holdout first/reuse; Official/LIVE; PIT/no-lookahead relaxation; destructive Frozen/history/evidence; security/Tenant weakening; irreversible deletion/migration; new material QGV/13F/backtest/investment methods or numeric thresholds/defaults/cutoffs/weights; unproven alignment. Main still cannot trade/order/transfer funds.
- One D3-R dependency waits only its lane; independent D1/D2/D3-A and owner intake continue. Former D3-a–e/G7 decisions already disposition-decided under PIW-D001…D006 are not reopened; missing independent evidence or owner acceptance remains a dependency, not fabricated approval.
- No canonical merge is authorized: later explicit Main protected restriction and exact-result acceptance remain. No owner write-set/lease/grant transferred. New Main D3-A approvals in this intake: 0; one existing owner Chart SAMPLE fallback D3-A consumed within presentation-only scope.
- Decision Receipt / verification: [PIWD-013](evidence/main_d3_delegation_2026-10-05/DECISION_RECEIPT.json), [verification](evidence/main_d3_delegation_2026-10-05/VERIFICATION.json).

User wording (verbatim):

> Investment-System1 — D3 Delegated Approval Policy v1.0
> 기존 D1/D2/D3 체계를 D1 / D2 / D3-A / D3-R로 확장한다.
> **D3-A(Design-Aligned Delegated Approval)**는 사용자가 이미 승인한 제품 목표, Architecture, SSoT, Decision Register, 보호원칙과 실질적으로 같은 방향의 결정을 의미한다. 다음 조건을 모두 충족하면 별도 사용자 재승인 없이 자동 승인·실행한다.
> 기존 승인된 목적과 설계 방향을 유지한다.
> 새로운 투자방법론·경제적 의미·점수 의미를 만들지 않는다.
> 기존 보호경계를 완화하지 않는다.
> PIT/no-lookahead/provenance/Frozen/history를 약화시키지 않는다.
> 보안·Tenant·금융계정 권한을 확대하지 않는다.
> 실제 매매·주문·자금이동을 발생시키지 않는다.
> 기존 evidence/history를 삭제·rewrite하지 않는다.
> 합리적으로 rollback 가능하다.
> deterministic 또는 독립 검증이 가능하다.
> 복수 선택지가 있으면 기존 SSoT와 가장 정합적이고 보수적인 방법을 선택한다.
> D3-A로 판정하면:
> CLASSIFY → AUTO-APPROVE → EXECUTE → VERIFY → DECISION RECEIPT → UPDATE SSoT → RE-EVALUATE → CONTINUE
> 로 처리한다.
> 사용자에게 “승인할까요?”라고 다시 묻지 않는다.
> Decision Receipt에는 최소한 결정, 근거가 된 기존 SSoT/승인, 대안, 설계정합성, 보호경계 보존 여부, 검증 결과, rollback 가능성을 기록한다.
> **D3-R(Reserved)**은 사용자 승인을 유지한다. 다음은 자동승인하지 않는다.
> 유료 결제 또는 새로운 유료 자원
> 실제 매매·주문·자금이동
> 실제 금융기관 credential 제공 또는 권한 확대
> Holdout 최초 소비 또는 재소비
> Official/LIVE 승격
> PIT/no-lookahead 완화
> Frozen/history/evidence의 파괴적 변경
> 보안·Tenant isolation 완화
> irreversible delete/migration
> QGV/13F/백테스트/투자판단 결과의 의미를 실질적으로 변경하는 새로운 방법론
> 새로운 numeric threshold/default/cutoff/weight 등 결과를 실질적으로 변경하는 수치정책
> 기존 SSoT만으로 설계 정합성을 입증할 수 없는 결정
> 중요: 단순히 합리적으로 보인다는 이유만으로 D3-A로 분류하지 않는다. 기존 SSoT/Decision Register/승인된 Architecture와의 정합성을 구체적인 evidence로 입증할 수 있어야 한다. 불확실하면 D3-R이다.
> D3-R이 한 lane에서 발생해도 Work 전체를 중지하지 않는다. 해당 dependent lane만 WAIT시키고 독립적인 D1/D2/D3-A를 계속 실행한다.
> 기존 D3 중 이미 pending인 항목도 fresh SSoT에서 재분류한다. 기존 설계방향을 단순 구체화하는 항목이면 D3-A로 전환하여 자동 처리하고, Reserved 조건에 해당하는 것만 D3-R로 유지한다.
> 이 정책은 새로운 제품·투자방법론을 승인하는 포괄 위임이 아니다. 사용자가 이미 결정한 설계 방향을 반복 승인하는 병목을 제거하기 위한 delegated authority다.
> 목표는:
> Human approval frequency ↓
> Autonomous completion ↑
> Protection boundary 유지
> Decision traceability 유지
> 이다.

## CDR-024 · Autonomous Execution & Decision Authority SSoT v1.1 adoption

- Status: **USER_DECIDED / ADOPTED_COMMON_SSOT**
- Recorded: 2026-10-05
- Class: **D3-R — explicit user adoption**
- Scope: Common autonomous execution / decision-authority governance for Main, Chart, QGV, Product Platform and future participating Works.
- Supersedes operationally: PR #48 v1.0 proposal and CDR-023 policy details where v1.1 is more specific. CDR-023 history is retained; its D1/D2/D3-A/D3-R principle remains incorporated by v1.1.
- Adopted file: implementation/docs/coordination/policies/Investment-System1_Autonomous_Execution_Decision_Authority_SSoT_v1_1.md
- Adopted file blob: 89b48bca0aeeff54bdc0fc97d6ee768e5f0e326c
- Historical v1.0 file: implementation/docs/coordination/policies/AUTONOMOUS_EXECUTION_DECISION_AUTHORITY_SSoT_v1.0.md — retained and marked SUPERSEDED; body/history not deleted.
- PR: #48, branch governance/autonomous-execution-decision-authority-v1.

User wording (verbatim):

> Status: ADOPTED COMMON SSoT (v1.1)

The immediately preceding user directive also stated:

> 깃헙ssot 루프를 업데이트하자

Decision:

- Adopt Autonomous Execution & Decision Authority SSoT v1.1 as the common operational governance SSoT.
- Confirm operating values without future re-question unless a D3-R change is proposed:
  - cycle maximum tasks = 5;
  - lease TTL = 2 hours;
  - lease deadlock escalation = TTL × 2;
  - repair/retest cap = 3 rounds;
  - D3-A Digest window = 10 decisions or 1 week, whichever occurs first;
  - same module/contract D3-A cap = 5 per Digest window;
  - rolling pattern display = previous 3 windows;
  - veto window = 72 hours;
  - dependent D3-A chain depth during veto = 3;
  - per-cycle token budget remains unset until observable and separately user-decided.
- Unattended autonomous execution remains disabled until PART G Gate A is satisfied. User-observed/session execution may follow v1.1 immediately.
- Watchers are read-only wake-up mechanisms, not executors; watcher failure must not mutate Work ownership/state.
- TTL expiry alone never authorizes lease takeover.
- D3-A requires SSoT alignment, rollbackability, semantic_delta classification and independent re-adjudication; conservative synthesis governs.
- Hard-Guard states are evidence-based. NOT_VERIFIED / NOT_IMPLEMENTED are Hard-Guard Gaps and become blocking only at their defined Gate, unless G2 immediate-blocker evidence is actually observed.
- Existing pending D3 decisions are to be reclassified under §§25, 26A and 26F. D3-R blocks only dependent lanes; independent D1/D2/D3-A work continues.
- No canonical merge, Holdout consumption, Official/LIVE promotion, production deployment, paid-resource use, real credential activation, trade/order/fund transfer, PIT relaxation, Frozen/history destruction or protected owner takeover is authorized by this adoption itself.

Follow-ups:

1. Register PART G G3 hard-guard gaps with evidence-based states.
2. Reclassify open D3 decisions under v1.1.
3. Verify Gate A controls before enabling unattended AUTONOMY_MODE=RUN.
4. Pilot one lane for 1–2 weeks and adjust only from operational evidence; operating-value changes remain D3-R.

## CDR-025 · CDR-024 execution receipt — PR #48 merged to Global

- Status: **EXECUTED / APPEND_ONLY_FOLLOW_UP**
- Recorded: 2026-10-05
- Class: D1 execution receipt under CDR-024; no new policy authority.
- PR #48 merge result: `82de599ee90a6beabd774dd22e7e2b939ff75b44`.
- Global branch after merge: `integration/global-handoff-v1` @ `82de599ee90a6beabd774dd22e7e2b939ff75b44`.
- Canonical/default branch remains `claude/investment-system-top500-validation-alrugm` @ `b8e39a2196a6d7794a04a0cd5393c68329e126ca`.
- PR #48 final head before merge: `1d2c8195ffb936c56ba91d9fe41e627ef172a5e7`.
- Global sync merge on governance branch: `18e79a9a320b2a7b21a9fa2daad95d4e5d6eb5b3`.
- Three-file governance diff revalidated before merge:
  1. `implementation/docs/coordination/COORDINATION_DECISION_REGISTER.md` — append-only CDR-024.
  2. `implementation/docs/coordination/policies/AUTONOMOUS_EXECUTION_DECISION_AUTHORITY_SSoT_v1.0.md` — historical v1.0 retained and marked SUPERSEDED; original body preserved.
  3. `implementation/docs/coordination/policies/Investment-System1_Autonomous_Execution_Decision_Authority_SSoT_v1_1.md` — adopted v1.1.
- No CDR-024 rewrite is performed by this receipt. This entry records the post-merge exact state append-only.
- No canonical merge, Holdout consumption, Official/LIVE promotion, production deployment, paid-resource activation, real credential activation, trade/order/fund transfer, PIT relaxation, Frozen/history destruction or protected-owner takeover is authorized by this receipt.
- Next execution under CDR-024: register PART G Hard-Guard Gaps and begin pending D3 reclassification under §§25, 26A, 26F.

## CDR-026 · CDR-024 merged-file identity clarification

- Status: **EXECUTED / APPEND_ONLY_CLARIFICATION**
- Recorded: 2026-10-05
- Class: D1 evidence clarification under CDR-024; no new authority.
- CDR-024 is not edited. Its earlier adopted-file blob remains historical pre-merge evidence.
- PR #48 final head: `1d2c8195ffb936c56ba91d9fe41e627ef172a5e7`; Global merge result: `82de599ee90a6beabd774dd22e7e2b939ff75b44`.
- Exact merged-file identities: decision register `4ead1ef620d7b4f5addbb201681242020d0d55ca`; historical v1.0 `425c0b647073c16b021fb501c71b78c2d0248320`; adopted v1.1 `4736bbcb508ce1f4310fbe96cbcfdd8e080b275f`.
- No canonical merge, Holdout, Official/LIVE, production, paid resource, credential, financial operation, PIT relaxation, Frozen/history destruction, protected-owner takeover, or QGV production-semantic authority is granted.

## CDR-027 · One observed-session bounded Chart owner-dependency cycle

- Status: USER_DECIDED_EXPLICIT_DIRECTIVE; recorded 2026-10-06T09:38:20Z. Submission timestamp is not independently provided; this is the receipt time.
- Scope: current six Chart OPEN gates, Main integration coordination only; CDR-024 v1.1 applies.
- User explicitly authorizes acting on their behalf to change READ_ONLY → RUN for this one session and to restore READ_ONLY at completion/WAIT_DEPENDENCY/D3-R/tool blocker. This scoped instruction overrides §4A's agent-mutation prohibition only for these two user-directed transitions. It does not enable unattended RUN or satisfy Gate A.
- Maximum five tasks, lease TTL two hours, maximum three repairs for an identical failure; no stale takeover. Recheck mode before publication.
- Portfolio/Identity/Theme owner claims and exact branch/write-set; TARGET/19 Security/Theme returns; P01 applicability; Web/Integration acceptance; FPIA governance and independent verifier/launcher/runtime/GIE; routing/reconciliation/verification/evidence/handoff are authorized within existing protection boundaries.
- Prohibited: canonical merge, Official/LIVE, Holdout, PIT/no-lookahead relaxation, destructive Frozen/history/evidence, credential/rights expansion, paid resources, trades/orders/funds.
- Verbatim user directive: [USER_DIRECTIVE.md](evidence/main_chart_owner_cycle_2026-10-06/USER_DIRECTIVE.md).
- No source owner acceptance, source admission, Product grant or production gate closure is implied by this mode receipt.

## CDR-028 · CDR-027 bounded cycle execution receipt and READ_ONLY restoration

- Recorded 2026-10-06T09:49:45.650Z; D1 execution receipt only, no new authority. User directive and CDR-027 preserved verbatim.
- Activation Global commit `80c4d823a1062b569a5c3f3655570b67bcd5ed64`; immutable packet `2cda490a93bd2c093ff07557af4fe748964c20c1`; final containing commit resolves from Git metadata, not recursive self-embedding.
- Five bounded tasks: source-owner claim intake #54; P01 applicability; three-asset Web/Integration reconfirmation; candidate FPIA source/runtime evidence; verification/routing/handoff/control restoration.
- Four new PR routing comments exact readback verified; source issue exact readback verified. Source owner claims/closing returns0, production gates closed0/remaining6. Proposals and delivery do not establish owner assignment, authority, execution or product acceptance.
- Current verifier/workflow33 selected blobs agree; run/attempt/job/artifact digest and actual workflow8479/subject7215 observed. Independent acceptance, external coverage, GIE and Chart assembled-subject FPIA remain open.
- User-directed end-of-cycle restoration to READ_ONLY and release of this Main lease are atomic in the containing publication. No other lease/ref/automation/canonical/production/protected/financial operation changed.
- [Final receipt](evidence/main_chart_owner_cycle_2026-10-06/FINAL_RECEIPT.json), [handoff](evidence/main_chart_owner_cycle_2026-10-06/HANDOFF.md).


## CDR-029 · Explicit user-observed Main five-task session mode grant · 2026-10-07

- User answered “계속 진행해” to the exact preceding five-task RUN/restoration permission question at 2026-10-07T19:45:52+09:00. Preserve [exchange](evidence/main_single_control_cycle_2026-10-07/USER_SESSION_APPROVAL.md).
- On the user's behalf, READ_ONLY→RUN is authorized for this one observed Main cycle only; restore READ_ONLY at completion/task cap/WAIT/D3-R/tool blocker. This is the same narrow §4A exception pattern as CDR-027, with a new explicit session decision; CDR-027/028 are not reused as current permission.
- Maximum five tasks; own lease TTL two hours; same-failure repair maximum three; no stale recovery. Recheck mode and exact parent before each publish. Unattended executor false; Gate A unchanged.
- Authorized next cycle: Single-Control adoption, eligible evidence-owner/write-set assignment, operational-return consumption, inactive Phase A contracts, scoped verification/evidence/handoff. No protected/canonical/production/scoring/financial/Holdout/paid permission is created.


## CDR-030 · Main Single-Control Execution Policy v1.0 adoption

- Status: USER_OPERATIONAL_DECISION_ADOPTED, history-preserving; original [directive](evidence/main_single_control_cycle_2026-10-07/SINGLE_CONTROL_USER_DIRECTIVE.md) retained. [Policy](policies/Investment-System1_Main_Single_Control_Execution_Policy_v1_0.md), [ten scoped reconciliations](evidence/main_single_control_cycle_2026-10-07/SINGLE_CONTROL_RECONCILIATION.json).
- Main is the one observed-session control point. Specialist evidence is reused. Main may directly assign/claim eligible free bounded D1/D2/D3-A tasks; specialist-chat inactivity is not a dependency. Prior routing-only restrictions are superseded only in that exact scope.
- Existing owner branches/contracts/evidence and leases are preserved; QGV qgv-b47-muupb538 expiry=null is not cleared. Evidence-preparation owner assignment does not create TARGET currentness, Security admission, Theme source authority, Product grant, independent trust or production gate closure.
- CDR-024 protections and D3-A proof remain controlling. This policy grants no AUTONOMY_MODE change or Gate A passage; CDR-029 is separate session authority.


## CDR-031 · New user Company Analysis product design intake / inactive Phase A contract

- “QGV Company Analysis UI/UX Extension v1.1” + “Historical Price Context Contract v1.0” accepted as authoritative user product-design input; [structured input](../company_analysis_extension_v1_1/USER_DESIGN_INPUT.json), [Phase A contract](../company_analysis_extension_v1_1/CONTRACT.md), [field contract](../company_analysis_extension_v1_1/FIELD_CONTRACT.json).
- D1 inactive docs-only contract. Preserve three independent classification axes, source/versioned existing Type profiles, same-basis price context, completed-full-period/Flat/QTD/YTD/partial rules, raw-score separation and Overview→Detail→Evidence navigation.
- User candidate drawdown numbers remain inactive display-reference candidates; no episode/peer/scoring/weight/default/cutoff activation. Existing critical paths/evidence/owner leases preserved. No new D3-A execution or runtime/production acceptance is claimed.


## CDR-032 · 2026-10-07T11:09:49.723867+00:00 · CDR-029 bounded observed cycle receipt / READ_ONLY restoration

Execution receipt, no new authority: CDR029 five-taskcycle complete; CDR030 Main Single-Control adopted, CDR031 userdesign/inactivePhaseA preserved. Published source7b27 and Globalpacket74cd; TREE_IDENTICAL/API_NATIVE_COMMIT, no COMMIT_IDENTICAL claim. Three free bounded evidence roles assigned, authoritativeadmission0; Chart6OPEN/0CLOSED/Market0of19. QGV12hashes verified,193checks reused, Platform9blockers; FPIACI7/7 reused, trust/GIEopen. Five exact routing comments verified, no receiving/automaticexecution inference.

Containing publication restores AUTONOMY_MODE=READ_ONLY, own Mainlease=null and runtimeIDLE after freshRUN/lease/exactpacketparent checks. HG01/HG02 VERIFIED, HG03 PARTIAL_VERIFIED; unattended disabled.0D3-A/0D3-R/0productionclosures/0CI dispatch. Oldhistory/evidence and ownerbranches/leases preserved. This receipt does not renew CDR029 modegrant or grant nextcycle runtime execution. Final identity resolves from containingcommit; remote readback follows publication. See evidence/main_single_control_cycle_2026-10-07/FINAL_RECEIPT.json.


## CDR-033 · 2026-10-08T09:35:52.934Z · Explicit observed Main Phase A five-task session grant

User direct Main answer “계속 진행해” at2026-10-08T18:31:26+09:00 approves the previously presented five-task RUN/restoration question; exact exchange retained at evidence/main_company_analysis_cycle_2026-10-08/USER_SESSION_APPROVAL.md. New one-cycle authority; CDR029 expired and is not reused. Main applies READ_ONLY→RUN on user's behalf, owns only bounded new sidecar/module/test scope, restores READ_ONLY at completion/cap/WAIT/D3-R/tool blocker. Gate A remains CLOSED; unattended false. CDR024/030/031 protections, leaseTTL2hours, repair3 and non-force exact-parent publication preserved. Pure isolated supplied-input display adapter/preview is D1/D2; no D3-A activation, source admission, protected semantics or production/canonical approval.


## CDR-034 · 2026-10-08T10:16:33Z · CDR-033 Phase A execution receipt / READ_ONLY restoration

Execution receipt only; no new authority. User continuation “계속 진행해”, then “이어서 마무리해”, resumes completion of the existing Main Work cycle. Phase A source 8cabb2e93bbc8425592221456f44801e0f4ca413 (tree 7db0d8c91a453ed3d61cb1c6b32af46bdc1fb7f5) is consumed as an inactive supplied-input adapter and synthetic offline preview only. Source evidence records 57 targeted tests, nine context mismatch cases, desktop/mobile browser checks and independent PASS_SOURCE_SCOPE + PASS_OFFLINE_PREVIEW. Fresh receipt consumption verified seven subject SHA-256 hashes and three input Git blobs; 22 additions are within the claimed paths. Existing exact verification is reused; no test/CI rerun.

Containing Global publication restores AUTONOMY_MODE=READ_ONLY, releases only Main lease main-ca-phase-a-20261008T093552Z, and sets runtime IDLE. CDR033 five-task observed grant ends here. Source admission, route attachment, D3-A activation and production gate closure remain zero. Chart remains 6 OPEN / Market 0/19, FPIA independent trust/GIE and actual assembled Chart acceptance remain open; MissingData lease qgv-b47-muupb538 and all owner/history scopes are preserved. Canonical b8e39a2196a6d7794a04a0cd5393c68329e126ca is unchanged.

Publication uses fresh exact Global parent 84f2dd99e44e6c5e25b59391fdf44254e4d8be30, matching RUN/own lease, non-force ref update, local/API tree equality and remote byte/control readback. Old owner/canonical/protected scopes and PR60 automation changes are retained. Final identity resolves from the containing commit. See evidence/main_company_analysis_cycle_2026-10-08/FINAL_RECEIPT.json.


## CDR-035 · 2026-10-08T10:42:13Z · Direct Main named-action instruction / #51-only approval / READ_ONLY retained

User directive (2026-10-08) is retained verbatim at [USER_DIRECTIVE.md](evidence/main_directed_execution_2026-10-08/USER_DIRECTIVE.md). User attests Active HG02 canonical Ruleset with empty bypass, deletion/non-fast-forward denial, PR0 approval and repository-guard required; PR51 merge is expressly authorized only for51. Automation expansion is frozen until GateA OPEN and>=1 product blocker closed; only already-merged55–60 bug fixes allowed. User explicitly orders named HG/51/PPA-F08/TARGET/FPIA actions and lane leases while production AUTONOMY_MODE stays READ_ONLY. Apply this direct observed instruction only to those named actions; do not manufacture an autonomous RUN, unattended/GateA or standing-mode grant. This current explicit user instruction takes precedence for its bounded named actions; §4A remains controlling for autonomous/Watcher activity and all other unrequested writes.

Claims/plan: evidence/main_directed_execution_2026-10-08/. Five-task checkpoints continue to later observed cycles under this same prompt. No Ruleset/mode change, canonical merge other than51, Holdout/methodology/credential/financial/source authority/numeric permission. MissingData lease retained. Existing Web owner ref is preserved; explicit PPA-F08 successor claim uses app.js+existing browser runner only, negative reproduction then minimal ACTUAL availability presentation repair.


## CDR-036 · 2026-10-08T10:59:36Z · User FPIA lane replacement / existing recorded defects only

Latest explicit steering is preserved verbatim at [USER_FPIA_SCOPE_OVERRIDE.md](evidence/main_directed_execution_2026-10-08/USER_FPIA_SCOPE_OVERRIDE.md) and below. It supersedes only CDR035 section6 / B1–B4 discovery; other named actions, protections and READ_ONLY constraints remain unchanged.

```text
B1–B4 묶음은 찾지 말고 종료한다. 대신 FPIA lane을 다음으로 대체한다.
- 새 감사나 새 반례 작성은 하지 않는다.
- #42, #46, #47에 이미 기록된 결함(literal-source 거짓 PASS, AC-32 spoof 우회, #47 CI 실패 등)을
  F1, F2…로 번호 붙여 목록화하고, 각 항목의 기존 재현 근거·현재 수정 상태·남은 작업만 정리한다.
- 수정은 이 목록 범위로 한정한다. 완료 조건: 기존 반례 차단, 정상 사례 보존, 관련 회귀 통과.
  같은 방식 3회 실패 시 재계획(9A).
- 이 lane은 우선순위를 PPA-F08과 HG-02 다음으로 둔다.
```

This replacement does not authorize new audits/counterexamples or repairs outside the existing numbered inventory. PPA-F08 and HG-02 have priority over this lane. The same direct prompt continues across five-task checkpoints; no autonomous RUN/unattended/standing-mode grant is created.

## CDR-037 · 2026-10-08T10:59:36Z · Directed checkpoint 1 receipt / own lease release / continue cycle 2

Execution receipt only, no new authority. CDR035 named actions and CDR036 latest FPIA replacement remain the same observed user directive. Five tasks reach checkpoint 1; this is CHECKPOINT_CONTINUE, with existing PPA-F08 CI compatibility repair, TARGET draft package and existing #42/#46/#47 FPIA record inventory READY for cycle 2. The B1–B4 bundle search is terminated. No new FPIA audit or counterexample is authorized; repairs are confined to the numbered existing-defect inventory, with existing counterexamples blocked, normal cases preserved and relevant regressions passing; same-method third failure requires 9A replanning.

PR #51 source `de84abf11df64041f666628493b8ae54f2e6df4a` exact repository-guard run37303986881/job111743115747 SUCCESS is reused. External user merge by `kco994553-star` at 2026-10-08T10:41:37Z advanced canonical to `c109c81a3e417e5f61fd26b67b171fb13628dc21`; this Main session consumed that merge and did not perform it.

HG01 VERIFIED; HG02 PARTIAL_VERIFIED pending authenticated canary deletion and complete executor identity/refusal matrix; HG03 PARTIAL_VERIFIED / actual Watcher-to-Work E2E WAIT_PRODUCT_RUNTIME_CAPABILITY; actual PAUSE wake NOT_RUN, isolated fixture PASS only; Gate A CLOSED; automation expansion frozen; unattended executor disabled; AUTONOMY_MODE READ_ONLY. Canonical/canary normal pushes and genuine canary non-fast-forward force update were denied. Authenticated canary deletion is unavailable; actor credential type and Claude identity remain unverified. Ruleset24499602 Active/empty bypass includes canonical and canary following the user's external update; no ruleset update or target-addition request was made here. Actual product-runtime E2E and actual PAUSE wake remain unproved.

PPA-F08 draft [PR #63](https://github.com/kco994553-star/Investment-System1/pull/63) source `c6e00273b212a8d2c134909ec6ed803f8a43fb46` / tree `cd0dbe37c55e7d02a8d834f7da70ef0b15f87dc0` is VERIFIED_LOCAL_PRESENTATION_FIX_CI_BLOCKED_PENDING_COMPATIBILITY_REPAIR_AND_INTEGRATION. Genuine RED, 41 Python and31 browser checks pass; ko/en company/portfolio390 screenshots and finite zero/nonzero normal controls are retained. Local/API trees are identical. Exact native CI presentation37766480718 and MVP37766480693 SUCCESS; research guard37766480805/job113275278268 step10 FAILURE on existing line162/167 target-only44.44% expectations. This compatibility regression blocks completion; the next bounded cycle will show separately labelled persisted TARGET/Model weight beside ACTUAL NOT_AVAILABLE in the same claimed files, preserving the no-fallback boundary. Presentation source fix1; final product/canonical production closures0, source admission0, Chart6OPEN/Market0of19. Existing Web owner ref, all other owner/history scopes and MissingData lease `qgv-b47-muupb538` are preserved. Automation expansion freeze remains active.

Containing Global publication from `71a19b66ec8a7bdc0b21e5543d558ef22d7631f4` targets only matching own lease `main-directed-20261008-104213Z` release, Mainlease null and runtimeIDLE; AUTONOMY_MODE remains READ_ONLY throughout. Final identity resolves from the containing commit; remote exact-byte/control readback is required after non-force publication. The checkpoint does not finish the user's directed work or require a new directive for the next bounded cycle. [Checkpoint](evidence/main_directed_execution_2026-10-08/CHECKPOINT_1.json) · [HG02](evidence/main_directed_execution_2026-10-08/HG02_RECEIPT.json) · [HG03 E2E](evidence/main_directed_execution_2026-10-08/GATE_A_E2E.json) · [PPA publication](evidence/main_directed_execution_2026-10-08/PPA_F08_PUBLICATION.json) · [FPIA override](evidence/main_directed_execution_2026-10-08/USER_FPIA_SCOPE_OVERRIDE.md).


## CDR-038 · 2026-10-08T11:13:57Z · Directed cycle2 final execution receipt / READY0 / own release

Execution receipt only; no new authority. CDR035 named actions with CDR036 FPIA override complete cycle2's five bounded tasks. READY0; remaining user/source, acceptance and tool dependencies are WAIT. AUTONOMY_MODE stayed READ_ONLY throughout; unattended execution remains disabled. Checkpoint1 `main-directed-20261008-104213Z` control restoration was externally read back at Global9b18106f86a58b6d908cbbae4e36dbcb4751eae2; cycle2 claim2f44c70ea467a0ad1c10a53b8a3eeb09d0201b66 and packagepublication `dd3729f71e7f3cdc790e8859b238b13f568c77ff` are preserved.

PPA-F08 draft [PR63](https://github.com/kco994553-star/Investment-System1/pull/63) exact source `50e3d3e6942460468388af9b0ec969f3605f6ab1` / tree `5876f894a60d917f42ed9e1ab9bb3704c4463cf7` is VERIFIED_SOURCE_PRESENTATION_BLOCKER_CLOSED_IN_PROPOSAL_ONLY. 41 affected Python / 31 state-browser / 10 research-guard browser checks and exact native CI3SUCCESS (37768379561, 37768379569, 37768379552) establish the bounded source presentation repair. ACTUAL remains finite-only or NOT_AVAILABLE; persisted finite TARGET/Model is displayed separately, retaining original normal controls and relevant existing regressions. One source presentation blocker is closed; canonical integration/production closures0, proposal unmerged, source authority admission0. Platform historical9 product blockers are preserved without blanket subtraction or Product acceptance.

Seven [TARGET decision artifacts](evidence/main_target_decision_bundle_2026-10-08/DECISION_BUNDLE.json) and three [FPIA recorded-defect artifacts](evidence/main_fpia_recorded_defects_2026-10-08/INVENTORY.json) were published at `dd3729f71e7f3cdc790e8859b238b13f568c77ff`; independent packaging PASS_SCOPE is evidence for packaging only. TARGET/Theme values and adoption remain blank,18 common-contract source returns plus1Tokyo venue choice remain unresolved and admission0. One26E question was sent asynchronously to the current user session; no issue/email or repeated decision/tool/mode request was sent, and no timeout approval is inferred. F1–F25 enumerate existing #42/#46/#47 defects with recorded fixes already inherited; no new audit/counterexample, new FPIA source fix or blocker closure is claimed. Independent verifier/launcher/runtime, authenticated compound selection, dynamic/transitive/external coverage/isolation, GIE and actual assembled Chart acceptance remain OPEN/WAIT. Chart6OPEN/Market0of19.

HG01 VERIFIED; HG02 PARTIAL_VERIFIED pending authenticated canary deletion and complete executor identity/refusal matrix; HG03 PARTIAL_VERIFIED / actual E2E WAIT_PRODUCT_RUNTIME_CAPABILITY; actual PAUSE wake NOT_RUN; Gate A CLOSED; automation freeze ACTIVE; unattended executor disabled; mode READ_ONLY. Canonical `c109c81a3e417e5f61fd26b67b171fb13628dc21` is the externally user-merged PR51 result consumed by this session, with no further canonical action. Other owner refs, automations, histories and MissingData lease `qgv-b47-muupb538` are preserved. The documented canary deletion-zeroOID wrapper attempt ended before GitHub with `InvalidInputException: update_ref cannot delete a branch`; branch-rule deletion proof remains NOT_RUN and the claimed canary lane is BOUNDED_ATTEMPT_COMPLETED_TOOL_DEPENDENCY with its own cycle lease released. Canary/canonical readback remains `c109c81a3e417e5f61fd26b67b171fb13628dc21`. Claude auth capability remains unavailable; actual E2E/PAUSE wake remains unproved.

Containing non-force Global publication from `dc2305ebc7d87cffa518da41fe94ea9c07139bc3` targets release of only own lease `main-directed-cycle2-20261008T110350Z`, Mainlease null and runtimeIDLE. Final identity resolves from the containing commit; remote exact-byte/control readback must follow publication. Resume on actual current TARGET/Theme/source/user input, accepted owner/PR integration, independent FPIA/GIE acceptance or permitted hard-guard capability evidence after fresh scope/lease/mode checks. Own docs-only movement is not an execution trigger. [Final receipt](evidence/main_directed_execution_2026-10-08/FINAL_RECEIPT.json) · [PPA completion](evidence/main_directed_execution_2026-10-08/PPA_F08_COMPLETION.json).


## CDR-039 · 2026-10-08T11:46:34Z · User TARGET v0 adoption / USER source ownership / #63 noncanonical-only merge approval

User original directive is retained verbatim at [USER_DIRECTIVE.md](evidence/main_target_v0_adoption_2026-10-08/USER_DIRECTIVE.md). Attachment TARGET_v0.yaml SHA256 `a4424f9e9c4e463963d719a3f10949c311902238bc71ca926f0dd045cdf6cb8b`, 4463 bytes is user-adopted v0 for A-S1 and A-S3. Source owner is USER, resolving #54 source OWNER_UNASSIGNED for those two source roles. Exact original weights/themes/holdings/clocks are immutable to agents; future TARGET changes occur only through user revisions. Explicit attachment listing choices TSE8035, KRX042700 and Alphabet Class A GOOGL are retained without replacing them with the alternative hints in the message. Effective/available/adopted clocks are user-attested 2026-10-08T11:37:00Z; no retrospective use from September14 is authorized.

Direct user authorization covers source addition via PR, declared invariant tests, existing-approved-contract A-S2 mapping or UNRESOLVED, display-only TARGET screen attachment with ACTUAL NOT_AVAILABLE, six-gate evidence rejudgment and PR63 merge only when base is not canonical/default. Apply only these observed named actions while AUTONOMY_MODE remains READ_ONLY; no standing RUN/unattended permission. No canonical merge, new investment calculation, QGV recomputation, renormalization, Holdout or automation expansion. Fresh own lease and five-task checkpoints required; other owner/history scopes and MissingData held lease preserved. Source/display integration through noncanonical PRs is limited to the named additions and ordinary display write-set; no protected contracts or owner scope takeover.


## CDR-040 · 2026-10-08T11:50:25Z · USER D3-R QGV Scoring Standard v1 adoption (independent lane)

Exact user directive retained at [USER_DIRECTIVE.md](evidence/main_qgv_standard_v1_2026-10-08/USER_DIRECTIVE.md). USER adopts current exact Q/G/V weights, 3Y G default, existing D10 linear clip and identity Type adjustment as STANDARD v1 · UNCALIBRATED; no numeric changes. Q7 name Management Quality(경영진 품질), Capital Allocation subordinate interpretation, unchanged10%. Enable only existing v1-prior V operational output with standard=v1/calibration=UNCALIBRATED on every result; research candidates remain RESEARCH, never operational. Exact source HEAD and immutable fixed-value/sum/5–30% regressions must be recorded. Preserve all existing QGV numerical expectations, report unexpected score changes rather than rewriting them. C03 append-only RESOLVED; v2 is a future separate user adoption after PIT/OOS/Calibration and first-confirmed Holdout protection, with no current calibration/period selection/consumption.

Adoption takes effect prospectively from this observed decision-record receipt 2026-10-08T11:50:25Z (recording time, not an inferred original user submission time); no historical v1 assertion is authorized. This source standard adoption is distinct from TARGET v0, Chart identity, MissingData or production-data/Official-LIVE permissions. Direct named actions remain observed and bounded with AUTONOMY_MODE READ_ONLY and no autonomous mode grant. Code write-set/base must be claimed before editing; no canonical merge, new numbers, Holdout, automation expansion, owner takeover or held-lease clearing.


## CDR-041 · 2026-10-08T12:36:16Z · Directed TARGET v0/QGV final receipt / checkpoint5

USER TARGET v0 source [PR64](https://github.com/kco994553-star/Investment-System1/pull/64) merged `a81a45a087b4409d2df11bf34b10a7d79bf82c84`; original 4463 bytes / SHA256 `a4424f9e9c4e463963d719a3f10949c311902238bc71ca926f0dd045cdf6cb8b` are preserved. USER TARGET weight-root admission 1; Security identity admission 0. TARGET input request is ANSWERED; no renewed TARGET/listing question. Display [PR66](https://github.com/kco994553-star/Investment-System1/pull/66) merged `47dce4c768f315ff6036e8a34c177920c1d50b14` into `codex/chart-contract-mcp-api-v0-1`. Chart A-S1 CLOSED only on authenticated source consumption; A-S2/A-S3/A-G1/A-G2/A-G3 OPEN. Security identity 0/19 mapped, 19 UNRESOLVED; hints and company namespace evidence remain nonidentity.

[PR63](https://github.com/kco994553-star/Investment-System1/pull/63) merged `558108a657839bc909272b103ab00faeaf25c957` into the noncanonical Web branch. PPA-F08 CLOSED, Platform 1/9 closed and 8 remain. ACTUAL remains finite-only or NOT_AVAILABLE; TARGET is separate. Native CI receipts: `[37768379561,37768379569,37768379552]`.

QGV [PR65](https://github.com/kco994553-star/Investment-System1/pull/65) merged `753f225caa2da1877a1e6391df9e10b1085e9578` into `codex/qgv-architecture-reconciliation-review-2026-10-05`. STANDARD v1 · UNCALIBRATED and append-only C03 RESOLVED are prospective from the observed adoption receipt 2026-10-08T11:50:25Z; numerical invariance is verified in the supplied final receipt. Actual test receipt: `{"passed":503,"existing":488,"new":15,"audit_golden":71}`. Actual CI disposition: `{"status":"SUCCESS","run_id":37775779453,"job_id":113306115143,"head_sha":"c72458c9608c4f7814fa2ed6e251bea465570d7c","url":"https://github.com/kco994553-star/Investment-System1/actions/runs/37775779453"}`. The first full-run failure evidence and immutable historical golden fixtures remain preserved.

HG01 VERIFIED; HG02/HG03 PARTIAL_VERIFIED; actual E2E/PAUSE wake unproved, Gate A CLOSED, automation freeze ACTIVE, unattended executor disabled, AUTONOMY_MODE READ_ONLY. Canonical `c109c81a3e417e5f61fd26b67b171fb13628dc21` unchanged. Inherited MissingData lease `qgv-b47-muupb538` and historical returns remain intact; authorized noncanonical Chart/QGV base changes are recorded above. Existing FPIA records are unchanged; no new audit/countercase.

Both directed lanes are done. Checkpoint5 releases only matching own Main lease `target-v0-20261008T114634Z` and any remaining own child leases; previously recorded child releases retain their original timestamps. runtime IDLE, READY0. Remaining reviewed identity, complete Theme assignment, Product/cross-owner acceptance, independent FPIA/GIE and hard-guard runtime capabilities remain OPEN/WAIT. This is an execution receipt, with no new grant. Containing publication identity resolves from the actual commit; remote exact-byte/control readback follows. [Final facts](evidence/main_target_v0_adoption_2026-10-08/final/FINAL_FACTS.json) · [Checkpoint5](evidence/main_target_v0_adoption_2026-10-08/final/CHECKPOINT_5.json)


## CDR-042 · 2026-10-09 · USER26E conditional PR67 merge and device-only ACTUAL adoption

Direct user decision responding to the2026-10-08 request; exact original follows and is retained at [USER_DECISION.txt](evidence/user_26e_decision_2026-10-09/USER_DECISION.txt). User-submission timestamp is not inferred beyond session date. Applies to named observed work with READ_ONLY unchanged. No public deployment, standing autonomy, GateA, Holdout, new scoring or force-push grant.

PR67 exact candidate ab295f7d4e66b5cada04a8ad93361152d4e6d665 is conditionally approved: attempt unchanged FPIA scope classification; PASS/OUTSIDE_SCOPE permits PR merge, or documented tool-indeterminate scope may use current repository-guard CI and independent fresh-session technical PASS as the explicit user exception. Public web deployment linkage is a hard pre-merge report boundary. Any problem rolls back through a revert PR. F1–F25 LATER remain separate; this exception grants no global FPIA PASS or policy rewrite.

ACTUAL design/implementation is authorized on a scoped branch: user-device IndexedDB,19A-S2 instruments, quantity/averagecost/currency, supplied-price calculations or NOT_AVAILABLE, user-owned versioned JSON backup/import/delete, no private holdings in repo/build/CI/logs/network, privacy guard and390pxko/en flow verification. Public deployment and merging the new ACTUAL implementation into canonical require separate review/authorization; the current canonical merge authorization is PR67 only.

```text
26E 결정 (2026-10-08 요청분, Decision Register에 원문과 함께 append-only 기록)

1. PR #67 병합: 조건부 승인
- 다음 사이클 안에 #67에 대한 FPIA 적용 범위를 판정한다.
- PASS 또는 "적용 대상 아님"이면 #67을 PR로 병합한다(force push 금지).
- FPIA 도구 한계로 판정할 수 없으면 repository-guard CI 통과와 독립 세션 재검증 PASS를 대체 근거로 병합하고,
  이 예외와 사유를 Decision Register에 기록한다. FPIA LATER 항목은 별도로 계속한다.
- 기준 브랜치가 공개 웹 배포와 연결돼 있으면 병합하지 말고 먼저 보고한다.
- 병합 후 문제가 생기면 revert PR로 되돌린다.

2. ACTUAL 입력 방식: 휴대폰 브라우저 내 저장 (사용자 기기 전용)
- 저장소는 공개로 유지한다. 저장소·빌드·CI·로그 어디에도 실제 보유 데이터를 두지 않는다.
- 웹 cockpit에 ACTUAL 입력 화면을 추가한다: 종목(A-S2 식별자 기준 19종목)별 수량·평균단가·통화 입력.
  데이터는 사용자 기기의 브라우저 저장소(IndexedDB 등)에만 저장하고 서버나 외부로 전송하지 않는다.
- 화면은 기기 내 데이터로 비중·평가액·TARGET 대비 차이를 계산해 표시한다. 시세가 없으면 해당 값은 NOT_AVAILABLE.
  데이터가 없으면 기존처럼 ACTUAL NOT_AVAILABLE.
- 백업: JSON 파일 내보내기/가져오기 기능을 제공한다. 파일 형식은 TARGET_v0.yaml과 같은 구조
  (사용자 소유, 버전, effective_at·available_at, A-S2 식별자)로 해서 나중에 DB로 옮길 수 있게 한다.
- 데이터 삭제 버튼과 "이 기기에만 저장됨" 안내를 표시한다.
- 실제 데이터가 담긴 파일이 커밋되면 실패하는 검사를 repository-guard에 추가한다.
- 웹 cockpit을 GitHub Pages 등 공개 주소로 배포하는 것은 데이터가 포함되지 않음을 확인한 뒤 별도 승인으로 한다.
- 브라우저 검증: 390px 휴대폰, ko/en, 입력→저장→새로고침 후 유지→내보내기→삭제→가져오기.
```


## CDR-043 · 2026-10-09 · PR67 explicit substitute acceptance / pre-merge receipt

Execution of CDR042, not a standing FPIA waiver. Exact head ab295f7d4e66b5cada04a8ad93361152d4e6d665/tree d1b8efa97947743ed56d402cc415b340f434cf4a/base c109c81a3e417e5f61fd26b67b171fb13628dc21. Fresh untouched7215/CDR014 applicability returned BLOCKED exit2/NOT_RUN, nested authorityPASS but top authenticationNOT_VERIFIED, with19253 unclassified records over307files. Existing conservative execution/import rules cannot classify the subset. Do not relabel this as FPIA_PASS or OUTSIDE_SCOPE. The user explicitly approved guardCI+independentPASS as substitute for this tool limitation for PR67.

Fresh independent remote-clone technicalPASS:665Python+93subtests, guard801records/0violations, modeREAD_ONLY, identities19/19/themes19/19, original source7426files preserved. Exact-head all5GitHubchecksSUCCESS, repository-guard run37861673301/job113598638928. Deployment condition checked: has_pages=false, Pages404, deployments200empty, environments0, no canonical push/deploy workflows or tracked hosting config, exact-repository Vercel search0 in connected scope. No observable public deployment linkage; unseen external accounts/hooks are not asserted impossible.

Substitute acceptance is authorized for PR67 only; F1–F25 remain25LATER, broader formal FPIA and production gates remain unchanged. Merge through normal PR with exact-head check and no force push; rollback by revert PR. ACTUAL implementation is separate and undeployed. [Exception](evidence/user_26e_decision_2026-10-09/MERGE_ACCEPTANCE_EXCEPTION.json) · [Independent receipt](evidence/user_26e_decision_2026-10-09/INDEPENDENT_TECHNICAL_RECEIPT.json) · [Release audit](evidence/user_26e_decision_2026-10-09/RELEASE_AUDIT_RECEIPT.json).


## CDR-044 · 2026-10-09 · PR67 merge execution and independently verified device-only ACTUAL PR68

Execution receipt of CDR042/043; no new user authority. PR67 was normally merged through GitHub at2026-10-09T00:28:02Z: source ab295f7d4e66b5cada04a8ad93361152d4e6d665, canonical merge e03b9a10997e195f3681a32b5315feb998d55312, identical verified/merged tree d1b8efa97947743ed56d402cc415b340f434cf4a. No force push or public deployment. The exact user-authorized FPIA classification/tool-indeterminate substitute in CDR043 was used; formal applicability remains BLOCKED and audit NOT_RUN, not PASS/OUTSIDE_SCOPE. Recorded F1–F25 candidate defect blockers0,25LATER remain separate. Rollback is by revert PR if an observed problem occurs.

Device-only ACTUAL is implemented in ready-for-review [PR68](https://github.com/kco994553-star/Investment-System1/pull/68), exact head17b8f82bd09bce4cd0655e9f0795f3670bd805d8/treef0462875d374da2f7edcc9324090a7df8590d4ce/basee03b9a10997e195f3681a32b5315feb998d55312, unmerged and undeployed. User holdings remain in browser IndexedDB with local versioned owner/effective_at/available_at/A-S2/TARGET-pinned JSON backup/import/delete. No actual user data was requested or used. Public build contains only original public producer data and identity/TARGET metadata; recognizable private build inputs are rejected before output. Repository-guard rejects populated structured ACTUAL exports, including renamed files and committed-then-deleted new history, without logging their values. Arbitrary encoded/encrypted/binary data is not exhaustively recognized. Current quotation route is absent, so valuation/weights/TARGET deltas are NOT_AVAILABLE; missing/mixed currencies never receive invented prices or FX.

Fresh independent session PASS_WITH_MINOR_FINDING at exact final source tree:701Python+99subtests,17ACTUALNode,40ACTUAL390pxko/en,21additional independent browser,10existingweb,8searchbrowser,26searchNode; final remote guard PASS READ_ONLY. Evidence scan20files/0holdings canary matches, request/console/header privacy and isolation PASS. Critical/important findings0. Minor1: generated public actual-catalog.json filename causes conservative guard false positive if later tracked; it is currently built outside tracked source and is not a privacy leak. All final-head native CI4SUCCESS: repository-guard37865830515/job113612208278, Web37865830465/job113612208340, presentation37865830508/job113612208334, research37865830555/job113612208894. Independent receipt captured WebCI in progress; this later execution receipt records its completed SUCCESS without rewriting that earlier evidence.

Current-target A-S2 resolves19/19, unresolved0; A-S3 assignments19/19. Chart source gates3/6 and Platform1/9 remain distinct from broader production closure: A-G1 original authority/read/invalidation, A-G2 original production route/affected-owner acceptance, A-G3 broader formal FPIA remain open. PR67's scoped substitute does not waive those production obligations. Full dated ListingIdentity0/19 remains separate. READ_ONLY, Frozen/TARGET/scoring histories and deferred GateA/unattended automation/operational refresh remain unchanged.

The existing merge authorization covered PR67; PR68 canonical merge awaits a separate [26E decision](evidence/user_26e_decision_2026-10-09/PR68_MERGE_DECISION_26E.md). Public deployment awaits separate approval after data-exclusion confirmation. No timeout grant. [Final execution receipt](evidence/user_26e_decision_2026-10-09/FINAL_EXECUTION_RECEIPT.json) · [Independent ACTUAL review](evidence/user_26e_decision_2026-10-09/ACTUAL_INDEPENDENT_REVIEW_RECEIPT.json) · [ACTUAL browser results](evidence/user_26e_decision_2026-10-09/ACTUAL_BROWSER_RESULTS.json)


## CDR-045 · 2026-10-09 · USER26E PR68 merge approval and conditional GitHub Actions Pages deployment

Exact original user directive retained at [USER_DECISION.txt](evidence/user_26e_pages_quotes_2026-10-09/USER_DECISION.txt) and reproduced below. Authorizes normal PR68 merge after confirming exact-head native CI and independent PASS; no force push and rollback through revert PR. The user applies PR67's bounded conditions to PR68, without declaring global formal FPIA PASS.

User attests on2026-10-09 that Pages Source is None and PR67 did not deploy. Public cockpit deployment is conditionally authorized through GitHub Actions only: prepare a deployment-workflow PR with fail-closed pre-deployment exclusion of real holdings, monetary fields, secrets and local/ files; upload only the generated web folder. Before merging that PR, request its merge approval and a user-operated Pages Source change to GitHub Actions together in26E. Agent must not change Pages settings. After actual deployment, verify its served URL at390px through ACTUAL input/save/refresh/export/import. Preparing and verifying the requested PR is authorized now; its merge and public execution await the named final user decisions.

Quotes/FX are public data, while holdings remain on device. Authorized work is a26E comparison only: manual current-price input, daily close/FX publicJSON via Actions, real-time API; include costs/terms/effort/risks and all19US17/TSE8035/KRX042700 coverage, USD/JPY/KRWFX sources and KRW/USDbase-currency decision. No quotation collection/integration, paid service, new scoring/calculation method, Holdout or AUTONOMY_MODE change is authorized. READ_ONLY remains. GateA/unattended automation and operational data refresh remain outside the directed scope.

```text
26E 결정 (Decision Register에 원문과 함께 append-only 기록)

1. PR #68 병합: 승인
- 조건은 #67과 같다. CI·독립 검증 PASS 상태를 확인하고 PR로 병합한다(force push 금지).
- 문제가 생기면 revert PR로 되돌린다.

2. 웹 cockpit 공개 배포: 조건부 승인
- 사용자 확인(2026-10-09): GitHub Pages는 현재 비활성(Source None). #67 병합으로 배포된 것은 없다.
- 배포는 "GitHub Actions" 방식으로 한다. 배포 workflow를 PR로 추가하되, 배포 직전에
  실제 보유 데이터·금액성 필드·비밀 값·local/ 파일이 산출물에 있으면 실패하는 검사 단계를 넣는다.
- 웹 산출물 폴더만 배포한다(저장소 전체를 올리지 않는다).
- PR이 준비되면 병합 승인과 "Pages Source를 GitHub Actions로 변경" 요청을 26E로 함께 올린다.
  Pages 설정 변경은 사용자가 한다.
- 배포 후 주소에서 390px 휴대폰 기준으로 ACTUAL 입력→저장→새로고침 후 유지→내보내기→가져오기를 검증한다.

3. 시세 연결: 선택지 요청 (구현 금지)
- 시세·환율은 개인정보가 아니므로 공개 데이터로 다룬다. 보유 정보는 계속 휴대폰 안에만 둔다.
- 다음 선택지를 비용·이용약관·소요·위험과 함께 26E로 정리한다.
  · 앱에서 현재가를 사용자가 직접 입력
  · 매일 종가·환율을 GitHub Actions로 받아 공개 JSON으로 저장하고 앱이 읽기
  · 실시간 시세 API (유료 가능성)
- 19종목 전체(미국 17, TSE 8035, KRX 042700) 커버 여부와 USD·JPY·KRW 환율 소스를 포함한다.
- 기준 통화 선택지(KRW / USD)도 함께 묻는다.

이번 사이클 보고: #68 병합, Pages 설정 확인 결과와 배포 주소, 휴대폰 검증 결과, 시세 선택지 묶음, Chart n/6, Platform n/9.

포함하지 않는 것: 시세 수집 구현, 유료 서비스, 새 투자 계산법, Holdout, AUTONOMY_MODE 변경.
```


## CDR-046 · 2026-10-09 · USER Pages cockpit deployment preparation directive

Latest steering retains the existing CDR045 quote-options lane. Exact original follows and is retained at [USER_DIRECTIVE.txt](evidence/pages_cockpit_preparation_2026-10-09/USER_DIRECTIVE.txt). This names the already-authorized preparation workflow: canonical-target PR, repository-guard, GitHub upload/deploy Pages actions, canonical merge plus manual triggers, only web output, fail-closed holdings/monetary/secrets/local exclusion, minimal three permissions, project-subpath/PWA review and390/1280screenshots. The final26E must request PR merge approval and the user-operated Source change together. Agent settings mutation and merging the new deployment PR before the named final approval are not authorized. READ_ONLY and holdings-only-on-device remain.

```text
[웹 cockpit GitHub Pages 배포 준비 — v1.1 범위, READ_ONLY 유지]

사용자 결정(2026-10-09, Decision Register에 append-only 기록):
웹 cockpit을 중간 확인과 개인 사용을 위해 GitHub Pages로 배포한다. 보유 데이터는 계속 휴대폰 브라우저 안에만 둔다.

1. 배포 workflow를 PR로 추가한다(기준 브랜치 대상, repository-guard 통과).
   - 방식: GitHub Actions (actions/upload-pages-artifact + actions/deploy-pages)
   - 실행 조건: 기준 브랜치에 병합될 때 + 수동 실행(workflow_dispatch)
   - 웹 cockpit 빌드 산출물 폴더만 업로드한다. 저장소 전체를 올리지 않는다.
   - 업로드 직전 검사: 실제 보유 데이터, 금액성 필드, 비밀 값, local/ 파일이 산출물에 있으면 배포를 중단한다.
   - 권한은 pages: write, id-token: write, contents: read만 준다.
2. 산출물이 GitHub Pages 하위 경로(/Investment-System1/)에서 정상 동작하는지 확인한다(상대 경로·PWA 설정).
3. 390px·1280px 브라우저 검사와 스크린샷을 첨부한다.
4. PR이 준비되면 26E로 두 가지를 요청한다: PR 병합 승인, Pages Source를 GitHub Actions로 변경.
   Pages 설정은 사용자가 한다.
```


## CDR-047 · 2026-10-09 · PR68 merge execution / independently verified Pages PR69 ready for final26E

Execution receipt of CDR045/046, no new grant. [PR68](https://github.com/kco994553-star/Investment-System1/pull/68) normally merged at2026-10-09T00:56:05Z: source17b8f82bd09bce4cd0655e9f0795f3670bd805d8, mergec8c2073ad5cdee3cc11d03fc2fe895b7d8d77114, exact verified/merged treef0462875d374da2f7edcc9324090a7df8590d4ce. Its native CI4SUCCESS and independent technicalPASS were rechecked before merge. CDR045 applies the bounded CDR043 tool-indeterminate substitute, not global FPIA_PASS or policy rewrite. No force push or public deployment. Revert PR remains the authorized code rollback.

Pages [PR69](https://github.com/kco994553-star/Investment-System1/pull/69) is prepared against canonical at exact head29bd7f3437f34f40dae319fe875a19b6e19225bb/tree3eecea810778f2d78daa51dce29a8bdfe543e02c/basec8c2073ad5cdee3cc11d03fc2fe895b7d8d77114; unmerged. All8494baseline tracked blobs/modes are unchanged. Publication-only projection omits501public monetary fields; identity/rank/provenance/clocks and original producers/TARGET/scoring are preserved. Only11reviewed web files are uploaded. Directory and downloaded immutable-ID raw-tar checks reject populated private/monetary fields, secrets, local/extra paths, links, extended metadata, padding and trailing payload before upload/deploy. No actual user holdings were requested, used or retained in repository/build/CI/logs. Direct Actions are pinned; privileged deployment job is canonical push/manual only, uses only contents:read/pages:write/id-token:write and does not enable/change Pages settings.

Native exact-head CI2SUCCESS: repository-guard run37868295034/job113620188643 and Pages build run37868295036/job113620189440. Deploy job113620753739 is SKIPPED on PR as intended, not evidence of deployment. Fresh separate-context independent review PASS_WITH_MINOR_RESIDUAL, critical/important findings0:745Python+217subtests,17Node,10subpath390/1280ko/en,40ACTUAL390ko/en and17additional adversarial checks. Four empty-device screenshots are attached to PR69. Reviewer independently downloaded actual Pages artifact11589101948:11raw-tar files PASS and all bytes identical to its independent build. Minor1: official pinned upload-pages-artifact composite internally references mutable upload-artifact@v4; immutable-ID raw-tar validation passed, without a claim of a fully pinned transitive dependency graph.

Pages is still user-attested SourceNone; public repo has_pages=false, Pages API404 and planned address https://kco994553-star.github.io/Investment-System1/ returns404. Authenticated Source enum was not read by the agent. Relative resources work under /Investment-System1/; no manifest/service-worker currently exists or is added. Public-address mobile validation remains NOT_RUN until final approval and user Source change cause actual deployment. Final [deployment26E](https://github.com/kco994553-star/Investment-System1/blob/29bd7f3437f34f40dae319fe875a19b6e19225bb/implementation/docs/pages_cockpit_owner/DEPLOYMENT_DECISION_26E.md) requests PR69 normal merge approval and user-operated SourceGitHubActions together; WAIT without timeout permission. Settings are exclusively the user's action. Code rollback uses revert PR; a previously deployed site may persist until an approved replacement deployment or user disablement.

The [quote/FX26E comparison](https://github.com/kco994553-star/Investment-System1/blob/29bd7f3437f34f40dae319fe875a19b6e19225bb/implementation/docs/pages_cockpit_owner/QUOTES_FX_OPTIONS_26E.md) presents manual on-device prices/FX, daily Actions publicJSON and real-time API with costs/terms/effort/risks;19instruments and USD/JPY/KRW are listed. Automatic19/19coverage and redistribution permission are not yet confirmed. FX references are ECB and BOKECOS (JPY unit100). KRW/USD base currency remains a user choice. No observation collection, quotation integration or paid service was performed. Quote implementation remains WAIT for a separate decision.

A-S2 current-TARGET resolved19/19/unresolved0 and A-S3 assigned19/19. Chart source gates3/6, Platform1/9 remain. A-G1 original production authority/read/invalidation, A-G2 original production route/affected-owner acceptance, A-G3 broader formal FPIA remain OPEN; full dated ListingIdentity0/19 remains separate. Recorded F1–F25 defect blockers0,25LATER; no formal global FPIA_PASS. READ_ONLY, Frozen/TARGET/scoring/Holdout histories and existing owner leases are preserved. Deferred GateA, unattended automation and operational refresh are outside this cycle.

[Final execution receipt](evidence/pages_cockpit_preparation_2026-10-09/FINAL_EXECUTION_RECEIPT.json) · [Fresh independent review including actual uploaded tar](evidence/pages_cockpit_preparation_2026-10-09/INDEPENDENT_REVIEW_RECEIPT.json) · [Pages preparation probes](evidence/pages_cockpit_preparation_2026-10-09/PAGES_PREPARATION_PROBE.json)

The unchanged Global-branch conservative name/status guard reports one register-M violation even for this genuine append; it does not inspect byte prefixes. [Append-only proof](evidence/pages_cockpit_preparation_2026-10-09/APPEND_ONLY_VERIFICATION.json) verifies all127489prior register bytes and every other original blob/mode are preserved, with controls/leases unchanged. The explicit user record instruction is fulfilled without changing guard/policy or declaring this Global check PASS. This separate documentation-tool limit does not change PR69's exact-head native repository-guard SUCCESS.


## CDR-048 · 2026-10-09 · USER26E PR69 merge approval / manual device quotations and KRW adoption

Exact original follows and is retained at [USER_DECISION.txt](evidence/manual_quotes_decision_2026-10-09/USER_DECISION.txt). Authorizes normal PR69 merge without force push. User operates Pages Source; only after change confirmation run the deployment workflow and verify the actual public address at390/1280ko/en through ACTUAL input/save/refresh/export/delete/import. READ_ONLY remains; no standing autonomy grant.

Manual quotations/FX are authorized now on a scoped feature branch:19A-S2-native current prices and editable input timestamps, >=7days STALE, missing prices/FX NOT_AVAILABLE without estimated substitutes, KRW valuation/weights/TARGET percentage-point differences with native values shown. Data remains only on device. API-key structure is also authorized but provider selection is a separate26E; no provider is selected and API remains OFF/no automatic polling. Key stored separately on device, explicit delete, excluded from holdings/quote/FX/time backup; no external script, CSP connect allowance stays self-only until a reviewed provider is chosen. No Actions price collection, public quote files, paid API, Frozen/TARGET/scoring/Holdout or mode changes. The named canonical merge grant is PR69; a subsequently prepared implementation PR is a separate reviewable result, not an inferred new named-PR merge grant.

Root owns integration/build/CSP/privacy guards/docs/workflow tests; manual_market_core owns only new market module/Node test and manual_quotes_ui owns existing ACTUAL module/CSS/new browser test. No lease takeover or unrelated controls rewrite. Existing holdings schema1 stays local; versioned backup2 includes strict market metadata without keys and imports schema1 safely. Storage/import must be atomic and preserve prior state on invalid/canceled/conflicting operations. Implementation choices follow the explicit user design and do not require repeating a design-permission flow. [Authority receipt](evidence/manual_quotes_decision_2026-10-09/USER_DECISION_RECEIPT.json).

```text
26E 결정 (Decision Register에 원문과 함께 append-only 기록)

1. PR #69 병합: 승인. PR로 병합한다(force push 금지).

2. Pages Source: 사용자가 GitHub Actions로 변경한다. 변경을 확인하면 배포 workflow를 실행하고
   공개 주소에서 390px·1280px, ko/en, ACTUAL 입력→저장→새로고침 후 유지→내보내기→삭제→가져오기를 검증한다.

3. 시세: 수동 입력 + 사용자 API 키 직접 조회 (두 방식 병행)
   A. 수동 입력 (이번에 구현)
   - 종목별 현재가와 입력 시각을 사용자가 입력한다. 데이터는 휴대폰 브라우저 안에만 저장한다.
   - 입력 시각을 표시하고, 7일 이상 지난 시세는 STALE로 표시한다.
   - 시세가 없는 종목은 평가액·비중을 NOT_AVAILABLE로 둔다. 추정하거나 대체하지 않는다.
   B. 사용자 API 키로 휴대폰에서 직접 조회 (구조만 구현, 서비스 선택은 26E)
   - 사용자가 앱 설정에 본인의 무료 API 키를 입력하면, 휴대폰 브라우저가 시세 서비스에 직접 요청한다.
     서버·GitHub Actions·저장소를 거치지 않으므로 시세를 재배포하지 않는다.
   - API 키는 휴대폰 브라우저 안에만 저장한다. 저장소·빌드·로그에 넣지 않고, 백업 JSON 내보내기에서도 제외한다.
     키 삭제 버튼을 둔다.
   - 시세 출처는 종목별로 "API / 수동 / 없음"을 표시한다. API가 실패하거나 지원하지 않는 종목은 수동 입력으로 대체한다.
   - 키 보호를 위해 외부 스크립트를 불러오지 않고, 연결 허용 주소를 선택한 시세 서비스로 제한한다(CSP).
   - 무료 호출 한도를 넘지 않도록 자동 갱신은 하지 않고, 사용자가 "시세 새로고침"을 누를 때만 조회한다.
   - 시세 서비스 선택지를 26E로 정리한다: 브라우저 직접 호출 가능 여부(CORS), 19종목 커버리지
     (미국 17, TSE 8035, KRX 042700), 환율 지원, 무료 한도, 개인 사용 약관. 서비스가 정해지기 전까지 B는 꺼진 상태로 둔다.

4. 기준 통화: KRW
   - USD/KRW, JPY/KRW 환율은 수동 입력(또는 B에서 선택한 서비스)으로 받고 입력·조회 시각을 표시한다.
   - 종목별로 원래 통화(USD·JPY·KRW) 값도 함께 보여준다.
   - 화면: 평가액(KRW), 실제 비중, TARGET 대비 차이(비중 %p).

5. 백업 JSON에는 보유 정보·시세·환율과 시각을 포함하고, API 키는 포함하지 않는다.

이번 범위가 아닌 것: GitHub Actions 기반 시세 수집, 공개 저장소에 시세 저장, 유료 API.
보고: 배포 주소, 공개 주소 검증 결과, 390px·1280px 스크린샷, 시세 서비스 선택지, Chart n/6, Platform n/9.
```


## CDR-049 · 2026-10-09 · USER confirms Pages Source changed to GitHub Actions

User response to the setup-completion question confirms the Source change is complete. This is user attestation, not an authenticated Pages settings enum observed by the agent. Agent did not change settings. Together with CDR048 it satisfies the named pre-deployment wait: recheck unchanged PR69 exact-head CI/independent PASS, then normal merge triggers the authorized canonical deployment; manual dispatch is needed only if no push run executes. Verify deployed address rather than claiming local tests prove publication. Exact response retained at [PAGES_SOURCE_USER_CONFIRMATION.txt](evidence/manual_quotes_decision_2026-10-09/PAGES_SOURCE_USER_CONFIRMATION.txt):

```text
Source를 GitHub Actions로 변경하신 뒤 완료 여부를 알려주세요
변경했어
```


## CDR-050 · 2026-10-09 · USER supplements API-provider26E candidates and user-only free relay alternative

Exact original follows and is retained at [USER_API_AMENDMENT.txt](evidence/manual_quotes_decision_2026-10-09/USER_API_AMENDMENT.txt). Requires KISDevelopers and FinancialServicesCommission public stock-price data among candidates; verify19coverage/free delay/auth/token/possible future holdings linkage, CORS and phone-secret risks. User's broad KISmarket statement is a candidate requirement, not agent-verified endpoint/plan/instrument coverage. If direct browser access is blocked or a secret is required, describe user-only free relay such as CloudflareWorkers with credentials exclusively server-side secret storage and its access-control/cost/abuse risks. This authorizes options/structure research only, no relay setup or broker holdings connection. Provider remains unselected/API OFF. Already-authorized PR69 merge/Pages/manual implementation continue; no restart or scope cancellation.

```text
[추가 지시 — 앞 지시 3번 B 보완]

시세 서비스 선택지(26E)에 다음 후보를 반드시 포함한다.
- 한국투자증권 Open API(KIS Developers): 국내 KRX + 해외(미국 NAS·NYS·AMS, 도쿄 TSE)를 한 계정으로 조회 가능.
  19종목 전체 커버 여부, 무료 지연 시세 범위, 앱 키·시크릿·토큰 방식, 향후 보유 내역 연동 가능성.
- 공공데이터포털 금융위원회 주식시세정보: 국내 종목, 무료, 갱신 주기.

각 후보마다 브라우저 직접 호출 가능 여부(CORS)와 키·시크릿을 휴대폰에 둘 때의 위험을 적는다.
직접 호출이 안 되거나 시크릿이 필요하면 "사용자 전용 무료 중계 서버(예: Cloudflare Workers, 키는 서버 비밀 저장소에만)"
방식의 구조와 위험도 함께 적는다.

서비스가 정해지기 전까지 API 조회는 꺼둔다. 증권 계좌 연동(보유 내역 조회)은 이번 범위가 아니다.
이미 진행 중인 #69 병합, Pages 배포, 수동 시세 입력 작업은 그대로 진행한다.
```


## CDR-051 · 2026-10-09 · Authorized PR69 merge and actual Pages deployment; device quotes candidate final verification

CDR048–050 exact user originals remain unchanged. PR69 merged normally without force push to d71243bcc79139149541f3627e8f227a32c463c5 with approved tree3eecea810778f2d78daa51dce29a8bdfe543e02c. User confirmed Source changed to GitHub Actions; agent did not change settings. The canonical push deployment run37869779655 build/deploy succeeded, including uploaded raw-tar exclusion immediately before deployment. Public https://kco994553-star.github.io/Investment-System1/ returns200; all11served files match the approved artifact. Actual390/1280ko/en ACTUAL input/save/refresh/export/delete/import80checks and subpath10checks passed; empty screenshots are in PR70 owner evidence. This public verification covers PR69 baseline, not the unmerged manual-quote feature.

PR70 head80704d3f600ac034705a46eab16f22ed522e0ed9 / treec2fe43912ffede1525bc481892bd44bdb34ecaee is a separately reviewable canonical-target candidate. Native CI5/5 SUCCESS and final fresh-context independent verdict PASS_WITH_MINOR_RESIDUAL; no remaining critical/important blocker. Initial independent R1 FAIL found stale corrupt-tab explicit deletion could delete another tab's recovered pair or key. The defect was corrected with transactional comparison of originally read structured clones, safe unsupported-type failure, and RED/GREEN browser regression; final independent full tests/adversarial checks were rerun on the corrected head. The independent build and locally generated raw-tar12files passed; actual CI archive byte inspection is BLOCKED/NOT_RUN because File-Service download returns403. Immutable artifact metadata binds the exact head/run/digest; native pre-upload directory check passed and the actual-archive guard is retained for future authorized deployment (PR deploy skipped). Preserve [initial FAIL](evidence/manual_quotes_execution_2026-10-09/INITIAL_INDEPENDENT_REVIEW_FAIL.json), [final review](evidence/manual_quotes_execution_2026-10-09/FINAL_INDEPENDENT_REVIEW.json), [native CI](evidence/manual_quotes_execution_2026-10-09/FINAL_CI_RECEIPT.json) and [execution receipt](evidence/manual_quotes_execution_2026-10-09/FINAL_EXECUTION_RECEIPT.json). PR70 is unmerged and awaits final26E; no approval inferred from elapsed time or PR69's named grant.

Manual19native prices and USD/KRW·JPY/KRW inputs/timestamps stay in the device; KRW/native values and TARGET%p require complete supplied denominator, missing data NOT_AVAILABLE,>=7days STALE. Backup2 includes holdings/quotes/FX/clocks but no credentials; legacy1 remains supported. API-key structure has separate local password storage/delete, serviceNOT_SELECTED/queryOFF/disabledrefresh, self-only CSP, no outside scripts/polling/provider URL. KIS and FSC V2 plus3other free candidates are compared with coverage/FX/delay/limits/terms/authentication/CORS/secret risks and estimated implementation effort. No single free19/19+FX provider is confirmed; selected-service26E WAIT. User-only authenticated free Worker/server-secret relay is architecture only, not deployed. Broker holdings linking remains out of scope.

A-S2 mapping19/19, unresolved0; themes19/19. Chart source3/6 and Platform1/9 remain. A-G1 original authority/read/invalidation, A-G2 original production route/affected-owner acceptance and A-G3 broader formalFPIA obligations stay open. Recorded candidate defect blockers0 after R1 correction; formalFPIA NOT_RUN, F1–F25 LATER25, no globalPASS. Frozen/TARGET/scoring/Holdout/READ_ONLY/leases and operating-data/automation deferrals unchanged. The old Global guard rejects a register M by name/status despite true append; do not bypass or rewrite its governance policy. Exact prior bytes and all existing unrelated blobs are preserved and proved below.
