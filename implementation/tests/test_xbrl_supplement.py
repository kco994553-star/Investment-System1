import copy
from datetime import date
import pytest
from investment_system.research.xbrl_supplement import supplement

FILING = {'accn': '0000000001-26-000001', 'filed': '2026-02-01', 'form': '10-K'}
PAYLOAD = {'cik': 1, 'facts': {}}

def xml(value='25', extra='', context_extra='', entity='0000000001', measure='iso4217:USD'):
    return f'''<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:g="http://fasb.org/us-gaap/2026" xmlns:iso4217="http://www.xbrl.org/2003/iso4217" xmlns:xbrli="http://www.xbrl.org/2003/instance">
    <context id="c"><entity><identifier scheme="http://www.sec.gov/CIK">{entity}</identifier>{context_extra}</entity><period><startDate>2025-01-01</startDate><endDate>2025-12-31</endDate></period></context>
    <unit id="u"><measure>{measure}</measure></unit>
    <g:OperatingIncomeLoss contextRef="c" unitRef="u" decimals="-6">{value}</g:OperatingIncomeLoss>{extra}</xbrl>'''.encode()

def test_missing_exact_fact_added_without_mutating_original_or_scaling_decimals():
    before = copy.deepcopy(PAYLOAD)
    data, audit = supplement(PAYLOAD, xml(), FILING, date(2026, 2, 2))
    fact = data['facts']['us-gaap']['OperatingIncomeLoss']['units']['USD'][0]
    assert fact == {'start': '2025-01-01', 'end': '2025-12-31', 'val': 25, **FILING}
    assert audit['added'] == 1 and audit['conflicts'] == []
    assert PAYLOAD == before

def test_conflict_or_duplicate_does_not_overwrite_source():
    data, _ = supplement(PAYLOAD, xml(), FILING, date(2026, 2, 2))
    duplicate, audit = supplement(data, xml(), FILING, date(2026, 2, 2))
    assert duplicate == data and audit['added'] == 0
    conflict, audit = supplement(data, xml('30'), FILING, date(2026, 2, 2))
    assert conflict == data and len(audit['conflicts']) == 1

@pytest.mark.parametrize('kwargs', [
    {'entity': '0000000002'},
    {'context_extra': '<segment><dimension>business</dimension></segment>'},
    {'measure': 'iso4217:EUR'},
    {'measure': 'bad:USD'},
])
def test_wrong_entity_dimensions_or_units_not_supplemented(kwargs):
    source = {'cik': 1, 'facts': {'us-gaap': {'Revenues': {'units': {'USD': []}}}}}
    data, audit = supplement(source, xml(**kwargs), FILING, date(2026, 2, 2))
    assert audit['added'] == 0 and data == source

def test_future_filing_and_custom_namespace_rejected():
    with pytest.raises(ValueError, match='FILING'):
        supplement(PAYLOAD, xml(), FILING, date(2026, 1, 1))
    custom = xml().replace(b'http://fasb.org/us-gaap/2026', b'http://issuer.example/us-gaap/2026')
    assert supplement(PAYLOAD, custom, FILING, date(2026, 2, 2))[1]['added'] == 0

def test_conflicting_facts_inside_instance_are_not_arbitrarily_selected():
    extra = '<g:OperatingIncomeLoss contextRef="c" unitRef="u">30</g:OperatingIncomeLoss>'
    data, audit = supplement(PAYLOAD, xml(extra=extra), FILING, date(2026, 2, 2))
    assert audit['added'] == 0 and len(audit['conflicts']) == 1
    assert data == PAYLOAD
