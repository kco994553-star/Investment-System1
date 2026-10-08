# Independent Consumer / Profile Review — B5, B6, B7

**RECOMMENDATION_READY / INACTIVE / SPEC-ONLY.** This review does not approve
criteria, activate a runtime policy, issue a grant, change scores/ranks, or merge.
M1–M5 are approved principles; their implementation contract is design-ready and
inactive. The actual concrete completeness/ranking rules were expressly excluded
from the principle approval. B5–B7 below are technical recommendations.

Source authority: owner intake `1e79920bdea5f5580bf46414a083c06d5d3604d6`, canonical
`b8e39a2196a6d7794a04a0cd5393c68329e126ca`, integration
`523e702a806a718d163cfbf62aa3fc29d8c3ef3c`. Integration-only files were read from
that exact Git object and the matching detached worktree; no integration writes
occurred. Hashes of 24 source files and actual counterexample results are in
[consumer_profiles.json](consumer_profiles.json). Paths below are relative to
`implementation/src/investment_system/`; line references describe those pins.

## Findings that matter to consumer admission

| Finding | Current evidence | Consequence for the proposal |
|---|---|---|
| Numeric partial totals exist | Owner `qgv/scoring.py:24–57` preserves fixed contribution; `qgv/analysis.py:42–61` can emit PARTIAL and `(Q+G)/2` together | Scalar existence is not a new complete/valid result contract |
| Direct Leaderboard accepts every supplied snapshot | Owner `qgv/leaderboard.py:29–55` sorts then assigns ranks without coverage/validity filter; PARTIAL survives only as freshness text | A consumer boundary is needed; changing legacy eligibility is a D3 migration |
| Producer PASS is deliberately mechanical | Integration `leaderboard_producer/rank.py:37–45,63,226–244,285–292` ranks every PASS QGV snapshot; `partial_blocked_filter=NOT_DEFINED_NOT_INVENTED` | PASS proves persistence/identity/lineage and existing sort behavior, not QGV full scoring or new rankability |
| Producer does enforce some identity/PIT protections | Integration `leaderboard_producer/qgv_input.py:135–218` checks semantic hash, snapshot identity/version/weights, synthetic state, availability and raw-input lineage | Do not claim the producer lacks all admission; the missing layer is semantic completeness/result-use admission |
| Research Portfolio selection uses numeric presence | Owner `validation/vertical_slice.py:28–59` selects Q/G-present results, with explicit PROVISIONAL_RESEARCH/non-Official labels at 103–108 | Preserve historical research behavior; do not relabel it Official or migrate implicitly |
| Portfolio constructors attach references | Owner `qgv/portfolio.py:46–79,81–111` attaches snapshot IDs to generic or fixture holdings; it does not select by QGV or validate referenced score maturity | Holding/reference existence is not a score admission claim; actual holdings/valuation can remain usable while a QGV context is blocked |
| Track Record records facts, not score authority | Owner `qgv/track_record.py:19–43,45–59` archives payload/reference and appends outcome children | Archive failed/partial attempts with exact meanings; immutable storage does not grant validity/ranking/publication |
| Personal PARTIAL has a different meaning | Owner `personal/quality.py:26–28` permits VALID/PARTIAL presentation; `personal/ports.py:64–71` checks `available_at`, and `personal/fit.py:57–66` constrains invalid/unresolved contexts | Never translate Personal actionable(PARTIAL) into QGV completeness/PIT/rankability; Personal timestamps also do not supply absent QGV publication times |
| Research display has independent authority | Integration `publication/authorization.py:14–17,45–68,85–93` requires exact explicit grants; active grants empty. `publication/predicate.py:42–101` allows PARTIAL disclosure only with matching grant and no veto, and never Official/Live | Blanket “only complete results may ever be research-displayed” would conflict with existing P01 policy. Diagnostic partial disclosure and normal ranking stay separate |
| Publication currency is not scoring validity | Integration `publication/qgv_binding.py:63–110,145–182` binds persisted hashes/methodology and resolves invalidation into `current_valid`; no score calculation or grant | Reuse provenance/currentness refs, but do not alias `current_valid` to complete score/PIT/ranking |
| Web is presentation-only | Integration `product/web_mvp.py:25–67` validates envelopes/identity; `product/web_assets/app.js:89–107,281,310–313` guards false published research and renders supplied scores/ranks | Browser must not invent result eligibility. Existing guard is not a factor-level completeness evaluator. No new API implementation is found or introduced here |

The historical `leaderboard_producer/research_publication.py` probe still says P01
is unapproved. It is not the current publication authority: actual
`publication/*` and `docs/research_publication/STATUS.md` record approved/active
P01 policy while production display remains inactive because grants are NONE.
This distinction prevents both a false “publication policy absent” finding and
a false “research is already published” finding.

## Minimum result expressions — B5

Preserve the existing QGVSnapshot scalar, QualityState, CoverageState and Common
Contract `legacy_score` as literal historical values. Add only inactive,
reference-composed assessments in this design; no runtime enum/class is added.

| Independent expression | Authority needed | What cannot substitute |
|---|---|---|
| Numeric contribution | Admitted input/contribution trace and exact method/arithmetic refs | Presence cannot prove the remaining expressions |
| Coverage | Named evidence universe, units and assessment method | QualityState, default confidence, or an unnamed percentage |
| Completeness | Pinned requirements/completeness declaration for the selected method/scope | All positive weights, all twenty factors, READY, or a guessed cutoff |
| Scoring validity | Identity/configuration, applicability-proof and related/shared admission obligations | Complete data or finite arithmetic alone |
| Ranking eligibility | Explicit consumer/method/version/namespace/cohort policy and decision | Complete, valid, producer PASS, or a scalar alone |
| Publication eligibility | Existing exact P01 subject/grant/veto plus any consumer contract | Rank, producer PASS, complete data, or current invalidation state alone |

Unresolved policy remains UNASSESSED with reason and references. Dependency-scoped
blocking preserves the original rejected evidence without representing it as a
valid score. The proposal does not decide which factor is required, whether
optional missing is complete, or the scope of every ordinary missing failure.

**B5 verdict: APPROVE_RECOMMENDED.** Reason: independent meanings already exist
in source and in M4/P01; a single score/null or READY flag loses them. The
alternative “READY means valid/rankable/publishable” is rejected. The alternative
“all factors with positive weight are required” is also rejected because M5 makes
obligations independent of weight and actual factor roles are unresolved.

Compatibility: old scalar/coverage fields and serialized QGV shapes stay literal;
the design is additive. Score impact now: zero. Future result-use restriction can
change ranks/selection without altering any scalar, so implementation/adoption
still needs D3 authority and versioned comparison. PIT impact: no scalar or
metadata flag can turn related PIT/integrity failure into PASS. Migration cost:
reference-sidecar and consumer adapter work after actual criteria are approved;
no universal replacement result enum. Audit/design D1; conservative recommendation
D2; concrete criterion/adoption/version migration D3.

## Consumer-specific boundary — B6

| Consumer | Diagnostic partial / blocked information | Complete / valid information | Ranking / publication |
|---|---|---|---|
| Analysis | Show admitted diagnostic components and missing/rejection reasons under explicit diagnostic/research label; blocked numeric is not a valid score | Report independent assessments and exact method/version | No inherited authority |
| Leaderboard | Partial arithmetic does not enter normal ranking merely because it exists. Any partial research comparison needs an explicitly approved cohort/policy and clear diagnostic meaning | Completeness/validity still need consumer admission | Ranking policy separate; rank does not grant publication |
| Portfolio | May attach read-only context/reference or preserve actual holdings when QGV is unavailable. Selection/allocation cannot infer eligibility from a partial number | Use a separately bound selection/decision policy | Preserve provisional research selection and actual holdings; no implicit Official promotion |
| Track Record | Archive partial, blocked and rejected attempts with exact source/assessment refs | Archive the original decision-time policy/version | No score-validity claim or grant from archive existence; outcome is a linked child |
| Research display/publication | P01 permits partial disclosure only with exact RESEARCH_DISPLAY grant and existing veto checks | Complete does not issue grant; blocked score remains withheld | Active grant set NONE; no Live/Official claim. Explicit research comparison policy if ranks are shown |
| Personal/Custom | Namespace-separated diagnostic context; actionable(PARTIAL) stays a Personal presentation meaning | Resolve exact method, quality and consumer policy | Custom result never mutates Official validity/rank/grant |
| Web/API | Render producer-owned states/reasons/envelope; browser does not fill scores or interpret their existence as eligibility | Preserve supplied assessment and provenance | Render only authorized persisted rank; reuse schema-1/P01 guards. No frontend rescore/filter or API added |

**B6 verdict: APPROVE_RECOMMENDED** for this reference-based boundary, with
explicit adoption deferred. The proposal does **not** claim that M4 already
approved a blanket partial-ranking ban or that P01 grants display now. It
recommends no normal ranking from an unassessed diagnostic partial. A later
consumer can select a justified partial research policy only through separate
authority; no default/cutoff is supplied.

Rejected alternatives: producer PASS ⇒ rank-valid; total exists ⇒ Portfolio
eligible; archive exists ⇒ publishable; complete ⇒ P01 grant; research partial
display ⇒ Official/Live. Each conflates a source-proven independent boundary.

Compatibility: preserve existing engine sort, producer records, research labels,
Track Record history, and zero active grants. Score impact now: zero. Future rank
filter, selected universe or publication change is result-affecting even if
arithmetic stays identical, requiring D3 and explicit cohort/version comparison.
PIT impact: consumer admission consumes original admitted lineage, never creates
full PIT PASS from a mechanical producer PASS. Migration cost: exact consumer
policies/adapters and historical comparison; no engine duplication. Audit/design
D1; recommendation D2; actual selection/ranking/publication adoption D3.

B5 and B6 should remain logically separate: completeness/validity is a result
assessment; ranking/publication is a consumer assessment. They may share one
approval package, but cannot become one boolean.

## Profile mutation boundary — B7

Existing Personal layer already provides the minimal profile structure:
`personal/weights.py:1–7` separates its purpose from provisional StrategyProfile
(C-24) and refuses guessed Official weights (C-30); `65–82` validates the registry;
`94–109` restricts editable node/maturity/namespace; `113–147` pins immutable
version and refuses silent rebase; `149–186` calculates local/global weights while
keeping missing weights unset and zero-parent child mix. `personal/versioning.py`
has namespace, content hash and source Provenance.

| Mechanism | Can change within its existing authority | Cannot acquire by changing a profile |
|---|---|---|
| Frozen Q/G dictionaries | No mutation in this phase | New Official factor/method/requiredness/ranking policy |
| V initial prior / research candidates | Current separate candidate identities and maturity are preserved | Calibrated/Official identity or publication authority |
| StrategyProfile | Existing provisional configurable risk/technical/macro/cash/execution parameters | Q/G weights, V production switch, Q7 label, unknown method/role keys (`contracts/strategy.py:19–35,139–145,179–183`) |
| Personal WeightOverride | Existing permitted WEIGHT-node numeric local weight in an authorized Custom/research namespace; resulting contribution only after separately authorized runtime wiring | Factor/method identity/version, input contract/horizon/fallback/normalization, requiredness, economic applicability truth, evidence/PIT/integrity/provenance obligation, or Official result/ranking validity |

The current WeightOverride fields are exactly `node_id` and `local_weight`; do
not create a second ProfileConfig or place semantic policy inside this numeric
override. Actual factor-node mapping and authoritative maturity/weight dataset
remain bindings; a sample node or current code use does not establish authority.

**B7 verdict: APPROVE_RECOMMENDED.** The key adversarial condition is a zero
Custom weight for a method-required input: contribution may become zero, while
the requiredness/admission trace is unchanged. Current tree code proves weight
and registry isolation only; it is **not** wired to QGV and cannot itself prove
runtime PIT/requiredness preservation. Future evaluator/cache/storage/consumer
identities must pin namespace, registry, immutable override-set hash and exact
method/input/applicability refs. No method-only sidecar is sufficient if a shared
cache key omits those bindings.

Rejected alternatives: Custom weight zero means factor removed/optional/N/A;
Custom method switch under the same override/version; preview result reused by
Official board; provisional registry values filled from examples. These violate
M1/M2/M5, C-24/C-30 or exact identity. Compatibility: current Personal objects,
namespaces, validations and no-silent-rebase semantics are reused. Score impact:
zero now; future authorized Custom arithmetic may differ while Official stays
literal. PIT impact: weights never alter obligations. Migration cost: explicit
factor-node/cache/consumer binding after authorization, without another engine.
Audit/design D1; recommendation D2; runtime wiring or new method authority D3.

## Dependency and adversarial review

An acyclic assessment order is: exact method/input scope (B4) → evidence admission
for predicates (B3) → applicability/conditional role (B2/B1) → observation
admission (B3) → contribution/basis → result assessments (B5) → consumer policy
(B6). B7 selects only a permitted numeric configuration, outside semantic/evidence
truth. Reusing B3 for predicate and observation stages is not a semantic cycle.

Completeness depends on requirements, so unresolved method semantics must not be
silently frozen by a guessed requiredness assignment. Consumer needs define
policy selection, not truth of source evidence. Method declarations may name
consumer scopes, but cannot consume the resulting rank to redefine their own
requiredness/applicability. Conditional-role/applicability dependency cycles stay
unresolved; weight defaults cannot solve them.

| Adversarial route | Independent disposition |
|---|---|
| Missing → N/A → smaller denominator → higher score | REJECT. Economic proof/permission is independent of observation presence and Custom profile; no available-only renormalization |
| Zero weight → requiredness/PIT/integrity bypass | REJECT. Method/evidence obligation trace precedes contribution; current tree isolation is insufficient runtime proof |
| Custom profile → Official validity / method replacement | REJECT. Separate namespace and immutable method declaration; WeightOverride has no such authority |
| Diagnostic partial → normal Leaderboard | Characterized in legacy engine; proposal cannot infer new admission from number/PASS. Any new filter needs explicit D3 adoption |
| Complete or mechanical PASS → publication | REJECT. Exact P01 grant and veto/currentness are independent |
| Partial → explicitly granted research disclosure | Compatible with current P01 only when its existing checks pass; does not imply ranking/Official/Live |
| Method changed → old result/cache/profile identity reused | REJECT. B4 exact semantic version/content binding plus namespace/config identity; preserve old snapshot and history |

## Actual bounded verification

Read-only runtime probes reused golden `all_70` and
`competitive_advantage__MISSING_DATA__numeric`. Legacy partial output was
**Q=56, G=70, total=63, coverage=PARTIAL**; the direct Leaderboard ranked it second
after the full all-70 case. The provisional Portfolio selector accepted the same
Q/G-present partial arithmetic. No golden expectation or engine changed.

Synthetic Personal registry probes changed Custom local weights 0.5/0.5 → 0/1;
the registry hash remained identical. Official override, StrategyProfile method
key and frozen Q weight key were rejected. This characterizes existing profile
isolation rather than accepting a new runtime zero-weight rule.

Pinned integration publication probes used manufactured fact dictionaries and a
local-only synthetic grant fixture. Production active grants remained empty.
Partial without grant stayed NOT_AVAILABLE; the explicit fixture grant permitted
DISCLOSURE_PARTIAL; BLOCKED with the same fixture grant remained NOT_AVAILABLE;
LIVE/OFFICIAL promotion requests were rejected. These manufactured facts are not
real company evidence or real authorizations.

All five counterexample families completed. This is current-boundary
characterization, **not** vNext runtime-policy acceptance, full regression,
real PIT/OOS, actual event delivery or production migration. Holdout UNCONSUMED.

The reproducible [read-only probe](consumer_profile_probe.py) completed a second
run with **5 families / 20 explicit assertions**, with each actual result matching
the original evidence. It writes only the requested scratch JSON. Use owner
`implementation/src` on PYTHONPATH and pass `--out <scratch>/consumer-profile.json`;
optionally pass `--integration-root` to the detached worktree at the exact pin.
Its isolated publication subprocess checks the integration HEAD before using it.

## Required follow-up authority

The minimal semantic choice is approval/amendment of B5/B6/B7 boundary principles
alongside B4 identity and B1/B2/B3 authority, without guessing concrete twenty-factor
roles, N/A predicates, completeness/ranking cutoffs or numeric defaults. Actual
method changes, runtime Missing-Data wiring, calculation migration, legacy
recomputation, consumer adoption, grants and merges remain separate D3 paths.
Independent source/contract/synthetic work may continue before those approvals.
