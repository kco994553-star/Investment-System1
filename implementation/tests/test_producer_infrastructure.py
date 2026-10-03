"""Producer Infrastructure v1: contract, freshness, provenance, assembly, persistence.

Test-local LIVE payloads below are contract fixtures only; they are never exported or registered.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile

import pytest

from investment_system.contracts.models import MacroSnapshot
from investment_system.macro.engine import MacroEngine
from investment_system.product.web_mvp import ROOT, build, repository_bundle, validate_bundle
from investment_system.producers import adapters
from investment_system.producers.assembler import assemble_bundle, bundle_sha256, write_bundle_atomic
from investment_system.producers.contract import (file_resolver, make_snapshot, not_available, validate_snapshot,
                                                  verify_inputs)
from investment_system.producers.errors import (FreshnessContractError, IdentityError, IncompatibleShapeError,
                                                MissingFieldError, ProducerContractError, ProvenanceError,
                                                ResearchStatusError, SchemaVersionError, SourceHashError,
                                                SyntheticStateError, TimestampError, UnsupportedStateError,
                                                ValidationStatusError)
from investment_system.producers.freshness import FRESH, NOT_APPLICABLE, NOT_USABLE, STALE, classify
from investment_system.producers.raw_persistence import artifact_records, manifest_set_sha256, retention_audit
from investment_system.producers.registry import FrozenUniverseProducer, ProduceRequest, default_registry
from investment_system.producers.serialization import canonical_bytes, canonical_sha256
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.providers.catalog import iter_official_raw
from investment_system.technical.engine import TechnicalEngine

NOW = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
H = '0' * 64


def companies():
    return FrozenUniverseProducer().companies()


def live(**over):
    cid = companies()[0]['company_id']
    kw = dict(producer_id='test.technical', producer_version='t1', section='technical', data_state='LIVE',
              as_of='2026-10-01T00:00:00+00:00', requested_as_of='2026-10-01T00:00:00+00:00',
              generated_at='2026-10-01T01:00:00+00:00', expires_at='2026-10-02T00:00:00+00:00',
              methodology={'id': 'TEST', 'version': '1', 'status': 'VALIDATED'}, synthetic=False,
              provenance={'source': 'test fixture', 'inputs': [{'artifact_id': 'raw:x', 'sha256': H}]},
              validation={'status': 'PASS', 'checks': ['test']}, scope_kind='ENTITY_MAP',
              data={cid: {'regime': 'RANGE', 'execution_zone': 'WAIT', 'invalidation': 'x'}})
    kw.update(over)
    return make_snapshot(**kw)


def registry_snaps(now=NOW):
    return default_registry().run(ProduceRequest(now, now))


def test_valid_live_snapshot_passes_and_is_fresh():
    s = validate_snapshot(live())
    assert classify(s, NOW) == FRESH


def test_missing_required_timestamps_fail():
    for field in ('as_of', 'generated_at', 'expires_at'):
        s = live()
        s[field] = None
        with pytest.raises(MissingFieldError):
            validate_snapshot(s)


def test_absent_key_and_schema_version_fail():
    s = live(); del s['provenance']
    with pytest.raises(MissingFieldError):
        validate_snapshot(s)
    s = live(); s['schema_version'] = 2
    with pytest.raises(SchemaVersionError):
        validate_snapshot(s)


def test_naive_or_invalid_timestamp_fails():
    for field in ('as_of', 'generated_at', 'expires_at', 'requested_as_of'):
        for bad in ('2026-10-01T00:00:00', 'yesterday', 20261001):
            s = live(); s[field] = bad
            with pytest.raises(TimestampError):
                validate_snapshot(s)


def test_freshness_ordering_contract():
    with pytest.raises(FreshnessContractError):
        validate_snapshot(live(expires_at='2026-10-01T00:00:00+00:00'))
    with pytest.raises(FreshnessContractError):
        validate_snapshot(live(generated_at='2026-09-30T00:00:00+00:00'))
    with pytest.raises(FreshnessContractError):
        validate_snapshot(live(requested_as_of='2026-09-30T00:00:00+00:00'))
    with pytest.raises(FreshnessContractError):
        validate_snapshot(live(usable_until='2026-10-01T12:00:00+00:00'))
    with pytest.raises(FreshnessContractError):
        classify(live(), datetime(2026, 9, 30, tzinfo=timezone.utc))
    with pytest.raises(TimestampError):
        classify(live(), datetime(2026, 10, 1))


def test_expired_is_stale_then_not_usable_only_when_producer_declares_it():
    s = live()
    assert classify(s, datetime(2026, 10, 2, tzinfo=timezone.utc)) == STALE
    assert classify(s, datetime(2030, 1, 1, tzinfo=timezone.utc)) == STALE  # no TTL invented
    u = live(usable_until='2026-10-03T00:00:00+00:00')
    assert classify(u, datetime(2026, 10, 2, 12, tzinfo=timezone.utc)) == STALE
    assert classify(u, datetime(2026, 10, 3, tzinfo=timezone.utc)) == NOT_USABLE


def test_stale_kept_with_expiry_and_not_usable_withheld_in_bundle():
    snaps = registry_snaps(datetime(2026, 10, 5, tzinfo=timezone.utc))
    snaps['technical'] = live()
    b = assemble_bundle(companies(), snaps, datetime(2026, 10, 5, tzinfo=timezone.utc))
    assert b['technical']['state'] == 'LIVE' and b['technical']['expires_at'] == '2026-10-02T00:00:00+00:00'
    assert b['producer_manifest']['sections']['technical']['freshness'] == STALE
    snaps['technical'] = live(usable_until='2026-10-03T00:00:00+00:00')
    b = assemble_bundle(companies(), snaps, datetime(2026, 10, 5, tzinfo=timezone.utc))
    assert b['technical']['state'] == 'NOT_AVAILABLE' and b['technical']['data'] is None
    assert b['technical']['producer']['reason_code'] == 'EXPIRED_NOT_USABLE'


def test_missing_provenance_fails():
    for prov in ({'source': None, 'inputs': [{'artifact_id': 'a', 'sha256': H}]}, {'source': 's', 'inputs': []},
                 {'source': 's', 'inputs': [{'sha256': H}]},
                 {'source': 's', 'inputs': [{'artifact_id': 'a', 'sha256': H}, {'artifact_id': 'a', 'sha256': H}]}):
        with pytest.raises(ProvenanceError):
            validate_snapshot(live(provenance=prov))


def test_bad_source_hash_fails():
    for bad in ('abc', 'G' * 64, H.upper().replace('0', 'A')):
        with pytest.raises(SourceHashError):
            validate_snapshot(live(provenance={'source': 's', 'inputs': [{'artifact_id': 'a', 'sha256': bad}]}))
    s = live(); s['data'][next(iter(s['data']))]['regime'] = 'TREND_UP'
    with pytest.raises(SourceHashError):
        validate_snapshot(s)
    u = FrozenUniverseProducer().produce(ProduceRequest(NOW, NOW))
    assert len(verify_inputs(u, file_resolver(ROOT))) == 2
    t = deepcopy(u); t['provenance']['inputs'][0]['sha256'] = H
    with pytest.raises(SourceHashError):
        verify_inputs(t, file_resolver(ROOT))
    t = deepcopy(u); t['provenance']['inputs'][0]['artifact_id'] = 'file:../outside.json'
    with pytest.raises(ProvenanceError):
        verify_inputs(t, file_resolver(ROOT))


def test_synthetic_cannot_be_live_or_hidden():
    with pytest.raises(SyntheticStateError):
        validate_snapshot(live(synthetic=True))
    cid = companies()[0]['company_id']
    with pytest.raises(SyntheticStateError):
        validate_snapshot(live(data={cid: {'regime': 'RANGE', 'synthetic': True}}))
    assert validate_snapshot(live(synthetic=True, data_state='DEMO', expires_at=None))


def test_research_status_and_validation_status_not_publishable():
    for state in ('LIVE', 'FROZEN_SNAPSHOT'):
        with pytest.raises(ResearchStatusError):
            validate_snapshot(live(data_state=state, methodology={'id': 'q', 'version': '1', 'status': 'PROVISIONAL_RESEARCH'}))
        with pytest.raises(ValidationStatusError):
            validate_snapshot(live(data_state=state, validation={'status': 'NOT_RUN', 'checks': []}))


def test_unsupported_state_fails():
    for state in ('STALE', 'PROVISIONAL_RESEARCH', 'RESEARCH', 'SYNTHETIC', 'live'):
        with pytest.raises(UnsupportedStateError):
            validate_snapshot(live(data_state=state))


def test_not_available_is_explicit_absence():
    s = validate_snapshot(not_available('news', 'news.none', 'v', NOW.isoformat(), 'none', 'NEWS_NO_SOURCE'))
    assert classify(s, NOW) == NOT_APPLICABLE
    bad = deepcopy(s); bad['data'] = []
    with pytest.raises(UnsupportedStateError):
        validate_snapshot(bad)
    bad = deepcopy(s); bad['reason'] = ''
    with pytest.raises(MissingFieldError):
        validate_snapshot(bad)


def test_errors_are_typed_value_errors():
    with pytest.raises(ValueError):
        validate_snapshot(live(synthetic=True))
    assert issubclass(SyntheticStateError, ProducerContractError) and SyntheticStateError.code == 'SYNTHETIC_STATE'


def test_deterministic_serialization_and_bundle_hash():
    a, b = {'b': [1, 2.5], 'a': {'y': None, 'x': 'ü'}}, {'a': {'x': 'ü', 'y': None}, 'b': [1, 2.5]}
    assert canonical_bytes(a) == canonical_bytes(b) and canonical_sha256(a) == canonical_sha256(b)
    for bad in ({'x': float('nan')}, {'x': {1, 2}}, {'x': datetime(2026, 1, 1)}, {1: 'x'}):
        with pytest.raises(ValueError):
            canonical_bytes(bad)
    b1 = assemble_bundle(companies(), registry_snaps(), NOW)
    b2 = assemble_bundle(companies(), registry_snaps(), NOW)
    assert canonical_bytes(b1) == canonical_bytes(b2) and bundle_sha256(b1) == bundle_sha256(b2)
    assert bundle_sha256(assemble_bundle(companies(), registry_snaps(NOW + timedelta(seconds=1)),
                                         NOW + timedelta(seconds=1))) != bundle_sha256(b1)


def test_default_export_equals_existing_web_default_semantics():
    b = assemble_bundle(companies(), registry_snaps(), NOW)
    r = repository_bundle()
    assert b['companies'] == r['companies'] and b['universe']['data'] == r['universe']['data']
    assert b['universe']['state'] == 'FROZEN_SNAPSHOT' and b['universe']['source'] == r['universe']['source']
    for name in ('qgv', 'technical', 'macro', 'portfolio', 'leaderboard', 'news', 'relationships', 'changes'):
        assert b[name]['state'] == 'NOT_AVAILABLE' and b[name]['data'] is None and b[name]['reason'] == r[name]['reason']
        assert b[name]['producer']['reason_code']
    validate_bundle(b)
    with tempfile.TemporaryDirectory() as d:
        build(d, b)
        assert json.loads((Path(d) / 'data.json').read_text())['producer_manifest']['contract'] == 'PRODUCER_BUNDLE'


def test_assembler_requires_every_section_and_matching_identity():
    snaps = registry_snaps(); del snaps['news']
    with pytest.raises(IdentityError):
        assemble_bundle(companies(), snaps, NOW)
    snaps = registry_snaps(); snaps['news'] = snaps['changes']
    with pytest.raises(IdentityError):
        assemble_bundle(companies(), snaps, NOW)
    snaps = registry_snaps(); snaps['technical'] = live(data={'not-a-member': {'regime': 'RANGE'}})
    with pytest.raises(ValueError):
        assemble_bundle(companies(), snaps, NOW)  # existing Web referential integrity


def test_atomic_write_fails_closed_and_preserves_previous():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / 'bundle.json'
        good = assemble_bundle(companies(), registry_snaps(), NOW)
        digest = write_bundle_atomic(good, out)
        before = out.read_bytes()
        assert (Path(d) / 'bundle.json.sha256').read_text().split()[0] == digest == bundle_sha256(good)
        bad = deepcopy(good); bad['qgv'] = {'state': 'LIVE', 'as_of': '2026-10-01T00:00:00+00:00', 'source': 's', 'data': {}}
        with pytest.raises(ValueError):
            write_bundle_atomic(bad, out)
        assert out.read_bytes() == before and sorted(p.name for p in Path(d).iterdir()) == ['bundle.json', 'bundle.json.sha256']


def test_web_validator_live_missing_expiry_is_value_error_not_key_error():
    b = repository_bundle()
    cid = b['companies'][0]['company_id']
    b['technical'] = {'state': 'LIVE', 'as_of': '2026-10-01T00:00:00+00:00', 'source': 's', 'data': {cid: {}}}
    with pytest.raises(ValueError) as e:
        validate_bundle(b)
    assert not isinstance(e.value, KeyError) and 'expires_at' in str(e.value)
    c = repository_bundle(); del c['news']
    with pytest.raises(ValueError):
        validate_bundle(c)
    b['technical']['expires_at'] = '2026-10-02T00:00:00+00:00'
    validate_bundle(b)


def test_adapters_are_verbatim_and_fail_closed():
    raws = [r for r in iter_official_raw()][:3]
    pipe = AnalysisPipeline()
    snaps = [pipe.analyze_raw(r) for r in raws]
    before = [(s.Q_score, s.G_score, s.V_score, s.total_score) for s in snaps]
    kind, data, synthetic = adapters.qgv_section(snaps)
    assert kind == 'ENTITY_MAP' and synthetic is True
    assert [(data[s.company_id]['Q_score'], data[s.company_id]['G_score'], data[s.company_id]['V_score'],
             data[s.company_id]['total_score']) for s in snaps] == before
    snap = make_snapshot(producer_id='qgv.fixture', producer_version='t', section='qgv', data_state='LIVE',
                         as_of='2026-09-14T00:00:00+00:00', generated_at=NOW.isoformat(),
                         expires_at='2026-10-02T00:00:00+00:00', methodology={'id': 'q', 'version': '1', 'status': 'x'},
                         synthetic=synthetic, provenance={'source': 'fixture', 'inputs': [{'artifact_id': 'a', 'sha256': H}]},
                         validation={'status': 'PASS', 'checks': []}, scope_kind=kind, data=data)
    with pytest.raises(SyntheticStateError):
        validate_snapshot(snap)
    t = TechnicalEngine().evaluate('nvda', NOW, [0.01, 0.02])
    assert adapters.technical_section([t])[2] is True
    with pytest.raises(IdentityError):
        adapters.technical_section([t, t])
    with pytest.raises(IncompatibleShapeError):
        adapters.macro_section(MacroEngine().evaluate(NOW, {'growth': 0.01, 'inflation': 0.02}))
    with pytest.raises(IncompatibleShapeError):
        adapters.qgv_section([t])
    assert adapters.SECTION_COMPATIBILITY['macro']['compatibility'] == 'INCOMPATIBLE'
    assert isinstance(MacroEngine().evaluate(NOW, {}), MacroSnapshot)


def test_registry_has_no_live_producer_and_universe_is_frozen():
    snaps = registry_snaps()
    assert snaps['universe']['data_state'] == 'FROZEN_SNAPSHOT' and snaps['universe']['as_of'] == '2024-12-31T00:00:00+00:00'
    assert snaps['universe']['requested_as_of'] == NOW.isoformat()
    assert all(s['data_state'] == 'NOT_AVAILABLE' for k, s in snaps.items() if k != 'universe')
    assert not any(s['data_state'] in ('LIVE', 'DEMO') for s in snaps.values())


def test_raw_persistence_manifest_binding_and_retention():
    recs = artifact_records(ROOT / 'data/raw')
    assert len(recs) == 6808 and all(r['available_at'] is None for r in recs)
    assert manifest_set_sha256(recs) == manifest_set_sha256(list(reversed(recs)))
    committed = json.loads((ROOT / 'reports/raw_persistence/raw_dataset_manifest_2026-10-01.json').read_text())
    assert committed['manifest_set_sha256'] == manifest_set_sha256(recs)
    assert committed['integrity_binding']['consistent_with_committed_manifests'] is True
    assert committed['retention']['overall'] == 'AT_RISK_ONLY_EXPIRING_COPIES'
    art = {'kind': 'GITHUB_ACTIONS_ARTIFACT', 'ref': 'a', 'expires_at': '2026-12-26T08:21:15Z', 'complete_blobs': True, 'verified': True}
    assert retention_audit([art], NOW)['loss_deadline_if_no_action'] == '2026-12-26T08:21:15Z'
    assert retention_audit([art], datetime(2027, 1, 1, tzinfo=timezone.utc))['overall'] == 'NO_VERIFIED_COMPLETE_COPY'
    durable = dict(art, kind='GITHUB_RELEASE', expires_at=None)
    assert retention_audit([art, durable], NOW)['overall'] == 'DURABLE_COPY_PRESENT'
    assert retention_audit([dict(durable, verified=False)], NOW)['overall'] == 'NO_VERIFIED_COMPLETE_COPY'
    with pytest.raises(ValueError):
        retention_audit([dict(art, kind='S3_BUCKET_X')], NOW)
