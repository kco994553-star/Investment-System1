"""Universe identity-conflict withdrawal in the three Universe files (owner decision UNI-WITHDRAWN (a), 2026-10-17):
generation -> pre-deploy freshness guard -> device.

The owner's purpose: a Universe observation whose use stops for an identity conflict reaches the published files and their
readers as a withdrawal, the same way as TARGET /4 (#285); it is not a relaxation to keep deploys green.

Generation runs the real daily shard tool (tools/sec_universe_shares.py `run`: daily, --all-shards and --preserve-only)
on synthetic SEC bytes and the in-memory previous Pages copy; the deploy check is the real freshness guard
(tools/pages_freshness_guard.py); the device side runs the real browser modules in node on the published bytes
(SecUniverseShares, SecQgv2 -> Qgv2Inputs -> QgvScores -> PlaybookScreen.candidateRanking). Synthetic CIKs, bytes and
clocks only: no network, credential or real price.
"""
from datetime import timedelta
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from investment_system.universe import sec_qgv2 as qgv2
from investment_system.universe import sec_universe_qg as uqg
from investment_system.universe import sec_universe_shares as us
from tests import test_previous_observation_preservation as P
from tests import test_target_withdrawal_e2e as W
from tests import test_universe_conflict_na_priority as T
from tests.test_pages_freshness_guard import Site, guard, guard_against, load_tool, section_line

AS = T.AS
UNIVERSE = T.UNIVERSE
SHARD = load_tool('sec_universe_shares')
COVERAGE = load_tool('published_coverage')
WEB = W.WEB
NODE = shutil.which('node') is not None
REASON = us.WITHDRAWN_REASON
stamp, day, rows = T.stamp, T.day, T.rows


def payload(folder, name):
    return json.loads((Path(folder) / name).read_bytes())


def lines(out, prefix):
    return [dict(p.split('=', 1) for p in l.split() if '=' in p) for l in out.splitlines() if l.startswith(prefix + ' shard=')]


def copy(folder, to):
    to.mkdir()
    for p in Path(folder).iterdir():
        if p.is_file():
            shutil.copyfile(p, to / p.name)
    return to


def tamper(tmp_path, folder, name, code, **changes):
    """A copy of `folder` whose `name` row `code` has `changes` (the file stays valid for its strict validator)."""
    out = copy(folder, tmp_path / f'tampered-{len(list(tmp_path.iterdir()))}')
    data = payload(out, name)
    data['records'][code].update(changes)
    {us.FILENAME: us.require_universe_shares, uqg.FILENAME: uqg.require_universe_qg, qgv2.FILENAME: qgv2.require_qgv2}[name](data)
    (out / name).write_text(json.dumps(data))
    return out


@pytest.fixture(scope='module')
def history(tmp_path_factory):
    """Day 0: all-shards publication, X has values in all three files (acquired day 0).
    Day 1 (X's shard): X's bytes arrive but its cover filing request fails and its two share counts leave no count:
    the shares row stays the verified day-0 row (#278), Q·G and QGV v2 are new rows of day 1. So the three files hold
    observations of X with different acquired_at.
    Day 2: X's ticker is also claimed by another CIK (multi-CIK conflict): every file withdraws its own row of X."""
    folder = tmp_path_factory.mktemp('withdrawal')
    x = T.members(1)[0]
    code_x = AS.CODE[x]
    day0 = T.run(folder, 'day0', T.Sec(rich={x}), 0, all_shards=True)
    day1 = T.run(folder, 'day1', T.Sec(rich={x}, ambiguous={x}, cover_fail={x}), 1, previous=day0)
    assert rows(day1, us.FILENAME)[code_x] == rows(day0, us.FILENAME)[code_x]
    assert all(rows(day1, n)[code_x]['acquired_at'] == stamp(day(1)) and T.has_values(n, rows(day1, n)[code_x])
               for n in (uqg.FILENAME, qgv2.FILENAME))
    claim = [(P.fresh_cik(0), code_x)]
    day2 = T.run(folder, 'day2', T.Sec(rich={x}, claims=claim), 2, previous=day1)
    return {'folder': folder, 'x': x, 'code': code_x, 'claim': claim, 'day0': day0, 'day1': day1, 'day2': day2}


# ---------------- 1. normal withdrawal publish: each file names its own live observation ----------------
def test_each_file_publishes_a_withdrawal_naming_its_own_observation_and_the_guard_passes(history, capsys):
    code_x, x, day1, day2 = history['code'], history['x'], history['day1'], history['day2']
    named = {us.FILENAME: stamp(day(0)), uqg.FILENAME: stamp(day(1)), qgv2.FILENAME: stamp(day(1))}
    for name in UNIVERSE:
        row = rows(day2, name)[code_x]
        assert set(row) - set(us.WITHDRAWAL_KEYS) == set(rows(day1, name)[code_x])          # only the three keys added
        assert (row['state'], row['reason_codes'], row['cik'], row['acquired_at']) == ('NOT_AVAILABLE', [REASON], None, None)
        # detected_at is this run's detection, never a collection time; each file names its own live row.
        assert row['detected_at'] == stamp(day(2)) and row['withdrawn_acquired_at'] == named[name] == rows(day1, name)[code_x]['acquired_at']
        assert row['withdrawn_cik'] == x and not T.has_values(name, row)
        assert all(v is None for v in row['source_sha256'].values())
    v2 = rows(day2, qgv2.FILENAME)[code_x]
    assert v2['metrics'] == {} and v2['calc_version'] is None and v2['axes']['Q']['score'] is None and v2['sic'] is None
    shares = rows(day2, us.FILENAME)[code_x]
    assert shares['listing_id'] is None and shares['share_class_basis'] == 'BASIS_UNCONFIRMED' and shares['shares'] is None
    code, out = guard_against(day2, day1, capsys)
    assert code == 0 and ' rows_regressed=0 ' in out
    for name in UNIVERSE:
        line = section_line(out, name, 'records')
        assert (line['verdict'], line['withdrawn'], line['withdrawal_mismatch'], line['lost_record']) == ('PASS', '1', '0', '0')


def test_withdrawal_rows_are_outside_every_count_of_new_collections_and_coverage(history, tmp_path, capsys):
    """Day 2's own report lines: the withdrawal is counted as withdrawn (never collected, live, scored or preserved); Q·G
    coverage and the cross-section lose X; the 504-code denominator is unchanged. The published coverage line agrees."""
    x, code_x, day1 = history['x'], history['code'], history['day1']
    capsys.readouterr()
    again = T.run(tmp_path, 'again', T.Sec(rich={x}, claims=history['claim']), 2, previous=day1)
    out = capsys.readouterr().out
    shares, qg_line, v2_line = (lines(out, p)[0] for p in ('SEC_UNIVERSE_SHARES', 'SEC_UNIVERSE_QG', 'SEC_QGV2'))
    before = qgv2.require_qgv2(payload(day1, qgv2.FILENAME))
    after = qgv2.require_qgv2(payload(again, qgv2.FILENAME))
    assert shares['withdrawn'] == qg_line['withdrawn'] == v2_line['withdrawn'] == '1'
    assert int(shares['live']) + int(shares['stale']) + int(shares['not_available']) == 504
    assert int(v2_line['live']) + int(v2_line['stale']) + int(v2_line['not_available']) == 504
    assert int(v2_line['cross_section']) == before['cross_section_size'] - 1 == after['cross_section_size']
    scored = lambda data, axis: sum(1 for r in data['records'].values() if r['axes'][axis]['score'] is not None)
    for axis, key in (('Q', 'q_scored'), ('G', 'g_scored')):
        had = before['records'][code_x]['axes'][axis]['score'] is not None
        assert int(v2_line[key]) == scored(after, axis) == scored(before, axis) - had and after['records'][code_x]['axes'][axis]['score'] is None
    assert before['records'][code_x]['axes']['G']['score'] is not None          # X was in the G coverage before
    counts = P.collection_counts(out)
    assert counts['identity_not_preserved'] == '1' and counts['preserved_unconfirmed'] == '0'
    assert counts['preserved_previous_shares'] == counts['preserved_previous_qg'] == counts['preserved_previous_qgv2'] == '0'
    line = COVERAGE.coverage_line(after)
    old = COVERAGE.coverage_line(before)
    field = lambda text, key: int(re.search(rf' {key}=(\d+) ', text).group(1))
    assert field(line, 'withdrawn') == 1 and field(old, 'withdrawn') == 0
    assert field(line, 'never_acquired_rows') == field(old, 'never_acquired_rows')          # it was acquired once
    assert field(line, 'g') == field(old, 'g') - 1 and field(line, 'live') == field(old, 'live') - 1
    assert all(after['records'][c]['state'] == 'NOT_AVAILABLE' for c in [code_x])


# ---------------- 2. a withdrawal naming anything but the live observation is refused ----------------
@pytest.mark.parametrize('name', UNIVERSE)
def test_a_withdrawal_naming_another_observation_or_issuer_is_refused(history, tmp_path, capsys, name):
    code_x, day1, day2 = history['code'], history['day1'], history['day2']
    other = {us.FILENAME: stamp(day(1)), uqg.FILENAME: stamp(day(0)), qgv2.FILENAME: stamp(day(0))}[name]
    live_at = day(0) if name == us.FILENAME else day(1)
    cases = [
        # another file's collection time (a TARGET or other-file time copied in), later or earlier than the live row
        (dict(withdrawn_acquired_at=other), 'WITHDRAWAL_MISMATCH' if other > rows(day1, name)[code_x]['acquired_at'] else 'OLDER'),
        (dict(withdrawn_acquired_at=stamp(day(-3))), 'OLDER'),
        (dict(withdrawn_cik=P.fresh_cik(3)), 'WITHDRAWAL_MISMATCH'),                                 # another issuer
        # detected before the live observation was collected
        (dict(detected_at=stamp(live_at - timedelta(hours=1)), withdrawn_acquired_at=stamp(live_at - timedelta(hours=2))), 'OLDER'),
    ]
    for changes, kind in cases:
        artifact = tamper(tmp_path, day2, name, code_x, **changes)
        code, out = guard_against(artifact, day1, capsys)
        assert code == 1 and f'file={name} section=records code={code_x} kind={kind} ' in out, (changes, out)
    # A status alone is no withdrawal: the reason without the keys fails the strict validator -> no rows trusted.
    bad = copy(day2, tmp_path / 'status-only')
    data = payload(bad, name)
    data['records'][code_x] = dict({k: v for k, v in data['records'][code_x].items() if k not in us.WITHDRAWAL_KEYS})
    with pytest.raises(ValueError):
        {us.FILENAME: us.require_universe_shares, uqg.FILENAME: uqg.require_universe_qg, qgv2.FILENAME: qgv2.require_qgv2}[name](data)
    data['records'][code_x]['detected_at'] = stamp(day(2))             # one key only: invalid file -> no rows trusted
    (bad / name).write_text(json.dumps(data))
    code, out = guard_against(bad, day1, capsys)
    assert code == 1 and f'PAGES_FRESHNESS_ARTIFACT_INVALID file={name} rows=NONE' in out


# ---------------- 3. the withdrawal stays: conflict persisting, failures, preserve-only, stale redeploys ----------------
def test_the_withdrawal_stays_unchanged_until_a_confirmed_new_collection(history, tmp_path, capsys):
    x, code_x, day2, claim = history['x'], history['code'], history['day2'], history['claim']
    withdrawn = {name: rows(day2, name)[code_x] for name in UNIVERSE}
    previous = day2
    steps = [
        ('conflict-day3', T.Sec(rich={x}, claims=claim), 3, {}),                     # conflict persists
        ('conflict-day8', T.Sec(rich={x}, claims=claim), 8, {}),                     # ... on X's own shard day
        ('fetch-fail', T.Sec(rich={x}, fail={x}), 8, {}),                           # conflict gone, X's fetch fails
        ('mismatch', T.Sec(mismatch={x}), 8, {}),                                  # SEC response names another CIK
        ('unresolved', T.Sec(rich={x}, hidden={x}), 9, {}),                         # ticker missing from the registry
        ('all-shards-conflict', T.Sec(rich={x}, claims=claim), 10, {'all_shards': True}),
    ]
    evidence = {'fetch-fail': 'SEC_UNIVERSE_FAILURE ', 'mismatch': 'code=SEC_CIK_MISMATCH'}
    for label, sec, n, kwargs in steps:
        capsys.readouterr()
        out = T.run(tmp_path, label, sec, n, previous=previous, **kwargs)
        printed = capsys.readouterr().out
        assert evidence.get(label, '') in printed and (label != 'unresolved' or ' unresolved_codes=478 ' in printed), label
        for name in UNIVERSE:
            assert rows(out, name)[code_x] == withdrawn[name], (label, name)        # same detected_at, same named row
        code, text = guard_against(out, previous, capsys)
        assert code == 0 and all(section_line(text, name, 'records')['equal'] != '0' for name in UNIVERSE), (label, text)
        assert all(section_line(text, name, 'records')['withdrawal_mismatch'] == '0' for name in UNIVERSE)
        previous = out
    # The manual (cockpit-pages.yml) preserve-only build re-publishes the live withdrawal unchanged.
    site = Site()
    site.deploy(previous)
    manual = tmp_path / 'manual'
    manual.mkdir()
    assert SHARD.run(manual, live=False, preserve_only=True, now=lambda: day(11), open_previous=site) == 0
    assert all(rows(manual, name)[code_x] == withdrawn[name] for name in UNIVERSE)
    code, text = guard(manual, site, capsys)
    assert code == 0


def test_an_artifact_built_before_the_withdrawal_cannot_bring_the_stopped_values_back(history, capsys):
    """The live copy holds the withdrawal (day 2). The day-1 artifact (built before the conflict) carries X's stopped
    rows: OLDER than the detection in every file -> refused. An artifact that lost the withdrawal is LOST_RECORD."""
    code_x, day1, day2 = history['code'], history['day1'], history['day2']
    code, out = guard_against(day1, day2, capsys)
    assert code == 1
    for name in UNIVERSE:
        assert f'file={name} section=records code={code_x} kind=OLDER artifact={stamp(day(1)) if name != us.FILENAME else stamp(day(0))} ' in out
    for module, name in ((us, us.FILENAME), (uqg, uqg.FILENAME), (qgv2, qgv2.FILENAME)):
        # an older producer (no withdrawal rows): the merge on the live withdrawal leaves a row without any record
        plain = copy(day2, history['folder'] / f'plain-{name}')
        data = payload(plain, name)
        data['records'][code_x] = module.empty_record(reasons=('CIK_UNRESOLVED',))
        if name == qgv2.FILENAME:
            data['records'][code_x]['calc_version'] = None
        (plain / name).write_text(json.dumps(data))
        code, out = guard_against(plain, day2, capsys)
        assert code == 1 and f'file={name} section=records code={code_x} kind=LOST_RECORD ' in out


# ---------------- 4. recovery only by a confirmed new collection; never another issuer's history ----------------
def test_a_confirmed_new_collection_replaces_the_withdrawal(history, tmp_path, capsys):
    x, code_x, day2 = history['x'], history['code'], history['day2']
    restored = T.run(tmp_path, 'restored', T.Sec(rich={x}), 4, previous=day2, all_shards=True)
    for name in UNIVERSE:
        row = rows(restored, name)[code_x]
        assert not us.is_withdrawal(row) and row['cik'] == x and row['acquired_at'] == stamp(day(4))
        assert row['state'] == 'LIVE' and T.has_values(name, row)
    code, out = guard_against(restored, day2, capsys)
    assert code == 0 and all(section_line(out, name, 'records')['withdrawn'] == '0' for name in UNIVERSE)


def test_a_new_issuer_of_the_ticker_does_not_inherit_the_withdrawn_history(history, tmp_path, capsys):
    """After the withdrawal the ticker is bound to a new CIK (no annual financials): its own NOT_AVAILABLE rows with its own
    collection record replace the withdrawal; nothing of X (values, CIK, times) is joined to it."""
    x, code_x, day2 = history['x'], history['code'], history['day2']
    new = P.fresh_cik(AS.shard_of(x))
    reused = T.run(tmp_path, 'reused', P.Sec(rebind={code_x: new}), 4, previous=day2, all_shards=True)
    for name in UNIVERSE:
        row = rows(reused, name)[code_x]
        assert not us.is_withdrawal(row) and row['cik'] == new and row['acquired_at'] == stamp(day(4))
        assert row['state'] == 'NOT_AVAILABLE' and not T.has_values(name, row) and x not in json.dumps(row)
    code, out = guard_against(reused, day2, capsys)
    assert code == 0 and ' rows_regressed=0 ' in out


def test_without_a_previous_collection_the_conflict_is_plain_cik_unresolved_without_any_time(history, tmp_path):
    """A Universe code never collected (no record in any file) claimed by two CIKs: nothing to withdraw, no time made up."""
    day2 = history['day2']
    code = next(c for c in us.universe_codes() if c not in AS.CODE.values() and c.startswith('NASDAQ:'))
    assert all(rows(day2, name)[code]['acquired_at'] is None for name in UNIVERSE)
    out = T.run(tmp_path, 'never', P.Sec(claims=[(P.fresh_cik(1), code), (P.fresh_cik(2), code)]), 3, previous=day2)
    for name in UNIVERSE:
        row = rows(out, name)[code]
        assert row['reason_codes'] == ['CIK_UNRESOLVED'] and row['acquired_at'] is None and row['cik'] is None
        assert not set(us.WITHDRAWAL_KEYS) & set(row)


def test_merge_rules_at_the_file_level():
    """The shared helpers: a withdrawal needs a kept collection record, keeps its first detection, and only a collection
    at or after the detection without conflict evidence replaces it."""
    kept = dict(us.empty_record(cik='0000000007', reasons=('COVER_NOT_AVAILABLE',)), acquired_at=stamp(day(0)))
    w = us.withdrawal(kept, us.empty_record, detected_at=day(1))
    assert (w['detected_at'], w['withdrawn_acquired_at'], w['withdrawn_cik'], w['cik']) == (stamp(day(1)), stamp(day(0)), '0000000007', None)
    assert us.withdrawal(w, us.empty_record, detected_at=day(5)) is w                  # first detection kept
    assert us.withdrawal(us.empty_record(), us.empty_record, detected_at=day(1)) is None
    seen = lambda r: r['acquired_at'] is not None
    new = dict(kept, acquired_at=stamp(day(2)))
    assert us.withdrawal_stays(w, None, code='C', conflicts=(), observed=seen)
    assert us.withdrawal_stays(w, new, code='C', conflicts={'C'}, observed=seen)
    assert us.withdrawal_stays(w, dict(kept, acquired_at=stamp(day(0))), code='C', conflicts=(), observed=seen)  # before detection
    assert us.withdrawal_stays(w, dict(kept, acquired_at=None), code='C', conflicts=(), observed=seen)
    assert not us.withdrawal_stays(w, new, code='C', conflicts=(), observed=seen)
    assert not us.withdrawal_stays(kept, None, code='C', conflicts={'C'}, observed=seen)


# ---------------- 5. device: no score, rank, candidate or market cap; no TARGET <-> Universe substitution ----------------
SHARES_DEVICE = r"""
const path=require('node:path'),fs=require('node:fs'),W=process.argv[2],input=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const R=require(path.join(W,'sec-universe-shares.js')),i=R.toInputs(input.payload,{now:input.now}),r=i.publicShares[input.code];
process.stdout.write(JSON.stringify({seed:Object.hasOwn(i.identityLookup,input.code),state:r.state,shares:r.shares,reasons:[...r.reason_codes]}));
"""


@pytest.mark.skipif(not NODE, reason='Node runtime required')
def test_device_uses_no_withdrawn_value_anywhere(history, tmp_path):
    code_x, day2 = history['code'], history['day2']
    ticker = code_x.split(':')[1]
    seen = W.device(tmp_path, payload(day2, qgv2.FILENAME), identities=[{'company_id': 'xco', 'ticker': ticker}],
                    quotes={code_x: {'price': 10.0, 'currency': 'USD'}}, records=(code_x,), codes=(code_x,))
    row = seen['rows']['xco']
    assert row['code'] == code_x and (row['q'], row['g'], row['v'], row['total'], row['rank']) == (None,) * 5
    assert row['total_reason'] == 'SOURCE_NOT_AVAILABLE' and row['source_reason_codes'] == [REASON]
    assert seen['records'][code_x] == {'state': 'WITHDRAWN', 'identity_withdrawn': True, 'in_cross_section': False, 'q': None, 'g': None}
    assert seen['ranked'] == [{'code': code_x, 'total': None, 'rank': None, 'qg_available': False}]
    # shares: no identity seed -> no M3 market cap or rank; the reason is shown.
    script, data = tmp_path / 'shares.js', tmp_path / 'shares.json'
    script.write_text(SHARES_DEVICE)
    data.write_text(json.dumps({'payload': payload(day2, us.FILENAME), 'now': stamp(day(2) + timedelta(hours=1)), 'code': code_x}))
    result = subprocess.run(['node', str(script), str(WEB), str(data)], text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    assert json.loads(result.stdout) == {'seed': False, 'state': 'NOT_AVAILABLE', 'shares': None, 'reasons': [REASON]}


@pytest.mark.skipif(not NODE, reason='Node runtime required')
def test_device_never_substitutes_between_target_and_a_withdrawn_universe_code(tmp_path, capsys):
    """NASDAQ:GOOGL (Universe) is withdrawn for a multi-CIK claim; TARGET googl is TARGET's own observation (fixed CIK).
    - TARGET googl with data: its own score stays; the Universe code GOOGL gets no candidate score from it.
    - TARGET googl NOT_AVAILABLE: the ticker fallback lands on the withdrawn GOOGL row -> no score, reason shown.
    GOOG (same issuer, other code) keeps its own row."""
    base = W.live_qgv2()
    entries = [(cid, *(json.dumps(x).encode() for x in W.bodies(cid)), W.T0) for cid in ('googl', 'msft')]
    live = qgv2.merge(base, {}, as_of=W.T0 + timedelta(minutes=10), shard_index=3, target_updates=qgv2.build_target_rows(entries))
    site = Site({qgv2.FILENAME: qgv2.encode(live)})
    withdrawn = qgv2.merge(live, {}, as_of=W.T1, shard_index=3, conflicts={'NASDAQ:GOOGL'})
    assert withdrawn['records']['NASDAQ:GOOGL']['withdrawn_acquired_at'] == live['records']['NASDAQ:GOOGL']['acquired_at']
    folder = tmp_path / 'artifact'
    folder.mkdir()
    (folder / qgv2.FILENAME).write_bytes(qgv2.encode(withdrawn))
    code, out = guard(folder, site, capsys)
    assert code == 0 and section_line(out, qgv2.FILENAME, 'records')['withdrawn'] == '1'
    ids = [{'company_id': 'googl', 'ticker': 'GOOGL'}, {'company_id': 'goog', 'ticker': 'GOOG'}]
    seen = W.device(tmp_path, withdrawn, identities=ids, quotes=W.QUOTES, records=('NASDAQ:GOOGL', 'NASDAQ:GOOG', 'TARGET:googl'),
                    codes=('NASDAQ:GOOGL', 'NASDAQ:GOOG'))
    assert seen['rows']['googl']['code'] == 'TARGET:googl' and seen['rows']['googl']['total'] is not None   # TARGET's own row
    assert seen['records']['NASDAQ:GOOGL']['state'] == 'WITHDRAWN' and seen['records']['NASDAQ:GOOG']['state'] == 'LIVE'
    ranked = {r['code']: r for r in seen['ranked']}
    assert (ranked['NASDAQ:GOOGL']['total'], ranked['NASDAQ:GOOGL']['rank']) == (None, None)     # no TARGET score borrowed
    assert ranked['NASDAQ:GOOG']['total'] is not None and seen['rows']['goog']['code'] == 'NASDAQ:GOOG'
    # TARGET googl collected without annual financials (NOT_AVAILABLE): the ticker fallback must not revive anything.
    cik = qgv2.target_cik('googl')
    none = (json.dumps({'cik': int(cik), 'facts': {}}).encode(), json.dumps({'cik': int(cik), 'sic': '7370'}).encode())
    na = qgv2.merge(withdrawn, {}, as_of=W.T1 + timedelta(minutes=5), shard_index=3,
                    target_updates=qgv2.build_target_rows([('googl', *none, W.T1)]))
    assert na['target']['googl']['state'] == 'NOT_AVAILABLE' and us.is_withdrawal(na['records']['NASDAQ:GOOGL'])
    seen = W.device(tmp_path, na, identities=ids, quotes=W.QUOTES, records=('NASDAQ:GOOGL',), codes=('NASDAQ:GOOGL',))
    row = seen['rows']['googl']
    assert row['code'] == 'NASDAQ:GOOGL' and (row['q'], row['g'], row['total'], row['rank']) == (None,) * 4
    assert row['source_reason_codes'] == [REASON]


@pytest.mark.skipif(not NODE, reason='Node runtime required')
def test_screen_reason_text_is_the_owner_wording():
    script = ("const QS=require(process.argv[1]+'/qgv-scores.js');"
              "process.stdout.write(QS.naText({total_reason:'SOURCE_NOT_AVAILABLE',source_reason_codes:['IDENTITY_CONFLICT_WITHDRAWN']},false))")
    result = subprocess.run(['node', '-e', script, str(WEB)], text=True, capture_output=True, timeout=60)
    assert result.stdout == 'QGV v2 산출 불가 · 원자료 없음 (식별 충돌로 사용 중지)'
    for asset in ('app.js', 'private-subset-view.js'):
        assert '식별 충돌로 사용 중지' in (WEB / asset).read_text()


# ---------------- 6. JS == Python on the new keys (shares; Q·G and QGV v2 have fixture vectors) ----------------
@pytest.mark.skipif(not NODE, reason='Node runtime required')
def test_shares_js_validator_reaches_the_python_verdict_on_withdrawal_rows(history):
    code_x, day2 = history['code'], history['day2']
    good = payload(day2, us.FILENAME)
    w = good['records'][code_x]
    other = next(c for c in AS.CODE.values() if c != code_x)
    mutations = {
        'valid': [],
        'with_shares': [(code_x, 'shares', 5)],
        'with_cik': [(code_x, 'cik', w['withdrawn_cik'])],
        'other_reason': [(code_x, 'reason_codes', ['CIK_UNRESOLVED'])],
        'extra_reason': [(code_x, 'reason_codes', [REASON, 'CIK_UNRESOLVED'])],
        'no_named_observation': [(code_x, 'withdrawn_acquired_at', None)],
        'names_later_observation': [(code_x, 'withdrawn_acquired_at', stamp(day(3)))],
        'detected_after_as_of': [(code_x, 'detected_at', stamp(day(9)))],
        'no_issuer': [(code_x, 'withdrawn_cik', None)],
        'issuer_zero': [(code_x, 'withdrawn_cik', '0000000000')],
        'state_live': [(code_x, 'state', 'LIVE')],
        'reason_on_another_row': [(other, 'reason_codes', [REASON])],
        'keys_on_another_row': [(other, 'detected_at', stamp(day(2)))],
    }
    script = ("const a=require(process.argv[1]),p=JSON.parse(require('fs').readFileSync(0,'utf8'));"
              "try{a.validate(p);console.log('OK')}catch(e){console.log('REJECT')}")
    for label, ops in mutations.items():
        data = json.loads(json.dumps(good))
        for code, key, value in ops:
            data['records'][code][key] = value
        try:
            us.require_universe_shares(data)
            expected = 'OK'
        except ValueError:
            expected = 'REJECT'
        assert (expected == 'OK') == (label == 'valid'), label
        got = subprocess.run(['node', '-e', script, str(WEB / 'sec-universe-shares.js')], input=json.dumps(data), text=True,
                             capture_output=True, timeout=60).stdout.strip()
        assert got == expected, label
