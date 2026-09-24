"""Korea market track. DEFERRED.

Decision D-16: current implementation line is US listings only.
Do not fetch KRX prices or invent KR adapters here.
Official v1.1 still records hanmi; this track does not consume it.
"""

KR_DEFERRED = {
    "hanmi": {
        "company_id": "hanmi",
        "legal_name": "Hanmi Semiconductor",
        "local_ticker": "042700",
        "exchange": "KRX",
        "country": "KR",
        "status": "DEFERRED",
        "official_v11_weight": 0.045,
        "reason": "Korea book will be a separate implementation track.",
    }
}
