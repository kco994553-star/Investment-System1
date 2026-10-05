"""List differing leaf paths between the 'result' sections of two FPIA outputs."""
import json, sys
a, b = (json.load(open(p))["result"] for p in sys.argv[1:3])
out = []
def walk(x, y, path):
    if type(x) != type(y):
        out.append((path, x, y)); return
    if isinstance(x, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x or k not in y:
                out.append((path + "." + k, x.get(k, "<absent>"), y.get(k, "<absent>")))
            else:
                walk(x[k], y[k], path + "." + k)
    elif isinstance(x, list):
        if len(x) != len(y):
            out.append((path + "[len]", len(x), len(y)))
        for i, (p, q) in enumerate(zip(x, y)):
            walk(p, q, "%s[%d]" % (path, i))
    elif x != y:
        out.append((path, x, y))
walk(a, b, "result")
print(len(out), "differing leaf paths")
for p, x, y in out[:60]:
    print(p, "|", str(x)[:160], "|", str(y)[:160])
