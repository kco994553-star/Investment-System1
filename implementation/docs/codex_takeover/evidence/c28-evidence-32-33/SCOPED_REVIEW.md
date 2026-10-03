# C-28 evidence adoption PR32/33 independent read-only review

Workflow: `C28_EVIDENCE_ADOPTION_32_33_READONLY_2026_10_03`.
Remote baseline: **2026-10-03T07:46:02.433621+00:00**, 41 branches and
28 open PRs, all Draft. Canonical remains `b8e39a2`, Global `6dedaaf`, parent
integration `86ad362`. These are **two external upstream evidence proposals**;
they are separate from Codex G-SUP source675 and its fixed prior checkpoint.

Both proposals satisfy the three scoped review criteria:

1. Exact additive paths, retained history and CDR-004 authority.
2. Independently reproduced fingerprint exception and existing-value invariance.
3. Validation evidence with exact executed/declared/NOT_RUN attribution and actual
   observed absence of Actions, rather than an invented Actions PASS.

PR32 `e9aee0cb8b80e17f7ae12e01156f6670135de2fa` is one commit ahead and
zero behind owner `f8af596df4d235fee1f29bf0cb6c9a3cc0f89f36`; merge-base
equals that owner. It adds one JSON evidence record and appends 18 STATUS lines.
PR33 `9626ab06cd2b93cdd250159347cdda5d08f76e03` is one commit ahead and
zero behind owner `a013f1c1758642f90a65fe11df69fc234c143a48`; merge-base
equals that owner. It adds one JSON evidence record and appends 17 HANDOFF lines.
Both original validation files and all existing source/tests/tools/workflows are
byte-identical. Neither branch merges Track C, moves a test pin, edits a Frozen
file or overwrites a historical digest. The full CDR-004 user wording matches
the exact Global register at `6dedaaf`.

The reviewer independently reconstructed each before+TrackC owner `b9e01a9`
merge with `git merge-tree --write-tree --messages`, without creating a commit or
ref. The result trees exactly match the producer's recorded `f6f5f560…` and
`3c2a0a39…`. This proves **tree identity**, not identity of the author's unpushed
throwaway commit. All four adopted source blobs equal exact ownerb9 blobs.

Exact unchanged generators were run twice per tree on CPython3.11.16. PR32 has
92 additive lineage entries, exactly four optional keys on 19 Technical and
four Macro snapshots; no existing field changes. The two original-tool content
digests become Technical `66cb2383…` and Macro `7e427949…`; removing only those
four keys restores `82165414…` and `7bbfad69…` exactly. QGV, leaderboard and
portfolio payloads remain identical. These are disclosed serialized-shape digest
changes, not investment-output changes.

PR33 has 44 lineage additions plus **27 report-inventory additions**. These are
separately disclosed; report inventory is not a C-28 schema change. All140 old
report hashes and all existing investment values remain identical. Exact stdout
changes from `d1b9cd91…` to `9b9a276e…`; removing both the four fields and27
report entries reconstructs the original stdout byte-for-byte and re-hashes to
`d1b9cd91…`. All declared decomposition hashes reproduce. This extra inventory
effect must remain visible when the proposal is summarized.

Owner records declare native full-suite and mini-shim counts (PR32 owner431,
context961; PR33 owner419, context949) and distinguish final exact proposal
counts in the PR bodies from their recorded pre-final-doc draft. The reviewer did
**not** rerun those full suites/shims or Web E2E for this docs-only change. The
reviewer's actual executions are exact deterministic fingerprints, normalized
field comparisons, Git ancestry/blob/path/history and pin searches. Commands,
actual stdout and artifact hashes are in the receipt directory.

No Actions were dispatched or rerun. Reviewer PR32 branch query returned zero
runs; reviewer PR33 branch query encountered HTTP401 (retained raw response),
then connector exact-commit PR-triggered query returned an empty list. The root
subsequently executed successful all-branch Actions queries for **both** proposals;
both receipts show `total_count:0, workflow_runs:[]`. Those root executions are
explicitly attributed to root. This is an observed absence/NOT_RUN condition,
not a successful workflow and not new real-data validation.

BRANCH_STATE: REMOTE_DRAFT_EVIDENCE_ONLY_PROPOSAL.
INTEGRATION_STATE: NOT_MERGED_TO_OWNER; Track C not merged in either proposal.
CANONICAL_STATE: NOT_MERGED, unchangedb8. Capability maturity does not change from
docs/evidence alone. Owner adoption is still pending; no canonical merge is
authorized. No actual CAL_VERIFY, Holdout, grant or numerical configuration was
consumed/approved. No source, branch, PR, commit or remote state was mutated by
this reviewer.

Authoritative scoped result: `FINAL_REVIEW.json`, with all exact hashes and
declared/observed/executed qualifications. Acceptance is **3/3 for each
evidence-only proposal**; it does not mean source adoption is integrated.
