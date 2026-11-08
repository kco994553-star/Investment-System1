#!/usr/bin/env python3
"""Offline, private static delivery of existing issuer results. No network."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.research.held_issuer_delivery import project_delivery, verify_delivery


def run(job, output, *, synthetic=False):
    out = Path(output).resolve()
    if job.get('data_kind') != ('SYNTHETIC' if synthetic else 'RETAINED_INPUT'):
        raise ValueError('DATA_KIND_MISMATCH')
    if not synthetic and any((p / '.git').exists() for p in (out, *out.parents)):
        raise ValueError('PRIVATE_OUTPUT_OUTSIDE_CHECKOUT_REQUIRED')
    if out.exists():
        raise ValueError('OUTPUT_ALREADY_EXISTS')
    files = project_delivery(job, index_bytes=job.get('index_byte_budget', 2 * 1024 * 1024))
    out.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.' + out.name + '-', dir=out.parent))
    try:
        for name, body in files.items():
            p = temp / name;p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(body);p.chmod(0o600)
        manifest = verify_delivery({name: (temp / name).read_bytes() for name in files})
        temp.rename(out)
    finally:
        if temp.exists():shutil.rmtree(temp)
    return {'status': 'VERIFIED', 'issuers': manifest['detail_rows'], 'files': len(files),
            'indexes': len(manifest['indexes']), 'max_bytes': max(map(len, files.values())), 'new_calculations': 0}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--job', required=True);p.add_argument('--output', required=True);p.add_argument('--synthetic', action='store_true');a = p.parse_args()
    try:
        print(json.dumps(run(json.loads(Path(a.job).read_text()), a.output, synthetic=a.synthetic)))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'status': 'FAILED', 'error_type': type(exc).__name__}), file=sys.stderr);raise SystemExit(1)
