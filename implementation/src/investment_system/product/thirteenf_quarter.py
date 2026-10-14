"""Python reference for the device S16 13F quarter view (web_assets/thirteenf-quarter.js).

Pure functions over the already-public sec-13f-changes.json reports and actual-catalog.json. Reported
quantities and original-unit aggregate values; never unit prices or trades. US ISINs embed CUSIPs.
Eaton uses the reviewed SEC N-PORT identifier; other unmapped identifiers stay NOT_AVAILABLE. Never a producer.
"""
from __future__ import annotations

import re

TARGET = (('asml', 'ASML'), ('lrcx', 'LRCX'), ('klac', 'KLAC'), ('tokyo_electron', '8035'), ('hanmi', '042700'),
          ('nvda', 'NVDA'), ('amd', 'AMD'), ('avgo', 'AVGO'), ('qcom', 'QCOM'), ('intc', 'INTC'), ('msft', 'MSFT'),
          ('googl', 'GOOGL'), ('amzn', 'AMZN'), ('rtx', 'RTX'), ('stry', 'SYK'), ('etn', 'ETN'), ('hubb', 'HUBB'),
          ('gev', 'GEV'), ('rok', 'ROK'))
KINDS = ('NEW', 'ADD', 'REDUCE', 'EXIT')
GAPS = {'filed_date': 'FILING_DATE_NOT_PUBLISHED', 'holdings_count': 'UNCHANGED_POSITIONS_NOT_PUBLISHED',
        'top10_weight': 'REPORTED_VALUES_NOT_PUBLISHED', 'issuer_name': 'ISSUER_NAME_NOT_PUBLISHED'}
# Current-only reviewed SEC N-PORT identity, never inferred from an Irish ISIN.
EATON_EVIDENCE = {'isin': 'IE00B8KQN827', 'cusip': 'G29183103',
                  'source_url': 'https://www.sec.gov/Archives/edgar/data/1100663/000175272425034052/primary_doc.xml',
                  'source_sha256': '1c9162bf36195494f709f310502e389edeb8a08e8c645d7cbdd34d57a0a11639'}


def _char_value(ch):
    if '0' <= ch <= '9':
        return ord(ch) - 48
    if 'A' <= ch <= 'Z':
        return ord(ch) - 55
    return {'*': 36, '@': 37, '#': 38}.get(ch, -1)


def cusip_valid(cusip):
    if not isinstance(cusip, str) or re.fullmatch(r'[0-9A-Z*@#]{8}[0-9]', cusip) is None:
        return False
    total = 0
    for i in range(8):
        v = _char_value(cusip[i]) * (2 if i % 2 == 1 else 1)
        total += v // 10 + v % 10
    return (10 - total % 10) % 10 == int(cusip[8])


def isin_valid(isin):
    if not isinstance(isin, str) or re.fullmatch(r'[A-Z]{2}[0-9A-Z]{9}[0-9]', isin) is None:
        return False
    digits = ''.join(str(_char_value(ch)) for ch in isin)
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def cusip_from_isin(isin):
    if not isin_valid(isin) or isin[:2] != 'US':
        return None
    cusip = isin[2:11]
    return cusip if cusip_valid(cusip) else None


def target_securities(catalog):
    instruments = catalog.get('instruments') if isinstance(catalog, dict) else None
    instruments = instruments if isinstance(instruments, list) else None
    out = []
    for cid, ticker in TARGET:
        found = [i for i in instruments if isinstance(i, dict) and i.get('ticker') == ticker] if instruments is not None else []
        inst = found[0] if len(found) == 1 else None
        label = inst['label'] if inst is not None and isinstance(inst.get('label'), str) else None
        if inst is None:
            out.append({'company_id': cid, 'ticker': ticker, 'label': label, 'cusip': None, 'reason': 'CATALOG_NOT_AVAILABLE'})
            continue
        ref = inst.get('security_reference') or {}
        if ref.get('scheme') == 'EXCHANGE_CODE':
            out.append({'company_id': cid, 'ticker': ticker, 'label': label, 'cusip': None, 'reason': 'NOT_13F_SECURITY'})
            continue
        cusip = cusip_from_isin(ref.get('value')) if ref.get('scheme') == 'ISIN' else None
        if cid == 'etn' and ref.get('scheme') == 'ISIN' and ref.get('value') == EATON_EVIDENCE['isin']:
            cusip = EATON_EVIDENCE['cusip']
        out.append({'company_id': cid, 'ticker': ticker, 'label': label, 'cusip': cusip,
                    'reason': None if cusip else 'CUSIP_NOT_IN_PUBLIC_CATALOG'})
    return out


def _quantity(c):
    return {'kind': c['kind'], 'unit': c['unit'], 'reported_before': c['reported_before'],
            'reported_after': c['reported_after'], 'reported_delta': c['reported_delta']}


def summarize_report(report, targets):
    counts = {k: 0 for k in KINDS}
    changes = report.get('changes') if isinstance(report.get('changes'), list) else []
    by_cusip = {}
    for c in changes:
        if c['kind'] in counts:
            counts[c['kind']] += 1
        by_cusip.setdefault(c['cusip'], []).append(c)
    comparable = report['state'] != 'NOT_AVAILABLE'
    mapped = {t['cusip'] for t in targets if t['cusip']}
    target = []
    for t in targets:
        if t['reason']:
            target.append({'company_id': t['company_id'], 'cusip': t['cusip'], 'status': 'NOT_AVAILABLE', 'reason': t['reason'], 'changes': [], 'multiple_buckets': False})
        elif not comparable:
            target.append({'company_id': t['company_id'], 'cusip': t['cusip'], 'status': 'NOT_AVAILABLE', 'reason': 'COMPARISON_NOT_AVAILABLE', 'changes': [], 'multiple_buckets': False})
        else:
            rows = by_cusip.get(t['cusip'], [])
            target.append({'company_id': t['company_id'], 'cusip': t['cusip'], 'status': 'CHANGED' if rows else 'NO_REPORTED_CHANGE',
                           'reason': None, 'changes': [_quantity(c) for c in rows], 'multiple_buckets': len(rows) > 1})
    other = [{'cusip': c['cusip'], **_quantity(c)} for c in sorted((c for c in changes if c['cusip'] not in mapped), key=lambda c: c['cusip'])]
    out = {'manager_cik': report['manager_cik'], 'previous_quarter': report['previous_quarter'], 'current_quarter': report['current_quarter'],
            'state': report['state'], 'filed_date': None, 'filed_date_reason': GAPS['filed_date'],
            'holdings_count': None, 'holdings_count_reason': GAPS['holdings_count'],
            'top10_weight': None, 'top10_weight_reason': GAPS['top10_weight'],
            'counts': counts, 'change_count': len(changes), 'target': target, 'other': other}
    details = report.get('details')
    if details and comparable:
        out.update(details=details, filed_date=details['current']['filing_date'], filed_date_reason=None,
                   holdings_count=len({h['cusip'] for h in details['current']['reported_holdings']}), holdings_count_reason=None,
                   top10_weight_reason='DERIVED_VALUE_WEIGHTS_NOT_PUBLISHED')
    return out


def playbook_evidence(payload, catalog, config):
    """W2 references and informational E4 candidates from complete same-quarter reports.

    No report/legacy changes-only files cannot establish held counts or full exits.
    One manager counts once; any remaining long SH bucket prevents a full exit.
    """
    data = (payload or {}).get('data', {})
    verified = {m['cik'] for m in data.get('managers', []) if m['state'] == 'VERIFIED'}
    managers = {m['candidate_cik']: m for m in config['managers']}
    reports = [r for r in data.get('reports', []) if r['manager_cik'] in verified and r['manager_cik'] in managers
               and r['state'] == 'LIVE' and r.get('details')]
    latest = max((r['current_quarter'] for r in reports), default=None)
    reports = [r for r in reports if r['current_quarter'] == latest]
    from collections import Counter
    counts = Counter(r['manager_cik'] for r in reports)
    reports = [r for r in reports if counts[r['manager_cik']] == 1]
    out = {}
    for target in target_securities(catalog):
        held, exited, styles = set(), set(), set()
        for r in reports if target['cusip'] else []:
            before = [h for h in r['details']['previous']['reported_holdings'] if h['cusip'] == target['cusip']]
            after = [h for h in r['details']['current']['reported_holdings'] if h['cusip'] == target['cusip']]
            if after:
                held.add(r['manager_cik'])
                styles.update(managers.get(r['manager_cik'], {}).get('styles', []))
            exits = {c['security_key']: c for c in r['changes'] if c['kind'] == 'EXIT' and c['unit'] == 'SH'}
            if before and not after and all(h['security_key'] in exits and exits[h['security_key']]['reported_before'] == h['reported_quantity'] and exits[h['security_key']]['cusip'] == target['cusip'] for h in before):
                exited.add(r['manager_cik'])
        available = bool(reports and target['cusip'])
        out[target['company_id']] = {'quarter': latest if available else None,
            'tracked_holding_count': len(held) if available else None, 'tracked_holding_types': sorted(styles),
            'observed_managers': len({r['manager_cik'] for r in reports}) if available else 0,
            'tracked_managers': len(config['managers']), 'full_exit_count': len(exited) if available else None,
            'structural_event': len(exited) >= 3 if available else False,
            'reason_code': 'THIRTEENF_REPORTED_FULL_EXITS_3_PLUS' if len(exited) >= 3 and available else
                           target['reason'] or ('THIRTEENF_COMPLETE_REPORTS_NOT_AVAILABLE' if not available else None),
            'informational_only': True}
    return out


def target_overlap(summaries, targets):
    out = []
    for t in targets:
        if t['reason']:
            out.append({'company_id': t['company_id'], 'cusip': t['cusip'], 'status': 'NOT_AVAILABLE', 'reason': t['reason'],
                        'entries': [], 'unchanged': [], 'not_available': []})
            continue
        entries, unchanged, na = [], [], []
        for s in summaries:
            row = next((r for r in s['target'] if r['company_id'] == t['company_id']), None)
            if row is None or row['status'] == 'NOT_AVAILABLE':
                na.append(s['manager_cik'])
            elif row['status'] == 'NO_REPORTED_CHANGE':
                unchanged.append(s['manager_cik'])
            else:
                entries.extend({'manager_cik': s['manager_cik'], 'current_quarter': s['current_quarter'], **c} for c in row['changes'])
        status = 'CHANGED' if entries else 'NO_REPORTED_CHANGE' if unchanged else 'NOT_AVAILABLE'
        out.append({'company_id': t['company_id'], 'cusip': t['cusip'], 'status': status,
                    'reason': 'NO_COMPARABLE_REPORT' if status == 'NOT_AVAILABLE' else None,
                    'entries': entries, 'unchanged': unchanged, 'not_available': na})
    return out
