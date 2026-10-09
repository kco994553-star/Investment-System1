# Method-lineage → consumer safety evidence delta

**D1/D2 / INACTIVE / NO_PRODUCTION_ADOPTION.** This report adds method-lineage
transport evidence to the prior Result Admission & Consumer Safety proposal.
The old partial/BLOCKED ranking and P01 projection counterexamples are reused,
not rerun for new counts. Their nine supporting production source hashes match
fresh integration `11d2f25e`; see `source_evidence.json`.

## Where information exists, disappears, or never existed

| Information | Producer/Analysis boundary | Persisted QGV carrier | Leaderboard / publication projection | Finding type |
|---|---|---|---|---|
| Stable factor ID | `raw_map` creates factor observations with ID | `qgv_producer/record.py:129` persists a sub-factor table | Legacy row has only Q/G/V/total and snapshot ID; producer stores upstream semantic-hash reference | Projected out but source-reference retained; not evidence destruction |
| Method ID/version/input-contract identity | Absent in FactorObservation and QGVSnapshot; textual notes/coarse versions only | Sub-factor table cannot preserve a field never produced | Coarse-version/weights checks exist; no exact method compatibility assessment | **Never produced**, not “lost at Leaderboard” |
| Actual raw metric | `_obs.raw_value` is already normalized score | Observation export preserves this literal value and original raw-input hash refs | Board carries scores; original raw artifacts remain referenced upstream | Not retained in observation; cannot reconstruct from clipped score |
| Horizon declaration | Pipeline creates `g_horizon` metadata with `mutates_g_score=False` | Verbatim snapshot serialization and hash preserve it | Direct row omits horizon; persisted board keeps source semantic hash, not a horizon eligibility guard | Produced/retained upstream, projected out of row, unused as method authority |
| Fallback branch | Mapper encodes rough notes; selected branch/version/dependency contract absent | Notes survive sub-factor export | Board does not consume branch or method admissibility | Partly recorded, exact structured identity never produced |
| Legacy coverage/PARTIAL/BLOCKED | `_weighted`/Analysis emit explicit states | Snapshot state is preserved | Direct row projects it to freshness (synthetic overrides coverage); producer separately retains eligibility.coverage_state but ranks mechanical PASS | **Retained but unused** for cohort selection; different from missing information |
| Completeness/scoring validity | No independent assessment under method/requirements authority | Producer PASS checks persistence/identity/lineage, not full QGV scoring validity | Normal rank cannot obtain an assessment absent upstream | **Never produced**, not a board-only filter omission |
| Ranking eligibility | Direct engine accepts supplied snapshots; persisted producer selects mechanical PASS | Cross-section eligibility is provisional research and not a new semantic method policy | Producer declares `NO_SEPARATE_RULE_ENGINE_RANKS_EVERY_PASS_SNAPSHOT` | Legacy meaning exists; future vNext admission unassessed |
| Code provenance | Coarse snapshot versions; producer's code_commit stored operationally | Semantic hash excludes operational code commit | P01 binding separately includes manifest code_commit in its provenance hash | Existing protection must be retained; code pin alone still not factor-method equivalence |
| Publication | P01 has independent exact grant/currentness/veto authority | Original subject hashes exist | Existing structural extractors compress upstream states; old synthetic probe exposed projection limitations | Separate authority; rank or mechanical PASS cannot grant publication |

Source anchors: `qgv/analysis.py:77–132`, `contracts/models.py:75–126,194–204`,
`qgv_producer/record.py:123–133`, `qgv_producer/batch.py:151–191`,
`leaderboard_producer/qgv_input.py:135–218`, `leaderboard_producer/rank.py:226–244,285–331`,
`publication/qgv_binding.py:63–110`, `publication/extractors.py:53–127`.
Exact source hashes are recorded alongside this report.

The prior direct partial-rank finding remains a real legacy behavior, while
normal ranking adoption would be D3. No blanket partial-research display ban is
inferred: existing P01 can permit exact-granted partial disclosure, independently
of normal ranking and without Official/Live promotion. The production real
producer rejects synthetic input; test-only carriers do not prove actual release.

## New bounded lineage carrier characterization

`consumer_lineage_probe.py` adds 11 assertions; all PASS in
`lineage_probe_results.json`. It does not rerun the old missing→partial ranking
counterexample or use any replacement growth/valuation formula.

1. Two synthetic QGV records with identical semantic output/coarse versions and
   different operational `code_commit` values both validate under
   `require_real=False`. Their semantic hashes are equal; operational pins remain
   distinct outside that hash. This demonstrates the need for method identity
   even when differing code/methods could happen to produce the same number. It
   does **not** execute or prove an actual different method in this fixture.
2. Declared `g_horizon` 1Q versus 5Y metadata gives different persisted semantic
   hashes, so content hashing **does detect reported horizon drift**. Coarse
   versions remain equal; direct legacy rows are identical and no consumer
   method-compatibility/admission guard is supplied. This fixture changes only
   metadata; it is not evidence of a real 1Q/5Y growth calculation.
3. Dataclass and exported-subfactor inspection confirms that exact method/version
   and independent result assessments cannot be carried by the current fields.
   All inspected production source bytes remain unchanged.

The P01 binding's separate provenance hash retains manifest `code_commit`. The
probe does not exercise or weaken it, and this report does not claim that code
provenance is absent throughout the system. Its remaining limitation is absence
of exact factor-method/input/fallback/normalizer closure and economic use
assessment, not absence of every code or source reference.

## Minimum future boundary, with no activation

Reuse the existing inactive ref shape (`id/version/sha256/locator`) and source
semantic hash. A producer-side assessment owns method identity, context,
applicability, admission, numeric trace, completeness and scoring validity.
The consumer consumes exact result/assessment references under a separately
authorized purpose/version/namespace/cohort policy. It does not rescore factors.

The narrow persisted integration point is after existing record/identity/hash/PIT
validation and **before** `leaderboard_producer/rank.py:226` constructs the
mechanical PASS cohort. An eventual sanctioned direct ranking API needs the same
admission reference. Export/research display should carry both admitted and
withheld inventory plus upstream rejection/assessment refs, preserving original
scope rather than inferring validity from rank or an absent marker.

Unavailable assessments remain explicit UNASSESSED/legacy references with
reasons, not default true. No exact cutoff, coverage number, all-factor rule,
ranking ban, N/A predicate or validity criterion is chosen here. Cohort adoption
may change ranking without changing a scalar and is therefore D3 migration.

Current source already preserves raw input hashes, snapshot identity, coarse
versions, weight hash, selected availability times and provisional research
state. Those guards remain useful. Method admission is an additional upstream
assessment boundary, not a reason to duplicate growth/valuation logic in the
Leaderboard or browser.

## B1 and next executable evidence

B1 remains MORE_EVIDENCE_REQUIRED. No factor role changed. The G/V method
manifests should provide exact source/hash, raw units/periods, input availability,
selected branch, normalization, scope and unresolved economic meaning. They can
reference this transport matrix without equating source support with semantic
authority or requiredness.

Next independent D1/D2 task: compare the accepted G/V descriptor manifest hashes
against the minimal producer-result and consumer/P01 assessment-reference
requirements above, with scope-preserving reject/unassessed traces. Method
selection, factor requirements and actual ranking/publication activation remain
D3. Manual Work contributes **0 scheduler hops**, preserving **0/2 UNVERIFIED**
until independent real scheduler receipts establish otherwise.
