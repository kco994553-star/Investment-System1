# TECHNICAL_REAL_MODEL_V1

Status: M1/M2/M4 implemented. M3 not approved and not implemented.
Not an Official Technical model. Not Track C validation.

Branch: `feature/technical-real-model-v1`, stacked on `feature/technical-real-producer-v1`.
PR #11 is not modified and is not merged.

## Path split

| Path | Code | Output |
|---|---|---|
| DEMO | unchanged `TechnicalEngine.evaluate` | synthetic placeholder |
| Real input record | unchanged `produce_company` | `TECHNICAL_COMPANY_RECORD`, model still not applied |
| Research | `technical/real_model_v1.py` | `TECHNICAL_RESEARCH_RECORD` |

The research record uses stored Yahoo `close` simple returns. `adjclose` is not read. Closes are not rewritten. Total return is not computed. There is no composite weight.

## Continuity

No exchange calendar exists in this repository. A fixed calendar-day gap is not a market rule (`gap_rule_days` is null).

Windows use an explicit `session_index` on the stored observations. Duplicate or non-monotonic timestamps fail. Missing session indexes make session-based features `NOT_AVAILABLE` (`SESSION_CONTINUITY_UNVERIFIED`). A hole in the session index makes any feature that needed the missing session `NOT_AVAILABLE` (`SESSION_GAP`). Weekend bars are not invented and missing observations are not filled.

## Corporate actions

`split_status=UNKNOWN` makes every price feature `NOT_AVAILABLE`. Volume can still be computed. `NONE` and `KNOWN` use the stored close unchanged.

## Availability

Each feature has its own status. Regime mandatory inputs are `r_20`, `r_60`, `structure`, `sigma_20`, `sigma_252`. If one is missing, regime and zone are `NOT_AVAILABLE`, not `WAIT`, `0`, or `MIXED`.

`v_20`, `rs_20`, `r_5`, and confirmed swing are not regime inputs. Swing confirmation uses ±5 stored sessions and does not confirm the current session.

## Regime and zone

1. `sigma_20 > sigma_252` and `r_20 < 0` → `HIGH_VOL` / `RISK_REDUCTION`
2. else trend `UP` and structure not `PRIOR_LOW` → `TREND_UP`; zone `ADD` only when structure is `PRIOR_HIGH`, otherwise `ENTRY`
3. else trend `DOWN` and structure not `PRIOR_HIGH` → `TREND_DOWN` / `WAIT`
4. else `RANGE` / `WAIT`

Sigma is the sample standard deviation (`ddof=1`) of successive stored-session simple returns. Zone is not an order. Integration multipliers are not applied. The -20% re-check is not part of this model.

Given these definitions, `PRIOR_LOW` already implies `r_20 < 0`, and `PRIOR_HIGH` implies `r_20 > 0`. The extra structure guards in rules 2 and 3 are still applied as approved.

## Not in this record

Scenarios and probabilities are `M3_NOT_APPROVED`. Placeholder shocks are not copied.

`publish_web_research` always raises. The existing producer export remains `NOT_AVAILABLE` until an explicit P01 decision. Web research publication stays blocked.

`REAL_TECHNICAL_RESEARCH_PRODUCER_READY` and `OFFICIAL_TECHNICAL_PRODUCER_READY` stay NO. Live Yahoo bytes do not carry a verified session index, and this module will not invent one.
