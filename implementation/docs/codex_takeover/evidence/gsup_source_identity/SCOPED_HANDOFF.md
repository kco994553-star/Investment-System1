# Synthetic G-SUP source identity checkpoint

Source commit: `0b8b3ad3d3538d9ad224858acbd452d7b193423a` on
`codex/gsup-source-identity-2026-10-03`. Base and merge-base:
`8230007f5edb86aec949166e25fd62a680db3ae2`. The current explicit approval
was recorded before implementation; approval JSON Git blob is
`a5279d516c028f0a8cb9166ee2d54366da00877b`.

This is the approved metadata-only, synthetic software identity component.
Maturity advances DESIGN → SYNTHETIC_VERIFIED for this component in its branch.
SOFTWARE_FROZEN is false; parent integration and combined validation are separate.
Canonical state is NOT_INCLUDED. Actual CAL_VERIFY, Holdout, real source taxonomy,
numeric configuration, foundation registry unification, Freeze and grants remain
unapproved. Authoritative M-v2 arithmetic reduction is a separate unresolved
decision and this component neither selects nor activates a statistical kernel.

## Trust boundary and replay protection

The synthetic fixture coordinator calls explicit bootstrap and descriptor issuance.
It pins `SourceAnchor` plus `expected_authority_ref` outside untrusted attempt
specifications. Normal resolution opens an existing complete authority; it never
creates a missing store. The reference commits the absolute root, coordinator
identity, timestamp, approval blob and explicit historical registry path. A copied
store or valid fresh bootstrap at another root cannot substitute for this pin.

The descriptor contains source/vintage, explicit ordered period/sample identities,
the unchanged profile/role and designated role identity, all four existing cohorts
and both existing controls. It admits no outcomes or unknown fields. Source and
sample identity correctness is a trusted fixture-coordinator assertion: the module
does not infer aliases from numeric content, issue a real taxonomy or validate
actual external data sources. Provider metadata must match the issued descriptor
exactly, including ordered sample/period alignment; existing parent raw-content
commitment checks remain necessary to detect changed or reordered numerical arrays.

Consumption keys use source/vintage/sample qualified by the existing profile and
role. Campaign, local attempt root, dataset label, role label and raw number
encoding are excluded. Any overlapping key rejects the whole new reservation.
Disjoint samples and the existing different profile/role groups remain allowed.
The parent must reserve before feasibility estimation/verdict, even if that verdict
is infeasible or estimation crashes. A reservation has no release operation.

One authority lock serializes the full sample-set reservation. Exclusive immutable
intent is fsynced before the journal append; the append and directory are fsynced
before admission returns. Unmatched/partial intents, missing/torn journals or an
invalid hash chain fail closed across restart. An exclusive access record is
fsynced before provider invocation and cannot be retried. Filesystem journaling
and POSIX `flock` are required. Descriptor changes are rechecked at resolution,
claim, access and response validation.

Any nonempty opaque historical G-SUP registry, including pending registration or
partial files, closes admission globally as unresolved. No historical result is
rewritten, migrated to the foundation registry or inferred to mean unseen samples.
The coordinator may provision an explicitly empty **synthetic fixture** historical
directory, but attempts cannot choose another historical store after the authority
is pinned.

Privileged deletion/rewriting of authority files, arbitrary descriptor issuance by
a malicious coordinator and replacement of the externally pinned trust
configuration are outside this compliant-worker protocol's threat model. Local
POSIX records cannot prove protection against an administrator deliberately
resetting both storage and trust. The tests distinguish fresh-root substitution
against an existing pin from a privileged reset of that pin.

## Validation actually executed

True CPython 3.11.16, native pytest 9.1.1:

`PYTHONPATH=implementation/src /workspace/validation-venv311/bin/python -m pytest -q implementation/tests/test_evl_gsup_source_identity.py implementation/tests/test_evl_c8_gsup.py`

117 PASS in 12.97s: 33 new protocol cases and 84 unchanged existing G-SUP cases.
Coverage includes full alignment, outcome/real/incomplete rejection, immutable
resolution, fresh/copy authority substitution, alias/reencoding replay, partial
overlap, preserved groups, cross-process concurrency, pre-access crash/infeasible
consumption, fsync failure, interrupted journal/intents, descriptor TOCTOU,
historical opaque records, provider ordering and exact synthetic legacy numerical
input/result invariance. The identity validator returns the same numerical object
without coercion or recalculation.

The first local run exposed 13 failures from the append journal's incorrect
read-only mode. Independent review also found this. The journal now has mode0644
and is written only with O_APPEND under the authority lock; immutable descriptor,
intent, access and manifest records remain mode0444. Final targeted validation
passed. The separate reviewer reports 38 direct adversarial PASS; their execution
and evidence belong to their own branch and are not relabeled as this worker's
validation.

Every baseline tracked file was compared byte-for-byte; no existing source,
test, decision, approval, Frozen record or history changed. The only code/test
changes are two new owned files. Exact hashes and baseline file count are in
`CHECKPOINT.json`; actual stdout is `targeted-python311.log`.

Actions, this worker's full combined suite, push, canonical merge and real-data
access: NOT_RUN. The next autonomous action is parent history-preserving normal
integration, wrapper adversarial regression and actual combined Actions evidence.
No new USER_DECISION_REQUIRED exists within the approved synthetic identity scope.
