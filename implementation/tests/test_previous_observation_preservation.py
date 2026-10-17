"""Owner decision 2026-10-17 (option a): a verified previous observation survives a collection/identification failure,
connected to the pre-deploy freshness guard (PR #278, tools/pages_freshness_guard.py).

Every case runs the real daily generation path (tools/public_screens_pipeline.py collect for sec-public-inputs.json,
tools/sec_universe_shares.py run for the three Universe files) against an in-memory live Pages copy, then the guard on
the artifact. Synthetic SEC bytes, fake transports and injected clocks only: no network, credential or price.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import shutil
import sys

import pytest

from investment_system.markets.us import US_LISTINGS
from investment_system.providers.sec_collection import SecCollectionError, SecResponse
from investment_system.qgv import v2_factors as vf
from investment_system.universe import sec_qgv2 as qgv2
from investment_system.universe import sec_universe_qg as uqg
from investment_system.universe import sec_universe_shares as us
from investment_system.validation import forward_ledger as fl
from tests import test_sec_universe_all_shards as AS
from tests.test_pages_freshness_guard import Site, guard, guard_against, load_tool, section_line
from tests.test_public_sec_inputs import raw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
PIPE = load_tool('public_screens_pipeline')
INPUTS = load_tool('public_sec_inputs')
COVERAGE = load_tool('published_coverage')
UTC = timezone.utc
INPUTS_FILE = INPUTS.FILENAME
UNIVERSE = (us.FILENAME, uqg.FILENAME, qgv2.FILENAME)
ENV = {'SEC_USER_AGENT': 'synthetic setting'}


# ======================= TARGET: sec-public-inputs.json (public_screens_pipeline.collect) =======================
T1 = datetime(2026, 9, 1, 22, 0, tzinfo=UTC)
T2 = T1 + timedelta(days=1)
IDS = sorted(US_LISTINGS)
A, B, C = IDS[0], IDS[1], IDS[2]


def target_factory(when, failures=None, bodies=None):
    """SEC client for the 17 TARGET issuers: `failures` {company: exception}, `bodies` {company: (facts, subs) dicts}."""
    class Client:
        def __init__(self, _agent):
            pass

        def collect(self, company, cik):
            if company in (failures or {}):
                raise failures[company]
            facts, subs = (bodies or {}).get(company) or raw(company)
            return json.dumps(facts).encode(), json.dumps(subs).encode(), when
    return Client


def target_day(tmp_path, name, site, when, *, failures=None, bodies=None, read_live=True):
    """The daily TARGET step: read the live copy, collect, keep only sec-public-inputs.json as the artifact."""
    out = tmp_path / name
    out.mkdir()
    previous, state = PIPE.load_previous_inputs(open_response=site) if read_live else (None, 'UNAVAILABLE')
    result = PIPE.collect(out, environ=ENV, client_factory=target_factory(when, failures, bodies), previous=previous)
    artifact = tmp_path / (name + '-artifact')
    artifact.mkdir()
    shutil.copyfile(out / INPUTS_FILE, artifact / INPUTS_FILE)
    return artifact, result, state


def companies(folder):
    return {row['company_id']: row for row in json.loads((folder / INPUTS_FILE).read_bytes())['companies']}


def published_target(tmp_path, site):
    """Day 1: all 17 collected at T1 and deployed (first publication)."""
    first, result, state = target_day(tmp_path, 'day1', site, T1)
    assert state == 'NO_LIVE' and result['failed_companies'] == 0 and result['preserved'] == []
    site.deploy(first)
    return first


def collection_line(capsys, result, state):
    capsys.readouterr()
    INPUTS._print_collection(result, state)
    return capsys.readouterr().out


def test_a_target_partial_fetch_failure_keeps_the_previous_row_and_its_acquired_at_and_deploys(tmp_path, capsys):
    """(a) Day 2: A's fetch fails with HTTP 503, B's transport retries run out; both keep their T1 rows unchanged."""
    site = Site()
    first = published_target(tmp_path, site)
    failures = {A: SecCollectionError('SEC_HTTP_503', stage='fetch', http_status=503),
                B: SecCollectionError('SEC_TRANSPORT_RETRIES_EXHAUSTED')}
    artifact, result, state = target_day(tmp_path, 'day2', site, T2, failures=failures)
    before, after = companies(first), companies(artifact)
    assert state == 'LOADED'
    assert after[A] == before[A] and after[B] == before[B]                 # unchanged: acquired_at, sources, values
    assert after[A]['acquired_at'] == after[B]['acquired_at'] == '2026-09-01T22:00:00+00:00'
    assert all(after[c]['acquired_at'] == '2026-09-02T22:00:00+00:00' for c in IDS[2:])
    # Collection completeness stays visible: two failed collections, kept as preserved, never counted as success.
    assert result['failed_companies'] == 2 and result['collected_companies'] == 15
    assert result['preserved'] == [{'company_index': 1, 'code': 'SEC_HTTP_503'},
                                   {'company_index': 2, 'code': 'SEC_TRANSPORT_RETRIES_EXHAUSTED'}]
    out = collection_line(capsys, result, state)
    assert out == ('SEC_PRESERVED company_index=1 code=SEC_HTTP_503 previous=LIVE\n'
                   'SEC_PRESERVED company_index=2 code=SEC_TRANSPORT_RETRIES_EXHAUSTED previous=LIVE\n'
                   'SEC_PUBLIC_COLLECTION companies=17 collected=15 failed=2 preserved_previous=2 not_available=0 '
                   'previous=LOADED\n')
    code, out = guard(artifact, site, capsys)
    line = section_line(out, INPUTS_FILE, 'companies')
    assert code == 0 and (line['verdict'], line['compared'], line['equal'], line['newer']) == ('PASS', '17', '2', '15')


def test_d_target_row_loss_is_still_refused_when_no_previous_row_could_be_read(tmp_path, capsys):
    """(d) The live copy could not be read at collection time (preservation off): the failed company is NOT_AVAILABLE
    without acquired_at and the guard refuses that real loss."""
    site = Site()
    published_target(tmp_path, site)
    failures = {A: SecCollectionError('SEC_HTTP_503', stage='fetch', http_status=503)}
    artifact, result, state = target_day(tmp_path, 'day2', site, T2, failures=failures, read_live=False)
    assert companies(artifact)[A]['status'] == 'NOT_AVAILABLE' and result['preserved'] == []
    assert collection_line(capsys, result, state).endswith('preserved_previous=0 not_available=1 previous=UNAVAILABLE\n')
    code, out = guard(artifact, site, capsys)
    assert code == 1 and f'code={A} kind=LOST_RECORD artifact=NONE live=2026-09-01T22:00:00Z\n' in out


@pytest.mark.parametrize('error, reason', [
    (SecCollectionError('SEC_CIK_MISMATCH', stage='parse'), 'SEC_CIK_MISMATCH'),          # response of another CIK
    (SecCollectionError('SEC_ISSUER_NOT_ALLOWED'), 'SEC_ISSUER_NOT_ALLOWED'),              # issuer outside the scope
    (SecCollectionError('SEC_HTTP_404', stage='fetch', http_status=404), 'SEC_HTTP_404'),  # SEC resource absent
    (ValueError('unknown'), 'SEC_COLLECTION_FAILED'),                                      # not a known transient failure
])
def test_e_target_identity_conflicts_and_non_transient_failures_are_not_preserved(tmp_path, capsys, error, reason):
    """(e) Never preserved: the row is NOT_AVAILABLE with its fixed reason. Its live row had a collection record, so the
    guard refuses the deploy (fail closed) instead of carrying the old values."""
    site = Site()
    published_target(tmp_path, site)
    artifact, result, _ = target_day(tmp_path, 'day2', site, T2, failures={A: error})
    row = companies(artifact)[A]
    assert row['status'] == 'NOT_AVAILABLE' and row['reason_codes'] == [reason] and 'acquired_at' not in row
    assert result['preserved'] == [] and result['failed_companies'] == 1
    code, out = guard(artifact, site, capsys)
    assert code == 1 and f'code={A} kind=LOST_RECORD ' in out


def test_f_target_policy_na_of_a_successful_collection_is_not_overwritten_by_the_old_row(tmp_path, capsys):
    """(f) A's SEC bytes arrive but carry no share concept: SEC_SHARE_CONCEPT_MISSING (normalize stage) is the result
    of today's collection and is published as such, never replaced by the T1 values. The NOT_AVAILABLE schema of this
    file has no acquired_at, so the guard reports the live T1 record as lost and refuses (fail closed)."""
    site = Site()
    published_target(tmp_path, site)
    facts, subs = raw(A)
    facts = dict(facts, facts={'dei': {}})
    artifact, result, _ = target_day(tmp_path, 'day2', site, T2, bodies={A: (facts, subs)})
    row = companies(artifact)[A]
    assert (row['status'], row['reason_codes'], row['failure_stage']) == ('NOT_AVAILABLE', ['SEC_SHARE_CONCEPT_MISSING'], 'normalize')
    assert result['preserved'] == []
    code, out = guard(artifact, site, capsys)
    assert code == 1 and f'code={A} kind=LOST_RECORD ' in out


def test_target_previous_copy_of_an_older_schema_is_not_used_for_preservation(tmp_path):
    previous = INPUTS.require_public_inputs(json.loads((published_target(tmp_path, Site()) / INPUTS_FILE).read_bytes()))
    assert set(INPUTS.previous_rows(previous)) == set(IDS)
    assert INPUTS.previous_rows(dict(previous, schema='public-sec-reported-inputs/2')) == {}


# ======================= Universe: the three shard files (tools/sec_universe_shares.py run) =======================
DAY0 = datetime(2026, 9, 20, 23, 0, tzinfo=UTC)


def day(n):
    return DAY0 + timedelta(days=n)


def shard_today(n):
    return day(n).date().toordinal() % 7


def members(n):
    return [cik for _, cik, _, _ in AS.SPEC if AS.shard_of(cik) == shard_today(n)]


def outside(*days):
    """Synthetic issuers whose shard is collected on none of `days`."""
    return [cik for _, cik, _, _ in AS.SPEC if AS.shard_of(cik) not in {shard_today(k) for k in days}]


def fresh_cik(shard):
    """A CIK outside the synthetic Universe whose daily shard is `shard` (a new holder of a reused ticker)."""
    return next(c for c in (str(900000 + i).zfill(10) for i in range(500)) if AS.shard_of(c) == shard)


def empty_bytes(cik, code):
    """An issuer without annual SEC financials (its submissions still list the ticker)."""
    ticker, exchange = AS.sec_ticker(code)
    subs = {'cik': int(cik), 'sic': '3674', 'tickers': [ticker], 'exchanges': [exchange], 'filings': {'recent': {
        'accessionNumber': [], 'form': [], 'filingDate': [], 'reportDate': [], 'acceptanceDateTime': [], 'primaryDocument': []}}}
    return json.dumps({'cik': int(cik), 'facts': {}}).encode(), json.dumps(subs).encode()


class Sec(AS.Sec):
    """all-shards fake SEC plus registry and identity changes:
    hidden: CIKs missing from today's ticker file (symbol unresolved); claims: extra (cik, code) ticker claims (one
    code claimed by several CIKs); rebind: {code: new CIK} (ticker reuse, the new holder has no annual financials);
    unticked: CIKs whose submissions no longer list the ticker; mismatch: CIKs whose SEC response names another CIK."""

    def __init__(self, *, hidden=(), claims=(), rebind=None, unticked=(), mismatch=(), **kwargs):
        super().__init__(**kwargs)
        self.hidden, self.claims, self.rebind = set(hidden), list(claims), dict(rebind or {})
        self.unticked, self.mismatch = set(unticked), set(mismatch)

    def ticker_body(self):
        rows = [[int(self.rebind.get(code, cik)), 'Synthetic', *AS.sec_ticker(code)]
                for code, cik, _, _ in AS.SPEC if cik not in self.hidden]
        rows += [[int(cik), 'Synthetic', *AS.sec_ticker(code)] for cik, code in self.claims]
        return json.dumps({'fields': ['cik', 'name', 'ticker', 'exchange'], 'data': rows}).encode()

    def transport(self, url, *, headers, timeout, max_body_bytes):
        self.calls.append((url, self.clock[0], headers['User-Agent']))
        if url.endswith('company_tickers_exchange.json'):
            return SecResponse(200, self.ticker_body(), final_url=url)
        cik = url.split('CIK')[-1].split('.')[0]
        if cik in self.fail:
            return SecResponse(403, b'', final_url=url)
        reused = {new: code for code, new in self.rebind.items()}
        facts, subs = empty_bytes(cik, reused[cik]) if cik in reused else AS.issuer_bytes(cik, empty=cik in self.empty)
        if cik in self.unticked:
            value = json.loads(subs)
            subs = json.dumps(dict(value, tickers=[], exchanges=[])).encode()
        body = facts if 'companyfacts' in url else subs
        if cik in self.mismatch:
            body = json.dumps(dict(json.loads(body), cik=int(cik) + 1)).encode()
        return SecResponse(200, body, final_url=url)


def run(tmp_path, name, sec, n, previous=None, *, all_shards=False):
    tool = load_tool('sec_universe_shares')
    out = tmp_path / name
    assert AS.run(tool, out, sec, when=day(n), previous=previous, all_shards=all_shards) == 0
    return out


def rows(folder, name):
    return json.loads((folder / name).read_bytes())['records']


COLLECTION = re.compile(r'SEC_UNIVERSE_COLLECTION shard=(?:\d+|all)/7 issuers=\d+ collected=\d+ failed=\d+ unresolved_codes=\d+ '
                        r'preserved_previous_shares=\d+ preserved_previous_qg=\d+ preserved_previous_qgv2=\d+ '
                        r'preserved_unconfirmed=\d+ identity_not_preserved=\d+')


def collection_counts(out):
    lines = [l for l in out.splitlines() if l.startswith('SEC_UNIVERSE_COLLECTION ')]
    assert len(lines) == 1 and COLLECTION.fullmatch(lines[0]), out
    return dict(part.split('=', 1) for part in lines[0].split()[2:])


@pytest.fixture(scope='module')
def baseline(tmp_path_factory):
    """Day 0: one all-shards publication of the 27 synthetic issuers; E has no annual SEC financials (a NOT_AVAILABLE
    row WITH a collection record in all three files)."""
    folder = tmp_path_factory.mktemp('baseline')
    e = outside(1, 2)[0]
    out = run(folder, 'day0', Sec(empty={e}), 0, all_shards=True)
    return out, e


def test_b_unresolved_symbol_keeps_a_verified_na_row_with_its_collection_record(tmp_path, capsys, baseline):
    """(b) Day 1: E's ticker is missing from SEC's ticker file. Before: the daily merge reset E's collected NA rows to
    CIK_UNRESOLVED with acquired_at null and the guard refused (LOST_RECORD). Now the rows stay unchanged."""
    day0, e = baseline
    code_e = AS.CODE[e]
    for name in UNIVERSE:
        assert rows(day0, name)[code_e]['state'] == 'NOT_AVAILABLE' and rows(day0, name)[code_e]['acquired_at'] is not None
    capsys.readouterr()
    day1 = run(tmp_path, 'day1', Sec(empty={e}, hidden={e}), 1, previous=day0)
    counts = collection_counts(capsys.readouterr().out)
    for name in UNIVERSE:
        assert rows(day1, name)[code_e] == rows(day0, name)[code_e]
    assert counts['preserved_unconfirmed'] == '1' and counts['identity_not_preserved'] == '0'
    assert counts['collected'] == str(len(members(1))) and counts['failed'] == '0'
    assert counts['preserved_previous_qgv2'] == counts['preserved_previous_qg'] == '1'
    code, out = guard_against(day1, day0, capsys)
    assert code == 0 and ' rows_regressed=0 ' in out
    for name in UNIVERSE:
        assert section_line(out, name, 'records')['newer'] == str(len(members(1)))


def test_b_symbol_missing_from_the_submissions_keeps_the_verified_shares_row(tmp_path, capsys, baseline):
    """(b) Day 1: U is collected but its submissions no longer list its ticker (shares identity unconfirmed for that
    code, same CIK): the shares row of day 0 stays; Q·G rows are new observations of the same bytes and update."""
    day0, _ = baseline
    u = members(1)[0]
    code_u = AS.CODE[u]
    assert rows(day0, us.FILENAME)[code_u]['listing_id'] is not None
    capsys.readouterr()
    day1 = run(tmp_path, 'day1', Sec(unticked={u}), 1, previous=day0)
    counts = collection_counts(capsys.readouterr().out)
    assert rows(day1, us.FILENAME)[code_u] == rows(day0, us.FILENAME)[code_u]
    assert rows(day1, qgv2.FILENAME)[code_u]['acquired_at'] > rows(day0, qgv2.FILENAME)[code_u]['acquired_at']
    assert counts['preserved_unconfirmed'] == '1' and counts['preserved_previous_shares'] == '1'
    assert counts['preserved_previous_qgv2'] == '0'
    code, out = guard_against(day1, day0, capsys)
    assert code == 0 and section_line(out, us.FILENAME, 'records')['equal'] == str(27 - len(members(1)) + 1)


def test_iii_builder_failure_is_no_new_observation_and_keeps_the_verified_row(tmp_path, capsys, baseline, monkeypatch):
    """(iii) The QGV v2 builder fails for U after a successful fetch (tool fallback: INVALID_INPUT without a collection
    record). It is not a confirmed invalid input of a successful collection: U's verified row of day 0 stays."""
    day0, _ = baseline
    u = members(1)[1]
    original = qgv2.build_issuer_records

    def failing(*, cik, **kwargs):
        if cik == u:
            raise RuntimeError('builder failure')
        return original(cik=cik, **kwargs)
    monkeypatch.setattr(qgv2, 'build_issuer_records', failing)
    capsys.readouterr()
    day1 = run(tmp_path, 'day1', Sec(), 1, previous=day0)
    counts = collection_counts(capsys.readouterr().out)
    assert rows(day1, qgv2.FILENAME)[AS.CODE[u]]['acquired_at'] == rows(day0, qgv2.FILENAME)[AS.CODE[u]]['acquired_at']
    assert rows(day1, qgv2.FILENAME)[AS.CODE[u]]['fiscal_year_end'] is not None
    assert counts['preserved_unconfirmed'] == '1' and counts['preserved_previous_qgv2'] == '1'
    code, out = guard_against(day1, day0, capsys)
    assert code == 0 and ' rows_regressed=0 ' in out


def test_iii_a_row_rejected_by_the_strict_check_keeps_the_verified_row_of_the_same_issuer(baseline):
    """(iii) merge-time INVALID_INPUT downgrade: the rejected row records no verified collection, so the verified row of
    the same CIK stays; for another CIK nothing is kept."""
    day0, _ = baseline
    previous = qgv2.require_qgv2(json.loads((day0 / qgv2.FILENAME).read_bytes()))
    code = AS.SPEC[3][0]
    bad = dict(previous['records'][code], acquired_at='2099-01-01T00:00:00Z')    # after the publication time: rejected
    stats = {}
    merged = qgv2.merge(previous, {code: bad}, as_of=day(1), shard_index=0, stats=stats)
    assert merged['records'][code]['acquired_at'] == previous['records'][code]['acquired_at'] and stats['preserved'] == {code}
    other = dict(bad, cik='0000999999')
    merged = qgv2.merge(previous, {code: other}, as_of=day(1), shard_index=0, stats=stats)
    assert merged['records'][code]['reason_codes'] == ['INVALID_INPUT'] and merged['records'][code]['acquired_at'] is None
    assert stats['identity_not_preserved'] == {code}


def test_c_a_preserved_row_ages_by_its_original_acquired_at(tmp_path, capsys, baseline):
    """(c) D's ticker disappears from day 1 on. Every other issuer is collected again within days 1..7, D never: its
    rows keep the day-0 acquired_at, so the 7-day rule marks the basis ROW_DATA_STALE from day 8 and the 14-day window
    makes the QGV v2 row STALE on day 15. The guard passes each day (equal record, nothing lost)."""
    day0, e = baseline
    d = next(cik for _, cik, _, _ in AS.SPEC if cik != e)
    code_d = AS.CODE[d]
    original = {name: rows(day0, name)[code_d]['acquired_at'] for name in UNIVERSE}
    previous = day0
    for n in range(1, 16):
        previous = run(tmp_path, f'day{n}', Sec(empty={e}, hidden={d}), n, previous=previous)
        screen = qgv2.require_qgv2(json.loads((previous / qgv2.FILENAME).read_bytes()))
        assert {name: rows(previous, name)[code_d]['acquired_at'] for name in UNIVERSE} == original
        basis = fl.observation_basis(screen, day(n).date())
        if n in (7, 8):
            assert basis['acquired'][0] == day(0).date().isoformat()    # the oldest row used is D's preserved row
            assert ('ROW_DATA_STALE' in basis['evaluation']['reasons']) == (n == 8)
            stale_7d = int(re.search(r' stale_7d_rows=(\d+) ', COVERAGE.coverage_line(screen)).group(1))
            assert stale_7d == (0 if n == 7 else 1)
        if n == 8:
            day8 = previous
            assert rows(previous, qgv2.FILENAME)[code_d]['state'] == 'LIVE'
    # The synthetic bytes give QGV v2 data (shares and Q·G v1 rows of these issuers are NA with their record).
    row = rows(previous, qgv2.FILENAME)[code_d]
    assert (row['state'], row['reason_codes'], row['fiscal_year_end'] is not None) == ('STALE', ['STALE_INPUT'], True)
    capsys.readouterr()
    code, out = guard_against(previous, day8, capsys)
    assert code == 0 and ' rows_regressed=0 ' in out


def test_d_new_observations_update_and_an_older_artifact_is_still_refused(tmp_path, capsys, baseline):
    """(d) Day 1 and day 2 collect their shards normally (newer rows); the day-1 artifact deployed after day 2 is refused."""
    day0, _ = baseline
    day1 = run(tmp_path, 'day1', Sec(), 1, previous=day0)
    day2 = run(tmp_path, 'day2', Sec(), 2, previous=day1)
    code, out = guard_against(day2, day1, capsys)
    assert code == 0 and section_line(out, qgv2.FILENAME, 'records')['newer'] == str(len(members(2)))
    code, out = guard_against(day1, day2, capsys)
    assert code == 1 and section_line(out, qgv2.FILENAME, 'records')['older'] == str(len(members(2)))


def test_e_ticker_reuse_never_carries_the_previous_issuers_values(tmp_path, capsys, baseline):
    """(e) Day 1: D's ticker now belongs to another CIK (collected today, no annual financials). Before, the daily merge
    kept D's values under the code because the new row had none. Now the new issuer's NOT_AVAILABLE rows are published
    with their own collection record and reason; the guard passes (newer record)."""
    day0, _ = baseline
    d = members(1)[0]
    code_d = AS.CODE[d]
    assert rows(day0, qgv2.FILENAME)[code_d]['fiscal_year_end'] is not None
    new = fresh_cik(shard_today(1))
    capsys.readouterr()
    day1 = run(tmp_path, 'day1', Sec(rebind={code_d: new}), 1, previous=day0)
    counts = collection_counts(capsys.readouterr().out)
    for name in UNIVERSE:
        row = rows(day1, name)[code_d]
        assert row['cik'] == new and row['state'] == 'NOT_AVAILABLE' and row['acquired_at'] > rows(day0, name)[code_d]['acquired_at']
    assert rows(day1, qgv2.FILENAME)[code_d]['reason_codes'] == ['NO_ANNUAL_SEC_FINANCIALS']
    assert rows(day1, us.FILENAME)[code_d]['shares'] is None
    assert counts['identity_not_preserved'] == '1' and counts['preserved_unconfirmed'] == '0'
    code, out = guard_against(day1, day0, capsys)
    assert code == 0 and ' rows_regressed=0 ' in out


def test_e_a_ticker_claimed_by_several_ciks_is_not_preserved(tmp_path, capsys, baseline):
    """(e) Day 1: E's ticker is claimed by E and another CIK. Identity is not confirmed: E's NA row is not preserved
    (CIK_UNRESOLVED, no record) and the guard refuses the deploy (fail closed)."""
    day0, e = baseline
    code_e = AS.CODE[e]
    capsys.readouterr()
    day1 = run(tmp_path, 'day1', Sec(empty={e}, claims=[(fresh_cik(0), code_e)]), 1, previous=day0)
    counts = collection_counts(capsys.readouterr().out)
    for name in UNIVERSE:
        row = rows(day1, name)[code_e]
        assert row['reason_codes'] == ['CIK_UNRESOLVED'] and row['acquired_at'] is None and row['cik'] is None
    assert counts['preserved_unconfirmed'] == '0'
    code, out = guard_against(day1, day0, capsys)
    assert code == 1 and f'code={code_e} kind=LOST_RECORD ' in out


def test_e_a_response_naming_another_cik_is_not_preserved(tmp_path, capsys, baseline):
    """(e) Day 1: SEC answers M's request with another CIK (SEC_CIK_MISMATCH). Before, M's rows were kept as a failed
    issuer. Now they are NOT_AVAILABLE with the reason (shares CIK_MISMATCH, Q·G INVALID_INPUT): no values carried; the
    guard refuses (fail closed) because the response is not a collection record."""
    day0, _ = baseline
    m = members(1)[0]
    code_m = AS.CODE[m]
    capsys.readouterr()
    day1 = run(tmp_path, 'day1', Sec(mismatch={m}), 1, previous=day0)
    out = capsys.readouterr().out
    counts = collection_counts(out)
    assert 'code=SEC_CIK_MISMATCH' in out and counts['failed'] == '1' and counts['identity_not_preserved'] == '1'
    assert rows(day1, us.FILENAME)[code_m]['reason_codes'] == ['CIK_MISMATCH']
    for name in (uqg.FILENAME, qgv2.FILENAME):
        assert rows(day1, name)[code_m]['reason_codes'] == ['INVALID_INPUT'] and rows(day1, name)[code_m]['acquired_at'] is None
    code, out = guard_against(day1, day0, capsys)
    assert code == 1 and f'code={code_m} kind=LOST_RECORD ' in out


def test_f_a_successful_collection_with_a_policy_na_is_published_not_the_old_row(tmp_path, capsys, baseline):
    """(f) E is collected again (its shard on day k): still no annual financials. The new NA rows (newer record) replace
    the old ones; nothing is preserved. The one-off all-shards publication turns a code with data into NA with its
    reason (never the old value) and deploys."""
    day0, e = baseline
    k = next(n for n in range(1, 8) if e in members(n))
    capsys.readouterr()
    dayk = run(tmp_path, 'dayk', Sec(empty={e}), k, previous=day0)
    counts = collection_counts(capsys.readouterr().out)
    for name in UNIVERSE:
        assert rows(dayk, name)[AS.CODE[e]]['acquired_at'] > rows(day0, name)[AS.CODE[e]]['acquired_at']
    assert counts['preserved_unconfirmed'] == '0'
    d = next(cik for cik in members(k) if cik != e)
    refreshed = run(tmp_path, 'all', Sec(empty={e, d}), k, previous=day0, all_shards=True)
    row = rows(refreshed, qgv2.FILENAME)[AS.CODE[d]]
    assert row['state'] == 'NOT_AVAILABLE' and row['reason_codes'] == ['NO_ANNUAL_SEC_FINANCIALS'] and row['calc_version'] is None
    code, out = guard_against(refreshed, day0, capsys)
    assert code == 0 and ' rows_regressed=0 ' in out


def test_g_a_preserved_row_of_an_older_calc_version_stays_outside_the_ranking(tmp_path, capsys, monkeypatch):
    """(g) Day 0 published under the previous calc_version; on day 1 (current version) D's ticker is unresolved and its
    row is preserved with the old calc_version: excluded (CALC_VERSION_MISMATCH axes, no factor score, not in the
    cross-section) and the basis reports CALC_VERSION_MIXED. The guard passes (record unchanged)."""
    old_version = 'qgv2-calc/2026-10-15.1'
    d = outside(1)[0]
    with monkeypatch.context() as patch:
        patch.setattr(vf, 'CALC_VERSION', old_version)
        day0 = run(tmp_path, 'day0', Sec(), 0, all_shards=True)
    day1 = run(tmp_path, 'day1', Sec(hidden={d}), 1, previous=day0)
    screen = qgv2.require_qgv2(json.loads((day1 / qgv2.FILENAME).read_bytes()))
    row = screen['records'][AS.CODE[d]]
    assert screen['calc_version'] == vf.CALC_VERSION != old_version
    assert row['calc_version'] == old_version and row['acquired_at'] == rows(day0, qgv2.FILENAME)[AS.CODE[d]]['acquired_at']
    assert row['fiscal_year_end'] is not None and row['state'] == 'LIVE'
    assert all(axis['reason_codes'] == ['CALC_VERSION_MISMATCH'] and axis['score'] is None for axis in row['axes'].values())
    assert all(score is None for score in row['factors'].values())
    current = [r for r in screen['records'].values() if r['calc_version'] == vf.CALC_VERSION]
    assert screen['cross_section_size'] == len({r['cik'] for r in current})
    assert 'CALC_VERSION_MIXED' in fl.observation_basis(screen, day(1).date())['evaluation']['reasons']
    code, out = guard_against(day1, day0, capsys)
    assert code == 0 and ' rows_regressed=0 ' in out
