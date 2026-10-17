"""Owner follow-up 2026-10-17 (after PR #278) on the three Universe files (sec-universe-shares.json, sec-universe-qg.json,
sec-qgv2.json):

1. A ticker claimed by several CIKs is an identity conflict with no row this run: the kept row is withdrawn also when it
   has values (before, `previous_decision` returned None for a missing row and the merges re-selected the kept values).
   The code is published CIK_UNRESOLVED without acquired_at (detecting a conflict is not a collection), so the
   pre-deploy freshness guard refuses the deploy as LOST_RECORD (fail closed).
2. A successful collection whose result is NOT_AVAILABLE or INVALID_INPUT is published, also by the DAILY merge, never
   replaced by an older value (before, the M3 option-a daily rule kept the older value); a transient failure (fetch
   failure, the cover filing fetch failing after the bytes arrived) or an identification failure still keeps the
   verified previous row. Daily and --all-shards publish the same rows for the same observation.

Every case runs the real generation path (tools/sec_universe_shares.py run, tools/public_screens_pipeline.py
stage_qgv2_target), the merges and the guard on synthetic SEC bytes, fake transports and injected clocks only.
"""
from datetime import datetime, timedelta, timezone
import json

import pytest

from investment_system.providers.sec_collection import SecResponse
from investment_system.universe import sec_qgv2 as qgv2
from investment_system.universe import sec_universe_qg as uqg
from investment_system.universe import sec_universe_shares as us
from tests import test_previous_observation_preservation as P
from tests import test_sec_universe_all_shards as AS
from tests import test_sec_universe_qg as QG
from tests import test_sec_universe_shares as SH
from tests.test_pages_freshness_guard import TARGET_SEED, guard_against, load_tool, section_line

UNIVERSE = (us.FILENAME, uqg.FILENAME, qgv2.FILENAME)
# After the 10-Q of the synthetic bytes (filed 2026-10-01): a share count is only valid once it was filed.
DAY0 = datetime(2026, 10, 20, 23, 0, tzinfo=timezone.utc)


def day(n):
    return DAY0 + timedelta(days=n)


def stamp(when):
    return when.isoformat().replace('+00:00', 'Z')


def shard(n):
    return day(n).date().toordinal() % 7


def members(n):
    return [cik for _, cik, _, _ in AS.SPEC if AS.shard_of(cik) == shard(n)]


def rich_bytes(cik, *, ambiguous=False):
    """Bytes with values in all three files: a 10-Q share count (single class, confirmed by the served cover filing),
    four annual revenues (Q·G v1 scores) and QGV v2 data. `ambiguous` adds a second count for the same date: without
    the cover filing no count can be published."""
    facts, subs = QG.sec_bytes(cik, *AS.sec_ticker(AS.CODE[cik]))
    if ambiguous:
        value = json.loads(facts)
        rows = value['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares']
        rows.append(dict(rows[0], val=50))
        facts = json.dumps(value).encode()
    return facts, subs


class Sec(P.Sec):
    """P.Sec plus `rich` CIKs (rich_bytes, cover filing served), `ambiguous` CIKs and `cover_fail` CIKs whose cover
    filing request answers HTTP 503 every time (a transient failure after their companyfacts/submissions arrived)."""

    def __init__(self, *, rich=(), ambiguous=(), cover_fail=(), **kwargs):
        super().__init__(**kwargs)
        self.rich, self.ambiguous, self.cover_fail = set(rich), set(ambiguous), set(cover_fail)

    def transport(self, url, *, headers, timeout, max_body_bytes):
        if '/Archives/' in url:
            self.calls.append((url, self.clock[0], headers['User-Agent']))
            cik = url.split('/data/')[1].split('/')[0].zfill(10)
            if cik in self.cover_fail:
                return SecResponse(503, b'', final_url=url)
            return SecResponse(200, SH.cover(cik, AS.sec_ticker(AS.CODE[cik])[0]), final_url=url)
        cik = url.split('CIK')[-1].split('.')[0]
        if cik in self.rich - self.empty - self.fail and not url.endswith('company_tickers_exchange.json'):
            self.calls.append((url, self.clock[0], headers['User-Agent']))
            facts, subs = rich_bytes(cik, ambiguous=cik in self.ambiguous)
            return SecResponse(200, facts if 'companyfacts' in url else subs, final_url=url)
        return super().transport(url, headers=headers, timeout=timeout, max_body_bytes=max_body_bytes)


def run(tmp_path, name, sec, n, previous=None, *, all_shards=False, out=None):
    out = out or tmp_path / name
    assert AS.run(load_tool('sec_universe_shares'), out, sec, when=day(n), previous=previous, all_shards=all_shards) == 0
    return out


def rows(folder, name):
    return json.loads((folder / name).read_bytes())['records']


def has_values(name, row):
    if name == us.FILENAME:
        return row['shares'] is not None
    if name == uqg.FILENAME:
        return any(v is not None for v in row['factors'].values())
    return row['fiscal_year_end'] is not None


@pytest.fixture(scope='module')
def published(tmp_path_factory):
    """Day 0: one all-shards publication; X and Y (both in day 1's shard) have LIVE values in all three files."""
    x, y = members(1)[:2]
    out = run(tmp_path_factory.mktemp('published'), 'day0', Sec(rich={x, y}), 0, all_shards=True)
    for cik in (x, y):
        for name in UNIVERSE:
            row = rows(out, name)[AS.CODE[cik]]
            assert row['state'] == 'LIVE' and has_values(name, row) and row['acquired_at'] == stamp(day(0)), (name, cik)
    assert rows(out, us.FILENAME)[AS.CODE[x]]['share_class_basis'] == 'SINGLE_CLASS_CONFIRMED'
    return out, x, y


# ---------------- 1. identity conflict with a kept row that HAS values ----------------
@pytest.mark.parametrize('all_shards', [False, True], ids=['daily', 'all_shards'])
def test_a_ticker_claimed_by_several_ciks_withdraws_a_kept_row_with_values(tmp_path, capsys, published, all_shards):
    """Day 1: X's ticker is also claimed by another CIK in SEC's ticker file, so X has no row this run. Before, the
    kept LIVE values stayed in all three files (decision None, kept by the 'no new row' branches and `_pick`). Now they
    are withdrawn: CIK_UNRESOLVED, no CIK, no acquired_at. The live rows carry a collection record and the artifact
    rows none, so the guard refuses the deploy (LOST_RECORD, fail closed) for exactly this code in each file."""
    day0, x, y = published
    code_x = AS.CODE[x]
    capsys.readouterr()
    day1 = run(tmp_path, 'day1', Sec(rich={x, y}, claims=[(P.fresh_cik(0), code_x)]), 1, previous=day0,
               all_shards=all_shards)
    counts = P.collection_counts(capsys.readouterr().out)
    for name in UNIVERSE:
        row = rows(day1, name)[code_x]
        assert (row['state'], row['reason_codes'], row['cik'], row['acquired_at']) == ('NOT_AVAILABLE', ['CIK_UNRESOLVED'], None, None)
        assert not has_values(name, row) and all(v is None for v in row['source_sha256'].values())
        assert rows(day1, name)[AS.CODE[y]]['acquired_at'] == stamp(day(1))         # Y collected normally
    assert rows(day1, qgv2.FILENAME)[code_x]['metrics'] == {} and rows(day1, qgv2.FILENAME)[code_x]['calc_version'] is None
    assert counts['identity_not_preserved'] == '1' and counts['preserved_unconfirmed'] == '0'
    code, out = guard_against(day1, day0, capsys)
    assert code == 1 and 'PAGES_FRESHNESS_REFUSED ' in out and ' rows_regressed=3 ' in out
    for name in UNIVERSE:
        assert (f'PAGES_FRESHNESS_REGRESSION file={name} section=records code={code_x} kind=LOST_RECORD '
                f'artifact=NONE live={stamp(day(0))}\n') in out
        assert section_line(out, name, 'records')['lost_record'] == '1'


def test_withdrawal_needs_no_kept_record_and_never_invents_one():
    """Merge level: a conflicting code without a row this run is withdrawn whatever the kept row is."""
    code = AS.SPEC[0][0]
    kept = {us.FILENAME: us.empty_record(), uqg.FILENAME: uqg.empty_record(), qgv2.FILENAME: qgv2.empty_record()}
    for module, name in ((us, us.FILENAME), (uqg, uqg.FILENAME), (qgv2, qgv2.FILENAME)):
        assert us.previous_decision(kept[name], None, code=code, unresolved={code}, conflicts={code},
                                    new_observation=lambda r: True) == us.IDENTITY_CONFLICT
        stats = {}
        merged = module.merge(None, {}, as_of=day(1), shard_index=0, unresolved={code}, conflicts={code}, stats=stats)
        row = merged['records'][code]
        assert (row['reason_codes'], row['acquired_at'], row['cik']) == (['CIK_UNRESOLVED'], None, None)
        assert stats == {}            # nothing kept, no record of another identity dropped


# ---------------- 2. a successful collection's NA vs a transient failure, daily and all-shards ----------------
def test_new_na_of_a_successful_collection_is_published_and_daily_equals_all_shards(tmp_path, capsys, published):
    """Day 1, X's shard: X's bytes arrive but have no shares concept, no annual financials and no filings (shares
    COVER_NOT_AVAILABLE with listing_id, Q·G M1_NOT_AVAILABLE, QGV v2 NO_ANNUAL_SEC_FINANCIALS: NA of a successful
    collection). Before, the daily merge kept X's day-0 values in all three files (the one-off all-shards run published
    the NA in Q·G and QGV v2 only). Now both paths publish the new NA rows with acquired_at day 1 and their reasons.
    Y's bytes arrive too but its cover filing request fails (transient) and its two share counts for one date leave no
    count without the cover: Y's verified shares row of day 0 is kept unchanged (Q·G rows of Y are new observations).
    The daily run and an all-shards run of the same day, in which only that shard succeeds, write identical files."""
    day0, x, y = published
    code_x, code_y = AS.CODE[x], AS.CODE[y]
    others = [cik for _, cik, _, _ in AS.SPEC if AS.shard_of(cik) != shard(1)]
    sec = lambda: Sec(rich={x, y}, empty={x}, ambiguous={y}, cover_fail={y}, fail=others)
    capsys.readouterr()
    daily = run(tmp_path, 'daily', sec(), 1, previous=day0)
    counts = P.collection_counts(capsys.readouterr().out)
    every = run(tmp_path, 'all', sec(), 1, previous=day0, all_shards=True)
    out = capsys.readouterr().out
    assert 'ALL_SHARDS_PARTIAL' in out and f'SEC_UNIVERSE_SHARD shard={shard(1)}/7 ' in out
    for name in UNIVERSE:
        assert (daily / name).read_bytes() == (every / name).read_bytes(), name
    reasons = {us.FILENAME: ['COVER_NOT_AVAILABLE'], uqg.FILENAME: ['M1_NOT_AVAILABLE'], qgv2.FILENAME: ['NO_ANNUAL_SEC_FINANCIALS']}
    for name in UNIVERSE:
        row = rows(daily, name)[code_x]
        assert (row['state'], row['reason_codes'], row['acquired_at'], row['cik']) == ('NOT_AVAILABLE', reasons[name], stamp(day(1)), x)
        assert not has_values(name, row) and has_values(name, rows(day0, name)[code_x])
    assert rows(daily, us.FILENAME)[code_x]['listing_id'] is not None                  # identity confirmed this run
    assert rows(daily, us.FILENAME)[code_y] == rows(day0, us.FILENAME)[code_y]           # transient: kept unchanged
    assert rows(daily, uqg.FILENAME)[code_y]['acquired_at'] == stamp(day(1))
    assert counts['preserved_unconfirmed'] == '1' and counts['preserved_previous_shares'] == '1'
    capsys.readouterr()
    code, out = guard_against(daily, day0, capsys)
    assert code == 0 and ' rows_regressed=0 ' in out
    assert section_line(out, us.FILENAME, 'records')['equal'] == str(len(AS.SPEC) - len(members(1)) + 1)


def test_a_shares_row_without_a_count_after_a_cover_failure_is_no_new_observation():
    """Merge level: the same row is a new observation (published over the kept count) when the cover was fetched,
    and no new observation (the verified kept row stays) when this run's cover fetch failed for the code."""
    code, cik, _, _ = AS.SPEC[0]
    facts, subs = rich_bytes(cik)
    acc = cik + '-26-000009'
    kept = us.build_issuer_records(codes=(code,), cik=cik, companyfacts_body=facts, submissions_body=subs, acquired_at=day(0),
                                   as_of=day(0), cover_xml=SH.cover(cik, AS.sec_ticker(code)[0]), cover_accession=acc,
                                   cover_acquired_at=day(0))[0]
    previous = us.merge(None, kept, as_of=day(0), shard_index=0)
    amb, _ = rich_bytes(cik, ambiguous=True)
    new = us.build_issuer_records(codes=(code,), cik=cik, companyfacts_body=amb, submissions_body=subs, acquired_at=day(1), as_of=day(1))[0]
    assert new[code]['shares'] is None and new[code]['listing_id'] is not None and new[code]['reason_codes'] == ['COVER_NOT_AVAILABLE']
    published = us.merge(previous, new, as_of=day(1), shard_index=0)
    assert published['records'][code]['shares'] is None and published['records'][code]['acquired_at'] == stamp(day(1))
    stats = {}
    transient = us.merge(previous, new, as_of=day(1), shard_index=0, transient={code}, stats=stats)
    assert transient['records'][code] == previous['records'][code] and stats == {'preserved': {code}}


def test_target_na_of_a_successful_collection_replaces_kept_target_data(tmp_path, capsys):
    """TARGET section of sec-qgv2.json through the real staging (public_screens_pipeline.stage_qgv2_target) and the
    shard tool. Day 1: nvda's bytes arrive without annual financials; msft is not collected (fetch failure). Before,
    `target_updates_from` dropped the staged NA row and the merge kept nvda's day-0 data. Now nvda is NOT_AVAILABLE with
    acquired_at day 1 and msft keeps its day-0 row; the guard passes (newer + equal record)."""
    pipe = load_tool('public_screens_pipeline')

    def stage(out, n, bodies):
        root = tmp_path / f'raw{n}'
        root.mkdir()
        manifest = {'sec': []}
        for cid, (facts, subs) in bodies.items():
            (root / f'{cid}-f.json').write_bytes(facts)
            (root / f'{cid}-s.json').write_bytes(subs)
            manifest['sec'].append({'company_id': cid, 'companyfacts': f'{cid}-f.json', 'submissions': f'{cid}-s.json',
                                    'acquired_at': day(n).isoformat(), 'synthetic': False})
        out.mkdir()
        assert pipe.stage_qgv2_target(out, manifest, root, now=day(n)) is not None

    data = lambda cid: AS.REF.synthetic_sec(qgv2.target_cik(cid), seed=TARGET_SEED.get(cid, 7))
    cik = qgv2.target_cik('nvda')
    none = (json.dumps({'cik': int(cik), 'facts': {}}).encode(), json.dumps({'cik': int(cik), 'sic': '3674'}).encode())
    stage(tmp_path / 'day0', 0, {'nvda': data('nvda'), 'msft': data('msft')})
    day0 = run(tmp_path, 'day0', Sec(), 0, out=tmp_path / 'day0')
    target0 = json.loads((day0 / qgv2.FILENAME).read_bytes())['target']
    assert target0['nvda']['fiscal_year_end'] is not None and target0['msft']['fiscal_year_end'] is not None
    stage(tmp_path / 'day1', 1, {'nvda': none})
    staged = qgv2.require_qgv2(json.loads((tmp_path / 'day1' / qgv2.FILENAME).read_bytes()))
    assert set(qgv2.target_updates_from(staged)) == {'nvda'}
    day1 = run(tmp_path, 'day1', Sec(), 1, previous=day0, out=tmp_path / 'day1')
    target1 = json.loads((day1 / qgv2.FILENAME).read_bytes())['target']
    nvda = target1['nvda']
    assert (nvda['state'], nvda['reason_codes'], nvda['acquired_at'], nvda['metrics']) == ('NOT_AVAILABLE', ['NO_ANNUAL_SEC_FINANCIALS'], stamp(day(1)), {})
    assert target1['msft']['acquired_at'] == target0['msft']['acquired_at'] and target1['msft']['fiscal_year_end'] is not None
    capsys.readouterr()
    code, out = guard_against(day1, day0, capsys)
    line = section_line(out, qgv2.FILENAME, 'target')
    assert code == 0 and (line['verdict'], line['newer'], line['equal']) == ('PASS', '1', '1')


@pytest.mark.parametrize('observed, new_value, old_value, expected', [
    (True, False, True, True),      # successful collection without a value replaces a kept value (new rule)
    (True, True, True, True),
    (True, False, False, True),
    (False, False, True, False),    # no collection record of its own: never erases a kept value
    (False, False, False, True),
    (False, True, True, True),
])
def test_replaces_rule(observed, new_value, old_value, expected):
    new, old = {'o': observed, 'v': new_value}, {'v': old_value}
    assert us.replaces(new, old, observed=lambda r: r['o'], has_value=lambda r: r['v']) is expected
    assert us.replaces(None, old, observed=lambda r: True, has_value=lambda r: True) is False
