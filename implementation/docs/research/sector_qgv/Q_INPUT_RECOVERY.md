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

## Retained-source execution (2026-11-13)

Actual transformation and six existing dual CLI runs:
`93a699ede9480ca0d173cd7efd4c5109e4d590f4`.
Baseline EPS results: `8e9e5baf95873fc129888b10c2428ce67110423a`.
Evaluation2026-11-04 remains fixed; original financial cutoff
2026-11-04T02:29:35.166580Z is retained in review_context. New review/input cutoff
is2026-11-13T11:57:04.159366+00:00. All source publication dates and acquisition
clocks are unchanged. This demonstrates review of already-held inputs, not new
late-acquisition or historical PIT verification. The existing availability gate
was not relaxed to accept future facts. Calculation execution is pinned separately.

| Unique-issuer stage | operating501 (504code rows) | held1057 |
|---|---:|---:|
| Newly connected explicit debt / raw debt-assets |3 /3|10 /10|
| Unified debt element scores |333→336 (+3)|612→618 (+6)|
| Unified Q (U1 and U2 separately) |303→305 (+2)|569→574 (+5)|
| S1 debt element scores |312→314 (+2)|591→596 (+5)|
| S1 Q |242→244 (+2)|494→498 (+4)|
| New EPS adopted / G / V / joint / total |0 /0 /0 /0 /0|0 /0 /0 /0 /0|
| Lost axis / joint / total outputs |0|0|

Operating3 issuers are included in held10; the scopes/candidates are not summed.
One operating recovered debt issuer remains unified-accounting-incompatible.
Four held new raw ratios are still mapping-unresolved. The sixth newly scored
debt issuer is the same accounting-incompatible REIT; its other unified Q
factors remain NOT_APPLICABLE. No accounting restriction was removed.
ROA/accrual raw recoveries0. No explicit zero was used by these10 real recoveries.

Debt's valid unified reference pool grew358→361 and615→621. This changed existing
Q scores for300 operating and567 held issuers in EACH unified candidate. S1
changed55/285 existing Q scores within affected sector/accounting pools. These
are relative-score effects, not financial improvement. Other factor outputs,
G/V axes and gate decisions were compared unchanged. Existing old outputs/settings
remain pinned; a complete new bundle must be selected to display the new scores.

After repair, mutually exclusive primary Q statuses:
- operating:available305, accounting-incompatible67, classification/accounting
  unknown79, missing exact eligible component46, period mismatch4 (=501).
- held:available574, accounting-incompatible132, classification/accounting
  unknown213, missing exact eligible component134, period mismatch4 (=1057).
Overlaps and per-issuer field/period/source requirements are private. Raw
validation is fail-fast: zero observed unit/currency/peer failures is not proof
that unresolved earlier inputs satisfy later checks. Missing eligible components
are not described as absence from every filing. Latest conflict/attribution
questions not established from the retained review remain unconfirmed.

### Official gate, independent of the Q recovery

No official gate input/decision was recovered. Operating known409, unknown92:
74 have a linked official percentile but unresolved recipe;15 have official Q
AXIS_COVERAGE_BELOW_50;3 have unavailable official source rows. Held known406,
unknown651:72 linked percentiles with unresolved recipe;563 outside the frozen
operating official reference population;15 official Q coverage failures;1
unavailable official source row. No available matching official result was found
missing from the link. Percentile inputs linked483/501 and478/1057 are not gate
PASS counts. No new research Q substitutes for these official inputs.

### Shared evidence and remaining primary work

Three operating source cases retain a claim-specific debt citation, publication
DATE, acquisition, period and review. EPS common-class/split history and valuation
security remain UNCONFIRMED; common equity/dividend and ownership claims are not
promoted by the debt review. Separate claim status is preserved in private
shared-evidence-claims.json. Company values are not public fixtures.

No new annual body, WRB receipt, price or security/action bridge arrived. The
already-specified ADM annual bodies (accessions0000007084-26-000011 and
0000007084-25-000011) remain the minimum proposed history-proof review; they were
not re-requested or collected. WRB's approved execution/delivery is Main-owned.
The first adopted historical EPS proof and first V ratio therefore remain0;
resume locations are retained, and this independent Q repair did not wait for them.

The95% target remains simultaneous Q/G/V and final total476/501,1005/1057.
Neither target is attained. Whole-market denominator/coverage remains null.
No new acquisition, official-model change, merge, deployment or performance test.
