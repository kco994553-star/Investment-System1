"""Fail closed on the GSQ-010 price-free public Pages artifact.

Byte/canonical hashes protect reviewed assets. The independent public bundle
contract rejects legacy ranks, membership order, prices and arbitrary nested
values even if a legacy or modified payload hash is repinned. Private device
quotation code is an asset, never permission to publish device data.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import tarfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from investment_system.public_price_boundary import require_public_bundle, require_public_catalog, PublicPriceBoundaryError


from investment_system.product.sec_m2_candidates import require_public_candidates

# Reviewed public output, not hashes derived from potentially changed inputs.
APPROVED_SHA256 = {
    "private-trades.js": "44f63bb92a8b7614734478bf7997919d4a9e859d374f6091201d4e9955c714b2",
    "technical-chart.js": "64b581fd186cdcb39f31def58412052dfa777dc2920a4f2432c1842b19c65eb8",
    "chart-indicators.js": "30cf6571f32c0496acd247099feb5f71fce0acf8870dcd78781018b872291fcc",
    "device-backup.js": "d8229be35d744153ecd5cda57ca700aac080297bd3c80d7f07d076ba35d63323",
    "sec-m2-candidates.json": "3499f945e45bdc61b627148755cb017008568e49d6cc1276c9a2b780c412b816",
    "actual-catalog.json": "f73548d955a722e91e732074cfc3686e2c1e5dc70784b4134e9294ba46e7256e",
    "app-config.js": "e69b8fe9fe492969a765a66f33170684e1d5fd0f40f47434cdb361a4b50a0361",
    "app.js": "740ae9fa5d9f9abc74f7757b91fee2eeea8bd7d99d524730b0b392566e3154e8",
    "data.json": "7afba9f30d4322ae67593cba3866db78d0d0f7822c32e2eff375497156b5b7e1",
    "device-actual.css": "319b0aa07e9f47f19cadaae773fa555a65d9c52f3c28320604e382872fa8d4b9",
    "device-actual.js": "05770dd8e99d40c43d320970549f7f91f8c93bd77496553c593172ab5a1f7407",
    "device-market.js": "4a4517d31dbdeb95af45f6f12b15364711faf8eafdde4723c4874014da3baddc",
    "entities.json": "8a452006b4821bb0c1fed05de17a2a81da7457fe546f6d9161a1d8b4bda16ac2",
    "entity-search.js": "0e6e237eff6aa4b3dec95550c52fcfa70e355ed4a77558b9693d4fdffb3d2b3a",
    "google-sheet-core.js": "9825b81e6f81c87c2608979b533f2ad5e7bfba63c4e88d6ce292940958be624c",
    "google-sheet-quotes.js": "db349214e345c7e67a030b61aa70c8dc84d0f98a831acf40a71bdc4befb118c1",
    "google-sheet-quotes.css": "5e37d704c69891893a8ca81a9a41d7f268696be210774609cc9c1d7ac7db5237",
    "index.html": "52f5b901cebfd68a77d99a29ae444f136140b14a917c0dd64fde404fdf8a02d6",
    "locale.js": "0e27312c7885dd1edbaf5c5eed939ba4b642695e5541653a21c786dcff9089fc",
    "private-history.css": "c3c0eb9e71aa52ae9acf79e9e2b0a7aeefdf3a0138ff2856a2562a029c11ad52",
    "private-history.js": "54cd4ecff5691f60edc32207817559eb9ee7740f631f2742aa6666aef4acab93",
    "research.html": "ec9f6b90a4dd490959c244e6716a948c7cfae2fe5f060c56c19e6d5c1469763e",
    "style.css": "035930c2bdeb760f768562f8a9fb6b7aec703bc4663392b8f91db5796145b56e",
}
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 4 * 1024 * 1024
MAX_ENTRIES = 64
MAX_JSON_DEPTH = 64

SENSITIVE_KEYS = frozenset({
    "rank", "marketcaprank", "rankislowerbound", "vscore", "totalscore",
    "periodreturn", "realizedreturn", "dailyreturn", "performance",
    "quantity", "quantities", "averagecost", "avgcost", "amount", "cash",
    "balance", "account", "accountnumber", "accountid", "marketvalue",
    "money", "moneyvalue", "mcap", "cutoffmcap", "marketcap",
    "marketcapitalization", "costbasis", "purchaseprice", "networth",
    "holdings", "positions", "actualholdings", "investedamount",
    "totalcost", "cost", "price", "valueamount", "cashbalance",
    "spreadsheetid", "spreadsheeturl", "accesstoken", "refreshtoken", "clientsecret",
})
SECRET_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9_])ya29\.[A-Za-z0-9._~-]+"),
    re.compile(r"https://docs\.google\.com/spreadsheets/(?:u/\d+/)?d/[A-Za-z0-9_-]{20,100}"),
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    re.compile(
        r"(?i)(?<!\w)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|"
        r"auth[_-]?token|client[_-]?secret|private[_-]?key|password|secret|token)"
        r"\s*[\"']?\s*[:=]\s*[\"'][^\"'\r\n]+[\"']"
    ),
    re.compile(r"(?i)authorization\s*:\s*[\"']?bearer\s+[a-z0-9._~+/=-]{8,}"),
)


def _receipt(violations: Counter, files_scanned: int) -> dict:
    return {
        "pages_artifact_guard": "FAIL" if violations else "PASS",
        "files_scanned": files_scanned,
        "violations": dict(sorted(violations.items())),
    }


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("nonfinite JSON number")


def _populated(value: object) -> bool:
    # Zero and false are populated. Container contents need not be numeric.
    return value is not None and value != "" and value != [] and value != {}


def _inspect_json(value: object, violations: Counter, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ValueError("JSON nesting limit")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite JSON number")
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
            if normalized in SENSITIVE_KEYS and _populated(child):
                violations["sensitive_json_fields"] += 1
            if key in {"schema", "schema_version"} and isinstance(child, str):
                if re.search(r"device[-_]actual[-_](?:holdings|export)(?:/|$)", child, re.I):
                    violations["private_device_schema"] += 1
            _inspect_json(child, violations, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _inspect_json(child, violations, depth + 1)


def _check_payload(name: str, payload: bytes, violations: Counter) -> None:
    try:
        text = payload.decode("utf-8", errors="strict")
        if any(ord(character) < 32 and character not in "\t\n\r" for character in text):
            raise ValueError("binary control character")
        violations["secret_patterns"] += sum(len(pattern.findall(text)) for pattern in SECRET_PATTERNS)
        if not violations["secret_patterns"]:
            del violations["secret_patterns"]
        if name.endswith(".json"):
            value = json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
            _inspect_json(value, violations)
            if name == "sec-m2-candidates.json":
                try:
                    require_public_candidates(value)
                except ValueError:
                    violations["m2_candidate_boundary"] += 1
            if name in {'data.json', 'entities.json', 'actual-catalog.json'}:
                try:
                    if name == 'data.json':
                        require_public_bundle(value)
                    else:
                        require_public_catalog(name, value)
                except PublicPriceBoundaryError:
                    violations['public_price_boundary'] += 1
            payload = json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
            ).encode("utf-8", errors="strict")
        if hashlib.sha256(payload).hexdigest() != APPROVED_SHA256[name]:
            violations["unapproved_content"] += 1
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        violations["invalid_format"] += 1


def _read_regular(fd: int, limit: int, violations: Counter) -> bytes | None:
    metadata = os.fstat(fd)
    if not stat.S_ISREG(metadata.st_mode):
        violations["nonregular_entries"] += 1
        return None
    if metadata.st_size > limit:
        violations["oversized_files"] += 1
        return None
    with os.fdopen(fd, "rb", closefd=False) as handle:
        payload = handle.read(limit + 1)
    if len(payload) > limit:
        violations["oversized_files"] += 1
        return None
    return payload


def scan_artifact(artifact_dir: str | Path) -> dict:
    """Return only category counts; never return artifact paths or contents."""
    violations = Counter()
    files_scanned = 0
    seen = set()
    try:
        # Directory fd and no-follow child opens also prevent check/open races.
        root_fd = os.open(artifact_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with os.scandir(root_fd) as entries:
                for index, entry in enumerate(entries):
                    if index >= MAX_ENTRIES:
                        violations["excessive_entries"] += 1
                        break
                    name = entry.name
                    if name not in APPROVED_SHA256:
                        violations["unexpected_entries"] += 1
                    else:
                        seen.add(name)
                    if not entry.is_file(follow_symlinks=False):
                        violations["nonregular_entries"] += 1
                        continue
                    if name not in APPROVED_SHA256:
                        continue
                    try:
                        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
                        try:
                            payload = _read_regular(fd, MAX_FILE_BYTES, violations)
                        finally:
                            os.close(fd)
                        if payload is not None:
                            files_scanned += 1
                            _check_payload(name, payload, violations)
                    except OSError:
                        violations["unreadable_entries"] += 1
        finally:
            os.close(root_fd)
        missing = len(APPROVED_SHA256.keys() - seen)
        if missing:
            violations["missing_files"] += missing
    except (OSError, ValueError):
        violations["invalid_artifact_directory"] += 1
    return _receipt(violations, files_scanned)


def _plain_tar_layout(payload: bytes, violations: Counter) -> bool:
    """Inspect physical headers too: tarfile otherwise hides extension records.

    The upload step must set TAR_OPTIONS='--owner=0 --group=0 --numeric-owner'.
    Only ordinary GNU/USTAR headers, zero padding and the zero EOF trailer are
    accepted. Owner names may also be 'root' for equivalent local GNU fixtures.
    """
    block_size = tarfile.BLOCKSIZE
    if len(payload) % block_size or len(payload) < block_size * 2:
        violations["invalid_archive"] += 1
        return False
    offset = 0
    for _ in range(MAX_ENTRIES + 1):
        block = payload[offset:offset + block_size]
        if block == bytes(block_size):
            if len(payload) - offset < block_size * 2 or any(payload[offset:]):
                violations["invalid_archive"] += 1
                return False
            return True
        if len(block) != block_size:
            violations["invalid_archive"] += 1
            return False
        member = tarfile.TarInfo.frombuf(block, encoding="utf-8", errors="strict")
        if member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE}:
            violations["nonregular_entries"] += 1
            if member.type in {tarfile.XHDTYPE, tarfile.XGLTYPE,
                               tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK}:
                violations["unsupported_archive_metadata"] += 1
            return False
        if member.type == tarfile.DIRTYPE and member.name not in {".", "./"}:
            violations["nonregular_entries"] += 1
            return False
        name_field = block[:100]
        name_bytes = name_field.split(b"\0", 1)[0]
        owner_fields = ((265, member.uname), (297, member.gname))
        metadata_valid = (
            block[257:265] in {b"ustar  \0", b"ustar\00000"}
            and member.uid == 0 and member.gid == 0
            and member.devmajor == 0 and member.devminor == 0
            and member.mode in {
                0o600, 0o644, 0o700, 0o755,
                stat.S_IFREG | 0o600, stat.S_IFREG | 0o644,
                stat.S_IFDIR | 0o700, stat.S_IFDIR | 0o755,
            }
            and not member.linkname and block[157:257] == bytes(100)
            and name_field == name_bytes.ljust(100, b"\0")
            and not any(block[345:])
        )
        for start, owner in owner_fields:
            metadata_valid = metadata_valid and owner in {"", "root"}
            metadata_valid = metadata_valid and block[start:start + 32] == owner.encode().ljust(32, b"\0")
        for start, length in ((100, 8), (108, 8), (116, 8), (124, 12),
                              (136, 12), (148, 8), (329, 8), (337, 8)):
            field = block[start:start + length]
            number, separator, padding = field.partition(b"\0")
            # No ignored bytes after a terminator; GNU checksum ends NUL-space.
            metadata_valid = metadata_valid and bool(re.fullmatch(rb" *[0-7]* *", number))
            metadata_valid = metadata_valid and (not separator or all(byte in b" \0" for byte in padding))
        if not metadata_valid:
            violations["unsupported_archive_metadata"] += 1
            return False
        if member.size < 0 or member.size > MAX_FILE_BYTES:
            violations["oversized_files"] += 1
            return False
        if member.type == tarfile.DIRTYPE and member.size:
            violations["invalid_archive"] += 1
            return False
        data_end = offset + block_size + member.size
        next_offset = ((data_end + block_size - 1) // block_size) * block_size
        if next_offset > len(payload) or any(payload[data_end:next_offset]):
            violations["invalid_archive"] += 1
            return False
        offset = next_offset
    violations["excessive_entries"] += 1
    return False


def validate_pages_tar(archive_path: str | Path) -> dict:
    """Check a raw GitHub Pages artifact.tar in place, without extracting it."""
    violations = Counter()
    files_scanned = 0
    seen = set()
    root_seen = False
    try:
        fd = os.open(archive_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            metadata = os.fstat(fd)
            if not stat.S_ISREG(metadata.st_mode):
                violations["nonregular_entries"] += 1
                return _receipt(violations, files_scanned)
            if metadata.st_size > MAX_ARCHIVE_BYTES:
                violations["oversized_archive"] += 1
                return _receipt(violations, files_scanned)
            with os.fdopen(fd, "rb", closefd=False) as handle:
                payload = handle.read(MAX_ARCHIVE_BYTES + 1)
                if len(payload) > MAX_ARCHIVE_BYTES:
                    violations["oversized_archive"] += 1
                    return _receipt(violations, files_scanned)
                if not _plain_tar_layout(payload, violations):
                    return _receipt(violations, files_scanned)
                # Pages upload uses an uncompressed tar. Compression and PAX
                # metadata are outside the approved transport shape.
                with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
                    for index, member in enumerate(archive):
                        if index >= MAX_ENTRIES:
                            violations["excessive_entries"] += 1
                            break
                        if archive.pax_headers or member.pax_headers:
                            violations["unsupported_archive_metadata"] += 1
                        if member.name in {".", "./"} and member.type == tarfile.DIRTYPE:
                            if root_seen:
                                violations["duplicate_entries"] += 1
                            root_seen = True
                            continue
                        name = member.name[2:] if member.name.startswith("./") else member.name
                        if name not in APPROVED_SHA256:
                            violations["unexpected_entries"] += 1
                        elif name in seen:
                            violations["duplicate_entries"] += 1
                        else:
                            seen.add(name)
                        if member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE}:
                            violations["nonregular_entries"] += 1
                            continue
                        if name not in APPROVED_SHA256:
                            continue
                        if member.size < 0 or member.size > MAX_FILE_BYTES:
                            violations["oversized_files"] += 1
                            continue
                        source = archive.extractfile(member)
                        if source is None:
                            violations["invalid_archive"] += 1
                            continue
                        with source:
                            payload = source.read(MAX_FILE_BYTES + 1)
                        if len(payload) != member.size:
                            violations["invalid_archive"] += 1
                            continue
                        files_scanned += 1
                        _check_payload(name, payload, violations)
        finally:
            os.close(fd)
        missing = len(APPROVED_SHA256.keys() - seen)
        if missing:
            violations["missing_files"] += missing
    except (OSError, ValueError, tarfile.TarError, UnicodeError, RecursionError, OverflowError):
        violations["invalid_archive"] += 1
    return _receipt(violations, files_scanned)


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        print(json.dumps(_receipt(Counter({"invalid_arguments": 1}), 0), sort_keys=True))
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> int:
    parser = _SafeArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--artifact-dir")
    inputs.add_argument("--pages-artifact")
    args = parser.parse_args(argv)
    receipt = scan_artifact(args.artifact_dir) if args.artifact_dir else validate_pages_tar(args.pages_artifact)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["pages_artifact_guard"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
