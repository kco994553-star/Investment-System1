import base64
import copy
import importlib.util
import json
import struct
import zlib
from pathlib import Path
import pytest
from investment_system.product.company_logos import FILENAME,PREFIX,public_payload,require_company_logos,sanitize_png
from investment_system.universe.universe_domains import public_payload as domains_payload

ROOT=Path(__file__).resolve().parents[1]
def chunk(kind,body):
    return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body)&0xffffffff)
def png(metadata=False):
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+(chunk(b'tEXt',b'private metadata') if metadata else b'')+chunk(b'IDAT',zlib.compress(b'\0\xff\0\0\xff'))+chunk(b'IEND',b'')
def tool():
    spec=importlib.util.spec_from_file_location('logo_pipeline',ROOT/'tools/company_logos_pipeline.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_metadata_removed_and_code_order_complete_with_initials():
    assert sanitize_png(png(True))==png()
    payload=public_payload({'NASDAQ:NVDA':png(True)})
    require_company_logos(payload)
    assert len(payload['rows'])==506
    row=next(r for r in payload['rows'] if r[0]=='NASDAQ:NVDA')
    assert base64.b64decode(row[1][len(PREFIX):])==png()
    assert all(r[1] is None for r in payload['rows'] if r[0]!='NASDAQ:NVDA')

@pytest.mark.parametrize('value',[b'<svg/>',b'PNG',png()[:-1]])
def test_non_png_corrupt_or_truncated_content_is_rejected(value):
    with pytest.raises(ValueError):sanitize_png(value)

def test_public_bundle_rejects_external_url_metadata_and_extra_keys():
    p=public_payload();p['rows'][0][1]='https://external.invalid/logo.png';p['rows'][0][2]='WIKIDATA'
    with pytest.raises(ValueError):require_company_logos(p)
    p=public_payload();p['rows'][0][1]=PREFIX+base64.b64encode(png(True)).decode();p['rows'][0][2]='WIKIDATA'
    with pytest.raises(ValueError):require_company_logos(p)
    p=public_payload();p['price']=1
    with pytest.raises(ValueError):require_company_logos(p)

def test_build_failure_is_nonfatal_one_attempt_fixed_tokens_and_initials(tmp_path,capsys):
    (tmp_path/'universe-domains.json').write_text(json.dumps(domains_payload()))
    attempts=[]
    def blocked(url,limit):attempts.append(url);raise OSError('do not expose diagnostics')
    p=tool().emit(tmp_path,live=True,fetcher=blocked)
    assert len(attempts)==1 and all(row[1] is None for row in p['rows'])
    assert 'LOGO_WIKIDATA_SOURCE_UNAVAILABLE' in capsys.readouterr().out
    assert (tmp_path/FILENAME).exists()

def test_wikidata_domain_ambiguity_stays_missing():
    m=tool();body={'results':{'bindings':[{'site':{'value':'https://www.nvidia.com'},'logo':{'value':'http://commons.wikimedia.org/wiki/Special:FilePath/Nvidia.svg'}}]}}
    assert m.domain_logos(json.dumps(body))=={'nvidia.com':'Nvidia.svg'}
    body['results']['bindings'].append({'site':{'value':'https://nvidia.com'},'logo':{'value':'http://commons.wikimedia.org/wiki/Special:FilePath/Other.svg'}})
    assert m.domain_logos(json.dumps(body))=={}


def test_live_build_matches_reviewed_domain_downloads_png_and_publishes_local_bytes(tmp_path):
    m=tool();(tmp_path/'universe-domains.json').write_text(json.dumps(domains_payload()))
    calls=[]
    def fake(url,limit):
        calls.append(url)
        if url.startswith('https://query.wikidata.org/'):
            return json.dumps({'results':{'bindings':[{'site':{'value':'https://www.nvidia.com/'},'logo':{'value':'http://commons.wikimedia.org/wiki/Special:FilePath/Nvidia_logo.svg'}}]}}).encode()
        if url.startswith('https://commons.wikimedia.org/'):
            return json.dumps({'query':{'pages':{'1':{'title':'File:Nvidia logo.svg','imageinfo':[{'thumburl':'https://upload.wikimedia.org/nvidia.svg.png'}]}}}}).encode()
        assert url=='https://upload.wikimedia.org/nvidia.svg.png'
        return png(True)
    p=m.emit(tmp_path,live=True,fetcher=fake)
    assert len(calls)==3
    row=next(r for r in p['rows'] if r[0]=='NASDAQ:NVDA')
    assert base64.b64decode(row[1][len(PREFIX):])==png()
    assert sanitize_png(base64.b64decode(row[1][len(PREFIX):]))==png()
    assert 'WIKIDATA'==row[2]
    assert 'nvidia' in m.wikidata_query(['nvidia.com'])
