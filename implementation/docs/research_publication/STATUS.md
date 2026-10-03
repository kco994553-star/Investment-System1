# P01 Research Publication — Status

**State: IMPLEMENTATION BASELINE / INTEGRATION WAIT**

| Item | Value |
|---|---|
| Policy | APPROVED / ACTIVE_POLICY at `f8af596` (`P01_APPROVAL_2026-10-02.md`) |
| Branch | `feature/p01-research-publication-v1` stacked on `feature/producer-infrastructure-v1`. Not merged |
| Base | PR #9. Not canonical |

## Verdicts

| Verdict | Value |
|---|---|
| P01_IMPLEMENTATION_READY | **YES** for the phase-1 predicate, extractors, envelope, and schema-1 compatibility |
| PUBLICATION_PREDICATE_READY | **YES**. One predicate. No producer-name branch |
| LEGACY_COMPATIBLE | **YES**. schema-1 `STATES` unchanged. `schema_version` 1. Section `data` not rewritten |
| RESEARCH_DISPLAY_ACTIVE | **NO** |
| Research-display grant | **NONE** |
| Frozen grant | **NONE** |
| Live grant | **NONE** |
| QGV / Macro / Leaderboard / Technical schema-1 state | **NOT_AVAILABLE** |

`DISPLAY_RESEARCH` is not enabled. Official, Live, Frozen, and Validated are not issued.

## Not done

No research-display grant is issued. No producer section is switched on.
Track C is not read. Holdout is not consumed. Canonical is not the base.
Real persisted batches from PR #10, #12, #14, and #15 are not vendored into this branch; the extractors accept their document shapes when those bytes are supplied.

## Additive note 2026-10-03 — C-28 adoption re-pin (user CDR-004)

This section is appended; nothing above it is rewritten. Prepared by the Primary Integration Writer under user CDR-004 2026-10-03; it becomes the owner's adoption when merged into `feature/p01-research-publication-v1` by the owner or the user.

| Item | Value |
|---|---|
| Authority | User CDR-004 2026-10-03: IF-1 approved as A1 + Technical/Macro owner adoption; Track C `2137883` additive lineage/schema change kept as integration target; Technical aligned with canonical C-28 (Contract Conflict Register 2026-09-23, L348-353: upstream PATCH adds `available_at` from input data stamps); Macro recorded as a separate current owner adoption, not retroactive. Not an approval to change any formula, value, regime, zone, Macro state, QGV or ranking |
| Gate | Independent before/after comparison, recorded before any pin edit: `evidence/c28_adoption_invariance_2026-10-03.json`. BEFORE `21039a0` vs AFTER `21039a0` + Track C owner tip `b9e01a97` (`--no-ff`, 0 conflicts, throwaway `ccdbd036`). Verdict **PASS**: the fingerprint tool's own `norm()` output differs only by the four added keys `available_at=null`, `data_stamp_refs=[]`, `source_vintages=[]`, `input_hash=null` on the 19 technical and 4 macro snapshots; qgv/leaderboard/portfolio fingerprints unchanged; publication predicate/extractor/envelope outputs on this PR's fixtures byte-identical (same sha256) |
| Pins (state-exact, history-preserving) | `tests/test_p01_research_publication.py`: `FINGERPRINTS_PRE_ADOPTION` (macro `7bbfad69…`, technical `82165414…`) and `PROTECTED_DIGEST_PRE_ADOPTION` `1d6c56e4…` kept verbatim as the pre-adoption pins (origin PR #17 @ `21039a0`, 2026-10-02). Added `FINGERPRINTS_C28_ADOPTED` (macro `7e427949…`, technical `66cb2383…`) and `PROTECTED_DIGEST_C28_ADOPTED` `e6de4671…`, reason "C-28 upstream adoption of Track C 2137883 per user CDR-004 2026-10-03". `_c28_adoption_state()` selects exactly one pin from the adopted feature itself (lineage fields on `TechnicalSnapshot`/`MacroSnapshot`, `evaluate_stamped` on both engines); a partial state raises; a detected-state/bytes mismatch still fails. No key stripped from the fingerprint (A2 not approved). No "either value accepted" |
| Historical evidence | `evidence/invariance.json` kept verbatim (its `fingerprint_before` and `protected_digest` are the pre-adoption values). Post-adoption values live only in the additive `evidence/c28_adoption_invariance_2026-10-03.json`. `docs/producer_infrastructure/evidence/validation.json` belongs to PR #9 (`f8af596`) and is untouched |
| Verification on this proposal branch alone (pre-adoption state) | pytest full suite: 444 passed (same count as PR #17 pre-change). `tools/mini_pytest.py` (the PR's Actions runner): 444 passed, 0 failed. P01 file: 13 passed (both runners) |
| Verification in throwaway tree = proposal + Track C owner tip `b9e01a97` (adopted state) | merge `--no-ff` 0 conflicts (throwaway `56cbc9e3`, not pushed). `tests/test_p01_research_publication.py`: 13 passed (pytest and shim); `_c28_adoption_state()` = True; observed fingerprint == `FINGERPRINTS_C28_ADOPTED`, != pre-adoption |
| Negative checks (throwaway) | partial state (technical/engine.py reverted to canonical, macro adopted): both pin tests fail with "partial C-28 adoption state is not a pinned state". Adopted state with one comment byte appended to macro/engine.py: protected-digest test fails, fingerprint test passes |
| GitHub Actions | NOT_RUN for this proposal branch at the time of writing |
| Not changed | Technical/Macro formulas, values, regime, zone, Macro state, QGV, ranking; any file under `implementation/src`; dependency-not-merged sentinels and CI-mode `models.py` compare in #10/#14 (separate CDR-004 items); Track C Frozen chain; existing records above |
| Stacking | PR #19 (`c3dbf8a`) stacks on this branch, has no pins of its own, and inherits this re-pin; no change needed there |
| BRANCH_STATE | proposal branch `integration/a1-adoption/pr17-p01`, created from PR #17 tip `21039a0` |
| INTEGRATION_STATE | NOT_MERGED into `feature/p01-research-publication-v1`; Track C not merged into this branch |
| CANONICAL_STATE | NOT_MERGED |
