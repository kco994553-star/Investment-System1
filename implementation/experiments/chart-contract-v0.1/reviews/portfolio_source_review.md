
## Fresh independent oracle — 2026-10-04 KST

Reviewed experimental `portfolio_contract.mjs`, `portfolio_fixture.mjs`, `portfolio_reference.json`, and `evidence/portfolio-reference-source.json` after implementation. No implementation edited by this reviewer.

Result: **11/11 independent checks PASS**, including **40 deterministic generated set-membership cases** in one check. This is display aggregation validation, not actual holdings/quarterly history/PIT validation.

Checks performed:

1. Hand-authored independent expectation reproduced all 19 source holding IDs, exact target units, and group labels.
2. Reference partitions exactly 10,000 units: equipment 3,000; AI/semiconductor 2,500; Big Tech 2,000; other 2,500; cash zero. TARGET/REFERENCE statuses preserved.
3. All real-reference company_types remain null; all security IDs unresolved. TEL warning retained, publication grant null, PIT not verified. Unknown type exposure is 10,000 units for every requested type, never interpreted as classified zero.
4. SHA256 of all three original source files and the reference JSON matched the evidence file.
5. Fictional type memberships total 105 units on a 100-unit denominator; overlap exact-set partition totals100. Every ring's members + known nonmembers + unknown + cash equals100.
6. Types `A|B`, `A,B`, and the exact two-type set `[A,B]` remain three different semantic buckets.
7. `__proto__`/`constructor` remain ordinary labels without prototype pollution; repeated security IDs rejected.
8. OBSERVED_DATA cannot pass renderer; reference cannot be promoted to ACTUAL.
9. Input mutation after aggregation cannot mutate output; output arrays and metadata are frozen.
10. Supplied zero weight remains known zero; null weight rejected.
11. Forty independently generated portfolios reproduced direct per-type membership sums and exclusive exact-set sums, with variable cash, unknown classifications, known empty types, and zero-weight holdings.

No new blocking discrepancy found. Existing limitations remain: these four sectors are user-authored allocation groups, not detailed GICS industries; no genuine company-type assignments; no actual-account or quarterly snapshot ingestion; no PIT certification. The extractor time in `as_of` is explicitly documented by evidence as extraction time, not historical publication/valuation time. The reference source itself remains dated Portfolio v1.1 · 2026-09-14.
