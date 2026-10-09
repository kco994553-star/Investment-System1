# Google Sheet quotes verification — 2026-10-09

Base: `011b75648f48f2890736d37c4a354f57004cf1f0` on the requested canonical branch.
Work branch: `codex/google-sheet-quotes-20261009`. Merge requires user approval.

## Local verification

| Check | Result |
| --- | --- |
| Full Python regression | 855 tests + 345 subtests PASS |
| Node: existing holdings / existing market / sheet core / memory authentication | 17 / 34 / 21 / 8 PASS |
| Browser: Pages / legacy holdings / manual prices / sheet import / atomic import storage | 10 / 40 / 119 / 32 / 13 checks PASS |
| Additional independent four-width/locale integration | 36 checks PASS |
| Directory and normalized raw Pages tar | 16 files PASS |
| Public data hashes | `data.json`, `entities.json`, `actual-catalog.json` unchanged from base |
| Repository privacy / immutable history / READ_ONLY guard | PASS; no mode change |
| Independent code review | No remaining critical or important finding |

The browser combinations are 390px and 1280px, ko-KR and en-US. All Google
script, Sheets, and revoke responses are mocked. Unexpected external requests,
runtime errors and private console output are zero. Filled screenshots and
payload files are never created. Existing Pages/manual screenshots use fresh
empty device contexts. Test evidence stays outside the public site and repository.

The privacy review identified escaped JSON URL/token and JavaScript ID assignment
gaps. Dynamic in-memory regression tests reproduce these cases, and the updated
guard rejects them while preserving public OAuth configuration and hash handling.
No guard bypass or fixture waiver was added.

## Limits of verification

Real Google OAuth, the actual GIS runtime under the exact requested CSP, account
access and mobile popup behavior require the user’s own private account/device.
CI must not make live Google requests; PR Checks record native CI separately.
TYO:8035 remains manual when GOOGLEFINANCE returns NOT_AVAILABLE.

Minor reviewed caveat: disconnect after the atomic write enqueue boundary may
commit the already accepted batch while clearing the token. Its result summary
and history refresh on re-entering settings. Cancellation before that boundary
preserves market data/history. Stored import history is capped at 1,000 batches;
at the limit a new save fails without overwriting observations.
