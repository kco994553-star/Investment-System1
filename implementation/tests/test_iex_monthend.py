"""U8 IEX V4 month-end backfill: plan, backfill streaming/upload, split check. Synthetic numbers only (no real prices)."""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS / 'iex_hist'))
sys.path.insert(0, str(TOOLS))
import monthend_backfill as bf  # noqa: E402
import monthend_plan as mp  # noqa: E402
import split_check as sc  # noqa: E402
import sec_universe_shares as sus  # noqa: E402

TOKEN = 'synthetic-token-not-real'


def feed(day, kind='TOPS', version='1.6', size=1000):
    return {'link': f'https://example.invalid/download/storage/v1/b/iex/o/data%2F{day}_{kind}.pcap.gz?generation=7&alt=media',
            'date': day, 'feed': kind, 'version': version, 'protocol': 'IEXTP1', 'size': str(size)}


def history(*ends):
    return [{'fiscal_year_end': e, 'value': 1.0 + i} for i, e in enumerate(ends)]


def qgv2(records):
    return {'as_of': '2026-10-23T00:00:00Z', 'calc_version': 'synthetic',
            'records': {c: {'v_inputs_v2': {'ebit_per_share_history': h}} for c, h in records.items()}}


INDEX = {
    '20240628': [feed('20240628', size=3000), feed('20240628', 'DEEP')],
    '20240627': [feed('20240627', size=2900)],
    '20240630': [feed('20240630', 'DEEP')],  # no TOPS that day: not the month-end file
    '20241231': [feed('20241231', size=2000)],
    '20250930': [feed('20250930', size=4000)],
    '20251231': [feed('20251231', version='1.5', size=5)],  # other TOPS version only: month without file
    '20230630': [feed('20230630', size=1000)],
}


# ---- plan ----

def test_plan_months_dates_symbols_and_aliases():
    data = qgv2({'NASDAQ:AAA': history('2019-06-30', '2020-06-30', '2021-06-30', '2022-06-30', '2023-06-30', '2024-06-30'),
                 'NYSE:BRK.B': history('2024-12-31'), 'NASDAQ:PSKY': history('2024-06-30', '2025-09-30'),
                 'NASDAQ:ZZZ': history('2025-12-31'), 'NASDAQ:OUT': history('2024-06-30')})
    plan = mp.build(data, INDEX, ['NASDAQ:AAA', 'NYSE:BRK.B', 'NASDAQ:PSKY', 'NASDAQ:ZZZ'])
    months = {m['month']: m for m in plan['months']}
    # latest 5 entries only (2019-06 dropped); codes outside the list (OUT) ignored
    # PSKY 2024-06 is before its V4_NA_BEFORE cut (pre-merger basis): not requested; 2025-09 is after it
    assert sorted(months) == ['2023-06', '2024-06', '2024-12', '2025-09']
    assert 'NASDAQ:PSKY' not in months['2024-06']['codes']
    assert months['2024-06']['date'] == '20240628' and months['2024-06']['size'] == 3000
    assert months['2024-06']['codes'] == {'NASDAQ:AAA': 'AAA'}
    assert months['2025-09']['codes'] == {'NASDAQ:PSKY': 'PSKY'}  # merged line, before the SKYD switch
    assert months['2024-12']['symbols'] == ['BRK.B']
    assert plan['months_without_file'] == ['2020-06', '2021-06', '2022-06', '2025-12']  # 2019-06: not in the latest 5
    s = mp.summary(plan, 2)
    assert (s['months'], s['files'], s['symbols_per_month_min'], s['symbols_per_month_max'], s['codes']) == (4, 4, 1, 1, 3)
    assert s['total_gb'] == round(10000 / 1e9, 1) and len(s['shard_gb']) == 2
    assert mp.build(data, INDEX, ['NASDAQ:AAA', 'NYSE:BRK.B', 'NASDAQ:PSKY', 'NASDAQ:ZZZ']) == plan  # deterministic


def test_iex_symbol_alias_by_date():
    aliases = {'NASDAQ:X': (('2025-01-01', 'XNEW', 'test'),)}
    assert mp.iex_symbol('NASDAQ:X', '20241231', aliases) == 'X'
    assert mp.iex_symbol('NASDAQ:X', '2025-01-01', aliases) == 'XNEW'
    assert mp.iex_symbol('NYSE:BF.B', '20250101', aliases) == 'BF.B'


def test_shard_months_cover_every_month_once_and_balance():
    plan = {'months': [{'month': f'2024-{i:02d}', 'size': s} for i, s in enumerate((9, 8, 7, 6, 5, 4, 3, 2, 1), 1)]}
    shards = mp.shard_months(plan, 3)
    assert sorted(m for s in shards for m in s) == sorted(m['month'] for m in plan['months'])
    by = {m['month']: m['size'] for m in plan['months']}
    loads = [sum(by[m] for m in s) for s in shards]
    assert max(loads) - min(loads) <= 3 and mp.shard_months(plan, 3) == shards


def test_gcs_md5_from_object_metadata():
    link = 'https://www.googleapis.com/download/storage/v1/b/iex/o/data%2Ffeeds%2F20240628%2Fx.pcap.gz?generation=7&alt=media'
    assert mp.gcs_metadata_url(link) == 'https://www.googleapis.com/storage/v1/b/iex/o/data%2Ffeeds%2F20240628%2Fx.pcap.gz?generation=7'
    digest = hashlib.md5(b'abc').digest()
    plan = {'months': [{'month': '2024-06', 'link': link, 'size': 3, 'md5': None}]}
    mp.add_gcs_md5(plan, fetch=lambda url: {'size': '3', 'md5Hash': base64.b64encode(digest).decode()})
    assert plan['months'][0]['md5'] == digest.hex()
    plan['months'][0].update(md5=None, size=4)
    with pytest.raises(ValueError):
        mp.add_gcs_md5(plan, fetch=lambda url: {'size': '3', 'md5Hash': base64.b64encode(digest).decode()})


# ---- backfill ----

def small_plan():
    data = qgv2({'NASDAQ:AAA': history('2024-06-30', '2024-12-31'), 'NASDAQ:BBB': history('2024-06-30')})
    return mp.build(data, INDEX, ['NASDAQ:AAA', 'NASDAQ:BBB'])


def rows_for(month):
    out = {}
    for i, sym in enumerate(month['symbols']):
        out[sym] = ({'status': 'NO_TRADE', 'price_e4': None, 'ts_ns': None, 'n': 0} if sym == 'BBB' else
                    {'status': 'ROUND', 'price_e4': 123456 + i, 'ts_ns': 1, 'n': 3})
    return out


def test_parse_rows_requires_exact_symbols_and_positive_prices():
    rows = bf.parse_rows('AAA\tROUND\t1000\t5\t2\t0\tT\t9\nBBB\tNO_TRADE\t0\t0\t0\t0\t-\t0\n', ['AAA', 'BBB'])
    assert rows == {'AAA': {'status': 'ROUND', 'price_e4': 1000, 'ts_ns': 5, 'n': 2},
                    'BBB': {'status': 'NO_TRADE', 'price_e4': None, 'ts_ns': None, 'n': 0}}
    for bad, syms in (('AAA\tROUND\t0\t5\t2\n', ['AAA']), ('AAA\tROUND\t1\t5\t2\n', ['AAA', 'BBB']), ('AAA\tWHAT\t1\t5\t2\n', ['AAA'])):
        with pytest.raises(bf.BackfillError):
            bf.parse_rows(bad, syms)


def test_run_uploads_one_private_gzip_json_and_prints_counts_only(tmp_path, capsys):
    plan, uploads = small_plan(), []

    def upload(data, **kw):
        uploads.append((data, kw))
        return 'RAW_UPLOADED bytes=1 sha256=' + 'f' * 64

    rc = bf.run(plan, shard=0, shards=1, parser='p', stamp='20261023', token=TOKEN, workdir=tmp_path,
                stream=lambda m, *a, **k: rows_for(m), upload=upload)
    out = capsys.readouterr().out
    assert rc == 0 and len(uploads) == 1
    data, kw = uploads[0]
    assert kw['tag'] == 'iex-v4-monthend-20261023-shard0' and kw['name'] == 'iex-v4-monthend-20261023-shard0.json.gz'
    assert kw['token'] == TOKEN and kw['content_type'] == 'application/gzip'
    body = json.loads(gzip.decompress(data))
    assert body['schema'] == 'iex-monthend/1' and sorted(body['months']) == ['2024-06', '2024-12']
    assert body['months']['2024-06']['symbols']['AAA']['price_e4'] == 123456
    assert body['months']['2024-06']['codes'] == {'NASDAQ:AAA': 'AAA', 'NASDAQ:BBB': 'BBB'}
    assert '12345' not in out and '1234' not in out and 'sha256' not in out and TOKEN not in out
    assert 'month=2024-06 date=20240628' in out and 'round=1 odd=0 no_trade=1' in out and 'no_trade_codes=NASDAQ:BBB' in out


def test_run_failure_or_missing_token_uploads_nothing(tmp_path, capsys):
    plan, uploads, streamed = small_plan(), [], []
    with pytest.raises(bf.BackfillError, match='RAW_UPLOAD_NOT_CONFIGURED'):
        bf.run(plan, shard=0, shards=1, parser='p', stamp='20261023', token=None, workdir=tmp_path,
               stream=lambda *a, **k: streamed.append(1), upload=lambda *a, **k: uploads.append(1))
    assert not streamed

    def failing(month, *a, **k):
        if month['month'] == '2024-12':
            raise bf.BackfillError('MD5_MISMATCH')
        return rows_for(month)
    with pytest.raises(bf.BackfillError, match='MD5_MISMATCH'):
        bf.run(plan, shard=0, shards=1, parser='p', stamp='20261023', token=TOKEN, workdir=tmp_path, stream=failing,
               upload=lambda *a, **k: uploads.append(1))
    assert not uploads
    assert bf.main(['--parser', 'p', '--plan', str(tmp_path / 'missing.json'), '--shard', '0', '--shards', '1',
                    '--stamp', '20261023']) == 1
    assert 'FAILED code=' in capsys.readouterr().out


def test_stream_month_verifies_size_and_md5(tmp_path):
    compressed = gzip.compress(b'synthetic capture bytes', mtime=0)
    src = tmp_path / 'file.gz'
    src.write_bytes(compressed)
    parser = tmp_path / 'parser.py'
    parser.write_text('import sys\nsys.stdin.buffer.read()\n'
                      'for s in open(sys.argv[1]).read().split():\n    print(s + "\\tROUND\\t1000\\t5\\t1\\t0\\t-\\t1")\n')
    exe = tmp_path / 'parser.sh'
    exe.write_text(f'#!/bin/sh\nexec {sys.executable} {parser} "$@"\n')
    exe.chmod(0o755)

    def popen(args, **kw):
        return subprocess.Popen(['cat', str(src)] if args[0] == 'curl' else args, **kw)

    month = {'month': '2024-06', 'date': '20240628', 'link': 'https://example.invalid/x', 'symbols': ['AAA', 'BRK.B'],
             'size': len(compressed), 'md5': hashlib.md5(compressed).hexdigest()}
    rows = bf.stream_month(month, str(exe), tmp_path, popen=popen)
    assert set(rows) == {'AAA', 'BRK.B'} and not list(tmp_path.glob('symbols-*'))
    with pytest.raises(bf.BackfillError, match='MD5_MISMATCH'):
        bf.stream_month(dict(month, md5='0' * 32), str(exe), tmp_path, popen=popen)
    with pytest.raises(bf.BackfillError, match='SIZE_MISMATCH'):
        bf.stream_month(dict(month, size=month['size'] + 1), str(exe), tmp_path, popen=popen)


class Resp(io.BytesIO):
    def __init__(self, status, body):
        super().__init__(body)
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_upload_raw_bytes_shared_path_headers_and_no_token_echo():
    seen = []

    def opener(request, timeout=None):
        seen.append(request)
        return Resp(201, json.dumps({'id': 42}).encode())
    status = sus.upload_raw_bytes(b'gzip-bytes', tag='iex-v4-monthend-20261023-shard0', name='a.json.gz',
                                  content_type='application/gzip', token=TOKEN, body='b', open_response=opener)
    assert status.startswith('RAW_UPLOADED bytes=10 ') and TOKEN not in status
    assert seen[0].full_url == f'https://api.github.com/repos/{sus.RAW_REPO}/releases'
    assert [r.full_url.rsplit('=', 1)[1] for r in seen[1:]] == ['a.json.gz', 'a.json.gz.sha256']
    assert all(r.get_header('Authorization') == 'Bearer ' + TOKEN and
               r.get_header('User-agent') == 'investment-system-raw-archive' for r in seen)


def test_read_shard_roundtrip_and_sha_check():
    tag = 'iex-v4-monthend-20261023-shard0'
    data = gzip.compress(json.dumps({'schema': 'iex-monthend/1', 'months': {}}).encode(), mtime=0)
    assets = {1: data, 2: f'{hashlib.sha256(data).hexdigest()}  {tag}.json.gz\n'.encode()}
    release = {'id': 9, 'assets': [{'id': 1, 'name': tag + '.json.gz'}, {'id': 2, 'name': tag + '.json.gz.sha256'}]}

    def call(method, url, **kw):
        if url.endswith('/releases/tags/' + tag):
            return 200, {}, json.dumps(release).encode()
        if '/releases/assets/' in url:
            return 302, {'Location': 'https://objects.example.invalid/' + url.rsplit('/', 1)[1]}, b''
        assert kw.get('auth') is False  # the signed location gets no token
        return 200, {}, assets[int(url.rsplit('/', 1)[1])]
    assert bf.read_shard(tag, call=call)['schema'] == 'iex-monthend/1'
    assets[2] = b'0' * 64 + b'\n'
    with pytest.raises(bf.BackfillError, match='SHA256_MISMATCH'):
        bf.read_shard(tag, call=call)


# ---- split check ----

def facts(covers, ratios):
    return {'facts': {'dei': {'EntityCommonStockSharesOutstanding': {'units': {'shares': [
                {'end': e, 'val': v, 'filed': e, 'form': '10-Q'} for e, v in covers]}}},
            'us-gaap': {'StockholdersEquityNoteStockSplitConversionRatio1': {'units': {'pure': [
                {'val': r, 'filed': '2024-08-01', 'accn': 'A-1'} for r in ratios]}}}}}


def test_derive_events_needs_ratio_fact_and_matching_cover_jump():
    f = facts([('2024-03-01', 100.0), ('2024-05-24', 99.0), ('2024-08-23', 985.0), ('2024-11-15', 980.0)], [10])
    assert sc.derive_events(f) == [{'ratio': 10.0, 'low': '2024-05-24', 'high': '2024-08-23', 'ratio_fact_accn': 'A-1',
                                     'ratio_fact_filed': '2024-08-01'}]
    assert sc.derive_events(facts([('2024-05-24', 99.0), ('2024-08-23', 985.0)], [4])) == []  # unmatched jump
    assert sc.derive_events(facts([('2024-05-24', 100.0), ('2024-08-23', 101.0)], [10])) == []  # fact without a jump
    rev = sc.derive_events(facts([('2024-05-24', 800.0), ('2024-08-23', 100.0)], [8]))  # reverse split 1:8
    assert rev[0]['ratio'] == 0.125


def test_factor_and_ambiguous_days():
    ev = [{'ratio': 10.0, 'low': '2024-05-24', 'high': '2024-08-23'}]
    assert sc.factor('2024-01-31', ev, '2026-07-31') == 10.0
    assert sc.factor('2025-01-31', ev, '2026-07-31') == 1.0
    assert sc.factor('2024-06-28', ev, '2026-07-31') is None  # inside the bracket
    assert sc.factor('2024-01-31', ev, '2024-06-30') is None  # basis date inside the bracket
    assert sc.factor('2024-01-31', ev, '2024-03-31') == 1.0  # split after the latest basis: not applied


YEARS = ('2021-12-31', '2022-12-31', '2023-12-31', '2024-12-31', '2025-12-31')
EPS = (2.0, 2.2, 2.5, 2.4, 2.8)       # synthetic EBIT/share on the latest (post-split) basis
TRUE_YIELD = (0.05, 0.045, 0.055, 0.05, 0.048)


def synthetic_prices(split_after: int, ratio: float, raw=True):
    """{YYYY-MM: (day, price)}: price = EPS / true yield on the latest basis, times the ratio before the split if raw."""
    return {y[:7]: (y, e / t * (ratio if raw and i <= split_after else 1.0))
            for i, (y, e, t) in enumerate(zip(YEARS, EPS, TRUE_YIELD))}


def test_check_stock_raw_mismatch_fixed_by_basis_factor():
    ev = [{'ratio': 10.0, 'low': '2024-02-01', 'high': '2024-05-01'}]
    hist = [{'fiscal_year_end': y, 'value': e} for y, e in zip(YEARS, EPS)]
    (r,) = sc.check_stock(hist, synthetic_prices(2, 10.0), ev, '2026-06-30')
    assert (r['pre'], r['post']) == (3, 2)
    assert r['raw'] == 'MISMATCH' and r['adjusted'] == 'CONSISTENT' and r['verdict'] == 'RAW_MISMATCH_FIXED_BY_F'
    assert r['raw_jump'] == pytest.approx(0.1 * 0.05 / 0.049, rel=1e-9) and r['adjusted_jump'] == pytest.approx(0.05 / 0.049)
    line = sc.report_line('NASDAQ:SYN', r)
    assert 'MISMATCH' in line and 'CONSISTENT' in line
    for p in synthetic_prices(2, 10.0).values():  # no price and no yield level in the report
        assert f'{p[1]:.2f}' not in line and f'{p[1]:.3g}' not in line
    assert '0.05' not in line and '0.045' not in line
    # Already split-adjusted prices: no raw jump, and applying F would break it (adjusted jump ~ R).
    (a,) = sc.check_stock(hist, synthetic_prices(2, 10.0, raw=False), ev, '2026-06-30')
    assert a['raw'] == 'NO_JUMP' and a['adjusted'] == 'MISMATCH' and a['verdict'] == 'RAW_CONSISTENT'
    assert sc.overall({'A': [a], 'B': [a], 'C': [a]})['decision'] == 'SPLIT_RULE_APPLIES_AS_IS'
    assert sc.overall({'A': [r], 'B': [a], 'C': [a]})['decision'].startswith('MIXED')
    assert sc.overall({'A': [r], 'B': [r]})['decision'].startswith('INSUFFICIENT')


def test_check_stock_not_testable_without_both_sides():
    ev = [{'ratio': 4.0, 'low': '2020-05-01', 'high': '2020-08-01'}]
    hist = [{'fiscal_year_end': y, 'value': e} for y, e in zip(YEARS, EPS)]
    (r,) = sc.check_stock(hist, synthetic_prices(-1, 4.0), ev, '2026-06-30')
    assert r['verdict'] == 'NOT_TESTABLE' and 'raw_jump' not in r


def test_run_check_end_to_end_from_shard_payloads():
    splits = {f'NASDAQ:S{i}': ({'ratio': r, 'low': '2024-02-01', 'high': '2024-05-01'},) for i, r in enumerate((10.0, 20.0, 3.0))}
    records, months = {}, {}
    for code, (ev,) in splits.items():
        records[code] = {'v_inputs_v2': {'ebit_per_share_history': [{'fiscal_year_end': y, 'value': e} for y, e in zip(YEARS, EPS)],
                                         'diluted_shares': {'period_end': '2026-06-30'}}}
        for m, (day, px) in synthetic_prices(2, ev['ratio']).items():
            entry = months.setdefault(m, {'date': day.replace('-', ''), 'codes': {}, 'symbols': {}})
            sym = code.split(':')[1]
            entry['codes'][code] = sym
            entry['symbols'][sym] = {'status': 'ROUND', 'price_e4': round(px * 1e4), 'ts_ns': 1, 'n': 1}
    shard = {'schema': 'iex-monthend/1', 'months': months}
    results, summary = sc.run_check({'records': records}, [shard], splits)
    assert summary['stocks_tested'] == 3 and summary['fixed_by_f'] == 3
    assert summary['decision'].startswith('SPLIT_RULE_NEEDS_BASIS_FACTOR')
    plan = {'months': [{'month': m, 'symbols': sorted(v['symbols'])} for m, v in months.items()]}
    assert sc.coverage(plan, [shard])['complete_months'] == len(months)
    assert sc.coverage(dict(plan, months=plan['months'] + [{'month': '2026-01', 'symbols': []}]), [shard])['missing_months'] == ['2026-01']


def test_verified_split_table_matches_requested_examples():
    expect = {'NASDAQ:NVDA': (10.0, '2024-06'), 'NASDAQ:AMZN': (20.0, '2022-06'), 'NASDAQ:WMT': (3.0, '2024-02'),
              'NYSE:CMG': (50.0, '2024-06'), 'NASDAQ:AVGO': (10.0, '2024-07'), 'NASDAQ:LRCX': (10.0, '2024-10'),
              'NYSE:DECK': (6.0, '2024-09'), 'NASDAQ:CTAS': (4.0, '2024-09'), 'NASDAQ:ORLY': (15.0, '2025-06')}
    for code, (ratio, month) in expect.items():
        assert any(e['ratio'] == ratio and e['low'][:7] <= month <= e['high'][:7] for e in sc.VERIFIED_SPLITS[code]), code


def test_workflow_is_manual_private_and_counts_only():
    text = (Path(__file__).resolve().parents[2] / '.github/workflows/iex-v4-backfill.yml').read_text()
    body = '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('#'))
    on = body.split('\non:\n', 1)[1].split('\npermissions:', 1)[0]
    # Owner go 2026-10-23: one run from this branch only (push of the workflow file), guarded by the existing-release check;
    # the push trigger is removed after the run. No schedule, never another branch.
    assert 'schedule:' not in on and 'workflow_dispatch:' in on
    assert 'push:' not in on  # the one push-triggered run completed (run 39945012772); trigger removed per the owner
    if 'push:' in on:
        assert "branches: [claude/iex-v4-backfill]" in on and "paths: ['.github/workflows/iex-v4-backfill.yml']" in on
        assert "t.startswith('iex-v4-monthend-')" in body and 'BACKFILL_SKIPPED' in body
    assert 'permissions:\n  contents: read\n' in body and 'group: iex-v4-backfill' in body
    assert 'upload-artifact' not in body and 'actions/cache' not in body and 'download-artifact' not in body
    assert body.count('persist-credentials: false') == body.count('actions/checkout@') == 3
    assert 'timeout-minutes: 120' in body and 'shard: [0, 1, 2, 3, 4, 5]' in body
    # The token appears only in the env of the plan step (existing-release check), the backfill step and the read-back check step.
    assert body.count('secrets.RAW_REPO_TOKEN') == 3
    for block in body.split('      - name: ')[1:]:
        if 'secrets.RAW_REPO_TOKEN' in block:
            assert block.startswith(('Plan (counts only)', 'Backfill shard', 'Coverage + split consistency'))
    assert "default: 'true'" in body  # plan_only by default: the first dispatch only prints counts
