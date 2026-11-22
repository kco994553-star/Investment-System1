#!/usr/bin/env python3
"""Size early warning for the FINAL Pages artifact (owner 2026-11-22, PUBLIC_FILE_INCIDENTS.md §3).

Read-only. Run as the last step before the Pages upload. For each file of the artifact it prints the file name, its size,
the per-file limit the Pages guard applies to it and the ratio, and nothing else: no value or per-company content is read.

    PAGES_SIZE file=<name> bytes=<n> limit=<n> ratio=<pct>%          (one line per file, largest ratio first)
    PAGES_SIZE_TOTAL entries=<n>/<MAX_ENTRIES> bytes=<n> warn=<k> alert=<k>

At or above 80% a file also gets a GitHub `::warning`; at or above 95% it is listed in its own block at the top of the run
summary ($GITHUB_STEP_SUMMARY). No new notification channel. The tool always exits 0, so it never withholds the upload, and
it changes no guard or limit: the limits are read from pages_artifact_guard.py.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pages_artifact_guard as guard  # noqa: E402

WARN_RATIO = 0.80
ALERT_RATIO = 0.95
SUMMARY_ROWS = 15


def limit_of(name: str) -> int:
    return guard.FONT_MAX_BYTES if name in guard.FONT_FILES else guard.MAX_FILE_BYTES


def measure(artifact_dir: Path) -> list[dict]:
    """One row per regular file directly in the artifact (the guard refuses folders and links), largest ratio first."""
    rows = []
    for entry in sorted(Path(artifact_dir).iterdir(), key=lambda p: p.name):
        if entry.is_symlink() or not entry.is_file():
            continue
        size, limit = entry.stat().st_size, limit_of(entry.name)
        rows.append({'file': entry.name, 'bytes': size, 'limit': limit, 'ratio': size / limit})
    rows.sort(key=lambda r: (-r['ratio'], r['file']))
    return rows


def pct(ratio: float) -> str:
    return f'{ratio * 100:.1f}'


def summary(rows: list[dict]) -> str:
    alert = [r for r in rows if r['ratio'] >= ALERT_RATIO]
    warn = [r for r in rows if WARN_RATIO <= r['ratio'] < ALERT_RATIO]
    out = []
    if alert:
        out += ['## ⚠ 공개 파일 크기 95% 이상', '', '| 파일 | 크기(B) | 한도(B) | 비율 |', '|---|---:|---:|---:|']
        out += [f"| {r['file']} | {r['bytes']:,} | {r['limit']:,} | {pct(r['ratio'])}% |" for r in alert]
        out.append('')
    out += ['## 공개 파일 크기', '']
    out.append(f"파일 {len(rows)}개 / 한도 {guard.MAX_ENTRIES}개 · 80% 이상 {len(warn) + len(alert)}개 · 95% 이상 {len(alert)}개")
    out += ['', '| 파일 | 크기(B) | 한도(B) | 비율 |', '|---|---:|---:|---:|']
    out += [f"| {r['file']} | {r['bytes']:,} | {r['limit']:,} | {pct(r['ratio'])}% |" for r in rows[:SUMMARY_ROWS]]
    return '\n'.join(out) + '\n'


def report(artifact_dir: Path, *, summary_path: str | None = None, stream=None) -> list[dict]:
    stream = stream or sys.stdout
    rows = measure(artifact_dir)
    for r in rows:
        print(f"PAGES_SIZE file={r['file']} bytes={r['bytes']} limit={r['limit']} ratio={pct(r['ratio'])}%", file=stream)
    for r in rows:
        if r['ratio'] >= WARN_RATIO:
            level = '95' if r['ratio'] >= ALERT_RATIO else '80'
            print(f"::warning title=Pages file size {level}%::{r['file']} {r['bytes']}/{r['limit']} B ({pct(r['ratio'])}%)",
                  file=stream)
    warn = sum(r['ratio'] >= WARN_RATIO for r in rows)
    alert = sum(r['ratio'] >= ALERT_RATIO for r in rows)
    print(f"PAGES_SIZE_TOTAL entries={len(rows)}/{guard.MAX_ENTRIES} bytes={sum(r['bytes'] for r in rows)} "
          f"warn={warn} alert={alert}", file=stream)
    if summary_path:
        # The 95% block goes to the top of the run summary: GITHUB_STEP_SUMMARY is per step, so it is written first here.
        with open(summary_path, 'a', encoding='utf-8') as handle:
            handle.write(summary(rows))
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--artifact-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report(args.artifact_dir, summary_path=os.environ.get('GITHUB_STEP_SUMMARY') or None)
    except Exception as error:  # reporting only: never withhold the upload
        print(f'PAGES_SIZE_REPORT_FAILED {type(error).__name__}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
