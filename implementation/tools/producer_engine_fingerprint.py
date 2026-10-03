"""Numerical fingerprint of existing QGV/Technical/Macro/Leaderboard/Portfolio engines on repository fixtures.

Random ids and wall-clock fields are excluded. Compare two trees:
  python tools/producer_engine_fingerprint.py <treeA>/implementation/src > a.json   (repeat for treeB; diff)
"""
import sys, json, hashlib, dataclasses, enum
from datetime import datetime, timezone
sys.path.insert(0, sys.argv[1])
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.providers.catalog import iter_official_raw
from investment_system.technical.engine import TechnicalEngine
from investment_system.macro.engine import MacroEngine
from investment_system.qgv.leaderboard import LeaderboardEngine
from investment_system.qgv.book import run_official_book
DROP = {'qgv_snapshot_id', 'technical_snapshot_id', 'macro_snapshot_id', 'leaderboard_snapshot_id',
        'portfolio_snapshot_id', 'analyzed_at', 'generated_at', 'snapshot_at', 'revision_parent_id', 'leaderboard_id', 'qgv_refs', 'technical_ref', 'macro_ref'}


def norm(o):
    if dataclasses.is_dataclass(o):
        o = dataclasses.asdict(o)
    if isinstance(o, dict):
        return {k: norm(v) for k, v in sorted(o.items()) if k not in DROP}
    if isinstance(o, (list, tuple)):
        return [norm(v) for v in o]
    if isinstance(o, enum.Enum):
        return o.value
    if isinstance(o, datetime):
        return o.isoformat()
    return o


def h(x):
    return hashlib.sha256(json.dumps(norm(x), sort_keys=True, default=str).encode()).hexdigest()


now = datetime(2026, 9, 14, tzinfo=timezone.utc)
q = [AnalysisPipeline().analyze_raw(r) for r in iter_official_raw()]
t = [TechnicalEngine().evaluate(s.company_id, now, [0.01, -0.02, 0.03, 0.005, 0.01, -0.001]) for s in q]
m = [MacroEngine().evaluate(now, x) for x in ({}, {'growth': 0.04, 'inflation': 0.02},
                                              {'growth': -0.01, 'inflation': 0.06}, {'inflation': 0.09})]
lb = LeaderboardEngine().build('u', now, q, {s.company_id: s.company_id for s in q})
book = run_official_book()
print(json.dumps({'qgv': h(q), 'technical': h(t), 'macro': h(m), 'leaderboard': h(lb),
                  'portfolio_official_book': h(book), 'n_qgv': len(q)}, indent=1, sort_keys=True))
