# Final exact-head integration checkpoint · 2026-10-03

Current combined trial: **`codex/combined-integration-2026-10-03@86ad3628dd5c62c6d873e42511e577f24f4fb588`**, Draft [PR30](https://github.com/kco994553-star/Investment-System1/pull/30).

Canonical/base/merge-base: **`b8e39a2196a6d7794a04a0cd5393c68329e126ca`**, unchanged. Global Handoff: **`integration/global-handoff-v1@f26dc7adbfedd9209e757b5e8566c665c7bbd677`**, unchanged. Existing Global writer designation was preserved; this worker only writes its scoped handoff.

## Actually completed validation

| Execution | Exact source scope | Outcome |
|---|---|---|
| Local complete regression | `bfa3e26a6fad894bfde7d96149f9d05555bac53c`, Python3.11.16 | 1160 PASS |
| Final source guard targeted | `71d5773dd235f93682722b9db762dc254379491e` | 29 PASS |
| CI configuration repair targeted | `0ea00d27f715140a380df94aa1618b5a46d07839` | 170 PASS; source/tests unchanged |
| Initial combined Actions [37102512487](https://github.com/kco994553-star/Investment-System1/actions/runs/37102512487) | actual checkout `71d5773dd235f93682722b9db762dc254379491e` | 1165 PASS; 0 failures/errors/skips; browser6groups PASS |
| Final combined Actions [37102973395](https://github.com/kco994553-star/Investment-System1/actions/runs/37102973395) | actual checkout `86ad3628dd5c62c6d873e42511e577f24f4fb588` | 1165 PASS; 0 failures/errors/skips; browser6groups PASS |
| Independent Macro job in both combined runs | actual checkout `4a07099e36ec3cecda24b82ecedad53800f0aa81`, distinct from run head | 11 PASS each |
| Technical producer/model, US Session, SEC, P01 and Invalidation final Actions | run head `86ad362…`; actual GitHub synthetic PR merge `5a0bcb54e1b683af08c965194ec05dad227a502b` | six workflows SUCCESS; each native1165PASS |
| Existing Web validation [37102973427](https://github.com/kco994553-star/Investment-System1/actions/runs/37102973427) | final PR merged tree | SUCCESS |

All **eight current workflows succeeded**. The inherited PR checkout and exact proposal HEAD are different commits; both have tree **`93982063e20229be3ed7daab97019c4a6aa33ee3`**. Explicit-head combined CI independently validates the exact proposal commit. Earlier failed inherited runs are historical evidence of test-runner/shallow-history/Python-runtime incompatibilities, not current PASS and not hidden failures.

Final exact-head full **local** regression is `NOT_RUN`; the final exact-head Actions full regression is actually executed and passed. No additional duplicate local suite was implied.

Browser evidence validates the existing Web implementation with producer/P01 withheld-contract fixtures: PASS/PARTIAL/BLOCKED remain NOT_AVAILABLE with grants NONE; provenance/as_of/freshness/methodology survive; ko/en and mobile/desktop routes, loading, HTTP/malformed-JSON failure, retry and immutable bundle/search bytes pass. This is fixture verification, not live producer publication or actual investment operation.

## Artifact integrity and preservation

Both complete Actions artifact ZIPs were downloaded through the authorized GitHub connector, and local SHA256 equals GitHub's digest. Direct shell Azure redirect403 was resolved by the connector without repeating the blocked route.

Final combined artifact SHA256: **`30d1f80b1b69dd904e88fc90ed8e5262675d11547ff4c278db18035d6e86bdbb`**. Final Macro artifact SHA256: **`5fa34f36bba73db3a3961cab08c8d403bf2e95d7e1df50fb4e11527d5b3fd2a1`**.

Portable receipts, downloaded ZIPs, JUnit, screenshots and extracted fixture evidence are retained under [evidence/final-actions](evidence/final-actions/ARTIFACT_MANIFEST.json). Machine checkpoint SHA256: **`7f78c4d16d91dadcdca3ea4625ec1b0c5c4958ab91d48eb88a2f257685d04c4d`**. The tool manifests' `Actions: NOT_RUN` means those tools did not dispatch a workflow themselves; enclosing actual Actions are recorded in separate execution receipts.

Independent final review confirms: 331 source/test blobs equal validated71d; owner EVL43, pre-C8Frozen232, canonical TrackA/QGV/Personal7351, ownerTrackC evidence/approval/register100 and all four exact approved C28 files are preserved. All16 original branch tips retain ancestry. All35 non-Codex remote heads remain unchanged. No history rewrite, force-push, owner branch mutation, shared Global write or canonical merge occurred.

## Capability and runtime state

Fresh snapshot: **25 open PRs, all Draft;38 remote branches**. The three new review proposals are [audit28](https://github.com/kco994553-star/Investment-System1/pull/28), [existing-Web fixture29](https://github.com/kco994553-star/Investment-System1/pull/29), and combinedtrial30. Existing proposals22–27 retain their exact SHAs and independently audited approved lineage adoption/re-pin evidence.

The [24-entry inventory checkpoint](evidence/final-actions/capability-inventory-checkpoint.json) records each capability's owner, exact HEAD, PR, maturity, Freeze, latest owner Actions/head match, dependency, blocker, next step and three separate states. Routing/serialization qualifications are appended in [the addendum](TAKEOVER_ROUTING_AND_INVARIANCE_ADDENDUM.md).

No overall percentage is calculated without an approved completion denominator. No capability maturity is promoted by test count or a Draft trial. TrackA is canonically integrated; TrackB P0 implemented/frozen; TrackC C0–C7 SOFTWARE_FROZEN with C8 NOT_FROZEN; QGV/Leaderboard research-data and Entity display-metadata verification retain their bounded prior stages; most producers/Web remain SYNTHETIC_VERIFIED. No operational capability completion is claimed. QGV/Leaderboard persisted research does not mean fully scored investment output.

`LOCAL_GIT`, `WORKSPACE_WRITE`, `COMMIT_LOCAL`, `REMOTE_READ`, `NETWORK_GITHUB`, `REMOTE_WRITE`, `BRANCH_CREATE`, `PR_CREATE`, `PR_UPDATE`, `ACTIONS_READ` and `ACTIONS_DISPATCH` were actually exercised successfully. Git transport `PUSH` remains `BLOCKED_HTTP401`; it was not retried. Authenticated Git object API publication preserves exact local commit SHAs and only creates/fast-forwards this worker's proposal branches. Thus `REMOTE_WRITE_BLOCKED` does not apply to the runtime as a whole. Sandbox is `workspace-write`; effective approval is `auto_review`, not `never`; additional sandbox network permission is supported. This result establishes the present session's capability and cannot establish another chat runtime's permissions.

| State | Actual outcome |
|---|---|
| BRANCH_STATE | exact86ad published; eight current Actions SUCCESS |
| INTEGRATION_STATE | history-preserving combined trial verified; owner proposals remain Draft/read-only |
| CANONICAL_STATE | NOT_MERGED; canonicalb8 unchanged |
| Maturity before→after | unchanged; integration readiness verified |
| USER_DECISION_REQUIRED | YES, next TrackC method/source-identity software cycle |

## Decision boundary and next handoff

The current critical path is C8 authoritative method/source identity → remaining approved adoption and combined acceptance → QGV/Leaderboard and Technical/US/Macro real/PIT paths → Producer/Web/P01 → Portfolio/daily operation. Calculation, validation, publication and canonical acceptance remain distinct.

Two concrete pending decisions have reviewable evidence in audit28: (1) authoritative G-SUP convention K/M/C; the same approved example yields p0.10 versus p0.15, and v1 has not been overwritten; (2) the proposed trusted source/sample descriptor for one-shot enforcement, synthetic scope only. New statistical configuration, real CAL_VERIFY first access, Holdout consumption, grants, Official/LIVE, paid provider, canonical merge and deployment remain separate unapproved gates. No answer was inferred from elapsed time.

This cycle's independent approved READY compatibility/fixture/CI/evidence work is complete. The next software change requires the outstanding decisions under the user's §14 and Worker Contract PR21 §D.15. Suggested next allocation after an answer: one TrackC implementation writer, one independent oracle/authority reviewer, and a scoped producer/Web validation worker where publication contracts allow work; worker count follows dependencies rather than a fixed model/count requirement.

Primary Integration Writer may append these exact receipts to Global Handoff. The existing designation remains authoritative. Dynamic Workflow remains SOFTWARE_FROZEN with no new feature or mandatory model tier.
