# Additive routing and invariance clarification · 2026-10-03

This extends the original takeover audit. Original records and upstream evidence remain unchanged.

## Exact PR routing

- Track A's canonical integration is merged PR3, original tip `a79642f7aa174cc37b981298d0ff1cec6b04e974`, merge `bd6bf42bdd9c6274b595471c65e3482f37317f9c`.
- Track D's canonical integration is merged PR1, original tip `da86dfc26dcaa5c32c60762683dcca702a0c57b8`, merge `281b13ec253e422b19e5499ad9b04cd5aa9f34fa`.
- Track E's canonical integration is merged PR2, original tip `d226481e1b49e0910642478ae80545598e2e5a98`, merge `ebf8263e925b657f38463988ba85eb3ce2d7bb51`.
- Track C's open Draft PR4 tip is `ff78c4f6c4a1a8fd15db21807de6be3905c89548`. Its active owner `ccr-22e3ff16-p7n5k5` is `b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565`, nine commits ahead of PR4. The owner and PR head are distinct; neither is canonical.
- Dynamic Workflow remains `DYNAMIC_WORKFLOW_V1_SOFTWARE_FROZEN` under the user's explicit instruction. A matching repository artifact was not located in the fresh all-ref audit. Its canonical artifact state is `UNDETERMINED_ARTIFACT_NOT_LOCATED`; absence from the audit is not proof that it was never implemented. No Dynamic Workflow feature was created or changed.

## C-28 field-level result, without widening PASS

The existing independently recomputed `producer_engine_fingerprint.py` outputs differ in two digest fields in addition to 688 additive lineage keys. Therefore the earlier phrase "no existing field difference" must be read as **no change to existing investment output values or decisions**, not zero change to every JSON metadata field.

The unchanged fingerprint tool normalizes `dataclasses.asdict` payloads and hashes their complete serialized shape. Its legacy volatile-ID/time exclusion does not strip the four approved lineage fields. Of the 688 additions, 92 enter the tool's 19 Technical and four Macro fixtures; the rest belong to the independent direct-input cases (103 Technical and 46 Macro).

| Existing fingerprint | Before | Approved adopted value |
|---|---|---|
| Technical | `82165414a2c86c5c489b7c071c44b967c344dd654238af445714bb0fe14097c7` | `66cb23830d65d1867df895a52d6cf3adef52c84a8ee2645d2c06617711a5e655` |
| Macro | `7bbfad69ac46b5886fb30f32b871ce68983adbc089d7ea21ae3b6317d108732f` | `7e427949a4c15ebaf78304cfec2d7a952f8bfec2a694371801ad90d09fe0c501` |

These are normalized-output content fingerprints, not source-file hashes or arbitrary permitted changes. Their exact old/adopted constants are enforced by the existing P01 tests. QGV, Leaderboard and Portfolio-book fingerprints remain unchanged under the approved Python 3.11 runtime. The root did not invent a replacement pin or change a numerical output to make tests pass.

The source impact remains the four existing CDR-004 approved files. Both legacy `evaluate` bodies remain AST-identical. Scoped before/after tests and the full integrated regression are separate evidence; neither grants publication or authorizes canonical merge.

## Actual decision boundary

Worker contract PR21 at `f1b5afb2c9c2e2e6cf0ed8dfccbc740a05647798`, section D item15 states: "합리적인 복수 선택지 중 선택에 따라 투자 결과 또는 검증 결과가 달라지는 경우" requires `USER_DECISION_REQUIRED`. The user's current instruction §14 gives the same boundary.

G-SUP's approved M-B simulation and implemented kernel conventions have a reproduced result difference. Neither was selected by this worker. The trusted source/sample identity document is a proposal because the opaque raw JSON commitment permits equivalent numeric re-encoding; choosing the enforcement contract affects validation eligibility. Numeric configuration, real CAL_VERIFY access, Holdout consumption and publication authority remain separate decisions. All independent approved compatibility and Web validation work continues before returning this boundary.
