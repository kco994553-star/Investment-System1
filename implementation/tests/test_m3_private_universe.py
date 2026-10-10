"""Private RAM calculations exercised exclusively with invented inputs."""
import builtins
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import hashlib
import importlib
import importlib.util
import json
import logging
from pathlib import Path
import socket

import pytest

AT=datetime(2030,2,10,12,tzinfo=timezone.utc)
HEADER=["code","marketcap","price"]


def api():
    name="investment_system.universe.private_subset"
    assert importlib.util.find_spec(name) is not None, "M3 pure computation module is missing"
    return importlib.import_module(name)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()


def seed(a,name="a",**changes):
    value=a.ListingSeed("listing_"+name,"synthetic_"+name,"issuer_"+name,"security_"+name,name.upper(),"XNYS","USD","America/New_York",name.upper(),"0000000001",date(2020,1,1),None,"synthetic-identity",digest([name]),True)
    return replace(value,**changes)


def basis(a,s,**changes):
    value=a.ShareBasisReceipt(s.listing_id,s.company_id,s.security_id,"SINGLE_CLASS_CONFIRMED","synthetic-unit-evidence",digest([s.security_id]),AT-timedelta(days=1),"shares","GOOGLEFINANCE_CURRENT",s.currency,True)
    return replace(value,**changes)


def parse(a,values,identities=None,**changes):
    identities={"NYSE:A":seed(a)} if identities is None else identities
    receipt=a.UniverseReceipt("GOOGLEFINANCE_PRIVATE_UNIVERSE",AT,digest(values),"synthetic-job",1,True)
    return a.parse_universe_values(values,replace(receipt,**changes),identity_lookup=identities)


def sec(a,s,*,dei=10,gaap=99,at=AT,changes=None):
    accession="0000000001-30-000001"
    row=dict(end="2030-01-31",val=dei,accn=accession,form="10-K",filed="2030-02-01")
    facts={"cik":1,"facts":{"dei":{"EntityCommonStockSharesOutstanding":{"units":{"shares":[row]}}},"us-gaap":{"CommonStockSharesOutstanding":{"units":{"shares":[{**row,"val":gaap}]}}}}}
    submissions={"cik":1,"filings":{"recent":{"accessionNumber":[accession],"form":["10-K"],"filingDate":["2030-02-01"],"acceptanceDateTime":["2030-02-01T12:00:00Z"]}}}
    if changes: changes(facts,submissions)
    bodies=[json.dumps(x).encode() for x in (facts,submissions)]
    receipt=a.SecReceipt(s.cik,*bodies,at,*(hashlib.sha256(b).hexdigest() for b in bodies),True)
    return receipt


def check(a,row,*,shares=10,quality=None,s=None,parsed=None):
    s=seed(a) if s is None else s
    unit=basis(a,s)
    sh=a.prepare_sec_shares(s,sec(a,s,dei=shares),unit,AT)
    price=a.prepare_universe_price(row,unit,as_of=AT)
    return a.compare_universe_market_cap(row,sh,price,quality or a.QualityConfig(.1,True))


def test_universe_columns_are_code_marketcap_price_not_quotes_format():
    a=api()
    for values in [[HEADER,["NYSE:A",90,10]],[["NYSE:A",90,10]],[["CODE","MARKETCAP","PRICE"],["NYSE:A",90,10]]]:
        p=parse(a,values); assert p.state=="INPUT_RESEARCH" and p.row_count==1
        assert (p.rows[0].google_mcap,p.rows[0].sheet_price)==(90,10)
        assert p.receipt.content_sha256==digest(values)


@pytest.mark.parametrize("bad",[None,"","#N/A","#VALUE!","#REF!",True,False,float("nan"),float("inf"),0,-1,"$10","10M","1,000"])
def test_universe_missing_and_error_rows_are_not_zero_or_filled(bad):
    a=api(); p=parse(a,[["NYSE:A",bad,bad]])
    assert p.row_count==1 and p.rows[0].google_mcap is None and p.rows[0].sheet_price is None
    c=check(a,p.rows[0]); assert c.state=="NOT_AVAILABLE" and c.effective_cap is None


def test_universe_numeric_strings_use_only_explicit_decimal_grammar():
    a=api(); p=parse(a,[["NYSE:A","90.5","10.5"]])
    assert (p.rows[0].google_mcap,p.rows[0].sheet_price)==(90.5,10.5)
    assert parse(a,[["NYSE:A","1e9","10"]]).rows[0].google_mcap is None


def test_trailing_empty_rows_only_are_removed():
    a=api(); p=parse(a,[HEADER,["NYSE:A",90,10],[],["",None,""],[]])
    assert p.row_count==1
    p=parse(a,[[],["NYSE:A",90,10],[]]); assert p.row_count==2
    assert p.rows[0].reason_codes==("IDENTITY_UNCONFIRMED",)


def test_universe_receipt_hash_time_source_and_mixed_identity_are_required():
    a=api(); values=[["NYSE:A",90,10]]
    for changes,reason in [(dict(content_sha256="0"*64),"MANIFEST_MISMATCH"),(dict(acquired_at=AT.replace(tzinfo=None)),"INVALID_TIMESTAMP"),(dict(source="OTHER"),"UNIVERSE_SCHEMA_MISMATCH")]:
        p=parse(a,values,**changes); assert p.state=="NOT_AVAILABLE" and p.reason_codes==(reason,)
    assert parse(a,values,{"NYSE:A":seed(a,synthetic=False)}).rows[0].reason_codes==("MIXED_SYNTHETIC_INPUT",)


def test_universe_identity_requires_explicit_mapping_mic_currency_and_evidence():
    a=api()
    assert parse(a,[["A",90,10]]).rows[0].listing is None
    assert parse(a,[["A",90,10]],{"A":seed(a)}).rows[0].listing is not None
    for s,reason in [(seed(a,mic="XNAS"),"IDENTITY_UNCONFIRMED"),(seed(a,currency="KRW"),"CURRENCY_SCOPE_NOT_SUPPORTED"),(seed(a,cik=None),"IDENTITY_UNCONFIRMED"),(seed(a,identity_evidence_ref=""),"IDENTITY_UNCONFIRMED")]:
        assert parse(a,[["NYSE:A",90,10]],{"NYSE:A":s}).rows[0].reason_codes==(reason,)
    assert parse(a,[["NYSE:A.B",90,10]],{"NYSE:A-B":seed(a,symbol="A-B")}).rows[0].listing is None


def test_identical_listing_rows_deduplicate_and_conflicts_fail_closed():
    a=api(); p=parse(a,[["NYSE:A",90,10],["NYSE:A",90,10]])
    assert p.row_count==1 and len(p.rows)==1
    p=parse(a,[["NYSE:A",90,10],["NYSE:A",100,10]])
    assert p.row_count==1 and "INVALID_INPUT" in p.rows[0].reason_codes
    assert check(a,p.rows[0]).state=="NOT_AVAILABLE"


def test_row_limit_is_partial_coverage_and_not_a_complete_pool():
    a=api(); values=[["NYSE:A",90,10]]+[["UNKNOWN"+str(i),90,10] for i in range(1023)]
    p=parse(a,values); assert p.row_limit_reached and "ROW_LIMIT_REACHED" in p.reason_codes
    selection=a.select_verified_universe_top_n((check(a,p.rows[0]),),a.SelectionConfig(1,True),parsed=p)
    assert selection.selection_status=="PARTIAL" and selection.row_count==1024 and selection.missing_count==1023
    assert selection.selected_n==1 and selection.candidate_pool_complete is False and selection.official is False


def test_shares_follow_concept_precedence_and_gaap_only_when_no_eligible_dei():
    a=api(); s=seed(a); b=basis(a,s)
    sh=a.prepare_sec_shares(s,sec(a,s),b,AT)
    assert sh.shares==10 and sh.concept=="dei:EntityCommonStockSharesOutstanding"
    def remove(f,sub): f["facts"]["dei"]={}
    sh=a.prepare_sec_shares(s,sec(a,s,changes=remove),b,AT)
    assert sh.shares==99 and sh.concept=="us-gaap:CommonStockSharesOutstanding"
    assert sh.historical_first_publication is False and sh.shares_available_at==AT


def test_shares_latest_filing_and_latest_measurement_end_are_selected():
    a=api(); s=seed(a)
    def add(f,sub):
        rows=f["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]["shares"]
        rows.append({**rows[0],"end":"2030-01-01","val":8})
        newer={**rows[0],"end":"2030-01-15","val":12,"accn":"0000000001-30-000002","filed":"2030-02-02"}
        rows.append(newer)
        rec=sub["filings"]["recent"]
        for key,val in dict(accessionNumber=newer["accn"],form="10-K",filingDate="2030-02-02",acceptanceDateTime="2030-02-02T12:00:00Z").items(): rec[key].append(val)
    sh=a.prepare_sec_shares(s,sec(a,s,changes=add),basis(a,s),AT)
    assert sh.shares==12 and sh.measurement_date==date(2030,1,15) and sh.accn.endswith("000002")


def test_shares_conflicting_same_end_is_ambiguous_not_gaap_fallback():
    a=api(); s=seed(a)
    def conflict(f,sub):
        rows=f["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]["shares"]
        rows.append({**rows[0],"val":11})
    sh=a.prepare_sec_shares(s,sec(a,s,changes=conflict),basis(a,s),AT)
    assert sh.state=="NOT_AVAILABLE" and sh.shares is None and sh.reason_codes==("MULTI_CLASS_AMBIGUOUS",)


def test_shares_require_cik_body_hash_accession_units_and_acquisition_cutoff():
    a=api(); s=seed(a); b=basis(a,s); r=sec(a,s)
    for changed,reason in [(replace(r,facts_sha256="0"*64),"MANIFEST_MISMATCH"),(replace(r,cik="0000000002"),"CIK_MISMATCH"),(replace(r,acquired_at=AT+timedelta(seconds=1)),"AVAILABLE_AFTER_AS_OF"),(replace(r,acquired_at=AT.replace(tzinfo=None)),"INVALID_TIMESTAMP")]:
        sh=a.prepare_sec_shares(s,changed,b,AT); assert sh.state=="NOT_AVAILABLE" and sh.reason_codes==(reason,)
    def unknown(f,sub):
        sub["filings"]["recent"]["accessionNumber"]=["0000000001-30-000999"]
        f["facts"]["us-gaap"]={}
    assert a.prepare_sec_shares(s,sec(a,s,changes=unknown),b,AT).reason_codes==("ACCESSION_UNCONFIRMED",)
    def units(f,sub):
        f["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]={"USD":[]}; f["facts"]["us-gaap"]={}
    assert a.prepare_sec_shares(s,sec(a,s,changes=units),b,AT).state=="NOT_AVAILABLE"


def test_shares_acceptance_is_aware_and_no_filed_midnight_backfill():
    a=api(); s=seed(a); b=basis(a,s)
    for accepted,reason in [("2030-02-11T12:00:00Z","INVALID_TIME_ORDER"),("2030-02-01T12:00:00","INVALID_TIMESTAMP"),(None,"ACCESSION_UNCONFIRMED")]:
        def change(f,sub): sub["filings"]["recent"]["acceptanceDateTime"]=[accepted]; f["facts"]["us-gaap"]={}
        sh=a.prepare_sec_shares(s,sec(a,s,changes=change),b,AT)
        assert sh.reason_codes==(reason,)


def test_single_value_shares_do_not_prove_class_or_adr_basis():
    a=api(); s=seed(a); r=sec(a,s)
    for changes in [dict(basis_status="UNKNOWN"),dict(source_evidence_ref=""),dict(source_sha256=""),dict(security_id="other"),dict(price_basis="RAW_CLOSE")]:
        sh=a.prepare_sec_shares(s,r,basis(a,s,**changes),AT)
        assert sh.state=="NOT_AVAILABLE" and sh.reason_codes==("BASIS_UNCONFIRMED",)


@pytest.mark.parametrize("symbol",["GOOGL","GOOG","BRK.B"])
def test_evidenced_share_class_difference_has_distinct_notice_without_correction(symbol):
    a=api(); s=seed(a,symbol=symbol,provider_symbol=symbol)
    p=parse(a,[["NYSE:"+symbol,1000,10]],{"NYSE:"+symbol:s})
    b=replace(basis(a,s),basis_status="UNKNOWN",share_class_basis="DIFFERENT")
    sh=a.prepare_sec_shares(s,sec(a,s),b,AT)
    px=a.prepare_universe_price(p.rows[0],b,as_of=AT)
    c=a.compare_universe_market_cap(p.rows[0],sh,px,a.QualityConfig(.1,True))
    assert sh.reason_codes==px.reason_codes==c.reason_codes==("SHARE_CLASS_BASIS",)
    assert c.state=="NOT_AVAILABLE" and c.quality==c.quality_label=="SHARE_CLASS_BASIS"
    assert sh.shares is None and px.price is None and c.recomputed_cap is c.effective_cap is None
    assert c.google_mcap==1000 and p.rows[0].sheet_price==10
    selected=a.select_verified_universe_top_n((c,),a.SelectionConfig(1,True),parsed=p)
    assert selected.selected_n==0 and selected.selection_status=="PARTIAL"
    assert selected.missing==((p.rows[0].row_index,("SHARE_CLASS_BASIS",)),)


def test_share_class_notice_requires_bound_evidence_and_does_not_infer_from_ticker_or_error():
    a=api(); s=seed(a,symbol="GOOGL",provider_symbol="GOOGL")
    p=parse(a,[["NYSE:GOOGL",1000,10]],{"NYSE:GOOGL":s})
    assert check(a,p.rows[0],s=s).quality=="MISMATCH"
    for changes in [dict(source_evidence_ref=""),dict(source_sha256=""),dict(security_id="other")]:
        b=replace(basis(a,s,**changes),basis_status="UNKNOWN",share_class_basis="DIFFERENT")
        sh=a.prepare_sec_shares(s,sec(a,s),b,AT)
        assert sh.reason_codes==("BASIS_UNCONFIRMED",)


def test_share_class_annotation_does_not_change_valid_cap_formula_or_basis_gate():
    a=api(); s=seed(a); p=parse(a,[["NYSE:A",90,10]])
    original=basis(a,s); annotated=replace(original,share_class_basis="ALIGNED")
    sh=a.prepare_sec_shares(s,sec(a,s),annotated,AT)
    px=a.prepare_universe_price(p.rows[0],annotated,as_of=AT)
    c=a.compare_universe_market_cap(p.rows[0],sh,px,a.QualityConfig(.1,True))
    assert c==check(a,p.rows[0])
    b=replace(original,basis_status="UNKNOWN")
    assert a.prepare_sec_shares(s,sec(a,s),b,AT).reason_codes==("BASIS_UNCONFIRMED",)
    b=replace(original,share_class_basis="made-up")
    assert a.prepare_sec_shares(s,sec(a,s),b,AT).reason_codes==("BASIS_UNCONFIRMED",)


def test_sheet_price_is_current_reference_not_raw_close_or_exact_eod():
    a=api(); s=seed(a); p=parse(a,[["NYSE:A",90,10]])
    px=a.prepare_universe_price(p.rows[0],basis(a,s),as_of=AT)
    assert px.state=="INPUT_RESEARCH" and px.price==10 and px.price_kind=="GOOGLEFINANCE_CURRENT"
    assert px.available_at==px.observed_at==AT and px.trade_time is None and px.exact_eod is False
    assert a.prepare_universe_price(p.rows[0],basis(a,s),as_of=AT-timedelta(seconds=1)).reason_codes==("AVAILABLE_AFTER_AS_OF",)


def test_marketcap_uses_sec_shares_times_same_row_sheet_price():
    a=api(); p=parse(a,[["NYSE:A",1000,10]]); c=check(a,p.rows[0])
    assert c.state=="VERIFIED" and c.recomputed_cap==c.effective_cap==100
    assert c.google_mcap==1000 and c.relative_difference==9 and c.quality=="MISMATCH"
    assert c.quality_label=="검증 불일치"
    assert c.shares_input.concept=="dei:EntityCommonStockSharesOutstanding"
    assert c.shares_input.accn=="0000000001-30-000001" and c.shares_input.measurement_date==date(2030,1,31)
    assert c.shares_input.facts_sha256==sec(a,seed(a)).facts_sha256
    assert c.shares_input.submissions_sha256==sec(a,seed(a)).submissions_sha256
    assert c.price_input.content_sha256==p.receipt.content_sha256


def test_google_cap_missing_or_invalid_still_uses_verified_recomputed_value():
    a=api()
    for value,quality in [(None,"GOOGLE_MCAP_MISSING"),("#N/A","GOOGLE_MCAP_INVALID")]:
        p=parse(a,[["NYSE:A",value,10]]); c=check(a,p.rows[0])
        assert c.state=="VERIFIED" and c.effective_cap==100 and c.quality==quality and c.relative_difference is None


@pytest.mark.parametrize("google,quality,relative",[(90,"MISMATCH",.1),(90.01,"WITHIN_TOLERANCE",.0999),(10,"MISMATCH",.9),(1,"MISMATCH",.99),(100,"WITHIN_TOLERANCE",0)])
def test_threshold_denominator_is_recomputed_cap_and_boundary_inclusive(google,quality,relative):
    a=api(); p=parse(a,[["NYSE:A",google,10]]); c=check(a,p.rows[0])
    assert c.relative_difference==relative and c.quality==quality and c.effective_cap==100


def test_decimal_quality_boundary_has_no_binary_float_label_slip():
    a=api(); p=parse(a,[["NYSE:A",2.7,1]])
    c=check(a,p.rows[0],shares=3)
    assert c.effective_cap==3 and c.relative_difference==.1 and c.quality=="MISMATCH"


def test_comparison_rejects_other_row_price_lineage_and_bad_basis():
    a=api(); s=seed(a); p=parse(a,[["NYSE:A",90,10]]); row=p.rows[0]; b=basis(a,s)
    sh=a.prepare_sec_shares(s,sec(a,s),b,AT); px=a.prepare_universe_price(row,b,as_of=AT)
    for altered in [replace(px,price=11),replace(px,listing_id="other"),replace(px,content_sha256="0"*64)]:
        c=a.compare_universe_market_cap(row,sh,altered,a.QualityConfig(.1,True))
        assert c.state=="NOT_AVAILABLE" and c.effective_cap is None


def test_nonfinite_product_and_relative_difference_never_produce_rank():
    a=api(); p=parse(a,[["NYSE:A",90,1e308]])
    c=check(a,p.rows[0],shares=1e308); assert c.reason_codes==("NONFINITE_MCAP",)
    p=parse(a,[["NYSE:A",1e308,1e-308]])
    c=check(a,p.rows[0],shares=1); assert c.state=="NOT_AVAILABLE" and c.reason_codes==("NONFINITE_MCAP",)


def test_n_and_quality_settings_require_explicit_user_confirmation():
    a=api(); p=parse(a,[["NYSE:A",90,10]]); row=p.rows[0]
    c=check(a,row,quality=a.QualityConfig(.1,False))
    assert c.state=="NOT_AVAILABLE" and c.reason_codes==("CONFIG_CONFIRMATION_REQUIRED",)
    pending=a.select_verified_universe_top_n((c,),a.SelectionConfig(1,True),parsed=p)
    assert pending.selected_n==0 and pending.selection_status=="UNCONFIRMED"
    selection=a.select_verified_universe_top_n((check(a,row),),a.SelectionConfig(1,False),parsed=p)
    assert selection.selected_n==0 and selection.selection_status=="UNCONFIRMED"
    for n in [0,-1,True,1.5,2]:
        assert a.select_verified_universe_top_n((check(a,row),),a.SelectionConfig(n,True),parsed=p).state=="NOT_AVAILABLE"
    for tau in [0,-1,True,float("nan"),float("inf")]:
        assert check(a,row,quality=a.QualityConfig(tau,True)).state=="NOT_AVAILABLE"


def test_full_pool_validation_precedes_top_n_and_understated_google_cap_cannot_hide_winner():
    a=api(); sa=seed(a); sb=seed(a,"b"); identities={"NYSE:A":sa,"NYSE:B":sb}
    p=parse(a,[["NYSE:A",1000,10],["NYSE:B",1,20]],identities)
    checks=(check(a,p.rows[0],s=sa),check(a,p.rows[1],s=sb))
    selected=a.select_verified_universe_top_n(checks,a.SelectionConfig(1,True),parsed=p)
    assert selected.selected_listing_ids==(sb.listing_id,) and selected.verified_count==2 and selected.selection_status=="COMPLETE"
    shortcut=a.select_verified_universe_top_n(checks[:1],a.SelectionConfig(1,True),parsed=p)
    assert shortcut.selection_status=="PARTIAL" and shortcut.missing_count==1


def test_top_n_ascii_ties_and_missing_counts_match_existing_pure_helper():
    a=api(); sa=seed(a); sb=seed(a,"b"); p=parse(a,[["NYSE:B",100,10],["NYSE:A",100,10]],{"NYSE:A":sa,"NYSE:B":sb})
    checks=(check(a,p.rows[0],s=sb),check(a,p.rows[1],s=sa))
    selected=a.select_verified_universe_top_n(checks,a.SelectionConfig(2,True),parsed=p)
    from investment_system.universe.sources import mcap_top_n_snapshot
    snap,report=mcap_top_n_snapshot([dict(company_id=s.company_id,ticker=s.symbol,shares=10,shares_available_at=AT,price=10,price_observed_at=AT) for s in (sb,sa)],AT,n=2)
    assert selected.selected_listing_ids==(sa.listing_id,sb.listing_id)
    assert tuple(m.company_id for m in snap.members)==(sa.company_id,sb.company_id)
    assert report["candidate_pool_complete"] is False and selected.scope=="VERIFIED_UNIVERSE_ROWS"
    assert (selected.row_count,selected.verified_count,selected.missing_count,selected.selected_n)==(2,2,0,2)


def test_missing_candidates_are_not_padded_to_requested_n():
    a=api(); sa=seed(a); sb=seed(a,"b"); p=parse(a,[["NYSE:A",100,10],["NYSE:B",100,None]],{"NYSE:A":sa,"NYSE:B":sb})
    selection=a.select_verified_universe_top_n((check(a,p.rows[0],s=sa),check(a,p.rows[1],s=sb)),a.SelectionConfig(2,True),parsed=p)
    assert selection.selected_n==1 and selection.missing_count==1 and selection.selection_status=="PARTIAL"
    assert selection.full_configured_rank_status=="UNKNOWN" and selection.official is False


def test_duplicate_issuers_and_mixed_synthetic_checks_are_blocked():
    a=api(); sa=seed(a); sb=seed(a,"b",issuer_id=sa.issuer_id)
    p=parse(a,[["NYSE:A",100,10],["NYSE:B",100,10]],{"NYSE:A":sa,"NYSE:B":sb})
    checks=(check(a,p.rows[0],s=sa),check(a,p.rows[1],s=sb))
    selection=a.select_verified_universe_top_n(checks,a.SelectionConfig(2,True),parsed=p)
    assert selection.selected_n==0 and "DUPLICATE_ISSUER" in selection.reason_codes
    selection=a.select_verified_universe_top_n((replace(checks[0],synthetic=False),checks[1]),a.SelectionConfig(2,True),parsed=p)
    assert selection.selected_n==0 and "MIXED_SYNTHETIC_INPUT" in selection.reason_codes


def test_known_duplicate_issuer_blocks_a_valid_listing_even_if_other_price_is_missing():
    a=api(); sa=seed(a); sb=seed(a,"b",issuer_id=sa.issuer_id)
    p=parse(a,[["NYSE:A",100,10],["NYSE:B",100,None]],{"NYSE:A":sa,"NYSE:B":sb})
    selection=a.select_verified_universe_top_n((check(a,p.rows[0],s=sa),check(a,p.rows[1],s=sb)),a.SelectionConfig(1,True),parsed=p)
    assert selection.selected_n==0 and "DUPLICATE_ISSUER" in selection.reason_codes


def test_sec_acceptance_cannot_precede_filing_and_measurement_dates():
    a=api(); s=seed(a)
    def change(f,sub):
        sub["filings"]["recent"]["acceptanceDateTime"]=["2029-01-01T12:00:00Z"]
        f["facts"]["us-gaap"]={}
    shares=a.prepare_sec_shares(s,sec(a,s,changes=change),basis(a,s),AT)
    assert shares.state=="NOT_AVAILABLE" and shares.reason_codes==("INVALID_TIME_ORDER",)


def test_malformed_private_sidecars_return_fixed_codes_without_raw_exception():
    a=api(); p=parse(a,[["NYSE:A",90,10]]); row=p.rows[0]; s=seed(a); b=basis(a,s)
    sh=a.prepare_sec_shares(s,sec(a,s),b,AT); px=a.prepare_universe_price(row,b,as_of=AT)
    for altered in [replace(row,receipt=None),replace(row,listing="bad")]:
        result=a.compare_universe_market_cap(altered,sh,px,a.QualityConfig(.1,True))
        assert result.state=="NOT_AVAILABLE" and result.reason_codes==("IDENTITY_UNCONFIRMED",)
        assert a.prepare_universe_price(altered,b,as_of=AT).state=="NOT_AVAILABLE"
    assert a.prepare_sec_shares(s,replace(sec(a,s),synthetic=1),b,AT).state=="NOT_AVAILABLE"
    altered=replace(row,listing=replace(s,issuer_id=[]))
    malformed=replace(p,rows=(altered,))
    assert a.select_verified_universe_top_n((),a.SelectionConfig(1,True),parsed=malformed).reason_codes==("INVALID_INPUT",)
    forged=replace(sh,state="NOT_AVAILABLE",reason_codes=("private-sentinel",))
    result=a.compare_universe_market_cap(row,forged,px,a.QualityConfig(.1,True))
    assert result.reason_codes==("INVALID_INPUT",) and "private-sentinel" not in repr(result)
    check_result=check(a,row)
    for malformed in [replace(p,row_count=2),replace(p,rows=(replace(row,row_index=[]),)),replace(p,reason_codes=("private-sentinel",))]:
        result=a.select_verified_universe_top_n((check_result,),a.SelectionConfig(1,True),parsed=malformed)
        assert result.state=="NOT_AVAILABLE" and result.reason_codes==("INVALID_INPUT",)


def test_pure_boundary_has_no_io_mutation_storage_or_diagnostic_payloads(monkeypatch,capsys):
    a=api(); values=[["NYSE:A",100,10]]; original=deepcopy(values); p=parse(a,values); r=sec(a,seed(a)); b=basis(a,seed(a))
    def forbidden(*args,**kwargs): pytest.fail("I/O at private pure boundary")
    with monkeypatch.context() as m:
        m.setattr(builtins,"open",forbidden); m.setattr(Path,"open",forbidden)
        m.setattr(socket,"create_connection",forbidden); m.setattr(socket.socket,"connect",forbidden)
        m.setattr(logging.Logger,"_log",forbidden)
        sh=a.prepare_sec_shares(seed(a),r,b,AT); px=a.prepare_universe_price(p.rows[0],b,as_of=AT)
        c=a.compare_universe_market_cap(p.rows[0],sh,px,a.QualityConfig(.1,True))
        result=a.select_verified_universe_top_n((c,),a.SelectionConfig(1,True),parsed=p)
    assert result.state=="PERSONAL_REFERENCE" and values==original
    assert "NYSE:A" not in repr(p) and "listing_a" not in repr(result)
    assert capsys.readouterr()==("","")
