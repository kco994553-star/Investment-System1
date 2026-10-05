# Independent negative findings and bounded repairs

Historical failures are preserved here. These were found in the new uncommitted synthetic harness; no existing owner/Frozen source was changed.

| ID | Independent reproduced pre-repair behavior | Bounded repair / required retest |
|---|---|---|
| PP-F01 | Callable connector `.trade` passed service admission; synthetic sync returned SUCCEEDED | Reject expanded trade/order/funds method aliases at admission and each read; direct API trade paths absent |
| PP-F02 | Unknown `client_secret` envelope key caused SCHEMA_REJECTED after raw was persisted, retaining plaintext marker | Reject credential/token/secret-like keys recursively before raw persistence; closed normalized schema unchanged |
| PP-F03 | Provider-side revoke rejected new sync, but persisted connection stayed ACTIVE and prior portfolio had no revoked/stale flag | Observe provider revocation at connector access and portfolio read, persist REVOKED; retained snapshot becomes STALE; no deletion |
| PP-F04 | Empty positions response marked STALE lost metadata; balance=250 yielded DEMO/reconciled analytics | Preserve every resource envelope, including empty pages; stale/delayed suppress analytics; retain raw refs for empty resources |
| PP-F05 | Replaying month-old provider values set portfolio as_of to new sync time | as_of derives from financial source effective time; sync_completed_at is separate; mixed source times are NOT_COMPARABLE |
| PP-F06 | Unsupported negative synthetic quantity could produce normal calculated weights | Preserve source record but withhold long-fixture analytics when direction is unsupported/inconsistent; no real short-selling numeric policy adopted |
| PP-F07 | Application append-only writes did not detect direct normalized/snapshot byte tampering | Add scoped content hashes and verify them plus raw receipt hashes on read; these hashes are corruption detection, not an external authenticated tamper-proof ledger |
| PP-F08 | Existing Decimal context can round large-source totals; unary negation before exact reconciliation can also round | Use context-free copy_negate in exact source comparison; withhold existing analytics if inherited context cannot represent source sum exactly; preserve source precision |
| PP-F09 | Unknown `passcode` and Unicode-confusable credential keys escaped a keyword-only secret detector and persisted raw before normalization failed | Validate closed resource/envelope shape before raw persistence; malformed/unknown keys fail closed; durable negative tests |
| PP-F10 | A historical portfolio response exposed a sync attempt completed after its decision time | Scope last-run visibility to decision time; hide future-started runs and mask future completion/error as RUNNING |
| PP-F11 | Incomplete intermediate pagination page followed by a complete terminal page promoted the resource group to success | Completeness is independent of next_cursor; any incomplete page keeps run PARTIAL and prevents snapshot/cursor commit |
| PP-F12 | API outer envelope remained DEMO for revoked retained data although domain portfolio was STALE | Propagate effective data_state/connection_state/last_sync/as_of for portfolio/export/current resources without rewriting original row provenance |
| PP-F13 | Raw receipt resource/connection anchor could be relabelled without changing body SHA; portfolio still produced analytics | Recompute scoped receipt ID from user, tenant, connection, resource and body digest; anchor tamper returns PROVENANCE_FAILED |
| PP-F14 | Snapshot available_at tampering into the future could skip corrupted data before verification | Validate snapshot content/ownership/time hash before availability filtering; past/future tamper denied |
| PP-F15 | Python HTTP parser canonicalized raw `//api/me` before the handler's path check | Inspect original request target from requestline; raw doubled-slash variants return404 while normal authorized request remains200 |

Lower-revision replay after a correction is deliberately rejected as REVISION_REGRESSION, retaining all prior revisions/raw and the last good snapshot. Equal-revision different content is REVISION_COLLISION. Replaying identical current revision is idempotent. Complete resource membership controls current positions; historical absence never erases the record ledger.

The earlier auth test checkpoint had 12 PASS, then 14 PASS after concurrency/rate-key coverage; connector had 8 then 9 PASS. Final consolidated counts belong to the final evidence receipt, not these intermediate checks. Independent final review ran 81/81 before three durable storage/history regression cases were added. Seven separate final adversarial probes passed. Existing canonical regression completed 396/396 with the repository mini_pytest shim (not pytest).

External limitation: production provider authentication, secrets vault/encryption/retention, real broker schema, background scheduler, production ChartDocument and owner-admitted Web integration have not been verified. No finding is suppressed by declaring those capabilities ready.
