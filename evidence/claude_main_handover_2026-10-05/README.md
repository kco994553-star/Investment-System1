# Handover from the previous Main (Claude Code session `session_019znshzTYgyBnuuBmSxdPFN`) — unpublished outputs

Prepared 2026-10-05 ~14:35 KST after reading CDR-018 (Main transferred to GPT Work `gpt-work-main-2026-10-05-3a80dcef6444`). The previous Main stopped all shared integration writes at that point. Nothing here is a decision, approval or verified closure; these are raw intermediate outputs, offered to the successor as inputs.

| File | What it is | State |
|---|---|---|
| `cdr015_decision_round.json` | workflow `wf_4e292ba4-85c`: analyses of FPIA D3-a, D3-b, D3-c, D3-d, D3-e and G7 (requirement, alternatives, recommended PIW decision, verification, recovery, implementation changes), adversarial review of D3-b, and two inventories of open items (coordination docs; remote) | analyses complete; reviews of D3-a/c/d/e/G7, reclassification, integration plan and synthesis NOT RUN (session limit) |
| `chart_pr41_routing.json` | workflow `wf_4a3fbe46-9d8`: six owner-state readers for Chart PR #41's gates (Chart request slots and preflight usage, Portfolio, Identity, Product/P01 + Web, QGV, Integration) | readers complete; per-gate routing, adversarial verification, automation-gap analysis and synthesis NOT RUN |
| `qgv_platform_routing.json` | workflow `wf_2e2232f2-8be`: QGV state reader (15 cross-owner items X01–X15) and Product Platform discovery reader (items PLAT-00/01, D1–D9, G1–G2) | readers complete; routing, verification, propagation design and synthesis NOT RUN |
| `fpia_fix_round_3.json` | workflow `wf_bdfed701-366` journal | no agent result recorded; fix3 pushed `11d2f25` to PR #42 before the session limit, but its report, the v3 verifiers and completeness never ran |
| `fpia_fix3_local_evidence/` | fix3's local evidence for `11d2f25`: H8 over-detection measurement on real trees (`h8_final.json`), variant battery on acaf1b5, commit message, scripts | unreviewed; not independently verified |
| `fpia_fix_round_2_complete_results.json` | workflow `wf_91d664d4-8f3` complete results (fix2, v2-real, v2-regress-ci, v2-adversarial) | complete; its findings drove fix round 3 |
| `fpia_round2_adversarial_classification_156.json` | v2-adversarial classification of 156 variants at `523e702` (76 hold, 22 D1, 41 D2, 9 D3-c, 1 D3-e candidate, …) | complete |
| `GIE-014_DRAFT_by_previous_main_UNPUBLISHED.md` | the previous Main's partial GIE-014 draft (placeholders left) | superseded in name by the successor's GIE-014; content only |

Integrity: `SHA256SUMS`. Larger artifacts (probe trees, clones, venvs) stay in the previous session's scratch area and are not included.

## Added 2026-10-05: repro and regression material (`repro_and_regression/`)

- `round2_adversarial/`: scripts that reproduce the round-2 bypasses (`harness.py`, `run_battery.py`, `variants.py` = 156 variants, `probe_static.py`, `probe_det.py` = environment-dependent verdicts, `mkcommit.py`), their outputs (`out_v3/`: battery, classification, ICU confusable sweep), G3/G4/G6 probes, and the S24V2 end-to-end run scripts (T = 3b09df4e…, FPIA_PASS on a spoofing tree at 523e702).
- `round1_adversarial/`, `real_runs/`: earlier probe sets and the real-run drivers/tables.
- The fix-round regression tests themselves are committed on PR #42 (`integration/fpia-hardened-v1`), not duplicated here.
- Scripts expect the previous session's clones/venvs and paths; they are references, not turnkey.
