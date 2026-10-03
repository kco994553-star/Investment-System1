# Track C C8 A6 Statistical Method Package Q1–Q6 — CONDITIONAL APPROVAL

Approval processing clock: **2026-10-02T20:43:44+09:00** (actual KST); UTC 2026-10-02 11:43:44 UTC.
Authority: explicit latest user message approving Q1–Q6 per recommendation, with conditions. Source HEAD `ff78c4f`
(feature/track-c-evl); package `track_c_c8_a6_method_decision_package_2026-10-02.md` (ccr-22e3ff16-p7n5k5 862955a).
Supplements A6 partial approval (2026-10-02T20:04:01 KST, S1–S8); prior records unchanged.

- **Q1** G-SUP hard-decision method = versioned **studentized block-bootstrap (B)**, `C8_GSUP_STUDENTIZED_CBB_v1`.
  Existing C6 unstudentized kernel (A) may be preserved as computation/comparison evidence only, never a C8 G-SUP hard decision.
  Batch-means t (C) preserved as INACTIVE alternative; no automatic fallback.
- **Q2** Empirical size feasibility is assessed before actual CAL_VERIFY access by an approved synthetic/pre-access procedure that never reads CAL_VERIFY outcomes.
- **Q3** Dependence assumption = stricter of a predefined Development-only estimate and a separately preregistered conservative dependence envelope. Envelope values/margin NOT approved.
- **Q4** Failure of the approved feasibility criterion → NOT_RUN_INFEASIBLE. No automatic switch to A/C; no retest with changed block length/alpha/B/seed/effect floor.
- **Q5** Block convention fixed before CAL_VERIFY access as one fixed L or a pre-approved deterministic rule. Block selection from observed CAL_VERIFY results forbidden. Actual L or rule NOT approved.
- **Q6** p-value = (r+1)/(B+1); before CAL_VERIFY access verify the chosen α is reachable at that B. α and B NOT approved.

Not approved: size tolerance, dependence-envelope values/margin, α, B, L, seed, effect floor, minimum support. They require separate
preregistered configuration and power/feasibility evidence before real data access. Expected support n≈4–12 does not create any number.
If the approved feasibility condition is not met, G-SUP is NOT_RUN_INFEASIBLE, not PASS/FAIL.

Status: A6 = METHOD_APPROVED_CONDITIONAL / NUMERIC_CONFIG_PENDING (S7 effect-floor combination still deferred). A8, A10 NOT APPROVED.
C8 NOT FROZEN; 8/11 = 72.7%; Holdout UNCONSUMED; Package B/C unchanged.
Authorized next (Autonomous Execution Mode): versioned B contract, independent oracle, synthetic negative fixtures, feasibility-gate
infrastructure. Stop and request approval where actual numeric configuration or CAL_VERIFY access becomes necessary.
