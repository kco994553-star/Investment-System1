# Independent CDR-012 oracle and bounded review

**PASS in the authorized synthetic scope; no new findings or unresolved F1/F3 finding.** New files are frozen after 77 tests passed with zero skips. The main owner can continue the single full-suite run and Actions. This report does not assign HANDOFF_READY or replace the Primary Integration Writer's external verification.

Reviewer: Codex independent oracle/test author, this session. Authored only [new oracle](/workspace/Investment-System1/implementation/tests/evl_c8_gsup_v2_cdr012_oracle.py) and [new tests](/workspace/Investment-System1/implementation/tests/test_evl_gsup_v2_cdr012.py), plus evidence in this audit directory. Production, verifier, workflow, old-test adapters and approval supplement were authored separately by the main owner and reviewed read-only.

Authority: Global `1620f7118dbe91283cde1cc1431cdea236ab0829`, CDR-012. Baseline PR31 `e0b6d809058511d4bef7ad1aeccad79c5eae3ff8`.

Initial [red receipt](/workspace/investment-audit/gie010-repair/cdr012-independent-red-kernel.json) was captured with baseline production confirmed unchanged: historical near-tie p=.20, independent multiplication p=.15; both alternating-negative seeds returned .05 despite 19/19 degenerate draws, while the new oracle refuses them. The receipt is preserved.

New targeted command (CPython 3.11.16, pytest 9.1.1, implementation directory):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /workspace/investment-audit/venv311/bin/python -m pytest -p no:cacheprovider tests/test_evl_gsup_v2_cdr012.py -q --junitxml=/workspace/investment-audit/gie010-repair/cdr012-independent-targeted.xml > /workspace/investment-audit/gie010-repair/cdr012-independent-targeted.log
```

**77 passed, 0 failed/skipped in 0.40 seconds.** [Log](/workspace/investment-audit/gie010-repair/cdr012-independent-targeted.log) and [JUnit](/workspace/investment-audit/gie010-repair/cdr012-independent-targeted.xml). Four actual registry tests cover all-F3 and mixed one-F3/seven-valid-cell cases at seeds 7/11. Every aggregate is NOT_RUN; claims/provider reads remain spent; same-target and renamed-root/campaign retries are refused. Missing/tampered supplement tests refuse before registration, claim or outcome.

The oracle imports exactly hashlib/json/math/random and reproduces the original Random/randrange circular-block stream. Residuals are multiplied d*d before fsum. All-degenerate refusal happens before p-value construction. Partial degeneracy retains B+1. `[.05]*12` is explicitly preserved as literal .05 when no replicate is degenerate; exact-zero and positive-variance/zero-SE underflow cases refuse as specified.

Pins: 12 computed full-output fingerprints, 3 no-p diagnostic fingerprints, and 19 complete near-tie hex trace rows. All 267 trace rows were corroborated against the separate read-only GIE008c scalar derivation, adapted in memory solely for multiplication. Production outputs were never used for expected pins.

Historical pins: old oracle SHA256 remains `e2db7498b6819783ac5d977c34950078f632c4e4dbb2ddf973b26cace8a9c6f5`. Old EXACT_FINGERPRINTS/GOLDEN_TRACES AST literal values are unchanged. Original diagnostic/seed275/underflow numerical hex fields do not change; new fingerprints include the two added contract keys.

Near-tie changes are separately pinned: LRV `0x1.48eca8641fdb9p+3` → `0x1.48eca8641fdb8p+3`; observed T `0x1.cf1f15ba01c38p+0` → `0x1.cf1f15ba01c3ap+0`. Replicate index 4 keeps t=`0x1.cf1f15ba01c38p+0`, loses tie/exceedance, and r/ties/p change 3/1/.20 → 2/0/.15. Other changed variance/SE/t fields are listed losslessly in the JSON; history is not repinned.

| Read-only check | Assessment |
|---|---|
| F1_multiplication | COMPLIES: both authoritative variance sums use d*d; no Pow AST node in v2. Reducer, direct block sums, grouped mean, Frozen C6 RNG, ceil(n/L)-1 and SE predicate remain as approved. |
| F3_all_degenerate | COMPLIES: exact degenerate==replicates check after all B draws raises MissingStatisticalEvidence before return; no p-value exists. New oracle raises OracleNotRun with diagnostic-only evidence without p. |
| partial_degeneracy | COMPLIES: remaining valid draws retain denominator B+1; CE4 r=1,d=1,p=.10. |
| positive_literal_residue | COMPLIES: [.05]*12 at seeds7/11 has positive residual LRV, zero degenerate draws and p=.05, unchanged without epsilon/tolerance. |
| actual_registry | COMPLIES: four new actual-assess tests cover all-F3 and one-F3/seven-REJECT_H0 mixed cells at seeds7/11. Aggregate is NOT_RUN, grants stay closed, one claim/provider read stays consumed; both same-key assess retry and renamed-root/campaign feasibility retry are refused. |
| supplement_authority | COMPLIES: original CDR010 bytes/pin unchanged; supplemental CDR012 source commit/blob/SHA256 and exact quoted section verified; runtime supplemental blob matches. Missing/tampered supplement refused before registration/provider/claim in two new tests. |
| verifier | COMPLIES: imports new independent oracle, retains explicit PUBLIC_KEYS and independently literal six-key APPROVED_CONTRACT, checks complete schema, exact repr/hex, near-tie p=.15 and both all-degenerate refusals; reports sources for both old/new oracle and both approvals. |
| workflow | COMPLIES: new oracle/test/supplement paths trigger readiness; new oracle/test allowed as additive protected paths; predicate covers old/new v2 oracles, and historical owner-file guards unchanged; replay renamed CDR010/012 and still uploaded. No new dispatch/grants. |
| historical_preservation | COMPLIES: old CDR010 oracle, v1 oracle/tests/kernel, Frozen C6 and identity modules remain byte-identical to initial baseline hashes. Old active arithmetic EXACT_FINGERPRINTS and GOLDEN_TRACES literals match e0b6d80 AST values; owner only adapted their evaluation to H while active comparisons use O. |
| scope_and_grants | COMPLIES in reviewed synthetic scope: no epsilon, rounding, numeric default, actual CAL_VERIFY/Holdout or new grant. N2 real-source normalization/issuance remains a separate unresolved upstream gate. |

Owner replay evidence was inspected, not rerun: 15 cases PASS, numerical hash `bb883332e44e97689bc28ab36f55a88e295ee44149dd4306a94401607cec9227`, matching current production SHA256. Full regression and Actions remain outside this worker's execution scope. N2 identity normalization/issuance is still an unresolved upstream gate before real-source work. No actual CAL_VERIFY/Holdout, defaults, epsilon, grants, source edits or branch-history changes occurred.

| Source | SHA256 | Git blob SHA1 |
|---|---|---|
| `implementation/tests/evl_c8_gsup_v2_cdr012_oracle.py` | `fdf999c763f0f03fb4b4590daddf8e7a2b04b4050790ff648466be4eec099326` | `82d256beb531500eead76e1d9f743e4ea1e65b02` |
| `implementation/tests/test_evl_gsup_v2_cdr012.py` | `51d7e177601370674972be6c7f210f42a0a0ff340da0465544a07723558e74ad` | `6cc33bb13fa50ba95337c0699ac1dcb734925bff` |
| `implementation/src/investment_system/evl/superiority_v2.py` | `4733f41ee5c85a8a159047a8f2f996fed9edc9a1a4e14d01aa671b33a8a1fa64` | `8e56a66e011c83f0d8a7bc222c1705c407887268` |
| `implementation/tools/verify_gsup_v2_arithmetic.py` | `04b3012cbe0f94a17d8a94022252c2b1d0f18e54bd08e6728d4e09a4a84e1e91` | `9647d1b601a10b87b68effcc856c59c472c095ab` |
| `.github/workflows/codex-integration-readiness.yml` | `4af6061dd0ca6fc191425d19af21a07a13ef36fc6fc6265b27030dcc5b76b3b6` | `0fddb87381ce8d4cb3c9cc0d45d3dedd5eb74e94` |
| `implementation/tests/evl_c8_gsup_v2_oracle.py` | `e2db7498b6819783ac5d977c34950078f632c4e4dbb2ddf973b26cace8a9c6f5` | `aca5567dbb61c0b3e31531a228420af441961a9e` |
| `implementation/tests/test_evl_gsup_v2_arithmetic.py` | `2640f88d87b110a6b24c54abc71f9df6da470594dde4478cc649527e2c2d9478` | `5280e303fa845534c94dfc0ca5b1a19d9a7901ad` |
| `implementation/tests/test_evl_gsup_v2_registry.py` | `2d81fdb3b70d20cd074cd2b7b32b4e3b7118036758084e9f0ac1962f98a83989` | `1eb623bf50488dcf2ce292def30edd646cea24b6` |
| `implementation/tests/test_evl_gsup_v2_repair_negatives.py` | `8c896575532b60f31769ab63a406e70c9df575ae51ff8dd07d50bb1c19046b81` | `a9f83bbb40a8dcffa65f02f93fc8fbeed0bb0533` |
| `implementation/src/investment_system/evl/superiority.py` | `c61268921e5a9147e90810747e9ab6cd2896dd2fab89cb314d390dc0ff760498` | `8a1254d7b77514f6015dfff4af0e4a53f57f22af` |
| `implementation/src/investment_system/evl/statistical_kernels.py` | `61f70937456d8a54cb027a7522f2a2d1c890bccc92f9f19de28082a2001e12d1` | `28e1c1842625bacabc6ffc9c9b172261e7d6585a` |
| `implementation/src/investment_system/evl/gsup_source_identity.py` | `d34fc10d396f37fce65a5580263d2d35207e7d2f4f347fe300c1f1b81c33c548` | `fa93bf88f8d77b293421a8d0b5095757b22f72d8` |
| `implementation/src/investment_system/evl/superiority_source_identity.py` | `3ad8ca25f724cd3d07271ec8a38b95ca8779fe57f14ccf252e1030aa7acca0fa` | `71bf737578866b762a0ee82506f8f5db9418f8ba` |
| `implementation/docs/codex_takeover/gsup_v2_handoff_2026_10_03/evidence/authoritative-v2/CDR010_APPROVAL.json` | `2e0ad6e96bd1b0494fd739cc55a03b337d326fd6dff2863203ebc9b6bd036231` | `3a9eecbba5a7454c5d81ee6db209aecc4bdf113b` |
| `implementation/docs/codex_takeover/gsup_v2_handoff_2026_10_03/evidence/cdr012-repair/CDR012_APPROVAL.json` | `91f40de84ec27c8e0d74d6175ffe4d2cac4ccf78dc63f06a269141e0bea9e187` | `e16038e90117ae4873ac56c1234a26e5bf3d9c0f` |
| `implementation/reports/track_c_c8_a6_method_simulation_source_2026-10-02.py` | `c1f56a3f709c5fed65336fb5f33473f957c8caad706bfc4e48534ca3161f34ce` | `e112f41f34d4ead287699657750875770b4c4705` |

Evidence byte hashes, complete pin catalog and near-tie differences are in [JSON](/workspace/investment-audit/gie010-repair/cdr012-independent-authoring-and-review.json).
