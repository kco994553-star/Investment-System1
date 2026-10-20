"""Connect the merged public projection to Pages; raw captures stay temporary."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.product.public_engine_screens import generate_screen_bundle
from investment_system.universe import sec_qgv2 as qgv2
from public_sec_inputs import collect_public_inputs, CollectionFailure, Parser, STALE_AFTER_SECONDS, _print_collection, _print_diagnostics, _print_exclusions, parse, require_public_inputs
import preserve_public_sec_inputs

# Daily acquisition cadence, not a model or calibration threshold (published in sec-public-inputs.json /4 as the file's
# stale_after_seconds).
ACQUISITION_TTL = timedelta(seconds=STALE_AFTER_SECONDS)

def emit(directory, manifest=None, input_root=None, as_of=None):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('PUBLIC_SCREENS_OUTPUT_INVALID')
    outputs = generate_screen_bundle(manifest=manifest or {'schema_version':1,'sec':[],'macro':[],'thirteen_f':[]},
        input_root=Path(input_root or directory), as_of=as_of or datetime.now(timezone.utc), stale_after=ACQUISITION_TTL)
    for name in outputs:
        if (directory / name).is_symlink():
            raise ValueError('PUBLIC_SCREENS_OUTPUT_INVALID')
    prepared = []
    try:
        for name, payload in outputs.items():
            with tempfile.NamedTemporaryFile(dir=directory, delete=False) as handle:
                path = Path(handle.name)
                prepared.append((path, directory / name))
                handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False).encode())
        for path, destination in prepared:
            path.replace(destination)
    finally:
        for path, _ in prepared:
            path.unlink(missing_ok=True)
    return outputs

def _write_staged(directory, rows, now):
    payload = qgv2.merge(None, {}, as_of=now or datetime.now(timezone.utc), shard_index=None, target_updates=rows)
    body = qgv2.encode(payload)
    with tempfile.NamedTemporaryFile(dir=directory, prefix='.sec-qgv2-', delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(body)
    try:
        temporary.replace(Path(directory) / qgv2.FILENAME)
    finally:
        temporary.unlink(missing_ok=True)
    return payload


def withdrawn_companies(directory):
    """{company_id: detected_at} of the WITHDRAWN rows (identity conflicts, new or kept) of the sec-public-inputs.json /4
    this run wrote, read back through its strict validator ({} when absent, older or invalid)."""
    try:
        payload = json.loads((Path(directory) / 'sec-public-inputs.json').read_bytes())
        require_public_inputs(payload)
    except Exception:
        return {}
    return {row['company_id']: row['detected_at'] for row in payload['companies'] if row.get('status') == 'WITHDRAWN'}


def stage_qgv2_target(directory, manifest, root, *, now=None, withdrawn=None):
    """QGV v2 Q·G for the TARGET US SEC issuers from this run's SEC bytes, staged as `sec-qgv2.json`.

    Universe rows stay NOT_COLLECTED here; the Universe shard step (tools/sec_universe_shares.py) later merges these
    TARGET rows with the published Universe rows and recomputes every percentile. `withdrawn` ({company_id: detected_at},
    sec-public-inputs.json WITHDRAWN rows) are staged as withdrawal rows: the shard merge then withdraws the kept TARGET
    row of that issuer (never carried, never a fallback). When the rows from bytes cannot be staged, the withdrawals
    alone still are. A failure prints a fixed code only and never changes the six screen files."""
    directory = Path(directory)
    withdrawals = {}
    try:
        withdrawals = {cid: qgv2.withdrawn_target(cid, at) for cid, at in sorted((withdrawn or {}).items())}
        destination = directory / qgv2.FILENAME
        if directory.is_symlink() or not directory.is_dir() or destination.is_symlink():
            raise ValueError('SEC_QGV2_OUTPUT_INVALID')
        entries = []
        for entry in manifest['sec']:
            if entry['synthetic']:
                continue
            entries.append((entry['company_id'], (Path(root) / entry['companyfacts']).read_bytes(),
                            (Path(root) / entry['submissions']).read_bytes(), datetime.fromisoformat(entry['acquired_at'])))
        rows = qgv2.build_target_rows(entries)
        rows.update(withdrawals)
        payload = _write_staged(directory, rows, now)
        staged = [r for r in payload['target'].values() if r['state'] != 'NOT_AVAILABLE']
        print(f'SEC_QGV2_TARGET staged companies={len(entries)} with_data={len(staged)} withdrawn={len(withdrawals)}')
        return payload
    except Exception:
        pass
    try:
        if withdrawals and not directory.is_symlink() and directory.is_dir() and not (directory / qgv2.FILENAME).is_symlink():
            payload = _write_staged(directory, withdrawals, now)
            print(f'SEC_QGV2_TARGET STAGE_FAILED withdrawn_only={len(withdrawals)}')
            return payload
    except Exception:
        pass
    print('SEC_QGV2_TARGET STAGE_FAILED')
    return None


def load_previous_inputs(*, open_response=None):
    """(validated live sec-public-inputs.json payload (/3 or /4) or None, LOADED | NO_LIVE | UNAVAILABLE). A failed read
    only turns preservation off for this run (the pre-deploy freshness guard still compares with the live copy); the
    state is published in the /4 `collection.previous` field."""
    try:
        payload = preserve_public_sec_inputs.fetch_previous(open_response=open_response)
    except Exception:
        return None, 'UNAVAILABLE'
    return payload, 'LOADED' if payload is not None else 'NO_LIVE'


def collect(directory, *, environ=None, client_factory=None, macro_v0=None, macro_curve=None, previous=None,
            previous_state=None, now=None, macro_evidence=None):
    if client_factory is None:
        from investment_system.providers.sec_collection import SecCollectionClient
        client_factory = SecCollectionClient
    with tempfile.TemporaryDirectory(prefix='sec-private-capture-') as private:
        root = Path(private)
        manifest = {'schema_version':1,'sec':[],'macro':[],'thirteen_f':[]}
        if macro_v0 is not None:
            # Government macro statistics (not prices); raw bodies stay in this private directory.
            manifest['macro_v0'] = macro_v0(root)
        if macro_curve is not None:
            # Treasury daily par yield curve (government statistics, macro lights v1); raw XML stays private here.
            manifest['macro_curve_v1'] = macro_curve(root)
        if macro_evidence is not None:
            # Macro evidence lines (exploration only, MEV-10): reuses the macro files above from this private directory
            # and writes only macro-evidence.json. Any failure prints a fixed code and never stops the SEC collection.
            try:
                macro_evidence(root, manifest)
            except Exception:
                print('MACRO_EVIDENCE BUILD_FAILED nothing_written')
        class Capture:
            def __init__(self, agent):
                self.client = client_factory(agent)
            def collect(self, company, cik):
                facts, submissions, acquired = self.client.collect(company, cik)
                parse(facts, cik); parse(submissions, cik)
                if not isinstance(acquired, datetime) or acquired.utcoffset() is None:
                    raise ValueError('SEC_ACQUISITION_TIMESTAMP_INVALID')
                paths = {}
                for kind, body in [('companyfacts', facts), ('submissions', submissions)]:
                    name = company + '-' + kind + '.json'
                    (root / name).write_bytes(body)
                    paths[kind] = name
                manifest['sec'].append(dict(company_id=company, **paths,
                    acquired_at=acquired.astimezone(timezone.utc).isoformat(), synthetic=False))
                return facts, submissions, acquired
        result = collect_public_inputs(Path(directory) / 'sec-public-inputs.json', environ=environ, client_factory=Capture,
                                       previous=previous, previous_state=previous_state, now=now)
        emit(directory, manifest, root)
        stage_qgv2_target(directory, manifest, root, withdrawn=withdrawn_companies(directory))
        return result

def _print_macro_v0(directory):
    # States and fixed reason codes only: no URL, setting or provider message.
    try:
        data = json.loads((Path(directory) / 'macro-screen.json').read_text())['data']
        block, raw = data['growth_inflation_v0'], data['raw_axes_v0']
        for axis, row in list(block['axes'].items()) + list(raw['axes'].items()):
            print('MACRO_V0 axis=%s state=%s reasons=%s' % (axis, row['state'], ','.join(row['reason_codes']) or '-'))
        print('MACRO_V0 engine=%s regime=%s raw_regime=%s' % (block['engine']['state'], block['regime']['state'], raw['regime']['state']))
    except Exception:
        print('MACRO_V0 summary=NOT_AVAILABLE')
    # Public lights only (employment, inflation, curve): state, on/off and fixed reason codes; no values.
    try:
        lights = json.loads((Path(directory) / 'macro-screen.json').read_text())['data']['macro_lights_v1']['lights']
        for name, row in lights.items():
            print('MACRO_V1_LIGHT light=%s state=%s lit=%s reason=%s' % (name, row['state'], {True: 'ON', False: 'OFF', None: 'NO_DATA'}[row['lit']], row['reason']))
    except Exception:
        print('MACRO_V1_LIGHT summary=NOT_AVAILABLE')

def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--macro-evidence', action='store_true', help='with --live --macro-v0, also write macro-evidence.json (MEV-1 P1 13 evidence lines, exploration only)')
    parser.add_argument('--macro-v0', action='store_true', help='with --live, also collect the macro v0 official series (BLS CUUR0000SA0+LNS14000000, BEA T10101 line 1, Fed H.15/H.4.1/H.8 DDP CSV, Treasury MTS Table 1) and the Treasury daily par yield curve XML for the macro lights v1')
    args = parser.parse_args(argv)
    try:
        if args.live:
            macro_v0 = macro_curve = None
            if args.macro_v0:
                from investment_system.providers.macro_v0_collection import collect_macro_v0, collect_treasury_curve
                macro_diagnostics = []

                def macro_v0(root):
                    entries = collect_macro_v0(root, environ=os.environ, diagnostics=macro_diagnostics)
                    # Fixed tokens only (status number, content/size class, DDP rel and the first 8 hex of the public package id).
                    for d in macro_diagnostics:
                        print('MACRO_V0_FETCH axis=%s stage=%s code=%s http=%s content=%s size=%s rel=%s series=%s type=%s' % tuple(
                            (d.get(k) if d.get(k) is not None else '-') for k in ('axis', 'stage', 'code', 'http', 'content', 'size', 'rel', 'series8', 'type')))
                    return entries

                def macro_curve(root):
                    curve_diagnostics = []
                    entries = collect_treasury_curve(root, diagnostics=curve_diagnostics)
                    for d in curve_diagnostics:
                        print('MACRO_V1_CURVE_FETCH stage=%s code=%s http=%s content=%s size=%s' % tuple(
                            (d.get(k) if d.get(k) is not None else '-') for k in ('stage', 'code', 'http', 'content', 'size')))
                    return entries
            macro_evidence = None
            if args.macro_v0 and args.macro_evidence:
                import macro_evidence as evidence_tool

                def macro_evidence(root, manifest):
                    evidence_tool.run_from_capture(args.out, root, manifest, environ=os.environ)
            previous, previous_state = load_previous_inputs()
            result = collect(args.out, macro_v0=macro_v0, macro_curve=macro_curve, previous=previous,
                             previous_state=previous_state, macro_evidence=macro_evidence)
            _print_diagnostics(result['diagnostics']); _print_exclusions(result['exclusions'])
            _print_collection(result, previous_state)
            if args.macro_v0:
                _print_macro_v0(args.out)
            print(f"SEC_PUBLIC_BUILD_OK failed_companies={result['failed_companies']}")
        else:
            emit(args.out)
    except CollectionFailure as error:
        _print_diagnostics(error.diagnostics); _print_exclusions(error.exclusions)
        print(f'SEC_PUBLIC_BUILD_FAILED failed_companies={error.failed_companies}')
        return 1
    except Exception:
        print('PUBLIC_SCREENS_BUILD_FAILED')
        return 1
    print('PUBLIC_SCREENS_OK files=6')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
