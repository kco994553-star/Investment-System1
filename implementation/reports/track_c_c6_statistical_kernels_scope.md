# C6 approved statistical kernels — implementation scope

Recorded: 2026-09-30 21:03:55 KST (actual clock; before CI).
Source baseline: 8ab49b0e1b937d92ed194c2ace82f5d721f6dd05.
Authority: TC-D3P-004 A items 1–8, approval record
`track_c_c6_statistics_policy_approved.md`.
Status: IMPLEMENTING / NOT FROZEN; CI pending at this commit.

## Implemented independent scope

New `evl/statistical_kernels.py` computes complete-family numerical outputs:
C2/C3-qualified net pre-tax arithmetic risk-free excess series, sample-SD
period Sharpe, published PSR moment correction, both approved DSR count views
with separate supplied provenance, complete all-combination CSCV/PBO including
tied maxima and median equality, joint circular-block bootstrap and centered
full-family White Reality Check. No selected subset, interpolated alignment,
C8 threshold, fitted predictor, promotion or Holdout path is added.

PSR central moments use population central m2/m3/m4 with non-excess kurtosis,
and C3 sample-SD Sharpe. References remain in unannualized period units.
DSR uses registered cross-candidate sample Sharpe variance and the published
zero-null Gaussian expected-maximum approximation; neither count is claimed
to estimate effective independence. CSCV relative rank is average ascending
rank/(N+1), with equal partition/tied-winner mass. Bootstrap inverse-CDF
quantiles are explicitly supplied, never defaulted: empirical order statistics,
no interpolation. Reality Check reports the original Monte Carlo tail fraction
count(T_boot >= T_observed)/B, with no significance decision.

These are low-level kernels, not a registered C6 diagnostic runner.
Caller-supplied roster/count references alone are not a ledger audit.
The remaining runner must verify those references, all complete C1/C5 attempts,
C4/C6 evidence resolution/invalidation, immutable pre-result method registration,
every required benchmark/control path, budget charges and terminal report hashes.
Bare kernel output cannot support diagnostic PASS or C6 acceptance.

## Approval-record conflict — TC-C6-APPROVAL-RECORD-001

The latest task describes TC-D3P-005 S as approved but explicitly says to use it
only if repository approval evidence matches, and to prefer repository evidence
on conflict. At the source baseline, `track_c_c6_freeze_policy_proposal.md`
still says PROPOSED / NOT APPROVED / NOT ACTIVE; the recursive tree contains
no TC-D3P-005 approval record. This conflict is recorded without inventing an
approval time, silently activating S or editing the preserved proposal.

The latest instruction requests every enumerated C6 diagnostic MANDATORY and
explicit PASS/FAIL/NOT_RUN. No missing diagnostic is labeled PASS here.
Freeze-role/status/scope activation remains blocked by the exact repository
consistency condition. Independent approved mathematical implementation proceeds.
C6 software acceptance family and real PIT research validation remain unexecuted;
C7–C10 remain dependency-blocked. Holdout remains UNCONSUMED.
