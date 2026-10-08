"""Finite inactive G1/G2 method-family comparison and diagnostic invariants.

Consumes exact approved semantics and frozen prior evidence, without rerunning
lineage tests, calculating candidate scores, changing production or using history.
"""
from pathlib import Path
from datetime import date, datetime, timezone
import argparse
import hashlib
import json

PRIOR_HASHES = {
    'G_METHOD_REPLAY_MANIFEST.json': '139757a9b5cfca3317aa009bb94e92f8af72034838ea0a88711d0b1fe505216f',
    'G_LINEAGE_REPLAY.json': '77f8300c2ebf594e640582dc213d8af1b012f7c11bf825a2c2b5f536fd2595d3',
    'G_SOURCE_READINESS_MATRIX.json': '4e8a76dcbf19c723b18b35eb2b9ed1439dca9bdd94e44572be70cf3b24c9f113',
}
APPROVAL_SHA = '5be72465e1882f5913f723e7857d8ee6b27f0f8f4e9d051b88ab2b809a0f0f2c'
REVIEW_HEAD = '4d53aa3047ba397cda992d2e784316a9d889bc22'
APPROVAL_COMMIT = '2ba29b048c8601145c4a2cca0f85299c07262286'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')


def ref(name, pointer):
    return {'artifact': name, 'sha256': PRIOR_HASHES[name], 'json_pointer': pointer,
            'authenticated_review_head': REVIEW_HEAD}


def unknown_outputs():
    return {key: 'UNCOMPUTED' for key in ['candidate_factor_score', 'G_aggregate', 'QGV_composite',
        'ranking', '3Y_5Y_stability_estimate', 'sector_bias_estimate', 'OOS_performance',
        'normalization', 'coverage_threshold', 'confidence_calibration']}


def common(identifier, family, dimension, verdict, rationale, input_requests, evidence):
    return {'candidate_id': identifier, 'family': family, 'decision': dimension,
        'verdict': verdict, 'rationale': rationale,
        'factor_id': 'next_3_5y_growth' if dimension == 'G1' else 'eps_fcf_per_share_growth',
        'method_id': None, 'method_version': None, 'approved_production_formula': None,
        'method_equation': 'UNKNOWN_UNSELECTED', 'source_requests': input_requests,
        'evidence_refs': evidence, 'outputs': unknown_outputs(),
        'runtime_enabled': False, 'production_eligibility': 'NOT_AUTHORIZED',
        'new_requiredness': None, 'numeric_policy': None,
        'consumer_migration': 'BLOCKED_BY_UNAPPROVED_RESULT_AND_CONSUMER_ADMISSION'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--approval', required=True, type=Path)
    parser.add_argument('--prior-dir', required=True, type=Path)
    parser.add_argument('--out-dir', required=True, type=Path)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert sha(args.approval) == APPROVAL_SHA, 'approval evidence identity changed'
    approval = json.loads(args.approval.read_text())
    prior = {}
    prior_dir = args.prior_dir.resolve()
    for name, expected in PRIOR_HASHES.items():
        assert sha(prior_dir / name) == expected, 'prior evidence identity changed: ' + name
        prior[name] = json.loads((prior_dir / name).read_text())
    assert approval['G1']['economic_target'] == 'LONG_HORIZON_REALIZED_GROWTH'
    assert approval['G2']['principle'] == 'NO_AUTOMATIC_CROSS_METRIC_SUBSTITUTION_WITHOUT_SEMANTIC_AUTHORITY'
    assert approval['method_selection'] == 'NOT_APPROVED' and not approval['runtime_enabled']
    M, R, S = 'G_METHOD_REPLAY_MANIFEST.json', 'G_LINEAGE_REPLAY.json', 'G_SOURCE_READINESS_MATRIX.json'
    candidates = []

    legacy = common('G1-LEGACY', 'Legacy latest-revenue-YoY proxy', 'G1', 'KEEP_ARCHIVAL_ONLY',
        'Actual executed branch is preserved literal evidence; one pair does not establish long-horizon realized magnitude and persistence.',
        ['No new inputs requested to preserve archived legacy results; exact archived method attribution still requires archived proof.'],
        [ref(M, '/records/0'), ref(R, '/persisted_historical_sample')])
    legacy['disposition_for_new_economic_target'] = 'REJECT_AS_AUTHORITATIVE_LONG_HORIZON_METHOD'
    legacy['existing_normalization_ref'] = 'Frozen legacy source expression only; no candidate adoption'
    legacy['observed_legacy_expression'] = prior[M]['records'][0]['normalization']['expression']
    legacy['observed_legacy_method_source_id'] = prior[M]['records'][0]['observed_method_id']
    candidates.append(legacy)

    endpoint = common('G1-ENDPOINT', 'Realized endpoint-summary family', 'G1', 'REJECT_AS_STANDALONE_FOR_APPROVED_TARGET',
        'Can describe start-to-end realized magnitude but loses the path. Distinct persistent, delayed and cyclical sequences can share endpoints.',
        ['Exact paired realized endpoints with matched accounting scope/unit/period/vintage', 'Separate persistence evidence if this family is retained as a component'],
        [ref(M, '/records/0/input_source_map'), ref(S, '/rows/4')])
    endpoint['economic_meaning'] = 'Observed change between two historical endpoints; not by itself sustained realization across intervening periods'
    endpoint['three_vs_five_year_stability'] = 'Endpoint/phase choice changes consumed inputs; empirical stability UNCOMPUTED and 3Y/5Y selection unapproved'
    endpoint['pit'] = 'Both endpoints need exact availability/publication and archived source vintage at each evaluation time'
    endpoint['restatement'] = 'Later restated endpoint cannot replace the value known at historical decision time'
    endpoint['sparse_or_young_history'] = 'Available endpoints can hide missing intervening periods; no assumed coverage adequacy'
    endpoint['cyclical_or_sector_bias'] = 'Different observed paths can share endpoints; any sector/phase comparability remains data-dependent'
    endpoint['historical_compatibility'] = 'Separate candidate/result lineage; does not relabel old YoY results'
    candidates.append(endpoint)

    series = common('G1-SERIES', 'Matched realized-period sequence-summary family', 'G1', 'MORE_EVIDENCE_REQUIRED',
        'Preserves observations across the historical window, permitting magnitude and persistence evidence. The summary statistic and normalization remain unselected.',
        ['Matched per-period source values with source concepts/units/fiscal durations', 'Archived vintage and per-observation availability/publication',
         'Explicit handling authority for missing periods, discontinuities, negative/zero bases and reporting changes'],
        [ref(M, '/records/0'), ref(S, '/rows/1'), ref(S, '/rows/2'), ref(S, '/rows/4')])
    series['economic_meaning'] = 'Multi-period realized observations; averaging, median, CAGR, slope and any other aggregation are not approved'
    series['three_vs_five_year_stability'] = 'Compare identical issuer data using separately identified windows after source readiness; numerical stability UNCOMPUTED'
    series['pit'] = 'Every observation is a dated vintage; the later full-series view cannot certify earlier knowledge'
    series['restatement'] = 'Retain original and revised source identities; historical run consumes only revisions then available'
    series['sparse_or_young_history'] = 'Gaps/short listing history remain explicit; neither interpolation nor minimum count selected'
    series['cyclical_or_sector_bias'] = 'Input sequence exposes reversals/one-time realization; industry accounting/seasonality scope needs evidence and separate policy'
    series['historical_compatibility'] = 'Parallel inactive lineage; unknown method until exact approved contract and input scope exist'
    candidates.append(series)

    persistence = common('G1-MAGNITUDE-PERSISTENCE', 'Separate realized magnitude and persistence assessments', 'G1', 'ALIGN_CANDIDATE_TO_APPROVED_MEANING',
        'Keeps the two approved economic dimensions visible rather than replacing persistence with a single endpoint scalar. This is a semantic decomposition, not a chosen formula.',
        ['Same PIT-bound realized period sequence as G1-SERIES', 'Explicit definitions and economic authority for magnitude and persistence',
         'Comparison with existing growth_durability concept to avoid undocumented evidence reuse/composite duplication'],
        [ref(M, '/records/0'), ref(M, '/records/4'), ref(S, '/rows/2')])
    persistence['economic_meaning'] = 'Magnitude and persistence separately assessed; no score, threshold, blend or extra factor is created'
    persistence['three_vs_five_year_stability'] = 'Window sensitivity and each assessment stability remain UNCOMPUTED; keep requested window in lineage'
    persistence['pit'] = 'Both assessments cite the same exact eligible source sequence, without Profile or zero-weight waivers'
    persistence['restatement'] = 'Late revisions preserve predecessor source/result identities and never rewrite archived results'
    persistence['sparse_or_young_history'] = 'Assessment may remain unknown with sparse/young inputs; no automatic N/A or denominator exclusion'
    persistence['cyclical_or_sector_bias'] = 'Separates endpoint magnitude from path evidence; sector-specific meaning and calibration remain unselected'
    persistence['historical_compatibility'] = 'No new factor ID; declared candidate method is not registered or retroactively attached to history'
    persistence['independent_factor_overlap'] = 'growth_durability rubric authority unresolved; shared input does not prove independent evidence or justify weight changes'
    candidates.append(persistence)

    for identifier, family, verdict, rationale, requirements in [
        ('G2-A', 'Factor unavailable when no admitted authorized substitute exists', 'PRINCIPLE_COMPATIBLE_CONTRACT_CANDIDATE',
         'Preserves the EPS target and does not manufacture another metric. Availability consequences still need B2/B3/B5/B6 approval.',
         ['Reasoned unavailable status with exact failed/missing input refs', 'No zero/N/A/denominator-exclusion/ranking implication']),
        ('G2-B', 'Economically comparable per-share alternative', 'MORE_EVIDENCE_REQUIRED',
         'Per-share units alone do not establish EPS-equivalent earnings meaning; exact numerator, shareholder claim, accounting basis and periods need authority.',
         ['Approved economic target/equivalence or explicit alternative authority', 'Paired attributable numerator and compatible share basis',
          'Basic/diluted, split, issuance/buyback/restatement and issuer/security lineage']),
        ('G2-C', 'Separately declared cash-flow method family', 'MORE_EVIDENCE_REQUIRED',
         'Cash generation can be separately described only under distinct economic meaning and method/version; it does not automatically inherit EPS semantics.',
         ['Exact current/prior cash-flow definitions and direct-versus-constructed component sources', 'Matched period/currency/vintage/domain and potential share basis',
          'Explicit approved cash-flow target and label if selected, without selecting an equation here']),
        ('G2-D', 'Conditional method applicability', 'MORE_EVIDENCE_REQUIRED',
         'Applicability is method/context authority, not an alternative metric and not a rule to choose the available/favorable branch.',
         ['Exact separately authorized method/context predicate with evidence', 'Issuer/sector/economic scope known at decision time',
          'Unknown/missing evidence preserved instead of converted into N/A']),
    ]:
        c = common(identifier, family, 'G2', verdict, rationale, requirements,
            [ref(M, '/records/3'), ref(S, '/rows/6'), ref(S, '/rows/8'), ref(S, '/rows/9'), ref(S, '/rows/10'), ref(S, '/rows/13')])
        c['semantic_comparability'] = rationale
        c['per_share_and_capital_structure'] = 'Attributable numerator and matched period/share basis required if per-share; current shares cannot stand in for prior weighted/diluted shares'
        c['dilution_corporate_actions'] = 'Exact security/issuer, diluted/basic treatment, splits/issuance/buybacks and revision evidence; none inferred from a finite ratio'
        c['volatility_domain'] = 'Observed zero/negative bases or changing cash-flow components expose domain questions; no smoothing, epsilon, transform, cutoff or normalization selected'
        c['pit'] = 'Every numerator/denominator/predicate/corporate-action observation carries source, period, as_of, available_at, published_at and audit method source; actual method refs remain null'
        c['missingness'] = 'Missing EPS alone never authorizes cross-metric substitution; missing predicate evidence never proves N/A; invalid input never becomes complete/valid/rankable'
        c['historical_compatibility'] = 'Legacy FCF/prior-revenue result stays LEGACY/METHOD_MISMATCH, separately hash-bound'
        candidates.append(c)

    matrix = {'artifact_kind': 'INACTIVE_G_METHOD_CANDIDATE_MATRIX', 'status': 'COMPARISON_COMPLETE_METHODS_UNSELECTED',
        'source_owner_head': prior[M]['source_owner_head'], 'authenticated_review_head': REVIEW_HEAD,
        'approval_ref': {'artifact': 'lanes/semantic/root/approval.json', 'sha256': APPROVAL_SHA,
            'authenticated_remote_commit': APPROVAL_COMMIT,
            'approval_id': approval['approval_id'], 'status': approval['status']},
        'approved_semantics': {'G1': approval['G1'], 'G2': approval['G2']},
        'factor_ids_preserved': ['next_3_5y_growth', 'eps_fcf_per_share_growth'],
        'prior_evidence_refs': PRIOR_HASHES, 'candidate_count': len(candidates), 'candidates': candidates,
        'forward_estimate_inclusion': 'NOT_APPROVED; not included as an authoritative G1 realized method',
        'new_formula_or_numeric_default': None, 'production_method_registration': None,
        'new_requiredness_assignments': 0, 'B1': 'MORE_EVIDENCE_REQUIRED',
        'result_and_consumer_admission': 'B2/B3/B5/B6 not yet approved; any selected future method still has migration blocker',
        'runtime_enabled': False, 'production_migration_authorized': False,
        'old_lineage_checks_rerun': False, 'real_scoring_or_real_input_replay': 'NOT_RUN',
        'scheduler_hops_added': 0,
        'minimal_remaining_D3': [
            {'clause': 'G1_CALCULATION_INPUT_CONTRACT', 'already_approved': 'Long-horizon realized magnitude and persistence target',
             'still_unselected': ['Exact accounting measure/input scope', '3Y/5Y window and period resolution', 'Realized summary/persistence method',
                 'Observation/domain requirements', 'Normalization/scoring policy'], 'requires_reapproval_of_economic_target': False},
            {'clause': 'G2_SUBSTITUTION_METHOD_CONTRACT', 'already_approved': 'No automatic unauthorized cross-metric substitution',
             'still_unselected': ['A/B/C/D exact branch/applicability treatment', 'Specific alternative target and input basis if any',
                 'Domain, missingness and normalization/scoring consequences'], 'requires_reapproval_of_principle': False},
            {'clause': 'DEPENDENT_ADMISSION_MIGRATION', 'still_unselected': ['B2/B3/B5/B6 evidence/result/consumer policy',
                'Production method binding and exact migration scope'], 'purpose': 'Separate gating; current comparison does not authorize activation'},
        ]}
    write(out / 'G_CANDIDATE_MATRIX.json', matrix)
    requests = [
        {'request_id': 'DATA-G-01', 'scope': 'G1+G2 exact archived real source bytes',
         'known_available': prior[R]['real_cached_raw_replay'],
         'needed': ['Archived companyfacts bytes matching recorded blob SHA256', 'Original manifest/fetch/source provenance'],
         'requested_owner_role': 'Authorized source-data/ingestion owner; assignment unresolved',
         'acceptance': ['Exact archived byte hash match', 'Restoration recorded as evidence; no latest-data substitution'],
         'next_action_if_supplied': 'Source-row vintage/period extraction only; no candidate scores'},
        {'request_id': 'DATA-G-02', 'scope': 'G1 observed realized history',
         'known_available': 'Current/prior source shape and quarterly monitor anchor; no actual full real source bytes in prior replay',
         'needed': ['All available dated realized-period rows with concepts/units/start/end/fiscal context',
                    'Original and revised vintage references with exact publication/availability precision'],
         'requested_owner_role': 'Fundamental-period data owner; assignment unresolved',
         'acceptance': ['Each observed row ties to archived source and as_of', 'Gaps/young history/period changes explicit',
                        'No minimum count, interpolation or 3Y/5Y selection implied'],
         'next_action_if_supplied': 'Inactive realized input comparability/window sensitivity evidence only'},
        {'request_id': 'DATA-G-03', 'scope': 'G2 earnings/share comparability',
         'known_available': 'Existing EPS producer concepts and synthetic pair; actual comparable share/claim evidence absent',
         'needed': ['Paired attributable earnings/EPS and basic/diluted denominator basis',
                    'Issuer/security/splits/issuance/buybacks/restatement source lineage'],
         'requested_owner_role': 'Earnings/share/corporate-action data owner; assignment unresolved',
         'acceptance': ['Same declared economic claim/accounting basis for paired observations',
                        'No current-share shortcut or hindsight corporate-action substitution'],
         'next_action_if_supplied': 'Source comparability evidence; B family economic equivalence still needs authority'},
        {'request_id': 'DATA-G-04', 'scope': 'G2 separate cash-generation inputs',
         'known_available': 'Direct FCF or CFO-abs(CAPEX) source shape; no scored prior-FCF/share pair',
         'needed': ['Exact current/prior cash-flow component definitions, concepts, currency and periods',
                    'Any proposed per-share numerator claim/basis and source vintages'],
         'requested_owner_role': 'Cash-flow data owner plus G-method authority; assignments unresolved',
         'acceptance': ['Separate earnings versus cash-generation meaning preserved',
                        'Constructed versus directly supplied cash-flow method lineage explicit'],
         'next_action_if_supplied': 'Inactive input readiness; no automatic EPS substitution or new formula'},
        {'request_id': 'DATA-G-05', 'scope': 'Method-specific context/applicability evidence',
         'known_available': 'Current G profile Boolean exists but is not applicability authority',
         'needed': ['Issuer/sector/economic context from dated source', 'Predicate authority if a conditional family is later selected'],
         'requested_owner_role': 'QGV applicability/sector authority under B2; assignment unresolved',
         'acceptance': ['Missing evidence remains unknown', 'No data/favorable-score-triggered N/A or denominator exclusion'],
         'next_action_if_supplied': 'Inactive applicability evidence comparison; production predicate unapproved'},
        {'request_id': 'AUTH-G-06', 'scope': 'Concrete method/input/admission package',
         'known_available': 'G1/G2 economic principles approved; all eight candidate methods still unselected',
         'needed': ['Exact future method/domain/window/normalization contract', 'Dependent B2/B3/B5/B6 result/consumer contract'],
         'requested_owner_role': 'User D3/QGV semantic and consumer authority',
         'acceptance': ['Separate method/version and result lineage', 'No archived rewrite, profile method override or ranking activation by implication'],
         'next_action_if_supplied': 'Only specifically approved scope may proceed; this comparison does not migrate production'},
    ]
    write(out / 'G_CANDIDATE_SOURCE_REQUESTS.json', {'kind': 'FINITE_INACTIVE_DATA_AUTHORITY_REQUESTS',
        'count': len(requests), 'requests': requests, 'prior_evidence_hashes': PRIOR_HASHES,
        'approval_sha256': APPROVAL_SHA, 'authoritative_owner_assignments': 'UNRESOLVED; requested roles do not claim ownership',
        'new_formula': None, 'production_enabled': False, 'scheduler_hops_added': 0})

    as_of = '2025-03-01T00:00:00+00:00'
    audit_method = {'method_id': None, 'method_version': None,
        'observed_audit_source_ref': prior[M]['records'][0]['observed_method_id'],
        'observed_audit_source_version': prior[M]['records'][0]['observed_method_version'],
        'audit_anchor_role': 'Predecessor source context only; not an executed candidate method or authoritative input measurement method'}
    shapes = {'sustained': [100, 105, 110, 115, 120, 125],
        'delayed': [100, 100, 100, 100, 100, 125],
        'reversal': [100, 150, 90, 140, 80, 125],
        'same_last_pair_different_earlier_path': [80, 140, 90, 135, 120, 125]}
    fixtures = []
    for name, levels in shapes.items():
        rows = []
        for index, value in enumerate(levels):
            year = 2019 + index
            rows.append({'period': {'start': f'{year}-01-01', 'end': f'{year}-12-31'},
                'source': {'provider': 'SYNTHETIC_DIAGNOSTIC', 'reference': name + ':' + str(year),
                           'value_kind': 'unscaled_reported_level_fixture_not_a_chosen_G1_metric'},
                'raw_level': value, 'as_of': as_of, 'available_at': f'{year+1}-02-20T10:00:00+00:00',
                'published_at': f'{year+1}-02-20T10:00:00+00:00', **audit_method})
        fixtures.append({'case': name, 'synthetic': True, 'observations': rows,
            'candidate_factor_score': 'UNCOMPUTED', 'magnitude_estimator': 'UNCOMPUTED',
            'persistence_estimator': 'UNCOMPUTED'})
    pit_rows = [
        {'vintage_id': 'original', 'period': {'start': '2024-01-01', 'end': '2024-12-31'},
         'raw_level': 100, 'source': 'SYNTHETIC_ORIGINAL', 'as_of': as_of,
         'available_at': '2025-02-20T10:00:00+00:00', 'published_at': '2025-02-20T10:00:00+00:00', **audit_method},
        {'vintage_id': 'later_restatement', 'period': {'start': '2024-01-01', 'end': '2024-12-31'},
         'raw_level': 140, 'source': 'SYNTHETIC_LATER_AMENDMENT', 'as_of': as_of,
         'available_at': '2025-06-20T10:00:00+00:00', 'published_at': '2025-06-20T10:00:00+00:00', **audit_method},
        {'vintage_id': 'future_published', 'period': {'start': '2024-01-01', 'end': '2024-12-31'},
         'raw_level': 150, 'source': 'SYNTHETIC_INCONSISTENT_STAMPS', 'as_of': as_of,
         'available_at': '2025-02-20T10:00:00+00:00', 'published_at': '2025-06-20T10:00:00+00:00', **audit_method},
        {'vintage_id': 'future_available', 'period': {'start': '2024-01-01', 'end': '2024-12-31'},
         'raw_level': 160, 'source': 'SYNTHETIC_INCONSISTENT_STAMPS', 'as_of': as_of,
         'available_at': '2025-06-20T10:00:00+00:00', 'published_at': '2025-02-20T10:00:00+00:00', **audit_method},
    ]
    per_share_case = {'case': 'shared_units_different_economic_quantities', 'synthetic': True,
        'reported_EPS_levels': [2.0, 3.0], 'separate_cash_flow_per_share_levels': [10.0, 4.0],
        'economic_source_identity': ['declared_earnings_per_share_fixture', 'declared_cash_generation_per_share_fixture'],
        'share_basis': 'matched synthetic declaration only; no production numerator/share basis approved',
        'direction_only': ['EPS_level_increased', 'separate_cash_flow_per_share_level_decreased'],
        'candidate_factor_score': 'UNCOMPUTED', 'substitution_allowed': False}
    per_share_case['observations'] = [
        {'period': {'start': f'{year}-01-01', 'end': f'{year}-12-31'},
         'source': {'provider': 'SYNTHETIC_DIAGNOSTIC', 'reference': 'per-share-comparability:' + str(year)},
         'as_of': as_of, 'published_at': f'{year+1}-02-20T10:00:00+00:00',
         'available_at': f'{year+1}-02-20T10:00:00+00:00',
         'EPS_level_fixture': per_share_case['reported_EPS_levels'][index],
         'separate_cash_flow_per_share_level_fixture': per_share_case['separate_cash_flow_per_share_levels'][index],
         **audit_method} for index, year in enumerate([2023, 2024])]
    diagnostics = {'kind': 'SYNTHETIC_INPUT_PROPERTIES_ONLY', 'shape_cases': fixtures,
        'PIT_vintage_cases': pit_rows, 'per_share_semantic_case': per_share_case,
        'production_scorer_called': False, 'new_G1_or_G2_formula_executed': False,
        'notes': ['Illustrative fixture points are not a minimum observation count or period policy.',
            'No CAGR/mean/median/normalization is computed.', 'Existing raw-derived scores were not recalculated.']}
    write(out / 'G_CANDIDATE_DIAGNOSTICS.json', diagnostics)

    # Focused evidence invariants, not method acceptance or production tests.
    checks = []
    def check(name, actual, expected):
        okay = actual == expected
        checks.append({'case': name, 'actual': actual, 'expected': expected, 'pass': okay})
        assert okay, name
    check('approval target is realized and method selection remains excluded',
        (approval['G1']['economic_target'], approval['method_selection']),
        ('LONG_HORIZON_REALIZED_GROWTH', 'NOT_APPROVED'))
    check('factor identity retained without renaming', matrix['factor_ids_preserved'], ['next_3_5y_growth', 'eps_fcf_per_share_growth'])
    check('production method identities not invented', all(c['method_id'] is None and c['method_version'] is None for c in candidates), True)
    check('legacy proxy not promoted to realized-authoritative method', legacy['disposition_for_new_economic_target'], 'REJECT_AS_AUTHORITATIVE_LONG_HORIZON_METHOD')
    check('known legacy expression preserved separately from unselected future equation',
        (legacy['observed_legacy_expression'], legacy['method_equation']),
        (prior[M]['records'][0]['normalization']['expression'], 'UNKNOWN_UNSELECTED'))
    check('same endpoints cannot establish persistence',
        shapes['sustained'][0] == shapes['delayed'][0] and shapes['sustained'][-1] == shapes['delayed'][-1] and shapes['sustained'][1:-1] != shapes['delayed'][1:-1], True)
    check('same endpoints cannot resolve cyclical path',
        shapes['sustained'][0] == shapes['reversal'][0] and shapes['sustained'][-1] == shapes['reversal'][-1] and shapes['sustained'][1:-1] != shapes['reversal'][1:-1], True)
    check('same last pair does not establish same long history', shapes['sustained'][-2:] == shapes['same_last_pair_different_earlier_path'][-2:] and shapes['sustained'][:-2] != shapes['same_last_pair_different_earlier_path'][:-2], True)
    check('3Y/5Y input window identity differs without selecting a scoring window',
        [r['period']['end'] for r in fixtures[0]['observations'] if r['period']['end'] >= '2021-12-31'] != [r['period']['end'] for r in fixtures[0]['observations']], True)

    def known_at_fixture_as_of(row):
        t = datetime.fromisoformat(row['as_of'])
        return datetime.fromisoformat(row['available_at']) <= t and datetime.fromisoformat(row['published_at']) <= t and date.fromisoformat(row['period']['end']) <= t.date()
    check('past run preserves then-known original rather than later restatement', [r['vintage_id'] for r in pit_rows if known_at_fixture_as_of(r)], ['original'])
    check('future published time not hidden by earlier available time', known_at_fixture_as_of(pit_rows[2]), False)
    check('future availability not hidden by earlier publication', known_at_fixture_as_of(pit_rows[3]), False)
    check('matched per-share unit cannot authorize cash-flow/EPS substitution', per_share_case['substitution_allowed'], False)
    check('per-share different quantities can move in opposite directions', per_share_case['reported_EPS_levels'][1] > per_share_case['reported_EPS_levels'][0] and per_share_case['separate_cash_flow_per_share_levels'][1] < per_share_case['separate_cash_flow_per_share_levels'][0], True)
    check('unavailable is not N/A or denominator exclusion', candidates[4]['source_requests'][1], 'No zero/N/A/denominator-exclusion/ranking implication')
    check('all candidate scoring/order outputs remain uncomputed', all(set(c['outputs'].values()) == {'UNCOMPUTED'} for c in candidates), True)
    check('new requiredness and numeric policy absent', matrix['new_requiredness_assignments'] == 0 and matrix['new_formula_or_numeric_default'] is None, True)
    check('consumer admission is a remaining migration blocker', all(c['consumer_migration'] == 'BLOCKED_BY_UNAPPROVED_RESULT_AND_CONSUMER_ADMISSION' for c in candidates), True)
    check('manual work cannot count scheduler hops', matrix['scheduler_hops_added'], 0)
    check('approved semantics do not authorize production migration', approval['production_migration_authorized'], False)
    check('frozen prior artifact identities unchanged', all(sha(prior_dir / name) == expected for name, expected in PRIOR_HASHES.items()), True)
    verification = {'status': 'LOCAL_INACTIVE_CANDIDATE_INVARIANTS_PASS', 'count': len(checks),
        'passed': sum(c['pass'] for c in checks), 'checks': checks,
        'candidate_factor_scores_computed': False, 'real_PIT_OOS': 'NOT_RUN',
        'old_lineage_checks_rerun': False, 'production_runtime_changed': False, 'scheduler_hops_added': 0,
        'approval_sha256': APPROVAL_SHA, 'prior_input_hashes': PRIOR_HASHES,
        'script_sha256': sha(Path(__file__)),
        'outputs': {n: sha(out / n) for n in ['G_CANDIDATE_MATRIX.json', 'G_CANDIDATE_DIAGNOSTICS.json', 'G_CANDIDATE_SOURCE_REQUESTS.json']}}
    write(out / 'G_CANDIDATE_VERIFICATION.json', verification)
    print(json.dumps({'status': verification['status'], 'candidate_count': len(candidates), 'checks': len(checks),
        'passed': verification['passed'], 'scores': 'UNCOMPUTED', 'matrix_sha256': sha(out / 'G_CANDIDATE_MATRIX.json')}))


if __name__ == '__main__':
    main()
