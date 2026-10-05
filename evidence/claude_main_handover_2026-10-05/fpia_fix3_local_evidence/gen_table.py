"""Dev-time (not shipped): fix round 3 confusable table = every NFD-stable code point whose ICU 74.2
uspoof_getSkeleton prototype is non-empty ASCII (fix round 2 kept only NFKC-stable sources)."""
import json, sys, unicodedata
d = json.load(open("icu_extract.json"))
assert d["icu"] == "74.2" and d["unicode"] == "15.1.0"
groups = {}
for k, v in d["map"].items():
    proto = [int(x, 16) for x in v.split()]
    if not proto or any(c >= 128 for c in proto):
        continue
    groups.setdefault(".".join("%X" % c for c in proto), []).append(int(k, 16))
items = []
for proto in sorted(groups, key=lambda p: [int(x, 16) for x in p.split(".")]):
    items.append(proto + "=" + ",".join("%X" % c for c in sorted(groups[proto])))
s = ";".join(items)
n = sum(len(v) for v in groups.values())
stable = sum(1 for v in groups.values() for c in v if unicodedata.normalize("NFKC", chr(c)) == chr(c))
lines = [s[i:i + 100] for i in range(0, len(s), 100)]
out = "CONFUSABLES_ASCII = (\n" + "\n".join('    "%s"' % l for l in lines) + "\n)\n"
open("table.py", "w").write(out)
print("code points", n, "groups", len(groups), "nfkc-stable", stable, "chars", len(s))
