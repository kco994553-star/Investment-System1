"""BT-DATA-PILOT v0.5: bounded accountless acquisition, private raw store only.

No prices are inferred from current identifiers or reference-price master fields.
Run with --private-dir outside the repository. Existing successful responses are cached.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from investment_system.ingestion.raw_store import RawDatasetStore

CIKS = (1800, 2098, 2178, 2186, 2488, 3197, 3453, 3499, 3570, 4187)
EVENT_CIKS = (1326801, 1418091, 718877, 806085)


def acquire(store, aid, url, kind, headers=None):
    if store.has(aid):
        body = store.get_bytes(aid)
        receipt = store.get_manifest(aid)
        if hashlib.sha256(body).hexdigest() != receipt["sha256"]:
            raise ValueError("cached source checksum mismatch")
        return body, receipt
    try:
        request_headers = {"User-Agent": "Investment-System1 BT-DATA-PILOT research", **(headers or {})}
        with urlopen(Request(url, headers=request_headers), timeout=25) as response:
            body = response.read(12 * 1024 * 1024 + 1)
            if len(body) > 12 * 1024 * 1024:
                raise ValueError("bounded acquisition exceeded 12 MiB")
            receipt = store.put(aid, body, url, kind, response.headers.get("Content-Type", ""),
                                "BT-DATA-PILOT v0.5", response.status).to_dict()
            return body, receipt
    except (HTTPError, URLError, TimeoutError) as error:
        return None, {"artifact_id": aid, "source_url": url, "status": type(error).__name__,
                      "retrieved_at": datetime.now(timezone.utc).isoformat(),
                      "http_status": getattr(error, "code", None)}


def run(private_dir):
    if private_dir.resolve().is_relative_to(ROOT.parent):
        raise ValueError("private directory must be outside repository")
    private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_dir.chmod(0o700)
    store = RawDatasetStore(private_dir / "store")
    result = {"version": "BT-DATA-PILOT v0.5", "data_fee": 0, "receipts": [],
              "issuers": [], "masters": [], "formal_backtests": 0}
    for cik in CIKS + EVENT_CIKS:
        url = f"https://data.sec.gov/submissions/CIK{cik:010}.json"
        body, receipt = acquire(store, f"submissions:{cik:010}", url, "SEC_SUBMISSIONS")
        result["receipts"].append(receipt)
        record = {"cik": cik, "cohort": "FIXED10" if cik in CIKS else "EVENT4", "status": "NOT_ACQUIRED"}
        if body is not None:
            try:
                data = json.loads(body)
                if int(data["cik"]) != cik:
                    raise ValueError("CIK mismatch")
                recent = data["filings"]["recent"]
                record.update(status="ACQUIRED", name=data.get("name"), tickers=data.get("tickers"),
                              exchanges=data.get("exchanges"), sic=data.get("sic"),
                              former_names=data.get("formerNames"),
                              filing_rows=len(recent["accessionNumber"]),
                              filing_min=min(recent["filingDate"], default=None),
                              filing_max=max(recent["filingDate"], default=None),
                              historical_files=data["filings"].get("files", []),
                              ticker_scope="CURRENT_SNAPSHOT_NOT_HISTORICAL_SECURITY_ID")
            except (ValueError, KeyError, TypeError):
                record["status"] = "INVALID_PAYLOAD"
        result["issuers"].append(record)
        time.sleep(0.15)
    for market in ("nas", "nys", "ams"):
        url = f"https://new.real.download.dws.co.kr/common/master/{market}mst.cod.zip"
        body, receipt = acquire(store, f"kis_master:{market}", url, "KIS_PUBLIC_CURRENT_MASTER")
        result["receipts"].append(receipt)
        item = {"market": market, "status": "NOT_ACQUIRED"}
        if body is not None:
            try:
                with zipfile.ZipFile(io.BytesIO(body)) as archive:
                    if archive.testzip() is not None:
                        raise ValueError("ZIP CRC")
                    matches = [name for name in archive.namelist() if name.lower() == f"{market}mst.cod"]
                    if len(matches) != 1:
                        raise ValueError("ambiguous ZIP member")
                    raw = archive.read(matches[0])
                rows = list(csv.reader(io.StringIO(raw.decode("cp949")), delimiter="\t"))
                widths = sorted(set(map(len, rows)))
                item.update(status="ACQUIRED", rows=len(rows), column_counts=widths,
                            snapshot_only=True, prices_usable_for_execution=False)
                (private_dir / f"kis-{market}-rows.json").write_text(json.dumps(rows, ensure_ascii=False))
            except (ValueError, zipfile.BadZipFile, KeyError):
                item["status"] = "INVALID_PAYLOAD"
        result["masters"].append(item)
    # One tiny bounded test of the advertised CSV endpoint; never solve a challenge.
    url = "https://stooq.com/q/d/l/?s=abt.us&i=d&d1=20160328&d2=20160401"
    body, receipt = acquire(store, "stooq_probe:abt", url, "STOOQ_BOUNDED_DOWNLOAD")
    result["receipts"].append(receipt)
    valid = body is not None and body.startswith(b"Date,Open,High,Low,Close,Volume")
    result["stooq"] = {"status": "CSV_ACQUIRED" if valid else "NO_VALID_CSV",
                       "rows": len(body.splitlines()) - 1 if valid else 0,
                       "challenge_not_bypassed": True}
    (private_dir / "acquisition.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return {"sec_submissions": sum(x["status"] == "ACQUIRED" for x in result["issuers"]),
            "masters": result["masters"], "stooq": result["stooq"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.private_dir), indent=2))
