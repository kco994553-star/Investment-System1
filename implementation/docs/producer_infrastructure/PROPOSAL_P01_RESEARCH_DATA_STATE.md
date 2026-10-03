# PROPOSAL P01 — Web data state for research / provisional producer outputs

Status: **PROPOSED / NOT APPROVED / NOT IMPLEMENTED**. Nothing in the production contract changes until approval.

## Current state
- QGV can compute Q/G/V from real historical PIT data (Track A store). The cross-section selection rule is
  `PROVISIONAL_RESEARCH` (`validation/vertical_slice.RULE_STATUS`) with `official_selection=false`.
- Web schema-1 states are `LIVE`, `FROZEN_SNAPSHOT`, `DEMO`, `NOT_AVAILABLE`. None of them means "real data, research-grade, not validated".
- Producer Infrastructure v1 therefore blocks such output from `LIVE`/`FROZEN_SNAPSHOT` (`ResearchStatusError`).
  Research producers must publish `NOT_AVAILABLE`.

## Why a decision is needed
Without a state for it, real research outputs cannot reach the Web at all. If one were mislabelled `LIVE` or `FROZEN_SNAPSHOT`,
users would see unvalidated research as operational or official data.

## Options
| Option | Description | Compatibility impact |
|---|---|---|
| A. Keep blocked | Research output stays NOT_AVAILABLE until Track C validates/promotes | None. Web shows nothing for QGV |
| B. New state `RESEARCH` | Add `RESEARCH` to `web_mvp.STATES`; UI badge "연구용 · 검증 전" (research use · not yet validated); never counted as LIVE | Changes the schema-1 state set. app.js needs a badge style. Existing bundles stay valid |
| C. LIVE/FROZEN + mandatory research label field | Keep the state set; require `producer.methodology.status` to be shown prominently | Schema unchanged, but the meaning of LIVE becomes overloaded. **Not recommended** |
| D. DEMO reuse | Mark as DEMO | Wrong: DEMO means synthetic/fixture. **Rejected** |

Questions for the decision owner: A or B? If B, does RESEARCH need `expires_at` like LIVE? And which methodology statuses map to it?
Track C ownership of Official promotion is unaffected by any option.
