# Global Language & Search implementation baseline

Presentation/navigation contract v1 — 2026-09-30. Candidate until current CI passes.

## Fresh repository audit
GitHub API refs and original files read in this session; historical reports are not the baseline.
Local shell/git execution is unavailable, so remote API fetches replace a local git fetch.
Canonical: claude/investment-system-top500-validation-alrugm @ b8e39a2196a6d7794a04a0cd5393c68329e126ca.
Web: feature/web-mvp-v1 @ a4e49c83f5783c19617fb609b8f95b179cb13e84.
PR #5 is OPEN/DRAFT, unmerged. Web is 6 commits ahead, 0 behind canonical.
Separate child branch: feature/global-language-search-v1. No rewrite or automatic merge.
No AGENTS.md found in the fetched recursive Web tree.

Read actual Web app/builder/assets/tests/workflow; legacy render_app/NAV_PAGES; QGV identity/models/
Leaderboard consumers; Technical and Macro engines; Portfolio producer contracts; RIG Language/terms/
view preferences/renderers; Prompt Library UI/catalog payload and boundary tests.
Track A recovery ref: a79642f7aa174cc37b981298d0ff1cec6b04e974, already integrated into canonical.
Track B personal P0 packages remain untouched.
Track C remote ref: aca11a699ede7e6a20e72e22cc49ba56038aa760 (latest commit records TC-D3P-003 v1 approval).
The current Track C branch is more advanced than older Web documentation; none of its phases are imported or modified.
Track D ref: da86dfc26dcaa5c32c60762683dcca702a0c57b8, latest commit documents P5 hold.
Track E ref: d226481e1b49e0910642478ae80545598e2e5a98; canonical Frozen catalog/UI reused.
No Investor-QGV runtime registry/profile/methodology found in this baseline. Default INVESTOR results remain empty.
Existing News Network #lang/Language.EN/KO/EN_KO is a label presentation setting, not an article source-language filter.

## Language boundary
AppSettings lives at localStorage investment.web.v1.settings, separate from existing interests/groups.
display_locale: ko-KR (default), en-US. source_language: all (default), ko, en.
The existing News language selector is adapted through the existing relabel API to global display_locale.
News source_language is producer article metadata. The preference filters News only, never rewrites provider language.
Unknown source language remains visible with the default all filter.
Locale changes only labels/number formatting and supplied localized summaries; no engine calls, ranking,
holdings, PIT/available_at, original identifier or source changes. Source Evidence is original JSON.

String fallback: requested locale -> ko-KR -> en-US -> canonical label, ignoring absent/empty strings.
No translation service or transliteration. Missing translation never hides an entity or snapshot.
UI strings and financial terminology are separate. ko-KR may display Free Cash Flow(잉여현금흐름),
Drawdown(낙폭), Operating Margin(영업이익률); ordinary UI labels stay compact.
AppLanguage.text/term/status/fallback are reusable for Reports/Alerts/Investor-QGV consumers.
Producer headline_localized/summary_localized/reason_localized and snapshot presentation maps are optional.
Frozen Prompt bodies, hints, names, input variables and copied previews remain source_original; product bridge translates
controls/status labels only. Track D labels use its existing Language/relabel extension.

## Search boundary
Python entity_catalog creates a separate entities.json from the read-only bundle. data.json remains byte-value equivalent.
COMPANY:<existing company_id>, INDUSTRY:<id>, INVESTOR:<id>, MACRO:<id>; extensible THEME/PORTFOLIO/NEWS/PROMPT.
COMPANY identity comes only from companies. The adapter reuses OFFICIAL_PORTFOLIO_V11 identity metadata by company_id,
never ticker identity guessing, and merges separate ID-keyed presentation aliases.
Companies may supply official_name, localized_names, aliases (locale -> text list), historical_names,
historical_tickers, industry/industry_id and metadata_source.
Companies without name metadata remain visible and searchable by their existing ticker; no invented identity/name.
Current curated Korean aliases cover common registered IDs, including NVIDIA and ASML. This is not a complete
translation of all 500 issuers. Producers can add names/aliases without new entity records.

Built-in navigation records: Semiconductor presentation taxonomy, CPIAUCSL (existing provisional FRED mapping).
These contain no financial values, Universe membership decisions or investment classification inference.
Additional search_entities require type, canonical_id, canonical_label, source. No seeded investor/profile.
Duplicate canonical type/id is rejected. Historical aliases are navigation labels, not PIT assertions.
The public demo tool supplies explicit TEST company_id -> issuer_id links instead of duplicate fixture company records;
no ticker/name identity inference is used.

## Deterministic ranking and fuzzy policy
NFKC -> lowercase -> Unicode apostrophe/dash normalization -> punctuation as spaces -> trim/collapse.
Ticker comparison additionally ignores normalized spaces (NVDA, $NVDA; BRK.B/BRK-B equivalent for search only).
Original query and normalized query are available in returned results; no query telemetry/network logging is added.
Order: exact ticker, exact canonical name, exact localized name, exact alias, prefix, substring, fuzzy.
Tie: edit ratio (fuzzy only), canonical entity type/id by codepoint. Input order and locale never affect ranking.
Substring requires >=2 codepoints. Fuzzy requires >=4; max 1 edit for 4–7, max 2 for >=8,
edit ratio <=0.25, length bounded at 128. Optimal-string-alignment distance supports adjacent transposition.
No aggressive fuzzy for single-letter/short inputs. Alias database contains no manual typo variants.
One result per canonical entity. Explicit selection navigates COMPANY results to the existing #company/<id>.
Colliding tickers produce distinct candidates, never silent identity resolution; search does not close C-08 TEL.
Search ranks are never QGV/Leaderboard ranks or buy signals. UI states this and shows supplied auxiliary metadata only.
window.investmentSearch(query, options) returns match_type, matched_label, rank, edit ratio for debugging.
No Elasticsearch, framework, service or new package dependency.

## Integration and protection
Search -> canonical ID -> existing producer snapshot -> localized presentation.
Default frozen Universe payload and all producer data/provenance preserved. Existing Leaderboard rows stay upstream order.
All Track A/B/C/D/E source/test/Frozen artifacts remain unchanged. Only product UI, public demo tooling, additive tests,
validation workflow and scoped docs change. No scoring, portfolio calculation, Holdout, methodology or PIT changes.
No D3-P policy decision required for these reversible presentation/search details.
Integration order: review/normal-merge PR #5, then this child branch (or review both together). Never auto-merge.
Current producer/hosting blockers from the Web baseline persist. Investor profile availability requires real registration
and future reviewed producer data; no research methodology is added.
