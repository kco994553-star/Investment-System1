# G3 read-only triage — approved-policy adapter path

Three triage criteria are complete. At exact source HEAD
`675d0d298fbaab5b8473ed048a561ef84e2f3e78`, an isolated hand-built TEST VECTOR with
schema-1 qgv state LIVE and methodology status PROVISIONAL_RESEARCH passes the
unchanged Frozen validator/builder. Actual mobile Chromium displays LIVE and 11.11.
The existing producer validator rejects the equivalent methodology and state with
ResearchStatusError. No producer/engine/real-data API was called; browser requests
were fulfilled from isolated local files. The original app bytes are unchanged.

The initial GIE-006 head 6cd7eee was superseded during fresh fetch by exact Global
HEAD `5fafee22ae4c1d246b6f2ef1f3d870344d7627c4`. Both GIE-006 evidence blobs remain
identical, so G3 is CURRENT. The Global routing paragraph still calling that audit
pending is stale routing text; it cannot override exact evidence or scoped policy.
Owner branch heads #5/#6/#9/#17/#19 remain unchanged in fresh GitHub observations.
No new Web source writer appears in the observed PR/branch topology. Active session
availability cannot be established from GitHub alone; coordination still reserves
all old owner branches as read-only upstream.

## Binding authority and preservation

- Treat scoped M1/M2 FROZEN as binding even though overall status is FREEZE_READY.
  No original Web source, asset, test, contract, phase status or historical manifest
  is editable in this cycle. An absent byte pin does not authorize app.js edits.
- P01's protected digest explicitly includes product/web_mvp.py. Its pin remains.
  GIE's separate claim that test_web_mvp.py line75 is a byte pin is inaccurate:
  that line is an AST import boundary check. This does not weaken Frozen authority.
- Current P01 approval was recorded 2026-10-02T17:08:01+09:00. Research display,
  Frozen and Live grants remain NONE. Approved P01-H keeps schema-1 unchanged and
  prevents research bytes being relabelled LIVE/FROZEN_SNAPSHOT/DEMO.
- The existing producer rule is exact: published states LIVE/FROZEN_SNAPSHOT reject
  methodology.status in IDEA, RESEARCH, PROVISIONAL, PROVISIONAL_INITIAL_PRIOR or
  PROVISIONAL_RESEARCH. No new research taxonomy, normalization, threshold, grant,
  schema state, score/rank/regime/zone/action computation is required.
- The user's current Production-shaped Integration UI authorization permits new
  presentation/adapter admission guards. It does not unfreeze the old v1. A new
  isolated adapter applies already-approved producer policy; no Frozen contract
  change is necessary. If implementation requires editing old v1 files, stop that
  path as USER_DECISION_REQUIRED and continue independent READY work.

## Smallest permitted implementation

1. Add a new tool/importable adapter outside Frozen product modules:
   `implementation/tools/build_production_web_integration.py`.
2. Read the existing producer contract constants PUBLISHED_STATES and
   RESEARCH_STATUSES. Run the unchanged Web validator, then reject an explicitly
   research methodology on a published schema-1 section using the existing error
   class. Handle the schema-1 direct methodology shape reproduced by GIE and the
   actual assembler's `section.producer.methodology` metadata shape. Reject if
   either explicit status violates the existing rule; do not invent a fallback.
   Do not recursively interpret arbitrary numeric/data fields as methodology.
3. Admit or reject without modifying the raw bundle. Only after admission call
   the unchanged Frozen builder into a dedicated new integration output directory.
   All old v1 source and existing output directories remain untouched. Rejection
   writes no partial production output. This is a guard, not research rendering.
4. Add only new scoped tests/evidence. Test both published states against all five
   exact existing research statuses and both metadata locations; valid current
   NOT_AVAILABLE/DEMO/Frozen-Universe bundles must preserve complete bytes and
   original values. Check raw-input immutability, no builder call/output on denial,
   no recomputation, protected bytes and original tests.

This minimal adapter closes admission on the NEW production integration entrypoint.
It does not claim to repair, rewrite or retire the historic v1 CLI/app bypass.
Operators must use the new admitted integration path for the new scope.

## Optional browser boundary, still additive

A new JS guard may live outside Frozen web_assets, for example
`implementation/tools/web_production_admission_guard.js`. A NEW derived integration
entrypoint can load it before the byte-identical Frozen app. Keep the original
copied index/app and legacy output path unchanged. Export the exact existing
producer status/state constants through the adapter, not independent JS policy.

The guard can inspect each received data.json Response clone before making its
original body available to the Frozen app; a rejected explicit research/published
combination throws into its existing unavailable/retry path. This binds admission
to the actual response and avoids a check-then-second-fetch bypass. It returns
valid original bytes unchanged. It does not recalculate values, change state,
render research, or grant publication. Browser negatives should cover direct and
nested metadata, a bad replacement response after reload, unchanged admitted bytes
and the existing unavailable/retry behavior.

No production guard implementation has been written during this triage. A wrapper
only path is the smallest permitted first cycle; the additive browser boundary can
be included only with a clearly named new integration entrypoint and unchanged old
Frozen assets. New source paths are disjoint from root's F1 compatibility repair,
all Track C work, all shared Global files and active owner branches.

BRANCH_STATE: exact source675d read-only; no worker implementation branch created.
INTEGRATION_STATE: G3 reproduced; additive adapter path READY, not implemented.
CANONICAL_STATE: unchanged.
Actual Actions for G3: NOT_RUN. CAL_VERIFY/Holdout: NOT_RUN. Grants issued: zero.
