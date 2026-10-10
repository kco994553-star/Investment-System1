"""GSQ-017 provisional memberships and parent Q/G/V mixing. RAM-only.

No original factor/snapshot mutation, serializer, prices, network or IO.
Metric derivation and source/basis validation belong to supplied inputs.
"""
from .type_config import PILLARS, TypeConfig, finite, validate_type_config


def _membership(rule, metrics):
    kind = rule['kind']; evidence = {}
    def output(value, reasons=(), components=None):
        return {'membership': value, 'state': 'NOT_AVAILABLE' if value is None else 'PROVISIONAL',
                'reason_codes': list(reasons), 'evidence': evidence,
                **({'components': components} if components is not None else {})}
    if kind == 'unresolved':
        return output(None, rule['reasons'], [_membership(r, metrics) for r in rule.get('components', [])])
    metric = rule['metric']; value = metrics.get(metric)
    # Explicit evidence preserves missing; never substitute zeros.
    evidence[metric] = value if finite(value) else None
    if kind == 'gated_ramp':
        gate = metrics.get(rule['gate_metric'])
        evidence[rule['gate_metric']] = gate if type(gate) is bool else None
        if gate is False: return output(0.)
        if gate is not True: return output(None, ('GATE_NOT_AVAILABLE',))
    if not finite(value): return output(None, ('METRIC_NOT_AVAILABLE',))
    if kind == 'rank':
        if type(value) is not int or value < 1: return output(None, ('RANK_NOT_AVAILABLE',))
        return output(1. if value <= rule['max_rank'] else 0.)
    return output(min(1., max(0., (value - rule['lower']) / (rule['upper'] - rule['lower']))))


def calculate_company_types(*, metrics, original_qgv, config):
    """Pure function. Input metrics use ratios (0.10=10%); scores use 0..100.

    Both original pillars and adjusted pillars survive. Only a supplied
    normalized-earnings V score may replace cyclical V; no scoring map is made.
    Membership/weights never imply model activation or publication permission.
    """
    if not isinstance(config, TypeConfig) or not isinstance(metrics, dict) or not isinstance(original_qgv, dict): raise ValueError('INVALID_INPUT')
    cfg = config.to_dict(); errors = validate_type_config(cfg)
    if errors: raise ValueError('|'.join(errors))
    originals = {p: original_qgv.get(p) for p in PILLARS}
    if any(v is not None and (not finite(v) or not 0 <= v <= 100) for v in originals.values()): raise ValueError('QGV_INVALID')
    types = cfg['types']; memberships = {t['id']: _membership(t['rule'], metrics) for t in types}
    mix = cfg['mixing']; order = {t['id']: i for i, t in enumerate(types)}
    recognized = [t for t in types if t['affects_qgv'] and memberships[t['id']]['membership'] is not None and memberships[t['id']]['membership'] >= mix['minimum_membership']]
    recognized.sort(key=lambda t: (-memberships[t['id']]['membership'], order[t['id']]))
    dropped = set()
    for a, b in mix['exclusive_pairs']:
        present = [t for t in recognized if t['id'] in (a, b) and t['id'] not in dropped]
        if len(present) == 2: dropped.add(present[1]['id'])
    selected = [t for t in recognized if t['id'] not in dropped][:mix['maximum_types']]
    reasons = []
    if not selected:
        weights = {p: float(cfg['fallback']['weights'][p]) for p in PILLARS}
        if all(memberships[t['id']]['membership'] is None for t in types if t['affects_qgv']): reasons.append('TYPE_UNCONFIRMED')
        else: reasons.append('NO_RECOGNIZED_TYPE')
    else:
        mass = sum(memberships[t['id']]['membership'] for t in selected)
        weights = {p: sum(t['weights'][p] * memberships[t['id']]['membership'] for t in selected) / mass for p in PILLARS}
    # Exact approved order: one clamp, then one renormalization. Do not iterate.
    clamped = {p: min(mix['pillar_max'], max(mix['pillar_min'], weights[p])) for p in PILLARS}
    total = sum(clamped.values())
    if total <= 0: raise ValueError('MIXING_INVALID')
    weights = {p: 100. * clamped[p] / total for p in PILLARS}
    adjusted = dict(originals)
    if cfg['value_basis']['cyclical_type'] in [t['id'] for t in selected]:
        value = metrics.get(cfg['value_basis']['required_metric'])
        if not finite(value) or not 0 <= value <= 100:
            adjusted['V'] = None; reasons.append('NORMALIZED_EARNINGS_VALUE_REQUIRED')
        else: adjusted['V'] = value
    missing = [p for p in PILLARS if adjusted[p] is None]
    adjusted_score = None if missing else sum(adjusted[p] * weights[p] / 100. for p in PILLARS)
    return {'role': 'OFFICIAL_PROVISIONAL' if config.official else 'PREVIEW',
            'config_status': 'OFFICIAL_PROVISIONAL' if config.official else 'CUSTOM_PREVIEW',
            'config_version': cfg['config_version'], 'calibration': 'V2_PENDING',
            'memberships': memberships, 'selected_types': [t['id'] for t in selected],
            'excluded_unavailable': [t['id'] for t in types if memberships[t['id']]['membership'] is None],
            'fallback_type': cfg['fallback']['id'] if not selected else None,
            'weights': weights, 'original_qgv': originals, 'adjusted_qgv': adjusted,
            'adjusted_score': adjusted_score, 'missing_pillars': missing, 'reason_codes': reasons}
