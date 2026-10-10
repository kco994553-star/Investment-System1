"""Connect the merged public projection to Pages; raw captures stay temporary."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.product.public_engine_screens import generate_screen_bundle
from public_sec_inputs import collect_public_inputs, CollectionFailure, Parser, _print_diagnostics, _print_exclusions, parse

# Daily acquisition cadence, not a model or calibration threshold.
ACQUISITION_TTL = timedelta(hours=24)

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

def collect(directory, *, environ=None, client_factory=None):
    if client_factory is None:
        from investment_system.providers.sec_collection import SecCollectionClient
        client_factory = SecCollectionClient
    with tempfile.TemporaryDirectory(prefix='sec-private-capture-') as private:
        root = Path(private)
        manifest = {'schema_version':1,'sec':[],'macro':[],'thirteen_f':[]}
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
        result = collect_public_inputs(Path(directory) / 'sec-public-inputs.json', environ=environ, client_factory=Capture)
        emit(directory, manifest, root)
        return result

def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.live:
            result = collect(args.out)
            _print_diagnostics(result['diagnostics']); _print_exclusions(result['exclusions'])
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
    print('PUBLIC_SCREENS_OK files=5')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
