"""US-listed working universe. NEW IMPLEMENTATION.

Official Portfolio v1.1 is not rewritten.
US track uses NASDAQ/NYSE listings only.
tokyo_electron stays C-08 unresolved and is out of this track.
hanmi is KR-deferred.
"""

from __future__ import annotations

# Official v1.1 slice for US listings only. Source weights unchanged.
_OFFICIAL_SLICE = {
    "asml": 0.09,
    "lrcx": 0.06,
    "klac": 0.055,
    "nvda": 0.08,
    "amd": 0.05,
    "avgo": 0.05,
    "qcom": 0.04,
    "intc": 0.03,
    "msft": 0.07,
    "googl": 0.07,
    "amzn": 0.06,
    "rtx": 0.06,
    "stry": 0.055,
    "etn": 0.05,
    "hubb": 0.035,
    "gev": 0.03,
    "rok": 0.02,
}

# Yahoo symbol + SEC CIK for US-listed official names. ASML is the NASDAQ ADR.
US_LISTINGS = {
    "asml": {"yahoo": "ASML", "cik": "0000937966", "exchange": "NASDAQ"},
    "lrcx": {"yahoo": "LRCX", "cik": "0000707549", "exchange": "NASDAQ"},
    "klac": {"yahoo": "KLAC", "cik": "0000319201", "exchange": "NASDAQ"},
    "nvda": {"yahoo": "NVDA", "cik": "0001045810", "exchange": "NASDAQ"},
    "amd": {"yahoo": "AMD", "cik": "0000002488", "exchange": "NASDAQ"},
    "avgo": {"yahoo": "AVGO", "cik": "0001730168", "exchange": "NASDAQ"},
    "qcom": {"yahoo": "QCOM", "cik": "0000804328", "exchange": "NASDAQ"},
    "intc": {"yahoo": "INTC", "cik": "0000050863", "exchange": "NASDAQ"},
    "msft": {"yahoo": "MSFT", "cik": "0000789019", "exchange": "NASDAQ"},
    "googl": {"yahoo": "GOOGL", "cik": "0001652044", "exchange": "NASDAQ"},
    "amzn": {"yahoo": "AMZN", "cik": "0001018724", "exchange": "NASDAQ"},
    "rtx": {"yahoo": "RTX", "cik": "0000101829", "exchange": "NYSE"},
    "stry": {"yahoo": "SYK", "cik": "0000310764", "exchange": "NYSE"},
    "etn": {"yahoo": "ETN", "cik": "0001551182", "exchange": "NYSE"},
    "hubb": {"yahoo": "HUBB", "cik": "0000048898", "exchange": "NYSE"},
    "gev": {"yahoo": "GEV", "cik": "0001996810", "exchange": "NYSE"},
    "rok": {"yahoo": "ROK", "cik": "0001024478", "exchange": "NYSE"},
}

OUT_OF_US_TRACK = {
    "hanmi": "KR_DEFERRED",
    "tokyo_electron": "C-08_NON_US",
}


def us_company_ids() -> tuple[str, ...]:
    return tuple(US_LISTINGS)


def official_us_weight_mass() -> float:
    return sum(_OFFICIAL_SLICE.values())


# Renormalized working weights. PROVISIONAL. Not Official v1.1.
US_WORKING_TARGETS = {
    cid: _OFFICIAL_SLICE[cid] / official_us_weight_mass() for cid in _OFFICIAL_SLICE
}
