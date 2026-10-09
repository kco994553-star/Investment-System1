"""Manually export offline SEC M1 Q/G candidates to one private JSON file."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from investment_system.producers.serialization import canonical_bytes
from investment_system.qgv.sec_m2 import SecM2Error, analyze_receipts

_SAFE_CODES = {
    'INVALID_ARGUMENTS', 'INVALID_RECEIPT_REQUEST', 'INVALID_INPUT_KIND', 'INVALID_CLOCK',
    'STORE_NOT_AVAILABLE', 'DUPLICATE_ISSUER', 'UNSAFE_OUTPUT', 'OUTPUT_EXISTS', 'PROCESSING_FAILED',
}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's normal error prints untrusted argv and argument values.
        raise SecM2Error('INVALID_ARGUMENTS')


def _timestamp(value: str) -> datetime:
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError
        return stamp.astimezone(timezone.utc)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('INVALID_ARGUMENTS') from exc


def _private_output(output: Path, store: Path) -> Path:
    if '..' in output.parts:
        raise SecM2Error('UNSAFE_OUTPUT')
    target = output.absolute()
    if target.suffix.lower() != '.json' or not target.parent.is_dir():
        raise SecM2Error('UNSAFE_OUTPUT')
    if any(p.is_symlink() for p in (target, *target.parents)):
        raise SecM2Error('UNSAFE_OUTPUT')
    target = target.resolve()
    if target.is_relative_to(store.resolve()):
        raise SecM2Error('UNSAFE_OUTPUT')
    for parent in target.parents:
        if (parent.name.lower() in {'public', 'cockpit'}
                or (parent / '.git').exists() or (parent / '.git').is_symlink()
                or ((parent / 'index.html').exists() and (parent / 'data.json').exists())):
            raise SecM2Error('UNSAFE_OUTPUT')
    if target.exists() and not target.is_file():
        raise SecM2Error('UNSAFE_OUTPUT')
    return target


def _write_private(target: Path, data: bytes) -> None:
    """Exclusive 0600 creation; an equal existing private file is a no-op."""
    directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            fd = os.open(target.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        except FileExistsError:
            existing = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            with os.fdopen(existing, 'rb') as handle:
                info = os.fstat(handle.fileno())
                if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
                    raise SecM2Error('UNSAFE_OUTPUT')
                if info.st_size != len(data) or handle.read(len(data) + 1) != data:
                    raise SecM2Error('OUTPUT_EXISTS')
            return
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.fsync(directory)
        except BaseException:
            os.unlink(target.name, dir_fd=directory)
            raise
    finally:
        os.close(directory)


def main(argv=None) -> int:
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--receipt', action='append', required=True)
    parser.add_argument('--as-of', type=_timestamp, required=True)
    parser.add_argument('--input-kind', choices=('SYNTHETIC', 'OBSERVED_UNVERIFIED'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    try:
        args = parser.parse_args(argv)
        target = _private_output(args.output, args.store)
        result = analyze_receipts(args.store, args.receipt, args.as_of,
                                  evaluated_at=datetime.now(timezone.utc),
                                  synthetic_inputs=args.input_kind == 'SYNTHETIC')
        _write_private(target, canonical_bytes(result))
    except SystemExit as exc:
        return int(exc.code or 0)
    except SecM2Error as exc:
        code = str(exc) if str(exc) in _SAFE_CODES else 'PROCESSING_FAILED'
        print(json.dumps({'status': code}, sort_keys=True))
        return 2
    except Exception:
        print(json.dumps({'status': 'PROCESSING_FAILED'}, sort_keys=True))
        return 2
    rows = [{'receipt_id': row['receipt_id'], 'company_id': row.get('company_id'),
             'status': row['status'], 'reason_codes': row.get('reason_codes', [])}
            for row in result['companies'].values()]
    rows.extend({'receipt_id': row['receipt_id'], 'company_id': None,
                 'status': row['status'], 'reason_codes': row['reason_codes']}
                for row in result['failures'] if row['company_id'] is None)
    summary = {'status': 'CANDIDATE_WRITTEN', 'candidate_id': result['candidate_id'],
               'n_calculated': result['n_calculated'], 'n_unavailable': result['n_unavailable'],
               'results': sorted(rows, key=lambda row: row['receipt_id'])}
    print(json.dumps(summary, sort_keys=True))
    return int(result['n_unavailable'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())
