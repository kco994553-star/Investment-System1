# QGV invalidation binding — implementation contract

Policy already approved: AUTH-P1 through AUTH-P4, QGV composite subject option C, and INV-P1 through INV-P8, including the INV-P4 amendment that a current event must be the single head of one append-only supersedes chain. This file does not change those sentences.

Code: `src/investment_system/publication/invalidation.py` and `qgv_binding.py`.
Tests: `tests/test_qgv_invalidation_binding.py`.

## What this layer does

It copies persisted QGV company and batch-manifest fields, hashes them with the existing `producers.serialization.canonical_sha256`, and resolves `RESEARCH_INVALIDATION_EVENT_V1` chains. It does not recompute Q, G, V, rank, a subfactor, a peer median, or a cross-section. It does not issue a research-display, Frozen, or Live grant. `ACTIVE_AUTHORIZATIONS` stays empty. Publication stays `NOT_AVAILABLE`.

## Provenance

`producer_id` is the persisted literal `qgv.real_research_producer`. The web snapshot's reuse of `code_commit` as `producer_version` is not copied into the producer version. `qgv_system_version` and `code_commit` stay separate. `as_of` is the stored text; `Z` is not rewritten. `generated_at`, snapshot UUID, `run_id`, and the `SAMPLE`/`FULL` label are not provenance fields. A change to `code_commit` or to a bound lineage hash is a different subject even when the company semantic hash is unchanged.

The event target is the provenance hash, not the subject hash. The subject hash includes `invalidation_event_id`. Putting the subject hash inside the event would be circular.

## Currency

A composite is current-valid only when its bound event is the unique visible `CLEAR` head of the provenance target and no bound component hash has a visible non-`CLEAR` resolution. No event on `persisted_output_sha256`, `inputs_sha256`, `members_sha256`, or `weights_sha256` does not block the composite and is not component `CLEAR`. A component event can veto. A component `CLEAR` does not grant display.

`INVALID_CHAIN` covers a branching chain, multiple terminal heads, a cycle, a missing predecessor, a cross-target `supersedes`, a duplicate event, and any successor of `INVALIDATED`. The same effective instant on one otherwise valid chain is `AMBIGUOUS`. Timestamp order never chooses a head.

Replay includes an event only when `available_at <= decision_time`. A later `available_at` does not change the earlier result.

## Not in this layer

Leaderboard dependency, Macro withheld bytes, Technical eligibility, partial-disclosure copy, tie presentation, and TTL are not implemented. Freshness, authorization revoke, Track C `TrialStatus`, `QualityState`, `CoverageState`, `CalibrationLifecycle`, and the Technical invalidation string are not invalidation states.
