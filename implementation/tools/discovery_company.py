#!/usr/bin/env python3
"""Offline held-source discovery runner. Actual jobs require private output storage."""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import sys

from investment_system.ingestion.raw_store import RawDatasetStore
from investment_system.research.discovery_company import canonical, evaluate, extract_fact, summarize


def run(job, output_dir):
    output = Path(output_dir)
    # Do not accidentally commit real research through this runner.
    real = any(not p['company_id'].startswith('SYNTH:') for p in job['packages'])
    if real and (any((p / '.git').exists() for p in (output.resolve(), *output.resolve().parents))
                 and job.get('approved_private_repository') is not True):
        raise ValueError('real research requires approved private output storage')
    records = []
    planned = {}
    for entry in job['packages']:
        p = deepcopy(entry)
        extracts = p.pop('extracts', [])
        if real and not extracts:
            raise ValueError('real jobs require source-byte extraction, not supplied facts')
        if extracts:
            p['evidence'] = []
            for item in extracts:
                if 'raw_store' in item:
                    store = RawDatasetStore(item['raw_store'])
                    body = store.get_bytes(item['artifact_id'])
                    receipt = store.get_manifest(item['artifact_id'])
                else:
                    body = Path(item['path']).read_bytes()
                    receipt = item['receipt']
                p['evidence'].append(extract_fact(body, receipt, item['selector'], p['company_id'], item['metadata']))
        previous = json.loads(Path(p.pop('previous_path')).read_text()) if p.get('previous_path') else None
        result = evaluate(p, previous)
        # The manifest points to every snapshot. Files are never overwritten.
        planned[f"record-{result['record_hash']}.json"] = canonical(result) + '\n'
        records.append(result)
    summary = summarize(records)
    from investment_system.research.discovery_company import digest
    manifest = dict(schema_version='discovery-company-run/v1', summary=summary, records=sorted(planned))
    planned[f"run-{digest(manifest)}.json"] = canonical(manifest) + '\n'
    output.mkdir(parents=True, exist_ok=True)
    for name, content in planned.items():
        dest = output / name
        if dest.exists():
            if dest.read_text() != content:
                raise ValueError('immutable result collision')
        else:
            with dest.open('x') as f:
                f.write(content)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    try:
        summary = run(json.loads(Path(args.job).read_text()), args.output_dir)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        # No source values, company details, local paths or exception content in logs.
        print(f'discovery job failed: {type(exc).__name__}', file=sys.stderr)
        return 1
    print(canonical(summary))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
