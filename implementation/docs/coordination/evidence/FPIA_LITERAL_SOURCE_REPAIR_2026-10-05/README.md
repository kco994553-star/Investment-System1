# FPIA fix3 literal-source successor repair · 2026-10-05

Status: LOCAL_REPAIR_VERIFIED / INDEPENDENT_BOUNDED_REVIEW_APPROVE. Remote publication is coordinated by the successor Main. This record does not grant canonical merge, Frozen changes, Holdout access, production semantics, or FPIA governance adoption.

Base: `11d2f25ef8bef3459ca969f50eec190099f15ecb` (PR #42 fix3).
Branch: `codex/fpia-fix3-literal-repair-2026-10-05`.
Only FPIA source, its regression tests and this additive evidence directory change.

## Finding and repair

The fix3 mention scanner missed literal executable source files when their names lacked a code suffix or contained spaces. Examples: `bash ci/commands.txt`, `python ci/commands.txt`, `bash "ci/run commands.sh"`, and a nested shell invocation of a `.txt` script. The files contained a literal Track C tool invocation. The existing resolver followed them correctly, but fix3 discarded that positive source reachability as evidence-only. These are literal commands, not a request to claim detection of arbitrary dynamic invocations.

The repair seeds the mention scan with the resolver's positively resolved literal source files. The original mention scanner still runs and its existing detections cannot be removed by a resolver miss. Resolver reasons remain evidence; the mention scanner decides the finding. Filename extension is no longer used to exclude a file already resolved as executable source. Existing verifier self-placement and authenticated V attribution checks remain active. Reading a `.txt` file with `cat` remains a benign control.

Explicit `jobs.<job>.container` (scalar or image mapping) and `jobs.<job>.services.<service>.image` were also absent from external-reference evidence. They are now recorded with their declaration kind and source job/service. An action's arbitrary `with.image` input is not inferred to be a container. The external-code status remains `NOT_ANALYSED`; no external code is fetched, executed, inspected or declared safe by this repair. Installed packages, arbitrary downloaded code and all dynamic source reachability remain outside this bounded repair.

## Evidence

| Check | Result | Meaning |
|---|---|---|
| Original fix3 suite on base HEAD | 234 PASS | Existing suite did not expose these counterexamples |
| New regressions before source repair | 7 FAIL, 4 PASS | Four literal-source misses, three missing image records; four normal controls |
| Fix2 + fix3 + new regressions after repair | 308 PASS, 2 DESELECTED | Affected regression run; not a full repository suite |
| Added aggregate end-to-end regression | 1 PASS | Separate run after adding the aggregate assertion |
| Independent reviewer additional cases | 10 PASS | Working-directory, quoted/nested/source invocations, benign data, dynamic non-claim controls, alias/service/reusable image evidence; bounded approval only |
| FPIA self constraints | 7 PASS | No new numeric/default/SHA exceptions, no Track C imports, clean self-placement and workflow contract |
| Exact same synthetic tree and register, original verifier | FPIA_PASS / INTEGRATION_INTERFERENCE_NONE | False negative reproduced with extracted base sources |
| Exact same synthetic tree and register, repaired verifier | FPIA_FAIL / AC-32.spoof | Runtime provenance and full synthetic regression still PASS |

The two deselections are `test_symlinked_venv_tmpdir_and_user_give_same_verdict_and_sha` and `test_result_sha256_independent_of_venv_location`. This repair does not touch interpreter/environment handling. The first was included in the original 234-pass fix3 baseline. The second is a fix2 environment test and was not independently rerun here. Do not combine the baseline and affected counts into a claim of all-tests-on-final-HEAD.

Local runtime: Python 3.12.14, pytest 9.1.1, numpy 2.3.5, isolated venv. Existing GitHub workflow uses Python 3.11; CI runtime equivalence is not claimed.

Aggregate comparison uses synthetic T `e6fde4628c1154e5ff840729949daa5ff8284faf` and G `d2ccd9252f3680b4828fe13648f8a45f1d3dc88c` on both runs. `CODE_IDENTITY_DIVERGED`, verbatim `FROZEN_TOOLS_ON_T_FAIL`, historical Frozen preservation and projection preservation remain distinct in both outputs. The fixture's full regression PASS is not the repository's full real-history regression.

`prior_head_ci_snapshot.json` fresh-read at 2026-10-05 13:42:36 KST confirms original-head run 37260997788 attempt 1 completed success at 13:41:34 KST. Its Tier 1 and Tier 2 steps were skipped on the PR event; it therefore does not establish those regressions or fix3 governance closure. No duplicate CI was started.

An initial aggregate baseline extraction used a path relative to the implementation directory and failed. The first supposed baseline run consequently imported the repaired verifier. Its output is preserved as `excluded_initial_wrong_source.json` and is excluded from the comparison. The extraction was corrected with an explicit repository root, the probe now asserts the requested verifier source path, and `aggregate_before.json` is the valid base-source run. No earlier result was silently treated as correct.

Raw logs, output JSON and probes are adjacent. `summary.json` pins their SHA-256 values. Probe scripts preserve the local paths used in this run; change their workspace path when reproducing elsewhere. The checked-in tests provide the portable regression cases.

## Authority and unfinished decision round

These are recommendations for Main's append-only decision record, not decisions issued by this repair worker. The remote PIW decision file contained rules only; no a–e/G7 entry was recovered. Global GIE-014 was absent from the inspected tree. CDR-015 alone must not override the later CDR-016/017 restrictions.

| Old label | Permitted next work | Boundary that remains |
|---|---|---|
| D3-a verifier identity | Main D2: establish exact trusted verifier commit/blob requirements and verify an independently reviewed candidate; keep its identity separate from subject T | PR-head self-report and output hashes alone are not authentication; canonical adoption remains a distinct restricted action |
| D3-b job-id collision | Main D2: record a reasoned generic-id note policy or design a stronger compound-identity rule with normal controls | No blanket assumption that common job IDs authenticate Track C; no silent alteration of protected owner contracts |
| D3-c dynamic invocation | D1/D2: repair literal-source gaps and disclose static-analysis limitations; treat unverified claims as unresolved | `NOT_FOUND` is not a proof about arbitrary constructed execution; no safety claim or Frozen acceptance reinterpretation |
| D3-d importer attribution | D1 routing to #28/Codex/Track C owner for exact-source provenance and scope; D2 verify a received attestation | Do not manufacture attribution or modify another owner's protected contract |
| D3-e external code | D1/D2: enumerate actual external inputs and require appropriate provenance/inspection evidence for the intended certification scope | `NOT_ANALYSED` cannot become safe by assumption; paid/credential/production activation restrictions still apply |
| G7 subject/trigger scope | Main D2: document dispatch versus PR coverage and actual R ancestry; distinguish non-candidate skipped coverage from audited FAIL | Branch-prefix filtering is a scheduling heuristic, not evidence that R exists; pre-R audited trees must not be relabelled PASS |

The literal source false negative blocks treating the old fix3 verdict as complete. This bounded successor removes the demonstrated defect; it does not finish verifier authentication, dynamic-execution coverage, importer attribution, external-code certification or canonical adoption. Revert/supersede this additive repair commit if needed; previous fix3/history/evidence are retained.
