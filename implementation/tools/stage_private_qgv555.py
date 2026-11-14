#!/usr/bin/env python3
"""Stage one scope of Codex #537's saved QGV 555 delivery (qgv-555-delivery/1) for the owner-checked private Worker (owner 2026-11-14,
「#537 최신 미리보기·Top500 표시 계약 인수」 §3; DC-49).

The private Worker serves /kis/classification?part=q555_stage|q555_manifest|q555_index&scope=<scope> and
?part=q555_file&scope=<scope>&name=<member> from the data branch of the private repository, under classification/q555/<scope>/
(implementation/worker/src/index.js). This tool copies Codex's saved delivery there BYTE FOR BYTE after checking it. It computes no
score, re-serializes nothing and fetches nothing. It is the stored-result path; it never runs a recalculation.

  python implementation/tools/stage_private_qgv555.py --extracted <archive root: r2-<scope>/ or <scope>/, and inputs-v3/> --scope operating504|held1057 \
      --manifest-sha256 <the outside <scope>-manifest.json SHA-256 the handoff names> --data-dir <private data branch checkout> \
      --producer-sha <execution commit> --handoff <commit>:<path> --handoff-manifest-sha256 <handoff-manifest.json SHA-256>

Checks, all before anything is written:
- r2-<scope>/manifest.json's bytes have --manifest-sha256 (the producer's pin); schema qgv-555-delivery-manifest/1, PRIVATE;
- the directory holds the manifest's members, index.json among them (each ≤ 2 MiB, the Worker's bound, with the manifest's size and
  SHA-256 byte for byte), and manifest.json; nothing else is copied (full results, verification notes and inputs stay out);
- independent anchors (owner §1): the evaluation and reference INPUT files named by inputs-v3/<scope>-job.json have the job's pinned
  SHA-256 and size; expected_evaluation = identity(evaluation input) and expected_references[model] = identity(reference input) are
  computed here from those inputs (Codex research.qgv_555.identity), never read from the delivery;
- Codex research.qgv_555_delivery.validate(files, manifest_sha256, expected_evaluation, expected_references) passes: member hashes,
  the evaluation anchor, each model's reference anchor, SHARDED group files (count, duplicates), group member hashes and bin counts;
- index models are exactly U1-555 / S1-555 with their model ids;
- --data-dir is outside this public repository.
classification/q555/<scope>/ is replaced whole or not at all (written beside it, then swapped); on any failure the existing copy
stays. stage.json is Main's receipt (qgv-555-stage/1): pins, the two expected anchors, counts, producer and handoff identity.
Output: one line with counts, sizes and hashes (no content).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / 'implementation' / 'src'))
from investment_system.research import qgv_555, qgv_555_delivery  # noqa: E402

MAX_BYTES = 2 * 1024 * 1024
SCOPES = {'operating504': 'operating504-job.json', 'held1057': 'held1057-job.json'}
MODELS = {'U1-555': 'unified-555/0.1.0', 'S1-555': 'sector-555/0.1.0'}
MEMBER = re.compile(r'^(index|group-index-\d{4}|(?:U1|S1)-555-detail-\d{4}|distribution-[0-9a-f]{24}-\d{4})\.json$')
STAGE_SCHEMA = 'qgv-555-stage/1'
HEX = re.compile(r'^[0-9a-f]{64}$')


class Refused(Exception):
    pass


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def check(extracted: Path, scope: str, manifest_sha256: str, *, producer_sha: str, handoff: str, handoff_manifest_sha256: str,
          job_dir: Path | None = None):
    """Every check; returns (members {name: bytes}, receipt). Writes nothing."""
    if scope not in SCOPES:
        raise Refused('SCOPE')
    for v in (manifest_sha256, handoff_manifest_sha256):
        if not HEX.match(v or ''):
            raise Refused('PIN_FORMAT')
    if not re.match(r'^[0-9a-f]{40}$', producer_sha or '') or not re.match(r'^[0-9a-f]{7,40}:[A-Za-z0-9._/-]+$', handoff or ''):
        raise Refused('IDENTITY_FORMAT')
    # r2 archives hold r2-<scope>/; later deliveries (FY debt, raw c0a8bf51) hold <scope>/. Exactly one must exist.
    found = [d for d in (extracted / ('r2-' + scope), extracted / scope) if d.is_dir()]
    if len(found) != 1 or (len(set(p.resolve() for p in found)) != len(found)):
        raise Refused('SCOPE_DIRECTORY')
    src = found[0]
    mbytes = (src / 'manifest.json').read_bytes()
    if sha(mbytes) != manifest_sha256:
        raise Refused('MANIFEST_PIN')
    manifest = json.loads(mbytes)
    if manifest.get('schema_version') != 'qgv-555-delivery-manifest/1' or manifest.get('data_kind') not in ('PRIVATE', 'SYNTHETIC'):
        raise Refused('MANIFEST_SCHEMA')
    names = [f['path'] for f in manifest['files']]
    if len(set(names)) != len(names) or not all(MEMBER.match(n) for n in names) or 'index.json' not in names:
        raise Refused('MEMBER_NAME')
    members = {}
    for f in manifest['files']:
        b = (src / f['path']).read_bytes()
        if len(b) != f['size'] or len(b) > MAX_BYTES or sha(b) != f['sha256']:
            raise Refused('MEMBER_BYTES:' + f['path'])
        members[f['path']] = b
    ibytes = members['index.json']
    index = json.loads(ibytes)
    if index.get('schema_version') != 'qgv-555-delivery/1' or {k: v['model_id'] for k, v in index['models'].items()} != MODELS:
        raise Refused('INDEX_MODELS')
    # Independent anchors: from the input files themselves (pinned by the job), never from the delivery.
    jobs = job_dir or (extracted / 'inputs-v3')
    job = json.loads((jobs / SCOPES[scope]).read_bytes())
    loaded = {}
    for side in ('evaluation', 'reference'):
        pin = job[side]
        b = (jobs / Path(pin['path']).name).read_bytes()
        if len(b) != pin['size'] or sha(b) != pin['sha256']:
            raise Refused('INPUT_PIN:' + side)
        loaded[side] = json.loads(b)
    expected_evaluation = qgv_555.identity(loaded['evaluation'])
    expected_references = {k: qgv_555.identity(loaded['reference']) for k in MODELS}
    files = {n: json.loads(b) for n, b in members.items()}
    files['manifest.json'] = manifest
    try:
        report = qgv_555_delivery.validate(files, manifest_sha256=sha(qgv_555_delivery.json_bytes(manifest)),
                                           expected_evaluation=expected_evaluation, expected_references=expected_references)
    except (ValueError, KeyError, TypeError) as exc:
        raise Refused('DELIVERY:' + str(exc).split(':')[0]) from None
    receipt = {'schema_version': STAGE_SCHEMA, 'scope': scope, 'data_kind': manifest['data_kind'], 'visibility': 'AUTHENTICATED_RESEARCH',
               'stored_result_only': True, 'producer_sha': producer_sha, 'handoff': handoff, 'handoff_manifest_sha256': handoff_manifest_sha256,
               'manifest_sha256': manifest_sha256, 'index_sha256': sha(ibytes), 'files': len(members), 'bytes': sum(map(len, members.values())),
               'groups': report['groups'], 'expected_evaluation': expected_evaluation, 'expected_references': expected_references,
               'input_pins': {side: {'sha256': job[side]['sha256'], 'size': job[side]['size']} for side in ('evaluation', 'reference')}}
    return {**members, 'manifest.json': mbytes}, receipt


def stage(data_dir: Path, scope: str, files: dict, receipt: dict) -> Path:
    """Write beside the live copy, then swap; the existing copy stays on any failure."""
    data_dir = data_dir.resolve()
    if REPO_ROOT == data_dir or REPO_ROOT in data_dir.parents:
        raise Refused('DATA_DIR_PUBLIC')
    base = data_dir / 'classification' / 'q555'
    base.mkdir(parents=True, exist_ok=True)
    final, tmp, old = base / scope, base / ('.' + scope + '.new'), base / ('.' + scope + '.old')
    for p in (tmp, old):
        if p.exists():
            shutil.rmtree(p)
    try:
        tmp.mkdir()
        for name, b in files.items():
            (tmp / name).write_bytes(b)
        (tmp / 'stage.json').write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=1) + '\n', 'utf-8')
        for name, b in files.items():  # read back before the swap
            if sha((tmp / name).read_bytes()) != sha(b):
                raise Refused('WRITE_VERIFY:' + name)
        if final.exists():
            os.replace(final, old)
        os.replace(tmp, final)
    except BaseException:
        if not final.exists() and old.exists():
            os.replace(old, final)
        if tmp.exists():
            shutil.rmtree(tmp)
        raise
    if old.exists():
        shutil.rmtree(old)
    return final


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--extracted', type=Path, required=True)
    ap.add_argument('--scope', required=True, choices=sorted(SCOPES))
    ap.add_argument('--manifest-sha256', required=True)
    ap.add_argument('--data-dir', type=Path, required=True)
    ap.add_argument('--producer-sha', required=True)
    ap.add_argument('--handoff', required=True)
    ap.add_argument('--handoff-manifest-sha256', required=True)
    a = ap.parse_args(argv)
    try:
        files, receipt = check(a.extracted, a.scope, a.manifest_sha256, producer_sha=a.producer_sha, handoff=a.handoff,
                               handoff_manifest_sha256=a.handoff_manifest_sha256)
        stage(a.data_dir, a.scope, files, receipt)
    except Refused as exc:
        print('STAGE_PRIVATE_QGV555 refused=' + str(exc))
        return 2
    print('STAGE_PRIVATE_QGV555 scope=' + a.scope + ' files=' + str(receipt['files']) + ' bytes=' + str(receipt['bytes']) + ' groups='
          + str(receipt['groups']) + ' manifest=' + receipt['manifest_sha256'][:12] + ' index=' + receipt['index_sha256'][:12]
          + ' evaluation=' + receipt['expected_evaluation']['input_hash'][:12])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
