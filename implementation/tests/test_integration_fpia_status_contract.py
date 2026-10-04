"""FPIA status contract: decision table, vocabulary, evidence classes, non-claims, determinism,
frozen tools on T recorded verbatim, full regression as a PASS conjunct, positive controls."""
import itertools
import json

import pytest

from tests import integration_fpia_testkit as tk
from tools.integration import track_c_fpia as fpia

ALL_PASS = {"authority": "PASS", "runtime_provenance": "PASS",
            "historical_frozen_identity": "HISTORICAL_FROZEN_IDENTITY_PRESERVED",
            "track_c_projection": "TRACK_C_PROJECTION_PRESERVED",
            "integration_interference": "INTEGRATION_INTERFERENCE_NONE", "v2_binding": "PASS",
            "full_regression": "PASS", "code_identity": "CODE_IDENTITY_SAME",
            "frozen_tools_on_T": "FROZEN_TOOLS_ON_T_PASS"}


def test_composition_table():
    # review rows: all conjuncts PASS + FROZEN_TOOLS_ON_T_FAIL + DIVERGED -> FPIA_PASS
    assert fpia.compose(dict(ALL_PASS, frozen_tools_on_T="FROZEN_TOOLS_ON_T_FAIL",
                             code_identity="CODE_IDENTITY_DIVERGED"))[0] == "FPIA_PASS"
    assert fpia.compose(dict(ALL_PASS, frozen_tools_on_T="NOT_RUN"))[0] == "FPIA_NOT_RUN"
    assert fpia.compose(dict(ALL_PASS, code_identity="NOT_RUN"))[0] == "FPIA_NOT_RUN"
    assert fpia.compose(dict(ALL_PASS, v2_binding="NOT_APPLICABLE"))[0] == "FPIA_PASS"
    # authority short-circuits
    assert fpia.compose(dict(ALL_PASS, authority="FAIL"))[0] == "FPIA_FAIL"
    assert fpia.compose(dict(ALL_PASS, authority="NOT_RUN"))[0] == "FPIA_NOT_RUN"
    assert fpia.compose(dict(ALL_PASS, authority="NOT_RUN", track_c_projection="TRACK_C_PROJECTION_NOT_PRESERVED"))[0] \
        == "FPIA_NOT_RUN"
    # full regression is a PASS conjunct (PIW ruling D3-A)
    assert fpia.compose(dict(ALL_PASS, full_regression="FAIL"))[0] == "FPIA_FAIL"
    assert fpia.compose(dict(ALL_PASS, full_regression="NOT_RUN"))[0] == "FPIA_NOT_RUN"
    # FAIL takes precedence over NOT_RUN once authority passed
    assert fpia.compose(dict(ALL_PASS, runtime_provenance="NOT_RUN",
                             integration_interference="INTEGRATION_INTERFERENCE_FOUND"))[0] == "FPIA_FAIL"
    # exhaustive table over conjunct values
    values = {"historical_frozen_identity": ["HISTORICAL_FROZEN_IDENTITY_PRESERVED", "HISTORICAL_FROZEN_IDENTITY_NOT_PRESERVED", "NOT_RUN"],
              "track_c_projection": ["TRACK_C_PROJECTION_PRESERVED", "TRACK_C_PROJECTION_NOT_PRESERVED", "NOT_RUN"],
              "integration_interference": ["INTEGRATION_INTERFERENCE_NONE", "INTEGRATION_INTERFERENCE_FOUND", "NOT_RUN"],
              "v2_binding": ["PASS", "NOT_APPLICABLE", "FAIL", "NOT_RUN"],
              "full_regression": ["PASS", "FAIL", "NOT_RUN"]}
    keys = sorted(values)
    for combo in itertools.product(*(values[k] for k in keys)):
        st = dict(ALL_PASS, **dict(zip(keys, combo)))
        status, _ = fpia.compose(st)
        failing = any(v in fpia.FAILING for v in combo)
        not_run = any(v == "NOT_RUN" for v in combo)
        expected = "FPIA_FAIL" if failing else ("FPIA_NOT_RUN" if not_run else "FPIA_PASS")
        assert status == expected, (st, status)


def test_exit_codes_and_vocabulary_closed():
    assert fpia.EXIT == {"FPIA_PASS": 0, "FPIA_FAIL": 1, "FPIA_NOT_RUN": 2}
    vocabulary = {"HISTORICAL_FROZEN_IDENTITY_PRESERVED", "HISTORICAL_FROZEN_IDENTITY_NOT_PRESERVED",
                  "CODE_IDENTITY_SAME", "CODE_IDENTITY_DIVERGED", "TRACK_C_PROJECTION_PRESERVED",
                  "TRACK_C_PROJECTION_NOT_PRESERVED", "INTEGRATION_INTERFERENCE_NONE",
                  "INTEGRATION_INTERFERENCE_FOUND", "FROZEN_TOOLS_ON_T_PASS", "FROZEN_TOOLS_ON_T_FAIL",
                  "FPIA_PASS", "FPIA_FAIL", "FPIA_NOT_RUN", "NOT_RUN", "PASS", "FAIL", "NOT_APPLICABLE"}
    assert fpia.FAILING | fpia.PASSING <= vocabulary


@pytest.fixture(scope="module")
def t0_result(tmp_path_factory):
    w = tk.base_world()
    return w.fpia(w.c["T0"])


def test_t0_end_to_end_pass_with_diverged_and_frozen_fail(t0_result):
    r = t0_result
    st = r["statuses"]
    assert r["fpia"]["status"] == "FPIA_PASS", r["fpia"]
    assert st["code_identity"] == "CODE_IDENTITY_DIVERGED"
    assert st["frozen_tools_on_T"] == "FROZEN_TOOLS_ON_T_FAIL"
    assert st["v2_binding"] == "PASS" and st["full_regression"] == "PASS"
    assert "CODE_IDENTITY_DIVERGED" in r["summary"] and "FROZEN_TOOLS_ON_T_FAIL" in r["summary"]
    assert r["code_identity"]["registration_binding"].startswith("PRIOR_TRACK_C_REGISTRATIONS_FAIL_CLOSED_ON_T")
    assert r["evidence_validity"].startswith("NON_DEFAULT_OPTIONS_NOT_EVIDENCE")


def test_vocabulary_closed(t0_result):
    text = json.dumps(t0_result)
    assert "IDENTITY_PRESERVED" not in text.replace("HISTORICAL_FROZEN_IDENTITY_PRESERVED", "")
    assert "CODE_IDENTITY_SAME" not in text


def test_equality_claim_sources(t0_result):
    claims = t0_result["equality_claims"]
    assert claims
    assert {c["source"] for c in claims} <= set(fpia.EVIDENCE_CLASSES)
    assert all(c["evidence_class"] == "COUNTERFACTUAL_CODE_IDENTITY_NORMALISED"
               for c in t0_result["integration_interference"]["counterfactual"] if "evidence_class" in c)
    for item in t0_result["integration_interference"]["computations_on_T"]:
        assert "INTEGRATED_TREE_RAW" in item["class"]


def test_frozen_tools_fail_recorded_verbatim(t0_result):
    ft = t0_result["frozen_tools_on_T"]
    assert ft["status"] == "FROZEN_TOOLS_ON_T_FAIL" and ft["evidence_class"] == "BRANCH_FROZEN_VALIDATION"
    tools = [s for s in ft["steps"] if s["kind"] == "tool"]
    assert tools and all(s["rc"] != 0 for s in tools)
    assert tools[0]["matched_tool_message"] == "new file outside authorized Track C: "
    assert ft["ci_first_failure"]
    assert any(s.get("deviation") for s in ft["steps"] if s["kind"] == "pytest")
    assert "PASS" not in json.dumps([s.get("matched_tool_message") for s in tools])


def test_non_claims_present(t0_result):
    assert t0_result["non_claims"] == fpia.NON_CLAIMS
    assert any("canonical-merge approval" in n for n in fpia.NON_CLAIMS)
    assert any("C8 Freeze" in n for n in fpia.NON_CLAIMS)
    assert t0_result["latent_policy_notes"] == fpia.LATENT_POLICY_NOTES and len(fpia.LATENT_POLICY_NOTES) == 5


def test_no_order_independence_claim(t0_result):
    assert "order-independ" not in json.dumps(t0_result).replace("no order-independence claim", "")
    assert t0_result["merge_result_audited"] == t0_result["subject"]["tree"]


def test_two_runs_identical_result_sha(tmp_path):
    w = tk.base_world()
    opts = {"lanes": ["R", "T", "PI"]}
    a = fpia.run_fpia(str(w.repo), w.c["T0"], w.c["G0"], tk.TEST_CDR, work_dir=str(tmp_path / "a"),
                      options=dict(opts, authority_remote=str(w.repo), require_clean_verifier=False))
    b = fpia.run_fpia(str(w.repo), w.c["T0"], w.c["G0"], tk.TEST_CDR, work_dir=str(tmp_path / "b"),
                      options=dict(opts, authority_remote=str(w.repo), require_clean_verifier=False))
    assert a["result_sha256"] == b["result_sha256"]
    assert a["result"] == b["result"]


def test_full_regression_failure_blocks_pass(tmp_path):
    w = tk.variant(tmp_path)
    T = w.git.change(w.c["T0"], {"implementation/tests/test_other_capability_broken.py":
                                 "def test_broken():\n    assert False\n"}, "foreign failing test")
    r = w.fpia(T, options={"lanes": ["T-full", "T", "V", "R"]})
    assert r["statuses"]["full_regression"] == "FAIL"
    assert r["fpia"]["status"] != "FPIA_PASS"


def test_deselecting_complement_interferer_rejected(tmp_path):
    # Deselection is not caller-controlled: the CLI has no deselect option, and the single
    # live-network node is honoured only while its file is byte-identical to R's.
    with pytest.raises(SystemExit):
        fpia.main(["--repo", ".", "--tree", "x", "--register-commit", "y", "--cdr", "z", "--out", "o",
                   "--deselect-non-track-c", "tests/x.py::t"])
    w = tk.variant(tmp_path)
    T = w.git.change(w.c["T0"], {tk.NETWORK_FILE: w.git.read(w.c["T0"], tk.NETWORK_FILE).decode()
                                 + "\n\ndef test_complement_interferer():\n    assert True\n"}, "edit network file")
    r = w.fpia(T, options={"lanes": ["T-full"]})
    assert r["full_regression"]["deselect_rule"]["valid"] is False
    assert r["statuses"]["full_regression"] == "NOT_RUN"
    assert r["fpia"]["status"] != "FPIA_PASS"


@pytest.mark.parametrize("control", ["PC1_merge_K_R", "PC3_merge_Kdocs_R"])
def test_positive_controls(tmp_path, control):
    w = tk.variant(tmp_path)
    K, R0 = w.c["K"], w.c["R0"]
    base = K if control == "PC1_merge_K_R" else w.git.change(K, {"docs-only/README.md": "docs\n"}, "K' docs only")
    T = w.git.merge(base, R0, "Track C landing")
    w.git.ref(tk.CANON_REF, T)          # live canonical has advanced to the landing commit
    G = w.register(R0, [], subjects=[T])
    r = w.fpia(T, G)
    assert r["fpia"]["status"] == "FPIA_PASS", r["fpia"]
    assert r["statuses"]["frozen_tools_on_T"] == "FROZEN_TOOLS_ON_T_FAIL"
    first = [s for s in r["frozen_tools_on_T"]["steps"] if s["kind"] == "tool"][0]
    assert first["matched_tool_message"] == "canonical advanced; fresh integration audit required"
    assert r["statuses"]["v2_binding"] == "NOT_APPLICABLE"
    assert r["track_c_projection"]["provenance"]["lineage_base"] == R0
