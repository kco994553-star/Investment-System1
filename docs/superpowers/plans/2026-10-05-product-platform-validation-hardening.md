# Product Platform Validation Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the non-production Product Platform contract reject blank identity/provenance fields and malformed lineage references before reconciliation.

**Architecture:** Keep validation at immutable dataclass construction boundaries so invalid objects never enter import or reconciliation. Reuse one private nonblank-string validator and preserve the existing read-only, tenant, and lineage-only semantics without adding Auth, persistence, financial arithmetic, or production admission.

**Tech Stack:** Python dataclasses; repository `mini_pytest.py` shim.

**Spec:** `implementation/docs/product_platform/CURRENT_HANDOFF.md` on independent audit subject `17244b4f1be0d3b2423d91f76af8b0ad2c262a65`, reconsumed against owner HEAD `c9e1adb5fbd9a1b8e005c4f4cea7eec30ccc84d9`.

## Global Constraints

- Owner branch is `codex/product-platform-audit-v1`; canonical merge/deploy is prohibited.
- No production Auth, Product API, financial provider, tenant-policy, persistence, trade path, or accounting semantics are added.
- Validation fails closed and keeps TARGET separate from ACTUAL.
- Durable ledger and financial reconciliation completeness remain open blockers.

## Review Focus

- Whitespace-only tenant/principal identifiers must fail at `TenantContext` construction.
- Blank or malformed `SourceRecordRef` fields/hash must fail before lineage processing.
- `NormalizedFinancialRecord.source_refs` must contain only `SourceRecordRef` instances.
- Valid existing source/ref/reconciliation behavior must remain unchanged.
- Empty lineage remains a lineage-only result and must not be promoted to financial reconciliation verification.

---

### Task 1: Fail-closed identity and provenance values

**Files:**
- Modify: `implementation/tests/test_product_platform_contracts.py`
- Modify: `implementation/src/investment_system/platform/contracts.py`

**Interfaces:**
- Consumes: existing `TenantContext`, `SourceRecord`, and `SourceRecordRef` constructors.
- Produces: `_require_nonblank(name: str, value: object) -> None`; validated immutable identity/reference objects.

- [ ] **Step 1: Add failing tests** for whitespace tenant/principal values, blank reference fields, and non-64-hex reference digests.
- [ ] **Step 2: Run** `PYTHONPATH=implementation/src python implementation/tools/mini_pytest.py implementation/tests/test_product_platform_contracts.py` and confirm the new tests fail because invalid values are accepted.
- [ ] **Step 3: Implement** `_require_nonblank` and call it from `TenantContext`, `SourceRecordRef`, and `SourceRecord`; validate reference SHA-256 with the existing canonical rule.
- [ ] **Step 4: Re-run the focused tests** and confirm PASS.

### Task 2: Reject malformed lineage references

**Files:**
- Modify: `implementation/tests/test_product_platform_contracts.py`
- Modify: `implementation/src/investment_system/platform/contracts.py`
- Modify: `implementation/docs/product_platform_audit/STATUS.md`
- Modify: `implementation/docs/product_platform_audit/CURRENT_HANDOFF.md`
- Modify: `implementation/docs/product_platform_audit/automation/STATE.json`

**Interfaces:**
- Consumes: validated `SourceRecordRef` from Task 1.
- Produces: `NormalizedFinancialRecord` instances whose `source_refs` are a non-empty tuple of `SourceRecordRef`; scoped evidence that PPF-003/PPF-005 are closed while PPF-004/PPF-006 remain open.

- [ ] **Step 1: Add a failing test** showing integer/mixed lineage references are rejected at construction rather than raising inside reconciliation.
- [ ] **Step 2: Run the focused test command** and confirm the failure is acceptance of the malformed reference.
- [ ] **Step 3: Add the minimal constructor type check** without changing reconciliation arithmetic or empty-lineage policy.
- [ ] **Step 4: Run focused tests**, then `cd implementation && python tools/mini_pytest.py`, and confirm all pass.
- [ ] **Step 5: Update scoped status/handoff/state** with exact findings, tests, unresolved blockers, and no production claim.

