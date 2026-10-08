# Q/G/V consistency evidence delta — G/V continuation

**READ_ONLY / D1_D2_EVIDENCE_COMPLETE / INACTIVE.** No method, requiredness,
consumer criterion, formula, rank, production source, state, receipt, Handoff,
golden or history was changed. B4/B7 principles are approved from the explicit
user instruction; B2/B3/B5/B6 remain unapproved recommendations. B1 remains
MORE_EVIDENCE_REQUIRED, with zero production roles assigned by this review.

## Source scope and reuse

Root supplied fresh refs: canonical `b8e39a2`, owner `4fb08a0`, evidence-review
`df5c7044`, PR44 `cb1906b2`, PR42/integration `11d2f25e`, Global `b3532a2`.
Those remote reads were performed by the root, not this child. This review read
the established binding/admission and V reconciliation artifacts and did not
restart their broad audits or prior partial-score counterexamples.

The local integration checkout is actually `523e702a806a718d163cfbf62aa3fc29d8c3ef3c`.
All 23 inspected source files were compared with exact latest
`11d2f25ef8bef3459ca969f50eec190099f15ecb` Git blobs and match byte for byte.
All nine production sources supporting the previous admission trace match the
fresh integration pin too. `source_evidence.json` records those hashes. This is
source equivalence, not a new full integration or CI run.

The owner's `identity_contract/` and `admission_safety/` files were read at their
local paths and hashed separately. At intake they were uncommitted/unpublished
owner output; this review does not authenticate them as accepted delivery.
Their design is relevant for avoiding duplicate work, while actual authority
comes from explicit user approvals and already published evidence.

## Shared meaning matrix

Paths below are relative to `implementation/src/investment_system/`.

| Dimension | Q observed meaning | G observed meaning | V observed meaning | Inactive reconciliation |
|---|---|---|---|---|
| Factor identity | Seven stable Q IDs; Q7 management rubric remains distinct from unresolved capital-allocation intent | Six stable G IDs; next_3_5y intent is not the actual annual proxy | Seven distinct valuation concepts and research history remain | **KEEP** existing factor identity; no role inference from code use or weight |
| Method identity | Algorithm/rubric identified by code and free-text notes, no explicit field | Horizon/fallback branches have no factor-level method identity | DCF/P-E/proxy/passthrough branches share factor IDs without branch identity | **ALIGN** exact immutable method refs separate from factor ref under approved B4; method replacement remains D3 |
| Method version | Snapshot has coarse system/standard/contract/implementation labels | Same coarse labels survive horizon and fallback differences | Same coarse labels cover different normalizers and lifecycle paths | **ALIGN** method-version plus exact input/normalization/fallback/source-closure references; don't invent historical binding |
| Raw versus normalized | `_obs.raw_value` repeats supplied normalized score; actual ROIC/margin/etc. not carried here | Actual YoY/capital intensity is lost from this field after clipping | Value/price/multiple fields become scores or passthrough scores | **ALIGN** separate raw metric refs, units, calculation result and normalized score; never invert clipped score to reconstruct raw data |
| Fallback | Financial profile selects NIM/CET1; textual health/margin labels do not fully describe the branch | EPS branch or current FCF/prior revenue branch; notes say “eps or fcf yoy” | Central value/MOS/reverse proxy branches can share P/E input family | **KEEP** literal branches in legacy replay; **ALIGN** selected branch/input dependency; **CHANGE_CANDIDATE** any economic fallback correction |
| Applicability | `factor_applicable` excludes financial ROIC/WACC; raw mapping also marks it N/A | No actual factor-specific requiredness authority supplied | V prior receives profile; V candidate admission has no profile argument | **ALIGN** declared context and admitted predicate evidence; **CHANGE_CANDIDATE** new predicate/exclusion; missing never establishes N/A |
| Missing/admission | `_weighted` preserves fixed contribution and diagnostic partial; BLOCKED_DEPENDENCY blocks axis | Same reducer; absent/PIT_UNAVAILABLE omission does not supply semantic validity | Prior shares reducer; candidate loop requires seven numeric components but permits numeric N/A | **ALIGN** original evidence/disposition/scope; **KEEP** literal legacy arithmetic; candidate admission adoption is D3 |
| Coverage | Axis coverage is reducer state based on missing/admitted used weight, not an input-history fraction | Same axis state, plus separate quarter-inventory `g_horizon` coverage | V table duplicates quality as coverage; prior state differs from candidate completeness; overall snapshot ignores V readiness | **ALIGN** named scope/method/units for input coverage, scoring completeness and legacy state; **CHANGE_CANDIDATE** runtime criteria |
| Confidence | Snapshot caller string, default MEDIUM; not computed from source coverage | Same string; horizon completeness is not a confidence estimator | Table repeats QualityState as confidence; lifecycle is separate | **ALIGN** confidence assessment and method independent of quality, coverage, lifecycle and weight; no number/default selected |
| Provenance | Stamp ref/notes are carriers, not authenticated method closure | Same; paired-period/share/unit/source/vintage data are not fully represented by observation | Same; peer/history/implied-growth producer scope matters | **ALIGN** actual source artifacts/hash, vintage, units and per-input period refs; production producer already preserves raw hashes |
| PIT | Provider resolver checks both published_at and available_at; direct raw/observation entry points do not resolve stamps | Same; requested horizon metadata does not establish decision-time historical input availability | Same; peer/history/DCF assumptions also need exact availability provenance | **ALIGN** input-scope admission before weights; keep existing protections and SEC-restatement limitations; no full-PIT claim from producer PASS |
| Consumer use | Q total may be partial despite numeric output | G proxy result may be numerically finite while method semantics remain unresolved | V provisional prior exists independently of Q/G total | **ALIGN** producer-owned assessments → shared consumer admission refs; actual criterion/adoption remains D3 |

`FactorObservation` is shared across Q/G/V, so the lack of exact method binding
is a common problem. Economic transformations may deliberately differ. Alignment
means consistent meanings and references, not transplanting a growth normalizer
into valuation or imposing seven-factor admission everywhere.

## Authority and dependency consequence

The approved B4/B7 principles permit this source characterization and inactive
descriptor work. They do not approve producer validity, real applicability,
requiredness, consumer cohorts or runtime override use. A complete method
descriptor can improve B1 evidence quality without proving any factor REQUIRED,
OPTIONAL or CONDITIONAL. In particular, source-supported “uses current FCF divided
by prior revenue” proves arithmetic, not an EPS-growth or FCF-per-share meaning.

The coherent dependency remains: exact context/method refs → predicate evidence
admission → applicability/requirements authority → method input admission →
literal diagnostic contribution → independent producer result assessments →
consumer purpose/version/namespace admission → separate ranking/publication.
Weights cannot choose applicability/requirements or waive source/PIT obligations.

The current `(Q+G)/2` remains literal. V participation, normalization, admission,
history/legacy migration, factor roles and production WeightOverride wiring are
still separate D3 questions.
