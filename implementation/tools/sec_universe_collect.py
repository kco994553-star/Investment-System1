#!/usr/bin/env python3
"""Explicit daily Universe shard entrypoint; local raw workspace only."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.providers.sec_collection import MAX_BODY_BYTES,SecCollectionError
from investment_system.providers.sec_universe_collection import universe_registry,daily_partition,UniverseSecClient,collect_partition


class SafeParser(argparse.ArgumentParser):
    def error(self,message):
        print('SEC_UNIVERSE SEC_UNIVERSE_CONFIG_INVALID');raise SystemExit(2)


def main(argv=None):
    p=SafeParser(description=__doc__)
    p.add_argument('--sec-ticker-exchange-json',required=True)
    p.add_argument('--shard-count',type=int,required=True)
    p.add_argument('--shard-index',type=int,required=True)
    p.add_argument('--output-dir',required=True)
    p.add_argument('--allow-live',action='store_true')
    args=p.parse_args(argv)
    if not args.allow_live:
        print('SEC_UNIVERSE LIVE_OPT_IN_REQUIRED');return 1
    try:
        with Path(args.sec_ticker_exchange_json).open('rb') as stream:body=stream.read(MAX_BODY_BYTES+1)
        registry=universe_registry(body)
        issuers=daily_partition(registry,shard_count=args.shard_count,shard_index=args.shard_index)
        client=UniverseSecClient(os.environ.get('SEC_USER_AGENT',''),registry=registry)
        root=Path(args.output_dir);root.mkdir(parents=True,exist_ok=True)
        manifest=[]
        def save(issuer,facts,sub,acquired):
            hashes=[sha256(b).hexdigest() for b in (facts,sub)]
            for digest,data in zip(hashes,(facts,sub)):
                target=root/(digest+'.json');temporary=root/(digest+'.part')
                temporary.write_bytes(data);temporary.replace(target)
            manifest.append({'cik':issuer.cik,'codes':list(issuer.codes),'acquired_at':acquired.isoformat(),
                'facts_sha256':hashes[0],'submissions_sha256':hashes[1],'status':'LIVE'})
        result=collect_partition(client,issuers,on_success=save)
        for index,code in result.failures:print(f'SEC_UNIVERSE_FAILURE company_index={index} code={code}')
        print(f'SEC_UNIVERSE collected={result.collected} failed={result.failed} unresolved_codes={registry.unresolved_code_count}')
        if result.all_failed:return 1
        output={'schema_version':1,'role':'RAW_LOCAL_WORKSPACE_ONLY','registry_sha256':registry.source_sha256,
            'shard_count':args.shard_count,'shard_index':args.shard_index,'companies':manifest,
            'failed_companies':result.failed,'unresolved_code_count':registry.unresolved_code_count}
        temp=root/'universe-shard-manifest.part';temp.write_text(json.dumps(output,allow_nan=False));temp.replace(root/'universe-shard-manifest.json')
        return 0
    except SecCollectionError as error:
        code=error.args[0] if error.args and error.args[0] in {'SEC_USER_AGENT_INVALID','SEC_UNIVERSE_INPUT_INVALID','SEC_UNIVERSE_CONFIG_INVALID','SEC_CONFIG_INVALID'} else 'SEC_UNIVERSE_FAILED'
        print('SEC_UNIVERSE '+code);return 1
    except Exception:
        print('SEC_UNIVERSE SEC_UNIVERSE_FAILED');return 1


if __name__=='__main__':raise SystemExit(main())
