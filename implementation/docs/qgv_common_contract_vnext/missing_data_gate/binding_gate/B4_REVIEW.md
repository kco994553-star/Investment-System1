# B4 — factor identity and calculation-method identity: independent review

**APPROVE_RECOMMENDED for identity separation as an inactive contract principle.**
**RECOMMENDATION ≠ USER APPROVAL. RUNTIME_ENABLED=false.**

Input owner HEAD `1e79920bdea5f5580bf46414a083c06d5d3604d6`; canonical
`b8e39a2196a6d7794a04a0cd5393c68329e126ca`; integration
`523e702a806a718d163cfbf62aa3fc29d8c3ef3c`. This is a bounded continuation of
the approved M1–M5 principles and inactive implementation design. It does not
repeat the broad audit or approve a replacement G/FCF/V method.

## 1. Verdict and its limits

Factor identity names the economic question; method identity names an exact
operational calculation answering that question. They must be separately
referenceable. A factor can legitimately have separately authorized alternative
methods, but a method that answers a different economic question cannot be made
equivalent merely by reusing its factor ID. Factor-definition changes need their
own explicit definition version/authority; semantic split/merge needs the ID and
migration decision already described in the existing inactive Common Contract.

The present implementation does not enforce factor-level method identity. Coarse
snapshot version labels, Git/source hashes, numeric differences and saved payload
immutability provide useful evidence but do not establish method equivalence,
approved dispatch or historical executable replay. The current inactive sidecar
can carry generic immutable references; it has no active method registry or
runtime lookup and its validator does not authenticate referenced source bytes.

Approve the separation principle and exact-reference requirements as a bounded
design decision; **MORE_EVIDENCE_REQUIRED** remains the verdict for intended G
3–5Y, EPS/FCF and V replacement semantics. Deployment, dispatch, migration and
consumer adoption remain separate D3 decisions.

## 2. Actual source evidence

Paths and line ranges below refer to the unchanged input production files.

| Evidence | Exact source | What it establishes / does not establish |
|---|---|---|
| Legacy factor observation | `implementation/src/investment_system/contracts/models.py:74–81` | Contains factor ID, value, score, quality, stamp and free-text notes; no first-class selected method ID/version/input contract |
| Snapshot version envelope | `implementation/src/investment_system/contracts/models.py:94–122`; `implementation/src/investment_system/qgv/analysis.py:76–80`; `implementation/src/investment_system/versions.py:1–5` | Stores static implementation/system/standard/analysis-contract labels; it does not derive an exact factor-method closure identity |
| G forecast-name mismatch | `implementation/src/investment_system/qgv/raw_map.py:37–47,92–93,139–142` | `next_3_5y_growth` uses the same revenue YoY normalization as `revenue_growth`; note explicitly says it is a proxy, not a 3–5Y forecast |
| EPS fallback | `implementation/src/investment_system/qgv/raw_map.py:37–40,142`; `implementation/src/investment_system/contracts/raw.py:16–28` | Fallback is `fcf / revenue_prev - 1`; RawFundamentals has no prior FCF field and this fallback uses no per-share denominator. Intended replacement is not established |
| Horizon metadata | `implementation/src/investment_system/qgv/pipeline.py:21–43`; `implementation/src/investment_system/qgv/g_horizon.py:14–23,26–44,74–90` | Requested horizon changes coverage metadata, with `mutates_g_score=False`; it does not select a multi-year calculation method |
| V method alternatives | `implementation/src/investment_system/qgv/raw_map.py:57–84,145–156` | Central value uses DCF or P/E fallback; MOS uses conservative DCF or EPS proxy; reverse DCF may use a P/E-derived implied-growth proxy and realized YoY |
| V normalization differences | `implementation/src/investment_system/qgv/raw_map.py:16–17,57–84,146–156` | Multiple clipped transforms, direct percentile and direct rubric/context values coexist. A factor name or normalized scalar does not identify the transform, parameters, direction or source universe |
| Reuse references | `implementation/docs/qgv_common_contract_vnext/contract_record.schema.json:5–32,160–168,415–429,447–467`; `implementation/docs/qgv_common_contract_vnext/CONTRACT.md:25–32,43–56,122–128` | Generic `id/version/sha256/locator`, config binding, factor, normalization and aggregation refs can express the proposal without another runtime ProfileConfig |
| Inactive validator limit | `implementation/tools/qgv_contract_audit.py:58–101` | Validates schema, serializability and limited PIT coherence; explicitly does not authenticate source bytes/full revision closure or approved factor-to-method relationships |
| Weight-only Personal editing | `implementation/src/investment_system/personal/weights.py:94–108,112–131,142–157` | Overrides contain only node ID/local weight; editability and exact base registry version are checked. This is not active QGV method dispatch |
| Existing supported StrategyProfile API | `implementation/src/investment_system/contracts/strategy.py:19–35,139–145` | Custom API rejects non-configurable keys, including method identity; frozen weights/labels remain protected. Arbitrary direct construction of a params dict is not a scoring grant |
| Reuse hashes and provenance | `implementation/src/investment_system/personal/versioning.py:13–21,24–47,50–59` | Existing canonical content hashing, namespace and source/version/hash provenance are reusable primitives, not authentication by themselves |
| Historical payload protection | `implementation/src/investment_system/qgv/track_record.py:19–59`; `implementation/src/investment_system/validation/file_store.py:19–48,56–67` | Saved decisions cannot be overwritten through these APIs; outcomes are children and file reload retains payload. It does not choose archived executable methods |
| Raw historical bytes | `implementation/src/investment_system/ingestion/raw_store.py:47–70`; `implementation/src/investment_system/ingestion/replay.py:28–35,69–85` | Previous raw artifacts are retained, while ordinary replay getters address the current artifact. Raw history retention alone is not an exact historical raw/method manifest binding |
| PIT boundary | `implementation/src/investment_system/contracts/models.py:35–50`; `implementation/src/investment_system/pit/resolver.py:21–38` | DataStamp keeps economic period/publication/availability; provider resolution guards both published_at and available_at. Method identity must preserve this lineage, not substitute calculated_at |

The existing tests already characterize the G/FCF/horizon behavior at
`implementation/tests/test_qgv_common_contract_vnext.py:105–131`. They are not
evidence that the economic labels are approved, that every historical result is
invalid, or that a new method has been selected. No broad regression rerun was
needed to repeat those prior findings; the six focused probes below assess the
additional identity question.

## 3. Six adversarial cases, executed against existing paths

Machine-readable results and protected hashes: [b4_cases.json](b4_cases.json).
Six cases produced **17 PASS characterization assertions**. PASS means the
described legacy behavior and reference-hash sensitivity were reproduced; the
design is not an implemented admission mechanism.

The read-only [b4_verify.py](b4_verify.py) reproduces those exact 17 checks and
compares the eight recorded source/golden hashes before and after. From the
repository root in this execution workspace:

```sh
PYTHONPATH=/workspace/scratch/5f9c0923784f/test-deps:implementation/src:implementation/tools python implementation/docs/qgv_common_contract_vnext/missing_data_gate/binding_gate/b4_verify.py
```

`test-deps` contains the already-present jsonschema dependency; no package was
downloaded for this review. Another environment can use its existing jsonschema
installation. The verifier has no record/overwrite option.

| Case | Observed existing behavior | Detectability verdict | Minimum inactive contract response |
|---|---|---|---|
| 1. Same factor ID, alternative method output | Existing analyzer accepts a synthetic substitution of `next_3_5y_growth` score 90→60; partial G changes 36→28.5 with the same coarse version labels | Numeric drift visible; selected method identity and the reason for drift cannot be certified. This test substitutes an output; it does not deploy a forecast method | Factor-definition ref and selected method ref must be distinct and authenticated in the calculation binding |
| 2. Same name, input horizon change | Requested 1Q and 5Y produce different horizon metadata and the same G=36 on the same inputs | Display/request horizon visible; actual method input horizon is not authenticated | Separate requested/view horizon from the method's economic input horizon and pin the latter in its input contract |
| 3. Fallback method change | EPS 3/2 yields score 100; EPS-absent FCF 20/prior revenue 100 yields score 0. Both observations share ID and the same `eps or fcf yoy` note | Raw source inputs can aid reconstruction; the observation does not preserve a selected branch identity | Ordered authorized fallback refs, selection condition and selected branch/input refs; an altered fallback needs new exact binding authority |
| 4. Normalization method change | Central-value DCF=20/price=20 and P/E=20 emit identical score-50 FactorObservations. A well-shaped changed calculation SHA under the same version still yields `SPEC_VALID` | Identical output can conceal different methods. A compared trusted source hash detects bytes; structural `SPEC_VALID` does not authenticate equivalence | Pin transform, unit/direction/period/parameters and source closure; reject one ID+version resolving to different authenticated bytes |
| 5. Method version and historical retrieval | A stored original decision payload stays unchanged when another synthetic result is created | Stored bytes protected; archived executable dispatch/replay is absent. File reload was reviewed from source, not claimed as executed in this probe | Read exact historical payload/refs; never recompute it using latest method under the old identity. New linked research result requires separate authorization |
| 6. Personal method mutation | Supported `custom_profile` rejects method identity, method version and normalization keys; WeightOverride rejects an added method field | Existing supported APIs protect this boundary; no future evaluator/cache enforcement follows automatically | Preserve weight-only editing, no silent registry rebase, immutable method/validity references outside editable weights |

No method replacement, normalization change, coverage/ranking threshold, new
numeric default or Official score update occurred. All numeric variations above
are explicit synthetic fixtures or existing mappings. Real PIT/OOS and archived
executable replay are **NOT_RUN**; Holdout is untouched.

## 4. Minimum reuse contract — references, not a new engine

Use `config_binding_ref` to point to an immutable, authorized binding artifact
whose ordered records reference the existing generic ref shape. Do not mutate
the current sidecar schema/example or introduce new runtime enums/classes here.

| Reference / trace | Minimum meaning |
|---|---|
| `factor_ref` | Axis + stable factor ID + immutable economic-definition version/hash; display name is not identity |
| `method_ref` | Exact selected algorithm family/identity and immutable version/hash; source locator resolves its implementation and dependency closure |
| `input_contract_ref` | Original metrics, units, currency, economic periods/horizons, expected shapes and input lineage; no reconstruction of raw metrics by inverting clipped scores |
| `fallback_ref` and selected branch | Ordered permitted alternatives, deterministic selection predicate and actual branch ref; absent primary data is not permission for any fallback |
| `normalization_ref` | Exact transform and parameters, direction/scale, peer/history universe and applicable period where consumed; no invented percentile/cutoff |
| `applicability_ref` / `requirements_ref` | Versioned authority and evidence-backed predicates/input obligations; no declaration inferred from a nonzero weight |
| `calculation_ref` / source closure | Effective calculation identity bound to the complete selected method, normalization, aggregation and configuration refs, including exact source identity |
| Result context / provenance | Subject, namespace, as_of, decision_time, calculated_at, DataStamp/source/vintage refs and original QualityState/reasons; references preserve information rather than copying source facts |

An immutable ID+version must never resolve to different content. A method,
computation horizon, fallback, normalization, rounding/arithmetic or relevant
dependency change must change the exact effective calculation binding; it cannot
remain an equivalent calculation merely because the top-level display labels
match. No semantic-version numbering convention is selected. Bind source bytes
and dependencies as well as the declarative text; a hash over a stale declaration
does not detect a changed implementation.

Cache/result/comparison cohort identity must resolve subject/time/namespace and
the authenticated method/config/input lineage. These are **future requirements**,
not a claim that a new cache or registry was implemented. Compare only methods
that a separately authorized consumer declares comparable; same factor ID alone
does not authorize pooling, ranking or history aggregation.

The five mutation experiments in b4_cases.json reuse `content_hash` on synthetic
reference dictionaries and show that the method, input horizon, fallback,
normalization and method version can independently alter a binding fingerprint.
This establishes representation feasibility. It does not implement a resolver,
authenticate remote data or prove version selection.

When old snapshots lack these fields, preserve their original payload and coarse
versions and mark the missing factor-level identity **UNASSESSED/legacy**. A
bounded source audit may attach a new historical characterization sidecar,
without claiming that its metadata existed at the past decision or replacing
the original snapshot. Latest source/profile/configuration cannot fill a missing
historical binding silently. Retrospective research cannot be relabeled as an
original PIT decision; dated selection/authority must be explicit for the run's
actual decision regime.

## 5. Dependencies and cycle check

Separate planning from result assessment to avoid a circular definition:

1. Resolve authenticated subject/factor definition and authorized method/config
   references, retaining unresolved declarations.
2. Read declared input and predicate dependencies from that fixed method.
3. Admit predicate inputs before deciding applicability/conditional requiredness;
   resolve observation admission before any numeric contribution.
4. Resolve numeric weights independently of validity and compute only an
   authorized method under its exact binding, if later authorized.
5. Assess completeness/validity and then each consumer's ranking/publication
   authority against separate referenced policies.

| B relation | Dependency rule / cycle prevention |
|---|---|
| B1 requiredness ↔ B4 method | The authorized method declares input obligations; current use is implementation evidence, not required-factor authority. Unresolved intended methods cannot receive guessed production requiredness |
| B2 applicability ↔ B4 method | A factor's economic scope and the method's applicability evidence/predicate must both be explicit. N/A proof is not inferred from input absence or failed computation |
| B3 admission ↔ B4 input | Input and shared/predicate scope comes from an authenticated declaration; admission cannot be inferred backwards from a successful scalar |
| B5 completeness ↔ B1 | Completeness consumes requirements plus admitted evidence. It cannot decide its own requirements from the surviving contributors |
| B6 ranking ↔ B5 | Ranking/publication admission is a downstream consumer decision; numerical existence, completeness and validity are separately assessed |
| B7 profile ↔ weights | A permitted profile changes numeric weights/contribution using the pinned registry; it cannot select a method or rewrite applicability/requirements/admission/Official validity |

Conditional declarations may share evidence. A declaration dependency cycle,
missing authority or unresolved reference is an explicit unresolved binding,
never resolved by zero weight, field presence, a default method or retrospective
selection from whichever result ranked highest. The graph above is acyclic when
declaration resolution is independent of observed scores; concrete conditional
predicate graphs still require their own check when proposed.

## 6. M1–M5 conflict and bypass review

| Attempt | Recommended boundary | Finding |
|---|---|---|
| Missing input → N/A → smaller denominator → higher score | Applicability proof uses admitted predicate evidence and separate authority; missing observation never proves N/A | Candidate with this inference is REJECT_RECOMMENDED |
| Zero weight → requiredness/PIT/integrity bypass | Requirements and dependency admission occur independently before numeric weighting | M2/M5 preserve blocking obligations; method identity cannot erase failed input lineage |
| Custom → Official validity change | Namespace and immutable Official binding remain separate; weight edits create only their authorized custom version | Supported weight APIs provide reuse evidence; runtime wiring remains unapproved |
| Custom → new method identity | Method refs are outside mutable weights/parameter API | Supported custom APIs reject the tested keys; arbitrary alternate-method execution needs separate authority |
| Partial scalar → ranking/publication | B5 separates meanings and B6 applies explicit consumer policy | Method equality/complete metadata is not a ranking or publication grant |
| Method change → same calculation identity | Authenticated effective closure differs; same ID+version/different bytes is rejected as equivocation | Current static labels cannot enforce this; structural sidecar validator is insufficient |
| Method change → historical rewrite | Preserve original payload/refs; create a distinct linked result only under separate authorized migration/research scope | TrackRecord APIs support immutability; archived dispatch remains a future gate |

No unresolved production path is declared safe because these recommendations
exist. The B4 design is acceptable only with these guards; a proposal that permits
one of the bypasses above is not a PASS candidate.

## 7. Recommendation record and decision classification

| Field | B4 recommendation |
|---|---|
| Current | Stable factor IDs, static snapshot versions, implicit methods in raw_map, free-text notes; inactive generic-reference sidecar |
| Proposed | Separate factor definition from selected method and immutable version; bind exact input/fallback/normalization/applicability/requirements and source/calculation closure |
| Rationale | Existing G label/proxy, EPS fallback and identical DCF/P/E output demonstrate that names/scalars cannot identify the computation |
| Alternatives rejected | One global version only; method encoded into display labels; a new factor ID for every operational algorithm change; hash shape treated as authentication; editable method refs in Personal weights |
| Backward compatibility | Original snapshots, notes, stored coarse versions and histories retained. Missing old method metadata stays unknown rather than fabricated |
| Legacy score impact | Zero in this audit/design; no recalculation. Future method replacement can change scores and is separately D3 |
| Official impact | Zero current change; no method registry/default promotion, consumer migration, merge or publication grant |
| PIT impact | Existing published_at/available_at and source/vintage lineage retained; selected method cannot cure missing/future evidence. Real PIT/OOS NOT_RUN |
| Consumer impact | Future admission must compare exact authorized method/config regimes; identity is necessary but insufficient for rank/publication validity |
| Migration impact | Reference-based design reuses existing primitives; future provenance backfill/dispatch/cache/consumer changes must declare limitations and scope. No production migration authorized |
| D1 | Source/structure audit, six bounded probes, reference-hash demonstration and evidence documentation completed |
| D2 | Conservative identity-separation and no-equivalence recommendation completed |
| D3 | User adoption of B4 contract principle; actual method/fallback/normalization selection, effective calculation migration, factor semantic change and production consumer/runtime adoption remain pending |

**Exact next design gate:** combine this B4 recommendation with B1/B2/B3/B5/B6/B7
into the minimum coherent binding/admission decision package. B4 does not depend
on first choosing a new G/FCF/V method; it can define identity boundaries now while
their concrete meanings remain unresolved. A subsequent G/FCF method-decision
package can be designed independently of production migration and cannot
retroactively assign requiredness to resolve its own missing method semantics.
