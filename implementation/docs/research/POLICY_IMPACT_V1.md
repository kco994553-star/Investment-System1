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
The envelope is `policy-impact-view/1`, its `bundle` carries `policy-impact/1`.
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
optional public, public_macro_ids, query_timezone (IANA, default UTC), previous
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
