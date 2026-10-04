"""CDR-010 synthetic arithmetic regressions, independent of production code.

The immutable hex trace tables were derived from the original run() formula
and cross-checked against the read-only GIE-008c global probe (fsum/blocks).
Only CASES fixture definitions are imported from the historical diagnostic.
No tolerance, rounding, real data, calibration default, or historical edit.
The production module is mandatory: a missing module fails collection.
"""

import ast
import hashlib
import inspect
import json
import math
from pathlib import Path

import pytest

from investment_system.evl.superiority_v2 import studentized_cbb
from tests import evl_c8_gsup_v2_oracle as O
from tools.gsup_mb_reduction_diagnostic import CASES


SEED275 = {"id": "OPERAND_SEED275", "delta": [.01, -.03, .04, -.01, -.01],
           "block_length": 2, "replicates": 19, "seed": 275}
UNDERFLOW = {"delta": [0., 0., 4e-162, 4e-162, 4e-162, 4e-160],
             "block_length": 1, "replicates": 19, "seed": 0}
FIXTURES = {case["id"]: {k: v for k, v in case.items() if k != "id"}
            for case in (*CASES, SEED275)}
CONTRACT = {"reducer": "MATH_FSUM", "replicate_aggregation": "BLOCK_GROUPING",
            "block_sums": "DIRECT", "degeneracy": "SQRT_V_OVER_N_GT_ZERO"}
TRACE_KEYS = ("replicate_mean", "variance", "se", "block_sums", "partial_sum",
              "statistic", "degenerate", "tie", "exceeds")
PUBLIC_KEYS = ("method", "n", "mean", "long_run_variance", "statistic",
               "exceedances", "degenerate_replicates", "replicates", "p_value",
               "draws", "indices_hash", "block_length", "seed", "one_sided",
               "variance_blocks", "ties", "arithmetic_contract", "traces")

# p, exceedances, degenerates, ties, q. These are synthetic evidence pins,
# never acceptance thresholds or a numeric configuration for real outcomes.
EXPECTED = {
    "CE2_BLOCKS_AND_DEGENERACY": (.05, 0, 1, 0, 2),
    "CE3_CONTROL": (.05, 0, 0, 0, 2),
    "CE4_DEGENERACY": (.10, 1, 1, 0, 2),
    "CE5_BLOCK_COUNT": (.30, 5, 0, 0, 3),
    "ARITHMETIC_NUMPY_FLIP": (.10, 1, 2, 0, 2),
    "ARITHMETIC_LEFT_SUM": (.35, 6, 1, 0, 2),
    "ARITHMETIC_TIE": (.45, 8, 2, 3, 2),
    "OPERAND_SEED275": (.55, 10, 2, 0, 2),
}
# Fingerprints cover every oracle field, including observed intermediates and
# every trace field, serialized as float.hex() strings (signed zero included).
EXACT_FINGERPRINTS = {
    "CE2_BLOCKS_AND_DEGENERACY": "088704be6d437abe06b94e65c7eb44d26b68dd239bf40d6bb5121458e09e7078",
    "CE3_CONTROL": "f154142a4d81b6f92d91061f6bd9ac36f2a9158d55db51f9fb6444a01c7473fe",
    "CE4_DEGENERACY": "4dbc24f777c32784849108efba9a4799c78825e1ac2cbb10242a4f345f01846c",
    "CE5_BLOCK_COUNT": "1ef39d093701406edde1c47c1ceb5854c4dca84cc10238a73c03f2acba782363",
    "ARITHMETIC_NUMPY_FLIP": "2e15bf582a637246537170abdc78e9e2486e5d2e6c247b14ea193552ebfe591a",
    "ARITHMETIC_LEFT_SUM": "bfbf7faf40a89f8a722d866e8cb52205e971344af9e34147ba5710eb9619e266",
    "ARITHMETIC_TIE": "72126df3321812ac9f0677a93d192491f6aafe44d35704ac8fd4874e4abd1b27",
    "OPERAND_SEED275": "e61ab6d07c64467aef66f32e9559ad644060e8bf5c6970fddad48d1bce7dadf3",
}


def exact(value):
    """Lossless float transport; list/tuple are equivalent API containers."""
    if type(value) is float:
        return value.hex()
    if isinstance(value, dict):
        return {key: exact(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact(item) for item in value]
    return value


def trace_pin(row):
    """Compact readable hex row containing all nine named trace fields."""
    assert set(row) == set(TRACE_KEYS)
    for key in ("replicate_mean", "variance", "se", "partial_sum"):
        assert type(row[key]) is float, key
    assert all(type(value) is float for value in row["block_sums"])
    assert row["statistic"] is None or type(row["statistic"]) is float
    assert all(type(row[key]) is bool for key in ("degenerate", "tie", "exceeds"))
    return "|".join((row["replicate_mean"].hex(), row["variance"].hex(),
                     row["se"].hex(), ",".join(value.hex() for value in row["block_sums"]),
                     row["partial_sum"].hex(),
                     "None" if row["statistic"] is None else row["statistic"].hex(),
                     "".join(str(int(row[key])) for key in ("degenerate", "tie", "exceeds"))))


@pytest.fixture(params=("oracle", "production"))
def engine(request):
    if request.param == "oracle":
        return O.oracle_studentized
    return studentized_cbb


def test_oracle_is_independent_and_has_no_numeric_defaults():
    source = Path(O.__file__).read_text()
    tree = ast.parse(source)
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            modules.append(node.module)
    assert set(modules) == {"hashlib", "json", "math", "random"}
    assert all(parameter.default is inspect.Parameter.empty
               for parameter in inspect.signature(O.oracle_studentized).parameters.values())
    assert len(CASES) == 9 and set(FIXTURES) == set(EXPECTED) | {
        "CE1_RUNNABILITY", "UNDEFINED_ORIGINAL"}


@pytest.mark.parametrize("case_id", tuple(EXPECTED))
def test_oracle_exact_fingerprints(case_id):
    output = O.oracle_studentized(**FIXTURES[case_id])
    wire = json.dumps(exact(output), sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(wire.encode()).hexdigest() == EXACT_FINGERPRINTS[case_id]


@pytest.mark.parametrize("case_id", tuple(EXPECTED))
def test_approved_results_and_every_trace_field_exact(engine, case_id):
    arguments = FIXTURES[case_id]
    output = engine(**arguments)
    oracle = O.oracle_studentized(**arguments)
    assert set(PUBLIC_KEYS) <= set(output)
    assert exact({key: output[key] for key in PUBLIC_KEYS}) == exact(
        {key: oracle[key] for key in PUBLIC_KEYS})
    assert output["method"] == "C8_GSUP_STUDENTIZED_CBB_v2"
    assert output["arithmetic_contract"] == CONTRACT
    assert (output["p_value"], output["exceedances"], output["degenerate_replicates"],
            output["ties"], output["variance_blocks"]) == EXPECTED[case_id]
    assert len(output["traces"]) == arguments["replicates"]
    assert [trace_pin(row) for row in output["traces"]] == GOLDEN_TRACES[case_id].splitlines()
    assert exact(output["draws"]) == exact([row["statistic"] for row in output["traces"]])
    assert output["p_value"] == (output["exceedances"] + 1) / (arguments["replicates"] + 1)
    for row in output["traces"]:
        if row["degenerate"]:
            assert row["statistic"] is None and not row["tie"] and not row["exceeds"]
        else:
            assert row["tie"] == (row["statistic"] == output["statistic"])
            assert row["exceeds"] == (row["statistic"] >= output["statistic"])


@pytest.mark.parametrize("case_id,reason", [
    ("CE1_RUNNABILITY", "fewer than two variance blocks"),
    ("UNDEFINED_ORIGINAL", "undefined original statistic"),
])
def test_all_original_not_run_cases_refuse_p_value(engine, case_id, reason):
    with pytest.raises(O.OracleNotRun, match=reason):
        O.oracle_studentized(**FIXTURES[case_id])
    with pytest.raises(ValueError):
        engine(**FIXTURES[case_id])


@pytest.mark.parametrize("delta,length", [([1., 2., 3.], 3), ([1., 2., 3., 4.], 2),
                                          ([1., 2.], 3), ([], 1), ([.01], 1)])
def test_insufficient_evidence(engine, delta, length):
    with pytest.raises(ValueError):
        engine(delta, block_length=length, replicates=19, seed=1)


@pytest.mark.parametrize("field,value", [
    ("seed", None), ("seed", True), ("seed", 275.), ("seed", "275"),
    ("delta", [0., math.nan, .01]), ("delta", [0., math.inf, .01]),
    ("delta", [0., -math.inf, .01]), ("delta", [0., True, .01]),
    ("delta", [0., ".01", .02]), ("block_length", True),
    ("block_length", 0), ("block_length", -1), ("block_length", 2.),
    ("replicates", True), ("replicates", 0), ("replicates", -1), ("replicates", 19.),
])
def test_explicit_seed_dimensions_and_finite_observations_required(engine, field, value):
    arguments = dict(FIXTURES["CE3_CONTROL"], **{field: value})
    with pytest.raises(ValueError):
        engine(**arguments)


def test_ce4_v1_counterexample_is_preserved(engine):
    # Historical code is only exercised here; the independent oracle never
    # imports it or borrows its reductions/index stream.
    from investment_system.evl import superiority as v1
    arguments = FIXTURES["CE4_DEGENERACY"]
    historical = v1.studentized_cbb(**arguments)
    current = engine(**arguments)
    assert (historical["method"], historical["p_value"], historical["exceedances"],
            historical["degenerate_replicates"]) == ("C8_GSUP_STUDENTIZED_CBB_v1", .15, 2, 1)
    assert (current["p_value"], current["exceedances"], current["degenerate_replicates"]) == (.10, 1, 1)
    assert current["indices_hash"] == historical["indices_hash"]
    assert exact(current["statistic"]) == exact(historical["statistic"])
    # The omitted degenerate is still in the fixed B+1 denominator.
    assert current["p_value"] != (current["exceedances"] + 1) / (
        current["replicates"] - current["degenerate_replicates"] + 1)


def test_seed275_grouped_mean_operand_is_not_flattened(engine):
    output = engine(**FIXTURES["OPERAND_SEED275"])
    indices = O.oracle_indices(5, 2, 19, 275)
    row = output["traces"][18]
    flat_mean = math.fsum(SEED275["delta"][i] for i in indices[18]) / 5
    assert flat_mean.hex() == "0x1.999999999999ap-61"
    assert row["replicate_mean"].hex() == "0x1.999999999999ap-60"
    assert row["replicate_mean"] == (math.fsum(row["block_sums"]) + row["partial_sum"]) / 5
    assert row["exceeds"] and not row["tie"]


@pytest.mark.parametrize("case_id", ["CE2_BLOCKS_AND_DEGENERACY", "CE5_BLOCK_COUNT"])
def test_divisible_n_last_full_length_block_stays_out_of_variance(engine, case_id):
    arguments = FIXTURES[case_id]
    output = engine(**arguments)
    n, length = len(arguments["delta"]), arguments["block_length"]
    assert n % length == 0 and output["variance_blocks"] == n // length - 1
    indices = O.oracle_indices(n, length, arguments["replicates"], arguments["seed"])
    for sample, row in zip(indices, output["traces"]):
        assert len(row["block_sums"]) == n // length - 1
        assert row["partial_sum"].hex() == math.fsum(
            arguments["delta"][i] for i in sample[-length:]).hex()


def test_positive_variance_standard_error_underflow_is_degenerate(engine):
    output = engine(**UNDERFLOW)
    oracle = O.oracle_studentized(**UNDERFLOW)
    assert oracle["se"] > 0 and oracle["long_run_variance"] > 0
    assert exact({key: output[key] for key in PUBLIC_KEYS}) == exact(
        {key: oracle[key] for key in PUBLIC_KEYS})
    assert [trace_pin(row) for row in output["traces"]] == GOLDEN_TRACES["SE_UNDERFLOW"].splitlines()
    row = output["traces"][2]
    assert row["variance"].hex() == "0x0.0000000000001p-1022"
    assert row["variance"] > 0 and row["variance"] / len(UNDERFLOW["delta"]) == 0
    assert row["se"].hex() == "0x0.0p+0"
    assert row["degenerate"] and row["statistic"] is None
    assert not row["tie"] and not row["exceeds"]
    assert (output["exceedances"], output["degenerate_replicates"], output["p_value"]) == (1, 9, .10)


def test_frozen_c6_stream_exact_grid_and_no_global_rng_side_effect():
    import random
    from investment_system.evl.statistical_kernels import circular_block_indices
    before = random.getstate()
    for n in (2, 4, 5, 6, 8, 9, 12):
        for length in range(1, n + 1):
            for seed in (-2, 0, 1, 46, 275):
                expected = O.oracle_indices(n, length, 19, seed)
                assert expected == circular_block_indices(
                    n=n, block_length=length, replicates=19, seed=seed)
    assert random.getstate() == before


def test_explicit_zero_and_negative_seeds_are_deterministic(engine):
    arguments = FIXTURES["CE3_CONTROL"]
    for seed in (0, -2):
        supplied = dict(arguments, seed=seed)
        first = engine(**supplied)
        assert exact(first) == exact(engine(**supplied))
        assert first["indices_hash"] == O.oracle_studentized(**supplied)["indices_hash"]


# Immutable full-trace pins follow. Column order:
# replicate_mean|variance|se|comma-separated block_sums|partial_sum|statistic|DTE
# DTE is the exact degenerate/tie/exceeds boolean triple; None means no statistic.
# Source: independently instrumented GIE-008c mb_scalar(fsum, blocks), checked
# against this oracle before freezing. No test regenerates these expectations.
GOLDEN_TRACES = {
    'CE2_BLOCKS_AND_DEGENERACY': """\
0x1.1111111111111p-7|0x1.d208a5a912e32p-17|0x1.8ed6e2933ef92p-10|0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-6|0x1.47ae147ae147ap-6|-0x1.186f174f88473p+1|000
0x1.47ae147ae147bp-7|0x1.a36e2eb1c432ap-16|0x1.0b8cb28fd8cf4p-9|0x1.eb851eb851eb8p-6,0x1.47ae147ae147ap-6|0x1.47ae147ae147bp-7|-0x1.a20bd700c2c40p-1|000
0x1.7e4b17e4b17e5p-7|0x1.74d3b7ba75829p-14|0x1.f87f11a8fb365p-9|0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-7|0x1.999999999999ap-5|0x0.0p+0|000
0x1.b4e81b4e81b4dp-8|0x1.74d3b7ba7581dp-18|0x1.f87f11a8fb35cp-11|0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-7|0x1.47ae147ae147ap-6|-0x1.4c8dc2e423987p+2|000
0x1.b4e81b4e81b4fp-8|0x1.d208a5a912e2ap-17|0x1.8ed6e2933ef8ep-10|0x1.47ae147ae147bp-7,0x1.47ae147ae147ap-6|0x1.47ae147ae147bp-7|-0x1.a4a6a2f74c6afp+1|000
0x1.1111111111111p-7|0x1.d208a5a912e32p-17|0x1.8ed6e2933ef92p-10|0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-6|0x1.47ae147ae147ap-6|-0x1.186f174f88473p+1|000
0x1.eb851eb851eb8p-7|0x1.a36e2eb1c432dp-13|0x1.7a5f4d3ebc68bp-8|0x1.999999999999ap-5,0x1.47ae147ae147bp-7|0x1.eb851eb851eb8p-6|0x1.279a74590331ap-1|000
0x1.b4e81b4e81b4fp-7|0x1.af14cc6f97df0p-13|0x1.7f97690fb688ap-8|0x1.999999999999ap-5,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-6|0x1.2394d27497b92p-2|000
0x1.7e4b17e4b17e4p-7|0x1.d208a5a912e34p-17|0x1.8ed6e2933ef93p-10|0x1.47ae147ae147ap-6,0x1.eb851eb851eb8p-6|0x1.47ae147ae147ap-6|-0x1.48a22f5133b35p-50|000
0x1.eb851eb851eb8p-7|0x1.a36e2eb1c4330p-15|0x1.7a5f4d3ebc68cp-9|0x1.47ae147ae147ap-6,0x1.47ae147ae147ap-6|0x1.999999999999ap-5|0x1.279a74590331ap+0|000
0x1.1111111111111p-7|0x1.74d3b7ba75824p-18|0x1.f87f11a8fb361p-11|0x1.47ae147ae147bp-6,0x1.47ae147ae147ap-6|0x1.47ae147ae147bp-7|-0x1.bb67ae8584caep+1|000
0x1.7e4b17e4b17e5p-7|0x1.d208a5a912e33p-13|0x1.8ed6e2933ef92p-8|0x1.999999999999ap-5,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-7|0x0.0p+0|000
0x1.eb851eb851eb9p-7|0x1.0624dd2f1a9fdp-13|0x1.2b2129ee6f3aep-8|0x1.999999999999ap-5,0x1.47ae147ae147ap-6|0x1.47ae147ae147bp-6|0x1.75e9746a0b099p-1|000
0x1.47ae147ae147bp-8|0x0.0p+0|0x0.0p+0|0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-7|None|100
0x1.47ae147ae147bp-7|0x1.a36e2eb1c432dp-16|0x1.0b8cb28fd8cf5p-9|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-7|0x1.eb851eb851eb8p-6|-0x1.a20bd700c2c3fp-1|000
0x1.7e4b17e4b17e5p-7|0x1.d208a5a912e33p-13|0x1.8ed6e2933ef92p-8|0x1.47ae147ae147bp-7,0x1.999999999999ap-5|0x1.47ae147ae147bp-7|0x0.0p+0|000
0x1.47ae147ae147bp-7|0x1.a36e2eb1c432cp-15|0x1.7a5f4d3ebc68ap-9|0x1.47ae147ae147bp-7,0x1.eb851eb851eb8p-6|0x1.47ae147ae147ap-6|-0x1.279a74590331ep-1|000
0x1.b4e81b4e81b4fp-7|0x1.51dfde80fa7e6p-14|0x1.e044279bca11ap-9|0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-6|0x1.999999999999ap-5|0x1.d1c6831a662dcp-2|000
0x1.b4e81b4e81b4fp-7|0x1.51dfde80fa7e7p-14|0x1.e044279bca11bp-9|0x1.47ae147ae147ap-6,0x1.47ae147ae147bp-7|0x1.999999999999ap-5|0x1.d1c6831a662dbp-2|000""",
    'CE3_CONTROL': """\
0x1.cac083126e97ap-7|0x1.57eed45e9185ep-14|0x1.09668be41ed00p-8|0x1.47ae147ae147bp-7,0x1.eb851eb851eb8p-6|0x1.eb851eb851eb8p-6|0x1.f9b7b195cd71fp-1|000
0x1.89374bc6a7efap-7|0x1.b43526527a207p-17|0x1.a6b1cab04e1ccp-10|0x1.eb851eb851eb8p-6,0x1.47ae147ae147ap-6|0x1.47ae147ae147bp-7|0x1.3d87675649727p+0|000
0x1.89374bc6a7efap-8|0x1.0c6f7a0b5ed8dp-19|0x1.4b96be9c2da2cp-11|0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-7|-0x1.94c583ada5b53p+2|000
0x1.0624dd2f1a9fcp-7|0x1.b43526527a202p-17|0x1.a6b1cab04e1cap-10|0x1.47ae147ae147bp-7,0x1.47ae147ae147ap-6|0x1.47ae147ae147bp-7|-0x1.3d87675649729p+0|000
0x1.0624dd2f1a9fcp-7|0x1.b43526527a202p-17|0x1.a6b1cab04e1cap-10|0x1.47ae147ae147ap-6,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-7|-0x1.3d87675649729p+0|000
0x1.89374bc6a7efap-7|0x1.b43526527a207p-17|0x1.a6b1cab04e1ccp-10|0x1.eb851eb851eb8p-6,0x1.47ae147ae147ap-6|0x1.47ae147ae147bp-7|0x1.3d87675649727p+0|000
0x1.0624dd2f1a9fcp-7|0x1.e68a0d349be8fp-15|0x1.be6a47014a5bdp-9|0x1.eb851eb851eb8p-6,0x1.47ae147ae147bp-7|0x0.0p+0|-0x1.2ca820ecbb2efp-1|000
0x1.0624dd2f1a9fbp-6|0x1.3660e51d25aa8p-15|0x1.648dec67aecafp-9|0x1.47ae147ae147ap-6,0x1.eb851eb851eb8p-6|0x1.eb851eb851eb8p-6|0x1.1a5289c8269e6p+1|000
0x1.0624dd2f1a9fbp-7|0x1.0c6f7a0b5ed8dp-17|0x1.4b96be9c2da2cp-10|0x1.47ae147ae147ap-6,0x1.47ae147ae147ap-6|0x0.0p+0|-0x1.94c583ada5b59p+0|000
0x1.0624dd2f1a9fbp-8|0x1.3660e51d25aabp-15|0x1.648dec67aecb1p-9|0x1.47ae147ae147ap-6,0x1.47ae147ae147bp-7|-0x1.47ae147ae147bp-7|-0x1.1a5289c8269e8p+1|000
0x1.89374bc6a7efap-8|0x1.1d3671ac14c62p-16|0x1.e35ea18adf7f6p-10|0x1.47ae147ae147bp-7,0x1.47ae147ae147ap-6|0x0.0p+0|-0x1.15abc5bd2feb1p+1|000
0x1.89374bc6a7efap-8|0x1.0c6f7a0b5ed8dp-19|0x1.4b96be9c2da2cp-11|0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-7|-0x1.94c583ada5b53p+2|000
0x1.89374bc6a7efap-7|0x1.e68a0d349be90p-15|0x1.be6a47014a5bdp-9|0x1.eb851eb851eb8p-6,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-6|0x1.2ca820ecbb2efp-1|000
0x1.89374bc6a7efap-8|0x1.0c6f7a0b5ed8dp-19|0x1.4b96be9c2da2cp-11|0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-7|-0x1.94c583ada5b53p+2|000
0x1.89374bc6a7efap-7|0x1.b43526527a207p-17|0x1.a6b1cab04e1ccp-10|0x1.eb851eb851eb8p-6,0x1.47ae147ae147ap-6|0x1.47ae147ae147bp-7|0x1.3d87675649727p+0|000
0x1.0624dd2f1a9fbp-7|0x1.bc98a222d5174p-15|0x1.aabd50d4c1a52p-9|0x1.eb851eb851eb8p-6,0x1.47ae147ae147ap-6|-0x1.47ae147ae147bp-7|-0x1.3a84e3b9c9e48p-1|000
0x1.cac083126e978p-7|0x1.1d3671ac14c66p-16|0x1.e35ea18adf7fap-10|0x1.eb851eb851eb8p-6,0x1.47ae147ae147ap-6|0x1.47ae147ae147bp-6|0x1.15abc5bd2feadp+1|000
0x1.0624dd2f1a9fcp-7|0x1.e68a0d349be8fp-15|0x1.be6a47014a5bdp-9|0x1.eb851eb851eb8p-6,0x1.47ae147ae147bp-7|0x0.0p+0|-0x1.2ca820ecbb2efp-1|000
0x1.89374bc6a7efap-7|0x1.e68a0d349be90p-15|0x1.be6a47014a5bdp-9|0x1.47ae147ae147bp-7,0x1.eb851eb851eb8p-6|0x1.47ae147ae147bp-6|0x1.2ca820ecbb2efp-1|000""",
    'CE4_DEGENERACY': """\
0x1.6f0068db8bac6p-10|0x1.4bdbcb98445a0p-11|0x1.70af95547edd3p-7|-0x1.78d4fdf3b645ap-6,0x1.78d4fdf3b645ap-5|-0x1.0624dd2f1a9fcp-6|-0x1.d027d3c92788dp-1|000
0x1.205bc01a36e2ep-6|0x1.270db5f61ba58p-11|0x1.5ba3f9b1e405fp-7|0x1.78d4fdf3b645ap-5,-0x1.6872b020c49bap-7|0x1.b22d0e5604189p-5|0x1.218fbb436fd07p-1|000
-0x1.a36e2eb1c432ap-12|0x1.5aa0b56cb3dd6p-12|0x1.0a70345600eeep-7|-0x1.78d4fdf3b645ap-6,0x1.cac083126e979p-6|-0x1.cac083126e979p-8|-0x1.79cf97c94afe6p+0|000
0x1.7c1bda5119ce0p-7|0x1.1ac9041563698p-11|0x1.54561a7e58eedp-7|-0x1.78d4fdf3b645ap-6,0x1.cac083126e979p-6|0x1.b22d0e5604189p-5|0x0.0p+0|000
0x1.41205bc01a36ep-7|0x1.27f3391d2d0c9p-15|0x1.5c2b14f0c9848p-9|0x1.cac083126e979p-6,0x1.cac083126e979p-6|-0x1.cac083126e979p-8|-0x1.5af270ddfbbfcp-1|000
0x1.f212d77318fc5p-7|0x1.95a8485e12afep-11|0x1.979fb896dd579p-7|0x1.78d4fdf3b645ap-5,-0x1.78d4fdf3b645ap-6|0x1.b22d0e5604189p-5|0x1.28577877ebfc4p-2|000
0x1.205bc01a36e2ep-6|0x1.c1f705db613a3p-12|0x1.2f911b8ed11f3p-7|0x1.cac083126e979p-6,0x1.374bc6a7ef9dbp-4|-0x1.0624dd2f1a9fcp-6|0x1.4b9a0d5e7e74ep-1|000
0x1.41205bc01a36ep-7|0x1.27f3391d2d0c9p-15|0x1.5c2b14f0c9848p-9|0x1.cac083126e979p-6,0x1.cac083126e979p-6|-0x1.cac083126e979p-8|-0x1.5af270ddfbbfcp-1|000
0x1.205bc01a36e2ep-6|0x1.c1f705db613a3p-12|0x1.2f911b8ed11f3p-7|0x1.cac083126e979p-6,0x1.374bc6a7ef9dbp-4|-0x1.0624dd2f1a9fcp-6|0x1.4b9a0d5e7e74ep-1|000
0x1.78d4fdf3b645ap-6|0x0.0p+0|0x0.0p+0|0x1.78d4fdf3b645ap-5,0x1.78d4fdf3b645ap-5|0x1.78d4fdf3b645ap-6|None|100
0x1.b71758e219652p-7|0x1.840e97f351460p-14|0x1.19e955db66c8fp-8|0x1.cac083126e979p-6,0x1.78d4fdf3b645ap-5|-0x1.cac083126e979p-8|0x1.ac7d2d747342dp-2|000
0x1.0624dd2f1a9fcp-7|0x1.2dfd694ccab3fp-14|0x1.f1621dea44742p-9|0x1.cac083126e979p-6,0x1.cac083126e979p-6|-0x1.0624dd2f1a9fcp-6|-0x1.e5b9d136c6d94p-1|000
0x1.0624dd2f1a9fcp-7|0x1.ab0856e696a26p-12|0x1.27bae5906fc1cp-7|-0x1.6872b020c49bap-7,0x1.78d4fdf3b645ap-5|0x1.47ae147ae147bp-8|-0x1.987789740cec8p-2|000
0x1.2d77318fc5048p-7|0x1.49c240d7b68acp-10|0x1.03dfcbecdab5bp-6|0x1.374bc6a7ef9dbp-4,-0x1.78d4fdf3b645ap-6|-0x1.cac083126e979p-8|-0x1.35e215f946966p-3|000
0x1.f212d77318fc6p-9|0x1.dd3d077265223p-12|0x1.38a1a6ae210cfp-7|-0x1.6872b020c49bap-7,0x1.78d4fdf3b645ap-5|-0x1.0624dd2f1a9fcp-6|-0x1.a2954f27a94a3p-1|000
0x1.7c1bda5119ce1p-7|0x1.035b7f2cb0e30p-10|0x1.ccf09d29d658ap-7|-0x1.6872b020c49bap-7,0x1.374bc6a7ef9dbp-4|-0x1.cac083126e979p-8|0x1.1c5bad585f342p-53|000
0x1.8fc504816f006p-7|0x1.b2dd8d6457184p-18|0x1.2a6e11f2f5df8p-10|0x1.cac083126e979p-6,0x1.cac083126e979p-6|0x1.47ae147ae147bp-8|0x1.0dd90273c3cddp-1|000
0x1.db22d0e560418p-6|0x1.53bd1676640a8p-13|0x1.7509966fb3572p-8|0x1.374bc6a7ef9dbp-4,0x1.374bc6a7ef9dbp-4|-0x1.cac083126e979p-8|0x1.874776c175846p+1|001
0x1.f212d77318fc5p-7|0x1.95a8485e12afep-11|0x1.979fb896dd579p-7|-0x1.78d4fdf3b645ap-6,0x1.78d4fdf3b645ap-5|0x1.b22d0e5604189p-5|0x1.28577877ebfc4p-2|000""",
    'CE5_BLOCK_COUNT': """\
0x1.0624dd2f1a9f0p-13|0x1.138e99d2ec126p-14|0x1.779cf4324904cp-9|-0x1.0624dd2f1aa00p-10,-0x1.16872b020c49cp-6,0x1.47ae147ae147bp-7|0x1.26e978d4fdf3bp-7|-0x1.6554692ebdda7p+0|000
0x1.4fdf3b645a1cap-7|0x1.ce6c093d96639p-15|0x1.5810624dd2f1bp-9|0x1.fbe76c8b43958p-6,0x1.fbe76c8b43958p-6,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-7|0x1.2aaaaaaaaaaa9p+1|001
0x1.5810624dd2f1ap-9|0x1.93b3a68b19a43p-17|0x1.417a2ff098dc3p-10|-0x1.0624dd2f1aa00p-10,0x1.47ae147ae147bp-7,0x1.0624dd2f1a9fcp-9|0x1.47ae147ae147bp-7|-0x1.3920926f55b8ap+0|000
0x1.26e978d4fdf3cp-9|0x1.f3a57eaa2a0a9p-14|0x1.f9c917aa5e619p-9|0x1.0624dd2f1a9fcp-9,0x1.fbe76c8b43958p-6,0x1.0624dd2f1a9fcp-9|-0x1.16872b020c49cp-6|-0x1.f18f2811d6cd4p-2|000
0x1.374bc6a7ef9dbp-8|0x1.90619addf5a25p-14|0x1.c4c39358f3cebp-9|0x1.26e978d4fdf3bp-7,-0x1.0624dd2f1aa00p-10,0x1.fbe76c8b43958p-6|-0x1.0624dd2f1aa00p-10|0x1.728d111e8fe3ap-3|000
0x1.a1cac083126e9p-7|0x1.d137dd2db4b5dp-15|0x1.591a49a37e436p-9|0x1.fbe76c8b43958p-6,0x1.fbe76c8b43958p-6,0x1.26e978d4fdf3bp-7|0x1.fbe76c8b43958p-6|0x1.a34e3ba2cff36p+1|001
0x1.70a3d70a3d70ap-8|0x1.4d940789613d3p-14|0x1.9d451c05c710bp-9|0x1.47ae147ae147bp-7,0x1.fbe76c8b43958p-6,0x1.0624dd2f1a9fcp-9|0x1.0624dd2f1a9fcp-9|0x1.e727b86b6660fp-2|000
0x1.26e978d4fdf3bp-7|0x1.84ac136076a9dp-16|0x1.be1826051a099p-10|0x1.6872b020c49bap-7,0x1.26e978d4fdf3bp-7,0x1.5810624dd2f1ap-6|0x1.fbe76c8b43958p-6|0x1.6eb05e376349ap+1|001
0x1.16872b020c49cp-8|0x1.15df6555c52e5p-15|0x1.0ab65284f9072p-9|0x1.5810624dd2f1ap-6,0x1.26e978d4fdf3bp-7,0x1.0624dd2f1a9fcp-9|0x1.0624dd2f1a9fcp-9|0x1.f73b05f60fd42p-5|000
-0x1.89374bc6a7efcp-12|0x1.8655193708aadp-15|0x1.3c1bfc0333cf4p-9|0x1.0624dd2f1a9fcp-9,-0x1.16872b020c49cp-6,0x1.0624dd2f1a9fcp-9|0x1.47ae147ae147bp-7|-0x1.ddaab7704b319p+0|000
0x1.3f7ced916872bp-8|0x1.43393ab430f4bp-15|0x1.1fa79abf4ca25p-9|-0x1.0624dd2f1aa00p-10,0x1.47ae147ae147bp-7,-0x1.0624dd2f1aa00p-10|0x1.fbe76c8b43958p-6|0x1.5df1e4be5e795p-2|000
0x1.26e978d4fdf3bp-7|0x1.78c9cea3f5cc5p-14|0x1.b738bad0150fep-9|0x1.fbe76c8b43958p-6,0x1.5810624dd2f1ap-6,-0x1.0624dd2f1aa00p-10|0x1.5810624dd2f1ap-6|0x1.746d3ceb3e445p+0|001
0x1.a9fbe76c8b43ap-9|0x1.971c10d7be985p-13|0x1.42d4d1db3a9edp-8|0x1.47ae147ae147bp-7,-0x1.16872b020c49cp-6,0x1.fbe76c8b43958p-6|0x1.0624dd2f1a9fcp-9|-0x1.6bc86b3d9747ap-3|000
0x1.89374bc6a7ef9p-10|0x1.530a217a5c75ep-14|0x1.a0a3a5a50919ep-9|0x1.26e978d4fdf3bp-7,0x1.47ae147ae147bp-7,-0x1.16872b020c49cp-6|0x1.47ae147ae147bp-7|-0x1.a6d04c8d959b7p-1|000
0x1.26e978d4fdf3bp-9|0x1.fb82c2bd7f521p-17|0x1.6872b020c49bbp-10|-0x1.0624dd2f1aa00p-10,0x1.47ae147ae147bp-7,-0x1.0624dd2f1aa00p-10|0x1.47ae147ae147bp-7|-0x1.5d1745d1745d2p+0|000
0x1.89374bc6a7ef6p-11|0x1.0fb65668c2614p-12|0x1.74fbc53b95523p-8|-0x1.16872b020c49cp-6,0x1.fbe76c8b43958p-6,-0x1.16872b020c49cp-6|0x1.26e978d4fdf3bp-7|-0x1.2f9f61c24934bp-1|000
0x1.fbe76c8b43958p-8|0x1.967f7a7b37f65p-15|0x1.4296b5f70b92ep-9|0x1.fbe76c8b43958p-6,0x1.5810624dd2f1ap-6,0x1.6872b020c49bap-7|-0x1.0624dd2f1aa00p-10|0x1.790ef9b9b7288p+0|001
0x1.1eb851eb851ebp-8|0x1.1cc100e6afccfp-13|0x1.0dfe9455a67d5p-8|-0x1.16872b020c49cp-6,0x1.47ae147ae147bp-7,0x1.5810624dd2f1ap-6|0x1.5810624dd2f1ap-6|0x1.f11ce7decdc8cp-5|000
0x1.47ae147ae147ap-8|0x1.fb82c2bd7f51dp-15|0x1.6872b020c49bap-9|-0x1.0624dd2f1aa00p-10,0x1.5810624dd2f1ap-6,0x1.5810624dd2f1ap-6|-0x1.0624dd2f1aa00p-10|0x1.45d1745d17457p-2|000""",
    'ARITHMETIC_NUMPY_FLIP': """\
0x1.eb851eb851eb8p-9|0x1.d0369d0369d03p-13|0x1.58bad21cceb2dp-8|-0x1.47ae147ae147bp-6,0x1.eb851eb851eb8p-6|0x1.47ae147ae147bp-6|-0x1.e6ad64dd600bap-3|000
0x1.47ae147ae147bp-9|0x1.b4e81b4e81b50p-15|0x1.4e6fdf33cf032p-9|0x1.47ae147ae147bp-7,-0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-6|-0x1.f5a7cecdb684ap-1|000
0x1.47ae147ae147bp-10|0x1.a59d6c455be31p-14|0x1.d09d5ed7847e8p-9|0x1.47ae147ae147bp-7,-0x1.47ae147ae147bp-6|0x1.47ae147ae147bp-6|-0x1.0ed31c177da54p+0|000
-0x1.47ae147ae147ap-10|0x1.08541ac2b2500p-14|0x1.6fe17585ca1d0p-9|0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-7|-0x1.eb851eb851eb8p-6|-0x1.1d081297ca9cep+1|000
0x1.1eb851eb851ecp-7|0x1.1bfd44f307825p-15|0x1.0da1b8ff6f992p-9|0x1.47ae147ae147bp-5,0x1.eb851eb851eb8p-6|0x0.0p+0|0x1.d2ab98cdcaff5p+0|001
0x1.47ae147ae147bp-7|0x0.0p+0|0x0.0p+0|0x1.eb851eb851eb8p-6,0x1.eb851eb851eb8p-6|0x1.47ae147ae147bp-6|None|100
0x1.47ae147ae147ap-8|0x1.2918b66895a3fp-13|0x1.13c8a8170bc24p-8|-0x1.47ae147ae147bp-7,0x1.eb851eb851eb8p-6|0x1.47ae147ae147bp-6|-0x1.db4554802fcb4p-53|000
0x1.47ae147ae147ap-10|0x1.b5ffba184d8d0p-13|0x1.4edad32df8bccp-8|-0x1.47ae147ae147bp-6,0x1.eb851eb851eb8p-6|0x0.0p+0|-0x1.77c5af0f3338cp-1|000
0x1.eb851eb851eb8p-8|0x1.2918b66895a3fp-15|0x1.13c8a8170bc24p-9|0x1.eb851eb851eb8p-6,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-6|0x1.302c5f0a5c072p+0|000
0x1.47ae147ae147cp-8|0x1.2918b66895a3fp-13|0x1.13c8a8170bc24p-8|0x1.eb851eb851eb8p-6,0x1.47ae147ae147bp-5|-0x1.eb851eb851eb8p-6|0x1.db4554802fcb4p-53|000
0x1.47ae147ae147ap-10|0x1.b5ffba184d8d0p-13|0x1.4edad32df8bccp-8|-0x1.47ae147ae147bp-6,0x1.eb851eb851eb8p-6|0x0.0p+0|-0x1.77c5af0f3338cp-1|000
0x1.47ae147ae147bp-7|0x0.0p+0|0x0.0p+0|0x1.eb851eb851eb8p-6,0x1.eb851eb851eb8p-6|0x1.47ae147ae147bp-6|None|100
0x1.9999999999999p-8|0x1.4d242e6bdc804p-13|0x1.2408d89940ba6p-8|-0x1.47ae147ae147bp-7,0x1.eb851eb851eb8p-6|0x1.eb851eb851eb8p-6|0x1.1f3f4229a0310p-2|000
0x1.47ae147ae147bp-8|0x1.5d867c3ece2a5p-15|0x1.2b2129ee6f3adp-9|0x1.eb851eb851eb8p-6,0x1.47ae147ae147bp-7|0x0.0p+0|0x0.0p+0|000
0x1.47ae147ae147bp-8|0x1.5d867c3ece2a5p-15|0x1.2b2129ee6f3adp-9|0x1.47ae147ae147bp-7,0x1.eb851eb851eb8p-6|0x0.0p+0|0x0.0p+0|000
0x1.47ae147ae147bp-8|0x1.434f9953b1e73p-12|0x1.96dc341887e52p-8|0x1.47ae147ae147bp-5,-0x1.47ae147ae147bp-6|0x1.47ae147ae147bp-6|0x0.0p+0|000
-0x1.47ae147ae147cp-10|0x1.9bc8d72d3149fp-13|0x1.44adfa0d25a42p-8|-0x1.47ae147ae147bp-7,0x1.eb851eb851eb8p-6|-0x1.eb851eb851eb8p-6|-0x1.42f50857c5b22p+0|000
0x1.47ae147ae147bp-10|0x1.a59d6c455be31p-14|0x1.d09d5ed7847e8p-9|0x1.47ae147ae147bp-7,-0x1.47ae147ae147bp-6|0x1.47ae147ae147bp-6|-0x1.0ed31c177da54p+0|000
-0x1.47ae147ae147bp-9|0x1.1111111111111p-12|0x1.75e9746a0b098p-8|-0x1.47ae147ae147bp-6,0x1.eb851eb851eb8p-6|-0x1.eb851eb851eb8p-6|-0x1.50854f2c3d223p+0|000""",
    'ARITHMETIC_LEFT_SUM': """\
0x1.23456789abcdfp-9|0x1.02e85c0898b71p-15|0x1.e573ac901e574p-10|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-6|-0x1.47ae147ae147bp-6|-0x1.3333333333333p+0|000
0x1.6c16c16c16c17p-8|0x1.b8249c75039d9p-16|0x1.bf90829d07d4fp-10|0x1.eb851eb851eb8p-6,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-7|0x1.4d3486e3064d4p-1|000
0x1.fdb97530eca85p-8|0x1.a89bca22940d8p-16|0x1.b79868c19be39p-10|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-5|0x1.47ae147ae147bp-7|0x1.fcde5430e6292p+0|001
0x1.6c16c16c16c17p-8|0x1.4b66dc33f6ad0p-20|0x1.845c8a0ce512bp-12|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-6|0x1.47ae147ae147bp-7|0x1.8000000000000p+1|001
0x1.fdb97530eca85p-8|0x1.a89bca22940d8p-16|0x1.b79868c19be39p-10|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-5|0x1.47ae147ae147bp-7|0x1.fcde5430e6292p+0|001
0x1.23456789abcdfp-9|0x1.02e85c0898b71p-15|0x1.e573ac901e574p-10|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-6|-0x1.47ae147ae147bp-6|-0x1.3333333333333p+0|000
0x1.fdb97530eca85p-8|0x1.a89bca22940d8p-16|0x1.b79868c19be39p-10|0x1.47ae147ae147bp-5,0x1.47ae147ae147bp-6|0x1.47ae147ae147bp-7|0x1.fcde5430e6292p+0|001
0x1.23456789abcdfp-8|0x1.12712e5b08472p-17|0x1.f3cda3385e1b4p-11|0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-6|0x1.47ae147ae147bp-7|0x0.0p+0|000
0x1.23456789abcdfp-8|0x1.12712e5b08472p-17|0x1.f3cda3385e1b4p-11|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-7|0x0.0p+0|000
0x1.fdb97530eca85p-8|0x1.a89bca22940d8p-16|0x1.b79868c19be39p-10|0x1.47ae147ae147bp-5,0x1.47ae147ae147bp-6|0x1.47ae147ae147bp-7|0x1.fcde5430e6292p+0|001
0x1.23456789abcdfp-10|0x1.d881a7f616b47p-15|0x1.47e79866b2057p-9|-0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-6|0x0.0p+0|-0x1.5519766c94cd2p+0|000
0x1.b4e81b4e81b4ep-9|0x1.af14cc6f97decp-14|0x1.baeee97c4ad31p-9|0x1.eb851eb851eb8p-6,-0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-7|-0x1.50b06a8fc6b72p-2|000
0x1.47ae147ae147bp-7|0x0.0p+0|0x0.0p+0|0x1.47ae147ae147bp-5,0x1.47ae147ae147bp-5|0x1.47ae147ae147bp-7|None|100
0x1.23456789abcdfp-10|0x1.d881a7f616b47p-15|0x1.47e79866b2057p-9|0x1.47ae147ae147bp-6,-0x1.47ae147ae147bp-7|0x0.0p+0|-0x1.5519766c94cd2p+0|000
0x1.23456789abcdfp-7|0x1.a89bca22940dbp-18|0x1.b79868c19be3ap-11|0x1.eb851eb851eb8p-6,0x1.47ae147ae147bp-5|0x1.47ae147ae147bp-7|0x1.533ee2cb441b8p+2|001
0x1.23456789abcdfp-9|0x1.f7934c9af5d4cp-15|0x1.52837384a9b8fp-9|-0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-6|0x1.47ae147ae147bp-7|-0x1.b88bd015c7d1dp-1|000
0x1.b4e81b4e81b4ep-8|0x1.d208a5a912e33p-16|0x1.cc8a41a0067e8p-10|0x1.47ae147ae147bp-5,0x1.47ae147ae147bp-6|0x0.0p+0|0x1.43d136248490dp+0|000
0x1.23456789abcdfp-8|0x1.4bb9b5eb03aa8p-13|0x1.12bf4179016e3p-8|0x1.47ae147ae147bp-5,-0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-7|0x0.0p+0|000
0x1.23456789abcdfp-8|0x1.4bb9b5eb03aa8p-13|0x1.12bf4179016e3p-8|-0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-5|0x1.47ae147ae147bp-7|0x0.0p+0|000""",
    'ARITHMETIC_TIE': """\
0x1.1111111111111p-7|0x1.d208a5a912e32p-17|0x1.8ed6e2933ef92p-10|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-7|0x1.47ae147ae147bp-6|0x1.5e8add236a58ep+2|001
-0x1.47ae147ae147bp-8|0x1.0624dd2f1a9fbp-13|0x1.2b2129ee6f3adp-8|-0x1.47ae147ae147bp-6,-0x1.eb851eb851eb8p-6|0x1.47ae147ae147bp-6|-0x1.186f174f88473p+0|000
-0x1.b4e81b4e81b4dp-10|0x1.74d3b7ba75827p-14|0x1.f87f11a8fb363p-9|0x1.47ae147ae147bp-7,0x1.47ae147ae147bp-7|-0x1.eb851eb851eb8p-6|-0x1.bb67ae8584ca9p-2|000
0x1.b4e81b4e81b50p-10|0x1.6c16c16c16c17p-12|0x1.f28c9b380eb76p-8|-0x1.eb851eb851eb8p-6,0x1.47ae147ae147bp-6|0x1.47ae147ae147bp-6|0x1.c0b1bee5a6d85p-3|001
0x1.b4e81b4e81b4dp-10|0x1.51dfde80fa7e4p-14|0x1.e044279bca119p-9|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-7|-0x1.47ae147ae147bp-6|0x1.d1c6831a662dap-2|001
0x1.b4e81b4e81b50p-10|0x1.23456789abcdfp-13|0x1.3b4f6b099d01ep-8|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-6|-0x1.eb851eb851eb8p-6|0x1.62b9586ad0a23p-2|001
-0x1.b4e81b4e81b4fp-8|0x1.d208a5a912e33p-15|0x1.8ed6e2933ef92p-9|-0x1.47ae147ae147bp-6,0x0.0p+0|-0x1.47ae147ae147bp-6|-0x1.186f174f88472p+1|000
0x1.47ae147ae147bp-7|0x0.0p+0|0x0.0p+0|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-6|0x1.47ae147ae147bp-6|None|100
0x0.0p+0|0x1.a36e2eb1c432dp-14|0x1.0b8cb28fd8cf5p-8|-0x1.47ae147ae147bp-6,0x0.0p+0|0x1.47ae147ae147bp-6|0x0.0p+0|011
-0x1.b4e81b4e81b4dp-10|0x1.23456789abce0p-13|0x1.3b4f6b099d01fp-8|0x0.0p+0,0x1.47ae147ae147bp-6|-0x1.eb851eb851eb8p-6|-0x1.62b9586ad0a20p-2|000
0x0.0p+0|0x1.0624dd2f1a9fcp-13|0x1.2b2129ee6f3adp-8|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-7|-0x1.eb851eb851eb8p-6|0x0.0p+0|011
0x1.b4e81b4e81b4fp-8|0x1.74d3b7ba75827p-16|0x1.f87f11a8fb363p-10|0x1.47ae147ae147bp-6,0x1.47ae147ae147bp-6|0x0.0p+0|0x1.bb67ae8584cabp+1|001
-0x1.eb851eb851eb8p-7|0x0.0p+0|0x0.0p+0|-0x1.eb851eb851eb8p-6,-0x1.eb851eb851eb8p-6|-0x1.eb851eb851eb8p-6|None|100
-0x1.b4e81b4e81b4fp-7|0x1.d208a5a912e31p-17|0x1.8ed6e2933ef92p-10|-0x1.eb851eb851eb8p-6,-0x1.47ae147ae147bp-6|-0x1.eb851eb851eb8p-6|-0x1.186f174f88472p+3|000
0x0.0p+0|0x1.a36e2eb1c432dp-14|0x1.0b8cb28fd8cf5p-8|0x0.0p+0,0x1.47ae147ae147bp-6|-0x1.47ae147ae147bp-6|0x0.0p+0|011
-0x1.b4e81b4e81b4dp-9|0x1.af14cc6f97deep-13|0x1.7f97690fb6889p-8|-0x1.eb851eb851eb8p-6,0x1.47ae147ae147bp-7|0x0.0p+0|-0x1.2394d27497b90p-1|000
-0x1.47ae147ae147bp-8|0x1.0624dd2f1a9fcp-12|0x1.a70876aee57c4p-8|0x1.47ae147ae147bp-6,-0x1.47ae147ae147bp-6|-0x1.eb851eb851eb8p-6|-0x1.8c97ef43f7248p-1|000
-0x1.b4e81b4e81b4dp-9|0x1.51dfde80fa7e4p-14|0x1.e044279bca119p-9|0x0.0p+0,0x1.47ae147ae147bp-7|-0x1.eb851eb851eb8p-6|-0x1.d1c6831a662dap-1|000
-0x1.b4e81b4e81b4fp-8|0x1.d208a5a912e33p-15|0x1.8ed6e2933ef92p-9|-0x1.47ae147ae147bp-6,0x0.0p+0|-0x1.47ae147ae147bp-6|-0x1.186f174f88472p+1|000""",
    'OPERAND_SEED275': """\
0x1.0624dd2f1a9fdp-8|0x1.bc98a222d5171p-13|0x1.aabd50d4c1a51p-8|-0x1.47ae147ae147ap-6,0x0.0p+0|0x1.47ae147ae147bp-5|0x1.3a84e3b9c9e45p-1|001
0x1.cac083126e97ap-7|0x1.9d2391d57ff9dp-13|0x1.9b5d9c4f8efc2p-8|0x0.0p+0,0x1.eb851eb851eb8p-6|0x1.47ae147ae147bp-5|0x1.1d7d454ade664p+1|001
0x1.0624dd2f1a9fdp-9|0x1.754b05b7cfe58p-13|0x1.87067e4ae15d8p-8|0x1.47ae147ae147cp-7,0x1.eb851eb851eb8p-6|-0x1.eb851eb851eb8p-6|0x1.573ede52451bdp-2|001
0x1.cac083126e97ap-7|0x1.9d2391d57ff9dp-13|0x1.9b5d9c4f8efc2p-8|0x0.0p+0,0x1.eb851eb851eb8p-6|0x1.47ae147ae147bp-5|0x1.1d7d454ade664p+1|001
-0x1.47ae147ae147bp-7|0x0.0p+0|0x0.0p+0|-0x1.47ae147ae147bp-6,-0x1.47ae147ae147bp-6|-0x1.47ae147ae147bp-7|None|100
-0x1.89374bc6a7efap-8|0x1.b43526527a206p-15|0x1.a6b1cab04e1cbp-9|0x0.0p+0,-0x1.47ae147ae147bp-6|-0x1.47ae147ae147bp-7|-0x1.dc4b1b016e2bcp+0|000
0x1.0624dd2f1a9fep-9|0x1.2dfd694ccab3fp-16|0x1.f1621dea44742p-10|0x1.47ae147ae147cp-7,0x1.47ae147ae147cp-7|-0x1.47ae147ae147bp-7|0x1.0dd90273c3ce3p+0|001
-0x1.89374bc6a7efap-8|0x1.b43526527a204p-15|0x1.a6b1cab04e1cbp-9|0x0.0p+0,-0x1.47ae147ae147ap-6|-0x1.47ae147ae147bp-7|-0x1.dc4b1b016e2bcp+0|000
0x1.0624dd2f1a9fcp-6|0x1.ffb480a5accd4p-14|0x1.43b9556aab801p-8|0x1.eb851eb851eb8p-6,0x1.47ae147ae147cp-7|0x1.47ae147ae147bp-5|0x1.9e9b00ce62fdcp+1|001
0x1.89374bc6a7efap-8|0x1.57eed45e9185cp-14|0x1.09668be41ecffp-8|0x1.47ae147ae147cp-7,0x1.eb851eb851eb8p-6|-0x1.47ae147ae147bp-7|0x1.7b49c5305a156p+0|001
-0x1.0624dd2f1a9fbp-8|0x1.eabbcb1cc9648p-14|0x1.3d0558043a959p-8|0x1.47ae147ae147cp-7,-0x1.47ae147ae147bp-6|-0x1.47ae147ae147bp-7|-0x1.a75f34730c988p-1|000
0x1.89374bc6a7efap-8|0x1.57eed45e9185cp-14|0x1.09668be41ecffp-8|0x1.47ae147ae147cp-7,0x1.eb851eb851eb8p-6|-0x1.47ae147ae147bp-7|0x1.7b49c5305a156p+0|001
-0x1.0624dd2f1a9fbp-7|0x1.6aceaaf35e310p-13|0x1.817e8b8f21b06p-8|-0x1.47ae147ae147ap-6,0x1.47ae147ae147cp-7|-0x1.eb851eb851eb8p-6|-0x1.5c2ba24d1c93dp+0|000
-0x1.47ae147ae147bp-7|0x0.0p+0|0x0.0p+0|-0x1.47ae147ae147bp-6,-0x1.47ae147ae147bp-6|-0x1.47ae147ae147bp-7|None|100
-0x1.89374bc6a7ef8p-8|0x1.0c6f7a0b5ed90p-15|0x1.4b96be9c2da2ep-9|-0x1.47ae147ae147ap-6,-0x1.47ae147ae147bp-6|0x1.47ae147ae147bp-7|-0x1.2f9422c23c47bp+1|000
0x1.47ae147ae147bp-7|0x1.0624dd2f1a9fcp-13|0x1.47ae147ae147bp-8|0x1.47ae147ae147cp-7,0x0.0p+0|0x1.47ae147ae147bp-5|0x1.0000000000000p+1|001
-0x1.0624dd2f1a9fcp-8|0x1.a048e043a2164p-12|0x1.23fc1950df13ap-7|-0x1.47ae147ae147bp-6,0x1.eb851eb851eb8p-6|-0x1.eb851eb851eb8p-6|-0x1.cbac7a64e0cd8p-2|000
-0x1.0624dd2f1a9fbp-7|0x1.6aceaaf35e310p-13|0x1.817e8b8f21b06p-8|-0x1.47ae147ae147ap-6,0x1.47ae147ae147cp-7|-0x1.eb851eb851eb8p-6|-0x1.5c2ba24d1c93dp+0|000
0x1.999999999999ap-60|0x1.a36e2eb1c432dp-13|0x1.9e7c6e43390b7p-8|-0x1.47ae147ae147ap-6,-0x1.47ae147ae147ap-6|0x1.47ae147ae147bp-5|0x1.7b792b72cb59ep-53|001""",
    'SE_UNDERFLOW': """\
0x1.7fe8457fb207cp-537|0x0.0p+0|0x0.0p+0|0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x0.0p+0,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537|0x1.ccb0536608d61p-537|None|100
0x1.7fe8457fb207cp-537|0x0.0p+0|0x0.0p+0|0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537|0x0.0p+0|None|100
0x1.ccb0536608d61p-538|0x0.0000000000001p-1022|0x0.0p+0|0x1.ccb0536608d61p-537,0x0.0p+0,0x1.ccb0536608d61p-537,0x0.0p+0,0x0.0p+0|0x1.ccb0536608d61p-537|None|100
0x1.f3145a59343d4p-533|0x0.0000000001413p-1022|0x1.d41ea0e98af91p-533|0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x1.67e9c127b6e74p-530,0x1.ccb0536608d61p-537,0x0.0p+0|0x1.ccb0536608d61p-537|0x1.4fea40e0699afp-7|000
0x1.e4aed7be03f68p-532|0x0.0000000001eb3p-1022|0x1.218d270d44d6ep-532|0x0.0p+0,0x1.67e9c127b6e74p-530,0x0.0p+0,0x1.67e9c127b6e74p-530,0x1.ccb0536608d61p-537|0x1.ccb0536608d61p-537|0x1.a40911a89c082p-1|000
0x1.7fe8457fb207cp-537|0x0.0p+0|0x0.0p+0|0x1.ccb0536608d61p-537,0x0.0p+0,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537|0x1.ccb0536608d61p-537|None|100
0x1.f3145a59343d4p-533|0x0.0000000001413p-1022|0x1.d41ea0e98af91p-533|0x1.67e9c127b6e74p-530,0x0.0p+0,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537|0x1.ccb0536608d61p-537|0x1.4fea40e0699afp-7|000
0x1.e97b589c69638p-533|0x0.000000000037dp-1022|0x1.869c1a85cc346p-534|0x1.ccb0536608d61p-537,0x0.0p+0,0x1.ccb0536608d61p-537,0x0.0p+0,0x0.0p+0|0x1.67e9c127b6e74p-530|-0x1.9292597962971p-6|000
0x1.6a500196e99dcp-531|0x0.0000000001f4bp-1022|0x1.244d1c64c7fd2p-532|0x1.ccb0536608d61p-537,0x1.67e9c127b6e74p-530,0x1.67e9c127b6e74p-530,0x1.67e9c127b6e74p-530,0x0.0p+0|0x1.ccb0536608d61p-537|0x1.a22f73898328bp+0|001
0x1.e715182d36ad0p-532|0x0.0000000001628p-1022|0x1.ebda87f068e4ep-533|0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x0.0p+0,0x1.67e9c127b6e74p-530,0x1.ccb0536608d61p-537|0x1.67e9c127b6e74p-530|0x1.f38a4c7eb8d30p-1|000
0x1.332037995b396p-539|0x0.0p+0|0x0.0p+0|0x0.0p+0,0x0.0p+0,0x1.ccb0536608d61p-537,0x0.0p+0,0x0.0p+0|0x0.0p+0|None|100
0x1.332037995b396p-537|0x0.0p+0|0x0.0p+0|0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x0.0p+0,0x0.0p+0,0x1.ccb0536608d61p-537|0x1.ccb0536608d61p-537|None|100
0x1.f3145a59343d4p-533|0x0.0000000000376p-1022|0x1.854bfb363dc39p-534|0x1.ccb0536608d61p-537,0x0.0p+0,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537|0x1.67e9c127b6e74p-530|0x1.93edeef755988p-6|000
0x1.332037995b396p-537|0x0.0p+0|0x0.0p+0|0x0.0p+0,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x0.0p+0|0x1.ccb0536608d61p-537|None|100
0x1.7fe8457fb207cp-537|0x0.0p+0|0x0.0p+0|0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x0.0p+0|0x1.ccb0536608d61p-537|None|100
0x1.332037995b396p-537|0x0.0p+0|0x0.0p+0|0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x1.ccb0536608d61p-537,0x0.0p+0,0x1.ccb0536608d61p-537|0x0.0p+0|None|100
0x1.e97b589c69638p-533|0x0.0000000001445p-1022|0x1.d692f95c389fdp-533|0x0.0p+0,0x0.0p+0,0x0.0p+0,0x1.ccb0536608d61p-537,0x1.67e9c127b6e74p-530|0x1.ccb0536608d61p-537|-0x1.4e29b6f6f71e3p-7|000
0x1.e4aed7be03f69p-533|0x0.0000000001449p-1022|0x1.d6d89689b3806p-533|0x1.ccb0536608d61p-537,0x0.0p+0,0x0.0p+0,0x1.67e9c127b6e74p-530,0x0.0p+0|0x0.0p+0|-0x1.4df84f2462c15p-6|000
0x1.e4aed7be03f68p-532|0x0.0000000001eb3p-1022|0x1.218d270d44d6ep-532|0x0.0p+0,0x0.0p+0,0x1.67e9c127b6e74p-530,0x1.ccb0536608d61p-537,0x1.67e9c127b6e74p-530|0x1.ccb0536608d61p-537|0x1.a40911a89c082p-1|000""",
}
