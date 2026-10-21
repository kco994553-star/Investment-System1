"""Manual UI deploy (cockpit-pages.yml workflow_dispatch): the preserve step re-publishes the live Pages data unchanged.

Nothing is collected in that path, so every preserved file must keep the bytes of the live copy: the file-level
`as_of`, the states and the classification sources are never restated at the deploy time (a screen reads `as_of` as
the basis time and judges STALE from it). Offline only: the live site is an injected `open_response`.
"""
from datetime import timedelta
import importlib
import json
from pathlib import Path
import sys
import urllib.error

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from investment_system.product import news_signals as ns
from investment_system.product import sec_disclosures as sd
from investment_system.product.public_classification import FILENAME as CLASSIFICATION, unavailable_classification
from investment_system.universe import sec_qgv2 as qgv2
from investment_system.universe import sec_universe_qg as uqg
from investment_system.universe import sec_universe_shares as us
from tests import test_news_signals as news_fixture
from tests import test_sec_disclosures as disclosures_fixture
from tests import test_sec_qgv2 as qgv2_fixture
from tests import test_sec_universe_qg as qg_fixture
from tests import test_sec_universe_shares as shares_fixture

BASE = 'https://kco994553-star.github.io/Investment-System1/'
LATER = timedelta(days=5)   # a manual deploy long after the scheduled publication: restating would age every state


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


def site(files, requests=None):
    """Live Pages copies by file name; missing name -> 404; an exception instance is raised."""
    def open_(request, **_):
        name = request.full_url[len(BASE):]
        if requests is not None:
            requests.append(name)
        value = files.get(name)
        if value is None:
            raise urllib.error.HTTPError(request.full_url, 404, '', {}, None)
        if isinstance(value, Exception):
            raise value
        return Response(request.full_url, value)
    return open_


def tool(name):
    return importlib.import_module(name)


# ---------------- company-classification.json ----------------

def live_classification():
    payload = json.loads((ROOT / 'tests/fixtures/company_classification_v0_payloads.json').read_text())['live']
    assert payload['state'] == 'LIVE' and payload['sources']
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()


def built(tmp_path):
    """The build's offline NOT_AVAILABLE file, as build_pages_cockpit.py writes it."""
    tool('public_classification_pipeline').emit(tmp_path)
    return (tmp_path / CLASSIFICATION).read_bytes()


def test_classification_preserve_restores_the_live_copy_byte_for_byte(tmp_path):
    offline = built(tmp_path)
    assert json.loads(offline)['state'] == 'NOT_AVAILABLE' and json.loads(offline)['sources'] == []
    body = live_classification()
    requests = []
    code = tool('public_classification_pipeline').preserve(tmp_path, open_response=site({CLASSIFICATION: body}, requests))
    assert code == 'PUBLIC_CLASSIFICATION PREVIOUS_RESTORED' and requests == [CLASSIFICATION]
    assert (tmp_path / CLASSIFICATION).read_bytes() == body
    assert sorted(p.name for p in tmp_path.iterdir()) == [CLASSIFICATION]     # no temporary file left


def test_classification_preserve_404_keeps_the_build_not_available_file(tmp_path):
    offline = built(tmp_path)
    code = tool('public_classification_pipeline').preserve(tmp_path, open_response=site({}))
    assert code == 'PUBLIC_CLASSIFICATION PREVIOUS_NOT_AVAILABLE'
    assert (tmp_path / CLASSIFICATION).read_bytes() == offline


@pytest.mark.parametrize('live', [
    b'{"price":1}',                                                     # served but invalid
    b'not json',
    json.dumps({**unavailable_classification(), 'extra': 1}).encode(),  # strict validator: unknown key
    urllib.error.URLError('down'),                                      # unreachable
    urllib.error.HTTPError(BASE + CLASSIFICATION, 500, '', {}, None),
])
def test_classification_preserve_fails_closed_and_writes_nothing(tmp_path, live):
    offline = built(tmp_path)
    with pytest.raises(ValueError):
        tool('public_classification_pipeline').preserve(tmp_path, open_response=site({CLASSIFICATION: live}))
    assert (tmp_path / CLASSIFICATION).read_bytes() == offline
    assert sorted(p.name for p in tmp_path.iterdir()) == [CLASSIFICATION]


def test_classification_preserve_refuses_a_redirected_copy(tmp_path):
    offline = built(tmp_path)
    redirected = lambda request, **_: Response('https://example.invalid/' + CLASSIFICATION, live_classification())
    with pytest.raises(ValueError):
        tool('public_classification_pipeline').preserve(tmp_path, open_response=redirected)
    assert (tmp_path / CLASSIFICATION).read_bytes() == offline


def test_classification_cli_preserve_only_codes(tmp_path, capsys, monkeypatch):
    t = tool('public_classification_pipeline')
    assert t.main(['--out', str(tmp_path), '--preserve-only', '--live']) == 2
    assert capsys.readouterr().out == 'PUBLIC_CLASSIFICATION_ARGUMENTS_INVALID\n'

    def broken(directory, **_):
        raise ValueError('PUBLIC_SCREENS_RESTORE_FAILED')
    monkeypatch.setattr(t, 'preserve', broken)
    assert t.main(['--out', str(tmp_path), '--preserve-only']) == 1
    assert capsys.readouterr().out == 'PUBLIC_CLASSIFICATION PREVIOUS_RESTORE_FAILED\n'
    monkeypatch.setattr(t, 'preserve', lambda directory, **_: 'PUBLIC_CLASSIFICATION PREVIOUS_RESTORED')
    assert t.main(['--out', str(tmp_path), '--preserve-only']) == 0
    assert capsys.readouterr().out == 'PUBLIC_CLASSIFICATION PREVIOUS_RESTORED\n'


# ---------------- Universe files: sec-universe-shares.json, sec-universe-qg.json, sec-qgv2.json ----------------

def universe_site():
    return {us.FILENAME: us.encode(shares_fixture.merged({'NASDAQ:ADBE': shares_fixture.record()})),
            uqg.FILENAME: uqg.encode(qg_fixture.merged({'NASDAQ:NVDA': qg_fixture.row()})),
            qgv2.FILENAME: qgv2.encode(qgv2_fixture.payload())}


def test_universe_preserve_only_keeps_live_bytes_and_as_of(tmp_path, capsys):
    live = universe_site()
    when = shares_fixture.NOW + LATER
    assert tool('sec_universe_shares').run(tmp_path, live=False, preserve_only=True, now=lambda: when, open_previous=site(live)) == 0
    out = capsys.readouterr().out
    assert all(f'{code} PREVIOUS_RESTORED' in out for code in ('SEC_UNIVERSE_SHARES', 'SEC_UNIVERSE_QG', 'SEC_QGV2'))
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(live)
    for name, body in live.items():
        assert (tmp_path / name).read_bytes() == body, name                 # as_of, last_shard_index, states unchanged


def test_universe_daily_restore_path_is_unchanged(tmp_path, capsys):
    """Without --preserve-only (the daily run) the previous copy is still merged at the run time before collection."""
    live = universe_site()
    when = shares_fixture.NOW + LATER
    assert tool('sec_universe_shares').run(tmp_path, live=False, now=lambda: when, open_previous=site(live)) == 1
    assert 'SEC_UNIVERSE_SHARES LIVE_OPT_IN_REQUIRED' in capsys.readouterr().out
    for name in live:
        assert json.loads((tmp_path / name).read_bytes())['as_of'] != json.loads(live[name])['as_of'], name


def test_universe_preserve_only_upgrades_a_legacy_shares_copy_without_a_new_as_of(tmp_path):
    legacy = shares_fixture.merged({'NASDAQ:ADBE': shares_fixture.record()})
    del legacy['unlisted_classes']
    files = {us.FILENAME: json.dumps(legacy).encode()}
    assert tool('sec_universe_shares').run(tmp_path, live=False, preserve_only=True, now=lambda: shares_fixture.NOW + LATER,
                                           open_previous=site(files)) == 0
    restored = us.require_universe_shares(json.loads((tmp_path / us.FILENAME).read_bytes()))
    assert restored['as_of'] == legacy['as_of'] and restored['records'] == legacy['records']
    assert restored['unlisted_classes']['alphabet']['reason_codes'] == ['NOT_COLLECTED']


# ---------------- news-signals.json and sec-disclosures.json ----------------

def test_news_preserve_only_keeps_live_bytes_and_as_of(tmp_path, capsys):
    body = ns.encode(news_fixture.payload()[0])
    assert tool('news_signals').run(tmp_path, live=False, preserve_only=True, now=lambda: news_fixture.NOW + LATER,
                                    open_previous=site({ns.FILENAME: body})) == 0
    out = capsys.readouterr().out
    assert (tmp_path / ns.FILENAME).read_bytes() == body
    assert f"PREVIOUS_RESTORED items={len(json.loads(body)['items'])} state={json.loads(body)['state']}" in out
    # The old restatement at the deploy time would have changed the published bytes (as_of and aged states).
    assert ns.encode(ns.merge(json.loads(body), {}, as_of=news_fixture.NOW + LATER)) != body


def test_disclosures_preserve_only_keeps_live_bytes_and_as_of(tmp_path, capsys):
    body = sd.encode(disclosures_fixture.payload_nvda())
    assert tool('sec_disclosures').run(tmp_path, live=False, preserve_only=True, environ={},
                                       now=lambda: disclosures_fixture.NOW + LATER,
                                       open_previous=site({sd.FILENAME: body})) == 0
    out = capsys.readouterr().out
    assert (tmp_path / sd.FILENAME).read_bytes() == body
    assert f"PREVIOUS_RESTORED events={len(json.loads(body)['events'])} state={json.loads(body)['state']}" in out
    assert sd.encode(sd.merge(json.loads(body), {}, as_of=disclosures_fixture.NOW + LATER)) != body


@pytest.mark.parametrize('name,filename', [('news_signals', ns.FILENAME), ('sec_disclosures', sd.FILENAME)])
def test_preserve_only_invalid_or_missing_live_copy_writes_nothing(tmp_path, capsys, name, filename):
    extra = {'environ': {}} if name == 'sec_disclosures' else {}
    for files, text in (({}, 'PREVIOUS_NOT_AVAILABLE'), ({filename: b'{"price":1}'}, 'PREVIOUS_DISCARDED')):
        assert tool(name).run(tmp_path, live=False, preserve_only=True, open_previous=site(files), **extra) == 0
        assert text in capsys.readouterr().out and not (tmp_path / filename).exists()


# ---------------- workflow wiring ----------------

def test_manual_preserve_step_runs_the_classification_preserve_and_the_daily_run_never_preserves():
    pages = (ROOT.parent / '.github/workflows/cockpit-pages.yml').read_text()
    daily = (ROOT.parent / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    line = 'python implementation/tools/public_classification_pipeline.py --preserve-only --out "$RUNNER_TEMP/public-cockpit"'
    start = pages.index('- name: Preserve previously published validated SEC observations for UI deployment')
    end = pages.index('- uses:', start)
    step = pages[start:end]
    assert "if: github.event_name == 'workflow_dispatch'" in step and pages.count(line) == 1 and line in step
    assert step.index('preserve_public_screens.py') < step.index(line) < step.index('pages_artifact_guard.py')
    assert 'public_classification_pipeline.py --live' not in pages
    # The daily workflow collects (--live) and never passes --preserve-only, so the verbatim restore is manual-only.
    assert '--preserve-only' not in daily and 'public_classification_pipeline.py --live' in daily
    assert 'forward_validation_ledger.py --preserve-only' in step
