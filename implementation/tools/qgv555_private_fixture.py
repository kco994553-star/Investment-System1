#!/usr/bin/env python3
"""A staged SYNTHETIC QGV 555 delivery for tests (owner 2026-11-14, DC-49): Codex #537's own synthetic delivery
(tests/fixtures/qgv555, made by qgv_555_delivery.artifacts on qgv_555.fixture()) laid out like the private r2 handoff (r2-<scope>/
plus inputs-v3/ with a job pinning the two input files) and staged with tools/stage_private_qgv555.py into <out>/data.

  python implementation/tools/qgv555_private_fixture.py --out <new directory> [--scope operating504]
prints the staged directory. Synthetic only; nothing is fetched."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import stage_private_qgv555 as stage  # noqa: E402
from investment_system.research import qgv_555  # noqa: E402

FIX = ROOT / 'tests' / 'fixtures' / 'qgv555'
PRODUCER, HANDOFF, HM = 'a' * 40, 'b' * 8 + ':handoffs/synthetic', 'c' * 64


def layout(out: Path, scope: str = 'operating504') -> tuple[Path, str]:
    root = out / 'extracted'
    src = root / ('r2-' + scope)
    src.mkdir(parents=True)
    manifest = json.loads((FIX / 'manifest.json').read_bytes())
    for f in manifest['files']:
        shutil.copyfile(FIX / f['path'], src / f['path'])
    shutil.copyfile(FIX / 'manifest.json', src / 'manifest.json')
    inputs = root / 'inputs-v3'
    inputs.mkdir()
    e, ref = qgv_555.fixture()
    job = {}
    for side, name, obj in (('evaluation', 'operating.json', e), ('reference', 'operating_reference.json', ref)):
        b = json.dumps(obj).encode()
        (inputs / name).write_bytes(b)
        job[side] = {'path': '/elsewhere/' + name, 'sha256': hashlib.sha256(b).hexdigest(), 'size': len(b)}
    (inputs / stage.SCOPES[scope]).write_text(json.dumps(job))
    return root, hashlib.sha256((src / 'manifest.json').read_bytes()).hexdigest()


def build(out: Path, scope: str = 'operating504') -> Path:
    root, ms = layout(out, scope)
    files, receipt = stage.check(root, scope, ms, producer_sha=PRODUCER, handoff=HANDOFF, handoff_manifest_sha256=HM)
    return stage.stage(out / 'data', scope, files, receipt)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--scope', default='operating504', choices=sorted(stage.SCOPES))
    a = ap.parse_args()
    print(build(a.out, a.scope))
