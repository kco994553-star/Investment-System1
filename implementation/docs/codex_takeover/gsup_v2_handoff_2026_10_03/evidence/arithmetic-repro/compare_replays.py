"""Compare stored evidence-only traces without executing any statistical method."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LABELS = ("cpython311_numpy235", "cpython312_numpy235", "cpython313_numpy224")
CANDIDATES = ("MATH_FSUM", "ACTUAL_PYTHON_BUILTIN_SUM", "PYTHON_311_LEFT_SUM_RECONSTRUCTION", "NUMPY_CUMULATIVE_2_3_5")


def differences(left, right, prefix=""):
    if type(left) != type(right):
        return [{"path": prefix, "left": left, "right": right}]
    if isinstance(left, dict):
        result = []
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                result.append({"path": prefix + "/" + key, "left": left.get(key), "right": right.get(key)})
            else:
                result.extend(differences(left[key], right[key], prefix + "/" + key))
        return result
    if isinstance(left, list):
        if len(left) != len(right):
            return [{"path": prefix + "/length", "left": len(left), "right": len(right)}]
        return [item for index, (a, b) in enumerate(zip(left, right))
                for item in differences(a, b, prefix + "/" + str(index))]
    return [] if left == right else [{"path": prefix, "left": left, "right": right}]


def reference(case, candidate):
    return next(item for item in case["references"] if item["candidate"] == candidate)


def canonical_payload(reference):
    return {key: value for key, value in reference["trace"].items() if key != "reduction"}


def main():
    data, process_pairs = {}, []
    for label in LABELS:
        paths = [ROOT / (label + "_process" + str(index) + ".json") for index in (1, 2)]
        raw = [path.read_bytes() for path in paths]
        assert raw[0] == raw[1]
        data[label] = json.loads(raw[0])
        assert data[label]["driver_sha256"] == hashlib.sha256((ROOT / "replay_arithmetic_candidates.py").read_bytes()).hexdigest()
        process_pairs.append({"runtime": label, "byte_identical": True,
                              "processes": [{"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(value).hexdigest()}
                                            for path, value in zip(paths, raw)],
                              "canonical_numeric_output_sha256": data[label]["canonical_numeric_output_sha256"]})
    source_bindings = data[LABELS[0]]["pinned_sources"]
    assert all(item["pinned_sources"] == source_bindings for item in data.values())
    index_hashes = {item["frozen_index_grid_sha256"] for item in data.values()}
    assert len(index_hashes) == 1
    runtime_comparisons = []
    for left_label, right_label in ((LABELS[0], LABELS[1]), (LABELS[0], LABELS[2]), (LABELS[1], LABELS[2])):
        for candidate in CANDIDATES:
            rows = []
            for left_case, right_case in zip(data[left_label]["cases"], data[right_label]["cases"]):
                assert left_case["fixture"] == right_case["fixture"] and left_case["indices_sha256"] == right_case["indices_sha256"]
                left, right = reference(left_case, candidate), reference(right_case, candidate)
                unsupported = any(item["summary"].get("reason") == "NUMPY_2_3_5_NOT_INSTALLED_FOR_THIS_RUNTIME" for item in (left, right))
                rows.append({"case": left_case["fixture"]["id"],
                             "status": "NOT_RUN_UNSUPPORTED_NUMPY_RUNTIME" if unsupported else "COMPARED",
                             "exact_numeric_payload_match": None if unsupported else left["numeric_payload_sha256"] == right["numeric_payload_sha256"],
                             "left_summary": left["summary"], "right_summary": right["summary"],
                             "summary_difference": None if unsupported else differences(left["summary"], right["summary"]),
                             "full_trace_differences": None if unsupported else differences(canonical_payload(left), canonical_payload(right))})
            runtime_comparisons.append({"left": left_label, "right": right_label, "candidate": candidate,
                                        "cases": rows, "exact_numeric_payload_matches": sum(row["exact_numeric_payload_match"] is True for row in rows),
                                        "compared_cases": sum(row["status"] == "COMPARED" for row in rows)})
    candidate_comparisons = []
    for label, evidence in data.items():
        for left_name, right_name in (("MATH_FSUM", "ACTUAL_PYTHON_BUILTIN_SUM"),
                                      ("MATH_FSUM", "NUMPY_CUMULATIVE_2_3_5"),
                                      ("ACTUAL_PYTHON_BUILTIN_SUM", "PYTHON_311_LEFT_SUM_RECONSTRUCTION")):
            rows = []
            for case in evidence["cases"]:
                left, right = reference(case, left_name), reference(case, right_name)
                unsupported = any(item["summary"].get("reason") == "NUMPY_2_3_5_NOT_INSTALLED_FOR_THIS_RUNTIME" for item in (left, right))
                rows.append({"case": case["fixture"]["id"], "status": "NOT_RUN_UNSUPPORTED_NUMPY_RUNTIME" if unsupported else "COMPARED",
                             "exact_numeric_payload_match": None if unsupported else left["numeric_payload_sha256"] == right["numeric_payload_sha256"],
                             "left_summary": left["summary"], "right_summary": right["summary"],
                             "summary_difference": None if unsupported else differences(left["summary"], right["summary"]),
                             "full_trace_differences": None if unsupported else differences(canonical_payload(left), canonical_payload(right))})
            candidate_comparisons.append({"runtime": label, "left": left_name, "right": right_name, "cases": rows})
    original_checks = {label: [{"case": case["fixture"]["id"], "check": case["pinned_original_mb_s_plus1_check"]}
                               for case in item["cases"]] for label, item in data.items()}
    output = {"status": "EVIDENCE_COMPLETE_NO_ARITHMETIC_SELECTION", "source_head": "675d0d298fbaab5b8473ed048a561ef84e2f3e78",
              "scope": "SYNTHETIC_SOFTWARE_VALIDATION_ONLY", "process_pairs": process_pairs,
              "fixtures_per_process": 9, "fresh_processes": 6,
              "pinned_sources": source_bindings, "frozen_index_grid_sha256": next(iter(index_hashes)),
              "frozen_index_grid_combinations_per_process": 176,
              "index_stream_semantics": "Read-only extracted exact Frozen C6 Python random.Random; independent stream equality confirmed for 44 n/L combinations x4 seeds and all9 fixed fixtures",
              "runtime_comparisons": runtime_comparisons, "candidate_comparisons": candidate_comparisons,
              "original_mb_source_checks": original_checks,
              "new_repository_tests": 0, "authoritative_v2_implemented": False, "selected_reduction": None,
              "full_regression": "NOT_RUN_BY_THIS_DIAGNOSTIC_WORKER",
              "GitHub_Actions": "NOT_RUN_BY_THIS_DIAGNOSTIC_WORKER",
              "safety": {"CAL_VERIFY_accesses": 0, "Holdout_consumptions": 0, "numeric_configuration_selected": False,
                         "C8_Freeze": False, "publication": False, "canonical_merge": False}}
    destination = ROOT / "COMPARISON_RESULTS.json"
    destination.write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": output["status"], "fresh_processes": 6, "fixtures": 9,
                      "process_pairs_byte_identical": "3/3", "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
