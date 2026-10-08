# Offline Target owner-return preflight

Use the existing v0.5 `TARGET_OWNER_ADMISSION_REQUEST.json` or a returned copy.
Fill only the existing `root_owner_return` and constituent `owner_return` slots;
preserve original observed fields, reference metadata and provenance. This
diagnostic is not a production schema or an admission/publication authority.
Changed authoritative source revisions need a separate owner receipt and bounded
reconciliation; this checker deliberately rejects changes to the current request.

```bash
python implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6/receipt_preflight.py \
  --repo . \
  --packet implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/lane-a/TARGET_OWNER_ADMISSION_REQUEST.json \
  --decision-time 2026-10-05T01:00:00+00:00
```

| Exit | Diagnostic meaning |
|---|---|
| 0 | INPUT_COMPLETE_UNAUTHENTICATED: candidate slots are internally consistent; all six production gates remain OPEN |
| 2 | INVALID: source mutation, malformed/conflicting input, invalid time or unresolved source pin |
| 3 | INCOMPLETE: owner input is absent; the preserved current request returns this |

Always inspect `production_readiness`, `open_gate_ids` and authentication markers.
Exit0 is not implementation readiness, source admission, a grant or display
permission. Claimed snapshot_hash is checked for lexical shape only; its adopted
preimage is not available. Source/evidence reference strings cannot authenticate
themselves. The tool never queries external services or writes source/owner data.

The numeric replay is exact Fraction-from-Decimal on original pinned authored
tokens, after immutable identity/hash checks. It is an offline oracle, not a
selected production Decimal context. No financial computation is placed in an
API, Web or MCP route. Diagnostic reference totals are marked non-renderable;
production_payload is always null and ACTUAL is always NOT_AVAILABLE.

`--output NEW_PATH` exclusively creates a new diagnostic file and refuses to
overwrite one. Missing original Git objects fail closed without a current-source
fallback. Use an explicit aware decision time; source labels or Git clocks are
never substituted for effective_at or available_at. Explicit effective_to=null
means an open-ended claim, whose authority still requires owner verification.

```bash
python -m unittest discover \
  -s implementation/experiments/chart-contract-v0.1/p0-receipt-preflight-v0.6 \
  -p 'test_*.py' -v
```

Tests include fictional filled packets strictly for negative authority controls.
No fictional identity/source/Theme receipt is shipped as production input. Prior
v0.4 reference replay is retained unchanged. This preflight prepares automatic
inspection of the next real owner response while the six existing prerequisites
remain open; it cannot close A-G1/A-G2/A-G3 or replace owner evidence verification.
