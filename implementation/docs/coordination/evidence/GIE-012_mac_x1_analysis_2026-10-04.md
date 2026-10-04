# GIE-012 · MAC-X1: Track C Frozen acceptance on an integrated or advanced canonical · 2026-10-04

**Authority: none.** Integration analysis by the Primary Integration Writer under CDR-013. Nothing was merged, pushed or commented. The frozen tools (`track_c_c6_acceptance.py` `a60c4c5f`, `track_c_c7_acceptance.py` `6b9362d0`, `track_c_c8_partial_acceptance.py` `e587a8d5`), the Frozen records, owner and Codex branches, and PR #40 were not modified or relabelled. No CAL_VERIFY, Holdout or real-provider access. Canonical `b8e39a2` unchanged.

Workflow `wf_89a6c422-edf` (6 agents, 0 errors): failure reproduction, Frozen semantics and decision class, CI and ownership context, design, and two adversarial design reviews. The implementation and verification phases did **not** run: both reviews refuted the design (§4), so the gate stopped before any code was written. Raw results: `GIE-012_mac_x1_analysis_2026-10-04.json`. All runs used private clones; local canonical refs were moved only to reproduce conditions and restored.

## 1. Root cause

Reproduced with the unmodified tools. Baseline S0 (`b9e01a9` with canonical `b8e39a2`) passes all three tools, and its evidence is byte-identical to Actions run 37097149378.

Three mechanisms, none of which is a Frozen violation:

1. **Live canonical pin.** C6.a compares the runner's fetched canonical ref with the hard-coded `b8e39a2`; C8.6 compares it with `canonical_head` inside the blob-pinned C8 user approval record; C7 inherits C6.a. Any canonical advance fails them, even with an identical tree, and even immediately after Track C's own landing. **No merge order avoids this.**
2. **Closed-world new-file allowlists.** C6.d, C7.3 and C8.4 reject every file added anywhere outside a fixed Track C list. Every other capability trips them, and so do the approved Track C v2 files in the #31 lineage (CDR-006..012).
3. **Whole-package code identity.** Track C's provenance identity (`calibration_contracts.code_hash()` and `evl_c6_fixture.CODE`) hashes every `*.py` under `src/investment_system` (141 files at `b9e01a9`, 204 at #40). The Primary Integration Writer reproduced it: `b9e01a9` `0ef3a900`, #40 `df34b84f`, `b9e01a9` plus one empty foreign package file `2ab94d34`. Any capability that adds Python source changes Track C's code identity; a C8 registration bound to `b9e01a9`'s identity is rejected on #40 by Track C's own `validate_plan` ("current code identity mismatch"). With the code identity normalised in memory (counterfactual only), #40 reproduces the Frozen acceptance hashes bit-exactly (C6 `a9ca68be`, C7 `516ca461`), so the acceptance behaviour is preserved; only the code-identity binding depends on the base.

Every Frozen identity check passes on every integrated tree: C6.b/c/e/f, C7.1/2 and C8.1/2/3/5 never fire. The Frozen hashes reproduce only at their own evidence-head classes (C6 at `166dcba`…, C7 at `c5932f9`…, C8 partial at `ff78c4f`…) and already differ at `b9e01a9` because of mechanism 3.

The Frozen records define acceptance as exact-tree synthetic software acceptance relative to `b8e39a2`, and they require a separate **Integration Audit** when canonical advances or Track C integrates. That audit is **never defined or approved** in the records.

## 2. Affected PRs (dependency matrix, 35 heads merged onto the Track-C-landed tree)

- Every owner chain is add-only against `b8e39a2` and touches 0 Track C paths. It trips only the new-file checks, with a count equal to its added files: #21 2, #13 16, #16 21, #5 16, #6 25, #7 42 (+#33 43), #9 51 (+#32 52), #17 63 (+#27 64), #19 70, #29 77, #34 55, #36 59, #10 33, #14 27 (+#26 28), #11 15 (+#22 17), #15 20 (+#23 21), #18 30 (+#24 31), #12 56 (+#25 59), #37 3, #28 412, docs/qgv-context 7.
- The Technical/Macro chains and A1 adoptions do not modify the IF-1 trio.
- Code identity (mechanism 3) changes for every chain that adds Python under `src/investment_system`; #21, #37 and docs-only branches do not change it.
- The Codex lineage (#31/#35/#39/#40) changes exactly 2 tool-allowed Track C paths (workflow pip pin; pure append to the decision register) and adds 15–17 Track C-namespace v2 files.
- Only `track-c-evl-validation.yml` runs the tools (push to `feature/track-c-evl`, dispatch). It has never run on the #30–#40 trees, and nothing runs on a push to canonical.

## 3. Candidate solutions and decision class

| Candidate | What it is | Weakens a Frozen invariant? | Class |
|---|---|---|---|
| A. Frozen Projection Identity Audit (FPIA) | additive PIW tool: replay the unmodified tools at the Frozen evidence heads and at the Track C head; run them unmodified on a projection holding only Track C's paths; require byte identity of Track C content; classify every other change as add-only and non-interfering; re-run the acceptance computations on the merge-result tree | no, if the code-identity divergence is reported as DIVERGED and never pinned to PASS | building it as evidence: D1/D2. Adopting its verdict as Track C acceptance or the canonical-merge gate: **D3** (§D5, §D12, §D15, §N) |
| B. Merge-ordering policy (Track C first and alone) | sequencing only | no, but does not fix MAC-X1 (the pin fails right after Track C lands) | D3, and ineffective |
| C. Re-baseline the frozen tools in place | edit CANONICAL, extend allowlists, re-pin the C8 approval record | yes (confinement, pin semantics); needs hard-coded SHAs and foreign path lists | D3, prohibited by CDR-013 |
| D. Owner-issued successor tools (`*_v2.py` by the Track C owner / Codex) | same logic as A, owned by Track C | no, if it mirrors A | D3 (new Frozen acceptance meaning, owner scope) |

## 4. Adversarial design review: refuted

Both reviewers refuted the FPIA design as specified, with measured sandbox counterexamples:

- **Code identity pinned to PASS (high).** The design normalised `code_hash` back to the projection's value, so a foreign capability that changes Track C's provenance binding would still be labelled identity-preserved.
- **Import and test-runner bypasses (high).** Committed `.pyc` bytecode under `__pycache__` replaces executed code while the source blob stays identical; a committed `*.dist-info` pytest11 plugin turns a failing test into a pass; pytest 9.1.1 config files (`pytest.toml`, `.pytest.toml`, `.pytest.ini`) were not banned; extension-suffix and `.gitattributes` gaps.
- **Unattributed appends to the Track C decision register (medium).** The overlay prefix rule accepted a foreign append to Track C's scoped authority record.
- **Unauthenticated inputs (medium).** The Track C head and the verified v2 head were free CLI parameters, so any branch could be declared the reference; the replayed tool set was fixed at three tools.
- **Hidden ordering assumption (medium).** If another capability appends to a shared overlay (for example the root CURRENT_HANDOFF) before Track C lands, `git merge` conflicts and the append-only checks interact; the "order-independent" claim does not hold.

Classification: both reviewers agree that building an evidence-only audit is D1/D2; one reviewer found that the verdict, as specified, embeds choices that change the validation result (§D15). The reviewers' required changes are recorded in the raw JSON and become the specification if the user chooses option (a) below.

## 5. Decisions for the user (D3), with recommendation

1. **How Track C acceptance is established on an integrated or advanced canonical** (the undefined Integration Audit).
   - (a) **Recommended.** Frozen records stay exact-tree history, unchanged. For each candidate merge-result SHA, a hardened PIW Integration Audit certifies Track C content identity to the accepted Track C head, add-only and non-interfering other changes (bytecode, plugins, test config and startup hooks banned), the unmodified tools passing on the Track C projection, and the unmodified acceptance computations passing on the merge-result tree, reproducing the Frozen hashes when code identity is normalised. The frozen tools' pin and new-file failures are recorded verbatim, never converted. Code identity is reported separately as DIVERGED with the new value (item 2). Recorded as a new CDR and a Track C scoped register entry; precedent: Track A's FROZEN_VERIFIED integration audit at canonical merge.
   - (b) The Track C owner and Codex issue versioned successor tools with the same logic.
   - (c) Narrow Track C's code identity to its dependency closure: a Frozen contract change that invalidates every recorded hash; not recommended.
   - (d) Keep Track C off canonical for now; MAC-X1 stays open.
2. **Code identity after integration.** After any canonical merge that adds or changes Python under `src/investment_system`, Track C registrations bound to the previous identity fail closed. (a) **Recommended:** accept this fail-closed behaviour; Track C registrations for any future run are made on the final canonical tree after the last code change. (b) Narrow the scope (= 1c).
3. **v2 files (CDR-006..012)** are outside the frozen tools. (a) **Recommended:** certify by byte identity to an independently verified head recorded in a GIE/CDR (today `c9e0fa7`, GIE-011), bound in-tool to that record, plus a v2 test re-run. (b) Require owner tool coverage first.
4. **Shared root overlays edited before Track C lands** (merge conflict on append-only files). (a) **Recommended:** keep fail-closed; resolve as a normal history-preserving merge by the owners, then audit the exact result. (b) A merge-ordering rule (not needed if (a)).
5. **Track C's own branch CI** goes red after any canonical advance because of the pin. (a) **Recommended:** accept, and rely on the integration audit for canonical. (b) Owner successor tools later (1b).

## 6. Recommended integration order once item 1 is decided

MAC-X1 does not impose an order (no order avoids the pin). The order follows dependency chains and readiness (§M; GIE-009, GIE-011):

1. Implement and verify the hardened audit per the reviewers' required changes; run it on `b9e01a9` alone and on #40 with the verified v2 head.
2. Owner actions from GIE-009/011: A1 adoptions into owner branches; IF-2 sentinel conversions under the second-merger rule; Leaderboard owner pushes CI-green before Track C, Technical or Macro land (QL-B5); CI runtime ports (`0ea00d2` + numpy 2.3.5); RIG F6.
3. User decides the Track C landing vehicle (`b9e01a9` lineage or the #31/#35 lineage carrying CDR-012 v2).
4. Each canonical merge (a user decision, §D12) is preceded by the audit on its exact merge-result SHA and re-audited after any canonical advance. #21 and other docs-only branches do not change code identity and can go at any point once item 1 is decided.

Maturity transitions: none. Nothing here approves numeric configuration, CAL_VERIFY, Holdout, C8 Freeze, grants, Official/LIVE, the #17 digest repin or a canonical merge.
