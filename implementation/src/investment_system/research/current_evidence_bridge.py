"""Link retained documentary evidence to current-expansion.evaluate, without computing financials.

An issuer observation, an archived security description, a dated identity link and
an external fixed security ID are separate facts. None supplies missing price,
representative, share-class or all-class market-cap evidence.
"""
from collections import Counter
from copy import deepcopy
import re

from . import current_expansion as pipeline

SCHEMA = 'current-expansion-staged-evidence/1'


def _source(member, sha256, sources):
    ref = sources.get(member)
    if not ref or ref.get('sha256') != sha256 or not ref.get('source_url') or not ref.get('fetched_at'):
        raise ValueError('SOURCE_REFERENCE_MISMATCH')
    return {'member':member, **deepcopy(ref)}


def _document_links(links):
    out = {}
    for link in links:
        cik = pipeline._cik(link.get('issuer_cik')); ticker = link.get('ticker_observation')
        identity = link.get('cover_identity', {}); proof = link.get('existing_research_evidence', {})
        start, end = pipeline._day(proof.get('from')), pipeline._day(proof.get('to'))
        if (link.get('kind') != 'EXISTING_DOCUMENT_EVIDENCE_LINK' or not cik or not ticker
                or pipeline._cik(identity.get('EntityCentralIndexKey')) != cik or identity.get('TradingSymbol') != ticker
                or not isinstance(identity.get('Security12bTitle'),str) or not identity['Security12bTitle'].strip()
                or not start or not end or start > end or proof.get('level') != 'DOCUMENT_RECONSTRUCTED'
                or not proof.get('source_repo') or not proof.get('source_evidence')
                or not re.fullmatch('[0-9a-f]{40}', proof.get('source_commit', ''))):
            raise ValueError('DOCUMENT_LINK_UNCONFIRMED')
        out.setdefault((cik,ticker), []).append(deepcopy(link))
    return out


def _current_type(identity):
    # Only explicit security-title language; never issuer name or ticker suffix.
    title = ' '.join((identity.get('Security12bTitle') or '').split()).casefold()
    if re.match(r'^class\s+\S+\s+common stock\b',title):return 'COMMON_CLASS'
    if re.match(r'^common stock\b',title):return 'COMMON'
    if re.match(r'^preferred stock\b',title):return 'PREFERRED'
    return None


def link_and_evaluate(*, held, crosswalk, cover_evidence, source_evidence, document_links, basis_date):
    """Read the stored issuer metrics once, build evidence stages, then call evaluate.

    evaluate indexes its supplied candidates locally. Preserve the original catalog
    observation ID separately rather than joining the subset's position to that ID.
    """
    if not pipeline._day(basis_date):raise ValueError('INVALID_BASIS_DATE')
    links = _document_links(document_links)
    covers = {c['evidence_id']:c for c in cover_evidence}
    if len(covers) != len(cover_evidence):raise ValueError('DUPLICATE_COVER_EVIDENCE_ID')
    rows=[]; candidates=[]; evidence={}; observed=set(); issuer_ids=set()
    for index, row in enumerate(crosswalk['rows']):
        oid = row['observation_id']; local_id = str(index)
        if oid in observed:raise ValueError('DUPLICATE_OBSERVATION_ID')
        observed.add(oid)
        if not isinstance(oid,str) or not oid.isdigit() or str(int(oid)) != oid or int(oid) >= len(held['candidates']):
            raise ValueError('INVALID_OBSERVATION_ID')
        candidate = held['candidates'][int(oid)]
        cik = pipeline._cik(candidate.get('cik_str')); ticker=candidate.get('ticker')
        if not cik or cik != row.get('cik') or ticker != row.get('ticker'):
            raise ValueError('CANDIDATE_CROSSWALK_MISMATCH')
        catalog = row['catalog_observation']
        if any(catalog.get(k) != held['source'].get(k) for k in ('sha256','source_ref','observed_at')) or not catalog.get('source_ref'):
            raise ValueError('CATALOG_REFERENCE_MISMATCH')
        f = held['financials'].get(cik)
        if f is not None and f.get('cik') != cik:raise ValueError('CACHED_FINANCIAL_IDENTITY_MISMATCH')
        if f and f.get('state') in ('LIVE','STALE') and f.get('calc_version') != pipeline.vf.CALC_VERSION:
            raise ValueError('CACHED_FINANCIAL_VERSION_MISMATCH')
        issuer_ids.add(cik); f = f or {}
        sub = row.get('submissions_evidence') or {}
        sub_ref = _source(sub['member'],sub['sha256'],source_evidence) if sub else None
        corroborated = sub.get('exact_ticker_match') is True
        if corroborated and ticker not in sub.get('observed_tickers',[]):raise ValueError('EXACT_TICKER_LINK_MISMATCH')
        archived=[]
        for proof in row.get('cover_evidence',[]):
            original=covers.get(proof['evidence_id'])
            keys=('cik','symbol','titles','source_member','source_sha256','accession','context_id','context',
                  'symbol_byte_ranges','title_byte_ranges')
            if (not original or any(original.get(k) != proof.get(k) for k in keys)
                    or original['cik'] != cik or original['symbol'] != ticker):
                raise ValueError('COVER_EVIDENCE_LINK_MISMATCH')
            ref=_source(original['source_member'],original['source_sha256'],source_evidence)
            archived.append({**deepcopy(original),'source_reference':ref,
                             'context_period_is_identity_validity':False})
        bounded=links.get((cik,ticker),[])
        inside=[l for l in bounded if l['existing_research_evidence']['from'] <= basis_date <= l['existing_research_evidence']['to']]
        if len(inside)>1 and any(l['cover_identity'] != inside[0]['cover_identity'] for l in inside[1:]):
            raise ValueError('CONFLICTING_DATED_IDENTITY_DOCUMENTS')
        selected=(inside or sorted(bounded,key=lambda l:l['existing_research_evidence']['to'],reverse=True) or [None])[0]
        interval=selected['existing_research_evidence'] if selected else {}
        identity=selected['cover_identity'] if selected else {}
        current_type=_current_type(identity) if inside else None
        same_state=('DOCUMENTED_AT_BASIS' if inside else 'DOCUMENTED_OUTSIDE_BASIS' if bounded
                    else 'ARCHIVED_DESCRIPTION_ONLY' if archived else 'UNKNOWN')
        type_state=('DOCUMENTED_AT_BASIS' if current_type else 'DOCUMENTED_ARCHIVED_TYPE' if archived or bounded else 'UNKNOWN')
        # These are target-row fields. Their dated applicability is established
        # separately above; observation/capture timestamps never become valid_from.
        e=dict(cik=cik,ticker=ticker,issuer_id='CIK:'+cik,security_id=None,source_ref=catalog['source_ref'],
               basis_date=basis_date,valid_from=interval.get('from'),valid_to=interval.get('to'),
               security_type=current_type,exchange=identity.get('SecurityExchangeName') if inside else None,
               listed=True if inside else None,iex_tradable=None,shell_or_spac=None,representative=None,
               previous_member=None,issuer_market_cap_usd=None,market_cap_basis=None,
               price=None,price_currency=None,price_basis=None,price_date=None,quote_security_id=None,price_source_ref=None,
               original_observation_id=oid,
               document_references={'catalog':deepcopy(catalog),'submissions':sub_ref,'archived_covers':archived,'bounded_links':bounded})
        shares=f.get('v_inputs_v2',{}).get('diluted_shares') or {}
        stages={
            'issuer_link':dict(state='SUBMISSIONS_CORROBORATED' if corroborated else 'CATALOG_ONLY',
                               issuer_id=e['issuer_id'],catalog_reference=deepcopy(catalog),submissions_reference=sub_ref,
                               exact_ticker_match=corroborated,observed_exchanges=deepcopy(sub.get('exchange_values',[])),
                               financial_record_ref='/financials/'+cik,financial_available=f.get('state') in ('LIVE','STALE')),
            'security_type_evidence':dict(state=type_state,current_type=current_type,archived_descriptions=deepcopy(row.get('archived_title_descriptions',[])),
                                         archived_cover_references=archived,bounded_document_references=bounded),
            'same_security_at_basis':dict(state=same_state,value=True if inside else None,valid_from=interval.get('from'),
                                         valid_to=interval.get('to'),basis_date=basis_date,document_reference=selected,
                                         reason=None if inside else 'DATED_SAME_SECURITY_EVIDENCE_MISSING_OR_OUTSIDE_BASIS'),
            'external_fixed_id':dict(state='UNVERIFIED_INPUT' if row.get('security_id') else 'NOT_SUPPLIED',value=None,
                                     supplied_value=row.get('security_id'),reason='EXTERNAL_SECURITY_ID_NOT_EVIDENCED'),
            'representative':dict(state='UNCONFIRMED',value=None,observed_issuer_ticker_rows=row.get('issuer_ticker_multiplicity'),
                                  reason='TICKER_COUNT_DOES_NOT_ESTABLISH_REPRESENTATIVE'),
            'valuation_inputs':dict(
                shares=dict(state='UNCONFIRMED_FOR_MARKET_CAP',candidate_financial_value_present=shares.get('value') is not None,
                            candidate_period_end=shares.get('period_end'),financial_input_ref='/financials/'+cik+'/v_inputs_v2/diluted_shares',
                            all_class_same_day_shares=None,reason='FINANCIAL_DILUTED_SHARES_NOT_ALL_CLASS_MARKET_CAP_PROOF'),
                price=dict(state='NOT_SUPPLIED',value=None,basis_date=basis_date,source_ref=None),
                currency=dict(state='UNCONFIRMED_FOR_PRICE',financial_currency=f.get('currency'),price_currency=None),
                actions=dict(state='UNCONFIRMED_FOR_SHARE_PRICE_LINK',reference=None)),
            'market_cap_eligibility':dict(state='NOT_COMPUTED',value=None,issuer_market_cap_usd=None,
                reasons=['ALL_CLASS_SHARES_UNCONFIRMED','SAME_DAY_RAW_PRICE_MISSING','QUOTE_SECURITY_LINK_MISSING',
                         'PRICE_CURRENCY_UNCONFIRMED','SHARE_PRICE_ACTION_SCALE_UNCONFIRMED']),
        }
        rows.append(dict(original_observation_id=oid,evaluation_observation_id=local_id,cik=cik,ticker=ticker,
                         stages=stages,engine_evidence=e))
        candidates.append(deepcopy(candidate)); evidence[local_id]=e
    source={**deepcopy(held['source']), 'complete':False, 'scope':'HELD_FINANCIAL_CROSSWALK_SUBSET',
            'selection_scope':'EXACT_SUPPLIED_CROSSWALK_ROWS', 'catalog_rows_observed':len(held['candidates'])}
    evaluated=pipeline.evaluate(candidates,financials=held['financials'],evidence=evidence,source=source,basis_date=basis_date)
    for linked, result in zip(rows,evaluated['rows']):
        if (result['ticker'] != linked['ticker'] or result['cik'] != linked['cik']
                or result['raw_metrics'] != ((held['financials'].get(linked['cik']) or {}).get('metrics') or {})):
            raise AssertionError('CACHED_METRICS_CHANGED')
        linked['pipeline_result']=dict(eligibility=result['eligibility'],reasons=result['reasons'],
                                       calculation_attempted=result['calculation_attempted'],score=result['score'],rank=result['rank'])
    counts={stage:dict(Counter(r['stages'][stage]['state'] for r in rows)) for stage in
            ('issuer_link','security_type_evidence','same_security_at_basis','external_fixed_id','representative','market_cap_eligibility')}
    return dict(schema_version=SCHEMA,basis_date=basis_date,visibility='PRIVATE_RESEARCH',rows=rows,
                counts=dict(candidate_rows=len(rows),unique_issuers=len(issuer_ids),stages=counts),
                pipeline_inputs=dict(candidates=candidates,evidence=evidence,source=source,
                                     financials_ref='ORIGINAL_VERIFIED_HELD_NORMALIZED_CACHE',selected_issuer_ids=sorted(issuer_ids)),
                financial_reuse=dict(financial_records_recomputed=0,raw_metrics_equal=True,
                                     financial_issuers_reused=len(issuer_ids & set(held['financials']))),evaluation=evaluated)
