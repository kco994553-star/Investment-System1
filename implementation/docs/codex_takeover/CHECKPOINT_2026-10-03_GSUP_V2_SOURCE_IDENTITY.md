# G-SUP M-v2/source identity checkpoint — fixed-baseline Delta mode

Workflow: `GSUP_M_V2_SOURCE_IDENTITY_2026_10_03`.

The two requested approvals are recorded by an additive scoped Decision Register entry and exact approval blob `a5279d516c028f0a8cb9166ee2d54366da00877b`. M-B is authoritative for a separate future v2. Synthetic source identity admission is implemented and verified. The active authoritative M-v2 kernel remains **NOT_IMPLEMENTED_PENDING_ARITHMETIC_REDUCTION**; the synthetic identity compatibility wrapper intentionally delegates the unchanged v1 kernel. No v1 source/result/evidence has been replaced.

## Background Work / Agent Map

Stage: verified synthetic scope → final evidence publication. Verify:8/8 new ActionsSUCCESS, local/native1277PASS. Parent C8 maturityΔ0; separate source identity component DESIGN→SYNTHETIC_VERIFIED. No percentages.

```text
Scoped integration handoff
└─ root 🟢  final evidence publication
       ↓
M-v2 implementation / independent oracle (after arithmetic decision)
├─ root          ⏸ planned
└─ mb_v2_oracle   ⏸ planned
```

Completed workers are recorded separately below. C28 PR32/33 read-only review is a distinct completed workflow, not a newly completed source integration.

## Fixed baseline and exact proposal

- Workflow observed_at: **2026-10-03T06:48:04Z**. Baseline is never reset. The retained prior GitHub count snapshot has no exact API wallclock; see the explicit timestamp qualification alongside the immutable baseline JSON.
- Canonical baseline/current: `b8e39a2196a6d7794a04a0cd5393c68329e126ca`.
- Original Track C owner baseline/current: `ccr-22e3ff16-p7n5k5@b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565`, read-only upstream.
- Integration baseline/current: `codex/combined-integration-2026-10-03@86ad3628dd5c62c6d873e42511e577f24f4fb588`, Draft [PR30](https://github.com/kco994553-star/Investment-System1/pull/30).
- Proposal: `codex/track-c-gsup-v2-2026-10-03@675d0d298fbaab5b8473ed048a561ef84e2f3e78`, Draft [PR31](https://github.com/kco994553-star/Investment-System1/pull/31). Base/merge-base exact86ad; ahead14/behind0. Ownerb9 is also an ancestor, ahead100/behind0.
- Global baseline: `f26dc7adbfedd9209e757b5e8566c665c7bbd677`. Fresh current routing: `6dedaaf36a417e9301ba22ea9595bff5f37acb38`. **Two external Claude commits** are distinct from Codex changes. CDR-006/007 match scoped approvals; CDR-008 assigns Codex implementation and Claude read-only review; CDR-009 preserves the active-write exclusion. Global's branch-absence observations at06:58/07:03 are HISTORICAL and superseded by the actual PR31 checkpoint. No new arithmetic approval was found.

## Actual workflow delta

| Metric | Baseline → current / delta |
|---|---|
| Open PRs | 25 → 28, +3 total: Codex DraftPR31 +1; external owner DraftPR32/33 +2 |
| Remote branches | 38 → 41, +3 total: Codex proposal +1; external owner proposals +2 |
| Code proposal history | +14 commits, including normal history-preserving merges |
| Code proposal files | +22 added / 9 modified / 0 deleted |
| Code proposal lines | +16,719 / -10; includes diagnostic traces and evidence |
| Production source | +2 modules; existing source edits0 |
| Test cases/modules | +112 cases in4 new modules |
| Full regression | 1,165 → 1,277 PASS; existing1,165 RECONFIRMED |
| Scoped approvals | +2 recorded; old decision blockers -2, arithmetic blocker +1 |
| Parent Track C C8 maturity | SYNTHETIC_VERIFIED → SYNTHETIC_VERIFIED, Δ0 stages |
| Source identity subcomponent | DESIGN → SYNTHETIC_VERIFIED, Δ+2 stages; synthetic only |
| Active authoritative M-v2 kernels | +0; blocked on arithmetic choice |
| SOFTWARE_FROZEN | ±0; C0–C7 preserved, C8 NOT_FROZEN |
| Protected v1/Frozen source/tests changed | 0 |
| Scoped Decision Register | one authorized additive append; original byte prefix unchanged |
| Actual CAL_VERIFY / Holdout / grants / Official / canonical merge | +0 each |
| Codex Global writes / unapproved numeric policy changes | +0 each |

Code history and the final audit-only evidence commit are counted separately; this source proposal has14commits and the audit checkpoint adds one normal documentation/evidence commit without changing675. Workflow reruns never count as new tests. These deltas do not imply Official, LIVE, real-data validation, canonical integration or actual operation.

## Verify and preservation

Executed local full regression: Python3.11.16/NumPy2.3.5/pytest9.1.1, 1,277 PASS, zero failures/errors/skips. Actual tested commit3b6ed7eac3fe8f0f852b4d42eb57cf5f3ff497eb. Final675 changes only the additive-file CI guard/routing; all337 source/test blobs equal tested3b6. The guard itself was actually executed:41 owner-existing files preserved, precisely6 approved source/test additions permitted. Final exact-head GitHub CI is separately recorded below; it is not inferred from source equality.

New targeted groups: source protocol33, independent adversarial48, independent arithmetic diagnostic20, unmocked v1-kernel/result invariance11. Negative checks include stable identity under reencoding/relabeling/campaign changes, authority pin outside untrusted specs, incomplete metadata/provider/response lineage rejection, claim substitution, crash/retry/journal failure and durable consumption. Feasibility/access charge survives failed attempts. Synthetic test fixtures are not approved real configuration.

Independent final protection review:331 integration-existing source/test blobs,41 owner EVL blobs,232 pre-C8 Frozen blobs,7,351 canonical protected blobs and99 historical evidence blobs are byte-identical. The100th scoped-register record is an explicitly approved append, with original prefix SHA256 `e665f5a6c07abf849f3863b3535f89e811515dec6e2a3c4f93decbaae8f47597` unchanged. Four exact adopted C28 source files remain unchanged. The final preservation receipt's stale71d baseline-scope field is transparently corrected by its immutable addendum: selected1165 baseline was actual86ad Actions37102973395.

Trusted source protocol: synthetic coordinator authority is explicitly configured and pinned outside attempt specs; source/vintage/sample metadata precedes outcome reads. Content hashes are integrity evidence, not consumption identity. A fresh alternate bootstrap cannot replace the expected authority pin. Privileged reset/deletion/replacement of trusted authority configuration is outside this threat model. Legacy opaque consumption fails closed; no foundation-registry unification or real taxonomy/default was introduced.

## GitHub Actions

All **eight new final workflows SUCCESS**, each1,277PASS. This counts new runs only and does not recount the eight baseline runs. Native [37106686279](https://github.com/kco994553-star/Investment-System1/actions/runs/37106686279) checks out exact675d0d298fbaab5b8473ed048a561ef84e2f3e78, full1,277PASS/0fail/errors/skips and6 producer-Web E2E groups. Its separate Macro job actually checks out4a07099e36ec3cecda24b82ecedad53800f0aa81 and11PASS. Inherited P01, Invalidation, Technical input/model, US, SEC and Web check out synthetic PR merge547676da75308b02a35f9cef1b5be3b028bdf101; **different commits**, identical tree0d4852e3b682cad038fd432dc1625167022ca82e. Existing Web10groups, Language/Search8groups, Node26checks and entity metadata failures[] pass. Withheld browser fixture/evidence bytes equal prior86ad baseline; no publication grant is inferred.

Three connector-downloaded artifact ZIPs match GitHub's published SHA256 digests: native3a7054bbca344cf07bb3ff3520502f603f0d22e45efb33b24432e7d71f9aee69, Macro6816821106fe6f590ffa5cc5f138fc773ed5daef559542df4409fb7b83fba19a, originalWebb4e22c87c2a5d39032cfa86d4d1f710dd66933c0eee7902fa985e692a3256dfb. See [final receipt](evidence/gsup-v2/actions-review/FINAL_ACTIONS_REVIEW_RECEIPT.json) SHA25632b24c81533a081bd996e20735ea1fde6d69fda736d8e23b3dc3e2c9dac38b40 and [artifact manifest](evidence/gsup-v2/actions-review/ARTIFACT_MANIFEST.json) SHA256726eb3404b6b07873a49f647506eaf31a3d0035e23a6b0f5518a745737a2a8aa.

Final remote count snapshot observed2026-10-03T07:46:02.433621Z:28openPRs allDraft,41branches. External Claude proposals [PR32](https://github.com/kco994553-star/Investment-System1/pull/32) e9aee0cb8b80e17f7ae12e01156f6670135de2fa and [PR33](https://github.com/kco994553-star/Investment-System1/pull/33) 9626ab06cd2b93cdd250159347cdda5d08f76e03 appeared during this workflow. They remain READ_ONLY upstream; the independent docs/evidence C28 audit completed3/3 for each proposal as a separate fixed-baseline workflow; see CHECKPOINT_2026-10-03_C28_EVIDENCE_32_33.md. They are not Codex-authored PRs or automatically included in the green675 source.

## Completed work / optional agent detail

| Agent | Completed bounded task | Acceptance | Source branch/HEAD |
|---|---|---|---|
| adoption_audit | descriptor source and scoped validation; later topology audit | 5/5;2/2 | codex/gsup-source-identity-2026-10-03@f538893468502cef2e019f00d8f86703fd55b186 |
| mb_v2_oracle | independent three-reduction diagnostic/counterexamples | 4/4 | codex/gsup-v2-oracle-2026-10-03@2d67d84ab0cba547520cfb21f447d6564e7939c1 |
| track_c_audit | unchanged kernel invariance; preservation; metadata addendum | 4/4;3/3;1/1 | codex/gsup-identity-kernel-invariance-2026-10-03@881a6a21746f3a4e07515e25f38c9d966d5638ce |
| web_integration_audit | independent identity adversarial review; final CI artifacts | 4/4;3/3 | codex/gsup-v2-identity-adversarial-2026-10-03@f354be3622f6983b509df6cc845023119c15fe01 |
| root | approval record, unchanged-v1 wrapper, normal integration, full regression, exact publication, CI guard, scoped handoff | full regression, final8/8CI and evidence complete | codex/track-c-gsup-v2-2026-10-03@675d0d298fbaab5b8473ed048a561ef84e2f3e78 |

Completed agents are excluded from Active work. The production source identity mechanism and its compatibility wrapper are complete within the bounded synthetic scope; active M-v2 remains pending. No percentage, token/time/test-count progress proxy is used.

## Project maturity and dependency DAG

The complete24-row inventory is [CAPABILITY_MATURITY_CURRENT.json](evidence/gsup-v2/CAPABILITY_MATURITY_CURRENT.json). Existing project stages remain: DESIGN4, IMPLEMENTED1, SYNTHETIC_VERIFIED14, REAL_DATA_VERIFIED3, INTEGRATED1, OPERATIONAL0, UNDETERMINED1. Dynamic Workflow SOFTWARE_FROZEN is preserved per user; searched artifact absence does not prove no implementation. Research/metadata REAL_DATA_VERIFIED scopes are bounded and do not grant scored/Official outputs.

Critical path: explicit arithmetic choice → separate approved M-v2 → production-kernel independent oracle/exact M-B conformity → C8 approved-software combined acceptance → owner C28 adoption acceptance/canonical decision → QGV/Leaderboard and Technical/US/Macro permitted real/PIT paths → Producer/P01/Invalidation to existing Web → TrackB/Portfolio actual-operation → daily pipeline. Existing adoption/integration proposals and fixtures are preserved, not recreated. Source identity is an independently completed dependency; it does not consume real CAL_VERIFY or Holdout.

BRANCH_STATE: descriptor/diagnostic bounded synthetic implementation verified, exact675 published. INTEGRATION_STATE: DraftPR31 on DraftPR30; not merged. CANONICAL_STATE: NOT_MERGED, canonicalb8 unchanged. Canonical merge/deployment: NOT_RUN. Actual M-v2 kernel validation: NOT_RUN because arithmetic authority is pending. Bounded sourceidentity/diagnostic checkpoint: HANDOFF_READY_READ_ONLY_VALIDATION; active M-v2 task: USER_DECISION_REQUIRED. CDR-008/009 ownership remains explicit; this handoff does not invite replacement of Codex-owned source or scoped records.

## USER_DECISION_REQUIRED and next autonomous batch

M is approved and is not reopened. With identical Frozen C6 Python random.Random indices, n8/L3/B19/seed46 and synthetic [.01,.01,-.01,-.02,.02,.01,.01,.01], math.fsum gives r1/degenerate2/p.10 while literal NumPy2.3.5 cumulative-block reduction gives r3/degenerate0/p.20. Δp+.10, Δr+2, Δdegenerate-2; another Python3.11-sum comparison changes p.35↔.40. Fixed inputs/configuration are diagnostics only. The historical NumPy version was not recorded. No tolerance/rounding/default or active reduction was selected.

A user choice is pending among literal NumPy2.3.5 under Python3.11 with Frozen C6 indices, existing scalar math.fsum, or Python3.11 builtin sum. This boundary follows the user's§14 and exact PR21 [Worker Contract D.15](https://github.com/kco994553-star/Investment-System1/blob/f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798/implementation/docs/coordination/CLAUDE_CODE_WORKER_CONTRACT.md): “선택에 따라 투자 결과 또는 검증 결과가 달라지는 경우”. The concrete diagnostic is [on immutable GitHub](https://github.com/kco994553-star/Investment-System1/blob/f29ea6e4f5c041196a8311b0d685aa52d49eb3ff/implementation/reports/gsup_v2_oracle/ARITHMETIC_REDUCTION_REVIEW_2026-10-03.md). This does not request or imply actual numeric/CAL_VERIFY/Holdout approval.

After an explicit answer: append its exact authority record without rewriting this approval, normal additive v2 implementation branch commit, independent production-kernel oracle + fixed v1/v2 counterexamples + negatives, full regression and final exact-head CI, bounded scoped handoff. Assign implementation, independent oracle and preservation/CI workers by disjoint file ownership. No shared Global edit, source repin for test convenience, v1 rewrite or canonical merge.

The Primary Integration Writer can review these exact references read-only under CDR-008/009 and append its own Global routing. No external comment/message was sent by Codex.
