"""Private metadata update ledger. Reuses production parsers; no network or body text.

This is an opt-in collector state, not a replacement public/UI contract. Cursors
describe the observed frontier: overlap rows must still be passed through, so
late arrivals and revisions before the frontier are not silently lost.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, timedelta
import hashlib
import json

from ..markets.us import US_LISTINGS
from ..product import news_signals as ns
from .dart_collection import KST
from .sec_8k_disclosures import index_url


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def issuer_id(company):
    return 'SEC:' + US_LISTINGS[company]['cik'] if company in US_LISTINGS else 'COMPANY:' + company


def _identified(row, identity):
    row['issuer_id'] = issuer_id(row['company_id'])
    row['item_id'] = _digest([row['source'], row['issuer_id'], identity])
    return row


def news_rows(source, company, raw_rows, *, acquired_at, sec=None):
    """Production title/link/relevance normalization, with honest time provenance."""
    rows = []
    for raw in raw_rows:
        row = ns.normalize(source, company, raw, acquired_at=acquired_at,
                           cutoff=acquired_at - timedelta(days=ns.WINDOW_DAYS), counts={})
        if row is None:
            continue
        relation = ns.related_8k(row, sec['events']) if source == 'IR' and sec else None
        result = {k: row[k] for k in ('company_id', 'source', 'title', 'link', 'classification')}
        result.update(published_at=row['published_at'] if source == 'IR' else None, accepted_at=None,
                      source_seen_at=row['published_at'] if source == 'GDELT' else None, filing_date=None,
                      filing_id=None, related_filing_id=relation[0] if relation else None)
        rows.append(_identified(result, row['link']))
    return rows


def sec_rows(company, reports):
    """Already parsed SEC reports -> accession/issuer identity, without inferring publication time."""
    rows = []
    for report in reports:
        row = {'source': 'SEC', 'company_id': company, 'title': None,
               'link': index_url(company, report['accession']), 'published_at': None,
               'source_seen_at': None, 'accepted_at': ns.instant(datetime.fromisoformat(report['accepted_at'])),
               'filing_date': report['filing_date'], 'filing_id': report['accession'],
               'form': report['form'], 'items': report['items'], 'event_date': report['event_date'],
               'related_filing_id': None}
        rows.append(_identified(row, report['accession']))
    return rows


def dart_rows(payload, company):
    """Validated DART public metadata: receipt identity, date precision, no invented acceptance."""
    rows = []
    issuer = 'DART:' + payload['companies'][company]['corp_code']
    for event in payload['events']:
        if event['company_id'] != company:
            continue
        row = {k: event[k] for k in ('source', 'company_id', 'title', 'link', 'classification', 'filing_date', 'accepted_at')}
        row.update(published_at=None, source_seen_at=None, time_precision=event['time_precision'],
                   filing_id=event['rcept_no'], related_filing_id=None, issuer_id=issuer)
        row['item_id'] = _digest(['DART', issuer, event['rcept_no']])
        rows.append(row)
    return rows


class UpdateLedger:
    """Atomic per-batch updates; failures/cache hits never restamp last source success."""

    def __init__(self, state=None):
        self.state = copy.deepcopy(state) if state is not None else {
            'schema_version': 1, 'kind': 'LOCAL_NEWS_UPDATE_STATE', 'sources': {}, 'items': {}, 'cache': {}}
        if (self.state.get('schema_version') != 1 or self.state.get('kind') != 'LOCAL_NEWS_UPDATE_STATE'
                or any(not isinstance(self.state.get(k), dict) for k in ('sources', 'items', 'cache'))):
            raise ValueError('NEWS_UPDATE_STATE_INVALID')

    def cached(self, source, company, *, now, ttl_seconds):
        if not 0 <= ttl_seconds <= 86400:
            raise ValueError('NEWS_CACHE_TTL_INVALID')
        cache = self.state['cache'].get(source + ':' + company)
        if cache and 0 <= (now - datetime.fromisoformat(cache['acquired_at'])).total_seconds() < ttl_seconds:
            return copy.deepcopy(cache)
        return None

    def apply(self, source, company, rows, *, acquired_at, attempted_at, failure=None, cached=False):
        key, attempted = source + ':' + company, ns.instant(attempted_at)
        old = self.state['sources'].get(key, {})
        entry = dict(old, last_attempt_at=attempted, result='FAILED' if failure else 'CACHED' if cached else 'UPDATED',
                     reason_code=failure, changes={'new': 0, 'duplicate': 0, 'revision': 0})
        entry.setdefault('last_success_at', None)
        entry.setdefault('cursor', None)
        if cached and key not in self.state['cache']:
            raise ValueError('NEWS_CACHE_MISSING')
        if failure:
            entry.update(last_failure_at=attempted, last_failure_code=failure)
        if failure or cached:
            self.state['sources'][key] = entry
            return copy.deepcopy(entry)
        acquired = ns.instant(acquired_at)
        if acquired > attempted:
            raise ValueError('NEWS_ACQUISITION_AFTER_ATTEMPT')
        if old.get('last_success_at') and acquired < old['last_success_at']:
            entry['result'] = 'OLDER_INPUT'
            self.state['sources'][key] = entry
            return copy.deepcopy(entry)
        # Stage all mutations first: invalid batches cannot advance the cursor or partially commit rows.
        items = copy.deepcopy(self.state['items'])
        frontier = [entry['cursor']] if entry['cursor'] else []
        seen_ids = set()
        for row in rows:
            expected_issuer = row['issuer_id'] if source == 'DART' and row['issuer_id'].startswith('DART:') else issuer_id(company)
            if row['source'] != source or row['company_id'] != company or row['issuer_id'] != expected_issuer:
                raise ValueError('NEWS_ISSUER_MISMATCH')
            moment = row.get('accepted_at') or row.get('published_at') or row.get('source_seen_at') or row.get('filing_date')
            if source == 'DART' and row.get('time_precision') == 'DATE_KST':
                after_acquisition = date.fromisoformat(row['filing_date']) > acquired_at.astimezone(KST).date()
            else:
                after_acquisition = moment and moment > acquired
            if after_acquisition:
                raise ValueError('NEWS_EVENT_AFTER_ACQUISITION')
            # Match public merge precedence: one response cannot manufacture successive versions.
            if row['item_id'] in seen_ids:
                entry['changes']['duplicate'] += 1
                continue
            seen_ids.add(row['item_id'])
            frontier.append([moment or '', row['item_id']])
            # GDELT's discovery timestamp is observational, not an article content revision.
            fingerprint = _digest({k: v for k, v in row.items() if k != 'source_seen_at'})
            previous = items.get(row['item_id'])
            if previous and previous['content_hash'] == fingerprint:
                entry['changes']['duplicate'] += 1
                continue
            related = None
            if previous is None and source in ns.SOURCES and row.get('title'):
                matches = [i['item_id'] for i in items.values() if i['source'] in ns.SOURCES
                           and i['issuer_id'] == row['issuer_id'] and i.get('title')
                           and abs((datetime.fromisoformat(i.get('published_at') or i['source_seen_at'])
                                    - datetime.fromisoformat(moment)).total_seconds()) <= ns.GROUP_WINDOW.total_seconds()
                           and ns.tokens(i['title']) == ns.tokens(row['title'])]
                related = min(matches) if matches else None
            change = 'revision' if previous else 'duplicate' if related else 'new'
            entry['changes'][change] += 1
            items[row['item_id']] = dict(row, content_hash=fingerprint, version_id=_digest([row['item_id'], fingerprint]),
                previous_version_id=previous['version_id'] if previous else None,
                revision=previous['revision'] + 1 if previous else 1, related_item_id=related,
                first_acquired_at=previous['first_acquired_at'] if previous else acquired,
                acquired_at=acquired, change=change.upper())
        if len(items) > 10000:
            raise ValueError('NEWS_UPDATE_CAPACITY_EXCEEDED')
        entry.update(last_success_at=acquired, cursor=max(frontier) if frontier else None)
        if not entry['changes']['new'] and not entry['changes']['revision']:
            entry['result'] = 'NO_NEW_ITEMS'
        self.state['items'] = items
        self.state['sources'][key] = entry
        self.state['cache'][key] = {'acquired_at': acquired, 'rows': copy.deepcopy(rows)}
        return copy.deepcopy(entry)
