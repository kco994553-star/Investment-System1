"""Universe504 price-free Q·G projection from the daily SEC shard (synthetic SEC data and transports only)."""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import urllib.error

import pytest

from investment_system.providers.sec_collection import SecResponse
from investment_system.providers.sec_universe_collection import daily_partition, universe_registry
from investment_system.universe import sec_universe_qg as q
from investment_system.universe import sec_universe_shares as shares

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 10, 22, 30, tzinfo=timezone.utc)
UA = 'Synthetic Tester tester@example.com'


def load_tool(name):
    spec = importlib.util.spec_from_file_location('_qg_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sec_bytes(cik, ticker='NVDA', exchange='Nasdaq', revenues=(100, 115, 132.25, 152.0875), extra_rows=(), canary=True):
    """Four annual 10-K revenue facts + a 10-Q cover share count (both shard outputs from one pair of bodies)."""
    rows, forms = [], []
    for year, value in zip(range(2022, 2026), revenues):
        accn = f'{cik}-{year + 1 - 2000:02d}-000001'
        filed = f'{year + 1}-02-01'
        rows.append({'start': f'{year}-01-01', 'end': f'{year}-12-31', 'val': value, 'accn': accn, 'form': '10-K', 'filed': filed, 'fp': 'FY', 'fy': year})
        forms.append((accn, '10-K', filed, f'{year}-12-31', f'demo-{year}1231.htm'))
    rows.extend(extra_rows)
    q_accn = f'{cik}-26-000009'
    forms.append((q_accn, '10-Q', '2026-10-01', '2026-09-30', 'demo-20260930.htm'))
    us_gaap = {'Revenues': {'units': {'USD': rows}}}
    if canary:
        us_gaap['StockPrice'] = {'units': {'USD': [{'val': 99999}]}}
    facts = {'cik': int(cik), 'facts': {'us-gaap': us_gaap, 'dei': {'EntityCommonStockSharesOutstanding': {'units': {'shares': [
        {'val': 100, 'end': '2026-09-25', 'filed': '2026-10-01', 'form': '10-Q', 'accn': q_accn}]}}}}}
    subs = {'cik': int(cik), 'tickers': [ticker], 'exchanges': [exchange], 'filings': {'recent': {
        'accessionNumber': [f[0] for f in forms], 'form': [f[1] for f in forms], 'filingDate': [f[2] for f in forms],
        'reportDate': [f[3] for f in forms], 'acceptanceDateTime': [f[2] + 'T12:00:00Z' for f in forms],
        'primaryDocument': [f[4] for f in forms]}}}
    return json.dumps(facts).encode(), json.dumps(subs).encode()


def row(cik='0001045810', when=NOW, **kwargs):
    facts, subs = sec_bytes(cik, **kwargs)
    return q.build_issuer_row(cik=cik, companyfacts_body=facts, submissions_body=subs, acquired_at=when)


# ---- same methodology as the TARGET sec-qg-factors.json ----
def test_universe_row_equals_target_qg_factors_for_the_same_bytes(tmp_path):
    from investment_system.product.public_engine_screens import generate_screen_bundle
    facts, subs = sec_bytes('0001045810')
    (tmp_path / 'f.json').write_bytes(facts)
    (tmp_path / 's.json').write_bytes(subs)
    manifest = {'schema_version': 1, 'sec': [{'company_id': 'nvda', 'companyfacts': 'f.json', 'submissions': 's.json',
                                              'acquired_at': NOW.isoformat(), 'synthetic': False}], 'macro': [], 'thirteen_f': []}
    target = generate_screen_bundle(manifest=manifest, input_root=tmp_path, as_of=NOW, stale_after=timedelta(days=1))
    target_row = target['sec-qg-factors.json']['data']['companies']['nvda']
    universe = q.build_issuer_row(cik='0001045810', companyfacts_body=facts, submissions_body=subs, acquired_at=NOW)
    assert set(universe['factors']) == set(target_row['factors']) == set(q.FACTORS) and len(q.FACTORS) == 13
    assert {k: v['score'] for k, v in target_row['factors'].items()} == universe['factors']
    assert universe['factors']['revenue_growth'] is not None and universe['factors']['competitive_advantage'] is None
    assert universe['state'] == target_row['state'] == 'LIVE' and universe['reason_codes'] == []
    assert universe['source_sha256'] == target_row['source_hashes'] == {'companyfacts': sha256(facts).hexdigest(), 'submissions': sha256(subs).hexdigest()}


def test_m1_safe_fast_path_matches_the_generic_serialization():
    """The plain-JSON fast path in providers.sec_m1._safe is a cost change only (same output as the generic path)."""
    import math
    from investment_system.contracts.enums import ProfileKind
    from investment_system.contracts.models import _to_json
    from investment_system.providers.sec_m1 import _safe

    def generic(value):
        value = _to_json(value)
        if isinstance(value, dict):
            return {str(k): generic(v) for k, v in value.items()}
        if isinstance(value, list):
            return [generic(v) for v in value]
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    sample = {'a': [1, 2.5, float('nan'), float('inf'), None, True, 'x', (3, {'d': date(2026, 1, 2)})], 1: {'t': NOW, 'k': ProfileKind.FINANCIAL},
              'nested': [{'v': [{'w': -0.0}]}], 'tuple': ('a', float('-inf'))}
    assert _safe(sample) == generic(sample)
    assert json.dumps(_safe(sample), allow_nan=False)


def test_factor_set_is_q_plus_g_without_v():
    from investment_system.qgv.factors import G_WEIGHTS, Q_WEIGHTS, V_INITIAL_PRIOR
    from investment_system.product.public_engine_screens import FACTORS
    assert set(q.FACTORS) == set(Q_WEIGHTS) | set(G_WEIGHTS) == FACTORS
    assert not set(q.FACTORS) & set(V_INITIAL_PRIOR)


def test_no_price_value_or_unrelated_source_text_reaches_the_row():
    r = row()
    text = json.dumps(r)
    assert '99999' not in text and 'StockPrice' not in text and 'price' not in text.lower()
    assert r['acquired_at'] == '2026-10-10T22:30:00Z' and r['cik'] == '0001045810'


@pytest.mark.parametrize('kwargs,reason', [
    ({'revenues': ()}, 'M1_NOT_AVAILABLE'),
    ({'extra_rows': ({'start': '2025-01-01', 'end': '2025-12-31', 'val': 999, 'accn': '0001045810-26-000001', 'form': '10-K',
                      'filed': '2026-02-01', 'fp': 'FY', 'fy': 2025},)}, 'UNRESOLVED_CURRENT_FACT_AMBIGUITY'),
])
def test_unavailable_or_ambiguous_m1_is_not_available_with_reason_never_zero(kwargs, reason):
    r = row(**kwargs)
    assert r['state'] == 'NOT_AVAILABLE' and r['reason_codes'] == [reason]
    assert all(v is None for v in r['factors'].values())
    assert r['acquired_at'] is not None and r['source_sha256']['companyfacts'] is not None


def test_cik_mismatch_and_invalid_bytes_are_fixed_reasons():
    facts, subs = sec_bytes('0001045810')
    mismatch = q.build_issuer_row(cik='0000000007', companyfacts_body=facts, submissions_body=subs, acquired_at=NOW)
    assert mismatch['reason_codes'] == ['M1_NOT_AVAILABLE'] and mismatch['state'] == 'NOT_AVAILABLE'
    for bad in (b'{"cik":1,"a":NaN}', b'{"cik":1,"cik":2}', b'\xff', b'[]'):
        r = q.build_issuer_row(cik='0001045810', companyfacts_body=bad, submissions_body=subs, acquired_at=NOW)
        assert r['state'] == 'NOT_AVAILABLE' and r['reason_codes'] in (['INVALID_INPUT'], ['M1_NOT_AVAILABLE'])
    assert q.build_issuer_row(cik='1', companyfacts_body=facts, submissions_body=subs, acquired_at=NOW)['cik'] is None
    naive = q.build_issuer_row(cik='0001045810', companyfacts_body=facts, submissions_body=subs, acquired_at=NOW.replace(tzinfo=None))
    assert naive['reason_codes'] == ['INVALID_INPUT'] and naive['acquired_at'] is None


def test_issuer_codes_share_one_row():
    facts, subs = sec_bytes('0001652044', ticker='GOOGL')
    rows = q.build_issuer_records(codes=('NASDAQ:GOOGL', 'NASDAQ:GOOG'), cik='0001652044', companyfacts_body=facts,
                                  submissions_body=subs, acquired_at=NOW)
    assert rows['NASDAQ:GOOGL'] == rows['NASDAQ:GOOG'] and rows['NASDAQ:GOOGL'] is not rows['NASDAQ:GOOG']


# ---- merge (same rules as sec-universe-shares.json) ----
def merged(updates=None, previous=None, as_of=NOW, **kwargs):
    return q.merge(previous, updates or {}, as_of=as_of, shard_index=0, **kwargs)


def test_merge_covers_504_codes_keeps_rows_with_own_time_and_ages_them():
    p = merged({'NASDAQ:NVDA': row()}, unresolved={'BATS:CBOE'})
    assert p['code_count'] == 504 and set(p['records']) == set(shares.universe_codes()) and p['state'] == 'LIVE'
    assert p['records']['BATS:CBOE']['reason_codes'] == ['CIK_UNRESOLVED']
    assert p['records']['NYSE:MMM']['reason_codes'] == ['NOT_COLLECTED'] and all(v is None for v in p['records']['NYSE:MMM']['factors'].values())
    assert p['config_status'] == 'DEFAULT_V0_UNCALIBRATED' and p['method_status'] == 'PROVISIONAL_UNCALIBRATED'
    assert p['stale_after_seconds'] == 14 * 86400 and p['shard_count'] == 7
    later = NOW + timedelta(days=3)
    # Owner rule 2026-10-17: a successful collection without scores is published (its reason and its own acquired_at),
    # never replaced by the kept scores; a row without its own collection record (tool fallback) never erases them.
    unavailable = row(revenues=(), when=later)
    replaced = merged({'NASDAQ:NVDA': unavailable}, previous=p, as_of=later)
    assert replaced['records']['NASDAQ:NVDA'] == unavailable and unavailable['reason_codes'] == ['M1_NOT_AVAILABLE']
    assert unavailable['acquired_at'] == '2026-10-13T22:30:00Z'
    failed = q.empty_record(cik='0001045810', reasons=('INVALID_INPUT',))
    kept = merged({'NASDAQ:NVDA': failed}, previous=p, as_of=later)
    assert kept['records']['NASDAQ:NVDA'] == p['records']['NASDAQ:NVDA']
    stale = merged(previous=kept, as_of=NOW + timedelta(days=15))
    nvda = stale['records']['NASDAQ:NVDA']
    assert nvda['state'] == 'STALE' and nvda['reason_codes'] == ['STALE_INPUT'] and nvda['factors'] == p['records']['NASDAQ:NVDA']['factors']
    assert stale['state'] == 'STALE' and stale['reason_codes'] == ['STALE_INPUT']
    refreshed = merged({'NASDAQ:NVDA': row(when=NOW + timedelta(days=15))}, previous=stale, as_of=NOW + timedelta(days=15))
    assert refreshed['records']['NASDAQ:NVDA']['state'] == 'LIVE' and refreshed['records']['NASDAQ:NVDA']['acquired_at'] == '2026-10-25T22:30:00Z'


def test_merge_downgrades_an_invalid_new_row_instead_of_breaking_the_file():
    bad = row()
    bad['factors']['roic_wacc'] = 101
    p = merged({'NASDAQ:NVDA': bad})
    assert p['records']['NASDAQ:NVDA']['reason_codes'] == ['INVALID_INPUT'] and p['records']['NASDAQ:NVDA']['cik'] == '0001045810'
    assert p['records']['NASDAQ:NVDA']['state'] == 'NOT_AVAILABLE'


def test_size_at_504_codes_stays_far_below_the_public_file_limit():
    empty = len(q.encode(merged()))
    full_row = dict(row(), factors={f: 55.55555555555556 for f in q.FACTORS})
    full = len(q.encode(merged({code: full_row for code in shares.universe_codes()})))
    assert empty < 300 * 1024 and full < 450 * 1024 < q.MAX_BYTES


# ---- strict validators (Python; JS parity through the shared vectors) ----
def test_vectors_fixture_is_regenerated_from_the_python_validator():
    reference = load_tool('sec_universe_qg_reference')
    fixture = json.loads((ROOT / 'tests/fixtures/sec_universe_qg_vectors_v1.json').read_text())
    assert fixture == json.loads(json.dumps(reference.build()))
    assert fixture['synthetic'] is True and len(fixture['cases']) >= 40
    assert [c['id'] for c in fixture['cases'] if c['valid']] == ['base_valid', 'null_shard_and_registry_valid', 'zero_score_is_a_score_not_missing',
                                                                           'withdrawn_valid']


@pytest.mark.skipif(shutil.which('node') is None, reason='Node runtime required')
def test_js_validator_reaches_the_python_verdict_on_every_vector():
    result = subprocess.run(['node', str(ROOT / 'tools/sec_universe_qg_node_test.js')], text=True, capture_output=True, timeout=120)
    assert result.returncode == 0 and 'fail=0' in result.stdout


@pytest.mark.parametrize('path,value', [
    (('price',), 1), (('records', 'NASDAQ:NVDA', 'factors', 'roic_wacc'), -1), (('records', 'NASDAQ:NVDA', 'factors', 'fundamental_value'), 1),
    (('records', 'NASDAQ:NVDA', 'state'), 'STALE'), (('records', 'NYSE:MMM', 'factors', 'roic_wacc'), 5), (('code_count',), 503),
])
def test_validator_is_strict(path, value):
    p = merged({'NASDAQ:NVDA': row()})
    target = p
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError, match='SEC_UNIVERSE_QG_INVALID'):
        q.require_universe_qg(p)


def test_json_parser_rejects_nonfinite_duplicates_and_oversize():
    for body in (b'{"a":NaN}', b'{"a":1,"a":2}', b'\xff', b'x' * (q.MAX_BYTES + 1)):
        with pytest.raises(ValueError, match='SEC_UNIVERSE_QG_INVALID'):
            q.parse_json(body)
    assert q.require_universe_qg(q.parse_json(q.encode(merged())))['state'] == 'NOT_AVAILABLE'


def test_pages_guard_allows_valid_file_and_rejects_tampered_values(tmp_path):
    build = load_tool('build_pages_cockpit')
    guard = load_tool('pages_artifact_guard')
    site = tmp_path / 'site'
    build.build_public_cockpit(site)
    assert not (site / q.FILENAME).exists()  # offline builds do not publish it (404 like the shares file)
    (site / q.FILENAME).write_bytes(q.encode(merged({'NASDAQ:NVDA': row()})))
    assert guard.scan_artifact(site)['pages_artifact_guard'] == 'PASS'
    tampered = json.loads((site / q.FILENAME).read_text())
    tampered['records']['NASDAQ:NVDA']['factors']['roic_wacc'] = 101
    (site / q.FILENAME).write_text(json.dumps(tampered))
    receipt = guard.scan_artifact(site)
    assert receipt['pages_artifact_guard'] == 'FAIL' and receipt['violations'].get('universe_qg_boundary') == 1
    tampered = json.loads(q.encode(merged({'NASDAQ:NVDA': row()})))
    tampered['records']['NASDAQ:NVDA']['price'] = 1
    (site / q.FILENAME).write_text(json.dumps(tampered))
    assert guard.scan_artifact(site)['violations'].get('sensitive_json_fields') == 1


# ---- daily shard tool: one fetch feeds shares + Q·G (mocked transport only) ----
ISSUERS = {'0000000001': ('ADBE', 'Nasdaq'), '0000000002': ('BRK-B', 'NYSE'), '0000000003': ('MMM', 'NYSE')}


def ticker_body():
    return json.dumps({'fields': ['cik', 'name', 'ticker', 'exchange'],
                       'data': [[int(c), 'Synthetic', t, e] for c, (t, e) in ISSUERS.items()]}).encode()


def day_for(cik):
    registry = universe_registry(ticker_body())
    for offset in range(7):
        day = date(2026, 10, 10) + timedelta(days=offset)
        if any(i.cik == cik for i in daily_partition(registry, shard_count=7, shard_index=day.toordinal() % 7)):
            return datetime(day.year, day.month, day.day, 22, 30, tzinfo=timezone.utc)
    raise AssertionError


def cover(cik, symbol):
    ns = ('<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:xbrli="http://www.xbrl.org/2003/instance" '
          'xmlns:dei="http://xbrl.sec.gov/dei/2026">')
    body = ns + (f'<context id="a"><entity><identifier scheme="http://www.sec.gov/CIK">{cik}</identifier></entity>'
                 '<period><instant>2026-09-25</instant></period></context><unit id="u"><measure>xbrli:shares</measure></unit>')
    body += f'<dei:TradingSymbol contextRef="a">{symbol}</dei:TradingSymbol><dei:Security12bTitle contextRef="a">Common Stock</dei:Security12bTitle>'
    body += '<dei:EntityCommonStockSharesOutstanding contextRef="a" unitRef="u">100</dei:EntityCommonStockSharesOutstanding>'
    return (body + '</xbrl>').encode()


def transport_for(calls, *, fail=False):
    def transport(url, *, headers, timeout, max_body_bytes):
        calls.append(url)
        if url.endswith('company_tickers_exchange.json'):
            return SecResponse(200, ticker_body(), final_url=url)
        if fail:
            return SecResponse(403, b'', final_url=url)
        if '/Archives/' in url:
            cik = url.split('/data/')[1].split('/')[0].zfill(10)
            return SecResponse(200, cover(cik, ISSUERS[cik][0]), final_url=url)
        cik = url.split('CIK')[-1].split('.')[0]
        facts, subs = sec_bytes(cik, *ISSUERS[cik])
        return SecResponse(200, facts if 'companyfacts' in url else subs, final_url=url)
    return transport


def client_kwargs(transport, when):
    clock = [0.0]
    def sleep(seconds):
        clock[0] += seconds
    return {'transport': transport, 'sleep': sleep, 'monotonic': lambda: clock[0], 'now': lambda: when}


class Response:
    def __init__(self, url, body, status=200):
        self.url, self.body, self.status = url, body, status
    def geturl(self):
        return self.url
    def read(self, n=-1):
        return self.body if n < 0 else self.body[:n]
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False


def pages(bodies):
    """Previous Pages copies by file name; missing name -> 404; an exception instance is raised."""
    def opener(request, **_):
        name = request.full_url.rsplit('/', 1)[1]
        value = bodies.get(name)
        if value is None:
            raise urllib.error.HTTPError(request.full_url, 404, '', {}, None)
        if isinstance(value, Exception):
            raise value
        return Response(request.full_url, value)
    return opener


def test_tool_one_fetch_feeds_shares_and_qg_without_extra_requests(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    when = day_for('0000000002')
    calls = []
    code = tool.run(tmp_path, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when,
                    client_kwargs=client_kwargs(transport_for(calls), when), open_previous=pages({}))
    out = capsys.readouterr().out
    assert code == 0 and sorted(p.name for p in tmp_path.iterdir()) == ['sec-qgv2.json', q.FILENAME, shares.FILENAME]
    shard = [i.cik for i in daily_partition(universe_registry(ticker_body()), shard_count=7, shard_index=when.date().toordinal() % 7)]
    # Exactly the shares step's requests: ticker file + companyfacts + submissions + cover per shard issuer, none repeated.
    assert len(calls) == len(set(calls)) == 1 + 3 * len(shard)
    payload = q.require_universe_qg(json.loads((tmp_path / q.FILENAME).read_text()))
    brk = payload['records']['NYSE:BRK.B']
    assert brk['state'] == 'LIVE' and brk['cik'] == '0000000002' and brk['factors']['revenue_growth'] is not None
    assert payload['last_shard_index'] == when.date().toordinal() % 7 and payload['registry_sha256'] == sha256(ticker_body()).hexdigest()
    assert payload['records']['BATS:CBOE']['reason_codes'] == ['CIK_UNRESOLVED']
    assert shares.require_universe_shares(json.loads((tmp_path / shares.FILENAME).read_text()))['records']['NYSE:BRK.B']['shares'] == 100
    line = [l for l in out.splitlines() if l.startswith('SEC_UNIVERSE_QG shard=')]
    assert len(line) == 1 and f'codes={len(shard)}' in line[0] and 'live=' in line[0]
    for secret in (UA, 'tester@', '0000000002', 'sec.gov', 'BRK', 'revenue'):
        assert secret not in out
    text = (tmp_path / q.FILENAME).read_text().lower()
    assert 'price' not in text and 'rank' not in text and 'market_cap' not in text and '99999' not in text


def test_tool_keeps_previous_qg_rows_from_other_shards_and_on_total_failure(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    previous = q.encode(merged({'NASDAQ:NVDA': row()}))
    when = day_for('0000000002') + timedelta(days=7)
    code = tool.run(tmp_path, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when,
                    client_kwargs=client_kwargs(transport_for([], fail=True), when), open_previous=pages({q.FILENAME: previous}))
    out = capsys.readouterr().out
    assert code == 0 and 'SEC_UNIVERSE_QG PREVIOUS_RESTORED' in out and 'SHARD_ALL_FAILED' in out
    kept = json.loads((tmp_path / q.FILENAME).read_text())['records']['NASDAQ:NVDA']
    assert kept['acquired_at'] == '2026-10-10T22:30:00Z' and kept['factors']['revenue_growth'] is not None
    assert kept['state'] == ('STALE' if when - NOW > timedelta(days=14) else 'LIVE')


def test_tool_qg_previous_network_failure_writes_nothing_and_exits_1(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    shares_body = shares.encode(shares.merge(None, {}, as_of=NOW, shard_index=0))
    code = tool.run(tmp_path, live=True, environ={'SEC_USER_AGENT': UA},
                    open_previous=pages({shares.FILENAME: shares_body, q.FILENAME: urllib.error.URLError('synthetic')}))
    assert code == 1 and 'SEC_UNIVERSE_QG PREVIOUS_FETCH_FAILED' in capsys.readouterr().out and not list(tmp_path.iterdir())


def test_tool_preserve_only_restores_qg_and_discards_invalid_copy(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    body = q.encode(merged({'NASDAQ:NVDA': row()}))
    assert tool.run(tmp_path, live=False, preserve_only=True, now=lambda: NOW + timedelta(hours=1), open_previous=pages({q.FILENAME: body})) == 0
    assert 'SEC_UNIVERSE_QG PREVIOUS_RESTORED' in capsys.readouterr().out
    assert sorted(p.name for p in tmp_path.iterdir()) == [q.FILENAME]
    assert json.loads((tmp_path / q.FILENAME).read_text())['records']['NASDAQ:NVDA']['factors']['revenue_growth'] is not None
    other = tmp_path / 'other'
    other.mkdir()
    assert tool.run(other, live=False, preserve_only=True, open_previous=pages({q.FILENAME: b'{"price":1}'})) == 0
    out = capsys.readouterr().out
    assert 'SEC_UNIVERSE_QG PREVIOUS_DISCARDED' in out and 'SEC_UNIVERSE_QG PREVIOUS_NOT_AVAILABLE' in out and not list(other.iterdir())


def test_tool_invalid_previous_qg_starts_fresh_on_live_run(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    when = day_for('0000000001')
    assert tool.run(tmp_path, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when,
                    client_kwargs=client_kwargs(transport_for([]), when), open_previous=pages({q.FILENAME: b'{"a":NaN}'})) == 0
    assert 'SEC_UNIVERSE_QG PREVIOUS_DISCARDED' in capsys.readouterr().out
    assert q.require_universe_qg(json.loads((tmp_path / q.FILENAME).read_text()))['records']['NASDAQ:ADBE']['state'] == 'LIVE'


def test_tool_qg_failure_never_changes_the_shares_row(tmp_path, monkeypatch):
    tool = load_tool('sec_universe_shares')
    when = day_for('0000000002')
    baseline = tmp_path / 'a'
    baseline.mkdir()
    tool.run(baseline, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when,
             client_kwargs=client_kwargs(transport_for([]), when), open_previous=pages({}))
    def boom(**_):
        raise RuntimeError('synthetic')
    monkeypatch.setattr(tool.qg, 'build_issuer_records', boom)
    broken = tmp_path / 'b'
    broken.mkdir()
    assert tool.run(broken, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when,
                    client_kwargs=client_kwargs(transport_for([]), when), open_previous=pages({})) == 0
    assert (broken / shares.FILENAME).read_bytes() == (baseline / shares.FILENAME).read_bytes()
    assert json.loads((broken / q.FILENAME).read_text())['records']['NYSE:BRK.B']['reason_codes'] == ['INVALID_INPUT']


# ---- workflows ----
def test_daily_workflow_runs_the_combined_shard_and_ui_deploy_preserves_it():
    daily = (ROOT.parent / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    assert 'tests/test_sec_universe_qg.py' in daily
    step = daily.index('python implementation/tools/sec_universe_shares.py --live --out "$RUNNER_TEMP/public-cockpit"')
    assert daily.index('pages_artifact_guard.py --artifact-dir', step) < daily.index('actions/upload-pages-artifact')
    pages_yml = (ROOT.parent / '.github/workflows/cockpit-pages.yml').read_text()
    assert 'python implementation/tools/sec_universe_shares.py --preserve-only --out "$RUNNER_TEMP/public-cockpit"' in pages_yml
    empty = (ROOT / 'tools/empty_public_screens.js').read_text()
    assert "'sec-universe-qg.json'" in empty
