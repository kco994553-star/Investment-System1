"""Offline private run from the already restored #461/#467 input handoff.

No provider calls or credentials. Public stdout contains aggregate counts only.
PYTHONPATH=implementation/src python <this file> --input-handoff <private-root>
    --output <new-private-directory-outside-any-checkout> --reference-symbol AMD
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

from investment_system.research.exp_deciles.technical_measures import measure, METRIC_IDS, SETTINGS_BYTES
from investment_system.research.exp_deciles.technical_leaderboard import build_board


def write(root, name, value):
    path = root / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    path.chmod(0o600)


def run(input_root, output, reference_symbol):
    input_root, output = input_root.resolve(), output.resolve()
    if output.exists():
        raise ValueError('OUTPUT_MUST_BE_NEW')
    if any((p / '.git').exists() for p in (output, *output.parents)):
        raise ValueError('PRIVATE_OUTPUT_OUTSIDE_CHECKOUT_REQUIRED')
    manifest = json.loads((input_root / 'bundle-manifest.json').read_text())
    entries = {r['path']: r for r in manifest['files']}
    inputs, refs = {}, []
    for name in ('normalized-2017-2018.json', 'sample-momentum.json', 'sample-liquidity-recomputed.json'):
        path = 'computed/' + name
        raw = (input_root / path).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != entries[path]['sha256']:
            raise ValueError('INPUT_HASH_MISMATCH')
        inputs[name] = json.loads(raw)
        refs.append(dict(path=path, sha256=digest, bytes=len(raw)))
    normalized = inputs['normalized-2017-2018.json']
    previous_momentum = inputs['sample-momentum.json']
    previous_liquidity = inputs['sample-liquidity-recomputed.json']
    signal = '2018-02-16'
    if previous_momentum['signal_day'] != signal:
        raise ValueError('BASELINE_SIGNAL_MISMATCH')
    # Freeze inventory and group availability before any new metric is measured.
    request_series = [f'ALPACA:SIP:RAW:ASOF_MINUS:{s}' for s in sorted(normalized)]
    groups = [dict(group_id=g, signal_day=signal, membership_status='UNKNOWN',
                   member_security_ids=None, membership_source=None)
              for g in ('HELD_SECURITY_SAMPLE', 'U_A', 'U_B')]
    code_root = Path(__file__).resolve().parents[3]
    code_sha = subprocess.run(['git', '-C', str(code_root), 'rev-parse', 'HEAD'],
                              check=True, capture_output=True, text=True).stdout.strip()
    output.mkdir(parents=True, mode=0o700)
    frozen = dict(signal_day=signal, fixed_before_measurement_at=datetime.now(timezone.utc).isoformat(),
                  code_sha=code_sha, settings=json.loads(SETTINGS_BYTES),
                  settings_sha256=hashlib.sha256(SETTINGS_BYTES).hexdigest(),
                  request_series=request_series, groups=groups,
                  sample_group_reason='HELD_REQUEST_INVENTORY_KNOWN_BUT_FIXED_SECURITY_MAPPING_UNCONFIRMED',
                  source_inputs=refs, source_handoff='handoffs/input-handoff-20261103 at private commit ee072c73e7b922f7d1ed2ddd5fbdf9ad0d0e3ab4')
    write(output, 'frozen-inputs-and-settings.json', frozen)
    records = []
    for symbol, node in sorted(normalized.items()):
        old_m = [r for r in previous_momentum['rows'] if r['symbol'] == symbol]
        identity = (symbol == reference_symbol and len(old_m) == 3
                    and all(r['economic_momentum'] is not None for r in old_m))
        prior_l = previous_liquidity[symbol]
        evidence = dict(identity_status='DOCUMENT_RECONSTRUCTED' if identity else 'UNKNOWN',
            identity_reference='Prior private handoff/HANDOFF.md and sample-momentum.json' if identity else None,
            security_id=None, original_identity_page_bytes_recovered=False,
            no_split_start=min(r['start_day'] for r in old_m) if identity else None,
            no_split_end=signal if identity else None,
            no_split_reference='Prior documented full split-history reconstruction; not newly fetched' if identity else None,
            currency=prior_l.get('currency'), currency_reference='Prior exact-endpoint USD-default report' if prior_l.get('currency') == 'USD' else None,
            trade_scope_status='UNCONFIRMED', trade_scope_reference=None,
            scope_note='Same provider bar is known; matching VWAP and volume trade eligibility is not established by the retained report')
        records.append(measure(node['rows'], signal_day=signal, symbol=symbol,
                               series_id=f'ALPACA:SIP:RAW:ASOF_MINUS:{symbol}', evidence=evidence))
    boards = {g['group_id']: build_board(records, group=g) for g in groups}
    target = next(r for r in records if r['symbol'] == reference_symbol)
    checks = []
    with localcontext() as ctx:
        ctx.prec = 50
        for old in previous_momentum['rows']:
            if old['symbol'] != reference_symbol:
                continue
            metric = target['metrics'][f"momentum_{old['months']}m"]
            assert Decimal(metric['value']) == Decimal(old['economic_momentum']) * 100
            checks.append(dict(metric=f"momentum_{old['months']}m", prior_equal=True))
    old_liq = previous_liquidity[reference_symbol]
    dv = target['metrics']['dollar_volume_6m']
    assert dv['raw_value'] == old_liq['vwap_volume']['mean_complete']
    assert (dv['observed_days'], dv['expected_days']) == (old_liq['vwap_volume']['valid_days'], old_liq['expected_sessions'])
    assert dv['value'] is None and 'TRADE_SCOPE_UNCONFIRMED' in dv['null_reasons']
    checks.append(dict(metric='dollar_volume_6m', raw_mean_and_coverage_match_prior=True,
                       primary_adoption='BLOCKED_ON_MATCHING_TRADE_SCOPE'))
    # Independent variance identity over rational prices, not the production two-pass algorithm.
    prices = {r['date']: Fraction(r['close']) for r in normalized[reference_symbol]['rows']
              if '2017-08-16' <= r['date'] <= signal}
    days = sorted(prices)
    returns = [(prices[b]-prices[a])/prices[a] for a,b in zip(days, days[1:])]
    n = len(returns)
    variance = (sum(r*r for r in returns) - sum(returns)**2 / n) / (n-1)
    with localcontext() as ctx:
        ctx.prec = 100
        independent = (Decimal(variance.numerator)/Decimal(variance.denominator)).sqrt()*100
        delta = abs(Decimal(target['metrics']['volatility_6m']['value']) - independent)
        assert delta < Decimal('1e-45')
    float_reference = statistics.stdev([float(r) for r in returns]) * 100
    assert abs(float(target['metrics']['volatility_6m']['value']) - float_reference) < 1e-12
    checks.append(dict(metric='volatility_6m', rational_variance_identity_pass=True,
                       sample_stdev_reference_pass=True, return_count=n,
                       independent_percent=str(independent), absolute_delta_percent=str(delta)))
    counts = dict(requested_price_series=len(records), documented_security_identities=sum(r['identity_status']=='DOCUMENT_RECONSTRUCTED' for r in records),
                  fixed_security_ids=sum(r['security_id'] is not None for r in records),
                  valid_raw_values={k:sum(r['metrics'][k]['raw_value'] is not None for r in records) for k in METRIC_IDS},
                  valid_adopted_values={k:sum(r['metrics'][k]['value'] is not None for r in records) for k in METRIC_IDS},
                  group_n={g:{k:boards[g]['metrics'][k]['n_valid'] for k in METRIC_IDS} for g in boards})
    diagnostics = {}
    for k in METRIC_IDS:
        available = [(r['series_id'], Decimal(r['metrics'][k]['raw_value'])) for r in records if r['metrics'][k]['raw_value'] is not None]
        with localcontext() as ctx:
            ctx.prec = 50
            median = statistics.median([v for _,v in available]) if available else None
        diagnostics[k] = dict(population='ORIGINAL_REQUEST_SERIES_NOT_SECURITIES', members=[sid for sid,_ in available],
                              n_valid=len(available), median_raw=None if median is None else str(median),
                              rank=None, decile=None, reason='FIXED_SECURITY_COMPARISON_POPULATION_UNCONFIRMED')
    write(output, 'measurements.json', records)
    write(output, 'boards.json', boards)
    write(output, 'raw-series-diagnostics.json', diagnostics)
    write(output, 'counts.json', counts)
    write(output, 'verification.json', dict(reference_symbol=reference_symbol, checks=checks, new_provider_requests=0,
                                          qgv_score_engine_invoked=False, strategy_performance_computed=False))
    files = [dict(path=p.name, bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(output.iterdir())]
    write(output, 'manifest.json', dict(schema='technical-leaderboard-private-manifest/1', code_sha=code_sha,
          settings_sha256=frozen['settings_sha256'], input_files=refs, output_files=files))
    print(json.dumps(counts))
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-handoff', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reference-symbol', required=True)
    args = parser.parse_args()
    run(args.input_handoff, args.output, args.reference_symbol)
