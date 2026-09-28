# Personal Web MVP — operation and producer integration

This is a read-only presentation application. It does not run scoring/Universe,
Track C validation, RIG inference, broker actions or LLM APIs.

## Build / preview
From `implementation/`:

```sh
PYTHONPATH=src python -m investment_system.product.web_mvp --out /tmp/web-mvp
python -m http.server 8765 --bind 127.0.0.1 --directory /tmp/web-mvp
```

Open `http://127.0.0.1:8765/`. HTTP is required (data.json fetch); file:// is unsupported.
For explicitly synthetic UI validation, add `--demo` and use a separate output directory.
Both modes reuse the exact frozen Prompt Library catalog and upstream validation/UI.
Default contains the hash-verified 2024-12-31 Universe only. It is not today's market.
Other dates/operating snapshots are supplied through the producer bundle; Web does not choose or reconstruct them.

No hosting, public access, login or paid service is configured. A secure hosting/access choice
remains necessary for everyday phone access outside the build environment. Never publish actual
holdings/context exports to a public repository or unprotected static host.

## Read-only bundle
`--input /private/path/bundle.json` accepts schema_version 1. Start with generated data.json;
replace only producer-owned envelopes. Web validates metadata and IDs, not financial correctness.

Top-level: schema_version, companies, universe, qgv, technical, macro, portfolio,
leaderboard, news, relationships, changes.

Each envelope:
- state: LIVE / FROZEN_SNAPSHOT / DEMO / NOT_AVAILABLE
- as_of: upstream timestamp/date (NOT invented by Web)
- source: producer reference
- data: original fields, or null when NOT_AVAILABLE
- reason: useful missing-data explanation
- LIVE additionally needs offset-aware expires_at. Expired LIVE is prominently STALE.

| Section | data shape consumed |
|---|---|
| companies | list of company_id, ticker, name; optional market_cap_rank, rank_is_lower_bound, issuer_id |
| qgv | company_id → canonical QGVSnapshot dict; Q/G/V/total/Confidence preserved |
| technical | company_id → canonical TechnicalSnapshot dict; no guessed available_at |
| macro | canonical MacroSnapshot; optional producer exposures mapping |
| portfolio | holdings array with company_id/ticker and supplied weights; role; optional return, market_value, currency, exposure |
| leaderboard | rows array in upstream order with original rank, company_id, ticker, Q/G/V/total_score; optional market_cap_rank/daily_move/consensus/scenario/reevaluation_trigger |
| news | NewsCard-like list with event_id/headline/issuer_ids/available_at/status and source fields |
| relationships | non-null signals availability; --rig-page must supply a trusted Track D rendered HTML page |
| changes | producer summary; no frontend difference/score calculation |

Existing contracts do not provide every requested field. Absent daily move/consensus/scenario,
returns/exposure, company-level Macro exposure and price/FX context stay '미제공'.
Financial units/scales and any extra provenance are retained in Evidence. Market-cap rank is
never silently used as QGV rank. Unknown identities are rejected; mapping is never inferred from tickers.

## News/Network operator boundary
Operator ChatGPT analysis → reviewed structured input → Track D ingestion/gates → rendered page +
NewsCard export → bundle → static build. The Web command accepts only the final read-only outputs.
`--rig-page` is trusted local build input, not an end-user HTML upload endpoint. It contains scripts,
so use only a page produced by the reviewed Track D renderer. Personal storage is same-origin.
6/12-hour cadence belongs to an external operator/build schedule; no scheduler or LLM collector added.

## Personal preferences
One interest list and simple groups live at localStorage key investment.web.v1.personal.
No account sync. Export a JSON backup before clearing browser storage/changing origin. Imports merge,
not replace, existing preferences. Group deletion does not delete interests or upstream data.
These are organization preferences, not Official investment logic or Track B Actual Portfolio.

## Tests
```sh
python -m pytest -q tests/test_web_mvp.py
python -m pytest -q
```
`.github/workflows/web-mvp-validation.yml` runs regression, default and DEMO builds, and mobile
browser checks at 360/390px plus desktop 1280px. Browser evidence is retained as Actions artifact
`web-mvp-validation`; source fixtures remain explicitly synthetic.

## Limitations / release gate
Read-only screens can show NOT_AVAILABLE correctly while operating-data readiness remains incomplete.
No claim of today's investment feed, actual portfolio, Track C promotion, production V score,
common three-language framework, cross-device storage or deployed phone URL.
M8/FREEZE_READY requires the phase acceptance evidence, including mobile browser tests; code creation
alone is not acceptance. Daily-use readiness also requires the producer and hosting integrations in CONTRACT.md.
