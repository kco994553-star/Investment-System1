"""FPIA derivation: everything FPIA knows about Track C is derived here from the authenticated
reference trees, never listed in FPIA.

* Frozen tools are parsed by AST with each name bound to its role (anchors, protection predicates,
  modification allowlists, admitted-new predicates, evidence dictionary, result key, audit call).
  Predicates are evaluated by a small closed evaluator; any unknown shape raises ShapeError, which
  callers report as NOT_RUN (never as PASS).
* Python import resolution is simulated over git trees (FileFinder order, regular packages,
  namespace packages, extension/source/bytecode suffixes) for shadowing and closure checks.
* __file__-relative data paths are resolved symbolically from AST.

Discovery anchors (the only repository paths FPIA names) are the constants below.
"""
from __future__ import annotations

import ast
import fnmatch
import importlib.machinery as machinery
import json
import re
import shlex
import sys

# ---- discovery anchors ------------------------------------------------------------------
TRACK_C_WORKFLOW = ".github/workflows/track-c-evl-validation.yml"
WORKFLOW_DIR = ".github/workflows/"
TOOL_GLOB = "implementation/tools/track_c_*acceptance*.py"
TOOL_INVOKED_RE = re.compile(r"(?:^|\s)(tools/track_c_[A-Za-z0-9_]+\.py)\b")
RECORD_GLOB = "implementation/reports/track_c_*.json"
CI_LOG_GLOB = "implementation/reports/track_c_*ci_log*.txt"
IMPL = "implementation"
# Import roots used by the Track C workflow steps and the v2 replay (cwd implementation;
# PYTHONPATH=src for pytest, src:. plus the script directory for tools).
STATIC_ROOTS = ("implementation/tools", "implementation/src", "implementation")

EVIDENCE_LINE_RE = re.compile(r"^(\d{4}-\d\d-\d\dT[0-9:.]+Z )?(TRACK_C_[A-Z0-9_]*EVIDENCE)=(.*)$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ShapeError(Exception):
    """A tool, record or source does not have a shape FPIA can bind; reported as NOT_RUN."""


# ---- small helpers ------------------------------------------------------------------------
def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def glob_match(path, pattern):
    return fnmatch.fnmatchcase(path, pattern)


def parse_py(data: bytes, name="<tree>"):
    try:
        return ast.parse(data, filename=name)
    except (SyntaxError, ValueError) as exc:
        raise ShapeError("unparseable python %s: %s" % (name, exc))


# ---- closed predicate evaluator ------------------------------------------------------------
class Predicate:
    """A predicate over a path variable, taken from a tool's AST.

    ``membership`` names the baseline variables whose ``p (not) in <var>`` test is treated as the
    path's newness (True = p is new relative to that baseline)."""

    def __init__(self, expr, var, consts, membership=(), negate=False, label=""):
        self.expr, self.var, self.consts = expr, var, consts
        self.membership = set(membership)
        self.negate = negate
        self.label = label
        self.prefixes, self.literals = set(), set()
        self._collect(expr)
        self("__fpia_shape_probe__")  # shape check: evaluating once raises ShapeError on unknown nodes

    def _collection(self, node):
        if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
            out = []
            for elt in node.elts:
                if not (isinstance(elt, ast.Constant) and isinstance(elt.value, str)):
                    raise ShapeError("non-literal collection element in " + self.label)
                out.append(elt.value)
            return out
        if isinstance(node, ast.Name) and node.id in self.consts:
            value = self.consts[node.id]
            if isinstance(value, str):
                return [value]
            return list(value)
        raise ShapeError("unsupported collection in " + self.label + ": " + ast.dump(node)[:120])

    def _str(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name) and isinstance(self.consts.get(node.id), str):
            return self.consts[node.id]
        raise ShapeError("unsupported string operand in " + self.label)

    def _is_var(self, node):
        return isinstance(node, ast.Name) and node.id == self.var

    def _collect(self, node):
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "startswith" \
                    and self._is_var(n.func.value):
                arg = n.args[0]
                vals = self._collection(arg) if isinstance(arg, (ast.Tuple, ast.List)) else [self._str(arg)]
                self.prefixes.update(vals)
            elif isinstance(n, ast.Compare) and len(n.ops) == 1 and self._is_var(n.left):
                right = n.comparators[0]
                if isinstance(right, ast.Name) and right.id in self.membership:
                    continue
                if isinstance(n.ops[0], (ast.In, ast.NotIn)):
                    self.literals.update(self._collection(right))
                elif isinstance(n.ops[0], (ast.Eq, ast.NotEq)):
                    self.literals.add(self._str(right))

    def _eval(self, node, p):
        if isinstance(node, ast.BoolOp):
            vals = [self._eval(v, p) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not self._eval(node.operand, p)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "startswith" \
                and self._is_var(node.func.value) and len(node.args) == 1 and not node.keywords:
            arg = node.args[0]
            vals = self._collection(arg) if isinstance(arg, (ast.Tuple, ast.List)) else [self._str(arg)]
            return p.startswith(tuple(vals))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and self._is_var(node.left):
            op, right = node.ops[0], node.comparators[0]
            if isinstance(right, ast.Name) and right.id in self.membership:
                if isinstance(op, ast.NotIn):
                    return True
                if isinstance(op, ast.In):
                    return False
                raise ShapeError("unsupported baseline test in " + self.label)
            if isinstance(op, (ast.In, ast.NotIn)):
                inside = p in self._collection(right)
                return inside if isinstance(op, ast.In) else not inside
            if isinstance(op, (ast.Eq, ast.NotEq)):
                equal = p == self._str(right)
                return equal if isinstance(op, ast.Eq) else not equal
        raise ShapeError("unsupported predicate node in %s: %s" % (self.label, ast.dump(node)[:160]))

    def __call__(self, p):
        value = self._eval(self.expr, p)
        return (not value) if self.negate else value


# ---- tool model ------------------------------------------------------------------------------
KIND_BY_PREFIX = {"TRACK_C_C6_EVIDENCE": "C6", "TRACK_C_C7_EVIDENCE": "C7",
                  "TRACK_C_C8_PARTIAL_EVIDENCE": "C8_PARTIAL"}
# Role names bound per kind: (baseline anchor variable -> constant), predicates, allowlists.
ROLE_SPEC = {
    "C6": {"audit": "boundary_audit", "frozen": "frozen", "allowed": "allowed",
           "admit": "unexpected_new", "anchors": ("CANONICAL", "START", "BRANCH")},
    "C7": {"audit": "preservation", "frozen": "frozen", "allowed": "allowed_existing",
           "admit": "unexpected_new", "anchors": ("START",)},
    "C8_PARTIAL": {"audit": "preservation", "frozen": "frozen", "allowed": "allowed",
                   "admit": "unauthorized", "anchors": ("BASE",)},
}


def _module_consts(tree):
    consts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name, value = node.targets[0].id, node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                consts[name] = value.value
            elif isinstance(value, (ast.List, ast.Tuple)) and all(
                    isinstance(e, ast.Constant) and isinstance(e.value, str) for e in value.elts):
                consts[name] = tuple(e.value for e in value.elts)
    return consts


def _main_block(tree):
    for node in tree.body:
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
                and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__":
            return node
    return None


def _flatten_stmts(stmts):
    for st in stmts:
        yield st


class ToolModel:
    """AST model of one frozen acceptance tool (one blob)."""

    def __init__(self, path, data: bytes):
        self.path = path
        self.tree = parse_py(data, path)
        self.consts = _module_consts(self.tree)
        self.functions = {n.name: n for n in self.tree.body if isinstance(n, ast.FunctionDef)}
        self.imports = {}
        for n in self.tree.body:
            if isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                for a in n.names:
                    self.imports[a.asname or a.name] = (n.module, a.name)
            elif isinstance(n, ast.Import):
                for a in n.names:
                    self.imports[a.asname or a.name.split(".")[0]] = (a.name, None)
        main = _main_block(self.tree)
        if main is None:
            raise ShapeError("no __main__ block in " + path)
        self.main = main
        self._bind_main()
        self.kind = KIND_BY_PREFIX.get(self.prefix)
        if self.kind is None:
            raise ShapeError("unbound evidence prefix %s in %s" % (self.prefix, path))
        self._bind_roles()

    # main block: print prefix, evidence dict, result key, audit call, fixture call, out dir
    def _bind_main(self):
        prints = []
        assigns = {}
        for node in ast.walk(self.main):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print" \
                    and len(node.args) == 1 and isinstance(node.args[0], ast.BinOp) \
                    and isinstance(node.args[0].left, ast.Constant) and isinstance(node.args[0].left.value, str) \
                    and node.args[0].left.value.startswith("TRACK_C_") and node.args[0].left.value.endswith("_EVIDENCE="):
                dump = node.args[0].right
                if not (isinstance(dump, ast.Call) and isinstance(dump.func, ast.Attribute) and dump.func.attr == "dumps"
                        and dump.args and isinstance(dump.args[0], ast.Name)):
                    raise ShapeError("unexpected evidence print shape in " + self.path)
                prints.append((node.args[0].left.value[:-1], dump.args[0].id))
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                assigns.setdefault(node.targets[0].id, []).append(node)
        if len(prints) != 1:
            raise ShapeError("expected exactly one evidence print in %s, found %d" % (self.path, len(prints)))
        self.prefix, self.evidence_var = prints[0]
        ev = assigns.get(self.evidence_var, [])
        if len(ev) != 1 or not isinstance(ev[0].value, ast.Dict):
            raise ShapeError("evidence variable is not a single dict literal in " + self.path)
        self.evidence_dict = ev[0].value
        keys = []
        for k in self.evidence_dict.keys:
            if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
                raise ShapeError("non-literal evidence key in " + self.path)
            keys.append(k.value)
        self.evidence_keys = frozenset(keys)
        # fixture call: an assignment from a call to a name imported from a non-tool module
        self.fixture = None
        self.audit_call = None
        for name, nodes in assigns.items():
            for node in nodes:
                v = node.value
                if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id in self.imports:
                    module = self.imports[v.func.id][0]
                    if module.startswith("tools."):
                        continue
                    if self.fixture is None and module.startswith("tests."):
                        self.fixture = {"var": name, "module": module, "function": self.imports[v.func.id][1],
                                        "lineno": node.lineno}
                if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and not v.args \
                        and (v.func.id in self.functions or (v.func.id in self.imports
                                                             and self.imports[v.func.id][0].startswith("tools."))):
                    if self.audit_call is None:
                        self.audit_call = {"var": name, "function": v.func.id, "lineno": node.lineno}
        if self.fixture is None or self.audit_call is None:
            raise ShapeError("fixture or audit call not found in main block of " + self.path)
        self.result_key = None
        self.audit_key = None
        for k, v in zip(self.evidence_dict.keys, self.evidence_dict.values):
            if isinstance(v, ast.Name) and v.id == self.fixture["var"]:
                self.result_key = k.value
            if isinstance(v, ast.Name) and v.id == self.audit_call["var"]:
                self.audit_key = k.value
        self.out_dirs = sorted({n.args[0].value for n in ast.walk(self.main)
                                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "Path"
                                and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)})

    def _assign_in(self, fn, name):
        found = [n for n in ast.walk(fn) if isinstance(n, ast.Assign) and len(n.targets) == 1
                 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
        if len(found) != 1:
            raise ShapeError("role %s not bound exactly once in %s" % (name, self.path))
        return found[0].value

    def _baseline_vars(self, fn):
        """{var: anchor-constant-name or 'HEAD'} from ``a, b = blobs(X), blobs('HEAD')`` forms."""
        out = {}
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign) and len(n.targets) == 1:
                t, v = n.targets[0], n.value
                pairs = []
                if isinstance(t, ast.Tuple) and isinstance(v, ast.Tuple) and len(t.elts) == len(v.elts):
                    pairs = list(zip(t.elts, v.elts))
                elif isinstance(t, ast.Name):
                    pairs = [(t, v)]
                for tt, vv in pairs:
                    if isinstance(tt, ast.Name) and isinstance(vv, ast.Call) and isinstance(vv.func, ast.Name) \
                            and vv.func.id == "blobs" and len(vv.args) == 1:
                        a = vv.args[0]
                        if isinstance(a, ast.Name) and a.id in self.consts:
                            out[tt.id] = a.id
                        elif isinstance(a, ast.Constant) and a.value == "HEAD":
                            out[tt.id] = "HEAD"
                        else:
                            raise ShapeError("unexpected baseline expression in " + self.path)
        return out

    def _comp_pred(self, value, label, baselines, negate=False):
        if not (isinstance(value, ast.ListComp) and len(value.generators) == 1):
            raise ShapeError("role %s is not a list comprehension in %s" % (label, self.path))
        gen = value.generators[0]
        if not (isinstance(gen.target, ast.Name) and isinstance(gen.iter, ast.Name) and len(gen.ifs) == 1):
            raise ShapeError("role %s comprehension shape in %s" % (label, self.path))
        return gen.iter.id, Predicate(gen.ifs[0], gen.target.id, self.consts, membership=baselines,
                                      negate=negate, label=self.path + ":" + label)

    def _bind_roles(self):
        spec = ROLE_SPEC[self.kind]
        for a in spec["anchors"]:
            if a not in self.consts:
                raise ShapeError("anchor %s missing in %s" % (a, self.path))
        fn = self.functions.get(spec["audit"])
        if fn is None:
            raise ShapeError("audit function %s missing in %s" % (spec["audit"], self.path))
        self.audit_function = spec["audit"]
        bases = self._baseline_vars(fn)
        if "HEAD" not in bases.values():
            raise ShapeError("current-tree binding missing in " + self.path)
        self.baselines = {v: c for v, c in bases.items() if c != "HEAD"}
        cur = [v for v, c in bases.items() if c == "HEAD"][0]
        # frozen predicate over a baseline
        it, self.frozen = self._comp_pred(self._assign_in(fn, spec["frozen"]), "frozen", ())
        if it not in self.baselines:
            raise ShapeError("frozen predicate not over a baseline in " + self.path)
        self.frozen_anchor = self.baselines[it]
        # allowlist
        allowed = self._assign_in(fn, spec["allowed"])
        if isinstance(allowed, ast.Set):
            self.allowed = frozenset(e.value for e in allowed.elts
                                     if isinstance(e, ast.Constant) and isinstance(e.value, str))
            if len(self.allowed) != len(allowed.elts):
                raise ShapeError("non-literal allowlist in " + self.path)
        elif isinstance(allowed, ast.BinOp) and isinstance(allowed.op, ast.BitOr):
            items = []
            for side in (allowed.left, allowed.right):
                if isinstance(side, ast.Call) and isinstance(side.func, ast.Name) and side.func.id == "set" \
                        and len(side.args) == 1 and isinstance(side.args[0], ast.Name) \
                        and isinstance(self.consts.get(side.args[0].id), tuple):
                    items.extend(self.consts[side.args[0].id])
                else:
                    raise ShapeError("allowlist union shape in " + self.path)
            self.allowed = frozenset(items)
        else:
            raise ShapeError("allowlist shape in " + self.path)
        # which baseline the allowlist governs: the comprehension computing modified paths
        self.allowed_anchor = None
        for n in ast.walk(fn):
            if isinstance(n, ast.ListComp) and len(n.generators) == 1:
                it = n.generators[0].iter
                if isinstance(it, ast.Call) and isinstance(it.func, ast.Attribute) and it.func.attr == "items":
                    it = it.func.value
                if not (isinstance(it, ast.Name) and it.id in self.baselines):
                    continue
                src = ast.dump(n.generators[0].ifs[0]) if n.generators[0].ifs else ""
                if "'%s'" % spec["allowed"] in src:
                    self.allowed_anchor = self.baselines[it.id]
        if self.allowed_anchor is None:
            raise ShapeError("allowlist baseline not found in " + self.path)
        # admitted-new predicate
        admit_value = self._assign_in(fn, spec["admit"])
        it, unexpected = self._comp_pred(admit_value, "admit", tuple(self.baselines))
        if it == cur:
            membership_ok = any(isinstance(n, ast.Compare) and isinstance(n.ops[0], ast.NotIn)
                                and isinstance(n.comparators[0], ast.Name) and n.comparators[0].id in self.baselines
                                for n in ast.walk(admit_value.generators[0].ifs[0]))
            if not membership_ok:
                raise ShapeError("admitted-new predicate lacks a newness test in " + self.path)
            self.admit_anchor = [self.baselines[n.comparators[0].id] for n in ast.walk(admit_value.generators[0].ifs[0])
                                 if isinstance(n, ast.Compare) and isinstance(n.comparators[0], ast.Name)
                                 and n.comparators[0].id in self.baselines][0]
        else:
            # ``added = [p for p in current if p not in baseline]`` then ``[p for p in added if ...]``
            added = self._assign_in(fn, it)
            ait, _ = self._comp_pred(added, "added", tuple(self.baselines))
            if ait != cur:
                raise ShapeError("admitted-new source shape in " + self.path)
            self.admit_anchor = [self.baselines[n.comparators[0].id] for n in ast.walk(added.generators[0].ifs[0])
                                 if isinstance(n, ast.Compare) and isinstance(n.comparators[0], ast.Name)
                                 and n.comparators[0].id in self.baselines][0]
        self.unexpected_new = unexpected
        self.admit_prefixes = frozenset(unexpected.prefixes)
        self.admit_literals = frozenset(unexpected.literals)
        # append-only overlays (C8): ``for p in OVERLAYS: ... startswith(before)``
        self.append_only = frozenset()
        for n in ast.walk(fn):
            if isinstance(n, ast.For) and isinstance(n.iter, ast.Name) and isinstance(self.consts.get(n.iter.id), tuple):
                if "startswith" in ast.dump(n):
                    self.append_only = frozenset(self.consts[n.iter.id])
        # strict-to-start rules (C6.e/C6.f) are subsumed by the src/tests protections of later
        # tools; their literal targets are recorded for the subsumption check.
        self.start_equal_literals = sorted({n.args[0].value for n in ast.walk(fn)
                                            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                                            and n.func.attr == "get" and n.args and isinstance(n.args[0], ast.Constant)
                                            and isinstance(n.args[0].value, str)})
        self.start_equal_prefixes = sorted({c.value for n in ast.walk(fn) if isinstance(n, ast.For)
                                            and isinstance(n.iter, ast.Name) and n.iter.id == spec["allowed"]
                                            for c in ast.walk(n) if isinstance(c, ast.Constant)
                                            and isinstance(c.value, str) and c.value.endswith("/")})
        # canonical pin: a module constant compared with ``git('rev-parse', 'origin/...')``
        self.branch = self.consts.get("BRANCH")
        self.hex_constants = {k: v for k, v in self.consts.items() if isinstance(v, str) and HEX40.match(v)}

    def admitted_new(self, p):
        return not self.unexpected_new(p)

    def raise_messages(self):
        """Literal prefixes of every ValueError/SystemExit/IntegrityFailure message in the tool."""
        out = []
        for n in ast.walk(self.tree):
            if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call) and n.exc.args:
                a = n.exc.args[0]
                while isinstance(a, ast.BinOp):
                    a = a.left
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    out.append(a.value)
        return out

    def summary(self):
        return {"path": self.path, "kind": self.kind, "prefix": self.prefix,
                "audit_function": self.audit_function, "fixture": self.fixture,
                "result_key": self.result_key, "audit_key": self.audit_key,
                "evidence_keys": sorted(self.evidence_keys),
                "anchors": {k: self.consts[k] for k in ROLE_SPEC[self.kind]["anchors"]},
                "baselines": dict(sorted(self.baselines.items())),
                "allowed": sorted(self.allowed), "allowed_anchor": self.allowed_anchor,
                "frozen_prefixes": sorted(self.frozen.prefixes), "frozen_anchor": self.frozen_anchor,
                "admit_prefixes": sorted(self.admit_prefixes), "admit_literals": sorted(self.admit_literals),
                "admit_anchor": self.admit_anchor, "append_only": sorted(self.append_only),
                "out_dirs": self.out_dirs}


def boundary_paths(tools_by_kind):
    """Exact JSON paths of boundary dictionaries inside each kind's evidence (rv2 7c)."""
    out = {}
    for kind, tool in tools_by_kind.items():
        paths = []
        if tool.audit_key is None:
            out[kind] = paths
            continue
        if tool.audit_call["function"] == "boundary_audit":
            paths.append((tool.audit_key,))
        else:
            fn = tool.functions.get(tool.audit_call["function"])
            if fn is not None:
                for ret in [n for n in ast.walk(fn) if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict)]:
                    for k, v in zip(ret.value.keys, ret.value.values):
                        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "boundary_audit" \
                                and isinstance(k, ast.Constant):
                            paths.append((tool.audit_key, k.value))
        out[kind] = paths
    return out


STRIP_KEYS = ("tested_head", "merge_base", "ahead", "behind")


def strip_evidence(evidence, paths):
    """Remove ONLY top-level tested_head and STRIP_KEYS inside the exact boundary paths."""
    import copy
    e = copy.deepcopy(evidence)
    removed = []
    if isinstance(e, dict) and "tested_head" in e:
        e.pop("tested_head")
        removed.append("/tested_head")
    for path in paths:
        node = e
        for part in path:
            node = node.get(part) if isinstance(node, dict) else None
        if isinstance(node, dict):
            for k in STRIP_KEYS:
                if k in node:
                    node.pop(k)
                    removed.append("/" + "/".join(path) + "/" + k)
    return e, removed


# ---- workflow parsing -------------------------------------------------------------------------
def parse_workflow(text):
    """Return {name, jobs:[ids], job_names:[...], steps:[{name, run, wd}], python_version, defaults_wd}."""
    lines = text.splitlines()
    name = None
    for line in lines:
        m = re.match(r"^name:\s*(.+?)\s*$", line)
        if m:
            name = m.group(1).strip("'\"")
            break
    jobs, job_names = [], []
    job_indent = None
    in_jobs = False
    for line in lines:
        if re.match(r"^jobs:\s*$", line):
            in_jobs = True
            continue
        if in_jobs:
            if line and not line.startswith(" ") and not line.startswith("#"):
                in_jobs = False
                continue
            m = re.match(r"^( +)([A-Za-z0-9_-]+):\s*$", line)
            if m and (job_indent is None or len(m.group(1)) == job_indent):
                if job_indent is None:
                    job_indent = len(m.group(1))
                jobs.append(m.group(2))
                continue
            m = re.match(r"^( +)name:\s*(.+?)\s*$", line)
            if m and job_indent is not None and len(m.group(1)) == job_indent + 2:
                job_names.append(m.group(2).strip("'\""))
    steps = []
    defaults_wd = None
    m = re.search(r"defaults:\s*\n\s+run:\s*\n\s+working-directory:\s*(\S+)", text)
    if m:
        defaults_wd = m.group(1).strip("'\"")
    # step blocks: list items under a ``steps:`` key; each block runs until the next item at the
    # same indentation or a dedent
    i = 0
    while i < len(lines):
        m = re.match(r"^(\s*)steps:\s*$", lines[i])
        if not m:
            i += 1
            continue
        base = len(m.group(1))
        j = i + 1
        item_indent = None
        block = None
        blocks = []
        while j < len(lines):
            line = lines[j]
            if line.strip() and not line.lstrip().startswith("#"):
                ind = len(line) - len(line.lstrip())
                if ind <= base:
                    break
                mm = re.match(r"^(\s*)- ", line)
                if mm and (item_indent is None or len(mm.group(1)) == item_indent):
                    item_indent = len(mm.group(1))
                    block = [line[:item_indent] + "  " + line[item_indent + 2:]]
                    blocks.append(block)
                elif block is not None:
                    block.append(line)
            elif block is not None:
                block.append(line)
            j += 1
        for blk in blocks:
            sname, run, wd = None, None, None
            k = 0
            key_indent = len(blk[0]) - len(blk[0].lstrip())
            while k < len(blk):
                line = blk[k]
                ind = len(line) - len(line.lstrip())
                mm = re.match(r"^\s*([A-Za-z_-]+):\s*(.*)$", line)
                if mm and ind == key_indent:
                    key, val = mm.group(1), mm.group(2)
                    if key == "name":
                        sname = val.strip().strip("'\"")
                    elif key == "working-directory":
                        wd = val.strip().strip("'\"")
                    elif key == "run":
                        if val.strip() in ("|", ">", "|-", ">-"):
                            body = []
                            k += 1
                            while k < len(blk) and (not blk[k].strip() or len(blk[k]) - len(blk[k].lstrip()) > key_indent):
                                body.append(blk[k].strip())
                                k += 1
                            run = "\n".join(b for b in body if b)
                            continue
                        run = val.strip()
                k += 1
            if run:
                steps.append({"name": sname, "run": run, "wd": wd})
        i = j
    py = None
    m = re.search(r"python-version:\s*['\"]?([0-9.]+)['\"]?", text)
    if m:
        py = m.group(1)
    return {"name": name, "jobs": jobs, "job_names": job_names, "steps": steps,
            "python_version": py, "defaults_wd": defaults_wd}


def classify_step(run):
    """('pytest', env, args) | ('tool', env, script) | ('pip', pins) | ('git', None) | ('other', run)."""
    try:
        tokens = shlex.split(run, comments=False)
    except ValueError:
        return ("other", run, None)
    env = {}
    while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
        k, v = tokens.pop(0).split("=", 1)
        env[k] = v
    if not tokens:
        return ("other", run, None)
    if tokens[:3] == ["python", "-m", "pytest"]:
        return ("pytest", env, tokens[3:])
    if tokens[:4] == ["python", "-m", "pip", "install"]:
        return ("pip", env, tokens[4:])
    if tokens[0] == "python" and len(tokens) >= 2 and tokens[1].endswith(".py"):
        return ("tool", env, tokens[1:])
    if tokens[0] == "git":
        return ("git", env, tokens)
    return ("other", env, tokens)


def pins_from(tokens):
    pins = {}
    for t in tokens or ():
        m = re.match(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)$", t)
        if m:
            pins[m.group(1).lower()] = m.group(2)
        elif re.match(r"^[A-Za-z0-9_.-]+$", t):
            pins[t.lower()] = None
    return pins


def expand_glob(pattern, files, cwd):
    """bash-like expansion of a relative glob against the tree's file set (sorted; no match keeps
    the literal word, as bash does without nullglob)."""
    full = (cwd.rstrip("/") + "/" + pattern) if cwd else pattern
    if not any(c in pattern for c in "*?["):
        return [pattern]
    hits = sorted(p for p in files if fnmatch.fnmatchcase(p, full) and "/" not in p[len(full.rsplit("/", 1)[0]) + 1:])
    if not hits:
        return [pattern]
    prefix = cwd.rstrip("/") + "/" if cwd else ""
    return [h[len(prefix):] for h in hits]


# ---- python import simulation ----------------------------------------------------------------------
EXT_SUFFIXES = tuple(machinery.EXTENSION_SUFFIXES)
SRC_SUFFIXES = tuple(machinery.SOURCE_SUFFIXES)
BC_SUFFIXES = tuple(machinery.BYTECODE_SUFFIXES)
LOADER_ORDER = EXT_SUFFIXES + SRC_SUFFIXES + BC_SUFFIXES
ALL_SUFFIXES = tuple(sorted(set(machinery.all_suffixes()) | {".pyc", ".pyo", ".pyd"}, key=len, reverse=True))
NON_SOURCE_SUFFIXES = tuple(s for s in ALL_SUFFIXES if s not in SRC_SUFFIXES)


def strip_suffix(name):
    for s in ALL_SUFFIXES:
        if name.endswith(s) and len(name) > len(s):
            return name[:-len(s)], s
    return None, None


def dotted(path, root):
    """Dotted module name of ``path`` under ``root`` (longest suffix stripped; __init__ -> package)."""
    if not path.startswith(root.rstrip("/") + "/"):
        return None
    rel = path[len(root.rstrip("/")) + 1:]
    parts = rel.split("/")
    stem, suffix = strip_suffix(parts[-1])
    if stem is None:
        return None
    parts[-1] = stem
    if "__pycache__" in parts:
        return None
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts or not all(p.isidentifier() for p in parts):
        return None
    return ".".join(parts)


def dir_dotted(d, root):
    if not d.startswith(root.rstrip("/") + "/"):
        return None
    parts = d[len(root.rstrip("/")) + 1:].split("/")
    if not all(p.isidentifier() for p in parts):
        return None
    return ".".join(parts)


def all_dirs(files):
    out = set()
    for p in files:
        parts = p.split("/")
        for i in range(1, len(parts)):
            out.add("/".join(parts[:i]))
    return out


def frozen_or_builtin(top):
    if top in sys.builtin_module_names:
        return "builtin"
    try:
        if machinery.FrozenImporter.find_spec(top) is not None:
            return "frozen"
    except Exception:
        pass
    return None


class ImportSim:
    """Simulated PathFinder/FileFinder resolution over a git tree's file set."""

    def __init__(self, files, roots):
        self.files = set(files)
        self.dirs = all_dirs(self.files)
        self.roots = list(roots)

    def _find_in(self, directory, tail):
        base = directory + "/" + tail if directory else tail
        if base in self.dirs:
            for s in LOADER_ORDER:
                if base + "/__init__" + s in self.files:
                    return ("package", base + "/__init__" + s, [base])
            ns = True
        else:
            ns = False
        for s in LOADER_ORDER:
            if base + s in self.files:
                return ("module", base + s, None)
        if ns:
            return ("namespace", None, [base])
        return None

    def find(self, name):
        parts = name.split(".")
        kind = frozen_or_builtin(parts[0])
        if kind:
            return (kind, None)
        search = self.roots
        result = None
        for i, part in enumerate(parts):
            portions = []
            found = None
            for d in search:
                r = self._find_in(d, part)
                if r is None:
                    continue
                if r[0] == "namespace":
                    portions.extend(r[2])
                    continue
                found = r
                break
            if found is None and portions:
                found = ("namespace", None, portions)
            if found is None:
                return ("outside", None) if i == 0 else ("missing", None)
            result = found
            if i < len(parts) - 1:
                if found[0] == "module":
                    return ("attribute_of_module", found[1])
                search = found[2]
        return (result[0], result[1] if result[0] != "namespace" else tuple(result[2]))


def module_imports(data: bytes, path, roots):
    """Imported dotted names (absolute, relative resolved), constant dynamic imports, parse flag."""
    try:
        tree = ast.parse(data, filename=path)
    except (SyntaxError, ValueError):
        return None
    own = None
    for root in roots:
        d = dotted(path, root)
        if d is not None:
            own = d
            break
    is_pkg = path.rsplit("/", 1)[-1].startswith("__init__.")
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            if n.level:
                if own is None:
                    continue
                base = own.split(".") if is_pkg else own.split(".")[:-1]
                if n.level > 1:
                    base = base[:-(n.level - 1)]
                mod = ".".join(base + ([n.module] if n.module else []))
            else:
                mod = n.module
            if not mod:
                continue
            names.add(mod)
            names.update(mod + "." + a.name for a in n.names if a.name != "*")
        elif isinstance(n, ast.Call):
            f = n.func
            fname = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
            if fname in ("import_module", "__import__", "run_module") and n.args \
                    and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                names.add(n.args[0].value)
    return names


def name_prefixes(name):
    parts = name.split(".")
    return [".".join(parts[:i]) for i in range(1, len(parts) + 1)]


# ---- __file__-relative data paths ------------------------------------------------------------
class _PathVal(str):
    pass


def file_relative_paths(data: bytes, path):
    """Repo-relative paths built from ``Path(__file__)`` expressions in a module (symbolic)."""
    try:
        tree = ast.parse(data, filename=path)
    except (SyntaxError, ValueError):
        return [], []
    env = {}

    def norm(parts):
        out = []
        for part in parts:
            if part in ("", "."):
                continue
            if part == "..":
                if not out:
                    return None
                out.pop()
            else:
                out.append(part)
        return "/".join(out)

    def ev(node):
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Call):
            f = node.func
            fname = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
            if fname in ("Path", "PurePath", "PosixPath") and len(node.args) == 1 \
                    and isinstance(node.args[0], ast.Name) and node.args[0].id == "__file__":
                return _PathVal(path)
            if isinstance(f, ast.Attribute) and f.attr in ("resolve", "absolute") and not node.args:
                return ev(f.value)
            return None
        if isinstance(node, ast.Attribute) and node.attr == "parent":
            v = ev(node.value)
            if isinstance(v, _PathVal):
                return _PathVal(v.rsplit("/", 1)[0] if "/" in v else "")
            return None
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "parents":
            v = ev(node.value.value)
            idx = node.slice
            if isinstance(v, _PathVal) and isinstance(idx, ast.Constant) and isinstance(idx.value, int):
                parts = v.split("/")
                keep = len(parts) - 1 - idx.value
                if keep < 0:
                    return None
                return _PathVal("/".join(parts[:keep]))
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left, right = ev(node.left), ev(node.right)
            if isinstance(left, _PathVal) and isinstance(right, str) and not isinstance(right, _PathVal):
                joined = norm(left.split("/") + right.split("/"))
                return _PathVal(joined) if joined is not None else None
            return None
        return None

    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            v = ev(node.value)
            if v is not None:
                env[node.targets[0].id] = v
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.BinOp, ast.Subscript, ast.Attribute, ast.Call, ast.Name)):
            v = ev(node)
            if isinstance(v, _PathVal):
                out.add(str(v))
    # tuples of (path, blob) and module constants holding 40-hex blob pins
    pins = sorted({n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                   and isinstance(n.value, str) and HEX40.match(n.value)})
    return sorted(out), pins


# ---- code identity sites -------------------------------------------------------------------------
def _rglob_py(node):
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "rglob" \
                and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "*.py":
            return True
    return False


def code_identity_sites(data: bytes, path):
    """[(kind, name)] where kind is 'attribute' (module-level assignment) or 'call' (zero-argument
    function). Raises ShapeError for any other rglob('*.py') location (unsupported site kind)."""
    tree = parse_py(data, path)
    sites = []
    covered = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and _rglob_py(node):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                sites.append(("attribute", node.targets[0].id))
                covered.update(id(n) for n in ast.walk(node))
            else:
                raise ShapeError("unsupported code-identity site (assignment target) in " + path)
        elif isinstance(node, ast.FunctionDef) and _rglob_py(node):
            a = node.args
            if a.args or a.posonlyargs or a.kwonlyargs or a.vararg or a.kwarg:
                raise ShapeError("unsupported code-identity site (function with arguments) in " + path)
            sites.append(("call", node.name))
            covered.update(id(n) for n in ast.walk(node))
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "rglob" \
                and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "*.py" and id(n) not in covered:
            raise ShapeError("unsupported code-identity site kind in " + path)
    return sites


def site_root(data: bytes, path):
    """Repo-relative directory enumerated by the site's ``<X>.rglob('*.py')`` (symbolic)."""
    tree = parse_py(data, path)
    env = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            v = _eval_path(node.value, env, path)
            if v is not None:
                env[node.targets[0].id] = v
    roots = set()
    for scope in [tree] + [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        local = dict(env)
        body = scope.body
        for st in body:
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                v = _eval_path(st.value, local, path)
                if v is not None:
                    local[st.targets[0].id] = v
        for n in ast.walk(scope):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "rglob" \
                    and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "*.py":
                v = _eval_path(n.func.value, local, path)
                if isinstance(v, _PathVal):
                    roots.add(str(v))
    if len(roots) != 1:
        raise ShapeError("code-identity site root not uniquely derivable in " + path)
    return roots.pop()


def _eval_path(node, env, path):
    def norm(parts):
        out = []
        for part in parts:
            if part in ("", "."):
                continue
            if part == "..":
                if not out:
                    return None
                out.pop()
            else:
                out.append(part)
        return "/".join(out)

    def ev(node):
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Call):
            f = node.func
            fname = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
            if fname in ("Path", "PurePath", "PosixPath") and len(node.args) == 1 \
                    and isinstance(node.args[0], ast.Name) and node.args[0].id == "__file__":
                return _PathVal(path)
            if isinstance(f, ast.Attribute) and f.attr in ("resolve", "absolute") and not node.args:
                return ev(f.value)
            return None
        if isinstance(node, ast.Attribute) and node.attr == "parent":
            v = ev(node.value)
            if isinstance(v, _PathVal):
                return _PathVal(v.rsplit("/", 1)[0] if "/" in v else "")
            return None
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "parents":
            v = ev(node.value.value)
            idx = node.slice
            if isinstance(v, _PathVal) and isinstance(idx, ast.Constant) and isinstance(idx.value, int):
                parts = v.split("/")
                keep = len(parts) - 1 - idx.value
                if keep < 0:
                    return None
                return _PathVal("/".join(parts[:keep]))
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left, right = ev(node.left), ev(node.right)
            if isinstance(left, _PathVal) and isinstance(right, str) and not isinstance(right, _PathVal):
                joined = norm(left.split("/") + right.split("/"))
                return _PathVal(joined) if joined is not None else None
            return None
        return None
    return ev(node)


def site_importers(data: bytes, path, roots, site_module, site_names):
    """Local names in a module bound by ``from <site_module> import <site_name>``."""
    try:
        tree = ast.parse(data, filename=path)
    except (SyntaxError, ValueError):
        return []
    own = None
    for root in roots:
        own = dotted(path, root)
        if own:
            break
    is_pkg = path.rsplit("/", 1)[-1].startswith("__init__.")
    out = []
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            if n.level:
                if own is None:
                    continue
                base = own.split(".") if is_pkg else own.split(".")[:-1]
                if n.level > 1:
                    base = base[:-(n.level - 1)]
                mod = ".".join(base + ([n.module] if n.module else []))
            else:
                mod = n.module
            if mod == site_module:
                for a in n.names:
                    if a.name in site_names:
                        out.append((a.asname or a.name, a.name))
    return out


# ---- registration-binding validator (AC-09) --------------------------------------------------------
def binding_validator(data: bytes, path, site_function):
    """Find ``if <param>[KEY] != <site_function>(): raise Exc(MSG)`` in a module.

    Returns {function, key, exception, message} or None."""
    tree = parse_py(data, path)
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        for n in ast.walk(fn):
            if isinstance(n, ast.If) and isinstance(n.test, ast.Compare) and len(n.test.ops) == 1 \
                    and isinstance(n.test.ops[0], ast.NotEq) and isinstance(n.test.left, ast.Subscript) \
                    and isinstance(n.test.left.slice, ast.Constant) \
                    and isinstance(n.test.comparators[0], ast.Call) \
                    and isinstance(n.test.comparators[0].func, ast.Name) \
                    and n.test.comparators[0].func.id == site_function and n.body \
                    and isinstance(n.body[0], ast.Raise) and isinstance(n.body[0].exc, ast.Call) \
                    and isinstance(n.body[0].exc.func, ast.Name) and n.body[0].exc.args \
                    and isinstance(n.body[0].exc.args[0], ast.Constant):
                return {"function": fn.name, "key": n.test.left.slice.value,
                        "exception": n.body[0].exc.func.id, "message": n.body[0].exc.args[0].value}
    return None


# ---- JSON helpers for Frozen records -------------------------------------------------------------
def nested_dicts(obj, path=()):
    if isinstance(obj, dict):
        yield path, obj
        for k, v in obj.items():
            yield from nested_dicts(v, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from nested_dicts(v, path + (i,))


def evidence_candidates(record):
    """Embedded tool-evidence candidates: nested (non top-level) dicts with an own 40-hex
    tested_head or a child dict with one; only outermost candidates are kept."""
    cands = []
    for path, d in nested_dicts(record):
        if not path:
            continue
        own = isinstance(d.get("tested_head"), str) and HEX40.match(d["tested_head"])
        child = any(isinstance(v, dict) and isinstance(v.get("tested_head"), str) and HEX40.match(v["tested_head"])
                    for v in d.values())
        if own or child:
            cands.append((path, d))
    outer = [c for c in cands if not any(o[0] != c[0] and c[0][:len(o[0])] == o[0] for o in cands)]
    return outer


def evidence_head(obj):
    """tested_head of an evidence object: own top-level value, else the unique nested value."""
    if isinstance(obj, dict) and isinstance(obj.get("tested_head"), str):
        return obj["tested_head"] if HEX40.match(obj["tested_head"]) else None
    heads = {d["tested_head"] for _, d in nested_dicts(obj)
             if isinstance(d.get("tested_head"), str) and HEX40.match(d["tested_head"])}
    return heads.pop() if len(heads) == 1 else None


def scalar_values(obj):
    out = set()
    for _, d in nested_dicts(obj):
        for v in d.values():
            if isinstance(v, str):
                out.add(v)
    return out


def boundary_dicts(evidence, head):
    return [d for _, d in nested_dicts(evidence) if d.get("tested_head") == head]


def keys_anywhere(obj):
    out = {}
    for _, d in nested_dicts(obj):
        for k, v in d.items():
            out.setdefault(k, []).append(v)
    return out
