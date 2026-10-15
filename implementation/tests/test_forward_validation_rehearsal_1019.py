"""Offline rehearsal of the 10/19 forward-validation recording (queue 2-2). Synthetic data and fake transports only.

The daily workflow `sec-daily-public-inputs.yml` is replayed step by step for the simulated runs of 2026-10-16 (Fri,
before the start), 2026-10-17 (Sat), 2026-10-19 (Mon, first session) and 2026-10-20 (Tue). Every step uses the repo's
own tool entry points with the fake SEC/DART transports already used in tests; the live Pages copy is emulated by an
in-memory site that each simulated deploy replaces, so each day reads the previous day's ledger through the same
`fetch_previous` path. No network, credential, price, holding or personal value is used.

Checks: rows are appended (v2 default + v1 comparison) only on a completed session on its own date; nothing is
backfilled; NA is never filled with 0; public output carries no price or personal value; the chain is deterministic.
"""
from datetime import datetime, timedelta, timezone
import contextlib
import hashlib
import io
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
import sys
import urllib.error

import pytest

from investment_system.validation import forward_ledger as fl

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
sys.path.insert(0, str(TOOLS))
PAGES = 'https://kco994553-star.github.io/Investment-System1/'
UA = 'synthetic rehearsal setting'
DART_KEY_ENV = 'DART_API_KEY'
UTC = timezone.utc


def load_tool(name):
    spec = importlib.util.spec_from_file_location('_rehearsal_' + name, TOOLS / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REF = load_tool('sec_qgv2_reference')


def clock(day, hour, minute):
    return datetime.fromisoformat(day).replace(hour=hour, minute=minute, tzinfo=UTC)


# ---- emulated live Pages (the previous-copy read path of every tool) ----
class Response:
    def __init__(self, url, body):
        self.url, self.body, self.status = url, body, 200

    def geturl(self):
        return self.url

    def read(self, n=-1):
        return self.body if n < 0 else self.body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class Site:
    """The published Pages copy. `deploy` replaces it with a checked artifact folder, like actions/deploy-pages."""

    def __init__(self, files=None):
        self.files = dict(files or {})
        self.reads = []

    def __call__(self, request, **_):
        url = request.full_url
        name = url[len(PAGES):] if url.startswith(PAGES) else None
        self.reads.append(name)
        if name not in self.files:
            raise urllib.error.HTTPError(url, 404, '', {}, None)
        return Response(url, self.files[name])

    def deploy(self, folder):
        self.files = {p.name: p.read_bytes() for p in Path(folder).iterdir() if p.is_file() and not p.name.startswith('.')}


# ---- fake SEC / DART transports (synthetic bytes only) ----
class SimulatedClock(datetime):
    """datetime whose now() is the simulated run time (set per step). Only `now` differs from datetime."""
    moment = None

    @classmethod
    def now(cls, tz=None):
        value = cls.fromtimestamp(cls.moment.timestamp(), UTC)
        return value if tz is None else value.astimezone(tz)


def target_client(acquired):
    """SEC client for the 17 US TARGET issuers: synthetic multi-year companyfacts plus a reported share count."""
    from investment_system.markets.us import US_LISTINGS
    order = sorted(US_LISTINGS)

    class Client:
        def __init__(self, _agent):
            pass

        def collect(self, company, cik):
            n = order.index(company)
            facts, subs = REF.synthetic_sec(cik, seed=40 + n, growth=0.05 + 0.01 * n, ebit_margin=0.1 + 0.01 * n)
            facts, subs = json.loads(facts), json.loads(subs)
            facts['facts']['dei'] = {'EntityCommonStockSharesOutstanding': {'units': {'shares': [
                {'end': '2025-12-31', 'val': 1000 + n, 'accn': f'{cik}-26-000010', 'fy': 2025, 'fp': 'FY', 'form': '10-K',
                 'filed': '2026-02-15'}]}}}
            # Filing metadata for every accession the facts cite (newest first), as SEC submissions lists them.
            filings = {}
            for concept in facts['facts']['us-gaap'].values():
                for rows in concept['units'].values():
                    for row in rows:
                        if 'accn' in row and row['accn'] not in filings:
                            filings[row['accn']] = (row['form'], row['filed'], row['end'])
            ordered = sorted(filings.items(), key=lambda item: (item[1][1], item[0]), reverse=True)
            subs['filings']['recent'] = {
                'accessionNumber': [a for a, _ in ordered], 'form': [f for _, (f, _, _) in ordered],
                'filingDate': [d for _, (_, d, _) in ordered], 'reportDate': [e for _, (_, _, e) in ordered],
                'acceptanceDateTime': [d + 'T12:00:00Z' for _, (_, d, _) in ordered],
                'primaryDocument': ['syn-' + e.replace('-', '') + '.htm' for _, (_, _, e) in ordered]}
            return json.dumps(facts).encode(), json.dumps(subs).encode(), acquired
    return Client


OFFLINE_PLACEHOLDERS = {'company-classification.json', 'news-signals.json', 'sec-disclosures.json'}


def universe_kwargs(when, *, fail=False):
    from investment_system.providers.sec_collection import SecResponse
    from tests.test_sec_universe_shares import client_kwargs, transport_for

    def unavailable(url, *, headers, timeout, max_body_bytes):
        return SecResponse(403, b'', final_url=url)  # every SEC request refused (registry included)
    return client_kwargs(unavailable if fail else transport_for([]), when)


def schema_one_ledger(at):
    """The ledger as the 10/13 deploy published it: schema 1, NOT_STARTED, no record (the code of that day)."""
    ledger = fl.new_ledger(at)
    ledger['schema_version'], ledger['strategy'] = 1, fl.STRATEGY
    ledger['versions'].pop(fl.V2_VERSION)
    ledger['version_status'].pop(fl.V2_VERSION)
    return fl.encode(fl.require_ledger(ledger))


def seeded_site(published_at):
    """Pages before the rehearsal: the schema-1 NOT_STARTED ledger and a Universe504 v2 file whose synthetic peers came
    from earlier shards (the TARGET Q/G percentiles need at least 8 peers)."""
    from investment_system.universe import sec_qgv2 as q, sec_universe_qg as uq, sec_universe_shares as us
    rows = REF.synthetic_universe_updates(acquired_at=published_at - timedelta(minutes=20))
    shard, registry = published_at.date().toordinal() % 7, hashlib.sha256(b'synthetic-registry').hexdigest()
    payload = q.merge(None, rows, as_of=published_at, shard_index=shard, registry_sha256=registry, unresolved=set())
    # The two other Universe files as earlier shards left them (rows NOT_COLLECTED here; only their presence matters).
    shares = us.merge(None, {}, as_of=published_at, shard_index=shard, registry_sha256=registry)
    factors = uq.merge(None, {}, as_of=published_at, shard_index=shard, registry_sha256=registry)
    return Site({q.FILENAME: q.encode(payload), us.FILENAME: us.encode(shares), uq.FILENAME: uq.encode(factors),
                 fl.FILENAME: schema_one_ledger(clock('2026-10-13', 9, 50))})


# ---- one simulated daily run (same step order as sec-daily-public-inputs.yml) ----
def daily_run(work, site, day, *, deploy=True, universe_fails=False):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), pytest.MonkeyPatch.context() as mp:
        # Wall-clock reads (the TARGET step's time stamp and 'not in the future' checks) see the simulated run time.
        import public_sec_inputs
        SimulatedClock.moment = clock(day, 22, 20)
        mp.setattr(public_sec_inputs, 'datetime', SimulatedClock)
        out, log = _daily_run(work, site, day, deploy=deploy, universe_fails=universe_fails)
    log['printed'] = buffer.getvalue()
    return out, log


def _daily_run(work, site, day, *, deploy, universe_fails):
    from tests.dart_fake_opendart import FAKE_KEY
    from tests.test_dart_qgv2_history import SixAnnualDart
    build, guard = load_tool('build_pages_cockpit'), load_tool('pages_artifact_guard')
    pipeline, shares = load_tool('public_screens_pipeline'), load_tool('sec_universe_shares')
    dart, project, ledger = load_tool('dart_daily'), load_tool('project_dart_qgv2'), load_tool('forward_validation_ledger')
    out = work / day
    log = {'previous_ledger': site.files.get(fl.FILENAME), 'guard': []}

    def check(step):
        receipt = guard.scan_artifact(out)
        log['guard'].append((step, receipt['pages_artifact_guard']))
        assert receipt['pages_artifact_guard'] == 'PASS', (step, receipt.get('violations'))

    build.build_public_cockpit(out)
    check('build')
    acquired = SimulatedClock.fromtimestamp(clock(day, 22, 19).timestamp(), UTC)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pipeline, 'datetime', SimulatedClock)
        result = pipeline.collect(out, environ={'SEC_USER_AGENT': UA}, client_factory=target_client(acquired))
    assert result['failed_companies'] == 0
    check('screens')
    assert dart.run(out, environ={DART_KEY_ENV: FAKE_KEY}, transport=SixAnnualDart(), now=clock(day, 22, 24), max_calls=30,
                    open_previous=site, include_qgv2=True, collect_history=True) == 0
    check('dart')
    when = clock(day, 22, 28)
    assert shares.run(out, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when,
                      client_kwargs=universe_kwargs(when, fail=universe_fails), open_previous=site) == 0
    check('universe')
    assert project.project(out) == 0
    check('project')
    log['ledger_exit'] = ledger.run(out, environ={}, now=lambda: clock(day, 22, 45), open_previous=site)
    if log['ledger_exit'] == 0:
        check('ledger')
        if deploy:
            site.deploy(out)
    return out, log


def ledger_of(folder):
    return fl.require_ledger(fl.parse_json((Path(folder) / fl.FILENAME).read_bytes()))


DAYS = ('2026-10-16', '2026-10-17', '2026-10-19', '2026-10-20')


def rehearse(work, plan=None):
    work.mkdir(parents=True)
    site = seeded_site(clock('2026-10-15', 22, 40))
    runs = {}
    for day, options in (plan or [(d, {}) for d in DAYS]):
        runs[day] = daily_run(work, site, day, **options)
    return site, runs


@pytest.fixture(scope='module')
def chain(tmp_path_factory):
    return rehearse(tmp_path_factory.mktemp('rehearsal') / 'a')


def rows(folder, version):
    return ledger_of(folder)['versions'][version]


# ---- 1. chain: each day reads the previous day's published ledger; nothing before the start ----
def test_each_run_reads_the_previously_deployed_ledger_and_pre_start_runs_record_nothing(chain):
    site, runs = chain
    assert all(log['ledger_exit'] == 0 for _, log in runs.values())
    previous = schema_one_ledger(clock('2026-10-13', 9, 50))
    for day in DAYS:
        out, log = runs[day]
        assert log['previous_ledger'] == previous  # read path: the live Pages copy deployed by the run before
        previous = (out / fl.FILENAME).read_bytes()
    for day in ('2026-10-16', '2026-10-17'):
        ledger = ledger_of(runs[day][0])
        assert ledger['schema_version'] == 2 and ledger['status'] == 'NOT_STARTED'
        assert ledger['versions'] == {fl.VERSION: [], fl.V_VERSION: [], fl.V2_VERSION: []}
    assert ('status=NOT_STARTED records=0 appended=0 record=NONE session=2026-10-16 v2_records=0 v2_record=NONE'
            in runs['2026-10-16'][1]['printed'])
    assert ('status=NOT_STARTED records=0 appended=0 record=NONE session=NONE v2_records=0 v2_record=NONE'
            in runs['2026-10-17'][1]['printed'])
    assert site.files[fl.FILENAME] == (runs['2026-10-20'][0] / fl.FILENAME).read_bytes()


# ---- 2. rows appended: v2 default + v1 comparison, same session only, no backfill ----
def test_first_session_appends_one_v2_and_one_v1_row_and_never_backfills(chain):
    _, runs = chain
    mon, tue = runs['2026-10-19'][0], runs['2026-10-20'][0]
    for version, strategy in ((fl.V2_VERSION, fl.V2_STRATEGY), (fl.VERSION, fl.STRATEGY)):
        [first] = rows(mon, version)
        assert first['date'] == '2026-10-19' and first['state'] == 'RECORDED' and first['reason_codes'] == []
        assert first['strategy'] == strategy and first['calibration'] == 'UNCALIBRATED'
        assert first['created_at'] == '2026-10-19T22:45:00+00:00' and first['qg_as_of'].startswith('2026-10-19T22:')
        # 2026-10-16 is a completed session before the start: never recorded, then or later.
        later = rows(tue, version)
        assert [r['date'] for r in later] == ['2026-10-19', '2026-10-20']
        assert fl.canonical(later[0]) == fl.canonical(first)  # the 10/19 row is carried byte-identically
    ledger = ledger_of(tue)
    assert ledger['versions'][fl.V_VERSION] == []
    assert ledger['version_status'][fl.V_VERSION]['reason_codes'] == ['V_REQUIRES_DEVICE_PRICES']
    assert 'appended=1 record=RECORDED session=2026-10-19 v2_records=1 v2_record=RECORDED' in runs['2026-10-19'][1]['printed']
    assert ('records=2 appended=1 record=RECORDED session=2026-10-20 v2_records=2 v2_record=RECORDED'
            in runs['2026-10-20'][1]['printed'])


def test_rows_point_at_the_same_runs_public_inputs_and_target_v0(chain):
    _, runs = chain
    for day in ('2026-10-19', '2026-10-20'):
        out = runs[day][0]
        catalog = json.loads((out / 'actual-catalog.json').read_text())
        sha = lambda name: hashlib.sha256((out / name).read_bytes()).hexdigest()
        v1, v2 = rows(out, fl.VERSION)[-1], rows(out, fl.V2_VERSION)[-1]
        assert v1['source_sha256'] == {name: sha(name) for name in fl.SOURCES}
        assert v2['source_sha256'] == {name: sha(name) for name in fl.V2_SOURCES}
        assert v2['reference_sources']['hanmi']['sha256'] == sha('dart-financials.json')
        for row in (v1, v2):
            assert row['date'] == day
            assert row['target']['weights_units'] == dict(zip(fl.IDS, (i['target_units'] for i in catalog['instruments'])))
            assert sum(row['target']['weights_units'].values()) == 10000


# ---- 3. NA stays NA (null), never 0 ----
def test_missing_values_stay_null_and_scores_match_the_published_inputs(chain):
    from investment_system.universe import sec_qgv2 as q
    _, runs = chain
    for day in ('2026-10-19', '2026-10-20'):
        out = runs[day][0]
        source = q.require_qgv2(q.parse_json((out / q.FILENAME).read_bytes()))
        factors = json.loads((out / 'sec-qg-factors.json').read_text())['data']['companies']
        v1, v2 = rows(out, fl.VERSION)[-1], rows(out, fl.V2_VERSION)[-1]
        for row in (v1, v2):
            for company in row['companies'].values():
                for axis in ('Q', 'G'):
                    value = company[axis]
                    assert (value['score'] is None) == (value['coverage'] == 'BLOCKED')
                    if company['state'] == 'NOT_AVAILABLE':
                        assert value['score'] is None
        for cid in fl.IDS:
            assert v1['companies'][cid] == fl.company_axes(factors[cid])
            if cid != 'hanmi':  # hanmi: the optional DART reference, checked below
                for axis in ('Q', 'G'):
                    assert v2['companies'][cid][axis]['score'] == source['target'][cid]['axes'][axis]['score']
        # Issuers without a public source stay NA in both versions; no zero is substituted.
        assert v1['companies']['tokyo_electron']['Q']['score'] is None and v2['companies']['tokyo_electron']['G']['score'] is None
        assert v1['companies']['hanmi']['state'] == 'NOT_AVAILABLE' and v1['companies']['hanmi']['Q']['score'] is None
        assert v2['companies']['hanmi']['state'] == 'LIVE' and v2['reference_sources']['hanmi']['reference_only'] is True
        # The synthetic v1 Q axis computes under half of its weight: NA with coverage BLOCKED, never 0.
        assert all(v1['companies'][c]['Q'] == {'score': None, 'coverage': 'BLOCKED', 'missing_factor_count': 4}
                   for c in fl.IDS if v1['companies'][c]['state'] == 'LIVE')


# ---- 4. no prices or personal values in any public output or log ----
def _keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _keys(item)


def test_public_output_and_logs_hold_no_price_or_personal_value(chain):
    from tests.dart_fake_opendart import FAKE_KEY
    _, runs = chain
    # 987654321 / StockPrice: a synthetic price planted in every fake companyfacts body; it must never come out.
    canaries = (UA, FAKE_KEY, '987654321', 'StockPrice')
    for day, (out, log) in runs.items():
        assert [status for _, status in log['guard']] == ['PASS'] * 6
        for path in out.iterdir():
            if path.is_file():
                text = path.read_bytes().decode('utf-8', errors='replace')
                assert not any(c in text for c in canaries), (day, path.name)
        assert not any(c in log['printed'] for c in canaries)
        ledger = ledger_of(out)
        keys = {k.lower() for k in _keys(ledger)}
        words = ('price', 'close', 'return', 'holding', 'quantity', 'market')
        assert {k for k in keys if any(w in k for w in words)} == {'price_free'}
        assert ledger['price_free'] is True and ledger['holdout'] == 'UNCONFIRMED_NOT_USED'


# ---- 5. determinism: the same synthetic inputs give the same bytes ----
def test_the_whole_chain_is_byte_deterministic(chain, tmp_path):
    _, first = chain
    _, second = rehearse(tmp_path / 'b')
    for day in DAYS:
        a, b = first[day][0], second[day][0]
        names = sorted(p.name for p in a.iterdir() if p.is_file())
        assert names == sorted(p.name for p in b.iterdir() if p.is_file())
        differ = [n for n in names if (a / n).read_bytes() != (b / n).read_bytes()]
        # Only the offline build's NOT_AVAILABLE placeholders differ, by their build wall-clock `as_of` (the real run
        # replaces them in steps that do not feed the ledger). The ledger and every ledger input are byte-identical.
        assert set(differ) <= OFFLINE_PLACEHOLDERS, (day, differ)
        for name in differ:
            x, y = json.loads((a / name).read_text()), json.loads((b / name).read_text())
            x.pop('as_of'), y.pop('as_of')
            assert x == y, (day, name)
        for name in (fl.FILENAME, *fl.SOURCES, *fl.V2_SOURCES, 'dart-financials.json'):
            assert (a / name).read_bytes() == (b / name).read_bytes(), (day, name)
        assert first[day][1]['printed'] == second[day][1]['printed']


# ---- 6. the device side reads the v2 rows (Set A starts on the first prepared v2 day) ----
@pytest.mark.skipif(shutil.which('node') is None, reason='Node runtime required')
def test_device_reader_and_runner_take_the_rehearsed_ledger(chain):
    _, runs = chain
    body = (runs['2026-10-20'][0] / fl.FILENAME).read_text()
    assets = ROOT / 'src/investment_system/product/web_assets'
    # Ready day: the runner's rule (virtual-trading-runner.js assemble): first v2 RECORDED row with a numeric Q and G.
    script = ("const f=require(process.argv[1]),r=require(process.argv[2]);const p=JSON.parse(require('fs').readFileSync(0,'utf8'));"
              "f.validate(p);const s=r.snapshotsFromLedger(p),v2=p.versions['forward_validation/v2'];"
              "const ready=v2.find(x=>x.state==='RECORDED'&&Object.values(x.companies||{}).some(c=>typeof c.Q.score==='number'&&typeof c.G.score==='number'));"
              "console.log(JSON.stringify({dates:Object.keys(s),ready:ready?ready.date:null,basis:p.schema_version}));")
    done = subprocess.run(['node', '-e', script, str(assets / 'forward-validation.js'), str(assets / 'virtual-trading-runner.js')],
                          input=body, text=True, capture_output=True)
    assert done.returncode == 0, done.stderr[-400:]
    assert json.loads(done.stdout) == {'dates': ['2026-10-19', '2026-10-20'], 'ready': '2026-10-19', 'basis': 2}




# ---- 7. failure modes that leave a gap: never filled later ----
def test_first_run_on_the_session_day_upgrades_schema_one_and_a_withheld_deploy_leaves_a_gap(tmp_path):
    seed = schema_one_ledger(clock('2026-10-13', 9, 50))
    _, runs = rehearse(tmp_path / 'c', plan=[
        # No successful run between 10/13 and 10/19: 10/19 reads the schema-1 copy itself. Every Universe SEC request
        # is refused; the staged TARGET rows and the previously published peers still give v2 Q/G. Then the day's
        # verify fails (PR #240 split): collect and ledger finish, the deploy is withheld.
        ('2026-10-19', {'universe_fails': True, 'deploy': False}),
        ('2026-10-20', {}),
    ])
    mon, tue = runs['2026-10-19'][0], runs['2026-10-20'][0]
    printed = runs['2026-10-19'][1]['printed']
    assert runs['2026-10-19'][1]['previous_ledger'] == seed
    assert 'SEC_UNIVERSE_SHARES COLLECTION_NOT_RUN' in printed and 'previous_kept' in printed
    assert ledger_of(mon)['schema_version'] == 2
    assert [r['state'] for r in rows(mon, fl.V2_VERSION)] == [r['state'] for r in rows(mon, fl.VERSION)] == ['RECORDED']
    # 10/20 reads the copy still on Pages (10/19 was not deployed): 10/19 stays a public gap, never backfilled.
    assert runs['2026-10-20'][1]['previous_ledger'] == seed
    for version in (fl.VERSION, fl.V2_VERSION):
        assert [r['date'] for r in rows(tue, version)] == ['2026-10-20']
