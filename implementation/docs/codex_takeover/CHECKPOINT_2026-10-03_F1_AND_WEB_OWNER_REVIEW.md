# Background Work — F1 verified, Web owner review, M-v2 decision pending

This checkpoint is an additive successor to the source-identity and C28 evidence checkpoints at audit commit `e07beb9ecd77bdeb0cc94465259caa8c2f022f1f`. Those documents and their evidence remain unchanged. New reports use workflow cards, stage arrows and role groups, without tables or progress percentages. Archived upstream documents retain their original format and bytes.

> **Completed · Source protection / integration debt**
>
> Implementation ✓ → independent negative checks ✓ → full regression ✓ → exact Actions ✓ → HANDOFF_READY
>
> Implementation: `adoption_audit` — 4/4 acceptance.
> Independent checks: `same_tree_protection_review` — complete.
> CI and preservation: `track_c_audit`, `f1_source_preservation`, `f1_evidence_hashes` — complete.
> Next: Primary Integration Writer independently reviews Draft PR35; canonical merge remains gated.

> **Completed with findings · Web owner read-only review**
>
> PR34 exact source ✓ → independent browser/oracle ✓ → G3 still reproduced → owner follow-up
>
> Reviewer: `web_integration_audit` — original PR34 review 3/3 complete.
> Next: owner consumes the direct-methodology counterexample and producer-parity evidence. Codex does not write the active Web work set.

> **Paused · Authoritative G-SUP M-v2**
>
> M approval ✓ → reduction decision pending → separate v2 implementation → independent production-kernel oracle → regression / Actions
>
> Implementation and oracle workers are planned after an explicit answer, not reported as running.
> Source identity is already SYNTHETIC_VERIFIED; its compatibility wrapper uses the preserved v1 kernel. Active authoritative M-v2 remains NOT_IMPLEMENTED_PENDING_ARITHMETIC_REDUCTION.

## Fixed baselines and fresh remote

Original G-SUP workflow baseline remains **2026-10-03T06:48:04Z**: canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`, original owner `b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565`, integration `86ad3628dd5c62c6d873e42511e577f24f4fb588`, Global `f26dc7adbfedd9209e757b5e8566c665c7bbd677`, 1,165 PASS. Retained count baseline is 25 open Draft PRs / 38 branches; its API wallclock qualification remains in the prior immutable record. No baseline is reset.

F1 is a separate bounded workflow, `SHARED_SOURCE_HARDENING_F1_2026_10_03`. Its [fixed baseline](evidence/integration-final-2026-10-03/f1-actions-review/local-root-regression/BASELINE.json) uses source `675d0d298fbaab5b8473ed048a561ef84e2f3e78`, 1,277 full-suite PASS, 9 targeted PASS and one nonblocking F1 finding. The 08:07:10Z registration timestamp is the first root clock capture, not a claimed worker launch time. The 28 PR / 41 branch counts are the retained exact 07:46 snapshot. Standalone raw output for the before-9 target run was not located; its scoped checkpoint result is preserved with that qualification.

Fresh fetch preceded the [08:52:11.488111Z remote snapshot](evidence/integration-final-2026-10-03/remote-snapshot/REMOTE_SNAPSHOT.json): **30 open PRs, all Draft; 44 remote branches**. Canonical is still `claude/investment-system-top500-validation-alrugm@b8e39a2196a6d7794a04a0cd5393c68329e126ca`. Original Track C owner is still `ccr-22e3ff16-p7n5k5@b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565`.

Global routing is `integration/global-handoff-v1@5fafee22ae4c1d246b6f2ef1f3d870344d7627c4`. Exact archived routing is in [routing-snapshot](evidence/integration-final-2026-10-03/routing-snapshot/GLOBAL_CURRENT_HANDOFF.md). CDR-006/007 approvals and CDR-008/009 ownership remain CURRENT. Old branch-absence and worker-progress statements are HISTORICAL/SUPERSEDED by exact published receipts. GSI007 explicitly routes active external wf5 Web work. Global is an index, not method authority. No new arithmetic selection was observed, and Codex made no shared Global edit.

Relevant preserved topology:

- Canonical `b8e39a2` → Draft PR30 `86ad3628dd5c62c6d873e42511e577f24f4fb588` → Draft PR31 `675d0d298fbaab5b8473ed048a561ef84e2f3e78` → Draft PR35 `fc6720bdc8143e97bf25e37e4091b1f2aa54b69f`.
- PR35 branch is `codex/integration-hardening-2026-10-03`; its base and merge-base are exact PR31/675, ahead4 / behind0. These are normal history-preserving commits/merges. PR31 source stays unchanged and green at675.
- Owner evidence proposals PR32/e9aee0c and PR33/9626ab0 remain independent read-only upstreams, not silently included in the green source candidate. Their independent before/after evidence audit is already recorded in the preserved C28 checkpoint. Their Actions remain NOT_RUN in that review.
- Producer owner `feature/producer-infrastructure-v1@f8af596df4d235fee1f29bf0cb6c9a3cc0f89f36` → external Draft PR34 `integration/web/research-render-guard-v1@2b53b27fe0f570557159d02552911e9e1cc7be9c` → external active presentation branch `integration/web/production-state-presentation-v1@e91dc773af600ff66d31575ce3774490a0b0be8c`.
- The new presentation branch has no open PR in the snapshot. Its separate current-source review is appended below; it does not replace the immutable PR34 review.

## Actual delta

F1 versus its fixed675 source baseline:

- Commits **+4**, including normal integration merges.
- Files **14 added / 2 modified / 0 deleted**; lines **+991 / -0**. Evidence accounts for most lines. Only `producer_source_compat.py` and its owned test file are modified.
- New test cases **+18**; targeted **9 → 27 PASS**; full suite **1,277 → 1,295 PASS**. Existing1,277 cases are RECONFIRMED.
- Actions **7 new SUCCESS**. No legacy Web run was triggered by F1-only paths.
- Before mutation matrix: **10/10 false PASS**. After: **10/10 correct FAIL**. Independent probes **21/21 expected outcomes**.
- Production source files changed **0**; protected Frozen/v1 source/tests changed **0**; producer numerical-fingerprint changes **0**.
- F1 finding resolved **-1 in this proposal's bounded scope**. Canonical's state is unchanged; resolution is not a canonical promotion.
- Parent maturity **SYNTHETIC_VERIFIED → SYNTHETIC_VERIFIED, Δ0 stages**.

Cumulative source-proposal delta versus the original86ad G-SUP baseline:

- Code-proposal history **+18 commits**; unique changed files **36 added / 11 modified / 0 deleted**, lines **+17,710 / -10**. This excludes the audit branch's documentation/evidence commits.
- New test cases **+130 = 112 source/diagnostic/invariance cases + 18 F1 cases**; **1,165 → 1,295 PASS**.
- New Codex Draft PRs **+2**: PR31 and PR35. External owner Draft PRs **+3**: PR32, PR33 and PR34. Total observed open PR delta **+5**.
- Remote branches **38 → 44, +6 total**. The new presentation branch is an external owner branch, not Codex implementation.
- New exact final Codex Actions **+15 SUCCESS = 8 at675 + 7 atfc**. Old baseline runs and reruns are not counted as new tests or new capabilities.
- Source-identity subcomponent: **DESIGN → SYNTHETIC_VERIFIED, +2 stages**, synthetic scope only. Parent capability transitions **0**.
- User's M/source approvals recorded **+2**, old decision blockers **-2**, pending reduction decision **+1**. Actual numeric-policy selections **+0**.
- CAL_VERIFY accesses, Holdout consumption, publication grants, Official promotions, deployments and canonical merges: **+0 each**.

Relative to the prior e07 evidence checkpoint: F1 adds18 cases and seven confirmed Actions; repository open Draft count28→30 and branches41→44. PR34/source presentation work is external and G3 remains unresolved. Parent capability advances0 / regressions0; REAL_DATA_VERIFIED+0, INTEGRATED+0, OPERATIONAL+0, SOFTWARE_FROZEN±0. No new user decision is invented from the Web audit.

## Verify — F1 complete

The same-tree helper previously compared each shared file to itself. It now compares ten non-models shared source paths with immutable canonical Git blobs, with `git --no-replace-objects`. Missing Git, baseline object or expected path fails closed. Distinct external-tree equality checks and the two approved `models.py` states/mixed directions remain unchanged. This applies the approved protection contract without selecting a new model/policy convention.

Actual local full regression ran on exact `fc6720bdc8143e97bf25e37e4091b1f2aa54b69f`, Python3.11.16: **1,295 PASS, 0 failures, 0 errors, 0 skips**. [Local receipt](evidence/integration-final-2026-10-03/f1-actions-review/local-root-regression/LOCAL_REGRESSION_RECEIPT.json); JUnit SHA256 `4e7b8ff11346e3cedb5b02f2fa8c0ee3b309dd9359dcaa00fd21e895cb46b125`.

[Native Actions37109899437](https://github.com/kco994553-star/Investment-System1/actions/runs/37109899437) checks out exactfc: **1,295 PASS + six producer-Web withheld-contract E2E groups**. Its separate Macro job checks out `4a07099e36ec3cecda24b82ecedad53800f0aa81`: **11 PASS**.

Other successful final workflows are Technical model37109899400, Technical producer37109899401, US37109899426, SEC37109899391, P0137109899414 and Invalidation37109899449. Each actually ran1,295PASS at synthetic PR merge `d7c9908c827cac1a53e5b1654e0a7502ee10b34d`. That is a **different commit**, with the same tree `e236e62a6ff8b0a151710c5e7a77068d08ab0256` as exactfc. GitHub commit-object receipts and actual checkout log lines are archived. Legacy Web workflow is **NOT_TRIGGERED**, not PASS.

Two downloaded artifact ZIPs match GitHub's published SHA256 digests: native `d7f5e980a8a92a82076f09532de9133fa3b800384958c4daebbb14b1dcd34cd9`; Macro `525d4860fa54e09d091ccb45083bcc25b7613ddb1f75b3b9c464eafb3be34cdb`. Connector download was used; the previously blocked direct Azure route was not retried. Full [final Actions/preservation receipt](evidence/integration-final-2026-10-03/f1-actions-review/FINAL_RECEIPT.json) SHA256 `3ca6497e4843a16e3118d64915555571b80f3290d740cbcbc8de8fbb7cdbabc5` includes64 relative artifact hashes.

All215 production source files,45 EVL source/test paths,112 scoped Track C/G-SUP records and14 workflows match fixed675. Fingerprint stdout BEFORE/AFTER is byte-identical, SHA256 `f690f9c08b6b2692af5c0c1cdfc957c768ffa13841406f837f4f899518320866`. No source, v1 outcome, Frozen record or earlier approval was rewritten. No new full regression is required or claimed for this audit-only documentation commit.

## Verify — Web owner completed with unresolved findings

The [immutable PR34 review](evidence/integration-final-2026-10-03/web-g3-owner-review/upstream-2b53b27/FINAL_READ_ONLY_REVIEW_RECEIPT.json) examines exact2b53b27, with base/merge-basef8af596. Reviewer acceptance3/3 is complete; upstream G3 acceptance is **NOT_ACCEPTED**.

The original synthetic counterexample has section `state=LIVE` and direct `section.methodology.status=PROVISIONAL_RESEARCH`. The owner guard checks nested `section.producer.methodology.status` and recursive `research_state.status`, but omits direct methodology. Exact owner's app still renders `LIVE` and synthetic score11.11 in actual mobile Chromium. This is isolated hand-built data with zero external page requests; no real investment result or grant was accessed.

Independent exact-function matrix: nested methodology **10/10 blocked**, direct methodology **10/10 bypassed**. Existing owner tests **4 PASS** and browser fixture **11 groups PASS** coexist with that counterexample; they do not establish that G3 is fixed. The existing producer predicate accepts two published, nonresearch controls with an unrelated old diagnostic `research_state=IDEA`; the recursive owner guard hides them. This is a documented semantic difference, not an approved new withholding policy selected by Codex.

Owner `app.js` and `locale.js` changes are visible. Protected builder bytes and82 original tests are preserved;7,747 other base files are unchanged. Scoped Web status says historical M1/M2 FROZEN while later Language evidence covers scoped UI changes. No current approval/Frozen-supersession record is added in PR34's diff. Classification: **CONFLICT_PENDING_PRIMARY_SCOPED_AUTHORITY_CLARIFICATION**. Absence of an app byte pin is not permission. Primary must supply exact scoped authority; a user decision is raised only if a new Frozen change or materially different eligibility policy is actually necessary.

Observed owner Actions37109567361 and37109567406 are SUCCESS in metadata. Actual checkout/logs were **NOT_INSPECTED** in this read-only Web audit. Reviewer full suite and Actions dispatch: **NOT_RUN**. No Codex Web source/test edits, new UI implementation branches or owner commits occurred. No re-pin, upstream integration or external comment/message was performed.

New presentation branch exact `e91dc773af600ff66d31575ce3774490a0b0be8c` is the direct child of exact2b53b27. Its changed scope is five existing assets plus four new files, with no scoped approval/Frozen supersession. Its `researchMarker` function is byte-identical to PR34. The narrowly necessary existing mobile-browser counterexample was actually rerun on exacte91: direct methodology again renders `LIVE 11.11`, page errors[] and external requests0. It is separate presentation work, not G3 supersession. Reviewer acceptance3/3 is complete; no new repository tests, full suite, owner E2E or Actions run is claimed. [Separate new-owner review](evidence/integration-final-2026-10-03/web-g3-owner-review/new-owner-branch-review/READ_ONLY_REVIEW_RECEIPT.json) SHA256 `1e2f8da79acc9be323e6ca0f06a58b2031b214b463faecb6186b2b8de3f34ace`; previous receipts/manifests remain byte-identical.

## Maturity, ownership and handoff

The preserved [24-capability inventory](evidence/gsup-v2/CAPABILITY_MATURITY_CURRENT.json) remains the detailed per-capability owner/HEAD/PR/dependency/validation reference. Parent stages are unchanged: DESIGN4, IMPLEMENTED1, SYNTHETIC_VERIFIED14, REAL_DATA_VERIFIED3, INTEGRATED1, OPERATIONAL0 and one artifact-undetermined Dynamic Workflow entry. The three real-data stages are bounded research/metadata evidence, not investment-ready scored publication. Dynamic Workflow SOFTWARE_FROZEN is maintained per the user; artifact absence does not prove no implementation.

SOFTWARE_FROZEN is separate from maturity. C0–C7 are preserved; C8 is NOT_FROZEN. Synthetic PASS does not certify real data, Holdout, Official, forward validation or canonical integration.

F1 BRANCH_STATE: exactfc published and CI_VERIFIED; bounded scoped implementation HANDOFF_READY. INTEGRATION_STATE: Draft PR35 on Draft PR31/PR30, **NOT_MERGED**. CANONICAL_STATE: canonicalb8 **UNCHANGED / NOT_MERGED**. Source-identity BRANCH_STATE remains verified at675; active M-v2 remains USER_DECISION_REQUIRED. Web BRANCH_STATE is external active owner/read-only; INTEGRATION_STATE is G3_NOT_ACCEPTED, not integrated by Codex; CANONICAL_STATE is NOT_MERGED.

Codex can fast-forward its own proposal refs through exact Git object APIs and update Draft PRs; these actions actually succeeded. Direct Git transport push remains separately BLOCKED_HTTP401 and was not repeatedly retried. Sandbox is workspace-write, default network restricted with explicit network permissions, effective approval is auto_review rather than never. No auto-review rejection was encountered. Global remains Primary Integration Writer-owned.

Critical path: explicit reduction authority → separate exact M-B v2 → independent production-kernel oracle/counterexamples → C8 approved-software acceptance. In parallel, Primary reviews C28/F1 trial evidence and active Web findings. Real provider/calendar paths, publication grants and canonical merges retain their independent gates. No new capability is added to bypass these dependencies.

## USER_DECISION_REQUIRED and next batch

M remains approved; it is not reopened. With identical Frozen C6 Python `random.Random` indices and synthetic `[.01,.01,-.01,-.02,.02,.01,.01,.01]`, n8/L3/B19/seed46: scalar `math.fsum` yields r1/degenerate2/p.10; literal NumPy2.3.5 cumulative-block reduction yields r3/degenerate0/p.20. The actual difference is **Δp+.10, Δr+2, Δdegenerate-2**. Another Python3.11 builtin-sum example changes p.35↔.40. Historical M-B simulation evidence did not record its NumPy version; no tolerance or rounding workaround was chosen. These inputs are diagnostic fixtures, not actual numeric configuration.

The pending choice is (1) literal NumPy2.3.5/Python3.11 reduction with preserved Frozen C6 indices, (2) scalar `math.fsum`, or (3) Python3.11 builtin `sum`. Concrete [immutable arithmetic review](https://github.com/kco994553-star/Investment-System1/blob/f29ea6e4f5c041196a8311b0d685aa52d49eb3ff/implementation/reports/gsup_v2_oracle/ARITHMETIC_REDUCTION_REVIEW_2026-10-03.md). The pause follows user's§14 and exact [Worker Contract D.15](https://github.com/kco994553-star/Investment-System1/blob/f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798/implementation/docs/coordination/CLAUDE_CODE_WORKER_CONTRACT.md): “선택에 따라 투자 결과 또는 검증 결과가 달라지는 경우”. Report-format steering does not answer that pending choice.

Next authorized batch after an explicit selection: append exact scoped decision without replacing old records; implement additive v2; assign independent oracle and preservation/CI workers with disjoint write sets; fix v1/v2 counterexamples; run necessary negative/full regression and exact-head Actions; publish bounded handoff. No numeric configuration, real CAL_VERIFY, Holdout, registry unification, C8 Freeze, grant, canonical merge or deployment is included.

Completed independent READY tasks are handed off concretely. Current user decision blocks M-v2. Web follow-up stays with its active owner. The Primary Integration Writer can read this exact proposal/evidence and update its own Global routing; Codex does not write that shared index or send messages through external tools.
