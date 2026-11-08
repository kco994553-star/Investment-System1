"""Deploy-time carry of the verified live macro-evidence.json (owner 2026-11-07 4th, tools/macro_evidence_carry.py).

When only the collect-time read of the live copy failed, the daily step withholds the file; without a carry the deploy
then removes the live good copy (guard MISSING -> WITHHELD, effect=LIVE_GOOD_COPY_REMOVED). The carry step, run on the
deploy artifact before the freshness guard, puts the verified live bytes back byte for byte with a truthful record
(CARRIED_LIVE). Every case runs on a real artifact made by the real daily path (public_screens_pipeline.collect + the
generator), then the real carry, then the real guards (pages_freshness_guard.run unchanged, pages_artifact_guard per file).
Offline: in-memory live sites only.
"""
from __future__ import annotations

from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import urllib.error

import pytest

from tests import test_macro_evidence as tme

el = tme.el
AT = tme.AT
PAGES = 'https://kco994553-star.github.io/Investment-System1/'
CARRY_AT = AT + timedelta(hours=1)
ENV = {'GITHUB_RUN_ID': '9', 'GITHUB_RUN_ATTEMPT': '1'}
LINE = re.compile(r'MACRO_EVIDENCE_CARRY outcome=[A-Z_]+( [a-z_0-9]+=[A-Za-z0-9_:.\-]+)*')


@pytest.fixture(autouse=True)
def _no_retry_wait(monkeypatch):
    import macro_evidence as tool
    monkeypatch.setattr(tool, '_sleep', lambda seconds: None)


def _tools():
    import macro_evidence as tool
    import macro_evidence_carry as carry
    import pages_freshness_guard as fg
    return tool, carry, fg


class Site:
    """The live Pages site by file name (query strings ignored, as a CDN copy): bytes -> 200, an exception -> raised,
    absent -> 404. `deploy` replaces it with an artifact folder, as actions/deploy-pages does."""

    def __init__(self, files=None):
        self.files, self.urls = dict(files or {}), []

    def __call__(self, request, timeout=None):
        url = request.full_url
        self.urls.append(url)
        name = url[len(PAGES):].split('?', 1)[0]
        value = self.files.get(name)
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise urllib.error.HTTPError(url, 404, 'nf', {}, None)

        class Response(io.BytesIO):
            status = 200

            def geturl(self):
                return url

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return Response(value)

    def deploy(self, folder):
        self.files = {p.name: p.read_bytes() for p in Path(folder).iterdir() if p.is_file()}


def _built_record(body):
    payload = json.loads(body)
    return el.encode_status(el.status_record(attempt_at=AT - timedelta(days=1), result='BUILT', stage=None, error_class=None,
                                             published='NEW', data_generated_at=payload['generated_at'],
                                             data_sha256=hashlib.sha256(body).hexdigest(), previous='NO_LIVE'))


def _withheld_artifact(tmp_path, monkeypatch, name='site'):
    """The real daily path when only the collect-time read of the live copy fails (after the retries): file withheld."""
    import macro_evidence as tool
    out = tme._daily_live(tmp_path, monkeypatch, name, tme._Live({tool.SOURCE: urllib.error.URLError('down')}))
    assert not (out / el.FILENAME).exists()
    record = tme._status(out)
    assert (record['published'], record['failure_stage'], record['failure_class'], record['previous']) == \
        ('WITHHELD', 'PREVIOUS', 'OSError', 'UNAVAILABLE')
    return out


def _snapshot(folder):
    return {p.name: p.read_bytes() for p in Path(folder).iterdir()}


def _carry(out, site, capsys):
    _, carry, _ = _tools()
    capsys.readouterr()
    outcome, code = carry.carry(out, open_response=site, environ=ENV, now=lambda: CARRY_AT)
    printed = capsys.readouterr().out
    assert len(printed.splitlines()) == 1 and LINE.fullmatch(printed.strip()), printed
    assert 'http' not in printed and 'github.io' not in printed
    return outcome, code, printed.strip()


def _guard(out, site, capsys):
    _, _, fg = _tools()
    capsys.readouterr()
    code = fg.run(out, open_response=site, environ=ENV)
    printed = capsys.readouterr().out
    line = next((l for l in printed.splitlines() if l.startswith(f'PAGES_FRESHNESS file={el.FILENAME} ')), '')
    return code, printed, line


# ---------------------------------------------------------------- CARRIED

def test_collect_read_failed_deploy_read_ok_carries_the_live_bytes_and_the_guard_passes(tmp_path, monkeypatch, capsys):
    good = tme._good_previous(tmp_path)
    live = el.encode(good)
    site = Site({el.FILENAME: live, el.STATUS_FILENAME: _built_record(live)})
    out = _withheld_artifact(tmp_path, monkeypatch)
    withheld = tme._status(out)
    # without the carry the guard would remove the live good copy (the #513 path: not preservation)
    before = tmp_path / 'no-carry'
    shutil.copytree(out, before)
    code, printed, line = _guard(before, site, capsys)
    assert code == 0 and 'kind=MISSING' in line and 'effect=LIVE_GOOD_COPY_REMOVED' in printed

    outcome, code, printed = _carry(out, site, capsys)
    assert (outcome, code) == ('CARRIED', 0)
    assert printed == ('MACRO_EVIDENCE_CARRY outcome=CARRIED generated_at=%s sha256=%s status=CARRIED_LIVE '
                       'attempt_stage=PREVIOUS attempt_error=OSError attempt_previous=UNAVAILABLE'
                       % (good['generated_at'], hashlib.sha256(live).hexdigest()))
    assert (out / el.FILENAME).read_bytes() == live, 'byte for byte: generated_at and every observation time unchanged'
    record = tme._status(out)
    # the attempt's own failure is kept as it was; the record adds the carried file and the deploy read
    for key in ('attempt_at', 'attempt_result', 'failure_stage', 'failure_class', 'previous'):
        assert record[key] == withheld[key]
    assert record['published'] == 'CARRIED_LIVE' and record['data_generated_at'] == good['generated_at']
    assert record['data_sha256'] == hashlib.sha256(live).hexdigest()
    assert record['carry'] == {'at': el.iso(CARRY_AT), 'basis': 'DEPLOY_LIVE_READ', 'generated_at': good['generated_at'],
                               'sha256': hashlib.sha256(live).hexdigest()}
    # the real guards, unchanged, on the carried artifact
    assert tme._artifact_checks(out, live) == ('EQUAL', 'PASS', {})
    code, printed, line = _guard(out, site, capsys)
    assert code == 0 and 'verdict=PASS kind=EQUAL' in line and 'PUBLICATION_WITHHELD file=macro-evidence.json' not in printed
    assert printed.splitlines()[-1].startswith('PAGES_FRESHNESS_PASS ')
    # the deploy's own read used a per-run query (like the guard), once per file with no retry needed
    import macro_evidence as tool
    assert [u for u in site.urls if 'deploy-carry' in u] == [tool.SOURCE + '?deploy-carry=9-1', tool.STATUS_SOURCE + '?deploy-carry=9-1']

    # next day: the carried copy is the live bytes, read as LOADED, and the new file continues it
    site.deploy(out)
    nxt = tme._daily_live(tmp_path, monkeypatch, 'next', tme._Live({tool.SOURCE: site.files[el.FILENAME],
                                                                    tool.STATUS_SOURCE: site.files[el.STATUS_FILENAME]}))
    new = json.loads((nxt / el.FILENAME).read_bytes())
    assert tme._status(nxt)['previous'] == 'LOADED' and (new['previous'], new['continuity']) == ('LOADED', 'CONTINUOUS')
    assert tool.continues(new, good) and new['collection_started_at'] == good['collection_started_at']
    assert tme._artifact_checks(nxt, live) == ('NEWER', 'PASS', {})
    assert _carry(nxt, site, capsys)[:2] == ('NOT_NEEDED', 0)


def test_carried_live_copy_without_a_live_record_is_carried(tmp_path, monkeypatch, capsys):
    """Deploys before the attempt record existed serve no record: the data copy alone is verified and carried."""
    live = el.encode(tme._good_previous(tmp_path))
    site = Site({el.FILENAME: live})
    out = _withheld_artifact(tmp_path, monkeypatch)
    assert _carry(out, site, capsys)[:2] == ('CARRIED', 0)
    assert (out / el.FILENAME).read_bytes() == live and _guard(out, site, capsys)[0] == 0


# ---------------------------------------------------------------- LIVE_UNREADABLE

@pytest.mark.parametrize('down', [el.FILENAME, el.STATUS_FILENAME])
def test_deploy_read_failing_carries_nothing_and_the_deploy_is_refused(tmp_path, monkeypatch, capsys, down):
    live = el.encode(tme._good_previous(tmp_path))
    files = {el.FILENAME: live, el.STATUS_FILENAME: _built_record(live)}
    files[down] = urllib.error.URLError('down')
    site = Site(files)
    out = _withheld_artifact(tmp_path, monkeypatch)
    before = _snapshot(out)
    outcome, code, printed = _carry(out, site, capsys)
    assert (outcome, code) == ('LIVE_UNREADABLE', 1) and f'file={down} error=OSError carried=NONE deploy=REFUSED' in printed
    assert _snapshot(out) == before, 'nothing carried, nothing changed'
    assert sum(1 for u in site.urls if u.split('?')[0].endswith('/' + down)) == 3, 'the daily retries: three tries'
    if down == el.FILENAME:
        # the freshness guard refuses the whole deploy, as before (a failed read is never taken for absence)
        code, printed, _ = _guard(out, site, capsys)
        assert code == 1 and f'PAGES_FRESHNESS_LIVE_UNREACHABLE file={el.FILENAME} deploy=REFUSED' in printed


def test_a_passing_deploy_read_failure_is_tried_again(tmp_path, monkeypatch, capsys):
    live = el.encode(tme._good_previous(tmp_path))
    base = Site({el.FILENAME: live})
    fails = []

    def flaky(request, timeout=None):
        if el.FILENAME in request.full_url and el.STATUS_FILENAME not in request.full_url and len(fails) < 2:
            fails.append(1)
            raise urllib.error.URLError('down')
        return base(request, timeout)
    out = _withheld_artifact(tmp_path, monkeypatch)
    assert _carry(out, flaky, capsys)[:2] == ('CARRIED', 0) and (out / el.FILENAME).read_bytes() == live


# ---------------------------------------------------------------- LIVE_INVALID

@pytest.mark.parametrize('case', ['corrupt', 'rejected'])
def test_damaged_live_copy_is_never_carried(tmp_path, monkeypatch, capsys, case):
    good = tme._good_previous(tmp_path)
    live = el.encode(good)
    if case == 'corrupt':
        files = {el.FILENAME: live[:-40]}
    else:
        bad = json.loads(live)
        bad['scope']['probability'] = True
        files = {el.FILENAME: json.dumps(bad).encode()}
    site = Site(files)
    out = _withheld_artifact(tmp_path, monkeypatch)
    before = _snapshot(out)
    outcome, code, printed = _carry(out, site, capsys)
    assert (outcome, code) == ('LIVE_INVALID', 0) and 'carried=NONE effect=WITHHELD' in printed
    assert _snapshot(out) == before
    code, printed, line = _guard(out, site, capsys)
    assert code == 0 and 'verdict=WITHHELD' in line         # the existing WITHHELD path, said as it is
    assert 'kind=LIVE_INVALID' in line and 'effect=LIVE_INVALID_COPY_REPLACED' in printed


# ---------------------------------------------------------------- LIVE_RECORD_MISMATCH (Codex #437 6716049571)

@pytest.mark.parametrize('case,error', [('record_mismatch', 'STATUS_MISMATCH'), ('record_withheld', 'STATUS_WITHHELD'),
                                        ('record_damaged', 'JSONDecodeError')])
def test_good_live_body_with_an_inconsistent_live_record_stops_the_deploy_and_keeps_the_site(tmp_path, monkeypatch, capsys,
                                                                                             case, error):
    """A verified good live body served with a live record that does not describe it: the pair is not adopted (the record
    is not rewritten to fit) and the WITHHELD path is not taken (it would remove the good body): exit 1, the deploy stops
    (no guard, no upload, no deploy step runs after a failed step), the live site keeps every byte."""
    good = tme._good_previous(tmp_path)
    live = el.encode(good)
    if case == 'record_mismatch':                       # a live record describing another valid file
        record = _built_record(el.encode(el.build({}, previous=good, previous_state='LOADED', now=AT)))
    elif case == 'record_withheld':                     # a live WITHHELD record beside a live good body
        record = tme._record()
    else:                                               # a damaged live record
        record = _built_record(live)[:-7]
    site = Site({el.FILENAME: live, el.STATUS_FILENAME: record})
    site_before = {k: bytes(v) for k, v in site.files.items()}
    out = _withheld_artifact(tmp_path, monkeypatch)
    before = _snapshot(out)
    outcome, code, printed = _carry(out, site, capsys)
    assert (outcome, code) == ('LIVE_RECORD_MISMATCH', 1), printed
    assert (f'file={el.STATUS_FILENAME} error={error} carried=NONE deploy=REFUSED site=KEPT') in printed
    assert 'attempt_stage=PREVIOUS' in printed, 'this attempt\'s own failure is still reported'
    assert _snapshot(out) == before, 'nothing carried, the artifact record not rewritten'
    assert site.files == site_before, 'the live site keeps every byte (the deploy never runs)'


def test_a_consistent_live_record_still_carries(tmp_path, monkeypatch, capsys):
    """The normal carry is unchanged: a live record that describes the live body (BUILT/NEW) carries, guard EQUAL."""
    live = el.encode(tme._good_previous(tmp_path))
    site = Site({el.FILENAME: live, el.STATUS_FILENAME: _built_record(live)})
    out = _withheld_artifact(tmp_path, monkeypatch)
    assert _carry(out, site, capsys)[:2] == ('CARRIED', 0) and (out / el.FILENAME).read_bytes() == live
    code, printed, line = _guard(out, site, capsys)
    assert code == 0 and 'verdict=PASS kind=EQUAL' in line, printed


# ---------------------------------------------------------------- LIVE_ABSENT

@pytest.mark.parametrize('live,read', [({}, 'NO_LIVE'), ('placeholder', 'EMPTY_LIVE')])
def test_confirmed_live_absence_has_nothing_to_carry(tmp_path, monkeypatch, capsys, live, read):
    files = {el.FILENAME: el.encode(el.empty_payload(AT))} if live == 'placeholder' else {}
    site = Site(files)
    out = _withheld_artifact(tmp_path, monkeypatch)
    before = _snapshot(out)
    outcome, code, printed = _carry(out, site, capsys)
    assert (outcome, code) == ('LIVE_ABSENT', 0) and f'read={read} carried=NONE effect=NOT_PUBLISHED' in printed
    assert _snapshot(out) == before
    code, printed, line = _guard(out, site, capsys)
    assert code == 0 and 'verdict=NO_LIVE kind=NO_GOOD_LIVE' in line


# ---------------------------------------------------------------- NOT_NEEDED / NOT_ELIGIBLE

def test_artifact_with_a_built_or_kept_file_is_not_touched_and_nothing_is_read(tmp_path, monkeypatch, capsys):
    import macro_evidence as tool
    good = tme._good_previous(tmp_path)
    live = el.encode(good)
    site = Site({el.FILENAME: live})
    new = tme._daily_live(tmp_path, monkeypatch, 'new', tme._Live({tool.SOURCE: live}))
    assert tme._status(new)['published'] == 'NEW'
    monkeypatch.setattr(el, 'build', lambda *a, **k: (_ for _ in ()).throw(KeyError('x')))
    kept = tme._daily_live(tmp_path, monkeypatch, 'kept', tme._Live({tool.SOURCE: live}))
    assert tme._status(kept)['published'] == 'PREVIOUS_KEPT'
    for out, published in ((new, 'NEW'), (kept, 'PREVIOUS_KEPT')):
        before = _snapshot(out)
        outcome, code, printed = _carry(out, site, capsys)
        assert (outcome, code) == ('NOT_NEEDED', 0) and f'artifact_published={published}' in printed
        assert _snapshot(out) == before
    assert site.urls == [], 'nothing needed, nothing read'


def test_anything_else_is_left_to_the_guard(tmp_path, capsys):
    live = el.encode(el.empty_payload(AT))
    site = Site({el.FILENAME: el.encode(tme._good_previous(tmp_path))})
    cases = {'PLACEHOLDER': {el.FILENAME: live, el.STATUS_FILENAME: tme._record()},
             'DATA_INVALID': {el.FILENAME: b'{"schema":', el.STATUS_FILENAME: tme._record()},
             'STATUS_ABSENT': {},
             'STATUS_INVALID': {el.STATUS_FILENAME: b'{"schema":"macro-evidence-status/1"}'}}
    for reason, files in cases.items():
        out = tmp_path / reason
        out.mkdir()
        for name, body in files.items():
            (out / name).write_bytes(body)
        outcome, code, printed = _carry(out, site, capsys)
        assert (outcome, code) == ('NOT_ELIGIBLE', 0) and f'artifact={reason}' in printed
        assert _snapshot(out) == files
    assert site.urls == []


def test_a_failed_carry_write_puts_the_artifact_back(tmp_path, monkeypatch, capsys):
    import macro_evidence as tool
    live = el.encode(tme._good_previous(tmp_path))
    site = Site({el.FILENAME: live})
    out = _withheld_artifact(tmp_path, monkeypatch)
    before = _snapshot(out)
    real = tool.write_bytes

    def status_write_fails(directory, body, name=el.FILENAME):
        if name == el.STATUS_FILENAME and b'CARRIED_LIVE' in body:
            raise OSError('disk')
        return real(directory, body, name)
    monkeypatch.setattr(tool, 'write_bytes', status_write_fails)
    outcome, code, printed = _carry(out, site, capsys)
    assert (outcome, code) == ('CARRY_FAILED', 1) and 'restored=YES deploy=REFUSED' in printed
    assert _snapshot(out) == before


# ---------------------------------------------------------------- the CARRIED_LIVE record (Python and the screen mirror)

def _carried_record(tmp_path):
    body = el.encode(tme._good_previous(tmp_path))
    generated = json.loads(body)['generated_at']
    withheld = el.status_record(attempt_at=AT, result='FAILED', stage='PREVIOUS', error_class='OSError', published='WITHHELD',
                                data_generated_at=None, data_sha256=None, previous='UNAVAILABLE')
    return el.carried_status(withheld, carried_at=CARRY_AT, generated_at=generated, sha256=hashlib.sha256(body).hexdigest())


def _broken(record):
    out = [{k: v for k, v in record.items() if k != 'carry'}]                          # CARRIED_LIVE without its block
    out.append(dict(record, published='PREVIOUS_KEPT'))                                 # a carry block on another value
    out.append(dict(record, carry=dict(record['carry'], sha256='0' * 64)))              # block not describing the file
    out.append(dict(record, carry=dict(record['carry'], generated_at='2020-01-01T00:00:00Z')))
    out.append(dict(record, carry=dict(record['carry'], basis='GUESS')))
    out.append(dict(record, carry=dict(record['carry'], at=el.iso(AT - timedelta(days=2)))))   # read before the attempt
    out.append(dict(record, carry=dict(record['carry'], extra=1)))
    out.append(dict(record, attempt_result='BUILT', failure_stage=None, failure_class=None))
    out.append(dict(record, failure_stage='BUILD'))                                     # an unreadable read stops at PREVIOUS
    out.append(dict(record, data_sha256=None, carry=dict(record['carry'], sha256=None)))
    return out


def test_carried_status_rules(tmp_path):
    record = _carried_record(tmp_path)
    assert el.require_status(json.loads(el.encode_status(record))) == record
    for bad in _broken(record):
        with pytest.raises(ValueError):
            el.require_status(bad)
    with pytest.raises(ValueError):                    # only a WITHHELD attempt can be carried
        el.carried_status(dict(record, published='NEW'), carried_at=CARRY_AT, generated_at=record['data_generated_at'],
                          sha256=record['data_sha256'])
    import pages_artifact_guard as guard
    from collections import Counter
    violations = Counter()
    guard._check_payload(el.STATUS_FILENAME, el.encode_status(record), violations)
    assert not violations


def test_screen_mirror_accepts_the_carried_record_and_refuses_broken_ones(tmp_path):
    node = shutil.which('node')
    if node is None:
        pytest.skip('node not installed')
    source = (tme.ROOT / 'src/investment_system/product/web_app/screen-macro-live.js').read_text(encoding='utf-8')
    start = source.index("const MES='macro-evidence-status.json'")
    end = source.index('return p;}catch(_){return null;}}', start) + len('return p;}catch(_){return null;}}')
    record = _carried_record(tmp_path)
    cases = [record, *_broken(record)]
    script = source[start:end] + '\nconst cases=' + json.dumps(cases) + ';\nprocess.stdout.write(JSON.stringify(cases.map(c=>mesValid(c)!==null)));\n'
    result = subprocess.run([node, '-e', script], capture_output=True, text=True, timeout=60, check=True)
    assert json.loads(result.stdout) == [True] + [False] * (len(cases) - 1)
    # the Python records the mirror already accepted still pass
    for ok in (json.loads(tme._record()), dict(record, published='WITHHELD', data_generated_at=None, data_sha256=None)):
        ok.pop('carry', None)
        script = source[start:end] + '\nprocess.stdout.write(String(mesValid(' + json.dumps(ok) + ')!==null));\n'
        assert subprocess.run([node, '-e', script], capture_output=True, text=True, timeout=60, check=True).stdout == 'true'


def test_declared_outcomes_are_exactly_the_outcomes_carry_returns():
    """OUTCOMES is the public list of carry() results (Codex #437: LIVE_RECORD_MISMATCH was returned but undeclared)."""
    import ast
    _, carry, _ = _tools()
    tree = ast.parse(Path(carry.__file__).read_text(encoding='utf-8'))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'carry')
    returned = {node.value.elts[0].value for node in ast.walk(function)
                if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple)}
    assert len(carry.OUTCOMES) == len(set(carry.OUTCOMES))
    assert set(carry.OUTCOMES) == returned
