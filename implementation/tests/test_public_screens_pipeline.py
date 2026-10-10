"""Offline integration: one acquisition, temporary raw inputs, exact public schemas."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import pytest

sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
from public_screens_pipeline import emit, collect
from preserve_public_screens import preserve
from investment_system.product.public_engine_screens import require_public_screen
from tests.test_public_sec_inputs import raw
from tests.test_public_engine_screens import sec, NOW, macro_manifest, remaining_manifest, thirteen_f_manifest


@pytest.mark.parametrize("factory",[sec,macro_manifest,remaining_manifest,thirteen_f_manifest])
def test_browser_reader_agrees_with_canonical_projection_vectors(tmp_path,factory):
    from investment_system.product.public_engine_screens import generate_screen_bundle
    m=factory(tmp_path)
    for name,p in generate_screen_bundle(manifest=m,input_root=tmp_path,as_of=NOW,stale_after=timedelta(hours=24)).items():
        require_public_screen(name,p)
        result=subprocess.run(['node','-e',"const a=require(process.argv[1]),p=JSON.parse(require('fs').readFileSync(0,'utf8'));a.validate(process.argv[2],p)",str(Path(__file__).parents[1]/'src/investment_system/product/web_assets/public-screens.js'),name],input=json.dumps(p),text=True,capture_output=True)
        assert result.returncode==0, 'PUBLIC_READER_PARITY_FAILED'


def test_collector_reuses_each_raw_capture_once_and_never_exports_raw(tmp_path):
    calls=[]
    class Client:
        def __init__(self,_):pass
        def collect(self,company,cik):
            calls.append(company)
            return *(json.dumps(x).encode() for x in raw(company)),datetime(2026,2,2,12,tzinfo=timezone.utc)
    result=collect(tmp_path,environ={'SEC_USER_AGENT':'synthetic setting'},client_factory=Client)
    assert len(calls)==len(set(calls))==17 and result['failed_companies']==0
    assert len(list(tmp_path.iterdir()))==6
    for path in tmp_path.iterdir():
        text=path.read_text(); assert 'never publish' not in text and '987654321' not in text and 'synthetic setting' not in text
        if path.name!='sec-public-inputs.json':require_public_screen(path.name,json.loads(text))


def test_failed_collection_preserves_previous_sidecars(tmp_path):
    emit(tmp_path); before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    class Client:
        def __init__(self,_):pass
        def collect(self,*_):raise ValueError('private diagnostic must not be emitted')
    with pytest.raises(Exception):collect(tmp_path,environ={'SEC_USER_AGENT':'synthetic setting'},client_factory=Client)
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}


def test_ui_restore_validates_all_before_writing_and_404_keeps_unavailable(tmp_path):
    emit(tmp_path); before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    class Response:
        status=200
        def __init__(self,url):self.url=url
        def geturl(self):return self.url
        def read(self,n):return before[self.url.rsplit('/',1)[1]][:n]
        def __enter__(self):return self
        def __exit__(self,*_):pass
    assert preserve(tmp_path,open_response=lambda req,**_:Response(req.full_url))==5
    def missing(req,**_):raise urllib.error.HTTPError(req.full_url,404,'',{},None)
    assert preserve(tmp_path,open_response=missing)==0
    def invalid(req,**_):
        r=Response(req.full_url)
        if req.full_url.endswith('sec-qg-factors.json'):r.read=lambda _:b'{"price":123}'
        return r
    with pytest.raises(ValueError,match='PUBLIC_SCREENS_RESTORE_FAILED'):preserve(tmp_path,open_response=invalid)
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}
