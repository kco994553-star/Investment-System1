# Chart CI follow-up v0.11 — PR #46 terminal failure

- Observed: 2026-10-05T06:36:14.933Z
- Chart owner branch intake: `40a5c266322d36dbf30a683f6f632508352145bc`
- Dependency subject: PR #46 `a3e3f6cf5452d056de2df7845a17014765aa3ff3`
- Exact run: `37267962000`, attempt `1`, job `111628676484`
- Result: **FPIA_FAIL** / workflow **failure**
- Artifact: `11328740798`, digest `sha256:13d7f067019af8530e7a2aaabc21201ffa39018f472b15dbb8510d75c219728c`
- Verified result hash: `3f7b27e7fc9c1d25fc9dc66cc9db76f37ad43b338289a3022c3c7012d263b41d`

The failure is exact-subject evidence, not a stale-head inference: full regression recorded 2 failures among 2,184 tests (`test_no_numeric_thresholds`, `test_no_sha_or_pr_literals`). Authority, runtime provenance, Track C projection, v2 binding and integration-interference checks passed, while code identity remained diverged and Frozen tools on T failed. D3-c and D3-e non-claims remain.

Chart impact: A-G3 remains **OWNER_ACTION_REQUIRED**. Lane A remains 6 open / 0 closed; Lane B remains 0/19 admitted. This run closes 0 requirements and 0 production blockers, creates 0 new Chart product blockers, and changes only the PR #46 dependency state from running to terminal failure. Current Target Strategy Theme production implementation is not admitted. No retry or other-owner write was made.

Next exact action: Integration/FPIA owner repairs the current PR #46 subject and publishes a fresh exact-head run plus governance/independent evidence. Chart Main may continue independent FAST/STANDARD work under the risk-proportional policy, but this CI follower only consumes queued exact runs.
