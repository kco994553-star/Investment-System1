from copy import deepcopy
import hashlib
import pytest
from investment_system.research.v_book_disclosure import connect


def inputs():
    pack=dict(valuation_date='2026-11-04',as_of='2026-11-04T22:00:00Z',snapshot=dict(as_of='2026-11-04T22:00:00Z',members=['SYN'],rows=[]),
        rows=[dict(company_id='SYN',issuer_id='issuer',security_id=None,sector_id='FINANCIALS',accounting_template='INSURANCE',
                   inputs={},diagnostics={},selected_variants=['common_bp'])])
    body=b'synthetic disclosed common BPS'
    claim=dict(schema_version='reviewed-common-bps-disclosure/1',document_sha256=hashlib.sha256(body).hexdigest(),
        issuer_id='issuer',source_locator='synthetic page1 footnote4',reviewer='synthetic reviewer',accession='synthetic',
        source_url='https://example.invalid/synthetic',common_share_basis='COMMON_EXCLUDING_TRUST',
        common_attribution_evidence='synthetic common equity divided by common outstanding',value=25.87,currency='USD',unit='USD/share',
        observed_day='2026-09-30',published_day='2026-10-19',acquired_at='2026-11-13T23:06:25Z',reviewed_at='2026-11-14T00:00:00Z')
    return pack,claim,body


def test_new_acquisition_is_not_old_pit_or_price_ready():
    p,c,b=inputs();old=deepcopy(p);new,r=connect(p,c,b,input_cutoff=c['reviewed_at'])
    assert p==old and new['rows'][0]['inputs']['common_bps']['value']==25.87
    assert new['disclosure_review_context']['historical_system_available'] is False
    assert r['counts']['numerator_ready']==1 and r['counts']['price_only_ready']==0
    assert new['rows'][0]['inputs']['common_bps']['security_id'] is None


def test_hash_and_clock_rejected():
    p,c,b=inputs()
    with pytest.raises(ValueError,match='HASH'):connect(p,c,b+b'x',input_cutoff=c['reviewed_at'])
    with pytest.raises(ValueError,match='AVAILABILITY'):connect(p,c,b,input_cutoff=p['as_of'])
