"""Separate financial V candidate raw metrics. No score, ranking or publication."""
from datetime import date
import hashlib
import json
import math

VERSION = 'financial-v-research/1'
CONFIG = {
    'version': VERSION, 'rule_origin': 'RESEARCHER_PROPOSAL', 'max_age_days': 550,
    'annual_days': [350, 380], 'positive_numerator_required': True,
    'groups': {
        '6021': ['DEPOSITORY_BANK', 'tangible_book_yield'], '6022': ['DEPOSITORY_BANK', 'tangible_book_yield'],
        '6311': ['LIFE_INSURANCE', 'book_yield'],
        '6331': ['PROPERTY_CASUALTY_INSURANCE', 'book_yield'], '6399': ['OTHER_INSURANCE', 'book_yield'],
        '6321': ['HEALTH_ACCIDENT_INSURANCE', 'earnings_yield'], '6324': ['HEALTH_ACCIDENT_INSURANCE', 'earnings_yield'],
        '6211': ['SECURITIES_BROKER_DEALER', 'book_yield'],
        '6282': ['ASSET_MANAGER', 'earnings_yield'], '6411': ['INSURANCE_INTERMEDIARY', 'earnings_yield'],
    },
    'metrics': ['earnings_yield', 'book_yield', 'tangible_book_yield'],
    'score_policy': 'NOT_DEFINED', 'rank_policy': 'NOT_DEFINED',
    'book_common_basis': 'DIRECT_COMMON_EQUITY_OR_PARENT_WITH_EXPLICIT_ZERO_PREFERRED_SHARES',
    'tangible_basis': 'EXPLICIT_ZERO_NCI_AND_COMPLETE_INTANGIBLES',
    'diagnostic_date_policy': 'SAME_FISCAL_END_MONTH',
    'security_basis_policy': 'CONFIRMED_CLASS_OR_EX_POST_ARITHMETIC_ONLY',
}
CONFIG_SHA256 = hashlib.sha256(json.dumps(CONFIG, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _day(value):
    try:
        return date.fromisoformat(value) if isinstance(value, str) and len(value) == 10 else None
    except ValueError:
        return None


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def evaluate(row):
    """Evaluate independently sourced per-share inputs on an explicit date/basis.

    The caller must establish common-equity attribution for book inputs and provide
    audit sources. No preferred/NCI/intangible component is inferred or filled here.
    EX_POST rows allow filings after the price date, but can never be primary-eligible.
    """
    kind = row.get('result_kind')
    if kind not in ('OPERATIONAL_CANDIDATE_RAW', 'EX_POST_FISCAL_DIAGNOSTIC'):
        raise ValueError('RESULT_KIND_REQUIRED')
    valuation, vintage = _day(row.get('valuation_date')), _day(str(row.get('input_vintage', ''))[:10])
    if valuation is None or vintage is None or not row.get('code'):
        raise ValueError('DATE_AND_CODE_REQUIRED')
    group, primary = CONFIG['groups'].get(str(row.get('sic')), ['BUSINESS_MODEL_UNRESOLVED', None])
    diagnostic = kind == 'EX_POST_FISCAL_DIAGNOSTIC'
    security = row.get('security_basis') or {}
    security_confirmed = (security.get('status') == 'SINGLE_CLASS_CONFIRMED' and bool(security.get('source')))
    evidence_status = ('CLASS_BASIS_DOCUMENTED' if security_confirmed
                       else 'ARITHMETIC_ONLY_SECURITY_BASIS_UNCONFIRMED')
    price = row.get('price') or {}
    results = {}
    for metric in CONFIG['metrics']:
        fact = (row.get('inputs') or {}).get(metric) or {}
        reasons = []
        p, numerator = price.get('value'), fact.get('value')
        if not _finite(p) or p <= 0:
            reasons.append('PRICE_UNAVAILABLE')
        if not _finite(numerator):
            reasons.append('INPUT_UNAVAILABLE')
        elif numerator <= 0:
            reasons.append('NONPOSITIVE_NUMERATOR')
        if _day(price.get('date')) != valuation:
            reasons.append('PRICE_DATE_MISMATCH')
        currency = fact.get('currency')
        if (not currency or currency != price.get('currency')
                or fact.get('unit') != currency + '/share' or price.get('unit') != currency + '/share'):
            reasons.append('CURRENCY_OR_UNIT_MISMATCH')
        if not fact.get('share_basis') or fact.get('share_basis') != price.get('share_basis'):
            reasons.append('SHARE_BASIS_UNCONFIRMED')
        if not fact.get('source') or not price.get('source'):
            reasons.append('SOURCE_UNCONFIRMED')
        end, filed = _day(fact.get('period_end')), _day(fact.get('filed'))
        if end is None or not 0 <= (valuation - end).days <= CONFIG['max_age_days']:
            reasons.append('PERIOD_NOT_ELIGIBLE')
        if diagnostic and end is not None and (end.year, end.month) != (valuation.year, valuation.month):
            reasons.append('DIAGNOSTIC_FISCAL_MONTH_MISMATCH')
        if not diagnostic and not security_confirmed:
            reasons.append('SECURITY_CLASS_BASIS_UNCONFIRMED')
        if metric == 'earnings_yield':
            start = _day(fact.get('period_start'))
            if start is None or end is None or not CONFIG['annual_days'][0] <= (end - start).days <= CONFIG['annual_days'][1]:
                reasons.append('ANNUAL_SPAN_REQUIRED')
        if filed is None or filed > vintage or end is not None and filed < end:
            reasons.append('FILING_NOT_ELIGIBLE')
        elif filed > valuation and not diagnostic:
            reasons.append('FILING_AFTER_VALUATION')
        if metric != 'earnings_yield':
            required = ('COMMON_EXCLUDING_PREFERRED_NCI' if metric == 'book_yield'
                        else 'COMMON_TANGIBLE_EXCLUDING_GOODWILL_INTANGIBLES')
            if fact.get('equity_basis') != required or fact.get('share_count_basis') != 'POINT_IN_TIME':
                reasons.append('COMMON_EQUITY_BASIS_UNCONFIRMED')
        if row.get('identity_status') != 'DOCUMENT_LINKED':
            reasons.append('SECURITY_LINK_UNCONFIRMED')
        value = None if reasons else numerator / p
        if value is not None and not _finite(value):
            reasons.append('RATIO_NOT_FINITE'); value = None
        results[metric] = {'value': value, 'unit': 'x', 'reasons': reasons,
                           'inputs': {'numerator': fact or None, 'price': price or None},
                           'evidence_status': evidence_status}
    return {'schema_version': VERSION, 'config_sha256': CONFIG_SHA256, 'result_kind': kind,
            'code': row['code'], 'cik': row.get('cik'), 'valuation_date': str(valuation),
            'input_vintage': row['input_vintage'], 'business_group': group,
            'classification_basis': 'SIC_SCREEN_PROVISIONAL', 'identity_status': row.get('identity_status'),
            'security_basis': security,
            'primary_metric': primary, 'metrics': results,
            'primary_available': bool(not diagnostic and primary and results[primary]['value'] is not None),
            'score': None, 'rank': None, 'scoring_reason': 'RESEARCH_RAW_ONLY_SCORING_NOT_DEFINED',
            'pit_eligible': False if diagnostic else None}


def candidate_coverage(official_rows, results, valuation_date):
    """Fixed operational membership; raw availability cannot masquerade as scored V."""
    universe = {k: r for k, r in official_rows.items() if not k.startswith('TARGET:')}
    seen, valid = set(), set()
    for r in results:
        if r['code'] in seen or r['code'] not in universe:
            raise ValueError('DUPLICATE_OR_OUT_OF_POPULATION_CODE')
        seen.add(r['code'])
        if (r['valuation_date'] == valuation_date and r['result_kind'] == 'OPERATIONAL_CANDIDATE_RAW'
                and r['primary_available']):
            valid.add(r['code'])
    joint = sum(r['axes']['Q']['score'] is not None and r['axes']['G']['score'] is not None
                and (r['axes']['V']['score'] is not None or k in valid) for k, r in universe.items())
    return {'denominator': len(universe), 'valuation_date': valuation_date,
            'same_date_primary_raw_valid': len(valid), 'potential_joint_input_valid': joint,
            'scored_joint_valid': None, 'preset_feasibility': None, 'actual_preset_totals': None,
            'reason': 'CANDIDATE_RAW_METRIC_IS_NOT_A_V_SCORE'}


BALANCE_COMPONENTS = {
    'common_equity': (('CommonStockholdersEquity',), 'USD'),
    'parent_equity': (('StockholdersEquity',), 'USD'),
    'preferred_shares': (('PreferredStockSharesOutstanding',), 'shares'),
    'common_shares': (('CommonStockSharesOutstanding',), 'shares'),
    'nci': (('MinorityInterest',), 'USD'),
    'goodwill': (('Goodwill',), 'USD'),
    'intangibles_ex_goodwill': (('IntangibleAssetsNetExcludingGoodwill',), 'USD'),
    'combined_intangibles': (('IntangibleAssetsNetIncludingGoodwill', 'GoodwillAndIntangibleAssetsNet'), 'USD'),
}


def _balance_observations(payload, concepts, unit, cutoff):
    """One value per exact balance/filing/accession; retain rejected pointers.

    Shared by the existing numerator extractor and its component audit. No
    cross-period, cross-filing, currency, issued-share or weighted-share fallback.
    """
    from investment_system.qgv.v2_factors import INSTANT_FORMS
    tax = payload.get('facts', {}).get('us-gaap', {})
    grouped, rejected, present = {}, [], False
    for concept in concepts:
        present |= concept in tax
        for observed_unit, rows in tax.get(concept, {}).get('units', {}).items():
            for index, row in enumerate(rows):
                pointer = '/facts/us-gaap/' + concept + '/units/' + observed_unit.replace('~', '~0').replace('/', '~1') + '/' + str(index)
                end, filed = _day(row.get('end')), _day(row.get('filed'))
                reasons = []
                if observed_unit != unit: reasons.append('UNIT_MISMATCH')
                if row.get('start') is not None: reasons.append('INSTANT_REQUIRED')
                if end is None or not 0 <= (cutoff-end).days <= CONFIG['max_age_days']: reasons.append('PERIOD_NOT_ELIGIBLE')
                if filed is None: reasons.append('FILING_DATE_INVALID')
                elif filed > cutoff: reasons.append('FILED_AFTER_CUTOFF')
                if end is not None and filed is not None and end > filed: reasons.append('END_AFTER_FILING')
                if row.get('form') not in INSTANT_FORMS: reasons.append('FORM_NOT_ELIGIBLE')
                if not row.get('accn'): reasons.append('ACCESSION_MISSING')
                if not _finite(row.get('val')): reasons.append('NONFINITE_VALUE')
                if reasons:
                    rejected.append({'json_pointer': pointer, 'reasons': reasons})
                    continue
                key = (end, filed, row['accn'])
                grouped.setdefault(key, []).append((row['val'], pointer))
    accepted = {}
    for key, values in grouped.items():
        if len({v for v, _ in values}) != 1:
            rejected.extend({'json_pointer': p, 'balance_key': [str(v) for v in key],
                             'reasons': ['CONFLICTING_OBSERVATIONS']} for _, p in values)
        else:
            accepted[key] = {'value': values[0][0], 'json_pointers': [p for _, p in values]}
    return accepted, rejected, present


def balance_input_audit(payload, cutoff, class_evidence, primary_metric):
    """Connect held primitives even when class proof prevents book adoption.

    ELIGIBLE_OBSERVATION means only the exact dated fiscal observation. It does
    not assert common-holder attribution, security identity or ratio eligibility.
    Assets/total equity may locate a balance date but never supply common equity.
    """
    anchor_tags = ('CommonStockholdersEquity', 'StockholdersEquity',
                   'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 'Assets')
    keys = set()
    for tag in anchor_tags:
        keys.update(_balance_observations(payload, (tag,), 'USD', cutoff)[0])
    latest = max((k[:2] for k in keys), default=None)
    anchors = [k for k in keys if k[:2] == latest]
    anchor = anchors[0] if len(anchors) == 1 else None
    components = {}
    for name, (tags, unit) in BALANCE_COMPONENTS.items():
        accepted, rejected, present = _balance_observations(payload, tags, unit, cutoff)
        selected = accepted.get(anchor)
        reasons = sorted({r for entry in rejected for r in entry['reasons']})
        if selected is None and accepted: reasons.append('ANCHOR_MISMATCH' if anchor else 'ANCHOR_UNCONFIRMED')
        applicable = (primary_metric in ('book_yield', 'tangible_book_yield') and
                      (name in ('common_equity', 'parent_equity', 'preferred_shares', 'common_shares') or primary_metric == 'tangible_book_yield'))
        components[name] = {
            'status': 'ELIGIBLE_OBSERVATION' if selected else 'PRESENT_BUT_INELIGIBLE' if present else 'NOT_PRESENT_IN_HELD_SOURCE',
            'value': selected['value'] if selected else None, 'unit': unit,
            'primary_applicability': 'INPUT_OR_EXPLICIT_ALTERNATIVE' if applicable else 'UNRESOLVED_MODEL' if primary_metric is None else 'NOT_APPLICABLE',
            'reasons': [] if selected else sorted(set(reasons)),
            'period_end': str(anchor[0]) if selected else None,
            'filed': str(anchor[1]) if selected else None,
            'source': {'accession': anchor[2], 'json_pointers': selected['json_pointers']} if selected else None,
            'rejected_observations': rejected,
        }
    return {'schema_version': 'financial-v-balance-inputs/1',
            'anchor': [str(v) for v in anchor] if anchor else None,
            'anchor_reason': None if anchor else 'BALANCE_ANCHOR_UNCONFIRMED',
            'class_status': class_evidence.get('status'), 'components': components,
            'scope': 'DATED_COMPONENTS_NOT_COMMON_EQUITY_OR_CANDIDATE_ADOPTION'}


def common_book_inputs(payload, cutoff, class_evidence):
    """Conservative USD common-book inputs from one exact balance-sheet filing.

    Parent equity excludes NCI by definition. Direct common equity or explicit zero
    preferred shares is mandatory; preferred par/stated value is never a deduction. Tangible deduction additionally requires explicit zero
    NCI because the consolidated intangible amount otherwise needs attribution.
    """
    empty = {'book_yield': None, 'tangible_book_yield': None, 'reasons': []}
    cik = str(payload.get('cik', '')).zfill(10)
    proof_date = _day(class_evidence.get('date'))
    if (class_evidence.get('status') != 'SINGLE_CLASS_CONFIRMED'
            or class_evidence.get('cik') != cik or not class_evidence.get('source')
            or proof_date is None or proof_date > cutoff):
        return {**empty, 'reasons': ['COMMON_CLASS_BASIS_UNCONFIRMED']}
    def observations(concept, unit='USD'):
        concepts = (concept,) if isinstance(concept, str) else concept
        return {k: v['value'] for k, v in _balance_observations(payload, concepts, unit, cutoff)[0].items()}

    direct_common = observations('CommonStockholdersEquity')
    equity = observations('StockholdersEquity')
    anchors = {**equity, **direct_common}
    if not anchors:
        return {**empty, 'reasons': ['PARENT_EQUITY_UNAVAILABLE']}
    latest_end = max(k[0] for k in anchors)
    latest_filed = max(k[1] for k in anchors if k[0] == latest_end)
    keys = [k for k in anchors if k[:2] == (latest_end, latest_filed)]
    if len(keys) != 1 or proof_date < latest_end:
        return {**empty, 'reasons': ['BALANCE_OR_CLASS_DATE_UNCONFIRMED']}
    key = keys[0]
    preferred_shares = observations('PreferredStockSharesOutstanding', 'shares').get(key)
    shares = observations('CommonStockSharesOutstanding', 'shares').get(key)
    common = direct_common.get(key)
    if common is None and preferred_shares == 0:
        common = equity.get(key)
    if common is None or shares is None or shares <= 0:
        return {**empty, 'reasons': ['COMMON_EQUITY_OR_SAME_FILING_INSTANT_SHARES_UNAVAILABLE']}
    source = {'accession': key[2], 'class_evidence': class_evidence,
              'components': {'parent_equity': equity.get(key), 'direct_common_equity': direct_common.get(key),
                             'preferred_shares': preferred_shares, 'shares': shares},
              'concepts': ['CommonStockholdersEquity', 'StockholdersEquity',
                           'PreferredStockSharesOutstanding', 'CommonStockSharesOutstanding']}
    book = {'value': common / shares, 'unit': 'USD/share', 'currency': 'USD',
            'period_end': str(key[0]), 'filed': str(key[1]), 'source': source,
            'share_basis': 'BALANCE_COMMON:' + key[2], 'share_count_basis': 'POINT_IN_TIME',
            'equity_basis': 'COMMON_EXCLUDING_PREFERRED_NCI'}
    nci = observations('MinorityInterest').get(key)
    tags = BALANCE_COMPONENTS['combined_intangibles'][0]
    combined, rejected, _ = _balance_observations(payload, tags, 'USD', cutoff)
    intangible = combined.get(key, {}).get('value')
    # Conflicting aliases at this exact key cannot be bypassed through a sum.
    aliases = [observations(tag).get(key) for tag in tags]
    conflict = (len({v for v in aliases if v is not None}) > 1 or
                any(r.get('balance_key') == [str(v) for v in key] for r in rejected))
    components = {'MinorityInterest': nci, 'combined_intangibles': intangible,
                  'combined_concepts': list(tags)}
    if intangible is None and not conflict:
        goodwill = observations('Goodwill').get(key)
        other = observations('IntangibleAssetsNetExcludingGoodwill').get(key)
        components.update(Goodwill=goodwill, IntangibleAssetsNetExcludingGoodwill=other)
        if goodwill is not None and other is not None and goodwill >= 0 and other >= 0:
            intangible = goodwill + other
    tangible = None
    if not conflict and nci == 0 and intangible is not None and intangible >= 0:
        tangible = {**book, 'value': (common - intangible) / shares,
                    'equity_basis': 'COMMON_TANGIBLE_EXCLUDING_GOODWILL_INTANGIBLES',
                    'source': {**source, 'tangible_components': components}}
    return {'book_yield': book, 'tangible_book_yield': tangible,
            'reasons': [] if tangible else ['COMMON_ATTRIBUTABLE_INTANGIBLES_UNCONFIRMED']}
