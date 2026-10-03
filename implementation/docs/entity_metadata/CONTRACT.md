# Entity Metadata Coverage — Top-500 search metadata contract v1

Recorded 2026-10-01. Single responsibility: entity metadata coverage for Global Search over the Frozen
Top-500 Universe (`uni_0d1a30b1ee47`, `official_snapshot_2024-12-31.json`,
sha256 `75f795f8…a47c9`, Track A FROZEN). Stacked on PR #6 (`feature/global-language-search-v1` @ eda65bf).

## Structure
canonical company entity (existing `company_id`, bound by Universe CIK)
→ ticker (Frozen Universe, unchanged)
→ official/canonical name (SEC EDGAR submissions `name`)
→ en-US common name + aliases (Wikidata `en` label/aliases; SEC company_tickers title)
→ ko-KR name + aliases (Wikidata `ko` label/aliases; KIS overseas master Korean listing name)
→ historical names (SEC `formerNames` with from/to) / historical tickers (Wikidata P414+P249 with P582 end date on NYSE/Nasdaq;
  Track A Frozen snapshots when a company_id's ticker differs — none observed)
→ other SEC-issued listing tickers of the same CIK (aliases locale `und`: language-neutral, never a display name).

## Identity rules
- Records are keyed by the existing `company_id`; the registry has exactly the 500 Universe members. No entity is created,
  merged or split. `entity_catalog` applies a record only when Universe `universe_id`, `company_id`, `cik` and `ticker` all match.
- Source joins: SEC by CIK; Wikidata by P5531 (SEC CIK); KIS only by SEC-issued tickers of that CIK **and** an English-name
  cross-check. No ticker/name similarity ever decides identity.
- More than one Wikidata item per CIK → rejected unless exactly one item carries the Universe/SEC ticker.

## Normalization and false-positive protection (deterministic, `product/entity_metadata.py`)
Normalization is the Python twin of `entity-search.js normalize()`. EDGAR state suffixes (`/DE/`) are stripped with the raw
value kept. Rejections are recorded in the registry with a reason:
`NO_HANGUL` (ko-KR value without Hangul — no transliteration/guessing), `NON_COMMON_LISTING` (preferred, depositary, notes,
units, warrants, ETNs), `LISTING_NAME_MISMATCH`, `NOT_STOCK_LISTING`, `OTHER_ENTITY_TICKER`, `OTHER_ENTITY_OFFICIAL_NAME`,
`AMBIGUOUS_ACROSS_ENTITIES` (label claimed by two issuers, e.g. 시스코 Cisco/Sysco, 로우스 Lowe's/Loews — dropped from both),
`RESERVED_NAVIGATION_LABEL` (Semiconductor/반도체/CPI…), `IMPLAUSIBLE_LABEL` (>80 chars, URL/@ — Wikidata vandalism),
`TOO_SHORT`, `AMBIGUOUS_CIK_ITEMS`.

## Precedence (fill-only)
Producer bundle fields and the PR #6 curated `COMPANY_ALIASES` win exactly as supplied. The registry only fills absent fields
or absent locales; it never appends to a curated/producer list. Canonical label: producer name → OFFICIAL_PORTFOLIO_V11
legal name → SEC official name.

## Pipeline
`tools/ingest_entity_metadata.py fetch` runs on a GitHub runner (`.github/workflows/entity-metadata-ingest.yml`; the Claude
container denies sec.gov/wikidata.org egress) and commits `reports/entity_metadata/sources/*.json` extracts with per-response
URL, sha256, fetched_at, HTTP status and Wikidata revision ids. Raw responses are kept as the workflow artifact.
`build` is offline and pure: same sources + Universe → byte-identical registry (checked in the workflow and in pytest).
Re-ingestion: edit `reports/entity_metadata/REFRESH_REQUEST` or dispatch the workflow. No issuer is hand-coded.

## Boundary
Search/presentation metadata only. Not a PIT assertion; never read by QGV, Technical, Macro, Portfolio, Leaderboard, Track C
or any engine. `data.json` (producer payload) is unchanged; only `entities.json` gains labels. Search rank stays separate
from QGV/Leaderboard rank. Track A/B/C/D/E sources, Frozen contracts and the PR #5/#6 search engine are unchanged.
