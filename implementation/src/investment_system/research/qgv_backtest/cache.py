"""Versioned preparation cache with current rights and private-path checks."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def dependency_fingerprint():
    """Include actual operational scoring code/config, not just the adapter."""
    research = Path(__file__).parent
    package = research.parents[1]
    paths = list(research.glob('*.py'))
    for root in (package/'qgv', package/'contracts'):
        paths.extend(p for p in root.rglob('*') if p.suffix in ('.py','.json') and p.is_file())
    fingerprint = hashlib.sha256()
    for path in sorted(set(paths)):
        fingerprint.update(str(path.relative_to(package)).encode())
        fingerprint.update(path.read_bytes())
    return fingerprint.hexdigest()


def check_rights(rights, now):
    try:
        expires = datetime.fromisoformat(rights['expires_at'].replace('Z','+00:00'))
        if expires.tzinfo is None:
            raise ValueError('naive expiry')
        valid = (bool(rights.get('receipt')) and rights.get('revoked') is False
                 and all(rights.get(k) is True for k in ('research','ai_processing','storage','derived_storage'))
                 and now < expires)
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise PermissionError('CACHE_RIGHTS_NOT_CURRENT')


class PreparationCache:
    """No persistent storage by default; scopes identify PIT/scores/selection.

    Dependencies must be cost-independent for these scopes. NAVs remain in the
    runner's separate, cost-specific immutable result contract. Every access,
    including an in-process hit, checks the current persistent-storage grant.
    """
    def __init__(self, root=None, *, private_root=None, rights=None, clock=None):
        self.root = Path(root) if root else None
        self.private_root = Path(private_root) if private_root else None
        self.rights = rights
        self.clock = clock or (lambda:datetime.now(timezone.utc))
        self.memory = {}
        self.stats = dict(hits=0, misses=0, writes=0)

    def key(self, scope, dependencies):
        if scope not in ('pit','scores','selection','factor_inputs'):
            raise ValueError('UNKNOWN_PREPARATION_SCOPE')
        return digest(dict(cache_version='qgv-preparation/1',scope=scope,dependencies=dependencies))

    def _guard(self):
        if self.root is None:
            return
        check_rights(self.rights, self.clock())
        checkout = Path(__file__).resolve().parents[5]
        private = self.private_root.resolve() if self.private_root else None
        resolved = self.root.resolve()
        if (private is None or private.is_relative_to(checkout) or not resolved.is_relative_to(private)
                or resolved == private or resolved != self.root.absolute()):
            raise PermissionError('PRIVATE_CACHE_DESTINATION_REQUIRED')

    def get_or_compute(self, scope, dependencies, factory):
        self._guard()
        key = self.key(scope, dependencies)
        if key in self.memory:
            self.stats['hits'] += 1
            return deepcopy(self.memory[key])
        path = self.root/f'{key}.json' if self.root else None
        if path and (path.exists() or path.is_symlink()):
            descriptor = os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(descriptor) as handle:
                record = json.load(handle)
            if record.get('key') != key or record.get('payload_sha256') != digest(record.get('payload')):
                raise ValueError('CACHE_INTEGRITY_FAILED')
            value = record['payload']
            self.stats['hits'] += 1
        else:
            self.stats['misses'] += 1
            value = factory()
            # Validate JSON serializability and reject NaN before any write.
            payload_hash = digest(value)
            if path:
                self._guard()
                self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
                self.root.chmod(0o700)
                temporary = path.with_suffix(f'.{os.getpid()}.tmp')
                descriptor = os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                try:
                    with os.fdopen(descriptor,'w') as handle:
                        json.dump(dict(key=key,payload=value,payload_sha256=payload_hash),handle,sort_keys=True,separators=(',',':'),allow_nan=False)
                        handle.flush()
                        os.fsync(handle.fileno())
                    # Link publishes a complete immutable entry without ever
                    # replacing another worker's entry or following a symlink.
                    os.link(temporary,path)
                    self.stats['writes'] += 1
                finally:
                    temporary.unlink(missing_ok=True)
        self.memory[key] = deepcopy(value)
        return deepcopy(value)
