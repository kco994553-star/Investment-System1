"""Cross-track numerical fingerprint (Entity Metadata v1 evidence).

Usage: python docs/entity_metadata/evidence/numeric_fingerprint.py <implementation-dir> | sha256sum
Run on PR #6 head (eda65bf) and PR #7 head; the outputs must be byte-identical.

Volatile identifiers (uuid snapshot ids, generated timestamps) are removed; every
numeric field, label and row order is kept.
"""
import hashlib, json, re, sys, tempfile
from pathlib import Path
ROOT = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.technical.engine import TechnicalEngine
from investment_system.macro.engine import MacroEngine
from investment_system.qgv.portfolio import PortfolioEngine
from investment_system.qgv.leaderboard import LeaderboardEngine
from investment_system.product.web_mvp import build, repository_bundle, demo_bundle
from tests.helpers import AS_OF, complete_obs

VOLATILE = re.compile(r'(_snapshot_id|_id_run|generated_at|created_at)$')
def clean(v):
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items() if not VOLATILE.search(k)}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    return v

ids = ['nvda', 'asml', 'aapl', 'msft', 'amd', 'avgo', 'intc', 'qcom', 'lrcx', 'klac']
qgv = {c: AnalysisEngine().analyze(c, AS_OF, complete_obs(40.0 + 5 * i), synthetic=True) for i, c in enumerate(ids)}
out = {
    'qgv': {c: clean(s.to_dict()) for c, s in qgv.items()},
    'technical': {c: clean(TechnicalEngine().evaluate(c, AS_OF, [0.01 * (i % 3), 0.02, -0.01, 0.005 * i]).to_dict()) for i, c in enumerate(ids)},
    'macro': clean(MacroEngine().evaluate(AS_OF, {'growth': 0.04, 'inflation': 0.02}).to_dict()),
    'portfolio': clean(PortfolioEngine().official_v11(AS_OF, qgv).to_dict()),
}
lb = LeaderboardEngine().build('us500', AS_OF, list(qgv.values()), {c: c.upper() for c in ids})
out['leaderboard'] = clean(lb.to_dict())
out['leaderboard_order'] = [r['company_id'] for r in out['leaderboard']['rows']]
# Product build: data.json (producer payload) must stay identical; entities.json is the only expected delta.
with tempfile.TemporaryDirectory() as d:
    build(Path(d) / 'a', bundle=repository_bundle())
    build(Path(d) / 'b', bundle=demo_bundle(repository_bundle()))
    out['data_json_sha256'] = {k: hashlib.sha256((Path(d) / k / 'data.json').read_bytes()).hexdigest() for k in 'ab'}
# Committed numerical reports (Track A/QGV outputs) - byte hashes.
out['reports_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted((ROOT / 'reports').rglob('*.json')) if 'entity_metadata' not in p.parts}
print(json.dumps(out, sort_keys=True, ensure_ascii=False, default=str))
