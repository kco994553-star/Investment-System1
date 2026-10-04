"""FPIA static checks: projection derivation and identity, provenance, v2 attribution and the
complement (non-Track C) integrity checks. Every check is exact; findings are fail-closed."""
from __future__ import annotations

import fnmatch
import importlib.metadata as metadata
import re
import sys
import unicodedata

try:
    from . import track_c_fpia_derive as fd
except ImportError:
    import track_c_fpia_derive as fd

CONFLICT_MARKER = re.compile(rb"^(<<<<<<< |>>>>>>> |\|\|\|\|\|\|\| )", re.M)
CLASSES = ("FROZEN_TOOL", "STRICT", "NS_OVERLAY", "SHARED_OVERLAY", "INFRA_REPLACE")


def check(cid, status, detail=None, evidence_class=None, **extra):
    out = {"id": cid, "status": status}
    if detail is not None:
        out["detail"] = detail
    if evidence_class:
        out["evidence_class"] = evidence_class
    out.update(extra)
    return out


# ---- projection derivation (AC-14) ----------------------------------------------------------------
class Projection:
    def __init__(self, sb, R, tools, anchor_paths):
        self.sb, self.R = sb, R
        self.tools = tools                      # {path: ToolModel}
        self.by_kind = {}
        for t in tools.values():
            self.by_kind.setdefault(t.kind, []).append(t)
        for kind, lst in self.by_kind.items():
            if len(lst) != 1:
                raise fd.ShapeError("ambiguous tool binding for kind %s: %s" % (kind, [t.path for t in lst]))
        self.by_kind = {k: v[0] for k, v in self.by_kind.items()}
        self.anchor_paths = anchor_paths        # {anchor_const_value: set(paths)}
        self.paths_R = sb.tree(R)
        self.classes = {}
        self.unclassified = []
        self._classify()

    def ns(self, p):
        for t in self.tools.values():
            if t.admitted_new(p):
                return True
        c6 = self.by_kind.get("C6")
        return bool(c6 and c6.frozen(p))

    def _anchor_set(self, tool, const):
        return self.anchor_paths[tool.consts[const]]

    def forbids(self, tool, p):
        allowed_base = self._anchor_set(tool, tool.allowed_anchor)
        frozen_base = self._anchor_set(tool, tool.frozen_anchor)
        if p in allowed_base and p not in tool.allowed:
            return True
        if p in frozen_base and tool.frozen(p):
            return True
        return False

    def in_baseline(self, tool, p):
        return p in self._anchor_set(tool, tool.allowed_anchor) or p in self._anchor_set(tool, tool.frozen_anchor)

    def _classify(self):
        c8 = self.by_kind.get("C8_PARTIAL")
        overlays = c8.append_only if c8 else frozenset()
        replace = (c8.allowed - c8.append_only) if c8 else frozenset()
        for p in self.paths_R:
            if p in self.tools:
                self.classes[p] = "FROZEN_TOOL"
                continue
            tools = list(self.tools.values())
            modifiable = any(self.in_baseline(t, p) for t in tools) and not any(self.forbids(t, p) for t in tools)
            if not modifiable:
                self.classes[p] = "STRICT"
            elif p in overlays:
                self.classes[p] = "NS_OVERLAY" if self.ns(p) else "SHARED_OVERLAY"
            elif p in replace:
                self.classes[p] = "INFRA_REPLACE"
            else:
                self.classes[p] = "UNCLASSIFIED"
                self.unclassified.append(p)
        # subsumption: C6.e/C6.f start-equality targets must already be strict
        c6 = self.by_kind.get("C6")
        if c6:
            for lit in c6.start_equal_literals:
                if lit in self.paths_R and self.classes.get(lit) != "STRICT":
                    self.unclassified.append(lit)
            for pre in c6.start_equal_prefixes:
                for p in c6.allowed:
                    if p.startswith(pre) and p in self.paths_R and self.classes.get(p) != "STRICT":
                        self.unclassified.append(p)

    def counts(self):
        out = {}
        for c in self.classes.values():
            out[c] = out.get(c, 0) + 1
        return dict(sorted(out.items()))

    def of(self, cls):
        return sorted(p for p, c in self.classes.items() if c == cls)


def track_c_modules(paths, ns, roots=fd.STATIC_ROOTS):
    mods = set()
    for p in paths:
        if ns(p) and p.endswith(".py"):
            for root in roots:
                d = fd.dotted(p, root)
                if d:
                    mods.add(d)
    return mods


def references_track_c(names, tcm):
    if names is None:
        return True        # unparseable python is fail-closed
    for n in names:
        for m in tcm:
            if n == m or n.startswith(m + "."):
                return True
    return False


def derive_av(sb, R, V, proj, tcm, roots=fd.STATIC_ROOTS, dynamic=()):
    """A_V = (V\\R) ∩ (NS ∪ EVLREF), closed under static imports and __file__ data paths at V."""
    tR, tV = sb.tree(R), sb.tree(V)
    VR = {p for p in tV if p not in tR}
    av = {p for p in VR if proj.ns(p)}
    reasons = {p: "NS" for p in av}
    for p in sorted(VR - av):
        if p.endswith(".py"):
            names = fd.module_imports(sb.blob(tV[p].sha), p, roots)
            if references_track_c(names, tcm):
                av.add(p)
                reasons[p] = "EVLREF"
    sim = fd.ImportSim(set(tV), roots)
    queue = sorted(p for p in av if p.endswith(".py"))
    while queue:
        p = queue.pop()
        data = sb.blob(tV[p].sha)
        for name in fd.module_imports(data, p, roots) or ():
            for prefix in fd.name_prefixes(name):
                res = sim.find(prefix)
                if res[0] in ("module", "package") and res[1] in VR and res[1] not in av:
                    av.add(res[1])
                    reasons[res[1]] = "IMPORT_CLOSURE:" + p
                    if res[1].endswith(".py"):
                        queue.append(res[1])
        paths, _pins = fd.file_relative_paths(data, p)
        for q in paths:
            if q in VR and q not in av and tV[q].type == "blob":
                av.add(q)
                reasons[q] = "DATA_CLOSURE:" + p
                if q.endswith(".py"):
                    queue.append(q)
    for q in dynamic:
        if q in VR and q not in av:
            av.add(q)
            reasons[q] = "DYNAMIC_READ_AT_V"
    return av, reasons


# ---- projection identity (AC-15..19, AC-21) -------------------------------------------------------
def projection_identity(sb, R, Vs, T, proj, av, v_applies):
    tR, tT = sb.tree(R), sb.tree(T)
    checks = []
    changed = []
    for p, cls in sorted(proj.classes.items()):
        r, t = tR[p], tT.get(p)
        if t is None:
            checks.append(check("AC-15", "NOT_PRESERVED", "projection path missing in T", path=p, cls=cls))
            continue
        if (t.mode, t.type) != (r.mode, r.type):
            checks.append(check("AC-19", "NOT_PRESERVED", "mode/type changed", path=p, cls=cls,
                                R=list(r), T=list(t)))
            continue
        if t.sha == r.sha:
            continue
        changed.append(p)
        allowed_v = [V for V in Vs if v_applies.get(V)]
        if cls in ("FROZEN_TOOL", "STRICT", "UNCLASSIFIED"):
            checks.append(check("AC-15", "NOT_PRESERVED", "protected bytes changed", path=p, cls=cls))
        elif cls in ("NS_OVERLAY", "INFRA_REPLACE"):
            vblobs = {sb.tree(V).get(p).sha for V in allowed_v if sb.tree(V).get(p) is not None}
            if t.sha not in vblobs:
                checks.append(check("AC-17" if cls == "NS_OVERLAY" else "AC-21", "NOT_PRESERVED",
                                    "bytes are neither R's nor an authenticated V's", path=p, cls=cls))
            elif cls == "NS_OVERLAY":
                rb = sb.blob(r.sha)
                if not sb.blob(t.sha).startswith(rb):
                    checks.append(check("AC-17", "NOT_PRESERVED", "V's register is not an append to R's", path=p))
        elif cls == "SHARED_OVERLAY":
            base = sb.blob(r.sha)
            for V in allowed_v:
                e = sb.tree(V).get(p)
                if e is not None and e.sha != r.sha:
                    vb = sb.blob(e.sha)
                    if vb.startswith(base):
                        base = vb
            tb = sb.blob(t.sha)
            if not tb.startswith(base):
                checks.append(check("AC-18", "NOT_PRESERVED", "shared overlay is not an append on the merge result",
                                    path=p))
            elif CONFLICT_MARKER.search(tb[len(base):]):
                checks.append(check("AC-18", "NOT_PRESERVED", "conflict marker in appended delta", path=p))
    # v2 byte binding (AC-21); only when an authenticated V is an ancestor of T (otherwise the
    # A_V-type paths are unattributed complement files, AC-05)
    v2 = []
    applicable = [V for V in Vs if v_applies.get(V)]
    for p in sorted(av) if applicable else []:
        bound = [V for V in Vs if v_applies.get(V) and sb.tree(V).get(p) is not None]
        t = tT.get(p)
        vals = {sb.tree(V)[p] for V in bound}
        if len(vals) > 1:
            v2.append(check("AC-06", "FAIL", "authenticated V references disagree", path=p))
        elif not bound:
            v2.append(check("AC-21", "FAIL", "A_V path without an applicable V", path=p))
        elif t is None or t != vals.pop():
            v2.append(check("AC-21", "FAIL", "A_V bytes/mode differ from V", path=p))
    return checks, v2, changed


def overlay_ordering_note():
    return ("merge-result-only audit (CDR-014 §9, §13): no order-independence claim; shared-overlay "
            "conflicts or unauthorized resolutions fail closed (latent L1)")


# ---- provenance (AC-20 + review HIGH #2) --------------------------------------------------------------
def provenance(sb, T, L, protected, shared, max_paths_for_log=None):
    """Per-commit and per-merge provenance for ``T --not L``."""
    checks = []
    commits = sb.rev_list("--topo-order", T, "--not", L)
    protected = set(protected)
    shared = set(shared)
    merges, nonmerges = [], []
    for c in commits:
        ps = sb.parents(c)
        (merges if len(ps) > 1 else nonmerges).append((c, ps))
    for c, ps in nonmerges:
        if not ps:
            checks.append(check("AC-20", "FAIL", "root commit outside the authenticated lineage", commit=c))
            continue
        changed = set(sb.changed_paths(ps[0], c))
        hit = sorted(changed & protected)
        if hit:
            checks.append(check("AC-20", "FAIL", "non-merge commit outside L touches protected paths",
                                commit=c, paths=hit[:20]))
        for p in sorted(changed & shared):
            before, after = sb.read(ps[0], p), sb.read(c, p)
            if before is not None and (after is None or not after.startswith(before)):
                checks.append(check("AC-20", "FAIL", "non-append edit of a shared overlay outside L", commit=c, path=p))
    watched = protected | shared
    for c, ps in merges:
        if len(ps) > 2:
            trees = [sb.tree(x) for x in ps]
            mt = sb.tree(c)
            diff = sorted(p for p in watched if any(mt.get(p) != t.get(p) for t in trees))
            if diff:
                checks.append(check("AC-20", "NOT_RUN", "octopus merge touching protected paths cannot be recomputed",
                                    commit=c, paths=diff[:20]))
            continue
        clean, tree, conflicted = sb.merge_tree(ps[0], ps[1])
        actual = sb.tree(c)
        recomputed = sb.tree(tree) if tree else {}
        bad_conflict = sorted(set(conflicted) & watched)
        if bad_conflict:
            checks.append(check("AC-20", "FAIL", "merge conflict on protected/overlay paths (unauthorized resolution)",
                                commit=c, paths=bad_conflict[:20]))
        diff = sorted(p for p in watched if p not in conflicted and actual.get(p) != recomputed.get(p))
        if diff:
            checks.append(check("AC-20", "FAIL", "merge result differs from clean recomputation on protected paths",
                                commit=c, paths=diff[:20]))
    return checks, {"commits": len(commits), "merges": len(merges), "non_merges": len(nonmerges),
                    "lineage_base": L}


def git_log_diagnostic(sb, T, L, paths):
    hits = set()
    paths = sorted(paths)
    for i in range(0, len(paths), 400):
        out = sb.out("log", "--format=%H", T, "--not", L, "--", *paths[i:i + 400])
        hits.update(x for x in out.split() if x)
    return sorted(hits)


# ---- complement static checks ---------------------------------------------------------------------------
def config_names_from_pytest():
    """config_names list, extracted by AST from the installed pytest's locate_config."""
    import ast
    import inspect
    try:
        from _pytest.config import findpaths
        src = inspect.getsource(findpaths.locate_config)
    except Exception as exc:
        raise fd.ShapeError("installed pytest findpaths not readable: %s" % exc)
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and n.targets[0].id == "config_names" and isinstance(n.value, ast.List):
            return [e.value for e in n.value.elts]
    raise fd.ShapeError("config_names not found in installed pytest")


def nfc_fold(s):
    return unicodedata.normalize("NFC", s).casefold()


def complement_static(sb, T, R, Vs, v_applies, proj, av, tcm_all, config_names, config_dirs,
                      track_c_workflow, attributed_paths):
    """Findings for files of T outside paths(R) ∪ A_V (the complement)."""
    tT, tR = sb.tree(T), sb.tree(R)
    reference = set(tR) | set(av)
    complement = sorted(p for p in tT if p not in reference)
    findings = []

    def found(cid, what, path, **extra):
        findings.append(dict({"id": cid, "finding": what, "path": path}, **extra))

    for p in complement:
        e = tT[p]
        parts = p.split("/")
        base = parts[-1]
        if e.mode in ("120000", "160000"):
            found("AC-19", "symlink or gitlink in complement", p, mode=e.mode)
        if "__pycache__" in parts or base.endswith(fd.NON_SOURCE_SUFFIXES):
            found("AC-23", "committed bytecode or extension module", p)
        if any(x.endswith((".dist-info", ".egg-info")) for x in parts[:-1]) or base.endswith((".egg-link", ".egg")) \
                or base == "entry_points.txt":
            found("AC-28", "packaging metadata / plugin entry point", p)
        stem, suffix = fd.strip_suffix(base)
        if base.endswith(".pth") or stem in ("sitecustomize", "usercustomize", "conftest"):
            found("AC-28", "startup hook or conftest", p)
        if base in config_names or base == "setup.py":
            d = p.rsplit("/", 1)[0] if "/" in p else ""
            if d in config_dirs:
                found("AC-27", "pytest configuration / rootdir marker on an invocation path", p)
        if proj.ns(p):
            found("AC-21", "unattributed Track C-namespace file", p)
        if p.endswith(".py"):
            names = fd.module_imports(sb.blob(e.sha), p, fd.STATIC_ROOTS) if e.type == "blob" else None
            if names is None:
                found("AC-21", "unparseable python in complement (fail-closed EVLREF)", p)
            elif references_track_c(names, tcm_all):
                found("AC-21", "unattributed importer of Track C modules (latent L3)", p)
    # case / unicode variants (AC-19)
    ref_dirs = fd.all_dirs(reference)
    keys = {}
    for x in reference | ref_dirs:
        keys.setdefault(nfc_fold(x), set()).add(x)
    for p in complement:
        parts = p.split("/")
        for i in range(1, len(parts) + 1):
            q = "/".join(parts[:i])
            if q in reference or q in ref_dirs:
                continue
            if nfc_fold(q) in keys:
                found("AC-19", "case/Unicode variant of a projection path", p, variant_of=sorted(keys[nfc_fold(q)])[:3])
                break
    # shadowing (AC-24)
    findings.extend(shadowing(set(tT), reference, complement))
    # complement workflows that claim Track C identity or run Track C paths (review MEDIUM)
    findings.extend(workflow_spoof(sb, T, Vs, v_applies, complement, track_c_workflow, proj, av))
    return complement, findings


def shadowing(tree_files, reference, complement, roots=fd.STATIC_ROOTS):
    out = []
    ref_dirs = fd.all_dirs(reference)
    d_ref = set()
    for root in roots:
        for p in reference:
            d = fd.dotted(p, root)
            if d:
                d_ref.add(d)
        for d in ref_dirs:
            dd = fd.dir_dotted(d, root)
            if dd:
                d_ref.add(dd)
    tops_ref = {d.split(".")[0] for d in d_ref}
    try:
        dists = set(metadata.packages_distributions())
    except Exception:
        dists = set()
    d_ext = set(sys.stdlib_module_names) | set(sys.builtin_module_names) | dists
    for p in complement:
        base = p.rsplit("/", 1)[-1]
        stem, suffix = fd.strip_suffix(base)
        if stem is None:
            continue
        if stem == "__init__" and (p.rsplit("/", 1)[0] if "/" in p else "") in ref_dirs:
            out.append({"id": "AC-24", "finding": "__init__ added to an existing reference directory "
                        "(namespace package turned regular)", "path": p})
        for root in roots:
            d = fd.dotted(p, root)
            if d is None:
                continue
            if d in d_ref:
                out.append({"id": "AC-24", "finding": "complement module shadows a reference module/package",
                            "path": p, "root": root, "name": d})
                continue
            top = d.split(".")[0]
            top_path = root + "/" + top
            defines_top = top_path not in ref_dirs and not any((top_path + s) in reference for s in fd.ALL_SUFFIXES)
            if defines_top and (top in d_ext or top in tops_ref):
                out.append({"id": "AC-24", "finding": "complement top-level name shadows stdlib/installed/reference name",
                            "path": p, "root": root, "name": top})
    return out


def closure_identity(sb, T, R, Vs, v_applies, proj, av, orders):
    """AC-25: every Track C module's import closure resolves identically at T."""
    tT, tR = sb.tree(T), sb.tree(R)
    findings = []
    modules = sorted(p for p in tR if proj.ns(p) and p.endswith(".py")) + sorted(p for p in av if p.endswith(".py"))
    vref = [V for V in Vs if v_applies.get(V)]
    ref_files = {"R": set(tR)}
    for V in vref:
        ref_files[V] = set(sb.tree(V))
    sims_T = {name: fd.ImportSim(set(tT), roots) for name, roots in orders}
    sims_ref = {(k, name): fd.ImportSim(files, roots) for k, files in ref_files.items() for name, roots in orders}
    checked = 0
    for p in modules:
        refkey = "R" if p in tR else (vref[0] if vref else None)
        if refkey is None:
            continue
        reftree = tR if refkey == "R" else sb.tree(refkey)
        data = sb.blob(reftree[p].sha)
        names = fd.module_imports(data, p, fd.STATIC_ROOTS) or ()
        for name in sorted(names):
            for prefix in fd.name_prefixes(name):
                for oname, roots in orders:
                    a = sims_ref[(refkey, oname)].find(prefix)
                    b = sims_T[oname].find(prefix)
                    checked += 1
                    if a != b:
                        findings.append({"id": "AC-25", "finding": "import resolution changed", "module": p,
                                         "name": prefix, "order": oname, "reference": list(a), "T": list(b)})
                    elif a[0] in ("module", "package") and reftree.get(a[1]) != tT.get(a[1]):
                        findings.append({"id": "AC-25", "finding": "resolved file bytes changed", "module": p,
                                         "name": prefix, "path": a[1]})
    return findings, checked


def workflow_spoof(sb, T, Vs, v_applies, complement, track_c_workflow, proj, av):
    out = []
    tT = sb.tree(T)
    tc_text = sb.read(T, track_c_workflow) or b""
    tc = fd.parse_workflow(tc_text.decode("utf-8", "replace"))
    tc_ids = set(tc["jobs"]) | set(tc["job_names"])
    av_tokens = set()
    for p in av:
        av_tokens.add(p)
        if p.startswith(fd.IMPL + "/"):
            av_tokens.add(p[len(fd.IMPL) + 1:])
    for p in complement:
        if not p.startswith(fd.WORKFLOW_DIR) or not p.endswith((".yml", ".yaml")):
            continue
        text = sb.blob(tT[p].sha).decode("utf-8", "replace")
        wf = fd.parse_workflow(text)
        reasons = []
        if wf["name"] and wf["name"] == tc["name"]:
            reasons.append("workflow name equals the Track C workflow name")
        if (set(wf["jobs"]) | set(wf["job_names"])) & tc_ids:
            reasons.append("job id/name collides with the Track C workflow")
        if not wf["jobs"]:
            reasons.append("unparseable workflow (fail-closed)")
        for token in re.findall(r"[A-Za-z0-9_./*?\[\]-]+", text):
            if "/" not in token and not token.endswith(".py"):
                continue
            cands = {token, fd.IMPL + "/" + token}
            if any(proj.ns(c) and not c.endswith("/") for c in cands if "*" not in c and "?" not in c and "[" not in c):
                reasons.append("references a Track C namespace path: " + token)
                break
            if any(c in av_tokens for c in cands):
                reasons.append("references an A_V path: " + token)
                break
            if any(ch in token for ch in "*?["):
                hit = [q for q in list(proj.classes) + sorted(av) if proj.ns(q) and
                       (fnmatch.fnmatchcase(q, token) or fnmatch.fnmatchcase(q, fd.IMPL + "/" + token))]
                if hit:
                    reasons.append("glob matches Track C paths: " + token)
                    break
        if not reasons:
            continue
        attributed = any(v_applies.get(V) and sb.tree(V).get(p) == tT[p] for V in Vs)
        if not attributed:
            out.append({"id": "AC-32.spoof", "finding": "complement workflow claims or runs Track C scope "
                        "without attribution", "path": p, "reasons": reasons})
    return out


def gitattributes_check(sb, ref, T, paths):
    """AC-31: the given paths must carry the same attributes at T as at ``ref``."""
    tR, tT = sb.tree(ref), sb.tree(T)
    changed = sorted(p for p in set(tR) | set(tT) if p.rsplit("/", 1)[-1] == ".gitattributes"
                     and tR.get(p) != tT.get(p))
    if not changed:
        return [], {"changed_gitattributes": [], "compared": 0}
    keys = ("text", "eol", "crlf", "ident", "filter", "working-tree-encoding", "export-subst",
            "export-ignore", "merge")
    plist = sorted(paths)
    at_t = sb.check_attr(T, plist)
    at_r = sb.check_attr(ref, plist)
    findings = []
    for p in plist:
        a = {k: v for k, v in at_r.get(p, {}).items() if k in keys}
        b = {k: v for k, v in at_t.get(p, {}).items() if k in keys}
        if a != b:
            findings.append({"id": "AC-31", "finding": "attributes of a projection path changed", "path": p,
                             "reference": a, "T": b})
    return findings, {"changed_gitattributes": changed, "compared": len(plist)}
