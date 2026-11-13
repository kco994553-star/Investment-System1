# Q input recovery and review clocks

The existing held-input-repair CLI accepts projection `UNIFIED_Q_ONLY` with
`transform_only: true`. It changes only ROA, accruals/assets and debt/assets
observations; EPS, G, V, classification, gate inputs and membership are retained.
Adapter version: `held-sec-q-inputs/1`. This is input connection, not a factor,
accounting-applicability, weight, minimum-peer or official-model policy change.

The existing SEC fiscal extractor and balance validator connect reported
`DebtLongtermAndShorttermCombinedAmount` or `DebtAndCapitalLeaseObligations`
only when the existing composite debt is unavailable. These are combined
interest-bearing carrying amounts, not liabilities, debt investments, fair value,
individual instruments or scheduled future repayments. The exact balance date,
currency, instant/unit/form/accession and latest filing must validate. Overlapping
totals are not added. Explicit zero is allowed; missing debt remains null.
An invalid or conflicting newest total cannot reveal an older value.

## Time and claim contract (additive)

`sector-qgv-review-context/1` is an optional repair-plan field `review_context`.
It pins the original snapshot hash and evaluation date, supplies a separate
`input_cutoff` and `reviewed_at`, and preserves source publication (DATE,
TIMESTAMP or UNKNOWN), acquisition and each claim's reviewed time, valid period,
subject, locator and source hash. No time is invented for a date-only filing.
The new snapshot gets a different ID/input version and
`result_kind=RETROSPECTIVE_REVIEW`, `historical_system_pit_complete=false`.
Calculation time belongs to the run manifest/execution receipt, not source facts.

`reviews[]` records each claim separately. Confirming INTEREST_BEARING_DEBT,
COMMON_EQUITY, EPS_HISTORY, VALUATION_SECURITY, DIVIDEND or OWNERSHIP_RELATION
never verifies another claim. Historical EPS's existing optional proof includes
`reviewed_at` for new reviews; the kernel rejects a review after its input cutoff.
A claim review alone does not inject prices, assign security IDs or adopt EPS.
The normal input and raw-result validators still apply.

Synthetic producer-generated examples: `q-input-examples/`. The Feb2 evaluation
and acquisitions stay unchanged; Feb4 review creates a Feb4 knowledge cutoff.
Rows and their original acquisition timestamps are byte-equivalent as JSON values.
Old settings/results stay pinned to the old snapshot; this is not historical PIT.
Main may display input cutoff/review date separately from evaluation and price day.

## Official Q gate separation

Retained official Q percentile/calc23.1/industry-pool evidence remains the sole
gate input. Research Q is not substituted. A linked official percentile can coexist
with result gate UNKNOWN when the recipe/classification is unresolved. Missing
reference results, official-axis coverage failure, unmapped rows, and actual gate
PASS/VALUE_EXCLUDED must be shown separately. VALUE_EXCLUDED is not issuer removal.
No operating module, frontend, guard, workflow, existing public output is changed.

## Reproduction

`PYTHONPATH=implementation/src python implementation/tools/sector_qgv.py --job JOB --output NEW_PRIVATE_DIR`
The held repair job pins original snapshot, plan, source archive/member hashes.
The existing dual-study command consumes the resulting snapshots. Reference and
evaluation cutoffs must match. Only changed inputs/affected relative pools require
new scoring. Actual run and current producer commits are reported independently.
