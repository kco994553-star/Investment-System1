# Independent Product Platform audit handoff

Branch: `codex/product-platform-foundation-2026-10-05`; base canonical `b8e39a2196a6d7794a04a0cd5393c68329e126ca`. Exact publication HEAD is the containing Git commit/PR metadata, never a fabricated self-reference. STATUS.md contains the capability matrix; AUDIT_EXECUTION_POLICY.md contains the latest D1/D2/D3 boundary.

The original attached build Work was narrowed by the latest user to independent audit. New fixture-only implementation is retained as a bounded audit tool. No production owner source is replaced. No canonical merge, deployment, real credential, tenant policy or investment calculation-method change occurred.

Read next: `STATUS.md`, `OWNER_FINDINGS.md`, `FAILURE_AND_REPAIR_HISTORY.md`, `CONTRACT.md`, `evidence/validation.json` and its source/log manifest.

## Consuming route and acceptance

Claude Main / Primary Integration Coordinator consumes this packet under CDR-017, while Global and other owner branches remain read-only here. No message to a person was sent. The new Platform owner is `codex/product-platform-audit-v1`; its latest source and future handoff win over stale pinned findings. Owner route remains OWNER_ACTION_REQUIRED until an actual returned artifact and acceptance receipt exists.

| Packet | Owner / permitted write set | Required returned artifact | Acceptance |
|---|---|---|---|
| Owner provenance/runtime findings | Platform owner; its own `implementation/src/investment_system/platform/` and tests, not this branch | Closed typed provenance/ownership validation and missing-data semantics; initial package import/exports already CLOSED at c9e1adb | Malformed refs/blank identity and missing-source cases fail closed; declared hashes alone never represented as authenticated raw; preserve passed import controls |
| Auth/tenant/read-only integration | Platform owner plus security/runtime owner; new versioned adapter within accepted write set | Trusted auth→principal→tenant boundary, admitted read-only operations and explicit coverage receipt | Negative object access across user and tenant, capability escalation/order/funds surfaces and provider revoke fail closed; fixture receipt cannot authorize production |
| Accounting closure | Connector/Platform owner; fixture/schema/test scope only | Full opening→transactions→closing/statement fixture and required source/provenance | Deterministic exact financial reconciliation; mismatch/missing/duplicate remain distinguishable; no unapproved tolerance/FX policy |
| Product/Chart/Web admission | Respective owners under their existing branches | Accepted Product contract/read route/write set, admitted Chart document/renderer and browser evidence | No auth/financial calculations repeated in UI; actual and target remain separate; unavailable data/grants remain unavailable |
| Integration identity | Integration/FPIA owner | Exact integrated-result SHA, code identity, authenticated manifest and independent FPIA receipt | Local tests and old-byte preservation do not replace merge-result FPIA; no canonical merge performed here |

## Next finite D1/D2 work

Fresh-read the actual owner HEAD and handoff; suppress only already accepted identical finding fingerprints. Reconsume returned import/validation fixes, run affected probes, and rejudge this matrix. Reuse this synthetic harness rather than constructing another one. Add only an owner-compatible adapter after exact contracts/write set are published. Independently prepare the complete transaction/statement fixture if no active owner owns that write set. A pending D3 stops its dependent action only.

Browser/mobile E2E is NOT_RUN due to missing Chromium and a failed normal download. HTTP tests are real loopback tests, not browser tests. Production PWA/Chart and real connector/auth are not complete. No unattended scheduler-hop verification is inferred from this manual run.

## Reproduce the isolated harness

```sh
PYTHONPATH=implementation/src python -m unittest discover -s implementation/tests/product_platform -v
cd implementation
python tools/mini_pytest.py
```

Optional fixture-only UI launcher from repository root:

```sh
python implementation/tools/product_platform/run_local.py --db /tmp/platform-audit.sqlite
```

The launcher binds loopback only; synthetic IDs and data are clearly marked DEMO. The DB path must be outside the repository. Production cookie/TLS/IdP/financial credentials are not configured.
