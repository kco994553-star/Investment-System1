# GIE-007 · Web G3 render guard, production-state presentation, next local trial · 2026-10-03

Workflow `wf_21372e18-41b` (5 agents, 0 errors). Raw results: `GIE-007_web_guard_ui_trial_2026-10-03.json`. A repair round (`wf_ab303e4a-a45`) is in progress; its outcome is appended below as a later section. This section stays as recorded.

## 1. PR #34 · G3 render guard (presentation layer only)

| Field | Value |
|---|---|
| Branch / head | `integration/web/research-render-guard-v1` @ `2b53b27` |
| Base | #9 `feature/producer-infrastructure-v1` @ `f8af596`. Chosen so that the integration-ready #5 → #6 chain and its exact-SHA trial evidence stay untouched |
| Change | `app.js` render-time fail-closed guard plus one `locale.js` string. LIVE/FROZEN_SNAPSHOT sections carrying a research marker are shown in the existing NOT_AVAILABLE presentation with a ko/en reason, and their values never reach the page. The served `data.json` is not rewritten |
| Mirror | `producers/contract.py` @ `f8af596`: SECTION_NAMES L23, PUBLISHED_STATES L26, RESEARCH_STATUSES L28-30, rule L197-202, at the assembler path `<section>.producer.methodology.status`. In addition (a reviewer decision point, withhold-only), `research_state.status` is checked against the same set |
| Not changed | `product/web_mvp.py` (byte-pinned by #17), `producers/*`, schema-1 states, grants, DISPLAY_RESEARCH, Track C paths |
| Tests | Full pytest 435 (#9 tip 431 + 4). Existing browser tests pass. New browser regression passes; with the pre-guard `app.js` the same bundle leaks the probe values (negative control) |
| Actions | web-research-guard run 37109567406 ✓, web-mvp-validation run 37109567361 ✓ (head `2b53b27`) |
| Forward merge | `git merge-tree`: 0 conflicts into #17, #19, #29, #30. On a #30 tree with the guard merged, `test_p01_research_publication.py` passes |
| Adversarial review | **PASS**, 8 non-blocking findings. Of those, **N4** (the guard does not copy the contract's validation-PASS half of the same rule) is taken into the repair round. N1 (case variants also pass the contract) is consistent mirroring and is not hardened beyond the contract |

## 2. PR #36 · production-shaped state presentation (stacked on #34)

| Field | Value |
|---|---|
| Branch / head | `integration/web/production-state-presentation-v1` @ `e91dc77` |
| Change | presentation only, in `app.js`, `locale.js`, `style.css`, `index.html`, `network-bridge.js`: freshness as its own badge (FRESH/STALE/NOT_USABLE); withheld-section metadata shown from persisted fields only; ko/en strings; render-error fallback after hashchange |
| Tests / Actions | pytest 441; new browser test 19/19; 3 Actions runs on `e91dc77` ✓ |
| Adversarial review | **BLOCKING**: `freshnessOf()` trusted a persisted `FRESH` when JS could not parse `expires_at`. ISO forms such as `20260103T000000Z` are valid for Python `fromisoformat` but NaN for `Date.parse`, so expired LIVE data showed "FRESH · 만료 전" ("before expiry"). Reproduced through the real assembler and the unchanged validator. In repair (fail closed) |

## 3. Local next combined trial (never pushed)

`86ad362` (#30) + #32 + #33 + #34 `2b53b27` + #36 `e91dc77`, all clean `--no-ff` merges. Results:

- full pytest **1175 passed**, 0 failed (#30's 1165 + 10 new Web tests);
- every browser step from `codex-integration-readiness`, `web-mvp-validation`, `web-research-guard` and `web-state-presentation` passes;
- fingerprints equal the post-adoption values (technical `66cb2383`, macro `7e427949`, qgv/leaderboard/portfolio unchanged);
- the merges change 17 files: no Track C path, and `web_mvp.py` is byte-unchanged;
- a read-only `git merge-tree` against Codex #31 `675d0d2` is clean, with 0 file overlap (CDR-009: recorded, nothing resolved).

Verdict READY_FOR_NEXT_TRIAL_PR, **superseded** because it includes #36's defective head. It will be re-run on the repaired heads.

## 4. Validator hardening: separate follow-up, not done

Making `product/web_mvp.validate_bundle` enforce the contract's research and validation rule changes bytes covered by #17's protected digest (`test_protected_engine_bytes_are_unchanged`) and `tests/test_web_mvp.py` L75. Per the user instruction of 2026-10-03 this is not re-pinned autonomously. If it is pursued, it goes to the user as USER_DECISION_REQUIRED.

## 5. Addendum · repair round 1 (`wf_ab303e4a-a45`, 4 agents, 0 errors; raw: `GIE-007a_repair1_2026-10-03.json`)

| Item | Result |
|---|---|
| #34 → `a3cbf13` | Adds the contract's validation-PASS half (`producers/contract.py` L194-199; LIVE/FROZEN needs `<section>.producer.validation.status == "PASS"`; missing validation is rejected, as the contract's REQUIRED fields do). Sections without a `producer` key (legacy/demo) are unchanged: render is byte-identical against `f8af596` and `2b53b27` on the default and demo builds. pytest 446. Actions 37114503889 ✓, 37114503882 ✓. **Re-review PASS** |
| #36 → `8b6756b` | Merged #34 forward (normal merge `4ccdd3a`). An unparsable `expires_at` now fails closed to STALE. Displayed `reason_code` and methodology fields are restricted to code/token shapes. pytest 455. Actions 37115011166 / 37115011158 / 37115011179 ✓. **Re-review BLOCKING (B1)**: Python `fromisoformat` accepts `(` and U+0000 as separators that V8 misparses to a *later* instant, so expired data can read FRESH for up to about 36 h. Repair round 2 (`wf_d3aa55d6-117`) is in progress: pass only strict RFC 3339 strings to `Date.parse`, otherwise STALE |
| trial2 (local, never pushed) | `86ad362` + #32 + #33 + #34 `a3cbf13` + #36 `8b6756b` → `805b3c6`. **1189 passed**, 0 failed (1165 + 15 + 9). All browser steps pass. Fingerprints equal post-adoption. No Track C path touched; `web_mvp.py` blob `10ad8c76` unchanged; tests only added; merge-tree vs Codex #31 clean. Verdict READY_FOR_NEXT_TRIAL_PR. **Superseded** pending #36 repair round 2 |

## 6. Addendum · repair round 2 (`wf_d3aa55d6-117`, 3 agents, 0 errors; raw: `GIE-007b_repair2_2026-10-03.json`)

| Item | Result |
|---|---|
| #36 → `fb086ea` | Fast-forward from `8b6756b`; base still #34 @ `a3cbf13`. `freshnessOf()` passes `expires_at` to `Date.parse` only when it matches strict RFC 3339 (`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{1,9})?)?(Z|[+-]\d{2}:\d{2})$`). Any other string is STALE. No TTL, threshold or schema-1 state added. Count keys are displayed only when they match `^[A-Za-z][A-Za-z0-9_]{0,63}$` (N4). Tests only added. pytest 459. Actions 37117898008 / 37117898016 / 37117898071 ✓ |
| B1 closure, writer evidence | Node fuzz with the page logic extracted verbatim, in UTC, Etc/GMT+12, Pacific/Kiritimati and Asia/Seoul. Reviewer form set (175,827): 0 FRESH-after-expiry in every zone, against 64/188/14/33 on `8b6756b`. Every-code-point separator set (5,560,315 Python-accepted forms): 0 in every zone, against 2/4/2/2. 663,665 valid `isoformat()` forms read the same instant to the millisecond |
| **Re-review** | **PASS, B1 closed, no blocking finding.** The original exploit bundles were replayed on the `fb086ea` build: 108/108 renders STALE across 9 clocks and 4 zones, where `8b6756b` showed FRESH. Non-blocking notes: N1 a zero-width space inside a displayed token is not filtered (cosmetic); N2/N3/N5 fail closed early (offset minutes ≥60, sub-millisecond truncation, sub-minute offsets); N4 hand-edited impossible dates that `validate_bundle` rejects can still parse in JS. Local Playwright 1.56.1 vs CI 1.58.2; CI is green |
| trial3 (local, never pushed) | `86ad362` + #32 `e9aee0c` + #33 `9626ab0` + #34 `a3cbf13` + #36 `fb086ea` → `eb575c9`, all `--no-ff`, 0 conflicts. **1193 passed**, 0 failed (1165 + 15 + 13). All browser steps from the four Web workflows pass. Fingerprints equal post-adoption (technical `66cb2383`, macro `7e427949`; qgv, leaderboard, portfolio unchanged). No Track C or CDR-009 path; `implementation/src` changes only under `product/web_assets`; `web_mvp.py` blob `10ad8c76` unchanged; tests only added. `git merge-tree` against Codex #31 `29c2c20` and `codex/integration-hardening-2026-10-03` `722c812`: clean, 0 file overlap. Verdict **READY_FOR_NEXT_TRIAL_PR**. Supersedes trial2 `805b3c6` |

States after round 2: BRANCH_STATE #34 `a3cbf13`, #36 `fb086ea` pushed. INTEGRATION_STATE LOCAL_TRIAL_VERIFIED (trial3); trial-PR Actions are recorded in GIE-008. CANONICAL_STATE NOT_MERGED. Maturity: Web guard and state presentation stay SYNTHETIC_VERIFIED.
