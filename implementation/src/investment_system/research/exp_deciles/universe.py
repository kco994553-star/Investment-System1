"""U-A / U-B membership at one signal day S from caller-supplied security records. Pure; no data is fetched.

Ported from research/qgv_backtest @ 56a0e8ce (#417/#430) and changed for EXP-STOCK-INDICATOR-DECILES-v1:
pit_adapter.choose_share_classes (L251: one security per CIK, highest median dollar volume, ties by permanent ID, else the
lowest ID flagged SHARE_CLASS_LIQUIDITY_UNCONFIRMED). Changed: a supplied representative flag is used first; the median
dollar volume is a supplied input (no 60-session price window is read here); the fallback flag is REPRESENTATIVE_UNCONFIRMED;
the issuer nominal market cap (class sum, ADR rule), the security-type scope, the U-A entry/stay hysteresis, the U-B
threshold and the candidate / eligible / excluded / unknown counts are new.

Security types (owner decision 2026-10-30, implementation/docs/expanded_universe/EXPANDED_DEFINITION_20261030.md section
1.2; canonical names of universe.expanded_catalog.SECURITY_TYPES):
  eligible (settings.ELIGIBLE_SECURITY_TYPES)   COMMON, COMMON_CLASS (each class; the issuer is counted once), ADR (ADR/ADS),
                                                 REIT
  excluded (settings.EXCLUDED_SECURITY_TYPES)   ETF, CLOSED_END_FUND, PREFERRED, WARRANT, RIGHT, UNIT
                                                 -> EXCLUDED with NOT_ELIGIBLE_SECURITY_TYPE
  None                                           -> UNKNOWN with SECURITY_TYPE_UNKNOWN
  any other string (not a canonical name)        -> UNKNOWN with SECURITY_TYPE_NOT_CANONICAL (a mapping gap is not a rule
                                                    exclusion)

Record (one per security at S; dict keys):
  security_id           fixed security ID (required, non-empty str)
  cik                   issuer CIK (digits, any padding) or None = unknown
  listed                True / False / None = unknown (listed on S)
  security_type         canonical type name (see above) or None = unknown
  shares_outstanding    class shares outstanding at S: Decimal / int / decimal str, or None (float refused); for an ADR the
                        issuer's ORDINARY shares outstanding (e.g. the 20-F cover), not the ADS count
  shares_filed          New York filing date (ISO text or date) of the SEC filing the share count comes from (review F2).
                        Missing -> SHARES_FILED_MISSING; not usable at S under the 6th-session rule (schedule.is_usable)
                        -> SHARES_NOT_USABLE_AT_S. Either leaves the issuer UNKNOWN, never a threshold exclusion
  shares_period_end     the date the share count is as of (ISO text or date); missing -> SHARES_PERIOD_END_MISSING, later
                        than shares_filed -> SHARES_PERIOD_END_AFTER_FILED (UNKNOWN)
  share_price_basis     split-basis status of this share count against the price used at S, supplied by the price part:
                        'CONFIRMED' = same split basis (no split between the share count and S, or the count is
                        restated); anything else (None, 'UNCONFIRMED', 'SPLIT_AFTER_SHARE_COUNT', ...) ->
                        SHARE_PRICE_BASIS_UNCONFIRMED (UNKNOWN: a basis gap is never a rule exclusion)
  price                 price at S: Decimal / int / decimal str, or None; price_label names it (e.g. a labelled proxy); for
                        an ADR the ADS price
  adr_ratio             ADR only: ordinary shares per ADS (Decimal / int / decimal str, > 0). Missing or unusable (None,
                        float, bool, text, <= 0) -> the issuer cap is NA with ADR_RATIO_UNCONFIRMED; ignored for other types
  representative        supplied representative flag True / False / None
  median_dollar_volume  input of the representative rule (Decimal / int / str, or None)
  same_economic_rights  for an unlisted eligible-type class: True values it at the representative's price; False / None -> NA

Issuer nominal market cap (Decimal, precision 50) = sum over the issuer's eligible-type classes (COMMON, COMMON_CLASS,
REIT) of shares x price, where a listed class uses its own price and an unlisted class uses the representative's price
only when same_economic_rights is True. An ADR issuer's cap = ordinary shares outstanding / adr_ratio x ADS price (the
ADR stands for the whole ordinary class); an ADR next to any other eligible-type record of the same issuer (a second ADR,
an ordinary or REIT class) could count the ordinary class twice, so that cap is NA with ADR_CLASS_OVERLAP_UNCONFIRMED.
Any missing or unusable input of any (possibly) eligible class makes the cap NA with reasons; it is never partially summed.
A class can only be summed into its issuer through its CIK: a record without a CIK is its own UNKNOWN unit
('SECURITY:<id>'), so an issuer with no history that has such a class next to its CIK-carrying classes is summed only
over the latter (the input must carry a CIK on every record for the cap to be complete). An issuer WITH history (a
previous U-A member or previous UNKNOWN unit) is protected by the class IDs carried with it (review U1 / M1, below).

Membership: U-A first build (previous_u_a is None): cap >= entry. Later S: a previous U-A member stays iff cap >= stay;
any other issuer enters iff cap >= entry. U-B: cap >= 10bn at that S, no hysteresis. NA cap -> UNKNOWN, never EXCLUDED.

Unknown carried to the next S (review F3; settings doc section 5: a missing input is never a legitimate exclusion): the
previous S's U-A UNKNOWN units (previous_u_a_unknown, unit IDs: CIKs or 'SECURITY:<id>') are carried with the members.
An issuer whose previous status was UNKNOWN is ELIGIBLE at cap >= entry, EXCLUDED at cap < stay (either way) and UNKNOWN
with PREVIOUS_U_A_STATUS_UNKNOWN in [stay, entry). A previous member or previous UNKNOWN unit without any record at S is
an UNKNOWN candidate (NOT_IN_RECORDS_AT_S) in both groups, unless an evidenced termination of that unit is supplied
(terminations: [{'cik' (an issuer CIK, or 'SECURITY:<id>' for a carried CIK-less unit; review M2), 'evidence', 'filed'
(NY filing date of the evidence, usable at S under the 6th-session rule), 'effective_date'}]). A termination counts only
when its filing is usable at S AND its effective_date is supplied and <= S (review U2); such a unit is no longer a
candidate and is listed in U_A.terminated and transitions.left. A usable termination without an effective date
(TERMINATION_EFFECTIVE_DATE_MISSING) or not yet effective at S (TERMINATION_NOT_EFFECTIVE_AT_S, e.g. a pending merger)
leaves the unit an UNKNOWN candidate carried to the next S.
Class IDs carried (review U1 / M1; previous_u_a_securities = the previous U_A.unit_securities): {unit ID: the security
IDs of its eligible or possibly eligible classes (definitively excluded types left out)} for every previous member and
UNKNOWN unit. At S a CIK-less record whose security ID is a carried class of a previous issuer is attached to that issuer
(not counted as a separate SECURITY unit) and makes its cap NA (CIK_UNKNOWN); a carried class with no record attached to
the issuer at S (missing, or now under another CIK) makes its cap NA (CLASS_RECORD_NOT_ATTACHED_AT_S). Either way the
issuer is UNKNOWN in both groups, never partially summed into a threshold exclusion, and the unresolved class IDs stay
carried. Without previous_u_a_securities (direct calls only; the runner always passes it) no class is tracked.
The result's U_A.members, U_A.unknown and U_A.unit_securities are exactly what the next S needs.

Counting unit = issuer: each known CIK, plus each security without a CIK that could be a listed eligible security (it
cannot be attached to an issuer, so it is its own unknown unit), plus each carried unit without a record at S.
candidate = eligible + excluded + unknown for every group; each unit is counted once under its first reason
(`*_by_reason`), its full reason list stays on the unit.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext

from .. import pit_filings
from . import schedule, settings

SCHEMA = 'exp-deciles-universe/1'
ELIGIBLE, EXCLUDED, UNKNOWN = 'ELIGIBLE', 'EXCLUDED', 'UNKNOWN'
DECIMAL_PRECISION = 50

# reason codes (UPPER_SNAKE): exclusions by rule
NOT_LISTED = 'NOT_LISTED'
NOT_ELIGIBLE_SECURITY_TYPE = 'NOT_ELIGIBLE_SECURITY_TYPE'
NO_LISTED_ELIGIBLE_SECURITY = 'NO_LISTED_ELIGIBLE_SECURITY'
BELOW_U_A_ENTRY = 'BELOW_U_A_ENTRY_THRESHOLD'
BELOW_U_A_STAY = 'BELOW_U_A_STAY_THRESHOLD'
BELOW_U_B = 'BELOW_U_B_THRESHOLD'
# reason codes: unknown (missing or unusable input)
CIK_UNKNOWN = 'CIK_UNKNOWN'
CIK_INVALID = 'CIK_INVALID'
LISTING_STATUS_UNKNOWN = 'LISTING_STATUS_UNKNOWN'
SECURITY_TYPE_UNKNOWN = 'SECURITY_TYPE_UNKNOWN'
SECURITY_TYPE_NOT_CANONICAL = 'SECURITY_TYPE_NOT_CANONICAL'
ADR_RATIO_UNCONFIRMED = 'ADR_RATIO_UNCONFIRMED'
ADR_CLASS_OVERLAP_UNCONFIRMED = 'ADR_CLASS_OVERLAP_UNCONFIRMED'
SHARES_OUTSTANDING_MISSING = 'SHARES_OUTSTANDING_MISSING'
SHARES_OUTSTANDING_INVALID = 'SHARES_OUTSTANDING_INVALID'
PRICE_MISSING = 'PRICE_MISSING'
PRICE_INVALID = 'PRICE_INVALID'
UNLISTED_CLASS_RIGHTS_UNKNOWN = 'UNLISTED_CLASS_RIGHTS_UNKNOWN'
UNLISTED_CLASS_RIGHTS_DIFFER = 'UNLISTED_CLASS_RIGHTS_DIFFER'
MARKET_CAP_NOT_AVAILABLE = 'MARKET_CAP_NOT_AVAILABLE'
SHARES_FILED_MISSING = 'SHARES_FILED_MISSING'
SHARES_PERIOD_END_MISSING = 'SHARES_PERIOD_END_MISSING'
SHARES_PERIOD_END_AFTER_FILED = 'SHARES_PERIOD_END_AFTER_FILED'
SHARES_FILED_OUTSIDE_CALENDAR = 'SHARES_FILED_OUTSIDE_CALENDAR'
SHARES_NOT_USABLE_AT_S = 'SHARES_NOT_USABLE_AT_S'
SHARE_PRICE_BASIS_UNCONFIRMED = 'SHARE_PRICE_BASIS_UNCONFIRMED'
SHARE_PRICE_BASIS_CONFIRMED = 'CONFIRMED'
PREVIOUS_U_A_STATUS_UNKNOWN = 'PREVIOUS_U_A_STATUS_UNKNOWN'
# a previous member / previous UNKNOWN unit without any record at S (an UNKNOWN candidate), or with termination evidence
NOT_IN_RECORDS_AT_S = 'NOT_IN_RECORDS_AT_S'
TERMINATION_EVIDENCED = 'TERMINATION_EVIDENCED'
TERMINATION_NOT_EFFECTIVE_AT_S = 'TERMINATION_NOT_EFFECTIVE_AT_S'
TERMINATION_EFFECTIVE_DATE_MISSING = 'TERMINATION_EFFECTIVE_DATE_MISSING'
# a carried class ID of a previous issuer is not attached to it at S (missing, or under another CIK; review U1)
CLASS_RECORD_NOT_ATTACHED_AT_S = 'CLASS_RECORD_NOT_ATTACHED_AT_S'
SECURITY_UNIT_PREFIX = 'SECURITY:'
# representative sources and flags
REP_SUPPLIED_FLAG = 'SUPPLIED_FLAG'
REP_ONLY_CLASS = 'ONLY_LISTED_ELIGIBLE_CLASS'
REP_MEDIAN_DOLLAR_VOLUME = 'HIGHEST_MEDIAN_DOLLAR_VOLUME'
REP_LOWEST_ID = 'LOWEST_SECURITY_ID'
REPRESENTATIVE_UNCONFIRMED = 'REPRESENTATIVE_UNCONFIRMED'
REPRESENTATIVE_FLAG_CONFLICT = 'REPRESENTATIVE_FLAG_CONFLICT'
REPRESENTATIVE_FLAG_NOT_LISTED_ELIGIBLE = 'REPRESENTATIVE_FLAG_NOT_LISTED_ELIGIBLE'


def _decimal(value, field):
    """Decimal / int / decimal string -> finite Decimal; None stays None; float and bool are refused (exact arithmetic)."""
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(field.upper() + '_DECIMAL_REQUIRED')
    if isinstance(value, Decimal):
        out = value
    elif isinstance(value, int):
        out = Decimal(value)
    elif isinstance(value, str):
        try:
            out = Decimal(value.strip())
        except InvalidOperation:
            raise ValueError(field.upper() + '_INVALID') from None
    else:
        raise TypeError(field.upper() + '_DECIMAL_REQUIRED')
    if not out.is_finite():
        raise ValueError(field.upper() + '_INVALID')
    return out


def _date(value, field):
    """ISO text or date -> date; None stays None; anything else is refused."""
    if value is None:
        return None
    if type(value) is date:
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError(field.upper() + '_INVALID') from None
    raise TypeError(field.upper() + '_MUST_BE_DATE')


def _adr_ratio(value):
    """Ordinary shares per ADS as a positive finite Decimal, else None (missing or unusable: the cap rule makes it NA)."""
    try:
        ratio = _decimal(value, 'adr_ratio')
    except (TypeError, ValueError):
        return None
    return ratio if ratio is not None and ratio > 0 else None


def _tristate(value, field):
    if value not in (True, False, None) or (value is not None and not isinstance(value, bool)):
        raise TypeError(field.upper() + '_MUST_BE_TRUE_FALSE_OR_NONE')
    return value


def _cik(value):
    """(cik, reason): zero-padded CIK, or (None, CIK_UNKNOWN / CIK_INVALID)."""
    if value is None:
        return None, CIK_UNKNOWN
    if isinstance(value, bool):
        return None, CIK_INVALID
    text = str(value).strip()
    if not text.isdigit() or len(text) > 10 or int(text) == 0:
        return None, CIK_INVALID
    return text.zfill(10), None


def normalize_record(record):
    """A validated, normalized copy of one security record (see module doc)."""
    if not isinstance(record, dict):
        raise TypeError('SECURITY_RECORD_MUST_BE_DICT')
    sid = record.get('security_id')
    if not isinstance(sid, str) or not sid.strip():
        raise ValueError('PERMANENT_SECURITY_ID_REQUIRED')
    cik, cik_reason = _cik(record.get('cik'))
    security_type = record.get('security_type')
    if security_type is not None and (not isinstance(security_type, str) or not security_type.strip()):
        raise TypeError('SECURITY_TYPE_MUST_BE_STR_OR_NONE')
    label = record.get('price_label')
    if label is not None and not isinstance(label, str):
        raise TypeError('PRICE_LABEL_MUST_BE_STR_OR_NONE')
    basis = record.get('share_price_basis')
    if basis is not None and (not isinstance(basis, str) or not basis.strip()):
        raise TypeError('SHARE_PRICE_BASIS_MUST_BE_STR_OR_NONE')
    return {'security_id': sid, 'cik': cik, 'cik_reason': cik_reason,
            'listed': _tristate(record.get('listed'), 'listed'),
            'security_type': security_type,
            'shares_outstanding': _decimal(record.get('shares_outstanding'), 'shares_outstanding'),
            'shares_filed': _date(record.get('shares_filed'), 'shares_filed'),
            'shares_period_end': _date(record.get('shares_period_end'), 'shares_period_end'),
            'share_price_basis': basis,
            'price': _decimal(record.get('price'), 'price'), 'price_label': label,
            'adr_ratio': _adr_ratio(record.get('adr_ratio')) if security_type == settings.ADR_SECURITY_TYPE else None,
            'representative': _tristate(record.get('representative'), 'representative'),
            'median_dollar_volume': _decimal(record.get('median_dollar_volume'), 'median_dollar_volume'),
            'same_economic_rights': _tristate(record.get('same_economic_rights'), 'same_economic_rights')}


def _index(records):
    out = {}
    for raw in records:
        rec = normalize_record(raw)
        sid = rec['security_id']
        if sid in out and out[sid] != rec:
            raise ValueError('CONFLICTING_SECURITY_RECORDS')
        out[sid] = rec
    return out


def _is_eligible_type(rec):
    return rec['security_type'] in settings.ELIGIBLE_SECURITY_TYPES


def _is_excluded_type(rec):
    return rec['security_type'] in settings.EXCLUDED_SECURITY_TYPES


def _type_unknown_reason(rec):
    """SECURITY_TYPE_UNKNOWN / SECURITY_TYPE_NOT_CANONICAL, or None for a canonical type name."""
    if rec['security_type'] is None:
        return SECURITY_TYPE_UNKNOWN
    if not _is_eligible_type(rec) and not _is_excluded_type(rec):
        return SECURITY_TYPE_NOT_CANONICAL
    return None


def security_status(rec):
    """(status, reasons) of one normalized record as a candidate security. A rule exclusion is definitive even when
    other inputs are missing; otherwise any missing input gives UNKNOWN."""
    excluded, unknown = [], []
    if rec['listed'] is False:
        excluded.append(NOT_LISTED)
    if _is_excluded_type(rec):
        excluded.append(NOT_ELIGIBLE_SECURITY_TYPE)
    if rec['cik'] is None:
        unknown.append(rec['cik_reason'])
    type_reason = _type_unknown_reason(rec)
    if type_reason:
        unknown.append(type_reason)
    if rec['listed'] is None:
        unknown.append(LISTING_STATUS_UNKNOWN)
    if excluded:
        return EXCLUDED, excluded + unknown
    if unknown:
        return UNKNOWN, unknown
    return ELIGIBLE, []


def choose_representative(listed_eligible, flagged_elsewhere=False):
    """(security_id, source, flags) among one issuer's listed eligible-type records.

    Supplied flag first (exactly one True); one listed eligible class -> that class; else highest median dollar volume when
    every class has a usable (>= 0) median, ties by security_id ascending; else the lowest security_id flagged
    REPRESENTATIVE_UNCONFIRMED. Several True flags -> REPRESENTATIVE_FLAG_CONFLICT and the rule decides."""
    if not listed_eligible:
        raise ValueError('NO_LISTED_ELIGIBLE_CLASS')
    flags = [REPRESENTATIVE_FLAG_NOT_LISTED_ELIGIBLE] if flagged_elsewhere else []
    classes = sorted(listed_eligible, key=lambda r: r['security_id'])
    flagged = [r for r in classes if r['representative'] is True]
    if len(flagged) == 1:
        return flagged[0]['security_id'], REP_SUPPLIED_FLAG, flags
    if len(flagged) > 1:
        flags.append(REPRESENTATIVE_FLAG_CONFLICT)
    if len(classes) == 1:
        return classes[0]['security_id'], REP_ONLY_CLASS, flags
    medians = {r['security_id']: r['median_dollar_volume'] for r in classes
               if r['median_dollar_volume'] is not None and r['median_dollar_volume'] >= 0}
    if len(medians) == len(classes):
        best = min(classes, key=lambda r: (-medians[r['security_id']], r['security_id']))
        return best['security_id'], REP_MEDIAN_DOLLAR_VOLUME, flags
    return classes[0]['security_id'], REP_LOWEST_ID, flags + [REPRESENTATIVE_UNCONFIRMED]


def _positive(value, missing, invalid):
    if value is None:
        return missing
    if value <= 0:
        return invalid
    return None


def share_provenance(rec, signal_day):
    """({'security_id', 'shares_filed', 'shares_period_end', 'shares_usable_from', 'usable_at_s', 'share_price_basis'},
    [reasons]) of one record's share count at S (review F2): filing date usable at S, period end, split-basis status."""
    filed, period_end = rec['shares_filed'], rec['shares_period_end']
    reasons, usable_from = [], None
    if filed is None:
        reasons.append(SHARES_FILED_MISSING)
    else:
        try:
            usable_from = schedule.usable_from(filed)
        except pit_filings.CalendarNotConfigured:
            reasons.append(SHARES_FILED_OUTSIDE_CALENDAR)
        else:
            if usable_from > signal_day:
                reasons.append(SHARES_NOT_USABLE_AT_S)
    if period_end is None:
        reasons.append(SHARES_PERIOD_END_MISSING)
    elif filed is not None and period_end > filed:
        reasons.append(SHARES_PERIOD_END_AFTER_FILED)
    if rec['share_price_basis'] != SHARE_PRICE_BASIS_CONFIRMED:
        reasons.append(SHARE_PRICE_BASIS_UNCONFIRMED)
    record = {'security_id': rec['security_id'], 'shares_filed': filed, 'shares_period_end': period_end,
              'shares_usable_from': usable_from, 'usable_at_s': usable_from is not None and usable_from <= signal_day,
              'share_price_basis': rec['share_price_basis']}
    return record, reasons


def issuer_market_cap(issuer_records, representative_id, signal_day):
    """(cap | None, reasons, classes, provenance) for one issuer's normalized records at S; classes = valued
    eligible-type classes [{'security_id', 'security_type', 'shares_outstanding', 'adr_ratio', 'share_basis', 'price',
    'price_basis', 'price_label', 'value'}]; share_basis is CLASS_SHARES, or ORDINARY_SHARES_DIV_ADR_RATIO for an ADR;
    provenance = share_provenance of every eligible-type class with a known listing status."""
    by_id = {r['security_id']: r for r in issuer_records}
    rep = by_id.get(representative_id)
    reasons, classes, provenance = [], [], []
    eligible_type = [r for r in issuer_records if _is_eligible_type(r)]
    if any(r['security_type'] == settings.ADR_SECURITY_TYPE for r in eligible_type) and len(eligible_type) > 1:
        reasons.append(ADR_CLASS_OVERLAP_UNCONFIRMED)
    for rec in sorted(issuer_records, key=lambda r: r['security_id']):
        type_reason = _type_unknown_reason(rec)
        if type_reason:
            reasons.append(type_reason)
            continue
        if not _is_eligible_type(rec):
            continue
        if rec['listed'] is None:
            reasons.append(LISTING_STATUS_UNKNOWN)
            continue
        problem = _positive(rec['shares_outstanding'], SHARES_OUTSTANDING_MISSING, SHARES_OUTSTANDING_INVALID)
        if problem:
            reasons.append(problem)
        origin, share_reasons = share_provenance(rec, signal_day)
        provenance.append(origin)
        if share_reasons:
            reasons.extend(share_reasons)
            problem = problem or share_reasons[0]
        is_adr = rec['security_type'] == settings.ADR_SECURITY_TYPE
        if is_adr and rec['adr_ratio'] is None:
            reasons.append(ADR_RATIO_UNCONFIRMED)
            problem = problem or ADR_RATIO_UNCONFIRMED
        if rec['listed'] is True:
            price, basis, label = rec['price'], 'OWN_PRICE', rec['price_label']
        elif rec['same_economic_rights'] is True:
            price, basis = (rep['price'], 'REPRESENTATIVE_PRICE') if rep is not None else (None, 'REPRESENTATIVE_PRICE')
            label = rep['price_label'] if rep is not None else None
        else:
            reasons.append(UNLISTED_CLASS_RIGHTS_DIFFER if rec['same_economic_rights'] is False
                           else UNLISTED_CLASS_RIGHTS_UNKNOWN)
            continue
        price_problem = _positive(price, PRICE_MISSING, PRICE_INVALID)
        if price_problem:
            reasons.append(price_problem)
        if problem or price_problem:
            continue
        classes.append({'security_id': rec['security_id'], 'security_type': rec['security_type'],
                        'shares_outstanding': rec['shares_outstanding'], 'adr_ratio': rec['adr_ratio'],
                        'share_basis': 'ORDINARY_SHARES_DIV_ADR_RATIO' if is_adr else 'CLASS_SHARES',
                        'price': price, 'price_basis': basis, 'price_label': label, 'value': None})
    reasons = list(dict.fromkeys(reasons))
    if reasons:
        return None, reasons, classes, provenance
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        total = Decimal(0)
        for c in classes:
            shares = c['shares_outstanding'] / c['adr_ratio'] if c['adr_ratio'] is not None else c['shares_outstanding']
            c['value'] = shares * c['price']
            total += c['value']
    return total, [], classes, provenance


def u_a_decision(cap, cik, previous_u_a, previous_unknown=False):
    """(status, reasons, basis): first build entry; later S stay for previous members, entry for the rest; an issuer
    whose previous status was UNKNOWN is UNKNOWN between the stay and entry thresholds (review F3)."""
    if cap is None:
        return UNKNOWN, [MARKET_CAP_NOT_AVAILABLE], None
    if previous_u_a is not None and cik in previous_u_a:
        return (ELIGIBLE, [], 'STAY') if cap >= settings.U_A_STAY_USD else (EXCLUDED, [BELOW_U_A_STAY], 'STAY')
    if previous_unknown:
        if cap >= settings.U_A_ENTRY_USD:
            return ELIGIBLE, [], 'ENTRY'
        if cap < settings.U_A_STAY_USD:
            return EXCLUDED, [BELOW_U_A_STAY], 'PREVIOUS_STATUS_UNKNOWN'
        return UNKNOWN, [PREVIOUS_U_A_STATUS_UNKNOWN], 'PREVIOUS_STATUS_UNKNOWN'
    basis = 'FIRST_BUILD_ENTRY' if previous_u_a is None else 'ENTRY'
    return (ELIGIBLE, [], basis) if cap >= settings.U_A_ENTRY_USD else (EXCLUDED, [BELOW_U_A_ENTRY], basis)


def u_b_decision(cap):
    if cap is None:
        return UNKNOWN, [MARKET_CAP_NOT_AVAILABLE]
    return (ELIGIBLE, []) if cap >= settings.U_B_MIN_USD else (EXCLUDED, [BELOW_U_B])


def _counts(units, group):
    counts = Counter()
    by_reason = {EXCLUDED: Counter(), UNKNOWN: Counter()}
    for unit in units.values():
        status, reasons = unit[group]['status'], unit[group]['reasons']
        counts[status] += 1
        if status in by_reason:
            by_reason[status][reasons[0]] += 1
    return {'candidate': len(units), 'eligible': counts[ELIGIBLE], 'excluded': counts[EXCLUDED],
            'unknown': counts[UNKNOWN], 'excluded_by_reason': dict(sorted(by_reason[EXCLUDED].items())),
            'unknown_by_reason': dict(sorted(by_reason[UNKNOWN].items()))}


def _unit_id(value):
    """A carried unit ID: a zero-padded CIK, or 'SECURITY:<security id>'."""
    if isinstance(value, str) and value.startswith(SECURITY_UNIT_PREFIX) and value[len(SECURITY_UNIT_PREFIX):].strip():
        return value
    cik = _cik(value)[0]
    if cik is None:
        raise ValueError('PREVIOUS_U_A_UNKNOWN_INVALID')
    return cik


def _termination_unit(value):
    """The unit a termination names: an issuer CIK, or 'SECURITY:<id>' (a carried CIK-less unit; review M2)."""
    if isinstance(value, str) and value.startswith(SECURITY_UNIT_PREFIX):
        return value if value[len(SECURITY_UNIT_PREFIX):].strip() else None
    return _cik(value)[0]


def _terminations(terminations, signal_day):
    """({unit: evidenced record}, {unit: UNKNOWN reason}, every supplied record).

    Evidenced: the filing is usable at S and effective_date is supplied and <= S (review U2). A usable filing without an
    effective date or with one after S is not a termination at S; the unit gets that reason instead."""
    usable, pending, listed = {}, {}, []
    for item in terminations or ():
        if not isinstance(item, dict) or not {'cik', 'evidence', 'filed'} <= set(item) or \
                set(item) - {'cik', 'evidence', 'filed', 'effective_date'}:
            raise ValueError('TERMINATION_RECORD_INVALID')
        unit = _termination_unit(item['cik'])
        if unit is None or not isinstance(item['evidence'], str) or not item['evidence'].strip():
            raise ValueError('TERMINATION_RECORD_INVALID')
        filed = _date(item['filed'], 'termination_filed')
        effective = _date(item.get('effective_date'), 'termination_effective_date')
        try:
            usable_from = schedule.usable_from(filed)
        except pit_filings.CalendarNotConfigured:
            usable_from = None
        usable_at_s = usable_from is not None and usable_from <= signal_day
        effective_at_s = effective is not None and effective <= signal_day
        if not usable_at_s:
            status = 'NOT_USABLE_AT_S'
        elif effective is None:
            status = TERMINATION_EFFECTIVE_DATE_MISSING
        elif not effective_at_s:
            status = TERMINATION_NOT_EFFECTIVE_AT_S
        else:
            status = TERMINATION_EVIDENCED
        record = {'unit': unit, 'cik': None if unit.startswith(SECURITY_UNIT_PREFIX) else unit,
                  'evidence': item['evidence'], 'filed': filed, 'effective_date': effective,
                  'usable_from': usable_from, 'usable_at_s': usable_at_s, 'effective_at_s': effective_at_s,
                  'status': status}
        listed.append(record)
        if status == TERMINATION_EVIDENCED:
            usable.setdefault(unit, record)
        elif status != 'NOT_USABLE_AT_S':
            pending.setdefault(unit, status)
    for unit in usable:
        pending.pop(unit, None)
    return usable, pending, listed


def _class_ids(value):
    """{unit ID: frozenset of security IDs} of a previous_u_a_securities mapping (review U1)."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError('PREVIOUS_U_A_SECURITIES_INVALID')
    out = {}
    for unit, ids in value.items():
        unit = _unit_id(unit)
        if isinstance(ids, str) or not all(isinstance(i, str) and i.strip() for i in ids) or unit in out:
            raise ValueError('PREVIOUS_U_A_SECURITIES_INVALID')
        out[unit] = frozenset(ids)
    return out


def _carried_unit(unit_id, cik, carried_from, reasons=(NOT_IN_RECORDS_AT_S,), securities=()):
    unknown = {'status': UNKNOWN, 'reasons': list(reasons)}
    return {'issuer_id': unit_id, 'cik': cik, 'securities': list(securities), 'listed_eligible': [],
            'representative': None, 'representative_source': None, 'representative_flags': [], 'price_label': None,
            'market_cap_usd': None, 'market_cap_reasons': list(reasons), 'classes': [], 'share_provenance': [],
            'carried_from': carried_from, settings.U_A: dict(unknown, basis=None), settings.U_B: dict(unknown)}


def _tracked_ids(records):
    """Security IDs of the eligible or possibly eligible records (definitively excluded types left out)."""
    return {r['security_id'] for r in records if not _is_excluded_type(r)}


def build_universes(records, *, signal_day=None, previous_u_a=None, previous_u_a_unknown=None, terminations=None,
                    previous_u_a_securities=None):
    """U-A and U-B at one S. previous_u_a: CIKs of the U-A members at the previous S (None = first build);
    previous_u_a_unknown: the previous S's U-A UNKNOWN unit IDs (CIKs or 'SECURITY:<id>'); previous_u_a_securities: the
    previous S's U_A.unit_securities (class IDs carried, review U1); terminations: evidenced terminations (module doc).
    signal_day (a session) is required: the share counts' filing dates are checked against it.

    Returns {'schema', 'signal_day', 'first_build', 'previous', 'thresholds', 'securities', 'issuers', 'security_counts',
    'terminations', 'U_A': {'members', 'member_securities', 'representatives', 'unknown', 'unit_securities',
    'terminated', 'counts', 'transitions'}, 'U_B': {... no unknown / unit_securities / terminated / transitions}}.
    members are sorted CIKs; member_securities the members' representative security IDs (the scoring keys); U_A.unknown
    the U-A UNKNOWN unit IDs and U_A.unit_securities the class IDs of every member and UNKNOWN unit (for the next S)."""
    if signal_day is None:
        raise ValueError('SIGNAL_DAY_REQUIRED')
    signal = schedule._signal(signal_day)
    if previous_u_a is not None:
        previous_u_a = frozenset(_cik(c)[0] for c in previous_u_a)
        if None in previous_u_a:
            raise ValueError('PREVIOUS_U_A_CIK_INVALID')
    elif previous_u_a_unknown:
        raise ValueError('PREVIOUS_U_A_UNKNOWN_WITHOUT_MEMBERS')
    previous_unknown = frozenset(_unit_id(u) for u in previous_u_a_unknown or ())
    previous_classes = _class_ids(previous_u_a_securities)
    if previous_classes is not None and previous_u_a is None and previous_classes:
        raise ValueError('PREVIOUS_U_A_SECURITIES_WITHOUT_MEMBERS')
    previous_classes = previous_classes or {}
    class_owner = {}
    for unit in sorted(previous_classes):
        if unit.startswith(SECURITY_UNIT_PREFIX):
            continue
        for class_id in previous_classes[unit]:
            if class_owner.setdefault(class_id, unit) != unit:
                raise ValueError('PREVIOUS_U_A_SECURITIES_INVALID')
    evidenced, not_terminated, termination_records = _terminations(terminations, signal)
    index = _index(records)
    securities = {}
    by_cik = defaultdict(list)
    attached = defaultdict(list)       # carried issuer -> its CIK-less class records at S (review U1 / M1)
    units = {}
    for sid in sorted(index):
        rec = index[sid]
        status, reasons = security_status(rec)
        securities[sid] = {'security_id': sid, 'cik': rec['cik'], 'security_type': rec['security_type'],
                           'status': status, 'reasons': reasons, 'price_label': rec['price_label']}
        if rec['cik'] is not None:
            by_cik[rec['cik']].append(rec)
        elif sid in class_owner:
            attached[class_owner[sid]].append(rec)
        elif status == UNKNOWN:
            unknown = {'status': UNKNOWN, 'reasons': list(reasons)}
            units[SECURITY_UNIT_PREFIX + sid] = {
                'issuer_id': SECURITY_UNIT_PREFIX + sid, 'cik': None, 'securities': [sid], 'listed_eligible': [],
                'representative': None, 'representative_source': None, 'representative_flags': [], 'price_label': None,
                'market_cap_usd': None, 'market_cap_reasons': list(reasons), 'classes': [], 'share_provenance': [],
                settings.U_A: dict(unknown, basis=None), settings.U_B: dict(unknown)}
    for cik in sorted(by_cik):
        recs = by_cik[cik]
        listed_eligible = [r for r in recs if securities[r['security_id']]['status'] == ELIGIBLE]
        unit = {'issuer_id': cik, 'cik': cik, 'securities': [r['security_id'] for r in recs],
                'listed_eligible': [r['security_id'] for r in listed_eligible], 'representative': None,
                'representative_source': None, 'representative_flags': [], 'price_label': None, 'market_cap_usd': None,
                'market_cap_reasons': [], 'classes': [], 'share_provenance': []}
        if not listed_eligible:
            possible = [r for r in recs if securities[r['security_id']]['status'] == UNKNOWN]
            if possible:
                reasons = list(dict.fromkeys(x for r in possible for x in securities[r['security_id']]['reasons']))
                status = UNKNOWN
            else:
                reasons, status = [NO_LISTED_ELIGIBLE_SECURITY], EXCLUDED
            unit['market_cap_reasons'] = list(reasons)
            unit[settings.U_A] = {'status': status, 'reasons': list(reasons), 'basis': None}
            unit[settings.U_B] = {'status': status, 'reasons': list(reasons)}
            units[cik] = unit
            continue
        flagged_elsewhere = any(r['representative'] is True and r not in listed_eligible for r in recs)
        rep, source, flags = choose_representative(listed_eligible, flagged_elsewhere)
        cap, cap_reasons, classes, provenance = issuer_market_cap(recs, rep, signal)
        unit.update(representative=rep, representative_source=source, representative_flags=flags,
                    price_label=index[rep]['price_label'], market_cap_usd=cap, market_cap_reasons=cap_reasons,
                    classes=classes, share_provenance=provenance)
        was_unknown = cik in previous_unknown or any(SECURITY_UNIT_PREFIX + r['security_id'] in previous_unknown
                                                     for r in recs)
        a_status, a_reasons, a_basis = u_a_decision(cap, cik, previous_u_a, was_unknown)
        b_status, b_reasons = u_b_decision(cap)
        if cap is None:
            a_reasons = b_reasons = list(cap_reasons)
        unit[settings.U_A] = {'status': a_status, 'reasons': list(a_reasons), 'basis': a_basis}
        unit[settings.U_B] = {'status': b_status, 'reasons': list(b_reasons)}
        units[cik] = unit
    # Carried class IDs (review U1 / M1): a previous issuer whose class is CIK-less at S, missing, or under another CIK
    # cannot be summed; it is UNKNOWN in both groups and keeps the unresolved class IDs.
    unresolved = {}
    for unit_id in sorted(previous_classes):
        if unit_id.startswith(SECURITY_UNIT_PREFIX):
            continue
        present = {r['security_id'] for r in list(by_cik.get(unit_id, ())) + list(attached.get(unit_id, ()))}
        missing = previous_classes[unit_id] - present
        reasons = ([CIK_UNKNOWN] if attached.get(unit_id) else []) + ([CLASS_RECORD_NOT_ATTACHED_AT_S] if missing else [])
        if not reasons or (unit_id not in by_cik and not attached.get(unit_id)):
            continue        # no record at all: the carried-unit rule below decides
        unresolved[unit_id] = missing
        if unit_id in by_cik:
            unit = units[unit_id]
            unit['securities'] = sorted(unit['securities'] + [r['security_id'] for r in attached.get(unit_id, [])])
            reasons = reasons + [r for r in unit['market_cap_reasons'] if r not in reasons]
            unit.update(market_cap_usd=None, market_cap_reasons=list(reasons), classes=[])
            unit[settings.U_A] = {'status': UNKNOWN, 'reasons': list(reasons), 'basis': None}
            unit[settings.U_B] = {'status': UNKNOWN, 'reasons': list(reasons)}
        else:
            origin = 'PREVIOUS_U_A_MEMBER' if unit_id in (previous_u_a or ()) else 'PREVIOUS_U_A_UNKNOWN'
            units[unit_id] = _carried_unit(unit_id, unit_id, origin, reasons,
                                           sorted(r['security_id'] for r in attached[unit_id]))
    # Previous members and previous UNKNOWN units without any record at S stay UNKNOWN candidates (review F3) unless
    # an evidenced termination (filing usable at S, effective at S; review U2) is supplied.
    terminated = []
    carried = [(c, 'PREVIOUS_U_A_MEMBER') for c in sorted(previous_u_a or ())]
    carried += [(u, 'PREVIOUS_U_A_UNKNOWN') for u in sorted(previous_unknown) if u not in (previous_u_a or ())]
    for unit_id, origin in carried:
        if unit_id in units:
            continue        # it has records (or attached CIK-less class records) at S
        is_security = unit_id.startswith(SECURITY_UNIT_PREFIX)
        if (is_security and unit_id[len(SECURITY_UNIT_PREFIX):] in index) or (not is_security and unit_id in by_cik):
            continue
        if unit_id in evidenced:
            terminated.append(dict(evidenced[unit_id], previous_status=origin, reasons=[TERMINATION_EVIDENCED]))
            continue
        reasons = ([not_terminated[unit_id]] if unit_id in not_terminated else []) + [NOT_IN_RECORDS_AT_S]
        units[unit_id] = _carried_unit(unit_id, None if is_security else unit_id, origin, reasons)
    out = {'schema': SCHEMA, 'signal_day': signal_day if isinstance(signal_day, str) else signal.isoformat(),
           'first_build': previous_u_a is None,
           'previous': None if previous_u_a is None else {
               'members': tuple(sorted(previous_u_a)), 'unknown': tuple(sorted(previous_unknown)),
               'securities': None if previous_u_a_securities is None else
               {unit: tuple(sorted(ids)) for unit, ids in sorted(previous_classes.items())}},
           'thresholds': {'u_a_entry_usd': settings.U_A_ENTRY_USD, 'u_a_stay_usd': settings.U_A_STAY_USD,
                          'u_b_min_usd': settings.U_B_MIN_USD},
           'securities': securities, 'issuers': units, 'terminations': termination_records}
    sec_counts = Counter(s['status'] for s in securities.values())
    sec_reasons = {EXCLUDED: Counter(), UNKNOWN: Counter()}
    for s in securities.values():
        if s['status'] in sec_reasons:
            sec_reasons[s['status']][s['reasons'][0]] += 1
    out['security_counts'] = {'candidate': len(securities), 'listed_eligible': sec_counts[ELIGIBLE],
                              'excluded': sec_counts[EXCLUDED], 'unknown': sec_counts[UNKNOWN],
                              'excluded_by_reason': dict(sorted(sec_reasons[EXCLUDED].items())),
                              'unknown_by_reason': dict(sorted(sec_reasons[UNKNOWN].items()))}
    for group in settings.GROUPS:
        members = tuple(sorted(u['cik'] for u in units.values() if u[group]['status'] == ELIGIBLE))
        reps = {cik: units[cik]['representative'] for cik in members}
        out[group] = {'members': members, 'member_securities': tuple(sorted(reps.values())), 'representatives': reps,
                      'counts': _counts(units, group)}
    out[settings.U_A]['unknown'] = tuple(sorted(uid for uid, u in units.items()
                                                if u[settings.U_A]['status'] == UNKNOWN))
    carried_ids = {}
    for uid in out[settings.U_A]['members'] + out[settings.U_A]['unknown']:
        unit = units[uid]
        if uid.startswith(SECURITY_UNIT_PREFIX):
            ids = {uid[len(SECURITY_UNIT_PREFIX):]}
        else:
            ids = _tracked_ids(index[sid] for sid in unit['securities']) | unresolved.get(uid, set())
            if not unit['securities']:                      # carried without any record: keep what was carried
                ids |= previous_classes.get(uid, frozenset())
        carried_ids[uid] = tuple(sorted(ids))
    out[settings.U_A]['unit_securities'] = carried_ids
    out[settings.U_A]['terminated'] = tuple(terminated)
    previous = previous_u_a or frozenset()
    current = set(out[settings.U_A]['members'])
    gone = {item['unit']: item['reasons'] for item in terminated}
    left = []
    for cik in sorted(previous - current):
        unit = units.get(cik)
        left.append({'cik': cik, 'reasons': list(gone.get(cik, [NOT_IN_RECORDS_AT_S])) if unit is None
                     else list(unit[settings.U_A]['reasons'])})
    out[settings.U_A]['transitions'] = {'entered': tuple(sorted(current - previous)) if previous_u_a is not None else (),
                                        'stayed': tuple(sorted(current & previous)), 'left': tuple(left)}
    return out
