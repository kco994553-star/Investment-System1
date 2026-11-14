"""Price-free population sidecar and read-only sheet review; never selects/publishes.

Keep the existing exact universe-codes/1 producer and reader unchanged. Trusted
callers supply independent source/mapping pins; hashes prove integrity, not the
truth of an external security or Google-symbol claim.
"""
from copy import deepcopy
from datetime import date
import hashlib
import json
import re

from ..universe import universe_codes
from .sector_qgv import digest, timestamp
from .qgv_555_preview import top500_view
from .dual_qgv_delivery import MAX_BYTES

SCHEMA = 'population-public-list/1'
IDENTIFIERS = {'PERMNO','FIGI','ISIN','CUSIP','EXCHANGE_SECURITY_ID','PROVIDER_SECURITY_ID'}
META = {'source_kind','data_kind','population_id','population_version','basis_date','apply_at',
        'mapping_day','input_cutoff','null_reasons'}
NULLABLE = {'population_version','basis_date','apply_at','mapping_day','input_cutoff'}
NULL_CODES = {'LEGACY_SOURCE_NOT_RECORDED','NOT_DECIDED','SOURCE_NOT_DATED',
              'MAPPING_AS_OF_UNCONFIRMED','SOURCE_VERSION_UNRECORDED','APPLY_TIME_NOT_DECIDED',
              'INPUT_CUTOFF_NOT_RECORDED'}


def _need(ok, reason):
    if not ok: raise ValueError(reason)


def _text(value): return isinstance(value,str) and bool(value) and value==value.strip()
def _token(value): return isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_.:\-]{1,160}',value) is not None
def _google(value): return isinstance(value,str) and re.fullmatch(r'(?:NASDAQ|NYSE|BATS|KRX|TYO):[A-Z0-9][A-Z0-9.\-]{0,15}',value) is not None


def _day(value):
    try: return isinstance(value,str) and date.fromisoformat(value).isoformat()==value
    except ValueError: return False


def _refs(value): return isinstance(value,list) and bool(value) and all(_text(v) for v in value)


def _mapping(code, record, meta):
    r=record or {}; reasons=[]
    day=meta['mapping_day'];cutoff=meta['input_cutoff']; valid=False
    if not r: reasons.append('MAPPING_NOT_PROVIDED')
    elif not _token(r.get('record_id')): reasons.append('MAPPING_RECORD_UNCONFIRMED')
    elif day is None or cutoff is None: reasons.append('MAPPING_TIME_UNCONFIRMED')
    elif not _day(r.get('valid_from')) or r['valid_from']>day or (
            r.get('valid_to') is not None and (not _day(r['valid_to']) or day>=r['valid_to'])):
        reasons.append('MAPPING_OUTSIDE_APPLICABLE_PERIOD')
    else:
        try: valid=timestamp(r['available_at'])<=timestamp(cutoff)
        except (KeyError,ValueError,TypeError,AttributeError): pass
        if not valid: reasons.append('MAPPING_UNAVAILABLE_AT_CUTOFF')
    issuer=r.get('issuer_id') if valid and r.get('issuer_status')=='VERIFIED' and _refs(r.get('issuer_refs')) and _token(r.get('issuer_id')) else None
    if issuer is None: reasons.append('ISSUER_LINK_UNCONFIRMED')
    kinds=IDENTIFIERS | ({'SYNTHETIC_FIXED_SECURITY_ID'} if meta['data_kind']=='SYNTHETIC' else set())
    security=(r.get('security_id') if issuer and r.get('security_status')=='VERIFIED' and
        _refs(r.get('security_refs')) and r.get('identifier_type') in kinds and
        _token(r.get('security_id')) and _token(r.get('share_class_id')) and
        r['security_id'] not in (issuer,code,code.split(':')[-1]) else None)
    if security is None: reasons.append('SECURITY_LINK_UNCONFIRMED')
    representative=security if security and r.get('representative_status')=='VERIFIED' and _refs(r.get('representative_refs')) else None
    if representative is None: reasons.append('REPRESENTATIVE_SECURITY_UNCONFIRMED')
    google=r.get('google_symbol') if security and r.get('google_status')=='VERIFIED' and _refs(r.get('google_refs')) and _google(r.get('google_symbol')) else None
    if google is None: reasons.append('GOOGLE_SYMBOL_UNCONFIRMED')
    return dict(company_id=code,code=code,issuer_id=issuer,
        issuer_status='VERIFIED' if issuer else 'UNCONFIRMED',security_id=security,
        security_status='VERIFIED' if security else 'UNCONFIRMED',
        representative_security_id=representative,
        representative_status='VERIFIED' if representative else 'UNCONFIRMED',
        requested_google_symbol=code,google_symbol=google,
        google_symbol_status='VERIFIED' if google else 'UNCONFIRMED',
        mapping_record_id=r.get('record_id') if valid else None,
        mapping_valid_from=r.get('valid_from') if valid else None,
        mapping_valid_to=r.get('valid_to') if valid else None,
        mapping_reasons=list(dict.fromkeys(reasons)))


def build_listing(source_bytes, *, metadata, links, expected_source_sha256, expected_links_hash):
    """Project already reviewed source data. This grants no publication approval.

    CURRENT_OFFICIAL is the current Universe504 only. A stored Top500 research
    selection remains CANDIDATE and cannot seed a new official user sheet.
    """
    _need(isinstance(source_bytes,bytes) and hashlib.sha256(source_bytes).hexdigest()==expected_source_sha256,'PUBLIC_LIST_SOURCE_HASH')
    _need(isinstance(links,list) and digest(links)==expected_links_hash,'PUBLIC_LIST_MAPPING_HASH')
    _need(isinstance(metadata,dict) and set(metadata)==META,'PUBLIC_LIST_METADATA')
    meta=deepcopy(metadata);kind=meta['source_kind']
    _need(kind in ('CURRENT_OFFICIAL','SYNTHETIC_CURRENT','TOP500_RESEARCH_CANDIDATE'),'PUBLIC_LIST_SOURCE_KIND')
    _need(meta['data_kind'] in ('PUBLIC_CODE_LIST','SYNTHETIC','RESEARCH_CANDIDATE') and _text(meta['population_id']),'PUBLIC_LIST_SCOPE')
    _need(isinstance(meta['null_reasons'],dict) and set(meta['null_reasons'])<=NULLABLE and
          all(v in NULL_CODES for v in meta['null_reasons'].values() if isinstance(v,str)) and
          all(isinstance(v,str) for v in meta['null_reasons'].values()) and
          all(meta[k] is None for k in meta['null_reasons']),'PUBLIC_LIST_NULL_REASONS')
    for field in ('population_version','basis_date','apply_at','mapping_day','input_cutoff'):
        if meta[field] is None: _need(_text(meta['null_reasons'].get(field)),'PUBLIC_LIST_UNKNOWN_METADATA_REASON')
    _need(meta['population_version'] is None or _text(meta['population_version']),'PUBLIC_LIST_VERSION')
    for field in ('basis_date','mapping_day'):
        _need(meta[field] is None or _day(meta[field]),'PUBLIC_LIST_DATE')
    for field in ('apply_at','input_cutoff'):
        if meta[field] is not None:
            try: timestamp(meta[field])
            except (ValueError,TypeError,AttributeError): raise ValueError('PUBLIC_LIST_TIME') from None
    source=json.loads(source_bytes);source_result_hash=None;selected=None
    if kind=='CURRENT_OFFICIAL':
        _need(meta['population_id']=='Universe504' and meta['data_kind']=='PUBLIC_CODE_LIST','CURRENT_OFFICIAL_POPULATION')
        universe_codes.require_universe_codes(source)
        codes=source['codes']
    elif kind=='SYNTHETIC_CURRENT':
        _need(meta['data_kind']=='SYNTHETIC' and meta['population_id'].startswith('SYNTHETIC:'),'SYNTHETIC_LIST_SCOPE')
        _need(source.get('schema')=='universe-codes/1' and set(source)=={'schema','codes'},'PUBLIC_LIST_CODE_SOURCE')
        codes=source['codes']
    else:
        view=top500_view(source)  # Existing hash validation and private allowlist; no selection run.
        _need(meta['data_kind'] in ('SYNTHETIC','RESEARCH_CANDIDATE'),'TOP500_LIST_SOURCE_SCOPE')
        _need(all(meta[k]==view[v] for k,v in [('population_id','population_id'),('population_version','population_version'),
            ('basis_date','evaluation_day'),('mapping_day','evaluation_day'),('apply_at','apply_at'),('input_cutoff','input_cutoff')]),'TOP500_LIST_SOURCE_CONTEXT')
        selected={r['issuer_id']:r['representative_security_id'] for r in view['members']}
        _need(len(selected)==len(view['members']),'TOP500_DUPLICATE_ISSUER')
        _need(len(links)==len(selected) and {r.get('issuer_id') for r in links}==set(selected),'TOP500_CODE_RELATION_INCOMPLETE')
        by_issuer={r['issuer_id']:r for r in links}
        codes=[by_issuer[r['issuer_id']]['company_id'] for r in view['members']]
        source_result_hash=view['source_result_hash']
    _need(isinstance(codes,list) and bool(codes) and len(codes)<=universe_codes.MAX_CODES and
          all(_text(c) and universe_codes._CODE.fullmatch(c) for c in codes),'PUBLIC_LIST_CODE_FORMAT')
    _need(len(codes)==len(set(codes)),'PUBLIC_LIST_DUPLICATE_CODE')
    by_code={}
    for row in links:
        _need(isinstance(row,dict) and row.get('company_id') in codes and row['company_id'] not in by_code,'PUBLIC_LIST_MAPPING_ROSTER')
        by_code[row['company_id']]=row
    members=[_mapping(code,by_code.get(code),meta) for code in codes]
    representatives={};google_symbols={}
    for row in members:
        if row['representative_security_id'] is not None:
            old=representatives.setdefault(row['issuer_id'],row['representative_security_id'])
            _need(old==row['representative_security_id'],'PUBLIC_LIST_REPRESENTATIVE_CONFLICT')
        if row['google_symbol'] is not None:
            old=google_symbols.setdefault(row['google_symbol'],row['security_id'])
            _need(old==row['security_id'],'PUBLIC_LIST_GOOGLE_SYMBOL_CONFLICT')
    if selected is not None:
        _need(all(r['issuer_id'] in selected and r['representative_security_id']==selected[r['issuer_id']] for r in members),'TOP500_CODE_RELATION_UNCONFIRMED')
    known={r['issuer_id'] for r in members if r['issuer_id'] is not None}
    official=kind=='CURRENT_OFFICIAL'
    out=dict(schema_version=SCHEMA,**meta,status='CANDIDATE' if selected is not None else 'CONFIRMED',
        official_current=official,use_for_new_sheet=official,
        public_publication_authorized=False,
        visibility='AUTHENTICATED_RESEARCH' if selected is not None else 'PUBLIC_CODE_METADATA_PROPOSAL',
        code_rows=len(codes),issuers=len(known) if all(r['issuer_id'] is not None for r in members) else None,
        known_issuers=len(known),issuer_count_reason=None if all(r['issuer_id'] is not None for r in members) else 'ISSUER_LINKS_INCOMPLETE',
        codes=deepcopy(codes),members=members,membership_unit='CODE_ROW',
        members_hash=digest(sorted(codes)),ordered_codes_hash=digest(codes),
        source_sha256=expected_source_sha256,source_result_hash=source_result_hash,
        mapping_input_hash=expected_links_hash,
        verified_google_mappings=sum(r['google_symbol_status']=='VERIFIED' for r in members),
        selection_is_not_qgv_rank=True,whole_market_denominator=None)
    out['list_hash']=digest(out)
    _need(len(json.dumps(out,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())+1<=MAX_BYTES,'PUBLIC_LIST_TOO_LARGE')
    return out


def _validated(listing, expected_hash):
    _need(isinstance(listing,dict) and listing.get('schema_version')==SCHEMA and
          listing.get('list_hash')==expected_hash==digest({k:v for k,v in listing.items() if k!='list_hash'}),'PUBLIC_LIST_HASH')


def sheet_difference(listing, sheet_codes, *, saved_identity, expected_listing_hash):
    """Review only. Prices, sheet IDs, Trades, Quotes and cells are not accepted."""
    _validated(listing,expected_listing_hash)
    _need(isinstance(sheet_codes,list) and all(_text(x) for x in sheet_codes),'SHEET_CODE_LIST')
    _need(len(sheet_codes)==len(set(sheet_codes)),'SHEET_DUPLICATE_CODE')
    current=listing['codes'];reasons=[]
    if listing['population_version'] is None: reasons.append('CURRENT_POPULATION_VERSION_UNRECORDED')
    if saved_identity is None: reasons.append('SHEET_POPULATION_IDENTITY_UNRECORDED')
    else:
        _need(isinstance(saved_identity,dict),'SHEET_POPULATION_IDENTITY')
        for field,reason in [('population_id','POPULATION_ID_MISMATCH'),('population_version','POPULATION_VERSION_MISMATCH')]:
            if saved_identity.get(field)!=listing[field]: reasons.append(reason)
        if saved_identity.get('members_hash')!=digest(sorted(sheet_codes)): reasons.append('SHEET_MEMBERS_HASH_MISMATCH')
    added=[c for c in current if c not in set(sheet_codes)]
    removed=[c for c in sheet_codes if c not in set(current)]
    if added or removed: reasons.append('SHEET_LIST_OUTDATED_OR_DIFFERENT')
    elif sheet_codes!=current: reasons.append('SHEET_ORDER_DIFFERS')
    unversioned={'SHEET_POPULATION_IDENTITY_UNRECORDED','CURRENT_POPULATION_VERSION_UNRECORDED'}
    state='UNVERSIONED_LIST_MATCH' if reasons and set(reasons)<=unversioned and sheet_codes==current else 'CURRENT' if not reasons else 'REVIEW_REQUIRED'
    return dict(schema_version='sheet-population-review/1',state=state,reasons=reasons,
        expected_listing_hash=expected_listing_hash,added_codes=added,removed_codes=removed,
        old_code_rows=len(sheet_codes),current_code_rows=len(current),
        action='USER_SELECTED_UPDATE_ONLY',writes=0,touches_trades_or_quotes=False)


def retain_listing(previous, *, expected_previous_hash, failure):
    """Caller selects the trusted previous object; no filesystem or publishing here."""
    _validated(previous,expected_previous_hash)
    _need(previous.get('status')=='CONFIRMED','PREVIOUS_CONFIRMED_LIST_REQUIRED')
    _need(failure in ('SOURCE_READ_FAILED','SOURCE_INVALID','MAPPING_INVALID','PUBLIC_LIST_TOO_LARGE'),'PUBLIC_LIST_FAILURE_STATE')
    return dict(schema_version='population-list-response/1',status='RETAINED_PREVIOUS',
                failure=failure,listing=deepcopy(previous),retained_listing_hash=expected_previous_hash)
