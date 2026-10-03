"""Producer interface and registry. No scheduling is activated here.

A producer receives a ProduceRequest (requested_as_of + explicit evaluation clock) and returns a
PRODUCER_SNAPSHOT v1. Each snapshot distinguishes requested_as_of, actual data as_of,
generated_at and expires_at. Sections without a real producer are registered as explicit
NOT_AVAILABLE producers that carry the audit blocker; nothing is fabricated.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from ..product.web_mvp import ROOT, repository_bundle
from .contract import SECTION_NAMES, make_snapshot, not_available, validate_snapshot
from .errors import IdentityError
from .freshness import require_aware
from .serialization import sha256_hex

INFRA_VERSION = 'PRODUCER_INFRA_V1'
DEFAULT_REASON = '운영 Snapshot이 연결되지 않았습니다.'  # identical to web_mvp.repository_bundle


@dataclass(frozen=True)
class ProduceRequest:
    requested_as_of: datetime
    now: datetime

    def __post_init__(self):
        require_aware(self.requested_as_of)
        require_aware(self.now)


class Producer(Protocol):
    producer_id: str
    section: str
    cadence: str

    def produce(self, request: ProduceRequest) -> dict: ...


@dataclass(frozen=True)
class UnavailableProducer:
    section: str
    reason_code: str
    blocker: str
    producer_id: str = ''
    cadence: str = 'NOT_SCHEDULED'

    def produce(self, request: ProduceRequest) -> dict:
        return validate_snapshot(not_available(
            self.section, self.producer_id or f'{self.section}.unavailable', INFRA_VERSION,
            request.now.isoformat(), DEFAULT_REASON, self.reason_code, request.requested_as_of.isoformat(),
            {'id': 'NONE', 'version': 'NONE', 'status': 'NOT_AVAILABLE', 'blocker': self.blocker}))


@dataclass(frozen=True)
class FrozenUniverseProducer:
    """Track A FROZEN_VERIFIED Official Universe, loaded through the existing hash-verified
    web_mvp.repository_bundle() path. Point-in-time; never presented as current."""
    producer_id: str = 'track_a.official_universe.frozen'
    section: str = 'universe'
    cadence: str = 'FROZEN (new as_of requires gate chain + CA review; interim policy = PROPOSAL_P02)'
    snapshot_file: str = 'reports/gate_evidence/official_snapshot_2024-12-31.json'
    manifest_file: str = 'reports/gate_evidence/track_a_freeze_readiness_2026-09-27.json'

    def companies(self) -> list[dict]:
        return repository_bundle()['companies']

    def produce(self, request: ProduceRequest) -> dict:
        b = repository_bundle()  # raises on frozen hash / identity mismatch
        u = b['universe']['data']
        manifest = json.loads((ROOT / self.manifest_file).read_text())
        inputs = [{'artifact_id': 'file:' + f, 'sha256': sha256_hex((ROOT / f).read_bytes()),
                   'bytes': (ROOT / f).stat().st_size} for f in (self.snapshot_file, self.manifest_file)]
        snap = make_snapshot(
            producer_id=self.producer_id, producer_version=manifest['validated_source_commit'],
            section='universe', data_state='FROZEN_SNAPSHOT',
            as_of=datetime.fromisoformat(u['as_of'] + 'T00:00:00+00:00').isoformat(),
            requested_as_of=request.requested_as_of.isoformat(), generated_at=request.now.isoformat(),
            methodology={'id': u['kind'], 'version': u['universe_kind'], 'status': manifest['status']},
            synthetic=False,
            provenance={'source': b['universe']['source'], 'inputs': inputs,
                        'universe_id': u['universe_id'], 'gate_evidence': u['gate_evidence']},
            validation={'status': 'PASS', 'checks': ['freeze_manifest_sha256_match', 'universe_id_match']},
            data=u)
        return validate_snapshot(snap)


# Audit blockers (implementation/reports/producer_readiness_audit_2026-10-01.md §7).
DEFAULT_UNAVAILABLE = {
    'qgv': ('QGV_RESEARCH_ONLY_NO_EXPORT', 'B1/B2: per-company snapshots not persisted; PROVISIONAL_RESEARCH not publishable (P01)'),
    'technical': ('TECHNICAL_NO_REAL_MODEL', 'B3: engine is v0.6 structural placeholder (synthetic)'),
    'macro': ('MACRO_SHAPE_INCOMPATIBLE', 'B4: synthetic-flagged output; Web reads indicators/exposures'),
    'portfolio': ('PORTFOLIO_NO_ACTUAL_HOLDINGS', 'B5/B6: Track B P1+ not started; Official profiles need Track C'),
    'leaderboard': ('LEADERBOARD_NO_UPSTREAM_QGV', 'B1: depends on persisted QGV snapshots'),
    'news': ('NEWS_NO_SOURCE', 'B7: no news source/ingestion; provider not selected'),
    'relationships': ('RELATIONSHIPS_OUT_OF_BUNDLE', 'B7: reviewed Track D page via web_mvp --rig-page only'),
    'changes': ('CHANGES_NO_PRODUCER', 'no producer defined'),
}


@dataclass
class ProducerRegistry:
    producers: dict = field(default_factory=dict)

    def register(self, producer) -> None:
        if producer.section not in SECTION_NAMES:
            raise IdentityError(f'unknown section {producer.section!r}')
        self.producers[producer.section] = producer

    def describe(self) -> dict:
        return {s: {'producer_id': getattr(p, 'producer_id', None) or f'{s}.unavailable',
                    'kind': type(p).__name__, 'cadence': p.cadence,
                    'blocker': getattr(p, 'blocker', None)} for s, p in sorted(self.producers.items())}

    def run(self, request: ProduceRequest) -> dict:
        out = {}
        for section in SECTION_NAMES:
            p = self.producers.get(section) or UnavailableProducer(section, 'NO_PRODUCER_REGISTERED', 'none registered')
            snap = validate_snapshot(p.produce(request))
            if snap['section'] != section:
                raise IdentityError(f'producer for {section} emitted section {snap["section"]}')
            out[section] = snap
        return out


def default_registry() -> ProducerRegistry:
    r = ProducerRegistry()
    r.register(FrozenUniverseProducer())
    for section, (code, blocker) in DEFAULT_UNAVAILABLE.items():
        r.register(UnavailableProducer(section, code, blocker))
    return r
