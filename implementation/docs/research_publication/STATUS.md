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
