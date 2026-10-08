"""Producer snapshots -> validated Web schema-1 bundle (atomic). No calculation, no network.

Default registry: Track A FROZEN Official Universe + explicit NOT_AVAILABLE for every section
without a real producer. External producers may supply PRODUCER_SNAPSHOT v1 JSON files with
--snapshot; each is validated (and its file:/raw: source inputs re-hashed) before assembly.

Usage:
  python tools/export_web_bundle.py --now 2026-10-01T00:00:00+00:00 --out /tmp/bundle.json [--snapshot s.json ...]
      [--build-web /tmp/web]   # then: python -m investment_system.product.web_mvp --input /tmp/bundle.json --out DIR
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.producers.assembler import assemble_bundle, write_bundle_atomic  # noqa: E402
from investment_system.producers.contract import file_resolver, store_resolver, validate_snapshot, verify_inputs  # noqa: E402
from investment_system.producers.registry import FrozenUniverseProducer, ProduceRequest, default_registry  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--now', required=True, help='explicit tz-aware evaluation clock')
    p.add_argument('--requested-as-of', help='defaults to --now')
    p.add_argument('--snapshot', action='append', default=[], help='PRODUCER_SNAPSHOT v1 JSON (repeatable)')
    p.add_argument('--raw-store', help='RawDatasetStore root used to re-hash raw: inputs')
    p.add_argument('--out', required=True)
    p.add_argument('--build-web', help='optional: build the static Web MVP from the bundle into this dir')
    a = p.parse_args(argv)
    now = datetime.fromisoformat(a.now)
    req = ProduceRequest(datetime.fromisoformat(a.requested_as_of) if a.requested_as_of else now, now)
    snaps = default_registry().run(req)
    resolvers = [file_resolver(ROOT)] + ([store_resolver(RawDatasetStore(a.raw_store))] if a.raw_store else [])
    for f in a.snapshot:
        s = validate_snapshot(json.loads(Path(f).read_text(encoding='utf-8')))
        if s['data_state'] != 'NOT_AVAILABLE':
            verify_inputs(s, lambda aid: next((b for b in (r(aid) for r in resolvers) if b is not None), None))
        snaps[s['section']] = s
    bundle = assemble_bundle(FrozenUniverseProducer().companies(), snaps, now)
    digest = write_bundle_atomic(bundle, a.out)
    if a.build_web:
        from investment_system.product.web_mvp import build
        build(a.build_web, bundle)
    print(json.dumps({'out': a.out, 'bundle_sha256': digest,
                      'sections': {k: v['state'] + '/' + v['freshness'] for k, v in bundle['producer_manifest']['sections'].items()}},
                     indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
