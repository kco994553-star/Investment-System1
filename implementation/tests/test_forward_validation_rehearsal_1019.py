"""Offline rehearsal of the 10/19 forward-validation recording (queue 2-2). Synthetic data and fake transports only.

The daily workflow `sec-daily-public-inputs.yml` is replayed step by step for the simulated runs of 2026-10-16 (Fri,
before the start), 2026-10-17 (Sat), 2026-10-19 (Mon, first session) and 2026-10-20 (Tue). Every step uses the repo's
own tool entry points with the fake SEC/DART transports already used in tests; the live Pages copy is emulated by an
in-memory site that each simulated deploy replaces, so each day reads the previous day's ledger through the same
`fetch_previous` path. No network, credential, price, holding or personal value is used.

The collect job's steps are read from the workflow file and run in its order (a failed required step ends the job and
withholds deploy). Steps that do not feed the ledger (classification, domains/logos, 13F, 8-K, news) are offline no-ops
that can be made to fail. The private release is a synthetic in-memory store (W-F2, user decision 2026-10-15).

Checks: rows are appended (v2 default + v1 comparison) only on a completed session on its own date; nothing is
backfilled; NA is never filled with 0; public output carries no price or personal value; the chain is deterministic;
an unrelated step's failure keeps the day's row (W-F1) and a withheld day comes back from the private copy (W-F2).
"""
from datetime import datetime, timedelta, timezone
import contextlib
import hashlib
import io
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path
import sys
import urllib.error

import pytest

from investment_system.validation import forward_ledger as fl
from tests.test_forward_validation_ledger import RawStore

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


# ---- the collect job of sec-daily-public-inputs.yml, read as plain text (CI has no YAML parser) ----
WORKFLOW = ROOT.parent / '.github/workflows/sec-daily-public-inputs.yml'
# Run label first (owner instruction 2026-10-17): one RUN_CONTEXT line, never a gate and never a ledger input.
CONTEXT_TOOLS = ('daily_run_context',)
LEDGER_INPUT_TOOLS = ('build_pages_cockpit', 'public_screens_pipeline', 'dart_daily', 'sec_universe_shares', 'project_dart_qgv2')
# Central QGV publication (GSQ-024, PR-C): after the ledger, before the unrelated steps; both continue on error. Offline here: the
# Secrets are not configured, so the publisher records NOT_RUN in its status file and the history step skips.
CENTRAL_V_TOOLS = ('qgv_official_publish', 'qgv_official_history')
UNRELATED_TOOLS = ('public_classification_pipeline', 'universe_domains_pipeline', 'company_logos_pipeline', 'sec_13f_managers',
                   'sec_disclosures', 'news_signals')
# Counts-only report of the final artifact (owner instruction 2026-10-15): last before the upload, never a gate.
REPORT_TOOLS = ('published_coverage',)
RAW_SETTING = 'synthetic private release setting'


def collect_steps():
    """Steps of the collect job in file order: name, tools run, guard, continue-on-error, `if:` and env (name -> value)."""
    job = WORKFLOW.read_text().split('\n  collect:\n', 1)[1].split('\n  verify:\n', 1)[0]
    steps = []
    for chunk in job.split('\n      - ')[1:]:
        lines = chunk.splitlines()
        name = lines[0].split('name: ', 1)[1] if lines[0].startswith('name: ') else lines[0]
        tools = [t for t in re.findall(r'python implementation/tools/([a-z0-9_]+)\.py', chunk) if t != 'pages_artifact_guard']
        env = dict(re.findall(r'^          ([A-Z_]+): (.+)$', chunk, re.M))
        steps.append({'name': name, 'tools': tools, 'guard': 'pages_artifact_guard.py --artifact-dir' in chunk, 'env': env,
                      'continue': '        continue-on-error: true' in lines, 'if': any(l.startswith('        if:') for l in lines),
                      'upload': 'actions/upload-pages-artifact@' in chunk})
    return steps


class StepFailed(RuntimeError):
    pass


# ---- one simulated daily run: the collect job's steps in workflow order; deploy only after the whole job and verify ----
def daily_run(work, site, day, *, deploy=True, universe_fails=False, fail_tools=(), raw=None):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), pytest.MonkeyPatch.context() as mp:
        # Wall-clock reads (the TARGET step's time stamp and 'not in the future' checks) see the simulated run time.
        import public_sec_inputs
        SimulatedClock.moment = clock(day, 22, 20)
        mp.setattr(public_sec_inputs, 'datetime', SimulatedClock)
        out, log = _daily_run(work, site, day, deploy=deploy, universe_fails=universe_fails, fail_tools=fail_tools, raw=raw)
    log['printed'] = buffer.getvalue()
    return out, log


def _daily_run(work, site, day, *, deploy, universe_fails, fail_tools, raw):
    from tests.dart_fake_opendart import FAKE_KEY
    from tests.test_dart_qgv2_history import SixAnnualDart
    build, guard = load_tool('build_pages_cockpit'), load_tool('pages_artifact_guard')
    pipeline, shares = load_tool('public_screens_pipeline'), load_tool('sec_universe_shares')
    dart, project, ledger = load_tool('dart_daily'), load_tool('project_dart_qgv2'), load_tool('forward_validation_ledger')
    out = work / day
    log = {'previous_ledger': site.files.get(fl.FILENAME), 'guard': [], 'ran': [], 'failed_step': None, 'uploaded': False,
           'ledger_exit': None}

    def screens(env):
        acquired = SimulatedClock.fromtimestamp(clock(day, 22, 19).timestamp(), UTC)
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(pipeline, 'datetime', SimulatedClock)
            result = pipeline.collect(out, environ={'SEC_USER_AGENT': UA}, client_factory=target_client(acquired))
        return 0 if result['failed_companies'] == 0 else 1

    def universe(env):
        when = clock(day, 22, 28)
        return shares.run(out, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when,
                          client_kwargs=universe_kwargs(when, fail=universe_fails), open_previous=site)

    def append(env):
        # The step's literal settings come from the workflow; secrets are synthetic and present only with a raw store.
        environ = {k: v for k, v in env.items() if not v.startswith('${{')}
        if raw is not None and 'RAW_REPO_TOKEN' in env:
            environ['RAW_REPO_TOKEN'] = RAW_SETTING
        log['ledger_exit'] = ledger.run(out, environ=environ, now=lambda: clock(day, 22, 45), open_previous=site,
                                        raw_call=raw, upload_call=raw)
        return log['ledger_exit']

    def unrelated(env):
        return 0  # offline: the placeholders from the build stay; only their failure matters here

    def central_v(env):
        # The step's literal settings come from the workflow; its two Secrets are not configured in the rehearsal (NOT_RUN).
        environ = {k: v.strip("'") for k, v in env.items() if not v.startswith('${{')}
        log['qgv_official'] = load_tool('qgv_official_publish').run(
            out=out, parser='', monthend_stamp=environ['QGV_MONTHEND_STAMP'], monthend_shards=6, previous=None,
            raw_token=None, hmac_key=None, now=clock(day, 22, 50), workdir=work / 'qgv-official-work')
        return 0

    def central_v_history(env):
        environ = {'RAW_REPO_TOKEN': RAW_SETTING} if raw is not None and 'RAW_REPO_TOKEN' in env else {}
        print(load_tool('qgv_official_history').run(out, environ=environ, call=raw))
        return 0

    actions = {
        'daily_run_context': lambda env: load_tool('daily_run_context').run(
            environ={'GITHUB_EVENT_NAME': 'schedule', 'RUN_MODE': 'daily'}, now=lambda: clock(day, 22, 18)),
        'build_pages_cockpit': lambda env: (build.build_public_cockpit(out), 0)[1],
        'public_screens_pipeline': screens,
        'dart_daily': lambda env: dart.run(out, environ={DART_KEY_ENV: FAKE_KEY}, transport=SixAnnualDart(),
                                           now=clock(day, 22, 24), max_calls=30, open_previous=site, include_qgv2=True,
                                           collect_history=True),
        'sec_universe_shares': universe,
        'project_dart_qgv2': lambda env: project.project(out),
        'forward_validation_ledger': append,
        'qgv_official_publish': central_v,
        'qgv_official_history': central_v_history,
        **{tool: unrelated for tool in UNRELATED_TOOLS},
        'published_coverage': lambda env: load_tool('published_coverage').main(['--artifact-dir', str(out)]),
    }
    for step in collect_steps():
        if step['upload']:
            log['uploaded'] = True
            continue
        if not step['tools']:
            continue  # checkout, setup and the offline test gate
        try:
            for tool in step['tools']:
                if tool in fail_tools:
                    raise StepFailed(tool)
                if actions[tool](step['env']) != 0:
                    raise StepFailed(tool)
            if step['guard']:
                receipt = guard.scan_artifact(out)
                log['guard'].append((step['tools'][0], receipt['pages_artifact_guard']))
                assert receipt['pages_artifact_guard'] == 'PASS', (step['name'], receipt.get('violations'))
            log['ran'].append(step['tools'][0])
        except StepFailed:
            if step['continue']:
                continue
            log['failed_step'] = step['tools'][0]
            break  # a failed required step ends the job: no Pages artifact, so verify and deploy do not run
    log['deployed'] = bool(log['uploaded'] and deploy)
    if log['deployed']:
        site.deploy(out)
    return out, log


def ledger_of(folder):
    return fl.require_ledger(fl.parse_json((Path(folder) / fl.FILENAME).read_bytes()))


DAYS = ('2026-10-16', '2026-10-17', '2026-10-19', '2026-10-20')


def rehearse(work, plan=None, raw=None):
    work.mkdir(parents=True)
    site = seeded_site(clock('2026-10-15', 22, 40))
    runs = {}
    for day, options in (plan or [(d, {}) for d in DAYS]):
        runs[day] = daily_run(work, site, day, raw=raw, **options)
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
    every = [t for step in collect_steps() for t in step['tools'][:1]]
    assert all(log['ran'] == every and log['failed_step'] is None and log['deployed'] for _, log in runs.values())
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
    # Central QGV (PR-C): without its two Secrets the V step is NOT_RUN before any download, records the attempt in the
    # guarded status file, ships no publication, and every later step, the upload and the deploy still run.
    for day in DAYS:
        out, log = runs[day]
        summary = log['qgv_official']
        assert (summary['attempt'], summary['reason'], summary['published']) == ('NO_OFFICIAL_YET', 'HMAC_KEY_MISSING', 'NONE')
        assert not (out / 'qgv-official.json').exists() and (out / 'qgv-official-status.json').is_file()
        assert 'QGV_OFFICIAL_HISTORY skipped=NO_PUBLICATION' in log['printed']
    assert 'qgv-official-status.json' in site.files and 'qgv-official.json' not in site.files


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
        assert [status for _, status in log['guard']] == ['PASS'] * sum(step['guard'] for step in collect_steps())
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


# ---- 6. observation basis on 10/19 (owner instruction 2026-10-16) and the device side ----
def test_first_session_v2_row_records_its_observation_basis(chain):
    from investment_system.universe import sec_qgv2 as q
    _, runs = chain
    for day in ('2026-10-19', '2026-10-20'):
        out = runs[day][0]
        used = q.require_qgv2(q.parse_json((out / q.FILENAME).read_bytes()))
        [v2] = [r for r in rows(out, fl.V2_VERSION) if r['date'] == day]
        basis = v2['basis']
        # The basis of the file this run actually read; the input pointer stays in source_sha256 (not repeated).
        assert basis == fl.observation_basis(used, datetime.fromisoformat(day).date())
        assert v2['source_sha256']['sec-qgv2.json'] == hashlib.sha256((out / q.FILENAME).read_bytes()).hexdigest()
        assert basis['population']['n'] == used['cross_section_size'] and basis['acquired'][0] <= basis['acquired'][1]
        # The synthetic Universe is small: recorded as 준비 관측 (not a primary evaluation target), with its reasons.
        assert basis['evaluation']['status'] == 'PREPARATORY' and basis['evaluation']['eligible'] is False
        assert basis['evaluation']['reasons'][:2] == ['Q_BELOW_454', 'G_BELOW_454']
        assert ('CALC_VERSION_MISSING' in basis['evaluation']['reasons']) == (used.get('calc_version') is None)
        assert 'basis' not in rows(out, fl.VERSION)[-1]  # the v1 comparison row is unchanged
    # The 10/19 row (basis included) is carried byte-identically into 10/20.
    assert fl.canonical(rows(runs['2026-10-20'][0], fl.V2_VERSION)[0]) == fl.canonical(rows(runs['2026-10-19'][0], fl.V2_VERSION)[0])


@pytest.mark.skipif(shutil.which('node') is None, reason='Node runtime required')
def test_device_reader_and_runner_take_the_rehearsed_ledger(chain):
    _, runs = chain
    body = (runs['2026-10-20'][0] / fl.FILENAME).read_text()
    assets = ROOT / 'src/investment_system/product/web_assets'
    # Ready day: the runner's rule (virtual-trading-runner.js assemble): first PRIMARY v2 row of the current evaluation
    # segment with a numeric Q and G. The rehearsal rows are PREPARATORY: kept and shown, but not run.
    script = ("const f=require(process.argv[1]),r=require(process.argv[2]);const p=JSON.parse(require('fs').readFileSync(0,'utf8'));"
              "f.validate(p);const s=r.snapshotsFromLedger(p),v2=p.versions['forward_validation/v2'];"
              "const ready=r.evaluationRecords(v2).find(x=>Object.values(x.companies||{}).some(c=>typeof c.Q.score==='number'&&typeof c.G.score==='number'));"
              "console.log(JSON.stringify({dates:Object.keys(s),ready:ready?ready.date:null,basis:p.schema_version,"
              "labels:v2.map(x=>f.rowEvaluation(x).status),segments:f.segments(v2).map(x=>[x.segment,x.preparatory_dates])}));")
    done = subprocess.run(['node', '-e', script, str(assets / 'forward-validation.js'), str(assets / 'virtual-trading-runner.js')],
                          input=body, text=True, capture_output=True)
    assert done.returncode == 0, done.stderr[-400:]
    segment = rows(runs['2026-10-20'][0], fl.V2_VERSION)[0]['basis']['segment']
    assert json.loads(done.stdout) == {'dates': [], 'ready': None, 'basis': 2, 'labels': ['PREPARATORY', 'PREPARATORY'],
                                       'segments': [[segment, ['2026-10-19', '2026-10-20']]]}




# ---- 7. failure modes that leave a gap: never filled later ----
def test_first_run_on_the_session_day_upgrades_schema_one_and_a_withheld_deploy_leaves_a_gap(tmp_path):
    seed = schema_one_ledger(clock('2026-10-13', 9, 50))
    _, runs = rehearse(tmp_path / 'c', plan=[
        # No successful run between 10/13 and 10/19: 10/19 reads the schema-1 copy itself. Every Universe SEC request
        # is refused; the staged TARGET rows and the previously published peers still give v2 Q/G. Then the day's
        # verify fails (PR #240 split): collect and ledger finish, the deploy is withheld. No private copy is configured
        # (no RAW_REPO_TOKEN), so the W-F2 read falls back to Pages.
        ('2026-10-19', {'universe_fails': True, 'deploy': False}),
        ('2026-10-20', {}),
    ])
    mon, tue = runs['2026-10-19'][0], runs['2026-10-20'][0]
    printed = runs['2026-10-19'][1]['printed']
    assert 'FORWARD_LEDGER_PREVIOUS source=PAGES raw=NOT_CONFIGURED' in runs['2026-10-20'][1]['printed']
    assert runs['2026-10-19'][1]['previous_ledger'] == seed
    assert 'SEC_UNIVERSE_SHARES COLLECTION_NOT_RUN' in printed and 'previous_kept' in printed
    assert ledger_of(mon)['schema_version'] == 2
    assert [r['state'] for r in rows(mon, fl.V2_VERSION)] == [r['state'] for r in rows(mon, fl.VERSION)] == ['RECORDED']
    # 10/20 reads the copy still on Pages (10/19 was not deployed): 10/19 stays a public gap, never backfilled.
    assert runs['2026-10-20'][1]['previous_ledger'] == seed
    for version in (fl.VERSION, fl.V2_VERSION):
        assert [r['date'] for r in rows(tue, version)] == ['2026-10-20']


# ---- 8. W-F1: the ledger and its inputs run before the required steps that do not feed it ----
def test_collect_job_runs_ledger_inputs_and_ledger_before_unrelated_required_steps():
    steps = [s for s in collect_steps() if s['tools'] or s['upload']]
    order = [s['tools'][0] if s['tools'] else 'UPLOAD' for s in steps]
    ledger = order.index('forward_validation_ledger')
    # After the run label, exactly the steps whose files the ledger reads (actual-catalog, sec-qg-factors, sec-qgv2,
    # dart-financials) precede it.
    assert order[:ledger] == list(CONTEXT_TOOLS + LEDGER_INPUT_TOOLS)
    after = [t for s in steps[ledger + 1:] for t in s['tools']]
    assert after == list(CENTRAL_V_TOOLS) + list(UNRELATED_TOOLS) + list(REPORT_TOOLS) and order[-1] == 'UPLOAD'
    by_tool = {s['tools'][0]: s for s in steps if s['tools']}
    assert by_tool['published_coverage']['continue'] and not by_tool['published_coverage']['env']
    # Semantics kept: the ledger step is unconditional and required; unrelated steps keep their own required/optional state.
    assert not by_tool['forward_validation_ledger']['continue'] and not by_tool['forward_validation_ledger']['if']
    assert [t for t in ('public_classification_pipeline', 'universe_domains_pipeline', 'sec_13f_managers')
            if by_tool[t]['continue']] == []
    assert by_tool['sec_disclosures']['continue'] and by_tool['news_signals']['continue'] and by_tool['dart_daily']['continue']
    # The private-release setting and its selector live only where they are used; no other step gets them.
    assert by_tool['forward_validation_ledger']['env'] == {'RAW_REPO_TOKEN': '${{ secrets.RAW_REPO_TOKEN }}',
                                                           'FORWARD_LEDGER_PREVIOUS_SOURCE': 'RAW_FIRST'}
    holders = sorted(t for t, s in by_tool.items() if 'RAW_REPO_TOKEN' in s['env'])
    assert holders == ['forward_validation_ledger', 'qgv_official_history', 'sec_universe_shares']
    # Central QGV (PR-C): both steps continue on error; the V step holds its two Secrets and the month-end stamp only, the
    # history step the raw-repo write token only.
    assert by_tool['qgv_official_publish']['continue'] and by_tool['qgv_official_history']['continue']
    assert by_tool['qgv_official_publish']['env'] == {'QGV_OFFICIAL_HMAC_KEY': '${{ secrets.QGV_OFFICIAL_HMAC_KEY }}',
                                                      'RAW_REPO_READ_TOKEN': '${{ secrets.RAW_REPO_READ_TOKEN }}',
                                                      'QGV_MONTHEND_STAMP': "'20261023'"}
    assert by_tool['qgv_official_history']['env'] == {'RAW_REPO_TOKEN': '${{ secrets.RAW_REPO_TOKEN }}'}
    assert by_tool['qgv_official_publish']['guard'] and not by_tool['qgv_official_history']['guard']
    assert all('FORWARD_LEDGER_PREVIOUS_SOURCE' not in s['env'] for t, s in by_tool.items() if t != 'forward_validation_ledger')
    assert all(not s['env'] for t, s in by_tool.items() if t in ('project_dart_qgv2', 'build_pages_cockpit'))
    job = WORKFLOW.read_text().split('\n  collect:\n', 1)[1].split('\n  verify:\n', 1)[0]
    assert 'set -x' not in job and 'echo $' not in job and 'echo "$' not in job


@pytest.mark.parametrize('tool', ['public_classification_pipeline', 'universe_domains_pipeline', 'company_logos_pipeline',
                                  'sec_13f_managers'])
def test_an_unrelated_required_step_failure_keeps_the_days_row_and_its_private_copy(tmp_path, tool):
    raw = RawStore()
    _, runs = rehearse(tmp_path / tool, plan=[('2026-10-19', {'fail_tools': (tool,)})], raw=raw)
    out, log = runs['2026-10-19']
    assert log['failed_step'] in (tool, 'universe_domains_pipeline') and not log['uploaded'] and not log['deployed']
    assert log['ran'][:len(CONTEXT_TOOLS + LEDGER_INPUT_TOOLS) + 1] == [*CONTEXT_TOOLS, *LEDGER_INPUT_TOOLS, 'forward_validation_ledger']
    assert log['ledger_exit'] == 0
    for version in (fl.VERSION, fl.V2_VERSION):
        assert [(r['date'], r['state']) for r in rows(out, version)] == [('2026-10-19', 'RECORDED')]
    assert raw.body('forward-ledger-2026-10-19') == (out / fl.FILENAME).read_bytes()
    assert 'RAW_UPLOADED tag=forward-ledger-2026-10-19' in log['printed']


# ---- 9. W-F2: a withheld day comes back from the private copy the next day ----
@pytest.fixture(scope='module')
def recovered(tmp_path_factory):
    raw = RawStore()
    site, runs = rehearse(tmp_path_factory.mktemp('recovered') / 'r', plan=[
        ('2026-10-16', {}),
        ('2026-10-19', {'fail_tools': ('sec_13f_managers',)}),  # 13F fails after the ledger: no artifact, no deploy
        ('2026-10-20', {}),
    ], raw=raw)
    return site, runs, raw


def test_a_withheld_day_is_recovered_from_the_private_copy_the_next_day(recovered):
    site, runs, raw = recovered
    mon, mon_log = runs['2026-10-19']
    tue, tue_log = runs['2026-10-20']
    pre_start = (runs['2026-10-16'][0] / fl.FILENAME).read_bytes()
    assert not mon_log['deployed'] and tue_log['previous_ledger'] == pre_start  # Pages still serves the 10/16 copy
    assert 'FORWARD_LEDGER_PREVIOUS source=RAW raw=FOUND recovered_records=1' in tue_log['printed']
    for version in (fl.VERSION, fl.V2_VERSION):
        assert [r['date'] for r in rows(tue, version)] == ['2026-10-19', '2026-10-20']
        assert fl.canonical(rows(tue, version)[0]) == fl.canonical(rows(mon, version)[0])  # carried byte-identically
    assert tue_log['deployed'] and site.files[fl.FILENAME] == (tue / fl.FILENAME).read_bytes()
    # Each dated private copy is exactly that day's public-format ledger: nothing beyond what Pages carries next.
    assert raw.body('forward-ledger-2026-10-19') == (mon / fl.FILENAME).read_bytes()
    assert raw.body('forward-ledger-2026-10-20') == (tue / fl.FILENAME).read_bytes()
    assert 'forward-ledger-2026-10-16' not in raw.releases  # nothing recorded or copied before the start
    assert 'FORWARD_LEDGER_PREVIOUS source=PAGES raw=NONE' in runs['2026-10-16'][1]['printed']


def test_without_a_reachable_private_copy_the_pages_copy_is_used_and_the_gap_stays(tmp_path):
    down = RawStore(status=503)
    _, runs = rehearse(tmp_path / 'down', plan=[
        ('2026-10-19', {'fail_tools': ('public_classification_pipeline',)}),
        ('2026-10-20', {}),
    ], raw=down)
    tue, log = runs['2026-10-20']
    assert 'FORWARD_LEDGER_PREVIOUS source=PAGES raw=HTTP_503 recovered_records=0' in log['printed']
    assert log['previous_ledger'] == schema_one_ledger(clock('2026-10-13', 9, 50)) and log['deployed']
    for version in (fl.VERSION, fl.V2_VERSION):
        assert [r['date'] for r in rows(tue, version)] == ['2026-10-20']


def test_the_private_read_leaks_no_setting_price_or_raw_location(recovered):
    from tests.dart_fake_opendart import FAKE_KEY
    _, runs, raw = recovered
    canaries = (RAW_SETTING, UA, FAKE_KEY, '987654321', 'StockPrice', RawStore.SIGNED, 'investment-system1-raw')
    for day, (out, log) in runs.items():
        assert not any(c in log['printed'] for c in canaries), day
        for path in out.iterdir():
            if path.is_file():
                text = path.read_bytes().decode('utf-8', errors='replace')
                assert not any(c in text for c in canaries), (day, path.name)
        keys = {k.lower() for k in _keys(ledger_of(out))}
        assert {k for k in keys if any(w in k for w in ('price', 'close', 'return', 'holding', 'quantity'))} == {'price_free'}
    # The setting is never part of a request line; the signed location is read without it.
    assert all(RAW_SETTING not in url for _, url, _ in raw.calls)
    assert all(not url.startswith('https://api.github.com') for _, url, auth in raw.calls if not auth)
    for line in runs['2026-10-20'][1]['printed'].splitlines():
        if line.startswith('FORWARD_LEDGER_PREVIOUS'):
            assert re.fullmatch(r'FORWARD_LEDGER_PREVIOUS source=[A-Z]+ raw=[A-Z_0-9]+ recovered_records=\d+', line)

