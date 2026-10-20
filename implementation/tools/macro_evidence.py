#!/usr/bin/env python3
"""Public `macro-evidence.json` (MEV-1 P1 13 macro evidence lines; exploration only, MEV-10).

- build (build_pages_cockpit.py): `emit_empty` writes a NOT_AVAILABLE copy without source data;
- daily run: `public_screens_pipeline.py --live --macro-v0 --macro-evidence` calls `run_from_capture` inside its
  private capture directory, so BLS LNS14000000, BEA A191RL and the Treasury curve are reused from the macro v0 /
  lights v1 collection (never fetched twice). The previous Pages copy is carried forward (append-only vintages):
  404 -> baseline; an invalid copy -> discarded (baseline, PREVIOUS_DISCARDED); a network failure -> a new baseline
  marked continuity=RESET_PREVIOUS_UNAVAILABLE (the earlier history is not on this runner);
- --preserve-only (UI-only deploys, cockpit-pages.yml) -> the validated live copy re-published byte for byte.

A failure here never fails the SEC step that hosts it: only fixed codes and counts are printed (no URL, key, value or
provider message).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.macro import evidence_lines as el

SOURCE = 'https://kco994553-star.github.io/Investment-System1/' + el.FILENAME


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print('MACRO_EVIDENCE ARGUMENTS_INVALID')
        raise SystemExit(2)


def _utc_now():
    return datetime.now(timezone.utc)


def parse_json(body: bytes) -> dict:
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError('MACRO_EVIDENCE_DUPLICATE_KEY')
            out[key] = value
        return out

    def constant(_value):
        raise ValueError('MACRO_EVIDENCE_NONFINITE')
    return json.loads(body.decode('utf-8', errors='strict'), object_pairs_hook=unique, parse_constant=constant)


def previous_copy(open_response=None):
    """(validated payload, live bytes); (None, None) on 404. Network errors raise OSError, invalid copies ValueError."""
    request = urllib.request.Request(SOURCE, headers={'Accept': 'application/json', 'Cache-Control': 'no-cache'})
    fetch = open_response or urllib.request.build_opener(NoRedirect()).open
    try:
        with fetch(request, timeout=20) as response:
            if response.status != 200 or response.geturl() != SOURCE:
                raise OSError('PREVIOUS_FETCH_FAILED')
            body = response.read(el.MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None, None
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    except (urllib.error.URLError, OSError):
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    if len(body) > el.MAX_BYTES:
        raise ValueError('MACRO_EVIDENCE_PREVIOUS_TOO_LARGE')
    return el.require_macro_evidence(parse_json(body)), body


def load_previous(open_response=None):
    """(payload or None, LOADED | NO_LIVE | UNAVAILABLE)."""
    try:
        payload, _ = previous_copy(open_response)
    except ValueError:
        print('MACRO_EVIDENCE PREVIOUS_DISCARDED')
        return None, 'NO_LIVE'
    except Exception:
        return None, 'UNAVAILABLE'
    return payload, 'LOADED' if payload is not None else 'NO_LIVE'


def write_bytes(directory, body: bytes) -> bytes:
    directory = Path(directory)
    destination = directory / el.FILENAME
    if directory.is_symlink() or not directory.is_dir() or destination.is_symlink() or len(body) > el.MAX_BYTES:
        raise ValueError('MACRO_EVIDENCE_OUTPUT_INVALID')
    with tempfile.NamedTemporaryFile(dir=directory, prefix='.macro-evidence-', delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(body)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return body


def emit_empty(directory, *, now=_utc_now):
    """Offline/PR builds: a NOT_AVAILABLE copy without source data, replaced by the daily or preserve step."""
    return write_bytes(directory, el.encode(el.empty_payload(now())))


def _summary(payload) -> None:
    for sid, row in payload['series'].items():
        print('MACRO_EVIDENCE series=%s state=%s reason=%s obs=%d revised_periods=%d' % (
            sid, row['state'], row['reason'] or '-', len(row['obs']), len(row['history'])))
    print('MACRO_EVIDENCE state=%s previous=%s continuity=%s releases=%d events=%d replay_events=%d' % (
        payload['state'], payload['previous'], payload['continuity'], len(payload['releases']), len(payload['events']),
        len(payload['replay_events'])))


def run_from_capture(directory, root, manifest, *, environ, now=_utc_now, open_previous=None, transport=None,
                     previous=None) -> int:
    """Collect, merge with the previous Pages copy and write `macro-evidence.json` into `directory`. Returns 0 even when
    sources fail (reason codes are published); 1 only when nothing could be written."""
    try:
        from investment_system.providers.macro_evidence_collection import collect_macro_evidence
        diagnostics = []
        kwargs = {'transport': transport} if transport is not None else {}
        captures = collect_macro_evidence(root, manifest, environ=environ, diagnostics=diagnostics, **kwargs)
        for d in diagnostics:
            print('MACRO_EVIDENCE_FETCH stage=%s code=%s http=%s size=%s' % tuple(
                (d.get(k) if d.get(k) is not None else '-') for k in ('stage', 'code', 'http', 'size')))
        prior, state = previous if previous is not None else load_previous(open_previous)
        payload = el.build(captures, previous=prior, previous_state=state, now=now())
        write_bytes(directory, el.encode(payload))
        _summary(payload)
        return 0
    except Exception:
        print('MACRO_EVIDENCE BUILD_FAILED nothing_written')
        return 1


def preserve(out, *, open_previous=None) -> int:
    try:
        previous, body = previous_copy(open_previous)
    except ValueError:
        print('MACRO_EVIDENCE PREVIOUS_DISCARDED')
        return 0
    except Exception:
        print('MACRO_EVIDENCE PREVIOUS_FETCH_FAILED nothing_written')
        return 0
    if previous is None:
        print('MACRO_EVIDENCE PREVIOUS_NOT_AVAILABLE')
        return 0
    try:
        write_bytes(out, body)
    except Exception:
        print('MACRO_EVIDENCE OUTPUT_FAILED')
        return 1
    print('MACRO_EVIDENCE PREVIOUS_RESTORED state=%s events=%d' % (previous['state'], len(previous['events'])))
    return 0


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--preserve-only', action='store_true')
    args = parser.parse_args(argv)
    if not args.preserve_only:
        print('MACRO_EVIDENCE PRESERVE_ONLY_REQUIRED (daily collection runs inside public_screens_pipeline.py --macro-evidence)')
        return 2
    return preserve(args.out)


if __name__ == '__main__':
    raise SystemExit(main())
