# PROPOSAL P02 — Universe between Official as_of dates (analysis only)

Status: **D3-P REQUIRED / NOT DECIDED / NOT IMPLEMENTED**. This affects results. The infrastructure does not choose.

## Facts
- The Official Universe exists only for 2024-06-30, 2024-09-30 and 2024-12-31 (Track A FROZEN_VERIFIED).
- Each new Official as_of needs:
  - an N-PORT fund-quarter-end reference, public about two months after quarter end;
  - a gate chain run with Promotion Gate v2 and sufficiency checks;
  - CA-UNIT reconciliation, which may raise new D3-C cases.
- The infrastructure publishes the Universe only as `FROZEN_SNAPSHOT`. It keeps `requested_as_of` (today) separate from the actual `as_of` (2024-12-31), so the gap is visible.

## Options (not implemented)
| Option | Effect | Risk |
|---|---|---|
| Last-known Official carry-forward | Reuse latest Official membership until the next one | Membership drift and survivorship between dates. Needs a maximum allowed staleness |
| Quarterly-only | Daily outputs reference only the latest Official date | Simple and PIT-clean, but up to ~5 months stale |
| Daily market-cap reconstruction | Recompute the top 500 daily from PIT shares × daily price | Bypasses the reference/sufficiency gates and CA review cadence. Large policy surface |
| Interpolation / hybrid | Carry-forward plus daily delisting/CA exclusions | New rules for eligibility and corporate actions |
| Allowed-staleness window | Any of the above, plus a limit after which the Universe is NOT_USABLE | Needs a number, which is a policy choice |

Decision needed from the user (D3-P): which option to use and the allowed staleness. Until then, the Universe stays FROZEN_SNAPSHOT 2024-12-31.
