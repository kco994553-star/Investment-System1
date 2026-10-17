#!/usr/bin/env python3
"""Serve the frontend at /app/ and a public-data directory at / (the layout of the Pages cockpit).

The app reads public JSON one level up from its page (<meta name="data-base" content="../">), so serving a cockpit build
(implementation/tools/build_pages_cockpit.py --out DIR) or a fixture directory at / reproduces the deployed layout.
Local only: binds 127.0.0.1, read-only GET/HEAD.

    python implementation/frontend/tools/dev_server.py --data /path/to/public-dir [--port 8994]
"""
from __future__ import annotations

import argparse
import functools
import http.server
import os
from pathlib import Path

APP = Path(__file__).resolve().parents[1]


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, data_dir: Path, **kwargs):
        self.data_dir = data_dir
        super().__init__(*args, directory=str(data_dir), **kwargs)

    def translate_path(self, path: str) -> str:
        clean = path.split('?', 1)[0].split('#', 1)[0]
        if clean == '/app' or clean.startswith('/app/'):
            rel = clean[len('/app'):].lstrip('/') or 'index.html'
            target = (APP / rel).resolve()
            if APP not in target.parents and target != APP:
                return str(APP / '__denied__')
            return str(target)
        return super().translate_path(path)

    def end_headers(self) -> None:
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:  # quiet by default
        if os.environ.get('FRONTEND_DEV_LOG'):
            super().log_message(fmt, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path, help='directory served at / (public JSON files)')
    parser.add_argument('--port', type=int, default=8994)
    args = parser.parse_args()
    data_dir = args.data.resolve()
    if not data_dir.is_dir():
        raise SystemExit('data directory not found')
    handler = functools.partial(Handler, data_dir=data_dir)
    with http.server.ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
        print(f'frontend: http://127.0.0.1:{args.port}/app/')
        server.serve_forever()


if __name__ == '__main__':
    main()
