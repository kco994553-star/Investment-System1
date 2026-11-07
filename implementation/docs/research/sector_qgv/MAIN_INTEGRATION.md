# #505 → #507: concrete contract differences and call path

Compared with Main #507 `cd2fd62ed7793541d09f34d871d0ff24fef24135`.
No Main-owned frontend, shared guard, CI list or workflow was edited.

| Current #507 difference | #505 contract / required Main change |
|---|---|
| Provisional selection `factor_id`, generated `*.v0`, `proposal-0` | `main-editor-contract.json`: canonical `variant_id` is the selection key; design Q/G/V ID is display metadata. `temporary_id_map` covers 27 unambiguous aliases; not an operating-ID equivalence claim. |
| `V_FWD_EARNINGS_YIELD` combines FY1/NTM | Explicitly choose `ep_fy1` or `ep_ntm`; bridge rejects the ambiguous ID. Their input absence is not undefined formula. |
| Roles `accrual_quality`, `financial_strength`, `capital`, `coverage`, `other` | `temporary_role_map` maps to canonical roles. Do not change economic role budgets automatically. |
| Discretionary V cash=65%, inner 6154/3846 | Exact v0 is earnings 35%, CFO cash 40%, FCF other_value 25%. Old combined cash tree is rejected as `MAIN_ROLE_REBASE_REQUIRED`; load the canonical tree before editing. |
| `gate_policy=NONE` only | Read `official-q-percentile-required/1`; PASS / VALUE_EXCLUDED / UNKNOWN. Unknown prevents final total/rank even with a valid pre-gate total. No browser bypass. |
| `compute()` / `preview()` aggregate/rank locally | Invoke the existing Python engine via the transport below; render `response.display` and retain full `before`/`after` for factors, valid N, effective weights, gate and versions. Do not call local `compute()` as fallback. |
| Recommendation enum excludes owner initial design | Add `OWNER_INITIAL_DESIGN`; `initial` is not performance validation or book-prescribed arithmetic. |
| Raw units shown as %, despite canonical decimal values | Use catalog raw unit (`decimal` vs multiple); format decimal ×100 only for display. Factor/axis/total scores remain 0–100. `VALID_ZERO` is not missing. |
| Template options imply FINANCIALS/Equity REIT assignment | Options are not evidence. No real REIT mapping is supplied. Preserve unknown rows in denominator. |
| Day-only snapshot field, 64-character versions, FNV config key | Preserve `valuation_date` and full `as_of`; allow full immutable version strings. Engine SHA-256 `config_hash/input_hash/cache_key` bind settings, inputs, population, engine and mapping. FNV may be an editor-local dirty check only. |
| Preview `why`, `excluded`, Lynch chips and common-rank rows | `response.display` has these shape-compatible fields; all numerical values/ranks are copied from engine previews/comparison. Lynch is display-only. Sector rank is null (`NOT_PROVIDED_BY_ENGINE`). |

The actual #507 Node reader accepted its own synthetic bundle, rejected the
required gate with `GATE_POLICY_UNSUPPORTED` at `$.presets[0].gate_policy`, and
rejected the engine response with `KEY_MISSING` at `$.schema`. This is a verified
integration gap, **not** a completed browser → engine connection.

## Offline execution and Main-owned invocation

Reuse `implementation/tools/sector_qgv.py`. Main's server or offline task runner
writes an authorized private JSON request and a normal `mode=normalized` job:

```json
{
  "mode": "normalized",
  "data_kind": "PRIVATE",
  "request_id": "active-request-id",
  "snapshot": {"path": "/approved/private/snapshot.json", "sha256": "<64 hex>"},
  "main_request": {"path": "/approved/private/request.json", "sha256": "<64 hex>"}
}
```

`python implementation/tools/sector_qgv.py --job /approved/private/job.json --output /approved/private/new-run`

Read `main-response.json`. `before_config`/`after_config` accept the existing
Main editor config schema or canonical `sector-qgv-config/1`. Empty editor
overrides load exact canonical defaults; no UI-local approximation is adopted.
Job/request IDs must match. `saved-config.json` binds the actual engine preview.
Check active request ID, expected input/universe/version context and canonical
config hash before display/save; reject late or mismatched answers. Do not expose
private requests/results through public bundles, logs, prompts or share features.
No new backend route or collection trigger is added by Codex.

Public synthetic inputs: `main-synthetic-request.json` + existing
`synthetic-input.json`; expected output: `main-synthetic-response.json`.
`response.display` may feed `previewView()` after Main changes the source/preview
adapter. It includes every original row, including no-total rows; `diff.common`
is the separately defined common-total-valid comparison count. Existing
`synthetic-states.json` remains the status fixture source (empty, missing,
STALE, unknown mapping/gate, small peers, invalid input). These are synthetic,
not production data or coverage. `main-editor-contract.json` is the canonical
catalog/config bridge, not a replacement publication format.

## Remaining parallel handoffs

- #504: Main's #502 producer-byte test passed against #504's converter; no format
  mismatch. The known pure-validator import/shared-guard conflict remains Main's
  change. No helper/guard patch was supplied in #437 as of this continuation;
  Codex will change only the consumer import when provided. No actual price input
  received; no November 2 prices are spliced into November 4 sector results.
- #503: existing first issuer remains CANDIDATE. Existing facts/judgments and
  #506 screen connection are reused. Durable attraction, complete contrary
  evidence review and review-date completeness still lack new supporting
  evidence; no new selection or redundant replay is reported.
- The 12 definition-pending variants remain itemized in `CATALOG_MAPPING.md` and
  their catalog `domain_rules`: ROIC recipe; profit-stability metric/std/loss rule;
  NOA decomposition/direction; depreciation/CAPEX direction/scope; CFO/share,
  FCF/share, tangible BPS and FFO/share growth horizons/bases; consensus horizon/
  vintage; FCFF recipe; AFFO reconciliation; forecast PEG horizon/consensus.
  The 39 implemented variants continue independently.

Main CI request: add `tests/test_sector_qgv_classification.py` and
`tests/test_sector_qgv_main.py` alongside the previously requested sector test
when integrating #505. No dependency installation, workflow/Secret or permission
change is needed. Main owns that CI list.

## 2026-11-07 continuation

New `axis-comparison.json` is documented in `PARTIAL_COMPARISON.md` with
`partial-synthetic-{snapshot,config,comparison}.json`. It exposes separate Q/G
common sets even if `diff.common_valid` for total is0. Existing Main response
schema and exact engine-produced display are unchanged; no screen-local rescoring.
Main #507 head remains unchanged, so actual server/reader connection is pending.
The earlier #504 helper blocker now has Main #508
`df1a9abb8c72ee57a7f7a50011bb0dbf9ffb116f`; #504 imports its pure `iex_values`
module and retains that exact dependency. No November2 prices have arrived.

## V resume handoff, 2026-11-07

New `V_RESUME.md` and `v-synthetic-{pack,market,job}.json` connect the existing CLI
and result reader. No preview/save schema change, new pricing engine or UI sum.
Add `tests/test_sector_qgv_v.py` to Main's CI test list when integrating; no new
package/dependency/workflow is edited here.

Latest repository evidence supersedes the earlier pending-screen note: #507
`4f392207cdcbc8a096e05dae09c78034339dc876` reports the synthetic dev-screen →
shared engine → preview/save path connected. This does not establish a private
real-input/authenticated production path. #510
`b2482e6506a2edf03c454f27dddb50fd98a80ae0` includes #505 only through
`aa9c4484e65baced0dd06622eb64c71e33a9c2fd`; retain the newer partial-Q/G commit
`7c2225a382aedf275749eb5c2f9f2385db7cdcf3` and the V-resume continuation when
Main reconciles dependencies. #505 is not empty relative to that integration.
#504 helper dependency is already connected; actual financial11 delivery is still
pending and remains November2-only. No new helper/guard change is requested.
