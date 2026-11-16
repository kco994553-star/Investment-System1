#!/usr/bin/env python3
"""Hash-pinned, network-free company ownership projection. No collection or publication."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from investment_system.research.company_ownership import (  # noqa: E402
    MAX_VIEW_BYTES, company_view, json_bytes, normalize_packet,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--input-sha256", required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True, help="Files named by their exact SHA-256; no URL fetching")
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--valid-on", required=True)
    parser.add_argument("--knowledge-at", required=True)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--relationship-type", choices=("OWNERSHIP", "PARENT_SUBSIDIARY"))
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args(argv)
    staging = None
    try:
        out = args.output_dir.resolve()
        if out.exists():
            raise ValueError("OUTPUT_EXISTS")
        raw = args.input.read_bytes()
        if hashlib.sha256(raw).hexdigest() != args.input_sha256:
            raise ValueError("INPUT_HASH")
        packet = json.loads(raw)
        if args.synthetic != (packet.get("data_kind") == "SYNTHETIC"):
            raise ValueError("DATA_KIND")
        if not args.synthetic and any((parent / ".git").exists() for parent in (out, *out.parents)):
            raise ValueError("PRIVATE_OUTPUT_INSIDE_CHECKOUT")
        artifacts = {}
        for item in packet["evidence"]:
            sha = item["artifact_hash"]
            if not isinstance(sha, str) or re.fullmatch(r"[a-f0-9]{64}", sha) is None:
                raise ValueError("ARTIFACT_HASH")
            artifacts[sha] = (args.artifacts / sha).read_bytes()
        identity = args.identity.read_bytes()
        normalized = normalize_packet(packet, identity, artifacts)
        view = company_view(normalized, entity_id=args.entity_id, valid_on=args.valid_on,
                            knowledge_at=args.knowledge_at, generated_at=args.generated_at,
                            relationship_type=args.relationship_type)
        payloads = {"view.json": json_bytes(view), "normalized.json": json_bytes(normalized)}
        manifest = {"schema_version": "company-ownership-manifest/1", "input_sha256": args.input_sha256,
                    "identity_sha256": hashlib.sha256(identity).hexdigest(),
                    "artifacts": sorted(artifacts), "generated_at": args.generated_at,
                    "files": {name: {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)} for name, body in payloads.items()}}
        payloads["manifest.json"] = json_bytes(manifest)
        if any(len(body) > MAX_VIEW_BYTES for body in payloads.values()):
            raise ValueError("OUTPUT_SIZE")
        out.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".ownership-", dir=out.parent))
        for name, body in payloads.items():
            target = staging / name
            target.write_bytes(body)
            if target.read_bytes() != body:
                raise ValueError("WRITE_VERIFY")
        # Fail on an existing destination including an empty directory. No old good copy is overwritten.
        out.mkdir()
        for name in payloads:
            os.replace(staging / name, out / name)
        staging.rmdir()
        staging = None
        print(json.dumps({"status": "COMPLETE", "schema_version": view["schema_version"], "counts": view["counts"]}))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        # Exceptions never print paths, raw documents or untrusted input values.
        code = str(error) if isinstance(error, ValueError) and re.fullmatch(r"[A-Z_]+", str(error)) else type(error).__name__
        print(json.dumps({"status": "FAILED", "error": code}), file=sys.stderr)
        return 1
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
