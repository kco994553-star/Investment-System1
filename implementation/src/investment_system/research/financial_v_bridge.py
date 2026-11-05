"""Connect hash-linked held SEC inputs to financial-v-research/1, without scores.

Each metric keeps its own share basis. A quote needs an explicit matching basis
and evidence; this adapter never guesses a split or carries a different day's price.
"""
from collections import Counter
from datetime import date, datetime, time, timezone
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from investment_system.qgv import v2_factors as vf
from investment_system.research.financial_v import BALANCE_COMPONENTS, CONFIG, CONFIG_SHA256, balance_input_audit, common_book_inputs, evaluate
from investment_system.research.xbrl_supplement import supplement

VERSION = 'financial-v-held-bridge/1.1'
X = '{http://www.xbrl.org/2003/instance}'


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _capture(value):
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError
        return stamp.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError):
        raise ValueError('CAPTURE_TIMESTAMP_REQUIRED') from None


def _cover_link(body, cik, symbol, cutoff):
    if b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():
        raise ValueError('COVER_XML_NOT_ELIGIBLE')
    root = ET.fromstring(body)
    contexts = set()
    for context in root.findall(X + 'context'):
        ids = context.findall(X + 'entity/' + X + 'identifier')
        end = (context.findtext(X + 'period/' + X + 'instant')
               or context.findtext(X + 'period/' + X + 'endDate'))
        if (len(ids) == 1 and ids[0].get('scheme') == 'http://www.sec.gov/CIK'
                and (ids[0].text or '').strip().zfill(10) == cik
                and vf._day(end) is not None and vf._day(end) <= cutoff):
            contexts.add(context.get('id'))
    for element in root:
        if not element.tag.startswith('{'):
            continue
        uri, name = element.tag[1:].split('}', 1)
        if (name == 'TradingSymbol' and re.fullmatch(r'https?://xbrl.sec.gov/dei/\d{4}(?:-\d{2}-\d{2})?', uri)
                and element.get('contextRef') in contexts and (element.text or '').strip() == symbol):
            return True
    return False


def _reference(value):
    return (isinstance(value, dict) and re.fullmatch(r'[0-9a-f]{64}', str(value.get('sha256', '')))
            and isinstance(value.get('json_pointer'), str) and value['json_pointer'].startswith('/'))


def _quote_time_faults(quote, valuation, vintage):
    """The prepared IEX handoff carries actual trade time, not only a date label."""
    from investment_system.research.pit_filings import session_close
    faults = []
    if quote.get('price_type') != 'IEX_LAST_REGULAR_TRADE': faults.append('PRICE_TYPE_UNCONFIRMED')
    if quote.get('price_basis') != 'RAW': faults.append('PRICE_RAW_BASIS_REQUIRED')
    if quote.get('trade_validation') != 'ELIGIBLE': faults.append('PRICE_TRADE_VALIDATION_UNCONFIRMED')
    trade, captured = None, None
    try: trade = _capture(quote.get('traded_at'))
    except ValueError: faults.append('PRICE_TRADE_TIME_UNCONFIRMED')
    try: captured = _capture(quote.get('acquired_at'))
    except ValueError: faults.append('PRICE_CAPTURE_TIME_UNCONFIRMED')
    end = session_close(valuation).close_at
    start = datetime.combine(valuation, time(9, 30), ZoneInfo('America/New_York'))
    if trade is not None and (end is None or not start <= trade <= end):
        faults.append('PRICE_OUTSIDE_REGULAR_SESSION')
    if captured is not None:
        if captured > vintage: faults.append('PRICE_CAPTURE_AFTER_VINTAGE')
        if (trade is not None and captured < trade) or (end is not None and captured < end):
            faults.append('PRICE_CAPTURE_BEFORE_SESSION_COMPLETE')
    return faults


def connect(*, record, companyfacts_bytes, shares, cover_bytes, valuation_date, input_vintage, prices=None):
    """Return prepared numerators, evaluated metrics and explicit connection gaps.

    `prices` maps metric name to a prepared price on that metric's documented
    share basis. No ex-post mode is enabled here. The original evaluator enforces
    period/currency/positive-capital/annual-span rules independently for each metric.
    """
    valuation = date.fromisoformat(valuation_date)
    vintage_stamp = _capture(input_vintage)
    acquired_stamp = _capture(record.get('acquired_at'))
    acquired = acquired_stamp.date()
    if acquired_stamp > vintage_stamp or valuation > vintage_stamp.date():
        raise ValueError('INPUT_VINTAGE_NOT_ELIGIBLE')
    if record.get('calc_version') != vf.CALC_VERSION or vf.profile_for_sic(record['sic']) != 'FINANCIAL':
        raise ValueError('FINANCIAL_CALC_VERSION_REQUIRED')
    cik, code = record['cik'], record['code']
    if not re.fullmatch(r'\d{10}', cik) or ':' not in code:
        raise ValueError('ISSUER_AND_CODE_REQUIRED')
    digest = _sha(companyfacts_bytes)
    if digest != record['source_sha256']['companyfacts']:
        raise ValueError('COMPANYFACTS_HASH_MISMATCH')
    payload = json.loads(companyfacts_bytes)
    if str(payload.get('cik', '')).zfill(10) != cik:
        raise ValueError('COMPANYFACTS_CIK_MISMATCH')
    if shares.get('cik') != cik:
        raise ValueError('SHARES_CIK_MISMATCH')
    cutoff = min(acquired, valuation)
    linked = False
    cover_hash = None
    if cover_bytes is not None:
        if _capture(shares.get('acquired_at')) > vintage_stamp:
            raise ValueError('INPUT_VINTAGE_NOT_ELIGIBLE')
        cover_hash = _sha(cover_bytes)
        if cover_hash != shares.get('source_sha256', {}).get('cover'):
            raise ValueError('COVER_HASH_MISMATCH')
        linked = _cover_link(cover_bytes, cik, code.split(':', 1)[1], cutoff)
    measured, filed = vf._day(shares.get('measurement_date')), vf._day(shares.get('filed'))
    status = shares.get('share_class_basis', 'BASIS_UNCONFIRMED')
    if not linked:
        status = 'COVER_SYMBOL_NOT_LINKED'
    elif measured is None or filed is None or measured > cutoff or filed > cutoff:
        status = 'CLASS_DATE_NOT_ELIGIBLE'
    proof = {'status': status, 'cik': cik, 'date': shares.get('measurement_date'),
             'source': {'cover_sha256': cover_hash,
                        'shares_record_sha256': _sha(json.dumps(shares, sort_keys=True).encode())},
             'scope': 'HELD_OPERATIONAL_CLASS_EVIDENCE_NOT_FIXED_SECURITY_ID'}
    taxonomy, currency = vf._taxonomy_and_currency(payload, cutoff)
    eps, eps_reasons = None, []
    if taxonomy is None:
        eps_reasons.append('ANNUAL_TAXONOMY_CURRENCY_ANCHOR_UNAVAILABLE')
    else:
        facts = vf._Facts(payload, taxonomy, currency, cutoff)
        ends = set().union(*(facts.annual_ends(item) for item in vf.ANCHOR_ITEMS))
        if ends:
            fy = max(ends)
            company = vf._Company(facts, fy, sic=record['sic'], profile='FINANCIAL')
            hit, filing = facts.annual('eps_diluted', fy), facts.annual_filing('eps_diluted', fy)
            basis, value = company._basis(), company.eps(0)
            if hit is not None and filing is not None and basis is not None and value is not None:
                eps = {'value': value, 'unit': currency + '/share', 'currency': currency,
                       'period_start': str(hit[1]), 'period_end': str(hit[2]), 'filed': str(filing[1]),
                       'share_basis': 'FY0:' + basis[0] + ':' + str(basis[1]),
                       'source': {'companyfacts_sha256': digest, 'taxonomy': taxonomy,
                                  'accession': filing[0], 'basis_accession': basis[0],
                                  'basis_filed': str(basis[1]), 'rule': 'calc23.1 Company.eps'}}
        if eps is None:
            eps_reasons.append('ANNUAL_DILUTED_EPS_OR_SHARE_BASIS_UNAVAILABLE')
    balance_payload = payload
    balance_supplement = {'added': 0, 'reason': 'HELD_INSTANCE_NOT_AVAILABLE', 'observations': []}
    if cover_bytes is not None:
        filing = {k: shares.get(k) for k in ('accn', 'filed', 'form')}
        concepts = {('us-gaap', tag): {unit} for tags, unit in BALANCE_COMPONENTS.values() for tag in tags}
        try:
            balance_payload, balance_supplement = supplement(payload, cover_bytes, filing, cutoff, concept_units=concepts)
        except ValueError as error:
            balance_supplement = {'added': 0, 'reason': str(error), 'source_sha256': cover_hash,
                                  'filing': filing, 'observations': []}
    balance_digest = _sha(json.dumps(balance_payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
    books = common_book_inputs(balance_payload, cutoff, proof)
    for metric in ('book_yield', 'tangible_book_yield'):
        fact = books[metric]
        concepts = {tag for name, (tags, _) in BALANCE_COMPONENTS.items()
                    if metric == 'tangible_book_yield' or name in ('common_equity', 'parent_equity', 'preferred_shares', 'common_shares')
                    for tag in tags}
        if fact and any(c['concept'] in concepts and c['start'] is None
                and c['end'] == fact['period_end']
                and balance_supplement['filing']['filed'] == fact['filed']
                and balance_supplement['filing']['accn'] == fact['source']['accession']
                for c in balance_supplement.get('conflicts', [])):
            books[metric] = None
            books['reasons'].append('INSTANCE_COMPANYFACTS_CONFLICT')
    inputs = {'earnings_yield': eps, 'book_yield': books['book_yield'],
              'tangible_book_yield': books['tangible_book_yield']}
    for metric in ('book_yield', 'tangible_book_yield'):
        if inputs[metric] is not None:
            inputs[metric]['source']['companyfacts_sha256'] = digest
            if balance_supplement['added']:
                inputs[metric]['source'].update(balance_payload_sha256=balance_digest, instance_sha256=cover_hash)
    common = {'code': code, 'cik': cik, 'sic': record['sic'], 'valuation_date': valuation_date,
              'input_vintage': input_vintage, 'result_kind': 'OPERATIONAL_CANDIDATE_RAW',
              'identity_status': 'DOCUMENT_LINKED' if linked else 'SYMBOL_ONLY', 'security_basis': proof}
    results, prepared = {}, {}
    for metric in CONFIG['metrics']:
        quote = (prices or {}).get(metric)
        faults = []
        if quote is not None:
            faults.extend(_quote_time_faults(quote, valuation, vintage_stamp))
            if quote.get('code') != code or quote.get('cik') != cik:
                faults.append('PRICE_IDENTITY_MISMATCH')
            if not _reference(quote.get('source')):
                faults.append('PRICE_SOURCE_UNCONFIRMED')
            if not _reference(quote.get('basis_source')):
                faults.append('PRICE_BASIS_SOURCE_UNCONFIRMED')
        prepared[metric] = {**common, 'price': quote, 'inputs': {metric: inputs[metric]}}
        result = evaluate(prepared[metric])
        detail = result['metrics'][metric]
        if faults:
            detail['value'] = None
            detail['reasons'].extend(faults)
        results[metric] = detail
    result['metrics'] = results
    primary = result['primary_metric']
    result['primary_available'] = bool(primary and results[primary]['value'] is not None)
    balance = balance_input_audit(balance_payload, cutoff, proof, primary)
    balance['derived_payload_sha256'] = balance_digest
    for name, component in balance['components'].items():
        tags = BALANCE_COMPONENTS[name][0]
        seen = [o for o in balance_supplement['observations'] if o['concept'] in tags]
        component['instance_observations'] = seen
        if component['source'] is not None and any(
                c['concept'] in tags and c['start'] is None and c['end'] == component['period_end']
                and balance_supplement['filing']['filed'] == component['filed']
                and balance_supplement['filing']['accn'] == component['source']['accession']
                for c in balance_supplement.get('conflicts', [])):
            component['status'] = 'PRESENT_BUT_INELIGIBLE'
            component['value'] = None
            component['reasons'] = ['INSTANCE_COMPANYFACTS_CONFLICT']
        if component['status'] == 'NOT_PRESENT_IN_HELD_SOURCE' and seen:
            component['status'] = 'PRESENT_BUT_INELIGIBLE'
            component['reasons'] = sorted({'INSTANCE_' + (o['reason'] or 'CONFLICTING_OBSERVATIONS') for o in seen})
        elif component['status'] == 'NOT_PRESENT_IN_HELD_SOURCE' and cover_bytes is not None and balance_supplement.get('reason'):
            # A held but inadmissible filing was not inspected for this field.
            # Do not turn an unknown XML value into a claim of source absence.
            component['status'] = 'HELD_INSTANCE_NOT_EVALUATED'
            component['reasons'] = ['INSTANCE_' + balance_supplement['reason']]
        if component['source'] is not None:
            component['source']['companyfacts_sha256'] = digest
            if balance_supplement['added']:
                component['source'].update(payload_kind='RESEARCH_INSTANCE_SUPPLEMENTED',
                    derived_payload_sha256=balance_digest, instance_sha256=cover_hash)
    return {'schema_version': VERSION, 'code': code, 'cik': cik, 'cutoff': str(cutoff),
            'inputs': inputs, 'prepared_rows_by_metric': prepared, 'result': result,
            'balance_inputs': balance,
            'balance_supplement': balance_supplement,
            'extraction_reasons': {'earnings_yield': eps_reasons, 'book_inputs': books['reasons']},
            'source_sha256': {'companyfacts': digest, 'cover': cover_hash}}


def summarize(rows):
    """Subtype inputs and shortages; no axis coverage or preset totals are inferred."""
    groups = {}
    for row in rows:
        result = row['result']; group = result['business_group']; primary = result['primary_metric']
        g = groups.setdefault(group, {'codes': 0, 'primary_metric': primary, 'primary_available': 0,
                                     'security_class_documented': 0, 'metrics': {m: {
            'numerator_present': 0, 'positive_numerator': 0, 'same_date_price_present': 0,
            'ratio_valid': 0, 'missing_reasons': Counter()} for m in CONFIG['metrics']}})
        g['codes'] += 1; g['primary_available'] += result['primary_available']
        g['security_class_documented'] += result['security_basis']['status'] == 'SINGLE_CLASS_CONFIRMED'
        for metric, detail in result['metrics'].items():
            fact = row['inputs'][metric]; quote = detail['inputs']['price'] or {}; count = g['metrics'][metric]
            count['numerator_present'] += fact is not None
            count['positive_numerator'] += fact is not None and fact['value'] > 0
            count['same_date_price_present'] += quote.get('date') == result['valuation_date'] and quote.get('value') is not None
            count['ratio_valid'] += detail['value'] is not None
            count['missing_reasons'].update(detail['reasons'])
    return {'operational_denominator': 504, 'financial_codes': len(rows), 'subtypes': groups,
            'same_date_primary_available': sum(r['result']['primary_available'] for r in rows),
            'scored_joint_valid': None, 'preset_totals': None, 'new_external_requests': 0,
            'calc_version': vf.CALC_VERSION, 'candidate_config_sha256': CONFIG_SHA256}
