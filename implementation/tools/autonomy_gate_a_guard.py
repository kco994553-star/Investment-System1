#!/usr/bin/env python3
"""Fail-closed repository guard for Autonomous Execution SSoT v1.1 Gate A.

This guard does not grant autonomy by itself. It enforces:
- immutable Frozen artifacts cannot be modified/deleted/renamed;
- append-only records cannot rewrite or delete existing bytes;
- AUTONOMY_MODE is a single explicit state;
- operating values stay within the adopted CDR-024 configuration.
- populated user-device holdings, market exports, private sheet settings and credentials cannot enter tracked content.

HG-02 still requires GitHub-side branch/ruleset enforcement.
"""

from __future__ import annotations

import argparse
import csv
import errno
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = IMPLEMENTATION_ROOT / "docs/coordination/governance/AUTONOMY_GUARD_CONFIG.v1.json"


# GSQ-010 grants exactly one protected preimage-to-absence transition. The JSON
# is metadata evidence, not configurable permission; its complete bytes are pinned.
_CLEANUP_READINESS_PATH = "implementation/reports/gate_evidence/track_a_freeze_readiness_2026-09-27.json"
_CLEANUP_RECEIPT_PATH = "implementation/docs/public_price_boundary/CLEANUP_AUTHORITY.json"
_CLEANUP_READINESS_BLOB_SHA1 = "d369dd3af1b7f10ccf5233cf9e04694bc7fad165"
_CLEANUP_READINESS_SHA256 = "5789dc3d3b10dd29d466931bf9c6f459d2569d15071f80dfd50236d0b0cef006"
_CLEANUP_READINESS_BYTES = 8781
_CLEANUP_RECEIPT_SHA256 = "43b9fa232185a21530d0310e1c866cc58e2594d5b89d1d7791bfc1d6a3997e19"
_CLEANUP_AUTHORITY_COMMIT = "ee039041ae7f5cb94e6a127930c7e43effb811ec"
_CLEANUP_AUTHORITY_PINS = {'implementation/docs/public_price_boundary/AUDIT.md': '780af5763ff24a10ce1538f083aa5aac80d470cd', 'implementation/docs/public_price_boundary/RECEIPTS.md': '55469fc2c68adc6fc380244b838e53b0a0b13a92', 'implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md': '4fc2fc62461cde4e86f96102f285696ea3a07ddb'}

# These are shape signals, not an allowlist of synthetic or trusted filenames.
# A synthetic label never permits a populated device export in the public tree.
_QUANTITY_KEYS = {"quantity", "qty", "shares", "units", "quantityheld"}
_COST_KEYS = {"averagecost", "avgcost", "averageprice", "avgprice", "costbasis", "unitcost"}
_CURRENCY_KEYS = {"currency", "ccy"}
_IDENTITY_KEYS = {"securityreference", "securityid", "symbol", "ticker", "tickerhint", "isin", "cusip"}
_COLLECTION_KEYS = {"positions", "holdings"}
_MARKET_VALUE_KEYS = {"price", "rate", "fxrate", "exchangerate"}
_MARKET_RECORD_KEYS = _MARKET_VALUE_KEYS | _IDENTITY_KEYS | _CURRENCY_KEYS | {"asof", "availableat", "source"}
_MARKET_COLLECTION_KEYS = {"quotes", "fx", "fxrates", "rates", "prices"}
_CREDENTIAL_KEYS = {
    "apikey", "appkey", "appsecret", "accesstoken", "refreshtoken", "clientsecret",
    "apisecret", "secretkey", "authtoken", "bearertoken",
    "spreadsheetid", "spreadsheeturl", "sheetid", "sheeturl",
    "googlesheetid", "googlesheeturl", "googlespreadsheetid", "googlespreadsheeturl",
}
# Raw text checks also cover source, logs and Markdown outside export envelopes.
# IDs need Google URL/setting context: a bare long string can be a public hash
# or public OAuth client ID. Neither is private spreadsheet configuration.
_PRIVATE_GOOGLE_PATTERNS = (
    re.compile(r"ya29\.[A-Za-z0-9._~-]+"),
    re.compile(
        r"(?i)(?:docs\.google\.com/spreadsheets/(?:u/\d+/)?d/|"
        r"sheets\.googleapis\.com/v4/spreadsheets/)[A-Za-z0-9_-]{20,}"
    ),
    re.compile(
        r"(?i)(?<!\w)(?:google[_-]?)?(?:spreadsheet|sheet)[_-]?id"
        r"[\"']?\s*(?:\]\s*)?[:=]\s*[\"'`][A-Za-z0-9_-]{20,}"
    ),
)
_PRIVATE_MARKET_EXPORT_NAME = re.compile(
    r"(?:^|[-_])(?:device|user|personal|broker|manual)[-_]"
    r"(?:market(?:[-_]data)?|quotes?|fx(?:[-_]rates)?)(?:[-_]|$)", re.IGNORECASE,
)
_PRIVATE_EXPORT_NAME = re.compile(
    r"(?:^|[-_])(?:actual(?:[-_](?:holdings|positions|portfolio|v\d+))?"
    r"|(?:device|user|personal|broker)[-_](?:actual[-_])?(?:holdings|positions|portfolio))"
    r"(?:[-_]|$)", re.IGNORECASE,
)
_YAML_FIELD = re.compile(
    r"(?:^[ \t]*(?:-[ \t]*)?|[,{][ \t]*)['\"]?([A-Za-z_][\w .-]*)['\"]?[ \t]*:[ \t]*"
    r"((?:&[\w-]+[ \t]+)?(?:'(?:''|[^'])*'|\"(?:\\.|[^\"\\])*\"|[^,}\]\n]*))",
    re.MULTILINE,
)


class GuardError(RuntimeError):
    pass


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _populated(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_populated(v) for v in value.values())
    if isinstance(value, list):
        return any(_populated(v) for v in value)
    return True  # Zero quantities and costs are still private holding information.


def _number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) or (
        isinstance(value, str)
        and bool(re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value.strip()))
    )


def _actual_marker(fields: dict) -> bool:
    return any(
        (key == "schema" and str(value).lower().startswith("device-actual-holdings/"))
        or (key in {"kind", "portfoliokind"} and str(value).upper() == "ACTUAL")
        or (key in {"ownership", "storage", "ownerstorage"} and str(value).upper() == "USER_DEVICE_ONLY")
        for key, value in fields.items()
    )


def _market_marker(fields: dict) -> bool:
    return _actual_marker(fields) or any(
        key == "schema" and str(value).lower().startswith("device-market-data/")
        for key, value in fields.items()
    )


def _credential_fields(fields: dict) -> bool:
    # Property/type descriptions are mappings, not populated credential strings.
    return any(
        key in _CREDENTIAL_KEYS and isinstance(value, str) and _populated(value)
        for key, value in fields.items()
    )


def _private_google_text(value: object) -> bool:
    return isinstance(value, str) and any(pattern.search(value) for pattern in _PRIVATE_GOOGLE_PATTERNS)


def _market_row(fields: dict, *, timing_fields: bool = False) -> bool:
    record_keys = _MARKET_RECORD_KEYS if timing_fields else _MARKET_RECORD_KEYS - {"asof", "availableat"}
    return any(
        key in record_keys and isinstance(value, (str, int, float)) and _populated(value)
        for key, value in fields.items()
    )


def _holding_row(fields: dict, *, partial: bool = False) -> bool:
    quantity = any(_number(fields.get(key)) for key in _QUANTITY_KEYS)
    identity = any(_populated(fields.get(key)) for key in _IDENTITY_KEYS)
    if partial:
        return quantity or identity
    return quantity and identity and any(_number(fields.get(key)) for key in _COST_KEYS) and any(
        isinstance(fields.get(key), str) and _populated(fields[key]) for key in _CURRENCY_KEYS
    )


def _structured_private(value: object, named_export: bool, named_market_export: bool = False) -> bool:
    mappings: list[dict] = []
    populated_holdings = False
    populated_market = False
    populated_google = False

    def visit(node: object) -> None:
        nonlocal populated_holdings, populated_market, populated_google
        if isinstance(node, dict):
            fields = {_key(key): item for key, item in node.items()}
            mappings.append(fields)
            populated_holdings |= any(
                key in _COLLECTION_KEYS and isinstance(item, (list, dict)) and _populated(item)
                for key, item in fields.items()
            )
            populated_market |= any(
                key in _MARKET_COLLECTION_KEYS and isinstance(item, (list, dict)) and _populated(item)
                for key, item in fields.items()
            )
            for item in node.values():
                visit(item)
        elif isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, str):
            # json.loads resolves escaped slashes and unicode before inspection.
            populated_google |= _private_google_text(node)

    visit(value)
    marked = any(_actual_marker(fields) for fields in mappings)
    market_marked = named_market_export or any(_market_marker(fields) for fields in mappings)
    return (
        populated_google
        or any(_credential_fields(fields) for fields in mappings)
        or (market_marked and (populated_market or any(_market_row(fields) for fields in mappings)))
        or (marked and populated_holdings)
        or any(_holding_row(fields) for fields in mappings)
        or (named_export and any(_holding_row(fields, partial=True) for fields in mappings))
    )


def _yaml_scalar(raw_value: str) -> tuple[str, bool]:
    raw_value = raw_value.strip()
    if raw_value.startswith(("'", '"')):
        pattern = r"^'((?:''|[^'])*)'" if raw_value[0] == "'" else r'^"((?:\\.|[^"\\])*)"'
        match = re.match(pattern, raw_value)
        if match and raw_value[0] == '"':
            try:
                return json.loads(match.group(0)), True
            except ValueError:
                pass
        # Incomplete quoted text remains a conservative population signal.
        return (match.group(1) if match else raw_value[1:]), True
    return ("" if raw_value.startswith("#") else raw_value.split(" #", 1)[0].strip()), False


def _yaml_quote_continues(content: str, quote: str) -> bool:
    index = 0
    while index < len(content):
        if quote == '"' and content[index] == "\\":
            index += 2
        elif content[index] == quote:
            if quote == "'" and content[index:index + 2] == "''":
                index += 2
            else:
                return False
        else:
            index += 1
    return True


def _yaml_private(content: str, named_export: bool, named_market_export: bool = False) -> bool:
    """Recognize export-shaped YAML without requiring a CI YAML dependency.

    Only mapping/sequence documents are considered, so source code describing the
    format is not treated as a payload. Flow mappings, anchors and stream markers
    are accepted. This is deliberately a shape check, not a YAML schema validator.
    """
    lines = [line for line in content.splitlines() if line.strip()]
    if not lines:
        return False
    block_indent = None
    credential_block = False
    continued_quote = None
    scan_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if continued_quote is not None:
            scan_lines.append(line)
            if not _yaml_quote_continues(line, continued_quote):
                continued_quote = None
            continue
        if block_indent is not None and indent > block_indent:
            if credential_block:
                return True
            continue
        block_indent = None
        credential_block = False
        if stripped.startswith("#"):
            continue
        if stripped in {"---", "...", "[", "]", "{", "}"} or stripped.startswith(("%", "!")):
            scan_lines.append(line)
            continue
        if not (indent or re.match(r"^[ \t]*(?:-[ \t]+|(?:['\"]?[A-Za-z_][\w .-]*['\"]?[ \t]*:|[\[{]|[&*][\w-]+))", line)):
            return False
        scan_lines.append(line)
        for field in _YAML_FIELD.finditer(line):
            raw_value = re.sub(r"^&[\w-]+[ \t]+", "", field.group(2).strip())
            if raw_value.startswith(("'", '"')) and _yaml_quote_continues(raw_value[1:], raw_value[0]):
                continued_quote = raw_value[0]
        if re.search(r":\s*[|>][-+]?\s*(?:#.*)?$", line):
            block_indent = indent
            match = _YAML_FIELD.search(line)
            credential_block = match is not None and _key(match.group(1)) in _CREDENTIAL_KEYS

    fields: dict[str, str] = {}
    market_fields: dict[str, str] = {}
    anchors: dict[str, tuple[str, bool]] = {}
    marked = False
    market_marked = named_market_export
    credentials = False
    for match in _YAML_FIELD.finditer("\n".join(scan_lines)):
        raw_value = match.group(2).strip()
        anchor = re.match(r"^&([\w-]+)[ \t]+(.*)$", raw_value, re.DOTALL)
        value, quoted = _yaml_scalar(anchor.group(2) if anchor else raw_value)
        if anchor:
            anchors[anchor.group(1)] = (value, quoted)
        if not quoted and value.startswith("*"):
            value, quoted = anchors.get(value[1:], (value, quoted))
        if not quoted and (value.lower() in {"null", "~"} or value in {"[]", "{}"}):
            value = ""
        key = _key(match.group(1))
        marked |= _actual_marker({key: value})
        market_marked |= _market_marker({key: value})
        scalar = quoted or (not value.startswith(("{", "[")) and not re.fullmatch(r"[|>][-+]?", value))
        if scalar:
            credentials |= _credential_fields({key: value})
            if key not in market_fields or (_populated(value) and (not _number(market_fields[key]) or _number(value))):
                market_fields[key] = value
        # Never let a later placeholder erase evidence of an exported row.
        if key not in fields or (_populated(value) and (not _number(fields[key]) or _number(value))):
            fields[key] = value
    identity = any(key in fields for key in _IDENTITY_KEYS) and (
        any(_populated(fields.get(key)) for key in _IDENTITY_KEYS)
        or _populated(fields.get("value")) or _populated(fields.get("code"))
    )
    generic_row = any(_number(fields.get(key)) for key in _QUANTITY_KEYS) and identity and any(
        _number(fields.get(key)) for key in _COST_KEYS
    ) and any(_populated(fields.get(key)) for key in _CURRENCY_KEYS)
    holding_data = any(_number(fields.get(key)) for key in _QUANTITY_KEYS | _COST_KEYS) or identity
    market_data = _market_row(market_fields, timing_fields=bool(_MARKET_COLLECTION_KEYS.intersection(fields)))
    return credentials or (market_marked and market_data) or generic_row or ((marked or named_export) and holding_data)


def _csv_private(content: str, named_export: bool, named_market_export: bool = False) -> bool:
    content = content.lstrip("\r\n \t")
    first_line = next((line for line in content.splitlines() if line.strip()), "")
    for delimiter in (",", "\t", ";"):
        if delimiter not in first_line and (
            delimiter != "," or not re.fullmatch(r"['\"]?[A-Za-z_][\w .-]*['\"]?", first_line.strip())
        ):
            continue
        try:
            reader = csv.reader(io.StringIO(content), delimiter=delimiter)
            headers = [_key(key) for key in next(reader, [])]
            if not set(headers).intersection(_QUANTITY_KEYS | _MARKET_RECORD_KEYS | _CREDENTIAL_KEYS):
                continue
            for row in reader:
                pairs = list(zip(headers, row))
                fields: dict[str, str] = {}
                for key, value in pairs:
                    # Duplicate or normalized headers cannot erase an earlier
                    # populated cell, including zero-valued market/holding data.
                    if key not in fields or (_populated(value) and (not _number(fields[key]) or _number(value))):
                        fields[key] = value
                if (
                    any(_credential_fields({key: value}) for key, value in pairs)
                    or ((any(_market_marker({key: value}) for key, value in pairs) or named_market_export) and _market_row(fields, timing_fields=True))
                    or _holding_row(fields)
                    or ((any(_actual_marker({key: value}) for key, value in pairs) or named_export) and _holding_row(fields, partial=True))
                ):
                    return True
        except csv.Error:
            # No parser text is returned: parse errors may include private values.
            continue
    return False


def contains_device_actual(content: bytes, path: str) -> bool:
    """Recognize populated export payloads; never return their fields or values."""
    try:
        if content.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
            decoded = content.decode("utf-32")
        elif content.startswith((b"\xff\xfe", b"\xfe\xff")):
            decoded = content.decode("utf-16")
        else:
            decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    if _private_google_text(decoded):
        return True
    if "\0" in decoded:
        return False
    filename = Path(path)
    named_export = filename.suffix.lower() in {".json", ".yaml", ".yml", ".csv", ".tsv", ".txt", ".dat"} and bool(
        _PRIVATE_EXPORT_NAME.search(filename.stem)
    )
    named_market_export = filename.suffix.lower() in {".json", ".yaml", ".yml", ".csv", ".tsv", ".txt", ".dat"} and bool(
        _PRIVATE_MARKET_EXPORT_NAME.search(filename.stem)
    )
    try:
        if _structured_private(json.loads(decoded), named_export, named_market_export):
            return True
    except (ValueError, RecursionError):
        pass
    if _csv_private(decoded, named_export, named_market_export) or _yaml_private(decoded, named_export, named_market_export):
        return True
    # Payloads pasted into Markdown/logs are still repository content. Ordinary
    # source/tests are not searched for string literals describing this schema.
    if filename.suffix.lower() in {".md", ".markdown", ".log", ".txt"}:
        for match in re.finditer(r"(?m)^```(?:json|ya?ml|csv|tsv)?\s*\n(.*?)^```\s*$", decoded, re.DOTALL):
            if contains_device_actual(match.group(1).encode("utf-8"), "embedded.dat"):
                return True
    return False


def _git_bytes(args: list[str]) -> bytes:
    proc = subprocess.run(["git", "--no-replace-objects", *args], cwd=REPO_ROOT, check=False, capture_output=True)
    if proc.returncode:
        # Git diagnostics can include a private path; keep this failure generic.
        raise GuardError("tracked-content privacy scan could not read repository state")
    return proc.stdout


def _tracked_worktree_bytes(path: str) -> bytes | None:
    """Read only regular tracked files; never follow any symlink component."""
    if not hasattr(os, "O_NOFOLLOW"):
        raise GuardError("tracked-content privacy scan requires no-follow filesystem support")
    directory = None
    file_fd = None
    try:
        directory = os.open(REPO_ROOT, os.O_RDONLY | os.O_DIRECTORY)
        parts = Path(path).parts
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            return None
        with os.fdopen(file_fd, "rb") as file:
            file_fd = None
            return file.read()
    except OSError as exc:
        if exc.errno in {errno.ENOENT, errno.ELOOP, errno.ENOTDIR}:
            return None
        raise GuardError("tracked-content privacy scan could not read a tracked file") from None
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory is not None:
            os.close(directory)


def device_actual_violations(base: str | None = None) -> list[str]:
    """Scan new committed versions, HEAD, index and tracked working files.

    Reading blobs catches staged/committed values hidden by working-tree edits.
    Reading tracked worktree files also catches a payload before it is staged.
    Findings intentionally omit filenames, parser details, and private values.
    """
    blobs: dict[tuple[str, str], None] = {}
    tracked_paths: set[str] = set()
    for entry in _git_bytes(["ls-files", "--stage", "-z"]).split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, oid, _stage = metadata.split()
        path = raw_path.decode("utf-8", "surrogateescape")
        tracked_paths.add(path)
        if mode != b"160000":
            blobs[(oid.decode("ascii"), path)] = None
    for entry in _git_bytes(["ls-tree", "-r", "-z", "HEAD"]).split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        _mode, kind, oid = metadata.split()
        if kind == b"blob":
            path = raw_path.decode("utf-8", "surrogateescape")
            blobs[(oid.decode("ascii"), path)] = None

    if base is not None:
        # A payload added then deleted in this range would still publish its
        # intermediate Git blob. Include every new version, including merges.
        history = iter(_git_bytes([
            "log", "--format=", "--raw", "-z", "--no-abbrev", "--no-renames",
            "--diff-merges=separate", f"{base}..HEAD", "--",
        ]).split(b"\0"))
        for entry in history:
            entry = entry.lstrip(b"\n")
            if not entry.startswith(b":"):
                continue
            metadata = entry[1:].split()
            if len(metadata) != 5:
                raise GuardError("tracked-content privacy scan received invalid history metadata")
            _old_mode, mode, _old_oid, oid, _status = metadata
            raw_path = next(history, None)
            if raw_path is None:
                raise GuardError("tracked-content privacy scan received incomplete history metadata")
            if mode not in {b"000000", b"160000"}:
                path = raw_path.decode("utf-8", "surrogateescape")
                blobs[(oid.decode("ascii"), path)] = None

    requests = b"".join(oid.encode("ascii") + b"\n" for oid, _path in blobs)
    output = io.BytesIO()
    if requests:
        proc = subprocess.run(["git", "--no-replace-objects", "cat-file", "--batch"], cwd=REPO_ROOT, input=requests, capture_output=True)
        if proc.returncode:
            raise GuardError("tracked-content privacy scan could not read repository blobs")
        output = io.BytesIO(proc.stdout)
    rejected: set[str] = set()
    for _oid, path in blobs:
        header = output.readline().split()
        if len(header) != 3 or header[1] != b"blob":
            raise GuardError("tracked-content privacy scan received an invalid repository blob")
        content = output.read(int(header[2]))
        output.read(1)
        if contains_device_actual(content, path):
            rejected.add(path)
    for path in tracked_paths:
        content = _tracked_worktree_bytes(path)
        if content is not None and contains_device_actual(content, path):
            rejected.add(path)
    return ["populated device ACTUAL holdings in tracked repository content"] * len(rejected)


def load_config(path: Path = CONFIG_PATH) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    expected = {"cycle_max_tasks": 5, "lease_ttl_seconds": 7200, "repair_round_cap": 3}
    if cfg.get("operating_values") != expected:
        raise GuardError(f"operating values drift: {cfg.get('operating_values')!r}")
    return cfg


def parse_name_status(raw: str) -> list[tuple[str, list[str]]]:
    """Accept Git's unquoted NUL format and the legacy unit-test text format."""
    out: list[tuple[str, list[str]]] = []
    if "\0" in raw:
        fields = raw.split("\0")
        if fields.pop() != "":
            raise GuardError("incomplete protected-content diff metadata")
        index = 0
        while index < len(fields):
            status = fields[index]
            count = 2 if status.startswith(("R", "C")) else 1
            paths = fields[index + 1:index + 1 + count]
            if not re.fullmatch(r"[ACDMRTUXB][0-9]*", status) or len(paths) != count or not all(paths):
                raise GuardError("invalid protected-content diff metadata")
            out.append((status, paths))
            index += count + 1
        return out
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            raise GuardError("invalid protected-content diff metadata")
        out.append((parts[0], parts[1:]))
    return out


def _touches(path: str, cfg: dict) -> bool:
    return (
        path in {_CLEANUP_READINESS_PATH, _CLEANUP_RECEIPT_PATH}
        or path in cfg["immutable_exact_paths"]
        or path in cfg["append_only_exact_paths"]
        or any(path.startswith(prefix) for prefix in cfg["append_only_prefixes"])
    )


def classify_diff(records: list[tuple[str, list[str]]], cfg: dict, append_verifier=None) -> list[str]:
    """An M may append only to an exact log with independent content proof.

    Without a verifier this remains conservative. Evidence-directory entries
    and immutable paths never use the log append exception.
    """
    violations: list[str] = []
    immutable = set(cfg["immutable_exact_paths"]) | {_CLEANUP_RECEIPT_PATH}
    append_files = set(cfg["append_only_exact_paths"])
    prefixes = tuple(cfg["append_only_prefixes"])
    for status, paths in records:
        if not status or not paths:
            raise GuardError("invalid protected-content diff metadata")
        code = status[0]
        old_path, new_path = paths[0], paths[-1]
        if old_path in immutable or new_path in immutable:
            if code != "A":
                violations.append(f"immutable path changed: {status} {paths}")
            continue
        evidence_hit = old_path.startswith(prefixes) or new_path.startswith(prefixes)
        append_hit = old_path in append_files or new_path in append_files or evidence_hit
        if append_hit and code != "A":
            proven_append = (
                code == "M" and old_path == new_path and old_path in append_files
                and not evidence_hit and append_verifier is not None
                and append_verifier(old_path)
            )
            if not proven_append:
                violations.append(f"append-only existing content changed: {status} {paths}")
    return violations


def _guard_git_bytes(args: list[str]) -> bytes:
    proc = subprocess.run(
        ["git", "--no-replace-objects", *args], cwd=REPO_ROOT,
        check=False, capture_output=True,
    )
    if proc.returncode:
        raise GuardError("protected-content verification could not read repository state")
    return proc.stdout


def _reject_grafted_history() -> None:
    """Grafts can conceal committed states despite --no-replace-objects."""
    if "GIT_GRAFT_FILE" in os.environ:
        raise GuardError("protected-content verification does not support grafted history")
    graft_path = _guard_git_bytes([
        "rev-parse", "--path-format=absolute", "--git-path", "info/grafts",
    ]).removesuffix(b"\n")
    if not graft_path:
        raise GuardError("protected-content verification could not locate history metadata")
    try:
        os.lstat(os.fsdecode(graft_path))
    except FileNotFoundError:
        return
    except OSError:
        raise GuardError("protected-content verification could not inspect history metadata") from None
    raise GuardError("protected-content verification does not support grafted history")


def resolve_comparison(base: str) -> tuple[str, str]:
    """Freeze the same unique merge base and HEAD used by the reported diff."""
    _reject_grafted_history()
    def commit(ref):
        oid = _guard_git_bytes(["rev-parse", "--verify", "--end-of-options", ref + "^{commit}"]).strip()
        if not re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", oid):
            raise GuardError("invalid protected-content comparison commit")
        return oid.decode("ascii")
    base_commit, head = commit(base), commit("HEAD")
    bases = _guard_git_bytes(["merge-base", "--all", base_commit, head]).splitlines()
    if len(bases) != 1 or not re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", bases[0]):
        raise GuardError("protected-content verification requires one unambiguous merge base")
    if _guard_git_bytes(["rev-parse", "--is-shallow-repository"]).strip() != b"false":
        raise GuardError("protected-content verification requires complete repository history")
    return bases[0].decode("ascii"), head


def git_name_status(base: str, *, head: str | None = None) -> str:
    if head is None:
        base, head = resolve_comparison(base)
    return _guard_git_bytes([
        "diff", "--name-status", "-z", "--no-renames", "--no-ext-diff",
        "--no-textconv", "--ignore-submodules=none", base, head, "--",
    ]).decode("utf-8", "surrogateescape")


def _safe_git_path(raw_path: bytes) -> str:
    path = raw_path.decode("utf-8", "surrogateescape")
    if not path or path.startswith("/") or any(part in {"", ".", ".."} for part in path.split("/")):
        raise GuardError("invalid protected-content repository path")
    return path


def _cleanup_structural_obstructions(path: str, kind: str) -> set[str]:
    """A tree at a cleanup leaf or a non-directory ancestor is not absence."""
    return {
        target for target in (_CLEANUP_READINESS_PATH, _CLEANUP_RECEIPT_PATH)
        if (path == target and kind == "tree")
        or path.startswith(target + "/")
        or (target.startswith(path + "/") and kind != "tree")
    }


def _protected_tree(tree: str, cfg: dict) -> dict:
    state = {}
    obstructed = set()
    for entry in _guard_git_bytes(["ls-tree", "-r", "-t", "--full-tree", "-z", tree]).split(b"\0"):
        if not entry:
            continue
        try:
            metadata, raw_path = entry.split(b"\t", 1)
            mode, kind, oid = metadata.split()
        except ValueError:
            raise GuardError("invalid protected-content tree metadata") from None
        path = _safe_git_path(raw_path)
        obstructed.update(_cleanup_structural_obstructions(path, kind.decode("ascii")))
        if kind == b"tree":
            continue  # Ordinary ancestor directories are not protected leaf files.
        if _touches(path, cfg) or oid.decode("ascii") == _CLEANUP_READINESS_BLOB_SHA1:
            state[path] = (mode.decode("ascii"), kind.decode("ascii"), oid.decode("ascii"))
    state.update({path: ("INVALID", "structural-obstruction", b"") for path in obstructed})
    return state


def _protected_index(cfg: dict) -> dict:
    state = {}
    obstructed = set()
    for entry in _guard_git_bytes(["ls-files", "--stage", "-z"]).split(b"\0"):
        if not entry:
            continue
        try:
            metadata, raw_path = entry.split(b"\t", 1)
            mode, oid, stage = metadata.split()
        except ValueError:
            raise GuardError("invalid protected-content index metadata") from None
        path = _safe_git_path(raw_path)
        kind = "commit" if mode == b"160000" else "tree" if mode == b"040000" else "blob"
        affected = _cleanup_structural_obstructions(path, kind)
        obstructed.update(affected)
        if affected and stage != b"0":
            raise GuardError("protected-content verification requires a resolved index")
        if _touches(path, cfg) or oid.decode("ascii") == _CLEANUP_READINESS_BLOB_SHA1:
            if stage != b"0" or path in state:
                raise GuardError("protected-content verification requires a resolved index")
            state[path] = (mode.decode("ascii"), kind, oid.decode("ascii"))
    state.update({path: ("INVALID", "structural-obstruction", b"") for path in obstructed})
    return state


def _protected_worktree_entry(path: str):
    """Read a protected tracked file without following any symlink component."""
    if not hasattr(os, "O_NOFOLLOW"):
        raise GuardError("protected-content verification requires no-follow filesystem support")
    directory = file_fd = None
    try:
        directory = os.open(REPO_ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        parts = path.split("/")
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            return ("INVALID", "nonregular", b"")
        with os.fdopen(file_fd, "rb") as file:
            file_fd = None
            content = file.read()
            after = os.fstat(file.fileno())
        stable_fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
            raise GuardError("protected-content file changed during verification")
        mode = "100755" if before.st_mode & stat.S_IXUSR else "100644"
        return mode, "blob", content
    except OSError as exc:
        if exc.errno in {errno.ENOENT, errno.ELOOP, errno.ENOTDIR}:
            return None if _physically_absent(path) else ("INVALID", "nonregular", b"")
        raise GuardError("protected-content verification could not read a tracked file") from None
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory is not None:
            os.close(directory)


def _physically_absent(path: str) -> bool:
    """Absence never includes symlinks, non-directory parents or special files."""
    current = REPO_ROOT
    for part in path.split("/"):
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return True
        except OSError:
            return False
        if stat.S_ISLNK(info.st_mode):
            return False
        if current != REPO_ROOT / path and not stat.S_ISDIR(info.st_mode):
            return False
    return False


def _cleanup_authority_known() -> bool:
    """Read historical metadata at the pinned source commit, never current docs."""
    try:
        raw = _guard_git_bytes(["ls-tree", "-r", "--full-tree", "-z", _CLEANUP_AUTHORITY_COMMIT])
    except GuardError:
        return False
    found = {}
    for item in raw.split(b"\0"):
        if not item:
            continue
        metadata, path = item.split(b"\t", 1)
        path = path.decode("utf-8", "surrogateescape")
        if path in _CLEANUP_AUTHORITY_PINS:
            mode, kind, oid = metadata.decode("ascii").split()
            if (mode, kind) != ("100644", "blob"):
                return False
            found[path] = oid
    return found == _CLEANUP_AUTHORITY_PINS


def _regular_entry(entry) -> bool:
    return entry is not None and entry[0] in {"100644", "100755"} and entry[1] == "blob"


def _log_text(content: bytes) -> bool:
    if b"\0" in content:
        return False
    try:
        content.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _protected_transition(before: dict, after: dict, cfg: dict, blob_cache: dict, cleanup_authority: bool = False) -> list[str]:
    def content(entry):
        value = entry[2]
        if isinstance(value, bytes):
            return value
        if value not in blob_cache:
            blob_cache[value] = _guard_git_bytes(["cat-file", "blob", value])
        return blob_cache[value]

    def append_proof(path):
        old, new = before[path], after[path]
        if not _regular_entry(old) or not _regular_entry(new) or old[:2] != new[:2]:
            return False
        old_bytes, new_bytes = content(old), content(new)
        return _log_text(old_bytes) and _log_text(new_bytes) and new_bytes.startswith(old_bytes)

    def receipt_valid(state):
        entry = state.get(_CLEANUP_RECEIPT_PATH)
        return (cleanup_authority and entry is not None and entry[:2] == ("100644", "blob")
                and hashlib.sha256(content(entry)).hexdigest() == _CLEANUP_RECEIPT_SHA256)

    def original_readiness(entry):
        if entry is None or entry[:2] != ("100644", "blob"):
            return False
        data = content(entry)
        oid = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        return (oid == _CLEANUP_READINESS_BLOB_SHA1 and len(data) == _CLEANUP_READINESS_BYTES
                and hashlib.sha256(data).hexdigest() == _CLEANUP_READINESS_SHA256)

    records, invalid = [], []
    for state in (before, after):
        receipt = state.get(_CLEANUP_RECEIPT_PATH)
        readiness = state.get(_CLEANUP_READINESS_PATH)
        if any(entry is not None and not _regular_entry(entry) for entry in (receipt, readiness)):
            invalid.append("cleanup paths require regular leaf artifacts or exact absence, without structural obstruction")
        if receipt is not None and (not receipt_valid(state) or (readiness is not None and not original_readiness(readiness))):
            invalid.append("cleanup requires the exact pinned regular authority receipt and legacy preimage or absence")
        if cleanup_authority and readiness is None and not receipt_valid(state):
            invalid.append("removed readiness requires its pinned metadata receipt in every state")
        for path, entry in state.items():
            if path != _CLEANUP_READINESS_PATH and _regular_entry(entry):
                value = entry[2]
                # Blob aliases in trees/index and their physical worktree contents.
                if value == _CLEANUP_READINESS_BLOB_SHA1 or (isinstance(value, bytes) and original_readiness(entry)):
                    invalid.append("cleanup cannot relocate the protected readiness payload")
    if before.get(_CLEANUP_RECEIPT_PATH) is not None and after.get(_CLEANUP_RECEIPT_PATH) is None:
        invalid.append("cleanup authority receipt cannot be removed")
    if (before.get(_CLEANUP_READINESS_PATH) is None and receipt_valid(before)
            and after.get(_CLEANUP_READINESS_PATH) is not None):
        invalid.append("removed readiness cannot be reintroduced")
    for path in sorted(before.keys() | after.keys()):
        old, new = before.get(path), after.get(path)
        if old == new:
            continue
        if old is None:
            code = "A"
            if not _regular_entry(new) or (
                path in cfg["append_only_exact_paths"] and not _log_text(content(new))
            ):
                invalid.append("protected repository addition requires a regular artifact of the configured type")
        elif new is None:
            if path == _CLEANUP_READINESS_PATH and original_readiness(old) and receipt_valid(after):
                continue
            code = "D"
        elif old[:2] != new[:2] or not _regular_entry(old) or not _regular_entry(new):
            code = "T"
        elif content(old) == content(new):
            continue
        else:
            code = "M"
        records.append((code, [path]))
    return invalid + classify_diff(records, cfg, append_proof)


def protected_repository_violations(comparison: str, head: str, cfg: dict) -> list[str]:
    """Verify every committed parent edge, final tree, index, and tracked files."""
    trees, blobs = {}, {}
    cleanup_authority = _cleanup_authority_known()
    def tree(oid):
        if oid not in trees:
            trees[oid] = _protected_tree(oid, cfg)
        return trees[oid]
    violations = _protected_transition(tree(comparison), tree(head), cfg, blobs, cleanup_authority)
    history = _guard_git_bytes([
        "rev-list", "--reverse", "--topo-order", "--parents", f"{comparison}..{head}", "--",
    ])
    for line in history.splitlines():
        commits = line.decode("ascii").split()
        if not commits or not all(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid) for oid in commits):
            raise GuardError("invalid protected-content history metadata")
        commit, parents = commits[0], commits[1:]
        for parent in parents:
            violations.extend(_protected_transition(tree(parent), tree(commit), cfg, blobs, cleanup_authority))
        if not parents:
            violations.extend(_protected_transition({}, tree(commit), cfg, blobs, cleanup_authority))
    index = _protected_index(cfg)
    violations.extend(_protected_transition(tree(head), index, cfg, blobs, cleanup_authority))
    worktree = {}
    for path in tree(head).keys() | index.keys() | {_CLEANUP_READINESS_PATH, _CLEANUP_RECEIPT_PATH}:
        entry = _protected_worktree_entry(path)
        if entry is not None:
            worktree[path] = entry
    violations.extend(_protected_transition(index, worktree, cfg, blobs, cleanup_authority))
    return list(dict.fromkeys(violations))


def validate_mode(cfg: dict) -> str:
    p = REPO_ROOT / cfg["autonomy_mode_file"]
    mode = p.read_text(encoding="utf-8").strip()
    if mode not in cfg["allowed_modes"]:
        raise GuardError(f"invalid AUTONOMY_MODE={mode!r}")
    return mode


def cmd_diff(base: str) -> int:
    cfg = load_config()
    mode = validate_mode(cfg)
    comparison, head = resolve_comparison(base)
    records = parse_name_status(git_name_status(comparison, head=head))
    violations = protected_repository_violations(comparison, head, cfg)
    privacy_violations = device_actual_violations(comparison)
    if privacy_violations:
        # Other rule diagnostics include paths; a private export's filename may
        # itself carry account/holdings information. Preserve failure counts.
        violations = ["protected repository artifact changed"] * len(violations)
    violations.extend(privacy_violations)
    print(json.dumps({
        "mode": mode,
        "records": len(records),
        "violations": violations,
        "device_actual_privacy_guard": "FAIL" if privacy_violations else "PASS",
        "gate_a_repository_guard": "PASS" if not violations else "FAIL",
    }, ensure_ascii=False, indent=2))
    return 1 if violations else 0


def cmd_mode() -> int:
    cfg = load_config()
    mode = validate_mode(cfg)
    print(mode)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_diff = sub.add_parser("diff")
    p_diff.add_argument("--base", required=True)
    sub.add_parser("mode")
    args = parser.parse_args()
    try:
        if args.cmd == "diff":
            return cmd_diff(args.base)
        return cmd_mode()
    except (GuardError, OSError, json.JSONDecodeError) as exc:
        print(f"AUTONOMY_GUARD_FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
