# PR31 CDR-012 F1/F3 repair handoff

Current checkpoint for the approved synthetic M-B v2 scope. Earlier CDR-010
handoff, approval, acceptance, numerical receipts and review history remain
historical and unchanged. Fresh Global read-only HEAD is
`1620f7118dbe91283cde1cc1431cdea236ab0829`; GCH-010/CDR-012 records the user's
approval to resolve the two GIE-010 findings. The verbatim decision, exact
source blob and SHA256 are in `evidence/cdr012-repair/CDR012_APPROVAL.json`.

## Approved repair

- F1: both observed and replicate squared residuals use `d*d`. No `** 2`
  or libm `pow` remains in the authoritative v2 module.
- F3: if all B bootstrap replicates have `sqrt(v/n)>0` false, the kernel
  raises missing statistical evidence before creating any p-value. Each
  affected registry cell is NOT_RUN, and the inherited aggregate is NOT_RUN,
  never STAT_PASS. The original source reservation/access remains one-shot.
- CDR-010 math.fsum, direct block sums, block grouping, mean operand order,
  final block exclusion, literal standard-error predicate and inclusive ties
  stay unchanged. Partly degenerate sets retain the original B+1 denominator.
- No epsilon, tolerance, threshold, numeric default, additional method or
  real-access permission is introduced. `[0.05]*12`, whose replicates are
  not all degenerate, retains the literal result described in CDR-012.

The method/version and registration policy identifiers remain v2. The active
arithmetic contract explicitly adds MULTIPLICATION and all-degenerate NOT_RUN.
Authority checks require the original unchanged CDR-010 approval and the new
pinned CDR-012 supplement; a missing/changed supplement fails before access.

## Evidence and verification

An independent formula oracle and CDR-012 fixed hex pins are added in new
files. The original CDR-010 oracle, fingerprint tables and full-trace tables
are unchanged, remain separately executable and are labelled historical.
Active v2 tests compare current output against the new oracle. The F1
near-tie input `[8.7,0,0,0,-2.9,2.9,2.9,8.7,-2.9]`, L2/B19/seed11, is pinned
at p=.15; historical pow-squaring p=.20 is retained as baseline evidence.
F3 `[-0.2,-0.1]*6`, L2/B19, seed7 and seed11, is pinned at all19 degenerate
and NOT_RUN. Underflow, partial degeneracy and registry propagation are
negative regressions, with no numerical acceptance tolerance.

The initial red kernel receipt was captured on exact old31
`e0b6d809058511d4bef7ad1aeccad79c5eae3ff8` before the production repair.
It is not overwritten by the green execution. Targeted/full execution,
independent final review, source hashes and evidence hashes are recorded in
`ACCEPTANCE_MANIFEST_CDR012.json` and `evidence/cdr012-repair/`.

Publication-time exact HEAD and fresh Actions/JUnit/artifact digest receipts
are recorded in the current PR31 description. Committed pre-publish evidence
does not invent an Actions result: until the exact-head runs complete, CI is
PENDING. Once published, PR31's exact-head receipt determines CI_VERIFIED.
PR35 is updated only after PR31 HANDOFF_READY/CI_VERIFIED, by a normal
dependency merge; its own fresh CI receipt determines its state.

## Preservation, routing and boundaries

V1, C0-C7 Frozen source/tests, historical reports/evidence and original
approvals remain byte-preserved. Existing Decision Register and scoped
status/handoff prefixes are retained with additive routing entries. The
source descriptor, consumption journal, response commitments and PIT/no-lookahead
guards remain unchanged. Producer/engine fingerprints are preserved.

PR39 `0d31e06022c3162e83f2ff5a984b07e59e4e216b` is Claude Main's verified
earlier combined trial: 1441 PASS/10 workflows on its original tree. Those
results do not certify a successor with this CDR-012 repair. Claude Main
independently re-verifies F1/F3 and creates/verifies PR39's fresh successor.
No PR37/38/39, Global Handoff, or integration owner branch is modified here.

BRANCH_STATE: approved CDR-012 synthetic repair; acceptance and the PR31
exact-head CI receipt determine HANDOFF_READY/CI_VERIFIED.
INTEGRATION_STATE: stacked draft proposal, NOT_MERGED; Claude Main independent
re-verification and the successor combined trial remain owner dependencies.
CANONICAL_STATE: `b8e39a2196a6d7794a04a0cd5393c68329e126ca`, NOT_MERGED.

C0-C7 SOFTWARE_FROZEN; C8 SYNTHETIC_VERIFIED/NOT_FROZEN; maturity delta0.
Actual numeric configuration0, actual CAL_VERIFY0, Holdout0, C8 Freeze0,
publication/Official/LIVE grants0, canonical merges0, deployments0, paid
resources0. No new result-impacting policy was chosen beyond CDR-012.
The previously recorded residual/real-source identity issues remain outside
this repair, with their original authority boundaries.
