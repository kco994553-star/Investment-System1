from datetime import datetime, timezone
import importlib.util
import importlib
import json
from pathlib import Path
import pytest

NOW = datetime(2026,10,10,tzinfo=timezone.utc)
CIK='0000000001'
ACCN='0000000001-26-000001'

def api():
    name='investment_system.providers.sec_m3_adapter'
    assert importlib.util.find_spec(name) is not None, 'SEC M3 adapter is not implemented'
    return importlib.import_module(name)

def payloads(tickers=None, exchanges=None, shares=100):
    sub={'cik':1,'tickers':tickers or ['DEMO'],'exchanges':exchanges or ['Nasdaq'],'filings':{'recent':{'accessionNumber':[ACCN],'form':['10-Q'],'filingDate':['2026-10-01'],'acceptanceDateTime':['2026-10-01T12:00:00Z']}}}
    facts={'cik':1,'facts':{'dei':{'EntityCommonStockSharesOutstanding':{'units':{'shares':[{'val':shares,'end':'2026-09-25','filed':'2026-10-01','form':'10-Q','accn':ACCN}]}}}}}
    return json.dumps(facts).encode(),json.dumps(sub).encode()

def cover(shares=100,symbol='DEMO',cik=CIK,unit='shares',multi=False):
    extra='<context id="total"><entity><identifier scheme="http://www.sec.gov/CIK">'+cik+'</identifier></entity><period><instant>2026-09-25</instant></period></context><dei:EntityCommonStockSharesOutstanding contextRef="total" unitRef="u">150</dei:EntityCommonStockSharesOutstanding><context id="b"><entity><identifier scheme="http://www.sec.gov/CIK">'+cik+'</identifier><segment><d:explicitMember dimension="g:StatementClassOfStockAxis">g:CommonClassBMember</d:explicitMember></segment></entity><period><instant>2026-09-25</instant></period></context><dei:EntityCommonStockSharesOutstanding contextRef="b" unitRef="u">50</dei:EntityCommonStockSharesOutstanding>' if multi else ''
    body=(f'<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:g="http://fasb.org/us-gaap/2026" xmlns:dei="http://xbrl.sec.gov/dei/2026" xmlns:d="http://xbrl.org/2006/xbrldi"><context id="a"><entity><identifier scheme="http://www.sec.gov/CIK">{cik}</identifier></entity><period><instant>2026-09-25</instant></period></context><unit id="u"><measure>xbrli:{unit}</measure></unit><dei:TradingSymbol contextRef="a">{symbol}</dei:TradingSymbol><dei:Security12bTitle contextRef="a">Common Stock</dei:Security12bTitle><dei:EntityCommonStockSharesOutstanding contextRef="a" unitRef="u">{shares}</dei:EntityCommonStockSharesOutstanding>{extra}</xbrl>').encode()
    if multi:body=body.replace(b'</identifier></entity>',b'</identifier><segment><d:explicitMember dimension="g:StatementClassOfStockAxis">g:CommonClassAMember</d:explicitMember></segment></entity>',1)
    return body

def build(**kwargs):
    a=api();facts,sub=payloads(shares=kwargs.pop('facts_shares',100))
    args=dict(code='NASDAQ:DEMO',companyfacts_body=facts,submissions_body=sub,acquired_at=NOW,as_of=NOW,synthetic=True,cover_xml=cover(),cover_accession=ACCN,cover_acquired_at=NOW)
    args.update(kwargs)
    return a.build_sec_m3_input(**args)

def test_single_class_cover_binds_existing_m3_and_contains_no_price():
    r=build();assert r.state=='INPUT_RESEARCH';assert r.shares.shares==100
    assert r.basis.basis_status=='SINGLE_CLASS_CONFIRMED'
    out=api().public_sec_input_json(r)
    assert set(out)=={'identityLookup','secByListing','basisByListing','state','reason_codes'}
    assert 'price' not in out['secByListing'][r.seed.listing_id]
    assert out['identityLookup']['NASDAQ:DEMO']['cik']==CIK

def test_no_cover_never_infers_class_from_single_ticker():
    r=build(cover_xml=None);assert r.state=='NOT_AVAILABLE';assert 'BASIS_UNCONFIRMED' in r.reason_codes
    assert r.seed is not None and r.receipt is not None

def test_multi_class_difference_is_display_only_and_original_count_is_kept():
    r=build(facts_shares=150,cover_xml=cover(multi=True))
    assert r.state=='NOT_AVAILABLE';assert r.basis.share_class_basis=='DIFFERENT'
    assert r.reason_codes==('SHARE_CLASS_BASIS',)
    assert json.loads(r.receipt.companyfacts_body)['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0]['val']==150

@pytest.mark.parametrize('kwargs,reason',[
 ({'code':'NYSE:DEMO'},'IDENTITY_UNCONFIRMED'),
 ({'code':'NASDAQ:OTHER'},'IDENTITY_UNCONFIRMED'),
 ({'cover_xml':cover(cik='0000000002')},'COVER_UNCONFIRMED'),
 ({'cover_xml':cover(symbol='OTHER')},'COVER_UNCONFIRMED'),
 ({'cover_xml':cover(unit='USD')},'COVER_UNCONFIRMED'),
 ({'cover_accession':'0000000001-26-000002'},'ACCESSION_UNCONFIRMED'),
 ({'cover_xml':b'<!DOCTYPE x><x/>'},'COVER_UNCONFIRMED'),
 ({'cover_xml':b'<x/>\x00'},'COVER_UNCONFIRMED'),
 ({'cover_xml':cover().replace(b'Common Stock',b'American Depositary Shares')},'BASIS_UNCONFIRMED'),
 ({'as_of':datetime(2026,10,9,tzinfo=timezone.utc)},'AVAILABLE_AFTER_AS_OF'),
 ({'acquired_at':datetime(2026,10,10)},'INVALID_TIMESTAMP'),
 ({'synthetic':1},'INVALID_INPUT'),
 ({'submissions_body':b'{"cik":1,"cik":2}'},'INVALID_INPUT'),
])
def test_unconfirmed_inputs_are_excluded_without_guesses(kwargs,reason):
    assert reason in build(**kwargs).reason_codes

def test_public_repacked_share_hashes_do_not_claim_to_be_original():
    r=build();o=api().public_sec_input_json(r)
    raw=o['secByListing'][r.seed.listing_id]
    from hashlib import sha256
    original_facts,original_sub=payloads()
    assert r.receipt.companyfacts_body==original_facts and r.receipt.submissions_body==original_sub
    assert sha256(raw['companyfacts_text'].encode()).hexdigest()==raw['facts_sha256']
    assert raw['facts_sha256']!=raw['origin_facts_sha256']==r.receipt.facts_sha256
    assert json.loads(raw['companyfacts_text'])['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0]['val']==100
    assert o['basisByListing'][r.seed.listing_id]['share_class_basis']=='ALIGNED'

def test_universe_static_asset_is_only_504_unique_codes_and_has_both_classes():
    p=Path(__file__).parents[1]/'src/investment_system/universe/universe_codes_v1.json'
    codes=json.loads(p.read_text());assert len(codes)==len(set(codes))==504
    assert {'NASDAQ:ASML','NASDAQ:PSKY','NASDAQ:GOOGL','NASDAQ:GOOG','NYSE:BRK.B'}<=set(codes)
    assert all(isinstance(x,str) and len(x.split(':'))==2 for x in codes)


def test_public_projection_excludes_price_and_unknown_payload_fields():
    facts,sub=payloads();data=json.loads(facts)
    data['unknown_private_field']='TEST_ONLY_SENTINEL'
    data['facts']['us-gaap']={'StockPrice':{'units':{'USD':[{'val':999}]}}}
    r=build(companyfacts_body=json.dumps(data).encode())
    text=json.dumps(api().public_sec_input_json(r))
    assert 'TEST_ONLY_SENTINEL' not in text and 'StockPrice' not in text


def test_rejected_cover_does_not_export_usable_confirmation():
    r=build(cover_accession='0000000001-26-000002')
    assert r.basis is None or r.basis.basis_status=='UNKNOWN'
    assert r.shares is None or r.shares.state=='NOT_AVAILABLE'

def test_numeric_mismatch_without_class_evidence_is_not_class_difference():
    r=build(cover_xml=cover(shares=99))
    assert r.state=='NOT_AVAILABLE' and 'SHARE_CLASS_BASIS' not in r.reason_codes
    assert r.basis is None or r.basis.share_class_basis!='DIFFERENT'

def test_multi_class_matching_count_is_not_single_class_confirmation():
    r=build(cover_xml=cover(multi=True))
    assert r.state=='NOT_AVAILABLE'
    assert r.basis is None or r.basis.basis_status=='UNKNOWN'

def test_cover_capture_must_follow_matched_filing_acceptance():
    r=build(cover_acquired_at=datetime(2026,9,26,tzinfo=timezone.utc))
    assert r.state=='NOT_AVAILABLE' and 'INVALID_TIME_ORDER' in r.reason_codes

def test_unit_qname_namespace_cannot_be_spoofed():
    xml=cover().replace(b'xmlns:xbrli="http://www.xbrl.org/2003/instance"',b'xmlns:xbrli="http://example.com/dollars"')
    assert build(cover_xml=xml).state=='NOT_AVAILABLE'

def test_security_facts_in_unrelated_old_context_do_not_confirm_new_shares():
    xml=cover().replace(b'</xbrl>',b'<context id="old"><entity><identifier scheme="http://www.sec.gov/CIK">0000000001</identifier></entity><period><instant>2025-09-25</instant></period></context></xbrl>')
    xml=xml.replace(b'TradingSymbol contextRef="a"',b'TradingSymbol contextRef="old"').replace(b'Security12bTitle contextRef="a"',b'Security12bTitle contextRef="old"')
    assert build(cover_xml=xml).state=='NOT_AVAILABLE'

def test_whitelist_projection_remains_consumable_with_fractional_acceptance():
    from investment_system.universe.private_subset import SecReceipt,prepare_sec_shares
    facts,sub=payloads();data=json.loads(sub)
    data['filings']['recent']['acceptanceDateTime']=['2026-10-01T12:00:00.000Z']
    r=build(submissions_body=json.dumps(data).encode())
    out=api().public_sec_input_json(r)['secByListing'][r.seed.listing_id]
    projected=SecReceipt(r.seed.cik,out['companyfacts_text'].encode(),out['submissions_text'].encode(),NOW,out['facts_sha256'],out['submissions_sha256'],True)
    assert prepare_sec_shares(r.seed,projected,r.basis,NOW).state=='INPUT_RESEARCH'

def test_cover_exchange_cannot_contradict_requested_listing():
    xml=cover().replace(b'</identifier></entity>',b'</identifier><segment><d:explicitMember dimension="dei:EntityListingsExchangeAxis">dei:NYSEMember</d:explicitMember></segment></entity>')
    assert build(cover_xml=xml).state=='NOT_AVAILABLE'

def test_old_other_class_cannot_be_hidden_by_measurement_date():
    xml=cover(multi=True)
    import re
    xml=re.sub(br'<context id="total">.*?</context><dei:EntityCommonStockSharesOutstanding contextRef="total".*?</dei:EntityCommonStockSharesOutstanding>',b'',xml)
    xml=xml.replace(b'<context id="b">',b'<context id="b">',1)
    a,b=xml.split(b'<context id="b">')
    xml=a+b'<context id="b">'+b.replace(b'2026-09-25',b'2026-09-24',1)
    assert build(cover_xml=xml).state=='NOT_AVAILABLE'

def test_unused_malformed_taxonomy_does_not_crash_projection():
    facts,_=payloads();d=json.loads(facts);d['facts']['us-gaap']=[]
    r=build(companyfacts_body=json.dumps(d).encode())
    assert r.state=='INPUT_RESEARCH'
    assert api().public_sec_input_json(r)['secByListing']

def test_unrelated_security_exchange_does_not_reject_selected_evidence():
    extra=b'<context id="other"><entity><identifier scheme="http://www.sec.gov/CIK">0000000001</identifier><segment><d:explicitMember dimension="dei:EntityListingsExchangeAxis">dei:NYSEMember</d:explicitMember></segment></entity><period><instant>2026-09-25</instant></period></context><dei:TradingSymbol contextRef="other">OTHER</dei:TradingSymbol><dei:Security12bTitle contextRef="other">Preferred Stock</dei:Security12bTitle>'
    assert build(cover_xml=cover().replace(b'</xbrl>',extra+b'</xbrl>')).state=='INPUT_RESEARCH'

def test_conflicting_explicit_totals_do_not_prove_class_difference():
    extra=b'<dei:EntityCommonStockSharesOutstanding contextRef="total" unitRef="u">160</dei:EntityCommonStockSharesOutstanding>'
    r=build(facts_shares=150,cover_xml=cover(multi=True).replace(b'</xbrl>',extra+b'</xbrl>'))
    assert r.reason_codes==('COVER_FACT_MISMATCH',)
    assert r.basis.share_class_basis=='UNKNOWN'
