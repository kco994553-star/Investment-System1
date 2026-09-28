# C2 decision request — EVL-SPLIT-01 v1.0

Status: **D3-P PROPOSED — NOT APPROVED / NOT ACTIVE**
Contract: EVL_SPEC_v0.1 §§2–3, 10, 13. No change to those locked rules is proposed.
Scope: Track C chronological dataset boundary selection only.

## Why a decision is needed

The frozen specification fixes Train 5Y / Validation 1Y / OOS 1Y, annual
re-optimization, comparison of rolling and expanding forms, and derivation of
Purge/Embargo from label horizon and rebalance interval. It does not define the
formula, whether nominal windows move or lose boundary samples, or whether
Embargo is a pre-evaluation gap or the post-test exclusion used in nonchronological
cross-validation. C0 stores two nonnegative integer seconds, but does not derive
or enforce either. Selecting these semantics changes the eligible observations
and OOS experiment, so this is proposed as one reusable validation policy rather
than silently selected after observing results.

Existing: ordered, non-overlapping nominal windows; arbitrary nonnegative
`purge_seconds` / `embargo_seconds`; no sample-level exclusion implementation.
Proposed: the deterministic chronological-gap rule below. This is **not** a
claim that all forms of purged cross-validation use the same embargo convention.

## Recommended general rule

1. Keep nominal Train 5Y / Validation 1Y / OOS 1Y calendar windows unchanged.
   Use half-open windows `[start, end)` in the new C2 selector. Preserve the C0
   inclusive endpoint API; the C2 adapter must explicitly translate it, never
   silently reinterpret an existing DatasetSplit instance.
2. Pre-register `H`, the maximum label horizon, and `R`, the rebalance interval,
   from the experiment's actual upstream schedule **before any trial results**.
   For fixed-duration schedules, H and R are positive timedeltas. Calendar or
   trading-session schedules must resolve actual boundary timestamps using the
   registered schedule; a month is not guessed to be 30 days.
3. At each Train→Validation and Validation→OOS boundary `B`, purge any earlier
   sample whose label endpoint is at or after B. Require recorded label intervals
   and label-availability timestamps. A label used to fit/calibrate must be fully
   available before its cutoff; horizon alone is not publication evidence.
4. Add a conservative chronological **pre-evaluation gap** of one R: retain an
   earlier sample only when **label_end < B − R** AND
   **label_available_at < B − R**. Thus for a fixed-horizon label ending at t+H,
   the latest permissible decision timestamp satisfies **t < B − R − H**.
   `purge_seconds=H` and `embargo_seconds=R` are derived metadata, not search knobs.
   This explicitly defines “Embargo” for this strictly chronological engine;
   a future nonchronological CV engine would require its own approved semantics.
5. Apply the same rule to rolling and expanding windows and every annual fold.
   Trim boundary samples; never shift validation/OOS windows to recover results.
   Record retained/excluded IDs, boundary, cutoff, H/R/schedule identity and reason.
6. Unknown horizon, schedule, label availability, provenance or vintage means
   fail-closed. An empty required partition is NOT_RUN_INSUFFICIENT_DATA, not PASS.
   No minimum sample count or significance threshold is invented by this policy.
7. Feature observations still require `available_at <= decision_time`. This
   proposal grants **no exception** for Track A retrospective reconstruction.
   Final Holdout remains inaccessible to research/calibration; its lifecycle and
   one-use runner belong to C9. This policy cannot authorize holdout access.
8. Approve once as D3-P; later instances using these exact semantics are D3-C.
   A shorter gap, recovered excluded rows, changed boundary convention or relaxed
   PIT rule requires a new policy review, never a result-dependent exception.

## Concrete review examples (UTC, fixed-duration demonstration only)

Let B = 2020-02-01 00:00, H = 2 days, R = 1 day. Cutoff = 2020-01-31 00:00.
These values illustrate the formula; they are not Official experiment defaults.

| Decision time | Label end | Label available | Decision |
|---|---|---|---|
| Jan 28 00:00 | Jan 30 00:00 | Jan 30 12:00 | Retain: both label times precede cutoff |
| Jan 29 00:00 | Jan 31 00:00 | Jan 31 00:00 | Exclude: equality with cutoff is blocked |
| Jan 30 00:00 | Feb 1 00:00 | Feb 1 00:00 | Exclude: crosses evaluation boundary |
| Jan 28 00:00 | Jan 30 00:00 | Jan 31 12:00 | Exclude: label publication too late |
| Jan 28 00:00 | Jan 30 00:00 | Unknown | Block: unknown label availability |

## Alternative and tradeoff

An overlap-only purge with no pre-evaluation gap retains more data and treats
post-test embargo as vacuous when all training observations precede evaluation.
It is less conservative about near-boundary dependence. EVL_SPEC_v0.1 does not
select between this interpretation and the proposed H+R chronological gap.
The recommendation is the explicit H+R gap, chosen without inspecting returns.

## Compatibility and validation before C2 freeze

- Existing C0 records/APIs remain readable; new schedule metadata is additive.
- Do not change Track A/B/D/E contracts, snapshots, scores or source data.
- Unit checks: equality, microsecond edges, timezone equivalence, leap/calendar
  boundaries, variable label endpoints, delayed label availability, missing inputs.
- Compare rolling and expanding partitions; verify annual folds and 5/1/1 nominal
  windows. Assert zero interval leakage and deterministic exclusion reasons.
- PIT checks: unknown/future features rejected; Track A retrospective availability
  cannot be relabelled. Isolation checks must prevent holdout in fit/calibration.
- Run targeted, full and normal-merge integration regressions before FROZEN.
- Unit/software PASS does not establish statistical skill, real-data coverage,
  profile distinctness, Holdout PASS or Official promotion.

Implementation: **not started pending this D3-P**. No C2 runtime, threshold,
experiment output or Official artifact is introduced by this proposal.


Superseded 2026-09-28T21:03:11+09:00: user approved revised EVL-SPLIT-01 v1.1, recorded in
track_c_c2_split_policy_approved.md. The mandatory-extra-gap v1.0 above was NOT approved.
