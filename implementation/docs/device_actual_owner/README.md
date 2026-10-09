# Device-only ACTUAL cockpit

Authorized by user26E, recorded verbatim in Global
[CDR-042/043](https://github.com/kco994553-star/Investment-System1/blob/0eb7ffd4c4207f6dcfa344f25f859d2cc1b852ad/implementation/docs/coordination/COORDINATION_DECISION_REGISTER.md).
PR67 was merged separately under its explicit substitute-acceptance condition.
This new ACTUAL implementation is a scoped reviewed PR. Public deployment
requires a separate user approval and contains no private device data.

Portfolio → ACTUAL opens19 reviewed A-S2 instrument rows. Enter quantity,
average cost and USD/JPY/KRW currency; blank numeric pairs exclude a row.
Explicit Save commits to this browser origin's IndexedDB only. There is no
account, server adapter, telemetry or holdings upload. The UI states that data
is stored only on this device. Browser storage can be cleared by the browser;
local JSON backups are the recovery path. A different browser/origin has a
separate empty store.

Export/import follows a user-owned versioned JSON structure with owner,
effective_at/available_at, exact TARGET and A-S2 version/hash pins and
themes/holdings. Schema is device-actual-holdings/1. Import validates before
asking to replace saved data; canceled/invalid imports preserve it. Older
backups can be explicitly restored with a new local revision/availability
clock. Deletion clears browser holdings; downloaded backup files remain on
the user's device and must be removed there separately. Corrupt or inaccessible
storage is reported without logging contents or claiming a successful save.

The static build emits only public19-instrument identity/TARGET metadata in
actual-catalog.json. Device holdings never enter data.json or shared producer
snapshots. Build input containing recognizable private holdings is rejected
before files are written. Public identity/TARGET/Theme source hashes are pinned.
The cockpit blocks external scripts and form submissions with a local-resource
Content Security Policy; module operations perform no network requests.

Market valuation uses supplied exact-identity, same-currency prices with
as_of/available_at, never average cost. This build has no accepted quotation
route, so market value, weight and TARGET difference remain NOT_AVAILABLE.
Missing prices or mixed currencies without an FX contract do not produce
subset-normalized weights. The arithmetic helper is tested with synthetic
quotes for the eventual supplied-price interface; no quote feed is activated.

Repository-guard rejects recognizable populated device ACTUAL JSON/YAML/CSV,
including renamed files, staged/tracked contents and committed-then-deleted
exports in the new comparison history. It logs generic findings only. It
does not exhaustively recognize arbitrary encoded/encrypted/binary exports.
Do not commit device backups. Synthetic tests generate holdings in memory or
temporary directories; browser tests write only result labels/counts, with no
screenshots, downloaded payload files or holdings values.

Verification commands (from repository root):

```sh
cd implementation
python -m pytest -q
python tools/autonomy_gate_a_guard.py diff --base origin/claude/investment-system-top500-validation-alrugm
cd ..
node implementation/tools/device_actual_node_test.js
```

Build with the existing Web builder, serve on localhost, then run
device_actual_browser_test.js with DEVICE_ACTUAL_URL pointing to /#actual and
DEVICE_ACTUAL_EVIDENCE_DIR pointing outside the source tree. The same browser
check runs in Web CI. It covers390pxko/en save/refresh/export/delete/import,
validation/confirmation/storage failures, isolated contexts and network egress.

READ_ONLY/Frozen/TARGET histories, QGV calculations and unattended automation
remain unchanged. Actual data was neither requested nor used for development.
