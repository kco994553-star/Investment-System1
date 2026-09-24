from datetime import datetime, timezone

from investment_system.validation.historical import oos_partition

def test_oos_partition_is_label_only():
    a = datetime(2024, 12, 31, tzinfo=timezone.utc)
    b = datetime(2025, 6, 30, tzinfo=timezone.utc)
    part = oos_partition([a, b])
    assert part["oos"] is False
    assert part["calibrated"] is False
    assert part["official_pass"] is False
    assert len(part["in_sample"]) == 1
    assert len(part["out_of_sample"]) == 1
