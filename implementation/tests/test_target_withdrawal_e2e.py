"""TARGET identity withdrawal, Universe conflict code and shares policy NA: generation -> deploy check -> device (owner
instruction 2026-10-17 item 3).

Generation runs the real daily producers: the TARGET step (tools/public_screens_pipeline.py `collect`, which writes
sec-public-inputs.json /4 and stages the TARGET rows of sec-qgv2.json) and the shard step's merge of the staged TARGET rows
into the live sec-qgv2.json (tools/sec_universe_shares.py `run`, preserve-only path, the same `qgv2.merge(previous, ...,
target_updates=staged)` call the live path makes first). The deploy check is the real pre-deploy freshness guard
(tools/pages_freshness_guard.py) against an in-memory live Pages copy. The device side runs the real browser modules in
node (SecQgv2 strict reader -> Qgv2Inputs -> QgvScores, PlaybookScreen candidate ranking) on the deployed bytes.

Synthetic SEC bytes, fake clients, injected clocks and made-up quotes only: no network, credential or real price.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from investment_system.markets.us import US_LISTINGS
from investment_system.providers.sec_collection import SecCollectionError
from investment_system.universe import sec_qgv2 as qgv2
from tests.test_pages_freshness_guard import REF, Site, guard, load_tool, section_line
from tests.test_public_sec_inputs import raw
from tests.test_target_na_schema_v4 import SCHEDULED, factory

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'src/investment_system/product/web_assets'
PIPE = load_tool('public_screens_pipeline')
SHARD = load_tool('sec_universe_shares')
INPUTS = 'sec-public-inputs.json'
UTC = timezone.utc
T0 = datetime(2026, 10, 14, 22, 20, tzinfo=UTC)          # New York 18:20, after the close
T1 = T0 + timedelta(days=1)
UNIVERSE_AT = datetime(2026, 10, 13, 22, 30, tzinfo=UTC)
CIK_MISMATCH = SecCollectionError('SEC_CIK_MISMATCH', stage='parse')
IDS = sorted(US_LISTINGS)


def bodies(company, *, reported_shares=True, diluted_shares=True):
    """Synthetic companyfacts rich enough for QGV v2 Q·G, with the TARGET cover share fact unless `reported_shares` is
    False (sec-public-inputs.json policy NA) and the diluted share counts unless `diluted_shares` is False (V NA)."""
    cik = US_LISTINGS[company]['cik']
    omit = () if diluted_shares else ('WeightedAverageNumberOfDilutedSharesOutstanding',)
    facts_b, subs_b = REF.synthetic_sec(cik, seed=50 + IDS.index(company), growth=0.06 + 0.01 * (IDS.index(company) % 7), omit=omit)
    facts, subs = json.loads(facts_b), json.loads(subs_b)
    cover_facts, cover_subs = raw(company)
    if reported_shares:
        facts['facts']['dei'] = cover_facts['facts']['dei']
    subs['filings'] = cover_subs['filings']
    return facts, subs


def live_qgv2():
    """The live sec-qgv2.json before day 0: the synthetic Universe cross-section plus the issuer of the TARGET company
    googl under both of its share-class codes (one CIK)."""
    updates = REF.synthetic_universe_updates(acquired_at=UNIVERSE_AT)
    facts, subs = bodies('googl')
    updates.update(qgv2.build_issuer_records(codes=('NASDAQ:GOOGL', 'NASDAQ:GOOG'), cik=US_LISTINGS['googl']['cik'],
                                             companyfacts_body=json.dumps(facts).encode(), submissions_body=json.dumps(subs).encode(),
                                             acquired_at=UNIVERSE_AT))
    return qgv2.merge(None, updates, as_of=UNIVERSE_AT + timedelta(minutes=5), shard_index=3)


def daily(tmp_path, name, site, when, *, failures=None, overrides=None):
    """TARGET step then the shard step's merge of the staged TARGET rows, into one artifact folder."""
    out = tmp_path / name
    out.mkdir()
    previous, state = PIPE.load_previous_inputs(open_response=site)
    sec = {company: bodies(company) for company in IDS}
    sec.update(overrides or {})
    PIPE.collect(out, environ=SCHEDULED, client_factory=factory(when, failures, sec), previous=previous,
                 previous_state=state, now=lambda: when + timedelta(minutes=5))
    assert SHARD.run(out, live=False, preserve_only=True, now=lambda: when + timedelta(minutes=10), open_previous=site) == 0
    artifact = tmp_path / (name + '-artifact')
    artifact.mkdir()
    for file in (INPUTS, qgv2.FILENAME):
        shutil.copyfile(out / file, artifact / file)
    return artifact


def load(folder, name):
    return json.loads((Path(folder) / name).read_bytes())


DEVICE = r"""
const path=require('node:path'),fs=require('node:fs'),W=process.argv[2],input=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
for(const [name,file] of [['EnginePreview','engine-preview.js'],['ProfileDefaults','profile-defaults.js'],['TypeConfigDefaults','type-config-defaults.js'],['DcfParametersDefaults','dcf-parameters-defaults.js'],['SecQgv2','sec-qgv2.js'],['QgvV2','qgv-v2.js'],['Qgv2Inputs','qgv2-inputs.js'],['QgvScores','qgv-scores.js']])globalThis[name]=require(path.join(W,file));
const P=require(path.join(W,'playbook-screen.js')),SQ=globalThis.Qgv2Inputs,QS=globalThis.QgvScores;
const inputs=SQ.fromInputs(globalThis.SecQgv2.toInputs(input.payload,{now:input.now}));
const computed=QS.compute({identities:input.identities,publicScreens:{[SQ.FILE]:inputs},quotes:input.quotes,scoringDefault:'v2'});
const rows={};for(const [id,r] of Object.entries(computed.rows)){const p=r.primary;rows[id]={code:r.code,q:p.q,g:p.g,v:p.v,total:p.total,rank:r.rank,total_reason:p.total_reason||null,source_reason_codes:p.source_reason_codes||[],v_reasons:Object.fromEntries(Object.entries(p.factors||{}).filter(([k])=>k.startsWith('v_')).map(([k,f])=>[k,f.reason]))};}
const records={};for(const k of input.records)records[k]={state:inputs.records[k].state,identity_withdrawn:inputs.records[k].identity_withdrawn===true,in_cross_section:inputs.records[k].in_cross_section,q:inputs.records[k].qg_axes.Q.score,g:inputs.records[k].qg_axes.G.score};
const ranked=P.candidateRanking(computed,{[SQ.FILE]:inputs},input.codes).map(r=>({code:r.code,total:r.total,rank:r.rank,qg_available:r.qg_available}));
process.stdout.write(JSON.stringify({rows,records,ranked}));
"""


def device(tmp_path, payload, *, identities, quotes, records=(), codes=()):
    """The real browser modules on the deployed sec-qgv2.json bytes (strict reader). Prints scores and states only."""
    script, data = tmp_path / 'device.js', tmp_path / 'device-input.json'
    script.write_text(DEVICE)
    data.write_text(json.dumps({'payload': payload, 'now': (T1 + timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
                                'identities': identities, 'quotes': quotes, 'records': list(records), 'codes': list(codes)}))
    result = subprocess.run(['node', str(script), str(WEB), str(data)], text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout)


IDENTITIES = [{'company_id': 'googl', 'ticker': 'GOOGL'}, {'company_id': 'msft', 'ticker': 'MSFT'},
              {'company_id': 'nvda', 'ticker': 'NVDA'}]
# Made-up device quotes (RAM in the app; numbers are synthetic, never real prices).
QUOTES = {code: {'price': 50.0 + i, 'currency': 'USD'} for i, code in enumerate(
    ['TARGET:googl', 'TARGET:msft', 'TARGET:nvda', 'NASDAQ:GOOGL', 'NASDAQ:GOOG'] + [c for c, *_ in REF.universe_spec()])}


@pytest.mark.skipif(shutil.which('node') is None, reason='Node runtime required')
def test_target_withdrawal_and_policy_na_from_generation_through_the_guard_to_the_device(tmp_path, capsys):
    site = Site({qgv2.FILENAME: qgv2.encode(live_qgv2())})
    # Day 0: every TARGET issuer collected; msft without the cover share fact and without diluted share counts.
    msft_na = {'msft': bodies('msft', reported_shares=False, diluted_shares=False)}
    day0 = daily(tmp_path, 'day0', site, T0, overrides=msft_na)
    code, out = guard(day0, site, capsys)
    assert code == 0 and section_line(out, qgv2.FILENAME, 'target')['verdict'] == 'PASS'
    site.deploy(day0)
    live = load(day0, qgv2.FILENAME)
    googl_acquired = live['target']['googl']['acquired_at']
    assert live['target']['googl']['state'] == 'LIVE' and live['target']['googl']['axes']['Q']['score'] is not None

    # (c) Shares policy NA: sec-public-inputs.json NOT_AVAILABLE with the real acquired_at; Q·G of the same collection
    # published and scored; only the shares-dependent values (V inputs) are NA.
    msft_inputs = next(r for r in load(day0, INPUTS)['companies'] if r['company_id'] == 'msft')
    assert (msft_inputs['status'], msft_inputs['reason_codes'], msft_inputs['acquired_at']) == (
        'NOT_AVAILABLE', ['SEC_SHARE_CONCEPT_MISSING'], T0.isoformat())
    msft = live['target']['msft']
    assert msft['state'] == 'LIVE' and msft['axes']['Q']['score'] is not None and msft['axes']['G']['score'] is not None
    assert msft['v_inputs_v2']['diluted_shares'] is None and msft['acquired_at'] == T0.isoformat().replace('+00:00', 'Z')

    seen = device(tmp_path, live, identities=IDENTITIES, quotes=QUOTES, records=('TARGET:googl', 'NASDAQ:GOOGL', 'NASDAQ:GOOG'),
                  codes=('NASDAQ:GOOGL', 'NASDAQ:GOOG', 'NASDAQ:MSFT'))
    assert seen['rows']['googl']['code'] == 'TARGET:googl' and seen['rows']['googl']['total'] is not None
    assert seen['rows']['msft']['q'] is not None and seen['rows']['msft']['g'] is not None   # Q·G kept with shares NA
    assert seen['rows']['msft']['v'] is None and seen['rows']['msft']['total'] is not None   # V NA, total from Q·G
    assert set(seen['rows']['msft']['v_reasons'].values()) == {'SHARES_NOT_AVAILABLE'}           # every V factor: shares NA
    assert seen['records']['NASDAQ:GOOG']['state'] == 'LIVE'

    # Day 1: googl's TARGET collection hits an identity conflict (SEC response bound to another CIK).
    day1 = daily(tmp_path, 'day1', site, T1, failures={'googl': CIK_MISMATCH}, overrides=msft_na)
    inputs_row = next(r for r in load(day1, INPUTS)['companies'] if r['company_id'] == 'googl')
    assert (inputs_row['status'], inputs_row['withdrawn_acquired_at']) == ('WITHDRAWN', T0.isoformat())
    # (a) Generation: the sec-qgv2.json TARGET row is withdrawn, never the previous values.
    target = load(day1, qgv2.FILENAME)['target']['googl']
    assert target['reason_codes'] == [qgv2.WITHDRAWN_REASON] and target['state'] == 'NOT_AVAILABLE'
    assert target['acquired_at'] is None and target['metrics'] == {} and target['fiscal_year_end'] is None
    assert target['axes']['Q']['score'] is None and all(v is None for v in target['factors'].values())
    assert target['detected_at'] == inputs_row['detected_at'].replace('+00:00', 'Z') and target['withdrawn_acquired_at'] == googl_acquired
    qgv2.require_qgv2(load(day1, qgv2.FILENAME))
    # Deploy check: the withdrawal names the live observation exactly -> passes as WITHDRAWN in both files.
    code, out = guard(day1, site, capsys)
    target_line, inputs_line = section_line(out, qgv2.FILENAME, 'target'), section_line(out, INPUTS, 'companies')
    assert code == 0 and (target_line['verdict'], target_line['withdrawn'], target_line['lost_record']) == ('PASS', '1', '0')
    assert inputs_line['withdrawn'] == '1'
    # ... a withdrawal that names another observation is refused (no status-only withdrawal).
    tampered = load(day1, qgv2.FILENAME)
    tampered['target']['googl']['withdrawn_acquired_at'] = (T0 - timedelta(days=2)).isoformat().replace('+00:00', 'Z')
    bad = tmp_path / 'bad'
    bad.mkdir()
    (bad / qgv2.FILENAME).write_text(json.dumps(tampered))
    code, out = guard(bad, site, capsys)
    assert code == 1 and f'file={qgv2.FILENAME} section=target code=googl kind=OLDER ' in out
    site.deploy(day1)
    # (b) Device: the deployed file read by the real modules. googl is scored through no row: not its TARGET row, not
    # GOOGL / GOOG (same CIK, other share class), not the ticker fallback, and is never a candidate.
    seen = device(tmp_path, load(day1, qgv2.FILENAME), identities=IDENTITIES, quotes=QUOTES,
                  records=('TARGET:googl', 'NASDAQ:GOOGL', 'NASDAQ:GOOG'), codes=('NASDAQ:GOOGL', 'NASDAQ:GOOG', 'NASDAQ:MSFT'))
    row = seen['rows']['googl']
    assert row['code'] == 'TARGET:googl' and (row['q'], row['g'], row['v'], row['total'], row['rank']) == (None,) * 5
    assert row['total_reason'] == 'SOURCE_NOT_AVAILABLE' and row['source_reason_codes'] == [qgv2.WITHDRAWN_REASON]
    for key in ('TARGET:googl', 'NASDAQ:GOOGL', 'NASDAQ:GOOG'):
        assert seen['records'][key] == {'state': 'WITHDRAWN', 'identity_withdrawn': True, 'in_cross_section': False,
                                        'q': None, 'g': None}, key
    ranked = {r['code']: r for r in seen['ranked']}
    assert all(ranked[c]['total'] is None and ranked[c]['rank'] is None for c in ('NASDAQ:GOOGL', 'NASDAQ:GOOG'))
    assert seen['rows']['msft']['total'] is not None   # the policy NA company keeps its Q·G score

    # Day 2: the conflict persists and the TARGET collection fails transiently: the withdrawal stays (never the old row).
    day2 = daily(tmp_path, 'day2', site, T1 + timedelta(days=1), failures={'googl': SecCollectionError('SEC_HTTP_503', stage='fetch', http_status=503)},
                 overrides=msft_na)
    kept = load(day2, qgv2.FILENAME)['target']['googl']
    assert kept['reason_codes'] == [qgv2.WITHDRAWN_REASON] and kept['withdrawn_acquired_at'] == googl_acquired
    code, out = guard(day2, site, capsys)
    line = section_line(out, qgv2.FILENAME, 'target')
    assert code == 0 and (line['equal'], line['newer'], line['withdrawn']) == ('1', '16', '0')   # googl: the same withdrawal
    # An artifact built before the withdrawal (day 0) cannot bring the stopped TARGET row back.
    code, out = guard(day0, site, capsys)
    assert code == 1 and f'file={qgv2.FILENAME} section=target code=googl kind=OLDER ' in out


def test_universe_conflict_code_is_withdrawn_in_generation_and_passes_the_deploy_check(tmp_path, capsys):
    """(d) Universe conflict code (multi-CIK claim): generation publishes a withdrawal row naming the live observation
    (owner decision UNI-WITHDRAWN (a), 2026-10-17; before: CIK_UNRESOLVED, refused as LOST_RECORD), the deploy check
    passes it as WITHDRAWN, and the other code of the same issuer keeps its own row."""
    live = live_qgv2()
    site = Site({qgv2.FILENAME: qgv2.encode(live)})
    code_ = 'NASDAQ:GOOG'
    mine = qgv2.merge(live, {}, as_of=T1, shard_index=3, conflicts={code_})
    row = mine['records'][code_]
    assert (row['state'], row['reason_codes'], row['cik'], row['acquired_at']) == ('NOT_AVAILABLE', [qgv2.WITHDRAWN_REASON], None, None)
    assert (row['withdrawn_acquired_at'], row['withdrawn_cik']) == (live['records'][code_]['acquired_at'], live['records'][code_]['cik'])
    assert mine['records']['NASDAQ:GOOGL']['state'] == 'LIVE'      # the other code of the issuer is its own row
    folder = tmp_path / 'a'
    folder.mkdir()
    (folder / qgv2.FILENAME).write_bytes(qgv2.encode(mine))
    code, out = guard(folder, site, capsys)
    line = section_line(out, qgv2.FILENAME, 'records')
    assert code == 0 and (line['withdrawn'], line['lost_record']) == ('1', '0')


def test_merge_rules_of_a_target_withdrawal():
    """qgv2.merge: a staged withdrawal never carries the kept values; it names the kept observation, re-detection keeps the
    named observation, a newer collection resolves it, and the strict validator accepts the two keys on TARGET rows only."""
    base = live_qgv2()
    entries = [(cid, *(json.dumps(x).encode() for x in bodies(cid)), T0) for cid in ('googl', 'msft')]
    live = qgv2.merge(base, {}, as_of=T0 + timedelta(minutes=10), shard_index=3, target_updates=qgv2.build_target_rows(entries))
    observed = live['target']['googl']['acquired_at']
    staged = lambda at: qgv2.target_updates_from(qgv2.merge(None, {}, as_of=at + timedelta(minutes=1), shard_index=None,
                                                            target_updates={'googl': qgv2.withdrawn_target('googl', at.isoformat())}))
    assert set(staged(T1)) == {'googl'}                                     # carried although it has no acquired_at
    first = qgv2.merge(live, {}, as_of=T1 + timedelta(minutes=10), shard_index=3, target_updates=staged(T1))
    row = first['target']['googl']
    assert (row['withdrawn_acquired_at'], row['detected_at'], row['metrics'], row['axes']['G']['score']) == (
        observed, T1.isoformat().replace('+00:00', 'Z'), {}, None)
    assert first['target']['msft']['acquired_at'] == live['target']['msft']['acquired_at']   # other TARGET rows untouched
    # Detected again later: the same stopped observation, a later detection.
    later = T1 + timedelta(days=1)
    again = qgv2.merge(first, {}, as_of=later + timedelta(minutes=10), shard_index=3, target_updates=staged(later))['target']['googl']
    assert (again['withdrawn_acquired_at'], again['detected_at']) == (observed, later.isoformat().replace('+00:00', 'Z'))
    # The same (kept) detection again, or none staged: unchanged; never the kept values.
    assert qgv2.merge(first, {}, as_of=later, shard_index=3, target_updates=staged(T1))['target']['googl'] == row
    assert qgv2.merge(first, {}, as_of=later, shard_index=3)['target']['googl'] == row
    # Resolved: a new successful collection after the detection replaces the withdrawal.
    fresh = [('googl', *(json.dumps(x).encode() for x in bodies('googl')), later)]
    resolved = qgv2.merge(first, {}, as_of=later + timedelta(minutes=10), shard_index=3, target_updates=qgv2.build_target_rows(fresh))
    assert resolved['target']['googl']['state'] == 'LIVE' and 'detected_at' not in resolved['target']['googl']
    # Only US SEC TARGET issuers can be withdrawn; a withdrawal never appears in the Universe records.
    with pytest.raises(ValueError):
        qgv2.withdrawn_target('hanmi', T1.isoformat())
    bad = json.loads(json.dumps(first))
    bad['records']['NASDAQ:GOOG'] = dict(bad['target']['googl'])
    with pytest.raises(ValueError, match='SEC_QGV2_INVALID'):
        qgv2.require_qgv2(bad)
