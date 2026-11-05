"""Collection regressions: synthetic metadata/transports, no supplier requests."""
from datetime import datetime, timedelta, timezone
import copy
import json

import pytest

from investment_system.product import news_signals as ns
from investment_system.providers import news_feeds as nf

NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
URL = 'https://news.example.com/nvidia-results'


def collected(title, when=NOW):
    return {'GDELT': {'nvda': {'acquired_at': when, 'rows': [
        {'title': title, 'link': URL, 'published_at': NOW - timedelta(hours=1)}]}}}


def test_same_link_changed_title_replaces_previous_metadata():
    old = ns.merge(None, collected('Nvidia reports quarterly results'), as_of=NOW)
    counts = {}
    revised = ns.merge(old, collected('Nvidia corrects quarterly results', NOW + timedelta(hours=1)),
                       as_of=NOW + timedelta(hours=1), counts=counts)
    assert revised['items'][0]['title'] == 'Nvidia corrects quarterly results'
    assert counts['revisions'] == 1
    assert revised['refresh']['sources']['GDELT']['new_items'] == 0
    assert old['items'][0]['title'] == 'Nvidia reports quarterly results'


def test_provider_pause_survives_client_recreation_and_is_host_scoped():
    state = {}
    url = nf.gdelt_url('nvda')
    def limited(url, **kwargs):
        return nf.NewsResponse(429, b'', url, '3600')
    first = nf.PacedClient(min_interval=5.5, budget=40, state=state, transport=limited,
                           now=lambda: NOW, sleep=lambda _: None)
    with pytest.raises(nf.NewsFetchError, match='HTTP_429'):
        first.get(url, accept='application/json')
    assert first.used == 1
    copied = json.loads(json.dumps(state))
    def never(url, **kwargs):
        pytest.fail('A paused provider must not be requested')
    later = nf.PacedClient(min_interval=5.5, budget=40, state=copied, transport=never,
                           now=lambda: NOW + timedelta(minutes=1))
    with pytest.raises(nf.NewsFetchError, match='SOURCE_PAUSED'):
        later.get(nf.gdelt_url('amd'), accept='application/json')
    assert later.used == 0
    ir = nf.PacedClient(min_interval=1, budget=20, state=copied,
        transport=lambda u, **kw: nf.NewsResponse(200, b'<rss><channel/></rss>', u), now=lambda: NOW)
    assert ir.get(ns.IR_FEEDS['nvda']['url'], accept='application/xml')[0].startswith(b'<rss>')


def test_local_ledger_links_duplicates_tracks_revisions_and_keeps_failure_cursor():
    from investment_system.providers.news_update import UpdateLedger, news_rows
    ledger = UpdateLedger()
    raw = collected('Nvidia reports quarterly results')['GDELT']['nvda']['rows']
    rows = news_rows('GDELT', 'nvda', raw, acquired_at=NOW)
    assert rows[0]['published_at'] is None  # GDELT seen time is not publisher time.
    assert rows[0]['source_seen_at'] == '2026-11-04T11:00:00+00:00'
    first = ledger.apply('GDELT', 'nvda', rows, acquired_at=NOW, attempted_at=NOW)
    assert first['changes'] == {'new': 1, 'duplicate': 0, 'revision': 0}
    duplicate = ledger.apply('GDELT', 'nvda', rows, acquired_at=NOW, attempted_at=NOW + timedelta(hours=1), cached=True)
    assert duplicate['result'] == 'CACHED'
    assert duplicate['last_success_at'] == NOW.isoformat()
    changed = copy.deepcopy(rows)
    changed[0]['title'] = 'Nvidia corrects quarterly results'
    revised = ledger.apply('GDELT', 'nvda', changed, acquired_at=NOW + timedelta(hours=2), attempted_at=NOW + timedelta(hours=2))
    assert revised['changes']['revision'] == 1
    item = next(iter(ledger.state['items'].values()))
    assert item['revision'] == 2 and item['first_acquired_at'] == NOW.isoformat()
    assert item['previous_version_id'] is not None
    before = copy.deepcopy(ledger.state)
    failed = ledger.apply('GDELT', 'nvda', [], acquired_at=None, attempted_at=NOW + timedelta(hours=3), failure='HTTP_429')
    assert failed['last_success_at'] == (NOW + timedelta(hours=2)).isoformat()
    assert failed['cursor'] == before['sources']['GDELT:nvda']['cursor']
    assert ledger.state['items'] == before['items']
    cached_after_failure = ledger.apply('GDELT', 'nvda', [], acquired_at=NOW + timedelta(hours=2),
        attempted_at=NOW + timedelta(hours=3), cached=True)
    assert cached_after_failure['last_failure_code'] == 'HTTP_429'
    other = news_rows('GDELT', 'nvda', [{'title': 'Nvidia corrects quarterly results',
        'link': 'https://wire.example.com/copy', 'published_at': NOW}], acquired_at=NOW + timedelta(hours=4))
    repeat = ledger.apply('GDELT', 'nvda', other, acquired_at=NOW + timedelta(hours=4), attempted_at=NOW + timedelta(hours=4))
    assert repeat['changes']['duplicate'] == 1
    assert ledger.state['items'][other[0]['item_id']]['related_item_id'] == rows[0]['item_id']


def test_cache_retains_original_acquisition_and_late_arrival_not_lost_by_cursor():
    from investment_system.providers.news_update import UpdateLedger, news_rows
    ledger = UpdateLedger()
    rows = news_rows('GDELT', 'nvda', collected('Nvidia results')['GDELT']['nvda']['rows'], acquired_at=NOW)
    ledger.apply('GDELT', 'nvda', rows, acquired_at=NOW, attempted_at=NOW)
    cache = ledger.cached('GDELT', 'nvda', now=NOW + timedelta(minutes=5), ttl_seconds=3600)
    assert cache['acquired_at'] == NOW.isoformat()
    assert ledger.cached('GDELT', 'nvda', now=NOW + timedelta(hours=2), ttl_seconds=3600) is None
    late = [{'title': 'Nvidia launches chip', 'link': 'https://news.example.com/late',
             'published_at': NOW - timedelta(days=2)}]
    result = ledger.apply('GDELT', 'nvda', news_rows('GDELT', 'nvda', late, acquired_at=NOW),
                          acquired_at=NOW, attempted_at=NOW)
    assert result['changes']['new'] == 1
    assert len(ledger.state['items']) == 2


def test_older_snapshot_never_reverts_a_revision_or_advances_success():
    from investment_system.providers.news_update import UpdateLedger, news_rows
    ledger = UpdateLedger()
    original = news_rows('GDELT', 'nvda', collected('Nvidia results')['GDELT']['nvda']['rows'], acquired_at=NOW)
    updated = copy.deepcopy(original)
    updated[0]['title'] = 'Nvidia corrected results'
    ledger.apply('GDELT', 'nvda', updated, acquired_at=NOW + timedelta(hours=1), attempted_at=NOW + timedelta(hours=1))
    result = ledger.apply('GDELT', 'nvda', original, acquired_at=NOW, attempted_at=NOW + timedelta(hours=2))
    assert result['result'] == 'OLDER_INPUT'
    assert next(iter(ledger.state['items'].values()))['title'] == 'Nvidia corrected results'


def test_distinct_issuer_same_news_url_is_not_discarded():
    from investment_system.providers.news_update import UpdateLedger, news_rows
    ledger = UpdateLedger()
    raw = [{'title': 'Nvidia and Microsoft announce partnership', 'link': URL, 'published_at': NOW}]
    for company in ('nvda', 'msft'):
        ledger.apply('GDELT', company, news_rows('GDELT', company, raw, acquired_at=NOW), acquired_at=NOW, attempted_at=NOW)
    assert len(ledger.state['items']) == 2
    assert {x['issuer_id'] for x in ledger.state['items'].values()} == {'SEC:0001045810', 'SEC:0000789019'}


def test_replay_cli_normalizes_raw_sec_and_reports_partial_failure(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[1]
    source = {'cik': '1045810', 'filings': {'recent': {
        'form': ['8-K'], 'accessionNumber': ['0001045810-26-000001'], 'filingDate': ['2026-11-03'],
        'reportDate': ['2026-11-02'], 'acceptanceDateTime': ['2026-11-03T20:00:00Z'], 'items': ['2.02,9.01']}}}
    (tmp_path / 'sec.json').write_text(json.dumps(source))
    (tmp_path / 'bad.json').write_text('{')
    manifest = {'inputs': [
        {'kind': 'SEC_SUBMISSIONS', 'company_id': 'nvda', 'path': 'sec.json', 'acquired_at': NOW.isoformat()},
        {'kind': 'GDELT_JSON', 'company_id': 'amd', 'path': 'bad.json', 'acquired_at': NOW.isoformat()}]}
    (tmp_path / 'inputs.json').write_text(json.dumps(manifest))
    cmd = [sys.executable, str(root / 'tools/news_collection_replay.py'), '--inputs', str(tmp_path / 'inputs.json'),
           '--out', str(tmp_path / 'out'), '--as-of', NOW.isoformat()]
    result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ)
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / 'out/report.json').read_text())
    assert report['result'] == 'PARTIAL_FAILED' and report['items'] == 1
    state = json.loads((tmp_path / 'out/state.json').read_text())
    item = next(iter(state['items'].values()))
    assert item['filing_id'] == '0001045810-26-000001'
    assert item['accepted_at'] == '2026-11-03T20:00:00+00:00' and item['published_at'] is None
    assert item['acquired_at'] == NOW.isoformat()
    assert state['sources']['GDELT:amd']['last_success_at'] is None
    # Idempotent resume through the same CLI: no second new filing.
    second = subprocess.run(cmd + ['--state', str(tmp_path / 'out/state.json')], capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    report = json.loads((tmp_path / 'out/report.json').read_text())
    assert report['changes'] == {'new': 0, 'duplicate': 1, 'revision': 0}


def test_extreme_retry_after_and_corrupt_pause_state_do_not_bypass_cooldown():
    state = {}
    client = nf.PacedClient(min_interval=5.5, budget=40, state=state,
        transport=lambda u, **kw: nf.NewsResponse(429, b'', u, '9' * 60), now=lambda: NOW)
    with pytest.raises(nf.NewsFetchError, match='HTTP_429'):
        client.get(nf.gdelt_url('nvda'), accept='application/json')
    assert client.used == 1
    state['api.gdeltproject.org'] = 'invalid'
    with pytest.raises(nf.NewsFetchError, match='CONFIG_INVALID'):
        client.get(nf.gdelt_url('amd'), accept='application/json')
    assert client.used == 1


def test_older_public_news_snapshot_cannot_overwrite_latest_source():
    old = ns.merge(None, collected('Nvidia results corrected', NOW + timedelta(hours=1)), as_of=NOW + timedelta(hours=1))
    updated = ns.merge(old, collected('Nvidia results preliminary'), as_of=NOW + timedelta(hours=2))
    assert updated['items'][0]['title'] == 'Nvidia results corrected'
    assert updated['sources']['GDELT']['nvda']['acquired_at'] == (NOW + timedelta(hours=1)).isoformat()
    assert updated['sources']['GDELT']['nvda']['last_result'] == 'NOT_RUN'
    assert updated['sources']['GDELT']['nvda']['last_result_code'] == 'OLDER_INPUT'


def test_invalid_batch_and_cached_flag_cannot_create_false_success():
    from investment_system.providers.news_update import UpdateLedger, news_rows
    ledger = UpdateLedger()
    with pytest.raises(ValueError, match='NEWS_CACHE_MISSING'):
        ledger.apply('IR', 'nvda', [], acquired_at=NOW, attempted_at=NOW, cached=True)
    rows = news_rows('GDELT', 'nvda', collected('Nvidia results')['GDELT']['nvda']['rows'], acquired_at=NOW)
    rows.append(dict(rows[0], company_id='msft'))
    with pytest.raises(ValueError, match='NEWS_ISSUER_MISMATCH'):
        ledger.apply('GDELT', 'nvda', rows, acquired_at=NOW, attempted_at=NOW)
    assert ledger.state['sources'] == {} and ledger.state['items'] == {}


def test_partial_source_replay_survives_invalid_reference_and_preserves_dart_date_precision(tmp_path):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
    from news_collection_replay import replay
    from investment_system.providers.news_update import dart_rows
    # An unreadable optional SEC reference must not block a valid independent news source.
    (tmp_path / 'bad-sec.json').write_text('{')
    (tmp_path / 'news.json').write_text(json.dumps({'articles': [
        {'title': 'Nvidia results', 'url': URL, 'seendate': '20261104T110000Z'}]}))
    (tmp_path / 'inputs.json').write_text(json.dumps({'inputs': [
        {'kind': 'SEC_PUBLIC', 'path': 'bad-sec.json'},
        {'kind': 'GDELT_JSON', 'company_id': 'nvda', 'path': 'news.json', 'acquired_at': NOW.isoformat()}]}))
    report = replay(tmp_path / 'inputs.json', out=tmp_path / 'out', as_of=NOW)
    assert report['result'] == 'PARTIAL_FAILED' and report['items_by_source'] == {'GDELT': 1}
    data = {'companies': {'hanmi': {'corp_code': '00161383'}}, 'events': [{
        'source': 'DART', 'company_id': 'hanmi', 'title': '공시', 'link': 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261104000001',
        'classification': 'OTHER', 'filing_date': '2026-11-04', 'accepted_at': None, 'time_precision': 'DATE_KST',
        'rcept_no': '20261104000001'}]}
    row = dart_rows(data, 'hanmi')[0]
    assert row['issuer_id'] == 'DART:00161383' and row['accepted_at'] is None
    assert row['published_at'] is None and row['time_precision'] == 'DATE_KST'


def test_different_filing_receipts_with_generic_equal_titles_are_new_filings():
    from investment_system.providers.news_update import UpdateLedger, dart_rows
    ledger = UpdateLedger()
    data = {'companies': {'hanmi': {'corp_code': '00161383'}}, 'events': [
        {'source': 'DART', 'company_id': 'hanmi', 'title': '임원특정증권등소유상황보고서',
         'link': 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=' + receipt,
         'classification': 'OTHER', 'filing_date': '2026-11-04', 'accepted_at': None,
         'time_precision': 'DATE_KST', 'rcept_no': receipt}
        for receipt in ['20261104000001', '20261104000002']]}
    result = ledger.apply('DART', 'hanmi', dart_rows(data, 'hanmi'), acquired_at=NOW, attempted_at=NOW)
    assert result['changes'] == {'new': 2, 'duplicate': 0, 'revision': 0}


def test_dart_date_uses_kst_day_at_utc_boundary_without_inventing_acceptance():
    from investment_system.providers.news_update import UpdateLedger, dart_rows
    acquired = datetime(2026, 11, 4, 23, tzinfo=timezone.utc)  # Nov 5, 08:00 KST
    data = {'companies': {'hanmi': {'corp_code': '00161383'}}, 'events': [{
        'source': 'DART', 'company_id': 'hanmi', 'title': '공시',
        'link': 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261105000001',
        'classification': 'OTHER', 'filing_date': '2026-11-05', 'accepted_at': None,
        'time_precision': 'DATE_KST', 'rcept_no': '20261105000001'}]}
    rows = dart_rows(data, 'hanmi')
    ledger = UpdateLedger()
    result = ledger.apply('DART', 'hanmi', rows, acquired_at=acquired, attempted_at=acquired)
    assert result['changes'] == {'new': 1, 'duplicate': 0, 'revision': 0}
    stored = next(iter(ledger.state['items'].values()))
    assert stored['filing_date'] == '2026-11-05'
    assert stored['accepted_at'] is None and stored['published_at'] is None
    future = copy.deepcopy(rows)
    future[0]['filing_date'] = '2026-11-06'
    with pytest.raises(ValueError, match='NEWS_EVENT_AFTER_ACQUISITION'):
        ledger.apply('DART', 'hanmi', future, acquired_at=acquired, attempted_at=acquired)
    assert ledger.state['items'][rows[0]['item_id']] == stored


def test_same_batch_same_identity_conflicting_titles_keep_first_without_replay_revisions():
    from investment_system.providers.news_update import UpdateLedger, news_rows
    raw = [{'title': title, 'link': URL, 'published_at': NOW - timedelta(hours=1)}
           for title in ('Nvidia preliminary results', 'Nvidia corrected results')]
    rows = news_rows('GDELT', 'nvda', raw, acquired_at=NOW)
    ledger = UpdateLedger()
    initial = ledger.apply('GDELT', 'nvda', rows, acquired_at=NOW, attempted_at=NOW)
    assert initial['changes'] == {'new': 1, 'duplicate': 1, 'revision': 0}
    stored = copy.deepcopy(next(iter(ledger.state['items'].values())))
    assert stored['title'] == 'Nvidia preliminary results' and stored['revision'] == 1
    repeated = ledger.apply('GDELT', 'nvda', rows, acquired_at=NOW, attempted_at=NOW + timedelta(hours=1))
    assert repeated['changes'] == {'new': 0, 'duplicate': 2, 'revision': 0}
    assert ledger.state['items'][rows[0]['item_id']] == stored
