# discovery-company/v1 — current evidence-based discovery

Owner instruction, 2026-11-06. This is a research selection contract, not a QGV
model, recommendation, public publication approval or historical universe.
Codex owns the new research producer/CLI/tests; Main owns existing list/detail,
authorization, publication, workflows and shared CI registration.

## Authority and reuse

Lynch chapter 7's six types and chapter 8's business characteristics are the
owner-supplied conceptual references. No book quotation/page has been newly
verified in this change. Six type labels are descriptive only: SLOW_GROWER,
STALWART, FAST_GROWER, CYCLICAL, TURNAROUND, ASSET_PLAY. Empty tags mean unclassified.
Multiple substantiated tags are allowed. Loss/low P/B alone cannot establish the
last two types. Existing QGV company-types are a different taxonomy.

**The six selection gates, evidence schema and state rules below are our initial
operating rules, not a mechanical formula claimed to be in the book.** No counting
of chapter-8 traits, automatic numerical ranking, awareness threshold, or QGV
weight change is introduced.

Reuse: `contracts.global_universe.IssuerIdentity` for upstream company references;
`ingestion.RawDatasetStore` for raw receipts/immutable source bytes; existing SEC
collection/retained manifests as inputs (no collector in this feature). Existing
RIG `LineageIndex` handles relationship/event lineage; this producer does not
create relationship events merely to select a company. RIG is isolated by its
existing dependency guard; its internal records are not imported. Only evidence
and history content IDs are generated here, never new security identities.
#472's qualitative and
intangible evidence remains a separate reviewed input, not source fact. RIG P4
network-discovery labels and QGV company-types do not determine selection here.

## Three layers and deterministic review

`evidence` contains only source-extracted values with company_id, document_id,
SHA-256, source URL, exact locator, publication date (time may be unknown), period,
acquisition time, unit and original region/basis. Local extractors verify bytes
against the existing receipt and select a JSON pointer or exact XML element ID.
An analyst/AI sentence cannot be supplied as the extracted value. Missing source
metadata stays null and blocks confirmation when necessary. Source assertions
are what the issuer reported, not independent proof of competitive advantage.

`judgments` contain claim, supporting evidence IDs, counterevidence IDs, category,
topic, CONFIRMED/UNCONFIRMED/REFUTED, rationale, reviewed_by, rule_version, core and
material flags. Confirmation is a recorded analyst review, never an automatic
semantic verdict from source text. Human-readable summaries are generated from
these reviewed statements and always carry IDs/status/counterevidence. No free
standing generated summary is promoted to fact. Every source field can be audited.

Required core categories: IDENTITY, BUSINESS, DISCOVERY, ATTRACTIVENESS,
COUNTER_REVIEW, CURRENTNESS. All must have a confirmed, sourced core judgment,
reviewer and reason before a manual SELECTED transition. Any additional unresolved
core claim or material REFUTED claim also blocks. Automatic runs always start
CANDIDATE even if all gates pass; IN_REVIEW then explicit reviewed selection.
Currentness is assessed against the claimed period and new information. No
invented blanket expiry horizon. Missing coverage stays unknown.

`DISCOVERY` explains a verified business characteristic that merits investigation.
It need not claim low awareness. `awareness.consumer_contact` and
`awareness.market_attention` are distinct judgment references or null. Missing
institutional/analyst data remains unmeasured; B2B, failed searches and missing
records do not establish low awareness. No percentile field is supported.

SIGNAL topics distinguish SPINOFF, INSIDER_OPEN_MARKET_PURCHASE,
INSIDER_COMPENSATION, BUYBACK_PLAN, BUYBACK_EXECUTED and SHARE_COUNT_CHANGE. A
reviewed signal is not proof of value creation. REGION topics distinguish REVENUE,
PRODUCTION, HEADQUARTERS, PERFORMANCE, REPLICATION, PROFITABILITY, EXPANSION,
SATURATION, PROTECTION, ACQUISITION_EFFECT and FX_EFFECT. Retain issuer taxonomy
and revenue attribution basis; no country shares or profitability inferred from
absence. All unknowns and material counterevidence survive display generation.

## State and display contract

| State | General selection list, after separate access/publication gate | Mark |
|---|---|---|
| CANDIDATE / IN_REVIEW | excluded | null |
| SELECTED | included | SELECTED |
| REVIEW_REQUIRED | retained | REVIEW_REQUIRED + reason |
| SUSPENDED / REMOVED | excluded | null |

Direct links read the same state within the caller's existing permissions.
`display.list_eligible` is **not** public authorization. `publication_approved`
is always false in this producer; Main must use the existing publication decision.
QGV joins only through `qgv_ref.company_id`; no copied score/rank fields.
First selection date is null before selection and preserved thereafter.

Transitions: CANDIDATE→IN_REVIEW→SELECTED;
SELECTED→REVIEW_REQUIRED→SELECTED/SUSPENDED/REMOVED;
SELECTED→SUSPENDED for IDENTITY_ERROR/CORE_EVIDENCE_ERROR/MATERIAL_REFUTATION.
Reopening a suspended/removed record requires IN_REVIEW, then the full gates.
Evidence aging requests review, never immediate negative evaluation.

An update event declares the affected evidence IDs, document ID/hash, timestamp,
kind and reason. Only dependent judgments are scheduled for review. A document
revision marks affected judgments UNCONFIRMED (or REFUTED for an established
critical error); it cannot silently keep a confirmed core assertion. Same event
ID with different content is rejected; same event repeats are idempotent. An
unrelated document changes no selection state. Original evidence is retained;
new observations use new IDs. Events, selection reasons/times, original snapshots
and rule versions are append-only. A result points to its predecessor hash.

## First handoff and execution

`schema.json` is the output contract; `synthetic.json` contains six states and
literal expected list/mark/null behavior. Main can connect existing screens now,
without real-company selection. Text is plain text: escape it in the reader.
Synthetic company IDs and example.invalid source URLs cannot be mistaken for
actual research. UI filters cannot change original scope, state or QGV rank.

Offline command: `PYTHONPATH=implementation/src python implementation/tools/discovery_company.py --job /private/job.json --output-dir /private/results`.
Job: explicit company registry, local document receipts + hashes + extraction
selectors, review judgments, as_of, review scope and optional previous record / events.
The CLI emits content-addressed records and summary; no network, AI API, pricing,
workflow or public write. Actual records must stay in the approved private repo.
Never pass a public output directory for held real-company inputs.

Main requests: add the new targeted test to shared CI when integrating; no runtime
dependency is added. JSON Schema checking is test-only. Contract integration and
publication remain Main-owned. Actual selection does not imply awareness measured,
whole-market coverage, investment performance, or historical PIT completeness.
