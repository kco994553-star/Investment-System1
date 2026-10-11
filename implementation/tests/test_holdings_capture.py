"""Holdings tab parser: Python reference vectors are current, replay, prompt v1 copy and Node parity."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess

from investment_system.product.holdings_capture import HEADER, divide, parse

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / 'tests/fixtures/holdings_capture_reference_v1.json'
DOC = ROOT / 'docs/virtual_trading/HOLDINGS_CAPTURE_PROMPT_V1.md'
ASSET = ROOT / 'src/investment_system/product/web_assets/holdings-capture.js'


def tool():
    spec = importlib.util.spec_from_file_location('holdings_capture_reference', ROOT / 'tools/holdings_capture_reference.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cases():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))['cases']


def test_fixture_is_current_generator_output():
    assert json.loads(FIXTURE.read_text(encoding='utf-8')) == json.loads(json.dumps(tool().build(), ensure_ascii=False))


def test_every_case_replays_and_is_synthetic():
    for case in cases():
        assert case['synthetic'] is True
        assert parse(case['input']['values']) == json.loads(case['expected_json'])


def test_rules_fixed_by_the_prompt_contract():
    by = {c['id']: json.loads(c['expected_json']) for c in cases()}
    assert HEADER == ('as_of', 'symbol', 'quantity', 'avg_cost', 'currency', 'cost_krw', 'name')
    assert by['header-mismatch']['state'] == 'HEADER_MISMATCH' and by['header-mismatch']['review'] == []
    assert by['cost-krw-preferred']['positions'][0]['cost_basis'] == 'COST_KRW_DIV_QTY'
    assert by['avg-cost-fallback']['positions'][0]['cost_basis'] == 'AVG_COST_FIELD'
    missing = by['no-cost-not-zero-filled']['positions'][0]
    assert missing['average_cost'] is None and missing['cost_basis'] == 'NOT_AVAILABLE'
    assert [c['symbol'] for c in by['cash-rows']['cash']] == ['CASH_KRW', 'CASH_USD'] and by['cash-rows']['positions'] == []
    assert all(r['reason_codes'] == ['QUANTITY_FORMAT'] for r in by['number-format-errors']['review'] if r['row'] in (2, 5, 7, 8))
    for expected in by.values():
        for position in expected['positions']:
            assert position['symbol'] and not position['symbol'].startswith('CASH_')
    assert divide('100', '3') == '33.333333' and divide('2', '3') == '0.666667' and divide('1', '0') is None


def test_prompt_document_matches_web_asset():
    doc = DOC.read_text(encoding='utf-8')
    assert doc.startswith('# 잔고 캡처 변환 프롬프트 v1\n') and 'prompt_id: `holdings-capture-prompt/v1`' in doc
    block = re.search(r'## 프롬프트 \(원문 그대로\)\n\n```text\n(.*?)\n```\n', doc, re.S).group(1)
    out = subprocess.run(['node', '-e', 'process.stdout.write(require(process.argv[1]).PROMPT_TEMPLATE)', str(ASSET)],
                         capture_output=True, text=True, encoding='utf-8')
    assert out.returncode == 0 and out.stdout == block
    assert '{{AS_OF}}' in block and '모르면 빈칸' in block


def test_node_port_matches_every_vector():
    out = subprocess.run(['node', str(ROOT / 'tools/holdings_capture_node_test.js')], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:]
