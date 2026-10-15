"""One-off all-shards Universe504 collection (owner instruction 2026-10-15). Synthetic SEC bytes and fake transports only."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import tarfile

from investment_system.providers.sec_collection import MIN_REQUEST_INTERVAL, SecResponse
from investment_system.providers.sec_universe_collection import daily_partition, universe_registry
from investment_system.universe import sec_qgv2 as q
from investment_system.universe import sec_universe_qg as qg
from investment_system.universe import sec_universe_shares as shares

ROOT = Path(__file__).resolve().parents[1]
WHEN = datetime(2026, 10, 15, 23, 0, tzinfo=timezone.utc)
UA = 'Synthetic setting ' + 'tester' + chr(64) + 'example.org'
TOKEN = 'synthetic-raw-token-value-all-shards-0123'


def load_tool(name):
    spec = importlib.util.spec_from_file_location('_all_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REF = load_tool('sec_qgv2_reference')
SPEC = REF.universe_spec()   # 27 synthetic issuers (code, cik, sic, n) spread over all 7 shards
CODE = {cik: code for code, cik, _, _ in SPEC}


def shard_of(cik):
    return int(sha256(cik.encode()).hexdigest(), 16) % 7


def sec_ticker(code):
    venue, symbol = code.split(':')
    return symbol.replace('.', '-'), 'Nasdaq' if venue == 'NASDAQ' else 'NYSE'


def ticker_body():
    return json.dumps({'fields': ['cik', 'name', 'ticker', 'exchange'],
                       'data': [[int(cik), 'Synthetic', *sec_ticker(code)] for code, cik, _, _ in SPEC]}).encode()


def issuer_bytes(cik, *, empty=False):
    code = CODE[cik]
    _, _, sic, n = next(s for s in SPEC if s[1] == cik)
    ticker, exchange = sec_ticker(code)
    if empty:   # an issuer with no annual SEC financials at all
        subs = {'cik': int(cik), 'sic': sic, 'tickers': [ticker], 'exchanges': [exchange], 'filings': {'recent': {
            'accessionNumber': [], 'form': [], 'filingDate': [], 'reportDate': [], 'acceptanceDateTime': [], 'primaryDocument': []}}}
        return json.dumps({'cik': int(cik), 'facts': {}}).encode(), json.dumps(subs).encode()
    return REF.synthetic_sec(cik, sic=sic, seed=n, growth=0.02 + 0.01 * (n % 9), ebit_margin=0.08 + 0.015 * (n % 11),
                             debt_to_assets=0.05 + 0.03 * (n % 7), share_growth=-0.02 + 0.006 * (n % 8),
                             financial=sic == '6021', equity_to_assets=0.1 if sic == '6021' else 0.5, ticker=ticker, exchange=exchange)


class Sec:
    """Fake SEC transport on a fake monotonic clock that only the client's pacer advances."""
    def __init__(self, *, empty=(), fail=()):
        self.empty, self.fail, self.clock, self.calls = set(empty), set(fail), [0.0], []

    def transport(self, url, *, headers, timeout, max_body_bytes):
        self.calls.append((url, self.clock[0], headers['User-Agent']))
        if url.endswith('company_tickers_exchange.json'):
            return SecResponse(200, ticker_body(), final_url=url)
        cik = url.split('CIK')[-1].split('.')[0]
        if cik in self.fail:
            return SecResponse(403, b'', final_url=url)
        facts, subs = issuer_bytes(cik, empty=cik in self.empty)
        return SecResponse(200, facts if 'companyfacts' in url else subs, final_url=url)

    def kwargs(self, when):
        def sleep(seconds):
            self.clock[0] += seconds
        return {'transport': self.transport, 'sleep': sleep, 'monotonic': lambda: self.clock[0], 'now': lambda: when}


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


def pages(folder=None):
    """Previous Pages copies from a folder written by an earlier run; absent -> 404."""
    import urllib.error
    def opener(request, **_):
        path = None if folder is None else Path(folder) / request.full_url.rsplit('/', 1)[1]
        if path is None or not path.is_file():
            raise urllib.error.HTTPError(request.full_url, 404, '', {}, None)
        return Response(request.full_url, path.read_bytes())
    return opener


def run(tool, out, sec, when=WHEN, previous=None, **kwargs):
    out.mkdir(parents=True, exist_ok=True)
    return tool.run(out, live=True, environ=kwargs.pop('environ', {'SEC_USER_AGENT': UA}), now=lambda: when,
                    client_kwargs=sec.kwargs(when), open_previous=pages(previous), **kwargs)


def files(out):
    return (shares.require_universe_shares(json.loads((out / shares.FILENAME).read_text())),
            qg.require_universe_qg(json.loads((out / qg.FILENAME).read_text())),
            q.require_qgv2(json.loads((out / q.FILENAME).read_text())))


def assert_no_identifiers(out):
    for secret in (UA, 'tester' + chr(64), 'sec.gov', '000000100', 'NASDAQ:', 'NYSE:', 'MMM', 'revenue', TOKEN):
        assert secret not in out


def test_spec_reaches_every_shard():
    assert sorted({shard_of(cik) for _, cik, _, _ in SPEC}) == list(range(7))


# ---------------- daily mode is unchanged ----------------
def test_daily_mode_collects_only_todays_shard_exactly_as_before(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    today = WHEN.date().toordinal() % 7
    issuers = daily_partition(universe_registry(ticker_body()), shard_count=7, shard_index=today)
    assert issuers
    sec = Sec()
    assert run(tool, tmp_path / 'a', sec) == 0
    out = capsys.readouterr().out
    # one registry request plus companyfacts + submissions per issuer of today's shard (no cover filing in these bytes)
    assert len(sec.calls) == len({u for u, _, _ in sec.calls}) == 1 + 2 * len(issuers)
    assert not [l for l in out.splitlines() if l.startswith('SEC_UNIVERSE_SHARD ')] and 'shard=all/' not in out
    assert [l.split()[1] for l in out.splitlines() if l.startswith(('SEC_UNIVERSE_SHARES shard=', 'SEC_UNIVERSE_QG shard=', 'SEC_QGV2 shard='))] \
        == [f'shard={today}/7'] * 3
    s, g, v = files(tmp_path / 'a')
    assert s['last_shard_index'] == g['last_shard_index'] == v['last_shard_index'] == today
    collected = {code for issuer in issuers for code in issuer.codes}
    assert {c for c, r in v['records'].items() if r['acquired_at'] is not None} == collected
    # all_shards=False is the same call as the default: identical bytes in every output file
    assert run(tool, tmp_path / 'b', Sec(), all_shards=False) == 0
    capsys.readouterr()
    for name in (shares.FILENAME, qg.FILENAME, q.FILENAME):
        assert (tmp_path / 'a' / name).read_bytes() == (tmp_path / 'b' / name).read_bytes()


def test_collect_explicit_shard_index_matches_the_date_derived_shard():
    tool = load_tool('sec_universe_shares')
    today = WHEN.date().toordinal() % 7
    a, b = {}, {}
    implicit = tool.collect(user_agent=UA, now=lambda: WHEN, client_kwargs=Sec().kwargs(WHEN), qgv2_updates=a)
    explicit = tool.collect(user_agent=UA, now=lambda: WHEN, client_kwargs=Sec().kwargs(WHEN), qgv2_updates=b, shard_index=today)
    assert implicit[4] == explicit[4] == today and implicit[0] == explicit[0] and a == b and a
    other = (today + 1) % 7
    rows = tool.collect(user_agent=UA, now=lambda: WHEN, client_kwargs=Sec().kwargs(WHEN), shard_index=other)
    assert rows[4] == other and {CODE[c] for c in CODE if shard_of(c) == other} == set(rows[0])


# ---------------- all shards in one run ----------------
def test_all_shards_covers_every_shard_with_one_registry_fetch_and_the_same_pacing(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    sec = Sec()
    assert run(tool, tmp_path, sec, all_shards=True) == 0
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if l.startswith('SEC_UNIVERSE_SHARD ')]
    assert [l.split()[1] for l in lines] == [f'shard={i}/7' for i in range(7)] and all(l.endswith('status=OK') for l in lines)
    urls = [u for u, _, _ in sec.calls]
    assert sum(u.endswith('company_tickers_exchange.json') for u in urls) == 1   # registry fetched once
    assert len(urls) == len(set(urls)) == 1 + 2 * len(SPEC)
    assert all(ua == UA for _, _, ua in sec.calls)
    # one serial paced client: every Universe request at least MIN_REQUEST_INTERVAL after the previous one
    times = [t for _, t, _ in sec.calls[1:]]
    assert all(b - a >= MIN_REQUEST_INTERVAL - 1e-9 for a, b in zip(times, times[1:]))
    s, g, v = files(tmp_path)
    stamp = WHEN.isoformat().replace('+00:00', 'Z')
    for code, cik, _, _ in SPEC:
        assert v['records'][code]['acquired_at'] == stamp and v['records'][code]['state'] == 'LIVE'
        assert g['records'][code]['acquired_at'] == stamp
    assert sum(r['axes']['Q']['score'] is not None for r in v['records'].values()) > 0
    assert s['last_shard_index'] == g['last_shard_index'] == v['last_shard_index'] == 6
    for prefix in ('SEC_UNIVERSE_SHARES shard=all/7 shards_ok=7 shards_failed=0 ', 'SEC_UNIVERSE_QG shard=all/7 shards_ok=7 ',
                   'SEC_QGV2 shard=all/7 shards_ok=7 '):
        assert sum(l.startswith(prefix) for l in out.splitlines()) == 1
    assert f'codes={len(SPEC)} ' in next(l for l in out.splitlines() if l.startswith('SEC_QGV2 shard=all/7'))
    assert 'RAW_UPLOAD_NOT_CONFIGURED shard=6' in out and 'ALL_SHARDS_PARTIAL' not in out
    assert_no_identifiers(out)
    coverage = load_tool('published_coverage').report(tmp_path)
    assert ' shards_seen=7/7 ' in coverage and f' acquired_oldest={WHEN.date().isoformat()} ' in coverage


def test_a_failing_shard_keeps_its_previous_rows_and_the_others_are_written(tmp_path, capsys, monkeypatch):
    tool = load_tool('sec_universe_shares')
    first = tmp_path / 'first'
    assert run(tool, first, Sec(), when=WHEN - timedelta(days=1), all_shards=True) == 0
    capsys.readouterr()
    before = files(first)
    bad = shard_of(SPEC[0][1])
    bad_ciks = {cik for _, cik, _, _ in SPEC if shard_of(cik) == bad}
    second = tmp_path / 'second'
    assert run(tool, second, Sec(fail=bad_ciks), previous=first, all_shards=True) == 0
    out = capsys.readouterr().out
    line = next(l for l in out.splitlines() if l.startswith(f'SEC_UNIVERSE_SHARD shard={bad}/7 '))
    assert f'collected=0 failed={len(bad_ciks)} ' in line and line.endswith('status=SHARD_ALL_FAILED previous_kept')
    assert f'SEC_UNIVERSE_SHARES ALL_SHARDS_PARTIAL failed_shards={bad} previous_kept' in out
    assert f'shards_ok=6 shards_failed=1 failed_shards={bad} ' in out
    after = files(second)
    old, new = (WHEN - timedelta(days=1)).isoformat().replace('+00:00', 'Z'), WHEN.isoformat().replace('+00:00', 'Z')
    for code, cik, _, _ in SPEC:
        want = old if cik in bad_ciks else new
        assert after[2]['records'][code]['acquired_at'] == want and after[1]['records'][code]['acquired_at'] == want
        if cik in bad_ciks:
            assert after[2]['records'][code]['metrics'].keys() == before[2]['records'][code]['metrics'].keys()
            assert after[0]['records'][code]['reason_codes'] == before[0]['records'][code]['reason_codes']
    # a shard whose collection raises is reported the same way; the run still writes the other shards
    real = tool.collect
    def flaky(**kwargs):
        if kwargs.get('shard_index') == bad:
            raise RuntimeError('synthetic')
        return real(**kwargs)
    monkeypatch.setattr(tool, 'collect', flaky)
    third = tmp_path / 'third'
    assert run(tool, third, Sec(), previous=first, all_shards=True) == 0
    out = capsys.readouterr().out
    assert f'SEC_UNIVERSE_SHARD shard={bad}/7 status=SHARD_FAILED code=SEC_UNIVERSE_FAILED previous_kept' in out
    v = files(third)[2]
    assert all(v['records'][code]['acquired_at'] == (old if cik in bad_ciks else new) for code, cik, _, _ in SPEC)
    assert_no_identifiers(out)


def test_codes_without_data_are_not_available_with_reasons_never_zero_or_an_older_row(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    first = tmp_path / 'first'
    assert run(tool, first, Sec(), when=WHEN - timedelta(days=1), all_shards=True) == 0
    empty = {SPEC[1][1], SPEC[20][1]}
    second = tmp_path / 'second'
    assert run(tool, second, Sec(empty=empty), previous=first, all_shards=True) == 0
    s, g, v = files(second)
    for cik in empty:
        row = v['records'][CODE[cik]]
        assert row['state'] == 'NOT_AVAILABLE' and row['reason_codes'] == ['NO_ANNUAL_SEC_FINANCIALS'] and row['metrics'] == {}
        assert all(value is None for value in row['factors'].values())
        assert row['axes']['Q']['score'] is None and row['axes']['G']['score'] is None
        assert all(value is None for value in row['v_inputs_v2'].values() if not isinstance(value, (list, dict)))
        assert row['acquired_at'] == WHEN.isoformat().replace('+00:00', 'Z')
        q_row = g['records'][CODE[cik]]
        assert q_row['state'] == 'NOT_AVAILABLE' and q_row['reason_codes'] and all(x is None for x in q_row['factors'].values())
    # every NA row anywhere carries a reason and no number
    for payload in (g, v):
        for row in payload['records'].values():
            if row['state'] == 'NOT_AVAILABLE':
                assert row['reason_codes'] and all(x is None for x in row['factors'].values())
    for row in s['records'].values():
        if row['state'] == 'NOT_AVAILABLE':
            assert row['shares'] is None and row['reason_codes']
    assert v['records']['BATS:CBOE']['reason_codes'] in (['CIK_UNRESOLVED'], ['NOT_COLLECTED'])
    # The daily rule (unchanged) keeps an older row with data when today's row has none; the one-off run does not.
    daily = tmp_path / 'daily'
    when = WHEN
    while shard_of(SPEC[1][1]) != when.date().toordinal() % 7:
        when += timedelta(days=1)
    assert run(tool, daily, Sec(empty=empty), when=when, previous=first) == 0
    assert files(daily)[2]['records'][SPEC[1][0]]['metrics'] == files(first)[2]['records'][SPEC[1][0]]['metrics'] != {}
    assert_no_identifiers(capsys.readouterr().out)


def test_raw_is_uploaded_per_shard_with_its_own_tag(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    requests = []
    def upload(request, **_):
        requests.append(request)
        return Response(request.full_url, b'{"id": 7}', 201)
    assert run(tool, tmp_path, Sec(), environ={'SEC_USER_AGENT': UA, 'RAW_REPO_TOKEN': TOKEN}, open_upload=upload, all_shards=True) == 0
    out = capsys.readouterr().out
    day = WHEN.date().isoformat()
    created = [json.loads(r.data)['tag_name'] for r in requests if r.full_url.endswith('/releases')]
    assert created == [f'sec-universe-raw-{day}-all-shard{i}' for i in range(7)]
    assert sum(l.startswith(f'shard={i} RAW_UPLOADED ') for i in range(7) for l in out.splitlines()) == 7
    archives = [r for r in requests if r.full_url.endswith('.tar.gz')]
    for i, archive in enumerate(archives):
        with tarfile.open(fileobj=io.BytesIO(archive.data)) as tar:
            manifest = json.loads(tar.extractfile(f'sec-universe-raw-{day}-all-shard{i}/manifest.json').read())
        assert manifest['shard_index'] == i and {c['cik'] for c in manifest['companies']} == {cik for _, cik, _, _ in SPEC if shard_of(cik) == i}
    assert TOKEN not in out and all(TOKEN not in p.read_text() for p in tmp_path.iterdir())


def test_cli_flag_reaches_run_only_when_given(tmp_path, monkeypatch):
    tool = load_tool('sec_universe_shares')
    seen = []
    monkeypatch.setattr(tool, 'run', lambda out, **kwargs: seen.append(kwargs) or 0)
    tool.main(['--out', str(tmp_path), '--live'])
    tool.main(['--out', str(tmp_path), '--live', '--all-shards'])
    assert seen == [{'live': True, 'preserve_only': False}, {'live': True, 'preserve_only': False, 'all_shards': True}]


def test_workflow_dispatch_input_and_final_coverage_step():
    text = (ROOT.parent / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    head, jobs = text.split('\njobs:\n', 1)
    assert "all_shards:\n        description: '1회성: 504종목 전체 샤드를 한 번에 수집(새 계산 규칙 게시용)'\n        type: boolean" in head
    assert 'default: false' in head and "cron: '17 22 * * *'" in head
    step = jobs.index('- name: Collect Universe504 SEC shard')
    body = jobs[step:jobs.index('- name:', step + 10)]
    # Scheduled runs: the expression is '' and the command is the daily one; only a dispatch with the box ticked adds the flag.
    assert "ALL_SHARDS_FLAG: ${{ github.event_name == 'workflow_dispatch' && inputs.all_shards && '--all-shards' || '' }}" in body
    assert 'python implementation/tools/sec_universe_shares.py --live --out "$RUNNER_TEMP/public-cockpit" $ALL_SHARDS_FLAG\n' in body
    assert text.count('sec_universe_shares.py --live') == 1 and text.count('--all-shards') == 1
    collect = jobs[jobs.index('\n  collect:\n'):jobs.index('\n  verify:\n')]
    assert "timeout-minutes: ${{ github.event_name == 'workflow_dispatch' && inputs.all_shards && 120 || 40 }}" in collect
    names = [line.strip()[len('- name: '):] for line in collect.splitlines() if line.strip().startswith('- name: ')]
    assert names[-2:] == ['Report published Q·G coverage of the final artifact (counts only)', 'Upload checked public SEC Pages artifact']
    assert 'python implementation/tools/published_coverage.py --artifact-dir "$RUNNER_TEMP/public-cockpit"' in collect
    # W-F1/W-F2 order is unchanged: ledger right after the DART projection, raw-first previous source
    run_of = lambda name: collect.index('python implementation/tools/' + name)
    assert run_of('sec_universe_shares.py') < run_of('project_dart_qgv2.py') < run_of('forward_validation_ledger.py') \
        < run_of('public_classification_pipeline.py') < run_of('news_signals.py') < run_of('published_coverage.py')
    assert 'FORWARD_LEDGER_PREVIOUS_SOURCE: RAW_FIRST' in collect
