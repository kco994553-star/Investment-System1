# Factor role audit — inactive Method/Profile Binding Gate

**Status: AUDIT_ONLY / D1 COMPLETED / D2 RECOMMENDATIONS / NO PRODUCTION BINDING.**

This is an additive continuation of approved M1–M5 and the inactive Implementation Contract. It reads the existing 20-factor map and current production sources. It does not rerun the broad audit, revise weights, recalculate stored scores, classify a production factor as REQUIRED/OPTIONAL/CONDITIONAL, or promote research V. Full per-factor evidence is in [factor_roles.json](factor_roles.json).

## Evidence classes and authority

`SUPPORTED` means enough current documentation and nonconflicting source characterization support the narrow intended semantic purpose shown below. It does **not** mean the method is domain-calibrated or the factor is required. `PROPOSED` means a plausible role remains dependent on proxy/input/rubric authority. `UNRESOLVED` means a live semantic conflict or method/name mismatch prevents a fixed role. All observed calculations are source-supported facts; none supplies requiredness by mere code usage.

Classification: **SUPPORTED 3; PROPOSED 10; UNRESOLVED 7**. Production requiredness roles assigned: **0/20**. The SUPPORTED three are narrow concept/identity preservation only; production roles for all20 still require separate authority.

Frozen Q/G weights are preserved observations (`qgv/factors.py:13–30`). C-30 keeps Official Weight Dataset/maturity open (`Investment-System1 · Contract Conflict Register 2026-09-23.md:363–369`), so even these weights cannot make a registry node PRODUCTION. V prior is PROVISIONAL_INITIAL_PRIOR and V candidates are RESEARCH (`qgv/factors.py:65–100`, `qgv/scoring.py:126–128`). The older C-30 text saying V null is historical and superseded for runtime behavior by the explicit initial-prior implementation; the authority/maturity question remains open.

## Twenty factors

| Axis / factor | Local weight | Role evidence | Actual method and input | Bounded recommendation |
|---|---:|---|---|---|
| Q · `competitive_advantage` | 20% | SUPPORTED | rubric direct score; actual rubric taxonomy and observer authority are not complete here; fields: competitive_advantage_rubric | Bind the preserved rubric method and its source/version first; requiredness stays unassigned. |
| Q · `roic_wacc` | 20% | PROPOSED | net_income/invested_capital minus supplied WACC; a proxy, with financial exclusion; fields: net_income, invested_capital, wacc | Keep legacy spread literal; require separate proxy/input-unit and financial applicability authority before roles. |
| Q · `market_position` | 15% | PROPOSED | share-versus-peer linear clip; share-only *400 fallback; fields: market_share, peer_median_market_share | Record relative-share and share-only as separate method branches; do not infer roles from positive weight. |
| Q · `fcf_quality` | 15% | PROPOSED | FCF/revenue margin linear clip; FCF itself may be CFO-abs(capex); fields: fcf, revenue | Bind numerator production and period/unit lineage; FCF margin is not proof of complete cash-flow quality rubric. |
| Q · `margin_quality` | 10% | PROPOSED | EBIT/revenue linear clip; FINANCIAL with NIM overrides using separate mapping; fields: ebit, revenue, nim | Resolve one shared issuer context and distinguish EBIT-margin versus NIM methods before role binding. |
| Q · `financial_health` | 10% | PROPOSED | net cash/revenue clip; FINANCIAL CET1 overrides when supplied; fields: cash, total_debt, revenue, cet1 | Record net-cash and CET1 alternatives with predicate evidence; no completeness authority from their availability. |
| Q · `management_quality` | 10% | UNRESOLVED | direct management_quality_rubric, not a capital-allocation method; fields: management_quality_rubric | Preserve management_quality legacy identity. Defer fixed requiredness until C-03 semantic choice. |
| G · `next_3_5y_growth` | 25% | UNRESOLVED | same revenue/revenue_prev-1 mapping as revenue_growth, no forecast/CAGR; fields: revenue, revenue_prev | Preserve legacy proxy; defer horizon/method semantics and requiredness. Horizon metadata cannot promote a forecast. |
| G · `growth_efficiency` | 20% | PROPOSED | 50 + revenue YoY/max(invested_capital/revenue,.05)*20, clipped; fields: revenue, revenue_prev, invested_capital | Pin the existing heuristic and its units/horizon; do not adopt .05 as a new policy default. |
| G · `revenue_growth` | 15% | SUPPORTED | revenue/revenue_prev-1 through provisional linear clipping; fields: revenue, revenue_prev | Preserve the YoY semantic label and distinguish method/input-period version. REQUIRED/OPTIONAL still unresolved. |
| G · `eps_fcf_per_share_growth` | 15% | UNRESOLVED | EPS/eps_prev-1 else FCF/revenue_prev-1; no FCF prior or shares in fallback; fields: eps, eps_prev, fcf, revenue_prev | Bind the actual EPS branch and incompatible fallback separately. Defer semantic replacement and fixed roles. |
| G · `growth_durability` | 15% | SUPPORTED | direct growth_durability_rubric score; rubric authority not completed here; fields: growth_durability_rubric | Bind rubric provenance/version; factor identity is supported, no production requiredness inferred. |
| G · `excess_growth_vs_industry` | 10% | PROPOSED | revenue YoY minus supplied industry_revenue_growth, linear clip; fields: revenue, revenue_prev, industry_revenue_growth | Bind company and industry period/units/reference universe before any requiredness/completeness claim. |
| V · `fundamental_value` | 25% | UNRESOLVED | supplied DCF/price scaling else price/EPS versus fixed PE20; no solver; fields: dcf_value, price, eps | Separate supplied-DCF and PE-proxy methods; no intrinsic-value maturity or role promotion. |
| V · `reverse_dcf` | 20% | UNRESOLVED | supplied implied growth else clipped (PE-15)/100 compared with revenue YoY; fields: reverse_dcf_implied_growth, price, eps, revenue, revenue_prev | Bind actual proxy branches/input horizon; do not call proxy evidence a reverse-DCF solver. |
| V · `peer_relative_value` | 15% | PROPOSED | relative own/peer supplied multiples; historical provider median of current raw cohort; fields: peer_median_multiple, own_multiple | Require comparable multiple, peer membership and PIT cohort evidence; no sector-peer authority inferred. |
| V · `historical_valuation` | 15% | UNRESOLVED | direct hist_valuation_percentile field; historical provider uses two-point PE change score; fields: hist_valuation_percentile | Separate true-percentile input from two-point PE-change method; defer historical method and requiredness. |
| V · `margin_of_safety` | 10% | UNRESOLVED | 75% of supplied DCF else 12*EPS, then price scaling; not adopted vNext rules; fields: dcf_value, price, eps | Pin observed heuristics and defer conservative-value/normalization authority. |
| V · `sector_context` | 10% | PROPOSED | direct sector_context_score; no current historical source producer; fields: sector_context_score | Require sector methodology/input authority. Absence is missing, not economic N/A. |
| V · `theme_premium_discount` | 5% | PROPOSED | direct theme_premium_score; no current historical source producer; fields: theme_premium_score | Require theme rubric/source authority. Absence is missing, not economic N/A. |

## Requiredness binding evidence

Current `FactorObservation` has factor ID, score, QualityState, stamp ID and notes only (`contracts/models.py:74–81`). `RawFundamentals` marks raw values Optional (`contracts/raw.py:16–51`); this describes absent input representation, not economic optionality. `_weighted` skips ordinary missing while keeping denominator (`qgv/scoring.py:24–57`). V candidate complete-vector behavior (`:87–104`) is an algorithm precondition and cannot be promoted to a REQUIRED declaration. No authoritative factor role/default registry was found in these structures.

The minimal proposal is a **versioned method-to-factor role reference** attached to the inactive binding sidecar, reusing stable IDs and existing Personal/version references. It must cite actual authority, predicate and dependent input roles. A binding may be unresolved; the new consumer may receive labeled legacy/diagnostic evidence but must not claim new admitted completeness through guessing. Do not assign fixed requiredness to Q7, G 3–5Y, EPS→FCF or the four unresolved V methods until their method semantics are decided. This affects only the proposed vNext path: existing legacy scores stay literal.

Confidence in exact current source arithmetic is high. Confidence in adopting a complete semantic role is represented separately by factor row MEDIUM/LOW and is **not** a new numeric confidence score. Any actual requiredness adoption is D3; D1 source audit and D2 recommendation are complete.

## Applicability, missing and PIT/provenance

`factor_applicable` excludes only financial ROIC/WACC (`qgv/factors.py:42,103–106`); all other bool True results indicate current code branch behavior, not proof of applicable truth. Financial NIM and CET1 alter methods rather than remove factors (`qgv/raw_map.py:104–115`). Direct raw-profile and scoring-profile contexts can disagree (`qgv/pipeline.py:21–33`); [APPLICABILITY_AUDIT.md](APPLICABILITY_AUDIT.md) gives the bounded actual synthetic counterexample and 56→70 decomposition.

All factor observations share raw `stamp_id` (`qgv/raw_map.py:87–90,159–169`), but that field does not carry per-input/peer/rubric/predicate/branch provenance or method version. DataStamp already supports source/provider and both time guards (`contracts/models.py:34–50`, `pit/resolver.py:21–38`). Memory provider uses both, while direct analyze_raw maps without require_available (`providers/memory.py:20–28`; `qgv/pipeline.py:21–43`). This does not establish that all historical Official evidence leaked; it identifies exact entry preconditions needing B2/B3/B4 binding.

Ordinary missing keeps registered denominator1; NOT_APPLICABLE observation states and PIT_UNAVAILABLE currently follow generic missing in prior reducers (`qgv/factors.py:109–117`; `qgv/scoring.py:24–57`). Numeric VERSION_MISMATCH/IDENTIFIER_AMBIGUOUS/CALCULATION_ERROR may reach prior/candidate reducers. Existing source behavior remains preserved; the approved M2 principle motivates independent preweight vNext admission.

## Consumer and historical maturity

Q/G factors enter `(Q+G)/2` when both axis numbers exist, including partial contributions (`qgv/analysis.py:42–61`); V prior/candidates are output separately (`:36–40,100–118`) and V is excluded from total. Leaderboard sorts numbers and emits rank for every supplied snapshot (`qgv/leaderboard.py:30–54`), so availability is not a new completeness/ranking gate. Portfolio attaches snapshot ID without changing holdings from its score (`qgv/portfolio.py:46–64`). Historical Track Record stores predictions and snapshot references (`validation/historical.py:195–214`). Consumers do not independently establish factor requiredness.

Legacy tables/snapshots keep their original factor ID, observed calculation, weights, values, quality, dates and versions. Preserve archived missing/partial behavior and V lifecycle literally. Future parallel vNext method/role/applicability binding and consumer promotion need a separate D3 approval; no historical rewrite or automatic migration is recommended.

## Exact per-factor source references

- `competitive_advantage`: implementation/src/investment_system/qgv/raw_map.py:132.
- `roic_wacc`: implementation/src/investment_system/qgv/raw_map.py:96-97,133,163-165.
- `market_position`: implementation/src/investment_system/qgv/raw_map.py:117-121,134.
- `fcf_quality`: implementation/src/investment_system/qgv/raw_map.py:95,108-110,135; implementation/src/investment_system/providers/sec_companyfacts.py:218-238.
- `margin_quality`: implementation/src/investment_system/qgv/raw_map.py:94,111-115,136.
- `financial_health`: implementation/src/investment_system/qgv/raw_map.py:98-106,137.
- `management_quality`: implementation/src/investment_system/qgv/raw_map.py:138; Investment-System1 · Contract Conflict Register 2026-09-23.md:23-27.
- `next_3_5y_growth`: implementation/src/investment_system/qgv/raw_map.py:92,139; implementation/src/investment_system/qgv/pipeline.py:27,36-42.
- `growth_efficiency`: implementation/src/investment_system/qgv/raw_map.py:123-125,140.
- `revenue_growth`: implementation/src/investment_system/qgv/raw_map.py:37-47,92,141.
- `eps_fcf_per_share_growth`: implementation/src/investment_system/qgv/raw_map.py:93,142; implementation/src/investment_system/contracts/raw.py:20,26-28.
- `growth_durability`: implementation/src/investment_system/qgv/raw_map.py:143.
- `excess_growth_vs_industry`: implementation/src/investment_system/qgv/raw_map.py:127-129,144.
- `fundamental_value`: implementation/src/investment_system/qgv/raw_map.py:57-63,145.
- `reverse_dcf`: implementation/src/investment_system/qgv/raw_map.py:76-84,155.
- `peer_relative_value`: implementation/src/investment_system/qgv/raw_map.py:146-151; implementation/src/investment_system/validation/historical.py:177-189.
- `historical_valuation`: implementation/src/investment_system/qgv/raw_map.py:152; implementation/src/investment_system/validation/historical.py:179-184.
- `margin_of_safety`: implementation/src/investment_system/qgv/raw_map.py:66-73,156.
- `sector_context`: implementation/src/investment_system/qgv/raw_map.py:153; implementation/tests/test_hist_peer_ablation_pit.py:48-51.
- `theme_premium_discount`: implementation/src/investment_system/qgv/raw_map.py:154; implementation/tests/test_hist_peer_ablation_pit.py:48-51.

Common reducers, provenance, consumers, authority and input-contract references are retained in each JSON record and in its reference catalog. Source inspection and the financial context probe are bounded new evidence. Existing 102×4 comparison and71 golden are prior reusable evidence; they are not newly run production vNext acceptance.
