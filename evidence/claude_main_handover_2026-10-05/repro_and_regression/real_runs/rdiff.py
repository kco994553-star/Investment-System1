"""Diff two FPIA outputs' result sections path by path (lists compared index-wise; dict keys sorted)."""
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
lim = int(sys.argv[3]) if len(sys.argv) > 3 else 400
n = [0]
def emit(*x):
    n[0] += 1
    if n[0] <= lim: print(*x)
def diff(x, y, p=''):
    if type(x) != type(y): emit('TYPE', p, str(x)[:200], '|', str(y)[:200]); return
    if isinstance(x, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x: emit('ONLY_B', p + '/' + k, json.dumps(y[k], sort_keys=True)[:300]); continue
            if k not in y: emit('ONLY_A', p + '/' + k, json.dumps(x[k], sort_keys=True)[:300]); continue
            diff(x[k], y[k], p + '/' + k)
    elif isinstance(x, list):
        if len(x) != len(y): emit('LEN', p, len(x), len(y))
        for i, (u, v) in enumerate(zip(x, y)): diff(u, v, p + '[%d]' % i)
        if len(x) > len(y):
            for i in range(len(y), len(x)): emit('ONLY_A', p + '[%d]' % i, json.dumps(x[i], sort_keys=True)[:300])
        if len(y) > len(x):
            for i in range(len(x), len(y)): emit('ONLY_B', p + '[%d]' % i, json.dumps(y[i], sort_keys=True)[:300])
    elif x != y: emit('VAL', p, str(x)[:200], '|', str(y)[:200])
diff(a['result'], b['result'])
print('TOTAL_DIFFS', n[0])
