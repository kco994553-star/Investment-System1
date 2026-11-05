"""BT-DATA-PILOT v0.5: manual API/MCP/download response ingestion and gap planning.

Accept original bytes plus a source manifest, never chat summaries. Content-addressed
private storage and SQLite transactions permit offline replay and idempotent resume.
No trading engine, price inference, network request, or publication is performed.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sqlite3

from price_adapter import ROOT, internal_rights_allowed, normalize_tiingo

VERSION = "BT-DATA-PILOT v0.5"


def encoded(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(body):
    return hashlib.sha256(body).hexdigest()


def no_credentials(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if re.search(r"secret|password|authorization|api.?key|access.?token|^token$", key, re.I):
                raise ValueError("credential fields must not be included in source manifests")
            no_credentials(value)
    elif isinstance(obj, list):
        for value in obj:
            no_credentials(value)
    elif isinstance(obj, str) and re.search(r"(?:[?&](?:token|apikey|api_key)=)|(?:Bearer\s+)", obj, re.I):
        raise ValueError("credential-bearing URL or value")


def path_get(obj, path):
    for part in path.split(".") if path else []:
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


def validate_manifest(manifest, body):
    no_credentials(manifest)
    required = ("provider", "access_method", "tool_name", "arguments", "retrieved_at",
                "source_url", "raw_sha256", "schema", "rights", "request_start", "request_end")
    if any(key not in manifest for key in required):
        raise ValueError("incomplete source manifest")
    if manifest["access_method"] not in ("DIRECT_API", "DOWNLOAD", "PLUGIN_MCP", "MANUAL_EXPORT"):
        raise ValueError("unsupported access method")
    if manifest["raw_sha256"] != digest(body):
        raise ValueError("raw response SHA-256 mismatch")
    if datetime.fromisoformat(manifest["retrieved_at"].replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("retrieval timestamp needs timezone")
    if date.fromisoformat(manifest["request_start"]) > date.fromisoformat(manifest["request_end"]):
        raise ValueError("reversed request window")
    if not isinstance(manifest["arguments"], dict):
        raise ValueError("tool arguments must be structured")
    if not internal_rights_allowed(manifest["rights"]) or not manifest["rights"].get("evidence"):
        raise ValueError("zero-cost internal research/storage/cloud permission evidence required")


def normalize(body, manifest):
    schema = manifest["schema"]
    if schema == "SEC_SUBMISSIONS":
        obj = json.loads(body)
        if not isinstance(obj, dict) or not isinstance(obj.get("filings", {}).get("recent"), dict):
            raise ValueError("not an original SEC submissions response")
        if str(int(obj["cik"])) != str(int(manifest["issuer_cik"])):
            raise ValueError("issuer mismatch")
        return [], {"issuer_cik": obj["cik"], "filing_rows": len(obj["filings"]["recent"]["accessionNumber"])}
    if manifest.get("instrument_type") != "US_EQUITY":
        raise ValueError("only US spot equities accepted; crypto/derivatives are not replacements")
    if manifest.get("price_basis") not in ("RAW_UNADJUSTED", "SPLIT_ADJUSTED", "TOTAL_RETURN_ADJUSTED"):
        raise ValueError("explicit price adjustment basis required")
    if not manifest.get("security_scope") or not manifest.get("currency"):
        raise ValueError("dated security scope and currency required; may remain unverified")
    if schema == "TIINGO_EOD":
        if manifest["price_basis"] != "RAW_UNADJUSTED":
            raise ValueError("Tiingo raw fields must be declared unadjusted")
        records = normalize_tiingo(body, manifest["symbol"], manifest["currency"])
    else:
        if schema == "OHLCV_CSV":
            reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
            header = reader.fieldnames or []
            if len(header) != len(set(header)) or not set(manifest["field_map"].values()).issubset(header):
                raise ValueError("CSV header does not match declared provider fields")
            source = list(reader)
        elif schema == "OHLCV_JSON":
            source = path_get(json.loads(body), manifest["bars_path"])
        else:
            raise ValueError("unsupported source schema; add explicit adapter, never infer columns")
        if not isinstance(source, list):
            raise ValueError("expected bar array")
        mapping = manifest["field_map"]
        if any(key not in mapping for key in ("date", "open", "high", "low", "close", "volume")):
            raise ValueError("explicit OHLCV field map required")
        intermediate = []
        for row in source:
            mapped = {"date": path_get(row, mapping["date"])}
            for target, field in mapping.items():
                if target == "date":
                    continue
                value = path_get(row, field)
                mapped[target] = None if value in (None, "") else float(value)
            intermediate.append(mapped)
        records = normalize_tiingo(encoded(intermediate), manifest["symbol"], manifest["currency"])
        for normalized, source_row in zip(records, sorted(source, key=lambda r: path_get(r, mapping["date"]))):
            normalized["provider_payload"] = source_row
    for row in records:
        if not manifest["request_start"] <= row["session_date"] <= manifest["request_end"]:
            raise ValueError("bar outside declared request window")
        row["provider"] = manifest["provider"]
        row["price_basis"] = manifest["price_basis"]
        # The supplied namespace is a join candidate, not proof of permanent identity.
        row["security_scope"] = manifest["security_scope"]
        row["ledger_ready"] = False
    return records, {"rows": len(records), "ledger_ready": False}


def private_store(root):
    if root.resolve().is_relative_to(ROOT.parent):
        raise ValueError("private store must be outside repository")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    for folder in ("raw", "sources", "normalized"):
        (root / folder).mkdir(exist_ok=True, mode=0o700)
    db = sqlite3.connect(root / "index.sqlite")
    db.execute("CREATE TABLE IF NOT EXISTS captures (manifest_sha TEXT PRIMARY KEY, raw_sha TEXT, request_sha TEXT, schema TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS bars (provider TEXT, scope TEXT, day TEXT, basis TEXT, currency TEXT, value_sha TEXT, PRIMARY KEY(provider,scope,day,basis,currency))")
    return db


def put_once(path, body):
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError("content-addressed storage conflict")
        return
    tmp = path.with_suffix(".partial")
    tmp.write_bytes(body)
    tmp.chmod(0o600)
    tmp.replace(path)


def ingest(root, body, manifest):
    validate_manifest(manifest, body)
    source_body = encoded(manifest)
    mh, rh = digest(source_body), digest(body)
    request = {key: manifest[key] for key in ("provider", "tool_name", "arguments", "request_start", "request_end")}
    db = private_store(root)
    try:
        # Preserve received evidence even when schema validation or overlap review fails.
        # Only a committed captures row makes it an accepted input.
        put_once(root / "raw" / rh, body)
        put_once(root / "sources" / mh, source_body)
        records, summary = normalize(body, manifest)
        with db:
            if db.execute("SELECT 1 FROM captures WHERE manifest_sha=?", (mh,)).fetchone():
                # Revalidate persisted bytes; dedup must not hide a deleted/corrupt blob.
                if (root / "raw" / rh).read_bytes() != body:
                    raise ValueError("persisted raw response corrupt")
                return {"status": "ALREADY_IMPORTED", **summary}
            duplicate_rows = 0
            for row in records:
                key = (manifest["provider"], manifest["security_scope"], row["session_date"],
                       manifest["price_basis"], manifest["currency"])
                vh = digest(encoded({k: row[k] for k in ("raw", "adjusted", "events")}))
                old = db.execute("SELECT value_sha FROM bars WHERE provider=? AND scope=? AND day=? AND basis=? AND currency=?", key).fetchone()
                if old and old[0] != vh:
                    raise ValueError("overlap revision/conflict: retain separately for review, do not overwrite")
                duplicate_rows += bool(old)
                db.execute("INSERT OR IGNORE INTO bars VALUES (?,?,?,?,?,?)", (*key, vh))
            put_once(root / "normalized" / mh, encoded({"parser_version": VERSION, "records": records, "summary": summary}))
            db.execute("INSERT INTO captures VALUES (?,?,?,?)", (mh, rh, digest(encoded(request)), manifest["schema"]))
        return {"status": "IMPORTED", "duplicate_rows": duplicate_rows, **summary}
    finally:
        db.close()


def gaps(root, manifest, expected_sessions):
    """Use a supplied exchange calendar; never treat weekdays as verified sessions."""
    if len(set(expected_sessions)) != len(expected_sessions):
        raise ValueError("duplicate expected sessions")
    for day in expected_sessions:
        date.fromisoformat(day)
    db = private_store(root)
    try:
        present = {r[0] for r in db.execute("SELECT day FROM bars WHERE provider=? AND scope=? AND basis=? AND currency=?",
                   tuple(manifest[k] for k in ("provider", "security_scope", "price_basis", "currency")))}
        return {"missing_sessions": sorted(set(expected_sessions) - present),
                "present_sessions": sorted(set(expected_sessions) & present),
                "scope": "INGESTED_BARS_ONLY_NOT_PIT_OR_LEDGER_CERTIFICATION", "network_calls": 0}
    finally:
        db.close()


def replay(root):
    """Reparse committed captures from retained raw bytes with no network access."""
    db = private_store(root)
    checked = 0
    try:
        for mh, rh in db.execute("SELECT manifest_sha,raw_sha FROM captures"):
            source = (root / "sources" / mh).read_bytes()
            body = (root / "raw" / rh).read_bytes()
            if digest(source) != mh or digest(body) != rh:
                raise ValueError("stored source/raw checksum mismatch")
            manifest = json.loads(source)
            validate_manifest(manifest, body)
            records, summary = normalize(body, manifest)
            expected = encoded({"parser_version": VERSION, "records": records, "summary": summary})
            if (root / "normalized" / mh).read_bytes() != expected:
                raise ValueError("offline replay differs from captured normalization")
            checked += 1
        return {"replayed_captures": checked, "network_calls": 0, "status": "MATCHED"}
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("ingest", "plan", "replay"))
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--sessions", type=Path)
    args = parser.parse_args()
    if args.command != "replay" and not args.manifest:
        parser.error("--manifest required for ingest/plan")
    manifest = json.loads(args.manifest.read_text()) if args.manifest else None
    if args.command == "replay":
        result = replay(args.store)
    elif args.command == "ingest":
        if not args.raw:
            parser.error("--raw required")
        result = ingest(args.store, args.raw.read_bytes(), manifest)
    else:
        if not args.sessions:
            parser.error("--sessions required")
        result = gaps(args.store, manifest, json.loads(args.sessions.read_text()))
    print(json.dumps(result))
