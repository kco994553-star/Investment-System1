#!/usr/bin/env python3
"""Offline policy-impact build. stdout contains aggregate counts/error paths only."""
import argparse
import json
import os
import tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.policy_impact import build,Invalid

def main():
    p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    target=Path(a.output).resolve();tmp=None
    try:
        j=json.loads(Path(a.job).read_text());b=j.get('bundle',{})
        data_kind=j.get('state',{}).get('data_kind') if j.get('mode')=='fr-replay' else j.get('navigation',{}).get('data_kind') if j.get('mode')=='navigation' else b.get('data_kind')
        if data_kind!='SYNTHETIC' and any((d/'.git').exists() for d in [target.parent,*target.parents]):raise Invalid('PRIVATE_OUTPUT_REQUIRED','$')
        if j.get('mode')=='fr-replay':
            from investment_system.research.policy_impact.federal_register import replay
            result=replay(j['state'],j.get('responses',[]),through=j['through'],now=j['now'],settings=j.get('settings'),last_good=j.get('last_good'))
        elif j.get('mode')=='navigation':
            import hashlib
            from investment_system.research.policy_impact.navigation import project,project_bytes
            if 'view' in j and 'view_source' in j:raise Invalid('VIEW_INPUT_AMBIGUOUS','view')
            originals={}
            for spec in j.get('title_sources',[]):
                body=Path(spec['path']).read_bytes()
                if hashlib.sha256(body).hexdigest()!=spec['sha256']:raise Invalid('SOURCE_HASH','title_sources')
                originals[spec['sha256']]=body
            if 'view_source' in j:
                from investment_system.research.policy_impact.contract import shape
                spec=j['view_source'];shape(spec,['path','sha256'],'view_source')
                body=Path(spec['path']).read_bytes()
                if hashlib.sha256(body).hexdigest()!=spec['sha256']:raise Invalid('SOURCE_HASH','view_source')
                result=project_bytes(body,j['navigation'],j['as_of'],public=j.get('public',False),title_sources=originals)
            else:result=project(j['view'],j['navigation'],j['as_of'],public=j.get('public',False),title_sources=originals)
        else:result=build(b,j['company_ids'],j['as_of'],public=j.get('public',False),public_macro_ids=j.get('public_macro_ids',[]),previous=j.get('previous'),query_timezone=j.get('query_timezone','UTC'),watch_publication_permissions=j.get('watch_publication_permissions'))
        target.parent.mkdir(parents=True,exist_ok=True)
        fd,name=tempfile.mkstemp(prefix=target.name+'.',dir=target.parent);tmp=Path(name)
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,allow_nan=False,indent=2);f.write('\n')
        os.replace(tmp,target)
        if j.get('mode')=='navigation':summary={'status':'PROJECTED','titles':len(result['titles']),'news_links':len(result['news_links'])}
        elif j.get('mode')=='fr-replay':summary={'status':'REPLAYED','changes':result['changes'],'actual_http_requests':0}
        else:summary={'status':'BUILT','counts':{g:len(result['bundle'][g]) for g in ('sources','policies','exposures','hypotheses')},'historical_pit_eligible':False}
        print(json.dumps(summary));return 0
    except (Invalid,ValueError,KeyError,TypeError,OSError) as e:
        if tmp is not None and tmp.exists():tmp.unlink()
        print(json.dumps({'status':'FAILED','code':e.code if isinstance(e,Invalid) else 'INPUT_INVALID','path':e.path if isinstance(e,Invalid) else '$'}));return 2
if __name__=='__main__':raise SystemExit(main())
