"""Dual QGV forward versions: same-session only, immutable old records, no price inputs."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys

import pytest

from investment_system.validation import forward_ledger as fl
from investment_system.universe import sec_qgv2 as q

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
MON = datetime(2026, 10, 19, 22, 30, tzinfo=timezone.utc)


def source(at='2026-10-19T22:30:00Z'):
    from sec_qgv2_reference import expand
    value = expand(json.loads((ROOT / 'tests/fixtures/sec_qgv2_vectors_v1.json').read_text())['base'])
    # Source fixture represents real-shaped SEC inputs with synthetic amounts, never live data.
    value['as_of'] = at
    for row in [*value['records'].values(), *value['target'].values()]:
        if row['acquired_at']:
            row['acquired_at'] = at
    return q.encode(q.require_qgv2(value))


def test_valid_source_v2_qg_same_session_and_target_weights(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('_build_v2_test', ROOT / 'tools/build_pages_cockpit.py')
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    build.build_public_cockpit(tmp_path / 'site')
    result = fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=source(),
                                catalog_body=(tmp_path / 'site/actual-catalog.json').read_bytes())
    assert result['state'] == 'RECORDED'
    assert result['version'] == fl.V2_VERSION and result['strategy'] == fl.V2_STRATEGY
    assert result['companies']['nvda']['Q']['missing_factor_count'] <= 5
    assert all(set(row) == {'state', 'Q', 'G'} for row in result['companies'].values())
    ledger = fl.append(fl.new_ledger(MON), result, MON)
    fl.require_ledger(ledger)
    node = subprocess.run(['node', '-e', "const m=require(process.argv[1]);m.validate(JSON.parse(process.argv[2]));", str(ROOT / 'src/investment_system/product/web_assets/forward-validation.js'), fl.encode(ledger).decode()], capture_output=True)
    assert node.returncode == 0, node.stderr.decode()


def test_missing_stale_future_v2_sources_are_na_never_backfilled():
    missing = fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=None, catalog_body=None)
    assert missing['reason_codes'] == ['TARGET_CATALOG_MISSING', 'SEC_QGV2_MISSING']
    old = json.loads(source('2026-10-18T22:30:00Z'))
    stale = fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=q.encode(old), catalog_body=None)
    assert 'SEC_QGV2_NOT_SAME_SESSION' in stale['reason_codes']
    ledger = fl.new_ledger(MON)
    with pytest.raises(ValueError):
        fl.require_ledger(fl.append(ledger, {**missing, 'date': '2026-10-18'}, MON + timedelta(days=1)))


def test_schema_one_upgrade_preserves_every_record_and_v2_starts_now():
    v1 = fl.build_record(now=MON, session=MON.date(), qg_body=None, catalog_body=None)
    old = fl.append(fl.new_ledger(MON), v1, MON)
    old['schema_version'], old['strategy'] = 1, fl.STRATEGY
    old['versions'].pop(fl.V2_VERSION)
    old['version_status'].pop(fl.V2_VERSION)
    fl.require_ledger(old)
    upgraded = fl.finalize(old, MON + timedelta(days=1))
    assert fl.canonical(old['versions'][fl.VERSION]) == fl.canonical(upgraded['versions'][fl.VERSION])
    assert upgraded['versions'][fl.V2_VERSION] == []
    fl.require_append_only(old, upgraded)
    fl.require_ledger(upgraded)
