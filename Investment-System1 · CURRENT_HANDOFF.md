Investment-System1 · CURRENT_HANDOFF

Timestamp: 2026-09-27T20:50:49.316653+09:00
AI: Codex
Scope: Track A only. Other-track sections below are historical carry-forward, not current Track A assertions.
Validated source: 682bbae1687d237f72c3f2266913b8bf61f1ff0b
Canonical base: ebf8263e925b657f38463988ba85eb3ce2d7bb51
Handoff Status: Track A REAL-DATA Baseline FROZEN (local commit/package); GitHub NOT UPLOADED, prior 403.

Track A — REAL-DATA Main Track
CA-UNIT-v1.0 approved by the user and implemented as general primary-evidenced share/price unit reconciliation.
Original20 and additional3 D3-C cases resolved. All candidates 992/990/987 audited; CA applications 6/7/9.
Corrected Gate -> exact Official consistency -> three real singles -> 3-date/two-step Walk-Forward -> PIT/provenance/regression: PASS.
Each date has 500 unique issuer CIKs. Selected/linked 471/469/468, zero name errors. Singles and WF match exactly.
Network-inclusive500: 2000 actual requests, 1986 OK/14 historical fallback404; 1983 fresh payloads replayed, 569.576s, peak733.984MiB.
Raw6830 SHA/size PASS; regression396/396 PASS. Fixed-vintage baseline and fresh benchmark separately retained.
Source-run70 is a seed, not the final corrected execution. No new GitHub workflow success is claimed.
Final evidence: implementation/reports/gate_evidence/track_a_freeze_readiness_2026-09-27.json.
No new D3-P. STOP under user instruction; do not start B/C/D/E. See TRACK_A_REAL_DATA_STATUS for boundaries.

Track B — Personal Investment Layer v1: Architecture FROZEN; P0 Common Contracts implemented and FROZEN
(src/investment_system/personal/, 10 package files, 13 tests). P1+ NOT STARTED; no live broker/integration. Track B code
has no Track A imports and Track A has no reverse runtime imports into personal/. C-24, C-25, C-28, C-29, C-30, C-33
remain explicit upstream/contract items; none was resolved by inference. All Official tracks remain Pre-Tax.

Track C — Experiment & Validation Layer: `EVL_SPEC_v0.1` is registered as
`Investment-System1 · Experiment & Validation Layer Specification v0.1.md`. Status is DESIGN FROZEN /
IMPLEMENTATION NOT STARTED. Track C owns PIT experiments, validation, and Official Aggressive/Balanced/Defensive profile
promotion; Track B is a consumer. Core scores, Official/Custom isolation, Trial Ledger completeness, Final Holdout
isolation, invalidation propagation, tax exclusion, and fail-closed uncertainty are locked. C0 implementation must not
start until Track A REAL-DATA baseline Freeze; current Track A is not frozen because 2024-06-30 is NOT OFFICIAL.

Track A regression this round: 396/396 PASS; final log implementation/reports/track_a_regression_2026-09-27.txt.

RIG / News — `RIG_NEWS_ARCH_v0.1` is registered as
`Investment-System1 · RIG News Architecture v0.1.md`. Status is DESIGN FROZEN / IMPLEMENTATION NOT STARTED; P0–P5
are NOT_STARTED. Repository audit confirmed that existing DataEvent NEWS handling is evidence-only, future-available
events are deferred, Frontend IA uses Summary→Evidence→Detail, and the Global/Korea contract already defines shared
NewsItem→Claim→Event and Feed/Network identity. No RIG code, store, UI, notification runtime, score, or test was added.
`yahoo_events__*` is split-event market-data provenance, not news. C-39 is now RESOLVED: the common Global/Korea
`IssuerIdentity -> SecurityIdentity -> ListingIdentity`, independent Analysis/Network/News contexts, and fail-closed
FX/eligibility PIT contracts are implemented in `contracts/global_universe.py` with six regressions. Track B's frozen
private identity implementation was not imported or changed. RIG remains DESIGN FROZEN / IMPLEMENTATION NOT STARTED.

Repository delivery: Track A FROZEN locally; GitHub upload remains blocked by prior HTTP 403. See Track A status and delivery package.


## Integration verification · 2026-09-28 20:23 KST

Track A — REAL-DATA BASELINE **FROZEN_VERIFIED**. PR #3 was normal-merged into canonical as `bd6bf42bdd9c6274b595471c65e3482f37317f9c`, preserving original Frozen HEAD `a79642f7aa174cc37b981298d0ff1cec6b04e974`. Integration audit re-confirmed the 17-file Freeze evidence manifest, raw 6,830-artifact integrity, CA-UNIT-v1.0 (original 20 + 3 D3-C), exact three-date Gate/Official consistency, 3-date/two-step Walk-Forward, the approved retrospective PIT/provenance boundary, retained Network500 evidence, and 396/396 full regression. This status does not promote `PROVISIONAL_RESEARCH`, claim strict zero-lookahead, or alter Tracks B/C/D/E.


## Track C C1 handoff — 2026-09-28T20:42:40+09:00

AI: Codex. Scope: Track C EVL only. This entry supersedes earlier Track C
IMPLEMENTATION NOT STARTED / C0-only status; other-track records are unchanged.
Started from canonical b8e39a2 and feature/track-c-evl 27bd69d, PR #4 draft.
C0 baseline reproduced: 400/400 pytest PASS. C0 + C1 are now SOFTWARE FROZEN.
C1 implementation 5db4acf: immutable preregistration, experiment-bound append-only
Trial Ledger, corrupt/partial-write containment, serialized writers, budget-aware
supporting evidence, append-only invalidation. Targeted 24/24; full 420/420;
normal-merge integration 420/420 PASS. Actions 36417028774 SUCCESS. Runtime/data
changes outside Track C = 0. No new D3-P for C1. EVL_SPEC_v0.1 unchanged.
Evidence: implementation/reports/track_c_c1_acceptance.md and associated logs/JSON.

Open decision TC-D3P-001: EVL-SPLIT-01 v1.0, C2 chronological Purge/Embargo policy.
The spec requires derivation from horizon/rebalance but leaves boundary semantics
unspecified. Proposal retains 5Y/1Y/1Y nominal windows, removes crossing labels and
adds one registered rebalance interval before evaluation; label end/publication
must precede that cutoff. General policy only; no numeric default or PIT relaxation.
Details: implementation/reports/track_c_c2_split_policy_proposal.md.
Status: PROPOSED / NOT APPROVED / NOT ACTIVE. C2 not frozen; C3–C10 not started.
Next: obtain this D3-P decision, then implement C2 acceptance in existing order.
Do not repeat C1 or alter upstream scores/data/contracts. Do not auto-merge PR #4.
Progress: 2/11 software phases frozen (18.2% phase-count proxy, not effort estimate);
no Official profile, real-data EVL validation or Forward Validation is claimed.


## Track C C2–C3 handoff — 2026-09-28T21:03:11+09:00

Scope: Track C only. This supersedes the earlier C2 approval-pending status.
User approved the revised EVL-SPLIT-01 v1.1 at 2026-09-28 20:48:39 KST. Mandatory
purge is primary; one registered rebalance interval extra gap is a separately
preregistered stress view. The original v1.0 mandatory extra-gap proposal was not
approved and remains historical. TC-D3P-001 is RESOLVED / IMPLEMENTED.

C0–C3 are SOFTWARE FROZEN. C2 targeted 42/42, full and normal-merge integration
438/438; C3 targeted 56/56, full and normal-merge integration 452/452, all real
pytest PASS. Evidence: implementation/reports/track_c_c2_acceptance.md and
track_c_c3_acceptance.md, logs and hash/commit records. No upstream runtime/data
or core-score change; canonical remains b8e39a2. PR #4 remains draft/unmerged.

C4 is BLOCKED_UPSTREAM_CONTRACT; C4–C10 not started. TechnicalSnapshot lacks
input-derived available_at/source-vintage binding (existing C-28); its engine
accepts untimestamped returns. C5 readiness additionally finds six strategy
configurable keys without direct calculation consumers and profile ID/hash used
as metadata only. No Official maturity is inferred from provisional profiles
(existing C-30). Actual audit: track_c_c4_upstream_readiness.json.

EVL_SPEC_v0.1 §13 requires reporting these existing contract gaps, not redefining
upstream modules. Next: upstream Technical PIT lineage + timestamped integrated
evaluator, then C4; behaviorally verified parameter binding is required before C5.
No new D3-P. Do not bypass this with invented timestamps, dummy parameter effects
or a synthetic-as-real result. Do not repeat C2/C3 or auto-merge PR #4.
Progress: 4/11 software phases (36.4% phase-count proxy, not effort percentage).
Real-data EVL validation, Official profile promotion and Forward Validation remain
unverified; software Freeze does not imply any of them.
