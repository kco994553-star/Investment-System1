# TC-D3P-003 v1 — APPROVED

Approval recorded at actual clock time: 2026-09-30T19:38:07+09:00 (KST / UTC+9).
User explicitly approved the existing proposal items 1–8 unchanged.
Scope: Track C C6 research execution baseline; not broker/live execution or a claim of exact real fills.

Approved proposal Git blob: f8d0b148e787e490e7e958738533636327175594.
Approved source HEAD: 34973baa77925815e1950fcc9d1954b74bfc009f.

# TC-D3P-003 — EVL execution-delay / trading-cost stress contract v1

Status: PROPOSED / NOT APPROVED / NOT ACTIVE.
Scope: C6 research robustness. No broker connection, live order or paid data purchase.

## Verified gap

EVL_SPEC_v0.1 §6 requires execution delay and 1x/2x/3x trading-cost stress.
IntegrationEngine currently produces target weights and PROVISIONAL order intents,
not fills. SimulationEngine compounds externally supplied returns. C3 accepts a
trading-cost fraction of opening equity; it does not supply a fill model. Repository
inspection found no operational execution delay, fill-price or slippage contract.
TC-D3P-002 explicitly excluded order-only deadband from target-weight optimization.
A target-weight return series cannot establish execution-delay robustness merely
by shifting its dates or subtracting an arbitrary fee.

## Recommended general policy (single reusable approval)

1. Pre-register an execution schedule per security/session, decision timestamps,
   target/order path, starting positions/cash, price convention, source/vintage,
   currency and cost model. Freeze these before observing scenario results.
2. Baseline delay=0 means the first registered tradable opportunity strictly after
   the decision. Stress delay=1 means the next actual registered opportunity after
   that baseline opportunity. This is not one calendar day or one rebalance period.
   Extra delays may only be added by prior registration and must all be reported.
3. Freeze the original decision path for the paired comparison. Do not re-optimize
   or use later outcomes to replace an order. Holdings remain unchanged until an
   eligible fill; cash/positions and subsequent P&L follow the scenario's actual
   execution path. Missing valid quotes, untradeable instruments, insufficient cash
   or undefined fill/capacity rules yield NOT_RUN/REJECTED with reason, never a
   synthetic fill. Partial-fill/cancel rules require explicit upstream definitions.
4. Execution outcomes may be published after decision_time, but their provenance,
   vintage and available_at must be present and <= evaluation_time. They are never
   passed to predictors or research fitting as decision-time features.
5. Use explicit per-scenario execution evidence (positions, fills, gross P&L,
   nonnegative trading costs, opening equity). No default fee/spread/slippage and
   no double counting spread/slippage already embedded in fill prices.
6. For each fixed execution path, report costs at 1x/2x/3x. Multiply the separately
   identified monetary trading-cost component, then divide by that period's
   registered opening equity for C3. Freeze gross P&L/filled quantities for this
   sensitivity comparison. Insolvent results fail closed; no cash top-up or
   rebalancing is invented to rescue a scenario. This is fixed-path cost
   sensitivity, not a claim to model endogenous market impact at larger sizes.
7. Retain all delay × cost results with Trial Ledger and input/report hashes.
   Synthetic fixtures are SOFTWARE evidence only; incomplete real execution
   evidence cannot support a robustness PASS or Official promotion.
8. TAX_MODE=EXCLUDED. No change to frozen QGV/Technical/Macro rules, no immediate
   activation of deadband optimization, no automatic promotion or PR merge.

## Concrete boundary example

Decision 10:00; registered opportunities 10:05, 10:10, 10:20. Baseline uses 10:05;
one-opportunity stress uses 10:10. A missing 10:10 quote is reported as missing;
it is not replaced after results by the best later price. A pre-registered halt/
calendar rule may mark an opportunity ineligible before choosing eligible slots.

If a scenario's opening equity is 100, gross P&L is 2 and separately identified
trading cost is 0.1, the fixed-path 1x/2x/3x net returns are 1.9%, 1.8%, 1.7%.
Those numbers illustrate units only and are not default costs or expected returns.

## Why D3-P rather than an implementation choice

Choosing the first tradable price, delay interval and whether costs alter the
execution path changes the evaluated strategy and economic results. Existing
SSoT does not choose among these conventions. EVL_SPEC_v0.1 §13 and supplied
code.md §23.7 require a policy decision rather than invented financial behavior.
This approval can cover repeated execution scenarios as D3-C; no per-security
exception approvals are proposed. C6 remains PREFLIGHT_ONLY / NOT FROZEN.

Non-blocking C6 preparation: original-method references identified for PSR/DSR,
PBO/CSCV and Reality Check; no statistical implementation or result is claimed.
- https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
- https://escholarship.org/uc/item/4w1110bb
- https://users.ssc.wisc.edu/~behansen/718/White2000.pdf


## Approval overlay

The PROPOSED / NOT APPROVED / NOT ACTIVE statements above are the preserved proposal history. TC-D3P-003 v1 is now APPROVED for implementation. Baseline is first registered eligible opportunity strictly after decision; delay is one following eligible opportunity. Fixed quantities/gross P&L and separately identified execution costs at 1x/2x/3x. No invented fill/fee. Missing evidence fails closed. No partial-fill/capacity/cancel/retry/auction/impact model. PIT, lineage, Train/Holdout isolation and TAX_MODE=EXCLUDED remain locked. Approval does not declare C6 frozen or consume Holdout.
