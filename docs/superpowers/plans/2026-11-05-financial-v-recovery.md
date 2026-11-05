# Financial V recovery implementation plan

> **For agentic workers:** Use superpowers:executing-plans task by task; owner has authorized autonomous implementation.

**Goal:** Recover exact archived inputs and calculate separate financial V candidate raw metrics without changing official QGV.
**Architecture:** Offline XBRL supplement adapter, unchanged official normalization, isolated financial metric evaluator, private CLI output.
**Tech Stack:** Python standard library and pytest.
**Spec:** implementation/docs/research/FINANCIAL_V_RESEARCH_20261105.md

## Global Constraints

No external collection, official formula/version changes, merge, deployment, workflow changes or public real values. Fixed 504 denominator. Raw ratio availability is not a V score.

## Review Focus

- XBRL dimension, entity, namespace and units must not contaminate consolidated facts.
- Conflict and future filing cannot override archived observations.
- EPS/book inputs must match price currency and share basis.
- Missing/negative data must remain null, not neutral scores.
- Alternate-date or ex-post diagnostics cannot increase same-date coverage.

### Task 1: Exact archived XBRL supplement
Files: `implementation/src/investment_system/research/xbrl_supplement.py`; `implementation/tests/test_xbrl_supplement.py`.
Interface: `supplement(payload, xml, filing, cutoff) -> (copied_payload, audit)`.
- [x] Test exact missing insertion, duplicate/conflict, dimensional/foreign entity, future filing and prohibited custom/unit inputs; run red.
- [x] Implement allowlisted, source-preserving supplement; run green.
- [x] Run on 47 existing targets; preserve changed fields and normalizer comparisons privately.

### Task 2: Financial candidate evaluator and CLI
Files: `implementation/src/investment_system/research/financial_v.py`; `implementation/tools/financial_v_research.py`; `implementation/tests/test_financial_v.py`.
Interface: `evaluate(row) -> result`; CLI local JSON rows to private output.
- [x] Test business routing, ratio arithmetic, negative/missing/unit/basis/date failures, ex-post isolation and CLI; run red.
- [x] Implement raw ratios only, immutable research version/config; run green.
- [x] Calculate same-date 68 rows and separate held-price fiscal diagnostics. Preserve 504 coverage and acquisition gaps privately.
- [ ] One independent calculation review, required checks once, Draft PR, private remote preservation/readback.

Execution record: 47 targets; 254 exact observations supplement four codes, all original missing requirements remain. Official Q/G recalculated on504 codes; G scores change71 codes without changing valid counts. One independent review: preferred par-value subtraction rejected, class evidence disclosed, diagnostic period enforced; regression tests red then green. Same-date V/total rescore blocked only by missing original daily quotes, not history research. No official modules edited.
