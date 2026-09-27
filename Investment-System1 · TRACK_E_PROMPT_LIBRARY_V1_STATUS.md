Investment-System1 · Track E — Prompt Library v1 · Implementation Status

Timestamp: 2026-09-27 (KST) · Branch: `feature/track-e-prompt-library-v1` (branched from `claude/investment-system-top500-validation-alrugm` @ 11b3dc4; Track A has since advanced — not merged, by rule)
Status: **E0-E8 IMPLEMENTED on the Track E feature branch — FREEZE READINESS CANDIDATE (not merged)**
Content baseline: `PLV1_CONTENT_V1.0` · CONTENT FROZEN 2026-09-27 12:36:40 KST · 70 Active · sha256 `f0a6ed90…c283e68e`

## Scope and boundaries

- Track E only. No Track A (universe / ingestion / Promotion Gate / corporate action / Official snapshot / walk-forward /
  c21 workflow / evidence), Track B (PIL P0), Track C, Track D (RIG/News; C-39) file is touched; no shared SSoT
  (CURRENT_HANDOFF, Project Index, Conflict/Evidence Register, CHANGELOG, contracts, App Shell) is edited — see
  INTEGRATION_REQUIRED.
- The runtime never calls an LLM, a network service, or the QGV / Technical / Macro engines (enforced by an import test).
  Copy-first: the user copies a vendor-neutral plain-text prompt into any AI.
- Frozen content is immutable: the three Frozen files are stored byte-identical; the loader verifies the pinned SHA-256
  and refuses altered or missing content. No prompt body, merge/retire decision, Starter or Bundle was changed.

## Files (all new)

| path | purpose |
|---|---|
| `implementation/src/investment_system/prompt_library/content/Investment_Prompt_Library_v1_Content_Catalog_FROZEN.md` | Frozen catalog, verbatim (sha256 f0a6ed90…) |
| `…/content/Investment_Prompt_Library_v1_Decision_History.md` | merge / retire migration, verbatim (sha256 a8e764c2…) |
| `…/content/Investment_Prompt_Library_v1_Content_Regression_Report.md` | content regression 33/33, verbatim |
| `…/prompt_library/catalog.py` | E0 loader (pinned hash, deterministic, cached) + E1 schema, `resolve()` for ID / code / legacy code / merged alias / retired |
| `…/prompt_library/validation.py` | E2 fail-closed integrity checks, run at every load |
| `…/prompt_library/search.py` | E3 filters (domain, role, category, subcategory, scope, Starter, Bundle, input_mode, tags, keyword) + facets |
| `…/prompt_library/fill.py` | E4 variable fill, E5 preview, E6 copy text + Bundle / multi-prompt export (text / json) |
| `…/prompt_library/ui.py` | E7 standalone page renderer |
| `implementation/reports/prompt_library/prompt_library.html` | generated page (self-contained, offline; `#<prompt_id>` deep link) |
| `implementation/tools/prompt_library.py` | CLI: search / show / fill / bundle / render-html (exit 2 = fail-closed) |
| `implementation/tests/test_prompt_library_v1.py` | 21 tests (pytest and mini_pytest shim) |

## Schema `plv1.runtime.schema.v1`

Only fields present in the Frozen catalog, plus read-only derived views:
- PromptRecord: `prompt_id` (stable), `prompt_code` (versioned), `content_version`, `title`, `purpose`, `status`,
  `domain`, `role`, `category`, `subcategory`, `tags`, `keywords`, `aliases`, `variables`, `system_overlap`, `body`.
  Derived: `legacy_code`, `requires_input_mode` (TECH/MACRO), `scopes` (COMPANY / INDUSTRY / THEME / UNIVERSE / MARKET,
  from declared subject variables), `system_input_variables` (variables that carry an existing system result).
- MigrationRecord: `prompt_id`, `legacy_code`, `status` (MERGED_INTO | RETIRED_SYSTEM_OVERLAP), `target_prompt_id`,
  `note`, `replacement_path`. Merged IDs/codes resolve to their Active target; retired ones raise with the replacement path.
- Bundle: `number`, `name`, `prompt_ids` — IDs only, never a body copy.
- Input mode is a prompt VARIABLE (`{{input_mode}}`, 27 TECH/MACRO prompts), exactly as in the Frozen content — not a
  new metadata field. SYSTEM_CONTEXT consumes existing snapshots; STANDALONE requires PIT data and ends
  `INSUFFICIENT_DATA` without it (both enforced by the Frozen body text; validation checks the text is present).

## Phase status

| phase | status | evidence |
|---|---|---|
| E0 Frozen Catalog Loader / Contract | DONE | pinned SHA; altered → FROZEN_CONTENT_HASH_MISMATCH; missing → CATALOG_NOT_PRESENT; deterministic rebuild equal |
| E1 Data Schema | DONE | 70 Active; IDs == Decision History continuity list; 38 merged (22 groups) + 6 retired; 70+44 = 114 |
| E2 Validation | DONE | as_of declared+used 70/70; body vars == declared 70/70; input_mode only TECH/MACRO 27/27; body contract lines; Discovery boundary |
| E3 Search / Filter | DONE | domain/role/scope/Starter/Bundle(order kept)/input_mode/keyword; unknown filter value → error |
| E4 Variable Fill | DONE | required/optional; ISO dates; as_of not future; prior_cutoff < as_of; enum; positive int; no braces; unknown names rejected |
| E5 Preview | DONE | partial preview keeps `{{var}}` for unfilled/invalid values; ready_to_copy only when all checks pass |
| E6 Copy / Export | DONE | copy = filled canonical body only; Bundle export text/json with catalog sha + as_of |
| E7 Minimal UI | DONE (standalone) | select → description → variables → preview → copy; Starter ★ and Bundle filter; headless-Chromium render checked |
| E8 Regression / docs / Freeze readiness | DONE | 322/322 pytest and mini_pytest shim (301 baseline + 21 Track E) |

## Decision Log

| id | authority | decision | alternatives | rationale / impact | rollback |
|---|---|---|---|---|---|
| E-D1 | D1 | Store the three Frozen files verbatim inside the package; parse the Markdown at load time (no second JSON copy) | convert to JSON/YAML | one source of truth, SHA-verifiable, cannot drift | delete `content/` + loader |
| E-D2 | D1 | Pin Decision History sha256 as received (a8e764c2…); catalog sha as recorded in the Frozen docs | not pinning history | migration table is part of identity; alteration fails closed | update pin with a new approved history |
| E-D3 | D2 | Every declared variable is required; only `qgv_snapshot_summary` is optional (the Frozen body says "요약이 비어 있어도…"); blank → `NOT_PROVIDED` | all optional; all context variables optional | only choice grounded in Frozen text; fail-closed otherwise | edit `OPTIONAL_VARIABLES` |
| E-D4 | D2 | Value kinds from variable names: `as_of`/`prior_cutoff` ISO date (date-only = 00:00 KST) or offset-aware datetime (naive rejected); `as_of` ≤ now; `prior_cutoff` < `as_of`; `input_mode` ∈ {SYSTEM_CONTEXT, STANDALONE}; `candidate_count` positive int; values may not contain `{{`/`}}`; unknown names rejected | free text everywhere | mechanical PIT consequences of "as_of is the information cutoff"; no PIT relaxation | relax per kind in `fill.py` |
| E-D5 | D2 | `scopes` and `system_input_variables` are derived views, not content fields | new metadata fields | Frozen content unchanged; filters still possible | drop the properties |
| E-D6 | D2 | UI = standalone static page (no App Shell edit); linking into navigation is INTEGRATION_REQUIRED | edit `contracts.product` / `render_app` | shared frontend files may be changed by other agents | add nav entry at merge |
| E-D7 | D1 | Tests use a plain helper instead of a pytest fixture | fixture | the c21 workflow's offline baseline runs the mini_pytest shim (no fixtures) | — |
| E-D8 | D2 | Generated page is committed; a test fails if it is not identical to `render_html()` | generate on demand only | reviewable artifact, no drift | delete file + assertion |

No D3-P decision was needed. No Frozen content conflict found (catalog status line "CONTENT ONLY / NO SCHEMA-UI-RUNTIME"
describes the content artifact itself; the runtime lives outside it and changes nothing in it).

## Known limitations

- Language: Frozen prompt text is Korean (unchanged); UI chrome uses "English (한국어)" labels only. No language
  presentation layer is built here (integration boundary below).
- `existing_system_candidates`, `system_summary` and other context variables are required; a user without system
  results must type e.g. `none` (strict by design, E-D3).
- Clipboard: on `file://` (not a secure context) the page falls back to `document.execCommand('copy')`.
- Browser-rule parity test runs only where `node` is installed; the Python rules are the contract.
- Bundle export uses one shared value set for all member prompts.
- SYSTEM_CONTEXT inputs are pasted by the user; no automatic read of TechnicalSnapshot / MacroSnapshot / QGV results.

## INTEGRATION_REQUIRED (at merge time, by the integrating agent)

1. App Shell navigation: add a Prompt Library page (`contracts/product.py` NAV_PAGES / `product/render_app.py`) linking to
   or embedding `reports/prompt_library/prompt_library.html`.
2. SSoT registration: Project Index, CURRENT_HANDOFF, Artifact Evidence Register — Track E runtime + location of the
   Frozen content (`implementation/src/investment_system/prompt_library/content/`) and its hashes.
3. `implementation/CHANGELOG.md` entry for Track E.
4. Language Presentation Layer (English / English (한국어) / 한국어): when a common layer exists, route UI labels through it;
   Frozen prompt bodies stay as frozen.
5. Optional read-only wiring of SYSTEM_CONTEXT inputs from existing snapshots (no recomputation) — separate decision.

## Verification commands

```
cd implementation
python -m pytest -q tests/test_prompt_library_v1.py      # or: python tools/mini_pytest.py tests/test_prompt_library_v1.py
python tools/prompt_library.py search --starter
python tools/prompt_library.py show TECH-002             # merged -> TECH-001.v1.0
python tools/prompt_library.py render-html               # regenerate the page
```
