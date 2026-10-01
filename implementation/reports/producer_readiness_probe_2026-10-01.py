"""Producer -> Web MVP schema-1 contract probe (Producer Readiness Audit 2026-10-01). Read-only; existing engines unchanged.
Run from a checkout of PR #6 head eda65bf: python3 reports/producer_readiness_probe_2026-10-01.py src"""
import json, sys, dataclasses, enum
from copy import deepcopy
from datetime import datetime, timezone
sys.path.insert(0, sys.argv[1])
from investment_system.product.web_mvp import repository_bundle, validate_bundle, SECTIONS
from investment_system.technical.engine import TechnicalEngine
from investment_system.macro.engine import MacroEngine
from investment_system.validation.adapters import TechnicalAdapter, MacroAdapter
from investment_system.qgv.leaderboard import LeaderboardEngine
from investment_system.contracts import models
R = {}
def ser(o):
    if dataclasses.is_dataclass(o): return {k: ser(v) for k, v in dataclasses.asdict(o).items()}
    if isinstance(o, dict): return {k: ser(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [ser(v) for v in o]
    if isinstance(o, enum.Enum): return o.value
    if isinstance(o, datetime): return o.isoformat()
    return o
def attempt(name, fn):
    try: fn(); R[name] = 'ACCEPTED'
    except Exception as e: R[name] = f'REJECTED: {type(e).__name__}: {e}'
b = repository_bundle()
R['default_bundle_states'] = {s: b[s]['state'] for s in ('universe', *SECTIONS)}
R['default_universe_as_of'] = b['universe']['as_of']
R['companies'] = len(b['companies'])
R['companies_with_issuer_id'] = sum(1 for c in b['companies'] if c.get('issuer_id'))
cid = b['companies'][0]['company_id']
now = datetime.now(timezone.utc)
live = lambda data: {'state': 'LIVE', 'as_of': now.isoformat(), 'expires_at': now.isoformat(), 'source': 'probe', 'data': data}
# Technical through the existing adapter path (default synthetic)
t = TechnicalAdapter().snapshot(cid, now, [0.01, 0.02, -0.01, 0.005, 0.01])
R['technical_adapter_synthetic_flag'] = t.synthetic
x = deepcopy(b); x['technical'] = live({cid: ser(t)}); attempt('technical_adapter_output_as_LIVE', lambda: validate_bundle(x))
t2 = TechnicalEngine().evaluate(cid, now, [0.01]*5, synthetic=False)
R['technical_engine_placeholder_fields'] = {'invalidation': t2.invalidation, 'scenario_kind': t2.scenarios[0]['kind'], 'version': t2.technical_version, 'kind': t2.implementation_kind}
# Macro
m = MacroAdapter().snapshot(now, {'growth': 0.02, 'inflation': 0.03})
R['macro_adapter_synthetic_flag'] = m.synthetic
md = ser(m)
R['macro_web_fields_present'] = {k: k in md for k in ('state', 'regime', 'indicators', 'exposures')}
x = deepcopy(b); x['macro'] = live(md); attempt('macro_adapter_output_as_LIVE', lambda: validate_bundle(x))
# LIVE without expires_at
x = deepcopy(b); s = live({cid: {'regime': 'RANGE'}}); s.pop('expires_at'); x['technical'] = s
attempt('LIVE_without_expires_at', lambda: validate_bundle(x))
# Already-expired LIVE
x = deepcopy(b); s = live({cid: {'regime': 'RANGE'}}); s['expires_at'] = '2020-01-01T00:00:00+00:00'; x['technical'] = s
attempt('LIVE_already_expired', lambda: validate_bundle(x))
# Leaderboard field coverage vs Web consumer
web_lb = ['rank', 'company_id', 'ticker', 'market_cap_rank', 'total_score', 'daily_move', 'consensus', 'scenario', 'reevaluation_trigger']
lb = [f.name for f in dataclasses.fields(models.LeaderboardRow)]
R['leaderboard_web_fields_missing_in_LeaderboardRow'] = [f for f in web_lb if f not in lb]
web_q = ['Q_score', 'G_score', 'V_score', 'total_score', 'confidence', 'coverage_state']
R['qgv_web_fields_missing_in_QGVSnapshot'] = [f for f in web_q if f not in [f.name for f in dataclasses.fields(models.QGVSnapshot)]]
web_p = ['holdings[].company_id', 'holdings[].ticker', 'holdings[].actual_weight', 'holdings[].return', 'return', 'market_value', 'currency', 'exposure']
R['portfolio_web_fields'] = web_p
R['portfolio_snapshot_fields'] = [f.name for f in dataclasses.fields(models.PortfolioSnapshot)]
# exporter existence
import pkgutil, investment_system
mods = [m.name for m in pkgutil.walk_packages(investment_system.__path__, 'investment_system.')]
R['modules_named_export_or_daily'] = [m for m in mods if any(k in m for k in ('export', 'daily', 'producer', 'bundle'))]
print(json.dumps(R, indent=1, ensure_ascii=False))
