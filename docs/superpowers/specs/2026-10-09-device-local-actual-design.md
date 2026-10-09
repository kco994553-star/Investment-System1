# Device-only ACTUAL cockpit

Authority: user's explicit 26E decision on 2026-10-09, responding to the
2026-10-08 request. The source decision is append-only in Global CDR-042.
This specification carries the user's approved implementation requirements;
an extra implementation approval is not a prerequisite. READ_ONLY remains.

The existing static cockpit gains a Portfolio link to a 19-instrument ACTUAL
entry view. A separate browser module owns IndexedDB, validation, backup,
deletion and supplied-price arithmetic. The static builder publishes only the
existing A-S2 identity and TARGET metadata, never device holdings. The module
accepts public metadata as arguments and performs no network calls.

Save is explicit and atomic. Quantities/average costs are nonnegative decimal
strings, currencies USD/JPY/KRW. Unknown or duplicate identities, nonfinite
values, incorrect versions/hashes and invalid clocks fail closed. IndexedDB
errors never claim successful persistence. Import replaces after validation
and user confirmation; invalid import preserves existing records. No user
values are sent to logging, shared producer snapshots or localStorage.

The JSON envelope mirrors TARGET's owner/version/effective_at/available_at
and themes/holdings structure. It uses schema device-actual-holdings/1,
kind ACTUAL, ownership USER_DEVICE_ONLY, owner.role USER and owner.storage
USER_DEVICE_ONLY; target_root_version/target_root_sha256 and
identity_map_version/identity_map_sha256 pin public source metadata. Holdings
carry exact A-S2 security_reference, quantity, average_cost and currency.
Versions advance on each save. Export is a local browser download. Deletion
clears the IndexedDB record; previously exported device files remain user's
responsibility, stated in the UI.

Valuation uses quantity times a supplied same-identity/same-currency market
price with explicit as_of/available_at, never average cost. The current
cockpit has no accepted market-price route, so those values remain
NOT_AVAILABLE. Arithmetic helpers support future supplied prices without
fetching them. Total value/weight/TARGET delta require complete comparable
prices; mixed currencies require an existing FX contract, absent here, so
global totals/weights/deltas remain unavailable. No subset normalization,
broker connection, new score or investment methodology is introduced.

The existing repository guard scans tracked payloads for populated device
ACTUAL export/holding shapes and rejects them without logging values.
Synthetic tests construct data in memory or temporary directories, never
commit populated exports. Original Frozen/history/TARGET/mode bytes stay intact.

Verification covers 390px ko/en input, save, refresh, export, delete, import,
invalid-import preservation, unavailable prices, independent storage contexts,
network egress observation and IndexedDB failure. Public deployment requires
a separate user approval after an empty-build/privacy verification; this work
produces a reviewed PR, not a public deployment. PR67 is a separate explicitly
approved canonical merge with deployment-linkage and FPIA fallback conditions.
