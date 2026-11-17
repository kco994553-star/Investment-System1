from copy import deepcopy
import hashlib,importlib
import pytest

XML=b'''<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:dei="http://xbrl.sec.gov/dei/2026" xmlns:xbrldi="http://xbrl.org/2006/xbrldi"><context id="c"><entity><identifier>0000000001</identifier><segment><xbrldi:explicitMember dimension="us-gaap:StatementClassOfStockAxis">test:ClassAMember</xbrldi:explicitMember></segment></entity><period><startDate>2026-01-01</startDate><endDate>2026-09-30</endDate></period></context><dei:TradingSymbol contextRef="c">SYN</dei:TradingSymbol><dei:Security12bTitle contextRef="c">Class A Common Stock</dei:Security12bTitle><dei:SecurityExchangeName contextRef="c">NASDAQ</dei:SecurityExchangeName></xbrl>'''

def module():return importlib.import_module('investment_system.research.security_correspondence')
def doc(body=XML):return module().cover_observations(body,expected_sha256=hashlib.sha256(body).hexdigest(),source={'issuer_id':'0000000001','filing_date':'2026-10-28','accession':'SYNTHETIC','acquired_at':'2026-10-29T00:00:00Z','locator':'SYNTHETIC'})
def call(d=None,code='NASDAQ:SYN',link=None):return module().correspondence(code,'0000000001',d or doc(),link or {'symb':'SYN','excd':'NAS','returned_symbol':'DNASSYN'},evaluation_day='2026-11-13')

def test_document_match_is_not_effective_interval_or_verification():
 r=call();assert r['document_status']=='CONFIRMED'
 assert r['evaluation_status']=='VALIDITY_UNCONFIRMED'
 assert r['security_id'] is None and r['valid_from'] is None and r['valid_to'] is None
 assert r['security_title']=='Class A Common Stock' and r['issuer_id']=='0000000001'
 assert r['verification']=='UNVERIFIED_REFERENCE' and r['price_adjusted'] is False
 assert r['sec']['filing_date']!='2026-11-13'

@pytest.mark.parametrize('change,reason',[('venue','SEC_KIS_EXCHANGE_CONFLICT'),('ticker','SEC_SYMBOL_UNCONFIRMED'),('kind','SEC_CLASS_UNCONFIRMED'),('response','KIS_RETURNED_SYMBOL_CONFLICT')])
def test_conflicts_are_not_filled(change,reason):
 body=XML;link={'symb':'SYN','excd':'NAS','returned_symbol':'DNASSYN'}
 if change=='venue':body=body.replace(b'>NASDAQ<',b'>NYSE<')
 if change=='ticker':body=body.replace(b'>SYN<',b'>OTHER<')
 if change=='kind':body=body.replace(b'Class A Common Stock',b'')
 if change=='response':link['returned_symbol']='DNASOTHER'
 r=call(doc(body),link=link);assert r['document_status']=='UNCONFIRMED' and reason in r['reasons']

def test_distinct_classes_not_merged_by_issuer():
 b=XML.replace(b'</xbrl>',b'<dei:Security12bTitle contextRef="c">Class B Common Stock</dei:Security12bTitle></xbrl>')
 assert call(doc(b))['document_status']=='UNCONFIRMED'

def test_hash_and_cik_checked():
 with pytest.raises(ValueError,match='SOURCE_HASH'):module().cover_observations(XML,expected_sha256='0'*64,source={})
 d=doc();d['source']['issuer_id']='0000000002';assert call(d)['document_status']=='UNCONFIRMED'

def test_future_document_not_backdated():
 d=doc();d['source']['filing_date']='2026-11-14';r=call(d);assert 'SEC_FILING_AFTER_EVALUATION' in r['reasons']

def test_missing_response_preserves_sec_observation():
 r=module().correspondence('NASDAQ:SYN','0000000001',doc(),None,evaluation_day='2026-11-13');assert r['document_status']=='UNCONFIRMED' and 'KIS_RESPONSE_MISSING' in r['reasons']

def test_no_automatic_separator_alias():
 assert 'SEC_SYMBOL_UNCONFIRMED' in call(code='NASDAQ:SYN-A')['reasons']


def test_multiple_venues_of_same_class_are_not_multiple_classes():
 extra=XML.decode().split('<xbrl',1)[1].split('>',1)[1].rsplit('</xbrl>',1)[0].replace('id="c"','id="d"').replace('contextRef="c"','contextRef="d"').replace('>NASDAQ<','>NYSE<')
 b=XML.replace(b'</xbrl>',extra.encode()+b'</xbrl>')
 r=call(doc(b));assert r['document_status']=='CONFIRMED' and r['sec_exchanges']==['NASDAQ','NYSE']


def test_registered_debt_with_same_symbol_does_not_become_common_class():
 extra=XML.decode().split('<xbrl',1)[1].split('>',1)[1].rsplit('</xbrl>',1)[0].replace('id="c"','id="d"').replace('contextRef="c"','contextRef="d"').replace('ClassAMember','NotesMember').replace('Class A Common Stock','3.125% Notes due 2028')
 b=XML.replace(b'</xbrl>',extra.encode()+b'</xbrl>')
 r=call(doc(b));assert r['document_status']=='CONFIRMED' and r['security_title']=='Class A Common Stock'

@pytest.mark.parametrize('reported',[b'\xe2\x80\x9cSYN\xe2\x80\x9d',b'SYN (NASDAQ)'])
def test_only_literal_symbol_decoration_is_removed_and_retained(reported):
 b=XML.replace(b'>SYN<',b'>'+reported+b'<');r=call(doc(b))
 assert r['document_status']=='CONFIRMED'
 assert reported.decode() in r['class_evidence']['reported_symbols']


def test_explicit_dated_symbol_transition_preserves_old_symbol_and_no_validity_claim():
 d=doc();edge=dict(issuer_id='0000000001',old_symbol='SYN',new_symbol='NEW',class_title='Class A Common Stock',cover_sha256=d['source']['sha256'],effective_day='2026-10-30',event_source_sha256='a'*64,document_location='SYNTHETIC Item5.03',status='REVIEWED_IDENTITY_STATEMENT')
 link={'symb':'NEW','excd':'NAS','returned_symbol':'DNASNEW'}
 r=module().correspondence('NASDAQ:NEW','0000000001',d,link,evaluation_day='2026-11-13',symbol_transitions=[edge])
 assert r['document_status']=='CONFIRMED' and r['symbol_transition_evidence']==[edge]
 assert r['class_evidence']['reported_symbols']==['SYN'] and r['valid_from'] is None
 r=module().correspondence('NASDAQ:NEW','0000000001',d,link,evaluation_day='2026-10-29',symbol_transitions=[edge])
 assert r['document_status']=='UNCONFIRMED'


def test_exchange_suffix_cannot_override_conflicting_cover_venue():
 b=XML.replace(b'>SYN<',b'>SYN (NYSE)<')
 assert call(doc(b))['document_status']=='UNCONFIRMED'


def test_top500_candidate_does_not_promote_or_invent_security_inputs():
 r=call();c=module().top500_class_candidate(r)
 assert c['issuer_id']==r['issuer_id'] and c['class_member']==r['class_member']
 assert c['identity_status']=='UNVERIFIED' and c['security_id'] is None
 assert c['economic_class_id'] is None and c['price'] is None and c['shares'] is None
 assert c['corporate_action_status']=='NOT_EVALUATED'
