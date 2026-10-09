"""Explicit, offline SEC M1 -> unchanged v1 Q/G research candidates.

Receipt custody and original-cutoff replay are admission checks, not source
truth or historical first-publication proof. This export has no producer,
provider, registry, price, or publication integration.
"""
from __future__ import annotations

from dataclasses import MISSING, dataclass, fields, replace
from datetime import datetime, timezone
import math
from pathlib import Path
import re
from types import SimpleNamespace

from ..contracts.enums import ProfileKind
from ..contracts.raw import RawFundamentals
from ..ingestion import sec_m1
from ..markets.us import US_LISTINGS
from ..producers.adapters import leaderboard_section, qgv_section
from ..producers.serialization import canonical_bytes, canonical_sha256, to_jsonable
from ..versions import IMPLEMENTATION_KIND, IMPLEMENTATION_LINE, QGV_ANALYSIS_CONTRACT, QGV_STANDARD, QGV_SYSTEM_LINE
from .analysis import AnalysisEngine
from .factors import G_WEIGHTS, Q_WEIGHTS, V_INITIAL_PRIOR
from .g_horizon import GHorizonConfig, assess_horizon
from .leaderboard import LeaderboardEngine
from .raw_map import map_raw
from .scoring_standard import SCORING_CALIBRATION, SCORING_STANDARD_STATUS, SCORING_STANDARD_VERSION

FINANCIAL_FIELDS = ('revenue', 'revenue_prev', 'ebit', 'ebit_prev', 'fcf', 'net_income', 'equity',
                    'invested_capital', 'cash', 'total_debt', 'shares', 'eps', 'eps_prev')
_METADATA_FIELDS = ('profile_kind', 'period_quality', 'reporting_currency')
_METHOD = {
    'mapper': 'investment_system.qgv.raw_map.map_raw', 'analysis': 'investment_system.qgv.analysis.AnalysisEngine',
    'leaderboard': 'investment_system.qgv.leaderboard.LeaderboardEngine',
    'standard': SCORING_STANDARD_VERSION, 'calibration': SCORING_CALIBRATION,
    'standard_status': SCORING_STANDARD_STATUS, 'Q_weights': Q_WEIGHTS, 'G_weights': G_WEIGHTS,
    'V_initial_prior': V_INITIAL_PRIOR, 'implementation_line': IMPLEMENTATION_LINE,
    'implementation_kind': IMPLEMENTATION_KIND, 'analysis_contract': QGV_ANALYSIS_CONTRACT,
    'system_line': QGV_SYSTEM_LINE, 'legacy_standard': QGV_STANDARD,
}
_METHOD_HASH = canonical_sha256(_METHOD)
_DEPENDENCIES = {
    'competitive_advantage': (), 'roic_wacc': ('net_income', 'invested_capital'), 'market_position': (),
    'fcf_quality': ('fcf', 'revenue'), 'margin_quality': ('ebit', 'revenue'),
    'financial_health': ('cash', 'total_debt', 'revenue'), 'management_quality': (),
    'next_3_5y_growth': ('revenue', 'revenue_prev'), 'growth_efficiency': ('revenue', 'revenue_prev', 'invested_capital'),
    'revenue_growth': ('revenue', 'revenue_prev'), 'eps_fcf_per_share_growth': ('eps', 'eps_prev', 'fcf', 'revenue_prev'),
    'growth_durability': (), 'excess_growth_vs_industry': ('revenue', 'revenue_prev'),
    'fundamental_value': ('eps',), 'reverse_dcf': ('revenue', 'revenue_prev', 'eps'), 'margin_of_safety': ('eps',),
    'peer_relative_value': (), 'historical_valuation': (), 'sector_context': (), 'theme_premium_discount': (),
}
_V_REASONS = {
    'fundamental_value': 'MISSING_PRICE_AND_VALUATION_INPUTS', 'margin_of_safety': 'MISSING_PRICE_AND_VALUATION_INPUTS',
    'reverse_dcf': 'MISSING_PRICE_OR_INDEPENDENT_IMPLIED_GROWTH_INPUT',
    'peer_relative_value': 'MISSING_PEER_VALUATION_SOURCE', 'historical_valuation': 'MISSING_VALUATION_HISTORY_SOURCE',
    'sector_context': 'MISSING_SECTOR_CONTEXT_SOURCE', 'theme_premium_discount': 'MISSING_THEME_CONTEXT_SOURCE',
}
# The supported converter concepts are admission metadata only. No extraction or
# arithmetic is implemented here. Related aliases share a current-period bound.
_CONSUMED_FACTS = {
    ('us-gaap', 'Revenues', 'USD'): 'revenue',
    **{('us-gaap', 'RevenueFromContractWithCustomerExcludingAssessedTax', u): 'revenue' for u in ('USD', 'EUR')},
    **{('ifrs-full', 'Revenue', u): 'revenue' for u in ('USD', 'EUR')},
    **{('us-gaap', c, u): group for c, group in (
        ('OperatingIncomeLoss', 'ebit'), ('NetIncomeLoss', 'net_income'),
        ('FreeCashFlow', 'fcf'), ('NetCashProvidedByUsedInOperatingActivities', 'cfo'),
        ('PaymentsToAcquirePropertyPlantAndEquipment', 'capex'),
        ('CashAndCashEquivalentsAtCarryingValue', 'cash'), ('LongTermDebt', 'total_debt'),
        ('LongTermDebtNoncurrent', 'total_debt'), ('StockholdersEquity', 'equity'),
        ('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 'equity'),
    ) for u in ('USD', 'EUR')},
    **{('ifrs-full', 'ProfitLoss', u): 'net_income' for u in ('USD', 'EUR')},
    **{('us-gaap', 'CommonStockSharesOutstanding', u): 'shares' for u in ('shares', 'Shares')},
    **{('us-gaap', c, u): 'eps' for c in ('EarningsPerShareDiluted', 'EarningsPerShareBasic')
       for u in ('USD/shares', 'EUR/shares')},
    ('us-gaap', 'EarningsPerShareDiluted', 'USD-per-shares'): 'eps',
    ('us-gaap', 'EarningsPerShareDiluted', 'pure'): 'eps',
}
_AMBIGUITIES = {'AMBIGUOUS_FACT_VALUES', 'AMBIGUOUS_REVISION_ORDER', 'AMBIGUOUS_FILING'}


class SecM2Error(ValueError):
    """A fixed, printable code, never an untrusted path/payload/exception."""


@dataclass(frozen=True)
class _ObservationalStamp:
    data_stamp_id: str
    synthetic: bool


class _RawMappingView(SimpleNamespace):
    """Structural map_raw input, deliberately not a legacy PIT DataStamp."""


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SecM2Error('INVALID_CLOCK')
    return value.astimezone(timezone.utc)


def _source_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise SecM2Error('INVALID_SOURCE_METADATA')
    return _utc(datetime.fromisoformat(value.replace('Z', '+00:00')))


def _mapping_view(company_id: str, normalized: dict, synthetic: bool) -> _RawMappingView:
    values = {f.name: f.default for f in fields(RawFundamentals) if f.default is not MISSING}
    for name in FINANCIAL_FIELDS:
        value = normalized.get(name)
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
            raise SecM2Error('INVALID_NORMALIZED_VALUE')
        values[name] = value
    for name in _METADATA_FIELDS:
        value = normalized.get(name, values[name])
        if not isinstance(value, str):
            raise SecM2Error('INVALID_NORMALIZED_METADATA')
        values[name] = value
    stamp_id = normalized['stamp']['data_stamp_id']
    if not isinstance(stamp_id, str) or not stamp_id:
        raise SecM2Error('INVALID_SOURCE_METADATA')
    values.update(company_id=company_id, stamp=_ObservationalStamp(stamp_id, synthetic), source_kind='OBSERVED_RAW_INPUT')
    return _RawMappingView(**values)


def _current_ambiguity(replayed: dict) -> bool:
    """Withhold unresolved current/newer conflicts; let M1's later winners resolve.

    Use the supporting pool, not a claim of exact field extraction. Older economic
    periods do not replace a conflicted current period; clearly later revisions
    selected by M1 can resolve earlier same-period contradictory rows.
    """
    selected = replayed['selected_input_facts']
    for conflict in replayed['revision_candidates']:
        reasons = set(conflict['exclusion_reasons']) & _AMBIGUITIES
        group = _CONSUMED_FACTS.get(tuple(conflict[k] for k in ('taxonomy', 'concept', 'unit')))
        if not reasons or group is None:
            continue
        # An otherwise unavailable filing at this cutoff cannot affect today's
        # admitted pool. Ambiguous filing candidates have no unique available_at.
        if any(r in conflict['exclusion_reasons'] for r in ('NOT_AVAILABLE_AT_AS_OF', 'UNSUPPORTED_FORM',
                                                          'ACCEPTANCE_AFTER_ACQUISITION', 'FILING_AFTER_ACQUISITION')):
            continue
        end = conflict.get('end')
        if not isinstance(end, str):
            continue
        relevant = [r for r in selected
                    if _CONSUMED_FACTS.get(tuple(r[k] for k in ('taxonomy', 'concept', 'unit'))) == group]
        if relevant and end < max(r['end'] for r in relevant):
            continue
        identity = ('taxonomy', 'concept', 'unit', 'start', 'end')
        resolvers = [r for r in relevant if all(r[k] == conflict[k] for k in identity)]
        resolved = any(r['filed'] > conflict['filed'] or (
            r['filed'] == conflict['filed'] and r['accepted_at'] is not None and conflict['accepted_at'] is not None
            and r['accepted_at'] > conflict['accepted_at']) for r in resolvers)
        if not resolved:
            return True
    return False


def _source(receipt: dict, replayed: dict | None = None) -> dict:
    original = receipt['input']
    normalized = original.get('raw_fundamentals')
    stamp = normalized['stamp'] if normalized is not None else None
    current = original if replayed is None else replayed
    requested_raw = None if replayed is None else replayed.get('raw_fundamentals')
    return {
        'receipt_id': receipt['receipt_id'], 'receipt_sha256': receipt['receipt_sha256'],
        'inputs': receipt['inputs'], 'acquired_at': original['acquired_at'], 'stored_as_of': original['as_of'],
        'original_availability': original['availability'], 'original_stamp': stamp,
        'requested_stamp': None if requested_raw is None else requested_raw['stamp'],
        'requested_availability': None if replayed is None else replayed['availability'],
        'source_freshness': None if stamp is None else stamp['freshness_status'],
        'freshness_classification': 'NOT_APPLICABLE',
        'selected_input_facts': current['selected_input_facts'], 'filings': current['filings'],
        'revision_candidates': current['revision_candidates'], 'excluded': current['excluded'],
        'original_selected_input_facts': original['selected_input_facts'],
        'revision_parent_receipt_id': receipt.get('revision_parent_receipt_id'), 'changes': receipt.get('changes', []),
        'full_pit_historical': False, 'real_data_verified': False, 'publication_approved': False,
    }


def _factor_records(observations: dict, raw: _RawMappingView, source: dict) -> dict:
    out = {}
    for fid in sorted(observations):
        observation = observations[fid]
        group = 'Q' if fid in Q_WEIGHTS else 'G' if fid in G_WEIGHTS else 'V'
        names = _DEPENDENCIES[fid]
        if fid == 'eps_fcf_per_share_growth':
            # Mirror the mapper's exact branch selection, including its legacy
            # FCF/current-to-previous-revenue fallback (not per-share FCF).
            names = ('eps', 'eps_prev') if raw.eps is not None and raw.eps_prev not in (None, 0) else ('fcf', 'revenue_prev')
        calculated = observation.score_0_100 is not None
        reasons = [] if calculated else [_V_REASONS.get(fid, 'MISSING_SEC_FINANCIAL_OR_UNSUPPLIED_CONTEXT_INPUTS')]
        out[fid] = {
            'factor_id': fid, 'group': group, 'weight': {**Q_WEIGHTS, **G_WEIGHTS, **V_INITIAL_PRIOR}[fid],
            'status': 'CALCULATED' if calculated else 'NOT_AVAILABLE', 'reason_codes': reasons,
            'observation': to_jsonable(observation),
            'financial_dependencies': list(names), 'used_normalized_fields': {k: getattr(raw, k) for k in names},
            'source_trace_basis': 'SUPPORTING_SELECTED_FACT_POOL_NOT_EXACT_FIELD_EXTRACTION',
            'source_references': {'receipt_id': source['receipt_id'], 'receipt_sha256': source['receipt_sha256'],
                'inputs': source['inputs'], 'source_stamp_id': raw.stamp.data_stamp_id,
                'source_stamp': source['requested_stamp'],
                'selected_input_facts': source['selected_input_facts']},
            'source_freshness': source['source_freshness'],
        }
    return out


def analyze_receipts(store_root: Path | str, receipt_ids: list[str] | tuple[str, ...], as_of: datetime,
                     *, evaluated_at: datetime, synthetic_inputs: bool) -> dict:
    """Analyze 1–17 explicitly supplied M1 receipts without latest/network fallback.

    Invalid request shape/clocks and duplicate validated issuers raise fixed-code
    SecM2Error. Individual custody/admission failures remain unavailable records.
    The evaluation clock is execution metadata, never publication or ID evidence.
    """
    if (not isinstance(receipt_ids, (list, tuple)) or not 1 <= len(receipt_ids) <= 17
            or any(not isinstance(rid, str) or not re.fullmatch('[0-9a-f]{64}', rid) for rid in receipt_ids)
            or len(set(receipt_ids)) != len(receipt_ids)):
        raise SecM2Error('INVALID_RECEIPT_REQUEST')
    if type(synthetic_inputs) is not bool:
        raise SecM2Error('INVALID_INPUT_KIND')
    as_of, evaluated_at = _utc(as_of), _utc(evaluated_at)
    if as_of > evaluated_at:
        raise SecM2Error('INVALID_CLOCK')
    root = Path(store_root)
    # RawDatasetStore creates these folders in its constructor, even on reads.
    # Check them first so this additive reader never creates source storage.
    if not all(p.is_dir() for p in (root, root / 'm1' / 'receipts', root / 'blobs', root / 'manifests', root / 'history')):
        raise SecM2Error('STORE_NOT_AVAILABLE')
    input_kind = 'SYNTHETIC' if synthetic_inputs else 'OBSERVED_UNVERIFIED'
    loaded, records, seen = {}, [], set()
    for rid in sorted(receipt_ids):
        try:
            receipt = sec_m1.load_receipt(root, rid)
        except (OSError, ValueError, TypeError, KeyError):
            records.append({'receipt_id': rid, 'company_id': None, 'status': 'NOT_AVAILABLE',
                            'reason_codes': ['RECEIPT_INTEGRITY_FAILURE']})
            continue
        company_id = receipt['input']['company_id']
        if company_id in seen:
            raise SecM2Error('DUPLICATE_ISSUER')
        seen.add(company_id)
        loaded[rid] = receipt
    companies, usable, unavailable = {}, [], []
    for rid, receipt in loaded.items():
        original, company_id = receipt['input'], receipt['input']['company_id']
        row = {'receipt_id': rid, 'company_id': company_id, 'ticker': US_LISTINGS[company_id]['yahoo'],
               'status': 'NOT_AVAILABLE', 'reason_codes': [], 'score_basis': 'LEGACY_QG_ONLY',
               'candidate_only': True, 'prices_used': False, 'publication_approved': False}
        try:
            original_replay = sec_m1.replay_receipt(root, rid, _source_time(original['as_of']))
            if canonical_bytes(original_replay) != canonical_bytes(original):
                raise SecM2Error('ORIGINAL_REPLAY_MISMATCH')
            row['source'] = _source(receipt)
            if original['form_filter'] != '10-K':
                raise SecM2Error('ANNUAL_FORM_REQUIRED')
            if _source_time(original['acquired_at']) > as_of:
                raise SecM2Error('ACQUISITION_AFTER_CUTOFF')
            replayed = sec_m1.replay_receipt(root, rid, as_of)
            row['source'] = _source(receipt, replayed)
            if replayed['status'] != 'READY':
                raise SecM2Error('M1_NOT_AVAILABLE')
            if _source_time(replayed['availability']['available_at']) > as_of:
                raise SecM2Error('AVAILABILITY_AFTER_CUTOFF')
            if _current_ambiguity(replayed):
                raise SecM2Error('UNRESOLVED_CURRENT_FACT_AMBIGUITY')
            raw = _mapping_view(company_id, replayed['raw_fundamentals'], synthetic_inputs)
            observations = map_raw(raw)
            row['normalized_financial_fields'] = {k: getattr(raw, k) for k in FINANCIAL_FIELDS}
            row['financial_metadata'] = {k: getattr(raw, k) for k in _METADATA_FIELDS}
            row['factors'] = _factor_records(observations, raw, row['source'])
            horizon = to_jsonable(assess_horizon(GHorizonConfig(), available_quarters=0))
            native = AnalysisEngine().analyze(company_id, as_of, observations,
                profile_kind=ProfileKind(raw.profile_kind), data_stamp_refs=(raw.stamp.data_stamp_id,),
                synthetic=synthetic_inputs, g_horizon=horizon)
            identity = {'receipt_id': rid, 'receipt_sha256': receipt['receipt_sha256'],
                        'as_of': as_of.isoformat(), 'input_kind': input_kind, 'method_sha256': _METHOD_HASH}
            native = replace(native, qgv_snapshot_id='sec_m2_qgv_' + canonical_sha256(identity))
            row['snapshot_id'] = native.qgv_snapshot_id
            row['coverage'] = {
                'Q_observed_weight': sum(w for fid, w in Q_WEIGHTS.items() if observations[fid].score_0_100 is not None),
                'G_observed_weight': sum(w for fid, w in G_WEIGHTS.items() if observations[fid].score_0_100 is not None),
                'V_observed_weight': sum(w for fid, w in V_INITIAL_PRIOR.items() if observations[fid].score_0_100 is not None),
                'native_coverage': native.coverage_state.value, 'weights_renormalized': False,
            }
            row['confidence_basis'] = 'UNCHANGED_NATIVE_DEFAULT_NOT_MEASURED'
            if native.Q_score is None or native.G_score is None:
                unavailable.append(native)
                raise SecM2Error('INCOMPLETE_QG')
            row['status'] = 'CALCULATED'
            usable.append(native)
        except SecM2Error as exc:
            row['reason_codes'] = [str(exc)]
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            row['reason_codes'] = ['REPLAY_OR_NORMALIZED_INPUT_FAILURE']
        companies[company_id] = row
        if row['status'] != 'CALCULATED':
            records.append(row)
    companies = dict(sorted(companies.items()))
    usable.sort(key=lambda snapshot: snapshot.company_id)
    candidate_identity = {'receipts': [{'receipt_id': rid, 'receipt_sha256': loaded[rid]['receipt_sha256']}
                           for rid in sorted(loaded)], 'requested_receipt_ids': sorted(receipt_ids),
                           'as_of': as_of.isoformat(), 'input_kind': input_kind, 'method_sha256': _METHOD_HASH}
    candidate_hash = canonical_sha256(candidate_identity)
    leaderboard = LeaderboardEngine().build('SEC_M2_EXPLICIT_SUBSET', as_of, usable)
    leaderboard = replace(leaderboard, leaderboard_snapshot_id='sec_m2_lb_' + candidate_hash)
    qscope, qdata, qsynthetic = qgv_section(usable)
    lscope, ldata, lsynthetic = leaderboard_section(leaderboard)
    result = {
        'contract': 'OFFLINE_SEC_QG_CANDIDATE', 'version': 1, 'schema_version': 1,
        'candidate_id': 'sec_m2_' + candidate_hash, 'as_of': as_of.isoformat(), 'evaluated_at': evaluated_at.isoformat(),
        'input_kind': input_kind, 'synthetic_inputs': synthetic_inputs, 'candidate_only': True, 'prices_used': False,
        'publication_approved': False, 'publication_eligible': False, 'real_data_verified': False, 'full_pit_historical': False,
        'research_state': {'status': 'PROVISIONAL_RESEARCH', 'candidate_only': True},
        'publication': {'status': 'NOT_RUN', 'grant': 'NONE'},
        'methodology': {'status': 'PROVISIONAL_RESEARCH', 'existing_method': _METHOD, 'method_sha256': _METHOD_HASH},
        'scope': {'basis': 'EXPLICIT_RECEIPTS_US17_SUBSET', 'requested_receipt_ids': sorted(receipt_ids),
                  'company_ids': list(companies), 'public_500_rank': False},
        'companies': companies, 'failures': sorted(records, key=lambda r: r['receipt_id']),
        'unavailable_snapshots': qgv_section(unavailable)[1],
        'candidate_data': {
            'qgv': {'scope': qscope, 'data': qdata, 'adapter_synthetic': qsynthetic, 'candidate_only': True,
                    'score_basis': 'LEGACY_QG_ONLY', 'complete_qgv_available': False},
            'leaderboard': {'scope': lscope, 'data': ldata, 'adapter_synthetic': lsynthetic,
                'synthetic_inputs': synthetic_inputs, 'preview_only': True, 'candidate_only': True,
                'rank_basis': 'EXPLICIT_SUBSET_LEGACY_QG_ONLY_CANDIDATE', 'qgv_ranking_validated': False,
                'freshness_basis': 'NATIVE_ROW_SYNTHETIC_OR_COVERAGE_NOT_SOURCE_FRESHNESS'},
        },
        'n_calculated': len(usable), 'n_unavailable': len(receipt_ids) - len(usable),
        'limitations': ['FIRST_PUBLICATION_UNKNOWN', 'SUPPORTING_FACT_POOL_NOT_EXACT_FIELD_EXTRACTION',
            'ANNUAL_ONLY_ZERO_QUARTERLY_OBSERVATIONS', 'LAST_PERIOD_GROWTH_PROXY_NOT_FORECAST',
            'UNCHANGED_LEGACY_EPS_OR_FCF_PREVIOUS_REVENUE_FALLBACK', 'FIXED_WEIGHTS_MISSING_NOT_RENORMALIZED',
            'NORMALIZED_FIELDS_MAY_DIFFER_IN_PERIOD_OR_CURRENCY', 'PREVIOUS_PERIOD_NOT_PROVEN_CONSECUTIVE',
            'NORMALIZED_DEBT_IS_LONG_TERM_DEBT', 'INVESTED_CAPITAL_USES_EXISTING_EQUITY_FALLBACK',
            'SOURCE_FRESHNESS_NOT_REMEASURED', 'UNCALIBRATED_PARTIAL_QG_NATIVE_SUBSET_PREVIEW'],
    }
    return to_jsonable(result)
