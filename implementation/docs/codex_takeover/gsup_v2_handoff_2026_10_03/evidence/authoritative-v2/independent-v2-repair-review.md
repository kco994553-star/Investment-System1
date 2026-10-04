# Independent v2 repair review

**IRV2-001, IRV2-002 and IRV2-003 are closed on the reviewed source snapshot. No unresolved repair finding or new issue was observed in this focused review.** N2 remains the separately documented upstream policy gate before real-source work.

Reviewer: Codex independent arithmetic-oracle worker, this session. I authored the earlier independent oracle/tests, not these production/verifier/workflow repairs. Original [JSON](/workspace/investment-audit/independent-v2-review.json) and [Markdown](/workspace/investment-audit/independent-v2-review.md) are preserved byte-for-byte. This follow-up does not assign HANDOFF_READY or certify the external Global13 verification.

Working HEAD: `29c2c202aabc480c8251fc44b7b488417a56177f`. Repairs are identified by exact working-tree hashes below; this is not a new committed checkpoint.

| Finding | Prior severity | Disposition |
|---|---|---|
| IRV2-001 | MEDIUM | CLOSED_VERIFIED |
| IRV2-002 | MEDIUM | CLOSED_VERIFIED |
| IRV2-003 | LOW | CLOSED_VERIFIED |

**IRV2-001:** Public wrapper validates raw inputs before catching arithmetic OverflowError/ZeroDivisionError as MissingStatisticalEvidence. Nonfinite derived role-control differences become per-cell NOT_RUN. Independent fsum/square/derived-delta/zero-division probes all refused a p-value; _evaluate returned NOT_RUN rather than aborting. Normal fsum/block/RNG operation sequence remains unchanged by source inspection.

**IRV2-002:** Verifier requires exact independently literal PUBLIC_KEYS and APPROVED_CONTRACT, selects oracle keys from the public schema, and reports the approved literal contract. Independent omission of draws/contract, unknown-field and changed-contract faults now fail at the first valid fixture; all in-memory replacements restored.

**IRV2-003:** pull_request.paths includes the exact CDR010_APPROVAL.json path, so an approval-only change matches. Repair-test path is also in trigger/protected-addition allowlist; existing preservation and replay/upload steps remain. No workflow dispatch was performed.

Nine independent focused fault probes passed on CPython 3.11.16 using `/workspace/investment-audit/venv311/bin/python`, with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src` from the implementation directory. The schema faults stopped at the first valid fixture. No normal 118/86-test suite or full regression was rerun. No persistent fault-probe log was written; the exact observed results are in the JSON and conversation tool-result chunk `9de037`.

Owner final evidence: [log](/workspace/investment-audit/v2-final-targeted.log) and [JUnit](/workspace/investment-audit/v2-final-targeted.xml) independently inspected: **118 passed, zero failures/errors/skips** (86 arithmetic + 21 registry + 11 repair cases), log duration 0.51 seconds. The log/XML do not record the exact command or interpreter version; this is owner evidence, not a reviewer execution.

The numerical wrapper preserves the approved normal operation sequence. Verifier constants were checked from their AST against independent literal requirements. The exact approval path now matches the PR trigger. Ten historical files remain byte-identical to HEAD. Identity/one-shot implementations, authority JSON, oracle/tests, N3/NB4 settings and grant gates remain unchanged from the original review.

N2 normalization/issuance policy remains **unresolved before real-source work**. No source taxonomy/default policy or new real-source authorization was introduced. Global13/fresh committed HEAD/Actions/full-regression/combined-trial work remains external.

| Final source path | SHA256 | Git blob SHA1 |
|---|---|---|
| `implementation/src/investment_system/evl/superiority_v2.py` | `41f67dd28200370f472016e16214ee08edb31dcd75aba91726494799a6614603` | `370e9b4204ba30772dae9ce1f031350a2c7ad05e` |
| `implementation/tests/test_evl_gsup_v2_registry.py` | `2d81fdb3b70d20cd074cd2b7b32b4e3b7118036758084e9f0ac1962f98a83989` | `1eb623bf50488dcf2ce292def30edd646cea24b6` |
| `implementation/tools/verify_gsup_v2_arithmetic.py` | `fa4295124667de17eb3123cefdc16565d353a105ec575cbb07bcb1ea14a308fc` | `0b134fd88f70054bbbbec04d5cef9684ff0d0ec2` |
| `implementation/docs/codex_takeover/gsup_v2_handoff_2026_10_03/evidence/authoritative-v2/CDR010_APPROVAL.json` | `2e0ad6e96bd1b0494fd739cc55a03b337d326fd6dff2863203ebc9b6bd036231` | `3a9eecbba5a7454c5d81ee6db209aecc4bdf113b` |
| `.github/workflows/codex-integration-readiness.yml` | `12ee056c95ac9c612d106841420b11ac18d9414f5a3ff8cf5c7d88abb39acca2` | `f36f9df3a6dcb518274edf002bbcf115bb988181` |
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
| `.github/workflows/track-c-evl-validation.yml` | `9dd09fc991eeb4a131f3c85594e0ce878d4ce017c224ca81f4e2436214330813` | `2cc85ba4a2f222826c5ea50bdf80359ea890e6ac` |
| `.github/workflows/leaderboard-real-producer.yml` | `d242494bec6e0a877f547d6ab404ff03cb6a4be97afcdaa8b665d8990f5f2af3` | `da568b4e43561b194fab5ed2cf9479f5702946b7` |
| `.github/workflows/qgv-producer-real.yml` | `c4ae20933585080b6cbeef14ff94cfb8fbacb40d37784aa4cac6b158b73f8bd3` | `efec0e794c664dc9458429aab4f0ab1c54d77ee3` |
| `implementation/tests/test_evl_gsup_v2_repair_negatives.py` | `8c896575532b60f31769ab63a406e70c9df575ae51ff8dd07d50bb1c19046b81` | `a9f83bbb40a8dcffa65f02f93fc8fbeed0bb0533` |

| Evidence / preserved review | SHA256 |
|---|---|
| `/workspace/investment-audit/v2-final-targeted.log` | `060b3d7b94ed5b198e057c507cee4a1a38de94f176b31df37de2092e49b055fe` |
| `/workspace/investment-audit/v2-final-targeted.xml` | `cbfef9f6107059901fcf4aed1d29b20ad0ce178a2a76e724c11c67424a51737d` |
| `/workspace/investment-audit/independent-v2-review.json` | `4a171405d40d6f36edffd2bc15cf830f9d6dcb4ba478d46960f776f23cb995cb` |
| `/workspace/investment-audit/independent-v2-review.md` | `e578e94912564fef8175308c14c3266687ab4a02db3fe5643570d85493a5657e` |

Only the new [JSON](/workspace/investment-audit/independent-v2-repair-review.json) and [Markdown](/workspace/investment-audit/independent-v2-repair-review.md) were written. No source/test edits, commit, push, workflow dispatch, physical registry creation, real-data access, grants, or handoff assignment.
