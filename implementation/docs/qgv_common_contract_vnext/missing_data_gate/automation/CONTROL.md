# QGV Work automatic continuation control

Owner-scoped coordination infrastructure only; no QGV runtime/domain policy.

| Automation | ID | Confirmed setup |
|---|---|---|
| QGV Work 자동 재개 | `6ac2f22087288191abd144fb4a7655f8` | Webhook create/update SUCCESS, enabled |
| QGV CI 후속 확인 | `6ac2efbd34fc8191a60dccbbe338c291` | Separate hourly condition watch, enabled |

Both target conversation `6ac230f1-0ff0-83ee-a932-45244e2c4afe`.
Accepted setup is **not real event delivery: NOT_TESTED**. Inventory confirms
enabled/chat state but does not expose trigger readback. Submitted triggers are
preserved in the setup receipt. No artificial event or GitHub comment was sent.

## Owner, input and event boundary

Repository: `kco994553-star/Investment-System1`.
Only write `codex/qgv-missing-data-decision-gate-2026-10-05` and this
`missing_data_gate/` directory. Owner Phase B PR is unresolved/null;
do not invent a number. PR #44 is the inherited contract input and PR #42 the
direct integration-compatibility input, both read-only. Once an actual owner PR
exists, add only its exact number to the same webhook's complete trigger set.
No duplicate watcher or unrelated PR subscription.

Exact #44/#42 filters enable commit updates, submitted human reviews, newly
created human conversation/inline comments and closed/merge; opened and
ready-for-review are also supported. Edited/deleted comments/reviews, non-PR
issues and Actions completion are not webhook event families. Pending CI uses
the separate watch; no pending record means no-op, not a new test/publication.

Fresh-read canonical, latest integration, Global/scoped Handoffs and approvals
before acting. Global files are Claude/Primary Integration Writer's single-writer
scope. Reviews/comments/merge do not independently grant M1-M5 authority.
PR #42 comment 5986162506 was a Chart handoff: **NO_ACTION** for this Work.

## State, exclusion and idempotency

`STATE.json` starts with no lease/pending run/test. Seed HEADs/event IDs are
observations with dispositions, not fabricated webhook deliveries. Receipts
are additive. Use repository+PR+event family+delivery/review/comment ID+HEAD;
for CI use run ID+attempt+conclusion. HEAD/timestamp alone misses distinct events.

Prefer read-only CI polling. Every mutation (also receipts/handoff) needs the
same owner lease: read latest HEAD, prepare a sibling commit recording
RUNNING+unique run token+input fingerprint, update ref with `force:false`.
One competing sibling can advance; the other is non-fast-forward and must stop.
Re-read remote lease token after claim and before every later mutation.
This is optimistic git-ref exclusion, **not a scheduler mutex**. Lost ownership
means discard cached writes, never rebase them onto another token. If durable
state/safe ref updates are unavailable, remain read-only. No invented expiry
or stale-lease takeover: prove the prior run ended or report recovery needed.
Release on completion/failure/approval wait/external-CI wait; record pending
IDs instead of holding a lease while waiting for CI.

Compare semantic source hashes/paths, not just actor names: connector commits
can be attributed to humans. Exclude `automation/` from semantic fingerprint.
Own setup/lease/receipt-only updates must not resume semantic work. Do not
commit 'no change' receipts. Do not queue CI or recursively record CI generated
only by state commits: QGV push trigger currently covers only #44's branch,
but its PR path filter covers these docs once a Phase B PR exists. Otherwise a
CI receipt can create a CI-to-receipt-to-CI loop. Genuine pending runs retain
their original HEAD/attempt. An ancestor/content-equivalent PASS is **not**
exact-current-HEAD Actions PASS.

Advance watermark only after SUCCESS, NO_ACTION or WAITING_FOR_APPROVAL.
Fresh-read uncertain publications before retry. A policy/material blocker
holds only dependent work; independently approved audit/evidence can continue.

## Approval and stop boundary

M1-M5 are RECOMMENDED, NOT_APPROVED, INACTIVE. Production Missing-Data
implementation is not authorized. No production Q/G/V, factor meaning/weight,
G/FCF, V, composite, runtime WeightOverride, PIT admission, Official/Personal
boundary, Leaderboard/TrackRecord, Frozen history, Holdout, canonical or other
owner branch changes. No PR #44 merge, scoring threshold/default, grant or paid
purchase. Stop for processed/irrelevant input or completed approved scope.
Report only meaningful new results/blockers/minimal decisions to this chat.
