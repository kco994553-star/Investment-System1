# Independent synthetic G-SUP source identity review

The four approved source-identity review criteria are complete within the bounded
trusted-coordinator synthetic software model. This is not approval of an M-B v2
arithmetic convention, real calibration, Holdout consumption, publication or
Official promotion. The engine tested here explicitly retains v1 statistics for
source-identity compatibility validation.

Approval base: `8230007f5edb86aec949166e25fd62a680db3ae2`.
Executed immutable integration source: `d9a8cffd5339312264ba40c497163ed9544fb27c`.
Source protocol implementation commit: `0b8b3ad3d3538d9ad224858acbd452d7b193423a`.
Independent test branch: `codex/gsup-v2-identity-adversarial-2026-10-03`.
The independent branch adds tests and this evidence only; its base implementation
does not contain the new source modules. The run imports the exact integration
source through explicit PYTHONPATH and disables the independent branch conftest
to prevent accidentally testing its older source.

| Review criterion | Actual evidence | Status |
| --- | --- | --- |
| Trusted source/vintage/sample resolution before outcome access | Missing or incomplete descriptors, copied/fresh authority substitutions, descriptor changes after resolution, missing feasibility and undeclared/non-synthetic providers have zero spy reads. An authentic claim belonging to another descriptor with the same exact registration digest is rejected before access. | COMPLETE_SYNTHETIC |
| Repeat attempts blocked before another outcome read | Raw integer/float/signed-zero encodings, campaign/role-id/label/local-root changes, one shared sample, concurrent overlapping claims, process death, incomplete durable intent/journal, provider interruption, infeasible verdict and Development gate failure retain reservations and block another read. | COMPLETE_SYNTHETIC |
| Existing grouping and numerical/foundation isolation | Disjoint samples and existing CHAMPION/CHALLENGER and Balanced/Defensive groups remain independent. Identity validation returns the same numerical objects without conversion/reduction. Compatibility result retains v1 method and no Official grant. Exact byte guards pass for four original source files. | COMPLETE_SYNTHETIC |
| Preservation and independent receipt | Owned 48 tests executed against the immutable integration commit with Python 3.11.16; 48 passed, zero failures/errors/skips. All 8,088 original files on the independent branch remain unchanged. Machine receipt and unmodified JUnit evidence accompany this review. | COMPLETE_SYNTHETIC |

Executed command:

```text
PYTHONPATH=/workspace/gsup-v2-integration/implementation/src:/workspace/gsup-v2-integration/implementation /workspace/validation-venv311/bin/python -m pytest --noconftest -q /workspace/gsup-identity-adversarial/implementation/tests/test_evl_gsup_v2_identity_adversarial.py --junitxml=/workspace/takeover-evidence/track_c/identity-independent/combined-identity-wrapper-fixed.xml
```

The wrapper negatives use an explicitly declared synthetic feasibility gate to
reach identity/access checks; they do not validate feasibility size simulations.
The final access/retry case invokes the unchanged v1 evaluation with an explicit
literal synthetic fixture and retains its original raw-content commitment check.
No numerical default or alternative statistical convention was introduced.

Initial work-in-progress tests found a real implementation defect: the immutable
record helper also created the appendable journal with mode 0444, causing ordinary
workers to fail on append. The source owner corrected only that journal creation
to 0644; the independent direct suite then passed. Read-only review also identified
an authentic wrong-descriptor claim substitution; the wrapper owner added exact
authority/ref/hash/profile/role binding, verified by the independent regression.
An intermediate positive wrapper fixture incorrectly used an unbound raw content
hash; the existing v1 integrity check correctly rejected it. The fixture was
corrected to preregister its literal synthetic cohorts. Failed intermediate JUnit
records remain in the external takeover evidence directory and were not rewritten.

The trusted coordinator pins the authority outside untrusted attempt specifications
and issues truthful immutable descriptors before outcomes. Bootstrap, descriptor
issuance, coordinator configuration replacement and privileged authority deletion
are outside the attempt caller's permissions. This local POSIX protocol is not a
security sandbox against a privileged process, filesystem administrator, lying
trusted descriptor issuer or a provider falsely claiming to be synthetic. It does
not infer equivalence between incorrectly issued source/vintage/sample identities.
No foundation registry migration or unification was performed; unresolved historical
G-SUP records fail closed and remain byte-identical.

BRANCH_STATE: local independent test/evidence branch, ready for normal merge.
INTEGRATION_STATE: synthetic trial verified at the exact source commit above;
the owned tests are awaiting normal merge when this receipt is created.
CANONICAL_STATE: unchanged; not merged.
Actions: NOT_RUN for this identity cycle.
Real CAL_VERIFY / Holdout: NOT_RUN; no provider access was authorized or performed.
Remaining numerical blocker: USER_DECISION_REQUIRED_ARITHMETIC_REDUCTION.
Next autonomous action: normal-merge this additive test/evidence commit into the
integration branch and execute its approved CI validation.
