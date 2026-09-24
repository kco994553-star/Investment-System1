from datetime import datetime, timezone

from investment_system.providers.fred_csv import collect_indicators, parse_observations, yoy
from investment_system.validation.historical import live_macro

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)

CPI = """observation_date,CPIAUCSL
2024-08-01,314.0
2025-08-01,325.0
2026-08-01,330.0
"""

DGS = """DATE,DGS10
2026-09-10,4.10
2026-09-11,4.20
"""


def test_parse_and_yoy_from_csv_fixture():
    rows = parse_observations(CPI, "CPIAUCSL")
    assert abs(yoy(rows, AS_OF) - (330 / 325 - 1)) < 1e-9


def test_live_macro_from_fixtures_is_not_verified():
    pack = collect_indicators(
        AS_OF,
        {"CPIAUCSL": CPI, "DGS10": DGS, "INDPRO": CPI.replace("CPIAUCSL", "INDPRO"), "WALCL": DGS.replace("DGS10", "WALCL"), "BAMLH0A0HYM2": DGS.replace("DGS10", "BAMLH0A0HYM2")},
    )
    assert pack["availability"] in {"LIVE_FETCH", "PARTIAL"}
    assert pack["vintage"] == "CURRENT_REVISED_NOT_ALFRED"
    snap = live_macro(AS_OF, {"CPIAUCSL": CPI, "DGS10": DGS, "INDPRO": CPI.replace("CPIAUCSL", "INDPRO"), "WALCL": DGS.replace("DGS10", "WALCL"), "BAMLH0A0HYM2": DGS.replace("DGS10", "BAMLH0A0HYM2")})
    assert snap.environment["real_data_verified"] is False
    assert snap.regime != "UNAVAILABLE"
    assert snap.mutated_qgv is False
