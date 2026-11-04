# Calculation queue — 2026-11-04

Owner scope: offline calculation, existing data, ordinary development branches and Draft PRs. Main owns screens and operations. No collection, workflow change, merge or deployment.

## Plan and execution ledger

1. **Layer 6 (in progress)** — extend `validation.vertical_slice`'s existing research selection and every store/walk-forward entry point with an optional immutable policy (`all`, `top_n`, `top_percent`). Preserve omitted-option behavior and the existing `equal_weight_input` path. Test 137-to-137 / 137-to-20 through `PortfolioEngine`, zero, missing scores, ties, percentage floor, store entry points. Fixed TARGET and book strategies are outside this policy. Reviewer focus: no hidden truncation, no changed eligibility, no dropped option on wrappers.
2. **Layer 2 (pending)** — locate one dated operational publication and its membership/input evidence; measure factors, axes and presets using authoritative computation evidence. Preserve private inputs and a reproducible coverage artifact. Unknown identity denominators remain null. Fix only demonstrated input joins.
3. **Layer 9.1 (pending)** — inspect the approved stacked research entry points and Lab reader version. Reuse prior same-input/SHA verification. If a real schema/hash mismatch exists, fix only that path and run an eligible private result through the reader contract.
4. **Layer 9.2 (pending)** — distinguish operating ledgers from approved v3 design; implement the first absent offline archive/PIT comparison path keyed by security, date and calculation version. No fabricated PIT reconstruction or performance.

Independent code changes use separate branches/PRs; a blocked analysis alone does not earn a PR. Real company values stay in the approved private handoff. One fresh final review covers changed code and boundaries before Draft delivery.

## Layer 6 contract

The existing general Python path already selects all Q/G-present companies; N10/N15/N20 are explicit official-model sets in Main's `product/web_assets/qgv-scores.js:modelPortfolios`, not a common Python cap. New modes apply only to the provisional general research path. A supplied policy ranks finite eligible Q/G observations by existing Q, G, V ordering, then `company_id` for a deterministic tie (this is an existing company-keyed path, not a claim of historical security identity). An omitted policy retains legacy order. Percentage counts use floor over eligible names, including zero; top N is bounded by available eligible names. Weights remain equal across selected names. No relaxation or filling with ineligible names.

Main can expose the three modes using `selection_policy`, `n_eligible`, `n_selected`, and `weights` from the research result. The official N15 tier settings, book counts, eligibility and official-model limits remain independent.
