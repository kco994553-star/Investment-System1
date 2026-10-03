"""Independent deterministic, synthetic-only invariance probe; never a method approval."""
import contextlib, dataclasses, enum, hashlib, io, json, random, runpy, sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / 'src'))
from investment_system.technical.engine import TechnicalEngine
from investment_system.macro.engine import MacroEngine

DROP = {'qgv_snapshot_id', 'technical_snapshot_id', 'macro_snapshot_id', 'leaderboard_snapshot_id',
        'portfolio_snapshot_id', 'analyzed_at', 'generated_at', 'snapshot_at', 'revision_parent_id',
        'leaderboard_id', 'qgv_refs', 'technical_ref', 'macro_ref'}
def norm(value):
    if dataclasses.is_dataclass(value): value = dataclasses.asdict(value)
    if isinstance(value, dict): return {k: norm(v) for k,v in sorted(value.items()) if k not in DROP}
    if isinstance(value, (list, tuple)): return [norm(v) for v in value]
    if isinstance(value, enum.Enum): return value.value
    if isinstance(value, datetime): return value.isoformat()
    return value

now = datetime(2026, 9, 14, tzinfo=timezone.utc)
rng = random.Random(17393)
series = [[], [0.0], [0.01,-0.02,0.03,0.005,0.01,-0.001]]
series += [[rng.uniform(-0.2,0.2) for _ in range(n)] for n in range(2,102)]
technical = [norm(TechnicalEngine().evaluate('synthetic-audit', now, xs, synthetic=True)) for xs in series]
indicators = [{}, {'growth':0.04,'inflation':0.02}, {'growth':-0.01,'inflation':0.06}, {'inflation':0.09}]
indicators += [{'growth':g,'inflation':i} for g in [-0.05, -0.00001, 0, 0.03, 0.03001, 0.06] for i in [0,0.02999,0.03,0.05,0.05001,0.08,0.08001]]
macro = [norm(MacroEngine().evaluate(now, x, synthetic=True)) for x in indicators]
with contextlib.redirect_stdout(io.StringIO()) as capture:
    sys.argv = [sys.argv[0], str(root/'src')]
    tool = runpy.run_path('/workspace/adoption-audit-pr17/implementation/tools/producer_engine_fingerprint.py')
payload = {'technical': technical, 'macro': macro, 'fingerprints':json.loads(capture.getvalue()),
           'fingerprint_inputs':{k:norm(tool[k]) for k in ['q','t','m','lb','book']},
           'scope':'repository synthetic fixtures only; CAL_VERIFY/Holdout NOT_ACCESSED'}
print(json.dumps(payload, sort_keys=True, default=str))
