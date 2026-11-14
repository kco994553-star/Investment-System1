#!/usr/bin/env python3
"""Fixed SYNTHETIC listing examples; no source requests, prices or selection run."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.population_public_listing import build_listing, sheet_difference, retain_listing
from investment_system.research.sector_qgv import digest


def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()+b'\n'


def examples():
    day='2026-11-13';cutoff=day+'T22:00:00Z';codes=['NYSE:SYN0','NYSE:SYN1','NYSE:SYN2']
    meta=dict(source_kind='SYNTHETIC_CURRENT',data_kind='SYNTHETIC',population_id='SYNTHETIC:CURRENT',
        population_version='1',basis_date=day,apply_at='2026-11-16T14:30:00Z',mapping_day=day,input_cutoff=cutoff,null_reasons={})
    def record(code,issuer,security):
        return dict(company_id=code,issuer_id=issuer,issuer_status='VERIFIED',issuer_refs=['SYNTHETIC:ISSUER'],
            security_id=security,identifier_type='SYNTHETIC_FIXED_SECURITY_ID',security_status='VERIFIED',
            security_refs=['SYNTHETIC:SECURITY'],share_class_id='SYNTHETIC:CLASS:'+code,
            representative_status='VERIFIED',representative_refs=['SYNTHETIC:REPRESENTATIVE'],
            google_symbol=code,google_status='VERIFIED',google_refs=['SYNTHETIC:GOOGLE'],
            record_id='SYNTHETIC:RECORD:'+code,valid_from='2026-01-01',valid_to=None,available_at=cutoff)
    links=[record(c,'SYNTHETIC:ISSUER:'+str(i//2),'SYNTHETIC:SECURITY:'+str(i)) for i,c in enumerate(codes)]
    links[1]['representative_status']='UNCONFIRMED';links[1]['google_status']='UNCONFIRMED'
    source=dict(schema='universe-codes/1',codes=codes);body=encoded(source)
    request=dict(source_payload=source,metadata=meta,links=links,expected_source_sha256=hashlib.sha256(body).hexdigest(),expected_links_hash=digest(links))
    normal=build_listing(body,metadata=meta,links=links,expected_source_sha256=request['expected_source_sha256'],expected_links_hash=request['expected_links_hash'])
    old_codes=['NYSE:SYN0','NYSE:SYN9'];saved=dict(population_id=meta['population_id'],population_version='old',members_hash=digest(sorted(old_codes)))
    old_review=sheet_difference(normal,old_codes,saved_identity=saved,expected_listing_hash=normal['list_hash'])
    unversioned=sheet_difference(normal,codes,saved_identity=None,expected_listing_hash=normal['list_hash'])
    retained=retain_listing(normal,expected_previous_hash=normal['list_hash'],failure='SOURCE_READ_FAILED')
    fixture=Path(__file__).resolve().parents[1]/'tests/fixtures/qgv555-preview/top500-result.json'
    raw=fixture.read_bytes();selected=json.loads(raw)
    if not selected['population_id'].startswith('synthetic-'):raise ValueError('SYNTHETIC_SELECTION_FIXTURE_REQUIRED')
    top_meta={**meta,'source_kind':'TOP500_RESEARCH_CANDIDATE','population_id':selected['population_id'],
        'population_version':selected['population_version'],'basis_date':selected['evaluation_day'],
        'apply_at':selected['apply_at'],'mapping_day':selected['evaluation_day'],'input_cutoff':selected['input_cutoff']}
    top_links=[record('NYSE:SYN'+str(i),r['issuer_id'],r['representative_security_id']) for i,r in enumerate(selected['members'])]
    for r in top_links:r['available_at']=selected['input_cutoff']
    top=build_listing(raw,metadata=top_meta,links=top_links,expected_source_sha256=hashlib.sha256(raw).hexdigest(),expected_links_hash=digest(top_links))
    return dict(schema_version='synthetic-population-listing-examples/1',data_kind='SYNTHETIC',cases=[
        dict(case='confirmed_synthetic_membership',request=request,result=normal),
        dict(case='old_sheet',sheet_codes=old_codes,saved_identity=saved,result=old_review),
        dict(case='matching_unversioned_sheet',sheet_codes=codes,saved_identity=None,result=unversioned),
        dict(case='failed_refresh',expected_previous_hash=normal['list_hash'],result=retained),
        dict(case='top500_candidate',source_fixture='implementation/tests/fixtures/qgv555-preview/top500-result.json',
             source_sha256=hashlib.sha256(raw).hexdigest(),metadata=top_meta,links=top_links,result=top)])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    data=encoded(examples());path=a.output/'examples.json'
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(data)
    manifest=dict(schema_version='synthetic-population-listing-manifest/1',data_kind='SYNTHETIC',files=[dict(path=path.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())])
    with os.fdopen(os.open(a.output/'manifest.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(encoded(manifest))
    print('SYNTHETIC_POPULATION_EXAMPLES_WRITTEN')


if __name__=='__main__':main()
