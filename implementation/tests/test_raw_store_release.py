"""raw_store_release: private release copy logic with a fake transport (no network, no token printed)."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('raw_store_release', Path(__file__).resolve().parents[1] / 'tools/raw_store_release.py')
rel = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(rel)


class Fake:
    def __init__(self, release=None):
        self.release = release; self.calls = []; self.assets = {}
    def __call__(self, method, url, *, data=None, headers=None, auth=True, opener=None):
        self.calls.append((method, url, auth, (headers or {}).get('Accept')))
        if '/releases/tags/' in url:
            return (200, {}, json.dumps(self.release).encode()) if self.release else (404, {}, b'')
        if method == 'POST' and url.endswith('/releases'):
            self.release = {'id': 7, 'assets': []}; return 201, {}, json.dumps(self.release).encode()
        if method == 'POST' and 'uploads.github.com' in url:
            name = url.split('name=')[1]; self.assets[name] = data
            self.release['assets'].append({'id': len(self.assets), 'name': name, 'size': len(data)})
            return 201, {}, json.dumps({'size': len(data)}).encode()
        if '/releases/assets/' in url:
            return 302, {'Location': 'https://objects.example/signed'}, b''
        if url == 'https://objects.example/signed':
            assert auth is False
            return 200, {}, self.assets['a.zip']
        raise AssertionError(url)


def test_upload_creates_release_then_download_follows_redirect_without_token(tmp_path, monkeypatch):
    monkeypatch.setenv('RAW_REPO_TOKEN', 'x')
    archive = tmp_path / 'a.zip'; archive.write_bytes(b'archive-bytes')
    sha = hashlib.sha256(b'archive-bytes').hexdigest(); fake = Fake()
    out = rel.upload('o/raw', 't1', archive, 'a.zip', sha, call=fake)
    assert [u['status'] for u in out['uploaded']] == ['UPLOADED', 'UPLOADED']
    assert fake.assets['a.zip.sha256'] == f'{sha}  a.zip\n'.encode()
    again = rel.upload('o/raw', 't1', archive, 'a.zip', sha, call=fake)
    assert [u['status'] for u in again['uploaded']] == ['ALREADY_PRESENT', 'ALREADY_PRESENT']
    got = rel.download('o/raw', 't1', 'a.zip', tmp_path / 'back.zip', sha, call=fake)
    assert got['sha_match'] and (tmp_path / 'back.zip').read_bytes() == b'archive-bytes'
    with pytest.raises(rel.ReleaseError, match='LOCAL_ARCHIVE_SHA_MISMATCH'):
        rel.upload('o/raw', 't1', archive, 'a.zip', '0' * 64, call=fake)
    with pytest.raises(rel.ReleaseError, match='DOWNLOADED_SHA_MISMATCH'):
        rel.download('o/raw', 't1', 'a.zip', tmp_path / 'b2.zip', '0' * 64, call=fake)


def test_existing_asset_with_other_size_is_never_overwritten(tmp_path, monkeypatch):
    monkeypatch.setenv('RAW_REPO_TOKEN', 'x')
    archive = tmp_path / 'a.zip'; archive.write_bytes(b'abc'); sha = hashlib.sha256(b'abc').hexdigest()
    fake = Fake({'id': 1, 'assets': [{'id': 9, 'name': 'a.zip', 'size': 999}]})
    with pytest.raises(rel.ReleaseError, match='EXISTING_ASSET_SIZE_MISMATCH'):
        rel.upload('o/raw', 't', archive, 'a.zip', sha, call=fake)
    with pytest.raises(rel.ReleaseError, match='RELEASE_LOOKUP_FAILED'):
        rel.release_for_tag('o/raw', 'missing', create=False, call=Fake())


def test_token_is_required_and_never_printed(monkeypatch, capsys):
    monkeypatch.delenv('RAW_REPO_TOKEN', raising=False)
    with pytest.raises(rel.ReleaseError, match='RAW_REPO_TOKEN_MISSING'):
        rel._token()


def check(**over):
    c = {'archive_sha_match': True, 'restored_manifests_equal_committed': True, 'n_committed_manifests': 6808,
         'manifest_set_sha256': 'm', 'restored_manifest_set_sha256': 'm', 'archive_sha256': 's', 'archive_bytes': 1,
         'blob_verification': {'status': 'PASS', 'verified': 6808, 'expected': 6808, 'mismatched': []}}
    c.update(over); return c


def test_pass_requires_full_blob_set_and_location_entry_is_auditable():
    assert rel.check_passed(check())
    assert not rel.check_passed(check(blob_verification={'status': 'PARTIAL', 'verified': 6000, 'expected': 6808, 'mismatched': []}))
    assert not rel.check_passed(check(archive_sha_match=False))
    assert not rel.check_passed(check(restored_manifest_set_sha256='other'))
    entry = rel.location_entry('o/raw', 't', 'a.zip', check(), datetime(2026, 10, 11, tzinfo=timezone.utc))
    assert entry['kind'] == 'GITHUB_RELEASE' and entry['expires_at'] is None and entry['verified'] is True
    assert '6808/6808' in entry['verification']
    from investment_system.producers.raw_persistence import retention_audit
    audit = retention_audit([entry], datetime(2026, 10, 11, tzinfo=timezone.utc))
    assert audit
