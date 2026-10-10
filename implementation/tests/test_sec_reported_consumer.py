"""Keep the browser reader compatible with the merged public SEC contract."""
import json
from pathlib import Path
import runpy
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.skipif(not shutil.which('node'), reason='Node required for browser contract')
def test_public_versions_and_partial_rows_match_python_schema():
    producer = runpy.run_path(str(ROOT / 'tools/public_sec_inputs.py'))
    script = """
const {fixture,unavailable}=require('./tools/sec_reported_fixture.js');
const api=require('./src/investment_system/product/web_assets/sec-reported.js');
const vectors=[1,2,3].map(fixture);
for(const version of [2,3]){const p=fixture(version);p.companies[0]=unavailable(p.companies[0],1,version);vectors.push(p);}
const p=fixture(3);p.companies[0].excluded_fact_counts={CLASS_SPLIT:2,VALUE_INVALID:3};p.companies[0].share_class_notice='SHARE_CLASS_BASIS';vectors.push(p);
process.stdout.write(JSON.stringify(vectors.map(input=>({input,display:api.project(input)}))));
"""
    result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, check=True, text=True)
    vectors = json.loads(result.stdout)
    assert len(vectors) == 6
    for vector in vectors:
        payload = producer['require_public_inputs'](vector['input'])
        display = vector['display']
        assert display['schema'] == payload['schema']
        for row in payload['companies']:
            shown = display['companies'][row['company_id']]
            assert shown['status'] == row.get('status', 'LIVE')
            assert shown['excluded_fact_counts'] == row.get('excluded_fact_counts', {})
            assert shown['share_class_notice'] == row.get('share_class_notice')
            assert shown['share_class_basis'] == row.get('share_class_basis')
            assert shown['reason_codes'] == row.get('reason_codes', [])
            assert 'reported_shares' not in shown
            assert 'sources' not in shown
