# Track C C8 G-SUP — approved M-B simulation vs implemented kernel: minimal counterexamples

**Status: USER_DECISION_REQUIRED (authoritative method). Evidence only / NOT_AN_APPROVAL.** Recorded 2026-10-03 under CDR-005.
"M-B" = the studentized CBB variant in `track_c_c8_a6_method_simulation_source_2026-10-02.py` (`run()`, `S_plus1`), whose size/power
tables backed the Q1 approval. "Kernel" = `C8_GSUP_STUDENTIZED_CBB_v1` in `evl/superiority.py` (ccr-22e3ff16-p7n5k5).
Both use identical original-sample statistic T = mean/se_LRV (all n overlapping circular blocks), the frozen C6 indices, `>=` and (r+1)/(B+1).
Data/source: `track_c_c8_gsup_mb_vs_kernel_counterexample_2026-10-03.{json,_source...py}`. All inputs are SYNTHETIC; B/L/levels are evaluation-only.

## Exact differences (only two)
| | M-B (approval evidence) | Kernel (implemented) |
|---|---|---|
| D1 replicate variance blocks | first ⌈n/L⌉−1 blocks | ⌊n/L⌋ full blocks |
| D1′ runnable when | ⌈n/L⌉−1 ≥ 2 | ⌊n/L⌋ ≥ 2 |
| D2 degenerate replicate (variance 0) | never exceeds (t* = −∞) | counts as exceedance |

D1 bites only when L divides n (then M-B drops one full block). D2 bites only when a replicate is degenerate (probability ≈ 1/n per
replicate when there are exactly 2 blocks). When L does not divide n and no replicate is degenerate the two are identical (300/300 checked).

## Minimal counterexamples
| ID | Isolates | Input (n, L, B, seed) | M-B | Kernel |
|---|---|---|---|---|
| CE1 | D1′ runnability | [0.03,−0.01,0.02,0.01] (4, 2, 19, 1) | **NOT_RUN** (1 block) | runs: p = 0.30 (5 degenerate, all counted) |
| CE5 | D1 block count only | [0.008,0.003,−0.02,0.019,0.012,−0.01,0.019,0.002] (8, 2, 19, 18) | 3 blocks, p = 0.30 | 4 blocks, p = 0.25 |
| CE4 | D2 degenerate scoring only | [−0.016,−0.007,0.053,0.023,0.005] (5, 2, 19, 200) | p = 0.10 (decision REJECT at evaluation 0.10) | p = 0.15 (NOT_REJECTED) |
| CE2 | D1 + D2 | [0.03,−0.01,0.02,0.01,0.00,0.02] (6, 2, 19, 1) | p = 0.05 | p = 0.10 |
| CE3 | none (control) | [0.03,−0.01,0.02,0.01,0.00] (5, 2, 19, 1) | p = 0.05 | p = 0.05 |

## Consequences
- The approved size/power tables describe M-B exactly; they describe the kernel exactly only where D1/D2 are inactive.
- D2 kernel rule is more conservative (fewer rejections; at very small n rejection becomes practically impossible, see impact evidence item 3).
- D1 kernel rule runs on one more block when L | n (M-B would be NOT_RUN at ⌊n/L⌋ = 2) — the kernel accepts smaller supports than the evidence covered.

## USER_DECISION_REQUIRED
- **Option K** — the implemented kernel is authoritative. Its size must then be re-established with the kernel's own conventions
  (the Q2 pre-access feasibility gate already simulates the exact kernel, so real decisions remain size-checked).
- **Option M** — M-B is authoritative. The kernel would change to ⌈n/L⌉−1 blocks and degenerate = non-exceedance under a new method version
  (e.g. `_v2`); `_v1` is retained, not rewritten.
- **Option C** — another explicit convention (e.g. degenerate replicates excluded with B_eff), requiring new evidence.
No option is selected here; no code was changed for this item.
