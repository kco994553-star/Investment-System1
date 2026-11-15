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
