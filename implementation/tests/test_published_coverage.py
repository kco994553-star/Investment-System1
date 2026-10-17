"""Counts-only coverage line of the published `sec-qgv2.json` (synthetic payloads only)."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re

from investment_system.universe import sec_qgv2 as q

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name):
    spec = importlib.util.spec_from_file_location('_cov_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TOOL = load_tool('published_coverage')
REF = load_tool('sec_qgv2_reference')
LINE = re.compile(r'PUBLISHED_COVERAGE basis=PUBLISHED_FILE file=sec-qgv2\.json universe=504 q=(\d+) g=(\d+) qg_both=(\d+) '
                  r'live=(\d+) stale=(\d+) not_available=(\d+) withdrawn=(\d+) shards_seen=(\d+)/7 acquired_oldest=(\S+) acquired_newest=(\S+) '
                  r'stale_7d_rows=(\d+) never_acquired_rows=(\d+) shard_rows=((?:\d:\d+,){6}\d:\d+) '
                  r'shard_acquired=((?:\d:(?:NONE|\d{4}-\d\d-\d\d/\d{4}-\d\d-\d\d),){6}\d:(?:NONE|\d{4}-\d\d-\d\d/\d{4}-\d\d-\d\d)) '
                  r'as_of=(\S+) calc_version=(\S+)')


def shard_of(cik):
    return int(sha256(cik.encode()).hexdigest(), 16) % 7


def test_line_counts_the_published_scores_and_nothing_else(tmp_path, capsys):
    payload = REF.base()
    (tmp_path / q.FILENAME).write_bytes(q.encode(payload))
    assert TOOL.main(['--artifact-dir', str(tmp_path)]) == 0
    line = capsys.readouterr().out.strip()
    match = LINE.fullmatch(line)
    assert match, line
    rows = payload['records'].values()
    q_n = sum(r['axes']['Q']['score'] is not None for r in rows)
    g_n = sum(r['axes']['G']['score'] is not None for r in rows)
    both = sum(r['axes']['Q']['score'] is not None and r['axes']['G']['score'] is not None for r in rows)
    shards = [shard_of(cik) for _, cik, _, _ in REF.universe_spec()]
    shard_rows = ','.join(f'{i}:{shards.count(i)}' for i in range(7))
    shard_acquired = ','.join(f'{i}:2026-10-13/2026-10-13' if i in shards else f'{i}:NONE' for i in range(7))
    assert match.groups() == (str(q_n), str(g_n), str(both), '27', '0', '477', '0', str(len(set(shards))),
                              '2026-10-13', '2026-10-13', '0', '477', shard_rows, shard_acquired, '2026-10-13T22:30:00Z',
                              payload['calc_version'])  # the file's own calculation version (v2_factors.CALC_VERSION)
    assert q_n > 0 and g_n > 0
    # no codes, tickers, CIKs, scores or prices in the line
    for code, cik, _, _ in REF.universe_spec():
        assert cik not in line and code.split(':')[1] + ' ' not in line + ' ' and code not in line
    # No values may leak: only the version label itself (e.g. qgv2-calc/2026-10-17.1) may contain a dot-number.
    assert 'price' not in line.lower() and not re.search(r'\d+\.\d', line.replace('22:30:00Z', '').replace(' calc_version=' + payload['calc_version'], ''))


def test_rows_older_than_seven_days_and_per_shard_acquisition_dates():
    from datetime import timedelta
    spec = REF.universe_spec()
    old_ciks = {cik for _, cik, _, _ in spec[:10]}
    edge_cik = spec[10][1]                                   # exactly 7 days old: still fresh (strictly older counts)
    updates = {}
    for when, ciks in ((REF.AS_OF - timedelta(days=8), old_ciks), (REF.AS_OF - timedelta(days=7), {edge_cik}),
                       (REF.AS_OF - timedelta(days=1), {cik for _, cik, _, _ in spec[11:]})):
        rows = REF.synthetic_universe_updates(acquired_at=when)
        updates.update({code: rows[code] for code, cik, _, _ in spec if cik in ciks})
    payload = q.merge(None, updates, as_of=REF.AS_OF, shard_index=None)
    assert all(payload['records'][code]['state'] == 'LIVE' for code, *_ in spec)   # 14-day STALE window not reached
    line = TOOL.coverage_line(payload)
    assert LINE.fullmatch(line), line
    assert ' stale_7d_rows=10 never_acquired_rows=477 ' in line
    acquired = dict(part.split(':', 1) for part in line.split(' shard_acquired=')[1].split()[0].split(','))
    for i in range(7):
        days = sorted(({REF.AS_OF.date() - timedelta(days=8)} if any(shard_of(c) == i for c in old_ciks) else set())
                      | ({REF.AS_OF.date() - timedelta(days=7)} if shard_of(edge_cik) == i else set())
                      | ({REF.AS_OF.date() - timedelta(days=1)} if any(shard_of(c) == i for _, c, _, _ in spec[11:]) else set()))
        assert acquired[str(i)] == (f'{days[0].isoformat()}/{days[-1].isoformat()}' if days else 'NONE')


def test_target_rows_are_not_counted_as_universe_coverage():
    payload = REF.base()
    assert any(r['axes']['Q']['score'] is not None for r in payload['target'].values())
    q_n = sum(r['axes']['Q']['score'] is not None for r in payload['records'].values())
    assert f' q={q_n} ' in TOOL.coverage_line(payload)


def test_empty_file_is_counted_as_zero_with_none_dates():
    payload = q.merge(None, {}, as_of=REF.AS_OF, shard_index=None)
    line = TOOL.coverage_line(payload)
    assert ' q=0 g=0 qg_both=0 ' in line and ' shards_seen=0/7 acquired_oldest=NONE acquired_newest=NONE ' in line
    assert ' stale_7d_rows=0 never_acquired_rows=504 shard_rows=0:0,1:0,2:0,3:0,4:0,5:0,6:0 ' in line
    assert ' shard_acquired=0:NONE,1:NONE,2:NONE,3:NONE,4:NONE,5:NONE,6:NONE ' in line


def test_calc_version_is_shown_only_when_present_and_plain():
    payload = REF.base()
    assert TOOL.coverage_line(payload).endswith(' calc_version=' + payload['calc_version'])
    assert TOOL.coverage_line({k: v for k, v in payload.items() if k != 'calc_version'}).endswith(' calc_version=NONE')
    assert TOOL.coverage_line(dict(payload, calc_version='qgv2-2026-10-15')).endswith(' calc_version=qgv2-2026-10-15')
    assert TOOL.coverage_line(dict(payload, calc_version='qgv2-calc/2026-10-17.1')).endswith(' calc_version=qgv2-calc/2026-10-17.1')
    assert TOOL.coverage_line(dict(payload, calc_version='bad value with spaces')).endswith(' calc_version=NONE')
    assert TOOL.coverage_line(dict(payload, calc_version=3)).endswith(' calc_version=NONE')


def test_missing_or_invalid_file_is_a_fixed_status_and_exit_zero(tmp_path, capsys):
    assert TOOL.main(['--artifact-dir', str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == 'PUBLISHED_COVERAGE basis=PUBLISHED_FILE file=sec-qgv2.json status=MISSING'
    tampered = REF.base()
    tampered['records'][REF._codes()[0]]['axes']['Q']['score'] = 0
    (tmp_path / q.FILENAME).write_text(json.dumps(tampered))
    assert TOOL.main(['--artifact-dir', str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == 'PUBLISHED_COVERAGE basis=PUBLISHED_FILE file=sec-qgv2.json status=INVALID'
    try:
        TOOL.main([])
    except SystemExit as exit_:
        assert exit_.code == 0
    assert capsys.readouterr().out.strip() == 'PUBLISHED_COVERAGE CONFIG_INVALID'
