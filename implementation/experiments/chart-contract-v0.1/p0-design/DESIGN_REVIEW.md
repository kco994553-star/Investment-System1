# P0 design verification record

Scope: documentation only. Baseline PR41 `8668c69070c7956cb85d1ccf8cbeb8d9d2daf5cf` preserved. The design is complete for contract/gap/dependency review; production implementation and V01–V16 remain NOT_STARTED / NOT_RUN.

## Independent lenses and resolution

| Lens | Initial result / finding | Resolution | Final scoped judgment |
|---|---|---|---|
| Market/Data/PIT | No blocking gap; RawDatasetStore incorrectly described as verifying reads | Reuse map distinguishes manifest/hash creation from PR41/producers byte verification | PASS design |
| Portfolio/Domain | Conditional PASS: portfolio non-finite admission and authoritative target validation not explicit | §4.1 and V10 reject NaN/Infinity/invalid Decimal strings and invalid/unvalidated target totals without rounding, epsilon or Frozen edits; reviewer reread confirms resolution | PASS design |
| Product/Integration | No blocking gap; same API/MCP hash wording could imply independently acquired raw responses must hash identically | V01 applies to the same immutable materialized document; consumer metadata excluded, original source provenance retained | PASS design |

Source review notes in reviews/ retain findings rather than erasing initial objections. Votes are not the evidence: actual symbols, pinned blobs and explicit invariant checks decide. Root independently inspected the producer serializer/validator, publication envelope, session binder, personal domain/FX/identity, frontend weight fallback and P01/hash boundary definitions.

## Additional material source findings carried into design

- `actual_weight ?? target_weight` in trial frontend needs Web-owner correction before actual/target production wiring.
- Search metadata is SEARCH_PRESENTATION_ONLY; cannot supply Portfolio/PIT classification.
- Current actual domain handles repeated securities across accounts; PR41 integer-only/duplicate-reject demo input is not a production substitute.
- Industry/type membership is per-assignment evidence with separate versions/availability. Unknown is not an empty verified set.
- Decimal transport is missing from existing serializer; lossless encoding adapter is proposed, arithmetic policy is not selected.
- Market session finality, provider availability and quote-feed delivery state are independent; existing session eligibility cannot certify all of them.
- Publication grants remain NONE; proposed sidecar registration does not bypass validation/authorization.

## Cheapest reliable verification

Fresh git fetch/PR read → filename/symbol/schema/source/test/handoff inspection → three complementary design reviews → correction of specific findings → static scope/source/hash checks. Source runtime is unchanged, so no full regression rerun was added. Historical75-test evidence remains scoped to the prior experiment.

Static results:46 exact source artifacts resolved and recorded; Core81/Extended24/Candidate8 preserved; existing tracked files identical to PR41 baseline; all additions confined to p0-design documentation. No owner/Frozen/Official/canonical files modified. No source/network acquisition, account access, grant, new numeric policy, Holdout use or merge performed in this increment.

## Acceptance checklist

- [x] Audit baseline and three scopes preserved.
- [x] Existing provider/calculation/schema reuse tied to exact sources.
- [x] Market identity, time/session/timezone, OHLCV, adjustment/actions, availability, provenance and feed state designed.
- [x] Portfolio TARGET/ACTUAL split, source/versioned classification and intentional overlap designed.
- [x] One shared verified domain/product payload for API/Web/future MCP; no duplicate financial calculation.
- [x] Actual upstream, projection, product, source-history and validation gaps enumerated.
- [x] V/Reverse DCF/MOS/scenario-target semantics deferred to reconciliation.
- [x] Protected paths/owner dependencies reported before implementation.
- [x] Critical path and implementation gates stated; no production completion claim.

No unresolved design-review blocker remains. Source acquisition, interface adoption, protected owner changes and publication decisions are implementation dependencies, not completed work.
