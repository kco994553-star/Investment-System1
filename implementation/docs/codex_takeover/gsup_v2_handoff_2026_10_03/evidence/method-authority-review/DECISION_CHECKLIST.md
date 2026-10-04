# PR31 M-B arithmetic decision checklist — independent read-only review

Scope: PR31 source `675d0d298fbaab5b8473ed048a561ef84e2f3e78`, original owner `b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565`. This is decision evidence, not an arithmetic choice, numeric approval, Freeze or grant. The authoritative production v2 kernel is **NOT_IMPLEMENTED** pending the arithmetic decision.

## Authority already fixed

Original conditional Q1 approval, recorded `2026-10-02T11:43:44Z`, selects M-B and inherits the frozen C6 `circular_block_indices` convention. The package §0, §5, §6 and §7/Q1 specify that shared convention; its RNG is Python `random.Random`, not the NumPy simulation RNG. Q2–Q6 still require pre-access synthetic feasibility, preregistered dependence bounds, no fallback/retest, a block rule fixed before access, plus-one p-values and alpha reachability.

The explicit M approval recorded `2026-10-03T06:56:04.745959+00:00` says: “M을 승인한다. 승인된 M-B simulation convention을 G-SUP의 authoritative method로 유지하고 이를 별도 v2로 구현한다.” It requires statistic, replicate construction, variance and degenerate/tie handling to match; it preserves v1 and prohibits rewriting historical results. That record separately identifies `USER_DECISION_REQUIRED_ARITHMETIC_REDUCTION`. M remains approved. The pending decision does not reopen the method choice or permit changes to Frozen C6.

The original Q1 package's pending-approval header and the old M/K/C choice queue are superseded only for the approved method choice. The original simulation and counterexamples remain immutable historical evidence. Numeric configuration, actual CAL_VERIFY access, Holdout, C8 Freeze, Official/publication, canonical merge and deployment remain unapproved.

## Mathematical rules shared by all arithmetic candidates

For a single series of length n and explicit L, set k = ceil(n/L), q = k−1, rem = n−qL. The final block has 1 through L observations. If L divides n, rem = L: the last block is full length, but is still excluded from the replicate variance. Require q ≥ 2; otherwise NOT_RUN.

Let μ be the mean of all n observations, and S_s the sum of the circular L-block starting at s for each s from 0 through n−1. The observed long-run variance is Σ_s(S_s−Lμ)²/(nL), and T = μ/√(LRV/n). The precise arithmetic used to obtain these sums is the pending choice.

Each replicate uses the frozen C6 indices, including its truncated final block, to obtain a mean μ_b over all n sampled observations. Replicate variance uses the first q full blocks only, centered at Lμ_b, with denominator qL. It does not center at a mean of those q blocks, use a Bessel q−1 denominator, or omit the final observations from μ_b. T_b = (μ_b−μ)/√(v_b/n).

A degenerate replicate never exceeds, remains in B, and is not retried or excluded using B_eff. Nondegenerate ties count through T_b ≥ T. The p-value is (r+1)/(B+1). An undefined original statistic remains fail-closed NOT_RUN. On the all-zero diagnostic the raw simulation transports a NaN original statistic into S_plus1=.05; that raw output is not an executable decision. No added tolerance, near-zero cutoff, rounding, quantization, fallback or numeric default is proposed.

The preserved v1 uses floor(n/L) variance blocks, math.fsum and degenerate-as-exceedance. Its presence is historical/compatibility behavior; approving M did not authorize silently retaining those v1 block/degenerate rules in v2.

## The remaining three transports

1. **Literal Q1 NumPy reduction algebra, currently qualified with NumPy 2.3.5.** It uses float64 arrays, cumulative sums and cumulative differences for circular/full/remnant block sums, NumPy mean and squared-sum reductions, and the original grouping `(sum(full block sums)+last)/n` for replicate means. The frozen C6 stream supplies starts in place of `rng.integers`. Current evidence matches the unchanged Q1 `S_plus1` p-value bit for bit on all seven runnable fixtures in each of four available NumPy 2.3.5 fresh processes. This is exact current source-algebra p reproduction under the mandatory RNG substitution, not an exact historical simulation/environment claim. The comparison does not expose every original intermediate to prove full trace identity.

2. **M-B equations with math.fsum.** This uses math.fsum for original/sample means, direct circular/full-block sums and variance reductions while retaining the approved q, denominator and degenerate/tie rules. It is mathematically M-B, but it is not the literal NumPy cumulative transport and must be approved as its own arithmetic contract. Its use in preserved v1 does not by itself approve it for v2. The observed runtime agreement is limited to the qualified fixtures and environments.

3. **Explicit Python 3.11-style left-to-right binary64 reduction.** A qualified CPython 3.11 runtime's actual builtin sum and the explicit left-sum reconstruction coincide in this evidence. Generic builtin sum is insufficient as a version-independent contract: actual CPython 3.12/3.13 produce different results on the same existing fixtures. The reconstruction is a control that specifies the old order, not proof that unqualified current builtin sum preserves it or that the original NumPy simulation used it.

None can claim exact historical M-B aggregate table replay. The historical record does not pin the NumPy/SciPy simulation versions or full runtime. Its Python 3.11.15 reproducibility metadata refers to the C6 index/kernel subsection. NumPy's original `default_rng` stream is also different from the mandatory frozen C6 stream. Same seed alone does not equate them. The available Python 3.13 environment contains NumPy 2.2.4: the NumPy 2.3.5 candidate is correctly NOT_RUN there, with no fallback or re-pin.

## Observed result impact

- Existing `ARITHMETIC_NUMPY_FLIP`, n=8, L=3, B=19, seed=46: math.fsum and left-sum give r=1, two degenerate replicates, p=.10; qualified NumPy gives r=3, no degenerates, p=.20. Both actual builtin runtimes 3.11 and 3.12 give .10.
- Existing `ARITHMETIC_LEFT_SUM`, n=9, L=4, B=19, seed=34: actual builtin 3.11 and explicit left-sum give r=7, no degenerates, p=.40; actual builtin 3.12/3.13, math.fsum and qualified NumPy give r=6, one degenerate, p=.35.
- Existing `ARITHMETIC_TIE`, n=6, L=2, B=19, seed=72: actual builtin 3.11 and explicit left-sum give r=7, one tie, p=.40; actual builtin 3.12/3.13, math.fsum and qualified NumPy give r=8, three ties, p=.45. Every transport keeps the same ≥ tie policy and two degenerate replicates.
- Immutable CE4 JSON and MD both record **M-B .10 versus preserved v1 .15**. Every available current M-B candidate and the current literal Q1 replay give .10. An internal review request reversed those labels; direct source inspection resolved it. No historical artifact was edited and no source/result conflict exists on CE4.
- CE2's p=.05 agrees across M-B transports while its degenerate count differs (one in scalar transports, zero in qualified NumPy). Matching p alone therefore does not certify identical intermediate arithmetic.

All these B/L/seed values are existing synthetic diagnostic inputs, not approved operational configuration or new defaults. The old counterexample's “only two differences” and “identical” statements describe its mathematical/sampled p comparison; they cannot be expanded to bit-identical arithmetic or universal equivalence after these counterexamples.

## Decision to record before implementation

- Select one complete arithmetic transport for new versioned M-B v2, including mean, block-sum, variance, replicate-mean grouping, dtype/order and runtime/library qualification. No choice is inferred by this review.
- For the NumPy choice, explicitly bind the selected version and source expressions, retain mandatory Frozen C6 RNG, and accept that unavailable qualification fails closed. Historical exact-environment replay remains unverified.
- For math.fsum, explicitly approve that reduction in M-B equations; do not label it literal original NumPy arithmetic or preserve v1 block/degenerate behavior by accident.
- For Python 3.11-style arithmetic, explicitly bind left-to-right binary64 behavior or a qualified 3.11 runtime; do not use unqualified builtin sum across versions.
- Keep q/remnant, variance center/denominator, degenerate/tie and undefined-original rules fixed as above; keep v1/Frozen/evidence unchanged and never rewrite v1 outcomes as v2.
- Leave α, B, L/block rule, seed, effect floor, minimum support, size tolerance, envelope/margin, real source taxonomy, CAL_VERIFY/Holdout, registry unification, Freeze and grants outside this decision.

Independent review verified 26 replay artifact hashes, 48 exact Git-source bindings (eight distinct sources across six process receipts), 216 numeric trace commitments, 154 computed trace counts/plus-one values and 28 literal p-bit matches. It verified three byte-identical process pairs, nine unchanged fixtures and their shared recorded index streams. The arithmetic worker actually executed the six fresh processes and the reported 176 index comparisons per process. The driver's rounded `r_recovered` is display metadata derived from the original p-value; it is not used to form a statistic, count exceedances or make a decision. This reviewer executed JSON/hash/AST/count checks only; numerical replay, production v2 tests, full regression and Actions were **NOT_RUN** by this reviewer.
