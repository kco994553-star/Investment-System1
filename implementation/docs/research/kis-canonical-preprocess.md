# Private KIS technical preprocessing on canonical

Scope: offline research/data preprocessing only. Worker, authentication, browser,
workflow, shared guards, collection, publication and deployment remain Main-owned.
The current official population remains Universe504; Top500 is a transition goal.

## Source and dependency boundary

Base: `719e23a042d2c737fe408844bf89ccbe081fac39`.
Reuse #542 (`637e4243432e55365d1976d977faff543a0a5c5b`), the split
assessment from #547 (`1aa15601ec995e7e08c41fc0aee37a6ba60f39dd`), and
#551's retained latest-query/slash-symbol normalization
(`49968f41042732203a59a9957c10e877546a979f`). This is a source port,
not a whole-branch merge. Existing indicator, pattern, calendar, Decimal and
initialization formulas are unchanged.

The port excludes the portfolio ledger, EXP runner, group ranking/selection,
QGV scoring, collection clients and strategy configuration. Existing single-series
measure/session functions retain their source locations. Artifact hashing and the
existing 1,800,000-byte research delivery ceiling no longer import the unmerged
sector/dual QGV engines. Canonical technical kernels are reused directly.

## Existing payloads, separate paths

| Stored path | Worker route | Schema |
|---|---|---|
| `chart/<first>/<symbol>.json` | `/kis/chart` | `kis-bars/1` |
| `technical/<first>/<symbol>.json` | `/kis/analysis` | `kis-bars/1/analysis` |
| `measures/<first>/<symbol>.json` | `/kis/technical` | `kis-technical-measures/1` |

`private_kis_preprocess.project_technical` takes the original normalized contract
and saved `kis-technical-handoff/1`, with **independent expected hashes of both**.
It checks the saved result's internal hash and contract provenance, scope, source,
symbol, signal date and exact projected bars. It emits bytes and a per-series
manifest; it does not run the indicator or pattern kernels again. The chart needs
the original contract: the handoff's chart object alone lacks the complete raw
and evidence fields. No missing evidence arrays or timestamps are fabricated.

`calculate_and_project` calls the same existing kernels only for newly received
or changed inputs. The saved projection is the intended path for already completed
day-1 calculations. All results retain `OWNER_PRIVATE_ONLY` and remain diagnostic
where the original result withheld adoption. No group rank or QGV join is created.
Patterns/readiness/split assessment preserved by the handoff are separate from
Main's existing component/measures display support.

Slash-to-underscore encoding, when needed for a local file name, is storage-only.
It is not a verified security alias. Such series carry
`BLOCKED_ROUTE_MAPPING_REQUIRED`: Main's current Worker symbol grammar and allow
list must have an explicit verified mapping before reading them. Other route
allow-list and authentication checks remain Main's responsibility.

## Prices, splits and clocks

Only original `MODP=0`, `GUBN=0` daily responses are accepted. `MODP=1` combines
split and dividend adjustments and is rejected as input/split evidence. A supplied
confirmed split uses new-shares/old-share direction: pre-event prices divide,
volume multiplies, raw amount remains raw. Source bars remain available, future
events never adjust an earlier view, and already adjusted bars cannot be adjusted
again. A declared evidence reference does not claim an independent original-file
review. Unknown action coverage, identity, currency or trade scope stays unknown.

Signal date, last observed chart date, receipt capture, source query and historical
availability are distinct. Blank provider `BYMD` is retained literally, bounded by
capture/completed-session context; it is not replaced with a fabricated request
date. Missing sessions are not filled. Price-only indicators are not blocked by
missing volume, while OHLC/volume-dependent metrics retain their own requirements.
A 100-session source is insufficient for all 6/12-month or long-average measures.

## Calls and synthetic examples

```python
from investment_system.research.private_kis_preprocess import project_technical
files = project_technical(contract, saved_handoff,
    expected_contract_hash=external_contract_pin,
    expected_handoff_hash=external_saved_result_pin)
# files is {relative_path: UTF-8 JSON bytes}; Main decides approved private storage.
```

The network-free saved-result CLI is `implementation/tools/kis_preprocess_private.py`:

```sh
PYTHONPATH=implementation/src python implementation/tools/kis_preprocess_private.py \
  --contract CONTRACT.json --handoff HANDOFF.json \
  --expected-contract-hash CONTRACT_CANONICAL_SHA256 \
  --expected-handoff-hash SAVED_RESULT_CANONICAL_SHA256 \
  --output-dir NEW_PRIVATE_DIRECTORY_OUTSIDE_GIT
```

It creates a new directory only, never overwrites a previous good artifact, and
prints counts/status only. Its outside-Git restriction is preserved. The pure
RAM API can be used by Main's approved private writer; this does not prove that
the CLI writer succeeded in an environment whose entire writable root is in Git.

Public examples are generated in memory by
`implementation/tools/kis_contract_fixture.py`: normal, confirmed split, missing
session, missing evidence, stale and explicit counterexamples. Every example is
synthetic. Tests cover the new import/runtime and stored projection boundaries;
CI `cockpit-pages` already discovers `implementation/tests/research` via its full
Python suite. No workflow or CI list change is requested.

## V: deliberately not relabelled or overwritten

This technical-only port does **not** produce `qgv/latest.json`. Each manifest
marks `NOT_PRODUCED_555_DEPENDENCY` and `retain_previous=true`. Do not create an
empty replacement or turn a previous good file into a current success.

#547 produces `owner-price-v-result/1` under the 555 model, whereas Main's existing
Worker reader expects `kis-qgv/1` and null private rank. A schema rename would
change model/gate/rank meaning. Minimum existing 555 runtime dependency set:

- #537: `qgv_555.py`, `qgv_555_central_v.py`, `qgv_555_financial_temporary.py`;
  0.4/0.5 share-policy inputs additionally need `qgv_555_official_share.py` and
  `qgv_555_share_review.py`.
- Existing sector/dual foundation: `sector_qgv.py`, `sector_qgv_registry.py`,
  `sector_qgv_reference.py`, `sector_qgv_partial.py`, `dual_qgv.py`,
  `dual_qgv_delivery.py`.
- #541/#547: `personal_sheet_v.py`, `personal_sheet_v.js`, `kis_owner_price.py`,
  `kis_split_evidence.py`, plus the bridge ported here.

These are file dependencies, not a request to merge entire PRs. Runtime engine
hashes read the existing file locations; moving or omitting them breaks that
validation. Canonical already contains the official QGV kernels/configuration.
The synthetic fixture helper importing test code is not an operational engine.

A smaller existing `private_layer_qgv.compute_private_qgv` uses canonical calc23.1
and can emit `kis-qgv/1`; it has different partial-total and gate semantics from
555. It is an alternative for Main/owner review, **not** a substitute implemented
by this port. Any later 555 bridge needs the actual reader contract aligned as
well as both evaluation/reference anchors, dated financial/share/action inputs
and current-context official gate evidence.

## Actual evidence and acceptance status

Actual source, company-level diagnostics, anomaly reviews and Top500 action notes
are preserved only in the approved private handoff repository. Public artifacts
contain code, synthetic examples and aggregate counts/status; no actual prices or
company-level result table. Day-1 raw calculations are reused, not counted as a
new calculation increase. Projection/receipt checks, consumer contract acceptance,
browser verification, branch integration and deployment are separate statuses.
The SEC review does not silently replace current population symbols or establish
all-series security/corporate-action eligibility.

## Changed-boundary evidence

The retained day-1 run is preserved; the port adds file projection, not new scores.
The actual projection contains 517 series / 2,068 files. Maximum individual file:
56,989 bytes. Source/result pins and every newly written file were reopened and
checked. Numerical indicator recalculations and new eligible adoptions: 0.

Direct Node checks use the exact #550 consumer/Worker source
`52c0305903ad207d04bdc564cd95026a7508f17e`, without validator stubs:

| Boundary | Accepted / checked |
|---|---:|
| Chart payload | 515 / 517 |
| Analysis payload | 517 / 517 |
| Measures payload | 515 / 517 |
| Signal-day context | 517 / 517 |
| Payload plus actual Worker symbol route | 500 / 517 |

The 17 route rejections comprise two class-symbol mappings and 15 ETF series
outside the current Worker allow list. The former also fail chart/measures symbol
validation. Their original source symbols are preserved; no aliases or synthetic
identities are assigned. Main owns the verified mapping, intended ETF scope and
consumer update. `PATHS_READY_NOT_DEPLOYED` describes file syntax only: it never
asserts allow-list, authentication, browser or deployment acceptance. Browser
execution, workflow application, deployment and live-site verification: not done.

The seven requested anomaly cases have private SEC review/Top500 action records.
Planned versus confirmed dates, partial documents and unconfirmed vendor failure
causality stay distinct. No official population replacement or source price
substitution was performed. Detailed company/event rows are private only.

## Owner follow-up: two private display tiers and calc23.1 stage 1

`private_kis_reference.reference_files(files, contract, signal_day)` enriches the
existing output without changing adopted `value`, original reasons or counts.
`display.validation_tier=UNVERIFIED_REFERENCE`, `label=검증 전(참고)` and
`official=false` apply to diagnostic output. Each metric has a separate
`reference_value`; verified adopted values retain tier `VERIFIED`. Main must read
this field explicitly with its label, not promote it into official/adopted value.
`display.state=WITHHELD` suppresses reference values when a retained hold or raw
split-like jump is present. Chart RAW remains evidence with an explicit hold.
The CLI exposes this opt-in as `--reference`; previous callers remain compatible.

The versioned conservative review screen uses consecutive observed raw closes
within the final 100 sessions, minimum absolute move 30%, near ratios
1.5/2/3/4/5/10/20 and reciprocals, relative tolerance 8%. It generates a review
candidate, never a confirmed split or price correction. A supplied confirmed
split is handled by the existing split path. Future bars are excluded. MODP1
remains rejected; no comparison to MODP1 establishes an event. A zero-volume
retained hold stays separate. No trade-scope proof is inferred from a reference
volume value. These thresholds are a review policy, not a scoring/formula change.

`official_reference(payload, contracts, provider_links, day=..., calculated_at=...,
expected_payload_hash=..., expected_links_hash=..., expected_contract_hashes=...)`
uses canonical `qgv_official.prepare/price_status/engine_quotes/score/projection`.
Only the quote supplier changes to KIS raw daily close. There are **no 555
imports**. The minimum added file is `research/private_kis_reference.py`, using
the bridge/split/artifact helpers already ported here and canonical QGV kernels.
The provider lookup is pinned and matched to the original requested/returned
contract. It is not a verified fixed-security-ID claim. Adoption inherits the
explicit official identity/ADR/share-basis/action rules as a private reference
policy, not the prior strict 555 sidecar requirements. The share denominator is
the official weighted-average diluted proxy, not actual outstanding shares.
Explicit conflicts, held inputs and official corporate-action exclusions remain
blocked. Rank stays null; no official publication or TARGET change occurs.

This creates `qgv/latest.json` with existing `kis-qgv/1`, owner-private reference
label and separate source clocks, input pins, raw diagnostics, stages and counts.
Partial official-engine totals are reported separately from three-axis completion;
they are not 555 totals, investment performance or official 95% coverage.
The original technical-only manifest remains historical. Its former “555
 dependency” limitation does not apply to this separate stage-1 adapter.

Actual diagnostics are stored only in the private handoff. The reference screen
allows 496 operating code rows and 15 ETF series for display, withholding 6
operating rows (4 jump candidates plus 2 prior holds); original adopted counts
remain unchanged. A same-price-date comparison against public central V also
requires identical financial snapshot/hash and historical price inputs. Different
financial hashes cannot substantiate a price-only explanation. No current data
is relabelled as available on the historical evaluation date.

The former `exp_deciles/adapters/alpaca_bars.py` contained only a pure NY-midnight
session-date check, with no HTTP, SDK or external call. That necessary function
is now `exp_deciles/session_dates.py` with the same body, calendar and errors;
the misleading supplier adapter path is removed. No supplier is introduced.

Stage-1 actual result (price day 2026-11-13; financial input acquired/as-of
2026-11-15, retrospective current-input context, not historical PIT): operating
504 code rows, official-rule supplied closes 495; raw V diagnostic/any V role403;
V343; three axes342; engine totals481, of which139 are partial without all three
axes. The three-axis totals correspond to340/501 issuers. A total481 is **not**
481 complete QGV results or an official95% achievement. Nonprice V-axis preflight
(50% factor-weight reachability) is362; this is stricter than “any raw metric” and
must not be presented as a monotone raw-any count.

The public11/11 central file needs financial snapshot SHA256
`001e0f39b0b7a26fe782870d1a93cd82f08e5df88593915b8db8e579ce87d084`,
as-of2026-11-13T02:48:41.511898Z. The currently provided financial file differs.
Paired V values exist for357 rows including TARGET, but price-only attribution is
unverified (0 confirmed explanations). Request the exact original financial
snapshot and retained IEX quote/month-end inputs for a causal supplier comparison;
do not substitute current financial data or infer raw prices from public scores.

## Follow-up output policy and matched-input comparison

Owner instruction: **V missing means total missing**. The private delivery also
requires Q/G, so every row lacking any of the three axes has `total=null` and
`total_reason=THREE_AXES_REQUIRED`. `coverage.total` counts only delivered complete
totals. The 139 previously delivered partial totals are suppressed by projection,
not recalculation. Axis/factor scores remain unchanged; delivered total count is
342/504 code rows. Original engine counts remain diagnostic counts only, never
partial numeric total values in the rows. The suppression is idempotent. Canonical
calc23.1 and public outputs are unchanged. Every private row remains explicitly
`verification=UNVERIFIED_REFERENCE` pending proof review.

The requested11/11 price-only comparison requires Main's exact published central
financial bundle. As of this change, #437 has no delivery of that bundle. Do not
repeat the previous mismatched-input calculation. Pin the provided manifest,
financial input hash, population, model/config versions and retained IEX day/
month-end inputs; reproduce the original public baseline first. Only then replace
the current quote with KIS close. Separate quote-value differences, missing/held
prices, changed valid reference samples, history inputs, identity/action filters
and unexplained baseline mismatches. “Not evaluated” is not “unexplained zero.”

The private priority proposal orders shared security-class linkage, WAD share/
period anchors, then complete dated action-interval evidence. Each touches up to
499 issuers in the prior blocked set; these sets overlap. No499-verification
forecast or actual batch execution is implied. Required fields and source paths
are in the private `verification-priority.json`; execution awaits owner decision.

The six held-series SEC review found three stock-split cases, one non-split
spinoff/distribution, and two previously reviewed exchange/acquisition cases.
Private evidence distinguishes announcement, distribution, price-basis effective
date, original period and acquisition/review clocks. No price adjustment, hold
release or verification promotion was performed. A distribution of a different
company's shares is never a stock-split factor for the original company.

For Main's #437 schema proposal: keep `rows` as the existing object keyed by code,
`population` as the existing code list, `axes.V.score`, `total`, `total_reason`,
`price_status` and `coverage`/`stages`. An array would break existing `kis-qgv/1`
readers and needs a separate version; do not relabel it as the same contract.
Current metadata equivalents: financial_input_as_of/input_sha256, engine_version/
calc_version, calculated_at, layer=OWNER_PRIVATE and display. Rank remains null
(private scope, not official or personal-sheet rank). 100 sessions do allow V via
other valid factors under the official50% rule; own-history value stays missing
without sufficient eligible historical inputs. Slash symbols are already accepted
by #551/#556 normalization, but explicit Worker/reader mappings remain Main-owned.
A score or paired-engine match alone never grants VERIFIED identity/share/action
status; that is a separate producer evidence decision over the exact dependency
window and scope.
