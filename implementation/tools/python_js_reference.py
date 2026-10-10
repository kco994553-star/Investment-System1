#!/usr/bin/env python3
"""Replay synthetic test contracts. Never a public/live-data serializer."""
from collections.abc import Mapping
from dataclasses import fields,is_dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))


class DependencyPending(RuntimeError):pass


def wire(value):
    if isinstance(value,Enum):return value.value
    if is_dataclass(value):return {f.name:wire(getattr(value,f.name)) for f in fields(value)}
    if isinstance(value,Mapping):return {k:wire(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [wire(v) for v in value]
    if isinstance(value,datetime):return value.isoformat()
    return value


def sec_adapter(data):
    from investment_system.providers.sec_m3_adapter import build_sec_m3_input
    args=dict(data)
    for key in ('companyfacts_body','submissions_body','cover_xml'):
        if args.get(key) is not None:args[key]=args[key].encode()
    for key in ('acquired_at','as_of','cover_acquired_at'):
        if args.get(key) is not None:args[key]=datetime.fromisoformat(args[key].replace('Z','+00:00'))
    args['synthetic']=True
    return build_sec_m3_input(**args)


def replay(case):
    if case.get('synthetic') is not True:raise ValueError('SYNTHETIC_ONLY')
    op=case['operation'];data=case['input']
    if op in ('dcf','reverse_dcf'):
        from investment_system.qgv.dcf import two_stage_dcf,reverse_dcf
        return wire((two_stage_dcf if op=='dcf' else reverse_dcf)(**data))
    if op=='v_factors':
        from investment_system.qgv.price_value import calculate_v_price_factors,VPriceInputs
        return wire(calculate_v_price_factors(VPriceInputs(**data['inputs']),price=data['price']))
    if op=='strategy':
        from investment_system.qgv.strategy_preview import recalculate_strategy_preview
        from investment_system.contracts.models import FactorObservation
        from investment_system.contracts.enums import QualityState,ProfileKind
        obs={k:FactorObservation(k,v['score'],v['score'],QualityState(v['quality']),'synthetic-vector') for k,v in data['observations'].items()}
        try:r=recalculate_strategy_preview(obs,data.get('user_weights'),ProfileKind(data.get('profile_kind','GENERAL_CORPORATE')))
        except ValueError:return {'state':'INVALID_INPUT'}
        out=wire(r)
        for axis in out['axes']:out['axes'][axis]['missing_factor_count']=r.axes[axis].missing_factor_count
        return out
    if op=='company_types':
        try:
            from investment_system.qgv.company_types import calculate_company_types
            from investment_system.qgv.type_config import compile_custom_config
        except ImportError:raise DependencyPending('TYPE_ENGINE_PENDING_MERGE') from None
        return calculate_company_types(metrics=data['metrics'],original_qgv=data['original_qgv'],config=compile_custom_config(data['config']))
    if op=='m3_sec':
        r=sec_adapter(data)
        return {'state':r.state,'reason_codes':list(r.reason_codes),'shares':r.shares.shares if r.shares else None,
            'basis_status':r.basis.basis_status if r.basis else None,
            'share_class_basis':r.basis.share_class_basis if r.basis else None,
            'listing_id':r.seed.listing_id if r.seed else None}
    if op=='m3_universe':
        from investment_system.universe.private_subset import UniverseReceipt,parse_universe_values,prepare_universe_price,compare_universe_market_cap,QualityConfig,SelectionConfig,select_verified_universe_top_n
        r=sec_adapter(data['sec']);values=data['values'];at=datetime.fromisoformat(data['sec']['as_of'].replace('Z','+00:00'))
        digest=sha256(json.dumps(values,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
        receipt=UniverseReceipt('GOOGLEFINANCE_PRIVATE_UNIVERSE',at,digest,'synthetic-vector',1,True)
        parsed=parse_universe_values(values,receipt,identity_lookup={data['sec']['code']:r.seed})
        checks=tuple(compare_universe_market_cap(row,r.shares,prepare_universe_price(row,r.basis,as_of=at),QualityConfig(.10,True)) for row in parsed.rows)
        selected=select_verified_universe_top_n(checks,SelectionConfig(data['n'],True),parsed=parsed)
        return {'rows':[{'state':c.state,'quality':c.quality,'reason_codes':list(c.reason_codes),'effective_cap':c.effective_cap,'relative_difference':c.relative_difference} for c in checks],
            'selection':{key:wire(getattr(selected,key)) for key in ('state','selection_status','requested_n','selected_n','verified_count','missing_count','selected_listing_ids','reason_codes')}}
    raise ValueError('UNKNOWN_OPERATION')


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser();p.add_argument('vectors');a=p.parse_args(argv)
    try:
        envelope=json.loads(Path(a.vectors).read_text())
        if envelope.get('synthetic') is not True:raise ValueError('SYNTHETIC_ONLY')
        results=[]
        for c in envelope['cases']:
            try:out=replay(c)
            except DependencyPending:out={'state':'DEPENDENCY_PENDING','reason':'TYPE_ENGINE_PENDING_MERGE'}
            results.append({'id':c['id'],'actual':out})
        print(json.dumps({'synthetic':True,'role':'REFERENCE_TEST_ONLY','results':results},allow_nan=False));return 0
    except Exception:
        print('SYNTHETIC_REFERENCE_INVALID');return 1


if __name__=='__main__':raise SystemExit(main())
