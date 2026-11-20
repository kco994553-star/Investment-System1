"""Read-only B2 source-storage estimate. No acquisition, data writer or release API.

Full records, including rejected rows and revisions, stay in month-grouped,
immutable parts. This is a sizing/roundtrip prototype, not an activated collector.
"""
import argparse
from collections import defaultdict
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import tarfile
import zlib


def price_part(rows):
    # Stable series order; never deduplicate dates or reorder a revision chain.
    raw = b''.join(json.dumps([sid, row], sort_keys=True, ensure_ascii=False,
                             separators=(',', ':')).encode() + b'\n'
                   for sid, row in sorted(rows, key=lambda item: item[0]))
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode='wb', mtime=0, compresslevel=9) as f:
        f.write(raw)
    return out.getvalue()


def read_price_part(value):
    return [(sid, row) for sid, row in
            (json.loads(line) for line in gzip.decompress(value).splitlines())]


def new_git_bytes(value):
    return len(zlib.compress(b'blob ' + str(len(value)).encode() + b'\0' + value, 1))


def annual_budget(*, month_git, row_count, series_count, max_daily_git,
                  sessions=1260, updates=252):
    if min(month_git, row_count, series_count, max_daily_git, sessions, updates) <= 0:
        raise ValueError('POSITIVE_MEASUREMENT_REQUIRED')
    parts = dict(view_updates_estimate=452904 * updates,
                 view_sealing_allowance=45925 * updates * 2,
                 # Replaces the old unmeasured 60MB allowance; derivation in doc.
                 view_bootstrap_allowance=20_000_000,
                 price_bootstrap_estimate=math.ceil(month_git * series_count * sessions / row_count),
                 price_new_rows_estimate=max_daily_git * updates,
                 summaries_allowance=1_000_000, other_git_reserve=40_000_000)
    total = sum(parts.values())
    return dict(parts, total_estimate=total, ceiling_bytes=300_000_000,
                headroom_estimate=300_000_000-total,
                actual_annual_growth_measured=False,
                sessions=sessions, updates=updates, series_count=series_count,
                assumptions='NO_DELTA_INITIAL_5Y_INCLUDED_BASE_VIEW_ESTIMATE_FOR_517_SERIES',
                enforcement='DESIGN_ONLY_COMBINED_GROWTH_NOT_ENFORCED_BY_VIEW_LEDGER')


def profile(archive, expected_sha256):
    archive = Path(archive)
    with archive.open('rb') as f:
        if hashlib.file_digest(f, 'sha256').hexdigest() != expected_sha256:
            raise ValueError('SOURCE_ARCHIVE_PIN')
    months, days = defaultdict(list), defaultdict(list)
    with tarfile.open(archive) as t:
        for member in t:
            if '/series/' not in member.name or '/months/' not in member.name or not member.name.endswith('.jsonl.gz'):
                continue
            sid = member.name.split('/series/')[1].split('/')[0]
            for line in gzip.decompress(t.extractfile(member).read()).splitlines():
                row = json.loads(line)
                months[row['date'][:7]].append((sid, row))
                days[row['date']].append((sid, row))
    series = {sid for rows in months.values() for sid, _ in rows}
    row_count = sum(map(len, months.values()))
    month_sizes = [new_git_bytes(price_part(rows)) for rows in months.values()]
    daily_sizes = [new_git_bytes(price_part(rows)) for rows in days.values()]
    # Contrast the same economic rows in a current-month file rewritten daily.
    # This is a storage scenario, not a replay of provider captures or indicators.
    rewritten = [new_git_bytes(price_part([item for item in months[day[:7]] if item[1]['date'] <= day]))
                 for day in sorted(days)]
    differences = 0
    for rows in months.values():
        differences += read_price_part(price_part(rows)) != sorted(rows, key=lambda item: item[0])
    return dict(source_archive_sha256=expected_sha256, kind='HELD_ROWS_STORAGE_ONLY_NO_RECALCULATION',
                series=len(series), rows=row_count, sessions=len(days), month_parts=len(months),
                lossless_month_differences=differences,
                month_git_bytes=sum(month_sizes), max_daily_git_bytes=max(daily_sizes),
                current_month_rewrite_max_daily_git_bytes=max(rewritten),
                current_month_rewrite_mean_daily_git_bytes=sum(rewritten)/len(rewritten),
                annual=annual_budget(month_git=sum(month_sizes), row_count=row_count,
                                     series_count=len(series), max_daily_git=max(daily_sizes)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--receipt', type=Path, required=True)
    args = p.parse_args()
    result = profile(args.archive, args.expected_sha256)
    with args.receipt.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({k: result[k] for k in ('series', 'rows', 'month_parts', 'lossless_month_differences')}))


if __name__ == '__main__':
    main()
