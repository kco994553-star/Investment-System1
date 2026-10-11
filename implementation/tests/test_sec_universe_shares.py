"""Universe504 public SEC shares projection, collection merge and guard (synthetic SEC data only)."""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.error

import pytest

from investment_system.providers.sec_collection import SecResponse
from investment_system.providers.sec_universe_collection import universe_registry, daily_partition
from investment_system.universe import sec_universe_shares as m
from investment_system.providers import sec_m3_adapter as m3

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 10, 22, 30, tzinfo=timezone.utc)
UA = 'Synthetic Tester tester@example.com'
TOKEN = 'synthetic-raw-token-value-0123456789'


def load_tool(name):
    spec = importlib.util.spec_from_file_location('_t_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def accn(cik):
    return cik + '-26-000001'


def facts(cik, shares=100):
    row = {'val': shares, 'end': '2026-09-25', 'filed': '2026-10-01', 'form': '10-Q', 'accn': accn(cik)}
    return json.dumps({'cik': int(cik), 'facts': {'dei': {'EntityCommonStockSharesOutstanding': {'units': {'shares': [row]}}}}}).encode()


def submissions(cik, ticker, exchange='Nasdaq'):
    return json.dumps({'cik': int(cik), 'tickers': [ticker], 'exchanges': [exchange], 'filings': {'recent': {
        'accessionNumber': [accn(cik)], 'form': ['10-Q'], 'filingDate': ['2026-10-01'],
        'acceptanceDateTime': ['2026-10-01T12:00:00Z'], 'reportDate': ['2026-09-30'], 'primaryDocument': ['demo-20260930.htm']}}}).encode()


def cover(cik, symbol, shares=100, multi=False, title='Common Stock'):
    ns = ('<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:xbrli="http://www.xbrl.org/2003/instance" '
          'xmlns:g="http://fasb.org/us-gaap/2026" xmlns:dei="http://xbrl.sec.gov/dei/2026" xmlns:d="http://xbrl.org/2006/xbrldi">')
    seg = lambda member: f'<segment><d:explicitMember dimension="g:StatementClassOfStockAxis">g:{member}</d:explicitMember></segment>' if member else ''
    ctx = lambda id_, member: f'<context id="{id_}"><entity><identifier scheme="http://www.sec.gov/CIK">{cik}</identifier>{seg(member)}</entity><period><instant>2026-09-25</instant></period></context>'
    body = ns + ctx('a', 'CommonClassAMember' if multi else None) + '<unit id="u"><measure>xbrli:shares</measure></unit>'
    body += f'<dei:TradingSymbol contextRef="a">{symbol}</dei:TradingSymbol><dei:Security12bTitle contextRef="a">{title}</dei:Security12bTitle>'
    body += f'<dei:EntityCommonStockSharesOutstanding contextRef="a" unitRef="u">{shares}</dei:EntityCommonStockSharesOutstanding>'
    if multi:
        body += ctx('b', 'CommonClassBMember') + '<dei:EntityCommonStockSharesOutstanding contextRef="b" unitRef="u">50</dei:EntityCommonStockSharesOutstanding>'
        body += ctx('t', None) + '<dei:EntityCommonStockSharesOutstanding contextRef="t" unitRef="u">150</dei:EntityCommonStockSharesOutstanding>'
    return (body + '</xbrl>').encode()


def record(code='NASDAQ:ADBE', cik='0000000001', symbol='ADBE', facts_shares=100, **cover_kwargs):
    cover_body = cover_kwargs.pop('cover_body') if 'cover_body' in cover_kwargs else cover(cik, symbol, **cover_kwargs)
    return m.build_share_record(code=code, cik=cik, companyfacts_body=facts(cik, facts_shares), submissions_body=submissions(cik, symbol.replace('.', '-')),
                                acquired_at=NOW, as_of=NOW, cover_xml=cover_body, cover_accession=accn(cik), cover_acquired_at=NOW)


def test_single_class_cover_confirms_and_publishes_no_price():
    r = record()
    assert r['share_class_basis'] == 'SINGLE_CLASS_CONFIRMED' and r['shares'] == 100 and type(r['shares']) is int
    assert r['listing_id'] == 'XNAS:ADBE:0000000001' and r['company_id'] == 'sec_0000000001'
    assert r['basis_evidence'] == {'cover_accn': accn('0000000001'), 'class_count': 0, 'class_members': [], 'listing_class_member': None}
    assert r['state'] == 'LIVE' and r['reason_codes'] == [] and r['concept'] == 'dei:EntityCommonStockSharesOutstanding'
    assert r['source_sha256']['cover'] == sha256(cover('0000000001', 'ADBE')).hexdigest()
    assert not {'price', 'marketcap', 'rank'} & set(json.dumps(r).lower().replace('"', ' ').split())


@pytest.mark.parametrize('facts_shares', [150, 100])
def test_multi_class_cover_uses_listing_class_value_shown_not_summed(facts_shares):
    r = record(facts_shares=facts_shares, multi=True)
    assert r['share_class_basis'] == 'SHARE_CLASS_BASIS' and r['shares'] == 100
    assert r['basis_evidence']['class_members'] == ['CommonClassAMember', 'CommonClassBMember']
    assert r['basis_evidence']['listing_class_member'] == 'CommonClassAMember' and r['reason_codes'] == ['SHARE_CLASS_BASIS']


@pytest.mark.parametrize('kwargs,reason', [
    ({'cover_body': None}, 'COVER_NOT_AVAILABLE'),
    ({'symbol': 'ADBE', 'cover_body': cover('0000000001', 'OTHER')}, 'COVER_UNCONFIRMED'),
    ({'title': 'American Depositary Shares'}, 'BASIS_UNCONFIRMED'),
    ({'facts_shares': 120}, 'COVER_FACT_MISMATCH'),
])
def test_unclear_basis_is_unconfirmed_and_keeps_sec_count_visible(kwargs, reason):
    r = record(**kwargs)
    assert r['share_class_basis'] == 'BASIS_UNCONFIRMED' and r['reason_codes'] == [reason]
    assert r['shares'] == kwargs.get('facts_shares', 100)


def test_identity_failure_publishes_null_never_zero():
    r = m.build_share_record(code='NYSE:ADBE', cik='0000000001', companyfacts_body=facts('0000000001'),
                             submissions_body=submissions('0000000001', 'ADBE'), acquired_at=NOW, as_of=NOW)
    assert r['shares'] is None and r['state'] == 'NOT_AVAILABLE' and r['listing_id'] is None
    assert r['reason_codes'] == ['IDENTITY_UNCONFIRMED']


def merged(updates=None, previous=None, as_of=NOW, **kwargs):
    return m.merge(previous, updates or {}, as_of=as_of, shard_index=0, **kwargs)


def test_merge_covers_all_504_codes_and_keeps_last_values_with_own_time():
    p = merged({'NASDAQ:ADBE': record()}, unresolved={'BATS:CBOE'})
    assert p['code_count'] == 504 and set(p['records']) == set(m.universe_codes())
    assert p['records']['BATS:CBOE']['reason_codes'] == ['CIK_UNRESOLVED']
    assert p['records']['NYSE:MMM']['reason_codes'] == ['NOT_COLLECTED'] and p['records']['NYSE:MMM']['shares'] is None
    assert p['state'] == 'LIVE' and p['config_status'] == 'DEFAULT_V0_UNCALIBRATED'
    later = NOW + timedelta(days=3)
    failed = m.empty_record(cik='0000000001', reasons=('SHARES_NOT_AVAILABLE',))
    kept = merged({'NASDAQ:ADBE': failed}, previous=p, as_of=later)
    assert kept['records']['NASDAQ:ADBE']['shares'] == 100 and kept['records']['NASDAQ:ADBE']['acquired_at'] == '2026-10-10T22:30:00Z'
    stale = merged(previous=kept, as_of=NOW + timedelta(days=15))
    assert stale['records']['NASDAQ:ADBE']['state'] == 'STALE' and stale['records']['NASDAQ:ADBE']['reason_codes'] == ['STALE_INPUT']
    assert stale['state'] == 'STALE' and stale['reason_codes'] == ['STALE_INPUT'] and stale['records']['NASDAQ:ADBE']['shares'] == 100
    refreshed = merged({'NASDAQ:ADBE': record(multi=True)}, previous=stale, as_of=NOW + timedelta(days=15))
    assert refreshed['records']['NASDAQ:ADBE']['share_class_basis'] == 'SHARE_CLASS_BASIS'


def test_merge_downgrades_an_invalid_new_row_instead_of_breaking_the_file():
    bad = dict(record(), shares=0)
    p = merged({'NASDAQ:ADBE': bad})
    assert p['records']['NASDAQ:ADBE']['shares'] is None and p['records']['NASDAQ:ADBE']['reason_codes'] == ['INVALID_INPUT']


def mutate(path, value):
    p = merged({'NASDAQ:ADBE': record()})
    target = p
    for key in path[:-1]:
        target = target[key]
    if value is KeyError:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return p


@pytest.mark.parametrize('path,value', [
    (('price',), 1), (('records', 'NASDAQ:ADBE', 'price'), 1), (('records', 'NASDAQ:ADBE', 'shares'), 0),
    (('records', 'NASDAQ:ADBE', 'shares'), -1), (('records', 'NASDAQ:ADBE', 'shares'), True), (('records', 'NASDAQ:ADBE', 'shares'), '100'),
    (('records', 'NASDAQ:ADBE', 'cik'), '1'), (('records', 'NASDAQ:ADBE', 'listing_id'), 'XNYS:ADBE:0000000001'),
    (('records', 'NASDAQ:ADBE', 'share_class_basis'), 'ALIGNED'), (('records', 'NASDAQ:ADBE', 'state'), 'STALE'),
    (('records', 'NASDAQ:ADBE', 'basis_evidence', 'class_members'), ['A', 'B']),
    (('records', 'NASDAQ:ADBE', 'basis_evidence', 'cover_accn'), None), (('records', 'NYSE:MMM', 'shares'), 5),
    (('records', 'NASDAQ:ADBE', 'reason_codes'), ['RANK']), (('records', 'NYSE:MMM'), KeyError),
    (('records', 'NASDAQ:ADBE', 'acquired_at'), '2026-10-11T00:00:00Z'), (('state',), 'STALE'), (('code_count',), 503),
    (('config_status',), 'CALIBRATED'), (('stale_after_seconds',), 1.5), (('records', 'NASDAQ:ADBE', 'source_sha256', 'cover'), 'x'),
])
def test_validator_is_strict(path, value):
    with pytest.raises(ValueError, match='SEC_UNIVERSE_SHARES_INVALID'):
        m.require_universe_shares(mutate(path, value))


def test_json_parser_rejects_nonfinite_and_duplicate_keys():
    for body in (b'{"a":NaN}', b'{"a":1,"a":2}', b'\xff', b'x' * (m.MAX_BYTES + 1)):
        with pytest.raises(ValueError, match='SEC_UNIVERSE_SHARES_INVALID'):
            m.parse_json(body)
    assert m.require_universe_shares(m.parse_json(m.encode(merged())))['state'] == 'NOT_AVAILABLE'


def test_pages_guard_allows_valid_file_and_rejects_tampered_values(tmp_path):
    build = load_tool('build_pages_cockpit')
    guard = load_tool('pages_artifact_guard')
    site = tmp_path / 'site'
    build.build_public_cockpit(site)
    (site / m.FILENAME).write_bytes(m.encode(merged({'NASDAQ:ADBE': record()})))
    assert guard.scan_artifact(site)['pages_artifact_guard'] == 'PASS'
    tampered = json.loads((site / m.FILENAME).read_text())
    tampered['records']['NASDAQ:ADBE']['shares'] = 0
    (site / m.FILENAME).write_text(json.dumps(tampered))
    receipt = guard.scan_artifact(site)
    assert receipt['pages_artifact_guard'] == 'FAIL' and receipt['violations'].get('universe_shares_boundary') == 1


# ---- collection tool (mocked transport only) ----
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


def transport_for(calls, *, fail=False):
    def transport(url, *, headers, timeout, max_body_bytes):
        calls.append((url, dict(headers)))
        if url.endswith('company_tickers_exchange.json'):
            return SecResponse(200, ticker_body(), final_url=url)
        if fail:
            return SecResponse(403, b'', final_url=url)
        if '/Archives/' in url:
            cik = url.split('/data/')[1].split('/')[0].zfill(10)
            return SecResponse(200, cover(cik, ISSUERS[cik][0]), final_url=url)
        cik = url.split('CIK')[-1].split('.')[0]
        body = facts(cik) if 'companyfacts' in url else submissions(cik, *ISSUERS[cik])
        return SecResponse(200, body, final_url=url)
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


def missing(request, **_):
    raise urllib.error.HTTPError(request.full_url, 404, '', {}, None)


def test_tool_collects_one_shard_merges_and_reports_raw_not_configured(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    when = day_for('0000000002')
    calls = []
    code = tool.run(tmp_path, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when,
                    client_kwargs=client_kwargs(transport_for(calls), when), open_previous=missing)
    out = capsys.readouterr().out
    assert code == 0 and 'RAW_UPLOAD_NOT_CONFIGURED' in out and UA not in out and 'tester@' not in out
    payload = m.require_universe_shares(json.loads((tmp_path / m.FILENAME).read_text()))
    row = payload['records']['NYSE:BRK.B']
    assert row['listing_id'] == 'XNYS:BRK-B:0000000002' and row['share_class_basis'] == 'SINGLE_CLASS_CONFIRMED' and row['state'] == 'LIVE'
    assert payload['last_shard_index'] == when.date().toordinal() % 7
    assert all(h['User-Agent'] == UA for _, h in calls)
    assert any('/Archives/edgar/data/2/000000000226000001/demo-20260930_htm.xml' in u for u, _ in calls)
    assert payload['records']['BATS:CBOE']['reason_codes'] == ['CIK_UNRESOLVED']
    text = (tmp_path / m.FILENAME).read_text().lower()
    assert 'price' not in text and 'marketcap' not in text and 'rank' not in text
    assert list(tmp_path.iterdir()) == [tmp_path / m.FILENAME]


def test_tool_keeps_previous_values_from_other_shards_and_on_total_failure(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    previous = merged({'NASDAQ:ADBE': record()}, as_of=NOW)
    body = m.encode(previous)
    opener = lambda request, **_: Response(request.full_url, body)
    when = day_for('0000000002') + timedelta(days=7)
    code = tool.run(tmp_path, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when,
                    client_kwargs=client_kwargs(transport_for([], fail=True), when), open_previous=opener)
    out = capsys.readouterr().out
    assert code == 0 and 'SHARD_ALL_FAILED' in out and 'PREVIOUS_RESTORED' in out
    payload = json.loads((tmp_path / m.FILENAME).read_text())
    kept = payload['records']['NASDAQ:ADBE']
    assert kept['shares'] == 100 and kept['acquired_at'] == '2026-10-10T22:30:00Z'
    assert kept['state'] == ('STALE' if when - NOW > timedelta(days=14) else 'LIVE')


def test_tool_previous_network_failure_writes_nothing(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    def broken(request, **_):
        raise urllib.error.URLError('synthetic')
    assert tool.run(tmp_path, live=True, environ={'SEC_USER_AGENT': UA}, open_previous=broken) == 1
    assert 'PREVIOUS_FETCH_FAILED' in capsys.readouterr().out and not list(tmp_path.iterdir())


def test_tool_preserve_only_and_invalid_previous_is_discarded(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    body = m.encode(merged({'NASDAQ:ADBE': record()}))
    assert tool.run(tmp_path, live=False, preserve_only=True, now=lambda: NOW + timedelta(hours=1),
                    open_previous=lambda r, **_: Response(r.full_url, body)) == 0
    assert json.loads((tmp_path / m.FILENAME).read_text())['records']['NASDAQ:ADBE']['shares'] == 100
    other = tmp_path / 'other'; other.mkdir()
    assert tool.run(other, live=False, preserve_only=True, open_previous=lambda r, **_: Response(r.full_url, b'{"price":1}')) == 0
    out = capsys.readouterr().out
    assert 'PREVIOUS_DISCARDED' in out and not list(other.iterdir())


def test_tool_raw_upload_uses_dated_private_release_and_never_prints_token(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    when = day_for('0000000001')
    requests = []
    def upload(request, **_):
        requests.append(request)
        if request.full_url.endswith('/releases'):
            return Response(request.full_url, b'{"id": 7}', 201)
        return Response(request.full_url, b'{"id": 8}', 201)
    code = tool.run(tmp_path, live=True, environ={'SEC_USER_AGENT': UA, 'RAW_REPO_TOKEN': TOKEN}, now=lambda: when,
                    client_kwargs=client_kwargs(transport_for([]), when), open_previous=missing, open_upload=upload)
    out = capsys.readouterr().out
    assert code == 0 and TOKEN not in out and 'RAW_UPLOADED' in out
    tag = f'sec-universe-raw-{when.date().isoformat()}-shard{when.date().toordinal() % 7}'
    create, archive, digest = requests
    assert create.full_url == 'https://api.github.com/repos/kco994553-star/investment-system1-raw/releases'
    assert json.loads(create.data)['tag_name'] == tag and create.get_header('Authorization') == 'Bearer ' + TOKEN
    assert archive.full_url.endswith('/releases/7/assets?name=' + tag + '.tar.gz')
    assert digest.data.decode() == sha256(archive.data).hexdigest() + '  ' + tag + '.tar.gz\n'
    with tarfile.open(fileobj=io.BytesIO(archive.data)) as tar:
        names = tar.getnames()
    assert tag + '/manifest.json' in names and tag + '/0000000001/companyfacts.json' in names
    assert any(n.endswith('.xml') for n in names)
    assert TOKEN not in (tmp_path / m.FILENAME).read_text()


def test_tool_raw_upload_failure_is_fixed_code_and_nonfatal(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    when = day_for('0000000001')
    def denied(request, **_):
        raise urllib.error.HTTPError(request.full_url, 403, 'secret detail ' + TOKEN, {}, None)
    assert tool.run(tmp_path, live=True, environ={'SEC_USER_AGENT': UA, 'RAW_REPO_TOKEN': TOKEN}, now=lambda: when,
                    client_kwargs=client_kwargs(transport_for([]), when), open_previous=missing, open_upload=denied) == 0
    out = capsys.readouterr().out
    assert 'RAW_UPLOAD_FAILED code=HTTP_403' in out and TOKEN not in out and 'secret detail' not in out


def test_tool_missing_user_agent_has_fixed_code(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    assert tool.run(tmp_path, live=True, environ={}, open_previous=missing) == 1
    assert 'COLLECTION_NOT_RUN code=SEC_USER_AGENT_INVALID' in capsys.readouterr().out


def test_shard_rotation_is_day_ordinal_mod_fixed_count():
    cfg = m.load_config()
    assert cfg['shard_count'] == 7 and cfg['stale_after_days'] == 14 and cfg['config_status'] == 'DEFAULT_V0_UNCALIBRATED'
    days = [date(2026, 10, 10) + timedelta(days=i) for i in range(7)]
    assert sorted(m.shard_index_for(d, 7) for d in days) == list(range(7))


# ---- Python reference golden vectors (JS parity fixture) ----
def reference():
    return load_tool('m3_public_shares_reference')


def test_public_shares_fixture_is_regenerated_from_python_reference():
    fixture = json.loads((ROOT / 'tests/fixtures/m3_public_shares_reference_v1.json').read_text())
    assert fixture == json.loads(json.dumps(reference().build()))
    assert len(fixture['cases']) == 14 and all(c['synthetic'] is True for c in fixture['cases'])


def test_fixture_records_are_valid_public_rows():
    fixture = json.loads((ROOT / 'tests/fixtures/m3_public_shares_reference_v1.json').read_text())
    cut = datetime(2030, 2, 10, 13, tzinfo=timezone.utc)
    for case in fixture['cases']:
        if case['id'] == 'venue_prefix_mismatch':  # deliberately inconsistent row: device core must refuse it
            continue
        for code, row in case['input']['records'].items():
            assert m._record(code, row, cut, timedelta(days=14)) in m.STATES


def test_reference_refuses_live_cases():
    with pytest.raises(ValueError, match='SYNTHETIC_ONLY'):
        reference().replay({'synthetic': False, 'input': {}})


@pytest.mark.skipif(shutil.which('node') is None or not (ROOT / 'src/investment_system/product/web_assets/sec-universe-shares.js').exists(),
                    reason='Node runtime and JS reader required')
def test_browser_reader_validator_agrees_with_python_validator():
    reader = ROOT / 'src/investment_system/product/web_assets/sec-universe-shares.js'
    script = ("const a=require(process.argv[1]),p=JSON.parse(require('fs').readFileSync(0,'utf8'));"
              "try{a.validate(p);console.log('OK')}catch(e){console.log('REJECT')}")
    good = merged({'NASDAQ:ADBE': record(), 'NYSE:MMM': record('NYSE:MMM', '0000000003', 'MMM', multi=True)})
    assert subprocess.run(['node', '-e', script, str(reader)], input=json.dumps(good), text=True, capture_output=True).stdout.strip() == 'OK'
    for path, value in [(('records', 'NASDAQ:ADBE', 'shares'), 0), (('price',), 1), (('records', 'NASDAQ:ADBE', 'state'), 'STALE'),
                        (('records', 'NYSE:MMM'), KeyError), (('records', 'NASDAQ:ADBE', 'listing_id'), 'XNYS:ADBE:0000000001')]:
        bad = mutate(path, value)
        result = subprocess.run(['node', '-e', script, str(reader)], input=json.dumps(bad), text=True, capture_output=True)
        assert result.stdout.strip() == 'REJECT'


# ---- unlisted cover class (decision 2026-10-11: Alphabet Class B valued at the Class A price) ----
ALPHA = '0001652044'


def alpha_cover(class_b=(300,), goog_title='Class C Common Stock'):
    """Synthetic Alphabet-shaped cover: Class A (GOOGL) and Class C (GOOG) listed, Class B on the cover without a symbol."""
    ns = ('<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:xbrli="http://www.xbrl.org/2003/instance" '
          'xmlns:g="http://fasb.org/us-gaap/2026" xmlns:dei="http://xbrl.sec.gov/dei/2026" xmlns:d="http://xbrl.org/2006/xbrldi">')
    ctx = lambda id_, member: (f'<context id="{id_}"><entity><identifier scheme="http://www.sec.gov/CIK">{ALPHA}</identifier>'
                               f'<segment><d:explicitMember dimension="g:StatementClassOfStockAxis">g:{member}</d:explicitMember></segment>'
                               '</entity><period><instant>2026-09-25</instant></period></context>')
    fact = lambda id_, value: f'<dei:EntityCommonStockSharesOutstanding contextRef="{id_}" unitRef="u">{value}</dei:EntityCommonStockSharesOutstanding>'
    body = ns + '<unit id="u"><measure>xbrli:shares</measure></unit>'
    body += ctx('a', 'CommonClassAMember') + ctx('c', 'CommonClassCMember')
    body += '<dei:TradingSymbol contextRef="a">GOOGL</dei:TradingSymbol><dei:Security12bTitle contextRef="a">Class A Common Stock</dei:Security12bTitle>'
    body += f'<dei:TradingSymbol contextRef="c">GOOG</dei:TradingSymbol><dei:Security12bTitle contextRef="c">{goog_title}</dei:Security12bTitle>'
    body += fact('a', 5800) + fact('c', 5400)
    for i, value in enumerate(class_b):
        body += ctx(f'b{i}', 'CommonClassBMember') + fact(f'b{i}', value)
    return (body + '</xbrl>').encode()


def alpha_records(**cover_kwargs):
    subs = json.dumps({'cik': int(ALPHA), 'tickers': ['GOOGL', 'GOOG'], 'exchanges': ['Nasdaq', 'Nasdaq'], 'filings': {'recent': {
        'accessionNumber': [accn(ALPHA)], 'form': ['10-Q'], 'filingDate': ['2026-10-01'],
        'acceptanceDateTime': ['2026-10-01T12:00:00Z'], 'reportDate': ['2026-09-30'], 'primaryDocument': ['goog-20260930.htm']}}}).encode()
    return m.build_issuer_records(codes=('NASDAQ:GOOGL', 'NASDAQ:GOOG'), cik=ALPHA, companyfacts_body=facts(ALPHA, 5800), submissions_body=subs,
                                  acquired_at=NOW, as_of=NOW, cover_xml=alpha_cover(**cover_kwargs), cover_accession=accn(ALPHA), cover_acquired_at=NOW)


def test_unlisted_class_b_count_is_published_from_the_same_cover_as_googl():
    records, unlisted = alpha_records()
    googl, goog = records['NASDAQ:GOOGL'], records['NASDAQ:GOOG']
    assert googl['share_class_basis'] == goog['share_class_basis'] == 'SHARE_CLASS_BASIS'
    assert googl['basis_evidence']['class_members'] == ['CommonClassAMember', 'CommonClassBMember', 'CommonClassCMember']
    assert unlisted == {'alphabet': {'cik': ALPHA, 'valued_at': 'NASDAQ:GOOGL', 'accn': googl['accn'], 'measurement_date': '2026-09-25',
                                     'cover_sha256': googl['source_sha256']['cover'], 'classes': [{'class_member': 'CommonClassBMember', 'shares': 300}],
                                     'state': 'LIVE', 'reason_codes': []}}
    payload = merged(records, unlisted_updates=unlisted)
    assert payload['unlisted_classes'] == unlisted
    body = m.encode(payload)
    assert m.require_universe_shares(m.parse_json(body))['unlisted_classes']['alphabet']['classes'][0]['shares'] == 300
    assert not {'price', 'marketcap', 'market_cap', 'rank'} & set(json.dumps(payload['unlisted_classes']).lower().replace('"', ' ').split())


@pytest.mark.parametrize('class_b,reason', [((), 'UNLISTED_CLASS_SHARES_NOT_AVAILABLE'), ((300, 310), 'UNLISTED_CLASS_AMBIGUOUS')])
def test_unlisted_class_b_missing_or_ambiguous_is_not_available_never_zero(class_b, reason):
    records, unlisted = alpha_records(class_b=class_b)
    entry = unlisted['alphabet']
    assert entry['classes'] == [] and entry['state'] == 'NOT_AVAILABLE' and entry['reason_codes'] == [reason]
    assert entry['accn'] is None and entry['measurement_date'] is None and entry['cover_sha256'] is None
    assert merged(records, unlisted_updates=unlisted)['unlisted_classes']['alphabet'] == entry


def test_goog_exact_capital_stock_title_is_allowed_only_for_alphabet():
    """GSQ-021: GOOG's real cover title (10-Q 0001652044-24-000053/-000118) is allowed as that exact string only."""
    records, unlisted = alpha_records(goog_title='Class C Capital Stock, $0.001 par value')
    assert records['NASDAQ:GOOG']['share_class_basis'] == 'SHARE_CLASS_BASIS'
    assert records['NASDAQ:GOOG']['reason_codes'] == records['NASDAQ:GOOGL']['reason_codes'] == ['SHARE_CLASS_BASIS']
    assert records['NASDAQ:GOOGL']['share_class_basis'] == 'SHARE_CLASS_BASIS' and unlisted['alphabet']['state'] == 'LIVE'
    assert m3.EXACT_TITLE_EXCEPTIONS == {('0001652044', 'GOOG'): 'Class C Capital Stock, $0.001 par value'}


@pytest.mark.parametrize('title', ['Class C Capital Stock', 'class c capital stock, $0.001 par value', 'Class C Capital Stock, $0.001 par value ',
                                   'Class C Capital Stock, $0.01 par value'])
def test_capital_stock_general_rule_not_loosened(title):
    records, _ = alpha_records(goog_title=title)
    if title.strip() == 'Class C Capital Stock, $0.001 par value':
        assert records['NASDAQ:GOOG']['share_class_basis'] == 'SHARE_CLASS_BASIS'   # cover text is stripped before matching
    else:
        assert records['NASDAQ:GOOG']['share_class_basis'] == 'BASIS_UNCONFIRMED' and records['NASDAQ:GOOG']['reason_codes'] == ['BASIS_UNCONFIRMED']


def test_capital_stock_title_is_not_allowed_for_another_issuer():
    xml = b"""<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:dei="http://xbrl.sec.gov/dei/2024">
<xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000000123</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2026-09-25</xbrli:instant></xbrli:period></xbrli:context>
<xbrli:unit id="s"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>
<dei:Security12bTitle contextRef="c">Class C Capital Stock, $0.001 par value</dei:Security12bTitle><dei:TradingSymbol contextRef="c">GOOG</dei:TradingSymbol>
<dei:EntityCommonStockSharesOutstanding contextRef="c" unitRef="s">100</dei:EntityCommonStockSharesOutstanding></xbrli:xbrl>"""
    with pytest.raises(ValueError, match='BASIS_UNCONFIRMED'):
        m3._cover(xml, '0000000123', 'GOOG', datetime(2026, 10, 1, tzinfo=timezone.utc))


def test_unlisted_entry_follows_its_listing_row_through_merge_and_staleness():
    records, unlisted = alpha_records()
    first = merged(records, unlisted_updates=unlisted)
    kept = merged({'NASDAQ:GOOGL': m.empty_record(cik=ALPHA, reasons=('SHARES_NOT_AVAILABLE',))}, previous=first, as_of=NOW + timedelta(days=1))
    assert kept['unlisted_classes'] == first['unlisted_classes']
    stale = merged(previous=first, as_of=NOW + timedelta(days=15))
    entry = stale['unlisted_classes']['alphabet']
    assert entry['state'] == 'STALE' and entry['reason_codes'] == ['STALE_INPUT'] and entry['classes'][0]['shares'] == 300
    replaced = merged({'NASDAQ:GOOGL': records['NASDAQ:GOOGL']}, previous=first)  # row replaced without a new entry
    assert replaced['unlisted_classes']['alphabet']['state'] == 'NOT_AVAILABLE'
    assert replaced['unlisted_classes']['alphabet']['reason_codes'] == ['UNLISTED_CLASS_SHARES_NOT_AVAILABLE']
    assert merged()['unlisted_classes']['alphabet']['reason_codes'] == ['NOT_COLLECTED']


def test_legacy_previous_copy_is_upgraded_not_discarded(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    legacy = merged({'NASDAQ:ADBE': record()})
    del legacy['unlisted_classes']
    with pytest.raises(ValueError, match='SEC_UNIVERSE_SHARES_INVALID'):
        m.require_universe_shares(legacy)
    body = json.dumps(legacy).encode()
    assert tool.run(tmp_path, live=False, preserve_only=True, now=lambda: NOW + timedelta(hours=1),
                    open_previous=lambda r, **_: Response(r.full_url, body)) == 0
    assert 'PREVIOUS_RESTORED' in capsys.readouterr().out
    out = json.loads((tmp_path / m.FILENAME).read_text())
    assert out['records']['NASDAQ:ADBE']['shares'] == 100 and out['unlisted_classes']['alphabet']['reason_codes'] == ['NOT_COLLECTED']


def alpha_payload():
    records, unlisted = alpha_records()
    return merged(records, unlisted_updates=unlisted)


@pytest.mark.parametrize('mutate', [
    lambda p: p.pop('unlisted_classes'),
    lambda p: p['unlisted_classes'].update(fox=p['unlisted_classes']['alphabet']),
    lambda p: p['unlisted_classes']['alphabet']['classes'][0].update(shares=0),
    lambda p: p['unlisted_classes']['alphabet']['classes'][0].update(shares=-1),
    lambda p: p['unlisted_classes']['alphabet']['classes'][0].update(shares=True),
    lambda p: p['unlisted_classes']['alphabet']['classes'][0].update(shares='300'),
    lambda p: p['unlisted_classes']['alphabet']['classes'][0].update(price=1),
    lambda p: p['unlisted_classes']['alphabet'].update(market_cap=1),
    lambda p: p['unlisted_classes']['alphabet']['classes'][0].update(class_member='CommonClassAMember'),
    lambda p: p['unlisted_classes']['alphabet']['classes'][0].update(class_member='CommonClassDMember'),
    lambda p: p['unlisted_classes']['alphabet'].update(accn='0001652044-26-000009'),
    lambda p: p['unlisted_classes']['alphabet'].update(measurement_date='2026-09-24'),
    lambda p: p['unlisted_classes']['alphabet'].update(cover_sha256='0' * 64),
    lambda p: p['unlisted_classes']['alphabet'].update(state='STALE'),
    lambda p: p['unlisted_classes']['alphabet'].update(valued_at='NASDAQ:GOOG'),
    lambda p: p['unlisted_classes']['alphabet'].update(cik='0000000001'),
    lambda p: p['unlisted_classes']['alphabet'].update(reason_codes=['RANK']),
    lambda p: p['unlisted_classes']['alphabet']['classes'].append({'class_member': 'CommonClassBMember', 'shares': 300}),
    lambda p: p['unlisted_classes']['alphabet'].update(classes=[], state='NOT_AVAILABLE', reason_codes=[]),
    lambda p: p['unlisted_classes']['alphabet'].update(classes=[], state='NOT_AVAILABLE', reason_codes=['UNLISTED_CLASS_SHARES_NOT_AVAILABLE']),
])
def test_unlisted_validator_is_strict_in_python_and_js(mutate):
    payload = alpha_payload()
    assert m.require_universe_shares(payload) is payload
    mutate(payload)
    with pytest.raises(ValueError, match='SEC_UNIVERSE_SHARES_INVALID'):
        m.require_universe_shares(payload)
    if shutil.which('node') is not None:
        reader = ROOT / 'src/investment_system/product/web_assets/sec-universe-shares.js'
        script = ("const a=require(process.argv[1]),p=JSON.parse(require('fs').readFileSync(0,'utf8'));"
                  "try{a.validate(p);console.log('OK')}catch(e){console.log('REJECT')}")
        out = subprocess.run(['node', '-e', script, str(reader)], input=json.dumps(payload), text=True, capture_output=True).stdout.strip()
        assert out == 'REJECT'
