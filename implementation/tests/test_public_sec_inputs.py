"""Only synthetic SEC observations; no live collection or credential lookup."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest
from investment_system.markets.us import US_LISTINGS

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
from public_sec_inputs import build_public_inputs, collect_public_inputs, require_public_inputs
from pages_artifact_guard import scan_artifact, validate_pages_tar
from investment_system.product.web_mvp import build, repository_bundle


def raw(company):
    cik = US_LISTINGS[company]['cik']
    fact = {'end': '2025-12-31', 'val': 100, 'accn': '0000000001-26-000001', 'fy': 2025,
            'fp': 'FY', 'form': '10-K', 'filed': '2026-02-01'}
    return ({'cik': int(cik), 'facts': {'dei': {'EntityCommonStockSharesOutstanding':
            {'label': 'discarded', 'units': {'shares': [fact]}}},
            'us-gaap': {'Price': {'units': {'USD': [{'val': 987654321}]}}}},
            'private_value': 'never publish'}, {'cik': cik, 'filings': {'recent': {
            'accessionNumber': ['0000000001-26-000001'], 'form': ['10-K'],
            'filingDate': ['2026-02-01'], 'reportDate': ['2025-12-31'],
            'acceptanceDateTime': ['2026-02-01T12:00:00Z']}}})


def observations():
    return [(company, *(json.dumps(x).encode() for x in raw(company)), '2026-02-02T12:00:00Z')
            for company in sorted(US_LISTINGS)]


def test_projection_is_reported_shares_and_filing_metadata_only():
    result = build_public_inputs(observations())
    require_public_inputs(result)
    text = json.dumps(result)
    assert '987654321' not in text and 'never publish' not in text and 'label' not in text
    assert len(result['companies']) == 17
    assert result['companies'][0]['reported_shares'][0]['val'] == 100
    assert result['scope'] == 'US_TARGET17_REPORTED_SEC_ONLY'


@pytest.mark.parametrize('mutation', ['price', 'derived', 'extra', 'issuer', 'url', 'negative', 'bool', 'date', 'missing', 'duplicate', 'unit', 'accession'])
def test_public_contract_rejects_contamination_and_incomplete_identity(mutation):
    p = build_public_inputs(observations()); row = p['companies'][0]
    if mutation == 'price': row['price'] = 100
    elif mutation == 'derived': row['Q_score'] = 10
    elif mutation == 'extra': p['user_agent'] = 'private'
    elif mutation == 'issuer': row['cik'] = '0000000000'
    elif mutation == 'url': row['sources']['companyfacts']['url'] = 'https://other.test/data'
    elif mutation == 'negative': row['reported_shares'][0]['val'] = -1
    elif mutation == 'bool': row['reported_shares'][0]['val'] = True
    elif mutation == 'date': row['reported_shares'][0]['filed'] = '2026-02-30'
    elif mutation == 'missing': p['companies'].pop()
    elif mutation == 'duplicate': p['companies'][1] = copy.deepcopy(row)
    elif mutation == 'unit': row['reported_shares'][0]['unit'] = 'USD'
    elif mutation == 'accession': row['filings'][0]['accession'] = 'private'
    with pytest.raises(ValueError, match='SEC_PUBLIC_INPUT_INVALID'): require_public_inputs(p)


def test_raw_issuer_duplicate_keys_and_nonfinite_inputs_fail_without_payload_output():
    for mode in ['issuer', 'duplicate', 'nonfinite']:
        rows = observations()
        if mode == 'issuer':
            value = json.loads(rows[0][1]); value['cik'] = 0; bad = json.dumps(value).encode()
        elif mode == 'duplicate': bad = b'{"cik":1,"cik":2}'
        else: bad = b'{"cik":NaN}'
        rows[0] = (rows[0][0], bad, *rows[0][2:])
        with pytest.raises(ValueError, match='SEC_PUBLIC_INPUT_INVALID'): build_public_inputs(rows)


def test_collector_reuses_codex2_client_and_does_not_publish_after_failure(tmp_path, capsys):
    from datetime import datetime, timezone
    class Client:
        def __init__(self, user_agent): assert user_agent == 'synthetic setting'
        def collect(self, company, cik):
            assert cik == US_LISTINGS[company]['cik']
            return *(json.dumps(x).encode() for x in raw(company)), datetime(2026, 2, 2, 12, tzinfo=timezone.utc)
    out = tmp_path / 'sec-public-inputs.json'
    collect_public_inputs(out, environ={'SEC_USER_AGENT': 'synthetic setting'}, client_factory=Client)
    assert out.is_file(); before = out.read_bytes()
    class Failing(Client):
        def collect(self, company, cik): raise OSError('private provider message')
    with pytest.raises(ValueError, match='SEC_COLLECTION_FAILED'):
        collect_public_inputs(out, environ={'SEC_USER_AGENT': 'synthetic setting'}, client_factory=Failing)
    assert out.read_bytes() == before and capsys.readouterr().out == ''


def test_optional_public_sec_file_is_semantically_guarded_in_directory_and_tar(tmp_path):
    import io, tarfile
    site = tmp_path / 'site'; build(site, bundle=repository_bundle())
    path = site / 'sec-public-inputs.json'; path.write_text(json.dumps(build_public_inputs(observations())))
    assert scan_artifact(site)['pages_artifact_guard'] == 'PASS'
    archive = tmp_path / 'artifact.tar'
    with tarfile.open(archive, 'w', format=tarfile.GNU_FORMAT) as tar:
        for file in sorted(site.iterdir()):
            payload = file.read_bytes(); info = tarfile.TarInfo('./' + file.name); info.size = len(payload); info.mode = 0o644
            tar.addfile(info, io.BytesIO(payload))
    assert validate_pages_tar(archive)['pages_artifact_guard'] == 'PASS'
    p = json.loads(path.read_text()); p['companies'][0]['price'] = 1; path.write_text(json.dumps(p))
    assert scan_artifact(site)['pages_artifact_guard'] == 'FAIL'


def test_daily_workflow_is_default_branch_only_and_checks_exact_public_directory():
    source = (TOOLS.parents[1] / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    assert "cron: '17 22 * * *'" in source
    assert "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)" in source
    assert 'SEC_USER_AGENT: ${{ secrets.SEC_USER_AGENT }}' in source
    assert "needs.dependency.outputs.ready == 'true'" in source
    assert 'providers/sec_collection.py' in source
    assert 'needs: dependency' in source
    for forbidden in ['actions/cache', 'upload-artifact@', 'git push', 'git commit', 'always()', 'TIINGO', 'CLOUDFLARE', 'GOOGLE']:
        assert forbidden not in source
    assert 'pages_artifact_guard.py' in source and 'test_public_sec_inputs.py' in source
    assert source.index('pages_artifact_guard.py') < source.index('actions/upload-pages-artifact')
    assert source.index('private_trades_browser_test.js') < source.index('actions/upload-pages-artifact')
    assert 'path: ${{ runner.temp }}/public-cockpit' in source and 'needs: build' in source


def test_missing_secret_stops_before_factory_or_requests(tmp_path):
    def forbidden(_setting):
        raise AssertionError('factory must not run without the named Secret')
    for value in (None, '', '   '):
        with pytest.raises(ValueError, match='SEC_USER_AGENT_MISSING'):
            collect_public_inputs(tmp_path / 'inputs.json', environ={'SEC_USER_AGENT': value}, client_factory=forbidden)
    assert not (tmp_path / 'inputs.json').exists()

@pytest.mark.parametrize('code',['SEC_USER_AGENT_INVALID','SEC_TRANSPORT_FAILED','SEC_HTTP_403','SEC_HTTP_429'])
def test_fixed_collection_codes_survive_without_arbitrary_values(tmp_path,code):
    from investment_system.providers.sec_collection import SecCollectionError
    class Failed:
        def __init__(self,_):raise SecCollectionError(code)
    with pytest.raises(ValueError,match=code):collect_public_inputs(tmp_path/'out.json',environ={'SEC_USER_AGENT':'synthetic setting'},client_factory=Failed)


def test_partial_failure_keeps_other_companies_and_records_only_fixed_diagnostics(tmp_path):
    from investment_system.providers.sec_collection import SecCollectionError
    from datetime import datetime,timezone
    first=sorted(US_LISTINGS)[0]
    class Client:
        def __init__(self,_):pass
        def collect(self,company,cik):
            if company==first:raise SecCollectionError('SEC_HTTP_403',stage='fetch',http_status=403)
            return *(json.dumps(x).encode() for x in raw(company)),datetime(2026,2,2,12,tzinfo=timezone.utc)
    p=tmp_path/'out.json';result=collect_public_inputs(p,environ={'SEC_USER_AGENT':'synthetic setting'},client_factory=Client)
    payload=json.loads(p.read_text());require_public_inputs(payload)
    assert payload['schema']=='public-sec-reported-inputs/3' and result['failed_companies']==1
    assert payload['companies'][0]['status']=='NOT_AVAILABLE'
    assert result['diagnostics']==[{'company_index':1,'stage':'fetch','code':'SEC_HTTP_403','http_status':403}]
    assert len(payload['companies'])==17 and all(x['status']=='LIVE' for x in payload['companies'][1:])


def test_parse_and_normalize_failures_have_company_stage_and_later_rows_continue(tmp_path):
    from datetime import datetime,timezone
    from investment_system.providers.sec_collection import SecCollectionError
    ids=sorted(US_LISTINGS)
    class Client:
        def __init__(self,_):pass
        def collect(self,company,cik):
            if company==ids[0]:raise SecCollectionError('SEC_JSON_INVALID',stage='parse')
            x=raw(company)
            if company==ids[1]:x[1]['filings']['recent']['reportDate']=[]
            return *(json.dumps(v).encode() for v in x),datetime(2026,2,2,12,tzinfo=timezone.utc)
    result=collect_public_inputs(tmp_path/'out.json',environ={'SEC_USER_AGENT':'synthetic setting'},client_factory=Client)
    assert result['failed_companies']==1
    assert [x['stage'] for x in result['diagnostics']]==['parse']
    assert [x['company_index'] for x in result['diagnostics']]==[1]
    assert result['exclusions']==[{'company_index':2,'code':'FILING_SCHEMA_INVALID','count':1}]


def test_all_failures_preserve_previous_file_and_cli_fixed_output(tmp_path,capsys,monkeypatch):
    import public_sec_inputs as module
    from investment_system.providers.sec_collection import SecCollectionError
    class Client:
        def __init__(self,_):pass
        def collect(self,*_):raise SecCollectionError('SEC_HTTP_429',http_status=429)
    p=tmp_path/'out.json';p.write_text('previous')
    with pytest.raises(ValueError) as caught:collect_public_inputs(p,environ={'SEC_USER_AGENT':'synthetic setting'},client_factory=Client)
    assert p.read_text()=='previous' and caught.value.failed_companies==17
    def fail(_):raise caught.value
    monkeypatch.setattr(module,'collect_public_inputs',fail)
    assert module.main(['--live','--output',str(p)])==1
    out=capsys.readouterr().out
    assert 'company_index=1 stage=fetch code=SEC_HTTP_429 http_status=429' in out
    assert 'failed_companies=17' in out and 'synthetic setting' not in out


def test_malicious_error_text_never_becomes_public_diagnostic(tmp_path):
    from investment_system.providers.sec_collection import SecCollectionError
    class Client:
        def __init__(self,_):raise SecCollectionError('private arbitrary sentinel')
    with pytest.raises(ValueError) as caught:collect_public_inputs(tmp_path/'out.json',environ={'SEC_USER_AGENT':'synthetic setting'},client_factory=Client)
    assert str(caught.value)=='SEC_COLLECTION_FAILED' and 'sentinel' not in repr(caught.value.diagnostics)


def test_partial_payload_still_passes_guard_and_cannot_hide_values_in_na(tmp_path):
    from datetime import datetime,timezone
    from investment_system.providers.sec_collection import SecCollectionError
    class Client:
        def __init__(self,_):pass
        def collect(self,company,cik):
            if company==sorted(US_LISTINGS)[0]:raise SecCollectionError('SEC_HTTP_403',http_status=403)
            return *(json.dumps(x).encode() for x in raw(company)),datetime(2026,2,2,12,tzinfo=timezone.utc)
    site=tmp_path/'site';build(site,bundle=repository_bundle())
    p=site/'sec-public-inputs.json';collect_public_inputs(p,environ={'SEC_USER_AGENT':'synthetic setting'},client_factory=Client)
    assert scan_artifact(site)['pages_artifact_guard']=='PASS'
    payload=json.loads(p.read_text());payload['companies'][0]['message']='private sentinel'
    with pytest.raises(ValueError):require_public_inputs(payload)


def collected_variant(tmp_path,mutate):
    from datetime import datetime,timezone
    class Client:
        def __init__(self,_):pass
        def collect(self,company,cik):
            value=raw(company)
            if company=='asml':mutate(*value)
            return *(json.dumps(v).encode() for v in value),datetime(2026,2,2,12,tzinfo=timezone.utc)
    output=tmp_path/'inputs.json'
    result=collect_public_inputs(output,environ={'SEC_USER_AGENT':'synthetic setting'},client_factory=Client)
    return result,json.loads(output.read_text())


def ifrs_only(facts,subs):
    fact=facts['facts'].pop('dei')['EntityCommonStockSharesOutstanding']['units']['shares'][0]
    fact['form']='20-F';fact['fp']=None;fact['frame']=None
    facts['facts']['ifrs-full']={'NumberOfSharesOutstanding':{'units':{'shares':[fact]}},
        'WeightedAverageNumberOfSharesOutstandingBasic':{'units':{'shares':[dict(fact,val=999)]}},
        'NumberOfSharesIssued':{'units':{'shares':[dict(fact,val=888)]}}}
    subs['filings']['recent']['form']=['20-F']


def test_ifrs_outstanding_shares_and_20f_nullable_optional_metadata(tmp_path):
    result,payload=collected_variant(tmp_path,ifrs_only)
    row=next(r for r in payload['companies'] if r['company_id']=='asml')
    assert result['failed_companies']==0 and len(row['reported_shares'])==1
    fact=row['reported_shares'][0]
    assert (fact['namespace'],fact['concept'],fact['form'],fact['val'])==('ifrs-full','NumberOfSharesOutstanding','20-F',100)
    assert 'fp' not in fact and 'frame' not in fact
    assert row['filings'][0]['form']=='20-F'
    require_public_inputs(payload)


def test_ifrs_public_payload_is_independently_guarded(tmp_path):
    result,payload=collected_variant(tmp_path,ifrs_only)
    site=tmp_path/'site';build(site,bundle=repository_bundle())
    (site/'sec-public-inputs.json').write_text(json.dumps(payload))
    assert scan_artifact(site)['pages_artifact_guard']=='PASS'
    text=json.dumps(payload)
    assert 'WeightedAverageNumber' not in text and 'NumberOfSharesIssued' not in text


@pytest.mark.parametrize('mutation,code',[
    (lambda f,s:f['facts'].pop('dei'),'SEC_SHARE_CONCEPT_MISSING'),
    (lambda f,s:f['facts']['dei']['EntityCommonStockSharesOutstanding'].update(units={'USD':[]}),'SEC_SHARE_UNIT_MISMATCH'),
    (lambda f,s:f['facts']['dei']['EntityCommonStockSharesOutstanding']['units'].update(shares='private sentinel'),'SEC_NO_ELIGIBLE_SHARE_FACTS'),
    (lambda f,s:f['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0].update(val=-1),'SEC_NO_ELIGIBLE_SHARE_FACTS'),
    (lambda f,s:f['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0].update(end='2025-02-30'),'SEC_NO_ELIGIBLE_SHARE_FACTS'),
    (lambda f,s:f['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0].update(filed='2026-02-03'),'SEC_NO_ELIGIBLE_SHARE_FACTS'),
    (lambda f,s:f['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0].update(accn='private sentinel'),'SEC_NO_ELIGIBLE_SHARE_FACTS'),
    (lambda f,s:f['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0].update(fp='private sentinel'),'SEC_NO_ELIGIBLE_SHARE_FACTS'),
])
def test_normalize_fixed_specific_reasons_partial_success_no_source_values(tmp_path,mutation,code):
    result,payload=collected_variant(tmp_path,mutation)
    assert result['failed_companies']==1
    assert result['diagnostics']==[{'company_index':3,'stage':'normalize','code':code,'http_status':None}]
    row=next(r for r in payload['companies'] if r['company_id']=='asml')
    assert row['status']=='NOT_AVAILABLE' and row['reason_codes']==[code]
    assert 'sentinel' not in json.dumps(payload)
    require_public_inputs(payload)


def test_all_normalization_failures_keep_specific_code_and_prior_file(tmp_path):
    from datetime import datetime,timezone
    class Client:
        def __init__(self,_):pass
        def collect(self,company,cik):
            values=raw(company);values[0]['facts'].pop('dei')
            return *(json.dumps(x).encode() for x in values),datetime(2026,2,2,12,tzinfo=timezone.utc)
    output=tmp_path/'inputs.json';output.write_text('old')
    with pytest.raises(ValueError,match='SEC_SHARE_CONCEPT_MISSING') as caught:
        collect_public_inputs(output,environ={'SEC_USER_AGENT':'synthetic setting'},client_factory=Client)
    assert caught.value.failed_companies==17 and output.read_text()=='old'


def bad_and_good(facts,subs):
    rows=facts['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares']
    valid=rows[0]
    rows.extend([dict(valid,form='S-1'),dict(valid,end='2025-02-30'),dict(valid,val=-1)])


def test_bad_fact_rows_excluded_and_valid_company_retained(tmp_path):
    result,payload=collected_variant(tmp_path,bad_and_good)
    row=next(r for r in payload['companies'] if r['company_id']=='asml')
    assert result['failed_companies']==0 and row['status']=='LIVE' and len(row['reported_shares'])==1
    assert row['excluded_fact_counts']=={'FORM_NOT_ALLOWED':1,'DATE_INVALID':1,'VALUE_INVALID':1}
    assert payload['schema']=='public-sec-reported-inputs/3'


@pytest.mark.parametrize('form',['10-KT','10-QT','10-KT/A','10-QT/A'])
def test_transition_form_share_facts_are_preserved_without_converting_form(tmp_path,form):
    def change(f,s):
        f['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0]['form']=form
        s['filings']['recent']['form']=[form]
    result,payload=collected_variant(tmp_path,change)
    row=next(r for r in payload['companies'] if r['company_id']=='asml')
    assert result['failed_companies']==0 and row['reported_shares'][0]['form']==form and row['filings'][0]['form']==form


def test_explicit_class_split_excluded_annotated_never_summed(tmp_path):
    def change(f,s):
        rows=f['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares']
        valid=rows[0];rows.extend([dict(valid,val=40,dimensions={'us-gaap:StatementClassOfStockAxis':'issuer:ClassAMember'}),dict(valid,val=60,dimensions={'us-gaap:StatementClassOfStockAxis':'issuer:ClassBMember'})])
    result,payload=collected_variant(tmp_path,change)
    row=next(r for r in payload['companies'] if r['company_id']=='asml')
    assert result['failed_companies']==0 and len(row['reported_shares'])==1 and row['reported_shares'][0]['val']==100
    assert row['share_class_basis']=='UNCONFIRMED' and row['share_class_notice']=='SHARE_CLASS_BASIS' and row['excluded_fact_counts']=={'CLASS_SPLIT':2}


def test_numeric_conflict_is_not_share_class_proof_and_conflicting_rows_not_selected(tmp_path):
    def change(f,s):
        rows=f['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares']
        valid=rows[0];rows.append(dict(valid,val=200))
        rows.append(dict(valid,end='2024-12-31',accn='0000000001-25-000001',filed='2025-02-01',val=90))
    result,payload=collected_variant(tmp_path,change)
    row=next(r for r in payload['companies'] if r['company_id']=='asml')
    assert result['failed_companies']==0 and [x['val'] for x in row['reported_shares']]==[90]
    assert row['share_class_basis']=='UNCONFIRMED' and row['excluded_fact_counts']=={'FACT_CONFLICT':2}


def test_all_bad_facts_company_na_counts_preserved_and_no_zero(tmp_path):
    def change(f,s):f['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0]['form']='S-1'
    result,payload=collected_variant(tmp_path,change)
    row=next(r for r in payload['companies'] if r['company_id']=='asml')
    assert result['failed_companies']==1 and row['status']=='NOT_AVAILABLE' and 'reported_shares' not in row
    assert row['reason_codes']==['SEC_NO_ELIGIBLE_SHARE_FACTS'] and row['excluded_fact_counts']=={'FORM_NOT_ALLOWED':1}


def test_exclusion_diagnostic_can_only_print_fixed_codes_counts_and_company_ordinal(tmp_path,capsys,monkeypatch):
    import public_sec_inputs as module
    result,_=collected_variant(tmp_path,bad_and_good)
    monkeypatch.setattr(module,'collect_public_inputs',lambda _:result)
    assert module.main(['--live','--output',str(tmp_path/'out')])==0
    out=capsys.readouterr().out
    assert 'SEC_EXCLUDED company_index=3 code=FORM_NOT_ALLOWED count=1' in out and 'failed_companies=0' in out
    assert 'synthetic setting' not in out and 'S-1' not in out and '2025-02-30' not in out


@pytest.mark.parametrize('change,code',[
    (lambda s:s['filings']['recent'].update(acceptanceDateTime=['private sentinel']),'FILING_TIMESTAMP_INVALID'),
    (lambda s:s['filings']['recent'].update(reportDate=['2025-02-30']),'FILING_REPORT_DATE_INVALID'),
])
def test_individual_bad_filing_rows_do_not_erase_valid_share_facts(tmp_path,change,code):
    result,payload=collected_variant(tmp_path,lambda f,s:change(s))
    row=next(r for r in payload['companies'] if r['company_id']=='asml')
    assert result['failed_companies']==0 and row['filings']==[] and row['reported_shares']
    assert row['excluded_fact_counts']=={code:1}


def test_corrupt_filing_columns_do_not_erase_valid_core_share_fact(tmp_path):
    result,payload=collected_variant(tmp_path,lambda f,s:s['filings']['recent'].update(reportDate=[]))
    row=next(r for r in payload['companies'] if r['company_id']=='asml')
    assert result['failed_companies']==0 and row['reported_shares'] and row['filings']==[]
    assert row['excluded_fact_counts']=={'FILING_SCHEMA_INVALID':1}


def test_bad_namespace_does_not_erase_another_valid_outstanding_concept(tmp_path):
    def change(f,s):
        concept=f['facts']['dei']['EntityCommonStockSharesOutstanding']
        f['facts']['us-gaap']['CommonStockSharesOutstanding']=concept
        f['facts']['dei']='private sentinel'
    result,payload=collected_variant(tmp_path,change)
    row=next(r for r in payload['companies'] if r['company_id']=='asml')
    assert result['failed_companies']==0 and row['reported_shares'][0]['namespace']=='us-gaap'
    assert row['excluded_fact_counts']=={'FACT_SCHEMA_INVALID':1}

@pytest.mark.parametrize('mutate',[
    lambda r:r['excluded_fact_counts'].update(arbitrary_private_code=1),
    lambda r:r['excluded_fact_counts'].update(FORM_NOT_ALLOWED=True),
    lambda r:r.update(share_class_basis='SINGLE_CLASS_CONFIRMED'),
    lambda r:r['reported_shares'].append(dict(r['reported_shares'][0],val=200)),
])
def test_v3_guard_rejects_counts_or_unproven_basis_and_conflicting_facts(tmp_path,mutate):
    _,payload=collected_variant(tmp_path,lambda f,s:None)
    mutate(payload['companies'][0])
    with pytest.raises(ValueError,match='SEC_PUBLIC_INPUT_INVALID'):require_public_inputs(payload)


def test_legacy_v1_and_v2_remain_accepted_independently_of_new_producer(tmp_path):
    _,payload=collected_variant(tmp_path,lambda f,s:None)
    for version in (1,2):
        old=copy.deepcopy(payload);old['schema']=f'public-sec-reported-inputs/{version}'
        for row in old['companies']:
            row.pop('excluded_fact_counts');row.pop('share_class_basis');row.pop('share_class_notice')
            if version==1:row.pop('status')
        require_public_inputs(old)


def test_invalid_class_dimensioned_fact_does_not_create_class_basis_notice(tmp_path):
    def change(f,s):
        rows=f['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares']
        rows.append(dict(rows[0],val=-1,end='2025-02-30',dimensions={'us-gaap:StatementClassOfStockAxis':'issuer:ClassAMember'}))
    result,payload=collected_variant(tmp_path,change)
    row=next(r for r in payload['companies'] if r['company_id']=='asml')
    assert row['share_class_basis']=='UNCONFIRMED' and row['share_class_notice'] is None
    assert row['excluded_fact_counts']=={'VALUE_INVALID':1}


def test_all_rejected_fact_counts_are_available_in_cli_without_replacing_old_file(tmp_path,capsys,monkeypatch):
    from datetime import datetime,timezone
    import public_sec_inputs as module
    class Client:
        def __init__(self,_):pass
        def collect(self,company,cik):
            values=raw(company);values[0]['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0]['val']=-1
            return *(json.dumps(x).encode() for x in values),datetime(2026,2,2,12,tzinfo=timezone.utc)
    p=tmp_path/'out';p.write_text('old')
    def collect(_):return collect_public_inputs(p,environ={'SEC_USER_AGENT':'synthetic setting'},client_factory=Client)
    monkeypatch.setattr(module,'collect_public_inputs',collect)
    assert module.main(['--live','--output',str(p)])==1
    out=capsys.readouterr().out
    assert 'SEC_EXCLUDED company_index=4 code=VALUE_INVALID count=1' in out and 'failed_companies=17' in out
    assert p.read_text()=='old'
