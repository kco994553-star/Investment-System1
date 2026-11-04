# Financial V input recovery and candidate pre-specification

Recorded 2026-11-04 UTC before candidate calculation; researcher proposal, not book-derived or owner-adopted. Version `financial-v-research/1`. Official `qgv2-calc/2026-10-23.1`, publication, gates, weights and Universe504 stay unchanged.

## Recovery boundary

Use the existing 43 input-missing and 4 connection-unconfirmed rows, not a new cause classification. Read hash-linked archived companyfacts, submissions and XBRL instances. Only undimensioned facts in the official standard-concept allowlist, matching CIK, accession, filing date, period and unit may supplement missing companyfacts observations. Conflicting values are evidence, not replacements. No custom-tag mapping, scale correction, class aggregation, predecessor merge, zero debt or partial capex inference. Re-run the unchanged official normalizer on supplemented facts. Official price-dependent rescoring requires the original date's quotes and complete cross-section; missing quotes leave the rescore null. A normalization change alone is not improved V coverage.

## Candidate selection criteria (fixed before results or performance)

Select by economic denominator and business model, attribution to common shareholders, explicit share basis, period/currency match and reproducibility. Coverage and returns do not select the formula. No returns are calculated. SIC routing is a provisional business-model screen, not filing-level verification of a diversified company's operations.

| SIC screen | Group | Primary candidate | Secondary diagnostic |
|---|---|---|---|
| 6021, 6022 | Depository banks | tangible common book / price | common book / price; diluted EPS / price |
| 6311 | Life insurance | common book / price | diluted EPS / price |
| 6331, 6399 | Property/casualty or other insurance | common book / price | diluted EPS / price |
| 6321, 6324 | Health/accident insurance | diluted EPS / price | common book / price |
| 6211 | Securities brokers/dealers | common book / price | diluted EPS / price |
| 6282 | Asset managers | diluted EPS / price | common book / price |
| 6411 | Insurance intermediaries | diluted EPS / price | common book / price |
| 6199, 6200; other | Diversified/unresolved financial | null pending business evidence | raw components only |

Debt is part of financial intermediation; EV/EBIT and EV/FCF are not reused. Common book must exclude preferred equity and NCI. The adapter accepts directly reported CommonStockholdersEquity, or parent StockholdersEquity only with same-filing explicit zero PreferredStockSharesOutstanding. PreferredStockValue is par/stated value, not full preferred carrying equity, and is never subtracted; tangible common book additionally excludes goodwill and identifiable intangibles attributable to common. Their absence is not zero. Book per share uses point-in-time common shares, not diluted weighted-average shares, and requires class/economic-rights evidence. EPS is the issuer's diluted EPS, not net income divided by a guessed share count. Positive price and positive numerator are required for the candidate; losses/nonpositive capital remain disclosed as missing reasons. Units: per-share inputs currency/share, price currency/share, ratios x. Annual EPS spans 350–380 days; annual/instant input end must be no later than the valuation date and no more than 550 days old. Sources, filed dates, periods, matching currency and share basis are mandatory. No imputation, reweighting or score/rank calculation.

## Three result scopes

1. Same-date operational comparison: fixed 504 codes, 2026-11-02 price basis and archived input vintage. Show baseline and after-recovery official counts; if official inputs do not change, counts are carried forward explicitly (not a new rescore). If changed but prices absent, after counts are null. Preset feasibility is distinct from actual totals.
2. Same-date financial candidate: raw eligible metrics, primary-metric availability and potential Q/G plus primary-metric availability. A raw metric is not a V axis score; combined scored coverage and preset totals remain null until scoring/adoption exists. No replacement of official V.
3. Optional **ex-post fiscal diagnostic**: exact held fiscal-year-end month prices and financial periods only, reusing calc23.1 split-basis conversion. Filing may follow price date; this mode is explicitly not PIT, not a strategy result, not part of same-date coverage. It reports EPS/price only where the same fiscal year, price symbol mapping and share-basis factor can be traced; incomplete security proof is disclosed separately. No ranking or financial-model adoption follows from it.

The existing book work does not establish the financial subgroup rules, weights, 550-day research freshness bound or candidate adoption. These are research proposals. Book strategy selection rules are not altered or re-audited.

## Output contract

`financial-v-research/1`: code, CIK (issuer only), valuation_date, input_vintage, business_group, classification_basis, primary_metric, metrics {value, unit, reasons, inputs}, primary_available, score=null, rank=null. Distinguish `OPERATIONAL_CANDIDATE_RAW` from `EX_POST_FISCAL_DIAGNOSTIC`. Missing sources/periods/currency/share basis and nonpositive inputs are explicit. Real data/results remain private; synthetic tests are public. Main owns any UI integration.

Independent review fixes: separate issuer-document linkage from class/economic-rights evidence; unconfirmed class ratios remain explicitly arithmetic-only diagnostics. Require the same fiscal-end month in the ex-post evaluator. Tangible book needs complete goodwill/intangibles and explicit zero NCI before using consolidated deductions. These input safeguards do not change the candidate selection criteria.
