"""New date/identity join boundaries; existing calculation suites are not replayed."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess

import pytest

from investment_system.research.technical_filter_join import join_filtered_rows


FOLDER = Path(__file__).parent / 'fixtures/technical_filter_join_v1'


def inputs():
    return json.loads((FOLDER / 'inputs.json').read_text())


def test_public_join_scenarios_and_original_rank_score_order():
    payload = inputs()
    expected = json.loads((FOLDER / 'expectations.json').read_text())
    board = payload['cases']['original_board']
    before = deepcopy(payload)
    for name, case in payload['join_inputs'].items():
        want = expected['cases'][name]
        if want['error']:
            with pytest.raises(ValueError, match='^' + want['error'] + '$'):
                join_filtered_rows(board, **case, data_kind=payload['data_kind'])
        else:
            rows = join_filtered_rows(board, **case, data_kind=payload['data_kind'])
            assert [r['id'] for r in rows] == want['selected_row_ids']
            assert [r['rank']['official'] for r in rows] == want['original_qgv_ranks']
            assert [r['score']['total'] for r in rows] == want['original_qgv_scores']
            assert rows == [r for r in case['qgv_rows'] if r['id'] in want['selected_row_ids']]
    assert payload == before


def test_new_fixture_uses_unchanged_main_reader_contract():
    root = Path(__file__).parents[2]
    script = r'''const fs=require('fs'),T=require(process.argv[1]);
const p=JSON.parse(fs.readFileSync(process.argv[2])),v=T.validate(p);
if(!v.ok)throw Error(JSON.stringify(v));
const b=v.value.boards[0].board,r=T.evaluate(b,p.join_inputs.same_date_same_security.conditions);
const ids=[...r.rows].filter(([,r])=>r.state==='PASS').map(([id])=>id).sort();
if(JSON.stringify(ids)!==JSON.stringify(['SYNTHETIC:001','SYNTHETIC:003']))throw Error('filter');
console.log('new join fixture accepted');'''
    result = subprocess.run(['node', '-e', script,
        str(root / 'src/investment_system/product/web_app/tech-screen.js'),
        str(FOLDER / 'inputs.json')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_historical_mapping_cannot_override_active_identity():
    payload = inputs()
    board = payload['cases']['original_board']
    case = payload['join_inputs']['same_date_same_security']
    old = deepcopy(case['security_links'][0])
    old.update(valid_from='2016-01-01', valid_to='2017-01-04',
               symbol='SYNTHETIC:OLD_SYMBOL', share_class='SYNTHETIC:OLD_LABEL')
    case['security_links'].insert(0, old)
    rows = join_filtered_rows(board, **case, data_kind='SYNTHETIC')
    assert [row['rank']['official'] for row in rows] == [4, 9]
    assert [row['rank']['of'] for row in rows] == [10, 10]


@pytest.mark.parametrize('change,error', [
    ('duplicate_board', 'DUPLICATE_TECHNICAL_KEY'),
    ('inconsistent_series', 'TECHNICAL_IDENTITY_MISMATCH'),
    ('retained_synthetic', 'SYNTHETIC_SECURITY_ID_ON_RETAINED_INPUT'),
    ('ticker_id', 'ISSUER_OR_TICKER_IS_NOT_SECURITY_ID'),
    ('issuer_id', 'ISSUER_OR_TICKER_IS_NOT_SECURITY_ID'),
    ('unconfirmed', 'FIXED_SECURITY_LINK_UNCONFIRMED'),
    ('reference_missing', 'FIXED_SECURITY_LINK_EVIDENCE_REQUIRED'),
    ('wrong_issuer', 'ISSUER_LINK_MISMATCH'),
    ('wrong_symbol', 'SYMBOL_LINK_MISMATCH'),
    ('unknown_group', 'GROUP_MEMBERSHIP_UNCONFIRMED'),
])
def test_additional_join_boundary(change, error):
    payload = inputs()
    board = payload['cases']['original_board']
    case = payload['join_inputs']['same_date_same_security']
    data_kind = 'SYNTHETIC'
    if change == 'duplicate_board':
        board['metrics']['momentum_3m']['rows'].append(deepcopy(board['metrics']['momentum_3m']['rows'][0]))
    elif change == 'inconsistent_series':
        board['metrics']['momentum_6m']['rows'][0]['series_id'] = 'REQUEST:OTHER'
    elif change == 'retained_synthetic':
        data_kind = 'RETAINED_INPUT'
    elif change in ('ticker_id', 'issuer_id'):
        row = case['qgv_rows'][0]
        row['security_id'] = row['ticker' if change == 'ticker_id' else 'id']
    elif change == 'unconfirmed':
        case['security_links'][0]['identity_status'] = 'UNVERIFIED'
    elif change == 'reference_missing':
        case['security_links'][0]['reference'] = ''
    elif change == 'wrong_issuer':
        case['qgv_rows'][0]['id'] = 'SYNTHETIC:ISSUER:WRONG'
    elif change == 'wrong_symbol':
        case['qgv_rows'][0]['ticker'] = 'SYNTHETIC:OTHER'
    else:
        board['membership_status'] = 'UNKNOWN'
    with pytest.raises(ValueError, match='^' + error + '$'):
        join_filtered_rows(board, **case, data_kind=data_kind)
