# 26E — ACTUAL input method

Question: Which source should provide actual holdings?

| Choice | Cost | Relative effort | Risk | Reversibility |
|---|---|---|---|---|
| User-maintained holdings file (recommended) | No external-service charge | Shortest | Manual staleness and entry validation | Preserve source/history, change adapter later |
| CSV upload | No external-service charge | Medium | Broker formats, duplicate rows, currencies, private-account data | Preserve original files, change adapter later |
| Broker integration | Provider-dependent; unconfirmed | Longest/provider-dependent | Credentials, permissions, API outages, provider data retention | Disconnect locally; provider-side effects need verification |

Recommendation: file-first, grounded in v1.1 section8 proportional verification, section26D rollback and section26E. No delivery-date promise is made before source shape and required fields are selected.

WAIT lane: ACTUAL implementation. Continuing lanes: identity mapping, candidate construction and independent verification. Deadline: none. The decision was requested once in the active user session; no timeout is approval.
