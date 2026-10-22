import base64
import copy
import importlib.util
import json
import io
import struct
import urllib.error
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


def test_ui_preserve_keeps_published_logo_bytes_without_collection(tmp_path, monkeypatch):
    m = tool()
    body = (json.dumps(public_payload({'NASDAQ:NVDA': png()}), indent=3) + '\n').encode()
    (tmp_path / FILENAME).write_text(json.dumps(public_payload()))
    calls = []
    class Response(io.BytesIO):
        status = 200
        def geturl(self):
            return 'https://kco994553-star.github.io/Investment-System1/' + FILENAME
    def opened(request, timeout):
        calls.append(request.full_url)
        assert request.get_method() == 'GET'
        return Response(body)
    def forbidden(*args, **kwargs):
        pytest.fail('UI preservation must not collect from logo providers')
    monkeypatch.setattr(m, 'emit', forbidden)
    monkeypatch.setattr(m, 'fetch', forbidden)
    assert m.preserve(tmp_path, open_response=opened) == 'LOGO_PREVIOUS_RESTORED'
    assert calls == ['https://kco994553-star.github.io/Investment-System1/' + FILENAME]
    assert (tmp_path / FILENAME).read_bytes() == body


@pytest.mark.parametrize('failure', ['404', '503', 'network', 'invalid', 'redirect'])
def test_ui_preserve_failure_never_replaces_existing_bytes(tmp_path, failure):
    m = tool()
    before = json.dumps(public_payload({'NASDAQ:NVDA': png()}), indent=2).encode()
    (tmp_path / FILENAME).write_bytes(before)
    class Response(io.BytesIO):
        status = 200
        def geturl(self):
            base = 'https://kco994553-star.github.io/Investment-System1/'
            return ('https://example.invalid/' if failure == 'redirect' else base) + FILENAME
    def opened(request, timeout):
        if failure in ('404', '503'):
            raise urllib.error.HTTPError(request.full_url, int(failure), 'hidden response', {}, None)
        if failure == 'network':
            raise OSError('hidden network diagnostics')
        return Response(b'{"unsafe":"payload"}' if failure == 'invalid' else before)
    if failure == '404':
        assert m.preserve(tmp_path, open_response=opened) == 'LOGO_PREVIOUS_NOT_AVAILABLE'
    else:
        with pytest.raises(ValueError, match='^LOGO_PREVIOUS_RESTORE_FAILED$'):
            m.preserve(tmp_path, open_response=opened)
    assert (tmp_path / FILENAME).read_bytes() == before


def test_manual_ui_workflow_preserves_logos_while_daily_collects():
    ui = (ROOT.parent / '.github/workflows/cockpit-pages.yml').read_text()
    daily = (ROOT.parent / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    assert 'company_logos_pipeline.py --preserve-only --out' in ui
    assert 'company_logos_pipeline.py --live' not in ui
    assert 'company_logos_pipeline.py --live --out' in daily


def test_ui_preserve_cli_fails_closed_with_fixed_output(tmp_path, monkeypatch, capsys):
    m = tool()
    def broken(*args, **kwargs):
        raise ValueError('sensitive upstream diagnostics')
    monkeypatch.setattr(m, 'preserve', broken)
    assert m.main(['--out', str(tmp_path), '--preserve-only']) == 1
    assert capsys.readouterr().out == 'LOGO_PREVIOUS_RESTORE_FAILED\n'
    with pytest.raises(SystemExit) as error:
        m.main(['--out', str(tmp_path), '--preserve-only', '--live'])
    assert error.value.code == 2


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

@pytest.mark.parametrize('bits,extra,raw',[(8,b'',b'\0'),(1,b'',b'\0\xff'),(8,chunk(b'tRNS',b'REVIEW_METADATA_CANARY'),b'\0\xff\0\0\xff')])
def test_illegal_depth_bad_scanline_and_rgba_trns_are_rejected(bits,extra,raw):
    content=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,bits,6,0,0,0))+extra+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
    with pytest.raises(ValueError):sanitize_png(content)

@pytest.mark.parametrize('color,bits,width,height,extra,raw,rgba',[
    (3,1,2,1,chunk(b'PLTE',bytes([255,0,0,0,255,0]))+chunk(b'tRNS',bytes([255,128])),b'\0\x40',b'\0\xff\0\0\xff\0\xff\0\x80'),
    (0,1,2,1,b'',b'\0\x40',b'\0\0\0\0\xff\xff\xff\xff\xff'),
    (6,8,1,2,b'',bytes([0,10,20,30,255,2,5,5,5,0]),bytes([0,10,20,30,255,0,15,25,35,255])),
    (2,8,1,1,chunk(b'tRNS',struct.pack('>HHH',10,20,30)),bytes([0,10,20,30]),bytes([0,10,20,30,0])),
])
def test_valid_palette_grayscale_filter_and_transparency_normalize_to_rgba(color,bits,width,height,extra,raw,rgba):
    content=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,bits,color,0,0,0))+extra+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
    normalized=sanitize_png(content)
    expected=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rgba))+chunk(b'IEND',b'')
    assert normalized==expected
    assert sanitize_png(normalized)==normalized
    assert b'tRNS' not in normalized and b'PLTE' not in normalized
