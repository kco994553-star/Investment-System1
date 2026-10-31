"""Strict research PIT adapter calling the unchanged operational factor engine.

Input bundle shapes (all dates ISO): companyfacts_by_cik maps zero-padded CIK
to SEC companyfacts JSON. Filings contain cik,filed,sic,accn (or adsh), optional
accepted/known_at. Membership contains cik,security_id,start,end (exclusive;
null means ongoing), optional known_at. Prices contain security_id,date,close,
optional volume/dollar_volume/open, currency, price_basis/shares_basis. V quotes
require both bases RAW and an explicit basis_alignment receipt identifying the
financial share period and filing; unknown bases remain unavailable. A receipt
has status=VERIFIED, source, signal_day, shares_period_end, shares_filing_accn,
verified_through=S, price_to_shares_factor and split_events (each with
effective_date, ratio, source). The factor must agree with its event bridge.
Historical month prices need their own receipt to that same financial basis.
`basis_alignments` may map each signal-day ISO string to its receipt, allowing
one immutable historical price observation to serve multiple rebalance dates.
Month closes also require is_month_end or a verified calendar month end.

No network, no price forward fill, no current SIC substitution, no fabricated
historical universe. Vintage status is RECONSTRUCTED_AS_OF; this filter cannot
prove that a vendor preserved every original filing.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import math
from statistics import median

from ...qgv import v2_factors
from ...qgv.sic_industry import classify_sic, normalize_sic
from .calendar_adapter import aware, day


def _finite(value, *, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (not positive or value > 0)


def _cik(value):
    value = str(value).strip() if value is not None else ''
    if not value.isdigit() or len(value) > 10 or int(value) == 0:
        raise ValueError('PERMANENT_ISSUER_ID_REQUIRED')
    return value.zfill(10)


def _visible(row, decision_at):
    for key in ('known_at', 'accepted'):
        if row.get(key) is not None:
            try:
                if aware(row[key]) > decision_at:
                    return False
            except (TypeError, ValueError):
                return False
    return True


def _accession(value):
    return str(value).replace('-', '').strip() if value is not None else ''


def _filing_evidence(rows):
    """Conservative, order-independent accession evidence, including availability.

    A later vendor availability or acceptance must not be overwritten by an
    earlier duplicate. Invalid timestamp evidence blocks that accession.
    """
    grouped = {}
    for row in rows:
        cik = _cik(row.get('cik'))
        accession = _accession(row.get('accn') or row.get('adsh'))
        if not accession:
            continue
        key = cik, accession
        current = grouped.setdefault(key, {'cik': cik, 'accn': accession})
        for marker in ('_invalid_time', '_sic_conflict'):
            if row.get(marker):
                current[marker] = True
        for field in ('accepted', 'known_at'):
            value = row.get(field)
            if value is None:
                continue
            try:
                at = aware(value)
                old = aware(current[field]) if current.get(field) is not None else None
                if old is None or at > old:
                    current[field] = at.isoformat()
            except (TypeError, ValueError):
                current['_invalid_time'] = True
        if row.get('filed') is not None:
            try:
                filed = day(str(row['filed'])).isoformat()
                current['filed'] = max(current.get('filed', filed), filed)
            except (TypeError, ValueError):
                current['_invalid_time'] = True
        sic = normalize_sic(row.get('sic'))
        if sic is not None:
            if current.get('sic') is not None and current['sic'] != sic:
                current['_sic_conflict'] = True
            current['sic'] = sic
        if current.get('_invalid_time'):
            current['known_at'] = 'INVALID_EVIDENCE'
    return grouped


def _decision(signal_day, decision_at=None):
    signal_day = day(signal_day)
    return aware(decision_at) if decision_at is not None else datetime.combine(signal_day, time.max, timezone.utc)


@dataclass(frozen=True)
class PITFacts:
    payload: dict
    cutoff: object
    provenance: tuple
    rejected: dict


def filter_companyfacts(companyfacts, signal_day, *, decision_at=None):
    """Keep only filed<S. Missing filed is never replaced with a fiscal end."""
    signal_day = day(signal_day)
    decision_at = _decision(signal_day, decision_at)
    if not isinstance(companyfacts, dict):
        raise ValueError('COMPANYFACTS_OBJECT_REQUIRED')
    payload = deepcopy(companyfacts)
    rejected, provenance = Counter(), []
    facts = payload.get('facts', {})
    if not isinstance(facts, dict):
        raise ValueError('COMPANYFACTS_FACTS_INVALID')
    for taxonomy, tags in facts.items():
        if not isinstance(tags, dict):
            raise ValueError('COMPANYFACTS_TAXONOMY_INVALID')
        for tag, info in tags.items():
            units = info.get('units', {}) if isinstance(info, dict) else {}
            if not isinstance(units, dict):
                raise ValueError('COMPANYFACTS_UNITS_INVALID')
            for unit, rows in units.items():
                kept = []
                if not isinstance(rows, list):
                    raise ValueError('COMPANYFACTS_ROWS_INVALID')
                for row in rows:
                    if not isinstance(row, dict):
                        rejected['INVALID_ROW'] += 1
                        continue
                    if row.get('filed') is None:
                        rejected['MISSING_FILED'] += 1
                        continue
                    try:
                        filed = day(str(row['filed']))
                    except (TypeError, ValueError):
                        rejected['INVALID_FILED'] += 1
                        continue
                    if filed >= signal_day or not _visible(row, decision_at):
                        rejected['NOT_PUBLIC_BEFORE_SIGNAL'] += 1
                        continue
                    if not _finite(row.get('val')):
                        rejected['NON_NUMERIC_VALUE'] += 1
                        continue
                    row.pop('frame', None)
                    kept.append(row)
                    provenance.append({'taxonomy': taxonomy, 'tag': tag, 'unit': unit, 'filed': filed.isoformat(),
                                       'accn': row.get('accn'), 'accepted': row.get('accepted'),
                                       'period_end': row.get('end')})
                units[unit] = kept
    return PITFacts(payload, signal_day - timedelta(days=1), tuple(provenance), dict(rejected))


def as_filed_sic(filing_rows, signal_day, cik=None, *, decision_at=None):
    signal_day = day(signal_day)
    decision_at = _decision(signal_day, decision_at)
    issuer = _cik(cik) if cik is not None else None
    eligible = []
    for row in _filing_evidence(filing_rows).values():
        try:
            if issuer is not None and _cik(row.get('cik')) != issuer:
                continue
            filed = day(str(row.get('filed')))
            accession = row.get('accn') or row.get('adsh')
            sic = None if row.get('_sic_conflict') else normalize_sic(row.get('sic'))
            if filed < signal_day and _visible(row, decision_at) and sic is not None and accession:
                eligible.append((filed, str(accession), sic, row))
        except (ValueError, TypeError):
            continue
    if not eligible:
        return {'sic': None, 'source': 'AS_FILED', 'reason': 'SIC_AS_FILED_NOT_AVAILABLE', 'accn': None, 'filed': None}
    filed, accn, sic, row = max(eligible, key=lambda x: (x[0], x[1]))
    return {'sic': sic, 'source': 'AS_FILED', 'reason': None, 'accn': accn, 'filed': filed.isoformat(),
            'accepted': row.get('accepted')}


def _price_index(prices, signal_day, *, decision_at=None):
    """Reject conflicting duplicate observations rather than input-order selection."""
    out = {}
    decision_at = _decision(signal_day, decision_at)
    for row in prices:
        sid = row.get('security_id')
        if not isinstance(sid, str) or not sid.strip():
            raise ValueError('PERMANENT_SECURITY_ID_REQUIRED')
        try:
            price_day = day(row.get('date'))
        except (ValueError, TypeError):
            raise ValueError('PRICE_DATE_INVALID') from None
        if price_day > signal_day or not _visible(row, decision_at):
            continue
        key = sid, price_day
        if key in out and out[key] != row:
            raise ValueError('CONFLICTING_PRICE_OBSERVATIONS')
        out[key] = row
    return out


def _basis_alignment(row, signal_day, price_day, decision_at):
    receipt = row.get('basis_alignment')
    if 'basis_alignments' in row:
        if not isinstance(row['basis_alignments'], dict):
            return None
        receipt = row['basis_alignments'].get(signal_day.isoformat(), receipt)
    if (not isinstance(receipt, dict) or receipt.get('status') != 'VERIFIED'
            or not isinstance(receipt.get('source'), str) or not receipt['source'].strip()
            or receipt.get('signal_day') != signal_day.isoformat()
            or receipt.get('verified_through') != signal_day.isoformat()
            or not _visible(receipt, decision_at)):
        return None
    try:
        share_day = day(receipt.get('shares_period_end'))
        basis_day = day(receipt.get('shares_basis_date', receipt.get('shares_period_end')))
        if share_day > signal_day or basis_day > signal_day:
            return None
        factor = receipt.get('price_to_shares_factor')
        if not _finite(factor, positive=True) or not isinstance(receipt.get('split_events'), list):
            return None
        product = 1.0
        seen = set()
        for event in receipt['split_events']:
            effective = day(event.get('effective_date'))
            if (not isinstance(event.get('source'), str) or not event['source'].strip()
                    or not min(price_day, basis_day) < effective <= max(price_day, basis_day)
                    or not _finite(event.get('ratio'), positive=True) or not _visible(event, decision_at)
                    or effective in seen):
                return None
            seen.add(effective)
            product *= event['ratio']
        expected = product if price_day >= basis_day else 1 / product
        if not _finite(expected, positive=True) or not math.isclose(factor, expected, rel_tol=1e-12):
            return None
        return receipt
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return None


def choose_share_classes(membership_rows, prices, signal_day, calendar):
    """One active security per CIK; sixty sessions ending at S, then ID ties.

    If any class lacks the full 60-session history, use permanent ID for the
    issuer and mark liquidity unconfirmed. Future rows cannot affect selection.
    """
    signal_day = day(signal_day)
    decision_at = calendar.session(signal_day).close_at
    sessions = calendar.completed_sessions(signal_day, 60)
    price_by_key = _price_index(prices, signal_day, decision_at=decision_at)
    issuers = defaultdict(dict)
    for row in membership_rows:
        start = day(row.get('start'))
        end = day(row['end']) if row.get('end') is not None else None
        if not start <= signal_day or (end is not None and signal_day >= end) or not _visible(row, decision_at):
            continue
        cik, sid = _cik(row.get('cik')), row.get('security_id')
        if not isinstance(sid, str) or not sid.strip():
            raise ValueError('PERMANENT_SECURITY_ID_REQUIRED')
        if sid in issuers[cik] and issuers[cik][sid] != row:
            raise ValueError('CONFLICTING_MEMBERSHIP_OBSERVATIONS')
        issuers[cik][sid] = row
    result = []
    for cik, classes in sorted(issuers.items()):
        medians = {}
        for sid in sorted(classes):
            values = []
            for session in sessions:
                row = price_by_key.get((sid, session.day), {})
                value = row.get('dollar_volume')
                if value is None and _finite(row.get('close'), positive=True) and _finite(row.get('volume')):
                    value = row['close'] * row['volume']
                if _finite(value) and value >= 0:
                    values.append(value)
            if len(sessions) == len(values) == 60:
                medians[sid] = median(values)
        confirmed = len(medians) == len(classes)
        selected = min(classes, key=lambda sid: (-medians[sid], sid)) if confirmed else min(classes)
        row = deepcopy(classes[selected])
        row.update(cik=cik, security_id=selected,
                   flags=[] if confirmed else ['SHARE_CLASS_LIQUIDITY_UNCONFIRMED'],
                   liquidity_median=medians.get(selected), liquidity_sessions=60 if confirmed else None)
        result.append(row)
    return tuple(result)


def quotes_as_of(prices, signal_day, *, calendar=None):
    """S close plus confirmed historical month closes, same raw share basis."""
    signal_day = day(signal_day)
    decision_at = calendar.session(signal_day).close_at if calendar is not None else None
    decision_at = _decision(signal_day, decision_at)
    index = _price_index(prices, signal_day, decision_at=decision_at)
    by_security = defaultdict(list)
    for (sid, price_day), row in index.items():
        by_security[sid].append((price_day, row))
    result = {}
    for sid, history in sorted(by_security.items()):
        signal = index.get((sid, signal_day))
        if (not signal or not _finite(signal.get('close'), positive=True) or signal.get('currency') != 'USD'
                or signal.get('price_basis') != 'RAW' or signal.get('shares_basis') != 'RAW'):
            continue
        alignment = _basis_alignment(signal, signal_day, signal_day, decision_at)
        if alignment is None:
            continue
        month_closes = {}
        for price_day, row in sorted(history):
            if (not _finite(row.get('close'), positive=True) or row.get('currency') != signal['currency']
                    or row.get('price_basis') != 'RAW' or row.get('shares_basis') != 'RAW'):
                continue
            historical_alignment = _basis_alignment(row, signal_day, price_day, decision_at)
            if (historical_alignment is None
                    or historical_alignment.get('shares_period_end') != alignment.get('shares_period_end')
                    or _accession(historical_alignment.get('shares_filing_accn')) !=
                    _accession(alignment.get('shares_filing_accn'))):
                continue
            last = row.get('is_month_end') is True
            if calendar is not None:
                # Completeness of this calendar month must be inside coverage.
                next_month = (price_day.replace(day=28) + timedelta(days=4)).replace(day=1)
                if next_month <= calendar.coverage_end:
                    last = calendar.previous_session(next_month).day == price_day
            if last:
                month_closes[price_day.strftime('%Y-%m')] = row['close'] * historical_alignment['price_to_shares_factor']
        result[sid] = {'price': signal['close'] * alignment['price_to_shares_factor'], 'currency': signal['currency'],
                       'month_closes': month_closes, 'basis_alignment': deepcopy(alignment)}
    return result


def build_pit_rows(companyfacts_by_cik, filing_rows, membership_rows, prices, signal_day, calendar):
    """Construct operational Q/G input rows over the historical, deduped universe."""
    signal_day = day(signal_day)
    decision_at = calendar.session(signal_day).close_at
    out = {}
    facts_by_cik = {_cik(cik): payload for cik, payload in companyfacts_by_cik.items()}
    evidence = _filing_evidence(filing_rows)
    evidence_by_cik = defaultdict(list)
    for (cik, _), filing in evidence.items():
        evidence_by_cik[cik].append(filing)
    for identity in choose_share_classes(membership_rows, prices, signal_day, calendar):
        cik, sid = identity['cik'], identity['security_id']
        sic = as_filed_sic(evidence_by_cik[cik], signal_day, cik, decision_at=decision_at)
        row = {'security_id': sid, 'cik': cik, 'state': 'NOT_AVAILABLE', 'profile': None,
               'sic': sic['sic'], 'industry_group': classify_sic(sic['sic'])['group'],
               'fiscal_year_end': None, 'currency': None, 'metrics': {}, 'v_inputs_v2': v2_factors.empty_v_inputs(),
               'calc_version': v2_factors.CALC_VERSION, 'flags': list(identity['flags']),
               'reason_codes': [], 'provenance': {'signal_day': signal_day.isoformat(),
                   'decision_at': decision_at.isoformat(), 'vintage_status': 'RECONSTRUCTED_AS_OF',
                   'sic': sic, 'membership_source': identity.get('source'), 'facts': (), 'rejected': {}}}
        if sic['sic'] is None:
            row['reason_codes'].append('SIC_AS_FILED_NOT_AVAILABLE')
        elif cik not in facts_by_cik:
            row['reason_codes'].append('COMPANYFACTS_NOT_AVAILABLE')
        else:
            payload = facts_by_cik[cik]
            if _cik(payload.get('cik')) != cik:
                raise ValueError('COMPANYFACTS_CIK_MISMATCH')
            # Join acceptance evidence without copying later issuer state into history.
            payload = deepcopy(payload)
            for tags in payload.get('facts', {}).values():
                for info in tags.values():
                    for values in info.get('units', {}).values():
                        for value in values:
                            filing = evidence.get((cik, _accession(value.get('accn'))), {})
                            for field in ('accepted', 'known_at'):
                                if filing.get(field) is not None:
                                    # Include the original fact's own evidence in the conservative join.
                                    previous = value.get(field)
                                    try:
                                        value[field] = max(aware(previous), aware(filing[field])).isoformat() if previous else filing[field]
                                    except (TypeError, ValueError):
                                        value[field] = 'INVALID_EVIDENCE'
                            if filing.get('filed'):
                                try:
                                    value['filed'] = max(day(value.get('filed')), day(filing['filed'])).isoformat()
                                except (TypeError, ValueError):
                                    value['filed'] = 'INVALID_EVIDENCE'
            view = filter_companyfacts(payload, signal_day, decision_at=decision_at)
            diagnostics = {}
            profile, fy_end, currency, metrics, v_inputs = v2_factors.compute(
                view.payload, sic=sic['sic'], cutoff=view.cutoff, diagnostics=diagnostics)
            row.update(profile=profile, fiscal_year_end=fy_end, currency=currency, metrics=metrics, v_inputs_v2=v_inputs)
            row['provenance'].update(facts=view.provenance, rejected=view.rejected, cutoff=view.cutoff.isoformat())
            row['provenance']['shares_basis'] = diagnostics.get('diluted_shares')
            if fy_end is not None:
                row['state'] = 'LIVE'
            else:
                row['reason_codes'].append('NO_PUBLIC_ANNUAL_FACTS')
        out[sid] = row
    return out
