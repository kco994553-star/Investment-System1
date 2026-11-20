"""Synthetic calc23.1 V-containing QGV timing; no prices/results are published.

Uses the existing strict fixture reader, normalizer and official_reference engine.
Q/G/V scoring is joint: the timed pipeline is NOT described as pure V arithmetic.
No I/O/network provider functions are called. Runtime uses the standard library.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import time

from kis_rebuild_benchmark import synthetic_contracts
from investment_system.research._private_artifacts import digest, json_bytes
from investment_system.research.private_kis_reference import official_reference
from investment_system.universe import sec_qgv2
from investment_system.universe.sec_universe_shares import universe_codes


def synthetic_inputs(sessions):
    base = json.loads((Path(__file__).parents[1] / 'tests/fixtures/sec_qgv2_vectors_v1.json').read_bytes())['base']
    model = next(r for r in base['records'].values() if r['profile'] == 'GENERAL'
                 and (r.get('v_inputs_v2') or {}).get('ebit_per_share_history'))
    clock = '2026-12-01T02:00:00Z'
    records, contracts, links, months = {}, {}, {}, {}
    codes = universe_codes()
    for i, (code, c) in enumerate(zip(codes, synthetic_contracts(len(codes), sessions))):
        row = deepcopy(model)
        row.update(cik=f'{9000000+i:010}', acquired_at=clock)
        # Fake fixture, not the real six held series or a verification upgrade.
        c['held_ranges'] = []
        records[code] = row
        contracts[code] = c
        links[code] = dict(symb=c['symbol'], excd=c['source_query']['EXCD'])
        sym = code.split(':', 1)[1]
        close = float(c['raw_bars'][-1]['close'])
        for year in range(2021, 2027):
            for month in range(1, 13):
                if (year, month) > (2026, 11):
                    continue
                m = f'{year}-{month:02}'
                item = months.setdefault(m, dict(date=m.replace('-', '')+'28', codes={}, symbols={}))
                item['codes'][code] = sym
                item['symbols'][sym] = dict(status='ROUND', price_e4=round(close * 10000), ts_ns=1, n=1)
    as_of = datetime(2026, 12, 1, 2, tzinfo=timezone.utc)
    stale_after = timedelta(seconds=base['stale_after_seconds'])
    target = {k: sec_qgv2.restate(deepcopy(r), as_of, stale_after) for k, r in base['target'].items()}
    payload = sec_qgv2.publish(records, target, as_of=as_of,
        cfg=sec_qgv2.load_config(), stale_after=stale_after,
        shard_index=base['last_shard_index'], registry_sha256=None)
    sec_qgv2.require_qgv2(payload)
    return payload, contracts, links, months, clock


def measure(sessions):
    if not 1 <= sessions <= 1260:
        raise ValueError('SESSIONS_OUT_OF_RANGE')
    begin = time.perf_counter()
    payload, contracts, links, months, clock = synthetic_inputs(sessions)
    setup = time.perf_counter() - begin
    hashes = {k: digest(v) for k, v in contracts.items()}
    begin = time.perf_counter()
    result = official_reference(payload, contracts, links, day='2026-11-30', calculated_at=clock,
        expected_payload_hash=digest(payload), expected_links_hash=digest(links),
        expected_contract_hashes=hashes, monthends=months)
    elapsed = time.perf_counter() - begin
    begin = time.perf_counter()
    encoded = json_bytes(result)
    serialize = time.perf_counter() - begin
    if result['coverage']['V'] == 0:
        raise ValueError('BENCHMARK_NO_COMPUTED_V')
    return dict(data_kind='SYNTHETIC_NOT_ACTUAL_V', code_rows=len(payload['records']),
        sessions=sessions, monthend_months=len(months), source_setup_seconds=setup,
        qgv_pipeline_seconds=elapsed, output_serialization_seconds=serialize,
        output_sha256=hashlib.sha256(encoded).hexdigest(), output_bytes=len(encoded),
        stages=result['stages'], coverage=result['coverage'],
        calculation_version=payload['calc_version'], engine_version=result['engine_version'],
        benchmark_scope='PRICE_VALIDATION_PLUS_JOINT_QGV_ENGINE_NOT_PURE_V_ARITHMETIC',
        real_five_year_runtime_measured=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sessions', nargs='+', type=int, default=[100, 1260])
    p.add_argument('--receipt', type=Path, required=True)
    args = p.parse_args()
    result = dict(kind='SYNTHETIC_V_TIMING', cases=[measure(n) for n in args.sessions])
    with args.receipt.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps(dict(cases=len(result['cases']), code_rows=504)))


if __name__ == '__main__':
    main()
