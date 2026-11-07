# Common classification implementation plan

**Goal:** reuse one dated company classification in QGV, technical groups and macro references.
**Architecture:** `common-classification/1` is a research-owned evidence envelope. Existing ten sector IDs, SIC rules, seven industry definitions, ETF reference rules and calculation kernels remain authoritative in their original scopes. Thin projections feed old contracts without replacing official calculations.
**Spec:** owner common dictionary / point-in-time mapping / three-analysis instruction, 2026-11-07.
**Execution:** implement within the already approved scope; no repeated design or ownership approval.

## Boundaries

- Base composes unchanged #514 and #515 dependencies locally; existing PR heads/canonical remain unchanged.
- Main owns frontend, workflow, guards, CI lists and decision records. New shared contract is proposed in #437 comment 6706590129.
- Classification validity is half-open; security-link validity is inclusive. Evaluation-only evidence has no inferred start date.
- Company code, issuer ID, security ID and source series ID stay distinct. No ticker/CIK security substitution.
- Sector, industry and accounting statuses are independent. Unknown rows remain in the original denominator.
- Current review using retained evidence is distinct from historical system availability. Import time is never first publication or original review time.
- QGV strict20, official Q gate/minimum/fallback, and technical decile10 stay unchanged. ETF reference is not an own-sector return.

## Tasks and verification

1. `research/common_classification/{catalog,records}.py`: reuse sector IDs and SIC subgroup definitions; explicit versioned parent map; validate source, revision, applicability and component evidence; deterministic resolution. Tests cover bad parents, duplicate identities, date-only availability, future changes, corrections, sector-only and unresolved exceptions.
2. `research/common_classification/{qgv,technical_macro}.py`: original-member QGV snapshot, technical group/identity linkage, macro source-system and ETF references. Reuse preview_qgv/build_board/filter_board; distinguish company/issuer fields in #515 join without breaking legacy callers. Tests cover class/ADR/date/basis mismatch, unknown membership, 9 versus 10/19 versus 20, rank preservation, tags and versioned caches.
3. `tools/common_classification.py`: offline hash-pinned input, no overwrite, private result guard; normalize retained snapshot, project, compare classification-only with retained preview. Shared synthetic input/expectations precede the real run. Register a separate common-classification gate diagnostic before inspecting results; never apply it to official gates.
4. Retained Universe504: reuse 365/139 snapshot and retained Q213/G293 preview, preserve raw observations/gates/config and all504 members. Report code/issuer counts, old/new classifications, input versus calculation availability, and zero versus unmeasured separately. Persist private manifest/replay command in the existing authorized raw handoff branch.
5. Targeted tests and unchanged old contract smoke only when affected; existing full pytest discovery requires no CI-list edit. Draft PR + precise Main handoff, no collection/merge/deployment.

## Review focus

- A late correction must not erase the old historical decision.
- Source publication date without time must not receive a fabricated midnight.
- A classified but financially unknown company must remain usable for nonfinancial grouping.
- Unknown companies or securities must not silently shrink a complete technical group.
- Legacy saved result and official Q gate remain unchanged when only display tags or new dictionary metadata change.
