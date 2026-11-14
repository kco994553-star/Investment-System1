from copy import deepcopy
from investment_system.research.qgv_555_held import held_input
from investment_system.research.qgv_555 import _usable


def test_raw_projection_preserves_formula_period_and_blocks_share_proof(monkeypatch):
    monkeypatch.setattr('investment_system.research.qgv_555_held._classification_valid',lambda r,s:True)
    row=dict(company_id='SYN:1',issuer_id='issuer-1',accounting_template='GENERAL',sector_id='INDUSTRIALS',observations={})
    snapshot=dict(rows=[row],members=['SYN:1'],as_of='2026-11-04T22:00:00Z',valuation_date='2026-11-04',universe_id='syn',universe_version='1',mapping_version='2')
    record=dict(cik='issuer-1',acquired_at='2026-11-04T20:00:00Z',calc_version='qgv2-calc/2026-10-23.1',
                state='LIVE',profile='GENERAL',metrics={'roic':.2,'eps_cagr_3y':.3},fiscal_year_end='2025-12-31')
    out=held_input(snapshot,[dict(sha256='a'*64,records={'SYN:1':record})],source_anchors=['synthetic-pin'])
    r=out['rows'][0]
    assert _usable(r,'roic',out)==(.2,'VALID')
    assert _usable(r,'eps_cagr_3y',out)==(None,'HISTORICAL_SHARE_BASIS_UNVERIFIED')
    assert r['metric_evidence']['roic']['period_end']=='2025-12-31'
    late=deepcopy(record);late.update(acquired_at='2026-11-05T00:00:00Z',metrics={'roic':.9})
    again=held_input(snapshot,[dict(sha256='a'*64,records={'SYN:1':record}),dict(sha256='b'*64,records={'SYN:1':late})],source_anchors=['synthetic-pin'])
    assert again['rows'][0]['metrics']['roic']==.2
