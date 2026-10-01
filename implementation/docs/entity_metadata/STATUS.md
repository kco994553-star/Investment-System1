# Entity Metadata Coverage — status

Recorded 2026-10-01 UTC. Status: IMPLEMENTED / REGRESSION PASS / READY FOR REVIEW (draft PR #7, not merged).
Branch `ccr-41677301-10nj3u`, stacked on PR #6 `feature/global-language-search-v1` @ eda65bf (PR #6 on PR #5).
Tested code HEAD: 773b264. This record changes docs only.

## Coverage — Frozen Top-500 (`uni_0d1a30b1ee47`), counts out of 500
| field | before (PR #6 @ eda65bf) | after |
|---|---|---|
| ticker | 500 | 500 |
| canonical company name (≠ ticker) | 75 | 500 |
| common English name | 11 | 456 |
| ko-KR company name (Hangul) | 11 | 476 |
| aliases (en-US/ko-KR) | 11 | 497 |
| historical names | 0 | 236 |
| historical tickers | 0 | 14 |
| other SEC listing tickers (same CIK) | 0 | 82 |
| registry provenance attached | 0 | 500 |
| company entities / duplicates | 500 / 0 | 500 / 0 |

Not covered (no reliable source value, so nothing invented): 24 have no ko-KR name, 44 have no Wikidata English common name
(the SEC official name is still searchable), and CIKs are not search keys (for example, BLK's pre-2024 CIK is not indexed).

## Sources (per-value provenance in `reports/entity_metadata/top500_entity_metadata_2024-12-31.json`)
Ingest run https://github.com/kco994553-star/Investment-System1/actions/runs/36847160494 (raw artifact 11153956757).
- SEC EDGAR submissions (500/500 CIKs, 0 failures): 500 official names, 316 historical names, 238 listing tickers.
- SEC company_tickers.json (sha256 a1d4b030a746…): 43 en-US aliases.
- Wikidata via P5531 (CC0; 455 items across 450 CIKs; revision ids recorded): 442 en-US / 233 ko-KR common names,
  617 en-US / 152 ko-KR aliases, 16 historical tickers (NYSE/Nasdaq with end date).
- KIS overseas masters NAS/NYS/AMS (sha256 recorded): 346 ko-KR listing names (SEC ticker join + English-name check).
- 122 rejected values: NO_HANGUL 54, NON_COMMON_LISTING 51, AMBIGUOUS_ACROSS_ENTITIES 6, LISTING_NAME_MISMATCH 5,
  AMBIGUOUS_CIK_ITEMS 2, NOT_STOCK_LISTING 2, IMPLAUSIBLE_LABEL 1, TOO_SHORT 1.

## Verification
PR CI https://github.com/kco994553-star/Investment-System1/actions/runs/36848115601: success.
| check | result |
|---|---|
| Full pytest (existing 409 + 10 new) | 419/419 PASS (CI and local) |
| PR #6 Node search/locale regression | 26/26 PASS |
| Top-500 exhaustive resolution (shipped entity-search.js) | 3,393/3,393 labels top-1 resolve to their own company_id |
| Web MVP browser E2E / Global Search browser | 10/10, 8/8 PASS |
| Registry rebuild from committed sources | byte-identical (workflow cmp + pytest) |
| QGV/Technical/Macro/Portfolio outputs, Leaderboard order, data.json, committed reports/*.json | identical before/after |

The 3,393 resolved labels break down as: ticker 500, canonical 500, en-US 1,101, ko-KR 722, listing ticker 238,
historical name 316, historical ticker 16.

Regression cases covered: ticker, English name, Korean name, alias, historical name/ticker (FACEBOOK→meta, FB→meta, FI→plan:fisv,
MHFI→spgi). Also covered: no duplicate entities, the CIK/universe binding, fill-only precedence and false-positive guards (MS stays
Morgan Stanley; reserved navigation labels; cross-issuer collisions; Latin-script values in ko-KR; vandalised labels).

## Cross-track impact
None on calculations. Changes are limited to product/entity_catalog.py (fill-only hook), the new product/entity_metadata.py,
search metadata reports, tests/tools, one added step and path filter in web-mvp-validation.yml, and the new ingest workflow.
Track A–E sources, Frozen artifacts, the PR #5/#6 search engine and ranking, and data.json are unchanged.

## Integration readiness
Ready for review once PR #5 and PR #6 are reviewed and merged, in that order. Nothing has been merged automatically.
Refresh: edit `reports/entity_metadata/REFRESH_REQUEST` or dispatch `entity-metadata-ingest`. Wikidata is
community-maintained; the guards and the per-item revision ids make every value auditable.
