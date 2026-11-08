import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest
from investment_system.research.sector_qgv import default_config, preset, preview_qgv
from investment_system.research.sector_qgv_partial import compare_axes, assert_retained_preview

FIX = Path(__file__).parents[1]/'docs/research/sector_qgv/synthetic-input.json'


def inputs():
    s = json.loads(FIX.read_text()); c = default_config()
    # A new valid factor needs opposite order; no engine formula is copied.
    for i, r in enumerate(s['rows']):
        obs = copy.deepcopy(r['observations']['operating_margin_ttm'])
        obs.update(variant_id='roa_ttm', formula_version='roa_ttm/1', value=(20-i)/100)
        from investment_system.research.sector_qgv_registry import CATALOG
        obs['formula_version']=CATALOG['roa_ttm']['formula_version']
        r['observations']['roa_ttm']=obs
        r['observations']={v:o for v,o in r['observations'].items() if not v.startswith('ep_') and v not in ['cfo_mcap','sales_ev']}
    p = preset(c,'INFORMATION_TECHNOLOGY','GENERAL')
    p['axes']['Q']['profitability']['factors']={'operating_margin_ttm':5000,'roa_ttm':5000}
    c['scoped_overrides']['INFORMATION_TECHNOLOGY|GENERAL']=p
    return s, c


def test_q_partial_delta_is_attributed_to_role_budget_not_total_or_gate():
    s,c=inputs();a=preview_qgv(default_config(),s,'old');b=preview_qgv(c,s,'new')
    out=compare_axes(a,b,default_config(),c,'D1')
    assert out['denominator']==20 and out['axes']['Q']['COMMON_VALID']==20
    for x in out['rows']:
        old=next(r for r in a['result_rows'] if r['company_id']==x['company_id'])
        # Independently derived linear allocation change: 0.2*(ROA - margin).
        expected=.2*(old['factors']['roa_ttm']['score']-old['factors']['operating_margin_ttm']['score'])
        assert x['axes']['Q']['delta']==pytest.approx(expected)
        assert x['axes']['G']['delta']==0
        assert x['total']=={'before':None,'after':None}
    assert out['performance'] is None and out['rank'] is None


def test_lost_axis_preserves_missing_and_small_peer_reasons():
    s,c=inputs();s['rows'][0]['observations'].pop('roa_ttm')
    a=preview_qgv(default_config(),s,'old');b=preview_qgv(c,s,'new')
    out=compare_axes(a,b,default_config(),c,'D1')
    assert out['axes']['Q']['LOST']==20
    assert out['rows'][0]['axes']['Q']['after_reasons']==['MISSING_INPUT']
    assert out['rows'][1]['axes']['Q']['after_reasons']==['PEER_SAMPLE_SMALL']
    assert out['axes']['G']['COMMON_VALID']==20


def test_reject_changed_date_config_members_and_non_setting_input_changes():
    s,c=inputs();a=preview_qgv(default_config(),s,'old');b=preview_qgv(c,s,'new')
    for key in ['as_of','valuation_date','input_hash','universe_version']:
        bad=copy.deepcopy(b);bad[key]='wrong'
        with pytest.raises(ValueError,match='CONTEXT'):compare_axes(a,bad,default_config(),c,'D1')
    with pytest.raises(ValueError,match='CONFIG_CHANGED'):compare_axes(a,b,default_config(),c,'I1',input_treatment=True)
    bad=copy.deepcopy(b);bad['result_rows'].pop()
    with pytest.raises(ValueError,match='MEMBERS'):compare_axes(a,bad,default_config(),c,'D1')
    with pytest.raises(ValueError,match='IDENTITY'):assert_retained_preview(a,s,c)


def test_cli_reuses_retained_reference_and_saved_setting(tmp_path):
    s,c=inputs();before=preview_qgv(default_config(),s,'old')
    def write(name,data):
        p=tmp_path/name;p.write_text(json.dumps(data));return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    job={'mode':'normalized','data_kind':'SYNTHETIC','request_id':'D1','config':c,
         'snapshot':write('s.json',s),'axis_comparison':{'comparison_id':'D1','before_preview':write('b.json',before),'before_config':default_config()}}
    spec=importlib.util.spec_from_file_location('partial_cli',FIX.parents[3]/'tools/sector_qgv.py')
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    cli.run(job,tmp_path/'out',True)
    view=json.loads((tmp_path/'out/preview.json').read_text())
    saved=json.loads((tmp_path/'out/saved-config.json').read_text())
    assert saved['config']==c and saved['canonical_config_hash']==view['config_hash']
    assert json.loads((tmp_path/'out/axis-comparison.json').read_text())['axes']['Q']['COMMON_VALID']==20
