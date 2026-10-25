"""Listing-ended registry (STALE_REPORT 2026-10-25 option B-a, PR-2): a reviewed table entry publishes one Universe code as
a reasoned NA row in all three Universe files, checked before the PRESERVE rule.

The real table holds exactly one entry, NASDAQ:WBD (CIK 0001437107: acquired for cash and delisted, 8-K items 2.01/3.01,
Form 25 / 25-NSE 2026-10-06, 15-12G 2026-10-16). The end-to-end cases run the real daily tool (tools/sec_universe_shares.py)
on the synthetic 27-issuer Universe with the table pointed at one synthetic issuer, against the same run with an empty table
(today's PRESERVE behaviour), then the strict Python and JS validators, the freshness guard, the forward-ledger basis and the
TARGET v1 finalize check (target-v1-builder.js publishedCheck) on the produced files. Synthetic bytes, fake transports and
injected clocks only: no network, credential or price.
"""
from datetime import timedelta
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from investment_system.qgv import v2_factors as vf
from investment_system.universe import sec_qgv2 as qgv2
from investment_system.universe import sec_universe_qg as uqg
from investment_system.universe import sec_universe_shares as us
from investment_system.validation import forward_ledger as fl
from tests import test_previous_observation_preservation as P
from tests import test_sec_universe_all_shards as AS
from tests.test_pages_freshness_guard import guard_against, section_line

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'src/investment_system/product/web_assets'
UNIVERSE = (us.FILENAME, uqg.FILENAME, qgv2.FILENAME)
WBD, WBD_CIK = 'NASDAQ:WBD', '0001437107'
QGV2_SCORE_KEYS = ('factors', 'axes')


# ------------------------------------------------ the reviewed table ------------------------------------------------
def test_the_table_holds_exactly_the_reviewed_wbd_entry_with_its_evidence():
    assert set(us.LISTING_ENDED_CODES) == {WBD}
    entry = us.LISTING_ENDED_CODES[WBD]
    assert set(entry) == {'cik', 'effective', 'reason', 'evidence'}
    assert (entry['cik'], entry['effective'], entry['reason']) == (WBD_CIK, '2026-10-06', 'ACQUIRED_FOR_CASH_DELISTED')
    assert WBD in us.universe_codes()            # the code stays in the fixed Universe504 list (UNI-DEF (a))
    assert len(us.universe_codes()) == 504
    evidence = ' | '.join(entry['evidence'])
    for ref in ('0001193125-26-415055', '0001193125-26-415091', '0001354457-26-000951', '0001193125-26-423513',
                'items 2.01 and 3.01', 'Form 25 ', '25-NSE', '15-12G', 'UNIVERSE_INDEX_FOLLOWING_20261023.md',
                '/edgar/data/1437107/000119312526415055/', '/edgar/data/1437107/000119312526423513/',
                'not merged: closed PR #390, branch claude/universe-membership-audit at commit '):
        assert ref in evidence, ref


def test_the_entry_uses_the_existing_reason_code_and_changes_no_contract():
    """No new reason code, schema version or calc_version: CIK_UNRESOLVED is already allowed in all three files."""
    assert us.LISTING_ENDED_REASON == 'CIK_UNRESOLVED'
    for reasons in (us.REASONS, uqg.REASONS, qgv2.REASONS):
        assert us.LISTING_ENDED_REASON in reasons and 'LISTING_ENDED' not in reasons
    assert qgv2.REASONS == ('NOT_COLLECTED', 'CIK_UNRESOLVED', 'INVALID_INPUT', 'NO_ANNUAL_SEC_FINANCIALS', 'NON_SEC_ISSUER', 'STALE_INPUT')
    assert uqg.REASONS == ('NOT_COLLECTED', 'CIK_UNRESOLVED', 'INVALID_INPUT', 'M1_NOT_AVAILABLE', 'UNRESOLVED_CURRENT_FACT_AMBIGUITY',
                           'QG_NOT_AVAILABLE', 'STALE_INPUT')
    assert (us.SCHEMA_VERSION, us.SCHEMA_VERSIONS) == (2, (1, 2))
    assert vf.CALC_VERSION == 'qgv2-calc/2026-10-17.1'
    for name in ('sec-qgv2.js', 'sec-universe-qg.js', 'sec-universe-shares.js'):
        assert "'CIK_UNRESOLVED'" in (WEB / name).read_text(), name


def verified(cik=WBD_CIK, when='2026-10-17T03:15:35Z'):
    return {'cik': cik, 'acquired_at': when, 'source_sha256': {'companyfacts': 'a' * 64, 'submissions': 'b' * 64}}


@pytest.mark.parametrize('new', [None, {'cik': WBD_CIK, 'acquired_at': '2026-10-24T00:40:00Z'}, {'cik': '0000999999', 'acquired_at': None}])
def test_listing_ended_is_decided_before_preserve_and_whatever_this_run_brings(new):
    observed = lambda r: r['acquired_at'] is not None
    for conflicts in ((), (WBD,)):
        assert us.previous_decision(verified(), new, code=WBD, unresolved={WBD}, conflicts=conflicts,
                                    new_observation=observed) == us.LISTING_ENDED


def test_preserve_still_applies_to_every_other_unresolved_code_and_to_a_kept_row_of_another_cik():
    observed = lambda r: r['acquired_at'] is not None
    psky = verified(cik='0002041610', when='2026-10-17T03:13:16Z')
    assert us.previous_decision(psky, None, code='NASDAQ:PSKY', unresolved={'NASDAQ:PSKY', WBD},
                                new_observation=observed) == us.PRESERVE
    # The entry names its CIK: a kept row of another issuer, or one without a verified observation, is not touched by it.
    assert us.previous_decision(verified(cik='0000999999'), None, code=WBD, unresolved={WBD}, new_observation=observed) == us.PRESERVE
    assert not us.listing_ended(WBD, dict(verified(), acquired_at=None))
    assert not us.listing_ended(WBD, dict(verified(), source_sha256={'companyfacts': None, 'submissions': None}))
    assert us.previous_decision(us.empty_record(), None, code=WBD, unresolved={WBD}, new_observation=observed) is None
    assert not us.listing_ended('NASDAQ:PSKY', psky)


def test_removing_the_entry_is_safe_the_ended_row_then_falls_under_preserve(monkeypatch):
    """The only way back is removing the entry: the ended row is itself a verified observation, so PRESERVE keeps it as is."""
    observed = lambda r: r['acquired_at'] is not None
    row = us.ended_row(dict(verified(), shares=1, listing_id='x'), us.empty_record)
    assert row['state'] == 'NOT_AVAILABLE' and row['reason_codes'] == ['CIK_UNRESOLVED'] and us.verified_observation(row)
    assert us.previous_decision(row, None, code=WBD, unresolved={WBD}, new_observation=observed) == us.LISTING_ENDED
    monkeypatch.setattr(us, 'LISTING_ENDED_CODES', {})
    assert us.previous_decision(row, None, code=WBD, unresolved={WBD}, new_observation=observed) == us.PRESERVE


# ------------------------------------------------ end to end (daily tool) ------------------------------------------------
@pytest.fixture(scope='module')
def baseline(tmp_path_factory):
    """Day 0: one all-shards publication of the 27 synthetic issuers (all with data)."""
    folder = tmp_path_factory.mktemp('ended-baseline')
    day0 = P.run(folder, 'day0', P.Sec(), 0, all_shards=True)
    screen = qgv2.require_qgv2(json.loads((day0 / qgv2.FILENAME).read_bytes()))
    scored = [cik for _, cik, _, _ in AS.SPEC if all(screen['records'][AS.CODE[cik]]['axes'][a]['score'] is not None for a in ('Q', 'G'))]
    ended, other = scored[0], scored[1]     # ended: the table's issuer; other: an unresolved code that PRESERVE keeps
    return day0, ended, other


def entry_for(cik):
    return {AS.CODE[cik]: {'cik': cik, 'effective': '2026-10-06', 'reason': 'ACQUIRED_FOR_CASH_DELISTED', 'evidence': ('synthetic',)}}


def payloads(folder):
    return (us.require_universe_shares(json.loads((folder / us.FILENAME).read_bytes())),
            uqg.require_universe_qg(json.loads((folder / uqg.FILENAME).read_bytes())),
            qgv2.require_qgv2(json.loads((folder / qgv2.FILENAME).read_bytes())))


def node(script, *args):
    done = subprocess.run(['node', '-e', script, str(WEB), *map(str, args)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def js_validate(folder):
    script = ("const W=process.argv[1]+'/',f=process.argv[2],fs=require('fs'),out={};"
              "for(const[m,n]of[['sec-universe-shares.js','sec-universe-shares.json'],['sec-universe-qg.js','sec-universe-qg.json'],['sec-qgv2.js','sec-qgv2.json']]){"
              "try{require(W+m).validate(JSON.parse(fs.readFileSync(f+'/'+n,'utf8')));out[n]='OK';}catch(e){out[n]=String(e.message);}}"
              "console.log(JSON.stringify(out));")
    return node(script, folder)


def published_check(folder, date):
    script = ("const B=require(process.argv[1]+'/target-v1-builder.js'),p=JSON.parse(require('fs').readFileSync(process.argv[2],'utf8'));"
              "const c=B.publishedCheck(p,{date:process.argv[3]});console.log(JSON.stringify(c));")
    return node(script, folder / qgv2.FILENAME, date)


def day1(tmp_path, baseline, monkeypatch, capsys, *, table):
    """Day 1: both issuers missing from SEC's ticker file (unresolved), with `table` as the listing-ended table."""
    day0, ended, other = baseline
    monkeypatch.setattr(us, 'LISTING_ENDED_CODES', table)
    capsys.readouterr()
    out = P.run(tmp_path, 'day1-' + ('ended' if table else 'preserve'), P.Sec(hidden={ended, other}), 1, previous=day0)
    return out, P.collection_counts(capsys.readouterr().out)


def test_the_listed_code_becomes_a_reasoned_na_row_in_all_three_files(tmp_path, capsys, monkeypatch, baseline):
    day0, ended, other = baseline
    code = AS.CODE[ended]
    out, counts = day1(tmp_path, baseline, monkeypatch, capsys, table=entry_for(ended))
    shares, qg, screen = payloads(out)
    before = {name: P.rows(day0, name)[code] for name in UNIVERSE}
    assert before[us.FILENAME]['listing_id'] is not None and before[qgv2.FILENAME]['fiscal_year_end'] is not None
    for name, payload in zip(UNIVERSE, (shares, qg, screen)):
        row = payload['records'][code]
        assert (row['state'], row['reason_codes']) == ('NOT_AVAILABLE', ['CIK_UNRESOLVED']), name
        # The last observation's identity record stays: cik, acquired_at and every source hash.
        assert (row['cik'], row['acquired_at'], row['source_sha256']) == (
            ended, before[name]['acquired_at'], before[name]['source_sha256']), name
        assert 'detected_at' not in row                      # never a withdrawal row
    s = shares['records'][code]
    assert s == dict(us.empty_record(cik=ended, reasons=('CIK_UNRESOLVED',)), acquired_at=s['acquired_at'], source_sha256=s['source_sha256'])
    assert s['shares'] is None and s['listing_id'] is None and s['accn'] is None
    q = qg['records'][code]
    assert all(v is None for v in q['factors'].values())     # NA is null, never 0
    v = screen['records'][code]
    assert (v['calc_version'], v['fiscal_year_end'], v['metrics'], v['sic'], v['profile']) == (None, None, {}, None, None)
    assert all(x is None for x in v['factors'].values()) and all(a['score'] is None for a in v['axes'].values())
    assert v['v_inputs_v2'] == vf.empty_v_inputs()
    # Run log: one listing-ended code; the other unresolved code is still PRESERVED; the ended row keeps its last
    # acquired_at, so preserved_previous_<file> still counts it (the approved entries are the daily check's baseline).
    # (the synthetic registry binds only the 27 issuers: every other Universe504 code is unresolved too)
    assert int(counts['unresolved_codes']) == 504 - len(AS.SPEC) + 2
    assert (counts['listing_ended'], counts['preserved_unconfirmed']) == ('1', '1')
    assert counts['preserved_previous_qgv2'] == counts['preserved_previous_qg'] == counts['preserved_previous_shares'] == '2'
    assert counts['identity_not_preserved'] == '0'


def test_validators_and_the_freshness_guard_accept_it_unchanged(tmp_path, capsys, monkeypatch, baseline):
    day0, ended, _ = baseline
    code = AS.CODE[ended]
    out, _ = day1(tmp_path, baseline, monkeypatch, capsys, table=entry_for(ended))
    payloads(out)                                            # strict Python validators (also the Pages guard's)
    for name in UNIVERSE:                                     # encode() re-validates the exact published bytes
        module = {us.FILENAME: us, uqg.FILENAME: uqg, qgv2.FILENAME: qgv2}[name]
        assert module.encode(json.loads((out / name).read_bytes())) == (out / name).read_bytes()
    assert js_validate(out) == dict.fromkeys(UNIVERSE, 'OK')  # device readers (sec-*.js)
    code_, text = guard_against(out, day0, capsys)
    assert code_ == 0 and ' rows_regressed=0 ' in text
    for name in UNIVERSE:
        line = section_line(text, name, 'records')
        assert (line['verdict'], line['lost_record'], line['older'], line['missing']) == ('PASS', '0', '0', '0'), name
    # Why acquired_at must stay: the same NA row without it is refused as LOST_RECORD.
    lost = tmp_path / 'lost'
    shutil.copytree(out, lost)
    for name in UNIVERSE:
        payload = json.loads((lost / name).read_bytes())
        row = payload['records'][code]
        row['acquired_at'] = None
        row['source_sha256'] = dict.fromkeys(row['source_sha256'])
        (lost / name).write_text(json.dumps(payload))
    code_, text = guard_against(lost, day0, capsys)
    assert code_ == 1 and f'code={code} kind=LOST_RECORD ' in text


def test_cross_section_and_coverage_drop_by_exactly_one_and_no_other_code_changes_state(tmp_path, capsys, monkeypatch, baseline):
    _, ended, other = baseline
    code, kept = AS.CODE[ended], AS.CODE[other]
    preserved, _ = day1(tmp_path, baseline, monkeypatch, capsys, table={})
    out, _ = day1(tmp_path, baseline, monkeypatch, capsys, table=entry_for(ended))
    a, b = payloads(preserved), payloads(out)
    score = lambda p, axis: sum(1 for r in p['records'].values() if r['axes'][axis]['score'] is not None)
    assert b[2]['cross_section_size'] == a[2]['cross_section_size'] - 1
    assert (score(b[2], 'Q'), score(b[2], 'G')) == (score(a[2], 'Q') - 1, score(a[2], 'G') - 1)
    assert sum(b[2]['cross_section_by_profile'].values()) == b[2]['cross_section_size']
    assert b[2]['calc_version'] == a[2]['calc_version'] == vf.CALC_VERSION      # calc_version unchanged
    # Without the entry the code is PRESERVED with its values (today's behaviour).
    assert a[2]['records'][code]['fiscal_year_end'] is not None and a[2]['records'][code]['state'] == 'LIVE'
    for i, name in enumerate(UNIVERSE):
        for c in us.universe_codes():
            if c == code:
                continue
            ra, rb = a[i]['records'][c], b[i]['records'][c]
            if name == qgv2.FILENAME:   # scores are recomputed over the smaller cross-section; nothing else moves
                strip = lambda r: {k: (v if k != 'metrics' else {m: x for m, x in v.items() if m != 'revenue_volatility_5y_rank_pct'})
                                   for k, v in r.items() if k not in QGV2_SCORE_KEYS}
                assert strip(ra) == strip(rb), (name, c)
            else:
                assert ra == rb, (name, c)
    assert a[2]['target'].keys() == b[2]['target'].keys()
    # PRESERVE still works for the other unresolved code: its verified row is kept with its values and acquired_at.
    for name in UNIVERSE:
        assert b[UNIVERSE.index(name)]['records'][kept]['acquired_at'] == P.rows(baseline[0], name)[kept]['acquired_at']
    assert b[2]['records'][kept]['fiscal_year_end'] is not None and b[2]['records'][kept]['state'] == 'LIVE'
    assert b[0]['records'][kept] == P.rows(baseline[0], us.FILENAME)[kept]


def test_the_row_is_idempotent_and_the_restore_merge_publishes_it_too(tmp_path, capsys, monkeypatch, baseline):
    day0, ended, other = baseline
    code = AS.CODE[ended]
    out, _ = day1(tmp_path, baseline, monkeypatch, capsys, table=entry_for(ended))
    capsys.readouterr()
    day2 = P.run(tmp_path, 'day2', P.Sec(hidden={ended, other}), 2, previous=out)
    for name in UNIVERSE:
        assert P.rows(day2, name)[code] == P.rows(out, name)[code]
    code_, text = guard_against(day2, out, capsys)
    assert code_ == 0 and ' rows_regressed=0 ' in text
    # The run's opening restore merge (no unresolved codes passed) and a merge with this run's collection of the
    # code both publish the same NA row: the entry is decided before PRESERVE and before `replaces`.
    previous = qgv2.require_qgv2(json.loads((day0 / qgv2.FILENAME).read_bytes()))
    restored = qgv2.merge(previous, {}, as_of=P.day(1), shard_index=previous['last_shard_index'])
    assert restored['records'][code] == P.rows(out, qgv2.FILENAME)[code]
    fresh = qgv2.merge(previous, {code: dict(previous['records'][code], acquired_at=P.day(1).isoformat().replace('+00:00', 'Z'))},
                       as_of=P.day(1) + timedelta(hours=1), shard_index=0)
    assert fresh['records'][code]['reason_codes'] == ['CIK_UNRESOLVED'] and fresh['records'][code]['acquired_at'] == previous['records'][code]['acquired_at']


def test_forward_ledger_and_target_v1_finalize_treat_it_as_a_normal_na(tmp_path, capsys, monkeypatch, baseline):
    """Eight days on, only the table's issuer and the other unresolved code are older than 7 days. Without the entry both
    are PRESERVED valued rows: the ledger basis is ROW_DATA_STALE and publishedCheck counts both. With the entry the
    ended code is a normal NA row (never used, never stale); the other preserved code alone still blocks."""
    day0, ended, other = baseline
    code = AS.CODE[ended]
    results = {}
    for label, table in (('preserve', {}), ('ended', entry_for(ended))):
        monkeypatch.setattr(us, 'LISTING_ENDED_CODES', table)
        previous = day0
        for n in range(1, 9):
            previous = P.run(tmp_path / label, f'day{n}', P.Sec(hidden={ended, other}), n, previous=previous)
        results[label] = previous
    session = P.day(8).date()
    a, b = (qgv2.require_qgv2(json.loads((results[k] / qgv2.FILENAME).read_bytes())) for k in ('preserve', 'ended'))
    basis_a, basis_b = fl.observation_basis(a, session), fl.observation_basis(b, session)
    assert 'ROW_DATA_STALE' in basis_a['evaluation']['reasons'] and 'ROW_DATA_STALE' in basis_b['evaluation']['reasons']
    assert basis_b['population']['n'] == basis_a['population']['n'] - 1 == b['cross_section_size']
    assert 'POPULATION_MISMATCH' not in basis_b['evaluation']['reasons'] and 'CALC_VERSION_MIXED' not in basis_b['evaluation']['reasons']
    assert (basis_b['q_scored'], basis_b['g_scored']) == (basis_a['q_scored'] - 1, basis_a['g_scored'] - 1)
    assert basis_b['segment'] == basis_a['segment'] == vf.CALC_VERSION
    date = session.isoformat()
    check_a, check_b = published_check(results['preserve'], date), published_check(results['ended'], date)
    # (na_rows also counts the 477 codes outside the synthetic registry: NA rows without a collection record)
    assert (check_a['stale_rows'], check_a['mixed_rows'], check_a['na_rows']) == (2, 0, 504 - len(AS.SPEC))
    assert (check_b['stale_rows'], check_b['mixed_rows'], check_b['na_rows']) == (1, 0, check_a['na_rows'] + 1)
    assert (check_b['q'], check_b['g']) == (check_a['q'] - 1, check_a['g'] - 1)
    # Once the other code is collected again (all shards), only the ended code is old: nothing blocks on freshness.
    monkeypatch.setattr(us, 'LISTING_ENDED_CODES', entry_for(ended))
    final = P.run(tmp_path / 'ended', 'day9', P.Sec(hidden={ended}), 9, previous=results['ended'], all_shards=True)
    screen = qgv2.require_qgv2(json.loads((final / qgv2.FILENAME).read_bytes()))
    assert 'ROW_DATA_STALE' not in fl.observation_basis(screen, P.day(9).date())['evaluation']['reasons']
    check = published_check(final, P.day(9).date().isoformat())
    assert (check['stale_rows'], check['mixed_rows'], check['na_rows']) == (0, 0, 504 - len(AS.SPEC) + 1)
    row = P.rows(final, qgv2.FILENAME)[code]
    assert row['state'] == 'NOT_AVAILABLE' and row['acquired_at'] == P.rows(day0, qgv2.FILENAME)[code]['acquired_at']
