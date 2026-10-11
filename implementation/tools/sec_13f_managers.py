"""Actions-side 13F step: verify configured manager CIKs, capture the latest two
13F-HR information tables, and rewrite only sec-13f-changes.json in --out.

Runs after public_screens_pipeline.py. Raw SEC bytes stay in a temporary private
directory; the published file is the existing reported-quantity projection plus
per-manager verification records (no personal data, no values, no trades).
Only the secret slot name SEC_USER_AGENT is read; its value is never printed.
"""
from datetime import datetime, timedelta, timezone
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.config.manager_styles import load_manager_styles, ManagerStylesError
from investment_system.product.public_engine_screens import generate_screen_bundle, require_public_screen
from investment_system.providers.sec_13f_managers import Sec13FClient, collect_managers, comparison_reasons
from investment_system.providers.sec_collection import SecCollectionError, SEC_USER_AGENT_SLOT

NAME = 'sec-13f-changes.json'
ACQUISITION_TTL = timedelta(hours=24)  # same daily acquisition cadence as public_screens_pipeline
# Pages guard and the device reader reject files above 2 MiB; keep headroom.
SIZE_BUDGET = 1_900_000


def _utc_now():
    return datetime.now(timezone.utc)


def _serialize(payload):
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()


def build(out_dir, *, config, fetch, now=_utc_now):
    """Return (payload, mismatched_names). Writes only sec-13f-changes.json."""
    out = Path(out_dir)
    if out.is_symlink() or not out.is_dir() or (out / NAME).is_symlink():
        raise ValueError('SEC_13F_OUTPUT_INVALID')
    records, captures, mismatched = collect_managers(config, fetch, now=now)
    as_of = now()
    by_id = {record['id']: record for record in records}
    with tempfile.TemporaryDirectory(prefix='sec-13f-private-') as private:
        root = Path(private)
        pairs = {}
        for capture in captures:
            pair = {'synthetic': False}
            for key in ('previous', 'current'):
                body, metadata = capture[key]
                name = capture['id'] + '-' + key + '.xml'
                (root / name).write_bytes(body)
                pair[key] = {'file': name, 'metadata': metadata}
            pairs[capture['id']] = pair
            by_id[capture['id']]['comparison_reasons'] = comparison_reasons(capture['previous'], capture['current'], as_of=as_of)
        while True:
            manifest = {'schema_version': 1, 'sec': [], 'macro': [], 'thirteen_f': list(pairs.values()),
                        'thirteen_f_managers': records}
            payload = generate_screen_bundle(manifest=manifest, input_root=root, as_of=as_of, stale_after=ACQUISITION_TTL)[NAME]
            body = _serialize(payload)
            if len(body) <= SIZE_BUDGET or not pairs:
                break
            # Withhold the largest report explicitly instead of truncating its changes.
            sizes = {cik: len(r['changes']) for cik, r in ((r['manager_cik'], r) for r in payload['data']['reports'])}
            drop = max(pairs, key=lambda mid: sizes.get(by_id[mid]['cik'], 0))
            del pairs[drop]
            by_id[drop].update(capture_reason='PUBLIC_SIZE_LIMIT', comparison_reasons=[])
    require_public_screen(NAME, payload)
    with tempfile.NamedTemporaryFile(dir=out, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(body)
    try:
        temporary.replace(out / NAME)
    finally:
        temporary.unlink(missing_ok=True)
    return payload, mismatched


def _print(payload, mismatched):
    reports = {r['manager_cik']: r for r in payload['data']['reports']}
    for m in payload['data']['managers']:
        report = reports.get(m['cik'])
        line = (f"SEC_13F_MANAGER id={m['id']} state={m['state']} reason={m['reason_code'] or '-'}"
                f" capture={m['capture_reason'] or '-'} comparison={report['state'] if report else 'NOT_AVAILABLE'}"
                f" changes={len(report['changes']) if report else 0} why={','.join(m['comparison_reasons']) or '-'}")
        if m['id'] in mismatched:
            line += f" sec_name={json.dumps(mismatched[m['id']])}"
        print(line)
    verified = sum(m['state'] == 'VERIFIED' for m in payload['data']['managers'])
    available = sum(r['state'] != 'NOT_AVAILABLE' for r in payload['data']['reports'])
    print(f"SEC_13F_MANAGERS_OK verified={verified} reports={len(reports)} available={available} state={payload['state']}")


def main(argv=None, *, environ=None, transport=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    environ = os.environ if environ is None else environ
    try:
        config = load_manager_styles()
        agent = environ.get(SEC_USER_AGENT_SLOT)
        if not agent:
            print('SEC_13F_MANAGERS_FAILED code=SEC_USER_AGENT_MISSING')
            return 1
        client = Sec13FClient(agent, **({'transport': transport} if transport else {}))
        payload, mismatched = build(args.out, config=config, fetch=client.fetch)
    except ManagerStylesError:
        print('SEC_13F_MANAGERS_FAILED code=MANAGER_STYLES_INVALID')
        return 1
    except SecCollectionError as error:
        code = error.args[0] if error.args and isinstance(error.args[0], str) and error.args[0].isupper() else 'SEC_CONFIG_INVALID'
        print('SEC_13F_MANAGERS_FAILED code=' + code)
        return 1
    except (OSError, ValueError, TypeError, KeyError):
        print('SEC_13F_MANAGERS_FAILED code=SEC_13F_OUTPUT_INVALID')
        return 1
    _print(payload, mismatched)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
