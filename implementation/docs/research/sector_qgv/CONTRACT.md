# Sector QGV v0: calculation / Main contract

`sector-qgv-default/0.1.0` is the owner-directed **default · initial setting**. State `draft`, validation `initial`, performance `NOT_MEASURED`, deployment `NOT_DEPLOYED` are independent. Official calc23.1/publication/ranks/TARGET and old A/B/C experiments remain unchanged. Lynch tags and display preferences have zero numerical/cache/order impact. No legacy company-type multiplier is applied.

## Ownership and invocation

Codex owns `research/sector_qgv{,_registry,_held}.py`, `tools/sector_qgv.py` and these tests/research contracts. Existing `qgv.qgv_v2.percentile` and `qgv.v2_factors` are called read-only. Main owns web/auth/server/workflow, public/private delivery and CI lists. No new dependency, service, data acquisition or runtime hook is introduced.

```sh
PYTHONPATH=implementation/src python implementation/tools/sector_qgv.py \
  --job /approved/private/job.json --output /approved/private/new-run
# Synthetic only:
PYTHONPATH=implementation/src python implementation/tools/sector_qgv.py \
  --job implementation/docs/research/sector_qgv/synthetic-job.json \
  --output /tmp/sector-qgv-synthetic-run --synthetic
```

The JSON batch boundary is ready for Main's existing reader. The actual authenticated execution location and storage/response transport remain Main integration work; they are not claimed deployed. Private CLI output is outside any Git checkout, mode 0600, no overwrite, no company values in logs. Public fixture jobs are explicitly `SYNTHETIC`. Main must not pass a private bundle to public output/sharing/copy/cache. The CLI is an offline calculation entry point, not an authorization boundary.

## Records and versions

- Catalog entries carry `factor_id` (design ID), `variant_id`, axis/role, aliases, formula version, inputs (field/unit/period), direction, applicability, overlap group, evidence and calculator status. EPS/BPS/DPS are inputs, never independent V factors. `CATALOG_MAPPING.md` separates operating definitions from design IDs.
- Preset resolution: exact §5 sector axes → accounting exception → explicit `sector_id|accounting_template` override. BANK, INSURANCE, BROKER, MORTGAGE_REIT peers are separate. ASSET_MANAGER means an evidenced low-capital fee business, not inferred from an insurance/holding label. Equity REIT needs its own evidenced book-sector mapping; it cannot fall back to PER.
- `sector-qgv-config/1`: base preset, scoped overrides, versioned policies, owner scope and display preferences. `preset()` returns axis basis points and `axes[axis][role] = {weight, factors:{variant:bp}}`. Each level sums to 10000, integer nonnegative. Same-role additions split its budget. Canonical alias duplicates are rejected. Unavailable inputs remain selectable; an unimplemented calculator is visible but cannot be positively weighted.
- `sector-qgv-input/1`: snapshot/input/universe/mapping versions, `as_of` timestamp, `valuation_date`, original `members`, rows keyed by company ID. Missing member rows are retained. A duplicate company ID or out-of-universe row is rejected. No external security ID is invented.
- Every observation includes issuer/security identity, variant/formula version, value/status, unit, period, price date, source availability and retrieval timestamps, currency, scope, corporate-action basis and source references. `VERIFIED_COMPONENTS` and `VERIFIED_DEFINITION` distinguish raw derivation and a verified external metric. A verified external definition does not require redundant component collection. An unverified vendor multiple cannot join a canonical score column.
- `sector-qgv-preview/1`: request/preview/config identity, input content hash, all model/engine/normalization/mapping/universe versions, result rows, original-denominator coverage, validation errors. Each factor exposes raw value/status, score/status and valid N. Each row exposes axes, pre/post-gate totals, nominal/effective weights, rank and missing reasons. Stored config references the successful matching preview; a changed configuration or request cannot save an old preview.

`cache_key` binds settings plus canonical input content, snapshot/input/universe versions, engine, normalizer and mapping. Factor observations can be reused, but peer changes always run scoring again. Main must also compare the active request ID, preview ID and context/cache key before accepting a response; a late A response must not replace B. A saved configuration is reapplied to **the original whole population**, not to a display-filtered subset. Filtering preserves original ranks; common-valid before/after ranks are separately reported by `compare_previews`.

## Value, period and eligibility semantics

Signed E/P, CFO/FCF yields and common B/P remain signed valid observations. Actual 0 is `VALID_ZERO`; missing is null. PER display is null for EPS <= 0. PEG uses decimal growth times 100 (20 / (.10*100) = 2), requiring positive EPS/growth. EV must be positive; its evidence identifies equity + debt + preferred + NCI − cash. Market cap evidence must cover the corresponding common classes. There is no price/EV/share reconstruction here.

Default EPS is explicitly verified TTM diluted EPS with matching price/share/ADR/action basis. The held SEC adapter **does not apply generic FY+YTD−prior YTD monetary-flow arithmetic to EPS**. That composition is unconnected, not silently replaced with FY EPS or NI/current shares. FY diluted, FY1 and NTM are different variants. All annual observations are required for CAGR histories; start and endpoint must be positive. G06 is latest annual ROA minus t−3 ROA; each uses beginning/end assets, including t−4. No single-quarter/annual fallback masquerades as TTM. TTM flows require explicit year duration and common period end. Financial ROE requires positive beginning and ending common equity.

The held adapter retains SEC filing-date cutoff logic and source hashes. Its `source_available_at` is explicitly **observed by acquisition**, not the first SEC release timestamp. It cannot establish availability before acquisition or intraday filing availability. Valuation dates after the snapshot cutoff are rejected; source availability after the valuation date is rejected even if the calculation is run later. Retrieval can occur later only when the source itself proves earlier availability. No historical performance is inferred. A source's STALE/failure status is retained by the held adapter and honored; new per-factor recency thresholds are not invented. Producer-specific freshness policy/evidence must be supplied by the owning adapter.

The book 10-sector mapping needs its own version, effective interval and evidence. Current Communication Services is not automatically old Telecommunications; SIC benchmark ETF rules are not substituted. Unknown mapping blocks scoring, while valid raw observations remain visible. Repeated issuer rows require one evidenced scoring representative; otherwise they are excluded from peer scoring and remain in the original denominator. This does not merge unresolved securities or establish market cap eligibility.

## Scores, gate and nulls

`sector-midrank-strict20/1`: same valuation date + book sector + accounting template, per-factor valid issuer representatives, minimum 20. Shared midrank formula, reverse for lower-is-better, ties all 50. No industry fallback, pooled-sector merge or neutral fill. Input failures and `PEER_SAMPLE_SMALL` are separate.

`strict/1`: every positive-weight factor in a positive-weight role and axis is required. Zero weights do not count as active-factor missing. Axes are independently reported; total requires every active axis. Strict completeness is evaluated **before** gate exclusion, so a trap does not cure missing V.

`official-q-percentile-required/1`: a separate mandatory observation of the existing official engine's Q industry percentile, its calc version, evaluation date and evidence. It is never inferred from the user's selected Q factors. Threshold is the imported official `GATE_PERCENTILE` (<=30 excludes V); remaining nominal axis weights are proportionally renormalized. Missing evidence/percentile => `UNKNOWN`, final total/rank null even if pre-gate total exists. A V-only allocation excluded by the gate has `NO_WEIGHT_AFTER_GATE`. Official unknown-gate behavior is not modified. Gate percentile source linking is separate from the new model's factor normalization.

Coverage exposes acquisition, raw validity and scoring separately for every catalog variant on original denominator N. `selected_coverage` counts only positive effective selections and has its own explicitly labelled selected denominator; it never replaces N. Q/G/V, all three and model total are independent counts. Unknown mapping/rows remain in N. Missing inputs are not 0. Non-measured performance remains null, while measured zero score coverage is 0/N.

## Main fixtures and required integration

`synthetic-input.json`, `synthetic-preview.json`, `synthetic-states.json`, `catalog.json`, `presets.json` are entirely artificial. All scenario expected counts/ranks are generated and tested by the calculation path. UI states include empty, partial, STALE, missing gate, mapping unknown, small peers and rejected input. A long Korean name is presentation-only and cannot enter scoring. Display default/recommendation/selected/calculator state/applicability/availability separately. `initial` must not look performance-validated.

Main actions: wire the existing configuration UI and JSON reader; enforce active request/context checks and private authorization; supply an evidence-bearing dated book-sector/accounting mapping and gate source link; optionally add `tests/test_sector_qgv.py` to the owned CI list. No new shared dependency or workflow permission is requested. The current operating 504-code run does not manufacture these missing mappings.
