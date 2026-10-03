# GIE-004 · Track C C8: method-choice impact analysis (independent, read-only) · 2026-10-03

**Authority: none.** This is an independent integration-writer analysis prepared for the user's CDR-003 decision. The Track C scoped Decision Register and approval evidence on the Track C branch remain the authority. Nothing was changed on any branch.

- All executions were synthetic: the `SYNTHETIC_SOFTWARE_VALIDATION_ONLY` scope or standalone scratch scripts.
- Every alpha, B, n, L or phi used in a probe is illustrative only, **not a proposed default**.
- No CAL_VERIFY or Holdout access.
- Raw analysis: `GIE-004_trackc_c8_method_impact_2026-10-03.json`.

Subject: `origin/ccr-22e3ff16-p7n5k5` @ `97d1b94`, `evl/superiority.py` (C8_GSUP_STUDENTIZED_CBB_v1). `tests/test_evl_c8_gsup.py` gives 68 passed at this SHA.

## 1. Already-approved scope that can continue autonomously (CDR-003)

Approved clauses: Package A partial (A1/A2/A3/A4/A7/A11 with modification, A5 reconfirmed, A9 structure, A12 synthetic protocol), A6-S1..S8 (S5/S6 excluded), and A6 method Q1..Q6 conditional.

Open work inside that approved scope:

| Item | Class | Note |
|---|---|---|
| **Fail-open (a): the Q3 "Development-only" estimate is not enforced at `record_feasibility`** | LOCAL_FIXABLE (approved policy) | Executed probe: a forged estimate labelled `dataset_role: CAL_VERIFY` was accepted |
| **Fail-open (b): the Q4 / A6-S4 one-shot no-retest rule is not enforced across `campaign_id` / registry roots** | LOCAL_FIXABLE (approved policy) | Executed probe: a second access with changed alpha/seed was ACCEPTED and returned STAT_PASS. `GsupRegistry` is not wired to the foundation one-shot claim (`calibration_ledger.py` L151-157) |
| CI for the G-SUP commits | autonomous | No Actions run exists for `a156a35`/`97d1b94`. The workflow triggers only on `feature/track-c-evl` |
| The "independent" oracle reconciliation | autonomous | `tests/evl_c8_gsup_oracle.py` re-encodes the kernel's own conventions rather than the M-B variant used as Q1 approval evidence |
| Q2 evidence completeness: descriptive synthetic **power** report | autonomous, if non-gating | Making power a gate is method policy (item 6) |
| A7/A12/S8 wiring of G-SUP NOT_RUN states into the foundation evidence and acceptance path | autonomous, as long as only NOT_RUN states are emitted | `calibration_evidence.py` L55/L124 still emit `statistical_decision None` |
| Status-label consistency (A6 shown as `PROPOSED_NOT_APPROVED_NOT_ACTIVE` vs the recorded `METHOD_APPROVED_CONDITIONAL…`) | documentation, additive | no result impact |
| AR(1) simulation fidelity (burn=50 from x0=0 is not stationary) | LOCAL_FIXABLE once the family is confirmed | affects only phi ≥ 0.97 materially |

## 2. Method choices NOT yet approved: result impact and rationale

Classification is strict: if a choice can flip FEASIBLE/INFEASIBLE or PASS/FAIL, it is METHOD_POLICY, not an implementation detail.

| # | Choice (current implementation) | Result impact | Rationale for the current choice | Class |
|---|---|---|---|---|
| 1 | Development dependence estimator: lag-1 sample autocorrelation on **one** unspecified Development series; envelope phi = min(max(phî,0)+margin, 0.99) | Can flip FEASIBLE ↔ NOT_RUN_INFEASIBLE, which decides whether CAL_VERIFY is consumed. **Anti-conservative** at small Development n (phî is biased low, e.g. true 0.3 → mean 0.116 at n=12) and for dependence that is not AR(1)-shaped. The choice of series is not preregistered (cell shopping) | Simplest deterministic Development-only scalar (Q3 "predefined") | METHOD_POLICY |
| 2 | Envelope family `AR1_GAUSSIAN` only | Adding families can only make feasibility stricter. Gaussian AR(1) alone is optimistic for seasonal / MA / negative-lag-1 shapes | Single parameter matches the Q3 scalar | METHOD_POLICY |
| 3a | **Degenerate bootstrap replicate counted as an exceedance.** The Q1 approval simulation used the opposite convention (never an exceedance) | For n=2L, p has a floor of about 1/n, so **STAT_PASS is unreachable** below that alpha. The size-only gate still says FEASIBLE, so CAL_VERIFY is consumed for a structural STAT_FAIL. Under the approved simulation convention the same configuration is NOT_RUN before access | "Conservative: an undefined replicate never supports rejection" | METHOD_POLICY |
| 3b | Statistic ties counted as exceedance (`>=`) | Conservative. Matches approved Q6 (r+1)/(B+1) and the Q1 simulation | — | IMPLEMENTATION_DETAIL_WITHIN_APPROVED_METHOD |
| 4 | **Replicate studentizer uses n//L full blocks.** The approved simulation used ceil(n/L)−1 blocks | Identical when n%L≠0. When L divides n the kernel is slightly more liberal/powerful, **runs at n=2L where the approved variant is NOT_RUN**, and flips about 1–5% of decisions. So the approved size table does not exactly describe the implemented kernel in those cells | "Use every full block" | METHOD_POLICY |
| 5 | Seed convention: the decision seed is reused for every feasibility replication, and one index set is shared across all 8 cells | The feasibility verdict depends on the seed value (it can flip with the seed alone). Combined with fail-open (b) this enables seed shopping | "Size under the exact registered procedure" (conditional size) | METHOD_POLICY |
| 6 | Feasibility gate: size-only point estimate; no power condition; no Monte Carlo uncertainty bound | Powerless configurations pass as FEASIBLE and burn the one-shot CAL_VERIFY on an uninformative STAT_FAIL | Literal reading of the Q2/Q4 approval | METHOD_POLICY |
| 7 | Aggregation: any NOT_RUN cell makes the overall result NOT_RUN, even when another cell is NOT_REJECTED | Flips NOT_RUN ↔ STAT_FAIL reporting. STAT_PASS is unaffected | Fail-closed "undefined = NOT_RUN" | METHOD_POLICY |
| 8 | Statistic basis: control-relative net period return difference; one-sided H0 μΔ ≤ 0. The C3 path (e.g. `NET_OF_TRADING_COST_PRE_TAX`) is not bound | A different basis changes every statistic. It must stay consistent with the S7 and A9 units | Q1 package §0 | METHOD_POLICY |
| 9 | Q5 block rule: only a FIXED L is usable; the rule form is not approved | At small n, L effectively sets size and power | Only the fixed form is enabled | METHOD_POLICY |
| 10 | CAL_VERIFY consumption unit: G-SUP registry separate from the A4 foundation claim | Decides whether G-SUP can produce any result. If A4 consumes CAL_VERIFY first, G-SUP is permanently NOT_RUN | Additive implementation | METHOD_POLICY |
| 11 | A6-S7 effect floor: metric, unit and combination rule (deferred; no zero default) | Decides whether a final PASS is possible at all. Accessing CAL_VERIFY before S7 wastes the slot | Deferred by A6-S7 | METHOD_POLICY |
| 12 | Randomized controls excluded (UNSUPPORTED_SINGLE_DRAW) | Adding them enlarges the conjunction, lowering power. The current claim is unaffected | A6-S2 | METHOD_POLICY (keep as is) |
| 13 | A8 profile distinctness hard decision: not implemented | PROFILE_NOT_DISTINCT blocks the three-profile batch. Needs its own approved two-sided test form | Held: PROPOSED_NOT_APPROVED | METHOD_POLICY |
| 14 | A10 Champion/Challenger designation (fixture only) | Determines what G-SUP tests. Designation timing (before CAL_FIT vs before CAL_VERIFY) affects false positives | Held | METHOD_POLICY |
| 15 | A9 economic-gate formula identities (premium / opportunity-cost / risk-adjusted) | The same candidate can PASS under one identity and FAIL under another | Only gate order approved | METHOD_POLICY |
| 16 | Embedded constants: 0.0 floor / 0.99 cap on phi, burn=50, Development minimum n=3, 16-hex seed derivation | Material only at phi ≥ 0.97 or in marginal seed cases. Not covered by `registration_hash` | Implementation convenience | NUMERIC_CONFIGURATION (should become registered fields or be removed) |

**Conformance note on 3a and 4.** Q1 approved `C8_GSUP_STUDENTIZED_CBB_v1` with the M-B simulation as its evidence, but the record does not pin which convention defines v1. Two directions are possible:

- aligning the kernel to the approved simulation (ceil(n/L)−1 blocks; degenerate replicate never an exceedance, or NOT_RUN) would make the implementation match the evidence the user approved;
- keeping the current convention needs explicit approval plus a re-run of the size table for L | n cells.

## 3. Numeric configuration: separate preregistered gate before any real CAL_VERIFY (not bundled with method approval)

- alpha (per cell, IUT) and B.
- Fixed L, or the coefficient of an approved rule.
- Decision seed value; feasibility seed value and replication count.
- Size tolerance; envelope phi points; margin; minimum support (verify_periods).
- Effect-floor value.
- The A1 actual calibration configuration: interval, CAL_FIT/CAL_VERIFY boundaries and ids, n per calendar, frequency, and the Development window.
- A2 budget.
- A3/A4 grid, refinement and plateau settings.
- A9 limits; A8 magnitudes and family alpha (if A8 is approved).
- Power target and effect size (only if a power gate is approved).
- The embedded constants in item 16.

Package IDs N-S10/12/13/14/19/20/21 and N-D1/2/5 are referenced in the decision package, but no file on the branch defines them.

## 4. Pre-CAL_VERIFY hazards (resolve or explicitly accept before the numeric gate)

1. Under the implemented degenerate convention, any n = 2L configuration is FEASIBLE but structurally STAT_FAIL.
2. With S7 still deferred, any CAL_VERIFY access today would end NOT_RUN_EFFECT_FLOOR_DEFERRED and consume the slot.
3. Fail-opens (a) and (b) in §1.
