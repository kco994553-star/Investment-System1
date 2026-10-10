"""A UI-only Pages deployment must preserve validated price-free SEC observations."""
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import subprocess
import urllib.error

import pytest

ROOT = Path(__file__).resolve().parents[1]

def tool():
    spec = importlib.util.spec_from_file_location('preserve_public_sec_inputs', ROOT / 'tools/preserve_public_sec_inputs.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Response(BytesIO):
    status = 200
    def geturl(self):
        return tool().SOURCE


def fixture():
    r = subprocess.run(['node','-e',"process.stdout.write(JSON.stringify(require('./tools/sec_reported_fixture.js').fixture()));"], cwd=ROOT, capture_output=True, check=True, text=True)
    return r.stdout.encode()


def test_preserve_price_free_schema_v3_and_fixed_request(tmp_path):
    module = tool()
    calls = []
    payload = fixture()
    def open_response(request, timeout):
        calls.append((request, timeout))
        return Response(payload)
    assert module.preserve(tmp_path, open_response=open_response) == 'SEC_PREVIOUS_RESTORED'
    assert json.loads((tmp_path/module.FILENAME).read_bytes()) == json.loads(payload)
    assert calls[0][0].full_url == module.SOURCE
    assert 'Authorization' not in calls[0][0].headers
    assert calls[0][1] <= 30


def test_initial_404_is_optional_and_has_no_file(tmp_path):
    module = tool()
    def missing(*args, **kwargs):
        raise urllib.error.HTTPError(module.SOURCE,404,'private provider message',None,None)
    assert module.preserve(tmp_path, open_response=missing) == 'SEC_PREVIOUS_NOT_AVAILABLE'
    assert not (tmp_path/module.FILENAME).exists()


@pytest.mark.parametrize('kind',['malformed','price','oversize','transport','http403','redirect'])
def test_other_errors_fail_closed_with_fixed_code_and_keep_previous_file(tmp_path,kind):
    module = tool()
    destination = tmp_path/module.FILENAME
    destination.write_bytes(b'previous validated sentinel')
    def bad(*args, **kwargs):
        if kind == 'transport': raise OSError('private provider message')
        if kind == 'http403': raise urllib.error.HTTPError(module.SOURCE,403,'private provider message',None,None)
        if kind == 'redirect':
            class WrongURL(Response):
                def geturl(self): return 'https://other.test/private'
            return WrongURL(fixture())
        if kind == 'oversize': return Response(b'x'*(module.MAX_BYTES+1))
        if kind == 'malformed': return Response(b'{bad')
        payload=json.loads(fixture());payload['price']=1
        return Response(json.dumps(payload).encode())
    with pytest.raises(ValueError,match='^SEC_PREVIOUS_RESTORE_FAILED$'):
        module.preserve(tmp_path, open_response=bad)
    assert destination.read_bytes() == b'previous validated sentinel'
