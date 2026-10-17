#!/usr/bin/env python3
"""One `RUN_CONTEXT` line at the start of the daily collect job (owner instruction 2026-10-17, fallback runs).

At the scheduled time + 2 h the owner checks for the day's run and, when none exists, starts a fallback through
workflow_dispatch (all_shards=false). Reports must tell a scheduled run from a manual fallback and the one-off
all-shards dispatch, and the run's actual time from the US trading day it observes, so a manual fallback success is
counted apart from the scheduled consecutive-run count. The line carries only fixed codes, dates and counts:

    RUN_CONTEXT event=<schedule|workflow_dispatch|OTHER> mode=<daily|all_shards|UNKNOWN>
        run_kind=<SCHEDULED|MANUAL_FALLBACK|ALL_SHARDS_ONE_OFF|OTHER> started_at=<UTC time>
        run_day=<New York date> observation_day=<NYSE session date|NONE> ledger=<code> shard=<i|all>/<shard_count>
        record_deadline=<UTC time|NONE>

- started_at: when this step ran (the collect job's start), never the observation day.
- run_day: the New York calendar day of that start; the daily shard is this day's (`shard_day`).
- observation_day / ledger: what the ledger step would record at this time (`completed_session`): RECORDABLE with the
  session date, or NONE with BEFORE_CLOSE, NOT_SESSION_DAY, BEFORE_START or CALENDAR_NOT_CONFIGURED. A day whose run
  did not reach the ledger step before New York midnight stays a gap: it is never written later as a past day.
- record_deadline: New York midnight ending the observation day, as UTC; the ledger step must run before it.

The ledger and shard steps still decide with their own clock and print their own `session=` and `shard=` values; this
line is the run's label only. It always exits 0, so it can never withhold the collection.
"""
import argparse
from datetime import datetime, time, timedelta, timezone
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.universe.sec_universe_shares import load_config, shard_day, shard_index_for
from investment_system.validation import forward_ledger as fl

EVENTS = ('schedule', 'workflow_dispatch')
MODES = ('daily', 'all_shards')
RUN_KINDS = {('schedule', 'daily'): 'SCHEDULED', ('workflow_dispatch', 'daily'): 'MANUAL_FALLBACK',
             ('workflow_dispatch', 'all_shards'): 'ALL_SHARDS_ONE_OFF'}
MODE_ENV = 'RUN_MODE'
EVENT_ENV = 'GITHUB_EVENT_NAME'


def _utc_now():
    return datetime.now(timezone.utc)


def _utc(moment):
    return moment.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def observation(moment):
    """(session date or None, ledger code) for a ledger step running at `moment`."""
    try:
        session = fl.completed_session(moment)
        day = fl.eastern(moment).date()
        if session is not None:
            return (session, 'RECORDABLE') if session >= fl.START_DATE else (None, 'BEFORE_START')
        return None, 'BEFORE_CLOSE' if fl.is_session_day(day) else 'NOT_SESSION_DAY'
    except fl.CalendarNotConfigured:
        return None, 'CALENDAR_NOT_CONFIGURED'


def context_line(moment, *, event, mode, shard_count):
    event = event if event in EVENTS else 'OTHER'
    mode = mode if mode in MODES else 'UNKNOWN'
    session, ledger = observation(moment)
    deadline = 'NONE'
    if session is not None:
        midnight = datetime.combine(session + timedelta(days=1), time(0, 0), tzinfo=fl.ET)
        deadline = _utc(midnight)
    shard = 'all' if mode == 'all_shards' else str(shard_index_for(shard_day(moment), shard_count))
    return (f"RUN_CONTEXT event={event} mode={mode} run_kind={RUN_KINDS.get((event, mode), 'OTHER')} "
            f"started_at={_utc(moment)} run_day={shard_day(moment).isoformat()} "
            f"observation_day={'NONE' if session is None else session.isoformat()} ledger={ledger} "
            f"shard={shard}/{shard_count} record_deadline={deadline}")


def run(*, environ=None, now=_utc_now):
    environ = os.environ if environ is None else environ
    try:
        line = context_line(now(), event=environ.get(EVENT_ENV, ''), mode=environ.get(MODE_ENV, ''),
                            shard_count=load_config()['shard_count'])
    except Exception:
        line = 'RUN_CONTEXT NOT_AVAILABLE'
    print(line)
    return 0


def main(argv=None):
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    return run()


if __name__ == '__main__':
    raise SystemExit(main())
