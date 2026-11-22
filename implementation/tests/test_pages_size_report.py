"""Size early warning for the final Pages artifact (owner 2026-11-22): tools/pages_size_report.py."""
import importlib.util
import io
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def load_tool(name):
    spec = importlib.util.spec_from_file_location('_size_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TOOL = load_tool('pages_size_report')
LIMIT = TOOL.guard.MAX_FILE_BYTES
LINE = re.compile(r'PAGES_SIZE file=[A-Za-z0-9._-]+ bytes=\d+ limit=\d+ ratio=\d+\.\d%')


def site(tmp_path, sizes):
    for name, size in sizes.items():
        (tmp_path / name).write_bytes(b'x' * size)
    return tmp_path


def run(path, summary=None):
    stream = io.StringIO()
    rows = TOOL.report(path, summary_path=summary, stream=stream)
    return rows, stream.getvalue().splitlines()


def test_limits_are_the_guards_and_unchanged():
    assert LIMIT == 2 * 1024 * 1024 and TOOL.guard.MAX_ENTRIES == 192
    assert TOOL.limit_of('jua-regular-ksx1001.woff2') == TOOL.guard.FONT_MAX_BYTES == 256 * 1024
    assert TOOL.limit_of('sec-qgv2.json') == LIMIT
    assert (TOOL.WARN_RATIO, TOOL.ALERT_RATIO) == (0.80, 0.95)


def test_lines_carry_name_size_limit_ratio_only_largest_first(tmp_path):
    (tmp_path / 'sec-qgv2.json').write_text('{"secret_value": 123456789}', encoding='utf-8')
    site(tmp_path, {'a.json': 1000, 'b.json': LIMIT // 2})
    rows, lines = run(tmp_path)
    assert [r['file'] for r in rows] == ['b.json', 'a.json', 'sec-qgv2.json']
    sized = [l for l in lines if l.startswith('PAGES_SIZE ')]
    assert len(sized) == 3 and all(LINE.fullmatch(l) for l in sized)
    assert sized[0] == f'PAGES_SIZE file=b.json bytes={LIMIT // 2} limit={LIMIT} ratio=50.0%'
    assert lines[-1] == f'PAGES_SIZE_TOTAL entries=3/192 bytes={1000 + LIMIT // 2 + 27} warn=0 alert=0'
    assert not any('secret_value' in l or '123456789' in l for l in lines)  # never reads content
    assert not any(l.startswith('::warning') for l in lines)


def test_80_percent_warns_and_95_percent_goes_to_the_top_of_the_summary(tmp_path):
    site(tmp_path, {'warm.json': int(LIMIT * 0.82), 'hot.json': int(LIMIT * 0.96), 'cool.json': 10})
    summary = tmp_path.parent / 'summary.md'
    _, lines = run(tmp_path, summary=str(summary))
    warnings = [l for l in lines if l.startswith('::warning')]
    assert len(warnings) == 2
    assert warnings[0].startswith('::warning title=Pages file size 95%::hot.json ')
    assert warnings[1].startswith('::warning title=Pages file size 80%::warm.json ')
    assert lines[-1].endswith('warn=2 alert=1')
    text = summary.read_text(encoding='utf-8')
    assert text.startswith('## ⚠ 공개 파일 크기 95% 이상')
    top = text.split('## 공개 파일 크기\n', 1)[0]
    assert 'hot.json' in top and 'warm.json' not in top and 'cool.json' not in top
    assert '80% 이상 2개 · 95% 이상 1개' in text


def test_exactly_at_the_lines(tmp_path):
    site(tmp_path, {'w.json': int(LIMIT * 0.80) + 1, 'a.json': int(LIMIT * 0.95) + 1, 'u.json': int(LIMIT * 0.80) - 1})
    _, lines = run(tmp_path)
    assert lines[-1].endswith('warn=2 alert=1')


def test_never_fails_and_never_withholds_the_upload(tmp_path, capsys):
    assert TOOL.main(['--artifact-dir', str(tmp_path / 'missing')]) == 0
    assert capsys.readouterr().out.strip() == 'PAGES_SIZE_REPORT_FAILED FileNotFoundError'
    site(tmp_path, {'big.json': LIMIT + 5})  # over the limit: the guard refuses it earlier; this step only reports
    assert TOOL.main(['--artifact-dir', str(tmp_path)]) == 0


def test_workflows_run_it_read_only_right_before_each_pages_upload():
    for workflow in ('cockpit-pages.yml', 'sec-daily-public-inputs.yml'):
        text = (REPO / '.github' / 'workflows' / workflow).read_text(encoding='utf-8')
        steps = text.split('\n      - ')
        upload = next(i for i, s in enumerate(steps) if 'actions/upload-pages-artifact@' in s)
        # Right before the upload; in the daily run only the read-only coverage line (kept last in the log) sits between.
        between = 1 if workflow == 'cockpit-pages.yml' else 2
        before = steps[upload - between]
        assert all('published_coverage.py' in s for s in steps[upload - between + 1:upload])
        assert 'python implementation/tools/pages_size_report.py --artifact-dir "$RUNNER_TEMP/public-cockpit"' in before
        assert '        continue-on-error: true' in before.splitlines()
        assert 'secrets.' not in before and 'env:' not in before
        assert text.count('pages_size_report.py') == 1
