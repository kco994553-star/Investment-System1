"""Preserve an already public, validated SEC sidecar across UI-only Pages deploys."""
from __future__ import annotations

import json
from pathlib import Path
import os
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from public_sec_inputs import FILENAME, MAX_BYTES, Parser, require_public_inputs, unique

SOURCE = 'https://kco994553-star.github.io/Investment-System1/sec-public-inputs.json'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def preserve(directory, *, open_response=None):
    temporary = None
    try:
        directory = Path(directory)
        destination = directory / FILENAME
        if directory.is_symlink() or not directory.is_dir() or destination.is_symlink():
            raise ValueError
        request = urllib.request.Request(SOURCE, headers={'Accept':'application/json', 'Cache-Control':'no-cache'})
        open_response = open_response or urllib.request.build_opener(NoRedirect()).open
        try:
            with open_response(request, timeout=20) as response:
                if response.status != 200 or response.geturl() != SOURCE:
                    raise ValueError
                body = response.read(MAX_BYTES + 1)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return 'SEC_PREVIOUS_NOT_AVAILABLE'
            raise ValueError from None
        if len(body) > MAX_BYTES:
            raise ValueError
        def invalid_constant(_):
            raise ValueError
        payload = json.loads(body.decode('utf-8', errors='strict'), object_pairs_hook=unique, parse_constant=invalid_constant)
        require_public_inputs(payload)
        # Keep the original validated bytes; no recalculation or new collection.
        with tempfile.NamedTemporaryFile(dir=directory, prefix='.sec-previous-', delete=False) as output:
            temporary = Path(output.name)
            output.write(body)
        os.replace(temporary, destination)
        temporary = None
        return 'SEC_PREVIOUS_RESTORED'
    except Exception:
        raise ValueError('SEC_PREVIOUS_RESTORE_FAILED') from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        print(preserve(args.out))
    except ValueError:
        print('SEC_PREVIOUS_RESTORE_FAILED')
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
