# Retained Q recovery delivery and gate bounds

This supplements `Q_INPUT_RECOVERY.md`. Source execution is
`93a699ede9480ca0d173cd7efd4c5109e4d590f4`; source handoff producer is
`4352c8ec206d41c40b29a4bd723b1fbb61d740a4`. No score calculation is performed
by this delivery work. Evaluation date remains 2026-11-04. The original financial
cutoff remains 2026-11-04T02:29:35.166580Z; the retrospective input/review cutoff
is 2026-11-13T11:57:04.159366+00:00. This is not historical system PIT.

## Delivery to Main

For each of `operating504` (504 code rows / 501 issuers) and `held1057`
(1057 issuers), `delivery/<scope>/manifest.json` binds the existing
`qgv-dual-delivery-manifest/1` summary/index/detail files containing all three
333 candidates. `distributions/<scope>/` and `bin-routing/<scope>/` use the
existing distribution/1 and bins/1 contracts. Every output is <=1,800,000 bytes.
Scores, ranks, D1–D10 and tie boundaries are read from the new saved results.
No old distribution member hashes are copied. Missing scores stay outside bins,
inside the original denominator. Additional factors still contribute zero.

There are 1071 / 969 model × ranking-scope × factor groups, respectively;
139 / 151 have enough valid evaluation rows for complete deciles. Their binned
factor-row memberships total 13679 / 27142, NOT unique company counts. All
26 / 28 groups whose D10 exceeds the old top20 window are delivered in full.
Stored ordinal company-ID tie boundaries remain unchanged.

## Two independent retained-input anchors

`dual_qgv_input_anchors.input_anchors` produces
`qgv-dual-input-anchors/1`, separately from result summary and runtime lineage.
Its trust chain is the **previously pinned** private handoff manifest → bundle
manifest → each exact retained snapshot's byte hash/size → existing `_identity`.
The root pin must come from the earlier preservation receipt, never from the
new result being checked. No original source archive is downloaded again.

Required output fields: `scope`, `expected_evaluation`, `expected_reference`,
`preservation` (repo/ref/path/commit, handoff hash, bundle descriptor),
`source_files` (two snapshot descriptors), `execution_sha`, `projection`,
`generation_rule`, `runtime_lineage_used_as_proof:false`,
`new_score_calculations:0`, `whole_market_denominator:null`.

Both full identities include population ID/version, members hash, evaluation
date, input cutoff, code-row and issuer counts, input hash, snapshot ID,
classification records hash/context. Compare both against **every** board's
bindings and candidate population, and evaluation against the delivery index.
`validate_anchored_delivery` performs those comparisons after validating the
separately installed anchor-file pin. File hashes and result manifests remain
mandatory; this check does not replace them or source accounting validation.

Projection means only exact equality of selected input rows with reference rows.
The two input version chains can legitimately differ. For held1057,
`review_context` also differs because each points to its own original snapshot.
Therefore do NOT label this as old `qgv-dual-input-projection-proof/1` (which
asserted only five top-level changes), or silently relax that contract. Nor can
old #528 reference-view input hashes attest the newly transformed reference.
The new anchors coexist with both old contracts; all old deliveries remain valid
under their original independently pinned inputs.

Main change: stage this anchor under an independent fixed SHA, verify each input
identity, then mark both checked. #536 `8430c9b7b551f413cd971056020f47c8c702a8ca`
does not yet consume it; a successful summary/detail/bin read is not completion
of this new independent-input check, browser integration or deployment.
`q-input-anchor-examples/` is a producer-generated synthetic **binding-only**
fixture, not a full board or real company data. Wrong evaluation/reference hashes,
members/date/cutoff/version, altered preserved bytes and runtime lineage fail.

## Calculation clock

The preserved execution script, six run manifests and logs contain no actual
calculation timestamp. `qgv-dual-delivery-clocks/1` explicitly contains
`calculated_at:null`, `calculated_at_reason:EXECUTION_TIMESTAMP_NOT_RECORDED`,
the execution SHA and inspected record references. `delivery_generated_at`
records only the new projection time. Producer verification, review, acquisition,
commit and file modification times are not substitutes. Main #536 already allows
null; the reason remains visible and must not be filled at staging.

## Official gate: fixed input scope versus a permanent issuer ban

`sector_qgv_classification.official_q_gate` replays existing calc23.1 published
Q with its original industry/issuer/representative/minimum8/fallback rules. It
only emits entries for supplied official source members. The retained source
has no matching official row for 563 of held1057. `sector_qgv.aggregate` requires
a finite official percentile, calc23.1 provenance and matching evaluation date.
No gate → UNKNOWN → final total null, even with nine otherwise valid factors.
There is no permanent hard-coded exclusion of those issuer IDs in the engine.
Under the **frozen official reference source and current research policy**,
however, price/financial repairs alone cannot resolve this scope barrier.

`VALUE_EXCLUDED` means V weight exclusion, not issuer removal. Current strict
aggregation still requires its pre-gate active axes; gate-known is not gate-pass.

Saved-results set analysis (unique issuers; no combining axes from different
code rows) separately retains A accounting inapplicability, E selected annual
EPS nonpositive endpoints, G gate UNKNOWN, I other core input/validation failures.
All pairwise/higher intersections and 16 mutually exclusive atoms are in the
private output. I includes historical share-basis validation, not just absent
documents. Fail-fast unvisited fields are not proven valid.

| Scope / candidate | A | E | G | I | Outside official scope P | Conditional upper N−(A∪E∪P) |
|---|---:|---:|---:|---:|---:|---:|
| Operating501 U1 | 67 | 0 | 92 | 501 | 0 | 434 |
| Operating501 U2 | 67 | 65 | 92 | 501 | 0 | 375 |
| Operating501 S1 | 0 | 52 | 92 | 422 | 0 | 449 |
| Held1057 U1 | 132 | 0 | 651 | 1057 | 563 | 427 |
| Held1057 U2 | 132 | 227 | 651 | 1057 | 563 | 368 |
| Held1057 S1 | 0 | 162 | 651 | 844 | 563 | 442 |

For held U2, A∩E=12, A∩P=65, E∩P=162, A∩E∩P=6: union689,
upper368. P alone caps held1057 at494. These bounds assume all **other** inputs,
classification, recipes and sample barriers solved. EPS endpoint restrictions
are conditional on validating the reported endpoints' common-share basis; the
numeric candidates are not adopted EPS observations. S1 A=0 does not prove all
unresolved/preparing recipes applicable. Actual joint/final totals remain0.
Keeping **all** currently UNKNOWN gates gives upper U1/U2/S1 344/297/358
operating and341/294/355 held. These are frozen-current-gate bounds, not claims
that every unknown gate is permanently structurally excluded.

95% targets remain476/501 and1005/1057. Even hypothetically resolving only the
563-member gate scope leaves accounting/EPS upper925/710/895 held: scope repair
alone cannot attain95%. Full-market denominator/coverage remain null.

### Separate research alternative; NOT applied

Investigate a versioned **official-formula out-of-sample gate replay**: reconstruct
eligible target official-Q inputs at the same date and score those target values
against the frozen original official reference pool, keeping old official outputs
unchanged. Preserve original calc23.1 industry mappings, definitions and fallback;
do not replace official Q with U1/U2/S1 Q. Target applicability, representative
identity and whether the official cross-sectional routine supports this exact
target/reference separation must be reviewed before implementation/adoption.
Compare gate-known/pass/value-excluded/unknown, overlap, and final eligibility
with a separate gate-policy ID. No promise of 563 recoveries or new final totals.
Accounting and nonpositive-EPS constraints require separate model research; this
delivery changes no formula, gate, weights, sample minimum or default.

## Resume / boundaries

New delivery and set-analysis scripts are preserved in the new private bundle.
Run `project.py` only to a fresh private output directory when source inputs or
delivery code changes. It uses existing delivery/distribution/bin producers,
not `run_board` or `dual-study`. `gate_sets.py` reads frozen results/diagnostics.
No new financial, price, security or EPS evidence was received during this work;
new inputs/raw ratios/axis scores/totals:0. Prior Q+2/+5 and REIT23 are reused.
WRB receipt and historical EPS class evidence remain precise existing blockers;
do not re-search their already inventoried source paths. Main owns acquisition
execution/delivery, authentication, staging, frontend and deployment.

Validation: 24 new anchor/time boundary tests, 158 generated files reopened
(largest1,799,692 bytes), and changed Main consumer Node reading. At #536
`8430c9b7`, summary/index and all504/1057 detail rows pass; all1071/969 distribution
groups and their bin member hashes pass. `inputVerified` correctly remains false
because that consumer does not yet handle the new two-input anchor. This direct
Node check is not a browser run or authenticated staging/deployment. Existing
score arithmetic, original 23-case classification acceptance and successful CI
tests are not rerun. The current CI full Python command is `pytest tests`, so the
new `tests/research/test_dual_qgv_input_anchors.py` is automatically discovered;
no CI list or workflow change is required.
