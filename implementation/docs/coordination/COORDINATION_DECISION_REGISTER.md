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
