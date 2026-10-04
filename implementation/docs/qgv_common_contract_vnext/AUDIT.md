# QGV reconciliation audit · 2026-10-04

Status: evidence-based current mapping; proposed contract INACTIVE / SPEC-ONLY.
Code paths below are relative to `implementation/src/investment_system/` unless
marked otherwise. Baseline full SHA and source hashes are in evidence/baseline.json.
No changes to production source, old fixtures, history or shared handoff.

## Fresh baseline and scope

Canonical b8e39a2196a6d7794a04a0cd5393c68329e126ca; integration trial
acaf1b5a82859ac2750a130ebe88f8b4d272ac66 (#40); Global routing
bb4cb174fd4a0af3b2281d4c37ae3abb4d540f88 (GCH-014). QGV producer #10
5eec129ef81641f0bc11f5adbb43d0b2122ee24b; Context design branch
b42f2be2a3688aaacb278239dfdd3c8253b1acf9. Fresh fetch found #41 advanced to
8668c69070c7956cb85d1ccf8cbeb8d9d2daf5cf; no chart code is adopted.
Canonical and #40 did not change relative to the previous audit. #40 is 190
commits ahead/0 behind canonical. That is not a completion percentage.

Working branch `codex/qgv-common-contract-vnext-spec-2026-10-04` starts from
canonical, 0/0 at intake, clean tree. Choose this base because QGV/Personal/strategy
sources match #40 byte-for-byte; do not bring 190 unrelated integration commits
into this scoped proposal. Source models.py on #40 adds Technical/Macro lineage,
not a QGV meaning change. Scoped final status carries actual commit/ahead/behind.

Read: live Global routing/status/decision register, root Current Handoff,
Project Index, Master Status, Common Schema/API, Module Map, history/conflicts,
Personal handoff, source/tests/fixtures, c21 workflow, #10 producer audit/status,
#14 consumer, #17/#19 publication/binding and Context AP1–AP3 design/decisions.
Root historical text and parts of Global indexes are stale; exact source/scoped
authority take precedence. No stale initial 'V=null' text overrides current tests.

The artifact recovers current implementation behavior; it does not prove all
original v1.7.6 method authorities exist in this checkout. Legacy 15×10 versus
current 20-factor semantic crosswalk remains unresolved. v1.5 standard and v1.7.6
analysis-contract version fields are distinct, not interchangeable score scales.

## 10 hypotheses rechecked

| ID | Verdict | Evidence and limits |
|---|---|---|
| H1 fixed Q/G weights | CONFIRMED | scoring.score_q/score_g call _weighted(Q_WEIGHTS/G_WEIGHTS). factors.py constants; existing test_analysis_scoring + golden |
| H2 tree/override exist but unwired | CONFIRMED | personal/weights.py effective_tree; src call-site search finds no production caller into QGV. C-24/C-30 record this split. Existing test_pil_p0_contracts + new isolation test |
| H3 no standalone ProfileConfig | CONFIRMED | fresh src symbol search finds none, at canonical and #40. #40 reports/investor_qgv_implementation_baseline.md explicitly records absence. Scope is current inspected trees, not all possible future branches |
| H4 StrategyProfile separate bundle | CONFIRMED | contracts/strategy.py configurable parameter pack + hash. q_weights/g_weights are FROZEN_KEYS, custom_profile rejects them; test_existing_strategy_still_rejects_q_weights |
| H5 V has 7 factors/prior | CONFIRMED | factors.py V_FACTORS, V_INITIAL_PRIOR, V_CANDIDATES; history 2026-09-23 14:27 plus later 25/20/15/15/10/10/5 records. This is research prior, not current Official maturity certification |
| H6 composite excludes V | CONFIRMED | analysis.py total=(Q+G)/2 rounded; V-only golden changes V 70→77.5 while total stays 70 |
| H7 prior/candidate missing differ | CONFIRMED | scoring._weighted vs score_v_candidates; golden absent/null/all QualityState combinations including numeric N/A divergence |
| H8 G 3–5y discrepancy | CONFIRMED | raw_map.map_raw uses _growth_to_score(revenue_yoy), explicit proxy note; pipeline attaches horizon with mutates_g_score=False. No CAGR/forecast input for this factor |
| H9 EPS→FCF semantic validity | PARTIALLY_CONFIRMED | implementation fcf/revenue_prev−1 and absence of fcf_prev/per-share fallback confirmed with raw test. This is not FCF YoY or per-share growth. Authoritative intended replacement and whether it was an explicitly accepted interim policy remain unresolved; cannot classify every historical result invalid |
| H10 V Quality reused as confidence/coverage | CONFIRMED | analysis.py v_factor_table reads quality.value into both; test_v_quality_label_origin. Whole-snapshot confidence default/caller provided, no independent per-factor confidence calculation |

Totals: 9 CONFIRMED, 1 PARTIALLY_CONFIRMED, 0 REFUTED, 0 wholly UNRESOLVED.
Specific unresolved semantic/authority questions remain inside confirmed findings.

## Current architecture map

1. Raw store/provider + dated source/stamp -> RawFundamentals.
2. raw_map: scalar ratios/rubrics/proxies and clip -> FactorObservation. raw_value
   currently repeats normalized score; no first-class metric/subfactor hierarchy.
3. Q(7) and G(6) -> _weighted fixed dictionaries. V prior(7) -> same _weighted;
   V research candidates -> independent complete-factor loop.
4. AnalysisEngine -> QGVSnapshot; V provisional, total Q/G only; combined coverage
   uses Q/G, not V. Type-adjusted is currently an alias of total.
5. Leaderboard consumes snapshots and orders total then Q (no QGV rescore).
   Portfolio links snapshots to supplied allocations; TrackRecord retains history.
6. Personal registry/version/overrides -> effective_tree, ending before QGV wiring.
7. StrategyProfile separate PROVISIONAL params; #40 EVL bindings support approved
   cash_buffer/lookback/deadband paths, not Q/G weights or 13F profile inference.

Full 20-factor raw/weight map: current_factor_map.json. No invented subfactors.

## KEEP / ALIGN / CHANGE_CANDIDATE matrix

All semantic decisions are **proposals**, not approvals. 'Official impact' below
means potential impact if changed, not evidence that current research is Official.

| Element / class | Current behavior | Intended meaning / Q-G-V difference | Evidence | Compatibility / Official impact | Migration requirement | Approval |
|---|---|---|---|---|---|---|
| IDs / KEEP | 7/6/7 stable factor keys | Distinct economic meaning; no forced symmetry | factors.py, factor map | Renaming meaning breaks snapshots; possible score impact on split/merge | Pin IDs/version; explicit semantic map for split/merge | Meaning changes require decision |
| Existing Q/G weights / KEEP | fixed dictionaries | Retain current legacy numeric behavior | factors.py, scoring.py, golden | High if changed | Preserve old dictionary/order and result | Official weight change gated |
| V prior/candidates / KEEP | initial prior + equal/MOS research alternatives | Research lifecycle distinct from Official | factors.py, history, test_v_prior_and_c15 | V result changes if weights move | Keep exact prior/candidate IDs/weights/history | Promotion/change gated |
| Financial applicability / KEEP | ROIC/WACC excluded; no redistribution | Economically intentional difference, denominator question separate | factor_applicable, financial golden | Changing denominator changes Q/rank | Preserve old path; new policy separate | New denominator gated |
| Weight binding / ALIGN | tree not connected; StrategyProfile blocks Q/G | Shared configuration references with namespace isolation | personal/weights.py; C-24/C-30 | Wiring alone must not change legacy score; custom runtime new behavior | Explicit node-factor map, maturity, pinned refs | Current spec authorized; runtime wiring not |
| Profile duplication / ALIGN | two differently scoped objects | Existing StrategyProfile may serve AdvancedParameters | strategy.py + personal/weights.py docstring | New storage/class unnecessary now | Reference manifest; no duplicate source of weight truth | No new class approved |
| Raw/normalized split / ALIGN | raw_value contains mapped score | Raw field/unit/source distinct from normalized score | raw_map._obs, G raw test | Neutral sidecar possible; redefining old raw_value not neutral | New referenced metric metadata, old payload unchanged | Semantic rewrite gated |
| Missing aggregation / CHANGE_CANDIDATE | partial fixed-weight contribution vs candidate blocking | Explicit complete score / partial contribution | scoring.py; missing matrix below | Yes: any new denominator/block/reweight can change scores | Version policy and fixture deltas; preserve legacy | QCC-P01 required |
| N/A numeric admission / CHANGE_CANDIDATE | prior skips N/A, candidate uses numeric N/A | Common domain admission needs decision | numeric N/A golden | Yes for candidate result | Do not silently 'fix' stored candidate evidence | QCC-P01 required |
| Value validation / CHANGE_CANDIDATE | out-of-range numeric factor can pass | New score must satisfy declared scale; legacy archive remains literal | Q=256 golden | Rejection changes eligibility/results | New admission boundary + negative tests | QCC-P02 required |
| PIT entry boundary / CHANGE_CANDIDATE | provider resolver guards; direct raw API does not | Admit only proven decision-time inputs at public boundary | pipeline.py, memory.py, future raw test | Changes acceptance, not proof of historical leak | Clarify trusted internal precondition vs public guard; pin policy | QCC-P02 runtime gate |
| G horizon / CHANGE_CANDIDATE | last YoY is 3–5y proxy, horizon metadata only | Name/period/forecast meaning must be explicit | raw_map.py, g_horizon.py, tests | Yes if calculation changes | Separate naming-only view from new forecasting method | QCC-P03 required |
| EPS/FCF fallback / CHANGE_CANDIDATE | fcf/prior revenue−1 | Not same-unit-period FCF growth nor per-share growth | RawFundamentals, raw_map, G test | Yes if removed/replaced | General fallback policy; no issuer exception | QCC-P03 required |
| V confidence/coverage / ALIGN | quality.value copied twice | Preserve legacy label, new metadata unassessed until method exists | analysis.py, metadata test | No numeric impact for sidecar; admission changes would affect results | Retain original; add typed separate assessments | Neutral spec now; new method QCC-P04 |
| V proxy meanings / CHANGE_CANDIDATE | fixed PE/DCF proxies, historic two-point PE comparison | Direct field name not proof of DCF solver/true percentile | raw_map.py, validation/historical.py | Yes on corrected methods | Normalization/version/peer-history basis and validity | QCC-P04 required |
| Composite / KEEP + CHANGE_CANDIDATE | legacy Q/G mean; V excluded | Future participating-axis/config contract only | analysis.py, V-only case | Yes, ranks/selection/records | Old composite retained; new version parallel history | QCC-P05 required |
| Immutable lineage / KEEP | existing snapshots/track records, separate namespace | Same engine per calculation version without Official/Custom write-through | track_record.py, personal/versioning.py, isolation test | None if preserved | Namespace/cache/storage isolation at future wiring | Runtime acceptance gate |
| Publication/Context / ALIGN | separate grants and AP1–AP3 admissions | Scoring schema cannot imply publication or rubric approval | #17/#19, Context branch decisions | Changes eligibility/display if conflated | Version/hash consumer compatibility, no grant inference | Existing scoped authorities |
| Old label/spec mismatch / ALIGN | stale 'V=null'; v1.5 and v1.7.6 fields coexist | Report actual provisional V and distinct version roles | versions.py, factors.py header vs tests | Metadata-only correction must be neutral | Add corrective note; do not rewrite history or infer 15→20 weights | New scoring crosswalk gated |

## Missing-data behavior matrix (actual current semantics)

No generic VALID/PRESENT shortcut is assumed. The following is from the complete
QualityState enum and golden cases with both numeric score and null score.

| Input | Q/G/V prior _weighted | V candidate evaluator | Current redistribution | Proposed handling |
|---|---|---|---|---|
| Factor absent | Skip contribution; PARTIAL if some weight used, BLOCKED if none | Entire candidate null | None | Preserve legacy; choose future completeness policy only via QCC-P01 |
| score=None, OK or other status | Skip; PARTIAL/BLOCKED | Entire candidate null | None | Retain presence and state separately |
| MISSING_DATA numeric or null | Score ignored; partial/block | Entire candidate null | None | Preserve original code/state in archive |
| PIT_UNAVAILABLE numeric or null | Score ignored; partial/block | Entire candidate null | None | Future PIT admission cannot be overridden by user weight |
| BLOCKED_DEPENDENCY | Entire affected axis null/BLOCKED | Entire candidate null | None | Do not relabel blocker as ordinary zero |
| NOT_APPLICABLE numeric | Ignore; partial/block | Numeric value included | None | Explicit discrepancy; QCC-P01 |
| Financial roic_wacc | Skip before reading observation, even BLOCKED | No comparable V applicability switch | None | Preserve financial old Q; applicability and denominator distinct |
| STALE_DATA / ESTIMATED_DATA / CONFLICTING_SOURCE numeric | Included | Included | None | New admission policy cannot be inferred from current inclusion |
| VERSION_MISMATCH / IDENTIFIER_CHANGED / IDENTIFIER_AMBIGUOUS / CALCULATION_ERROR numeric | Included | Included | None | Integrity acceptance risk; QCC-P02, never silently certify |
| OK / SYNTHETIC numeric | Included | Included if all factors present | None | Synthetic scope remains synthetic |
| Insufficient history | g_horizon records missing/partial; G score unchanged | No common history rule | None | Separate reason/period coverage; no invented cutoff |
| Source unavailable | Upstream missing/exception; not its own QualityState | Depends on resulting absent/null factor | None | Keep explicit source reason, not N/A |
| Zero-weight factor | _weighted still reads status; BLOCKED can block | existing candidates constrained to 5–30% so zero fails validation | None | Future zero-weight requiredness is unresolved, not assumed |

Partial arithmetic is `sum(w*observed_score)` in the original iteration order.
It is not divided by observed weight. Missing is not stored as a zero observation,
but the sum shrinks with missing weight. Overall snapshot coverage considers Q/G
only; V missing does not change that combined coverage. This is observed legacy
behavior, not a recommended new complete-score definition.

## Independent G semantic audit

| Question | Observed answer | Classification |
|---|---|---|
| Actual input | revenue, revenue_prev; _yoy=cur/prev−1 | C: explicitly documented legacy proxy |
| Forecast/CAGR | Neither a 3–5y forecast nor multi-year CAGR | A: UI/name can overstate meaning if proxy note is absent |
| Historical period | Raw map has no duration check; provider selects dated current/prior statements; arbitrary callers can pass mismatched periods | D: exact intended admissible horizon/annualization not defined by this mapper |
| Horizon selector | GHorizonConfig covers 1Q…5Y/custom, metadata and quarterly monitor only; no G-score recomputation | C: existing deliberate nonmutation |
| PIT | Raw mapper does not resolve availability; memory/provider and actual historical entry path own it. Direct raw entry is permissive | D: future common public boundary must specify admission; historical PIT failure not proven |
| EPS fallback | EPS YoY if both usable; otherwise _yoy(fcf,revenue_prev), no FCF prior or per-share denominator | B suspected: implementation does not realize label; D remains for authoritative replacement policy |
| Zero/negative prior | _yoy blocks zero, not negative; growth interpretation may be misleading | D: no new negative-base convention selected |

No naming-only finding authorizes changing old identifiers or old numerical
history. QCC-P03 separates proxy labeling from result-affecting replacement. The
intended growth horizon, positive/negative-base convention, same-period matching,
forecast versus realized distinction, fallback and coverage require an explicit
contract before implementation. No new forecast dataset or numerical default.

## V metadata audit

- Cause: AnalysisEngine builds v_factor_table directly from observations;
  confidence and coverage both read `quality.value`. provenance reads notes;
  snapshot data_stamp_refs are separate. The producer branch captures more
  lineage externally, so this finding is not 'no provenance anywhere'.
- Confidence keyword defaults to MEDIUM and is caller-controlled; changing it
  does not change Q/G/V. No independent factor confidence calculation exists.
- Domain output metadata is semantically conflated, not just an HTML label.
  However no numeric confidence multiplier was found. Quality legitimately affects
  numeric admission in scoring, which is distinct from confidence contamination.
- effective_weight in the table checks score presence, not quality admission.
  Numeric PIT_UNAVAILABLE can display a positive factor weight even when excluded
  by _weighted. Preserve archived field; a future contribution field must reference
  actual admitted aggregation rather than reconstruct it from display metadata.
- Coverage and confidence require separate methods/evidence and unknown states.
  The sidecar example does not invent a coverage ratio or confidence label.

## Dependencies and blockers

Numeric Q/G changes affect qgv/leaderboard.py sorting, validation cross-section
ranking/selection and integration/compatibility.py `(Q+G)/2>=50` annotation.
Portfolio primarily links supplied allocations/snapshot refs, not a new V-based
allocator. TrackRecord and producer semantic hashes must retain versions.
Web displays snapshot score/confidence/coverage, and P01/invalidation require
exact lineage/admission. Context Classification/Checklist/Suitability/Filter is
largely design-only: do not report unimplemented runtime dependencies as wired.
Approved Context CF15 preserves axis-local suitability; CF17 requires complete
configuration and does not supply numerical thresholds or new scoring policy.

No blocker prevents this SPEC-ONLY phase. Future blockers: missing authoritative
method/crosswalk decisions; Personal C-24/C-30 and runtime binding; unvalidated
growth/valuation replacements; rubric/data coverage; real PIT/OOS and consumer
version acceptance. Track C C5 does not authorize QGV-weight search by implication.

## Proposed decision queue (not existing approved register entries)

Local proposal IDs below are scoped to this package. They do not rewrite Global
or Track C decision registers and do not impersonate an approved D3-P.

| Proposal | Decision required before runtime | Impact / unapproved alternatives |
|---|---|---|
| QCC-P01 | Missing/N.A./partial/contribution/renormalization/zero-weight semantics | Keep legacy partial sums vs withhold vs approved applicable-weight denominator; numerical and ranking differences |
| QCC-P02 | Typed score admission and public PIT/provenance boundary | Preserve permissive historical replay; reject malformed new requests or other explicitly approved rule. No silent old-score repair |
| QCC-P03 | G forecast/horizon/EPS→FCF contract | Relabel only versus new forecast/CAGR/fallback or withhold; no formula chosen |
| QCC-P04 | V normalization and confidence/coverage methodology | Preserve prior research; define real percentile/valuation/rubric semantics later; no default or promotion |
| QCC-P05 | Composite + Official/Custom config binding scope | Keep QG legacy; separately approve participating axes/formula/weights and editable nodes; no weights chosen here |

Any resulting Official meaning/weight/normalization, Frozen contract, ranking,
historical evidence or numeric-policy change needs user decision. Approval of this
audit is not approval of any option above. No decision is needed to complete the
current score-neutral evidence package. Stop before production migration.
