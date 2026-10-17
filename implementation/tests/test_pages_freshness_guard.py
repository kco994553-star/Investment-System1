"""Pages rollback across the two deploy workflows and the pre-deploy freshness guard (owner queue 2026-10-17 §5).

Synthetic SEC bytes, an in-memory live Pages copy and injected clocks only; no network, credential or price.
The live copy is read through the same previous-copy readers the daily tools use, so the reproduction runs the real
daily collection (`sec_universe_shares.py --live`, `forward_validation_ledger.py`) and the real preserve-only build path
of `cockpit-pages.yml` against it.
"""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import re
import urllib.error

import pytest

from investment_system.universe import sec_qgv2 as qgv2
from investment_system.universe import sec_universe_qg as uqg
from investment_system.universe import sec_universe_shares as us
from investment_system.validation import forward_ledger as fl
from tests.test_sec_universe_shares import UA, client_kwargs, transport_for

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


def guard(folder, site, capsys, environ=None):
    code = GUARD.run(folder, open_response=site, environ=environ or {'GITHUB_RUN_ID': '7', 'GITHUB_RUN_ATTEMPT': '1'})
    return code, capsys.readouterr().out


# ---- reproduction: an artifact built from an older live copy, deployed after a newer daily deploy ----
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
    assert code == 0 and 'PAGES_FRESHNESS_PASS markers=6 newer=4 equal=0 no_live=2 ' in out  # 404 inputs/no session yet
    site.deploy(newer)
    live_before = dict(site.files)
    code, out = guard(artifact, site, capsys)
    assert code == 1 and site.files == live_before
    for name in UNIVERSE:
        assert (f'PAGES_FRESHNESS file={name} marker=acquired_at verdict=OLDER '
                'artifact=2026-10-11T22:30:00Z live=2026-10-13T22:30:00Z\n') in out
    assert (f'PAGES_FRESHNESS file={fl.FILENAME} marker=as_of verdict=OLDER '
            'artifact=2026-10-11T22:30:00Z live=2026-10-13T22:30:00Z\n') in out
    assert 'PAGES_FRESHNESS_REFUSED markers=6 newer=0 equal=0 no_live=2 live_invalid=0 older=4 missing=0\n' in out
    # The same manual build made after the daily deploy carries the live data and is deployable (UI-only change).
    code, out = guard(manual_build(tmp_path / 'manual-2', site, MANUAL_LATE), site, capsys)
    assert code == 0 and 'older=0 missing=0' in out and 'equal=4' in out


def test_older_daily_artifact_after_a_newer_daily_deploy_is_refused(tmp_path, capsys):
    site = Site()
    first = daily(tmp_path / 'day-a', site, DAY_A)
    site.deploy(daily(tmp_path / 'day-b', site, DAY_B))                  # 10/13 run deployed first (both read empty Pages)
    code, out = guard(first, site, capsys)
    assert code == 1 and 'verdict=OLDER' in out and 'PAGES_FRESHNESS_REFUSED' in out


def test_build_time_as_of_is_not_a_freshness_marker(tmp_path, capsys):
    """Daily collect reads the 10/11 copy at 10/13 22:30; a manual build from that same copy is made and deployed at
    10/14 01:00 (its Universe `as_of` is later). The daily artifact still carries newer data and must deploy."""
    site = Site()
    site.deploy(daily(tmp_path / 'day-a', site, DAY_A))
    late = daily(tmp_path / 'day-b', site, DAY_B)
    site.deploy(manual_build(tmp_path / 'manual', site, MANUAL_LATE))
    assert files(site)[us.FILENAME]['as_of'] > files(late)[us.FILENAME]['as_of']
    code, out = guard(late, site, capsys)
    assert code == 0 and 'older=0' in out and 'newer=4' in out


# ---- guard rules on minimal synthetic files ----
def shares(*stamps):
    return {'as_of': '2026-10-20T00:00:00Z', 'records': {f'X:{n}': {'acquired_at': s} for n, s in enumerate(stamps)}}


def ledger(as_of, *days):
    return {'as_of': as_of, 'versions': {fl.VERSION: [{'date': d} for d in days], fl.V2_VERSION: [{'date': d} for d in days]}}


def write(folder, payloads):
    folder.mkdir(exist_ok=True)
    for name, payload in payloads.items():
        (folder / name).write_bytes(payload if isinstance(payload, bytes) else json.dumps(payload).encode())
    return folder


def served(payloads):
    return Site({k: v if isinstance(v, bytes) else json.dumps(v).encode() for k, v in payloads.items()})


@pytest.mark.parametrize('mine, theirs, verdict, code', [
    ('2026-10-15T22:30:00Z', '2026-10-15T22:30:00Z', 'EQUAL', 0),
    ('2026-10-16T22:30:00Z', '2026-10-15T22:30:00Z', 'NEWER', 0),
    ('2026-10-15T22:29:59Z', '2026-10-15T22:30:00Z', 'OLDER', 1),
    ('2026-10-16T00:30:00+02:00', '2026-10-15T22:30:00Z', 'EQUAL', 0),   # offsets are compared as instants
])
def test_row_acquisition_marker_verdicts(tmp_path, capsys, mine, theirs, verdict, code):
    folder = write(tmp_path / 'a', {us.FILENAME: shares(None, '2026-10-01T00:00:00Z', mine)})
    result, out = guard(folder, served({us.FILENAME: shares(theirs, None)}), capsys)
    assert result == code and f'file={us.FILENAME} marker=acquired_at verdict={verdict} ' in out


def test_qgv2_target_rows_and_public_inputs_companies_count(tmp_path, capsys):
    live = {qgv2.FILENAME: {'records': {}, 'target': {'nvda': {'acquired_at': '2026-10-15T11:00:00Z'}}},
            'sec-public-inputs.json': {'companies': [{'acquired_at': '2026-10-15T11:00:00+00:00'}]}}
    older = {qgv2.FILENAME: {'records': {'A:1': {'acquired_at': '2026-10-14T22:00:00Z'}}, 'target': {}},
             'sec-public-inputs.json': {'companies': [{'acquired_at': '2026-10-14T11:00:00+00:00'}]}}
    code, out = guard(write(tmp_path / 'a', older), served(live), capsys)
    assert code == 1 and out.count('verdict=OLDER') == 2
    code, out = guard(write(tmp_path / 'b', live), served(live), capsys)
    assert code == 0 and 'equal=2' in out


def test_ledger_session_marker_refuses_a_ledger_missing_the_latest_session(tmp_path, capsys):
    live = {fl.FILENAME: ledger('2026-10-20T22:30:00+00:00', '2026-10-19', '2026-10-20')}
    mine = {fl.FILENAME: ledger('2026-10-21T00:00:00+00:00', '2026-10-19')}   # newer stamp, one session short
    code, out = guard(write(tmp_path / 'a', mine), served(live), capsys)
    assert code == 1 and (f'file={fl.FILENAME} marker=session verdict=OLDER artifact=2026-10-19 live=2026-10-20\n') in out
    assert f'file={fl.FILENAME} marker=as_of verdict=NEWER ' in out


def test_missing_markers(tmp_path, capsys):
    live = {us.FILENAME: shares('2026-10-15T22:30:00Z')}
    # Live has data and the artifact has no such file, or no stamped row: refused as MISSING.
    code, out = guard(write(tmp_path / 'none', {}), served(live), capsys)
    assert code == 1 and f'file={us.FILENAME} marker=acquired_at verdict=MISSING artifact=NONE live=2026-10-15T22:30:00Z' in out
    code, out = guard(write(tmp_path / 'blank', {us.FILENAME: shares(None)}), served(live), capsys)
    assert code == 1 and 'verdict=MISSING' in out
    code, out = guard(write(tmp_path / 'broken', {us.FILENAME: b'{not json'}), served(live), capsys)
    assert code == 1 and 'verdict=MISSING' in out
    # Live 404, or live without a stamped row: nothing to roll back.
    code, out = guard(write(tmp_path / 'first', {us.FILENAME: shares('2026-10-15T22:30:00Z')}), served({}), capsys)
    assert code == 0 and 'markers=6 newer=0 equal=0 no_live=6 ' in out
    code, out = guard(write(tmp_path / 'empty', {}), served({us.FILENAME: shares(None)}), capsys)
    assert code == 0 and 'no_live=6' in out


@pytest.mark.parametrize('body', [b'{not json', b'[1]', b'{"as_of": NaN}', b'x' * (2 * 1024 * 1024 + 1)])
def test_live_file_served_but_unreadable_is_not_compared(tmp_path, capsys, body):
    folder = write(tmp_path / 'a', {us.FILENAME: shares('2026-10-01T00:00:00Z')})
    code, out = guard(folder, served({us.FILENAME: body}), capsys)
    assert code == 0 and f'file={us.FILENAME} marker=acquired_at verdict=LIVE_INVALID ' in out and 'live_invalid=1' in out


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
    folder = write(tmp_path / 'a', {us.FILENAME: shares('2026-10-30T00:00:00Z')})
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
    assert code == 0 and 'http' not in out and 'github.io' not in out
    assert all(re.fullmatch(r'PAGES_FRESHNESS[A-Z_]* [a-z_]+=\S+( [a-z_]+=\S+)*', line) for line in out.splitlines())


def test_artifact_directory_must_exist(tmp_path, capsys):
    code, out = guard(tmp_path / 'absent', served({}), capsys)
    assert code == 1 and out == 'PAGES_FRESHNESS_CHECK_FAILED deploy=REFUSED\n'


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
