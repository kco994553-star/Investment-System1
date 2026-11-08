"""Common dated classifications projected through existing technical/SIC kernels.

No identity discovery, new numerical engine, ETF return or probability estimate.
Company IDs, issuer IDs and permanent security IDs remain separate.
"""
from copy import deepcopy

from investment_system.qgv.sector_basis import load_map, sector_benchmark
from investment_system.qgv.sic_industry import CONFIG_VERSION, classify_sic
from ..exp_deciles.technical_leaderboard import build_board
from ..exp_deciles.technical_measures import METRIC_IDS, number, settings_for_basis
from ..exp_deciles.settings import ELIGIBLE_SECURITY_TYPES
from ..kis_price_bridge import _day
from ..private_technical_board import SECURITY_IDENTIFIER_TYPES
from ..sector_qgv import digest, timestamp
from ..sector_qgv_registry import SECTORS
from .catalog import MAPPING_VERSION, VERSION, POLICY_DICTIONARY_VERSION, POLICY_MAPPING_VERSION, dictionary
from .records import _available


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _rows(view):
    if view.get('schema_version') != 'common-classification-view/1':
        raise ValueError('COMMON_VIEW_SCHEMA_MISMATCH')
    versions={VERSION:MAPPING_VERSION,POLICY_DICTIONARY_VERSION:POLICY_MAPPING_VERSION}
    if (view.get('dictionary_version') not in versions or
            view.get('mapping_version') != versions[view['dictionary_version']]):
        raise ValueError('COMMON_VIEW_VERSION_MISMATCH')
    _day(view.get('valuation_date'))
    try:
        timestamp(view.get('knowledge_as_of'))
    except (AttributeError, TypeError, ValueError):
        raise ValueError('KNOWLEDGE_CUTOFF_REQUIRED') from None
    if view.get('data_kind') not in ('SYNTHETIC', 'RETAINED_INPUT'):
        raise ValueError('DATA_KIND_REQUIRED')
    rows = view['rows']
    ids = [row['company_id'] for row in rows]
    members = view['members']
    if (any(not _text(key) for key in ids + members) or len(set(ids)) != len(ids)
            or len(set(members)) != len(members) or set(ids) != set(members)):
        raise ValueError('COMMON_VIEW_MEMBERSHIP_MISMATCH')
    return {row['company_id']: row for row in rows}


def _sector(row):
    value = row.get('sector', {})
    return value.get('id') if value.get('status') == 'CONFIRMED' and value.get('id') in SECTORS else None


def _ratio(row):
    if 'adr_ratio' not in row or row.get('security_type') not in ELIGIBLE_SECURITY_TYPES:
        return False, None
    value = row['adr_ratio']
    if row.get('security_type') == 'ADR':
        parsed = number(value)
        return parsed is not None and parsed > 0, parsed
    return value is None, None


def _link_time_reasons(link, cutoff, prefix):
    """Reuse record precision semantics: date-only on cutoff day is unknown."""
    reasons = []
    for field, label in (('recorded_at', 'RECORD'), ('acquired_at', 'EVIDENCE')):
        value = link.get(field)
        try:
            known = _available(value, cutoff) if _text(value) else None
        except (TypeError, ValueError):
            known = None
        if known is not True:
            reasons.append(prefix + '_' + label + ('_NOT_AVAILABLE' if known is False else '_TIME_UNKNOWN'))
    return reasons


def technical_groups(view, measurements, security_links, *, price_basis):
    """Build every sector board from its original dated membership.

    A missing classification can belong to any sector, so all memberships remain
    UNKNOWN. Missing identity evidence blocks that company's sector; a missing
    measurement retains the known member with null metric values instead.
    Original measurements remain in diagnostics; only verified matching measures
    enter boards. Unknown boards retain absolute values but no relative ranks.
    Security-link intervals include both ends; view classifications have already
    been resolved by their own (exclusive-end) record contract.

    ADR ratios must be positive; non-ADR rows explicitly carry adr_ratio=None.
    Common-connection links extend #515 with recorded_at (link review/record time)
    and acquired_at (availability of all referenced identity evidence). Both must
    be established by knowledge_as_of. Missing #515 legacy fields remain unknown;
    this adapter never substitutes evaluation dates or manufactures timestamps.
    Supplied security links are the complete declared dated membership evidence,
    not a lookup assembled from only companies with successful measurements.
    input_hash/cache_key binds classification and the complete supplied inputs,
    order-independently, plus price basis and the existing numerical settings
    version. Display tags are absent from this numerical identity.
    """
    companies = _rows(view)
    settings, _ = settings_for_basis(price_basis)
    signal = view['valuation_date']
    measurements = list(measurements)
    links = list(security_links)
    input_hash = digest(dict(classification_hash=view['classification_hash'],
                             measurements=sorted(measurements, key=digest),
                             security_links=sorted(links, key=digest),
                             price_basis=price_basis, settings_version=settings['settings_version']))
    by_series = {}
    for index, measurement in enumerate(measurements):
        series = measurement.get('series_id')
        if not _text(series):
            raise ValueError('REQUEST_SERIES_ID_REQUIRED')
        if series in by_series:
            raise ValueError('DUPLICATE_MEASUREMENT_SERIES')
        by_series[series] = (index, measurement)
    active_ids, active_series = set(), set()
    by_company = {key: [] for key in companies}
    link_diagnostics = []
    for link in links:
        company = link.get('company_id')
        if not _text(company) or company not in companies:
            raise ValueError('SECURITY_LINK_COMPANY_NOT_IN_VIEW')
        if _day(link.get('valid_from')) > _day(link.get('valid_to')):
            raise ValueError('INVALID_SECURITY_LINK_RANGE')
        time_reasons = _link_time_reasons(link, view['knowledge_as_of'], 'SECURITY_LINK')
        by_company[company].append((link, time_reasons))
        if time_reasons:
            link_diagnostics.append(dict(link=deepcopy(link), reasons=time_reasons))
        if link['valid_from'] <= signal <= link['valid_to'] and not time_reasons:
            sid, series = link.get('security_id'), link.get('series_id')
            if (_text(sid) and sid in active_ids) or (_text(series) and series in active_series):
                raise ValueError('DUPLICATE_SECURITY_LINK')
            if _text(sid):
                active_ids.add(sid)
            if _text(series):
                active_series.add(series)

    states, diagnostics = [], [dict(measurement=deepcopy(m), reasons=[]) for m in measurements]
    board_inputs = {sector: [] for sector in SECTORS}
    group_reasons = {sector: [] for sector in SECTORS}
    linked_ids = {sector: [] for sector in SECTORS}
    used = set()
    unclassified = sum(_sector(row) is None for row in companies.values())
    for company in view['members']:
        row = companies[company]
        sector = _sector(row)
        reasons, identity_reasons, verified_ids = [], [], []
        if sector is None:
            identity_reasons.extend(row.get('sector', {}).get('reasons') or ['CLASSIFICATION_UNCONFIRMED'])
        dated = [(link, why) for link, why in by_company[company] if link['valid_from'] <= signal <= link['valid_to']]
        active = [link for link, why in dated if not why]
        if not active:
            if dated:
                identity_reasons.extend(reason for _, why in dated for reason in why)
            else:
                identity_reasons.append('SECURITY_LINK_OUTSIDE_SIGNAL_DAY' if by_company[company] else 'FIXED_SECURITY_LINK_MISSING')
        for link in active:
            failures = []
            sid, series = link.get('security_id'), link.get('series_id')
            fields = ('security_id', 'series_id', 'symbol', 'share_class', 'security_type', 'reference', 'identity_reference')
            kind = link.get('identifier_type')
            if (any(not _text(link.get(field)) for field in fields)
                    or not _text(kind) or kind not in SECURITY_IDENTIFIER_TYPES):
                failures.append('FIXED_SECURITY_LINK_EVIDENCE_REQUIRED')
            if link.get('identity_status') != 'CONFIRMED':
                failures.append('FIXED_SECURITY_LINK_UNCONFIRMED')
            if not _text(row.get('issuer_id')) or link.get('issuer_id') != row.get('issuer_id'):
                failures.append('ISSUER_LINK_MISMATCH')
            if sid in (company, row.get('issuer_id'), link.get('symbol')):
                failures.append('ISSUER_OR_TICKER_IS_NOT_SECURITY_ID')
            if (link.get('identifier_type') == 'SYNTHETIC_FIXED_SECURITY_ID' or str(sid).startswith('SYNTHETIC:')) and view['data_kind'] != 'SYNTHETIC':
                failures.append('SYNTHETIC_SECURITY_ID_ON_RETAINED_INPUT')
            ratio_ok, ratio = _ratio(link)
            if not ratio_ok:
                failures.append('ADR_RATIO_UNCONFIRMED')
            identity_failures = list(failures)
            identity_reasons.extend(identity_failures)
            found = by_series.get(series) if _text(series) else None
            if found is None:
                failures.append('MEASUREMENT_MISSING')
            else:
                index, measurement = found
                used.add(index)
                if measurement.get('signal_day') != signal:
                    failures.append('SIGNAL_DAY_MISMATCH')
                if measurement.get('security_id') != sid:
                    failures.append('SECURITY_LINK_MISMATCH')
                for field in ('symbol', 'share_class', 'security_type'):
                    if not _text(measurement.get(field)) or measurement.get(field) != link.get(field):
                        failures.append(field.upper() + '_MISMATCH')
                measured_ok, measured_ratio = _ratio(measurement)
                if not measured_ok or measured_ratio != ratio:
                    failures.append('ADR_RATIO_MISMATCH')
                bases = [measurement[key] for key in ('price_basis', 'chart_basis') if key in measurement]
                if not bases or any(basis != price_basis for basis in bases):
                    failures.append('PRICE_BASIS_MISMATCH')
                diagnostics[index]['reasons'].extend(failures)
            if not identity_failures:
                verified_ids.append(sid)
                if sector:
                    linked_ids[sector].append(sid)
                    projected = (dict(signal_day=signal, security_id=sid, series_id=series,
                                      metrics={name: dict(value=None, null_reasons=list(failures)) for name in METRIC_IDS})
                                 if failures else deepcopy(found[1]))
                    board_inputs[sector].append(projected)
            reasons.extend(failures)
        reasons = list(dict.fromkeys(identity_reasons + reasons))
        states.append(dict(company_id=company, issuer_id=row.get('issuer_id'), sector_id=sector,
                           classification_record_id=row.get('record_id'),
                           status='UNKNOWN' if identity_reasons else 'CONFIRMED', reasons=reasons,
                           measurement_status='PARTIAL' if reasons else 'COMPLETE', security_ids=verified_ids))
        if sector and identity_reasons:
            group_reasons[sector].extend(identity_reasons)
    for index, diagnostic in enumerate(diagnostics):
        if index not in used:
            diagnostic['reasons'].append('MEASUREMENT_NOT_LINKED')
        diagnostic['reasons'] = list(dict.fromkeys(diagnostic['reasons']))

    groups = []
    for sector in SECTORS:
        reasons = list(dict.fromkeys((['CLASSIFICATION_POPULATION_INCOMPLETE'] if unclassified else []) + group_reasons[sector]))
        status = 'UNKNOWN' if reasons else 'CONFIRMED'
        group = dict(group_id='COMMON:' + sector + ':' + price_basis, signal_day=signal, price_basis=price_basis,
                     membership_status=status, membership_source='common-classification:' + view['classification_hash'] if not reasons else None,
                     member_security_ids=linked_ids[sector] if not reasons else None)
        board = build_board(board_inputs[sector], group=group)
        relevant = [row for row in states if row['sector_id'] == sector]
        groups.append(dict(sector_id=sector, membership_status=status, membership_reasons=reasons,
                           counts=dict(company_members=len(relevant), confirmed_companies=sum(row['status'] == 'CONFIRMED' for row in relevant),
                                       verified_security_count=len(linked_ids[sector]), unclassified_companies=unclassified), board=board))
    return dict(schema_version='common-classification-technical/1', valuation_date=signal, data_kind=view['data_kind'],
                classification_hash=view['classification_hash'], price_basis=price_basis, groups=groups,
                input_hash=input_hash, cache_key=input_hash, settings_version=settings['settings_version'],
                rows=states, diagnostics=diagnostics, security_link_diagnostics=link_diagnostics,
                counts=dict(original_companies=len(view['members']), unclassified_companies=unclassified,
                            requested_measurements=len(measurements)))


def macro_projection(view, source_links=()):
    """Keep common classification, legacy SIC group and benchmark choice distinct.

    Optional macro-statistic links explicitly name source system/version/code,
    target_industry_id, relation, evidence_refs and [valid_from, valid_to).
    Targets must exist in the common dictionary. recorded_at and acquired_at are
    independently supplied review/evidence times, both known by knowledge_as_of.
    Equal-looking source codes never imply a match. No statistics are calculated.
    """
    companies = _rows(view)
    signal = view['valuation_date']
    active = []
    unavailable = []
    industries = {row['id'] for row in dictionary(view['dictionary_version'])['industries']}
    seen = set()
    for link in source_links:
        if ('valid_to' not in link
                or any(not _text(link.get(key)) for key in ('system', 'version', 'code', 'target_industry_id'))
                or link.get('relation') not in ('EXACT', 'SOURCE_BROADER', 'SOURCE_NARROWER', 'OVERLAP')
                or not isinstance(link.get('evidence_refs'), list) or not link['evidence_refs']
                or any(not _text(ref) for ref in link['evidence_refs'])):
            raise ValueError('MACRO_SOURCE_LINK_EVIDENCE_REQUIRED')
        if link['target_industry_id'] not in industries:
            raise ValueError('MACRO_TARGET_INDUSTRY_UNKNOWN')
        start = _day(link.get('valid_from'))
        end = link.get('valid_to')
        if end is not None and start >= _day(end):
            raise ValueError('INVALID_MACRO_SOURCE_LINK_RANGE')
        if start <= signal and (end is None or signal < end):
            reasons = _link_time_reasons(link, view['knowledge_as_of'], 'MACRO_LINK')
            if reasons:
                unavailable.append(dict(link=deepcopy(link), reasons=reasons))
                continue
            key = tuple(link[key] for key in ('system', 'version', 'code', 'target_industry_id'))
            if key in seen:
                raise ValueError('DUPLICATE_MACRO_SOURCE_LINK')
            seen.add(key)
            active.append(link)
    mapping = load_map()
    rows = []
    for company in view['members']:
        row = companies[company]
        source = row.get('source_sic')
        sic = source.get('code') if isinstance(source, dict) and source.get('system') == 'SEC_SIC' else None
        industry = row.get('industry', {})
        links = [deepcopy(link) for link in active if industry.get('status') == 'CONFIRMED' and link['target_industry_id'] == industry.get('id')]
        reasons = list(dict.fromkeys(reason for item in unavailable
                                    if item['link']['target_industry_id'] == industry.get('id')
                                    for reason in item['reasons']))
        rows.append(dict(company_id=company, issuer_id=row.get('issuer_id'), classification_record_id=row.get('record_id'),
            sector=deepcopy(row.get('sector')), industry=deepcopy(industry), source_classification=deepcopy(source),
            source_industry=dict(system='SEC_SIC', version=CONFIG_VERSION, **classify_sic(sic)),
            benchmark=dict(system='SEC_SIC', version=mapping['config_version'], **sector_benchmark(sic, mapping=mapping)),
            statistic_mapping=dict(status='LINKED' if links else 'UNKNOWN', source_links=links,
                                   reasons=[] if links else reasons or ['EXPLICIT_MACRO_SOURCE_LINK_MISSING']),
            probabilities=None, sector_returns=None))
    return dict(schema_version='common-classification-macro/1', valuation_date=signal, data_kind=view['data_kind'],
                classification_hash=view['classification_hash'], rows=rows, source_link_diagnostics=unavailable,
                source_industry_is_common_sector=False, benchmark_is_common_sector=False,
                probabilities=None, sector_returns=None)
