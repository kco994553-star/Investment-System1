"""Write tools/fixtures/empty_public_screens.json: the NOT_AVAILABLE public screens of an offline build (fixed as_of).

Browser tests that check the empty state serve these through route interception, so they behave the same on a PR build
(no SEC data) and on the SEC daily / UI dispatch builds (live public data). Usage: python tools/empty_public_screens.py [--check]
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
import build_pages_cockpit  # noqa: E402

OUT = ROOT / 'tools/fixtures/empty_public_screens.json'
AS_OF = '2026-01-01T00:00:00+00:00'
# Files every build carries regardless of SEC/government collection; everything else is a public screen sidecar.
STATIC = {'data.json', 'entities.json', 'actual-catalog.json', 'manifest.json', 'sec-m2-candidates.json', 'universe-codes.json', 'universe-domains.json', 'company-logos.json'}


def build():
    """Every JSON sidecar of an offline build, with the top-level as_of fixed so the fixture is reproducible."""
    with tempfile.TemporaryDirectory() as d:
        site = Path(d) / 'site'
        site.mkdir()
        build_pages_cockpit.build_public_cockpit(site)
        outputs = {}
        for path in sorted(site.glob('*.json')):
            if path.name in STATIC:
                continue
            payload = json.loads(path.read_text())
            if isinstance(payload, dict) and 'as_of' in payload:
                payload['as_of'] = AS_OF
            outputs[path.name] = payload
    return json.dumps(outputs, sort_keys=True, ensure_ascii=True, allow_nan=False, indent=1) + '\n'


def main(argv):
    text = build()
    if '--check' in argv:
        ok = OUT.exists() and OUT.read_text() == text
        print('EMPTY_PUBLIC_SCREENS_OK' if ok else 'EMPTY_PUBLIC_SCREENS_STALE')
        return 0 if ok else 1
    OUT.write_text(text)
    print('wrote', OUT.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
