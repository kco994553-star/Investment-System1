"""One public counterexample set for Python and Main's Node/callsite/browser."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from investment_system.research.technical_filter_join import join_group_rows
from technical_membership_cases import apply_case, make_fixture

FIXTURE = Path(__file__).resolve().parents[2] / 'docs/research/common_classification/group-join-fixtures.json'
DATA = json.loads(FIXTURE.read_text())


def test_committed_cases_match_the_synthetic_generator():
    assert DATA == make_fixture()


@pytest.mark.parametrize('case', DATA['cases'], ids=lambda c: c['id'])
def test_shared_counterexample(case):
    args = apply_case(DATA['base'], case)['join']
    before = deepcopy(args)
    expected = case['expected']
    if not expected['ok']:
        with pytest.raises(ValueError) as exc:
            join_group_rows(**args)
        assert str(exc.value) == expected['code']
    else:
        actual = join_group_rows(**args)
        for key in ('selected_count', 'original_group_count', 'membership_validation'):
            assert actual[key] == expected[key]
        assert len(actual['issuer_connections']) == expected['issuer_connections']
        original = {row['code']: row for row in args['qgv_rows']}
        assert [row['code'] for row in actual['rows']] == [row['code'] for row in args['qgv_rows']
            if row['code'] in {r['code'] for r in actual['rows']}]
        for row in actual['rows']:
            assert row['score'] == original[row['code']]['score']
            assert row['rank'] == original[row['code']]['rank']
    assert args == before
