# Global Language & Search implementation baseline

Recorded 2026-09-30 UTC. Status: IMPLEMENTED / REGRESSION PASS / READY FOR INTEGRATION REVIEW.
Branch: feature/global-language-search-v1.
PR: https://github.com/kco994553-star/Investment-System1/pull/6 — OPEN/DRAFT, stacked on PR #5.
Tested code HEAD: 82ae07c5f0758038abda98cd8db9e0a0f2de1ee3.
The final baseline-record commit changes scoped documentation/evidence only; code remains exactly this tested SHA.

## Verified outcome
Global ko-KR/en-US display_locale, deterministic fallback and terminology; independent News source_language.
Existing Web MVP shell, company detail, News Network and Frozen Prompt Library reused.
Ticker/official English name/localized name/Korean-English aliases/prefix/substring/conservative transposition fuzzy.
Canonical COMPANY/INDUSTRY/INVESTOR/MACRO type contracts; future type extension.
NVDA/nvda/NVIDIA/NVIDIA Corporation/엔비디아/nvida/nvdia/엔디비아/nvd/엔비디 -> COMPANY:nvda.
ASML/에이에스엠엘 -> COMPANY:asml; 반도체 -> INDUSTRY:semiconductor; CPI -> MACRO:CPIAUCSL.
No fake 버핏/investor profile. Real producer registration is required.
Search rank is independent of QGV/Leaderboard; details use existing canonical IDs.
No new service, package dependency or calculation API.

## Current execution evidence
Successful PUSH workflow on exact tested code:
https://github.com/kco994553-star/Investment-System1/actions/runs/36709513419

| Check | Result |
|---|---|
| Full repository pytest (existing + additive tests) | 409/409 PASS, 14.65 seconds |
| Search + locale Node regression (same shipped modules) | 26/26 PASS |
| Existing Web MVP E2E, unchanged test script | 10/10 PASS |
| New Global Language/Search browser checks | 8/8 PASS, zero page errors |
| 360/390/1280px search/settings and existing route layouts | PASS, no horizontal overflow |
| QGV/Technical/Macro/Portfolio JSON and numerical state during locale changes | exact equality PASS |
| Original identifiers/news raw data/provenance | exact equality PASS |
| Leaderboard supplied row order/ranks | unchanged PASS |
| News source filter and display locale independence | PASS |
| Frozen Prompt payload/preview; Track D viewport state | unchanged PASS |
| Corrupt settings storage preservation | PASS |
| Default frozen Universe/500 canonical company identities | unchanged PASS |

Node timing: 509 demo entities, 100 repeated typo queries, 0.50170223 ms/query mean on GitHub runner.
This is a small-universe benchmark, not a production latency guarantee.
Artifact: https://github.com/kco994553-star/Investment-System1/actions/runs/36709513419/artifacts/11093536478
Archive SHA256: 2a4045992e7fc97c3f1d651d18213cf963de86a81c5b10c1932683dba2560894.
Artifact contains existing/new browser JSON evidence and screenshots. No manual visual-review claim.

Initial runs exposed new-test setup issues (hash navigation retained pre-fixture data; collapsed Evidence innerText
was empty). Both checks were corrected; none required relaxing the assertions or changing numerical/source data.
Current successful run supersedes those failed attempts.

## Changed files relative to Web MVP HEAD
- product/entity_catalog.py
- product/web_mvp.py
- product/web_assets/app.js
- product/web_assets/entity-search.js
- product/web_assets/locale.js
- product/web_assets/index.html
- product/web_assets/style.css
- product/web_assets/network-bridge.js
- product/web_assets/research-bridge.js
- implementation/tests/test_global_language_search.py
- implementation/tools/build_web_mvp_demo.py (explicit public TEST identity map)
- implementation/tools/global_language_search_test.js
- implementation/tools/global_language_search_browser_test.js
- .github/workflows/web-mvp-validation.yml
- implementation/docs/global_language_search/CONTRACT.md
- implementation/docs/global_language_search/STATUS.md
- implementation/docs/global_language_search/evidence/validation.json

The product paths above are under implementation/src/investment_system/.
Existing tests and upstream code are unchanged. Demo mapping is fixture tooling, not a production identity resolver.

## Canonical divergence and Track impact
Canonical rechecked: b8e39a2196a6d7794a04a0cd5393c68329e126ca.
Web parent remains a4e49c83f5783c19617fb609b8f95b179cb13e84 (PR #5 still unmerged).
Tested code is canonical +9 / -0 commits: six Web commits plus three current implementation/correction commits.
Final docs/evidence record adds one commit: final branch canonical +10 / -0; Web +4 / -0.
GitHub compare shows only product/UI, scoped docs, fixture/test tooling and validation workflow changes.
No Track A REAL-DATA/Frozen evidence, B personal contracts, C Frozen phases/Holdout, D/E source/Frozen catalog,
QGV/Technical/Macro/Portfolio formulas, Leaderboard calculation, PIT or provenance contract changed.
Latest remote Track C advanced independently during this session to 8ab49b0; it was read-only audited, not merged.
The 409-test result applies to this canonical + Web branch; it is not a regression claim about unmerged Track C code.

## Integration readiness and remaining dependencies
Implementation blockers: none. READY FOR REVIEW, not automatically merged or deployed.
PR #5 is a structural dependency; normal-merge/review it first, then review/merge this child PR, or review both together.
Current real producer snapshots/private hosting remain unconnected as in the Web MVP baseline.
Full 500-issuer name/Korean alias coverage depends on producer metadata; unknown translations retain canonical/ticker
fallback and stay searchable. Curated aliases cover existing common IDs; the schema accepts additional ID-keyed labels.
Investor type works only for real registration; no Investor-QGV research/profile availability is claimed.
Reports/Alerts/future modules can consume the shared AppLanguage API; no new report/alert calculation engine is added.
No D3-P calculation/Frozen-contract policy decision arose.
