Investment-System1 · CURRENT_HANDOFF

Timestamp: 2026-09-27 19:56 KST
AI: Codex
Scope: Track A only. Other-track sections below are carried unchanged from the prior handoff and are not current Track A assertions.
Repository base: ebf8263e925b657f38463988ba85eb3ce2d7bb51, canonical claude/investment-system-top500-validation-alrugm.
Working branch: fix/track-a-dated-walk-forward. Local changes NOT UPLOADED: GitHub write integration returned HTTP 403.
Handoff Status: BLOCKED / NOT FROZEN — D3-P CA-UNIT-v1.0 pending (C-41).

Track A — REAL-DATA Main Track
Run #70 completed GRAL's actual first-subsequent 2024-08-13 10-Q correction and declared all three dates Official.
That workflow ran the 3-date path, but its old union-of-listings replay replaced historical BLK CIK 0001364742 with
successor 0002012383. C-40 is fixed: dated inputs per slice, snapshot metadata overrides static listings, and a
single-vs-walk-forward consistency guard. Actual BLK replay and full 500-name diagnostic replay pass after the fix.

The independent share/price-unit audit now detects 20 unreconciled candidate events: 4 on 06-30, 8 on 09-30, 8 on 12-31.
All three gate chains were re-executed against verified run-70 raw data. Existing Promotion Gate v2 and internal snapshot
consistency pass, but final official_top500_declared is false with UNRECONCILED_SHARE_PRICE_UNITS. Thus all prior Official
snapshots/results are SUSPENDED under C-41. Current pipeline correctly blocks Official walk-forward. Do not restore any
Official claim solely because old gates or the workflow were green. Old snapshots remain immutable historical evidence.

Raw integrity: 6,808 artifacts / 6,136,954,924 bytes, hashes and sizes PASS. Memory-bounded replay avoids the observed
exit-137 failure; diagnostic peak 363.1 MiB. Three historical 500-name rosters were replayed as RESEARCH ONLY: selected 471/469/468,
0 name errors; 2 adjacent-date walk-forward steps match their singles exactly. Network-inclusive performance remains
unverified; prior ~28-second figures are cached replay. SEC/Yahoo connectivity succeeded in this session.

Next action: review the concrete D3-P proposal at implementation/reports/gate_evidence/track_a_share_unit_policy_proposal_2026-09-27.md.
After approval, apply result-independent classified share-unit rules with primary evidence, then corrected Gate -> Official
consistency -> Official single_as_of/3-date walk-forward -> actual network-inclusive 500 benchmark -> PIT/provenance/regression
and Freeze audit. No policy waiver, guessed shares, or automatic Yahoo multiplier was applied. No new API key is needed
for the completed work. Detailed status: Investment-System1 · TRACK_A_REAL_DATA_STATUS.md.

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

Track A regression this round: 388/388 PASS (mini_pytest shim); focused 113/113 PASS before the memory regression was added. Full final log is implementation/reports/track_a_regression_2026-09-27.txt.

RIG / News — `RIG_NEWS_ARCH_v0.1` is registered as
`Investment-System1 · RIG News Architecture v0.1.md`. Status is DESIGN FROZEN / IMPLEMENTATION NOT STARTED; P0–P5
are NOT_STARTED. Repository audit confirmed that existing DataEvent NEWS handling is evidence-only, future-available
events are deferred, Frontend IA uses Summary→Evidence→Detail, and the Global/Korea contract already defines shared
NewsItem→Claim→Event and Feed/Network identity. No RIG code, store, UI, notification runtime, score, or test was added.
`yahoo_events__*` is split-event market-data provenance, not news. C-39 is now RESOLVED: the common Global/Korea
`IssuerIdentity -> SecurityIdentity -> ListingIdentity`, independent Analysis/Network/News contexts, and fail-closed
FX/eligibility PIT contracts are implemented in `contracts/global_universe.py` with six regressions. Track B's frozen
private identity implementation was not imported or changed. RIG remains DESIGN FROZEN / IMPLEMENTATION NOT STARTED.

Repository delivery: latest fetched canonical ebf8263; local Track A commits pending upload because the integration returned 403. See Track A status and package.
