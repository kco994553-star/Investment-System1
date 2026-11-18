"""Cache hits are results reuse, never a substitute for current permissions."""
import importlib
from datetime import datetime, timezone

import pytest


def api():
    try:
        return importlib.import_module('investment_system.research.qgv_backtest.cache')
    except ModuleNotFoundError:
        pytest.fail('validated preparation cache missing')


def rights():
    return dict(receipt='SYNTHETIC_ONLY', research=True, ai_processing=True, storage=True,
                derived_storage=True, expires_at='2030-01-01T00:00:00Z', revoked=False)


def test_key_separates_universes_inputs_and_rules_but_cost_is_not_a_preparation_dependency():
    module = api()
    cache = module.PreparationCache()
    assert cache.key('scores',dict(group='U-BOOK200',input='a',rules='v1')) != cache.key('scores',dict(group='U-SPX-HIST',input='a',rules='v1'))
    assert cache.key('scores',dict(group='U-BOOK200',input='a',rules='v1')) != cache.key('scores',dict(group='U-BOOK200',input='b',rules='v1'))
    assert cache.key('scores',dict(group='U-BOOK200',input='a',rules='v1')) != cache.key('scores',dict(group='U-BOOK200',input='a',rules='v2'))
    calls = []
    for cost in (0,10,30):
        result = cache.get_or_compute('scores',dict(group='U-BOOK200',input='a',rules='v1'),lambda: calls.append(1) or {'score':42})
        assert result == {'score':42}
    assert calls == [1]
    assert cache.stats == dict(hits=2, misses=1, writes=0)


def test_persistent_cache_rechecks_expiry_revocation_and_derived_rights_on_hit(tmp_path):
    module = api()
    clock = [datetime(2026,10,27,tzinfo=timezone.utc)]
    grant = rights()
    cache = module.PreparationCache(tmp_path/'private'/'cache', private_root=tmp_path/'private', rights=grant, clock=lambda:clock[0])
    cache.get_or_compute('selection',{'input':'v1'},lambda:{'members':['SYNTHETIC']})
    assert cache.stats['writes'] == 1
    second = module.PreparationCache(tmp_path/'private'/'cache', private_root=tmp_path/'private', rights=grant, clock=lambda:clock[0])
    assert second.get_or_compute('selection',{'input':'v1'},lambda:pytest.fail('must reuse')) == {'members':['SYNTHETIC']}
    grant['revoked'] = True
    with pytest.raises(PermissionError,match='CACHE_RIGHTS'):
        second.get_or_compute('selection',{'input':'v1'},lambda:{})
    grant['revoked'] = False
    grant['derived_storage'] = False
    with pytest.raises(PermissionError,match='CACHE_RIGHTS'):
        second.get_or_compute('selection',{'input':'v1'},lambda:{})
    grant['derived_storage'] = True
    clock[0] = datetime(2031,1,1,tzinfo=timezone.utc)
    with pytest.raises(PermissionError,match='CACHE_RIGHTS'):
        second.get_or_compute('selection',{'input':'v1'},lambda:{})


def test_persistent_cache_detects_payload_tampering_and_symlink_paths(tmp_path):
    module = api()
    private = tmp_path/'private'
    cache = module.PreparationCache(private/'cache',private_root=private,rights=rights())
    cache.get_or_compute('pit',{'signal':'x'},lambda:{'value':1})
    path = next((private/'cache').glob('*.json'))
    path.write_text(path.read_text().replace('"value":1','"value":999'))
    other = module.PreparationCache(private/'cache',private_root=private,rights=rights())
    with pytest.raises(ValueError,match='CACHE_INTEGRITY'):
        other.get_or_compute('pit',{'signal':'x'},lambda:{})
    path.unlink()
    external = tmp_path/'external.json'
    external.write_text('{}')
    path.symlink_to(external)
    with pytest.raises((OSError,ValueError)):
        other.get_or_compute('pit',{'signal':'x'},lambda:{})
    assert external.read_text() == '{}'


def test_cached_values_are_not_mutated_by_a_later_portfolio():
    cache = api().PreparationCache()
    first = cache.get_or_compute('pit',{'x':1},lambda:{'metrics':{'x':3}})
    first['metrics']['x'] = 99
    assert cache.get_or_compute('pit',{'x':1},lambda:{}) == {'metrics':{'x':3}}


def test_resource_integrity_hashes_one_shared_source_file_once(tmp_path,monkeypatch):
    from pathlib import Path
    from test_qgv_backtest_runner import manifest_for,spec
    from investment_system.research.qgv_backtest import config
    manifest=manifest_for(tmp_path)
    source=Path(manifest['resources']['prices']['path'])
    original=Path.read_bytes
    reads=[]
    def observed(path):
        if path==source:
            reads.append(path)
        return original(path)
    monkeypatch.setattr(config,'validate_period_contract',lambda _:None)
    monkeypatch.setattr(Path,'read_bytes',observed)
    result=config.audit_inputs(spec(),manifest,'TARGET_QGV_V2')
    assert result['status']=='INPUT_INTEGRITY_PASS'
    assert len(reads)==1


def test_factor_preparation_indexes_price_and_financial_rows_once_per_call():
    from datetime import date
    from test_qgv_backtest_universe import inputs
    from investment_system.research.qgv_backtest.universe import factor_values
    class ObservedRows(list):
        iterations=0
        def __iter__(self):
            self.iterations+=1
            return super().__iter__()
    data=inputs()
    data['prices']=ObservedRows(data['prices'])
    data['factor_inputs']=ObservedRows([])
    identities={sid:dict(market_cap_usd=100,ordinary_price_usd=10) for sid in ('SYN00','SYN01','SYN02')}
    factor_values(data,identities,date(2016,2,12))
    assert data['prices'].iterations==1
    assert data['factor_inputs'].iterations==1
