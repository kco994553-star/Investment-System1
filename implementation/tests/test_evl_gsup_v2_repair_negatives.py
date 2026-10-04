"""Independent-review repairs: unsupported range and false evidence acceptance."""
from copy import deepcopy

import pytest

from investment_system.evl import superiority as v1, superiority_v2 as v2
from investment_system.evl.statistical_kernels import MissingStatisticalEvidence
from investment_system.evl.walkforward import digest
from tests.test_evl_c8_gsup import bound
from tools import verify_gsup_v2_arithmetic as verifier


@pytest.mark.parametrize("delta", [
    [1e308] * 5,
    [1e200, -1e200, 0., 1e200, -1e200],
    [0., 0., 5e-162],
])
def test_finite_overflow_or_observed_se_underflow_has_no_p_value(delta):
    with pytest.raises(MissingStatisticalEvidence):
        v2.studentized_cbb(delta, block_length=1 if len(delta) == 3 else 2, replicates=1, seed=0)


@pytest.mark.parametrize("role,control", [
    ([1e308] * 5, [-1e308] * 5),
    ([1e200, -1e200, 0., 1e200, -1e200], [0.] * 5),
])
def test_unsupported_derived_arithmetic_becomes_per_cell_not_run(role, control):
    cohorts = {c: {"role": role, "controls": {k: control for k in v1.SUPPORTED_CONTROLS}}
               for c in v1.REQUIRED_COHORTS}
    data = {"dataset_role": "CAL_VERIFY", "dataset_id": "fixture-verify-1",
            "role_id": "cand-fixture-1", "synthetic": True, "cohorts": cohorts}
    s = bound(lambda _: data, verify_periods=5, block_rule={"kind": "FIXED", "block_length": 2},
              replicates=1, seed=0)
    s.update(schema=v2.METHOD, policy=v2.POLICY, verify_content_hash=digest(cohorts))
    result = v2._evaluate(s, data)
    assert len(result) == 8
    assert all(cell["status"] == "NOT_RUN" and "p_value" not in cell for cell in result.values())


@pytest.mark.parametrize("field", ["draws", "arithmetic_contract", "indices_hash", "traces", "method"])
def test_verifier_refuses_omitted_mandatory_result_fields(monkeypatch, field):
    original = v2.studentized_cbb
    def omit(*args, **kwargs):
        row = original(*args, **kwargs)
        row.pop(field)
        return row
    monkeypatch.setattr(verifier.v2, "studentized_cbb", omit)
    with pytest.raises(AssertionError, match="production result schema"):
        verifier.verify()


def test_verifier_refuses_unknown_fields_and_changed_arithmetic_contract(monkeypatch):
    original = v2.studentized_cbb
    def change(*args, **kwargs):
        row = original(*args, **kwargs)
        row["arithmetic_contract"] = {**row["arithmetic_contract"], "reducer": "BUILTIN_SUM"}
        return row
    monkeypatch.setattr(verifier.v2, "studentized_cbb", change)
    with pytest.raises(AssertionError, match="unapproved result arithmetic contract"):
        verifier.verify()
    def extra(*args, **kwargs):
        row = original(*args, **kwargs)
        return {**row, "unexpected_policy_default": 0}
    monkeypatch.setattr(verifier.v2, "studentized_cbb", extra)
    with pytest.raises(AssertionError, match="production result schema"):
        verifier.verify()
