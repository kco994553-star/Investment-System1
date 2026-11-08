"""Independent synthetic inputs for the new common-classification projections."""
from copy import deepcopy

import pytest

from investment_system.research.common_classification.technical_macro import macro_projection, technical_groups
from investment_system.research.common_classification.catalog import MAPPING_VERSION, VERSION
from investment_system.research.exp_deciles.technical_leaderboard import filter_board
from investment_system.research.exp_deciles.technical_measures import METRIC_IDS


SECTOR = 'INFORMATION_TECHNOLOGY'


def fixture(count=10, basis='RAW'):
    view = dict(schema_version='common-classification-view/1', valuation_date='2017-01-06',
                knowledge_as_of='2017-01-06T23:00:00Z', data_kind='SYNTHETIC', members=[], rows=[],
                classification_hash='a' * 64, dictionary_version=VERSION, mapping_version=MAPPING_VERSION)
    measurements, links = [], []
    for index in range(count):
        company, issuer, sid, series = (f'SYNTHETIC:{kind}:{index}' for kind in ('COMPANY', 'ISSUER', 'SECURITY', 'SERIES'))
        symbol = f'SYNTHETIC:TICKER:{index}'
        dimension = lambda key: dict(id=key, status='CONFIRMED', reasons=[], evidence_refs=['SYNTHETIC:SOURCE'])
        view['members'].append(company)
        view['rows'].append(dict(company_id=company, issuer_id=issuer, record_id=f'SYNTHETIC:RECORD:{index}',
                                sector=dimension(SECTOR), industry=dimension('semiconductors'), accounting=dimension('GENERAL'),
                                source_sic=dict(system='SEC_SIC', code='3674', observed_at='2017-01-06T00:00:00Z'), tags={}))
        links.append(dict(company_id=company, issuer_id=issuer, security_id=sid, series_id=series, symbol=symbol,
                          share_class='A', security_type='COMMON', adr_ratio=None, reference='SYNTHETIC:FIXED_LINK',
                          identity_reference='SYNTHETIC:IDENTITY', identifier_type='SYNTHETIC_FIXED_SECURITY_ID',
                          identity_status='CONFIRMED', valid_from='2017-01-06', valid_to='2017-01-06',
                          recorded_at='2017-01-06T20:00:00Z', acquired_at='2017-01-06T19:00:00Z'))
        measurements.append(dict(signal_day='2017-01-06', security_id=sid, series_id=series, symbol=symbol,
                                 share_class='A', security_type='COMMON', adr_ratio=None, price_basis=basis,
                                 metrics={name: dict(value=str(index + 1), null_reasons=[]) for name in METRIC_IDS}))
    return view, measurements, links


def group(result):
    return next(item for item in result['groups'] if item['sector_id'] == SECTOR)


@pytest.mark.parametrize('basis', ['RAW', 'SPLIT_ADJUSTED'])
def test_complete_ten_member_sector_reuses_board_kernel_and_original_ranks(basis):
    view, measures, links = fixture(basis=basis)
    before = deepcopy((view, measures, links))
    result = technical_groups(view, measures, links, price_basis=basis)
    selected = group(result)
    assert selected['membership_status'] == 'CONFIRMED'
    board = selected['board']
    metric = board['metrics']['momentum_3m']
    assert (metric['n_members'], metric['n_valid'], metric['median'], metric['k']) == (10, 10, '5.5', 1)
    assert [row['rank'] for row in metric['rows']] == list(range(1, 11))
    assert [row['decile'] for row in metric['rows']] == list(range(10, 0, -1))
    snapshot = deepcopy(board)
    passed = filter_board(board, [dict(metric='volatility_6m', condition='exclude_D10')])
    assert len(passed) == 9
    assert min(row['rank'] for row in metric['rows'] if row['security_id'] in passed) == 2
    assert board == snapshot
    assert (view, measures, links) == before


def test_nine_members_keep_median_rank_without_deciles():
    view, measures, links = fixture(9)
    metric = group(technical_groups(view, measures, links, price_basis='RAW'))['board']['metrics']['momentum_3m']
    assert (metric['n_members'], metric['n_valid'], metric['median'], metric['k']) == (9, 9, '5', None)
    assert [row['rank'] for row in metric['rows']] == list(range(1, 10))
    assert all(row['decile'] is None and row['conditions']['exclude_D10'] is None for row in metric['rows'])


def test_missing_measurement_preserves_confirmed_membership_and_null_row():
    view, measures, links = fixture()
    result = technical_groups(view, measures[1:], links, price_basis='RAW')
    selected = group(result)
    metric = selected['board']['metrics']['momentum_3m']
    assert selected['membership_status'] == 'CONFIRMED'
    assert (metric['n_members'], metric['n_valid']) == (10, 9)
    missing = next(row for row in metric['rows'] if row['security_id'] == links[0]['security_id'])
    assert missing['series_id'] == links[0]['series_id']
    assert missing['value'] is None and 'MEASUREMENT_MISSING' in missing['null_reasons']


@pytest.mark.parametrize('field,value,reason', [
    ('signal_day', '2017-01-05', 'SIGNAL_DAY_MISMATCH'),
    ('share_class', 'B', 'SHARE_CLASS_MISMATCH'),
    ('share_class', None, 'SHARE_CLASS_MISMATCH'),
    ('security_type', 'ADR', 'SECURITY_TYPE_MISMATCH'),
    ('price_basis', 'SPLIT_ADJUSTED', 'PRICE_BASIS_MISMATCH'),
    ('price_basis', None, 'PRICE_BASIS_MISMATCH'),
    ('adr_ratio', '2', 'ADR_RATIO_MISMATCH'),
    ('security_id', 'SYNTHETIC:OTHER', 'SECURITY_LINK_MISMATCH'),
])
def test_bad_measurement_keeps_member_but_cannot_contribute_value(field, value, reason):
    view, measures, links = fixture()
    if value is None:
        del measures[0][field]
    else:
        measures[0][field] = value
    result = technical_groups(view, measures, links, price_basis='RAW')
    assert reason in result['rows'][0]['reasons']
    assert reason in result['diagnostics'][0]['reasons']
    assert result['diagnostics'][0]['measurement'] == measures[0]
    selected = group(result)
    assert selected['membership_status'] == 'CONFIRMED'
    assert (selected['board']['metrics']['momentum_3m']['n_members'], selected['board']['metrics']['momentum_3m']['n_valid']) == (10, 9)


def test_adr_ratio_missing_different_or_matching():
    view, measures, links = fixture()
    links[0].update(security_type='ADR', adr_ratio='2')
    measures[0].update(security_type='ADR', adr_ratio='2.0')
    assert group(technical_groups(view, measures, links, price_basis='RAW'))['board']['metrics']['momentum_3m']['n_valid'] == 10
    del measures[0]['adr_ratio']
    result = technical_groups(view, measures, links, price_basis='RAW')
    assert 'ADR_RATIO_MISMATCH' in result['rows'][0]['reasons']
    del links[0]['adr_ratio']
    result = technical_groups(view, measures, links, price_basis='RAW')
    assert group(result)['membership_status'] == 'UNKNOWN'


@pytest.mark.parametrize('bad_link', ['missing', 'expired', 'issuer', 'unconfirmed', 'security_type'])
def test_unknown_security_membership_never_shrinks_group_into_rankable_subset(bad_link):
    view, measures, links = fixture()
    if bad_link == 'missing':
        links = links[1:]
    elif bad_link == 'expired':
        links[0].update(valid_from='2017-01-05', valid_to='2017-01-05')
    elif bad_link == 'issuer':
        links[0]['issuer_id'] = 'SYNTHETIC:WRONG_ISSUER'
    elif bad_link == 'unconfirmed':
        links[0]['identity_status'] = 'UNKNOWN'
    else:
        del links[0]['security_type']
    result = technical_groups(view, measures, links, price_basis='RAW')
    selected = group(result)
    metric = selected['board']['metrics']['momentum_3m']
    assert selected['membership_status'] == 'UNKNOWN'
    assert selected['counts']['company_members'] == 10
    assert metric['n_members'] is metric['n_valid'] is metric['median'] is None
    assert all(row['rank'] is None for row in metric['rows'])
    assert result['counts']['original_companies'] == 10


def test_unknown_classification_blocks_all_sector_memberships_but_keeps_absolute_values():
    view, measures, links = fixture()
    view['rows'][0]['sector'].update(id=None, status='UNKNOWN', reasons=['SOURCE_UNRESOLVED'])
    result = technical_groups(view, measures, links, price_basis='RAW')
    assert all(g['membership_status'] == 'UNKNOWN' for g in result['groups'])
    metric = group(result)['board']['metrics']['momentum_3m']
    assert len(metric['rows']) == 9
    assert all(row['value'] is not None and row['rank'] is None and row['conditions']['gt_zero'] is True for row in metric['rows'])
    assert len(result['diagnostics']) == 10


def test_duplicate_security_mapping_rejected():
    view, measures, links = fixture()
    links.append(deepcopy(links[0]))
    with pytest.raises(ValueError, match='DUPLICATE_SECURITY_LINK'):
        technical_groups(view, measures, links, price_basis='RAW')


def test_tags_do_not_change_numerical_projection_or_benchmark_selection():
    view, measures, links = fixture()
    technical = technical_groups(view, measures, links, price_basis='RAW')
    macro = macro_projection(view)
    for row in view['rows']:
        row['tags'] = {'lynch': ['fast_grower'], 'semiconductors': True, 'cyclical': True}
    assert technical_groups(view, measures, links, price_basis='RAW') == technical
    assert macro_projection(view) == macro


def test_reit_and_media_etf_choices_do_not_confirm_common_sector():
    view, _, _ = fixture(2)
    for row, sic in zip(view['rows'], ('6798', '4841')):
        row['source_sic']['code'] = sic
        row['sector'].update(id=None, status='UNKNOWN', reasons=['BOOK_SECTOR_UNRESOLVED'])
    result = macro_projection(view)
    assert [row['benchmark']['etf'] for row in result['rows']] == ['XLRE', 'XLC']
    assert [row['source_industry']['group'] for row in result['rows']] == ['finance_real_estate', 'telecommunications']
    assert all(row['sector']['status'] == 'UNKNOWN' and row['statistic_mapping']['status'] == 'UNKNOWN' for row in result['rows'])
    assert result['probabilities'] is result['sector_returns'] is None


def source_link(**changes):
    return dict(system='SYNTHETIC:STATISTICS', version='1', code='3674',
                target_industry_id='semiconductors', relation='SOURCE_BROADER', evidence_refs=['SYNTHETIC:CORRESPONDENCE'],
                valid_from='2017-01-06', valid_to='2017-01-07',
                recorded_at='2017-01-06T20:00:00Z', acquired_at='2017-01-06T19:00:00Z', **changes)


def test_macro_mapping_requires_explicit_system_version_relation_and_active_target():
    view, _, _ = fixture(1)
    link = source_link()
    row = macro_projection(view, [link])['rows'][0]
    assert row['statistic_mapping'] == dict(status='LINKED', source_links=[link], reasons=[])
    assert row['probabilities'] is row['sector_returns'] is None
    link['target_industry_id'] = '3674'  # Same text as SEC code is insufficient.
    with pytest.raises(ValueError, match='MACRO_TARGET_INDUSTRY_UNKNOWN'):
        macro_projection(view, [link])
    link['target_industry_id'] = 'software'  # Existing but not this company's target.
    assert macro_projection(view, [link])['rows'][0]['statistic_mapping']['status'] == 'UNKNOWN'
    link = source_link()
    link.update(valid_from='2017-01-05', valid_to='2017-01-06')
    assert macro_projection(view, [link])['rows'][0]['statistic_mapping']['status'] == 'UNKNOWN'
    for field in ('system', 'version', 'relation', 'evidence_refs', 'valid_to'):
        bad = source_link()
        del bad[field]
        with pytest.raises(ValueError, match='MACRO_SOURCE_LINK_EVIDENCE_REQUIRED'):
            macro_projection(view, [bad])


TIME_CASES = [
    (None, 'TIME_UNKNOWN'),
    ('2017-01-06T23:00:01Z', 'NOT_AVAILABLE'),
    ('2017-01-06', 'TIME_UNKNOWN'),
    ('2017-01-05', None),
    ('2017-01-06T23:00:00Z', None),
    ('2017-01-06T19:00:00', 'TIME_UNKNOWN'),
]


@pytest.mark.parametrize('field,label', [('recorded_at', 'RECORD'), ('acquired_at', 'EVIDENCE')])
@pytest.mark.parametrize('value,error', TIME_CASES)
def test_security_link_time_boundary_never_promotes_future_or_unknown_evidence(field, label, value, error):
    view, measures, links = fixture()
    if value is None:
        del links[0][field]  # Legacy #515 does not supply these common-link extensions.
    else:
        links[0][field] = value
    result = technical_groups(view, measures, links, price_basis='RAW')
    metric = group(result)['board']['metrics']['momentum_3m']
    assert result['counts']['original_companies'] == 10
    if error:
        reason = 'SECURITY_LINK_' + label + '_' + error
        assert reason in result['rows'][0]['reasons']
        assert reason in result['security_link_diagnostics'][0]['reasons']
        assert group(result)['membership_status'] == 'UNKNOWN'
        assert metric['n_valid'] is metric['n_members'] is None
        assert all(row['rank'] is None for row in metric['rows'])
    else:
        assert group(result)['membership_status'] == 'CONFIRMED'
        assert metric['n_valid'] == metric['n_members'] == 10


@pytest.mark.parametrize('field,label', [('recorded_at', 'RECORD'), ('acquired_at', 'EVIDENCE')])
@pytest.mark.parametrize('value,error', TIME_CASES)
def test_macro_link_time_boundary_preserves_unknown_for_same_day_date_only(field, label, value, error):
    view, _, _ = fixture(1)
    link = source_link()
    if value is None:
        del link[field]
    else:
        link[field] = value
    result = macro_projection(view, [link])
    mapping = result['rows'][0]['statistic_mapping']
    if error:
        reason = 'MACRO_LINK_' + label + '_' + error
        assert mapping['status'] == 'UNKNOWN' and mapping['source_links'] == []
        assert reason in mapping['reasons']
        assert reason in result['source_link_diagnostics'][0]['reasons']
    else:
        assert mapping['status'] == 'LINKED' and mapping['source_links'] == [link]
    assert result['probabilities'] is result['sector_returns'] is None


def test_future_security_link_does_not_shadow_previously_available_link():
    view, measures, links = fixture()
    expected = technical_groups(view, measures, links, price_basis='RAW')
    future = deepcopy(links[0])
    future['recorded_at'] = '2017-01-07T00:00:00Z'
    result = technical_groups(view, measures, [future] + links, price_basis='RAW')
    assert result['groups'] == expected['groups']
    assert result['rows'] == expected['rows']
    assert result['security_link_diagnostics'][0]['reasons'] == ['SECURITY_LINK_RECORD_NOT_AVAILABLE']


def test_future_macro_link_does_not_shadow_previously_available_link():
    view, _, _ = fixture(1)
    link = source_link()
    future = deepcopy(link)
    future['acquired_at'] = '2017-01-07T00:00:00Z'
    result = macro_projection(view, [future, link])
    assert result['rows'][0]['statistic_mapping'] == dict(status='LINKED', source_links=[link], reasons=[])
    assert result['source_link_diagnostics'][0]['reasons'] == ['MACRO_LINK_EVIDENCE_NOT_AVAILABLE']


@pytest.mark.parametrize('field', ['dictionary_version', 'mapping_version'])
@pytest.mark.parametrize('value', ['SYNTHETIC/1', None])
def test_projection_version_mismatch_rejected(field, value):
    view, measures, links = fixture()
    if value is None:
        del view[field]
    else:
        view[field] = value
    with pytest.raises(ValueError, match='COMMON_VIEW_VERSION_MISMATCH'):
        technical_groups(view, measures, links, price_basis='RAW')
    with pytest.raises(ValueError, match='COMMON_VIEW_VERSION_MISMATCH'):
        macro_projection(view)


def test_technical_input_hash_is_order_independent_and_rows_keep_record_links():
    view, measures, links = fixture()
    result = technical_groups(view, measures, links, price_basis='RAW')
    reversed_result = technical_groups(view, list(reversed(measures)), list(reversed(links)), price_basis='RAW')
    assert result['input_hash'] == result['cache_key'] == reversed_result['input_hash'] == reversed_result['cache_key']
    assert result['settings_version'] == group(result)['board']['settings_version']
    expected = {row['company_id']: row['record_id'] for row in view['rows']}
    assert {row['company_id']: row['classification_record_id'] for row in result['rows']} == expected
    assert {row['company_id']: row['classification_record_id'] for row in macro_projection(view)['rows']} == expected


@pytest.mark.parametrize('changed', ['security', 'measurement', 'basis', 'classification'])
def test_technical_input_hash_changes_with_each_numerical_input(changed):
    view, measures, links = fixture()
    original = technical_groups(view, measures, links, price_basis='RAW')['input_hash']
    basis = 'RAW'
    if changed == 'security':
        measures[0]['security_id'] = links[0]['security_id'] = 'SYNTHETIC:SECURITY:REPLACEMENT'
    elif changed == 'measurement':
        measures[0]['metrics']['momentum_3m']['value'] = '11'
    elif changed == 'basis':
        basis = 'SPLIT_ADJUSTED'
        for measure in measures:
            measure['price_basis'] = basis
    else:
        view['classification_hash'] = 'b' * 64
    result = technical_groups(view, measures, links, price_basis=basis)
    assert result['input_hash'] != original
    assert result['cache_key'] == result['input_hash']


def test_technical_input_hash_ignores_display_tags():
    view, measures, links = fixture()
    original = technical_groups(view, measures, links, price_basis='RAW')
    for row in view['rows']:
        row['tags'] = dict(lynch=['FAST_GROWER'], note='SYNTHETIC DISPLAY ONLY')
    result = technical_groups(view, measures, links, price_basis='RAW')
    assert result['input_hash'] == original['input_hash']
    assert result['groups'] == original['groups']
