# INVESTMENT_SYSTEM_WEB_MVP_V1

M0 audit / contract — 2026-09-28 KST
Baseline: b8e39a2196a6d7794a04a0cd5393c68329e126ca
Branch: feature/web-mvp-v1. Owner: presentation/navigation/read-only aggregation/personal cockpit.

## Audit
Canonical fetched from GitHub, including complete ancestry. No AGENTS.md in this repository.
Read CURRENT_HANDOFF, Project Index, Master Status, Evidence/Conflict Registers, Architecture,
Frontend IA, product contracts/render_app, QGV models/leaderboard, Technical/Macro contracts,
Personal P0, RIG P0–P4 render/prefs/views/discovery, Prompt Library catalog/fill/UI and tests/workflow.
Historical handoff paragraphs are stale: latest Track A integration overlay supersedes them.
A: FROZEN_VERIFIED, PR3 normal merge; B: P0 only; C: remote 27bd69d C0 (not canonical).
D: P0–P4 code/tests present; P5 dependency remains. E: Frozen 70-prompt validated catalog/UI present.
Remote C0 workflow 36415853662 succeeded; no fresh canonical workflow success inferred.

Existing UI: product/render_app.py generates 17 mostly placeholder pages; no web application runtime.
Reuse static generation pattern, canonical snapshot models, rig.network.render and prompt_library.ui.
Do not change frozen modules or rebuild their interactions/content. New cockpit is an additive product entrypoint.

## Data and ownership contract
- Web never calls scoring, Universe construction, validation, relationship inference, or prompt generation engines.
- Default data: exact hash-verified Track A frozen Universe 2024-12-31. It is NOT current investment data.
- QGV/Technical/Macro/actual Portfolio/Leaderboard/current News missing => NOT_AVAILABLE, never zero.
- Explicit --demo: existing synthetic artifacts and Track D test fixtures only, persistently marked DEMO.
- LIVE requires explicit producer metadata and expiry; expired data is displayed STALE, never silently current.
- Preserve as_of, source, snapshot id, quality, policy and original values. No cross-scale arithmetic.
- Market-cap rank and QGV leaderboard rank are different. Do not derive leaderboard from Universe order.
- Local interests/groups are explicit user organization only; no allocation, broker, scoring, or Official logic.
- No new AI API, auth, payments, cloud scheduler or service. No public deployment of personal data.

## Architecture / boundaries (D2 decisions)
W-D01: Static Python build + native JS/CSS, same repository convention; no framework dependency.
W-D02: Six mobile-first routes; native hash navigation, progressive details; existing legacy shell retained.
W-D03: Lazy same-origin frames for D/E UI composition; product-owned style/interaction enhancements only.
W-D04: Browser localStorage versioned personal preferences with export/import; not cross-device sync.
W-D05: Canonical company_id used for cockpit; explicit issuer mapping required for production RIG linkage.
W-D06: Small read-only JSON bundle ingestion (--input); producer must supply metadata. 6/12h updates are
external operator builds, not a web-owned collection/LLM pipeline. No upload endpoint in static app.
W-D07: Korean/bilingual presentation now; label dictionary boundary; Frozen prompt bodies unchanged.
W-D08: Shared historical SSoT files are not rewritten; this scoped contract/status are integration inputs.
All choices reversible. No D3-P. No Track C merge. No new Official investment logic.

## Acceptance / phase gates
| Phase | Acceptance |
|---|---|
| M0 | Audit sources pinned; ownership/data contract; conflict/dependency list; baseline regression |
| M1 | Six routes, back/deep links, 360px layout, touch-sized controls, keyboard navigation |
| M2 | Home summaries and attention; source/as-of/state; no missing-to-zero; read-only adapter tests |
| M3 | Company search/detail, Portfolio holdings/context, upstream Leaderboard with missing columns explicit |
| M4 | Reused News/Network, zoom/pan/drag/focus/expansion/filter, same-page detail, Fact/Impact separation |
| M5 | Reused 70 Frozen prompts, search/filter/starter/bundle, validated variable fill/preview/copy |
| M6 | One interests list; groups create/rename/delete/membership; reload and storage failure handling |
| M7 | Mobile flow E2E on 360/390px plus desktop; no overflow/errors; actual missing-data and DEMO paths |
| M8 | Full regression, unchanged upstream files/content, docs/build reproducibility and integration report |

## INTEGRATION_REQUIRED
1. Integration owner merges feature branch normally; register scoped status in shared indices.
2. Producers export current snapshots with stable IDs, explicit lineage/availability and data-state metadata.
3. Track B P1+ actual holdings/return/exposure; no web synthesis. Technical available_at remains upstream.
4. Track D operating feed and explicit company_id↔issuer_id mapping; operator-reviewed structured news enters D first.
5. Hosting/access choice before private daily use on phone; no public hosting/security changes in this branch.
6. Full common language layer when available; not required to render current bilingual MVP.

Freeze means implementation acceptance only, never LIVE-data readiness or investment-model promotion.

## Validation decisions / corrections
W-D09 (D2): Keep RIG fixture projection in tools/build_web_mvp_demo.py, outside all runtime packages.
The initial full regression correctly rejected a product→RIG import. Existing owner-boundary tests are
unchanged; product now accepts only finished RIG page/data. Targeted boundary suite: 23 PASS.
W-D10 (D2): GitHub connector commits publish the feature branch because shell git has no write credential.
Original local checkpoints are retained on feature/web-mvp-v1-local-checkpoint; no force/history rewrite.
W-D11 (D2): Use existing public-repository GitHub Actions validation for browser tests; cloud Browser cannot
reach localhost and local Chromium download failed. No hosting or personal data upload is performed.
