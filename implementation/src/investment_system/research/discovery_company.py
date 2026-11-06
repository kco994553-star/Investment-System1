"""Offline discovery evidence/review producer. No QGV calculation or publication.

Facts are extracted from held bytes, judgments are explicit analyst attestations,
and explanations are projections of those judgments, never new source facts.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
import xml.etree.ElementTree as ET

from investment_system.contracts.global_universe import IssuerIdentity

VERSION = 'discovery-company/v1'
RULES = 'discovery-rules/1'
GATES = ('IDENTITY', 'BUSINESS', 'DISCOVERY', 'ATTRACTIVENESS', 'COUNTER_REVIEW', 'CURRENTNESS')
TYPES = {'SLOW_GROWER', 'STALWART', 'FAST_GROWER', 'CYCLICAL', 'TURNAROUND', 'ASSET_PLAY'}
SIGNALS = {'SPINOFF', 'INSIDER_OPEN_MARKET_PURCHASE', 'INSIDER_COMPENSATION',
           'BUYBACK_PLAN', 'BUYBACK_EXECUTED', 'SHARE_COUNT_CHANGE'}
REGIONS = {'REVENUE', 'PRODUCTION', 'HEADQUARTERS', 'PERFORMANCE', 'REPLICATION',
           'PROFITABILITY', 'EXPANSION', 'SATURATION', 'PROTECTION', 'ACQUISITION_EFFECT', 'FX_EFFECT'}
CRITICAL = {'IDENTITY_ERROR', 'CORE_EVIDENCE_ERROR', 'MATERIAL_REFUTATION'}
TRANSITIONS = {
    'CANDIDATE': {'IN_REVIEW'}, 'IN_REVIEW': {'SELECTED'},
    'SELECTED': {'REVIEW_REQUIRED', 'SUSPENDED'},
    'REVIEW_REQUIRED': {'SELECTED', 'SUSPENDED', 'REMOVED'},
    'SUSPENDED': {'IN_REVIEW', 'REMOVED'}, 'REMOVED': {'IN_REVIEW'},
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def _content_id(kind, *parts):
    # Evidence/history IDs only; never an issuer/security identity generator.
    return kind + '_' + digest(parts)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field}: required text')
    return value


def _time(value):
    dt = datetime.fromisoformat(_text(value, 'time').replace('Z', '+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('time requires timezone')
    return dt.astimezone(timezone.utc)


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('invalid date')
    return date.fromisoformat(value)


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('invalid hash')


def _unique(rows, key):
    out = {}
    for row in rows:
        rid = _text(row[key], key)
        if rid in out:
            raise ValueError(f'duplicate {key}')
        out[rid] = row
    return out


def extract_fact(body: bytes, receipt: dict, selector: dict, company_id: str, metadata: dict) -> dict:
    """Read one exact source field; receipt follows RawArtifactManifest.

    XML text blocks retain original markup (reader must escape). No text rewrite,
    imputation, generated text, XML external entities, or network transport.
    """
    if sha256(body).hexdigest() != receipt['sha256'] or len(body) != receipt['bytes']:
        raise ValueError('source hash/size mismatch')
    _text(company_id, 'company_id')
    if set(selector) == {'json_pointer'}:
        pointer = selector['json_pointer']
        if not isinstance(pointer, str) or (pointer and not pointer.startswith('/')):
            raise ValueError('invalid JSON pointer')
        value = json.loads(body, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
        for part in pointer.split('/')[1:]:
            part = part.replace('~1', '/').replace('~0', '~')
            if isinstance(value, list):
                if not re.fullmatch('0|[1-9][0-9]*', part):
                    raise ValueError('invalid array pointer')
                value = value[int(part)]
            else:
                value = value[part]
    elif set(selector) == {'xml_id'}:
        if b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():
            raise ValueError('XML declarations not accepted')
        nodes = [n for n in ET.fromstring(body).iter() if n.get('id') == selector['xml_id']]
        if len(nodes) != 1:
            raise ValueError('XML locator not unique')
        value = ''.join(nodes[0].itertext())
    else:
        raise ValueError('unsupported source selector; generated text is not a fact')
    fact = dict(company_id=company_id, document_id=receipt['artifact_id'], sha256=receipt['sha256'],
                source_url=receipt['source_url'], locator=deepcopy(selector), value=value,
                published_on=metadata.get('published_on'), published_at=metadata.get('published_at'),
                period=deepcopy(metadata.get('period', {'start': None, 'end': None})),
                acquired_at=receipt['fetched_at'], unit=metadata.get('unit'),
                region=metadata.get('region'), region_basis=metadata.get('region_basis'),
                origin='SOURCE_EXTRACT', source_assertion=True)
    # Same source observation with corrected provenance is a new immutable version.
    fact['evidence_id'] = _content_id('discovery_evidence', digest(fact))
    return fact


def _validate_fact(f, company, as_of):
    if f['company_id'] != company:
        raise ValueError('cross-company evidence')
    if f['origin'] != 'SOURCE_EXTRACT':
        raise ValueError('generated content cannot be a source fact')
    for key in ('evidence_id', 'document_id', 'source_url'):
        _text(f[key], key)
    if not f['source_url'].startswith(('https://', 'http://')):
        raise ValueError('source URL required')
    _sha(f['sha256'])
    if set(f['locator']) not in ({'json_pointer'}, {'xml_id'}):
        raise ValueError('source locator required')
    if f['published_on'] is not None and _day(f['published_on']) > as_of.date():
        raise ValueError('future publication')
    if f['published_at'] is not None:
        publication = _time(f['published_at'])
        if publication > as_of:
            raise ValueError('future publication time')
        if f['published_on'] is not None and publication.date() != _day(f['published_on']):
            raise ValueError('publication date/time mismatch (UTC date)')
    if _time(f['acquired_at']) > as_of:
        raise ValueError('future acquisition')
    start, end = f['period']['start'], f['period']['end']
    if start is not None:
        _day(start)
    if end is not None:
        _day(end)
    if start is not None and end is not None and start > end:
        raise ValueError('inverted source period')
    canonical(f)


def _validate_judgment(j, facts):
    if j['category'] not in {*GATES, 'TYPE', 'STRENGTH', 'REGION', 'SIGNAL', 'RISK', 'AWARENESS'}:
        raise ValueError('unknown judgment category')
    topics = {'TYPE': TYPES, 'SIGNAL': SIGNALS, 'REGION': REGIONS,
              'AWARENESS': {'CONSUMER_CONTACT', 'MARKET_ATTENTION'}}
    if j['category'] in topics and j['topic'] not in topics[j['category']]:
        raise ValueError('unknown judgment topic')
    if j['status'] not in {'CONFIRMED', 'UNCONFIRMED', 'REFUTED'} or j['rule_version'] != RULES:
        raise ValueError('judgment status/rule version')
    for flag in ('core', 'material'):
        if type(j[flag]) is not bool:
            raise ValueError('judgment flag must be boolean')
    _text(j['claim'], 'claim')
    _text(j['reason'], 'reason')
    for field in ('evidence_ids', 'counterevidence_ids'):
        ids = j[field]
        if not isinstance(ids, list) or len(set(ids)) != len(ids):
            raise ValueError('invalid evidence IDs')
        if any(i not in facts for i in ids):
            raise ValueError('missing evidence reference')
    if j['status'] in {'CONFIRMED', 'REFUTED'}:
        _text(j['reviewed_by'], 'reviewed_by')


def _is_supported(j, facts, invalidated):
    return (j['status'] == 'CONFIRMED' and bool(j['evidence_ids'])
            and all(facts[i]['value'] is not None and facts[i]['published_on'] is not None
                    and i not in invalidated for i in j['evidence_ids']))


def _display(record):
    js = record['judgments']
    def rows(category):
        return [deepcopy(j) for j in js if j['category'] == category]
    counters = sorted({h['evidence_id'] for h in record['counterevidence_history']})
    facts = {f['evidence_id']: f for f in record['evidence']}
    return dict(list_eligible=record['state'] in {'SELECTED', 'REVIEW_REQUIRED'},
                mark=record['state'] if record['state'] in {'SELECTED', 'REVIEW_REQUIRED'} else None,
                state_reason=record['state_reason'], business=rows('BUSINESS'),
                discovery_reason=rows('DISCOVERY'), selection_summary=rows('ATTRACTIVENESS'),
                strengths=rows('STRENGTH'), regions=rows('REGION'), signals=rows('SIGNAL'),
                types=rows('TYPE'), risks=[deepcopy(facts[i]) for i in counters],
                risk_judgments=rows('RISK'), unknowns=deepcopy(record['unknowns']))


def _validate_snapshot(previous):
    """A digest proves integrity, not authorization; validate internal state history.

    The enclosing private store/authentication still determines who may supply a
    snapshot. This is not a signature or a replacement for Main's access control.
    """
    state, first, last = 'CANDIDATE', None, None
    for h in previous['history']:
        at = _time(h['at'])
        if h['from_state'] != state or h['to_state'] not in TRANSITIONS[state]:
            raise ValueError('invalid previous state history')
        if last is not None and at < last or at > _time(previous['as_of']):
            raise ValueError('invalid previous history time')
        _text(h['reason'], 'history reason')
        if h['to_state'] == 'SELECTED':
            _text(h['reviewer'], 'history reviewer')
            first = first or h['at']
        state, last = h['to_state'], at
    if previous['state'] != state or previous['first_selected_at'] != first:
        raise ValueError('previous selection history mismatch')
    if previous['history_ref'] != _content_id('discovery_history', previous['company_id'], digest(previous['history'])):
        raise ValueError('previous history reference mismatch')
    facts = _unique(previous['evidence'], 'evidence_id')
    for j in previous['judgments']:
        _validate_judgment(j, facts)
    ready = (all(any(j['category'] == g and j['core'] and _is_supported(j, facts, previous['invalidated_evidence_ids'])
                     for j in previous['judgments']) for g in GATES)
             and not any((j['core'] and not _is_supported(j, facts, previous['invalidated_evidence_ids']))
                         or (j['material'] and j['status'] == 'REFUTED') for j in previous['judgments']))
    if previous['selection_ready'] != ready or state == 'SELECTED' and not ready:
        raise ValueError('previous selection gates mismatch')
    if previous['display'] != _display(previous) or previous['publication_approved'] is not False:
        raise ValueError('previous display/publication mismatch')


def evaluate(package: dict, previous: dict | None = None) -> dict:
    """Deterministic projection of verified extracts + explicit analyst reviews.

    This validates traceability, not the semantic truth of an analyst assertion.
    Real jobs must extract held source bytes in the CLI before calling evaluate.
    """
    p = deepcopy(package)
    company = _text(p['company_id'], 'company_id')
    registry = p['registry'][company]
    issuer = IssuerIdentity(registry['issuer_id'], registry['name'], registry['country_code'])
    identity = dict(issuer_id=issuer.issuer_id, security_id=registry.get('security_id'), listing_id=registry.get('listing_id'))
    if identity['listing_id'] is not None and identity['security_id'] is None:
        raise ValueError('listing requires upstream security reference')
    as_of = _time(p['as_of'])
    _text(p['population'], 'population'); _text(p['review_scope'], 'review_scope')
    facts = _unique(p['evidence'], 'evidence_id')
    js = _unique(p['judgments'], 'judgment_id')
    for f in facts.values():
        _validate_fact(f, company, as_of)
    for j in js.values():
        _validate_judgment(j, facts)
    if set(p['awareness']) != {'consumer_contact', 'market_attention'}:
        raise ValueError('awareness contract; unmeasured is null')
    for key, ref in p['awareness'].items():
        if ref is not None and (ref not in js or js[ref]['category'] != 'AWARENESS'
                                or js[ref]['topic'] != key.upper()):
            raise ValueError('awareness requires specific evidence-backed judgment')
    for value in p['unknowns']:
        _text(value, 'unknown item')
    # Normalize order only, never source values or unknowns into zeros/false.
    p['evidence'] = [facts[k] for k in sorted(facts)]
    p['judgments'] = [js[k] for k in sorted(js)]
    p['events'] = sorted(p.get('events', []), key=lambda x: (_time(x['at']), x['event_id']))
    input_hash = digest(p)
    if previous is not None:
        prior = deepcopy(previous); claimed_hash = prior.pop('record_hash')
        if digest(prior) != claimed_hash:
            raise ValueError('previous record hash mismatch')
        _validate_snapshot(previous)
        if previous['schema_version'] != VERSION or previous['company_id'] != company:
            raise ValueError('previous company/schema mismatch')
        if previous['identity_ref'] != identity:
            raise ValueError('company identity changed; separate identity review required')
        if _time(previous['as_of']) > as_of:
            raise ValueError('cannot rewrite prior history')
        if previous['input_hash'] == input_hash:
            return deepcopy(previous)
    old_facts = {f['evidence_id']: f for f in previous['evidence']} if previous else {}
    for eid, f in old_facts.items():
        if eid in facts and f != facts[eid]:
            raise ValueError('evidence is append-only; use a new version ID')
        facts.setdefault(eid, deepcopy(f))
    state = previous['state'] if previous else 'CANDIDATE'
    reason = previous['state_reason'] if previous else 'AUTOMATIC_CANDIDATE_REQUIRES_REVIEW'
    history = deepcopy(previous['history']) if previous else []
    events = deepcopy(previous['events']) if previous else []
    invalidated = set(previous['invalidated_evidence_ids']) if previous else set()
    affected = set()
    def transition(target, why):
        nonlocal state, reason
        if target != state:
            history.append(dict(from_state=state, to_state=target, at=p['as_of'], reason=why,
                                rule_version=RULES, reviewer=p.get('reviewer')))
        state, reason = target, why
    if previous and p['judgments'] != previous['judgments'] and state == 'SELECTED':
        transition('REVIEW_REQUIRED', 'JUDGMENTS_CHANGED')
    seen = {ev['event_id']: ev for ev in events}
    for ev in p['events']:
        _text(ev['event_id'], 'event_id'); _text(ev['reason'], 'event reason')
        _text(ev['document_id'], 'document_id'); _sha(ev['sha256'])
        if ev['kind'] not in CRITICAL | {'DOCUMENT_CHANGED', 'EVIDENCE_AGED', 'NEW_FILING'}:
            raise ValueError('unknown event kind')
        if ev['event_id'] in seen:
            if seen[ev['event_id']] != ev:
                raise ValueError('conflicting event ID')
            continue
        if _time(ev['at']) > as_of or (previous and _time(ev['at']) < _time(previous['as_of'])):
            raise ValueError('event time outside current processing window')
        if any(eid not in facts for eid in ev['evidence_ids']):
            raise ValueError('event evidence reference missing')
        changed = {j['judgment_id'] for j in js.values()
                   if set(j['evidence_ids'] + j['counterevidence_ids']) & set(ev['evidence_ids'])}
        affected.update(changed)
        for jid in changed:
            js[jid]['status'] = 'REFUTED' if ev['kind'] in CRITICAL else 'UNCONFIRMED'
        if changed and ev['kind'] in CRITICAL | {'DOCUMENT_CHANGED'}:
            invalidated.update(ev['evidence_ids'])
        if changed and state in {'SELECTED', 'REVIEW_REQUIRED'}:
            transition('SUSPENDED' if ev['kind'] in CRITICAL else 'REVIEW_REQUIRED', ev['reason'])
        events.append(deepcopy(ev)); seen[ev['event_id']] = deepcopy(ev)
    blocked = [cat for cat in GATES if not any(j['category'] == cat and j['core']
               and _is_supported(j, facts, invalidated) for j in js.values())]
    unresolved_core = sorted(j['judgment_id'] for j in js.values()
                             if j['core'] and not _is_supported(j, facts, invalidated))
    refuted = sorted(j['judgment_id'] for j in js.values() if j['material'] and j['status'] == 'REFUTED')
    ready = not (blocked or unresolved_core or refuted)
    if refuted and state in {'SELECTED', 'REVIEW_REQUIRED'}:
        transition('SUSPENDED', 'REVIEWED_MATERIAL_REFUTATION')
    if state == 'SELECTED' and not ready:
        transition('REVIEW_REQUIRED', 'CORE_REVIEW_INCOMPLETE')
    requested = p.get('requested_state')
    if requested is not None:
        _text(p.get('reviewer'), 'reviewer'); _text(p.get('transition_reason'), 'transition reason')
        if requested not in TRANSITIONS:
            raise ValueError('unknown state')
        # A failed selection request is retained as a blocked review, not promoted.
        if requested == 'SELECTED' and not ready:
            requested = None
        if requested is not None and requested != state:
            if requested not in TRANSITIONS[state]:
                raise ValueError('invalid state transition')
            if state == 'SELECTED' and requested == 'SUSPENDED' and not any(e['kind'] in CRITICAL for e in p['events']):
                raise ValueError('direct suspension requires critical evidence event')
            transition(requested, p['transition_reason'])
    first = previous['first_selected_at'] if previous else None
    if first is None and state == 'SELECTED':
        first = p['as_of']
    counter_history = {h['evidence_id']: deepcopy(h) for h in previous['counterevidence_history']} if previous else {}
    current_counters = {eid for j in js.values() for eid in j['counterevidence_ids']}
    for eid in current_counters:
        counter_history.setdefault(eid, dict(evidence_id=eid, first_recorded_at=p['as_of']))
    for eid, h in counter_history.items():
        h['disposition'] = 'CURRENT' if eid in current_counters else 'RETAINED_FOR_REVIEW'
    result = dict(schema_version=VERSION, rule_version=RULES, company_id=company,
                  company_name=registry['name'], identity_ref=identity, qgv_ref={'company_id': company},
                  as_of=p['as_of'], population=p['population'], review_scope=p['review_scope'],
                  state=state, state_reason=reason, first_selected_at=first,
                  last_reviewed_at=p['as_of'] if p.get('reviewer') else (previous['last_reviewed_at'] if previous else None),
                  evidence=[facts[k] for k in sorted(facts)], judgments=[js[k] for k in sorted(js)],
                  awareness=p['awareness'], unknowns=p['unknowns'], selection_ready=ready,
                  blocked_gates=blocked, unresolved_core=unresolved_core, material_refutations=refuted,
                  affected_judgment_ids=sorted(affected), invalidated_evidence_ids=sorted(invalidated),
                  events=events, history=history, history_ref=_content_id('discovery_history', company, digest(history)),
                  counterevidence_history=[counter_history[k] for k in sorted(counter_history)],
                  publication_approved=False,
                  previous_record_hash=previous['record_hash'] if previous else None, input_hash=input_hash)
    result['display'] = _display(result)
    result['record_hash'] = digest(result)
    return result


def summarize(records):
    """Denominator is explicit reviewed input companies, never all-market coverage."""
    if len({r['company_id'] for r in records}) != len(records):
        raise ValueError('duplicate reviewed company')
    return dict(reviewed_companies=len(records), states={s: sum(r['state'] == s for r in records) for s in TRANSITIONS},
                evidence_count=sum(len(r['evidence']) for r in records),
                confirmed_judgments=sum(j['status'] == 'CONFIRMED' for r in records for j in r['judgments']),
                gate_coverage={g: {'valid': sum(g not in r['blocked_gates'] for r in records),
                                   'denominator': len(records)} for g in GATES},
                item_coverage={g: {'confirmed_companies': sum(any(j['category'] == g and j['status'] == 'CONFIRMED'
                    for j in r['judgments']) for r in records), 'denominator': len(records)}
                    for g in ('TYPE','STRENGTH','REGION','SIGNAL','RISK','AWARENESS')},
                source_requests=0, external_ai_calls=0, publication_approved=False)
