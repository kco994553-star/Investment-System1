#!/usr/bin/env python3
"""Synthetic SEC companyfacts generator + JS parity vectors for the public `sec-qgv2.json` validator.

`synthetic_sec(...)` builds deterministic companyfacts/submissions bytes for tests (synthetic CIKs and
values only; never live data). `build()` produces tests/fixtures/sec_qgv2_vectors_v1.json: a full
payload (Universe rows built from synthetic bytes, scores computed by the Python publisher) plus
mutation cases, each with the verdict of Python `require_qgv2`. tools/sec_qgv2_node_test.js replays
every case through JS `SecQgv2.validate` and must reach the same verdict. `--write` regenerates the
fixture; without it the fixture is checked.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/sec_qgv2_vectors_v1.json'
AS_OF = datetime(2026, 10, 13, 22, 30, tzinfo=timezone.utc)
DELETE = {'$delete': True}


def _fact(rows, concept, unit, value, *, start=None, end, form, filed, accn, taxonomy='us-gaap'):
    row = {'end': end, 'val': value, 'accn': accn, 'form': form, 'filed': filed, 'fy': int(filed[:4]), 'fp': 'FY'}
    if start is not None:
        row['start'] = start
    rows.setdefault(taxonomy, {}).setdefault(concept, {'units': {}})['units'].setdefault(unit, []).append(row)


def synthetic_sec(cik, *, sic='3674', seed=0, years=7, last_fy=2025, revenue0=1000.0, growth=0.10, gross_margin=0.5,
                  ebit_margin=0.2, tax_rate=0.2, ocf_to_ni=1.2, capex_to_revenue=0.05, da_to_revenue=0.04,
                  interest_to_revenue=0.01, assets_to_revenue=1.5, equity_to_assets=0.5, debt_to_assets=0.2,
                  cash_to_assets=0.1, shares0=100.0, share_growth=0.01, quarters=True, financial=False,
                  omit=(), ticker='SYN', exchange='Nasdaq'):
    """Deterministic multi-year companyfacts (10-K annual flows/instants + 10-Q YTD) and submissions bytes."""
    facts = {}
    wobble = lambda y: 1.0 + 0.02 * (((seed * 7 + y * 3) % 5) - 2)  # deterministic +-4% per year
    def put(concept, unit, value, **kw):
        if concept not in omit:
            _fact(facts, concept, unit, value, **kw)
    first = last_fy - years + 1
    for year in range(first, last_fy + 1):
        k = last_fy - year
        rev = round(revenue0 * (1 + growth) ** (-k) * wobble(year), 2)
        ebit = round(rev * ebit_margin * wobble(year + 1), 2)
        pretax = round(ebit - rev * interest_to_revenue, 2)
        tax = round(pretax * tax_rate, 2)
        ni = round(pretax - tax, 2)
        shares = round(shares0 * (1 + share_growth) ** (-k), 3)
        start, end = f'{year}-01-01', f'{year}-12-31'
        filed, accn = f'{year + 1}-02-15', f'{cik}-{(year + 1) % 100:02d}-000010'
        kw = dict(start=start, end=end, form='10-K', filed=filed, accn=accn)
        put('Revenues', 'USD', rev, **kw)
        put('GrossProfit', 'USD', round(rev * gross_margin, 2), **kw)
        put('OperatingIncomeLoss', 'USD', ebit, **kw)
        put('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest', 'USD', pretax, **kw)
        put('IncomeTaxExpenseBenefit', 'USD', tax, **kw)
        put('NetIncomeLoss', 'USD', ni, **kw)
        put('NetCashProvidedByUsedInOperatingActivities', 'USD', round(ni * ocf_to_ni, 2), **kw)
        put('PaymentsToAcquirePropertyPlantAndEquipment', 'USD', round(rev * capex_to_revenue, 2), **kw)
        put('DepreciationDepletionAndAmortization', 'USD', round(rev * da_to_revenue, 2), **kw)
        put('InterestExpense', 'USD', round(rev * interest_to_revenue, 2), **kw)
        put('EarningsPerShareDiluted', 'USD/shares', round(ni / shares, 4), **kw)
        put('WeightedAverageNumberOfDilutedSharesOutstanding', 'shares', shares, **kw)
        if financial:
            put('InterestIncomeExpenseNet', 'USD', round(rev * 0.6, 2), **kw)
        assets = round(rev * assets_to_revenue, 2)
        ikw = dict(end=end, form='10-K', filed=filed, accn=accn)
        put('Assets', 'USD', assets, **ikw)
        put('StockholdersEquity', 'USD', round(assets * equity_to_assets, 2), **ikw)
        put('LongTermDebtNoncurrent', 'USD', round(assets * debt_to_assets, 2), **ikw)
        put('CashAndCashEquivalentsAtCarryingValue', 'USD', round(assets * cash_to_assets, 2), **ikw)
    if quarters:
        # Half-year YTD 10-Q facts for last_fy+1 (current) with last_fy and last_fy-1 comparatives.
        for year in (last_fy + 1, last_fy, last_fy - 1):
            k = last_fy - year
            rev = round(revenue0 * (1 + growth) ** (-k) * wobble(year) / 2, 2)
            ni = round(rev * ebit_margin * 0.7, 2)
            filed, accn = f'{year}-08-01', f'{cik}-{year % 100:02d}-000020'
            kw = dict(start=f'{year}-01-01', end=f'{year}-06-30', form='10-Q', filed=filed, accn=accn)
            put('Revenues', 'USD', rev, **kw)
            put('OperatingIncomeLoss', 'USD', round(rev * ebit_margin, 2), **kw)
            put('NetCashProvidedByUsedInOperatingActivities', 'USD', round(ni * ocf_to_ni, 2), **kw)
            put('PaymentsToAcquirePropertyPlantAndEquipment', 'USD', round(rev * capex_to_revenue, 2), **kw)
            put('WeightedAverageNumberOfDilutedSharesOutstanding', 'shares', round(shares0 * (1 + share_growth) ** (-k + 0.5), 3),
                start=f'{year}-04-01', end=f'{year}-06-30', form='10-Q', filed=filed, accn=accn)
            put('CashAndCashEquivalentsAtCarryingValue', 'USD', round(rev * assets_to_revenue * cash_to_assets * 2, 2),
                end=f'{year}-06-30', form='10-Q', filed=filed, accn=accn)
            put('LongTermDebtNoncurrent', 'USD', round(rev * assets_to_revenue * debt_to_assets * 2, 2),
                end=f'{year}-06-30', form='10-Q', filed=filed, accn=accn)
    facts['us-gaap'].setdefault('StockPrice', {'units': {'USD': [{'val': 987654321, 'end': '2026-06-30'}]}})
    payload = {'cik': int(cik), 'entityName': 'Synthetic', 'facts': facts}
    subs = {'cik': int(cik), 'sic': sic, 'tickers': [ticker], 'exchanges': [exchange],
            'filings': {'recent': {'accessionNumber': [], 'form': [], 'filingDate': [], 'reportDate': [],
                                   'acceptanceDateTime': [], 'primaryDocument': []}}}
    return json.dumps(payload).encode(), json.dumps(subs).encode()


# A small deterministic synthetic universe: enough GENERAL issuers in one SIC group for INDUSTRY_GROUP peers,
# a smaller group (UNIVERSE_FALLBACK), and FINANCIAL issuers ranked among themselves.
def universe_spec():
    from investment_system.universe.sec_universe_shares import universe_codes
    codes = list(universe_codes())
    spec = []
    for n in range(27):
        sic = '3674' if n < 10 else '7372' if n < 15 else '2834' if n < 18 else '6021'
        spec.append((codes[n], str(1000 + n).zfill(10), sic, n))
    return spec


def synthetic_universe_updates(acquired_at=AS_OF):
    from investment_system.universe import sec_qgv2 as q
    updates = {}
    for code, cik, sic, n in universe_spec():
        facts, subs = synthetic_sec(cik, sic=sic, seed=n, growth=0.02 + 0.01 * (n % 9), ebit_margin=0.08 + 0.015 * (n % 11),
                                    debt_to_assets=0.05 + 0.03 * (n % 7), share_growth=-0.02 + 0.006 * (n % 8),
                                    financial=sic == '6021', equity_to_assets=0.1 if sic == '6021' else 0.5)
        updates.update(q.build_issuer_records(codes=(code,), cik=cik, companyfacts_body=facts, submissions_body=subs,
                                              acquired_at=acquired_at))
    return updates


def synthetic_target_updates(acquired_at=AS_OF):
    from investment_system.universe import sec_qgv2 as q
    entries = []
    for n, company_id in enumerate(('nvda', 'msft', 'amd')):
        cik = q.target_cik(company_id)
        facts, subs = synthetic_sec(cik, sic='3674', seed=40 + n, growth=0.15 + 0.05 * n)
        entries.append((company_id, facts, subs, acquired_at))
    return q.build_target_rows(entries)


def base():
    from investment_system.universe import sec_qgv2 as q
    return q.merge(None, synthetic_universe_updates(), as_of=AS_OF, shard_index=3,
                   registry_sha256=sha256(b'registry').hexdigest(), unresolved={'BATS:CBOE'},
                   target_updates=synthetic_target_updates())


def _codes():
    return [c for c, *_ in universe_spec()]


def _diff_ops(old, new, path=()):
    """Leaf-level ops turning `old` into `new` (dicts compared key by key; anything else replaced whole)."""
    if isinstance(old, dict) and isinstance(new, dict):
        ops = []
        for key in sorted(set(old) | set(new)):
            if key not in new:
                ops.append((list(path) + [key], DELETE))
            elif key not in old:
                ops.append((list(path) + [key], new[key]))
            else:
                ops += _diff_ops(old[key], new[key], path + (key,))
        return ops
    return [] if old == new else [(list(path), new)]


OLD_CALC_VERSION = 'qgv2-calc/2026-10-14.1'


def mixed_version_ops():
    """Ops from the base file to a valid file where two Universe rows and one TARGET row are of another calc_version (one
    legacy, one older): the publisher keeps them out of the ranking population (CALC_VERSION_MISMATCH) and re-ranks the rest."""
    from investment_system.universe import sec_qgv2 as q
    from investment_system.universe.sec_universe_shares import load_config
    from datetime import timedelta
    before = expand(sparse(base()))
    after = json.loads(json.dumps(before))
    c = _codes()
    after['records'][c[2]]['calc_version'] = None
    after['records'][c[5]]['calc_version'] = OLD_CALC_VERSION
    after['target']['amd']['calc_version'] = None
    cfg = load_config()
    repub = q.publish(after['records'], after['target'], as_of=AS_OF, cfg=cfg, stale_after=timedelta(seconds=after['stale_after_seconds']),
                      shard_index=after['last_shard_index'], registry_sha256=after['registry_sha256'])
    return _diff_ops(before, json.loads(json.dumps(repub)))


def cases():
    from investment_system.universe.sec_universe_shares import universe_codes
    from investment_system.universe.sec_qgv2 import target_ids
    c = _codes()
    mixed = mixed_version_ops()
    legacy = [(['calc_version'], DELETE)] + [(['records', code, 'calc_version'], DELETE) for code in universe_codes()]
    legacy += [(['target', cid, 'calc_version'], DELETE) for cid in target_ids()]
    stale_scores = [op for op in mixed if op[0][:2] != ['records', c[5]] or op[0][2] not in ('factors', 'axes')]
    R, T = ['records'], ['target']
    first, second, fin, empty = c[0], c[1], c[21], universe_codes()[30]
    from investment_system.universe import sec_qgv2 as q
    withdrawn = dict(q.withdrawn_target('nvda', '2026-10-13T22:10:00Z'), withdrawn_acquired_at='2026-10-12T22:30:00Z')
    uw = dict(q.empty_record(reasons=(q.WITHDRAWN_REASON,)), detected_at='2026-10-13T22:10:00Z',
              withdrawn_acquired_at='2026-10-12T22:30:00Z', withdrawn_cik='0000000999')
    return [
        ('base_valid', []),
        ('null_shard_and_registry_valid', [(['last_shard_index'], None), (['registry_sha256'], None)]),
        ('top_price_key', [(['price'], 1)]),
        ('row_price_key', [(R + [first, 'price'], 1)]),
        ('v_inputs_market_cap_key', [(R + [first, 'v_inputs_v2', 'market_cap'], 1)]),
        ('factor_tampered', [(R + [first, 'factors', 'q_profitability'], 1.0)]),
        ('volatility_percentile_tampered', [(R + [first, 'metrics', 'revenue_volatility_5y_rank_pct'], 101.0)]),
        ('volatility_negative', [(R + [first, 'metrics', 'revenue_growth_std_5y'], -1.0)]),
        ('volatility_percentile_without_history', [(R + [empty, 'metrics', 'revenue_volatility_5y_rank_pct'], 70.0)]),
        ('factor_zero_filled', [(R + [first, 'factors', 'g_recent_acceleration'], 0)]),
        ('axis_score_tampered', [(R + [first, 'axes', 'Q', 'score'], 99.0)]),
        ('axis_peer_count_tampered', [(R + [first, 'axes', 'G', 'peer_count'], 3)]),
        ('axis_basis_tampered', [(R + [first, 'axes', 'Q', 'peer_basis'], 'UNIVERSE_FALLBACK')]),
        ('axis_fallbacks_tampered', [(R + [first, 'axes', 'Q', 'submetric_fallbacks'], 2)]),
        ('factors_available_tampered', [(R + [first, 'axes', 'Q', 'factors_available'], '4/5')]),
        ('metric_tampered_changes_scores', [(R + [first, 'metrics', 'roic'], 9.5)]),
        ('metric_string', [(R + [first, 'metrics', 'roic'], '0.1')]),
        ('metric_int_not_float', [(R + [first, 'metrics', 'roic'], 1)]),
        ('metric_outside_profile', [(R + [first, 'metrics', 'roe'], 0.1)]),
        ('metric_unknown_key', [(R + [first, 'metrics', 'v_score'], 0.1)]),
        ('moat_years_too_small', [(R + [first, 'metrics', 'moat_return_years'], 2)]),
        ('ebit_estimated_years_valid', [(R + [first, 'metrics', 'ebit_estimated_years'], 2),
                                        (R + [first, 'metrics', 'ebit_estimated_fiscal_years'], [2022, 2023])]),
        ('ebit_estimated_count_without_years', [(R + [first, 'metrics', 'ebit_estimated_years'], 2)]),
        ('ebit_estimated_years_without_count', [(R + [first, 'metrics', 'ebit_estimated_fiscal_years'], [2023])]),
        ('ebit_estimated_years_length_mismatch', [(R + [first, 'metrics', 'ebit_estimated_years'], 2),
                                                  (R + [first, 'metrics', 'ebit_estimated_fiscal_years'], [2023])]),
        ('ebit_estimated_years_unsorted', [(R + [first, 'metrics', 'ebit_estimated_years'], 2),
                                           (R + [first, 'metrics', 'ebit_estimated_fiscal_years'], [2023, 2022])]),
        ('ebit_estimated_years_after_fiscal_year', [(R + [first, 'metrics', 'ebit_estimated_years'], 1),
                                                    (R + [first, 'metrics', 'ebit_estimated_fiscal_years'], [2026])]),
        ('ebit_estimated_years_not_integers', [(R + [first, 'metrics', 'ebit_estimated_years'], 1),
                                               (R + [first, 'metrics', 'ebit_estimated_fiscal_years'], ['2023'])]),
        ('ebit_estimated_years_zero', [(R + [first, 'metrics', 'ebit_estimated_years'], 0),
                                       (R + [first, 'metrics', 'ebit_estimated_fiscal_years'], [])]),
        ('ebit_estimated_years_too_many', [(R + [first, 'metrics', 'ebit_estimated_years'], 7),
                                           (R + [first, 'metrics', 'ebit_estimated_fiscal_years'], list(range(2019, 2026)))]),
        ('ebit_estimated_years_not_integer', [(R + [first, 'metrics', 'ebit_estimated_years'], 1.5),
                                              (R + [first, 'metrics', 'ebit_estimated_fiscal_years'], [2023])]),
        ('ebit_estimated_years_on_financial', [(R + [fin, 'metrics', 'ebit_estimated_years'], 1),
                                               (R + [fin, 'metrics', 'ebit_estimated_fiscal_years'], [2023])]),
        ('roic_avg_3y_on_financial', [(R + [fin, 'metrics', 'roic_avg_3y'], 0.2)]),
        ('roic_avg_3y_string', [(R + [first, 'metrics', 'roic_avg_3y'], '0.2')]),
        ('operating_margin_std_negative', [(R + [first, 'metrics', 'operating_margin_std_5y_pp'], -0.5)]),
        ('operating_margin_std_too_large', [(R + [first, 'metrics', 'operating_margin_std_5y_pp'], 1e13)]),
        ('profile_mismatch', [(R + [fin, 'profile'], 'GENERAL')]),
        ('group_mismatch', [(R + [first, 'industry_group'], 'utilities')]),
        ('cross_section_size_tampered', [(['cross_section_size'], 99)]),
        ('cross_section_profile_tampered', [(['cross_section_by_profile', 'FINANCIAL'], 8)]),
        ('method_weight_changed', [(['method', 'weights', 'Q', 'q_profitability'], 30)]),
        ('method_min_peers_changed', [(['method', 'min_peers'], 5)]),
        ('method_bool_for_int', [(['method', 'min_peers'], True)]),
        ('standard_status_changed', [(['standard_status'], 'CALIBRATED')]),
        ('fresh_row_marked_stale', [(R + [first, 'state'], 'STALE'), (R + [first, 'reason_codes'], ['STALE_INPUT'])]),
        ('row_reason_unknown', [(R + [empty, 'reason_codes'], ['RANK'])]),
        ('not_available_row_with_metric', [(R + [empty, 'metrics', 'roic'], 0.1)]),
        ('record_removed', [(R + [second], DELETE)]),
        ('target_removed', [(T + ['hanmi'], DELETE)]),
        ('target_non_sec_with_cik', [(T + ['hanmi', 'cik'], '0000000001')]),
        ('target_cik_mismatch', [(T + ['nvda', 'cik'], '0000000001')]),
        ('target_axis_tampered', [(T + ['nvda', 'axes', 'G', 'score'], 1.0)]),
        ('v_inputs_negative_shares', [(R + [first, 'v_inputs_v2', 'diluted_shares', 'value'], -1)]),
        ('v_inputs_history_unsorted', [(R + [first, 'v_inputs_v2', 'ebit_per_share_history'],
                                        [{'fiscal_year_end': '2025-12-31', 'value': 1.0}, {'fiscal_year_end': '2024-12-31', 'value': 1.0}])]),
        ('v_inputs_flow_end_without_value', [(R + [first, 'v_inputs_v2', 'ebit', 'fy_value'], None)]),
        ('v_inputs_currency_mismatch', [(R + [first, 'v_inputs_v2', 'currency'], 'EUR')]),
        ('acquired_after_as_of', [(R + [first, 'acquired_at'], '2026-10-14T00:00:00Z')]),
        ('bad_hash', [(R + [first, 'source_sha256', 'companyfacts'], 'x')]),
        ('top_state_mismatch', [(['state'], 'STALE')]),
        ('code_count_changed', [(['code_count'], 503)]),
        ('kind_changed', [(['kind'], 'SEC_UNIVERSE_QG')]),
        ('calc_version_legacy_file_valid', legacy),
        ('calc_version_mixed_population_valid', mixed),
        ('calc_version_mismatch_row_still_ranked', stale_scores),
        ('calc_version_row_key_missing', [(R + [first, 'calc_version'], DELETE)]),
        ('calc_version_top_malformed', [(['calc_version'], 'v2')]),
        ('calc_version_row_malformed', [(R + [first, 'calc_version'], 'qgv2-calc/latest')]),
        ('calc_version_on_row_without_data', [(R + [empty, 'calc_version'], OLD_CALC_VERSION)]),
        # TARGET withdrawal (identity conflict, sec-public-inputs.json WITHDRAWN): TARGET section only, no values.
        ('target_withdrawn_valid', [(T + ['nvda'], withdrawn)]),
        ('target_withdrawn_without_observation_valid', [(T + ['asml'], dict(withdrawn, cik=q.target_cik('asml'),
                                                                            withdrawn_acquired_at=None))]),
        ('target_withdrawn_with_values', [(T + ['nvda', 'detected_at'], withdrawn['detected_at']),
                                          (T + ['nvda', 'withdrawn_acquired_at'], None)]),
        ('target_withdrawn_reason_without_keys', [(T + ['asml', 'reason_codes'], [q.WITHDRAWN_REASON])]),
        ('target_withdrawn_with_acquired_at', [(T + ['nvda'], dict(withdrawn, acquired_at=withdrawn['withdrawn_acquired_at']))]),
        ('target_withdrawn_other_reason', [(T + ['nvda'], dict(withdrawn, reason_codes=['NOT_COLLECTED']))]),
        ('target_withdrawn_cik_mismatch', [(T + ['nvda'], dict(withdrawn, cik=q.target_cik('msft')))]),
        ('target_withdrawn_without_cik', [(T + ['nvda'], dict(withdrawn, cik=None))]),
        ('target_withdrawn_non_sec_issuer', [(T + ['hanmi'], dict(withdrawn, cik=None))]),
        ('target_withdrawn_detected_after_as_of', [(T + ['nvda'], dict(withdrawn, detected_at='2026-10-14T00:00:00Z'))]),
        ('target_withdrawn_names_a_later_observation', [(T + ['nvda'], dict(withdrawn, withdrawn_acquired_at='2026-10-13T22:20:00Z'))]),
        ('target_withdrawn_detected_at_missing', [(T + ['nvda'], {k: v for k, v in withdrawn.items() if k != 'detected_at'})]),
        ('records_withdrawn_not_allowed', [(R + [empty], dict(withdrawn, cik=None))]),
        # Universe withdrawal (UNI-WITHDRAWN (a), records section): the empty row with the reason and the three keys only.
        ('universe_withdrawn_valid', [(R + [empty], uw)]),
        ('universe_withdrawn_with_cik', [(R + [empty], dict(uw, cik='0000000999'))]),
        ('universe_withdrawn_with_acquired_at', [(R + [empty, 'acquired_at'], uw['withdrawn_acquired_at'])]),
        ('universe_withdrawn_with_metric', [(R + [empty, 'metrics'], {'roic': 0.1})]),
        ('universe_withdrawn_other_reason', [(R + [empty], dict(uw, reason_codes=['CIK_UNRESOLVED']))]),
        ('universe_withdrawn_extra_reason', [(R + [empty], dict(uw, reason_codes=[q.WITHDRAWN_REASON, 'CIK_UNRESOLVED']))]),
        ('universe_withdrawn_reason_without_keys', [(R + [empty, 'reason_codes'], [q.WITHDRAWN_REASON])]),
        ('universe_withdrawn_without_named_observation', [(R + [empty], dict(uw, withdrawn_acquired_at=None))]),
        ('universe_withdrawn_names_a_later_observation', [(R + [empty], dict(uw, withdrawn_acquired_at='2026-10-13T22:20:00Z'))]),
        ('universe_withdrawn_detected_after_as_of', [(R + [empty], dict(uw, detected_at='2026-10-14T00:00:00Z'))]),
        ('universe_withdrawn_without_issuer', [(R + [empty], dict(uw, withdrawn_cik=None))]),
        ('universe_withdrawn_zero_issuer', [(R + [empty], dict(uw, withdrawn_cik='0000000000'))]),
        ('universe_withdrawn_issuer_key_missing', [(R + [empty], {k: v for k, v in uw.items() if k != 'withdrawn_cik'})]),
        ('universe_withdrawn_state_live', [(R + [empty], uw), (R + [empty, 'state'], 'LIVE')]),
        ('schema_v1_valid', [(['schema_version'], 1)]),
        ('universe_withdrawn_in_schema_v1_file', [(['schema_version'], 1), (R + [empty], uw)]),
        ('target_withdrawn_in_schema_v1_file_valid', [(['schema_version'], 1), (T + ['nvda'], withdrawn)]),
        ('schema_v3', [(['schema_version'], 3)]),
        ('universe_withdrawn_in_legacy_file', legacy + [(R + [empty], {k: v for k, v in uw.items() if k != 'calc_version'})]),
    ]


def apply(payload, ops):
    for path, value in ops:
        target = payload
        for key in path[:-1]:
            target = target[key]
        if value == DELETE:
            del target[path[-1]]
        else:
            target[path[-1]] = json.loads(json.dumps(value))
    return payload


def verdict(payload):
    from investment_system.universe.sec_qgv2 import require_qgv2
    try:
        require_qgv2(payload)
        return True
    except ValueError:
        return False


def sparse(payload):
    """Drop Universe rows equal to empty_record() (NOT_COLLECTED); expand() restores them in both languages."""
    from investment_system.universe.sec_qgv2 import empty_record
    out = json.loads(json.dumps(payload))
    out['records'] = {code: row for code, row in out['records'].items() if row != empty_record()}
    return out


def expand(payload):
    from investment_system.universe.sec_qgv2 import empty_record
    from investment_system.universe.sec_universe_shares import universe_codes
    out = json.loads(json.dumps(payload))
    out['records'] = {code: out['records'].get(code) or empty_record() for code in universe_codes()}
    return out


def build():
    payload = sparse(base())
    out_cases = [{'id': cid, 'ops': [{'path': path, 'value': value} for path, value in ops],
                  'valid': verdict(apply(expand(payload), ops))} for cid, ops in cases()]
    from investment_system.qgv import v2_factors as vf, v2_scoring as vs
    from investment_system.qgv.sic_industry import load_sic_config
    from investment_system.universe import sec_qgv2 as q
    constants = {'target_ciks': {cid: q.target_cik(cid) for cid in q.target_ids()},
                 'sic_groups': [[g['id'], g['sic_ranges']] for g in load_sic_config()['groups']],
                 'metric_keys': list(vf.METRIC_KEYS), 'factor_ids': list(vs.FACTOR_IDS), 'method': q.METHOD,
                 'extra_metrics': {k: list(v) for k, v in vf.EXTRA_METRIC_PROFILES.items()}, 'calc_version': vf.CALC_VERSION,
                 'submetrics': {p: {f: [list(x) for x in specs] for f, specs in by.items()} for p, by in vs.SUBMETRICS.items()}}
    return {'synthetic': True, 'delete_marker': DELETE, 'constants': constants, 'base': payload, 'cases': out_cases}


def main(argv):
    text = json.dumps(build(), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n'
    if '--write' in argv:
        FIXTURE.write_text(text)
        print('SEC_QGV2_VECTORS_WRITTEN')
        return 0
    ok = FIXTURE.exists() and FIXTURE.read_text() == text
    print('SEC_QGV2_VECTORS_OK' if ok else 'SEC_QGV2_VECTORS_STALE')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
