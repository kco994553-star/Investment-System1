# TC-D3P-005 — C6 diagnostic roles, status semantics and Freeze-evidence scope

Recorded: 2026-09-30 20:20:03 KST.
Status: PROPOSED / NOT APPROVED / NOT ACTIVE.
TC-D3P-004 option A items 1–8 were explicitly APPROVED at 2026-09-30 20:16:28 KST.
This proposal does not change the approved mathematical methods or silently downgrade diagnostics.

## Exact authority gap

1. EVL_SPEC §5 says "Statistical controls include" PSR, DSR, PBO, bootstrap and
   multiple-testing/Reality Check. It does not define a diagnostic status enum,
   a software-freeze acceptance algorithm or an explicit MANDATORY/ADVISORY map.
2. EVL_SPEC §6 explicitly calls execution, costs, parameter/regime/universe perturbation,
   bootstrap and drift "Required robustness checks"; none may be made advisory by convenience.
   Negative controls are listed, but their per-control Freeze role is not separately serialized.
3. Approved TC-D3P-004 A6: "Statistical significance levels and economic materiality are not
   defaulted here; C8 must freeze its threshold contract before decisions."
4. Approved A8: "Statistical diagnostics do not on their own imply NO_EVIDENCE_OF_SKILL
   or skill; C8 applies its separately frozen indistinguishability/hard-gate contract."
   A8 also says incomplete/failed/invalidated families cannot support full C6 acceptance.
5. Current C0–C5 and C6 execution acceptance are explicitly software/fixture-only.
   Neither EVL_SPEC nor A specifies whether that same fixture-only acceptance can satisfy
   the new mandatory-diagnostic C6 Freeze rule, or whether an actual complete research family
   must be analyzed first. Existing historical software freezes do not settle the newly added rule.

Two unsafe interpretations are rejected: NOT_RUN counted as PASS, and a computed probability
silently called statistical success with an invented alpha. No advisory waiver is active.
No diagnostic classification is applied where its authority is unresolved.

The user's latest instruction explicitly requires stopping if this classification/effect requires
a new policy. The acceptance/evidence gate cannot be implemented with invented semantics.
C6 remains IMPLEMENTING / NOT FROZEN. No new diagnostic has been executed or assigned PASS.

## Concrete common classification and status contract for approval

Proposed classification (not active until approved):

| Diagnostic/check | Proposed Freeze role | Source and limitation |
|---|---|---|
| PSR | MANDATORY | EVL_SPEC §5; approved A2 |
| DSR: distinct full candidate identities | MANDATORY | Approved A3 requires both views |
| DSR: all charged attempts | MANDATORY | Approved A3 requires both views |
| Full-family CSCV/PBO, including tied selections | MANDATORY | EVL_SPEC §5; approved A4 |
| Joint circular-block bootstrap | MANDATORY | EVL_SPEC §§5–6; approved A5 |
| Reality Check against equal-weight/simple baseline | MANDATORY | Approved A6 always reported |
| Reality Check against market-cap baseline | MANDATORY | Approved A6 always reported |
| Parameter perturbation | MANDATORY | Explicitly required by §6; A7 |
| Regime perturbation | MANDATORY | Explicitly required by §6; A7 |
| Universe perturbation | MANDATORY | Explicitly required by §6; A7 |
| Random ranking control | MANDATORY | §6 control; A7 |
| Randomized weight control | MANDATORY | §6 control; A7; no investor weights |
| Equal-weight/simple control | MANDATORY | §6 control; A6–7 |
| Market-cap control | MANDATORY | §6 control; A6–7 |
| Parameter drift | MANDATORY | Explicitly required by §6; A7 |
| Baseline execution and one-opportunity delay | MANDATORY | §6 and approved TC-D3P-003 |
| Isolated execution cost 1x/2x/3x | MANDATORY | §6 and approved TC-D3P-003 |
| Additional unregistered diagnostics | Cannot support acceptance | Registration cannot follow results |

No listed C6 diagnostic is proposed as ADVISORY. If the user specifies an advisory item,
its exact identity, waiver scope and reason must be recorded before execution; reasons,
missing evidence and affected scope must accompany any NOT_RUN. An advisory label can
never remove an Official promotion requirement imposed by EVL_SPEC.

Proposed status semantics:
- PASS: the registered method actually ran on complete eligible immutable evidence, with
  valid finite/defined outputs, correct family/partition/method lineage and all stated
  computational integrity requirements met. PASS is diagnostic-execution/protocol acceptance,
  NOT investment skill, significance, promotion or economic success.
- FAIL: observed contract/integrity violation, invalidation, family shrink, changed frozen input,
  forbidden partition or other violation. No valid success evidence can be returned.
- NOT_RUN: required evidence, aligned series, method prerequisites/parameters or valid sample
  support missing; no usable diagnostic conclusion. Record reason, missing evidence and scope.
- No fabricated, interpolated or zero-filled series; no scalar aggregate substituted for a series.
- A missing threshold never becomes statistical PASS. C6 reports numerical estimates only;
  statistical/economic decision status remains NOT_ASSESSED_PENDING_C8.
- Any MANDATORY status other than PASS blocks the corresponding acceptance scope.
  In particular MANDATORY evidence-insufficient NOT_RUN blocks C6 SOFTWARE FROZEN.
- Preserve each status separately; a successful bootstrap cannot offset NOT_RUN DSR/PBO.
  Each DSR view and each required benchmark comparison retains its own status and provenance.

These semantics retain approved A6/A8's C8 boundary. A user seeking a statistical-performance
PASS in C6 must first provide a compatible threshold authority; it cannot be invented here.

## Freeze-evidence scope: two reviewable choices, no recommendation

Option S — Software-only C6 Freeze with complete explicit fixture acceptance:
- All mandatory diagnostics must actually PASS under the common protocol semantics on a
  preregistered, complete, explicitly labeled synthetic software acceptance family.
- Fixtures test algorithms/interfaces/integrity; they do not substitute for missing real
  investor weights, upstream source evidence or a real research result.
- Every required perturbation/control/drift path must also have complete explicit software
  fixture evidence, with no NOT_RUN in the primary software acceptance artifact.
- Negative tests must prove FAIL/NOT_RUN block Freeze. Expected rejection in a test is not
  a PASS diagnostic in an acceptance family.
- Real-data research diagnostic artifacts remain separate and blocked when evidence is missing.
  Their MANDATORY NOT_RUN can never support a research-validation PASS or promotion.
- C6 SOFTWARE FROZEN is limited to software acceptance; C7/C8 cannot treat it as actual
  validated candidate, skill evidence, Official profile or completed real-data diagnostics.
- Investor-QGV remains FUTURE_TRACK_C_INPUT. All fixtures are generic testing inputs,
  never named-investor profiles or fabricated real evidence.

Technical effect: permits the software phase sequence after complete algorithm acceptance while
retaining a separate actual-research evidence gate. It does not resolve missing real family/control
coverage. This scope split is proposed explicitly; it is not currently treated as authorized.

Option R — Actual complete research evidence required for C6 Software Freeze:
- Software tests are necessary but do not satisfy mandatory diagnostic evidence.
- Every mandatory diagnostic must PASS on an actual preregistered complete PIT research
  family, with actual aligned upstream/execution/control/perturbation/drift evidence.
- A missing aligned series or control source produces NOT_RUN and blocks C6 SOFTWARE FROZEN.
- Existing synthetic regression remains software evidence only. No Holdout access to fill gaps.
- No need to require investment significance at C6; C8 still owns that decision.

Technical effect: ties software Freeze to available actual research coverage. The current repository
has no accepted complete real C6 family/control/perturbation package, so Freeze stays blocked until
that evidence exists. It prevents advancing C7 via a software-only acceptance artifact.

Approving this proposal requires:
1. the common all-MANDATORY classification and PASS/FAIL/NOT_RUN meanings above; and
2. explicit selection of Option S or Option R, or a concrete alternative mapping/scope.

Unchanged: TC-D3P-004 methods, C0–C5 frozen contracts, approved execution policy, upstream scores,
Track A artifacts, Tracks B/D/E/Web, TAX_MODE=EXCLUDED, once-only sealed Holdout, immutable lineage,
full candidate family and no automatic optimization/promotion/merge.

Next after decision: implement approved C6 statistics/perturbation/controls/drift with this exact
acceptance scope, targeted -> unchanged C0–C5 -> full regression -> PIT/lineage/Holdout/boundary audits
-> evidence -> fast-forward upload -> Actions -> C6 Freeze judgment. C7 cannot start before C6 Freeze.
