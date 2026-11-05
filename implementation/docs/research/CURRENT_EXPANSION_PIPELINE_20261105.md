# Current expansion: retained evidence to common QGV

Status: offline research implementation; no official population change, collection, workflow or deployment. Base: `620f57f264896c1efa34ac8e6c19ccd28c10d7d3`.

## Existing approval and boundary

This connects the current expansion decisions in `USER_DECISIONS_PENDING.md` (2026-10-30/31), `expanded_universe/IEX_UNIVERSE_PLAN_20261030.md` and the existing catalog design. The current source population is IEX-tradable securities on the evaluation date. The nominal gates are entry issuer capitalization USD250m/price USD5; retention USD200m/USD3 with prior membership evidence; one representative per issuer; monthly end-of-session selection. ADV remains deferred. This is separate from historical C2 real-2025-dollar/DC-43 thresholds and from fixed Universe504.

An SEC ticker observation is searchable issuer evidence, not an IEX roster, a security identity, a listing interval or proof of market completeness. CIK is an issuer identifier only. Observation IDs are source-row offsets only, never security IDs. No issuer's first ticker is automatically designated its representative. Partial lists and uncollected rows are never dropped to improve reported coverage.

## Normal entry point

```
python implementation/tools/current_expansion.py \
  --archive /PRIVATE/approved-held-c21.zip --basis-date 2026-11-02 \
  --output-dir /PRIVATE/new-current-expansion-run
```

This reads only local ZIP members and their original receipts; verifies the used bytes/hash/time; calls `sec_qgv2.build_row`/calc23.1; and writes `held-normalized.json`, `current-expansion.json`, `manifest.json` outside Git, mode0600, without overwriting. Missing companyfacts/submissions remain explicit. The archive itself is not downloaded or copied. No supplier calls occur. A failed run cannot replace a successful directory; resume with a new output directory.

`evaluate(candidates, financials, evidence, source, basis_date)` additionally accepts an evidence map keyed by source observation offset. For an executable selection population, supply a complete dated IEX roster and per-row evidence: CIK, fixed security and issuer IDs, ticker/exchange/type, listing interval/status, IEX membership, shell/SPAC classification, representative decision, all-class issuer market cap (USD, same date), and identity-linked raw USD price (same date). Prior membership needs a reference and date. Do not manufacture these fields from ticker strings. The CLI's retained SEC archive cannot assert complete IEX scope; its purpose is the actual held-input diagnostic path.

When the entire selection population is established, the API passes **all eligible rows**, including financially uncollected ones, into the existing Q/G cross-section scorer, official price/identity/ADR/split checks and `qgv_official.score`. It reuses the existing rank function; V-missing totals receive only the existing QG reference order. No separate public/private weights, gates, replacement values or scoring engine. Unknown membership blocks relative scoring for that population, but raw normalized financial metrics remain available. No V4 monthly history is invented.

## Main result contract and synthetic example

`current-expansion-research/1`, private research. `universe_version=U-US-EXPANDED-CURRENT/1`; official fixed504 remains independent. Fields:

- `basis_date`, `source.observed_at`, `source.scope`, `source.age_days_at_evaluation`: evaluation date versus retained observation age.
- `counts.candidate_rows`, `unique_tickers`, `unique_issuers`, `financial_rows`, `fixed_security_ids`, `eligible`, `excluded`, `unknown`, `scored`: different stages, not interchangeable denominators.
- `full_market_denominator`: null until complete dated IEX roster is evidenced.
- `rows[].searchable`, `financial_available`, `raw_metrics`, `eligibility`, `reasons`, `financial_reasons`, `financial_acquired_at`, `calculation_attempted`, `score`, `rank`: discovery/data/calculation/ranking are separate.
- `coverage.denominator`, `factors`, `Q/G/V`, `simultaneous`, `preset_actual_total`, `ranked`: null when population not established, zero only after executing the established population. `preset_actual_total` is an executed default balanced total count, not a calculation-possibility estimate or all-presets claim.

Synthetic complete12 candidates/one missing financial input gives denominator12 and Q11; the missing row remains. Synthetic partial12 observations/11 financial rows gives market denominatornull, eligibilityunknown12, score/ranknull for every row. These are test cases, not real market coverage.

Do not put this private research output into public files, logs, copy prompts or official population selectors. Main integration is a separate task. This implementation adds no workflow, secret, UI, public serializer or authentication code.

## Source/update handoff and minimum next input

Existing retained SEC `company_tickers.json` gives ticker/title/CIK only; it has neither fixed security identity nor IEX-tradable completeness. Original SEC companyfacts/submissions remain the financial source. Existing source receipt hashes deduplicate identical bodies; changed bodies can be normalized again with their own acquisition time and original archive. This job has request budget **0**, no scheduler, no live refresh. Financial timestamps and source age remain visible; no current refresh is implied.

The first missing current-market source is **one approved current evaluation-day IEX trading-status symbol list**, including source timestamp/scope and all observed securities, retained as a complete input artifact. Main's existing IEX expansion stream is the next implementation owner; historical2018 restoration is not a prerequisite. A listing/security master or equivalent documentation must then support security type, stable identity, issuer/class mapping, representative choice and all-class market cap. This PR neither selects a new vendor nor requests broad collection. Existing IEX last-trade data must not be called OHLCV. Public/private usage rights remain per existing source decisions, not expanded by this research pipeline.
