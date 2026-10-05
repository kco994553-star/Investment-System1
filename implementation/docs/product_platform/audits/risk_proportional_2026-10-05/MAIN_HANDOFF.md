# Main routing packet — SA01/SA02 bounded candidates

Packet: PLATFORM-RPV-20261005-SA01-SA02. Recipient role: current CDR-018 Main coordinator, GPT Work gpt-work-main-2026-10-05-3a80dcef6444. Source owner: codex/product-platform-audit-v1. This is a published, reviewable routing packet; Main consumption and owner adoption are NOT_CONFIRMED. No other-owner branch or person-directed message is written here.

## Exact subjects and reusable evidence

- Owner HEAD: 78a51462f89eac8e34647cddc4e53ed97e831178.
- Target: implementation/src/investment_system/platform/contracts.py.
- Base source SHA-256: b13686d8ce134ccb61ef78c51d178597404e7a3401e7b22240dcc47c01d0aa7b.
- Candidate source SHA-256: 4a120b6c5f5e866b9105e94b5ab06256a0da41551848b26f0eb94c438dd57314.
- Diff: [SA01_SA02_candidate.patch](SA01_SA02_candidate.patch), only two bounded helper edits; unchanged schema fields, operation allowlist, financial amounts and reconciliation result shape.
- Original source-pinned two RED counterexamples and two wrapper fixtures: [prior receipt](../storage_auth_2026-10-05/owner_probes.json), published in 11dba838c6e27430aa07957f69e4ae8b270c999b. Retained, not replayed.
- Actual transferable candidate verification: [candidate_verification.json](candidate_verification.json), [runner](verify_candidate.py), [stdout](candidate_verification.txt). Disposable-copy git apply check/application PASS, 12/12 checks PASS on candidate source bytes; existing nine affected contract tests plus two reused negatives and frozen canonical-reference preservation. No full repository rerun.

| Finding | Candidate action | Required closure on owner successor |
|---|---|---|
| SA01 — equivalent upper/lower SHA causes false missing/orphan | Normalize already validated SourceRecordRef digest at frozen dataclass construction; raw record metadata and bytes are untouched | Direct upper/lower refs compare/hash equally; same source reconciles without false missing/orphan; malformed digest still rejected; ref remains frozen; replay/version collision behavior preserved |
| SA02 — inherited public callable trade escapes class-dictionary drift check | Inspect effective public callable attributes across MRO, respecting subclass masks | Actual BrokerAdapter allowed; inherited trade/write rejected; subclass get_positions=None rejected; original unknown/trade operation dispatch still denied; cross-tenant checks preserved |

SA02 is a synthetic interface-admission gap, not observed current production trading. The operation gate already denies trade. The candidate's effective-MRO scope follows the known public-callable contract; it is not proof about dynamic provider instances, descriptors/metaclasses or runtime authorization. Broader runtime/connector acceptance needs its own concrete implementation and negative evidence. Do not reinterpret set-lineage checks as financial amount/completeness reconciliation.

## Next action and stopping condition

Main should route these two exact candidates to the accountable Platform source owner and obtain an accepted per-file write set. The source owner fresh-reads HEAD and lease, checks base hash/diff compatibility and either accepts the bounded changes on its own successor or returns a reasoned alternative. Any protected semantic decision stays behind the existing D3 boundary. Do not apply this patch to canonical or to the owner branch from this audit Work.

The owner can reuse the published negative helpers or add equivalent tests in its existing test_product_platform_contracts.py. No duplicate package/test tree is required. Return exact successor SHA, source/test hashes, targeted negative and affected contract result, and handoff acceptance. This audit compares affected source/dependency hashes, executes only affected negative/contract tests against that successor, then marks SA01 and SA02 CLOSED independently if they pass. Merely publishing this packet or returning a completion claim cannot close them.

Keep trusted runtime ownership, authentication/session/revocation, financial completeness/source-conflict admission, durable authenticated raw storage, real connector lifecycle and authenticated Product API open. Main's existing PPA-F08 Web route remains distinct; missing ACTUAL must never inherit TARGET. This patch cannot advance any whole product capability to VERIFIED.
