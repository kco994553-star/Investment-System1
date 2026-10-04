"""Independent CDR-012 F1/F3 regressions with new immutable multiplication pins.

Synthetic only. Expected values come from the independent formula, never
production. Historical CDR-010 oracle/pins remain unchanged and available.
"""

import ast
import hashlib
import inspect
import json
import math
from pathlib import Path

import pytest

from investment_system.evl import superiority_v2 as v2
from investment_system.evl.statistical_kernels import MissingStatisticalEvidence
from tests import evl_c8_gsup_v2_cdr012_oracle as O
from tests import evl_c8_gsup_v2_oracle as H
from tools.gsup_mb_reduction_diagnostic import CASES


CONTRACT = {"reducer": "MATH_FSUM", "replicate_aggregation": "BLOCK_GROUPING",
            "block_sums": "DIRECT", "degeneracy": "SQRT_V_OVER_N_GT_ZERO",
            "squaring": "MULTIPLICATION", "all_degenerate": "NOT_RUN"}
PUBLIC_KEYS = ("method", "arithmetic_contract", "n", "mean", "long_run_variance",
               "statistic", "variance_blocks", "exceedances", "degenerate_replicates",
               "ties", "replicates", "p_value", "draws", "traces", "indices_hash",
               "block_length", "seed", "one_sided")
NEAR_TIE = {"delta": [8.7, 0., 0., 0., -2.9, 2.9, 2.9, 8.7, -2.9],
            "block_length": 2, "replicates": 19, "seed": 11}
ALL_7 = {"delta": [-.2, -.1] * 6, "block_length": 2, "replicates": 19, "seed": 7}
ALL_11 = {**ALL_7, "seed": 11}
UNDERFLOW = {"delta": [0., 0., 4e-162, 4e-162, 4e-162, 4e-160],
             "block_length": 1, "replicates": 19, "seed": 0}
ALL_UNDERFLOW = {**UNDERFLOW, "replicates": 1, "seed": 1}
FIXTURES = {case["id"]: {k: v for k, v in case.items() if k != "id"} for case in CASES}
FIXTURES.update({
    "F1_NEAR_TIE": NEAR_TIE,
    "OPERAND_SEED275": {"delta": [.01, -.03, .04, -.01, -.01],
                        "block_length": 2, "replicates": 19, "seed": 275},
    "CONSTANT_LITERAL_7": {"delta": [.05] * 12, "block_length": 2, "replicates": 19, "seed": 7},
    "CONSTANT_LITERAL_11": {"delta": [.05] * 12, "block_length": 2, "replicates": 19, "seed": 11},
    "SE_UNDERFLOW": UNDERFLOW,
})
# p, exceedances, degenerates, ties; evaluation fixtures, never real defaults.
EXPECTED = {
    "CE2_BLOCKS_AND_DEGENERACY": (.05, 0, 1, 0), "CE3_CONTROL": (.05, 0, 0, 0),
    "CE4_DEGENERACY": (.10, 1, 1, 0), "CE5_BLOCK_COUNT": (.30, 5, 0, 0),
    "ARITHMETIC_NUMPY_FLIP": (.10, 1, 2, 0), "ARITHMETIC_LEFT_SUM": (.35, 6, 1, 0),
    "ARITHMETIC_TIE": (.45, 8, 2, 3), "OPERAND_SEED275": (.55, 10, 2, 0),
    "F1_NEAR_TIE": (.15, 2, 0, 0), "CONSTANT_LITERAL_7": (.05, 0, 0, 0),
    "CONSTANT_LITERAL_11": (.05, 0, 0, 0), "SE_UNDERFLOW": (.10, 1, 9, 0),
}


def exact(value):
    if type(value) is float:
        return value.hex()
    if isinstance(value, dict):
        return {key: exact(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact(item) for item in value]
    return value


def fingerprint(value):
    wire = json.dumps(exact(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(wire.encode()).hexdigest()


def trace_pin(row):
    assert set(row) == {"replicate_mean", "variance", "se", "block_sums", "partial_sum",
                        "statistic", "degenerate", "tie", "exceeds"}
    assert all(type(row[k]) is bool for k in ("degenerate", "tie", "exceeds"))
    return "|".join((row["replicate_mean"].hex(), row["variance"].hex(), row["se"].hex(),
                     ",".join(v.hex() for v in row["block_sums"]), row["partial_sum"].hex(),
                     "None" if row["statistic"] is None else row["statistic"].hex(),
                     "".join(str(int(row[k])) for k in ("degenerate", "tie", "exceeds"))))


@pytest.fixture(params=("oracle", "production"))
def engine(request):
    return O.oracle_studentized if request.param == "oracle" else v2.studentized_cbb


def test_new_oracle_independence_multiplication_and_explicit_arguments():
    tree = ast.parse(Path(O.__file__).read_text())
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module)
        assert not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow))
        assert not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "round")
    assert set(modules) == {"hashlib", "json", "math", "random"}
    for function in (O.oracle_indices, O.oracle_studentized):
        assert all(p.default is inspect.Parameter.empty
                   for p in inspect.signature(function).parameters.values())
    assert O.ARITHMETIC_CONTRACT == CONTRACT


@pytest.mark.parametrize("case_id", tuple(EXPECTED))
def test_independently_fixed_multiplication_fingerprints(case_id):
    assert fingerprint(O.oracle_studentized(**FIXTURES[case_id])) == PINS[case_id]


@pytest.mark.parametrize("case_id", tuple(EXPECTED))
def test_production_matches_all_independent_fields_exact(engine, case_id):
    result = engine(**FIXTURES[case_id])
    oracle = O.oracle_studentized(**FIXTURES[case_id])
    assert set(PUBLIC_KEYS) <= set(result)
    assert exact({key: result[key] for key in PUBLIC_KEYS}) == exact(
        {key: oracle[key] for key in PUBLIC_KEYS})
    assert result["arithmetic_contract"] == CONTRACT
    assert (result["p_value"], result["exceedances"], result["degenerate_replicates"],
            result["ties"]) == EXPECTED[case_id]


def test_near_tie_multiplication_changes_the_inclusive_comparison(engine):
    result = engine(**NEAR_TIE)
    assert result["p_value"].hex() == "0x1.3333333333333p-3"
    assert result["long_run_variance"].hex() == "0x1.48eca8641fdb8p+3"
    assert result["statistic"].hex() == "0x1.cf1f15ba01c3ap+0"
    row = result["traces"][4]
    assert row["statistic"].hex() == "0x1.cf1f15ba01c38p+0"
    assert not row["tie"] and not row["exceeds"]
    assert [trace_pin(row) for row in result["traces"]] == NEAR_TIE_TRACES.splitlines()


@pytest.mark.parametrize("arguments,pin_id", [(ALL_7, "ALL_DEGENERATE_7"),
                                              (ALL_11, "ALL_DEGENERATE_11"),
                                              (ALL_UNDERFLOW, "ALL_SE_UNDERFLOW")])
def test_all_degenerate_has_no_p_value(engine, arguments, pin_id):
    with pytest.raises(O.OracleNotRun, match="all bootstrap replicates degenerate") as refusal:
        O.oracle_studentized(**arguments)
    evidence = refusal.value.evidence
    assert "p_value" not in evidence
    assert evidence["degenerate_replicates"] == arguments["replicates"]
    assert evidence["long_run_variance"] > 0
    assert all(row["degenerate"] and row["statistic"] is None and not row["exceeds"]
               for row in evidence["traces"])
    assert fingerprint(evidence) == NOT_RUN_PINS[pin_id]
    error = O.OracleNotRun if engine is O.oracle_studentized else MissingStatisticalEvidence
    with pytest.raises(error, match="degenerate"):
        engine(**arguments)


def test_partial_degeneracy_keeps_all_b_in_denominator(engine):
    result = engine(**FIXTURES["CE4_DEGENERACY"])
    assert (result["exceedances"], result["degenerate_replicates"], result["p_value"]) == (1, 1, .10)
    assert result["p_value"] == (1 + 1) / (19 + 1)
    assert result["p_value"] != (1 + 1) / (19 - 1 + 1)
    assert all(not row["exceeds"] for row in result["traces"] if row["degenerate"])


@pytest.mark.parametrize("seed", [7, 11])
def test_positive_constant_residue_is_literal_without_epsilon(engine, seed):
    args = FIXTURES[f"CONSTANT_LITERAL_{seed}"]
    result = engine(**args)
    historical = H.oracle_studentized(**args)
    assert result["long_run_variance"] > 0 and result["statistic"] > 0
    assert result["degenerate_replicates"] == 0 and result["p_value"] == .05
    assert exact(result["traces"]) == exact(historical["traces"])
    assert result["long_run_variance"].hex() == historical["long_run_variance"].hex()


@pytest.mark.parametrize("delta,length", [([0.] * 12, 2), ([1.] * 12, 2),
                                          ([0., 0., 5e-162], 1)])
def test_exact_zero_and_observed_se_underflow_refuse(engine, delta, length):
    with pytest.raises(ValueError):
        engine(delta, block_length=length, replicates=19, seed=7)


def test_positive_replicate_variance_zero_se_remains_degenerate(engine):
    result = engine(**UNDERFLOW)
    row = result["traces"][2]
    assert row["variance"].hex() == "0x0.0000000000001p-1022"
    assert row["variance"] > 0 and row["se"] == 0
    assert row["degenerate"] and row["statistic"] is None and not row["exceeds"]
    assert result["degenerate_replicates"] == 9 and result["p_value"] == .10


@pytest.mark.parametrize("field,value", [("seed", None), ("seed", True),
                                        ("delta", [0., math.nan, .01]),
                                        ("block_length", True), ("replicates", 0)])
def test_invalid_inputs_remain_refused(engine, field, value):
    args = {**FIXTURES["CE3_CONTROL"], field: value}
    with pytest.raises(ValueError):
        engine(**args)


def test_historical_oracle_is_byte_identical_and_separately_available():
    assert hashlib.sha256(Path(H.__file__).read_bytes()).hexdigest() == (
        "e2db7498b6819783ac5d977c34950078f632c4e4dbb2ddf973b26cace8a9c6f5")
    assert H.ARITHMETIC_CONTRACT == {k: CONTRACT[k] for k in (
        "reducer", "replicate_aggregation", "block_sums", "degeneracy")}
    # Original fixtures' numerical hex bits stay unchanged; the supplemented
    # metadata gets new fingerprints without repinning historical expectations.
    for name in EXPECTED:
        if name == "F1_NEAR_TIE":
            continue
        new, old = O.oracle_studentized(**FIXTURES[name]), H.oracle_studentized(**FIXTURES[name])
        for key in PUBLIC_KEYS:
            if key != "arithmetic_contract":
                assert exact(new[key]) == exact(old[key]), (name, key)


def test_frozen_rng_convention_preserved():
    from investment_system.evl.statistical_kernels import circular_block_indices
    for n, length in ((5, 2), (9, 2), (12, 2), (6, 1)):
        for seed in (-2, 0, 7, 11, 275):
            assert O.oracle_indices(n, length, 19, seed) == circular_block_indices(
                n=n, block_length=length, replicates=19, seed=seed)


@pytest.mark.parametrize("kind", ["missing", "tampered"])
def test_supplement_refuses_before_registration_or_outcome(tmp_path, monkeypatch, kind):
    from investment_system.evl.calibration_contracts import IntegrityFailure
    from tests.test_evl_gsup_v2_registry import fixture
    from tests.test_evl_gsup_identity_kernel_invariance import claims
    spec, authority, binding, provider, registry, _ = fixture(tmp_path)
    path = tmp_path / "untrusted-cdr012-approval.json"
    if kind == "tampered":
        path.write_bytes(v2.SUPPLEMENT_PATH.read_bytes() + b"\n")
    monkeypatch.setattr(v2, "SUPPLEMENT_PATH", path)
    with pytest.raises((IntegrityFailure, FileNotFoundError)):
        registry.register(spec, source_binding=binding)
    assert provider.calls == [] and claims(authority) == []
    assert not list(registry.root.iterdir())


class ExplicitSyntheticCells:
    """Zero role and explicit controls produce exact F3/literal-positive deltas."""

    def __init__(self, mixed):
        self.mixed, self.calls = mixed, []

    def __call__(self, dataset_id):
        from investment_system.evl import superiority as legacy
        self.calls.append(dataset_id)
        cohorts = {}
        first_cohort, first_control = legacy.REQUIRED_COHORTS[0], legacy.SUPPORTED_CONTROLS[0]
        for cohort in legacy.REQUIRED_COHORTS:
            controls = {}
            for control in legacy.SUPPORTED_CONTROLS:
                f3 = not self.mixed or (cohort == first_cohort and control == first_control)
                controls[control] = [.2, .1] * 6 if f3 else [-.05] * 12
            cohorts[cohort] = {"role": [0.] * 12, "controls": controls}
        return {"dataset_role": "CAL_VERIFY", "dataset_id": dataset_id,
                "role_id": "cand-fixture-1", "synthetic": True, "cohorts": cohorts}


@pytest.mark.parametrize("mixed,seed", [(False, 7), (False, 11), (True, 7), (True, 11)])
def test_actual_registry_f3_blocks_stat_pass_and_stays_consumed(tmp_path, mixed, seed):
    from investment_system.evl.calibration_contracts import IntegrityFailure
    from tests.test_evl_gsup_identity_kernel_invariance import (
        ACCESSED_AT, claims, feasibility, source_fixture,
    )
    numerical = ExplicitSyntheticCells(mixed)
    spec, authority, binding, provider, _ = source_fixture(tmp_path, numerical)
    spec = {**spec, "schema": v2.METHOD, "policy": v2.POLICY, "seed": seed}
    registry = v2.GsupV2Registry(tmp_path / "cdr012-attempt", authority)
    key = registry.register(spec, source_binding=binding)
    gate = feasibility(registry, key)
    assert gate["status"] == "FEASIBLE" and provider.calls == []
    result = registry.assess(key, provider, accessed_at=ACCESSED_AT)
    assert result["statistical_status"] == "NOT_RUN"
    cells = list(result["cells"].values())
    refused = [cell for cell in cells if cell["status"] == "NOT_RUN"]
    assert len(refused) == (1 if mixed else 8)
    assert all("p_value" not in cell and "degenerate" in cell["reason"] for cell in refused)
    if mixed:
        assert all(cell["status"] == "REJECT_H0" and cell["p_value"] == .05
                   for cell in cells if cell not in refused)
    assert result["official"] is False and result["promotion_authority"] is None
    assert result["real_holdout_eligible"] is False
    assert provider.calls == [spec["verify_dataset_id"]] and len(claims(authority)) == 1
    with pytest.raises(IntegrityFailure):
        registry.assess(key, provider, accessed_at=ACCESSED_AT)
    retry = v2.GsupV2Registry(tmp_path / "renamed-cdr012-attempt", authority)
    renamed = {**spec, "campaign_id": "renamed-campaign", "verify_dataset_id": "renamed-label"}
    other_key = retry.register(renamed, source_binding=binding)
    with pytest.raises(IntegrityFailure):
        feasibility(retry, other_key)
    assert provider.calls == [spec["verify_dataset_id"]] and len(claims(authority)) == 1


# Frozen from independent arithmetic, before any production-derived comparison.
# Full float.hex transport includes every observed intermediate and trace field.
PINS = {
    'CE2_BLOCKS_AND_DEGENERACY': '93b36dafe30cf8d367824114478ad1a9a3eb3541423e5cbcd00816f20a385ac6',
    'CE3_CONTROL': '4cf8fad70398583376870d6880ae13bfde753356771b1df574fdde782c6f3c96',
    'CE4_DEGENERACY': '41baf9841ad1e9ca5528d4941e3f6ab0e9bb4ced03852111281b6bf76483ef8f',
    'CE5_BLOCK_COUNT': '5ecfa4384a520d9a4720dd8bfcccf00a86c642cca0eeda6b850f17459ecc6581',
    'ARITHMETIC_NUMPY_FLIP': '2aa1c1ba095f7cfd6db5b88a7807e883232c81b0fa828c9e06472904a095064b',
    'ARITHMETIC_LEFT_SUM': '1600c28ab62ac5c360cb1d6d6824fc358c05fb88b391b66c386bceef145007bd',
    'ARITHMETIC_TIE': 'bd9e3b6ff4fa785980beeb41980909643537f7662b0b206aa283620f4ed9214c',
    'OPERAND_SEED275': '6d1c2212cbb78accfc1e1fca9f2e060219f3a0cf9548bbd10bed8dd73b1b6f49',
    'F1_NEAR_TIE': '96c7d7e1e4b64e3198d2b5cdefbd509217c55a48def2b0a8c39da813d1e0aeb6',
    'CONSTANT_LITERAL_7': '4973a029cc47d9f67b58b132d100b030a0b584773bb390f7fec9ae5249674721',
    'CONSTANT_LITERAL_11': 'd4344abe0f1872ee3a4ed45242be5aec860c0404c19c5c0c634544f9e7f24f60',
    'SE_UNDERFLOW': '3edd2612196b843dd4f3d8a09e991742f326da6442bbf72be0930d49da523b74',
}
NOT_RUN_PINS = {
    'ALL_DEGENERATE_7': '708578b3032d49bb5f6555a489cfa099ffe27c16a699b4ae266e8dcf98317371',
    'ALL_DEGENERATE_11': '8e4ffffb6297551ef86956dd861b71e2df93da4109db0e555205139388905df8',
    'ALL_SE_UNDERFLOW': '888584d4ab4340331c5bef06c36721da493546d68e364d68fbecf5790e9c4b2b',
}
NEAR_TIE_TRACES = """\
0x1.20b60b60b60b5p+1|0x1.a946ab2c1ed89p-1|0x1.3715c7dff5769p-2|0x1.7333333333332p+2,0x1.7333333333332p+2,0x1.7333333333332p+2,0x1.7333333333332p+2|-0x1.7333333333333p+1|0x1.0f876ccdf6cd6p+0|000
0x1.eeeeeeeeeeeecp-1|0x1.c802468acf132p+2|0x1.c78f4daa8c4b6p-1|-0x1.7333333333333p+1,0x0.0p+0,0x1.7333333333332p+2,0x1.7333333333332p+2|0x0.0p+0|-0x1.16203534757d5p+0|000
0x1.49f49f49f49f4p-1|0x1.95575b260d666p+1|0x1.2fb4de71b2dcfp-1|0x0.0p+0,0x1.7333333333332p+2,0x0.0p+0,0x0.0p+0|0x0.0p+0|-0x1.16203534757d4p+1|000
0x1.c5b05b05b05b0p+1|0x1.a44ad72a9a7c3p+1|0x1.3541c72acf78ep-1|0x1.7333333333332p+2,0x1.1666666666666p+3,0x1.7333333333333p+3,0x1.7333333333332p+2|0x0.0p+0|0x1.556aeabe3f979p+1|001
0x1.c5b05b05b05afp+1|0x1.c8d6e9e06522ap+2|0x1.c7f978281fc2dp-1|0x1.1666666666666p+3,0x1.7333333333332p+2,0x0.0p+0,0x1.1666666666666p+3|0x1.1666666666666p+3|0x1.cf1f15ba01c38p+0|000
0x1.49f49f49f49f4p+0|0x1.af81742e044c5p+3|0x1.395af1da73654p+0|-0x1.7333333333333p+1,-0x1.7333333333333p+1,0x1.1666666666666p+3,0x1.7333333333332p+2|0x1.7333333333333p+1|-0x1.0d8fd5840ee24p-1|000
0x1.49f49f49f49f1p-2|0x1.39248909fcb67p+3|0x1.0af0d5143547bp+0|0x1.7333333333332p+2,-0x1.7333333333333p+1,0x1.7333333333332p+2,-0x1.7333333333333p+1|-0x1.7333333333333p+1|-0x1.8b8a458a9136cp+0|000
0x1.eeeeeeeeeeeeep+0|0x1.6e4d5e6f80918p+2|0x1.984c9655f22b9p-1|0x1.7333333333332p+2,0x1.1666666666666p+3,0x0.0p+0,0x1.7333333333332p+2|-0x1.7333333333333p+1|0x0.0p+0|000
0x1.20b60b60b60b5p+1|0x1.72748f1b6edebp+3|0x1.2257dacd434c5p+0|0x1.7333333333333p+3,0x1.7333333333332p+2,0x0.0p+0,0x0.0p+0|0x1.7333333333333p+1|0x1.22ed44db22753p-2|000
0x1.49f49f49f49f4p+0|0x1.520fad1192853p+3|0x1.155bc3a55a2f3p+0|-0x1.7333333333333p+1,0x1.7333333333332p+2,0x0.0p+0,0x1.1666666666666p+3|0x0.0p+0|-0x1.308bf95505858p-1|000
0x1.9c71c71c71c72p+0|0x1.95575b260d667p+3|0x1.2fb4de71b2dcfp+0|0x0.0p+0,0x1.7333333333333p+3,0x0.0p+0,0x0.0p+0|0x1.7333333333333p+1|-0x1.16203534757d1p-2|000
0x1.9c71c71c71c71p+0|0x1.af81742e044c5p+3|0x1.395af1da73654p+0|0x0.0p+0,0x1.1666666666666p+3,0x1.1666666666666p+3,-0x1.7333333333333p+1|0x0.0p+0|-0x1.0d8fd5840ee24p-2|000
0x1.20b60b60b60b5p+2|0x1.7c6c371e77980p+1|0x1.263924de7742fp-1|0x1.1666666666666p+3,0x1.7333333333332p+2,0x1.7333333333333p+3,0x1.7333333333333p+3|0x1.7333333333333p+1|0x1.1f171baff0ff2p+2|001
0x1.49f49f49f49f4p-2|0x1.3fc9a3b6ad31ep+2|0x1.7d7ee184e2ba5p-1|0x0.0p+0,-0x1.7333333333333p+1,0x0.0p+0,0x1.7333333333333p+2|0x0.0p+0|-0x1.14c49ae59f53fp+1|000
0x1.7333333333333p+1|0x1.2ec28f5c28f5cp+3|0x1.067a60a4f71c1p+0|0x0.0p+0,0x1.7333333333333p+2,0x1.1666666666666p+3,0x1.7333333333333p+3|0x0.0p+0|0x1.e2b7dddfefa67p-1|000
0x1.9c71c71c71c71p+0|0x1.610329161f9adp+3|0x1.1b6ce2bec5d66p+0|0x0.0p+0,-0x1.7333333333333p+1,0x0.0p+0,0x1.1666666666666p+3|0x1.1666666666666p+3|-0x1.2a071c54b35ddp-2|000
0x1.eeeeeeeeeeeeep+0|0x1.a2a1907f6e5d2p+1|0x1.34a5293c0564bp-1|0x1.7333333333332p+2,0x1.7333333333332p+2,0x0.0p+0,0x1.7333333333332p+2|0x0.0p+0|0x0.0p+0|000
0x1.49f49f49f49f4p+0|0x1.cb54d3e12750fp+2|0x1.c93763b7c07a8p-1|0x1.7333333333332p+2,0x1.7333333333332p+2,-0x1.7333333333333p+1,0x0.0p+0|0x1.7333333333333p+1|-0x1.717da59ed2e04p-1|000
0x1.eeeeeeeeeeeeep+1|0x1.a2a1907f6e5d4p+3|0x1.34a5293c0564bp+0|0x1.7333333333333p+3,0x0.0p+0,0x1.7333333333333p+3,0x1.7333333333333p+3|0x0.0p+0|0x1.9a8365810363fp+0|000"""
