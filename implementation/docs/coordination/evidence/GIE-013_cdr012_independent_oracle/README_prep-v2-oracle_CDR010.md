# prep-v2-oracle: CDR-010 reference oracle for re-verifying Codex PR #31 (M-B v2)

**Authority: none.** This is read-only integration prep by the Primary Integration Writer's agent. It is not a Track C approval and does not set acceptance thresholds. It does not approve numeric configuration. Inputs are synthetic and for software validation only. Nothing here touched CAL_VERIFY, Holdout, the network, a remote ref, or a repository path. Codex's v2 code was not read: no file under `origin/codex/track-c-gsup-v2-2026-10-03` was opened except the simulation source, whose blob is identical at `b9e01a9`.

## 1. What is implemented

`oracle_cdr010.mb_v2(x, L, B, seed)` with its default keyword arguments implements the CDR-010 contract together with the unchanged CDR-006 fields. Sources:

- Approved simulation `run()` / `S_plus1` (blob `e112f41f`).
- The C6 index convention (`statistical_kernels.circular_block_indices`, blob `28e1c184`).
- The v1 kernel (blob `8a1254d7`), for comparison only.

The algorithm:

```
k = ceil(n/L); q = k-1 (variance blocks); rem = n - q*L (1..L); q < 2 -> NOT_RUN
m   = fsum(x)/n
S_s = fsum(x[(s+j)%n], j<L)                       direct circular block sums, every start s
lrv = fsum((S_s - L*m)*(S_s - L*m))/(n*L); se = sqrt(lrv/n); not se > 0 -> UNDEFINED_STATISTIC_ZERO_SE
T   = m/se
replicate b (C6 starts s_0..s_{k-1}, random.Random(seed).randrange(n) per block):
  b_j = fsum(x[(s_j+i)%n], i<L) (j<q); P = fsum(x[(s_q+i)%n], i<rem)
  ms  = (fsum(b_0..b_{q-1}) + P)/n
  v   = fsum((b_j - L*ms)*(b_j - L*ms))/(q*L); sv = sqrt(v/n)
  degenerate iff not sv > 0  -> never counted
  t = (ms-m)/sv; counted iff t >= T; tie iff t == T
p = (r+1)/(B+1)
```

The default reading of the axes that CDR-010 leaves open is `square='mul'`, `partial_add='add'`, `grouping='blocks'`, `predicate='sqrt_v_over_n'`. Each axis also has a diagnostic variant (see §4).

- `oracle_cdr010_alt.mb_v2_alt` is a second, independently written implementation. It draws block starts directly and tabulates block sums once. It works column-wise over the replicates. It emulates every IEEE operation (sum, add, sub, mul, div, sqrt) as an exact Fraction followed by one round-half-even step. It decides degeneracy in Fractions: `v/n <= 2**-1075`. It never calls `math.fsum`, float `*` or `/`, or `math.sqrt` for the statistic.
- `exact_decimal` / `exact_binary`: exact rational M-B. Inputs are read as decimal strings or as the binary64 values. There is no sqrt: the comparison uses signs and squares.
- `literal_numpy_run` imports the **unmodified** simulation source and calls `run()`. The source is a byte copy `sim_source_e112f41f.py`, and its git blob and sha256 are verified on load. An rng shim feeds the C6 start rows. Per-replicate flags come from `run()` with B=1, and are cross-checked against a line-by-line transcription and against the aggregate.
- `v1_kernel` calls the real `superiority.studentized_cbb` from `src_b9e01a9`, a `git archive` of `b9e01a9:implementation/src`. Blobs are verified on import.

## 2. Results (Python 3.11.15, numpy 2.3.5, scipy 1.16.2 (only used by run()'s BM_t), glibc 2.39)

- **C6 replica** (`prove_c6.py` → `c6_replica_proof.json`):
  - 3000 (n, L, B, seed) combos, 113,013 replicates. n ranges over 1..64; 372 combos have negative seeds and 736 have seeds ≥ 2^32.
  - 0 mismatches for the primary `c6_indices`, for the alt's direct-start generator and for the alt's starts, each compared with the real kernel.
- **Fixtures** (expected values from GIE-008 §2). All five agree. The alt is bit-identical on all of them.

| Fixture | CDR-010 p | r / deg / ties | T | exact dec | exact bin | literal run() | v1 |
|---|---|---|---|---|---|---|---|
| CE4 n5 L2 B19 s200 | **.10** | 1/1/0 | `0x1.01cab10fef960p+0` | 2/20 | 3/20 | 2/20 | .15 |
| FLIP n8 L3 B19 s46 | **.10** | 1/2/0 | `0x1.3988e1409212ep+0` | 2/20 | 2/20 | 4/20 | .20 |
| LEFT_SUM n9 L4 B19 s34 | **.35** | 6/1/0 | `0x1.8624f6c0a4dbcp+0` | 7/20 | 7/20 | 7/20 | .40 |
| TIE n6 L2 B19 s72 | **.45** | 8/2/3 | `0x0.0p+0` | 9/20 | 9/20 | 9/20 | .55 |
| SEED275 n5 L2 B19 s275 | **.55** | 10/2/0 | `0x1.0aaaaaaaaaaacp-54` | 11/20 | 10/20 | 10/20 | .60 |

Literal `S_plus1` hex values reproduce GIE-008: CE4 `0x1.999999999999ap-4`, FLIP `0x1.999999999999ap-3`, LEFT_SUM `0x1.6666666666666p-2`, TIE `0x1.ccccccccccccdp-2`.

- **Battery**: 681 cases, of which 676 are graded and 71,004 graded replicates. The groups:
  - 5 fixtures.
  - 648 random cases: 9 families × 72; n 4..30; L 1..6 with ceil(n/L)-1 ≥ 2; B 19/99/199 = 212/208/228; 320 cases with L | n.
  - 10 subnormal-predicate edges.
  - 12 square-axis edges.
  - 6 undefined/near-undefined edges, 1 of them graded.
- **Second implementation**: bit-identical on 681/681 cases. That covers T, r, deg, ties, p, the per-replicate codes and t bits, and the block starts.
- **Third-party cross-check**: the GIE-008c probe (`gie008c_probe.py`, sha256 `e2312fd8…`) in `fsum/blocks` mode equals this oracle's `square_pow` variant on 676/676 graded cases (r, deg, ties, T bits). It also equals the CDR-010 p on 676/676. Its T bits differ from the CDR-010 default only on the 12 `E-SQUARE-*` cases, because the probe uses Python `**2`. See `gie008c_crosscheck.json`.
- **Random battery, CDR-010 vs comparators** (648 cases, 69,992 replicates; 85 cases have degenerate replicates, 15 have ties):

| comparator | equal p | flipped replicates by reason |
|---|---|---|
| exact decimal | 599/648 | TIE 266, DEGENERATE 33. Cause: decimal input 202, float arithmetic 97 |
| exact binary | 608/648 | ROUNDING 107, DEGENERATE 21, TIE 15 |
| literal NumPy run() | 589/648 (T bits equal 271/648) | ROUNDING 194, TIE 98, DEGENERATE 52 |
| v1 kernel | 450/648 (T bits equal 648/648) | V1_DEGENERATE_COUNTED 407, V1_VARIANCE_BLOCKS 339, ROUNDING 97, TIE 16, DEGENERATE 5 |

Most of the differences come from `decimal_zero_mean`: exact-decimal p differs in 41 of its 72 cases, because the decimal T is exactly 0 while the float T is a few ulps away from 0.

## 3. How to compare Codex's v2 when PR #31 reaches HANDOFF_READY

1. `git fetch origin`. Record the exact PR #31 head (`git ls-remote origin refs/pull/31/head`). Extract that head read-only, using `git archive <head> implementation/src | tar -x -C <your dir>/src_v2` or a detached worktree under your own dir.
2. Read Codex's v2 and find its entry point. Write `v2_adapter.py` in your own dir, with `adapter(x: list[float], L, B, seed) -> dict`:
   - Required keys: `T` (float), `r` (int), `deg` (int), `p` (float).
   - Optional keys: `status` (anything other than `"OK"` counts as a refusal), `ties`, and `draws` (one entry per replicate: a float t, or `None` when degenerate).
   - If v2 returns v1-shaped keys (`statistic`, `exceedances`, `degenerate_replicates`, `p_value`, `draws`), use `compare_v2.adapter_v1_shaped(fn)`. It calls `fn(x, block_length=L, replicates=B, seed=seed)`.
   - Pass any registration or wrapper arguments v2 needs, but keep the arithmetic path the one that production uses.
3. Run the comparison. Do not put `src_b9e01a9` on the path at the same time, because both trees provide `investment_system`:
   ```
   PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<this dir>:<your dir>/src_v2/implementation/src:<your dir> \
     <this dir>/venv/bin/python <this dir>/compare_v2.py --adapter v2_adapter:adapter --out v2_compare.json
   ```
4. **Fields that must match exactly** on every graded case (expected status OK), 676 in total:
   - `T.hex() == cdr010.T_hex`;
   - `r == cdr010.r`;
   - `deg == cdr010.deg`;
   - `p.hex() == cdr010.p_hex`, which is (r+1)/(B+1);
   - if exposed, `ties == cdr010.ties`;
   - if exposed, `draws`: the degenerate pattern, and `float(t).hex() == cdr010.t_hex[b]` for each b.

   Verdict `EXACT_MATCH_ALL_GRADED` and exit code 0 are required before items 5 and 6b can be PASS. Without `draws` the harness is much weaker: the partial-add and grouping mutants are then caught on only 21 and about 42 cases, instead of 569 and 585. Prefer an adapter that exposes per-replicate t.
5. **Index stream**: if v2 exposes its indices or starts, compare them directly with `oracle_cdr010.c6_indices`. Do not compare hashes, because hash formats differ. If v2 has its own index generator, rerun `prove_c6.py` against it.
6. **Ungraded cases** (`ungraded_contract_silent`; the 5 `E-UNDEF-*` / `E-NEARUNDEF-*` cases where CDR-010 is UNDEFINED): report what v2 does. Do not grade it. For reference:
   - literal `run()` returns p = 1/(B+1) on all 6 edge cases (fail-open);
   - v1 raises `MissingStatisticalEvidence` on 5 of them;
   - the exact oracles say all 6 are undefined.
7. **Triage of mismatches**: each mismatch row has `matches_reference`.

| matches_reference | meaning |
|---|---|
| `variant:square_pow` | v2 squares with Python `**2` (libm pow). This axis is not pinned by CDR-010; see F1 |
| `variant:partial_single_fsum` | v2 computes `fsum(blocks+[partial])`, which is the other reading of "(Σ full block sums + partial)"; see F2 |
| `variant:grouping_samples` | v2 averages over the n samples. This violates the CDR-010 grouping |
| `variant:predicate_v_positive` | v2 uses a `v > 0` predicate. This violates the CDR-010 predicate |
| `literal_numpy(r,deg)` | cumsum-difference block sums. This violates "block sums = direct summation" |
| `v1(r,deg)` | v2 delegates to v1. v2 is not implemented |

8. **"Exact decimal comparison" item**: `cases.*.exact_decimal` holds the decimal-exact result for every case. The fixtures agree 5/5. In the random battery 49/648 differ, all from decimal ties or decimal degeneracy. That is expected behaviour of the float contract, not a v2 defect. Report v2 against `exact_decimal` as information. The contract is fsum on binary64.
9. Self-tests of the harness (`selftest/*.json`):

| adapter | result |
|---|---|
| `self:primary` | 676/676 exact |
| `self:alt` | 676/676 exact |
| `pow_mutant` | caught in 27 cases (12 square-axis + 15 random t-bits) |
| `fsum_partial_mutant` | caught in 569 |
| `samples_mutant` | caught in 585 |
| `vpos_mutant` | caught in 10 |
| `v1` | caught in 634 |

## 4. Findings to route (facts, no decision taken)

- **F1. Squaring axis not pinned (CDR-010 gap).**
  - On glibc 2.39, Python `d**2` (libm pow) is not correctly rounded for about 0.085% of doubles: 2552 of 3,000,000 random doubles, and every one of the 2552 checked against the exact square. `d*d` and NumPy `arr**2` are correctly rounded (0 of 3,000,000 differ).
  - `run()` uses NumPy `**2`, so its squares are correctly rounded. v1 and the GIE-008c probe use Python `**2`.
  - Effect, over 106,509 random continuous cases plus this battery: T bits change in 43 of 106,509 cases and in 12/12 `E-SQUARE` cases, and t bits change in 741 of 106,509. r and p never changed.
  - An implementation that uses pow is libm-version dependent, so its T bits may not reproduce across platforms.
  - If v2 matches only `variant:square_pow`, report it as an unpinned-axis divergence for the Integration Writer to route. Do not silently PASS or FAIL it.
- **F2. "(Σ full block sums + partial)" has two readings.**
  - This oracle uses `fsum(full) + partial`. That matches the GIE-008 §2 "fsum / blocks" column cited by CDR-010, and the structure of `run()`.
  - The other reading, `fsum(full + [partial])`, changes p in 16/648 random cases and r/deg/ties in 21 cases. One of the 21 is the TIE fixture: ties go from 3 to 2 while p stays .45.
- **F3. Undefined and near-undefined statistic: the contract is silent.**
  - Literal `run()` returns the minimum p = 1/(B+1) whenever se is not > 0 (TS = nan), and also when cumsum residue makes lrv tiny (CONST-POS, 0102, 0307).
  - CDR-010 float arithmetic itself returns p = 1/20 with T ≈ 1.5e16 on `E-UNDEF-PERIOD3-L3`, where the exact lrv is 0 in both readings. v1 behaves the same way on that case.
  - Any guard would be a new threshold, so it would be USER_DECISION_REQUIRED (Track C owner/user). It is not part of this verification.
- **F4. v1 robustness (pre-existing, frozen, synthetic-only).**
  - `studentized_cbb` raises `ZeroDivisionError` when 0 < v and v/n underflows. All 10 `E-SUBNORMAL-*` cases hit this; their inputs are around 2^-540.
  - This fails closed by exception rather than by `MissingStatisticalEvidence`. v1 must stay unmodified (CDR-006). This is recorded only.
- **F5. Exact arithmetic is not a neutral referee.** Exact-decimal and exact-binary readings disagree with each other on CE4 and SEED275, and in the random battery.

## 5. Files and regeneration

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src_b9e01a9/implementation/src ./venv/bin/python prove_c6.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src_b9e01a9/implementation/src ./venv/bin/python run_battery.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src_b9e01a9/implementation/src ./venv/bin/python compare_v2.py --adapter self:primary
```

- The battery is deterministic: two full runs gave identical output apart from `runtime_seconds`. It takes about 50 s on this box.
- `expected_cdr010.json` records the sha256 of the oracle files in `file_sha256`.
- The venv is `venv/` (Python 3.11.15; numpy 2.3.5, scipy 1.16.2, pytest 9.1.1).
- `src_b9e01a9/` is `git archive b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565 implementation/src`.

NOT_RUN:
- Python 3.12/3.13.
- Other NumPy versions for the literal `run()`.
- Any comparison against Codex v2, which does not exist yet; this is by design.
- Repository pytest suites, which this task does not require.
