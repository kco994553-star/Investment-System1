# Track C G-SUP source/sample identity repair proposal

Status: **PROPOSED / NOT_APPROVED / NOT_ACTIVE**. This document is evidence and a
reviewable design only. No source, test, owner branch, Frozen blob or registry was
modified. No real CAL_VERIFY or Holdout was accessed.

Subject: `ccr-22e3ff16-p7n5k5` at
`b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565`,
`implementation/src/investment_system/evl/superiority.py`.

## Reproduced gap and existing authority

CDR-005 and approved A6-S4/Q4 prohibit relabel/retest. The current G-SUP access key
is `(verify_content_hash, profile, role)`. `verify_content_hash` is a hash of raw
cohort JSON. In the independent synthetic probe, `[2.0, 3.0, ...]` versus
`[2, 3, ...]`, and zero controls encoded as `0.0` versus `0`, are identical
numerical observations and produce identical eight-cell statistics. The raw
commitments differ. Both were admitted for the same dataset ID/profile/role and
shared registry, each returning `STAT_PASS`.

This is an additional representation weakness in the one-shot policy, not a new
statistical method. The final decision remained
`NOT_RUN_EFFECT_FLOOR_DEFERRED`; no Official/research permission was created.

## Why the audit did not apply a partial patch

Current preregistration exposes only a caller-supplied dataset label and an
opaque raw-content digest. It has no authoritative source/vintage/sample
resolver. The digest cannot reveal the underlying observations before access.

- Adding a durable alias key on dataset ID blocks the exact same-ID probe, but a
  simultaneous relabel plus equivalent reencoding still bypasses it.
- Normalizing observations after the provider returns detects a replay after
  the second read has already consumed the supposedly one-shot source.
- Treating a new caller-provided semantic hash as authoritative repeats the
  original trust issue unless a registered source resolver independently binds
  it before access.

A robust pre-access fix therefore needs scoped owner authority for source
identity resolution. No invented source identity or numeric-equivalence
convention was implemented here.

## Concrete proposed contract

1. Add a separately versioned **source-identity protocol** to G-SUP, retaining
   the existing statistical kernel/version, all historical registrations and
   evidence. Do not repurpose an old method SHA or registry key.
2. Preregister an immutable `verify_source_registration_ref` plus descriptor
   hash. The reference must resolve through an approved source registry before
   any outcome-provider call, rather than accepting a claimed lineage label.
3. The resolved descriptor must include authoritative `source_id`, `vintage`,
   stable ordered `sample_id`s, registered periods, and explicit cohort/control/
   role alignment. It must contain identity and lineage metadata only; resolver
   admission must not read target outcome values.
4. Reuse the existing foundation precedent for stable outcome identity:
   `digest([source_id, vintage, sample_id])` from
   `calibration_ledger.AccessRegistry.keys`. Preserve the current G-SUP
   profile/role consumption grouping unless a separate scoped decision changes
   it. Dataset labels and raw JSON numeric representation are excluded from
   the stable identity key. Keep raw-content commitments as additional
   immutable response-integrity evidence.
5. Claim the resolved stable identities exclusively and durably before the
   provider call. Existing verdict/access/result records remain charged and
   retained across crash, campaign changes, relabeling, and registry roots.
6. Bind the returned values to the exact preregistered sample alignment and raw
   commitment. Missing or unresolved source identity yields
   `NOT_RUN_MISSING_SOURCE_IDENTITY`; mismatched identity yields integrity
   failure. Never infer source IDs from labels, array position alone, or
   fabricated timestamps.
7. Historical registrations lacking source/sample identity remain historical;
   they cannot be retroactively mapped or claimed equivalent without explicit
   source evidence. An unresolved historical access record must fail closed
   under the new protocol.

Synthetic acceptance should cover equivalent int/float representations and
negative zero, label/campaign changes, overlapping stable sample sets,
provider mismatch, unresolved descriptors, failure/crash, concurrency and
preservation of the declared profile/role scope. No observed outcome is used to
choose identity or policy.

## Impact and authority still required

- Numerical/statistical outputs for a single authorized assessment should be
  byte/semantically invariant in all existing fields; independent before/after
  comparison is required before any implementation can be called compatible.
- Duplicate attempts on the same resolved observations would be rejected before
  target reads even when serialization or labels differ.
- Real source registry authority, real CAL_VERIFY admission, numeric calibration,
  G-SUP vs foundation unified consumption, and publication remain closed.
- This proposal does **not** decide whether G-SUP and the foundation must share
  one physical transaction, or change the permitted Champion/Challenger grouping.
  The current separate-registry limitation remains separately disclosed.

Decision question for the scoped owner/user: may the G-SUP synthetic protocol
adopt the foundation's source/vintage/sample identity precedent through a
current-resolving source descriptor while preserving its existing profile/role
grouping, or does the authority require a single foundation/G-SUP access
transaction? No option has been selected.
