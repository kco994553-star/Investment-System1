# Common research publication — verification, not adoption

Verified 2026-10-02 against the live branch tips below. This file does not approve P01, does not add `RESEARCH` to Web schema-1, and does not change ranking, eligibility, tie-break, consensus, scenario, or reassessment thresholds.

The predicate is `leaderboard_producer/research_publication.py`. It is a probe. It is not a publisher. `track_c_attestation_accepted` is unconditionally false, so this branch cannot mint Track C or emit `LIVE`, `FROZEN_SNAPSHOT`, or `OFFICIAL`.

## Pins (read-only)

| Case | PR | Tip verified | Role |
|---|---|---|---|
| QGV | [#10](https://github.com/kco994553-star/Investment-System1/pull/10) | `5eec129ef81641f0bc11f5adbb43d0b2122ee24b` | `PROVISIONAL_RESEARCH`, producer PASS, READY 0, published `NOT_AVAILABLE` |
| Macro | [#12](https://github.com/kco994553-star/Investment-System1/pull/12) | `61d3352d5d68c7830e924f17613598ca79fcec6f` | lifecycle `PROVISIONAL`, numbers withheld, published `NOT_AVAILABLE` |
| Leaderboard | [#14](https://github.com/kco994553-star/Investment-System1/pull/14) | `1f6b2d2f020843b13222b66a3f9bce82cded5bef` | existing engine, within-tie `POLICY_BLOCKED`, published `NOT_AVAILABLE`. This is the producer handoff, not the probe commit `c38ea87e9d796f1f7b8e1c19c69aca6e12f06792` |
| Technical | [#15](https://github.com/kco994553-star/Investment-System1/pull/15) | `ce587040e7beb31b66a423eab6ca89767f2a2cf8` | M1/M2 research record. No `methodology.status`. `m1`/`m2` `APPROVED` is not Track C. `publish_web_research` raises. `REAL_TECHNICAL_RESEARCH_PRODUCER_READY` stays NO |

Track C tip observed the same day, not read and not treated as a result: `feature/track-c-evl@31e7aedaac4b7fb9c8058cd8bc5959a80db0e9a0`. The audit-time pin `885c673` in `AUDIT.md` is historical.

## Verdict

| Question | Answer |
|---|---|
| Can one predicate cover all four cases? | **Yes**, if the axes below stay separate. No producer-name switch |
| Is that predicate adopted into Producer Infrastructure? | **No.** P01 is not approved. PR #9 is not edited |
| QGV-only exception? | **Not introduced.** A gate that blocks only `PROVISIONAL_RESEARCH` would let Macro (`PROVISIONAL`) and Technical (no such token, research record still exists) through. The probe marks that gate non-compliant |
| `RESEARCH` added to schema-1? | **No.** Tests may enable a hypothetical label. That label is not `LIVE` and not `OFFICIAL` |

## Why data_state cannot be the validation or lifecycle state

These are different facts. The four cases already use them differently. Folding them into one field is how a research result becomes Live.

| Axis | What it is | What it is not | Seen on |
|---|---|---|---|
| `data_state` | What Web schema-1 may render: `LIVE`, `FROZEN_SNAPSHOT`, `DEMO`, `NOT_AVAILABLE` | Not coverage, not a lifecycle token, not Track C | All four publish `NOT_AVAILABLE` |
| `producer_validation` | Mechanical PASS / FAIL / NOT_RUN (persistence, PIT, lineage) | Not Track C, not "fully scored", not a buy | QGV, Macro, Leaderboard are PASS and still unpublished |
| `methodology_lifecycle` | Domain status, copied verbatim | Not a Web state. `PROVISIONAL_RESEARCH` is one member of the shared research set, not the only one | QGV and Leaderboard `PROVISIONAL_RESEARCH`. Macro `PROVISIONAL`. Technical has no status field |
| `track_c_validation` | External attestation | Not something a producer sets because its own check passed | All four `NOT_RUN`. Forged `{issuer: track_c}` is ignored |
| `data_completeness` | READY / PARTIAL / BLOCKED, a missing feature, scenario `NOT_AVAILABLE` | Not the Web state. Not filled to unlock publication | Leaderboard READY 0. Technical feature/scenario `NOT_AVAILABLE`. Macro snapshot is not a Web payload |
| Policy facts | Withheld bytes, within-tie `POLICY_BLOCKED`, exposure not approved | Not a new ranking rule | Leaderboard tie stays blocked under a hypothetical label. Macro and Technical stay `NOT_AVAILABLE` even if the label switch is on, because their bytes are withheld |

Technical is the sharp case. `NOT_AVAILABLE` on a feature or on M3 is completeness. `web_publication.status=BLOCKED` is publication. `m1:APPROVED` is a phase label. Those three must not be one enum. Reading `APPROVED` as Track C would skip validation. The probe rejects that with `COMPONENT_LABEL_IS_NOT_TRACK_C`.

## If a RESEARCH data state is added later

The hypothetical path (`research_state_enabled=True`) is test-only. It still cannot:

- set `official`, `live`, or `track_c_validated`
- treat producer PASS as Track C
- accept a self-issued Track C attestation
- rewrite `VALIDATED` plus a forged attestation into `LIVE` (`TRACK_C_REQUIRED`, then this probe still has no success path)
- turn `m1`/`m2` `APPROVED` into `FROZEN_SNAPSHOT`
- clear Leaderboard `within_tie_order=POLICY_BLOCKED`
- publish Macro or Technical numbers (`research_bytes_withheld`)
- mark synthetic bytes as research (DEMO only, and DEMO is not Live)

QGV and Leaderboard may receive the hypothetical label only because their cases are not withheld. The decision function does not read `producer_id`. Renaming either case to `qgv` or away from it does not change the result. That is the opposite of a QGV exception.

Adoption of the label remains P01, owned outside this PR. Until then `current_publication` returns `NOT_AVAILABLE` for every case.
