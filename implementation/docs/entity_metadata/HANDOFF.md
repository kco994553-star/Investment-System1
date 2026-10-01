# Entity Metadata v1 — scoped handoff (implementation baseline)

Recorded 2026-10-01 UTC. **State: WAIT.** The defined scope is complete. PR #7 stays Open/Draft and is not merged.
Do not add alias sources, fuzzy algorithms, coverage targets or features under this baseline.
This file is scoped to Entity Metadata. The shared `Investment-System1 · CURRENT_HANDOFF.md` was intentionally not edited
so it cannot conflict with parallel tracks. The Integration agent registers this baseline there at integration time.

Machine-readable evidence: [`evidence/validation.json`](evidence/validation.json). Contract: [`CONTRACT.md`](CONTRACT.md).
Status record: [`STATUS.md`](STATUS.md).

## 1. Baseline identity
| item | value |
|---|---|
| Branch / PR | `ccr-41677301-10nj3u` / https://github.com/kco994553-star/Investment-System1/pull/7 (OPEN, DRAFT) |
| Tested code SHA | 773b264 (later commits change only docs and evidence) |
| Frozen Universe | `uni_0d1a30b1ee47`, as_of 2024-12-31, sha256 `75f795f838a608a6554e9a3fa3aa8e9e56e72fdfad4e5f8f74623aa00c7a47c9` |
| Registry | `reports/entity_metadata/top500_entity_metadata_2024-12-31.json`, sha256 `d5a338dd…596b00` |

## 2. Dependency chain (review/normal-merge in this order; never auto-merge, never rewrite history)
| order | PR | head → base | head SHA at record time |
|---|---|---|---|
| 1 | #5 Web MVP v1 | `feature/web-mvp-v1` → `claude/investment-system-top500-validation-alrugm` (b8e39a2) | a4e49c8 |
| 2 | #6 Global Language & Search | `feature/global-language-search-v1` → `feature/web-mvp-v1` | eda65bf |
| 3 | #7 Entity Metadata v1 | `ccr-41677301-10nj3u` → `feature/global-language-search-v1` | branch head |

All three were OPEN/DRAFT with mergeable_state `clean`. PR #7 needs PR #6 code (`entity_catalog.py` and `entity-search.js`).
After PR #5 and PR #6 merge, retarget PR #7 to the canonical branch and re-run `web-mvp-validation`.

## 3. Source provenance
Ingest run: https://github.com/kco994553-star/Investment-System1/actions/runs/36847160494. Raw responses are in artifact 11153956757,
which is subject to Actions retention. The committed extracts keep URL, sha256, fetched_at and HTTP status per response.

| source | join key | contributes | kept values |
|---|---|---|---|
| SEC EDGAR submissions (500/500 CIKs, 0 failures) | Universe CIK | official name, formerNames, listing tickers | 500 / 316 / 238 |
| SEC company_tickers.json | CIK | en-US alias (title) | 43 |
| Wikidata SPARQL (CC0; revision id per item) | P5531 = CIK | en/ko labels and aliases, ended NYSE/Nasdaq tickers | en 442+617, ko 233+152, hist. tickers 16 |
| KIS overseas masters NAS/NYS/AMS | SEC-issued ticker of the same CIK + English-name check | ko-KR listing name | 346 |

The egress policy of the Claude container blocks sec.gov and wikidata.org. Fetching runs only in
`.github/workflows/entity-metadata-ingest.yml` (secret `SEC_USER_AGENT`).

## 4. Coverage before / after (out of 500)
| field | before (PR #6 eda65bf) | after |
|---|---|---|
| ticker | 500 | 500 |
| canonical company name | 75 | 500 |
| common English name | 11 | 456 |
| ko-KR company name | 11 | 476 |
| aliases (en-US/ko-KR) | 11 | 497 |
| historical names | 0 | 236 |
| historical tickers | 0 | 14 |
| other SEC listing tickers (same CIK) | 0 | 82 |
| company entities / duplicates | 500 / 0 | 500 / 0 |

## 5. Rejected records (122, each recorded with source and reason in the registry `rejections`)
NO_HANGUL 54 · NON_COMMON_LISTING 51 · AMBIGUOUS_ACROSS_ENTITIES 6 · LISTING_NAME_MISMATCH 5 · AMBIGUOUS_CIK_ITEMS 2 ·
NOT_STOCK_LISTING 2 · IMPLAUSIBLE_LABEL 1 · TOO_SHORT 1.
Examples:
- Cross-issuer collisions dropped from both issuers: 시스코 (csco/plan:syy), 로우스 (low/plan:l), 파카 (pcar/ph).
- META ↔ MetLife preferred `MET-A`.
- Vandalised Wikidata alias on ndaq.
- Multiple Wikidata items for one CIK: dell, plan:hpq.

## 6. Deterministic rebuild
`python implementation/tools/ingest_entity_metadata.py build` is offline and pure. Rebuilding from the committed sources is
byte-identical in all three checks: the ingest workflow `cmp`, pytest
`test_committed_registry_rebuilds_byte_identically_from_committed_sources`, and a local recheck at 6c4648e.

## 7. Numerical invariance
`docs/entity_metadata/evidence/numeric_fingerprint.py <implementation-dir> | sha256sum` gives the same value on both heads:
- PR #6 head eda65bf: `d1b9cd913c51f65b084b2ff4596f3361834bb5419dbcf17ff19eb7f1b032a535`
- PR #7 head: `d1b9cd913c51f65b084b2ff4596f3361834bb5419dbcf17ff19eb7f1b032a535`

The fingerprint covers:
- QGV, Technical, Macro and Portfolio outputs
- Leaderboard rows and order
- `data.json` sha256 for the default and demo builds
- sha256 of all 140 committed `reports/*.json`

## 8. Full regression
PR CI: https://github.com/kco994553-star/Investment-System1/actions/runs/36848115601 (success, code 773b264, artifact 11154726084).

| check | result |
|---|---|
| pytest | 419/419 |
| PR #6 Node search/locale | 26/26 |
| Top-500 exhaustive resolution (shipped `entity-search.js`) | 3,393/3,393 labels top-1 to their own company_id |
| Web MVP browser | 10/10 |
| Global Search browser | 8/8 |

## 9. Unresolved coverage (accepted for v1; nothing guessed)
- **No ko-KR name (24):** ajg, crh, mmm, mplx, plan:avb, plan:ball, plan:cdw, plan:ctra, plan:dfs, plan:dhi, plan:eqt, plan:hpq,
  plan:l, plan:msci, plan:nvr, plan:ppl, plan:ptc, plan:syy, r1000:0000004447, r1000:0000859737, r1000:0001880661,
  r1000:0001897982, schw, tjx.
- **No en-US common label (44).** These remain searchable by ticker and SEC official name. The list is in `validation.json`.
- **Ambiguity left unresolved by design:** Wikidata items for dell and plan:hpq; the shared Korean labels listed in §5.
- **Not indexed:** CIK values, so BLK's pre-2024 CIK 0001364742 does not resolve.

## 10. Boundaries confirmed
- Search and presentation metadata only. Never an input to QGV, Technical, Macro, Portfolio, Leaderboard or Track C.
- `data.json` is unchanged.
- Fill-only precedence: PR #6 curated aliases and producer fields win as supplied.
- Unchanged: Track A–E, Frozen contracts, the PR #5/#6 search engine and ranking, and the shared CURRENT_HANDOFF.

## 11. Next actions (Integration agent only)
1. Review and normal-merge PR #5, then PR #6.
2. Retarget PR #7 to the canonical branch and confirm `web-mvp-validation` is green.
3. Re-run the fingerprint script against the new base.
4. Register this baseline in the shared CURRENT_HANDOFF.

An optional metadata refresh (edit `reports/entity_metadata/REFRESH_REQUEST`) changes data, not scope. Re-verify sections 6–8
after any refresh. Until then: WAIT.
