# Inactive G/C dependency-scope fixture handoff

**PASS — bounded D1/D2 fixture acceptance only; bounded closure count: 1.** Runtime remains disabled;
semantic validity and consumer admission remain NOT_EVALUATED. Production domain
blockers closed: **0**. Scheduler hops added: **0**.

The final probe ran **30/30 targeted STANDARD checks**, with **0 failures**.
The first run also passed 30/30; `ATTEMPT_01_RESULTS.json` is retained. The final
run after compacting the output and making G2 factor scope explicit is retained
in `ATTEMPT_02_RESULTS.json` and `SCOPE_VERIFICATION.json`. No failed attempt was
discarded. The previous G 21 and C 38 assertions were consumed by exact hashes;
their mains were not executed or rewritten.

Root independently reproduced the final CLI at **30/30**, with identical cases
and byte-identical `INPUT_PINS.json`, `SCOPE_FIXTURE_SPEC.json` and
`SCOPE_FIXTURE_DIGESTS.json`; its receipt is `ROOT_VERIFICATION.json`.

Executed from `/workspace/scratch/5f9c0923784f`:

```sh
python qgv-autonomous-loop/scope/dependency_scope_probe.py --semantic-dir qgv-semantic-lanes-output --pin-manifest qgv-autonomous-loop/scope/FROZEN_INPUT_PINS.json --output-dir qgv-autonomous-loop/scope
```

The portable equivalent, from the repository's architecture review directory:

```sh
python lanes/execution_loop/scope/dependency_scope_probe.py --semantic-dir lanes/semantic --pin-manifest lanes/execution_loop/scope/FROZEN_INPUT_PINS.json --output-dir /tmp/qgv-scope-reproduction
```

All **29** inputs match authenticated review HEAD
`19e4e47d3f8fc02fb35d33399f7b052317896b62` before and after execution.
`FROZEN_INPUT_PINS.json` contains repository-relative paths and exact Git/SHA256
pins, with no scratch paths. The checker imports frozen `C.validate` and
`C.preserve_zero_profile_authority`. It does not execute `C.main`, `G.main`, a
scorer, ranker, JSONSchema engine, runtime producer or policy engine.

| Supplied fixture reason | Exact declared affected scope | Unrelated scope |
|---|---|---|
| Local METHOD_MISMATCH | G representative G2 factor `eps_fcf_per_share_growth` | Q/V receive no rejection; G1 descriptors remain UNASSESSED evidence |
| Shared synthetic PIT rejection | Declared Q fixture factor and G representative G2 factor | V remains UNASSESSED |
| Combined local and shared reasons | G retains both independent original reasons; Q retains only shared PIT | V remains UNASSESSED |
| Local synthetic V source rejection | Declared V fixture factor | Q/G receive no rejection |

These are supplied fixture markers, not a newly evaluated failure rubric. Q/V
factor scaffolding and the dependency declaration are synthetic; no production
cross-axis dependency inventory is established. The literal 70/READY is the
frozen C synthetic diagnostic, not a genuine Q/G/V result. All eight G candidate
descriptors remain UNASSESSED, methods unselected, and outputs UNCOMPUTED. Actual
G/C byte hashes are evidence attachments, never genuine raw inputs or PIT proof.

Bounded gaps closed: exact local/shared reason carriage from producer through
aggregate to consumer; exact declared dependency relevance; coherently rehashed
scope/attachment drift rejection; zero/profile obligation preservation; retained
rejection reasons; and no ranking promotion from structural acceptance. Every
negative is limited to these relationships. There is no general aggregate,
withholding, arithmetic, completeness, confidence or consumer-admission method.

Publish the script, frozen pins, `INPUT_PINS.json`, compact
`SCOPE_FIXTURE_SPEC.json`, `SCOPE_FIXTURE_DIGESTS.json`, final verification and
attempt receipts. The complete carriers/reference DAG are deterministically
generated in memory and identified by canonical digests. Obsolete repeated
`SCOPE_FIXTURES.json` and `SCOPE_REFERENCE_CONTENTS.json` are not current outputs.
Byte-compare the compact outputs on reproduction; verification's command and
attempt number reflect its invocation.

| Current artifact | SHA256 |
|---|---|
| Probe | `80bbd7f2fae59de7d5996c67842e04386cb6243d4196f953639de937d622f045` |
| Frozen input pins | `2e723b62b798e5e2be7f2136e6e772dc595ecb105f3b070774fde0f6198ec53e` |
| Compact fixture spec | `741b3b99ea490ca27fc9a78bf80f922152e2e3eba2fbf6f91ad29a153b963c02` |
| Generated fixture digests | `e480d35a86a0f4cee84d618b72533448f0ce99511791b92ac08df320b66ad8ac` |
| Final verification | `682ea9675a66f1af90b4a0f07f8e4fc510f69e0af4dbbef48651a5ab892a44cd` |

Genuine source requests DATA-G-01–05 and authority request AUTH-G-06 remain open.
This lane restored no archived bytes and performed no genuine PIT/OOS replay.
Root's finite archive-download retry returned 502 twice; archive restoration is
`WAIT_DEPENDENCY_TOOL_TRANSPORT`, not established source availability.
Remaining D3 concerns are the concrete G1/G2 method/input/window/domain/
normalization and branch selection, B2/B3/B5/B6 actual criteria and consumer/
migration/activation authority, B1 requirements, and pending V1/V2 methodology.
No new research question or decision ID is introduced. The fixture lane stops
here; CONTROL, CURRENT_HANDOFF, Global, owner branches and scheduler are untouched.
