"""Synthetic B2 storage accounting and real-engine timing harness checks."""
import importlib.util
from pathlib import Path
import sys


def tool(name):
    path = Path(__file__).parents[2] / 'tools' / (name + '.py')
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_month_parts_preserve_every_record_including_revisions():
    m = tool('kis_b2_capacity')
    rows = [('a', {'date': '2026-01-02', 'provider': {'clos': '12.00'},
                   'bar': None, 'receipt_sha256': 'a' * 64, 'supersedes': None}),
            ('a', {'date': '2026-01-02', 'provider': {'clos': '12.10'},
                   'bar': None, 'receipt_sha256': 'b' * 64, 'supersedes': 'c' * 64}),
            ('b', {'date': '2026-01-02', 'provider': {'clos': None}, 'bar': None})]
    part = m.price_part(rows)
    assert part == m.price_part(rows)
    assert m.read_price_part(part) == rows


def test_capacity_includes_initial_prices_views_new_rows_and_summaries():
    m = tool('kis_b2_capacity')
    out = m.annual_budget(month_git=1000, row_count=100, series_count=2,
                          max_daily_git=30, sessions=1260, updates=252)
    assert out['price_bootstrap_estimate'] == 25200
    assert out['price_new_rows_estimate'] == 7560
    assert out['summaries_allowance'] == 1_000_000
    assert out['total_estimate'] == sum(out[k] for k in (
        'view_updates_estimate', 'view_sealing_allowance', 'view_bootstrap_allowance',
        'price_bootstrap_estimate', 'price_new_rows_estimate', 'summaries_allowance', 'other_git_reserve'))


def test_synthetic_v_benchmark_really_computes_v_without_network(monkeypatch):
    import socket
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: (_ for _ in ()).throw(AssertionError('NETWORK')))
    m = tool('kis_v_benchmark')
    out = m.measure(5)
    assert out['data_kind'] == 'SYNTHETIC_NOT_ACTUAL_V'
    assert out['code_rows'] == 504
    assert out['stages']['raw_any'] > 0
    assert out['coverage']['V'] > 0
    assert out['coverage']['total'] <= out['coverage']['QGV']
    assert out['qgv_pipeline_seconds'] > 0
    assert out['calculation_version'] == 'qgv2-calc/2026-10-23.1'
