# Policy impact v1 — Codex data handoff

Scope: function 4.5, US federal tariff/export-control/industrial-subsidy curated
samples. Owner attachment Policy_Impact_Design_and_Prompts_20261107.md §§4–10.
Canonical base ab6a83c3be2276abdcf855c71c5f273926e2dcc4. Data/research only.
Main owns frontend, final screen input contract, CI lists, shared guards,
workflow/Secret/operations, decisions, merge and deployment.

## Contract and invocation

`policy_impact/contract.py` is the validator; `policy_impact/build.py` is the
append-only/as-of/public projection. No network, scoring engine, scheduler or
external AI service. `policy_impact/contract.json` lists fixed fields/enums;
`synthetic-job.json` and `synthetic-view.json` are public artificial fixtures.
The current public envelope is `policy-impact-view/2`; private output remains
`policy-impact-view/1`. Both carry the factual `policy-impact/1` bundle.
Retained public v1 fixtures are historical contracts, not implicit publication
permission. See the availability/publication section below and
`synthetic-public-v2.json` for the current public contract.
`current_policy_revisions` identifies current visible revisions; the bundle also
retains referenced previous revisions. Render old hypotheses REVIEW_REQUIRED,
not as current assertions. `historical_pit_eligible` is always false.

```
PYTHONPATH=implementation/src python implementation/tools/policy_impact.py \
 --job implementation/docs/research/policy_impact/synthetic-job.json \
 --output /tmp/policy-impact-synthetic.json
PYTHONPATH=implementation/src python -m pytest implementation/tests/research/test_policy_impact.py -q
```

Job keys: bundle, company_ids (trusted existing company registry IDs), as_of UTC;
optional public, public_macro_ids, watch_publication_permissions,
query_timezone (IANA, default UTC), previous
(the full prior input ledger, not a projected view). CLI validates, builds and
atomically replaces output; a rejected input leaves the previous file intact.
Real output is required outside Git checkouts, mode600. stdout contains counts
or error code/path, no company values. Main's authenticated runner chooses trusted
paths/registry, never an arbitrary user URL. No source() route is implemented here.

## Identity, time and evidence

Policies have stable policy IDs and separate immutable revisions. Identity uses
issuer + document number + verified relation; absent document numbers permit an
explicit issuer/official-URL mapping. Same policy must retain issuer/type/
jurisdiction and one nonbranching revision chain. A title or news cluster ID is
never an identity rule. No automatic legal applicability inference.

Rows and review records are append-only. Same-ID content changes are rejected;
new reviews are separate records, projected at query time. Independent reviewers
are distinguished from authors and AI review is never labelled human review.
Dates retain DATE/null timezone. Acquisition and review are actual UTC instants.
GDELT source_seen_at is first discovery, never publication. Effective dates do
not automatically change lifecycle status. Partial policy units use independent
IDs and an evidenced parent; subsidy projects have their own scope/stage.

Availability includes all referenced source revisions, revision-relation evidence,
policy/exposure dependencies, recording and review times. Unknown/future evidence
cannot enter past views. `response.as_of` is query time; `bundle.policy_as_of`
retains actual confirmation time, or null when no confirmation is available at
that query. generated_at is artifact generation, not a policy check. Freshness and
refresh future metadata is removed with explicit history-unavailable reasons.
Review due uses the chosen query timezone and date, never a new stale threshold.

Sources have hash-pinned content; display has only summaries, URLs and locators.
The exact nested allowlist rejects private objects in metadata/text arrays as
well as root fields. Unknown private macro references must be UNAVAILABLE with
no numeric value. Company identity is a supplied existing registry association,
not ticker/name matching or a new security ID. Regional revenue evidence and
policy_applicability remain independent; ratios are null+reason when unknown.

## Reuse and dependency boundary

- #483 864c40ea1beccee40d9f966ffede2ddb2e8d065c: reuse normalized `news_update`
  link/title/source_seen_at metadata in `from_news_reference`. No new feed enum,
  grouping ID policy key, collector, title-based facts or publication inference.
- #477 a90a93f392310dff92ebf5dd5131f62c2ae68d19: preserve its distinction between
  observation/publication/acquisition and source version availability. Macro
  values are not copied. Public registry IDs are references only; no macro model
  restart or gate change. The policy dependency maximum is specific to its typed
  source/review graph, not a second macro reconstruction engine.
- #503 998414635aa4f1899748b1b76fc7ebf3ddc9d12f: `from_discovery_fact` consumes its
  SOURCE_EXTRACT receipt, locator, company ID and period; no second XML/JSON fact
  extractor. Regional attributes remain facts, not policy applicability.

These PRs are semantic input dependencies, not unmerged runtime dependencies.
The offline job runs from canonical + this PR. Main need not merge unrelated
preservation Drafts or recalculate the delivered result.

## Refresh preparation (no fetch activated)

Pure `collection_outcome` distinguishes valid complete empty results from 429,
parse error and truncated pages. Only complete intervals advance checkpoints.
`retain_good` keeps content/confirmation/last-success timestamps during failure.
Partial source results retain source-specific status; no policy is withdrawn
because a source fails. Invalid builds do not replace output.

First future adapter: Federal Register API, no API key per attached official
research. Propose once/day, 7-day overlapping date windows plus tracked document
IDs, dedup by agency/document/revision hash; split date intervals above the 2,000
result paging ceiling. Bound requests/pages/bytes and honor Retry-After. Request
rate, operational rights and exact schedule remain to be verified/approved by
Main. USTR/BIS/NIST are supplemental official review sources; API/RSS and reuse
conditions unconfirmed. Government HTML and legally official PDF are distinct.
No operation trigger, account, paid service, workflow or permission was added.

## Actual historical cases and gaps

Three official webpages were manually opened for the owner-requested case review,
one per type. Response URLs, actual acquisition instants, sizes and SHA256 are in
the private manifest, separate from publication dates. Independent AI source
review (not human review) matched the retained HTML. No original HTML is copied
into repository fixtures. These are historical cases, current status UNKNOWN.

- USTR FR2024-21217, 89FR76581: 2024 entry cohort September27; 2025/2026 cohorts
  and AnnexB exclusion dates are distinct. The sample does not collapse them.
  Company/product exposure and present legal state are not established.
- BIS FR2023-23055, 88FR73458: general November17,2023 date and instruction11's
  separate January1,2026 endpoint. No company licence/product application or
  present successor-rule state established.
- NIST December10,2024: Micron NY/ID FINAL_AWARD announcement has milestone-based
  future disbursement; Virginia PMT is separate. Award ceiling is not cash paid.
  Existing NASDAQ:MU/CIK registry link is separate from security identity. Actual
  project exposure and a conditional funding hypothesis are reviewed separately.

No corporate filings were newly collected. Missing tariff/export exposure needs
specific product/origin/end-user/licence evidence and matching corporate filing
periods; headquarters/sector is insufficient. Missing subsidy payment needs
actual disbursement evidence and company receipt reporting. Current policy
status needs successor/amendment/suspension checks. Legal PDFs were not retrieved.
Three case checks do not measure market coverage, causality, returns or accuracy.

## Verification and Main responsibilities

P01–P19/P22 data cases: repeat input, immutable revisions, partial scope, date
precision, dependency times, nulls, stable company registry reference, invalid/
cyclic refs, stale hypotheses, failures/truncation, preserved good output,
independent review/public boundary, subsidy stages and synthetic/real separation.
P17 additionally calls the existing QGV engine and existing playbook macro gate
with fixed synthetic inputs before/after policy changes. No operating policy is
altered. P19 validates URL safety; HTML strings remain text for Main rendering.
P20 navigation and P21 accessibility are Main-owned, not claimed tested here.

Fresh independent review found/fixed missing revision-relation dependency times,
nested metadata/type leakage, policy chain identity/forks, future freshness and
confirmation-time restamping. Counterexamples are retained as synthetic regressions.
Main must confirm the envelope/null semantics and fixture hashes, implement strict
reader/text rendering, source()/auth/list/detail links, and add the new test to
its CI list. Contract proposal delivered at #437; Main acceptance and actual UI
integration are pending. No synthetic fallback for production data absence.

Review records additionally require `recorded_at`, separate from `reviewed_at`:
a review entered later cannot backfill an earlier system query. Draft rows stay
immutable UNREVIEWED; appending an independent record promotes the as-of view.
Output temporary files are unique, private and atomically replaced.

Actual execution: synthetic sources/policies/exposures/hypotheses = 3/3/3/3;
separate private REAL_REVIEWED output = 3/3/1/1, all three current lifecycle
states UNKNOWN, historical_pit_eligible=false. The one project exposure and one
conditional hypothesis passed separate AI review (2026-11-07T01:04:55Z). Tariff
and export-control company exposures remain unconnected; no artificial company
was added. NIST's project-specific award is not a corporate-filing or cash-receipt
confirmation. Actual numerical amount is omitted from the output schema v1;
subsidy stage and scope are preserved. No public publication approval is implied.

Affected tests: 45 policy data cases passed; privacy static suite 28 passed.
P20/P21 and browser safety rendering remain Main-owned. Canonical is unchanged;
Draft code availability is distinct from Main contract acceptance/UI integration.

## Federal Register offline update adapter (2026-11-07)

`policy-fr-replay/1` adds `mode=fr-replay` to the existing policy CLI. See
`policy_impact/fr-synthetic-job.json` and `fr-synthetic-result.json` for the public
fixture. It reuses the pure `request_limits` Retry-After parser/size limit and
policy collection_outcome/retain_good. A validated max_requests setting and the
existing loop counter bound requests without importing operational providers.
It does not add an HTTP client, scheduler,
DB, policy identity resolver or automatic publication path.

```sh
python implementation/tools/policy_impact.py --job implementation/docs/research/policy_impact/fr-synthetic-job.json --output /tmp/fr-replay-result.json
```

Input: existing replay state, explicitly typed responses, observation `through`,
replay `now`, optional versioned settings and previous published `last_good`.
Each response retains its request URL/range/page, status, acquisition time and
original JSON response text for RETAINED_API. Synthetic JSON objects are explicitly
SYNTHETIC. HTML cannot validate API compatibility. Output: appended source versions,
UNREVIEWED candidates, attempt outcomes, next_plan, incomplete/blocked ranges,
last_attempt/last_success/retry_at and retained_good. No real request is executed.

Default plan: publication-date windows7days, overlap7days, per_page100,
max_pages20, max_requests12 per invocation, body limit1MiB. It also rotates tracked
document refreshes and a bounded historical reconciliation sweep. No finite overlap
guarantees discovery of all arbitrarily late corrections; only completed requested
intervals as observed at acquisition are claimed. `completed_through` is not a
policy-effective-date, current-status, full-text, or historical-PIT checkpoint.
The first run needs an explicitly chosen scope_start/through; this is not an
approval to collect data. Official API response compatibility/rights/limits need
actual verification before Main enables collection; defaults are our client caps.

URLs use only `/api/v1/documents.json` and tracked `/documents/{number}.json`.
Content hashes cover normalized API metadata, **not fetched legal full text**;
unchanged metadata cannot prove unchanged legal text. Full response hashes are
retained. Same ID/content deduplicates; changed content appends immutable evidence;
A→B→A records a review event while reusing version A. A new document/correction does
not establish policy revision relationships, lifecycle, scope, corporate exposure
or an impact hypothesis. Every candidate remains UNREVIEWED, policy IDs null,
automatic_publication=false. Publication precision stays DATE when only a date exists.

An unfinished interval resumes its next page without planning a concurrent page1.
Page-count drift/duplicate IDs restart that interval from page1. Over-limit ranges
split by date; an over-limit single day remains blocked for explicit scope refinement.
Only fully reconciled pages advance the contiguous checkpoint. Partial candidates
are retained for review, not marked as a complete source scan. 429 honors Retry-After
(fallback600seconds); unrepresentably large waits saturate at year9999 without
shortening the provider wait. No retry is performed here. Parse/HTTP/partial failures
retain the previous good policy and original confirmation/last-success timestamps;
FAILED/INCOMPLETE never become NO_NEW_ITEMS. Private mode is decided by replay state,
not any unrelated legacy bundle field, and cannot write into a Git checkout.

All replay validation here is synthetic. No retained Federal Register API response
was supplied; the three previously reviewed government HTML documents are not reused
as API fixtures. Actual API verification, scheduled execution and public UI are not
claimed. Main must persist the returned checkpoint atomically, preserve the prior
normal policy bundle, honor request/retry limits, and pass actual retained responses
only after separately approved collection. No new Secret is requested by this code.

## CI boundary fix and Main contract followup (2026-11-07)

The actual f086e3ca build run42333107495/job128283873663 failed P17,
`test_p17_no_operating_modules_changed_or_imported`. Local reproduction confirmed
that the FR adapter imported operational providers. The test remains intact.
`request_limits.py` now owns the unchanged pure Retry-After parser and1MiB limit;
Codex-owned #483 `providers/news_feeds.py` reexports the same function/constant.
No duplicate parser exists. RSS retains its separate standard-library date import.
The FR loop's existing bounded max_requests check/counter replaces the unnecessary
DART class dependency; DART code is unchanged. No operating provider is imported
by the policy package. Main was notified of these exact shared files in #437.

### Availability and publication are independent

`watch_items[].availability` is now an enum in contract.json:
- PUBLIC_REFERENCE: an available public-source reference; not publication approval.
- UNAVAILABLE: unavailable; never false/0.
- UNKNOWN: availability unestablished; never public permission.
Missing/invalid enum values fail validation. Private views preserve UNKNOWN.
`build` additionally accepts `watch_publication_permissions`, a trusted caller map
from `kind:reference_id` to ALLOWED/PRIVATE_ONLY/UNKNOWN. Missing permission means
UNKNOWN. Public watch items require both PUBLIC_REFERENCE and explicit ALLOWED;
unknown availability still fails even if permission is ALLOWED. This parameter
controls projection, not permission to publish/enable a workflow.

The changed public semantics are **policy-impact-view/2**, with the same factual
bundle policy-impact/1. Private output stays policy-impact-view/1. Retained public
v1 fixtures/history remain untouched; they are not automatically republished under
v2. `synthetic-public-v2.json` is the new example. Main #511's strict v1 reader must
explicitly support v2 and update expected hashes/variant generation. Its green CI
at e0bb68dd does not validate this newer code.

### Titles and reviewed news navigation

Optional `policy-impact-navigation/1` is a separately versioned sidecar, bound to
the exact base-view digest. It preserves existing policy/revision IDs. It contains
`titles` (official_title, explanation_title_ko, RESEARCH_SUMMARY origin, original
source ID/revision/hash, h1 locator and extraction time) and `news_links`.
Original title-as-ID ledger rows are not overwritten and no fictional legal
amendment is created for a presentation correction. Main joins by policy/revision
and shows official title, Korean explanation and identifier separately.

Existing news has group_id/company_id/link rather than a per-article ID; retain
that exact existing reference tuple. Never reuse the news group as policy ID.
A news link pins the article metadata revision hash, exact policy revision,
independent reviewer, reviewed/recorded times, explanation and explicit article/link
publication permission. Policy availability at review time is checked by the
existing projection via reproject_view, including its source and review-record time closure. Public navigation requires view/2; unknown policy_as_of stays null during re-projection.
Changed metadata/revision, self-review, future references or unknown permission
cannot produce a public link. A source first-seen time never becomes publication.
Links say DISCOVERY_REFERENCE_ONLY/evidence_effect=NONE/application NOT_ASSESSED.
`from_news_reference` remains SOURCE_UNVERIFIED; policy sources still require
VERIFIED. The sidecar never inserts news into policy evidence or hypotheses.

CLI mode=navigation consumes view/navigation/as_of/public and hash-pinned
`title_sources`. It recomputes each official title from the retained original bytes
and exact h1 index. A legitimate source hash with fabricated title text is rejected.
Output uses the existing atomic/private CLI writer. Main fixtures:
`navigation-synthetic-{job,view}.json`, `navigation-synthetic-source.html`.

```sh
python implementation/tools/policy_impact.py --job implementation/docs/research/policy_impact/navigation-synthetic-job.json --output /tmp/policy-navigation.json
```

This run: synthetic1 title/1 news link; private retained3 official titles/0 news
links. No new policy/exposure/hypothesis or source3 case review. The private sidecar
is preserved separately and requires Main reader integration. No public posting.

### Minimum actual API compatibility acquisition proposal (not executed)

No retained API response is present in the identified handoff; only the already
reviewed HTML sources exist. Propose **one free GET, one list-response file**:
`https://www.federalregister.gov/api/v1/documents.json?conditions%5Bpublication_date%5D%5Bgte%5D=2024-09-18&conditions%5Bpublication_date%5D%5Blte%5D=2024-09-18&order=oldest&per_page=100&page=1`.
Bound to one day, first page, at most100 metadata entries; expected bytes unknown,
download cap1MiB. Stop on error/429/redirect/HTML/over-cap; no retries, next page,
legal-text fetch or automatic policy promotion. Preserve raw response, request,
status/headers/acquired_at/byte count/SHA in the existing private raw handoff.
This tests actual list shape/normalization and partial-page handling only. It does
not prove full pagination coverage, current policy state or historical PIT. Main
owns execution after separate owner approval; no API request was made here.
