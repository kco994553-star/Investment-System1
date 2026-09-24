from datetime import datetime, timezone

from investment_system.providers.yahoo_chart import parse_bars, pit_bar

PAYLOAD = {
    "chart": {
        "result": [
            {
                "meta": {"symbol": "INTC", "currency": "USD"},
                "timestamp": [1, 2],
                "indicators": {
                    "quote": [{"close": [20.0, 80.0]}],
                    "adjclose": [{"adjclose": [80.0, 80.0]}],
                },
            }
        ]
    }
}


def test_parse_bars_uses_adjclose_as_price():
    bars = parse_bars(PAYLOAD)
    assert bars[0]["price"] == 80.0
    assert bars[0]["close"] == 20.0
    assert bars[0]["adjusted"] is True
    a = pit_bar(bars, datetime(1970, 1, 1, 0, 0, 2, tzinfo=timezone.utc))
    assert a["price"] == 80.0
