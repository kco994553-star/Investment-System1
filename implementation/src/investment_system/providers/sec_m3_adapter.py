"""Supplied SEC identity/cover evidence -> M3. No network, prices or selection.

An undimensioned share count is not proof of a security's economic basis.
Confirmation requires the same filing's cover symbol, title, shares unit/date
and issuer. Class mismatches are annotations; no counts are corrected.
"""
from dataclasses import dataclass, asdict, field, replace
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET

from ..markets.us import US_LISTINGS
from ..universe.private_subset import ListingSeed, SecReceipt, ShareBasisReceipt, prepare_sec_shares

XBRLI='http://www.xbrl.org/2003/instance'
XBRLDI='http://xbrl.org/2006/xbrldi'

@dataclass(frozen=True)
class SecM3Input:
    state: str
    reason_codes: tuple[str,...]
    code: str | None = field(default=None,repr=False)
    seed: ListingSeed | None = field(default=None,repr=False)
    receipt: SecReceipt | None = field(default=None,repr=False)
    basis: ShareBasisReceipt | None = field(default=None,repr=False)
    shares: object = field(default=None,repr=False)

def _aware(d):
    return isinstance(d,datetime) and d.tzinfo is not None and d.utcoffset() is not None

def _cik(x):
    if type(x) not in (str,int) or not re.fullmatch(r'[0-9]{1,10}',str(x)) or int(x)<=0:
        raise ValueError('INVALID_INPUT')
    return str(x).zfill(10)

def _pairs(items):
    d={}
    for k,v in items:
        if k in d:raise ValueError('INVALID_INPUT')
        d[k]=v
    return d

def _json(b):
    if type(b) is not bytes or len(b)>8388608:raise ValueError('INVALID_INPUT')
    def reject(_):raise ValueError('INVALID_INPUT')
    d=json.loads(b,object_pairs_hook=_pairs,parse_constant=reject)
    if type(d) is not dict:raise ValueError('INVALID_INPUT')
    return d

def _cover(xml,cik,symbol,cutoff,report_period_end=None,venue=None):
    from io import BytesIO
    from datetime import date
    if type(xml) is not bytes or len(xml)>8388608 or b'\x00' in xml or re.search(br'<!\s*(DOCTYPE|ENTITY)',xml,re.I):
        raise ValueError('COVER_UNCONFIRMED')
    pending={};stack=[];qnames={};count=0
    parser=ET.iterparse(BytesIO(xml),events=('start-ns','start','end'))
    for event,item in parser:
        if event=='start-ns':pending[item[0]]=item[1];continue
        if event=='start':
            env=dict(stack[-1]) if stack else {};env.update(pending);pending={};stack.append(env)
            count+=1
            if len(stack)>128 or count>200000:raise ValueError('COVER_UNCONFIRMED')
            if item.tag in ('{'+XBRLI+'}measure','{'+XBRLDI+'}explicitMember'):qnames[id(item)]=env
        else:stack.pop()
    root=parser.root
    if root.tag!='{'+XBRLI+'}xbrl':raise ValueError('COVER_UNCONFIRMED')
    def qname(e,text):
        text=text.strip();parts=text.split(':')
        if len(parts)>2:return None
        prefix,local=parts if len(parts)==2 else ('',parts[0])
        uri=qnames.get(id(e),{}).get(prefix)
        return (uri,local) if uri and local else None
    contexts={};seen=set();units={}
    for e in root.findall('{'+XBRLI+'}context'):
        id_=e.get('id')
        if not id_ or id_ in seen:raise ValueError('COVER_UNCONFIRMED')
        seen.add(id_)
        identifiers=e.findall('.//{'+XBRLI+'}identifier')
        days=e.findall('.//{'+XBRLI+'}instant')+e.findall('.//{'+XBRLI+'}endDate')
        if len(identifiers)!=1 or len(days)!=1:continue
        if identifiers[0].get('scheme') not in ('http://www.sec.gov/CIK','https://www.sec.gov/CIK'):continue
        if _cik((identifiers[0].text or '').strip())!=cik:continue
        day=(days[0].text or '').strip()
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day) or date.fromisoformat(day)>cutoff.date():continue
        if e.findall('.//{'+XBRLDI+'}typedMember'):continue
        classes=[];venues=[];bad=False
        for m in e.findall('.//{'+XBRLDI+'}explicitMember'):
            axis=qname(m,m.get('dimension') or '');value=qname(m,m.text or '')
            if axis is None or value is None:bad=True;break
            if axis[1]=='StatementClassOfStockAxis' and re.fullmatch(r'https?://(?:fasb\.org/us-gaap|xbrl\.us/us-gaap)/.+',axis[0]):classes.append(value)
            elif axis[1]=='EntityListingsExchangeAxis' and re.fullmatch(r'https?://xbrl\.sec\.gov/dei/.+',axis[0]):venues.append(value)
            else:bad=True;break
        if bad or len(classes)>1:continue
        contexts[id_]=(classes[0] if classes else None,day,tuple(sorted(venues)))
    for u in root.findall('{'+XBRLI+'}unit'):
        id_=u.get('id')
        if not id_ or id_ in units:raise ValueError('COVER_UNCONFIRMED')
        measures=u.findall('{'+XBRLI+'}measure')
        units[id_]=len(list(u))==1 and len(measures)==1 and qname(measures[0],measures[0].text or '')==(XBRLI,'shares')
    rows=[];symbols={};titles={}
    for e in root:
        if not re.fullmatch(r'\{https?://xbrl\.sec\.gov/dei/\d{4}(?:-\d{2}-\d{2})?\}(EntityCommonStockSharesOutstanding|TradingSymbol|Security12bTitle)',e.tag):continue
        ctxid=e.get('contextRef');ctx=contexts.get(ctxid)
        if ctx is None:continue
        name=e.tag.split('}')[-1];text=(e.text or '').strip()
        if name=='TradingSymbol':symbols.setdefault(ctxid,set()).add(text)
        elif name=='Security12bTitle':titles.setdefault(ctxid,set()).add(text)
        else:
            if not units.get(e.get('unitRef')) or e.get('scale') not in (None,'0') or e.get('{http://www.w3.org/2001/XMLSchema-instance}nil')=='true':continue
            try:value=float(text)
            except ValueError:continue
            if math.isfinite(value) and value>0:rows.append((ctxid,ctx,value))
    hits=[]
    for id_,ctx,value in rows:
        member,day,venues=ctx
        compatible={id_}|{i for i,(m,d,v) in contexts.items() if report_period_end is not None and d==report_period_end and m==member and v==venues}
        syms=set().union(*(symbols.get(i,set()) for i in compatible));labels=set().union(*(titles.get(i,set()) for i in compatible))
        if syms!={symbol}:continue
        allowed={'NASDAQ':{'nasdaqmember','nasdaqstockmarketllcmember','nasdaqglobalselectmarketmember','nasdaqglobalmarketmember','nasdaqcapitalmarketmember'},'NYSE':{'nysemember','newyorkstockexchangemember'}}
        if any(v[1].casefold() not in allowed.get(venue,set()) for v in venues):raise ValueError('COVER_UNCONFIRMED')
        if not labels or any(re.search(r'depositary|\bADR\b|preferred|warrant|note|unit',t,re.I) for t in labels):raise ValueError('BASIS_UNCONFIRMED')
        if not all(re.search(r'common\s+stock|ordinary\s+shares',t,re.I) for t in labels):raise ValueError('BASIS_UNCONFIRMED')
        hits.append((member,day,venues,value))
    if not hits:raise ValueError('COVER_UNCONFIRMED')
    latest=max(r[1] for r in hits);hits=set(r for r in hits if r[1]==latest)
    if len(hits)!=1:raise ValueError('COVER_UNCONFIRMED')
    member,day,venues,value=next(iter(hits))
    same_day=[(ctx,v) for _,ctx,v in rows if ctx[1]==day and ctx[2]==venues]
    multi=len({ctx[0] for _,ctx,_ in rows})>1
    explicit_totals=tuple(v for ctx,v in same_day if ctx[0] is None)
    return value,day,multi,member is not None,explicit_totals

def build_sec_m3_input(*,code,companyfacts_body,submissions_body,acquired_at,as_of,synthetic=False,cover_xml=None,cover_accession=None,cover_acquired_at=None):
    seed=receipt=basis=shares=None
    def fail(reason):
        nonlocal basis,shares
        if basis is not None and reason!='SHARE_CLASS_BASIS':basis=replace(basis,basis_status='UNKNOWN',share_class_basis='UNKNOWN')
        if reason!='SHARE_CLASS_BASIS':shares=None
        return SecM3Input('NOT_AVAILABLE',(reason,),code if type(code) is str else None,seed,receipt,basis,shares)
    try:
        if type(synthetic) is not bool:return fail('INVALID_INPUT')
        if not _aware(acquired_at) or not _aware(as_of):return fail('INVALID_TIMESTAMP')
        captured=acquired_at.astimezone(timezone.utc);cut=as_of.astimezone(timezone.utc)
        if captured>cut:return fail('AVAILABLE_AFTER_AS_OF')
        if type(code) is not str or not re.fullmatch(r'(NASDAQ|NYSE):[A-Z0-9][A-Z0-9.\-]*',code):return fail('IDENTITY_UNCONFIRMED')
        venue,symbol=code.split(':');mic={'NASDAQ':'XNAS','NYSE':'XNYS'}[venue]
        facts=_json(companyfacts_body);sub=_json(submissions_body);cik=_cik(sub.get('cik'))
        if _cik(facts.get('cik'))!=cik:return fail('CIK_MISMATCH')
        tickers=sub.get('tickers');exchanges=sub.get('exchanges')
        if type(tickers) is not list or type(exchanges) is not list or len(tickers)!=len(exchanges):return fail('IDENTITY_UNCONFIRMED')
        matches=[i for i,t in enumerate(tickers) if t==symbol]
        if len(matches)!=1 or type(exchanges[matches[0]]) is not str or exchanges[matches[0]].upper()!=venue:return fail('IDENTITY_UNCONFIRMED')
        sha=lambda b:hashlib.sha256(b).hexdigest()
        company=next((cid for cid,v in US_LISTINGS.items() if v['cik']==cik and v['yahoo']==symbol),'sec_'+cik)
        listing=f'{mic}:{symbol}:{cik}';security=f'sec:{cik}:{symbol}'
        seed=ListingSeed(listing,company,'sec:'+cik,security,symbol,mic,'USD','America/New_York',code,cik,captured.date(),None,'sec-submissions:'+cik,sha(submissions_body),synthetic)
        receipt=SecReceipt(cik,companyfacts_body,submissions_body,captured,sha(companyfacts_body),sha(submissions_body),synthetic)
        if cover_xml is None:return fail('BASIS_UNCONFIRMED')
        if not _aware(cover_acquired_at):return fail('INVALID_TIMESTAMP')
        cover_at=cover_acquired_at.astimezone(timezone.utc)
        if cover_at>cut:return fail('AVAILABLE_AFTER_AS_OF')
        if type(cover_accession) is not str or not re.fullmatch(r'\d{10}-\d{2}-\d{6}',cover_accession):return fail('ACCESSION_UNCONFIRMED')
        recent=sub.get('filings',{}).get('recent',{})
        accns=recent.get('accessionNumber',[])
        report_period_end=None
        if type(accns) is list and accns.count(cover_accession)==1:
            index=accns.index(cover_accession);reports=recent.get('reportDate',[])
            if type(reports) is list and len(reports)==len(accns):report_period_end=reports[index]
        expected,measurement,multi,dimensioned,explicit_totals=_cover(cover_xml,cik,symbol,min(captured,cover_at),report_period_end,venue)
        basis=ShareBasisReceipt(listing,company,security,'SINGLE_CLASS_CONFIRMED',f'sec-cover:{cik}/{cover_accession}',sha(cover_xml),max(captured,cover_at),'shares','GOOGLEFINANCE_CURRENT','USD',synthetic,'ALIGNED')
        shares=prepare_sec_shares(seed,receipt,basis,cut)
        if shares.state!='INPUT_RESEARCH':return fail(shares.reason_codes[0])
        if shares.accn!=cover_accession:return fail('ACCESSION_UNCONFIRMED')
        index=accns.index(cover_accession)
        accepted=datetime.fromisoformat(recent['acceptanceDateTime'][index].replace('Z','+00:00')).astimezone(timezone.utc)
        if cover_at<accepted:return fail('INVALID_TIME_ORDER')
        if shares.measurement_date.isoformat()!=measurement:return fail('COVER_UNCONFIRMED')
        if shares.shares!=expected:
            if not (multi and dimensioned and set(explicit_totals)=={shares.shares}):return fail('COVER_FACT_MISMATCH')
            basis=replace(basis,basis_status='UNKNOWN',share_class_basis='DIFFERENT')
            shares=prepare_sec_shares(seed,receipt,basis,cut)
            return fail('SHARE_CLASS_BASIS')
        if multi:return fail('MULTI_CLASS_AMBIGUOUS')
        return SecM3Input('INPUT_RESEARCH',(),code,seed,receipt,basis,shares)
    except ValueError as error:
        reason=str(error)
        return fail(reason if reason in ('COVER_UNCONFIRMED','BASIS_UNCONFIRMED','INVALID_INPUT') else 'COVER_UNCONFIRMED')
    except (TypeError,KeyError,OverflowError,ET.ParseError,RecursionError):return fail('COVER_UNCONFIRMED' if cover_xml is not None and seed is not None else 'INVALID_INPUT')

def public_sec_input_json(result):
    """Whitelist projection, not publication. Repacked bytes get NEW hashes.

    JS loadInputs must TextEncoder the text fields into Uint8Array bodies.
    Only identity and outstanding-share concepts/filing join columns survive.
    Original full SEC payloads and every price/marketcap/unknown field stay out.
    """
    if not isinstance(result,SecM3Input):raise ValueError('INVALID_INPUT')
    out={'identityLookup':{},'secByListing':{},'basisByListing':{},'state':result.state,'reason_codes':list(result.reason_codes)}
    if result.seed is None or result.receipt is None:return out
    seed=result.seed;receipt=result.receipt;facts=_json(receipt.companyfacts_body);sub=_json(receipt.submissions_body)
    safe_facts={'cik':receipt.cik,'facts':{}}
    for tax,concept in (('dei','EntityCommonStockSharesOutstanding'),('us-gaap','CommonStockSharesOutstanding')):
        obj=facts.get('facts',{})
        for key in (tax,concept,'units'):
            obj=obj.get(key,{}) if type(obj) is dict else {}
        rows=obj.get('shares',[]) if type(obj) is dict else []
        if type(rows) is not list:rows=[]
        clean=[]
        for r in rows:
            if type(r) is not dict:continue
            if type(r.get('val')) not in (int,float) or not math.isfinite(r['val']) or r['val']<=0:continue
            if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',str(r.get('accn',''))):continue
            if r.get('form') not in ('10-K','10-K/A','10-Q','10-Q/A','20-F','20-F/A','40-F','6-K'):continue
            if any(not re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(r.get(k,''))) for k in ('filed','end')):continue
            clean.append({k:r[k] for k in ('val','end','filed','form','accn')})
        safe_facts['facts'].setdefault(tax,{})[concept]={'units':{'shares':clean}}
    recent=sub.get('filings',{}).get('recent',{})
    cols=('accessionNumber','form','filingDate','acceptanceDateTime')
    safe_recent={k:[] for k in cols}
    columns=[recent.get(k,[]) for k in cols]
    if all(type(c) is list for c in columns) and len({len(c) for c in columns})==1:
        for accn,form,filed,accepted in zip(*columns):
            if type(accn) is not str or not re.fullmatch(r'\d{10}-\d{2}-\d{6}',accn) or form not in ('10-K','10-K/A','10-Q','10-Q/A','20-F','20-F/A','40-F','6-K'):continue
            if type(filed) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',filed):continue
            if type(accepted) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})',accepted):continue
            for k,v in zip(cols,(accn,form,filed,accepted)):safe_recent[k].append(v)
    safe_sub={'cik':receipt.cik,'tickers':[seed.symbol],'exchanges':['NASDAQ' if seed.mic=='XNAS' else 'NYSE'],'filings':{'recent':safe_recent}}
    encode=lambda x:json.dumps(x,separators=(',',':'),allow_nan=False).encode()
    fb,sb=encode(safe_facts),encode(safe_sub)
    def convert(x):
        d=asdict(x)
        for k,v in d.items():
            if hasattr(v,'isoformat'):d[k]=v.isoformat()
        return d
    out['identityLookup'][result.code]=convert(seed)
    out['secByListing'][seed.listing_id]={'cik':receipt.cik,'companyfacts_text':fb.decode(),'submissions_text':sb.decode(),'acquired_at':receipt.acquired_at.isoformat(),'facts_sha256':hashlib.sha256(fb).hexdigest(),'submissions_sha256':hashlib.sha256(sb).hexdigest(),'origin_facts_sha256':receipt.facts_sha256,'origin_submissions_sha256':receipt.submissions_sha256,'synthetic':receipt.synthetic,'projection':'SEC_PUBLIC_SHARES_ONLY_V1'}
    if result.basis is not None:out['basisByListing'][seed.listing_id]=convert(result.basis)
    return out
