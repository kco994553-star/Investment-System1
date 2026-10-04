# Final G-SUP source identity Actions review

Three review criteria are complete: all eight new PR #31 runs were independently
observed and completed successfully; actual checkout identities, native regression
and browser/Macro outputs were parsed; all three published artifacts were archived
through the GitHub connector and verified against GitHub-provided SHA256 digests.
The completed run-specific receipts and artifact bytes are retained in this scoped
external directory. The reviewer did not dispatch, rerun or modify GitHub or source.

PR #31 is Draft, based on exact `86ad3628dd5c62c6d873e42511e577f24f4fb588`.
Final source HEAD is `675d0d298fbaab5b8473ed048a561ef84e2f3e78`.
The inherited workflows actually checked out synthetic PR merge commit
`547676da75308b02a35f9cef1b5be3b028bdf101`, whose tree exactly equals the source
tree `0d4852e3b682cad038fd432dc1625167022ca82e`. These are distinct commits.
The native combined job checked out the exact source HEAD; the Macro job checked
out exact approved source `4a07099e36ec3cecda24b82ecedad53800f0aa81`.
GitHub job metadata head SHA describes its enclosing run and does not override the
checkout identity proven by `git log -1 --format=%H` in each archived job log.

| New workflow | Run ID | Result | Actual checkout |
| --- | --- | --- | --- |
| codex-integration-readiness | 37106686279 | Native pytest 1,277 PASS; Producer-Web 6 groups PASS; Macro 11 PASS | Source 675d; Macro 4a07099 |
| web-mvp-validation | 37106686295 | Native pytest 1,277 PASS; original Web 10 groups, Language/Search 8 groups, Node 26 checks PASS; entity metadata failures empty | Synthetic merge 547676d |
| technical-real-producer | 37106686280 | Native pytest 1,277 PASS | Synthetic merge 547676d |
| technical-real-model | 37106686281 | Native pytest 1,277 PASS | Synthetic merge 547676d |
| us-equity-session | 37106686274 | Native pytest 1,277 PASS | Synthetic merge 547676d |
| sec-primary-disclosure | 37106686285 | Native pytest 1,277 PASS | Synthetic merge 547676d |
| p01-research-publication | 37106686269 | Native pytest 1,277 PASS | Synthetic merge 547676d |
| qgv-invalidation-binding | 37106686317 | Native pytest 1,277 PASS | Synthetic merge 547676d |

The native combined JUnit has zero failures, errors and skips. Producer-Web browser
artifact reports six completed check groups with zero errors, preserved provenance,
as_of/freshness/methodology, ko/en and mobile/desktop absence states, loading and
failure/retry. Research display, Frozen and Live grants remain NONE. Its literal
withheld fixture manifest, records and browser JSON are byte-identical to the
previous 86ad integration artifact; this is synthetic fixture compatibility only.

| Artifact | GitHub digest verified against local download SHA256 |
| --- | --- |
| 11268415800 native combined | `3a7054bbca344cf07bb3ff3520502f603f0d22e45efb33b24432e7d71f9aee69` |
| 11268445230 Macro | `6816821106fe6f590ffa5cc5f138fc773ed5daef559542df4409fb7b83fba19a` |
| 11268815169 original Web | `b4e22c87c2a5d39032cfa86d4d1f710dd66933c0eee7902fa985e692a3256dfb` |

The fixed workflow baseline remains 2026-10-03T06:48:04Z, source 86ad, eight already
successful workflow runs and 1,165 passing tests. This review records only the eight
new successful runs. Test counts describe verification coverage, not progress or
completion percentages. Tool manifests retain Actions=NOT_RUN because tools do not
dispatch workflows; the enclosing completed Actions execution is documented here.

Actual CAL_VERIFY/Holdout: NOT_RUN. Publication grants: NONE. Canonical merge:
NOT_RUN. Authoritative M-B v2 numeric kernel: inactive. Arithmetic reduction remains
USER_DECISION_REQUIRED_ARITHMETIC_REDUCTION. These CI results validate additive
synthetic source identity software and retained compatibility, not real investment
validation, Freeze, Official promotion or operational readiness.

BRANCH_STATE: exact remote source observed at 675d, Draft PR #31 open.
INTEGRATION_STATE: all eight new trial workflows passed with source checkout/tree
identities recorded separately.
CANONICAL_STATE: unchanged; not merged.
