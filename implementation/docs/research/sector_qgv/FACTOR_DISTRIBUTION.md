# Full factor distribution delivery

Owner follow-up2026-11-12: a factor's upper-percent view must support all ten
bands, not a top-N/D10 prefix. Codex owns this projection/contract/examples;
Main owns the band selector, company-detail join, authentication and staging.
This is a companion to #529 saved dual results, not a new QGV scorer.

## Existing rules and owner-selected delivery basis

The existing `_rank_factors` first ranks **valid evaluation code rows** within
COMMON (U1/U2) or SECTOR|sector_id|accounting_template (S1). It orders unrounded,
direction-adjusted factor scores descending, then exact company_id ascending;
rank is unique ordinal. For N>=10, D10 and D1 contain floor(N/10) rows; remaining
rows are distributed among D9..D2, with the remainder allocated from D9 down.
N<10 has SAMPLE_LT_10. Equal scores can straddle these stored boundaries.

This is different from the factor score's **reference pool**: the existing engine
uses the midpoint percentile `100*(less+0.5*(equal-1))/(N-1)`, reverses LOWER
factors once, and requires at least20 valid reference issuers. Reference-only
issuers are not silently added to the evaluation display. A reference N of20
and evaluation N of3 are both valid facts and must not be interchanged.

The 2026-11-12 follow-up explicitly selects the existing saved evaluation
deciles and tie boundaries for this delivery. No score or bin is recalculated.
The earlier reference-score display remains a separate archived research candidate:

| display_policy | Basis | Ties | Status |
|---|---|---|---|
| stored-evaluation-deciles/1 | original evaluation factor rank/decile | existing company_id boundary splitting retained and flagged | existing compatibility rule; full private projection supplied |
| reference-score-deciles/1 | existing direction-adjusted reference percentile score, in ten score intervals | same score always same band | archived research display candidate; synthetic only, not selected for this delivery |

The candidate preserves original rank and stored_decile side by side. It neither
recalculates factor scores nor changes the original board result, cache/saved
settings or official score. At score100/90/80/50/0 the candidate D is10/10/9/6/1.
Equivalently upper percentile =100-score: D10 covers[0,10], D9 covers(10,20],
..., D1 covers(90,100]. It uses unrounded values. Empty/unequal-sized bands are
valid; no tie is split to fill a quota. Twenty scores of50 all enter D6. With
only3 evaluation rows and a valid20-issuer reference, these three can receive
candidate bands even though their stored evaluation deciles are null.

Do not automatically enable the candidate or alter stored ties. The owner has
selected the stored rule for this delivery, including its flagged tie splits. Original scores,
rankings, reference samples, minimum20, missing rules, gates and axis/factor weights
are unchanged. Additional-factor displays contribute zero to the core score.

## Files and join context

Entry manifest: `qgv-dual-factor-distribution-manifest/1` →
`distribution-index.json` (`qgv-dual-factor-distribution/1`) and bounded
`distribution-NNN.json` (`qgv-dual-factor-distribution-part/1`). Each file is
<=1,800,000bytes under Main's2MB ceiling. Verify the manifest's trusted SHA and
each named file's byte size/hash before consuming it. Unknown paths, schemas,
policies or incompatible contexts must fail closed. This uses a separate optional
route; the old delivery/leader manifest allowlists are not broadened.

The index contains:

- scope/data_kind/display_policy/policy_state; original board/model/configuration,
  engine and normalization versions, evaluation/reference population identities,
  source result and source byte hashes. Original whole-market denominator/coverage
  remain null. Policy is an additional cache/delivery key, not a score change.
- companies: original company_id/issuer_id/security_id, with null security IDs
  preserved. A company_id is an evaluation code-row ID, not a new security ID.
- bands: all ten labels, D10=`상위 0–10%` through D1=`상위 90–100%`.
  Stored labels are nominal decile labels, not a claim of exactly10% membership.
- groups: board×ranking_scope×variant; raw_direction and HIGHER_IS_BETTER score
  direction; evaluation_rows_in_scope/evaluation_valid_n/reference_valid_n;
  comparison_group(role, unit, N, members_hash); reference row/issuer member
  hashes; all ten bin counts including empty bins; unavailable count/reason counts;
  legacy_tie_splits; file list. Group comparison date is the referenced board's
  evaluation_population.valuation_date, not generation or price time.

Each part has group_id and **all original evaluation rows** of that factor/scope,
possibly split across files. Row fields are company_id, score, rank/rank_n,
stored_decile/stored_decile_status, display decile/decile_status, score_status,
raw_status and CORE/ADDITIONAL kind. It includes unscored/unclassified rows with
null bands and preserved reasons; null is never a zero score or D1. Joining
row→group→board and row→companies supplies its percentile interval, N, comparison
population, date and issuer/security context without copying those into every row.
No raw financial or price values are included, but real company results stay private.

`bins.count` describes evaluation rows represented in that band, **not** the count
of every reference-only issuer. Sum(all ten counts)+unavailable_count equals
original evaluation_rows_in_scope for the group. There is no full-market claim.
A QGV total/gate may be null while an individual factor score/decile is valid.
The projection never uses total availability to suppress that factor.

## Reader/filter expectations

1. Validate the source-result/manifest chain and select an explicit policy.
2. List groups from the index, without combining sector/accounting scopes into
   a COMMON distribution. The factor score already reflects HIGHER/LOWER direction.
3. Load every file named by the chosen group, validate hashes and exact group/row
   completeness; no duplicate/missing company row. A file can contain several groups.
4. Resolve all ten bands and the separate unavailable state. Select any band(s),
   including empty bands. Filtering is a row projection; never re-rank, re-bin or
   replace original N, comparison members hash or source result.
5. Join company detail using original company_id in the same evaluation context.
   Preserve different code rows of one issuer. Missing stable security ID is null.

`select_rows(artifacts,group_id,[10,1])` is the pure reference consumer helper after
byte verification. It returns original group/board context and exact retained
rows. The UI may order by the stored ordinal rank, but cannot recompute it.
The old top-N leaders remain a compatibility display limit, not this feature's
completion criterion.

## Offline command and synthetic acceptance

```sh
PYTHONPATH=implementation/src python -m investment_system.research.dual_qgv_distribution \
 --job PRIVATE_DISTRIBUTION_JOB.json --output-dir FRESH_PRIVATE_DIR
```

Job schema `qgv-dual-factor-distribution-job/1`: scope, PRIVATE/SYNTHETIC,
explicit display_policy, board_results map U1/U2/S1 → path/sha256/result_hash.
The source is the already saved `dual-result.json`. CLI validates both byte and
semantic result hashes. Private inputs require the retained scorer code version
to match for factor-direction metadata. It never invokes run_board/preview or
rebuilds a financial/price input. A private output inside a Git checkout and an
existing output directory are rejected. Fixed error codes omit private values.

Shared `dual-distribution-synthetic/cases.json` pins five hand-worked saved-score
inputs and ten outputs (each under both explicit display policies):

- All ten bands, actual0 score, LOWER factor with already-adjusted score, totalnull.
- Twenty equal50 scores: stored two per band versus candidate all20 inD6.
- Evaluation3/reference20: stored SAMPLE_LT_10 versus candidateD10/D6/D1.
- Reference19: unscored PEER_SAMPLE_SMALL outside all ten bands.
- Two sector/accounting groups: independent Ns and distributions.

Expected counts are manually specified. These are fictional saved-result fixtures,
not a claim that a scoring/strategy backtest ran. Missing/shard tampering, source
hash mismatch, duplicate/group/filter and output-size behavior are covered by
`tests/research/test_dual_qgv_distribution.py`. No existing successful scorer suite
or same-input real calculation is repeated for this projection.

## Retained-data projection verification (2026-11-12)

No new input or score computation. Stored compatibility policy only:

| Evaluation scope | Original factor records preserved | Stored valid scores/deciles | Unavailable records | Groups / all-ten-band summaries | Files / maximum bytes |
|---|---:|---:|---:|---:|---:|
| operating504 code rows /501 issuers |77112|13671|63441|1071/1071|20 /1799344|
| held1057 issuers |161721|27125|134596|969/969|40 /1799893|

These are factor-record/group counts, not newly recovered companies or QGV axes.
Each original score/rank/rank_n/stored_decile/reason/kind was compared with the
new projection; no missing/duplicate row, source result mutation or new adoption.
The comparison date remains2026-11-04. Whole-market denominator remains null.
The retained rule splits a same-score boundary in10 operating and11 held groups;
this is an actual reason to distinguish it from the unadopted display candidate.
No alternate real-company display bins have been produced pending the choice.

Main consumer332aaa561354faef33164c40d88ad8e68487d4ae was independently checked
only at the changed three input-binding boundaries: matching proof accepted,
wrong evaluation hash rejected LINEAGE_MISMATCH, wrong reference hash rejected
DUAL_INPUT_MISMATCH. Without proof, evaluation remains explicitly unverified.
This is direct Node evidence, separate from Main's reported browser tests.

Main's operating reference-anchor question: #528 reference-view.json's
reference_population.input_hash matches the retained586-row combined snapshot
and all #529 boards' bindings.reference input hash. Its **504 selected-reference
members_hash is not the586 candidate members_hash**. A private verified
operating-reference-anchor.json supplies the full `_identity` of the retained
snapshot, its raw SHA, and the view SHA. Original source8004 remains another
population in #528 bindings.reference_source. Use these distinctions when pinning
the second anchor; do not compare all three membership hashes as if identical.

## All-bin routing companion /1 (2026-11-12)

`dual_qgv_distribution_index.bin_index_artifacts` validates the **entire pinned
saved distribution batch** and adds `qgv-dual-factor-bins-manifest/1` →
`bin-index.json` (`qgv-dual-factor-bins/1`) → `bins-NNN.json`
(`qgv-dual-factor-bins-part/1`). The original distribution files remain byte
identical. This optional companion does not rename or replace top-N delivery,
its completeness checks, or the old manifest allowlist. Main adds an authenticated
route for these bounded files; no Worker/auth/limit change is made by Codex.

Each group has all ten bins with count, first/last **saved** ordinal rank,
ordered code-row members hash and `member_files` (path/bytes/SHA-256 in the
original distribution root). Empty bins have null ranks and no files. The bin
index points to the independently pinned source distribution manifest/index;
board metadata supplies model/version/configuration hash, evaluation/reference
identities/date/input/classification context and original result hash. Group
records supply variant, scope, both valid Ns and member hashes. Thus a bin must
be read with its group and board context, never as a freestanding ranking.

For N>=10, every scored evaluation code row belongs to exactly one stored bin;
sum of ten bins=N. For 0<N<10 all scored rows remain outside bins with
SAMPLE_LT_10; for N=0 NO_VALID_SCORE. Original unscored rows remain in the source
and denominator. One issuer's different code rows remain separate. No S1 scopes
are merged. Existing ordinal ties and their boundary splits are explicitly
retained; upper-percent labels describe nominal bands, not equal-sized quotas.

Main acceptance:

1. Pin `bin-manifest.json` from approved handoff, verify every listed size/hash;
   its source manifest pin must equal the approved original delivery pin.
2. Resolve group → bins file → selected band(s) → original member files. A file
   may hold other groups/bands: select exact group_id and decile after validation.
3. Check selected members' count, ranks and ordered member hash against the bin.
   Do not replace original N or ranks after filtering. Empty is valid; absent,
   duplicate, wrong-scope or corrupt files are batch failures, not empty bands.
4. Validate the complete batch before replacing the previous normal bundle;
   partial failure must retain the old manifest and its original clocks.
5. Input projection attestation is separate: distribution byte consistency
   neither proves source financial inputs nor substitutes for evaluation/reference
   independent anchors. A missing held1057 proof remains UNVERIFIED.

Reproduce (offline; output must be new, private output outside checkout):

```sh
PYTHONPATH=implementation/src python -m investment_system.research.dual_qgv_distribution_index --source-dir <existing-distribution> --source-manifest-sha256 <approved-pin> --output-dir <new-bin-routing>
PYTHONPATH=implementation/src python implementation/tools/generate_dual_bin_examples.py
```

Shared synthetic cases: `dual-bin-synthetic/cases.json` references the existing
synthetic distribution bytes and lists every expected company/rank in every bin.
No company values are copied from private results. New acceptance tests cover
missing shard, corrupted bytes, duplicated member, foreign group, mismatched
scope/count/rank, missing bin, N<10, N=23 remainder/ties and N=230 D10>top20.

Main #437/6819503612 requested N9/10/11/17/20: the additive bin fixture now
contains nine cases (five retained cases plus four manual small-N boundaries).
N9 has no bins with reference N20; N10 counts are all1; N11 counts D10..D1 are
1,2,1,1,1,1,1,1,1,1; N17 counts are1,2,2,2,2,2,2,2,1,1. These explicit saved
synthetic scores/ranks do not invoke the financial/scoring engine. Original
synthetic distribution and all real distribution/routing bytes remain unchanged.
