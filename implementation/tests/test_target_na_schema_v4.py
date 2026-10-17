"""sec-public-inputs.json schema /4 (owner decision 2026-10-17, TARGET NA schema supplement items 3 and 4).

A NA produced by a successful collection records that collection's real acquired_at; a failure time (checked_at) or an
identity-conflict detection time (detected_at) is never an acquired_at; an identity conflict withdraws the previous
observation; the pre-deploy freshness guard passes normal NA / withdrawal transitions and still refuses row loss, older
artifacts and timestamp refreshes without a successful collection; a /3 live copy is read during the transition.

Real producer (tools/public_screens_pipeline.py collect), real live readers and the real guard against an in-memory live
Pages copy. Synthetic SEC bytes, fake clients and injected clocks only: no network, credential or price.
"""
import copy
from datetime import datetime, timedelta, timezone
import json
import shutil
import sys

import pytest

from investment_system.markets.us import US_LISTINGS
from investment_system.providers.sec_collection import SecCollectionError
from tests.test_pages_freshness_guard import Site, guard, load_tool, section_line, served, write
from tests.test_public_sec_inputs import raw

PIPE = load_tool('public_screens_pipeline')
INPUTS = load_tool('public_sec_inputs')
ARTIFACT_GUARD = load_tool('pages_artifact_guard')
PRESERVE = load_tool('preserve_public_sec_inputs')
FILE = INPUTS.FILENAME
UTC = timezone.utc
IDS = sorted(US_LISTINGS)
A, B, C, D = IDS[:4]
T1 = datetime(2026, 9, 1, 22, 0, tzinfo=UTC)          # New York 2026-09-01 18:00 (EDT)
DELAY = timedelta(minutes=5)
SCHEDULED = {'SEC_USER_AGENT': 'synthetic setting', 'GITHUB_EVENT_NAME': 'schedule'}
MANUAL = {'SEC_USER_AGENT': 'synthetic setting', 'GITHUB_EVENT_NAME': 'workflow_dispatch'}
HTTP_503 = SecCollectionError('SEC_HTTP_503', stage='fetch', http_status=503)
CIK_MISMATCH = SecCollectionError('SEC_CIK_MISMATCH', stage='parse')


def day_(n):
    return T1 + timedelta(days=n)


def factory(when, failures=None, bodies=None):
    class Client:
        def __init__(self, _agent):
            pass

        def collect(self, company, cik):
            if company in (failures or {}):
                raise failures[company]
            facts, subs = (bodies or {}).get(company) or raw(company)
            return json.dumps(facts).encode(), json.dumps(subs).encode(), when
    return Client


def no_share_concept(company):
    facts, subs = raw(company)
    return dict(facts, facts={'dei': {}}), subs


def run_day(tmp_path, name, site, when, *, failures=None, bodies=None, environ=SCHEDULED, read_live=True):
    """The daily TARGET step (read the live copy, collect) -> (artifact folder with only this file, result, state)."""
    out = tmp_path / name
    out.mkdir()
    previous, state = PIPE.load_previous_inputs(open_response=site) if read_live else (None, 'UNAVAILABLE')
    result = PIPE.collect(out, environ=environ, client_factory=factory(when, failures, bodies), previous=previous,
                          previous_state=state, now=lambda: when + DELAY)
    artifact = tmp_path / (name + '-artifact')
    artifact.mkdir()
    shutil.copyfile(out / FILE, artifact / FILE)
    return artifact, result, state


def rows(folder):
    return {r['company_id']: r for r in payload(folder)['companies']}


def payload(folder):
    return json.loads((folder / FILE).read_bytes())


def first_day(tmp_path, site, **kwargs):
    artifact, result, state = run_day(tmp_path, 'day0', site, day_(0), **kwargs)
    assert state == 'NO_LIVE' and result['failed_companies'] == 0
    site.deploy(artifact)
    return artifact


def as_v3(p):
    """The same observations as the /3 file the producer wrote before this change (LIVE rows unchanged; a /3
    NOT_AVAILABLE row has no record)."""
    old = copy.deepcopy(p)
    old['schema'] = 'public-sec-reported-inputs/3'
    del old['collection']
    for i, row in enumerate(old['companies']):
        row.pop('preserved_previous')
        if row['status'] != 'LIVE':
            old['companies'][i] = {k: row[k] for k in ('company_id', 'cik', 'status', 'reason_codes', 'failure_stage',
                                                       'company_index', 'http_status', 'excluded_fact_counts',
                                                       'share_class_basis', 'share_class_notice')}
            old['companies'][i]['status'] = 'NOT_AVAILABLE'
    return INPUTS.require_public_inputs(old)


def inputs_line(out):
    return section_line(out, FILE, 'companies')


# ---------------------------------------------------------------------------------------------------------------
# 1. A NA of a successful collection carries the real acquired_at and passes; a failure never gets an acquired_at.
# ---------------------------------------------------------------------------------------------------------------
def test_policy_na_of_a_successful_collection_records_the_real_acquired_at_and_passes_the_guard(tmp_path, capsys):
    site = Site()
    first_day(tmp_path, site)
    artifact, result, _ = run_day(tmp_path, 'day1', site, day_(1), bodies={A: no_share_concept(A)})
    row = rows(artifact)[A]
    assert (row['status'], row['reason_codes'], row['failure_stage']) == ('NOT_AVAILABLE', ['SEC_SHARE_CONCEPT_MISSING'], 'normalize')
    assert row['acquired_at'] == day_(1).isoformat()                     # the SEC client's time, not the collector's
    assert row['sources']['companyfacts']['url'].endswith('CIK' + US_LISTINGS[A]['cik'] + '.json')
    assert result['policy_na'] == 1 and result['collected_companies'] == 16
    code, out = guard(artifact, site, capsys)
    line = inputs_line(out)
    assert code == 0 and (line['verdict'], line['newer'], line['lost_record']) == ('PASS', '17', '0')


def test_failure_and_detection_times_are_never_written_as_acquired_at(tmp_path):
    site = Site()
    first_day(tmp_path, site)
    failures = {A: SecCollectionError('SEC_HTTP_404', stage='fetch', http_status=404), B: CIK_MISMATCH}
    artifact, _, _ = run_day(tmp_path, 'day1', site, day_(1), failures=failures)
    a, b = rows(artifact)[A], rows(artifact)[B]
    assert a['status'] == 'COLLECTION_FAILED' and a['checked_at'] == (day_(1) + DELAY).isoformat() and 'acquired_at' not in a
    assert b['status'] == 'WITHDRAWN' and b['detected_at'] == (day_(1) + DELAY).isoformat() and 'acquired_at' not in b
    # The validator refuses any of these times disguised as a successful collection.
    for status, row in (('COLLECTION_FAILED', a), ('WITHDRAWN', b)):
        p = payload(artifact)
        target = next(r for r in p['companies'] if r['company_id'] == row['company_id'])
        target['acquired_at'] = (day_(1) + DELAY).isoformat()
        with pytest.raises(ValueError, match='SEC_PUBLIC_INPUT_INVALID'):
            INPUTS.require_public_inputs(p)
    # A NOT_AVAILABLE row with an acquired_at must be a normalize-stage policy result, never a fetch failure.
    p = payload(artifact)
    p['companies'][0] = dict({k: v for k, v in a.items() if k != 'checked_at'}, status='NOT_AVAILABLE',
                             acquired_at=(day_(1) + DELAY).isoformat(), sources=rows(artifact)[C]['sources'])
    with pytest.raises(ValueError, match='SEC_PUBLIC_INPUT_INVALID'):
        INPUTS.require_public_inputs(p)


# ---------------------------------------------------------------------------------------------------------------
# 2. A transient failure keeps the previous row unchanged: LIVE, NA and WITHDRAWN rows alike.
# ---------------------------------------------------------------------------------------------------------------
def test_fetch_failure_keeps_previous_live_na_and_withdrawn_rows_unchanged(tmp_path, capsys):
    site = Site()
    first_day(tmp_path, site)
    day1, _, _ = run_day(tmp_path, 'day1', site, day_(1), bodies={B: no_share_concept(B)}, failures={C: CIK_MISMATCH})
    site.deploy(day1)
    before = rows(day1)
    artifact, result, _ = run_day(tmp_path, 'day2', site, day_(2), failures={A: HTTP_503, B: HTTP_503, C: HTTP_503})
    after = rows(artifact)
    for company, status in ((A, 'LIVE'), (B, 'NOT_AVAILABLE'), (C, 'WITHDRAWN')):
        kept = {k: v for k, v in after[company].items() if k != 'preserved_previous'}
        assert kept == {k: v for k, v in before[company].items() if k != 'preserved_previous'} and kept['status'] == status
        assert after[company]['preserved_previous'] == {'checked_at': (day_(2) + DELAY).isoformat(),
                                                        'reason_codes': ['SEC_HTTP_503'], 'failure_stage': 'fetch',
                                                        'http_status': 503}
    assert [p['previous'] for p in result['preserved']] == ['LIVE', 'NOT_AVAILABLE', 'WITHDRAWN']
    code, out = guard(artifact, site, capsys)
    line = inputs_line(out)
    assert code == 0 and (line['equal'], line['newer'], line['preserved_mismatch']) == ('3', '14', '0')


# ---------------------------------------------------------------------------------------------------------------
# 3. Identity conflict: WITHDRAWN, the previous value is never used, the guard checks the withdrawal's lineage.
# ---------------------------------------------------------------------------------------------------------------
def test_identity_conflict_withdraws_the_previous_value_and_carries_no_values(tmp_path, capsys):
    site = Site()
    first = first_day(tmp_path, site)
    artifact, result, _ = run_day(tmp_path, 'day1', site, day_(1), failures={A: CIK_MISMATCH})
    row = rows(artifact)[A]
    assert row['withdrawn_acquired_at'] == rows(first)[A]['acquired_at'] == day_(0).isoformat()
    assert not {'acquired_at', 'sources', 'reported_shares', 'filings'} & set(row) and row['excluded_fact_counts'] == {}
    assert result['withdrawn'] == [{'company_index': 1, 'code': 'SEC_CIK_MISMATCH', 'previous': 'LIVE'}]
    code, out = guard(artifact, site, capsys)
    assert code == 0 and inputs_line(out)['withdrawn'] == '1'
    site.deploy(artifact)
    # Next day: the conflict persists -> the same withdrawn observation, detected again (NEWER); never the old values.
    again, _, _ = run_day(tmp_path, 'day2', site, day_(2), failures={A: CIK_MISMATCH})
    assert rows(again)[A]['withdrawn_acquired_at'] == day_(0).isoformat()
    code, out = guard(again, site, capsys)
    assert code == 0 and inputs_line(out)['newer'] == '17'
    # Resolved: a new successful collection after the detection replaces the withdrawal (NEWER).
    resolved, _, _ = run_day(tmp_path, 'day2b', site, day_(2))
    code, out = guard(resolved, site, capsys)
    assert code == 0 and rows(resolved)[A]['status'] == 'LIVE'


def test_an_older_artifact_cannot_bring_a_withdrawn_value_back(tmp_path, capsys):
    """An artifact built before the withdrawal (it still has A's LIVE row from day 0) deployed after it: OLDER."""
    site = Site()
    first = first_day(tmp_path, site)
    withdrawn, _, _ = run_day(tmp_path, 'day1', site, day_(1), failures={A: CIK_MISMATCH})
    site.deploy(withdrawn)
    code, out = guard(first, site, capsys)
    assert code == 1 and f'code={A} kind=OLDER artifact={day_(0):%Y-%m-%dT%H:%M:%SZ} live={day_(1) + DELAY:%Y-%m-%dT%H:%M:%SZ}' in out


@pytest.mark.parametrize('change, kind', [
    (lambda r, live: r.update(withdrawn_acquired_at=None), 'WITHDRAWAL_MISMATCH'),            # names no observation
    (lambda r, live: r.update(withdrawn_acquired_at=(day_(1) - timedelta(hours=1)).isoformat()), 'WITHDRAWAL_MISMATCH'),
    (lambda r, live: r.update(withdrawn_acquired_at=(day_(0) - timedelta(days=3)).isoformat()), 'OLDER'),
    (lambda r, live: r.update(detected_at=(day_(0) - timedelta(hours=1)).isoformat(),
                              withdrawn_acquired_at=(day_(0) - timedelta(hours=2)).isoformat()), 'OLDER'),
])
def test_a_status_alone_never_passes_a_withdrawal(tmp_path, capsys, change, kind):
    """The withdrawal must name exactly the live observation and be detected after it; WITHDRAWN alone is refused."""
    site = Site()
    first_day(tmp_path, site)
    artifact, _, _ = run_day(tmp_path, 'day1', site, day_(1), failures={A: CIK_MISMATCH})
    p = payload(artifact)
    change(p['companies'][0], None)
    INPUTS.require_public_inputs(p)                                   # still a valid file: the guard decides
    code, out = guard(write(tmp_path / 'tampered', {FILE: p}), site, capsys)
    assert code == 1 and f'code={A} kind={kind} ' in out


def test_withdrawal_without_reading_the_live_copy_is_refused(tmp_path, capsys):
    site = Site()
    first_day(tmp_path, site)
    artifact, _, state = run_day(tmp_path, 'day1', site, day_(1), failures={A: CIK_MISMATCH}, read_live=False)
    assert state == 'UNAVAILABLE' and rows(artifact)[A]['withdrawn_acquired_at'] is None
    code, out = guard(artifact, site, capsys)
    assert code == 1 and f'code={A} kind=WITHDRAWAL_MISMATCH ' in out


def test_withdrawn_rows_need_an_identity_code_and_an_unchanged_status_is_not_a_withdrawal(tmp_path, capsys):
    site = Site()
    first_day(tmp_path, site)
    artifact, _, _ = run_day(tmp_path, 'day1', site, day_(1), failures={A: CIK_MISMATCH})
    p = payload(artifact)
    p['companies'][0]['reason_codes'] = ['SEC_HTTP_503']
    with pytest.raises(ValueError, match='SEC_PUBLIC_INPUT_INVALID'):
        INPUTS.require_public_inputs(p)
    code, out = guard(write(tmp_path / 'bad', {FILE: p}), site, capsys)      # not a valid file -> no rows
    assert code == 1 and f'PAGES_FRESHNESS_ARTIFACT_INVALID file={FILE} rows=NONE\n' in out
    assert inputs_line(out)['missing'] == '17'


# ---------------------------------------------------------------------------------------------------------------
# 4. Real row loss, older artifacts and timestamp refreshes without a successful collection stay refused.
# ---------------------------------------------------------------------------------------------------------------
def test_older_artifact_and_row_loss_are_refused(tmp_path, capsys):
    site = Site()
    first = first_day(tmp_path, site)
    newer, _, _ = run_day(tmp_path, 'day1', site, day_(1))
    site.deploy(newer)
    code, out = guard(first, site, capsys)
    assert code == 1 and inputs_line(out)['older'] == '17'
    lost, _, _ = run_day(tmp_path, 'day2', site, day_(2), failures={A: SecCollectionError('SEC_HTTP_404', stage='fetch', http_status=404)})
    code, out = guard(lost, site, capsys)
    assert code == 1 and f'code={A} kind=LOST_RECORD artifact=NONE ' in out


@pytest.mark.parametrize('tamper', ['bump_kept', 'edit_kept', 'edit_collected'])
def test_timestamp_or_value_refresh_without_a_successful_collection_is_refused(tmp_path, capsys, tamper):
    site = Site()
    first_day(tmp_path, site)
    artifact, _, _ = run_day(tmp_path, 'day1', site, day_(1), failures={A: HTTP_503})
    p = payload(artifact)
    kept = p['companies'][0]
    assert kept['preserved_previous'] is not None and kept['acquired_at'] == day_(0).isoformat()
    if tamper == 'bump_kept':          # the kept row re-stamped as if collected today
        kept['acquired_at'] = day_(1).isoformat()
        kind = 'PRESERVED_MISMATCH'
    elif tamper == 'edit_kept':        # same acquired_at, other values
        kept['reported_shares'][0]['val'] = 101
        kind = 'PRESERVED_MISMATCH'
    else:                              # marker unchanged and not kept, but values differ from the live record
        kept['reported_shares'][0]['val'] = 101
        kept['preserved_previous'] = None
        kind = 'CHANGED'
    INPUTS.require_public_inputs(p)
    code, out = guard(write(tmp_path / tamper, {FILE: p}), site, capsys)
    assert code == 1 and f'code={A} kind={kind} ' in out


def test_kept_row_with_a_failure_time_older_than_its_observation_is_invalid(tmp_path):
    site = Site()
    first_day(tmp_path, site)
    artifact, _, _ = run_day(tmp_path, 'day1', site, day_(1), failures={A: HTTP_503})
    for mutate in (lambda k: k['preserved_previous'].update(checked_at=(day_(0) - timedelta(hours=1)).isoformat()),
                   lambda k: k['preserved_previous'].update(reason_codes=['SEC_CIK_MISMATCH']),
                   lambda k: k['preserved_previous'].update(reason_codes=['SEC_HTTP_404'], http_status=404),
                   lambda k: k['preserved_previous'].update(checked_at=(day_(2)).isoformat())):   # after the run
        p = payload(artifact)
        mutate(p['companies'][0])
        with pytest.raises(ValueError, match='SEC_PUBLIC_INPUT_INVALID'):
            INPUTS.require_public_inputs(p)


# ---------------------------------------------------------------------------------------------------------------
# 5. Transition: the first deploy after the merge reads a /3 live copy.
# ---------------------------------------------------------------------------------------------------------------
def test_v3_live_copy_to_v4_artifact(tmp_path, capsys):
    site = Site()
    day0, _, _ = run_day(tmp_path, 'day0', Site(), day_(0), bodies={D: no_share_concept(D)})
    v3 = as_v3(payload(day0))
    assert v3['companies'][3]['status'] == 'NOT_AVAILABLE' and 'acquired_at' not in v3['companies'][3]
    site.files = {FILE: json.dumps(v3).encode()}
    # Both live readers accept the /3 copy; preservation uses its LIVE rows.
    previous, state = PIPE.load_previous_inputs(open_response=site)
    assert state == 'LOADED' and set(INPUTS.previous_rows(previous)) == set(IDS) - {D}
    artifact, result, _ = run_day(tmp_path, 'day1', site, day_(1), failures={A: HTTP_503, B: CIK_MISMATCH},
                                  bodies={C: no_share_concept(C)})
    after = rows(artifact)
    assert payload(artifact)['schema'] == 'public-sec-reported-inputs/4'
    assert {k: v for k, v in after[A].items() if k != 'preserved_previous'} == v3['companies'][0]   # kept /3 row
    assert after[B]['status'] == 'WITHDRAWN' and after[B]['withdrawn_acquired_at'] == day_(0).isoformat()
    assert after[C]['status'] == 'NOT_AVAILABLE' and after[C]['acquired_at'] == day_(1).isoformat()
    assert after[D]['status'] == 'LIVE'                   # live /3 NA row had no record: a new record, nothing lost
    assert payload(artifact)['collection']['scheduled_streak'] == {'start_day': '2026-10-19', 'count': 0, 'since': None,
                                                                    'last_run_day': '2026-09-02'}   # before the start day
    code, out = guard(artifact, site, capsys)
    line = inputs_line(out)
    assert code == 0 and (line['compared'], line['equal'], line['withdrawn'], line['newer'], line['new_record']) == (
        '16', '1', '1', '14', '1')
    site.deploy(artifact)
    # The other way round: a /3 artifact built before the /4 deploy is refused (older rows, lost NA record).
    code, out = guard(write(tmp_path / 'old-v3', {FILE: v3}), site, capsys)
    assert code == 1 and f'code={C} kind=OLDER ' in out


def test_manual_preserve_path_republishes_v3_and_v4_live_bytes_unchanged(tmp_path, capsys):
    """cockpit-pages.yml (manual): the validated live bytes are copied as they are, /3 or /4, and pass both guards."""
    site = Site()
    day0, _, _ = run_day(tmp_path, 'day0', Site(), day_(0))
    for version, body in (('v3', json.dumps(as_v3(payload(day0))).encode()), ('v4', (day0 / FILE).read_bytes())):
        site.files = {FILE: body}
        out = tmp_path / ('manual-' + version)
        out.mkdir()
        assert PRESERVE.preserve(out, open_response=site) == 'SEC_PREVIOUS_RESTORED'
        assert (out / FILE).read_bytes() == body
        ARTIFACT_GUARD.require_public_inputs(json.loads(body))
        code, text = guard(out, site, capsys)
        assert code == 0 and inputs_line(text)['equal'] == str(len(IDS))


# ---------------------------------------------------------------------------------------------------------------
# 6. Collection block: run context and the self-certifying scheduled deploy streak (counts only).
# ---------------------------------------------------------------------------------------------------------------
def streak_start(monkeypatch, value):
    """Move the fixed start day (the reader refuses future times, so the producer runs on synthetic past days)."""
    for module in {INPUTS, sys.modules['public_sec_inputs']}:
        monkeypatch.setattr(module, 'STREAK_START_DAY', value)


def streak(folder):
    return payload(folder)['collection']['scheduled_streak']


def test_streak_start_day_is_the_first_ledger_observation_day():
    """Owner decisions (queue §9, 2026-10-17 item 2): counted from the scheduled run observing the 2026-10-19 US trading
    day: cron 22:17 UTC on 2026-10-19 = New York 18:17 the same day, after the close."""
    from investment_system.validation import forward_ledger as fl
    run = datetime(2026, 10, 19, 22, 17, tzinfo=UTC)
    assert INPUTS.STREAK_START_DAY == fl.START_DATE.isoformat() == run.astimezone(INPUTS.NEW_YORK).date().isoformat()
    assert fl.completed_session(run) == fl.START_DATE


@pytest.mark.parametrize('previous, state, trigger, day, expected', [
    # before the start day: 0, never `since`, whatever the live copy says
    (None, 'NO_LIVE', 'SCHEDULED', '2026-10-18', (0, None, '2026-10-18')),
    ('live:5:2026-10-13:2026-10-17', 'LOADED', 'SCHEDULED', '2026-10-18', (0, None, '2026-10-18')),
    (None, 'UNAVAILABLE', 'SCHEDULED', '2026-10-18', (0, None, '2026-10-18')),
    # the start day: 1 (nothing before it counts), also when the live copy could not be read
    ('live:0:-:2026-10-18', 'LOADED', 'SCHEDULED', '2026-10-19', (1, '2026-10-19', '2026-10-19')),
    (None, 'UNAVAILABLE', 'SCHEDULED', '2026-10-19', (1, '2026-10-19', '2026-10-19')),
    # continuing, same-day re-run, missed day, unknown
    ('live:1:2026-10-19:2026-10-19', 'LOADED', 'SCHEDULED', '2026-10-20', (2, '2026-10-19', '2026-10-20')),
    ('live:2:2026-10-19:2026-10-20', 'LOADED', 'SCHEDULED', '2026-10-20', (2, '2026-10-19', '2026-10-20')),
    ('live:2:2026-10-19:2026-10-20', 'LOADED', 'SCHEDULED', '2026-10-22', (1, '2026-10-22', '2026-10-22')),
    (None, 'UNAVAILABLE', 'SCHEDULED', '2026-10-21', (None, None, '2026-10-21')),
    ('live:-:-:2026-10-20', 'LOADED', 'SCHEDULED', '2026-10-21', (None, None, '2026-10-21')),
    ('live:-:-:2026-10-19', 'LOADED', 'SCHEDULED', '2026-10-21', (1, '2026-10-21', '2026-10-21')),   # a known missed day
    ('v3', 'LOADED', 'SCHEDULED', '2026-10-21', (None, None, '2026-10-21')),                         # /3 copy: no record
    (None, 'NO_LIVE', 'SCHEDULED', '2026-10-21', (1, '2026-10-21', '2026-10-21')),
    # manual runs neither count nor reset
    ('live:2:2026-10-19:2026-10-20', 'LOADED', 'MANUAL', '2026-10-21', (2, '2026-10-19', '2026-10-20')),
    (None, 'NO_LIVE', 'MANUAL', '2026-10-21', (0, None, None)),
    (None, 'UNAVAILABLE', 'MANUAL', '2026-10-21', (None, None, None)),
])
def test_scheduled_streak_rule(previous, state, trigger, day, expected):
    if previous == 'v3':
        live = {'schema': 'public-sec-reported-inputs/3', 'companies': []}
    elif previous is None:
        live = None
    else:
        _, count, since, last = previous.split(':')
        live = {'schema': INPUTS.SCHEMA, 'collection': {'scheduled_streak': {
            'start_day': INPUTS.STREAK_START_DAY, 'count': None if count == '-' else int(count),
            'since': None if since == '-' else since, 'last_run_day': last}}}
    out = INPUTS.scheduled_streak(live, state, trigger, day)
    assert (out['start_day'], out['count'], out['since'], out['last_run_day']) == ('2026-10-19',) + expected
    INPUTS._require_streak(out, trigger, day)


def test_scheduled_streak_through_the_producer_and_deploys(tmp_path, monkeypatch):
    """Real producer and live readers; the start day moved to the synthetic day 2026-09-02 (day 1)."""
    streak_start(monkeypatch, '2026-09-02')
    site = Site()
    first_day(tmp_path, site)                                                   # 09-01: before the start
    assert streak(tmp_path / 'day0-artifact') == {'start_day': '2026-09-02', 'count': 0, 'since': None, 'last_run_day': '2026-09-01'}
    day1, _, _ = run_day(tmp_path, 'day1', site, day_(1))
    assert streak(day1)['count'] == 1 and streak(day1)['since'] == '2026-09-02'
    site.deploy(day1)
    # A manual run the same day (fallback or one-off) carries the count; it neither adds to it nor resets it.
    manual, _, _ = run_day(tmp_path, 'manual1', site, day_(1) + timedelta(hours=3), environ=MANUAL)
    assert payload(manual)['collection']['trigger'] == 'MANUAL' and streak(manual) == streak(day1)
    site.deploy(manual)
    # A scheduled re-run of the same New York run day is not counted twice.
    rerun, _, _ = run_day(tmp_path, 'rerun1', site, day_(1) + timedelta(hours=1))
    assert streak(rerun) == streak(day1)
    site.deploy(rerun)
    day2, _, _ = run_day(tmp_path, 'day2', site, day_(2))
    assert streak(day2) == {'start_day': '2026-09-02', 'count': 2, 'since': '2026-09-02', 'last_run_day': '2026-09-03'}
    site.deploy(day2)
    # Day 3's artifact is never deployed (refused or failed): day 4 reads day 2's copy, a missed day, 1 again.
    day3, _, _ = run_day(tmp_path, 'day3', site, day_(3))
    assert streak(day3)['count'] == 3
    day4, _, _ = run_day(tmp_path, 'day4', site, day_(4))
    assert streak(day4) == {'start_day': '2026-09-02', 'count': 1, 'since': '2026-09-05', 'last_run_day': '2026-09-05'}
    # Live copy unreadable: unknown, never guessed; it stays unknown while the chain continues, a missed day ends it.
    blind, _, _ = run_day(tmp_path, 'blind', site, day_(4), read_live=False)
    assert streak(blind) == {'start_day': '2026-09-02', 'count': None, 'since': None, 'last_run_day': '2026-09-05'}
    assert payload(blind)['collection']['previous'] == 'UNAVAILABLE'
    site.deploy(blind)
    day5, _, _ = run_day(tmp_path, 'day5', site, day_(5))
    assert streak(day5)['count'] is None and streak(day5)['last_run_day'] == '2026-09-06'
    site.deploy(day5)
    day7, _, _ = run_day(tmp_path, 'day7', site, day_(7))
    assert streak(day7) == {'start_day': '2026-09-02', 'count': 1, 'since': '2026-09-08', 'last_run_day': '2026-09-08'}


def test_collection_block_is_validated(tmp_path):
    site = Site()
    artifact = first_day(tmp_path, site)
    good = payload(artifact)
    assert good['collection'] == {'checked_at': (day_(0) + DELAY).isoformat(), 'run_day': '2026-09-01',
                                  'trigger': 'SCHEDULED', 'previous': 'NO_LIVE', 'stale_after_seconds': 86400,
                                  'scheduled_streak': {'start_day': '2026-10-19', 'count': 0, 'since': None,
                                                       'last_run_day': '2026-09-01'}}
    for mutate in (lambda c: c.update(run_day='2026-09-02'), lambda c: c.update(trigger='CRON'),
                   lambda c: c.update(stale_after_seconds=3600), lambda c: c['scheduled_streak'].update(count=5),
                   lambda c: c['scheduled_streak'].update(count=1, since='2026-09-01'),        # before the start day
                   lambda c: c['scheduled_streak'].update(start_day='2026-09-01'),
                   lambda c: c['scheduled_streak'].update(since='2026-09-01'),
                   lambda c: c['scheduled_streak'].update(last_run_day='2026-08-31'),
                   lambda c: c.update(checked_at=(day_(0) - timedelta(minutes=1)).isoformat()),
                   lambda c: c.update(price=1)):
        p = copy.deepcopy(good)
        mutate(p['collection'])
        with pytest.raises(ValueError, match='SEC_PUBLIC_INPUT_INVALID'):
            INPUTS.require_public_inputs(p)
    without = copy.deepcopy(good)
    del without['collection']
    with pytest.raises(ValueError, match='SEC_PUBLIC_INPUT_INVALID'):
        INPUTS.require_public_inputs(without)


def test_v4_artifact_passes_the_pages_artifact_guard_and_stays_price_free(tmp_path):
    site = Site()
    first_day(tmp_path, site)
    artifact, _, _ = run_day(tmp_path, 'day1', site, day_(1), failures={A: HTTP_503, B: CIK_MISMATCH,
                             C: SecCollectionError('SEC_HTTP_404', stage='fetch', http_status=404)},
                             bodies={D: no_share_concept(D)})
    p = payload(artifact)
    assert {r['status'] for r in p['companies']} == {'LIVE', 'NOT_AVAILABLE', 'WITHDRAWN', 'COLLECTION_FAILED'}
    ARTIFACT_GUARD.require_public_inputs(p)
    text = json.dumps(p)
    assert '987654321' not in text and 'never publish' not in text and 'price' not in text.lower()
