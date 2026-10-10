"""Keep validated public projections across UI deployments, without raw inputs."""
from pathlib import Path
import tempfile
import urllib.error
import urllib.request
from preserve_public_sec_inputs import NoRedirect
from public_sec_inputs import Parser
import public_screens_pipeline  # Initialize the engine source path.
from investment_system.product.public_engine_screens import FILENAMES, parse_json, require_public_screen

BASE = 'https://kco994553-star.github.io/Investment-System1/'
MAX = 2 * 1024 * 1024

def preserve(directory, *, open_response=None):
    prepared = []
    try:
        directory = Path(directory)
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError
        fetch = open_response or urllib.request.build_opener(NoRedirect()).open
        bodies = {}
        for name in sorted(FILENAMES):
            if (directory / name).is_symlink():
                raise ValueError
            url = BASE + name
            request = urllib.request.Request(url, headers={'Accept':'application/json','Cache-Control':'no-cache'})
            try:
                with fetch(request, timeout=20) as response:
                    if response.status != 200 or response.geturl() != url:
                        raise ValueError
                    body = response.read(MAX + 1)
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    continue
                raise ValueError from None
            if len(body) > MAX:
                raise ValueError
            require_public_screen(name, parse_json(body))
            bodies[name] = body
        for name, body in bodies.items():
            with tempfile.NamedTemporaryFile(dir=directory, delete=False) as handle:
                path = Path(handle.name); prepared.append((path, directory / name)); handle.write(body)
        for path, destination in prepared:
            path.replace(destination)
        return len(bodies)
    except Exception:
        raise ValueError('PUBLIC_SCREENS_RESTORE_FAILED') from None
    finally:
        for path, _ in prepared:
            path.unlink(missing_ok=True)

def main(argv=None):
    parser = Parser(description=__doc__); parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        print(f'PUBLIC_SCREENS_RESTORED files={preserve(args.out)}')
    except ValueError:
        print('PUBLIC_SCREENS_RESTORE_FAILED'); return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
