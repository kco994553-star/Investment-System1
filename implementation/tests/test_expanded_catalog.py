"""Synthetic-only acceptance and adversarial cases; no source/API requests."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import importlib

import pytest


def core():
    return importlib.import_module('investment_system.universe.expanded_catalog')


def at(day=1):
    return datetime(2020, 1, day, tzinfo=timezone.utc)


def raw(**changes):
    value = dict(issuer_id='cik:0000000001', cik='1', security_id='synthetic:class-a',
                 ticker='SYN.A', exchange='NASDAQ', security_type='COMMON_CLASS',
                 display_name='Synthetic Issuer', valid_from=at().isoformat(),
                 valid_to=None, status='ACTIVE', source_ref='synthetic:listing-1')
    value.update(changes)
    return value


def record(**changes):
    m = core()
    result = m.normalize_security_record(raw(**changes), m.CatalogPolicy())
    assert isinstance(result, m.SecurityRecord)
    return result


def test_c01_normalization_uses_existing_cik_identity_and_preserves_class_ids():
    m = core()
    a, b = record(), record(security_id='synthetic:class-b', ticker='SYN.B')
    assert a.issuer_id == b.issuer_id == 'cik:0000000001'
    assert a.security_id != b.security_id
    assert a.cik == '0000000001'
    assert a.eligibility == 'INCLUDED'
    with pytest.raises(FrozenInstanceError):
        a.ticker = 'BAD'


@pytest.mark.parametrize('kind', ['ETF', 'CLOSED_END_FUND', 'PREFERRED', 'WARRANT', 'RIGHT', 'UNIT'])
def test_c06_non_common_securities_are_explicitly_excluded(kind):
    result = record(security_type=kind)
    assert result.eligibility == 'EXCLUDED'
    assert result.reason_codes == ('SECURITY_TYPE_EXCLUDED',)


@pytest.mark.parametrize('kind', ['ADR', 'REIT'])
def test_c07_adr_reit_remain_pending_without_policy(kind):
    m = core()
    assert record(security_type=kind).reason_codes == ('SOURCE_POLICY_PENDING',)
    for decision, expected in [('INCLUDE', 'INCLUDED'), ('EXCLUDE', 'EXCLUDED')]:
        policy = replace(m.CatalogPolicy(), **{kind.lower() + '_policy': decision})
        assert m.normalize_security_record(raw(security_type=kind), policy).eligibility == expected


@pytest.mark.parametrize('cik', [None, '', 0, True, '0000000000', '１', '١', '-1', '1.0', '1e2', '12345678901'])
def test_c08_missing_or_invalid_cik_never_guesses_identity(cik):
    m = core()
    result = m.normalize_security_record(raw(cik=cik), m.CatalogPolicy())
    assert isinstance(result, m.Rejection)
    assert result.reason_codes == ('IDENTITY_AMBIGUOUS',)


def test_c08_different_issuer_cannot_claim_the_same_cik():
    m = core()
    assert m.normalize_security_record(raw(issuer_id='cik:0000000002'), m.CatalogPolicy()).reason_codes == ('IDENTITY_AMBIGUOUS',)


@pytest.mark.parametrize('changes', [
    {'valid_from': None}, {'valid_from': '2020-01-01'},
    {'valid_from': '2020-01-01T00:00:00'}, {'valid_to': at().isoformat()},
    {'valid_to': at(2).isoformat()}, {'status': 'ENDED'}, {'ticker': ''},
    {'ticker': 2}, {'security_id': ''}, {'security_type': 'UNKNOWN'},
    {'display_name': ''}, {'exchange': 'OTC'},
])
def test_c05_c06_bad_schema_dates_and_unsupported_exchange_are_rejections(changes):
    m = core()
    assert isinstance(m.normalize_security_record(raw(**changes), m.CatalogPolicy()), m.Rejection)


def test_c11_unknown_sensitive_fields_do_not_enter_models_or_diagnostics():
    m = core()
    for key in ('price', 'holdings', 'access_token', 'sheet_id', 'derived_price'):
        result = m.normalize_security_record(raw(**{key: 'SENSITIVE_SENTINEL'}), m.CatalogPolicy())
        assert isinstance(result, m.Rejection)
        assert 'SENSITIVE_SENTINEL' not in repr(result)
    assert 'Synthetic Issuer' not in repr(record())


@pytest.mark.parametrize('field', ['display_name', 'source_ref', 'security_id'])
def test_c11_credential_patterns_in_allowed_text_are_rejected(field):
    m = core()
    sentinel = 'Bearer ' + 'SENSITIVE_SENTINEL'
    result = m.normalize_security_record(raw(**{field: sentinel}), m.CatalogPolicy())
    assert isinstance(result, m.Rejection)
    assert sentinel not in repr(result)


def test_utc_normalization_preserves_actual_instant():
    assert record(valid_from='2020-01-01T09:00:00+09:00').valid_from == at()


def test_policy_is_checked_instead_of_silently_defaulting():
    m = core()
    assert isinstance(m.normalize_security_record(raw(), replace(m.CatalogPolicy(), adr_policy='guess')), m.Rejection)


def events_module():
    return importlib.import_module('investment_system.universe.expanded_catalog_events')


def event(event_id='e1', kind='LISTED', day=1, *, rec=None, available=None, collected=None, **changes):
    m = core()
    if kind == 'LISTED' and rec is None:
        rec = record(valid_from=at(day))
    args = dict(event_id=event_id, issuer_id=rec.issuer_id if rec else 'cik:0000000001',
                security_id=rec.security_id if rec else 'synthetic:class-a', event_type=kind,
                effective_at=at(day), available_at=available or at(day),
                collected_at=collected or available or at(day), source_ref='synthetic:event',
                raw_hash='0' * 64, record=rec, successor_security_id=None)
    args.update(changes)
    return m.ListingEvent(**args)


def empty(day=1, **changes):
    return core().CatalogSnapshot(as_of=at(day), **changes)


def apply(previous, events, day):
    return events_module().apply_listing_events(previous, events, at(day))


def test_c01_snapshot_counts_issuer_once_and_classes_separately():
    b = record(security_id='synthetic:class-b', ticker='SYN.B')
    s = apply(empty(), [event(), event('b', rec=b)], 1)
    assert (s.issuer_count, s.security_count, len(s.included)) == (1, 2, 2)
    assert len(s.issuers) == 1
    assert s.issuers[0].issuer_id == 'cik:0000000001'
    assert core().validate_catalog(s).ok


def test_c02_ticker_reuse_keeps_distinct_security_and_issuer_intervals():
    old = apply(empty(), [event()], 1)
    other = record(issuer_id='cik:0000000002', cik='2', security_id='synthetic:other', valid_from=at(3))
    new = apply(old, [event('end', 'DELISTED', 2), event('new', day=3, rec=other)], 3)
    assert new.current == (other,)
    assert len(new.records) == 2
    assert next(r for r in new.records if r.security_id == 'synthetic:class-a').valid_to == at(2)
    assert old.current[0].valid_to is None
    diff = events_module().diff_snapshots(old, new)
    assert diff.added == ('synthetic:other',)
    assert diff.ended == ('synthetic:class-a',)


def test_c03_not_public_or_not_effective_is_deferred_and_later_applied():
    later = event(available=at(3), collected=at(8))
    s = apply(empty(), [later], 2)
    assert not s.current and len(s.events) == 1
    assert apply(s, [], 3).security_count == 1
    announced = event(day=4, available=at(1), collected=at(2))
    s = apply(empty(), [announced], 2)
    assert not s.current
    assert apply(s, [], 4).security_count == 1


def test_c04_same_event_id_is_idempotent_but_conflicting_payload_is_rejected():
    m = core()
    s = apply(empty(), [event(), event()], 1)
    assert len(s.events) == 1
    assert apply(s, [event()], 1) == s
    with pytest.raises(m.CatalogError, match='EVENT_ID_CONFLICT'):
        apply(s, [replace(event(), raw_hash='1' * 64)], 1)


@pytest.mark.parametrize('field,value', [('available_at', None), ('effective_at', None),
    ('collected_at', None), ('available_at', at(3)), ('effective_at', '2020-01-01'),
    ('raw_hash', 'bad'), ('event_type', 'UNKNOWN')])
def test_c05_malformed_event_rejects_entire_batch(field, value):
    m = core()
    with pytest.raises(m.CatalogError):
        apply(empty(), [replace(event(), **{field: value})], 4)


def test_c05_snapshot_time_cannot_move_backwards():
    m = core()
    s = apply(empty(), [event()], 3)
    with pytest.raises(m.CatalogError, match='CUTOFF_REGRESSION'):
        apply(s, [], 2)


@pytest.mark.parametrize('kind,changes', [
    ('TICKER_CHANGED', {'ticker': 'NEW.A'}), ('EXCHANGE_CHANGED', {'exchange': 'NYSE'}),
    ('CLASS_CHANGED', {'security_type': 'PREFERRED'}), ('NAME_CHANGED', {'display_name': 'New Synthetic Name'})])
def test_changes_preserve_history_and_diff_counts_security_once(kind, changes):
    s = apply(empty(), [event()], 1)
    changed = record(valid_from=at(2), **changes)
    n = apply(s, [event('change', kind, 2, rec=changed)], 2)
    assert n.current == (changed,)
    assert len(n.records) == 2
    assert n.records[0].valid_to == at(2)
    assert events_module().diff_snapshots(s, n).changed == ('synthetic:class-a',)


def test_reversed_input_and_late_historical_event_replay_deterministically():
    e1 = event()
    e2 = event('rename', 'TICKER_CHANGED', 2, rec=record(valid_from=at(2), ticker='NEW.A'))
    e3 = event('end', 'DELISTED', 4)
    ordered = apply(empty(), [e1, e2, e3], 4)
    assert apply(empty(), [e3, e1, e2], 4) == ordered
    previous = apply(empty(), [e1, e3], 4)
    assert apply(previous, [e2], 4) == ordered


def test_c10_failed_batch_preserves_previous_and_can_be_retried_as_whole():
    m = core()
    s = apply(empty(), [event()], 1)
    end = event('end', 'DELISTED', 3)
    invalid = event('invalid', 'DELISTED', 4, security_id='synthetic:missing')
    with pytest.raises(m.CatalogError):
        apply(s, [end, invalid], 4)
    assert s.security_count == 1 and len(s.events) == 1
    n = apply(s, [end, end], 4)
    assert n.security_count == 0 and len(n.events) == 2
    assert apply(n, [end], 4) == n


def test_c08_same_ticker_overlap_and_security_rebinding_are_rejected():
    m = core()
    s = apply(empty(), [event()], 1)
    for changes in [dict(security_id='synthetic:b'), dict(issuer_id='cik:0000000002', cik='2')]:
        with pytest.raises(m.CatalogError):
            apply(s, [event('bad', day=2, rec=record(valid_from=at(2), **changes))], 2)


def test_same_security_same_effective_instant_is_ambiguous_not_lexical_order():
    m = core()
    with pytest.raises(m.CatalogError, match='EVENT_ORDER_AMBIGUOUS'):
        apply(empty(), [event(), event('end', 'DELISTED')], 1)


def test_merge_closes_predecessor_without_merging_issuer_identity():
    target = record(issuer_id='cik:0000000002', cik='2', security_id='synthetic:target', ticker='DEST')
    s = apply(empty(), [event(), event('target', rec=target)], 1)
    n = apply(s, [event('merge', 'MERGED', 2, successor_security_id='synthetic:target')], 2)
    assert n.current == (target,)
    assert n.security_count == n.issuer_count == 1
    assert len(n.records) == 2


@pytest.mark.parametrize('changes', [{'schema_version': 'bad'}, {'universe_id': 'UNIVERSE504'},
    {'records': []}, {'events': []}, {'source_rights_state': 'PERMITTED'},
    {'quality': 'LIVE'}, {'as_of': None}])
def test_validate_catalog_rejects_forged_envelopes(changes):
    s = apply(empty(), [event()], 1)
    assert not core().validate_catalog(replace(s, **changes)).ok


def test_validate_catalog_rejects_forged_counts_intervals_and_event_provenance():
    m = core()
    s = apply(empty(), [event()], 1)
    for records in [(replace(s.records[0], valid_to=at(), status='ENDED'),),
                    (s.records[0], s.records[0]), (replace(s.records[0], ticker='FAKE'),)]:
        assert not m.validate_catalog(replace(s, records=records)).ok
    assert not m.validate_catalog(replace(s, policy=replace(s.policy, adr_policy='INCLUDE'))).ok


def snapshots():
    return importlib.import_module('investment_system.universe.expanded_catalog_snapshot')


def test_c04_serialization_and_hash_are_deterministic_across_retries_and_event_order():
    mod = snapshots()
    a = event()
    b = event('end', 'DELISTED', 3)
    x, y = apply(empty(), [a, b], 3), apply(empty(), [b, a, b], 3)
    assert mod.snapshot_bytes(x) == mod.snapshot_bytes(y)
    assert mod.snapshot_hash(x) == mod.snapshot_hash(y) == x.universe_version
    assert mod.snapshot_hash(apply(x, [a, b], 3)) == mod.snapshot_hash(x)
    assert mod.snapshot_hash(apply(x, [], 4)) != mod.snapshot_hash(x)


@pytest.mark.parametrize('failure', ['HTTP_429', 'SOURCE_INTERRUPTED', 'SOURCE_CORRUPT'])
def test_c09_source_failure_keeps_previous_object_hash_and_success_time(failure):
    mod = snapshots()
    old = apply(empty(), [event()], 1)
    before = mod.snapshot_bytes(old)
    outcome = mod.dry_run_refresh(old, [event('end', 'DELISTED', 2)], at(2), at(3),
                                  source_status=failure, last_success_at=at(1))
    assert outcome.snapshot is old
    assert mod.snapshot_bytes(old) == before
    assert outcome.receipt.status == 'FAILED'
    assert outcome.receipt.last_success_at == at(1)
    assert outcome.receipt.attempted_at == at(3)
    assert outcome.receipt.new_snapshot_version == outcome.receipt.previous_snapshot_version
    assert outcome.receipt.reason_codes == (failure,)


def test_c10_invalid_or_partial_batch_keeps_previous_until_valid_retry():
    mod = snapshots()
    old = apply(empty(), [event()], 1)
    end = event('end', 'DELISTED', 2)
    bad = replace(end, event_id='bad', available_at=None)
    failed = mod.dry_run_refresh(old, [end, bad], at(2), at(3))
    assert failed.snapshot is old and failed.receipt.status == 'FAILED'
    assert failed.receipt.ended == 0
    good = mod.dry_run_refresh(old, [end], at(2), at(3))
    assert good.receipt.status == 'SYNTHETIC_PASS' and good.receipt.ended == 1
    assert good.snapshot.security_count == 0
    assert mod.dry_run_refresh(good.snapshot, [end], at(2), at(3)).snapshot is good.snapshot


def test_private_receipt_is_only_counts_codes_and_versions_without_company_level_input():
    from dataclasses import asdict
    import json
    mod = snapshots()
    old = empty()
    s = apply(old, [event()], 1)
    diff = events_module().diff_snapshots(old, s)
    receipt = mod.render_private_receipt(s, diff, 'SYNTHETIC_PASS', previous=old, attempted_at=at(2))
    payload = json.dumps(asdict(receipt), default=str)
    for forbidden in ('SYN.A', 'Synthetic Issuer', 'synthetic:class-a', 'cik:0000000001'):
        assert forbidden not in payload
    assert receipt.issuer_count == receipt.security_count == receipt.added == 1
    assert receipt.source_rights == 'UNVERIFIED' and receipt.real_data_executed is False


def test_c11_receipt_input_fail_closed_and_never_echoes_sentinel(capsys):
    m, mod = core(), snapshots()
    s = apply(empty(), [event()], 1)
    diff = events_module().diff_snapshots(empty(), s)
    sentinel = 'SENSITIVE_SENTINEL'
    for status in (sentinel, {'price': sentinel}, ['holdings', sentinel]):
        with pytest.raises(m.CatalogError) as error:
            mod.render_private_receipt(s, diff, status, previous=empty(), attempted_at=at(2))
        assert sentinel not in str(error.value)
    bad = replace(s, records=(replace(s.records[0], display_name='Bearer ' + sentinel),))
    with pytest.raises(m.CatalogError) as error:
        mod.snapshot_bytes(bad)
    assert sentinel not in str(error.value)
    assert sentinel not in repr(bad)
    assert not capsys.readouterr().out and not capsys.readouterr().err


def test_c12_existing_official_504_bytes_are_unchanged_by_catalog_operations():
    import hashlib
    from pathlib import Path
    from investment_system.universe.universe_codes import SOURCE, source_codes
    root = Path(__file__).resolve().parents[1]
    protected = [SOURCE, root / 'src/investment_system/universe/sec_qgv2.py',
                 root / 'src/investment_system/validation/forward_ledger.py']
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in protected]
    ticker = source_codes()[0].split(':')[1]
    s = apply(empty(), [event(rec=record(ticker=ticker)), event('end', 'DELISTED', 2)], 2)
    assert s.universe_id == 'U-US-DISCOVERY'
    snapshots().snapshot_hash(s)
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in protected] == before
    assert len(source_codes()) == 504


@pytest.mark.parametrize('changes', [{'source_status': 'SENSITIVE_SENTINEL'},
    {'source_status': {'price': 123}}, {'attempted_at': at(1)}, {'cutoff': None}])
def test_refresh_invalid_controls_fail_with_fixed_code(changes):
    m, mod = core(), snapshots()
    s = apply(empty(), [event()], 1)
    args = dict(cutoff=at(2), attempted_at=at(3), source_status='OK')
    args.update(changes)
    with pytest.raises(m.CatalogError) as error:
        mod.dry_run_refresh(s, [], **args)
    assert 'SENSITIVE_SENTINEL' not in str(error.value)


def test_supplied_synthetic_fixture_runs_without_network_or_filesystem_writes(monkeypatch):
    import builtins
    import json
    from pathlib import Path
    import socket
    fixture = json.loads((Path(__file__).parent / 'fixtures/expanded_universe/catalog_cases.json').read_text())
    assert fixture['fixture_kind'] == 'SYNTHETIC_ONLY' and fixture['real_data_executed'] is False
    m, mod = core(), snapshots()

    def forbidden(*args, **kwargs):
        raise AssertionError('UNEXPECTED_IO')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr(Path, 'write_text', forbidden)
    for index, (kind, expected) in enumerate(fixture['types']):
        r = record(security_type=kind)
        assert r.eligibility == expected
        result = mod.dry_run_refresh(empty(), [event(event_id='synthetic:' + str(index), rec=r)], at(1), at(2))
        assert result.receipt.status == 'SYNTHETIC_PASS'
        assert m.validate_catalog(result.snapshot).ok
    for reason in fixture['source_failures']:
        assert mod.dry_run_refresh(empty(), [], at(1), at(2), source_status=reason).receipt.status == 'FAILED'


def test_unobserved_success_time_is_not_fabricated_from_asof_or_availability():
    old = apply(empty(), [event()], 1)
    result = snapshots().dry_run_refresh(old, [], at(2), at(3), source_status='HTTP_429')
    assert result.receipt.last_success_at is None


def test_c04_recollection_keeps_original_timestamp_and_hash():
    first = event()
    recollected = replace(first, collected_at=at(3))
    old = apply(empty(), [first], 1)
    retried = apply(old, [recollected], 1)
    assert retried is old
    assert snapshots().snapshot_hash(old) == snapshots().snapshot_hash(retried)
    assert apply(empty(), [recollected, first], 1) == apply(empty(), [first, recollected], 1) == old


@pytest.mark.parametrize('predecessor', ['synthetic:aaa', 'synthetic:zzz'])
@pytest.mark.parametrize('target_action', ['LISTED', 'DELISTED'])
def test_same_instant_merger_dependencies_fail_closed_independently_of_ids(predecessor, target_action):
    m = core()
    first = event(rec=record(security_id=predecessor, ticker='OLD'))
    target = record(issuer_id='cik:0000000002', cik='2', security_id='synthetic:middle', ticker='DEST',
                    valid_from=at(2) if target_action == 'LISTED' else at(1))
    base_events = [first] if target_action == 'LISTED' else [first, event('target', rec=target)]
    old = apply(empty(), base_events, 1)
    merge = event('merge', 'MERGED', 2, security_id=predecessor, successor_security_id=target.security_id)
    target_event = (event('target', day=2, rec=target) if target_action == 'LISTED' else
                    event('target-end', 'DELISTED', 2, security_id=target.security_id, issuer_id=target.issuer_id))
    with pytest.raises(m.CatalogError, match='MERGER_TARGET_TIME_AMBIGUOUS'):
        apply(old, [merge, target_event], 2)


def test_success_receipt_cannot_predate_any_collection_including_retrospective_snapshot():
    m, mod = core(), snapshots()
    old = empty()
    s = apply(old, [event(collected=at(8))], 1)
    with pytest.raises(m.CatalogError, match='INVALID_TIME_ORDER'):
        mod.render_private_receipt(s, events_module().diff_snapshots(old, s), 'SYNTHETIC_PASS',
                                   previous=old, attempted_at=at(2))
    assert mod.render_private_receipt(s, events_module().diff_snapshots(old, s), 'SYNTHETIC_PASS',
                                      previous=old, attempted_at=at(8)).last_success_at == at(8)


def test_extremely_large_cik_returns_fixed_rejection():
    m = core()
    result = m.normalize_security_record(raw(cik=10 ** 5000), m.CatalogPolicy())
    assert result.reason_codes == ('IDENTITY_AMBIGUOUS',)


def test_timezone_exception_never_leaks_through_model_or_refresh():
    from datetime import tzinfo
    m, mod = core(), snapshots()

    class BrokenTZ(tzinfo):
        def utcoffset(self, value):
            raise ValueError('SENSITIVE_SENTINEL')

    broken = datetime(2020, 1, 1, tzinfo=BrokenTZ())
    assert m.normalize_security_record(raw(valid_from=broken), m.CatalogPolicy()).reason_codes == ('INVALID_TIMESTAMP',)
    with pytest.raises(m.CatalogError, match='INVALID_TIMESTAMP') as error:
        mod.dry_run_refresh(empty(), [], at(1), broken)
    assert 'SENSITIVE_SENTINEL' not in str(error.value)
