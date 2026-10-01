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


## Track C C4 software freeze / C5 scope decision — 2026-09-29

Supersedes the 2026-09-28 C4 BLOCKED_UPSTREAM_CONTRACT status for software implementation.
C0–C4 are SOFTWARE FROZEN. C4 tested implementation `0cb9a7c`; targeted 88/88,
full 484/484, normal merge integration against canonical `b8e39a2` 484/484.
Actual input-derived Technical/Macro availability, source/vintage and digest are
now available through additive stamped evaluators. Legacy decisions and unknown
qualification remain unchanged. C4 enforces registered paired annual rolling /
expanding execution, Train/Validation/OOS isolation, frozen calibration/prediction,
complete terminal accounting, interrupted-attempt recovery and hash-bound reports.

Authorized upstream repair touches four files: contracts/lineage.py (new),
contracts/models.py, technical/engine.py, macro/engine.py. The earlier zero-upstream-
changes statement is historical; QGV, Track A artifacts and B/D/E code remain unchanged.
No qualified seven-year real-data result, skill, Official profile, Holdout consumption
or Forward validation is claimed. TAX_MODE=EXCLUDED; EVL_SPEC_v0.1 is not redesigned.

C5 preflight: cash_buffer and technical_lookback have verified performance effects;
deadband affects order intents only. Three advertised controls have undefined
financial semantics (risk_multiplier, signal_threshold, macro_warning_sensitivity).
TC-D3P-002 proposes explicit first-search coverage of the two functional controls,
with unchanged/fixed stages explicitly recorded and undefined controls rejected.
This is a proposed capability-scope decision, not permission to invent financial
rules. C5–C10 are NOT FROZEN and no C5 search has run. User decision pending.

Evidence: implementation/reports/track_c_c4_acceptance.md,
track_c_c4_evidence.json, track_c_c5_binding_policy_proposal.md.
PR #4 remains draft/open; automatic merge is prohibited.


## Track C C5 software freeze / C6 execution decision — 2026-09-29T19:27:45.256043+09:00

TC-D3P-002 APPROVED by user “어 진행해” at 2026-09-29 19:19:50 KST;
previous proposal-pending entries are historical. C0–C5 now SOFTWARE FROZEN.
C5 implements approved cash_buffer/technical_lookback search with immutable
registration, Train-only input, mandated stage ordering, explicit fixed stages,
coarse/refine over all survivors, increasing resource screening, precision and
complexity rejection, complete budget/terminal accounting and crash recovery.
No peak/champion selected. Actual bound-engine behavior and reproducibility tested.
Targeted 103/103, full 499/499, canonical normal-merge integration 499/499 PASS.
No upstream source change since C4. Prior C4's four-file additive repair remains.

C6 preflight inspected Integration order intents, QGV Simulation compounding and
C3 externally supplied cost fractions. No fill-price/execution-delay contract exists.
New TC-D3P-003 proposes first eligible post-decision opportunity baseline, one
registered opportunity delay stress, explicit execution evidence and fixed-path
1x/2x/3x trading-cost sensitivity; missing evidence fails closed. No fees, fills or
financial behavior were invented. C6–C10 NOT FROZEN, no C6 result is claimed.
Proposal: implementation/reports/track_c_c6_execution_policy_proposal.md.
Approval of TC-D3P-002 does not imply approval of this distinct execution policy.

Evidence: implementation/reports/track_c_c5_acceptance.md and
track_c_c5_evidence.json plus final targeted/full/integration logs.
EVL_SPEC_v0.1 unchanged, TAX_MODE=EXCLUDED, no Official/real 7Y/Holdout/Forward claim.
Progress: 6/11 software phases (54.5% phase-count proxy, not effort or product completion).
PR #4 remains draft/open; no auto merge. Next: TC-D3P-003 decision, then C6 in order.


## Track C C6 execution verification / statistical policy boundary — 2026-09-30 20:00 KST

Track C scope only; historical entries are retained. TC-D3P-003 v1 items 1–8 APPROVED
by the user at actual clock 2026-09-30 19:38:07 KST. Earlier proposal-pending state is superseded.
Approved research execution evaluator implemented at fb1cc7415703142ecd01461fbe1c89e7e2d51c7e; source/tests limited
to evl/execution.py and test_evl_c6_execution.py. Baseline first eligible post-decision slot,
one-slot delay, isolated 1x/2x/3x costs, cash/position/P&L reconciliation, strict execution
provenance, immutable input/report lineage and fail-closed missing evidence are verified.
CI 36705694417 / job 109855289599: real pytest targeted 137/137 (34 new + unchanged C0–C5 103),
full 533/533 PASS. No local Git fetch/pytest or fresh temporary normal-merge replay claimed;
GitHub refs/compare refreshed and fast-forward Git Data commits used.

C0–C5 SOFTWARE FROZEN preserved. C6 IMPLEMENTING / NOT FROZEN:
execution subsection complete, full statistics/perturbation/controls/drift acceptance pending.
New TC-D3P-004 statistical family/resampling policy is PROPOSED / NOT APPROVED / NOT ACTIVE;
no DSR effective-trial assumptions, PBO ranking or bootstrap defaults applied.
C7–C10 NOT STARTED. Holdout UNCONSUMED; no Official/Forward result.
Investor-QGV NOT_IMPLEMENTED / FUTURE_TRACK_C_INPUT; no substitute investor weights.
Track A frozen evidence and B/D/E/Web source unchanged. Prior authorized four-file
additive C4 repair is preserved. EVL_SPEC unchanged; TAX_MODE=EXCLUDED.
Evidence: implementation/reports/track_c_c6_execution_acceptance.md,
track_c_c6_execution_evidence.json, track_c_c6_statistics_policy_proposal.md.
PR #4 must remain Draft/Open/unmerged; NOT_TRACK_C_FREEZE_CANDIDATE.
Next: TC-D3P-004 decision, then complete C6 before starting C7.


## Track C TC-D3P-004 approval / C6 Freeze-policy boundary — 2026-09-30 20:23 KST

Scope: Track C only. TC-D3P-004 option A items 1–8 explicitly APPROVED by the user
at actual clock 2026-09-30 20:16:28 KST. Earlier NOT APPROVED entries are historical.
Approved methods remain complete-family PSR/DSR(two views)/CSCV-PBO/joint circular-block
bootstrap/full-family Reality Check and registered perturbation/controls/drift;
no evidence interpolation or post-selection family shrink.

The user's additional PASS/FAIL/NOT_RUN and mandatory-diagnostic Freeze rule exposed
an unresolved acceptance authority: A6/A8 leave significance/skill decisions to C8,
and neither A nor EVL_SPEC defines the full software Freeze role/status/evidence-scope
matrix. TC-D3P-005 records concrete common all-MANDATORY protocol semantics plus
Option S (complete software-fixture acceptance only) or R (actual complete research
evidence required). PROPOSED / NOT APPROVED / NOT ACTIVE. No advisory waiver or
software/real-evidence scope is silently applied.

C0–C5 SOFTWARE FROZEN preserved. C6 execution subsection VERIFIED; C6 overall
IMPLEMENTING / NOT FROZEN. Statistics/perturbation/controls/drift NOT IMPLEMENTED,
no diagnostic PASS or statistical result claimed. No runtime/test source edit this round.
Latest prior HEAD 34d9c3d actual CI 36706043418: targeted 137/137, full 533/533.
C7–C10 NOT STARTED. Holdout UNCONSUMED; Investor-QGV FUTURE_TRACK_C_INPUT.
Track A frozen artifacts and B/D/E/Web unchanged; authorized upstream repair preserved.
PR #4 remains Draft/Open/unmerged; NOT_TRACK_C_FREEZE_CANDIDATE.
Evidence: track_c_c6_statistics_policy_approved.md,
track_c_c6_freeze_policy_proposal.md, track_c_c6_freeze_policy_audit.json.
Next: TC-D3P-005 role/status/evidence-scope decision, then approved C6 implementation.


## Track C independent statistical kernel verification / approval-record conflict — 2026-09-30T21:13:50.000+09:00

Track C-only overlay; historical/other-track records preserved. C0–C5 remain SOFTWARE FROZEN.
C6 IMPLEMENTING / NOT FROZEN: approved execution unchanged; TC-D3P-004 A kernels now implemented
and tested at `a8e187cea6b117602dff986a3ff6a76b8c244a19`. Actual pytest Actions 36712457163 / job109877255098:
targeted180/180 (C0–C5 103 + execution34 + kernel43), full576/576 PASS, completed21:05:00 KST.
These are SYNTHETIC SOFTWARE TEST results; not a registered complete C6 family diagnostic PASS,
REAL_PIT_VALIDATED, skill, profile selection or promotion. Required family diagnostics explicitly
NOT_RUN in the new kernel evidence; no NOT_RUN counted as PASS. Runner/perturbation/controls/drift pending.

TC-D3P-001..004 approval evidence verified. TC-C6-APPROVAL-RECORD-001: latest task says TC-D3P-005 S
approved, while actual proposal/register/tree remains PROPOSED / NOT APPROVED / NOT ACTIVE and
no approval record or PR discussion exists. User section2 explicitly requires matching repository
evidence and repository precedence on conflict. S not silently activated; no approval time invented.
Concrete additive reconciliation is prepared; no new policy or Track A D3-C case selected.

C7–C10 NOT STARTED; independent interface preflight only. Holdout UNCONSUMED. Investor-QGV remains
NOT_IMPLEMENTED / FUTURE_TRACK_C_INPUT; no saved Research Spec v1.0 or accepted 13F pipeline identified.
Full canonical source diff contains only EVL plus the four pre-existing authorized additive lineage
repairs; those repairs and all frozen C0–C5 source/tests are unchanged this round. Track A frozen
artifacts and QGV/B/D/E/Web source unchanged. PR5/PR6 separate, untouched. No fresh normal-merge
replay claimed; retained C5 103/499/499 evidence preserved with verified remote commit mapping.

Evidence: `implementation/reports/track_c_c6_independent_validation_2026-09-30.md`,
`track_c_c6_statistical_kernels_evidence.json`, `track_c_c6_statistical_kernels_ci_log.txt`,
`track_c_c6_approval_record_reconciliation.md`. PR #4 Draft/Open/unmerged.
Freeze eligibility: NOT_TRACK_C_FREEZE_CANDIDATE; canonical integration NOT READY.
Engineering Progress: **6/11 Frozen = 54.5%**, partial C6 separately reported.
Next: reconcile TC-D3P-005 S approval RECORD under the user's explicit repository consistency
condition; then finish registered mandatory C6 acceptance and verification before C7.


## TC-D3P-005 S explicit approval / record synchronization — 2026-10-01T18:02:42+09:00

TC-D3P-005 common all-MANDATORY classification, distinct PASS/FAIL/NOT_RUN and S —
Synthetic Software Freeze Evidence are **APPROVED / ACTIVE** by explicit user message.
Approval processing time is the actual current KST clock above; no older timestamp invented.
Authoritative record: `implementation/reports/track_c_c6_freeze_policy_approved.md`,
bound to original proposal blob `bbd3321e9966957e862199622ca53f5a4b3ec556`.
Historical proposal/evidence/status records are retained and superseded, not rewritten.
TC-C6-APPROVAL-RECORD-001 **RESOLVED**. No new policy design or D3-P required for this sync.

All 17 enumerated C6 diagnostic groups MANDATORY, no advisory exemption; any FAIL/NOT_RUN
blocks C6 acceptance/Freeze. Complete deterministic explicit SYNTHETIC fixture family
all-PASS may support software-only Freeze, separately labeled SYNTHETIC_SOFTWARE_VALIDATION.
REAL_PIT_RESEARCH_VALIDATION remains separate; no alpha/skill/significance/Holdout/Forward/
promotion readiness follows from synthetic PASS. C8 significance responsibility unchanged.

C0–C5 SOFTWARE FROZEN preserved; C6 IMPLEMENTING / NOT FROZEN pending full registered runner,
ledger/provenance wiring, perturbation/controls/drift and actual mandatory acceptance.
Existing execution and statistical kernels are reused. C7–C10 NOT STARTED until C6 Freeze.
Holdout UNCONSUMED; Investor-QGV FUTURE_TRACK_C_INPUT. Track A/B/D/E/Web source untouched.
PR #4 Draft/Open/unmerged; canonical automatic merge forbidden. Continue autonomously
inside approved scope after remote approval record verification.


## Track C C6 SOFTWARE FROZEN / C7 D3-P boundary — 2026-10-01 09:57:08 UTC

Timestamp: 2026-10-01 09:57:08 UTC. AI: Codex. Module/Area: Track C EVL only.
Started From: fresh GitHub canonical/merge-base b8e39a2196a6d7794a04a0cd5393c68329e126ca,
Track C88da6f30560c4a2aee281a4cc45760eb3e0f4e80 (35ahead/0behind), PR#4 Draft/Open.
Previous chat logs were not used. Canonical/feature documents, full tree, code/tests,
workflow, latest Actions and PR discussion were read directly.
TC-D3P-005 S actually APPROVED/ACTIVE in repository; earlier approval-record conflict resolved.

Completed: registered full-family C6 runner, all mandatory controls/perturbation/drift,
ledger budget/terminal reports, C4 frozen-prediction/source lineage and current invalidation
resolution. Every registered grid identity is preserved, including unattempted/failed
coverage; incomplete family blocks acceptance. Existing C0–C5/execution/kernels unchanged.
Files Changed: EVL robustness.py, additive C6 fixture/tests/audit tool, Track C workflow/
reports and Track C-only SSoT overlays. Prior four-file C4 repair preserved; no new upstream
or Track A/B/D/E/Web source/artifact edit. EVL_SPEC_v0.1 unchanged; TAX_MODE=EXCLUDED.

Tests: source166dcba64b20aaead70981e84c0a4d87390744fb; Actions36845447156/job110314362158 SUCCESS.
Actual C6 targeted130/130 -> C0–C5 previous103/103 -> full629/629 ->
PIT/lineage/Holdout/cross-track audit -> complete acceptance evidence PASS.
Rolling/Expanding x Primary/Gap-stress: each17/17 MANDATORY diagnostic groups actually PASS.
Archive artifact11153252067 and its digest/full logs/hashes retained in
implementation/reports/track_c_c6_acceptance_2026-10-01.json/.md and CI log.
Two prior audit-script failures retained; path/Unicode parsing fixed without weakening checks.
GitHub tools have no local shell; actual fresh git fetch/pytest performed in Actions.
No fresh normal-merge replay claimed; preserved prior C5 integration499.

Decisions: TC-D3P-001..005 approved; C6 **SOFTWARE FROZEN** under TC-D3P-005 S,
limited to SYNTHETIC_SOFTWARE_VALIDATION. C0–C6 Frozen7/11=63.6% phase-count proxy.
TC-D3P-006 A **PROPOSED / NOT APPROVED / NOT ACTIVE**: exact C7 Pareto/cohort aggregation,
plateau/complexity/drift/medoid/distinctness policy; reviewed gap is result-impacting.
See implementation/reports/track_c_c7_selection_policy_proposal.md and current Track C
D3-P/D3-C register. No new C7 policy applied or selected candidate produced.

Provisional/Open Issues: REAL_PIT_RESEARCH_VALIDATION NOT_RUN (no complete real family).
C7 PREFLIGHT COMPLETE / BLOCKED_D3P_006, selection implementation/acceptance not started;
C8/C9/C10 NOT STARTED / DEPENDENCY BLOCKED. No Track C implementation baseline yet.
No significance, investment skill, alpha, Official profile, promotion or real Forward claim.
Holdout **UNCONSUMED**. Investor-QGV **NOT_IMPLEMENTED / FUTURE_TRACK_C_INPUT**.
PR#4 Draft/Open/unmerged; canonical automatic merge forbidden; separate Integration Audit needed.

Next Action: user decision on TC-D3P-006 A items1–9, then C7 targeted/prior/full/audits/
evidence/push/Actions/Freeze -> C8 -> C9 -> C10 -> Track C implementation baseline.
Do Not Repeat: C0–C6 implementation, past approval reconciliation, upstream redesign,
Track A/B/D/E/Web edits, Holdout peek, fabricated investor evidence, force push/history rewrite.


## TC-D3P-006B explicit approval — 2026-10-01T19:13:51.000+09:00

Scope: Track C only. Actual KST approval-processing clock above; source HEAD9cf4d7d68dd6bc9eda5db78571acf6e74811144d.
User did NOT approve A1–9 unchanged. B is **APPROVED / ACTIVE**; original A remains
unapproved historical proposal blob e4aa773a3b2d00dc530453875d3a14a796779a01, unchanged.
Authority: implementation/reports/track_c_c7_selection_policy_approved.md.
B: complete immutable Landscape and pre-OOS-selection configuration; invalid/nonfinite
integrity inputs FAIL versus legitimate undefined support NOT_RUN; independent metric x
cohort/fold exact Pareto; all eligible plateaus (min2 definition), full range/edge evidence,
no largest-size priority; existing C5 complexity; vector drift Pareto with trade-off ties;
restricted medoid with TIED_EQUIVALENT_REPRESENTATIVES and hash only for serialization;
raw OOS pair differences with statistical/economic distinctness left to C8.
Explicit synthetic-only algorithm fixture values allowed; no actual research threshold default.

C0–C6 SOFTWARE FROZEN preserved. C7 IMPLEMENTING / NOT FROZEN until complete actual
acceptance/regression/audits/evidence/Actions. C8–C10 NOT STARTED.
Holdout UNCONSUMED; Investor-QGV FUTURE_TRACK_C_INPUT; TAX_MODE=EXCLUDED.
No Track A/B/D/E/Web edits, C6 rewrite, automatic merge, force push or history rewrite.
PR#4 Draft/Open. Next: implement/verify B exactly; C7 Freeze then C8 policy audit.
