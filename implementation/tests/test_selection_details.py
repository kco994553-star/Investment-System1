from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timezone
import pytest
from investment_system.validation import vertical_slice as vs
from investment_system.contracts.universe import UniverseMember
from investment_system.universe.engine import UniverseEngine

AT=datetime(2026,11,4,tzinfo=timezone.utc)


def execute(tmp_path,monkeypatch,quality,policy,*,duplicate=False):
    universe=UniverseEngine().snapshot(AT,roster=tuple(UniverseMember(k,k,cik='0000000001' if duplicate else str(i+1).zfill(10)) for i,k in enumerate(quality)),source_vintage='2026-11-04')
    universe=replace(universe,available_at=AT,universe_id='SYN:POPULATION')
    monkeypatch.setattr(vs,'run_as_of',lambda *a,**kw:{'quality':deepcopy(quality)})
    return vs.run_vertical_slice(AT,AT,{}, {},universe=universe,selection_policy=policy,store_path=tmp_path/'store.json')


def test_normal_entry_returns_missing_reasons_cash_and_saved_input_identity(tmp_path,monkeypatch):
    q={'SYN:A':{'Q':80,'G':70},'SYN:B':{'Q':80,'G':70},'SYN:C':{'Q':None,'G':20},'SYN:D':{'Q':40,'G':None}}
    r=execute(tmp_path,monkeypatch,q,vs.SelectionPolicy('top_n',1));d=r['selection_details']
    assert d['original_population']['members']==list(q)
    by={x['company_id']:x for x in d['rows']}
    assert by['SYN:C']['exclusion_reasons']==['Q_MISSING'] and by['SYN:D']['exclusion_reasons']==['G_MISSING']
    assert by['SYN:B']['exclusion_reasons']==['OUTSIDE_SELECTION_LIMIT']
    assert d['portfolio']['cash_weight']==0 and d['portfolio']['weight_sum']==1
    again=execute(tmp_path,monkeypatch,q,vs.SelectionPolicy(**r['selection_policy']))
    assert again['selection_details']['reproduction']==d['reproduction']
    changed=deepcopy(q);changed['SYN:B']['Q']=81
    after=execute(tmp_path,monkeypatch,changed,vs.SelectionPolicy(**r['selection_policy']))['selection_details']
    assert after['reproduction']['input_hash']!=d['reproduction']['input_hash']
    assert after['reproduction']['setting_hash']==d['reproduction']['setting_hash']
    assert d['reproduction']['scope']=='SELECTION_AND_WEIGHTS_FROM_RETAINED_AXES_NOT_QGV_OR_PERFORMANCE_REPLAY'


def test_empty_is_not_invented_all_cash_and_duplicates_are_explicit(tmp_path,monkeypatch):
    r=execute(tmp_path,monkeypatch,{'SYN:A':{'Q':None,'G':None}},vs.SelectionPolicy('all'))
    assert r['selection_details']['portfolio']['state']=='NOT_FORMED'
    assert r['selection_details']['portfolio']['cash_weight'] is None
    r=execute(tmp_path,monkeypatch,{'SYN:A':{'Q':80,'G':70},'SYN:B':{'Q':80,'G':70}},vs.SelectionPolicy('all'),duplicate=True)
    d=r['selection_details'];assert len(r['selected'])==2
    assert d['issuers']['duplicate_groups']=={'0000000001':['SYN:A','SYN:B']}
    assert d['issuers']['handling']=='NO_CONSOLIDATION_OR_ISSUER_CAP_IN_EXISTING_RULE'
    assert d['issuers']['security_identity_verified'] is False


def test_walk_forward_passes_same_details_without_new_rule(tmp_path,monkeypatch):
    q={'SYN:A':{'Q':80,'G':70}};single=execute(tmp_path,monkeypatch,q,vs.SelectionPolicy('all'))
    monkeypatch.setattr(vs,'run_vertical_slice',lambda *a,**kw:single)
    nextday=datetime(2026,11,5,tzinfo=timezone.utc)
    result=vs.run_walk_forward([AT,nextday],{}, {},lambda _:None,selection_policy=vs.SelectionPolicy('all'))
    assert result['steps'][0]['selection_details']==single['selection_details']
