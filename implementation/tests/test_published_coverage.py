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
                  r'live=(\d+) stale=(\d+) not_available=(\d+) shards_seen=(\d+)/7 acquired_oldest=(\S+) acquired_newest=(\S+) '
                  r'as_of=(\S+) calc_version=(\S+)')


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
    shards = {int(sha256(cik.encode()).hexdigest(), 16) % 7 for _, cik, _, _ in REF.universe_spec()}
    assert match.groups() == (str(q_n), str(g_n), str(both), '27', '0', '477', str(len(shards)),
                              '2026-10-13', '2026-10-13', '2026-10-13T22:30:00Z', 'NONE')
    assert q_n > 0 and g_n > 0
    # no codes, tickers, CIKs, scores or prices in the line
    for code, cik, _, _ in REF.universe_spec():
        assert cik not in line and code.split(':')[1] + ' ' not in line + ' ' and code not in line
    assert 'price' not in line.lower() and not re.search(r'\d+\.\d', line.replace('22:30:00Z', ''))


def test_target_rows_are_not_counted_as_universe_coverage():
    payload = REF.base()
    assert any(r['axes']['Q']['score'] is not None for r in payload['target'].values())
    q_n = sum(r['axes']['Q']['score'] is not None for r in payload['records'].values())
    assert f' q={q_n} ' in TOOL.coverage_line(payload)


def test_empty_file_is_counted_as_zero_with_none_dates():
    payload = q.merge(None, {}, as_of=REF.AS_OF, shard_index=None)
    line = TOOL.coverage_line(payload)
    assert ' q=0 g=0 qg_both=0 ' in line and ' shards_seen=0/7 acquired_oldest=NONE acquired_newest=NONE ' in line


def test_calc_version_is_shown_only_when_present_and_plain():
    payload = REF.base()
    assert TOOL.coverage_line(payload).endswith(' calc_version=NONE')
    assert TOOL.coverage_line(dict(payload, calc_version='qgv2-2026-10-15')).endswith(' calc_version=qgv2-2026-10-15')
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
