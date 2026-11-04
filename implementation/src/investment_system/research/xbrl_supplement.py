"""Exact, offline XBRL-instance supplements; never changes an official extraction rule.

Only consolidated standard concepts already allowed by calc23.1 are read. Missing
companyfacts observations may be added; conflicting observations are never replaced.
The returned payload is research input, not a publication or collector side effect.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import io
import math
import re
import xml.etree.ElementTree as ET

from investment_system.qgv import v2_factors as vf

X = '{http://www.xbrl.org/2003/instance}'
ISO = 'http://www.xbrl.org/2003/iso4217'


def _day(value):
    return vf._day(value)


def supplement(payload, xml, filing, cutoff):
    """Return (copied companyfacts, audit), retaining accession/period/unit provenance."""
    if (not isinstance(filing, dict) or filing.get('form') not in vf.INSTANT_FORMS
            or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', str(filing.get('accn', '')))
            or _day(filing.get('filed')) is None or _day(filing['filed']) > cutoff):
        raise ValueError('FILING_NOT_ELIGIBLE')
    if (not isinstance(xml, bytes) or len(xml) > 32 * 1024 * 1024
            or b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper()):
        raise ValueError('XML_NOT_ELIGIBLE')
    namespaces = {}
    for _, (prefix, uri) in ET.iterparse(io.BytesIO(xml), events=('start-ns',)):
        if prefix in namespaces and namespaces[prefix] != uri:
            raise ValueError('XML_NAMESPACE_REBOUND')
        namespaces[prefix] = uri
    root = ET.fromstring(xml)
    if root.tag != X + 'xbrl':
        raise ValueError('XML_INSTANCE_REQUIRED')
    cik = str(payload.get('cik', '')).zfill(10)
    if not re.fullmatch(r'\d{10}', cik):
        raise ValueError('CIK_REQUIRED')
    currencies = {u for tax in payload.get('facts', {}).values() for fact in tax.values()
                  for u in fact.get('units', {}) if re.fullmatch('[A-Z]{3}', u)}
    # A source with no monetary concepts can be supplemented in USD only. No FX inference.
    currencies = currencies or {'USD'}
    allowed = {}
    for tax, items in vf.CONCEPTS.items():
        for item, concepts in items.items():
            unit = {'shares'} if item == 'diluted_shares' else (
                {c + '/shares' for c in currencies} if item == 'eps_diluted' else currencies)
            for name in concepts:
                allowed.setdefault((tax, name), set()).update(unit)
    allowed[('dei', 'EntityCommonStockSharesOutstanding')] = {'shares'}
    ctx = {}
    for e in root.findall(X + 'context'):
        ids = e.findall(X + 'entity/' + X + 'identifier')
        if (len(ids) != 1 or ids[0].get('scheme') != 'http://www.sec.gov/CIK'
                or (ids[0].text or '').strip().zfill(10) != cik
                or e.find('.//' + X + 'segment') is not None or e.find(X + 'scenario') is not None):
            continue
        period = e.find(X + 'period')
        if period is None:
            continue
        instant = period.findtext(X + 'instant')
        start, end = period.findtext(X + 'startDate'), period.findtext(X + 'endDate')
        if instant is not None:
            if start is not None or end is not None:
                continue
            start, end = None, instant
        if (_day(end) is None or _day(end) > _day(filing['filed'])
                or start is not None and (_day(start) is None or _day(start) > _day(end))):
            continue
        if e.get('id') in ctx:
            raise ValueError('DUPLICATE_CONTEXT_ID')
        ctx[e.get('id')] = (start, end)

    def measure(text):
        prefix, sep, name = (text or '').strip().partition(':')
        if not sep:
            prefix, name = '', prefix
        uri = namespaces.get(prefix)
        if uri == ISO and name in currencies:
            return name
        if uri == X[1:-1] and name == 'shares':
            return name
        return None

    units = {}
    for e in root.findall(X + 'unit'):
        simple = e.findall(X + 'measure')
        unit = measure(simple[0].text) if len(simple) == 1 and len(e) == 1 else None
        divide = e.find(X + 'divide')
        if divide is not None:
            num = divide.findall(X + 'unitNumerator/' + X + 'measure')
            den = divide.findall(X + 'unitDenominator/' + X + 'measure')
            if len(num) == len(den) == 1 and measure(den[0].text) == 'shares':
                n = measure(num[0].text)
                unit = n + '/shares' if n in currencies else None
        if e.get('id') in units:
            raise ValueError('DUPLICATE_UNIT_ID')
        units[e.get('id')] = unit
    groups = defaultdict(list)
    skipped = Counter()
    for e in root:
        if 'contextRef' not in e.attrib or not e.tag.startswith('{'):
            continue
        uri, name = e.tag[1:].split('}', 1)
        tax = ('us-gaap' if re.fullmatch(r'https?://fasb.org/us-gaap/\d{4}(?:-\d{2}-\d{2})?', uri)
               else 'ifrs-full' if re.fullmatch(r'https?://xbrl.ifrs.org/taxonomy/\d{4}-\d{2}-\d{2}/ifrs-full', uri)
               else 'dei' if re.fullmatch(r'https?://xbrl.sec.gov/dei/\d{4}(?:-\d{2}-\d{2})?', uri) else None)
        if (tax, name) not in allowed:
            skipped['CONCEPT_NOT_ALLOWED'] += 1
            continue
        period, unit = ctx.get(e.get('contextRef')), units.get(e.get('unitRef'))
        if period is None or unit not in allowed[(tax, name)]:
            skipped['CONTEXT_OR_UNIT_NOT_ELIGIBLE'] += 1
            continue
        try:
            number = Decimal((e.text or '').strip())
            if not number.is_finite():
                raise ValueError()
            value = int(number) if number == number.to_integral_value() else float(number)
            if not math.isfinite(value):
                raise ValueError()
        except (ValueError, InvalidOperation, OverflowError):
            skipped['VALUE_NOT_FINITE'] += 1
            continue
        groups[(tax, name, unit, *period)].append(value)
    result = deepcopy(payload)
    audit = {'source_sha256': hashlib.sha256(xml).hexdigest(), 'filing': dict(filing),
             'added': 0, 'additions': [], 'conflicts': [], 'skipped': dict(skipped)}
    for (tax, name, unit, start, end), values in sorted(groups.items(), key=str):
        old = result.get('facts', {}).get(tax, {}).get(name, {}).get('units', {}).get(unit, [])
        hits = [r for r in old if r.get('start') == start and r.get('end') == end
                and r.get('accn') == filing['accn'] and r.get('filed') == filing['filed']]
        key = {'taxonomy': tax, 'concept': name, 'unit': unit, 'start': start, 'end': end}
        if len(set(values + [r.get('val') for r in hits])) > 1:
            audit['conflicts'].append({**key, 'instance_values': sorted(set(values)), 'archived_values': [r['val'] for r in hits]})
            continue
        if hits:
            continue
        row = {**filing, 'end': end, 'val': values[0]}
        if start is not None:
            row['start'] = start
        result.setdefault('facts', {}).setdefault(tax, {}).setdefault(name, {}).setdefault('units', {}).setdefault(unit, []).append(row)
        audit['added'] += 1
        audit['additions'].append({**key, 'value': values[0]})
    return result, audit
