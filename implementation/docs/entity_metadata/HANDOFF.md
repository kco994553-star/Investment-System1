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

## 12. Additive note 2026-10-03: C-28 adoption evidence record (user CDR-004)

This section is appended. Nothing above it is rewritten, and the §7 values stay as recorded. The Primary Integration Writer prepared it under user CDR-004 (2026-10-03). It becomes the owner's record when the owner or the user merges it into `ccr-41677301-10nj3u`.

| Item | Value |
|---|---|
| Record | [`evidence/c28_adoption_post_adoption_2026-10-03.json`](evidence/c28_adoption_post_adoption_2026-10-03.json) |
| Authority | User CDR-004 (2026-10-03): IF-1 = A1 + Technical/Macro owner adoption of the Track C additive lineage/schema change. Existing numerical/semantic invariance is re-verified on the new schema before any fingerprint is re-recorded. This is not an approval to change any Technical/Macro formula, value, regime, zone, Macro state, QGV or ranking. It is not canonical-merge approval |
| Pin check | No test on this branch (`a013f1c`) pins `d1b9cd91…`. It appears only in §7 and `evidence/validation.json`. Evidence-only adoption, so no test repin |
| Gate | BEFORE `a013f1c` vs AFTER `a013f1c` + Track C owner tip `b9e01a97` (`--no-ff`, 0 conflicts, throwaway `d1dd81ce`, never pushed). Generator: `docs/entity_metadata/evidence/numeric_fingerprint.py`, unchanged. The engine outputs (QGV, Technical, Macro, Portfolio, Leaderboard rows and order) differ only by the four keys `available_at=null`, `data_stamp_refs=[]`, `source_vintages=[]`, `input_hash=null` on 10 technical snapshots and 1 macro snapshot (44 ADDED entries; nothing removed or changed). **PASS** |
| Values | BEFORE reproduces `d1b9cd913c51f65b084b2ff4596f3361834bb5419dbcf17ff19eb7f1b032a535`. AFTER whole-stdout sha256 is `9b9a276e…`. That value also reflects 27 extra `reports/*.json` entries: the script hashes every report present in the tree, and the throwaway merge adds 27 Track C report files (all status `A`). Removing those 27 entries and the four keys reproduces `d1b9cd91…` byte for byte. Without the 27 entries, the post-adoption value is `ce845bb6…` |
| Other committed hashes reproduced unchanged (both trees) | `data.json` sha256 for the default build (`8206d6c5…`) and the demo build (`649a144d…`). All 140 committed `reports/*.json` sha256. The six entity-metadata artifact sha256. The Frozen Universe `75f795f8…`. The deterministic registry rebuild is byte-identical |
| Tests | Owner tip `a013f1c`: pytest 419 passed, mini_pytest shim 419 passed / 0 failed. This proposal: same counts. Merged throwaway tree: pytest 949 passed, 0 failed |
| Not changed | `evidence/validation.json`, `evidence/numeric_fingerprint.py`, the text above, and every file under `src/`, `tests/`, `tools/`. Track C is not merged into this branch |
| GitHub Actions | NOT_RUN for this proposal (docs-only; no matching workflow path filter) |
| BRANCH_STATE / INTEGRATION_STATE / CANONICAL_STATE | proposal branch `integration/a1-adoption/pr7-entity-metadata` from `a013f1c` / NOT_MERGED into the owner branch / NOT_MERGED |
