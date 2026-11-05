#!/usr/bin/env python3
"""Replay retained SEC/DART/news metadata locally. No supplier request or publication path.

Inputs manifest: {"inputs": [{"kind": "SEC_SUBMISSIONS|SEC_PUBLIC|NEWS_PUBLIC|DART_PUBLIC|GDELT_JSON|IR_FEED",
"path": "local file", "company_id": "nvda", "acquired_at": "...+00:00", "sha256": "optional expected digest"}]}.
Raw inputs require company_id/acquired_at; validated public inputs carry those fields.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.product import dart_public as dp, news_signals as ns, sec_disclosures as sd
from investment_system.providers import news_feeds as nf
from investment_system.providers.news_update import UpdateLedger, dart_rows, news_rows, sec_rows
from investment_system.providers.sec_8k_disclosures import current_reports, foreign_earnings_candidates


def _read(path):
    if path.is_symlink() or path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('INPUT_INVALID')
    return path.read_bytes()


def _write(path, data):
    if path.is_symlink():
        raise ValueError('OUTPUT_INVALID')
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(data, handle, sort_keys=True, ensure_ascii=False, indent=2)
        handle.write('\n')
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def replay(manifest_path, *, out, as_of, state_path=None, cache_ttl=0):
    manifest = json.loads(_read(manifest_path))
    if not 0 <= cache_ttl <= 86400:
        raise ValueError('NEWS_CACHE_TTL_INVALID')
    ledger = UpdateLedger(json.loads(_read(state_path)) if state_path else None)
    counts, inputs, held_status, changes = Counter(), [], [], Counter(new=0, duplicate=0, revision=0)
    sec = None
    # A retained validated SEC public file can confirm supported ASML quarterly candidates.
    for spec in manifest['inputs']:
        if spec['kind'] == 'SEC_PUBLIC':
            try:
                path = manifest_path.parent / spec['path']
                body = _read(path)
                if spec.get('sha256') and hashlib.sha256(body).hexdigest() != spec['sha256']:
                    raise ValueError('INPUT_DIGEST_MISMATCH')
                sec = sd.require_sec_disclosures(sd.parse_json(body))
            except (ValueError, OSError, KeyError, TypeError):
                continue  # recorded per-input below; unrelated sources still proceed

    def apply(source, company, rows, acquired, *, failure=None, cached=False, attempted=None):
        result = ledger.apply(source, company, rows, acquired_at=acquired, attempted_at=attempted or as_of,
                              failure=failure, cached=cached)
        changes.update(result['changes'])
        counts[result['result']] += 1

    for index, spec in enumerate(manifest['inputs']):
        kind, company = spec['kind'], spec.get('company_id')
        source = {'SEC_SUBMISSIONS': 'SEC', 'GDELT_JSON': 'GDELT', 'IR_FEED': 'IR'}.get(kind)
        entry = {'index': index, 'kind': kind, 'result': 'PARSED', 'rows': 0}
        try:
            if source:
                cached = ledger.cached(source, company, now=as_of, ttl_seconds=cache_ttl)
                if cached:
                    apply(source, company, [], datetime.fromisoformat(cached['acquired_at']), cached=True)
                    entry.update(result='CACHED', rows=len(cached['rows']))
                    inputs.append(entry)
                    continue
            path = manifest_path.parent / spec['path']
            body = _read(path)
            digest = hashlib.sha256(body).hexdigest()
            if spec.get('sha256') and digest != spec['sha256']:
                raise ValueError('INPUT_DIGEST_MISMATCH')
            entry['sha256'] = digest
            if source:
                acquired = datetime.fromisoformat(spec['acquired_at'])
                if kind == 'SEC_SUBMISSIONS':
                    data = json.loads(body)
                    since = (acquired - timedelta(days=sd.WINDOW_DAYS)).date()
                    reports, excluded = current_reports(company, data, acquired_at=acquired, since=since)
                    candidates = foreign_earnings_candidates(company, data, acquired_at=acquired, since=since)
                    known = {e['accession'] for e in sec['events'] if e['company_id'] == company} if sec else set()
                    reports.extend(c for c in candidates if c['accession'] in known)
                    entry.update(parser_counts=excluded, foreign_candidates=len(candidates),
                                 foreign_unconfirmed=sum(c['accession'] not in known for c in candidates))
                    rows = sec_rows(company, reports)
                else:
                    raw = nf.parse_gdelt(body) if source == 'GDELT' else nf.parse_feed(body)
                    rows = news_rows(source, company, raw, acquired_at=acquired, sec=sec)
                apply(source, company, rows, acquired)
                entry['rows'] = len(rows)
            elif kind == 'SEC_PUBLIC':
                data = sd.require_sec_disclosures(sd.parse_json(body))
                for cid, status in data['companies'].items():
                    if status['acquired_at']:
                        rows = sec_rows(cid, [e for e in data['events'] if e['company_id'] == cid])
                        apply('SEC', cid, rows, datetime.fromisoformat(status['acquired_at']))
                        entry['rows'] += len(rows)
                held_status.append({'kind': kind, 'as_of': data['as_of'], 'state': data['state']})
            elif kind == 'NEWS_PUBLIC':
                data = ns.require_news_signals(ns.parse_json(body))
                for provider, companies in data['sources'].items():
                    for cid, status in companies.items():
                        if status['acquired_at']:
                            raw = [dict(i, published_at=datetime.fromisoformat(i['published_at']))
                                   for i in data['items'] if i['source'] == provider and i['company_id'] == cid]
                            acquired = datetime.fromisoformat(status['acquired_at'])
                            rows = news_rows(provider, cid, raw, acquired_at=acquired, sec=sec)
                            apply(provider, cid, rows, acquired)
                            entry['rows'] += len(rows)
                        if status.get('last_result') in ('FAILED', 'NOT_RUN'):
                            apply(provider, cid, [], None, failure=status['last_result_code'],
                                  attempted=datetime.fromisoformat(data['as_of']))
                            ledger.state['sources'][provider + ':' + cid]['result'] = status['last_result']
                held_status.append({'kind': kind, 'as_of': data['as_of'], 'state': data['state'], 'refresh': data.get('refresh')})
            elif kind == 'DART_PUBLIC':
                data = dp.require_disclosures(dp.parse_json(body))
                for cid, status in data['companies'].items():
                    if status['acquired_at']:
                        rows = dart_rows(data, cid)
                        apply('DART', cid, rows, datetime.fromisoformat(status['acquired_at']))
                        entry['rows'] += len(rows)
                held_status.append({'kind': kind, 'as_of': data['as_of'], 'state': data['state']})
            else:
                raise ValueError('INPUT_KIND_INVALID')
        except (ValueError, OSError, KeyError, TypeError):
            entry['result'] = 'INPUT_INVALID'
            if source and company:
                apply(source, company, [], None, failure='REPLAY_INPUT_INVALID')
        inputs.append(entry)
    failed = sum(i['result'] == 'INPUT_INVALID' for i in inputs)
    report = {'mode': 'RETAINED_REPLAY', 'as_of': ns.instant(as_of), 'network_requests': 0,
              'result': 'PARTIAL_FAILED' if 0 < failed < len(inputs) else 'FAILED' if failed else 'OK',
              'inputs': inputs, 'items': len(ledger.state['items']), 'changes': dict(changes),
              'source_results': dict(counts), 'items_by_source': dict(Counter(i['source'] for i in ledger.state['items'].values())),
              'retained_source_status': held_status}
    if out.is_symlink():
        raise ValueError('OUTPUT_INVALID')
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    _write(out / 'state.json', ledger.state)
    _write(out / 'report.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--state', type=Path)
    parser.add_argument('--as-of', type=datetime.fromisoformat, required=True)
    parser.add_argument('--cache-ttl', type=int, default=0)
    args = parser.parse_args(argv)
    try:
        result = replay(args.inputs, out=args.out, as_of=args.as_of, state_path=args.state, cache_ttl=args.cache_ttl)
    except (ValueError, OSError, KeyError, TypeError):
        print('NEWS_REPLAY INPUT_OR_OUTPUT_INVALID')
        return 1
    print(f"NEWS_REPLAY result={result['result']} items={result['items']} network_requests=0")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
