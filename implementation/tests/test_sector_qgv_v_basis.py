import copy,hashlib
import pytest
from investment_system.research.sector_qgv_v import connect_held_cover
from pathlib import Path
import runpy
fixture=runpy.run_path(str(Path(__file__).with_name("test_sector_qgv_v.py")))["fixture"]

BODY=b'''<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:dei="http://xbrl.sec.gov/dei/2026"><context id="c"><entity><identifier scheme="http://www.sec.gov/CIK">SYNTHETIC</identifier></entity><period><instant>2026-07-27</instant></period></context><dei:TradingSymbol contextRef="c">SYN</dei:TradingSymbol><dei:Security12bTitle contextRef="c">Common Stock</dei:Security12bTitle><dei:EntityCommonStockSharesOutstanding contextRef="c">10</dei:EntityCommonStockSharesOutstanding></xbrl>'''

def test_held_cover_links_metadata_without_extending_identity_interval():
 p,_=fixture();r=p['rows'][0];r['security_id']=None;old=copy.deepcopy(p)
 sr={'cik':r['issuer_id'],'filed':'2026-07-31','acquired_at':p['as_of'],'accn':'SYNTHETIC','source_sha256':{'cover':hashlib.sha256(BODY).hexdigest()}}
 out,audit=connect_held_cover(p,r['company_id'],'SYN',BODY,sr,'synthetic:shares')
 assert p==old and out['rows'][0]['security_id'] is None
 assert out['rows'][0]['held_cover_evidence']['titles']==['Common Stock']
 assert audit['new_documentary_connections']==1 and audit['new_valuation_date_identity']==0
 assert out['snapshot']==old['snapshot']
 sr['source_sha256']['cover']='0'*64
 with pytest.raises(ValueError,match='HASH'):connect_held_cover(p,r['company_id'],'SYN',BODY,sr,'synthetic:shares')

def test_single_security_raw_ratios_do_not_need_twenty_peers():
 from investment_system.research.sector_qgv_v import resume
 from investment_system.research.sector_qgv import digest
 p,m=fixture();code=p['rows'][0]['company_id'];p['rows']=p['rows'][:1];p['snapshot']['rows']=p['snapshot']['rows'][:1];p['snapshot']['members']=[code]
 m['records']={code:m['records'][code]};m['resume_hash']=digest(p)
 s,v=resume(p,m,'one-security')
 assert sum(o.get('value') is not None for k,o in s['rows'][0]['observations'].items() if k in ('ep_ttm_diluted','cfo_mcap','sales_ev'))==3
 assert v['coverage']['axes']['V']['valid']==0 and v['coverage']['total']['valid']==0
 assert v['result_rows'][0]['factors']['cfo_mcap']['score_status']=='PEER_SAMPLE_SMALL'
