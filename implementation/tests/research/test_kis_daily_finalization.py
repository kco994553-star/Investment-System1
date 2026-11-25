from datetime import datetime
import hashlib
import json

import pytest

from investment_system.research import kis_request_builder as builder
from investment_system.research import monthly_price_store as monthly
from investment_system.research.kis_price_bridge import latest_finalized_session


@pytest.mark.parametrize(('clock', 'expected'), [
    ('2026-11-25T03:29:59Z', '2026-11-23'),
    ('2026-11-25T03:30:00Z', '2026-11-24'),
    ('2026-11-25T10:40:00Z', '2026-11-24'),
    ('2026-11-27T03:30:00Z', '2026-11-25'),  # holiday
    ('2026-11-28T03:29:59Z', '2026-11-25'),  # early close
    ('2026-11-28T03:30:00Z', '2026-11-27'),
    ('2026-03-09T04:05:00Z', '2026-03-06'),  # spring transition weekend
    ('2026-03-10T03:30:00Z', '2026-03-09'),
    ('2026-11-02T04:05:00Z', '2026-10-30'),  # fall transition weekend
])
def test_cutoff(clock, expected):
    assert latest_finalized_session(datetime.fromisoformat(clock)).isoformat() == expected


def page(root, dates, *, clock='2026-11-25T04:05:00Z', received='2026-11-25T10:40:00Z', close='10'):
    rows = [dict(xymd=d, open='10', high='12', low='9', clos=close, tvol='7', tamt='70') for d in dates]
    body = json.dumps(dict(rt_cd='0', output1=dict(rsym='DNASSYN'), output2=rows)).encode()
    query = dict(SYMB='SYN', EXCD='NAS', MODP='0', GUBN='0', BYMD='')
    receipt = json.dumps(dict(bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), http_status=200,
                              fetched_at=received, request=query)).encode()
    return builder.ingest_page(root, body, receipt, hashlib.sha256(receipt).hexdigest(),
                               dict(currency='USD', currency_reference='SYNTHETIC_NOT_A_COMPANY'), daily_as_of=clock)


def test_mixed_page_replay_and_overlap(tmp_path):
    dates = ['20261125', '20261124', '20261123']
    result = page(tmp_path, dates)
    assert result['new_rows'] == 2 and result['target_present']
    assert result['deferred_reasons'] == {'SESSION_OPEN_OR_PENDING': 1}
    manifest = monthly.load_manifest(tmp_path, result['series_id'])
    assert [row['date'] for row in monthly.retained_contract(tmp_path, manifest)['bars']] == ['2026-11-23', '2026-11-24']
    second = page(tmp_path, dates)
    assert second['appended_bytes'] == 0 and second['unchanged_rows'] == 2
    with pytest.raises(ValueError, match='ROW_REVISION_REVIEW_REQUIRED'):
        page(tmp_path, dates, received='2026-11-25T10:41:00Z', close='11')
    assert monthly.load_manifest(tmp_path, result['series_id']) == manifest


def test_deferred_only_and_crossing_cutoff(tmp_path):
    for received, reason in [('2026-11-25T03:29:59Z', 'AWAITING_FINALIZATION'),
                             ('2026-11-25T03:30:01Z', 'AFTER_RUN_CUTOFF')]:
        result = page(tmp_path, ['20261124'], clock='2026-11-25T03:29:59Z', received=received)
        assert result['deferred_only'] and result['new_rows'] == 0
        assert result['deferred_reasons'] == {reason: 1}
        assert not (tmp_path/'series').exists()


@pytest.mark.parametrize('dates', [['20261126'], ['20261125', '20261125']])
def test_corrupt_dates_still_fail(tmp_path, dates):
    with pytest.raises(ValueError, match='DUPLICATE_OR_FUTURE_SESSION'):
        page(tmp_path, dates)


def test_receipt_cannot_predate_run(tmp_path):
    with pytest.raises(ValueError, match='INVALID_DAILY_FINALIZATION_CONTEXT'):
        page(tmp_path, ['20261123'], received='2026-11-24T10:40:00Z')


def test_filtered_page_appends_to_legacy_journal_and_restores(tmp_path):
    from investment_system.research import kis_stock_journal as journal
    from investment_system.research.kis_rebuild import load_request
    from test_kis_rebuild import inputs

    request, initial = inputs(tmp_path)
    baseline = json.loads(request.read_bytes())
    request.rename(tmp_path/'baseline.json')
    code = next(iter(json.loads((tmp_path/'symbols.json').read_bytes())))
    initial_patch = journal.changes({code: initial}, {}, baseline, None)
    files, old_head = journal.archive_files(baseline, initial_patch, None)

    def stage(files):
        for path, data in files.items():
            dest = tmp_path/path
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                assert dest.read_bytes() == data
            else:
                dest.write_bytes(data)

    stage(files)
    page(tmp_path/'store', ['20261125', '20261124'])
    frozen = builder.freeze(tmp_path, store_path='store', evaluation_day='2026-11-24',
                            calculated_at='2026-11-25T10:41:00Z', financial=baseline['financial'],
                            symbols=baseline['symbols'], expected_series=1)
    _, config, contracts = load_request(request, frozen['request_sha256'])
    _, previous = journal.replay(tmp_path, old_head)
    updates = journal.changes(contracts, previous, config, None)
    assert len(updates[code]['rows']) == 1
    files, head = journal.archive_files(config, updates, old_head)
    stage(files)
    assert journal.main(['restore', '--source-root', str(tmp_path), '--head', head['path'],
                         '--head-sha256', head['sha256'], '--check-only']) == 0
    _, restored = journal.replay(tmp_path, head)
    assert max(restored[code]['rows']) == '2026-11-24'
