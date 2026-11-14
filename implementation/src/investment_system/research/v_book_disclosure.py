"""Attach reviewed retained BPS disclosure to existing V resume input.

The document claim does not certify a later valuation-date security/action chain.
"""
from copy import deepcopy
import hashlib
from .sector_qgv import timestamp,day
from .sector_qgv_v import component,input_issues,readiness
from .sector_qgv_registry import CATALOG


def connect(pack,claim,body,*,input_cutoff):
    if claim.get('schema_version')!='reviewed-common-bps-disclosure/1':raise ValueError('CLAIM_SCHEMA')
    if hashlib.sha256(body).hexdigest()!=claim['document_sha256']:raise ValueError('DOCUMENT_HASH')
    for k in ('source_locator','reviewer','accession','source_url','common_share_basis','common_attribution_evidence'):
        if not claim.get(k):raise ValueError('CLAIM_EVIDENCE:'+k)
    acquired=timestamp(claim['acquired_at']);reviewed=timestamp(claim['reviewed_at']);cutoff=timestamp(input_cutoff)
    if not acquired<=reviewed<=cutoff or cutoff<timestamp(pack['as_of']):raise ValueError('AVAILABILITY_CONTEXT')
    if day(claim['published_day'])>day(pack['valuation_date']) or day(claim['observed_day'])>day(pack['valuation_date']):raise ValueError('FUTURE_OBSERVATION')
    if claim.get('currency')!='USD' or claim.get('unit')!='USD/share' or claim.get('value') is None:raise ValueError('BOOK_UNIT_VALUE')
    out=deepcopy(pack);matches=[r for r in out['rows'] if r['issuer_id']==claim['issuer_id']]
    if not matches:raise ValueError('ISSUER_NOT_IN_RESUME')
    original=out['as_of'];out['as_of']=input_cutoff;out['snapshot']['as_of']=input_cutoff
    out['disclosure_review_context']=dict(original_input_cutoff=original,input_cutoff=input_cutoff,
        acquired_at=claim['acquired_at'],reviewed_at=claim['reviewed_at'],historical_system_available=False)
    for row in matches:
        if 'common_bp' not in row['selected_variants']:continue
        reference=claim['source_url']+'#sha256='+claim['document_sha256']+';'+claim['source_locator']
        x=component(dict(currency=claim['currency'],acquired_at=claim['acquired_at'],cik=claim['issuer_id']),
            'common_bps',claim['value'],'INSTANT',claim['observed_day'],reference,unit=claim['unit'])
        x.update(share_basis=claim['common_share_basis'],source_publication_day=claim['published_day'],
                 reviewed_at=claim['reviewed_at'],availability_basis='NEWLY_ACQUIRED_HISTORICAL_DISCLOSURE',
                 disclosure_claim=deepcopy(claim),valuation_date_identity='UNCONFIRMED',corporate_action_continuity='UNCONFIRMED')
        prior=row['inputs'].get('common_bps');row.setdefault('input_history',[]).append(dict(field='common_bps',previous=deepcopy(prior)))
        row['inputs']['common_bps']=x
        issues=input_issues('common_bps',x,CATALOG['common_bp']['inputs'][0],out,row['issuer_id'])
        if issues:raise ValueError('BOOK_INPUT_INVALID:'+','.join(issues))
    return out,readiness(out)
