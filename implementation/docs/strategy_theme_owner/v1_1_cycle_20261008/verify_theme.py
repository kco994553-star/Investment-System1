#!/usr/bin/env python3
"""Validate authored catalog and exact19 source-native identity assignments."""
from pathlib import Path
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SECURITY = ROOT / "implementation/docs/security_map19_owner/v1_1_cycle_20261008"
sys.path.insert(0, str(SECURITY))
from verify_mapping import require, verify


def main():
    document = json.loads((HERE / "CURRENT_TARGET_THEME_ASSIGNMENTS.json").read_text())
    mapping_bytes = (ROOT / document["identity_map_path"]).read_bytes()
    require(hashlib.sha256(mapping_bytes).hexdigest() == document["identity_map_sha256"], "identity-map hash mismatch")
    mapping = json.loads(mapping_bytes)
    verify(mapping)
    require(document["source_values_changed"] is False and document["economic_method_changed"] is False, "authored meaning changed")
    require(document["catalog_source_sha256"] == mapping["source_root_sha256"], "source-root hash mismatch")
    yaml = (ROOT / mapping["source_pins"]["target_v0"]["replay_path"]).read_text()
    expected = []
    for group in re.split(r"(?m)^  - theme_id: ", yaml)[1:]:
        expected.append((group.splitlines()[0].strip(), re.search(r"(?m)^    label: (.+)$", group).group(1).strip(),
                         int(re.search(r"(?m)^    target_units: (\d+)", group).group(1))))
    actual = [(t["theme_id"], t["label"], t["target_units"]) for t in document["catalog"]]
    require(actual == expected and len(actual) == 4, "user theme catalog changed")
    assignments = document["assignments"]
    require(len(assignments) == 19, "assignment set incomplete")
    require(len({json.dumps(a["security_ref"], sort_keys=True) for a in assignments}) == 19, "duplicate assigned security")
    for index, (assignment, row) in enumerate(zip(assignments, mapping["rows"])):
        require(assignment["row_index"] == row["row_index"] == index, "assignment row order changed")
        require(assignment["target_row_pointer"] == row["target_row_pointer"], "wrong source row")
        require(assignment["security_ref"] == row["security_ref"], "wrong security assignment")
        require(assignment["theme_id"] == row["target_row"]["theme_id"], "user theme membership changed")
        require(assignment["weight_units"] == row["target_row"]["weight_units"], "user weight changed")
        require(assignment["identity_map_sha256"] == document["identity_map_sha256"], "row map revision mismatch")
    for theme_id, _, units in expected:
        require(sum(a["weight_units"] for a in assignments if a["theme_id"] == theme_id) == units, "theme completeness mismatch")
    require(sum(a["weight_units"] for a in assignments) + document["cash_units"] == document["total_units"] == 10000,
            "full-portfolio completeness mismatch")
    require(document["assignment_available_at"] == mapping["mapping_available_at"] == document["assignment_mapping_effective_from"],
            "assignment availability changed")
    print(json.dumps({"status": "PASS", "source_catalog": "4/4", "security_reference_assignments": "19/19",
                      "source_units": 10000, "source_values_changed": False}, indent=2))


if __name__ == "__main__":
    main()
