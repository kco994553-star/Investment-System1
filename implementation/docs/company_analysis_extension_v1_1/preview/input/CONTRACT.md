# Company Analysis UI/UX v1.1 + Historical Price Context v1.0 — Phase A

Status: INACTIVE_SPEC_ONLY / USER_PRODUCT_DESIGN_INPUT_RECORDED. D1 contract preparation. No runtime attachment, new source admission, scoring method, economic threshold, Product grant or production gate closure. This additive contract does not replace existing Chart/QGV/Platform/News contracts.

## Classification
Investment Type, GICS and Strategy Theme are independent top-level axes. Hierarchy exists only within each taxonomy. Investment Type carries primary_type and secondary_characteristics with source/taxonomy version. GICS preserves Sector→Industry Group→Industry→Sub-Industry. Strategy Theme carries a separate multi-theme source/catalog/assignment version. Overlap is separate. Missing assignments stay unavailable.
Investment Type may reference ONLY an existing approved weighting/profile and type-relative comparison contract with method/version/provenance; no new Q/G/V numbers. CALIBRATION_PENDING/type_adjusted=total is not active type weighting. GICS peer universe, Type peer comparison and Theme exposure/premium-discount have separate roles; no duplicate economic credit.

## Historical price summary
Fields: current_price, historical_ath, percent_from_ath, high_52w, percent_from_high_52w. Prices must share security/currency/series identity and a single declared raw/split-adjusted/total-return basis with corporate-action consistency evidence. Missing/ambiguous coverage, window, quote or adjustment authority means NOT_AVAILABLE. Document/Git/extraction time cannot replace available_at/effective time. Do not pick 252 sessions or a calendar-week window without an existing authoritative window contract. Lifetime ATH needs lifetime coverage evidence; partial observed history is not relabeled historical ATH.
When admitted same-basis operands exist, position is (current_price / reference_high − 1) × 100; a zero/nonpositive reference cannot be admitted. A split-adjusted high and raw current quote cannot be combined. These displays do not enter QGV raw score.

## Return periods and denominator
Quarterly/annual 0% baseline bars carry calendar/period/window and same-basis source refs. Return>0 is Positive; Return<0 Negative; Return=0 Flat. A complete full period contributes to denominator; only Positive contributes to numerator. QTD/YTD and partial IPO quarter/year are explicitly labeled and excluded. No arbitrary inclusion threshold is added. Missing/unknown completed-period returns invalidate the summary instead of silently shrinking denominator. An empty denominator yields NOT_AVAILABLE, not 0%. Overview shows positive count / completed full-period count (positive rate); it does not show a separate negative count/rate. Period detail may expose start/end prices, return, high/low, max drawdown and existing events only where separately admitted.

## Drawdown context
Keep General Reference / Company History / Investment Type Peer / GICS Peer / Current VMR separate. The user's six reference-band numbers are preserved ONLY as DISPLAY_REFERENCE_CANDIDATE_NOT_ACTIVE in USER_DESIGN_INPUT.json. Endpoint inclusion/overlap and existing-policy conflict are unresolved; no threshold is activated. Company median/percentiles/MDD/duration/recovery and peer/episode calibration are deferred B/C. Never create an episode-start cutoff. A drawdown may link Q→G→V→News/Event→VMR thesis recheck; it is not automatic buy/sell or score credit.

## Overview and navigation
Order: Company/Data Stamp; Business; Market Position/Competition; Classification; News & Consensus; Price Position/Drawdown; Quarterly; Annual; QGV Core/VMR/Scenario; Conclusion. Overview→Detail→Evidence/Full Technical Chart. Reuse existing Web cards/navigation, Chart bars/full view and data-stamp/version refs. This draft adds no production routes. News shows existing 3–5 records with source/time/new-duplicate/sentiment/structural-temporary/horizon/QGV-impact/confidence only when present; no new classifier/provider. Consensus is separate, and absent revision evidence cannot imply a change.

## Ownership and next implementation
Main owns this docs-only delta on Global under Single-Control. Current old owner paths remain read-only. Next free candidate: main/company-analysis-phase-a-v1, new docs/sidecar paths only; UI/runtime attachment and cross-Work APIs need exact accepted write-set and D3-A evidence where §26A triggers. Existing QGV Missing-Data lease, Chart six gates, Platform nine blockers and FPIA trust gates remain. B/C are not critical-path prerequisites.
