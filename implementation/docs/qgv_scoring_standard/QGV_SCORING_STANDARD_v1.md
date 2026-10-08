# QGV Scoring Standard v1

Status: **STANDARD v1 · UNCALIBRATED**. The user fixes these meanings before
real-data calibration. This adoption does not claim CALIBRATED, PIT-tested or
OOS-tested results.

Authority: user D3-R decision dated 2026-10-08, recorded append-only in Global
Decision Register CDR040 and
`implementation/docs/coordination/evidence/main_qgv_standard_v1_2026-10-08/ADOPTION_RECEIPT.json`.
The forward effective recording time is **2026-10-08T11:50:25Z**. This is the
actual receipt-recording time, not an inferred earlier submission timestamp.
Historical saved results and previous provisional evidence remain unchanged.

Exact source HEAD: `d1566aeb1bbf11b1d514ad874b069d8b127ff1c7`, existing
`codex/qgv-architecture-reconciliation-review-2026-10-05`. Its scoring sources
equal canonical `c109c81a3e417e5f61fd26b67b171fb13628dc21` at adoption intake.
This document freezes the exact values already present at that HEAD; it does
not retune them. The final implementation publication identifies its separate
exact HEAD in the Main completion receipt.

## Weights and analysis horizon

Source: `implementation/src/investment_system/qgv/factors.py`.

| Q factor | Exact weight |
| --- | ---: |
| competitive_advantage | 0.20 |
| roic_wacc | 0.20 |
| market_position | 0.15 |
| fcf_quality | 0.15 |
| margin_quality | 0.10 |
| financial_health | 0.10 |
| management_quality | 0.10 |

Q7 is **Management Quality (경영진 품질)**. Capital Allocation is a subordinate
interpretation of Management Quality, not a renamed or additional factor.
The factor ID remains `management_quality`, weight **10%**. This explicit
user decision resolves C-03 from the effective adoption time.

| G factor | Exact weight |
| --- | ---: |
| next_3_5y_growth | 0.25 |
| growth_efficiency | 0.20 |
| revenue_growth | 0.15 |
| eps_fcf_per_share_growth | 0.15 |
| growth_durability | 0.15 |
| excess_growth_vs_industry | 0.10 |

Default G analysis horizon: **3Y**, exactly
`implementation/src/investment_system/qgv/g_horizon.py:DEFAULT_G_HORIZON`.
Other existing explicit horizon requests and quarterly raw monitors remain
unchanged; the 3Y default does not manufacture missing history.

| V factor | Exact Initial Prior weight |
| --- | ---: |
| fundamental_value | 0.25 |
| reverse_dcf | 0.20 |
| peer_relative_value | 0.15 |
| historical_valuation | 0.15 |
| margin_of_safety | 0.10 |
| sector_context | 0.10 |
| theme_premium_discount | 0.05 |

Each production weight set sums to **1.0 (100%)**, and each listed weight is
within **5–30%**, inclusive. The V vector remains **25/20/15/15/10/10/5** in
the above Initial Prior source order. No missing-component renormalization is
introduced. Existing blocked/missing/NOT_APPLICABLE semantics are retained.

## D-10 raw score conversion

Source: `implementation/src/investment_system/qgv/raw_map.py`, exact source HEAD
above. `clip(x) = max(0.0, min(100.0, x))`; the following are the existing
expressions, frozen without any coefficient or branch change.

| Existing mapping | Existing expression or fixed behavior |
| --- | --- |
| YoY growth | `clip(50.0 + yoy / 0.25 * 50.0)` |
| ROIC minus WACC | `clip(50.0 + spread / 0.10 * 50.0)` |
| Central value, DCF branch | `clip(50.0 + (dcf_value / price - 1.0) / 0.4 * 50.0)` |
| Central value, existing positive-EPS fallback | `clip(50.0 + (20.0 - price / eps) / 20.0 * 50.0)` |
| Margin of safety, DCF branch | conservative value `0.75 * dcf_value`; `clip(50.0 + (conservative / price - 1.0) / 0.3 * 50.0)` |
| Margin of safety, existing positive-EPS fallback | conservative value `12.0 * eps`; same `/ 0.3 * 50.0` expression |
| Reverse DCF | `clip(50.0 + (realized_yoy - implied_growth) / 0.15 * 50.0)` |
| Existing implied-growth fallback | `max(-0.2, min(0.4, (price / eps - 15.0) / 100.0))` |
| Net-cash financial health | `clip(50.0 + (net_cash / revenue) / 0.4 * 50.0)` |
| Existing financial CET1 branch | `clip(50.0 + (cet1 - 0.12) / 0.04 * 50.0)` |
| FCF quality | `clip(50.0 + fcf_margin / 0.15 * 50.0)` |
| Margin quality | `clip(50.0 + ebit_margin / 0.25 * 50.0)` |
| Existing financial NIM branch | `clip(50.0 + (nim - 0.025) / 0.015 * 50.0)` |
| Market position vs peer | `clip(50.0 + (market_share - peer_median_market_share) / 0.10 * 50.0)` |
| Existing no-peer market-share branch | `clip(market_share * 400.0)` |
| Growth efficiency | `clip(50.0 + revenue_yoy / max(invested_capital / revenue, 0.05) * 20.0)` |
| Excess growth vs industry | `clip(50.0 + (revenue_yoy - industry_revenue_growth) / 0.15 * 50.0)` |
| Peer-relative value | `clip(50.0 + ((peer_median_multiple - own_multiple) / peer_median_multiple) / 0.3 * 50.0)` |
| Rubric/history/context inputs | Existing direct rubric/percentile/context values and existing missing-data guards remain unchanged. |

The existing EPS/FCF proxy branches, zero-denominator checks, raw quality flags
and financial-profile input applicability are retained exactly. Freezing them
does not imply calibration or add a new investment calculation.

## Operational output and research separation

Sources: `implementation/src/investment_system/qgv/scoring.py`,
`implementation/src/investment_system/qgv/analysis.py`,
`implementation/src/investment_system/contracts/models.py`, and
`implementation/src/investment_system/contracts/enums.py`.

The intake code already emits numeric Initial Prior V when computable, with
`PROVISIONAL_INITIAL_PRIOR` status. This adoption preserves that numeric output
and marks it operational **STANDARD v1 · UNCALIBRATED**. Every newly computed
operational QGV result carries explicit fields:

```json
{
  "standard": "v1",
  "calibration": "UNCALIBRATED",
  "standard_status": "STANDARD v1 · UNCALIBRATED",
  "standard_effective_at": "2026-10-08T11:50:25Z",
  "V_policy_status": "STANDARD v1 · UNCALIBRATED"
}
```

The Initial Prior V result also carries `standard=v1` and
`calibration=UNCALIBRATED` in the candidate output. `equal_research` and
`mos_tilt_research` remain **RESEARCH**, and neither may replace operational V.
Missing/blocked V keeps the same prior score or null and coverage as before;
standard adoption does not fabricate missing factors.

Existing downstream copies retain these source metadata fields:
`implementation/src/investment_system/qgv/leaderboard.py`,
`implementation/src/investment_system/qgv/us_live.py`, and
`implementation/src/investment_system/validation/historical.py`. Leaderboard
rows copy the original snapshot fields, leaving historical unset fields unset.
US session rows and new fixture/historical predictions carry the same labels.
`implementation/src/investment_system/qgv/html_sample.py` displays the existing
V value and source standard/calibration labels instead of its stale hardcoded
null. These are payload/display changes, not scoring or ranking changes.

The existing product App Shell's Home/QGV descriptions in
`implementation/src/investment_system/product/render_app.py` display the same
adopted status instead of stale "V production null" text.

The combined `total_score` retains the existing Q/G-only mean. V is not added
to that total by this decision. Company-type score adjustment is **identity**:
`type_adjusted_score_100 == total_score`; no calibrated type matrices are
applied. The separate `attractiveness_10` heuristic remains PROVISIONAL.

The legacy frozen schema fields retain `qgv_standard_version=v1.5-balanced`
and `qgv_analysis_contract=v1.7.6`; the new scoring standard metadata is
additive. Historical enum values remain parseable. New metadata defaults to
unset on legacy records and is explicitly assigned only to newly computed
results. A new computation may use historical `as_of` inputs, but its adoption
time remains 2026-10-08; neither old stored results nor earlier standard
authority is rewritten. Existing `analyzed_at/as_of` behavior is unchanged.

## Verification and separate v2 conditions

`implementation/tests/test_qgv_scoring_standard_v1.py` fixes literal weight
maps, sums, inclusive 5–30% bounds, 3Y, raw-map expression/literal pins and
linear-clip anchors. It verifies metadata, research isolation, unchanged
complete/partial/blocked score behavior, identity adjustment, legacy enum
parsing and forward-only adoption. Existing numeric test expectations remain
unchanged; only the explicitly adopted lifecycle/status assertions change.

The historical common-contract `golden_cases.json` remains byte-for-byte
unchanged. `implementation/tools/qgv_contract_audit.py` deep-copies its expected
payload and applies only 13 explicit user-adopted status/metadata fields, with
hard literals and strict original lifecycle/schema guards. The existing golden
tests and audit CLI compare every remaining field exactly, including all scores
and `score_hex`. Unknown or numeric differences are never dropped or accepted.
This comparison is reported as legacy-score/full-field equivalence with the
explicit v1 metadata delta, not unchanged historical lifecycle authority.

Before any v2 real-data calibration, **Holdout protection status must first be
explicitly confirmed**. PIT, OOS and Calibration evidence then supports a
separate user decision for v2. This is a recorded prerequisite only: no
Holdout period is selected or consumed, no calibration/refit is run, and no
calibrated status is claimed here. v2 must be preserved separately; this v1
definition and its adoption evidence must not be overwritten.
