#!/usr/bin/env python3
"""Fail-closed repository guard for Autonomous Execution SSoT v1.1 Gate A.

This guard does not grant autonomy by itself. It enforces:
- immutable Frozen artifacts cannot be modified/deleted/renamed;
- append-only records cannot rewrite or delete existing bytes;
- AUTONOMY_MODE is a single explicit state;
- operating values stay within the adopted CDR-024 configuration.
- populated user-device holdings, market exports and credentials cannot enter tracked content.

HG-02 still requires GitHub-side branch/ruleset enforcement.
"""

from __future__ import annotations

import argparse
import csv
import errno
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
}
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

    def visit(node: object) -> None:
        nonlocal populated_holdings, populated_market
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

    visit(value)
    marked = any(_actual_marker(fields) for fields in mappings)
    market_marked = named_market_export or any(_market_marker(fields) for fields in mappings)
    return (
        any(_credential_fields(fields) for fields in mappings)
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
    out: list[tuple[str, list[str]]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        paths = parts[1:]
        if not paths:
            raise GuardError(f"invalid diff record: {line!r}")
        out.append((status, paths))
    return out


def _touches(path: str, cfg: dict) -> bool:
    if path in cfg["immutable_exact_paths"]:
        return True
    if path in cfg["append_only_exact_paths"]:
        return True
    return any(path.startswith(prefix) for prefix in cfg["append_only_prefixes"])


def classify_diff(records: list[tuple[str, list[str]]], cfg: dict) -> list[str]:
    violations: list[str] = []
    immutable = set(cfg["immutable_exact_paths"])
    append_files = set(cfg["append_only_exact_paths"])
    prefixes = tuple(cfg["append_only_prefixes"])

    for status, paths in records:
        code = status[0]
        old_path = paths[0]
        new_path = paths[-1]

        if old_path in immutable or new_path in immutable:
            if code in {"M", "D", "R", "C", "T"}:
                violations.append(f"immutable path changed: {status} {paths}")
            continue

        append_hit = (
            old_path in append_files
            or new_path in append_files
            or old_path.startswith(prefixes)
            or new_path.startswith(prefixes)
        )
        if append_hit and code in {"M", "D", "R", "C", "T"}:
            violations.append(f"append-only existing content changed: {status} {paths}")

    return violations


def git_name_status(base: str) -> str:
    proc = subprocess.run(
        ["git", "diff", "--name-status", f"{base}...HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode:
        raise GuardError(proc.stderr.strip() or "git diff failed")
    return proc.stdout


def validate_mode(cfg: dict) -> str:
    p = REPO_ROOT / cfg["autonomy_mode_file"]
    mode = p.read_text(encoding="utf-8").strip()
    if mode not in cfg["allowed_modes"]:
        raise GuardError(f"invalid AUTONOMY_MODE={mode!r}")
    return mode


def cmd_diff(base: str) -> int:
    cfg = load_config()
    mode = validate_mode(cfg)
    records = parse_name_status(git_name_status(base))
    violations = classify_diff(records, cfg)
    privacy_violations = device_actual_violations(base)
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
