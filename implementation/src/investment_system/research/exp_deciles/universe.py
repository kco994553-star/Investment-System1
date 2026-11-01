"""U-A / U-B membership at one signal day S from caller-supplied security records. Pure; no data is fetched.

Ported from research/qgv_backtest @ 56a0e8ce (#417/#430) and changed for EXP-STOCK-INDICATOR-DECILES-v1:
pit_adapter.choose_share_classes (L251: one security per CIK, highest median dollar volume, ties by permanent ID, else the
lowest ID flagged SHARE_CLASS_LIQUIDITY_UNCONFIRMED). Changed: a supplied representative flag is used first; the median
dollar volume is a supplied input (no 60-session price window is read here); the fallback flag is REPRESENTATIVE_UNCONFIRMED;
the issuer nominal market cap (class sum), the U-A entry/stay hysteresis, the U-B threshold and the candidate / eligible /
excluded / unknown counts are new.

Record (one per security at S; dict keys):
  security_id           fixed security ID (required, non-empty str)
  cik                   issuer CIK (digits, any padding) or None = unknown
  listed                True / False / None = unknown (listed on S)
  security_type         'COMMON' / 'COMMON_CLASS' = common stock (settings.COMMON_SECURITY_TYPES); any other str = not
                        common; None = unknown
  shares_outstanding    class shares outstanding at S: Decimal / int / decimal str, or None (float refused)
  price                 price at S: Decimal / int / decimal str, or None; price_label names it (e.g. a labelled proxy)
  representative        supplied representative flag True / False / None
  median_dollar_volume  input of the representative rule (Decimal / int / str, or None)
  same_economic_rights  for an unlisted common class: True values it at the representative's price; False / None -> NA

Issuer nominal market cap (Decimal, precision 50) = sum over the issuer's common classes of shares x price, where a listed
class uses its own price and an unlisted class uses the representative's price only when same_economic_rights is True.
Any missing or unusable input of any (possibly) common class makes the cap NA with reasons; it is never partially summed.

Membership: U-A first build (previous_u_a is None): cap >= entry. Later S: a previous U-A member stays iff cap >= stay;
any other issuer enters iff cap >= entry. U-B: cap >= 10bn at that S, no hysteresis. NA cap -> UNKNOWN, never EXCLUDED,
and an UNKNOWN issuer is not a member at S (so at the next S it is judged against the entry threshold).

Counting unit = issuer: each known CIK, plus each security without a CIK that could be a listed common stock (it cannot be
attached to an issuer, so it is its own unknown unit). candidate = eligible + excluded + unknown for every group; each unit
is counted once under its first reason (`*_by_reason`), its full reason list stays on the unit.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, localcontext

from . import settings

SCHEMA = 'exp-deciles-universe/1'
ELIGIBLE, EXCLUDED, UNKNOWN = 'ELIGIBLE', 'EXCLUDED', 'UNKNOWN'
DECIMAL_PRECISION = 50

# reason codes (UPPER_SNAKE): exclusions by rule
NOT_LISTED = 'NOT_LISTED'
NOT_COMMON_STOCK = 'NOT_COMMON_STOCK'
NO_LISTED_COMMON_STOCK = 'NO_LISTED_COMMON_STOCK'
BELOW_U_A_ENTRY = 'BELOW_U_A_ENTRY_THRESHOLD'
BELOW_U_A_STAY = 'BELOW_U_A_STAY_THRESHOLD'
BELOW_U_B = 'BELOW_U_B_THRESHOLD'
# reason codes: unknown (missing or unusable input)
CIK_UNKNOWN = 'CIK_UNKNOWN'
CIK_INVALID = 'CIK_INVALID'
LISTING_STATUS_UNKNOWN = 'LISTING_STATUS_UNKNOWN'
SECURITY_TYPE_UNKNOWN = 'SECURITY_TYPE_UNKNOWN'
SHARES_OUTSTANDING_MISSING = 'SHARES_OUTSTANDING_MISSING'
SHARES_OUTSTANDING_INVALID = 'SHARES_OUTSTANDING_INVALID'
PRICE_MISSING = 'PRICE_MISSING'
PRICE_INVALID = 'PRICE_INVALID'
UNLISTED_CLASS_RIGHTS_UNKNOWN = 'UNLISTED_CLASS_RIGHTS_UNKNOWN'
UNLISTED_CLASS_RIGHTS_DIFFER = 'UNLISTED_CLASS_RIGHTS_DIFFER'
MARKET_CAP_NOT_AVAILABLE = 'MARKET_CAP_NOT_AVAILABLE'
# transition reason for a previous member without any record at S
NOT_IN_RECORDS_AT_S = 'NOT_IN_RECORDS_AT_S'
# representative sources and flags
REP_SUPPLIED_FLAG = 'SUPPLIED_FLAG'
REP_ONLY_CLASS = 'ONLY_LISTED_COMMON_CLASS'
REP_MEDIAN_DOLLAR_VOLUME = 'HIGHEST_MEDIAN_DOLLAR_VOLUME'
REP_LOWEST_ID = 'LOWEST_SECURITY_ID'
REPRESENTATIVE_UNCONFIRMED = 'REPRESENTATIVE_UNCONFIRMED'
REPRESENTATIVE_FLAG_CONFLICT = 'REPRESENTATIVE_FLAG_CONFLICT'
REPRESENTATIVE_FLAG_NOT_LISTED_COMMON = 'REPRESENTATIVE_FLAG_NOT_LISTED_COMMON'


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
    return {'security_id': sid, 'cik': cik, 'cik_reason': cik_reason,
            'listed': _tristate(record.get('listed'), 'listed'),
            'security_type': security_type,
            'shares_outstanding': _decimal(record.get('shares_outstanding'), 'shares_outstanding'),
            'price': _decimal(record.get('price'), 'price'), 'price_label': label,
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


def _is_common(rec):
    return rec['security_type'] in settings.COMMON_SECURITY_TYPES


def security_status(rec):
    """(status, reasons) of one normalized record as a candidate security. A rule exclusion is definitive even when
    other inputs are missing; otherwise any missing input gives UNKNOWN."""
    excluded, unknown = [], []
    if rec['listed'] is False:
        excluded.append(NOT_LISTED)
    if rec['security_type'] is not None and not _is_common(rec):
        excluded.append(NOT_COMMON_STOCK)
    if rec['cik'] is None:
        unknown.append(rec['cik_reason'])
    if rec['security_type'] is None:
        unknown.append(SECURITY_TYPE_UNKNOWN)
    if rec['listed'] is None:
        unknown.append(LISTING_STATUS_UNKNOWN)
    if excluded:
        return EXCLUDED, excluded + unknown
    if unknown:
        return UNKNOWN, unknown
    return ELIGIBLE, []


def choose_representative(listed_common, flagged_elsewhere=False):
    """(security_id, source, flags) among one issuer's listed common records.

    Supplied flag first (exactly one True); one listed common class -> that class; else highest median dollar volume when
    every class has a usable (>= 0) median, ties by security_id ascending; else the lowest security_id flagged
    REPRESENTATIVE_UNCONFIRMED. Several True flags -> REPRESENTATIVE_FLAG_CONFLICT and the rule decides."""
    if not listed_common:
        raise ValueError('NO_LISTED_COMMON_CLASS')
    flags = [REPRESENTATIVE_FLAG_NOT_LISTED_COMMON] if flagged_elsewhere else []
    classes = sorted(listed_common, key=lambda r: r['security_id'])
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


def issuer_market_cap(issuer_records, representative_id):
    """(cap | None, reasons, classes) for one issuer's normalized records; classes = valued common classes
    [{'security_id', 'shares_outstanding', 'price', 'price_basis', 'price_label', 'value'}]."""
    by_id = {r['security_id']: r for r in issuer_records}
    rep = by_id.get(representative_id)
    reasons, classes = [], []
    for rec in sorted(issuer_records, key=lambda r: r['security_id']):
        if rec['security_type'] is None:
            reasons.append(SECURITY_TYPE_UNKNOWN)
            continue
        if not _is_common(rec):
            continue
        if rec['listed'] is None:
            reasons.append(LISTING_STATUS_UNKNOWN)
            continue
        problem = _positive(rec['shares_outstanding'], SHARES_OUTSTANDING_MISSING, SHARES_OUTSTANDING_INVALID)
        if problem:
            reasons.append(problem)
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
        classes.append({'security_id': rec['security_id'], 'shares_outstanding': rec['shares_outstanding'],
                        'price': price, 'price_basis': basis, 'price_label': label, 'value': None})
    reasons = list(dict.fromkeys(reasons))
    if reasons:
        return None, reasons, classes
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        total = Decimal(0)
        for c in classes:
            c['value'] = c['shares_outstanding'] * c['price']
            total += c['value']
    return total, [], classes


def u_a_decision(cap, cik, previous_u_a):
    """(status, reasons, basis): first build entry; later S stay for previous members, entry for the rest."""
    if cap is None:
        return UNKNOWN, [MARKET_CAP_NOT_AVAILABLE], None
    if previous_u_a is not None and cik in previous_u_a:
        return (ELIGIBLE, [], 'STAY') if cap >= settings.U_A_STAY_USD else (EXCLUDED, [BELOW_U_A_STAY], 'STAY')
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


def build_universes(records, *, previous_u_a=None, signal_day=None):
    """U-A and U-B at one S. previous_u_a: CIKs of the U-A members at the previous S (None = first build).

    Returns {'schema', 'signal_day', 'first_build', 'thresholds', 'securities', 'issuers', 'security_counts',
    'U_A': {'members', 'member_securities', 'representatives', 'counts', 'transitions'}, 'U_B': {... no transitions}}.
    members are sorted CIKs; member_securities the members' representative security IDs (the scoring keys)."""
    if previous_u_a is not None:
        previous_u_a = frozenset(_cik(c)[0] for c in previous_u_a)
        if None in previous_u_a:
            raise ValueError('PREVIOUS_U_A_CIK_INVALID')
    index = _index(records)
    securities = {}
    by_cik = defaultdict(list)
    units = {}
    for sid in sorted(index):
        rec = index[sid]
        status, reasons = security_status(rec)
        securities[sid] = {'security_id': sid, 'cik': rec['cik'], 'status': status, 'reasons': reasons,
                           'price_label': rec['price_label']}
        if rec['cik'] is not None:
            by_cik[rec['cik']].append(rec)
        elif status == UNKNOWN:
            unknown = {'status': UNKNOWN, 'reasons': list(reasons)}
            units['SECURITY:' + sid] = {'issuer_id': 'SECURITY:' + sid, 'cik': None, 'securities': [sid],
                                        'listed_common': [], 'representative': None, 'representative_source': None,
                                        'representative_flags': [], 'price_label': None, 'market_cap_usd': None,
                                        'market_cap_reasons': list(reasons), 'classes': [],
                                        settings.U_A: dict(unknown, basis=None), settings.U_B: dict(unknown)}
    for cik in sorted(by_cik):
        recs = by_cik[cik]
        listed_common = [r for r in recs if securities[r['security_id']]['status'] == ELIGIBLE]
        unit = {'issuer_id': cik, 'cik': cik, 'securities': [r['security_id'] for r in recs],
                'listed_common': [r['security_id'] for r in listed_common], 'representative': None,
                'representative_source': None, 'representative_flags': [], 'price_label': None, 'market_cap_usd': None,
                'market_cap_reasons': [], 'classes': []}
        if not listed_common:
            possible = [r for r in recs if securities[r['security_id']]['status'] == UNKNOWN]
            if possible:
                reasons = list(dict.fromkeys(x for r in possible for x in securities[r['security_id']]['reasons']))
                status = UNKNOWN
            else:
                reasons, status = [NO_LISTED_COMMON_STOCK], EXCLUDED
            unit['market_cap_reasons'] = list(reasons)
            unit[settings.U_A] = {'status': status, 'reasons': list(reasons), 'basis': None}
            unit[settings.U_B] = {'status': status, 'reasons': list(reasons)}
            units[cik] = unit
            continue
        flagged_elsewhere = any(r['representative'] is True and r not in listed_common for r in recs)
        rep, source, flags = choose_representative(listed_common, flagged_elsewhere)
        cap, cap_reasons, classes = issuer_market_cap(recs, rep)
        unit.update(representative=rep, representative_source=source, representative_flags=flags,
                    price_label=index[rep]['price_label'], market_cap_usd=cap, market_cap_reasons=cap_reasons,
                    classes=classes)
        a_status, a_reasons, a_basis = u_a_decision(cap, cik, previous_u_a)
        b_status, b_reasons = u_b_decision(cap)
        if cap is None:
            a_reasons = b_reasons = list(cap_reasons)
        unit[settings.U_A] = {'status': a_status, 'reasons': list(a_reasons), 'basis': a_basis}
        unit[settings.U_B] = {'status': b_status, 'reasons': list(b_reasons)}
        units[cik] = unit
    out = {'schema': SCHEMA, 'signal_day': signal_day, 'first_build': previous_u_a is None,
           'thresholds': {'u_a_entry_usd': settings.U_A_ENTRY_USD, 'u_a_stay_usd': settings.U_A_STAY_USD,
                          'u_b_min_usd': settings.U_B_MIN_USD},
           'securities': securities, 'issuers': units}
    sec_counts = Counter(s['status'] for s in securities.values())
    sec_reasons = {EXCLUDED: Counter(), UNKNOWN: Counter()}
    for s in securities.values():
        if s['status'] in sec_reasons:
            sec_reasons[s['status']][s['reasons'][0]] += 1
    out['security_counts'] = {'candidate': len(securities), 'listed_common': sec_counts[ELIGIBLE],
                              'excluded': sec_counts[EXCLUDED], 'unknown': sec_counts[UNKNOWN],
                              'excluded_by_reason': dict(sorted(sec_reasons[EXCLUDED].items())),
                              'unknown_by_reason': dict(sorted(sec_reasons[UNKNOWN].items()))}
    for group in settings.GROUPS:
        members = tuple(sorted(u['cik'] for u in units.values() if u[group]['status'] == ELIGIBLE))
        reps = {cik: units[cik]['representative'] for cik in members}
        out[group] = {'members': members, 'member_securities': tuple(sorted(reps.values())), 'representatives': reps,
                      'counts': _counts(units, group)}
    previous = previous_u_a or frozenset()
    current = set(out[settings.U_A]['members'])
    left = []
    for cik in sorted(previous - current):
        unit = units.get(cik)
        left.append({'cik': cik, 'reasons': [NOT_IN_RECORDS_AT_S] if unit is None else list(unit[settings.U_A]['reasons'])})
    out[settings.U_A]['transitions'] = {'entered': tuple(sorted(current - previous)) if previous_u_a is not None else (),
                                        'stayed': tuple(sorted(current & previous)), 'left': tuple(left)}
    return out
