#!/usr/bin/env python3
"""Additional producer-made synthetic cases; existing pinned fixture unchanged."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from investment_system.research.company_ownership import normalize_packet, company_view, merge_update, json_bytes, digest

ROOT=Path(__file__).resolve().parents[1]/'docs/research/company_ownership'


def generate():
    original=(ROOT/'synthetic.json').read_bytes();base=json.loads(original)
    cases={c['case_id']:c for c in base['cases']}
    identity=base['identity_document_utf8'].encode();artifacts={h:b.encode() for h,b in base['artifacts_utf8'].items()}
    result=[]
    def append(name,p,q,note,extra=None,attempt=None):
        a={**artifacts,**(extra or {})};normalized=normalize_packet(p,identity,a)
        view=company_view(normalized,**q)
        c=dict(case_id=name,input=p,query=q,artifacts_utf8={h:b.decode() for h,b in (extra or {}).items()},
               expected_view=view,expected_view_sha256=digest(view),expected_behavior=note)
        if attempt:
            merged=merge_update(normalized,None,outcome=attempt,attempted_at='2026-01-06T12:00:00Z')
            assert json_bytes(merged['dataset'])==json_bytes(normalized)
            c['refresh']=dict(attempt=merged['attempt'],retained_dataset_sha256=digest(normalized),retained_view_sha256=digest(view),
                unchanged_generated_at=view['generated_at'],unchanged_last_success_at=view['collection']['last_success_at'])
        result.append(c)
    def fresh():
        c=deepcopy(cases['direct_ownership_and_parent']);return c['input'],c['query']
    def source(p,text,kind=None):
        raw=('<p>'+text+'</p>').encode();h=hashlib.sha256(raw).hexdigest()
        p['evidence'][0].update(artifact_hash=h,excerpt=text)
        if kind:p['evidence'][0]['source_kind']=kind
        return {h:raw}
    p,q=fresh();q['entity_id']='SYN-B'
    p['collection']['target_entity_ids']+=['SYN-B'];p['collection']['reviewed_entity_ids']+=['SYN-B']
    append('incoming_holder',p,q,'Same source/target and relationship IDs as outgoing; centre B receives INCOMING, not a reversed assertion.')
    p,q=fresh();p['assertions']=p['assertions'][:1];p['assertions'][0].update(directness='INDIRECT',statement='Synthetic A indirectly owns 60 percent of Class A of B; intermediate chain is undisclosed.')
    a=source(p,'Synthetic A indirectly owns approximately 60 percent of Class A of B; intermediate chain is undisclosed.')
    append('indirect_ownership',p,q,'INDIRECT is an observed claim; no intermediate entity or multiplied economic ratio is inferred.',a)
    p,q=fresh();p['assertions']=p['assertions'][:1]
    claim=p['assertions'][0];claim.update(capacity='INVESTMENT_DISCRETION',statement='Synthetic manager A reports managed holdings of B, not a corporate investment or control claim.')
    claim['observations'][0].update(metric='MANAGED_HOLDINGS')
    a=source(p,'Synthetic manager A reports investment discretion over approximately 60 percent of Class A of B; this is not corporate beneficial ownership.','FORM_13F')
    append('13f_investment_discretion',p,q,'Display in managed holdings; never parent/subsidiary or corporate investment.',a)
    p,q=fresh();p['assertions']=[]
    p['collection'].update(completeness='COMPLETE',zero_relationships_evidence_ids=['e1'],zero_observed_on='2025-12-31',scope='Synthetic reviewed subsidiary list at 2025-12-31')
    a=source(p,'Synthetic A explicitly reports no subsidiaries in its reviewed list at 2025-12-31.')
    append('verified_zero_in_scope',p,q,'Zero is explicit evidence only in this dated subsidiary scope; no claim about all ownership.',a)
    p,q=fresh();p['collection']['completeness']='COMPLETE'
    append('reviewed_scope',p,q,'REVIEWED_SCOPE: complete within the declared review scope, not a whole-market census.')
    for case in ('not_collected','not_found_in_reviewed_scope','filter_empty'):
        c=deepcopy(cases[case]);append(case,c['input'],c['query'],c['expected_behavior'])
    for outcome in ('FAILED','PARTIAL','PARSE_FAILED'):
        p,q=fresh();append('refresh_'+outcome.lower(),p,q,'Separate attempt receipt; retain old dataset/view bytes and original success/generated times. No inline arbitrary error text.',attempt=outcome)
    # NOT_COLLECTED is query-centre review status, not a denial of incoming evidence.
    p,q=fresh();q['entity_id']='SYN-B'
    append('incoming_centre_not_reviewed',p,q,'Incoming evidence can exist while the queried centre itself has not had a dedicated collection pass.')
    return dict(schema_version='company-ownership-consumer-examples/1',data_kind='SYNTHETIC',
                original_fixture_sha256=hashlib.sha256(original).hexdigest(),identity_document_utf8=base['identity_document_utf8'],
                artifacts_utf8=base['artifacts_utf8'],cases=result)


if __name__=='__main__':
    (ROOT/'consumer-synthetic.json').write_bytes(json_bytes(generate()))
