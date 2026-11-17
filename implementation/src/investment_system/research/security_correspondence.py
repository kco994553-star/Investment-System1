"""Offline, claim-specific SEC class/venue -> provider correspondence.

Reuses the held SEC cover parser. No shares/price arithmetic, network, security-ID
assignment, validity interpolation, verification promotion or Top500 selection.
"""
from copy import deepcopy
from datetime import date
import hashlib,json,re
import xml.etree.ElementTree as ET
from ..providers.sec_cover_shares import parse_cover,CLASS_AXIS,VENUE_AXES

SCHEMA='security-correspondence/1'
RULE_VERSION='sec-cover-kis-document-match/0.1.0'
VENUES={
 'NASDAQ':{'NASDAQ','The Nasdaq Stock Market LLC','Nasdaq Global Select Market','Nasdaq Global Market','Nasdaq Capital Market','NASDAQ Global Select Market','NASDAQ Global Market','NASDAQ Capital Market','Nasdaq Stock Market LLC','Nasdaq','NASDAQMember','NasdaqMember','NasdaqStockMarketLLCMember','NasdaqGlobalSelectMarketMember','NasdaqGlobalMarketMember','NasdaqCapitalMarketMember'},
 'NYSE':{'NYSE','New York Stock Exchange','New York Stock Exchange LLC','NYSEMember','NewYorkStockExchangeMember','XNYS'},
 'NYSE_AMERICAN':{'NYSE American','NYSE American LLC','NYSEAmericanMember','NYSEAmericanLLCMember'},
 'NYSE_TEXAS':{'NYSETX','NYSE Texas','NYSE Texas, Inc.','NYSETexasMember','NYSEChicagoMember','XCHI'},
 'CBOE_BZX':{'Cboe BZX Exchange','Cboe BZX Exchange, Inc.','CBOEBZXExchangeMember','CboeBZXExchangeMember'},
}
PROVIDER_VENUES={'NAS':'NASDAQ','NYS':'NYSE','AMS':'NYSE_AMERICAN'}
def _local(value):return value.rsplit('}',1)[-1].rsplit(':',1)[-1]
def _hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def _venue(text):
 # Case/spacing policy only applies to institution names, never symbols/classes.
 value=' '.join(text.split()).casefold()
 return next((key for key,names in VENUES.items() if value in {' '.join(n.split()).casefold() for n in names}),None)

def _symbol_literal_match(reported, symbol):
 if reported==symbol:return True
 if reported in ('“'+symbol+'”','"'+symbol+'"',"'"+symbol+"'"):return True
 # A syntactic exchange suffix is allowed only when the institution is known;
 # the cover's independent exchange fact is still required and checked below.
 return bool(re.fullmatch(re.escape(symbol)+r' \((?:NYSE|NASDAQ)\)',reported))


def cover_observations(body,*,expected_sha256,source):
 if hashlib.sha256(body).hexdigest()!=expected_sha256:raise ValueError('SEC_SOURCE_HASH_MISMATCH')
 parsed=parse_cover(body) # Existing normalizer; shares are deliberately not emitted or used.
 root=ET.fromstring(body);contexts={}
 for e in root.iter():
  if _local(e.tag)!='context':continue
  classes=[];venues=[];unknown=[];identifiers=[];period={}
  for x in e.iter():
   name=_local(x.tag);text=(x.text or '').strip()
   if name in ('explicitMember','typedMember'):
    dim=_local(x.get('dimension',''))
    if dim==CLASS_AXIS:classes.append(text)
    elif dim in VENUE_AXES:venues.append(text)
    else:unknown.append(dim)
   elif name=='identifier':identifiers.append(text.zfill(10))
   elif name in ('instant','startDate','endDate'):period[name]=text
  if unknown or len(classes)>1 or len(set(identifiers))!=1:continue
  contexts[e.get('id')]=dict(issuer_id=identifiers[0],member=classes[0] if classes else None,
    venue_members=venues,period=period)
 facts=[]
 for e in root.iter():
  if not re.fullmatch(r'\{https?://xbrl\.sec\.gov/dei/[^}]+\}(TradingSymbol|Security12bTitle|SecurityExchangeName)',e.tag):continue
  context=contexts.get(e.get('contextRef'))
  if context is None:continue
  text=(e.text or '').strip()
  if not text:continue
  facts.append(dict(name=_local(e.tag),value=text,context_id=e.get('contextRef'),**deepcopy(context)))
 return dict(source={**deepcopy(source),'sha256':expected_sha256},facts=facts,
             reused_parser_class_members=sorted(str(m) for m in parsed['symbols']),
             security_id=None)

def correspondence(company_id,issuer_id,document,provider,*,evaluation_day,known_conflicts=(),symbol_transitions=()):
 date.fromisoformat(evaluation_day)
 reasons=[];source=deepcopy(document.get('source',{})) if document else {}
 result=dict(schema_version=SCHEMA,rule_version=RULE_VERSION,company_id=company_id,issuer_id=issuer_id,
  security_id=None,class_observation_id=None,class_member=None,security_title=None,security_kind=None,
  sec_symbol=None,sec_exchanges=[],provider=deepcopy(provider),sec=source,
  valid_from=None,valid_to=None,validity_basis='NOT_PROVEN_BY_REPORT_CONTEXT_OR_FILING_DATE',
  evaluation_day=evaluation_day,evaluation_status='VALIDITY_UNCONFIRMED',
  document_status='UNCONFIRMED',reasons=reasons,verification='UNVERIFIED_REFERENCE',
  price_adjusted=False,top500_identity_status='UNVERIFIED',scope='DOCUMENT_CORRESPONDENCE_NOT_TRADING_ELIGIBILITY')
 if not document:reasons.append('SEC_COVER_NOT_HELD')
 if document and source.get('issuer_id')!=issuer_id:reasons.append('SEC_ISSUER_CONFLICT')
 if document and not source.get('filing_date'):reasons.append('SEC_FILING_DATE_UNKNOWN')
 elif source.get('filing_date') and source['filing_date']>evaluation_day:reasons.append('SEC_FILING_AFTER_EVALUATION')
 if provider is None:reasons.append('KIS_RESPONSE_MISSING')
 else:
  expected='D'+str(provider.get('excd'))+str(provider.get('symb'))
  if provider.get('returned_symbol')!=expected:reasons.append('KIS_RETURNED_SYMBOL_CONFLICT')
  if provider.get('excd') not in PROVIDER_VENUES:reasons.append('KIS_VENUE_UNKNOWN')
 if not document:
  if known_conflicts:reasons.append('KNOWN_DATED_IDENTITY_CONFLICT');result['known_identity_conflicts']=deepcopy(known_conflicts)
  result['reasons']=sorted(set(reasons));return result
 symbol=company_id.split(':',1)[1]
 facts=(document or {}).get('facts',[])
 eligible_transitions=[e for e in symbol_transitions if e.get('issuer_id')==issuer_id and e.get('new_symbol')==symbol and e.get('cover_sha256')==source.get('sha256') and e.get('effective_day') and e['effective_day']<=evaluation_day and e.get('status')=='REVIEWED_IDENTITY_STATEMENT' and re.fullmatch('[0-9a-f]{64}',e.get('event_source_sha256','')) and e.get('document_location')]
 matches=[f for f in facts if f['name']=='TradingSymbol' and (_symbol_literal_match(f['value'],symbol) or any(e.get('old_symbol')==f['value'] for e in eligible_transitions)) and f['issuer_id']==issuer_id]
 if not matches:reasons.append('SEC_SYMBOL_UNCONFIRMED')
 candidates=[]
 for m in matches:
  # Same issuer, class and report context. A context period is not a security-validity interval.
  compatible=[f for f in facts if f['issuer_id']==issuer_id and f['member']==m['member'] and f['period']==m['period']]
  titles={f['value'] for f in compatible if f['name']=='Security12bTitle'}
  if len(titles)!=1:continue
  if not _symbol_literal_match(m['value'],symbol):
   edges=[e for e in eligible_transitions if e.get('old_symbol')==m['value'] and e.get('class_title')==next(iter(titles))]
   if not edges:continue
   result['symbol_transition_evidence']=deepcopy(edges)
  # The Universe lookup is a stock-price endpoint; explicitly registered debt,
  # preferred and warrants are not alternative common classes for that quote.
  if re.search(r'\bnotes?\b|\bbonds?\b|debentures?|warrants?|preferred',next(iter(titles)),re.I):continue
  raw_exchanges={f['value'] for f in compatible if f['name']=='SecurityExchangeName'}
  raw_exchanges.update(_local(v) for v in m['venue_members'])
  # A unique undimensioned venue on the same report can describe a listed class;
  # never carry a class-specific venue from a different class.
  if not raw_exchanges and m['member'] is not None:
   raw_exchanges={f['value'] for f in facts if f['name']=='SecurityExchangeName' and f['member'] is None and f['period']==m['period'] and f['issuer_id']==issuer_id}
  exchanges={_venue(x) for x in raw_exchanges};exchanges.discard(None)
  suffix=re.fullmatch(re.escape(symbol)+r' \((NYSE|NASDAQ)\)',m['value'])
  if suffix and _venue(suffix.group(1)) not in exchanges:reasons.append('SEC_SYMBOL_VENUE_DECORATION_CONFLICT')
  candidates.append(dict(member=m['member'],title=next(iter(titles)),reported_symbols=[m['value']],exchanges=sorted(exchanges),
   exchange_reported=sorted(raw_exchanges),context_ids=sorted({f['context_id'] for f in compatible}),period=m['period']))
 unique={}
 for candidate in candidates:
  key=_hash([candidate['member'],candidate['title']])
  if key not in unique:
   unique[key]=deepcopy(candidate);unique[key]['periods']=[candidate['period']]
  else:
   prior=unique[key]
   for field in ('exchanges','exchange_reported','context_ids','reported_symbols'):prior[field]=sorted(set(prior[field]+candidate[field]))
   if candidate['period'] not in prior['periods']:prior['periods'].append(candidate['period'])
 # Periods are distinct observations, never interpolated into effective validity.
 if not candidates:reasons.append('SEC_CLASS_UNCONFIRMED')
 elif len(unique)!=1:reasons.append('SEC_CLASS_AMBIGUOUS')
 else:
  c=next(iter(unique.values()));result.update(class_member=c['member'],security_title=c['title'],sec_symbol=symbol,
      sec_exchanges=c['exchanges'],class_evidence=c)
  title=c['title'].casefold()
  result['security_kind']=('ADR' if re.search(r'depositary|\badr\b',title) else
   'COMMON_STOCK' if re.search(r'common\s+(stock|shares)',title) else
   'ORDINARY_SHARE' if re.search(r'ordinary\s+shares',title) else 'UNKNOWN')
  result['class_observation_id']='SEC_CLASS_OBSERVATION:'+_hash([issuer_id,source.get('sha256'),c['member'],c['title'],symbol])
  if not c['exchanges']:reasons.append('SEC_EXCHANGE_UNCONFIRMED')
  elif provider and PROVIDER_VENUES.get(provider.get('excd')) not in c['exchanges']:reasons.append('SEC_KIS_EXCHANGE_CONFLICT')
 if known_conflicts:
  reasons.append('KNOWN_DATED_IDENTITY_CONFLICT');result['known_identity_conflicts']=deepcopy(known_conflicts)
 if not reasons:result['document_status']='CONFIRMED'
 result['reasons']=sorted(set(reasons))
 return result


def top500_class_candidate(row):
 """Field-compatible evidence candidate, never an identity/eligibility promotion."""
 return {k:deepcopy(row.get(k)) for k in ('issuer_id','security_id','security_kind','valid_from','valid_to')} | {
  'identity_status':'UNVERIFIED','identity_evidence':deepcopy(row.get('sec')),
  'economic_class_id':None,'class_observation_id':row.get('class_observation_id'),
  'source_company_id':row['company_id'],'class_member':row.get('class_member'),
  'security_title':row.get('security_title'),'exchanges':row.get('sec_exchanges'),
  'exchange':PROVIDER_VENUES.get((row.get('provider') or {}).get('excd')) if row['document_status']=='CONFIRMED' else None,
  'exchange_basis':'MATCHED_QUERY_VENUE_NOT_REPRESENTATIVE_LISTING',
  'symbol_transition_evidence':deepcopy(row.get('symbol_transition_evidence',[])),
  'price':None,'shares':None,'corporate_action_status':'NOT_EVALUATED',
  'representative_security_status':'NOT_DECIDED','mapping_status':row['document_status']}
