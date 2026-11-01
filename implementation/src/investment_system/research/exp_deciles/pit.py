"""Point-in-time SEC rows for a signal day S under the 6th-session filing rule.

Ported from research/qgv_backtest @ 56a0e8ce (#417/#430) and changed for EXP-STOCK-INDICATOR-DECILES-v1:
pit_adapter.filter_companyfacts (L119), pit_adapter.as_filed_sic (L172) and the per-issuer part of pit_adapter.build_pit_rows
(L339). Changed:

- the fact filter was `filed < S`; it is now `filed <= schedule.compute_cutoff(S)`, i.e. exactly the facts whose filing is
  usable at S (usable_from(F) = the 6th NYSE session after the New York filing date F, usable iff usable_from(F) <= S);
- acceptance / vendor known_at times are not read: with 5 full sessions between F and first use, the filing date alone
  decides (settings doc section 1). companyfacts carries the filing date only, which is enough;
- membership, share-class choice and quotes are not built here (universe.py / the price part own them);
- each row records the signal day S, the execution day T, both cutoffs and the filings it used, each with its usable date;
- a missing as-filed SIC no longer drops the row (review SYN-2, conformance with calc 23.1's own missing-data rule; owner
  11/01: the original QGV missing-data rule is kept and 15-factor completeness is not a new selection condition): the row
  keeps the reason SIC_AS_FILED_NOT_AVAILABLE and is still computed with sic=None, which calc 23.1 scores as GENERAL with
  industry group NA (universe fallback, v2_factors.profile_for_sic(None)). A current SIC is never substituted.

How v2_factors.compute treats `cutoff` (checked in qgv/v2_factors.py: _Facts._table, _share_filings, _split_ratios,
_cover_counts and _taxonomy_and_currency): a fact is kept iff its `filed` (strict YYYY-MM-DD string) is <= cutoff; a fact
without a parseable `filed` is ignored. So passing cutoff = compute_cutoff(S) (the last calendar date with
usable_from <= S) makes the 6th-session rule hold exactly, also for filing dates on non-session days. The filter below
applies the same comparison first, so the facts compute sees and the facts this module records are the same set.

Amendments: each companyfacts row is one filing's report of one period; a 10-K/A or a later comparative row has its own
filing date and becomes usable only on its own usable date, while v2_factors keeps the latest usable filing of a period
(same-day conflicts dropped). The companyfacts `frame` tag is hindsight and is removed from every row.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
import math
import re

from ...qgv import v2_factors
from ...qgv.sic_industry import classify_sic, normalize_sic
from . import schedule

RULE = 'FILED_NY_DATE_PLUS_5_FULL_NYSE_SESSIONS_USABLE_ON_6TH_SESSION'
SIC_SOURCE = 'AS_FILED'
_FILED = re.compile(r'\d{4}-\d{2}-\d{2}')

# reason codes
MISSING_FILED = 'MISSING_FILED'
INVALID_FILED = 'INVALID_FILED'
INVALID_ROW = 'INVALID_ROW'
NON_NUMERIC_VALUE = 'NON_NUMERIC_VALUE'
NOT_USABLE_AT_SIGNAL_DAY = 'NOT_USABLE_AT_SIGNAL_DAY'
SIC_AS_FILED_NOT_AVAILABLE = 'SIC_AS_FILED_NOT_AVAILABLE'
COMPANYFACTS_NOT_AVAILABLE = 'COMPANYFACTS_NOT_AVAILABLE'
NO_PUBLIC_ANNUAL_FACTS = 'NO_PUBLIC_ANNUAL_FACTS'


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _cik(value):
    value = str(value).strip() if value is not None else ''
    if not value.isdigit() or len(value) > 10 or int(value) == 0:
        raise ValueError('PERMANENT_ISSUER_ID_REQUIRED')
    return value.zfill(10)


def _accession(value):
    return str(value).replace('-', '').strip() if value is not None else ''


def _filed(value):
    """The filing date exactly as v2_factors._day reads it (strict YYYY-MM-DD string), else None."""
    if not isinstance(value, str) or not _FILED.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def signal_context(signal_day, execution_day=None):
    """{'signal_day', 'execution_day', 'filing_cutoff', 'compute_cutoff', 'rule'} for S (ISO dates).

    T defaults to the next session after S; a supplied T must be exactly that session (annual rule: S is the session
    before T)."""
    signal = schedule._signal(signal_day)
    expected = schedule.next_session(signal)
    execution = expected if execution_day is None else schedule._day(execution_day)
    if execution != expected:
        raise ValueError('EXECUTION_DAY_NOT_NEXT_SESSION')
    return {'signal_day': signal.isoformat(), 'execution_day': execution.isoformat(),
            'filing_cutoff': schedule.filing_cutoff(signal).isoformat(),
            'compute_cutoff': schedule.compute_cutoff(signal).isoformat(), 'rule': RULE}


@dataclass(frozen=True)
class PITFacts:
    payload: dict
    signal_day: object
    compute_cutoff: object
    filings: tuple      # distinct kept filings: {'accn', 'filed', 'usable_from'}, sorted by (filed, accn)
    rejected: dict      # reason code -> row count


def filter_companyfacts(companyfacts, signal_day):
    """Keep only rows usable at S; never fill a missing filing date from a period end. Input is not modified."""
    signal = schedule._signal(signal_day)
    cutoff = schedule.compute_cutoff(signal)
    if not isinstance(companyfacts, dict):
        raise ValueError('COMPANYFACTS_OBJECT_REQUIRED')
    payload = deepcopy(companyfacts)
    facts = payload.get('facts', {})
    if not isinstance(facts, dict):
        raise ValueError('COMPANYFACTS_FACTS_INVALID')
    rejected, kept_filings = Counter(), set()
    for tags in facts.values():
        if not isinstance(tags, dict):
            raise ValueError('COMPANYFACTS_TAXONOMY_INVALID')
        for info in tags.values():
            units = info.get('units', {}) if isinstance(info, dict) else {}
            if not isinstance(units, dict):
                raise ValueError('COMPANYFACTS_UNITS_INVALID')
            for unit, rows in units.items():
                if not isinstance(rows, list):
                    raise ValueError('COMPANYFACTS_ROWS_INVALID')
                kept = []
                for row in rows:
                    if not isinstance(row, dict):
                        rejected[INVALID_ROW] += 1
                        continue
                    if row.get('filed') is None:
                        rejected[MISSING_FILED] += 1
                        continue
                    filed = _filed(row['filed'])
                    if filed is None:
                        rejected[INVALID_FILED] += 1
                        continue
                    if filed > cutoff:
                        rejected[NOT_USABLE_AT_SIGNAL_DAY] += 1
                        continue
                    if not _finite(row.get('val')):
                        rejected[NON_NUMERIC_VALUE] += 1
                        continue
                    row.pop('frame', None)
                    kept.append(row)
                    kept_filings.add((filed, _accession(row.get('accn'))))
                units[unit] = kept
    usable = {}
    filings = []
    for filed, accn in sorted(kept_filings):
        if filed not in usable:
            usable[filed] = schedule.usable_from(filed).isoformat()
        filings.append({'accn': accn or None, 'filed': filed.isoformat(), 'usable_from': usable[filed]})
    return PITFacts(payload, signal, cutoff, tuple(filings), dict(rejected))


def as_filed_sic(filing_rows, signal_day, cik=None):
    """SIC of the latest filing usable at S that carries one: {'sic', 'source', 'reason', 'accn', 'filed', 'usable_from'}.

    Filing rows: {cik, accn (or adsh), filed, sic}. Duplicate rows of one accession keep the latest filing date; two
    different SICs on one accession leave that accession without a SIC. Never filled from a current SIC."""
    signal = schedule._signal(signal_day)
    cutoff = schedule.compute_cutoff(signal)
    issuer = _cik(cik) if cik is not None else None
    grouped = {}
    for row in filing_rows or ():
        if not isinstance(row, dict):
            continue
        try:
            row_cik = _cik(row.get('cik'))
        except ValueError:
            continue
        accn = _accession(row.get('accn') or row.get('adsh'))
        if not accn or (issuer is not None and row_cik != issuer):
            continue
        current = grouped.setdefault((row_cik, accn), {'accn': accn, 'filed': None, 'sic': None, 'invalid': False,
                                                       'conflict': False})
        filed = _filed(row.get('filed'))
        if filed is None:
            current['invalid'] = True
        elif current['filed'] is None or filed > current['filed']:
            current['filed'] = filed
        sic = normalize_sic(row.get('sic'))
        if sic is not None:
            if current['sic'] is not None and current['sic'] != sic:
                current['conflict'] = True
            current['sic'] = sic
    eligible = [g for g in grouped.values() if not g['invalid'] and not g['conflict'] and g['sic'] is not None
                and g['filed'] is not None and g['filed'] <= cutoff]
    if not eligible:
        return {'sic': None, 'source': SIC_SOURCE, 'reason': SIC_AS_FILED_NOT_AVAILABLE, 'accn': None, 'filed': None,
                'usable_from': None}
    best = max(eligible, key=lambda g: (g['filed'], g['accn']))
    return {'sic': best['sic'], 'source': SIC_SOURCE, 'reason': None, 'accn': best['accn'],
            'filed': best['filed'].isoformat(), 'usable_from': schedule.usable_from(best['filed']).isoformat()}


def _sic_of(sic_record):
    """The SIC of an as_filed_sic record; a bare string is refused so a current SIC cannot slip in."""
    if sic_record is None:
        return None
    if not isinstance(sic_record, dict) or sic_record.get('source') != SIC_SOURCE:
        raise TypeError('AS_FILED_SIC_RECORD_REQUIRED')
    return normalize_sic(sic_record.get('sic'))


def compute_row(companyfacts, *, sic_record, signal_day, execution_day=None, cik=None, security_id=None):
    """One operational-shape input row for v2_scoring.score_rows, computed with the 6th-session cutoff. A missing
    as-filed SIC is recorded (SIC_AS_FILED_NOT_AVAILABLE) and the row is computed with sic=None (GENERAL, industry NA).

    Shape (as universe.sec_qgv2.build_row plus `security_id` and `pit`): security_id, cik, state LIVE | NOT_AVAILABLE,
    profile, sic, industry_group, fiscal_year_end, currency, metrics (None kept for missing), v_inputs_v2, calc_version,
    reason_codes, pit = {signal_day, execution_day, filing_cutoff, compute_cutoff, rule, sic, latest_filing_used
    ({accn, filed, usable_from} | None), filings_used, rejected, shares_basis}. filings_used are the distinct filings
    whose facts were handed to compute (each with its usable date); latest_filing_used is the latest of them;
    shares_basis is compute's diluted-share diagnostic (value, period_end, accn) for the price part's basis checks."""
    ctx = signal_context(signal_day, execution_day)
    sic = _sic_of(sic_record)
    if cik is None and isinstance(companyfacts, dict):
        cik = companyfacts.get('cik')
    cik = _cik(cik)
    industry = classify_sic(sic)
    row = {'security_id': security_id, 'cik': cik, 'state': 'NOT_AVAILABLE', 'profile': None, 'sic': sic,
           'industry_group': industry['group'], 'fiscal_year_end': None, 'currency': None,
           'metrics': dict.fromkeys(v2_factors.METRIC_KEYS), 'v_inputs_v2': v2_factors.empty_v_inputs(),
           'calc_version': v2_factors.CALC_VERSION, 'reason_codes': [],
           'pit': dict(ctx, sic=deepcopy(sic_record), latest_filing_used=None, filings_used=(), rejected={},
                       shares_basis=None)}
    if sic is None:
        # calc 23.1: no SIC -> GENERAL, industry NA (universe fallback); the row is still computed (review SYN-2).
        row['reason_codes'].append(SIC_AS_FILED_NOT_AVAILABLE)
    if not isinstance(companyfacts, dict):
        row['reason_codes'].append(COMPANYFACTS_NOT_AVAILABLE)
        return row
    if _cik(companyfacts.get('cik')) != cik:
        raise ValueError('COMPANYFACTS_CIK_MISMATCH')
    view = filter_companyfacts(companyfacts, ctx['signal_day'])
    diagnostics = {}
    profile, fy_end, currency, metrics, v_inputs = v2_factors.compute(
        view.payload, sic=sic, cutoff=view.compute_cutoff, diagnostics=diagnostics)
    row.update(profile=profile, fiscal_year_end=fy_end, currency=currency, metrics=metrics, v_inputs_v2=v_inputs)
    row['pit'].update(filings_used=view.filings, rejected=view.rejected,
                      latest_filing_used=dict(view.filings[-1]) if view.filings else None,
                      shares_basis=deepcopy(diagnostics.get('diluted_shares')))
    if fy_end is not None:
        row['state'] = 'LIVE'
    else:
        row['reason_codes'].append(NO_PUBLIC_ANNUAL_FACTS)
    return row


def build_rows(companyfacts_by_cik, filing_rows, issuers, signal_day, execution_day=None):
    """{security_id: compute_row(...)} for issuers = iterable of {'cik', 'security_id'} (e.g. the U-A representatives).

    companyfacts_by_cik maps a CIK (any zero padding) to its companyfacts JSON; as-filed SIC comes from filing_rows."""
    facts_by_cik = {_cik(k): v for k, v in (companyfacts_by_cik or {}).items()}
    filings = list(filing_rows or ())
    out = {}
    for issuer in issuers:
        cik, sid = _cik(issuer['cik']), issuer['security_id']
        if not isinstance(sid, str) or not sid.strip():
            raise ValueError('PERMANENT_SECURITY_ID_REQUIRED')
        if sid in out:
            raise ValueError('DUPLICATE_SECURITY_ID')
        out[sid] = compute_row(facts_by_cik.get(cik), sic_record=as_filed_sic(filings, signal_day, cik),
                               signal_day=signal_day, execution_day=execution_day, cik=cik, security_id=sid)
    return out
