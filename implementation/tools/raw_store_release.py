#!/usr/bin/env python3
"""Copy the raw store archive to a PRIVATE GitHub Release asset and verify it (used by raw-store-private-release.yml).

Token: env RAW_REPO_TOKEN only (fine-grained PAT limited to the private raw repository). It is never printed.
Output: counts, sizes, sha256 and a storage_locations entry. No blob contents.

  require-pass --check restore_check.json
  upload       --repo OWNER/NAME --tag TAG --asset FILE --name NAME --expected-sha HEX
  download     --repo OWNER/NAME --tag TAG --name NAME --out FILE --expected-sha HEX
  location     --repo OWNER/NAME --tag TAG --name NAME --check restore_check.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

API = 'https://api.github.com'
UPLOADS = 'https://uploads.github.com'


class ReleaseError(RuntimeError):
    pass


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _token() -> str:
    token = os.environ.get('RAW_REPO_TOKEN', '')
    if not token:
        raise ReleaseError('RAW_REPO_TOKEN_MISSING')
    return token


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # handle redirects explicitly (never forward the token)
        return None


def http(method: str, url: str, *, data: bytes | None = None, headers: dict | None = None, auth: bool = True,
         opener=None):
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Accept', (headers or {}).pop('Accept', 'application/vnd.github+json'))
    req.add_header('X-GitHub-Api-Version', '2022-11-28')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if auth:
        req.add_header('Authorization', 'Bearer ' + _token())
    opener = opener or urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=600) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read() if e.fp else b''


def release_for_tag(repo: str, tag: str, *, create: bool, call=http) -> dict:
    status, _, body = call('GET', f'{API}/repos/{repo}/releases/tags/{urllib.parse.quote(tag)}')
    if status == 200:
        return json.loads(body)
    if status != 404 or not create:
        raise ReleaseError(f'RELEASE_LOOKUP_FAILED http={status}')
    payload = json.dumps({'tag_name': tag, 'name': tag, 'draft': False, 'prerelease': False,
                          'body': 'Raw store archive copy (private). Verify with sha256 and verify_blobs.'}).encode()
    status, _, body = call('POST', f'{API}/repos/{repo}/releases', data=payload, headers={'Content-Type': 'application/json'})
    if status != 201:
        raise ReleaseError(f'RELEASE_CREATE_FAILED http={status}')
    return json.loads(body)


def upload(repo: str, tag: str, asset: Path, name: str, expected_sha: str, *, call=http) -> dict:
    actual = file_sha(asset)
    if actual != expected_sha:
        raise ReleaseError('LOCAL_ARCHIVE_SHA_MISMATCH')
    release = release_for_tag(repo, tag, create=True, call=call)
    existing = {a['name']: a for a in release.get('assets', [])}
    out = {'release_id': release['id'], 'uploaded': []}
    for asset_name, data, ctype in ((name, None, 'application/zip'),
                                    (name + '.sha256', f'{expected_sha}  {name}\n'.encode(), 'text/plain')):
        if asset_name in existing:
            if asset_name == name and existing[asset_name].get('size') != asset.stat().st_size:
                raise ReleaseError('EXISTING_ASSET_SIZE_MISMATCH')
            out['uploaded'].append({'name': asset_name, 'status': 'ALREADY_PRESENT'})
            continue
        body = data if data is not None else asset.read_bytes()
        url = f'{UPLOADS}/repos/{repo}/releases/{release["id"]}/assets?name={urllib.parse.quote(asset_name)}'
        status, _, resp = call('POST', url, data=body, headers={'Content-Type': ctype})
        if status != 201:
            raise ReleaseError(f'ASSET_UPLOAD_FAILED name={asset_name} http={status}')
        out['uploaded'].append({'name': asset_name, 'status': 'UPLOADED', 'size': json.loads(resp).get('size')})
    return out


def download(repo: str, tag: str, name: str, out: Path, expected_sha: str, *, call=http) -> dict:
    release = release_for_tag(repo, tag, create=False, call=call)
    asset = next((a for a in release.get('assets', []) if a['name'] == name), None)
    if asset is None:
        raise ReleaseError('ASSET_NOT_FOUND')
    status, headers, body = call('GET', f'{API}/repos/{repo}/releases/assets/{asset["id"]}',
                                 headers={'Accept': 'application/octet-stream'})
    if status in (301, 302, 303, 307, 308):
        location = headers.get('Location') or headers.get('location')
        if not location or urllib.parse.urlparse(location).scheme != 'https':
            raise ReleaseError('ASSET_REDIRECT_INVALID')
        status, _, body = call('GET', location, headers={'Accept': 'application/octet-stream'}, auth=False)
    if status != 200:
        raise ReleaseError(f'ASSET_DOWNLOAD_FAILED http={status}')
    out.write_bytes(body)
    actual = file_sha(out)
    if actual != expected_sha:
        raise ReleaseError('DOWNLOADED_SHA_MISMATCH')
    return {'bytes': out.stat().st_size, 'sha256': actual, 'sha_match': True}


def check_passed(check: dict) -> bool:
    blobs = check.get('blob_verification') or {}
    return (check.get('archive_sha_match') is True and check.get('restored_manifests_equal_committed') is True
            and blobs.get('status') == 'PASS' and blobs.get('verified') == blobs.get('expected') == check.get('n_committed_manifests')
            and not blobs.get('mismatched') and check.get('manifest_set_sha256') == check.get('restored_manifest_set_sha256'))


def location_entry(repo: str, tag: str, name: str, check: dict, now: datetime) -> dict:
    blobs = check['blob_verification']
    return {'kind': 'GITHUB_RELEASE', 'ref': f'private repository {repo} release {tag} asset {name}',
            'archive_sha256': check['archive_sha256'], 'archive_bytes': check['archive_bytes'], 'expires_at': None,
            'complete_blobs': True, 'verified': check_passed(check),
            'verification': f"downloaded back from the release; sha256 match; verify_blobs {blobs['status']} "
                            f"{blobs['verified']}/{blobs['expected']}; manifest_set_sha256 {check['manifest_set_sha256']}",
            'verified_at': now.isoformat().replace('+00:00', 'Z')}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('require-pass'); s.add_argument('--check', required=True)
    for cmd in ('upload', 'download', 'location'):
        s = sub.add_parser(cmd)
        s.add_argument('--repo', required=True); s.add_argument('--tag', required=True); s.add_argument('--name', required=True)
        if cmd == 'upload':
            s.add_argument('--asset', required=True); s.add_argument('--expected-sha', required=True)
        if cmd == 'download':
            s.add_argument('--out', required=True); s.add_argument('--expected-sha', required=True)
        if cmd == 'location':
            s.add_argument('--check', required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'require-pass':
            check = json.loads(Path(a.check).read_text())
            blobs = check.get('blob_verification') or {}
            print(json.dumps({'archive_sha_match': check.get('archive_sha_match'), 'blob_status': blobs.get('status'),
                              'verified': blobs.get('verified'), 'expected': blobs.get('expected'),
                              'n_committed_manifests': check.get('n_committed_manifests')}))
            return 0 if check_passed(check) else 1
        if a.cmd == 'upload':
            print(json.dumps(upload(a.repo, a.tag, Path(a.asset), a.name, a.expected_sha)))
        elif a.cmd == 'download':
            print(json.dumps(download(a.repo, a.tag, a.name, Path(a.out), a.expected_sha)))
        else:
            entry = location_entry(a.repo, a.tag, a.name, json.loads(Path(a.check).read_text()), datetime.now(timezone.utc))
            print('### storage_locations entry\n\n```json\n' + json.dumps(entry, indent=1) + '\n```')
            return 0 if entry['verified'] else 1
        return 0
    except ReleaseError as e:
        print(str(e)); return 1


if __name__ == '__main__':
    raise SystemExit(main())
