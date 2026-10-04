# PR31 CDR-010 authoritative M-B v2 handoff

This supersedes the **arithmetic-pending** status of the earlier handoff within
the approved synthetic software scope. The earlier records remain historical.
CDR-010/011 were discovered by fresh fetch on Global read-only commit
`e30241f49e31f4ac5ab0d4f322ecddc78a044d75`; the exact quoted decision and source
blob are retained in `evidence/authoritative-v2/CDR010_APPROVAL.json`.

## Implemented contract

`evl/superiority_v2.py` implements separate `C8_GSUP_STUDENTIZED_CBB_v2`:
math.fsum, direct block sums, block grouping, replicate mean
`(math.fsum(full_block_sums) + partial_sum) / n`, variance over
`ceil(n/L)-1` blocks, and degeneracy when `sqrt(v/n)>0` is false.
The final block remains outside replicate variance even when its length is L.
Degenerates do not exceed; ties use `>=`; the denominator remains B+1.
There is no tolerance, rounding, fallback or numerical default.

The v2 registry uses the existing trusted source descriptor, claim journal,
development-content/lineage gate, pre-provider synthetic gate and one-shot
access protocol. Changing v1/v2, labels, campaign or attempt root cannot reset
the same source consumption. No legacy kernel globals are replaced. V1's
identity wrapper and its result schema remain unchanged.

## Validation and evidence

- Local native full collection at execution start: **1296 PASS**, 0 failures,
  errors or skips (1277 existing + 19 v2 registry cases).
- Independently authored arithmetic tests: **86 PASS**, 0 skips; 171 complete
  hex traces pinned, including CE4 .10/v1 .15, FLIP .10, LEFT_SUM .35,
  TIE .45 and seed275 .55. Positive-variance SE-underflow is tested.
- Two subsequently added approval-authority negatives: **2 PASS**.
- Final targeted v2 source after independent-review repairs: **118 PASS**
  (86 arithmetic +21 registry +11 repair negatives). Current collection:
  **1395** unique tests. The prior full1296 and final targeted118 share19 cases;
  the testcase union is1395. Existing1277 source/test cases are unchanged;
  the full1296 source snapshot precedes the overflow/verifier repairs. A single
  final-source local full1395-case rerun is NOT_RUN. The native Actions workflow runs that whole
  current collection and the standalone production/oracle replay.
- Four fresh standalone replay processes: CPython3.11.16 and3.12.14, two each.
  Each runtime pair is byte-identical and all numerical output hashes equal
  `d4642fa50523c75f4278afc5463c9751d582c427077916788e8fd39f1f99cfd5`.
  The two committed replay receipts retain exact decimal/hex values and trace
  commitments. This does not certify the unrecorded historical NumPy runtime.
- Every pre-existing215 source file,122 test file and199 report JSON is
  unchanged from exact29c. Existing14 workflows remain; four have bounded CI
  changes. All existing Frozen, approval, report and diagnostic evidence stays.
- Producer fingerprint stdout SHA256 remains
  `f690f9c08b6b2692af5c0c1cdfc957c768ffa13841406f837f4f899518320866`.
- Existing evidence reuse is explicit: 105 historical manifest hashes verified;
  old exact29c/722/7e3 Actions logs re-read, with1277/1295/1193 PASS respectively.
  Those runs are not new executions of this v2 source.

Independent-review findings were repaired without changing approved arithmetic:
finite-input overflow/derived nonfinite deltas become per-cell NOT_RUN; the replay
requires the complete result schema and literal approved contract; approval-only
edits trigger readiness CI. Original review and successor repair review are
retained separately. Normal-case numerical trace commitments are unchanged.

The new `ACCEPTANCE_MANIFEST_V2.json` and independent implementation review
record the bounded handoff verdict. Fresh publish-time Actions and the exact
carrier SHA are recorded in PR31's current description, with actual checkout
SHAs and artifact digests. Until those runs finish, current CI is PENDING,
not CI_VERIFIED. No post-publish result is invented in this pre-push package.

## CI repairs and remaining dependencies

N3: the three inherited push-only workflows now install the already-used
pytest9.1.1/NumPy2.3.5 on Python3.11; diagnostic tests are not weakened/skipped.
QGV and Leaderboard offline jobs use explicit bash, which supplies pipefail;
the synthetic `false | tail` negative returns1 and positive returns0.
These push-only workflows are NOT_TRIGGERED on this Codex branch. No real
producer workflow was dispatched and no external owner branch was edited.

Primary Integration Writer must fresh-fetch and independently re-run CDR-011's
13-point verification, particularly items5 and6b, then build its new combined
trial from fresh38/31/35 heads. The earlier38 results do not certify that trial.
Codex preserves PR35's F1 implementation and updates its dependency by a normal
merge. Global, PR38 and Dynamic Workflow PR37 remain read-only.

The earlier N2 trusted-issuer identity normalization issue remains a
before-real-source boundary; this change adds no real source taxonomy/default.
PR35's NB1 external-copy transport finding remains non-blocking in the current
pinned checkout context. Web validator hardening requiring the17 protected
digest repin remains USER_DECISION_REQUIRED and belongs to its external owner.

## States and boundaries

BRANCH_STATE: approved additive production v2 and bounded synthetic validation;
see the acceptance manifest for the local review verdict and PR31 for current CI.
INTEGRATION_STATE: Draft stacked PR31 on exactPR30/86ad, NOT_MERGED; external
independent integration verification and the successor combined trial are pending.
CANONICAL_STATE: `b8e39a2196a6d7794a04a0cd5393c68329e126ca`, NOT_MERGED.

C0-C7 SOFTWARE_FROZEN; C8 SYNTHETIC_VERIFIED / NOT_FROZEN, maturity delta0.
Actual CAL_VERIFY0, Holdout0, actual numeric configuration0, publication/grants0,
Official/LIVE0, canonical merges0, deployments0, paid resources0.
Arithmetic selection is resolved by CDR-010; no new arithmetic D3 is needed.
Real numeric calibration, effect floor, A8/A10, real access and promotion remain
unapproved. The next automatic step belongs to the Primary Integration Writer.
