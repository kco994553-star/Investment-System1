# New owner branch: narrow read-only G3 check

Fresh-fetched `integration/web/production-state-presentation-v1` HEAD: `e91dc773af600ff66d31575ce3774490a0b0be8c`. Its exact sole parent and merge-base with the previously reviewed guard is `2b53b27fe0f570557159d02552911e9e1cc7be9c` (PR #34). The local Global routing ref remains `5fafee22ae4c1d246b6f2ef1f3d870344d7627c4`, GSI-007 “wf5 Web batch running”.

This is stacked, separate production-state presentation work: freshness badges, persisted unavailable metadata, ko/en labels and rendering-error fallback. It is not an evidenced supersession of PR #34. The commit message explicitly says G3-withheld sections are unchanged. The exact `researchMarker` function is byte-identical to PR #34 and still omits direct `section.methodology.status`.

Because app.js changed, only the existing narrowly targeted actual-browser probe was rerun against this exact head. Result: **STILL_REPRODUCED_PRESENTATION_CHILD**. A hand-built synthetic test vector with direct `qgv.methodology.status=PROVISIONAL_RESEARCH` still renders LIVE and QGV 11.11 in mobile Chromium. Zero page errors; zero external page requests; local files intercepted. The unchanged builder still admits the same original bundle. No real provider is invoked and no grant is issued.

The new commit changes five existing Web assets (`app.js`, `index.html`, `locale.js`, `network-bridge.js`, `style.css`) and adds four workflow/test/tool files. It adds no scoped docs, approval record, or Frozen supersession evidence. Existing builder, producer contract, and original tests are unchanged against its parent. The prior original-Web Frozen scope authority CONFLICT is not resolved by this commit; no permission is inferred from branch names or presentation labels.

Read-only inspection tasks: **3/3 completed with findings**. G3: **NOT_RESOLVED**. Full pytest, owner presentation E2E, Actions and production-state maturity acceptance are **NOT_RUN / NOT_CERTIFIED** by this observer. No owner edit, competing UI branch, upstream resolution, re-pin, push, dispatch, real-data access, canonical merge or deployment was performed. Earlier review files remain byte-identical.
