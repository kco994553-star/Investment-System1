"""Prompt Library v1 (Track E) command line: search / show / fill (copy text) / bundle export / render the page.

Copy-first and offline: prints plain text for pasting into any AI; calls no LLM, no network, no analysis engine.

Usage:
  python tools/prompt_library.py search --domain TECHNICAL --role BASIC --keyword Momentum
  python tools/prompt_library.py show TECH-002            # merged legacy code resolves to TECH-001.v1.0
  python tools/prompt_library.py fill plv1.tech.001 --var input_mode=SYSTEM_CONTEXT --var ticker=AAPL \
      --var period=1Y --var as_of=2024-12-31 --var technical_input="(paste TechnicalSnapshot)"
  python tools/prompt_library.py bundle 4 --values values.json [--format json]
  python tools/prompt_library.py render-html [--out path]
Exit code 2 on any fail-closed error (missing/invalid variable, retired or unknown prompt, bad filter).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from investment_system.prompt_library.catalog import RetiredPromptError, load_catalog, resolve  # noqa: E402
from investment_system.prompt_library.fill import VariableFillError, bundle_variables, export, fill, variable_specs  # noqa: E402
from investment_system.prompt_library.search import SearchFilterError, search  # noqa: E402
from investment_system.prompt_library.ui import write_html  # noqa: E402


def _values(a) -> dict:
    vals = json.loads(Path(a.values).read_text(encoding="utf-8")) if getattr(a, "values", None) else {}
    for kv in getattr(a, "var", None) or []:
        k, sep, v = kv.partition("=")
        if not sep:
            raise VariableFillError("CLI", invalid=[f"--var {kv!r} is not name=value"])
        vals[k.strip()] = v
    return vals


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("--keyword")
    for k in ("domain", "role", "category", "subcategory", "scope", "input_mode"):
        s.add_argument(f"--{k.replace('_', '-')}", dest=k)
    s.add_argument("--starter", action="store_true")
    s.add_argument("--bundle", type=int)
    sh = sub.add_parser("show")
    sh.add_argument("prompt")
    f = sub.add_parser("fill")
    f.add_argument("prompt")
    f.add_argument("--var", action="append")
    f.add_argument("--values")
    b = sub.add_parser("bundle")
    b.add_argument("number", type=int)
    b.add_argument("--var", action="append")
    b.add_argument("--values")
    b.add_argument("--format", default="text", choices=("text", "json"))
    r = sub.add_parser("render-html")
    r.add_argument("--out")
    a = ap.parse_args(argv)
    cat = load_catalog()
    try:
        if a.cmd == "search":
            for p in search(cat, a.keyword, domain=a.domain, role=a.role, category=a.category, subcategory=a.subcategory,
                            scope=a.scope, input_mode=a.input_mode, starter=True if a.starter else None, bundle=a.bundle):
                print(f"{p.prompt_code}\t{p.prompt_id}\t{p.domain}\t{p.role}\t{p.title}")
        elif a.cmd == "show":
            res = resolve(cat, a.prompt)
            p = res.prompt
            if res.via == "MERGED_INTO":
                print(f"# {a.prompt} was MERGED_INTO {p.prompt_id}: {res.migration.note}")
            print(f"{p.prompt_code} — {p.title}\n{p.prompt_id} · {p.domain} · {p.role} · {p.content_version}\n{p.purpose}\n")
            for v in variable_specs(p):
                print(f"  {{{{{v.name}}}}}\t{'required' if v.required else 'optional'}\t{v.kind}\t{v.hint}")
            print("\n" + p.body)
        elif a.cmd == "fill":
            print(fill(resolve(cat, a.prompt).prompt, _values(a)))
        elif a.cmd == "bundle":
            bundle = next((x for x in cat.bundles if x.number == a.number), None)
            if bundle is None:
                raise SearchFilterError(f"unknown bundle {a.number}")
            vals = _values(a)
            if not vals:
                print(f"Bundle {bundle.number}. {bundle.name}: {' -> '.join(bundle.prompt_ids)}")
                for v in bundle_variables(cat, bundle.number):
                    print(f"  {{{{{v.name}}}}}\t{'required' if v.required else 'optional'}\t{v.kind}")
                return 0
            print(export(cat, bundle.prompt_ids, vals, a.format))
        elif a.cmd == "render-html":
            print(write_html(Path(a.out) if a.out else None, cat))
    except (VariableFillError, RetiredPromptError, SearchFilterError, KeyError) as e:
        print(f"FAIL_CLOSED: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
