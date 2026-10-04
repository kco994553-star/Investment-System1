# prep-cdr012-oracle: independent CDR-012 expectations for Codex PR #31's next head

**Authority: none.** This is read-only integration prep by an agent working for the Primary Integration Writer (session `session_019znshzTYgyBnuuBmSxdPFN`).

- It is not a Track C approval and sets no acceptance threshold for Track C.
- It approves no numeric configuration, CAL_VERIFY, Holdout, C8 Freeze, publication/Official/LIVE or canonical merge.
- All inputs are synthetic and serve software validation only.
- No CAL_VERIFY, Holdout, real-provider or network data was read.
- No remote ref was written. No `codex/*` branch was touched. No repository path was patched.
- v2 at `e0b6d80` was read only to write the adapter and the registry probe.

This directory is a copy of `wf9/prep-v2-oracle` (the CDR-010 oracle). Every copied file is byte-identical to its source, with one exception: the old README was renamed to `README_prep-v2-oracle_CDR010.md`, byte-identical. New files carry `cdr012` in their names.

Routing: `origin/integration/global-handoff-v1` @ `1620f7118dbe91283cde1cc1431cdea236ab0829`, with the `COORDINATION_DECISION_REGISTER` entries CDR-010 and CDR-012 and the evidence GIE-010.

## 1. CDR-012 reference

`oracle_cdr012.mb_v2_cdr012(x, L, B, seed)` with its default arguments is the CDR-010 oracle default plus F3:

- **Unchanged from CDR-010:**
  - squaring is `d*d`;
  - sums use `math.fsum`;
  - replicate means use block grouping;
  - block sums are summed directly;
  - the replicate mean is `(fsum(full block sums) + partial)/n`;
  - a replicate is degenerate iff `not sqrt(v/n) > 0`;
  - ties count (`t >= T`);
  - `p = (r+1)/(B+1)`;
  - `se` not > 0 is `UNDEFINED_SE` and stays ungraded, as in CDR-010;
  - `q < 2` is `NOT_RUN_GEOMETRY`.
- **F1:** the squaring operator is pinned to `d*d`. The `square='pow'` path exists only as a negative mutant.
- **F3:** if `deg == B` (every replicate degenerate), the outcome class is **NOT_RUN**. There is no p and no r, so nothing can grade REJECT_H0. Nothing else changes:
  - `deg == B-1` still yields a p;
  - a near-undefined statistic whose replicates are not all degenerate keeps the CDR-010-literal p. Example: `[0.05]*12`, L=2, B=19, seed 7 gives T `0x1.f5a7cecdb684cp+53` (about +1.77e16), deg 0, p 1/20;
  - no epsilon, tolerance or threshold is added.
- **Second implementation.** `oracle_cdr012_alt.mb_v2_cdr012_alt` restates the same rule over `oracle_cdr010_alt`:
  - it emulates every IEEE operation as an exact rational followed by one rounding;
  - it decides degeneracy in Fractions;
  - it shares no code with the primary.
- **Agreement:** primary and alt are bit-identical on **752/752** cases. On STAT cases they agree on T, r, deg, ties, p, codes and every t bit. On NOT_RUN cases they agree on class, deg, T and codes. `build_expected_cdr012.py` aborts on any disagreement.

## 2. expected_cdr012.json (deterministic: two builds are identical apart from `runtime_seconds`)

| group | cases | expected class | graded replicates |
|---|---|---|---|
| fixtures (GIE-008 CE4/FLIP/LEFT_SUM/TIE/SEED275) | 5 | STAT | 95 |
| random | 648 | STAT | 69,992 |
| edge_subnormal | 10 | STAT | 190 |
| edge_square_axis (E-SQUARE-00..11) | 12 | STAT | 708 |
| edge_undefined | 6 | 1 STAT (E-UNDEF-PERIOD3-L3), 5 UNDEFINED_SE (ungraded) | 19 |
| **cdr012_f3_all_degenerate** | 37 | **NOT_RUN** | – |
| **cdr012_f3_boundary** (deg == B-1) | 17 | STAT | 106 |
| **cdr012_f1_square** (refuter p-flips) | 4 | STAT | 40 |
| **cdr012_near_undefined** | 13 | STAT | 749 |
| total | 752 | 710 STAT + 37 NOT_RUN graded; 5 ungraded | 71,899 |

**Re-grade of the 681-case CDR-010 battery:**
- 681 cases, of which 676 are graded under CDR-010 and 5 are UNDEFINED.
- **0 cases became NOT_RUN** (the most degenerate battery case is E-SUBNORMAL-04 at 9/19).
- **0 other changes**: status, T, r, deg, ties, p, codes, every t bit, the indices hash, mean, lrv and se are identical to `expected_cdr010.json` on all 681 cases.
- The alt is bit-identical on 681/681.

**F3 all-degenerate fixtures (37).** Each has CDR-010 status OK (se > 0) and `deg == B`. Each is asserted at build time.

- **GIE-010 reproducers:** `[-0.2,-0.1]*6`, L2, B19, at seeds 7 and 11.
  - CDR-010-literal result: p 1/20, deg 19, T `-0x1.783ddb1a48e38p+53`.
  - v2 at `e0b6d80` gives the same p .05.
- **Constant blocks** (period divides L), 5 cases:
  - positive mean: `[0.2,0.1]*6` L2 B99; `[0.1,0.7]*5` L2; `[0.3,0.6]*11` L6 B99; `[0.05,-0.02,0.01,0.03]*3` L4;
  - negative mean: `[-0.2,-0.1]*5` L4 B199 (n % L ≠ 0).
- **Constant series:**
  - 0.9 n9 L3; -0.9 n13 L5 B99; 0.45 n21 L5 B199; 0.11 n19 L5; -0.43 n23 L7;
  - B=1: 0.9 n9 L3 and -0.19 n11 L3;
  - scaled: 0.9·2^400 and -0.9·2^-400.
- **Rounding-induced** (exact lrv ≠ 0 and exact replicate v ≠ 0, but every float block sum is equal):
  - 0.9 n9 L3 with x[0] one ulp up, B19;
  - -0.9 n18 L6 with x[9] two ulps down, B99.
- **Seed-lucky with non-constant float blocks.** About 56% of start tuples give a degenerate replicate; the seed draws only degenerate ones. Same series, different seeds:

  | series | all-degenerate seeds | boundary seed (deg 18) |
  |---|---|---|
  | `POS9` (0.9·9, x[3] +16 ulp), L3, B19 | 4813 | 1960 |
  | `NEG14` (-0.47·14, x[0] -1 ulp), L5, B19 | 84181 | 10868 |
  | `NEG9`, B19 | 77127 | 7077 |
  | `POS9`, small B | B3 s0, B5 s27, B9 s280 | – |

- **Moderate T** (≈ ∓12.6): X5 = `[-0.2,-0.1,-0.2,-0.1,-0.2]` L2 at B1 s74, B2 s390 and B3 s38188; the positive mirror at B2 s390.
- **Zero mean, T == 0 exactly:**
  - `[0.1,-0.1,0.1,-0.1]` L1 at B1 s2, B2 s152, B3 s633 and B4 s2881;
  - dyadic `[0.5,-0.25,-0.25,0.5,-0.5]` L1, B2 s2766.
- **Subnormal underflow (4):** every replicate is degenerate because `v > 0` but `fl(v/n) == 0`. A `v > 0` predicate would miss them. The inputs are in `fixtures_subnormal_f3.json`.
- Coverage: B ∈ {1, 2, 3, 4, 5, 9, 19, 99, 199}; n 4..23; L 1..7.

**Boundary fixtures (17), deg == B-1, which must keep a p:**
- `POS9`, `NEG14` and `NEG9` at B19, with deg 18;
- `POS9` at B3, B5 and B9; `NEG14` at B9;
- X5 at B1 (deg 0), B2 and B3; the X5 mirror at B2;
- the zero-mean series at B1 (deg 0), B2, B3 and B4; the dyadic series at B2 and B3.

**F1 fixtures.** The detector set has 16 cases: the 12 E-SQUARE cases plus 4 refuter cases. Values verified by this oracle:

| case | `d*d` | pow |
|---|---|---|
| `[8.7,0,0,0,-2.9,2.9,2.9,8.7,-2.9]` L2 B19 s11 | **p 3/20 (.15)**, T `0x1.cf1f15ba01c3ap+0` | **4/20 (.20)**, T `…c38p+0`, one tie |
| `[0.3,0,0.8999999999999999,0.3,-0.3,0,-0.3,0.3,-0.3,0.3,0.3,0.3]` L3 B19 s13 | **2/20 (.10)** | **3/20 (.15)**; T identical, one replicate t changes and ties T |
| the same two series at B1 (s364, s1308) | 1/2 | 2/2 |

**Near-undefined fixtures (13), which must keep a p:**
- `[0.05]*12` L2 B19 s7: T ≈ +1.77e16, p .05, deg 0;
- the same at B1;
- `[-0.05]*12`; `[0.05]*6` L1; `[0.1]*6` L2 B99;
- `[-0.2,-0.1]*7` (n=14, no replicate degenerate);
- `[0.02,-0.01,0.05]*4` L3 B199; `[0.01,0.02]*9`; `[0.3,0.6]*5` B99; `[0.03,0.07]*6`;
- three mixed-degeneracy cases with 0 < deg < B-1: `POS9` B19 s0 (deg 11), `NEG14` B19 s0 (deg 12) and `POS9` B199 s3 (deg 106).
- E-UNDEF-PERIOD3-L3 from the battery is in the same detector set.

**Comparators on the 37 F3 cases (information):**
- Literal `run()` returns a p on all 37.
- The v1 kernel returns a p on 33 and raises `ZeroDivisionError` on the 4 subnormal cases.
- Exact-binary arithmetic calls the statistic undefined on the 16 exact-lrv-0 cases and is not all-degenerate on 10 others. CDR-010/012 mandate the float predicate, so the float result rules.

## 3. compare_cdr012.py and its self-tests

`compare_cdr012.py` treats NOT_RUN as an outcome class.

- **STAT cases:** the implementation must produce a statistic, with T.hex, r, deg, ties, p.hex and every per-replicate t bit and degenerate position identical. A missing `ties` or `draws` field is a mismatch unless `--allow-missing-*` is passed.
- **NOT_RUN cases:** it must return the mapped NOT_RUN class. Producing any p, or refusing in an unmapped way, is a mismatch.
- **UNDEFINED_SE cases:** reported only.
- The exit code is 0 only for `EXACT_MATCH_ALL_GRADED`.
- Each mismatch gets a triage tag (§5). Detector sets are reported as caught/total.

**Adapter (`adapters_cdr012.make_kernel_adapter`, CLI `--adapter v2kernel`), mapping configurable:**

| setting | default | meaning |
|---|---|---|
| `--v2-module` / `--v2-func` | `investment_system.evl.superiority_v2` / `studentized_cbb` | called as `f(list(x), block_length=L, replicates=B, seed=seed)` |
| `--not-run-exc` | `MissingStatisticalEvidence` | exception class names, matched against the raised exception's **MRO**, so a new subclass counts too → NOT_RUN |
| `--not-run-reason-regex` | none | if set, a mapped refusal counts as NOT_RUN only when its message matches, otherwise REFUSED_OTHER. Use it to insist the refusal is the all-degenerate one |
| `--not-run-result` | `status=NOT_RUN,outcome=NOT_RUN,statistical_status=NOT_RUN,outcome_class=NOT_RUN` | a returned dict with any of these items → NOT_RUN |
| p-value None | NOT_RUN (`--no-p-none-is-not-run` turns this off) | |
| result keys | `statistic, exceedances, degenerate_replicates, ties, p_value, draws` | the `e0b6d80` shape |

**Expected mapping.** Each of the following is right with the default flags:
- Codex raises `MissingStatisticalEvidence`, as `e0b6d80` already does for zero SE, which the registry turns into cell status NOT_RUN;
- Codex raises a subclass of it;
- Codex returns `status: NOT_RUN` / `p_value: None`.

If Codex uses a new, unrelated exception class, pass `--not-run-exc <Name>`. Record whichever mapping was used.

**Self-tests** (`selftest_cdr012/`, `SUMMARY.json`; these are the results of `run_selftests.sh <e0b6d80 extract> e0b6d80`):

| adapter | verdict | F1 16 | F3 37 | boundary 17 | near-undef 14 | triage |
|---|---|---|---|---|---|---|
| self:primary | EXACT_MATCH_ALL_GRADED (747) | 0 | 0 | 0 | 0 | – |
| self:alt | EXACT_MATCH_ALL_GRADED (747) | 0 | 0 | 0 | 0 | – |
| **v2 @ e0b6d80** | MISMATCH_IN_68 | **16/16** | **37/37** | 0 | 0 | F1_POW_SQUARING_SUSPECT 31 (12 E-SQUARE + 15 random t bits + 4 refuter), F3_MISSING_PRODUCED_P 37 |
| pow_mutant | MISMATCH_IN_31 | 16/16 | 0 | 0 | 0 | F1 31 |
| f3_off_mutant (CDR-010 literal) | MISMATCH_IN_37 | 0 | 37/37 | 0 | 0 | F3_MISSING 37 |
| pow_and_f3_off_mutant | MISMATCH_IN_68 | 16/16 | 37/37 | 0 | 0 | **its 68 rows equal v2@e0b6d80's row for row** |
| f3_broad_mutant (deg ≥ B-1) | MISMATCH_IN_20 | 2 (B1 refuter) | 0 | 17/17 | 1 (B1) | F3_OVERBROAD* 20 |
| f3_any_mutant (deg > 0) | MISMATCH_IN_119 | 1 | 0 | 15/17 | 3 | F3_OVERBROAD_SOME_DEGENERATE 101 + others |
| eps_abs_mutant (lrv < 2^-80 → NOT_RUN) | MISMATCH_IN_21 | 0 | 0 | 7/17 | 14/14 | EPSILON_GUARD_SUSPECT 13 + 8 |
| eps_rel_mutant (se < 2^-40·\|m\| → NOT_RUN) | MISMATCH_IN_21 | 0 | 0 | 7/17 | 14/14 | same |
| f3_p_one_mutant (all-degenerate → p = 1.0) | MISMATCH_IN_37 | 0 | 37/37 | 0 | 0 | F3_MISSING 37 |
| f3_exact_predicate_mutant (exact v == 0) | MISMATCH_IN_26 | 0 | 26/37 | 0 | 0 | F3_MISSING 26 |
| vpos_mutant (`v > 0` predicate) | MISMATCH_IN_14 | 0 | 4/37 (subnormal) | 0 | 0 | + 10 E-SUBNORMAL bit rows |
| v1 | MISMATCH_IN_747 | 16/16 | 37/37 | 17/17 | 14/14 | – |
| v2@e0b6d80 + in-memory F3 shim (raises MSE when deg == B) | MISMATCH_IN_31 | 16/16 | **0/37** | 0 | 0 | shows the default mapping works; only F1 remains |
| v2@e0b6d80 + in-memory epsilon shim | MISMATCH_IN_66 | 16/16 | 14/37 | 7/17 | 14/14 | |

On v2 at `e0b6d80`, the 5 UNDEFINED_SE cases (ungraded) raise `MissingStatisticalEvidence: zero standard error`, which maps to NOT_RUN.

## 4. Registry-level probe (registry_probe_cdr012.py)

**Coupling to Codex's code is small, and every element can be overridden or is discovered.** The probe relies on:
- the v2 module's `METHOD`, `POLICY` and `studentized_cbb`, plus its registry class (`GsupV2Registry`, otherwise the single `*Registry` class that has register and assess);
- the head's own synthetic identity fixture helpers (`tests.test_evl_gsup_identity_kernel_invariance.source_fixture/feasibility/ACCESSED_AT`), which Codex's v2 registry tests also use;
- `spec = {**spec, schema: v2.METHOD, policy: v2.POLICY}`, as those tests do;
- n, L, B, seed and alpha read from the head's spec. At `e0b6d80` these are 12, 2, 19, 7 and 0.2;
- planted series that are re-checked with the oracle at exactly those parameters. Constant-block series stay all-degenerate for any seed.

Every planted delta is checked to arrive exactly. The provider is synthetic; the head's `_evaluate` refuses anything else.

**Scenarios:**

| scenario | assertion |
|---|---|
| S1: all 8 cells are all-degenerate (`[-0.2,-0.1]*6` and `[0.2,0.1]*6`) | no REJECT_H0 and no STAT_PASS (statistical NOT_RUN expected) |
| S2: 7 strong-effect cells plus 1 all-degenerate cell | the F3 cell is not REJECT_H0, and the result is not STAT_PASS |
| S3 (control): all cells `[0.05]*12`, near-undefined but not all-degenerate | cells keep REJECT_H0 and the result stays STAT_PASS. CDR-012-literal: NOT_RUN here would be an unapproved guard |

**Run at e0b6d80** (`selftest_cdr012/registry_probe_e0b6d80.json`): `CDR012_DEVIATION`, exit 1. This reproduces GIE-010 F3 at registry level:
- **S1:** statistical_status **STAT_PASS**, and **8/8 cells REJECT_H0** at p .05, while the oracle says deg 19 == B in every cell. The four `[-0.2,-0.1]*6` cells have negative mean (T ≈ -1.32e16) and are still REJECT_H0 under the one-sided GREATER test.
- **S2:** **STAT_PASS**, with the F3 cell REJECT_H0 at p .05.
- **S3:** STAT_PASS, as expected under CDR-012.
- In every scenario: decision `NOT_RUN_EFFECT_FLOOR_DEFERRED`, official false, `SYNTHETIC_M_B_V2_ONLY`, 1 provider call.

**Self-test of the probe** with in-memory shims in `probe_selftest_shims.py`. These are wrappers around the head's own output, not a v2 implementation, and are not for any repository path:

| shim | result | scenarios |
|---|---|---|
| f3_kernel_raise | ALL_SCENARIOS_CDR012_EXPECTED, exit 0 | S1 NOT_RUN, S2 NOT_RUN, S3 STAT_PASS |
| f3_registry_only | exit 0 | the kernel would still fail compare_cdr012 (see §5) |
| eps_guard_kernel | CDR012_DEVIATION | S3 turns NOT_RUN |
| none | same as the plain run | |

**Limitation:** at the fixture parameters (n 12, L 2, B 19, seed 7), no deg == B-1 cell can be constructed. The best n=12/L=2 defect series reach a per-replicate degeneracy probability below 0.5 (`search/search_reg_boundary.py` found no candidate). The over-broad `deg >= B-1` rule is therefore covered only by the kernel compare (17/17).

## 5. Commands at Codex's new #31 head (run when it is HANDOFF_READY)

```bash
O=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf11/prep-cdr012-oracle/base
W=<your private scratch dir>
# 0. private clone only (never a worktree registered in /home/user/Investment-System1)
git clone --no-checkout --shared -q /home/user/Investment-System1 $W/repo
git -C $W/repo remote set-url origin https://github.com/kco994553-star/Investment-System1
git -C $W/repo fetch -q origin
H=$(git -C $W/repo ls-remote origin refs/pull/31/head | cut -f1); echo "#31 head $H"
git -C $W/repo cat-file -e "$H^{commit}" || git -C $W/repo fetch -q origin refs/pull/31/head
git -C $W/repo rev-parse "origin/codex/track-c-gsup-v2-2026-10-03"     # must equal $H
# 1. read-only extraction (src, tests, docs/codex_takeover, reports/track_c_c8* only; never data/gate_evidence;
#    refuses on any non-.py holdout/cal_verify file)
$O/extract_head.sh $W/repo "$H" $W/head31
# 2. source facts for F1/F3 (read-only)
grep -n -E '\*\* ?2|pow\(|math\.pow' $W/head31/implementation/src/investment_system/evl/superiority_v2.py   # F1: expect no hit in v2 arithmetic
grep -n -E 'degenerate|NOT_RUN|MissingStatisticalEvidence|raise ' $W/head31/implementation/src/investment_system/evl/superiority_v2.py
#    -> choose adapter flags (default fits MSE / MSE subclass / status NOT_RUN / p None)
# 3. kernel comparison (exit 0 required)
cd $O && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$O:$W/head31/implementation/src ./venv/bin/python compare_cdr012.py \
    --adapter v2kernel --out $W/cdr012_compare.json; echo rc=$?
#    optional strict F3 identity: add --not-run-reason-regex '<Codex F3 message regex>'
# 4. registry probe (exit 0 required)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$O:$W/head31/implementation/src:$W/head31/implementation ./venv/bin/python \
    registry_probe_cdr012.py --work $W/regprobe --out $W/cdr012_registry_probe.json; echo rc=$?
# 5. optional: whole self-test suite against the new head, written outside this directory
SELFTEST_OUT=$W/selftest SELFTEST_WORK=$W/st $O/run_selftests.sh $W/head31 head31
# 6. delete the private clone and extracts when done
rm -rf $W/repo $W/head31 $W/regprobe
```

Do not put `src_b9e01a9` on `PYTHONPATH` together with a head extract; both provide `investment_system`.

**Expected at a CDR-012-compliant head:**
- compare: `EXACT_MATCH_ALL_GRADED`, 747 graded (710 STAT bit-exact over 71,899 replicates, 37 NOT_RUN), detectors F1 0/16, F3 0/37, boundary 0/17 and near-undef 0/14, rc 0. The 5 UNDEFINED_SE cases are reported, not graded.
- registry probe: `ALL_SCENARIOS_CDR012_EXPECTED`, rc 0. S1 is NOT_RUN with 8 cells NOT_RUN. S2 is NOT_RUN with 1 NOT_RUN cell and 7 REJECT_H0. S3 is STAT_PASS.

**Status mapping (never convert FAIL/NOT_RUN to PASS):**

| item | PASS | FAIL | NOT_RUN |
|---|---|---|---|
| F1 | compare rc 0 with the F1 detectors at 0/16, and step 2 shows no `**2`/pow in v2 arithmetic | otherwise | – |
| F3 kernel | detector F3 0/37, boundary 0/17, near-undef 0/14 | otherwise | – |
| F3 registry | probe rc 0 | otherwise | the probe aborts with `API_CHANGED`: fix the overrides (`--registry-class`, `--fixture-module`, `--v2-module`) and rerun |

**Triage tags:**

| tag | meaning |
|---|---|
| `F1_POW_SQUARING_SUSPECT` | the result equals the oracle's pow variant |
| `F3_MISSING_PRODUCED_P` | a p was produced on an all-degenerate case. `matches_cdr010_literal` says whether it is the CDR-010 result |
| `F3_WRONG_REFUSAL_CLASS` | refused, but not as mapped NOT_RUN |
| `F3_OVERBROAD_DEG_EQ_B_MINUS_1`, `F3_OVERBROAD_SOME_DEGENERATE` | NOT_RUN although some replicates are not degenerate |
| `EPSILON_GUARD_SUSPECT_NEAR_UNDEFINED`, `F3_OVERBROAD_OR_EPSILON_GUARD` | NOT_RUN on a near-undefined case, which suggests an unapproved epsilon. These labels are heuristic; the grading is exact |
| `PER_REPLICATE_BITS_MISMATCH`, `ARITHMETIC_MISMATCH`, `UNEXPECTED_REFUSAL` | other differences |

**F3 implemented only in the registry:** the kernel compare reports `F3_MISSING_PRODUCED_P` 37 while the registry probe passes. Record F3-kernel as FAIL against this oracle's kernel expectation and F3-registry as PASS, and route the difference to the Primary Integration Writer. Do not merge the two into one PASS.

## 6. Files

| file | role |
|---|---|
| `oracle_cdr012.py`, `oracle_cdr012_alt.py` | CDR-012 thin wrappers (primary, alt) |
| `build_expected_cdr012.py` → `expected_cdr012.json` | battery re-grade + dedicated fixtures. The build asserts each fixture's construction and primary/alt identity. Run with `PYTHONPATH=.:src_b9e01a9/implementation/src` |
| `fixtures_subnormal_f3.json` | 4 subnormal underflow F3 inputs |
| `compare_cdr012.py`, `adapters_cdr012.py` | comparison harness, configurable adapter, built-in mutants |
| `registry_probe_cdr012.py`, `probe_selftest_shims.py` | registry probe and its in-memory self-test shims |
| `extract_head.sh`, `run_selftests.sh` | read-only head extraction; whole self-test suite |
| `selftest_cdr012/` | self-test outputs (`SUMMARY.json`) against `e0b6d80` |
| `search/` | the search scripts and raw outputs that located the fixtures (provenance only) |
| `SHA256SUMS` | sha256 of every file except `venv/`, `src_b9e01a9/` and itself |
| unchanged from wf9 | `oracle_cdr010*.py`, `expected_cdr010.json`, `compare_v2.py`, `run_battery.py`, `prove_c6.py`, `gie008c_*`, `sim_source_e112f41f.py`, `selftest/`, `src_b9e01a9/`, `venv/` |

Environment: Python 3.11.15, numpy 2.3.5, scipy 1.16.2 (copied venv), glibc 2.39.

NOT_RUN:
- Python 3.12/3.13.
- A comparison against Codex's next #31 head, which does not exist yet.
- Repository pytest suites.
- Actions.
- Cross-platform libm behaviour.
