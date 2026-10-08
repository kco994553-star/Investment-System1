# Scoped handoff: QGV Common Contract vNext

**STATUS: INACTIVE / SPEC-ONLY · CURRENT PHASE COMPLETE**

Owner branch: `codex/qgv-common-contract-vnext-spec-2026-10-04`.
Base/canonical: `b8e39a2196a6d7794a04a0cd5393c68329e126ca`.
Read-only integration comparison: `acaf1b5a82859ac2750a130ebe88f8b4d272ac66`.
Delivery commit is the commit containing this scoped package; resolve exact SHA
from the branch/PR, not a mutable short-name assertion. Remote CI state is recorded
in GitHub Actions on that exact SHA; at authoring, the new workflow is NOT_RUN.

No changes to existing tracked source/tests/fixtures/history/Frozen artifacts;
only this docs directory, one new audit tool, one new test module and one dedicated
workflow are added. Other owner branches and Global handoff remain read-only.

## Read order

1. evidence/baseline.json: fresh pins and 33 source fingerprints.
2. AUDIT.md: 10 hypotheses, architecture, full KEEP/ALIGN/CHANGE matrix,
   missing-data comparison, G/V audits, downstream effects and decision queue.
3. CONTRACT.md: inactive shared contract and planned reuse/binding boundaries.
4. current_factor_map.json: exact current 20-factor/weight/candidate inventory.
5. COMPATIBILITY.md: equivalence, intentional-delta and migration gates.
6. contract_record.schema.json + contract_record.example.json: inactive sidecar
   shape, not a production score schema or runtime request.
7. golden_cases.json and evidence/: reproducible neutral verification.

## Local validation actually run

| Gate | Result | Evidence |
|---|---|---|
| Existing initial targeted modules | 32 PASS, pytest | evidence/existing_targeted.txt |
| Expanded QGV targeted set incl. V prior/G horizon | 39 PASS, pytest | evidence/existing_targeted_final.txt |
| Baseline full regression before new tests | 396 PASS, pytest | evidence/baseline_full.txt |
| New contract/characterization/isolation/provenance tests | 92 PASS, pytest | evidence/contract_targeted.txt |
| Exact golden semantic replay | 71 cases PASS | evidence/golden_verification.json |
| Existing + additive full regression | 488 PASS, pytest | evidence/final_full.txt |
| New neutral checks on #40 tree with scoped files overlaid | 92 PASS, pytest | evidence/integration_neutral_overlay.txt |
| Source/old tracked file preservation | no pre-existing tracked file change | Git diff against canonical; baseline manifest |
| Real-data PIT/OOS, CAL_VERIFY, Holdout | NOT_RUN | no access/execution in this phase |

Environment: Python 3.12 (full version in baseline.json), pytest 9.1.1,
jsonschema 4.26.0. These are test-only dependencies, not production additions.
First new-test attempt had 1 failure (naive time was accepted by optional format
validation) and 89 passes. The audit-only validator now explicitly rejects naive
times; original failed log is preserved, and final 92 checks pass. No production
time or score implementation was changed to make this pass.

Integration check is a **synthetic neutral overlay**, not a merge or full #40
regression/Track C acceptance. No historical golden output was regenerated after
the tests were written. Existing fixture expectations were not modified.

Commands (from implementation, with pytest/jsonschema installed):

```
PYTHONPATH=src:. python -m pytest -q tests/test_analysis_scoring.py tests/test_v_prior_and_c15.py tests/test_g_horizon.py tests/test_raw_and_providers.py tests/test_pil_p0_contracts.py tests/test_product_strategy_validation.py
PYTHONPATH=src:. python -m pytest -q tests/test_qgv_common_contract_vnext.py
PYTHONPATH=src:. python tools/qgv_contract_audit.py --verify
PYTHONPATH=src:. python -m pytest -q
```

## Progress semantics

This phase's design delivery progress is **100% (10/10 stop criteria)**:
current mapping; hypothesis recheck; classification; inactive common contract;
Official/Custom isolation specification; missing comparison; compatibility;
golden accidental-change detection; approval separation; legacy preservation.

vNext **production-runtime implementation progress is 0% by explicit scope**:
no runtime schema migration, new scoring/aggregation, WeightOverride wiring,
composite change or operational migration has begun. Audit tooling/schema/tests
for this phase are implemented and verified. This is not “all existing QGV code
is 0% complete”. Whole QGV-system design/implementation percentages cannot be
honestly calculated from a fixed, approved total-scope denominator in the current
repository; they remain NOT_ESTIMABLE rather than an invented blended percentage.
Analysis, Simulation, Portfolio, Leaderboard and TrackRecord have existing code;
factor coverage, personal wiring, method validation and operational promotion are
different dimensions, not equivalent to counts of tests or commits.

## Isolation and approval boundary

LEGACY SCORE CHANGED: NO.
OFFICIAL/CUSTOM ISOLATION: PASS for the existing boundary and synthetic immutable
objects. Future runtime request/cache/storage/publication isolation: NOT_TESTED,
because runtime wiring is expressly prohibited in this phase.
PIT/OOS: NOT_RUN (synthetic contract/entrypoint probes are not real PIT/OOS).

No blocker remains for the current spec-only deliverables. Migration blockers:
QCC-P01 missing/N.A. policy; QCC-P02 validation/PIT admission; QCC-P03 G meaning and
fallback; QCC-P04 V normalization/metadata methods; QCC-P05 composite/editability/
binding; C-24/C-30 maturity/config references. Full original methodology authority
crosswalk and real data coverage/validation remain unresolved.

All QCC-P IDs are local PROPOSED / NOT APPROVED / NOT ACTIVE proposals. They do not
rename approved global decisions. Canonical merge, Official/publication grants,
CAL_VERIFY/Holdout and history changes are not authorized.

Recommended next **single** step: review a policy-only QCC-P01 decision package
using the preserved missing/N.A. counterexamples, without runtime migration.
Do not start that migration from this handoff. The user's stop condition is met.

BRANCH_STATE: scoped spec/test package complete; commit/push/CI status must be
read at exact remote SHA. INTEGRATION_STATE: neutral #40 overlay verified only.
CANONICAL_STATE: unchanged b8e39a2; unmerged proposal.
