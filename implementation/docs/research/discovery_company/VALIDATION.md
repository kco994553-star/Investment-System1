# First implementation validation — 2026-11-06

Base canonical ab6a83c3be2276abdcf855c71c5f273926e2dcc4. Draft #503; no stacked
research dependency. QGV, collectors, UI, authorization, shared guards and CI lists
are unchanged. Contract: discovery-company/v1, rules: discovery-rules/1.

New tests were observed failing before implementation. Initial 16 cases plus six
independent-review counterexamples now pass (22). Existing RIG/common identity
isolation suite: 15 pass. Private-boundary/direction tests: 32 pass before the
review fixes; required guards are run on the final changes separately. CI status
and exact final SHA are recorded in the PR, not assumed from local success.

Independent review found and this branch fixes: rehashed snapshot bypass of state
history, material refutation remaining visible, output outside Git incorrectly
assumed private, removed opposing references disappearing from the summary,
duplicate events rejected as the clock advances, and no identity for corrected
provenance. Each has a failing-then-passing synthetic regression. No known deferred
review finding. Initial RIG direct import also failed its isolation test and was
replaced with the upstream common issuer contract; its guard was preserved.

First actual execution: **1 held issuer / 5 source extracts / 10 judgments,
6 confirmed / 1 CANDIDATE / 0 SELECTED / 0 SUSPENDED**. Existing code/CIK was matched
to source issuer-name/CIK. Business and discovery rationale were supported;
durable attractiveness, complete counterevidence review and current completeness
remain unconfirmed. Regional disclosure and risk are partially supported; type,
strength, signals and awareness remain unconfirmed/unclassified. This is a
one-company review denominator, not whole-market coverage. Source facts were
compared to a held quarterly report; no new document, price, AI service or external
request was used. Company-level inputs and output stay in the approved private
handoff, separate from synthetic.json. Selection count was not forced.

Cost: 2 existing local source files + original release receipt; 1 XML document
provides 5 exact-ID extracts, 10 explicit analyst judgments; network requests 0,
external AI calls 0, incremental data cost 0. No scale/throughput claim. Expansion
requires current business/attractiveness and contrary-evidence coverage per claim,
not C2 or historical universe completion.

Main: consume the schema and six synthetic states, retain risks/unknowns, escape
all source/analyst text, join existing QGV by company_id, preserve publication and
private authorization gates. Add test_discovery_company.py to the appropriate CI
list (test-only jsonschema is already used by repository tests). Actual browser,
auth flow, public posting and periodic updates are not implemented by this PR.
