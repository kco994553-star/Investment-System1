# Independent CDR-010 v2 review

Reviewer: Codex independent arithmetic-oracle worker (this session). I authored the independent oracle/tests earlier; I did not author the production implementation, registry tests, verifier, approval JSON, or workflow delta. This review reads those changes independently. Global 13-point verification remains with the separate external main writer; no HANDOFF_READY or release verdict is assigned.

**Conclusion:** approved arithmetic, registry/schema wiring, scoped v1 preservation, shared one-shot consumption, and closed grants comply. Two medium findings concern overflow error classification and verifier completeness; one low finding concerns the approval-only CI trigger. No arithmetic mismatch, positive result from undefined arithmetic, grant, or retry bypass was observed.

Reviewed working-tree HEAD: `29c2c202aabc480c8251fc44b7b488417a56177f` on `codex/track-c-gsup-v2-2026-10-03`. This is an uncommitted source snapshot, not a new checkpoint commit. Authority: CDR-010/011 at `e30241f49e31f4ac5ab0d4f322ecddc78a044d75`. Exact SHA256 and Git blob SHA1 hashes are recorded below and in the JSON.

**IRV2-001 — MEDIUM: Finite-input overflow bypasses per-cell NOT_RUN conversion**

Unsupported arithmetic range aborts all cells through inherited CRASH_NO_RETRY rather than producing a per-cell NOT_RUN reason. No p-value, PASS, grant, or reopened one-shot was observed; durable crash refusal is preserved by inspected inherited code.

- studentized_cbb([1e308]*5, block_length=2, replicates=1, seed=0) raises OverflowError: intermediate overflow in fsum.
- studentized_cbb([1e200,-1e200,0.,1e200,-1e200], block_length=2, replicates=1, seed=0) raises OverflowError while squaring residuals, before isfinite(lrv).
- Synthetic _evaluate with the second finite vector and zero controls propagates OverflowError because it catches only MissingStatisticalEvidence.
- Finite role=[1e308]*5 and control=[-1e308]*5 produce infinite differences and _evaluate propagates ValueError: metrics require finite numeric inputs.

Recommendation: Normalize fsum/square overflow and nonfinite derived deltas into MissingStatisticalEvidence within v2 numerical boundaries, preserving the approved reducer/grouping and durable claim semantics; add focused finite-extreme regressions.

Locations: [superiority_v2.py:65](/workspace/Investment-System1/implementation/src/investment_system/evl/superiority_v2.py:65), [superiority_v2.py:83](/workspace/Investment-System1/implementation/src/investment_system/evl/superiority_v2.py:83), [superiority_v2.py:180](/workspace/Investment-System1/implementation/src/investment_system/evl/superiority_v2.py:180), [superiority_v2.py:184](/workspace/Investment-System1/implementation/src/investment_system/evl/superiority_v2.py:184).

**IRV2-002 — MEDIUM: Standalone verifier accepts omitted mandatory result fields**

Replay evidence alone can claim exact agreement for an incomplete API response. Current production includes these fields, and the separate 86-test arithmetic suite requires them, so this is a verifier weakness rather than an observed current arithmetic mismatch.

- expected is selected from production keys; it does not require the complete public v1-plus-v2 schema.
- In-memory fault injection removed draws and arithmetic_contract from genuine production results; verifier returned PASS on CE3_CONTROL, OPERAND_SEED275 and STANDARD_ERROR_UNDERFLOW. Source files were not modified.
- Removing variance_blocks was caught later by KeyError; the confirmed gap is specifically fields not subsequently dereferenced.
- The displayed report arithmetic_contract is copied from v2.ARITHMETIC_CONTRACT, so it does not prove each returned result carried that contract.

Recommendation: Require an explicit complete public key set, validate result arithmetic_contract against the approved literal contract, and compare that schema against the independent oracle rather than selecting expected keys from production.

Locations: [verify_gsup_v2_arithmetic.py:50](/workspace/Investment-System1/implementation/tools/verify_gsup_v2_arithmetic.py:50), [verify_gsup_v2_arithmetic.py:67](/workspace/Investment-System1/implementation/tools/verify_gsup_v2_arithmetic.py:67).

**IRV2-003 — LOW: Approval-JSON-only changes do not trigger readiness workflow**

Approval-only edits can miss automatic pinned-authority validation. Runtime pinning still refuses missing/tampered approval; workflow_dispatch and combined source changes remain available. This is a future CI coverage gap.

- The final reviewed workflow adds the v2 source, oracle/tests and replay-tool trigger, runs the replay, and uploads /tmp/gsup-v2-arithmetic.json.
- The pull_request paths omit implementation/docs/codex_takeover/gsup_v2_handoff_2026_10_03/evidence/authoritative-v2/CDR010_APPROVAL.json; an isolated approval record change does not match any listed trigger.

Recommendation: Add the exact CDR010 approval JSON path to pull_request.paths; retain the authority pin and immutable historical-file checks.

Locations: [codex-integration-readiness.yml:4](/workspace/Investment-System1/.github/workflows/codex-integration-readiness.yml:4).

| Check | Assessment |
|---|---|
| arithmetic | COMPLIES |
| wiring_and_schema_adaptation | COMPLIES |
| no_v1_rewrite | COMPLIES_FOR_REVIEWED_FILES |
| one_shot | COMPLIES_BY_SOURCE_REVIEW |
| no_grants | COMPLIES |
| approval_provenance | COMPLIES |
| workflow | COMPLIES_WITH_COVERAGE_FINDING |
| CDR011_routing | REVIEW_BOUNDARY_RESPECTED_EXTERNAL_VERIFICATION_OUTSTANDING |
| N3_dependency_workflow_delta | ADDRESSED_BY_REVIEWED_CONFIGURATION |
| NB4_pipeline_failure_propagation | ADDRESSED_BY_REVIEWED_CONFIGURATION_AND_LOCAL_PROBE |
| N2_real_source_normalization | DEFERRED_UPSTREAM_POLICY_GATE_BEFORE_REAL_SOURCE |
| authority_pin_negatives | COVERAGE_REVIEWED_OWNER_EVIDENCE_INSPECTED |

Schema adaptation was exercised in memory: the temporary v1 validation labels do not mutate or persist over the v2 registration; its result hash still binds the v2 spec. The registry overrides all numerical hooks and reuses the unchanged source-authority store. Stable sample claim keys omit method version, campaign, and attempt root. Claim/access intents precede feasibility/provider access, and failure stays spent.

Underflow probe `[0., 0., 5e-162]`, `L=1`, `B=1`, `seed=0` has positive original LRV `0x0.0000000000001p-1022` but SE `0x0.0p+0`; production correctly raises `MissingStatisticalEvidence`. The earlier 19-draw test also pins positive replicate variance with zero SE. Overflow checks fail closed, but raw overflow currently aborts the cohort evaluation rather than becoming a per-cell NOT_RUN.

Approval provenance passed: runtime JSON blob `3a9eecbba5a7454c5d81ee6db209aecc4bdf113b`, original approvals, full routing-source hashes, and the verbatim CDR-010 excerpt all match their pinned sources. Ten historical arithmetic/identity/test/approval paths remain byte-identical to baseline HEAD. Workflow keeps exact owner guards and read-only permissions; its latest delta runs and uploads the independent replay.

**Earlier 86-test evidence (not rerun):** CPython 3.11.16, pytest 9.1.1; 86 passed, 0 failed, 0 skipped in 0.73 seconds. Working directory `/workspace/Investment-System1/implementation`.

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/investment-audit/venv311/bin/python -m pytest -p no:cacheprovider tests/test_evl_gsup_v2_arithmetic.py -q
```

No persistent log file was produced for this reviewer-run command. The terminal output is conversation tool-result chunk `141ad5`. The reviewed audit directory’s `v2-authority.log` contains two separate approval tests and is not the 86-test log. The 86 tests pin 171 complete hex traces, all original nine diagnostic cases plus seed275, CE4 .10 versus historical .15, FLIP .10, LEFT_SUM .35, TIE .45, seed275 .55, invalid inputs, underflow, and Frozen C6 indices.

New review work was limited to source/hash checks and in-memory numerical/schema fault probes. The verifier fault probe removed two result keys on three fixtures and restored the replacement; no source or test was edited. No full regression, normal 86-test rerun, new Actions execution, or physical one-shot registry probe was performed. No real data was accessed. Fresh-head Actions/full-regression/combined-trial verification remains external.

The latest owner delta was also independently reviewed. N3 is addressed in configuration: Track C, Leaderboard and QGV offline regression jobs now install the already-used `pytest==9.1.1 numpy==2.3.5`. Their event/permission headers are unchanged; they retain branch-filtered push events and their existing manual-dispatch capability. NB4 is addressed by explicit `bash` defaults for the Leaderboard/QGV offline jobs. A new local probe with `bash --noprofile --norc -eo pipefail` confirmed `false | tail -1` exits 1 and `true | tail -1` exits 0. QGV's real-producer job remains byte-identical to baseline; no workflow was dispatched and no real producer was run. Its inherited `contents: write` permission is unchanged, not a new grant.

The added registry missing/tampered-approval negatives were reviewed. The owner's `/workspace/investment-audit/v2-authority.log` and matching JUnit show **2 passed, 19 deselected**, zero failures/errors/skips. This is inspected owner evidence, not a reviewer-run test suite; its exact invocation/interpreter are not recorded in those files.

**N2 remains unresolved:** identity strings are not normalized for Unicode/case/whitespace equivalence, and descriptor issuance remains inside the declared trusted-coordinator boundary. Same-sample refusal assumes stable approved source/vintage/sample identifiers. Real-source normalization/issuance policy is an upstream gate before any real-source work, consistent with unapproved real taxonomy/defaults. This review neither marks N2 fixed nor introduces policy for it.

| Source path | SHA256 | Git blob SHA1 |
|---|---|---|
| `implementation/src/investment_system/evl/superiority_v2.py` | `e3f7a9977625be671fd5154b70ff8871b14459a16b3d5f838a9caf6f613a8c59` | `ceee14dc9ad7c0ba48189574cbd72ad3971d6a40` |
| `implementation/tests/test_evl_gsup_v2_registry.py` | `2d81fdb3b70d20cd074cd2b7b32b4e3b7118036758084e9f0ac1962f98a83989` | `1eb623bf50488dcf2ce292def30edd646cea24b6` |
| `implementation/tools/verify_gsup_v2_arithmetic.py` | `f9344b529dc4c737a8c9b867e922fd99556dadf80d1470726b067aa4ea0157ed` | `f788d887056a6be13fca1d38e9351e2d34aa4727` |
| `implementation/docs/codex_takeover/gsup_v2_handoff_2026_10_03/evidence/authoritative-v2/CDR010_APPROVAL.json` | `2e0ad6e96bd1b0494fd739cc55a03b337d326fd6dff2863203ebc9b6bd036231` | `3a9eecbba5a7454c5d81ee6db209aecc4bdf113b` |
| `.github/workflows/codex-integration-readiness.yml` | `e8f3ae2812a7e450be24517c872030374af41734cd126507adab18daff9b50a1` | `10ba816333675d58de98226b215001b12b034898` |
| `implementation/tests/evl_c8_gsup_v2_oracle.py` | `e2db7498b6819783ac5d977c34950078f632c4e4dbb2ddf973b26cace8a9c6f5` | `aca5567dbb61c0b3e31531a228420af441961a9e` |
| `implementation/tests/test_evl_gsup_v2_arithmetic.py` | `6f7b24013016b9956a3ff4496f717826db6dbea3e7af5c1a6127807eb7014b17` | `8ac4b88bcf3154a5ac2dafa3923d58099528bd7e` |
| `implementation/src/investment_system/evl/superiority.py` | `c61268921e5a9147e90810747e9ab6cd2896dd2fab89cb314d390dc0ff760498` | `8a1254d7b77514f6015dfff4af0e4a53f57f22af` |
| `implementation/src/investment_system/evl/statistical_kernels.py` | `61f70937456d8a54cb027a7522f2a2d1c890bccc92f9f19de28082a2001e12d1` | `28e1c1842625bacabc6ffc9c9b172261e7d6585a` |
| `implementation/src/investment_system/evl/gsup_source_identity.py` | `d34fc10d396f37fce65a5580263d2d35207e7d2f4f347fe300c1f1b81c33c548` | `fa93bf88f8d77b293421a8d0b5095757b22f72d8` |
| `implementation/src/investment_system/evl/superiority_source_identity.py` | `3ad8ca25f724cd3d07271ec8a38b95ca8779fe57f14ccf252e1030aa7acca0fa` | `71bf737578866b762a0ee82506f8f5db9418f8ba` |
| `implementation/reports/track_c_c8_gsup_v2_source_identity_approval_2026-10-03.json` | `0fc8ed2b55b3aba4cf566f0e7c9e7146324ae4aec5e22c307fd9a9a8ae9991d8` | `a5279d516c028f0a8cb9166ee2d54366da00877b` |
| `implementation/reports/track_c_c8_a6_method_simulation_source_2026-10-02.py` | `c1f56a3f709c5fed65336fb5f33473f957c8caad706bfc4e48534ca3161f34ce` | `e112f41f34d4ead287699657750875770b4c4705` |
| `implementation/reports/track_c_c8_a6_method_approval_2026-10-02.json` | `e3ba85ad8fa2a2e49aa8003aa1b663fd9758e20a7bfeec136ecd558bcc084987` | `a6f994144ac8e7073c74fdd16983c92eac54eb5f` |
| `implementation/reports/track_c_c8_a6_partial_approval_2026-10-02.json` | `262a1e3be64f7f1a7bdb75bf288eb0f8dea8603e5f55bb61248a35ed866c62ed` | `4f897ec79f341653d8a69aecdfe7aa7eb33b6566` |
| `/workspace/investment-audit/global-oracle.py` | `e2312fd87e29c4f3b057bfcf7b054e02ba81b916e02b08b3e241f5def64b74b2` | `ec671fa87f18aff22450d1a6ede285bc6b5402c7` |
| `.github/workflows/track-c-evl-validation.yml` | `9dd09fc991eeb4a131f3c85594e0ce878d4ce017c224ca81f4e2436214330813` | `2cc85ba4a2f222826c5ea50bdf80359ea890e6ac` |
| `.github/workflows/leaderboard-real-producer.yml` | `d242494bec6e0a877f547d6ab404ff03cb6a4be97afcdaa8b665d8990f5f2af3` | `da568b4e43561b194fab5ed2cf9479f5702946b7` |
| `.github/workflows/qgv-producer-real.yml` | `c4ae20933585080b6cbeef14ff94cfb8fbacb40d37784aa4cac6b158b73f8bd3` | `efec0e794c664dc9458429aab4f0ab1c54d77ee3` |
| `/workspace/investment-audit/global-latest-review.md` | `dfbd5816035c101b4dde9c62dd5871433c881033cafdbb040576ed3b7e802763` | `2a882e2e43b1dc3b131d61d6527cacabf63c32d6` |
| `/workspace/investment-audit/global-current-handoff.md` | `23e65cadb5d98598c9e51102e962ee4eaadc3a98d77c1546f6db4bd5df37be5f` | `15977cbc0c64da8ff67396b818f695e0c71f402f` |
| `/workspace/investment-audit/v2-authority.log` | `b72275b4e68b6f37d8c40407fff5159aec2308200810467ae158bf9083857e1e` | `e6dabec777bacb4d649344af3f675149102288a7` |
| `/workspace/investment-audit/v2-authority-junit.xml` | `2772bbe01f447447b4597aaaf7b68265a759d6185679d6676048c408e018c23a` | `6bd100cf917906e8e10872cd8e5396822c67464a` |

Coordination authority source SHA256: `43e6409a7de5d62ed9a6e253fd2a010efd59bdbf17288036c4efd9781e57e5ae`; Git blob SHA1: `46e4a67b2fb7c3b961fe9dc35b9b981e6fe6662a`.

Only written artifacts: [JSON](/workspace/investment-audit/independent-v2-review.json) and [Markdown](/workspace/investment-audit/independent-v2-review.md). No source/test/workflow changes, commit, push, grants, or handoff assignment.
