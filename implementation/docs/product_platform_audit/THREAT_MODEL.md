# Product Platform Audit · Threat Model v0.1

This is a bounded read-only platform threat model, not a production security certification.

- Cross-tenant object access: explicit tenant on every record; mismatch denies.
- Financial-write bypass: external operations use an exact BrokerAdapter-derived allowlist; unknown methods deny.
- Replay/mutation: exact source-version replay is idempotent; conflicting content under the same version fails closed.
- Lost lineage: normalized records preserve immutable source refs; missing/orphan/duplicate/cross-tenant reconciliation fails.
- Time fabrication: source times must be timezone-aware and ordered observed <= available <= ingested.
- Public personal-data exposure: existing static Web is not a secure hosted personal-data service.
- Credential leakage: no credential/secret store or real provider is introduced here.
- Frontend recomputation: Web/API must consume verified domain/product projections.
- Audit-log mutation: durable append-only storage remains required before operational claims.

Non-goals: real login/provider activation, real account connection, paid provider selection, trading/transfers, canonical merge/deploy.
