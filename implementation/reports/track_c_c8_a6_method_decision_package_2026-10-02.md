# Track C C8 — A6 Statistical-Method (G-SUP test form) Decision Package

**Status: PROPOSED / NOT APPROVED / NOT ACTIVE.** Written 2026-10-02 (KST). Source HEAD `ff78c4f` (feature/track-c-evl).
Authority: A6 partial approval (2026-10-02T20:04:01 KST) A6-S5 "TEST FORM NOT APPROVED". This package proposes the decision for S5.
S1–S4 (superiority requirement, EQUAL_SIMPLE/MARKET_CAP only, conjunction, fresh one-shot CAL_VERIFY) are approved and are not changed here.
Numeric configuration (α, B, L, seed, effect floor, minimum support) is **kept separate from the method choice**. Every number below is a
SYNTHETIC evaluation grid and **does not propose a default**. No code was implemented; C0–C7/C8 foundation blobs are unchanged.

Evidence:
- `track_c_c8_a6_method_simulation_2026-10-02.json`: all size/power/reproducibility results
- `track_c_c8_a6_method_simulation_source_2026-10-02.py`: simulation source (numpy/scipy; outside the repo runtime)
- Earlier audit: independent oracle matches the existing kernel exactly (CBB indices identical; singleton RC == U, difference ≤ 1e-17)

---

## 0. Methods compared

| ID | Form | Statistic / decision | Relation to existing code |
|---|---|---|---|
| **M-A** | Existing C6 unstudentized kernel | T=√n·mean(Δ), T*=√n·(mean*−mean), centered CBB, one-sided | Calls the frozen `family_reality_check` unchanged, with a singleton roster |
| **M-B** | Studentized CBB bootstrap-t | T=mean/se_LRV (overlapping circular block long-run variance), T*=(mean*−mean)/se*_b (replicate block-sum variance) | Reuses the frozen `circular_block_indices`; the statistic and variance are a **new method version** |
| **M-C** | Batch-means t (other new method) | Non-overlapping batches of length L, t = mean(batch)/(sd/√m), t_{m−1} distribution | No bootstrap or RNG. Needs a t CDF, so new numeric code (CI is stdlib only) |

Δ_t = net(role) − net(control), with control ∈ {EQUAL_SIMPLE, MARKET_CAP} (A6-S2), one-sided H0: μ_Δ ≤ 0.
In every form the "block length L" is part of the block convention (A6-S4) and its value is decided under A9.

## 1. Empirical size (nominal 0.05, L = ⌈n^{1/3}⌉ on the grid, 3000 datasets per cell, B=499)

MC standard error ≈ 0.004 (95% band ≈ 0.042–0.058). Format: M-A / M-B / M-C.

| DGP (dependence strength) | n=8 | n=12 | n=16 | n=24 | n=36 | n=60 | n=120 | n=240 |
|---|---|---|---|---|---|---|---|---|
| iid | .107/.034/.056 | .106/.025/.051 | .081/.030/.048 | .071/.038/.051 | .067/.041/.046 | .063/.047/.056 | .059/.045/.045 | .061/.053/.054 |
| t3 (heavy tail) | .106/.039/.047 | .103/.028/.044 | .088/.045/.044 | .071/.048/.043 | .069/.052/.048 | .057/.053/.044 | .051/.053/.045 | .050/.053/.046 |
| GARCH | .102/.028/.045 | .090/.020/.046 | .093/.039/.058 | .065/.036/.044 | .071/.043/.047 | .056/.040/.043 | .054/.044/.048 | .052/.045/.048 |
| AR 0.1 | .118/.041/.056 | .120/.032/.055 | .108/.046/.061 | .088/.050/.056 | .081/.048/.060 | .068/.044/.052 | .059/.043/.052 | .057/.044/.048 |
| AR 0.2 | .146/.049/.066 | .130/.038/.066 | .119/.048/.060 | .088/.050/.055 | .079/.043/.054 | .083/.062/.062 | .068/.052/.057 | .064/.051/.053 |
| AR 0.3 | .158/.056/.072 | .139/.047/.068 | .125/.059/.066 | .109/.068/.069 | .096/.056/.065 | .078/.061/.062 | .075/.057/.062 | .067/.059/.058 |
| AR 0.45 | .204/.076/.101 | .174/.061/.089 | .144/.066/.077 | .120/.072/.076 | .106/.070/.077 | .098/.076/.080 | .076/.060/.063 | .071/.062/.063 |
| AR 0.6 | .243/.102/.128 | .208/.085/.106 | .197/.115/.119 | .145/.100/.100 | .126/.085/.091 | .126/.107/.103 | .097/.082/.085 | .076/.066/.068 |
| MA(2) (3-period overlapping horizon) | .185/.076/.084 | .153/.054/.075 | .159/.080/.095 | .118/.067/.076 | .107/.066/.073 | .096/.073/.079 | .076/.064/.068 | .059/.053/.053 |
| AR 0.3 + GARCH | .156/.056/.077 | .132/.037/.060 | .115/.050/.060 | .107/.066/.071 | .105/.065/.069 | .083/.066/.071 | .070/.058/.058 | .063/.056/.056 |

Cells with size ≤ 0.058 (out of 10 DGPs × n group):

| n range | M-A | M-B | M-C |
|---|---|---|---|
| 8–16 (30 cells) | **0** (max .243) | 21 (max .115) | 11 (max .128) |
| 24–60 (30 cells) | 2 (max .145) | 15 (max .107) | 13 (max .103) |
| 120–240 (20 cells) | 5 (max .097) | 14 (max .082) | 14 (max .085) |

Interpretation:
1. **M-A is liberal in every condition**, including iid, and especially at small n (≈2× at n ≤ 16). Its unstudentized centered distribution underestimates the variance of short samples. The existing kernel's r/B and (r+1)/(B+1) produced **identical** rejection rates in every cell at B=499 (difference 0.0).
2. M-B and M-C are close to nominal up to weak dependence (AR ≤ 0.2) and are **conservative** at small n. Under moderate dependence (AR 0.3) they are mildly liberal, and under **strong dependence (AR ≥ 0.45, MA(2)) all three methods are liberal for n ≤ 60.**
3. **No method keeps nominal size at n ≤ 16 for every dependence structure.**

## 2. Block-length sensitivity (nominal 0.05; M-A/M-B/M-C)

| DGP | n | L=1 | L=2 | L=3 | L=4 | L=6 | L=8 | L=12 |
|---|---|---|---|---|---|---|---|---|
| iid | 12 | .068/.046/.048 | .082/.037/.051 | .106/.025/.051 | .125/.020/.050 | .165/—/— | | |
| iid | 36 | .053/.048/.049 | .057/.045/.048 | .066/.046/.049 | .067/.041/.046 | .078/.035/.051 | .089/.030/.048 | .113/.014/.050 |
| AR 0.3 | 12 | .137/.112/.111 | .136/.070/.078 | .139/.047/.068 | .152/.031/.059 | .191/—/— | | |
| AR 0.3 | 36 | .126/.117/.117 | .102/.081/.085 | .094/.065/.071 | .096/.056/.065 | .102/.049/.064 | .107/.042/.060 | .132/.024/.056 |
| AR 0.3 | 120 | .115/.112/.113 | .094/.084/.085 | .081/.071/.076 | .077/.064/.067 | .075/.057/.062 | .075/.052/.059 | .078/.047/.057 |
| AR 0.6 | 36 | .202/.194/.193 | .159/.136/.137 | .138/.104/.104 | .126/.085/.091 | .121/.063/.074 | .126/.047/.064 | .146/.032/.062 |
| AR 0.6 | 120 | .210/.209/.207 | .155/.152/.151 | .131/.123/.123 | .116/.106/.103 | .097/.082/.085 | .093/.070/.069 | .090/.060/.064 |
| MA(2) | 36 | .181/.172/.175 | .131/.111/.110 | .108/.077/.085 | .107/.066/.073 | .109/.053/.062 | .116/.044/.056 | .135/.025/.053 |

- M-A: **larger L makes it more liberal** (iid n=12: .068→.125). At small n there is no L that makes it nominal.
- M-B: as L grows it moves from liberal to strongly conservative. **At small n, L effectively determines the size**, and the right L depends on the unknown dependence. The L convention therefore changes results (A6-S4 fixes it before access).
- M-C: the least sensitive to L (iid n=36: .046–.051), but insufficient at strong dependence with small L. A NOT_RUN region appears when there are too few batches (m<3).
- An i.i.d. bootstrap (L=1) under dependence is liberal for every method (AR 0.6: ≈0.2).

## 3. Power by sample size (nominal 0.05, 2000 datasets, effect = per-period mean(Δ)/sd(Δ); M-A/M-B/M-C)

Selected L=2 (best power under this grid; L=4 and 8 are in the JSON). **M-A's power includes its size inflation, so it is not a fair comparison.**

| DGP | n | effect 0.2 | effect 0.4 | effect 0.8 |
|---|---|---|---|---|
| iid | 8 | .244/.084/.119 | .426/.154/.225 | .818/.428/.560 |
| iid | 12 | .241/.120/.144 | .470/.262/.327 | .889/.691/.768 |
| iid | 24 | .290/.215/.226 | .651/.562/.574 | .986/.971/.974 |
| iid | 60 | .464/.434/.442 | .925/.908/.915 | 1/1/1 |
| iid | 120 | .720/.700/.708 | .996/.996/.995 | 1/1/1 |
| AR 0.2 | 12 | .248/.132/.152 | .454/.264/.312 | .825/.628/.694 |
| AR 0.2 | 36 | .347/.308/.311 | .699/.650/.660 | .992/.989/.990 |
| AR 0.2 | 120 | .616/.604/.608 | .983/.982/.982 | 1/1/1 |
| AR 0.3 + GARCH | 12 | .261/.141/.164 | .462/.290/.331 | .819/.630/.704 |
| AR 0.3 + GARCH | 36 | .365/.313/.320 | .679/.627/.634 | .979/.971/.972 |
| AR 0.3 + GARCH | 240 | .812/.804/.814 | 1/1/1 | 1/1/1 |

- At n ≤ 12, M-B/M-C power at effect 0.4 (a large effect: per-period Sharpe of Δ = 0.4) is only **0.15–0.33**.
- Under the approved conjunction (2 controls × 4 cohorts, A6-S3), power drops further. Earlier audit: n=120, AR 0.3, effect 0.2 went from 0.519 for a single test to 0.198 under the IUT.
- Larger L lowers M-B/M-C power (iid n=24, effect 0.4: L=2 .562 → L=8 .225).

## 4. Expected CAL_VERIFY sample support (scenarios from repository facts; no numbers proposed)

Repository facts:
- Track A REAL-DATA Frozen baseline = **3 quarterly dated snapshots** (2024-06/09/12), **2 adjacent walk-forward steps**.
- C2 EVL-SPLIT-01 v1.1: nominal Train 5Y / Validation 1Y / OOS 1Y, annual rolling/expanding.
- A1: CAL_VERIFY is a sub-partition of an outer calibration interval between Development/C7 and the Final Holdout. Its actual boundaries are not registered (A9 N-D1/D2).
- The 4 required cohorts (Rolling/Expanding × Primary/Gap-stress) are **variants over overlapping calendars**, so they do not add independent periods.

Scenario mapping (period frequency × CAL_VERIFY length → n):

| Period frequency | 1 year | 2 years | 3 years | 5 years |
|---|---|---|---|---|
| Quarterly (current Track A snapshot cadence) | 4 | 8 | 12 | 20 |
| Monthly (if a producer supplies it) | 12 | 24 | 36 | 60 |

Conclusions:
- If quarterly cadence continues, CAL_VERIFY's realistic n is **4–12**. At n=4, M-B (fewer than 2 replicate blocks) and M-C (fewer than 3 batches) are **NOT_RUN** for most L; M-A runs but is severely liberal and has only 35 distinct resamples (n=4, L=1) or 9 (L=2).
- **Under the current data cadence, no test form can produce a G-SUP real decision with controlled size.** Unless the expected support grows to a level verified by simulation (more periods/frequency, or a longer CAL_VERIFY), the likely real outcome is a feasibility NOT_RUN. This is a data-design issue for A1/A9, not a method issue.

## 5. Computational reproducibility

| Item | M-A | M-B | M-C |
|---|---|---|---|
| Determinism (same seed) | Verified: identical draws and hashes within and across processes (Python 3.11.15) | Same as M-A if it reuses the shared indices (new code needs its own verification) | No RNG; fully deterministic |
| Roster-order invariance | Verified (kernel sorts) | Needs design | Not applicable |
| RNG dependence | Python `random.Random` (Mersenne Twister) stream. A different implementation/version must be re-verified | Same | None |
| MC error | Exists. Across 20 seeds, n=120, B=199: tail 0.317–0.462 | Same | None |
| Cost | n=120, B=999 ≈ 0.2 s (pure Python) | Similar, plus variance per replicate | Negligible |
| New numeric code | None (adapter only) | Statistic, variance, adapter | t CDF (stdlib has none) → needs its own oracle |

## 6. Method-versioning impact

| | M-A | M-B | M-C |
|---|---|---|---|
| Frozen C6 blobs | Unchanged (calls the frozen kernel) | Unchanged (reuses `circular_block_indices`) | Unchanged |
| New method ID | `C8_GSUP_U_v1` = `EVL_STATISTICAL_KERNELS_v1` + a one-sided singleton adapter | `C8_GSUP_STUDENTIZED_CBB_v1` (new kernel file) | `C8_GSUP_BATCH_MEANS_T_v1` (new kernel and t CDF) |
| Independent oracle | Done (exact match) | Needed (independent implementation of statistic and variance) | Needed (t CDF oracle) |
| Future change ripple | Changing a C6 kernel is blocked by the C6 Freeze. Any C6 change invalidates the C8 pin | Can be changed independently, but a C8 version change → the preregistration hash changes | Same |
| Reuse of C6 joint dependence | Yes (same index convention) | Yes | No (different dependence handling than C6) |

## 7. Result-changing choices (approval pending; numbers separate)

### Q1 — Test form
- **A (M-A)**: liberal in every condition; the highest FP risk. **Not recommended for a hard decision.**
- **B (M-B)**: closest to nominal at weak dependence and small n, uses the C6 index convention. Its size depends heavily on L, and it is liberal under strong dependence.
- **C (M-C)**: deterministic and least sensitive to L; slightly more liberal than M-B at small n; needs a new t CDF.
- **Recommendation: B**, with Q2–Q4 below required as conditions. C is kept as a recorded alternative and inactive.

> Approval sentence: "A6-S5 Q1 option B is approved. The G-SUP test form is the studentized circular-block bootstrap-t (C8_GSUP_STUDENTIZED_CBB_v1), using the frozen C6 `circular_block_indices` convention. M-A (the existing unstudentized kernel) is not used for hard decisions, and M-C is kept as a recorded alternative but inactive. This approval does not include α, B, L, seed, the effect floor or minimum support."

### Q2 — Pre-access size-validation (feasibility) criterion
In the simulation, nominal size depends on the combination of n, L and the dependence structure. Options:
- **A**: Before CAL_VERIFY access, run a **simulation demonstrating size and power** under the preregistered (n, L, B) and a preregistered **dependence envelope**. If simulated size exceeds the preregistered tolerance anywhere in the envelope, the result is **NOT_RUN_INFEASIBLE** (decided before access, no adjustment).
- **B**: Rely only on an asymptotic argument (no feasibility check). Small-n liberality is left in place.
- **Recommendation: A.**

> Approval sentence: "A6-S5 Q2 option A is approved. Before CAL_VERIFY access, a size/power simulation under the preregistered n, L, B and dependence envelope is attached to the registration. If the simulated size exceeds the preregistered tolerance in that envelope, G-SUP is recorded as NOT_RUN_INFEASIBLE before access. The tolerance and the envelope's numeric values are preregistered separately."

### Q3 — Source of the dependence envelope
- **A**: Estimate Δ's dependence (for example autocorrelation and a variance ratio) from **Development data only (before CAL_VERIFY access)**, plus a preregistered conservative margin.
- **B**: A fixed conservative envelope independent of the data (for example covering up to the strongest DGP in this package).
- **C**: A + B (the stricter of the two).
- **Consequence**: A adapts to the data but carries estimation error. B is safe but makes NOT_RUN frequent at small n (by this package's table, B with n ≤ 60 is almost always INFEASIBLE). Using CAL_VERIFY to estimate dependence is prohibited (A6-S4).
- **Recommendation: C** (but conditionally, depending on the user's tolerance for NOT_RUN).

> Approval sentence: "A6-S5 Q3 option C is approved. The dependence envelope is the stricter of the Development-only estimate (plus a preregistered margin) and a preregistered fixed conservative envelope. CAL_VERIFY data is not used for dependence estimation."

### Q4 — Handling infeasibility
- **A**: NOT_RUN_INFEASIBLE (no other form, L or data is substituted).
- **B**: Automatically fall back to a more conservative form (for example M-C) → an A6-S4 violation (changing the statistic). Listed for comparison only.
- **Recommendation: A.**

> Approval sentence: "A6-S5 Q4 option A is approved. Infeasibility is recorded only as NOT_RUN_INFEASIBLE, with no automatic replacement of the form, block convention, seed, B or data."

### Q5 — Block convention semantics (not the value)
- **A**: A preregistered single fixed L.
- **B**: A preregistered deterministic rule L = f(n) (for example of the form ⌈c·n^{1/3}⌉; c is a number to register).
- **C**: Data-driven automatic selection (for example Politis–White) → **not recommended**: a result-dependent choice that conflicts with A6-S4. If used, only on Development data.
- **Recommendation: A or B** (the user's choice; with one CAL_VERIFY, A and B are effectively the same).

> Approval sentence (if A is chosen): "A6-S5 Q5 option A is approved. The G-SUP block length is a single preregistered integer fixed before CAL_VERIFY access, and is never selected automatically from the data."

### Q6 — p-value convention
- (r+1)/(B+1) (A6-6 B in the earlier package) vs. raw r/B. In this package's simulation (B=499), the rejection rates were identical, but they differ at small B or near the boundary.
- **Recommendation: (r+1)/(B+1)**, with a pre-access check that the minimum attainable p is at or below the decision threshold (otherwise NOT_RUN_INFEASIBLE).

> Approval sentence: "A6-S5 Q6 is approved. The G-SUP decision p-value is (r+1)/(B+1). If 1/(B+1) exceeds the decision threshold at registration, the result is NOT_RUN_INFEASIBLE."

## 8. Separation from numeric configuration (still not approved)

| Item | Status after this package's approval |
|---|---|
| α (per-test level under the IUT) | Not approved (A9 N-S10) |
| B, seed | Not approved (N-S12, N-S14) |
| L or the rule coefficient | Not approved (N-S13) |
| Size tolerance, dependence-envelope values and margin | **New A9 items** (N-S19 tolerance, N-S20 envelope, N-S21 margin) — not approved |
| Minimum sample support | Not approved (N-D5). Section 4 shows the likely real support (4–12 at quarterly cadence) is very small |
| Effect floor | Deferred (A6-S7) |

## 9. Summary judgement

- The existing unstudentized kernel (M-A) **does not keep nominal size** for hard decisions, especially at small n.
- The studentized bootstrap-t (M-B) is the best of the three at weak dependence, but **at small n its size is effectively decided by the block convention**, and it is liberal under strong dependence.
- At the **expected CAL_VERIFY support** under the current data cadence (quarterly, n ≈ 4–12), **no form keeps nominal size and has meaningful power**. So the recommended path is not to choose a method and force a decision, but **method B plus a pre-access feasibility gate (NOT_RUN_INFEASIBLE)**. If an actual G-SUP decision is wanted, increasing CAL_VERIFY period support (frequency or length) in the A1/A9 data design is a prerequisite.

**STOP — awaiting approval of result-changing choices Q1–Q6. No implementation started. C8 NOT FROZEN, 8/11 = 72.7%, Holdout UNCONSUMED, Package B/C unchanged.**
