"""Daily fallback run of sec-daily-public-inputs.yml (owner instruction 2026-10-17). Synthetic data, fake transports only.

At the scheduled time (22:17 UTC) + 2 h the owner checks for the day's run; when none exists a fallback is started
through workflow_dispatch with all_shards=false. Before that fallback is used, these tests drive the real tool code
with an injected clock and read the workflow file as plain text (CI has no YAML parser):

1. a run after 00:00 UTC still observes the intended US trading day (New York session);
2. the shard follows the same New York day, so a fallback after 00:00 UTC keeps that day's shard;
3. a late scheduled run after a fallback (or the other way round) keeps the one existing ledger record;
4. runs never overlap (workflow concurrency) and the private copies are never overwritten;
5. the daily fallback and the all-shards one-off are distinct options and are labelled apart.

Also: a record keeps its actual record time (`created_at`) apart from its observation day (`date`); a day whose
inputs were not captured on that New York day stays a gap and is never backfilled; the RUN_CONTEXT label tells a
scheduled run from a manual fallback so the two are counted apart.
"""
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re

import pytest

from investment_system.universe import sec_universe_shares as shares
from investment_system.validation import forward_ledger as fl
from tests.test_forward_validation_ledger import RawStore, TOKEN, load_tool, missing, run as run_ledger, serving, site
from tests import test_sec_universe_all_shards as fixtures

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT.parent / '.github/workflows/sec-daily-public-inputs.yml'
UTC = timezone.utc
BEFORE = datetime(2026, 10, 16, 22, 37, tzinfo=UTC)          # Fri, before the ledger start
SCHEDULED = datetime(2026, 10, 19, 22, 37, tzinfo=UTC)       # Mon 18:37 New York: the 22:17 UTC cron, 20 min in
FALLBACK = datetime(2026, 10, 20, 0, 17, tzinfo=UTC)         # Mon 20:17 New York: scheduled time + 2 h, next UTC day
LATE = datetime(2026, 10, 20, 1, 40, tzinfo=UTC)             # Mon 21:40 New York: a late scheduled run after the fallback
AFTER_NY_MIDNIGHT = datetime(2026, 10, 20, 4, 30, tzinfo=UTC)  # Tue 00:30 New York: too late for Monday
TUESDAY = datetime(2026, 10, 20, 22, 37, tzinfo=UTC)
MONDAY = date(2026, 10, 19)
RAW_FIRST = {'RAW_REPO_TOKEN': TOKEN, 'FORWARD_LEDGER_PREVIOUS_SOURCE': 'RAW_FIRST'}


def ledger_rows(folder, version=fl.VERSION):
    return fl.require_ledger(fl.parse_json((Path(folder) / fl.FILENAME).read_bytes()))['versions'][version]


def pre_start_ledger(tmp_path):
    tool = load_tool('forward_validation_ledger')
    before = site(tmp_path, BEFORE, name='before')
    assert run_ledger(tool, before, BEFORE, missing) == 0
    return tool, (before / fl.FILENAME).read_bytes()


def shard_of_day(day):
    return shares.shard_index_for(day, shares.load_config()['shard_count'])


def context(moment, event, mode):
    tool = load_tool('daily_run_context')
    return tool.context_line(moment, event=event, mode=mode, shard_count=shares.load_config()['shard_count'])


# ---------------- 1. observation day after 00:00 UTC ----------------
def test_a_fallback_after_utc_midnight_observes_the_same_us_session():
    assert fl.completed_session(SCHEDULED) == fl.completed_session(FALLBACK) == fl.completed_session(LATE) == MONDAY
    assert FALLBACK.date() == MONDAY + timedelta(days=1)  # the UTC date has already moved on
    # Up to New York midnight in both offsets; from New York midnight on, nothing (never the previous day).
    assert fl.completed_session(datetime(2026, 10, 20, 3, 59, tzinfo=UTC)) == MONDAY       # 23:59 EDT
    assert fl.completed_session(AFTER_NY_MIDNIGHT) is None
    assert fl.completed_session(datetime(2026, 12, 22, 4, 59, tzinfo=UTC)) == date(2026, 12, 21)  # 23:59 EST
    assert fl.completed_session(datetime(2026, 12, 22, 5, 0, tzinfo=UTC)) is None


def test_the_fallback_ledger_row_is_the_session_day_and_keeps_its_actual_record_time(tmp_path, capsys):
    tool, before = pre_start_ledger(tmp_path)
    out = site(tmp_path, FALLBACK, name='fallback')
    capsys.readouterr()
    assert run_ledger(tool, out, FALLBACK, serving(before)) == 0
    assert 'appended=1 record=RECORDED session=2026-10-19 ' in capsys.readouterr().out
    for version in (fl.VERSION, fl.V2_VERSION):
        [row] = ledger_rows(out, version)
        # Observation day and actual record time are separate fields; the validator ties them to the same NY day.
        assert row['date'] == '2026-10-19' and row['created_at'] == '2026-10-20T00:17:00+00:00'
        assert fl.eastern(datetime.fromisoformat(row['created_at'])).date() == MONDAY
    assert ledger_rows(out)[0]['qg_as_of'] is not None  # the same-session inputs written after 00:00 UTC are accepted


# ---------------- no backfill ----------------
def test_a_run_after_new_york_midnight_records_nothing_and_the_day_is_never_backfilled(tmp_path, capsys):
    tool, before = pre_start_ledger(tmp_path)
    store = RawStore()
    too_late = site(tmp_path, AFTER_NY_MIDNIGHT, name='too-late')
    capsys.readouterr()
    assert run_ledger(tool, too_late, AFTER_NY_MIDNIGHT, serving(before), environ=RAW_FIRST, upload_call=store,
                      raw_call=store) == 0
    printed = capsys.readouterr().out
    assert 'records=0 appended=0 record=NONE session=NONE' in printed and 'RAW_UPLOAD_SKIPPED no_session_record' in printed
    assert store.releases == {}
    # The next session records only itself: Monday stays a gap (absent row) and is never written as a past day.
    tue = site(tmp_path, TUESDAY, name='tue')
    assert run_ledger(tool, tue, TUESDAY, serving((too_late / fl.FILENAME).read_bytes())) == 0
    assert [r['date'] for r in ledger_rows(tue)] == [r['date'] for r in ledger_rows(tue, fl.V2_VERSION)] == ['2026-10-20']
    # A Monday row made on Tuesday is refused by the validator, and nothing can be inserted before Tuesday's row.
    late_row = fl.build_record(now=TUESDAY, session=MONDAY, qg_body=None, catalog_body=None)
    with pytest.raises(ValueError):
        fl.require_ledger(fl.append(fl.new_ledger(TUESDAY), late_row, TUESDAY))
    tuesday_ledger = fl.parse_json((tue / fl.FILENAME).read_bytes())
    in_time = fl.build_record(now=FALLBACK, session=MONDAY, qg_body=None, catalog_body=None)
    with pytest.raises(ValueError):
        fl.append(tuesday_ledger, in_time, TUESDAY)
    # What exists for the gap today: no ledger row and no stored reason; the run's own log lines carry the cause.
    assert '"date":"2026-10-19"' not in (tue / fl.FILENAME).read_text()
    assert ' observation_day=NONE ledger=BEFORE_CLOSE ' in context(AFTER_NY_MIDNIGHT, 'workflow_dispatch', 'daily')


# ---------------- 2. shard selection across the date change ----------------
def test_shard_day_is_the_utc_day_for_every_scheduled_start_and_the_ny_day_after_utc_midnight():
    day = date(2026, 10, 1)
    while day <= date(2027, 12, 31):
        for hour, minute in ((5, 0), (12, 0), (22, 17), (22, 37), (23, 59)):
            moment = datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)
            assert shares.shard_day(moment) == day  # scheduled runs keep exactly the shard they had
        for hour in (0, 1, 2, 3):
            moment = datetime(day.year, day.month, day.day, hour, 17, tzinfo=UTC)
            assert shares.shard_day(moment) == day - timedelta(days=1)  # still the previous New York day
        day += timedelta(days=1)
    with pytest.raises(ValueError):
        shares.shard_day(datetime(2026, 10, 19, 22, 37))  # naive time: refused


def test_scheduled_and_fallback_runs_collect_the_same_shard_and_raw_tag(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    intended = shard_of_day(MONDAY)
    assert intended != shard_of_day(MONDAY + timedelta(days=1))
    seen = {}
    for name, when in (('scheduled', SCHEDULED), ('fallback', FALLBACK)):
        sec, requests = fixtures.Sec(), []

        def upload(request, **_):
            requests.append(request)
            return fixtures.Response(request.full_url, b'{"id": 7}', 201)

        assert fixtures.run(tool, tmp_path / name, sec, when=when, open_upload=upload,
                            environ={'SEC_USER_AGENT': fixtures.UA, 'RAW_REPO_TOKEN': fixtures.TOKEN}) == 0
        out = capsys.readouterr().out
        assert f'SEC_UNIVERSE_SHARES shard={intended}/7 ' in out
        tags = [json.loads(r.data)['tag_name'] for r in requests if r.full_url.endswith('/releases')]
        assert tags == [f'sec-universe-raw-2026-10-19-shard{intended}']
        seen[name] = sorted(u for u, _, _ in sec.calls)
        fixtures.assert_no_identifiers(out)
    assert seen['scheduled'] == seen['fallback']  # the very same issuers were requested
    for name in ('scheduled', 'fallback'):
        assert fixtures.files(tmp_path / name)[0]['last_shard_index'] == intended


def test_the_domains_step_follows_the_same_new_york_shard():
    tool = load_tool('universe_domains_pipeline')
    fetched = {}
    for name, when in (('scheduled', SCHEDULED), ('fallback', FALLBACK)):
        sec = fixtures.Sec()
        tool.sec_websites(fixtures.UA, now=when, client_kwargs=sec.kwargs(when))
        fetched[name] = {u.split('CIK')[-1].split('.')[0] for u, _, _ in sec.calls if '/submissions/' in u}
    assert fetched['scheduled'] == fetched['fallback'] != set()
    assert {fixtures.shard_of(cik) for cik in fetched['fallback']} == {shard_of_day(MONDAY)}


# ---------------- 3. no duplicate record for the same observation day ----------------
def test_a_late_scheduled_run_after_the_fallback_keeps_the_one_existing_record(tmp_path, capsys):
    tool, before = pre_start_ledger(tmp_path)
    store = RawStore()
    first = site(tmp_path, FALLBACK, name='first')
    assert run_ledger(tool, first, FALLBACK, serving(before), environ=RAW_FIRST, upload_call=store, raw_call=store) == 0
    first_body = (first / fl.FILENAME).read_bytes()
    capsys.readouterr()
    # The fallback's deploy may not have reached Pages yet: the late run still finds the record in the private copy.
    late = site(tmp_path, LATE, name='late')
    assert run_ledger(tool, late, LATE, serving(before), environ=RAW_FIRST, upload_call=store, raw_call=store) == 0
    printed = capsys.readouterr().out
    assert 'FORWARD_LEDGER_PREVIOUS source=RAW raw=FOUND recovered_records=1' in printed
    assert 'appended=0 record=EXISTS session=2026-10-19 ' in printed and 'v2_record=EXISTS' in printed
    for version in (fl.VERSION, fl.V2_VERSION):
        assert [fl.canonical(r) for r in ledger_rows(late, version)] == \
            [fl.canonical(r) for r in fl.parse_json(first_body)['versions'][version]]
    assert ledger_rows(late)[0]['created_at'] == '2026-10-20T00:17:00+00:00'  # the first record's time is kept
    # Same when the late run reads the fallback's deployed Pages copy.
    pages = site(tmp_path, LATE, name='pages')
    assert run_ledger(tool, pages, LATE, serving(first_body)) == 0
    assert 'appended=0 record=EXISTS' in capsys.readouterr().out and len(ledger_rows(pages)) == 1


# ---------------- 4. no overlap, no overwrite ----------------
def test_the_private_ledger_copy_of_a_day_is_never_overwritten(tmp_path, capsys):
    tool, before = pre_start_ledger(tmp_path)
    store = RawStore()
    a, b = site(tmp_path, FALLBACK, name='a'), site(tmp_path, LATE, name='b')
    assert run_ledger(tool, a, FALLBACK, serving(before), environ={'RAW_REPO_TOKEN': TOKEN}, upload_call=store) == 0
    # Two runs that did not see each other (what workflow concurrency prevents) each make a Monday row; the private
    # dated copy keeps the first one and only reports the second.
    assert run_ledger(tool, b, LATE, serving(before), environ={'RAW_REPO_TOKEN': TOKEN}, upload_call=store) == 0
    assert (a / fl.FILENAME).read_bytes() != (b / fl.FILENAME).read_bytes()
    assert 'already_present' in capsys.readouterr().out.splitlines()[-1]
    assert store.body('forward-ledger-2026-10-19') == (a / fl.FILENAME).read_bytes()


def test_a_second_raw_release_with_the_same_tag_is_refused_not_overwritten(tmp_path):
    tool = load_tool('sec_universe_shares')
    (tmp_path / 'raw').mkdir()
    (tmp_path / 'raw' / 'manifest.json').write_text('{}')
    requests = []

    def exists(request, **_):
        requests.append(request)
        return fixtures.Response(request.full_url, b'{}', 422)

    assert tool.upload_raw(tmp_path / 'raw', tag='sec-universe-raw-2026-10-19-shard1', token=fixtures.TOKEN,
                           open_response=exists) == 'RAW_UPLOAD_FAILED code=HTTP_422'
    assert [r.full_url.rsplit('/', 1)[1] for r in requests] == ['releases']  # no asset was sent


def test_overlapping_runs_lose_a_shard_and_serialized_runs_keep_it(tmp_path, capsys):
    """Why the runs must not overlap: each run merges into the copy it read before its own collection."""
    tool = load_tool('sec_universe_shares')
    first_day = SCHEDULED - timedelta(days=1)
    assert fixtures.run(tool, tmp_path / 'p0', fixtures.Sec(), when=first_day) == 0
    assert fixtures.run(tool, tmp_path / 'a', fixtures.Sec(), when=SCHEDULED, previous=tmp_path / 'p0') == 0
    nxt = TUESDAY
    assert fixtures.run(tool, tmp_path / 'overlap', fixtures.Sec(), when=nxt, previous=tmp_path / 'p0') == 0
    assert fixtures.run(tool, tmp_path / 'serial', fixtures.Sec(), when=nxt, previous=tmp_path / 'a') == 0
    capsys.readouterr()
    monday_codes = {code for code, cik, _, _ in fixtures.SPEC if fixtures.shard_of(cik) == shard_of_day(MONDAY)}
    assert monday_codes
    stamp = SCHEDULED.isoformat().replace('+00:00', 'Z')
    acquired = lambda name: {c: fixtures.files(tmp_path / name)[2]['records'][c]['acquired_at'] for c in monday_codes}
    assert set(acquired('a').values()) == {stamp}
    assert set(acquired('serial').values()) == {stamp}          # serialized: Monday's rows are carried
    assert stamp not in set(acquired('overlap').values())       # overlapping: Monday's rows are lost


def workflow_head_and_jobs():
    text = WORKFLOW.read_text()
    head, jobs = text.split('\njobs:\n', 1)
    return text, head, jobs


def test_workflow_runs_never_overlap_and_deploy_keeps_its_pages_group():
    text, head, jobs = workflow_head_and_jobs()
    # One group for every event on a ref: only the ref is in the group, so the scheduled run and both dispatch options
    # on the default branch share it (schedule always runs on the default branch).
    assert '\nconcurrency:\n  group: sec-daily-public-inputs-${{ github.ref }}\n  cancel-in-progress: false\n' in head + '\n'
    assert 'event_name' not in head.split('\nconcurrency:\n', 1)[1] and 'inputs.' not in head.split('\nconcurrency:\n', 1)[1]
    assert text.count('\nconcurrency:\n') == 1 and 'cancel-in-progress: true' not in text
    assert 'ONE pending run per group' in head and 'cancels the older pending' in head
    deploy = jobs.split('\n  deploy:\n', 1)[1]
    assert '    concurrency:\n      group: checked-cockpit-pages\n      cancel-in-progress: false' in deploy


# ---------------- 5. daily fallback vs the all-shards one-off ----------------
def test_fallback_and_all_shards_are_distinct_dispatch_options():
    text, head, jobs = workflow_head_and_jobs()
    assert "all_shards:\n        description: '1회성: 504종목 전체 샤드를 한 번에 수집(새 계산 규칙 게시용)'\n" \
           "        type: boolean\n        required: false\n        default: false" in head
    collect = jobs[jobs.index('\n  collect:\n'):jobs.index('\n  verify:\n')]
    one_off = "github.event_name == 'workflow_dispatch' && inputs.all_shards"
    # The flag, the longer timeout and the run label switch only on a dispatch with the box ticked; a fallback
    # dispatch with all_shards=false gets exactly the scheduled command.
    assert f"ALL_SHARDS_FLAG: ${{{{ {one_off} && '--all-shards' || '' }}}}" in collect
    assert f"timeout-minutes: ${{{{ {one_off} && 120 || 40 }}}}" in collect
    assert f"RUN_MODE: ${{{{ {one_off} && 'all_shards' || 'daily' }}}}" in collect
    step = collect[collect.index('- name: Record run context'):]
    step = step[:step.index('\n      - ', 1)]
    assert '        continue-on-error: true' in step and 'secrets.' not in step
    assert 'run: python implementation/tools/daily_run_context.py' in step
    names = [l.strip()[len('- name: '):] for l in collect.splitlines() if l.strip().startswith('- name: ')]
    assert names[0] == 'Record run context (event, mode, start time, observation day, shard)'


def test_the_daily_and_all_shards_raw_tags_never_collide(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    tags = {}
    for mode, extra in (('daily', {}), ('all', {'all_shards': True})):
        requests = []

        def upload(request, **_):
            requests.append(request)
            return fixtures.Response(request.full_url, b'{"id": 7}', 201)

        assert fixtures.run(tool, tmp_path / mode, fixtures.Sec(), when=FALLBACK, open_upload=upload,
                            environ={'SEC_USER_AGENT': fixtures.UA, 'RAW_REPO_TOKEN': fixtures.TOKEN}, **extra) == 0
        tags[mode] = {json.loads(r.data)['tag_name'] for r in requests if r.full_url.endswith('/releases')}
    capsys.readouterr()
    assert tags['daily'] == {f'sec-universe-raw-2026-10-19-shard{shard_of_day(MONDAY)}'}
    assert tags['all'] == {f'sec-universe-raw-2026-10-19-all-shard{i}' for i in range(7)}


@pytest.mark.parametrize('moment, event, mode, expected', [
    (SCHEDULED, 'schedule', 'daily',
     'event=schedule mode=daily run_kind=SCHEDULED started_at=2026-10-19T22:37:00Z run_day=2026-10-19 '
     'observation_day=2026-10-19 ledger=RECORDABLE shard={mon}/7 record_deadline=2026-10-20T04:00:00Z'),
    (FALLBACK, 'workflow_dispatch', 'daily',
     'event=workflow_dispatch mode=daily run_kind=MANUAL_FALLBACK started_at=2026-10-20T00:17:00Z run_day=2026-10-19 '
     'observation_day=2026-10-19 ledger=RECORDABLE shard={mon}/7 record_deadline=2026-10-20T04:00:00Z'),
    (FALLBACK, 'workflow_dispatch', 'all_shards',
     'event=workflow_dispatch mode=all_shards run_kind=ALL_SHARDS_ONE_OFF started_at=2026-10-20T00:17:00Z '
     'run_day=2026-10-19 observation_day=2026-10-19 ledger=RECORDABLE shard=all/7 record_deadline=2026-10-20T04:00:00Z'),
    (AFTER_NY_MIDNIGHT, 'workflow_dispatch', 'daily',
     'event=workflow_dispatch mode=daily run_kind=MANUAL_FALLBACK started_at=2026-10-20T04:30:00Z run_day=2026-10-20 '
     'observation_day=NONE ledger=BEFORE_CLOSE shard={tue}/7 record_deadline=NONE'),
    (datetime(2026, 12, 22, 0, 17, tzinfo=UTC), 'schedule', 'daily',
     'event=schedule mode=daily run_kind=SCHEDULED started_at=2026-12-22T00:17:00Z run_day=2026-12-21 '
     'observation_day=2026-12-21 ledger=RECORDABLE shard={dec}/7 record_deadline=2026-12-22T05:00:00Z'),
    (datetime(2026, 10, 24, 22, 37, tzinfo=UTC), 'schedule', 'daily',
     'event=schedule mode=daily run_kind=SCHEDULED started_at=2026-10-24T22:37:00Z run_day=2026-10-24 '
     'observation_day=NONE ledger=NOT_SESSION_DAY shard={sat}/7 record_deadline=NONE'),
    (BEFORE, 'schedule', 'daily',
     'event=schedule mode=daily run_kind=SCHEDULED started_at=2026-10-16T22:37:00Z run_day=2026-10-16 '
     'observation_day=NONE ledger=BEFORE_START shard={fri}/7 record_deadline=NONE'),
    (datetime(2029, 1, 2, 22, 37, tzinfo=UTC), 'push', '',
     'event=OTHER mode=UNKNOWN run_kind=OTHER started_at=2029-01-02T22:37:00Z run_day=2029-01-02 '
     'observation_day=NONE ledger=CALENDAR_NOT_CONFIGURED shard={y29}/7 record_deadline=NONE'),
])
def test_run_context_labels_kind_actual_time_and_observation_day(moment, event, mode, expected):
    shards = {'mon': MONDAY, 'tue': date(2026, 10, 20), 'dec': date(2026, 12, 21), 'sat': date(2026, 10, 24),
              'fri': date(2026, 10, 16), 'y29': date(2029, 1, 2)}
    expected = expected.format(**{k: shard_of_day(d) for k, d in shards.items()})
    assert context(moment, event, mode) == 'RUN_CONTEXT ' + expected


def test_run_context_tool_reads_only_the_event_and_mode_and_always_exits_zero(capsys, monkeypatch):
    tool = load_tool('daily_run_context')
    secret = 'synthetic-secret-value-' + 'x' * 8
    environ = {'GITHUB_EVENT_NAME': 'workflow_dispatch', 'RUN_MODE': 'daily', 'SEC_USER_AGENT': secret,
               'RAW_REPO_TOKEN': secret}
    assert tool.run(environ=environ, now=lambda: FALLBACK) == 0
    line = capsys.readouterr().out
    assert line.startswith('RUN_CONTEXT event=workflow_dispatch mode=daily run_kind=MANUAL_FALLBACK ') and secret not in line
    assert re.fullmatch(r'RUN_CONTEXT( [a-z_]+=[A-Za-z0-9_:/.-]+)+\n', line)
    monkeypatch.setattr(tool, 'load_config', lambda: (_ for _ in ()).throw(ValueError('broken')))
    assert tool.run(environ=environ, now=lambda: FALLBACK) == 0
    assert capsys.readouterr().out == 'RUN_CONTEXT NOT_AVAILABLE\n'
