"""Pages rollback across the two deploy workflows and the pre-deploy freshness guard (owner queue 2026-10-17 §5, with the
owner's amendments of 2026-10-17: row-level comparison, ledger record preservation, LIVE_INVALID refused).

Synthetic SEC bytes, an in-memory live Pages copy and injected clocks only; no network, credential or price.
The live copy is read through the same previous-copy readers the daily tools use, so the reproduction runs the real
daily collection (`sec_universe_shares.py --live`, `forward_validation_ledger.py`) and the real preserve-only build path
of `cockpit-pages.yml` against it. Row-level cases use files built by the real producers and validators.
"""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import itertools
import json
from pathlib import Path
import re
import urllib.error

import pytest

from investment_system.markets.us import US_LISTINGS
from investment_system.providers.sec_collection import SecCollectionError
from investment_system.qgv import v2_factors as vf
from investment_system.universe import sec_qgv2 as qgv2
from investment_system.universe import sec_universe_qg as uqg
from investment_system.universe import sec_universe_shares as us
from investment_system.validation import forward_ledger as fl
from tests import test_sec_universe_all_shards as all_shards
from tests.test_sec_universe_shares import UA, accn, client_kwargs, cover, facts, submissions, transport_for

ROOT = Path(__file__).resolve().parents[1]
PAGES = 'https://kco994553-star.github.io/Investment-System1/'
UTC = timezone.utc
# Synthetic shard days (tests/test_sec_universe_shares.py ISSUERS): BRK-B on 10/11, ADBE and MMM on 10/13.
DAY_A = datetime(2026, 10, 11, 22, 30, tzinfo=UTC)
MANUAL = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
DAY_B = datetime(2026, 10, 13, 22, 30, tzinfo=UTC)
MANUAL_LATE = datetime(2026, 10, 14, 1, 0, tzinfo=UTC)
UNIVERSE = (us.FILENAME, uqg.FILENAME, qgv2.FILENAME)


def load_tool(name):
    spec = importlib.util.spec_from_file_location('_fresh_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GUARD = load_tool('pages_freshness_guard')
INPUTS = load_tool('public_sec_inputs')
REF = load_tool('sec_qgv2_reference')


class Response:
    def __init__(self, url, body, status=200, final=None):
        self.url, self.body, self.status = final or url, body, status

    def geturl(self):
        return self.url

    def read(self, n=-1):
        return self.body if n < 0 else self.body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class Site:
    """The live Pages copy. `deploy` replaces it with an artifact folder, as actions/deploy-pages does."""

    def __init__(self, files=None):
        self.files = dict(files or {})
        self.urls = []

    def __call__(self, request, **_):
        url = request.full_url
        self.urls.append(url)
        name = url[len(PAGES):].split('?', 1)[0] if url.startswith(PAGES) else None
        if name not in self.files:
            raise urllib.error.HTTPError(url, 404, '', {}, None)
        return Response(url, self.files[name])

    def deploy(self, folder):
        self.files = {p.name: p.read_bytes() for p in Path(folder).iterdir() if p.is_file()}


def daily(out, site, when):
    """The two daily collect steps that merge into the live copy: one SEC shard, then the ledger (before 10/19)."""
    out.mkdir()
    assert load_tool('sec_universe_shares').run(out, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when,
                                                client_kwargs=client_kwargs(transport_for([]), when), open_previous=site) == 0
    assert load_tool('forward_validation_ledger').run(out, environ={}, now=lambda: when, open_previous=site) == 0
    return out


def manual_build(out, site, when):
    """cockpit-pages.yml 'Preserve previously published validated SEC observations' for the same files."""
    out.mkdir()
    assert load_tool('sec_universe_shares').run(out, live=False, preserve_only=True, now=lambda: when, open_previous=site) == 0
    assert load_tool('forward_validation_ledger').run(out, preserve_only=True, environ={}, open_previous=site) == 0
    return out


def files(site_or_folder):
    if isinstance(site_or_folder, Site):
        return {k: json.loads(v) for k, v in site_or_folder.files.items()}
    return {p.name: json.loads(p.read_bytes()) for p in Path(site_or_folder).iterdir()}


def acquired(payload, code):
    return payload['records'][code]['acquired_at']


FIXED_LINE = re.compile(r'PAGES_FRESHNESS[A-Z_]* [a-z_]+=\S+( [a-z_]+=\S+)*')


def guard(folder, site, capsys, environ=None):
    capsys.readouterr()   # only the guard's own lines below (the producers above print their own reports)
    code = GUARD.run(folder, open_response=site, environ=environ or {'GITHUB_RUN_ID': '7', 'GITHUB_RUN_ATTEMPT': '1'})
    out = capsys.readouterr().out
    # Fixed format only: codes, counts, dates and public row keys; never a URL, value or address.
    assert all(FIXED_LINE.fullmatch(line) for line in out.splitlines()), out
    assert 'http' not in out and 'github.io' not in out and chr(64) not in out
    return code, out


def section_line(out, name, section):
    """The counts of one `PAGES_FRESHNESS file=... section=...` line as a dict."""
    line = next(l for l in out.splitlines() if l.startswith(f'PAGES_FRESHNESS file={name} section={section} '))
    return dict(part.split('=', 1) for part in line.split()[1:])


# ---- (e) reproduction: an artifact built from an older live copy, deployed after a newer daily deploy ----
def test_manual_artifact_built_before_a_newer_daily_deploy_rolls_the_public_data_back(tmp_path, capsys):
    site = Site()
    site.deploy(daily(tmp_path / 'day-a', site, DAY_A))                  # 10/11: BRK-B shard published
    artifact = manual_build(tmp_path / 'manual', site, MANUAL)           # 10/12: cockpit-pages built from that copy
    site.deploy(daily(tmp_path / 'day-b', site, DAY_B))                  # 10/13: ADBE + MMM shard published
    newer = files(site)
    for name in UNIVERSE:
        assert acquired(newer[name], 'NASDAQ:ADBE') == '2026-10-13T22:30:00Z'
        assert acquired(newer[name], 'NYSE:BRK.B') == '2026-10-11T22:30:00Z'
    assert newer[fl.FILENAME]['as_of'] == '2026-10-13T22:30:00+00:00'

    # Without a guard the queued manual deploy simply replaces the newer copy (the Pages group only serialises).
    site.deploy(artifact)
    rolled = files(site)
    for name in UNIVERSE:
        assert acquired(rolled[name], 'NASDAQ:ADBE') is None and rolled[name]['records']['NASDAQ:ADBE']['state'] == 'NOT_AVAILABLE'
        assert acquired(rolled[name], 'NYSE:BRK.B') == '2026-10-11T22:30:00Z'
        # `as_of` alone hides the rollback: the preserve-only build re-stamps it to its own build time.
        assert rolled[name]['as_of'] == '2026-10-12T09:00:00Z'
    assert rolled[us.FILENAME]['records']['NASDAQ:ADBE']['shares'] is None
    assert rolled[fl.FILENAME]['as_of'] == '2026-10-11T22:30:00+00:00'


def test_guard_refuses_that_manual_artifact_and_passes_the_newer_daily_one(tmp_path, capsys):
    site = Site()
    site.deploy(daily(tmp_path / 'day-a', site, DAY_A))
    artifact = manual_build(tmp_path / 'manual', site, MANUAL)
    newer = daily(tmp_path / 'day-b', site, DAY_B)
    code, out = guard(newer, site, capsys)                               # newer daily artifact vs older live -> deploy
    assert code == 0
    for name in UNIVERSE:   # BRK.B kept as published, ADBE and MMM collected for the first time
        assert section_line(out, name, 'records') == {
            'file': name, 'section': 'records', 'verdict': 'PASS', 'compared': '1', 'newer': '0', 'equal': '1', 'older': '0',
            'missing': '0', 'lost_record': '0', 'new_record': '2', 'artifact_latest': '2026-10-13T22:30:00Z',
            'live_latest': '2026-10-11T22:30:00Z'}
    assert f'PAGES_FRESHNESS file={fl.FILENAME} marker=as_of verdict=NEWER ' in out
    assert out.endswith('PAGES_FRESHNESS_PASS checks=10 refused=0 no_live=2 live_invalid=0 rows_compared=3 rows_regressed=0 '
                        'records_compared=0 records_regressed=0\n')   # 404 inputs, no session yet
    site.deploy(newer)
    live_before = dict(site.files)
    code, out = guard(artifact, site, capsys)
    assert code == 1 and site.files == live_before
    for name in UNIVERSE:
        assert section_line(out, name, 'records')['verdict'] == 'REFUSED'
        for code_ in ('NASDAQ:ADBE', 'NYSE:MMM'):
            assert (f'PAGES_FRESHNESS_REGRESSION file={name} section=records code={code_} kind=LOST_RECORD '
                    'artifact=NONE live=2026-10-13T22:30:00Z\n') in out
    assert (f'PAGES_FRESHNESS file={fl.FILENAME} marker=as_of verdict=OLDER '
            'artifact=2026-10-11T22:30:00Z live=2026-10-13T22:30:00Z\n') in out
    assert out.endswith('PAGES_FRESHNESS_REFUSED checks=10 refused=4 no_live=2 live_invalid=0 rows_compared=9 '
                        'rows_regressed=6 records_compared=0 records_regressed=0\n')
    # The same manual build made after the daily deploy carries the live data and is deployable (UI-only change).
    code, out = guard(manual_build(tmp_path / 'manual-2', site, MANUAL_LATE), site, capsys)
    assert code == 0 and 'rows_compared=9 rows_regressed=0 ' in out
    assert all(section_line(out, name, 'records')['equal'] == '3' for name in UNIVERSE)


def test_older_daily_artifact_after_a_newer_daily_deploy_is_refused(tmp_path, capsys):
    site = Site()
    first = daily(tmp_path / 'day-a', site, DAY_A)
    site.deploy(daily(tmp_path / 'day-b', site, DAY_B))                  # 10/13 run deployed first (both read empty Pages)
    code, out = guard(first, site, capsys)
    assert code == 1 and 'kind=LOST_RECORD' in out and 'marker=as_of verdict=OLDER' in out and 'PAGES_FRESHNESS_REFUSED' in out


def test_build_time_as_of_is_not_a_freshness_marker(tmp_path, capsys):
    """Daily collect reads the 10/11 copy at 10/13 22:30; a manual build from that same copy is made and deployed at
    10/14 01:00 (its Universe `as_of` is later). The daily artifact still carries newer data and must deploy."""
    site = Site()
    site.deploy(daily(tmp_path / 'day-a', site, DAY_A))
    late = daily(tmp_path / 'day-b', site, DAY_B)
    site.deploy(manual_build(tmp_path / 'manual', site, MANUAL_LATE))
    assert files(site)[us.FILENAME]['as_of'] > files(late)[us.FILENAME]['as_of']
    code, out = guard(late, site, capsys)
    assert code == 0 and 'rows_regressed=0' in out and 'marker=as_of verdict=NEWER' in out


# ---- row-level rule on files built by the real producers ----
T17 = datetime(2026, 10, 17, 0, 0, tzinfo=UTC)
T16, T15 = T17 - timedelta(days=1), T17 - timedelta(days=2)
AS_OF = T17 + timedelta(hours=1)
ROW_A, ROW_B, ROW_C = 'NASDAQ:ADBE', 'NYSE:BRK.B', 'NYSE:MMM'
ISSUER = {ROW_A: ('0000000001', 'ADBE', 'Nasdaq'), ROW_B: ('0000000002', 'BRK-B', 'NYSE'), ROW_C: ('0000000003', 'MMM', 'NYSE')}
TARGET_A, TARGET_B = 'nvda', 'msft'
TARGET_SEED = {TARGET_A: 40, TARGET_B: 41}
INPUT_A, INPUT_B = 'amd', 'nvda'
_names = itertools.count()


def shares_payload(stamps, as_of=AS_OF):
    """sec-universe-shares.json; `stamps` = {code: acquisition time, or None = not collected}."""
    updates = {}
    for code, when in stamps.items():
        if when is not None:
            cik, ticker, exchange = ISSUER[code]
            updates[code] = us.build_share_record(code=code, cik=cik, companyfacts_body=facts(cik),
                                                  submissions_body=submissions(cik, ticker, exchange), acquired_at=when,
                                                  as_of=when, cover_xml=cover(cik, ticker), cover_accession=accn(cik),
                                                  cover_acquired_at=when)
    return us.merge(None, updates, as_of=as_of, shard_index=0)


def qg_row(code, when, cik=None, companyfacts_body=None):
    cik = cik or ISSUER[code][0]
    return uqg.build_issuer_records(codes=(code,), cik=cik, companyfacts_body=companyfacts_body or facts(cik),
                                    submissions_body=submissions(cik, 'X'), acquired_at=when)


def qg_payload(stamps, as_of=AS_OF):
    updates = {}
    for n, (code, when) in enumerate(stamps.items()):
        if when is not None:
            updates.update(qg_row(code, when, cik=ISSUER[code][0] if code in ISSUER else str(1000 + n).zfill(10)))
    return uqg.merge(None, updates, as_of=as_of, shard_index=0)


def qgv2_rows(code, when, *, no_financials=False):
    cik = ISSUER[code][0]
    body = ((json.dumps({'cik': int(cik), 'facts': {}}).encode(), json.dumps({'cik': int(cik), 'sic': '3674'}).encode())
            if no_financials else REF.synthetic_sec(cik, seed=int(cik)))
    return qgv2.build_issuer_records(codes=(code,), cik=cik, companyfacts_body=body[0], submissions_body=body[1], acquired_at=when)


def qgv2_target(company_id, when):
    body = REF.synthetic_sec(qgv2.target_cik(company_id), seed=TARGET_SEED[company_id])
    return qgv2.build_target_rows([(company_id, body[0], body[1], when)])


def qgv2_payload(stamps=None, target=None, as_of=AS_OF):
    """sec-qgv2.json with Universe rows (`stamps`) and TARGET rows (`target`); None = not collected."""
    updates, rows = {}, {}
    for code, when in (stamps or {}).items():
        if when is not None:
            updates.update(qgv2_rows(code, when))
    for company_id, when in (target or {}).items():
        if when is not None:
            rows.update(qgv2_target(company_id, when))
    return qgv2.merge(None, updates, as_of=as_of, shard_index=0, target_updates=rows)


def reported_sec(company):
    cik = US_LISTINGS[company]['cik']
    fact = {'end': '2025-12-31', 'val': 100, 'accn': '0000000001-26-000001', 'fy': 2025, 'fp': 'FY', 'form': '10-K',
            'filed': '2026-02-01'}
    facts_ = {'cik': int(cik), 'facts': {'dei': {'EntityCommonStockSharesOutstanding': {'units': {'shares': [fact]}}}}}
    subs = {'cik': cik, 'filings': {'recent': {'accessionNumber': ['0000000001-26-000001'], 'form': ['10-K'],
            'filingDate': ['2026-02-01'], 'reportDate': ['2025-12-31'], 'acceptanceDateTime': ['2026-02-01T12:00:00Z']}}}
    return json.dumps(facts_).encode(), json.dumps(subs).encode()


def inputs_payload(tmp_path, stamps):
    """sec-public-inputs.json from the daily collector with a fake SEC client: every company acquired at T17 unless
    `stamps` says otherwise; None = that company's fetch failed in this run (NOT_AVAILABLE row without acquired_at)."""
    class Client:
        def __init__(self, _):
            pass

        def collect(self, company, cik):
            when = stamps.get(company, T17)
            if when is None:
                raise SecCollectionError('SEC_HTTP_503', stage='fetch', http_status=503)
            return (*reported_sec(company), when)
    path = tmp_path / f'inputs-{next(_names)}.json'
    INPUTS.collect_public_inputs(path, environ={'SEC_USER_AGENT': 'synthetic setting'}, client_factory=Client)
    return INPUTS.require_public_inputs(json.loads(path.read_bytes()))


KINDS = ('shares', 'qg', 'qgv2-records', 'qgv2-target', 'inputs')


def section_payload(kind, tmp_path, a, b):
    """(file, section, key A, key B, payload) with row A acquired at `a` and row B at `b` (None: no collection record)."""
    if kind == 'shares':
        return us.FILENAME, 'records', ROW_A, ROW_B, shares_payload({ROW_A: a, ROW_B: b})
    if kind == 'qg':
        return uqg.FILENAME, 'records', ROW_A, ROW_B, qg_payload({ROW_A: a, ROW_B: b})
    if kind == 'qgv2-records':
        return qgv2.FILENAME, 'records', ROW_A, ROW_B, qgv2_payload({ROW_A: a, ROW_B: b})
    if kind == 'qgv2-target':
        return qgv2.FILENAME, 'target', TARGET_A, TARGET_B, qgv2_payload(target={TARGET_A: a, TARGET_B: b})
    return INPUTS.FILENAME, 'companies', INPUT_A, INPUT_B, inputs_payload(tmp_path, {INPUT_A: a, INPUT_B: b})


def compared_rows(kind):
    return len(US_LISTINGS) if kind == 'inputs' else 2


def file_maximum(payload, section):
    """The only quantity f4a9c563 compared for these files: the latest acquired_at over the whole section."""
    rows = payload[section].values() if isinstance(payload[section], dict) else payload[section]
    return max(GUARD._instant(r['acquired_at']) for r in rows if r.get('acquired_at'))


def without_row(payload, section, key):
    out = copy.deepcopy(payload)
    if isinstance(out[section], dict):
        del out[section][key]
    else:
        out[section] = [r for r in out[section] if r['company_id'] != key]
    return out


def write(folder, payloads):
    folder.mkdir(exist_ok=True)
    for name, payload in payloads.items():
        (folder / name).write_bytes(payload if isinstance(payload, bytes) else json.dumps(payload).encode())
    return folder


def served(payloads):
    return Site({k: v if isinstance(v, bytes) else json.dumps(v).encode() for k, v in payloads.items()})


@pytest.mark.parametrize('kind', KINDS)
def test_a_row_older_than_live_is_refused_although_the_file_maximum_is_unchanged(tmp_path, capsys, kind):
    """(a) Row A acquired 10/17 on both sides; row B 10/16 live and 10/15 in the artifact."""
    name, section, _, b, live = section_payload(kind, tmp_path, T17, T16)
    *_, mine = section_payload(kind, tmp_path, T17, T15)
    # f4a9c563 compared only the per-file maximum, equal here (10/17 on both sides): it let this artifact deploy.
    assert file_maximum(mine, section) == file_maximum(live, section) == T17
    code, out = guard(write(tmp_path / 'artifact', {name: mine}), served({name: live}), capsys)
    n = compared_rows(kind)
    assert code == 1
    assert (f'PAGES_FRESHNESS file={name} section={section} verdict=REFUSED compared={n} newer=0 equal={n - 1} older=1 '
            'missing=0 lost_record=0 new_record=0 artifact_latest=2026-10-17T00:00:00Z live_latest=2026-10-17T00:00:00Z\n') in out
    assert (f'PAGES_FRESHNESS_REGRESSION file={name} section={section} code={b} kind=OLDER '
            'artifact=2026-10-15T00:00:00Z live=2026-10-16T00:00:00Z\n') in out
    assert out.count('PAGES_FRESHNESS_REGRESSION ') == 1 and ' rows_regressed=1 ' in out
    # Equal on both rows (the artifact carries the live rows) deploys.
    code, out = guard(write(tmp_path / 'same', {name: live}), served({name: live}), capsys)
    assert code == 0 and f' compared={n} newer=0 equal={n} older=0 ' in out


@pytest.mark.parametrize('loss', ('row_missing', 'acquired_at_null', 'file_missing'))
@pytest.mark.parametrize('kind', KINDS)
def test_a_row_whose_collection_record_disappears_is_refused(tmp_path, capsys, kind, loss):
    """(b) Row B was collected in the live copy (10/16); in the artifact it is missing, or present without acquired_at
    (a valid file where B was not collected this time; for sec-public-inputs.json: today's fetch of B failed)."""
    name, section, a, b, live = section_payload(kind, tmp_path, T17, T16)
    if loss == 'acquired_at_null':
        *_, mine = section_payload(kind, tmp_path, T17, None)
        assert file_maximum(mine, section) == T17                       # f4a9c563 saw no change here either
    else:
        mine = without_row(live, section, b)
    code, out = guard(write(tmp_path / 'artifact', {} if loss == 'file_missing' else {name: mine}), served({name: live}), capsys)
    kind_ = 'LOST_RECORD' if loss == 'acquired_at_null' else 'MISSING'
    assert code == 1 and section_line(out, name, section)['verdict'] == 'REFUSED'
    assert (f'PAGES_FRESHNESS_REGRESSION file={name} section={section} code={b} kind={kind_} artifact=NONE '
            'live=2026-10-16T00:00:00Z\n') in out
    n = compared_rows(kind)
    lost = n if loss == 'file_missing' else 1
    assert section_line(out, name, section)[kind_.lower()] == str(lost) and f' rows_regressed={lost} ' in out


@pytest.mark.parametrize('target_b', (T15, None))
def test_a_target_section_regression_is_refused_while_every_universe_row_is_newer(tmp_path, capsys, target_b):
    """(c) sec-qgv2.json `target` is its own section: newer Universe rows never cover a TARGET row that went back."""
    live = qgv2_payload({ROW_A: T16, ROW_B: T16}, target={TARGET_A: T16, TARGET_B: T16})
    mine = qgv2_payload({ROW_A: T17, ROW_B: T17}, target={TARGET_A: T17, TARGET_B: target_b})
    assert file_maximum(mine, 'target') > file_maximum(live, 'target')   # the per-file maximum moved forward
    code, out = guard(write(tmp_path / 'a', {qgv2.FILENAME: mine}), served({qgv2.FILENAME: live}), capsys)
    assert code == 1
    records, target = section_line(out, qgv2.FILENAME, 'records'), section_line(out, qgv2.FILENAME, 'target')
    assert (records['verdict'], records['compared'], records['newer']) == ('PASS', '2', '2')
    kind = 'OLDER' if target_b else 'LOST_RECORD'
    assert (target['verdict'], target['compared'], target['newer'], target[kind.lower()]) == ('REFUSED', '2', '1', '1')
    assert (f'PAGES_FRESHNESS_REGRESSION file={qgv2.FILENAME} section=target code={TARGET_B} kind={kind} '
            f"artifact={'2026-10-15T00:00:00Z' if target_b else 'NONE'} live=2026-10-16T00:00:00Z\n") in out


def test_rows_turned_na_with_reasons_under_a_new_calc_version_and_a_newer_collection_pass(tmp_path, capsys, monkeypatch):
    """(d) Normal NA transition under approved new calculation rules is not a retreat: the rows were collected again
    (acquired_at present and later) but have no value, carry reason codes and/or another calc_version."""
    old_version = 'qgv2-calc/2026-10-15.1'
    with monkeypatch.context() as patch:   # the live copy was computed under the previous rules
        patch.setattr(vf, 'CALC_VERSION', old_version)
        live = qgv2_payload({ROW_A: T16, ROW_B: T16, ROW_C: T16}, target={TARGET_A: T16, TARGET_B: T16})
    assert live['calc_version'] == old_version and all(r['calc_version'] == old_version for r in live['target'].values()
                                                       if r['acquired_at'])
    # The one-off all-shards publication path (tools/sec_universe_shares.py _refresh_base): each collected code is cleared,
    # then replaced by this run's row under the current rules. A: data again; B: no annual financials now (NA with its
    # reason); C: not collected (kept, still the old version); TARGET nvda refreshed, msft kept.
    updates = {**qgv2_rows(ROW_A, T17), **qgv2_rows(ROW_B, T17, no_financials=True)}
    base = load_tool('sec_universe_shares')._refresh_base(live, updates, lambda: qgv2.empty_record())
    mine = qgv2.merge(base, updates, as_of=AS_OF, shard_index=6, target_updates=qgv2_target(TARGET_A, T17))
    assert mine['calc_version'] == vf.CALC_VERSION != old_version
    assert mine['records'][ROW_A]['calc_version'] == vf.CALC_VERSION and mine['records'][ROW_C]['calc_version'] == old_version
    na = mine['records'][ROW_B]
    assert (na['state'], na['reason_codes'], na['calc_version'], na['metrics']) == ('NOT_AVAILABLE', ['NO_ANNUAL_SEC_FINANCIALS'], None, {})
    assert na['acquired_at'] == '2026-10-17T00:00:00Z' and live['records'][ROW_B]['state'] == 'LIVE'
    # Q·G v1: row A now NOT_AVAILABLE with INVALID_INPUT after a newer collection (unreadable bytes), row B unchanged.
    qg_live = qg_payload({ROW_A: T16, ROW_B: T16})
    qg_mine = uqg.merge(qg_live, qg_row(ROW_A, T17, companyfacts_body=b'{'), as_of=AS_OF, shard_index=6)
    assert qg_mine['records'][ROW_A]['reason_codes'] == ['INVALID_INPUT'] and qg_mine['records'][ROW_A]['acquired_at'] == '2026-10-17T00:00:00Z'
    code, out = guard(write(tmp_path / 'a', {qgv2.FILENAME: mine, uqg.FILENAME: qg_mine}),
                      served({qgv2.FILENAME: live, uqg.FILENAME: qg_live}), capsys)
    assert code == 0 and 'PAGES_FRESHNESS_PASS ' in out and ' rows_regressed=0 ' in out
    for name, section, compared, newer in ((qgv2.FILENAME, 'records', 3, 2), (qgv2.FILENAME, 'target', 2, 1),
                                           (uqg.FILENAME, 'records', 2, 1)):
        line = section_line(out, name, section)
        assert (line['verdict'], line['compared'], line['newer'], line['equal']) == ('PASS', str(compared), str(newer),
                                                                                   str(compared - newer))


def test_regressed_codes_are_listed_up_to_a_fixed_number(tmp_path, capsys):
    codes = us.universe_codes()[:GUARD.MAX_DETAIL + 5]
    live = qg_payload(dict.fromkeys(codes, T16))
    code, out = guard(write(tmp_path / 'a', {uqg.FILENAME: qg_payload(dict.fromkeys(codes, T15))}),
                      served({uqg.FILENAME: live}), capsys)
    assert code == 1 and out.count('PAGES_FRESHNESS_REGRESSION ') == GUARD.MAX_DETAIL
    assert f'PAGES_FRESHNESS_REGRESSION_MORE file={uqg.FILENAME} section=records shown={GUARD.MAX_DETAIL} total={len(codes)}\n' in out
    assert section_line(out, uqg.FILENAME, 'records')['older'] == str(len(codes))


def test_first_publication_and_live_rows_without_collection_records_pass(tmp_path, capsys):
    mine = {us.FILENAME: shares_payload({ROW_A: T17}), INPUTS.FILENAME: inputs_payload(tmp_path, {})}
    code, out = guard(write(tmp_path / 'first', mine), served({}), capsys)       # every live file 404
    assert code == 0 and out.endswith('PAGES_FRESHNESS_PASS checks=10 refused=0 no_live=10 live_invalid=0 rows_compared=0 '
                                      'rows_regressed=0 records_compared=0 records_regressed=0\n')
    assert section_line(out, us.FILENAME, 'records')['new_record'] == '1'
    # A live file whose rows were never collected has nothing to lose, even against an artifact without that file.
    code, out = guard(write(tmp_path / 'empty', {}), served({us.FILENAME: shares_payload({})}), capsys)
    assert code == 0 and section_line(out, us.FILENAME, 'records')['compared'] == '0'


def test_an_unreadable_artifact_file_has_no_rows(tmp_path, capsys):
    live = shares_payload({ROW_A: T16})
    code, out = guard(write(tmp_path / 'broken', {us.FILENAME: b'{not json'}), served({us.FILENAME: live}), capsys)
    assert code == 1 and f'code={ROW_A} kind=MISSING artifact=NONE live=2026-10-16T00:00:00Z\n' in out
    unstamped = copy.deepcopy(live)
    unstamped['records'][ROW_A]['acquired_at'] = '2026-10-17'   # not a date-time with an offset: no record
    code, out = guard(write(tmp_path / 'naive', {us.FILENAME: unstamped}), served({us.FILENAME: live}), capsys)
    assert code == 1 and f'code={ROW_A} kind=LOST_RECORD artifact=NONE ' in out


# ---- ledger: every live record kept unchanged and in order, the artifact only appends ----
BEFORE = datetime(2026, 10, 16, 22, 30, tzinfo=UTC)
MON, TUE, WED, THU = (datetime(2026, 10, d, 22, 30, tzinfo=UTC) for d in (19, 20, 21, 22))
VERSIONS = (fl.VERSION, fl.V2_VERSION)


def ledger_payload(*sessions):
    """A valid ledger with one v1 and one v2 record per session (NOT_AVAILABLE: no inputs in this synthetic run)."""
    led = fl.new_ledger(BEFORE)
    for when in sessions:
        day = fl.completed_session(when)
        led = fl.append(led, fl.build_record(now=when, session=day, qg_body=None, catalog_body=None), when)
        led = fl.append(led, fl.build_v2_record(now=when, session=day, qgv2_body=None, catalog_body=None), when)
    return fl.require_ledger(fl.parse_json(fl.encode(led)))


def ledger_line(out, version):
    return section_line(out, fl.FILENAME, 'versions.' + version)


def test_ledger_identical_or_append_only_passes(tmp_path, capsys):
    live = ledger_payload(MON, TUE, WED)
    code, out = guard(write(tmp_path / 'same', {fl.FILENAME: live}), served({fl.FILENAME: live}), capsys)
    assert code == 0 and ' records_compared=6 records_regressed=0' in out
    for version in VERSIONS:
        assert ledger_line(out, version) == {'file': fl.FILENAME, 'section': 'versions.' + version, 'verdict': 'PASS',
                                             'live_records': '3', 'artifact_records': '3', 'preserved': '3', 'moved': '0',
                                             'changed': '0', 'missing': '0', 'appended': '0'}
    assert ledger_line(out, fl.V_VERSION)['live_records'] == '0'           # the empty V list is checked as well
    code, out = guard(write(tmp_path / 'next', {fl.FILENAME: ledger_payload(MON, TUE, WED, THU)}), served({fl.FILENAME: live}), capsys)
    assert code == 0 and all(ledger_line(out, v)['appended'] == '1' and ledger_line(out, v)['preserved'] == '3' for v in VERSIONS)
    assert f'marker=session verdict=NEWER artifact=2026-10-22 live=2026-10-21\n' in out


@pytest.mark.parametrize('version', VERSIONS)
def test_ledger_middle_record_dropped_with_the_same_last_date_is_refused(tmp_path, capsys, version):
    live = ledger_payload(MON, TUE, WED)
    mine = copy.deepcopy(live)
    del mine['versions'][version][1]
    code, out = guard(write(tmp_path / 'a', {fl.FILENAME: mine}), served({fl.FILENAME: live}), capsys)
    # The markers f4a9c563 compared are unchanged (same as_of, same last session): only the record check sees the loss.
    assert f'marker=as_of verdict=EQUAL ' in out and 'marker=session verdict=EQUAL artifact=2026-10-21 live=2026-10-21\n' in out
    assert code == 1 and ledger_line(out, version) == {
        'file': fl.FILENAME, 'section': 'versions.' + version, 'verdict': 'REFUSED', 'live_records': '3',
        'artifact_records': '2', 'preserved': '1', 'moved': '1', 'changed': '0', 'missing': '1', 'appended': '0'}
    assert f'PAGES_FRESHNESS_REGRESSION file={fl.FILENAME} section=versions.{version} index=1 kind=MISSING date=2026-10-20\n' in out
    assert f'PAGES_FRESHNESS_REGRESSION file={fl.FILENAME} section=versions.{version} index=2 kind=MOVED date=2026-10-21\n' in out
    other = next(v for v in VERSIONS if v != version)
    assert ledger_line(out, other)['verdict'] == 'PASS' and ' records_regressed=2' in out


def changed_reason(p):
    p['versions'][fl.VERSION][0]['reason_codes'] = ['SEC_QG_FACTORS_MISSING']


def changed_v2_created_at(p):
    p['versions'][fl.V2_VERSION][1]['created_at'] = '2026-10-20T22:31:00+00:00'


def reordered(p):
    rows = p['versions'][fl.V2_VERSION]
    rows[0], rows[1] = rows[1], rows[0]


def versions_absent(p):
    del p['versions']


@pytest.mark.parametrize('mutate, version, regressions', [
    (changed_reason, fl.VERSION, [(0, 'CHANGED', '2026-10-19')]),
    (changed_v2_created_at, fl.V2_VERSION, [(1, 'CHANGED', '2026-10-20')]),
    (reordered, fl.V2_VERSION, [(0, 'MOVED', '2026-10-19'), (1, 'MOVED', '2026-10-20')]),
    (versions_absent, fl.VERSION, [(i, 'MISSING', d) for i, d in enumerate(('2026-10-19', '2026-10-20', '2026-10-21'))]),
])
def test_ledger_old_record_changed_or_reordered_is_refused(tmp_path, capsys, mutate, version, regressions):
    live = ledger_payload(MON, TUE, WED)
    mine = copy.deepcopy(live)
    mutate(mine)
    code, out = guard(write(tmp_path / 'a', {fl.FILENAME: mine}), served({fl.FILENAME: live}), capsys)
    assert code == 1 and ledger_line(out, version)['verdict'] == 'REFUSED' and 'marker=as_of verdict=EQUAL ' in out
    for index, kind, day in regressions:
        assert f'section=versions.{version} index={index} kind={kind} date={day}\n' in out
    assert 'reason_codes' not in out and 'created_at' not in out and 'SEC_QG' not in out   # dates only, never content


# ---- live copy states ----
def tampered_shares():
    p = shares_payload({ROW_A: T16})
    p['records'][ROW_A]['shares'] = -1
    return json.dumps(p).encode()


@pytest.mark.parametrize('body', [b'{not json', b'[1]', b'{"as_of": NaN}', b'x' * (2 * 1024 * 1024 + 1), b'{}',
                                  tampered_shares()])
def test_live_copy_served_but_invalid_refuses_the_deploy(tmp_path, capsys, body):
    """(4) HTTP 200 but oversized, not JSON or rejected by the file's strict validator: nothing can be compared."""
    folder = write(tmp_path / 'a', {us.FILENAME: shares_payload({ROW_A: T17})})
    code, out = guard(folder, served({us.FILENAME: body}), capsys)
    assert code == 1 and f'PAGES_FRESHNESS_LIVE_INVALID file={us.FILENAME} deploy=REFUSED\n' in out
    assert f'PAGES_FRESHNESS file={us.FILENAME} ' not in out                   # not compared
    assert out.endswith('PAGES_FRESHNESS_REFUSED checks=9 refused=0 no_live=9 live_invalid=1 rows_compared=0 '
                        'rows_regressed=0 records_compared=0 records_regressed=0\n')


@pytest.mark.parametrize('name', [us.FILENAME, uqg.FILENAME, qgv2.FILENAME, 'sec-public-inputs.json', fl.FILENAME])
def test_every_file_rejected_by_its_strict_validator_is_live_invalid(tmp_path, capsys, name):
    code, out = guard(write(tmp_path / 'a', {}), served({name: b'{"as_of": "2026-10-17T00:00:00Z", "records": {}}'}), capsys)
    assert code == 1 and f'PAGES_FRESHNESS_LIVE_INVALID file={name} deploy=REFUSED\n' in out and ' live_invalid=1 ' in out


def unreachable_url_error(request, **_):
    raise urllib.error.URLError('synthetic')


def unreachable_http_500(request, **_):
    raise urllib.error.HTTPError(request.full_url, 500, '', {}, None)


def unreachable_redirected(request, **_):
    return Response(request.full_url, b'{}', final=PAGES + 'elsewhere.json')


def unreachable_status(request, **_):
    return Response(request.full_url, b'{}', status=203)


@pytest.mark.parametrize('opener', [unreachable_url_error, unreachable_http_500, unreachable_redirected, unreachable_status])
def test_live_unreachable_fails_closed(tmp_path, capsys, opener):
    folder = write(tmp_path / 'a', {us.FILENAME: shares_payload({ROW_A: T17})})
    code, out = guard(folder, opener, capsys)
    assert code == 1 and out == f'PAGES_FRESHNESS_LIVE_UNREACHABLE file={us.FILENAME} deploy=REFUSED\n'


def test_live_reads_use_the_daily_reader_urls_with_a_per_run_query_and_print_no_url(tmp_path, capsys):
    site = served({})
    code, out = guard(write(tmp_path / 'a', {}), site, capsys, environ={'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '2'})
    shares_tool = load_tool('sec_universe_shares')
    ledger_tool = load_tool('forward_validation_ledger')
    inputs_tool = load_tool('preserve_public_sec_inputs')
    sources = [shares_tool.SOURCE, shares_tool.QG_SOURCE, shares_tool.QGV2_SOURCE, inputs_tool.SOURCE, ledger_tool.SOURCE]
    assert site.urls == [s + '?deploy-check=123-2' for s in sources]   # one read per file
    assert code == 0


def test_artifact_directory_must_exist(tmp_path, capsys):
    code, out = guard(tmp_path / 'absent', served({}), capsys)
    assert code == 1 and out == 'PAGES_FRESHNESS_CHECK_FAILED deploy=REFUSED\n'


# ---- (8) the daily merge and the all-shards publication keep the rows of issuers whose collection failed ----
def guard_against(folder, live_folder, capsys):
    site = Site()
    site.deploy(live_folder)
    return guard(folder, site, capsys)


def stamps(folder, name):
    return {code: row['acquired_at'] for code, row in json.loads((folder / name).read_bytes())['records'].items()}


def assert_counts_match_files(out, artifact, live):
    """Each Universe section line agrees with an independent row-by-row count of the two folders."""
    for name in UNIVERSE:
        mine, theirs = stamps(artifact, name), stamps(live, name)
        collected = [c for c, at in theirs.items() if at is not None]
        line = section_line(out, name, 'records')
        assert line['verdict'] == 'PASS' and line['compared'] == str(len(collected))
        assert line['newer'] == str(sum(1 for c in collected if mine[c] > theirs[c]))
        assert line['equal'] == str(sum(1 for c in collected if mine[c] == theirs[c]))
        assert (line['older'], line['missing'], line['lost_record']) == ('0', '0', '0')


def test_daily_shard_with_a_failed_issuer_keeps_its_published_rows_and_deploys(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    first = tmp_path / 'first'
    assert all_shards.run(tool, first, all_shards.Sec(), when=all_shards.WHEN - timedelta(days=1), all_shards=True) == 0
    today = all_shards.WHEN.date().toordinal() % 7
    members = [cik for _, cik, _, _ in all_shards.SPEC if all_shards.shard_of(cik) == today]
    assert len(members) >= 2
    failed = members[0]
    daily_out = tmp_path / 'daily'
    assert all_shards.run(tool, daily_out, all_shards.Sec(fail={failed}), previous=first) == 0
    assert 'SEC_UNIVERSE_FAILURE ' in capsys.readouterr().out
    for name in UNIVERSE:   # the failed issuer's rows are the published ones, with their own acquisition time
        assert stamps(daily_out, name)[all_shards.CODE[failed]] == stamps(first, name)[all_shards.CODE[failed]] is not None
    code, out = guard_against(daily_out, first, capsys)
    assert code == 0 and ' rows_regressed=0 ' in out
    assert_counts_match_files(out, daily_out, first)
    assert section_line(out, qgv2.FILENAME, 'records')['newer'] == str(len(members) - 1)


def test_all_shards_run_with_failed_issuers_and_normal_na_rows_deploys(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    first = tmp_path / 'first'
    assert all_shards.run(tool, first, all_shards.Sec(), when=all_shards.WHEN - timedelta(days=1), all_shards=True) == 0
    bad = all_shards.shard_of(all_shards.SPEC[0][1])
    whole_shard = {cik for _, cik, _, _ in all_shards.SPEC if all_shards.shard_of(cik) == bad}
    one = next(cik for _, cik, _, _ in all_shards.SPEC if all_shards.shard_of(cik) != bad)
    empty = next(cik for _, cik, _, _ in all_shards.SPEC if all_shards.shard_of(cik) != bad and cik != one)
    second = tmp_path / 'second'
    assert all_shards.run(tool, second, all_shards.Sec(fail=whole_shard | {one}, empty={empty}), previous=first,
                          all_shards=True) == 0
    assert 'ALL_SHARDS_PARTIAL' in capsys.readouterr().out
    for cik in whole_shard | {one}:
        for name in UNIVERSE:
            assert stamps(second, name)[all_shards.CODE[cik]] == stamps(first, name)[all_shards.CODE[cik]] is not None
    na = json.loads((second / qgv2.FILENAME).read_bytes())['records'][all_shards.CODE[empty]]
    assert na['state'] == 'NOT_AVAILABLE' and na['reason_codes'] == ['NO_ANNUAL_SEC_FINANCIALS'] and na['calc_version'] is None
    assert na['acquired_at'] > stamps(first, qgv2.FILENAME)[all_shards.CODE[empty]]
    code, out = guard_against(second, first, capsys)
    assert code == 0 and ' rows_regressed=0 ' in out
    assert_counts_match_files(out, second, first)


# ---- both deploy jobs run the check immediately before actions/deploy-pages (plain text; CI has no YAML parser) ----
def deploy_job(workflow):
    text = (ROOT.parent / '.github/workflows' / workflow).read_text()
    return text, text.split('\n  deploy:\n', 1)[1]


@pytest.mark.parametrize('workflow', ['sec-daily-public-inputs.yml', 'cockpit-pages.yml'])
def test_both_deploy_jobs_check_freshness_immediately_before_deploy(workflow):
    text, job = deploy_job(workflow)
    assert '    concurrency:\n      group: checked-cockpit-pages\n      cancel-in-progress: false\n' in job
    assert '    permissions:\n      contents: read\n      pages: write\n      id-token: write\n' in job
    steps = ('\n' + job.split('\n    steps:\n', 1)[1]).split('\n      - ')[1:]
    assert steps[0].startswith('uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4\n') \
        and 'persist-credentials: false' in steps[0]
    assert steps[1].startswith('uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5\n')
    assert steps[2].startswith('name: Download the Pages artifact this job deploys\n')
    assert 'uses: actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093 # v4.3.0' in steps[2]
    assert 'name: github-pages\n' in steps[2] and 'path: ${{ runner.temp }}/pages-artifact' in steps[2]
    check, deploy = steps[-2], steps[-1]
    assert check.startswith('name: Refuse to deploy public data older than the live Pages copy\n')
    assert [line.strip() for line in check.split('run: |\n', 1)[1].strip().splitlines()] == [
        'mkdir "$RUNNER_TEMP/deploy-check"',
        'tar -xf "$RUNNER_TEMP/pages-artifact/artifact.tar" -C "$RUNNER_TEMP/deploy-check"',
        'python implementation/tools/pages_freshness_guard.py --artifact-dir "$RUNNER_TEMP/deploy-check"']
    # The check gates the deploy: no condition, no continue-on-error, no secret, and nothing runs between them.
    assert 'continue-on-error' not in job and '\n        if:' not in job and 'secrets.' not in job
    assert deploy.startswith('name: Deploy checked Pages artifact\n        id: deployment\n'
                             '        uses: actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e # v4')
    assert len(steps) == 5 and text.count('pages_freshness_guard.py') == 1 and text.count('actions/deploy-pages@') == 1
    assert text.rstrip('\n').endswith(deploy.rstrip('\n'))   # the deploy step ends the workflow file
    # The comment states the amended rules, and that a broken live copy is never repaired automatically.
    comment = ' '.join(line.strip().lstrip('# ') for line in steps[2].splitlines() if line.strip().startswith('#'))
    for phrase in ('row by row', 'acquired_at', 'append only', 'PAGES_FRESHNESS_LIVE_INVALID',
                   'separate, evidence-based procedure', 'never automatic', 'fail closed'):
        assert phrase in comment
