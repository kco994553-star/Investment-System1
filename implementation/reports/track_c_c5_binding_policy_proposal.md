# TC-D3P-002 — C5 executable search scope / profile capability contract

Status: PROPOSED, NOT APPROVED. No C5 search or C5 Freeze is claimed.

## Why a policy decision remains

C4's prior missing-lineage problem has been repaired without changing core formulas.
The remaining issue is the meaning of configurable strategy controls, not a Python
binding error. PRODUCT_ARCHITECTURE.md and contracts/strategy.py advertise six
configurable keys. Three have no operational definition or consumer:

| Key | Existing evidence | Ambiguity that cannot be settled by wiring a name |
|---|---|---|
| risk_multiplier | Profile defaults 0.7/1.0/1.3; QGV and risk module metadata; Integration's common rm scalar cancels at normalization | Gross exposure/leverage, per-security allocation, or risk limits? These give different portfolios. |
| signal_threshold | Defaults 0.7/0.55/0.45; Technical engine has sign, last-return and volatility rules, no normalized confidence score | Which signal and units does the threshold measure? Mapping 0.55 directly to a return would invent a rule. |
| macro_warning_sensitivity | Defaults 0.8/0.6/0.4; confirmed Macro v0.1.1 thresholds are fixed | Changing confirmed Macro thresholds is prohibited. A downstream response overlay would require its own financial definition. |

The current adapter rejects these controls instead of silently running identical
strategies. Metadata-only profile labels remain provisional, not Official.

## Recommended decision

Approve the first executable C5 research scope as **cash_buffer + technical_lookback**.
- These two controls have verified effects on exposure and Technical decisions.
- execution_deadband_pp remains executable for order-intent tests but is excluded
  from target-weight return optimization until an execution/fill/cost contract exists.
- The three undefined controls remain UNSUPPORTED_FOR_EVL_SEARCH, not optimized,
  not certified functional, and not silently replaced with invented financial rules.
- Preserve the mandated stage order. Baseline, Technical, Portfolio/Risk and
  Interaction can have eligible searches; QGV, Macro and Integration stages retain
  unchanged inputs and explicitly record NO_ELIGIBLE_BOUND_PARAMETER.
- C5 software acceptance will disclose this capability boundary. It cannot certify
  complete six-control profile optimization or promote any integrated profile.
- Reopening the other controls requires explicit upstream operational definitions
  and behavior tests, without changing frozen core scores.

This decision changes the advertised executable coverage of the first C5 search,
not EVL_SPEC_v0.1, the stage ordering, the split policy, locked rules or gate rigor.
The alternative is to define all three financial controls before the first C5
search. That would require choices about exposure/leverage, signal units and Macro
response; those choices are not inferred here.

Authority: EVL_SPEC_v0.1 §1 ownership, §2 core immutability, §13 stop/report on
SSoT/architecture conflict; supplied code.md §23.7 covers product/contract decisions.
The user's autonomous D1/D2/D3-C authorization covers implementation repairs, not
inventing financial behavior for previously undefined controls. This proposal is
ready for one scope decision. C0–C4 software freezes remain valid while it is pending.

## Approval — 2026-09-29 19:19:50 KST

User replied “어 진행해” to the explicit TC-D3P-002 scope approval question.
Recommended scope above is APPROVED. The original proposal remains historical.
Only cash_buffer and technical_lookback are eligible for first C5 search. No new
meaning is assigned to the three undefined controls; deadband remains order-only.
