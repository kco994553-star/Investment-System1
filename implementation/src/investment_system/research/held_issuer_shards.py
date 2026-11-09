"""Fixed-route sharding of already verified issuer projections for Main."""
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import re
from .classification_counts import reference, require, MAX_BYTES
from .held_issuer_delivery import descriptor,encode,verify_delivery
from .sector_qgv import digest


def shard_delivery(files, summary, summary_ref, *, producer_sha):
    original=verify_delivery(files)
    require(re.fullmatch('[0-9a-f]{40}',producer_sha) is not None,'PRODUCER_SHA_REQUIRED')
    scope=summary['calculation_counts']['scopes']['held_financial_subsample']
    context=original['context']
    for key in ('valuation_date','population','scoring_population','versions','classification','result_identity'):
        require(scope[key]==context[key],'SUMMARY_CONTEXT_MISMATCH')
    identity={'summary':reference(summary_ref),'valuation_date':context['valuation_date'],'context':context,'producer_sha':producer_sha}
    ih=digest(identity);kind=original['data_kind'];out={};groups=defaultdict(list)
    rows=[r for n in original['indexes'] for r in json.loads(files[n])['rows']]
    for row in rows:
        key=hashlib.sha256(row['issuer_id'].encode()).hexdigest()[:2]
        groups[key].append(json.loads(files[row['detail']['path']]))
    for key,details in sorted(groups.items()):
        name='expanded-detail/'+key+'.json'
        out[name]=encode({'schema_version':'held-issuer-shard/1','data_kind':kind,'identity':identity,'identity_hash':ih,'shard_key':key,
                          'issuers':sorted(details,key=lambda r:r['issuer_id'])})
        require(len(out[name])<=MAX_BYTES,'SHARD_BYTE_LIMIT_REQUIRES_NEW_AGREED_LAYOUT')
    index=[]
    for original_row in rows:
        row=deepcopy(original_row);key=hashlib.sha256(row['issuer_id'].encode()).hexdigest()[:2];name='expanded-detail/'+key+'.json'
        row['shard_key']=key;row['detail']=descriptor(name,out[name]);index.append(row)
    out['expanded-index.json']=encode({'schema_version':'held-issuer-search/1','data_kind':kind,'identity':identity,'identity_hash':ih,'rows':index})
    coverage=json.loads(files['coverage.json']);coverage['identity']=identity;coverage['identity_hash']=ih;out['coverage.json']=encode(coverage)
    manifest={'schema_version':'held-issuer-sharded/1','data_kind':kind,'identity':identity,'identity_hash':ih,
              'index':'expanded-index.json','shards':sorted(groups),'issuer_count':len(index),'max_file_bytes':MAX_BYTES,
              'routes':{'index_part':'expanded_index','detail_part':'expanded_detail','shard_pattern':'^[0-9a-f]{2}$'},
              'files':[descriptor(k,b) for k,b in sorted(out.items())]}
    out['manifest.json']=encode(manifest);verify_shards(out);return out


def verify_shards(files):
    m=json.loads(files['manifest.json']);require(m['schema_version']=='held-issuer-sharded/1','SHARD_SCHEMA')
    require(m['identity_hash']==digest(m['identity']),'IDENTITY_HASH_MISMATCH')
    entries={r['path']:r for r in m['files']}
    require(len(entries)==len(m['files']) and set(files)==set(entries)|{'manifest.json'},'FILE_SET_MISMATCH')
    require(all(len(b)<=MAX_BYTES for b in files.values()),'DELIVERY_BYTE_LIMIT')
    require(len(m['shards'])==len(set(m['shards'])) and all(re.fullmatch('[0-9a-f]{2}',s) for s in m['shards']),'SHARD_KEY_INVALID')
    require(set(entries)=={'expanded-index.json','coverage.json'}|{'expanded-detail/'+s+'.json' for s in m['shards']},'SHARD_FILE_SET')
    decoded={}
    for name,d in entries.items():
        require(descriptor(name,files[name])==d,'DELIVERY_HASH_MISMATCH');v=json.loads(files[name]);decoded[name]=v
        require(v['identity']==m['identity'] and v['identity_hash']==m['identity_hash'] and v['data_kind']==m['data_kind'],'IDENTITY_MISMATCH')
    idx=decoded['expanded-index.json'];require(idx['schema_version']=='held-issuer-search/1','INDEX_SCHEMA')
    details={}
    for key in m['shards']:
        value=decoded['expanded-detail/'+key+'.json'];require(value['schema_version']=='held-issuer-shard/1' and value['shard_key']==key,'SHARD_SCHEMA')
        for d in value['issuers']:
            i=d['issuer_id'];require(i not in details and hashlib.sha256(i.encode()).hexdigest()[:2]==key,'SHARD_MEMBERSHIP_MISMATCH');details[i]=(key,d)
            require(d['context']==m['identity']['context'] and d['context_hash']==digest(d['context']),'DETAIL_CONTEXT_MISMATCH')
    ids=set()
    for row in idx['rows']:
        i=row['issuer_id'];require(i not in ids and i in details,'INDEX_MEMBER_MISMATCH');ids.add(i);key,d=details[i]
        require(row['shard_key']==key and row['detail']==entries['expanded-detail/'+key+'.json'],'DETAIL_REF_MISMATCH')
        require(row['analysis_row_id']==d['analysis_row_id'] and row['observed_names']==d['observed_names'] and
                row['operating_code_rows']==d['operating_code_rows'] and row['calculation_status']==d['calculation']['status'] and
                row['observed_tickers']==sorted({o['observed_ticker'] for o in d['catalog_observations']}) and
                all(row['classification'][k]==d['classification'][k] for k in ('sector','accounting','industry')),'INDEX_DETAIL_MISMATCH')
    require(ids==set(details) and len(ids)==m['issuer_count']==m['identity']['context']['population']['denominator'],'DENOMINATOR_MISMATCH')
    return m
