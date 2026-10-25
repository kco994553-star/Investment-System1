"""Central V publication guards (PR-B, GSQ-024; design CENTRAL_V_PUBLICATION_DESIGN_20261018.md §12, AUDIT.md §10).

- tools/pages_artifact_guard.py: qgv-official.json / qgv-official-status.json are allowed with their strict validators, and the
  ONLY sensitive-key exception is rows.<code>.rank of qgv-official.json (`rank` anywhere else and price / market cap / cash keys
  anywhere still fail);
- src/investment_system/public_price_boundary.py: the IEX HIST sources (exact URL shapes) are allowed only inside the route
  tools/qgv_official_publish.py, apart from AUDITED_ROUTES and the SEC allowlists; the adapters ask the boundary before any request;
- tools/pages_freshness_guard.py: the qgv-official rule (older basis refused, same publication_id byte-equal, status never
  compared, a broken or missing live publication withholds the publication only, D-CV16 (a));
- static: who may reference the IEX sources, how workflows may call the publisher and hold its Secrets, AUDIT.md append-only.

Synthetic publications (tests/test_qgv_official.py builders: made-up prices), an in-memory live Pages copy, no network.
"""
import copy
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile
import types
from collections import Counter

import pytest

from investment_system import public_price_boundary as boundary
from investment_system.providers import iex_hist, iex_monthend
from investment_system.qgv import qgv_official as qo
from investment_system.universe import sec_qgv2
from tests.test_public_price_boundary import prohibit_network  # noqa: F401  (autouse: every test here is offline)
from tests.test_qgv_official import KEY, NOW, base_payload, build, synthetic_day, tool as publisher
from tests.test_pages_freshness_guard import Site, guard, load_tool, served, write

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
CODE = 'NYSE:ABT'


def _load(name):
    spec = importlib.util.spec_from_file_location('qgv_guard_' + name, ROOT / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ARTIFACT_GUARD = _load('pages_artifact_guard')


@pytest.fixture(scope='module')
def official():
    o = build(base_payload())[0]
    o['times']['verified_at'] = qo.iso(NOW)
    qo.require_qgv_official(o)
    return o


@pytest.fixture(scope='module')
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp('cockpit') / 'site'
    _load('build_pages_cockpit').build_public_cockpit(out)
    return out


def _ranked_key(o):
    return min((r['rank'], k) for k, r in o['rows'].items() if r['rank'] is not None)[1]


def _check(name, value):
    violations = Counter()
    ARTIFACT_GUARD._check_payload(name, value if isinstance(value, bytes) else json.dumps(value).encode(), violations)
    return violations


def _tar(folder, archive):
    with tarfile.open(archive, 'w', format=tarfile.USTAR_FORMAT) as handle:
        for entry in sorted(folder.iterdir()):
            info = handle.gettarinfo(str(entry), arcname='./' + entry.name)
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            with entry.open('rb') as content:
                handle.addfile(info, content)
    return archive


# ---- pages_artifact_guard: allowed names and file validators -----------------------------------------------------------
def test_the_two_files_are_allowed_and_optional():
    assert {qo.FILENAME, qo.STATUS_FILENAME} <= ARTIFACT_GUARD.ALLOWED_NAMES
    assert not {qo.FILENAME, qo.STATUS_FILENAME} & set(ARTIFACT_GUARD.APPROVED_SHA256)   # absent before the first publication
    assert ARTIFACT_GUARD._OFFICIAL_CODE.pattern == qo._CODE.pattern                    # the publication's own row-key pattern
    assert ARTIFACT_GUARD.PUBLIC_SCORE_PATHS.keys() == {qo.FILENAME}                     # one file, one path
    assert [p[0] for p in ARTIFACT_GUARD.PUBLIC_SCORE_PATHS[qo.FILENAME]] == ['rows']
    assert [p[-1] for p in ARTIFACT_GUARD.PUBLIC_SCORE_PATHS[qo.FILENAME]] == ['rank']
    assert 'rank' in ARTIFACT_GUARD.SENSITIVE_KEYS                                      # the key list itself is unchanged


def test_the_publishers_real_output_passes_the_guard_in_directory_and_tar_mode(official, site, tmp_path):
    """The tool's own bytes (first publication + status), copied into the full price-free build: PASS both ways."""
    out = tmp_path / 'artifact'
    out.mkdir()
    payload = base_payload()
    (out / sec_qgv2.FILENAME).write_bytes(sec_qgv2.encode(payload))
    parser = tmp_path / 'parser'
    parser.write_text('')
    day = synthetic_day(payload)
    s = publisher.run(out=out, parser=str(parser), monthend_stamp='20261023', monthend_shards=6, previous=None, raw_token='t',
                      hmac_key=KEY, now=NOW, workdir=tmp_path / 'w', fetch_day=lambda *a, **k: day,
                      read_store=lambda stamp, n: {}, clock=lambda: NOW)
    assert (s['attempt'], s['published']) == ('OK', 'NEW')
    full = tmp_path / 'site'
    shutil.copytree(site, full)
    for name in (qo.FILENAME, qo.STATUS_FILENAME):
        shutil.copyfile(out / name, full / name)
    receipt = ARTIFACT_GUARD.scan_artifact(full)
    assert receipt['pages_artifact_guard'] == 'PASS' and receipt['violations'] == {}
    assert receipt['files_scanned'] == sum(1 for _ in site.iterdir()) + 2
    assert ARTIFACT_GUARD.validate_pages_tar(_tar(full, tmp_path / 'artifact.tar')) == receipt
    # The same bytes under another public name keep every check: the 18 ranks are sensitive there.
    renamed = _check(sec_qgv2.FILENAME, (out / qo.FILENAME).read_bytes())
    assert renamed['sensitive_json_fields'] == official['coverage']['ranked'] == 18 and renamed['qgv2_boundary'] == 1


def test_a_build_without_the_publication_still_passes(site):
    receipt = ARTIFACT_GUARD.scan_artifact(site)
    assert receipt['pages_artifact_guard'] == 'PASS' and receipt['violations'] == {}


def test_file_validators_are_wired(official):
    assert _check(qo.FILENAME, official) == Counter()
    bad = copy.deepcopy(official)
    bad['rows'][_ranked_key(bad)]['total'] -= 1e-9                   # no sensitive key: only the strict validator sees it
    assert dict(_check(qo.FILENAME, bad)) == {'qgv_official_boundary': 1}
    status = qo.status_payload(attempt_at=NOW, state='OK', reason=None, official=official, inputs_sha256='a' * 64,
                               inputs_as_of=official['inputs'][0]['as_of'])
    assert _check(qo.STATUS_FILENAME, status) == Counter()
    unknown = qo.status_payload(attempt_at=NOW, state='NOT_RUN', reason='LIVE_UNREACHABLE', official=None, inputs_sha256=None,
                                inputs_as_of=None, live_unknown=True)
    assert unknown['attempt_state'] == 'NOT_RUN' and _check(qo.STATUS_FILENAME, unknown) == Counter()
    assert dict(_check(qo.STATUS_FILENAME, dict(unknown, attempt_state='NO_OFFICIAL_YET'))) == {'qgv_official_status_boundary': 1}
    for state, reason in (('NOT_RUN', 'MONTHEND_TOKEN_MISSING'), ('NOT_RUN', 'HMAC_KEY_MISSING'), ('SUPPLY_FAILED', 'IEX_MD5_MISMATCH')):
        st = qo.status_payload(attempt_at=NOW, state=state, reason=reason, official=None, inputs_sha256=None, inputs_as_of=None)
        assert _check(qo.STATUS_FILENAME, st) == Counter()           # fixed codes never look like secrets
    assert dict(_check(qo.STATUS_FILENAME, dict(status, attempt_state='DONE'))) == {'qgv_official_status_boundary': 1}
    assert dict(_check(qo.FILENAME, status)) == {'qgv_official_boundary': 1}          # each file only passes its own validator
    assert _check(qo.STATUS_FILENAME, official)['qgv_official_status_boundary'] == 1


# ---- the one path-scoped sensitive-key exception -------------------------------------------------------------------------
def _row(o):
    return o['rows'][_ranked_key(o)]


SENSITIVE_ELSEWHERE = [
    ('top_level_rank', lambda o: o.update(rank=1)),
    ('coverage_rank', lambda o: o['coverage'].update(rank=1)),
    ('factor_rank', lambda o: _row(o)['factors']['q_profitability'].update(rank=1)),
    ('axis_rank', lambda o: _row(o)['axes']['V'].update(rank=1)),
    ('deeper_rank', lambda o: _row(o).update(extra={'rank': 1})),
    ('other_spelling', lambda o: _row(o).update(Rank=1)),
    ('dashed_spelling', lambda o: _row(o).update(**{'r-a-n-k': 1})),
    ('string_value', lambda o: _row(o).update(rank='1')),
    ('bool_value', lambda o: _row(o).update(rank=True)),
    ('zero_value', lambda o: _row(o).update(rank=0)),
    ('float_value', lambda o: _row(o).update(rank=1.0)),
    ('list_value', lambda o: _row(o).update(rank=[1])),
    ('bad_row_key', lambda o: o['rows'].update({'not a code': {'rank': 1}})),
    ('rows_as_list', lambda o: o.update(rows=[{'rank': 1}] + [None] * 0)),
    ('list_in_between', lambda o: o['rows'].update({'NYSE:ZZZ': [{'rank': 1}]})),
]


CANARY = 4321.0987          # synthetic price that must never pass the Pages guard in any field


def _smuggle(o, path, value):
    """Set the field at `path` (keys; the string 'ROW' = the first row key) of a copy to `value`."""
    bad = copy.deepcopy(o)
    node = bad
    keys = [sorted(bad['rows'])[0] if k == 'ROW' else k for k in path]
    for k in keys[:-1]:
        node = node[k]
    node[keys[-1]] = value
    return bad


# Review 2026-10-24: the strict validator is the only content check of qgv-official.json (no pinned hash), so the guard must
# refuse a price smuggled into any scalar field, not only in a key it already knows.
@pytest.mark.parametrize('path, value', [
    (('inputs', 0, 'as_of'), CANARY), (('inputs', 0, 'acquired_newest'), CANARY), (('times', 'inputs_as_of'), CANARY),
    (('price_source', 'supply', 'eligible'), CANARY), (('price_source', 'supply', 'supplied'), 'x'),
    (('price_source', 'month_end', 'months'), CANARY), (('price_source', 'month_end', 'stamp'), [CANARY, CANARY]),
    (('price_source', 'month_end', 'basis'), 'ANYTHING'), (('price_source', 'currency'), 'EUR'), (('price_source', 'feed'), 'X'),
    (('engine', 'status'), CANARY), (('weights', 'weights_version'), CANARY), (('config_versions', 'type_config'), CANARY),
    (('population', 'registry_sha256'), CANARY), (('type_scope',), CANARY), (('rows', 'ROW', 'acquired_at'), str(CANARY)),
    (('rows', 'ROW', 'selected_types'), [str(CANARY)]),
])
def test_a_value_smuggled_into_any_scalar_is_refused_by_the_guard(official, path, value):
    assert dict(_check(qo.FILENAME, _smuggle(official, path, value))) == {'qgv_official_boundary': 1}


def test_supply_counts_that_break_d4_are_refused_by_the_guard(official):
    sup = official['price_source']['supply']
    for change in ({'supplied': 1}, {'eligible': 0, 'supplied': 0}, {'supplied': sup['eligible'] + 1},
                   {'eligible': sup['eligible'] + 1000, 'supplied': sup['eligible'] + 1000}):
        bad = copy.deepcopy(official)
        bad['price_source']['supply'].update(change)
        assert dict(_check(qo.FILENAME, bad)) == {'qgv_official_boundary': 1}, change


@pytest.mark.parametrize('name,mutate', SENSITIVE_ELSEWHERE, ids=[n for n, _ in SENSITIVE_ELSEWHERE])
def test_rank_anywhere_else_in_the_publication_still_fails(official, name, mutate):
    bad = copy.deepcopy(official)
    mutate(bad)
    found = _check(qo.FILENAME, bad)
    assert found['sensitive_json_fields'] >= 1 and found['qgv_official_boundary'] == 1


@pytest.mark.parametrize('key', ['price', 'marketcap', 'market_cap', 'cash', 'cost', 'amount', 'mcap', 'totalscore', 'vscore',
                                 'holdings', 'marketvalue', 'cashbalance'])
@pytest.mark.parametrize('where', ['top', 'row', 'factor', 'price_source', 'coverage'])
def test_price_marketcap_cash_keys_fail_anywhere_in_the_publication(official, key, where):
    bad = copy.deepcopy(official)
    target = {'top': bad, 'row': _row(bad), 'factor': _row(bad)['factors']['v_vs_own_history'], 'price_source': bad['price_source'],
              'coverage': bad['coverage']}[where]
    target[key] = 1
    found = _check(qo.FILENAME, bad)
    assert found['sensitive_json_fields'] == 1 and found['qgv_official_boundary'] == 1


@pytest.mark.parametrize('name', [qo.STATUS_FILENAME, sec_qgv2.FILENAME, 'sec-universe-qg.json', 'news-signals.json'])
def test_the_rank_path_is_not_exempt_in_any_other_file(official, name):
    shaped = {'rows': {CODE: {'rank': 1}}}
    violations = Counter()
    ARTIFACT_GUARD._inspect_json(shaped, violations, name=name)
    assert violations['sensitive_json_fields'] == 1
    violations = Counter()
    ARTIFACT_GUARD._inspect_json(shaped, violations, name=qo.FILENAME)
    assert violations['sensitive_json_fields'] == 0                  # the same shape, only in qgv-official.json
    violations = Counter()
    ARTIFACT_GUARD._inspect_json({'rows': {CODE: {'rank': 1, 'price': 2, 'cash': 3}}}, violations, name=qo.FILENAME)
    assert violations['sensitive_json_fields'] == 2


def test_the_exempt_path_covers_universe_and_target_row_keys_with_a_valid_rank():
    """A TARGET row stands for its Universe issuer's rank (D-CV8), so TARGET:<id> keys are exempt in the same way."""
    for key in ('NYSE:BRK.B', 'NASDAQ:GOOGL', 'TARGET:googl', 'TARGET:tokyo_electron'):
        for value in (None, 1, 523):
            violations = Counter()
            ARTIFACT_GUARD._inspect_json({'rows': {key: {'rank': value}}}, violations, name=qo.FILENAME)
            assert violations['sensitive_json_fields'] == 0, (key, value)
    for key in ('TARGET:Googl', 'nyse:abt', 'NYSE:', 'TARGET:'):
        violations = Counter()
        ARTIFACT_GUARD._inspect_json({'rows': {key: {'rank': 1}}}, violations, name=qo.FILENAME)
        assert violations['sensitive_json_fields'] == 1, key


# ---- public_price_boundary: the IEX sources and the one route ---------------------------------------------------------
LINK = ('https://www.googleapis.com/download/storage/v1/b/iex/o/data%2Ffeeds%2F20261016%2F20261016_IEXTP1_TOPS1.6.pcap.gz'
        '?generation=1760667839123456&alt=media')
ALLOWED = {
    'IEX_HIST_INDEX': ['https://iextrading.com/api/1.0/hist'],
    'IEX_HIST_OBJECT': [LINK, iex_hist.gcs_metadata_url(LINK),
                        'https://storage.googleapis.com/download/storage/v1/b/iex/o/data%2Ffeeds%2F20261016%2Fx.pcap.gz?alt=media'],
    'IEX_HIST_BUCKET': ['https://storage.googleapis.com/iex/data/feeds/20261016/20261016_IEXTP1_TOPS1.6.pcap.gz'],
    'IEX_MONTHEND_STORE': ['https://api.github.com/repos/kco994553-star/investment-system1-raw/releases/tags/iex-v4-monthend-20261023-shard5',
                           'https://api.github.com/repos/kco994553-star/investment-system1-raw/releases/assets/123456789'],
}
# A userinfo URL that only looks like the IEX host; built from parts so the repository email guard (Gate A EMAIL_PATTERN)
# does not read it as an address.
USERINFO_TRICK = 'https://storage.googleapis.com' + '@' + 'evil.example/iex/x'
REJECTED = [
    'http://iextrading.com/api/1.0/hist', 'https://iextrading.com/api/1.0/hist?token=x', 'https://iextrading.com/api/1.0/tops',
    'https://cloud.iexapis.com/stable/stock/aapl/quote', 'https://www.googleapis.com/download/storage/v1/b/other/o/x.gz',
    'https://www.googleapis.com/download/storage/v1/b/iex/o/a/b', 'https://storage.googleapis.com/iex/../other/x.gz',
    'https://storage.googleapis.com/iex/./x', 'https://storage.googleapis.com/iex//x', 'https://storage.googleapis.com/iexx/x',
    USERINFO_TRICK, 'https://evil.example/storage/v1/b/iex/o/x', LINK + '#frag',
    'https://query1.finance.yahoo.com/v8/finance/chart/AAPL', 'https://stooq.com/q/d/l/?s=aapl.us', 'https://api.tiingo.com/tiingo/daily/aapl/prices',
    'https://api.github.com/repos/kco994553-star/investment-system1-raw/releases/tags/forward-ledger-2026-10-23',
    'https://api.github.com/repos/kco994553-star/Investment-System1/releases/assets/1',
    'https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json', 'https://www.sec.gov/files/company_tickers.json',
    None, 42, b'https://iextrading.com/api/1.0/hist',
]


def test_the_price_source_url_shapes_are_exact():
    for kind, urls in ALLOWED.items():
        for url in urls:
            assert boundary.price_source_kind(url) == kind, url
    for url in REJECTED:
        assert boundary.price_source_kind(url) is None, url
    assert boundary.ACTIONS_PRICE_ROUTES == ('implementation/tools/qgv_official_publish.py',)
    assert not set(boundary.ACTIONS_PRICE_ROUTES) & set(boundary.AUDITED_ROUTES)   # separate from the 27+1 audited routes


def test_sec_and_price_allowlists_never_admit_each_other():
    for url in (u for urls in ALLOWED.values() for u in urls):
        with pytest.raises(boundary.PublicPriceBoundaryError):
            boundary.require_financial_url(url)
    for kind, url in [('SEC_COMPANYFACTS', 'https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json'),
                      ('SEC_TICKERS', 'https://www.sec.gov/files/company_tickers.json')]:
        boundary.require_financial_source(kind, url)
        for price_kind in boundary.PRICE_SOURCE_URL_PATTERNS:
            with pytest.raises(boundary.PublicPriceBoundaryError):
                boundary.require_price_source(price_kind, url)
    with pytest.raises(boundary.PublicPriceBoundaryError):
        boundary.require_price_source('IEX_HIST_OBJECT', 'https://iextrading.com/api/1.0/hist')   # the kind must match too


def _as_main(monkeypatch, entry):
    main = types.ModuleType('__main__')
    if entry is not None:
        main.__file__ = str(entry)
    monkeypatch.setitem(sys.modules, '__main__', main)


def test_only_the_publisher_entry_script_is_the_price_route(monkeypatch, tmp_path):
    url = ALLOWED['IEX_HIST_INDEX'][0]
    _as_main(monkeypatch, ROOT / 'tools/qgv_official_publish.py')
    boundary.require_price_route()
    boundary.require_price_source('IEX_HIST_INDEX', url)
    copy_elsewhere = tmp_path / 'implementation/tools/qgv_official_publish.py'
    copy_elsewhere.parent.mkdir(parents=True)
    copy_elsewhere.write_text('')
    for entry in (ROOT / 'tools/fetch_real_data.py', ROOT / 'tools/sec_universe_shares.py', ROOT / 'tools/pages_freshness_guard.py',
                  copy_elsewhere, None):
        _as_main(monkeypatch, entry)
        with pytest.raises(boundary.PublicPriceBoundaryError, match='^PUBLIC_PRICE_BOUNDARY: route withheld under GSQ-010$'):
            boundary.require_price_source('IEX_HIST_INDEX', url)


def test_adapters_ask_the_boundary_before_any_request(monkeypatch):
    calls = []
    monkeypatch.setattr(iex_hist, '_get_json', lambda url, timeout=120: calls.append(url) or {})
    # Under pytest the entry script is not the publisher: refused before the request.
    with pytest.raises(iex_hist.IexHistError, match='^SOURCE_ROUTE_NOT_ALLOWED$'):
        iex_hist.fetch_json(iex_hist.HIST_URL)
    with pytest.raises(iex_hist.IexHistError, match='^SOURCE_ROUTE_NOT_ALLOWED$'):
        iex_hist.curl_command(LINK)
    with pytest.raises(iex_monthend.MonthEndError, match='^ROUTE_NOT_ALLOWED$'):
        iex_monthend.github_call('synthetic-token')
    assert calls == []
    # Inside the route: exact shapes only, the token only on the store URLs.
    _as_main(monkeypatch, ROOT / 'tools/qgv_official_publish.py')
    assert iex_hist.fetch_json(iex_hist.HIST_URL) == {} and iex_hist.fetch_json(iex_hist.gcs_metadata_url(LINK)) == {}
    assert iex_hist.curl_command(LINK)[-1] == LINK
    for url in ('https://iextrading.com/api/1.0/deep', 'https://www.googleapis.com/download/storage/v1/b/other/o/x', 'https://example.com/x'):
        with pytest.raises(iex_hist.IexHistError, match='^SOURCE_URL_INVALID$'):
            iex_hist.fetch_json(url)
        with pytest.raises(iex_hist.IexHistError, match='^SOURCE_URL_INVALID$'):
            iex_hist.curl_command(url)
    with pytest.raises(iex_hist.IexHistError, match='^SOURCE_URL_INVALID$'):
        iex_hist.curl_command(iex_hist.HIST_URL)                       # the index is never "downloaded" as a file
    assert calls == [iex_hist.HIST_URL, iex_hist.gcs_metadata_url(LINK)]
    call = iex_monthend.github_call('synthetic-token')
    for url in ('https://api.github.com/repos/kco994553-star/Investment-System1/releases/tags/iex-v4-monthend-20261023-shard0',
                'https://objects.githubusercontent.com/x', 'https://api.github.com/user'):
        with pytest.raises(iex_monthend.MonthEndError, match='^TOKEN_HOST_INVALID$'):
            call('GET', url)
    # Index links outside the exact shapes are never selected.
    assert not iex_hist._link_ok('https://www.googleapis.com/x') and iex_hist._link_ok(LINK)


def test_the_real_tool_path_outside_the_route_is_supply_failed_without_network(tmp_path):
    """tools/qgv_official_publish.run with the production IEX reader (no injection) from a process that is not the route:
    a fixed SUPPLY_FAILED code, exit path unchanged, no socket (prohibit_network) and no publication."""
    out = tmp_path / 'artifact'
    out.mkdir()
    (out / sec_qgv2.FILENAME).write_bytes(sec_qgv2.encode(base_payload()))
    parser = tmp_path / 'parser'
    parser.write_text('')
    s = publisher.run(out=out, parser=str(parser), monthend_stamp='20261023', monthend_shards=6, previous=None, raw_token='t',
                      hmac_key=KEY, now=NOW, workdir=tmp_path / 'w', clock=lambda: NOW)
    assert (s['attempt'], s['reason'], s['published']) == ('NO_OFFICIAL_YET', 'IEX_SOURCE_ROUTE_NOT_ALLOWED', 'NONE')
    assert not (out / qo.FILENAME).exists()


def test_a_real_publisher_process_is_the_route(tmp_path):
    """`python implementation/tools/qgv_official_publish.py` in a fresh interpreter passes the route check: the first request is
    attempted (through a proxy on a closed local port, so it fails at once and nothing leaves the machine) and the attempt ends
    SUPPLY_FAILED IEX_SOURCE_UNAVAILABLE, not IEX_SOURCE_ROUTE_NOT_ALLOWED. Exit 0, one fixed line."""
    import os
    import subprocess
    out = tmp_path / 'artifact'
    out.mkdir()
    (out / sec_qgv2.FILENAME).write_bytes(sec_qgv2.encode(base_payload()))
    parser = tmp_path / 'parser'
    parser.write_text('')
    env = {k: v for k, v in os.environ.items() if k.lower() not in ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
    env.update(HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9', NO_PROXY='', no_proxy='',
               QGV_OFFICIAL_HMAC_KEY='synthetic-test-key-0123456789', RAW_REPO_READ_TOKEN='synthetic-token')
    run = subprocess.run([sys.executable, str(ROOT / 'tools/qgv_official_publish.py'), '--out', str(out), '--parser', str(parser),
                          '--monthend-stamp', '20261023', '--previous', '', '--now', '2026-10-13T22:40:00Z',
                          '--workdir', str(tmp_path / 'w')], cwd=REPO, env=env, capture_output=True, text=True, timeout=300)
    assert run.returncode == 0 and run.stderr == ''
    assert run.stdout == ('QGV_OFFICIAL attempt=NO_OFFICIAL_YET reason=IEX_SOURCE_UNAVAILABLE published=NONE basis=- rows=0 '
                          'ranked=0 supplied=-\n')
    status = json.loads((out / qo.STATUS_FILENAME).read_bytes())
    qo.require_status(status)
    assert not (out / qo.FILENAME).exists()


# ---- static: who may reach the price source -----------------------------------------------------------------------------
TEXT = ('.py', '.js', '.mjs', '.cjs', '.sh', '.yml', '.yaml', '.c', '.h', '.html', '.json', '.toml', '.cfg')
IEX_HOSTS = re.compile(r'iextrading\.com|iexapis\.com|storage\.googleapis\.com|/b/iex/o/')
ADAPTERS = re.compile(r'\biex_(?:hist|monthend)\b')
HOST_FILES = {'implementation/src/investment_system/providers/iex_hist.py',
              'implementation/src/investment_system/public_price_boundary.py'}
ADAPTER_FILES = {'implementation/src/investment_system/providers/iex_hist.py',
                 'implementation/src/investment_system/providers/iex_monthend.py',
                 'implementation/src/investment_system/qgv/qgv_official.py',
                 'implementation/src/investment_system/public_price_boundary.py',
                 'implementation/tools/qgv_official_publish.py'}


def _code_files():
    roots = [ROOT / 'src', ROOT / 'tools', ROOT / 'worker', REPO / '.github']
    for root in (r for r in roots if r.is_dir()):
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.suffix in TEXT and '__pycache__' not in path.parts and 'node_modules' not in path.parts:
                yield path.relative_to(REPO).as_posix(), path.read_text(encoding='utf-8', errors='replace')


def test_only_the_adapters_and_the_route_reference_the_price_source():
    hosts = {name for name, text in _code_files() if IEX_HOSTS.search(text)}
    adapters = {name for name, text in _code_files() if ADAPTERS.search(text)}
    assert hosts == HOST_FILES, hosts ^ HOST_FILES
    assert adapters == ADAPTER_FILES, adapters ^ ADAPTER_FILES
    assert set(boundary.ACTIONS_PRICE_ROUTES) <= ADAPTER_FILES


def _steps(job):
    return ('\n' + job.split('\n    steps:\n', 1)[1]).split('\n      - ')[1:] if '\n    steps:\n' in job else []


# Workflows that may run the full publisher, each under the same holder rules below:
# - sec-daily-public-inputs.yml: the production V step (PR-C);
# - central-v-rehearsal.yml: the GSQ-024 "검증 먼저" rehearsal (owner instruction 2026-10-24 item 3b; doc
#   CENTRAL_V_REHEARSAL_20261025.md), push-only on its own branch, no upload, no raw-repo write token. Its V step is the
#   production step byte for byte (tests/test_central_v_rehearsal_workflow.py pins that and the rest of the file).
PUBLISHER_WORKFLOWS = ('sec-daily-public-inputs.yml', 'central-v-rehearsal.yml')
# The rehearsal's presence job alone may also name the two Secrets outside the V step, and only as the yes/no comparison
# `${{ secrets.NAME != '' }}` (the runner evaluates it; the value never enters any step's environment or script, only true /
# false is placed in env), exactly once each, in a step that runs no publisher. Every other occurrence is counted as usual.
PRESENCE_ONLY = ('central-v-rehearsal.yml',)
PUBLICATION_SECRETS = ('QGV_OFFICIAL_HMAC_KEY', 'RAW_REPO_READ_TOKEN')


def _presence_expr(secret):
    return "${{ secrets.%s != '' }}" % secret


def test_workflows_reach_the_price_source_only_through_the_publication_step():
    """Holds now (no V step yet) and binds PR-C: the full publisher run only in the daily SEC workflow (and the rehearsal copy
    of its V step, PUBLISHER_WORKFLOWS), inside one step that holds the two new Secrets in its own env, continues on error and
    has neither RAW_REPO_TOKEN nor an upload; anywhere else only `--preserve-only` (validated byte copy, no prices)."""
    for path in sorted((REPO / '.github/workflows').glob('*.y*ml')):
        text = path.read_text()
        assert not IEX_HOSTS.search(text), path.name
        for line in text.splitlines():
            if 'qgv_official_publish.py' in line and path.name not in PUBLISHER_WORKFLOWS:
                assert '--preserve-only' in line, (path.name, line)
        for secret in PUBLICATION_SECRETS:
            if path.name not in PUBLISHER_WORKFLOWS:
                assert secret not in text, (path.name, secret)
        if path.name not in PUBLISHER_WORKFLOWS:
            continue
        counted = text
        if path.name in PRESENCE_ONLY:
            for secret in PUBLICATION_SECRETS:
                assert text.count(_presence_expr(secret)) == 1, (path.name, secret)
                counted = counted.replace(_presence_expr(secret), '')
        jobs = re.split(r'\n  (?=[a-z_-]+:\n)', text.split('\njobs:\n', 1)[1])
        holders = []
        for job in jobs:
            for step in _steps(job):
                seen = step
                if path.name in PRESENCE_ONLY:
                    for secret in PUBLICATION_SECRETS:
                        seen = seen.replace(_presence_expr(secret), '')
                    if seen != step:
                        assert 'qgv_official_publish.py' not in step and 'uses:' not in step, path.name
                if 'secrets.QGV_OFFICIAL_HMAC_KEY' in seen or 'secrets.RAW_REPO_READ_TOKEN' in seen or \
                        ('qgv_official_publish.py' in seen and '--preserve-only' not in seen):
                    holders.append(step)
        assert len(holders) <= 1
        if path.name in PRESENCE_ONLY:
            assert len(holders) == 1, path.name
        for step in holders:
            assert 'qgv_official_publish.py' in step and 'continue-on-error: true' in step
            assert 'RAW_REPO_TOKEN:' not in step and 'secrets.RAW_REPO_TOKEN' not in step and 'uses:' not in step
            assert 'GITHUB_STEP_SUMMARY' not in step and 'actions/upload' not in step
        assert counted.count('secrets.QGV_OFFICIAL_HMAC_KEY') <= 1 and counted.count('secrets.RAW_REPO_READ_TOKEN') <= 1


# ---- pages_freshness_guard: the qgv-official rule ----------------------------------------------------------------------
def variant(o, *, basis=None, inputs_as_of=None, pid=None, verified=None):
    v = copy.deepcopy(o)
    if basis is not None:
        v['price_source']['basis_date'] = v['times']['price_basis_date'] = basis
        v['price_source']['requested_basis_date'] = max(basis, v['price_source']['requested_basis_date'])
    if inputs_as_of is not None:
        v['times']['inputs_as_of'] = v['inputs'][0]['as_of'] = inputs_as_of
    if pid is not None:
        v['publication_id'] = 'qgvpub-' + hashlib.sha256(pid.encode()).hexdigest()
    if verified is not None:
        v['times']['verified_at'] = verified
    return qo.encode(v)


def official_line(out):
    line = next(l for l in out.splitlines() if l.startswith(f'PAGES_FRESHNESS file={qo.FILENAME} section=publication '))
    return dict(part.split('=', 1) for part in line.split()[1:])


@pytest.fixture(scope='module')
def live_body(official):
    return qo.encode(official)


def test_no_publication_anywhere_deploys(tmp_path, capsys):
    code, out = guard(write(tmp_path / 'a', {}), served({}), capsys)
    assert code == 0 and official_line(out) == {'file': qo.FILENAME, 'section': 'publication', 'verdict': 'NO_LIVE', 'kind': 'NONE',
                                               'artifact_basis': 'NONE', 'live_basis': 'NONE'}


def test_first_publication_deploys(tmp_path, capsys, live_body):
    code, out = guard(write(tmp_path / 'a', {qo.FILENAME: live_body}), served({}), capsys)
    assert code == 0 and official_line(out)['kind'] == 'NEW' and official_line(out)['artifact_basis'] == '2026-10-13'


@pytest.mark.parametrize('change, kind, refused', [
    ({}, 'EQUAL', False),
    ({'verified': '2026-10-13T23:00:00Z'}, 'CHANGED', True),                          # same id, other bytes
    ({'pid': 'b', 'basis': '2026-10-12'}, 'OLDER', True),
    ({'pid': 'b', 'basis': '2026-10-14'}, 'NEWER', False),
    ({'pid': 'b', 'inputs_as_of': '2026-10-12T22:40:00Z'}, 'OLDER', True),             # same basis, older inputs
    ({'pid': 'b', 'inputs_as_of': '2026-10-14T22:40:00Z'}, 'NEWER', False),
    ({'pid': 'b'}, 'REPLACED', False),                                                # same basis and inputs, recomputed
])
def test_publication_against_a_valid_live_copy(tmp_path, capsys, official, live_body, change, kind, refused):
    body = variant(official, **change) if change else live_body
    code, out = guard(write(tmp_path / 'a', {qo.FILENAME: body}), served({qo.FILENAME: live_body}), capsys)
    line = official_line(out)
    assert (line['kind'], line['verdict'], code) == (kind, 'REFUSED' if refused else 'PASS', 1 if refused else 0)
    assert line['live_basis'] == '2026-10-13'
    assert ('PAGES_FRESHNESS_REFUSED ' in out) == refused and 'qgvpub-' not in out


def test_a_newer_live_publication_refuses_the_older_artifact_whatever_its_inputs(tmp_path, capsys, official):
    live = variant(official, pid='live', basis='2026-10-14', inputs_as_of='2026-10-10T00:00:00Z')
    mine = variant(official, pid='mine', basis='2026-10-13', inputs_as_of='2026-10-20T00:00:00Z')
    code, out = guard(write(tmp_path / 'a', {qo.FILENAME: mine}), served({qo.FILENAME: live}), capsys)
    assert code == 1 and official_line(out)['kind'] == 'OLDER'


def test_missing_publication_is_withheld_and_the_deploy_continues(tmp_path, capsys, live_body):
    code, out = guard(write(tmp_path / 'a', {}), served({qo.FILENAME: live_body}), capsys)
    assert code == 0 and official_line(out)['verdict'] == 'WITHHELD' and official_line(out)['kind'] == 'MISSING'
    assert f'PAGES_FRESHNESS_PUBLICATION_WITHHELD file={qo.FILENAME} kind=MISSING deploy=CONTINUES\n' in out
    assert 'PAGES_FRESHNESS_PASS ' in out


@pytest.mark.parametrize('broken', [b'{not json', b'{"rank": 1}', b' ' * (qo.MAX_BYTES + 1), 'priced', 'duplicate'])
@pytest.mark.parametrize('with_new', [False, True])
def test_broken_live_publication_withholds_only_the_publication(tmp_path, capsys, official, live_body, broken, with_new):
    """D-CV16 (a): the broken live copy is not compared and never refuses the deploy; a row file that is broken still does."""
    if broken == 'priced':
        bad = json.loads(live_body)
        bad['rows'][_ranked_key(bad)]['price'] = 1.0
        broken = json.dumps(bad).encode()
    elif broken == 'duplicate':
        broken = b'{"schema":"qgv-official/1",' + live_body[1:]
    mine = {qo.FILENAME: variant(official, pid='new', basis='2026-10-14')} if with_new else {}
    code, out = guard(write(tmp_path / 'a', mine), served({qo.FILENAME: broken}), capsys)
    assert code == 0 and official_line(out)['kind'] == 'LIVE_INVALID' and official_line(out)['verdict'] == 'WITHHELD'
    assert f'PAGES_FRESHNESS_PUBLICATION_WITHHELD file={qo.FILENAME} kind=LIVE_INVALID deploy=CONTINUES\n' in out
    assert f'PAGES_FRESHNESS_LIVE_INVALID file={qo.FILENAME}' not in out and ' live_invalid=0 ' in out
    code, out = guard(write(tmp_path / 'b', mine), served({qo.FILENAME: broken, sec_qgv2.FILENAME: b'{not json'}), capsys)
    assert code == 1 and f'PAGES_FRESHNESS_LIVE_INVALID file={sec_qgv2.FILENAME} deploy=REFUSED\n' in out


@pytest.mark.parametrize('live', ['none', 'valid', 'broken'])
def test_an_invalid_artifact_publication_is_refused_whatever_the_live_state(tmp_path, capsys, official, live_body, live):
    bad = json.loads(live_body)
    bad['rows'][_ranked_key(bad)]['total'] -= 1e-9
    site = served({} if live == 'none' else {qo.FILENAME: live_body if live == 'valid' else b'{}'})
    code, out = guard(write(tmp_path / 'a', {qo.FILENAME: json.dumps(bad).encode()}), site, capsys)
    assert code == 1 and official_line(out)['kind'] == 'ARTIFACT_INVALID' and official_line(out)['verdict'] == 'REFUSED'


def test_the_status_file_is_never_read_or_compared(tmp_path, capsys, official, live_body):
    site = served({qo.FILENAME: live_body, qo.STATUS_FILENAME: b'{"anything": "older"}'})
    mine = {qo.FILENAME: live_body, qo.STATUS_FILENAME: b'{"attempt_state": "SUPPLY_FAILED"}'}
    code, out = guard(write(tmp_path / 'a', mine), site, capsys)
    assert code == 0 and official_line(out)['kind'] == 'EQUAL' and qo.STATUS_FILENAME not in out
    assert not any(qo.STATUS_FILENAME in url for url in site.urls)


def test_an_unreachable_live_publication_fails_closed(tmp_path, capsys, live_body):
    import urllib.error

    class Flaky(Site):
        def __call__(self, request, **kw):
            if qo.FILENAME in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 500, '', {}, None)
            return super().__call__(request, **kw)
    code, out = guard(write(tmp_path / 'a', {qo.FILENAME: live_body}), Flaky({}), capsys)
    assert code == 1 and out == f'PAGES_FRESHNESS_LIVE_UNREACHABLE file={qo.FILENAME} deploy=REFUSED\n'


def test_freshness_reads_the_publishers_live_url():
    fresh = load_tool('pages_freshness_guard')
    assert fresh.official_tool.LIVE_URL == publisher.LIVE_URL == 'https://kco994553-star.github.io/Investment-System1/' + qo.FILENAME
    assert set(fresh.OFFICIAL_VERDICTS.values()) == {'NO_LIVE', 'PASS', 'REFUSED', 'WITHHELD'}
    assert {k for k, v in fresh.OFFICIAL_VERDICTS.items() if v == 'REFUSED'} == {'CHANGED', 'OLDER', 'ARTIFACT_INVALID'}


# ---- AUDIT.md: the GSQ-024 section is appended, earlier text unchanged ------------------------------------------------
AUDIT_BEFORE_SECTION_10_SHA256 = '1ca338a358a780d97ff774ae6db8c05356f8596aa86809fa3ed4964f31526dc2'   # the file as of 068989fa


def test_audit_section_is_append_only():
    text = (ROOT / 'docs/public_price_boundary/AUDIT.md').read_text(encoding='utf-8')
    before, marker, section = text.partition('\n## 10. GSQ-024 후속')
    assert marker and hashlib.sha256(before.encode('utf-8')).hexdigest() == AUDIT_BEFORE_SECTION_10_SHA256
    for phrase in ('qgv_official_publish.py', 'ACTIONS_PRICE_ROUTES', 'AUDITED_ROUTES', 'rows.<code>.rank', 'qgv-official.json',
                   'qgv-official-status.json', 'PRICE_DEPENDENT_NOT_COMPUTABLE', 'D-CV16 (a)', '§4-4', 'GSQ-010'):
        assert phrase in section, phrase
    # The section adds no row to the audited-route table that test_original_27_plus_ishares_routes_are_accounted_for counts.
    assert not [l for l in section.splitlines() if l.startswith('| `') and '공개 출력 경로' in l and '| 정리 필요 |' in l]
