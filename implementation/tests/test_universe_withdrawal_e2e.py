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
REF = load_tool('sec_qgv2_reference')
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
    unhashed = dict(us.empty_record(cik='0000000007', reasons=('COVER_NOT_AVAILABLE',)), acquired_at=stamp(day(0)))
    assert us.withdrawal(unhashed, us.empty_record, detected_at=day(1)) is None      # observation not exactly identified
    kept = dict(unhashed, source_sha256={'companyfacts': 'a' * 64, 'submissions': 'b' * 64, 'cover': None})
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


def target_live():
    """Live sec-qgv2.json with TARGET googl and msft collected (fixed TARGET CIKs) and the Universe codes NASDAQ:GOOGL /
    NASDAQ:GOOG of googl's issuer (#285 fixture)."""
    entries = [(cid, *(json.dumps(x).encode() for x in W.bodies(cid)), W.T0) for cid in ('googl', 'msft')]
    return qgv2.merge(W.live_qgv2(), {}, as_of=W.T0 + timedelta(minutes=10), shard_index=3,
                      target_updates=qgv2.build_target_rows(entries))


@pytest.mark.skipif(not NODE, reason='Node runtime required')
def test_device_never_substitutes_between_target_and_a_withdrawn_universe_code(tmp_path, capsys):
    """NASDAQ:GOOGL (Universe) is withdrawn for a multi-CIK claim; TARGET googl is TARGET's own observation (fixed CIK).
    - The Universe code GOOGL gets no candidate score from the TARGET row of the same ticker.
    - TARGET googl NOT_AVAILABLE: the ticker fallback lands on the withdrawn GOOGL row -> no score, reason shown.
    GOOG (same issuer, other code) keeps its own row. (TARGET googl's price link: test_uni_target_* below.)"""
    live = target_live()
    site = Site({qgv2.FILENAME: qgv2.encode(live)})
    withdrawn = qgv2.merge(live, {}, as_of=W.T1, shard_index=3, conflicts={'NASDAQ:GOOGL'})
    assert withdrawn['records']['NASDAQ:GOOGL']['withdrawn_acquired_at'] == live['records']['NASDAQ:GOOGL']['acquired_at']
    assert withdrawn['target']['googl'] == live['target']['googl']                  # TARGET financials are not withdrawn
    folder = tmp_path / 'artifact'
    folder.mkdir()
    (folder / qgv2.FILENAME).write_bytes(qgv2.encode(withdrawn))
    code, out = guard(folder, site, capsys)
    assert code == 0 and section_line(out, qgv2.FILENAME, 'records')['withdrawn'] == '1'
    ids = [{'company_id': 'googl', 'ticker': 'GOOGL'}, {'company_id': 'goog', 'ticker': 'GOOG'}]
    seen = W.device(tmp_path, withdrawn, identities=ids, quotes=W.QUOTES, records=('NASDAQ:GOOGL', 'NASDAQ:GOOG', 'TARGET:googl'),
                    codes=('NASDAQ:GOOGL', 'NASDAQ:GOOG'))
    assert seen['records']['NASDAQ:GOOGL']['state'] == 'WITHDRAWN' and seen['records']['NASDAQ:GOOG']['state'] == 'LIVE'
    assert seen['records']['TARGET:googl']['state'] == 'LIVE' and seen['records']['TARGET:googl']['q'] is not None
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


UNI_TARGET = r"""
const path=require('node:path'),fs=require('node:fs'),W=process.argv[2],input=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
for(const [name,file] of [['EnginePreview','engine-preview.js'],['ProfileDefaults','profile-defaults.js'],['TypeConfigDefaults','type-config-defaults.js'],['DcfParametersDefaults','dcf-parameters-defaults.js'],['SecQgv2','sec-qgv2.js'],['QgvV2','qgv-v2.js'],['Qgv2Inputs','qgv2-inputs.js'],['QgvScores','qgv-scores.js']])globalThis[name]=require(path.join(W,file));
const P=require(path.join(W,'playbook-screen.js')),SQ=globalThis.Qgv2Inputs,QS=globalThis.QgvScores;
(async()=>{
 const inputs=SQ.fromInputs(globalThis.SecQgv2.toInputs(input.payload,{now:input.now}));
 // The device price paths by ticker: the Universe sheet tab (PrivateSubsetView.prices) and DeviceValuation.deviceQuote.
 const sheet=new Map(input.sheet.map(([code,price])=>[code,{price,currency:'USD'}]));
 const win={PrivateSubsetView:{prices:()=>sheet},DeviceValuation:{deviceQuote:async(_w,_c,ticker)=>({price:77,currency:'USD',ticker})}};
 const quotes=await QS.collectQuotes(win,{identities:input.identities,v2Inputs:inputs,catalog:{}});
 const computed=QS.compute({identities:input.identities,publicScreens:{[SQ.FILE]:inputs},quotes:{...input.quotes,...quotes}});
 const rows={};for(const [id,r] of Object.entries(computed.rows)){const p=r.primary;rows[id]={code:r.code,q:p.q,g:p.g,v:p.v,total:p.total,rank:r.rank,total_reason:p.total_reason||null,flags:p.flags,text:QS.naText(p,false)};}
 const ranked=P.candidateRanking(computed,{[SQ.FILE]:inputs},input.codes).map(r=>({code:r.code,total:r.total,rank:r.rank}));
 process.stdout.write(JSON.stringify({quoted:Object.keys(quotes).sort(),rows,ranked}));
})();
"""


def uni_target(tmp_path, payload, conflict_label, *, quotes=None):
    script, data = tmp_path / f'uni-{conflict_label}.js', tmp_path / f'uni-{conflict_label}.json'
    script.write_text(UNI_TARGET)
    data.write_text(json.dumps({'payload': payload, 'now': (W.T1 + timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
                                'identities': [{'company_id': 'googl', 'ticker': 'GOOGL'}, {'company_id': 'msft', 'ticker': 'MSFT'}],
                                'quotes': quotes or {c: q for c, q in W.QUOTES.items() if not c.startswith('TARGET:')},
                                'sheet': [['NASDAQ:GOOGL', 101.0], ['NASDAQ:GOOG', 100.0], ['NASDAQ:MSFT', 300.0]],
                                'codes': ['NASDAQ:GOOGL', 'NASDAQ:GOOG']}))
    result = subprocess.run(['node', str(script), str(WEB), str(data)], text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout)


@pytest.mark.skipif(not NODE, reason='Node runtime required')
def test_uni_target_price_link_affected_target_loses_price_v_total_and_candidate_place(tmp_path):
    """UNI-TARGET (owner decision 2026-10-17, #289 item 4). TARGET googl's device price is read by its ticker GOOGL (the
    Universe sheet row NASDAQ:GOOGL, deviceQuote('GOOGL')). With NASDAQ:GOOGL withdrawn, that price link is in conflict: no
    price, no V, no total, no rank or candidate place, reason shown; googl's own Q·G (fixed-CIK TARGET observation) stay.
    TARGET msft (ticker MSFT, no withdrawn code) is independent and unchanged."""
    live = target_live()
    before = uni_target(tmp_path, live, 'none')
    assert 'TARGET:googl' in before['quoted'] and before['rows']['googl']['total'] is not None
    withdrawn = qgv2.merge(live, {}, as_of=W.T1, shard_index=3, conflicts={'NASDAQ:GOOGL'})
    seen = uni_target(tmp_path, withdrawn, 'googl')
    googl, msft = seen['rows']['googl'], seen['rows']['msft']
    assert 'TARGET:googl' not in seen['quoted'] and 'NASDAQ:GOOGL' not in seen['quoted']           # no price read at all
    assert googl['code'] == 'TARGET:googl' and googl['q'] is not None and googl['g'] is not None   # financials kept
    assert (googl['v'], googl['total'], googl['rank'], googl['total_reason']) == (None, None, None, 'PRICE_IDENTITY_CONFLICT')
    assert 'PRICE_IDENTITY_CONFLICT' in googl['flags'] and googl['text'] == 'QGV v2 산출 불가 · 가격 식별 충돌로 가격·V·종합 점수 사용 중지'
    same = lambda r: {k: v for k, v in r.items() if k != 'rank'}          # its rank moves up: googl left the ranking
    assert same(msft) == same(before['rows']['msft']) and msft['total'] is not None and 'TARGET:msft' in seen['quoted']
    # Even a quote handed in from elsewhere is not used for the affected TARGET.
    forced = uni_target(tmp_path, withdrawn, 'forced', quotes=W.QUOTES)
    assert forced['rows']['googl']['v'] is None and forced['rows']['googl']['total'] is None
    ranked = {r['code']: r for r in seen['ranked']}
    assert ranked['NASDAQ:GOOGL']['total'] is None and ranked['NASDAQ:GOOGL']['rank'] is None


@pytest.mark.skipif(not NODE, reason='Node runtime required')
def test_uni_target_conflict_on_another_code_of_the_issuer_leaves_the_target_independent(tmp_path):
    """NASDAQ:GOOG (Class C, same issuer) is withdrawn; TARGET googl's price symbol is GOOGL, so its price link is
    independent: price, V and total stay. Only the GOOG code itself is stopped."""
    live = target_live()
    before = uni_target(tmp_path, live, 'none2')
    seen = uni_target(tmp_path, qgv2.merge(live, {}, as_of=W.T1, shard_index=3, conflicts={'NASDAQ:GOOG'}), 'goog')
    assert 'TARGET:googl' in seen['quoted'] and 'NASDAQ:GOOG' not in seen['quoted']
    assert seen['rows']['googl']['total'] is not None and 'PRICE_IDENTITY_CONFLICT' not in seen['rows']['googl']['flags']
    assert seen['rows']['googl']['q'] == before['rows']['googl']['q']
    assert {r['code']: r for r in seen['ranked']}['NASDAQ:GOOG']['total'] is None


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
        'withdrawal_in_schema_v1': [(None, 'schema_version', 1)],
        'schema_v3': [(None, 'schema_version', 3)],
    }
    script = ("const a=require(process.argv[1]),p=JSON.parse(require('fs').readFileSync(0,'utf8'));"
              "try{a.validate(p);console.log('OK')}catch(e){console.log('REJECT')}")
    for label, ops in mutations.items():
        data = json.loads(json.dumps(good))
        for code, key, value in ops:
            (data if code is None else data['records'][code])[key] = value
        try:
            us.require_universe_shares(data)
            expected = 'OK'
        except ValueError:
            expected = 'REJECT'
        assert (expected == 'OK') == (label == 'valid'), label
        got = subprocess.run(['node', '-e', script, str(WEB / 'sec-universe-shares.js')], input=json.dumps(data), text=True,
                             capture_output=True, timeout=60).stdout.strip()
        assert got == expected, label


# ---------------- 7. #289 item 1: plain failures are never withdrawals; only an exactly identified row is withdrawn ----------------
def no_withdrawal(folder):
    return not any(us.is_withdrawal(r) for name in UNIVERSE for r in rows(folder, name).values())


@pytest.mark.parametrize('case', ['fetch_failure', 'unresolved_symbol', 'identity_unconfirmed_same_cik', 'no_data'])
def test_plain_failures_keep_or_replace_rows_and_never_withdraw(history, tmp_path, capsys, case):
    """A plain fetch failure, an unresolved symbol and a ticker no longer listed by the same issuer (identity unconfirmed,
    same CIK) keep the verified live row unchanged (#278); a collection without data publishes its own NA row (#287).
    None of them is an identity conflict: no withdrawal row anywhere, nothing refused at deploy."""
    x, code_x, day1 = history['x'], history['code'], history['day1']
    sec = {'fetch_failure': T.Sec(rich={x}, fail={x}), 'unresolved_symbol': T.Sec(rich={x}, hidden={x}),
           'identity_unconfirmed_same_cik': P.Sec(unticked={x}), 'no_data': T.Sec(empty={x})}[case]
    out = T.run(tmp_path, case, sec, 8, previous=day1)
    assert no_withdrawal(out)
    for name in UNIVERSE:
        row, live = rows(out, name)[code_x], rows(day1, name)[code_x]
        if case in ('fetch_failure', 'unresolved_symbol') or case == 'identity_unconfirmed_same_cik' and name == us.FILENAME:
            assert row == live, (case, name)                                     # kept unchanged
        else:
            assert row['acquired_at'] == stamp(day(8)) and row['cik'] == x       # this run's own observation
    if case == 'no_data':
        assert all(rows(out, n)[code_x]['state'] == 'NOT_AVAILABLE' for n in UNIVERSE)
    code, text = guard_against(out, day1, capsys)
    assert code == 0 and all(section_line(text, n, 'records')['withdrawn'] == '0' for n in UNIVERSE)


def _without_record(folder, name, code):
    """`folder` with the `name` row of `code` replaced by a row without collection record (a valid file)."""
    module = {uqg.FILENAME: uqg, us.FILENAME: us}[name]
    data = payload(folder, name)
    data['records'][code] = module.empty_record()
    states = [r['state'] for r in data['records'].values()]
    data['state'] = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
    data['reason_codes'] = [] if data['state'] == 'LIVE' else ['STALE_INPUT'] if data['state'] == 'STALE' else ['NO_ELIGIBLE_INPUT']
    {uqg.FILENAME: uqg.require_universe_qg, us.FILENAME: us.require_universe_shares}[name](data)
    (Path(folder) / name).write_text(json.dumps(data))


def test_a_conflict_withdraws_only_the_exactly_identified_row_of_each_file(history, tmp_path):
    """The live Q·G row of X has no collection record (NOT_COLLECTED) while shares and QGV v2 have one. On the conflict
    the shares and QGV v2 rows are withdrawn (naming their own rows); the Q·G row has nothing to name: plain
    CIK_UNRESOLVED without keys or times. No other code's row in any file differs from the same run without the conflict."""
    x, code_x, claim = history['x'], history['code'], history['claim']
    live = copy(history['day1'], tmp_path / 'live')
    _without_record(live, uqg.FILENAME, code_x)
    out = T.run(tmp_path, 'conflict', T.Sec(rich={x}, claims=claim), 2, previous=live)
    control = T.run(tmp_path, 'control', T.Sec(rich={x}), 2, previous=live)
    assert us.is_withdrawal(rows(out, us.FILENAME)[code_x]) and us.is_withdrawal(rows(out, qgv2.FILENAME)[code_x])
    qg_row = rows(out, uqg.FILENAME)[code_x]
    assert qg_row == uqg.empty_record(reasons=('CIK_UNRESOLVED',)) and not set(us.WITHDRAWAL_KEYS) & set(qg_row)
    for name in (us.FILENAME, uqg.FILENAME):
        others = lambda f: {c: r for c, r in rows(f, name).items() if c != code_x}
        assert others(out) == others(control), name
    v2_out, v2_control = payload(out, qgv2.FILENAME)['records'], payload(control, qgv2.FILENAME)['records']
    for c in v2_out:   # QGV v2 scores are re-ranked over the cross-section; the observations (inputs) are unchanged
        if c != code_x:
            strip = lambda r: {k: v for k, v in r.items() if k not in ('factors', 'axes', 'metrics')}
            assert strip(v2_out[c]) == strip(v2_control[c]) and us.is_withdrawal(v2_out[c]) is False


def test_the_run_log_counts_new_and_persisting_withdrawals_without_touching_rows(history, tmp_path, capsys):
    x, day2, claim = history['x'], history['day2'], history['claim']
    capsys.readouterr()
    out = T.run(tmp_path, 'recheck', T.Sec(rich={x}, claims=claim), 3, previous=day2)
    printed = capsys.readouterr().out
    line = next(l for l in printed.splitlines() if l.startswith('SEC_UNIVERSE_WITHDRAWALS '))
    assert line.endswith(' new_shares=0 kept_shares=1 new_qg=0 kept_qg=1 new_qgv2=0 kept_qgv2=1')
    assert all(rows(out, n)[history['code']] == rows(day2, n)[history['code']] for n in UNIVERSE)   # detected_at kept
    capsys.readouterr()
    T.run(tmp_path, 'first', T.Sec(rich={x}, claims=claim), 2, previous=history['day1'])
    first = next(l for l in capsys.readouterr().out.splitlines() if l.startswith('SEC_UNIVERSE_WITHDRAWALS '))
    assert first.endswith(' new_shares=1 kept_shares=0 new_qg=1 kept_qg=0 new_qgv2=1 kept_qgv2=0')


# ---------------- 8. #289 item 3: schema transition 1 -> 2 ----------------
VALIDATE = {us.FILENAME: us.require_universe_shares, uqg.FILENAME: uqg.require_universe_qg, qgv2.FILENAME: qgv2.require_qgv2}


def as_version_1(folder, to):
    out = copy(folder, to)
    for name in UNIVERSE:
        data = payload(out, name)
        data['schema_version'] = 1
        VALIDATE[name](data)
        (out / name).write_text(json.dumps(data))
    return out


def test_schema_transition_new_files_are_version_2_and_version_1_live_copies_are_read(history, tmp_path, capsys):
    """Producers write schema_version 2. A version-1 live copy (no withdrawal rows) is read by the daily run, the
    preserve-only path (which re-publishes it unchanged until the next daily collection) and the guard; the withdrawal
    is only valid in a version-2 file."""
    x, claim = history['x'], history['claim']
    assert all(payload(history['day2'], n)['schema_version'] == 2 for n in UNIVERSE)
    old_live = as_version_1(history['day1'], tmp_path / 'v1-live')
    out = T.run(tmp_path, 'v2', T.Sec(rich={x}, claims=claim), 2, previous=old_live)
    assert all(payload(out, n)['schema_version'] == 2 for n in UNIVERSE)
    assert all(rows(out, n)[history['code']] == rows(history['day2'], n)[history['code']] for n in UNIVERSE)
    code, text = guard_against(out, old_live, capsys)                    # old live vs new artifact
    assert code == 0 and all(section_line(text, n, 'records')['withdrawn'] == '1' for n in UNIVERSE)
    site = Site()
    site.deploy(old_live)
    manual = tmp_path / 'manual'
    manual.mkdir()
    assert SHARD.run(manual, live=False, preserve_only=True, now=lambda: day(2), open_previous=site) == 0
    for n in UNIVERSE:   # the manual (UI-only) build re-publishes the live bytes: a version-1 copy stays version 1
        assert (manual / n).read_bytes() == site.files[n] and payload(manual, n)['schema_version'] == 1
    code, _ = guard(manual, site, capsys)
    assert code == 0
    for n in UNIVERSE:                                                   # a withdrawal in a version-1 file is refused
        data = payload(out, n)
        data['schema_version'] = 1
        with pytest.raises(ValueError):
            VALIDATE[n](data)


SCREENS = r"""
const path=require('node:path'),fs=require('node:fs'),W=process.argv[2],F=process.argv[3],out={};
const view=dir=>({fetch:async n=>({status:200,ok:true,text:async()=>fs.readFileSync(path.join(F,dir,n),'utf8')})});
(async()=>{
 const S=require(path.join(W,'sec-universe-shares.js')),Q=require(path.join(W,'sec-universe-qg.js')),V=require(path.join(W,'sec-qgv2.js'));
 globalThis.SecQgv2=V;for(const [name,file] of [['EnginePreview','engine-preview.js'],['ProfileDefaults','profile-defaults.js'],['TypeConfigDefaults','type-config-defaults.js'],['DcfParametersDefaults','dcf-parameters-defaults.js'],['QgvV2','qgv-v2.js'],['Qgv2Inputs','qgv2-inputs.js']])globalThis[name]=require(path.join(W,file));
 const I=globalThis.Qgv2Inputs,QS=fs.existsSync(path.join(W,'qgv-scores.js'))?require(path.join(W,'qgv-scores.js')):null;
 for(const dir of fs.readdirSync(F).sort()){const r={};
  for(const [n,m] of [['shares',S],['qg',Q],['qgv2',V]]){try{await m.loadInputs(view(dir),{now:'2026-10-23T00:00:00Z'});r[n]='OK';}catch(e){r[n]=e.message;}}
  const inputs=await I.load({...view(dir),SecQgv2:V});r.qgv2_inputs=inputs?'LOADED':'NULL';r.reason=typeof I.lastReason==='function'?I.lastReason():'OLD';
  if(QS){const c=QS.compute({identities:[{company_id:'x',ticker:'MMM'}],publicScreens:inputs?{[I.FILE]:inputs}:{}});const p=c.rows.x.primary;r.total=p.total;r.reason_code=c.v2_reason;r.text=QS.naText(p,false);r.scored=Object.values(c.rows).filter(x=>x.primary.total!==null).length;}
  out[dir]=r;}
 process.stdout.write(JSON.stringify(out));
})();
"""


def screens(tmp_path, web, folders):
    """The given screen modules (`web`) reading each folder's three files the way the app does."""
    root = tmp_path / ('files-' + Path(web).name)
    root.mkdir()
    for label, folder in folders.items():
        copy(folder, root / label)
    script = tmp_path / 'screens.js'
    script.write_text(SCREENS)
    result = subprocess.run(['node', str(script), str(web), str(root)], text=True, capture_output=True, timeout=180)
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout)


def newer(folder, to):
    out = copy(folder, to)
    for name in UNIVERSE:
        data = payload(out, name)
        data['schema_version'] = 3
        (out / name).write_text(json.dumps(data))
    return out


@pytest.mark.skipif(not NODE, reason='Node runtime required')
def test_new_screens_read_old_and_new_files_and_ask_for_a_reload_on_a_newer_format(history, tmp_path):
    seen = screens(tmp_path, WEB, {'a-old-v1': as_version_1(history['day1'], tmp_path / 'v1'), 'b-new-v2': history['day2'],
                                   'c-newer-v3': newer(history['day2'], tmp_path / 'v3')})
    assert seen['a-old-v1'] | {} == dict(seen['a-old-v1'], shares='OK', qg='OK', qgv2='OK', qgv2_inputs='LOADED', reason=None)
    assert seen['b-new-v2']['qgv2'] == 'OK' and seen['b-new-v2']['shares'] == 'OK' and seen['b-new-v2']['qgv2_inputs'] == 'LOADED'
    assert seen['b-new-v2']['total'] is None                                   # MMM is X: withdrawn, no score
    # The same page (same modules in RAM) scored the version-1 file first; after the newer file is rejected no score of the
    # earlier load stays (no cache: data files are fetched with no-cache, the service worker caches the offline shell only).
    assert seen['a-old-v1']['scored'] == 1
    v3 = seen['c-newer-v3']
    assert (v3['shares'], v3['qg'], v3['qgv2']) == ('SEC_UNIVERSE_SHARES_SCHEMA_NEWER', 'SEC_UNIVERSE_QG_SCHEMA_NEWER', 'SEC_QGV2_SCHEMA_NEWER')
    assert (v3['qgv2_inputs'], v3['reason'], v3['reason_code'], v3['total'], v3['scored']) == ('NULL', 'SCHEMA_NEWER', 'SEC_QGV2_SCHEMA_NEWER', None, 0)
    assert v3['text'] == 'QGV v2 산출 불가 · 자료 형식이 새 버전입니다. 새로고침하세요'


OLD_WEB_COMMIT = '8d3c9800'   # canonical with #285, before this change: the "old screen"


@pytest.mark.skipif(not NODE, reason='Node runtime required')
def test_old_screens_block_new_files_as_a_whole_and_show_no_value(history, tmp_path):
    """Old screen + new file (a SAFETY block, not backward compatibility): the readers of the canonical commit before
    this change reject every version-2 file as a whole; the QGV v2 inputs are null, so no score (old or new) is shown.
    They still read version-1 files."""
    root = Path(__file__).resolve().parents[2]
    old = tmp_path / 'old-web'
    old.mkdir()
    for name in ('sec-universe-shares.js', 'sec-universe-qg.js', 'sec-qgv2.js', 'qgv2-inputs.js', 'qgv-v2.js', 'private-subset.js',
                 'share-class-groups.js', 'engine-preview.js', 'profile-defaults.js', 'type-config-defaults.js', 'dcf-parameters-defaults.js'):
        result = subprocess.run(['git', '-C', str(root), 'show', f'{OLD_WEB_COMMIT}:implementation/src/investment_system/product/web_assets/{name}'],
                                capture_output=True, timeout=60)
        if result.returncode != 0:
            pytest.skip('old screen sources not in this checkout')
        (old / name).write_bytes(result.stdout)
    # V-PRICE-BASIS (calc_version 2026-10-23.1) rows carry share_basis_factor, which the old sec-qgv2.js rejects: the old
    # screen reads a version-1 file only with the history entries of the earlier rules (the data before this change), and
    # rejects a version-1 file of the new rules as a whole (so sec-qgv2.json and sec-qgv2.js must be deployed together).
    v1 = as_version_1(history['day1'], tmp_path / 'v1')
    v1_new_rules = as_version_1(history['day1'], tmp_path / 'v1-new-rules')
    data = json.loads((v1 / 'sec-qgv2.json').read_text())
    for row in [*data['records'].values(), *data['target'].values()]:
        REF.legacy_histories(row)
    (v1 / 'sec-qgv2.json').write_text(json.dumps(data))
    seen = screens(tmp_path, old, {'a-old-v1': v1, 'b-new-v2': history['day1'], 'c-old-v1-new-rules': v1_new_rules})
    assert seen['a-old-v1'] == {'shares': 'OK', 'qg': 'OK', 'qgv2': 'OK', 'qgv2_inputs': 'LOADED', 'reason': 'OLD'}
    assert seen['c-old-v1-new-rules']['qgv2'] == 'SEC_QGV2_INVALID' and seen['c-old-v1-new-rules']['qgv2_inputs'] == 'NULL'
    assert seen['b-new-v2'] == {'shares': 'SEC_UNIVERSE_SHARES_INVALID', 'qg': 'SEC_UNIVERSE_QG_INVALID', 'qgv2': 'SEC_QGV2_INVALID',
                                'qgv2_inputs': 'NULL', 'reason': 'OLD'}


def test_no_stored_copy_of_data_or_scores_can_outlive_a_rejected_file():
    """#289 item 3(d): the service worker caches the offline shell only (no data file or script), and no screen module
    writes scores or public data to browser storage, so a rejected file cannot leave an older score on screen."""
    sw = (WEB / 'service-worker.js').read_text()
    names = re.search(r"const NAMES=\[([^\]]*)\]", sw).group(1)
    assert 'sec-' not in names and '.js' not in names.replace('.json', '') and names.count('.json') == 1     # manifest.json only
    for asset in ('qgv-scores.js', 'qgv2-inputs.js', 'sec-qgv2.js', 'sec-universe-shares.js', 'sec-universe-qg.js', 'playbook-screen.js',
                  'leaderboard-screen.js', 'company-screen.js'):
        text = (WEB / asset).read_text()
        assert 'localStorage.setItem' not in text and 'indexedDB' not in text and 'caches.' not in text, asset


def test_screens_reach_no_device_price_path_by_ticker():
    """DC-31 (PR-1b): the withdrawal guards of the device price path (collectQuotes by ticker, UNI-TARGET above) now protect only
    the TARGET v1 builder's device result until the 11/16 PR. Every screen reads the central publication (QgvScores.officialPage),
    whose own rows carry the withdrawal (state WITHDRAWN, price_status PRICE_IDENTITY_CONFLICT): no screen module calls the device
    path any more, so no screen can price a withdrawn code by its ticker."""
    allowed = {'qgv-scores.js', 'playbook-screen.js', 'data-refresh.js', 'target-v1-builder.js', 'target-v1-screen.js'}
    for path in sorted(WEB.glob('*.js')):
        if path.name in allowed:
            continue
        text = path.read_text(encoding='utf-8')
        assert 'collectQuotes(' not in text and '.pageResult(' not in text, path.name
    playbook = (WEB / 'playbook-screen.js').read_text(encoding='utf-8')
    # The playbook keeps the device result only for TargetV1Screen; its facts and candidates read officialPage.
    assert 'officialPage(' in playbook and 'computed:device' in playbook
